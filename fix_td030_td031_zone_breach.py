#!/usr/bin/env python3
"""
fix_td030_td031_zone_breach.py

Session 11 extension / TD-030 + TD-031 fix.

ROOT CAUSE (shared):
  filter_breached_zones() is called BEFORE upsert_zones() in main().
  This means:
  (a) OBs/FVGs that were mitigated overnight are never written to DB
      -> ICT detector never sees them during the trading session (TD-031).
  (b) OBs/FVGs that were written on a prior day but get mitigated MID-SESSION
      stay ACTIVE in DB until valid_to expires -> detector sees stale ACTIVE
      zones that spot has already passed through (TD-030).

TD-031 specifics (D BEAR underactive since 04-11):
  Market has been recovering since 04-09 crash. Every BEAR_OB formed on a
  down day (e.g. 04-24, -1.17%) gets filtered at write time because next
  morning's spot has recovered above the zone level. The 04-27 08:45 IST run
  detected the 04-24 BEAR_OB but current_spot=24,089 > zone_low=23,857 ->
  filter removed it before it reached the DB.

FIX:
  1. TD-030: Add recheck_breached_zones() -- a DB UPDATE pass that marks
     existing ACTIVE zones as BREACHED where current spot has passed through
     their level. Called after daily_ohlcv loads, before new zone detection.

  2. TD-031: In weekly and daily detection loops, split filter_breached_zones()
     application:
     - OB/FVG patterns: write unconditionally (NO breach filter at write time).
       Fresh OBs are real structure regardless of overnight recovery. Breach
       assessment is handled by recheck_breached_zones() and detect_ict_
       patterns_runner.py at query time.
     - PDH/PDL patterns: keep filter (nearest 2+2 proximity logic is correct
       for liquidity levels; they don't need to "survive" overnight).

What this patch does NOT touch:
  - TD-018 (deprecated datetime.utcnow() at line 471) -- separate concern.
  - TD-031 framing note: D BEAR_FVG detection is zero because detect_daily_zones()
    was never designed to produce FVGs (only PDH/PDL/OB). Weekly FVG detection
    exists; daily FVG was out of original scope. Not a bug.

Validation:
  1. Run --dry-run after patch: confirm new log lines:
     "Rechecking breached zones for NIFTY @ spot ..."
     "Detected N weekly zones (M OB/FVG + K PDH/PDL)"
  2. Real run: check script_execution_log row (contract_met=true).
  3. Query ict_htf_zones to confirm any newly-written OBs and any
     BREACHED status updates on previously stale ACTIVE zones.
  4. At next down day: confirm D BEAR_OB appears in ict_htf_zones with
     status=ACTIVE at 08:45 IST, visible to detect_ict_patterns_runner.py.

Encoding: handles BOM + CRLF (same pattern as fix_f3/fix_td032 v3 scripts).

Usage:
  cd C:\\GammaEnginePython
  python fix_td030_td031_zone_breach.py
"""

import ast
import shutil
import sys
from pathlib import Path


TARGET = Path("build_ict_htf_zones.py")
BACKUP = Path("build_ict_htf_zones.py.pre_td030_td031.bak")


