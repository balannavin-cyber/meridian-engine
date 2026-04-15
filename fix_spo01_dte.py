#!/usr/bin/env python3
"""
fix_spo01_dte.py
=================
Fixes SPO-01: DTE null in signal_snapshots.

Root cause: compute_gamma_metrics_local.py computes expiry_date but never
derives DTE from it. DTE flows: gamma_metrics -> market_state_snapshots
-> build_trade_signal_local.py -> signal_snapshots. Null at source = null
everywhere.

Fix: add DTE computation in upsert_gamma_metrics() payload dict.
DTE = (expiry_date - today).days. Written to gamma_metrics table.
build_market_state_snapshot_local.py already reads dte from gamma_row.
"""
import shutil
from pathlib import Path

TARGET = Path("compute_gamma_metrics_local.py")
BACKUP = Path("compute_gamma_metrics_local.py.bak_spo01")

OLD_ANCHOR = '"expiry_date": result.expiry_date,'
NEW_ANCHOR = '''"expiry_date": result.expiry_date,
        "dte": (
            (__import__("datetime").date.fromisoformat(result.expiry_date) -
             __import__("datetime").date.today()).days
            if result.expiry_date else None
        ),'''

def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found.")
        return 1

    source = TARGET.read_text(encoding="utf-8")

    if '"dte":' in source and "expiry_date" in source:
        # Check if dte is already in the payload
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if '"dte":' in line and i > 0 and '"expiry_date"' in lines[max(0,i-3):i+1]:
                print("DTE fix already applied in payload.")
                return 0

    if OLD_ANCHOR not in source:
        print("ERROR: anchor not found.")
        print("Looking for expiry_date in payload...")
        for i, line in enumerate(source.splitlines(), 1):
            if '"expiry_date"' in line:
                print(f"  Line {i}: {line.strip()}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    patched = source.replace(OLD_ANCHOR, NEW_ANCHOR, 1)
    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if '"dte":' in result and "fromisoformat" in result:
        print("OK: DTE computation added to gamma_metrics payload.")
        print("\nDTE will now flow:")
        print("  compute_gamma_metrics_local.py")
        print("    -> gamma_metrics.dte")
        print("      -> market_state_snapshots.dte")
        print("        -> signal_snapshots.dte")
        print("\nSPO-01 CLOSED.")
        return 0
    else:
        print("ERROR: verification failed — restoring backup.")
        shutil.copy2(BACKUP, TARGET)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
