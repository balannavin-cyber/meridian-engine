# CC prompt — ADR-032 independent sweep, engine + board + SQL + live DB (READ-ONLY)

Where: the production box, tmux, one CC session rooted in `~/meridian-cc` (never `~/meridian-engine`). Plan phase on Opus; the fan-out on Sonnet.
Output: `~/meridian-cc/scratch/s103_sweep/` (untracked). Nothing else is written. **This session changes nothing.**

## 0. Why this exists

The operator will change the stored unit of every gamma-exposure size (Γ) from ₹ Cr per 100 % move (`γ·OI·S²/1e7`) to ₹ Cr per 1 %
(×0.01), added as **new columns beside the old**, with the board reading wrappers. The system is close to launch. A previous read
(by another Claude session) listed the readers and writers it found; **this sweep is independent of that read on purpose** and
exists to find what it missed. Anything that reads, writes, copies, compares, labels, prints or thresholds a Γ size is in scope.

## 1. Rules (binding)

- **Read-only.** No edit to any tracked file; no `git add/commit/push/pull/checkout`; no deploy; no crontab change; no `rm` outside
  `scratch/s103_sweep/`. `git fetch` is not needed. The only database access is `bin/roq.sh` (role `merdian_ro`), SELECT only.
- No `.env*` reads, no credential reads (CLAUDE.md rule 19). No fixture suite (`tests/run_offline.sh`) — rule 23. No network other
  than `bin/roq.sh`.
- Start by printing `git -C ~/meridian-cc rev-parse --short HEAD` and `git -C ~/meridian-connect rev-parse --short HEAD`.
  Expected `c11b564` and `6f14a92`. **If either differs, stop and report**; do not sweep a moving tree.
- **Phase 1 is blind.** Do not open `docs/research/s102/*`, `docs/decisions/ADR-032*`, `docs/lovable_prompts/s102/*`, or any file
  named `*adr032*`, `*impact_study*`, `*gex_unit_inventory*`. If a search returns one of them, note the path and move on without
  reading it. Phase 2 (§5) starts only when the operator says so.
- **A "none found" is a claim and needs proof.** For every search that returns zero hits, state the exact pattern, the file set
  searched and its size, and show that the same pattern **does** hit a known positive (for example `gex_cr` in
  `merdian_compute/gamma.py`). A pattern that cannot fire proves nothing (rule 0).
- Box memory is small (t3.small, ~1.1 GB free, no swap): `rg` and `git ls-files`, no pandas on big files, at most 2 read-only
  subagents at a time. If a command takes > 2 minutes, say so and narrow it.

## 2. What counts as a Γ size

Any quantity built from `γ · OI · S²` (per option, per strike, net, gross, absolute, signed): `gex_cr`, `net_gex`, `net_gex_cr`,
`abs_gex_cr`, `gamma_at_pin`, `peak_pin_gex_cr`, `total_pin_gex_cr`, `total_accel_gex_cr`, `trough_gex_cr`, `gex_drift_*`,
`*_cr_per_volpt`, `*_cr_per_day`, `flow_cr`, `oi_change_gex_cr`, sums, maxima, differences and ratios of these, **and anything
under another name that carries one** (`net_gamma`, `gamma_load`, `contrib_*`, `zone_signed_mass`, `total_abs_mass`, dict keys,
JSON keys inside `raw`, CSV columns, pandas columns, f-string-built names). Delta-type values (`oi·S/1e7`) are **not** Γ sizes, but
list any place that mixes the two. Today's stored scale is A (`/1e7`). A per-1 % copy is scale B (×0.01).

## 3. Phase 1 — method (independent)

1. **Coverage census** (`00_census.txt`): `git ls-files` for both trees, counts by extension; untracked files in each working tree
   (list them, flag any that contain a Γ token); total bytes. This is the proof that the whole code base was walked.
