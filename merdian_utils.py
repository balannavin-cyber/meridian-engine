"""
merdian_utils.py  v5
MERDIAN Shared Utilities.

v5 change (OI-26, 2026-04-21):
  Added get_nearest_expiry(sb, symbol). Reads the authoritative expiry
  from option_chain_snapshots, which is populated every 5 minutes by
  ingest_option_chain_local.py from live Dhan data. Dhan itself handles
  NSE holiday-driven expiry shifts (e.g. Thursday holiday -> Wednesday
  expiry), so this is always correct without needing calendar logic.

  Retired (kept for audit trail, no callers as of 2026-04-21):
    - build_expiry_index_simple()  -- was hardcoded to 2025-04..2026-03
                                      sample dates, producing stale/empty
                                      index on 2026-04-21. Even a fixed
                                      version would be re-implementing
                                      NSE calendar logic that Dhan does
                                      for us correctly.
    - nearest_expiry_db()          -- bisect over a locally-computed index.

  These stay in the file with DEPRECATED markers so anyone searching git
  blame sees the migration trail. Do not re-introduce callers.

Usage (v5 replacement):
    from merdian_utils import get_nearest_expiry
    ed = get_nearest_expiry(sb, "NIFTY")   # returns date or None
"""

import bisect
import time
from datetime import date


# =============================================================================
# Authoritative expiry lookup (v5, OI-26 fix)
# =============================================================================

def get_nearest_expiry(sb, symbol: str):
    """
    Return the nearest weekly expiry for `symbol` from the latest
    option_chain_snapshots row.

    option_chain_snapshots.expiry_date is written every 5-min cycle by
    ingest_option_chain_local.py from Dhan's option chain response.
    Dhan returns the nearest-expiry chain and handles NSE holiday
    rollforwards (e.g. Thursday holiday -> Wednesday expiry) natively,
    so this value is always correct without needing a local calendar.

    Args:
        sb:     supabase client
        symbol: "NIFTY" or "SENSEX"

    Returns:
        date: the nearest expiry as a datetime.date, OR
        None: if option_chain_snapshots has no rows for this symbol yet
              (pre-market startup, or ingest failure). Callers should
              fall back to a safe default (e.g. dte_days=2 for Kelly
              sizing).
    """
    try:
        rows = (
            sb.table("option_chain_snapshots")
            .select("expiry_date")
            .eq("symbol", symbol)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return None
        exp_str = rows[0].get("expiry_date")
        if not exp_str:
            return None
        return date.fromisoformat(exp_str)
    except Exception:
        return None


# =============================================================================
# DEPRECATED (2026-04-21, OI-26)
# =============================================================================
# These functions are retired. They were called only by
# detect_ict_patterns_runner.py, which now uses get_nearest_expiry() above.
#
# Why retired:
#   build_expiry_index_simple had hardcoded sample_dates covering only
#   Apr 2025 - Mar 2026. After Mar 2026 it returned a stale historical
#   index. nearest_expiry_db would then fall through to expiry_index[-1]
#   (a historical expiry), producing impossible DTEs observed on
#   2026-04-21 (SENSEX dte=-54d, NIFTY dte=252d).
#
#   Even with dynamic sample_dates, this approach re-implements NSE
#   calendar logic (holiday-driven expiry shifts) that Dhan already
#   handles correctly in the option chain response itself. The right
#   source is option_chain_snapshots.expiry_date.
#
# Do not add new callers. Use get_nearest_expiry() instead.
# =============================================================================

def build_expiry_index_simple(sb, inst_id, page_size=1000):
    """
    DEPRECATED 2026-04-21 (OI-26). Use get_nearest_expiry() instead.

    Had hardcoded sample_dates; returned stale index after Mar 2026.
    Retained only for audit trail.
    """
    all_dates = set()

    sample_dates = [
        "2025-04-03", "2025-05-02", "2025-06-02",
        "2025-07-01", "2025-08-01", "2025-09-01",
        "2025-10-01", "2025-11-03", "2025-12-01",
        "2026-01-02", "2026-02-02", "2026-03-03",
    ]

    for sample_date in sample_dates:
        rows = None
        for attempt in range(4):
            try:
                rows = (
                    sb.table("hist_option_bars_1m")
                    .select("expiry_date")
                    .eq("instrument_id", str(inst_id))
                    .gte("trade_date", sample_date)
                    .lte("trade_date", sample_date)
                    .limit(page_size)
                    .execute().data
                )
                break
            except Exception:
                if attempt == 3:
                    rows = []
                time.sleep(2 ** attempt)

        for r in (rows or []):
            if r.get("expiry_date"):
                try:
                    all_dates.add(date.fromisoformat(r["expiry_date"]))
                except (ValueError, TypeError):
                    pass

    if not all_dates:
        return []

    sorted_dates = sorted(all_dates)
    weekly = []
    for i, d in enumerate(sorted_dates):
        if i == len(sorted_dates) - 1:
            weekly.append(d)
        elif (sorted_dates[i + 1] - d).days <= 10:
            weekly.append(d)

    return weekly


def nearest_expiry_db(td, expiry_index):
    """
    DEPRECATED 2026-04-21 (OI-26). Use get_nearest_expiry() instead.

    Retained only for audit trail.
    """
    if not expiry_index:
        return None

    idx = bisect.bisect_left(expiry_index, td)
    if idx < len(expiry_index):
        return expiry_index[idx]

    return expiry_index[-1]


# =============================================================================

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

CAPITAL_FLOOR       = 10_000     # INR 10K -- trial floor (was 2L)
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
