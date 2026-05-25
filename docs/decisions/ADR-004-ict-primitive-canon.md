# ADR-004 — ICT PD-Array Canonical Primitive Layer

**Status:** ACCEPTED (S31-A close 2026-05-20). Amendments A (retest-anchored outcomes primary, formation-anchored retained) and B (Pine v2 canonical implementation) applied.
**Supersedes:** TD-049, TD-051 (canon deviations are now subsumed into this rewrite)
**Successor work:** S31-B (detector implementation + Pine v2 + backfill), S31-C (edge view + consumer rewire)
**Operator sign-off:** received 2026-05-20 covering all 15 primitives and the §11 parameter block

---

## 1. Context

MERDIAN's current ICT detection layer was assembled over Sessions 5-15 across multiple writers (`build_ict_htf_zones.py`, `detect_ict_patterns.py`, intraday helpers) with non-uniform interpretations of canonical ICT primitives. The S31 diagnostic established three load-bearing defects:

- **D-OB definition is non-canonical.** `detect_daily_zones` tags the prior day's own body as the order block whenever the day moved ≥0.4%. Canon requires the OB to be the *opposing-direction* candle preceding a displacement that creates an FVG. Result: ~5x over-detection at D timeframe.
- **PDH/PDL conflate level with zone.** PDH/PDL are *price levels* by canon. Production adds a ±10/±20 buffer treating them as zones. The buffer was a rendering convenience that propagated into detection logic and downstream consumers.
- **Detection, statistics, and rendering are entangled.** "WR 88%" labels are baked into the Pine overlay's source-time render via constants matched to Compendium experiments. The label is fixed at write time; the underlying number is from a non-canonical cohort. When the cohort changes, the label is stale.

Compounding context: every load-bearing experiment in the Compendium (Exp 2, 5, 10c, 11, 15, 17, 18, 23, 34, 35, 36, 40, 41) queries `hist_ict_htf_zones`, which was backfilled (Session 15) using the same broken detectors. The "edges" we promoted to production rules (ENH-76 88.2%, ENH-77 73.7%, ENH-78 90.9%, ENH-88 +12.8pp) are measured against this substrate. They are statistically valid statements about *what the broken detector tagged*, but the labels (BULL_OB, BEAR_OB, etc.) do not refer to canonical ICT primitives.

This ADR specifies the canonical definition of every PD-array primitive MERDIAN will detect. S31-B implements detectors against this spec. S31-C rebuilds the edge measurement view and rewires consumers. The Compendium is not preserved; old WR numbers are explicitly marked SUPERSEDED-BY-CANONICAL.

---

## 2. Design principles

Three rules govern the entire primitive layer. They are non-negotiable.

**Detection is pure observation.** A detector takes bars in and emits primitives out. It does not know about tier, WR, expectancy, confidence, gates, or trade outcomes. Two callers asking the same detector the same question on the same bars get the same answer, today and in six months.

**Statistics derive from primitives, not from detection.** WR, expectancy, and edge are computed by queries against a separate `ict_primitive_outcomes` table joined to `ict_primitives`. The rendering layer pulls these statistics at display time, not at write time. When the cohort changes, the displayed statistics change automatically.

**Canon over convenience.** Where canon and existing production logic conflict, canon wins. Where canon is ambiguous, this ADR picks one interpretation explicitly and names the choice. Deviations are forbidden in the detector layer; any operational adjustment lives in the consumer layer (e.g., visualisation buffers in Pine rendering, not in zone bounds).

---

## 3. Primitive taxonomy

Three categories. Each primitive belongs to exactly one.

| Category | Primitives |
|---|---|
| **Zone primitives** (have zone_low, zone_high, render as boxes) | Order Block, Fair Value Gap, Breaker Block, Mitigation Block, OTE, Premium/Discount Array |
| **Level primitives** (have a single price level, render as lines) | PDH, PDL, PWH, PWL, PMH, PML, Equal Highs, Equal Lows, BSL, SSL |
| **Event primitives** (have a timestamp, no zone or level, render as markers) | Sweep / Stop Run, Displacement, Inducement |
| **Context primitives** (have a state label, no chart render) | Power of Three (PO3), Order Flow Continuity, Premium/Discount State |

---

## 4. Common fields across all primitives

Every detected primitive carries these fields in the `ict_primitives` table:

- `id` — UUID
- `symbol` — NIFTY | SENSEX
- `timeframe` — W | D | H | M5 | M1
- `primitive_type` — see sections below for the enumeration
- `direction` — BULL | BEAR | NONE (NONE for direction-agnostic primitives like PDH/PDL)
- `created_at` — when the writer detected it (UTC)
- `source_bar_ts` — the timestamp of the canonical defining bar (UTC, the bar whose properties define the primitive)
- `valid_from` — when the primitive becomes consumable (typically `source_bar_ts` + 1 TF)
- `valid_to` — NULL by default; set only on breach or explicit time-based expiry per primitive section
- `zone_low`, `zone_high` — for zone primitives; NULL for others
- `level` — for level primitives; NULL for others
- `status` — ACTIVE | MITIGATED | BREACHED | EXPIRED
- `breach_ts` — timestamp of breach if status != ACTIVE
- `displacement_pct` — for primitives that require displacement (OB, FVG, Breaker, Mitigation); the displacement magnitude that confirmed the primitive
- `metadata` — JSONB for primitive-specific extra context (e.g., associated FVG ID for OBs, sweep target level for Breakers)

