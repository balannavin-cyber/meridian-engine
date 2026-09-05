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

Scheduling (ACTUAL, corrected S72 -- the cron block previously documented here was
stale and had not been the mechanism since the systemd migration):
    merdian-wsfeed-start.timer  OnCalendar=Mon-Fri 03:40:00 UTC  (09:10 IST)
    merdian-wsfeed.service      Restart=always, StartLimitBurst=3/300s
    A stop is issued ~10:05 UTC by an invoker that is in NEITHER the unit nor the
    timer -- unenumerated as of S72, see TD-S71-NEW-14 reconciliation.

S72 FIXES (2026-09-05) -- all three close TD-S72-NEW-5 / TD-S72-NEW-6:

  FAIL-OPEN INSTRUMENT LOADER (the root cause of the ~21% breadth failure rate).
  On 2026-09-04 `kite.instruments("NFO")` hit a read timeout at 03:40:13. The
  handler did `return instruments` -- returning the 3 hardcoded NSE index spots and
  NEVER ATTEMPTING the breadth universe, which is a SEPARATE NSE download that had
  nothing to do with the NFO failure and would very likely have succeeded. One
  second later the feed logged "Connected. Subscribing 3 instruments... Feed live."
  Zero EQ ticks flowed for the whole session; ingest_breadth_from_ticks wrote ~390
  synthetic zero-coverage rows; market_breadth_intraday and WCB were empty; the EOD
  check reported 2 FAIL for one upstream cause. Healthy days subscribe 1648-1855.
  Now: retry with backoff, disk cache fallback, NFO failure no longer aborts the
  breadth path, and a hard universe floor that refuses to report "Feed live".

  NO SIGTERM HANDLER. systemd's stop timed out at 90s (TimeoutStopSec default) and
  SIGKILLed, so the unit entered `failed (Result: timeout)` on the NORMAL daily
  shutdown and OnFailure= fired every single day -- including healthy ones. The
  alert channel emitted byte-identical text on 09-02 (good) and 09-04 (bad), which
  is why a 21% failure rate went unnoticed for weeks.
