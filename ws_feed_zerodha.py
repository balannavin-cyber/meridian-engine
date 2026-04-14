#!/usr/bin/env python3
"""
ws_feed_zerodha.py  --  MERDIAN Zerodha WebSocket Feed (ENH-51a)
================================================================
Connects to Zerodha KiteTicker and streams live market data to Supabase.

Instruments subscribed at startup:
  - NIFTY 50 spot      (NSE:NIFTY 50)
  - NIFTY BANK spot    (NSE:NIFTY BANK)   [optional, for breadth context]
  - NFO option chain   current weekly expiry, all strikes CE+PE
  - NFO futures        front-month NIFTY + SENSEX

For SENSEX: Dhan REST pipeline continues unchanged (Zerodha has no BSE F&O).

Writes to: MERDIAN Supabase → public.market_ticks

Token: reads ZERODHA_API_KEY + ZERODHA_ACCESS_TOKEN from .env
       Run core/refresh_kite_token.py each morning before starting this.

Run:
    python ws_feed_zerodha.py                    # all instruments
    python ws_feed_zerodha.py --spot-only        # spot only (testing)
    python ws_feed_zerodha.py --dry-run          # print ticks, no DB write

Cron (start at 09:14 IST, stop at 15:32 IST):
    14 3 * * 1-5 cd /home/ssm-user/meridian-engine && /bin/bash -lc \
        'set -a; . ./.env; set +a; python3 ws_feed_zerodha.py >> logs/ws_feed.log 2>&1 &'
    32 10 * * 1-5 pkill -f ws_feed_zerodha.py
"""

import os, sys, time, json, math, logging
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from threading import Thread, Event
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from kiteconnect import KiteTicker, KiteConnect

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY      = os.environ["ZERODHA_API_KEY"]
ACCESS_TOKEN = os.environ["ZERODHA_ACCESS_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

IST          = ZoneInfo("Asia/Kolkata")
DRY_RUN      = "--dry-run" in sys.argv
SPOT_ONLY    = "--spot-only" in sys.argv

# Batch writes to Supabase every N ticks to avoid overwhelming the DB
BATCH_SIZE   = 50
BATCH_FLUSH_SECS = 2   # also flush if N seconds passed since last flush

# Supabase table
TICKS_TABLE  = "market_ticks"

# NSE indices (these tokens are stable — never change)
NSE_INDICES = {
    "NIFTY 50":   256265,   # NSE:NIFTY 50
    "NIFTY BANK": 260105,   # NSE:NIFTY BANK
    "INDIA VIX":  264969,   # NSE:INDIA VIX
}

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s IST] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

def now_ist():
    return datetime.now(timezone.utc).astimezone(IST)

# ── Supabase write ────────────────────────────────────────────────────────────

def sb_headers():
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }

def flush_batch(batch: list):
    if not batch or DRY_RUN:
        if DRY_RUN and batch:
            log.info(f"  [DRY] Would write {len(batch)} ticks")
        return
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{TICKS_TABLE}",
            headers=sb_headers(),
            json=batch,
            timeout=10,
        )
        if r.status_code >= 300:
            log.warning(f"  Supabase write error {r.status_code}: {r.text[:100]}")
    except Exception as e:
        log.warning(f"  Supabase write failed: {e}")

# ── Instrument loader ─────────────────────────────────────────────────────────

