#!/usr/bin/env python3
"""merdian_stop.py  --  Stop all MERDIAN processes"""
import sys
sys.path.insert(0, r'C:\GammaEnginePython')
import merdian_pm as pm

print('\n  MERDIAN Stop All')
print('  ' + '='*40)
for name, msg in pm.stop_all():
    print(f'  • {name}: {msg}')
print('\n  Done. All processes stopped.\n')
