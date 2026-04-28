#!/usr/bin/env python3
"""
fix_f3_instrument_build_ict_htf_zones_v2.py

Session 11 / F3 / TD-017 close. v2 of the F3 instrumentation patch.

What v2 changes vs v1:
  - Reads target with encoding='utf-8-sig' (strips UTF-8 BOM for processing).
    v1 read with encoding='utf-8' which preserved the BOM in the string,
    causing ast.parse() to reject 'invalid non-printable character U+FEFF'.
    On Navin's box the source has a BOM (likely from PowerShell Set-Content
    upstream); same family as TD-026 PowerShell-encoding hazard.
  - Writes back with encoding='utf-8-sig' so the file on disk is BOM-preserved
    (identical to pre-patch, modulo our edits). Production runtime behaviour
    is unchanged.
  - Reuses an existing build_ict_htf_zones.py.pre_f3.bak if its bytes are
    identical to the current target. v1 created such a backup before failing
    cleanly; reusing it avoids accumulating stale .bak_v2 files.

Everything else identical to v1. Same six edits, same anchors, same
ast.parse() validation, same idempotency guard, same exit codes.

Usage:
  cd C:\\GammaEnginePython
  python fix_f3_instrument_build_ict_htf_zones_v2.py
"""

import ast
import shutil
import sys
from pathlib import Path


TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.pre_f3.bak")


# Each entry: (description, OLD, NEW, expected_count)
EDITS = [
    (
        "Add ExecutionLog import",
        "from supabase import create_client\n",
        (
            "from supabase import create_client\n"
            "\n"
            "# ENH-71 instrumentation (added Session 11, F3 / TD-017 close)\n"
            "from core.execution_log import ExecutionLog\n"
        ),
        1,
    ),
    (
        "Instantiate ExecutionLog after args parsing",
        "    args = parser.parse_args()\n"
        "\n"
        "    target_date = date.fromisoformat(args.date)\n",
        "    args = parser.parse_args()\n"
        "\n"
        "    # ENH-71 instrumentation (added Session 11, F3 / TD-017 close)\n"
        "    log_exec = ExecutionLog(\n"
        "        script_name=\"build_ict_htf_zones.py\",\n"
        "        expected_writes={} if args.dry_run else {\"ict_htf_zones\": 1},\n"
        "        symbol=None,\n"
        "        dry_run=args.dry_run,\n"
        "        notes=f\"timeframe={args.timeframe} date={args.date}\",\n"
        "    )\n"
        "\n"
        "    target_date = date.fromisoformat(args.date)\n",
        1,
    ),
    (
        "record_write after 1H upsert",
        "            n = upsert_zones(sb, h_zones, dry_run)\n"
        "            log(f\"  Written {n} 1H zones\")\n"
        "            total_written += n\n"
        "            continue\n",
        "            n = upsert_zones(sb, h_zones, dry_run)\n"
        "            log_exec.record_write(\"ict_htf_zones\", n)\n"
        "            log(f\"  Written {n} 1H zones\")\n"
        "            total_written += n\n"
        "            continue\n",
        1,
    ),
    (
        "record_write after weekly upsert",
        "            n = upsert_zones(sb, w_zones, dry_run)\n"
        "            log(f\"  Written {n} weekly zones\")\n"
        "            total_written += n\n",
        "            n = upsert_zones(sb, w_zones, dry_run)\n"
        "            log_exec.record_write(\"ict_htf_zones\", n)\n"
        "            log(f\"  Written {n} weekly zones\")\n"
        "            total_written += n\n",
        1,
    ),
    (
        "record_write after daily upsert",
        "            n = upsert_zones(sb, d_zones, dry_run)\n"
        "            log(f\"  Written {n} daily zones\")\n"
        "            total_written += n\n",
        "            n = upsert_zones(sb, d_zones, dry_run)\n"
        "            log_exec.record_write(\"ict_htf_zones\", n)\n"
        "            log(f\"  Written {n} daily zones\")\n"
        "            total_written += n\n",
        1,
    ),
    (
        "complete() at end of main()",
        "                log(f\"    {r['timeframe']} {r['pattern_type']:10s} \"\n"
        "                    f\"{float(r['zone_low']):,.0f}-{float(r['zone_high']):,.0f}\")\n",
        "                log(f\"    {r['timeframe']} {r['pattern_type']:10s} \"\n"
        "                    f\"{float(r['zone_low']):,.0f}-{float(r['zone_high']):,.0f}\")\n"
        "\n"
        "    # ENH-71 instrumentation (added Session 11, F3 / TD-017 close)\n"
        "    raise SystemExit(log_exec.complete(notes=f\"{total_written} zones written\"))\n",
        1,
    ),
]


