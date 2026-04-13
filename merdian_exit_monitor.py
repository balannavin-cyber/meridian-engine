#!/usr/bin/env python3
"""
merdian_exit_monitor.py  --  MERDIAN Phase 4A Exit Monitor
===========================================================
Polls exit_alerts table every 30 seconds.
When exit_ts is reached, fires alert via:
  - Console (always)
  - Telegram (if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env)

Run via process manager or manually:
    python merdian_exit_monitor.py

Typically started as part of merdian_start.py (add to PROCESSES dict).
"""

import os, sys, time, json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests
from supabase import create_client

SUPABASE = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

IST              = ZoneInfo("Asia/Kolkata")
POLL_INTERVAL    = 30   # seconds
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
LOT_SIZE         = {"NIFTY": 65, "SENSEX": 20}

def now_utc():
    return datetime.now(timezone.utc)

def now_ist():
    return now_utc().astimezone(IST)

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        print(f"  [WARN] Telegram send failed: {e}")

def fetch_pending_alerts():
    return (SUPABASE.table("exit_alerts")
            .select("*")
            .eq("status", "PENDING")
            .order("exit_ts")
            .execute().data)

def fetch_trade(trade_id):
    rows = SUPABASE.table("trade_log").select("*").eq("id", trade_id).limit(1).execute().data
    return rows[0] if rows else None

def fire_alert(alert):
    """Mark alert as FIRED and send notifications."""
    now = now_utc()
    SUPABASE.table("exit_alerts").update({
        "status":   "FIRED",
        "fired_at": now.isoformat(),
    }).eq("id", alert["id"]).execute()

    trade = fetch_trade(alert["trade_id"]) if alert.get("trade_id") else None
    sym       = alert["symbol"]
    strike    = alert["strike"]
    opt_type  = alert["option_type"]
    lots      = alert["lots"]
    lot_size  = LOT_SIZE.get(sym, 65)
    exit_time = datetime.fromisoformat(alert["exit_ts"]).astimezone(IST).strftime("%H:%M IST")

    entry_price = float(trade["entry_price"]) if trade else 0
    deployed    = entry_price * lot_size * lots

    # Console alert
    print(f"\n  {'!'*60}")
    print(f"  ⚡ EXIT NOW — {sym} {strike} {opt_type}")
    print(f"  Lots: {lots}  |  Exit at: {exit_time}")
    print(f"  Entry: INR {entry_price:,.1f}  |  Deployed: INR {deployed:,.0f}")
    print(f"  CLOSE POSITION on Dhan app NOW")
    print(f"  Then: python merdian_trade_logger.py --close {alert['trade_id'][:8]}")
    print(f"  {'!'*60}\n")

    # Telegram alert
    tg_msg = (
        f"*⚡ MERDIAN EXIT ALERT*\n\n"
        f"*{sym}* {strike} {opt_type} × {lots} lots\n"
        f"Exit at: {exit_time}\n"
        f"Entry price: INR {entry_price:,.1f}\n"
        f"Deployed: INR {deployed:,.0f}\n\n"
        f"Close on Dhan app immediately.\n"
        f"Then log: `python merdian_trade_logger.py --close {alert['trade_id'][:8] if alert.get('trade_id') else 'N/A'}`"
    )
    send_telegram(tg_msg)

def run():
    print(f"[{now_ist().strftime('%H:%M:%S IST')}] MERDIAN Exit Monitor started")
    print(f"  Polling every {POLL_INTERVAL}s for pending exit alerts")
    telegram_ok = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)
    print(f"  Telegram: {'ENABLED' if telegram_ok else 'DISABLED (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env)'}")

    while True:
        try:
            alerts = fetch_pending_alerts()
            now    = now_utc()
            for alert in alerts:
                exit_ts = datetime.fromisoformat(alert["exit_ts"].replace("Z", "+00:00"))
                if exit_ts.tzinfo is None:
                    exit_ts = exit_ts.replace(tzinfo=timezone.utc)
                if now >= exit_ts:
                    print(f"[{now_ist().strftime('%H:%M:%S IST')}] Alert firing: {alert['symbol']} {alert['strike']} {alert['option_type']}")
                    fire_alert(alert)
                else:
                    remaining = int((exit_ts - now).total_seconds() / 60)
                    print(f"[{now_ist().strftime('%H:%M:%S IST')}] {alert['symbol']} {alert['strike']} {alert['option_type']} — exit in {remaining}m")
        except Exception as e:
            print(f"[{now_ist().strftime('%H:%M:%S IST')}] [ERROR] {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nExit monitor stopped.")
