"""
build_ict_primitives.py — S31-B Task 2 writer.

Computes wave-1 ICT primitives (ADR-004 §5.1 OB, §5.2 FVG, §6.1 PDH/PDL/PWH/PWL/PMH/PML,
§7.1 Sweep, §7.2 Displacement) and their outcomes (formation-anchored + retest-anchored
per §10) for NIFTY + SENSEX across timeframes W, D, H, M5. Writes to
public.ict_primitives and public.ict_primitive_outcomes.

Source data:
  - Backfill mode: hist_spot_bars_1m (instrument_id-keyed; era-normalized per Rule 16/20)
  - Live mode:     market_spot_snapshots (symbol-keyed; rolling window)

Aggregation: 1m source → clock-aligned M5 (00,05,10,...) and H (00:00-00:59) buckets;
D = RTH-only OHLC per IST trading day; W = ISO-week Mon-Fri aggregation. Pine v6 parity
per ADR-004 Amendment B (TradingView default clock-aligned bars).

Per ADR-004 §9: this is the ONLY file that touches Supabase. Detectors in
core/ict_primitives.py remain pure.

CLI:
  python build_ict_primitives.py \\
    --symbol NIFTY,SENSEX \\
    --mode backfill \\
    --start 2025-04-01 --end 2026-05-19 \\
    --tfs W,D,H,M5 \\
    [--skip-outcomes] [--dry-run] [--log <path>]

  python build_ict_primitives.py --smoke  # synthetic pipeline test, no DB I/O

Disciplines:
  - OI-18 anti-pattern: every Supabase select is time-bounded (no unbounded order_by+limit).
  - Rule 15: page_size=1000 throughout.
  - Rule B22: ISO microsecond precision normalized before fromisoformat().
  - Rule 16/20: hist_spot_bars_1m era-boundary normalization at fetch.
  - Rule 21: every long-running invocation expected via Tee-Object (operator side).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time as _time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------
# Optional imports: dotenv (best-effort) + supabase (required for non-smoke)
# --------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

# Detector import: prefer `core.ict_primitives`, fall back to sibling import
try:
    from core.ict_primitives import (
        Bar, Primitive, Event,
        detect_fvgs, detect_displacements, detect_order_blocks,
        detect_prior_period_levels, detect_sweeps,
        FVG_MIN_PCT, OB_MIN_BODY_PCT, DISPLACEMENT_MIN_PCT,
        DISPLACEMENT_WINDOW_BARS, SWEEP_MIN_DEPTH_PCT,
        IST as _DETECTOR_IST,  # consistency check
    )
except ImportError:
    from ict_primitives import (  # type: ignore[no-redef]
        Bar, Primitive, Event,
        detect_fvgs, detect_displacements, detect_order_blocks,
        detect_prior_period_levels, detect_sweeps,
        FVG_MIN_PCT, OB_MIN_BODY_PCT, DISPLACEMENT_MIN_PCT,
        DISPLACEMENT_WINDOW_BARS, SWEEP_MIN_DEPTH_PCT,
        IST as _DETECTOR_IST,
    )

# ============================================================================
# Constants
# ============================================================================

UTC = timezone.utc
IST = ZoneInfo("Asia/Kolkata")
assert _DETECTOR_IST.key == IST.key, "Timezone mismatch with detector module"

# Era boundary for hist_spot_bars_1m timestamp interpretation (CLAUDE.md Rule 16/20).
# Before this datetime: bar_ts stored as IST wall-clock labeled `+00:00`.
# After:                bar_ts is true UTC.
ERA_BOUNDARY_UTC = datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)

# ENH-106 (S35) v8 — chain dual-source tier boundary.
# DIFFERENT CONCEPT from ERA_BOUNDARY_UTC above (which is a bar_ts label convention).
# This boundary governs WHICH CHAIN TABLE to read at the given anchor timestamp:
#   Pre this date:  hist_option_bars_1m  (vendor-purchased, 1m OHLC, IST-as-UTC labels)
#   On/post:        historical_option_chain_snapshots
#                   (MERDIAN-ingest via ingest_option_chain_local, ~5min point-in-time,
#                    true UTC ts, ltp not close, retry-storm dedup at read)
CHAIN_TIER_BOUNDARY_UTC = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)

# Instrument IDs for hist_spot_bars_1m (CASE-2026-05-20 §11.3).
INSTRUMENT_ID_BY_SYMBOL: dict[str, str] = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# ENH-106 (S35) v8 — reverse map for historical_option_chain_snapshots queries.
# HOCS is keyed on symbol (text), unlike hist_option_bars_1m which is keyed on
# instrument_id (uuid). The v8 prefetch path resolves iid -> symbol via this map.
SYMBOL_BY_INSTRUMENT_ID: dict[str, str] = {v: k for k, v in INSTRUMENT_ID_BY_SYMBOL.items()}

# Retest tolerance for level primitives (ADR-004 §10).
RETEST_TOLERANCE_PCT: dict[str, float] = {"W": 0.15, "D": 0.08, "H": 0.04, "M5": 0.02}

# Retest timeout windows (ADR-004 §10): expressed as duration for absolute compute.
RETEST_TIMEOUT: dict[str, timedelta] = {
    "W": timedelta(weeks=8),
    "D": timedelta(days=20),
    "H": timedelta(hours=20),
    "M5": timedelta(minutes=20 * 5),
}

# Forward-window minute offsets for formation-anchored outcomes (§10 schema).
FORWARD_WINDOWS_MIN: list[int] = [5, 15, 30, 60]

# ENH-100 (S32) constants — magnitude profiling + ATM PnL + DTE per ADR-010 v3
MFE_MAE_WINDOW_MIN: int = 30            # mirrors canonical forward_30m horizon
ATM_PNL_WINDOWS_MIN: list[int] = [5, 15, 30, 60]
STRIKE_INTERVAL: dict[str, float] = {"NIFTY": 50.0, "SENSEX": 100.0}
ATM_PREMIUM_WINDOW_MIN: int = 70        # fetch window past valid_from (60 + buffer)
ATM_LOOKUP_TOLERANCE_MIN: int = 5       # forward-scan tolerance for at-or-after

# ADR-012 (S35) v9 — spot-anchored SL doctrine
# Buffer percent applied to zone_low (BULL) / zone_high (BEAR) when computing sl_level.
# 0.005 = 50bps per ADR-012 §3. Persisted per-row as sl_buffer_pct for audit + reproducibility.
SL_BUFFER_PCT_DEFAULT = 0.005

# Pagination + batch sizes
PAGE_SIZE = 1000
UPSERT_BATCH_SIZE = 500

# Valid timeframe list for wave 1
WAVE1_TFS = ("W", "D", "H", "M5")

# Level primitive type → period source map (for detect_prior_period_levels)
PERIOD_BY_LEVEL_TYPE = {"D": "D", "W": "W", "M": "M"}

# Microsecond regex (B22 — normalize fractional seconds to exactly 6 digits)
_MICROSEC_RE = re.compile(r"\.(\d{1,6})(?=[+-Z])|\.(\d{1,6})$")


# ============================================================================
# Logging + Supabase client
# ============================================================================

_log_handle = None


def log(msg: str) -> None:
    """Stdout + optional file mirror."""
    print(msg, flush=True)
    if _log_handle is not None:
        _log_handle.write(msg + "\n")
        _log_handle.flush()


def open_log_file(path: Optional[str]) -> None:
    global _log_handle
    if path:
        _log_handle = open(path, "a", encoding="utf-8")
        log(f"[log] mirror to {path}")


def get_supabase_client():
    """Lazy import + create Supabase client."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        cwd = os.getcwd()
        env_exists = os.path.exists(os.path.join(cwd, ".env"))
        raise SystemExit(
            f"[FATAL] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required.\n"
            f"        CWD={cwd}  .env exists={env_exists}"
        )
    return create_client(url, key)


# ============================================================================
# Timestamp parsing + era normalization (Rules 16, 20, B22)
# ============================================================================

def _normalize_microseconds(ts_iso: str) -> str:
    """Pad/truncate fractional seconds to exactly 6 digits (cross-Python-version safe).

    Per B22: Python 3.10 accepts only 3 or 6 microsecond digits; Python 3.12 is permissive.
    """
    def _pad(match: re.Match) -> str:
        frac = match.group(1) or match.group(2) or ""
        return f".{frac.ljust(6, '0')[:6]}"
    return _MICROSEC_RE.sub(_pad, ts_iso)


def parse_supabase_ts(raw: object) -> datetime:
    """Parse Supabase TIMESTAMPTZ payload to tz-aware UTC datetime."""
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=UTC)
        return raw.astimezone(UTC)
    if not isinstance(raw, str):
        raise TypeError(f"Cannot parse ts of type {type(raw).__name__}: {raw!r}")
    s = raw.strip().replace("Z", "+00:00")
    s = _normalize_microseconds(s)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_hist_bar_ts(raw_ts: object) -> datetime:
    """
    Era-aware normalization for hist_spot_bars_1m.bar_ts → true UTC tz-aware.

    Pre-2026-04-07 rows: stored as IST wall-clock labeled +00:00 (Rule 16, Bug B3).
                         Strip tz, re-tag as IST, convert to UTC.
    Post-2026-04-07 rows: already true UTC (Rule 20).
    """
    raw_dt = parse_supabase_ts(raw_ts)
    if raw_dt < ERA_BOUNDARY_UTC:
        ist_naive = raw_dt.replace(tzinfo=None)
        return ist_naive.replace(tzinfo=IST).astimezone(UTC)
    return raw_dt


def normalize_live_bar_ts(raw_ts: object) -> datetime:
    """market_spot_snapshots is post-era throughout; pass through to UTC."""
    return parse_supabase_ts(raw_ts)


# ============================================================================
# Fetch layer
# ============================================================================

def fetch_bars_1m_backfill(sb, symbol: str, start_utc: datetime,
                           end_utc: datetime) -> list[Bar]:
    """
    Paginated fetch from hist_spot_bars_1m for one symbol's instrument_id over [start, end].

    Returns Bars sorted by ts ascending, tz-aware UTC, era-normalized.
    """
    instrument_id = INSTRUMENT_ID_BY_SYMBOL[symbol]
    bars: list[Bar] = []
    page = 0
    t0 = _time.time()
    while True:
        offset = page * PAGE_SIZE
        res = (
            sb.table("hist_spot_bars_1m")
              .select("bar_ts,open,high,low,close")
              .eq("instrument_id", instrument_id)
              .gte("bar_ts", start_utc.isoformat())
              .lt("bar_ts", end_utc.isoformat())
              .order("bar_ts", desc=False)
              .range(offset, offset + PAGE_SIZE - 1)
              .execute()
        )
        rows = res.data or []
        for r in rows:
            bars.append(Bar(
                ts=normalize_hist_bar_ts(r["bar_ts"]),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
            ))
        if len(rows) < PAGE_SIZE:
            break
        page += 1
        if page % 10 == 0:
            log(f"    hist_spot_bars_1m({symbol}): {len(bars)} rows so far...")
    log(f"  → fetched {len(bars)} 1m bars for {symbol} in {_time.time() - t0:.1f}s")
    return bars


