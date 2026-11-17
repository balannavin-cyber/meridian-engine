# Futures as the hedge footprint: M1 (hedge ratio at weekly expiry) and M2 (basis response to γ). Pre-registration

| Field | Value |
|---|---|
| **Status** | **DRAFT for operator acceptance.** Becomes PRE-REGISTERED when its `git hash-object` is recorded before the first outcome query. |
| **Lane** | Futures OI dimension, operator-only. Not on the S92-I priority track; mints no ADR, TD or ENH ID. |
| **Risk class** | **RO.** Reads through `bin/roq.sh` as `merdian_ro`; writes nothing to the database. |
| **Question** | Is the futures market where the chain's exposures get hedged, and if so, with which sign? |
| **Relation to prior results** | P2 left the dealer reading of the γ sign REGIME-DEPENDENT on daily NSE participant data. P1 was NO, P1c INCONCLUSIVE. The 2026-11-17 price × OI class test (Stage 1) did not meet its rule on the design period. M1 and M2 test the mechanism those results leave open. They do not reopen any of them. |

## 1. The claim under test

Every exposure layer is a predicted hedge demand:

    hedge flow in futures ≈ −s × (Γ-exposure · ΔS + ∂Δ/∂σ · Δσ + ∂Δ/∂t · Δt)

The bracket is computed from the chain. **s** (which side holds the book and hedges) is not observable in the chain. M1 asks whether the hedge exists at all in futures. M2 asks whether its sign and size follow the γ the chain shows.

## 2. Data (fixed at commit)

