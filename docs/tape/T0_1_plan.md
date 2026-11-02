# Tape T0.1 plan: silence watchdog, special sessions (Muhurat), counter reconciliation

Status: PLAN, awaiting operator go. Base: engine `origin/main` a1636b9 (T0 + T1a). Installed build: `a2694081d1fe`.
Written 2026-11-03 04:33 IST. Nothing in this plan has been built or run.

## 0. What I read, and what it showed

| Fact | Source | Consequence |
|---|---|---|
| kiteconnect 5.2.2 `_loop_ping` sets `_last_ping_time` and reschedules itself. **It never calls `sendPing()`** (no `sendPing` anywhere in `ticker.py`). | sdist fetched from pypi.org, sha256 `60bc1ea8...be1e` checked against PyPI metadata; read in scratchpad, not installed | `_last_pong_time` stays `None`, so `_loop_pong_check` (`if self._last_pong_time:`) can never fire. The library has **no** working dead-peer detection. A peer that drops without a close handshake is found only by the OS TCP timers. That is the ~59 s on day 1. The fix has to be ours. |
| `KiteTicker._on_message` calls `self.on_message(ws, payload, is_binary)` for **every** frame, before parsing. Ticks need `len(payload) > 4`; 1-byte heartbeats go only to `on_message`. | same file | `t.on_message` is the one hook that sees tick packets and heartbeats. The recorder sets `on_ticks`, `on_close` etc. but not `on_message`. |
| The library's reconnect is Twisted `ReconnectingClientFactory.retry`: wait `delay` (with jitter), then `delay = min(delay*factor, maxDelay)`. Defaults `initialDelay=1.0`, `factor=e`, `jitter=0.1196`. `onConnect` calls `resetDelay()`. `dropConnection(abort=True)` ends in `clientConnectionLost`, which calls `retry`. `on_reconnect` fires only when `retries > 0`, so the **first** retry of an outage is not reported. | twisted 26.10.0 `internet/protocol.py` (sdist, sha256 checked); kiteconnect `clientConnectionLost`. The venv's Twisted version is unknown to me (venv unreadable to this user). `retry()` has not changed shape in many years, but it is an assumption until checked. | Backoff 1, 2, 4, 8, 15, 15 means `initialDelay=1, factor=2, maxDelay=15, jitter=0` on the factory, set after `connect()` creates it. `maxDelay=15` shortens total retry time: `reconnect_max_tries=300` was ~5 h at 60 s, becomes ~75 min at 15 s, then `NORECONNECT` -> exit 1 -> systemd restart. See decision D2. |
| Recorder start-up and timeline are driven by `config.T_*` constants (`recorder.py:202-240`, `stats.py:66-67`, `:665`). The rehearsal driver overwrites those constants. | code | Special-session times must be a layer *on top of* `config.T_*`, read at use time, so the rehearsal's overwrite keeps working. |
| Instrument selection has no time dependence: `_price_for` is a live `kite.ltp`, falling back to the last index packet, then the resolve-time price; `atm_pos`, `window_tokens` and `_grow` take a price and nothing else. | `recorder.py:424-459`, `instruments.py:49-71` | A first read at 14:05 is fine mechanically. **A real risk is gating, not selection**: `_open_options` waits for `_witness_today()` (a packet dated today), which on a normal day exists from 09:00 pre-open. If Muhurat pre-open sends nothing dated today before 14:05, options subscribe only at the closed-check fallback (open+5), missing 5 minutes. See section 2. |
| Daily report vs event log (day 1: 9/2 vs 8/6/3). `reconnects` = `on_connect` calls after the first = connects - 1 = 2 (matches 3 connects exactly). The processor's 6 "reconnects" are ctl `reconnect` lines = `on_reconnect` callbacks = the report's separate `reconnect_attempts`, and they exclude each outage's first retry. Same word, two quantities. `disconnects` is incremented in `on_close` unconditionally, but the ctl line is suppressed once `stopping` (`_ctl_all`). | `recorder.py:135-138, 544-596`; `stats.py` | `connects`/`reconnects` is a **definition collision, proven by the arithmetic**. The 9 vs 8 is a **hypothesis**: one `on_close` after `stopping` is counted but not logged. I have not seen the day-1 control lines. I will confirm against them if you can give me the day-1 `session/` + one symbol's 15:35-15:40 segment, otherwise the build proves the mechanism by fixture and says so. |
| The processor hardcodes the day: `bucket_of` (09:15 / 10:00 / 15:30), `EARLY`/`LATE`, `verdict()` needs both windows >= 200 deltas. It has no session notion. On a Muhurat day it would not crash, but it would put 14:00-14:20 pre-open packets in a session hour bucket and report FAIL or NOT EVALUATED for the wrong reason. | `minute.py`, `replay.py`, `process_day.py` | Needs window-aware bucketing and a special-session verdict. |

