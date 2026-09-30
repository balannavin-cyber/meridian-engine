---
paths:
  - "**/*.bat"
  - "**/*.ps1"
  - "**/crontab*"
  - "deploy/systemd/**"
  - "docs/registers/aws_crontab*.txt"
---

# Schedulers, crontabs and services

Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028). Rule text is
unchanged; only its location moved.

- ❌ Reading `systemctl is-active merdian-wsfeed` as a health signal. Its normal daily shutdown lands in `failed (Result: timeout)`. Read the journal, or the tick/breadth row counts. (Session 71 / TD-S71-NEW-4.)
- ❌ Running `merdian_start.py` on AWS — this script uses `creationflags=CREATE_NO_WINDOW` (Windows-only) and hardcoded Windows paths. It will hang or error on Linux. Session 13: caused a frozen SSM terminal requiring EC2 reboot. AWS uses `python3 gamma_engine_supervisor.py` or individual script launches.
- ❌ Appending to a Windows batch file with `Add-Content` when there is an `exit /b` line — the appended line runs after `exit /b` and never executes. Always use string replacement to insert before the exit line. (Session 13 bat file patch.)
- ❌ Installing a crontab with `crontab <file>` from a long path. **Debian's `crontab.c` truncates the filename at ~100 chars (`MAX_FNAME`)**, and scratchpad paths exceed it — the S81 `disk_guard` install failed harmlessly on a truncated path. **Use `crontab - < file`.** Harmless when it fails loudly; the hazard is that a truncated path can name a *different* existing file.
- ✅ **A register entry written from inference decays differently from one written from measurement.** Session 71 audited five carried items and **four** described a system that measurement did not find: TD-NEW-7 said "no automation" when the automation had existed for a month and worked; TD-S69-NEW-1 named two Supabase tables as consumers of an EC2 root volume; ADR-023's Context said a floor was "still not written" when it existed as warn-only; "ADR-006 COMPLETE" was certified by enumerating Task Scheduler tasks, so an operator-invoked script could not have been in the sample. **Before executing a filed fix, verify the filed diagnosis still holds.** The fix is downstream of a claim that may have expired.
- **Orchestrator crontab syntax:** `cd /path && source .env && flock -n /lock timeout 90 python3 script.py` (cd and source BEFORE flock, relative paths work, env available). (S48)
- **Cron graceful degradation:** Script exit_code=0 on known failures OK (404 table missing), but log the condition even on success for operational visibility. (S48)
- **Cron `SHELL=/bin/bash` is mandatory as crontab line 1 on AWS (S53):** cron defaults to `/bin/sh` (dash), which lacks the `source` builtin — every `cd … && source .env && python3 …` chain dies silently with `/bin/sh: source: not found` into discarded cron mail. A dropped SHELL directive (crontab reinstall 00:47 UTC 2026-06-12) caused a ~28h total capture/compute blackout. Probe: `/bin/sh -c 'source .env && echo CHAIN_OK'` plus `pwd; echo HOME=$HOME; SHELL=$SHELL`. Verify the SHELL line is present as line 1 after ANY crontab change.
- **Live ingest cron form is UNQUOTED `bash run_ingest.sh NIFTY FULL` (S53):** `run_ingest.sh` self-sources `.env`; do NOT reintroduce S49's single-quoted `'NIFTY FULL'` arg. The unquoted form is what is live and working.
- **A month-long "frozen table" whose writer was declared "unidentified/decoupled" is almost always a scheduler/orchestration gap after an environment migration, not a mystery writer (S67).** The S66 breadth freeze was closed not by finding a hidden builder but by reading `run_equity_eod_until_done.py` (which names the builder as `DAILY_REBUILD_SCRIPT`) and confirming Local was retired at AWS migration (~Jun 7; all 22 Local scheduled tasks correctly Disabled per ADR-006 — NOT to be re-enabled). The canonical `40 10` AWS EOD cron existed all along and the cron daemon fires (sentinel-tested) — it was **self-aborting**: builder rc=1 on a cold-day 95%-gate miss broke the whole loop (L182) before the cursored ingest drained. Diagnostic order that worked: grep the writer → read its invoker → read the loop's stop-logic → check the cron → sentinel-test the daemon. When a scheduled job "fires but writes nothing", test the daemon AND read the loop's break conditions before hypothesizing a missing job.
- **The breadth prev-close baseline is refreshed by a cron on MERDIAN AWS — `35 3 * * 1-5` (09:05 IST), AFTER the 03:00 UTC token sync (S59).** It was missing from the AWS-only hosts crontab, freezing the baseline 2026-05-20→2026-06-24 and making breadth read BULLISH on down days — a verbatim re-run of **C-09 / ADR-001**. Re-added + verified self-firing 03:35 UTC on the 06-24 open. A stale reference price silently invalidates correct data; suspect baseline freshness first when a derived read contradicts an independent source (VRD/chart). Codified §D.25.2.
