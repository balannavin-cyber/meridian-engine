#!/usr/bin/env python3
"""
patch_expiry_fix.py  v2
Simpler, more robust patcher for nearest_expiry fix.
Restores from .bak first — safe to rerun.

Usage:
    python patch_expiry_fix.py
    Run from C:\\GammaEnginePython
"""

import os
import re
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TARGETS = [
    "experiment_2_options_pnl.py",
    "experiment_2b_futures_vs_options.py",
    "experiment_2c_pyramid_entry.py",
    "experiment_2c_v2_judas.py",
    "experiment_5_vix_stress.py",
    "experiment_8_sequence.py",
    "experiment_10c_mtf_pnl.py",
    "portfolio_simulation.py",
    "portfolio_simulation_v2.py",
    "experiment_14_session_pyramid.py",
    "experiment_14b_session_pyramid_v2.py",
]

IMPORT_TO_ADD = "from merdian_utils import build_expiry_index_simple, nearest_expiry_db"


def patch_file(filepath):
    filename = os.path.basename(filepath)

    if not os.path.exists(filepath):
        print(f"  SKIP {filename} — not found")
        return False

    # Restore from bak for clean slate
    bak = filepath + ".bak"
    if os.path.exists(bak):
        shutil.copy2(bak, filepath)
    else:
        shutil.copy2(filepath, bak)

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out           = []
    import_added  = False
    skip_func     = False

    i = 0
    while i < len(lines):
        line     = lines[i]
        stripped = line.rstrip()

        # Add import after last import block
        if not import_added:
            is_imp      = stripped.startswith("import ") or stripped.startswith("from ")
            next_strip  = lines[i+1].strip() if i+1 < len(lines) else ""
            next_is_imp = next_strip.startswith("import ") or next_strip.startswith("from ")
            if is_imp and not next_is_imp:
                out.append(line)
                out.append(IMPORT_TO_ADD + "\n")
                import_added = True
                i += 1
                continue

        # Skip EXPIRY_WD line
        if stripped.startswith("EXPIRY_WD"):
            i += 1
            continue

        # Skip nearest_expiry() function definition block
        if stripped.startswith("def nearest_expiry("):
            skip_func = True
            i += 1
            continue

        if skip_func:
            if stripped == "" or stripped.startswith("#"):
                i += 1
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                skip_func = False
                # fall through — process this line normally
            else:
                i += 1
                continue

        # Insert expiry_idx build after "for symbol in [..." line
        if re.search(r'for\s+symbol\s+in\s+\[', stripped):
            out.append(line)
            # Determine body indentation from next non-blank line
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                body_ind   = len(lines[j]) - len(lines[j].lstrip())
                indent_str = " " * body_ind
                out.append(f"{indent_str}expiry_idx = build_expiry_index_simple(sb, inst[symbol])\n")
            i += 1
            continue

        # Replace nearest_expiry(X, anything) calls
        if "nearest_expiry(" in line:
            line = re.sub(
                r'nearest_expiry\(([^,]+),\s*[^)]+\)',
                r'nearest_expiry_db(\1, expiry_idx)',
                line
            )

        out.append(line)
        i += 1

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(out)

    content = "".join(out)
    checks = {
        "import added":       IMPORT_TO_ADD in content,
        "db call present":    "nearest_expiry_db(" in content,
        "old call gone":      "nearest_expiry(td, symbol)" not in content
                              and "nearest_expiry(d, symbol)" not in content,
        "expiry_idx built":   "expiry_idx = build_expiry_index_simple" in content,
    }
    ok = all(checks.values())
    tag = "OK" if ok else "ISSUES"
    print(f"  {filename}: [{tag}]")
    if not ok:
        for k, v in checks.items():
            if not v:
                print(f"    FAIL: {k}")
    return ok


def main():
    print("=" * 70)
    print("  MERDIAN Expiry Fix Patcher v2")
    print("  Restores from .bak then patches clean")
    print("=" * 70)

    if not os.path.exists(os.path.join(BASE_DIR, "merdian_utils.py")):
        print("ERROR: merdian_utils.py not found")
        return

    ok = issues = 0
    for f in TARGETS:
        result = patch_file(os.path.join(BASE_DIR, f))
        if result:
            ok += 1
        else:
            issues += 1

    print()
    print(f"  {ok} clean | {issues} issues")
    if issues == 0:
        print()
        print("  Smoke test:")
        print("  python experiment_14_session_pyramid.py")


if __name__ == "__main__":
    main()