Common breach rule template: a primitive is BREACHED when spot **closes** beyond the invalidation boundary on the timeframe of the primitive. Wicks alone do not breach. Closing-bar timeframe matches the primitive's timeframe (e.g., a D-OB is breached only by a daily close beyond bounds; intraday wicks do not breach a daily primitive).

**Outcome anchoring (Amendment A, 2026-05-20).** Per ICT canon, primitives are tradable on retest: price returns to the zone (or level) and rejects from it. Outcomes in `ict_primitive_outcomes` are therefore anchored at *first retest* by default. The retest cohort is the canonical tradable population. Formation-anchored outcomes (forward returns from the bar that confirmed the primitive) are retained in the same table for backward comparison with pre-canon experiments but are explicitly marked as "non-discretionary cohort" in any edge-view output. The full schema with both anchor sets is specified in §10.

---

## 5. Zone primitives

### 5.1 Order Block (OB)

**Canon.** A BULL_OB is the last DOWN-close candle immediately preceding a bullish displacement that creates a bullish FVG. A BEAR_OB is the last UP-close candle immediately preceding a bearish displacement that creates a bearish FVG. The OB is *opposing direction* to the impulse it precedes.

**Detection algorithm:**
1. For each bar `i`, check whether a displacement occurred at bar `i+1` or within bars `[i+1, i+N]` where N is the displacement window (canonically N=3).
2. A displacement is confirmed only if it creates an FVG (see §5.2) within the same N-bar window.
3. If displacement is bullish and bar `i` is a down-close candle (close < open), bar `i` is a candidate BULL_OB.
4. If displacement is bearish and bar `i` is an up-close candle (close > open), bar `i` is a candidate BEAR_OB.
5. If multiple candidates exist (e.g., two down-close candles before the impulse), the canonical OB is the **most recent** one (closest to the impulse start).
6. The candidate becomes a confirmed OB once the displacement bar closes and the FVG is verified.

**Validity conditions:**
- Opposing-direction candle is not a doji: `abs(close - open) / open >= OB_MIN_BODY_PCT` where `OB_MIN_BODY_PCT` is per-TF (see §11).
- A canonical OB requires a *confirmed FVG* in the impulse leg. If no FVG forms, the candle is not an OB regardless of subsequent move.
- Multiple OBs in a chain (sequential opposing-direction candles before impulse): take the candle closest to the impulse start.

**Zone bounds:**
- `zone_low = min(open, close)` of the OB candle (body low)
- `zone_high = max(open, close)` of the OB candle (body high)
- "Wick-extended OB" (using high/low instead of body) is *not* canonical for our purposes; if needed for rendering it lives in metadata as `wick_low`/`wick_high`.

**Breach rule:**
- BULL_OB breached when a bar of the OB's timeframe closes with `close < zone_low`.
- BEAR_OB breached when a bar of the OB's timeframe closes with `close > zone_high`.
- Mitigation (price returns to and reacts at the zone, then moves on) does not breach; it transitions status to MITIGATED.

**Per-timeframe parameters:**

| TF | `OB_MIN_BODY_PCT` | Displacement window | `DISPLACEMENT_MIN_PCT` |
|---|---|---|---|
| W | 0.5% | 3 weeks | 2.0% |
| D | 0.3% | 3 days | 1.0% |
| H | 0.2% | 3 hours | 0.4% |
| M5 | 0.1% | 6 bars (30min) | 0.2% |

**Common deviations to avoid:**
- The current production `detect_daily_zones` uses prior-day-self with no opposing-direction check. Canon requires the opposing-direction lookback.
- Some retail implementations use "any large candle followed by move" without the FVG requirement. Canon requires FVG.

---

### 5.2 Fair Value Gap (FVG)

**Canon.** A three-bar imbalance where the wick of bar `i-1` and the wick of bar `i+1` do not overlap, creating an unfilled price gap. BULL_FVG: gap is between bar[i-1].high and bar[i+1].low (price gapped up). BEAR_FVG: gap is between bar[i+1].high and bar[i-1].low (price gapped down).

**Detection algorithm:**
1. For each three-bar window `(i-1, i, i+1)`:
2. If `bar[i-1].high < bar[i+1].low`: candidate BULL_FVG with zone `[bar[i-1].high, bar[i+1].low]`.
3. If `bar[i-1].low > bar[i+1].high`: candidate BEAR_FVG with zone `[bar[i+1].high, bar[i-1].low]`.
4. Bar `i` is the displacement bar (the one that caused the gap by closing strongly in the FVG direction).
5. Compute `gap_pct = (zone_high - zone_low) / reference_price * 100` where `reference_price = bar[i].open`.
6. FVG confirmed if `gap_pct >= FVG_MIN_PCT` for the timeframe.

