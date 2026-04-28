#!/usr/bin/env python3
"""
fix_f3_instrument_build_ict_htf_zones_v3.py

Session 11 / F3 / TD-017 close. v3 of the F3 instrumentation patch.

What v3 changes vs v2:
  - Writes via TARGET.write_bytes(new_text.encode(...)) instead of
    TARGET.write_text(new_text, encoding=...). On Windows, write_text()
    defaults to translating '\\n' to '\\r\\n' on output, which would
    convert an LF-on-disk source file to CRLF as a patch side-effect.
    The result was a working file but a noisy git diff (every line
    showed as modified). v3 reads bytes, decodes for processing,
    encodes and writes bytes back -- symmetric, no LE translation.

Everything else identical to v2. Same six edits, same anchors, same
ast.parse() validation, same idempotency guard, same backup-reuse
logic, same exit codes.

Usage:
  cd C:\\GammaEnginePython
  python fix_f3_instrument_build_ict_htf_zones_v3.py

Pre-condition: target file is in clean pre-patch state (i.e. restore
from .pre_f3.bak first if v2 was run).
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


def _detect_line_ending(text: str) -> str:
    """Return the dominant line-ending convention in text. Best-effort."""
    if "\r\n" in text:
        return "CRLF"
    if "\n" in text:
        return "LF"
    return "none"


def main():
    if not TARGET.exists():
        sys.stderr.write(f"ERROR: target file not found: {TARGET}\n")
        sys.stderr.write(f"  cwd={Path.cwd()}\n")
        return 1

    # Read raw bytes -- no newline translation, no encoding interpretation yet.
    target_bytes = TARGET.read_bytes()
    has_bom = target_bytes.startswith(b"\xef\xbb\xbf")

    # Decode for string processing. utf-8-sig strips BOM if present.
    text = target_bytes.decode("utf-8-sig")
    le_before = _detect_line_ending(text)
    print(f"Target: {TARGET}  ({len(target_bytes)} bytes, BOM={'yes' if has_bom else 'no'}, line-endings={le_before})")

    # Idempotency guard
    if "from core.execution_log import ExecutionLog" in text:
        sys.stderr.write(
            "ERROR: ExecutionLog import already present in target. Patch is not idempotent.\n"
            f"  To re-apply: restore from {BACKUP} first, then re-run.\n"
        )
        return 2

    # Backup logic. Reuse if byte-identical to current target (e.g. v2 wrote
    # it before aborting); otherwise refuse to overwrite.
    if BACKUP.exists():
        backup_bytes = BACKUP.read_bytes()
        if backup_bytes == target_bytes:
            print(f"Reusing existing backup: {BACKUP}  ({len(backup_bytes)} bytes, byte-identical)")
        else:
            sys.stderr.write(
                f"ERROR: backup at {BACKUP} differs from current target.\n"
                "  Inspect both files; restore-from-backup or remove-stale-backup, then re-run.\n"
            )
            return 3
    else:
        shutil.copy2(TARGET, BACKUP)
        print(f"Backup written: {BACKUP}  ({BACKUP.stat().st_size} bytes)")

    # Apply edits.  Anchors use \\n; if the file is CRLF this won't match
    # (count==0) and the patch aborts cleanly.  v3 keeps that defensive
    # behaviour -- if you see "expected count 1 found 0" on CRLF input, that
    # is the correct response.
    new_text = text
    for desc, old, new, expected in EDITS:
        count = new_text.count(old)
        if count != expected:
            sys.stderr.write(
                f"ERROR: edit '{desc}' expected count {expected}, found {count}.\n"
                f"  Aborting. Backup retained at {BACKUP}; target unchanged.\n"
                f"  If the file is CRLF on disk, that is the cause -- v3 expects LF.\n"
            )
            return 4
        new_text = new_text.replace(old, new, 1)
        print(f"Applied: {desc}")

    # Validate Python syntax (mandatory per CLAUDE.md non-negotiable rule 5).
    try:
        ast.parse(new_text, filename=str(TARGET))
    except SyntaxError as e:
        sys.stderr.write(f"ERROR: ast.parse failed on patched content: {e}\n")
        sys.stderr.write(f"  Aborting. Backup retained at {BACKUP}; target unchanged.\n")
        return 5

    # Encode for write.  Use utf-8-sig if original had BOM, else plain utf-8.
    write_encoding = "utf-8-sig" if has_bom else "utf-8"
    new_bytes = new_text.encode(write_encoding)

    # Write via write_bytes -- NO newline translation.  This is the v3 fix.
    TARGET.write_bytes(new_bytes)

    le_after = _detect_line_ending(TARGET.read_bytes().decode("utf-8-sig"))
    delta = len(new_bytes) - len(target_bytes)
    print(f"\nPatched {TARGET}: +{delta} bytes")
    print(f"  encoding={write_encoding}, BOM={'preserved' if has_bom else 'none'}, line-endings={le_before} -> {le_after}")
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
