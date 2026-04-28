#!/usr/bin/env python3
"""
fix_f3_instrument_build_ict_htf_zones.py

Session 11 / F3 / TD-017 close.

Adds ENH-71 ExecutionLog instrumentation to build_ict_htf_zones.py.
Pattern follows build_spot_bars_mtf.py (TD-019 closure, Session 9).

What this patch does:
  1. Adds `from core.execution_log import ExecutionLog` to imports
  2. Constructs ExecutionLog at the top of main() after arg parsing
  3. Calls log_exec.record_write("ict_htf_zones", n) after each upsert_zones() call
     (three call sites: 1H, weekly, daily)
  4. Replaces implicit None return at end of main() with
     `raise SystemExit(log_exec.complete(...))`

What this patch does NOT do (separate concerns, separate tech_debt entries):
  - TD-018: deprecated datetime.utcnow() at expire_old_zones (line ~468)
  - TD-030: build_ict_htf_zones doesn't re-evaluate breach on existing zones
  - TD-031: D BEAR_OB / D BEAR_FVG detection underactive

Failure mode (no try/except wrap):
  - Normal exit: raise SystemExit(log_exec.complete()) writes SUCCESS row.
  - Unhandled exception: ExecutionLog atexit hook fires, writes CRASH row
    with current actual_writes tally and traceback (where available).

Validation:
  - ast.parse() of patched content (mandatory per CLAUDE.md rule 5)
  - Each str.replace() asserts replacement count == 1 (no spurious matches)
  - Backup written to build_ict_htf_zones.py.pre_f3.bak

Idempotency:
  - If the import line is already present, the script raises and refuses
    to re-apply. Restore from .pre_f3.bak first to re-run.

Usage:
  cd C:\\GammaEnginePython
  python fix_f3_instrument_build_ict_htf_zones.py
"""

import ast
import shutil
import sys
from pathlib import Path


TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.pre_f3.bak")


# Each entry: (description, OLD, NEW, expected_count)
EDITS = [
    # 1. Add ExecutionLog import after supabase import
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
    # 2. Instantiate log_exec immediately after args parsing,
    #    before target_date/do_weekly/etc. are derived.
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
    # 3. record_write after 1H upsert.
    #    Disambiguated from W and D upserts by the trailing `continue`.
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
    # 4. record_write after weekly upsert.
    #    Disambiguated by "weekly zones" string.
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
    # 5. record_write after daily upsert.
    #    Disambiguated by "daily zones" string.
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
    # 6. SystemExit at end of main().
    #    Anchored on the unique inner-most `log()` call of the verify loop.
    #    The new SystemExit lands at indent 4 (function-body level), which
    #    Python reads as: inner blocks close, then SystemExit at function
    #    body. Validated by ast.parse below.
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

    text = TARGET.read_text(encoding="utf-8")

    # Idempotency guard: refuse to re-apply
    if "from core.execution_log import ExecutionLog" in text:
        sys.stderr.write(
            "ERROR: ExecutionLog import already present in target. Patch is not idempotent.\n"
            f"  To re-apply: restore from {BACKUP} first, then re-run.\n"
        )
        return 2

    # Backup
    if BACKUP.exists():
        sys.stderr.write(f"ERROR: backup already exists: {BACKUP}\n")
        sys.stderr.write("  Refusing to overwrite. Inspect and remove the backup if safe to clobber.\n")
        return 3
    shutil.copy2(TARGET, BACKUP)
    print(f"Backup written: {BACKUP}  ({BACKUP.stat().st_size} bytes)")

    # Apply edits sequentially
    new_text = text
    for desc, old, new, expected in EDITS:
        count = new_text.count(old)
        if count != expected:
            sys.stderr.write(
                f"ERROR: edit '{desc}' expected count {expected}, found {count}.\n"
                f"  Aborting. Backup retained at {BACKUP}; target unchanged.\n"
                f"  Most likely cause: line endings differ (CRLF vs LF) or upstream edits\n"
                f"  changed the surrounding code.\n"
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

    # Write
    TARGET.write_text(new_text, encoding="utf-8")
    delta = len(new_text) - len(text)
    print(f"\nPatched {TARGET}: +{delta} bytes")
    print(f"Backup: {BACKUP}")
    print()
    print("Next steps:")
    print(f"  1. Smoke test (dry-run, no DB writes):")
    print(f"       python {TARGET} --dry-run")
    print(f"  2. Real run (writes zones + 1 row to script_execution_log):")
    print(f"       python {TARGET} --timeframe both")
    print(f"  3. Confirm row in script_execution_log:")
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