**Validity conditions:**
- Displacement bar (bar `i`) must close in the direction of the FVG (bullish close for BULL_FVG, bearish close for BEAR_FVG).
- Gap size meets per-TF threshold (see §11).

**Zone bounds:**
- BULL_FVG: `zone_low = bar[i-1].high`, `zone_high = bar[i+1].low`
- BEAR_FVG: `zone_low = bar[i+1].high`, `zone_high = bar[i-1].low`

**Breach rule:**
- An FVG is *filled* when price retraces through the zone — wicking into it counts as partial fill (status: PARTIALLY_FILLED, not breached).
- An FVG is *breached* (and status set to BREACHED) when a bar of the FVG's timeframe closes with `close < zone_low` (BULL_FVG) or `close > zone_high` (BEAR_FVG) — i.e., closes through and beyond.
- Note: FVGs are commonly considered "consumed" once mitigated; canon does not treat single fill as breach. We track full close-beyond as breach.

**Per-timeframe parameters:**

| TF | `FVG_MIN_PCT` |
|---|---|
| W | 0.8% |
| D | 0.4% |
| H | 0.2% |
| M5 | 0.08% |

---

### 5.3 Breaker Block

**Canon.** A failed OB. A BULL_OB that gets breached (price closes through and beyond on its timeframe) becomes a BEAR Breaker — when price retraces back up to the failed OB zone, that zone now acts as resistance. Same in reverse for BEAR_OB → BULL Breaker.

**Detection algorithm:**
1. Monitor all ACTIVE OBs.
2. When an OB's breach rule fires, change its status to BREACHED *and* create a new Breaker primitive of opposite direction:
   - BULL_OB breached → BEAR_BREAKER created with same `zone_low`/`zone_high`.
   - BEAR_OB breached → BULL_BREAKER created with same `zone_low`/`zone_high`.
3. The new Breaker's `source_bar_ts` is the breach bar; `metadata.parent_ob_id` references the original OB.

**Validity conditions:**
- Parent OB must have been ACTIVE before breach (not already BREAKER or MITIGATED).
- Breaker validity window: typically the same timeframe as the parent OB.

**Zone bounds:** inherited from parent OB.

**Breach rule:**
- BULL_BREAKER (was BEAR_OB): breached when close < zone_low after creation.
- BEAR_BREAKER (was BULL_OB): breached when close > zone_high after creation.
- These are stricter than the parent OB because the structural shift has already happened once; a second breach indicates the breaker thesis itself has failed.

**Notes:**
- Breakers are second-derivative primitives. They depend on OB detection being correct.
- A common ICT teaching: the first retest of a breaker is often the highest-probability entry zone.

---

### 5.4 Mitigation Block

**Canon.** When price approaches an OB but does not fully tag it (wicks toward without closing inside), then continues in the impulse direction, the bar that came closest to the OB without entering it becomes a Mitigation Block — a new zone derived from that wick attempt.

**Detection algorithm:**
1. For each ACTIVE OB, monitor subsequent bars on the same timeframe.
2. If a bar's wick comes within `MITIGATION_PROXIMITY_PCT` of the OB zone but the bar closes back in the impulse direction without entering the OB:
   - That bar becomes a Mitigation Block of the same direction as the OB.
   - Zone bounds: the wick-side body of the mitigation bar.
3. The mitigation block becomes the new "lower-risk" zone for the same thesis as the parent OB.

**Validity conditions:**
- Bar must come within proximity threshold but not touch the OB.
- Bar's close must be in the impulse direction (the direction the OB supports).

**Zone bounds:**
- BULL Mitigation: `zone_low = bar.low`, `zone_high = min(bar.open, bar.close)`
- BEAR Mitigation: `zone_low = max(bar.open, bar.close)`, `zone_high = bar.high`

**Breach rule:** same as OB but on the mitigation block's bounds.

**Notes:**
- Mitigation blocks are less canonical than OBs/FVGs; some ICT students do not detect them separately. Including in the layer because they refine entry zones.
- Per-TF `MITIGATION_PROXIMITY_PCT`: W = 1.0%, D = 0.3%, H = 0.15%, M5 = 0.08%.

---

### 5.5 Optimal Trade Entry (OTE)

**Canon.** A Fibonacci-derived retracement zone within a directional leg, conventionally the 62%–79% retracement of the swing. Bullish leg's OTE is on retracement back down from the swing high; bearish leg's OTE on retracement back up from swing low.

**Detection algorithm:**
1. Identify a directional swing leg with a confirmed start (`leg_start_bar`) and end (`leg_end_bar`).
2. Swing leg must have `leg_magnitude_pct >= OTE_MIN_LEG_PCT` to qualify.
3. Compute Fibonacci levels: `fib_62 = end - 0.62 * (end - start)`, `fib_79 = end - 0.79 * (end - start)`.
4. OTE zone: `zone_low = min(fib_62, fib_79)`, `zone_high = max(fib_62, fib_79)`.

