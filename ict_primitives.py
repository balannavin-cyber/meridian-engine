"""
core/ict_primitives.py — Canonical ICT PD-array primitive detectors.

Per ADR-004 (ACCEPTED 2026-05-20) — Wave 1 of S31-B deliverables.

Implements §5.1 Order Block, §5.2 Fair Value Gap, §6.1 Prior Period Levels,
§7.1 Sweep / Stop Run, §7.2 Displacement.

Design principles (ADR-004 §2):
  - Detection is pure observation: no tier, no WR, no expectancy in detector code.
  - Statistics derive from primitives (separate ict_primitive_outcomes table).
  - Canon over convenience.

These functions are PURE: no DB I/O, no env reads, no file I/O, no logging
side effects. Bars in, dataclasses out. The writer (build_ict_primitives.py)
is the only file that touches Supabase.

Input assumptions:
  - bars are sorted ascending by ts
  - bar.ts is tz-aware (UTC or any tz; IST conversion applied where needed)
  - duplicate timestamps are not present
  - bars within a single call all belong to one (symbol, timeframe)

Per-TF parameters are symbolic via the module-level dicts (OB_MIN_BODY_PCT etc.)
sourced verbatim from ADR-004 §11. Detectors index these by timeframe string.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

Timeframe = Literal["W", "D", "H", "M5", "M1"]
Period = Literal["D", "W", "M"]

# ----------------------------------------------------------------------------
# Per-TF parameter tables (ADR-004 §11) — symbolic, not hardcoded in detectors.
# ----------------------------------------------------------------------------
OB_MIN_BODY_PCT: dict[str, float] = {"W": 0.5, "D": 0.3, "H": 0.2, "M5": 0.1}
DISPLACEMENT_MIN_PCT: dict[str, float] = {"W": 2.0, "D": 1.0, "H": 0.4, "M5": 0.2}
DISPLACEMENT_WINDOW_BARS: dict[str, int] = {"W": 3, "D": 3, "H": 3, "M5": 6}
FVG_MIN_PCT: dict[str, float] = {"W": 0.8, "D": 0.4, "H": 0.2, "M5": 0.08}
SWEEP_MIN_DEPTH_PCT: dict[str, float] = {"W": 0.2, "D": 0.1, "H": 0.05, "M5": 0.025}

# RTH session window (NSE/BSE) — used by PDH/PDL filtering.
RTH_OPEN_IST = time(9, 15)
RTH_CLOSE_IST = time(15, 30)

# Classification of level-type primitives for sweep direction-routing.
_HIGH_SIDE_LEVEL_TYPES = {"PDH", "PWH", "PMH", "BSL", "EQH"}
_LOW_SIDE_LEVEL_TYPES = {"PDL", "PWL", "PML", "SSL", "EQL"}


# ----------------------------------------------------------------------------
# Dataclasses (mirror ict_primitives / ict_primitive_outcomes schema)
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Bar:
    """OHLCV bar. ts is tz-aware. Volume is optional (NSE/BSE indices have no vol)."""
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Primitive:
    """
    Maps to public.ict_primitives row (less id+created_at which are server-side).
    Zone primitives use zone_low/zone_high; level primitives use level.
    Status defaults to 'ACTIVE' on emission.
    """
    symbol: str
    timeframe: str  # 'W' | 'D' | 'H' | 'M5' | 'M1'
    primitive_type: str  # 'BULL_OB' | 'BEAR_OB' | 'BULL_FVG' | 'BEAR_FVG' |
                         # 'PDH' | 'PDL' | 'PWH' | 'PWL' | 'PMH' | 'PML' | ...
    direction: Optional[str]  # 'BULL' | 'BEAR' | 'NONE'
    source_bar_ts: datetime
    valid_from: datetime
    valid_to: Optional[datetime] = None
    zone_low: Optional[float] = None
    zone_high: Optional[float] = None
    level: Optional[float] = None
    status: str = "ACTIVE"
    breach_ts: Optional[datetime] = None
    displacement_pct: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Event:
    """
    Event primitive (Sweep, Displacement, Inducement).
    Anchored at event_ts; no retest concept (ADR-004 §10).
    """
    symbol: str
    timeframe: str
    event_type: str  # 'SWEEP_HIGH' | 'SWEEP_LOW' | 'DISPLACEMENT_UP' | 'DISPLACEMENT_DOWN'
    direction: str   # 'BULL' | 'BEAR'
    event_ts: datetime
    metadata: dict = field(default_factory=dict)


# ----------------------------------------------------------------------------
# Helpers (pure)
# ----------------------------------------------------------------------------

def _is_rth(ts: datetime) -> bool:
    """True iff ts (converted to IST) falls within RTH window 09:15-15:30."""
    ist_ts = ts.astimezone(IST)
    t = ist_ts.time()
    return RTH_OPEN_IST <= t <= RTH_CLOSE_IST


def _body_pct(b: Bar) -> float:
    """abs((close-open)/open)*100. Returns 0.0 if open is 0 (defensive)."""
    return abs(b.close - b.open) / b.open * 100.0 if b.open else 0.0


def _move_pct(b: Bar) -> float:
    """Signed (close-open)/open*100."""
    return (b.close - b.open) / b.open * 100.0 if b.open else 0.0


def _bar_direction(b: Bar) -> str:
    """'BULL' if close>open, 'BEAR' if close<open, 'DOJI' if equal."""
    if b.close > b.open:
        return "BULL"
    if b.close < b.open:
        return "BEAR"
    return "DOJI"


def _period_key(ts: datetime, period: str) -> tuple:
    """IST-based grouping key for D/W/M periods."""
    ist = ts.astimezone(IST)
    if period == "D":
        return (ist.year, ist.month, ist.day)
    if period == "W":
        iso = ist.isocalendar()
        return (iso[0], iso[1])  # (iso-year, iso-week)
    if period == "M":
        return (ist.year, ist.month)
    raise ValueError(f"Unknown period: {period!r}")


# ============================================================================
# §5.2 Fair Value Gap (FVG)
# ============================================================================

def detect_fvgs(bars: list[Bar], symbol: str, tf: str) -> list[Primitive]:
    """
    Three-bar imbalance per ADR-004 §5.2.

    BULL_FVG: bar[i-1].high < bar[i+1].low → zone=[bar[i-1].high, bar[i+1].low]
              Validity: bar[i] closes bullish (close > open) AND
                        gap_pct = (zone_high-zone_low)/bar[i].open*100 >= FVG_MIN_PCT[tf]

    BEAR_FVG: bar[i-1].low > bar[i+1].high → zone=[bar[i+1].high, bar[i-1].low]
              Validity: bar[i] closes bearish AND gap_pct >= FVG_MIN_PCT[tf]

    source_bar_ts = bar[i].ts (middle/displacement bar — the bar that caused the gap)
    valid_from    = bar[i+1].ts (FVG observable at i+1 close)
    """
    out: list[Primitive] = []
    if tf not in FVG_MIN_PCT:
        return out
    min_pct = FVG_MIN_PCT[tf]

    for i in range(1, len(bars) - 1):
        prev, mid, nxt = bars[i - 1], bars[i], bars[i + 1]
        ref = mid.open if mid.open else 1.0

        # BULL_FVG
        if prev.high < nxt.low and mid.close > mid.open:
            zone_low, zone_high = prev.high, nxt.low
            gap_pct = (zone_high - zone_low) / ref * 100.0
            if gap_pct >= min_pct:
                out.append(Primitive(
                    symbol=symbol,
                    timeframe=tf,
                    primitive_type="BULL_FVG",
                    direction="BULL",
                    source_bar_ts=mid.ts,
                    valid_from=nxt.ts,
                    zone_low=zone_low,
                    zone_high=zone_high,
                    displacement_pct=_move_pct(mid),
                    metadata={
                        "bar_minus_1_ts": prev.ts.isoformat(),
                        "bar_plus_1_ts": nxt.ts.isoformat(),
                        "gap_pct": gap_pct,
                    },
                ))

        # BEAR_FVG
        elif prev.low > nxt.high and mid.close < mid.open:
            zone_low, zone_high = nxt.high, prev.low
            gap_pct = (zone_high - zone_low) / ref * 100.0
            if gap_pct >= min_pct:
                out.append(Primitive(
                    symbol=symbol,
                    timeframe=tf,
                    primitive_type="BEAR_FVG",
                    direction="BEAR",
                    source_bar_ts=mid.ts,
                    valid_from=nxt.ts,
                    zone_low=zone_low,
                    zone_high=zone_high,
                    displacement_pct=_move_pct(mid),
                    metadata={
                        "bar_minus_1_ts": prev.ts.isoformat(),
                        "bar_plus_1_ts": nxt.ts.isoformat(),
                        "gap_pct": gap_pct,
                    },
                ))
    return out


# ============================================================================
# §7.2 Displacement
# ============================================================================

def detect_displacements(bars: list[Bar], symbol: str, tf: str,
                         fvgs: list[Primitive]) -> list[Event]:
    """
    Strong directional bar that created an FVG per ADR-004 §7.2.

    A bar qualifies iff:
      - abs(_move_pct(bar)) >= DISPLACEMENT_MIN_PCT[tf]
      - The bar is the middle bar of a confirmed FVG of the same tf
        (FVG.source_bar_ts == bar.ts AND FVG direction matches bar's close direction).

    Event direction follows the bar's directional close.
    Metadata: displacement_pct, created_fvg_source_ts, created_fvg_zone_low/high.
    """
    out: list[Event] = []
    if tf not in DISPLACEMENT_MIN_PCT:
        return out
    min_pct = DISPLACEMENT_MIN_PCT[tf]

    # Index FVGs by source_bar_ts for O(1) lookup; filter to this tf.
    fvg_by_ts: dict[datetime, Primitive] = {
        f.source_bar_ts: f for f in fvgs if f.timeframe == tf
    }

    for b in bars:
        if abs(_move_pct(b)) < min_pct:
            continue
        fvg = fvg_by_ts.get(b.ts)
        if fvg is None:
            continue  # No FVG created — not a canonical displacement per §7.2
        direction = "BULL" if b.close > b.open else "BEAR"
        # Sanity: FVG direction must match bar close direction
        if fvg.direction != direction:
            continue
        event_type = "DISPLACEMENT_UP" if direction == "BULL" else "DISPLACEMENT_DOWN"
        out.append(Event(
            symbol=symbol,
            timeframe=tf,
            event_type=event_type,
            direction=direction,
            event_ts=b.ts,
            metadata={
                "displacement_pct": _move_pct(b),
                "created_fvg_source_ts": fvg.source_bar_ts.isoformat(),
                "created_fvg_zone_low": fvg.zone_low,
                "created_fvg_zone_high": fvg.zone_high,
            },
        ))
    return out


# ============================================================================
# §5.1 Order Block (OB)
# ============================================================================

def detect_order_blocks(bars: list[Bar], symbol: str, tf: str,
                        fvgs: list[Primitive],
                        displacements: list[Event]) -> list[Primitive]:
    """
    Canonical OB per ADR-004 §5.1.

    Algorithm:
      For each confirmed displacement of this tf (which by §7.2 has an associated FVG):
        Walk backward from the displacement bar up to DISPLACEMENT_WINDOW_BARS[tf].
        Take the MOST RECENT opposing-direction candle with body_pct >= OB_MIN_BODY_PCT[tf].
        That candle is the OB.

    Zone bounds: body only — [min(open, close), max(open, close)].
    Wick high/low go to metadata for rendering convenience (canon: body-bound).
    valid_from = displacement bar ts (OB is confirmed at displacement close).
    """
    out: list[Primitive] = []
    if tf not in OB_MIN_BODY_PCT or tf not in DISPLACEMENT_WINDOW_BARS:
        return out
    min_body = OB_MIN_BODY_PCT[tf]
    lookback = DISPLACEMENT_WINDOW_BARS[tf]

    # Bar index by ts for O(1) lookup
    bar_idx: dict[datetime, int] = {b.ts: i for i, b in enumerate(bars)}

    # Dedupe: multiple displacements within `lookback` of the same OB candle
    # would otherwise emit duplicate OBs. First-found (chronologically earliest
    # displacement) wins per "most recent OB closest to impulse start" semantics.
    seen_ob_ts: set[datetime] = set()

    tf_displacements = [d for d in displacements if d.timeframe == tf]

    # Index FVGs by source_bar_ts for OB→FVG linkage metadata
    fvg_by_ts: dict[datetime, Primitive] = {
        f.source_bar_ts: f for f in fvgs if f.timeframe == tf
    }

    for disp in tf_displacements:
        disp_idx = bar_idx.get(disp.event_ts)
        if disp_idx is None or disp_idx == 0:
            continue

        target_dir = "BEAR" if disp.direction == "BULL" else "BULL"
        start = max(0, disp_idx - lookback)
        ob_bar: Optional[Bar] = None
        # Walk back, most-recent first (§5.1 step 5)
        for j in range(disp_idx - 1, start - 1, -1):
            b = bars[j]
            if _bar_direction(b) != target_dir:
                continue
            if _body_pct(b) < min_body:
                continue
            ob_bar = b
            break

        if ob_bar is None or ob_bar.ts in seen_ob_ts:
            continue
        seen_ob_ts.add(ob_bar.ts)

        ob_type = "BULL_OB" if disp.direction == "BULL" else "BEAR_OB"
        zone_low = min(ob_bar.open, ob_bar.close)
        zone_high = max(ob_bar.open, ob_bar.close)
        fvg = fvg_by_ts.get(disp.event_ts)
        out.append(Primitive(
            symbol=symbol,
            timeframe=tf,
            primitive_type=ob_type,
            direction=disp.direction,
            source_bar_ts=ob_bar.ts,
            valid_from=disp.event_ts,
            zone_low=zone_low,
            zone_high=zone_high,
            displacement_pct=disp.metadata.get("displacement_pct"),
            metadata={
                "wick_low": ob_bar.low,
                "wick_high": ob_bar.high,
                "displacement_ts": disp.event_ts.isoformat(),
                "created_fvg_source_ts": (
                    fvg.source_bar_ts.isoformat() if fvg else None
                ),
            },
        ))
    return out


# ============================================================================
# §6.1 Prior Period Levels (PDH, PDL, PWH, PWL, PMH, PML)
# ============================================================================

def detect_prior_period_levels(bars: list[Bar], symbol: str,
                                period: str) -> list[Primitive]:
    """
    Prior-period highs/lows per ADR-004 §6.1.

    Levels are PRICES (level field), not zones (zone_low/zone_high stay NULL).

    period='D' → PDH/PDL, filtered to RTH 09:15-15:30 IST.
    period='W' → PWH/PWL.
    period='M' → PMH/PML, emitted at timeframe='W' (schema CHECK enum has no 'M');
                metadata.period='M' preserves semantic.

    For each period N (N>=1, i.e. not the first period in window): emit PXH+PXL
    with level=prior period's max(high)/min(low), valid_from=current period's
    first bar.ts. source_bar_ts is the bar that set the high/low (auditability).

    valid_to stays NULL; expiration is handled by status transitions (SWEPT/
    TAKEN_OUT) downstream, not by time.
    """
    out: list[Primitive] = []
    if period not in ("D", "W", "M"):
        return out

    # Filter RTH for daily; W/M use all bars within the period.
    if period == "D":
        rth_bars = [b for b in bars if _is_rth(b.ts)]
    else:
        rth_bars = list(bars)

    # Group bars by period_key
    groups: dict[tuple, list[Bar]] = {}
    for b in rth_bars:
        key = _period_key(b.ts, period)
        groups.setdefault(key, []).append(b)

    keys_sorted = sorted(groups.keys())
    type_high, type_low = {
        "D": ("PDH", "PDL"),
        "W": ("PWH", "PWL"),
        "M": ("PMH", "PML"),
    }[period]
    # M maps to TF='W' for schema CHECK compliance; semantic in metadata.
    tf_for_period = {"D": "D", "W": "W", "M": "W"}[period]

    for k in range(1, len(keys_sorted)):
        prev_key = keys_sorted[k - 1]
        curr_key = keys_sorted[k]
        prev_bars = groups[prev_key]
        curr_bars = groups[curr_key]
        if not prev_bars or not curr_bars:
            continue

        prev_high = max(b.high for b in prev_bars)
        prev_low = min(b.low for b in prev_bars)
        valid_from = curr_bars[0].ts
        bar_high = max(prev_bars, key=lambda x: x.high)
        bar_low = min(prev_bars, key=lambda x: x.low)

        out.append(Primitive(
            symbol=symbol,
            timeframe=tf_for_period,
            primitive_type=type_high,
            direction="NONE",
            source_bar_ts=bar_high.ts,
            valid_from=valid_from,
            level=prev_high,
            metadata={"period": period, "prior_period_key": str(prev_key)},
        ))
        out.append(Primitive(
            symbol=symbol,
            timeframe=tf_for_period,
            primitive_type=type_low,
            direction="NONE",
            source_bar_ts=bar_low.ts,
            valid_from=valid_from,
            level=prev_low,
            metadata={"period": period, "prior_period_key": str(prev_key)},
        ))
    return out


# ============================================================================
# §7.1 Sweep / Stop Run
# ============================================================================

def detect_sweeps(bars: list[Bar], symbol: str, tf: str,
                  known_levels: list[Primitive]) -> list[Event]:
    """
    Wick beyond a known liquidity level with close back inside per ADR-004 §7.1.

    SWEEP_HIGH: bar.high > level AND bar.close < level AND
                (bar.high-level)/level*100 >= SWEEP_MIN_DEPTH_PCT[tf]
    SWEEP_LOW:  bar.low < level AND bar.close > level AND
                (level-bar.low)/level*100 >= SWEEP_MIN_DEPTH_PCT[tf]

    known_levels: any level-type primitives (PDH/PDL/PWH/PWL/PMH/PML in wave 1;
    BSL/SSL + Equal H/L in wave 2). Only ACTIVE levels with valid_from <= bar.ts
    are evaluated.

    Per-bar aggregation (S31-B patch 2026-05-20): one SWEEP_HIGH and one
    SWEEP_LOW max per bar per timeframe. ICT canon treats a single bar's
    stop-hunt as one event that may target multiple liquidity pools.
    metadata.swept_levels carries the full list of (type, price, depth_pct).
    The primary scalar fields (swept_level_type/price/depth_pct) reflect the
    DEEPEST sweep at that bar — most informative for downstream consumers.

    Sweep direction:
      SWEEP_HIGH (above a high-side level) → direction='BEAR' (mean-reversion bias)
      SWEEP_LOW  (below a low-side level)  → direction='BULL'
    """
    out: list[Event] = []
    if tf not in SWEEP_MIN_DEPTH_PCT:
        return out
    min_depth = SWEEP_MIN_DEPTH_PCT[tf]

    candidate_levels = [
        lv for lv in known_levels
        if lv.level is not None and lv.status == "ACTIVE"
    ]

    for b in bars:
        high_hits: list[dict] = []
        low_hits: list[dict] = []
        for lv in candidate_levels:
            if lv.valid_from > b.ts:
                continue
            if lv.valid_to is not None and lv.valid_to <= b.ts:
                continue

            if lv.primitive_type in _HIGH_SIDE_LEVEL_TYPES:
                if b.high > lv.level and b.close < lv.level:
                    depth_pct = (b.high - lv.level) / lv.level * 100.0
                    if depth_pct >= min_depth:
                        high_hits.append({
                            "swept_level_type": lv.primitive_type,
                            "swept_level_price": lv.level,
                            "sweep_depth_pct": depth_pct,
                        })
            elif lv.primitive_type in _LOW_SIDE_LEVEL_TYPES:
                if b.low < lv.level and b.close > lv.level:
                    depth_pct = (lv.level - b.low) / lv.level * 100.0
                    if depth_pct >= min_depth:
                        low_hits.append({
                            "swept_level_type": lv.primitive_type,
                            "swept_level_price": lv.level,
                            "sweep_depth_pct": depth_pct,
                        })

        if high_hits:
            primary = max(high_hits, key=lambda h: h["sweep_depth_pct"])
            out.append(Event(
                symbol=symbol,
                timeframe=tf,
                event_type="SWEEP_HIGH",
                direction="BEAR",
                event_ts=b.ts,
                metadata={
                    "swept_level_type": primary["swept_level_type"],
                    "swept_level_price": primary["swept_level_price"],
                    "sweep_depth_pct": primary["sweep_depth_pct"],
                    "bar_high": b.high,
                    "bar_close": b.close,
                    "swept_levels": high_hits,
                },
            ))
        if low_hits:
            primary = max(low_hits, key=lambda h: h["sweep_depth_pct"])
            out.append(Event(
                symbol=symbol,
                timeframe=tf,
                event_type="SWEEP_LOW",
                direction="BULL",
                event_ts=b.ts,
                metadata={
                    "swept_level_type": primary["swept_level_type"],
                    "swept_level_price": primary["swept_level_price"],
                    "sweep_depth_pct": primary["sweep_depth_pct"],
                    "bar_low": b.low,
                    "bar_close": b.close,
                    "swept_levels": low_hits,
                },
            ))
    return out


# ============================================================================
# Module-level smoke test
#   python -m core.ict_primitives  (when placed under core/)
#   python ict_primitives.py       (when run standalone)
# ============================================================================

if __name__ == "__main__":
    UTC = timezone.utc
    base = datetime(2026, 5, 20, 4, 0, tzinfo=UTC)  # 09:30 IST = 04:00 UTC

    def mk(i: int, o: float, h: float, l: float, c: float,
           tf_min: int = 60) -> Bar:
        return Bar(ts=base + timedelta(minutes=tf_min * i),
                   open=o, high=h, low=l, close=c)

    # Synth on H timeframe: build a clean BULL_FVG + DISPLACEMENT_UP + BULL_OB
    #   bar 0: down-close strong body (will be the OB candidate)
    #   bar 1: small filler (avoid being the OB)
    #   bar 2: big bullish displacement (creates FVG between bar 1.high and bar 3.low)
    #   bar 3: continuation
    #   bar 4: filler
    bars_h = [
        mk(0, 24000, 24015, 23900, 23910),   # body ~0.375%, BEAR → OB candidate
        mk(1, 23910, 23925, 23895, 23900),   # small filler
        mk(2, 23905, 24080, 23900, 24075),   # +0.71% move BULL → displacement
        mk(3, 24080, 24105, 24070, 24095),   # creates BULL_FVG (23925, 24070)
        mk(4, 24095, 24120, 24085, 24110),
    ]

    fvgs = detect_fvgs(bars_h, "NIFTY", "H")
    assert len(fvgs) == 1, f"expected 1 H FVG, got {len(fvgs)}"
    assert fvgs[0].primitive_type == "BULL_FVG"
    assert fvgs[0].zone_low == 23925 and fvgs[0].zone_high == 24070
    print(f"[OK] §5.2 FVG  detected: {len(fvgs)} (BULL_FVG zone=[{fvgs[0].zone_low}, {fvgs[0].zone_high}] "
          f"gap_pct={fvgs[0].metadata['gap_pct']:.3f})")

    disps = detect_displacements(bars_h, "NIFTY", "H", fvgs)
    assert len(disps) == 1, f"expected 1 displacement, got {len(disps)}"
    assert disps[0].event_type == "DISPLACEMENT_UP"
    print(f"[OK] §7.2 Disp detected: {len(disps)} ({disps[0].event_type} "
          f"pct={disps[0].metadata['displacement_pct']:.3f})")

    obs = detect_order_blocks(bars_h, "NIFTY", "H", fvgs, disps)
    assert len(obs) == 1, f"expected 1 OB, got {len(obs)}"
    assert obs[0].primitive_type == "BULL_OB"
    assert obs[0].zone_low == 23910 and obs[0].zone_high == 24000  # body of bar 0
    print(f"[OK] §5.1 OB   detected: {len(obs)} ({obs[0].primitive_type} "
          f"zone=[{obs[0].zone_low}, {obs[0].zone_high}])")

    # PDH/PDL: two days of bars at 15-min granularity inside RTH.
    day1_start = datetime(2026, 5, 19, 3, 45, tzinfo=UTC)  # 09:15 IST
    day2_start = datetime(2026, 5, 20, 3, 45, tzinfo=UTC)
    day1 = [Bar(ts=day1_start + timedelta(minutes=15 * i),
                open=24000 + i, high=24050 + i,
                low=23950 + i, close=24010 + i) for i in range(20)]
    day2 = [Bar(ts=day2_start + timedelta(minutes=15 * i),
                open=24100 + i, high=24150 + i,
                low=24050 + i, close=24110 + i) for i in range(5)]
    levels = detect_prior_period_levels(day1 + day2, "NIFTY", "D")
    assert len(levels) == 2, f"expected 2 prior-day levels (PDH+PDL), got {len(levels)}"
    pdh = next(lv for lv in levels if lv.primitive_type == "PDH")
    pdl = next(lv for lv in levels if lv.primitive_type == "PDL")
    assert pdh.level == 24069  # day1 max(high) = 24050+19
    assert pdl.level == 23950  # day1 min(low)  = 23950+0
    print(f"[OK] §6.1 Lvls detected: {len(levels)} (PDH={pdh.level} PDL={pdl.level})")

    # Sweep: a bar wicks above PDH then closes back below it.
    sweep_bar = Bar(ts=day2_start + timedelta(hours=2),
                    open=pdh.level - 5,
                    high=pdh.level + 30,
                    low=pdh.level - 10,
                    close=pdh.level - 8)
    sweeps = detect_sweeps([sweep_bar], "NIFTY", "H", [pdh])
    assert len(sweeps) == 1, f"expected 1 sweep, got {len(sweeps)}"
    assert sweeps[0].event_type == "SWEEP_HIGH"
    assert sweeps[0].metadata["swept_level_type"] == "PDH"
    print(f"[OK] §7.1 Swp  detected: {len(sweeps)} ({sweeps[0].event_type} "
          f"swept {sweeps[0].metadata['swept_level_type']}@{sweeps[0].metadata['swept_level_price']:.0f} "
          f"depth={sweeps[0].metadata['sweep_depth_pct']:.3f}%)")

    print("\n[PASS] core/ict_primitives.py smoke test — all 5 wave-1 detectors operational.")
