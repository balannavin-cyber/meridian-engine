from __future__ import annotations

import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


UTC = timezone.utc


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


def utc_now() -> datetime:
    return datetime.now(UTC)


def get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def get_supabase_config(prefer: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
    url = get_env("SUPABASE_URL").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY fallback).")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return url, headers


def supabase_select(
    table_name: str,
    params: Dict[str, str],
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    base_url, headers = get_supabase_config(prefer="return=representation")
    url = f"{base_url}/rest/v1/{table_name}?{urlencode(params)}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase SELECT failed ({resp.status_code}) on {table_name}: {resp.text}")
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected SELECT response type from {table_name}: {type(data)}")
    return data


def supabase_upsert(
    table_name: str,
    rows: List[Dict[str, Any]],
    on_conflict: str,
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    if not rows:
        return []

    base_url, headers = get_supabase_config(prefer="resolution=merge-duplicates,return=representation")
    url = f"{base_url}/rest/v1/{table_name}?on_conflict={on_conflict}"
    resp = requests.post(url, headers=headers, json=rows, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase UPSERT failed ({resp.status_code}) on {table_name}: {resp.text}")

    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def fetch_latest_runs_per_symbol(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}

    for symbol in symbols:
        rows = supabase_select(
            "option_chain_snapshots",
            {
                "select": "symbol,run_id,created_at",
                "symbol": f"eq.{symbol}",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if rows:
            result[symbol] = rows[0]

    return result


def fetch_rows_for_run_id(run_id: str) -> List[Dict[str, Any]]:
    offset = 0
    limit = 1000
    rows: List[Dict[str, Any]] = []

    while True:
        batch = supabase_select(
            "option_chain_snapshots",
            {
                "select": "run_id,symbol,expiry_date,strike,option_type,ltp,oi,volume,iv,spot,created_at",
                "run_id": f"eq.{run_id}",
                "order": "strike.asc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        rows.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    return rows


def classify_pcr_regime(put_call_ratio: Optional[float]) -> Optional[str]:
    if put_call_ratio is None:
        return None
    if put_call_ratio >= 1.15:
        return "BEARISH"
    if put_call_ratio <= 0.85:
        return "BULLISH"
    return "NEUTRAL"


def classify_flow_regime(
    ce_vol_oi_ratio: Optional[float],
    pe_vol_oi_ratio: Optional[float],
) -> Optional[str]:
    if ce_vol_oi_ratio is None or pe_vol_oi_ratio is None:
        return None

    diff = pe_vol_oi_ratio - ce_vol_oi_ratio
    if diff >= 0.10:
        return "PE_ACTIVE"
    if diff <= -0.10:
        return "CE_ACTIVE"
    return "NEUTRAL"


def classify_skew_regime(chain_iv_skew: Optional[float]) -> Optional[str]:
    if chain_iv_skew is None:
        return None
    if chain_iv_skew >= 0.50:
        return "FEAR"
    if chain_iv_skew <= -0.50:
        return "COMPLACENCY"
    return "NEUTRAL"


def nearest_atm_strike(rows: List[Dict[str, Any]]) -> Optional[float]:
    valid_spots = [to_float(r.get("spot")) for r in rows if to_float(r.get("spot")) is not None]
    if not valid_spots:
        return None
    spot = valid_spots[0]

    strikes = [to_float(r.get("strike")) for r in rows if to_float(r.get("strike")) is not None]
    strikes = [s for s in strikes if s is not None]
    if not strikes:
        return None

    return min(strikes, key=lambda s: abs(s - spot))


def choose_window_strikes(rows: List[Dict[str, Any]], atm_strike: float, wing_count_each_side: int = 5) -> List[float]:
    all_strikes = sorted({to_float(r.get("strike")) for r in rows if to_float(r.get("strike")) is not None})
    if not all_strikes:
        return []

    try:
        atm_index = min(range(len(all_strikes)), key=lambda i: abs(all_strikes[i] - atm_strike))
    except Exception:
        return []

    lo = max(0, atm_index - wing_count_each_side)
    hi = min(len(all_strikes), atm_index + wing_count_each_side + 1)
    return all_strikes[lo:hi]


def safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def compute_for_run(run_row: Dict[str, Any], rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None

    symbol = str(run_row.get("symbol"))
    run_id = str(run_row.get("run_id"))

    created_ts = parse_ts(rows[0].get("created_at")) or utc_now()
    ts = created_ts.isoformat()

    total_rows = len(rows)
    usable_rows = 0

    ce_oi_total = 0.0
    pe_oi_total = 0.0

    for r in rows:
        option_type = str(r.get("option_type") or "").upper()
        oi = to_float(r.get("oi")) or 0.0
        if option_type == "CE":
            ce_oi_total += oi
        elif option_type == "PE":
            pe_oi_total += oi

    put_call_ratio = safe_ratio(pe_oi_total, ce_oi_total)

    atm = nearest_atm_strike(rows)
    if atm is None:
        return None

    window_strikes = set(choose_window_strikes(rows, atm, wing_count_each_side=5))

    ce_vol_sum = 0.0
    ce_oi_sum = 0.0
    pe_vol_sum = 0.0
    pe_oi_sum = 0.0
    skew_values: List[float] = []

    grouped_by_strike: Dict[float, Dict[str, Dict[str, Any]]] = defaultdict(dict)

    valid_spot = None
    for r in rows:
        strike = to_float(r.get("strike"))
        option_type = str(r.get("option_type") or "").upper()
        if strike is None or option_type not in ("CE", "PE"):
            continue

        grouped_by_strike[strike][option_type] = r

        if strike in window_strikes:
            oi = to_float(r.get("oi"))
            vol = to_float(r.get("volume"))
            iv = to_float(r.get("iv"))
            if oi is not None and iv is not None:
                usable_rows += 1
            if option_type == "CE":
                if vol is not None:
                    ce_vol_sum += vol
                if oi is not None:
                    ce_oi_sum += oi
            elif option_type == "PE":
                if vol is not None:
                    pe_vol_sum += vol
                if oi is not None:
                    pe_oi_sum += oi

        if valid_spot is None:
            valid_spot = to_float(r.get("spot"))

    for strike in window_strikes:
        pair = grouped_by_strike.get(strike, {})
        ce_iv = to_float(pair.get("CE", {}).get("iv"))
        pe_iv = to_float(pair.get("PE", {}).get("iv"))
        if ce_iv is not None and pe_iv is not None:
            skew_values.append(pe_iv - ce_iv)

    ce_vol_oi_ratio = safe_ratio(ce_vol_sum, ce_oi_sum)
    pe_vol_oi_ratio = safe_ratio(pe_vol_sum, pe_oi_sum)
    chain_iv_skew = (sum(skew_values) / len(skew_values)) if skew_values else None

    row = {
        "ts": ts,
        "symbol": symbol,
        "run_id": run_id,
        "spot": round(valid_spot, 6) if valid_spot is not None else None,
        "put_call_ratio": round(put_call_ratio, 6) if put_call_ratio is not None else None,
        "pcr_regime": classify_pcr_regime(put_call_ratio),
        "ce_vol_oi_ratio": round(ce_vol_oi_ratio, 6) if ce_vol_oi_ratio is not None else None,
        "pe_vol_oi_ratio": round(pe_vol_oi_ratio, 6) if pe_vol_oi_ratio is not None else None,
        "flow_regime": classify_flow_regime(ce_vol_oi_ratio, pe_vol_oi_ratio),
        "chain_iv_skew": round(chain_iv_skew, 6) if chain_iv_skew is not None else None,
        "skew_regime": classify_skew_regime(chain_iv_skew),
        "usable_rows": usable_rows,
        "total_rows": total_rows,
    }
    return row


def main() -> int:
    print("========================================================================")
    print("MERDIAN - compute_options_flow_local")
    print("========================================================================")

    latest_runs = fetch_latest_runs_per_symbol(["NIFTY", "SENSEX"])
    if not latest_runs:
        print("No latest runs found.")
        return 1

    out_rows: List[Dict[str, Any]] = []

    for symbol in ["NIFTY", "SENSEX"]:
        run_row = latest_runs.get(symbol)
        if not run_row:
            print(f"Skipping {symbol}: no latest run found.")
            continue

        run_id = str(run_row["run_id"])
        print("------------------------------------------------------------------------")
        print(f"Fetching option-chain rows for {symbol} | run_id={run_id}")
        rows = fetch_rows_for_run_id(run_id)
        print(f"Fetched rows: {len(rows)}")

        out = compute_for_run(run_row, rows)
        if out is None:
            print(f"Could not compute options flow row for {symbol}")
            continue

        out_rows.append(out)
        print(f"Prepared options flow row for {symbol}")
        for k, v in out.items():
            print(f"{k}={v}")

    if not out_rows:
        print("No output rows prepared. Exiting with code 1.")
        return 1

    print("------------------------------------------------------------------------")
    print("Upserting rows to public.options_flow_snapshots ...")
    inserted = supabase_upsert("options_flow_snapshots", out_rows, on_conflict="symbol,ts")
    print(f"Rows returned by Supabase: {len(inserted)}")
    print("COMPUTE OPTIONS FLOW COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())