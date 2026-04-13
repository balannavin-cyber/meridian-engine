#!/usr/bin/env python3
"""
merdian_trade_logger.py  --  MERDIAN Phase 4A Trade Logger
===========================================================
Logs a manual trade entry from the latest signal_snapshots data.
Pre-fills all fields from the active signal. Operator confirms or overrides.

Also exposes POST /log_trade endpoint for signal dashboard button.

Usage:
    python merdian_trade_logger.py NIFTY           # interactive CLI
    python merdian_trade_logger.py NIFTY --yes     # auto-confirm (no prompts)
    python merdian_trade_logger.py --show          # show open trades

What it writes:
    trade_log row  (status=OPEN, entry_mode=MANUAL)
    exit_alerts row (exit_ts = now + 30m)
"""

import os, sys, json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client

SUPABASE = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)
IST      = ZoneInfo("Asia/Kolkata")
LOT_SIZE = {"NIFTY": 65, "SENSEX": 20}

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_ist():
    return datetime.now(timezone.utc).astimezone(IST)

def inr(v):
    if v is None: return "—"
    return f"INR {v:,.0f}"

def fetch_latest_signal(symbol):
    rows = (SUPABASE.table("signal_snapshots")
            .select("ts,action,trade_allowed,atm_strike,expiry_date,dte,"
                    "atm_iv_avg,spot,ict_tier,ict_lots_t1,ict_lots_t2,ict_lots_t3,"
                    "confidence_score")
            .eq("symbol", symbol)
            .order("ts", desc=True)
            .limit(1)
            .execute().data)
    return rows[0] if rows else None

def fetch_open_trades():
    return (SUPABASE.table("trade_log")
            .select("*")
            .eq("status", "OPEN")
            .order("entry_ts", desc=True)
            .execute().data)

def get_active_lots(sig):
    tier = sig.get("ict_tier", "NONE")
    m = {"TIER1": sig.get("ict_lots_t1"), "TIER2": sig.get("ict_lots_t2"), "TIER3": sig.get("ict_lots_t3")}
    return m.get(tier) or sig.get("ict_lots_t1") or 1

def log_trade(symbol, strike, expiry, option_type, lots, entry_price, signal_ts, notes=""):
    """Write trade_log + exit_alerts rows."""
    now      = datetime.now(timezone.utc)
    exit_ts  = now + timedelta(minutes=30)
    lot_size = LOT_SIZE.get(symbol.upper(), 65)

    # trade_log
    trade = {
        "symbol":       symbol.upper(),
        "signal_ts":    signal_ts,
        "entry_ts":     now.isoformat(),
        "exit_ts":      exit_ts.isoformat(),
        "action":       f"BUY_{option_type}",
        "strike":       int(strike),
        "expiry_date":  str(expiry),
        "option_type":  option_type,
        "lots":         int(lots),
        "entry_price":  float(entry_price),
        "status":       "OPEN",
        "entry_mode":   "MANUAL",
        "notes":        notes,
    }
    result = SUPABASE.table("trade_log").insert(trade).execute()
    trade_id = result.data[0]["id"]

    # exit_alerts
    alert = {
        "trade_id":    trade_id,
        "symbol":      symbol.upper(),
        "exit_ts":     exit_ts.isoformat(),
        "strike":      int(strike),
        "option_type": option_type,
        "lots":        int(lots),
        "status":      "PENDING",
    }
    SUPABASE.table("exit_alerts").insert(alert).execute()

    return trade_id, exit_ts

def close_trade(trade_id, exit_price):
    """Update trade_log with exit price and compute PnL."""
    trade = SUPABASE.table("trade_log").select("*").eq("id", trade_id).limit(1).execute().data
    if not trade:
        return None
    t = trade[0]
    lot_size = LOT_SIZE.get(t["symbol"], 65)
    pnl = (exit_price - float(t["entry_price"])) * int(t["lots"]) * lot_size
    now = datetime.now(timezone.utc)
    SUPABASE.table("trade_log").update({
        "exit_price": float(exit_price),
        "pnl":        round(pnl, 2),
        "status":     "CLOSED",
        "exit_ts":    now.isoformat(),
    }).eq("id", trade_id).execute()
    SUPABASE.table("exit_alerts").update({
        "status":   "FIRED",
        "fired_at": now.isoformat(),
    }).eq("trade_id", trade_id).execute()
    # Update capital
    try:
        cap_rows = SUPABASE.table("capital_tracker").select("capital").eq("symbol", t["symbol"]).limit(1).execute().data
        if cap_rows:
            new_cap = float(cap_rows[0]["capital"]) + pnl
            SUPABASE.table("capital_tracker").update({
                "capital": round(new_cap, 2),
                "updated_at": now.isoformat()
            }).eq("symbol", t["symbol"]).execute()
    except Exception as e:
        print(f"  [WARN] Capital update failed: {e}")
    return pnl

# ── CLI ───────────────────────────────────────────────────────────────────────

