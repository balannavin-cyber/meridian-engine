"""
patch_kelly_sizing.py  —  ENH-38: Live Kelly Tiered Sizing  (v2)
=================================================================
Patches two files using exact anchor strings confirmed from source:

  1. merdian_utils.py              — appends effective_sizing_capital()
                                     + compute_kelly_lots()

  2. detect_ict_patterns_runner.py — 3 targeted insertions:
       [A] new import line after build_ict_htf_zones import
       [B] capital_tracker read after inst_id resolved
       [C] Kelly lot write to ict_zones before "ICT detector complete" log

Architecture note:
  The runner owns ict_zones. Lots are written there per active zone.
  build_trade_signal_local.py will read lots from ict_zones in a later patch
  and forward them to signal_snapshots.ict_lots_t1/t2/t3.

Run:      python patch_kelly_sizing.py
Dry-run:  python patch_kelly_sizing.py --dry-run

Creates .bak backups. Idempotency-safe — re-running is harmless.
"""

import os
import sys
import shutil

# ── Config ────────────────────────────────────────────────────────────────────

BASE        = r'C:\GammaEnginePython'
UTILS_PATH  = os.path.join(BASE, 'merdian_utils.py')
RUNNER_PATH = os.path.join(BASE, 'detect_ict_patterns_runner.py')
DRY_RUN     = '--dry-run' in sys.argv

UTILS_MARKER  = '# ENH-38: Kelly Tiered Sizing'
RUNNER_MARKER = '# ENH-38'

# ─────────────────────────────────────────────────────────────────────────────
# Block to append to merdian_utils.py
# ─────────────────────────────────────────────────────────────────────────────

UTILS_BLOCK = r'''

# =============================================================================
# ENH-38: Kelly Tiered Sizing  (2026-04-12)
# Decisions: A-02 (50L hard cap), A-03 (25L freeze), A-05 (start C, upgrade D)
# Validated by Experiment 16 -- full year Apr 2025-Mar 2026
# =============================================================================

CAPITAL_FLOOR       = 200_000    # INR 2L  -- minimum sizing base
CAPITAL_SCALE_START = 2_500_000  # INR 25L -- sizing freeze threshold
CAPITAL_HARD_CAP    = 5_000_000  # INR 50L -- absolute liquidity ceiling
CAPITAL_PER_LOT     = 100_000    # INR 1L  -- allocation per lot (backtest convention)

# Active strategy -- change this one line to promote C -> D
KELLY_FRACTIONS_C = {'TIER1': 0.50, 'TIER2': 0.40, 'TIER3': 0.20}  # Half Kelly
KELLY_FRACTIONS_D = {'TIER1': 1.00, 'TIER2': 0.80, 'TIER3': 0.40}  # Full Kelly
ACTIVE_KELLY      = KELLY_FRACTIONS_C


def effective_sizing_capital(capital: float) -> float:
    """
    Apply capital ceiling architecture (decisions A-02/A-03, Exp 16).
      < 2L   -> floor at 2L   (prevents sizing collapse after drawdown)
      > 50L  -> cap at 50L    (liquidity ceiling)
      > 25L  -> freeze at 25L (profits accumulate, lot counts stop growing)
    """
    if capital < CAPITAL_FLOOR:
        return float(CAPITAL_FLOOR)
    if capital > CAPITAL_HARD_CAP:
        return float(CAPITAL_HARD_CAP)
    if capital > CAPITAL_SCALE_START:
        return float(CAPITAL_SCALE_START)
    return float(capital)


def compute_kelly_lots(capital: float, tier: str) -> int:
    """
    Compute lot count for a given tier using the active Kelly strategy.

    Convention (backtest-validated, Exp 15 + Exp 16):
        allocated = effective_capital * kelly_fraction(tier)
        lots      = floor(allocated / CAPITAL_PER_LOT)   [min 1]

    Examples -- Half Kelly (Strategy C):
        2L capital,  TIER1: floor(2L * 0.50 / 1L) = 1 lot
        10L capital, TIER1: floor(10L * 0.50 / 1L) = 5 lots
        30L capital, TIER1: floor(25L * 0.50 / 1L) = 12 lots  (freeze kicks in)
    """
    eff      = effective_sizing_capital(capital)
    fraction = ACTIVE_KELLY.get(tier, ACTIVE_KELLY['TIER3'])
    return max(1, int((eff * fraction) // CAPITAL_PER_LOT))
'''