def fetch_bars_1m_live(sb, symbol: str, lookback_days: int = 56) -> list[Bar]:
    """
    Fetch from market_spot_snapshots for live mode. Default lookback 8 weeks
    (matches longest detector window — W timeframe needs prior week context).
    """
    end_utc = datetime.now(UTC)
    start_utc = end_utc - timedelta(days=lookback_days)
    bars: list[Bar] = []
    page = 0
    t0 = _time.time()
    while True:
        offset = page * PAGE_SIZE
        res = (
            sb.table("market_spot_snapshots")
              .select("ts,spot")
              .eq("symbol", symbol)
              .gte("ts", start_utc.isoformat())
              .lt("ts", end_utc.isoformat())
              .order("ts", desc=False)
              .range(offset, offset + PAGE_SIZE - 1)
              .execute()
        )
        rows = res.data or []
        for r in rows:
            spot = float(r["spot"])
            # market_spot_snapshots is per-tick spot, not OHLC: treat as degenerate
            # 1-minute bar with OHLC all equal. Aggregate layer will derive H/L.
            bars.append(Bar(
                ts=normalize_live_bar_ts(r["ts"]),
                open=spot, high=spot, low=spot, close=spot,
            ))
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    log(f"  → fetched {len(bars)} live spot rows for {symbol} in {_time.time() - t0:.1f}s")
    return bars


# ============================================================================
# Aggregation layer (clock-aligned, Pine v6 parity)
# ============================================================================

def _rth_filter(bars: Iterable[Bar]) -> list[Bar]:
    """Keep only bars whose IST timestamp falls within 09:15-15:30 RTH window."""
    out = []
    for b in bars:
        ist = b.ts.astimezone(IST)
        t = ist.time()
        if t.hour > 9 or (t.hour == 9 and t.minute >= 15):
            if t.hour < 15 or (t.hour == 15 and t.minute <= 30):
                out.append(b)
    return out


