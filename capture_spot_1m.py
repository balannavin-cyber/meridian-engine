#!/usr/bin/env python3
"""
capture_spot_1m.py  --  ENH-36: Live 1-min spot bar writer
===========================================================
Captures NIFTY + SENSEX spot from Dhan IDX_I every minute and writes:
  1. market_spot_snapshots  -- live spot (feeds signal dashboard)
  2. hist_spot_bars_1m      -- synthetic 1-min OHLC bar (feeds ICT detector)

Synthetic bar convention: O = H = L = C = spot (single price per minute)
Bar timestamp is truncated to the minute boundary.

Schedule via Windows Task Scheduler:
  Program:   python
  Arguments: C:\GammaEnginePython\capture_spot_1m.py
  Start in:  C:\GammaEnginePython
  Trigger:   Daily, repeat every 1 minute from 09:14 to 15:31 IST, Mon-Fri

Run manually:
    python capture_spot_1m.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Dict, List

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL     = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY     = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
DHAN_CLIENT_ID   = os.getenv("DHAN_CLIENT_ID", "").strip()
DHAN_API_TOKEN   = os.getenv("DHAN_API_TOKEN", "").strip()

DHAN_LTP_URL     = "https://api.dhan.co/v2/marketfeed/ltp"
TIMEOUT          = 30
MAX_RETRIES      = 4

# Instrument IDs confirmed from instruments table
INSTRUMENTS = {
    "NIFTY": {
        "exchange_segment": "IDX_I",
        "security_id":      13,
        "instrument_id":    "9992f600-51b3-4009-b487-f878692a0bc5",
    },
    "SENSEX": {
        "exchange_segment": "IDX_I",
        "security_id":      51,
        "instrument_id":    "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
    },
}

# ── Supabase helpers ──────────────────────────────────────────────────────────

def sb_headers():
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }

def sb_insert(table: str, rows: List[Dict]) -> None:
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=sb_headers(),
        json=rows,
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase INSERT {table} failed: {r.status_code} {r.text[:200]}")

def sb_upsert(table: str, rows: List[Dict], on_conflict: str) -> None:
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**sb_headers(), "Prefer": "resolution=merge-duplicates"},
        params={"on_conflict": on_conflict},
        json=rows,
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase UPSERT {table} failed: {r.status_code} {r.text[:200]}")

# ── Dhan IDX_I fetch (identical pattern to capture_market_spot_snapshot_local.py) ─

def fetch_spots() -> Dict[str, float]:
    """Fetch NIFTY + SENSEX LTP from Dhan IDX_I. Returns {symbol: price}."""
    payload = {}
    for cfg in INSTRUMENTS.values():
        payload.setdefault(cfg["exchange_segment"], []).append(cfg["security_id"])

    headers = {
        "Accept":        "application/json",
        "Content-Type":  "application/json",
        "access-token":  DHAN_API_TOKEN,
        "client-id":     DHAN_CLIENT_ID,
    }

    backoff = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        r = requests.post(DHAN_LTP_URL, headers=headers, json=payload, timeout=TIMEOUT)
        if r.status_code == 200:
            body = r.json()
            if body.get("status") == "success":
                spots = {}
                for symbol, cfg in INSTRUMENTS.items():
                    seg  = cfg["exchange_segment"]
                    sid  = str(cfg["security_id"])
                    price = body["data"][seg][sid]["last_price"]
                    spots[symbol] = float(price)
                return spots
            raise RuntimeError(f"Dhan non-success: {r.text[:200]}")
        if r.status_code == 429:
            if attempt < MAX_RETRIES:
                print(f"  [429] Rate limit, retry {attempt}/{MAX_RETRIES} in {backoff:.0f}s")
                time.sleep(backoff); backoff *= 2; continue
        raise RuntimeError(f"Dhan HTTP {r.status_code}: {r.text[:200]}")

    raise RuntimeError("Dhan fetch failed after all retries")

# ── Bar timestamp: truncate to minute boundary ────────────────────────────────

def bar_ts_minute(ts: datetime) -> str:
    """Truncate datetime to the minute, return ISO string with UTC tz."""
    truncated = ts.replace(second=0, microsecond=0)
    return truncated.isoformat()

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    for var, val in [("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
                     ("DHAN_CLIENT_ID", DHAN_CLIENT_ID), ("DHAN_API_TOKEN", DHAN_API_TOKEN)]:
        if not val:
            print(f"[ERROR] Missing {var}", file=sys.stderr)
            return 1

    now_utc    = datetime.now(timezone.utc)
    bar_ts     = bar_ts_minute(now_utc)
    trade_date = str(now_utc.astimezone(
        __import__('zoneinfo').ZoneInfo("Asia/Kolkata")).date())
    capture_ts = now_utc.isoformat()

    print(f"[{now_utc.strftime('%H:%M:%S UTC')}] capture_spot_1m.py")

    # ── Holiday gate (ENH-36 fix) ─────────────────────────────────────────────
    # Check trading_calendar before hitting Dhan API.
    # Exit 0 cleanly on holidays — no data written, no error logged.
    try:
        from zoneinfo import ZoneInfo as _ZI
        _today = str(datetime.now(timezone.utc).astimezone(_ZI("Asia/Kolkata")).date())
        _cal_url = f"{SUPABASE_URL}/rest/v1/trading_calendar"
        _cal_r = requests.get(
            _cal_url,
            headers=sb_headers(),
            params={"trade_date": f"eq.{_today}", "select": "is_open,open_time"},
            timeout=10,
        )
        if _cal_r.status_code == 200:
            _rows = _cal_r.json()
            if _rows:
                _row = _rows[0]
                if not _row.get("is_open", True) or _row.get("open_time") is None:
                    print(f"[{_today}] Market holiday — capture_spot_1m exiting cleanly.")
                    return 0
            # No row in calendar: allow run (merdian_start.py will upsert later)
    except Exception as _e:
        print(f"  [WARN] Calendar check failed (proceeding): {_e}")
    # ── End holiday gate ───────────────────────────────────────────────────────


    try:
        spots = fetch_spots()
    except Exception as e:
        print(f"  [ERROR] Dhan fetch failed: {e}", file=sys.stderr)
        return 1

    # ── 1. Write to market_spot_snapshots ─────────────────────────────────────
    snap_rows = []
    for symbol, spot in spots.items():
        print(f"  {symbol}: {spot}")
        snap_rows.append({
            "ts":           capture_ts,
            "symbol":       symbol,
            "spot":         spot,
            "source_table": "dhan_idx_i",
            "raw": {
                "provider":         "dhan",
                "endpoint":         "marketfeed/ltp",
                "exchange_segment": INSTRUMENTS[symbol]["exchange_segment"],
                "security_id":      INSTRUMENTS[symbol]["security_id"],
                "source_script":    "capture_spot_1m",
            },
        })

    try:
        sb_insert("market_spot_snapshots", snap_rows)
        print(f"  market_spot_snapshots: {len(snap_rows)} rows inserted")
    except Exception as e:
        print(f"  [WARN] market_spot_snapshots write failed: {e}", file=sys.stderr)

    # ── 2. Write synthetic 1-min bar to hist_spot_bars_1m ─────────────────────
    bar_rows = []
    for symbol, spot in spots.items():
        bar_rows.append({
            "instrument_id": INSTRUMENTS[symbol]["instrument_id"],
            "trade_date":    trade_date,
            "bar_ts":        bar_ts,
            "open":          spot,
            "high":          spot,
            "low":           spot,
            "close":         spot,
            "is_pre_market": False,
        })

    try:
        sb_upsert("hist_spot_bars_1m", bar_rows, on_conflict="instrument_id,bar_ts")
        print(f"  hist_spot_bars_1m:     {len(bar_rows)} rows upserted (bar_ts={bar_ts[:16]})")
    except Exception as e:
        print(f"  [WARN] hist_spot_bars_1m write failed: {e}", file=sys.stderr)

    print(f"  Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