"""

import os, sys, time, json, math, logging, signal
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

# ── S72: instrument-load resilience (TD-S72-NEW-5) ───────────────────────────
# The instrument list is fetched ONCE at startup and determines the entire
# session's subscription. A transient timeout there costs a full trading day of
# breadth data, permanently. Retry, then fall back to the last good list on disk.
INSTRUMENT_FETCH_ATTEMPTS = int(os.getenv("MERDIAN_WSFEED_FETCH_ATTEMPTS", "4"))
INSTRUMENT_RETRY_BASE_SECS = float(os.getenv("MERDIAN_WSFEED_RETRY_BASE", "3"))
INSTRUMENT_CACHE_DIR = os.getenv(
    "MERDIAN_WSFEED_CACHE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache"))
INSTRUMENT_CACHE_MAX_AGE_DAYS = float(os.getenv("MERDIAN_WSFEED_CACHE_MAX_AGE_DAYS", "5"))

# Hard floor on the subscribed universe. Below this the feed REFUSES to run rather
# than deliver a session that looks healthy and carries no breadth. Healthy sessions
# observed 2026-09-01/02/03: 1855, 1659, 1648. The failed session: 3.
MIN_UNIVERSE = int(os.getenv("MERDIAN_WSFEED_MIN_INSTRUMENTS", "100"))
EXIT_UNIVERSE_TOO_SMALL = 3

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

def _cache_path(exchange: str) -> str:
    return os.path.join(INSTRUMENT_CACHE_DIR, f"zerodha_instruments_{exchange}.json")


def _cache_write(exchange: str, rows: list):
    """Persist a good instrument list. Best-effort: a cache write failure must never
    take down a feed that has already fetched successfully."""
    try:
        os.makedirs(INSTRUMENT_CACHE_DIR, exist_ok=True)
        tmp = _cache_path(exchange) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, default=str)      # date objects -> ISO strings
        os.replace(tmp, _cache_path(exchange))    # atomic
        log.info(f"  {exchange} instrument cache written: {len(rows)} rows")
    except Exception as e:
        log.warning(f"  {exchange} instrument cache write failed (non-fatal): {e}")


def _cache_read(exchange: str):
    """Return (rows, age_days) from the last good list, or (None, None).

    Expiry values come back as ISO strings rather than date objects; both
    load_instruments() and load_breadth_universe() already handle the str form,
    so a cached list is consumed by exactly the same code path as a live one.
    """
    path = _cache_path(exchange)
    try:
        if not os.path.isfile(path):
            return None, None
        age_days = (time.time() - os.stat(path).st_mtime) / 86400.0
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        if not rows:
            return None, None
        return rows, age_days
    except Exception as e:
        log.warning(f"  {exchange} instrument cache read failed: {e}")
        return None, None


def fetch_instruments(kite, exchange: str):
    """S72 (TD-S72-NEW-5) -- fetch an instrument list with retry, then disk fallback.

    Returns (rows, source) where source is 'live', 'cache' or None. Never raises.

    The pre-S72 code called kite.instruments(exchange) once inside a try/except and
    treated any failure as terminal for that exchange. A single read timeout on
    2026-09-04 therefore cost an entire session of breadth data, unrecoverably.
    """
    last_err = None
    for attempt in range(1, INSTRUMENT_FETCH_ATTEMPTS + 1):
        try:
            rows = kite.instruments(exchange)
            if rows:
                log.info(f"  {exchange} instruments downloaded: {len(rows)} rows"
                         f"{'' if attempt == 1 else f' (attempt {attempt})'}")
                _cache_write(exchange, rows)
                return rows, "live"
            last_err = "empty list returned"
        except Exception as e:
            last_err = str(e)
        if attempt < INSTRUMENT_FETCH_ATTEMPTS:
            delay = INSTRUMENT_RETRY_BASE_SECS * (2 ** (attempt - 1))
            log.warning(f"  {exchange} instrument fetch attempt "
                        f"{attempt}/{INSTRUMENT_FETCH_ATTEMPTS} failed: {last_err} "
                        f"-- retrying in {delay:.0f}s")
            time.sleep(delay)

    log.error(f"  {exchange} instrument fetch FAILED after "
              f"{INSTRUMENT_FETCH_ATTEMPTS} attempts: {last_err}")

    rows, age_days = _cache_read(exchange)
    if rows is None:
        log.error(f"  {exchange} NO CACHE AVAILABLE -- universe will be degraded")
        return None, None
    if age_days is not None and age_days > INSTRUMENT_CACHE_MAX_AGE_DAYS:
        log.error(f"  {exchange} cache is {age_days:.1f} days old "
                  f"(> {INSTRUMENT_CACHE_MAX_AGE_DAYS}) -- REFUSING to use it; "
                  f"expiries and listings will have moved")
        return None, None
    log.warning(f"  {exchange} FALLING BACK to cached list: {len(rows)} rows, "
                f"{age_days:.1f} days old")
    return rows, "cache"


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
    #
    # S72 (TD-S72-NEW-5): this block previously did `return instruments` on any NFO
    # failure, which ALSO skipped the breadth universe below -- an entirely separate
    # NSE download that had nothing to do with the NFO error. That single line is
    # what turned a transient 2026-09-04 timeout into a lost session. NFO failure is
    # now degraded-but-continue; the universe floor at the end decides whether the
    # result is fit to run on.
    nfo, nfo_src = fetch_instruments(kite, "NFO")
    if not nfo:
        log.error("  NFO universe unavailable -- CONTINUING to breadth load "
                  "(options/futures will be absent this session)")
        nfo = []

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

    # Load breadth universe (NSE EQ stocks)
    breadth = load_breadth_universe(kite)
    instruments.update(breadth)
    log.info(f"  After breadth: {len(instruments)} total instruments")

    # Trim to Zerodha 3000 limit — priority: spots > futures > EQ breadth > options
    if len(instruments) > 3000:
        log.warning(f"  {len(instruments)} > 3000 limit — trimming options to fit")
        opts  = {t: v for t, v in instruments.items() if v["instrument_type"] in ("CE", "PE")}
        futs  = {t: v for t, v in instruments.items() if v["instrument_type"] == "FUT"}
        spots = {t: v for t, v in instruments.items() if v["instrument_type"] == "SPOT"}
        eq    = {t: v for t, v in instruments.items() if v["instrument_type"] == "EQ"}
        max_opts = max(0, 3000 - len(spots) - len(futs) - len(eq))
        opt_items = sorted(opts.items(), key=lambda x: x[1].get("strike") or 0)
        instruments = {**spots, **futs, **eq, **dict(opt_items[:max_opts])}
        log.info(f"  After trim: {len(instruments)} "
                 f"(spots={len(spots)}, fut={len(futs)}, eq={len(eq)}, opts={min(max_opts,len(opts))})")
    return instruments


def load_breadth_universe(kite) -> dict:
    """
    Load NSE EQ breadth universe from Supabase and match to Zerodha instrument tokens.
    Returns: {instrument_token: {symbol, instrument_type, tradingsymbol}}
    """
    import requests as _req
    log.info("Loading NSE EQ breadth universe from Supabase...")

    # Fetch breadth symbols from Supabase
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        url = f"{SUPABASE_URL}/rest/v1/breadth_universe_members"
        # Paginate to get all members past Supabase 1000-row limit
        members = []
        page_size = 1000
        offset = 0
        while True:
            params = {
                "select": "symbol,exchange",
                "is_active": "eq.true",
                "active": "eq.true",
                "limit": str(page_size),
                "offset": str(offset),
            }
            r = _req.get(url, headers=headers, params=params, timeout=15)
            if r.status_code != 200:
                log.warning(f"  Breadth universe fetch failed: {r.status_code}")
                break
            page = r.json()
            if not page:
                break
            members.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        breadth_symbols = {row["symbol"] for row in members if row.get("exchange") == "NSE"}
        log.info(f"  Breadth universe: {len(breadth_symbols)} NSE symbols")
    except Exception as e:
        log.warning(f"  Breadth universe fetch error: {e}")
        return {}

    # Download NSE EQ instruments from Zerodha (S72: retry + cache fallback)
    nse, nse_src = fetch_instruments(kite, "NSE")
    if not nse:
        log.error("  NSE universe unavailable -- breadth will be EMPTY this session")
        return {}

    # Match symbols
    breadth_instruments = {}
    for inst in nse:
        sym = inst.get("tradingsymbol", "")
        if sym not in breadth_symbols:
            continue
        if inst.get("instrument_type") != "EQ":
            continue
        token = inst.get("instrument_token")
        if not token:
            continue
        breadth_instruments[token] = {
            "exchange":        "NSE",
            "symbol":          sym,
            "instrument_type": "EQ",
            "tradingsymbol":   sym,
            "expiry_date":     None,
            "strike":          None,
        }

    log.info(f"  Breadth matched: {len(breadth_instruments)}/{len(breadth_symbols)} symbols")
    return breadth_instruments

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

        # S72 (TD-S72-NEW-5): composition breakdown. "Subscribing N instruments" alone
        # was not enough to spot the 2026-09-04 failure at a glance -- 3 read as a
        # number, not as an alarm. EQ count is the one that matters for breadth.
        comp = {}
        for meta in self.instruments.values():
            comp[meta["instrument_type"]] = comp.get(meta["instrument_type"], 0) + 1
        log.info("  Composition: " + ", ".join(f"{k}={v}" for k, v in sorted(comp.items())))

        # HARD FLOOR. Below this the universe cannot produce usable breadth, and a
        # feed that runs anyway manufactures a healthy-looking session with no data:
        # systemd sees a live process, the feed log says "Feed live", and
        # ingest_breadth_from_ticks writes ~390 synthetic zero-coverage rows.
        # Exiting non-zero is the only signal that survives to the operator.
        if not SPOT_ONLY and not DRY_RUN and len(self.tokens) < MIN_UNIVERSE:
            log.error(f"  UNIVERSE TOO SMALL: {len(self.tokens)} < {MIN_UNIVERSE} "
                      f"floor. Instrument load failed open. REFUSING to start -- a "
                      f"session run on this universe yields zero breadth while "
                      f"reporting healthy (TD-S72-NEW-5).")
            log.error(f"  Composition was: {comp}")
            sys.exit(EXIT_UNIVERSE_TOO_SMALL)

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
            # S72: close() alone leaves connect(threaded=False) blocked in the
            # Twisted reactor. stop_retry() prevents the client reconnecting out
            # from under us, and stop() halts the reactor so start()'s outer loop
            # can observe self._stop and return. Each guarded independently -- a
            # missing method on an older pykiteconnect must not abort shutdown.
            for meth in ("stop_retry", "close", "stop"):
                try:
                    fn = getattr(self.kws, meth, None)
                    if callable(fn):
                        fn()
                except Exception as e:
                    log.warning(f"  kws.{meth}() during shutdown: {e}")

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

if "--ddl" in sys.argv:
    print(DDL)
    sys.exit(0)

def install_signal_handlers(runner):
    """S72 (TD-S72-NEW-6) -- shut down cleanly on SIGTERM.

    Pre-S72 there was NO handler. systemd's stop request was ignored for the full
    TimeoutStopSec (90s default, unset in the unit), then SIGKILL followed and the
    unit entered `failed (Result: timeout)`. Because that is the NORMAL daily
    shutdown path, OnFailure= fired every single day and WSFEED_ALERTS emitted
    byte-identical "Feed DOWN" text on healthy and broken sessions alike. An alert
    channel that cannot distinguish the two is why a 21% failure rate persisted.

    Journal evidence, 2026-09-04:
        10:05:01 Stopping ...
        10:06:31 State 'stop-sigterm' timed out. Killing.   <- exactly 90s

    CAVEAT, not yet measured: KiteTicker runs a Twisted reactor, which installs its
    own signal handlers when connect(threaded=False) is used. If SIGTERM is still
    swallowed after this change, the reactor is the reason -- verify with
    `systemctl stop` and check for a clean exit rather than a 90s timeout. The
    fallback is KillSignal=SIGINT or an explicit TimeoutStopSec in the unit; do not
    reach for SuccessExitStatus=SIGKILL, which would mask genuine kills.
    """
    def _handler(signum, _frame):
        log.info(f"Received signal {signum} -- clean shutdown requested.")
        try:
            runner.stop()
        except Exception as e:
            log.warning(f"  stop() raised during shutdown: {e}")

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _handler)
        except Exception as e:
            log.warning(f"  could not install handler for {sig}: {e}")


if __name__ == "__main__":

    try:
        runner = FeedRunner()
        install_signal_handlers(runner)
        runner.start()
    except KeyboardInterrupt:
        log.info("Feed stopped.")
