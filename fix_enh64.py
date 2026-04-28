"""
MERDIAN ENH-64 (sub-rules 2+3) patch - detect_ict_patterns.py
Track A, not BREAKING. ASCII-only source to avoid encoding issues.

Sub-rule 2 - BEAR_OB AFTNOON hard skip (-24.7% exp, 17% WR, Exp 8)
Sub-rule 3 - BULL_FVG LOW_IV skip (0% WR N=23, Exp 5)

Sub-rule 1 (sequence features -> tier) is already live.
"""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import sys
from pathlib import Path


# Anchor 1: BEAR_OB block start up to first return "TIER2" just before
# the blank line separating BEAR_OB from BULL_OB.
BEAR_ANCHOR = (
    '    if pattern_type == "BEAR_OB":\n'
    '        if imp_str:\n'
    '            return "SKIP"\n'
    '        if mom_yes and tz_label == "MORNING":\n'
    '            return "TIER1"\n'
    '        return "TIER2"\n'
)

BEAR_REPLACEMENT = (
    '    if pattern_type == "BEAR_OB":\n'
    '        # ENH-64 sub-rule 2: BEAR_OB AFTNOON hard skip.\n'
    '        # -24.7% exp, 17% WR (Exp 8 / Signal Rule Book v1.1 Rule 1).\n'
    '        # Time-based skip takes precedence over impulse-based tiering.\n'
    '        if tz_label == "AFTNOON":\n'
    '            return "SKIP"\n'
    '        if imp_str:\n'
    '            return "SKIP"\n'
    '        if mom_yes and tz_label == "MORNING":\n'
    '            return "TIER1"\n'
    '        return "TIER2"\n'
)


# Anchor 2: the BULL_FVG / JUDAS_BULL fall-through -- last 2 lines of the
# function. We match them by their unique content and inject the FVG
# LOW_IV check before the final `return "TIER2"`.
FVG_ANCHOR = (
    '    # BULL_FVG and JUDAS_BULL\n'
    '    return "TIER2"\n'
)

FVG_REPLACEMENT = (
    '    # BULL_FVG and JUDAS_BULL\n'
    '    # ENH-64 sub-rule 3: BULL_FVG LOW_IV skip.\n'
    '    # 0% WR N=23, -14.3% exp (Exp 5).\n'
    '    if pattern_type == "BULL_FVG" and atm_iv is not None and atm_iv < LOW_IV_THRESHOLD:\n'
    '        return "SKIP"\n'
    '    return "TIER2"\n'
)


def apply_patch(text: str) -> str:
    # Refuse double-patch (ENH-59)
    if "ENH-64 sub-rule 2: BEAR_OB AFTNOON hard skip" in text:
        raise RuntimeError("ENH-64 already applied. Refusing to double-patch.")

    if BEAR_ANCHOR not in text:
        raise RuntimeError(
            "ENH-64 BEAR_OB anchor not found. Expected BEAR_OB branch of "
            "assign_tier() in detect_ict_patterns.py."
        )
    if text.count(BEAR_ANCHOR) != 1:
        raise RuntimeError(
            f"ENH-64 BEAR_OB anchor matched "
            f"{text.count(BEAR_ANCHOR)} times; refusing ambiguous patch."
        )

    if FVG_ANCHOR not in text:
        raise RuntimeError(
            "ENH-64 FVG anchor not found. Expected BULL_FVG/JUDAS_BULL "
            "fall-through block."
        )
    if text.count(FVG_ANCHOR) != 1:
        raise RuntimeError(
            f"ENH-64 FVG anchor matched "
            f"{text.count(FVG_ANCHOR)} times; refusing ambiguous patch."
        )

    text = text.replace(BEAR_ANCHOR, BEAR_REPLACEMENT, 1)
    text = text.replace(FVG_ANCHOR, FVG_REPLACEMENT, 1)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="detect_ict_patterns.py")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    # ENH-59: self-syntax
    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax: {e}", file=sys.stderr)
        return 1

    target = Path(args.target)
    if not target.exists():
        print(f"FAIL: target not found: {target.resolve()}", file=sys.stderr)
        return 2

    original = target.read_text(encoding="utf-8")

    try:
        ast.parse(original)
    except SyntaxError as e:
        print(f"FAIL: target has existing SyntaxError: {e}", file=sys.stderr)
        return 3

    try:
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 4

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"FAIL: patched file has SyntaxError: {e}", file=sys.stderr)
        return 5

    # Post-patch checks
    for needle in [
        "ENH-64 sub-rule 2: BEAR_OB AFTNOON hard skip",
        "ENH-64 sub-rule 3: BULL_FVG LOW_IV skip",
        'if tz_label == "AFTNOON":\n            return "SKIP"',
        'if pattern_type == "BULL_FVG" and atm_iv is not None and atm_iv < LOW_IV_THRESHOLD:',
    ]:
        if needle not in patched:
            print(f"FAIL: post-patch check missing: {needle[:60]}...", file=sys.stderr)
            return 6

    print(f"target:   {target.resolve()}")
    print(f"mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:   {'off' if args.no_backup else 'on'}")
    print(f"size:     {len(original)} bytes -> {len(patched)} bytes (+{len(patched)-len(original)})")
    print()
    print("Edits:")
    print("  [ENH-64 sub-rule 2] BEAR_OB AFTNOON -> SKIP")
    print("  [ENH-64 sub-rule 3] BULL_FVG + atm_iv < 12 -> SKIP")

    if args.dry_run:
        print()
        print("DRY RUN - nothing written.")
        return 0

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre_enh64.bak")
        shutil.copy2(target, backup)
        print(f"backup:   {backup.name}")

    target.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
