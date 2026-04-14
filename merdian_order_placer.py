#!/usr/bin/env python3
"""
merdian_order_placer.py  --  MERDIAN Phase 4B Order Placer
===========================================================
Places and squares off NSE/BSE options orders via Dhan Trading API.
Must run on AWS (Elastic IP 13.63.27.85 whitelisted in Dhan).

Core functions:
    find_security(symbol, strike, expiry_date, option_type)
    place_order(symbol, strike, expiry_date, option_type, lots, transaction='BUY')
    poll_fill(order_id, max_attempts=10, interval=2)
    square_off(trade_log_id)
    get_margin()

Also exposes HTTP endpoints for dashboard:
    POST /place_order?symbol=NIFTY&trade_log_id=<uuid>
    POST /square_off?trade_log_id=<uuid>
    GET  /order_status?order_id=<id>
    GET  /margin

Usage:
    python merdian_order_placer.py           # start HTTP server (port 8767)
    python merdian_order_placer.py --test    # test instrument lookup only
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from supabase import create_client
    SUPABASE = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
except Exception:
    SUPABASE = None

# ── Config ────────────────────────────────────────────────────────────────────

DHAN_CLIENT_ID  = os.getenv("DHAN_CLIENT_ID", "").strip()
DHAN_API_TOKEN  = os.getenv("DHAN_API_TOKEN", "").strip()
DHAN_ORDER_URL  = "https://api.dhan.co/v2/orders"
DHAN_FUNDS_URL  = "https://api.dhan.co/v2/fundlimit"
DHAN_SCRIP_URL  = "https://images.dhan.co/api-data/api-scrip-master.csv"

PORT            = 8767
IST             = ZoneInfo("Asia/Kolkata")
BASE_DIR        = Path(__file__).resolve().parent
RUNTIME_DIR     = BASE_DIR / "runtime"
SCRIP_CACHE     = RUNTIME_DIR / "dhan_scrip_master.csv"
SCRIP_CACHE_AGE = 86400  # refresh daily

LOT_SIZE        = {"NIFTY": 75, "SENSEX": 20}

# Dhan exchange segment by symbol
EXCHANGE_SEGMENT = {
    "NIFTY":  "NSE_FNO",
    "SENSEX": "BSE_FNO",
}

# Dhan symbol name in scrip master
SCRIP_SYMBOL = {
    "NIFTY":  "NIFTY",
    "SENSEX": "SENSEX",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_ist() -> datetime:
    return datetime.now(timezone.utc).astimezone(IST)

def log(msg: str) -> None:
    print(f"[{now_ist().strftime('%H:%M:%S IST')}] {msg}", flush=True)

def dhan_headers() -> dict:
    return {
        "access-token":  DHAN_API_TOKEN,
        "client-id":     DHAN_CLIENT_ID,
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }

# ── Scrip Master ──────────────────────────────────────────────────────────────

def _scrip_is_stale() -> bool:
    if not SCRIP_CACHE.exists():
        return True
    age = time.time() - SCRIP_CACHE.stat().st_mtime
    return age > SCRIP_CACHE_AGE

def load_scrip_master(force: bool = False) -> list[dict]:
    """Download and cache Dhan scrip master. Returns list of rows."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    if not force and not _scrip_is_stale():
        log(f"Scrip master cache hit: {SCRIP_CACHE}")
        with SCRIP_CACHE.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    log("Downloading Dhan scrip master...")
    r = requests.get(DHAN_SCRIP_URL, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Scrip master download failed: {r.status_code}")

    SCRIP_CACHE.write_bytes(r.content)
    log(f"Scrip master cached: {SCRIP_CACHE} ({len(r.content):,} bytes)")

    content = r.content.decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(content)))

