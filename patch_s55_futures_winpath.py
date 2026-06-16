#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_s55_futures_winpath.py  (Patch Script Canon v3)

Fixes TD-S53-NEW-6: capture_index_futures_snapshot_local.py never ran on AWS
because it carries three hardcoded Windows-path references:

  L50  DEBUG_DIR = Path(r"C:\\GammaEnginePython\\debug_outputs")   -> dir absent on EC2
  L246 print(... {path.relative_to(Path(r'C:\\GammaEnginePython'))})  -> f-string SyntaxError
  L253 print(... {path.relative_to(Path(r'C:\\GammaEnginePython'))})  -> f-string SyntaxError

Python forbids a backslash inside an f-string '{...}' expression, so the module
fails to even parse -> the post-market run's futures step returns 1 -> archive
gate fails -> "MARKET CLOSE CAPTURE FAILED" daily (surfaced via TD-S54-NEW-3).

Fix:
  - Repoint DEBUG_DIR to <script_dir>/debug_outputs (valid on AWS).
  - Ensure that directory exists (insert one mkdir after the assignment).
  - Drop the relative_to() calls; print the path plainly (no backslash in {}).

Idempotent: a second run finds no target substrings (and the mkdir already
present) and is a no-op.

Usage:
  python3 patch_s55_futures_winpath.py
  python3 patch_s55_futures_winpath.py --apply
  python3 patch_s55_futures_winpath.py --apply --file <path>
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

DEFAULT_FILE = "capture_index_futures_snapshot_local.py"
BACKUP_SUFFIX = "_PRE_S55.py"

# (old, new) exact-substring swaps, applied per line, all occurrences.
REPLACEMENTS: list[tuple[str, str]] = [
    ('Path(r"C:\\GammaEnginePython\\debug_outputs")',
     'Path(__file__).resolve().parent / "debug_outputs"'),
    ("{path.relative_to(Path(r'C:\\GammaEnginePython'))}",
     "{path}"),
]

# After the line that defines DEBUG_DIR, ensure the dir exists.
INSERT_ANCHOR = "DEBUG_DIR = Path("
INSERT_LINE = 'DEBUG_DIR.mkdir(parents=True, exist_ok=True)'
INSERT_GUARD = "DEBUG_DIR.mkdir("  # if already present anywhere, skip insert


def detect_eol(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return "\r\n" if crlf >= lf and crlf > 0 else "\n"


def main() -> int:
    apply = "--apply" in sys.argv
    path_str = DEFAULT_FILE
    if "--file" in sys.argv:
        i = sys.argv.index("--file")
        if i + 1 >= len(sys.argv):
            print("ERROR: --file requires a path argument", file=sys.stderr)
            return 2
        path_str = sys.argv[i + 1]

    path = Path(path_str)
    if not path.is_file():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2

    raw = path.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    eol = detect_eol(text)
    lines = text.replace("\r\n", "\n").split("\n")

    changes: list[tuple[int, str, str]] = []
    swapped: list[str] = []
    for idx, line in enumerate(lines, start=1):
        new_line = line
        for old, new in REPLACEMENTS:
            if old in new_line:
                new_line = new_line.replace(old, new)
        if new_line != line:
            changes.append((idx, line.strip(), new_line.strip()))
        swapped.append(new_line)

    # Insert mkdir after the DEBUG_DIR assignment, unless already present.
    has_guard = any(INSERT_GUARD in ln for ln in swapped)
    out_lines: list[str] = []
    inserted = False
    for ln in swapped:
        out_lines.append(ln)
        if (not has_guard) and (not inserted) and INSERT_ANCHOR in ln:
            # match the anchor's leading indentation (DEBUG_DIR is top-level)
            indent = ln[: len(ln) - len(ln.lstrip())]
            out_lines.append(indent + INSERT_LINE)
            inserted = True
            changes.append((0, "(insert after DEBUG_DIR =)", indent + INSERT_LINE))

    if not changes:
        print("No target substrings found and mkdir present -- already patched (no-op). Exiting 0.")
        return 0

    new_text = eol.join(out_lines)

    try:
        ast.parse(new_text)
    except SyntaxError as e:
        print(f"ERROR: patched source fails ast.parse: {e}", file=sys.stderr)
        return 1

    print(f"File:    {path}")
    print(f"EOL:     {'CRLF' if eol == chr(13)+chr(10) else 'LF'}"
          f"{'  (+BOM)' if had_bom else ''}")
    print(f"Changes: {len(changes)}")
    print("-" * 60)
    for ln, before, after in changes:
        loc = f"L{ln}" if ln else "INSERT"
        print(f"  {loc}")
        print(f"    - {before}")
        print(f"    + {after}")
    print("-" * 60)

    if not apply:
        print("DRY-RUN. Re-run with --apply to write the backup and patch.")
        return 0

    backup = path.with_name(path.stem + BACKUP_SUFFIX)
    backup.write_bytes(raw)
    print(f"Backup:  {backup}")

    out = new_text.encode("utf-8")
    if had_bom:
        out = b"\xef\xbb\xbf" + out
    path.write_bytes(out)
    print(f"WROTE:   {path} ({len(out)} bytes)")
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
