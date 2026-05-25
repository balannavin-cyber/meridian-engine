# ADR-011 — Chain-table held-strike ATM PnL: reverse ADR-010 v3 source decision

| Field | Value |
|---|---|
| Status | Accepted |
| Date decided | 2026-05-22 |
| Date documented | 2026-05-22 |
| Session | Session 33 |
| Supersedes | ADR-010 v3 §"Source table choice" (the decision to read ATM premiums from `hist_atm_option_bars_5m` with same-strike enforcement) |
| Related ENH | ENH-100 (IMPLEMENTED v3→v7 rebuild), ENH-103 (IMPLEMENTED v6→v7 rebuild), ENH-106 (the build that implements this ADR) |
| Related TD | TD-S32-NEW-4 (vendor cross-tier drift on `hist_atm_option_bars_5m` — made architecturally moot by v7) |
| Related commits | (S33 close commit TBD with v7 writer marker `ENH-106 (S33) v7`) |

---

## Context

ENH-100 (S32) shipped ATM PnL columns on `ict_primitive_outcomes` against `hist_atm_option_bars_5m` — the 27,082-row aggregated table that vendor pre-picks ATM per 5m bar. v3 architecture enforced same-strike between anchor and each future horizon: if vendor rolled its picked ATM between anchor and `+N` minutes (which happens on any spot drift of ~0.5%), the horizon's column was set to NULL.

ENH-103 (S33 mid-session) extended the same source-table architecture to retest-anchored option PnL (5 additional columns).

S33 post-build cohort analysis exposed two problems:

1. **Coverage attrition.** Even with healthy table density (~82% of expected 5m bar slots populated), only ~28-46% of primitives had `atm_pnl_30m_pct` populated. Same-strike enforcement killed 50-70% of primitives where vendor rolled the strike.
2. **Median PnL negative on every populated cell.** Cohort analysis showed median 30m option PnL was NEGATIVE across every (symbol, tf, primitive_type, direction) cell with N≥15. This contradicted prior experimental findings (Exp 2 BULL_OB N=101 +70% T+30m expectancy).

The operator challenged the "sparse vendor data" framing: they had paid for and verified 12 months of vendor option data Apr-25 through May-26 and known it was dense. The challenge was correct.

**Root-cause investigation (S33 mid-session):**

- `hist_atm_option_bars_5m` is a vendor-aggregated table written by `build_atm_option_bars_mtf.py` for **wick-reversal analysis** (read by `experiment_26_option_wick_reversal.py`, `experiment_27_premium_ict.py`, `experiment_27b_premium_small_sweep.py`). It stores ONE row per 5m bar with vendor's chosen ATM strike + that strike's CE/PE OHLC. Designed for OHLC + wick analysis at ATM, NOT for held-position PnL across horizons.
- `hist_option_bars_1m` is the actual vendor option chain — 54.8M rows, 1m bars per (strike, expiry, option_type), dense and excellent across the full window. This is the canonical chain data the operator paid for.
- Experiments 1-50 (e.g. `build_hist_pattern_signals_5m.py`) queried `hist_atm_option_bars_5m` at signal time AND signal+30m WITHOUT same-strike enforcement — comparing two different vendor-picked ATM strikes' premiums and calling the percent change "PnL." Inflated coverage but mathematically wrong: a held position holds the original strike, not vendor's rolled strike. The "negative median" of v6 was the inverse error: mathematically correct held-strike check applied to the wrong source table.

The architecturally correct source for trader-realistic held-strike PnL is the chain table `hist_option_bars_1m`, with manual ATM strike picking from spot (NIFTY/50, SENSEX/100) and strike held constant across all horizons.

---

## Decision

ATM PnL computation (formation-anchored ENH-100 + retest-anchored ENH-103, 9 columns total) reads from `hist_option_bars_1m` chain with:

1. **Manual ATM strike picking** from spot at anchor:
   - NIFTY: `round(spot / 50) * 50`
   - SENSEX: `round(spot / 100) * 100`
   - Strike grid from existing `STRIKE_INTERVAL` constant; no reliance on vendor's pre-picked atm_strike.

2. **Empirical expiry calendar** via DISTINCT against `hist_atm_option_bars_5m.expiry_date` at writer startup (small 27k table, fast). Nearest-weekly resolution via bisect on sorted calendar with same-day-pre-15:30-IST handling for DTE=0 intraday case.