def find_security(
    symbol: str,
    strike: int,
    expiry_date: str,
    option_type: str,
) -> dict:
    """
    Find Dhan security_id and trading_symbol for an options contract.

    Args:
        symbol:      'NIFTY' or 'SENSEX'
        strike:      e.g. 23800
        expiry_date: 'YYYY-MM-DD'
        option_type: 'CE' or 'PE'

    Returns:
        {'security_id': '...', 'trading_symbol': '...', 'lot_size': int}

    Raises:
        RuntimeError if not found.
    """
    symbol      = symbol.upper()
    option_type = option_type.upper()
    segment     = EXCHANGE_SEGMENT[symbol]
    scrip_sym   = SCRIP_SYMBOL[symbol]

    rows = load_scrip_master()

    matches = []
    for row in rows:
        # Filter by segment, symbol name, instrument type, option type
        if row.get("SEM_SEGMENT", "").strip() != segment:
            continue
        if row.get("SM_SYMBOL_NAME", "").strip().upper() != scrip_sym:
            continue
        if row.get("SEM_INSTRUMENT_NAME", "").strip() != "OPTIDX":
            continue
        if row.get("SEM_OPTION_TYPE", "").strip().upper() != option_type:
            continue

        # Match expiry date (stored as YYYY-MM-DD in scrip master)
        row_expiry = row.get("SEM_EXPIRY_DATE", "").strip()[:10]
        if row_expiry != expiry_date:
            continue

        # Match strike (stored as float e.g. "23800.0")
        try:
            row_strike = int(float(row.get("SEM_STRIKE_PRICE", "0")))
        except (ValueError, TypeError):
            continue
        if row_strike != int(strike):
            continue

        matches.append(row)

    if not matches:
        raise RuntimeError(
            f"Security not found: {symbol} {strike} {option_type} expiry={expiry_date}. "
            f"Check scrip master or expiry date format."
        )

    row = matches[0]
    security_id    = row.get("SEM_SMST_SECURITY_ID", "").strip()
    trading_symbol = row.get("SEM_TRADING_SYMBOL", "").strip()

    try:
        lot_size = int(float(row.get("SEM_LOT_UNITS", LOT_SIZE.get(symbol, 75))))
    except (ValueError, TypeError):
        lot_size = LOT_SIZE.get(symbol, 75)

    log(f"Found: {trading_symbol} | security_id={security_id} | lot_size={lot_size}")
    return {
        "security_id":    security_id,
        "trading_symbol": trading_symbol,
        "lot_size":       lot_size,
    }

# ── Order Placement ───────────────────────────────────────────────────────────

def place_order(
    symbol: str,
    strike: int,
    expiry_date: str,
    option_type: str,
    lots: int,
    transaction: str = "BUY",
    correlation_id: Optional[str] = None,
) -> dict:
    """
    Place a market order via Dhan API.

    Returns:
        {'order_id': '...', 'status': 'TRANSIT'|'PENDING', 'raw': {...}}
    """
    symbol      = symbol.upper()
    option_type = option_type.upper()
    transaction = transaction.upper()

    sec = find_security(symbol, strike, expiry_date, option_type)
    quantity = lots * sec["lot_size"]

    payload = {
        "dhanClientId":      DHAN_CLIENT_ID,
        "transactionType":   transaction,
        "exchangeSegment":   EXCHANGE_SEGMENT[symbol],
        "productType":       "INTRADAY",
        "orderType":         "MARKET",
        "validity":          "DAY",
        "securityId":        sec["security_id"],
        "quantity":          quantity,
        "disclosedQuantity": 0,
        "price":             0,
        "triggerPrice":      0,
        "afterMarketOrder":  False,
    }

    if correlation_id:
        payload["correlationId"] = correlation_id

    log(f"Placing {transaction} order: {symbol} {strike}{option_type} "
        f"x{lots} lots ({quantity} units) | security_id={sec['security_id']}")

    r = requests.post(
        DHAN_ORDER_URL,
        headers=dhan_headers(),
        json=payload,
        timeout=15,
    )

    if r.status_code >= 300:
        raise RuntimeError(
            f"Dhan order placement failed ({r.status_code}): {r.text[:300]}"
        )

    data = r.json()
    order_id = str(data.get("orderId", "")).strip()
    status   = str(data.get("orderStatus", "TRANSIT")).strip()

    log(f"Order placed: order_id={order_id} status={status}")
    return {"order_id": order_id, "status": status, "raw": data, "lot_size": sec["lot_size"]}

def get_order_status(order_id: str) -> dict:
    """Fetch order status from Dhan."""
    r = requests.get(
        f"{DHAN_ORDER_URL}/{order_id}",
        headers=dhan_headers(),
        timeout=10,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"Order status fetch failed ({r.status_code}): {r.text[:200]}")
    return r.json()

