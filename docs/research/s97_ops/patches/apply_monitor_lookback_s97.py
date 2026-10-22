"""S97 (TD-S97-NEW-20): monitor look-back 5 -> 7 min, so it cannot race the orchestrator's own row creation.
Run from the repo root (C:\\GammaEnginePython). Edits TWO files; nothing is written unless every anchor matches once.

Evidence (2026-10-22): the 03:25 orchestrator row was created 03:25:04.554 UTC; the monitor ticked at 03:30:04
(log, truncated to the second) and its window `created_at > now - 5 min` began after that row, so a healthy,
on-time cycle read "No orchestrator runs" and sent "Orchestrator not firing" (delivered); the same signature
(first_seen :04.8-:05.8 s past a cycle minute, RECOVERED ~10 min later) recurred through the session.
"""
import hashlib

MON = "monitor_orchestrator_health.py"
TEST = "tests/test_monitor_orchestrator_gate.py"

MON_EDITS = [
    (
        'LOOKBACK_MIN = 5    # the "no runs in last N minutes" probe window (unchanged)\n',
        'LOOKBACK_MIN = 7    # the "no runs in last N minutes" probe window: one 5-min cycle + 2 min.\n'
        "                    # S97 (TD-S97-NEW-20): at 5 it raced the orchestrator's own row creation --\n"
        "                    # on 2026-10-22 the 03:25 row was created 03:25:04.554 and the 03:30:04 tick's\n"
        '                    # window began after it, so a healthy cycle read "not firing".\n'
        "                    # Cost: a genuinely missed cycle alerts ~2 min later.\n",
    ),
    (
        "# back LOOKBACK_MIN=5 minutes every 1 minute, so a SINGLE SUCCESSFUL cycle sitting in that\n"
        "# look-back reads OK for up to 5 consecutive ticks. A 5-tick hold-down is therefore\n"
        "# satisfiable by one good cycle between two failing ones, and cannot tell recovery from a\n"
        "# single success; 10 ticks is two orchestrator cycles, which one success cannot span.\n",
        "# back LOOKBACK_MIN minutes every 1 minute (7 since S97; 5 before), so a SINGLE SUCCESSFUL\n"
        "# cycle sitting in that look-back reads OK for up to LOOKBACK_MIN consecutive ticks. A\n"
        "# hold-down at or below that is satisfiable by one good cycle between two failing ones, and\n"
        "# cannot tell recovery from a single success; 10 ticks exceeds 7 (margin 3; it was 5 at a\n"
        "# 5-min look-back), which one success cannot span.\n",
    ),
    (
        "            self.log('WARNING', 'No orchestrator runs in last 5 minutes')\n",
        "            self.log('WARNING', f'No orchestrator runs in last {LOOKBACK_MIN} minutes')\n",
    ),
    (
        "        self.log('INFO', f'Orchestrator OK ({len(rows)} runs in 5min)')\n",
        "        self.log('INFO', f'Orchestrator OK ({len(rows)} runs in {LOOKBACK_MIN}min)')\n",
    ),
    (
        "        # exit_code still alarms. A run that HANGS is not detected here (5-min look-back).\n",
        "        # exit_code still alarms. A run that HANGS is not detected here (LOOKBACK_MIN look-back).\n",
    ),
]

