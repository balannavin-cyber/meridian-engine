#!/usr/bin/env python3
"""Fix _breadth_html literal in render() output."""
import shutil
from pathlib import Path

TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.bak_breadth_fix")

# The bad injection in the f-string template
OLD_INJECT = "  ' + _breadth_html + '\n  <div class=\"rules\">"

# Replace with a placeholder that we'll substitute after the f-string
NEW_INJECT = "  %%BREADTH_PANEL%%\n  <div class=\"rules\">"

# Find the return statement in render() and add post-processing
OLD_RETURN = "    return f\"\"\"<!DOCTYPE html>"

NEW_RETURN = """    _page = f\"\"\"<!DOCTYPE html>"""

OLD_END = "\"\"\"

# ---------------------------------------------------------------------------
# HTTP server"

NEW_END = """\"\"\"
    _page = _page.replace("%%BREADTH_PANEL%%", _breadth_html)
    return _page

# ---------------------------------------------------------------------------
# HTTP server"""


def main():
    source = TARGET.read_text(encoding="utf-8")

    if "%%BREADTH_PANEL%%" in source or "_page.replace" in source:
        print("Fix already applied.")
        return 0

    errors = []
    for anchor, name in [
        (OLD_INJECT, "bad inject in template"),
        (OLD_RETURN, "return f-string start"),
        (OLD_END, "end of f-string"),
    ]:
        if anchor not in source:
            errors.append(f"MISSING: {name}")

    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    p = source
    p = p.replace(OLD_INJECT, NEW_INJECT, 1)
    p = p.replace(OLD_RETURN, NEW_RETURN, 1)
    p = p.replace(OLD_END, NEW_END, 1)

    TARGET.write_text(p, encoding="utf-8")

    # Verify syntax
    import subprocess, sys
    r = subprocess.run([sys.executable, "-c",
        f"import ast; ast.parse(open('{TARGET}').read()); print('Syntax OK')"],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"SYNTAX ERROR:\n{r.stderr}")
        shutil.copy2(BACKUP, TARGET)
        return 1

    print(r.stdout.strip())

    # Quick render test
    r2 = subprocess.run([sys.executable, "-c",
        "import merdian_signal_dashboard as d; html=d.render(); "
        "print('breadth-panel in body:', html.count('breadth-panel') > 1); "
        "print('literal _breadth_html:', '_breadth_html' in html)"],
        capture_output=True, text=True)
    print(r2.stdout.strip())
    if r2.stderr:
        print("STDERR:", r2.stderr[:200])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
