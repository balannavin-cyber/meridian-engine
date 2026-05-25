# ADR-012 — Spot-anchored stop-loss doctrine for ICT retest entries

| Field | Value |
|---|---|
| Status | Accepted (doctrine — empirical n=7, validation cohort pending TD-S34-NEW-4 closure) |
| Date decided | 2026-05-24 |
| Date documented | 2026-05-24 |
| Session | Session 34 |
| Supersedes | (none — first ADR on stop-loss anchoring; supersedes informal Compendium-era 30%+ wide premium SL as the canonical default) |
| Related ENH | ENH-107 (D-TF FVG retest signal isolation — should adopt spot SL on adoption), ENH-108 (second-touch retest detection — validation cohort consumer once chain gap closes), ENH-100 (formation-anchored magnitude profiling — MAE/MFE columns are downstream consumers of the right SL anchor) |
| Related TD | TD-S34-NEW-4 (`hist_option_bars_1m` post-2026-04-01 coverage gap — blocks expansion of validation cohort from n=7 to target n≥50) |
| Related commits | (S34 close commit TBD) |

---

## Context

S34 (2026-05-24) ran a stop-loss variant backtest on the same-day retest cohort: 22 retest entries on ≥1% index move-days where `ict_primitive_outcomes.first_retest_ts` fell on the move-day itself. Of the 22, 7 returned chain data (15 lost to TD-S34-NEW-4 post-2026-04-01 coverage gap). All 7 were directionally correct — long ATM CE (UP move) or PE (DOWN move) at the retest moment, every one closed in deep profit if held to EOD:

| Date | Symbol | Direction | TF | Type | Entry premium | EOD premium | Held PnL (points) |
|---|---|---|---|---|---|---|---|
| 2025-05-08 | NIFTY | DOWN | M5 | BEAR_FVG | 43.95 | 125.60 | +81.65 |
| 2025-05-15 | NIFTY | UP | H | BULL_FVG | 80.75 | 512.20 | +431.45 |
| 2025-05-20 | NIFTY | DOWN | H | BEAR_FVG | 137.30 | 220.60 | +83.30 |
| 2025-06-12 | NIFTY | DOWN | H | BEAR_FVG | 69.80 | 312.00 | +242.20 |
| 2025-12-08 | NIFTY | DOWN | H | BEAR_FVG | 57.50 | 216.50 | +159.00 |
| 2026-01-20 | NIFTY | DOWN | H | BEAR_FVG | 51.85 | 216.90 | +165.05 |
| 2025-05-15 | SENSEX | UP | H | BULL_FVG | 678.00 | 1659.10 | +981.10 |

Total held-to-EOD: +2143.75 premium points across 7 trades. At NIFTY lot 75 / SENSEX lot 20: NIFTY ₹87,266 + SENSEX ₹19,622 = **₹106,888 on 1 lot per day**.

Five stop-loss variants were tested against the same 7-day cohort:

| SL rule | Winners | Losers | Mean PnL (points) |
|---|---|---|---|
| No SL (hold to EOD) | 7 | 0 | +306.25 |
| 5% intra-bar low (1m wick) | 0 | 7 | -8.13 |
| 10% intra-bar low (1m wick) | 0 | 7 | -16.30 |
| 15% intra-bar low (1m wick) | 3 | 4 | +197.66 |
| 5% 1m-close-through | 0 | 7 | -8.13 |
| 10% 1m-close-through | 3 | 4 | +197.66 |

Every premium-based SL ≤ 10% wick-eliminated 100% of the winners. The 7 winners were structurally correct trades (spot moved decisively in the thesis direction same-day, never closed back through the zone), but premium on held ATM strikes routinely wicked 5-15% in the first 30-60 minutes from bid-ask, theta on tight-DTE options, and IV crush as morning gamma compressed. The wick noise was uncorrelated with whether the structural thesis remained valid.

A separate variant tested **spot-anchored stops** on the same 7 trades:

| Spot SL rule | Winners | Losers | SL triggers |
|---|---|---|---|
| 0.3% adverse spot 5m-close-through from entry | 7 | 0 | 0/7 |
| 0.5% adverse spot 5m-close-through from entry | 7 | 0 | 0/7 |
| 0.8% adverse spot 5m-close-through from entry | 7 | 0 | 0/7 |

