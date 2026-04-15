#!/usr/bin/env python3
"""
fix_breach_logic3.py
=====================
Final breach/filter logic for build_ict_htf_zones.py.

Rules (ICT-aligned):
  OBs and FVGs: keep all that are unmitigated relative to current price
    - BULL_OB / BULL_FVG: keep if current_spot > zone_high (support below)
    - BEAR_OB / BEAR_FVG: keep if current_spot < zone_low (overhead supply)

  PDH / PDL: keep only nearest 2 above + 2 below current price
    - Too many PDH/PDL = noise. ICT treats most recent as highest priority.
    - Sort by proximity to current price, take closest 2 on each side.
"""
import shutil
from pathlib import Path

TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.bak_breach4")

NEW_FUNCTION = '''def filter_breached_zones(zones: list, daily_ohlcv: dict, as_of: str) -> list:
    """
    ICT-aligned zone filter. Two rules:

    1. OBs and FVGs — keep if unmitigated relative to current price:
         BULL_OB / BULL_FVG: current_spot > zone_high  (support below price)
         BEAR_OB / BEAR_FVG: current_spot < zone_low   (resistance above price)

    2. PDH / PDL — keep nearest 2 above + 2 below current price only.
         ICT: most recent unmitigated PDH/PDL is highest priority.
         Older ones are superseded by newer structure.
    """
    sorted_dates = sorted(k for k in daily_ohlcv.keys() if k <= as_of)
    if not sorted_dates:
        return zones
    current_spot = daily_ohlcv[sorted_dates[-1]]["close"]

    ob_fvg = []
    pdh_above = []  # resistance PDH/PDL above current price
    pdl_below = []  # support PDH/PDL below current price

    for zone in zones:
        zone_high = float(zone["zone_high"])
        zone_low  = float(zone["zone_low"])
        pattern   = zone.get("pattern_type", "")
        direction = zone.get("direction", 0)

        if pattern in ("BULL_OB", "BULL_FVG"):
            # Support: valid if current price is above the zone
            if current_spot > zone_high:
                ob_fvg.append(zone)

        elif pattern in ("BEAR_OB", "BEAR_FVG"):
            # Resistance: valid if current price is below the zone
            if current_spot < zone_low:
                ob_fvg.append(zone)

        elif pattern == "PDH":
            # PDH = resistance level
            if current_spot < zone_low:
                # Above current price — potential overhead resistance
                pdh_above.append((zone_low, zone))
            # PDH below current price = already surpassed, skip

        elif pattern == "PDL":
            # PDL = support level
            if current_spot > zone_high:
                # Below current price — potential support
                pdl_below.append((zone_high, zone))
            # PDL above current price = doesn't make sense, skip

        else:
            # Unknown pattern type — keep
            ob_fvg.append(zone)

    # Sort PDH by proximity to current price (nearest first) — take top 2
    pdh_above.sort(key=lambda x: x[0])          # ascending = nearest first
    nearest_pdh = [z for _, z in pdh_above[:2]]

    # Sort PDL by proximity to current price (nearest first = highest PDL) — take top 2
    pdl_below.sort(key=lambda x: x[0], reverse=True)  # descending = nearest first
    nearest_pdl = [z for _, z in pdl_below[:2]]

    return ob_fvg + nearest_pdh + nearest_pdl
'''


def main():
    lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)

    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("def filter_breached_zones"):
            start = i
            break

    if start is None:
        print("ERROR: function not found")
        return 1

    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("def ") or lines[i].startswith("# ─"):
            end = i
            break

    if end is None:
        print("ERROR: could not find end of function")
        return 1

    print(f"Replacing filter_breached_zones at lines {start+1}–{end}...")

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    new_lines = lines[:start] + [NEW_FUNCTION] + lines[end:]
    TARGET.write_text("".join(new_lines), encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "nearest_pdh" in result and "nearest_pdl" in result:
        print("OK: ICT-aligned filter applied")
        print("  OBs/FVGs: all unmitigated zones kept")
        print("  PDH/PDL:  nearest 2 above + 2 below current price")
        return 0
    else:
        print("ERROR: verification failed — restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
