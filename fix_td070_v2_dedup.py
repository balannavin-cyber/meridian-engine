#!/usr/bin/env python3
r"""
fix_td070_v2_dedup.py

TD-070 v2 — fix duplicate-zone defect surfaced during Session 21 live rebuild.

Background:
  TD-070 v1 introduced 8-week unbreached-anchor lookback in detect_weekly_zones().
  When two consecutive impulse weeks find the SAME unbreached opposing anchor,
  both produce an OB zone dict with identical
    (symbol, timeframe, pattern_type, source_bar_date, zone_high, zone_low)
  -- which is exactly upsert_zones()'s ON CONFLICT key. Postgres rejects the
  batch with error 21000 ('cannot affect row a second time').

  Live rebuild on 2026-05-06 18:07 IST hit this on both NIFTY and SENSEX W
  upserts. 0 W zones written. TD-071 expire pass still fired correctly.

Fix:
  1. Add module-level helper _dedup_zones_by_conflict_key(zones) that walks
     the zones list and collapses duplicates (matched on conflict key) to
     the entry with the earliest valid_from.
  2. Call it at the end of detect_weekly_zones() just before return.

Rationale for "earliest valid_from":
  Zone exists from the moment the first impulse confirms it. Subsequent
  impulses are re-confirmations, not new zones. recheck_breached_zones()
  runs every 08:45 IST and updates status; valid_to bounding from earliest
  impulse is acceptable since fresh runs re-detect with new valid_to as
  long as anchor remains unbreached.

Stacked-patch context:
  - Canonical build_ict_htf_zones.py already has TD-070 v1 + TD-071 applied.
  - This patch adds the dedup helper. Anchors used here target the existing
    TD-070 v1 code blocks. No collision with TD-071 (which patched main()
    and expire_old_zones()).

v3 patch canon:
  - read_bytes() + decode('utf-8-sig') for BOM
  - normalize CRLF -> LF before anchor match
  - ast.parse() validate before write
  - idempotency guard (TD070V2_PATCH_MARKER)
  - write_bytes(text.encode(enc)) to preserve LF

Usage:
    python fix_td070_v2_dedup.py [--in PATH] [--out PATH] [--check]

Exit codes:
    0  success / already patched
    2  source not found
    3  anchor blocks not found
    4  ast.parse failed
    5  other
"""

from __future__ import annotations
import argparse
import ast
import sys
from pathlib import Path

DEFAULT_IN = r"C:\GammaEnginePython\build_ict_htf_zones.py"

TD070V2_PATCH_MARKER = "_dedup_zones_by_conflict_key"

# ---------- Anchor 1: helper insertion point ----------
# Insert the new helper immediately after _find_unbreached_anchor's closing
# `return None` and before `def detect_weekly_zones(`.

OLD_HELPER_END_AND_DETECT_START = '''\
    return None


def detect_weekly_zones(weekly_bars, symbol):
'''

NEW_HELPER_END_AND_DETECT_START = '''\
    return None


def _dedup_zones_by_conflict_key(zones):
    """Dedup zones list by the upsert ON CONFLICT key.

    TD-070 v2 (Session 21, 2026-05-06): when multiple impulse weeks find
    the same unbreached anchor via _find_unbreached_anchor(), both produce
    OB zones with identical (symbol, timeframe, pattern_type,
    source_bar_date, zone_high, zone_low). upsert_zones() ON CONFLICT
    matches that exact key, so the batched upsert fails with Postgres 21000
    (cannot affect row a second time).

    Resolution: collapse duplicates to the entry with the earliest
    valid_from. Zone is "published" the moment the first impulse confirms
    it; subsequent impulses are re-confirmations of the same zone.
    """
    seen = {}
    for z in zones:
        key = (
            z["symbol"],
            z["timeframe"],
            z["pattern_type"],
            z["source_bar_date"],
            z["zone_high"],
            z["zone_low"],
        )
        if key not in seen or z["valid_from"] < seen[key]["valid_from"]:
            seen[key] = z
    return list(seen.values())


def detect_weekly_zones(weekly_bars, symbol):
'''

# ---------- Anchor 2: call dedup at end of detect_weekly_zones ----------
# detect_weekly_zones ends with FVG block then `return zones`. The `    return zones`
# at function end is the call site. Need to identify it uniquely. The function
# has only one `return zones` statement at module-level indentation 4-space.

