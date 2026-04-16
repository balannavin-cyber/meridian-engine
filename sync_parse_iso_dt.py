#!/usr/bin/env python3
"""
Sync BREAK_GLASS fix from MERDIAN AWS to Local.
Patches parse_iso_dt in compute_volatility_metrics_local.py to pad
5-digit fractional seconds for Python 3.10 fromisoformat() compatibility.
"""
import shutil
from pathlib import Path

TARGET = Path("compute_volatility_metrics_local.py")
BACKUP = Path("compute_volatility_metrics_local.py.bak_parse_iso_dt")

OLD = '''def parse_iso_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None'''

NEW = '''def parse_iso_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        s = str(value).strip()
        # Pad fractional seconds to 6 digits for Python 3.10 compatibility
        import re
        s = re.sub(r'(\\.\\d{1,5})([+-]|Z|$)', lambda m: m.group(1).ljust(7, '0') + m.group(2), s)
        s = s.replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None'''

def main():
    source = TARGET.read_text(encoding="utf-8")

    if "Pad fractional seconds" in source:
        print("Already patched.")
        return 0

    if OLD not in source:
        print("ERROR: old function not found")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    patched = source.replace(OLD, NEW, 1)
    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "Pad fractional seconds" in result:
        print("OK: parse_iso_dt patched to match AWS BREAK_GLASS fix")
        return 0
    else:
        print("ERROR: restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
