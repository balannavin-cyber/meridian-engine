#!/usr/bin/env python3
"""AM-2 / S91 — build_market_spot_session_markers.parse_ts must parse every microsecond
fraction width PostgREST emits.

TD-S91-NEW-2 site 2. Sibling of tests/test_cycle_history_ts_parse.py (TD-S91-NEW-1),
which covers the ENH-133 pair; this file covers the marker writer, which carries the
SAME defect in a function with DIFFERENT failure semantics -- parse_ts swallows the
ValueError and returns None, so the symptom is not a traceback but a clean exit:

    latest_trade_date_from_spot()
      -> parse_ts(rows[0]["ts"]) is None
      -> fail("Could not parse latest ts from market_spot_snapshots")
      -> sys.exit(1)

which is why 2026-10-05 and 2026-10-06 have no market_spot_session_markers rows at all.
A None is a quieter failure than a crash, so this file asserts the returned INSTANT, not
merely that something came back.

THE DEFECT
PostgREST trims trailing zeros from the microsecond fraction, so a timestamp whose
microseconds end in 0 arrives with 1, 2, 4 or 5 digits. Python 3.10's
datetime.fromisoformat accepts a fraction of EXACTLY 3 or 6 digits, or none at all, and
raises ValueError on every other width; 3.11+ is permissive. The box is 3.10.12 (measured
2026-10-07).

WHAT WOULD MAKE THIS TEST FAIL (Rule 0, stated before the assertions)
  * a fraction width fromisoformat rejects -> parse_ts returns None -> the width cell
    fails. Against the unpatched module the failing widths are exactly [1, 2, 4, 5];
    0, 3 and 6 pass because bare fromisoformat already accepts them. That asymmetry is
    the defect's signature, and it is asserted, so "fixed" cannot be confused with
    "happened not to be hit".
  * a fix that STRIPS the fraction instead of PADDING it -> '.6' parses, but as 0 us
    instead of 600000 us. Every width case below asserts the exact microsecond value, so
    a strip-based fix fails here. Without that, this file would pass on a function that
    threw away sub-second precision.
  * a fix that loses the timezone -> the two rollover cases fail. 2026-10-06T19:00Z is
    2026-10-07 00:30 IST; a parse_ts whose result was later read with
    replace(tzinfo=None) (the TD-029 mistake, wrong for THIS table) would return
    2026-10-06 and pass everything else.
  * a fix that widens the except into a bare pass-through -> the malformed-input cases
    fail. parse_ts must still return None for genuinely bad input; that path is load
    bearing (callers test for None).

The pre-fix body is carried below as _parse_ts_PRE_S91, copied verbatim from
build_market_spot_session_markers.py_PRE_S91, and the signature is asserted against it.
That is not a substitute for running this file against the unpatched module -- which was
done, and failed, before the patch was applied -- it is what keeps the signature checkable
after the patch exists.

Offline: no database, no network. The two env vars are set to syntactically valid dummies
BEFORE the import because the module calls load_supabase() at module level; load_dotenv()
does not override an existing variable, and nothing here prints an environment value
(Rule 19).
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SUPABASE_URL", "https://offline.invalid")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "offline-dummy-not-a-credential")

import build_market_spot_session_markers as M  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

fails = 0


def check(name, got, want):
    global fails
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {name}  got {got!r} want {want!r}")
    fails += 0 if ok else 1
    return ok


def _parse_ts_PRE_S91(value):
    """The pre-fix body, verbatim from build_market_spot_session_markers.py_PRE_S91:33.

        def parse_ts(value: str | None) -> datetime | None:
            if not value:
                return None
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None

    Kept so the defect's signature stays checkable on whatever interpreter runs this
    file. It pins 3.10's fromisoformat behaviour, not my description of it.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


# ---- fraction widths 0..6, the +00:00 offset form -------------------------------
# 03:30:07 UTC = 09:00:07 IST, same calendar day. The microsecond value is asserted,
# not just the second: '.6' is 600000 us, which is what separates a padding fix from a
# stripping one.
WIDTHS = {
    0: ("2026-10-07T03:30:07+00:00", 0),
    1: ("2026-10-07T03:30:07.6+00:00", 600000),
    2: ("2026-10-07T03:30:07.61+00:00", 610000),
    3: ("2026-10-07T03:30:07.613+00:00", 613000),
    4: ("2026-10-07T03:30:07.6135+00:00", 613500),
    5: ("2026-10-07T03:30:07.61356+00:00", 613560),
    6: ("2026-10-07T03:30:07.613560+00:00", 613560),
}
# The string in logs/marker.log that this test exists to make parseable.
LOG_TS = "2026-10-07T03:30:07.61356+00:00"

