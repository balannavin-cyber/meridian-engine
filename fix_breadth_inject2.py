#!/usr/bin/env python3
"""Fix _breadth_html literal in render() output using line-based approach."""
import shutil, subprocess, sys
from pathlib import Path

TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.bak_breadth_fix")

def main():
    lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)

    if any("%%BREADTH_PANEL%%" in l for l in lines):
        print("Placeholder already in place.")
    else:
        # Step 1: replace the bad injection line
        for i, line in enumerate(lines):
            if "_breadth_html + '" in line and "BREADTH_PANEL" not in line:
                lines[i] = line.replace(
                    "' + _breadth_html + '",
                    "%%BREADTH_PANEL%%"
                )
                print(f"Fixed injection at line {i+1}")
                break

    # Step 2: find "return f" in render() and change to _page = f
    for i, line in enumerate(lines):
        if line.strip().startswith('return f"""<!DOCTYPE html>'):
            lines[i] = line.replace('return f"""<!DOCTYPE html>', '_page = f"""<!DOCTYPE html>')
            print(f"Changed return to _page at line {i+1}")
            break

    # Step 3: find the closing triple-quote of the f-string and add replacement + return
    # Look for a line that is just '"""' after the _page = f"""
    page_start = None
    for i, line in enumerate(lines):
        if '_page = f"""<!DOCTYPE html>' in line:
            page_start = i
            break

    if page_start is None:
        print("ERROR: _page assignment not found")
        return 1

    # Find closing triple quote after page_start
    for i in range(page_start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped == '"""':
            # Check this is the right one by looking at next line
            next_line = lines[i+1].strip() if i+1 < len(lines) else ""
            if "HTTP server" in next_line or "Handler" in next_line or next_line == "" or "class Handler" in next_line:
                # Insert after this line
                if '_page.replace' not in lines[i]:
                    lines.insert(i+1, '    _page = _page.replace("%%BREADTH_PANEL%%", _breadth_html)\n')
                    lines.insert(i+2, '    return _page\n')
                    print(f"Added _page.replace + return at line {i+2}")
                    break

    TARGET.write_text("".join(lines), encoding="utf-8")

    # Verify syntax
    r = subprocess.run([sys.executable, "-c",
        f"import ast; ast.parse(open(r'{TARGET}').read()); print('Syntax OK')"],
        capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(f"SYNTAX ERROR:\n{r.stderr}")
        shutil.copy2(BACKUP, TARGET)
        return 1

    # Test render
    r2 = subprocess.run([sys.executable, "-c",
        "import merdian_signal_dashboard as d; h=d.render(); "
        "print('breadth-panel count:', h.count('breadth-panel')); "
        "print('literal _breadth_html:', '_breadth_html' in h)"],
        capture_output=True, text=True)
    print(r2.stdout.strip())
    if r2.stderr and "Error" in r2.stderr:
        print("STDERR:", r2.stderr[:300])

    return 0

if __name__ == "__main__":
    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")
    raise SystemExit(main())
