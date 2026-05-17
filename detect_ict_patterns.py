"""
detect_ict_patterns.py
ENH-37 — MERDIAN ICT Pattern Detection Layer

Standalone module. No DB writes. Takes spot bars, returns detected patterns
with quality metadata. Called by the runner every 5-minute cycle.

Patterns detected:
  BULL_OB  — Bullish Order Block: bearish candle before bullish impulse
  BEAR_OB  — Bearish Order Block: bullish candle before bearish impulse
  BULL_FVG — Bullish Fair Value Gap: price gap upward between bars i-1 and i+1
  JUDAS_BULL — Opening trap: opening drop then reversal (one-shot at 09:30)

Quality tier assignment (from Experiment 8):
  TIER1 (1.5x): Morning + MOM_YES + IMP_WEK + HIGH_IV
  TIER2 (1.0x): IMP_WEK + any other
  SKIP  (0.0x): IMP_STR detected (BEAR_OB -7.4% expectancy)

MTF context (from ict_htf_zones lookup):
  HIGH:   intraday zone inside active weekly zone
  MEDIUM: intraday zone inside active daily zone only
  LOW:    no HTF zone confluence

Usage:
    from detect_ict_patterns import ICTDetector

    detector = ICTDetector(symbol="NIFTY")
    patterns = detector.detect(bars, atm_iv=15.2, htf_zones=[])
    # Returns list of ICTPattern objects
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time as dtime
from typing import Optional


# ── Configuration ─────────────────────────────────────────────────────

OB_MIN_MOVE_PCT   = 0.40   # % impulse after OB to qualify
FVG_MIN_PCT       = 0.10   # % gap size minimum
JUDAS_MIN_PCT     = 0.25   # % opening drop minimum for Judas
LOOKBACK_BARS     = 3      # bars before pattern for sequence features
SWEEP_LOOKBACK    = 5      # bars before pattern for prior sweep check
SWEEP_MIN_PCT     = 0.10   # % beyond prior session H/L to qualify as sweep
STRONG_IMPULSE    = 0.30   # cumulative |return|% = IMP_STR (skip signal)

# IV thresholds for size scaling (Experiment 5)
LOW_IV_THRESHOLD  = 12.0   # below = 0.5x
HIGH_IV_THRESHOLD = 18.0   # above = 1.5x

# Time zones (IST)
OPEN_START    = dtime(9, 15)
MORNING_START = dtime(10, 0)
MIDDAY_START  = dtime(11, 30)
AFTNOON_START = dtime(13, 30)
SESSION_END   = dtime(15, 30)
POWER_HOUR    = dtime(15, 0)   # no new signals after this

# Option type by pattern
OPT_TYPE = {
    "BULL_OB":    "CE",
    "BEAR_OB":    "PE",
    "BULL_FVG":   "CE",
    "BEAR_FVG":   "PE",
    "JUDAS_BULL": "CE",
}

# Direction by pattern
DIRECTION = {
    "BULL_OB":    +1,
    "BEAR_OB":    -1,
    "BULL_FVG":   +1,
    "BEAR_FVG":   -1,
    "JUDAS_BULL": +1,
}


# ── Data structures ───────────────────────────────────────────────────

@dataclass
class Bar:
    """Normalised 1-minute spot bar."""
    bar_ts:     datetime
    open:       float
    high:       float
    low:        float
    close:      float
    trade_date: object = None   # date


@dataclass
class HTFZone:
    """Higher-timeframe zone from ict_htf_zones table."""
    id:           str
    symbol:       str
    timeframe:    str           # W | D
    pattern_type: str
    direction:    int
    zone_high:    float
    zone_low:     float
    status:       str = "ACTIVE"


@dataclass
class ICTPattern:
    """Detected ICT pattern with full quality metadata."""
    # Core identity
    symbol:         str
    pattern_type:   str
    direction:      int
    opt_type:       str

    # Bar location
    bar_ts:         datetime
    trade_date:     object

    # Price levels
    zone_high:      float
    zone_low:       float
    spot_at_detection: float

    # Quality
    ict_tier:       str         # TIER1 | TIER2 | SKIP
    ict_size_mult:  float       # 0.5 | 1.0 | 1.5

    # Sequence features (Experiment 8)
    has_prior_sweep: bool = False
    mom_aligned:     bool = False
    impulse_strong:  bool = False
    time_zone:       str  = "OTHER"

    # MTF context
    mtf_context:    str  = "LOW"   # HIGH | MEDIUM | LOW
    htf_zone_id:    Optional[str] = None

    # IV context
    atm_iv_at_detection: Optional[float] = None

    def to_db_row(self) -> dict:
        """Convert to dict for Supabase upsert into ict_zones."""
        return {
            "symbol":               self.symbol,
            "trade_date":           str(self.trade_date),
            "detected_at_ts":       self.bar_ts.isoformat(),
            "session_bar_ts":       self.bar_ts.isoformat(),
            "pattern_type":         self.pattern_type,
            "direction":            self.direction,
            "opt_type":             self.opt_type,
            "zone_high":            self.zone_high,
            "zone_low":             self.zone_low,
            "spot_at_detection":    self.spot_at_detection,
            "ict_tier":             self.ict_tier,
            "ict_size_mult":        self.ict_size_mult,
            "has_prior_sweep":      self.has_prior_sweep,
            "mom_aligned":          self.mom_aligned,
            "impulse_strong":       self.impulse_strong,
            "time_zone":            self.time_zone,
            "mtf_context":          self.mtf_context,
            "htf_zone_id":          self.htf_zone_id,
            "atm_iv_at_detection":  self.atm_iv_at_detection,
            "status":               "ACTIVE",
        }


# ── Utility functions ─────────────────────────────────────────────────

def pct(a: float, b: float) -> float:
    return 100.0 * (b - a) / a if a else 0.0

def time_zone_label(ts: datetime) -> str:
    # Session 10 2026-04-26 fix: bar_ts arrives as UTC timestamptz from
    # hist_spot_bars_1m. Comparing UTC clock-time against IST constants
    # (OPEN_START=09:15 etc.) caused 100% of detections to fall through
    # to "OTHER" -- killing all TIER1 promotion paths.
    # Convert to IST before extracting time-of-day.
    from zoneinfo import ZoneInfo
    if ts.tzinfo is not None:
        ts_ist = ts.astimezone(ZoneInfo("Asia/Kolkata"))
    else:
        # Naive datetime: assume already IST (legacy callers).
        ts_ist = ts
    t = ts_ist.time()
    if OPEN_START <= t < MORNING_START:
        return "OPEN"
    if MORNING_START <= t < MIDDAY_START:
        return "MORNING"
    if MIDDAY_START <= t < AFTNOON_START:
        return "MIDDAY"
    if AFTNOON_START <= t <= SESSION_END:
        return "AFTNOON"
    return "OTHER"

def iv_size_mult(atm_iv: Optional[float], pattern_type: str) -> float:
    """
    IV-scaled position sizing from Experiment 5.
    JUDAS_BULL: always 1.0x (HIGH_IV degrades Judas slightly).
    """
    if pattern_type == "JUDAS_BULL":
        return 1.0
    if atm_iv is None:
        return 1.0
    if atm_iv < LOW_IV_THRESHOLD:
        return 0.5
    if atm_iv >= HIGH_IV_THRESHOLD:
        return 1.5
    return 1.0


# ── Sequence feature computation ──────────────────────────────────────

def compute_sequence_features(
    bars:       list[Bar],
    pat_idx:    int,
    direction:  int,
    prior_high: Optional[float],
    prior_low:  Optional[float],
) -> dict:
    """
    Compute Experiment 8 sequence features for bar at pat_idx.
    Returns dict with: has_prior_sweep, mom_aligned, impulse_strong.
    """
    n = pat_idx

    # Momentum alignment: 2+ of last 3 bars counter-direction
    mom_aligned = False
    if n >= LOOKBACK_BARS:
        preceding = bars[n - LOOKBACK_BARS:n]
        counter = sum(
            1 for b in preceding
            if (direction == +1 and b.close < b.open) or
               (direction == -1 and b.close > b.open)
        )
        mom_aligned = counter >= 2

    # Impulse strength: sum of |returns| in last 3 bars
    impulse_strong = False
    if n >= LOOKBACK_BARS:
        preceding = bars[n - LOOKBACK_BARS:n]
        total_move = sum(abs(pct(b.open, b.close)) for b in preceding)
        impulse_strong = total_move >= STRONG_IMPULSE

    # Prior sweep: did price breach prior session H/L in last 5 bars
    has_prior_sweep = False
    if prior_high is not None and prior_low is not None:
        sweep_start = max(0, n - SWEEP_LOOKBACK)
        for b in bars[sweep_start:n + 1]:
            if direction == +1 and pct(prior_low, b.low) * -1 >= SWEEP_MIN_PCT:
                has_prior_sweep = True
                break
            if direction == -1 and pct(prior_high, b.high) >= SWEEP_MIN_PCT:
                has_prior_sweep = True
                break

    return {
        "mom_aligned":    mom_aligned,
        "impulse_strong": impulse_strong,
        "has_prior_sweep": has_prior_sweep,
    }


def assign_tier(
    pattern_type:   str,
    seq:            dict,
    tz_label:       str,
    atm_iv:         Optional[float],
) -> str:
    """
    Assign signal quality tier from Experiment 8 findings.

    BEAR_OB tiers:
      TIER1: Morning + MOM_YES + IMP_WEK
      TIER2: IMP_WEK (any other)
      SKIP:  IMP_STR (-7.4% expectancy)

    BULL_OB tiers:
      TIER1: Morning OR Afternoon + IMP_WEK
      TIER2: NO_SWEEP + IMP_WEK
      SKIP:  OPEN session (3.4% expectancy, 45% WR)

    BULL_FVG: always TIER2 (no sequence filter adds value)
    JUDAS_BULL: always TIER2 (fixed sizing regardless)
    """
    imp_str = seq["impulse_strong"]
    mom_yes = seq["mom_aligned"]

    if pattern_type == "BEAR_OB":
        # ENH-64 sub-rule 2: BEAR_OB AFTNOON hard skip.
        # -24.7% exp, 17% WR (Exp 8 / Signal Rule Book v1.1 Rule 1).
        # Time-based skip takes precedence over impulse-based tiering.
        if tz_label == "AFTNOON":
            return "SKIP"
        if imp_str:
            return "SKIP"
        if mom_yes and tz_label == "MORNING":
            return "TIER1"
        return "TIER2"

    if pattern_type == "BULL_OB":
        if imp_str:
            return "TIER2"   # still positive but reduced
        if tz_label == "OPEN":
            return "SKIP"    # 3.4% exp, 45% WR — not worth it
        if tz_label in ("MORNING", "AFTNOON"):
            return "TIER1"
        return "TIER2"

    # BULL_FVG and JUDAS_BULL
    # ENH-64 sub-rule 3: BULL_FVG LOW_IV skip.
    # 0% WR N=23, -14.3% exp (Exp 5).
    if pattern_type == "BULL_FVG" and atm_iv is not None and atm_iv < LOW_IV_THRESHOLD:
        return "SKIP"
    return "TIER2"


# ── MTF context lookup ────────────────────────────────────────────────

def get_mtf_context(
    spot:      float,
    direction: int,
    htf_zones: list[HTFZone],
) -> tuple[str, Optional[str]]:
    """
    Determine MTF context by checking if current spot sits inside
    an active HTF zone in the same direction.

    MTF Hierarchy (zone age = institutional significance):
      VERY_HIGH: spot inside weekly zone  (multi-session, proven)
      HIGH:      spot inside daily zone   (session-proven, pre-market)
      MEDIUM:    spot inside 1H zone      (nascent, same-session)
      LOW:       no confluence
    """
    weekly_match = None
    daily_match  = None
    hourly_match = None

    for zone in htf_zones:
        if zone.status != "ACTIVE":
            continue
        if zone.direction != direction:
            continue
        if zone.zone_low <= spot <= zone.zone_high:
            if zone.timeframe == "W":
                weekly_match = zone
            elif zone.timeframe == "D":
                daily_match = zone
            elif zone.timeframe == "H":
                hourly_match = zone

    if weekly_match:
        return "VERY_HIGH", weekly_match.id
    if daily_match:
        return "HIGH", daily_match.id
    if hourly_match:
        return "MEDIUM", hourly_match.id
    return "LOW", None


# ── Pattern detectors ─────────────────────────────────────────────────

def detect_obs(
    bars:       list[Bar],
    prior_high: Optional[float],
    prior_low:  Optional[float],
) -> list[tuple[int, str]]:
    """
    Detect Order Blocks: (bar_index, pattern_type).
    A bearish OB (BULL_OB) = bearish candle before bullish impulse.
    A bullish OB (BEAR_OB) = bullish candle before bearish impulse.
    """
    results = []
    seen    = set()
    n       = len(bars)

    for i in range(n - 6):
        mv = pct(bars[i].close, bars[min(i + 5, n - 1)].close)

        if mv <= -OB_MIN_MOVE_PCT:
            # Bearish impulse → look back for last bullish candle (BEAR_OB)
            for j in range(i, max(i - 6, -1), -1):
                if bars[j].close > bars[j].open and j not in seen:
                    seen.add(j)
                    results.append((j, "BEAR_OB"))
                    break

        elif mv >= OB_MIN_MOVE_PCT:
            # Bullish impulse → look back for last bearish candle (BULL_OB)
            for j in range(i, max(i - 6, -1), -1):
                if bars[j].close < bars[j].open and j not in seen:
                    seen.add(j)
                    results.append((j, "BULL_OB"))
                    break

    return results


def detect_fvg(bars: list[Bar]) -> list[tuple[int, str]]:
    """
    Detect Fair Value Gaps in both directions (TD-058 fix, Session 17).
    BULL_FVG: bars[i-1].high < bars[i+1].low and gap >= FVG_MIN_PCT.
    BEAR_FVG: bars[i-1].low  > bars[i+1].high and gap >= FVG_MIN_PCT.
    Pattern bar is bars[i] (the middle bar).
    """
    results = []
    min_g   = FVG_MIN_PCT / 100.0

    for i in range(1, len(bars) - 1):
        prev, curr, nxt = bars[i - 1], bars[i], bars[i + 1]
        ref = curr.close
        if prev.high < nxt.low and (nxt.low - prev.high) / ref >= min_g:
            results.append((i, "BULL_FVG"))
        elif prev.low > nxt.high and (prev.low - nxt.high) / ref >= min_g:
            results.append((i, "BEAR_FVG"))

    return results


def detect_judas(bars: list[Bar]) -> list[tuple[int, str]]:
    """
    Detect Judas Bull setup (one-shot check at bar 14 = 09:29 IST).
    Opening move down > JUDAS_MIN_PCT, then retraces > 50% of the drop.
    """
    if len(bars) < 46:
        return []

    mv = pct(bars[0].open, bars[14].close)
    if abs(mv) < JUDAS_MIN_PCT:
        return []

    # Only BULL (opening drop then reversal upward)
    if mv < 0:
        rev = bars[15:45]
        max_recovery = pct(bars[14].close, max(b.high for b in rev))
        if max_recovery >= abs(mv) * 0.50:
            return [(14, "JUDAS_BULL")]

    return []


# ── Main detector class ───────────────────────────────────────────────

class ICTDetector:
    """
    Detects ICT patterns on intraday 1-minute spot bars.
    Called every 5-minute runner cycle with the last N bars of the session.

    Usage:
        detector = ICTDetector(symbol="NIFTY")
        patterns = detector.detect(
            bars=session_bars,        # list[Bar], full session so far
            atm_iv=15.2,              # from market_state_snapshots
            htf_zones=[],             # list[HTFZone] from ict_htf_zones
            prior_high=23550.0,       # prior session high
            prior_low=23200.0,        # prior session low
        )
    """

    def __init__(self, symbol: str):
        self.symbol = symbol

    def detect(
        self,
        bars:       list[Bar],
        atm_iv:     Optional[float] = None,
        htf_zones:  list[HTFZone]   = None,
        prior_high: Optional[float] = None,
        prior_low:  Optional[float] = None,
    ) -> list[ICTPattern]:
        """
        Run all detectors on bars, return list of ICTPattern.
        Only returns patterns detected on the LAST 10 bars (sub-cycle
        detection — avoids re-detecting old zones already in DB).
        Caller is responsible for deduplication against existing DB zones.
        """
        if not bars:
            return []

        htf_zones = htf_zones or []

        # TD-060 fix (Session 17): check_from filter removed.
        # Previous logic: check_from = max(0, len(bars) - 10) created a
        # 4-bar eligible window (slice_idx 20-23 in detect_obs's `i in
        # range(n-6)` loop). With runner's 5-bar cycle stride, the 4-bar
        # window + 5-bar stride created gaps where OBs at certain
        # session-idx offsets missed every cycle. Result: ~74% pattern
        # coverage at most, frequently 0 OBs in production.
        # Caller (runner) controls scan window via bars input slice
        # (bars[-30:]). Re-detection across cycles is idempotent via
        # on_conflict upsert in write_new_zones().

        # Detect all pattern types
        ob_candidates  = detect_obs(bars, prior_high, prior_low)
        fvg_candidates = detect_fvg(bars)
        judas_candidates = detect_judas(bars)

        all_candidates = (
            [(idx, pt) for idx, pt in ob_candidates] +
            [(idx, pt) for idx, pt in fvg_candidates] +
            [(idx, pt) for idx, pt in judas_candidates]
        )

        patterns = []
        for idx, pattern_type in all_candidates:
            bar = bars[idx]

            # Skip if before 09:15 or after 15:00 (power hour gate)
            if bar.bar_ts.time() >= POWER_HOUR:
                continue

            direction = DIRECTION[pattern_type]
            opt_type  = OPT_TYPE[pattern_type]
            tz_label  = time_zone_label(bar.bar_ts)

            # Sequence features
            seq = compute_sequence_features(
                bars, idx, direction, prior_high, prior_low
            )

            # Tier assignment
            tier = assign_tier(pattern_type, seq, tz_label, atm_iv)

            # Size multiplier: iv_scaled × tier modifier
            base_mult = iv_size_mult(atm_iv, pattern_type)
            if tier == "TIER1":
                size_mult = min(1.5, base_mult * 1.5)
            elif tier == "SKIP":
                size_mult = 0.0
            else:
                size_mult = base_mult

            # MTF context
            mtf_ctx, htf_zone_id = get_mtf_context(
                bar.close, direction, htf_zones
            )

            # Zone levels
            if pattern_type in ("BULL_OB", "BEAR_OB"):
                zone_high = max(bar.open, bar.close)
                zone_low  = min(bar.open, bar.close)
            elif pattern_type == "BULL_FVG":
                # Gap between prior bar high and next bar low
                if idx > 0 and idx < len(bars) - 1:
                    zone_low  = bars[idx - 1].high
                    zone_high = bars[idx + 1].low
                else:
                    zone_high = bar.high
                    zone_low  = bar.low
            elif pattern_type == "BEAR_FVG":
                # TD-058 mirror: gap between prior bar low and next bar high.
                # zone_high = prior bar low (top of gap, breach level on the way up).
                # zone_low  = next  bar high (bottom of gap).
                if idx > 0 and idx < len(bars) - 1:
                    zone_high = bars[idx - 1].low
                    zone_low  = bars[idx + 1].high
                else:
                    zone_high = bar.high
                    zone_low  = bar.low
            else:
                # JUDAS_BULL — use bar range
                zone_high = bar.high
                zone_low  = bar.low

            pattern = ICTPattern(
                symbol             = self.symbol,
                pattern_type       = pattern_type,
                direction          = direction,
                opt_type           = opt_type,
                bar_ts             = bar.bar_ts,
                trade_date         = bar.trade_date,
                zone_high          = zone_high,
                zone_low           = zone_low,
                spot_at_detection  = bar.close,
                ict_tier           = tier,
                ict_size_mult      = size_mult,
                has_prior_sweep    = seq["has_prior_sweep"],
                mom_aligned        = seq["mom_aligned"],
                impulse_strong     = seq["impulse_strong"],
                time_zone          = tz_label,
                mtf_context        = mtf_ctx,
                htf_zone_id        = htf_zone_id,
                atm_iv_at_detection = atm_iv,
            )
            patterns.append(pattern)

        return patterns

    def check_zone_breaches(
        self,
        active_zones: list[dict],
        current_spot: float,
    ) -> list[str]:
        """
        Check which active zones have been breached by current spot.
        A zone is BROKEN when spot CLOSES through it.

        Returns list of zone IDs to mark as BROKEN.
        Used each cycle to update zone lifecycle.
        """
        broken_ids = []
        for zone in active_zones:
            direction = zone.get("direction", 0)
            zone_high = float(zone.get("zone_high", 0))
            zone_low  = float(zone.get("zone_low", 0))

            if direction == +1:
                # BULL zone: broken if price closes BELOW zone low
                if current_spot < zone_low:
                    broken_ids.append(zone["id"])
            elif direction == -1:
                # BEAR zone: broken if price closes ABOVE zone high
                if current_spot > zone_high:
                    broken_ids.append(zone["id"])

        return broken_ids


# ── Signal enrichment helper ──────────────────────────────────────────

def get_best_active_zone(
    active_zones:  list[dict],
    current_spot:  float,
    action:        str,
) -> Optional[dict]:
    """
    TD-S30-NEW-3 fix (Session 31) — observational attachment.

    Returns the highest-quality ACTIVE zone whose
    [zone_low, zone_high] contains current_spot. Direction-of-action
    is NO LONGER a filter — S30 audit semantic is "which zone is
    spot currently inside", not "which zone matches my chosen trade
    direction". This makes ict_pattern an observation of zone-touch
    rather than an endorsement of trade direction. Sizing impact is
    nil while MERDIAN_TIER_MULT_DISABLE=1 (S30 default).

    Selection priority:
      1. Tier rank: TIER1 > TIER2 > TIER3 > SKIP (SKIP no longer
         excluded — observed truth needs the zone to be visible
         regardless of sizing).
      2. Recency: most recent detected_at_ts wins (docstring intent;
         prior sort was ASC and returned oldest — fixed).
      3. Tightness: smaller (zone_high - zone_low) wins (most
         specific containing zone is preferred).
    """
    if not active_zones or current_spot is None or current_spot == 0:
        return None

    spot_f = float(current_spot)
    _TIER_RANK = {"TIER1": 0, "TIER2": 1, "TIER3": 2, "SKIP": 3}

    matching = []
    for z in active_zones:
        if z.get("status") != "ACTIVE":
            continue
        try:
            zl = float(z.get("zone_low", 0))
            zh = float(z.get("zone_high", 0))
        except (TypeError, ValueError):
            continue
        if zl <= spot_f <= zh:
            matching.append(z)

    if not matching:
        return None

    def _ts_key(ts_str):
        # ISO-8601 strings sort lex equivalent to chronological for
        # same-zone-character prefixes; we want DESC (newest first).
        # Return a value that sorts ASC by negation: use a tuple of
        # length-and-content negation via reverse-string trick is
        # fragile; simpler — sort with reverse on this key dimension
        # only via two-pass stable sort. Implemented below.
        return ts_str or ""

    # Stable two-pass sort:
    # Pass 1: tightest first (last, least important).
    matching.sort(
        key=lambda z: float(z.get("zone_high", 0)) - float(z.get("zone_low", 0))
    )
    # Pass 2: most recent first.
    matching.sort(key=lambda z: _ts_key(z.get("detected_at_ts", "")), reverse=True)
    # Pass 3: best tier first (most important, last applied → wins).
    matching.sort(key=lambda z: _TIER_RANK.get(z.get("ict_tier"), 99))

    return matching[0]


def enrich_signal_with_ict(
    signal_dict:  dict,
    active_zones: list[dict],
    current_spot: float,
) -> dict:
    """
    TD-S30-NEW-3 fix (Session 31) — observational attachment.

    Enrich an existing signal dict with ICT pattern fields. Called
    from build_trade_signal_local.py after signal action is determined.

    SEMANTIC CHANGE: attachment is now observational (which zone is
    spot inside) rather than directional-action-endorsed. The previous
    early-return on action=DO_NOTHING is removed so gated cycles
    (LONG_GAMMA, NO_FLIP, DTE, power-hour, ENH-55/76/77/88) still
    surface their zone-touch context in ict_pattern. This is the S30
    audit semantic and unblocks per-OB-pattern live-cohort
    re-validation (D.13.5 closure path).

    Adds fields:
      ict_pattern       — pattern type or "NONE"
      ict_tier          — TIER1 | TIER2 | TIER3 | SKIP | NONE
      ict_size_mult     — value from matched zone or 1.0 default
                          (force-1.0 downstream while
                          MERDIAN_TIER_MULT_DISABLE=1)
      ict_mtf_context   — VERY_HIGH | HIGH | MEDIUM | LOW | NONE
    """
    # `action` kept for back-compat callers; no longer used for filtering.
    _ = signal_dict.get("action", "DO_NOTHING")

    best_zone = get_best_active_zone(active_zones, current_spot, _)

    if best_zone is None:
        signal_dict["ict_pattern"]     = "NONE"
        signal_dict["ict_tier"]        = "NONE"
        signal_dict["ict_size_mult"]   = 1.0
        signal_dict["ict_mtf_context"] = "NONE"
    else:
        signal_dict["ict_pattern"]     = best_zone.get("pattern_type", "NONE")
        signal_dict["ict_tier"]        = best_zone.get("ict_tier", "TIER2")
        signal_dict["ict_size_mult"]   = float(best_zone.get("ict_size_mult", 1.0))
        signal_dict["ict_mtf_context"] = best_zone.get("mtf_context", "LOW")

    return signal_dict
