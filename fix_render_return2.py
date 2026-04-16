#!/usr/bin/env python3
"""Direct fix: add return statement to render() after _page assignment."""
import shutil, subprocess, sys
from pathlib import Path

TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.bak_render_fix2")

# The HTTP server section starts right after render() ends
# We know render() ends just before "# ---------------------------------------------------------------------------"
# "# HTTP server"

OLD = '''# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):'''

NEW = '''    _page = _page.replace("%%BREADTH_PANEL%%", _breadth_html)
    return _page

# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):'''

def main():
    source = TARGET.read_text(encoding="utf-8")

    if "_page.replace" in source:
        print("Already fixed.")
        return 0

    if OLD not in source:
        print("ERROR: HTTP server anchor not found")
        return 1

    shutil.copy2(TARGET, BACKUP)
    patched = source.replace(OLD, NEW, 1)
    TARGET.write_text(patched, encoding="utf-8")

    r = subprocess.run([sys.executable, "-c",
        f"import ast; ast.parse(open(r'{TARGET}').read()); print('Syntax OK')"],
        capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
        shutil.copy2(BACKUP, TARGET)
        return 1

    r2 = subprocess.run([sys.executable, "-c",
        "import merdian_signal_dashboard as d; h=d.render(); "
        "print('OK, len:', len(h)); "
        "print('breadth-panel:', h.count('breadth-panel'))"],
        capture_output=True, text=True)
    print(r2.stdout.strip())
    if r2.returncode != 0:
        print(r2.stderr[:200])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