3. **Held strike across horizons.** At anchor: query chain at `(instrument_id, bar_ts, strike, expiry_date, option_type)`. At +5m/+15m/+30m/+60m/EOD: SAME `(strike, expiry, option_type)`, different `bar_ts`. No vendor-roll attrition; PnL is trader-realistic for the entry position.

4. **DTE derivation** from picked expiry: `(expiry - valid_from.date()).days`. Replaces v3's reliance on vendor's `dte` column.

5. **Era-aware vendor labeling.** Chain table `bar_ts` is IST-mislabeled-as-UTC (same Bug B3 era as 5m table). Existing `_vendor_bar_ts_label()` + `normalize_hist_bar_ts()` helpers reused.

6. **Per-tuple range prefetch.** Per unique `(strike, expiry, option_type)` tuple needed across primitive formation + retest + event anchors, one range query against chain covering `[min_target_ts, max_target_ts + 1min)`. Cached by minute-floored real-UTC ISO key for O(1) lookup during outcomes loop.

The schema (13 columns: 4 ENH-100 atm_pnl + 5 ENH-103 option_pnl + forward_*_pct + mfe + mae + time_to_mfe + dte_at_formation) is UNCHANGED. This is a source-table + compute-method reversal, not a schema change.

---

## Evidence

**Post-v7 backfill (2026-05-22, NIFTY+SENSEX 2025-04-01→2026-05-19, 19,399 outcomes in 1775.9s):**

Coverage jumped 20-30× on populated cells:

| Cell | v6 atm_pnl_30m | v7 atm_pnl_30m | Lift |
|---|---|---|---|
| NIFTY M5 BEAR | ~85 | 2650 | 31× |
| NIFTY M5 BULL | ~80 | 2607 | 33× |
| SENSEX M5 BEAR | ~70 | 2909 | 42× |
| SENSEX M5 BULL | ~60 | 2662 | 44× |
| NIFTY H BULL | ~22 | 91 | 4× |
| SENSEX H BULL | ~6 | 69 | 11× |

Median PnL flipped from universally negative (v6) to positive on every directional cell with real spot edge (v7):

| Cell (v7) | N_opt | Spot WR | Opt WR | Median 30m | Median 60m | Mean 30m |
|---|---|---|---|---|---|---|
| NIFTY M5 BULL_OB | 28 | 84.3% | 82.1% | +17.2% | +14.8% | +30.0% |
| NIFTY M5 BEAR_OB | 28 | 87.0% | 85.7% | +20.3% | +10.3% | +28.3% |
| SENSEX M5 BULL_OB | 45 | 80.0% | 77.8% | +16.4% | +5.7% | +33.6% |
| SENSEX M5 BEAR_OB | 45 | 76.8% | 75.6% | +15.0% | +8.1% | +20.2% |
| NIFTY M5 DISPLACEMENT_UP | 83 | 79.4% | 74.7% | +13.6% | +10.7% | +29.0% |
| NIFTY M5 DISPLACEMENT_DOWN | 93 | 80.5% | 77.4% | +14.8% | +10.3% | +19.7% |
| NIFTY H DISPLACEMENT_DOWN | 17 | 100% | 100% | +34.7% | +42.9% | +62.1% |
| NIFTY H DISPLACEMENT_UP | 29 | 94.9% | 89.7% | +22.0% | +61.9% | +44.2% |

M5 FVGs remain coin flips (~50% WR, ~0% median 30m) — confirms D.14.2 independently of source-table choice.

Retest-anchored cohort confirms ADR-009 §Phase 1 H-FVG retest finding empirically:

| Cell | N_opt | Retest Spot WR | Opt WR | Median 30m | Median 60m |
|---|---|---|---|---|---|
| NIFTY D BULL_FVG retest | 17 | 88.0% | 88.2% | +11.7% | +22.3% |
| NIFTY H BEAR_FVG retest | 51 | 83.8% | 72.5% | +4.8% | +7.3% |
| NIFTY H BULL_FVG retest | 50 | 76.1% | 60.0% | +3.8% | +2.1% |
| SENSEX H BEAR_FVG retest | 45 | 83.1% | 75.6% | +9.9% | +6.3% |
| SENSEX H BULL_FVG retest | 38 | 76.1% | 68.4% | +7.0% | +6.7% |