**Validity conditions:**
- Leg must be impulsive (single direction, no opposing displacement during the leg) — operationally, no FVG in the opposite direction during the leg.
- Leg endpoints are pivot highs/lows on the timeframe.

**Per-timeframe parameters:**

| TF | `OTE_MIN_LEG_PCT` |
|---|---|
| W | 4.0% |
| D | 1.5% |
| H | 0.6% |
| M5 | 0.25% |

**Breach rule:**
- BULL OTE (leg up, retracement down): breached when close < `leg_start` (price returns past swing origin, leg invalidated).
- BEAR OTE: breached when close > `leg_start`.

**Notes:**
- OTE detection requires swing-pivot identification, which has its own canon (fractal-5 / fractal-3). This ADR uses fractal-3 (one bar each side higher/lower) for M5/H, fractal-5 for D/W.

---

### 5.6 Premium / Discount Array

**Canon.** Half-of-range pricing. Within a defined range (`range_low`, `range_high`), the midpoint splits the range into:
- Premium half: `[midpoint, range_high]` — selling zone in bearish bias
- Discount half: `[range_low, midpoint]` — buying zone in bullish bias

**Detection algorithm:**
1. Define the operative range. Canonically the most recent significant swing (swing high to swing low or vice versa) on the timeframe.
2. Range source per TF: W uses last completed major weekly swing; D uses most recent W swing or prior-day range; H uses last completed daily range; M5 uses today's session range so far.
3. Compute `midpoint = (range_high + range_low) / 2`.
4. Emit two zones: PREMIUM `[midpoint, range_high]` and DISCOUNT `[range_low, midpoint]`.

**Validity conditions:**
- Range must have a clear high and low (both pivots identified).
- Range magnitude meets per-TF threshold.

**Breach rule:**
- Premium/Discount zones reset when the originating range is broken: i.e., when a close exceeds `range_high + tolerance` or falls below `range_low - tolerance`. New range derives a new Premium/Discount split.

**Notes:**
- Premium/Discount is more a *context* (which half is price in) than a tradable zone. The actual trade derives from confluence with OB/FVG inside the appropriate half.
- This primitive is also exposed as a context primitive in §8.3 for the directional state.

---

## 6. Level primitives

### 6.1 Prior Period Highs and Lows (PDH, PDL, PWH, PWL, PMH, PML)

**Canon.** Liquidity levels at prior session high/low. PDH = Prior Day High, PDL = Prior Day Low, PWH = Prior Week High, PWL = Prior Week Low, PMH = Prior Month High, PML = Prior Month Low. These are *price levels*, not zones.

**Detection algorithm:**
1. At session open of each new TF period, look back exactly one period and record the high and low.
2. PDH: high of prior trading day's RTH bars (09:15-15:30 IST).
3. PDL: low of prior trading day's RTH bars.
4. PWH/PWL: high/low of prior week (Monday-Friday).
5. PMH/PML: high/low of prior calendar month.

**Level:** the price itself. No `zone_low`/`zone_high` (these stay NULL).

**Validity:**
- A prior-period level becomes ACTIVE at the new period's open.
- It remains ACTIVE until swept.

**Breach rule (canonical: "swept", not "breached"):**
- PDH is *swept* when intraday price wicks above PDH and then closes back below it (a stop-run). Status: SWEPT.
- PDH is *taken out* (status: TAKEN_OUT) when a bar closes above PDH (not just wicks).
- Same logic in reverse for PDL.
- Distinction matters: sweeps are tradable signals (counter-trend entry post-sweep); takeouts are continuation signals.

**Notes:**
- TD-051 deviation: production wraps PDH/PDL in a ±20 (W) / ±10 (D) point buffer to render as a zone. **Canon: PDH/PDL are levels, period.** Any visual zone is a rendering decision in Pine, not a detection decision.
- The "sweep" event itself is a separate primitive (§7.1) that carries the level it swept as metadata.

---

### 6.2 Equal Highs / Equal Lows

**Canon.** Two or more swing highs (or lows) at approximately the same price, forming engineered liquidity. Once price sweeps the equal-highs/lows level, the move is typically aggressive.

**Detection algorithm:**
1. Identify swing pivots on the timeframe (fractal-3 or fractal-5 per TF — see §5.5).
2. For pairs of consecutive same-direction pivots (high1, high2), compute `delta_pct = abs(high2 - high1) / high1 * 100`.
3. If `delta_pct <= EQUAL_TOLERANCE_PCT`, emit an Equal Highs primitive at level `max(high1, high2)` with metadata listing both source bars.
4. Same logic for Equal Lows.

**Level:** the level value (typically the higher of the equal highs, or the lower of the equal lows — the actual liquidity pool sits at this exact price).

**Per-timeframe parameters:**

| TF | `EQUAL_TOLERANCE_PCT` |
|---|---|
| W | 0.15% |
| D | 0.08% |
| H | 0.04% |
| M5 | 0.02% |