The tightest spot SL (0.3%) never triggered on any of the 7 trades. The retest is structurally "the moment of maximum local risk" for the trade — once price has tagged the zone and begun rejecting, it does not return through. Premium wicked 5-15% on the same trades from microstructure alone; spot moved monotonically (with 5m-close granularity) in the thesis direction throughout the day.

---

## Decision

For ICT retest entries on ICT zone primitives (OB, FVG, Breaker, Mitigation, Premium/Discount), **the stop-loss is anchored to spot zone-invalidation on 5m-close-through, not to option premium decay.**

Specifically:

1. **BEAR retest stop.** A BEAR zone retest (BEAR_OB, BEAR_FVG, etc., entered as long PE on retest) is stopped out when a 5-minute spot bar **closes** at a price ≥ `zone_high * (1 + X)` where X is the per-timeframe invalidation buffer. The invalidation level is the zone's *upper* boundary plus a small slippage buffer; closing meaningfully above the zone means the rejection thesis has failed.

2. **BULL retest stop.** A BULL zone retest (BULL_OB, BULL_FVG, etc., entered as long CE on retest) is stopped out when a 5-minute spot bar **closes** at a price ≤ `zone_low * (1 - X)`. Closing meaningfully below the zone means the rejection thesis has failed.

3. **Buffer X — per-timeframe, initially bounded.** Initial empirical bound from the S34 cohort: 0.3%-0.8% across all 7 trades, none triggered at any level. The recommended initial setting is **X = 0.5% across all timeframes** as a conservative default. Calibration to per-timeframe values (analogous to ADR-004 §11 RETEST_TOLERANCE_PCT — W wider, M5 tighter) is a follow-on once validation cohort n≥50.

4. **Premium SL is explicitly retired** for retest-anchored entries. Premium-based stops measure option microstructure noise, not thesis validity. Wide premium stops (Compendium-era 30%+) approximate the right intent but couple SL hit rate to volatility regime, expiry distance, and bid-ask conditions that have nothing to do with the structural premise.

5. **Time-based exit policy is orthogonal and not addressed here.** ENH-107 (BEAR retest = EOD hold, BULL retest = 60m exit) defines time-based exit; ADR-012 defines stop-loss. The two compose: a BULL retest entry holds until the spot SL triggers, OR until the 60m horizon, whichever comes first.

---

## Why

The stop-loss must measure thesis failure. The thesis for a retest entry is: *price returned to a structural level, rejected from it, and is now moving away.* The thesis fails when price closes back through the level. It does not fail when an option premium wicks down 5% due to theta + spread + IV recompression while spot remains below (BEAR) or above (BULL) the zone.

Premium-anchored stops conflate two unrelated phenomena:
- **Thesis failure** (spot reverses through the structural level) — a real and decisive signal, occurs with O(seconds) latency on a 5m close-through.
- **Premium microstructure noise** (wide bid-ask on first morning bars, IV bleed as morning gamma compresses, theta drain on tight-DTE strikes) — uncorrelated with thesis, occurs continuously throughout the day.

Coupling SL to the second phenomenon while the first is the actual question being asked produces the empirical result observed in S34: 100% of structurally-correct trades stopped out, every winner converted to a loser. Premium SL on ATM held strikes is the wrong instrument-stop pairing.

Spot SL on 5m close-through measures thesis failure directly. It does not care about option premium, theta, IV, or bid-ask. It triggers if and only if the structural thesis is invalidated by price action on the timeframe that defines the primitive (5m bar close, consistent with ADR-004 §10 breach rule template: "a primitive is BREACHED when spot closes beyond the invalidation boundary on the timeframe of the primitive").

---

## Implementation

1. **Live signal builder.** Spot zone bounds are already exposed in `ict_primitives.zone_high` and `zone_low`. The signal-emitter computes and persists the SL level at signal time: `sl_level = zone_high * (1 + X)` for BEAR / `zone_low * (1 - X)` for BULL. Stop monitoring is then a simple bar-close check against `sl_level`.

2. **Order placer (`merdian_order_placer.py`).** Once a position is open against a signal, the placer subscribes to 5m bar-close events on the spot symbol and submits an exit market order when the bar-close triggers the SL condition. No premium-side stop is placed.

3. **Pine overlay.** `generate_pine_overlay.py` should render the SL level as a horizontal line on the chart for discretionary corroboration — the operator can see the line and confirm the algo's stop is in the right place. Standard rendering: solid red horizontal at SL level, label "SL: X% above/below zone."

