# ADR-033 — Gamma V2 alongside V1: versioned isolation (scope D)

| | |
|---|---|
| Status | **DRAFT** (authored S107, Wed 2026-11-25). Becomes PROPOSED when the V-2 results are in; ACCEPTED only on the operator's word. |
| Decided by | Operator rulings R1–R6, 2026-11-25 ~09:25 IST, relayed by MR-PIN3 |
| Lanes | Engine (author), Pin (independent check), Order flow and Retail (notified, no change required) |
| Evidence | `docs/research/pin_proof/` (gamma pipeline audit 2026-11-22, order check rev 3), I-002 rows 1, 11, 17; reads of 2026-11-24/25 recorded in the S107 close |

## 1. Context

The audit showed that per-strike exposure computed on each leg's own vendor gamma is wrong where the two vendor gammas disagree or one is missing. Correcting `gex_cr` in place was considered and rejected by the operator (R1) for four reasons read from `merdian_compute/gamma.py` at `934fe44`: `compute_flip_level` pools two constructions; `determine_regime` uses only whether a flip exists; `compute_expansion_probability` is a hand-set point score; and an in-place change fails live check I2 of `p3b_sweep` (v1.2, pg_cron job 47, every 5 minutes) on every run. An in-place change would also break the 313-row Retail contract test by design.

## 2. Decision

**D1 — V1 is frozen and named legacy.** `gex_cr`, `gamma_call`, `gamma_put`, `net_gex`, `gamma_concentration`, `flip_level`, `flip_distance`, `regime`, `gamma_zone`, `expansion_probability`, `max_gamma_strike`, `pin_risk_score`, every function behind them, `p3b_sweep` v1.2 and the contract test keep today's rule, columns and inputs. There is no break date. `merdian_compute/gamma.py` is not edited.

**D2 — V2 is computed alongside, never into a V1 column.** Code: `merdian_compute/gamma_v2.py` (new, standard library only, imports nothing from `gamma.py`, not exported from the package, not part of the Retail contract). Storage: two new tables, `gex_strike_v2` (per strike) and `gex_run_v2` (per run). The writer calls V2 after the V1 writes succeed; a V2 failure is logged and never stops V1.

**D3 — The V2 rule is rule v1.1** (section 3). V2 produces no flip, regime, zone, expansion probability, max-gamma strike or pin-risk score (R6: no V2 flip of any kind).

**D4 — V2 views carry new names** so each Board tile is repointed deliberately: `v_gex2_strike_rank`, `v_gex2_strike_pin_zone` (the like-for-like counterpart of the V1 pin zone: same walk and tau, on V2 net), `v_gex2_strike_accel_zone`, `v_gex2_concentration`, `v_gex2_abs_exposure`, `v_gex2_strike_terrain`, `v_gex2_net_gamma_river`; `_1pct` forms where the V1 tile reads one (ADR-032). `v_gex_strike_rank_gross` stays the gross pin view.

**D5 — V2 has its own invariants:** function `p3b2_sweep`, table `p3b2_invariant_checks`, job `p3b2_invariants`. Per-strike recompute from the chain; sum = V2 net; top shares and HHI recompute; `gex_run_v2.gross_top_share` = rank-1 share of `v_gex_strike_rank_gross` for the same run, symbol and expiry; a presence check that FAILS for a run that has V1 per-strike rows and no V2 rows; an INFO count of legs with more than one row.

**D6 — Backfill: yes** (operator, 2026-11-25), after V-2c passes, from stored `gex_strike_snapshots` rows, into the V2 tables only. Backfilled rows carry `rule_version = 'v2-1.1-gss'`; live rows `'v2-1.1'`. Duplicate leg rows are not visible in stored rows.

**D7 — The Board Pin switches to the gross pin as its own change** (R2, R3), through the wrapper `v_gex_pin_gross`. `v_gex_strike_rank` is not replaced; `gex_cycle_history.pin_leader_strike` is not redefined. Pin state, held cycles, conviction, HHI and top-5 appear under a line named "Net peak". Legacy outputs are labelled "legacy, unvalidated" on the Board (R4); removal is a later single release. Dealer wording is unchanged for now (R5).

