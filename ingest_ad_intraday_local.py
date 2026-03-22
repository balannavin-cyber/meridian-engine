import json
import os
import sys
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from trading_calendar import is_trading_day, get_today_session

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN", "")
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY or not DHAN_API_TOKEN or not DHAN_CLIENT_ID:
    print("ERROR: Missing SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DHAN_API_TOKEN, or DHAN_CLIENT_ID in .env")
    sys.exit(1)

SUPABASE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

DHAN_LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
PAGE_SIZE = 1000
LTP_CHUNK_SIZE = 1000
SLEEP_BETWEEN_CHUNKS_SEC = 1.1

DATA_DIR = Path(r"C:\GammaEnginePython\data")
CURRENT_SESSION_FILE = DATA_DIR / "ad_points_current_session.jsonl"
DAILY_SUMMARY_FILE = DATA_DIR / "ad_daily_summary.jsonl"
ARCHIVE_DIR = DATA_DIR / "archive"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def table_url(name: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{name}"


def get_json(url: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    r = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f"Expected list response from {url}, got {type(data)}")
    return data


def get_active_nse_universe_all() -> List[Dict[str, Any]]:
    all_rows: List[Dict[str, Any]] = []
    offset = 0

    while True:
        params = {
            "select": "ticker,dhan_security_id",
            "exchange": "eq.NSE",
            "is_active": "eq.true",
            "dhan_security_id": "not.is.null",
            "order": "ticker.asc",
            "offset": str(offset),
            "limit": str(PAGE_SIZE),
        }
        rows = get_json(table_url("dhan_scrip_map"), params=params)
        print(f"Universe page fetched | offset={offset} | rows={len(rows)}")

        if not rows:
            break

        for row in rows:
            try:
                all_rows.append({
                    "ticker": row["ticker"],
                    "security_id": int(str(row["dhan_security_id"]).strip())
                })
            except Exception:
                continue

        if len(rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return all_rows


def get_latest_eod_date() -> str:
    rows = get_json(table_url("breadth_coverage_latest"))
    if not rows or not rows[0].get("trade_date"):
        raise RuntimeError("Could not determine latest EOD trade_date from breadth_coverage_latest")
    return rows[0]["trade_date"]


def get_prev_close_map(latest_trade_date: str) -> Dict[str, float]:
    """
    Use breadth_indicators_daily as baseline because it already stores prev_close.
    """
    prev_close_map: Dict[str, float] = {}
    offset = 0

    while True:
        params = {
            "select": "ticker,prev_close",
            "trade_date": f"eq.{latest_trade_date}",
            "universe_id": "eq.excel_v1",
            "order": "ticker.asc",
            "offset": str(offset),
            "limit": str(PAGE_SIZE),
        }
        rows = get_json(table_url("breadth_indicators_daily"), params=params)
        print(f"Prev-close page fetched | offset={offset} | rows={len(rows)}")

        if not rows:
            break

        for row in rows:
            try:
                ticker = row["ticker"]
                prev_close = row.get("prev_close")
                if ticker and prev_close is not None:
                    prev_close_map[ticker] = float(prev_close)
            except Exception:
                continue

        if len(rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return prev_close_map


def chunk_list(items: List[Any], size: int) -> List[List[Any]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def fetch_dhan_ltp_chunk(security_ids: List[int]) -> Dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_API_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }
    body = {"NSE_EQ": security_ids}

    r = requests.post(DHAN_LTP_URL, headers=headers, json=body, timeout=120)
    text = r.text

    if not r.ok:
        raise RuntimeError(f"Dhan LTP HTTP {r.status_code}: {text[:500]}")

    data = r.json()
    if data.get("status") and data["status"] != "success":
        raise RuntimeError(f"Dhan LTP status not success: {text[:500]}")

    return data


def extract_ltp_map(dhan_json: Dict[str, Any]) -> Dict[int, float]:
    bucket = dhan_json.get("data", {}).get("NSE_EQ", {})
    out: Dict[int, float] = {}

    if not isinstance(bucket, dict):
        return out

    for sid_str, payload in bucket.items():
        try:
            sid = int(sid_str)
            last_price = float(payload.get("last_price"))
            out[sid] = last_price
        except Exception:
            continue

    return out


def read_current_session_points() -> List[Dict[str, Any]]:
    if not CURRENT_SESSION_FILE.exists():
        return []

    points: List[Dict[str, Any]] = []
    with open(CURRENT_SESSION_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                points.append(json.loads(line))
            except Exception:
                continue
    return points


def append_current_session_point(point: Dict[str, Any]) -> None:
    with open(CURRENT_SESSION_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(point, ensure_ascii=False) + "\n")


def write_daily_summary(summary: Dict[str, Any]) -> None:
    with open(DAILY_SUMMARY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")


def archive_and_reset_if_new_session(today_str: str) -> None:
    points = read_current_session_points()
    if not points:
        return

    existing_session_date = points[0].get("session_date")
    if existing_session_date == today_str:
        return

    # build compact summary for the old session
    advances = [p.get("advances", 0) for p in points]
    declines = [p.get("declines", 0) for p in points]
    ad_line = [p.get("ad_line", 0) for p in points]

    summary = {
        "session_date": existing_session_date,
        "points_count": len(points),
        "open_advances": advances[0] if advances else None,
        "open_declines": declines[0] if declines else None,
        "close_advances": advances[-1] if advances else None,
        "close_declines": declines[-1] if declines else None,
        "high_ad_line": max(ad_line) if ad_line else None,
        "low_ad_line": min(ad_line) if ad_line else None,
        "archived_at": utc_now_iso(),
    }
    write_daily_summary(summary)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARCHIVE_DIR / f"ad_points_{existing_session_date}.jsonl"
    CURRENT_SESSION_FILE.replace(archive_path)


def main() -> None:
    print("=" * 72)
    print("Gamma Engine - Local Python ingest_ad_intraday")
    print("=" * 72)

    if not is_trading_day():
        print("Today is not an open trading session according to trading_calendar.json")
        sys.exit(0)

    session = get_today_session()
    today_str = session["date"]
    archive_and_reset_if_new_session(today_str)

    latest_trade_date = get_latest_eod_date()
    print(f"Latest EOD trade date: {latest_trade_date}")

    universe = get_active_nse_universe_all()
    print(f"Active mapped NSE tickers: {len(universe)}")

    prev_close_map = get_prev_close_map(latest_trade_date)
    print(f"Prev-close map size: {len(prev_close_map)}")

    chunks = chunk_list(universe, LTP_CHUNK_SIZE)
    print(f"LTP chunk count: {len(chunks)}")

    ltp_map: Dict[int, float] = {}
    for idx, chunk in enumerate(chunks, start=1):
        security_ids = [x["security_id"] for x in chunk]
        print(f"Fetching chunk {idx}/{len(chunks)} | securities={len(security_ids)}")
        data = fetch_dhan_ltp_chunk(security_ids)
        chunk_ltp = extract_ltp_map(data)
        ltp_map.update(chunk_ltp)
        print(f"[OK] chunk {idx} | ltp_received={len(chunk_ltp)}")

        if idx < len(chunks):
            time.sleep(SLEEP_BETWEEN_CHUNKS_SEC)

    advances = 0
    declines = 0
    unchanged = 0
    matched = 0

    for item in universe:
        ticker = item["ticker"]
        sid = item["security_id"]

        prev_close = prev_close_map.get(ticker)
        last_price = ltp_map.get(sid)

        if prev_close is None or last_price is None:
            continue

        matched += 1

        if last_price > prev_close:
            advances += 1
        elif last_price < prev_close:
            declines += 1
        else:
            unchanged += 1

    ad_line = advances - declines
    ad_ratio = round((advances / declines), 4) if declines > 0 else None

    point = {
        "ts": utc_now_iso(),
        "session_date": today_str,
        "universe_id": "excel_v1",
        "active_universe": len(universe),
        "matched_universe": matched,
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "ad_line": ad_line,
        "ad_ratio": ad_ratio,
        "latest_eod_trade_date": latest_trade_date,
    }

    append_current_session_point(point)

    print("-" * 72)
    print("Run complete")
    print(f"Session date     : {today_str}")
    print(f"Active universe  : {len(universe)}")
    print(f"Matched universe : {matched}")
    print(f"Advances         : {advances}")
    print(f"Declines         : {declines}")
    print(f"Unchanged        : {unchanged}")
    print(f"A/D line         : {ad_line}")
    print(f"A/D ratio        : {ad_ratio}")
    print(f"Point appended to: {CURRENT_SESSION_FILE}")


if __name__ == "__main__":
    main()