def load_instruments(kite: KiteConnect) -> dict:
    """
    Fetch NFO instrument list from Zerodha and build subscription map.
    Returns: {instrument_token: {symbol, instrument_type, expiry, strike, tradingsymbol}}
    """
    log.info("Loading NFO instruments from Zerodha...")
    instruments = {}

    # 1. NSE index spots
    for name, token in NSE_INDICES.items():
        instruments[token] = {
            "exchange":        "NSE",
            "symbol":          name,
            "instrument_type": "SPOT",
            "tradingsymbol":   name,
            "expiry_date":     None,
            "strike":          None,
        }

    if SPOT_ONLY:
        log.info(f"  Spot-only mode: {len(instruments)} instruments")
        return instruments

    # 2. NFO options + futures
    try:
        nfo = kite.instruments("NFO")
        log.info(f"  NFO instruments downloaded: {len(nfo)} rows")
    except Exception as e:
        log.error(f"  Failed to download NFO instruments: {e}")
        return instruments

    today       = date.today()
    max_expiry  = today + timedelta(days=14)  # current + next weekly expiry

    nifty_count = 0
    fut_count   = 0

    for inst in nfo:
        sym = inst.get("name", "")
        if sym not in ("NIFTY", "BANKNIFTY"):
            continue

        expiry = inst.get("expiry")
        if not expiry:
            continue
        if isinstance(expiry, str):
            try:
                expiry = date.fromisoformat(expiry)
            except Exception:
                continue

        itype = inst.get("instrument_type", "")
        token = inst.get("instrument_token")
        if not token:
            continue

        # Options: current + next weekly expiry only
        if itype in ("CE", "PE"):
            if today <= expiry <= max_expiry:
                instruments[token] = {
                    "exchange":        "NFO",
                    "symbol":          sym,
                    "instrument_type": itype,
                    "tradingsymbol":   inst.get("tradingsymbol", ""),
                    "expiry_date":     expiry.isoformat(),
                    "strike":          inst.get("strike"),
                }
                nifty_count += 1

        # Futures: front month only
        elif itype == "FUT":
            if expiry >= today:
                instruments[token] = {
                    "exchange":        "NFO",
                    "symbol":          sym,
                    "instrument_type": "FUT",
                    "tradingsymbol":   inst.get("tradingsymbol", ""),
                    "expiry_date":     expiry.isoformat(),
                    "strike":          None,
                }
                fut_count += 1

    log.info(f"  Options: {nifty_count} | Futures: {fut_count} | "
             f"Total: {len(instruments)} instruments")

    if len(instruments) > 3000:
        log.warning(f"  WARNING: {len(instruments)} > 3000 Zerodha limit. Trimming to ATM ±50.")
        # If over limit, keep spot + futures + options sorted by proximity to round numbers
        opts = {t: v for t, v in instruments.items() if v["instrument_type"] in ("CE","PE")}
        futs = {t: v for t, v in instruments.items() if v["instrument_type"] == "FUT"}
        spots = {t: v for t, v in instruments.items() if v["instrument_type"] == "SPOT"}
        # Keep all futures + spots, trim options to 2990 slots
        max_opts = 3000 - len(spots) - len(futs)
        opt_items = sorted(opts.items(), key=lambda x: x[1].get("strike") or 0)
        instruments = {**spots, **futs, **dict(opt_items[:max_opts])}

    return instruments

# ── Tick processor ────────────────────────────────────────────────────────────

class TickProcessor:
    def __init__(self, instrument_map: dict):
        self.instrument_map = instrument_map
        self._batch   = []
        self._last_flush = time.time()

    def process(self, ticks: list):
        ts = now_ist().isoformat()
        for tick in ticks:
            token = tick.get("instrument_token")
            meta  = self.instrument_map.get(token)
            if not meta:
                continue

            ltp = tick.get("last_price")
            if ltp is None:
                continue

            row = {
                "ts":              ts,
                "exchange":        meta["exchange"],
                "symbol":          meta["symbol"],
                "instrument_type": meta["instrument_type"],
                "instrument_token":token,
                "tradingsymbol":   meta["tradingsymbol"],
                "expiry_date":     meta.get("expiry_date"),
                "strike":          meta.get("strike"),
                "last_price":      float(ltp),
                "open_interest":   tick.get("oi"),
                "oi_day_high":     tick.get("oi_day_high"),
                "oi_day_low":      tick.get("oi_day_low"),
                "volume":          tick.get("volume"),
                "buy_qty":         tick.get("buy_quantity"),
                "sell_qty":        tick.get("sell_quantity"),
                "average_price":   tick.get("average_price"),
                "net_change":      tick.get("net_change"),
            }
            self._batch.append(row)

            if DRY_RUN and meta["instrument_type"] == "SPOT":
                log.info(f"  TICK {meta['symbol']} {meta['instrument_type']}: "
                         f"{ltp:,.2f}")

        self._maybe_flush()

    def _maybe_flush(self):
        now = time.time()
        if (len(self._batch) >= BATCH_SIZE or
                now - self._last_flush >= BATCH_FLUSH_SECS):
            if self._batch:
                flush_batch(self._batch)
                self._batch = []
                self._last_flush = now

    def force_flush(self):
        if self._batch:
            flush_batch(self._batch)
            self._batch = []