## 1. A. Silence watchdog

**New config** (`config.py`): `SILENCE_S = 15`, `SILENCE_MIN_S = 5`, `WD_BACKOFF_S = (1, 2, 4, 8, 15)`. Effective threshold is `max(SILENCE_MIN_S, SILENCE_S)`, so a mis-set value cannot go below 5 s. Units: seconds in config, converted once with `* clk.NS`.

**Frame stamping.** `t.on_message = self.on_frame` stamps `self.last_frame_ns = clock.now_ns()` and bumps `frames_hb` (1-byte) or `frames_other`. No lock (an attribute store; `on_ticks` already holds the lock for the real work). `on_ticks` stamps too, so a ticker that only calls `on_ticks` (every existing test fake) behaves as before.

**Trip rule**, evaluated in `step()` every second, main thread, under the recorder lock:
- armed only when `connected` and `session_open <= now <= session_close` for today's window (section 2; default 09:15-15:30);
- reference `ref = max(last_frame_ns, connected_since, session_open_ns)`. The `session_open` term is what stops a quiet pre-open from tripping at 09:15:00; `connected_since` stops a fresh reconnect or a 11:00 restart tripping on a stale stamp;
- trip when `now - ref >= threshold`. Worst case detection delay is `SILENCE_S` + one 1 s poll = 16 s, inside the amended G2 limit of 20 s.

**On trip:** log `WATCHDOG_TRIP age=<s> n=<k>`; `stats.watchdog_trips += 1`; append `{ts_ist, age_s, ok}` to a bounded list (200); write a ctl `watchdog` record to every symbol (the processor ignores unknown ctl kinds, I will add a test that proves it); then `ticker.force_reconnect()`.

**`force_reconnect`** is a method on the production ticker, not on the recorder, so the recorder never imports Twisted. New `services/tape_runner/ticker_glue.py` (lazy import, production only, called from `__main__._kite`) defines `WatchedTicker(KiteTicker)`:
- `connect()`: calls super, then sets `factory.initialDelay=1.0, factor=2.0, maxDelay=15, jitter=0`;
- `force_reconnect()`: `reactor.callFromThread(self.factory.ws.dropConnection, abort=True)`. It must be thread-safe because `step()` is not the reactor thread. This goes through the library's own `clientConnectionLost -> retry` path, so no second reconnect mechanism exists.

**If the drop raises or no `on_close` follows:** `connected` stays true and silence persists, so the watchdog re-trips under its own backoff `WD_BACKOFF_S` (1, 2, 4, 8, 15, 15, ...), each attempt logged, failures counted in `watchdog_errors`. It never exits and never touches exit codes 75/78. Reset to step 0 on any frame. No ticker rebuild escalation is planned (see D3).

**Disabled** pre-open, post-close, and while `connected` is false (the library is already retrying then; the existing token probe covers a dead token).

**Reported:** heartbeat JSON gains `watchdog_trips`, `watchdog_errors`, `last_frame_age_s`, `frames_hb`, `frames_other`. Daily report gains `watchdog_trips`, `watchdog_errors`, `watchdog` (the trip list). `watchdog_trips` is persisted in `DayStats` so restarts accumulate. The `frames_hb` counter exists because I have **no measurement of Kite's heartbeat cadence**: the tape records neither heartbeats nor `on_message` events, and I will not assume one. In a window with live index/future packets the feed is never quiet for 15 s; the counters will tell us from Tuesday's data whether the 15 s default is safe in thin moments.

## 2. B. Special sessions

