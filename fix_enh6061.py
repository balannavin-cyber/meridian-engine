"""
MERDIAN ENH-60 + ENH-61 patch — build_trade_signal_local.py
Track A, not BREAKING, default-safe.

ENH-60 — Pre-initialise `action = "DO_NOTHING"` at top of build_signal()
         before the Gamma treatment block. Eliminates UnboundLocalError
         in the options-flow confidence-modifier block on SHORT_GAMMA /
         UNKNOWN paths where pcr_regime / skew_regime / flow_regime are
         populated.

ENH-61 — Initialise `trade_allowed = True` at function top; remove the
         unconditional `trade_allowed = True` inside the DTE block.
         LONG_GAMMA / NO_FLIP gated rows now correctly retain
         trade_allowed=False through to signal_snapshots.

Applies to both V3 and V4 signal paths — no flag branching at these sites.

ENH-59 compliance: validates own AST on startup, validates target file's
AST post-edit, refuses to write if either fails.

Usage:
  python fix_enh6061.py                 # edits build_trade_signal_local.py in place
  python fix_enh6061.py --dry-run       # show what would change
  python fix_enh6061.py --target X.py   # edit a different target file
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


OLD_PRE_GAMMA = '''    if not SIGNAL_V4_ENABLED:
        if direction_bias in {"BULLISH", "BEARISH"}:
            confidence += 20.0

    # Gamma treatment
    if gamma_regime == "SHORT_GAMMA":
'''


NEW_PRE_GAMMA = '''    if not SIGNAL_V4_ENABLED:
        if direction_bias in {"BULLISH", "BEARISH"}:
            confidence += 20.0

    # ENH-60: pre-init action = "DO_NOTHING" so the options-flow
    #   confidence-modifier block below can reference `action` safely
    #   even on SHORT_GAMMA / UNKNOWN paths where the gamma-treatment
    #   block below does not assign it. Without this, ~0.3% of rows
    #   raise UnboundLocalError when pcr_regime / skew_regime /
    #   flow_regime are populated.
    # ENH-61: pre-init trade_allowed = True here (moved up from the
    #   DTE block) so LONG_GAMMA / NO_FLIP gated rows correctly retain
    #   trade_allowed=False through to signal_snapshots.
    action: str = "DO_NOTHING"
    trade_allowed: bool = True

    # Gamma treatment
    if gamma_regime == "SHORT_GAMMA":
'''


OLD_DTE = '''    # DTE gating
    # NOTE: V3 legacy. `trade_allowed = True` here overrides any
    # False set by LONG_GAMMA/NO_FLIP above. Harmless because
    # action is already DO_NOTHING for those paths. Preserved for
    # V3 bit-identical behaviour.
    trade_allowed = True
    if dte is not None:
'''


NEW_DTE = '''    # DTE gating
    # ENH-61: `trade_allowed` is initialised True at function top and
    # only ever transitions downward. LONG_GAMMA / NO_FLIP gated paths
    # now correctly retain trade_allowed=False; previously the
    # unconditional `trade_allowed = True` here overrode them.
    if dte is not None:
'''


def apply_patch(text: str) -> str:
    if OLD_PRE_GAMMA not in text:
        raise RuntimeError(
            "ENH-60 edit point not found. Expected the `not SIGNAL_V4_ENABLED` "
            "block directly followed by `# Gamma treatment`. Target file may "
            "already be patched, or may diverge from the expected V4 baseline."
        )
    if OLD_DTE not in text:
        raise RuntimeError(
            "ENH-61 edit point not found. Expected `# DTE gating` block with "
            "V3 legacy comment and `trade_allowed = True` before `if dte is not None:`. "
            "Target file may already be patched."
        )
    text = text.replace(OLD_PRE_GAMMA, NEW_PRE_GAMMA, 1)
    text = text.replace(OLD_DTE, NEW_DTE, 1)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="build_trade_signal_local.py",
                    help="target file to patch (default: ./build_trade_signal_local.py)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would change, write nothing")
    ap.add_argument("--no-backup", action="store_true",
                    help="skip .bak file (not recommended)")
    args = ap.parse_args()

    # ENH-59: validate our own AST first
    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax check: {e}", file=sys.stderr)
        return 1

    target = Path(args.target)
    if not target.exists():
        print(f"FAIL: target not found: {target.resolve()}", file=sys.stderr)
        return 2

    original = target.read_text(encoding="utf-8")

    # Pre-flight: target's existing AST must be clean
    try:
        ast.parse(original)
    except SyntaxError as e:
        print(f"FAIL: target has existing SyntaxError — refusing to patch: {e}",
              file=sys.stderr)
        return 3

    # Apply patch
    try:
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 4

    # ENH-59: validate patched AST before writing
    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"FAIL: patched file has SyntaxError — refusing to write: {e}",
              file=sys.stderr)
        return 5

    # Post-patch structural checks
    checks = [
        ('action: str = "DO_NOTHING"', "action pre-init present"),
        ('trade_allowed: bool = True', "trade_allowed pre-init present"),
        ('# ENH-60: pre-init action = "DO_NOTHING"', "ENH-60 marker comment present"),
        ('# ENH-61: `trade_allowed` is initialised True at function top', "ENH-61 marker comment present"),
    ]
    for needle, label in checks:
        if needle not in patched:
            print(f"FAIL: post-patch check — {label}", file=sys.stderr)
            return 6

    # Must NOT contain the old V3-legacy DTE reset
    if "# V3 bit-identical behaviour.\n    trade_allowed = True" in patched:
        print("FAIL: post-patch check — old DTE-block trade_allowed=True reset still present",
              file=sys.stderr)
        return 7

    # Count trade_allowed=False code sites — should be 7 (LONG_GAMMA, NO_FLIP,
    # DTE<=0, DTE<=1, ENH-55 opposition, confidence gate, session gate).
    # Note: the comment block near the top of the file also contains the
    # string "trade_allowed = False." which brings the grep count to 8.
    # We assert >=7 rather than ==7 to stay robust to comment edits.
    false_sites = patched.count("trade_allowed = False")
    if false_sites < 7:
        print(f"FAIL: expected >=7 trade_allowed=False sites, got {false_sites}",
              file=sys.stderr)
        return 8

    print(f"target:       {target.resolve()}")
    print(f"mode:         {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:       {'off' if args.no_backup else 'on'}")
    print(f"size:         {len(original)} bytes → {len(patched)} bytes "
          f"(+{len(patched)-len(original)})")
    print(f"trade_allowed=False sites: {false_sites}")
    print()
    print("Edits applied:")
    print("  [ENH-60] pre-init action = \"DO_NOTHING\" before Gamma treatment")
    print("  [ENH-61] pre-init trade_allowed = True at function top")
    print("  [ENH-61] removed unconditional trade_allowed = True in DTE block")

    if args.dry_run:
        print()
        print("DRY RUN — nothing written. Re-run without --dry-run to apply.")
        return 0

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre_enh6061.bak")
        shutil.copy2(target, backup)
        print(f"backup:       {backup.name}")

    target.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
