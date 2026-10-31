# S101 session prompt — retail interface packaging (P4 prerequisite, scope §1.3) + Monday Part C

**Read first, before asking me anything:** `claude/CURRENT.md` (S100 state, NEXT SESSION PICKS UP);
`claude/retail/retail_scope_v0.4.md` §1.3 and §8; `claude/retail/rulings_mr_s1.md` (MR-S1 state); the repo at HEAD
(clone the public repo `https://github.com/balannavin-cyber/meridian-engine.git` and read there). State at S101 open
(2026-10-25 ~20:45 IST, Sunday): HEAD `7b91d1a` (S100 doc-close). Sunday evening is a capture-path deploy window
(ruling S90-J), but see "Deploy timing" below.

**Track with a task list**, one task per item, each done only on its PASS evidence pasted by me.

## Part A — Retail interface packaging (tonight: build + prove on the clone; NO deploy)

Goal (scope §1.3): retail-meridian computes per-user on each subscriber's own broker chain. It must **import** the
engine's compute, never copy it. Today it can't: importing the live writers connects to production.

Facts read from `7b91d1a` (re-verify on the clone before using):
- `compute_gamma_metrics_local.py` (1,403 lines) runs `SUPABASE: Client = _load_env()` at **module import** (L72) —
  reads `SUPABASE_SERVICE_ROLE_KEY` and opens a production client on import. `write_gex_cycle_history_local.py`
  (605 lines) does the same at L68.
- An AST pass found the math top-level functions free of `SUPABASE` / `os` / `requests`: `signed_gamma_exposure`,
  `filter_usable_option_rows`, `infer_*`, `compute_net_gex`, `build_strike_exposure_map`,
  `compute_gamma_concentration`, `_flip_short_gamma_perstrike`, `compute_flip_level`, `find_atm_strike`,
  `compute_straddle_atm/_slope`, `compute_expansion_probability`, `determine_regime`, `determine_gamma_zone`,
  `compute_straddle_velocity`, `compute_otm_oi_velocity/_snapshot`, `compute_max_gamma_strike`,
  `compute_pin_risk_score`, `compute_gamma_metrics`, `build_gss_rows`, `GammaMetricsResult`. That pass was
  **not transitive** (e.g. `compute_gamma_metrics` may call `fetch_*`) — redo it transitively.
- Walls, pin and max pain come from **database views** (`v_gex_strike_walls`, `v_gex_pin_maxpain`, `v_pin_board`,
  `v_gex_max_pain`, `v_max_pain_by_strike`; SQL under `sql/`), not Python.
- The gamma math is already re-implemented twice outside the writer (`backfill_gamma_metrics_to_main.py`,
  `measure_rate_sensitivity.py`) — drift evidence; out of scope tonight, note it.

Steps (each: read code on the clone → design → offline test with controls and mutants → bundle → box dry-run → suite):

1. **Transitive purity map.** For every function above, the full call closure; list exactly which are pure (no I/O,
   no env, no network, no DB, no clock beyond arguments). PASS = a table, computed by a script you show, not recalled.
2. **Extract, verbatim.** New package `merdian_compute/` (e.g. `gamma.py`, plus pure helpers from
   `write_gex_cycle_history_local.py` such as `trading_days_to_expiry`, `boost`, `conviction_for` if pure, and
   `core/pin_state.derive` if pure). Function bodies moved **byte-identical**; the writers import them back under
   the same names so every existing caller and the orchestrator's `python3 compute_gamma_metrics_local.py <run_id>`
   invocation are unchanged.
3. **Behaviour-neutral proof (Rule 0):**
   (a) AST equality: `ast.dump` of each moved function before vs after — identical, by script.
   (b) Golden replay: gamma outputs over every `tests/golden/*` day, before vs after, compared row-for-row; sha256
       of the serialized outputs identical. A mutant (one float constant changed in the extracted module) must make
       (b) FAIL.
   (c) Offline suite: `( ulimit -v 700000; bash tests/run_offline.sh )` green, plus the new step below.
4. **Import-purity test** (new offline-suite step 24): `import merdian_compute` in a subprocess with an EMPTY
   environment, `supabase`/`requests`/`dotenv` blocked from import, and sockets disabled → succeeds. Mutant: add an
   `os.getenv` or `create_client` at module level → the step FAILS.
5. **Contract tests** for the exported surface: signatures + golden-pinned outputs for the functions retail will
   call (the Board core: net Γ, flip, max-γ strike, regime, zone, concentration, straddle, pin-risk score).
6. **Interface contract doc** `docs/interfaces/retail_compute_contract.md`: the exported functions with signatures,
   units and sign conventions (Γ aggregate vs γ per-option, S100-R); the view definitions retail must re-create in
   its own schema (file paths under `sql/`, verbatim, with their dependencies); what retail must NOT import (any
   writer, `core.supabase_client`, `core.dhan_client`, `core.config`). Retail pins this repo by commit SHA.
7. **Packaging:** `pyproject.toml` exposing only `merdian_compute` (installable as
   `pip install "git+https://github.com/balannavin-cyber/meridian-engine@<sha>#egg=merdian_compute"`), no runtime
   deps beyond the stdlib (and whatever the pure math already uses — list them).

**Deploy timing (recommended, operator to rule):** commit to a branch `s101/retail-interface` tonight, pushed, NOT
pulled to `~/meridian-engine`. Monday's Part C reads measure the gamma writer's latency and closing rows; changing that
writer the night before would confound them. Deploy after the Part C read (Monday after 16:30 IST, S90-J window):
fast-forward merge, box pull, one manual `compute_gamma_metrics_local.py` run on the latest run_id compared against
the cron-written row, written rollback = `git revert` of the merge.

## Part B — Monday 2026-10-26 (from CURRENT.md NEXT SESSION PICKS UP, unchanged)

1. Before the open (operator): **BS-1** — Dhan TOTP re-enrolment and PIN change, `.env` update by hidden prompt, then
   `refresh_dhan_token.py` and `preopen_probe.py --check`. Read back the `27c0e17` promote.
2. After 15:45 IST: **Part C live reads** exactly as CURRENT.md item 1 (a)–(c). Also: `dhan_token_probe_log` for
   10-26 shows 200 (a retail dev Dhan token was minted on Sunday 19:4x IST on the same account — confirm it did not
   disturb production).
3. After Part C PASS: deploy Part A per "Deploy timing".

## Standing rules (binding) — as S100

- Every command and SQL block in full, one step at a time, with the exact output that means PASS; each SQL query in
  its own code block. Rule 0: a check must be able to fail for the reason it names; expected values computed, never
  recalled.
- No fixture suite 08:30–15:40 IST on a trading day (Sunday exempt); always under `ulimit -v`.
- One CC session per tree, rooted in `~/meridian-cc`, never `~/meridian-engine`. No `.env` reads (rule 19).
- DDL and data writes are operator actions in the SQL editor; every batch ends with its own verification SELECT.
- Commits by the box route (S99-A); messages via `git commit -F`. Rollback commands only inside a refusing block.
- At a CC permission prompt, give the option number only. Never name the parity target's product in artefacts.
- Retail scope line: this session changes `meridian-engine` only through the box route; it never touches the retail
  sandbox, and the retail sandbox never touches production.
- Session close is when the operator says so. Never mention sleep or rest, and never suggest ending the session.