**`services/tape_runner/special_sessions.json`** (checked in, IST):
```json
[{"date": "2026-11-08", "open": "14:20", "close": "15:30", "label": "Muhurat"}]
```
**`services/tape_runner/session.py`** (stdlib, pure): `load(path)` validates (ISO date, HH:MM, open < close, unique dates, loud failure on malformed) and `window(day)` returns a dict of the times the recorder uses. Default days return `config.T_*` read at call time (rehearsal overwrite still works). A special day derives them from `open`/`close` with the **same offsets the defaults have today**:

| Constant | Default | Special | Offset |
|---|---|---|---|
| `T_START` | 08:50 | 13:55 | open - 25 min |
| `T_RESOLVE` | 08:55 | 14:00 | open - 20 |
| `T_OPTIONS` | 09:00 | 14:05 | open - 15 |
| `T_CLOSED_CHECK` | 09:20 | **14:25** | open + 5 (as ruled) |
| `T_SESSION_START/END` | 09:15 / 15:30 | 14:20 / 15:30 | open / close |
| `T_STOP` | 15:40 | 15:40 | close + 10 |
| `T_RESOLVE_GIVEUP` | 09:10 | 14:15 | resolve + 15 |

`Recorder` and `DayStats` take their times from `session.window(self.day)` (`DayStats.from_dict` rebuilds from the day, so a restart re-derives it). A missing or unreadable calendar file falls back to the defaults with a loud log line, never a crash: the weekday case must not depend on this file.

**Added for special days only:** if `options_on` is still false at `open` and the feed is connected, open options anyway (`reason="special_open_forced"`), so a pre-open with nothing dated today cannot cost the first minutes. I need your call on this (D4). The pre-open start time for Muhurat is in the NSE circular, which I do not have.

**One-off timer, generated by `install.sh`** from the calendar through a stdlib helper (`session.py --emit-timers`), run as root from the installed copy. For 2026-11-08 the exact text is:
```
# /etc/systemd/system/tape-runner-special-2026-11-08.timer  (generated from special_sessions.json; Muhurat)
[Unit]
Description=MERIDIAN tape raw recorder (T0) -- special session 2026-11-08 (Muhurat), start 13:55 IST

[Timer]
OnCalendar=2026-11-08 13:55:00 Asia/Kolkata
Persistent=false
AccuracySec=1s
Unit=tape-runner.service

[Install]
WantedBy=timers.target
```
`install.sh` additions: (1) write one such file per entry whose date is >= today IST, `daemon-reload`, `systemd-analyze verify`, `enable --now`; (2) for any existing `tape-runner-special-*.timer` whose date is in the past **or no longer in the calendar**, `disable --now` and delete it; (3) the market-hours guard is extended: it also refuses within `[open - 60 min, close + 30 min]` on a special date, because the current guard only covers Mon-Fri and Muhurat is a Sunday. The weekday timer is untouched (its `OnBootSec=60` still covers a mid-session reboot on a special day, and the recorder then reads the special window).

**Offline processor.** `process_day.py` takes the window from `session.window(--day)`. For a special day: `bucket_of` is window-aware (before open -> `pre_0915`, at/after close -> `post_1530`, otherwise the clock-hour bucket), the G3 early/late split is skipped, the report carries one overall share over all in-window option volume, verdict string `NOT EVALUATED (special session)`, a `session` block in the JSON, exit 0 (INVALID/exit 4 on a broken invariant is unchanged). **Normal days must stay byte-identical**: the new keys appear only on special days, and the T1a golden/byte-identity tests are the check. Bucket key names are reused literally (`pre_0915` means "before open" on a special day), and the report says so in a note.

## 3. C. Small fixes

Counter definitions, one line each, in the code and in `DayStats`:
- `connects`: `on_connect` calls (new field; equals ctl `connect` lines);
- `reconnects`: `connects - 1`, successful re-connects (unchanged value, now documented);
- `reconnect_attempts`: `on_reconnect` callbacks = ctl `reconnect` lines; excludes each outage's first retry (a library property);
- `disconnects`: `on_close` calls **that were logged as ctl `disconnect`**, i.e. not after `stopping`. The shutdown close is counted separately as `close_at_stop` so nothing is hidden.

