"""
replay.replay_build_momentum_features — Replay mirror of build_momentum_features_local.py.

Differences from build_momentum_features_local.py:
  1. Reads market_spot_snapshots_replay, gamma_metrics_replay, momentum_snapshots_replay.
  2. Reads market_breadth_intraday LIVE (immutable past data — same justification as 
     OI lift from option_chain_snapshots; not in 10 _replay tables by design).
  3. Writes momentum_snapshots_replay.
  4. cycle_ts comes from --replay-ts CLI arg, NOT "latest gamma_metrics".
  5. Spot lookbacks (t-5m/15m/30m/60m) use 5-min boundary granularity in replay 
     (live uses 1-min). Returns may differ slightly in timing — known property.
  6. CLI uses argparse (--replay-ts, --symbol; no --run-id, momentum doesn't take one in live).

Live impact: ZERO writes to live. READS from market_breadth_intraday (immutable past).

Author: Session 24 (2026-05-09)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from postgrest.exceptions import APIError
from supabase import Client, create_client

from replay.replay_clock import parse_replay_ts, replay_today_ist
from replay.replay_execution_log import ExecutionLog


def _load_env() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url:
        raise RuntimeError("Missing SUPABASE_URL")
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


SUPABASE: Client = _load_env()


def _rows(result: Any) -> List[Dict[str, Any]]:
    if result is None:
        return []
    data = getattr(result, "data", None)
    if data is None:
        return []
    return data if isinstance(data, list) else []


def parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        s = str(value).strip().replace("Z", "+00:00").replace(" ", "T")
        if len(s) >= 3 and s[-3] in '+-' and ':' not in s[-3:]:
            s = s + ':00'
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def supabase_select(table_name, columns, filters=None, order_by=None, desc=False, limit=None):
    query = SUPABASE.table(table_name).select(columns)
    if filters:
        for k, v in filters.items():
            query = query.eq(k, v)
    if order_by:
        query = query.order(order_by, desc=desc)
    if limit is not None:
        query = query.limit(limit)
    return _rows(query.execute())


# ============================================================================
# REPLAY: read replay tables for spot/gamma/momentum, live for breadth
# ============================================================================

def get_spot_at_or_before(symbol: str, ts: datetime) -> Optional[Dict[str, Any]]:
    """REPLAY: read market_spot_snapshots_replay; pick latest at-or-before ts."""
    rows = supabase_select(
        "market_spot_snapshots_replay",
        "symbol, ts, spot",
        filters={"symbol": symbol},
        order_by="ts",
        desc=True,
        limit=200,
    )
    for row in rows:
        row_ts = parse_ts(row.get("ts"))
        if row_ts is not None and row_ts <= ts:
            return row
    return None


def get_latest_gamma_rows_replay(symbol: str, ts: datetime, limit: int = 20) -> List[Dict[str, Any]]:
    """REPLAY: read gamma_metrics_replay at-or-before ts."""
    rows = supabase_select(
        "gamma_metrics_replay",
        "symbol, ts, straddle_atm",
        filters={"symbol": symbol},
        order_by="ts",
        desc=True,
        limit=limit + 5,
    )
    out = []
    for row in rows:
        row_ts = parse_ts(row.get("ts"))
        if row_ts is not None and row_ts <= ts:
            out.append(row)
        if len(out) >= limit:
            break
    return out


def get_latest_breadth_rows(replay_date_str: str, ts: datetime, limit: int = 2) -> List[Dict[str, Any]]:
    """REPLAY: read live market_breadth_intraday for replay date (immutable past data)."""
    try:
        result = (
            SUPABASE.table("market_breadth_intraday")
            .select("ts, breadth_score, advances, declines")
            .gte("ts", f"{replay_date_str}T00:00:00Z")
            .lte("ts", f"{replay_date_str}T23:59:59Z")
            .order("ts", desc=True)
            .limit(500)
            .execute()
        )
        rows = _rows(result)
    except Exception:
        return []
    out = []
    for row in rows:
        row_ts = parse_ts(row.get("ts"))
        if row_ts is not None and row_ts <= ts:
            out.append(row)
        if len(out) >= limit:
            break
    return out


def get_latest_momentum_rows_replay(symbol: str, ts: datetime, limit: int = 50) -> List[Dict[str, Any]]:
    """REPLAY: read momentum_snapshots_replay at-or-before ts."""
    rows = supabase_select(
        "momentum_snapshots_replay",
        "symbol, ts, session_vwap",
        filters={"symbol": symbol},
        order_by="ts",
        desc=True,
        limit=limit + 5,
    )
    out = []
    for row in rows:
        row_ts = parse_ts(row.get("ts"))
        if row_ts is not None and row_ts < ts:
            out.append(row)
        if len(out) >= limit:
            break
    return out


def find_spot_before(symbol: str, before_ts: datetime, minutes_back: int) -> Optional[float]:
    """REPLAY: read market_spot_snapshots_replay, find row at/before (before_ts - minutes_back)."""
    rows = supabase_select(
        "market_spot_snapshots_replay",
        "symbol, ts, spot",
        filters={"symbol": symbol},
        order_by="ts",
        desc=True,
        limit=max(200, minutes_back * 2 + 10),
    )
    cutoff = before_ts.timestamp() - (minutes_back * 60)
    best_ts = None
    best_spot = None
    for row in rows:
        ts = parse_ts(row.get("ts"))
        spot = to_float(row.get("spot"))
        if ts is None or spot is None:
            continue
        t = ts.timestamp()
        if t <= cutoff:
            if best_ts is None or t > best_ts:
                best_ts = t
                best_spot = spot
    return best_spot


def get_session_open_spot(symbol: str, current_ts: datetime) -> Optional[float]:
    rows = supabase_select(
        "market_spot_snapshots_replay",
        "symbol, ts, spot",
        filters={"symbol": symbol},
        order_by="ts",
        desc=False,
        limit=500,
    )
    current_date = current_ts.astimezone(timezone.utc).date()
    for row in rows:
        ts = parse_ts(row.get("ts"))
        spot = to_float(row.get("spot"))
        if ts is None or spot is None:
            continue
        if ts.astimezone(timezone.utc).date() != current_date:
            continue
        hh = ts.astimezone(timezone.utc).hour
        mm = ts.astimezone(timezone.utc).minute
        if (hh > 3) or (hh == 3 and mm >= 35):
            return spot
    return None


def compute_return(curr, prev):
    if curr is None or prev is None or prev == 0:
        return None
    return (curr - prev) / prev


def compute_straddle_metrics(symbol: str, ts: datetime) -> Tuple[Optional[float], Optional[float]]:
    gamma_rows = get_latest_gamma_rows_replay(symbol, ts, limit=20)
    if not gamma_rows:
        return None, None
    current = to_float(gamma_rows[0].get("straddle_atm"))
    previous = None
    for row in gamma_rows[1:]:
        val = to_float(row.get("straddle_atm"))
        if val is not None:
            previous = val
            break
    if current is None:
        return None, None
    change = None if previous is None else (current - previous)
    return current, change


def compute_session_vwap(symbol: str, ts: datetime, current_straddle: Optional[float]) -> Optional[float]:
    rows = get_latest_momentum_rows_replay(symbol, ts, limit=1)
    prev_vwap = None
    if rows:
        prev_vwap = to_float(rows[0].get("session_vwap"))
    if current_straddle is None:
        return prev_vwap
    if prev_vwap is None:
        return current_straddle
    return ((prev_vwap * 8.0) + current_straddle) / 9.0


def compute_price_vs_vwap_pct(current_straddle, session_vwap):
    if current_straddle is None or session_vwap is None or session_vwap == 0:
        return None
    return ((current_straddle - session_vwap) / session_vwap) * 100.0


def compute_vwap_slope(current_vwap, prev_vwap):
    if current_vwap is None or prev_vwap is None:
        return None
    return current_vwap - prev_vwap


def compute_breadth_deltas(replay_date_str: str, ts: datetime) -> Tuple[Optional[float], Optional[int]]:
    rows = get_latest_breadth_rows(replay_date_str, ts, limit=2)
    if not rows:
        return None, None
    current_score = to_float(rows[0].get("breadth_score"))
    current_adv = rows[0].get("advances")
    current_dec = rows[0].get("declines")
    prev_score = None
    prev_adv = None
    prev_dec = None
    if len(rows) > 1:
        prev_score = to_float(rows[1].get("breadth_score"))
        prev_adv = rows[1].get("advances")
        prev_dec = rows[1].get("declines")
    score_change = None
    if current_score is not None and prev_score is not None:
        score_change = current_score - prev_score
    ad_delta = None
    if current_adv is not None and current_dec is not None:
        current_net = int(current_adv) - int(current_dec)
        if prev_adv is not None and prev_dec is not None:
            prev_net = int(prev_adv) - int(prev_dec)
            ad_delta = current_net - prev_net
        else:
            ad_delta = current_net
    return score_change, ad_delta


def derive_momentum_regime(r5, r15, r30, r60, rsess, pvw):
    score = 0.0
    used = 0
    for val, weight in [(r5, 1.0), (r15, 1.5), (r30, 2.0), (r60, 2.0), (rsess, 2.5)]:
        if val is not None:
            score += val * weight
            used += 1
    if pvw is not None:
        score += (pvw / 100.0) * 1.5
        used += 1
    if used == 0:
        return None
    if score > 0.0015:
        return "UP"
    if score < -0.0015:
        return "DOWN"
    return "NEUTRAL"


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="replay_build_momentum_features")
    parser.add_argument("--replay-ts", required=True)
    parser.add_argument("--symbol", required=True, choices=["NIFTY", "SENSEX"])
    return parser.parse_args(argv)


def main() -> int:
    try:
        args = parse_args(sys.argv[1:])
    except SystemExit:
        raise

    try:
        replay_ts = parse_replay_ts(args.replay_ts)
    except ValueError as e:
        print(f"[ERROR] Invalid --replay-ts: {e}", file=sys.stderr)
        return 2

    symbol = args.symbol.upper()
    replay_date = replay_today_ist(replay_ts)
    cycle_ts = replay_ts

    log = ExecutionLog(
        script_name="replay_build_momentum_features.py",
        expected_writes={"momentum_snapshots_replay": 1},
        symbol=symbol,
        notes=f"momentum replay_ts={args.replay_ts}",
    )

    print("=" * 72)
    print("MERDIAN REPLAY - replay_build_momentum_features")
    print("=" * 72)
    print(f"replay_ts={args.replay_ts}")
    print(f"replay_date={replay_date}")
    print(f"symbol={symbol}")

    try:
        spot_row = get_spot_at_or_before(symbol, cycle_ts)
        if spot_row is None:
            return log.exit_with_reason(
                "SKIPPED_NO_INPUT", 1,
                error_message=f"No market_spot_snapshots_replay rows for {symbol} at/before {cycle_ts}"
            )

        current_spot = to_float(spot_row.get("spot"))

        spot_5m = find_spot_before(symbol, cycle_ts, 5)
        spot_15m = find_spot_before(symbol, cycle_ts, 15)
        spot_30m = find_spot_before(symbol, cycle_ts, 30)
        spot_60m = find_spot_before(symbol, cycle_ts, 60)
        open_spot = get_session_open_spot(symbol, cycle_ts)

        ret_5m = compute_return(current_spot, spot_5m)
        ret_15m = compute_return(current_spot, spot_15m)
        ret_30m = compute_return(current_spot, spot_30m)
        ret_60m = compute_return(current_spot, spot_60m)
        ret_session = compute_return(current_spot, open_spot)

        current_straddle, atm_straddle_change = compute_straddle_metrics(symbol, cycle_ts)

        prior_rows = get_latest_momentum_rows_replay(symbol, cycle_ts, limit=1)
        prev_session_vwap = None
        if prior_rows:
            prev_session_vwap = to_float(prior_rows[0].get("session_vwap"))

        session_vwap = compute_session_vwap(symbol, cycle_ts, current_straddle)
        price_vs_vwap_pct = compute_price_vs_vwap_pct(current_straddle, session_vwap)
        vwap_slope = compute_vwap_slope(session_vwap, prev_session_vwap)

        breadth_score_change, ad_delta = compute_breadth_deltas(replay_date.isoformat(), cycle_ts)

        momentum_regime = derive_momentum_regime(
            ret_5m, ret_15m, ret_30m, ret_60m, ret_session, price_vs_vwap_pct
        )

        row = {
            "symbol": symbol,
            "ts": cycle_ts.isoformat(),
            "ret_5m": ret_5m,
            "ret_15m": ret_15m,
            "ret_30m": ret_30m,
            "ret_60m": ret_60m,
            "ret_session": ret_session,
            "breadth_score_change": breadth_score_change,
            "ad_delta": ad_delta,
            "source": "replay_momentum_v1",
            "price_vs_vwap_pct": price_vs_vwap_pct,
            "vwap_slope": vwap_slope,
            "atm_straddle_change": atm_straddle_change,
            "session_vwap": session_vwap,
            "momentum_regime": momentum_regime,
        }

        print(f"current_spot={current_spot}")
        print(f"ret_5m={ret_5m} ret_15m={ret_15m} ret_30m={ret_30m} ret_60m={ret_60m} ret_session={ret_session}")
        print(f"momentum_regime={momentum_regime}")
        print(f"price_vs_vwap_pct={price_vs_vwap_pct} session_vwap={session_vwap}")

        try:
            SUPABASE.table("momentum_snapshots_replay").upsert(row, on_conflict="symbol,ts").execute()
        except APIError as e:
            msg = str(e)
            if "uq_momentum" in msg or "duplicate key" in msg.lower():
                print("Already exists for (symbol, ts) — treating as success.")
            else:
                return log.exit_with_reason("DATA_ERROR", 1, error_message=f"momentum upsert APIError: {e}")
        except Exception as e:
            return log.exit_with_reason("DATA_ERROR", 1, error_message=f"momentum upsert exception: {e}")

    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"build_row failed: {e}")

    log.record_write("momentum_snapshots_replay", 1)
    return log.complete()


if __name__ == "__main__":
    sys.exit(main())