# ── WebSocket runner ──────────────────────────────────────────────────────────

class FeedRunner:
    def __init__(self):
        self.kite       = KiteConnect(api_key=API_KEY)
        self.kite.set_access_token(ACCESS_TOKEN)
        self.instruments = load_instruments(self.kite)
        self.tokens      = list(self.instruments.keys())
        self.processor   = TickProcessor(self.instruments)
        self.kws         = None
        self._stop       = Event()
        self._reconnect_delay = 5

    def start(self):
        log.info(f"MERDIAN WebSocket Feed starting")
        log.info(f"  Instruments: {len(self.tokens)}")
        log.info(f"  Dry run: {DRY_RUN}")
        log.info(f"  Supabase table: {TICKS_TABLE}")

        while not self._stop.is_set():
            try:
                self._connect()
            except KeyboardInterrupt:
                log.info("Stopped by user.")
                break
            except Exception as e:
                log.error(f"Feed error: {e}")

            if not self._stop.is_set():
                log.info(f"Reconnecting in {self._reconnect_delay}s...")
                time.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    def _connect(self):
        self.kws = KiteTicker(API_KEY, ACCESS_TOKEN)

        def on_ticks(ws, ticks):
            self.processor.process(ticks)
            self._reconnect_delay = 5  # reset on successful tick

        def on_connect(ws, response):
            log.info(f"Connected. Subscribing {len(self.tokens)} instruments...")
            ws.subscribe(self.tokens)
            ws.set_mode(ws.MODE_FULL, self.tokens)
            log.info("Subscribed. Feed live.")

        def on_close(ws, code, reason):
            log.warning(f"Connection closed: {code} {reason}")
            self.processor.force_flush()

        def on_error(ws, code, reason):
            log.error(f"WebSocket error: {code} {reason}")

        def on_reconnect(ws, attempts):
            log.info(f"Reconnecting... attempt {attempts}")

        def on_noreconnect(ws):
            log.error("Max reconnects reached — will restart outer loop")

        self.kws.on_ticks      = on_ticks
        self.kws.on_connect    = on_connect
        self.kws.on_close      = on_close
        self.kws.on_error      = on_error
        self.kws.on_reconnect  = on_reconnect
        self.kws.on_noreconnect= on_noreconnect

        self.kws.connect(threaded=False)  # blocks until closed

    def stop(self):
        self._stop.set()
        self.processor.force_flush()
        if self.kws:
            try:
                self.kws.close()
            except Exception:
                pass

# ── DDL reminder ─────────────────────────────────────────────────────────────

DDL = """
-- Run once in Supabase SQL editor before starting ws_feed_zerodha.py:

CREATE TABLE IF NOT EXISTS public.market_ticks (
  id               bigserial PRIMARY KEY,
  ts               timestamptz NOT NULL DEFAULT now(),
  exchange         text NOT NULL,
  symbol           text NOT NULL,
  instrument_type  text NOT NULL,        -- SPOT / FUT / CE / PE
  instrument_token int NOT NULL,
  tradingsymbol    text NOT NULL,
  expiry_date      date,
  strike           numeric,
  last_price       numeric NOT NULL,
  open_interest    bigint,
  oi_day_high      bigint,
  oi_day_low       bigint,
  volume           bigint,
  buy_qty          bigint,
  sell_qty         bigint,
  average_price    numeric,
  net_change       numeric,
  created_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mt_ts        ON market_ticks (ts DESC);
CREATE INDEX IF NOT EXISTS idx_mt_sym_type  ON market_ticks (symbol, instrument_type, ts DESC);
CREATE INDEX IF NOT EXISTS idx_mt_token_ts  ON market_ticks (instrument_token, ts DESC);

-- Aggressive retention: keep only last 2 trading days of ticks
-- (run as a daily cron or Supabase scheduled function)
-- DELETE FROM market_ticks WHERE ts < now() - interval '2 days';
"""

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--ddl" in sys.argv:
        print(DDL)
        sys.exit(0)

    try:
        runner = FeedRunner()
        runner.start()
    except KeyboardInterrupt:
        log.info("Feed stopped.")
