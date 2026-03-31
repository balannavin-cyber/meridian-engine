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
# MERDIAN - Capture Market Spot Snapshot
# ----------------------------------------------------------------------------
# Purpose:
#   Capture latest NIFTY and SENSEX index spot prices from Dhan Market Quote
#   API using IDX_I and write to public.market_spot_snapshots.
#
# Runtime hardening added:
#   - Retry on Dhan 429 rate limit
#   - Short exponential backoff
#   - Clean failure after retries
#
# IMPORTANT:
#   market_spot_snapshots requires source_table (NOT NULL).
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

DEBUG_DIR = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_outputs"))
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

INDEX_CONTRACTS = {
    "NIFTY": {
        "exchange_segment": "IDX_I",
        "security_id": 13,
    },
    "SENSEX": {
        "exchange_segment": "IDX_I",
        "security_id": 51,
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
    print("MERDIAN - Capture Market Spot Snapshot")
    print("=" * 72)


def get_supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


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


def build_dhan_payload() -> Dict[str, List[int]]:
    payload: Dict[str, List[int]] = {}
    for contract in INDEX_CONTRACTS.values():
        payload.setdefault(contract["exchange_segment"], []).append(contract["security_id"])
    return payload


def write_debug_payload(payload: Dict[str, Any]) -> None:
    path = DEBUG_DIR / "market_spot_idx_i_payload.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[DEBUG] Wrote payload to {path.relative_to(Path(r'C:\gammaenginepython'))}")


def fetch_idx_i_ltp_payload_with_retry() -> Dict[str, Any]:
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
                f"Dhan non-success payload for IDX_I spot capture | response={body_text}"
            )

        if response.status_code == 429:
            print(
                f"[WARN] Dhan HTTP 429 on IDX_I spot capture | attempt={attempt}/{MAX_RETRIES}"
            )
            if attempt < MAX_RETRIES:
                print(f"[RETRY] Sleeping {backoff:.1f}s before retry.")
                time.sleep(backoff)
                backoff *= 2
                continue

            raise DhanError(
                f"Dhan HTTP 429 for IDX_I market quote request after retries | response={body_text}"
            )

        raise DhanError(
            f"Dhan HTTP {response.status_code} for IDX_I market quote request | response={body_text}"
        )

    raise DhanError("Unexpected retry loop exit in fetch_idx_i_ltp_payload_with_retry().")


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

    for symbol, contract in INDEX_CONTRACTS.items():
        spot = extract_last_price(
            payload,
            contract["exchange_segment"],
            contract["security_id"],
        )

        print(f"{symbol}:  {spot}")
        print(f"{symbol}: {spot} @ {capture_ts}")

        rows.append(
            {
                "ts": capture_ts,
                "symbol": symbol,
                "spot": spot,
                "source_table": "dhan_idx_i",
                "raw": {
                    "provider": "dhan",
                    "endpoint": "marketfeed/ltp",
                    "exchange_segment": contract["exchange_segment"],
                    "security_id": contract["security_id"],
                },
            }
        )

    return rows


def capture_once() -> int:
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)
    require_env("DHAN_CLIENT_ID", DHAN_CLIENT_ID)
    require_env("DHAN_API_TOKEN", DHAN_API_TOKEN)

    payload = fetch_idx_i_ltp_payload_with_retry()
    print("[INFO] Fetched index spots from Dhan Market Quote API using IDX_I")

    rows = build_output_rows(payload)
    supabase_insert_rows("market_spot_snapshots", rows)

    print("-" * 72)
    print(f"Inserted rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(capture_once())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