TEST_ANCHOR = r'print(f"\nMONITOR GATE '
TEST_BLOCK = r'''print('\n--- scenario 13 (S97, TD-S97-NEW-20): the look-back must not race the orchestrator row creation ---')
import contextlib
import re
import unittest.mock as mock

# 2026-10-22 ledger (script_execution_log.created_at) and monitor log, read 2026-10-22 09:06 IST.
ROW_0325 = datetime(2026, 10, 22, 3, 25, 4, 554000, tzinfo=UTC)
ROW_0330 = datetime(2026, 10, 22, 3, 30, 5, 636000, tzinfo=UTC)
# The monitor logged "[03:30:04] No orchestrator runs"; its log truncates to the second and the
# miss proves only that the tick fell after 03:30:04.554 (ROW_0325 + 5 min). 03:30:04.800 is inside.
TICK_0330 = datetime(2026, 10, 22, 3, 30, 4, 800000, tzinfo=UTC)


class _EmptyLedger:
    status_code = 200

    def json(self):
        return []


def since_built(now_utc, lookback=None):
    """The `created_at=gt.` bound _fetch_rows_http itself puts in its query, as UTC."""
    tmp = tempfile.mkdtemp(prefix='s97_lookback_')
    mon = H.HealthMonitor(now_utc=now_utc, send=lambda *a: True, is_trading_day=lambda: True,
                          window=WINDOW, state_path=Path(tmp) / 'monitor_alert_state.json')
    pin = mock.patch.object(H, 'LOOKBACK_MIN', lookback) if lookback is not None else contextlib.nullcontext()
    with pin, mock.patch.object(H.requests, 'get', return_value=_EmptyLedger()) as get:
        mon._fetch_rows_http()
    bound = re.search(r'created_at=gt\.([^&]+)', get.call_args.args[0]).group(1)
    return datetime.fromisoformat(bound).replace(tzinfo=UTC)


def visible(since, created, now):
    """The rows the probe would have seen: created_at=gt.<since> (PostgREST), and only rows that
    exist when the query runs -- a row created after the tick cannot be returned (S97 D.51.12)."""
    return [c for c in created if since < c <= now]


# control: the pre-S97 5-minute window reproduces the 2026-10-22 03:30:04 miss.
check('control: 5-min window at the 03:30:04.8 tick sees no row (the false "not firing")',
      visible(since_built(TICK_0330, lookback=5), [ROW_0325, ROW_0330], TICK_0330), [])
check('fixed window at the same tick sees the 03:25 run',
      visible(since_built(TICK_0330), [ROW_0325, ROW_0330], TICK_0330), [ROW_0325])
check('LOOKBACK_MIN is one cycle plus 2 min', H.LOOKBACK_MIN, 7)
check('hold-down still exceeds the look-back (one success cannot satisfy it)',
      H.HOLDDOWN_TICKS > H.LOOKBACK_MIN, True)
# a genuinely missed 03:30 cycle still reads "not firing", 2 min later than at 5.
TICK_0332 = datetime(2026, 10, 22, 3, 32, 30, tzinfo=UTC)
check('missed 03:30 cycle: at 03:32:30 the probe sees no row',
      visible(since_built(TICK_0332), [ROW_0325], TICK_0332), [])
tmp13 = tempfile.mkdtemp(prefix='s97_msg_')
mon13 = H.HealthMonitor(now_utc=IN, send=lambda *a: True, is_trading_day=lambda: True,
                        window=WINDOW, state_path=Path(tmp13) / 'monitor_alert_state.json',
                        fetch_rows=lambda: [])
conds13, _ = mon13.check_orchestrator_failures()
check('not-firing log line names the actual look-back',
      any(a['msg'] == 'No orchestrator runs in last 7 minutes' for a in mon13.alerts), True)
check('not-firing context gap_minutes', conds13[KEY][2]['gap_minutes'], 7)

'''

PLAN = [(MON, MON_EDITS), (TEST, [(TEST_ANCHOR, TEST_BLOCK + TEST_ANCHOR)])]

prepared = []
for path, edits in PLAN:
    raw = open(path, "rb").read()
    crlf = b"\r\n" in raw
    s = raw.decode("utf-8").replace("\r\n", "\n")
    before = s.count("\n")
    for old, new in edits:
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"STOPPED - anchor in {path} found {n} times (need 1): {old[:60]!r}; NO file changed")
        s = s.replace(old, new)
    out = (s.replace("\n", "\r\n") if crlf else s).encode("utf-8")
    prepared.append((path, out, crlf, before, s.count("\n")))

for path, out, crlf, before, after in prepared:
    open(path, "wb").write(out)
    print(f"{path}: eol={'CRLF' if crlf else 'LF'} lines {before} -> {after} "
          f"(+{after - before}) sha256_12={hashlib.sha256(out).hexdigest()[:12]}")
print("APPLIED S97 TD-S97-NEW-20 look-back")
