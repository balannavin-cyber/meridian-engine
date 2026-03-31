from __future__ import annotations

import json
import os
import sys
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    sys.exit(1)

SUPABASE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

SIGNAL_FETCH_LIMIT = 1000
UPSERT_BATCH_SIZE = 500


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def jdump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def supabase_table_url(table_name: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table_name}"


def http_get(url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
    r = requests.get(url, headers=SUPABASE_HEADERS, params=params or {}, timeout=60)
    r.raise_for_status()
    return r


def http_post(url: str, json_body: Any, params: Optional[Dict[str, Any]] = None) -> requests.Response:
    r = requests.post(url, headers=SUPABASE_HEADERS, params=params or {}, json=json_body, timeout=120)
    r.raise_for_status()
    return r


def parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def get_recent_signals(limit: int = SIGNAL_FETCH_LIMIT) -> List[Dict[str, Any]]:
    url = supabase_table_url("signal_snapshots")
    params = {
        "select": (
            "id,ts,symbol,action,direction_bias,confidence_score,"
            "gamma_regime,breadth_regime,flip_distance,spot"
        ),
        "order": "ts.desc",
        "limit": str(limit),
    }
    r = http_get(url, params=params)
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"signal_snapshots response is not a list: {jdump(data)}")
    return data


def get_logged_signal_ids() -> set[int]:
    url = supabase_table_url("signal_regret_log")
    params = {
        "select": "signal_snapshot_id",
        "limit": "10000",
    }
    r = http_get(url, params=params)
    data = r.json()
    if not isinstance(data, list):
        return set()

    out: set[int] = set()
    for row in data:
        try:
            out.add(int(row["signal_snapshot_id"]))
        except Exception:
            continue
    return out


def get_unlogged_signals(limit: int = SIGNAL_FETCH_LIMIT) -> List[Dict[str, Any]]:
    recent = get_recent_signals(limit=limit)
    logged_ids = get_logged_signal_ids()

    out: List[Dict[str, Any]] = []
    for row in recent:
        try:
            signal_id = int(row["id"])
        except Exception:
            continue
        if signal_id not in logged_ids:
            out.append(row)
    out.sort(key=lambda r: str(r.get("ts") or ""))
    return out


def fetch_spot_rows_for_symbol(symbol: str, start_ts: datetime, end_ts: datetime) -> List[Dict[str, Any]]:
    url = supabase_table_url("market_spot_snapshots")
    params = {
        "select": "ts,spot",
        "symbol": f"eq.{symbol}",
        "ts": f"gte.{start_ts.isoformat()}",
        "order": "ts.asc",
        "limit": "10000",
    }

    r = http_get(url, params=params)
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"market_spot_snapshots response is not a list for {symbol}: {jdump(data)}")

    out: List[Dict[str, Any]] = []
    for row in data:
        ts_val = parse_ts(row.get("ts"))
        if ts_val is None:
            continue
        if ts_val > end_ts:
            break
        out.append(
            {
                "ts": ts_val,
                "spot": safe_float(row.get("spot")),
            }
        )
    return out


def build_spot_index(spot_rows: List[Dict[str, Any]]) -> Tuple[List[datetime], List[Optional[float]]]:
    ts_list: List[datetime] = []
    spot_list: List[Optional[float]] = []

    for row in spot_rows:
        ts_val = row["ts"]
        spot_val = row["spot"]
        ts_list.append(ts_val)
        spot_list.append(spot_val)

    return ts_list, spot_list


def first_spot_at_or_after(
    ts_list: List[datetime],
    spot_list: List[Optional[float]],
    target_ts: datetime,
) -> Optional[float]:
    idx = bisect_left(ts_list, target_ts)
    while idx < len(ts_list):
        val = spot_list[idx]
        if val is not None:
            return val
        idx += 1
    return None


def pct_move(from_spot: Optional[float], to_spot: Optional[float]) -> Optional[float]:
    if from_spot is None or to_spot is None:
        return None
    if from_spot == 0:
        return None
    return ((to_spot - from_spot) / from_spot) * 100.0


def direction_correct(action: str, move_pct: Optional[float]) -> Optional[bool]:
    if move_pct is None:
        return None

    action_u = str(action or "").upper()
    if action_u == "BUY_CE":
        return move_pct > 0
    if action_u == "BUY_PE":
        return move_pct < 0
    if action_u == "DO_NOTHING":
        return None
    return None


