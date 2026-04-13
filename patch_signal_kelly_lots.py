"""
patch_signal_kelly_lots.py  —  ENH-38 step 5: lots passthrough
===============================================================
Patches build_trade_signal_local.py to forward ict_lots_t1/t2/t3
from the active ict_zones row into the signal_snapshots output dict.

Three targeted changes inside the existing ENH-37 ICT enrichment block:
  [A] Extend SELECT to include ict_lots_t1, ict_lots_t2, ict_lots_t3
  [B] Read lots from _ict_rows after enrich_signal_with_ict call
  [C] Add None fallbacks in the except block

Note on lot values:
  The runner writes the same lots to ALL active zones for a symbol/date
  (same capital, same IV, same DTE per cycle). So any zone row in
  _ict_rows carries the current lots — _ict_rows[0] is sufficient.

Run:      python patch_signal_kelly_lots.py
Dry-run:  python patch_signal_kelly_lots.py --dry-run
"""

import os
import sys
import shutil

BASE        = r'C:\GammaEnginePython'
SIGNAL_PATH = os.path.join(BASE, 'build_trade_signal_local.py')
DRY_RUN     = '--dry-run' in sys.argv
MARKER      = '# ENH-38: forward Kelly lots'

# ─────────────────────────────────────────────────────────────────────────────
# [A] Extend SELECT string to include lot columns
# ─────────────────────────────────────────────────────────────────────────────

SELECT_OLD = ('"id,pattern_type,direction,zone_high,zone_low,"'
              '\n                             "status,ict_tier,ict_size_mult,mtf_context,detected_at_ts"')

SELECT_NEW = ('"id,pattern_type,direction,zone_high,zone_low,"'
              '\n                             "status,ict_tier,ict_size_mult,mtf_context,detected_at_ts,"'
              '\n                             "ict_lots_t1,ict_lots_t2,ict_lots_t3"')

# ─────────────────────────────────────────────────────────────────────────────
# [B] Insert lots read after enrich_signal_with_ict call
# ─────────────────────────────────────────────────────────────────────────────

ENRICH_CALL = '        out = enrich_signal_with_ict(out, _ict_rows, float(spot or 0))'

ENRICH_CALL_AND_LOTS = '''        out = enrich_signal_with_ict(out, _ict_rows, float(spot or 0))
        # ENH-38: forward Kelly lots from active zone to signal_snapshots
        # All active zones carry the same lots (same capital/IV/DTE per cycle)
        if _ict_rows:
            out['ict_lots_t1'] = _ict_rows[0].get('ict_lots_t1')
            out['ict_lots_t2'] = _ict_rows[0].get('ict_lots_t2')
            out['ict_lots_t3'] = _ict_rows[0].get('ict_lots_t3')
        else:
            out['ict_lots_t1'] = None
            out['ict_lots_t2'] = None
            out['ict_lots_t3'] = None'''

# ─────────────────────────────────────────────────────────────────────────────
# [C] Add None fallbacks in the except block
# ─────────────────────────────────────────────────────────────────────────────

EXCEPT_OLD = ('        out["ict_pattern"]     = "NONE"\n'
              '        out["ict_tier"]        = "NONE"\n'
              '        out["ict_size_mult"]   = 1.0\n'
              '        out["ict_mtf_context"] = "NONE"')

EXCEPT_NEW = ('        out["ict_pattern"]     = "NONE"\n'
              '        out["ict_tier"]        = "NONE"\n'
              '        out["ict_size_mult"]   = 1.0\n'
              '        out["ict_mtf_context"] = "NONE"\n'
              '        out["ict_lots_t1"]     = None\n'
              '        out["ict_lots_t2"]     = None\n'
              '        out["ict_lots_t3"]     = None')

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def backup(path):
    bak = path + '.bak'
    shutil.copy2(path, bak)
    print(f'  [bak] {bak}')

def p_ok(msg):   print(f'  [OK  ] {msg}')
def p_skip(msg): print(f'  [SKIP] {msg}')
def p_dry(msg):  print(f'  [DRY ] {msg}')
def p_fail(msg): print(f'  [FAIL] {msg}')

# ─────────────────────────────────────────────────────────────────────────────
# Main patch
# ─────────────────────────────────────────────────────────────────────────────

def patch():
    print('=' * 60)
    print('patch_signal_kelly_lots.py  --  ENH-38 step 5')
    print('DRY RUN' if DRY_RUN else 'LIVE -- file will be written')
    print('=' * 60)

    if not os.path.exists(SIGNAL_PATH):
        print(f'[ERROR] Not found: {SIGNAL_PATH}')
        sys.exit(1)

    src = read_file(SIGNAL_PATH)

    if MARKER in src:
        p_skip('Already patched (ENH-38 marker present).')
        _verify(src)
        return

    # Pre-flight
    print('\nPre-flight anchor check:')
    errors = 0
    for label, anchor in [
        ('[A] SELECT string',           SELECT_OLD),
        ('[B] enrich_signal_with_ict',  ENRICH_CALL),
        ('[C] except fallback block',   EXCEPT_OLD),
    ]:
        if anchor in src:
            p_ok(f'Found: {label}')
        else:
            p_fail(f'NOT found: {label}')
            errors += 1

    if errors:
        print(f'\n[ABORT] {errors} anchor(s) missing.')
        return

    new_src = src

    # [A] Extend SELECT
    new_src = new_src.replace(SELECT_OLD, SELECT_NEW, 1)
    p_ok('[A] SELECT extended with ict_lots_t1/t2/t3.')

    # [B] Add lots read after enrich call
    new_src = new_src.replace(ENRICH_CALL, ENRICH_CALL_AND_LOTS, 1)
    p_ok('[B] Lots passthrough inserted after enrich_signal_with_ict.')

    # [C] Add None fallbacks in except
    new_src = new_src.replace(EXCEPT_OLD, EXCEPT_NEW, 1)
    p_ok('[C] None fallbacks added to except block.')

    if DRY_RUN:
        p_dry('No files written.')
        return

    backup(SIGNAL_PATH)
    write_file(SIGNAL_PATH, new_src)
    p_ok('build_trade_signal_local.py patched.')
    _verify(new_src)

    print('\n' + '=' * 60)
    print('ENH-38 fully complete.\n')
    print('signal_snapshots will now carry:')
    print('  ict_lots_t1, ict_lots_t2, ict_lots_t3')
    print('  (None when no active ICT zone detected this cycle)')
    print('=' * 60)


def _verify(src):
    print('\nVerification:')
    checks = [
        ('ict_lots cols in SELECT',           'ict_lots_t1,ict_lots_t2,ict_lots_t3'),
        ('lots read from _ict_rows[0]',       "_ict_rows[0].get('ict_lots_t1')"),
        ('ict_lots_t1 written to out',        "out['ict_lots_t1']"),
        ('None fallback in except (t1)',      'out["ict_lots_t1"]     = None'),
        ('None fallback in except (t2)',      'out["ict_lots_t2"]     = None'),
        ('None fallback in except (t3)',      'out["ict_lots_t3"]     = None'),
    ]
    for label, token in checks:
        sym = 'v' if token in src else 'X'
        print(f'  [{sym}] {label}')


if __name__ == '__main__':
    patch()
