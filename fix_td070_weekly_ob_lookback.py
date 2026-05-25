#!/usr/bin/env python3
r"""
fix_td070_weekly_ob_lookback.py

TD-070 — relax single-bar prior-move check in detect_weekly_zones() to an 8-week
unbreached-anchor lookback. Symmetric application to BULL_OB and BEAR_OB.

Spec (locked Session 21, 2026-05-06):
  For each weekly bar i with displacement curr_move >= +0.40% (BULL) or <= -0.40% (BEAR):
    1. Scan i-1 .. max(0, i-8) for the most recent opposing-direction bar
       (BULL_OB anchor = bearish bar, BEAR_OB anchor = bullish bar).
    2. Verify the anchor is unbreached by intervening bars K+1 .. i-1:
       BULL_OB anchor breach: any intervening low < anchor body_low (min(open, close))
       BEAR_OB anchor breach: any intervening high > anchor body_high (max(open, close))
    3. If unbreached anchor found, write OB using anchor's body. Else skip.

Backward-compat: when the prior bar IS opposing (no intervening bars to check),
behavior is identical to today.

v3 patch canon:
  - read_bytes() + decode('utf-8-sig') for BOM
  - normalize CRLF -> LF before anchor match
  - ast.parse() validate before write
  - idempotency guard
  - write_bytes(text.encode(enc)) to preserve LF (no Windows silent CRLF)
  - backup via separate _PRE_S21.py file (operator handles git)
  - emit a _PATCHED.py first; operator renames to canonical post-review.

Usage:
    python fix_td070_weekly_ob_lookback.py [--in PATH] [--out PATH] [--check]
        --in    Source path (default: C:\GammaEnginePython\build_ict_htf_zones.py)
        --out   Patched output path (default: same dir + _PATCHED.py)
        --check Validate only (parse, anchor present, idempotency); no write.

Exit codes:
    0  success / already patched (idempotent)
    2  source not found / unreadable
    3  anchor blocks not found (file content drifted)
    4  ast.parse failed on patched output
    5  other
"""

from __future__ import annotations
import argparse
import ast
import sys
import os
import shutil
from pathlib import Path

# ---------- Anchors expected in source (verbatim, for unique match) ----------

# These are the two single-bar checks we are replacing. They appear verbatim in
# the user-supplied build_ict_htf_zones.py paste from Session 21 turn.

BULL_ANCHOR = """\
        if curr_move >= OB_MIN_MOVE_PCT and prev_move < 0:
            # Bullish impulse week — prior bearish week is the OB
            zones.append({
                "symbol":       symbol,
                "timeframe":    "W",
                "pattern_type": "BULL_OB",
                "direction":    +1,
                "zone_high":    max(prev["open"], prev["close"]),
                "zone_low":     min(prev["open"], prev["close"]),
                "valid_from":   str(valid_from),
                "valid_to":     str(valid_to + timedelta(weeks=4)),  # persist 4 weeks
                "source_bar_date": str(src_date),
                "status":       "ACTIVE",
            })
"""

BEAR_ANCHOR = """\
        if curr_move <= -OB_MIN_MOVE_PCT and prev_move > 0:
            # Bearish impulse week — prior bullish week is the OB
            zones.append({
                "symbol":       symbol,
                "timeframe":    "W",
                "pattern_type": "BEAR_OB",
                "direction":    -1,
                "zone_high":    max(prev["open"], prev["close"]),
                "zone_low":     min(prev["open"], prev["close"]),
                "valid_from":   str(valid_from),
                "valid_to":     str(valid_to + timedelta(weeks=4)),
                "source_bar_date": str(src_date),
                "status":       "ACTIVE",
            })
"""

# ---------- Replacements ----------

