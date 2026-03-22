from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from core.dhan_client import DhanClient
from core.supabase_client import SupabaseClient
from gamma_engine_retry_utils import retry_call


UNDERLYING_MAP = {
    "NIFTY": {
        "UnderlyingScrip": 13,
        "UnderlyingSeg": "IDX_I",
    },
    "SENSEX": {
        "UnderlyingScrip": 51,
        "UnderlyingSeg": "IDX_I",
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def extract_option_rows(
    symbol: str,
    expiry_date: str,
    snapshot_ts: str,
    run_id: str,
    spot: float | None,
    option_chain_response: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    data = option_chain_response.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Option chain response missing dict at key 'data'")

    oc = data.get("oc")
    if not isinstance(oc, dict):
        raise RuntimeError("Option chain response missing dict at key data['oc']")

    for strike_key, strike_block in oc.items():
        strike = to_int(strike_key)
        if strike is None:
            continue

        if not isinstance(strike_block, dict):
            continue

        option_key_map = {
            "ce": "CE",
            "pe": "PE",
        }

        for dhan_key, option_type in option_key_map.items():
            option_raw = strike_block.get(dhan_key)
            if not isinstance(option_raw, dict):
                continue

            greeks = option_raw.get("greeks") or {}
            previous_oi = option_raw.get("previous_oi")

            oi = to_int(option_raw.get("oi"))
            oi_change = None
            if oi is not None and previous_oi is not None:
                try:
                    oi_change = int(oi - int(float(previous_oi)))
                except Exception:
                    oi_change = None

            row = {
                "ts": snapshot_ts,
                "symbol": symbol,
                "expiry_date": expiry_date,
                "spot": to_float(spot),
                "strike": strike,
                "option_type": option_type,
                "ltp": to_float(option_raw.get("last_price")),
                "bid": to_float(option_raw.get("top_bid_price")),
                "ask": to_float(option_raw.get("top_ask_price")),
                "oi": oi,
                "oi_change": oi_change,
                "volume": to_int(option_raw.get("volume")),
                "iv": to_float(option_raw.get("implied_volatility")),
                "delta": to_float(greeks.get("delta")),
                "gamma": to_float(greeks.get("gamma")),
                "theta": to_float(greeks.get("theta")),
                "vega": to_float(greeks.get("vega")),
                "raw": option_raw,
                "run_id": run_id,
            }
            rows.append(row)

    return rows


def ingest_symbol(symbol: str) -> None:
    symbol = symbol.upper().strip()
    if symbol not in UNDERLYING_MAP:
        raise RuntimeError(f"Unsupported symbol: {symbol}. Use NIFTY or SENSEX.")

    dhan = DhanClient()
    sb = SupabaseClient()

    underlying = UNDERLYING_MAP[symbol]

    print("=" * 72)
    print("Gamma Engine - Local Python ingest_option_chain")
    print("=" * 72)
    print(f"Symbol: {symbol}")
    print(f"UnderlyingScrip: {underlying['UnderlyingScrip']}")
    print(f"UnderlyingSeg: {underlying['UnderlyingSeg']}")
    print("-" * 72)

    expiry_resp = retry_call(
        lambda: dhan.get_expiry_list(
            underlying_scrip=underlying["UnderlyingScrip"],
            underlying_seg=underlying["UnderlyingSeg"],
        ),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label=f"{symbol} get_expiry_list",
    )

    expiries = expiry_resp.get("data")
    if not isinstance(expiries, list) or not expiries:
        raise RuntimeError(f"No expiries returned for {symbol}: {expiry_resp}")

    expiry_date = str(expiries[0])
    print(f"Selected expiry: {expiry_date}")

    chain_resp = retry_call(
        lambda: dhan.get_option_chain(
            underlying_scrip=underlying["UnderlyingScrip"],
            underlying_seg=underlying["UnderlyingSeg"],
            expiry=expiry_date,
        ),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label=f"{symbol} get_option_chain",
    )

    data = chain_resp.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"Option chain response missing data dict: {chain_resp}")

    spot = to_float(data.get("last_price"))
    if spot is None:
        spot = to_float(data.get("spot_price"))

    snapshot_ts = utc_now_iso()
    run_id = str(uuid.uuid4())

    rows = extract_option_rows(
        symbol=symbol,
        expiry_date=expiry_date,
        snapshot_ts=snapshot_ts,
        run_id=run_id,
        spot=spot,
        option_chain_response=chain_resp,
    )

    if not rows:
        raise RuntimeError(f"No option rows extracted for {symbol}")

    print(f"Extracted rows: {len(rows)}")
    print(f"Run ID: {run_id}")
    print(f"Spot: {spot}")
    print("-" * 72)
    print("Writing rows to Supabase...")

    inserted = retry_call(
        lambda: sb.insert("option_chain_snapshots", rows),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label=f"{symbol} insert option_chain_snapshots",
    )

    inserted_count = len(inserted) if isinstance(inserted, list) else 0
    print(f"Inserted rows returned by Supabase: {inserted_count}")
    print("INGEST OPTION CHAIN COMPLETED")


def main() -> None:
    if len(sys.argv) < 2:
        raise RuntimeError("Usage: python .\\ingest_option_chain_local.py NIFTY")

    symbol = sys.argv[1]
    ingest_symbol(symbol)


if __name__ == "__main__":
    main()