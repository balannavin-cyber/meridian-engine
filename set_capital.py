#!/usr/bin/env python3
"""
set_capital.py  --  Set live capital for Kelly sizing
======================================================
Updates capital_tracker table. Use at:
  - Live deployment  (set real starting capital)
  - After adding funds
  - To manually correct after reviewing actual account balance

Capital ceiling rules are enforced by the engine regardless of what you set:
  Floor:  below INR 2L  -> engine sizes as if 2L
  Freeze: above INR 25L -> lots don't grow
  Cap:    above INR 50L -> engine sizes as if 50L

Usage:
    python set_capital.py --show
    python set_capital.py NIFTY 500000
    python set_capital.py SENSEX 300000
    python set_capital.py NIFTY 500000 SENSEX 300000
    python set_capital.py BOTH 500000          (sets both symbols to same value)

Examples:
    python set_capital.py NIFTY 200000         # reset to floor
    python set_capital.py BOTH 1000000         # INR 10L each
    python set_capital.py NIFTY 2500000        # INR 25L = freeze point
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

SYMBOLS   = ["NIFTY", "SENSEX"]
FLOOR     = 10_000
FREEZE    = 2_500_000
HARD_CAP  = 5_000_000

def inr(v): return f"INR {v:,.0f}"

def ceiling_note(capital):
    if capital < FLOOR:
        return f"  ⚠  Below floor -- engine will size as if {inr(FLOOR)}"
    if capital > HARD_CAP:
        return f"  ⚠  Above hard cap -- engine will size as if {inr(HARD_CAP)}"
    if capital > FREEZE:
        return f"  ℹ  Above freeze -- lots frozen at {inr(FREEZE)} equivalent"
    return f"  ✓  Within normal range -- full Kelly sizing active"

def show():
    rows = sb.table("capital_tracker").select("*").order("symbol").execute().data
    if not rows:
        print("No rows in capital_tracker. Table may not be seeded.")
        return
    print("\n  capital_tracker current state:")
    print(f"  {'Symbol':<10} {'Capital':>14} {'Effective sizing':>16}  Status")
    print(f"  {'-'*70}")
    for r in rows:
        cap = float(r["capital"])
        eff = min(max(cap, FLOOR), FREEZE)
        eff = min(eff, HARD_CAP)
        updated = r.get("updated_at", "")[:19]
        print(f"  {r['symbol']:<10} {inr(cap):>14} {inr(eff):>16}  (updated {updated})")
    print()

def set_capital(symbol, capital):
    capital = float(capital)
    now_ts  = datetime.now(timezone.utc).isoformat()
    result  = (sb.table("capital_tracker")
               .update({"capital": capital, "updated_at": now_ts})
               .eq("symbol", symbol)
               .execute())
    if result.data:
        print(f"  [OK] {symbol}: set to {inr(capital)}")
        print(ceiling_note(capital))
    else:
        print(f"  [ERR] {symbol}: update returned no data -- does the row exist?")

def main():
    args = sys.argv[1:]

    if not args or args[0] == "--show":
        show()
        return

    # Parse pairs: SYMBOL VALUE [SYMBOL VALUE ...]
    # Special: BOTH VALUE
    updates = {}
    i = 0
    while i < len(args):
        sym = args[i].upper()
        if sym == "BOTH":
            val = float(args[i+1])
            updates["NIFTY"]  = val
            updates["SENSEX"] = val
            i += 2
        elif sym in SYMBOLS:
            updates[sym] = float(args[i+1])
            i += 2
        else:
            print(f"Unknown symbol: {args[i]}. Use NIFTY, SENSEX, or BOTH.")
            sys.exit(1)

    print()
    for sym, val in updates.items():
        set_capital(sym, val)
    print()
    show()

if __name__ == "__main__":
    main()
