#!/usr/bin/env python3
"""Wire filter_breached_zones calls into build_ict_htf_zones.py main."""
import shutil
from pathlib import Path

TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.bak_breach2")

OLD_WEEKLY = '''            w_zones = detect_weekly_zones(weekly_bars, symbol)
            log(f"  Detected {len(w_zones)} weekly zones")
            n = upsert_zones(sb, w_zones, dry_run)'''

NEW_WEEKLY = '''            w_zones = detect_weekly_zones(weekly_bars, symbol)
            w_zones = filter_breached_zones(w_zones, daily_ohlcv, str(target_date))
            log(f"  Detected {len(w_zones)} weekly zones (after breach filter)")
            n = upsert_zones(sb, w_zones, dry_run)'''

OLD_DAILY = '''            d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)
            log(f"  Detected {len(d_zones)} daily zones")
            n = upsert_zones(sb, d_zones, dry_run)'''

NEW_DAILY = '''            d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)
            d_zones = filter_breached_zones(d_zones, daily_ohlcv, str(target_date))
            log(f"  Detected {len(d_zones)} daily zones (after breach filter)")
            n = upsert_zones(sb, d_zones, dry_run)'''


def main():
    source = TARGET.read_text(encoding="utf-8")

    if "filter_breached_zones" not in source:
        print("ERROR: breach function not in file — run fix_ict_zones_breach_detection.py first")
        return 1

    if "after breach filter" in source:
        print("Wire calls already applied.")
        return 0

    errors = []
    if OLD_WEEKLY not in source:
        errors.append("weekly anchor not found")
    if OLD_DAILY not in source:
        errors.append("daily anchor not found")

    if errors:
        print("ERROR: anchors not found:")
        for e in errors:
            print(f"  {e}")
        # Show what's actually there
        for i, line in enumerate(source.splitlines(), 1):
            if "detect_weekly" in line or "detect_daily" in line:
                print(f"  Line {i}: {line.strip()}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    patched = source.replace(OLD_WEEKLY, NEW_WEEKLY, 1)
    patched = patched.replace(OLD_DAILY, NEW_DAILY, 1)
    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "after breach filter" in result:
        print("OK: breach filter wired into weekly and daily zone detection")
        return 0
    else:
        print("ERROR: verification failed — restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