BULL_REPLACEMENT = """\
        # TD-070: 8-week unbreached-anchor lookback for BULL_OB.
        # Find most recent bearish week in i-1 .. max(0, i-8) that is unbreached
        # by intervening weeks (no intervening low < anchor body_low).
        if curr_move >= OB_MIN_MOVE_PCT:
            anchor = _find_unbreached_anchor(weekly_bars, i, direction="BULL")
            if anchor is not None:
                zones.append({
                    "symbol":       symbol,
                    "timeframe":    "W",
                    "pattern_type": "BULL_OB",
                    "direction":    +1,
                    "zone_high":    max(anchor["open"], anchor["close"]),
                    "zone_low":     min(anchor["open"], anchor["close"]),
                    "valid_from":   str(valid_from),
                    "valid_to":     str(valid_to + timedelta(weeks=4)),  # persist 4 weeks
                    "source_bar_date": str(anchor["week_end"]),
                    "status":       "ACTIVE",
                })
"""

BEAR_REPLACEMENT = """\
        # TD-070: 8-week unbreached-anchor lookback for BEAR_OB (symmetric).
        # Find most recent bullish week in i-1 .. max(0, i-8) that is unbreached
        # by intervening weeks (no intervening high > anchor body_high).
        if curr_move <= -OB_MIN_MOVE_PCT:
            anchor = _find_unbreached_anchor(weekly_bars, i, direction="BEAR")
            if anchor is not None:
                zones.append({
                    "symbol":       symbol,
                    "timeframe":    "W",
                    "pattern_type": "BEAR_OB",
                    "direction":    -1,
                    "zone_high":    max(anchor["open"], anchor["close"]),
                    "zone_low":     min(anchor["open"], anchor["close"]),
                    "valid_from":   str(valid_from),
                    "valid_to":     str(valid_to + timedelta(weeks=4)),
                    "source_bar_date": str(anchor["week_end"]),
                    "status":       "ACTIVE",
                })
"""

# ---------- Helper insertion (module-level, before detect_weekly_zones) ----

HELPER_INSERTION_ANCHOR = "def detect_weekly_zones(weekly_bars, symbol):"

HELPER_BLOCK = """\
# TD-070 (Session 21, 2026-05-06): unbreached-anchor lookback helper.
# Spec: 8-week lookback, most-recent-opposing, body-low/body-high breach test.
TD070_LOOKBACK_WEEKS = 8


def _find_unbreached_anchor(weekly_bars, i, direction):
    \"\"\"Find the most recent unbreached opposing-direction weekly bar in the
    8-week lookback window before bar i.

    Args:
        weekly_bars: list of weekly bar dicts with open/high/low/close/week_end.
        i:           index of the impulse (current) bar in weekly_bars.
        direction:   "BULL" -> looking for bearish anchor; "BEAR" -> bullish.

    Returns:
        The anchor bar dict if found and unbreached. None otherwise.

    Breach rule (body-based, TD-070 spec):
        BULL anchor (bearish bar) is breached if ANY intervening bar K+1..i-1
            has low < anchor body_low (= min(open, close)).
        BEAR anchor (bullish bar) is breached if ANY intervening bar K+1..i-1
            has high > anchor body_high (= max(open, close)).

    Backward-compat: when the prior bar (i-1) is opposing, no intervening bars
    exist; the anchor is vacuously unbreached. Behavior matches pre-TD-070 code.
    \"\"\"
    if direction not in ("BULL", "BEAR"):
        raise ValueError(f"direction must be BULL or BEAR, got {direction!r}")

    start = max(0, i - TD070_LOOKBACK_WEEKS)
    # Walk K from i-1 down to start (most recent first).
    for k in range(i - 1, start - 1, -1):
        anchor = weekly_bars[k]

        # Filter to the right anchor direction.
        if direction == "BULL":
            is_anchor = anchor["close"] < anchor["open"]   # bearish bar
        else:  # BEAR
            is_anchor = anchor["close"] > anchor["open"]   # bullish bar

        if not is_anchor:
            continue

        # Check breach by intervening bars k+1 .. i-1 (may be empty).
        body_low  = min(anchor["open"], anchor["close"])
        body_high = max(anchor["open"], anchor["close"])
        breached = False
        for j in range(k + 1, i):
            interv = weekly_bars[j]
            if direction == "BULL":
                if interv["low"] < body_low:
                    breached = True
                    break
            else:  # BEAR
                if interv["high"] > body_high:
                    breached = True
                    break

        if not breached:
            return anchor
        # else continue scanning further back

    return None


"""


