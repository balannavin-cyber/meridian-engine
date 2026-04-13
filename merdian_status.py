#!/usr/bin/env python3
"""
merdian_status.py  --  Show MERDIAN process status

Usage:
    python merdian_status.py           # one-shot
    python merdian_status.py --watch   # refresh every 5s
"""
import sys, time
sys.path.insert(0, r'C:\GammaEnginePython')
import merdian_pm as pm

if '--watch' in sys.argv:
    try:
        while True:
            print('\033[2J\033[H', end='')
            pm.print_status()
            print('  Ctrl+C to exit')
            time.sleep(5)
    except KeyboardInterrupt:
        print('\n  Stopped.')
else:
    pm.print_status()