def poll_fill(
    order_id: str,
    max_attempts: int = 12,
    interval: float = 2.5,
) -> dict:
    """
    Poll order status until filled or terminal state.

    Returns:
        {'filled': True/False, 'fill_price': float|None, 'status': str, 'filled_qty': int}
    """
    TERMINAL = {"TRADED", "CANCELLED", "REJECTED", "EXPIRED"}

    for attempt in range(1, max_attempts + 1):
        try:
            data = get_order_status(order_id)
        except Exception as e:
            log(f"Poll attempt {attempt}/{max_attempts} error: {e}")
            time.sleep(interval)
            continue

        status     = str(data.get("orderStatus", "")).upper()
        fill_price = data.get("averageTradedPrice") or data.get("price")
        filled_qty = data.get("filledQty", 0) or data.get("filled_qty", 0)

        try:
            fill_price = float(fill_price) if fill_price else None
        except (ValueError, TypeError):
            fill_price = None

        log(f"Poll {attempt}/{max_attempts}: status={status} fill_price={fill_price} filled_qty={filled_qty}")

        if status == "TRADED" and fill_price and fill_price > 0:
            return {"filled": True, "fill_price": fill_price, "status": status, "filled_qty": filled_qty}

        if status in TERMINAL:
            return {"filled": status == "TRADED", "fill_price": fill_price, "status": status, "filled_qty": filled_qty}

        time.sleep(interval)

    # Timeout — return last known state
    log(f"WARNING: Poll timed out after {max_attempts} attempts for order {order_id}")
    return {"filled": False, "fill_price": None, "status": "TIMEOUT", "filled_qty": 0}

# ── Supabase integration ───────────────────────────────────────────────────────

def fetch_trade(trade_log_id: str) -> Optional[dict]:
    """Fetch trade from trade_log by id."""
    if not SUPABASE:
        return None
    rows = (SUPABASE.table("trade_log")
            .select("*")
            .eq("id", trade_log_id)
            .limit(1)
            .execute().data)
    return rows[0] if rows else None

def update_trade_order(
    trade_log_id: str,
    order_id: str,
    fill_price: Optional[float],
    status: str,
    entry_mode: str = "AUTO",
) -> None:
    """Update trade_log with Dhan order details after placement."""
    if not SUPABASE:
        return
    update = {
        "dhan_order_id": order_id,
        "entry_mode":    entry_mode,
    }
    if fill_price:
        update["entry_price"] = fill_price
    if status in ("TRADED",):
        update["status"] = "OPEN"
    SUPABASE.table("trade_log").update(update).eq("id", trade_log_id).execute()

def log_auto_trade(
    symbol: str,
    strike: int,
    expiry_date: str,
    option_type: str,
    lots: int,
    fill_price: float,
    signal_ts: str,
    order_id: str,
    lot_size: int,
) -> str:
    """Insert a new trade_log row for an auto-placed order. Returns trade_id."""
    if not SUPABASE:
        raise RuntimeError("Supabase not available")

    now     = datetime.now(timezone.utc)
    exit_ts = now + timedelta(minutes=30)

    trade = {
        "symbol":       symbol.upper(),
        "signal_ts":    signal_ts,
        "entry_ts":     now.isoformat(),
        "exit_ts":      exit_ts.isoformat(),
        "action":       f"BUY_{option_type.upper()}",
        "strike":       int(strike),
        "expiry_date":  str(expiry_date),
        "option_type":  option_type.upper(),
        "lots":         int(lots),
        "entry_price":  float(fill_price),
        "status":       "OPEN",
        "entry_mode":   "AUTO",
        "dhan_order_id": order_id,
        "notes":        f"Auto-placed via merdian_order_placer. order_id={order_id}",
    }
    result   = SUPABASE.table("trade_log").insert(trade).execute()
    trade_id = result.data[0]["id"]

    alert = {
        "trade_id":    trade_id,
        "symbol":      symbol.upper(),
        "exit_ts":     exit_ts.isoformat(),
        "strike":      int(strike),
        "option_type": option_type.upper(),
        "lots":        int(lots),
        "status":      "PENDING",
    }
    SUPABASE.table("exit_alerts").insert(alert).execute()
    return trade_id

# ── Margin check ──────────────────────────────────────────────────────────────

def get_margin() -> dict:
    """Fetch available margin from Dhan."""
    r = requests.get(DHAN_FUNDS_URL, headers=dhan_headers(), timeout=10)
    if r.status_code >= 300:
        raise RuntimeError(f"Margin fetch failed ({r.status_code}): {r.text[:200]}")
    return r.json()

