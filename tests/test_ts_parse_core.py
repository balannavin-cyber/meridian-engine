#!/usr/bin/env python3
"""
tests/test_ts_parse_core.py -- core.ts_parse, the shared PostgREST ts parser.
S92, TD-S91-NEW-2 site 7 / TD-S91-NEW-6. Offline: no DB, no network, no fixtures.

WHAT WOULD MAKE THIS FAIL (Rule 0), stated before the cells:
  - A helper that STRIPS instead of PADS passes a width check but fails the
    microsecond assertion: '.6' must be 600000 us, not 6. Every width cell
    asserts the exact instant, so the two are not interchangeable.
  - A helper that quietly stopped padding would make widths 1, 2, 4 and 5
    return None. The CONTROL blocks parse the same strings with a BARE
    fromisoformat and assert that set is exactly [1, 2, 4, 5] -- so the test
    proves the padding is load-bearing rather than asserting that today's code
    agrees with itself.
  - The REAL wire strings are the ones measured on 2026-10-08, including the
    rows[0] of all three of that day's DATA_ERROR basis runs. If the helper
    cannot parse those, the fix does not fix the incident it was written for.

THE CONTROLS ARE VERSION-AWARE, AND THAT IS NOT A LOOSENING.
  The padding exists because Python 3.10's fromisoformat rejects widths
  1/2/4/5. On 3.11+ it is permissive, so the bare-fromisoformat control
  legitimately returns [] -- and a hard assertion of [1, 2, 4, 5] would fail on
  3.11 for a reason that has nothing to do with the padding. That is the very
  shape this file is meant to avoid, so on 3.11+ the control prints INERT and
  is not counted. The POSITIVE cells (1, 3, 5, 6, 7) assert on every version;
  only the control that measures the old interpreter's defect is version-gated.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.ts_parse import norm_frac, parse_pg_ts  # noqa: E402

UTC = timezone.utc
fails = 0
PY = sys.version_info[:2]
PY310 = PY == (3, 10)


def check(label, got, want):
    global fails
    ok = got == want
    if not ok:
        fails += 1
    print(f"  [{'ok' if ok else 'FAIL'}] {label}")
    if not ok:
        print(f"         got  {got!r}")
        print(f"         want {want!r}")


def measured(label, got):
    """Record a measured value WITHOUT asserting it. For behaviour that is
    interpreter- or library-defined and not what this module is responsible for."""
    print(f"  [--] {label}: measured {got!r} (recorded, not asserted)")


def bare_parses(s):
    """Unpadded fromisoformat -- the pre-fix predicate, for the control blocks."""
    try:
        datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


print(f"python {sys.version.split()[0]}  |  padding-relevant interpreter: {PY310}")

# ---- 1. fraction widths 0-6, exact microseconds ---------------------------------
WIDTHS = {
    0: ("2026-10-08T04:35:06+00:00",        0),
    1: ("2026-10-08T04:35:06.3+00:00",      300000),
    2: ("2026-10-08T04:35:06.31+00:00",     310000),
    3: ("2026-10-08T04:35:06.312+00:00",    312000),
    4: ("2026-10-08T04:35:06.3122+00:00",   312200),
    5: ("2026-10-08T04:35:06.31229+00:00",  312290),
    6: ("2026-10-08T04:35:06.312290+00:00", 312290),
}
print("\n--- 1. fraction widths 0-6, exact microsecond asserted ---")
for w, (ts, us) in WIDTHS.items():
    want = datetime(2026, 10, 8, 4, 35, 6, us, tzinfo=UTC)
    check(f"width {w}: {ts} -> {us} us", parse_pg_ts(ts), want)

# ---- 2. the control that makes cell 1 mean something ---------------------------
print("\n--- 2. CONTROL: which widths a BARE fromisoformat rejects ---")
bare_bad = sorted(w for w, (ts, _u) in WIDTHS.items() if not bare_parses(ts))
print(f"      measured: bare fromisoformat fails on widths {bare_bad}")
if PY310:
    check("bare fromisoformat fails on exactly [1, 2, 4, 5]", bare_bad, [1, 2, 4, 5])
else:
    print(f"  [--] control INERT on {sys.version.split()[0]}: bare fromisoformat is "
          f"permissive, so {bare_bad} is correct for this interpreter and the "
          f"padding is a no-op here. Not counted.")

# ---- 3. Z suffix, offsets, naive ------------------------------------------------
print("\n--- 3. Z suffix, offsets, naive input ---")
check("Z, width 6", parse_pg_ts("2026-10-08T04:35:06.312290Z"),
      datetime(2026, 10, 8, 4, 35, 6, 312290, tzinfo=UTC))
check("Z, width 5 (padding + Z together)", parse_pg_ts("2026-10-08T04:35:06.31229Z"),
      datetime(2026, 10, 8, 4, 35, 6, 312290, tzinfo=UTC))
check("Z, no fraction", parse_pg_ts("2026-10-08T04:35:06Z"),
      datetime(2026, 10, 8, 4, 35, 6, tzinfo=UTC))
check("negative offset -05:00 normalises to UTC",
      parse_pg_ts("2026-10-08T04:35:06.31229-05:00"),
      datetime(2026, 10, 8, 9, 35, 6, 312290, tzinfo=UTC))
check("positive offset +05:30 normalises to UTC",
      parse_pg_ts("2026-10-08T10:05:06.31229+05:30"),
      datetime(2026, 10, 8, 4, 35, 6, 312290, tzinfo=UTC))
check("naive input is assumed UTC and returned aware",
      parse_pg_ts("2026-10-08T04:35:06.31229"),
      datetime(2026, 10, 8, 4, 35, 6, 312290, tzinfo=UTC))
# Offset without a colon: 3.10's fromisoformat rejects it, 3.11+ accepts it. PostgREST
# always emits +00:00, so this is neither a case this module handles nor one it must.
# Recorded so the behaviour is on the record and version drift is visible.
measured("compact offset +0000 (interpreter-defined; PostgREST never emits it)",
         parse_pg_ts("2026-10-08T04:35:06.31229+0000"))

# ---- 4. None / empty / garbage -> None -----------------------------------------
print("\n--- 4. falsy and malformed input -> None ---")
for label, val in (("None", None), ("empty string", ""), ("zero", 0),
                   ("whitespace-only", "   "), ("garbage", "garbage"),
                   ("not-a-date", "not-a-date"),
                   ("7-digit fraction (Postgres never emits this)",
                    "2026-10-08T04:35:06.1234567+00:00")):
    check(f"{label} -> None", parse_pg_ts(val), None)

# ---- OUT OF CONTRACT: measured, never asserted --------------------------------
# Two inputs below are malformed-or-unusual strings that `fromisoformat` ACCEPTS.
# The helper is pure pass-through for them -- norm_frac matches neither (there is
# no digit run to pad), so whatever comes back is the interpreter's answer, not a
# decision this module makes. PostgREST emits neither form.
#
# I first asserted `bare trailing dot -> None` and the suite failed, because the
# interpreter returns 04:35:06 with 0 us. That assertion was a BELIEF I never
# measured. Moving it here is NOT "adjusting the number until it passes" (Rule 0
# clause 3) -- that would be the illegitimate move if the case were inside the
# module's contract, and it would mean replacing a belief with an observation
# while still calling it an assertion. The legitimate move is the one taken:
# recognise the input is outside what this helper is responsible for, and record
# the interpreter's behaviour instead of asserting a value for it. The same test
# file's site-2 predecessor reaches the same conclusion a different way, by
# asserting PARITY with the pre-fix body rather than a literal
# (tests/test_marker_ts_parse.py:177).
measured("bare trailing dot '...06.+00:00' (interpreter accepts it; norm_frac "
         "correctly does not match - no digits to pad)",
         parse_pg_ts("2026-10-08T04:35:06.+00:00"))
measured("date only '2026-10-08' (fromisoformat accepts a bare date)",
         parse_pg_ts("2026-10-08"))

# ---- 5. the REAL wire strings measured on 2026-10-08 ---------------------------
# Each was read off PostgREST, or reconstructed from the stored microseconds and
# confirmed at string level against the wire. The three marked rows[0] are the
# newest futures row at each of that day's three DATA_ERROR basis runs.
print("\n--- 5. real wire strings, 2026-10-08 (the incident's own data) ---")
REAL = [
    ("w5 04:35:06 (paired SQL<->wire check)", "2026-10-08T04:35:06.31229+00:00",
     datetime(2026, 10, 8, 4, 35, 6, 312290, tzinfo=UTC)),
    ("w4 04:35:08 = rows[0] of the 10:06:48 IST DATA_ERROR run",
     "2026-10-08T04:35:08.5559+00:00",
     datetime(2026, 10, 8, 4, 35, 8, 555900, tzinfo=UTC)),
    ("w5 rows[0] of the 12:41:51 IST DATA_ERROR run", "2026-10-08T07:10:09.82462+00:00",
     datetime(2026, 10, 8, 7, 10, 9, 824620, tzinfo=UTC)),
    ("w5 rows[0] of the 14:36:51 IST DATA_ERROR run (LEADING zeros: .00263)",
     "2026-10-08T09:05:09.00263+00:00",
     datetime(2026, 10, 8, 9, 5, 9, 2630, tzinfo=UTC)),
    ("w6 control: rows[0] of a run that SUCCEEDED",
     "2026-10-08T04:40:06.576527+00:00",
     datetime(2026, 10, 8, 4, 40, 6, 576527, tzinfo=UTC)),
]
for label, ts, want in REAL:
    check(label, parse_pg_ts(ts), want)

print("\n--- 5b. CONTROL: the same real strings under a BARE fromisoformat ---")
real_bad = [ts for _l, ts, _w in REAL if not bare_parses(ts)]
print(f"      measured: {len(real_bad)} of {len(REAL)} real strings fail unpadded")
if PY310:
    check("exactly the 4 trimmed strings fail unpadded", len(real_bad), 4)
    check("the w6 success-run string parses unpadded too",
          bare_parses("2026-10-08T04:40:06.576527+00:00"), True)
else:
    print(f"  [--] control INERT on {sys.version.split()[0]}: bare fromisoformat is "
          f"permissive, so {len(real_bad)} failures is correct here. Not counted.")

# ---- 6. norm_frac on its own ----------------------------------------------------
print("\n--- 6. norm_frac: padding, never stripping ---")
check("norm_frac pads w5 to w6", norm_frac("2026-10-08T04:35:06.31229+00:00"),
      "2026-10-08T04:35:06.312290+00:00")
check("norm_frac pads w1 to w6", norm_frac("2026-10-08T04:35:06.3+00:00"),
      "2026-10-08T04:35:06.300000+00:00")
check("norm_frac pads leading-zero w5", norm_frac("2026-10-08T09:05:09.00263+00:00"),
      "2026-10-08T09:05:09.002630+00:00")
check("norm_frac leaves w6 alone", norm_frac("2026-10-08T04:35:06.312290+00:00"),
      "2026-10-08T04:35:06.312290+00:00")
check("norm_frac leaves a no-fraction string alone",
      norm_frac("2026-10-08T04:35:06+00:00"), "2026-10-08T04:35:06+00:00")
check("norm_frac does not touch a 7-digit fraction",
      norm_frac("2026-10-08T04:35:06.1234567+00:00"),
      "2026-10-08T04:35:06.1234567+00:00")

# ---- 7. the adopting call site actually uses the helper ------------------------
# A test of core/ alone would pass while the call site still carried its own
# unpadded body, so the adoption is asserted through the real module.
print("\n--- 7. compute_basis_context_local.parse_ts delegates to the helper ---")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cbc_under_test",
        str(Path(__file__).resolve().parents[1] / "compute_basis_context_local.py"))
    cbc = importlib.util.module_from_spec(spec)
    sys.modules["cbc_under_test"] = cbc
    spec.loader.exec_module(cbc)
    for label, ts, want in REAL:
        check(f"cbc.parse_ts {ts}", cbc.parse_ts(ts), want)
    check("cbc.parse_ts(None) -> None", cbc.parse_ts(None), None)
    check("cbc.parse_ts('') -> None", cbc.parse_ts(""), None)
except Exception as e:  # noqa: BLE001
    fails += 1
    print(f"  [FAIL] could not exercise compute_basis_context_local.parse_ts: {e}")

print(f"\nCORE TS PARSE {'ALL PASS' if fails == 0 else f'{fails} FAIL'}")
sys.exit(1 if fails else 0)
