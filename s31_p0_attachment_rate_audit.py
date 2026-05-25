"""
s31_p0_attachment_rate_audit.py

TD-S30-NEW-3 closure verification (Session 31 P0 step 8).

Pure offline simulation of post-patch attachment rate. Imports the
patched `enrich_signal_with_ict()` from `detect_ict_patterns.py`
(which lives in the same dir post-deploy of S31) and applies it to
the same 8-week cohort the S30 audit measured.

No DB writes. No replay orchestrator. Audit-only.

Methodology mirror of s30_gate_audit_and_ob_attachment.py zone-touch
join, but the per-row attachment decision is recomputed using the
patched function instead of being read from the historical
signal_snapshots.ict_pattern column (which was written by the OLD
function).

Output:
  - Per-pattern attachment rate (BULL_OB, BEAR_OB, BULL_FVG, BEAR_FVG)
  - Per-pattern sub-cohort N (new, post-fix)
  - Per-symbol breakdown
  - Pre/post comparison table
  - Pass/fail vs operational threshold (>=80% per TD-S30-NEW-3)

Usage (Local Windows):
    python s31_p0_attachment_rate_audit.py

Optional:
    --start-date 2026-03-23
    --end-date   2026-05-15
    --symbols NIFTY,SENSEX
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

from dotenv import load_dotenv
from supabase import create_client

# Import the patched functions. THIS IS THE POINT — if the patch isn't
# deployed, this audit returns pre-fix numbers. Confirm marker presence
# before relying on output.
try:
    from detect_ict_patterns import enrich_signal_with_ict, get_best_active_zone  # noqa: F401
except ImportError as e:
    print(f"FATAL: cannot import enrich_signal_with_ict from detect_ict_patterns: {e}",
          file=sys.stderr)
    print("Run this script from C:\\GammaEnginePython\\ (Local) "
          "or /home/ssm-user/meridian-engine/ (AWS).", file=sys.stderr)
    sys.exit(1)

# Marker presence check — verify the patched function is actually in scope
import detect_ict_patterns as _dip
import inspect as _insp
_src = _insp.getsource(_dip.enrich_signal_with_ict)
if "TD-S30-NEW-3 fix (Session 31)" not in _src:
    print("FATAL: enrich_signal_with_ict() does NOT contain S31 marker.",
          file=sys.stderr)
    print("Run apply_s31_ob_attachment.py --live before this audit.",
          file=sys.stderr)
    sys.exit(2)


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
p.add_argument("--start-date", default="2026-03-23",
               help="Cohort start (IST date). Default: S30 cohort start.")
p.add_argument("--end-date", default="2026-05-15",
               help="Cohort end (IST date). Default: S30 cohort end.")
p.add_argument("--symbols", default="NIFTY,SENSEX",
               help="Comma-separated symbols.")
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


# ── Pull cohort + zones ───────────────────────────────────────────────

def fetch_signals_paginated(symbol: str) -> list[dict]:
    """Pull all signal_snapshots in cohort window for symbol."""
    out = []
    page = 0
    PAGE_SIZE = 1000
    while True:
        rows = (SB.table("signal_snapshots")
                .select("ts,symbol,spot,action,ict_pattern,direction_bias,gamma_regime")
                .eq("symbol", symbol)
                .gte("ts", f"{START}T00:00:00+00:00")
                .lte("ts", f"{END}T23:59:59+00:00")
                .order("ts")
                .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)
                .execute().data)
        if not rows:
            break
        out.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return out


def fetch_zones_for_dates(symbol: str, dates: set[str]) -> dict[str, list[dict]]:
    """Fetch all ict_zones for symbol × dates. Group by trade_date."""
    out: dict[str, list[dict]] = defaultdict(list)
    for d in sorted(dates):
        rows = (SB.table("ict_zones")
                .select("id,symbol,trade_date,pattern_type,direction,zone_high,zone_low,"
                        "status,ict_tier,ict_size_mult,mtf_context,detected_at_ts")
                .eq("symbol", symbol)
                .eq("trade_date", d)
                .execute().data)
        out[d] = rows
    return out


# ── IST date extraction ───────────────────────────────────────────────

def ist_date(ts_str: str) -> str:
    """Given a UTC ISO ts, return the IST calendar date as YYYY-MM-DD."""
    try:
        # Handle Postgres '+00' short suffix
        s = ts_str.replace(" ", "T")
        if s.endswith("+00"):
            s = s[:-3] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
        return ist.date().isoformat()
    except Exception:
        return ""


# ── Per-row simulation ────────────────────────────────────────────────

def simulate_row(signal_row: dict, zones_by_date: dict[str, list[dict]]) -> dict:
    """Apply patched enrich_signal_with_ict() to a historical signal row.

    Returns: copy of signal_row with simulated_ict_pattern populated.
    """
    d = ist_date(signal_row["ts"])
    candidate_zones = zones_by_date.get(d, [])
    # Filter to ACTIVE only — mirror S30 audit's status='ACTIVE' join.
    active = [z for z in candidate_zones if z.get("status") == "ACTIVE"]
    spot = float(signal_row.get("spot") or 0)
    sd = {"action": signal_row.get("action", "DO_NOTHING")}
    result = enrich_signal_with_ict(sd, active, spot)
    out = dict(signal_row)
    out["simulated_ict_pattern"] = result.get("ict_pattern", "NONE")
    out["simulated_ict_tier"] = result.get("ict_tier", "NONE")
    out["simulated_ict_mtf"] = result.get("ict_mtf_context", "NONE")
    return out


# ── Zone-touch tally (mirror S30 audit) ───────────────────────────────

def tally(rows: list[dict], zones_by_date_by_symbol: dict[str, dict[str, list[dict]]]) -> dict:
    """For each OB/FVG pattern, compute:
      - zone_touches: # of (signal_row, zone) pairs where spot ∈ zone
      - attached_correct: # where simulated_ict_pattern == zone.pattern_type
      - attached_other:   # where simulated picked a DIFFERENT zone
      - attached_none:    # where simulated returned NONE (zone fell out — bug?)
    """
    pat_stats = defaultdict(lambda: {"touches": 0, "correct": 0,
                                     "other": 0, "none": 0,
                                     "by_symbol": defaultdict(lambda: {"t": 0, "c": 0})})
    pre_fix_tagged = defaultdict(int)

    for r in rows:
        sym = r["symbol"]
        d = ist_date(r["ts"])
        spot = float(r.get("spot") or 0)
        if spot <= 0:
            continue
        zones = zones_by_date_by_symbol.get(sym, {}).get(d, [])
        for z in zones:
            if z.get("status") != "ACTIVE":
                continue
            try:
                zl = float(z["zone_low"])
                zh = float(z["zone_high"])
            except (TypeError, ValueError, KeyError):
                continue
            if not (zl <= spot <= zh):
                continue
            pt = z["pattern_type"]
            pat_stats[pt]["touches"] += 1
            pat_stats[pt]["by_symbol"][sym]["t"] += 1
            sim = r.get("simulated_ict_pattern", "NONE")
            if sim == pt:
                pat_stats[pt]["correct"] += 1
                pat_stats[pt]["by_symbol"][sym]["c"] += 1
            elif sim == "NONE":
                pat_stats[pt]["none"] += 1
            else:
                pat_stats[pt]["other"] += 1
            # Pre-fix observation
            if r.get("ict_pattern") == pt:
                pre_fix_tagged[pt] += 1

    return {"per_pattern": dict(pat_stats), "pre_fix_tagged": dict(pre_fix_tagged)}


# ── Main ──────────────────────────────────────────────────────────────

def main() -> int:
    print(f"S31 P0 attachment-rate audit")
    print(f"Cohort: {START} → {END} ({SYMBOLS})")
    print(f"Patched function source has S31 marker: confirmed")
    print()

    all_rows: list[dict] = []
    zones_by_symbol: dict[str, dict[str, list[dict]]] = {}

    for sym in SYMBOLS:
        print(f"Fetching signal_snapshots for {sym} ...", end=" ", flush=True)
        rows = fetch_signals_paginated(sym)
        print(f"{len(rows):,} rows")
        dates_needed = set(ist_date(r["ts"]) for r in rows if r.get("ts"))
        print(f"Fetching ict_zones for {sym} across {len(dates_needed)} trade_dates ...",
              end=" ", flush=True)
        zbd = fetch_zones_for_dates(sym, dates_needed)
        n_zones = sum(len(v) for v in zbd.values())
        print(f"{n_zones:,} zones")
        zones_by_symbol[sym] = zbd

        # Simulate
        print(f"Simulating attachment for {sym} ...", end=" ", flush=True)
        for r in rows:
            sim = simulate_row(r, zbd)
            all_rows.append(sim)
        print(f"done ({len(rows):,} rows)")
        print()

    # Tally
    print(f"Tallying zone-touch attachment ...")
    stats = tally(all_rows, zones_by_symbol)

    print()
    print("=" * 78)
    print("ATTACHMENT RATES — POST-FIX SIMULATION")
    print("=" * 78)
    print()
    print(f"{'Pattern':<10} {'Touches':>10} {'Attached':>10} {'Other':>8} "
          f"{'NONE':>8} {'Rate':>8}  PreFix-Rate")
    print("-" * 78)
    for pt in ("BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"):
        s = stats["per_pattern"].get(pt)
        if s is None:
            print(f"{pt:<10} (no touches in cohort)")
            continue
        t = s["touches"]
        c = s["correct"]
        o = s["other"]
        n = s["none"]
        rate = (c / t * 100.0) if t else 0.0
        pre = stats["pre_fix_tagged"].get(pt, 0)
        pre_rate = (pre / t * 100.0) if t else 0.0
        print(f"{pt:<10} {t:>10,} {c:>10,} {o:>8,} {n:>8,} {rate:>7.1f}%  "
              f"{pre:>6,} ({pre_rate:>5.1f}%)")

    # Per-symbol BULL_OB / BEAR_OB
    print()
    print("BULL_OB + BEAR_OB by symbol:")
    for pt in ("BULL_OB", "BEAR_OB"):
        s = stats["per_pattern"].get(pt)
        if not s:
            continue
        for sym, bb in sorted(s["by_symbol"].items()):
            t = bb["t"]
            c = bb["c"]
            rate = (c / t * 100.0) if t else 0.0
            print(f"  {pt:<10} {sym:<8} touches={t:>5,}  attached={c:>5,}  "
                  f"rate={rate:>5.1f}%")

    # Threshold check
    print()
    bull_ob = stats["per_pattern"].get("BULL_OB", {"touches": 0, "correct": 0})
    bear_ob = stats["per_pattern"].get("BEAR_OB", {"touches": 0, "correct": 0})
    bull_rate = (bull_ob["correct"] / bull_ob["touches"] * 100.0) if bull_ob["touches"] else 0.0
    bear_rate = (bear_ob["correct"] / bear_ob["touches"] * 100.0) if bear_ob["touches"] else 0.0

    print("=" * 78)
    print("THRESHOLD CHECK (per TD-S30-NEW-3 closure criterion: >=80%)")
    print("=" * 78)
    print(f"  BULL_OB attachment rate: {bull_rate:.1f}%  "
          f"{'PASS' if bull_rate >= 80.0 else 'FAIL'}")
    print(f"  BEAR_OB attachment rate: {bear_rate:.1f}%  "
          f"{'PASS' if bear_rate >= 80.0 else 'FAIL'}")
    print()
    print(f"NEW SUB-COHORT N (post-fix, for live-cohort re-validation):")
    print(f"  BULL_OB:  N={bull_ob['correct']:,}  (was {stats['pre_fix_tagged'].get('BULL_OB',0):,} pre-fix)")
    print(f"  BEAR_OB:  N={bear_ob['correct']:,}  (was {stats['pre_fix_tagged'].get('BEAR_OB',0):,} pre-fix)")
    return 0 if (bull_rate >= 80.0 and bear_rate >= 80.0) else 1


if __name__ == "__main__":
    sys.exit(main())
