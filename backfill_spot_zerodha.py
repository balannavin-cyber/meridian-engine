#!/usr/bin/env python3
"""
backfill_spot_zerodha.py  --  Backfill hist_spot_bars_1m from Zerodha Kite
==========================================================================
Pulls 1-min OHLCV for NIFTY and SENSEX spot from Kite for the 4 missing
live canary sessions (Apr 7-10 2026) and upserts into MERDIAN's
hist_spot_bars_1m table.

Runs on MeridianAlpha AWS instance inside the MeridianAlpha venv.
Reads credentials from ~/meridian-alpha/.env

Requirements already in venv: kiteconnect, requests, python-dotenv

Run:
    cd ~/meridian-alpha
    source venv/bin/activate
    python backfill_spot_zerodha.py
    python backfill_spot_zerodha.py --dry-run   # preview without writing
"""

import os
import sys
import time
import requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from kiteconnect import KiteConnect

load_dotenv()

# ── Credentials ───────────────────────────────────────────────────────────────

KITE_API_KEY     = os.environ["KITE_API_KEY"]
KITE_ACCESS_TOKEN= os.environ["KITE_ACCESS_TOKEN"]
SUPABASE_URL     = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY     = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

DRY_RUN = "--dry-run" in sys.argv
IST     = ZoneInfo("Asia/Kolkata")

# ── MERDIAN instrument IDs (confirmed from instruments table) ─────────────────

INSTRUMENTS = {
    "NIFTY": {
        "kite_token":   256265,           # NSE:NIFTY 50 spot
        "merdian_id":   "9992f600-51b3-4009-b487-f878692a0bc5",
    },
    "SENSEX": {
        "kite_token":   265,              # BSE:SENSEX spot
        "merdian_id":   "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
    },
}

# ── Dates to backfill (confirmed missing trading sessions) ────────────────────

BACKFILL_DATES = [
    date(2026, 4, 7),
    date(2026, 4, 8),
    date(2026, 4, 9),
    date(2026, 4, 10),
]

# ── Market hours filter (IST) ─────────────────────────────────────────────────

MARKET_OPEN  = (9, 15)   # 09:15 IST
MARKET_CLOSE = (15, 30)  # 15:30 IST

SUPABASE_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "resolution=merge-duplicates",  # upsert mode
}

# ─────────────────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now(IST).strftime("%H:%M:%S IST")
    print(f"[{ts}] {msg}", flush=True)

def is_market_hours(dt_ist):
    h, m = dt_ist.hour, dt_ist.minute
    total = h * 60 + m
    open_min  = MARKET_OPEN[0]  * 60 + MARKET_OPEN[1]
    close_min = MARKET_CLOSE[0] * 60 + MARKET_CLOSE[1]
    return open_min <= total <= close_min

def fetch_day(kite, instrument_token, trade_date):
    """Fetch 1-min bars for a single date. Returns list of Kite bar dicts."""
    from_dt = datetime(trade_date.year, trade_date.month, trade_date.day, 9, 0)
    to_dt   = datetime(trade_date.year, trade_date.month, trade_date.day, 15, 35)
    for attempt in range(4):
        try:
            bars = kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_dt,
                to_date=to_dt,
                interval="minute",
            )
            return bars
        except Exception as e:
            if attempt == 3:
                raise
            wait = 2 ** attempt
            log(f"    Retry {attempt+1}/3 after error: {e} (wait {wait}s)")
            time.sleep(wait)

def build_rows(bars, instrument_id, trade_date):
    """Convert Kite bars to hist_spot_bars_1m rows."""
    rows = []
    for b in bars:
        # b["date"] is a datetime object from kiteconnect, in IST
        bar_ts = b["date"]
        if hasattr(bar_ts, "tzinfo") and bar_ts.tzinfo is None:
            bar_ts = bar_ts.replace(tzinfo=IST)

        if not is_market_hours(bar_ts.astimezone(IST)):
            continue

        # Confirm bar is on the expected trade date
        bar_date = bar_ts.astimezone(IST).date()
        if bar_date != trade_date:
            continue

        rows.append({
            "instrument_id":  instrument_id,
            "trade_date":     str(trade_date),
            "bar_ts":         bar_ts.astimezone(IST).isoformat(),
            "open":           float(b["open"]),
            "high":           float(b["high"]),
            "low":            float(b["low"]),
            "close":          float(b["close"]),
            "is_pre_market":  False,
        })
    return rows

