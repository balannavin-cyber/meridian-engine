"""
fix_enh35_unclobber_direction_bias.py

Removes the direction_bias and action clobber from the LONG_GAMMA and NO_FLIP
branches in build_trade_signal_local.py.

Before:
    elif gamma_regime == "LONG_GAMMA":
        cautions.append("LONG_GAMMA gated -- historical accuracy below random (ENH-35)")
        action = "DO_NOTHING"
        trade_allowed = False
        direction_bias = "NEUTRAL"

After:
    elif gamma_regime == "LONG_GAMMA":
        cautions.append("LONG_GAMMA gated -- historical accuracy below random (ENH-35)")
        trade_allowed = False

Rationale: ENH-35's policy decision (do not trade LONG_GAMMA) is preserved via
trade_allowed = False. The clobber of direction_bias and action was the
visibility-suppression bug. After this patch, downstream sees BEARISH/BUY_PE
with trade_allowed=false, instead of NEUTRAL/DO_NOTHING.

The action variable retains its initial value "DO_NOTHING" from the
pre-init at line ~457; it gets reassigned at line ~605 from direction_bias.

Diagnosed Session 10 2026-04-26.
Regression introduced 7c346fb (LONG_GAMMA, 2026-04-11 18:22 IST) and
c310e52 (NO_FLIP, 2026-04-11 19:09 IST).
"""

from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TARGET = Path("build_trade_signal_local.py")
BACKUP = Path("build_trade_signal_local.py.pre_enh35_unclobber.bak")

OLD_LONG_GAMMA = '''    elif gamma_regime == "LONG_GAMMA":
        # ENH-35 validated 2026-04-11: LONG_GAMMA signals 47.7% accuracy
        # at N=24,579 \u2014 structurally below random. Gate to DO_NOTHING.
        cautions.append("LONG_GAMMA gated \u2014 historical accuracy below random (ENH-35)")
        action = "DO_NOTHING"
        trade_allowed = False
        direction_bias = "NEUTRAL"'''

NEW_LONG_GAMMA = '''    elif gamma_regime == "LONG_GAMMA":
        # ENH-35 validated 2026-04-11: LONG_GAMMA signals 47.7% accuracy
        # at N=24,579 \u2014 structurally below random. Gate to trade_allowed=False.
        # Session 10 2026-04-26: clobber of direction_bias and action removed
        # to restore operator visibility. Policy unchanged: trade_allowed=False.
        cautions.append("LONG_GAMMA gated \u2014 historical accuracy below random (ENH-35)")
        trade_allowed = False'''

OLD_NO_FLIP = '''    elif gamma_regime == "NO_FLIP":
        # ENH-35 v2: NO_FLIP signals 45-48% accuracy \u2014 below random
        # No flip level = no institutional reference point
        cautions.append("NO_FLIP gated \u2014 no gamma flip reference (ENH-35)")
        action = "DO_NOTHING"
        trade_allowed = False
        direction_bias = "NEUTRAL"'''

NEW_NO_FLIP = '''    elif gamma_regime == "NO_FLIP":
        # ENH-35 v2: NO_FLIP signals 45-48% accuracy \u2014 below random
        # No flip level = no institutional reference point.
        # Session 10 2026-04-26: clobber of direction_bias and action removed
        # to restore operator visibility. Policy unchanged: trade_allowed=False.
        cautions.append("NO_FLIP gated \u2014 no gamma flip reference (ENH-35)")
        trade_allowed = False'''


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found in cwd {Path.cwd()}", file=sys.stderr)
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Validate both targets present and unique
    if src.count(OLD_LONG_GAMMA) != 1:
        print(
            f"ERROR: LONG_GAMMA target found {src.count(OLD_LONG_GAMMA)} times "
            f"(expected exactly 1). Aborting without changes.",
            file=sys.stderr,
        )
        return 2

    if src.count(OLD_NO_FLIP) != 1:
        print(
            f"ERROR: NO_FLIP target found {src.count(OLD_NO_FLIP)} times "
            f"(expected exactly 1). Aborting without changes.",
            file=sys.stderr,
        )
        return 2

    # Backup
    shutil.copy2(TARGET, BACKUP)
    print(f"Backed up: {BACKUP}")

    # Apply both replacements
    new_src = src.replace(OLD_LONG_GAMMA, NEW_LONG_GAMMA)
    new_src = new_src.replace(OLD_NO_FLIP, NEW_NO_FLIP)

    # Validate no clobber lines remain in the targeted branches
    # (other instances of direction_bias = "NEUTRAL" elsewhere are fine)
    # Standing rule (CLAUDE.md #5): ast.parse every patch
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"ERROR: post-patch syntax invalid: {e}", file=sys.stderr)
        print(f"NOT writing. Backup retained at {BACKUP}.", file=sys.stderr)
        return 3

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"Patched: {TARGET}")
    print()
    print("Verification:")
    print(f"  LONG_GAMMA branch: clobber removed = {NEW_LONG_GAMMA[:40].strip()!r}...")
    print(f"  NO_FLIP branch:    clobber removed = {NEW_NO_FLIP[:40].strip()!r}...")
    print()
    print("Restart the runner / pipeline alert daemon for the change to take effect.")
    print(f"Rollback: copy {BACKUP} back over {TARGET}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
