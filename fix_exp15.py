#!/usr/bin/env python3
"""fix_exp15.py -- fixes bar_ts TypeError in experiment_15"""
from datetime import datetime

f = "C:/GammaEnginePython/experiment_15_pure_ict_compounding.py"
c = open(f, encoding="utf-8").read()

old = 'bar_ts=datetime.fromisoformat(r["bar_ts"]),'
new = 'bar_ts=r["bar_ts"] if isinstance(r["bar_ts"], datetime) else datetime.fromisoformat(r["bar_ts"]),'

if old in c:
    c = c.replace(old, new)
    open(f, "w", encoding="utf-8").write(c)
    print("Fixed OK")
else:
    print("Pattern not found -- checking what is on that line...")
    for i, line in enumerate(c.splitlines(), 1):
        if "fromisoformat" in line and "bar_ts" in line:
            print(f"  Line {i}: {line.strip()}")
