"""ENH-133 acceptance tests — G1-G3, A(a)-A(e), R1-R6.

    acceptance_enh133_local.py            # all suites
    acceptance_enh133_local.py A          # one suite: G | A | R

NOT RUN IN THE AUTHORING PASS. gex_cycle_history does not exist yet (the DDL is
authored-not-applied), so table-dependent tests report NOT-RUNNABLE until it is
created. That is the correct output for this state, not a failure — which is why
the script probes for the table first and says so rather than crashing.

Every verdict is COMPUTED from a query. The summary is computed from the
results, never a literal: a summary that cannot report failure is not a summary
(S80). The exit code carries the verdict, because a computed verdict that does
not reach the exit code is documentation, not verification (Rule 0 clause 2).

Specs:
  docs/research/s89_rulings/ENH-133_schema_spec_S89.md       (A(a)-A(d))
  docs/research/s89_rulings/ENH-133_writer_spec_S89.md       (G1-G3)
  docs/research/s89_rulings/ENH-133_reconciler_spec_S89.md    (R1-R6, A(e))
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

TABLE = "gex_cycle_history"
WRITER_NAME = "write_gex_cycle_history_local.py"
RECONCILER_NAME = "reconcile_gex_cycle_history_session_local.py"
IST = timezone(timedelta(hours=5, minutes=30))

# A(d) is bound to a MEASURED run, not to the one the ruling first named.
# 2026-09-28 has four interleaving rank-1 leaders (22800 x49 spanning
# 09:20-14:15 WHILE 23000 x31 spans 08:40-15:40), so there is no stable run
# there to increment across. Longest consecutive streak in the window:
AD_DATE = date(2026, 9, 30)
AD_SYMBOL = "NIFTY"
AD_LEADER = 23000.0
AD_EXPECTED_RUN = 73

# The frozen date from TD-S89-NEW-1: ~143k chain rows across 83 distinct ts,
# distinct_spot = 1 for both symbols.
FROZEN_DATE = date(2026, 10, 2)

# Every (relation, column) the writer binds. A(a) probes these BY NAME, so a
# miss is identified rather than merely counted.
BOUND_SOURCES: list[tuple[str, str]] = [
    ("gamma_metrics", "symbol"), ("gamma_metrics", "expiry_date"),
    ("gamma_metrics", "ts"), ("gamma_metrics", "run_id"), ("gamma_metrics", "dte"),
    ("gamma_metrics", "spot"), ("gamma_metrics", "net_gex"),
    ("gamma_metrics", "regime"), ("gamma_metrics", "flip_level"),
    ("option_chain_snapshots", "run_id"), ("option_chain_snapshots", "ts"),
    ("volatility_snapshots", "source_run_id"), ("volatility_snapshots", "atm_iv_avg"),
    ("v_gex_strike_rank", "strike_rank"), ("v_gex_strike_rank", "strike"),
    ("v_gex_strike_rank", "gex_cr"), ("v_gex_strike_rank", "share_of_abs"),
    ("v_gex_strike_rank", "cum_share_of_abs"), ("v_gex_strike_rank", "n_ranked"),
    ("v_gex_concentration", "hhi_net"), ("v_gex_concentration", "hhi_call"),
    ("v_gex_concentration", "hhi_put"),
    ("v_gex_max_pain", "max_pain_strike"), ("v_gex_max_pain", "is_fresh"),
    ("v_gex_max_pain", "snapshot_age_min"),
    ("v_gex_pin_maxpain", "is_fresh"), ("v_gex_pin_maxpain", "snapshot_age_min"),
    ("v_gex_strike_walls", "call_wall"), ("v_gex_strike_walls", "put_wall"),
    ("v_gex_repriced_flip", "ts"), ("v_gex_repriced_flip", "front_expiry"),
    ("v_gex_repriced_flip", "flip"),
    ("market_spot_snapshots", "symbol"), ("market_spot_snapshots", "ts"),
    ("market_spot_snapshots", "spot"),
]


def _load_env() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not found")
    return create_client(url, key)


SUPABASE: Client = _load_env()
RESULTS: list[tuple[str, str, str]] = []   # (id, verdict, detail)


def record(test_id: str, ok: Optional[bool], detail: str) -> None:
    """Verdict is COMPUTED from `ok`. None means the test could not run."""
    verdict = "NOT-RUNNABLE" if ok is None else ("PASS" if ok else "FAIL")
    RESULTS.append((test_id, verdict, detail))
    print(f"  {test_id:6s} {verdict:12s} {detail}")


def _rows(res: Any) -> list[dict[str, Any]]:
    data = getattr(res, "data", None) if res is not None else None
    return data if isinstance(data, list) else []


def _page(table: str, select: str, build) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch = _rows(build(SUPABASE.table(table).select(select))
                      .range(offset, offset + 999).execute())
        out.extend(batch)
        if len(batch) < 1000:
            return out
        offset += 1000


def _ist_date(ts_iso: str) -> date:
    return datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).astimezone(IST).date()


def _day_bounds(d: date) -> tuple[str, str]:
    lo = datetime.combine(d, datetime.min.time(), tzinfo=IST)
    return lo.isoformat(), (lo + timedelta(days=1)).isoformat()


def _expected(log_row: dict[str, Any]) -> Optional[int]:
    ew = log_row.get("expected_writes") or {}
    v = ew.get(TABLE) if isinstance(ew, dict) else None
    return int(v) if v is not None else None


def table_exists() -> bool:
    try:
        SUPABASE.table(TABLE).select("symbol").limit(1).execute()
        return True
    except Exception:
        return False


# ============================================================ G — writer guards
def suite_G(live: bool) -> None:
    print("\nG — writer guards (writer spec section 8)")

    # ---- G1: the declared contract must equal the MEASURED leg count.
    #
    # The earlier form of this test asked whether expected_writes was 1 or
    # absent. That could not fail for the reason it names: measured 2026-10-03,
    # run_pipeline is PER-SYMBOL and each symbol gets its OWN run_id, so a
    # run_id carries exactly ONE (symbol, expiry_date) row in gamma_metrics —
    # 493 of 493 run_ids since 09-29, zero carrying two symbols. On that data
    # "expected == 1" is the CORRECT answer, so a test that flags 1 as
    # floor-shaped would fail every healthy run, and a test that accepts 1
    # would accept a hardcoded floor. Neither measures the contract.
    #
    # So G1 compares the DECLARED expected against the COUNT re-derived from
    # gamma_metrics for that invocation's own run_id. It fails when the writer
    # declares a number it did not compute — which is the thing Rule 0 clause 1
    # is about — and it keeps working if capture depth ever puts two expiries
    # under one run_id.
    logs = _page("script_execution_log",
                 "invocation_id,expected_writes,actual_writes,notes,exit_reason",
                 lambda q: q.eq("script_name", WRITER_NAME))
    if not logs:
        record("G1", None, "no writer invocations logged yet")
    else:
        mismatched: list[str] = []
        unparsed = 0
        for l in logs:
            m = re.search(r"run_id=([0-9a-fA-F-]{36})", str(l.get("notes") or ""))
            if not m:
                unparsed += 1
                continue
            run_id = m.group(1)
            legs = {(r["symbol"], str(r["expiry_date"]))
                    for r in _page("gamma_metrics", "symbol,expiry_date",
                                   lambda q, rid=run_id: q.eq("run_id", rid))}
            declared = _expected(l)
            if declared != len(legs):
                mismatched.append(f"{run_id[:8]}: declared={declared} measured={len(legs)}")
        checked = len(logs) - unparsed
        record("G1", checked > 0 and not mismatched,
               f"{checked}/{len(logs)} invocations with a parseable run_id; "
               f"{len(mismatched)} declared != measured legs"
               + (f" -> {mismatched[:3]}" if mismatched else "")
               + ("" if checked else "  (none parseable — test vacuous, not passing)"))

    # ---- G2: per-symbol distinct-ts coverage = 100% of the gamma clock.
    # TD-S54-NEW-1: an upsert can merge a lost per-symbol write into silence,
    # so coverage is measured PER SYMBOL against the gamma clock's own ts set.
    if not live:
        record("G2", None, f"{TABLE} absent — apply the DDL first")
    else:
        gm = _page("gamma_metrics", "symbol,ts", lambda q: q)
        hx = _page(TABLE, "symbol,ts", lambda q: q)
        want: dict[str, set] = defaultdict(set)
        have: dict[str, set] = defaultdict(set)
        for r in gm:
            want[r["symbol"]].add(r["ts"])
        for r in hx:
            have[r["symbol"]].add(r["ts"])
        gaps = {s: len(want[s] - have.get(s, set())) for s in sorted(want)}
        record("G2", bool(gaps) and sum(gaps.values()) == 0,
               f"missing ts per symbol: {gaps}  (must be 100%, not 'high')")

    # ---- G3: provenance on every row.
    if not live:
        record("G3", None, f"{TABLE} absent")
    else:
        rows = _page(TABLE, "writer,writer_version", lambda q: q)
        missing = [r for r in rows if not r.get("writer") or not r.get("writer_version")]
        record("G3", bool(rows) and not missing,
               f"{len(rows)} rows; {len(missing)} without writer/writer_version")


# ============================================================ A — acceptance
def suite_A(live: bool) -> None:
    print("\nA — acceptance (schema spec section 5, reconciler spec section 7)")

    # ---- A(a): every bound source column exists, BY NAME.
    # information_schema is not exposed over PostgREST, so each column is
    # probed by selecting it: a missing column is a rejected request, and that
    # rejection is what identifies it.
    missing: list[str] = []
    for tbl, col in BOUND_SOURCES:
        try:
            SUPABASE.table(tbl).select(col).limit(1).execute()
        except Exception:
            missing.append(f"{tbl}.{col}")
    record("A(a)", not missing,
           f"{len(BOUND_SOURCES)} bound pairs probed; missing: {missing or 'none'}")

    # ---- A(b) is G2. Stated rather than silently skipped.
    record("A(b)", None, "same test as G2 by design (writer spec section 8)")

    # ---- A(c): the frozen date ends FROZEN, and no traded date keeps PRE_TICK.
    if not live:
        record("A(c)", None, f"{TABLE} absent")
    else:
        lo, hi = _day_bounds(FROZEN_DATE)
        frozen_rows = _page(TABLE, "session_gate_state",
                            lambda q: q.gte("ts", lo).lt("ts", hi))
        states = {r["session_gate_state"] for r in frozen_rows}
        today = datetime.now(timezone.utc).astimezone(IST).date()
        pre_tick = [r for r in _page(TABLE, "ts",
                                     lambda q: q.eq("session_gate_state", "PRE_TICK"))
                    if _ist_date(r["ts"]) < today]
        record("A(c)", bool(frozen_rows) and states == {"FROZEN"} and not pre_tick,
               f"{FROZEN_DATE} states={states or 'no rows'}; "
               f"PRE_TICK before today={len(pre_tick)}")

    # ---- A(d): held_for runs 1 -> 73 across 09-30 leader 23000, then resets.
    # AFTER reconciliation. The streak starts 08:50, before that day's first
    # tick at 09:11:04, so at write time its opening cycles are PRE_TICK and
    # the run reads short. This is a RECONCILER test and is not expected to
    # pass at write time.
    if not live:
        record("A(d)", None, f"{TABLE} absent")
    else:
        lo, hi = _day_bounds(AD_DATE)
        rows = sorted(
            _page(TABLE, "ts,pin_leader_strike,held_for_cycles,session_gate_state",
                  lambda q: q.eq("symbol", AD_SYMBOL).gte("ts", lo).lt("ts", hi)),
            key=lambda r: r["ts"])
        streak = [r for r in rows
                  if r.get("pin_leader_strike") is not None
                  and float(r["pin_leader_strike"]) == AD_LEADER
                  and r.get("session_gate_state") == "OPEN"]
        held = [r.get("held_for_cycles") for r in streak]
        monotonic = held == list(range(1, len(held) + 1))
        record("A(d)", bool(held) and monotonic and len(held) == AD_EXPECTED_RUN,
               f"leader {AD_LEADER} OPEN cycles={len(held)} "
               f"(expected {AD_EXPECTED_RUN}); strictly 1..n={monotonic}")

    # ---- A(e): carry-forward across a date boundary.
    # The expected value is COMPUTED at test time, never carried from a
    # document: an expected value obtained by running the thing is not an
    # assertion (Rule 0 clause 3). So this asserts the RELATIONSHIP — same
    # leader across a boundary implies +1 — not a number.
    if not live:
        record("A(e)", None, f"{TABLE} absent")
    else:
        rows = sorted(
            _page(TABLE, "symbol,expiry_date,ts,pin_leader_strike,held_for_cycles",
                  lambda q: q.eq("session_gate_state", "OPEN")),
            key=lambda r: (r["symbol"], str(r["expiry_date"]), r["ts"]))
        by_leg: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            by_leg[(r["symbol"], str(r["expiry_date"]))].append(r)
        violations: list[str] = []
        checked = 0
        for (sym, xp), leg in by_leg.items():
            for prev, cur in zip(leg, leg[1:]):
                if _ist_date(prev["ts"]) == _ist_date(cur["ts"]):
                    continue                      # same date: not a boundary
                if prev.get("pin_leader_strike") is None or cur.get("pin_leader_strike") is None:
                    continue
                if float(prev["pin_leader_strike"]) != float(cur["pin_leader_strike"]):
                    continue                      # leader changed: reset is correct
                checked += 1
                if (cur.get("held_for_cycles") or 0) != (prev.get("held_for_cycles") or 0) + 1:
                    violations.append(f"{sym}/{xp} {prev['ts']}->{cur['ts']}")
        record("A(e)", checked > 0 and not violations,
               f"{checked} same-leader date boundaries; {len(violations)} failed to carry"
               + ("" if checked else "  (no boundary present — test vacuous, not passing)"))


# ============================================================ R — reconciler
def suite_R(live: bool) -> None:
    print("\nR — reconciler guards (reconciler spec section 6)")
    today = datetime.now(timezone.utc).astimezone(IST).date()

    if not live:
        for t in ("R1", "R2", "R3", "R4", "R5", "R6"):
            record(t, None, f"{TABLE} absent — apply the DDL first")
        return

    logs = _page("script_execution_log", "expected_writes,actual_writes,notes",
                 lambda q: q.eq("script_name", RECONCILER_NAME))

    # ---- R1: the declared contract must equal the MEASURED row count of the
    # dates the invocation names. Same discipline as G1: not "is it 1", but
    # "does the declared number match what that invocation's own scope holds".
    # The reconciler's notes carry dates=['NIFTY:2026-09-30', ...].
    if not logs:
        record("R1", None, "no reconciler invocations logged yet")
    else:
        mismatched: list[str] = []
        unparsed = 0
        for l in logs:
            notes = str(l.get("notes") or "")
            pairs = re.findall(r"([A-Z]+):(\d{4}-\d{2}-\d{2})", notes)
            if not pairs:
                unparsed += 1
                continue
            n_rows = 0
            for sym, d in pairs:
                lo, hi = _day_bounds(date.fromisoformat(d))
                n_rows += len(_page(TABLE, "ts",
                                    lambda q, s=sym, a=lo, b=hi:
                                    q.eq("symbol", s).gte("ts", a).lt("ts", b)))
            declared = _expected(l)
            if declared != n_rows:
                mismatched.append(f"{pairs[0][1]}+: declared={declared} measured={n_rows}")
        checked = len(logs) - unparsed
        record("R1", checked > 0 and not mismatched,
               f"{checked}/{len(logs)} sweep invocations parseable; "
               f"{len(mismatched)} declared != measured"
               + (f" -> {mismatched[:3]}" if mismatched else "")
               + ("" if checked else "  (none parseable — test vacuous, not passing)"))

    # ---- R2: no PRE_TICK survives before today.
    survivors = [r for r in _page(TABLE, "ts",
                                  lambda q: q.eq("session_gate_state", "PRE_TICK"))
                 if _ist_date(r["ts"]) < today]
    record("R2", not survivors, f"{len(survivors)} PRE_TICK rows before {today}")

    # ---- R3: today untouched. A reconciled row on today's date means the date
    # comparison is off by one, which would freeze a live day.
    lo, hi = _day_bounds(today)
    touched = [r for r in _page(TABLE, "ts,reconciled_at",
                                lambda q: q.gte("ts", lo).lt("ts", hi))
               if r.get("reconciled_at")]
    record("R3", not touched, f"{len(touched)} rows on {today} carry reconciled_at")

    # ---- R4: measurements unchanged. Enforced in-process by _guarded_update;
    # checked here from the OUTSIDE — a reconciled FROZEN row must still carry
    # its measured scalars. A reconciler that recomputed instead of
    # re-verdicting would have nulled them.
    frozen = _page(TABLE, "ts,pin_leader_strike,conc_top1_share,spot,reconciled_at",
                   lambda q: q.eq("session_gate_state", "FROZEN"))
    stripped = [r for r in frozen if r.get("reconciled_at")
                and r.get("pin_leader_strike") is None
                and r.get("conc_top1_share") is None
                and r.get("spot") is None]
    record("R4", not frozen or not stripped,
           f"{len(frozen)} FROZEN rows; {len(stripped)} lost every measured scalar")

    # ---- R5: coverage — a reconciled date has NO row left unreconciled.
    rows = _page(TABLE, "symbol,ts,reconciled_at", lambda q: q)
    by_day: dict[tuple[str, date], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_day[(r["symbol"], _ist_date(r["ts"]))].append(r)
    partial = [f"{s}/{d}" for (s, d), rs in by_day.items()
               if d < today
               and any(r.get("reconciled_at") for r in rs)
               and any(not r.get("reconciled_at") for r in rs)]
    record("R5", not partial,
           f"{len(partial)} dates partially reconciled: {partial[:5]}")

    # ---- R6: streak continuity within a leg — strictly +1 while the leader
    # holds, exactly 1 on a change.
    open_rows = sorted(
        _page(TABLE, "symbol,expiry_date,ts,pin_leader_strike,held_for_cycles",
              lambda q: q.eq("session_gate_state", "OPEN")),
        key=lambda r: (r["symbol"], str(r["expiry_date"]), r["ts"]))
    legs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in open_rows:
        legs[(r["symbol"], str(r["expiry_date"]))].append(r)
    bad: list[str] = []
    for (sym, xp), leg in legs.items():
        for prev, cur in zip(leg, leg[1:]):
            if prev.get("pin_leader_strike") is None or cur.get("pin_leader_strike") is None:
                continue
            same = float(prev["pin_leader_strike"]) == float(cur["pin_leader_strike"])
            want = (prev.get("held_for_cycles") or 0) + 1 if same else 1
            if (cur.get("held_for_cycles") or 0) != want:
                bad.append(f"{sym}/{xp}@{cur['ts']}")
    record("R6", bool(open_rows) and not bad,
           f"{len(open_rows)} OPEN rows; {len(bad)} held_for discontinuities")


# ============================================================ main
def main() -> int:
    which = sys.argv[1].upper() if len(sys.argv) > 1 else "ALL"
    live = table_exists()

    print("=" * 72)
    print("ENH-133 acceptance — G1-G3, A(a)-A(e), R1-R6")
    print("=" * 72)
    print(f"{TABLE} present: {live}")
    if not live:
        print("  -> the DDL is authored-NOT-applied "
              "(sql/2026-10-03_s89_gex_cycle_history.sql).")
        print("  -> table-dependent tests report NOT-RUNNABLE, which is the correct")
        print("     output for this state rather than a failure.")

    if which in ("ALL", "G"):
        suite_G(live)
    if which in ("ALL", "A"):
        suite_A(live)
    if which in ("ALL", "R"):
        suite_R(live)

    n_pass = sum(1 for _, v, _ in RESULTS if v == "PASS")
    n_fail = sum(1 for _, v, _ in RESULTS if v == "FAIL")
    n_na = sum(1 for _, v, _ in RESULTS if v == "NOT-RUNNABLE")
    print("\n" + "=" * 72)
    print(f"{len(RESULTS)} tests: {n_pass} PASS  {n_fail} FAIL  {n_na} NOT-RUNNABLE")
    if n_fail:
        print("FAILING: " + ", ".join(t for t, v, _ in RESULTS if v == "FAIL"))
    print("=" * 72)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
