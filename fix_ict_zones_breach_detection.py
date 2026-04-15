#!/usr/bin/env python3
"""
fix_ict_zones_breach_detection.py
===================================
Adds breach detection to build_ict_htf_zones.py.

For each detected zone, checks every subsequent day's OHLC against zone bounds.
If price traded through the zone — marks it BREACHED and excludes it.

What counts as a breach:
  BULL_OB / BULL_FVG / PDL (support): breached if any subsequent day's LOW < zone_low
  BEAR_OB / BEAR_FVG / PDH (resistance): breached if any subsequent day's HIGH > zone_high

Result: only genuinely unbreached structural zones remain in ict_htf_zones.
"""
import shutil
from pathlib import Path

TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.bak_breach")

# Insert breach detection function before def upsert_zones
BREACH_FUNCTION = '''
# ── Breach detection ──────────────────────────────────────────────────────────

def filter_breached_zones(zones: list, daily_ohlcv: dict, as_of: str) -> list:
    """
    Filter out zones where price has traded through the zone bounds
    on any subsequent day after the zone was formed.

    BULL zones (support): breached if any day LOW < zone_low
    BEAR zones (resistance): breached if any day HIGH > zone_high
    PDH: breached if any day HIGH > zone_high (price pushed through resistance)
    PDL: breached if any day LOW < zone_low (price pushed through support)

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

    return active

'''

# The anchor to insert before
ANCHOR = "# ── DB write ──"
ANCHOR_ALT = "def upsert_zones"

# Add breach filter call in main, after zones are detected
OLD_WRITE_DAILY = '''        d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)
        n_daily = upsert_zones(sb, d_zones, dry_run=dry_run)'''

NEW_WRITE_DAILY = '''        d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)
        d_zones = filter_breached_zones(d_zones, daily_ohlcv, str(target_date))
        n_daily = upsert_zones(sb, d_zones, dry_run=dry_run)'''

OLD_WRITE_WEEKLY = '''        w_zones = detect_weekly_zones(weekly_bars, symbol)
        n_weekly = upsert_zones(sb, w_zones, dry_run=dry_run)'''

NEW_WRITE_WEEKLY = '''        w_zones = detect_weekly_zones(weekly_bars, symbol)
        w_zones = filter_breached_zones(w_zones, daily_ohlcv, str(target_date))
        n_weekly = upsert_zones(sb, w_zones, dry_run=dry_run)'''


def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found.")
        return 1

    source = TARGET.read_text(encoding="utf-8")

    if "filter_breached_zones" in source:
        print("Breach detection already applied.")
        return 0

    # Find insertion point
    if ANCHOR not in source and ANCHOR_ALT not in source:
        print("ERROR: insertion anchor not found.")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    # Insert breach function before the DB write section
    anchor = ANCHOR if ANCHOR in source else ANCHOR_ALT
    patched = source.replace(anchor, BREACH_FUNCTION + anchor, 1)

    # Wire in the filter calls
    errors = []
    if OLD_WRITE_DAILY in patched:
        patched = patched.replace(OLD_WRITE_DAILY, NEW_WRITE_DAILY, 1)
    else:
        errors.append("daily zones write anchor not found")

    if OLD_WRITE_WEEKLY in patched:
        patched = patched.replace(OLD_WRITE_WEEKLY, NEW_WRITE_WEEKLY, 1)
    else:
        errors.append("weekly zones write anchor not found")

    if errors:
        print(f"WARNING: Could not wire filter calls automatically:")
        for e in errors:
            print(f"  {e}")
        print("Breach function was added but filter calls need manual wiring.")
        print("Add after each detect_*_zones() call:")
        print("  zones = filter_breached_zones(zones, daily_ohlcv, str(target_date))")

    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "filter_breached_zones" in result:
        print("OK: Breach detection added to build_ict_htf_zones.py")
        if not errors:
            print("OK: Filter calls wired in for both daily and weekly zones")
        print("\nTest with dry run:")
        print("  python build_ict_htf_zones.py --dry-run")
        print("\nThen full rebuild:")
        print("  python build_ict_htf_zones.py")
        return 0
    else:
        print("ERROR: verification failed — restoring backup")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