# ---------- Patch driver ----------

DEFAULT_IN  = r"C:\GammaEnginePython\build_ict_htf_zones.py"


def _read_source(path: Path) -> tuple[str, str]:
    """Return (text_LF_normalized, original_encoding_label)."""
    if not path.is_file():
        print(f"[ERROR] source not found: {path}", file=sys.stderr)
        sys.exit(2)
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    enc = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    text_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    return text_lf, enc


def _is_already_patched(text: str) -> bool:
    return "TD070_LOOKBACK_WEEKS" in text and "_find_unbreached_anchor" in text


def _verify_anchors(text: str) -> None:
    if text.count(BULL_ANCHOR) != 1:
        n = text.count(BULL_ANCHOR)
        print(f"[ERROR] BULL_OB anchor block must appear exactly once, found {n}.",
              file=sys.stderr)
        sys.exit(3)
    if text.count(BEAR_ANCHOR) != 1:
        n = text.count(BEAR_ANCHOR)
        print(f"[ERROR] BEAR_OB anchor block must appear exactly once, found {n}.",
              file=sys.stderr)
        sys.exit(3)
    if HELPER_INSERTION_ANCHOR not in text:
        print(f"[ERROR] helper insertion anchor not found: "
              f"{HELPER_INSERTION_ANCHOR!r}", file=sys.stderr)
        sys.exit(3)


def _apply_patch(text: str) -> str:
    # 1. Insert helper block before detect_weekly_zones.
    text = text.replace(
        HELPER_INSERTION_ANCHOR,
        HELPER_BLOCK + HELPER_INSERTION_ANCHOR,
        1,
    )
    # 2. Replace BULL_OB block.
    text = text.replace(BULL_ANCHOR, BULL_REPLACEMENT, 1)
    # 3. Replace BEAR_OB block.
    text = text.replace(BEAR_ANCHOR, BEAR_REPLACEMENT, 1)
    return text


def _validate_python(text: str) -> None:
    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"[ERROR] ast.parse failed on patched text: {e}", file=sys.stderr)
        sys.exit(4)


def main() -> int:
    p = argparse.ArgumentParser(description="TD-070 patch")
    p.add_argument("--in",  dest="src",  default=DEFAULT_IN,
                   help=f"source file (default: {DEFAULT_IN})")
    p.add_argument("--out", dest="dst",  default=None,
                   help="output path (default: <src>_PATCHED.py)")
    p.add_argument("--check", action="store_true",
                   help="validate only; do not write")
    args = p.parse_args()

    src = Path(args.src)
    if args.dst is None:
        dst = src.with_name(src.stem + "_PATCHED.py")
    else:
        dst = Path(args.dst)

    text_lf, enc = _read_source(src)

    if _is_already_patched(text_lf):
        print(f"[OK] already patched (TD070_LOOKBACK_WEEKS present): {src}")
        return 0

    _verify_anchors(text_lf)

    patched = _apply_patch(text_lf)

    # Sanity: must have inserted helper + replaced both blocks.
    if not _is_already_patched(patched):
        print("[ERROR] post-patch idempotency check failed (helper missing).",
              file=sys.stderr)
        return 5
    if BULL_ANCHOR in patched or BEAR_ANCHOR in patched:
        print("[ERROR] one or both original anchor blocks still present "
              "after patch.", file=sys.stderr)
        return 5

    _validate_python(patched)

    if args.check:
        print("[OK] check: anchors found, patch would apply, ast.parse OK.")
        return 0

    # Write with the encoding we read in. Use bytes to preserve LF (no Windows
    # implicit CRLF conversion).
    dst.write_bytes(patched.encode(enc.replace("-sig", "")))
    print(f"[OK] wrote {dst}")
    print(f"     bytes:    {len(patched.encode('utf-8')):,}")
    print(f"     encoding: {enc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
