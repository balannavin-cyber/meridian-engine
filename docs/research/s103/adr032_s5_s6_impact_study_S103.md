# ADR-032 §5 impact study and §6 change roadmap — DRAFT for ruling (S103, 2026-10-31)

> **Form note (S103 doc-close, TD-S103-NEW-10).** Every view md5 in this file is `md5(pg_get_viewdef(oid))`. The rule-25 form (CLAUDE.md) is `md5(pg_get_viewdef(oid, true))`; the S104 engine sweep's md5s are in that form, so all 19 differ from these in form only — no view changed. A rebuild check must use one form throughout and re-read live. Function md5s (`prosrc`) are form-independent.

Answers the two owed sections of `claude/ADR-032-DRAFT-gex-stored-unit.md` (D2–D5 stay PROPOSED until ruled).
Evidence: code search of `meridian-engine` at `c11b564` and `meridian-connect` at `6f14a92` (read by me, 2026-10-31, then **repeated with wider patterns** — other spellings, non-Python files, every `1e7`, every `.rpc(` name); live reads by the operator in the SQL editor, 2026-10-31 07:1x–07:5x IST: views with `pg_get_viewdef` md5, functions with `prosrc` md5, tables with sizes, `net_gex` magnitude by month, `hist_gamma_metrics` scale split, first/last `ts` per symbol, columns under other names, pg_cron jobs, triggers, indexes, column comments, `gamma_metrics.raw` keys. **Not read:** the retail repos (`retail-platform`, `retail-meridian`) — they pin `merdian_compute` by SHA and the retail contract states the unit (below); the other Lovable projects on the same database; the target table of `insert_option_chain_batch`.

## 1. The scales that exist (read, not assumed)

| Scale | Where | Evidence |
|---|---|---|
| **A — stored, ₹ Cr per 100 % move** (`γ·OI·S²/1e7`) | `gex_strike_snapshots.gex_cr`, `gamma_metrics.net_gex`, `gex_cycle_history`, `gex_pin_maxpain_history`, the three copy tables, every `v_gex_*` | one production point: `merdian_compute/gamma.py:54` `base = gamma * oi * (spot ** 2) / 1e7`. NIFTY `gamma_metrics` median \|net_gex\| by month: Jun 1.61M, Jul 1.40M, Aug 1.73M, Sep 1.02M, Oct 1.02M — stable, no unscaled month |
| **B — per 1 %** (A × 0.01) | the seven `_1pct` wrapper views (D1, live 2026-10-30), `v_dealer_flow_sim.flow_cr` at ±1 % | S102 round; wrappers `security_invoker`, md5s below |
| **C — raw, no `/1e7`** (A × 1e7) | `hist_gamma_metrics.net_gex` (183,872 rows, 2025-04 → 2026-03) | median \|net_gex\| 1.0–2.1e13 every month (max 1e15–2.6e16): ≈ 1e7 × scale A. Answers inventory §5 Q1 for the bulk of the table: it is **unscaled**, matching `fill_gamma_concentration.py:72,104` ("table stores unscaled"). `backfill_gamma_metrics.py:83` divides by 1e7 and skips days that already have rows (`:133`), so its rows, if any were written, would be scale A: **settled by the split query (07:4x): 182,430 of 182,461 non-null rows are ≥ 1e9; the 31 below it are 0–11 a month across 2025-04 → 2026-03 (June 2025: 0) — scattered near-zero nets, not whole days of small values. One scale (C) throughout.** |
| **D — legacy proxy** (γ·OI or Σγ, no S², no `/1e7`) | SQL functions `compute_flip_level_v3`, `compute_gamma_metrics_for_run`; `compute_options_regime`'s ±0.0005; **`insert_option_chain_batch`** (selects `net_gex` and `gamma_concentration` from a source `c` — presumably `compute_gamma_metrics_for_run`, not confirmed — and uses them in an insert column list and an `UPDATE … net_gex = v_net_gex`; lines 6, 79, 100–102, 122; target table not read); four views `latest_atm_neighborhood`, `latest_gamma_walls`, `latest_net_gamma_by_strike`, `latest_top_gamma_strikes` (columns `net_gamma`, `abs_net_gamma`; found by the second pass, definitions and md5 not captured) | function bodies read; a different quantity, not rescaled by any option below. **No code in either repo calls any of them** (`.rpc(` names in the code: only `update_parameter`, `get_hocs_distinct_expiries`) |
| **E — delta-type** (`oi·S/1e7`) | DEX views, ∂Δ/∂t, ∂Δ/∂σ | out of scope, must not be rescaled (inventory §2) |
| **F — A × 100** (`γ·OI·S²·100/1e7`) | `canonical_ob_gamma_zone.py:178,204`, `canonical_ob_gamma_zone_bs.py:323` (ICT order-block research scripts) | found by the `1e7` sweep; used for shares of a total (zone mass fraction), so a rescale of the stored unit does not reach them |