# To make the anchor unique, capture the last bit of the FVG block + return.
OLD_DETECT_WEEKLY_TAIL = '''\
            # === S1.a FIX: BEAR_FVG ===
            # 3-bar structure: two_prev low > curr high, with curr displacing down.
            # The FVG is the gap between curr high and two_prev low.
            if two_prev["low"] > curr["high"]:
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

    return zones
'''

NEW_DETECT_WEEKLY_TAIL = '''\
            # === S1.a FIX: BEAR_FVG ===
            # 3-bar structure: two_prev low > curr high, with curr displacing down.
            # The FVG is the gap between curr high and two_prev low.
            if two_prev["low"] > curr["high"]:
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

    # TD-070 v2 (Session 21): dedup by upsert conflict key. Multiple impulse
    # weeks finding the same unbreached anchor produce duplicate OB rows
    # that crash the batched upsert (Postgres 21000). See helper docstring.
    zones = _dedup_zones_by_conflict_key(zones)

    return zones
'''

# ---------- Patch driver ----------


def _read_source(path: Path) -> tuple[str, str]:
    if not path.is_file():
        print(f"[ERROR] source not found: {path}", file=sys.stderr)
        sys.exit(2)
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    enc = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    text_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    return text_lf, enc


def _is_already_patched(text: str) -> bool:
    return TD070V2_PATCH_MARKER in text


def _verify_anchors(text: str) -> None:
    checks = [
        ("OLD_HELPER_END_AND_DETECT_START", OLD_HELPER_END_AND_DETECT_START),
        ("OLD_DETECT_WEEKLY_TAIL", OLD_DETECT_WEEKLY_TAIL),
    ]
    for name, anchor in checks:
        n = text.count(anchor)
        if n != 1:
            print(f"[ERROR] anchor {name} must appear exactly once, "
                  f"found {n}.", file=sys.stderr)
            sys.exit(3)


def _apply_patch(text: str) -> str:
    text = text.replace(OLD_HELPER_END_AND_DETECT_START,
                        NEW_HELPER_END_AND_DETECT_START, 1)
    text = text.replace(OLD_DETECT_WEEKLY_TAIL,
                        NEW_DETECT_WEEKLY_TAIL, 1)
    return text


def _validate_python(text: str) -> None:
    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"[ERROR] ast.parse failed on patched text: {e}",
              file=sys.stderr)
        sys.exit(4)


def main() -> int:
    p = argparse.ArgumentParser(description="TD-070 v2 dedup patch")
    p.add_argument("--in",  dest="src",  default=DEFAULT_IN,
                   help=f"source file (default: {DEFAULT_IN})")
    p.add_argument("--out", dest="dst",  default=None,
                   help="output path (default: <src>_PATCHED_TD070V2.py)")
    p.add_argument("--check", action="store_true",
                   help="validate only; do not write")
    args = p.parse_args()

    src = Path(args.src)
    if args.dst is None:
        dst = src.with_name(src.stem + "_PATCHED_TD070V2.py")
    else:
        dst = Path(args.dst)

    text_lf, enc = _read_source(src)

    if _is_already_patched(text_lf):
        print(f"[OK] already patched ({TD070V2_PATCH_MARKER!r} present): "
              f"{src}")
        return 0

    _verify_anchors(text_lf)
    patched = _apply_patch(text_lf)

    if not _is_already_patched(patched):
        print("[ERROR] post-patch idempotency marker missing.",
              file=sys.stderr)
        return 5
    if OLD_HELPER_END_AND_DETECT_START in patched:
        print("[ERROR] old helper anchor still present.", file=sys.stderr)
        return 5
    if OLD_DETECT_WEEKLY_TAIL in patched:
        print("[ERROR] old detect_weekly_zones tail still present.",
              file=sys.stderr)
        return 5

    _validate_python(patched)

    if args.check:
        print("[OK] check: anchors found, patch would apply, ast.parse OK.")
        return 0

    dst.write_bytes(patched.encode(enc.replace("-sig", "")))
    print(f"[OK] wrote {dst}")
    print(f"     bytes:    {len(patched.encode('utf-8')):,}")
    print(f"     encoding: {enc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