print("--- build_market_spot_session_markers.parse_ts: fraction widths, +00:00 form ---")
width_ok = {}
for n, (ts, micro) in sorted(WIDTHS.items()):
    want = datetime(2026, 10, 7, 3, 30, 7, micro, tzinfo=UTC)
    width_ok[n] = check(f"fraction {n} digit(s)  {ts}", M.parse_ts(ts), want)

print("\n--- the same widths with a 'Z' suffix ---")
for n, (ts, micro) in sorted(WIDTHS.items()):
    want = datetime(2026, 10, 7, 3, 30, 7, micro, tzinfo=UTC)
    check(f"fraction {n} digit(s), Z suffix", M.parse_ts(ts.replace("+00:00", "Z")), want)

print("\n--- the exact string from the failing run ---")
check(f"log string {LOG_TS}", M.parse_ts(LOG_TS),
      datetime(2026, 10, 7, 3, 30, 7, 613560, tzinfo=UTC))

# ---- the consumer: latest_trade_date_from_spot's own expression ------------------
# That function does parse_ts(...).astimezone(IST).date(). Asserting the date through
# the same expression is what ties this test to the thing that broke, rather than to
# parse_ts in isolation.
print("\n--- IST date, via the latest_trade_date_from_spot expression ---")


def ist_date(ts):
    dt = M.parse_ts(ts)
    return dt.astimezone(IST).date() if dt is not None else None


check(f"ist_date({LOG_TS})", ist_date(LOG_TS), date(2026, 10, 7))
check("IST rollover 2026-10-06T19:00:00.5+00:00 -> 2026-10-07",
      ist_date("2026-10-06T19:00:00.5+00:00"), date(2026, 10, 7))
check("IST rollover 6-digit control 2026-10-06T19:00:00.500000+00:00",
      ist_date("2026-10-06T19:00:00.500000+00:00"), date(2026, 10, 7))
check("IST no-rollover 2026-10-06T18:00:00.500000+00:00 -> 2026-10-06",
      ist_date("2026-10-06T18:00:00.500000+00:00"), date(2026, 10, 6))

# ---- the except -> None path must survive the fix -------------------------------
# parse_ts is called on rows that may carry a NULL ts (build_row_for_symbol:289 guards
# for exactly that), so None for bad input is the contract, not a leftover.
print("\n--- genuinely bad input still returns None ---")
for bad in (None, "", "not-a-timestamp", "2026-13-45T99:99:99+00:00"):
    check(f"parse_ts({bad!r})", M.parse_ts(bad), None)

# ---- out-of-contract inputs: asserted as PRE/POST PARITY, not as a value ---------
# Neither string below is in PostgREST's emission set (microsecond precision is 6 digits,
# and it never emits a bare '.'), so this fix is not required to do anything particular
# with them -- only to leave them as they were. Both cells are therefore a comparison
# against the pre-fix body, which is the only thing that can actually be claimed here.
#
# The trailing-dot case is on this list because my first pass asserted it returns None
# and the run said otherwise: 3.10's fromisoformat ACCEPTS '2026-10-07T03:30:07.+00:00'
# as 0 us. That expected value was recalled rather than measured, which is the error
# shape S81/§D.40.1 is about, so it is now stated as the parity it is and the measured
# value is printed beside it rather than written into the file as a literal.
print("\n--- out-of-contract inputs: unchanged before and after (parity) ---")
for label, ts in (("7-digit fraction", "2026-10-07T03:30:07.1234567+00:00"),
                  ("bare trailing dot", "2026-10-07T03:30:07.+00:00")):
    pre = _parse_ts_PRE_S91(ts)
    post = M.parse_ts(ts)
    print(f"      measured: pre={pre!r}  post={post!r}")
    check(f"{label} {ts}: post-fix == pre-fix", post, pre)

# ---- the defect's signature, asserted against the pre-fix body ------------------
print("\n--- pre-fix signature control ---")
pre_bad = sorted(n for n, (ts, _m) in WIDTHS.items() if _parse_ts_PRE_S91(ts) is None)
check("widths the PRE_S91 body returns None for == [1, 2, 4, 5]", pre_bad, [1, 2, 4, 5])

post_bad = sorted(n for n, ok in width_ok.items() if not ok)
if post_bad == [1, 2, 4, 5]:
    shape = "PRE-FIX signature -- the patch is NOT in this module"
elif not post_bad:
    shape = "POST-FIX -- every width 0-6 parses to the right instant"
else:
    shape = "UNEXPECTED SHAPE -- neither the pre-fix signature nor a clean pass"
print(f"live module widths failing: {post_bad}  -> {shape}")

print(f"\nMARKER TS PARSE {'ALL PASS' if fails == 0 else f'{fails} FAIL'}")
sys.exit(1 if fails else 0)
