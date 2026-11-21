# CC prompt: engine lane E1 + E3 + E10 (one login per broker account), written Fri 2026-11-20 (MR-S13, retail lane for the engine lane)

Engine box (`ssm-user@ip-172-31-35-90`). **Work only in the agent tree `~/meridian-cc`, on a new branch from `origin/main`** (Deployment Topology S73.A: `~/meridian-engine` is the production tree every cron line and unit resolves inside; the agent never edits it. It reaches production only by the operator's `git pull --ff-only` after merge). Reading `~/meridian-engine` is allowed for the plan step, read-only. Plan on Opus, then `/clear` and `/model claude-sonnet-5-5` for the build. Source: `claude/engine_request_one_login_2026-11-14.md`, `claude/engine_answer_one_login_2026-11-14.md`, `claude/retail/retail_drop_spec_2026-11-15.md` (sections 1, 1b, 3, 7).

## Hard rules (read first)
- **Never run `refresh_dhan_token.py` live, never log in to Dhan, never `ssh` to the retail box, never read or print a token, key or `.env` value.** One login on the operator's Dhan account kills the engine's key. Every test stubs the HTTP request, the ssh call and the clock. A test that could reach the network or the real `.env` is a defect.
- CC cannot take a secret. Nothing here needs one.
- **Do not edit the crontab, `.env`, `runtime/`, Supabase `system_config`, `~/meridian-engine`, or any file outside `~/meridian-cc`.** The crontab edit (E9) is the operator's, after 15:45 IST, with a backup, after this is merged and deployed.
- Absolute paths rather than `cd` compounds. Reports go to files plus a short summary. No reminder about closing the session.

## Basis (MEASURED by operator reads on the engine box, 2026-11-20 16:00 IST)
1. Crontab has exactly one Dhan login: `50 2 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 refresh_dhan_token.py >> cron.log 2>&1` (08:20 IST, weekdays). `reload_dhan_scripmaster.py` and the CAS line do not log in.
2. `generateAccessToken` appears only in `refresh_dhan_token.py` and `dhan_token_refresh_lib.py`. No `.py` file matches `DH-906`, `re-login`, `relogin`.
3. `refresh_dhan_token.py` calls `request_dhan_token` directly (not the lib's retry function). Path today: attempt 1; if the error contains `Invalid TOTP`, `sleep(30)`, attempt 2; a rate-limit error (`once every 2 minutes`) on either attempt writes `token_status.json` with `success=false` and returns exit 2 ("exiting cleanly"); any other error writes status false and raises. So the live path is **two attempts at most, not three** (the engine answer's "three" is stale; `dhan_token_refresh_lib.request_with_retry` is used only by `refresh_dhan_token_aws.py`, which is not in the crontab).
4. `_idempotency_skip()` skips only when `token_status.json` shows a **success** under 90 s old. It ignores failed and rate-limited attempts and is shorter than the 300 s rule.
5. Other callers of the script: `merdian_live_dashboard.py:57` runs it as a dashboard button. Old copies (`*_PRE_S25*.py`), `stage3_runner_drystart.py` (compile check only), a cron string inside `tests/test_monitor_orchestrator_gate.py`.
6. No holiday or calendar gate in the script. `token_status.json` is still written by `write_token_status`.
7. Local (Windows): all 19 `MERDIAN_*` scheduled tasks are Disabled and `DHAN_PIN` / `DHAN_TOTP_SEED` were removed from Local's `.env` on 2026-11-20 (OPERATOR-RUN). The engine box is the only place that can mint.

## Decisions already ruled (retail lane, to be recorded)
- **D1.** The 300 s spacing guard lives **inside `refresh_dhan_token.py`**, not only in a wrapper, so the cron, the dashboard button and a manual run all share one stamp. `bin/dhan_login.sh` stays as the operator's single named manual command (E10) and is a thin wrapper (`cd`, run the script, print what the exit code means). The cron line keeps calling the script; E9 later changes only `1-5` to `*`. This departs from the engine answer's "cron calls the wrapper"; the effect (one stamp covers both) is the same with one moving part fewer.
- **D2.** Stamp file `BASE_DIR / "logs" / "dhan_login_attempt.stamp"` (not `runtime/`: E8 says nothing for E1 may touch `runtime/`; in tests BASE_DIR is a temp dir). Written atomically **before every HTTP request to Dhan**, including the 30 s TOTP retry, so a crash mid-request still counts as an attempt. The guard is checked once at the start of a run: stamp younger than 300 s means refuse, print the seconds remaining, exit **3**, make no request, write no drop, no status. The in-run 30 s retry is the one allowed exception (retail ruled it in spec section 7: retry only on `Invalid TOTP`; any other answer stops the run). The existing 90 s `_idempotency_skip` stays unchanged and runs after the new guard.
- **D3.** Rate-limited (`once every 2 minutes`, either attempt): exit 2 as today, **no drop and no `dhan_login_status` write** (the engine's key is valid and an earlier invocation already dropped it). Non-rate-limit failure: write `dhan_login_status` = `failed <IST>`, never a `dhan` file, then the original exception propagates unchanged.
- **D4.** Success: write the `dhan` drop first; only if it succeeds write `dhan_login_status` = `ok <IST>`. If the `dhan` drop fails, log by name and write no `ok`.

## Build
**E1 helper** (new module `dhan_drop.py`, standard library only): called at the end of the success path, right after `write_token_status(True, ...)`. Content, key=value lines, LF only, split on the first `=`: `broker=dhan`, `access_token`, `expires` (as Dhan returned it, whitespace-stripped), `minted_at` (`datetime.now(IST).isoformat(timespec="seconds")`, must end `+05:30`), `client_id` (from `DHAN_CLIENT_ID`). Send by `ssh -i <sender private key> -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=<pinned file> retaildrop@<retail host> put dhan`, with the content on **stdin** (subprocess `input=`), never in argv, never logged, `timeout=30`. Refuse to send (and log the reason by name only) if the token is empty, any byte is outside printable ASCII 0x20-0x7E plus LF, more than 8 lines, more than 4096 bytes, a key name contains `secret`, or `minted_at` lacks `+05:30`. The helper catches every exception, returns a bool, **never changes the script's exit code, never raises into the login, never touches `.env`, `system_config` or `runtime/`**. Log line: `DHAN DROP name=dhan bytes=<n> ok|refused reason=<code>`, no value, no key name from the content.

**E3 status**: same helper, name `dhan_login_status`, content one line `failed <ISO with +05:30>` or `ok <ISO with +05:30>`, `put dhan_login_status`. Per D3/D4.

**E10**: the D2 guard in the script plus `bin/dhan_login.sh` (D1).

Where the sender key, the pinned host key file and the retail host address live: **do not guess.** The operator generated the sender key on this box and pinned the retail host key on 2026-11-16 (retail Elastic IP is not recorded in the docs; the outbound address seen was `16.4.29.153`, Elastic IP status UNVERIFIED). In the plan, report read-only what exists under `~/.ssh/` by file name and mode (never contents of a private key) and the `known_hosts` host field only, then name the three config values the helper needs (key path, known-hosts path, host). Read them from environment variables with no defaults for the host; the helper does nothing and logs `not configured` if any is missing.

## Plan first (read-only, then stop)
Before any code, report in at most 25 lines: (a) the `~/.ssh` inventory above; (b) `systemctl list-timers --all | grep -i dhan` and `ls /etc/systemd/system | grep -i dhan` (any second scheduler); (c) whether `merdian_live_dashboard.py` is run live (process or unit) and how its button reaches the script; (d) the test framework and how the existing tests run; (e) whether the repo has a mutant runner (if not, say so and add no mutant rows); (f) the exact lines where the success path and each failure branch end, so the helper calls sit in the right place; (g) `git -C ~/meridian-cc status -sb` and whether `origin/main` equals what `~/meridian-engine` runs (`git -C ~/meridian-engine rev-parse --short HEAD`); (h) the pre-registered PASS lines below, adjusted if the code disagrees. Then stop. Only after the operator says "build": tests first, then code, a branch pushed from `~/meridian-cc`, `docs/E1_E3_E10_report.md`.

## Pre-registered PASS lines (tests, all offline)
- **T1** success path: exactly one ssh call with `put dhan`; content has the five keys; `minted_at` matches `^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+05:30$`; the token appears only in stdin, never in argv, stdout, stderr or the log.
- **T2** helper failure (ssh rc 255, timeout, exception, missing config): the script's exit code and `.env` are unchanged, no exception escapes, the log line carries only name, bytes and a reason.
- **T3** empty token: no ssh call.
- **T4** non-rate-limit failure: one `put dhan_login_status` with `failed <ts+05:30>`, no `dhan` file, and the original exception is still raised.
- **T5** rate-limited on the first attempt and on the retry: exit 2, no drop, no status.
- **T6** spacing guard: stamp 100 s old means exit 3, zero Dhan requests, zero ssh calls, message states seconds remaining; stamp 301 s old runs; no stamp runs; the stamp is written before the request and again before the TOTP retry; a crash after the stamp still leaves the stamp.
- **T7** Invalid TOTP then success: exactly two requests, the 30 s sleep (patched), exactly one `dhan` drop carrying the second token, then `ok`.
- **T8** content rules (property test): never `secret` in a key, at most 8 lines, at most 4096 bytes, printable ASCII, no CR, no blank line.
- **T9** nothing under `runtime/`, `.env` or `system_config` is touched by the helper or the guard; the only new file is the stamp in `logs/`.
- Baseline: record the existing test count first; the new total is the old count plus the new tests; state both numbers in the report.

## Not in this build
E9 (crontab), MALPHA's Kite push (E6), the Local (Windows) scheduler, any change to `refresh_dhan_token_aws.py`, deploy to `~/meridian-engine` (the operator's `git pull --ff-only`).

## Report
Print at most 25 lines. Full report to `docs/E1_E3_E10_report.md` with every number labelled MEASURED, OPERATOR-RUN, DERIVED or OWED.
