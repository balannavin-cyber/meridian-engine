"""ENH-133 — EOD session-gate reconciler.

    reconcile_gex_cycle_history_session_local.py
    reconcile_gex_cycle_history_session_local.py --recompute 2026-09-30 [...]

Finalises what the per-cycle writer could not know. Spec:
docs/research/s89_rulings/ENH-133_reconciler_spec_S89.md

WHY IT EXISTS. The writer runs inside a cycle and sees the tape as it stands at
that instant. Measured 2026-10-03: the gamma clock starts 08:30-08:40 IST while
the first market_spot_snapshots tick lands ~09:11:03 every day, so 6-8 of each
day's 74-83 cycles are written with zero ticks and stamped PRE_TICK. PRE_TICK is
an honest statement of what the writer saw; it is not an answer to "did this
date trade?", and that question can only be answered once the date is complete.

TWO PASSES
  1. Whole-date tape verdict: PRE_TICK -> OPEN or FROZEN, uniformly per
     (symbol, date). The TAPE is the evidence; trading_calendar is NOT
     consulted (2026-10-02 is absent from it -- the Rule 18 fail-open shape --
     so a calendar-assisted verdict would read the frozen day as open).
  2. Recompute held_for_cycles over the finalised OPEN set, carrying the streak
     across date boundaries, then re-derive pin_state via core.pin_state.

NEVER touches today's in-progress date. NEVER rewrites a measurement -- and
that is ENFORCED, not conventional: every update goes through _guarded_update,
which refuses a patch touching any column outside MUTABLE (guard R4).
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from core.execution_log import ExecutionLog
from core.pin_state import derive as derive_pin_state

RECONCILER = "reconcile_gex_cycle_history_session_local.py"
RECONCILER_VERSION = "ENH133R_V1"
TARGET_TABLE = "gex_cycle_history"

IST = timezone(timedelta(hours=5, minutes=30))

# The ONLY columns this script is licensed to change. Everything else is a
# measurement taken on its own clock and is not re-derivable later: the
# reconciler changes verdicts, never measurements (spec 2.3, guard R4).
MUTABLE = frozenset({
    "session_gate_state",
    "held_for_cycles",
    "pin_state",
    "pin_state_reason",
    "reconciled_at",
    "reconciler_version",
})


def _load_env() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")
    if not url:
        raise RuntimeError("SUPABASE_URL not found in environment or .env")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not found in environment or .env")
    if not url.startswith(("http://", "https://")):
        raise RuntimeError(f"SUPABASE_URL is invalid: {url!r}. It must start with https://")
    return create_client(url, key)


SUPABASE: Client = _load_env()


def _rows(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    data = getattr(result, "data", None)
    if data is None:
        return []
    return data if isinstance(data, list) else []


def _guarded_update(patch: dict[str, Any]):
    """R4, ENFORCED: refuse any patch that touches a column outside MUTABLE.

    This is the single chokepoint for every write in this script. Without it,
    MUTABLE would be a declared-and-unused tuple and R4 would be a comment --
    a later edit could add a measurement to an update dict and silently break
    "changes verdicts, never measurements", with nothing failing until a parity
    test noticed the scalar had moved. The guard raises at the call site
    instead, before anything is sent.

    Returns the update query builder; the caller chains its own filters.
    """
    stray = sorted(set(patch) - MUTABLE)
    if stray:
        raise RuntimeError(
            f"R4 VIOLATION: {RECONCILER} may only write {sorted(MUTABLE)}; "
            f"patch touched {stray}. The reconciler changes verdicts, never measurements."
        )
    return SUPABASE.table(TARGET_TABLE).update(patch)


def _today_ist() -> date:
    return datetime.now(timezone.utc).astimezone(IST).date()


_FRAC = re.compile(r"\.(\d{1,6})(?=[+-]\d{2}:?\d{2}$|Z$|$)")


def _norm_frac(ts_iso: str) -> str:
    """Pad the microsecond fraction to 6 digits.

    PostgREST trims trailing zeros, so a timestamp whose microseconds end in 0
    arrives with 1, 2, 4 or 5 digits ('2026-10-07T03:30:07.61356+00:00').
    Python 3.10's fromisoformat accepts a fraction of EXACTLY 3 or 6 digits, or
    none at all, and raises ValueError on every other width; 3.11+ is
    permissive. The box is 3.10.

    Same defect and same fix as write_gex_cycle_history_local._norm_frac -- the
    two _ist_date bodies were byte-identical, so the writer's crash was this
    module's crash too (Rule 22: audit the parallel component). Regex is
    deliberately identical to check_contracts_shadow._FRAC. The repo holds ~40
    independent copies of this padding; one shared core/ helper is the right
    fix and is NOT this change (see the TS-PARSE findings, S91).
    """
    return _FRAC.sub(lambda m: "." + m.group(1).ljust(6, "0"), ts_iso)


def _ist_date(ts_iso: str) -> date:
    return datetime.fromisoformat(_norm_frac(ts_iso.replace("Z", "+00:00"))).astimezone(IST).date()


def _day_bounds(d: date) -> tuple[str, str]:
    lo = datetime.combine(d, datetime.min.time(), tzinfo=IST)
    return lo.isoformat(), (lo + timedelta(days=1)).isoformat()


def _page(table: str, select: str, build) -> list[dict[str, Any]]:
    """Paged read, so no count here is ever a capped one.

    Rule 15: PostgREST hard-caps a request at 1000 rows and `limit(n > 1000)`
    still returns 1000. The loop terminates on a SHORT PAGE, never on a
    computed total -- a total would have to come from the same capped source.
    """
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        q = build(SUPABASE.table(table).select(select))
        batch = _rows(q.range(offset, offset + 999).execute())
        out.extend(batch)
        if len(batch) < 1000:
            return out
        offset += 1000


# ---------------------------------------------------------------- eligibility
def unfinalised_dates() -> list[tuple[str, date]]:
    """(symbol, IST date) pairs carrying at least one PRE_TICK row, excluding today.

    A date is UNFINALISED iff it still holds a PRE_TICK row. That definition is
    what makes a re-run a no-op BY CONSTRUCTION rather than by a separate flag
    that could disagree with the work.
    """
    today = _today_ist()
    rows = _page(
        TARGET_TABLE, "symbol,ts",
        lambda q: q.eq("session_gate_state", "PRE_TICK").order("ts"),
    )
    pairs = {(r["symbol"], _ist_date(r["ts"])) for r in rows}
    # Refuse today UNCONDITIONALLY -- not "unless it looks finished". A partial
    # tape is indistinguishable from a frozen one, which is the whole defect
    # this component exists to resolve.
    return sorted((s, d) for (s, d) in pairs if d < today)


# ---------------------------------------------------------------- pass 1
def day_traded(symbol: str, d: date) -> tuple[bool, int]:
    """(traded, day_distinct_spot) from the TAPE over the full IST date.

    trading_calendar is deliberately not consulted: 2026-10-02 is absent from
    it, so a calendar-assisted verdict would read that frozen date as open.
    """
    lo, hi = _day_bounds(d)
    rows = _page(
        "market_spot_snapshots", "spot",
        lambda q: q.eq("symbol", symbol).gte("ts", lo).lt("ts", hi),
    )
    distinct = len({r["spot"] for r in rows if r.get("spot") is not None})
    return distinct > 1, distinct


def pass1_finalise_state(symbol: str, d: date, stamp: str) -> tuple[str, int]:
    """Stamp every row of (symbol, date) OPEN or FROZEN. Returns (state, n_rows).

    A whole-date verdict applied uniformly: once the date is known, the mid-day
    distinction the writer had to make disappears. A traded date has no frozen
    cycles and a frozen date has no open ones.
    """
    traded, distinct = day_traded(symbol, d)
    state = "OPEN" if traded else "FROZEN"
    lo, hi = _day_bounds(d)

    n_rows = len(_page(TARGET_TABLE, "ts",
                       lambda q: q.eq("symbol", symbol).gte("ts", lo).lt("ts", hi)))

    patch: dict[str, Any] = {"session_gate_state": state,
                             "reconciled_at": stamp,
                             "reconciler_version": RECONCILER_VERSION}
    if state == "FROZEN":
        # held_for / pin_state on a frozen row are NULL with a reason: a pin
        # state derived from a book that never moved would be a measurement of
        # the previous session's last print (TD-S89-NEW-1).
        patch["held_for_cycles"] = None
        patch["pin_state"] = None
        patch["pin_state_reason"] = "frozen date"

    (_guarded_update(patch)
     .eq("symbol", symbol).gte("ts", lo).lt("ts", hi).execute())

    print(f"  pass1 {symbol:7s} {d}  distinct_spot={distinct:4d} -> {state:6s}  rows={n_rows}")
    return state, n_rows


# ---------------------------------------------------------------- pass 2
def _prior_open_tail(symbol: str, expiry_date: str, day_lo: str) -> Optional[dict[str, Any]]:
    """The last OPEN row for this leg STRICTLY BEFORE this date.

    This is the carry-forward anchor. It is read per LEG, not per symbol: a
    streak belongs to a (symbol, expiry_date) pair, so anchoring per symbol
    would let one expiry's leader reset the other's streak.
    """
    rows = _rows(
        SUPABASE.table(TARGET_TABLE)
        .select("ts,pin_leader_strike,held_for_cycles")
        .eq("symbol", symbol).eq("expiry_date", expiry_date)
        .eq("session_gate_state", "OPEN")
        .lt("ts", day_lo)
        .order("ts", desc=True)
        .limit(1)
        .execute()
    )
    return rows[0] if rows else None


def pass2_recompute(symbol: str, d: date, stamp: str) -> int:
    """Recompute held_for_cycles then pin_state over the finalised OPEN set.

    THE CARRY-FORWARD RULE (recorded choice, overridable -- spec 3.2):
    a leader that persists across an overnight or holiday gap CONTINUES its
    streak; a leader change resets to 1; a FROZEN date contributes nothing and
    does not itself reset, so the streak bridges it. The alternative -- reset at
    each date boundary -- is defensible and was not chosen, because a pin that
    holds through a weekend is the phenomenon held_for_cycles exists to detect.
    """
    lo, hi = _day_bounds(d)
    rows = _page(
        TARGET_TABLE,
        "symbol,expiry_date,ts,pin_leader_strike,runnerup_share_ratio,conc_top1_share",
        lambda q: (q.eq("symbol", symbol).eq("session_gate_state", "OPEN")
                   .gte("ts", lo).lt("ts", hi).order("ts")),
    )
    if not rows:
        return 0

    by_leg: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_leg[str(r["expiry_date"])].append(r)

    n_updated = 0
    for expiry_date, leg_rows in sorted(by_leg.items()):
        leg_rows.sort(key=lambda r: r["ts"])
        anchor = _prior_open_tail(symbol, expiry_date, lo)
        prev_leader = anchor.get("pin_leader_strike") if anchor else None
        prev_held = int(anchor["held_for_cycles"]) if anchor and anchor.get("held_for_cycles") else 0

        for r in leg_rows:
            leader = r.get("pin_leader_strike")
            if leader is None:
                held: Optional[int] = None
            elif prev_leader is not None and float(prev_leader) == float(leader) and prev_held > 0:
                held = prev_held + 1
            else:
                held = 1

            pin_state, pin_reason = derive_pin_state(
                symbol, held, r.get("runnerup_share_ratio"), r.get("conc_top1_share"))

            (_guarded_update({"held_for_cycles": held,
                              "pin_state": pin_state,
                              "pin_state_reason": pin_reason,
                              "reconciled_at": stamp,
                              "reconciler_version": RECONCILER_VERSION})
             .eq("symbol", symbol).eq("expiry_date", expiry_date).eq("ts", r["ts"])
             .execute())
            n_updated += 1

            if held is not None:
                prev_leader, prev_held = leader, held
            # A NULL-leader row does NOT advance the anchor: it is a gap in the
            # series, not a leader change, so the streak neither grows nor
            # resets across it. A NULL is a gap, never a zero.

        print(f"  pass2 {symbol:7s} {d} {expiry_date}  open_rows={len(leg_rows)} "
              f"carry_from={'yes' if anchor else 'none'}")
    return n_updated


# ---------------------------------------------------------------- main
def _parse_args(argv: list[str]) -> list[date]:
    """Returns explicit --recompute dates, or [] for the normal sweep."""
    if len(argv) == 1:
        return []
    if argv[1] != "--recompute" or len(argv) < 3:
        raise ValueError(f"Usage: {RECONCILER} [--recompute YYYY-MM-DD ...]")
    return [date.fromisoformat(a) for a in argv[2:]]


def _run_recompute(recompute_dates: list[date], today: date, stamp: str) -> int:
    """--recompute runs PASS 2 ONLY, over dates given explicitly.

    Pass 1 is never re-run: a finalised OPEN/FROZEN verdict is evidence about
    the tape, and the tape may since have been archived. This hatch exists for
    a rule change or a recalibration, where pass 2's inputs changed but the
    tape verdict did not.
    """
    bad = [d for d in recompute_dates if d >= today]
    if bad:
        print(f"[ERROR] refusing today or later: {[d.isoformat() for d in bad]}",
              file=sys.stderr)
        return 2
    symbols = sorted({r["symbol"] for r in _page(TARGET_TABLE, "symbol", lambda q: q)})

    # EXACT contract on this path too, counted BEFORE the first update. An
    # expected of 0 would be met by any actual (0 < 0 is false), so it would
    # assert nothing -- the same Rule 0 clause 1 hole as a floor of 1.
    n_expected = 0
    for d in sorted(recompute_dates):
        lo, hi = _day_bounds(d)
        n_expected += len(_page(
            TARGET_TABLE, "ts",
            lambda q, a=lo, b=hi: q.eq("session_gate_state", "OPEN").gte("ts", a).lt("ts", b)))

    log = ExecutionLog(
        script_name=RECONCILER, expected_writes={TARGET_TABLE: n_expected},
        notes=("--recompute dates="
               + str([f'{s}:{d.isoformat()}' for d in sorted(recompute_dates) for s in symbols])),
    )
    print(f"MERDIAN - {RECONCILER}  (--recompute, PASS 2 ONLY)")
    print(f"rows_expected={n_expected}")
    n = 0
    try:
        for d in sorted(recompute_dates):
            for symbol in symbols:
                n += pass2_recompute(symbol, d, stamp)
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"pass2 failed: {e}")
    log.record_write(TARGET_TABLE, n)
    print(f"rows_recomputed={n}")
    return log.complete()


def main() -> int:
    try:
        recompute_dates = _parse_args(sys.argv)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    today = _today_ist()
    stamp = datetime.now(timezone.utc).isoformat()

    if recompute_dates:
        return _run_recompute(recompute_dates, today, stamp)

    targets = unfinalised_dates()
    if not targets:
        # Idempotent BY CONSTRUCTION: a finalised date carries no PRE_TICK row,
        # so a second run finds nothing and writes nothing.
        log = ExecutionLog(script_name=RECONCILER, expected_writes={TARGET_TABLE: 0},
                           notes="no unfinalised dates")
        print(f"MERDIAN - {RECONCILER}: nothing to reconcile "
              f"(no PRE_TICK rows before {today})")
        return log.complete()

    # EXACT contract: the number of rows the sweep will touch, counted BEFORE
    # the first update. A floor would pass on 1 row and on 6,000 alike
    # (Rule 0 clause 1).
    n_expected = 0
    for symbol, d in targets:
        lo, hi = _day_bounds(d)
        n_expected += len(_page(TARGET_TABLE, "ts",
                                lambda q, s=symbol, a=lo, b=hi:
                                q.eq("symbol", s).gte("ts", a).lt("ts", b)))

    log = ExecutionLog(
        script_name=RECONCILER,
        expected_writes={TARGET_TABLE: n_expected},
        notes=f"dates={[f'{s}:{d.isoformat()}' for s, d in targets]}",
    )

    print("=" * 72)
    print(f"MERDIAN - {RECONCILER}")
    print("=" * 72)
    print(f"today_ist={today}  targets={len(targets)}  rows_expected={n_expected}")
    print(f"mutable_columns={sorted(MUTABLE)}")

    n_written = 0
    try:
        for symbol, d in targets:
            state, n_rows = pass1_finalise_state(symbol, d, stamp)
            n_written += n_rows
            if state == "OPEN":
                pass2_recompute(symbol, d, stamp)
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"reconcile failed: {e}")

    log.record_write(TARGET_TABLE, n_written)

    # R2, COMPUTED rather than asserted: no PRE_TICK may survive on any date
    # before today. A survivor is a DATA_ERROR, not a warning -- it means a
    # date was silently skipped, and the count is what can see that.
    survivors = [r for r in _page(TARGET_TABLE, "symbol,ts",
                                  lambda q: q.eq("session_gate_state", "PRE_TICK"))
                 if _ist_date(r["ts"]) < today]
    print(f"R2 pre_tick_survivors_before_today={len(survivors)}")
    if survivors:
        return log.exit_with_reason(
            "DATA_ERROR", exit_code=1,
            error_message=f"R2 FAIL: {len(survivors)} PRE_TICK rows survive before {today}")

    print("=" * 72)
    return log.complete()


if __name__ == "__main__":
    sys.exit(main())