def show_open_trades():
    trades = fetch_open_trades()
    if not trades:
        print("\n  No open trades.\n")
        return
    print(f"\n  {'='*70}")
    print(f"  Open Trades")
    print(f"  {'='*70}")
    for t in trades:
        exit_dt = datetime.fromisoformat(t["exit_ts"]).astimezone(IST)
        now_ist_dt = now_ist()
        remaining = int((exit_dt - now_ist_dt).total_seconds() / 60)
        status_str = f"EXIT IN {remaining}m" if remaining > 0 else "⚡ EXIT NOW"
        print(f"\n  ID:     {t['id'][:8]}...")
        print(f"  Symbol: {t['symbol']}  |  {t['action']}  |  Strike: {t['strike']}  |  {t['option_type']}")
        print(f"  Lots:   {t['lots']}  |  Entry: INR {t['entry_price']:,.1f}  |  Expiry: {t['expiry_date']}")
        print(f"  Entry:  {t['entry_ts'][11:16]} IST  |  Exit target: {exit_dt.strftime('%H:%M IST')}  |  {status_str}")
    print(f"\n  {'='*70}\n")

def cli_log_trade(symbol, auto_confirm=False):
    symbol = symbol.upper()
    sig = fetch_latest_signal(symbol)

    if not sig:
        print(f"\n  No signal found for {symbol}.")
        return

    action = sig.get("action", "DO_NOTHING")
    if action == "DO_NOTHING":
        print(f"\n  {symbol} signal is DO_NOTHING — nothing to trade.")
        return

    strike     = sig.get("atm_strike")
    expiry     = sig.get("expiry_date")
    dte        = sig.get("dte")
    iv         = sig.get("atm_iv_avg")
    spot       = sig.get("spot")
    lots       = get_active_lots(sig)
    opt_type   = "PE" if action == "BUY_PE" else "CE"
    lot_size   = LOT_SIZE.get(symbol, 65)
    sig_ts     = sig.get("ts")
    conf       = sig.get("confidence_score", 0)

    print(f"\n  {'='*60}")
    print(f"  MERDIAN Trade Logger — {symbol}")
    print(f"  {'='*60}")
    print(f"  Signal:     {action}  (conf {conf:.0f})")
    print(f"  Strike:     {strike} {opt_type}")
    print(f"  Expiry:     {expiry}  (DTE {dte})")
    print(f"  Spot:       {spot:,.1f}  |  ATM IV: {iv:.1f}%" if spot and iv else "  Spot/IV: unavailable")
    print(f"  Lots:       {lots}  (lot size {lot_size} units)")
    print(f"  Signal at:  {sig_ts[11:16]} IST")
    print(f"  {'='*60}")

    # Get entry price
    if auto_confirm:
        print("  [AUTO] Logging trade at market (entry price required)")
        entry_price_str = input("  Entry price (premium paid per unit): ").strip()
    else:
        entry_price_str = input(f"\n  Enter premium paid per unit (or 'q' to quit): ").strip()
        if entry_price_str.lower() == 'q':
            print("  Cancelled.")
            return

    try:
        entry_price = float(entry_price_str)
    except ValueError:
        print("  Invalid price. Cancelled.")
        return

    lot_cost   = entry_price * lot_size
    deployed   = lot_cost * lots

    print(f"\n  Lot cost:   INR {lot_cost:,.0f}")
    print(f"  Deployed:   INR {deployed:,.0f}  ({lots} lots)")
    print(f"  Exit at:    T+30m from now")

    if not auto_confirm:
        confirm = input(f"\n  Confirm log trade? (y/n): ").strip().lower()
        if confirm != 'y':
            print("  Cancelled.")
            return

    notes = f"Manual entry. Signal conf={conf:.0f}. Spot={spot}."
    trade_id, exit_ts = log_trade(
        symbol, strike, expiry, opt_type, lots, entry_price, sig_ts, notes
    )
    exit_ist = exit_ts.astimezone(IST).strftime("%H:%M IST")

    print(f"\n  ✓ Trade logged.")
    print(f"  Trade ID:  {trade_id[:8]}...")
    print(f"  EXIT AT:   {exit_ist}  (T+30m)")
    print(f"\n  Run 'python merdian_trade_logger.py --show' to monitor.")
    print(f"  Run 'python merdian_trade_logger.py --close {trade_id[:8]}' to close.\n")

def cli_close_trade(trade_id_prefix):
    trades = fetch_open_trades()
    matches = [t for t in trades if t["id"].startswith(trade_id_prefix)]
    if not matches:
        print(f"  No open trade found with ID prefix '{trade_id_prefix}'")
        return
    t = matches[0]
    print(f"\n  Closing: {t['symbol']} {t['strike']} {t['option_type']} x{t['lots']} lots")
    print(f"  Entry price: INR {t['entry_price']:,.1f}")
    exit_price_str = input("  Exit price (premium received per unit): ").strip()
    try:
        exit_price = float(exit_price_str)
    except ValueError:
        print("  Invalid price."); return
    pnl = close_trade(t["id"], exit_price)
    lot_size = LOT_SIZE.get(t["symbol"], 65)
    pnl_str = f"INR {pnl:+,.0f}"
    print(f"\n  ✓ Trade closed.")
    print(f"  PnL: {pnl_str}  ({t['lots']} lots × {lot_size} units × INR {exit_price - float(t['entry_price']):+,.1f})")
    print(f"  Capital updated in capital_tracker.\n")

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args or '--show' in args:
        show_open_trades()
        return
    if '--close' in args:
        idx = args.index('--close')
        if idx + 1 < len(args):
            cli_close_trade(args[idx + 1])
        else:
            print("Usage: python merdian_trade_logger.py --close <trade_id_prefix>")
        return
    symbol = args[0].upper()
    auto   = '--yes' in args
    cli_log_trade(symbol, auto_confirm=auto)

if __name__ == "__main__":
    main()
