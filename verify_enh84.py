#!/usr/bin/env python3
"""
verify_enh84.py — diagnose why the REFRESH ZONES button isn't showing.
Read-only. Reports what's actually in the file.
"""
import pathlib
import sys

TARGET = pathlib.Path(r"C:\GammaEnginePython\merdian_signal_dashboard.py")

if not TARGET.exists():
    print(f"FAIL: target not found: {TARGET}")
    sys.exit(1)

src = TARGET.read_bytes().decode("utf-8-sig")

print(f"File size: {len(src):,} bytes")
print(f"Line ending: {'CRLF' if chr(13)+chr(10) in src else 'LF'}")
print()

checks = [
    ("ENH-84 marker (idempotency key)", "ENH-84"),
    ("New button HTML", "REFRESH ZONES"),
    ("New button onclick", "/refresh_and_download_pine"),
    ("New endpoint handler", 'startswith("/refresh_and_download_pine")'),
    ("subprocess import in endpoint", "import subprocess as _sp"),
    ("Hotfix applied (no sys.executable)", '["python", "build_ict_htf_zones.py"'),
    ("Original button still there",  "PINE OVERLAY"),
    ("Original endpoint still there", 'startswith("/download_pine")'),
]

all_ok = True
for label, needle in checks:
    found = needle in src
    print(f"  {'OK ' if found else 'MISS'}  {label}: {needle!r}")
    if not found:
        all_ok = False

print()
if all_ok:
    print("All markers present. If button still missing, this is a browser cache issue.")
    print("Try Ctrl+Shift+R in the browser.")
else:
    print("Markers missing — patch did not land OR was overwritten.")
    print("Check git status / recent file modifications.")

# Also report whether the dashboard process (current PID) is reading
# the patched file: print last 40 chars of the topbar block to confirm
print()
print("--- Topbar HTML block in file ---")
tb_start = src.find('class="topbar"')
if tb_start > 0:
    tb_end = src.find('</div>', tb_start)
    print(src[tb_start:tb_end+6])
else:
    print("Topbar block not found in file")
