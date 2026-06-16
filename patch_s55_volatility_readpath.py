#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_s55_volatility_readpath.py  (Patch Script Canon v3)

Fixes the volatility read-path table-name regression left by S48.

S48 corrected the WRITE path (TARGET_TABLE: 'compute_volatility_metrics' ->
'volatility_snapshots') but left two READ paths in
compute_volatility_metrics_local.py still querying the non-existent table
'compute_volatility_metrics'. Both 404 (PGRST205) every cycle; the graceful
handlers swallow it (return []), so the script still exits OK and still
inserts its row -- but every row is written with EMPTY intraday-change
context (5m/15m/30m VIX deltas, velocity, slope) and the stale-VIX fallback
can never find a prior snapshot.

Per the existing TD-NEW-12 design comments, reads MUST stay on the PRODUCTION
table 'volatility_snapshots' (even on shadow runs), so this repoints the dead
name to 'volatility_snapshots' rather than to TARGET_TABLE.

Targets (exact substrings; line 24's commented migration history is NOT a
match and is left untouched):
  - table="compute_volatility_metrics"                       (x2: reads)
  - label=f"select compute_volatility_metrics for {symbol}"  (log label)
  - label=f"fallback select compute_volatility_metrics for {symbol}"
  - "fallback_source": "compute_volatility_metrics"          (provenance)

Idempotent: a second run finds no target substrings and is a no-op.

Usage:
  python3 patch_s55_volatility_readpath.py             # dry-run (default)
  python3 patch_s55_volatility_readpath.py --apply     # write + backup
  python3 patch_s55_volatility_readpath.py --apply --file <path>
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

DEFAULT_FILE = "compute_volatility_metrics_local.py"
BACKUP_SUFFIX = "_PRE_S55.py"

# (old, new) exact-substring replacements, applied per line.
REPLACEMENTS: list[tuple[str, str]] = [
    ('table="compute_volatility_metrics"',
     'table="volatility_snapshots"'),
    ('label=f"select compute_volatility_metrics for {symbol}"',
     'label=f"select volatility_snapshots for {symbol}"'),
    ('label=f"fallback select compute_volatility_metrics for {symbol}"',
     'label=f"fallback select volatility_snapshots for {symbol}"'),
    ('"fallback_source": "compute_volatility_metrics"',
     '"fallback_source": "volatility_snapshots"'),
]


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
    # utf-8-sig strips a BOM if present; re-add on write only if it was there.
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    eol = detect_eol(text)

    # Normalise to \n for line-wise processing; restore eol on write.
    lines = text.replace("\r\n", "\n").split("\n")

    changes: list[tuple[int, str, str]] = []
    new_lines: list[str] = []
    for idx, line in enumerate(lines, start=1):
        new_line = line
        for old, new in REPLACEMENTS:
            if old in new_line:
                new_line = new_line.replace(old, new)
        if new_line != line:
            changes.append((idx, line.strip(), new_line.strip()))
        new_lines.append(new_line)

    if not changes:
        print("No target substrings found -- already patched (no-op). Exiting 0.")
        return 0

    new_text = eol.join(new_lines)

    # Validate syntax before writing.
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
        print(f"  L{ln}")
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
