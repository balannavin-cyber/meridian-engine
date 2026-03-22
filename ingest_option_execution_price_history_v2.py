from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# ============================================================================
# MERDIAN - Live Option Execution Price History Ingestion (V2)
# ----------------------------------------------------------------------------
# Purpose:
#   Replace stale DB-sourced execution price capture with direct live Dhan
#   Market Quote API requests for only the relevant execution strikes.
#
# Writes to:
#   public.option_execution_price_history
#
# Reads from:
#   public.market_spot_snapshots
#   public.dhan_scripmaster
#
# Notes:
#   - Uses Dhan Market Quote LTP API for live prices.
#   - IV is not provided by this endpoint, so iv is stored as NULL for now.
#   - Capture timestamp is the current UTC run time for all rows in a run.
#   - Contract selection is done in Python to avoid text/numeric strike mismatch.
# ============================================================================


if load_dotenv is not None:
    load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "").strip()
DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN", "").strip()

REQUEST_TIMEOUT_SECONDS = 30
DHAN_LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"

SYMBOL_CONFIG: Dict[str, Dict[str, Any]] = {
    "NIFTY": {
        "step": 50,
        "exchange_segment": "NSE_FNO",
        "exchange_id": "NSE",
    },
    "SENSEX": {
        "step": 100,
        "exchange_segment": "BSE_FNO",
        "exchange_id": "BSE",
    },
}

TARGET_SYMBOLS = list(SYMBOL_CONFIG.keys())


class ConfigError(RuntimeError):
    pass


class SupabaseError(RuntimeError):
    pass


class DhanError(RuntimeError):
    pass


@dataclass
class SpotSnapshot:
    symbol: str
    spot: float
    ts: str


@dataclass
class InstrumentContract:
    symbol: str
    strike: float
    option_type: str
    expiry_date: str
    security_id: str
    exchange_segment: str


def require_env(name: str, value: str) -> str:
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def print_header() -> None:
    print("=" * 72)
    print("MERDIAN - Live Option Execution Price History Ingestion (V2)")
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


