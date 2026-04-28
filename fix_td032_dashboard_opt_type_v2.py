#!/usr/bin/env python3
"""
fix_td032_dashboard_opt_type_v2.py

Session 11 / TD-032 fix. v2 handles CRLF line endings.

v1 abort reason: dashboard file has CRLF (\\r\\n) line endings on disk.
v1 anchor strings used \\n only -> count=0 -> correct abort, target unchanged.

v2 fix: normalize \\r\\n -> \\n on read for processing; restore original
line-ending convention on write via write_bytes(). Same approach used in
fix_f3_instrument_build_ict_htf_zones_v3.py (Session 11, F3 closure).

Root cause and fix are identical to v1:
  d["opt_type"] = zone.get("opt_type") in build() reads ICT zone direction
  BEFORE ENH-35 gate overrides. On LONG_GAMMA days this produces CE display
  for a BUY_PE signal. Fix: remove the zone.opt_type assignment; derive
  opt_type unconditionally from action (signal_snapshots ground truth).

Reuses existing .pre_td032.bak (byte-identical to current target after v1
wrote it pre-abort).

Usage:
  cd C:\\GammaEnginePython
  python fix_td032_dashboard_opt_type_v2.py
"""

import ast
import shutil
import sys
from pathlib import Path


TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.pre_td032.bak")


EDITS = [
    (
        "Remove zone.opt_type override; opt_type always from action",
        "    if zone:\n"
        "        d[\"pattern\"]  = zone.get(\"pattern_type\", d[\"pattern\"])\n"
        "        d[\"tier\"]     = zone.get(\"ict_tier\",     d[\"tier\"])\n"
        "        d[\"mtf\"]      = zone.get(\"mtf_context\",  d[\"mtf\"])\n"
        "        d[\"zone_high\"]= zone.get(\"zone_high\")\n"
        "        d[\"zone_low\"] = zone.get(\"zone_low\")\n"
        "        d[\"opt_type\"] = zone.get(\"opt_type\")\n"
        "        d[\"lots_t1\"]  = zone.get(\"ict_lots_t1\") or d[\"lots_t1\"]\n"
        "        d[\"lots_t2\"]  = zone.get(\"ict_lots_t2\") or d[\"lots_t2\"]\n"
        "        d[\"lots_t3\"]  = zone.get(\"ict_lots_t3\") or d[\"lots_t3\"]\n"
        "    else:\n"
        "        d[\"zone_high\"] = d[\"zone_low\"] = None\n"
        "        d[\"opt_type\"]  = \"PE\" if action==\"BUY_PE\" else \"CE\" if action==\"BUY_CE\" else None\n",
        "    if zone:\n"
        "        d[\"pattern\"]  = zone.get(\"pattern_type\", d[\"pattern\"])\n"
        "        d[\"tier\"]     = zone.get(\"ict_tier\",     d[\"tier\"])\n"
        "        d[\"mtf\"]      = zone.get(\"mtf_context\",  d[\"mtf\"])\n"
        "        d[\"zone_high\"]= zone.get(\"zone_high\")\n"
        "        d[\"zone_low\"] = zone.get(\"zone_low\")\n"
        "        # TD-032 fix (Session 11): opt_type NOT read from zone.\n"
        "        # zone.opt_type = ICT pattern direction BEFORE ENH-35 gate overrides.\n"
        "        # On LONG_GAMMA days the gate overrides a bullish ICT (opt_type='CE')\n"
        "        # to action='BUY_PE'. Reading zone.opt_type here caused CE display\n"
        "        # on BUY_PE signals. signal_snapshots.action is the source of truth.\n"
        "        d[\"lots_t1\"]  = zone.get(\"ict_lots_t1\") or d[\"lots_t1\"]\n"
        "        d[\"lots_t2\"]  = zone.get(\"ict_lots_t2\") or d[\"lots_t2\"]\n"
        "        d[\"lots_t3\"]  = zone.get(\"ict_lots_t3\") or d[\"lots_t3\"]\n"
        "    else:\n"
        "        d[\"zone_high\"] = d[\"zone_low\"] = None\n"
        "    # TD-032 fix: unconditional -- zone presence cannot override action.\n"
        "    d[\"opt_type\"] = \"PE\" if action == \"BUY_PE\" else \"CE\" if action == \"BUY_CE\" else None\n",
        1,
    ),
    (
        "Add render audit log before return d",
        "    if d[\"ts\"]:\n"
        "        try:\n"
        "            st = datetime.fromisoformat(d[\"ts\"].replace(\"Z\",\"+00:00\"))\n"
        "            d[\"exit_ts\"] = (st + timedelta(minutes=30)).isoformat()\n"
        "        except: d[\"exit_ts\"] = None\n"
        "    else: d[\"exit_ts\"] = None\n"
        "\n"
        "    return d\n",
        "    if d[\"ts\"]:\n"
        "        try:\n"
        "            st = datetime.fromisoformat(d[\"ts\"].replace(\"Z\",\"+00:00\"))\n"
        "            d[\"exit_ts\"] = (st + timedelta(minutes=30)).isoformat()\n"
        "        except: d[\"exit_ts\"] = None\n"
        "    else: d[\"exit_ts\"] = None\n"
        "\n"
        "    # TD-032 render audit log -- one line per symbol per page render.\n"
        "    # Verify in terminal that action/opt_type/strike match DB ground truth.\n"
        "    import sys as _sys\n"
        "    _sys.stderr.write(\n"
        "        f\"[DASHBOARD] {sym}: action={d.get('action')!r} \"\n"
        "        f\"opt_type={d.get('opt_type')!r} \"\n"
        "        f\"atm_strike={d.get('atm_strike')} \"\n"
        "        f\"zone={'present' if zone else 'absent'} \"\n"
        "        f\"signal_ts={str(d.get('ts',''))[:19]}\\n\"\n"
        "    )\n"
        "\n"
        "    return d\n",
        1,
    ),
]


