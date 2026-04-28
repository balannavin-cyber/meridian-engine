"""
Register update: ENH-63 REJECTED + ENH-65 COMPLETE (today's actual fix).

Target: docs/registers/MERDIAN_Enhancement_Register_v7.md

Edit 1: Flip ENH-63 Status PROPOSED -> REJECTED with rationale.
Edit 2: Append new ENH-65 entry after ENH-64's closing separator.

Rationale for ENH-63 rejection:
  compute_kelly_lots() in merdian_utils.py already applies IV scaling
  via estimate_lot_cost(spot, atm_iv_pct, dte_days). Higher IV ->
  higher per-lot premium estimate -> fewer lots. The proposed
  iv_size_multiplier (0.5/1.0/1.5) would layer a second IV adjustment
  on top, double-counting.

  Today's commit b2e8078 was a silent-bug repair (duplicate legacy
  Kelly block was overwriting the IV-aware V2 output for 6 days) -- not
  the ENH-63 feature. Filed as distinct ENH-65.

Per Documentation Protocol v2 Rule 5: REJECTED IDs keep their slot as
rejection record. Same pattern as ENH-54.
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


ENH63_STATUS_OLD = "| Status | **PROPOSED** |\n| Added | 2026-04-19 |\n| Priority | HIGH"

ENH63_STATUS_NEW = "| Status | **REJECTED** -- 2026-04-19 |\n| Rejection rationale | `compute_kelly_lots()` in `merdian_utils.py` (ENH-38v2, 2026-04-13) already applies IV scaling via `estimate_lot_cost(spot, atm_iv_pct, dte_days)`. Higher IV -> higher per-lot premium estimate -> fewer lots. Proposed layered multiplier would double-count IV. Today's commit `b2e8078` was a silent-bug repair (duplicate V1 block clobbering V2 output for 6 days) -- filed separately as ENH-65. |\n| Added | 2026-04-19 |\n| Priority | HIGH"


# ENH-65 insertion anchor: the final `---` separator after ENH-64's block,
# followed by blank line and `*End of v8 section.*`. We insert the new
# ENH-65 block between ENH-64's final `---` and that closing marker.

ENH65_ANCHOR_OLD = """| Could unblock | Refined Signal Rule Book v2.0 once this and ENH-63 ship. |

---

*End of v8 section.*
"""

ENH65_ANCHOR_NEW = """| Could unblock | Refined Signal Rule Book v2.0 once this and ENH-63 ship. |

---

### ENH-65: Remove duplicate Kelly-write block + cache expiry index

