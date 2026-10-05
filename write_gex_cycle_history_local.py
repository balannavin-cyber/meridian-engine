"""ENH-133 — per-cycle layer-history writer.

    write_gex_cycle_history_local.py <run_id>

Upserts ONE gex_cycle_history row per (symbol, expiry_date) for the given
gamma run. Idempotent on the PK (symbol, expiry_date, ts).

Spec: docs/research/s89_rulings/ENH-133_writer_spec_S89.md
      docs/research/s89_rulings/ENH-133_schema_spec_S89.md
DDL:  sql/2026-10-03_s89_gex_cycle_history.sql        (authored-NOT-applied)
Seed: sql/2026-10-03_s89_seed_pin_state_params.sql    (authored-NOT-applied)

HOOK POINT (measured, not chosen for convenience): this runs from
run_option_snapshot_and_gamma.py AFTER the vol_rc guard (:105) and BEFORE
run_market_state (:106). v_gex_strike_rank and v_gex_strike_walls READ
volatility_snapshots, which lands at :102 -- so hooking at the end of
compute_gamma_metrics_local.py would read atm_iv_used, sigma, dist_sigma,
band_used and both walls from the PREVIOUS cycle.

NOT A SHADOW WRITER. There is no --shadow flag and no shadow table (writer spec
section 4): held_for_cycles is a carry-forward chain, so two copies would
accumulate independent streaks that neither could check against. On a bug:
truncate and restart.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from core.execution_log import ExecutionLog
from core.pin_state import derive as derive_pin_state
from core.trading_calendar_gate import is_trading_day, previous_trading_day

WRITER = "write_gex_cycle_history_local.py"
WRITER_VERSION = "ENH133_V1"
TARGET_TABLE = "gex_cycle_history"

IST = timezone(timedelta(hours=5, minutes=30))

# D-5b / D-5c. T is in TRADING days; cap and floor are the ruled values.
BOOST_COEFF = 2.53
BOOST_CAP = 3.70
T_FLOOR = 0.47


# ---------------------------------------------------------------- env / client
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


def _ist_date(ts_iso: str) -> date:
    """IST calendar date of a true timestamptz string.

    option_chain_snapshots / gamma_metrics / market_spot_snapshots all store
    true timestamptz (verified S89) -- this is NOT the hist_spot_bars_5m
    IST-as-UTC case, so astimezone is correct here and replace(tzinfo=None)
    would be wrong.
    """
    return datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).astimezone(IST).date()


# ---------------------------------------------------------------- source reads
def fetch_legs(run_id: str) -> list[dict[str, Any]]:
    """The run's gamma_metrics rows -- one per (symbol, expiry_date) leg.

    This is also where the EXACT write contract comes from: N is the number of
    distinct (symbol, expiry_date) pairs HERE, computed BEFORE the first row is
    built. Deriving N from the rows actually sent would make the contract assert
    nothing (Rule 0 clause 3).
    """
    res = (
        SUPABASE.table("gamma_metrics")
        .select("symbol,expiry_date,ts,run_id,dte,spot,net_gex,regime,flip_level")
        .eq("run_id", run_id)
        .order("symbol")
        .order("expiry_date")
        .execute()
    )
    return _rows(res)


def _one(table: str, select: str, filters: list[tuple[str, Any]],
         order: Optional[tuple[str, bool]] = None) -> Optional[dict[str, Any]]:
    q = SUPABASE.table(table).select(select)
    for col, val in filters:
        q = q.eq(col, val)
    if order:
        q = q.order(order[0], desc=order[1])
    rows = _rows(q.limit(1).execute())
    return rows[0] if rows else None


def fetch_chain_ts(run_id: str, symbol: str) -> Optional[str]:
    """option_chain_snapshots.ts for THIS run_id -- bound on run_id, never nearest ts.

    Measured 2026-10-03: 480 chain rows carried the gamma run_id with ts exactly
    equal to the gamma ts. The maximum chain ts inside a +/-5-minute window was
    09:55:07, which belongs to the NEXT cycle -- a nearest-ts rule would have
    silently taken it.
    """
    row = _one("option_chain_snapshots", "ts", [("run_id", run_id), ("symbol", symbol)])
    return row["ts"] if row else None


def fetch_atm_iv(run_id: str, symbol: str, expiry_date: str) -> Optional[float]:
    """volatility_snapshots.atm_iv_avg -- joined on source_run_id, NOT run_id.

    That relation has no run_id column at all; its key is source_run_id, whose
    value equals gamma_metrics.run_id. Joining on `run_id` would not compile.
    """
    row = _one(
        "volatility_snapshots", "atm_iv_avg",
        [("source_run_id", run_id), ("symbol", symbol), ("expiry_date", expiry_date)],
    )
    return row["atm_iv_avg"] if row else None


def fetch_rank_rows(run_id: str, symbol: str, expiry_date: str) -> list[dict[str, Any]]:
    """Every ranked strike for the leg, rank ascending.

    This is the PostgREST path, where Rule 15's 1000-row cap is real (unlike
    bin/roq.sh, which streams). A ladder is ~116 strikes, so one request covers
    it; the explicit limit documents that rather than relying on a default.
    """
    res = (
        SUPABASE.table("v_gex_strike_rank")
        .select("strike_rank,strike,gex_cr,share_of_abs,cum_share_of_abs,n_ranked,n_strikes")
        .eq("run_id", run_id).eq("symbol", symbol).eq("expiry_date", expiry_date)
        .order("strike_rank")
        .limit(1000)
        .execute()
    )
    return _rows(res)


def fetch_concentration(run_id: str, symbol: str, expiry_date: str) -> Optional[dict[str, Any]]:
    return _one("v_gex_concentration", "hhi_net,hhi_call,hhi_put",
                [("run_id", run_id), ("symbol", symbol), ("expiry_date", expiry_date)])


def fetch_max_pain(run_id: str, symbol: str, expiry_date: str) -> Optional[dict[str, Any]]:
    return _one("v_gex_max_pain", "max_pain_strike,snapshot_age_min,is_fresh",
                [("run_id", run_id), ("symbol", symbol), ("expiry_date", expiry_date)])


def fetch_pin_maxpain(run_id: str, symbol: str, expiry_date: str) -> Optional[dict[str, Any]]:
    return _one("v_gex_pin_maxpain", "snapshot_age_min,is_fresh",
                [("run_id", run_id), ("symbol", symbol), ("expiry_date", expiry_date)])


def fetch_walls(run_id: str, symbol: str, expiry_date: str) -> Optional[dict[str, Any]]:
    return _one("v_gex_strike_walls", "call_wall,put_wall",
                [("run_id", run_id), ("symbol", symbol), ("expiry_date", expiry_date)])


def fetch_repriced_flip(symbol: str) -> Optional[dict[str, Any]]:
    """L3. Latest row only -- the view is latest-scoped and carries no run_id.

    The caller CLOCK-MATCHES whatever comes back; it is never trusted as-is.
    """
    return _one("v_gex_repriced_flip", "ts,spot,front_expiry,flip,status",
                [("symbol", symbol)], order=("ts", True))


# ---------------------------------------------------------------- derived fields
def derive_rank_fields(rank_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """pin_leader_strike, gamma_at_pin, runnerup_share_ratio, top5_share, conc_hhi.

    Five of the scalars this table stores exist in NO relation and are derived
    here rather than selected: runner-up strike, runner-up margin, gamma at pin,
    top-5 share, per-rank shares.
    """
    out: dict[str, Any] = {
        "pin_leader_strike": None, "gamma_at_pin": None,
        "runnerup_share_ratio": None, "top5_share": None,
        "top5_share_n_ranks": None, "conc_hhi": None,
    }
    if not rank_rows:
        return out

    by_rank = {int(r["strike_rank"]): r for r in rank_rows if r.get("strike_rank") is not None}
    r1 = by_rank.get(1)
    if r1 is not None:
        out["pin_leader_strike"] = r1.get("strike")
        out["gamma_at_pin"] = r1.get("gex_cr")

    r2 = by_rank.get(2)
    s1 = float(r1["share_of_abs"]) if r1 and r1.get("share_of_abs") is not None else None
    s2 = float(r2["share_of_abs"]) if r2 and r2.get("share_of_abs") is not None else None
    if s1 is not None and s2 is not None and s1 != 0:
        out["runnerup_share_ratio"] = s2 / s1
    # A single-ranked-strike ladder leaves this NULL. core.pin_state.derive
    # then reads STABLE rather than LOCKED -- "no runner-up" is "cannot confirm
    # a lock", a recorded choice, not an oversight.

    # top5_share: rank 5's cumulative share, or the deepest rank available.
    # The edge is real -- v_gex_strike_rank ranks only CONTRIBUTING strikes
    # (n_ranked 110 of n_strikes 116 on 10-01), so a thin ladder can rank fewer
    # than five. Storing the rank used keeps that degradation inspectable; a
    # bare NULL would be indistinguishable from "not computed".
    available = sorted(k for k in by_rank if k <= 5)
    if available:
        deepest = available[-1]
        out["top5_share"] = by_rank[deepest].get("cum_share_of_abs")
        out["top5_share_n_ranks"] = deepest

    # conc_hhi -- the TRUE Herfindahl, sum of squared shares over ALL ranked
    # strikes. Distinct from conc_top1_share, which is the single top strike's
    # share: measured 0.04635883 vs 0.09419433 on NIFTY 10-01, a factor of ~2.
    shares = [float(r["share_of_abs"]) for r in rank_rows if r.get("share_of_abs") is not None]
    if shares:
        out["conc_hhi"] = sum(s * s for s in shares)
    return out


def trading_days_to_expiry(run_date: date, expiry: date) -> int:
    """Count open days strictly after run_date, up to and including expiry.

    gamma_metrics.dte is CALENDAR days -- measured across 8 runs (10-01: dte 5 =
    2 trading days). Feeding dte to boost() would give 1.13 where 1.79 is
    correct, a 58% understatement. So the conversion is mandatory, not a nicety.

    Uses core/trading_calendar_gate.py rather than a new inline copy
    (TD-S60-NEW-3). NOTE the gate FAILS OPEN: a missing calendar row counts the
    day as open, which inflates T and so DEFLATES boost -- the conservative
    direction, but inherited behaviour, not a guarantee. Calendar health is
    checked separately, once per run, in main().
    """
    n = 0
    d = run_date + timedelta(days=1)
    while d <= expiry:
        if is_trading_day(d.isoformat()):
            n += 1
        d += timedelta(days=1)
    return n


def boost(t_days: float) -> float:
    t = max(float(t_days), T_FLOOR)
    return min(BOOST_COEFF * (t ** -0.5), BOOST_CAP)


def conviction_for(runnerup_share_ratio: Optional[float], t_days: Optional[int],
                   calendar_healthy: bool) -> tuple[Optional[float], Optional[str]]:
    """(conviction, conviction_reason). Stage 1 only -- D-5c.

    Stage 2 multiplies by the 30-session conc_top1_share percentile once this
    table has history; it is deliberately absent, not forgotten.
    """
    if runnerup_share_ratio is None:
        return None, "null input: runnerup_share_ratio"
    if not calendar_healthy:
        # The calendar could not answer, so T is not trustworthy. NULL with a
        # reason rather than a number computed off calendar days -- absence is
        # not a verdict.
        return None, "trading_calendar unavailable (fail-open detected)"
    if t_days is None:
        return None, "null input: t_days"
    return (1.0 - float(runnerup_share_ratio)) * boost(t_days), None


# ---------------------------------------------------------------- session gate
# One gate per (symbol, ts), not per leg. Both expiry legs of a cycle share
# the symbol and the ts, so the tape read is identical for each -- caching it
# halves the reads and guarantees the two legs cannot disagree about the state.
_GATE_CACHE: dict[tuple[str, str], tuple[str, Optional[int]]] = {}


def session_gate(symbol: str, ist_day: date, ts_iso: str) -> tuple[str, Optional[int]]:
    """(session_gate_state, session_gate_ticks) at WRITE TIME -- provisional.

    Three states, because two cannot tell a pre-open cycle from a closed market:

        ticks == 0                            -> PRE_TICK
        distinct_spot > 1                     -> OPEN
        else (ticks >= 1, distinct_spot == 1) -> FROZEN

    Measured 2026-10-03: the gamma clock starts 08:30-08:40 IST while the first
    market_spot_snapshots tick lands ~09:11:03 every day, so 6-8 of each day's
    74-83 cycles legitimately have zero ticks. A boolean gate would stamp those
    real cycles not-a-session, drop ~9% of each day from the default read, and
    shorten every streak that begins before 09:11.

    PRE_TICK is FINALISED by reconcile_gex_cycle_history_session_local.py, which
    is the only component that can see a completed date.
    """
    cache_key = (symbol, ts_iso)
    if cache_key in _GATE_CACHE:
        return _GATE_CACHE[cache_key]

    lo = datetime.combine(ist_day, datetime.min.time(), tzinfo=IST)

    # PAGED, so session_gate_ticks is an EXACT count rather than a capped one.
    # PostgREST hard-caps a request at 1000 rows and `limit(n > 1000)` still
    # returns 1000 (Rule 15), so a single bounded read would silently cap if the
    # feed cadence ever grew. Today's tape is ~420 ticks/day, well inside one
    # page -- which is exactly why a cap here would be invisible until it
    # mattered. The loop terminates on a short page, never on a computed total.
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch = _rows(
            SUPABASE.table("market_spot_snapshots")
            .select("spot")
            .eq("symbol", symbol)
            .gte("ts", lo.isoformat())
            .lte("ts", ts_iso)
            .order("ts")
            .range(offset, offset + 999)
            .execute()
        )
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    ticks = len(rows)
    if ticks == 0:
        out = ("PRE_TICK", 0)
    else:
        distinct_spot = len({r["spot"] for r in rows if r.get("spot") is not None})
        out = ("OPEN" if distinct_spot > 1 else "FROZEN"), ticks
    _GATE_CACHE[cache_key] = out
    return out


def clock_match_repriced_flip(symbol: str, run_ist_day: date,
                              expiry_date: str) -> dict[str, Any]:
    """L3, clock-matched to this run -- or NULL with the reason.

    v_gex_repriced_flip has NO run_id and NO dte, names its expiry front_expiry,
    and its latest row can sit on a different trading date than the gamma run:
    measured 2026-10-03 at 2026-10-02 10:10:04+00 on the FROZEN spot 22421.95
    while the gamma clock was 2026-10-01 09:50:07+00 -- a ~1,460-minute gap onto
    a frozen book. The stale latest is never taken.
    """
    row = fetch_repriced_flip(symbol)
    if row is None:
        return {"repriced_flip_level": None, "repriced_flip_ts": None,
                "repriced_flip_source": "UNMATCHED_NULL"}
    returned_ts = row.get("ts")
    same_day = returned_ts is not None and _ist_date(returned_ts) == run_ist_day
    same_expiry = str(row.get("front_expiry")) == str(expiry_date)
    if same_day and same_expiry:
        return {"repriced_flip_level": row.get("flip"), "repriced_flip_ts": returned_ts,
                "repriced_flip_source": "CLOCK_MATCHED"}
    # Record the ts it DID return, so a reader can test the mismatch rather
    # than trust that one was detected.
    return {"repriced_flip_level": None, "repriced_flip_ts": returned_ts,
            "repriced_flip_source": "UNMATCHED_NULL"}


def held_for_cycles_provisional(symbol: str, expiry_date: str, ts_iso: str,
                                leader: Optional[float], state: str) -> Optional[int]:
    """Carry-forward over OPEN rows only -- PROVISIONAL.

    A FROZEN row gets NULL: a pin state derived from a book that never moved
    would be a measurement of the previous session's last print.
    A PRE_TICK row also gets NULL at write time, because whether it belongs to
    the streak is exactly what the reconciler decides.
    """
    if state != "OPEN" or leader is None:
        return None
    prior = (
        SUPABASE.table(TARGET_TABLE)
        .select("pin_leader_strike,held_for_cycles")
        .eq("symbol", symbol).eq("expiry_date", expiry_date)
        .eq("session_gate_state", "OPEN")
        .lt("ts", ts_iso)
        .order("ts", desc=True)
        .limit(1)
        .execute()
    )
    rows = _rows(prior)
    if not rows:
        return 1
    prev = rows[0]
    if prev.get("pin_leader_strike") is not None and float(prev["pin_leader_strike"]) == float(leader):
        return int(prev.get("held_for_cycles") or 0) + 1
    return 1


# ---------------------------------------------------------------- row assembly
def build_row(leg: dict[str, Any], calendar_healthy: bool) -> dict[str, Any]:
    symbol = leg["symbol"]
    expiry_date = leg["expiry_date"]
    run_id = leg["run_id"]
    ts_iso = leg["ts"]
    ist_day = _ist_date(ts_iso)

    rank_rows = fetch_rank_rows(run_id, symbol, expiry_date)
    derived = derive_rank_fields(rank_rows)
    conc = fetch_concentration(run_id, symbol, expiry_date) or {}
    mp = fetch_max_pain(run_id, symbol, expiry_date) or {}
    pmp = fetch_pin_maxpain(run_id, symbol, expiry_date) or {}
    walls = fetch_walls(run_id, symbol, expiry_date) or {}
    flip3 = clock_match_repriced_flip(symbol, ist_day, expiry_date)
    state, ticks = session_gate(symbol, ist_day, ts_iso)

    t_days = trading_days_to_expiry(ist_day, date.fromisoformat(str(expiry_date)))
    conviction, conviction_reason = conviction_for(
        derived["runnerup_share_ratio"], t_days, calendar_healthy)

    held_for = held_for_cycles_provisional(symbol, expiry_date, ts_iso,
                                           derived["pin_leader_strike"], state)
    pin_state, pin_state_reason = derive_pin_state(
        symbol, held_for, derived["runnerup_share_ratio"], conc.get("hhi_net"),
    )
    # ONE FIELD, ONE REASON. pin_state_reason carries ONLY why pin_state is
    # NULL; conviction_reason carries ONLY why conviction is NULL. They are
    # never joined: a valid pin_state must leave pin_state_reason NULL even on
    # a cycle whose conviction could not be computed, or a reader cannot tell
    # which verdict is missing.

    # Freshness is persisted, never dropped: without it a stale-book cycle is
    # indistinguishable from a fresh one once it is history. The pin/maxpain
    # pair agree in practice; pin_maxpain is preferred and max_pain is the
    # fallback, with the choice explicit rather than by dict-merge order.
    # dict.get(key, default) returns None when the key EXISTS and holds None,
    # so it would silently discard max_pain's value whenever pin_maxpain had a
    # NULL there. Explicit is-not-None instead.
    is_fresh = pmp.get("is_fresh") if pmp.get("is_fresh") is not None else mp.get("is_fresh")
    age_min = (pmp.get("snapshot_age_min") if pmp.get("snapshot_age_min") is not None
               else mp.get("snapshot_age_min"))

    return {
        "symbol": symbol,
        "expiry_date": expiry_date,
        "ts": ts_iso,
        "run_id": run_id,
        "session_gate_state": state,
        "session_gate_ticks": ticks,
        "chain_ts": fetch_chain_ts(run_id, symbol),
        "dte": leg.get("dte"),
        "spot": leg.get("spot"),
        "atm_iv": fetch_atm_iv(run_id, symbol, expiry_date),
        "net_gex": leg.get("net_gex"),
        "gamma_regime": leg.get("regime"),
        "flip_level": leg.get("flip_level"),
        "repriced_flip_level": flip3["repriced_flip_level"],
        "repriced_flip_ts": flip3["repriced_flip_ts"],
        "repriced_flip_source": flip3["repriced_flip_source"],
        "pin_leader_strike": derived["pin_leader_strike"],
        "gamma_at_pin": derived["gamma_at_pin"],
        "runnerup_share_ratio": derived["runnerup_share_ratio"],
        "top5_share": derived["top5_share"],
        "top5_share_n_ranks": derived["top5_share_n_ranks"],
        "conc_top1_share": conc.get("hhi_net"),
        "conc_top1_share_call": conc.get("hhi_call"),
        "conc_top1_share_put": conc.get("hhi_put"),
        "conc_hhi": derived["conc_hhi"],
        "max_pain_strike": mp.get("max_pain_strike"),
        "pin_state": pin_state,
        "pin_state_reason": pin_state_reason,
        "held_for_cycles": held_for,
        "conviction": conviction,
        "conviction_reason": conviction_reason,
        "call_wall_strike": walls.get("call_wall"),
        "put_wall_strike": walls.get("put_wall"),
        "is_fresh": is_fresh,
        "snapshot_age_min": age_min,
        "writer": WRITER,
        "writer_version": WRITER_VERSION,
    }


# ---------------------------------------------------------------- main
def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: python {WRITER} <run_id>", file=sys.stderr)
        return 2
    run_id = sys.argv[1].strip()

    legs = fetch_legs(run_id)
    if not legs:
        log = ExecutionLog(script_name=WRITER, expected_writes={TARGET_TABLE: 0},
                           notes=f"run_id={run_id}",
                           run_id=run_id, product_relation="gex_cycle_history")  # S90_R07_LEDGER
        return log.exit_with_reason(
            "SKIPPED_NO_INPUT", exit_code=0,
            error_message=f"no gamma_metrics rows for run_id={run_id}")

    # EXACT contract, computed BEFORE the first row is built.
    # _compute_contract_met tests `actual < expected`, so a floor of 1 would
    # pass on 1 row and on 163 -- indistinguishable (Rule 0 clause 1).
    pairs = sorted({(l["symbol"], str(l["expiry_date"])) for l in legs})
    n_expected = len(pairs)

    log = ExecutionLog(
        script_name=WRITER,
        expected_writes={TARGET_TABLE: n_expected},
        symbol=legs[0]["symbol"] if len({l["symbol"] for l in legs}) == 1 else None,
        notes=f"run_id={run_id} legs={n_expected}",
        run_id=run_id, product_relation="gex_cycle_history",  # S90_R07_LEDGER
    )

    # Calendar health, once per run: previous_trading_day reports provenance,
    # so a fail-open is DETECTABLE here even though is_trading_day cannot
    # report it. Used to NULL conviction rather than compute it off a calendar
    # that is not answering.
    run_ist_day = _ist_date(legs[0]["ts"])
    try:
        _, provenance = previous_trading_day(run_ist_day.isoformat())
        calendar_healthy = not str(provenance).startswith("fail-open")
    except Exception:
        calendar_healthy = False

    # S90_ENH133_WIRE: bounded retry on statement timeout (57014) only. S90 first live run:
    # NIFTY build_row hit 57014 on a cold view read and passed on the next attempt.
    rows, last_err, attempts = None, None, 0
    for attempts in range(1, 4):
        try:
            rows = [build_row(leg, calendar_healthy) for leg in legs]
            break
        except Exception as e:
            last_err = e
            if "57014" not in str(e):
                break
            time.sleep(3)
    if rows is None:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"build_row failed after {attempts} attempt(s): {last_err}")

    if len(rows) != n_expected:
        return log.exit_with_reason(
            "DATA_ERROR", exit_code=1,
            error_message=f"built {len(rows)} rows for {n_expected} legs")

    try:
        SUPABASE.table(TARGET_TABLE).upsert(
            rows, on_conflict="symbol,expiry_date,ts"
        ).execute()
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"upsert failed: {e}")

    log.record_write(TARGET_TABLE, len(rows))

    print("=" * 72)
    print(f"MERDIAN - {WRITER}")
    print("=" * 72)
    print(f"run_id={run_id}")
    print(f"legs={n_expected}  rows_written={len(rows)}")
    print(f"calendar_healthy={calendar_healthy}")
    for r in rows:
        print(f"  {r['symbol']:7s} {r['expiry_date']}  gate={r['session_gate_state']:8s} "
              f"ticks={r['session_gate_ticks']}  leader={r['pin_leader_strike']} "
              f"held_for={r['held_for_cycles']}  pin_state={r['pin_state']} "
              f"conviction={r['conviction']}")
    print("=" * 72)
    return log.complete()


if __name__ == "__main__":
    sys.exit(main())
