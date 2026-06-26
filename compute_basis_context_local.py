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

# ENH-72 write-contract layer.
#
# ENH-07 (B) -- basis-velocity context (S57 scope add; display-not-gate per
# S37). Reads index_futures_snapshots ONLY (it carries spot_price, basis,
# basis_pct captured atomically in one row -> no futures/spot timing skew,
# no second basis definition). For each symbol it diffs the latest row
# against the row ~WINDOW minutes earlier and emits a fuel/fade label:
#
#   spot up   & basis_pct expanding  -> LONG_BUILD  (leveraged long; fuel)
#   spot up   & basis_pct shrinking  -> WEAK_LONG   (short-covering; fade)
#   spot down & basis_pct shrinking  -> SHORT_BUILD (leveraged short)
#   spot down & basis_pct expanding  -> WEAK_SHORT  (covering-bounce risk)
#   within deadband on either axis   -> NEUTRAL
#   velocity not computable          -> label NULL (still writes current basis)
#
# CONTRACT (same shape as compute_options_flow_local.py): no CLI args;
# discovers NIFTY+SENSEX itself; floor=1 row, typical=2; symbol=null.
from core.execution_log import ExecutionLog


UTC = timezone.utc

LOOKBACK_MIN = 30
WINDOW_MIN = int(float(os.getenv("MERDIAN_BASIS_VELOCITY_WINDOW_MIN", "15")))
MIN_GAP_MIN = float(os.getenv("MERDIAN_BASIS_MIN_GAP_MIN", "5"))      # reject prev closer than this
SPOT_DEADBAND_PCT = float(os.getenv("MERDIAN_BASIS_SPOT_DEADBAND_PCT", "0.0002"))  # 0.02%
VEL_DEADBAND_PP = float(os.getenv("MERDIAN_BASIS_VEL_DEADBAND_PP", "0.005"))       # 0.005 pp

VALID_LABELS = {"LONG_BUILD", "WEAK_LONG", "SHORT_BUILD", "WEAK_SHORT", "NEUTRAL"}


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


def fetch_recent_futures(symbol: str) -> List[Dict[str, Any]]:
    cutoff = (utc_now() - timedelta(minutes=LOOKBACK_MIN)).isoformat()
    return supabase_select(
        "index_futures_snapshots",
        {
            "select": "ts,symbol,spot_price,futures_price,basis,basis_pct",
            "symbol": f"eq.{symbol}",
            "ts": f"gte.{cutoff}",
            "order": "ts.desc",
            "limit": "200",
        },
    )


def classify(spot_delta: Optional[float], vel_pp: Optional[float], spot_now: Optional[float]) -> Optional[str]:
    if spot_delta is None or vel_pp is None or spot_now is None:
        return None
    spot_eps = abs(spot_now) * SPOT_DEADBAND_PCT
    spot_up = spot_delta > spot_eps
    spot_dn = spot_delta < -spot_eps
    basis_exp = vel_pp > VEL_DEADBAND_PP    # contango widening
    basis_shr = vel_pp < -VEL_DEADBAND_PP   # narrowing / toward backwardation
    if (not spot_up and not spot_dn) or (not basis_exp and not basis_shr):
        return "NEUTRAL"
    if spot_up and basis_exp:
        return "LONG_BUILD"
    if spot_up and basis_shr:
        return "WEAK_LONG"
    if spot_dn and basis_shr:
        return "SHORT_BUILD"
    if spot_dn and basis_exp:
        return "WEAK_SHORT"
    return "NEUTRAL"


