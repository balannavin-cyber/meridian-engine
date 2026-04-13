"""
fix_exp15b_v2.py  --  OI-07 complete fix: string-keyed daily_ohlcv
===================================================================
Root cause (from error line 275 of build_ict_htf_zones.py):
  detect_daily_zones does:
    dates = list(daily_ohlcv.keys())
    prior_dates = [d for d in dates if d < target_str]
  daily_ohlcv keys are date objects, target_str is now a string
  -> TypeError: '<' not supported between date and str

Fix: pass a str-keyed copy of daily_ohlcv to detect_daily_zones only.
The date-keyed original stays intact for build_weekly_bars and everything else.
"""

import os
import sys
import shutil

BASE   = r'C:\GammaEnginePython'
TARGET = os.path.join(BASE, 'experiment_15b_kelly_sizing.py')
DRY    = '--dry-run' in sys.argv

OLD = '    d_zone_dicts = detect_daily_zones(daily_ohlcv, symbol, str(td))  # OI-07 fix'
NEW = ('    # OI-07: detect_daily_zones compares keys with str target — needs str-keyed dict\n'
       '    _daily_str = {str(k): v for k, v in daily_ohlcv.items()}\n'
       '    d_zone_dicts = detect_daily_zones(_daily_str, symbol, str(td))')

def main():
    print('fix_exp15b_v2.py  --  OI-07 string key fix')
    src = open(TARGET, encoding='utf-8').read()

    if OLD not in src:
        print(f'[FAIL] Anchor not found. Has fix_exp15b.py been run?')
        sys.exit(1)
    print('[OK  ] Anchor found.')

    if '_daily_str' in src:
        print('[SKIP] Already patched.')
        return

    new_src = src.replace(OLD, NEW, 1)

    if DRY:
        print('[DRY ] No files written.')
        return

    shutil.copy2(TARGET, TARGET + '.bak2')
    open(TARGET, 'w', encoding='utf-8').write(new_src)

    final = open(TARGET, encoding='utf-8').read()
    ok = '_daily_str' in final and 'str(k)' in final
    print(f'[{"OK  " if ok else "FAIL"}] Patch applied.')
    print('\nRun:')
    print('  $env:PYTHONIOENCODING="utf-8"')
    print('  python experiment_15b_kelly_sizing.py')

if __name__ == '__main__':
    main()
