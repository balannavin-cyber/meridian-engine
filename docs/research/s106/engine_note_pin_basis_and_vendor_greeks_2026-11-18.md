# Engine note: why the pin did not move on 2026-11-18, and what could fix it

**Date:** 2026-11-19, written from the 2026-11-18 session (13:09 to 15:25 IST).
**Status:** FINDING and OPTIONS. Nothing here is a ruling, a build authorisation or a pre-registration. No production object is changed as of this note.
**Scope:** engine stream (Board pin, Net Γ). The tape stream and the retail stream are affected only through the consumers listed in section 7.

---

## 1. Summary

On 2026-11-18 NIFTY fell about 0.9 % and the Board pin stayed on 25,500 all session, with 25,400 as runner-up. The operator read this as the board being broken.

Ingestion, compute and the database were healthy. The behaviour comes from two design-level issues, both present before 18 November:

1. **Ranking basis (the larger effect).** The pin ranks strikes on call γ·OI minus put γ·OI. That can only nominate a lopsided strike, which in practice is one of the two OI walls. Strikes around spot with heavy OI on both sides cancel to near zero.
2. **Vendor greeks.** The vendor's call gamma and put gamma at the same strike disagree whenever the vendor's assumed forward differs from the forward the option prices imply. The netting subtracts one from the other, so every netted figure tilts toward calls on those days.

Neither is a one-day fault. Issue 1 shows whenever the front expiry is more than a day or two away. Issue 2 was present on most days from 5 to 18 November.

---

## 2. What was observed

Board at 13:05 IST, NIFTY, front expiry 23 Nov:

| Item | Reading |
|---|---|
| Spot | 25,181 (down about 232 points, −0.91 %) |
| Pin (γ-conc) | 25,500 · 9.3 % of gross · dampening · ≡ call OI wall |
| Runner-up | 25,400 · #2/#1 = 0.92 |
| Lead | 0.7 pts |
| Pin state | STABLE · held 46 cycles · 230 min |
| Conviction | 0.11 |

The leader was 25,500 from the 09:20 cycle onward (the 09:15 cycle was 26,000). SENSEX showed the same shape: netted leader 82,500 with spot near 81,800.

---

## 3. What was checked and found healthy

All checks cover 2026-11-18 up to 14:15 IST unless stated. Queries were run by the operator in the SQL editor.

| Check | Result |
|---|---|
| Chain ingestion | 156 runs per symbol 08:30 to 14:55, no gap over 7 minutes, no thin run. NIFTY 534 to 548 rows per run, SENSEX 500 |
| Two runs per 5-minute slot | Front and back expiry. Back expiry is ingested and not computed, by ruling S90-B |
| Compute per front-expiry chain run | 60 of 60 on `gamma_metrics`, `gex_strike_snapshots`, `volatility_snapshots` and `gex_cycle_history`, both symbols |
| Gamma clock | 60 runs per symbol, 09:15 to 14:10, max gap 5.0 minutes, no null `net_gex`, `flip_level`, `max_gamma_strike` or `spot` |
| `script_execution_log` | No failures. Only pre-open skips, and `compute_basis_context_local.py` skipping until 09:26 for lack of futures snapshots |
| Gamma repricing | Call γ at 25,500 moved 9.6 → 7.5 (×10⁻⁴) from 09:20 to 13:30 as spot fell. ATM γ about 9.8 against a Black-Scholes value of 9.6 to 10.0 |
| Arithmetic | The 25,500 bar (+4,874 per 1 %) reconciles exactly to γ·OI·S²/10⁷ from the stored inputs |

---

## 4. Problem 1: the ranking basis

**Where it lives.** `v_gex_strike_rank` (ENH-125, S81) ranks on `abs(gex_cr)`. `gex_cr` is the per-strike net, call contribution minus put contribution (ADR-024 Amendment A). `v_gex_concentration.hhi_net` and `top_strike_net` use the same basis by construction. `write_gex_cycle_history_local.py` reads rank 1 from the view into `gex_cycle_history.pin_leader_strike`.

**Why S81 chose it.** Ranking on `abs()` rather than positive-only was meant to escape the "OTM calls are above spot" tautology of ADR-024. It removes the sign from the sort order, but the netting inside `gex_cr` remains, so the top strike is still whichever strike is most one-sided.

**Evidence, NIFTY 13:30 IST, spot 25,169:**

| Strike | Call OI | Put OI | Netted rank · share | Both-sides rank · share |
|---|---|---|---|---|
| 25,500 | 144L | 45L | #1 · 9.5 % | #3 · 9.2 % |
| 25,400 | 113L | 37L | #2 · 8.5 % | #5 · 8.4 % |
| 25,000 | 38L | 120L | #3 · 7.7 % | #4 · 8.5 % |
| 25,300 | 111L | 59L | #4 · 6.9 % | #1 · 10.3 % |
| 25,200 | 87L | 79L | #18 · 2.0 % | #2 · 10.2 % |

