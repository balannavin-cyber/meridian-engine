"""
fix_gamma_set_symbol_call.py — convert `log.symbol = result.symbol` to
`log.set_symbol(result.symbol)` in compute_gamma_metrics_local.py.

Uses Python file I/O with explicit UTF-8 encoding to avoid the
cp1252 codec hazard that Set-Content triggers (V18F governance rule
`no_powershell_set_content_on_python`).

Idempotent: if the file already contains `log.set_symbol(result.symbol)`
(and no trailing `log.symbol = result.symbol`), prints [SKIP] and exits 0.

ast.parse validates the patched source before writing.
"""
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path


TARGET = Path("compute_gamma_metrics_local.py")
BACKUP = Path("compute_gamma_metrics_local.py.bak_set_symbol_call")

OLD_LINE = "    log.symbol = result.symbol"
NEW_LINE = "    log.set_symbol(result.symbol)"


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} not found.", file=sys.stderr)
        return 1

    # Explicit UTF-8 read — never trust the platform default for Python sources.
    src = TARGET.read_text(encoding="utf-8")

    if NEW_LINE in src and OLD_LINE not in src:
        print("[SKIP] Already patched: log.set_symbol(result.symbol) present,"
              " no stray log.symbol assignment.")
        return 0

    if OLD_LINE not in src:
        print(f"[ERROR] Could not find expected line:")
        print(f"        {OLD_LINE!r}")
        print(f"        File may have drifted. Aborting without changes.",
              file=sys.stderr)
        return 1

    patched = src.replace(OLD_LINE, NEW_LINE)

    # Confirm exactly one replacement happened.
    expected_delta = src.count(OLD_LINE)
    actual_delta = src.count(OLD_LINE) - patched.count(OLD_LINE)
    if actual_delta != expected_delta or expected_delta != 1:
        print(f"[ERROR] Expected exactly 1 replacement, got {actual_delta} "
              f"(target appeared {expected_delta} times).", file=sys.stderr)
        return 1

    # Governance rule patch_script_syntax_validation: ast.parse before writing.
    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"[FAIL] Patched source has SyntaxError: {e}", file=sys.stderr)
        return 1

    shutil.copy2(TARGET, BACKUP)
    TARGET.write_text(patched, encoding="utf-8")
    print(f"[OK] Backed up to {BACKUP}")
    print(f"[OK] {TARGET} patched: {OLD_LINE.strip()} -> {NEW_LINE.strip()}")
    print(f"[OK] ast.parse passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