# ── High-level order flow ─────────────────────────────────────────────────────

def execute_entry(
    symbol: str,
    strike: int,
    expiry_date: str,
    option_type: str,
    lots: int,
    signal_ts: str,
) -> dict:
    """
    Full entry flow:
    1. Place BUY order
    2. Poll for fill
    3. Log to trade_log + exit_alerts
    4. Return result dict

    Returns:
        {
          'ok': True/False,
          'trade_id': str,
          'order_id': str,
          'fill_price': float,
          'exit_ts_ist': str,
          'error': str
        }
    """
    try:
        # 1. Place order
        order = place_order(symbol, strike, expiry_date, option_type, lots, "BUY")
        order_id = order["order_id"]
        lot_size = order["lot_size"]

        # 2. Poll fill
        fill = poll_fill(order_id)

        if not fill["filled"] or not fill["fill_price"]:
            return {
                "ok":        False,
                "order_id":  order_id,
                "fill_price": fill["fill_price"],
                "status":    fill["status"],
                "error":     f"Order not filled: status={fill['status']}. Check Dhan order book.",
            }

        fill_price = fill["fill_price"]

        # 3. Log trade
        trade_id = log_auto_trade(
            symbol, strike, expiry_date, option_type,
            lots, fill_price, signal_ts, order_id, lot_size,
        )

        exit_ts = (datetime.now(timezone.utc) + timedelta(minutes=30))
        exit_ts_ist = exit_ts.astimezone(IST).strftime("%H:%M IST")

        log(f"Entry complete: trade_id={trade_id[:8]} fill={fill_price} exit={exit_ts_ist}")

        return {
            "ok":         True,
            "trade_id":   trade_id,
            "order_id":   order_id,
            "fill_price": fill_price,
            "exit_ts_ist": exit_ts_ist,
            "error":      "",
        }

    except Exception as e:
        log(f"ERROR execute_entry: {e}")
        return {"ok": False, "order_id": "", "fill_price": None, "error": str(e)}


def execute_exit(trade_log_id: str) -> dict:
    """
    Full exit flow:
    1. Fetch trade from trade_log
    2. Place SELL order
    3. Poll for fill
    4. Update trade_log with PnL
    5. Update capital_tracker

    Returns:
        {'ok': True/False, 'pnl': float, 'pnl_str': str, 'error': str}
    """
    try:
        trade = fetch_trade(trade_log_id)
        if not trade:
            return {"ok": False, "error": f"Trade not found: {trade_log_id}"}

        if trade.get("status") != "OPEN":
            return {"ok": False, "error": f"Trade is not OPEN (status={trade['status']})"}

        symbol      = trade["symbol"]
        strike      = trade["strike"]
        expiry_date = trade["expiry_date"]
        option_type = trade["option_type"]
        lots        = trade["lots"]
        entry_price = float(trade["entry_price"])

        # 1. Place SELL order
        order = place_order(symbol, strike, expiry_date, option_type, lots, "SELL")
        order_id = order["order_id"]
        lot_size = order["lot_size"]

        # 2. Poll fill
        fill = poll_fill(order_id)

        exit_price = fill.get("fill_price")
        if not exit_price:
            return {
                "ok":      False,
                "order_id": order_id,
                "error":   f"Exit order not filled: status={fill['status']}. Check Dhan order book.",
            }

        # 3. Compute PnL
        pnl = (exit_price - entry_price) * lots * lot_size
        pnl = round(pnl, 2)

        # 4. Update trade_log
        now = datetime.now(timezone.utc)
        if SUPABASE:
            SUPABASE.table("trade_log").update({
                "exit_price":     float(exit_price),
                "pnl":            pnl,
                "status":         "CLOSED",
                "exit_ts":        now.isoformat(),
                "dhan_exit_order_id": order_id,
            }).eq("id", trade_log_id).execute()

            SUPABASE.table("exit_alerts").update({
                "status":   "FIRED",
                "fired_at": now.isoformat(),
            }).eq("trade_id", trade_log_id).execute()

            # 5. Update capital
            try:
                cap_rows = (SUPABASE.table("capital_tracker")
                            .select("capital").eq("symbol", symbol).limit(1).execute().data)
                if cap_rows:
                    new_cap = float(cap_rows[0]["capital"]) + pnl
                    SUPABASE.table("capital_tracker").update({
                        "capital":    round(new_cap, 2),
                        "updated_at": now.isoformat(),
                    }).eq("symbol", symbol).execute()
            except Exception as e:
                log(f"WARNING: Capital update failed: {e}")

        pnl_str = f"INR {pnl:+,.0f}"
        log(f"Exit complete: PnL={pnl_str} fill={exit_price}")

        return {"ok": True, "pnl": pnl, "pnl_str": pnl_str, "fill_price": exit_price, "error": ""}

    except Exception as e:
        log(f"ERROR execute_exit: {e}")
        return {"ok": False, "pnl": 0, "pnl_str": "", "error": str(e)}