def build_symbol_spot_cache(signal_rows: List[Dict[str, Any]]) -> Dict[str, Tuple[List[datetime], List[Optional[float]]]]:
    by_symbol: Dict[str, List[datetime]] = {}

    for s in signal_rows:
        symbol = str(s.get("symbol") or "").strip().upper()
        signal_ts = parse_ts(s.get("ts"))
        if not symbol or signal_ts is None:
            continue
        by_symbol.setdefault(symbol, []).append(signal_ts)

    cache: Dict[str, Tuple[List[datetime], List[Optional[float]]]] = {}

    for symbol, ts_values in by_symbol.items():
        start_ts = min(ts_values) - timedelta(minutes=1)
        end_ts = max(ts_values) + timedelta(minutes=61)

        spot_rows = fetch_spot_rows_for_symbol(symbol, start_ts, end_ts)
        ts_list, spot_list = build_spot_index(spot_rows)
        cache[symbol] = (ts_list, spot_list)

        print(
            f"Spot cache built | symbol={symbol} | rows={len(spot_rows)} | "
            f"window={start_ts.isoformat()} -> {end_ts.isoformat()}"
        )

    return cache


def build_regret_rows(signal_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    spot_cache = build_symbol_spot_cache(signal_rows)

    for s in signal_rows:
        try:
            signal_id = int(s["id"])
        except Exception:
            continue

        symbol = str(s.get("symbol") or "").strip().upper()
        action = str(s.get("action") or "").strip()
        signal_ts = parse_ts(s.get("ts"))
        spot_at_signal = safe_float(s.get("spot"))

        if not symbol or not action or signal_ts is None:
            continue

        ts_15m = signal_ts + timedelta(minutes=15)
        ts_30m = signal_ts + timedelta(minutes=30)
        ts_60m = signal_ts + timedelta(minutes=60)

        ts_list, spot_list = spot_cache.get(symbol, ([], []))

        spot_15m = first_spot_at_or_after(ts_list, spot_list, ts_15m)
        spot_30m = first_spot_at_or_after(ts_list, spot_list, ts_30m)
        spot_60m = first_spot_at_or_after(ts_list, spot_list, ts_60m)

        move_15m_pct = pct_move(spot_at_signal, spot_15m)
        move_30m_pct = pct_move(spot_at_signal, spot_30m)
        move_60m_pct = pct_move(spot_at_signal, spot_60m)

        row = {
            "signal_snapshot_id": signal_id,
            "symbol": symbol,
            "signal_ts": signal_ts.isoformat(),
            "action": action,
            "direction_bias": s.get("direction_bias"),
            "confidence_score": s.get("confidence_score"),
            "gamma_regime": s.get("gamma_regime"),
            "breadth_regime": s.get("breadth_regime"),
            "flip_distance_raw": s.get("flip_distance"),
            "spot_at_signal": spot_at_signal,
            "spot_at_15m": spot_15m,
            "spot_at_30m": spot_30m,
            "spot_at_60m": spot_60m,
            "move_15m_pct": move_15m_pct,
            "move_30m_pct": move_30m_pct,
            "move_60m_pct": move_60m_pct,
            "direction_was_correct": direction_correct(action, move_60m_pct),
            "labeller_version": "v1",
            "created_at": utc_now_iso(),
        }
        rows.append(row)

    return rows


def chunked(items: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def upsert_regret_rows(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    url = supabase_table_url("signal_regret_log")
    headers = dict(SUPABASE_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"

    for batch in chunked(rows, UPSERT_BATCH_SIZE):
        r = requests.post(
            url,
            headers=headers,
            params={"on_conflict": "signal_snapshot_id"},
            json=batch,
            timeout=120,
        )
        r.raise_for_status()
        print(f"Upserted batch size: {len(batch)}")


def main() -> None:
    print("=" * 72)
    print("MERDIAN - build_signal_regret_log_v1")
    print("=" * 72)

    signal_rows = get_unlogged_signals(limit=SIGNAL_FETCH_LIMIT)
    print(f"Signals to process: {len(signal_rows)}")

    regret_rows = build_regret_rows(signal_rows)
    print(f"Regret rows built : {len(regret_rows)}")

    upsert_regret_rows(regret_rows)

    print("DONE")


if __name__ == "__main__":
    main()