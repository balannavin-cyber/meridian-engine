#!/usr/bin/env python3
"""Fix unicode arrow causing cp1252 error on Windows."""
from pathlib import Path

TARGET = Path("build_ict_htf_zones_historical.py")
content = TARGET.read_text(encoding="utf-8")
fixed = content.replace("\u2192", "->")
TARGET.write_text(fixed, encoding="utf-8")
print("OK: unicode arrow replaced")
