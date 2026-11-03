"""Special-session lookup for the OFFLINE processor (tape T0.1). Stdlib only; reads the same
services/tape_runner/special_sessions.json the recorder reads, but shares no code with it: the T1a isolation
guard forbids the processor importing the runner, and the runner is installed without merdian_compute.
Parity with the recorder's session.window() is asserted by tests/test_tape_t0_1.py (guard processor-special),
not by this comment.
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PATH = os.path.join(_ROOT, "services", "tape_runner", "special_sessions.json")


def special_window(day, path=None):
    """{"label", "open", "close"} when ``day`` is a special session, else None. A missing file is None;
    a malformed file raises ValueError (the processor reports it and exits 2 rather than guess)."""
    try:
        with open(path or DEFAULT_PATH, encoding="utf-8") as fh:
            entries = json.load(fh)
    except FileNotFoundError:
        return None
    except ValueError as exc:
        raise ValueError("unreadable special_sessions.json: %s" % exc)
    if not isinstance(entries, list):
        raise ValueError("special_sessions.json must be a list")
    for e in entries:
        if isinstance(e, dict) and e.get("date") == day:
            if not all(isinstance(e.get(k), str) for k in ("open", "close", "label")):
                raise ValueError("special session %s needs open, close, label" % day)
            return {"label": e["label"], "open": e["open"], "close": e["close"]}
    return None