# ─────────────────────────────────────────────────────────────────────────────
# Runner patch pieces -- exact anchor strings verified from source
# ─────────────────────────────────────────────────────────────────────────────

# [A] New import line inserted immediately after build_ict_htf_zones import
ANCHOR_A    = 'from build_ict_htf_zones import detect_1h_zones, upsert_zones'
INSERTION_A = '\nfrom merdian_utils import effective_sizing_capital, compute_kelly_lots  # ENH-38'

# [B] Capital tracker read -- inserted after inst_id assignment line
ANCHOR_B    = '    inst_id = inst_rows[0]["id"]'
INSERTION_B = """
    # -- ENH-38: read current capital from capital_tracker -----------------
    try:
        _cap_resp = fetch_with_retry(lambda: (
            sb.table('capital_tracker')
            .select('capital')
            .eq('symbol', symbol)
            .limit(1)
            .execute()
        ))
        _current_capital = float(_cap_resp.data[0]['capital']) if _cap_resp.data else 200_000.0
    except Exception as _cap_err:
        log(f'  Warning: capital_tracker read failed: {_cap_err} -- using floor')
        _current_capital = 200_000.0
    # -- ENH-38 end --------------------------------------------------------
"""

# [C] Lots write -- inserted BEFORE the final "ICT detector complete" log line.
#     Updates ALL ACTIVE ict_zones for this symbol/date with computed lots.
#     Non-blocking: wrapped in try/except like all other zone writes.
ANCHOR_C    = '    log(f"ICT detector complete [{symbol}]")'
INSERTION_C = """    # -- ENH-38: write Kelly lots to active ict_zones --------------------
    try:
        _lots_t1 = compute_kelly_lots(_current_capital, 'TIER1')
        _lots_t2 = compute_kelly_lots(_current_capital, 'TIER2')
        _lots_t3 = compute_kelly_lots(_current_capital, 'TIER3')
        fetch_with_retry(lambda: (
            sb.table('ict_zones')
            .update({
                'ict_lots_t1': _lots_t1,
                'ict_lots_t2': _lots_t2,
                'ict_lots_t3': _lots_t3,
            })
            .eq('symbol', symbol)
            .eq('trade_date', str(trade_date))
            .eq('status', 'ACTIVE')
            .execute()
        ))
        log(f'  Kelly lots -- T1:{_lots_t1} T2:{_lots_t2} T3:{_lots_t3} '
            f'(capital=INR {_current_capital:,.0f})')
    except Exception as _kelly_err:
        log(f'  Warning: Kelly lots write failed (non-blocking): {_kelly_err}')
    # -- ENH-38 end --------------------------------------------------------

"""

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
# Patch 1 -- merdian_utils.py
# ─────────────────────────────────────────────────────────────────────────────

def patch_utils():
    print('\n-- Patch 1: merdian_utils.py --------------------------------')
    src = read_file(UTILS_PATH)

    if UTILS_MARKER in src:
        p_skip('Already patched.')
        return

    new_src = src.rstrip() + '\n' + UTILS_BLOCK

    if DRY_RUN:
        p_dry('Would append Kelly sizing block (~45 lines).')
        return

    backup(UTILS_PATH)
    write_file(UTILS_PATH, new_src)
    p_ok('effective_sizing_capital() + compute_kelly_lots() appended.')

