#!/usr/bin/env python3
"""
fix_td019_add_sys_import.py

Follow-up to fix_td019_instrument_build_spot_bars_mtf.py.

The first patch added sys.exit(main()) at module bottom but did not add
`import sys` -- the original file never imported sys. This patch adds it.

Idempotent: re-running is a no-op.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\build_spot_bars_mtf.py")

OLD = '''import os
import time
from collections import defaultdict'''

NEW = '''import os
import sys
import time
from collections import defaultdict'''


def main() -> int:
    if not TARGET.exists():
        print(f"[FAIL] Target not found: {TARGET}", file=sys.stderr)
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Idempotency
    if "\nimport sys\n" in src:
        print(f"[SKIP] {TARGET.name} already imports sys. No-op.")
        return 0

    if OLD not in src:
        print("[FAIL] Could not locate import block.", file=sys.stderr)
        return 2

    new_src = src.replace(OLD, NEW, 1)

    if new_src.count("\nimport sys\n") != 1:
        print("[FAIL] sys import not present exactly once after replacement.",
              file=sys.stderr)
        return 3

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"[FAIL] ast.parse() rejected patched source: {e}", file=sys.stderr)
        return 4

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"[OK] Added 'import sys' to {TARGET}")
    print(f"     Size: {len(src):,} -> {len(new_src):,} bytes")
    print()
    print("Next: python build_spot_bars_mtf.py   (the backfill, again)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
