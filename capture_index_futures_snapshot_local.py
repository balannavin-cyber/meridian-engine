from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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
# Hardening:
#   - Dynamic front-month contract resolution from public.dhan_scripmaster
#   - STRICT symbol alias matching to avoid BANKNIFTY / SENSEX50 false matches
#   - Correct Dhan auth headers preserved
#   - Retry on Dhan 429
#   - Graceful degradation if one symbol fails
#   - Exit cleanly every run
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

DEBUG_DIR = Path(r"C:\GammaEnginePython\debug_outputs")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# One authoritative symbol map for futures capture.
FUTURES_SYMBOLS = {
    "NIFTY": {
        "marketfeed_segment": "NSE_FNO",
        "aliases": ["NIFTY"],
        "reject_if_display_contains": ["BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "GIFTNIFTY"],
    },
    "SENSEX": {
        "marketfeed_segment": "BSE_FNO",
        "aliases": ["SENSEX"],
        "reject_if_display_contains": ["SENSEX50"],
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


def today_iso_local() -> str:
    return datetime.now().strftime("%Y-%m-%d")


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


def load_candidate_contract_rows(symbol: str) -> List[Dict[str, Any]]:
    today = today_iso_local()
    aliases = FUTURES_SYMBOLS[symbol]["aliases"]

    all_rows: List[Dict[str, Any]] = []

    for alias in aliases:
        rows = supabase_get(
            "dhan_scripmaster",
            {
                "select": (
                    '"SECURITY_ID","DISPLAY_NAME","INSTRUMENT_TYPE","SM_EXPIRY_DATE","SEGMENT","EXCH_ID"'
                ),
                '"DISPLAY_NAME"': f"ilike.*{alias}*",
                '"INSTRUMENT_TYPE"': "ilike.*FUT*",
                '"SM_EXPIRY_DATE"': f"gte.{today}",
                "order": '"SM_EXPIRY_DATE".asc',
                "limit": "20",
            },
        )
        all_rows.extend(rows)

    return all_rows


def is_valid_contract_match(symbol: str, row: Dict[str, Any]) -> bool:
    display_name = str(row.get("DISPLAY_NAME") or "").upper()
    instrument_type = str(row.get("INSTRUMENT_TYPE") or "").upper()

    if "FUT" not in instrument_type:
        return False

    aliases = [a.upper() for a in FUTURES_SYMBOLS[symbol]["aliases"]]
    if not any(alias in display_name for alias in aliases):
        return False

    reject_terms = [x.upper() for x in FUTURES_SYMBOLS[symbol]["reject_if_display_contains"]]
    if any(term in display_name for term in reject_terms):
        return False

    return True


def resolve_front_month_contract(symbol: str) -> Dict[str, Any]:
    """
    Resolve nearest non-expired futures contract using strict allow/reject logic
    so we do not accidentally match related indices like BANKNIFTY or SENSEX50.
    """
    candidate_rows = load_candidate_contract_rows(symbol)

    valid_rows = [row for row in candidate_rows if is_valid_contract_match(symbol, row)]

    if not valid_rows:
        raise SupabaseError(
            f"No non-expired valid futures contract found in dhan_scripmaster for {symbol}"
        )

    def expiry_key(row: Dict[str, Any]) -> str:
        return str(row.get("SM_EXPIRY_DATE") or "9999-12-31")

    valid_rows.sort(key=expiry_key)
    row = valid_rows[0]

    security_id = row.get("SECURITY_ID")
    expiry_date = row.get("SM_EXPIRY_DATE")
    display_name = row.get("DISPLAY_NAME")

    if security_id in (None, ""):
        raise SupabaseError(f"Resolved contract for {symbol} has empty SECURITY_ID")

    return {
        "symbol": symbol,
        "security_id": int(str(security_id)),
        "expiry_date": str(expiry_date) if expiry_date is not None else None,
        "display_name": str(display_name) if display_name is not None else None,
        "marketfeed_segment": FUTURES_SYMBOLS[symbol]["marketfeed_segment"],
    }


def write_debug_payload(payload: Dict[str, Any]) -> None:
    path = DEBUG_DIR / "index_futures_ltp_payload.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[DEBUG] Wrote payload to {path.relative_to(Path(r'C:\GammaEnginePython'))}")


def write_debug_contracts(resolved_contracts: List[Dict[str, Any]]) -> None:
    path = DEBUG_DIR / "resolved_index_futures_contracts.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(resolved_contracts, f, indent=2)
    print(f"[DEBUG] Wrote contracts to {path.relative_to(Path(r'C:\GammaEnginePython'))}")


def build_dhan_payload(resolved_contracts: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    payload: Dict[str, List[int]] = {}

    for contract in resolved_contracts:
        segment = contract["marketfeed_segment"]
        security_id = contract["security_id"]
        payload.setdefault(segment, []).append(security_id)

    return payload


def fetch_ltp_payload_with_retry(payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_API_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }

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
            if isinstance(body_json, dict):
                status_val = str(body_json.get("status", "")).lower()
                if status_val in {"success", "status.success", ""}:
                    return body_json
            return body_json if isinstance(body_json, dict) else {}

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


def extract_last_price_or_none(
    payload: Dict[str, Any],
    exchange_segment: str,
    security_id: int,
) -> Optional[float]:
    lower_data = payload.get("data", {})
    if isinstance(lower_data, dict):
        segment_data = lower_data.get(exchange_segment, {})
        if isinstance(segment_data, dict):
            instrument_data = segment_data.get(str(security_id))
            if isinstance(instrument_data, dict):
                last_price = instrument_data.get("last_price")
                if last_price is not None:
                    return float(last_price)

    upper_data = payload.get("Data", {})
    if isinstance(upper_data, dict):
        instrument_data = upper_data.get(str(security_id))
        if isinstance(instrument_data, dict):
            last_price = instrument_data.get("last_price")
            if last_price is not None:
                return float(last_price)

    print(
        f"[WARN] Missing instrument data in Dhan payload | "
        f"segment={exchange_segment} | security_id={security_id}"
    )
    return None


def build_output_rows(
    payload: Dict[str, Any],
    resolved_contracts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    capture_ts = utc_now_iso()
    rows: List[Dict[str, Any]] = []

    for contract in resolved_contracts:
        symbol = contract["symbol"]

        try:
            spot = fetch_latest_spot(symbol)
        except Exception as exc:
            print(f"[WARN] Skipping {symbol} because latest spot could not be loaded: {exc}")
            continue

        futures_price = extract_last_price_or_none(
            payload,
            contract["marketfeed_segment"],
            contract["security_id"],
        )

        if futures_price is None:
            print(
                f"[WARN] Skipping {symbol} futures row for this cycle because "
                f"the resolved contract was not returned by Dhan."
            )
            continue

        basis = futures_price - spot
        basis_pct = (basis / spot) * 100 if spot != 0 else None

        print(
            f"{symbol} | contract={contract['display_name']} | expiry={contract['expiry_date']} | "
            f"spot={spot} | futures={futures_price} | basis={basis} | basis_pct={basis_pct}"
        )

        rows.append(
            {
                "ts": capture_ts,
                "symbol": symbol,
                "contract_symbol": contract["display_name"],
                "expiry_date": contract["expiry_date"],
                "spot_price": spot,
                "futures_price": futures_price,
                "basis": basis,
                "basis_pct": basis_pct,
                "source": "dhan_ltp_dynamic_contract_resolution",
                "raw": {
                    "security_id": contract["security_id"],
                    "marketfeed_segment": contract["marketfeed_segment"],
                    "display_name": contract["display_name"],
                    "expiry_date": contract["expiry_date"],
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

    resolved_contracts: List[Dict[str, Any]] = []

    for symbol in FUTURES_SYMBOLS:
        try:
            contract = resolve_front_month_contract(symbol)
            resolved_contracts.append(contract)
            print(
                f"[RESOLVED] {symbol} -> security_id={contract['security_id']} | "
                f"expiry={contract['expiry_date']} | display_name={contract['display_name']}"
            )
        except Exception as exc:
            print(f"[WARN] Could not resolve contract for {symbol}: {exc}")

    if not resolved_contracts:
        print("[ERROR] No contracts could be resolved. Treating this cycle as failed.")
        return 1

    write_debug_contracts(resolved_contracts)

    payload = build_dhan_payload(resolved_contracts)
    ltp_payload = fetch_ltp_payload_with_retry(payload)
    rows = build_output_rows(ltp_payload, resolved_contracts)

    if not rows:
        print("[ERROR] No futures rows were built. Treating this cycle as failed.")
        return 1

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