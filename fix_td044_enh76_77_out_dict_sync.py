#!/usr/bin/env python3
"""
fix_td044_enh76_77_out_dict_sync.py  (v2 — line-ending agnostic)

Patches build_trade_signal_local.py to fix TD-044:
  ENH-76/77 blocks set local action and trade_allowed but never sync to
  out["action"] / out["trade_allowed"]. Result: signal_snapshots row
  written to DB still shows BUY_PE / trade_allowed=True even when ENH-76
  supposedly blocked.

v2 change vs v1:
  v1 detected the file's predominant line ending (CRLF) and converted my
  in-script anchors to CRLF before matching. That failed on this target
  because the file has MIXED line endings — earlier patches inserted
  blocks with LF endings into an originally-CRLF file. So the surrounding
  code was CRLF but the ENH-76/77 block I needed to anchor on was LF.

  v2 normalises BOTH sides to LF before matching, applies replacements
  in LF-space, then restores the file's original predominant line ending
  on write. Outcome: ending-agnostic.

Idempotency guard: aborts if "TD-044" marker present.
Rule 5: ast.parse() before write.
Encoding: utf-8-sig read, utf-8 write.
"""
import ast
import pathlib
import sys

TARGET = pathlib.Path(r"C:\GammaEnginePython\build_trade_signal_local.py")

