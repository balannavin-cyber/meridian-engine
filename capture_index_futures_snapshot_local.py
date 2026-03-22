from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# ============================================================================
# MERDIAN - Capture Index Futures Snapshot
# ----------------------------------------------------------------------------
# Purpose:
#   Capture latest front-month NIFTY and SENSEX futures prices from Dhan,
#   compute basis vs latest spot, and write to public.index_futures_snapshots.
#
# Runtime hardening added:
#   - Retry on Dhan 429 rate limit
#   - Short exponential backoff
#   - Clean failure after retries
#
# IMPORTANT:
#   This script writes only the minimal validated canonical columns:
#     ts, symbol, futures_price, basis, basis_pct
# ============================================================================


if load_dotenv is not None:
    load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "").strip()
DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN", "").strip()

DHAN_LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 4
INITIAL_BACKOFF_SECONDS = 2.0

DEBUG_DIR = Path(r"C:\gammaenginepython\debug_outputs")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

FUTURES_CONTRACTS = {
    "NIFTY": {
        "exchange_segment": "NSE_FNO",
        "security_id": 51714,
    },
    "SENSEX": {
        "exchange_segment": "BSE_FNO",
        "security_id": 825565,
    },
}


class ConfigError(RuntimeError):
    pass


class SupabaseError(RuntimeError):
    pass


class DhanError(RuntimeError):
    pass


def require_env(name: str, value: str) -> str:
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def print_header() -> None:
    print("=" * 72)
    print("MERDIAN - Capture Index Futures Snapshot")
    print("=" * 72)


def get_supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def supabase_get(table: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.get(
        url,
        headers=get_supabase_headers(),
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise SupabaseError(
            f"GET {table} failed | status={response.status_code} | body={response.text}"
        )
    data = response.json()
    if not isinstance(data, list):
        raise SupabaseError(f"GET {table} returned unexpected payload: {data}")
    return data


def supabase_insert_rows(table: str, rows: List[Dict[str, Any]]) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.post(
        url,
        headers=get_supabase_headers(),
        json=rows,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise SupabaseError(
            f"POST {table} failed | status={response.status_code} | body={response.text}"
        )


def fetch_latest_spot(symbol: str) -> float:
    rows = supabase_get(
        "market_spot_snapshots",
        {
            "select": "symbol,spot,ts",
            "symbol": f"eq.{symbol}",
            "order": "ts.desc",
            "limit": "1",
        },
    )
    if not rows:
        raise SupabaseError(f"No market_spot_snapshots row found for {symbol}")

    spot = rows[0].get("spot")
    if spot is None:
        raise SupabaseError(f"Latest spot is null for {symbol}")

    return float(spot)


def build_dhan_payload() -> Dict[str, List[int]]:
    payload: Dict[str, List[int]] = {}
    for contract in FUTURES_CONTRACTS.values():
        payload.setdefault(contract["exchange_segment"], []).append(contract["security_id"])
    return payload


def write_debug_payload(payload: Dict[str, Any]) -> None:
    path = DEBUG_DIR / "index_futures_ltp_payload.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[DEBUG] Wrote payload to {path.relative_to(Path(r'C:\gammaenginepython'))}")


def fetch_ltp_payload_with_retry() -> Dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_API_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }

    payload = build_dhan_payload()
    write_debug_payload(payload)

    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.post(
            DHAN_LTP_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        body_text = response.text
        try:
            body_json = response.json()
        except Exception:
            body_json = None

        if response.status_code == 200:
            if isinstance(body_json, dict) and body_json.get("status") == "success":
                return body_json

            raise DhanError(
                f"Dhan non-success payload for index futures | response={body_text}"
            )

        if response.status_code == 429:
            print(
                f"[WARN] Dhan HTTP 429 on futures capture | attempt={attempt}/{MAX_RETRIES}"
            )
            if attempt < MAX_RETRIES:
                print(f"[RETRY] Sleeping {backoff:.1f}s before retry.")
                time.sleep(backoff)
                backoff *= 2
                continue

            raise DhanError(
                f"Dhan HTTP 429 for index futures market quote request after retries | response={body_text}"
            )

        raise DhanError(
            f"Dhan HTTP {response.status_code} for index futures market quote request | response={body_text}"
        )

    raise DhanError("Unexpected retry loop exit in fetch_ltp_payload_with_retry().")


def extract_last_price(payload: Dict[str, Any], exchange_segment: str, security_id: int) -> float:
    data = payload.get("data", {})
    segment_data = data.get(exchange_segment, {})
    instrument_data = segment_data.get(str(security_id))

    if not isinstance(instrument_data, dict):
        raise DhanError(
            f"Missing instrument data in Dhan payload | segment={exchange_segment} | security_id={security_id}"
        )

    last_price = instrument_data.get("last_price")
    if last_price is None:
        raise DhanError(
            f"Missing last_price in Dhan payload | segment={exchange_segment} | security_id={security_id}"
        )

    return float(last_price)


def build_output_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    capture_ts = utc_now_iso()
    rows: List[Dict[str, Any]] = []

    for symbol, contract in FUTURES_CONTRACTS.items():
        spot = fetch_latest_spot(symbol)
        futures_price = extract_last_price(
            payload,
            contract["exchange_segment"],
            contract["security_id"],
        )
        basis = futures_price - spot
        basis_pct = (basis / spot) * 100 if spot != 0 else None

        print(
            f"{symbol} | spot={spot} | futures={futures_price} | "
            f"basis={basis} | basis_pct={basis_pct}"
        )

        rows.append(
            {
                "ts": capture_ts,
                "symbol": symbol,
                "futures_price": futures_price,
                "basis": basis,
                "basis_pct": basis_pct,
            }
        )

    return rows


def capture_once() -> int:
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)
    require_env("DHAN_CLIENT_ID", DHAN_CLIENT_ID)
    require_env("DHAN_API_TOKEN", DHAN_API_TOKEN)

    payload = fetch_ltp_payload_with_retry()
    rows = build_output_rows(payload)
    supabase_insert_rows("index_futures_snapshots", rows)

    print("-" * 72)
    print(f"Inserted rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(capture_once())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise