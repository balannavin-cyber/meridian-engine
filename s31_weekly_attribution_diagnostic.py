#!/usr/bin/env python3
"""
s31_weekly_attribution_diagnostic.py  (v2)
==========================================

Weekly time series of MERDIAN production signal cohort metrics, to identify
when the production edge dropped and which dimension carries the change.

v2 SCHEMA CORRECTIONS (from --probe output):
  * signal_snapshots: uses `gamma_regime` not `regime`; `cautions`, `spot`,
    `net_gex`, `gamma_concentration`, `vix_regime`, `india_vix`,
    `volatility_regime`, `breadth_regime`, `ict_pattern`, `htf_pattern`,
    `direction_bias`, `confidence_score`, `dte`, `atm_strike`, `expiry_date`
    are all direct columns — no raw-JSON parsing needed for these.
  * Spot bars: switched from hist_spot_bars_1m (instrument_id-keyed, not symbol)
    to market_spot_snapshots (symbol, ts, spot — per memory schema).
  * ict_zones: validity window is `broken_at_ts IS NULL` for ACTIVE zones,
    not an `expiry_ts` column.

Phase 1 (always runs, written to disk before Phase 2 starts):
  * Signal volume by pattern, action, trade_allowed
  * Forward spot direction WR at T+15m / T+30m / T+60m
  * Per-week regime distribution + |net_gex| median + Vector 1 step detector
  * Gate-block rates by reason (from cautions)
  * OB attachment rate (zone-touches inside ACTIVE BULL_OB/BEAR_OB vs
    signals tagged BULL_OB/BEAR_OB)

Phase 2 (optional, may fail without affecting Phase 1):
  * Option P&L at T+30m on ATM CE/PE — median + WR per week

Usage:
  python s31_weekly_attribution_diagnostic.py --probe
  python s31_weekly_attribution_diagnostic.py --skip-option-pnl
  python s31_weekly_attribution_diagnostic.py --lookback-days 180
"""

# ====================================================================
# SCHEMA NOTES — derived from probe
# ====================================================================
SIGNAL_SNAPSHOTS_COLS = ("id, ts, symbol, action, trade_allowed, "
                         "spot, atm_strike, expiry_date, dte, "
                         "ict_pattern, htf_pattern, htf_tier, ict_tier, "
                         "direction_bias, confidence_score, "
                         "gamma_regime, net_gex, gamma_concentration, "
                         "vix_regime, india_vix, volatility_regime, "
                         "breadth_regime, breadth_score, "
                         "cautions, reasons, signal_source, "
                         "po3_session_bias, "
                         "straddle_atm, straddle_slope")
MARKET_SPOT_COLS = "ts, symbol, spot"
HIST_OPT_COLS = "bar_ts, instrument_id, strike, option_type, expiry_date, close, delta, iv"
GAMMA_METRICS_COLS = "ts, symbol, regime, net_gex"
ICT_ZONES_COLS = ("id, symbol, pattern_type, direction, status, "
                  "zone_low, zone_high, zone_mid, "
                  "created_at, detected_at_ts, broken_at_ts, trade_date")

# ====================================================================
# IMPORTS
# ====================================================================
import os
import sys
import json
import argparse
import time
import math
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("[FATAL] pandas + numpy required. pip install pandas numpy")
    sys.exit(1)

try:
    from supabase import create_client, Client
except ImportError:
    print("[FATAL] supabase-py required. pip install supabase")
    sys.exit(1)

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(override=False)
except ImportError:
    pass

# ====================================================================
# CONSTANTS
# ====================================================================
IST_OFFSET = timedelta(hours=5, minutes=30)
GAMMA_UNIT_BOUNDARY = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)  # TD-S30-CANDIDATE-1
NIFTY_GRID = 50
SENSEX_GRID = 100
SYMBOLS = ('NIFTY', 'SENSEX')
DEFAULT_LOOKBACK_DAYS = 180
DEFAULT_OUTPUT_DIR = 'output_s31_attribution'
DEFAULT_PCT_THRESHOLD = 0.0

GATE_BLOCK_PATTERNS = {
    'long_gamma':   ['LONG_GAMMA'],
    'short_gamma':  ['SHORT_GAMMA'],
    'enh77':        ['ENH-77', 'ENH77'],
    'enh76':        ['ENH-76', 'ENH76'],
    'enh88':        ['ENH-88', 'ENH88', 'BULL_FVG cluster', 'BULL_FVG standalone'],
    'enh90':        ['ENH-90', 'ENH90'],
    'dte':          ['DTE'],
    'confidence':   ['confidence', 'CONFIDENCE'],
    'vix':          ['VIX', 'high_vix', 'HIGH_VIX'],
    'breadth':      ['BREADTH', 'breadth'],
    'po3':          ['PO3'],
}

PAGE_SIZE = 1000
MAX_PAGES = 1000


# ====================================================================
# SUPABASE
# ====================================================================
def get_supabase_client() -> Client:
    url = os.environ.get('SUPABASE_URL') or os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
    key = (os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
           or os.environ.get('SUPABASE_SERVICE_KEY')
           or os.environ.get('SUPABASE_KEY')
           or os.environ.get('SUPABASE_ANON_KEY'))
    if not url or not key:
        print("[FATAL] SUPABASE_URL and a service key required (env or .env in CWD)")
        print(f"  CWD: {os.getcwd()}")
        print(f"  .env exists: {os.path.exists('.env')}")
        sys.exit(1)
    return create_client(url, key)


