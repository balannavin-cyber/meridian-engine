#!/usr/bin/env python3
"""Fix breach logic using line number based replacement."""
import shutil
from pathlib import Path

TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.bak_breach3")

NEW_FUNCTION = '''def filter_breached_zones(zones: list, daily_ohlcv: dict, as_of: str) -> list:
    """
    Filter zones by current price position.

    RESISTANCE (PDH, BEAR_OB, BEAR_FVG): valid if current spot < zone_low (overhead supply)
    SUPPORT (PDL, BULL_OB, BULL_FVG): valid if current spot > zone_high (support below)

    This correctly handles ATH zones: PDH at 26,200 with price at 24,200
    remains valid overhead resistance. Historical breach tracking incorrectly
    removes it because price traded through it on the way up to the ATH.
    """
    sorted_dates = sorted(k for k in daily_ohlcv.keys() if k <= as_of)
    if not sorted_dates:
        return zones
    current_spot = daily_ohlcv[sorted_dates[-1]]["close"]
    active = []
    for zone in zones:
        zone_high = float(zone["zone_high"])
        zone_low  = float(zone["zone_low"])
        direction = zone.get("direction", 0)
        pattern   = zone.get("pattern_type", "")
        is_resistance = direction < 0 or pattern in ("PDH", "BEAR_OB", "BEAR_FVG")
        is_support    = direction > 0 or pattern in ("PDL", "BULL_OB", "BULL_FVG")
        if is_resistance:
            if current_spot < zone_low:
                active.append(zone)
        elif is_support:
            if current_spot > zone_high:
                active.append(zone)
        else:
            active.append(zone)
    return active
'''

def main():
    lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)

    # Find start and end of the function
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("def filter_breached_zones"):
            start = i
            break

    if start is None:
        print("ERROR: function not found")
        return 1

    # Find next def after start
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("def ") or lines[i].startswith("# ─"):
            end = i
            break

    if end is None:
        print("ERROR: could not find end of function")
        return 1

    print(f"Found function at lines {start+1}–{end} — replacing...")

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    new_lines = lines[:start] + [NEW_FUNCTION] + lines[end:]
    TARGET.write_text("".join(new_lines), encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "current_spot = daily_ohlcv" in result:
        print("OK: breach logic fixed — now uses current price position")
        return 0
    else:
        print("ERROR: verification failed — restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