## 3. Rule v1.1 (V2 per-strike exposure)

**Scope.** One map per symbol, expiry and run. A run whose chain rows carry more than one expiry is an error and has no V2 output. V2 runs only after V1 succeeds.

**Spot.** S is the run's spot. From chain rows, S is the `spot` of the rows with `spot` > 0; all such rows of a run must carry the same value. If they carry more than one distinct value, the run is an error and has no V2 output. (V1 takes the first row with `spot` > 0 in read order, which is not a defined order.) From stored per-strike rows, S for each strike is that row's own `spot`.

**Row set.** One output row per strike K > 0 with OI_c + OI_p > 0.

1. **Leg OI.** From chain rows, OI_c and OI_p are the sums of `oi` over that leg's rows; a missing or non-positive `oi` counts as 0. From stored rows, `oi_call` and `oi_put` are already the leg sums.
2. **Leg gamma.** From chain rows, the largest vendor gamma > 0 among that leg's rows; none if no row has gamma > 0. From stored rows, `gamma_call` or `gamma_put` when it is > 0; NULL or ≤ 0 is none. The handling of more than one row per leg was not part of the audited rule.
3. **Guard, per leg, before averaging.** If |K − S| > 0.05 × S and the leg's gamma > 5e-5, the leg has no gamma. Within 5 % of spot the guard never acts and this rule equals the audited one-gamma rule. Beyond 5 % the per-leg guard is an addition the audit did not test.
4. **Strike gamma.** `gamma_strike` is the mean when both legs have gamma after step 3; the one that has it when only one does; none otherwise. `gamma_legs` is `both`, `call_only` or `put_only` accordingly, and None when `gamma_strike` is none.
5. **Net exposure.** `net_cr(K)` = `gamma_strike` × (OI_c − OI_p) × S² / 1e7, in Crore. It is 0 when `gamma_strike` is none.
6. **Map membership.** `in_map` is true when at least one leg has gamma at step 2, before the guard. (Every output row already has OI_c + OI_p > 0.) A strike with `net_cr` exactly 0 stays in the map.
7. **Gross exposure and band.** `gross_cr(K)` = `gamma_strike` × (OI_c + OI_p) × S² / 1e7, in Crore, and 0 when `gamma_strike` is none. `in_band` is true when |K − S| ≤ 0.05 × S. The band set is the strikes with `in_band` true and `gross_cr` > 0.
8. **Edge arithmetic.** The two distance tests in steps 3 and 7 are done in exact decimal arithmetic on the strike and spot as given, not in floating point. They are complements: a strike is either in the band or beyond the guard distance.
9. **Run figures.** `net_cr` = sum of `net_cr(K)` over the map; 0 when the map is empty. `net_top_share` = max |net_cr(K)| / Σ |net_cr(K)| over the map; None when that sum is 0. `gross_band_cr` = sum of `gross_cr(K)` over the band set; 0 when the band set is empty. `gross_top_share` = max gross / `gross_band_cr`; None when the band set is empty. `gross_hhi` = Σ (gross_cr(K) / `gross_band_cr`)² over the band set; None when the band set is empty. `n_map` = number of strikes with `in_map` true. `n_zero` = number of those with `net_cr` exactly 0.
10. **Not produced.** No flip, regime, zone, expansion probability, max-gamma strike or pin-risk score.
11. **Stored** in `gex_strike_v2` and `gex_run_v2` only. No V1 column is written. Live rows carry `rule_version` `v2-1.1`; rows backfilled from stored rows carry `v2-1.1-gss`.

## 4. Consequences, stated

