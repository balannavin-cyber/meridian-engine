#!/usr/bin/env python3
"""S90 — capture_cas_close.fetch_cas_bar picks the close-slot bar, not the last bar.

Fixture is the vendor response observed 2026-10-06 19:52 IST (15:25-15:35 window):
Dhan returned 15:26..15:29 and then a bar stamped at call time (NIFTY 18:30,
SENSEX 17:00). The job took the last bar and refused every session.

What would make this fail: picking [-1] (returns the 18:30 bar), picking the wrong
slot, or accepting a bar when no close slot exists (Guard 2 must still see a
non-slot bar). Offline: requests.post is stubbed; no network, no credentials.
Run: python3 tests/test_cas_close_slot_pick.py
"""
from __future__ import annotations

import sys
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import capture_cas_close as m  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
D = date(2026, 10, 6)


def ep(hm: str, d: date = D) -> int:
    h, mi = (int(x) for x in hm.split(":"))
    return int(datetime(d.year, d.month, d.day, h, mi, tzinfo=IST).timestamp())


class Resp:
    status_code = 200

    def __init__(self, body):
        self._b = body

    def json(self):
        return self._b


def body(rows):
    return {"timestamp": [ep(t) for t, _, _ in rows], "open": [o for _, o, _ in rows],
            "high": [max(o, c) for _, o, c in rows], "low": [min(o, c) for _, o, c in rows],
            "close": [c for _, _, c in rows], "volume": [0] * len(rows)}


def run(rows):
    m.requests.post = lambda *a, **k: Resp(body(rows))
    return m.fetch_cas_bar("NIFTY", D)


fails = 0


def check(name, cond, got):
    global fails
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {got}")
    fails += 0 if cond else 1


# 1. observed NIFTY shape: 15:29 is the settled close, 18:30 is the call-time tail
b = run([("15:26", 22717.7, 22717.7), ("15:27", 22717.7, 22717.7), ("15:28", 22717.7, 22717.7),
         ("15:29", 22717.7, 22776.1), ("18:30", 22776.1, 22776.1)])
slot = datetime.fromtimestamp(b["timestamp"], IST).strftime("%H:%M")
check("NIFTY picks 15:29, not the 18:30 tail", slot == "15:29" and b["close"] == 22776.1, (slot, b["close"]))

# 2. observed SENSEX shape: flat 15:29 bar after the settle in 15:28, 17:00 tail
b = run([("15:26", 72943.91, 72943.91), ("15:27", 72943.91, 72943.91), ("15:28", 72943.91, 73067.81),
         ("15:29", 73067.81, 73067.81), ("17:00", 73067.81, 73067.81)])
slot = datetime.fromtimestamp(b["timestamp"], IST).strftime("%H:%M")
check("SENSEX picks 15:29 (flat), close 73067.81", slot == "15:29" and b["close"] == 73067.81, (slot, b["close"]))

# 3. first-CAS-week shape: last bar 15:34 is itself a close slot
b = run([("15:30", 1.0, 1.0), ("15:34", 1.0, 2.0)])
slot = datetime.fromtimestamp(b["timestamp"], IST).strftime("%H:%M")
check("15:34 slot still accepted", slot == "15:34" and b["close"] == 2.0, slot)

# 4. no close slot at all: falls back to the last bar, which Guard 2 refuses
b = run([("15:26", 1.0, 1.0), ("16:20", 1.0, 1.0)])
t = datetime.fromtimestamp(b["timestamp"], IST)
check("no slot -> last bar returned, outside slot set (Guard 2 rejects)",
      (t.hour, t.minute) not in m.CAS_CLOSE_BAR_SLOTS, t.strftime("%H:%M"))

# 5. a 15:29 bar from ANOTHER day must not be taken
m.requests.post = lambda *a, **k: Resp({"timestamp": [ep("15:29", date(2026, 10, 5)), ep("16:20")],
                                        "open": [1.0, 1.0], "high": [1.0, 1.0], "low": [1.0, 1.0],
                                        "close": [9.0, 1.0], "volume": [0, 0]})
b = m.fetch_cas_bar("NIFTY", D)
check("other-day 15:29 ignored", b["close"] == 1.0, b["close"])

# 6. empty window still None
m.requests.post = lambda *a, **k: Resp({"open": []})
check("empty window -> None", m.fetch_cas_bar("NIFTY", D) is None, None)

print("CAS SLOT PICK " + ("ALL PASS" if fails == 0 else f"{fails} FAIL"))
sys.exit(1 if fails else 0)
