"""S97-N (TD-S97-NEW-7): contract-check spot condition -- 09:15-15:15 IST window, 3-min threshold, clear-on-pass.
Run from the repo root (C:\\GammaEnginePython). Edits validate_compute_contracts.py (count==1 anchors, then
ast.parse before writing) and CREATES tests/test_contract_check_s97.py (refuses if it exists).

Measured 2026-10-22 (bin/roq.sh, 84 spot checks at the cron's own times): pre-open 9/9 stale (spot starts ~09:11
IST); in session 12/72 stale at a 1-min window (the writer runs every 60-63 s), 0/72 at 2 or 3 min; after
15:15 IST 3/3 stale (capture stopped 15:15:05). Every spot alarm that day was an artefact of the check.
"""
import ast
import hashlib
import os

SRC = "validate_compute_contracts.py"
TEST = "tests/test_contract_check_s97.py"

HELPERS = '''# ---- S97-N: spot-check window, threshold and episode clearing (TD-S97-NEW-7) ---------------
# Measured 2026-10-22 (84 spot checks): pre-open 9/9 stale -- spot starts ~09:11 IST; in session
# 12/72 stale at a 1-min window (the writer runs every 60-63 s, so the check raced it) and 0/72 at
# 2 or 3 min; after 15:15 IST 3/3 stale -- capture stopped at 15:15:05. Whether spot SHOULD run to
# 15:30 is a separate question (parity evaluation D2-4), not this check's.
from datetime import time as _time, timezone as _timezone  # noqa: E402

SPOT_THRESHOLD_MIN = 3
_IST = _timezone(timedelta(hours=5, minutes=30))
_SPOT_WINDOW_IST = (_time(9, 15), _time(15, 15))   # half-open: 09:15 <= t < 15:15


def _in_spot_window(now_utc_naive) -> bool:
    """ContractValidator.ts is naive UTC (datetime.utcnow()). Inside 09:15-15:15 IST?"""
    t = now_utc_naive.replace(tzinfo=_timezone.utc).astimezone(_IST).time()
    return _SPOT_WINDOW_IST[0] <= t < _SPOT_WINDOW_IST[1]


def _clear_key(state, key: str) -> None:
    """A passing check closes the key's episode: first_seen / sends / clear_streak / variant are
    dropped, so the next failure starts a NEW episode (fresh first_seen, no '(still failing)').
    last_sent is KEPT, so the 30-min dedupe still holds across a pass -- a check that flaps
    fail/pass/fail cannot send more often than before."""
    if state is None:
        return
    rec = state.data.get(key)
    if rec and 'first_seen' in rec:
        state.data[key] = {'last_sent': rec.get('last_sent')}
        print(f'[CLEAR] {key}: check passed, episode since {rec["first_seen"]} closed')


'''

SPOT_GATE = (
    "        # S97-N: spot is checked only 09:15-15:15 IST, against a SPOT_THRESHOLD_MIN window.\n"
    "        if not _in_spot_window(self.ts):\n"
    "            self.log('INFO', 'Contract SKIPPED: spot outside 09:15-15:15 IST (S97-N)')\n"
    "            self.passed.append('spot_fresh_skipped')\n"
    "            return True\n"
    "        since = (self.ts - timedelta(minutes=SPOT_THRESHOLD_MIN)).isoformat()\n"
)

EDITS = [
    ("SUPABASE_URL = os.getenv('SUPABASE_URL')\n",
     HELPERS + "SUPABASE_URL = os.getenv('SUPABASE_URL')\n"),
    ('"""Verify spot data exists and is <1 min old."""',
     '"""Verify spot data exists and is < SPOT_THRESHOLD_MIN (3) min old; 09:15-15:15 IST only (S97-N)."""'),
    ("        one_min_ago = (self.ts - timedelta(minutes=1)).isoformat()\n", SPOT_GATE),
    ("ts=gt.{one_min_ago}&limit=1&select=ts,spot", "ts=gt.{since}&limit=1&select=ts,spot"),
    ('msg = "Contract VIOLATED: no spot data in last 1 minute"',
     'msg = f"Contract VIOLATED: no spot data in last {SPOT_THRESHOLD_MIN} minutes"'),
    ("{'threshold_min': 1, 'table': 'market_spot_snapshots'}",
     "{'threshold_min': SPOT_THRESHOLD_MIN, 'table': 'market_spot_snapshots'}"),
    ("            self.passed.append('spot_fresh')\n",
     "            self.passed.append('spot_fresh')\n"
     "            _clear_key(self.state, 'contract_spot_stale')\n"),
    ("            self.passed.append('option_chain_fresh')\n",
     "            self.passed.append('option_chain_fresh')\n"
     "            _clear_key(self.state, 'contract_option_chain_stale')\n"),
    ("        self.log('INFO', '=== ALL CONTRACTS PASSED ===')\n",
     "        self.log('INFO', '=== ALL CONTRACTS PASSED ===')\n"
     "        _clear_key(self.state, 'contract_violations_summary')\n"),
]

TEST_SRC = r'''#!/usr/bin/env python3
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
'''

if os.path.exists(TEST):
    raise SystemExit(f"STOPPED - {TEST} already exists; NO file changed")

raw = open(SRC, "rb").read()
crlf = b"\r\n" in raw
s = raw.decode("utf-8").replace("\r\n", "\n")
before = s.count("\n")
for old, new in EDITS:
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"STOPPED - anchor found {n} times (need 1): {old[:70]!r}; NO file changed")
    s = s.replace(old, new)
bom = s.startswith('\ufeff')   # the file carries a UTF-8 BOM: parse without it, write it back unchanged
try:
    ast.parse(s.lstrip('\ufeff'))
    ast.parse(TEST_SRC)
except SyntaxError as e:
    raise SystemExit(f"STOPPED - patched source does not parse ({e}); NO file changed")

out = (s.replace("\n", "\r\n") if crlf else s).encode("utf-8")
test_out = (TEST_SRC.replace("\n", "\r\n") if crlf else TEST_SRC).encode("utf-8")
open(SRC, "wb").write(out)
open(TEST, "wb").write(test_out)
print(f"{SRC}: bom={bom} eol={'CRLF' if crlf else 'LF'} lines {before} -> {s.count(chr(10))} "
      f"(+{s.count(chr(10)) - before}) sha256_12={hashlib.sha256(out).hexdigest()[:12]}")
print(f"{TEST}: created, {TEST_SRC.count(chr(10))} lines, sha256_12={hashlib.sha256(test_out).hexdigest()[:12]}")
print("APPLIED S97-N")
