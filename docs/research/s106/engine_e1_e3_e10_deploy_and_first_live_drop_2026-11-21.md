# Engine lane E1/E3/E10: build, deploy, first live drop (2026-11-21)

Labels: MEASURED (read from output), OPERATOR-RUN (operator ran, pasted output), OWED.

## Build (CC, tmux `e1`, branch `e1-e3-e10`)
- Commit `e4ef1b8` on `ba505cf`; 7 files (1939 insertions, 83 deletions): `dhan_drop.py` (149 lines, new), `refresh_dhan_token.py` (329), `bin/dhan_login.sh` (27, new), `tests/test_dhan_drop.py` (840), `tests/test_dhan_login_guard.py` (613), `tests/run_offline.sh` (230, now 42 steps), `docs/E1_E3_E10_report.md`. MEASURED (wc -l, git show --stat).
- Standalone tests: drop file `mutants 8, killed 8, surviving 0`; guard file `mutants 9, anchor failures 0, killed 9, surviving 0`. OPERATOR-RUN, full output reviewed.
- Late additions this session: T3b leak checks, whitespace-only client_id, newline in `expires`, valid-call control, mutants M7/M8 (drop file); future-dated stamp cell and mutants M8/M9 (guard file). Report corrected from 12 to 11 T6 cells (`grep -c '^def t6_'` = 11).
- Commit trailers: `Co-Authored-By: Claude Sonnet 5.5` and `Claude-Session`. Staged by the operator by name (CC's deny rule blocks naming `refresh_dhan_token` in a Bash command; `git add -u` was declined as a bulk stage).
- Pushed to `origin/e1-e3-e10` (OPERATOR-RUN, `git ls-remote` shows `e4ef1b8`). No PR opened.
- Merged to origin main by a direct fast-forward push (`git push origin main`, `ba505cf..e4ef1b8`, OPERATOR-RUN 2026-11-21 ~08:45 IST). GitHub reported `Bypassed rule violations for refs/heads/main: Cannot update this protected ref` — main is protected and the operator's admin rights bypassed it. Engine local main, origin/main and the tested commit are all `e4ef1b8`. If the rule should bind admins, set "include administrators" in branch protection (operator decision).

## Deploy (OPERATOR-RUN, engine box `~/meridian-engine`)
- Fast-forward `79efb0b` -> `e4ef1b8` by `git fetch /home/ssm-user/meridian-cc e1-e3-e10` + `git merge --ff-only FETCH_HEAD`. It also brought two docs/data-only futoi commits and a one-line `.gitattributes`.
- Three `MERIDIAN_RETAIL_DROP_*` lines (KEY, KNOWN_HOSTS, HOST) appended to engine `.env`; count 3. Backup `.env.bak_pre_e1` made with `cp -p`, then deleted after the first live drop was confirmed.
- File modes: `.env` and three older backups (`.env.bak_20260803_040202`, `.env.bak_20260812_032352`, `.env.bak_20260812_032445`) were 644/664; all set to 600 (OPERATOR-RUN, `ls -l` confirmed). Older backups (March/April/August) not deleted; operator decision.
- `py_compile` and `import dhan_drop` OK (`helper ok`).
- Full suite on the engine box, Saturday (override of the 15:40 gate; the box guard is Mon-Fri only): `SUITE EXIT=0`, `OFFLINE PASS`, steps 41/42 and 42/42 PASS, only `DEX_RECOMPUTE PASS (11 ok, 2 observed, 0 failed)` matches `fail`. About 20 minutes.
- E9 installed: crontab `50 2 * * 1-5` -> `50 2 * * *`, one-line diff, backup `~/crontab.bak_pre_e9_*`.

## First live drop (MEASURED, 2026-11-21 08:20 IST = 02:50 UTC)
- Engine `cron.log`: `DHAN DROP name=dhan bytes=418 ok reason=sent`, `DHAN DROP name=dhan_login_status bytes=29 ok reason=sent`, then `DHAN TOKEN REFRESH SUCCESS`, expiry `2026-11-22T08:20:03.45`, Supabase sync OK. Stamp `logs/dhan_login_attempt.stamp` written 02:50 UTC.
- Retail `journalctl -t retail-drop`: `02:50:06 sender=engine name=dhan bytes=418 ok` and `02:50:08 sender=engine name=dhan_login_status bytes=29 ok`. No values logged.
- Retail inbox afterwards: `dhan` file gone, `dhan_login_status` (29 bytes, 0640, retaildrop:retail-adopt) remains (the adopter does not process the status file).
- Retail adopter `broker-feed-adopt.service` logged at 02:50:36 UTC `{"broker":"dhan","kind":"stored","msg":"feed_adopted"}`, 28 s after the drop landed.
- Adopter window summary (MEASURED, `feed_adopt_window_done` at 03:15:07 UTC = 08:45:07 IST): passes 300, kite 300, dhan 60, stored 1, and every other counter 0 (older, stale, invalid, terminal, retry, store-errors, gateway-down, pass-errors, unreadable, not-regular, too-big, replaced, gone, status marked/ignored/malformed/no-account). Unit `Result=success`, `ExecMainStatus=0`, `MemoryMax=314572800` (300 MiB). Only 7 log lines in the window; no OOM/kill/warning/error/alert lines.
- Not measured: memory peak. `MemoryPeak=[not set]` on this systemd, so no peak figure exists; evidence for memory is only exit 0 and no OOM lines.
- Chain closed end to end, live: engine login -> drop -> retail adopt -> stored.
- Test-stub sizes (about 120-130 bytes) are not real sizes; a real token gives 418.
- Note: the `broker-feed-adopt.timer` description string still reads "(not installed: D6)" although the unit is loaded and active; stale description text, not a fault.

## Owed
- Sunday 2026-11-22 08:20 IST run as the second data point: `stat -c '%U %a' .env` stays `ssm-user 600`, `cron.log` shows `DHAN TOKEN REFRESH SUCCESS`, retail syslog shows both drops, adopter logs `feed_adopted`.
- Decide whether to delete the older `.env.bak_*` / `.env.save*` files.
- Retail side (operator): R3 retire of the old shared keyring after a clean weekday 08:10 watcher read; GitHub setting to disable squash/rebase merging; AMI `ami-01bc48c504bd8767f` + snapshot deletion; Kite/MALPHA report-back; record pass (TD-MR-119+).
- Older: confirm MALPHA Elastic IP `16.192.223.197`; update the unit description text (D6).
