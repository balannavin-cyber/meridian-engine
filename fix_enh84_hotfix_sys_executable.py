#!/usr/bin/env python3
"""
fix_enh84_hotfix_sys_executable.py
HOTFIX: ENH-84 endpoint references sys.executable but merdian_signal_dashboard.py
has no top-level `import sys`. Click would NameError -> HTTP 500.

Fix: replace sys.executable with literal "python" (matches every other
MERDIAN subprocess invocation -- bat files, Task Scheduler entries).

Idempotent: re-runs are no-ops (the search string won't be present after
first apply).
"""
import ast
import pathlib
import sys

TARGET = pathlib.Path(r"C:\GammaEnginePython\merdian_signal_dashboard.py")

# The exact line to replace (from the ENH-84 inserted block)
OLD_LINE_BARE = '                    [sys.executable, "build_ict_htf_zones.py",'
NEW_LINE_BARE = '                    ["python", "build_ict_htf_zones.py",'

def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    src = TARGET.read_bytes().decode("utf-8-sig")
    eol = "\r\n" if "\r\n" in src else "\n"
    print(f"Line ending detected: {'CRLF' if eol == chr(13) + chr(10) else 'LF'}")

    old_line = OLD_LINE_BARE + eol
    new_line = NEW_LINE_BARE + eol

    if new_line in src and old_line not in src:
        print("Already hotfixed (sys.executable already replaced) -- no-op.")
        return 0

    if old_line not in src:
        print(f"ERROR: target line not found:\n  {old_line!r}", file=sys.stderr)
        print("Either ENH-84 was never applied, or the line has been edited.")
        return 1

    if src.count(old_line) != 1:
        print(
            f"ERROR: target line found {src.count(old_line)} times "
            "(expected 1).",
            file=sys.stderr,
        )
        return 1

    patched = src.replace(old_line, new_line)

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"ERROR: ast.parse failed after hotfix: {e}", file=sys.stderr)
        return 1

    print("ast.parse: PASS")

    if "--dry-run" in sys.argv:
        print("[DRY-RUN] No file written.")
        return 0

    TARGET.write_bytes(patched.encode("utf-8"))
    print(f"ENH-84 hotfix applied to: {TARGET.name}")
    print(f"  sys.executable -> \"python\" (avoids missing import sys)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
