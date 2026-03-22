from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

# ✅ ADD THIS (critical fix)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


UTC = timezone.utc


def get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def supabase_select(table: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
    url = get_env("SUPABASE_URL").rstrip("/") + f"/rest/v1/{table}?{urlencode(params)}"
    key = get_env("SUPABASE_SERVICE_ROLE_KEY")

    resp = requests.get(
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
        },
        timeout=60,
    )

    if resp.status_code >= 400:
        raise RuntimeError(resp.text)

    return resp.json()


def supabase_insert(table: str, rows: List[Dict[str, Any]]) -> None:
    url = get_env("SUPABASE_URL").rstrip("/") + f"/rest/v1/{table}"
    key = get_env("SUPABASE_SERVICE_ROLE_KEY")

    resp = requests.post(
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=rows,
        timeout=60,
    )

    if resp.status_code >= 400:
        raise RuntimeError(resp.text)


def get_latest_signals(symbol: str):
    return supabase_select(
        "signal_snapshots",
        {
            "select": "*",
            "symbol": f"eq.{symbol}",
            "order": "ts.desc",
            "limit": "20",
        },
    )


def get_shadow_signals(symbol: str):
    return supabase_select(
        "shadow_signal_snapshots_v3",
        {
            "select": "*",
            "symbol": f"eq.{symbol}",
            "order": "ts.desc",
            "limit": "20",
        },
    )


def get_spot_at(symbol: str, ts: str):
    rows = supabase_select(
        "intraday_ohlc",
        {
            "select": "close",
            "symbol": f"eq.{symbol}",
            "ts": f"gte.{ts}",
            "order": "ts.asc",
            "limit": "1",
        },
    )
    return float(rows[0]["close"]) if rows else None


def classify_correct(action: str, move: float) -> Optional[bool]:
    if action == "BUY_CE":
        return move > 0
    if action == "BUY_PE":
        return move < 0
    if action == "DO_NOTHING":
        return abs(move) < 0.2
    return None


def evaluate_symbol(symbol: str):
    live = get_latest_signals(symbol)
    shadow = get_shadow_signals(symbol)

    shadow_map = {row["ts"]: row for row in shadow}

    rows_to_insert = []

    for l in live:
        ts = l["ts"]
        s = shadow_map.get(ts)

        if not s:
            continue

        spot_now = get_spot_at(symbol, ts)
        if spot_now is None:
            continue

        ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))

        spot_30 = get_spot_at(symbol, (ts_dt + timedelta(minutes=30)).isoformat())
        spot_60 = get_spot_at(symbol, (ts_dt + timedelta(minutes=60)).isoformat())

        if not spot_30 or not spot_60:
            continue

        move_30 = spot_30 - spot_now
        move_60 = spot_60 - spot_now

        row = {
            "ts": ts,
            "symbol": symbol,
            "live_action": l.get("action"),
            "shadow_action": s.get("action"),
            "spot_at_signal": spot_now,
            "spot_after_30m": spot_30,
            "spot_after_60m": spot_60,
            "move_30m": move_30,
            "move_60m": move_60,
            "live_correct_30m": classify_correct(l.get("action"), move_30),
            "shadow_correct_30m": classify_correct(s.get("action"), move_30),
            "live_correct_60m": classify_correct(l.get("action"), move_60),
            "shadow_correct_60m": classify_correct(s.get("action"), move_60),
        }

        rows_to_insert.append(row)

    if rows_to_insert:
        supabase_insert("shadow_vs_live_evaluation", rows_to_insert)
        print(f"Inserted {len(rows_to_insert)} rows for {symbol}")


def main():
    for symbol in ["NIFTY", "SENSEX"]:
        evaluate_symbol(symbol)


if __name__ == "__main__":
    main()