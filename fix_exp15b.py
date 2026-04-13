"""
fix_exp15b.py  --  OI-07: experiment_15b two fixes
====================================================
Fix 1 (OI-07 blocker): detect_daily_zones date type
  detect_daily_zones(daily_ohlcv, symbol, td)
  td is a date object. Function calls date.fromisoformat(td) internally
  which raises TypeError. Fix: pass str(td).

Fix 2 (correctness): LOT_SIZE values wrong for backtest period
  Script has NIFTY=25, SENSEX=15.
  Backtest covers Apr 2025 - Mar 2026:
    NIFTY: 75 units (Apr 2025 - Dec 2025), 65 units (Jan 2026 - Mar 2026)
    SENSEX: 20 units throughout (from early 2025)
  Fix: use 75/20 as the representative values.
  Note: a fully accurate backtest would switch NIFTY lot size mid-year
  (75 -> 65 on Jan 1 2026). This is acceptable for research purposes
  since Exp 15b compares strategies relatively -- all strategies use
  the same lot size, so relative rankings are unaffected.
  Using 75 (majority of the year) is the more conservative choice.

Run:      python fix_exp15b.py
Dry-run:  python fix_exp15b.py --dry-run
"""

import os
import sys
import shutil

BASE   = r'C:\GammaEnginePython'
TARGET = os.path.join(BASE, 'experiment_15b_kelly_sizing.py')
DRY    = '--dry-run' in sys.argv

# ── Fix 1: date type ──────────────────────────────────────────────────

DATE_OLD = '    d_zone_dicts = detect_daily_zones(daily_ohlcv, symbol, td)'
DATE_NEW = '    d_zone_dicts = detect_daily_zones(daily_ohlcv, symbol, str(td))  # OI-07 fix'

# ── Fix 2: lot sizes ──────────────────────────────────────────────────
# NIFTY 25 -> 75 (correct for Apr-Dec 2025, conservative for full year)
# SENSEX 15 -> 20 (correct from early 2025 onward)

LOT_OLD = 'LOT_SIZE   = {"NIFTY": 25, "SENSEX": 15}'
LOT_NEW = ('LOT_SIZE   = {"NIFTY": 75, "SENSEX": 20}'
           '  # NIFTY: 75 (Apr-Dec 2025), 65 from Jan 2026. Using 75 (majority of year).'
           ' SENSEX: 20 from early 2025.')

# ─────────────────────────────────────────────────────────────────────

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    print('=' * 60)
    print('fix_exp15b.py  --  OI-07 + lot size correction')
    print('DRY RUN' if DRY else 'LIVE')
    print('=' * 60)

    if not os.path.exists(TARGET):
        print(f'[ERROR] Not found: {TARGET}')
        sys.exit(1)

    src = read_file(TARGET)
    errors = 0

    print('\nPre-flight:')
    for label, anchor in [
        ('Fix 1: detect_daily_zones call', DATE_OLD),
        ('Fix 2: LOT_SIZE dict',           LOT_OLD),
    ]:
        if anchor in src:
            print(f'  [OK  ] Found: {label}')
        else:
            print(f'  [FAIL] NOT found: {label}')
            errors += 1

    if errors:
        print(f'\n[ABORT] {errors} anchor(s) missing.')
        sys.exit(1)

    new_src = src
    new_src = new_src.replace(DATE_OLD, DATE_NEW, 1)
    print('\n  [OK  ] Fix 1 applied: str(td) passed to detect_daily_zones.')

    new_src = new_src.replace(LOT_OLD, LOT_NEW, 1)
    print('  [OK  ] Fix 2 applied: LOT_SIZE NIFTY=75, SENSEX=20.')

    if DRY:
        print('\n[DRY] No files written.')
        return

    shutil.copy2(TARGET, TARGET + '.bak')
    print(f'  [bak] {TARGET}.bak')
    write_file(TARGET, new_src)

    # Verify
    final = read_file(TARGET)
    print('\nVerification:')
    checks = [
        ('str(td) in detect_daily_zones call', 'str(td))  # OI-07'),
        ('NIFTY lot size = 75',                '"NIFTY": 75'),
        ('SENSEX lot size = 20',               '"SENSEX": 20'),
    ]
    for label, token in checks:
        sym = 'v' if token in final else 'X'
        print(f'  [{sym}] {label}')

    print('\n' + '=' * 60)
    print('OI-07 fixed. Run:')
    print('  $env:PYTHONIOENCODING="utf-8"')
    print('  python experiment_15b_kelly_sizing.py')
    print('Expected runtime: ~3-5 hours')
    print('=' * 60)


if __name__ == '__main__':
    main()