def main():
    if not TARGET.exists():
        sys.stderr.write(f"ERROR: {TARGET} not found in cwd={Path.cwd()}\n")
        return 1

    raw = TARGET.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    # Decode: utf-8-sig strips BOM if present, otherwise equivalent to utf-8
    text_original = raw.decode("utf-8-sig")

    # Detect line-ending convention
    has_crlf = "\r\n" in text_original
    # Normalize to LF for processing so anchors always match
    text = text_original.replace("\r\n", "\n") if has_crlf else text_original

    print(f"Target: {TARGET}  ({len(raw)} bytes, BOM={'yes' if has_bom else 'no'}, LE={'CRLF' if has_crlf else 'LF'})")

    # Idempotency guard
    if "TD-032 fix (Session 11)" in text:
        sys.stderr.write("ERROR: patch already applied. Restore from backup first.\n")
        return 2

    # Backup
    if BACKUP.exists():
        if BACKUP.read_bytes() == raw:
            print(f"Reusing existing backup: {BACKUP}  ({len(raw)} bytes, byte-identical)")
        else:
            sys.stderr.write(
                f"ERROR: {BACKUP} exists but differs from target bytes.\n"
                "  Inspect both files. Remove stale backup if safe, then re-run.\n"
            )
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

    # ast.parse on LF-normalized text (mandatory per CLAUDE.md rule 5)
    try:
        ast.parse(new_text, filename=str(TARGET))
    except SyntaxError as e:
        sys.stderr.write(f"ERROR: ast.parse failed: {e}\n  Target unchanged.\n")
        return 5

    # Restore original line-ending convention before encoding
    if has_crlf:
        new_text = new_text.replace("\n", "\r\n")

    enc = "utf-8-sig" if has_bom else "utf-8"
    new_bytes = new_text.encode(enc)
    TARGET.write_bytes(new_bytes)

    print(f"\nPatched {TARGET}: {len(raw)} -> {len(new_bytes)} bytes (+{len(new_bytes) - len(raw)})")
    print(f"Encoding: {enc}, line-endings: {'CRLF' if has_crlf else 'LF'} preserved")
    print()
    print("Next steps:")
    print("  1. Restart the dashboard (kill + relaunch)")
    print("     Watch terminal -- [DASHBOARD] audit lines appear on every page load:")
    print("     [DASHBOARD] NIFTY: action='BUY_PE' opt_type='PE' atm_strike=24050 zone=present ...")
    print("     opt_type MUST match action (PE<->BUY_PE, CE<->BUY_CE). If it does, fix works.")
    print("  2. Compare to DB:")
    print("     SELECT symbol, action, atm_strike, ict_pattern, ts")
    print("       FROM signal_snapshots ORDER BY ts DESC LIMIT 4;")
    print("  3. TD-032 closes after 10+ consistent audit lines spanning BULLISH+BEARISH.")
    print("     Live verification at session start 2026-04-29 (market open 09:15 IST).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
