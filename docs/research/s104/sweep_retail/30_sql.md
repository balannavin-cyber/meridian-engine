# 30 — database objects (migrations in retail-meridian/supabase/migrations; apps/web copies are byte-identical)

## Tables / functions holding a Γ size (retail's own, not the engine's)
| Object | Γ column | Written by | Notes |
| --- | --- | --- | --- |
| mr_gamma_metrics (20261101000400:77-107) | `net_gex double precision not null` (:86) | mr_write_cycle (:348-365) from `p->'gamma'` via jsonb_to_record, fixed column list | scale = whatever merdian_compute returned; also gamma_concentration (ratio, scale-free), max_gamma_strike (a strike, not Γ), pin_risk_score |
| mr_gex_strike (:109-130) | `gex_cr double precision not null` (:124) | mr_write_cycle (:368-375) from `p->'gss'` | per-strike Γ; the name embeds the unit ("cr") |
| mr_cycle_exact (:420-425) | `to_jsonb(g)`, `to_jsonb(s)` | read-back | **row-to-json of whole rows: a new column on mr_gamma_metrics / mr_gex_strike appears in L2's read-back automatically** (L2's compared field list is fixed, so it would be ignored, not failed) |
| mr_chain_rows.gamma | per-option γ, copied from the broker | mr_write_cycle | NOT a Γ size (per-option) |
| mr_param_num + mr_parameters (13 seeded rows) | none | | parameters: pin_state.*, pin.tau.*, wall.band.*, wall.iv_floor_min. None is a Γ magnitude (all ratios, counts, a σ multiple, an IV floor). Check: `cut -f1,2 O2_parameters.tsv` read in full (13 rows) |
| 41_/43_ pgTAP (copies in apps/web) | literals net_gex 1.5, 111111, 222222, gex_cr 1.5 | | fingerprints and plumbing; unit-blind |

## mr_v_* views (8 retail copies of engine views, plus nothing for v_pin_board)
Transformation applied to each engine view (classify.py): 1 table rename (gex_strike_snapshots→mr_gex_strike, volatility_snapshots→mr_volatility, option_chain_snapshots→mr_chain_rows, index_futures_snapshots→mr_index_futures), 2 user_id additions (+USER-SEED CTE, F11 pin-zone list), 3 get_parameter_num→mr_param_num, 4 security_invoker + REVOKE/GRANT clause, 5 v_*→mr_v_*. Nothing else is allowed: any other hunk is UNCLASSIFIED.

| View (migration) | Γ names inside | Use |
| --- | --- | --- |
| mr_v_gex_strike_walls (…0600) | reads mr_gex_strike (no gex_cr token; picks walls via band/iv_floor params) | magnitude→walls (strike levels out) |
| mr_v_gex_concentration (…0700) | g.gex_cr; hhi_net = max|gex|/sum|gex|; n_contributing `gex_cr <> 0` | ratio (scale-free), sign/zero test |
| mr_v_gex_strike_rank (…0800) | gex_cr, **abs_gex_cr** output column, share and cumulative share, `gex_cr > 0/< 0` → DAMPENING/AMPLIFYING; `gex_cr <> 0` | outputs a Γ magnitude (`gex_cr`, `abs_gex_cr`) plus ratios and a sign label |
| mr_v_gex_max_pain (…0900) | only the run selector (no Γ values) | none |
| mr_v_gex_strike_pin_zone (…1000) | gex_cr, peak_gex_cr, **total_pin_gex_cr (sum), peak_pin_gex_cr (max)**, filter `gex_cr >= tau * peak_gex_cr` (tau 0.30) | outputs two Γ magnitudes; threshold is a ratio to the peak (scale-free) |
| mr_v_gex_pin_maxpain (…1100) | joins the views above; selects peak_pin_strike etc. | pass-through; no Γ column named (checked by grep, no match for gex_cr/_cr) |
| mr_v_max_pain_by_strike (…1200) | none (OI pain, delta-type/oi-based) | not Γ |
| mr_v_gex_repriced_flip (…1300) | **recomputes Γ**: `±N(d1)... / (S·σ√T) · oi · S² / 1e7` summed to `total_gex` over a 201-point spot grid (:150-163); only SIGN CROSSINGS are used (`prev_g<0 <> total_gex<0`, interpolation `s_star`); per-option `abs(s.gamma) > 5e-5` at :69 is γ not Γ | scale-A literal 1e7, but the output (a spot level) is scale-free |

Select-star: **none of the 8 views selects `*`** (pattern `select +\*|\w\.\*|,\s*\*\s` over the 8 files, count 0 each; the pattern fires on `select * from public.mr_worker_alerts` in 43_mr_isolation.test.sql:160 and on `SELECT x.*` in the engine v_pin_board file). `to_jsonb(row)` is used in mr_cycle_exact (above).
`mr_gex_strike` / `mr_gamma_metrics` are read with explicit column lists by the board loader (loader.ts:69,127,135).

## What happens to each if the ENGINE view gains a column
Nothing at all until the operator re-vendors the engine file. After that, per view: (1) engine-ref-gate: MISMATCH vs old O1 (exit 1) until O1 is re-exported; (2) view-transform: UNCLASSIFIED insert hunk until the retail migration is changed; (3) L4: column-name equality assertion fails until the retail view has the same column in the same position (user_id excluded), and the EXCEPT comparison runs on the engine view's column list so a retail view lacking the column raises an error; (4) VIEW-HEADER md5 goes stale when the retail migration is edited. A new column in the *engine base table* (gex_strike_snapshots) is not seen by any of them, because retail's staging tables use O4 DDL and explicit insert lists.
mr_v_* have `security_invoker` and are granted to authenticated/service_role by fixed trailing statements; a changed view must keep that (class 4) or view-transform flags it.
Retail views read `mr_gex_strike.gex_cr` (retail table). If the operator wants retail to show scale B, retail needs its own new column in mr_gex_strike/mr_gamma_metrics (and mr_write_cycle's two column lists, and the views that read gex_cr), or a pin bump that changes gex_cr's meaning in place.

## pgTAP / L4 files that compare with the engine
46_mr_views_l4.test.sql (generated, gitignored) via scripts/gen-l4.py; 41, 43 (plumbing), 44/45 (seed, generated by gen-seed.py). Header test: view-transform-check --headers (docker).
