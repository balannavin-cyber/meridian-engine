"""
backfill_gamma_metrics_broken_window.py — S28 P0 + P1 combined

Purpose:
  Re-run PATCHED compute_gamma_metrics_local against historical
  option_chain_snapshots cycles in a date range. Three-gate verify per cycle.
  Optionally UPSERT corrected values back to gamma_metrics on (symbol, ts).

Default: --dry-run (no writes). --live --confirm required for actual UPSERT.

Pattern source: verify_td_new_2_flip_level.py (S27 — importlib + sys.modules
registration for @dataclass GammaMetricsResult).

Usage:
  # dry-run, single day, both symbols
  python backfill_gamma_metrics_broken_window.py --date 2026-05-11

  # dry-run, broken window range
  python backfill_gamma_metrics_broken_window.py --start 2026-05-08 --end 2026-05-11

  # actually UPSERT (P1 backfill)
  python backfill_gamma_metrics_broken_window.py --start 2026-05-08 --end 2026-05-11 --live --confirm

  # narrow to one symbol
  python backfill_gamma_metrics_broken_window.py --date 2026-05-11 --symbol NIFTY
"""

import argparse
import importlib.util
import os
import sys
from pathlib import Path

# ============================================================
# importlib pattern for compute_gamma_metrics_local (PATCHED)
# sys.modules registration MUST precede exec_module because the
# module declares @dataclass GammaMetricsResult.
# ============================================================
MODULE_NAME = "compute_gamma_metrics_local"
MODULE_PATH = Path(__file__).resolve().parent / f"{MODULE_NAME}.py"

if not MODULE_PATH.exists():
    sys.exit(f"FATAL: {MODULE_PATH} not found. Run from repo root.")

spec = importlib.util.spec_from_file_location(MODULE_NAME, str(MODULE_PATH))
mod = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = mod
spec.loader.exec_module(mod)

# ============================================================
# Supabase client (same env convention as other production scripts)
# ============================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client

SUPA_URL = os.environ.get("SUPABASE_URL")
SUPA_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
if not (SUPA_URL and SUPA_KEY):
    sys.exit("FATAL: SUPABASE_URL / SUPABASE_KEY not in env.")
SUPA = create_client(SUPA_URL, SUPA_KEY)

# ============================================================
# Three-gate thresholds (S28 P0 verification criteria)
# ============================================================
FLIP_NEAR_SPOT_PCT = 0.02      # flip within 2% of spot
NETGEX_MIN_CR = 100
NETGEX_MAX_CR = 1_000_000


# ============================================================
# >>> TODO 1: Confirm option_chain_snapshots schema <<<
# Adjust columns / JSONB extraction to match your actual table.
# ============================================================
def fetch_cycles(start_date, end_date, symbol=None):
    """Returns list of cycle dicts ordered by ts."""
    q = (SUPA.table("option_chain_snapshots")
              .select("id, run_id, symbol, ts, spot, raw")
              .gte("ts", f"{start_date}T00:00:00+05:30")
              .lte("ts", f"{end_date}T23:59:59+05:30"))
    if symbol:
        q = q.eq("symbol", symbol)
    return q.order("ts").execute().data


# ============================================================
# >>> TODO 2: Confirm function names in compute_gamma_metrics_local <<<
# From S27 audit the module exports at least:
#   - signed_gamma_exposure(rows, spot, symbol)
#   - compute_flip_level(rows_or_aggregates, spot=spot)
#   - determine_regime(net_gex)
# If your module uses different names or different call signatures,
# adjust here. If there's a single top-level entry that returns
# GammaMetricsResult, prefer that — keeps parity with live writer.
# ============================================================
def patched_compute(rows, spot, symbol):
    """Run PATCHED pure functions on one cycle. Return dict of derived metrics."""
    sg = mod.signed_gamma_exposure(rows, spot, symbol)
    # signed_gamma_exposure may return a dict with net_gex + per-strike rows.
    # compute_flip_level may consume the per-strike data; adapt as needed.
    flip = mod.compute_flip_level(sg, spot=spot)
    net_gex = sg["net_gex"] if isinstance(sg, dict) and "net_gex" in sg else sg
    regime = mod.determine_regime(net_gex) if hasattr(mod, "determine_regime") else None
    flip_dist_pct = (abs(flip - spot) / spot) if (flip and spot) else None
    return {
        "net_gex": net_gex,
        "flip_level": flip,
        "regime": regime,
        "flip_distance_pct": flip_dist_pct,
    }


def three_gates(result, spot):
    flip = result["flip_level"]
    ng = result["net_gex"]
    gates = {
        "flip_near_spot": (flip is not None) and (abs(flip - spot) / spot <= FLIP_NEAR_SPOT_PCT),
        "netgex_in_cr_range": (ng is not None) and (NETGEX_MIN_CR < abs(ng) < NETGEX_MAX_CR),
        "regime_present": result["regime"] is not None,
    }
    return all(gates.values()), gates


