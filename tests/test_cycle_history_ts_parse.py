#!/usr/bin/env python3
"""AM-2 / S91 — the ENH-133 pair's _ist_date must parse every fraction width PostgREST
emits. Covers BOTH modules that carry the function:

    write_gex_cycle_history_local.py          (the writer)
    reconcile_gex_cycle_history_session_local.py  (the reconciler)

Both are scheduled, both read the same timestamps, and their _ist_date bodies were
byte-identical, so a test that covered only one would have left the other crashing on
the same strings. Every case below runs against both.

THE DEFECT THIS TEST EXISTS TO CATCH (logs/orchestrator.log, cycles 09:05-09:25 IST
2026-10-07):

    write_gex_cycle_history_local.py:87 in _ist_date
    ValueError: Invalid isoformat string '2026-10-07T03:30:07.61356+00:00'

PostgREST trims trailing zeros from the microsecond fraction, so a timestamp whose
microseconds end in 0 arrives with 1, 2, 4 or 5 digits. Python 3.10's
datetime.fromisoformat accepts a fraction of EXACTLY 3 or 6 digits, or NO fraction at
all, and raises on every other width; 3.11+ is permissive. The box is 3.10, so ~1 cycle
in 10 dies and that cycle's row is unrecoverable (ADR-030 D2: the table accumulates
forward and is never backfilled).

WHAT WOULD MAKE THIS TEST FAIL (Rule 0, stated before the assertions):
  * a fraction width that fromisoformat rejects -> ValueError, caught and reported;
  * a parse that succeeds but yields the WRONG IST date -> the rollover cases fail.
    Without those this file would pass on a function that ignored the timezone
    entirely, which is the TD-029 mistake in the opposite direction.
Against an unfixed module the widths that fail are exactly [1, 2, 4, 5] -- 0, 3 and 6
parse because bare fromisoformat already accepts them. That asymmetry is the defect's
signature and is asserted per module, so "fixed" and "happens not to have been hit"
cannot be confused.

Offline: no database, no network. The two env vars are set to syntactically valid
dummies BEFORE the imports so each module's module-level _load_env() passes without
reading a real credential; load_dotenv() does not override an existing variable, and
nothing here prints an environment value (Rule 19).
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SUPABASE_URL", "https://offline.invalid")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "offline-dummy-not-a-credential")

import reconcile_gex_cycle_history_session_local as R  # noqa: E402
import write_gex_cycle_history_local as W  # noqa: E402

MODULES = [("writer", W), ("reconciler", R)]

fails = 0


def check(name, got, want):
    global fails
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {name}  got {got!r} want {want!r}")
    fails += 0 if ok else 1
    return ok


def parse(mod, ts):
    """<mod>._ist_date, with a raised ValueError turned into the string 'ValueError' so
    one bad width reports as a failed cell instead of aborting the file."""
    try:
        return mod._ist_date(ts)
    except ValueError:
        return "ValueError"


D = date(2026, 10, 7)

# ---- fraction widths 0..6, the +00:00 offset form -------------------------------
# 03:30:07 UTC = 09:00:07 IST, same calendar day.
WIDTHS = {
    0: "2026-10-07T03:30:07+00:00",
    1: "2026-10-07T03:30:07.6+00:00",
    2: "2026-10-07T03:30:07.61+00:00",
    3: "2026-10-07T03:30:07.613+00:00",
    4: "2026-10-07T03:30:07.6135+00:00",
    5: "2026-10-07T03:30:07.61356+00:00",
    6: "2026-10-07T03:30:07.613560+00:00",
}
LOG_TS = "2026-10-07T03:30:07.61356+00:00"

width_ok = {}
for label, mod in MODULES:
    print(f"--- {label}: {mod.__name__} ---")
    width_ok[label] = {}
    # fraction widths, +00:00 form
    for n, ts in sorted(WIDTHS.items()):
        width_ok[label][n] = check(f"{label}: fraction {n} digit(s), +00:00  {ts}",
                                   parse(mod, ts), D)
    # the same widths with a 'Z' suffix
    for n, ts in sorted(WIDTHS.items()):
        check(f"{label}: fraction {n} digit(s), Z suffix", parse(mod, ts.replace("+00:00", "Z")), D)
    # the EXACT string from the log
    check(f"{label}: the exact string from logs/orchestrator.log  {LOG_TS}", parse(mod, LOG_TS), D)
    # the timezone must actually be applied. 2026-10-06 19:00 UTC is 2026-10-07 00:30 IST;
    # a function that dropped the offset, or used replace(tzinfo=None), would return
    # 2026-10-06 here and pass everything above.
    check(f"{label}: IST rollover 2026-10-06T19:00:00.5+00:00 -> 2026-10-07",
          parse(mod, "2026-10-06T19:00:00.5+00:00"), date(2026, 10, 7))
    check(f"{label}: IST rollover 6-digit control 2026-10-06T19:00:00.500000+00:00",
          parse(mod, "2026-10-06T19:00:00.500000+00:00"), date(2026, 10, 7))
    # and the other side of the boundary, so the rollover case is not one-directional
    check(f"{label}: IST no-rollover 2026-10-06T18:00:00.500000+00:00 -> 2026-10-06",
          parse(mod, "2026-10-06T18:00:00.500000+00:00"), date(2026, 10, 6))
    print()

# ---- the defect's signature, asserted PER MODULE --------------------------------
print("fraction widths that FAILED on the +00:00 form, per module:")
for label, _ in MODULES:
    bad = sorted(n for n, ok in width_ok[label].items() if not ok)
    if bad == [1, 2, 4, 5]:
        shape = "PRE-FIX signature (only 0-, 3- and 6-digit fractions parse)"
    elif not bad:
        shape = "POST-FIX (every width 0-6 parses)"
    else:
        shape = "UNEXPECTED SHAPE -- neither the pre-fix signature nor a clean pass"
    print(f"  {label:11s} {bad}  -> {shape}")

print(f"\nTS PARSE {'ALL PASS' if fails == 0 else f'{fails} FAIL'}")
sys.exit(1 if fails else 0)
