#!/usr/bin/env python3
"""
fix_td032_dashboard_opt_type.py

Session 11 / TD-032 fix.

Root cause of dashboard CE/PE flip:
  In build(), when an active ict_zones row exists for today, d["opt_type"]
  was set from zone.get("opt_type") -- which reflects ICT pattern direction
  BEFORE ENH-35 gate overrides. On LONG_GAMMA days the gate can override a
  bullish ICT pattern (ict_zones.opt_type="CE") to action="BUY_PE". The
  dashboard then rendered CE for a BUY_PE signal, causing wrong instrument
  display and wrong premium fetch from option_chain_snapshots.

  When no active zone existed the else-branch correctly derived opt_type
  from action -- hence non-deterministic behaviour across cycles.

Fix (two edits):
  1. Remove d["opt_type"] = zone.get("opt_type") from the zone branch.
     Move opt_type derivation OUTSIDE the if/else so it runs unconditionally,
     always reading from signal_snapshots.action (single source of truth).
  2. Add a server-side render audit log at the end of build() -- one line
     per symbol per render showing action / opt_type / atm_strike / zone
     presence. Provides runtime evidence that display matches DB ground truth.
     Satisfies TD-032 "DB-vs-display consistency check log line" requirement.

What this patch does NOT fix:
  - 60-second page staleness (meta http-equiv=refresh). When the pipeline
    writes a new signal_snapshots row mid-cycle, the dashboard can show a
    row that is up to 60 seconds old at next observation. Acceptable per
    architecture; ENH-42 WebSocket is permanently deferred (CLAUDE.md).
  - TD-033 "SELL / BUY PE" label conflation (separate cosmetic concern).
  - TD-035 wcb_regime NULL routing.
  - TD-036 confidence_score flat-line.

Success criterion (from CURRENT.md / TD-032):
  Dashboard render demonstrably matches signal_snapshots row across 10+
  test cycles spanning both BULLISH and BEARISH direction_bias.
  Patch ships today; live 10-cycle verification at tomorrow's session start
  (market open 09:15 IST 2026-04-29) via the render audit log in terminal.

Usage:
  cd C:\\GammaEnginePython
  python fix_td032_dashboard_opt_type.py
"""

import ast
import shutil
import sys
from pathlib import Path


TARGET = Path("merdian_signal_dashboard.py")
BACKUP = Path("merdian_signal_dashboard.py.pre_td032.bak")


EDITS = [
    # Edit 1 -- remove zone.opt_type override; move opt_type outside if/else.
    # Anchored on the full if-zone / else block (unique in file).
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
        # NEW
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
    # Edit 2 -- add render audit log before return d at end of build().
    # Anchored on the exit_ts block + return d (unique tail of build()).
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
        # NEW
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
    text = raw.decode("utf-8-sig")
    print(f"Target: {TARGET}  ({len(raw)} bytes, BOM={'yes' if has_bom else 'no'})")

    # Idempotency guard
    if "TD-032 fix (Session 11)" in text:
        sys.stderr.write("ERROR: patch already applied. Restore from backup first.\n")
        return 2

    # Backup
    if BACKUP.exists():
        if BACKUP.read_bytes() == raw:
            print(f"Reusing existing backup: {BACKUP}  (byte-identical)")
        else:
            sys.stderr.write(f"ERROR: {BACKUP} exists but differs from target. Inspect manually.\n")
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

    enc = "utf-8-sig" if has_bom else "utf-8"
    TARGET.write_bytes(new_text.encode(enc))
    new_size = TARGET.stat().st_size
    print(f"\nPatched {TARGET}: {len(raw)} -> {new_size} bytes (+{new_size - len(raw)})")
    print(f"Encoding: {enc}, line-endings preserved")
    print()
    print("Verify:")
    print("  1. Restart the dashboard:  python merdian_signal_dashboard.py")
    print("     Watch terminal for [DASHBOARD] audit lines on each page load.")
    print("  2. Check audit line format:")
    print("     [DASHBOARD] NIFTY: action='BUY_PE' opt_type='PE' atm_strike=24050 zone=present signal_ts=2026-...")
    print("     opt_type must always match action (PE<->BUY_PE, CE<->BUY_CE).")
    print("  3. Compare to signal_snapshots:")
    print("     SELECT symbol, action, atm_strike, direction_bias, ict_pattern, ts")
    print("       FROM signal_snapshots ORDER BY ts DESC LIMIT 4;")
    print("  4. Live 10-cycle verification at session start 2026-04-29 (market open 09:15 IST).")
    print("     TD-032 closes after 10+ consistent audit lines spanning BULLISH+BEARISH.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
