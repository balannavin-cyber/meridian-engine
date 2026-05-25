#!/usr/bin/env python3
"""
fix_enh46d_dashboard_pine_download.py

Session 11 extension / ENH-46-D.

Adds two things to merdian_signal_dashboard.py:
  1. /download_pine GET endpoint -- generates Pine v6 overlay from
     ict_htf_zones DB on demand and serves as a file download.
     Imports generate_pine_content() from generate_pine_overlay.py
     (ENH-46-D companion script, must be in same directory).
  2. "PINE OVERLAY" button in the dashboard topbar, next to REFRESH.
     Clicking it triggers the browser download.

Operator workflow (replaces manual Pine regeneration):
  1. Dashboard running at http://localhost:8766
  2. After build_ict_htf_zones.py runs at 08:45 IST (or any time)
  3. Click "PINE OVERLAY" on dashboard
  4. Browser downloads merdian_ict_htf_zones.pine (auto-named)
  5. Paste into TradingView Pine Editor -> Add to Chart

Prerequisite:
  generate_pine_overlay.py must be in C:\\GammaEnginePython\\ alongside
  merdian_signal_dashboard.py.

Encoding: handles BOM + CRLF (same v3 pattern as all Session 11 patches).

Usage:
  cd C:\\GammaEnginePython
  python fix_enh46d_dashboard_pine_download.py
"""

import ast
import shutil
import sys
from pathlib import Path


TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.pre_enh46d.bak")


EDITS = [
    # 1. Add import for generate_pine_overlay at the top of the file,
    #    after the existing imports. Anchored on the load_dotenv() call.
    (
        "Add generate_pine_overlay import",
        "load_dotenv()\n"
        "sb = create_client(os.environ[\"SUPABASE_URL\"], os.environ[\"SUPABASE_SERVICE_ROLE_KEY\"])\n",
        "load_dotenv()\n"
        "sb = create_client(os.environ[\"SUPABASE_URL\"], os.environ[\"SUPABASE_SERVICE_ROLE_KEY\"])\n"
        "\n"
        "# ENH-46-D: Pine overlay generator (Session 11 extension)\n"
        "try:\n"
        "    from generate_pine_overlay import generate_pine_content as _gen_pine\n"
        "except ImportError:\n"
        "    _gen_pine = None\n",
        1,
    ),
    # 2. Add PINE OVERLAY button in topbar, after the REFRESH button.
    (
        "Add PINE OVERLAY button in topbar",
        "  <button class=\"rb\" onclick=\"location.reload()\">&#8635; REFRESH</button>\n",
        "  <button class=\"rb\" onclick=\"location.reload()\">&#8635; REFRESH</button>\n"
        "  <button class=\"rb\" onclick=\"window.location.href='/download_pine'\" title=\"Download Pine overlay (auto-generated from ict_htf_zones)\">&#128190; PINE OVERLAY</button>\n",
        1,
    ),
    # 3. Add /download_pine GET handler at the top of do_GET, before render().
    (
        "Add /download_pine GET handler",
        "    def do_GET(self):\n"
        "        try:\n"
        "            html = render()\n",
        "    def do_GET(self):\n"
        "        if self.path.startswith(\"/download_pine\"):\n"
        "            # ENH-46-D: generate Pine overlay from DB and serve as download\n"
        "            try:\n"
        "                if _gen_pine is None:\n"
        "                    raise ImportError(\"generate_pine_overlay.py not found in working directory\")\n"
        "                content = _gen_pine(sb)\n"
        "                body = content.encode(\"utf-8\")\n"
        "                self.send_response(200)\n"
        "                self.send_header(\"Content-Type\", \"text/plain; charset=utf-8\")\n"
        "                self.send_header(\"Content-Disposition\", 'attachment; filename=\"merdian_ict_htf_zones.pine\"')\n"
        "                self.send_header(\"Content-Length\", len(body))\n"
        "                self.end_headers()\n"
        "                self.wfile.write(body)\n"
        "            except Exception as e:\n"
        "                err = f\"# Error generating Pine overlay: {e}\".encode()\n"
        "                self.send_response(500)\n"
        "                self.send_header(\"Content-Type\", \"text/plain\")\n"
        "                self.send_header(\"Content-Length\", len(err))\n"
        "                self.end_headers()\n"
        "                self.wfile.write(err)\n"
        "            return\n"
        "        try:\n"
        "            html = render()\n",
        1,
    ),
]


def main():
    if not TARGET.exists():
        sys.stderr.write(f"ERROR: {TARGET} not found in cwd={Path.cwd()}\n")
        return 1

    raw = TARGET.read_bytes()
    has_bom  = raw.startswith(b"\xef\xbb\xbf")
    text_raw = raw.decode("utf-8-sig")
    has_crlf = "\r\n" in text_raw
    text     = text_raw.replace("\r\n", "\n") if has_crlf else text_raw

    print(f"Target: {TARGET}  ({len(raw)} bytes, BOM={'yes' if has_bom else 'no'}, LE={'CRLF' if has_crlf else 'LF'})")

    if "_gen_pine" in text or "download_pine" in text:
        sys.stderr.write("ERROR: patch already applied (download_pine found in target). Restore from backup first.\n")
        return 2

    if BACKUP.exists():
        if BACKUP.read_bytes() == raw:
            print(f"Reusing existing backup: {BACKUP}  (byte-identical)")
        else:
            sys.stderr.write(f"ERROR: {BACKUP} exists but differs. Inspect manually.\n")
            return 3
    else:
        shutil.copy2(TARGET, BACKUP)
        print(f"Backup: {BACKUP}  ({BACKUP.stat().st_size} bytes)")

    new_text = text
    for desc, old, new, expected in EDITS:
        count = new_text.count(old)
        if count != expected:
            sys.stderr.write(
                f"ERROR: edit '{desc}' expected {expected}, found {count}.\n"
                f"  Target unchanged. Backup at {BACKUP}.\n"
            )
            return 4
        new_text = new_text.replace(old, new, 1)
        print(f"Applied: {desc}")

    try:
        ast.parse(new_text, filename=str(TARGET))
    except SyntaxError as e:
        sys.stderr.write(f"ERROR: ast.parse failed: {e}\n  Target unchanged.\n")
        return 5

    if has_crlf:
        new_text = new_text.replace("\n", "\r\n")
    enc       = "utf-8-sig" if has_bom else "utf-8"
    new_bytes = new_text.encode(enc)
    TARGET.write_bytes(new_bytes)

    print(f"\nPatched {TARGET}: {len(raw)} -> {len(new_bytes)} bytes (+{len(new_bytes)-len(raw)})")
    print(f"Encoding: {enc}, LE: {'CRLF' if has_crlf else 'LF'} preserved")
    print()
    print("Verify:")
    print("  1. Place generate_pine_overlay.py in C:\\GammaEnginePython\\")
    print("  2. Restart dashboard: python merdian_signal_dashboard.py")
    print("  3. Open http://localhost:8766 -- PINE OVERLAY button visible in topbar")
    print("  4. Click PINE OVERLAY -- browser downloads merdian_ict_htf_zones.pine")
    print("  5. Standalone test: python generate_pine_overlay.py")
    print("     Expected: 'Written: merdian_ict_htf_zones.pine  (N zones rendered)'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