**Breach rule:** SWEPT when wicked-through-and-closed-back; TAKEN_OUT when bar closes through.

---

### 6.3 BSL / SSL (Buy-Side / Sell-Side Liquidity)

**Canon.** BSL = liquidity sitting above the most recent swing high (stops of shorts, breakout buyers). SSL = liquidity sitting below the most recent swing low. ICT treats these as targets that price *gravitates toward*.

**Detection algorithm:**
1. Identify the most recent swing high above current price → that level is BSL.
2. Identify the most recent swing low below current price → that level is SSL.
3. Update on every new pivot.

**Level:** the swing pivot price itself.

**Notes:**
- BSL/SSL is essentially "the nearest PDH-equivalent above" and "the nearest PDL-equivalent below" but generalized to any timeframe's pivots.
- A canonical signal: price approaches BSL, sweeps it, reverses — that's a stop-hunt setup.

---

## 7. Event primitives

### 7.1 Sweep / Stop Run

**Canon.** A wick beyond a known liquidity level (PDH/PDL/PWH/PWL/Equal Highs/Lows/BSL/SSL) where the bar closes back inside the prior range. Indicates institutional stop-hunting.

**Detection algorithm:**
1. For each bar, check whether bar.high exceeds any known BSL/PDH/PWH/Equal-Highs level.
2. Check whether bar.close is back below that level.
3. If both: emit a SWEEP_HIGH event with metadata `{swept_level_type, swept_level_price, sweep_depth_pct, sweep_bar_ts}`.
4. Same logic for SWEEP_LOW with sell-side levels.

**Event field:** `event_ts = bar.ts`. No zone or level fields.

**Validity conditions:**
- Sweep must exceed level by at least `SWEEP_MIN_DEPTH_PCT` (per TF, see below).
- Close must return below (sweep high) or above (sweep low) the level.

**Per-timeframe parameters:**

| TF | `SWEEP_MIN_DEPTH_PCT` |
|---|---|
| W | 0.2% |
| D | 0.1% |
| H | 0.05% |
| M5 | 0.025% |

**Notes:**
- The swept level (in metadata) gets its status updated to SWEPT.
- Sweep events are the most direct tradable ICT signal — they often precede the move ICT students try to capture.

---

### 7.2 Displacement

**Canon.** A strong directional move that creates an FVG and resets the structural narrative. Displacement is what *makes* an OB an OB; without displacement, a preceding candle is just a candle.

**Detection algorithm:**
1. Compute `bar_move_pct = (close - open) / open * 100` for each bar.
2. If `abs(bar_move_pct) >= DISPLACEMENT_MIN_PCT` for the timeframe (see §5.1 params): candidate displacement.
3. Confirm by checking whether the bar (or the 3-bar window centered on it) created an FVG.
4. If yes: emit DISPLACEMENT_UP (bull move) or DISPLACEMENT_DOWN.

**Event field:** `event_ts = bar.ts`; metadata includes `displacement_pct`, `created_fvg_id` (if confirmed).

**Notes:**
- Displacement is the *cause* of OB validity. The OB and FVG primitives reference back to the displacement event via metadata.
- Detecting displacement explicitly (rather than only inferring it via OB/FVG presence) gives us a clean event stream for the "what triggered the structural shift" question.

---

### 7.3 Inducement

**Canon.** A counter-trend retracement that "induces" liquidity (traders enter the counter direction, placing stops) before the larger move resumes. Often the move that creates the OB.

**Detection algorithm:**
1. Within a confirmed trend leg (series of higher highs / lower lows on the timeframe):
2. Detect the most recent counter-trend pullback that didn't break structure.
3. If the pullback magnitude exceeds `INDUCEMENT_MIN_PCT` and stays within the prior swing's range: emit INDUCEMENT event with direction (which way the resumption is expected).

**Event field:** `event_ts = pullback_low_bar_ts` (for bull inducement) or `pullback_high_bar_ts`.

**Notes:**
- Inducement is observational; ICT mentorship treats it as context for OB validity rather than a tradable primitive on its own.
- Including it because the metadata helps reason about why an OB formed where it did.

---

## 8. Context primitives

Context primitives don't render on chart. They emit a state label per (symbol, timeframe, time-window) that consumers query.

### 8.1 Power of Three (PO3)

**Canon.** ICT's session model: accumulation → manipulation → distribution. Operationally for intraday sessions:
- **Accumulation phase:** open ± first 30-60 minutes, range-bound
- **Manipulation phase:** sweep of accumulation high or low
- **Distribution phase:** sustained move in the opposite direction of the manipulation sweep

PO3 bias for the session:
- PO3_BEARISH: manipulation swept the accumulation HIGH (took out buy stops), distribution is DOWN
- PO3_BULLISH: manipulation swept the accumulation LOW (took out sell stops), distribution is UP
- PO3_NONE: no clear sweep + reversal pattern detected by 10:05 IST or pattern aborted