def upsert_rows(rows, symbol, trade_date):
    """Upsert rows into hist_spot_bars_1m. Unique key: (instrument_id, bar_ts)."""
    if not rows:
        log(f"    No rows to write.")
        return 0

    url = f"{SUPABASE_URL}/rest/v1/hist_spot_bars_1m"
    params = {"on_conflict": "instrument_id,bar_ts"}

    # Batch in chunks of 500
    written = 0
    for i in range(0, len(rows), 500):
        chunk = rows[i:i+500]
        for attempt in range(4):
            try:
                r = requests.post(
                    url, headers=SUPABASE_HEADERS,
                    params=params, json=chunk, timeout=30
                )
                r.raise_for_status()
                written += len(chunk)
                break
            except Exception as e:
                if attempt == 3:
                    log(f"    [ERR] Upsert failed after 4 attempts: {e}")
                    raise
                time.sleep(2 ** attempt)

    return written

def verify_inserted(instrument_id, trade_date):
    """Confirm row count in hist_spot_bars_1m for this date."""
    url    = f"{SUPABASE_URL}/rest/v1/hist_spot_bars_1m"
    params = {
        "instrument_id": f"eq.{instrument_id}",
        "trade_date":    f"eq.{trade_date}",
        "select":        "bar_ts",
    }
    headers = {**SUPABASE_HEADERS, "Prefer": "count=exact"}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    count = int(r.headers.get("content-range", "0/0").split("/")[-1])
    return count

# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("backfill_spot_zerodha.py  --  MERDIAN hist_spot_bars_1m")
    print("DRY RUN -- no writes" if DRY_RUN else "LIVE -- will write to Supabase")
    print("=" * 60)

    # Init Kite
    kite = KiteConnect(api_key=KITE_API_KEY)
    kite.set_access_token(KITE_ACCESS_TOKEN)
    log("Kite client initialised.")

    # Verify profile (confirms token is valid)
    try:
        profile = kite.profile()
        log(f"Authenticated as: {profile['user_name']} ({profile['user_id']})")
    except Exception as e:
        log(f"[ERR] Kite auth failed: {e}")
        log("Run python core/refresh_kite_token.py first.")
        sys.exit(1)

    total_written = 0

    for symbol, cfg in INSTRUMENTS.items():
        log(f"\n── {symbol} ────────────────────────────────────────")
        instrument_id = cfg["merdian_id"]
        kite_token    = cfg["kite_token"]

        for td in BACKFILL_DATES:
            log(f"  {td}  fetching from Kite...")
            try:
                bars = fetch_day(kite, kite_token, td)
            except Exception as e:
                log(f"  [ERR] Fetch failed: {e} — skipping date.")
                continue

            rows = build_rows(bars, instrument_id, td)
            log(f"  {td}  {len(bars)} raw bars → {len(rows)} market-hours bars")

            if not rows:
                log(f"  [WARN] No market-hours bars — NSE may have been closed.")
                continue

            # Show sample
            log(f"  First: {rows[0]['bar_ts']}  O={rows[0]['open']} "
                f"H={rows[0]['high']} L={rows[0]['low']} C={rows[0]['close']}")
            log(f"  Last:  {rows[-1]['bar_ts']}  C={rows[-1]['close']}")

            if DRY_RUN:
                log(f"  [DRY]  Would upsert {len(rows)} rows.")
                continue

            n = upsert_rows(rows, symbol, td)
            total_written += n

            # Verify
            count = verify_inserted(instrument_id, td)
            log(f"  [OK]  {n} rows upserted. "
                f"Total in hist_spot_bars_1m for {td}: {count}")

            time.sleep(0.3)  # rate limit courtesy

    print("\n" + "=" * 60)
    if not DRY_RUN:
        print(f"Backfill complete. {total_written} rows written.")
        print("\nRun this in Supabase SQL editor to verify:")
        print("""
  SELECT trade_date, COUNT(*) AS bars,
         MIN(bar_ts::time) AS first_bar,
         MAX(bar_ts::time) AS last_bar
  FROM public.hist_spot_bars_1m
  WHERE trade_date IN ('2026-04-07','2026-04-08','2026-04-09','2026-04-10')
  GROUP BY trade_date ORDER BY trade_date;
        """)
        print("Tomorrow morning, run:")
        print("  python build_ict_htf_zones.py --timeframe D")
        print("  (builds daily zones from complete hist_spot_bars_1m)")
    print("=" * 60)


if __name__ == "__main__":
    main()
