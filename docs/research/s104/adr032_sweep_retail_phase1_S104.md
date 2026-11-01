# ADR-032 independent sweep — retail box, Phase 1 record (S104, 2026-10-31)

Run: Claude Code in tmux `s103_sweep_retail` on the retail sandbox box (`ubuntu@ip-172-31-30-166`), `~/retail-platform` @ `d95caf1` (1 untracked), `~/retail-meridian` @ `595ed47` (clean); read-only, no DB access, no engine clone; 5 min 54 s. Prompt `cc_prompt_adr032_sweep_retail_box.md` sha256 `c9343152…2505` (delivered by base64 heredoc — the box has no `aws`; a plain heredoc paste through the terminal stripped `#` headings and blank lines, base64 did not). STATE.md last green `0904f295…`; engine pin `merdian_compute @ 4a1d8e1` (`retail-meridian/compute/pyproject.toml:12`); contract cited as v2 / v2.1 but **the contract file is in neither retail repo**.

Deliverable: `~/retail-platform/scratch/s103_sweep/` → `s3://meridian-engine-deploy/s104/s103_sweep_retail_phase1.tgz` (presigned PUT from the box with `curl`; bucket region **`eu-north-1`**), sha256 `591c8b4a12c11045c61c3f1be987fe601e347105bc26b8ef4b6868c19879beea` (box = Local = this session). Per-file: 00_census `5c534342…`, 10_hits.tsv `27d49792…` (1,374 rows), 20_pin `f2258b91…`, 30_sql `5cf2e09c…`, 40_goldens `f8c4f76c…`, 50_ui `24f0ef8d…`, 60_constants `49de9459…`, 90_report `a890145b…`. `90_report.md` kept verbatim in PK as `claude/adr032_sweep_retail_90_report.md`. **Git home at the next close: `docs/research/s104/sweep_retail/` in the engine repo (whole folder).** Phase 2 not run (the study covers retail only as M7; a diff would be thin — operator's call).

## Coverage
883 tracked text files (764 platform + 119 meridian, 4.17 MB), every type; 1,374 hit lines in 103 files. Classification of `10_hits.tsv` is rule-based; the by-hand files 20–60 are the checked findings. Not read: `46_mr_views_l4.test.sql` (generated), golden cache contents, live Supabase objects, the engine repo.

## The decisive answer — what retail gates do when the engine ADDS columns
- **Columns added in the engine database (tables or views), nothing else changed: invisible to every retail gate.** Retail never queries the engine DB; it sees the engine only through (a) the `merdian_compute` SHA, (b) frozen vendored view files + the O1 md5 snapshot + the O4 scratch DDL, (c) the golden cache fetched by SHA. L1/L2/L3/L4, engine-ref, view-transform, view-headers all stay green. → **ADR-032 S2a–S2c (additive DB columns) is invisible to retail by construction.**
- It becomes visible only on a deliberate retail step: **SHA bump** (`test_pin`: 3 literals + pyproject move together; `test_surface.py:18` fails if the new fields are dataclass fields — exact ordered list; L3 fails if an existing `net_gex` changes scale in place — production goldens are scale A); **re-vendored view file** (`ENGINE-REF … MISMATCH` until O1 re-export; view-transform UNCLASSIFIED/REFUSED; L4 column-name equality; GEN-L4 sha); **payload**: new compute fields are forwarded by `service.py`/`payload.ts` and **silently dropped by `mr_write_cycle`** (`jsonb_to_record` with fixed columns, migration 0400:357-375) — no error, nothing stored. A retail "new column beside the old" needs a retail migration, both column lists, and view/loader edits.
- **Not additive-safe:** changing the *meaning* of `net_gex`/`gex_cr` in place after a pin bump — retail stores them under the old names.

## Retail unit state today (a live inconsistency, MR item)
- Stored `mr_gamma_metrics.net_gex` / `gex_cr` are **scale A** (copied unchanged from compute output at pin `4a1d8e1`).
- **`glossary_v0.2.json:235` already words the unit as "each 1 %" (scale B)** while the board label is `Net Γ (₹ Cr)` — one literal at `copy.ts:23`, not shared with the glossary text. Glossary says B, data is A, label says neither. → ruling needed at MR-S4: which is true for the shipped copy (ties to engine S2 timing).

## Γ sizes under unexpected names (retail)
`netGex`, `grossGex`, `localGex`, `strikeGamma` (TS); `total_gex`/`prev_g` (inline Γ curve in `mr_v_gex_repriced_flip`, migration 1300:150-183, literal `1e7`); `peak_gex_cr` (internal), `total_pin_gex_cr`, `peak_pin_gex_cr`, `abs_gex_cr` (view outputs the board loader does **not** select — `loader.ts:93-96`); `gamma_at_pin`/`net_gex` in the O4 DDL frozen copy. **Not Γ but close cousins (mixing risk):** `leg_call`/`leg_put` in `mr_v_gex_concentration` = `abs(gamma·oi)` without S²; per-option `gamma`, `ceGamma`/`peGamma`, `abs(s.gamma) > 5e-5`; delta-flow glossary entry (:352).

## Open questions CC could not settle (need engine side or operator)
1. Will the engine's S2 add scale-B figures as `GammaMetricsResult` dataclass fields / `gss_rows` keys, or DB columns only? Decides whether `test_surface`/`_GAMMA_FIELDS` fire on the next SHA bump. (Answer from the fallback plan: S2 is DB columns + writer; if W1 adds dataclass fields, retail's `test_surface` breaks on the bump — must be in the S2 design.)
2. How `exact_equal` (L1) treats a key present on one side only — not read.
3. Does anything in `merdian_compute` threshold on Γ magnitude (regime, gamma_zone, pin_risk_score, expansion_probability, `derive_core` floors)? (Engine sweep + study answer: no — sign and ratios only; `regime_sign(eps=2.5e5)` is research-only.)
4. Contract unit line vs glossary — see above.
5. `abs_gex_cr`/`total_pin_gex_cr`/`peak_pin_gex_cr` unselected by the loader: will a later UI step show them? Operator.
6. `v_pin_board` (9th engine view, `x.*`) is md5-gated but has no retail copy — will retail copy it? Operator.
7. ~170 prose lines in P4_plan/P4_close/H2_close state units — not checked line by line.
