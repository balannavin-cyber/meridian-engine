# E1 + E3 + E10 build report (dhan_drop SSH push + 300s login-attempt guard)

Branch `e1-e3-e10` created from `origin/main`. Ancestry re-checked just before writing
this report: `git merge-base e1-e3-e10 origin/main` → `ba505cf9246e7e89ff072a987036e271b7b55703`,
and `git log --oneline -1 origin/main` → `ba505cf`. The branch point matches `origin/main`'s
current tip. Work done entirely in `~/meridian-cc`; `~/meridian-engine` was never touched.
No login to Dhan, no ssh to the retail box, no read of any real `.env` value, no execution
of `bin/dhan_login.sh` or of the login script, at any point in this build.

## Baseline (MEASURED, before this build)

- `refresh_dhan_token.py`: 239 lines. Anchors confirmed line-for-line against the task's
  stated anchors (`:134` load_dotenv, `:137` `_idempotency_skip`, `:60` `requests.post`,
  call sites `:147`/`:162`, success block `:196`-`:204`, failure branches `:165-186`).
- `tests/run_offline.sh`: 40 steps, `tests/test_*.py`: 34 files.

## What shipped

- **`dhan_drop.py`** (new, stdlib only). `send_dhan_drop` / `send_dhan_login_status`
  build the 5-key `dhan` file or the 1-line `dhan_login_status` file, validate every value
  (non-empty token, non-empty/non-whitespace `client_id`, no embedded newline in ANY value —
  checked before the values are joined, so an injected value can never smuggle an extra
  key=value line onto the wire — ≤8 lines, ≤4096 bytes, printable ASCII+LF, no key containing
  "secret", `minted_at`/`ts` ends `+05:30`), send over
  `ssh -F /dev/null -i <key> ... put <name>` with content on stdin only (never argv/log), and
  never raise — every path returns a bool.
- **`refresh_dhan_token.py`** (MEASURED now 329 lines, +90). Defensive
  `try: import dhan_drop except Exception: dhan_drop = None`, plus `_send_dhan_drop` /
  `_send_dhan_login_status` wrappers that no-op when the helper is missing or broken (never
  stop the login). E10 guard: `LOGIN_ATTEMPT_STAMP` / `_write_login_attempt_stamp` (fails
  open on `OSError`, creates `logs/` on demand) / `_login_attempt_guard` (300s spacing,
  strict `0 <= age_s < 300`; treats a malformed, naive-tz, or missing stamp as "no stamp"
  via `OSError, ValueError, TypeError`), inserted in `main()` before the existing 90s
  idempotency skip (D2). Stamp write moved inside `request_dhan_token` itself, covering
  both the first call and the 30s TOTP retry. Outer handler broadened to
  `except Exception as e: if not isinstance(e, RuntimeError): ...` per D7 — confirmed this
  also catches `requests.HTTPError` and a `resp.json()` `ValueError` (malformed JSON), not
  just Timeout/ConnectionError; RuntimeError branches already send their own status, so this
  never double-sends. Confirmed by reading the code (and now by a test cell) that
  `request_dhan_token` already raised `RuntimeError` on a 200 with no `accessToken` before
  this build — no change was needed there.
- **`bin/dhan_login.sh`** (new). D1 thin wrapper: cd to the tree,
  `/usr/bin/python3 refresh_dhan_token.py` (matching cron's own interpreter, per
  `docs/registers/aws_crontab.txt` line 2), prints what 0/2/3/other mean — exit 2 now reads
  "a token was issued within the last 2 minutes; the one in .env is probably good. Do not
  retry for 5 minutes." Carries a comment that CC must never execute this script.
- **`tests/test_dhan_drop.py`** (new): T1-T5, T7, T8, T2b (dhan_drop
  unimportable), T2d (internal-exception + control), T3b (empty/whitespace client_id,
  embedded newline in token/client_id/expires, output-leak checks, control). 8 mutants
  (M1-M8), all CAUGHT.
- **`tests/test_dhan_login_guard.py`** (new): T6 (11 cells: spacing, both
  boundaries at 299s/300s, missing/old/future-dated stamp, write-order, crash survival,
  unwritable-`logs/` fail-open, naive/garbage timestamp), T9 (footprint), T10 (idempotency).
  9 mutants (M1-M9: threshold down, stamp order, fail-open removed, TypeError/ValueError
  dropped, refusal rc swallowed, threshold up, boundary `<=`, lower-bound dropped), all
  CAUGHT.