- **Two gamma methods on the Board until the own-solve work (R9).** The Board Flip is `v_gex_repriced_flip` (ENH-131), labelled "experimental": it has no value on expiry day, and its leg filter (`gamma IS NOT NULL AND gamma <> 0`) drops every leg whose vendor gamma is zero together with its open interest, so it is not independent of the vendor-gamma gap; the effect on the level is unmeasured. A replacement flip study is parked (R6).
- **A run with more than one distinct spot** has V1 output and no V2 output; the `p3b2` presence check flags it. Intended.
- **Shares are not comparable across the Pin switch.** Gross shares are over the 5 % band with gross > 0; `share_of_abs` is over every strike of the run with `gex_cr ≠ 0`.
- **Existing concentration names.** `gex_cycle_history.conc_hhi` is a true Herfindahl of V1 net `share_of_abs` over every ranked strike. `conc_top1_share` (from `v_gex_concentration.hhi_net`) and `gamma_metrics.gamma_concentration` are top-strike shares despite the `hhi_` name. No V2 name uses "hhi" for a top share.
- **Storage.** Per-strike rows roughly double (measured in the fixtures: about 105–176 rows per run per symbol).

## 5. Paths recorded, not covered by V2

- `insert_option_chain_run` — dead: the `payload` and `metrics` columns it writes do not exist (read 2026-11-25).
- `insert_option_chain_batch` (SECURITY DEFINER) — callable by `service_role`, fills `gamma_metrics` through `compute_gamma_metrics_for_run` / `compute_gamma_flip_for_run`; no caller found in the engine repo; `gamma_metrics` rows of 2026-11-23 all carry the Python builder version. Not covered by V2.
- `latest_net_gamma_by_strike`, `latest_gamma_walls`, `latest_top_gamma_strikes`, `latest_atm_neighborhood` — read `option_chain_snapshots.gamma` per leg directly; stay on the per-leg rule; no reader found in the engine repo or the Board source searched.
- `gex_pin_maxpain_history` — no writer since 2026-09-19. If `scripts/backfill_pin_maxpain.py` is ever run, it fills from V1 `gex_cr`; that is consistent because V1 has no break.
- `cleanup_gamma_engine_daily` (job 19) — inactive; stays inactive.
- EXECUTE on `backfill_pin_maxpain_runs`, `cleanup_gamma_engine_data`, `compute_gamma_*_for_run` is open to `anon`/`authenticated`/`merdian_ro`; they run with the caller's rights and those roles hold no INSERT/DELETE on the tables (read 2026-11-25). Hygiene item, not an exposure.
- The regime gate (`trade_allowed`): still written each cycle by `build_trade_signal_local.py`; no scheduled or running consumer on the box or the Windows host (reads 2026-11-24). Register lines that say otherwise are corrected at the S107 close (I-002 row 11).

## 6. Verification before any build is applied (V-2, on the six golden fixture days, no production access)

- **a.** `git diff 934fe44 -- merdian_compute/gamma.py` and every other V1 file is empty; the 313-row contract test passes unchanged.
- **b.** V2 output equals the pin lane's independent implementation of rule v1.1 on all 486 chain runs: membership, `in_band`, `gamma_legs` exact; `gamma_strike` 1e-12 relative; per-strike net and gross 1e-6 + 1e-9·|v|; run net 0.01; shares and HHI 1e-9.
- **c.** Chain-built rows equal stored-row-built rows on the 313 runs present in both (78 / 78 / 78 / 77 / 1 / 1).
- **d.** A dependency listing shows no V1 consumer reads a V2 object and no V2 view reads a V1 exposure column.
- The report counts, over the 486 runs: strikes by `gamma_legs`; legs removed by the guard; in-map strikes with net exactly 0; legs with more than one row; strikes exactly on the 5 % edge. A branch with a count of zero is covered only by the self-test. Known synthetic-only: duplicate leg rows, multi-expiry run, multi-spot run. Three of six fixture days are expiry days (233 of the 313 runs); no fixture day has dte 1–3.

## 7. Not approved by this ADR

Applying any SQL; creating `gex_strike_v2` / `gex_run_v2`; `p3b2` objects; the writer hook; the backfill run; any Board change. Each returns to the operator with the V-2 results.
