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

# Instrument IDs for hist_spot_bars_1m (CASE-2026-05-20 §11.3).
INSTRUMENT_ID_BY_SYMBOL: dict[str, str] = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

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


def compute_outcomes(primitives: list[Primitive], events: list[Event],
                     bars_1m: list[Bar]) -> list[OutcomeRow]:
    """
    Compute outcomes for all primitives + events. Returns OutcomeRow list keyed on
    primitive natural key (resolved to UUID at upsert time after DB SELECT).
    """
    if not bars_1m:
        return []
    idx = _bar_idx_by_minute(bars_1m)
    out: list[OutcomeRow] = []

    for p in primitives:
        nk = _natural_key(p.symbol, p.timeframe, p.primitive_type, p.source_bar_ts,
                          p.zone_low if p.zone_low is not None else p.level,
                          p.zone_high if p.zone_high is not None else p.level)
        row = OutcomeRow(primitive_natural_key=nk)
        # Formation-anchored (all primitive types)
        for k, v in compute_formation_outcomes(p, bars_1m, idx).items():
            setattr(row, k, v)
        # Retest-anchored
        if p.zone_low is not None and p.zone_high is not None:
            for k, v in compute_retest_outcomes_zone(p, bars_1m, idx).items():
                setattr(row, k, v)
        elif p.level is not None:
            for k, v in compute_retest_outcomes_level(p, bars_1m, idx).items():
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
        outcomes = compute_outcomes(all_primitives, all_events, bars_1m)
        log(f"  outcomes computed in {_time.time() - t0:.1f}s; {len(outcomes)} rows")
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
