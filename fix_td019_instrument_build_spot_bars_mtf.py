#!/usr/bin/env python3
"""
fix_td019_instrument_build_spot_bars_mtf.py

Adds ENH-71 ExecutionLog instrumentation to build_spot_bars_mtf.py.
TD-019 / TD-023 closure: makes the previously-uninstrumented 5m/15m
spot-bar rollup writer visible in script_execution_log.

What this patch does
--------------------
1. Adds `from core.execution_log import ExecutionLog` after existing imports.
2. At top of main(): instantiates ExecutionLog with expected_writes >= 1
   per output table.
3. After each upsert_batch loop: records actual write count via
   log.record_write(table, total_written).
4. At end of main(): wraps existing verification in success path,
   returns sys.exit(log.complete()).
5. Wraps main() body in try/except so unhandled exceptions land on
   log.exit_with_reason('CRASH', exit_code=1, error_message=...).

Per CLAUDE.md:
- File written, not python -c.
- ast.parse() validates output before write.
- Backup preserved at .pre_td019.bak.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\build_spot_bars_mtf.py")
BACKUP = TARGET.with_suffix(TARGET.suffix + ".pre_td019.bak")


# ── Replacement 1: import block ──────────────────────────────────────────────
OLD_IMPORTS = '''from dotenv import load_dotenv
from supabase import create_client

load_dotenv()'''

NEW_IMPORTS = '''from dotenv import load_dotenv
from supabase import create_client

# ENH-71 write-contract layer. ExecutionLog records every invocation to
# script_execution_log with expected vs actual writes, exit_reason, and
# contract_met. See core/execution_log.py for the API contract.
# TD-019/TD-023 closure 2026-04-26: previously uninstrumented; silent
# 7-trading-day stall (2026-04-15 -> 2026-04-24) discovered only by
# downstream observation. Instrumented now so the next silence surfaces.
from core.execution_log import ExecutionLog

load_dotenv()'''


# ── Replacement 2: main() body ──────────────────────────────────────────────
# Replace entire main() with an instrumented version. The original function
# body is reproduced verbatim inside _run(); main() is now the orchestrator
# that owns the ExecutionLog lifecycle.
OLD_MAIN = '''def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("build_spot_bars_mtf.py — 5m + 15m spot bars")
    log("=" * 65)

    for symbol, inst_id in INSTRUMENTS.items():
        log(f"\\n{'='*20} {symbol} {'='*20}")

        # Load all 1m bars for this instrument
        log(f"  Loading hist_spot_bars_1m for {symbol}...")
        bars_1m = fetch_all(
            sb, "hist_spot_bars_1m",
            "trade_date,bar_ts,open,high,low,close",
            filters=[
                ("eq", "instrument_id", inst_id),
                ("eq", "is_pre_market", False),
            ],
            order="bar_ts"
        )
        log(f"  Loaded {len(bars_1m):,} 1m bars")

        # ── 5m bars ──────────────────────────────────────────────────────
        log(f"  Aggregating to 5m...")
        bars_5m = aggregate_bars(bars_1m, 5)
        log(f"  {len(bars_5m):,} 5m bars")

        # Add instrument_id and symbol
        rows_5m = []
        for bar in bars_5m:
            rows_5m.append({
                "instrument_id": inst_id,
                "symbol":        symbol,
                "trade_date":    bar["trade_date"],
                "bar_ts":        bar["bar_ts"],
                "open":          bar["open"],
                "high":          bar["high"],
                "low":           bar["low"],
                "close":         bar["close"],
                "volume":        bar["volume"],
            })

        # Upsert in batches of 500
        written_5m = 0
        for i in range(0, len(rows_5m), 500):
            written_5m += upsert_batch(
                sb, "hist_spot_bars_5m",
                rows_5m[i:i+500],
                "instrument_id,bar_ts"
            )
        log(f"  Written {written_5m:,} 5m bars")

        # ── 15m bars ─────────────────────────────────────────────────────
        log(f"  Aggregating to 15m...")
        bars_15m = aggregate_bars(bars_1m, 15)
        log(f"  {len(bars_15m):,} 15m bars")

        rows_15m = []
        for bar in bars_15m:
            rows_15m.append({
                "instrument_id": inst_id,
                "symbol":        symbol,
                "trade_date":    bar["trade_date"],
                "bar_ts":        bar["bar_ts"],
                "open":          bar["open"],
                "high":          bar["high"],
                "low":           bar["low"],
                "close":         bar["close"],
                "volume":        bar["volume"],
            })

        written_15m = 0
        for i in range(0, len(rows_15m), 500):
            written_15m += upsert_batch(
                sb, "hist_spot_bars_15m",
                rows_15m[i:i+500],
                "instrument_id,bar_ts"
            )
        log(f"  Written {written_15m:,} 15m bars")

    # Verify
    log("\\n" + "=" * 65)
    log("Verification")
    log("=" * 65)
    for table in ["hist_spot_bars_5m", "hist_spot_bars_15m"]:
        r = sb.table(table).select("*", count="exact").limit(1).execute()
        log(f"  {table}: {r.count} rows")

    log("\\nSpot MTF bars complete.")
    log("Next: python build_atm_option_bars_mtf.py")


if __name__ == "__main__":
    main()'''

NEW_MAIN = '''def _run(exec_log: ExecutionLog) -> None:
    """Original main() body. Records writes to exec_log as they land."""
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("build_spot_bars_mtf.py — 5m + 15m spot bars")
    log("=" * 65)

    for symbol, inst_id in INSTRUMENTS.items():
        log(f"\\n{'='*20} {symbol} {'='*20}")

        # Load all 1m bars for this instrument
        log(f"  Loading hist_spot_bars_1m for {symbol}...")
        bars_1m = fetch_all(
            sb, "hist_spot_bars_1m",
            "trade_date,bar_ts,open,high,low,close",
            filters=[
                ("eq", "instrument_id", inst_id),
                ("eq", "is_pre_market", False),
            ],
            order="bar_ts"
        )
        log(f"  Loaded {len(bars_1m):,} 1m bars")

        # ── 5m bars ──────────────────────────────────────────────────────
        log(f"  Aggregating to 5m...")
        bars_5m = aggregate_bars(bars_1m, 5)
        log(f"  {len(bars_5m):,} 5m bars")

        # Add instrument_id and symbol
        rows_5m = []
        for bar in bars_5m:
            rows_5m.append({
                "instrument_id": inst_id,
                "symbol":        symbol,
                "trade_date":    bar["trade_date"],
                "bar_ts":        bar["bar_ts"],
                "open":          bar["open"],
                "high":          bar["high"],
                "low":           bar["low"],
                "close":         bar["close"],
                "volume":        bar["volume"],
            })

        # Upsert in batches of 500
        written_5m = 0
        for i in range(0, len(rows_5m), 500):
            written_5m += upsert_batch(
                sb, "hist_spot_bars_5m",
                rows_5m[i:i+500],
                "instrument_id,bar_ts"
            )
        log(f"  Written {written_5m:,} 5m bars")
        exec_log.record_write("hist_spot_bars_5m", written_5m)

        # ── 15m bars ─────────────────────────────────────────────────────
        log(f"  Aggregating to 15m...")
        bars_15m = aggregate_bars(bars_1m, 15)
        log(f"  {len(bars_15m):,} 15m bars")

        rows_15m = []
        for bar in bars_15m:
            rows_15m.append({
                "instrument_id": inst_id,
                "symbol":        symbol,
                "trade_date":    bar["trade_date"],
                "bar_ts":        bar["bar_ts"],
                "open":          bar["open"],
                "high":          bar["high"],
                "low":           bar["low"],
                "close":         bar["close"],
                "volume":        bar["volume"],
            })

        written_15m = 0
        for i in range(0, len(rows_15m), 500):
            written_15m += upsert_batch(
                sb, "hist_spot_bars_15m",
                rows_15m[i:i+500],
                "instrument_id,bar_ts"
            )
        log(f"  Written {written_15m:,} 15m bars")
        exec_log.record_write("hist_spot_bars_15m", written_15m)

    # Verify
    log("\\n" + "=" * 65)
    log("Verification")
    log("=" * 65)
    for table in ["hist_spot_bars_5m", "hist_spot_bars_15m"]:
        r = sb.table(table).select("*", count="exact").limit(1).execute()
        log(f"  {table}: {r.count} rows")

    log("\\nSpot MTF bars complete.")
    log("Next: python build_atm_option_bars_mtf.py")


def main() -> int:
    """ENH-71 instrumented entry point. Returns shell exit code."""
    # expected_writes = 1 per output table is "minimum-1 row" semantics: a
    # zero-row run trips contract_met=False even if exit_code=0. Catches
    # "ran cleanly but wrote nothing" — the failure mode that hid TD-019
    # for 10 days. Actual write counts will be in the thousands per run.
    exec_log = ExecutionLog(
        script_name="build_spot_bars_mtf.py",
        expected_writes={
            "hist_spot_bars_5m":  1,
            "hist_spot_bars_15m": 1,
        },
        notes="full-history rebuild of 5m/15m spot bars from hist_spot_bars_1m",
    )
    try:
        _run(exec_log)
    except SystemExit:
        # Allow callees to raise SystemExit cleanly. ExecutionLog atexit
        # hook handles non-zero exits via CRASH path.
        raise
    except Exception as e:
        import traceback
        return exec_log.exit_with_reason(
            "CRASH",
            exit_code=1,
            error_message="".join(traceback.format_exception(type(e), e, e.__traceback__)),
        )
    return exec_log.complete()


if __name__ == "__main__":
    sys.exit(main())'''


def main() -> int:
    if not TARGET.exists():
        print(f"[FAIL] Target not found: {TARGET}", file=sys.stderr)
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Idempotency guard: if already patched, exit clean.
    if "from core.execution_log import ExecutionLog" in src:
        print(f"[SKIP] {TARGET.name} already references ExecutionLog. No-op.")
        return 0

    # Replacement 1
    if OLD_IMPORTS not in src:
        print("[FAIL] Could not locate import block for Replacement 1.", file=sys.stderr)
        print("Expected exact substring:", file=sys.stderr)
        print(repr(OLD_IMPORTS[:200]), file=sys.stderr)
        return 2
    new_src = src.replace(OLD_IMPORTS, NEW_IMPORTS, 1)

    # Replacement 2
    if OLD_MAIN not in new_src:
        print("[FAIL] Could not locate main() block for Replacement 2.", file=sys.stderr)
        print("Expected exact substring (first 200 chars):", file=sys.stderr)
        print(repr(OLD_MAIN[:200]), file=sys.stderr)
        return 3
    new_src = new_src.replace(OLD_MAIN, NEW_MAIN, 1)

    # Sanity check: each replacement applied exactly once.
    if new_src.count("from core.execution_log import ExecutionLog") != 1:
        print("[FAIL] Replacement 1 produced wrong number of import lines.", file=sys.stderr)
        return 4
    if new_src.count("def _run(exec_log: ExecutionLog)") != 1:
        print("[FAIL] Replacement 2 produced wrong number of _run definitions.", file=sys.stderr)
        return 5
    if new_src.count("def main()") != 1:
        print("[FAIL] Replacement 2 produced wrong number of main() definitions.", file=sys.stderr)
        return 6

    # ast.parse() validation BEFORE write — CLAUDE.md patch_script_syntax_validation rule.
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"[FAIL] ast.parse() rejected patched source: {e}", file=sys.stderr)
        return 7

    # Backup, then write.
    if not BACKUP.exists():
        BACKUP.write_text(src, encoding="utf-8")
        print(f"[OK] Backup saved: {BACKUP}")
    else:
        print(f"[OK] Backup already exists: {BACKUP} (not overwriting)")

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"[OK] Patched: {TARGET}")
    print(f"     Original size: {len(src):,} bytes")
    print(f"     Patched size:  {len(new_src):,} bytes")
    print(f"     Delta:         +{len(new_src) - len(src):,} bytes")
    print()
    print("Next steps:")
    print(f"  1. python -m py_compile {TARGET}")
    print(f"  2. python {TARGET}   (this is the backfill run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
