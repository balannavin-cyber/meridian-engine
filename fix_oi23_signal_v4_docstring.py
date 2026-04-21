"""
OI-23 fix: MERDIAN_SIGNAL_V4 docstring/code default drift.

Code (line 86):
    SIGNAL_V4_ENABLED = os.getenv("MERDIAN_SIGNAL_V4", "1").strip() == "1"
Default = "1" (V4 on). Flipped from "0" post-ENH-53/55 validation
(commit e986cbb per update_registers_enh5355.py).

Comment block (lines 59-64) still says default is off and the
shadow-session lead-in is pending. Both are stale.

Fix: rewrite the Flag block to match current state. Keep the rollback
path visible so the escape hatch stays obvious.
"""
import ast
import sys
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\build_trade_signal_local.py")

OLD_BLOCK = '''# Flag: MERDIAN_SIGNAL_V4
#   "1"        -> V4 logic (ENH-53 + ENH-55)
#   unset / 0  -> V3 legacy (bit-identical to prior behaviour,
#                including known quirks)
# Default is off. Enable explicitly for shadow sessions. Flip
# default only after 5 clean shadow sessions per Change Protocol.'''

NEW_BLOCK = '''# Flag: MERDIAN_SIGNAL_V4
#   "1" (default) -> V4 logic (ENH-53 + ENH-55)
#   "0"           -> V3 legacy (bit-identical to prior behaviour,
#                    including known quirks) -- hot-rollback escape hatch
# Default flipped to "1" post-validation (commit e986cbb) after V4
# cleared the 5-session shadow gate per Change Protocol. V3 path
# retained for emergency rollback; set MERDIAN_SIGNAL_V4=0 in .env
# and restart the runner to revert without a code change.
# OI-23 closed 2026-04-22: prior docstring said default was "off";
# code has defaulted to "1" since e986cbb. Comment now matches code.'''


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    if OLD_BLOCK not in src:
        print("ERROR: comment block not found verbatim. Aborting, no file written.")
        return 2

    if src.count(OLD_BLOCK) != 1:
        print(f"ERROR: comment block found {src.count(OLD_BLOCK)} times, expected 1. Aborting.")
        return 3

    new_src = src.replace(OLD_BLOCK, NEW_BLOCK)

    # V18H governance: patch scripts MUST ast.parse() validate.
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in generated source: {e}")
        return 4

    # Sanity check: code line 86 untouched.
    if 'os.getenv("MERDIAN_SIGNAL_V4", "1")' not in new_src:
        print("ERROR: code default literal missing from new source. Aborting.")
        return 5

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"OK: {TARGET} patched. OI-23 closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())