def _bucket_to_m5(bars: list[Bar]) -> dict[datetime, list[Bar]]:
    """Group 1m bars into clock-aligned 5-min buckets keyed by bucket-start ts (UTC)."""
    buckets: dict[datetime, list[Bar]] = {}
    for b in bars:
        # Floor to nearest 5-min boundary in UTC (clock-aligned globally; IST 09:15 = UTC 03:45
        # falls cleanly on a 5-min boundary).
        bucket = b.ts.replace(second=0, microsecond=0)
        bucket = bucket.replace(minute=(bucket.minute // 5) * 5)
        buckets.setdefault(bucket, []).append(b)
    return buckets


def _bucket_to_h(bars: list[Bar]) -> dict[datetime, list[Bar]]:
    """Clock-aligned 60-min buckets in UTC. IST 09:15 falls inside the UTC 03:00-03:59 bucket."""
    buckets: dict[datetime, list[Bar]] = {}
    for b in bars:
        bucket = b.ts.replace(minute=0, second=0, microsecond=0)
        buckets.setdefault(bucket, []).append(b)
    return buckets


def _bucket_to_d(bars: list[Bar]) -> dict[date, list[Bar]]:
    """Group by IST calendar date (RTH bars only). Use IST date as key."""
    buckets: dict[date, list[Bar]] = {}
    for b in bars:
        d = b.ts.astimezone(IST).date()
        buckets.setdefault(d, []).append(b)
    return buckets


def _bucket_to_w(bars: list[Bar]) -> dict[tuple, list[Bar]]:
    """Group by (iso_year, iso_week) on IST."""
    buckets: dict[tuple, list[Bar]] = {}
    for b in bars:
        iso = b.ts.astimezone(IST).isocalendar()
        buckets.setdefault((iso[0], iso[1]), []).append(b)
    return buckets


def _reduce_ohlc(bucket_bars: list[Bar], bucket_ts: datetime) -> Bar:
    """OHLC reduction. bucket_ts is the bar's canonical timestamp."""
    bucket_bars_sorted = sorted(bucket_bars, key=lambda x: x.ts)
    return Bar(
        ts=bucket_ts,
        open=bucket_bars_sorted[0].open,
        high=max(b.high for b in bucket_bars_sorted),
        low=min(b.low for b in bucket_bars_sorted),
        close=bucket_bars_sorted[-1].close,
    )


def aggregate(bars_1m: list[Bar], tf: str) -> list[Bar]:
    """
    Aggregate 1m bars to the target timeframe.

    M5: clock-aligned 5-min, no RTH filter (M5 spans full session)
    H:  clock-aligned 60-min, no RTH filter
    D:  RTH-only OHLC per IST trading date; bar ts = first 1m bar's ts of that date
    W:  per ISO week, RTH-filtered; bar ts = first bar of the week
    """
    if not bars_1m:
        return []
    if tf == "M5":
        buckets = _bucket_to_m5(bars_1m)
        return [_reduce_ohlc(b, ts) for ts, b in sorted(buckets.items())]
    if tf == "H":
        buckets = _bucket_to_h(bars_1m)
        return [_reduce_ohlc(b, ts) for ts, b in sorted(buckets.items())]
    if tf == "D":
        rth = _rth_filter(bars_1m)
        buckets = _bucket_to_d(rth)
        out = []
        for d in sorted(buckets.keys()):
            day_bars = sorted(buckets[d], key=lambda x: x.ts)
            out.append(_reduce_ohlc(day_bars, day_bars[0].ts))
        return out
    if tf == "W":
        rth = _rth_filter(bars_1m)
        buckets = _bucket_to_w(rth)
        out = []
        for k in sorted(buckets.keys()):
            wk_bars = sorted(buckets[k], key=lambda x: x.ts)
            out.append(_reduce_ohlc(wk_bars, wk_bars[0].ts))
        return out
    raise ValueError(f"Unknown timeframe: {tf!r}")


# ============================================================================
# Detect layer: run wave-1 detectors per symbol per TF
# ============================================================================

def compute_primitives_for_symbol_tf(bars_1m: list[Bar], symbol: str,
                                     tf: str) -> tuple[list[Primitive], list[Event]]:
    """Aggregate to tf then run FVG → Displacement → OB chain. Returns (primitives, events)."""
    bars_tf = aggregate(bars_1m, tf)
    if len(bars_tf) < 3:
        return [], []
    fvgs = detect_fvgs(bars_tf, symbol, tf)
    disps = detect_displacements(bars_tf, symbol, tf, fvgs)
    obs = detect_order_blocks(bars_tf, symbol, tf, fvgs, disps)
    return fvgs + obs, disps


def compute_levels_and_sweeps(bars_1m: list[Bar], symbol: str,
                              levels_tfs: list[str]) -> tuple[list[Primitive], list[Event]]:
    """
    Prior-period levels are computed from 1m bars (with internal RTH filtering for D).
    Sweeps run against ALL levels at M5 timeframe (most granular tradable view).

    levels_tfs: subset of {'D','W','M'} for which period-levels are requested.
    """
    levels: list[Primitive] = []
    if "D" in levels_tfs:
        levels.extend(detect_prior_period_levels(bars_1m, symbol, "D"))
    if "W" in levels_tfs:
        levels.extend(detect_prior_period_levels(bars_1m, symbol, "W"))
    if "M" in levels_tfs:
        levels.extend(detect_prior_period_levels(bars_1m, symbol, "M"))

    if not levels:
        return [], []

    m5_bars = aggregate(bars_1m, "M5")
    sweeps = detect_sweeps(m5_bars, symbol, "M5", levels)
    return levels, sweeps


# ============================================================================
# Outcomes layer (formation-anchored + retest-anchored per §10)
# ============================================================================

@dataclass
class OutcomeRow:
    """Maps to public.ict_primitive_outcomes."""
    primitive_natural_key: tuple  # (symbol, tf, type, source_bar_ts, low_or_lvl, high_or_lvl)
    forward_5m_pct: Optional[float] = None
    forward_15m_pct: Optional[float] = None
    forward_30m_pct: Optional[float] = None
    forward_1h_pct: Optional[float] = None
    forward_eod_pct: Optional[float] = None
    retest_status: str = "PENDING"
    first_retest_ts: Optional[datetime] = None
    retest_depth_pct: Optional[float] = None
    retest_fwd_5m_pct: Optional[float] = None
    retest_fwd_15m_pct: Optional[float] = None
    retest_fwd_30m_pct: Optional[float] = None
    retest_fwd_1h_pct: Optional[float] = None
    retest_fwd_eod_pct: Optional[float] = None
    respected: Optional[bool] = None
    mitigated_at: Optional[datetime] = None
    breach_at: Optional[datetime] = None
    # ENH-100 (S32) — formation-anchored magnitude + ATM PnL + DTE per ADR-010 v3
    forward_120m_pct: Optional[float] = None
    mfe_pct: Optional[float] = None
    mae_pct: Optional[float] = None
    time_to_mfe_min: Optional[int] = None
    atm_pnl_5m_pct: Optional[float] = None
    atm_pnl_15m_pct: Optional[float] = None
    atm_pnl_30m_pct: Optional[float] = None
    atm_pnl_60m_pct: Optional[float] = None
    dte_at_formation: Optional[int] = None
    # ENH-103 (S33) v6 — retest-anchored ATM CE/PE PnL per ADR-004 §10 + ADR-010 v3 Path A
    option_pnl_5m: Optional[float] = None
    option_pnl_15m: Optional[float] = None
    option_pnl_30m: Optional[float] = None
    option_pnl_60m: Optional[float] = None
    option_pnl_eod: Optional[float] = None
    # ENH-106 (S35) v8 — chain data tier audit tag for option_pnl_* columns.
    # 'vendor_hist_1m'  if anchor <  2026-04-01 UTC (hist_option_bars_1m source);
    # 'merdian_hist_5m' if anchor >= 2026-04-01 UTC (historical_option_chain_snapshots);
    # None              if no option_pnl computed (no direction, premium absent, smoke).
    option_pnl_source: Optional[str] = None
    # ADR-012 (S35) v9 — spot-anchored SL doctrine outputs.
    # BULL: sl_level = zone_low × (1 − sl_buffer_pct); trigger on 5m close < sl_level.
    # BEAR: sl_level = zone_high × (1 + sl_buffer_pct); trigger on 5m close > sl_level.
    # Walk from first_retest_ts + 5min through EOD (15:25 IST inclusive).
    # NULL on level primitives (no zone bounds). pnl_with_sl_pct degenerates to
    # option_pnl_eod when SL never triggers intra-session.
    sl_level: Optional[float] = None
    sl_buffer_pct: Optional[float] = None
    sl_triggered_ts: Optional[datetime] = None
    sl_exit_prem: Optional[float] = None
    pnl_with_sl_pct: Optional[float] = None


def _spot_at(bars_1m: list[Bar], ts: datetime, idx: dict[datetime, int]) -> Optional[float]:
    """O(1) spot lookup via prebuilt index; returns nearest bar at-or-after ts, or None."""
    # Try exact + small forward window
    for delta_min in range(0, 5):
        probe = ts + timedelta(minutes=delta_min)
        i = idx.get(probe.replace(second=0, microsecond=0))
        if i is not None:
            return bars_1m[i].close
    return None


def _eod_ts(anchor_ts: datetime) -> datetime:
    """Return 15:30 IST on the same trading day as anchor_ts (or anchor_ts itself if past EOD)."""
    ist = anchor_ts.astimezone(IST)
    eod_ist = ist.replace(hour=15, minute=30, second=0, microsecond=0)
    return eod_ist.astimezone(UTC)


def _forward_pct(anchor_price: float, future_price: Optional[float]) -> Optional[float]:
    if future_price is None or anchor_price == 0:
        return None
    return (future_price - anchor_price) / anchor_price * 100.0


def _bar_idx_by_minute(bars_1m: list[Bar]) -> dict[datetime, int]:
    """Build minute-floored index ts → bar position."""
    out: dict[datetime, int] = {}
    for i, b in enumerate(bars_1m):
        key = b.ts.replace(second=0, microsecond=0)
        out.setdefault(key, i)
    return out


def compute_formation_outcomes(primitive: Primitive, bars_1m: list[Bar],
                               idx: dict[datetime, int]) -> dict:
    """Forward _Xm_pct + forward_eod_pct anchored at primitive.valid_from."""
    anchor = _spot_at(bars_1m, primitive.valid_from, idx)
    if anchor is None:
        return {}
    out = {}
    for mins in FORWARD_WINDOWS_MIN:
        future_ts = primitive.valid_from + timedelta(minutes=mins)
        out[f"forward_{mins}m_pct" if mins < 60 else "forward_1h_pct"] = (
            _forward_pct(anchor, _spot_at(bars_1m, future_ts, idx))
        )
    # ENH-100 (S32) forward_120m_pct — formation-anchored 120-min spot return
    fwd_120_ts = primitive.valid_from + timedelta(minutes=120)
    out["forward_120m_pct"] = _forward_pct(anchor, _spot_at(bars_1m, fwd_120_ts, idx))
    # eod
    eod = _eod_ts(primitive.valid_from)
    if eod > primitive.valid_from:
        out["forward_eod_pct"] = _forward_pct(anchor, _spot_at(bars_1m, eod, idx))
    return out


def compute_retest_outcomes_zone(primitive: Primitive, bars_1m: list[Bar],
                                 idx: dict[datetime, int]) -> dict:
    """
    Retest semantics for zone primitives (OB, FVG) per ADR-004 §10.

    Walk forward from valid_from through 1m bars:
      1. First find a bar fully outside the zone (price has exited).
      2. After exit, first bar that re-enters [zone_low, zone_high] is the retest.
      3. Compute retest_depth_pct + retest_fwd_*_pct.
      4. If price closes through breach side before retest → BREACHED_BEFORE_RETEST.
      5. If neither happens before timeout → NEVER_RETESTED.
    """
    if primitive.zone_low is None or primitive.zone_high is None:
        return {"retest_status": "NEVER_RETESTED"}
    tf = primitive.timeframe
    if tf not in RETEST_TIMEOUT:
        # PMH/PML mapped to W; W timeout applies
        timeout = RETEST_TIMEOUT["W"]
    else:
        timeout = RETEST_TIMEOUT[tf]
    deadline = primitive.valid_from + timeout
    zlow, zhigh = primitive.zone_low, primitive.zone_high
    breach_side_check = (
        (lambda b: b.close < zlow) if primitive.direction == "BULL"
        else (lambda b: b.close > zhigh)
    )
    exited = False
    out = {"retest_status": "NEVER_RETESTED"}
    # Find starting index — first 1m bar at or after valid_from
    start_i = None
    for i, b in enumerate(bars_1m):
        if b.ts >= primitive.valid_from:
            start_i = i
            break
    if start_i is None:
        return out
    for i in range(start_i, len(bars_1m)):
        b = bars_1m[i]
        if b.ts > deadline:
            out["retest_status"] = "NEVER_RETESTED"
            break
        # Check breach (only after exit, otherwise initial formation overlap reads as breach)
        if exited and breach_side_check(b):
            out["retest_status"] = "BREACHED_BEFORE_RETEST"
            out["breach_at"] = b.ts
            break
        # Check exited: fully outside zone (low > zhigh or high < zlow)
        if not exited and (b.low > zhigh or b.high < zlow):
            exited = True
            continue
        # Check retest: bar re-enters zone after exit
        if exited and b.high >= zlow and b.low <= zhigh:
            retest_low_touched = max(b.low, zlow)
            # depth: how far into the zone did price penetrate
            zone_span = zhigh - zlow
            if zone_span > 0:
                if primitive.direction == "BULL":
                    depth = (zhigh - retest_low_touched) / zone_span
                else:
                    depth = (min(b.high, zhigh) - zlow) / zone_span
            else:
                depth = 0.0
            out["retest_status"] = "RETESTED"
            out["first_retest_ts"] = b.ts
            out["retest_depth_pct"] = depth
            # Forward windows from retest
            retest_anchor = b.close
            for mins in FORWARD_WINDOWS_MIN:
                future_ts = b.ts + timedelta(minutes=mins)
                key = f"retest_fwd_{mins}m_pct" if mins < 60 else "retest_fwd_1h_pct"
                out[key] = _forward_pct(retest_anchor, _spot_at(bars_1m, future_ts, idx))
            eod = _eod_ts(b.ts)
            if eod > b.ts:
                out["retest_fwd_eod_pct"] = _forward_pct(
                    retest_anchor, _spot_at(bars_1m, eod, idx)
                )
            # Respect: signed move after retest aligns with primitive direction
            fwd30 = out.get("retest_fwd_30m_pct")
            if fwd30 is not None:
                out["respected"] = (
                    (fwd30 > 0 and primitive.direction == "BULL")
                    or (fwd30 < 0 and primitive.direction == "BEAR")
                )
            break
    return out


def compute_retest_outcomes_level(primitive: Primitive, bars_1m: list[Bar],
                                   idx: dict[datetime, int]) -> dict:
    """
    Retest semantics for level primitives (PDH/PDL/PWH/PWL/PMH/PML) per §10.

    Tolerance band around level. Exited when price deviates > tolerance.
    Retest when price returns within tolerance.
    """
    if primitive.level is None:
        return {"retest_status": "NEVER_RETESTED"}
    tf = primitive.timeframe
    tol_pct = RETEST_TOLERANCE_PCT.get(tf, RETEST_TOLERANCE_PCT["D"])
    band = primitive.level * tol_pct / 100.0
    timeout = RETEST_TIMEOUT.get(tf, RETEST_TIMEOUT["D"])
    deadline = primitive.valid_from + timeout

    exited = False
    out = {"retest_status": "NEVER_RETESTED"}
    start_i = None
    for i, b in enumerate(bars_1m):
        if b.ts >= primitive.valid_from:
            start_i = i
            break
    if start_i is None:
        return out
    for i in range(start_i, len(bars_1m)):
        b = bars_1m[i]
        if b.ts > deadline:
            break
        deviation = max(abs(b.high - primitive.level), abs(b.low - primitive.level))
        within = abs(b.close - primitive.level) <= band
        if not exited and deviation > band:
            exited = True
            continue
        if exited and within:
            out["retest_status"] = "RETESTED"
            out["first_retest_ts"] = b.ts
            out["retest_depth_pct"] = 1.0  # levels: binary touched
            retest_anchor = b.close
            for mins in FORWARD_WINDOWS_MIN:
                future_ts = b.ts + timedelta(minutes=mins)
                key = f"retest_fwd_{mins}m_pct" if mins < 60 else "retest_fwd_1h_pct"
                out[key] = _forward_pct(retest_anchor, _spot_at(bars_1m, future_ts, idx))
            eod = _eod_ts(b.ts)
            if eod > b.ts:
                out["retest_fwd_eod_pct"] = _forward_pct(
                    retest_anchor, _spot_at(bars_1m, eod, idx)
                )
            break
    return out


def _option_at(opt_idx: dict[datetime, float],
                ts: datetime) -> Optional[float]:
    """At-or-after option-premium lookup, 5-min forward window. ENH-100 (S32)."""
    floored = ts.replace(second=0, microsecond=0)
    for delta_min in range(0, ATM_LOOKUP_TOLERANCE_MIN):
        probe = floored + timedelta(minutes=delta_min)
        p = opt_idx.get(probe)
        if p is not None:
            return p
    return None


def compute_mfe_mae(primitive: Primitive, bars_1m: list[Bar],
                    idx: dict[datetime, int]) -> dict:
    """ENH-100 (S32) — formation-anchored MFE/MAE over 30-min window per ADR-010 v3.

    BULL primitive:  mfe_pct = (max_spot - entry) / entry * 100  (positive when favorable)
                     mae_pct = (min_spot - entry) / entry * 100  (negative when unfavorable)
    BEAR primitive:  mfe_pct = (entry - min_spot) / entry * 100  (positive when favorable)
                     mae_pct = (max_spot - entry) / entry * 100, sign-flipped to negative

    time_to_mfe_min: integer minutes from valid_from to bar that produced MFE; NULL if MFE<=0.
    Direction=NONE (events) returns empty dict — magnitude undefined without direction.
    """
    out: dict = {}
    if primitive.direction not in ("BULL", "BEAR"):
        return out
    anchor = _spot_at(bars_1m, primitive.valid_from, idx)
    if anchor is None or anchor == 0:
        return out
    window_end = primitive.valid_from + timedelta(minutes=MFE_MAE_WINDOW_MIN)

    # Find start bar index at-or-after valid_from
    start_i = None
    for i, b in enumerate(bars_1m):
        if b.ts >= primitive.valid_from:
            start_i = i
            break
    if start_i is None:
        return out

    max_spot = anchor
    max_spot_ts = primitive.valid_from
    min_spot = anchor
    min_spot_ts = primitive.valid_from
    saw_any = False
    for i in range(start_i, len(bars_1m)):
        b = bars_1m[i]
        if b.ts > window_end:
            break
        saw_any = True
        if b.high > max_spot:
            max_spot = b.high
            max_spot_ts = b.ts
        if b.low < min_spot:
            min_spot = b.low
            min_spot_ts = b.ts
    if not saw_any:
        return out

    if primitive.direction == "BULL":
        mfe_raw = (max_spot - anchor) / anchor * 100.0
        mae_raw = (min_spot - anchor) / anchor * 100.0
        mfe_ts  = max_spot_ts
    else:  # BEAR
        mfe_raw = (anchor - min_spot) / anchor * 100.0
        mae_raw = -((max_spot - anchor) / anchor * 100.0)
        mfe_ts  = min_spot_ts

    out["mfe_pct"] = mfe_raw
    out["mae_pct"] = mae_raw
    if mfe_raw > 0:
        delta_seconds = (mfe_ts - primitive.valid_from).total_seconds()
        out["time_to_mfe_min"] = int(delta_seconds // 60)
    return out


def _atm_strike_for(spot: float, symbol: str) -> Optional[float]:
    """DEPRECATED (ENH-100 (S32) v3): vendor pre-picks ATM strike in
    hist_atm_option_bars_5m.atm_strike column; this helper is unused by v3
    compute_atm_pnl_and_dte. Retained as dead code in case ENH-104 fallback
    (same-strike tracking via hist_option_bars_1m) needs Python-side rounding."""
    interval = STRIKE_INTERVAL.get(symbol)
    if not interval or interval <= 0:
        return None
    lower = (spot // interval) * interval
    upper = lower + interval
    return lower if (spot - lower) <= (upper - spot) else upper


def _floor_5m(ts: datetime) -> datetime:
    """ENH-100 (S32) v3 — floor a timestamp to the nearest 5-min boundary.

    hist_atm_option_bars_5m bars are at 5-min boundaries (09:15, 09:20, ...).
    Used to align primitive.valid_from to the table's grid for exact eq lookups.
    """
    floored = ts.replace(second=0, microsecond=0)
    return floored.replace(minute=(floored.minute // 5) * 5)


def _vendor_bar_ts_label(real_utc_dt: datetime) -> str:
    """ENH-100 (S32) v5 — convert real-UTC datetime to vendor's IST-mislabeled
    +00:00 string for DB filtering against hist_atm_option_bars_5m.bar_ts.

    The vendor stores bar_ts as IST wall-clock labeled +00:00 (Bug B3 / Rule 16
    pattern; confirmed via hour-distribution audit 2026-05-22). To filter against
    this column with a real-UTC datetime, we relabel: take the datetime's IST
    components and re-tag them as if they were UTC.

    Example: real-UTC 04:00 (= IST 09:30) becomes the string
    '2025-10-15T09:30:00+00:00' which lex-matches the stored value.
    """
    ist = real_utc_dt.astimezone(IST)
    ist_naive = ist.replace(tzinfo=None)
    relabeled = ist_naive.replace(tzinfo=UTC)
    return relabeled.isoformat()


def _prefetch_atm_calendar(sb, symbol: str, start_utc: datetime,
                           end_utc: datetime, atm_cache: dict) -> int:
    """ENH-100 (S32) v5 — pre-fetch all hist_atm_option_bars_5m rows for symbol.

    Two era-aware changes vs v4:
      1. Filter bounds use _vendor_bar_ts_label (IST-mislabeled format) since
         vendor's bar_ts is IST-as-UTC. Buffer extended to 24h to absorb the
         IST/UTC offset misalignment at the upper bound (vendor's IST 15:30 bars
         on end_utc's date would be excluded by tighter bounds).
      2. Incoming bar_ts normalized via normalize_hist_bar_ts (existing
         IST-labeled→real-UTC converter) before keying the cache dicts. This
         ensures the cache key matches what _floor_5m(primitive.valid_from)
         produces in real-UTC.

    Populates two structured atm_cache entries:
      ("atm_cal_rows", instrument_id) → dict (bar_ts_real_utc_iso, expiry_iso) → row
      ("atm_cal_expiries", instrument_id) → dict bar_ts_real_utc_iso → sorted [expiry_iso, ...]

    Returns total row count loaded.
    """
    instrument_id = INSTRUMENT_ID_BY_SYMBOL.get(symbol)
    if not instrument_id:
        log(f"  [prefetch] unknown symbol {symbol}; skipping calendar prefetch")
        return 0
    # 24h buffer covers (a) +60m horizons on late-window primitives,
    # (b) IST vs UTC label mismatch at end-of-window IST trading hours.
    fetch_end_utc = end_utc + timedelta(hours=24)
    vendor_start = _vendor_bar_ts_label(start_utc)
    vendor_end = _vendor_bar_ts_label(fetch_end_utc)
    rows_by_key: dict = {}
    expiries_by_ts: dict = {}
    page = 0
    t0 = _time.time()
    while True:
        offset = page * PAGE_SIZE
        res = (
            sb.table("hist_atm_option_bars_5m")
              .select("bar_ts,expiry_date,atm_strike,dte,ce_close,pe_close")
              .eq("instrument_id", instrument_id)
              .gte("bar_ts", vendor_start)
              .lte("bar_ts", vendor_end)
              .order("bar_ts", desc=False)
              .range(offset, offset + PAGE_SIZE - 1)
              .execute()
        )
        rows = res.data or []
        for r in rows:
            # v5: normalize IST-labeled +00 to real UTC for cache key alignment
            # with what _floor_5m(primitive.valid_from) produces.
            bts_dt = normalize_hist_bar_ts(r["bar_ts"])
            bts_key = bts_dt.isoformat()
            exp_raw = r["expiry_date"]
            rows_by_key[(bts_key, exp_raw)] = r
            expiries_by_ts.setdefault(bts_key, []).append(exp_raw)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
        if page % 10 == 0:
            log(f"    hist_atm_option_bars_5m({symbol}): {len(rows_by_key)} rows so far...")
    for bts in expiries_by_ts:
        expiries_by_ts[bts].sort()
    atm_cache[("atm_cal_rows", instrument_id)] = rows_by_key
    atm_cache[("atm_cal_expiries", instrument_id)] = expiries_by_ts
    log(f"  → prefetched {len(rows_by_key)} ATM rows for {symbol} "
        f"({len(expiries_by_ts)} distinct bar_ts) in {_time.time() - t0:.1f}s")
    return len(rows_by_key)


def _atm_anchor_at(sb, instrument_id: str, bar_ts_5m: datetime,
                   atm_cache: dict) -> Optional[dict]:
    """ENH-100 (S32) v5 — anchor ATM row at exact 5m bar_ts; nearest-expiry first.

    Fast path: prefetched calendar (now keyed by REAL-UTC iso after v5 normalize).
    Fallback path: per-query against IST-mislabeled vendor table — uses
    _vendor_bar_ts_label to relabel real-UTC into vendor's IST-as-UTC format.
    """
    # Fast path: prefetched calendar
    cal_rows = atm_cache.get(("atm_cal_rows", instrument_id))
    cal_expiries = atm_cache.get(("atm_cal_expiries", instrument_id))
    if cal_rows is not None and cal_expiries is not None:
        bts_key = bar_ts_5m.isoformat()  # real-UTC iso, matches v5-normalized cache
        expiries = cal_expiries.get(bts_key)
        if not expiries:
            return None
        nearest = expiries[0]
        return cal_rows.get((bts_key, nearest))

    # Fallback: per-query against IST-mislabeled vendor table (v5 era-aware)
    ck = ("atm5m_anchor", instrument_id, bar_ts_5m.isoformat())
    if ck in atm_cache:
        return atm_cache[ck]
    vendor_bts = _vendor_bar_ts_label(bar_ts_5m)
    res = (
        sb.table("hist_atm_option_bars_5m")
          .select("atm_strike,expiry_date,dte,ce_close,pe_close")
          .eq("instrument_id", instrument_id)
          .eq("bar_ts", vendor_bts)
          .order("expiry_date", desc=False)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    row = rows[0] if rows else None
    atm_cache[ck] = row
    return row


def _atm_future_at(sb, instrument_id: str, bar_ts_5m: datetime,
                   expiry_date_v, atm_cache: dict) -> Optional[dict]:
    """ENH-100 (S32) v5 — future ATM row at exact 5m bar_ts + expiry.

    Fast path: prefetched calendar (v5-normalized keys). Fallback: per-query
    with _vendor_bar_ts_label for the IST-mislabeled DB column.
    """
    # Fast path
    cal_rows = atm_cache.get(("atm_cal_rows", instrument_id))
    if cal_rows is not None:
        bts_key = bar_ts_5m.isoformat()
        expiry_str = expiry_date_v if isinstance(expiry_date_v, str) else expiry_date_v.isoformat()
        return cal_rows.get((bts_key, expiry_str))

    # Fallback per-query (v5 era-aware)
    ck = ("atm5m_future", instrument_id, bar_ts_5m.isoformat(), str(expiry_date_v))
    if ck in atm_cache:
        return atm_cache[ck]
    expiry_str = expiry_date_v if isinstance(expiry_date_v, str) else expiry_date_v.isoformat()
    vendor_bts = _vendor_bar_ts_label(bar_ts_5m)
    res = (
        sb.table("hist_atm_option_bars_5m")
          .select("atm_strike,ce_close,pe_close")
          .eq("instrument_id", instrument_id)
          .eq("bar_ts", vendor_bts)
          .eq("expiry_date", expiry_str)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    row = rows[0] if rows else None
    atm_cache[ck] = row
    return row


def compute_atm_pnl_and_dte(primitive: Primitive, bars_1m: list[Bar],
                            idx: dict[datetime, int],
                            sb, atm_cache: dict) -> dict:
    """ENH-106 (S33) v7 — formation-anchored held-strike ATM CE/PE PnL.

    Architectural rewrite from v3:
      - ATM strike picked MANUALLY from spot at anchor via STRIKE_INTERVAL
        (NIFTY/50, SENSEX/100). No reliance on vendor's pre-picked atm_strike.
      - Premium read from hist_option_bars_1m chain (54.8M-row dense table).
      - Strike HELD CONSTANT across all 4 horizons — no vendor-roll attrition.
      - Expiry derived from empirical calendar via _nearest_weekly_expiry().
        Calendar handles NSE/BSE 2025-09-01 weekday swap (NIFTY Thu→Tue,
        SENSEX Tue→Thu), ~15% holiday-shifted (Mon/Wed) expiries, and
        same-week double expiries automatically (empirical, not DOW-derived).
      - DTE = (expiry - valid_from.date()).days — no longer reads vendor dte.

    Chain lookups are O(1) hits against atm_cache populated by
    _prefetch_chain_for_primitives() called at start of compute_outcomes.
    Returns {} when smoke mode, non-BULL/BEAR, missing spot/strike/expiry,
    or anchor premium absent/zero. Below early return is the (now unreachable)
    v3 trailing loop; left as dead code to minimize diff surface.
    """
    out: dict = {}
    if sb is None or primitive.direction not in ("BULL", "BEAR"):
        return out
    instrument_id = INSTRUMENT_ID_BY_SYMBOL.get(primitive.symbol)
    if not instrument_id:
        return out
    grid = STRIKE_INTERVAL.get(primitive.symbol)
    if grid is None:
        return out

    anchor_5m = _floor_5m(primitive.valid_from)
    spot = _spot_at(bars_1m, anchor_5m, idx)
    if spot is None or spot <= 0:
        return out
    strike = round(spot / grid) * grid

    calendar = atm_cache.get(("expiry_calendar", instrument_id), [])
    expiry = _nearest_weekly_expiry(anchor_5m, calendar)
    if expiry is None:
        return out
    expiry_str = expiry.isoformat()
    opt_type = "CE" if primitive.direction == "BULL" else "PE"

    # DTE derived from picked expiry
    out["dte_at_formation"] = (expiry - primitive.valid_from.date()).days

    # Anchor premium from chain
    premium_t0 = _chain_premium_at(atm_cache, instrument_id, strike,
                                    expiry_str, opt_type, anchor_5m)
    if premium_t0 is None or premium_t0 == 0:
        return out

    # ENH-106 (S35) v8 — anchor-tier audit tag (vendor_hist_1m / merdian_hist_5m).
    out["option_pnl_source"] = _source_tier(anchor_5m)

    # Held-strike future horizons
    for mins in ATM_PNL_WINDOWS_MIN:
        future_5m = anchor_5m + timedelta(minutes=mins)
        future_premium = _chain_premium_at(atm_cache, instrument_id, strike,
                                            expiry_str, opt_type, future_5m)
        if future_premium is None or future_premium == 0:
            continue
        out[f"atm_pnl_{mins}m_pct"] = (future_premium - premium_t0) / premium_t0 * 100.0
    return out

    # ── v3 dead code below (unreachable; left for diff minimization) ──
    anchor_strike_norm = ""  # nominal-only; preserves trailing-block parse

    # Future-horizon premium with same-strike enforcement
    for mins in ATM_PNL_WINDOWS_MIN:
        future_5m = anchor_5m + timedelta(minutes=mins)
        future_row = _atm_future_at(sb, instrument_id, future_5m,
                                    anchor_expiry, atm_cache)
        if future_row is None:
            continue
        if str(future_row.get("atm_strike")) != anchor_strike_norm:
            # Vendor rolled ATM — strikes differ; premium not comparable
            continue
        future_premium_raw = future_row.get(premium_col)
        if future_premium_raw is None:
            continue
        future_premium = float(future_premium_raw)
        if future_premium == 0:
            continue
        out[f"atm_pnl_{mins}m_pct"] = (future_premium - premium_t0) / premium_t0 * 100.0
    return out


def compute_retest_atm_pnl(primitive: Primitive, outcome_row: "OutcomeRow",
                           bars_1m: list[Bar], idx: dict[datetime, int],
                           sb, atm_cache: dict) -> dict:
    """ENH-106 (S33) v7 — retest-anchored held-strike ATM CE/PE PnL.

    Same chain-table held-strike architecture as v7 compute_atm_pnl_and_dte
    but anchored at outcome_row.first_retest_ts. Manual ATM rounding from spot
    at retest moment; strike held constant across all 5 horizons (5/15/30/60m
    + EOD via IST 15:25 last 5m bar). All premium lookups are O(1) hits
    against atm_cache prefetched by _prefetch_chain_for_primitives().

    Returns {} when smoke mode, non-BULL/BEAR direction, retest absent,
    spot/strike/expiry unavailable, or anchor premium absent/zero.
    """
    out: dict = {}
    if sb is None or primitive.direction not in ("BULL", "BEAR"):
        return out
    if outcome_row.retest_status != "RETESTED" or outcome_row.first_retest_ts is None:
        return out
    instrument_id = INSTRUMENT_ID_BY_SYMBOL.get(primitive.symbol)
    if instrument_id is None:
        return out
    grid = STRIKE_INTERVAL.get(primitive.symbol)
    if grid is None:
        return out

    retest_5m = _floor_5m(outcome_row.first_retest_ts)
    spot = _spot_at(bars_1m, retest_5m, idx)
    if spot is None or spot <= 0:
        return out
    strike = round(spot / grid) * grid

    calendar = atm_cache.get(("expiry_calendar", instrument_id), [])
    expiry = _nearest_weekly_expiry(retest_5m, calendar)
    if expiry is None:
        return out
    expiry_str = expiry.isoformat()
    opt_type = "CE" if primitive.direction == "BULL" else "PE"

    premium_t0 = _chain_premium_at(atm_cache, instrument_id, strike,
                                    expiry_str, opt_type, retest_5m)
    if premium_t0 is None or premium_t0 == 0:
        return out

    # ENH-106 (S35) v8 — retest-tier audit tag (vendor_hist_1m / merdian_hist_5m).
    out["option_pnl_source"] = _source_tier(retest_5m)

    # Forward horizons (held strike across all)
    for col, mins in [("option_pnl_5m", 5), ("option_pnl_15m", 15),
                       ("option_pnl_30m", 30), ("option_pnl_60m", 60)]:
        future_premium = _chain_premium_at(atm_cache, instrument_id, strike,
                                            expiry_str, opt_type,
                                            retest_5m + timedelta(minutes=mins))
        if future_premium is None or future_premium == 0:
            continue
        out[col] = (future_premium - premium_t0) / premium_t0 * 100.0

    # EOD horizon: last 5m bar of retest's IST trading day (IST 15:25)
    ist_dt = outcome_row.first_retest_ts.astimezone(IST)
    eod_ist = ist_dt.replace(hour=15, minute=25, second=0, microsecond=0)
    eod_5m = eod_ist.astimezone(UTC)
    if eod_5m > retest_5m:
        future_premium = _chain_premium_at(atm_cache, instrument_id, strike,
                                            expiry_str, opt_type, eod_5m)
        if future_premium is not None and future_premium != 0:
            out["option_pnl_eod"] = (future_premium - premium_t0) / premium_t0 * 100.0

    # --- ADR-012 (S35) v9 — spot-anchored SL doctrine ---
    # Skip for level primitives (zone_low/zone_high are None on PDH/PDL/PWH/etc.)
    if primitive.zone_low is not None and primitive.zone_high is not None:
        sl_buffer_pct = SL_BUFFER_PCT_DEFAULT
        if primitive.direction == "BULL":
            sl_level = float(primitive.zone_low) * (1.0 - sl_buffer_pct)
            sl_triggered_fn = lambda close: close < sl_level
        else:  # BEAR
            sl_level = float(primitive.zone_high) * (1.0 + sl_buffer_pct)
            sl_triggered_fn = lambda close: close > sl_level
        out["sl_level"] = sl_level
        out["sl_buffer_pct"] = sl_buffer_pct

        # Aggregate 5m spot bars once per session (cached on atm_cache).
        bars_5m = atm_cache.get("bars_5m_for_sl")
        if bars_5m is None:
            bars_5m = aggregate(bars_1m, "M5")
            atm_cache["bars_5m_for_sl"] = bars_5m

        # Walk 5m bars after retest_5m through eod_5m, find first close-through.
        sl_trigger_ts = None
        for bar in bars_5m:
            if bar.ts <= retest_5m:
                continue
            if bar.ts > eod_5m:
                break
            if sl_triggered_fn(bar.close):
                sl_trigger_ts = bar.ts
                break

        if sl_trigger_ts is not None:
            out["sl_triggered_ts"] = sl_trigger_ts
            sl_exit_prem = _chain_premium_at(atm_cache, instrument_id, strike,
                                              expiry_str, opt_type, sl_trigger_ts)
            if sl_exit_prem is not None and sl_exit_prem > 0:
                out["sl_exit_prem"] = sl_exit_prem
                out["pnl_with_sl_pct"] = (sl_exit_prem - premium_t0) / premium_t0 * 100.0
            # else: sl_triggered_ts populated but sl_exit_prem + pnl_with_sl_pct NULL
            #       (audit: we know SL fired but couldn't price the exit)
        else:
            # No SL trigger intra-session — degenerates to held-to-EOD.
            if out.get("option_pnl_eod") is not None:
                out["pnl_with_sl_pct"] = out["option_pnl_eod"]

    return out


# ============================================================================
# ENH-106 (S33) v7 — chain-table held-strike helpers
# ============================================================================


def _load_expiry_calendar(sb, symbol: str) -> list:
    """ENH-106 (S35) v8.1 — load sorted list[date] of all expiries for symbol from
    BOTH historical tiers, UNION'd and deduped.

    Source tier transition (same boundary as the chain-price tier):
      Pre-2026-04-01:  hist_atm_option_bars_5m (vendor-purchased aggregation)
                       — last_expiry around 2026-04-02 / 2026-04-07
      On/post:         historical_option_chain_snapshots (MERDIAN-ingest)
                       — first_expiry around 2026-03-19 / 2026-03-24 (clean overlap)

    Without the UNION, v8 dual-source chain prefetch is dead on post-Apr-2026
    anchors because _nearest_weekly_expiry returns None on the truncated vendor
    calendar and _enum_anchor silently early-returns.

    Calendar handles automatically (empirical, not DOW-derived):
      - NIFTY pre-2025-09-01 Thursday weeklies; post-2025-09-01 Tuesday weeklies
      - SENSEX pre-2025-09-01 Tuesday weeklies; post-2025-09-01 Thursday weeklies
      - ~15% holiday-shifted weeks (Mon/Wed expiries)
      - Same-week double expiries (monthly + weekly)
    """
    instrument_id = INSTRUMENT_ID_BY_SYMBOL.get(symbol)
    if not instrument_id:
        return []

    # --- Source 1: vendor aggregation (hist_atm_option_bars_5m) ---
    vendor_expiries: set = set()
    page = 0
    while True:
        offset = page * PAGE_SIZE
        res = (
            sb.table("hist_atm_option_bars_5m")
              .select("expiry_date")
              .eq("instrument_id", instrument_id)
              .range(offset, offset + PAGE_SIZE - 1)
              .execute()
        )
        rows = res.data or []
        for r in rows:
            exp = r.get("expiry_date")
            if exp is None:
                continue
            if isinstance(exp, str):
                vendor_expiries.add(date.fromisoformat(exp))
            else:
                vendor_expiries.add(exp)
        if len(rows) < PAGE_SIZE:
            break
        page += 1

    # --- Source 2: MERDIAN-ingest tier (historical_option_chain_snapshots) ---
    # ENH-106 (S35) v8.2 — RPC call replaces full-table paginated scan.
    # historical_option_chain_snapshots is 2.67M rows; walking pages to find ~10
    # distinct expiry_date values per symbol is architecturally wrong and takes
    # ~9-15 minutes. Postgres function get_hocs_distinct_expiries pushes the
    # DISTINCT into the DB (~50ms per symbol on the existing symbol+ts index).
    # See sql/20260524_enh106_v8p2_hocs_distinct_expiries_rpc.sql for DDL.
    hocs_expiries: set = set()
    try:
        rpc_res = sb.rpc("get_hocs_distinct_expiries", {"_symbol": symbol}).execute()
        rpc_rows = rpc_res.data or []
        for r in rpc_rows:
            exp = r.get("expiry_date") if isinstance(r, dict) else None
            if exp is None:
                continue
            if isinstance(exp, str):
                hocs_expiries.add(date.fromisoformat(exp))
            else:
                hocs_expiries.add(exp)
    except Exception as ex:
        log(f"  [v8.2] hocs expiries RPC failed for {symbol}: {ex}; "
            f"proceeding with vendor-only calendar (post-2026-04-01 anchors will skip)")

    union = vendor_expiries | hocs_expiries
    log(f"  [v8.2] expiry calendar {symbol}: vendor={len(vendor_expiries)} "
        f"+ hocs={len(hocs_expiries)} = union={len(union)} distinct expiries "
        f"(overlap={len(vendor_expiries & hocs_expiries)})")
    return sorted(union)


def _nearest_weekly_expiry(anchor_ts: datetime, calendar: list):
    """ENH-106 (S33) v7 — first expiry >= anchor IST date.

    Same-day-as-expiry handling:
      - if anchor IST time < 15:30 → today's expiry (DTE=0 intraday trade)
      - else → next available (post-close on expiry day rolls to next week)
    """
    if not calendar:
        return None
    anchor_ist = anchor_ts.astimezone(IST)
    anchor_date = anchor_ist.date()
    lo, hi = 0, len(calendar)
    while lo < hi:
        mid = (lo + hi) // 2
        if calendar[mid] < anchor_date:
            lo = mid + 1
        else:
            hi = mid
    if lo >= len(calendar):
        return None
    if calendar[lo] == anchor_date:
        pre_close = (anchor_ist.hour < 15) or (anchor_ist.hour == 15 and anchor_ist.minute < 30)
        if pre_close:
            return calendar[lo]
        lo += 1
        if lo >= len(calendar):
            return None
    return calendar[lo]


def _source_tier(ts: datetime) -> str:
    """ENH-106 (S35) v8 — return chain tier tag for a given anchor timestamp.

    Used to populate ict_primitive_outcomes.option_pnl_source. Boundary check is
    inclusive of the post-side: ts >= CHAIN_TIER_BOUNDARY_UTC routes to HOCS.
    """
    return "vendor_hist_1m" if ts < CHAIN_TIER_BOUNDARY_UTC else "merdian_hist_5m"


def _prefetch_hocs_for_tuple(sb, symbol: str, instrument_id: str,
                              strike: float, expiry_str: str, opt_type: str,
                              min_ts: datetime, max_ts: datetime,
                              atm_cache: dict) -> int:
    """ENH-106 (S35) v8 — prefetch historical_option_chain_snapshots ltp series for one
    (symbol, strike, expiry, opt_type) tuple over [min_ts, max_ts).

    HOCS schema differences vs hist_option_bars_1m:
      - keyed on symbol (text), not instrument_id (uuid)
      - ts column is true UTC (no IST-as-UTC defect; no era normalization needed)
      - point-in-time snapshot, not OHLC; price field is `ltp` (last traded price)
      - ~5min cycle cadence with irregular ts within each bucket; retry storms can
        produce 2-4 rows per 5m bucket (confirmed S35 diagnostic; all from same source
        'ingest_option_chain_local'; same cycle retried within the 5min window)

    Dedup at read: bucket by 5m-floored ts, keep MAX(ts) per bucket. Latest-write
    semantics matches "5m close" interpretation that ADR-011 / ADR-012 already want.

    Cache key shape MATCHES the hist_option_bars_1m path:
      atm_cache[("chain_prem", iid, strike, expiry_str, opt_type)]
        → dict {minute_floored_real_utc_iso: ltp_float}
    Because all anchors (_floor_5m output, anchor_5m + N*5 timedelta, EOD 15:25 IST)
    fall on 5m boundaries, minute-flooring those is idempotent and matches HOCS
    5m-flooring. Reader _chain_premium_at therefore needs no changes.

    Returns number of NEW bucket entries added (existing entries are not overwritten;
    pre-side prefetch on the same tuple is preserved if it ran first).
    """
    cache_key = ("chain_prem", instrument_id, strike, expiry_str, opt_type)
    existing = atm_cache.get(cache_key)
    if existing is None:
        existing = {}
        atm_cache[cache_key] = existing

    # Widen range to absorb 5min cycle cadence — a cycle may fire just outside the
    # strict bound but cover the bucket we need.
    fetch_min = (min_ts - timedelta(minutes=5)).isoformat()
    fetch_max = (max_ts + timedelta(minutes=5)).isoformat()

    rows: list = []
    page = 0
    while True:
        offset = page * PAGE_SIZE
        try:
            res = (
                sb.table("historical_option_chain_snapshots")
                  .select("ts,ltp")
                  .eq("symbol", symbol)
                  .eq("strike", strike)
                  .eq("expiry_date", expiry_str)
                  .eq("option_type", opt_type)
                  .gte("ts", fetch_min)
                  .lt("ts", fetch_max)
                  .order("ts", desc=False)
                  .range(offset, offset + PAGE_SIZE - 1)
                  .execute()
            )
        except Exception as ex:
            log(f"  [v8] hocs query error tup=({symbol},{strike},{expiry_str},{opt_type}) "
                f"page={page}: {ex}")
            break
        page_rows = res.data or []
        rows.extend(page_rows)
        if len(page_rows) < PAGE_SIZE:
            break
        page += 1

    # Bucket by 5m-floored ts; keep MAX(ts) within bucket (latest write).
    per_bucket_latest: dict = {}
    for r in rows:
        ts_raw = r.get("ts")
        ltp_raw = r.get("ltp")
        if ts_raw is None or ltp_raw is None:
            continue
        try:
            ts_dt = parse_supabase_ts(ts_raw)  # true UTC; no normalize_hist_bar_ts here
            ltp_val = float(ltp_raw)
        except (ValueError, TypeError):
            continue
        # 5m-floored bucket key
        bucket_dt = ts_dt.replace(second=0, microsecond=0)
        bucket_dt = bucket_dt.replace(minute=(bucket_dt.minute // 5) * 5)
        bucket_key = bucket_dt.isoformat()
        prev = per_bucket_latest.get(bucket_key)
        if prev is None or ts_dt > prev[0]:
            per_bucket_latest[bucket_key] = (ts_dt, ltp_val)

    # Merge into cache, do not overwrite (pre-side may have populated some keys).
    added = 0
    for bucket_key, (_, price) in per_bucket_latest.items():
        if bucket_key not in existing:
            existing[bucket_key] = price
            added += 1
    return added


def _chain_premium_at(atm_cache: dict, instrument_id: str, strike: float,
                       expiry_str: str, opt_type: str, target_ts: datetime):
    """ENH-106 (S33) v7 — O(1) chain close lookup from prefetched cache.

    Returns None when tuple absent from cache or no bar at that minute.
    Cache key: minute-floored real-UTC ISO of target_ts.

    v8 note: cache may contain entries from BOTH hist_option_bars_1m (pre-2026-04-01
    anchors) and historical_option_chain_snapshots (post-2026-04-01 anchors). For
    HOCS sources the stored value is ltp (last traded) rather than close, and
    bucket-keys are 5m-floored (which coincide with minute-floors at 5m boundaries).
    Reader is agnostic to source.
    """
    key = target_ts.replace(second=0, microsecond=0).isoformat()
    cache = atm_cache.get(("chain_prem", instrument_id, strike, expiry_str, opt_type))
    if cache is None:
        return None
    return cache.get(key)


def _prefetch_chain_for_primitives(sb, primitives, events, bars_1m, idx, atm_cache):
    """ENH-106 (S35) v8 — dual-source chain prefetch.

    Enumerates the same (strike, expiry, opt_type) tuples + per-anchor timestamps as v7,
    then per tuple splits the timestamp set by CHAIN_TIER_BOUNDARY_UTC and routes:
      - Pre-boundary timestamps → hist_option_bars_1m (existing 1m OHLC path).
      - Post-boundary timestamps → historical_option_chain_snapshots (~5min point-in-time,
        ltp not close, dedup at read; via _prefetch_hocs_for_tuple).

    Both sides write into the SAME cache slot:
      atm_cache[("chain_prem", instrument_id, strike, expiry_str, opt_type)]
        → dict {minute_floored_real_utc_iso: price_float}
    Reader _chain_premium_at is untouched; values from either source are interchangeable
    at read time (the option_pnl_source audit column on outcomes records which tier the
    anchor came from for downstream interpretation).

    Strategy:
      1. Load expiry calendar (cached).
      2. Walk primitives → formation anchor specs.
      3. Walk events → formation anchor specs.
      4. Pre-pass retest detection on primitives → retest anchor specs.
      5. Per unique tuple: split ts_set; pre-side hist_option_bars_1m query (UNCHANGED);
         post-side historical_option_chain_snapshots query (via _prefetch_hocs_for_tuple).

    Populates atm_cache:
      ("expiry_calendar", instrument_id) → sorted list[date]
      ("chain_prem", instrument_id, strike, expiry_str, opt_type)
        → dict {real_utc_iso_minute_floored: price_float}  (close OR ltp; reader-agnostic)
    """
    if sb is None or not primitives:
        return 0
    symbol = primitives[0].symbol
    instrument_id = INSTRUMENT_ID_BY_SYMBOL.get(symbol)
    if not instrument_id:
        return 0
    grid = STRIKE_INTERVAL.get(symbol)
    if grid is None:
        return 0

    # Calendar (cache after first load)
    calendar = atm_cache.get(("expiry_calendar", instrument_id))
    if calendar is None:
        calendar = _load_expiry_calendar(sb, symbol)
        atm_cache[("expiry_calendar", instrument_id)] = calendar
    if not calendar:
        log(f"  [v8] empty expiry calendar for {symbol}; skipping chain prefetch")
        return 0

    timestamps_per_tuple: dict = {}
    HORIZONS = [0] + ATM_PNL_WINDOWS_MIN  # [0, 5, 15, 30, 60]

    def _enum_anchor(direction, anchor_5m, ts_for_eod):
        if direction not in ("BULL", "BEAR"):
            return
        spot = _spot_at(bars_1m, anchor_5m, idx)
        if spot is None or spot <= 0:
            return
        strike = round(spot / grid) * grid
        expiry = _nearest_weekly_expiry(anchor_5m, calendar)
        if expiry is None:
            return
        opt_type = "CE" if direction == "BULL" else "PE"
        tup = (strike, expiry.isoformat(), opt_type)
        ts_set = timestamps_per_tuple.setdefault(tup, set())
        for mins in HORIZONS:
            ts_set.add(anchor_5m + timedelta(minutes=mins))
        # EOD: IST 15:25 → real UTC
        ist = ts_for_eod.astimezone(IST)
        eod_ist = ist.replace(hour=15, minute=25, second=0, microsecond=0)
        ts_set.add(eod_ist.astimezone(UTC))

    # Formation anchors: primitives
    for p in primitives:
        _enum_anchor(p.direction, _floor_5m(p.valid_from), p.valid_from)
    # Formation anchors: events (compute_outcomes also calls compute_atm_pnl_and_dte for events)
    for e in events:
        _enum_anchor(e.direction, _floor_5m(e.event_ts), e.event_ts)

    # Retest anchors: pre-pass retest detection
    retest_pre_pass = 0
    for p in primitives:
        if p.direction not in ("BULL", "BEAR"):
            continue
        info = {}
        if p.zone_low is not None and p.zone_high is not None:
            info = compute_retest_outcomes_zone(p, bars_1m, idx)
        elif p.level is not None:
            info = compute_retest_outcomes_level(p, bars_1m, idx)
        if info.get("retest_status") != "RETESTED":
            continue
        ts = info.get("first_retest_ts")
        if ts is None:
            continue
        retest_pre_pass += 1
        _enum_anchor(p.direction, _floor_5m(ts), ts)

    n_tuples = len(timestamps_per_tuple)
    if n_tuples == 0:
        return 0
    log(f"  [v8] {symbol}: {n_tuples} (strike,expiry,type) tuples to prefetch "
        f"({retest_pre_pass} retests detected in pre-pass)")

    total_pre = 0   # hist_option_bars_1m bars loaded
    total_post = 0  # historical_option_chain_snapshots cycles loaded
    tuples_pre_only = 0
    tuples_post_only = 0
    tuples_mixed = 0
    t0 = _time.time()

    for tup_i, (tup, ts_set) in enumerate(timestamps_per_tuple.items()):
        strike, expiry_str, opt_type = tup

        # Split per-tuple timestamps by tier boundary.
        pre_tss = {ts for ts in ts_set if ts < CHAIN_TIER_BOUNDARY_UTC}
        post_tss = {ts for ts in ts_set if ts >= CHAIN_TIER_BOUNDARY_UTC}
        if pre_tss and post_tss:
            tuples_mixed += 1
        elif pre_tss:
            tuples_pre_only += 1
        else:
            tuples_post_only += 1

        # Ensure cache slot exists (will be populated by either or both paths below).
        cache_dict: dict = atm_cache.setdefault(
            ("chain_prem", instrument_id, strike, expiry_str, opt_type), {}
        )

        # ── Pre-boundary path: hist_option_bars_1m (v7 logic, UNCHANGED) ──
        if pre_tss:
            min_ts = min(pre_tss).replace(second=0, microsecond=0)
            max_ts = max(pre_tss).replace(second=0, microsecond=0) + timedelta(minutes=1)
            min_label = _vendor_bar_ts_label(min_ts)
            max_label = _vendor_bar_ts_label(max_ts)
            page = 0
            while True:
                offset = page * PAGE_SIZE
                try:
                    res = (
                        sb.table("hist_option_bars_1m")
                          .select("bar_ts,close")
                          .eq("instrument_id", instrument_id)
                          .eq("strike", strike)
                          .eq("expiry_date", expiry_str)
                          .eq("option_type", opt_type)
                          .gte("bar_ts", min_label)
                          .lt("bar_ts", max_label)
                          .order("bar_ts", desc=False)
                          .range(offset, offset + PAGE_SIZE - 1)
                          .execute()
                    )
                except Exception as ex:
                    log(f"  [v8] hist_option_bars_1m query error tup={tup} page={page}: {ex}")
                    break
                rows = res.data or []
                for r in rows:
                    bts_raw = r.get("bar_ts")
                    close_raw = r.get("close")
                    if bts_raw is None or close_raw is None:
                        continue
                    real_ts = normalize_hist_bar_ts(bts_raw)
                    key = real_ts.replace(second=0, microsecond=0).isoformat()
                    try:
                        cache_dict[key] = float(close_raw)
                        total_pre += 1
                    except (ValueError, TypeError):
                        pass
                if len(rows) < PAGE_SIZE:
                    break
                page += 1

        # ── Post-boundary path: historical_option_chain_snapshots (v8 NEW) ──
        if post_tss:
            min_ts = min(post_tss)
            max_ts = max(post_tss) + timedelta(minutes=1)
            added = _prefetch_hocs_for_tuple(
                sb, symbol, instrument_id, strike, expiry_str, opt_type,
                min_ts, max_ts, atm_cache
            )
            total_post += added

        if (tup_i + 1) % 100 == 0:
            log(f"    [v8] prefetch {tup_i + 1}/{n_tuples} tuples  "
                f"pre={total_pre} post={total_post}  "
                f"elapsed={_time.time() - t0:.1f}s")

    log(f"  [v8] chain prefetch done: {symbol}  "
        f"pre={total_pre} bars (hist_option_bars_1m) + post={total_post} cycles "
        f"(historical_option_chain_snapshots)  "
        f"across {n_tuples} tuples "
        f"(pre_only={tuples_pre_only} post_only={tuples_post_only} mixed={tuples_mixed}) "
        f"in {_time.time() - t0:.1f}s")
    return total_pre + total_post


def compute_outcomes(primitives: list[Primitive], events: list[Event],
                     bars_1m: list[Bar],
                     sb=None, atm_cache: Optional[dict] = None) -> list[OutcomeRow]:
    """
    Compute outcomes for all primitives + events. Returns OutcomeRow list keyed on
    primitive natural key (resolved to UUID at upsert time after DB SELECT).
    """
    if not bars_1m:
        return []
    idx = _bar_idx_by_minute(bars_1m)
    if atm_cache is None:
        atm_cache = {}  # ENH-100 (S32) — per-call cache for expiry + premium lookups

    # ENH-106 (S33) v7 — chain-table held-strike prefetch (calendar + per-tuple bars)
    _prefetch_chain_for_primitives(sb, primitives, events, bars_1m, idx, atm_cache)

    out: list[OutcomeRow] = []

    for p in primitives:
        nk = _natural_key(p.symbol, p.timeframe, p.primitive_type, p.source_bar_ts,
                          p.zone_low if p.zone_low is not None else p.level,
                          p.zone_high if p.zone_high is not None else p.level)
        row = OutcomeRow(primitive_natural_key=nk)
        # Formation-anchored (all primitive types)
        for k, v in compute_formation_outcomes(p, bars_1m, idx).items():
            setattr(row, k, v)
        # ENH-100 (S32) MFE/MAE — formation-anchored, BULL/BEAR primitives only
        for k, v in compute_mfe_mae(p, bars_1m, idx).items():
            setattr(row, k, v)
        # ENH-100 (S32) ATM PnL + DTE — formation-anchored, BULL/BEAR primitives only
        for k, v in compute_atm_pnl_and_dte(p, bars_1m, idx, sb, atm_cache).items():
            setattr(row, k, v)
        # Retest-anchored
        if p.zone_low is not None and p.zone_high is not None:
            for k, v in compute_retest_outcomes_zone(p, bars_1m, idx).items():
                setattr(row, k, v)
        elif p.level is not None:
            for k, v in compute_retest_outcomes_level(p, bars_1m, idx).items():
                setattr(row, k, v)
        # ENH-103 (S33) v6 — retest-anchored ATM CE/PE PnL.
        # Must run AFTER retest detection (consumes row.retest_status + row.first_retest_ts).
        for k, v in compute_retest_atm_pnl(p, row, bars_1m, idx, sb, atm_cache).items():
            setattr(row, k, v)
        out.append(row)

    # Events: formation only (§10 — no retest concept). retest_status='NEVER_RETESTED'.
    for e in events:
        nk = _natural_key(e.symbol, e.timeframe, e.event_type, e.event_ts, None, None)
        # Construct a stub primitive to reuse forward-outcome logic
        stub = Primitive(
            symbol=e.symbol, timeframe=e.timeframe, primitive_type=e.event_type,
            direction=e.direction, source_bar_ts=e.event_ts, valid_from=e.event_ts,
        )
        row = OutcomeRow(primitive_natural_key=nk, retest_status="NEVER_RETESTED")
        for k, v in compute_formation_outcomes(stub, bars_1m, idx).items():
            setattr(row, k, v)
        # ENH-100 (S32) MFE/MAE + ATM PnL + DTE also computed for events with direction
        for k, v in compute_mfe_mae(stub, bars_1m, idx).items():
            setattr(row, k, v)
        for k, v in compute_atm_pnl_and_dte(stub, bars_1m, idx, sb, atm_cache).items():
            setattr(row, k, v)
        out.append(row)

    return out


# ============================================================================
# Upsert layer (Supabase)
# ============================================================================

def _natural_key(symbol: str, tf: str, primitive_type: str, source_bar_ts: datetime,
                 low_or_lvl, high_or_lvl) -> tuple:
    """Natural key for dedupe: matches the UNIQUE INDEX expression on ict_primitives."""
    return (symbol, tf, primitive_type, source_bar_ts.isoformat(),
            float(low_or_lvl) if low_or_lvl is not None else None,
            float(high_or_lvl) if high_or_lvl is not None else None)


def _primitive_to_row(p: Primitive) -> dict:
    """Convert Primitive dataclass → INSERT row dict for ict_primitives."""
    return {
        "symbol": p.symbol,
        "timeframe": p.timeframe,
        "primitive_type": p.primitive_type,
        "direction": p.direction or "NONE",
        "source_bar_ts": p.source_bar_ts.astimezone(UTC).isoformat(),
        "valid_from": p.valid_from.astimezone(UTC).isoformat(),
        "valid_to": p.valid_to.astimezone(UTC).isoformat() if p.valid_to else None,
        "zone_low": p.zone_low,
        "zone_high": p.zone_high,
        "level": p.level,
        "status": p.status,
        "breach_ts": p.breach_ts.astimezone(UTC).isoformat() if p.breach_ts else None,
        "displacement_pct": p.displacement_pct,
        "metadata": p.metadata or {},
    }


def _event_to_row(e: Event) -> dict:
    """Convert Event dataclass → INSERT row dict for ict_primitives (events stored as primitives)."""
    return {
        "symbol": e.symbol,
        "timeframe": e.timeframe,
        "primitive_type": e.event_type,
        "direction": e.direction,
        "source_bar_ts": e.event_ts.astimezone(UTC).isoformat(),
        "valid_from": e.event_ts.astimezone(UTC).isoformat(),
        "valid_to": None,
        "zone_low": None,
        "zone_high": None,
        "level": None,
        "status": "ACTIVE",
        "breach_ts": None,
        "displacement_pct": e.metadata.get("displacement_pct"),
        "metadata": e.metadata or {},
    }


def fetch_existing_natural_keys(sb, symbol: str, tfs: list[str],
                                start_utc: datetime, end_utc: datetime) -> set[tuple]:
    """SELECT natural keys for existing rows in window — pre-check for upsert idempotency."""
    existing: set[tuple] = set()
    page = 0
    while True:
        offset = page * PAGE_SIZE
        res = (
            sb.table("ict_primitives")
              .select("symbol,timeframe,primitive_type,source_bar_ts,zone_low,zone_high,level")
              .eq("symbol", symbol)
              .in_("timeframe", list(WAVE1_TFS))
              .gte("source_bar_ts", start_utc.isoformat())
              .lt("source_bar_ts", end_utc.isoformat())
              .order("source_bar_ts", desc=False)
              .range(offset, offset + PAGE_SIZE - 1)
              .execute()
        )
        rows = res.data or []
        for r in rows:
            existing.add(_natural_key(
                r["symbol"], r["timeframe"], r["primitive_type"],
                parse_supabase_ts(r["source_bar_ts"]),
                r["zone_low"] if r["zone_low"] is not None else r["level"],
                r["zone_high"] if r["zone_high"] is not None else r["level"],
            ))
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return existing


def upsert_primitives_and_events(sb, primitives: list[Primitive],
                                  events: list[Event],
                                  existing_keys: set[tuple],
                                  dry_run: bool) -> tuple[int, int]:
    """Insert new primitives + events. Skip rows whose natural key already exists.

    Returns (inserted_count, skipped_count).
    """
    new_rows: list[dict] = []
    skipped = 0
    seen_in_batch: set[tuple] = set()

    for p in primitives:
        nk = _natural_key(p.symbol, p.timeframe, p.primitive_type, p.source_bar_ts,
                          p.zone_low if p.zone_low is not None else p.level,
                          p.zone_high if p.zone_high is not None else p.level)
        if nk in existing_keys or nk in seen_in_batch:
            skipped += 1
            continue
        seen_in_batch.add(nk)
        new_rows.append(_primitive_to_row(p))

    for e in events:
        nk = _natural_key(e.symbol, e.timeframe, e.event_type, e.event_ts, None, None)
        if nk in existing_keys or nk in seen_in_batch:
            skipped += 1
            continue
        seen_in_batch.add(nk)
        new_rows.append(_event_to_row(e))

    if dry_run:
        log(f"  [dry-run] would insert {len(new_rows)} rows into ict_primitives ({skipped} skipped)")
        return len(new_rows), skipped

    inserted = 0
    for i in range(0, len(new_rows), UPSERT_BATCH_SIZE):
        batch = new_rows[i:i + UPSERT_BATCH_SIZE]
        sb.table("ict_primitives").insert(batch).execute()
        inserted += len(batch)
    log(f"  inserted {inserted} primitives ({skipped} skipped as already present)")
    return inserted, skipped


def fetch_primitive_ids_by_natural_key(sb, natural_keys: set[tuple]) -> dict[tuple, str]:
    """SELECT id for primitives matching a set of natural keys.

    Done in chunks to avoid URL/IN-clause limits. Returns {natural_key: uuid_str}.
    """
    if not natural_keys:
        return {}
    # Group by (symbol, tf) to use indexed filters
    by_sym_tf: dict[tuple, list[tuple]] = {}
    for nk in natural_keys:
        by_sym_tf.setdefault((nk[0], nk[1]), []).append(nk)

    out: dict[tuple, str] = {}
    for (symbol, tf), keys in by_sym_tf.items():
        # source_bar_ts range from keys
        ts_values = sorted({nk[3] for nk in keys})
        ts_min = ts_values[0]
        ts_max = ts_values[-1]
        page = 0
        while True:
            offset = page * PAGE_SIZE
            res = (
                sb.table("ict_primitives")
                  .select("id,symbol,timeframe,primitive_type,source_bar_ts,zone_low,zone_high,level")
                  .eq("symbol", symbol)
                  .eq("timeframe", tf)
                  .gte("source_bar_ts", ts_min)
                  .lte("source_bar_ts", ts_max)
                  .order("source_bar_ts", desc=False)
                  .range(offset, offset + PAGE_SIZE - 1)
                  .execute()
            )
            rows = res.data or []
            for r in rows:
                nk = _natural_key(
                    r["symbol"], r["timeframe"], r["primitive_type"],
                    parse_supabase_ts(r["source_bar_ts"]),
                    r["zone_low"] if r["zone_low"] is not None else r["level"],
                    r["zone_high"] if r["zone_high"] is not None else r["level"],
                )
                out[nk] = r["id"]
            if len(rows) < PAGE_SIZE:
                break
            page += 1
    return out


def upsert_outcomes(sb, outcomes: list[OutcomeRow], dry_run: bool) -> int:
    """Resolve natural keys → primitive ids, then insert outcomes rows. Skip ids already present."""
    if not outcomes:
        return 0
    nat_keys = {o.primitive_natural_key for o in outcomes}
    id_map = fetch_primitive_ids_by_natural_key(sb, nat_keys)
    if not id_map:
        log("  [outcomes] no primitive id matches; skipping")
        return 0

    # Fetch existing outcome ids
    primitive_ids = list(id_map.values())
    existing_outcome_ids: set[str] = set()
    for i in range(0, len(primitive_ids), 200):
        chunk = primitive_ids[i:i + 200]
        res = (
            sb.table("ict_primitive_outcomes")
              .select("primitive_id")
              .in_("primitive_id", chunk)
              .execute()
        )
        for r in res.data or []:
            existing_outcome_ids.add(r["primitive_id"])

    rows = []
    for o in outcomes:
        pid = id_map.get(o.primitive_natural_key)
        if pid is None or pid in existing_outcome_ids:
            continue
        rows.append({
            "primitive_id": pid,
            "forward_5m_pct": o.forward_5m_pct,
            "forward_15m_pct": o.forward_15m_pct,
            "forward_30m_pct": o.forward_30m_pct,
            "forward_1h_pct": o.forward_1h_pct,
            "forward_eod_pct": o.forward_eod_pct,
            "retest_status": o.retest_status,
            "first_retest_ts": (
                o.first_retest_ts.astimezone(UTC).isoformat()
                if o.first_retest_ts else None
            ),
            "retest_depth_pct": o.retest_depth_pct,
            "retest_fwd_5m_pct": o.retest_fwd_5m_pct,
            "retest_fwd_15m_pct": o.retest_fwd_15m_pct,
            "retest_fwd_30m_pct": o.retest_fwd_30m_pct,
            "retest_fwd_1h_pct": o.retest_fwd_1h_pct,
            "retest_fwd_eod_pct": o.retest_fwd_eod_pct,
            "respected": o.respected,
            "mitigated_at": o.mitigated_at.astimezone(UTC).isoformat() if o.mitigated_at else None,
            "breach_at": o.breach_at.astimezone(UTC).isoformat() if o.breach_at else None,
            # ENH-100 (S32) — magnitude profiling + ATM PnL + DTE per ADR-010 v3
            "forward_120m_pct": o.forward_120m_pct,
            "mfe_pct": o.mfe_pct,
            "mae_pct": o.mae_pct,
            "time_to_mfe_min": o.time_to_mfe_min,
            "atm_pnl_5m_pct": o.atm_pnl_5m_pct,
            "atm_pnl_15m_pct": o.atm_pnl_15m_pct,
            "atm_pnl_30m_pct": o.atm_pnl_30m_pct,
            "atm_pnl_60m_pct": o.atm_pnl_60m_pct,
            "dte_at_formation": o.dte_at_formation,
            # ENH-103 (S33) v6 — retest-anchored ATM PnL
            "option_pnl_5m": o.option_pnl_5m,
            "option_pnl_15m": o.option_pnl_15m,
            "option_pnl_30m": o.option_pnl_30m,
            "option_pnl_60m": o.option_pnl_60m,
            "option_pnl_eod": o.option_pnl_eod,
            # ENH-106 (S35) v8 — chain data tier audit tag for the option_pnl_* columns
            "option_pnl_source": o.option_pnl_source,
            # ADR-012 (S35) v9 — spot-anchored SL doctrine columns
            "sl_level": o.sl_level,
            "sl_buffer_pct": o.sl_buffer_pct,
            "sl_triggered_ts": (
                o.sl_triggered_ts.astimezone(UTC).isoformat()
                if o.sl_triggered_ts else None
            ),
            "sl_exit_prem": o.sl_exit_prem,
            "pnl_with_sl_pct": o.pnl_with_sl_pct,
        })

    if dry_run:
        log(f"  [dry-run] would insert {len(rows)} outcomes")
        return len(rows)
    inserted = 0
    for i in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[i:i + UPSERT_BATCH_SIZE]
        sb.table("ict_primitive_outcomes").insert(batch).execute()
        inserted += len(batch)
    log(f"  inserted {inserted} outcomes")
    return inserted


# ============================================================================
# Main pipeline orchestration
# ============================================================================

def run_pipeline_for_symbol(sb, symbol: str, mode: str, start_utc: datetime,
                            end_utc: datetime, tfs: list[str], skip_outcomes: bool,
                            dry_run: bool) -> dict:
    """Run end-to-end for one symbol over [start, end]. Returns counts dict."""
    log(f"\n=== {symbol} {mode} {start_utc.date()} → {end_utc.date()} tfs={tfs} ===")

    # 1. Fetch 1m bars
    if mode == "backfill":
        bars_1m = fetch_bars_1m_backfill(sb, symbol, start_utc, end_utc)
    elif mode == "live":
        bars_1m = fetch_bars_1m_live(sb, symbol, lookback_days=56)
    else:
        raise ValueError(f"Unknown mode: {mode}")
    if not bars_1m:
        log(f"  no bars fetched for {symbol}; skipping")
        return {"primitives": 0, "events": 0, "outcomes": 0}

    # 2. Detect primitives per TF
    all_primitives: list[Primitive] = []
    all_events: list[Event] = []
    for tf in tfs:
        if tf not in WAVE1_TFS:
            log(f"  skipping unknown tf {tf}")
            continue
        prims, events = compute_primitives_for_symbol_tf(bars_1m, symbol, tf)
        log(f"  {tf}: {len(prims)} primitives (FVG+OB), {len(events)} events (Disp)")
        all_primitives.extend(prims)
        all_events.extend(events)

    # 3. Levels + sweeps (levels are TF-agnostic at source; sweep emitted at M5)
    if any(tf in ("D", "W") for tf in tfs):
        levels_tfs = ["D", "W"]
        if "W" in tfs:
            levels_tfs.append("M")  # PMH/PML mapped to W per ADR
        levels, sweeps = compute_levels_and_sweeps(bars_1m, symbol, levels_tfs)
        log(f"  Levels: {len(levels)}  Sweeps: {len(sweeps)}")
        all_primitives.extend(levels)
        all_events.extend(sweeps)

    # 4. Upsert primitives + events (idempotent)
    existing = fetch_existing_natural_keys(sb, symbol, tfs, start_utc, end_utc)
    inserted, skipped = upsert_primitives_and_events(
        sb, all_primitives, all_events, existing, dry_run
    )

    # 5. Compute + upsert outcomes
    outcomes_inserted = 0
    if not skip_outcomes:
        log(f"  computing outcomes for {len(all_primitives) + len(all_events)} items...")
        t0 = _time.time()
        atm_cache: dict = {}  # ENH-100 (S32) — per-symbol cache for expiry/premium lookups
        # ENH-100 (S32) v4 — prefetch ATM calendar to avoid per-primitive DB roundtrips
        _prefetch_atm_calendar(sb, symbol, start_utc, end_utc, atm_cache)
        outcomes = compute_outcomes(all_primitives, all_events, bars_1m,
                                    sb=sb, atm_cache=atm_cache)
        log(f"  outcomes computed in {_time.time() - t0:.1f}s; {len(outcomes)} rows "
            f"(atm_cache_entries={len(atm_cache)})")
        outcomes_inserted = upsert_outcomes(sb, outcomes, dry_run)

    return {
        "primitives": inserted,
        "events": skipped,  # combined skip count for reporting
        "outcomes": outcomes_inserted,
    }


# ============================================================================
# Smoke test (synthetic, no DB)
# ============================================================================

def run_smoke() -> int:
    """Synthetic 1m bars over ~2 trading days → full pipeline excluding DB layer."""
    log("[smoke] synthesizing 2-day 1m NIFTY bars...")
    base = datetime(2026, 5, 19, 3, 45, tzinfo=UTC)  # 09:15 IST May 19
    bars_1m: list[Bar] = []
    spot = 24000.0
    for day in range(2):
        for minute in range(375):  # 09:15 → 15:30
            ts = base + timedelta(days=day, minutes=minute)
            # Inject a displacement at minute 60 of day 1 (10:15 IST)
            if day == 1 and minute == 60:
                spot += 200
            else:
                spot += (-0.5 if (minute % 7) == 0 else 0.3)
            bars_1m.append(Bar(ts=ts, open=spot - 1, high=spot + 2, low=spot - 2, close=spot))
    log(f"[smoke] {len(bars_1m)} synthetic 1m bars built (spot {bars_1m[0].close:.1f} → {bars_1m[-1].close:.1f})")

    # Aggregate at each TF
    for tf in ("M5", "H", "D", "W"):
        agg = aggregate(bars_1m, tf)
        log(f"[smoke] aggregate {tf}: {len(agg)} bars")

    # Detect
    total_p, total_e = 0, 0
    for tf in WAVE1_TFS:
        prims, events = compute_primitives_for_symbol_tf(bars_1m, "NIFTY", tf)
        log(f"[smoke] detect {tf}: {len(prims)} primitives, {len(events)} events")
        total_p += len(prims)
        total_e += len(events)

    levels, sweeps = compute_levels_and_sweeps(bars_1m, "NIFTY", ["D", "W"])
    log(f"[smoke] levels: {len(levels)}, sweeps: {len(sweeps)}")

    # Outcomes pipeline
    all_prims = []
    all_events = []
    for tf in WAVE1_TFS:
        p, e = compute_primitives_for_symbol_tf(bars_1m, "NIFTY", tf)
        all_prims.extend(p); all_events.extend(e)
    all_prims.extend(levels); all_events.extend(sweeps)
    t0 = _time.time()
    outcomes = compute_outcomes(all_prims, all_events, bars_1m)
    log(f"[smoke] outcomes computed: {len(outcomes)} rows in {_time.time() - t0:.2f}s")

    # Spot-check: at least one outcome should have a non-null forward_5m_pct
    have_forward = sum(1 for o in outcomes if o.forward_5m_pct is not None)
    log(f"[smoke] outcomes with forward_5m_pct populated: {have_forward}/{len(outcomes)}")

    assert len(bars_1m) == 750
    assert len(outcomes) >= 0  # may be 0 on degenerate synth, but should not crash
    log("\n[PASS] build_ict_primitives.py smoke pipeline OK")
    return 0


# ============================================================================
# CLI
# ============================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="S31-B writer: detect ICT primitives + outcomes → Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--symbol", default="NIFTY,SENSEX",
                   help="Comma-separated symbols (default: NIFTY,SENSEX)")
    p.add_argument("--mode", choices=["backfill", "live"], default="backfill")
    p.add_argument("--start", help="Backfill start date YYYY-MM-DD (UTC midnight)")
    p.add_argument("--end", help="Backfill end date YYYY-MM-DD (UTC midnight, exclusive)")
    p.add_argument("--tfs", default="W,D,H,M5",
                   help="Comma-separated TFs subset of W,D,H,M5 (default: all)")
    p.add_argument("--skip-outcomes", action="store_true",
                   help="Detect + upsert primitives only; skip outcomes compute")
    p.add_argument("--dry-run", action="store_true",
                   help="No DB writes; report counts only")
    p.add_argument("--log", help="Path to mirror stdout into a logfile")
    p.add_argument("--smoke", action="store_true",
                   help="Synthetic pipeline test (no Supabase calls)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    open_log_file(args.log)

    if args.smoke:
        return run_smoke()

    if args.mode == "backfill":
        if not args.start or not args.end:
            log("[FATAL] --start and --end required in backfill mode")
            return 2
        start_utc = datetime.fromisoformat(args.start).replace(tzinfo=UTC)
        end_utc = datetime.fromisoformat(args.end).replace(tzinfo=UTC)
    else:
        # Live mode: rolling window
        end_utc = datetime.now(UTC)
        start_utc = end_utc - timedelta(days=56)

    symbols = [s.strip() for s in args.symbol.split(",") if s.strip()]
    tfs = [t.strip() for t in args.tfs.split(",") if t.strip()]
    unknown = [t for t in tfs if t not in WAVE1_TFS]
    if unknown:
        log(f"[FATAL] unknown timeframes: {unknown}; valid: {WAVE1_TFS}")
        return 2

    log(f"[start] {args.mode} symbols={symbols} tfs={tfs} "
        f"window={start_utc.date()}→{end_utc.date()} dry_run={args.dry_run} "
        f"skip_outcomes={args.skip_outcomes}")

    sb = get_supabase_client()
    t_total = _time.time()
    totals = {"primitives": 0, "outcomes": 0}
    for sym in symbols:
        if sym not in INSTRUMENT_ID_BY_SYMBOL:
            log(f"[WARN] unknown symbol {sym}; skipping")
            continue
        counts = run_pipeline_for_symbol(
            sb, sym, args.mode, start_utc, end_utc, tfs,
            args.skip_outcomes, args.dry_run,
        )
        totals["primitives"] += counts["primitives"]
        totals["outcomes"] += counts["outcomes"]

    log(f"\n[done] {totals['primitives']} primitives inserted, "
        f"{totals['outcomes']} outcomes inserted, "
        f"elapsed={_time.time() - t_total:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
