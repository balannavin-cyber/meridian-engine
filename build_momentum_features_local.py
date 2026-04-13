from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from postgrest.exceptions import APIError
from supabase import Client, create_client


# ============================================================
# MERDIAN - build_momentum_features_local.py
# FULL FILE REPLACEMENT
#
# Purpose
#   Build live momentum row for public.momentum_snapshots.
#
# Restart-safe behavior
#   Writes via UPSERT on (symbol, ts) so duplicate timestamp buckets
#   do NOT kill the live runner after manual restart / re-entry.
#
# Reads from
#   public.market_spot_snapshots
#   public.gamma_metrics
#   public.market_breadth_intraday
#   public.momentum_snapshots
#
# Writes to
#   public.momentum_snapshots
#
# Cloud-safe write contract
#   symbol
#   ts
#   ret_5m
#   ret_15m
#   ret_30m
#   ret_60m
#   ret_session
#   breadth_score_change
#   ad_delta
#   source
#   price_vs_vwap_pct
#   vwap_slope
#   atm_straddle_change
#   session_vwap
#   momentum_regime
# ============================================================


def fail(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def load_supabase() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url:
        fail("Missing SUPABASE_URL in environment/.env")
    if not key:
        fail("Missing SUPABASE_SERVICE_ROLE_KEY in environment/.env")

    return create_client(url, key)


SUPABASE = load_supabase()


def supabase_select(
    table_name: str,
    columns: str,
    filters: dict[str, Any] | None = None,
    order_by: str | None = None,
    desc: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    query = SUPABASE.table(table_name).select(columns)

    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)

    if order_by:
        query = query.order(order_by, desc=desc)

    if limit is not None:
        query = query.limit(limit)

    resp = query.execute()
    data = getattr(resp, "data", None) or []
    return data


def get_latest_spot_row(symbol: str) -> dict[str, Any]:
    rows = supabase_select(
        "market_spot_snapshots",
        "symbol, ts, spot",
        filters={"symbol": symbol},
        order_by="ts",
        desc=True,
        limit=1,
    )
    if not rows:
        fail(f"No market_spot_snapshots rows found for {symbol}")
    return rows[0]


def get_latest_gamma_rows(symbol: str, limit: int = 20) -> list[dict[str, Any]]:
    rows = supabase_select(
        "gamma_metrics",
        "symbol, ts, straddle_atm",
        filters={"symbol": symbol},
        order_by="ts",
        desc=True,
        limit=limit,
    )
    return rows


def get_latest_breadth_rows(limit: int = 2) -> list[dict[str, Any]]:
    rows = supabase_select(
        "market_breadth_intraday",
        "ts, breadth_score, advances, declines",
        order_by="ts",
        desc=True,
        limit=limit,
    )
    return rows


def get_latest_momentum_rows(symbol: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = supabase_select(
        "momentum_snapshots",
        "symbol, ts, session_vwap",
        filters={"symbol": symbol},
        order_by="ts",
        desc=True,
        limit=limit,
    )
    return rows


def choose_cycle_ts(symbol: str) -> datetime:
    gamma_rows = get_latest_gamma_rows(symbol, limit=1)
    if gamma_rows:
        ts = parse_ts(gamma_rows[0].get("ts"))
        if ts:
            return ts

    spot_row = get_latest_spot_row(symbol)
    ts = parse_ts(spot_row.get("ts"))
    if ts:
        return ts

    return now_utc()


def find_spot_before(symbol: str, before_ts: datetime, minutes_back: int) -> float | None:
    rows = supabase_select(
        "market_spot_snapshots",
        "symbol, ts, spot",
        filters={"symbol": symbol},
        order_by="ts",
        desc=True,
        limit=max(20, minutes_back + 10),
    )

    cutoff = before_ts.timestamp() - (minutes_back * 60)
    best_ts: float | None = None
    best_spot: float | None = None

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


def get_session_open_spot(symbol: str, current_ts: datetime) -> float | None:
    rows = supabase_select(
        "market_spot_snapshots",
        "symbol, ts, spot",
        filters={"symbol": symbol},
        order_by="ts",
        desc=False,
        limit=500,
    )

    current_date = current_ts.astimezone(timezone.utc).date()
    chosen: float | None = None

    for row in rows:
        ts = parse_ts(row.get("ts"))
        spot = to_float(row.get("spot"))
        if ts is None or spot is None:
            continue
        if ts.astimezone(timezone.utc).date() != current_date:
            continue

        # 09:05 IST ~= 03:35 UTC (accepts pre-open capture from MERDIAN_PreOpen task)
        hh = ts.astimezone(timezone.utc).hour
        mm = ts.astimezone(timezone.utc).minute
        if (hh > 3) or (hh == 3 and mm >= 35):
            chosen = spot
            break

    return chosen


def compute_return(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return (curr - prev) / prev


def compute_straddle_metrics(symbol: str) -> tuple[float | None, float | None]:
    gamma_rows = get_latest_gamma_rows(symbol, limit=20)
    if not gamma_rows:
        return None, None

    current = to_float(gamma_rows[0].get("straddle_atm"))
    previous: float | None = None
    for row in gamma_rows[1:]:
        val = to_float(row.get("straddle_atm"))
        if val is not None:
            previous = val
            break

    if current is None:
        return None, None

    change = None if previous is None else (current - previous)
    return current, change


def compute_session_vwap(symbol: str, current_straddle: float | None) -> float | None:
    rows = get_latest_momentum_rows(symbol, limit=1)
    prev_vwap = None
    if rows:
        prev_vwap = to_float(rows[0].get("session_vwap"))

    if current_straddle is None:
        return prev_vwap

    if prev_vwap is None:
        return current_straddle

    return ((prev_vwap * 8.0) + current_straddle) / 9.0


def compute_price_vs_vwap_pct(current_straddle: float | None, session_vwap: float | None) -> float | None:
    if current_straddle is None or session_vwap is None or session_vwap == 0:
        return None
    return ((current_straddle - session_vwap) / session_vwap) * 100.0


def compute_vwap_slope(current_vwap: float | None, prev_vwap: float | None) -> float | None:
    if current_vwap is None or prev_vwap is None:
        return None
    return current_vwap - prev_vwap


def compute_breadth_deltas() -> tuple[float | None, int | None]:
    rows = get_latest_breadth_rows(limit=2)
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


def derive_momentum_regime(
    ret_5m: float | None,
    ret_15m: float | None,
    ret_30m: float | None,
    ret_60m: float | None,
    ret_session: float | None,
    price_vs_vwap_pct: float | None,
) -> str | None:
    score = 0.0
    used = 0

    for val, weight in [
        (ret_5m, 1.0),
        (ret_15m, 1.5),
        (ret_30m, 2.0),
        (ret_60m, 2.0),
        (ret_session, 2.5),
    ]:
        if val is not None:
            score += val * weight
            used += 1

    if price_vs_vwap_pct is not None:
        score += (price_vs_vwap_pct / 100.0) * 1.5
        used += 1

    if used == 0:
        return None

    if score > 0.0015:
        return "UP"
    if score < -0.0015:
        return "DOWN"
    return "NEUTRAL"


def build_row(symbol: str) -> dict[str, Any]:
    cycle_ts = choose_cycle_ts(symbol)
    spot_row = get_latest_spot_row(symbol)
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

    current_straddle, atm_straddle_change = compute_straddle_metrics(symbol)

    prior_rows = get_latest_momentum_rows(symbol, limit=1)
    prev_session_vwap = None
    if prior_rows:
        prev_session_vwap = to_float(prior_rows[0].get("session_vwap"))

    session_vwap = compute_session_vwap(symbol, current_straddle)
    price_vs_vwap_pct = compute_price_vs_vwap_pct(current_straddle, session_vwap)
    vwap_slope = compute_vwap_slope(session_vwap, prev_session_vwap)

    breadth_score_change, ad_delta = compute_breadth_deltas()

    momentum_regime = derive_momentum_regime(
        ret_5m=ret_5m,
        ret_15m=ret_15m,
        ret_30m=ret_30m,
        ret_60m=ret_60m,
        ret_session=ret_session,
        price_vs_vwap_pct=price_vs_vwap_pct,
    )

    return {
        "symbol": symbol,
        "ts": cycle_ts.isoformat(),
        "ret_5m": ret_5m,
        "ret_15m": ret_15m,
        "ret_30m": ret_30m,
        "ret_60m": ret_60m,
        "ret_session": ret_session,
        "breadth_score_change": breadth_score_change,
        "ad_delta": ad_delta,
        "source": "momentum_engine_v4.7_restart_safe",
        "price_vs_vwap_pct": price_vs_vwap_pct,
        "vwap_slope": vwap_slope,
        "atm_straddle_change": atm_straddle_change,
        "session_vwap": session_vwap,
        "momentum_regime": momentum_regime,
    }


def insert_momentum(row: dict[str, Any]) -> None:
    try:
        (
            SUPABASE
            .table("momentum_snapshots")
            .upsert(row, on_conflict="symbol,ts")
            .execute()
        )
        print("Momentum snapshot upsert complete.")
        print(f"symbol={row.get('symbol')}")
        print(f"ts={row.get('ts')}")
        print(f"ret_5m={row.get('ret_5m')}")
        print(f"ret_15m={row.get('ret_15m')}")
        print(f"ret_30m={row.get('ret_30m')}")
        print(f"ret_60m={row.get('ret_60m')}")
        print(f"ret_session={row.get('ret_session')}")
        print(f"atm_straddle_change={row.get('atm_straddle_change')}")
        print(f"price_vs_vwap_pct={row.get('price_vs_vwap_pct')}")
        print(f"vwap_slope={row.get('vwap_slope')}")
        print(f"momentum_regime={row.get('momentum_regime')}")
    except APIError as e:
        msg = str(e)
        if "uq_momentum_snapshots_symbol_ts" in msg or "duplicate key value violates unique constraint" in msg:
            print("Momentum snapshot already exists for (symbol, ts). Treating as success.")
            print(f"symbol={row.get('symbol')}")
            print(f"ts={row.get('ts')}")
            return
        raise


def main() -> None:
    if len(sys.argv) != 2:
        fail("Usage: python .\\build_momentum_features_local.py <NIFTY|SENSEX>")

    symbol = sys.argv[1].strip().upper()
    if symbol not in {"NIFTY", "SENSEX"}:
        fail("Usage: python .\\build_momentum_features_local.py <NIFTY|SENSEX>")

    row = build_row(symbol)
    insert_momentum(row)


if __name__ == "__main__":
    main()
