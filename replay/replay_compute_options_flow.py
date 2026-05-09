"""
replay.replay_compute_options_flow — Replay mirror of compute_options_flow_local.py.

Differences from compute_options_flow_local.py:
  1. Reads option_chain_snapshots_replay (not _snapshots).
  2. Writes options_flow_snapshots_replay (not options_flow_snapshots).
  3. CLI: --replay-ts, --run-id, --symbol (single symbol per invocation, 
     matching orchestrator pattern).
  4. ts on output = replay_ts (canonical 5-min boundary), not row created_at.

Same compute logic: PCR, flow_regime, skew_regime classification, 
ATM±5 window for vol/oi ratios. Result tables differ in OI base width 
(replay 11 strikes vs live ~482) — same architectural property as gamma.

Author: Session 24 (2026-05-09)
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from replay.replay_clock import parse_replay_ts, replay_today_ist, to_iso_utc
from replay.replay_execution_log import ExecutionLog


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


def get_supabase_config(prefer: Optional[str] = None):
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url:
        raise RuntimeError("Missing SUPABASE_URL")
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY)")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    return url, headers


def supabase_select(table_name: str, params: Dict[str, str], timeout: int = 60) -> List[Dict[str, Any]]:
    base_url, headers = get_supabase_config(prefer="return=representation")
    url = f"{base_url}/rest/v1/{table_name}?{urlencode(params)}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase SELECT {table_name} failed {resp.status_code}: {resp.text}")
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response type from {table_name}")
    return data


def supabase_upsert(table_name: str, rows: List[Dict[str, Any]], on_conflict: str, timeout: int = 60) -> List[Dict[str, Any]]:
    if not rows:
        return []
    base_url, headers = get_supabase_config(prefer="resolution=merge-duplicates,return=representation")
    url = f"{base_url}/rest/v1/{table_name}?on_conflict={on_conflict}"
    resp = requests.post(url, headers=headers, json=rows, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase UPSERT {table_name} failed {resp.status_code}: {resp.text}")
    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def fetch_rows_for_run_id(run_id: str) -> List[Dict[str, Any]]:
    """REPLAY: read option_chain_snapshots_replay for run_id."""
    offset = 0
    limit = 1000
    rows: List[Dict[str, Any]] = []
    while True:
        batch = supabase_select(
            "option_chain_snapshots_replay",
            {
                "select": "run_id,symbol,expiry_date,strike,option_type,ltp,oi,volume,iv,spot,ts",
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


def classify_flow_regime(ce_vol_oi_ratio: Optional[float], pe_vol_oi_ratio: Optional[float]) -> Optional[str]:
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


def choose_window_strikes(rows: List[Dict[str, Any]], atm_strike: float, wing: int = 5) -> List[float]:
    all_strikes = sorted({to_float(r.get("strike")) for r in rows if to_float(r.get("strike")) is not None})
    if not all_strikes:
        return []
    try:
        atm_index = min(range(len(all_strikes)), key=lambda i: abs(all_strikes[i] - atm_strike))
    except Exception:
        return []
    lo = max(0, atm_index - wing)
    hi = min(len(all_strikes), atm_index + wing + 1)
    return all_strikes[lo:hi]


def safe_ratio(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None:
        return None
    if den == 0:
        return None
    return num / den


def compute_for_run(run_id: str, symbol: str, ts_iso: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None

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

    window_strikes = set(choose_window_strikes(rows, atm, wing=5))

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

    return {
        "ts": ts_iso,
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


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="replay_compute_options_flow")
    parser.add_argument("--replay-ts", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--symbol", required=True, choices=["NIFTY", "SENSEX"])
    return parser.parse_args(argv)


def main() -> int:
    load_dotenv()
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
    run_id = args.run_id.strip()
    replay_ts_iso = to_iso_utc(replay_ts)

    log = ExecutionLog(
        script_name="replay_compute_options_flow.py",
        expected_writes={"options_flow_snapshots_replay": 1},
        symbol=symbol,
        notes=f"options flow run_id={run_id} replay_ts={args.replay_ts}",
    )

    print("=" * 72)
    print("MERDIAN REPLAY - replay_compute_options_flow")
    print("=" * 72)
    print(f"replay_ts={args.replay_ts}")
    print(f"run_id={run_id}")
    print(f"symbol={symbol}")

    try:
        rows = fetch_rows_for_run_id(run_id)
    except RuntimeError as e:
        msg = str(e)
        if "Missing" in msg:
            return log.exit_with_reason("DEPENDENCY_MISSING", 1, error_message=msg)
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"fetch failed: {msg}")
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"fetch unexpected: {e}")

    if not rows:
        return log.exit_with_reason(
            "SKIPPED_NO_INPUT", 1,
            error_message=f"No option_chain_snapshots_replay rows for run_id={run_id}"
        )

    print(f"Fetched rows: {len(rows)}")

    try:
        out = compute_for_run(run_id, symbol, replay_ts_iso, rows)
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"compute failed: {e}")

    if out is None:
        return log.exit_with_reason(
            "DATA_ERROR", 1,
            error_message=f"compute_for_run returned None — likely no spot in chain"
        )

    print("Computed options flow row:")
    for k, v in out.items():
        print(f"  {k}={v}")

    try:
        inserted = supabase_upsert("options_flow_snapshots_replay", [out], on_conflict="symbol,ts")
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"upsert failed: {e}")

    log.record_write("options_flow_snapshots_replay", 1)

    note_parts = [f"run_id={run_id}", f"replay_ts={args.replay_ts}", f"usable_rows={out.get('usable_rows', 0)}"]
    if out.get("usable_rows", 0) < 5:
        note_parts.append("low_usable=true")

    return log.complete(notes=" ".join(note_parts))


if __name__ == "__main__":
    sys.exit(main())