"""
fix_ict_time_zone_utc.py

Bug B1c (Session 10 2026-04-26):
ICT detector's time_zone_label() compares bar_ts.time() against
naive IST clock-time constants (OPEN_START=09:15, MORNING_START=10:00, etc.)
But bar_ts comes from hist_spot_bars_1m as UTC timestamptz.

Effect: bar.bar_ts.time() returns UTC clock-time (e.g., 04:31 for an
IST 10:01 bar). 04:31 < OPEN_START (09:15), falls through every branch,
returns "OTHER".

Result: 100% of detected ict_zones rows have time_zone="OTHER", which
means assign_tier() never reaches the "MORNING" / "AFTNOON" branches.
TIER1 promotion is structurally unreachable. All zones land at TIER2.

Fix: convert bar_ts to IST inside time_zone_label() before extracting
time-of-day. Use the existing IST constant pattern from the runner
(zoneinfo.ZoneInfo("Asia/Kolkata")).

Verification post-patch: any 1m bar at 09:30 IST should classify as
"OPEN", a 10:30 IST bar as "MORNING", 14:00 IST as "AFTNOON".
"""

from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TARGET = Path("detect_ict_patterns.py")
BACKUP = Path("detect_ict_patterns.py.pre_tz_fix.bak")


# Old function body (search target)
OLD_FUNC = '''def time_zone_label(ts: datetime) -> str:
    t = ts.time()
    if OPEN_START <= t < MORNING_START:
        return "OPEN"
    if MORNING_START <= t < MIDDAY_START:
        return "MORNING"
    if MIDDAY_START <= t < AFTNOON_START:
        return "MIDDAY"
    if AFTNOON_START <= t <= SESSION_END:
        return "AFTNOON"
    return "OTHER"'''

# New function body
NEW_FUNC = '''def time_zone_label(ts: datetime) -> str:
    # Session 10 2026-04-26 fix: bar_ts arrives as UTC timestamptz from
    # hist_spot_bars_1m. Comparing UTC clock-time against IST constants
    # (OPEN_START=09:15 etc.) caused 100% of detections to fall through
    # to "OTHER" -- killing all TIER1 promotion paths.
    # Convert to IST before extracting time-of-day.
    from zoneinfo import ZoneInfo
    if ts.tzinfo is not None:
        ts_ist = ts.astimezone(ZoneInfo("Asia/Kolkata"))
    else:
        # Naive datetime: assume already IST (legacy callers).
        ts_ist = ts
    t = ts_ist.time()
    if OPEN_START <= t < MORNING_START:
        return "OPEN"
    if MORNING_START <= t < MIDDAY_START:
        return "MORNING"
    if MIDDAY_START <= t < AFTNOON_START:
        return "MIDDAY"
    if AFTNOON_START <= t <= SESSION_END:
        return "AFTNOON"
    return "OTHER"'''


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found in cwd {Path.cwd()}", file=sys.stderr)
        return 1

    src = TARGET.read_text(encoding="utf-8")

    if src.count(OLD_FUNC) != 1:
        print(
            f"ERROR: time_zone_label target found {src.count(OLD_FUNC)} times "
            f"(expected exactly 1). Function may already have been patched, "
            f"or its body has changed. Aborting without changes.",
            file=sys.stderr,
        )
        return 2

    shutil.copy2(TARGET, BACKUP)
    print(f"Backed up: {BACKUP}")

    new_src = src.replace(OLD_FUNC, NEW_FUNC)

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"ERROR: post-patch syntax invalid: {e}", file=sys.stderr)
        print(f"NOT writing. Backup retained at {BACKUP}.", file=sys.stderr)
        return 3

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"Patched: {TARGET}")
    print()
    print("Verification:")
    print("  Run a manual cycle:")
    print("    python detect_ict_patterns_runner.py NIFTY")
    print("  Then check ict_zones for time_zone != 'OTHER':")
    print("    SELECT time_zone, COUNT(*) FROM ict_zones GROUP BY 1;")
    print()
    print(f"Rollback: copy {BACKUP} back over {TARGET}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
