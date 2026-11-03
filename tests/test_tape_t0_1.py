#!/usr/bin/env python3
"""Tape T0.1 guards (docs/tape/T0_1_plan.md section 4): silence watchdog, special sessions, counters.
Offline: no network, no credentials, no kiteconnect, no Twisted. Reuses the T0 fakes (FakeKite, FakeS3,
ManualClock, packet builders) by importing tests/test_tape_t0.py from the tree under test.

  python3 tests/test_tape_t0_1.py [--root DIR] [--only GUARD]

--root runs the guards against another copy of the tree (tests/tape_t0_1_mutants.py uses it).
Every expected value below is written from the scripted inputs (the belief), never taken from a run.
Last line: "TAPE T0.1 PASS (G/G guards, U/U unit checks)" or "TAPE T0.1 FAIL ...". Exit 0 / 1.
"""
import argparse
import gzip
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--only", default=None)
ARGS = ap.parse_args()
ROOT = os.path.abspath(ARGS.root)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "tape_t1a"))


def _load_t0():
    saved = sys.argv
    sys.argv = ["test_tape_t0.py", "--root", ROOT]
    try:
        spec = importlib.util.spec_from_file_location("tape_t0_tests", os.path.join(ROOT, "tests", "test_tape_t0.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.argv = saved


T0 = _load_t0()
ManualClock, FakeKite, FakeS3, FakeTicker = T0.ManualClock, T0.FakeKite, T0.FakeS3, T0.FakeTicker
ist_ns, idx_pkt, full_pkt, TOK, tmpdir = T0.ist_ns, T0.idx_pkt, T0.full_pkt, T0.TOK, T0.tmpdir

from services.tape_runner import config  # noqa: E402

DN = "2026-11-03"       # a Tuesday, normal session (front weekly expiry 2026-11-04 in the T0 fake instruments)
DS = "2026-11-08"       # Sunday, Muhurat
PREV_S = "2026-11-06"   # last ordinary session before it
LABEL = "Muhurat F&O per NSE/FAOP/76940"
# NSE/FAOP/76940 (F&O segment, 2026-11-08): pre-open 14:05-14:20, normal market 14:20-15:40. Written from the circular.
CAL = [{"date": "2026-11-08", "open": "14:20", "close": "15:40", "label": LABEL}]
SILENCE = 15
NS = 10 ** 9

TIMER_TEXT = """# /etc/systemd/system/tape-runner-special-2026-11-08.timer  (generated from special_sessions.json; Muhurat F&O per NSE/FAOP/76940)
[Unit]
Description=MERIDIAN tape raw recorder (T0) -- special session 2026-11-08 (Muhurat F&O per NSE/FAOP/76940), start 13:55 IST

[Timer]
OnCalendar=2026-11-08 13:55:00 Asia/Kolkata
Persistent=false
AccuracySec=1s
Unit=tape-runner.service

[Install]
WantedBy=timers.target
"""


def write_cal(entries, name="cal.json"):
    p = os.path.join(tmpdir(), name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(entries, fh)
    return p


CAL_PATH = write_cal(CAL)


class WdTicker(FakeTicker):
    """FakeTicker + the two things the watchdog needs: on_message and a scripted force_reconnect.
    script items: 'ok' (drop works: on_close fires), 'raise', 'silent' (returns but nothing closes)."""

    def __init__(self, script=None):
        super().__init__()
        self.on_message = None
        self.script = list(script or [])
        self.drops = []
        self.clock = None
        self.pending_close = False

    def force_reconnect(self):
        self.drops.append(self.clock.now_ns())
        act = self.script.pop(0) if self.script else "ok"
        if act == "raise":
            raise RuntimeError("reactor refused")
        if act == "ok":
            self.on_close(self, 1006, "abort")

    def close(self, *a):
        self.calls.append(("close",))
        self.pending_close = True          # the real close handshake answers later, from the reactor thread

    def deliver_pending_close(self):
        if self.pending_close:
            self.pending_close = False
            self.on_close(self, 1000, "client close")


def make_rec(day, start, kite=None, script=None, cal=True, log=None, s3=None, root=None):
    from services.tape_runner.recorder import Recorder
    config.SPECIAL_SESSIONS_PATH = CAL_PATH if cal is True else (cal or os.path.join(tmpdir(), "absent.json"))
    clock = ManualClock(ist_ns(day, start))
    tickers = []

    def factory():
        t = WdTicker(script)
        t.clock = clock
        tickers.append(t)
        return t
    lines = [] if log is None else log
    rec = Recorder(kite or FakeKite(), factory, s3 or FakeS3(), clock, root=root or tmpdir(), bucket="test-bucket",
                   threaded=False, secrets=("SECRETKEY", "SECRETTOKEN"), log=lines.append)
    rec.lines = lines
    return rec, clock, tickers


def at(clock, day, hms):
    clock.set(ist_ns(day, hms))
    return clock.now_ns()


def boot_normal(day, script=None, connect_at="08:55", tick_at="09:00:01", **kw):
    rec, clock, tk = make_rec(day, "08:50", script=script, **kw)
    assert rec.step(clock.now_ns()) is None
    at(clock, day, connect_at)
    assert rec.step(clock.now_ns()) is None
    t = tk[0]
    t.on_connect(t, {})
    if tick_at:
        at(clock, day, tick_at)
        t.on_ticks(t, [idx_pkt("NIFTY", 25000.0, day, tick_at), idx_pkt("SENSEX", 80000.0, day, tick_at)])
        assert rec.step(clock.now_ns()) is None
    return rec, clock, t


def beat(t, clock):
    t.on_message(t, b"\x00", True)         # a 1-byte Kite heartbeat: only on_message sees it


def run_beats(rec, t, clock, day, start_hms, seconds):
    """one heartbeat + one step per second, from start_hms for `seconds`+1 steps."""
    base = ist_ns(day, start_hms)
    for s in range(seconds + 1):
        clock.set(base + s * NS)
        beat(t, clock)
        assert rec.step(clock.now_ns()) is None


def run_silent(rec, clock, day, start_hms, seconds):
    base = ist_ns(day, start_hms)
    for s in range(1, seconds + 1):
        clock.set(base + s * NS)
        assert rec.step(clock.now_ns()) is None


# ======================================================================== guards
def g_wd_trip():
    """Fails if the watchdog is off, trips at the wrong age, reads the threshold in the wrong unit,
    does not reconnect, or does not count."""
    rec, clock, t = boot_normal(DN)
    run_beats(rec, t, clock, DN, "09:16:00", 60)                       # a healthy minute of 1 s heartbeats
    cells = [(rec.stats.watchdog_trips == 0 and not t.drops, "60 s of 1 s heartbeats: trips=%d drops=%d"
              % (rec.stats.watchdog_trips, len(t.drops)))]
    last = ist_ns(DN, "09:17:00")
    run_silent(rec, clock, DN, "09:17:00", 14)                          # age 14 s
    cells.append((rec.stats.watchdog_trips == 0 and not t.drops, "age 14 s: no trip (trips=%d)" % rec.stats.watchdog_trips))
    clock.set(last + 15 * NS)                                           # age 15 s
    rec.step(clock.now_ns())
    cells.append((rec.stats.watchdog_trips == 1 and len(t.drops) == 1 and t.drops[0] == last + 15 * NS,
                  "age 15 s: trips=%d drops=%d at +%s s" % (rec.stats.watchdog_trips, len(t.drops),
                                                           [(d - last) // NS for d in t.drops])))
    cells.append((any("WATCHDOG_TRIP" in m and "age=15" in m for m in rec.lines),
                  "trip logged with the last-frame age"))
    cells.append((rec.connected is False, "the forced close reached on_close (connected=%s)" % rec.connected))
    run_silent(rec, clock, DN, "09:17:15", 5)
    cells.append((len(t.drops) == 1, "disconnected: the library is retrying, no second trip (drops=%d)" % len(t.drops)))
    # the library reconnects; recording resumes
    at(clock, DN, "09:17:22")
    t.on_connect(t, {})
    fut = TOK[("NIFTY", "FUT")]
    at(clock, DN, "09:17:23")
    t.on_ticks(t, [full_pkt(fut, 25100, 1000, DN, "09:17:23")])
    rec.step(clock.now_ns())
    cells.append((rec.connected and rec.stats.packets["NIFTY"] >= 1 and rec.stats.watchdog_trips == 1,
                  "recording resumed after reconnect: connected=%s packets=%d trips=%d"
                  % (rec.connected, rec.stats.packets["NIFTY"], rec.stats.watchdog_trips)))
    rec.writer.flush()
    spooled = b""
    for dp, _, fs in os.walk(rec.spool):
        for f in fs:
            if "NIFTY" in dp or "SENSEX" in dp:
                spooled += open(os.path.join(dp, f), "rb").read()
    cells.append((spooled.count(b'"ctl":"watchdog"') == 2, "a watchdog ctl record in each symbol's segment: %d"
                  % spooled.count(b'"ctl":"watchdog"')))
    t.on_message(t, b"\x00", True)
    rec.step(at(clock, DN, "09:18:01"))                  # the heartbeat file is rewritten once a minute
    hb = json.load(open(rec.heartbeat_path))
    cells.append((hb.get("watchdog_trips") == 1 and "last_frame_age_s" in hb and "frames_hb" in hb,
                  "heartbeat JSON carries watchdog_trips=%s, last_frame_age_s, frames_hb" % hb.get("watchdog_trips")))
    return cells


def g_wd_window():
    """Fails if the watchdog is armed outside the recording window or ignores the connect/open floor."""
    cells = []
    # A. connected and silent from 08:55: nothing before 09:15:15; first trip exactly 15 s after the open
    rec, clock, t = boot_normal(DN, tick_at=None)
    for hms in ("09:00", "09:10", "09:14:59", "09:15:00", "09:15:14"):
        rec.step(at(clock, DN, hms))
    cells.append((rec.stats.watchdog_trips == 0 and not t.drops,
                  "quiet pre-open 08:55-09:15:14: trips=%d" % rec.stats.watchdog_trips))
    rec.step(at(clock, DN, "09:15:15"))
    cells.append((rec.stats.watchdog_trips == 1, "09:15:15 (15 s after the open): trips=%d" % rec.stats.watchdog_trips))
    # B. after the close: silence from 15:29:40 -> no trip after 15:30:00; control: the same silence 15 s earlier trips
    rec, clock, t = boot_normal(DN)
    for hms in ("09:20", "12:00"):
        at(clock, DN, hms)
        beat(t, clock)
        rec.step(clock.now_ns())
    at(clock, DN, "15:29:40")
    beat(t, clock)
    rec.step(clock.now_ns())
    for hms in ("15:29:54", "15:29:55"):
        rec.step(at(clock, DN, hms))
    cells.append((rec.stats.watchdog_trips == 1 and len(t.drops) == 1,
                  "control: silence from 15:29:40, trip at 15:29:55 inside the window (trips=%d)" % rec.stats.watchdog_trips))
    rec, clock, t = boot_normal(DN)
    at(clock, DN, "15:29:50")
    beat(t, clock)
    rec.step(clock.now_ns())
    for hms in ("15:30:00", "15:30:30", "15:35", "15:39:59"):
        rec.step(at(clock, DN, hms))
    cells.append((rec.stats.watchdog_trips == 0 and not t.drops,
                  "silence after 15:30 until 15:39:59: trips=%d" % rec.stats.watchdog_trips))
    # C. a restart at 11:00: connect at 11:00:05, no stale-stamp trip before 11:00:20
    rec, clock, tk = make_rec(DN, "11:00:00")
    rec.step(clock.now_ns())
    t = tk[0]
    at(clock, DN, "11:00:05")
    t.on_connect(t, {})
    for hms in ("11:00:06", "11:00:19"):
        rec.step(at(clock, DN, hms))
    early = rec.stats.watchdog_trips
    rec.step(at(clock, DN, "11:00:20"))
    cells.append((early == 0 and rec.stats.watchdog_trips == 1,
                  "restart at 11:00: no trip at 11:00:19 (%d), trip at 11:00:20 (%d)" % (early, rec.stats.watchdog_trips)))
    return cells


def g_wd_backoff():
    """Fails if the retry spacing is not 1,2,4,8,15,15,..., if a raising reconnect escapes step(), or if
    recording does not resume once a reconnect works."""
    script = ["silent"] + ["raise"] * 6 + ["ok"]
    rec, clock, t = boot_normal(DN, script=script)
    run_beats(rec, t, clock, DN, "09:16:00", 5)
    last = ist_ns(DN, "09:16:05")
    codes = []
    for s in range(1, 90):
        clock.set(last + s * NS)
        codes.append(rec.step(clock.now_ns()))
    rel = [(d - last) // NS for d in t.drops]
    gaps = [b - a for a, b in zip(rel, rel[1:])]
    cells = [(all(c is None for c in codes), "no exit code from step() while the drop raises (%s)" % set(codes)),
             (rel == [15, 16, 18, 22, 30, 45, 60, 75], "attempt times after the last frame %s" % rel),
             (gaps == [1, 2, 4, 8, 15, 15, 15], "gaps %s (want 1,2,4,8,15,15,15)" % gaps),
             (rec.stats.watchdog_errors == 6 and rec.stats.watchdog_trips == 8,
              "trips=%d errors=%d (want 8, 6)" % (rec.stats.watchdog_trips, rec.stats.watchdog_errors)),
             (len(t.script) == 0 and rec.connected is False, "the 8th drop worked: on_close seen")]
    at(clock, DN, "09:17:40")
    t.on_connect(t, {})
    at(clock, DN, "09:17:41")
    t.on_ticks(t, [full_pkt(TOK[("NIFTY", "FUT")], 25100, 2000, DN, "09:17:41")])
    cells.append((rec.step(clock.now_ns()) is None and rec.connected and rec.stats.packets["NIFTY"] >= 1,
                  "recording resumed"))
    t.on_message(t, b"\x00", True)
    at(clock, DN, "09:17:42")
    rec.step(clock.now_ns())
    cells.append((rec._wd_step == 0, "a frame resets the backoff (step=%s)" % rec._wd_step))
    return cells


def g_special_day():
    """Fails if the calendar is ignored (window, closed-day rule, options, stop), or the timer text drifts."""
    from services.tape_runner import session
    cells = []
    # window, from NSE/FAOP/76940 (F&O): open 14:20, close 15:40; offsets of the weekday timeline (stop = close + 10)
    rec, clock, tk = make_rec(DS, "13:55:00")
    want = {"start": "13:55", "resolve": "14:00", "options": "14:05", "closed_check": "14:25",
            "session_start": "14:20", "session_end": "15:40", "stop": "15:50", "resolve_giveup": "14:15"}
    got = {k: rec.win[k] for k in want}
    cells.append((got == want and rec.win["special"] is True, "window %s" % got))
    # 13:54:59 is an early start; 13:55:00 is not
    r2, c2, _ = make_rec(DS, "13:54:59")
    code = r2.step(c2.now_ns())
    cells.append((code == 0 and r2.state == "EARLY_EXIT", "start 13:54:59 -> early exit (code %s, %s)" % (code, r2.state)))
    cells.append((rec.step(clock.now_ns()) is None and rec.state != "EARLY_EXIT", "start 13:55:00 -> runs"))
    # live Muhurat: price moved since resolve; no witness dated today until 14:19; first index packet 14:19:30
    kite = FakeKite()
    rec, clock, tk = make_rec(DS, "13:55:00", kite=kite)
    rec.step(clock.now_ns())
    rec.step(at(clock, DS, "14:00:00"))
    t = tk[0]
    t.on_connect(t, {})
    t.on_ticks(t, [idx_pkt("NIFTY", 25000.0, PREV_S, "15:30:00"), idx_pkt("SENSEX", 80000.0, PREV_S, "15:30:00")])
    kite.prices = {"NSE:NIFTY 50": 25600.0, "BSE:SENSEX": 80000.0}    # 600 points from the resolve-time price
    rec.step(at(clock, DS, "14:05:00"))
    rec.step(at(clock, DS, "14:19:59"))
    cells.append((not rec.options_on, "14:05-14:19:59 with no witness dated today: options not open"))
    rec.step(at(clock, DS, "14:20:00"))
    centre = rec.centre.get("NIFTY")
    opts = [m for m in rec.subscribed.values() if m["sym"] == "NIFTY" and m["role"] == "OPT"]
    reasons = {m["reason"] for m in opts}
    strikes = sorted({m["strike"] for m in opts}) or [None, None]
    cells.append((rec.options_on and reasons == {"special_open_forced"}, "options forced open at 14:20:00: %s" % reasons))
    cells.append((centre == 25600.0 and strikes[0] == 25600.0 - 20 * 50 and strikes[-1] == 25600.0 + 20 * 50
                  and len(opts) == 2 * 41,
                  "first price read at 14:20 (25600, not the resolve-time 25000): centre %s window %s..%s n=%d"
                  % (centre, strikes[0], strikes[-1], len(opts))))
    # today's packet arrives -> OPEN at 14:25, never earlier
    at(clock, DS, "14:20:05")
    t.on_ticks(t, [idx_pkt("NIFTY", 25600.0, DS, "14:20:05"), idx_pkt("SENSEX", 80000.0, DS, "14:20:05")])
    for hms in ("14:20:30", "14:21", "14:22", "14:23", "14:24"):
        beat(t, at(clock, DS, hms))
        rec.step(clock.now_ns())
    beat(t, at(clock, DS, "14:24:59"))
    rec.step(clock.now_ns())
    before = rec.closed_checked
    beat(t, at(clock, DS, "14:25:00"))
    rec.step(clock.now_ns())
    cells.append((before is False and rec.closed_checked and rec.stats.closed_check["verdict"] == "OPEN",
                  "closed check not before 14:25 (%s), then verdict %s" % (before, rec.stats.closed_check)))
    # stop at close + 10 = 15:50 (the F&O close is 15:40)
    code_a = rec.step(at(clock, DS, "15:49:59"))     # after the close: the watchdog is not armed
    code_b = rec.step(at(clock, DS, "15:50:00"))
    cells.append((code_a is None and code_b == 0, "stop: 15:49:59 -> %s, 15:50:00 -> %s" % (code_a, code_b)))
    # holiday-shaped special day: only previous-session witnesses, stale REST quote -> CLOSED at 14:25, not 14:02
    stale = {"NSE:NIFTY 50": {"timestamp": T0.datetime(2026, 11, 6, 15, 29, 58)},
             "BSE:SENSEX": {"timestamp": T0.datetime(2026, 11, 6, 15, 29, 59)}}
    rec, clock, tk = make_rec(DS, "13:55:00", kite=FakeKite(quote=stale))
    rec.step(clock.now_ns())
    rec.step(at(clock, DS, "14:00:00"))
    t = tk[0]
    t.on_connect(t, {})
    at(clock, DS, "14:00:02")
    t.on_ticks(t, [idx_pkt("NIFTY", 25000.0, PREV_S, "15:30:00"), idx_pkt("SENSEX", 80000.0, PREV_S, "15:30:00"),
                   full_pkt(TOK[("NIFTY", "FUT")], 25100, 5000, PREV_S, "15:29:59"),
                   full_pkt(TOK[("SENSEX", "FUT")], 80100, 5000, PREV_S, "15:29:59")])
    done = None
    for hms in ("14:02", "14:10", "14:20", "14:24:59", "14:25:00"):
        at(clock, DS, hms)
        beat(t, clock)
        c = rec.step(clock.now_ns())
        if c is not None:
            done = hms
            break
    cells.append((done == "14:25:00", "stale-witness special day: CLOSED declared at %s (14:25:00 wanted)" % done))
    # the timer text, byte for byte
    cells.append((session.render_timer(CAL[0]) == TIMER_TEXT, "generated timer text equals the plan's literal"))
    return cells


def _boot_special(hold=("14:21", "14:22", "14:23", "14:24", "14:25")):
    """A Muhurat recorder that is healthy and open: connects 14:00, options forced 14:20, today's packet 14:20:05,
    a heartbeat before every step so nothing is silent, closed check OPEN at 14:25."""
    rec, clock, tk = make_rec(DS, "13:55:00")
    rec.step(clock.now_ns())
    rec.step(at(clock, DS, "14:00:00"))
    t = tk[0]
    t.on_connect(t, {})
    rec.step(at(clock, DS, "14:20:00"))
    at(clock, DS, "14:20:05")
    t.on_ticks(t, [idx_pkt("NIFTY", 25000.0, DS, "14:20:05"), idx_pkt("SENSEX", 80000.0, DS, "14:20:05")])
    for hms in hold:
        beat(t, at(clock, DS, hms))
        assert rec.step(clock.now_ns()) is None
    return rec, clock, t


def g_fo_close():
    """NSE/FAOP/76940: the F&O close on 2026-11-08 is 15:40 (pre-open 14:05-14:20, market 14:20-15:40). Fails if the
    checked-in calendar says anything else, the stop / gap accounting / watchdog window still use 15:30, or the
    watchdog stays armed after 15:40."""
    from services.tape_runner import session
    from services.tape_runner.stats import DayStats
    real = os.path.join(ROOT, "services", "tape_runner", "special_sessions.json")
    ent = [e for e in json.load(open(real)) if e.get("date") == DS]
    cells = [(len(ent) == 1 and ent[0].get("open") == "14:20" and ent[0].get("close") == "15:40"
              and "NSE/FAOP/76940" in ent[0].get("label", ""),
              "checked-in calendar: open 14:20, close 15:40, label cites the circular: %s" % ent)]
    w = session.window(DS, path=real)
    cells.append(((w["session_start"], w["session_end"], w["stop"], w["closed_check"]) == ("14:20", "15:40", "15:50", "14:25"),
                  "window from the checked-in file: open %s close %s stop %s closed_check %s"
                  % (w["session_start"], w["session_end"], w["stop"], w["closed_check"])))
    saved = config.SPECIAL_SESSIONS_PATH
    try:
        config.SPECIAL_SESSIONS_PATH = real
        st = DayStats(DS, ["NIFTY", "SENSEX"])
        cells.append((st._end_ns == ist_ns(DS, "15:40") and st._start_ns == ist_ns(DS, "14:20"),
                      "gap accounting spans 14:20 -> 15:40, not -> 15:30"))
    finally:
        config.SPECIAL_SESSIONS_PATH = saved
    # watchdog: silent from 15:39:40 -> trips at 15:39:55, which is after the old 15:30 close and inside the new one
    rec, clock, t = _boot_special()
    for hms in ("15:00", "15:39:40"):
        beat(t, at(clock, DS, hms))
        rec.step(clock.now_ns())
    rec.step(at(clock, DS, "15:39:54"))
    before = rec.stats.watchdog_trips
    rec.step(at(clock, DS, "15:39:55"))
    cells.append((before == 0 and rec.stats.watchdog_trips == 1 and len(t.drops) == 1,
                  "control: silence from 15:39:40 trips at 15:39:55 (inside the F&O session): before=%d trips=%d"
                  % (before, rec.stats.watchdog_trips)))
    # ... and silence after the F&O close is not a fault
    rec, clock, t = _boot_special()
    for hms in ("15:00", "15:39:50"):
        beat(t, at(clock, DS, hms))
        rec.step(clock.now_ns())
    codes = [rec.step(at(clock, DS, hms)) for hms in ("15:40:00", "15:40:30", "15:45", "15:49:59")]
    cells.append((rec.stats.watchdog_trips == 0 and not t.drops and all(c is None for c in codes),
                  "silence after 15:40 until 15:49:59: trips=%d codes=%s" % (rec.stats.watchdog_trips, codes)))
    return cells


class _BadPayload:
    """A frame whose length cannot be read: the one way on_frame's counting can raise."""

    def __len__(self):
        raise RuntimeError("payload length unreadable")


def g_frame_errors():
    """Fails if on_frame can raise (the library would drop that frame's ticks), loses the liveness stamp when its
    counting fails, does not count or report the failure, or logs more than once a minute."""
    cells = []
    rec, clock, t = boot_normal(DN)
    at(clock, DN, "09:30:00")
    raised = None
    try:
        t.on_message(t, _BadPayload(), True)
    except BaseException as exc:  # noqa: BLE001
        raised = exc
    cells.append((raised is None, "on_frame with an unreadable payload does not raise (%r)" % (raised,)))
    cells.append((rec.stats.frame_errors == 1, "failure counted: frame_errors=%d" % rec.stats.frame_errors))
    cells.append((rec.last_frame_ns == ist_ns(DN, "09:30:00"),
                  "the liveness stamp survived the failed counting (last_frame_ns age %s s)"
                  % ((clock.now_ns() - (rec.last_frame_ns or 0)) / NS)))
    # ticks still flow after a failed on_message (they are a separate callback)
    before = rec.stats.packets["NIFTY"]
    at(clock, DN, "09:30:01")
    t.on_ticks(t, [idx_pkt("NIFTY", 25001.0, DN, "09:30:01")])
    cells.append((rec.stats.packets["NIFTY"] == before + 1, "on_ticks unaffected: NIFTY packets %d -> %d"
                  % (before, rec.stats.packets["NIFTY"])))
    # rate limit: 4 more failures inside the same minute add no log line; one 61 s later adds exactly one
    for s in (2, 3, 4, 5):
        at(clock, DN, "09:30:0%d" % s)
        t.on_message(t, _BadPayload(), True)
    n_same_minute = sum(1 for m in rec.lines if "FRAME_ERROR" in m)
    at(clock, DN, "09:31:01")
    t.on_message(t, _BadPayload(), True)
    n_later = sum(1 for m in rec.lines if "FRAME_ERROR" in m)
    cells.append((rec.stats.frame_errors == 6 and n_same_minute == 1 and n_later == 2,
                  "6 failures: counted %d; log lines after 5 in one minute=%d (want 1), after the 6th 61 s later=%d (want 2)"
                  % (rec.stats.frame_errors, n_same_minute, n_later)))
    # reported: heartbeat and daily report
    beat(t, clock)
    rec.step(at(clock, DN, "09:31:02"))
    hb = json.load(open(rec.heartbeat_path))
    daily = rec.daily_report(clock.now_ns())
    cells.append((hb.get("frame_errors") == 6 and daily.get("frame_errors") == 6,
                  "heartbeat frame_errors=%s, daily report frame_errors=%s (want 6, 6)" % (hb.get("frame_errors"), daily.get("frame_errors"))))
    # the handler of the handler cannot raise either: a log sink that raises
    rec2, clock2, t2 = boot_normal(DN)

    def bad_log(_m):
        raise OSError("log sink gone")
    rec2._log = bad_log
    raised2 = None
    try:
        at(clock2, DN, "09:30:00")
        t2.on_message(t2, _BadPayload(), True)
    except BaseException as exc:  # noqa: BLE001
        raised2 = exc
    cells.append((raised2 is None and rec2.stats.frame_errors == 1, "a raising log sink does not escape on_frame (%r)" % (raised2,)))
    # a healthy run reports zero
    rec3, clock3, t3 = boot_normal(DN)
    run_beats(rec3, t3, clock3, DN, "09:16:00", 30)
    cells.append((rec3.stats.frame_errors == 0 and rec3.frames_hb == 31, "healthy heartbeats: frame_errors=%d frames_hb=%d"
                  % (rec3.stats.frame_errors, rec3.frames_hb)))
    return cells


def g_normal_day():
    """Fails if special-session logic leaks into ordinary days, or the rehearsal's config overwrite stops working."""
    from services.tape_runner import session
    cells = []
    want = {"start": "08:50", "resolve": "08:55", "options": "09:00", "closed_check": "09:20",
            "session_start": "09:15", "session_end": "15:30", "stop": "15:40", "resolve_giveup": "09:10"}
    for day in ("2026-11-02", DN, "2026-11-09"):
        for cal in (CAL_PATH, os.path.join(tmpdir(), "absent.json")):
            config.SPECIAL_SESSIONS_PATH = cal
            w = session.window(day)
            cells.append(({k: w[k] for k in want} == want and w["special"] is False,
                          "%s (calendar %s): %s" % (day, "present" if cal == CAL_PATH else "absent", {k: w[k] for k in want})))
    config.SPECIAL_SESSIONS_PATH = CAL_PATH
    saved = (config.T_START, config.T_STOP)
    try:
        config.T_START, config.T_STOP = "10:11", "10:55"
        w = session.window(DN)
        cells.append((w["start"] == "10:11" and w["stop"] == "10:55", "config overwrite (rehearsal) still moves a normal day"))
        w = session.window(DS)
        cells.append((w["start"] == "13:55" and w["stop"] == "15:50", "...and does not move a special day"))
    finally:
        config.T_START, config.T_STOP = saved
    d = tmpdir()
    out = session.emit_timers(CAL, "2026-11-09", d)
    cells.append((out == [] and os.listdir(d) == [], "today 2026-11-09: past special date emits no timer"))
    out = session.emit_timers(CAL, "2026-11-08", d)
    cells.append((out == ["tape-runner-special-2026-11-08.timer"], "today 2026-11-08: the same-day timer is still emitted"))
    return cells


def _events(rec, sym="NIFTY"):
    out = {}
    seen = set()
    for _, r in T0.s3_records(rec.uploader.s3, sym + "/"):
        if r.get("k") == "ctl":
            key = (r["ctl"], r["recv_ns"])
            if key in seen:
                continue
            seen.add(key)
            out[r["ctl"]] = out.get(r["ctl"], 0) + 1
    return out


def g_counters():
    """Day-1 shape. Event log (scripted): 3 connects, 8 disconnects, 6 reconnect callbacks, then the
    shutdown close arrives after `stopping` (the 9th on_close). Fails if any report counter is defined
    differently from the event it names."""
    rec, clock, tk = make_rec(DN, "08:50")
    rec.step(clock.now_ns())
    rec.step(at(clock, DN, "08:55"))
    t = tk[0]
    t.on_connect(t, {})                                    # connect 1 (first)
    sec = [0]

    def tick():
        sec[0] += 1
        clock.set(ist_ns(DN, "10:00:00") + sec[0] * NS)

    script = (["close", "reconn", "close", "reconn", "reconn", "connect"]                       # -> connect 2
              + ["close", "close", "reconn", "close", "close", "reconn", "close", "close", "reconn", "connect"])  # -> connect 3
    for kind in script:
        tick()
        if kind == "close":
            t.on_close(t, 1006, "x")
        elif kind == "reconn":
            t.on_reconnect(t, sec[0])
        else:
            t.on_connect(t, {})
        t.on_message(t, b"\x00", True)
    tick()
    # the day-1 event log, as a belief: 3 connects, 8 disconnects, 6 reconnect callbacks
    n_close, n_recon = 8, 6
    cells = [(script.count("close") == n_close and script.count("reconn") == n_recon and script.count("connect") == 2,
              "the script itself has 8 closes, 6 retry callbacks, 2 connects after the first")]
    # stop: ticker.close() answers after stopping
    orig = rec._drain

    def drain(deadline):
        t.deliver_pending_close()
        return orig(deadline)
    rec._drain = drain
    clock.set(ist_ns(DN, "15:40"))
    code = rec.step(clock.now_ns())
    rep = json.loads(rec.uploader.s3.objects["session/%s/daily_report_%s.json" % (DN, DN)])
    ev = _events(rec)
    cells.append((code == 0, "stop exit code %s" % code))
    cells.append((ev.get("connect") == rep["connects"], "connects: log %s vs report %s" % (ev.get("connect"), rep["connects"])))
    cells.append((rep["reconnects"] == ev.get("connect", 0) - 1, "reconnects (= connects-1): report %s, log connects %s"
                  % (rep["reconnects"], ev.get("connect"))))
    cells.append((ev.get("disconnect") == rep["disconnects"], "disconnects: log %s vs report %s"
                  % (ev.get("disconnect"), rep["disconnects"])))
    cells.append((ev.get("reconnect") == rep["reconnect_attempts"], "reconnect callbacks: log %s vs report %s"
                  % (ev.get("reconnect"), rep["reconnect_attempts"])))
    cells.append((rep["close_at_stop"] == 1, "the shutdown close is counted apart: close_at_stop=%s" % rep.get("close_at_stop")))
    cells.append((rep["disconnects"] == n_close and ev.get("reconnect") == n_recon and rep["connects"] == 3,
                  "scripted totals: closes %d, retry callbacks %d, connects 3 (report %s/%s/%s)"
                  % (n_close, n_recon, rep["disconnects"], rep["reconnect_attempts"], rep["connects"])))
    return cells


class StubFactory:
    initialDelay = 99.0
    factor = 99.0
    maxDelay = 99.0
    jitter = 99.0


class StubBase:
    """stands in for kiteconnect.KiteTicker: connect() creates the factory, as the real one does."""
    def __init__(self, *a, **k):
        self.factory = None

    def connect(self, threaded=False, **kw):
        self.factory = StubFactory()
        self.factory.ws = StubWs()


class StubWs:
    def __init__(self):
        self.dropped = None

    def dropConnection(self, abort=False):
        self.dropped = abort


def g_glue():
    """Fails if the production ticker wrapper does not tune the factory, or drops from the wrong thread."""
    from services.tape_runner import ticker_glue
    calls = []

    def call_from_thread(fn, *a, **k):
        calls.append(fn)
        return fn(*a, **k)
    cls = ticker_glue.make_watched_ticker_class(StubBase, call_from_thread)
    t = cls()
    t.connect(threaded=True)
    f = t.factory
    cells = [((f.initialDelay, f.factor, f.maxDelay, f.jitter) == (1.0, 2.0, 15, 0),
              "factory tuned after connect(): %s" % ((f.initialDelay, f.factor, f.maxDelay, f.jitter),))]
    t.force_reconnect()
    cells.append((len(calls) == 1 and f.ws.dropped is True, "force_reconnect went through callFromThread, abort=True (%s, %s)"
                  % (len(calls), f.ws.dropped)))
    return cells


def g_processor_special():
    """Fails if the offline processor mis-handles a special-session day, changes a normal day, or its counter
    reconciliation cannot see a mismatch."""
    import gen_day
    from services.tape_offline import process_day
    from merdian_compute.tape import replay
    cells = []
    # A. Muhurat-shaped day: 14:15-14:30 packets, open 14:20 (pre-open packets exist and must stay out of the total)
    config.SPECIAL_SESSIONS_PATH = CAL_PATH
    spec = gen_day.Spec(day=DS, t_start="14:15:00", t_end="14:29:59", events=False)
    root = tmpdir()
    truth = gen_day.build_day(root, spec)
    out = os.path.join(tmpdir(), "o")
    rc = process_day.main([root, "--day", DS, "--out", out, "--calendar", CAL_PATH])
    rep = json.load(open(os.path.join(out, "g3_report.json")))
    txt = open(os.path.join(out, "g3_report.txt")).read()
    exp_cls = exp_tot = 0
    for (tok, mm), row in truth.minute.items():
        if truth.tok_sym.get(tok) == "NIFTY" and truth.tok_group.get(tok) != "FUT" and mm >= "14:20":
            exp_cls += row["B"] + row["S"]
            exp_tot += row["B"] + row["S"] + row["U"]
    nif = rep["symbols"]["NIFTY"]
    share = nif["verdict_detail"].get("overall", {}).get("share_pct")
    want = round(100.0 * exp_cls / exp_tot, 6) if exp_tot else None
    cells.append((rc == 0, "special day (calendar close 15:40, the F&O close): exit code %s" % rc))
    out_bad = os.path.join(tmpdir(), "o_bad")
    cal_bad = write_cal([dict(CAL[0], close="15:41")], "cal_1541.json")
    rc_bad = process_day.main([root, "--day", DS, "--out", out_bad, "--calendar", cal_bad])
    cells.append((rc_bad == 2, "a special close after 15:40 is refused (15:41 -> exit %s)" % rc_bad))
    from merdian_compute.tape import minute as M
    win = ("14:20", "15:40")
    bk = {hm: M.bucket_of(hm, win) for hm in ("14:19", "14:20", "15:00", "15:29", "15:30", "15:35", "15:39", "15:40")}
    want_bk = {"14:19": "pre_0915", "14:20": "1400_1500", "15:00": "1500_1530", "15:29": "1500_1530",
               "15:30": "1500_1530", "15:35": "1500_1530", "15:39": "1500_1530", "15:40": "post_1530"}
    cells.append((bk == want_bk, "special window 14:20-15:40: minutes 15:30-15:39 are in-session, 15:40 is after: %s" % bk))
    cells.append((M.bucket_of("15:30") == "post_1530" and M.bucket_of("15:35") == "post_1530"
                  and M.bucket_of("15:29") == "1500_1530",
                  "a normal day is unchanged: 15:29 -> 1500_1530, 15:30 and 15:35 -> post_1530"))
    cells.append((nif["verdict"] == "NOT EVALUATED (special session)", "verdict %r" % nif["verdict"]))
    cells.append((exp_tot > 0 and share is not None and abs(share - want) < 1e-5,
                  "one overall share %s (independent expectation %s over minutes >= 14:20)" % (share, want)))
    cells.append((rep.get("session", {}).get("kind") == "special" and rep["session"].get("open") == "14:20",
                  "report carries the session window: %s" % rep.get("session")))
    cells.append(("NOT EVALUATED (special session)" in txt, "text report shows the verdict"))
    cells.append((nif["hours"].get("pre_0915") and not any(k in nif["hours"] for k in ("0915_1000", "1000_1100")),
                  "packets before 14:20 land in the pre-open bucket (hours: %s)" % sorted(nif["hours"])))
    # B. a normal day is byte-identical with the calendar present and absent
    spec = gen_day.Spec(events=True)
    root = tmpdir()
    gen_day.build_day(root, spec)
    outs = {}
    for label, cal in (("present", CAL_PATH), ("absent", os.path.join(tmpdir(), "absent.json"))):
        o = os.path.join(tmpdir(), "o_" + label)
        rc2 = process_day.main([root, "--day", spec.day, "--out", o, "--calendar", cal])
        outs[label] = (rc2, {n: open(os.path.join(o, n), "rb").read() for n in
                             ("tape_minute.csv", "g3_report.json", "g3_report.txt")})
    cells.append((outs["present"] == outs["absent"] and outs["present"][0] == 0,
                  "normal day: csv, json, txt byte-identical with the calendar present and absent"))
    # B2. parity: the processor's calendar reader and the recorder's session.window agree (a test, not a comment)
    from merdian_compute.tape import special
    from services.tape_runner import session
    par = []
    for day in ("2026-11-02", DN, DS, "2026-11-09"):
        config.SPECIAL_SESSIONS_PATH = CAL_PATH
        sw, rw = special.special_window(day, CAL_PATH), session.window(day)
        par.append((day, (sw["open"], sw["close"], sw["label"]) if sw else None,
                    (rw["session_start"], rw["session_end"], rw["label"]) if rw["special"] else None))
    cells.append((all(a == b for _, a, b in par), "processor reader == recorder window on 4 dates: %s" % par))
    # C. ctl 'watchdog' is accepted, counted as a ctl line, and is not a gap event
    meta = {1: {"sym": "NIFTY", "role": "IDX", "token": 1}}
    sr = replay.SymbolReplay("NIFTY", DN, meta)
    before = len(sr.events)
    line = json.dumps({"k": "ctl", "ctl": "watchdog", "recv_ns": ist_ns(DN, "10:00:00"),
                       "recv_ist": "2026-11-03T10:00:00+05:30", "age_s": 15})
    sr.feed(line)
    cells.append((sr.c["ctl_lines"] == 1 and len(sr.events) == before and sr.c["bad_lines"] == 0,
                  "watchdog ctl line: ctl_lines=%d gap events unchanged=%s bad=%d"
                  % (sr.c["ctl_lines"], len(sr.events) == before, sr.c["bad_lines"])))
    # D. reconciliation: gen_day's events=True log has 2 connects, 1 disconnect, 1 reconnect; its daily report
    #    says reconnects 1 (= connects-1) and disconnects 1 -> OK. Break the report -> MISMATCH is flagged.
    config.SPECIAL_SESSIONS_PATH = CAL_PATH
    o = os.path.join(tmpdir(), "o_rec")
    process_day.main([root, "--day", spec.day, "--out", o, "--calendar", CAL_PATH])
    r1 = json.load(open(os.path.join(o, "g3_report.json")))
    ce = r1["symbols"]["NIFTY"].get("ctl_events")
    cells.append((ce == {"connect": 2, "disconnect": 1, "reconnect": 1, "watchdog": 0} and
                  r1.get("reconcile", {}).get("ok") is True,
                  "reconciliation OK on a consistent day: ctl_events=%s reconcile=%s" % (ce, r1.get("reconcile"))))
    rp = os.path.join(root, "session", spec.day, "daily_report_%s.json" % spec.day)
    d = json.load(open(rp))
    d["disconnects"] = 9
    json.dump(d, open(rp, "w"))
    o2 = os.path.join(tmpdir(), "o_rec2")
    process_day.main([root, "--day", spec.day, "--out", o2, "--calendar", CAL_PATH])
    r2 = json.load(open(os.path.join(o2, "g3_report.json")))
    t2 = open(os.path.join(o2, "g3_report.txt")).read()
    cells.append((r2.get("reconcile", {}).get("ok") is False and "MISMATCH" in t2 and "disconnects" in t2,
                  "report disconnects=9 vs log 1 -> MISMATCH flagged: %s" % r2.get("reconcile")))
    return cells


def _fake_systemctl(d):
    p = os.path.join(d, "systemctl")
    log = os.path.join(d, "systemctl.log")
    with open(p, "w") as fh:
        fh.write("#!/bin/sh\necho \"$@\" >> %s\n" % log)
    os.chmod(p, 0o755)
    return p, log


def _sync(unit_dir, cal, today, systemctl):
    sh = os.path.join(ROOT, "services", "tape_runner", "sync_special_timers.sh")
    env = dict(os.environ, UNIT_DIR=unit_dir, CALENDAR=cal, TODAY=today, SYSTEMCTL=systemctl,
               SESSION_PY=os.path.join(ROOT, "services", "tape_runner", "session.py"), PYBIN=sys.executable)
    return subprocess.run(["bash", sh], env=env, capture_output=True, text=True)


def g_timer_sync():
    """Fails if stale special timers survive, a future one is not written, the weekday timer is touched,
    or the install guard has a hole on a Sunday."""
    cells = []
    d = tmpdir()
    ud = os.path.join(d, "units")
    os.makedirs(ud)
    for n in ("tape-runner.timer", "tape-runner.service", "tape-runner-special-2026-10-31.timer",
              "tape-runner-special-2026-12-01.timer"):
        open(os.path.join(ud, n), "w").write("old " + n)
    sc, log = _fake_systemctl(d)
    p = _sync(ud, CAL_PATH, "2026-11-03", sc)
    files = sorted(os.listdir(ud))
    calls = open(log).read().splitlines() if os.path.exists(log) else []
    cells.append((p.returncode == 0, "sync exit %s %s" % (p.returncode, p.stderr.strip()[-200:])))
    cells.append((files == ["tape-runner-special-2026-11-08.timer", "tape-runner.service", "tape-runner.timer"],
                  "unit dir after sync: %s" % files))
    cells.append((open(os.path.join(ud, "tape-runner-special-2026-11-08.timer")).read() == TIMER_TEXT,
                  "installed timer text equals the literal"))
    cells.append((any(c.startswith("disable --now tape-runner-special-2026-10-31.timer") for c in calls)
                  and any(c.startswith("disable --now tape-runner-special-2026-12-01.timer") for c in calls)
                  and any(c.startswith("enable --now tape-runner-special-2026-11-08.timer") for c in calls)
                  and not any("tape-runner.timer" in c.replace("special", "") and "disable" in c for c in calls),
                  "systemctl calls: %s" % calls))
    cells.append((open(os.path.join(ud, "tape-runner.timer")).read() == "old tape-runner.timer", "weekday timer untouched"))
    p = _sync(ud, CAL_PATH, "2026-11-09", sc)
    cells.append((sorted(os.listdir(ud)) == ["tape-runner.service", "tape-runner.timer"],
                  "after the date: special timer removed: %s" % sorted(os.listdir(ud))))
    # the guard (exit 0 = inside a special-session window, install must refuse)
    py = os.path.join(ROOT, "services", "tape_runner", "session.py")

    def inside(date, hhmm):
        return subprocess.run([sys.executable, "-I", py, "--calendar", CAL_PATH, "--in-window", date, hhmm],
                              capture_output=True, text=True).returncode == 0
    # window = [open - 60 min, close + 30 min) = [13:20, 16:10) for open 14:20, close 15:40
    probes = {("2026-11-08", "13:19"): False, ("2026-11-08", "13:20"): True, ("2026-11-08", "15:59"): True,
              ("2026-11-08", "16:00"): True, ("2026-11-08", "16:09"): True, ("2026-11-08", "16:10"): False,
              ("2026-11-03", "14:00"): False, ("2026-11-07", "14:30"): False}
    got = {k: inside(*k) for k in probes}
    cells.append((got == probes, "install guard on a special date: %s" % {"%s %s" % k: v for k, v in got.items()}))
    from services.tape_runner import session as S
    rcs = {k: subprocess.run([sys.executable, "-I", py, "--calendar", CAL_PATH, "--in-window", *k],
                             capture_output=True, text=True).returncode for k in (("2026-11-08", "1400"), ("2026-11-03", "1400"))}
    cells.append((S.EXIT_OUTSIDE not in (0, 1, 2) and rcs == {("2026-11-08", "1400"): 0, ("2026-11-03", "1400"): S.EXIT_OUTSIDE},
                  "guard exit codes: inside -> 0, outside -> EXIT_OUTSIDE=%s (not 0, 1 or 2): %s" % (S.EXIT_OUTSIDE, list(rcs.values()))))
    badcal = os.path.join(tmpdir(), "bad.json")
    open(badcal, "w").write("{not json")
    rc_bad = subprocess.run([sys.executable, "-I", py, "--calendar", badcal, "--in-window", "2026-11-08", "1400"],
                            capture_output=True, text=True).returncode
    cells.append((rc_bad == 2, "guard on a malformed calendar exits 2 (could not evaluate), not 1 (outside): %s" % rc_bad))
    inst = open(os.path.join(ROOT, "services", "tape_runner", "install.sh")).read()
    cells.append(("sync_special_timers.sh" in inst and "--in-window" in inst,
                  "install.sh calls the sync script and the window guard"))
    m_out = re.search(r"^OUTSIDE_RC=(\d+)$", inst, re.M)
    cells.append((m_out is not None and int(m_out.group(1)) == S.EXIT_OUTSIDE,
                  "install.sh OUTSIDE_RC (%s) equals session.EXIT_OUTSIDE (%s)" % (m_out and m_out.group(1), S.EXIT_OUTSIDE)))
    # Run install.sh's own guard block, against a real session.py and against one that exits 1 on import:
    # only "outside" may proceed; "inside", "could not evaluate" and a SyntaxError (exit 1) must all refuse.
    blk = re.search(r"^OUTSIDE_RC=.*?^esac\n", inst, re.M | re.S)

    def run_guard_block(session_src, date, hhmm, cal_src=None):
        h = tmpdir()
        open(os.path.join(h, "session.py"), "w", encoding="utf-8").write(session_src)
        shutil.copy(CAL_PATH, os.path.join(h, "special_sessions.json"))
        if cal_src is not None:
            open(os.path.join(h, "special_sessions.json"), "w").write(cal_src)
        script = ('die() { echo "REFUSED: $*"; exit 2; }\nset -e\nHERE="%s"\nVENV_PY="%s"\nIST_DATE="%s"\nIST_HHMM="%s"\n%s\necho PROCEED\n'
                  % (h, sys.executable, date, hhmm, blk.group(0) if blk else "exit 99"))
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        return "PROCEED" if "PROCEED" in r.stdout else ("REFUSED" if "REFUSED" in r.stdout else "?%s" % r.returncode)
    real_src = open(os.path.join(ROOT, "services", "tape_runner", "session.py"), encoding="utf-8").read()
    broken_src = real_src + "\ndef broken(:\n"
    exits_1 = os.path.join(tmpdir(), "s.py")
    open(exits_1, "w", encoding="utf-8").write(broken_src)
    rc_syntax = subprocess.run([sys.executable, "-I", exits_1, "--in-window", "2026-11-03", "1400"],
                               capture_output=True).returncode
    g = {"outside (Tue 14:00)": run_guard_block(real_src, "2026-11-03", "1400"),
         "inside (Sun 14:30)": run_guard_block(real_src, "2026-11-08", "1430"),
         "SyntaxError in session.py": run_guard_block(broken_src, "2026-11-03", "1400"),
         "malformed calendar": run_guard_block(real_src, "2026-11-03", "1400", cal_src="{not json")}
    cells.append((g == {"outside (Tue 14:00)": "PROCEED", "inside (Sun 14:30)": "REFUSED",
                        "SyntaxError in session.py": "REFUSED", "malformed calendar": "REFUSED"} and rc_syntax == 1,
                  "install.sh guard block (a broken session.py itself exits %s, i.e. 1): %s" % (rc_syntax, g)))
    cells.append(('0) die "special session window' in inst and '*) die "could not evaluate the special-session guard' in inst
                  and inst.index("--in-window") > inst.index('[ -x "$VENV_PY" ]'),
                  "install.sh: guard runs after the venv check and fails closed on any exit other than 0 / OUTSIDE_RC"))
    return cells


# ======================================================================== unit checks
def u_calendar_file():
    from services.tape_runner import session
    p = os.path.join(ROOT, "services", "tape_runner", "special_sessions.json")
    cells = [(json.load(open(p)) == CAL, "checked-in calendar is exactly the NSE/FAOP/76940 Muhurat entry")]
    for bad, why in (([{"date": "2026-11-08", "open": "15:30", "close": "14:20", "label": "x"}], "open >= close"),
                     ([{"date": "08-11-2026", "open": "14:20", "close": "15:30", "label": "x"}], "bad date"),
                     ([{"date": "2026-11-08", "open": "14:20", "close": "15:30", "label": "x"}] * 2, "duplicate date"),
                     ([{"date": "2026-11-08", "open": "25:20", "close": "26:30", "label": "x"}], "bad time")):
        try:
            session.validate(bad)
            cells.append((False, "validate accepted: " + why))
        except ValueError:
            cells.append((True, "validate rejects: " + why))
    return cells


def u_calendar_failsoft():
    """A malformed or missing calendar must not stop a weekday: defaults, with a loud log line."""
    from services.tape_runner import session
    cells = []
    for label, path in (("malformed", None), ("missing", os.path.join(tmpdir(), "nope.json"))):
        if path is None:
            path = os.path.join(tmpdir(), "bad.json")
            open(path, "w").write("{not json")
        config.SPECIAL_SESSIONS_PATH = path
        logged = []
        w = session.window(DN, log=logged.append)
        cells.append((w["start"] == "08:50" and w["special"] is False and (label == "missing" or any("SESSION_CALENDAR" in m for m in logged)),
                      "%s calendar -> defaults%s" % (label, "" if label == "missing" else ", logged")))
    config.SPECIAL_SESSIONS_PATH = CAL_PATH
    return cells


GUARDS = [("wd-trip", g_wd_trip), ("wd-window", g_wd_window), ("wd-backoff", g_wd_backoff),
          ("special-day", g_special_day), ("fo-close", g_fo_close), ("frame-errors", g_frame_errors),
          ("normal-day", g_normal_day), ("counters", g_counters), ("glue", g_glue),
          ("processor-special", g_processor_special), ("timer-sync", g_timer_sync)]
UNITS = [u_calendar_file, u_calendar_failsoft]


def main():
    results = []
    for name, fn in [(n, f) for n, f in GUARDS if ARGS.only in (None, n)]:
        try:
            cells = fn()
            ok = bool(cells) and all(c[0] for c in cells)
        except Exception:
            cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            ok = False
        results.append((name, ok))
        print("%s %s" % ("PASS" if ok else "FAIL", name))
        for c in cells:
            print("    [%s] %s" % ("ok" if c[0] else "XX", c[1]))
    unit_ok = unit_n = 0
    if ARGS.only is None:
        for fn in UNITS:
            try:
                cells = fn()
            except Exception:
                cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            for c in cells:
                unit_n += 1
                unit_ok += bool(c[0])
                print("    unit %s [%s] %s" % (fn.__name__, "ok" if c[0] else "XX", c[1]))
    for d in T0.TMP:
        shutil.rmtree(d, ignore_errors=True)
    g_ok = sum(1 for _, ok in results if ok)
    passed = bool(results) and g_ok == len(results) and unit_ok == unit_n
    print("TAPE T0.1 %s (%d/%d guards, %d/%d unit checks)" % ("PASS" if passed else "FAIL", g_ok, len(results),
                                                          unit_ok, unit_n))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