- **`tests/run_offline.sh`**: all 40 existing step labels renumbered `/40`→`/42` (`sed`,
  verified 40→0 occurrences of `/40`), two new steps appended (41, 42) in the same
  `${PIPESTATUS[0]}` pattern, with accurate "needs requests and python-dotenv" dependency
  notes (not "stdlib only" — that claim is true of `dhan_drop.py` itself but not of the
  test files, which exec real `refresh_dhan_token.py` source) and final mutant counts
  (M1-M8 / M1-M9). Header comment updated with the new step count and history.

## Numbers (labelled)

- Baseline 40 steps / 34 `test_*.py` files — MEASURED (session start, `ba505cf`).
- New: 42 steps / 36 `test_*.py` files — MEASURED (`find tests -maxdepth 1 -name
  'test_*.py' | wc -l` = 36; `grep -c '/42' tests/run_offline.sh` = 42).
- Line counts — MEASURED, quoted from the measure script's own printed output, re-run
  immediately before writing this report:
  `refresh_dhan_token.py: 329 lines`, `dhan_drop.py: 149 lines`,
  `bin/dhan_login.sh: 27 lines`, `tests/test_dhan_drop.py: 840 lines`,
  `tests/test_dhan_login_guard.py: 613 lines`, `tests/run_offline.sh: 230 lines`.
- `test_dhan_drop.py` standalone: exit 0, 8/8 mutants CAUGHT — MEASURED; full output
  reviewed by the operator in session, saved at `/tmp/final1.out` (not committed, not
  reproduced in this file).
- `test_dhan_login_guard.py` standalone: exit 0, 9/9 mutants CAUGHT — MEASURED; full
  output reviewed by the operator in session, saved at `/tmp/final2.out` (not committed,
  not reproduced in this file).
- `refresh_dhan_token.py`: ast.parse + py_compile + required-function presence OK —
  MEASURED (static-only validator: no import, no `main()` call, no network, no `.env`
  read).
- `bin/dhan_login.sh`: `bash -n` syntax check only — MEASURED. Never executed this
  session.
- Full `( ulimit -v 700000; bash tests/run_offline.sh )` (steps 1-42): OWED. The
  operator runs it after 15:40 IST per Rule 23; CC never executes it. DERIVED
  expectation: 42/42 PASS, since both new steps pass standalone.
- Push: OWED, only if the operator permits it; no PR.

## Operator-side facts (not measured by CC this session; stated by the operator)

- The operator checked the key fingerprint and the ED25519 host fingerprint, and both
  matched the expected values.
- Engine `.env` held 0 `MERIDIAN_RETAIL_DROP_` lines at the check, so deploy must add
  three.
- Deploy is a fast-forward and brings two commits, `8fde9df` and `ba505cf`, which are
  docs and data only (plus a one-line `.gitattributes`) and carry no code.
- The first live drop is unobserved until an 08:20 IST cron run. Everything so far is
  offline stubs.
- `~/.ssh/config` was not read. `-F /dev/null` makes the helper ignore it.

## Rule 0 notes from this build (process record, not a finding against shipped code)

Three test-harness bugs were found and fixed before any mutant was trusted:
- `load_dhan_drop`'s `_now_ist` stub originally built its fixed instant from the *test
  file's own* `IST` constant, independent of the module under test — so "time offset not
  +05:30" (M5) was unkillable by construction regardless of what the mutant did. Fixed to
  build the instant from `mod.IST` (the exec'd module's own, possibly-mutated constant).
- No T1/T3/T8 cell ever raised an exception from inside `send_dhan_drop`'s own body (only
  from `_ssh_put`, which has its own inner catch), so narrowing the outer `except Exception`
  (M1) was invisible to every existing cell. Added T2d: injects via a stubbed clock that
  raises, with a same-shape control (real clock, expects exactly one ssh call) proving the
  FAIL is attributable to the injected exception, not something else.
- T10's planted "recent" `token_status.json` timestamp was anchored to the guard's stubbed
  `FIXED_NOW`, but `_idempotency_skip()` is pre-existing, unmodified code that reads the
  REAL wall clock (`datetime.now(IST)`) — so the computed age was enormous, not 30s, and the
  skip never fired. Fixed to anchor the planted timestamp to the real clock.

## Not in this build

E9 (crontab), MALPHA's Kite push (E6), the Local scheduler, `refresh_dhan_token_aws.py`,
any deploy to `~/meridian-engine`.
