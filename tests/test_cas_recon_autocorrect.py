#!/usr/bin/env python3
"""S90 — backfill_cas_close_from_daily auto-correct: fix a MISMATCH only when two sources agree.

Fixtures are the three SENSEX mismatches of 2026-10-06 (bar / Dhan daily / 16:00 snapshot).
What would make this fail: correcting on the daily close alone (a disagreeing or absent
snapshot must leave the bar), writing when the bar changed since it was read, or a PATCH that
does not carry the old close as a guard. Offline: requests is stubbed.
Run: python3 tests/test_cas_recon_autocorrect.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import backfill_cas_close_from_daily as m  # noqa: E402

fails = 0


def check(name, cond, got):
    global fails
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {got}")
    fails += 0 if cond else 1


# ---- plan_corrections: the two-source rule
items = [("2026-08-24", "SENSEX", 77370.13, 77369.11),
         ("2026-09-23", "SENSEX", 74826.76, 74828.25),
         ("2026-10-05", "SENSEX", 72312.23, 72382.47),
         ("2026-10-06", "SENSEX", 1.00, 2.00),     # snapshot disagrees with daily
         ("2026-10-07", "SENSEX", 1.00, 2.00)]     # no snapshot
snaps = {("2026-08-24", "SENSEX"): 77369.11, ("2026-09-23", "SENSEX"): 74828.25,
         ("2026-10-05", "SENSEX"): 72382.47, ("2026-10-06", "SENSEX"): 1.00,
         ("2026-10-07", "SENSEX"): None}
fix, left = m.plan_corrections(items, snaps)
check("the 3 observed cases are fixed", [f[0] for f in fix] == ["2026-08-24", "2026-09-23", "2026-10-05"], [f[0] for f in fix])
check("snapshot disagreeing with daily -> left", ("2026-10-06" in [l[0] for l in left]), [l[0] for l in left])
check("no snapshot -> left (daily alone is not enough)", ("2026-10-07" in [l[0] for l in left]), [l[0] for l in left])


# ---- correct_close_bar: guarded PATCH
class R:
    def __init__(self, code, body):
        self.status_code, self._b, self.text = code, body, str(body)

    def json(self):
        return self._b


calls = []


def get_ok(url, headers=None, params=None, timeout=None):
    calls.append(("GET", params))
    return R(200, [{"high": 72312.23, "low": 72312.23, "close": 72312.23}])


def patch_ok(url, headers=None, params=None, json=None, timeout=None):
    calls.append(("PATCH", params, json))
    return R(200, [dict(json)])


m.requests.get, m.requests.patch = get_ok, patch_ok
n = m.correct_close_bar("SENSEX", "2026-10-05", 72312.23, 72382.47)
p = [c for c in calls if c[0] == "PATCH"][0]
check("one row corrected", n == 1, n)
check("PATCH guarded by the old close", ("close", "eq.72312.23") in p[1], p[1])
check("PATCH keyed on 15:29 IST = 09:59 UTC", ("bar_ts", "eq.2026-10-05T09:59:00+00:00") in p[1], p[1])
check("high raised to the new close, low kept", p[2] == {"close": 72382.47, "high": 72382.47, "low": 72312.23}, p[2])

calls.clear()
m.requests.get = lambda *a, **k: R(200, [{"high": 1, "low": 1, "close": 72300.00}])
n = m.correct_close_bar("SENSEX", "2026-10-05", 72312.23, 72382.47)
check("bar changed since read -> no PATCH", n == 0 and not [c for c in calls if c[0] == "PATCH"], n)

m.requests.get = lambda *a, **k: R(200, [])
check("no bar -> no PATCH", m.correct_close_bar("SENSEX", "2026-10-05", 72312.23, 72382.47) == 0, 0)

print("CAS RECON AUTOCORRECT " + ("ALL PASS" if fails == 0 else f"{fails} FAIL"))
sys.exit(1 if fails else 0)
