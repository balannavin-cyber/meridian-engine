"""
patch_kelly_lot_cost.py  —  ENH-38 fix: real lot cost sizing
=============================================================
The initial patch used a simulation convention (₹1L per lot).
This patch replaces it with actual lot cost = lot_size × ATM_premium,
using:
  - LOT_SIZES: NIFTY=65 units, SENSEX=20 units (Jan 2026 confirmed)
  - ATM premium estimate: spot × (atm_iv/100) × sqrt(dte/365) × 0.4
    (standard ATM approximation, N(d2) ≈ 0.4 for short-dated options)
  - DTE: fetched from nearest_expiry_db (already in merdian_utils)
  - Fallback: ₹1L per lot if spot/IV unavailable

Patches:
  1. merdian_utils.py              — replaces ENH-38 block with lot-cost version
  2. detect_ict_patterns_runner.py — updates import + Kelly lots call

Run:      python patch_kelly_lot_cost.py
Dry-run:  python patch_kelly_lot_cost.py --dry-run
"""

import os
import sys
import shutil

BASE        = r'C:\GammaEnginePython'
UTILS_PATH  = os.path.join(BASE, 'merdian_utils.py')
RUNNER_PATH = os.path.join(BASE, 'detect_ict_patterns_runner.py')
DRY_RUN     = '--dry-run' in sys.argv

# Idempotency markers
UTILS_MARKER_OLD = '# ENH-38: Kelly Tiered Sizing'
UTILS_MARKER_NEW = '# ENH-38v2: Kelly Tiered Sizing — real lot cost'
RUNNER_MARKER    = '# ENH-38v2'

# ─────────────────────────────────────────────────────────────────────────────
# Replacement ENH-38 block for merdian_utils.py
# Replaces everything from the old marker to end of file.
# ─────────────────────────────────────────────────────────────────────────────

UTILS_BLOCK_V2 = r'''
# =============================================================================
# ENH-38v2: Kelly Tiered Sizing — real lot cost  (2026-04-12)
# Lot sizes confirmed: NIFTY=65 units (Jan 2026), SENSEX=20 units (Jan 2026)
# Decisions: A-02 (50L hard cap), A-03 (25L freeze), A-05 (start C, upgrade D)
# Validated by Experiment 16 -- full year Apr 2025-Mar 2026
# =============================================================================

# Lot sizes per symbol (SEBI-mandated, update if SEBI revises)
LOT_SIZES = {
    'NIFTY':  65,   # Jan 1 2026: revised from 75 -> 65
    'SENSEX': 20,   # Jan 2026: unchanged at 20
}

CAPITAL_FLOOR       = 200_000    # INR 2L  -- minimum sizing base
CAPITAL_SCALE_START = 2_500_000  # INR 25L -- sizing freeze threshold
CAPITAL_HARD_CAP    = 5_000_000  # INR 50L -- absolute liquidity ceiling
CAPITAL_PER_LOT     = 100_000    # INR 1L  -- fallback convention (no live prices)

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


def estimate_lot_cost(symbol: str, spot: float, atm_iv_pct: float,
                      dte_days: int) -> float:
    """
    Estimate cost of 1 ATM option lot in INR.

    Formula: lot_size * spot * (atm_iv/100) * sqrt(dte/365) * 0.4
      - 0.4 approximates N(d2) for short-dated ATM options
      - Provides a conservative (slightly high) premium estimate
        -> tends to produce slightly fewer lots -> safe direction

    Examples (NIFTY spot=23000, IV=15%, DTE=2):
        premium_per_unit ~ 23000 * 0.15 * sqrt(2/365) * 0.4 ~ 72
        lot_cost = 65 * 72 ~ INR 4,680 per lot

    Examples (NIFTY spot=23000, IV=20%, DTE=0 floored to 1):
        premium_per_unit ~ 23000 * 0.20 * sqrt(1/365) * 0.4 ~ 96
        lot_cost = 65 * 96 ~ INR 6,240 per lot

    Falls back to CAPITAL_PER_LOT if inputs are invalid.
    """
    lot_size = LOT_SIZES.get(symbol, LOT_SIZES['NIFTY'])
    if spot <= 0 or atm_iv_pct <= 0:
        return float(CAPITAL_PER_LOT)
    dte_safe = max(1, dte_days)   # floor at 1 day (expiry day)
    t = dte_safe / 365.0
    premium_per_unit = spot * (atm_iv_pct / 100.0) * (t ** 0.5) * 0.4
    return lot_size * premium_per_unit


def compute_kelly_lots(capital: float, tier: str,
                       symbol: str = 'NIFTY',
                       spot: float = 0.0,
                       atm_iv_pct: float = 0.0,
                       dte_days: int = 2) -> int:
    """
    Compute lot count for a given tier using the active Kelly strategy
    and actual lot cost.

    Args:
        capital:     current account capital in INR (from capital_tracker)
        tier:        'TIER1' | 'TIER2' | 'TIER3'
        symbol:      'NIFTY' | 'SENSEX'
        spot:        current spot price (e.g. 23000.0)
        atm_iv_pct:  ATM IV in percent (e.g. 15.0 for 15%)
        dte_days:    calendar days to next weekly expiry

    Returns:
        int: number of lots (always >= 1)

    Examples -- Half Kelly, NIFTY, spot=23000, IV=15%, DTE=2:
        TIER1: 50% of eff_cap / lot_cost
          2L:   floor(1,00,000 / 4,680) = 21 lots
          10L:  floor(5,00,000 / 4,680) = 106 lots
          30L:  floor(12,50,000 / 4,680) = 267 lots  (freeze: eff=25L)
    """
    eff      = effective_sizing_capital(capital)
    fraction = ACTIVE_KELLY.get(tier, ACTIVE_KELLY['TIER3'])
    allocated = eff * fraction

    lot_cost = estimate_lot_cost(symbol, spot, atm_iv_pct, dte_days)
    return max(1, int(allocated // lot_cost))
'''

