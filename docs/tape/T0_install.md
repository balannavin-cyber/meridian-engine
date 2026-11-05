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

The last line is `INSTALL OK sha=…`, followed by the `list-timers` row. The next calendar elapse should read 03:20
UTC, which is 08:50 IST.

**Enabling the timer starts the runner once, straight away.** The timer also has `OnBootSec=60`, and systemd fires
an `OnBootSec` that is already in the past as soon as the timer is activated. That start is harmless:
- before 08:50 IST it exits 0 without calling Kite (journal `EARLY_START`, heartbeat `EARLY_EXIT`);
- after 15:40 IST it only re-ships the spool and exits 0;
- on a weekend daytime install it connects, waits 60 s for witnesses, and at the closed-day check writes
  `session/<date>/CLOSED`, then exits 0.

## 4. Smoke test (as user `tape`, with the unit's environment files)

```bash
sudo systemd-run --uid=tape --gid=tape --pipe --wait --collect \
  -p EnvironmentFile=/etc/tape/kite_api.env -p EnvironmentFile=/etc/tape/kite_token.env -p EnvironmentFile=/etc/tape/aws.env \
  -p Environment=PYTHONPATH=/var/lib/tape/app/current -p Environment=TZ=Asia/Kolkata \
  -p WorkingDirectory=/var/lib/tape -p MemoryMax=400M \
  /var/lib/tape/venv/bin/python -m services.tape_runner --smoke
```

The smoke test prints, in order:
1. `SMOKE S3 PASS bucket=meridian-tape-raw region=eu-north-1 key=_smoke/<UTC>.txt etag=… == md5`. This is one real
   `PutObject`, made with the runner's own parameters (ContentMD5, SSE-S3), so the key, bucket and region are proven
   today rather than at Monday's first upload. It never reads anything back (the key is write-only).
2. `SMOKE profile OK`, then `RESOLVED …` per symbol.
3. `subscription list size=188` (4 index/future tokens + 82 NIFTY + 102 SENSEX; SENSEX ± 25 from 2026-11-06 —
   148 with 62 SENSEX before).
4. `connected=True subscribed=True packets=N`.
5. One `CLOCK_SKEW` line per symbol.
6. `SMOKE PASS` (exit 0).

It writes nothing to the spool. In S3 it leaves the single small `_smoke/<UTC>.txt` object.

- **Closed day (weekend or holiday):** a handful of snapshot packets dated the last session, or none. `CLOCK_SKEW`
  then reads `verdict=NOT_EXERCISED` with `stale_excluded=N`. This is a PASS, but the conversion has not been measured
  live. Re-run the smoke test on a trading day after 09:15 to measure it.
- **`SMOKE FAIL: CLOCK SKEW`** (exit 3, banner): the median of (recv − exchange_timestamp) is negative or above 3 s,
  which means the UTC→IST conversion is wrong. Disable the timer (§6) and report.
- **`SMOKE S3 FAIL …`** (exit 5 once the Kite part passes): the ETag did not match, or S3 refused the request. The
  line names the error code (e.g. `AccessDenied`, `PermanentRedirect` for a wrong region). Fix the AWS key, bucket or
  region before 08:50 Monday. Until then the recorder would keep every segment in the spool (2 GB cap).
- `TOKEN_FAIL` (exit 78): the token in `/etc/tape/kite_token.env` is not valid today.
- `connect/subscribe did not succeed` (exit 4).

## 5. Watch it run

```bash
systemctl list-timers tape-runner.timer --no-pager
sudo -u tape cat /var/lib/tape/heartbeat.json; echo        # rewritten each minute
journalctl -u tape-runner --since today --no-pager | grep -E 'TAPE (HB|START|EARLY_START|TOKEN_FAIL|TOKEN_PROBE|CLOSED_CHECK|CLOSED|SPOOL_CAP|SIGTERM|STOP|FATAL|UPLOAD_RETRY)'
sudo -u tape ls -la /var/lib/tape/spool /var/lib/tape/state
```

Heartbeat `state` values:

| State | Meaning |
|---|---|
| `WAITING`, `RECORDING`, `STOPPING`, `DONE` | normal progress through the day |
| `CLOSED` | closed day, see below |
| `TOKEN_FAIL` | At start: exit 78, no restart. Mid-session: after 60 s disconnected, a `profile()` probe was rejected, so segments were closed and uploaded and the runner exited 1. systemd restarts it after 10 s and re-reads `kite_token.env`; the restart exits 78 if the token is still bad. Refresh the token, then `sudo systemctl start tape-runner.service`. |
| `STOPPED` | SIGTERM: segments closed, uploads drained for up to 60 s, exit 0 |
| `EARLY_EXIT` | started before 08:50 IST, exit 0 |
| `SPOOL_CAP` | exit 75, no restart |
| `FAILED` | exit 1, systemd restarts after 10 s |
| `RESOLVE_FAIL` | instrument resolution kept failing until 09:10, exit 1 |

**Closed day.** The verdict is never given before 09:20 IST, and only after 60 s of connected feed. `CLOSED` needs
three things:
1. no packet dated today;
2. both the index and the future witness present and stale, for NIFTY and SENSEX alike;
3. Kite's REST quote confirming both indexes are stale.

Anything less means the runner keeps recording until 15:40. A quote error never closes the day.

Spool file suffixes: `.part` is the segment being written; `.closed` is closed and waiting for the upload thread to gzip
it; `.gz` is waiting for upload. `_r1` / `_c1` suffixes mean a name was already taken, and are never an overwrite.
At the end of the session (~15:40–15:55) the bucket holds
`session/<date>/daily_report_<date>.json` and `session/<date>/MANIFEST.sha256`.

**Daily token:** `kite_token.env` must hold a token valid for the day **before 08:50 IST**. T0 does not refresh it.
A stale token shows as `TOKEN_FAIL` in the heartbeat and the journal.

## 6. Stop / roll back

```bash
sudo systemctl disable --now tape-runner.timer      # no further starts
sudo systemctl stop tape-runner.service             # SIGTERM: closes segments, uploads for up to 60 s, then exits 0
```

The spool is never deleted by the runner except after a verified upload (ETag == md5). The next start re-ships
whatever is left, under its original date keys.

## 7. T0.1: silence watchdog and special sessions

**Silence watchdog.** Inside the recording window (09:15-15:30 IST, or the special-session window: Muhurat 2026-11-08 is 14:20-15:40, NSE/FAOP/76940), if no websocket
frame of any kind (tick packet or 1-byte heartbeat) arrives for 15 s (`config.SILENCE_S`, hard minimum 5 s), the
runner aborts the socket and the library reconnects after 1, 2, 4, 8, 15, 15 ... s. The journal shows
`WATCHDOG_TRIP age=<s> n=<k>`; the heartbeat JSON and the daily report carry `watchdog_trips`, `watchdog_errors` and `frame_errors` (the frame hook failed and was contained; expect 0). The watchdog is not armed before 09:15 (follow-up pending `frames_hb` data).
A watchdog failure never stops recording; exit codes 75 and 78 are unchanged.

**G2 (amended 2026-11-03):** no unexplained gap; an external gap over 60 s is allowed if logged, with detection
delay <= 20 s.

**Special sessions.** `services/tape_runner/special_sessions.json` lists dates that replace the default 09:15-15:30
window (today: Sun 2026-11-08 Muhurat, F&O 14:20-15:40 per NSE/FAOP/76940; the recorder starts 13:55 and stops 15:50). `install.sh` writes a one-off
`tape-runner-special-<date>.timer` (start 25 min before open, `Persistent=false`) for every future date in the file and
removes past ones; it also refuses to run from 60 min before a special open to 30 min after its close (Muhurat: 13:20-16:10), and refuses whenever the guard cannot be evaluated (`session.py --in-window` answers 0 inside, 10 outside; any other code, including the 1 of a SyntaxError, refuses). The weekday timer
is untouched. Counters: see T0_plan.md section 14.