EDITS = [
    # 1. Insert recheck_breached_zones() function before def upsert_zones.
    #    Anchored on the unique return statement that ends filter_breached_zones().
    (
        "Add recheck_breached_zones() function before upsert_zones",
        "    return ob_fvg + nearest_pdh + nearest_pdl\n"
        "def upsert_zones(sb, zones, dry_run=False):\n",
        "    return ob_fvg + nearest_pdh + nearest_pdl\n"
        "\n"
        "\n"
        "def recheck_breached_zones(sb, symbol, daily_ohlcv, as_of, dry_run=False):\n"
        "    \"\"\"\n"
        "    TD-030 fix (Session 11): mark ACTIVE zones BREACHED when current spot\n"
        "    has passed through their price level.\n"
        "\n"
        "    Previously, only expire_old_zones() cleaned up stale zones (by valid_to\n"
        "    date). Zones mitigated mid-session stayed ACTIVE indefinitely, so\n"
        "    detect_ict_patterns_runner.py queried them as valid even after spot had\n"
        "    already traded through them.\n"
        "\n"
        "    Breach logic mirrors filter_breached_zones():\n"
        "      BULL_OB / BULL_FVG / PDL: valid if current_spot > zone_high.\n"
        "        BREACHED if current_spot <= zone_high (price inside or below zone).\n"
        "      BEAR_OB / BEAR_FVG / PDH: valid if current_spot < zone_low.\n"
        "        BREACHED if current_spot >= zone_low (price inside or above zone).\n"
        "    \"\"\"\n"
        "    sorted_dates = sorted(k for k in daily_ohlcv.keys() if k <= as_of)\n"
        "    if not sorted_dates:\n"
        "        log(f\"  TD-030: no OHLCV for {symbol} as_of {as_of} -- skipping breach recheck\")\n"
        "        return\n"
        "\n"
        "    current_spot = daily_ohlcv[sorted_dates[-1]][\"close\"]\n"
        "    log(f\"  Rechecking breached zones for {symbol} @ spot {current_spot:,.1f}\")\n"
        "\n"
        "    if dry_run:\n"
        "        log(f\"  DRY RUN -- would mark BREACHED where spot passed through zone\")\n"
        "        return\n"
        "\n"
        "    try:\n"
        "        # BULL_OB / BULL_FVG / PDL: BREACHED if zone_high >= current_spot\n"
        "        # (current_spot <= zone_high means price is at or below the zone)\n"
        "        for pattern in (\"BULL_OB\", \"BULL_FVG\", \"PDL\"):\n"
        "            sb.table(\"ict_htf_zones\").update({\n"
        "                \"status\": \"BREACHED\",\n"
        "                \"updated_at\": datetime.utcnow().isoformat()\n"
        "            }).eq(\"symbol\", symbol).eq(\"status\", \"ACTIVE\").eq(\n"
        "                \"pattern_type\", pattern\n"
        "            ).gte(\"zone_high\", float(current_spot)).execute()\n"
        "\n"
        "        # BEAR_OB / BEAR_FVG / PDH: BREACHED if zone_low <= current_spot\n"
        "        # (current_spot >= zone_low means price is at or above the zone)\n"
        "        for pattern in (\"BEAR_OB\", \"BEAR_FVG\", \"PDH\"):\n"
        "            sb.table(\"ict_htf_zones\").update({\n"
        "                \"status\": \"BREACHED\",\n"
        "                \"updated_at\": datetime.utcnow().isoformat()\n"
        "            }).eq(\"symbol\", symbol).eq(\"status\", \"ACTIVE\").eq(\n"
        "                \"pattern_type\", pattern\n"
        "            ).lte(\"zone_low\", float(current_spot)).execute()\n"
        "\n"
        "        log(f\"  TD-030: breach recheck done for {symbol}\")\n"
        "    except Exception as e:\n"
        "        log(f\"  Warning: could not recheck breached zones for {symbol}: {e}\")\n"
        "\n"
        "\n"
        "def upsert_zones(sb, zones, dry_run=False):\n",
        1,
    ),
    # 2. Call recheck_breached_zones in main() after OHLCV loads, before
    #    weekly/daily detection. Anchored on the OHLCV count log line + if do_weekly.
    (
        "Call recheck_breached_zones after OHLCV load",
        "        log(f\"  {len(daily_ohlcv)} trading days loaded\")\n"
        "\n"
        "        if do_weekly:\n",
        "        log(f\"  {len(daily_ohlcv)} trading days loaded\")\n"
        "\n"
        "        # TD-030 fix: recheck breach on existing ACTIVE zones\n"
        "        recheck_breached_zones(sb, symbol, daily_ohlcv, str(target_date), dry_run)\n"
        "\n"
        "        if do_weekly:\n",
        1,
    ),
    # 3. TD-031: split filter for weekly zones -- OB/FVG unconditional, PDH/PDL filtered.
    #    Anchored on the weekly detection block (unique via "weekly zones" log lines +
    #    log_exec.record_write which was added by the F3 patch).
    (
        "TD-031: split breach filter for weekly zones",
        "            w_zones = detect_weekly_zones(weekly_bars, symbol)\n"
        "            w_zones = filter_breached_zones(w_zones, daily_ohlcv, str(target_date))\n"
        "            log(f\"  Detected {len(w_zones)} weekly zones (after breach filter)\")\n"
        "            n = upsert_zones(sb, w_zones, dry_run)\n"
        "            log_exec.record_write(\"ict_htf_zones\", n)\n"
        "            log(f\"  Written {n} weekly zones\")\n"
        "            total_written += n\n",
        "            w_zones = detect_weekly_zones(weekly_bars, symbol)\n"
        "            # TD-031 fix: OB/FVG written unconditionally -- fresh structure\n"
        "            # regardless of overnight recovery. PDH/PDL still proximity-filtered.\n"
        "            _w_ob  = [z for z in w_zones if z[\"pattern_type\"] not in (\"PDH\", \"PDL\")]\n"
        "            _w_pdl = filter_breached_zones(\n"
        "                [z for z in w_zones if z[\"pattern_type\"] in (\"PDH\", \"PDL\")],\n"
        "                daily_ohlcv, str(target_date)\n"
        "            )\n"
        "            w_zones = _w_ob + _w_pdl\n"
        "            log(f\"  Detected {len(w_zones)} weekly zones ({len(_w_ob)} OB/FVG + {len(_w_pdl)} PDH/PDL)\")\n"
        "            n = upsert_zones(sb, w_zones, dry_run)\n"
        "            log_exec.record_write(\"ict_htf_zones\", n)\n"
        "            log(f\"  Written {n} weekly zones\")\n"
        "            total_written += n\n",
        1,
    ),
    # 4. TD-031: same split for daily zones.
    (
        "TD-031: split breach filter for daily zones",
        "            d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)\n"
        "            d_zones = filter_breached_zones(d_zones, daily_ohlcv, str(target_date))\n"
        "            log(f\"  Detected {len(d_zones)} daily zones (after breach filter)\")\n"
        "            n = upsert_zones(sb, d_zones, dry_run)\n"
        "            log_exec.record_write(\"ict_htf_zones\", n)\n"
        "            log(f\"  Written {n} daily zones\")\n"
        "            total_written += n\n",
        "            d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)\n"
        "            # TD-031 fix: same as weekly -- OB/FVG unconditional.\n"
        "            _d_ob  = [z for z in d_zones if z[\"pattern_type\"] not in (\"PDH\", \"PDL\")]\n"
        "            _d_pdl = filter_breached_zones(\n"
        "                [z for z in d_zones if z[\"pattern_type\"] in (\"PDH\", \"PDL\")],\n"
        "                daily_ohlcv, str(target_date)\n"
        "            )\n"
        "            d_zones = _d_ob + _d_pdl\n"
        "            log(f\"  Detected {len(d_zones)} daily zones ({len(_d_ob)} OB/FVG + {len(_d_pdl)} PDH/PDL)\")\n"
        "            n = upsert_zones(sb, d_zones, dry_run)\n"
        "            log_exec.record_write(\"ict_htf_zones\", n)\n"
        "            log(f\"  Written {n} daily zones\")\n"
        "            total_written += n\n",
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

    if "recheck_breached_zones" in text:
        sys.stderr.write("ERROR: patch already applied. Restore from backup first.\n")
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
    print("  1. python build_ict_htf_zones.py --dry-run")
    print("     Look for: 'Rechecking breached zones for NIFTY @ spot ...'")
    print("     And:      'Detected N weekly zones (M OB/FVG + K PDH/PDL)'")
    print("  2. python build_ict_htf_zones.py --timeframe both")
    print("     Check script_execution_log row: contract_met=true")
    print("  3. Query ict_htf_zones:")
    print("     SELECT pattern_type, symbol, status, valid_from, zone_low, zone_high")
    print("       FROM ict_htf_zones")
    print("      WHERE status IN ('ACTIVE','BREACHED')")
    print("        AND valid_from >= '2026-04-28'")
    print("      ORDER BY valid_from, symbol, pattern_type;")
    print("  4. Confirm next down day: D BEAR_OB appears in ict_htf_zones ACTIVE")
    print("     at 08:45 IST even if overnight recovery is partial.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