# ====================================================================
# TIMESTAMP HELPERS
# ====================================================================
def to_utc(ts) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    s = str(ts).replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ('%Y-%m-%d %H:%M:%S+00:00', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def week_start_ist(ts_utc: datetime) -> str | None:
    if ts_utc is None:
        return None
    ist = ts_utc + IST_OFFSET
    ws = ist.date() - timedelta(days=ist.weekday())
    return ws.isoformat()


def minute_key(ts_utc: datetime) -> datetime | None:
    if ts_utc is None:
        return None
    return ts_utc.replace(second=0, microsecond=0)


# ====================================================================
# FETCH
# ====================================================================
def fetch_paginated(client, table: str, query_builder, page_size=PAGE_SIZE,
                    max_pages=MAX_PAGES, verbose=True):
    rows = []
    for page in range(max_pages):
        q = query_builder(client.table(table))
        q = q.range(page * page_size, (page + 1) * page_size - 1)
        try:
            resp = q.execute()
        except Exception as e:
            print(f"  [fetch error page={page} table={table}] {e}")
            break
        chunk = resp.data or []
        rows.extend(chunk)
        if verbose and (page % 20 == 0 or len(chunk) < page_size):
            print(f"    {table}: {len(rows)} rows (page {page})")
        if len(chunk) < page_size:
            break
    return rows


# ====================================================================
# CAUTIONS / GATE CLASSIFICATION
# ====================================================================
def cautions_to_list(cautions_field) -> list:
    if cautions_field is None:
        return []
    if isinstance(cautions_field, list):
        return [str(x) for x in cautions_field]
    if isinstance(cautions_field, str):
        s = cautions_field.strip()
        if s.startswith('['):
            try:
                v = json.loads(s)
                return [str(x) for x in v] if isinstance(v, list) else [s]
            except json.JSONDecodeError:
                return [s]
        return [s] if s else []
    return [str(cautions_field)]


def classify_gate_blocks(cautions: list) -> dict:
    flags = {gate: False for gate in GATE_BLOCK_PATTERNS}
    text = ' | '.join(cautions).lower()
    for gate, patterns in GATE_BLOCK_PATTERNS.items():
        for p in patterns:
            if p.lower() in text:
                flags[gate] = True
                break
    return flags


# ====================================================================
# SPOT FORWARD LOOKUP (from market_spot_snapshots)
# ====================================================================
def build_spot_index(spot_rows):
    """Build {symbol: {minute_utc: spot}} index from market_spot_snapshots rows."""
    idx = defaultdict(dict)
    for r in spot_rows:
        sym = r.get('symbol')
        if sym not in SYMBOLS:
            continue
        ts_utc = to_utc(r.get('ts'))
        if ts_utc is None:
            continue
        try:
            spot = float(r.get('spot') or 0)
        except (TypeError, ValueError):
            continue
        if spot <= 0:
            continue
        idx[sym][minute_key(ts_utc)] = spot
    return dict(idx)


def forward_move_pct(spot_idx_sym: dict, ts_entry_utc: datetime, horizon_min: int,
                     entry_spot_fallback: float | None) -> float | None:
    """Forward % move at T+horizon. Uses entry_spot_fallback for the entry price
    (this is signal_snapshots.spot, the canonical entry price) if minute key absent."""
    if ts_entry_utc is None:
        return None
    entry_key = minute_key(ts_entry_utc)
    p0 = spot_idx_sym.get(entry_key)
    if p0 is None or p0 == 0:
        p0 = entry_spot_fallback
    if p0 is None or p0 == 0:
        return None
    p1 = spot_idx_sym.get(entry_key + timedelta(minutes=horizon_min))
    if p1 is None or p1 == 0:
        return None
    return (p1 - p0) / p0 * 100.0


def direction_correct(action: str, fwd_pct: float | None, threshold_pct: float) -> int | None:
    if fwd_pct is None or action not in ('BUY_CE', 'BUY_PE'):
        return None
    if action == 'BUY_CE':
        return 1 if fwd_pct > threshold_pct else 0
    return 1 if fwd_pct < -threshold_pct else 0


# ====================================================================
# OB ZONES
# ====================================================================
def ob_zone_touch_at(ict_zones_rows, symbol, ts_utc, spot: float | None):
    """Return ('BULL_OB' present?, 'BEAR_OB' present?) for ACTIVE zones whose
    validity window covers ts_utc and whose [zone_low, zone_high] contains spot."""
    bull_hit = False
    bear_hit = False
    if spot is None or spot <= 0:
        return False, False
    for z in ict_zones_rows:
        if z.get('symbol') != symbol:
            continue
        pt = (z.get('pattern_type') or '').upper()
        if pt not in ('BULL_OB', 'BEAR_OB'):
            continue
        if (z.get('status') or '').upper() != 'ACTIVE':
            # Also accept zones that were ACTIVE at ts_utc but later broken
            broken = to_utc(z.get('broken_at_ts'))
            if broken is None or ts_utc >= broken:
                continue
        start = to_utc(z.get('created_at')) or to_utc(z.get('detected_at_ts'))
        if start is None or ts_utc < start:
            continue
        broken = to_utc(z.get('broken_at_ts'))
        if broken is not None and ts_utc > broken:
            continue
        try:
            lo = float(z.get('zone_low') or 0)
            hi = float(z.get('zone_high') or 0)
        except (TypeError, ValueError):
            continue
        if lo <= spot <= hi:
            if pt == 'BULL_OB':
                bull_hit = True
            else:
                bear_hit = True
    return bull_hit, bear_hit


# ====================================================================
# PHASE 1
# ====================================================================
def enrich_signals(signals, spot_idx_by_sym, ict_zones_rows, pct_threshold):
    print("\n=== Phase 1: enriching signals ===")
    rows = []
    n = len(signals)
    for i, s in enumerate(signals):
        if i % 2000 == 0:
            print(f"  enriched {i}/{n}")
        sym = s.get('symbol')
        if sym not in SYMBOLS:
            continue
        ts_utc = to_utc(s.get('ts'))
        if ts_utc is None:
            continue
        try:
            entry_spot = float(s.get('spot') or 0) or None
        except (TypeError, ValueError):
            entry_spot = None

        cautions = cautions_to_list(s.get('cautions'))
        gate_flags = classify_gate_blocks(cautions)
        action = s.get('action') or 'DO_NOTHING'
        pattern = (s.get('ict_pattern') or 'NONE').upper()

        sym_idx = spot_idx_by_sym.get(sym, {})
        fwd15 = forward_move_pct(sym_idx, ts_utc, 15, entry_spot)
        fwd30 = forward_move_pct(sym_idx, ts_utc, 30, entry_spot)
        fwd60 = forward_move_pct(sym_idx, ts_utc, 60, entry_spot)
        dc15 = direction_correct(action, fwd15, pct_threshold)
        dc30 = direction_correct(action, fwd30, pct_threshold)
        dc60 = direction_correct(action, fwd60, pct_threshold)

        bull_touch, bear_touch = ob_zone_touch_at(ict_zones_rows, sym, ts_utc, entry_spot)

        rows.append({
            'signal_id': s.get('id'),
            'ts_utc': ts_utc,
            'week': week_start_ist(ts_utc),
            'symbol': sym,
            'action': action,
            'trade_allowed': bool(s.get('trade_allowed')),
            'pattern': pattern,
            'htf_pattern': s.get('htf_pattern'),
            'htf_tier': s.get('htf_tier'),
            'ict_tier': s.get('ict_tier'),
            'direction_bias': s.get('direction_bias'),
            'confidence': s.get('confidence_score'),
            'dte': s.get('dte'),
            'entry_spot': entry_spot,
            'atm_strike': s.get('atm_strike'),
            'expiry_date': s.get('expiry_date'),
            'fwd15_pct': fwd15,
            'fwd30_pct': fwd30,
            'fwd60_pct': fwd60,
            'dc15': dc15,
            'dc30': dc30,
            'dc60': dc60,
            'gamma_regime': s.get('gamma_regime'),
            'net_gex': s.get('net_gex'),
            'gamma_concentration': s.get('gamma_concentration'),
            'vix_regime': s.get('vix_regime'),
            'india_vix': s.get('india_vix'),
            'volatility_regime': s.get('volatility_regime'),
            'breadth_regime': s.get('breadth_regime'),
            'po3_session_bias': s.get('po3_session_bias'),
            'straddle_atm': s.get('straddle_atm'),
            'straddle_slope': s.get('straddle_slope'),
            'zone_touch_bull_ob': bull_touch,
            'zone_touch_bear_ob': bear_touch,
            'n_cautions': len(cautions),
            **{f'gate_{k}': v for k, v in gate_flags.items()},
        })

    df = pd.DataFrame(rows)
    print(f"  enriched {len(df)} signals")
    return df


def weekly_rollup(df_signals: pd.DataFrame, gamma_rows: list) -> pd.DataFrame:
    print("\n=== Phase 1: weekly rollup ===")
    if df_signals.empty:
        print("  [WARN] no signals to roll up — returning empty")
        return pd.DataFrame()

    # gamma_metrics population time series (independent of signal alignment)
    g_records = []
    for r in gamma_rows:
        ts_utc = to_utc(r.get('ts'))
        if ts_utc is None:
            continue
        try:
            ng = float(r.get('net_gex') or 0)
        except (TypeError, ValueError):
            ng = 0.0
        g_records.append({
            'week': week_start_ist(ts_utc),
            'symbol': r.get('symbol'),
            'regime': r.get('regime'),
            'net_gex': ng,
            'abs_net_gex': abs(ng),
        })
    df_g = pd.DataFrame(g_records)

    weekly_rows = []
    for (week, symbol), g in df_signals.groupby(['week', 'symbol'], dropna=True):
        n = len(g)
        pat_counts = g['pattern'].value_counts().to_dict()
        directional = g[g['action'].isin(['BUY_CE', 'BUY_PE'])]

        def _wr(col):
            v = directional[col].dropna()
            return float(v.mean() * 100.0) if len(v) > 0 else None

        gate_cols = [c for c in g.columns if c.startswith('gate_')]
        gate_rates = {f'{c}_rate': float(g[c].mean()) * 100.0 if n else 0.0 for c in gate_cols}

        n_zt_bull = int(g['zone_touch_bull_ob'].sum())
        n_zt_bear = int(g['zone_touch_bear_ob'].sum())
        n_tag_bull = int((g['pattern'] == 'BULL_OB').sum())
        n_tag_bear = int((g['pattern'] == 'BEAR_OB').sum())
        att_bull = (n_tag_bull / n_zt_bull * 100.0) if n_zt_bull > 0 else None
        att_bear = (n_tag_bear / n_zt_bear * 100.0) if n_zt_bear > 0 else None

        # gamma_metrics rollup for this (week, symbol) — population level
        net_gex_median = abs_net_gex_median = None
        reg_dist = {}
        if not df_g.empty:
            gw = df_g[(df_g['week'] == week) & (df_g['symbol'] == symbol)]
            if len(gw):
                net_gex_median = float(gw['net_gex'].median())
                abs_net_gex_median = float(gw['abs_net_gex'].median())
                reg_dist = gw['regime'].value_counts(normalize=True).to_dict()

        # signal-level regime distribution (from signal_snapshots.gamma_regime)
        sig_reg_dist = g['gamma_regime'].value_counts(normalize=True).to_dict() if g['gamma_regime'].notna().any() else {}

        weekly_rows.append({
            'week': week,
            'symbol': symbol,
            'signals_total': n,
            'signals_buy_ce': int((g['action'] == 'BUY_CE').sum()),
            'signals_buy_pe': int((g['action'] == 'BUY_PE').sum()),
            'signals_do_nothing': int((g['action'] == 'DO_NOTHING').sum()),
            'signals_trade_allowed': int(g['trade_allowed'].sum()),
            'signals_trade_allowed_pct': float(g['trade_allowed'].mean()) * 100.0 if n else 0.0,
            'pat_bull_ob':  int(pat_counts.get('BULL_OB', 0)),
            'pat_bear_ob':  int(pat_counts.get('BEAR_OB', 0)),
            'pat_bull_fvg': int(pat_counts.get('BULL_FVG', 0)),
            'pat_bear_fvg': int(pat_counts.get('BEAR_FVG', 0)),
            'pat_none':     int(pat_counts.get('NONE', 0)),
            'directional_with_fwd_n': int(directional['dc30'].dropna().shape[0]),
            'wr_direction_15m': _wr('dc15'),
            'wr_direction_30m': _wr('dc30'),
            'wr_direction_60m': _wr('dc60'),
            'median_fwd_move_30m_pct': float(directional['fwd30_pct'].dropna().median()) if len(directional) and directional['fwd30_pct'].notna().any() else None,
            'mean_fwd_move_30m_pct': float(directional['fwd30_pct'].dropna().mean()) if len(directional) and directional['fwd30_pct'].notna().any() else None,
            'signal_regime_long_gamma_pct': sig_reg_dist.get('LONG_GAMMA', 0.0) * 100.0,
            'signal_regime_short_gamma_pct': sig_reg_dist.get('SHORT_GAMMA', 0.0) * 100.0,
            'signal_regime_no_flip_pct': sig_reg_dist.get('NO_FLIP', 0.0) * 100.0,
            'pop_regime_long_gamma_pct': reg_dist.get('LONG_GAMMA', 0.0) * 100.0,
            'pop_regime_short_gamma_pct': reg_dist.get('SHORT_GAMMA', 0.0) * 100.0,
            'pop_regime_no_flip_pct': reg_dist.get('NO_FLIP', 0.0) * 100.0,
            'net_gex_median': net_gex_median,
            'abs_net_gex_median': abs_net_gex_median,
            'ob_zone_touches_bull': n_zt_bull,
            'ob_zone_touches_bear': n_zt_bear,
            'ob_tagged_bull': n_tag_bull,
            'ob_tagged_bear': n_tag_bear,
            'ob_attachment_bull_pct': att_bull,
            'ob_attachment_bear_pct': att_bear,
            'median_confidence': float(g['confidence'].dropna().median()) if g['confidence'].notna().any() else None,
            'mean_india_vix': float(g['india_vix'].dropna().mean()) if g['india_vix'].notna().any() else None,
            **gate_rates,
        })

    return pd.DataFrame(weekly_rows).sort_values(['symbol', 'week']).reset_index(drop=True)


# ====================================================================
# PHASE 2 — OPTION P&L (deferred; requires instrument_id resolution)
# ====================================================================
def add_option_pnl_stub(df_signals: pd.DataFrame, df_weekly: pd.DataFrame, client) -> pd.DataFrame:
    """Option P&L reconstruction is deferred — hist_option_bars_1m has no `symbol`
    column (uses instrument_id), so we need a NIFTY/SENSEX→instrument_id mapping.
    The v1 single-row-fetch path doesn't work without that. Phase 2 will be
    rebuilt in v3 once mapping is resolved via probe."""
    print("\n=== Phase 2: option P&L (deferred to v3) ===")
    print("  hist_option_bars_1m uses instrument_id, not symbol — need mapping.")
    print("  Run with --probe-instruments to surface NIFTY/SENSEX instrument_id pairs.")
    return df_weekly


# ====================================================================
# STEP-FUNCTION DETECTOR & SUMMARY
# ====================================================================
def detect_stepfunction(series_values, dates, min_jump_ratio=10.0):
    out = []
    prev = None
    for d, v in zip(dates, series_values):
        if v is None or (isinstance(v, float) and (math.isnan(v) or v == 0)):
            continue
        if prev is not None and prev != 0:
            ratio = abs(v / prev)
            if ratio >= min_jump_ratio or (ratio > 0 and 1.0 / ratio >= min_jump_ratio):
                out.append((str(d), float(prev), float(v), float(ratio)))
        prev = v
    return out


def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("WEEKLY ATTRIBUTION SUMMARY")
    print("=" * 70)

    if df.empty:
        print("  [no weekly data]")
        return

    for symbol in SYMBOLS:
        sym = df[df['symbol'] == symbol].sort_values('week')
        if len(sym) == 0:
            print(f"\n--- {symbol}: no data ---")
            continue
        print(f"\n--- {symbol} (weeks={len(sym)}, "
              f"first={sym['week'].iloc[0]}, last={sym['week'].iloc[-1]}) ---")
        print(f"  signal volume: total {int(sym['signals_total'].sum())}, "
              f"avg/week {sym['signals_total'].mean():.0f}")

        if 'wr_direction_30m' in sym.columns:
            wr = sym['wr_direction_30m'].dropna()
            if len(wr) >= 4:
                h = len(wr) // 2
                fm, sm = wr.iloc[:h].median(), wr.iloc[h:].median()
                print(f"  WR T+30m (directional): first-half {fm:.1f}% / second-half {sm:.1f}% "
                      f"(Δ {sm - fm:+.1f}pp)")

        if 'abs_net_gex_median' in sym.columns:
            print(f"  |net_gex| Vector 1 step detector (≥10× w/w):")
            steps = detect_stepfunction(sym['abs_net_gex_median'].tolist(),
                                        sym['week'].tolist(), min_jump_ratio=10.0)
            if steps:
                for d, pv, nv, r in steps[:5]:
                    print(f"    {d}: prev={pv:.3e} → new={nv:.3e}  (×{r:.1f})")
                print("    ^ if a step lands on/near 2026-04-01 (week 2026-03-30), "
                      "Vector 1 (Cr→raw rupees) confirmed in production.")
            else:
                print("    no large step detected")

        for col, label in [
            ('signal_regime_long_gamma_pct', 'LONG_GAMMA freq (signal-level)'),
            ('signal_regime_short_gamma_pct', 'SHORT_GAMMA freq (signal-level)'),
            ('signals_trade_allowed_pct', 'trade_allowed rate'),
            ('ob_attachment_bull_pct', 'OB attachment BULL'),
            ('ob_attachment_bear_pct', 'OB attachment BEAR'),
        ]:
            if col not in sym.columns:
                continue
            s = sym[col].dropna()
            if len(s) < 4:
                continue
            h = len(s) // 2
            fm, sm = s.iloc[:h].median(), s.iloc[h:].median()
            print(f"  {label}: first-half {fm:.1f}% / second-half {sm:.1f}% (Δ {sm - fm:+.1f}pp)")

    print("\n" + "=" * 70)
    print("Open phase1_weekly.csv. The two columns that diagnose hardest:")
    print("  abs_net_gex_median (Vector 1)   wr_direction_30m (overall signal quality)")
    print("Plot both on the same date axis. Where they decouple is the inflection.")
    print("=" * 70)


# ====================================================================
# PROBE
# ====================================================================
def probe(client):
    print("\n=== PROBE ===")
    tables = [
        ('signal_snapshots', SIGNAL_SNAPSHOTS_COLS, 'ts'),
        ('market_spot_snapshots', MARKET_SPOT_COLS, 'ts'),
        ('hist_option_bars_1m', HIST_OPT_COLS, 'bar_ts'),
        ('gamma_metrics', GAMMA_METRICS_COLS, 'ts'),
        ('ict_zones', ICT_ZONES_COLS, 'created_at'),
    ]
    for table, expected, ts_col in tables:
        print(f"\n  {table}:")
        try:
            resp = client.table(table).select('*').limit(1).execute()
            row = (resp.data or [None])[0]
            print(f"    columns: {sorted(row.keys()) if row else '<empty>'}")
        except Exception as e:
            print(f"    [error] {e}")
            continue
        # time range
        try:
            r_min = client.table(table).select(ts_col).order(ts_col, desc=False).limit(1).execute()
            r_max = client.table(table).select(ts_col).order(ts_col, desc=True).limit(1).execute()
            tmin = (r_min.data or [{}])[0].get(ts_col)
            tmax = (r_max.data or [{}])[0].get(ts_col)
            print(f"    {ts_col} range: {tmin} → {tmax}")
        except Exception as e:
            print(f"    [ts range error] {e}")

    # hist_spot_bars_1m: needs instrument_id mapping
    print("\n  hist_spot_bars_1m  (instrument_id mapping):")
    try:
        resp = client.table('hist_spot_bars_1m').select('instrument_id, bar_ts, close').order(
            'bar_ts', desc=True).limit(20).execute()
        rows = resp.data or []
        ids = {r['instrument_id']: r['close'] for r in rows}
        print(f"    recent instrument_ids w/ last close: {ids}")
        print(f"    expected: NIFTY ~24000-25500 range, SENSEX ~79000-83000 range")
    except Exception as e:
        print(f"    [error] {e}")

    print("\n  hist_option_bars_1m  (instrument_id sample):")
    try:
        resp = client.table('hist_option_bars_1m').select(
            'instrument_id, strike, option_type, expiry_date'
        ).order('bar_ts', desc=True).limit(5).execute()
        rows = resp.data or []
        for r in rows:
            print(f"    {r}")
    except Exception as e:
        print(f"    [error] {e}")


# ====================================================================
# MAIN
# ====================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lookback-days', type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--skip-option-pnl', action='store_true',
                        help="(v2: Phase 2 is deferred regardless until instrument_id mapping known)")
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--pct-threshold', type=float, default=DEFAULT_PCT_THRESHOLD)
    parser.add_argument('--symbol', choices=list(SYMBOLS) + ['ALL'], default='ALL')
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = get_supabase_client()
    print(f"[OK] Supabase client created (CWD={os.getcwd()})")

    if args.probe:
        probe(client)
        return 0

    end_utc = datetime.now(timezone.utc).replace(microsecond=0)
    start_utc = end_utc - timedelta(days=args.lookback_days)
    print(f"\nFetch window: {start_utc.isoformat()} → {end_utc.isoformat()}")

    syms_filter = list(SYMBOLS) if args.symbol == 'ALL' else [args.symbol]

    print(f"\n[1/4] Fetching signal_snapshots ({args.lookback_days} days)...")
    t0 = time.time()
    signals = fetch_paginated(client, 'signal_snapshots', lambda q: (
        q.select(SIGNAL_SNAPSHOTS_COLS)
         .gte('ts', start_utc.isoformat())
         .lte('ts', end_utc.isoformat())
         .in_('symbol', syms_filter)
         .order('ts')
    ))
    print(f"  → {len(signals)} signals in {time.time() - t0:.1f}s")

    print(f"\n[2/4] Fetching market_spot_snapshots...")
    t0 = time.time()
    spot_start = (start_utc - timedelta(days=2)).isoformat()
    spot_end = (end_utc + timedelta(hours=2)).isoformat()
    spot_rows = fetch_paginated(client, 'market_spot_snapshots', lambda q: (
        q.select(MARKET_SPOT_COLS)
         .gte('ts', spot_start)
         .lte('ts', spot_end)
         .in_('symbol', syms_filter)
         .order('ts')
    ))
    print(f"  → {len(spot_rows)} spot snapshots in {time.time() - t0:.1f}s")
    if spot_rows:
        spot_ts_min = to_utc(spot_rows[0].get('ts'))
        spot_ts_max = to_utc(spot_rows[-1].get('ts'))
        print(f"    coverage: {spot_ts_min} → {spot_ts_max}")
    spot_idx_by_sym = build_spot_index(spot_rows)
    for sym in SYMBOLS:
        idx = spot_idx_by_sym.get(sym, {})
        if idx:
            mn, mx = min(idx.keys()), max(idx.keys())
            print(f"    {sym}: {len(idx)} minute bars, {mn} → {mx}")

    print(f"\n[3/4] Fetching gamma_metrics...")
    t0 = time.time()
    gamma_rows = fetch_paginated(client, 'gamma_metrics', lambda q: (
        q.select(GAMMA_METRICS_COLS)
         .gte('ts', start_utc.isoformat())
         .lte('ts', end_utc.isoformat())
         .in_('symbol', syms_filter)
         .order('ts')
    ))
    print(f"  → {len(gamma_rows)} gamma_metrics rows in {time.time() - t0:.1f}s")

    print(f"\n[4/4] Fetching ict_zones (OB only)...")
    t0 = time.time()
    ict_zones_rows = fetch_paginated(client, 'ict_zones', lambda q: (
        q.select(ICT_ZONES_COLS)
         .in_('pattern_type', ['BULL_OB', 'BEAR_OB'])
         .gte('created_at', start_utc.isoformat())
         .lte('created_at', end_utc.isoformat())
         .in_('symbol', syms_filter)
         .order('created_at')
    ))
    print(f"  → {len(ict_zones_rows)} ict_zones rows in {time.time() - t0:.1f}s")

    if not signals:
        print("\n[FATAL] no signal_snapshots in window — verify time range and symbol filter")
        return 1

    df_signals = enrich_signals(signals, spot_idx_by_sym, ict_zones_rows, args.pct_threshold)
    df_weekly = weekly_rollup(df_signals, gamma_rows)

    p1s = out_dir / 'phase1_signals_enriched.csv'
    p1w = out_dir / 'phase1_weekly.csv'
    df_signals.to_csv(p1s, index=False)
    df_weekly.to_csv(p1w, index=False)
    print(f"\n[OK] Phase 1 CSVs:")
    print(f"  {p1s.resolve()}")
    print(f"  {p1w.resolve()}")

    print_summary(df_weekly)

    if not args.skip_option_pnl:
        try:
            df_aug = add_option_pnl_stub(df_signals, df_weekly, client)
            p2 = out_dir / 'phase2_weekly_with_option_pnl.csv'
            df_aug.to_csv(p2, index=False)
            print(f"\n[OK] Phase 2 stub written: {p2.resolve()}")
        except Exception as e:
            print(f"\n[WARN] Phase 2 stub failed (Phase 1 preserved): {e}")
            traceback.print_exc()

    return 0


if __name__ == '__main__':
    sys.exit(main())
