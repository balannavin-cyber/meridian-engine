"""
fix_bear_fvg_htf_producer.py — patch build_ict_htf_zones.py to add BEAR_FVG
detection at W and H timeframes.

Context:
  Companion to fix_bear_fvg_detection.py (which patched detect_ict_patterns.py
  for the 5m runtime detector). This patches the offline HTF producer.

Phase 1 evidence (2026-04-30, 60-day audit):
  Both NIFTY and SENSEX showed:
    - 2 W BULL_FVG zones in window (created)
    - 0 W BEAR_FVG zones in window (impossible to create — no detector)
    - 0 H BEAR_FVG zones (same reason)
    - 0 D BEAR_FVG zones EVER (TD-031; daily has no FVG detector at all,
      separate issue, NOT addressed by this patch)

Decision:
  - Detection symmetric per ICT canon (this patch).
  - Routing for BEAR_FVG = SKIP (already enforced in detect_ict_patterns.py
    assign_tier; the HTF producer only writes zone metadata, doesn't tier).
  - Daily FVG detection (BULL or BEAR) NOT added — out of scope; would be
    a speculative addition without research basis.

Key observation:
  filter_breached_zones() and recheck_breached_zones() in this file ALREADY
  handle BEAR_FVG in their pattern lists. The plumbing was anticipated; only
  the detection logic was missing. So this patch is purely additive in two
  places: detect_weekly_zones() and detect_1h_zones().

What this script changes (in C:\\GammaEnginePython\\build_ict_htf_zones.py):

  1. detect_weekly_zones() — add BEAR_FVG branch after the existing BULL_FVG
     block. Mirror the gap-detection logic with two_prev["low"] > curr["high"].

  2. detect_1h_zones() — same mirror in the 1H detector.

Idempotency:
  Marker "# BEAR_FVG_HTF_PATCH_APPLIED" near top of file. Script exits 0 if
  already applied.

Pre-state verification:
  Asserts each expected old string appears exactly once. Aborts on drift.

Backup:
  Writes build_ict_htf_zones.py.bak_pre_bear_fvg_htf before any edit.

AST validation:
  Re-parses after edits. Auto-rollback from backup on syntax error.

Run on Local Windows from C:\\GammaEnginePython:
    python fix_bear_fvg_htf_producer.py
"""

from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path

TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.bak_pre_bear_fvg_htf")
MARKER = "# BEAR_FVG_HTF_PATCH_APPLIED"


# ── Edit specifications ──────────────────────────────────────────────
# Each edit appends a BEAR_FVG block immediately after an existing BULL_FVG
# block. The "old" string is the BULL_FVG block; the "new" string is BULL_FVG
# block + BEAR_FVG block. This keeps the surrounding code untouched.

EDIT_1_OLD = '''        # ── Weekly FVG ────────────────────────────────────────────────────────
        if i >= 2:
            two_prev = weekly_bars[i - 2]
            ref = curr["open"]
            # Bullish FVG: gap between two_prev.high and curr.low
            if two_prev["high"] < curr["low"]:
                gap_pct = (curr["low"] - two_prev["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "W",
                        "pattern_type": "BULL_FVG",
                        "direction":    +1,
                        "zone_high":    curr["low"],
                        "zone_low":     two_prev["high"],
                        "valid_from":   str(valid_from),
                        "valid_to":     str(valid_to + timedelta(weeks=4)),
                        "source_bar_date": str(src_date),
                        "status":       "ACTIVE",
                    })

    return zones'''

EDIT_1_NEW = '''        # ── Weekly FVG ────────────────────────────────────────────────────────
        if i >= 2:
            two_prev = weekly_bars[i - 2]
            ref = curr["open"]
            # Bullish FVG: gap between two_prev.high and curr.low
            if two_prev["high"] < curr["low"]:
                gap_pct = (curr["low"] - two_prev["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "W",
                        "pattern_type": "BULL_FVG",
                        "direction":    +1,
                        "zone_high":    curr["low"],
                        "zone_low":     two_prev["high"],
                        "valid_from":   str(valid_from),
                        "valid_to":     str(valid_to + timedelta(weeks=4)),
                        "source_bar_date": str(src_date),
                        "status":       "ACTIVE",
                    })
            # Bearish FVG: gap between two_prev.low and curr.high (mirror of BULL_FVG)
            # Routing in detect_ict_patterns.assign_tier() returns SKIP for BEAR_FVG
            # so these zones are detected for MTF context but never auto-routed as BUY_PE.
            elif two_prev["low"] > curr["high"]:
                gap_pct = (two_prev["low"] - curr["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "W",
                        "pattern_type": "BEAR_FVG",
                        "direction":    -1,
                        "zone_high":    two_prev["low"],
                        "zone_low":     curr["high"],
                        "valid_from":   str(valid_from),
                        "valid_to":     str(valid_to + timedelta(weeks=4)),
                        "source_bar_date": str(src_date),
                        "status":       "ACTIVE",
                    })

    return zones'''

EDIT_2_OLD = '''        # 1H BULL_FVG: gap between prev-prev high and curr low
        if i >= 2:
            two_prev = completed[i - 2]
            ref = curr["open"]
            if two_prev["high"] < curr["low"]:
                gap_pct = (curr["low"] - two_prev["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "H",
                        "pattern_type": "BULL_FVG",
                        "direction":    +1,
                        "zone_high":    curr["low"],
                        "zone_low":     two_prev["high"],
                        "valid_from":   valid_from,
                        "valid_to":     valid_to,
                        "source_bar_date": src_date,
                        "status":       "ACTIVE",
                    })'''

