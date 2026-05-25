#!/usr/bin/env python3
"""
backfill_option_zerodha.py  --  Backfill hist_option_bars_1m from Zerodha Kite
===============================================================================
Pulls 1-min OHLCV for NIFTY and SENSEX options from Kite for missing
trading sessions and upserts into MERDIAN's hist_option_bars_1m table.

Fetches ATM ±5 strikes for current week expiries:
- NIFTY: Weekly expiry (tomorrow if current week)  
- SENSEX: Weekly expiry (Thursday if current week)

Runs on MeridianAlpha AWS instance or Local Windows.
Reads credentials from .env file.

Usage:
    python backfill_option_zerodha.py
    python backfill_option_zerodha.py --dry-run   # preview without writing
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
KITE_API_KEY      = os.environ["KITE_API_KEY"]
KITE_ACCESS_TOKEN = os.environ["KITE_ACCESS_TOKEN"] 
SUPABASE_URL      = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY      = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

DRY_RUN = "--dry-run" in sys.argv
IST     = ZoneInfo("Asia/Kolkata")

# ── Base instruments (for ATM price discovery) ────────────────────────────────
SPOT_INSTRUMENTS = {
    "NIFTY": {"kite_token": 256265},   # NSE:NIFTY 50 spot
    "SENSEX": {"kite_token": 265},     # BSE:SENSEX spot  
}

# ── Configuration ─────────────────────────────────────────────────────────────
STRIKE_RANGE = 5        # ATM ±5 strikes
MIN_DTE = 0            # Include expiry day
MAX_DTE = 7            # Within 1 week

# ── Dates to backfill ────────────────────────────────────────────────────────
BACKFILL_DATES = [
    date(2026, 5, 4),   # Add dates with missing option data
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
    open_min  = MARKET_OPEN[0] * 60 + MARKET_OPEN[1]
    close_min = MARKET_CLOSE[0] * 60 + MARKET_CLOSE[1]
    return open_min <= total <= close_min

def get_atm_strike(spot_price, symbol):
    """Round to nearest ATM strike based on symbol conventions."""
    if symbol == "NIFTY":
        return round(spot_price / 50) * 50
    elif symbol == "SENSEX":
        return round(spot_price / 100) * 100
    else:
        raise ValueError(f"Unknown symbol: {symbol}")

def get_option_instruments(kite, symbol, trade_date):
    """Get option instrument tokens for symbol around ATM strikes."""
    
    # Get current spot price for ATM calculation
    spot_token = SPOT_INSTRUMENTS[symbol]["kite_token"]
    
    try:
        # Get spot price from yesterday's close or current LTP
        spot_data = kite.ltp([spot_token])
        spot_price = list(spot_data.values())[0]["last_price"]
        log(f"  {symbol} spot price: {spot_price}")
    except Exception as e:
        log(f"  Failed to get {symbol} spot price: {e}")
        return []
    
    atm_strike = get_atm_strike(spot_price, symbol)
    log(f"  ATM strike: {atm_strike}")
    
    # Get full instrument list for options
    if symbol == "NIFTY":
        exchange = "NFO"
        instruments = kite.instruments(exchange)
    else:  # SENSEX 
        exchange = "BFO"
        instruments = kite.instruments(exchange)
    
    # Filter for our symbol's options
    option_instruments = []
    
    for inst in instruments:
        if inst["name"] != symbol:
            continue
        if inst["instrument_type"] not in ["CE", "PE"]:
            continue
        
        # Parse expiry date
        try:
            expiry = datetime.strptime(inst["expiry"], "%Y-%m-%d").date()
        except:
            continue
        
        # Check DTE range
        dte = (expiry - trade_date).days
        if not (MIN_DTE <= dte <= MAX_DTE):
            continue
            
        # Check strike range  
        strike = float(inst["strike"])
        strike_diff = abs(strike - atm_strike)
        
        if symbol == "NIFTY":
            max_diff = STRIKE_RANGE * 50  # ±5 strikes × 50 points
        else:  # SENSEX
            max_diff = STRIKE_RANGE * 100  # ±5 strikes × 100 points
            
        if strike_diff <= max_diff:
            option_instruments.append({
                "instrument_token": inst["instrument_token"],
                "trading_symbol": inst["tradingsymbol"],
                "strike": strike,
                "opt_type": inst["instrument_type"],
                "expiry_date": expiry,
                "exchange": inst["exchange"],
            })
    
    log(f"  Found {len(option_instruments)} option instruments")
    return option_instruments

def fetch_day_option(kite, instrument, trade_date):
    """Fetch 1-min bars for a single option on a single date."""
    
    from_dt = datetime(trade_date.year, trade_date.month, trade_date.day, 9, 0)
    to_dt   = datetime(trade_date.year, trade_date.month, trade_date.day, 15, 35)
    
    for attempt in range(4):
        try:
            bars = kite.historical_data(
                instrument_token=instrument["instrument_token"],
                from_date=from_dt,
                to_date=to_dt,
                interval="minute",
            )
            
            # Filter to market hours only
            market_bars = []
            for bar in bars:
                dt_ist = bar["date"].replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)
                if is_market_hours(dt_ist):
                    market_bars.append(bar)
            
            return market_bars
            
        except Exception as e:
            if attempt == 3:
                log(f"    Failed after 4 attempts: {e}")
                return []
            log(f"    Attempt {attempt+1} failed: {e}, retrying...")
            time.sleep(2 ** attempt)

def upsert_option_bars(bars, instrument, symbol, trade_date):
    """Upsert option bars to Supabase hist_option_bars_1m table."""
    
    if not bars:
        return 0
        
    # Convert Kite bars to Supabase format
    rows = []
    for bar in bars:
        dt_utc = bar["date"].replace(tzinfo=ZoneInfo("UTC"))
        dt_ist = dt_utc.astimezone(IST)
        
        row = {
            "trade_date": trade_date.isoformat(),
            "bar_ts": dt_utc.isoformat(),
            "symbol": symbol,
            "strike_price": instrument["strike"],
            "opt_type": instrument["opt_type"],
            "expiry_date": instrument["expiry_date"].isoformat(),
            "exchange": instrument["exchange"],
            "trading_symbol": instrument["trading_symbol"],
            "open": bar["open"],
            "high": bar["high"], 
            "low": bar["low"],
            "close": bar["close"],
            "volume": bar["volume"],
        }
        rows.append(row)
    
    if DRY_RUN:
        log(f"    [DRY RUN] Would write {len(rows)} bars")
        return len(rows)
    
    # Upsert to Supabase
    url = f"{SUPABASE_URL}/rest/v1/hist_option_bars_1m"
    
    # Use conflict resolution on (trading_symbol, bar_ts) 
    params = {"on_conflict": "trading_symbol,bar_ts"}
    
    response = requests.post(url, headers=SUPABASE_HEADERS, json=rows, params=params)
    
    if response.status_code in [200, 201]:
        return len(rows)
    else:
        log(f"    Supabase error: {response.status_code} {response.text}")
        return 0

def main():
    print("=" * 60)
    print("backfill_option_zerodha.py  --  MERDIAN hist_option_bars_1m")
    print("LIVE -- will write to Supabase" if not DRY_RUN else "DRY RUN -- preview only")
    print("=" * 60)
    
    # Initialize Kite client
    kite = KiteConnect(api_key=KITE_API_KEY)
    kite.set_access_token(KITE_ACCESS_TOKEN)
    
    log("Kite client initialised.")
    
    # Verify authentication
    try:
        profile = kite.profile()
        log(f"Authenticated as: {profile['user_name']} ({profile['user_id']})")
    except Exception as e:
        log(f"Authentication failed: {e}")
        return 1
    
    total_rows = 0
    
    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} " + "─" * (50 - len(symbol)))
        
        for trade_date in BACKFILL_DATES:
            log(f"  {trade_date}  discovering option instruments...")
            
            # Get option instruments for this symbol/date
            instruments = get_option_instruments(kite, symbol, trade_date)
            
            if not instruments:
                log(f"  No option instruments found for {symbol} on {trade_date}")
                continue
                
            symbol_rows = 0
            
            for instrument in instruments:
                trading_symbol = instrument["trading_symbol"]
                log(f"    {trading_symbol}  fetching from Kite...")
                
                # Fetch bars
                bars = fetch_day_option(kite, instrument, trade_date)
                
                if not bars:
                    log(f"    {trading_symbol}  no bars returned")
                    continue
                
                log(f"    {trading_symbol}  {len(bars)} market-hours bars")
                log(f"    First: {trade_date}T09:15:00+05:30  O={bars[0]['open']} H={bars[0]['high']} L={bars[0]['low']} C={bars[0]['close']}")
                if len(bars) > 1:
                    log(f"    Last:  {trade_date}T15:29:00+05:30  C={bars[-1]['close']}")
                
                # Upsert to database
                written = upsert_option_bars(bars, instrument, symbol, trade_date)
                symbol_rows += written
                
                if written > 0:
                    log(f"    [OK]  {written} rows upserted.")
                
                # Rate limiting
                time.sleep(0.1)
                
            log(f"  {symbol} {trade_date} total: {symbol_rows} rows")
            total_rows += symbol_rows
    
    print("=" * 60)
    print(f"Backfill complete. {total_rows} rows written.")
    
    if not DRY_RUN:
        print("\nRun this in Supabase SQL editor to verify:")
        print("  SELECT trade_date, symbol, opt_type, COUNT(*) AS bars")
        print("  FROM hist_option_bars_1m") 
        print("  WHERE trade_date = '2026-05-04'")
        print("  GROUP BY trade_date, symbol, opt_type")
        print("  ORDER BY trade_date, symbol, opt_type;")
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
