# 20 — the engine pin (read from files; nothing run)

Repos: retail-platform d95caf1; retail-meridian 595ed47 (platform submodule pointer = 595ed47). STATE.md "last green commit": 0904f295dab33ced1d4854c8d3c203c43a7367ce
(STATE says it stays 0904f29 until CI Verify is green on PR 36's head; HEAD d95caf1 is the PR 36 merge, not yet recorded as green).

## What is pinned
| What | Value | Where |
| --- | --- | --- |
| merdian_compute | `git+https://github.com/balannavin-cyber/meridian-engine@4a1d8e181c37887407dcaa41ca3f3d9fdb45bd69` | retail-meridian/compute/pyproject.toml:12 |
| Same SHA, repeated | `ENGINE_SHA = "4a1d8e18..."` | compute/tests/test_pin.py:7, compute/tests/golden.py:16, scripts/gen-l4.py:25 (3 literals, must agree; gen-l4 says so in a comment) |
| Contract | "contract v2" (compute tests/CLAUDE.md §1,§3,§4,§5,§10) and "contract v2.1 section 8" (view order in MANIFEST.txt). The contract file itself is NOT in either repo (engine-side); only citations. | compute/tests/*, CLAUDE.md:13-14, MANIFEST.txt:1 |
| Interpreter | CPython 3.11 pinned (bit identity) | test_pin.py:12 |
| Engine view files | 9 files at 4a1d8e1 with git blob sha + sha256 + bytes | docs/engine_ref/4a1d8e1/MANIFEST.txt |
| Live view md5 snapshot (O1) | def_length + md5(pg_get_viewdef) for 9 views, exported once from production | docs/operator_exports/O1_live_md5.tsv, SHA256SUMS |
| Engine tables as scratch DDL (O4) | gex_strike_snapshots (gex_cr numeric NOT NULL), gex_cycle_history (net_gex, gamma_at_pin ...), option chain, vol, futures | docs/operator_exports/engine_ref_ddl_O4.sql |

## engine-ref files and md5s (O1; md5 of pg_get_viewdef, not of the file)
v_gex_strike_walls 4664 8135c42b..., v_gex_concentration 2140 c4cf15aa..., v_gex_strike_rank 4002 0ab189a4..., v_gex_max_pain 3088 3d067c67...,
v_gex_strike_pin_zone 3523 89c9ac6a..., v_gex_pin_maxpain 2577 0d7d5258..., v_max_pain_by_strike 4028 3d0ed5cb..., v_gex_repriced_flip 10260 58ad6ba8..., v_pin_board 2922 9a827e81...
(Full md5s in O1_live_md5.tsv.) Retail copies exist for 8; **v_pin_board is vendored and md5-gated but has no retail copy** and its body uses `SELECT x.*` (2026-10-08_s92_v_pin_board.sql:133).

## Where the unit is stated
- In retail, no file states "per 100 %" or "per 1 %" for a stored Γ. Pattern `per 1 ?%|per 100 ?%` over all 883 files hits exactly: packages/glossary/data/glossary_v0.2.json:235 ("each 1 % the index moves", i.e. scale B wording) and nothing else.
- `1e7`: engine file 2026-09-25_s83_v_gex_repriced_flip.sql:273-286 ("gamma * oi * S^2 / 1e7, PE negated ... Division by 1e7 is the Crore convention") and the retail copy 20261101001300_mr_v_gex_repriced_flip.sql:160 (also the apps/web copy). 2026-09-15_s79_v_gex_concentration.sql:132 ("unscaled 1e7 convention", prose).
- Unit text: board copy.ts:23 `Net Γ (₹ Cr)`; read-sentence.ts:4 "Aggregate Γ in ₹ crore"; docs/P4_plan.md:209 "Units: ₹ crore". The contract's own unit lines are in the engine repo and could not be read.
- Hence: stored values (mr_gex_strike.gex_cr, mr_gamma_metrics.net_gex) are scale A by provenance (copied unchanged from compute output); the one user-visible words about the unit that mention a percentage (glossary 235) say scale B. Both statements exist today.

## Gates, and what each does if the engine ADDS columns
All of these gates are static: they compare files in this repo with other files in this repo, or with the O1/O4 exports, or run the vendored engine files in a throwaway container. **None connects to the engine's database or repo at verify time**, except golden.py/gen-l4 fetching the golden cache by SHA.

| Gate (where) | Reads | Extra column at END of an engine view / table | Extra column in the MIDDLE | Changed values in an existing column |
| --- | --- | --- | --- | --- |
| compute pin test_pin (SHA) | installed merdian_compute commit | no effect until the SHA is bumped | same | same |
| test_surface RESULT_FIELDS / SIGNATURES (compute/tests/test_surface.py:18-22) | `dataclasses.fields(GammaMetricsResult)` as an ordered list, exact equality | **FAILS** on bump if the new Γ columns are new dataclass fields (end or middle; also on reorder). "A re-pin that changes any of it fails here first" | FAILS | not seen (values not in this test) |
| service shape test (test_service_unit.py:20-26) | keys of result and atm_iv | result key set is {id,ok,gamma,gss,atm_iv,atm_iv_error}: new keys INSIDE gamma/gss are not checked; atm_iv keys are exact | same | no |
| payload path (service.py:23 `_GAMMA_FIELDS` = all dataclass fields except gss_rows; payload.ts:50 passes result.gamma whole; mr_write_cycle uses jsonb_to_record with a fixed column list, 20261101000400:357-365) | | new fields travel to the database call and are **silently dropped** by jsonb_to_record (no error) | same | n/a |
| engine-ref-gate.sh + engine_ref_compare.py | vendored files + O1 + O4 DDL, in a container | none: vendored files unchanged, O1 unchanged. Visible only if the operator re-vendors AND re-exports O1; a re-vendored view with a new column and the OLD O1 prints `ENGINE-REF <v> ... MISMATCH` and exits 1 (`k == len(ev) == len(o1)`). A new table column in the live engine is not seen at all (O4 is a frozen copy) | same | same as middle |
| view-transform-check (scripts/view-transform-check, view_transform/classify.py) | vendored engine body vs retail migration, token diff | if only the engine file is re-vendored: `UNCLASSIFIED <view> hunk n: insert '...'` (exit 1), because the retail migration lacks the column; refuses with `REFUSED ... not md5-verified` (exit 3) if gate JSON is not MATCH or the file sha changed | same | a changed expression is an unclassified hunk (exit 1) |
| `--headers` (VIEW-HEADER retail_len/md5) | md5 of pg_get_viewdef of retail views built from migrations | only if a retail migration changes | same | same |
| L4 (46_mr_views_l4 from gen-l4.py) | engine view (vendored text) vs mr_ view on the same inputs: (a) column NAME lists must be equal (`is(array_agg(attname) ...)` 439-441), (b) `EXCEPT` both ways on the engine view's column list (`l4_cols`), exact, no tolerance | fails (a) if only one side gains the column; passes if both sides are changed together | same | EXCEPT diff > 0 if retail not changed with it |
| L4 staging into engine scratch tables (gen-l4.py:363-366) | `insert into gex_strike_snapshots (explicit column list) select ...` | a NEW column in the engine table is irrelevant to the explicit lists; a NEW NOT NULL column without default would make the insert fail (O4 table is retail's own DDL, so only if O4 is re-exported) | same | n/a |
| gen-l4 --check GEN-L4-SHA256 (docs/view_provenance.md:88) | sha256 of the generated test text | changes if the generator, golden manifests, or vendored view files change | same | same |
| L1 (test_parity_l1.py, 486 cycles) | service vs reference.py, both calling merdian_compute, bit for bit via `exact_equal` | after a bump both sides move together: stays 0 mismatches. (exact_equal's treatment of keys present on only one side was not read) | same | same: scale-blind by construction |
| L3 (l3.py, TOL 1e-9 relative) | service vs PRODUCTION values in the golden days (net_gex, max_gamma_strike ...) | unaffected by new fields (BOARD_FIELDS is a fixed list) | same | **FAILS** if existing net_gex changes scale after a bump; golden production data is scale A at the old SHA |
| L2 (l2_compare.py:89) | database read-back of gex_cr etc. vs engine directly, bit for bit, field list fixed | unaffected by new fields | same | follows the engine; golden values are scale A |
| M-ENGREF / view-transform mutants (tests/mutants/mutants.mjs:94-104,225) | | not about columns | | |

So: additive columns *in the engine database* are invisible to every retail gate. Retail only sees the engine through (1) the SHA of merdian_compute, (2) frozen vendored view files + O1/O4 exports, (3) the golden cache at the SHA. The additive step becomes visible exactly when the operator bumps the SHA, re-vendors, or re-exports O1, and then it is loud in the places named above.