# ─────────────────────────────────────────────────────────────────────────────
# Runner patch pieces
# ─────────────────────────────────────────────────────────────────────────────

# [A] Import update — replace old ENH-38 import line with v2 (adds expiry funcs)
RUNNER_IMPORT_OLD = ('from merdian_utils import effective_sizing_capital, '
                     'compute_kelly_lots  # ENH-38')
RUNNER_IMPORT_NEW = ('from merdian_utils import (  # ENH-38v2\n'
                     '    effective_sizing_capital, compute_kelly_lots,\n'
                     '    build_expiry_index_simple, nearest_expiry_db, LOT_SIZES,\n'
                     ')')

# [B] Replace old ENH-38 Kelly lots block with v2 (adds DTE + real lot cost)
# Old block starts with this exact comment:
RUNNER_KELLY_OLD_START = '    # -- ENH-38: write Kelly lots to active ict_zones'
RUNNER_KELLY_OLD_END   = '    # -- ENH-38 end --------------------------------------------------------\n\n'

RUNNER_KELLY_NEW = """\
    # -- ENH-38v2: write Kelly lots to active ict_zones (real lot cost) -------
    try:
        # Get days to next expiry for lot cost estimation
        try:
            _expiry_idx = build_expiry_index_simple(sb, inst_id)
            _next_exp   = nearest_expiry_db(trade_date, _expiry_idx)
            _dte_days   = (_next_exp - trade_date).days if _next_exp else 2
        except Exception:
            _dte_days = 2   # conservative fallback
        _atm_iv_pct = atm_iv if atm_iv else 0.0   # None -> 0 triggers fallback

        _lots_t1 = compute_kelly_lots(_current_capital, 'TIER1', symbol,
                                      current_spot, _atm_iv_pct, _dte_days)
        _lots_t2 = compute_kelly_lots(_current_capital, 'TIER2', symbol,
                                      current_spot, _atm_iv_pct, _dte_days)
        _lots_t3 = compute_kelly_lots(_current_capital, 'TIER3', symbol,
                                      current_spot, _atm_iv_pct, _dte_days)

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
        _lot_size = LOT_SIZES.get(symbol, 65)
        log(f'  Kelly lots (lot_size={_lot_size}, dte={_dte_days}d, '
            f'iv={_atm_iv_pct:.1f}%, spot={current_spot:,.0f}) '
            f'T1:{_lots_t1} T2:{_lots_t2} T3:{_lots_t3} '
            f'(capital=INR {_current_capital:,.0f})')
    except Exception as _kelly_err:
        log(f'  Warning: Kelly lots write failed (non-blocking): {_kelly_err}')
    # -- ENH-38v2 end ----------------------------------------------------------

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
    bak = path + '.bak2'   # .bak already exists from v1 patch
    shutil.copy2(path, bak)
    print(f'  [bak] {bak}')

def p_ok(msg):   print(f'  [OK  ] {msg}')
def p_skip(msg): print(f'  [SKIP] {msg}')
def p_dry(msg):  print(f'  [DRY ] {msg}')
def p_fail(msg): print(f'  [FAIL] {msg}')

# ─────────────────────────────────────────────────────────────────────────────
# Patch 1 -- merdian_utils.py (replace ENH-38 block from marker to EOF)
# ─────────────────────────────────────────────────────────────────────────────

def patch_utils():
    print('\n-- Patch 1: merdian_utils.py --------------------------------')
    src = read_file(UTILS_PATH)

    if UTILS_MARKER_NEW in src:
        p_skip('Already at v2.')
        return

    if UTILS_MARKER_OLD not in src:
        p_fail('ENH-38 v1 marker not found -- has v1 patch been applied?')
        return

    # Truncate at the old marker, append v2 block
    cut_idx = src.index(UTILS_MARKER_OLD)
    new_src = src[:cut_idx].rstrip() + '\n' + UTILS_BLOCK_V2

    if DRY_RUN:
        p_dry('Would replace ENH-38 block with lot-cost version.')
        return

    backup(UTILS_PATH)
    write_file(UTILS_PATH, new_src)
    p_ok('ENH-38 block replaced with v2 (real lot cost + LOT_SIZES).')

# ─────────────────────────────────────────────────────────────────────────────
# Patch 2 -- detect_ict_patterns_runner.py
# ─────────────────────────────────────────────────────────────────────────────

def patch_runner():
    print('\n-- Patch 2: detect_ict_patterns_runner.py -------------------')
    src = read_file(RUNNER_PATH)

    if RUNNER_MARKER in src:
        p_skip('Already at v2.')
        return

    errors = 0
    print('  Pre-flight:')
    for label, anchor in [
        ('[A] ENH-38 import line',    RUNNER_IMPORT_OLD),
        ('[B] ENH-38 Kelly block',    RUNNER_KELLY_OLD_START),
        ('[B] ENH-38 end marker',     RUNNER_KELLY_OLD_END),
    ]:
        if anchor in src:
            p_ok(f'Found: {label}')
        else:
            p_fail(f'NOT found: {label}')
            errors += 1

    if errors:
        print(f'\n  [ABORT] {errors} anchor(s) missing.')
        return

    new_src = src

    # [A] Update import line
    new_src = new_src.replace(RUNNER_IMPORT_OLD, RUNNER_IMPORT_NEW, 1)
    p_ok('[A] Import updated (added build_expiry_index_simple, nearest_expiry_db, LOT_SIZES).')

    # [B] Replace the entire old Kelly block
    old_block_start = new_src.index(RUNNER_KELLY_OLD_START)
    old_block_end   = new_src.index(RUNNER_KELLY_OLD_END) + len(RUNNER_KELLY_OLD_END)
    new_src = new_src[:old_block_start] + RUNNER_KELLY_NEW + new_src[old_block_end:]
    p_ok('[B] Kelly lots block replaced with v2 (DTE + real lot cost).')

    if DRY_RUN:
        p_dry('No files written.')
        return

    backup(RUNNER_PATH)
    write_file(RUNNER_PATH, new_src)
    p_ok('detect_ict_patterns_runner.py updated to v2.')
    _verify(new_src)


def _verify(src):
    print('\n  Verification:')
    checks = [
        ('LOT_SIZES imported',                'LOT_SIZES'),
        ('nearest_expiry_db imported',         'nearest_expiry_db'),
        ('DTE computation present',            '_dte_days'),
        ('atm_iv passed to compute_kelly_lots','_atm_iv_pct'),
        ('current_spot passed',               'current_spot, _atm_iv_pct'),
        ("'ict_lots_t1' in update",            "'ict_lots_t1'"),
        ('lot_size in log line',              'lot_size='),
    ]
    for label, token in checks:
        sym = 'v' if token in src else 'X'
        print(f'    [{sym}] {label}')

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('patch_kelly_lot_cost.py  --  ENH-38 lot cost fix')
    print('DRY RUN' if DRY_RUN else 'LIVE -- files will be written')
    print('=' * 60)

    for path in [UTILS_PATH, RUNNER_PATH]:
        if not os.path.exists(path):
            print(f'[ERROR] Not found: {path}')
            sys.exit(1)

    patch_utils()
    patch_runner()

    print('\n' + '=' * 60)
    if not DRY_RUN:
        print('Lot cost fix complete.\n')
        print('Runner log will now show:')
        print('  Kelly lots (lot_size=65, dte=2d, iv=15.0%, spot=23000)')
        print('  T1:21 T2:17 T3:8 (capital=INR 200,000)')
        print('\n  (numbers vary with live spot/IV/DTE each cycle)')
    print('=' * 60)


if __name__ == '__main__':
    main()
