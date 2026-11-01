# CC prompt — ADR-032 independent sweep, RETAIL repos (READ-ONLY)

Where: the retail sandbox box (`sudo su - ubuntu`), **inside tmux**, one CC session in `~/retail-platform` (repos `~/retail-platform`,
`~/retail-meridian`; read-only design clone if present). Plan on Opus, fan-out on Sonnet.
Output: `~/retail-platform/scratch/s103_sweep/` (untracked, outside any commit). **This session changes nothing.**

Scope line (every MR session): retail repos read-write — **for this task, no writes at all**; `meridian-engine` read-only; the
production box and the production database are never touched.

## 0. Why

The operator will change the engine's stored unit of every gamma-exposure size (Γ) from ₹ Cr per 100 % move (`γ·OI·S²/1e7`, scale A)
to ₹ Cr per 1 % (×0.01, scale B), added as **new columns beside the old** in the engine database. Retail imports the engine's pure
compute (`merdian_compute`, pinned by SHA), keeps copies of the engine's view DDL (`engine-ref`) with md5 pins, compares its own
`mr_v_*` views against them (L4), replays 486 golden cycles bit-for-bit (L1), and displays Γ figures. The product is close to launch.
**Find every place retail reads, copies, pins, compares, labels or thresholds a Γ size or the unit.** This sweep is independent of any
earlier list, on purpose.

## 1. Rules (binding)

- Read-only. No edit, commit, push, branch, worktree, `supabase` command that writes, `db reset`, `--db=linked`, `gh` write, or
  deploy. No `.env*` and no `~/.config/retail-platform/*` reads (the hooks deny them). No Dhan or Zerodha calls. No `pnpm verify`
  and no mutants run (they write `.verify/` and `mutants-output/`); read their definitions only.
- Start by printing `git rev-parse --short HEAD` in each repo, `docs/STATE.md`'s "last green" line, and the engine pin recorded in the
  repo (SHA, path). Report them; do not change them.
- Do not open any file with `adr032`, `impact_study` or `gex_unit_inventory` in its name until the operator hands you the study
  (Phase 2).
- A "none found" is a claim: give the exact pattern, the file set and its size, and show the pattern fires on a known positive.
- Box memory is small: `rg`, `git ls-files`, no big in-memory loads, at most 2 read-only subagents.

## 2. What counts as a Γ size

As in the engine prompt: anything built from `γ·OI·S²` — `gex_cr`, `net_gex`, `net_gex_cr`, `abs_gex_cr`, `gamma_at_pin`,
`peak_pin_gex_cr`, `total_pin_gex_cr`, `total_accel_gex_cr`, `trough_gex_cr`, `gex_drift_*`, `flow_cr`, sums/ratios of these, and
the same quantity under any other name (including `mr_` view columns, TypeScript field names, glossary entries, copy strings).
Delta-type (`oi·S/1e7`) is not a Γ size; list any mixing.

## 3. Method (Phase 1, independent)

1. **Coverage census** (`00_census.txt`): `git ls-files` counts by extension for both repos, untracked files, the pinned engine copy
   (`engine-ref`, `vendor`, submodules) and the generated test files (for example `46_mr_views_l4.test.sql`); total bytes.
2. **Token sweep** (`10_hits.tsv`) over **every tracked text file of every type** (`.ts .tsx .js .mjs .sql .py .sh .json .md .toml
   .yml .css`; migrations, tests, fixtures, glossary and strings files, docs — nothing excluded): the §2 names plus `gex`, `gamma_exp`,
   `net_gamma`, `1e7`, `Cr per`, `L Cr`, `K Cr`, `crore`, `per 1 %`, `per 100 %`. One row per hit:
   `file:line | token | kind | use | scale assumed | change needed | test that would catch it | owner`.
   kind ∈ writer · reader · copy · pin · compare · recompute · test · fixture · label · glossary · threshold · dead;
   use ∈ sign · ratio · magnitude · pass-through · display · unknown.
3. **The engine pin** (`20_pin.md`): which `merdian_compute` SHA and which contract version retail pins; the `engine-ref` files with
   their md5s and the `M-ENGREF` / `view-transform` gates that check them; the exact lines in the contract and in `engine-ref` that
   state the unit; what each gate would do if the engine **added columns** to a view (extra column at the end; extra column in the
   middle; changed values in an existing column). Read the gate code; do not run it.
4. **Database objects** (`30_sql.md`): every `mr_v_*` view, function, policy and migration that mentions a Γ token, with the
   transformation applied to the engine view (the `view-transform` hunks); which of them select `*`; the pgTAP/L4 files that compare
   them with the engine; what happens to each if an engine view gains a column.
5. **Goldens and replays** (`40_goldens.md`): L1 (486 cycles), L2/L3 (0 mismatches), the GEN-L4 hash, the O2 parameter file, every fixture
   under `tests/fixtures/**` and every `golden` file that holds a Γ value or its hash; how each is regenerated and by whom.
6. **UI and copy** (`50_ui.md`): every board-port component, string, glossary entry, tooltip and number formatter that shows a Γ size
   or its unit; the wording-lint allowlist entries that mention Γ; whether the unit is a constant in one place or repeated.
7. **Thresholds and tolerances** (`60_constants.md`): every numeric literal compared with or scaled against a Γ value.

## 4. Report (then stop)

`90_report.md`: coverage in three lines; counts by kind × use; **the unknown bucket** with the question that would settle each;
**every Γ size found under an unexpected name**; **what each retail gate does when the engine adds new columns** (this is the
question that decides whether the engine's additive step is invisible to retail); things you could not check and why. No fixes, no
ranking. Print `sha256sum` of every output file. The operator uploads the folder to S3 for review.

## 5. Phase 2 (only on the operator's word, with `study_for_diff.md`)

`95_diff.md`: missing from the study / missing from the sweep (and why your pattern missed it) / disagreements, each with file:line.
Then stop.
