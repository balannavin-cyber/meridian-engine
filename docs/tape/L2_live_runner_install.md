# Tape live runner (stage 2a): install note for the production box

**Status: instructions only.** Nothing in this repository installs anything or touches a box. Every command below is run by the
operator, as written, on the production box (AWS SSM session). The runner is FILE-ONLY: it reads `s3://meridian-tape-raw` (instance
role) and the chain snapshots (a read-only database role) and writes files under `/var/lib/tape-live`. It never writes to S3 or to
the database. Plan: `docs/tape/L2_live_runner_plan.md`. Templates: `docs/tape/L2_live_runner.service.template`,
`docs/tape/L2_live_runner.timer.template`.

Rules that apply while doing this (CLAUDE.md):
- **Rule 19:** never `cat`, `grep`, `bash -x` or `set -x` the environment file or anything that sources it. To compare a value across
  places, compare hashes (`cut -d= -f2- /etc/tape-live/tape-live.env | tr -d '\r\n' | sha256sum`), never values.
- **Rule 23:** no fixture-suite run between 08:30 and 15:40 IST on a trading day. The recorded-day rehearsal (step 7) is a run of the
  runner itself, not the fixture suite, but it is also done outside market hours. The first manual live start (step 9) is the
  market-hours run that ruling R-D covers.
- **Rule 24:** the code reaches the box by `git pull` / `git archive` of a pushed commit, never by editing on the box.

## 0. Preconditions the operator confirms first

| Check | Command (as the SSM user) | Expect |
|---|---|---|
| Programs present | `command -v aws psql python3` | three paths; if `psql` is missing: `sudo apt-get install -y postgresql-client` |
| Python | `python3 --version` | 3.10 or newer (the runner is written for 3.10; it has only been run on 3.12 by its author) |
| Free disk | `df -h /var/lib` | at least 1 GB free (the runner refuses to start below 1 GB) |
| Free memory | `free -m` | at least 700 MB available beyond the engine |
| Attached security group, if a rule ever needs editing | IMDSv2 query from CLAUDE.md (S39) | not needed for this install |

## 1. Dedicated OS user (no shell, no sudo, no groups)

```bash
sudo useradd --system --home-dir /var/lib/tape-live --create-home --shell /usr/sbin/nologin --user-group tapelive
sudo chmod 700 /var/lib/tape-live
id tapelive            # expect: uid/gid only; no sudo, no wheel
sudo -l -U tapelive    # expect: "User tapelive is not allowed to run sudo"
```

## 2. The code (an exported commit, owned by root, read-only to the runner)

Run from a clean checkout of `tape-staging` branch `tape/live-l2` on the box (or any host that can copy the result). `<SHA>` is the
full 40-hex commit the operator has verified equals the reviewed commit.

```bash
SHA=<40-hex commit>
sudo mkdir -p /opt/tape-live/$SHA
git archive $SHA merdian_compute/__init__.py merdian_compute/tape services/__init__.py services/tape_live \
    services/tape_offline services/tape_db services/tape_runner/special_sessions.json | sudo tar -x -C /opt/tape-live/$SHA
echo $SHA | sudo tee /opt/tape-live/$SHA/CODE_SHA > /dev/null
sudo chown -R root:root /opt/tape-live && sudo chmod -R go-w /opt/tape-live
sudo -u tapelive python3 -I -c "import sys; sys.path.insert(0,'/opt/tape-live/$SHA'); import services.tape_live.cli" \
    && echo IMPORT OK
```

`services/tape_live/__init__.py` is not tracked (`.gitignore` pattern `_*.py`); `services.tape_live` loads as a namespace package, as
it does in the offline suite.

## 3. The state directory and the environment file

The environment file holds exactly one variable, the connection string of a **read-only** database role (the `merdian_ro` class).
The operator types it into the editor; it is never pasted into a chat, a shell history line or a command argument.

```bash
sudo install -d -o tapelive -g tapelive -m 700 /var/lib/tape-live
sudo install -d -o root -g root -m 755 /etc/tape-live
sudo install -o tapelive -g tapelive -m 600 /dev/null /etc/tape-live/tape-live.env
sudo -u tapelive nano /etc/tape-live/tape-live.env
```

In the editor, one line (a single variable, no quotes; the value is the connection string of the read-only role with
`sslmode=require`, in the usual `postgresql://` form):

```
TAPE_LIVE_RO_DSN=<connection string of the read-only role>
```

Check the mode and owner (this prints neither the value nor any part of it):

```bash
stat -c '%a %U:%G %n' /etc/tape-live/tape-live.env     # expect: 600 tapelive:tapelive /etc/tape-live/tape-live.env
sudo -u tapelive sh -c '[ -n "$(cut -d= -f2- /etc/tape-live/tape-live.env)" ] && echo value-present'
```

The runner refuses to start if any of the three AWS key variables is set in its environment, and its S3 access is the instance
role only. Do **not** add AWS keys to this file.

## 4. Install the unit files (the timer is installed, NOT enabled)

