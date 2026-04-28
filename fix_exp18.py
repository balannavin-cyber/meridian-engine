#!/usr/bin/env python3
"""Fix in_ filter in experiment_18_oi_ict_confluence.py"""
from pathlib import Path

TARGET = Path("experiment_18_oi_ict_confluence.py")
source = TARGET.read_text(encoding="utf-8")
fixed = source.replace(
    '("in", "pattern_type", \'("BEAR_OB","BULL_OB","BULL_FVG","BEAR_FVG")\')',
    '("in_", "pattern_type", \'("BEAR_OB","BULL_OB","BULL_FVG","BEAR_FVG")\')'
)
TARGET.write_text(fixed, encoding="utf-8")
print("Fixed" if '("in_"' in TARGET.read_text() else "FAILED")