# ── HTTP server ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs     = parse_qs(parsed.query)

        if parsed.path == "/health":
            self._json({"ok": True, "ts": now_ist().isoformat()})

        elif parsed.path == "/margin":
            try:
                data = get_margin()
                self._json({"ok": True, "data": data})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})

        elif parsed.path == "/order_status":
            order_id = qs.get("order_id", [None])[0]
            if not order_id:
                self._json({"ok": False, "error": "order_id required"})
                return
            try:
                data = get_order_status(order_id)
                self._json({"ok": True, "data": data})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})

        else:
            self._json({"ok": False, "error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        qs     = parse_qs(parsed.query)

        if parsed.path == "/place_order":
            symbol      = (qs.get("symbol",      [None])[0] or "").upper()
            strike      = qs.get("strike",      [None])[0]
            expiry_date = qs.get("expiry_date", [None])[0]
            option_type = (qs.get("option_type", [None])[0] or "").upper()
            lots        = qs.get("lots",        [None])[0]
            signal_ts   = qs.get("signal_ts",   [""])[0]

            if not all([symbol, strike, expiry_date, option_type, lots]):
                self._json({"ok": False, "error": "Missing params: symbol, strike, expiry_date, option_type, lots"})
                return

            try:
                result = execute_entry(symbol, int(strike), expiry_date, option_type, int(lots), signal_ts)
                self._json(result)
            except Exception as e:
                self._json({"ok": False, "error": str(e)})

        elif parsed.path == "/square_off":
            trade_log_id = qs.get("trade_log_id", [None])[0]
            if not trade_log_id:
                self._json({"ok": False, "error": "trade_log_id required"})
                return
            try:
                result = execute_exit(trade_log_id)
                self._json(result)
            except Exception as e:
                self._json({"ok": False, "error": str(e)})

        else:
            self._json({"ok": False, "error": "Not found"}, 404)

    def log_message(self, *a):
        pass  # suppress default access log

# ── Entry point ───────────────────────────────────────────────────────────────

def _check_env() -> None:
    missing = [k for k in ("DHAN_CLIENT_ID", "DHAN_API_TOKEN", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
               if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}")

def _test_mode() -> None:
    log("=== TEST MODE — instrument lookup only ===")
    _check_env()
    # Test: find NIFTY ATM CE for nearest expiry
    # Get today's signal to find actual strike/expiry
    if SUPABASE:
        rows = (SUPABASE.table("signal_snapshots")
                .select("symbol,atm_strike,expiry_date,dte")
                .eq("symbol", "NIFTY")
                .order("ts", desc=True)
                .limit(1)
                .execute().data)
        if rows:
            sig = rows[0]
            strike = int(sig["atm_strike"])
            expiry = sig["expiry_date"][:10]
            log(f"Testing with live signal: NIFTY {strike} CE expiry={expiry}")
            result = find_security("NIFTY", strike, expiry, "CE")
            log(f"Result: {result}")
        else:
            log("No signal found — testing with placeholder")
    else:
        log("Supabase not available — skipping signal fetch")

    log("=== TEST COMPLETE ===")

def main() -> int:
    if "--test" in sys.argv:
        _test_mode()
        return 0

    _check_env()
    log(f"MERDIAN Order Placer  http://0.0.0.0:{PORT}")
    log(f"Dhan client: {DHAN_CLIENT_ID}")
    log("Endpoints: POST /place_order  POST /square_off  GET /margin  GET /health")

    # Pre-warm scrip master
    try:
        rows = load_scrip_master()
        log(f"Scrip master loaded: {len(rows):,} instruments")
    except Exception as e:
        log(f"WARNING: Scrip master load failed: {e}")

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Stopped.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
