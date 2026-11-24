#!/usr/bin/env python3
"""Stub reader for case (b): leaves a file that a detached writer keeps
appending to for ~3 s, so it is still changing when the manifest is taken --
the same shape as the log-hashed-mid-write defect. Exits 0.

The writer is detached with its streams on /dev/null so it does not hold the
tee pipe open; otherwise tee would wait for it and there would be no window.
"""
import pathlib, subprocess, sys
day = pathlib.Path(sys.argv[1]); day.mkdir(exist_ok=True)
f = day / "NIFTY_T1_strikes.txt"
f.write_text("fake|raw|read\n")
subprocess.Popen(
    ["sh", "-c", f"for i in $(seq 300); do printf x >> '{f}'; sleep 0.01; done"],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL, start_new_session=True)
print("stub reader: left a file that is still being written, exiting 0")