4. **Backtest infrastructure.** Cohort backtests (e.g. S34's 7-day retest backtest) compute the SL trigger by walking `hist_spot_bars_5m` from `first_retest_ts` forward, finding the first 5m close that crosses the SL level. Exit premium is read from the chain table at that bar's timestamp. This is the SQL pattern that produced the S34 spot-SL result.

5. **Outcomes table.** `ict_primitive_outcomes` should add columns to record SL outcome per retest: `sl_triggered_ts`, `sl_exit_prem`, `pnl_with_sl_pct`. These compose cleanly with ENH-103/106 v7 option PnL columns — same compute path, different exit anchor. Filed as a sub-task under ENH-108 or as a standalone ENH if ENH-108 takes longer.

---

## Validation cohort requirements

n=7 is far too small for a doctrine commitment. The doctrine is **accepted as the default rule** based on the strength of the empirical signal (0/7 SL triggers at every level tested, 7/7 winners held cleanly), but parameter X is **provisional at 0.5%** until validation cohort reaches **n≥50**.

The validation cohort expansion path:

1. **Closing TD-S34-NEW-4** unlocks 15 additional same-day-retest entries (post-2026-04-01). Expected: cohort grows from 7 to ~22.
2. **ENH-108 (N-touch retest detection)** unlocks the 112 invisible-retest days. Each non-first-touch retest becomes a measurable entry. Expected: cohort grows from ~22 to several hundred.
3. **Parameter calibration.** Once n≥50, sweep X across {0.3%, 0.5%, 0.8%, 1.0%, 1.5%} per timeframe. Lock per-TF values matching ADR-004 §11 RETEST_TOLERANCE_PCT proportions.

Until n≥50 is reached, X = 0.5% is the operating default and any per-symbol or per-timeframe variations are explicitly out of scope.

---

## Consequences

**Immediate:**
- ENH-107 (D-TF FVG retest signal isolation) on adoption will use spot SL, not premium SL.
- Discretionary trades against the Pine overlay should use spot SL — operator updates SL line on chart manually from zone bounds.
- `merdian_order_placer.py` Phase 4B work, when scheduled, builds against spot-SL exit logic from day 1.

**Downstream:**
- Compendium WR labels that were measured with premium-anchored stops (pre-canonical era) are historical artifacts. Re-measurement of those cells under spot-SL is desirable but not blocking.
- ENH-101 (Stop-loss optimization from MAE distribution per TF×type×direction) was originally framed as premium-MAE optimization. Re-scope to spot-MAE under ADR-012 — same statistical approach, different anchor table column.

**Risks:**
- Spot SL on a strongly trending day with shallow pullbacks may stop out a valid trade if X is too tight. The S34 cohort suggests X = 0.3%-0.8% is comfortable, but the cohort is biased toward strong-trend days (≥1% intraday). Counterfactual: on a chop day where the move never materialized, spot SL at 0.5% may trigger correctly (thesis failed), but at 0.3% may trigger prematurely. The validation cohort must include non-≥1% days to test for this.
- The spot SL ignores intra-bar wick depth. A spot bar that wicks deep through the zone but closes back inside is *not* a stop trigger under ADR-012's close-through rule. This is consistent with ADR-004 §10 breach rule (closes, not wicks) but may produce subjectively uncomfortable holds during deep wicks. Premium drawdown during such a wick may exceed any premium-SL the operator would have set discretionarily. The doctrine accepts this — wick-based exits are exactly the failure mode the doctrine is built to prevent.

**Non-risks:**
- The doctrine does not interfere with profit-taking. Time-based exit (ENH-107) and any future profit-target rule compose independently.
- The doctrine does not require chain-side data (`hist_option_bars_1m`) for SL evaluation — only spot bars (`hist_spot_bars_5m`). Backtests can run on the full window even while TD-S34-NEW-4 blocks chain-side validation of premium outcomes.

---

## Status notes

- **2026-05-24 (S34):** Doctrine accepted on n=7 empirical signal strength. X = 0.5% default. Validation cohort expansion gated on TD-S34-NEW-4 closure and ENH-108 build. Filed as ADR-012.
- **Pending:** validation cohort n≥50, per-TF X calibration, ENH-101 re-scope under ADR-012 anchor, `ict_primitive_outcomes` schema extension for SL columns, Pine overlay SL-line rendering, `merdian_order_placer.py` Phase 4B build against spot-SL exit.
