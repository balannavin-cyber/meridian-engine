#!/usr/bin/env python3
"""S97-N: the contract check's spot condition (TD-S97-NEW-7). Offline: no database, no network,
no Telegram, no real state file. Run from the repo root: python3 tests/test_contract_check_s97.py

Measured 2026-10-22 (bin/roq.sh): 84 spot checks; pre-open 9/9 stale (spot starts ~09:11 IST); in
session 12/72 stale at a 1-min window (writer every 60-63 s), 0/72 at 2 or 3 min; after 15:15 IST
3/3 stale (capture stopped 15:15:05). Each passing cell has a control that fails without the fix,
or is a real outage that must still alarm.
"""
from __future__ import annotations

import contextlib
import os
import re
import sys
import tempfile
import unittest.mock as mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ['TELEGRAM_BOT_TOKEN'] = ''
os.environ['TELEGRAM_CHAT_ID'] = ''
os.environ.setdefault('SUPABASE_URL', 'https://offline.invalid')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'offline-dummy-not-a-credential')

import validate_compute_contracts as V  # noqa: E402

fails = 0


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def check(name, got, want):
    global fails
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {name}  got {got!r} want {want!r}")
    fails += 0 if ok else 1
    return ok


class _Resp:
    def __init__(self, rows):
        self.status_code = 200
        self._rows = rows

    def json(self):
        return self._rows


def run_spot(now_utc, spot_rows, *, state_records=None, threshold=None):
    """Run the REAL check_spot_fresh at `now_utc` (naive UTC, as ContractValidator.ts is) against a
    fake table of `spot_rows` (naive UTC). The fake honours the check's own ts=gt.<since> bound and
    returns only rows that exist at `now_utc`. Returns (result, messages sent, validator)."""
    tmp = Path(tempfile.mkdtemp(prefix='s97n_state_')) / 'contract_alert_state.json'
    sent = []

    def fake_get(url, headers=None, timeout=None):
        since = datetime.fromisoformat(re.search(r'ts=gt\.([^&]+)', url).group(1))
        return _Resp([{'ts': r.isoformat(), 'spot': 22600.0} for r in spot_rows if since < r <= now_utc])

    pin = (mock.patch.object(V, 'SPOT_THRESHOLD_MIN', threshold) if threshold is not None
           else contextlib.nullcontext())
    with mock.patch.object(V, '_STATE_PATH', tmp), pin, \
            mock.patch.object(V, 'send_warning', lambda m, context=None: sent.append(m) or True), \
            mock.patch.object(V.requests, 'get', side_effect=fake_get):
        v = V.ContractValidator()
        if state_records and v.state is not None:
            v.state.data.update({k: dict(r) for k, r in state_records.items()})
        v.ts = now_utc
        result = v.check_spot_fresh()
    return result, sent, v


D = datetime(2026, 10, 22)


def utc(h, m, s=0, ms=0):
    return D.replace(hour=h, minute=m, second=s, microsecond=ms * 1000)


MSG3 = 'Contract VIOLATED: no spot data in last 3 minutes'

print('--- S97-N: spot check window, threshold and episode clearing ---')
# 1. the in-session race: check 03:49:04 UTC (09:19:04 IST), last write 61 s earlier
race = [utc(3, 48, 3)]
r_old, s_old, _ = run_spot(utc(3, 49, 4), race, threshold=1)
check('control: 1-min window, last write 61 s old -> stale (the 10-22 race)', r_old, False)
r_new, s_new, _ = run_spot(utc(3, 49, 4), race)
check('3-min window, same write -> fresh, nothing sent', (r_new, s_new), (True, []))
# 2. pre-open 08:34:04 IST, no spot yet
r, s, v = run_spot(utc(3, 4, 4), [])
check('pre-open 08:34 IST: skipped, not a violation, nothing sent',
      (r, v.violations, 'spot_fresh_skipped' in v.passed, s), (True, [], True, []))
r_c, s_c, _ = run_spot(utc(3, 49, 4), [])
check('control: the same empty table in session -> stale and sent', (r_c, s_c), (False, [MSG3]))
# 3. after capture stops: 15:19:04 IST, last write 15:15:05.244 IST
r, s, _ = run_spot(utc(9, 49, 4), [utc(9, 45, 5, 244)])
check('after 15:15 IST: skipped, nothing sent', (r, s), (True, []))
# 4. a real stop inside the session must still alarm: 10:00:04 IST, last write 244 s earlier
r, s, _ = run_spot(utc(4, 30, 4), [utc(4, 26, 0)])
check('real 4-min stop in session -> stale, message names 3 minutes', (r, s), (False, [MSG3]))
# 5. window edges (half-open 09:15 <= t < 15:15 IST) and the constant
check('window: 09:15:00 IST inside', V._in_spot_window(utc(3, 45)), True)
check('window: 09:14:59 IST outside', V._in_spot_window(utc(3, 44, 59)), False)
check('window: 15:15:00 IST outside', V._in_spot_window(utc(9, 45)), False)
check('threshold constant', V.SPOT_THRESHOLD_MIN, 3)
# 6. clear-on-pass closes an old episode and keeps last_sent
old = {'contract_spot_stale': {'first_seen': '2026-10-09T03:04:03.875241',
                               'last_sent': (_utcnow() - timedelta(minutes=40)).isoformat(),
                               'sends': 100, 'clear_streak': 0, 'variant': None}}
r, s, v = run_spot(utc(3, 49, 4), race, state_records=old)
rec = dict(v.state.data.get('contract_spot_stale', {})) if v.state is not None else {}
check('pass closes the episode: first_seen and sends dropped, last_sent kept',
      (r, 'first_seen' in rec, 'sends' in rec, 'last_sent' in rec), (True, False, False, True))
# 7. the next failure after the clear (>30 min since last_sent) is a NEW episode
r, s, _ = run_spot(utc(4, 30, 4), [utc(4, 26, 0)], state_records={'contract_spot_stale': rec})
check('failure after a clear: sent once, no (still failing)', s, [MSG3])
r, s, _ = run_spot(utc(4, 30, 4), [utc(4, 26, 0)], state_records=old)
check('control: uncleared old record -> (still failing)', s, [MSG3 + ' (still failing)'])
# 8. the 30-min dedupe survives a clear
recent = {'contract_spot_stale': {'last_sent': (_utcnow() - timedelta(minutes=10)).isoformat()}}
r, s, _ = run_spot(utc(4, 30, 4), [utc(4, 26, 0)], state_records=recent)
check('cleared record last sent 10 min ago -> failure suppressed', (r, s), (False, []))

print(f"\nCONTRACT CHECK S97-N {'ALL PASS' if fails == 0 else f'{fails} FAIL'}")
sys.exit(1 if fails else 0)