2. **Token sweep** (`10_hits.tsv`): `rg` over **every tracked text file of every type** (`.py .ts .tsx .js .mjs .sql .sh .json .md
   .toml .yml .yaml .pine .txt .csv .cfg`; docs, tests, research and scratch-tracked files included — do not exclude them). Tokens: the
   names in §2 plus `gex`, `gamma_exp`, `net_gamma`, `dealer_gamma`, `1e7`, `10_000_000`, `Cr per`, `L Cr`, `K Cr`, `crore`. One row per hit:
   `file:line | token | kind | use | scale assumed | change needed | test that would catch it | owner`.
   - kind ∈ writer · reader · copy-through · formula-copy · recompute · test · fixture · doc · label · alert-text · threshold · dead
   - use ∈ sign · ratio · magnitude · compensating · pass-through · display · unknown
3. **Python AST sweep** (`20_ast_findings.md`): for every `.py` walk the AST and report (a) string constants and attribute/subscript
   names matching §2; (b) `BinOp` Div by `1e7` / `10_000_000` or Mult by `100` / `0.01` within the same function as a Γ token;
   (c) column names built at run time (f-strings, `+` concatenation, `getattr`, `.get(var)`); (d) every `select("*")`, `.select()`
   with no argument, `SELECT *` or `t.*` over a table or view that carries a Γ column; (e) every function that takes a Γ size as an
   argument and compares it with a numeric literal.
4. **TypeScript sweep** (`30_ts_findings.md`, board tree `~/meridian-connect`): every `supabase.from("…")` target and its `.select(…)`
   string; every field read from a Γ source and what is done with it; every formatter applied to a Γ value (`fmtCr`, `crLakh`,
   `fmtNum` with "Cr", `lad`…); every UI string containing "Cr", "L Cr", "K Cr", "unit", "per 1 %", "per 100 %"; mocks and dead code
   (list, do not judge).
5. **Database, live** (`40_db_findings.md`, via `bin/roq.sh`): (a) every view and materialized view whose definition mentions a Γ
   token, with `md5(pg_get_viewdef(oid))`; (b) every function whose body mentions one, with `md5(prosrc)`; (c) dependents by
   `pg_depend` / `pg_rewrite` of every Γ column; (d) triggers, `pg_cron` jobs, indexes, policies, generated columns, column
   comments that mention one; (e) tables and views with columns whose **name** contains `gex`, `gamma`, `dealer` or ends `_cr`;
   (f) if `merdian_ro` may read `pg_stat_statements`: the statements that mention a Γ object, by role and calls (this shows readers
   that are not in any repo). Say plainly what the role is not allowed to read.
6. **Outbound text and constants** (`50_outbound_and_constants.md`): every Telegram/alert/log/report/CSV/overlay string that prints a
   Γ value; every numeric literal compared with, scaled against, or used as a tolerance for a Γ value (for example `2.5e5`,
   `1_000_000`, `0.01`, `/ 1000`), with its file:line and the unit it assumes.
7. **Tests and fixtures:** every test, fixture and golden file that embeds a Γ value, a Γ formula, or a hash of Γ output (golden
   hashes, contract pins, expected-row files), with the step number in `tests/run_offline.sh` that runs it.
8. **Documents that state the unit or a magnitude** (list only): CLAUDE.md, contracts under `docs/interfaces/`, manuals, registers.

## 4. What to report (then stop; Phase 2 only on the operator's word)

`90_report.md`: (1) the coverage census in three lines; (2) counts by kind × use; (3) **the unknown bucket** — every hit you could
not classify, with the question that would settle it; (4) **every place where a Γ size is read under a name you did not expect**;
(5) things you could not check and why (permissions, file types, dynamic code). Do not propose fixes. Do not rank importance.
Print `sha256sum` of each output file at the end so the operator can verify the copy. The operator uploads the folder to S3 for review.

## 5. Phase 2 (only when the operator hands you `study_for_diff.md`)

Read it. Produce `95_diff.md`: **missing from the study** (found by you), **missing from the sweep** (in the study, not found by you —
for each, find out why your sweep missed it and say whether a pattern needs widening), and **disagreements** (same object, different
use or scale), each with file:line evidence. Re-run any search that the study's author found and you did not. Then stop.
