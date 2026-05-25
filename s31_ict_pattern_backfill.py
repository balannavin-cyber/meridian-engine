"""
s31_ict_pattern_backfill.py — TD-S30-NEW-3 historical backfill.

Rewrites signal_snapshots.ict_pattern + ict_tier + ict_size_mult +
ict_mtf_context on historical rows using the S31-patched
enrich_signal_with_ict() (observational attachment). Marks each
backfilled row with raw->>'ict_pattern_backfilled' = 'S31_observational'
for provenance.

Zone validity is reconstructed by timestamp predicate rather than
current `status` column:
  zone.detected_at_ts <= signal.ts
  AND (zone.broken_at_ts IS NULL OR zone.broken_at_ts > signal.ts)

This recovers historical zone-touch context even though current zone
status may be BREACHED/EXPIRED — we ask "was this zone ACTIVE at
signal_ts" not "is it ACTIVE now".

Scope: 2026-03-23 → 2026-05-15 (S30 cohort window). Override via
--start-date / --end-date.

Idempotency: skips rows whose raw->>'ict_pattern_backfilled' is already
'S31_observational'.

Usage (Local Windows, after S31 P0 patch is on disk):
    python s31_ict_pattern_backfill.py --dry-run
    python s31_ict_pattern_backfill.py --live
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client

# Import patched function — abort if S31 marker not present
try:
    from detect_ict_patterns import enrich_signal_with_ict
    import detect_ict_patterns as _dip
    import inspect as _insp
    _src = _insp.getsource(_dip.enrich_signal_with_ict)
    if "TD-S30-NEW-3 fix (Session 31)" not in _src:
        print("FATAL: enrich_signal_with_ict() does NOT contain S31 marker.",
              file=sys.stderr)
        print("Apply S31 P0 patch before running backfill.", file=sys.stderr)
        sys.exit(2)
except ImportError as e:
    print(f"FATAL: cannot import enrich_signal_with_ict: {e}", file=sys.stderr)
    sys.exit(1)


IST = timezone(timedelta(hours=5, minutes=30))


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
g = p.add_mutually_exclusive_group(required=True)
g.add_argument("--dry-run", action="store_true",
               help="Report transitions only; no DB writes.")
g.add_argument("--live", action="store_true",
               help="Write updates to signal_snapshots.")
p.add_argument("--start-date", default="2026-03-23",
               help="IST cohort start. Default: S30 cohort start.")
p.add_argument("--end-date", default="2026-05-15",
               help="IST cohort end. Default: S30 cohort end.")
p.add_argument("--symbols", default="NIFTY,SENSEX")
p.add_argument("--batch-report-every", type=int, default=500,
               help="Print progress every N rows.")
args = p.parse_args()

SYMBOLS = [s.strip().upper() for s in args.symbols.split(",")]
START = args.start_date
END = args.end_date


# ── Supabase ──────────────────────────────────────────────────────────

load_dotenv()
SB = create_client(
    os.getenv("SUPABASE_URL").strip(),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
)


# ── Helpers ──────────────────────────────────────────────────────────

def parse_ts(ts_str):
    if not ts_str:
        return None
    s = ts_str.replace(" ", "T")
    if s.endswith("+00"):
        s = s[:-3] + "+00:00"
    # Normalize microsecond padding
    import re
    m = re.search(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$", s)
    if m and len(m.group(1)) > 6:
        s = re.sub(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$",
                   f".{m.group(1)[:6]}{m.group(2) or ''}", s)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def ist_date(ts_str):
    dt = parse_ts(ts_str)
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).date().isoformat()


# ── Fetch cohort ─────────────────────────────────────────────────────

def fetch_signals(symbol):
    out, page = [], 0
    PAGE = 1000
    while True:
        rows = (SB.table("signal_snapshots")
                .select("id,ts,symbol,spot,action,ict_pattern,ict_tier,"
                        "ict_size_mult,ict_mtf_context,raw")
                .eq("symbol", symbol)
                .gte("ts", f"{START}T00:00:00+00:00")
                .lte("ts", f"{END}T23:59:59+00:00")
                .order("ts")
                .range(page * PAGE, (page + 1) * PAGE - 1)
                .execute().data)
        if not rows:
            break
        out.extend(rows)
        if len(rows) < PAGE:
            break
        page += 1
    return out


def fetch_zones_for_dates(symbol, dates):
    """Fetch ALL ict_zones for symbol × dates regardless of current status.
    Returns dict[trade_date] -> list[zone_rows] with broken_at_ts included.
    """
    out = defaultdict(list)
    for d in sorted(dates):
        rows = (SB.table("ict_zones")
                .select("id,symbol,trade_date,pattern_type,direction,"
                        "zone_high,zone_low,status,ict_tier,ict_size_mult,"
                        "mtf_context,detected_at_ts,broken_at_ts")
                .eq("symbol", symbol)
                .eq("trade_date", d)
                .execute().data)
        out[d] = rows
    return out


# ── Per-row backfill ─────────────────────────────────────────────────

def valid_zones_at(signal_ts_str, zones):
    """Reconstruct zones ACTIVE at signal_ts via timestamp predicate."""
    sig_ts = parse_ts(signal_ts_str)
    if sig_ts is None:
        return []
    out = []
    for z in zones:
        det = parse_ts(z.get("detected_at_ts"))
        if det is None or det > sig_ts:
            continue
        brk = parse_ts(z.get("broken_at_ts"))
        if brk is not None and brk <= sig_ts:
            continue
        # Synthesize ACTIVE status for the enrich function
        zc = dict(z)
        zc["status"] = "ACTIVE"
        out.append(zc)
    return out


def simulate_attachment(signal_row, valid_zones):
    """Apply patched enrich to one row. Returns dict of new field values."""
    spot = float(signal_row.get("spot") or 0)
    sd = {"action": signal_row.get("action", "DO_NOTHING")}
    result = enrich_signal_with_ict(sd, valid_zones, spot)
    return {
        "ict_pattern":     result.get("ict_pattern", "NONE"),
        "ict_tier":        result.get("ict_tier", "NONE"),
        "ict_size_mult":   result.get("ict_size_mult", 1.0),
        "ict_mtf_context": result.get("ict_mtf_context", "NONE"),
    }


def has_marker(row):
    raw = row.get("raw") or {}
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            return False
    return raw.get("ict_pattern_backfilled") == "S31_observational"


def update_row(row_id, new_fields, existing_raw):
    raw_out = dict(existing_raw) if existing_raw else {}
    raw_out["ict_pattern_backfilled"] = "S31_observational"
    payload = dict(new_fields)
    payload["raw"] = raw_out
    return (SB.table("signal_snapshots")
            .update(payload)
            .eq("id", row_id)
            .execute())


# ── Main ──────────────────────────────────────────────────────────────

def main():
    print(f"S31 ict_pattern backfill")
    print(f"Cohort: {START} → {END}  symbols={SYMBOLS}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE WRITES'}")
    print()

    grand_totals = {
        "scanned": 0,
        "skipped_marker": 0,
        "unchanged": 0,
        "rewritten": 0,
        "transitions": Counter(),
    }

    for symbol in SYMBOLS:
        print(f"=== {symbol} ===")
        print(f"Fetching signals ...", end=" ", flush=True)
        signals = fetch_signals(symbol)
        print(f"{len(signals):,}")

        dates_needed = set(ist_date(r["ts"]) for r in signals if r.get("ts"))
        print(f"Fetching zones for {len(dates_needed)} trade_dates ...",
              end=" ", flush=True)
        zones_by_date = fetch_zones_for_dates(symbol, dates_needed)
        n_zones = sum(len(v) for v in zones_by_date.values())
        print(f"{n_zones:,}")

        sym_scanned = 0
        sym_skipped = 0
        sym_unchanged = 0
        sym_rewritten = 0
        sym_transitions = Counter()

        for i, row in enumerate(signals):
            sym_scanned += 1
            if has_marker(row):
                sym_skipped += 1
                continue
            d = ist_date(row["ts"])
            day_zones = zones_by_date.get(d, [])
            valid = valid_zones_at(row["ts"], day_zones)
            new = simulate_attachment(row, valid)
            old_pattern = row.get("ict_pattern") or "NONE"
            new_pattern = new["ict_pattern"]

            changed = (
                old_pattern != new_pattern
                or (row.get("ict_tier") or "NONE") != new["ict_tier"]
                or float(row.get("ict_size_mult") or 1.0) != float(new["ict_size_mult"])
                or (row.get("ict_mtf_context") or "NONE") != new["ict_mtf_context"]
            )

            if not changed:
                sym_unchanged += 1
                # Still mark as backfilled for provenance + idempotency
                if args.live:
                    existing_raw = row.get("raw") or {}
                    if isinstance(existing_raw, str):
                        import json
                        try:
                            existing_raw = json.loads(existing_raw)
                        except Exception:
                            existing_raw = {}
                    try:
                        update_row(row["id"], new, existing_raw)
                    except Exception as e:
                        print(f"  WARN: marker-only update failed id={row['id']}: {e}")
                continue

            sym_rewritten += 1
            sym_transitions[(old_pattern, new_pattern)] += 1

            if args.live:
                existing_raw = row.get("raw") or {}
                if isinstance(existing_raw, str):
                    import json
                    try:
                        existing_raw = json.loads(existing_raw)
                    except Exception:
                        existing_raw = {}
                try:
                    update_row(row["id"], new, existing_raw)
                except Exception as e:
                    print(f"  WARN: update failed id={row['id']}: {e}")

            if (sym_scanned % args.batch_report_every) == 0:
                print(f"  ... {sym_scanned:,}/{len(signals):,}  "
                      f"rewritten={sym_rewritten:,}")

        print()
        print(f"{symbol} totals:")
        print(f"  scanned          {sym_scanned:>6,}")
        print(f"  skipped (marker) {sym_skipped:>6,}")
        print(f"  unchanged        {sym_unchanged:>6,}")
        print(f"  rewritten        {sym_rewritten:>6,}")
        print(f"  top transitions:")
        for (o, n), c in sym_transitions.most_common(10):
            print(f"    {o:<10} → {n:<10}  N={c:>5,}")
        print()

        grand_totals["scanned"] += sym_scanned
        grand_totals["skipped_marker"] += sym_skipped
        grand_totals["unchanged"] += sym_unchanged
        grand_totals["rewritten"] += sym_rewritten
        for k, v in sym_transitions.items():
            grand_totals["transitions"][k] += v

    print("=" * 78)
    print(f"GRAND TOTAL")
    print("=" * 78)
    print(f"  scanned          {grand_totals['scanned']:>6,}")
    print(f"  skipped (marker) {grand_totals['skipped_marker']:>6,}")
    print(f"  unchanged        {grand_totals['unchanged']:>6,}")
    print(f"  rewritten        {grand_totals['rewritten']:>6,}")
    print(f"  top transitions:")
    for (o, n), c in grand_totals["transitions"].most_common(15):
        print(f"    {o:<10} → {n:<10}  N={c:>5,}")
    print()
    print(f"Mode was {'DRY-RUN — no DB writes' if args.dry_run else 'LIVE — writes committed'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