| Field | Detail |
|---|---|
| Status | **COMPLETE** -- 2026-04-19 |
| Completed | 2026-04-19 (commit `b2e8078`) |
| Priority | HIGH -- silent bug in production signal path |
| Discovery | Session 2026-04-19 investigation of ENH-63 scope. `detect_ict_patterns_runner.py` (436 lines) contained two Kelly-write blocks back-to-back. V2 block (ENH-38v2, commit `c78b6ea` 2026-04-13): IV-aware, calls `compute_kelly_lots(capital, tier, symbol, spot, atm_iv_pct, dte_days)`. V1 block (ENH-38, commit `26c5e72` 2026-04-11): IV-blind, calls `compute_kelly_lots(capital, tier)` positional -- triggers `CAPITAL_PER_LOT=100000` fallback. Both executed each cycle; V1 ran second and overwrote V2's lot counts. IV-scaled sizing had been dead code for 6 days. |
| Root cause | Commit `c78b6ea` (2026-04-13 session) added the V2 block by prepending without deleting V1. Dual-block layout went unnoticed because both executed without error -- result always round-number lots from V1's `CAPITAL_PER_LOT` fallback. |
| Secondary finding | V2 block called `build_expiry_index_simple(sb, inst_id)` every 5-min cycle. That helper issues 12 paginated Supabase queries per call. Runtime impact: ~1,728 queries/day/symbol for a near-static dataset (expiry calendar changes weekly, not every 5 minutes). |
| Build | Single patch `fix_enh63.py` applied to `detect_ict_patterns_runner.py`: (1) delete 85-line duplicate region (2nd Session-start block through V1 end marker); (2) add `_EXPIRY_INDEX_CACHE: dict = {}` at module scope; (3) wrap `build_expiry_index_simple` call with cache lookup keyed by `inst_id`. |
| File delta | 436 -> 370 lines (-75), 18,361 -> 15,262 bytes (-3,099). |
| Schema change | None. |
| Flag gate | None -- straight bug fix, not a toggleable feature. |
| Validation | Pre-commit: `ast.parse()` on patched file passes. Post-commit structural: 1 Session-start block (was 2), 1 V2 end marker, 0 V1 Kelly header, 3 `_EXPIRY_INDEX_CACHE` references (decl + get + set). Runtime verification: Monday 2026-04-21 09:15+ IST -- confirm `ict_zones.ict_lots_t1/t2/t3` values vary with `atm_iv_at_detection` across cycles (was constant under V1 fallback). |
| Environment | Local only. AWS shadow runner has been FAILED since 2026-04-15 -- not DEGRADED gate because AWS never ran this file in the affected window. AWS `git pull` needed before AWS shadow recovery. |
| Depends on | None. |
| Supersedes | ENH-63 (REJECTED -- the IV-scaled multiplier it proposed would have double-counted IV given ENH-38v2's existing IV-aware cost model). |

---

*End of v8 section.*
"""


def apply_patch(text: str) -> str:
    # Idempotence check
    if "ENH-65: Remove duplicate Kelly-write block" in text:
        raise RuntimeError("ENH-65 entry already present in register.")
    if "REJECTED** -- 2026-04-19 |\n| Rejection rationale" in text:
        raise RuntimeError("ENH-63 already flipped to REJECTED.")

    # Edit 1: ENH-63 status
    c = text.count(ENH63_STATUS_OLD)
    if c != 1:
        raise RuntimeError(f"ENH-63 status anchor matched {c} times (need 1).")
    text = text.replace(ENH63_STATUS_OLD, ENH63_STATUS_NEW, 1)

    # Edit 2: ENH-65 insertion
    c = text.count(ENH65_ANCHOR_OLD)
    if c != 1:
        raise RuntimeError(f"ENH-65 insertion anchor matched {c} times (need 1).")
    text = text.replace(ENH65_ANCHOR_OLD, ENH65_ANCHOR_NEW, 1)

    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target",
                    default="docs/registers/MERDIAN_Enhancement_Register_v7.md")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    # Self-syntax
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
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 3

    # Structural: ENH-65 must appear exactly once
    if patched.count("### ENH-65:") != 1:
        print(f"FAIL: ENH-65 count = {patched.count('### ENH-65:')}, expected 1",
              file=sys.stderr)
        return 4

    # ENH-63 must still have exactly one occurrence as a heading
    if patched.count("### ENH-63:") != 1:
        print("FAIL: ENH-63 heading count changed", file=sys.stderr)
        return 5

    # Rejected marker must be present exactly once for ENH-63
    rejected_markers = patched.count("**REJECTED** -- 2026-04-19")
    if rejected_markers != 1:
        print(f"FAIL: REJECTED marker count = {rejected_markers}", file=sys.stderr)
        return 6

    # "End of v8 section" must still be present exactly once
    if patched.count("*End of v8 section.*") != 1:
        print("FAIL: end-of-section marker count changed", file=sys.stderr)
        return 7

    orig_lines = original.count("\n")
    new_lines = patched.count("\n")

    print(f"target:   {target.resolve()}")
    print(f"mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:   {'off' if args.no_backup else 'on'}")
    print(f"size:     {len(original)} -> {len(patched)} bytes "
          f"({len(patched)-len(original):+d})")
    print(f"lines:    {orig_lines} -> {new_lines} ({new_lines-orig_lines:+d})")
    print()
    print("Edits:")
    print("  [1] ENH-63 Status: PROPOSED -> REJECTED (redundant with ENH-38v2)")
    print("  [2] ENH-65 entry appended: Remove duplicate Kelly block + cache expiry")

    if args.dry_run:
        print()
        print("DRY RUN - nothing written.")
        return 0

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre_enh65.bak")
        shutil.copy2(target, backup)
        print(f"backup:   {backup.name}")

    target.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
