#!/usr/bin/env python3
"""Fix indentation error at line 492-499 in run_option_snapshot_intraday_runner.py"""
from pathlib import Path

TARGET = Path("run_option_snapshot_intraday_runner.py")
lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)

# Lines 491-499 (0-indexed: 490-498)
# The breadth block has 8-space indent, needs 4-space
fixed = []
for i, line in enumerate(lines):
    lineno = i + 1
    if 492 <= lineno <= 499:
        # Strip 4 extra leading spaces
        if line.startswith("        "):
            line = "    " + line[8:]
    fixed.append(line)

TARGET.write_text("".join(fixed), encoding="utf-8")

# Verify
import ast
try:
    ast.parse(TARGET.read_text(encoding="utf-8"))
    print("OK: syntax valid")
except SyntaxError as e:
    print(f"STILL BROKEN at line {e.lineno}: {e.msg}")