**Detection algorithm (current production logic is correct; preserved):**
1. At 10:05 IST, evaluate accumulation range from 09:15-10:00.
2. Check whether 09:15-10:05 wicked beyond accumulation_high (PO3_BEARISH candidate) or below accumulation_low (PO3_BULLISH candidate).
3. Check whether price closed back inside accumulation range after the sweep.
4. Emit PO3 label.

**State value:** `po3_session_bias ∈ {PO3_BULLISH, PO3_BEARISH, PO3_NONE}` per (symbol, trade_date).

**Notes:** The existing `detect_po3_session_bias.py` already implements this correctly. Reuse, do not rewrite.

---

### 8.2 Order Flow Continuity (OFC)

**Canon.** Higher-timeframe directional state: BOS (Break of Structure) intact vs broken. A BULLISH trend has a series of higher swing highs and higher swing lows; broken when a swing low gets taken out by a daily close.

**Detection algorithm:**
1. Identify swing pivots per timeframe.
2. Track the sequence: each new swing high either confirms the trend (higher than prior swing high) or signals weakness (lower).
3. Emit OFC state per (symbol, timeframe, day):
   - BULLISH_INTACT: most recent swing low > prior swing low AND no daily close below the most recent swing low
   - BEARISH_INTACT: symmetric
   - BULLISH_BROKEN: a daily close below the most recent swing low after a bullish sequence
   - BEARISH_BROKEN: symmetric
   - RANGING: no clean swing sequence in either direction

**State value:** `ofc_state` per (symbol, timeframe, day).

---

### 8.3 Premium/Discount State

**Canon.** Where is current price within the operative range, half-by-half.

**Detection algorithm:**
1. Compute the operative range per §5.6.
2. Emit `pd_state ∈ {PREMIUM, DISCOUNT, MIDPOINT_BAND}` based on current price vs range midpoint.

**Notes:** Companion to the Premium/Discount zone primitive (§5.6). Zone is rendered; state is queried.

---

## 9. Detector module structure (S31-B implementation handoff)

A single new module: `core/ict_primitives.py`. One function per primitive per timeframe is overkill; instead, parameterized detectors:

```
detect_order_blocks(bars: list[Bar], tf: Timeframe) -> list[Primitive]
detect_fvgs(bars: list[Bar], tf: Timeframe) -> list[Primitive]
detect_breakers(existing_obs: list[Primitive], bars: list[Bar], tf: Timeframe) -> list[Primitive]
detect_mitigation_blocks(existing_obs, bars, tf) -> list[Primitive]
detect_ote(bars, tf) -> list[Primitive]
detect_premium_discount_zones(bars, tf) -> list[Primitive]
detect_prior_period_levels(bars, period: 'D'|'W'|'M') -> list[Primitive]
detect_equal_pivots(bars, tf) -> list[Primitive]
detect_bsl_ssl(bars, tf, current_price) -> list[Primitive]
detect_sweeps(bars, known_levels: list[Primitive], tf) -> list[Event]
detect_displacements(bars, tf) -> list[Event]
detect_inducements(bars, tf) -> list[Event]
detect_po3(session_bars, accumulation_window) -> PO3State
detect_ofc(swing_pivots, tf) -> OFCState
```

Each detector is pure (no DB, no I/O, no env reads). Bars come in pre-validated; primitives go out as dataclasses. The writer (`build_ict_primitives.py`) is the only file that touches Supabase — it iterates over symbols/timeframes, calls detectors, batches upserts.

The legacy `build_ict_htf_zones.py` is preserved untouched during S31-B and S31-C. Migration cutover happens at the end of S31-C: consumers are pointed to `ict_primitives`; the old writer is retired only after 4+ weeks of operator confirmation that the primitives layer is paying.

---

## 10. Schema decisions

**New tables (S31-B writes them):**

