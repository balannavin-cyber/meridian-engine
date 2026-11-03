# T0.1 afternoon run list (after 15:45 IST)

Branch `tape/t0-1`. Written 2026-11-03. **Nothing below has been run for this head**: the changes it covers (frame-error
containment, install-guard exit code, Muhurat close 15:40 per NSE/FAOP/76940, the new tests and mutants) were written
without running any test, because the live recorder runs 08:50-15:40 on this box.

Rules for the whole list
- Start only after **15:45 IST** (15:40 is when CLAUDE.md rule 23 lifts; 15:45 is the rehearsal and stage guard).
- Fixture suites and mutants run under an explicit `ulimit -v` (rule 23). Rehearsals use 2000000 (the unit's `LimitAS`).
- Run the steps in this order and stop at the first FAIL. A FAIL is read, not re-run: if a new cell fails, the message
  names the belief that broke. Do **not** change an expected value to make it pass (rule 0); fix the code or the belief.
- "Counts" below were counted from the source (guards in `GUARDS`, cells in the unit functions, mutants in `M`), not
  measured. The criterion is `PASS` and numerator == denominator; if a printed denominator differs from the one here,
  say so in the report rather than treating it as noise.
- Run everything from the repo clone, on the branch at the pushed head:

```bash
cd ~/meridian-tape-dev
git fetch -q staging && git rev-parse --short HEAD staging/tape/t0-1     # both lines must be identical
git status --short                                                          # only " M .claude/settings.json" (intentional, uncommitted)
mkdir -p ~/tape_reh
```

## 1. T0.1 suite (the new cells are `fo-close`, `frame-errors`, and the extended `timer-sync`, `special-day`, `processor-special`)

```bash
( ulimit -v 700000; python3 tests/test_tape_t0_1.py ) 2>&1 | tee ~/tape_reh/t0_1.log | tail -40
```
PASS line (last line): `TAPE T0.1 PASS (11/11 guards, 7/7 unit checks)`

## 2. T0 suite

```bash
( ulimit -v 700000; python3 tests/test_tape_t0.py ) 2>&1 | tee ~/tape_reh/t0.log | tail -5
```
PASS line: `TAPE T0 PASS (G/G guards, U/U unit checks)` with G == the guard count and U == the unit count
(`run_offline.sh` says 21 guards; the file's docstring still says 12, which is stale). This suite also runs the T0.1
changes to `recorder.py` / `stats.py` through the T0 guards (heartbeat and daily-report shape).

## 3. T1a suite

```bash
( ulimit -v 700000; python3 tests/test_tape_t1a.py ) 2>&1 | tee ~/tape_reh/t1a.log | tail -5
```
PASS line: `TAPE T1A PASS (12/12 guards, 9/9 unit checks)` (counts from `run_offline.sh`). The normal-day byte-identity
guards are the check that the `bucket_of` change (special days only) moved nothing on an ordinary day.

## 4. T0.1 mutants (M1-M8, each with its control)

M1-M6 are the original set. **M7** `on_frame` re-raises (guard `frame-errors`); **M8** `install.sh` reads exit 1 as
"outside" (guard `timer-sync`, which runs the install guard block against a SyntaxError'd `session.py`). Extras X1-X12;
**X12** puts the calendar close back at 15:30 (guard `fo-close`). Every guard that has a mutant also gets a control: the
unpatched copy must PASS.

```bash
( ulimit -v 700000; python3 tests/tape_t0_1_mutants.py ) 2>&1 | tee ~/tape_reh/t0_1_mutants.log | tail -30
```
PASS line: `TAPE T0.1 MUTANTS PASS (8/8 required caught x1, 12/12 extra caught, 10/10 controls x1)`

Read the per-row lines too: `CAUGHT M7-ON-FRAME-RAISES guard=frame-errors 1/1`, `CAUGHT M8-INSTALL-GUARD-1-IS-OUTSIDE guard=timer-sync 1/1`,
`CONTROL PASS guard=frame-errors 1/1`, `CONTROL PASS guard=timer-sync 1/1`. `MUTANT NOT APPLIED` is a FAIL (the anchor
string drifted), never a skip.

## 5. P7 (silent socket) and P8 (special session)

Offline, fake S3, as user `ubuntu`, everything under `~/tape_reh` (D1 in the plan: nothing under `/var/lib/tape` or
`/etc/tape`). P7 is ~8 min, P8 ~8 min.

```bash
# P7: the socket goes silent for 40 s, 120 s after connect, without closing
( ulimit -v 2000000; python3 tests/rehearsal/run_rehearsal.py --schedule 2x:6m --silence 120:40 --fake-s3 0.3 \
    --root ~/tape_reh/root --out ~/tape_reh/out7 --keep ~/tape_reh/keep ) 2>&1 | tee ~/tape_reh/p7.log | tail -3
python3 tests/rehearsal/verify_p7_p8.py --scenario silent --run "$(ls -d ~/tape_reh/out7/* | tail -1)"
```
PASS line: `REHEARSAL P7 VERDICT PASS` (exit 0). Preceded by `REHEARSAL DONE exit=0` in the driver log.

```bash
# P8: today is a special session (temp calendar: open = start+1 min, close = stop); SIGTERM-equivalent after 450 s
( ulimit -v 2000000; python3 tests/rehearsal/run_rehearsal.py --schedule 2x:9m --special --terminate-after 450 --fake-s3 0.3 \
    --root ~/tape_reh/root --out ~/tape_reh/out8 --keep ~/tape_reh/keep ) 2>&1 | tee ~/tape_reh/p8.log | tail -3
python3 tests/rehearsal/verify_p7_p8.py --scenario special --run "$(ls -d ~/tape_reh/out8/* | tail -1)"
```
PASS line: `REHEARSAL P8 VERDICT PASS` (exit 0).

P8's expectation did not need editing for the close change: it derives everything from the temp calendar it writes
(`stop = close + 10 min`, `closed_check = open + 5 min`), and the +10 / +5 offsets did not change. The real
15:40 -> 15:50 case is asserted by the `special-day` and `fo-close` guards in step 1, not by P8.

Optional, proves the verifier can fail on these runs (copies the run to /tmp):

```bash
python3 tests/rehearsal/selftest_p7_p8.py --p7 "$(ls -d ~/tape_reh/out7/* | tail -1)" --p8 "$(ls -d ~/tape_reh/out8/* | tail -1)"
```
PASS line: `P7/P8 VERIFIER SELFTEST PASS (n/n)`.

## 6. Fenced real-S3 rehearsal (P1-P6; user `tape`, the unit's fences, real `aws.env`, bucket `meridian-tape-raw`)

~51 min wall; it refuses to cross IST midnight and Mon-Fri 08:30-15:45. It stages the **committed** HEAD
(`stage.sh` refuses uncommitted changes under `services/` and `tests/rehearsal/`), so run it from the clone at the pushed
head. This touches `/var/lib/tape/rehearsal_*` and writes under `_rehearsal/<id>/` in the real bucket (not deletable with
the runner's write-only key; see `tests/rehearsal/README.md`). It does **not** install anything.

```bash
cd ~/meridian-tape-dev
sudo bash tests/rehearsal/stage.sh                      # last line: STAGED <12-char sha> -> /var/lib/tape/rehearsal_app (sha == HEAD)

sudo systemd-run --unit=tape-rehearsal --uid=tape --gid=tape \
  -p EnvironmentFile=/etc/tape/aws.env \
  -p Environment=TZ=Asia/Kolkata -p Environment=PYTHONDONTWRITEBYTECODE=1 -p Environment=PYTHONUNBUFFERED=1 \
  -p Environment=HOME=/var/lib/tape -p WorkingDirectory=/var/lib/tape \
  -p MemoryMax=400M -p CPUWeight=20 -p Nice=10 -p LimitAS=2000000000 \
  -p ReadWritePaths=/var/lib/tape -p ProtectSystem=strict -p NoNewPrivileges=true -p PrivateTmp=true -p ProtectHome=true \
  /var/lib/tape/venv/bin/python /var/lib/tape/rehearsal_app/tests/rehearsal/run_rehearsal.py --schedule 2x:35m,4x:15m
journalctl -fu tape-rehearsal | grep -vE 'TAPE (HB|SUBSCRIBE)'      # ends with: REHEARSAL DONE exit=0   (Ctrl-C to leave)

sudo -u tape /var/lib/tape/venv/bin/python /var/lib/tape/rehearsal_app/tests/rehearsal/verify_rehearsal.py --latest
```
PASS line: `REHEARSAL VERDICT PASS` (exit 0). `INCOMPLETE` (exit 3) is not a pass: a criterion could not be measured.
Clean up afterwards: `sudo rm -rf /var/lib/tape/rehearsal_{root,keep,out}`.

## After the list

- All six green: tell the operator the head sha; installing is a separate step (`sudo bash services/tape_runner/install.sh`,
  outside 08:30-15:45 on weekdays and outside 13:20-16:10 on 2026-11-08) and writes the 2026-11-08 timer.
- Anything red: report the failing cell text verbatim; do not install.
- Still the operator's: a valid Kite token in `/etc/tape/kite_token.env` before 13:55 IST on Sunday 2026-11-08 (T0 does not
  refresh it).

## Follow-ups recorded, not done

1. **Watchdog is not armed before 09:15** (decision). Pending `frames_hb` data from the first live days: if heartbeats
   arrive through the pre-open, arm from the connect or from open - 5 min to close the up-to-16 s blind spot at the open.
   The same applies to a special session's pre-open (14:05-14:20).
2. `tests/run_offline.sh` (34 steps) does not call `tests/test_tape_t0_1.py` or `tests/tape_t0_1_mutants.py`; add them when
   the step count is next revised (the counts in its header comment and in CLAUDE.md-level docs move with it).
3. Muhurat: whether packets dated today arrive before 14:05 is unmeasured; the forced options open at 14:20
   (`special_open_forced`) is the cover.
