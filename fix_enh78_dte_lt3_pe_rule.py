#!/usr/bin/env python3
"""
fix_enh78_dte_lt3_pe_rule.py
Patch build_trade_signal_local.py to implement ENH-78:
  DTE<3 PDH sweep -> current-week PE rule.

Evidence: Exp 35D
  PDH DTE<3 + PO3_BEARISH = 90.9% EOD WR (N=11)
  Mean option return: +125% SENSEX (current-week beats next-week at DTE<3).
  DTE=1 sub-case strongest: 75% T+1D WR, mean|wins=0.556%.

What this patch does
--------------------
  Inserts the ENH-78 block immediately before `return out, flags`
  inside build_signal().

  Logic:
    - If po3_session_bias=PO3_BEARISH AND 1 <= dte <= 2 AND action=BUY_PE:
        * DTE=1: lifts the standard DTE<=1 trade_allowed=False gate.
                 Reverses the -12 confidence penalty from the DTE gate.
                 Removes "DTE gate blocks trade" cautions.
        * DTE=2: annotates as ENH-78 confirmed (gate never fired for DTE=2).
        * Both: appends stop rule to cautions.
                Sets out["raw"]["enh78_triggered"]=True, enh78_dte, enh78_stop_note.
    - If 1 <= dte <= 2 AND action=BUY_PE but PO3_BEARISH absent:
        Sets out["raw"]["enh78_triggered"]=False (diagnostic, DTE<3 without bias).
    - All other signals: no change.

  IMPORTANT: Updates both local vars AND out[] keys. Does NOT share the
  ENH-76/77 bug where local action/trade_allowed diverge from out dict.

Idempotency guard: aborts if ENH-78 marker already present.
Rule 5: ast.parse() validation before write.
Encoding: read utf-8-sig, write utf-8 bytes (CRLF-safe).
Line endings: auto-detected (CRLF on Windows, LF on Linux).

Run from the GammaEnginePython directory:
  python fix_enh78_dte_lt3_pe_rule.py [--dry-run]
"""

import ast
import pathlib
import sys

TARGET = pathlib.Path(r"C:\GammaEnginePython\build_trade_signal_local.py")

# Anchor bare (without line ending — EOL detected at runtime)
ANCHOR_BARE = "    return out, flags"

# ── ENH-78 block to insert (LF-terminated; EOL normalised at runtime) ───────
ENH78_BLOCK = """\
    # -- ENH-78: DTE<3 PDH sweep -> current-week PE rule ---------------------
    # Must run AFTER ENH-76/77 block and AFTER out["po3_session_bias"] set.
    # Evidence: Exp 35D -- PDH DTE<3 + PO3_BEARISH = 90.9% EOD WR (N=11),
    #   mean option return +125% SENSEX (current-week beats next-week).
    #   DTE=1 sub-case strongest: 75% T+1D WR, mean|wins=0.556%.
    # Condition:
    #   po3_session_bias = PO3_BEARISH
    #   AND 1 <= dte <= 2   (DTE=0 = already-expired context, excluded)
    #   AND action = BUY_PE (bearish signal active)
    # DTE=1 override: the standard DTE<=1 gate blocks trade_allowed and
    #   deducts 12 confidence points. This edge is confirmed by session
    #   bias -- gate lifted and penalty reversed.
    # Stop rule: 40% of entry premium OR price re-takes PDH.
    # -------------------------------------------------------------------------
    _po3_78 = out.get("po3_session_bias", "PO3_NONE")
    _enh78_active = (
        _po3_78 == "PO3_BEARISH"
        and dte is not None
        and 1 <= dte <= 2
        and action == "BUY_PE"
    )
    if _enh78_active:
        if dte == 1:
            # Lift the standard DTE<=1 gate for this confirmed-bias edge
            trade_allowed = True
            out["trade_allowed"] = True
            # Reverse the -12 confidence penalty applied by DTE gate above
            confidence += 12.0
            confidence = max(0.0, min(100.0, confidence))
            out["confidence_score"] = round(confidence, 1)
            # Remove "DTE gate blocks trade" cautions added by DTE gate block
            out["cautions"][:] = [
                c for c in out.get("cautions", [])
                if "DTE gate" not in c
            ]
            out["reasons"].append(
                "ENH-78: DTE=1 gate lifted -- PO3_BEARISH PDH sweep, "
                "current-week PE (90.9% EOD WR, Exp 35D)"
            )
        else:  # dte == 2
            out["reasons"].append(
                "ENH-78: DTE=2 PDH sweep confirmed -- current-week PE "
                "(90.9% EOD WR, Exp 35D)"
            )
        out["cautions"].append(
            "ENH-78: Stop = 40% of entry premium OR price re-takes PDH"
        )
        if not out.get("raw"):
            out["raw"] = {}
        out["raw"]["enh78_triggered"] = True
        out["raw"]["enh78_dte"] = dte
        out["raw"]["enh78_stop_note"] = "40pct_premium_or_pdh_reclaim"
    elif dte is not None and 1 <= dte <= 2 and action == "BUY_PE":
        # DTE<3 BUY_PE present but PO3_BEARISH not confirmed -- standard rules
        if not out.get("raw"):
            out["raw"] = {}
        out["raw"]["enh78_triggered"] = False
    # -- end ENH-78 -----------------------------------------------------------
"""


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    raw_bytes = TARGET.read_bytes()
    src = raw_bytes.decode("utf-8-sig")

    # Detect line ending from the file itself
    eol = "\r\n" if "\r\n" in src else "\n"
    print(f"Line ending detected: {'CRLF' if eol == chr(13) + chr(10) else 'LF'}")

    ANCHOR = ANCHOR_BARE + eol

    # Idempotency guard
    if "ENH-78" in src:
        print("ERROR: ENH-78 marker already present -- aborting (idempotent guard).")
        return 1

    # Anchor check
    count = src.count(ANCHOR)
    if count == 0:
        print(f"ERROR: anchor not found: {ANCHOR!r}", file=sys.stderr)
        return 1
    if count != 1:
        print(
            f"ERROR: anchor found {count} times (expected 1) -- ambiguous insertion.",
            file=sys.stderr,
        )
        return 1

    # Normalise ENH78_BLOCK line endings to match the file
    block_normalised = ENH78_BLOCK.replace("\n", eol)

    patched = src.replace(ANCHOR, block_normalised + ANCHOR)

    # Rule 5: ast.parse validation before write
    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"ERROR: ast.parse failed after patch: {e}", file=sys.stderr)
        return 1

    print("ast.parse: PASS")

    if dry_run:
        print("[DRY-RUN] No file written.")
        print("\n-- Inserted block preview --")
        print(ENH78_BLOCK)
        print("----------------------------")
        return 0

    # Write back with same encoding, CRLF preserved
    TARGET.write_bytes(patched.encode("utf-8"))
    print(f"ENH-78 patch applied to: {TARGET.name}")
    print(f"  Insertion point: immediately before `return out, flags`")
    print(f"  Idempotency key: 'ENH-78'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