def compute_for_symbol(symbol: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None
    now_row = rows[0]
    now_ts = parse_ts(now_row.get("ts"))
    if now_ts is None:
        return None

    basis_pct_now = to_float(now_row.get("basis_pct"))
    spot_now = to_float(now_row.get("spot_price"))
    basis_now = to_float(now_row.get("basis"))

    target_ts = now_ts - timedelta(minutes=WINDOW_MIN)
    min_gap = timedelta(minutes=MIN_GAP_MIN)

    # candidate prev rows: at least MIN_GAP older than now
    prev_row = None
    best = None
    for r in rows[1:]:
        r_ts = parse_ts(r.get("ts"))
        if r_ts is None:
            continue
        if (now_ts - r_ts) < min_gap:
            continue
        dist = abs((r_ts - target_ts).total_seconds())
        if best is None or dist < best:
            best = dist
            prev_row = r
            prev_ts_sel = r_ts

    basis_pct_prev = spot_prev = vel_pp = spot_delta = None
    window_actual = None
    if prev_row is not None:
        basis_pct_prev = to_float(prev_row.get("basis_pct"))
        spot_prev = to_float(prev_row.get("spot_price"))
        if basis_pct_now is not None and basis_pct_prev is not None:
            vel_pp = basis_pct_now - basis_pct_prev
        if spot_now is not None and spot_prev is not None:
            spot_delta = spot_now - spot_prev
        window_actual = int(round((now_ts - prev_ts_sel).total_seconds() / 60.0))

    label = classify(spot_delta, vel_pp, spot_now)

    return {
        "ts": now_ts.isoformat(),
        "symbol": symbol,
        "basis": round(basis_now, 6) if basis_now is not None else None,
        "basis_pct_now": round(basis_pct_now, 6) if basis_pct_now is not None else None,
        "basis_pct_prev": round(basis_pct_prev, 6) if basis_pct_prev is not None else None,
        "basis_velocity_pp": round(vel_pp, 6) if vel_pp is not None else None,
        "window_min": window_actual,
        "spot_now": round(spot_now, 6) if spot_now is not None else None,
        "spot_delta": round(spot_delta, 6) if spot_delta is not None else None,
        "context_label": label,
    }


def main() -> int:
    print("========================================================================")
    print("MERDIAN - compute_basis_context_local (ENH-07 B)")
    print("========================================================================")

    log = ExecutionLog(
        script_name="compute_basis_context_local.py",
        expected_writes={"basis_context_snapshots": 1},
        symbol=None,
        notes="basis-velocity context NIFTY+SENSEX batch",
    )

    per_symbol_status: Dict[str, str] = {}
    out_rows: List[Dict[str, Any]] = []

    for symbol in ["NIFTY", "SENSEX"]:
        try:
            rows = fetch_recent_futures(symbol)
        except RuntimeError as e:
            msg = str(e)
            if "Missing environment variable" in msg or "Missing SUPABASE" in msg:
                return log.exit_with_reason("DEPENDENCY_MISSING", exit_code=1, error_message=msg)
            print(f"[ERR] fetch failed for {symbol}: {msg}")
            per_symbol_status[symbol] = "fetch_failed"
            continue
        except Exception as e:
            print(f"[ERR] fetch unexpected for {symbol}: {e}")
            per_symbol_status[symbol] = "fetch_failed"
            continue

        if not rows:
            print(f"Skipping {symbol}: no recent index_futures_snapshots rows.")
            per_symbol_status[symbol] = "no_input"
            continue

        try:
            out = compute_for_symbol(symbol, rows)
        except Exception as e:
            print(f"[ERR] compute failed for {symbol}: {e}")
            per_symbol_status[symbol] = "compute_failed"
            continue

        if out is None:
            per_symbol_status[symbol] = "no_rows"
            continue

        out_rows.append(out)
        per_symbol_status[symbol] = "ok"
        for k, v in out.items():
            print(f"{k}={v}")
        print("------------------------------------------------------------------------")

    if not out_rows:
        if all(s == "no_input" for s in per_symbol_status.values()) and per_symbol_status:
            return log.exit_with_reason(
                "SKIPPED_NO_INPUT", exit_code=1,
                error_message=f"No recent index_futures_snapshots for either symbol. statuses={per_symbol_status}",
            )
        return log.exit_with_reason(
            "DATA_ERROR", exit_code=1,
            error_message=f"No basis-context rows produced. statuses={per_symbol_status}",
        )

    try:
        supabase_upsert("basis_context_snapshots", out_rows, on_conflict="symbol,ts")
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1, error_message=f"upsert failed: {e}")

    log.record_write("basis_context_snapshots", len(out_rows))
    ok_symbols = [s for s, st in per_symbol_status.items() if st == "ok"]
    note = f"symbols={'+'.join(ok_symbols)}"
    if len(ok_symbols) < 2:
        missing = [s for s in ["NIFTY", "SENSEX"] if s not in ok_symbols]
        note += f" missing={'+'.join(missing)}"
    print("COMPUTE BASIS CONTEXT COMPLETED")
    return log.complete(notes=note)


if __name__ == "__main__":
    sys.exit(main())
