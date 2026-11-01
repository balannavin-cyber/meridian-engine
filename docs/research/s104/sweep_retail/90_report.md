# 90 — ADR-032 independent sweep, retail repos (read-only, Phase 1)

Baseline: retail-platform d95caf1, retail-meridian 595ed47 (= products/meridian pointer). STATE.md last green: 0904f295dab33ced1d4854c8d3c203c43a7367ce. Engine pin: merdian_compute @ 4a1d8e181c37887407dcaa41ca3f3d9fdb45bd69 (retail-meridian/compute/pyproject.toml:12), contract v2 / v2.1 (cited, file not in either repo). Nothing was changed, run or committed; no environment files or operator config read; the only writes are this folder.

## Coverage (3 lines)
1. 883 tracked text files (764 platform + 119 meridian, 4,170,531 B), every type, no exclusions except binary images/fonts; 1,374 raw hit lines in 103 files → `10_hits.tsv`.
2. Read by hand: the engine pin chain (pyproject, test_pin, test_surface, golden.py, l3.py, gen-l4.py key parts, engine_ref_compare.py, engine-ref-gate.sh, view-transform-check, classify.py, verify-gates), migrations 0400/0500/0600-1300, board loader/copy/read-sentence/view-model, worker normalize/payload. Not read: 46_mr_views_l4.test.sql (generated, gitignored), the golden cache contents, any engine repo (none cloned), the contract file.
3. **`10_hits.tsv` kind/use columns are assigned by path-and-text rules in a script, not by reading each of the 1,374 lines.** The by-hand files above are reliable; vendored-engine comments and doc prose are bulk-tagged. Treat the counts below as a map and the section files (20-60) as the checked findings.

## Counts by kind × use (from 10_hits.tsv)
```
compare    magnitude     4
compare    pass-through  16
compare    ratio         2
compare    sign          3
compare    unknown       12
copy       unknown       169
dead       n/a           14
dead       unknown       68
fixture    magnitude     26
glossary   display       13
label      display       41
pin        magnitude     23
pin        pass-through  35
pin        ratio         10
pin        sign          10
pin        unknown       226
reader     magnitude     45
reader     pass-through  236
reader     ratio         35
reader     sign          24
reader     unknown       72
recompute  magnitude     4
recompute  pass-through  2
recompute  sign          2
recompute  unknown       6
test       magnitude     5
test       n/a           5
test       pass-through  94
test       ratio         29
test       sign          3
test       unknown       16
writer     pass-through  124
total 1374
```
(`pin/unknown` 226 and `copy/unknown` 169 are comments inside vendored engine files and prose in plan/close docs; `dead` are false positives such as "regex", "is-route-active", lockfile.)

## The unknown bucket, with the question that settles each
1. Does the new engine compute add the scale-B figures as new `GammaMetricsResult` dataclass fields, new `gss_rows` keys, or only as DB columns? Decides whether `test_surface.py:18` (exact ordered field list) and `service.py:23` (`_GAMMA_FIELDS` = all fields) fire on a SHA bump. Settled by: the engine commit's dataclass diff.
2. How does `exact_equal` (L1) treat a key present on one side only? Not read. Settled by: reading its definition in compute/tests.
3. Does anything inside merdian_compute threshold on Γ magnitude (regime, gamma_zone, pin_risk_score, expansion_probability, `derive_core` floors)? Retail stores these outputs (mr_gamma_metrics) and displays pin_risk_score, so a scale change inside the engine could shift them. Settled by: the engine source at the pinned and the new SHA.
4. Is the contract's unit line "₹ Cr per 100 % move" or per 1 %? The glossary (line 235) says per 1 % today. Settled by: contract v2.1 text (engine repo) and the operator's ruling on which is true for the shipped copy.
5. `abs_gex_cr`, `total_pin_gex_cr`, `peak_pin_gex_cr` are view outputs, but the board loader does not select them (loader.ts:93-96 selects only walls, pin_lower/upper/peak_pin_strike, max_pain_strike, flip/status). Will a later UI step show them? Settled by: the operator.
6. `v_pin_board` (9th engine view, uses `x.*`) is md5-gated but has no retail copy. Will retail ever copy it? Settled by: the operator.
7. Prose in P4_plan.md / P4_close.md / H2_close.md (about 170 lines) states units and "₹ Cr"; I did not check each for a unit claim that differs from copy.ts.

