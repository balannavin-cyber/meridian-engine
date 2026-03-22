from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))


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


def supabase_select(table_name: str, params: Dict[str, str], timeout: int = 60) -> List[Dict[str, Any]]:
    base_url, headers = get_supabase_config(prefer="return=representation")
    url = f"{base_url}/rest/v1/{table_name}?{urlencode(params)}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase SELECT failed ({resp.status_code}) on {table_name}: {resp.text}")
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected SELECT response type from {table_name}: {type(data)}")
    return data


def supabase_upsert(table_name: str, rows: List[Dict[str, Any]], on_conflict: str, timeout: int = 60) -> List[Dict[str, Any]]:
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


def fetch_latest_row(table_name: str, symbol: str) -> Optional[Dict[str, Any]]:
    rows = supabase_select(
        table_name,
        {
            "select": "*",
            "symbol": f"eq.{symbol}",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def fetch_latest_ohlc_rows(symbol: str, limit: int = 60) -> List[Dict[str, Any]]:
    rows = supabase_select(
        "intraday_ohlc",
        {
            "select": "*",
            "symbol": f"eq.{symbol}",
            "order": "ts.desc",
            "limit": str(limit),
        },
    )
    rows.sort(key=lambda r: r.get("ts") or "")
    return rows


def session_date_ist(ts: datetime) -> str:
    return ts.astimezone(IST).date().isoformat()


def compute_straddle_velocity(gamma_row: Optional[Dict[str, Any]], previous_gamma_row: Optional[Dict[str, Any]]) -> Optional[float]:
    if not gamma_row or not previous_gamma_row:
        return None

    curr = to_float(gamma_row.get("straddle_atm"))
    prev = to_float(previous_gamma_row.get("straddle_atm"))
    if curr is None or prev is None:
        return None

    return curr - prev


def fetch_previous_gamma_row(symbol: str, latest_run_id: Optional[str]) -> Optional[Dict[str, Any]]:
    params = {
        "select": "*",
        "symbol": f"eq.{symbol}",
        "order": "created_at.desc",
        "limit": "2",
    }
    rows = supabase_select("gamma_metrics", params)
    if not rows:
        return None
    if len(rows) == 1:
        return None

    if latest_run_id and str(rows[0].get("run_id")) == latest_run_id:
        return rows[1]
    return rows[1]


def infer_pattern(
    gamma_row: Optional[Dict[str, Any]],
    options_flow_row: Optional[Dict[str, Any]],
    latest_ohlc: Optional[Dict[str, Any]],
) -> Tuple[str, int, bool, float, str]:
    squeeze_score = 0
    reasons: List[str] = []

    gamma_regime = str(gamma_row.get("regime") or "") if gamma_row else ""
    flip_distance_pct = to_float(gamma_row.get("flip_distance_pct")) if gamma_row else None
    gamma_concentration = to_float(gamma_row.get("gamma_concentration")) if gamma_row else None

    flow_regime = str(options_flow_row.get("flow_regime") or "") if options_flow_row else ""
    skew_regime = str(options_flow_row.get("skew_regime") or "") if options_flow_row else ""

    if gamma_regime == "LONG_GAMMA":
        squeeze_score += 1
        reasons.append("LONG_GAMMA present")

    if flip_distance_pct is not None and abs(flip_distance_pct) <= 1.0:
        squeeze_score += 1
        reasons.append("Near gamma flip")

    if gamma_concentration is not None and gamma_concentration >= 0.10:
        squeeze_score += 1
        reasons.append("High gamma concentration")

    if flow_regime in ("PE_ACTIVE", "CE_ACTIVE"):
        squeeze_score += 1
        reasons.append(f"Directional options flow: {flow_regime}")

    if skew_regime == "FEAR":
        squeeze_score += 1
        reasons.append("Fear skew present")

    pattern = "NONE"
    confidence = 0.35
    caution_text = "No strong SMDM condition detected."

    if squeeze_score >= 4:
        pattern = "SQUEEZE"
        confidence = 0.75
        caution_text = "Multiple squeeze conditions detected."
    elif gamma_regime == "LONG_GAMMA" and gamma_concentration is not None and gamma_concentration >= 0.10:
        pattern = "GAMMA_PINNING"
        confidence = 0.65
        caution_text = "Long gamma with high concentration may pin price."
    elif skew_regime == "FEAR" and flow_regime == "PE_ACTIVE":
        pattern = "STOP_HUNT"
        confidence = 0.55
        caution_text = "Fear skew plus PE activity may indicate stress/stop dynamics."

    squeeze_active = pattern in ("SQUEEZE", "GAMMA_PINNING")

    if latest_ohlc:
        session_high = to_float(latest_ohlc.get("session_high"))
        session_low = to_float(latest_ohlc.get("session_low"))
        close = to_float(latest_ohlc.get("close"))
        if close is not None and session_high is not None and session_low is not None:
            if abs(session_high - close) < abs(close - session_low):
                caution_text += " Price is closer to session high."
            else:
                caution_text += " Price is closer to session low."

    return pattern, squeeze_score, squeeze_active, confidence, caution_text


def build_row(symbol: str) -> Optional[Dict[str, Any]]:
    gamma_row = fetch_latest_row("gamma_metrics", symbol)
    options_flow_row = fetch_latest_row("options_flow_snapshots", symbol)
    ohlc_rows = fetch_latest_ohlc_rows(symbol, limit=60)

    if not gamma_row and not options_flow_row and not ohlc_rows:
        return None

    latest_ohlc = ohlc_rows[-1] if ohlc_rows else None
    latest_ts_candidates = [
        parse_ts(gamma_row.get("ts")) if gamma_row else None,
        parse_ts(options_flow_row.get("ts")) if options_flow_row else None,
        parse_ts(latest_ohlc.get("ts")) if latest_ohlc else None,
    ]
    latest_ts_candidates = [t for t in latest_ts_candidates if t is not None]
    ts = max(latest_ts_candidates).isoformat() if latest_ts_candidates else datetime.now(UTC).isoformat()

    latest_run_id = str(gamma_row.get("run_id")) if gamma_row and gamma_row.get("run_id") else None
    previous_gamma_row = fetch_previous_gamma_row(symbol, latest_run_id)
    straddle_velocity = compute_straddle_velocity(gamma_row, previous_gamma_row)

    otm_oi_velocity = None

    dte = to_int(gamma_row.get("dte")) if gamma_row else None

    pattern, squeeze_score, squeeze_active, pattern_confidence, caution_text = infer_pattern(
        gamma_row=gamma_row,
        options_flow_row=options_flow_row,
        latest_ohlc=latest_ohlc,
    )

    row = {
        "ts": ts,
        "symbol": symbol,
        "run_id": latest_run_id,
        "dte": dte,
        "days_to_futures_expiry": None,
        "squeeze_active": squeeze_active,
        "squeeze_score": squeeze_score,
        "pattern": pattern,
        "pattern_confidence": round(pattern_confidence, 6),
        "straddle_velocity": round(straddle_velocity, 6) if straddle_velocity is not None else None,
        "otm_oi_velocity": otm_oi_velocity,
        "caution_text": caution_text,
    }
    return row


def main() -> int:
    print("========================================================================")
    print("MERDIAN - compute_smdm_local")
    print("========================================================================")

    out_rows: List[Dict[str, Any]] = []

    for symbol in ["NIFTY", "SENSEX"]:
        print("------------------------------------------------------------------------")
        print(f"Building SMDM row for {symbol}")
        row = build_row(symbol)
        if row is None:
            print(f"No row prepared for {symbol}")
            continue

        out_rows.append(row)
        for k, v in row.items():
            print(f"{k}={v}")

    if not out_rows:
        print("No output rows prepared. Exiting with code 1.")
        return 1

    print("------------------------------------------------------------------------")
    print("Upserting rows to public.smdm_snapshots ...")
    inserted = supabase_upsert("smdm_snapshots", out_rows, on_conflict="symbol,ts")
    print(f"Rows returned by Supabase: {len(inserted)}")
    print("COMPUTE SMDM COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())