Inventory §5 Q2 (rows before 2026-05-11, TD-NEW-3, unscaled): **none live for either symbol** — `gamma_metrics` starts NIFTY 2026-06-12, SENSEX 2026-06-10; `gex_strike_snapshots` starts 2026-05-25 (both) and runs to 2026-10-30 10:10 UTC. `gamma_metrics.raw` carries no Γ size (keys: `builder`, `builder_version`, `gamma_zone_policy`, `otm_oi_snapshot` = an OI quantity).
Inventory §5 Q3 (OI unit of `backfill_gamma_metrics_to_main.py`'s vendor source): still unstated; the script carries its own copy of the formula (`:224`, `signed_gex_cr = sign * gamma * oi * (spot ** 2) / 1e7`) — a second writer outside `merdian_compute` (TD-S101-NEW-5 class).
Inventory §5 Q4 (sign conventions): untouched; keep out of any rescale.

## 2. Writers of a scale-A value (a change at D2 lands here)

| # | Writer | Writes | Change at D2 | Test | Owner |
|---|---|---|---|---|---|
| W1 | `merdian_compute/gamma.py:54` `signed_gamma_exposure` | the per-strike `gex_cr` and the sum `net_gex` (via `build_gss_rows`, `compute_gamma_core`) | one factor: `/1e7` → `* 0.01 / 1e7` | step 24/25 (import purity, contract vs golden rows), golden replay 486/486 regenerated, P3a invariants, a new per-1 % cell | engine |
| W2 | `compute_gamma_metrics_local.py` (imports W1) | `gamma_metrics.net_gex`, `gex_strike_snapshots.gex_cr` | none beyond W1 | as W1 | engine |
| W3 | `write_gex_cycle_history_local.py` + `merdian_compute/cycle.py:81` | `gex_cycle_history.net_gex`, `gamma_at_pin` (= `gex_cr` of the rank-1 strike) | none beyond W1 (copies through) | step 25 | engine |
| W4 | `backfill_pin_maxpain_runs(...)` (DB function, md5 `df1ffdf9…`) and the pin/accel views it mirrors | `gex_pin_maxpain_history.peak_pin_gex_cr` — **a static table: one backfill of 2026-05-25 → 2026-09-18 (11,795 rows, S80; the script hard-codes the window), no live writer; last `ts` 2026-09-18 09:50 UTC (read 2026-10-31)**, so D2 needs no live write for it | follows `gex_strike_snapshots.gex_cr`; the τ comparison `gex_cr >= tau * peak` is a ratio, unchanged | per-view equality before/after on one run | engine |
| W5 | copies: `build_market_state_snapshot_local.py:191`, `build_trade_signal_local.py:541/880`, `compute_structural_divergence_local.py:330`, `backfill_market_state.py:67/259` (→ `hist_market_state.net_gex`, 181,848 rows) | `market_state_snapshots`, `signal_snapshots`, `structural_divergence_snapshots`, `hist_market_state` | none (copy through) — but each table then holds two scales across the break | dated-break registration | engine |
| W6 | **copies of the formula outside `merdian_compute`** (every `1e7` in the repo, swept): `replay/replay_compute_gamma_metrics.py:88`, `backfill_gamma_metrics.py:83`, `backfill_gamma_metrics_to_main.py:224`, `backfill_hist_greeks.py` (`CR_SCALE`, vectorised), `measure_rate_sensitivity.py:107`; SQL recompute copies `v_gex_repriced_flip` (sign-crossing only), `p3b_sweep()` / `sql/2026-10-12_s96_p3b_invariant_checks.sql:104`; test copies `tests/test_p3a_invariants.py:38`, `tests/test_dex_recompute.py:174` (anchors the scale) | backfills / replays / hist / invariant recompute | **must change in step with W1** or they write or compare the old scale (the TD-S101-NEW-5 hazard). The two **invariant recomputes** are the sharp ones: I1 compares a recompute with the stored `net_gex`, so it FAILS until its copy moves | grep gate: no `/ 1e7` outside `merdian_compute`; the P3a/P3b fixtures re-run | engine |
| W7 | `v_gex_greeks_l2_leg/_net/_strike` (S² basis, `gex_drift_*` / `*_cr_per_*`) | per-strike and net ∂Γ/∂t, ∂Γ/∂σ | same missing 0.01: change the view bodies | the T1-style equality per view | engine (SQL) |

## 3. Readers of a scale-A value, by what they do with it

**Sign only — unaffected by any rescale (read in code):** `compute_gamma_core` regime (`net_gex >= 0`), flip side (`gamma.py:278`), pin-risk base (`:405`); `detect_structural_manipulation.py:491` (`net_gex <= 0`); `compile_market_environment_local.py` regime label; `backfill_expiry_outcomes.py`, `relate_ambient_to_open_local.py` (regime words); SQL `compute_expansion_probability` (`net_gex < 0`); `compute_options_regime` (±0.0005 on a magnitude of thousands is a sign test); `v_dealer_flow_sim.direction`.

**Ratio — unaffected (a constant factor cancels):** `gamma_concentration`, `share_of_abs`, `cum_share_of_abs`, HHI, runner-up ratio, `v_gex_concentration`, `v_gex_strike_rank` shares, pin/accel τ × peak (`0.3 * peak_gex_cr`), `held_for_cycles` inputs.

**Compensating — must change with the writer:** `v_dealer_flow_sim.flow_cr = −net_gex × pct` (pct 0.005/0.01/0.02): with scale B stored, the factor becomes `pct / 0.01`; the view's md5 in §4 is the baseline. Test: `flow_cr` at ±1 % equals `∓net_gex` per 1 % on the same run (the S102 T2 pattern).

**Magnitude — a number is shown or compared (these are the real impacts):**

| # | Reader | What it does | Change at D2 | Test | Owner |
|---|---|---|---|---|---|
| M1 | Board A1–A10 (inventory §3A) | shows the value | none after D1: the board already reads `*_1pct`; the wrappers become identity | S102 T1–T5 re-run | board |
| M2 | in-app manual figures (inventory §3D) | quotes magnitudes | already restated ÷100 (v0.5); text unchanged at D2 | grep | board / docs |
| M3 | **`generate_pine_overlay.py:334–364`** — prints `peak +…K Cr`, `zone +…K Cr`, `trough …K Cr` from `v_gex_strike_pin_zone` / `_accel_zone` (`/1000`) | **a shown magnitude on the TradingView overlay — not in the S102 inventory** | labels fall 100× (a "K Cr" would read in tens): relabel or re-scale; operator ruling on wording | generate once before/after on one run, diff | engine |
| M4 | `backfill_hist_greeks.regime_sign(eps=2.5e5)` and `validate_hist_greeks_flat_r.regime_sign(eps=2.5e5)` | a **magnitude cut-off** on `net_gex` in stored units | only if they are ever pointed at post-D2 rows; they act on hist values (scale C/A) | pin by comment; no live consumer | research |
| M5 | `backfill_gamma_metrics_broken_window.py:72` `NETGEX_MAX_CR = 1_000_000`; `verify_td_new_3_net_gex_unit.py:124` `100 < \|net_gex\| < 1_000_000`; `phase0b_p5_pinned_proxy_v2.py` `\|net_gex\| > 1e9` | sanity bounds in stored units | one-off scripts; bounds would be wrong on scale B — mark retired or re-bound | none live | research |
| M6 | P3a (`tests/test_p3a_invariants.py:67`) and live P3b (`p3b_sweep()` md5 `af57a99c…`, `p3b_invariant_checks`) — `abs(Σ gex_cr − net_gex) > 0.01` | an **absolute** tolerance in stored units, **and** a recompute copy of the formula (W6) | the recompute must move with the writer; the 0.01 is then 100× looser in relative terms: re-derive (0.0001). The `gex_strike_snapshots.run_id` column comment states the invariant ("SUM(gex_cr) per run_id == gamma_metrics.net_gex ±0.01 Cr") — update it | mutant that perturbs by 0.5 % must still FAIL | engine |
| M7 | retail contract (`docs/interfaces/retail_compute_contract.md` §2, lines 65–66: "`gex = gamma × oi × spot² / 1e7` (₹ crore)"), §8 view md5 table, the S101 golden rows, retail's SHA pin | states the unit; golden rows hold scale-A values | **contract v3**, goldens regenerated, retail re-pin (retail repos not read) | step 25; retail's own L1/L4 (486 cycles bit-identical) | engine + retail |

**Pass-through copies (no use of the value in this repo):** nine live views carry `net_gex` — `latest_gamma_metrics`(+`_v2`), `latest_signal_inputs`(+`_v2`), `latest_signal_snapshots`, `signal_outcome_research_v1/_v2`, `wcb_signal_validation_v1/_v2` — and **no code in the engine or board repo reads any of them** (grep of `.py/.ts/.tsx/.js/.mjs/.sh`; the only hits for the function names are the Python `compute_expansion_probability`, a different object). **But `pg_stat_statements` (stats since 2026-08-18 03:04 UTC, read 2026-10-31) shows live readers outside both repos, all as role `service_role`:** `wcb_signal_validation_v2` — 632, 490 and 236 calls in three query shapes (`symbol = … AND ts >= …`, a `spot` column read, `select *`); `latest_signal_snapshots` — 100 calls in the same shape, plus a few more; every other legacy view, `study_recon_accel` / `study_recon_pin` and `latest_gamma_metrics_v2`, `latest_signal_inputs`, `latest_atm_neighborhood`, `latest_gamma_walls`, `signal_outcome_research_v1`, `wcb_signal_validation_v1` show **one call each** (a `LIMIT/OFFSET` page or `EXPLAIN (FORMAT JSON) SELECT $1 FROM …`, the shape of a dashboard table browse). `supabase_admin` shows one-call `CREATE VIEW` / `CREATE FUNCTION` / `GRANT` / `ALTER VIEW … OWNER` statements for the same objects (including `insert_option_chain_batch`, `compute_flip_level_v3`, `latest_net_gamma_by_strike`) — consistent with a schema restore or migration replay on or after 2026-08-18. **Who the `service_role` reader of `wcb_signal_validation_v2` and `latest_signal_snapshots` is, and whether it is still running, is unknown** (it is in no repo read here; `pg_stat_statements` carries no last-call time in this read). Both views pass `net_gex` through unchanged, so the additive plan does not touch them, but they are **not** retirement candidates until the reader is named. Other apps on the same database were not read — the Lovable projects *Live Sheet Sync*, *Market Breadth View* and *Sheet Sync Live* (Projects page, 2026-10-31) and the retail repos could still query them. Likewise no code calls the SQL functions `compute_options_regime`, `compute_expansion_probability`, `compute_flip_level_v3`, `compute_gamma_metrics_for_run`. They are candidates for a retirement TD, not a D2 task. `hist_market_state` is read by ~10 research scripts (`experiment_*`, `build_hist_pattern_signals*`) for regime and `atm_iv`, not for magnitude (grep; the scripts' `net_gex` use not read line by line).

**Research artefacts** (P1, P1c, P2, R2.4 `score.py`, the S72 SQL): use sign and ratios or are pinned to the day they ran. Unaffected unless re-run against post-break rows without registering the break.

## 4. Live md5 captures (rule 25) — the inventory §4 precondition, now met

Captured by the operator's read; the five the inventory listed as having no md5 (`v_gex_abs_exposure`, `v_gex_strike_rank`, `v_gex_concentration`, `v_gex_net_gamma_river`, `v_dealer_flow_sim`) are now recorded. Functions: `p3b_sweep` `af57a99c11fb83cf43872721c71b3ff9` (len 11,293); `backfill_pin_maxpain_runs` `df1ffdf9d64f67ae371b15d05e09cd89` (len 4,174). These are `pg_get_viewdef` / `prosrc` md5s, not the file md5s the retail contract §8 table pins.

| View | `pg_get_viewdef` md5 (live, 2026-10-31 07:1x IST) |
|---|---|
| `v_gex_abs_exposure` | `3ae144c73e4191f4c906709aa7b5d5a0` |
| `v_gex_net_gamma_river` | `8f7bb678085c9a2c41d7b37ee8937204` |
| `v_gex_strike_rank` | `9cc07f97e0b7862e265d5422439d304c` |
| `v_gex_concentration` | `5c075092325391d869b3397bcdca832a` |
| `v_dealer_flow_sim` | `166948d6c7429d5c8765bf48c8f58d3d` |
| `v_gex_strike_terrain` | `25f0fd7d088426b8458a8e3f0e2fddcb` |
| `v_pin_board` | `0cf9c82f1ad5090dd3bc615e8fe42004` |
| `v_gex_greeks_l2_net` | `dd74b2b79d6ed46fd259e8e55059697f` |
| `v_gex_greeks_l2_strike` | `8cbd78e543e8eb77eaf4ef87bb5d758b` |
| `v_gex_greeks_l2_leg` | `e66be9f4aee80c6e981ba1774f6d0228` |
| `v_gex_strike_pin_zone` | `2503e61efde43af0f5f747339087deca` |
| `v_gex_strike_accel_zone` | `c34bc2a228d615bc63080425805ff69a` |
| `v_gex_abs_exposure_1pct` | `c0c59ecf0921f50ee245311bb8abe966` |
| `v_gex_net_gamma_river_1pct` | `44813e088b92024e01a4b08d223e5745` |
| `v_gex_strike_terrain_1pct` | `c8a5624e1dffa0309f3b55499de99c4f` |
| `v_gex_greeks_l2_net_1pct` | `528ee96cced70676c522252c7a16e463` |
| `v_gex_greeks_l2_strike_1pct` | `bbf3f693d3e3e6d8256de9878ac0e798` |
| `v_gex_strike_snapshots_1pct` | `d45a16a29eb2c3ab5f5ebf45382cb3da` |
| `v_gamma_metrics_1pct` | `ed2e9a53c32a683ecf60f5dd8d27a359` |

## 5. D3 — history: volume and time (measured)

| Table | Rows (est.) | Size | In-place conversion cost |
|---|---|---|---|
| `gex_strike_snapshots` | **2,102,679** | **824 MB** | a full rewrite: ~2.1M new row versions on a table the live writer inserts into every 5 min; temporary bloat ≈ the table's own size until vacuum. The table carries **8 indexes** (read live), none on `gex_cr`; an UPDATE is HOT only where a page has room, so on a full 824 MB table most rows would write an entry into every index (up to ~17M index entries). Two of the eight are a duplicate pair, `idx_gss_symbol_ts` = `ix_gex_strike_snap_sym_ts` (`(symbol, ts DESC)`; TD-S72-NEW-4) |
| `gamma_metrics` (+`_shadow`, `_replay`) | 14,256 (+1,952, +144) | 37 MB | small |
| `hist_gamma_metrics` | 183,872 | 46 MB | small — but it is scale C (×1e7), a different conversion factor (÷1e9 to reach B) |
| `hist_market_state` | 181,848 | 45 MB | small, scale unstated |
| `signal_snapshots` | 24,397 | 43 MB | small |
| `structural_divergence_snapshots` | 12,975 | 15 MB | small |
| `gex_pin_maxpain_history` | 11,795 | 3 MB | small |
| `gex_cycle_history` | 2,787 | 2 MB | small |

Only `gex_strike_snapshots` is large. The dated-break alternative converts nothing.

## 6. Change roadmap — least impact first (DRAFT; each step gated on its test, S90-J window where a writer changes)

0. **Done:** D1 wrappers live; board reads `*_1pct`; md5 captures above.
1. **Registration first (no code; also D4):** **CORRECTED 2026-10-31 08:57 IST (S1 rehearsal):** one comment does exist on the eight Γ targets — `gex_strike_snapshots.gex_cr` = "Signed Cr. Positive=dampening (dealer long). Negative=amplifying (dealer short)." (a sign note with no unit base). The earlier statement here that none existed on `gex_cr` was wrong (the earlier live read reported none; why it missed this one was not established); `signal_snapshots`, `structural_divergence_snapshots` and `hist_gamma_metrics` were first checked at that point, and the 08:57 query over all eight targets returned only the `gex_cr` row, so the other seven carry none. The other related comment is the invariant text on `gex_strike_snapshots.run_id`. D4 therefore extends one comment (original text kept verbatim) and creates seven. Live scheduling is one `pg_cron` job (`p3b_invariants` → `SELECT public.p3b_sweep()`) and there are no triggers on any Γ table.
   **Then the registration:** a dated unit-break record (Rule-13 style) — one table row or `data_contamination_ranges`-shaped entry: "before T: scale A; from T: scale B" per Γ column. **Decide D3 here.**
2. **Writers, additive:** W1 (+ W6 copies in the same bundle) writes a **new nullable column** beside the old (`gex_cr_1pct`, `net_gex_1pct`, `gamma_at_pin_1pct` …) — `ALTER TABLE … ADD COLUMN` on `gex_strike_snapshots` is metadata-only; old columns keep writing unchanged. No reader moves.
3. **Wrappers repointed:** each `_1pct` wrapper redefined from `col × 0.01` to the stored new column (`CREATE OR REPLACE`, same output) — **the board needs no change**; per-view equality `old × 0.01 = new` on every row of the latest run, then md5 re-capture.
4. **Compensating and derived views:** `v_dealer_flow_sim` factor, `v_gex_greeks_l2_*`, pin/accel zone views (ratios unchanged), `p3b_sweep` tolerance, P3a tolerance (M6), `generate_pine_overlay.py` labels (M3, wording ruling), contract v3 + goldens + retail re-pin (M7).
5. **Retire** the old columns and the D1 wrappers only after a stated quiet period; rename or alias as ruled.
Each step: offline test with a mutant, replay before vs after, `/staging/` read before any board change, written rollback (given only in a refusing block, in its own message).

## 7. Rulings this study needs (my recommendation in each)

| # | Ruling | Recommendation |
|---|---|---|
| 1 | **D2 form:** additive new columns (steps 2–3) or an in-place factor change at W1 | **Additive.** The in-place change makes every Γ table hold two scales at once with no reader-visible marker. The additive route leaves the board and every reader untouched until each one is moved. **A concrete hazard of the in-place route (read):** the legacy pages alias `net_gex` and `gex_cr` to the `_1pct` columns (`queries.ts:43,210,392`) and every Board surface reads the `*_1pct` wrappers (× 0.01). If the writer's scale changes in place, each wrapper multiplies an already-per-1 % value and the board shows numbers 100× too small until the wrappers are redefined — the writer (a box deploy) and the wrappers (SQL) cannot switch at the same instant. The additive route has no such window. |
| 2 | **D3:** convert history, or a dated break | **Dated break everywhere** (one registered date), no conversion. Only `gex_strike_snapshots` is large, but a *partial* conversion creates several boundaries; a break creates one. Sign and ratio studies are unaffected; magnitude studies must scale across it. |
| 3 | **`hist_gamma_metrics` (scale C):** leave, convert, or retire | **Leave as is and COMMENT its scale** (D4): it is ≈ 1e7 × A, not read by the board, and studies use it for sign and ratios. |
| 4 | **Pine overlay labels (M3)** | Relabel to per-1 % with the unit named; operator ruling on wording. |
| 5 | **Legacy objects** — nine `net_gex` pass-through views, four `latest_*` gamma views, `insert_option_chain_batch`, four legacy SQL functions, tables `study_recon_pin` (141 rows) and `study_recon_accel` (not sized). **Amended by the `pg_stat_statements` read:** no repo reads them, but `wcb_signal_validation_v2` and `latest_signal_snapshots` have a sustained `service_role` reader (hundreds of calls) | File one retirement TD, kept out of D2, **whose first step is to name that reader**; the rest show one dashboard-style call each and are the real candidates. Nothing is dropped before the other Lovable apps and the retail repos are checked. |
| 6 | **Scope of D5** (√τ) | unchanged: out of scope (R26). |

## 8. What this study does not establish

Closed by the second pass: `hist_gamma_metrics` scale (one scale, C); SENSEX history (June 2026); `study_recon_pin` (a 141-row study table; no code reads it, and its sibling `study_recon_accel` is the same); `insert_option_chain_batch` (uses a proxy-scale `net_gex`; no caller in code — its source `c` and target table remain unconfirmed). **Still open:** the identity and recency of the `service_role` reader of `wcb_signal_validation_v2` / `latest_signal_snapshots` (re-run the `pg_stat_statements` read after Monday's session and compare `calls`: a rise means it is live); the retail repos (M7 beyond the contract text) and the other Lovable projects on this database (*Live Sheet Sync*, *Market Breadth View*, *Sheet Sync Live*) — either could read the pass-through views; the target table of `insert_option_chain_batch`; definitions and md5 of the four `latest_*` gamma views; the line-by-line `net_gex` use in the ~10 `hist_market_state` research scripts. None changes the order in §6; the first two should be answered before any retirement TD is executed and before step 2 ships.
