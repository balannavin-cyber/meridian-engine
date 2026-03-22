from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


# ============================================================
# MERDIAN - build_momentum_features_local.py
# Full-file replacement
#
# Safe against current cloud Supabase schema for momentum_snapshots.
#
# This version computes:
#   - ret_5m
#   - ret_15m
#   - ret_30m
#   - ret_60m
#   - ret_session
#   - atm_straddle_change
#   - price_vs_vwap_pct
#   - vwap_slope
#
# It inserts ONLY columns that already exist in your live table:
#   symbol, ts, ret_5m, ret_15m, ret_30m, ret_60m, ret_session,
#   price_vs_vwap_pct, vwap_slope, atm_straddle_change, source
#
# No 'raw', no 'session_vwap', no 'momentum_regime' insert.
# ============================================================


# -----------------------------
# Environment / Supabase client
# -----------------------------
def _load_env() -> Client:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL not found in environment or .env")

    if not service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not found in environment or .env")

    if not supabase_url.startswith("http://") and not supabase_url.startswith("https://"):
        raise RuntimeError(
            f"SUPABASE_URL is invalid: {supabase_url!r}. It must start with https://"
        )

    return create_client(supabase_url, service_role_key)


SUPABASE: Client = _load_env()


# -----------------------------
# Helpers
# -----------------------------
def _rows(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    data = getattr(result, "data", None)
    if data is None:
        return []
    return data if isinstance(data, list) else []


def to_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def as_iso_ts(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.isoformat()
    return datetime.now(timezone.utc).isoformat()


def parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported timestamp value: {value!r}")


def latest_rows(
    table_name: str,
    symbol: str | None = None,
    limit: int = 1,
    order_col: str = "ts",
) -> list[dict[str, Any]]:
    query = SUPABASE.table(table_name).select("*")

    if symbol is not None:
        query = query.eq("symbol", symbol)

    result = query.order(order_col, desc=True).limit(limit).execute()
    return _rows(result)


def latest_row(table_name: str, symbol: str | None = None, order_col: str = "ts") -> dict[str, Any] | None:
    rows = latest_rows(table_name, symbol=symbol, limit=1, order_col=order_col)
    return rows[0] if rows else None


def fetch_latest_before(
    table_name: str,
    symbol: str,
    cutoff_ts: datetime,
    order_col: str = "ts",
) -> dict[str, Any] | None:
    result = (
        SUPABASE.table(table_name)
        .select("*")
        .eq("symbol", symbol)
        .lt(order_col, cutoff_ts.isoformat())
        .order(order_col, desc=True)
        .limit(1)
        .execute()
    )
    rows = _rows(result)
    return rows[0] if rows else None


def fetch_latest_at_or_before(
    table_name: str,
    symbol: str,
    cutoff_ts: datetime,
    order_col: str = "ts",
) -> dict[str, Any] | None:
    result = (
        SUPABASE.table(table_name)
        .select("*")
        .eq("symbol", symbol)
        .lte(order_col, cutoff_ts.isoformat())
        .order(order_col, desc=True)
        .limit(1)
        .execute()
    )
    rows = _rows(result)
    return rows[0] if rows else None


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous


def session_day_bounds(ts: datetime) -> tuple[str, str]:
    day = ts.date().isoformat()
    return (f"{day}T00:00:00+00:00", f"{day}T23:59:59.999999+00:00")


# -----------------------------
# Source fetch
# -----------------------------
def latest_spot(symbol: str) -> dict[str, Any]:
    row = latest_row("market_spot_snapshots", symbol=symbol, order_col="ts")
    if not row:
        raise RuntimeError(f"No market_spot_snapshots row found for symbol={symbol}")
    return row


def latest_gamma(symbol: str) -> dict[str, Any]:
    row = latest_row("gamma_metrics", symbol=symbol, order_col="ts")
    if not row:
        raise RuntimeError(f"No gamma_metrics row found for symbol={symbol}")
    return row


def fetch_session_open_spot(symbol: str, current_ts: datetime) -> dict[str, Any] | None:
    start_ts, end_ts = session_day_bounds(current_ts)

    result = (
        SUPABASE.table("market_spot_snapshots")
        .select("*")
        .eq("symbol", symbol)
        .gte("ts", start_ts)
        .lte("ts", end_ts)
        .order("ts", desc=False)
        .limit(1)
        .execute()
    )
    rows = _rows(result)
    return rows[0] if rows else None


def fetch_today_gamma_rows(symbol: str, current_ts: datetime) -> list[dict[str, Any]]:
    start_ts, _ = session_day_bounds(current_ts)

    result = (
        SUPABASE.table("gamma_metrics")
        .select("ts,straddle_atm")
        .eq("symbol", symbol)
        .gte("ts", start_ts)
        .lt("ts", current_ts.isoformat())
        .order("ts", desc=False)
        .execute()
    )
    return _rows(result)


# -----------------------------
# Computation
# -----------------------------
def compute_returns(symbol: str, current_ts: datetime, current_spot: float) -> dict[str, float | None]:
    lookbacks = {
        "ret_5m": 5,
        "ret_15m": 15,
        "ret_30m": 30,
        "ret_60m": 60,
    }

    out: dict[str, float | None] = {}

    for key, minutes_back in lookbacks.items():
        cutoff = datetime.fromtimestamp(
            current_ts.timestamp() - minutes_back * 60,
            tz=timezone.utc,
        )
        prev_row = fetch_latest_at_or_before("market_spot_snapshots", symbol, cutoff, order_col="ts")
        prev_spot = None
        if prev_row:
            prev_spot = (
                to_float(prev_row.get("spot"))
                or to_float(prev_row.get("ltp"))
                or to_float(prev_row.get("price"))
            )

        out[key] = pct_change(current_spot, prev_spot)

    session_open_row = fetch_session_open_spot(symbol, current_ts)
    session_open = None
    if session_open_row:
        session_open = (
            to_float(session_open_row.get("spot"))
            or to_float(session_open_row.get("ltp"))
            or to_float(session_open_row.get("price"))
        )

    out["ret_session"] = pct_change(current_spot, session_open)
    return out


def compute_straddle_metrics(symbol: str, current_ts: datetime, current_straddle: float | None) -> dict[str, float | None]:
    previous_gamma = fetch_latest_before("gamma_metrics", symbol, current_ts, order_col="ts")
    previous_straddle = to_float(previous_gamma.get("straddle_atm")) if previous_gamma else None

    atm_straddle_change = None
    if current_straddle is not None and previous_straddle is not None:
        atm_straddle_change = current_straddle - previous_straddle

    today_gamma_rows = fetch_today_gamma_rows(symbol, current_ts)

    historical_straddles: list[float] = []
    for row in today_gamma_rows:
        val = to_float(row.get("straddle_atm"))
        if val is not None:
            historical_straddles.append(val)

    if current_straddle is not None:
        full_series = historical_straddles + [current_straddle]
    else:
        full_series = historical_straddles

    session_vwap = None
    if full_series:
        session_vwap = sum(full_series) / len(full_series)

    price_vs_vwap_pct = None
    if current_straddle is not None and session_vwap is not None and session_vwap != 0:
        price_vs_vwap_pct = ((current_straddle - session_vwap) / session_vwap) * 100.0

    previous_session_vwap = None
    if historical_straddles:
        previous_session_vwap = sum(historical_straddles) / len(historical_straddles)

    vwap_slope = None
    if session_vwap is not None and previous_session_vwap is not None:
        vwap_slope = session_vwap - previous_session_vwap

    return {
        "atm_straddle_change": atm_straddle_change,
        "price_vs_vwap_pct": price_vs_vwap_pct,
        "vwap_slope": vwap_slope,
    }


def build(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper()

    spot_row = latest_spot(symbol)
    gamma_row = latest_gamma(symbol)

    current_ts = parse_ts(spot_row.get("ts") or spot_row.get("created_at"))
    current_spot = (
        to_float(spot_row.get("spot"))
        or to_float(spot_row.get("ltp"))
        or to_float(spot_row.get("price"))
    )
    if current_spot is None:
        raise RuntimeError(f"Could not derive current spot for symbol={symbol}")

    current_straddle = to_float(gamma_row.get("straddle_atm"))

    returns = compute_returns(symbol, current_ts, current_spot)
    straddle_metrics = compute_straddle_metrics(symbol, current_ts, current_straddle)

    row = {
        "symbol": symbol,
        "ts": current_ts.isoformat(),
        "ret_5m": returns.get("ret_5m"),
        "ret_15m": returns.get("ret_15m"),
        "ret_30m": returns.get("ret_30m"),
        "ret_60m": returns.get("ret_60m"),
        "ret_session": returns.get("ret_session"),
        "price_vs_vwap_pct": straddle_metrics.get("price_vs_vwap_pct"),
        "vwap_slope": straddle_metrics.get("vwap_slope"),
        "atm_straddle_change": straddle_metrics.get("atm_straddle_change"),
        "source": "momentum_engine_v4.7_vwap_straddle_fixed",
    }

    return row


def insert_momentum(row: dict[str, Any]) -> None:
    SUPABASE.table("momentum_snapshots").insert(row).execute()


# -----------------------------
# CLI
# -----------------------------
def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python build_momentum_features_local.py <symbol>")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    row = build(symbol)
    insert_momentum(row)

    print("Momentum snapshot insert complete.")
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


if __name__ == "__main__":
    main()