The processor's `read_daily` passes `connects`, `reconnect_attempts`, `watchdog_trips` through, and the processor adds a reconciliation line: counts of ctl `connect` / `disconnect` / `reconnect` / `watchdog` events (distinct per symbol file) next to the report's, with a `MISMATCH` flag. Docs: amended G2 wording added to `T0_install.md` and `T0_plan.md` ("no unexplained gap; an external gap over 60 s is allowed if logged, with detection delay <= 20 s"). Neither doc mentions G2 today (grep), so this is an addition under the gate list, not an edit.

## 4. Tests (tester first, Loop D)

New `tests/test_tape_t0_1.py` in the same style as `test_tape_t0.py` (`--root`, `--only`, ManualClock, FakeTicker extended with `on_message` and a scripted `force_reconnect`). Each check states what makes it fail (CLAUDE.md Rule 0); expected values are written from the scripted inputs, never taken from a run.

| # | Fixture | Fails if |
|---|---|---|
| 1 | Frames every 1 s for 60 s, then silence. Age 14.9 s: no trip. 15.0 s: trip. Exactly one `force_reconnect`; on_close/on_connect then recording resumes. | threshold unit wrong (either direction), watchdog off, trip not counted |
| 2 | Silence 08:55-09:15 with connected feed: no trip at 09:15:00 or 09:15:14. Silence 15:31-15:39: no trip. Reconnect at 11:00 with a stale stamp: no trip. | window ignored, no `session_open`/`connected_since` floor |
| 3 | `force_reconnect` raises x3 then works. Attempts at +0, +1, +3, +7 s (gaps 1, 2, 4), recording resumes, `watchdog_errors == 3`, process still alive, no exit code returned. | backoff wrong, a raise propagates, exit code changed |
| 4 | Date 2026-11-08 with the calendar: window, `T_CLOSED_CHECK` = 14:25 (CLOSED not declared at 14:02 even with a stale witness), stop 15:40, options opened at 14:05 and forced at 14:20 if no witness, first price read at 14:05 far from the resolve-time price still gives the right ATM window. Timer text equals the literal above, byte for byte. | calendar ignored, default 09:20 used, timer text drifts |
| 5 | A normal date (2026-11-02, 11-03) with the calendar present: every time equals `config.T_*`, no special timer emitted. | special logic leaking into normal days |
| 6 | Counter reconciliation: scripted events (3 connects, 8 disconnects, 6 reconnect callbacks, one `on_close` after `stopping`). The daily report fields equal counts of ctl lines read back from the written segments with the processor's own reader. | any counter defined differently from its event |
| 7 | Library glue: stub factory gets `initialDelay=1, factor=2, maxDelay=15, jitter=0` after `connect()`. `force_reconnect` goes through `callFromThread` (stub reactor). This checks the attributes **set**, not the delay sequence; see the gap in section 7. | glue not applied |
| 8 | Processor on a synthetic special-session day: no crash, exit 0, verdict `NOT EVALUATED (special session)`, one overall share, pre-open packets outside the session total. A normal-day run stays byte-identical to the T1a golden. | crash, wrong bucket, normal-day drift |
| 9 | `install.sh` timer step (dry-run mode that writes into a temp dir, no systemd): past and removed dates are deleted, future one written, guard refuses inside the Muhurat window. | stale timers kept, guard hole |

**Mutants** (`tests/tape_t0_1_mutants.py`, copy of the `tape_mutants.py` harness: one exact-string patch, must match once, guard must FAIL, unpatched control must PASS, repeated):
M1 watchdog disabled; M2 threshold unit error (seconds read as milliseconds; I add the x1000 direction as a seventh, reported separately); M3 watchdog active outside the window; M4 calendar ignored; M5 `watchdog_trips` not incremented; M6 daily-report counters reverted to the old definitions. Gate: 6/6 caught, 6/6 controls pass.

**Existing-test risk, stated now.** Existing T0 tests jump the clock with a "connected" fake that sends no frames; the new watchdog would trip in them. Planned handling: the existing fakes keep no `force_reconnect`, so a trip with no drop method logs `WATCHDOG_NO_DROP` and counts, but I expect some exact-count assertions in `test_tape_t0.py` to move. If any do, I will fix the **fixture** (feed a frame where the test means "healthy") and say which ones changed, not loosen an assertion. Order of work: write the new tests first, run the **unchanged** T0/T1a suites on the new code, list every failure, then decide per failure.

