#!/usr/bin/env python3
f = "C:/GammaEnginePython/experiment_15b_kelly_sizing.py"
c = open(f, encoding="utf-8").read()
old = '"date":  str(d),'
new = '"date":  d,'
if old in c:
    c = c.replace(old, new)
    open(f, "w", encoding="utf-8").write(c)
    print("Fixed OK")
else:
    print("Not found -- checking file:")
    for i, line in enumerate(c.splitlines(), 1):
        if '"date"' in line and "daily_ohlcv" in c[max(0,c.find(line)-200):c.find(line)+200]:
            print(f"  Line {i}: {line.strip()}")