# ============================================================
# >>> TODO 3: Confirm gamma_metrics write contract <<<
# V18A baseline says gamma_metrics has gamma_zone + raw + UPSERT on (symbol, ts).
# If your live writer also writes gamma_zone, expansion_probability, structural
# manipulation flags, etc — add them to the payload below to maintain parity.
# Missing columns will be NULL on backfilled rows.
# ============================================================
def upsert_gamma_metrics(symbol, ts, spot, result, source_run_id):
    payload = {
        "symbol": symbol,
        "ts": ts,
        "spot": spot,
        "net_gex": result["net_gex"],
        "flip_level": result["flip_level"],
        "flip_distance_pct": result["flip_distance_pct"],
        "regime": result["regime"],
        "raw": {
            "backfill_source": "S28_P1_broken_window",
            "patched_compute": True,
            "td_new_2_applied": True,
            "td_new_3_applied": True,
            "source_run_id": str(source_run_id),
        },
    }
    SUPA.table("gamma_metrics").upsert(payload, on_conflict="symbol,ts").execute()


# ============================================================
# Main
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--date", help="single day YYYY-MM-DD")
    g.add_argument("--start", help="range start YYYY-MM-DD (requires --end)")
    ap.add_argument("--end", help="range end YYYY-MM-DD")
    ap.add_argument("--symbol", choices=["NIFTY", "SENSEX"], help="default both")
    ap.add_argument("--live", action="store_true", help="actually UPSERT (default dry-run)")
    ap.add_argument("--confirm", action="store_true", help="required with --live")
    ap.add_argument("--max-detail", type=int, default=10, help="cycles to print in detail")
    args = ap.parse_args()

    if args.date:
        start = end = args.date
    else:
        if not args.end:
            ap.error("--start requires --end")
        start, end = args.start, args.end

    if args.live and not args.confirm:
        ap.error("--live requires --confirm (writes to gamma_metrics)")

    print(f"Range:  {start} → {end}")
    print(f"Symbol: {args.symbol or 'BOTH'}")
    print(f"Mode:   {'LIVE UPSERT' if args.live else 'DRY-RUN'}")
    print(f"Module: {MODULE_PATH}")
    print()

    cycles = fetch_cycles(start, end, args.symbol)
    print(f"Fetched {len(cycles)} cycles\n")
    if not cycles:
        sys.exit("No cycles found. Check date range and symbol filter.")

    pass_count = 0
    fail_count = 0
    upsert_count = 0
    err_count = 0
    failures = []

    print(f"{'#':>5} {'ts':<26} {'sym':<6} {'spot':>10} {'flip':>10} {'Δ%':>8} {'net_gex_Cr':>14} {'regime':<8} gates")
    print("-" * 120)

    for i, c in enumerate(cycles):
        symbol = c["symbol"]
        ts = c["ts"]
        spot = c["spot"]
        # >>> TODO 1b: confirm how `rows` is extracted from `raw`
        rows = c["raw"] if not isinstance(c.get("raw"), dict) or "chain" not in c["raw"] else c["raw"]["chain"]

        try:
            result = patched_compute(rows, spot, symbol)
            ok, gates = three_gates(result, spot)
            gate_str = "".join("✓" if v else "✗" for v in gates.values())

            if i < args.max_detail or not ok:
                flip = result["flip_level"]
                ng = result["net_gex"]
                dpct = result["flip_distance_pct"]
                print(f"{i:>5} {str(ts):<26} {symbol:<6} {spot:>10.2f} "
                      f"{(flip or 0):>10.2f} {((dpct or 0)*100):>7.2f}% "
                      f"{(ng or 0):>14.2f} {str(result['regime']):<8} {gate_str}")

            if ok:
                pass_count += 1
                if args.live:
                    upsert_gamma_metrics(symbol, ts, spot, result, c["run_id"])
                    upsert_count += 1
            else:
                fail_count += 1
                failures.append((ts, symbol, spot, result, gates))
        except Exception as e:
            err_count += 1
            failures.append((ts, symbol, spot, f"ERROR: {e}", None))
            print(f"{i:>5} {str(ts):<26} {symbol:<6} ERROR: {e}")

    print()
    print("=" * 60)
    print(f"Total:    {len(cycles)}")
    print(f"Pass:     {pass_count} ({100*pass_count/max(1,len(cycles)):.1f}%)")
    print(f"Fail:     {fail_count}")
    print(f"Error:    {err_count}")
    if args.live:
        print(f"UPSERTs:  {upsert_count}")
    print("=" * 60)

    if failures:
        print(f"\nFirst 20 failure/error rows:")
        for f in failures[:20]:
            print(f"  {f}")


if __name__ == "__main__":
    main()
