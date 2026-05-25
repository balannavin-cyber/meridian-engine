#!/usr/bin/env python3
"""
fix_enh84_refresh_zones_pine_button.py
Patch merdian_signal_dashboard.py to implement ENH-84:
  Dashboard "Refresh Zones + Pine" button.

What this patch does
--------------------
  1. Adds a new topbar button "REFRESH ZONES" next to the existing
     "PINE OVERLAY" button.
  2. Adds a new GET endpoint /refresh_and_download_pine that:
       a) Runs build_ict_htf_zones.py --timeframe H via subprocess
          (60s timeout, working dir = dashboard's directory).
       b) Calls _gen_pine(sb) for fresh Pine content.
       c) Returns Pine as a download.
  3. Button has confirm() prompt warning ~10-30s wait.

Idempotency guard: aborts if "ENH-84" marker already present.
Rule 5: ast.parse() validation before write.
Encoding: utf-8-sig read, utf-8 write, CRLF auto-detect.

Run from C:\\GammaEnginePython:
  python fix_enh84_refresh_zones_pine_button.py [--dry-run]
"""

import ast
import pathlib
import sys

TARGET = pathlib.Path(r"C:\GammaEnginePython\merdian_signal_dashboard.py")

# ---- Anchor 1: topbar HTML button line (existing PINE OVERLAY) ----
ANCHOR1_BARE = (
    '  <button class="rb" onclick="window.location.href=\'/download_pine\'" '
    'title="Download Pine overlay (auto-generated from ict_htf_zones)">'
    '&#128190; PINE OVERLAY</button>'
)

# Inserted immediately AFTER anchor 1
NEW_BUTTON_HTML = (
    '  <button class="rb" '
    'onclick="if(confirm(\'Rebuild hourly zones in DB then regenerate Pine? '
    'Takes 10-30 seconds.\'))window.location.href=\'/refresh_and_download_pine\'" '
    'title="ENH-84: Rebuild hourly zones then download fresh Pine">'
    '&#128260; REFRESH ZONES</button>'
)

# ---- Anchor 2: do_GET handler — first line of /download_pine block ----
# Insert the new endpoint as a block BEFORE this anchor (so the new
# endpoint matches first; both startswith() calls remain unambiguous
# because the new path is more specific).
ANCHOR2_BARE = '        if self.path.startswith("/download_pine"):'

# New endpoint block — inserted BEFORE anchor 2
ENDPOINT_BLOCK = """\
        if self.path.startswith("/refresh_and_download_pine"):
            # -- ENH-84: rebuild H zones then regenerate and serve Pine ----
            # Synchronous: subprocess + Pine regen runs inside the GET
            # handler. Browser will hang ~10-30s. Acceptable for manual
            # refresh action; not used during automated cycles.
            # --------------------------------------------------------------
            try:
                import subprocess as _sp
                import os as _os
                _cwd = _os.path.dirname(_os.path.abspath(__file__))
                _result = _sp.run(
                    [sys.executable, "build_ict_htf_zones.py",
                     "--timeframe", "H"],
                    capture_output=True, text=True, timeout=60, cwd=_cwd,
                )
                if _result.returncode != 0:
                    _stderr_tail = (_result.stderr or "")[-500:]
                    raise RuntimeError(
                        f"build_ict_htf_zones.py exited "
                        f"{_result.returncode}: {_stderr_tail}"
                    )
                if _gen_pine is None:
                    raise ImportError(
                        "generate_pine_overlay.py not importable"
                    )
                _content = _gen_pine(sb)
                _body = _content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type",
                                 "text/plain; charset=utf-8")
                self.send_header(
                    "Content-Disposition",
                    'attachment; filename='
                    '"merdian_ict_htf_zones_refreshed.pine"',
                )
                self.send_header("Content-Length", len(_body))
                self.end_headers()
                self.wfile.write(_body)
            except _sp.TimeoutExpired:
                _err = b"# ENH-84: zone rebuild timed out after 60s"
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", len(_err))
                self.end_headers()
                self.wfile.write(_err)
            except Exception as _e:
                _err = f"# ENH-84: refresh failed: {_e}".encode()
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", len(_err))
                self.end_headers()
                self.wfile.write(_err)
            return
"""


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    raw = TARGET.read_bytes()
    src = raw.decode("utf-8-sig")

    eol = "\r\n" if "\r\n" in src else "\n"
    print(f"Line ending detected: {'CRLF' if eol == chr(13) + chr(10) else 'LF'}")

    # Idempotency
    if "ENH-84" in src:
        print(
            "ERROR: ENH-84 marker already present -- aborting (idempotent guard)."
        )
        return 1

    # ---- Anchor 1 ----
    anchor1 = ANCHOR1_BARE + eol
    if src.count(anchor1) == 0:
        print(f"ERROR: anchor1 not found: {anchor1!r}", file=sys.stderr)
        return 1
    if src.count(anchor1) != 1:
        print(
            f"ERROR: anchor1 found {src.count(anchor1)} times "
            "(expected 1).",
            file=sys.stderr,
        )
        return 1

    # ---- Anchor 2 ----
    anchor2 = ANCHOR2_BARE + eol
    if src.count(anchor2) == 0:
        print(f"ERROR: anchor2 not found: {anchor2!r}", file=sys.stderr)
        return 1
    if src.count(anchor2) != 1:
        print(
            f"ERROR: anchor2 found {src.count(anchor2)} times "
            "(expected 1).",
            file=sys.stderr,
        )
        return 1

    # Apply patch 1: insert new button AFTER anchor 1
    new_button = NEW_BUTTON_HTML + eol
    patched = src.replace(anchor1, anchor1 + new_button)

    # Apply patch 2: insert endpoint block BEFORE anchor 2
    block_normalised = ENDPOINT_BLOCK.replace("\n", eol)
    patched = patched.replace(anchor2, block_normalised + anchor2)

    # Rule 5: ast.parse validation
    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"ERROR: ast.parse failed after patch: {e}", file=sys.stderr)
        return 1

    print("ast.parse: PASS")

    if dry_run:
        print("[DRY-RUN] No file written.")
        print("\n-- Inserted button --")
        print(NEW_BUTTON_HTML)
        print("\n-- Inserted endpoint block --")
        print(ENDPOINT_BLOCK)
        return 0

    TARGET.write_bytes(patched.encode("utf-8"))
    print(f"ENH-84 patch applied to: {TARGET.name}")
    print(f"  Anchor 1: topbar PINE OVERLAY button -> new REFRESH ZONES button after it")
    print(f"  Anchor 2: /download_pine handler -> new /refresh_and_download_pine handler before it")
    print(f"  Idempotency key: 'ENH-84'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