"Both-sides" means call γ·OI plus put γ·OI per strike.

**Why the leader did not move during the fall.**

- At 5 calendar days to expiry the straddle priced about ±343 points, so a 230-point move is under one standard deviation. Call γ at 25,500 fell about 20 %.
- Call OI at 25,500 rose from 81L (09:15) to 114L (09:45) to 144L (13:30). At 25,400 it rose from 77L to 113L. OI growth outran γ decay.
- The strikes spot moved into hold OI on both sides and cancel.

**SENSEX, same day.** At 09:45, after a fall of about 400 points to 82,058, the netted leader was 83,000 (23L calls, 1L puts), more than 1 % above spot. The both-sides leader was 82,500 and then 82,000 by 13:30. 82,200 (9L calls, 10L puts) ranked 61st on the netted basis and 3rd on both sides.

**Across days (09:15 to 15:30; 18 Nov to 14:15):**

| | Netted leader, avg distance from spot | Cycles above spot | Distinct netted leaders | Both-sides leader, avg distance |
|---|---|---|---|---|
| NIFTY 16 Nov (1 day to expiry) | 0.35 % | 44 of 75 | 5 | 0.13 % |
| NIFTY 17 Nov (expiry day) | 0.27 % | 26 of 75 | 5 | 0.10 % |
| NIFTY 18 Nov (5 days) | 1.07 % | 60 of 60 | 2 | 0.30 % |
| SENSEX 16 Nov (3 days) | 0.64 % | 64 of 75 | 5 | 0.28 % |
| SENSEX 17 Nov (2 days) | 0.65 % | 46 of 75 | 2 | 0.43 % |
| SENSEX 18 Nov (1 day) | 0.59 % | 45 of 60 | 4 | 0.22 % |

NIFTY looked new on the 18th because it was the first day on the 23 Nov contract. Near expiry gamma is narrow and concentrates at the money, so the netted pin stays close. Early in the contract gamma is wide and OI imbalance dominates.

**Counterfactual seen live.** For about four minutes on 18 Nov the both-sides basis was live in production (section 8). Rank 1 read 25,200 on NIFTY and 82,000 on SENSEX.

**A related presentation point.** PIN STATE read STABLE on a lead of 0.7 pts. The state counts cycles held and not margin, and its thresholds are still the uncalibrated D-6 seeds. `engine_note_tape_pin_anchor_2026-11-07.md` already notes that the leader hops when the lead is under about 1 pt.

---

## 5. Problem 2: vendor greeks

**Where it lives.** `ingest_option_chain_local.py` stores the vendor's per-leg `gamma` and `iv` as delivered. `compute_gamma_metrics_local.py` uses that gamma in `signed_gamma_exposure` (CE positive, PE negative). Nothing in between checks that the two legs of one strike agree.

**What theory requires.** A call and a put at the same strike and expiry share one implied volatility and therefore one gamma.

**What the vendor delivers, 18 Nov, near-the-money strikes:**

| | Call IV | Put IV | Call γ ÷ put γ |
|---|---|---|---|
| NIFTY 09:15 | 12.56 | 16.28 | 1.28 |
| NIFTY 13:45 | 12.89 | 14.85 | 1.14 |
| SENSEX 09:15 | 14.92 | 18.10 | 1.19 |
| SENSEX 13:45 | 14.50 | 16.40 | 1.12 |

Measured on `gex_strike_snapshots` across 54 NIFTY cycles, the near-the-money call/put gamma ratio ran 1.11 to 1.43, median 1.22.

**Cause, confirmed in direction.** The gap tracks the difference between the option-implied forward (call price minus put price plus strike) and a vendor forward of spot plus carry at roughly 10 % a year. The 10 % is inferred from the fit; it is not from vendor documentation.

| Date, contract (10:00 to 10:30) | Implied forward minus spot | Vendor carry at ~10 % | Mismatch | Call IV ÷ put IV |
|---|---|---|---|---|
| NIFTY 17 Nov, 6 days | +40.0 | about +42 | about 2 | 0.97 |
| NIFTY 16 Nov, 1 day | +8.8 | about +7 | about 2 | 0.98 |
| NIFTY 12 Nov, 5 days | +21.8 | about +35 | about 13 | 0.92 |
| NIFTY 13 Nov, 4 days | +6.1 | about +28 | about 22 | 0.86 |
| NIFTY 18 Nov, 5 days | −8.0 | about +35 | about 43 | 0.76 |
| NIFTY 6 Nov, 3 days | −28.4 | about +21 | about 49 | 0.73 |
| SENSEX 17 Nov, 2 days | +37.7 | about +45 | about 7 | 0.96 |
| SENSEX 18 Nov, 1 day | −49.2 | about +22 | about 71 | 0.79 |

