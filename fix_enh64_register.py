"""
MERDIAN ENH-64 register close-out. Track C (docs-only).

Flips ENH-64 Status field PROPOSED -> COMPLETE and adds a sub-rule
disposition breakdown with commit references.

Sub-rule 1: COMPLETE (pre-existing in detect_ict_patterns.py before
this session - compute_sequence_features + assign_tier).
Sub-rule 2: COMPLETE (commit 3362b8f - BEAR_OB AFTNOON hard skip).
Sub-rule 3: COMPLETE (commit 3362b8f - BULL_FVG LOW_IV skip).
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


# Match the ENH-64 Status line -- first line of its table body.
OLD_LINE = "| Status | **PROPOSED** |\n| Added | 2026-04-19 |\n| Priority | MEDIUM-HIGH - tier classifier becomes evidence-driven |"

NEW_LINE = (
    "| Status | **COMPLETE** - 2026-04-19 |\n"
    "| Completed | 2026-04-19 (commit 3362b8f, code); sub-rule 1 pre-existing |\n"
    "| Sub-rule 1 | COMPLETE - compute_sequence_features + assign_tier already live in detect_ict_patterns.py before this session. Tier promotion on MOM_YES + IMP_WEK + time zone. |\n"
    "| Sub-rule 2 | COMPLETE - BEAR_OB AFTNOON -> SKIP (commit 3362b8f). |\n"
    "| Sub-rule 3 | COMPLETE - BULL_FVG + atm_iv < LOW_IV_THRESHOLD -> SKIP (commit 3362b8f). Register proposal said TIER3 downgrade; adjusted to SKIP at build time because module tier vocabulary is TIER1/TIER2/SKIP (no TIER3). 0% WR N=23 warrants hard skip. |\n"
    "| Added | 2026-04-19 |\n"
    "| Priority | MEDIUM-HIGH - tier classifier becomes evidence-driven |"
)


def apply_patch(text: str) -> str:
    if "COMPLETE - 2026-04-19 |\n| Completed | 2026-04-19 (commit 3362b8f" in text:
        raise RuntimeError("ENH-64 register already flipped to COMPLETE.")
    if OLD_LINE not in text:
        raise RuntimeError(
            "ENH-64 register PROPOSED line not found. Either already patched "
            "or register layout diverged from baseline."
        )
    if text.count(OLD_LINE) != 1:
        raise RuntimeError(
            f"ENH-64 PROPOSED line matched {text.count(OLD_LINE)} times; "
            "refusing ambiguous patch."
        )
    return text.replace(OLD_LINE, NEW_LINE, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--enh-register",
        default="docs/registers/MERDIAN_Enhancement_Register_v7.md",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax: {e}", file=sys.stderr)
        return 1

    p = Path(args.enh_register)
    if not p.exists():
        print(f"FAIL: not found: {p.resolve()}", file=sys.stderr)
        return 2

    original = p.read_text(encoding="utf-8")

    try:
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 3

    # Post-patch checks
    for needle, label in [
        ("| Sub-rule 1 | COMPLETE", "sub-rule 1 line"),
        ("| Sub-rule 2 | COMPLETE - BEAR_OB AFTNOON", "sub-rule 2 line"),
        ("| Sub-rule 3 | COMPLETE - BULL_FVG", "sub-rule 3 line"),
        ("commit 3362b8f", "commit reference"),
    ]:
        if needle not in patched:
            print(f"FAIL: post-patch check missing: {label}", file=sys.stderr)
            return 4

    print(f"target:   {p.resolve()}")
    print(f"mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:   {'off' if args.no_backup else 'on'}")
    print(f"size:     {len(original)} bytes -> {len(patched)} bytes (+{len(patched)-len(original)})")
    print()
    print("Edit:")
    print("  [ENH-64] Status PROPOSED -> COMPLETE (sub-rules 1/2/3 disposition + commit 3362b8f ref)")

    if args.dry_run:
        print()
        print("DRY RUN - nothing written.")
        return 0

    if not args.no_backup:
        backup = p.with_suffix(p.suffix + ".pre_enh64_close.bak")
        shutil.copy2(p, backup)
        print(f"backup:   {backup.name}")

    p.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
