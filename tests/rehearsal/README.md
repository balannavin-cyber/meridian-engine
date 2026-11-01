# T0 load rehearsal

Goal: prove that the real runner survives open-time load before Monday 2026-11-02. It runs as user `tape`, under the
unit's own fences, with the real `aws.env`, the real clock and real S3, at 2x and 4x the measured open rate.

`tests/` is never installed by `install.sh`. The rehearsal is staged separately into `/var/lib/tape/rehearsal_app`.

## What is real, and what is synthetic

| Real | Synthetic or rehearsal-only |
|---|---|
| `Recorder`, `SegmentWriter`, the upload thread, gzip, ETag verification, manifest, daily report, heartbeat | `SyntheticKite` (profile, instruments, ltp, quote) and `SyntheticTicker` in place of `KiteTicker` (`feed.py`) |
| boto3 S3 client, region from `aws.env`, bucket `meridian-tape-raw` | keys under `_rehearsal/<UTC id>/` via the runner's own `TAPE_KEY_PREFIX` hook |
| systemd fences: `MemoryMax=400M`, `CPUWeight=20`, `Nice=10`, `LimitAS`, `ProtectSystem=strict`, user `tape` | a local copy of every uploaded object in `/var/lib/tape/rehearsal_keep/<id>` (`TAPE_REHEARSAL_KEEP` hook), because the key is write-only |
| wall clock, 5-minute segments, boundaries | session times moved to now (start = next whole minute); own root `/var/lib/tape/rehearsal_root/<id>` |

**Load.** 1x is 58,000 packets per symbol per 5-minute segment, the open rate measured on this box. That is 386.7
packets/s in total, spread over the real 148-token window: 82 NIFTY and 62 SENSEX options, 2 indexes and 2 futures.
Packets are full-mode with 5+5 depth levels, and the exchange timestamps are built the way kiteconnect builds them.
Every packet carries `rehearsal_seq`, numbered 0, 1, 2 … per token with no gaps, and `rehearsal_batch`, the id of the
`on_ticks` call that delivered it. The recorder stores both verbatim.

## Operator commands (outside Mon–Fri 08:30–15:45 IST)

```bash
# 0. the branch is on the box and checked out in a clone the stage script can read
cd ~/meridian-tape-dev && git fetch -q staging && git log --oneline -1 staging/tape/t0-rehearsal
#    (after approval it is merged; until then: git worktree add ~/wt-reh staging/tape/t0-rehearsal && cd ~/wt-reh)

# 1. stage (root-owned copy for user tape + the rehearsal's own directories)
sudo bash tests/rehearsal/stage.sh

# 2. optional: the generator's own CPU (no recorder), to read P4 net of the harness
for L in 2x 4x; do
sudo systemd-run --unit=tape-rehearsal-cal-$L --uid=tape --gid=tape --pipe --wait --collect \
  -p Environment=TZ=Asia/Kolkata -p WorkingDirectory=/var/lib/tape -p MemoryMax=400M -p CPUWeight=20 -p Nice=10 \
  -p LimitAS=2000000000 -p ProtectSystem=strict -p ReadWritePaths=/var/lib/tape -p NoNewPrivileges=true \
  -p PrivateTmp=true -p ProtectHome=true \
  /var/lib/tape/venv/bin/python /var/lib/tape/rehearsal_app/tests/rehearsal/run_rehearsal.py --calibrate $L:60s
done

# 3. the rehearsal: 35 min at 2x (seven segments, six boundaries) then 15 min at 4x; ~51 min wall
sudo systemd-run --unit=tape-rehearsal --uid=tape --gid=tape \
  -p EnvironmentFile=/etc/tape/aws.env \
  -p Environment=TZ=Asia/Kolkata -p Environment=PYTHONDONTWRITEBYTECODE=1 -p Environment=PYTHONUNBUFFERED=1 \
  -p Environment=HOME=/var/lib/tape -p WorkingDirectory=/var/lib/tape \
  -p MemoryMax=400M -p CPUWeight=20 -p Nice=10 -p LimitAS=2000000000 \
  -p ReadWritePaths=/var/lib/tape -p ProtectSystem=strict -p NoNewPrivileges=true -p PrivateTmp=true -p ProtectHome=true \
  /var/lib/tape/venv/bin/python /var/lib/tape/rehearsal_app/tests/rehearsal/run_rehearsal.py --schedule 2x:35m,4x:15m
journalctl -fu tape-rehearsal | grep -vE 'TAPE (HB|SUBSCRIBE)'     # ends with "REHEARSAL DONE exit=0"; Ctrl-C to leave

# 4. verify + score the PASS criteria (last line: REHEARSAL VERDICT PASS|FAIL|INCOMPLETE; exit 0/1/3)
#    INCOMPLETE = a criterion could not be measured (e.g. P6 needs two full 5-minute intervals per phase)
sudo -u tape /var/lib/tape/venv/bin/python /var/lib/tape/rehearsal_app/tests/rehearsal/verify_rehearsal.py --latest

# 5. optional: prove the verifier can fail on this run's data (copies the run to /tmp; ~1 GB free needed)
sudo -u tape /var/lib/tape/venv/bin/python /var/lib/tape/rehearsal_app/tests/rehearsal/selftest.py \
  --run "$(sudo ls -d /var/lib/tape/rehearsal_out/* | tail -1)"

# 6. hand back for analysis (metrics, samples, heartbeats, upload log; no credentials in any of them)
sudo tar -C /var/lib/tape/rehearsal_out -czf /tmp/rehearsal_out.tgz . && sudo chown ubuntu /tmp/rehearsal_out.tgz
```

Stop early with `sudo systemctl stop tape-rehearsal`. The runner's SIGTERM path closes the segments, drains uploads
for up to 60 s and exits 0. The verifier then scores whatever was recorded.

Clean up afterwards: `sudo rm -rf /var/lib/tape/rehearsal_{root,keep,out}`. The objects under `_rehearsal/` in the
bucket cannot be deleted with the runner's write-only key. Remove them from the console, or with a lifecycle rule on
the `_rehearsal/` prefix.

## PASS criteria (fixed 2026-11-01, before the run)

1. Zero lost or duplicated packets.
2. Maximum `on_ticks` stall under 200 ms.
3. Peak RSS under 150 MB.
4. Mean CPU under 40 % of one core at 2x.
5. Every upload verified by ETag on the first attempt, with no retries.
6. Spool does not trend upward.

`verify_rehearsal.py` prints each criterion with its numbers, and its docstring states what makes each check fail.
`selftest.py` shows that each integrity check fails on a tampered copy.

**What the rehearsal cannot see:**
- anything S3 does after acknowledging a `PutObject` (nothing is read back, by design);
- the real Kite websocket's own parsing cost (the synthetic generator stands in for it, and step 2 measures it);
- real market burstiness beyond the flat 2x and 4x rates;
- the 08:55–09:15 timeline and the closed-day path, which are covered by the offline guards instead.