- **Window:** 2025-04-01 to 2026-03-30, **NIFTY** for both verdicts. SENSEX is reported descriptively only (§7).
- **Futures:** `hist_future_bars_1m`, NIFTY instrument `9992f600-51b3-4009-b487-f878692a0bc5`, `contract_series` 1, 2, 3. Verified 2026-11-17 against the Fyers pull: series = expiry rank, OI at 15:29 identical on 247/247 (series 1), 246/247, 242/247.
- **Options:** `hist_option_bars_1m` (OI, close) joined to `hist_option_greeks_1m` (`iv`, `gamma`, `r_used`) on `instrument_id, bar_ts, expiry_date, strike, option_type` (join measured 100 %, Data Inventory §6.1).
- **Spot:** `hist_spot_bars_1m`.
- **Clock:** all four tables carry the vendor clock (IST written as UTC, `:59`). No clock conversion is made between them.
- **Close:** the last bar at or before 15:29:59. The 15:30 bar is never used.
- **Delta:** Black–Scholes from the stored `iv`, spot, strike, `r_used`, T = exact time to 15:30 IST on expiry ÷ 365. Call Δ = N(d1); put Δ = N(d1) − 1. Vendor delta is not used.
- **Futures expiry days** (a `contract_series` 1 contract's last session) **and the session after** are excluded from every set in M1 and M2, and counted.

## 3. M1: hedge ratio at weekly expiry

**Idea.** When an option series expires, its delta ceases to exist. Futures held against it must be closed. No futures contract expires that day, so little else predicts a fall in futures OI on exactly those days.

- **Event:** an option `expiry_date` E in the window on which no NIFTY futures contract expires, with chain rows and a solved `iv` at the close of the prior session E−1. An event without them is ineligible and counted.
- **F(d):** total futures OI, series 1 + 2 + 3, at the close of session d (roll-invariant).
- **Expiring gross delta G(E):** Σ over strikes of |Δ| × OI for the series expiring on E, calls and puts, at the close of E−1. Net delta N(E) = |Σ Δ × OI| is reported beside it.
- **Outcome:** d(E) = [ln F(E) − ln F(E−1)] − median of the same one-day change over the other eligible sessions in the same calendar week.

**Tests (fixed):**
1. **Expiry effect.** Wilcoxon signed-rank on d(E), one-sided, H: median < 0, α = 0.05.
2. **Dose.** Spearman ρ between the abnormal fall in quantity, −[ΔF(E) − week median ΔF], and G(E), one-sided, H: ρ > 0, α = 0.05.
3. **Estimate, no verdict.** ĥ = median of abnormal fall ÷ G(E), with a bootstrap 95 % interval over events (10,000 resamples, seed 20261117). Also against N(E).

**Verdict:** both tests met → **HEDGE FOOTPRINT PRESENT**. Test 1 only → **EXPIRY EFFECT, NOT DOSE-SCALED**. Otherwise → **NOT DETECTED**.

**Placebo, descriptive.** NIFTY's weekly expiry moved from Thursday to Tuesday in September 2025. The same statistic is reported for non-expiry Tuesdays before the move and non-expiry Thursdays after it.

## 4. M2: does the futures basis respond to spot the way γ predicts?

**Idea.** A hedger who dampens sells futures into a rise, so futures lag spot and the basis narrows on up-moves. One who amplifies does the reverse. If the chain's γ describes real hedgers, the basis response to a spot move scales with γ.

- **Sessions:** window sessions that are not an option expiry day (the Greeks sidecar skips dte 0), not excluded by §2, with at least 95 % of spot and series-1 bars present. Others are counted.
- **Windows:** non-overlapping 5-minute windows starting 09:20, the last ending 15:00.
- **ΔS:** change in spot close over the window. **Δb:** change in b = series-1 futures close − spot close over the same window.
- **Dose g:** net ÷ gross γ at the window's first minute, front expiry (nearest `expiry_date` after the session date): g = Σ sign × γ × OI ÷ Σ γ × OI, CE positive, PE negative. Unitless, range −1 to +1. This is the board's own net-over-gross.
- **Model:** Δb = a + β0·ΔS + β1·(g × ΔS) + ε, ordinary least squares. Intervals by session-clustered bootstrap, 10,000 resamples, seed 20261117.

**Test (fixed):** β1 ≠ 0, **two-sided**, α = 0.05. Two-sided because P2 left the side REGIME-DEPENDENT. The sign found is a mapping **found, not predicted**: β1 < 0 reads as dampening where net γ is positive.

**Stability conditions (fixed):** the sign of β1 is the same (a) in both half-years (Apr–Sep 2025, Oct 2025–Mar 2026) and (b) in at least two of three terciles of session realised volatility (from 5-minute spot returns). The volatility strata exist because short-γ periods are faster, and a faster tape alone widens the futures–cash lead.

**Verdict:** significant and both stability conditions met → **MECHANISM OBSERVED (indicative)**, with the sign. Significant but unstable → **UNSTABLE**. Not significant → **NOT OBSERVED**.

**Degeneracy gate.** If g has one sign on ≥ 90 % of windows, the result carries the label "dose nearly one-signed" and the sign reading is not made.

## 5. Controls that must pass before any outcome is computed (Rule 0)

- **C1 clock.** Correlation of 1-minute series-1 futures returns with spot returns at lags −1, 0, +1 minute over 20 sessions: lag 0 must be the largest.
- **C2 units.** Median series-1 futures OI at close and median front-expiry option OI per strike near spot are printed with their magnitudes. Both must be quantities (index units), not contracts. If they differ in unit, ĥ is not reported until converted, and the conversion is stated.
- **C3 γ parity.** sign(g) agrees with the sign of `hist_gamma_metrics.net_gex` at the same minute on ≥ 85 % of 500 sampled window starts. The two use different expiry scopes, so agreement is expected to be high but not exact; the measured rate is reported.
- **C4 delta sanity.** At the close of five sampled E−1 sessions, the strike nearest spot has call Δ within 0.35–0.65.

**Any control failing stops the run. The cause is diagnosed before anything in §3 or §4 is computed.**

## 6. Sample

No cell is suppressed. Every count is reported. M1 with fewer than 20 eligible events carries **UNDERPOWERED** beside its verdict. Expected: about 35–40 NIFTY events, fewer where the sidecar has no `iv` (193 of 247 sessions solved); about 150–180 M2 sessions at 68 windows each.

## 7. Reported descriptively, no verdict

- **SENSEX → NIFTY.** For SENSEX option expiries: the M1 statistic computed on NIFTY futures F(d) against SENSEX G(E). This previews the claim that SENSEX γ is hedged in NIFTY futures. SENSEX's own futures are not used (vendor series unusable; OI a few thousand).
- **Volume.** Regression of series-1 futures volume per window on |ΔS| and |ΔS| × gross γ, with time-of-day slot effects.
- **Synthetic forward.** M2 repeated with b measured against the put–call-parity forward (median over the three strikes nearest spot with both legs in that minute, front expiry) in place of spot.
- **Expiry-afternoon path.** F at 15-minute steps on event days against the week's other days.

## 8. Limits

- **One year, one index, no like-for-like holdout.** The vendor option bars and the Greeks sidecar end in March 2026. Confirmation is forward, on the live chain and the Fyers futures tables, under its own pre-registration.
- **OI is a stock.** A hedge closed against another closing position lowers OI; one passed to a new holder does not. ĥ is therefore a lower bound on hedging, and M1 can miss hedges that change hands.
- **The basis is a proxy for signed flow.** No aggressor side exists for futures in this window. The tape recorder does not cover it.
- **Arbitrage and cash-carry positions** sit in futures OI and are unrelated to options. They add noise to M1, not bias, unless they also unwind on option expiry days.
- **Positioning sign, not a dealer sign** (P2). M2 tests whether a number scales a response, not who holds what.
- **The Stage 1 holdout (2026-04 onward) stays sealed.** Nothing here reads futures data after 2026-03-30.
