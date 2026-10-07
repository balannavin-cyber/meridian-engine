#!/usr/bin/env python3
"""AM-2 / S91 — monitor_orchestrator_health.py must not send outside the orchestrator's
own schedule, must not re-send inside it, and must not come apart under flapping.

THE DEFECT THIS TEST EXISTS TO CATCH, in two layers
---------------------------------------------------
LAYER 1, the flood. The orchestrator runs `*/5 03-09 * * 1-5` UTC; the monitor runs
`*/1 * * * *`, 24x7. For ~17 hours a day and all weekend "no orchestrator runs in the
last 5 minutes" is the correct state of the system, and the pre-S91 body sent a Telegram
warning on every such minute -- 366 such lines in the live logs/monitor.log on 2026-10-07,
~1,000 sends a night, operator chat 4.1k unread and MUTED, and the 09:10 IST wsfeed alert
(TD-S91-NEW-3) missed inside that muted chat.

LAYER 2, the flapping -- and this is the one review missed. The first version of this file
passed 40/40 over a design that would still have sent 148 times on 2026-10-07, because its
scenarios were built from the spec (flat failure, clean recovery) and the real sequence is
neither: 119 adjacent-minute condition changes inside the band, so nothing ever stayed
active for 30 minutes and the re-notify window engaged ZERO times. Every change cost an
alert plus a RECOVERED. That is why scenario 10 replays real data against an independent
model, and why its control is kept in the file rather than quoted in a report.

WHAT WOULD MAKE THIS TEST FAIL (Rule 0, stated before the assertions)
  * a gate that lets an off-session condition through -> scenario 1 asserts 0 sends over
    60 off-session ticks AND replays the same 60 through PreS91Replica (the pre-fix logic,
    verbatim) asserting 60. Without that control the cell would also pass against a stub
    that never sends anything.
  * dedupe or hold-down state that does not survive the process -> cron starts a NEW
    interpreter every minute, so EVERY tick in EVERY scenario builds a new HealthMonitor
    reading state off disk. In-memory state passes a single-object test and floods live.
  * a window parser that ignores its input -> scenario 7 parses the real crontab line AND
    a different one and asserts DIFFERENT windows; a constant-returning parser passes the
    first and fails the second.
  * a gate so tight it silences a real failure -> scenarios 2/3/6 assert sends DO happen
    in-session and that the grace boundary OPENS.
  * a hold-down that absorbs a real recovery -> scenario 4 asserts RECOVERED does arrive,
    on the HOLDDOWN_TICKS-th clear tick and not before.
  * a hold-down fed by non-observations -> scenario 11: an active alert plus 12 probe
    failures asserts 0 RECOVERED. A probe failure is UNKNOWN, not health.
  * the fixture replay asserting a number nobody predicted -> scenario 10's expectation is
    computed by `independent_episode_model`, which walks the fixture with its own logic
    and never calls the module. A figure read off a previous run and pasted back in would
    assert nothing (§D.40.1).

OFFLINE AND SAFE
No database, no network, no clock. Telegram credentials are blanked BEFORE the import so
even a mis-wired call cannot reach the operator's chat (telegram_utils captures the token
at import and returns False on an empty one), and every scenario also injects a counting
send stub -- two independent reasons no message can leave this process. Nothing here
prints an environment value (Rule 19).
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ['TELEGRAM_BOT_TOKEN'] = ''
os.environ['TELEGRAM_CHAT_ID'] = ''
os.environ.setdefault('SUPABASE_URL', 'https://offline.invalid')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'offline-dummy-not-a-credential')

import monitor_orchestrator_health as H  # noqa: E402

UTC = timezone.utc
KEY = H.CONDITION_KEY
fails = 0


def check(name, got, want):
    global fails
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {name}  got {got!r} want {want!r}")
    fails += 0 if ok else 1
    return ok


REAL_CRON_LINE = ('*/5 03-09 * * 1-5 cd /home/ssm-user/meridian-engine && source .env && '
                  'python3 run_merdian_shadow_runner_aws.py >> logs/orchestrator.log 2>&1')
REAL_CRONTAB = ('SHELL=/bin/bash\n'
                '5 3 * * 1-5 cd /home/ssm-user/meridian-engine && python3 refresh_dhan_token.py\n'
                + REAL_CRON_LINE + '\n'
                '*/1 * * * * cd /home/ssm-user/meridian-engine && python3 monitor_orchestrator_health.py\n')

WINDOW = H.parse_orchestrator_window(REAL_CRONTAB)

SENDS_IN_29_MIN = len([m for m in range(29) if m % H.DEDUPE_MIN == 0])
SENDS_IN_60_MIN = len([m for m in range(60) if m % H.DEDUPE_MIN == 0])

NOFIRE: list = []
OK_RUN = [{'exit_code': 0, 'duration_ms': 1200, 'created_at': '2026-10-07T05:00:01'}]
BAD_RUN = [{'exit_code': 1, 'duration_ms': 900, 'created_at': '2026-10-07T05:00:01'}]
ROWS = {'NOT_FIRING': NOFIRE, 'OK': OK_RUN, 'FAILED': BAD_RUN}


class PreS91Replica:
    """The pre-fix notification logic, from monitor_orchestrator_health.py_PRE_S91:52-55:

        rows = resp.json()
        if not rows:
            self.log('WARNING', 'No orchestrator runs in last 5 minutes')
            send_warning('Orchestrator not firing', {'gap_minutes': 5})
            return

    No gate, no state, one send per tick. The control: a scenario counting 0 sends against
    the new code is only a test if the same inputs produce sends against what it replaced.
    """

    def __init__(self, send):
        self._send = send

    def tick(self, rows):
        if not rows:
            self._send('WARNING', 'Orchestrator not firing', {'gap_minutes': 5})


def replay(start_utc, seq, *, trading_day=True, window=WINDOW, state_dir=None,
           probe_fails_at=frozenset()):
    """Run one tick per entry in `seq` (a list of condition tokens, one per minute), each
    in a FRESH HealthMonitor, as cron does. Returns the (level, message) list sent."""
    sent: list[tuple[str, str]] = []

    def send_stub(level, message, context):
        sent.append((level, message))
        return True

    tmp = state_dir or tempfile.mkdtemp(prefix='s91_monitor_state_')
    state_path = Path(tmp) / 'monitor_alert_state.json'
    for i, token in enumerate(seq):
        def fetch(_i=i, _t=token):
            if _i in probe_fails_at:
                raise H.QueryFailed('simulated')
            return ROWS[_t]
        H.HealthMonitor(
            now_utc=start_utc + timedelta(minutes=i),
            send=send_stub,
            is_trading_day=lambda: trading_day,
            window=window,
            state_path=state_path,
            fetch_rows=fetch,
        ).run()
    return sent


def quiet(n):
    return ['NOT_FIRING'] * n


# =================================================================================
print('--- scenario 1: OFF-SESSION, 60 ticks, condition active throughout ---')
OFF = datetime(2026, 10, 7, 12, 40, tzinfo=UTC)          # Wednesday 18:10 IST
off_sent = replay(OFF, quiet(60))
check('off-session sends (new code)', len(off_sent), 0)

replica_sent: list = []
replica = PreS91Replica(lambda lvl, msg, ctx: replica_sent.append((lvl, msg)))
for _ in range(60):
    replica.tick(NOFIRE)
check('off-session sends (PRE_S91 replica -- the control)', len(replica_sent), 60)
check('the gate is what differs, not the inputs',
      (len(off_sent), len(replica_sent)), (0, 60))

print('\n--- scenario 1b: OFF-SESSION on a WEEKEND ---')
SAT = datetime(2026, 10, 10, 5, 0, tzinfo=UTC)
check('the chosen date is a Saturday', SAT.isoweekday(), 6)
check('weekend in-hours sends', len(replay(SAT, quiet(60))), 0)

print('\n--- scenario 2: IN-SESSION failure, 29 minutes ---')
IN = datetime(2026, 10, 7, 5, 0, tzinfo=UTC)             # 10:30 IST, mid-session
check('the chosen start is inside the window', H.in_alert_window(IN, WINDOW)[0], True)
s29 = replay(IN, quiet(29))
check(f'sends across 29 min at DEDUPE_MIN={H.DEDUPE_MIN}', len(s29), SENDS_IN_29_MIN)
check('and that expectation is 1', SENDS_IN_29_MIN, 1)
check('the send is the WARNING', s29[0][0] if s29 else None, 'WARNING')

print('\n--- scenario 3: IN-SESSION failure, 60 minutes ---')
s60 = replay(IN, quiet(60))
check(f'sends across 60 min at DEDUPE_MIN={H.DEDUPE_MIN}', len(s60), SENDS_IN_60_MIN)
check('and that expectation is 2', SENDS_IN_60_MIN, 2)
check('the second send is marked as a re-notify',
      'still failing' in s60[1][1] if len(s60) > 1 else False, True)

print(f'\n--- scenario 4: RECOVERY needs HOLDDOWN_TICKS={H.HOLDDOWN_TICKS} clear ticks ---')
rec = replay(IN, quiet(5) + ['OK'] * H.HOLDDOWN_TICKS)
check('total sends across fail -> sustained clear', len(rec), 2)
check('first is the WARNING', rec[0][0] if rec else None, 'WARNING')
check('second is the RECOVERED',
      rec[1][1].startswith('RECOVERED:') if len(rec) > 1 else False, True)
check('RECOVERED names the single merged key',
      KEY in rec[1][1] if len(rec) > 1 else False, True)

print('\n--- scenario 4a: one tick SHORT of the hold-down -> no RECOVERED ---')
check('sends with HOLDDOWN_TICKS-1 clear ticks',
      len(replay(IN, quiet(5) + ['OK'] * (H.HOLDDOWN_TICKS - 1))), 1)

print('\n--- scenario 4b: a FLAP is absorbed (this is what (2) buys over (1)) ---')
# fail, clear just short of the hold-down, fail again, then clear properly.
flap = quiet(5) + ['OK'] * (H.HOLDDOWN_TICKS - 1) + ['FAILED'] + ['OK'] * H.HOLDDOWN_TICKS
fl = replay(IN, flap)
check('one episode, not two: total sends', len(fl), 2)
check('  ... and no second WARNING/CRITICAL',
      len([x for x in fl if x[0] in ('WARNING', 'CRITICAL')]), 1)

print('\n--- scenario 4c: NOT_FIRING <-> FAILED alternation is ONE key (this is (1)) ---')
alt = ['NOT_FIRING', 'FAILED'] * 10
al = replay(IN, alt)
check('20 alternating unhealthy minutes -> 1 send', len(al), 1)
check('  ... and it is not a RECOVERED',
      any(x[1].startswith('RECOVERED') for x in al), False)

print('\n--- scenario 4d: a healthy run with no prior alert sends nothing ---')
check('healthy ticks send nothing', len(replay(IN, ['OK'] * 20)), 0)

print('\n--- scenario 5: HOLIDAY inside the window ---')
check('holiday in-window sends', len(replay(IN, quiet(60), trading_day=False)), 0)

print('\n--- scenario 6: the start GRACE boundary ---')
check('03:05 UTC (inside grace) -> no send',
      len(replay(datetime(2026, 10, 7, 3, 5, tzinfo=UTC), quiet(1))), 0)
check('03:09 UTC (last grace minute) -> no send',
      len(replay(datetime(2026, 10, 7, 3, 9, tzinfo=UTC), quiet(1))), 0)
check('03:10 UTC (grace over) -> 1 send',
      len(replay(datetime(2026, 10, 7, 3, 10, tzinfo=UTC), quiet(1))), 1)
check('09:59 UTC (last alertable minute) -> 1 send',
      len(replay(datetime(2026, 10, 7, 9, 59, tzinfo=UTC), quiet(1))), 1)
check('10:00 UTC (window closed) -> no send',
      len(replay(datetime(2026, 10, 7, 10, 0, tzinfo=UTC), quiet(1))), 0)

print('\n--- scenario 7: the window is READ, not hardcoded ---')
check('real line -> first start 03:00 UTC', H._hhmm(WINDOW.first_start_min), '03:00')
check('real line -> last start 09:55 UTC', H._hhmm(WINDOW.last_start_min), '09:55')
check('real line -> step 5m', WINDOW.step_min, 5)
check('real line -> Mon-Fri', sorted(WINDOW.dows), [1, 2, 3, 4, 5])
check('real line -> alert band 03:10-10:00',
      (H._hhmm(WINDOW.alert_from_min), H._hhmm(WINDOW.alert_to_min)), ('03:10', '10:00'))

ALT_W = H.parse_orchestrator_window(
    '*/3 04-08 * * 1-6 cd /x && python3 run_merdian_shadow_runner_aws.py\n')
check('alt line -> first start 04:00', H._hhmm(ALT_W.first_start_min), '04:00')
check('alt line -> last start 08:57', H._hhmm(ALT_W.last_start_min), '08:57')
check('alt line -> step 3m', ALT_W.step_min, 3)
check('alt line -> Mon-Sat', sorted(ALT_W.dows), [1, 2, 3, 4, 5, 6])
check('alt window differs from the real one', ALT_W == WINDOW, False)

SUN = H.parse_orchestrator_window(
    '*/5 03-09 * * 0 cd /x && python3 run_merdian_shadow_runner_aws.py\n')
check('cron dow 0 normalises to isoweekday 7', sorted(SUN.dows), [7])

print('\n--- scenario 8: the parse-failure path falls back LOUDLY, not to silence ---')
fb = H.resolve_window('# nothing here mentions the orchestrator\n')
check('no matching line -> fallback window', fb.source, 'fallback:default')
check('commented-out orchestrator line is not read',
      H.resolve_window('# */5 03-09 * * 1-5 python3 run_merdian_shadow_runner_aws.py\n').source,
      'fallback:default')
check('a dom-restricted line is refused rather than silently flattened',
      H.resolve_window('*/5 03-09 1 * 1-5 python3 run_merdian_shadow_runner_aws.py\n').source,
      'fallback:default')
check('fallback window still sends in-session', len(replay(IN, quiet(1), window=fb)), 1)

print('\n--- scenario 9: state is on DISK, and [STATE_RESET] closes a stale alert ---')
tmpdir = tempfile.mkdtemp(prefix='s91_monitor_state_')
sp = Path(tmpdir) / 'monitor_alert_state.json'
replay(IN, quiet(1), state_dir=tmpdir)
check('state file written under the given dir', sp.exists(), True)
check('the merged key is in it', KEY in H.AlertState(sp).load().keys(), True)
post = replay(datetime(2026, 10, 7, 12, 40, tzinfo=UTC), quiet(1), state_dir=tmpdir)
check('off-session tick sends nothing (no out-of-band RECOVERED)', len(post), 0)
check('and the stale alert was dropped', H.AlertState(sp).load().keys(), [])

# =================================================================================
print('\n--- scenario 10: FLAPPING, replayed from the real 2026-10-07 sequence ---')
FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'monitor_conditions_2026-10-07.tsv'
seq: dict[int, str] = {}
for line in FIXTURE.read_text().splitlines():
    if line.startswith('#') or not line.strip():
        continue
    mn, token = line.split('\t')
    seq[int(mn)] = token
minutes = sorted(seq)
check('fixture loaded', len(minutes) > 900, True)


def independent_episode_model(order, cond, *, holddown, dedupe, lo, hi):
    """Predict the send count WITHOUT calling the module.

    Walks the observed minutes and counts, with its own logic:
      * an episode OPENS on the first unhealthy minute inside the band -> 1 send;
      * while open, a re-notify every `dedupe` minutes since the last send;
      * `holddown` consecutive in-band CLEAR minutes close it -> 1 RECOVERED send;
      * leaving the band drops the episode silently (the [STATE_RESET] path).
    If this disagrees with the module, one of the two is wrong and the cell fails --
    which is the point. The expectation is derived from the constants, never pasted.
    """
    sends = 0
    active = False
    clear = 0
    last_sent = None
    for m in order:
        in_band = lo <= m < hi
        if not in_band:
            active, clear, last_sent = False, 0, None
            continue
        unhealthy = cond[m] in ('NOT_FIRING', 'FAILED')
        if unhealthy:
            clear = 0
            if not active:
                active, last_sent, sends = True, m, sends + 1
            elif m - last_sent >= dedupe:
                last_sent, sends = m, sends + 1
        elif active:
            clear += 1
            if clear >= holddown:
                sends += 1          # RECOVERED
                active, clear, last_sent = False, 0, None
    return sends


predicted = independent_episode_model(
    minutes, seq, holddown=H.HOLDDOWN_TICKS, dedupe=H.DEDUPE_MIN,
    lo=WINDOW.alert_from_min, hi=WINDOW.alert_to_min)

DAY0 = datetime(2026, 10, 7, tzinfo=UTC)


def replay_fixture(holddown):
    """Replay the fixture at a given hold-down. holddown=1 reproduces (1)-alone:
    one merged key, RECOVERED on the first clear tick, no hold-down."""
    saved = H.HOLDDOWN_TICKS
    H.HOLDDOWN_TICKS = holddown
    try:
        sent: list[tuple[int, str, str]] = []
        tmp = Path(tempfile.mkdtemp(prefix='s91_fixture_')) / 'state.json'
        for m in minutes:
            cur = m

            def send_stub(level, message, context, _m=cur):
                sent.append((_m, level, message))
                return True

            def fetch(_t=seq[m]):
                return ROWS[_t]

            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                H.HealthMonitor(
                    now_utc=DAY0 + timedelta(minutes=m),
                    send=send_stub,
                    is_trading_day=lambda: True,
                    window=WINDOW,
                    state_path=tmp,
                    fetch_rows=fetch,
                ).run()
        return sent
    finally:
        H.HOLDDOWN_TICKS = saved


final = replay_fixture(H.HOLDDOWN_TICKS)
one_only = replay_fixture(1)                      # the (1)-alone control
pre_s91 = sum(1 for m in minutes if seq[m] in ('NOT_FIRING', 'FAILED'))

print(f'      PRE_S91 (ungated, two keys, no dedupe)      : {pre_s91} sends')
print(f'      (1) alone: one key, RECOVERED on first clear: {len(one_only)} sends')
print(f'      (1)+(2) as shipped, hold-down {H.HOLDDOWN_TICKS} ticks      : {len(final)} sends')
for mn, lvl, msg in final:
    print(f'        {H._hhmm(mn)} UTC  {lvl}: {msg}')

check('(1)+(2) send count matches the independent model', len(final), predicted)
check('(1)+(2) is strictly better than (1) alone', len(final) < len(one_only), True)
check('(1) alone is strictly better than PRE_S91', len(one_only) < pre_s91, True)
check('every send lands inside the alertable band',
      all(WINDOW.alert_from_min <= m < WINDOW.alert_to_min for m, _l, _m2 in final), True)

print('\n--- scenario 11: an UNKNOWN tick is not a clear tick ---')
# Active alert, then 12 consecutive probe failures (> HOLDDOWN_TICKS). A probe failure is
# evidence of nothing; counting it would manufacture a RECOVERED nobody observed.
unk = replay(IN, quiet(3) + ['OK'] * 12, probe_fails_at=frozenset(range(3, 15)))
check('sends across 3 fail + 12 probe-failure ticks', len(unk), 1)
check('RECOVERED count across 12 probe failures',
      len([x for x in unk if x[1].startswith('RECOVERED')]), 0)
# control: the SAME 12 ticks as real OK readings DO recover, so the cell above is
# measuring the UNKNOWN handling and not merely a hold-down that never fires.
ctl = replay(IN, quiet(3) + ['OK'] * 12)
check('control: the same 12 ticks as real OK readings -> 1 RECOVERED',
      len([x for x in ctl if x[1].startswith('RECOVERED')]), 1)

print(f"\nMONITOR GATE {'ALL PASS' if fails == 0 else f'{fails} FAIL'}")
sys.exit(1 if fails else 0)