```bash
SHA=<40-hex commit>
sed "s/@CODE_SHA@/$SHA/" docs/tape/L2_live_runner.service.template | sudo tee /etc/systemd/system/tape-live.service > /dev/null
sudo cp docs/tape/L2_live_runner.timer.template /etc/systemd/system/tape-live.timer
sudo systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/tape-live.service
```

**Do not run `systemctl enable` or `systemctl start` on `tape-live.timer`.** Enabling the timer is a separate, later decision.

## 5. Pre-checks as the runner user (read-only)

```bash
sudo -u tapelive env AWS_DEFAULT_REGION=eu-north-1 AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
    aws sts get-caller-identity
sudo -u tapelive env AWS_DEFAULT_REGION=eu-north-1 AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null \
    aws s3api list-objects-v2 --bucket meridian-tape-raw --prefix session/<a recent trading day>/ --max-items 5
```

Expect the instance role in the first, and a few `subscriptions_*.json` keys in the second. If the second says `AccessDenied`, the
role has no read access to the bucket: stop and report (plan open item P-7); do not add keys.

The runner's own check (environment, code sha, and the database role: it refuses unless the role is read-only on the snapshot
relation). It prints `CHECK PASS` or one refusal line, and never a value:

```bash
sudo systemd-run --pipe --wait --collect --uid=tapelive --gid=tapelive \
    -p EnvironmentFile=/etc/tape-live/tape-live.env -E AWS_DEFAULT_REGION=eu-north-1 \
    -p WorkingDirectory=/opt/tape-live/$SHA -p NoNewPrivileges=yes -p PrivateTmp=yes \
    /usr/bin/python3 -m services.tape_live.cli live --day <a recent trading day> --out /var/lib/tape-live/check \
    --source s3 --chain psql --clock sim --check
```

## 6. What the runner writes

Under `/var/lib/tape-live/<day>/`: `heartbeat.json` (state, last cycle, lag, memory, errors), `live_metrics.csv` (one row per cycle),
`arrival_log.csv` (every object and chain run first seen, with its S3 LastModified), `state.json`, `runner.log`, `raw/` (the
downloaded segments), and `live/` (the same files `cli replay` writes: `cycles/`, `tape_live_{cycle,events,wall,label}.csv`,
`run_manifest.json`).

## 7. Recorded-day rehearsal, outside market hours, before any live day

Replays a past trading day against the real bucket and the real database with a simulated clock, under the same caps as the unit.
Objects appear in the order of their S3 `LastModified`; chain rows by their `ts`.

```bash
sudo systemd-run --pipe --wait --collect --uid=tapelive --gid=tapelive \
    -p EnvironmentFile=/etc/tape-live/tape-live.env -E AWS_DEFAULT_REGION=eu-north-1 \
    -p WorkingDirectory=/opt/tape-live/$SHA -p Nice=10 -p CPUQuota=50% -p MemoryMax=700M -p MemorySwapMax=0 \
    -p OOMScoreAdjust=500 -p NoNewPrivileges=yes -p PrivateTmp=yes -p ProtectSystem=strict \
    -p ReadWritePaths=/var/lib/tape-live \
    /usr/bin/python3 -m services.tape_live.cli live --day <past trading day> --out /var/lib/tape-live/rehearsal \
    --source s3 --chain psql --clock sim --start 08:50
```

Then compare with a plain replay of the downloaded copy (byte comparison of the live outputs; `live_run_id` differs by design in
Phase A):

```bash
sudo -u tapelive python3 -m services.tape_live.cli replay --day <day> --raw /var/lib/tape-live/rehearsal/<day>/raw \
    --chain-runs <the two chain export CSVs of that day> --out /var/lib/tape-live/rehearsal/replay
```

## 8. Stop and kill switch

```bash
sudo -u tapelive touch /var/lib/tape-live/KILL        # the runner exits 0 at its next check (within seconds), state "killed"
sudo systemctl stop tape-live.service                 # SIGTERM: same, state "stopped"
sudo rm /var/lib/tape-live/KILL                       # before the next start
cat /var/lib/tape-live/<day>/heartbeat.json
```

## 9. First live day: a manual start

```bash
sudo systemctl start tape-live.service
journalctl -u tape-live.service -n 20 --no-pager
cat /var/lib/tape-live/$(TZ=Asia/Kolkata date +%F)/heartbeat.json
tail -n 3 /var/lib/tape-live/$(TZ=Asia/Kolkata date +%F)/live_metrics.csv
```

The runner exits by itself after the 15:45 IST cycle (state `done`). Exit codes: 0 done / killed / stopped / no session; 1 unexpected
error; 2 refused at start; 3 memory or disk cap. Codes 2 and 3 are not restarted by the unit.

Starting mid-day is supported: the runner rebuilds from the objects already in S3 and continues at the current grid point (grid
points that passed are recorded as missed, never back-filled). Running it twice on a finished day changes nothing.

## 10. Uninstall

```bash
sudo systemctl stop tape-live.service
sudo rm -f /etc/systemd/system/tape-live.service /etc/systemd/system/tape-live.timer && sudo systemctl daemon-reload
sudo rm -rf /opt/tape-live
# keep /var/lib/tape-live (the measurements) until they have been read; then:
# sudo userdel tapelive && sudo rm -rf /var/lib/tape-live /etc/tape-live
```