# ─────────────────────────────────────────────────────────────────────────────
# Patch 2 -- detect_ict_patterns_runner.py
# ─────────────────────────────────────────────────────────────────────────────

def patch_runner():
    print('\n-- Patch 2: detect_ict_patterns_runner.py -------------------')
    src    = read_file(RUNNER_PATH)
    errors = 0

    print('  Pre-flight anchor check:')
    for label, anchor in [
        ('[A] build_ict_htf_zones import line', ANCHOR_A),
        ('[B] inst_id assignment line',          ANCHOR_B),
        ('[C] ICT detector complete log line',   ANCHOR_C),
    ]:
        if anchor in src:
            p_ok(f'Found: {label}')
        else:
            p_fail(f'NOT found: {label}')
            errors += 1

    if errors:
        print(f'\n  [ABORT] {errors} anchor(s) missing. Patch not applied.')
        return

    if RUNNER_MARKER in src:
        p_skip('Already patched (ENH-38 marker present).')
        _verify(src)
        return

    new_src = src

    # [A] Import
    if 'effective_sizing_capital' not in new_src:
        new_src = new_src.replace(ANCHOR_A, ANCHOR_A + INSERTION_A, 1)
        p_ok('[A] Kelly import line added.')
    else:
        p_skip('[A] Import already present.')

    # [B] Capital read (insert after inst_id line)
    if '_current_capital' not in new_src:
        new_src = new_src.replace(ANCHOR_B, ANCHOR_B + INSERTION_B, 1)
        p_ok('[B] Capital tracker read block inserted.')
    else:
        p_skip('[B] _current_capital already present.')

    # [C] Lots write (insert before the final log line)
    if 'ict_lots_t1' not in new_src:
        new_src = new_src.replace(ANCHOR_C, INSERTION_C + ANCHOR_C, 1)
        p_ok('[C] Kelly lots write block inserted.')
    else:
        p_skip('[C] ict_lots_t1 already present.')

    if DRY_RUN:
        p_dry('No files written.')
        return

    backup(RUNNER_PATH)
    write_file(RUNNER_PATH, new_src)
    p_ok('detect_ict_patterns_runner.py patched.')
    _verify(new_src)


def _verify(src):
    print('\n  Post-patch verification:')
    checks = [
        ('effective_sizing_capital imported', 'effective_sizing_capital'),
        ('compute_kelly_lots imported',       'compute_kelly_lots'),
        ("capital_tracker read present",      "'capital_tracker'"),
        ('_current_capital assigned',         '_current_capital'),
        ('_lots_t1 computed',                 '_lots_t1'),
        ("'ict_lots_t1' in ict_zones update", "'ict_lots_t1'"),
        ('Kelly log line present',            'Kelly lots --'),
    ]
    for label, token in checks:
        sym = 'v' if token in src else 'X'
        print(f'    [{sym}] {label}')

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('patch_kelly_sizing.py v2  --  ENH-38 Kelly Tiered Sizing')
    print('DRY RUN -- no files written' if DRY_RUN else 'LIVE -- files will be written')
    print('=' * 60)

    for path in [UTILS_PATH, RUNNER_PATH]:
        if not os.path.exists(path):
            print(f'[ERROR] File not found: {path}')
            sys.exit(1)

    patch_utils()
    patch_runner()

    print('\n' + '=' * 60)
    if not DRY_RUN:
        print('ENH-38 patch complete.\n')
        print('Next steps:')
        print('  1. Run enh38_ict_zones_ddl.sql in Supabase')
        print('  2. Restart runner for next live session')
        print('  3. Check runner log for "Kelly lots -- T1:x T2:x T3:x" line')
        print('  4. Query ict_zones to confirm ict_lots_t1/t2/t3 populated')
        print('  5. Patch build_trade_signal_local.py to forward lots to signal_snapshots')
    print('=' * 60)


if __name__ == '__main__':
    main()