EDIT_2_NEW = '''        # 1H BULL_FVG: gap between prev-prev high and curr low
        if i >= 2:
            two_prev = completed[i - 2]
            ref = curr["open"]
            if two_prev["high"] < curr["low"]:
                gap_pct = (curr["low"] - two_prev["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "H",
                        "pattern_type": "BULL_FVG",
                        "direction":    +1,
                        "zone_high":    curr["low"],
                        "zone_low":     two_prev["high"],
                        "valid_from":   valid_from,
                        "valid_to":     valid_to,
                        "source_bar_date": src_date,
                        "status":       "ACTIVE",
                    })
            # 1H BEAR_FVG: gap between prev-prev low and curr high (mirror)
            # Routing SKIP enforced in detect_ict_patterns.assign_tier — see ADR-004.
            elif two_prev["low"] > curr["high"]:
                gap_pct = (two_prev["low"] - curr["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "H",
                        "pattern_type": "BEAR_FVG",
                        "direction":    -1,
                        "zone_high":    two_prev["low"],
                        "zone_low":     curr["high"],
                        "valid_from":   valid_from,
                        "valid_to":     valid_to,
                        "source_bar_date": src_date,
                        "status":       "ACTIVE",
                    })'''


EDITS = [
    ("1. detect_weekly_zones() — add BEAR_FVG mirror branch", EDIT_1_OLD, EDIT_1_NEW),
    ("2. detect_1h_zones() — add BEAR_FVG mirror branch",     EDIT_2_OLD, EDIT_2_NEW),
]


def main() -> int:
    print("=" * 70)
    print("fix_bear_fvg_htf_producer.py — patching build_ict_htf_zones.py")
    print("=" * 70)

    if not TARGET.exists():
        print(f"[FATAL] {TARGET} not found in current directory.")
        print(f"        cd to C:\\GammaEnginePython and re-run.")
        return 2

    src = TARGET.read_text(encoding="utf-8")

    if MARKER in src:
        print(f"[idempotent] marker {MARKER!r} found — already patched. No changes.")
        return 0

    print("\nPre-state verification:")
    for desc, old, _ in EDITS:
        n = src.count(old)
        status = "OK" if n == 1 else f"FAIL (found {n} matches, expected 1)"
        print(f"  [{status}] {desc}")
        if n != 1:
            print(f"\n[FATAL] Edit '{desc}' cannot be applied safely.")
            print(f"        Expected exactly 1 match for the old string, found {n}.")
            print(f"        File may have been modified since this patch was authored.")
            print(f"        No changes written. Backup not created.")
            return 3

    print(f"\n[backup] writing {BACKUP}")
    shutil.copy2(TARGET, BACKUP)

    print("\nApplying edits:")
    new_src = src
    for desc, old, new in EDITS:
        new_src = new_src.replace(old, new, 1)
        print(f"  [applied] {desc}")

    # Inject idempotency marker. Insert just before "import os"
    marker_block = f"\n{MARKER}  # added by fix_bear_fvg_htf_producer.py — see ADR-004\n"
    insert_anchor = "import os"
    if insert_anchor in new_src:
        new_src = new_src.replace(insert_anchor, marker_block + insert_anchor, 1)
    else:
        new_src = new_src + "\n" + marker_block

    TARGET.write_text(new_src, encoding="utf-8")

    print("\nAST validation:")
    try:
        ast.parse(new_src)
        print("  [OK] AST parse clean")
    except SyntaxError as e:
        print(f"  [FAIL] SyntaxError: {e}")
        print(f"  [rollback] restoring from {BACKUP}")
        shutil.copy2(BACKUP, TARGET)
        print(f"  [rollback] complete. {TARGET} restored to pre-patch state.")
        return 4

    print("\n" + "=" * 70)
    print("PATCH APPLIED SUCCESSFULLY")
    print("=" * 70)
    print(f"  Modified : {TARGET}")
    print(f"  Backup   : {BACKUP}")
    print(f"  Marker   : {MARKER}")
    print()
    print("Verification suggested:")
    print()
    print("  1. Smoke test (no DB write):")
    print("     python build_ict_htf_zones.py --timeframe W --dry-run")
    print()
    print("  2. Real run for weekly (writes to ict_htf_zones):")
    print("     python build_ict_htf_zones.py --timeframe W")
    print()
    print("  3. Confirm BEAR_FVG zones exist post-run:")
    print("     # In Supabase or via psql/REST:")
    print("     # SELECT symbol, COUNT(*) FROM ict_htf_zones")
    print("     # WHERE timeframe='W' AND pattern_type='BEAR_FVG' GROUP BY symbol;")
    print()
    print("Note: BEAR_FVG zones may not appear immediately if no qualifying")
    print("      gap exists in the lookback window. The patch enables detection;")
    print("      whether zones get written depends on actual price action.")
    print()
    print("Note: Daily FVG detection (BULL or BEAR) is NOT in this patch.")
    print("      detect_daily_zones() has no FVG logic at all — separate question,")
    print("      not addressed here. TD-031 D BEAR_FVG=0 lifetime is partially")
    print("      explained by this absence.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