## Γ sizes under unexpected names
- `net_gex` (carries Cr, name says nothing): mr_gamma_metrics.net_gex; TS `netGex`, `grossGex`, `localGex`, `strikeGamma`; glossary "Dealer hedging".
- `total_gex` (and `prev_g`): inline Γ curve in mr_v_gex_repriced_flip (…1300:150-183), literal 1e7.
- `peak_gex_cr` (internal to pin zone), `total_pin_gex_cr`, `peak_pin_gex_cr` (outputs), `abs_gex_cr` (rank output); `hhi_net` (ratio, scale-free); `n_contributing` (count).
- `leg_call`, `leg_put` in mr_v_gex_concentration: `abs(gamma_call*oi_call)`, γ·OI without S². Not a Γ size, but a close cousin (mixing risk).
- `gamma_at_pin` and `net_gex` in the O4 DDL (gex_cycle_history, engine_ref_ddl_O4.sql:113,120): engine columns in a frozen copy only.
- `regime` text `LONG_GAMMA` (test literals) and `gamma_zone`: words derived from the sign of Γ.
- Delta-type, listed for mixing: glossary "Delta flow … in rupees crore" (:352); the max-pain views (OI-based, no Γ).
- Per-option γ (NOT Γ): mr_chain_rows.gamma, `ceGamma`/`peGamma`, `abs(s.gamma) > 5e-5`, worker `hasGamma`, Dhan greeks.

## What each retail gate does when the engine ADDS columns (decisive question)
Full table in `20_pin.md`. Summary:
- **Columns added in the engine DATABASE (tables or views), nothing else changed: invisible to every retail gate.** Retail never queries the engine DB. It sees the engine through (a) the SHA of merdian_compute, (b) frozen vendored view files + the O1 md5 snapshot + the O4 scratch DDL, (c) the golden cache fetched by SHA. L1, L2, L3, L4, engine-ref, view-transform and view-headers stay as they are.
- It becomes visible only on a deliberate step:
  - **SHA bump**: `test_pin` (3 literals + pyproject must move together); `test_surface` fails if the new fields are dataclass fields (end or middle; exact ordered list); L3 fails if an existing `net_gex` changed scale (production goldens are scale A); L1/L2 follow the engine and stay bit-identical.
  - **Re-vendored view file**: `ENGINE-REF … MISMATCH` until O1 is re-exported; view-transform UNCLASSIFIED/REFUSED; L4 column-name equality fails if only one side gets the column; GEN-L4 sha changes.
  - **Payload**: new compute fields are forwarded by service.py / payload.ts and **silently dropped** by `mr_write_cycle` (`jsonb_to_record` with fixed columns, 0400:357-375): no error, nothing stored. A retail "new column beside the old" needs a retail migration, both column lists, and view/loader edits.
- Not additive: a change of the *meaning* of `net_gex` / `gex_cr` in place after a pin bump (retail stores them under the old names; the board prints "Net Γ (₹ Cr)"; the glossary already says per 1 %).

## Things I could not check, and why
- Engine source, contract text, any new SHA: no engine clone (scope). Items 1, 3, 4.
- Whether the 486-cycle L1/L2 and L3 are green today: not run (rules). Counts are quoted from docs/P4_close.md.
- 46_mr_views_l4.test.sql and the golden cache data: generated or cache, not read; gen-l4.py was read instead.
- Live Supabase objects (grants, live view definitions, dashboard-made objects): no DB access; migrations only.
- `exact_equal` and l2_compare beyond line 89: partly read.
- No second reviewer on the hit classification (no subagents used).

No fixes, no ranking.

## sha256 of output files (this file excluded; it cannot contain its own hash)
5c53434239c2fbc1c194ac1ff25ae2023a56c58c27e034b8fe15485472fcd459  00_census.txt
27d49792f871af76b141b6a87c737c8efe2238514082250493cbeea642949d27  10_hits.tsv
f2258b919a9aa5fc800222f1ead239909556b80906efce3f6c06af732f5066be  20_pin.md
5cf2e09ca9fc53f77ae43734209ad124ae4493f495688e57c6c310ee7de96472  30_sql.md
f8c4f76cf04cde32640ba2f9d930a201b749ab99dc7e5bf7169fdf2cb1c6adef  40_goldens.md
24f0ef8d8edb22a81b3a1b2553b049dd22555edafdc187baa918b8d68857055e  50_ui.md
49de9459a4979ec58c6a4451325f9e9c21e776b9d423175d7bd43f742012107e  60_constants.md