M5 retest cohort confirmed bad (every M5 cell has negative median 30m PnL; OB retest paradox documented at D.14.3 confirmed at option-PnL level — trade M5 OBs at formation, not retest).

DTE bucketing reveals structure:
- DTE=0: feast-or-famine (median 30m +58.7% to +19% on UP-direction displacements; median 60m turns negative on DOWN-direction at -4.8% to -9.2%). Exit at 30m.
- DTE=1-2: sweet spot for M5 (median 30m +13.6% to +24.4%, WR 74-83%, holds to 60m).
- DTE≥3: best for H-TF DISPLACEMENT (92-100% WR, median 60m +37-48%).

Falsification commitment satisfied — held-strike PnL on a primitive whose spot moved 0.3% favorably is +15-30% on ATM option, recoverable in chain data, missed by v6's vendor-rolled approximation. The "negative median everywhere" v6 result was an artifact of source-table mismatch, not a property of the underlying edge.

---

## Alternatives considered

**A. Keep v6 architecture, accept the coverage attrition as a property.**

Rejected. v6's universally-negative median was diagnostically misleading and would have led to incorrect trading decisions ("ATM options have no edge"). The attrition is non-random — it filters precisely the primitives where spot moved enough for vendor to roll, which are the very primitives where the edge plays out. Self-selection bias against winners.

**B. Drop same-strike enforcement (mirror Exp 2 methodology).**

Rejected. Comparing premiums of two different vendor-picked ATM strikes is not a tradeable PnL. A real trader at primitive formation buys ATM CE at strike X; if spot moves and vendor's ATM rolls to X+50 at +30min, the trader still holds X. Exp 2's "PnL" computation across vendor-rolled strikes was an unintentional source of upward bias — accepting it would have meant trading on the bias rather than the edge.