```sql
CREATE TABLE ict_primitives (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol          TEXT NOT NULL,
    timeframe       TEXT NOT NULL CHECK (timeframe IN ('W','D','H','M5','M1')),
    primitive_type  TEXT NOT NULL,  -- enum: see §3 taxonomy
    direction       TEXT CHECK (direction IN ('BULL','BEAR','NONE')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_bar_ts   TIMESTAMPTZ NOT NULL,
    valid_from      TIMESTAMPTZ NOT NULL,
    valid_to        TIMESTAMPTZ,
    zone_low        NUMERIC,
    zone_high       NUMERIC,
    level           NUMERIC,
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE','MITIGATED','BREACHED','SWEPT','TAKEN_OUT','EXPIRED')),
    breach_ts       TIMESTAMPTZ,
    displacement_pct NUMERIC,
    metadata        JSONB,
    UNIQUE (symbol, timeframe, primitive_type, source_bar_ts, COALESCE(zone_low, level), COALESCE(zone_high, level))
);
CREATE INDEX idx_ict_primitives_active ON ict_primitives (symbol, timeframe, status) WHERE status = 'ACTIVE';
CREATE INDEX idx_ict_primitives_lookup ON ict_primitives (symbol, source_bar_ts, primitive_type);

CREATE TABLE ict_primitive_outcomes (
    primitive_id          UUID REFERENCES ict_primitives(id) ON DELETE CASCADE,
    -- Formation-anchored (retained for backward comparison with pre-canon experiments)
    forward_5m_pct        NUMERIC,
    forward_15m_pct       NUMERIC,
    forward_30m_pct       NUMERIC,
    forward_1h_pct        NUMERIC,
    forward_eod_pct       NUMERIC,
    -- Retest-anchored (PRIMARY — canonical tradable cohort per ICT)
    retest_status         TEXT NOT NULL DEFAULT 'PENDING'
                          CHECK (retest_status IN ('PENDING','RETESTED','NEVER_RETESTED','BREACHED_BEFORE_RETEST')),
    first_retest_ts       TIMESTAMPTZ,
    retest_depth_pct      NUMERIC,  -- how far into the zone did price penetrate (0.0 = touched edge, 1.0 = fully traversed)
    retest_fwd_5m_pct     NUMERIC,
    retest_fwd_15m_pct    NUMERIC,
    retest_fwd_30m_pct    NUMERIC,
    retest_fwd_1h_pct     NUMERIC,
    retest_fwd_eod_pct    NUMERIC,
    -- Shared
    respected             BOOLEAN,  -- did price react at the zone (rejection candle within zone on first retest)
    mitigated_at          TIMESTAMPTZ,
    breach_at             TIMESTAMPTZ,
    option_pnl_30m        NUMERIC,  -- ATM CE/PE P&L anchored at retest
    option_pnl_eod        NUMERIC,
    computed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (primitive_id)
);
```

**Retest definition (applies to all zone and level primitives in §5-§6):**
- **Zone primitive (OB, FVG, Breaker, Mitigation, OTE, Premium/Discount zone):** price re-enters `[zone_low, zone_high]` for the first time after first exiting the zone post-formation. `retest_depth_pct = (zone_high - retest_low_touched) / (zone_high - zone_low)` for BULL primitives (0.0 = wicked the upper edge only; 1.0 = fully traversed to lower edge); symmetric for BEAR.
- **Level primitive (PDH, PDL, PWH, PWL, PMH, PML, Equal Highs/Lows, BSL, SSL):** price returns to within `RETEST_TOLERANCE_PCT` of `level` after first deviating by more than that tolerance. Per-TF values: W = 0.15%, D = 0.08%, H = 0.04%, M5 = 0.02% (same as `EQUAL_TOLERANCE_PCT` table in §11).

**Retest status transitions:**
- `PENDING` (default at primitive creation) → `RETESTED` once a retest occurs while the primitive is still ACTIVE.
- `PENDING` → `BREACHED_BEFORE_RETEST` if the primitive's invalidation boundary is closed-through before any retest.
- After N TF-bars without retest (per-TF: W=8 weeks, D=20 days, H=20 hours, M5=20 bars), `PENDING` transitions to `NEVER_RETESTED`. The N values are operationally chosen so that genuinely live primitives don't time out; a NEVER_RETESTED primitive is still ACTIVE in the primitive table — only its outcome anchor is closed.

**Event primitives (§7) have no retest concept.** Outcomes for Sweep, Displacement, Inducement are anchored at `event_ts` and use only the formation-anchored columns.

**Edge view (S31-C builds this):** `v_ict_primitive_edge` joins the two tables and aggregates by configurable grouping (primitive_type × timeframe × context filters), exposing WR + expectancy + N + Wilson 95% CI per cell. **Default cohort: retest-anchored** (the canonical tradable population per ICT). Formation-anchored outcomes are queryable as a secondary column set, labeled "non-discretionary cohort" in any output to prevent confusion. OOS train/test split is parameterized.

**Legacy tables (untouched until cutover):** `ict_zones`, `ict_htf_zones`, `hist_ict_htf_zones`. These continue to be written by old code paths during the transition.

---

## 11. Parameter summary table

All per-timeframe constants in one place. S31-B implementations must reference these symbolically (e.g., `OB_PARAMS[tf]['min_body_pct']`), not hardcode.

| Parameter | W | D | H | M5 |
|---|---|---|---|---|
| `OB_MIN_BODY_PCT` | 0.5 | 0.3 | 0.2 | 0.1 |
| `DISPLACEMENT_MIN_PCT` | 2.0 | 1.0 | 0.4 | 0.2 |
| `DISPLACEMENT_WINDOW_BARS` | 3 | 3 | 3 | 6 |
| `FVG_MIN_PCT` | 0.8 | 0.4 | 0.2 | 0.08 |
| `MITIGATION_PROXIMITY_PCT` | 1.0 | 0.3 | 0.15 | 0.08 |
| `OTE_MIN_LEG_PCT` | 4.0 | 1.5 | 0.6 | 0.25 |
| `EQUAL_TOLERANCE_PCT` | 0.15 | 0.08 | 0.04 | 0.02 |
| `SWEEP_MIN_DEPTH_PCT` | 0.2 | 0.1 | 0.05 | 0.025 |
| `INDUCEMENT_MIN_PCT` | 0.8 | 0.3 | 0.15 | 0.08 |
| `FRACTAL_DEPTH` (swing pivots) | 5 | 5 | 3 | 3 |