Front-expiry ratio by day, 5 to 18 Nov: NIFTY 0.77, 0.73, 0.95, 0.92, 0.92, 0.86, 0.98, 1.06, 0.76. SENSEX 0.98, 0.74, 0.84, 0.98, 1.03, 0.83, 0.95, 0.96, 0.79. Back expiries ranged 0.63 to 0.97.

**Effect on the board, 18 Nov, NIFTY.**

- **Pin.** With call and put gamma equalised (mean of the two per strike), the netted leader would have been 25,000 in 44 of 54 cycles, 25,500 in 8 and 26,000 in 2. The asymmetry decided which wall led.
- **Net Γ.** On strikes carrying both gammas, the stored net was 12 to 36 % above the equal-gamma net from 09:45 onward (for example 14,991 against 10,998 at 09:45, and 19,691 against 17,553 at 12:45, per 1 %). At 09:15 it was +6,094 against −132. This replaces the rougher "15 to 25 %" quoted in the session.
- **Missing legs.** On average 69 legs per run on NIFTY (about 13 %) and 138 on SENSEX (about 28 %) have open interest and no vendor gamma, so they contribute nothing. Example: the 24,900 call at 09:20, 1.8 % in the money, carried γ = 0.

**A register entry to correct.** Assumption Register D.19.2 (VALIDATED-S37) reads the same-strike call/put gamma gap as an "IV skew signal" and a regime indicator. Skew is across strikes. This gap is a property of the vendor's solve.

---

## 6. Possible fixes

These are options as I see them. The order in section 6.3 is my recommendation; the choices are the operator's.

### 6.1 Vendor greeks

