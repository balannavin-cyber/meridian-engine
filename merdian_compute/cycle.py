"""merdian_compute.cycle — ENH-133 cycle-history helpers: IST date of a PostgREST timestamp, rank-ladder
fields, boost(T) and Stage-1 conviction.

S101_MERDIAN_COMPUTE: every definition below was moved byte-identical from
write_gex_cycle_history_local.py at 7b91d1a (S101, scope §1.3). Pure: no I/O, no env, no network, no DB.
The writer re-imports each name, so production behaviour is unchanged.
Any edit here changes the live writer: golden replay + offline suite first.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional


IST = timezone(timedelta(hours=5, minutes=30))


# D-5b / D-5c. T is in TRADING days; cap and floor are the ruled values.
BOOST_COEFF = 2.53


BOOST_CAP = 3.70


T_FLOOR = 0.47


_FRAC = re.compile(r"\.(\d{1,6})(?=[+-]\d{2}:?\d{2}$|Z$|$)")


def _norm_frac(ts_iso: str) -> str:
    """Pad the microsecond fraction to 6 digits.

    PostgREST trims trailing zeros, so a timestamp whose microseconds end in 0
    arrives with 1, 2, 4 or 5 digits ('2026-10-07T03:30:07.61356+00:00').
    Python 3.10's fromisoformat accepts a fraction of EXACTLY 3 or 6 digits, or
    none at all, and raises ValueError on every other width; 3.11+ is
    permissive. The box is 3.10, so an unpadded fraction killed ~1 cycle in 10
    and that cycle's row is unrecoverable (ADR-030 D2: the table accumulates
    forward and is never backfilled).

    The regex is deliberately identical to check_contracts_shadow._FRAC. The
    repo holds ~40 independent copies of this padding; one shared core/ helper
    is the right fix and is NOT this change (see TS-PARSE findings, S91).
    """
    return _FRAC.sub(lambda m: "." + m.group(1).ljust(6, "0"), ts_iso)


def _ist_date(ts_iso: str) -> date:
    """IST calendar date of a true timestamptz string.

    option_chain_snapshots / gamma_metrics / market_spot_snapshots all store
    true timestamptz (verified S89) -- this is NOT the hist_spot_bars_5m
    IST-as-UTC case, so astimezone is correct here and replace(tzinfo=None)
    would be wrong.
    """
    return datetime.fromisoformat(_norm_frac(ts_iso.replace("Z", "+00:00"))).astimezone(IST).date()


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


# S101_C4_PIN_PATH: the pin path's calendar count and carry-forward, cut from
# write_gex_cycle_history_local.py (S101 C4); the writer keeps the reads and passes them in.
from typing import Callable  # noqa: E402


def trading_days_between(run_date: date, expiry: date, is_open: Callable[[str], bool]) -> int:
    """Open days strictly after run_date, up to and including expiry. `is_open(iso_date)` is the
    caller's calendar; production passes core.trading_calendar_gate.is_trading_day, which FAILS
    OPEN (a date with no calendar row counts as open).
    """
    n = 0
    d = run_date + timedelta(days=1)
    while d <= expiry:
        if is_open(d.isoformat()):
            n += 1
        d += timedelta(days=1)
    return n


def held_for_cycles_next(state: str, leader: Optional[float],
                         prior_rows: list[dict[str, Any]]) -> Optional[int]:
    """Carry-forward of held_for_cycles. prior_rows = the latest EARLIER row of the same
    (symbol, expiry_date) with session_gate_state OPEN, as a list of at most one dict with
    pin_leader_strike and held_for_cycles. None unless state is OPEN and a leader exists.
    """
    if state != "OPEN" or leader is None:
        return None
    rows = prior_rows
    if not rows:
        return 1
    prev = rows[0]
    if prev.get("pin_leader_strike") is not None and float(prev["pin_leader_strike"]) == float(leader):
        return int(prev.get("held_for_cycles") or 0) + 1
    return 1