**C. Use `hist_option_bars_1m` with same-strike enforcement (drop manual strike picking; use vendor's atm_strike at anchor).**

Rejected. Vendor's atm_strike at anchor IS the manually-picked ATM in nearly all cases (vendor uses the same `round(spot/grid)*grid` formula). Skipping the vendor lookup eliminates one DB query per primitive and removes a coupling between writer and the aggregated table.

**D. Use both source tables — chain for held-strike PnL and 5m table for vendor-anchored sanity check.**

Rejected for v7. Adds writer complexity for no decision impact. The chain table is sufficient. The 5m table remains active and read by wick-reversal experiments (its original purpose); we only stop using it for ATM PnL computation.

**E. Add a "vendor cross-tier drift" column documenting the v6→v7 delta per row.**

Rejected as bloat. The post-rebuild cohort analysis IS the diff. Per-row delta has no downstream consumer.

---

## Consequences

### Positive

- **Coverage ~95% on 5/15/30m horizons** (chain density × calendar coverage) vs ~28-46% under v6.
- **Held-strike PnL is trader-realistic.** Pre-trade simulation, post-trade attribution, and live routing rule calibration all reflect what a trader actually experiences.
- **Source-of-truth alignment.** Chain table is the data the operator paid for and verified; the 27k-row 5m aggregation is a derived asset for a different purpose (wick analysis).
- **Source-table independence.** ATM PnL no longer depends on vendor's ATM-picking heuristic (which can change across vendor versions or instruments).
- **TD-S32-NEW-4 vendor cross-tier drift made architecturally moot.** The drift exists between vendor's pre-picked atm_strike and our manually-computed strike in the 5m aggregation; v7 never reads that column.

### Negative — risk to manage

- **Prefetch wall time is higher.** ~10 min per symbol for chain prefetch (~700k-970k bars per symbol across 839-1417 unique tuples) vs ~3s for the v5 5m-table prefetch. Acceptable for backfill; live-cycle path is untouched (live ATM is computed differently).
- **The 5m aggregated table now has reduced reason-to-exist post-ENH-106.** It remains read by wick-reversal experiments. If those are deprecated, the table becomes orphaned. Tracked as a TD candidate to revisit only when the wick experiments are retired.
- **`_atm_anchor_at` / `_atm_future_at` retired as dead code** in v7 writer. Trailing for-loop in `compute_atm_pnl_and_dte` is unreachable. Both intentional; will be cleaned in next writer refactor (low priority, no behavioral impact).
- **ADR-010 v3's "lightweight schema additive" framing remains correct;** ADR-011 does NOT re-litigate schema, only source-table choice + compute method.

### Mitigations

- v7 patch script (`patch_s33_enh106_chain_heldstrike_atm_pnl_writer.py`) AST-validates pre + post, requires v6 marker, refuses if v7 marker already present, creates `_PRE_S33_v7.py` backup. Dry-run + live workflow.
- Post-v7 cohort analysis IS the falsification check — coverage lift and median flip on directional cells are direct evidence that the rebuild was necessary and correct.
- Chain-table prefetch architecture is bounded: per-tuple range queries, paginated, with error handling per page. Worst-case behavior is degraded coverage on specific tuples, not write failure.

---

## Relationship to other documents

- **ADR-010 v3.** §"Source table choice for ATM premium reads" is superseded by ADR-011. ADR-010 v3 §"Schema extension (13 additive columns on ict_primitive_outcomes)" remains in force. ADR-010 v3 is annotated `[Source-table decision SUPERSEDED by ADR-011]` in the Decision Index but otherwise stands.
- **ADR-004 ICT Canonical Primitives.** Unchanged. Primitive detection layer is unaffected.
- **ADR-009 §Phase 1 calibration discipline.** v7 retest cohort empirically confirms H-FVG retest finding cross-symbol with real held-strike option PnL — strengthens D.14.1 from spot-WR-only to spot-WR + option-PnL. The validation now has two independent metrics agreeing.
- **MERDIAN_Assumption_Register.md.** New §D.15 added (D.15.1 chain-table canonical for held-strike PnL; D.15.2 M5 OB retest paradox confirmed at option-PnL level — falsified as edge; D.15.3 DTE structure on Tier 1 cells discovered; D.15.4 D-TF needs longer-than-30m horizons hypothesis).
- **MERDIAN_Enhancement_Register.md.** ENH-100 status v3→v7 IMPLEMENTED, ENH-103 v6→v7 IMPLEMENTED, ENH-106 IMPLEMENTED entry added.
- **tech_debt.md.** TD-S32-NEW-4 closed via architectural retirement (no longer reads the drifting column). Two new TDs filed: TD-S33-NEW-X (5m aggregated table reason-to-exist post-wick-experiment-retirement); TD-S33-NEW-Y (v6 dead code in `compute_atm_pnl_and_dte` trailing loop — clean up in next writer refactor).
- **CLAUDE.md.** Settled-decisions footer appends ADR-011 governance line.

---

## Governance language (one-line for CLAUDE.md settled-decisions)

> ATM PnL across horizons is computed from the chain table `hist_option_bars_1m` with manually-picked ATM strike (NIFTY/50, SENSEX/100) held constant — never via vendor's pre-picked atm_strike in `hist_atm_option_bars_5m`. The held position holds the entry strike; the PnL reflects that. Same-strike enforcement on a vendor-rolled-ATM source is a category error — strikes don't roll; vendor's pick does.

---

## Open follow-ups

1. **Post-v7 falsification audit (deferred from S33 close).** A 100-sample audit comparing v7 chain reads against locally-computed forward percent-change from `hist_option_bars_1m` directly — verifies writer is using the chain correctly. Original ENH-100 falsification criterion (5% agreement) now tautological since both audit and writer read the same source, but a per-row sanity check on strike rounding + expiry calendar lookup remains valuable. Tracked as audit task in S34+.
2. **D-TF horizon extension.** D-TF cells show positive spot WR (~67%) but negative option PnL median at 30m/60m. The MFE/time_to_mfe columns may already answer "what horizon would the D-TF cells be tradeable at" — analysis SQL only, no writer work. Carry-forward.
3. **TD-S33-NEW-X (5m aggregated table re-evaluation post-wick-experiment-retirement)** — file in tech_debt.md as S3.
4. **TD-S33-NEW-Y (v6 dead code cleanup in compute_atm_pnl_and_dte)** — file in tech_debt.md as S4.

---

*ADR-011 — 2026-05-22 — Session 33 — accepted. Reverses ADR-010 v3 §"Source table choice"; schema (13 columns on `ict_primitive_outcomes`) and ADR-010's other clauses unchanged.*