| Option | What changes | For | Against |
|---|---|---|---|
| **G1. Own solve** | Per run and expiry, take the forward from put-call parity on near-the-money strikes. Solve one IV per strike (from the out-of-the-money leg). Compute gamma for both legs from it with `core/bs_engine.py`. Keep vendor gamma in its own columns | Legs agree by construction. Fills the legs the vendor leaves empty. Removes the day-to-day call tilt | Capture-path change: after-hours deploy window, replay check, written rollback. Needs stale-price handling for illiquid legs |
| **G2. Symmetrise in compute** | In `compute_gamma_metrics_local.py`, use one gamma per strike for both legs (the out-of-the-money leg's, or the mean) | Small change, no solver | Still vendor numbers. Does not fill empty legs. Choice of leg is a judgement |
| **G3. Leave and caveat** | Board carries a caveat on netted figures | No build | The tilt stays and moves with the market |

### 6.2 Ranking basis

| Option | What changes | For | Against |
|---|---|---|---|
| **R1. Add a both-sides leader beside the netted one** | New view (for example `v_gex_strike_rank_gross`) and new columns in `gex_cycle_history`. Board shows both, named for what they are | Additive and reversible. No break in stored history. Gives live side-by-side data before any ruling | One more item on the Pin tab. Needs a Lovable round |
| **R2. Replace the basis** | `v_gex_strike_rank` and `v_gex_concentration` rank on call γ·OI plus put γ·OI | The pin follows where gamma is | Breaks pin-state history at the switch date. Needs an ADR-024 amendment, new view comments, and restated pre-registrations (section 7). The measure becomes sign-blind in a stronger sense |
| **R3. Keep the basis, change the presentation** | Show distance from spot in σ once a canonical σ exists (E-2). Withhold the state word when the lead is under a threshold | No compute change | Does not move the pin. Board wording changes need operator approval. Thresholds need D-6 calibration |
| **R4. Re-open pressure ranking** | A proximity-weighted rank, as the parity target describes its own (gamma × distance decay around spot × time amplifier) | Closest to the parity target's stated definition | Declined on evidence at D-5a (S89). Formula undisclosed. Needs a new ruling |

### 6.3 Recommended order

1. **G1 first.** Every netted number changes under corrected greeks, so the ranking question should be judged on clean inputs. G2 is acceptable as a stopgap if G1 cannot be scheduled soon.
2. **R1 next.** Run both leaders side by side for a few weeks across a full expiry cycle on each symbol.
3. **Rule R2 or R3 on that evidence.**
4. **Calibrate the pin-state thresholds (D-6)** on whichever basis survives.

### 6.4 How to test before anything goes live

- Replay stored days 5 to 18 November from `option_chain_snapshots` with G1 and compare against the stored values: call/put gamma ratio per strike equal to 1.00, count of legs filled, Net Γ and flip before and after.
- For R1, recompute both leaders per run from `gex_strike_snapshots` (available from 2026-05-25) and report distance from spot and number of leader changes by days-to-expiry bucket.
- Controls: a day with a ratio near 1.00 (17 November) should change little under G1.

---

## 7. What a basis change touches

| Consumer | Effect |
|---|---|
| Board Pin tab (tile, runner-up, lead, ladder) | Reads `v_gex_strike_rank` and `v_pin_board` |
| `gex_cycle_history` (`pin_leader_strike`, `runnerup_share_ratio`, `top5_share`, `conc_top1_share`, `conc_hhi`, `pin_state`, `held_for_cycles`, `conviction`) | Written from the views each cycle. History is not comparable across a switch |
| `/tape` PIN card | Uses `gex_cycle_history`. The recorder's own `tape_chain_runs.leader_strike` is computed separately and would differ, raising the "pin differs from tape record" chip |
| H-C pre-registration (tape stream) | Asserts `leader_strike` equals the `gex_cycle_history` leader and excludes mismatches |
| P1d pre-registration (engine stream) | Defines the pin as recomputed from `gex_strike_snapshots` on the current basis |
| `gamma_metrics.gamma_concentration` | Same arithmetic as `hhi_net`, computed in Python. Would diverge from the view |
| ADR-024, ENH-125, ENH-122, view `COMMENT`s, manual §3.2 and glossary | Describe the current basis |

---

## 8. Production change made and rolled back on 2026-11-18

Recorded so the session log is complete.

- At about 13:36 IST Claude ran `CREATE OR REPLACE VIEW` on `public.v_gex_strike_rank` and `public.v_gex_concentration` through the operator's SQL editor, switching both to the both-sides basis. This was done on the instruction "fix it" without first showing the SQL. The operator objected.
- Before the change, live definitions matched `sql/snapshots/adr032_pre_defs_2026-10-31.sql` by md5 (`9cc07f97e0b7862e265d5422439d304c` and `5c075092325391d869b3397bcdca832a`).
- At about 13:40 IST both views were restored from that snapshot. The md5 check returned both original values.
- The 13:35 and 13:40 cycles in `gex_cycle_history` were written on the original basis (pin 25,500, held 52 and 53). No stored row carries the changed basis.
- No table, row, grant, function or parameter was touched.
- Standing rule from this: Supabase queries are given to the operator to run. Claude does not run SQL on production.

---

## 9. Database health, same session

- **Size:** 46 GB. `hist_option_bars_1m` is 19 GB, of which 10.2 GB is indexes.
- **Load:** one read on `market_ticks` accounts for about 143,000 seconds of database time (2.95M calls, 48.5 ms mean). Its indexes are 527 MB on a 368 MB table of about 2M rows; `idx_mt_token_ts` and `idx_market_ticks_sym_type` (about 400 MB together) show almost no use. Probable index bloat.
- **Views near the timeout:** `v_gex_max_pain` averages 0.9 to 1.0 s with a worst case of 8.0 s; `v_gex_pin_maxpain` peaks at 7.9 s. The pin-history writer reads both every cycle.
- **Little-used indexes:** about 3.2 GB, the largest being primary keys (`hist_option_bars_1m_pkey` 2,157 MB with 0 scans). Counters cover only the period since statistics were last reset.
- **Dead rows:** worst on the stock-screener tables (`eq_feature_store` 15.9 %, `equity_eod` 16.3 %). Engine hot tables are at about 1 %.
- **Retention:** `option_chain_snapshots` reaches back to 2026-08-24. `pg_cron` job 19 (`cleanup_gamma_engine_daily`) is inactive, which matches the S89 tripwire. The table grows by roughly 150 MB a day at current volume.
- **Leftovers:** `eq_price_daily_backup_20260618` (510 MB); one idle connection open about 82 days.

---

## 10. Not verified

- The vendor's carry rate. About 10 % fits; it has not been confirmed with the vendor.
- The option-implied forward on 18 Nov (−8.0 on NIFTY, 10:00 to 10:30) against the futures basis the board showed (+17.6 at 13:05). Different times, and last-traded prices can be stale. Not reconciled.
- The both-sides basis used raw `gamma_call`/`gamma_put` columns, which bypass the deep-in-the-money guard that `gex_cr` carries (TD-NEW-2 Part A). S79 measured that effect as at most 0.0021 on the concentration figure; it was not re-measured here.
- Whether the parity target nets per strike before ranking. Its pin is described as pressure-ranked, which is a different construction.
- The plan's disk limit, which is visible only in the dashboard.
- The 18 Nov session after 14:15 IST.