# All anchors and replacements in LF form. Will be matched against an
# LF-normalised view of the source.
REPLACEMENTS = [
    # ── Site 1: ENH-76 BEAR_OB MIDDAY blocked path ─────────────────────
    (
        '        if _in_midday and _ict76 == "BEAR_OB" and action == "BUY_PE":\n'
        '            if _po3_76 != "PO3_BEARISH":\n'
        '                action        = "DO_NOTHING"\n'
        '                trade_allowed = False\n'
        '                cautions.append(\n'
        '                    f"ENH-76: BEAR_OB MIDDAY blocked -- "\n'
        '                    f"po3_session_bias={_po3_76} (requires PO3_BEARISH)"\n'
        '                )',

        '        if _in_midday and _ict76 == "BEAR_OB" and action == "BUY_PE":\n'
        '            if _po3_76 != "PO3_BEARISH":\n'
        '                # TD-044 fix: sync block decision to out{} dict so the\n'
        '                # signal_snapshots row reflects the gate. Local-only\n'
        '                # assignment was a latent bug that left action=BUY_PE\n'
        '                # and trade_allowed=True in the DB row.\n'
        '                action        = "DO_NOTHING"\n'
        '                trade_allowed = False\n'
        '                out["action"]        = "DO_NOTHING"\n'
        '                out["trade_allowed"] = False\n'
        '                cautions.append(\n'
        '                    f"ENH-76: BEAR_OB MIDDAY blocked -- "\n'
        '                    f"po3_session_bias={_po3_76} (requires PO3_BEARISH)"\n'
        '                )',
    ),

    # ── Site 2: ENH-77 NIFTY hard skip ─────────────────────────────────
    (
        '            if symbol == "NIFTY":\n'
        '                action        = "DO_NOTHING"\n'
        '                trade_allowed = False\n'
        '                cautions.append(\n'
        '                    "ENH-77: BULL_OB AFTERNOON NIFTY hard skip -- 50% WR (Exp 40)"\n'
        '                )',

        '            if symbol == "NIFTY":\n'
        '                # TD-044 fix: sync block decision to out{} dict.\n'
        '                action        = "DO_NOTHING"\n'
        '                trade_allowed = False\n'
        '                out["action"]        = "DO_NOTHING"\n'
        '                out["trade_allowed"] = False\n'
        '                cautions.append(\n'
        '                    "ENH-77: BULL_OB AFTERNOON NIFTY hard skip -- 50% WR (Exp 40)"\n'
        '                )',
    ),

    # ── Site 3: ENH-77 SENSEX blocked path ─────────────────────────────
    (
        '                if _po3_76 != "PO3_BULLISH":\n'
        '                    action        = "DO_NOTHING"\n'
        '                    trade_allowed = False\n'
        '                    cautions.append(\n'
        '                        f"ENH-77: BULL_OB AFTERNOON SENSEX blocked -- "\n'
        '                        f"po3_session_bias={_po3_76} (requires PO3_BULLISH)"\n'
        '                    )',

        '                if _po3_76 != "PO3_BULLISH":\n'
        '                    # TD-044 fix: sync block decision to out{} dict.\n'
        '                    action        = "DO_NOTHING"\n'
        '                    trade_allowed = False\n'
        '                    out["action"]        = "DO_NOTHING"\n'
        '                    out["trade_allowed"] = False\n'
        '                    cautions.append(\n'
        '                        f"ENH-77: BULL_OB AFTERNOON SENSEX blocked -- "\n'
        '                        f"po3_session_bias={_po3_76} (requires PO3_BULLISH)"\n'
        '                    )',
    ),
]


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    src_raw = TARGET.read_bytes().decode("utf-8-sig")

    # Detect predominant line ending for the WRITE side
    crlf_count = src_raw.count("\r\n")
    bare_lf_count = src_raw.count("\n") - crlf_count
    write_eol = "\r\n" if crlf_count >= bare_lf_count else "\n"
    print(
        f"Line endings: CRLF={crlf_count} bare-LF={bare_lf_count}  "
        f"-> write as {'CRLF' if write_eol == chr(13)+chr(10) else 'LF'} "
        f"(predominant)"
    )
    if crlf_count > 0 and bare_lf_count > 0:
        print("  Mixed line endings detected — normalising file to predominant on write.")

    if "TD-044" in src_raw:
        print("ERROR: TD-044 marker already present -- aborting (idempotent guard).")
        return 1

    # Normalise EVERYTHING to LF for matching/replacement
    src_lf = src_raw.replace("\r\n", "\n")

    # Verify all 3 anchors match exactly once in LF space
    for i, (old, _new) in enumerate(REPLACEMENTS, 1):
        c = src_lf.count(old)
        if c == 0:
            print(f"ERROR: replacement {i} anchor not found", file=sys.stderr)
            print(f"  Looking for (first 100 chars): {old[:100]!r}",
                  file=sys.stderr)
            return 1
        if c != 1:
            print(f"ERROR: replacement {i} anchor found {c} times "
                  "(expected 1)", file=sys.stderr)
            return 1
        print(f"  anchor {i}: matched once OK")

    # Apply all three replacements in LF space
    patched_lf = src_lf
    for old, new in REPLACEMENTS:
        patched_lf = patched_lf.replace(old, new)

    # ast.parse on LF-form (Python doesn't care about line ending kind)
    try:
        ast.parse(patched_lf)
    except SyntaxError as e:
        print(f"ERROR: ast.parse failed after patch: {e}", file=sys.stderr)
        return 1

    print("ast.parse: PASS")

    # Restore the predominant line ending on write
    if write_eol == "\r\n":
        patched_out = patched_lf.replace("\n", "\r\n")
    else:
        patched_out = patched_lf

    if dry_run:
        print("[DRY-RUN] No file written.")
        print(f"\nWould apply {len(REPLACEMENTS)} replacements:")
        print("  1. ENH-76 BEAR_OB MIDDAY blocked path")
        print("  2. ENH-77 BULL_OB AFTERNOON NIFTY hard skip")
        print("  3. ENH-77 BULL_OB AFTERNOON SENSEX blocked path")
        print(f"  + would normalise mixed line endings to {'CRLF' if write_eol==chr(13)+chr(10) else 'LF'}")
        return 0

    TARGET.write_bytes(patched_out.encode("utf-8"))
    print(f"TD-044 patch applied to: {TARGET.name}")
    print(f"  3 sites synced: out[action] + out[trade_allowed] now match local vars")
    print(f"  File line endings normalised to {'CRLF' if write_eol==chr(13)+chr(10) else 'LF'}")
    print(f"  Idempotency key: 'TD-044'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
