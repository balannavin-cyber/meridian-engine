#!/usr/bin/env python3
"""
fix_breach_logic.py
====================
Fixes filter_breached_zones in build_ict_htf_zones.py.

Problem: resistance zones near ATH get marked as 'breached' because price 
traded through them on the way UP to the ATH. But those levels are still 
valid overhead resistance now that price has pulled back.

Fix: use current price position instead of historical breach tracking.
  - Resistance (PDH, BEAR_OB, BEAR_FVG): valid if current spot < zone_low
  - Support (PDL, BULL_OB, BULL_FVG): valid if current spot > zone_high

Current spot is fetched from market_spot_snapshots or computed from 
the last available daily close in the OHLCV data.
"""
import shutil
from pathlib import Path

TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.bak_breach3")

OLD_FUNCTION = '''def filter_breached_zones(zones: list, daily_ohlcv: dict, as_of: str) -> list:
    """
    Filter out zones where price has traded through the zone bounds
    on any subsequent day after the zone was formed.

    BULL zones (support): breached if any day LOW < zone_low
    BEAR zones (resistance): breached if any day HIGH > zone_high

    Args:
        zones: list of zone dicts (already detected)
        daily_ohlcv: full daily OHLCV dict {date_str: {open,high,low,close}}
        as_of: today's date string — only check days up to today

    Returns:
        list of unbreached zones only
    """
    from datetime import date as _date

    # Build sorted list of (date_str, high, low) for fast iteration
    sorted_days = sorted(
        [(k, v["high"], v["low"]) for k, v in daily_ohlcv.items()
         if k <= as_of],
        key=lambda x: x[0]
    )

    active = []
    for zone in zones:
        src = zone.get("source_bar_date", zone.get("valid_from", ""))
        zone_high = float(zone["zone_high"])
        zone_low  = float(zone["zone_low"])
        direction = zone.get("direction", 0)
        pattern   = zone.get("pattern_type", "")

        # Only check days AFTER the zone was formed
        subsequent = [(d, h, l) for d, h, l in sorted_days if d > src]

        breached = False
        for day_str, day_high, day_low in subsequent:
            if direction > 0 or pattern in ("PDL", "BULL_OB", "BULL_FVG"):
                # Support zone: breached if price closed below zone_low
                if day_low < zone_low:
                    breached = True
                    break
            elif direction < 0 or pattern in ("PDH", "BEAR_OB", "BEAR_FVG"):
                # Resistance zone: breached if price pushed above zone_high
                if day_high > zone_high:
                    breached = True
                    break

        if not breached:
            active.append(zone)

    return active'''

NEW_FUNCTION = '''def filter_breached_zones(zones: list, daily_ohlcv: dict, as_of: str) -> list:
    """
    Filter zones by current price position — keeps only zones that are
    still actionable relative to where price is today.

    Logic:
      RESISTANCE (PDH, BEAR_OB, BEAR_FVG, direction<0):
        Valid only if current spot is BELOW the zone (overhead supply).
        If price is already above the zone, it's been surpassed — not useful.

      SUPPORT (PDL, BULL_OB, BULL_FVG, direction>0):
        Valid only if current spot is ABOVE the zone (support below).
        If price has fallen through the zone, it's breached.

    This correctly handles ATH zones: if NIFTY made a PDH at 26,200
    and is now at 24,200, that 26,200 PDH is valid overhead resistance.
    Historical breach tracking incorrectly removes it because price
    traded through it on the way up to the ATH.

    Args:
        zones: list of zone dicts (already detected)
        daily_ohlcv: full daily OHLCV dict {date_str: {open,high,low,close}}
        as_of: today's date string

    Returns:
        list of currently-actionable zones
    """
    # Get current spot = last available close price
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
            # Keep if current price is below the zone (still overhead)
            if current_spot < zone_low:
                active.append(zone)
        elif is_support:
            # Keep if current price is above the zone (still support below)
            if current_spot > zone_high:
                active.append(zone)
        else:
            # Unknown direction — keep it
            active.append(zone)

    return active'''


def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found")
        return 1

    source = TARGET.read_text(encoding="utf-8")

    if OLD_FUNCTION not in source:
        print("ERROR: old function anchor not found")
        # Check if already patched
        if "current_spot = daily_ohlcv" in source:
            print("Already patched.")
            return 0
        # Show what's there
        for i, line in enumerate(source.splitlines(), 1):
            if "filter_breached" in line:
                print(f"  Line {i}: {line.strip()}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    patched = source.replace(OLD_FUNCTION, NEW_FUNCTION, 1)
    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "current_spot = daily_ohlcv" in result:
        print("OK: breach logic fixed — now uses current price position")
        print("\nDry run to verify:")
        print("  python build_ict_htf_zones.py --dry-run")
        return 0
    else:
        print("ERROR: verification failed — restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
