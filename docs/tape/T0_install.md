# T0 install — tape raw recorder (operator commands)

Branch `tape/t0-raw` on `staging` (`balannavin-cyber/meridian-tape-staging`). Design: `docs/tape/T0_plan.md`.
The recorder runs on the **retail box** (`ubuntu@ip-172-31-30-166`) only. It touches no database, no Dhan account
and not the production box, and it places no orders.

## 1. Merge into `meridian-engine` `main` (Local, Windows)

```powershell
cd C:\GammaEnginePython
git remote get-url tape-staging 2>$null; if ($LASTEXITCODE) { git remote add tape-staging git@github.com:balannavin-cyber/meridian-tape-staging.git }
git fetch tape-staging tape/t0-raw
git switch main
git pull --ff-only origin main
git log --oneline -1 tape-staging/tape/t0-raw          # expect the head SHA from the session report
git merge --ff-only tape-staging/tape/t0-raw           # base is 232a3bc; if main has moved: git merge --no-ff tape-staging/tape/t0-raw
git push origin main
```

What the merge changes on the engine: it adds `services/`, `merdian_compute/tape/`, two test files and
`docs/tape/T0_*.md`, and it extends `tests/run_offline.sh` from 30 to 32 steps. `pyproject.toml` and
`merdian_compute/__init__.py` are unchanged, so the retail contract is unaffected. AWS shadow receives the files on
its next `git pull`, but nothing there schedules or imports them.

## 2. Pull `main` on the retail box

```bash
cd ~/meridian-tape-dev
git fetch -q origin && git merge --ff-only origin/main
git log --oneline -1
```

## 3. Install (sudo; refused Mon–Fri 08:30–15:45 IST)

```bash
sudo sed -n 's/=.*//p' /etc/tape/kite_api.env /etc/tape/kite_token.env /etc/tape/aws.env
#   expect NAMES only: ZERODHA_API_KEY / ZERODHA_ACCESS_TOKEN / AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION
cd ~/meridian-tape-dev && sudo bash services/tape_runner/install.sh
```

`install.sh` does the following:
- refuses to run during market hours or without root;
- checks that user `tape` and the three env files exist (it never reads their contents);
- checks `/var/lib/tape/venv` for kiteconnect 5.2.2 and boto3 1.43.123 (it never creates or modifies the venv);
- copies the committed `services/` tree at HEAD to `/var/lib/tape/app/<sha12>`, with `current` pointing at it;
- creates `spool`, `state` and `manifest` under `/var/lib/tape`;
- installs the unit and the timer, runs `systemd-analyze verify`, and enables and starts **the timer only**.

The last line is `INSTALL OK sha=…`, followed by the `list-timers` row. The next elapse should read 03:20 UTC, which
is 08:50 IST.

## 4. Smoke test (as user `tape`, with the unit's environment files)

```bash
sudo systemd-run --uid=tape --gid=tape --pipe --wait --collect \
  -p EnvironmentFile=/etc/tape/kite_api.env -p EnvironmentFile=/etc/tape/kite_token.env -p EnvironmentFile=/etc/tape/aws.env \
  -p Environment=PYTHONPATH=/var/lib/tape/app/current -p Environment=TZ=Asia/Kolkata \
  -p WorkingDirectory=/var/lib/tape -p MemoryMax=400M \
  /var/lib/tape/venv/bin/python -m services.tape_runner --smoke
```

The smoke test prints, in order: `SMOKE profile OK`, `RESOLVED …` per symbol, `subscription list size=148`
(4 index/future tokens + 82 NIFTY + 62 SENSEX), `connected=True subscribed=True packets=N`, one `CLOCK_SKEW` line per
symbol, then `SMOKE PASS` (exit 0). It writes nothing to the spool or S3.

- **Closed day (weekend or holiday):** a handful of snapshot packets dated the last session, or none. `CLOCK_SKEW`
  then reads `verdict=NOT_EXERCISED` with `stale_excluded=N`. This is a PASS, but the conversion has not been measured
  live. Re-run the smoke test on a trading day after 09:15 to measure it.
- **`SMOKE FAIL: CLOCK SKEW`** (exit 3, banner): the median of (recv − exchange_timestamp) is negative or above 3 s,
  which means the UTC→IST conversion is wrong. Disable the timer (§6) and report.
- `TOKEN_FAIL` (exit 78): the token in `/etc/tape/kite_token.env` is not valid today.
- `connect/subscribe did not succeed` (exit 4).

**What the smoke test cannot see:** S3. It makes no `PutObject`, so the first proof that the AWS key and bucket work
is the first segment upload on Monday (about 09:00 IST). If S3 rejects uploads, segments stay in the spool (2 GB cap)
and the heartbeat's `upload_queue` and `uploads.*.failed_attempts` grow.

## 5. Watch it run

```bash
systemctl list-timers tape-runner.timer --no-pager
sudo -u tape cat /var/lib/tape/heartbeat.json; echo        # rewritten each minute
journalctl -u tape-runner --since today --no-pager | grep -E 'TAPE (HB|START|TOKEN_FAIL|CLOSED|SPOOL_CAP|STOP|FATAL|UPLOAD_RETRY)'
sudo -u tape ls -la /var/lib/tape/spool /var/lib/tape/state
```

Heartbeat `state` values: `WAITING`, `RECORDING`, `CLOSED`, `STOPPING`, `DONE`, `TOKEN_FAIL` (exit 78, no restart),
`SPOOL_CAP` (exit 75, no restart), `FAILED` (exit 1, systemd restarts after 10 s), `RESOLVE_FAIL`.
At the end of the session (~15:40–15:55) the bucket holds
`session/<date>/daily_report_<date>.json` and `session/<date>/MANIFEST.sha256`.

**Daily token:** `kite_token.env` must hold a token valid for the day **before 08:50 IST**. T0 does not refresh it.
A stale token shows as `TOKEN_FAIL` in the heartbeat and the journal.

## 6. Stop / roll back

```bash
sudo systemctl disable --now tape-runner.timer      # no further starts
sudo systemctl stop tape-runner.service             # stop a running session (segments stay in the spool)
```

The spool is never deleted by the runner except after a verified upload (ETag == md5). The next start re-ships
whatever is left, under its original date keys.
