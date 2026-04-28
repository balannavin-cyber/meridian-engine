#!/usr/bin/env python3
p = open('merdian_signal_dashboard.py', encoding='utf-8').read()
old = 'HTTPServer(("localhost", PORT)'
new = 'HTTPServer(("0.0.0.0", PORT)'
if old not in p:
    print("ERROR: anchor not found")
else:
    p = p.replace(old, new, 1)
    open('merdian_signal_dashboard.py', 'w', encoding='utf-8').write(p)
    print("OK: bound to 0.0.0.0")