def supabase_post_upsert(
    table: str,
    rows: List[Dict[str, Any]],
    on_conflict: str,
) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = get_supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates"

    response = requests.post(
        url,
        headers=headers,
        params={"on_conflict": on_conflict},
        json=rows,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise SupabaseError(
            f"POST upsert {table} failed | status={response.status_code} | body={response.text}"
        )


def fetch_latest_spot(symbol: str) -> SpotSnapshot:
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
        raise SupabaseError(f"No market_spot_snapshots row found for symbol={symbol}")

    row = rows[0]
    spot_val = row.get("spot")
    ts_val = row.get("ts")

    if spot_val is None:
        raise SupabaseError(f"Latest market_spot_snapshots row has null spot for {symbol}")
    if not ts_val:
        raise SupabaseError(f"Latest market_spot_snapshots row has null ts for {symbol}")

    return SpotSnapshot(
        symbol=symbol,
        spot=float(spot_val),
        ts=str(ts_val),
    )


def compute_execution_strikes(symbol: str, spot: float) -> List[Tuple[float, str]]:
    step = SYMBOL_CONFIG[symbol]["step"]
    lower = math.floor(spot / step) * step
    upper = math.ceil(spot / step) * step

    return [
        (float(lower), "CE"),
        (float(lower - step), "CE"),
        (float(upper), "PE"),
        (float(upper + step), "PE"),
    ]


def parse_numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if text == "":
            return None
        return float(text)
    except Exception:
        return None


def fetch_candidate_contract_rows(symbol: str, option_type: str) -> List[Dict[str, Any]]:
    today_str = date.today().isoformat()
    exchange_id = SYMBOL_CONFIG[symbol]["exchange_id"]

    rows = supabase_get(
        "dhan_scripmaster",
        {
            "select": "SECURITY_ID,UNDERLYING_SYMBOL,STRIKE_PRICE,OPTION_TYPE,SM_EXPIRY_DATE,INSTRUMENT,EXCH_ID,SEGMENT",
            "UNDERLYING_SYMBOL": f"eq.{symbol}",
            "OPTION_TYPE": f"eq.{option_type}",
            "INSTRUMENT": "eq.OPTIDX",
            "EXCH_ID": f"eq.{exchange_id}",
            "SM_EXPIRY_DATE": f"gte.{today_str}",
            "order": "SM_EXPIRY_DATE.asc",
            "limit": "5000",
        },
    )
    return rows


def choose_exact_contract(
    symbol: str,
    strike: float,
    option_type: str,
) -> Optional[InstrumentContract]:
    candidate_rows = fetch_candidate_contract_rows(symbol, option_type)

    if not candidate_rows:
        return None

    exact_rows: List[Dict[str, Any]] = []
    for row in candidate_rows:
        row_strike = parse_numeric(row.get("STRIKE_PRICE"))
        expiry_date = row.get("SM_EXPIRY_DATE")
        security_id = row.get("SECURITY_ID")

        if row_strike is None or not expiry_date or security_id is None:
            continue

        if abs(row_strike - strike) < 0.0001:
            exact_rows.append(row)

    if not exact_rows:
        return None

    exact_rows.sort(key=lambda r: str(r.get("SM_EXPIRY_DATE")))
    chosen = exact_rows[0]

    return InstrumentContract(
        symbol=symbol,
        strike=float(strike),
        option_type=option_type,
        expiry_date=str(chosen["SM_EXPIRY_DATE"]),
        security_id=str(chosen["SECURITY_ID"]),
        exchange_segment=SYMBOL_CONFIG[symbol]["exchange_segment"],
    )


def build_contract_universe(spots: Dict[str, SpotSnapshot]) -> List[InstrumentContract]:
    contracts: List[InstrumentContract] = []

    for symbol, spot_snapshot in spots.items():
        strike_pairs = compute_execution_strikes(symbol, spot_snapshot.spot)
        print(
            f"[STRIKES] {symbol} | spot={spot_snapshot.spot:.2f} | "
            f"targets={[(int(s), t) for s, t in strike_pairs]}"
        )

        for strike, option_type in strike_pairs:
            contract = choose_exact_contract(symbol, strike, option_type)
            if contract is None:
                print(
                    f"[WARN] No contract found | symbol={symbol} | "
                    f"strike={int(strike)} | option_type={option_type}"
                )
                continue

            contracts.append(contract)
            print(
                f"[MAP] {symbol} {option_type} {int(strike)} | "
                f"expiry={contract.expiry_date} | security_id={contract.security_id} | "
                f"segment={contract.exchange_segment}"
            )

    if not contracts:
        raise RuntimeError("No execution contracts could be resolved from dhan_scripmaster.")

    return contracts


def fetch_dhan_ltp(contracts: List[InstrumentContract]) -> Dict[Tuple[str, str], float]:
    payload: Dict[str, List[int]] = {}

    for contract in contracts:
        payload.setdefault(contract.exchange_segment, []).append(int(contract.security_id))

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_API_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }

    print(f"[DHAN] Request payload: {payload}")

    response = requests.post(
        DHAN_LTP_URL,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code >= 300:
        raise DhanError(
            f"Dhan LTP failed | status={response.status_code} | body={response.text}"
        )

    body = response.json()
    status = body.get("status")
    if status != "success":
        raise DhanError(f"Dhan LTP returned non-success payload: {body}")

    data = body.get("data", {})
    result: Dict[Tuple[str, str], float] = {}

    for exchange_segment, segment_map in data.items():
        if not isinstance(segment_map, dict):
            continue
        for security_id, instrument_data in segment_map.items():
            last_price = instrument_data.get("last_price")
            if last_price is None:
                continue
            result[(exchange_segment, str(security_id))] = float(last_price)

    return result


def build_output_rows(
    capture_ts: str,
    spots: Dict[str, SpotSnapshot],
    contracts: List[InstrumentContract],
    ltp_map: Dict[Tuple[str, str], float],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for contract in contracts:
        ltp = ltp_map.get((contract.exchange_segment, contract.security_id))
        if ltp is None:
            print(
                f"[WARN] No live LTP returned | symbol={contract.symbol} | "
                f"segment={contract.exchange_segment} | security_id={contract.security_id}"
            )
            continue

        spot_snapshot = spots[contract.symbol]

        rows.append(
            {
                "symbol": contract.symbol,
                "ts": capture_ts,
                "expiry_date": contract.expiry_date,
                "strike": contract.strike,
                "option_type": contract.option_type,
                "ltp": ltp,
                "iv": None,
                "spot": spot_snapshot.spot,
                "source": "dhan_execution_capture_v2",
            }
        )

        print(
            f"[ROW] {contract.symbol} {contract.option_type} {int(contract.strike)} | "
            f"expiry={contract.expiry_date} | ltp={ltp} | spot={spot_snapshot.spot:.2f}"
        )

    return rows


def main() -> int:
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)
    require_env("DHAN_CLIENT_ID", DHAN_CLIENT_ID)
    require_env("DHAN_API_TOKEN", DHAN_API_TOKEN)

    capture_ts = now_utc_iso()
    print(f"[RUN] capture_ts_utc={capture_ts}")

    spots: Dict[str, SpotSnapshot] = {}
    for symbol in TARGET_SYMBOLS:
        spot_snapshot = fetch_latest_spot(symbol)
        spots[symbol] = spot_snapshot
        print(
            f"[SPOT] {symbol} | spot={spot_snapshot.spot:.2f} | spot_ts={spot_snapshot.ts}"
        )

    contracts = build_contract_universe(spots)
    print(f"[INFO] Contracts resolved: {len(contracts)}")

    ltp_map = fetch_dhan_ltp(contracts)
    print(f"[INFO] Live prices returned: {len(ltp_map)}")

    rows = build_output_rows(capture_ts, spots, contracts, ltp_map)
    if not rows:
        raise RuntimeError("No output rows built; nothing to upsert.")

    supabase_post_upsert(
        "option_execution_price_history",
        rows,
        on_conflict="symbol,ts,expiry_date,strike,option_type",
    )

    print(f"[DONE] Rows upserted: {len(rows)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise