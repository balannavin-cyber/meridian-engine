#!/usr/bin/env python3
p = open('merdian_signal_dashboard.py', encoding='utf-8').read()
old = '.order("detected_at", desc=True)'
new = '.order("detected_at_ts", desc=True)'
if old not in p:
    print(f"ERROR: anchor not found. Searching for 'detected_at' occurrences:")
    for i, line in enumerate(p.splitlines(), 1):
        if 'detected_at' in line:
            print(f"  Line {i}: {line.strip()}")
else:
    p = p.replace(old, new, 1)
    open('merdian_signal_dashboard.py', 'w', encoding='utf-8').write(p)
    print("OK: fixed detected_at -> detected_at_ts")