These values are first-cut canonical estimates. After S31-B detects against a year of vendor data, we will get histogram distributions per primitive count by timeframe; if counts are obviously wrong (e.g., D-OB still firing >1/week), thresholds get one round of recalibration in S31-C before edge measurement begins.

---

## 12. Consequences

**Immediate:**
- `build_ict_htf_zones.py` continues running unchanged during S31-B. Live signal not affected by detector work.
- ENH-76, ENH-77, ENH-78, ENH-88 stay env-disabled (already so per S30). Re-promotion only from `v_ict_primitive_edge` cells with N≥30 + OOS pass.
- Pine overlay renders unchanged until S31-C cutover. Operator continues trading off the legacy overlay (or off chart natively) during S31-B.

**Downstream:**
- Compendium WR labels (BULL_OB 86%, BEAR_OB 88%, etc.) become historical artifacts. The Compendium is preserved as a record of what was measured pre-canon, marked SUPERSEDED-BY-CANONICAL.
- Old `hist_ict_htf_zones`-dependent experiments (Exp 15, 17, 18, 23, 34, 35, 36, 39, 40, 41) are re-runnable against `ict_primitives` once backfill completes in S31-B.
- TD-049 and TD-051 close on this ADR.

**Risks:**
- Canonical detection may produce sparser zone counts than the broken detector. Pine overlay will look emptier. This is the intended outcome; operator must accept it.
- First-cut parameter values may need adjustment. Building one round of recalibration into S31-C explicitly.
- The mitigation, inducement, and breaker primitives are less universally agreed-upon in ICT pedagogy. If a primitive section produces results that don't survive sanity-check, that primitive is dropped before S31-C.

**Non-risks:**
- Live signal builder (`build_trade_signal_local.py`) is not modified in this ADR. S31-C will rewire it; until then it reads the legacy tables.
- Existing Pine overlays in TradingView continue to work — they reference the legacy `merdian_ict_htf_zones.pine` file which generates from `ict_htf_zones`. Operator's chart is not disrupted.

---

## 13. S31-B and S31-C session boundaries

**S31-B (next session) deliverables:**
- `core/ict_primitives.py` implementing all detectors specified in §5-§8
- `build_ict_primitives.py` writer
- `ict_primitives` + `ict_primitive_outcomes` tables created in Supabase
- Backfill: detect + outcome compute over the full vendor window (2025-04-01 → 2026-05-19) for both symbols; outcomes table populated with both formation-anchored and retest-anchored columns
- `MERDIAN_ICT_Primitives_canonical.pine` — client-side Pine v6 implementation of all primitives specified in §5-§7 (excluding §8 context primitives, which depend on persisted backend state and stay backend-only). Input groups per primitive matching the per-TF parameter table in §11. Toggleable visibility per primitive type, configurable colors, configurable timeframe per-primitive overrides where the primitive supports MTF rendering. Validates against `core/ict_primitives.py` output on overlapping chart windows; mismatches treated as bugs in whichever side disagrees with canon.
- Sanity-check counts per primitive × TF against expectations in this ADR; flag deviations for discussion before parameter recalibration

**S31-C deliverables:**
- `v_ict_primitive_edge` SQL view with OOS split
- Pine overlay generator (`generate_pine_overlay_v2.py`) reads `ict_primitives` and pulls WR live from the edge view
- `build_trade_signal_local.py` rewired to read `ict_primitives` instead of `ict_zones`/`ict_htf_zones`
- ENH-76/77/78/88 re-derivation attempted from edge view; promotion gate enforced (N≥30, OOS survival)
- Legacy `build_ict_htf_zones.py` marked deprecated but kept running for 4 weeks post-cutover
- ADR-004 status changed from PROPOSED to ACCEPTED

---

## 14. Operator sign-off

Per-primitive review checkbox. Operator signs each before S31-B implements that primitive. Sign-off can be partial (e.g., approve OB + FVG, defer Mitigation Block to a later phase).

| Primitive | §  | Operator sign-off |
|---|---|---|
| Order Block | 5.1 | [ ] |
| Fair Value Gap | 5.2 | [ ] |
| Breaker Block | 5.3 | [ ] |
| Mitigation Block | 5.4 | [ ] |
| Optimal Trade Entry | 5.5 | [ ] |
| Premium/Discount Array | 5.6 | [ ] |
| Prior Period Levels | 6.1 | [ ] |
| Equal Highs/Lows | 6.2 | [ ] |
| BSL/SSL | 6.3 | [ ] |
| Sweep / Stop Run | 7.1 | [ ] |
| Displacement | 7.2 | [ ] |
| Inducement | 7.3 | [ ] |
| Power of Three (PO3) | 8.1 | [ ] |
| Order Flow Continuity | 8.2 | [ ] |
| Premium/Discount State | 8.3 | [ ] |

Parameters in §11 also require sign-off as a block.

---

**End of ADR-004.**
