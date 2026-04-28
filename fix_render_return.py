#!/usr/bin/env python3
"""Fix render() — add _page.replace and return _page after the f-string."""
import shutil, subprocess, sys
from pathlib import Path

TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.bak_render_fix")

def main():
    lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)

    # Find the line with _page = f"""<!DOCTYPE html>
    page_line = None
    for i, line in enumerate(lines):
        if '_page = f"""<!DOCTYPE html>' in line:
            page_line = i
            break

    if page_line is None:
        print("ERROR: _page assignment not found")
        return 1

    print(f"Found _page assignment at line {page_line+1}")

    # Find the closing triple-quote of this f-string
    # It will be a line containing just '"""' after page_line
    close_line = None
    for i in range(page_line + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped == '"""':
            close_line = i
            print(f"Found closing triple-quote at line {i+1}")
            break

    if close_line is None:
        print("ERROR: closing triple-quote not found")
        return 1

    # Check if _page.replace already exists right after
    next_meaningful = close_line + 1
    while next_meaningful < len(lines) and lines[next_meaningful].strip() == "":
        next_meaningful += 1

    if "_page.replace" in lines[next_meaningful]:
        print("Fix already applied.")
        return 0

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    # Insert after the closing triple-quote
    lines.insert(close_line + 1, '    _page = _page.replace("%%BREADTH_PANEL%%", _breadth_html)\n')
    lines.insert(close_line + 2, '    return _page\n')
    print(f"Inserted _page.replace + return at lines {close_line+2}–{close_line+3}")

    TARGET.write_text("".join(lines), encoding="utf-8")

    # Syntax check
    r = subprocess.run([sys.executable, "-c",
        f"import ast; ast.parse(open(r'{TARGET}').read()); print('Syntax OK')"],
        capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(f"SYNTAX ERROR:\n{r.stderr}")
        shutil.copy2(BACKUP, TARGET)
        return 1

    # Render test
    r2 = subprocess.run([sys.executable, "-c",
        "import merdian_signal_dashboard as d; h=d.render(); "
        "print('type:', type(h).__name__); "
        "print('breadth-panel count:', h.count('breadth-panel') if h else 0); "
        "print('literal placeholder:', '%%BREADTH' in h if h else 'n/a')"],
        capture_output=True, text=True)
    print(r2.stdout.strip())
    if r2.stderr and "Error" in r2.stderr:
        print("STDERR:", r2.stderr[:300])

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
