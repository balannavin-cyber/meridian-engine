#!/usr/bin/env python3
"""
fix_expiry_lookup.py
=====================
Patches build_atm_option_bars_mtf.py to fix expiry loading.

Problem: Script loads all expiry dates upfront with limit=100,
gets only early expiries, so nearest_expiry returns None for
most dates -> 0 rows written.

Fix: Load expiry per trade_date directly from hist_option_bars_1m.
This is one query per date but guaranteed correct.
"""
from pathlib import Path

TARGET = Path("build_atm_option_bars_mtf.py")
content = TARGET.read_text(encoding="utf-8")

# Fix 1: Remove the upfront expiry loading from main()
old_expiry_load = '''    # Load expiry dates from existing option data
    log("\\nLoading expiry dates from hist_option_bars_1m...")
    expiry_rows = fetch_all(
        sb, "hist_option_bars_1m",
        "expiry_date",
        order="expiry_date"
    )
    expiry_dates = sorted(set(
        date.fromisoformat(r["expiry_date"])
        for r in expiry_rows if r.get("expiry_date")
    ))
    log(f"  {len(expiry_dates)} unique expiry dates")

    total_5m = total_15m = 0
    for symbol, inst_info in INSTRUMENTS.items():
        w5, w15 = build_for_symbol(sb, symbol, inst_info, expiry_dates)'''

new_expiry_load = '''    # Expiry dates loaded per-date inside build_for_symbol
    log("\\nExpiry dates will be loaded per trade date.")

    total_5m = total_15m = 0
    for symbol, inst_info in INSTRUMENTS.items():
        w5, w15 = build_for_symbol(sb, symbol, inst_info, [])'''

content = content.replace(old_expiry_load, new_expiry_load)

# Fix 2: In build_for_symbol, load expiry per date
old_exp_lookup = '''        # Get expiry for this date
        exp = nearest_expiry(trade_date, expiry_dates)
        if not exp:
            continue
        dte = (exp - date.fromisoformat(trade_date)).days'''

new_exp_lookup = '''        # Get expiry for this date directly from option bars
        exp_rows = sb.table("hist_option_bars_1m").select("expiry_date").eq(
            "instrument_id", inst_id).eq("trade_date", trade_date).limit(1).execute().data
        if not exp_rows or not exp_rows[0].get("expiry_date"):
            continue
        exp = date.fromisoformat(exp_rows[0]["expiry_date"])
        dte = (exp - date.fromisoformat(trade_date)).days'''

content = content.replace(old_exp_lookup, new_exp_lookup)

TARGET.write_text(content, encoding="utf-8")

# Verify syntax
import ast
try:
    ast.parse(TARGET.read_text(encoding="utf-8"))
    print("OK: syntax valid")
    print("Fixed: expiry lookup now per-date from hist_option_bars_1m")
    print("Note: adds 1 DB query per trading date (~244 queries total)")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
