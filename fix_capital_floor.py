"""
fix_capital_floor.py  --  Lower capital floor for trial runs
=============================================================
Changes:
  1. merdian_utils.py          -- CAPITAL_FLOOR 200,000 -> 10,000
  2. merdian_signal_dashboard.py -- input min + JS check 200000 -> 10000

With floor at 10K:
  50K capital, TIER1 (50%), NIFTY premium ~150, lot cost ~9,750:
    allocated = 25,000 / 9,750 = 2 lots  (workable)
  50K capital, TIER3 (20%):
    allocated = 10,000 / 9,750 = 1 lot   (minimum, fine)
"""

import os, sys, shutil

BASE   = r'C:\GammaEnginePython'
UTILS  = os.path.join(BASE, 'merdian_utils.py')
DASH   = os.path.join(BASE, 'merdian_signal_dashboard.py')
DRY    = '--dry-run' in sys.argv

def fix(path, old, new, label):
    src = open(path, encoding='utf-8').read()
    if old not in src:
        print(f'  [SKIP] {label}: anchor not found')
        return
    if DRY:
        print(f'  [DRY ] {label}: would replace')
        return
    shutil.copy2(path, path + '.bak_floor')
    open(path, 'w', encoding='utf-8').write(src.replace(old, new, 1))
    verify = open(path, encoding='utf-8').read()
    sym = 'v' if new in verify else 'X'
    print(f'  [{sym}]   {label}')

print('fix_capital_floor.py  --', 'DRY RUN' if DRY else 'LIVE')

# 1. merdian_utils.py -- lower CAPITAL_FLOOR constant
fix(UTILS,
    'CAPITAL_FLOOR       = 200_000    # INR 2L  -- minimum sizing base',
    'CAPITAL_FLOOR       = 10_000     # INR 10K -- trial floor (was 2L)',
    'merdian_utils CAPITAL_FLOOR')

# 2. dashboard -- input min attribute
fix(DASH,
    'min="200000"',
    'min="10000"',
    'dashboard input min attr')

# 3. dashboard -- JS validation check
fix(DASH,
    'if(!val||val<200000){msg.textContent="Min 2,00,000"',
    'if(!val||val<10000){msg.textContent="Min 10,000"',
    'dashboard JS min check')

if not DRY:
    print('\nDone. Restart dashboard:')
    print('  python merdian_signal_dashboard.py')
    print('\nYou can now set capital as low as INR 10,000.')
    print('At INR 50K, NIFTY TIER1: ~2 lots. TIER3: 1 lot.')