**Rehearsal** (`tests/rehearsal/`): P1-P6 code unchanged. New `P7` (synthetic ticker goes silent for 40 s at 2x without closing; expects a trip within 16 s of silence start, a disconnect/connect pair, packets resume, `rehearsal_seq` contiguous, `watchdog_trips == 1`) and `P8` (calendar override via `config.SPECIAL_SESSIONS_PATH` pointing at a temp file with today as a special date; expects the special window in the log, closed-check at open+5, daily report `session.kind == "special"`). P8 does not run to its 10-minute post-close stop: it ends with SIGTERM after the open+5 check, and the stop time is covered by fixture 4. P1-P6 must also show `watchdog_trips == 0` on the continuous feed (reported, not a new gate on P1-P6).

## 5. Where I need your decision

- **D1 (constraint conflict).** The existing rehearsal stages into `/var/lib/tape/rehearsal_app`, runs as user `tape` with `/etc/tape/aws.env` and real S3. You told me not to touch `/var/lib/tape` or `/etc/tape`. To run P1-P8 tonight I will run them as `ubuntu` with `--fake-s3 0.3` and `--root/--out/--keep` under the scratchpad, under `ulimit -v`. This is the weaker run: no systemd fences (MemoryMax/LimitAS/CPUWeight) and no real S3 latency. **Recommended**; the real-S3, fenced re-run goes in the Tuesday-after-15:45 commands. Say "no" if you want P1-P8 deferred entirely.
- **D2.** `maxDelay=15` cuts `reconnect_max_tries=300` from ~5 h to ~75 min of unbroken failure before `NORECONNECT` and a systemd restart. Default plan: leave 300 and accept it. Alternative: `maxRetries=None` (never give up; the 60 s token probe still ends a dead-token outage).
- **D3.** No ticker-rebuild escalation if the drop keeps failing (retry the same drop under backoff, as you specified). A rebuild means a second `KiteTicker` and stale callbacks; I judge it out of scope.
- **D4.** Force options open at `open` on special days when no witness exists (section 2). Needs your OK, and ideally the Muhurat pre-open time from the circular.
- **Branch.** `git checkout -b tape/t0-1 origin/main` was denied by the permission layer on this box, so I am still on local `main` (a269408, behind origin). This plan file is untracked. I will not work around it: either allow that command, or create the branch yourself (`git switch -c tape/t0-1 origin/main`; your `.claude/settings.json` change carries over and stays uncommitted).

## 6. Schedule and resources

Now 04:33 IST; target 07:30; no tests after 08:30. Rough budget: tests+code 1h45, mutants 30 min, rehearsal P1-P6 51 min + P7 ~12 min + P8 ~8 min (can overlap with mutants only if memory allows). Memory: 177 MB free, 689 MB available; rehearsal at 4x and the mutant harness will not run at the same time. If time runs short I will drop the order of P-runs, not skip the mutants, and report what did not run.

## 7. What I cannot verify

- The Twisted/autobahn versions actually in the venv, and so the delay sequence of the real `ReconnectingClientFactory` under the tuned attributes. Tests check the attributes set; the sequence is read from source. If I can extract pure-Python wheels into the scratchpad and run the real factory on `twisted.internet.task.Clock`, I will; otherwise the first evidence is the first live outage's journal.
- Kite heartbeat cadence (counters added to measure it).
- The 9 vs 8 disconnect cause, without day-1 control lines.
- The Muhurat pre-open start time and whether packets dated today arrive before 14:05.
- Behaviour of `callFromThread(dropConnection(abort=True))` on a real half-dead TCP socket: tests use stubs.

## 8. Files

New: `services/tape_runner/{session.py,special_sessions.json,ticker_glue.py}`, `tests/test_tape_t0_1.py`, `tests/tape_t0_1_mutants.py`, `docs/tape/T0_1_plan.md`.
Changed: `config.py`, `recorder.py`, `stats.py`, `__main__.py`, `install.sh`, `services/tape_offline/process_day.py`, `merdian_compute/tape/{minute.py,replay.py}`, `tests/rehearsal/{feed.py,run_rehearsal.py,verify_rehearsal.py}`, `docs/tape/{T0_install.md,T0_plan.md}`.
Not changed: unit file, weekday timer, `uploader.py`, `segments.py`, `serialize.py`, exit codes.