def main():
    if not TARGET.exists():
        sys.stderr.write(f"ERROR: target file not found: {TARGET}\n")
        sys.stderr.write(f"  cwd={Path.cwd()}\n")
        return 1

    # Read raw bytes first so we can detect BOM presence and confirm
    # the existing backup (if any) is byte-identical.
    target_bytes = TARGET.read_bytes()
    has_bom = target_bytes.startswith(b"\xef\xbb\xbf")
    print(f"Target: {TARGET}  ({len(target_bytes)} bytes, BOM={'yes' if has_bom else 'no'})")

    # Decode for string processing. utf-8-sig strips the BOM if present.
    text = target_bytes.decode("utf-8-sig")

    # Idempotency guard
    if "from core.execution_log import ExecutionLog" in text:
        sys.stderr.write(
            "ERROR: ExecutionLog import already present in target. Patch is not idempotent.\n"
            f"  To re-apply: restore from {BACKUP} first, then re-run.\n"
        )
        return 2

    # Backup logic. If a backup exists and is byte-identical to the current
    # target (e.g. v1 wrote it before aborting), reuse it. Otherwise refuse
    # to overwrite — operator should inspect manually.
    if BACKUP.exists():
        backup_bytes = BACKUP.read_bytes()
        if backup_bytes == target_bytes:
            print(f"Reusing existing backup: {BACKUP}  ({len(backup_bytes)} bytes, byte-identical to target)")
        else:
            sys.stderr.write(
                f"ERROR: backup already exists at {BACKUP} but its bytes differ from current target.\n"
                "  This means the target has been modified since the backup was taken.\n"
                "  Inspect both files and decide manually whether to:\n"
                "    (a) restore from backup before re-running,\n"
                "    (b) move the backup aside if it represents a different prior state, or\n"
                "    (c) delete the backup if it is known stale.\n"
            )
            return 3
    else:
        shutil.copy2(TARGET, BACKUP)
        print(f"Backup written: {BACKUP}  ({BACKUP.stat().st_size} bytes)")

    # Apply edits
    new_text = text
    for desc, old, new, expected in EDITS:
        count = new_text.count(old)
        if count != expected:
            sys.stderr.write(
                f"ERROR: edit '{desc}' expected count {expected}, found {count}.\n"
                f"  Aborting. Backup retained at {BACKUP}; target unchanged.\n"
            )
            return 4
        new_text = new_text.replace(old, new, 1)
        print(f"Applied: {desc}")

    # Validate Python syntax (mandatory per CLAUDE.md non-negotiable rule 5)
    try:
        ast.parse(new_text, filename=str(TARGET))
    except SyntaxError as e:
        sys.stderr.write(f"ERROR: ast.parse failed on patched content: {e}\n")
        sys.stderr.write(f"  Aborting. Backup retained at {BACKUP}; target unchanged.\n")
        return 5

    # Write back. Use utf-8-sig if the original had a BOM, else plain utf-8.
    # This preserves the file's encoding signature exactly except for our edits.
    write_encoding = "utf-8-sig" if has_bom else "utf-8"
    TARGET.write_text(new_text, encoding=write_encoding)

    new_bytes = TARGET.read_bytes()
    delta = len(new_bytes) - len(target_bytes)
    print(f"\nPatched {TARGET}: +{delta} bytes (encoding={write_encoding}, BOM preserved={'yes' if has_bom else 'n/a'})")
    print(f"Backup: {BACKUP}")
    print()
    print("Next steps:")
    print(f"  1. Smoke test (dry-run, no DB writes):")
    print(f"       python {TARGET} --dry-run")
    print(f"  2. Real run:")
    print(f"       python {TARGET} --timeframe both")
    print(f"  3. Verify in Supabase:")
    print(f"       SELECT script_name, host, exit_reason, contract_met,")
    print(f"              expected_writes, actual_writes, duration_ms, started_at")
    print(f"         FROM script_execution_log")
    print(f"        WHERE script_name='build_ict_htf_zones.py'")
    print(f"        ORDER BY started_at DESC LIMIT 3;")
    print(f"  4. Register Task Scheduler:")
    print(f"       powershell -ExecutionPolicy Bypass -File register_ict_htf_zones_task.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
