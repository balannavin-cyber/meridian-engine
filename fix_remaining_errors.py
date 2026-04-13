#!/usr/bin/env python3
"""
fix_remaining_errors.py
Fixes three remaining issues:
1. compute_dte in experiment_2b and experiment_10c
2. Broken f-strings in build_ict_htf_zones.py
Run from C:\\GammaEnginePython
"""
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))

def fix_compute_dte(filename):
    path = os.path.join(BASE, filename)
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Match any form of compute_dte that uses EXPIRY_WD
    pattern = re.compile(
        r'def compute_dte\(\w+, symbol\):\s*\n\s*return \(EXPIRY_WD\[symbol\] - \w+\.weekday\(\)\) % 7'
    )
    if pattern.search(content):
        content = pattern.sub(
            'def compute_dte(td, expiry_idx):\n'
            '    ed = nearest_expiry_db(td, expiry_idx)\n'
            '    return (ed - td).days if ed else 0',
            content
        )
        # Also fix call sites
        content = re.sub(r'compute_dte\((\w+), symbol\)', r'compute_dte(\1, expiry_idx)', content)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        remaining = "EXPIRY_WD" in content
        print(f"  {filename}: fixed {'(EXPIRY_WD still present!)' if remaining else 'OK'}")
    else:
        print(f"  {filename}: pattern not found - checking for EXPIRY_WD...")
        if "EXPIRY_WD" in content:
            # Find it manually
            for i, line in enumerate(content.splitlines(), 1):
                if "EXPIRY_WD" in line:
                    print(f"    Line {i}: {line.strip()}")


def fix_htf_zones():
    path = os.path.join(BASE, "build_ict_htf_zones.py")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Fix broken f-strings caused by newlines inside them
    # Pattern: log(f"\nSomething {var}") -> log(f"Something {var}")
    fixes = [
        ('log(f"\nDone -- {total_written} total zones written to ict_htf_zones")',
         'log(f"Done -- {total_written} total zones written to ict_htf_zones")'),
        ('log("\nVerify:")',
         'log("Verify:")'),
        ('log(f"\n-- {symbol} ---")',
         'log(f"-- {symbol} ---")'),
    ]

    changed = 0
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            changed += 1

    # Also catch any remaining newline-broken f-strings
    # Pattern: log(f"\n...") -> log(f"...")
    content = re.sub(r'log\(f"\s*\n\s*([^"]+)"\)', r'log(f"\1")', content)
    content = re.sub(r'log\("\s*\n\s*([^"]+)"\)', r'log("\1")', content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  build_ict_htf_zones.py: {changed} direct fixes applied")

    # Verify no syntax errors
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", path],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  build_ict_htf_zones.py: syntax OK")
    else:
        print(f"  build_ict_htf_zones.py: SYNTAX ERROR: {result.stderr}")


print("Fixing remaining errors...")
fix_compute_dte("experiment_2b_futures_vs_options.py")
fix_compute_dte("experiment_10c_mtf_pnl.py")
fix_htf_zones()
print("Done.")
