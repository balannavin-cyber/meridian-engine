"""Session window: the default weekday timeline, overridden on dates listed in special_sessions.json.

Everything the recorder schedules by wall time comes from ``window(day)``. On an ordinary day it is
``config.T_*`` read AT CALL TIME (so the rehearsal driver's overwrite of those constants still moves the
timeline). On a special day it is derived from the calendar's ``open`` / ``close`` with the SAME offsets the
ordinary day has (start open-25 min, resolve -20, options -15, closed-day check +5, stop close+10, resolve
give-up resolve+15). All times are IST ``HH:MM``.

Stdlib only; also runs as a script (``python -I session.py ...``) for install.sh:
  --emit-timers OUTDIR --today YYYY-MM-DD     write one systemd timer per special date >= today
  --in-window YYYY-MM-DD HHMM                 exit 0 when inside [open-60 min, close+30 min) of a special date
"""
import argparse
import json
import os
import sys
from datetime import datetime

OFF_START, OFF_RESOLVE, OFF_OPTIONS, OFF_CLOSED = -25, -20, -15, 5     # minutes from open
OFF_STOP, OFF_GIVEUP = 10, 15                                          # minutes from close / from resolve
GUARD_BEFORE, GUARD_AFTER = 60, 30                                     # install guard, minutes
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(_HERE, "special_sessions.json")


def _mins(hm):
    if not isinstance(hm, str) or len(hm) != 5 or hm[2] != ":" or not (hm[:2] + hm[3:]).isdigit():
        raise ValueError("bad time %r (want HH:MM)" % (hm,))
    h, m = int(hm[:2]), int(hm[3:])
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError("bad time %r" % (hm,))
    return h * 60 + m


def _hm(minutes):
    if not 0 <= minutes < 24 * 60:
        raise ValueError("derived time %d min leaves the day" % minutes)
    return "%02d:%02d" % divmod(minutes, 60)


def validate(entries):
    if not isinstance(entries, list):
        raise ValueError("calendar must be a list")
    seen = set()
    for e in entries:
        if not isinstance(e, dict) or not all(k in e for k in ("date", "open", "close", "label")):
            raise ValueError("entry needs date, open, close, label: %r" % (e,))
        d = e["date"]
        if not isinstance(d, str) or len(d) != 10:
            raise ValueError("bad date %r" % (d,))
        datetime.strptime(d, "%Y-%m-%d")
        if d in seen:
            raise ValueError("duplicate date %s" % d)
        seen.add(d)
        o, c = _mins(e["open"]), _mins(e["close"])
        if not o < c:
            raise ValueError("%s: open %s must be before close %s" % (d, e["open"], e["close"]))
        _hm(o + OFF_START)
        _hm(c + OFF_STOP)
    return entries


def load(path=None):
    with open(path or DEFAULT_PATH, encoding="utf-8") as fh:
        return validate(json.load(fh))


def derive(entry):
    o, c = _mins(entry["open"]), _mins(entry["close"])
    resolve = o + OFF_RESOLVE
    return {"start": _hm(o + OFF_START), "resolve": _hm(resolve), "options": _hm(o + OFF_OPTIONS),
            "closed_check": _hm(o + OFF_CLOSED), "session_start": entry["open"], "session_end": entry["close"],
            "stop": _hm(c + OFF_STOP), "resolve_giveup": _hm(resolve + OFF_GIVEUP),
            "special": True, "label": entry["label"]}


def window(day, path=None, log=None):
    """The timeline for IST date ``day``. A missing calendar is the ordinary day; an unreadable or invalid
    one is the ordinary day too, with a loud log line -- the weekday recorder must not depend on this file."""
    from . import config
    w = {"start": config.T_START, "resolve": config.T_RESOLVE, "options": config.T_OPTIONS,
         "closed_check": config.T_CLOSED_CHECK, "session_start": config.T_SESSION_START,
         "session_end": config.T_SESSION_END, "stop": config.T_STOP, "resolve_giveup": config.T_RESOLVE_GIVEUP,
         "special": False, "label": None}
    try:
        entries = load(path or config.SPECIAL_SESSIONS_PATH)
    except FileNotFoundError:
        return w
    except Exception as exc:  # noqa: BLE001
        if log:
            log("SESSION_CALENDAR_ERROR %s -- using the default window" % type(exc).__name__)
        return w
    for e in entries:
        if e["date"] == day:
            return derive(e)
    return w


def render_timer(entry):
    d = derive(entry)
    name = "tape-runner-special-%s.timer" % entry["date"]
    return (
        "# /etc/systemd/system/%s  (generated from special_sessions.json; %s)\n"
        "[Unit]\n"
        "Description=MERIDIAN tape raw recorder (T0) -- special session %s (%s), start %s IST\n"
        "\n"
        "[Timer]\n"
        "OnCalendar=%s %s:00 Asia/Kolkata\n"
        "Persistent=false\n"
        "AccuracySec=1s\n"
        "Unit=tape-runner.service\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n" % (name, entry["label"], entry["date"], entry["label"], d["start"],
                                      entry["date"], d["start"]))


def emit_timers(entries, today, outdir):
    """Write a timer for every special date >= today (IST). Returns the file names, sorted."""
    names = []
    for e in sorted(entries, key=lambda x: x["date"]):
        if e["date"] >= today:
            name = "tape-runner-special-%s.timer" % e["date"]
            with open(os.path.join(outdir, name), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(render_timer(e))
            names.append(name)
    return names


def in_window(entries, date, hhmm):
    t = _mins(hhmm[:2] + ":" + hhmm[2:]) if ":" not in hhmm else _mins(hhmm)
    for e in entries:
        if e["date"] == date and _mins(e["open"]) - GUARD_BEFORE <= t < _mins(e["close"]) + GUARD_AFTER:
            return True
    return False


def _main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--calendar", default=DEFAULT_PATH)
    ap.add_argument("--emit-timers")
    ap.add_argument("--today")
    ap.add_argument("--in-window", nargs=2, metavar=("DATE", "HHMM"))
    a = ap.parse_args(argv)
    entries = load(a.calendar)
    if a.emit_timers:
        if not a.today:
            ap.error("--emit-timers needs --today")
        for n in emit_timers(entries, a.today, a.emit_timers):
            print(n)
        return 0
    if a.in_window:
        return 0 if in_window(entries, *a.in_window) else 1
    ap.error("nothing to do")


def _guarded_main(argv):
    """exit 0 / 1 are answers (inside / outside); 2 means 'could not evaluate' so a caller can fail closed."""
    try:
        return _main(argv)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print("session.py: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_guarded_main(sys.argv[1:]))
