"""
Experiment 33 — Stage 2 Analyser

Reads experiment_33_analysis.csv (already produced) and answers four specific
questions about the breakout behavior:

  Q1: How many of the "broke at 09:15" cases were gap-ups (open > inside_high)
      or gap-downs (open < inside_low)?
  Q2: For gap cases, how much did it move BEYOND the gap?
      - day_high - open (post-gap upside excursion)
      - close - open  (post-gap directional follow-through)
  Q3: How many closed within +/-25pts of day high or day low? (trend-day closes)
  Q4: Did the next trading day gap in the same direction as expiry-day move?

This requires one extra data fetch per case: next-trading-day's first 1m bar.

Author: 2026-04-27 Session 10 close
"""

import os
import csv
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

ERA_BOUNDARY = date(2026, 4, 7)
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_CSV = os.path.join(WORKING_DIR, "experiment_33_analysis.csv")
OUTPUT_CSV   = os.path.join(WORKING_DIR, "experiment_33_stage2.csv")

CLOSE_AT_EXTREME_TOL = 25.0   # points

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ---------------------------------------------------------------------------
# Get instrument_ids
# ---------------------------------------------------------------------------

def load_instrument_ids():
    res = sb.table("instruments").select("id, symbol").execute()
    out = {}
    for r in res.data:
        sym = (r.get("symbol") or "").upper()
        if "NIFTY" in sym and "BANK" not in sym and "NIFTY" not in out:
            out["NIFTY"] = r["id"]
        elif "SENSEX" in sym and "SENSEX" not in out:
            out["SENSEX"] = r["id"]
    return out

# ---------------------------------------------------------------------------
# Get next trading day's open price from hist_spot_bars_1m
# ---------------------------------------------------------------------------

def get_next_trading_open(instrument_id, after_date):
    """Fetch the open price of the next trading day's first regular-session bar."""
    PAGE_SIZE = 1000
    candidate_dates = []
    # Find dates after `after_date` with bars
    res = (sb.table("hist_spot_bars_1m")
             .select("trade_date")
             .eq("instrument_id", instrument_id)
             .gt("trade_date", after_date.isoformat())
             .lte("trade_date", (after_date + timedelta(days=10)).isoformat())
             .order("trade_date")
             .range(0, PAGE_SIZE - 1).execute())
    seen = set()
    for r in res.data or []:
        td = r["trade_date"]
        if isinstance(td, str): td = date.fromisoformat(td)
        if td not in seen:
            candidate_dates.append(td)
            seen.add(td)
    if not candidate_dates:
        return None, None
    next_td = sorted(candidate_dates)[0]

    # Get the first non-pre-market 1m bar of that day
    res = (sb.table("hist_spot_bars_1m")
             .select("bar_ts, open, is_pre_market")
             .eq("instrument_id", instrument_id)
             .eq("trade_date", next_td.isoformat())
             .eq("is_pre_market", False)
             .order("bar_ts")
             .range(0, 5).execute())
    if not res.data:
        return next_td, None
    # Take the open of the first bar
    return next_td, float(res.data[0]["open"])

# ---------------------------------------------------------------------------
# Read prior analysis CSV
# ---------------------------------------------------------------------------

def read_analysis():
    if not os.path.exists(ANALYSIS_CSV):
        raise FileNotFoundError(f"Run experiment_33_analyse.py first to produce {ANALYSIS_CSV}")
    rows = []
    with open(ANALYSIS_CSV, "r", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log("=" * 70)
    log("Experiment 33 — Stage 2 (gaps, post-gap moves, close-at-extreme, next-day continuation)")
    log("=" * 70)

    instrument_ids = load_instrument_ids()
    rows = read_analysis()
    log(f"Loaded {len(rows)} rows from {ANALYSIS_CSV}")

    enriched = []
    for r in rows:
        inside_high = float(r["inside_high"])
        inside_low  = float(r["inside_low"])
        open_       = float(r["open"])
        close_      = float(r["close"])
        day_high    = float(r["day_high"])
        day_low     = float(r["day_low"])

        # Q1: Gap classification
        if open_ > inside_high:
            gap_dir = "GAP_UP"
            gap_pts = open_ - inside_high
        elif open_ < inside_low:
            gap_dir = "GAP_DOWN"
            gap_pts = inside_low - open_
        else:
            gap_dir = "INSIDE"
            gap_pts = 0.0

        # Q2: Post-gap moves
        post_gap_high_excursion = day_high - open_     # peak above open (always >= 0)
        post_gap_low_excursion  = open_ - day_low      # peak below open (always >= 0)
        post_gap_oc             = close_ - open_       # directional follow-through

        # Q3: Close at extreme
        close_to_high_dist = day_high - close_
        close_to_low_dist  = close_  - day_low
        if close_to_high_dist <= CLOSE_AT_EXTREME_TOL and close_to_low_dist > CLOSE_AT_EXTREME_TOL:
            close_at_extreme = "AT_HIGH"
        elif close_to_low_dist <= CLOSE_AT_EXTREME_TOL and close_to_high_dist > CLOSE_AT_EXTREME_TOL:
            close_at_extreme = "AT_LOW"
        elif close_to_high_dist <= CLOSE_AT_EXTREME_TOL and close_to_low_dist <= CLOSE_AT_EXTREME_TOL:
            close_at_extreme = "TIGHT_RANGE"  # both near close — narrow range day
        else:
            close_at_extreme = "MID"

        # Q4: Next-day gap
        expiry_date = date.fromisoformat(r["expiry_date"])
        next_td, next_open = get_next_trading_open(instrument_ids[r["symbol"]], expiry_date)
        next_gap_pts = None
        next_gap_pct = None
        next_gap_continuation = None
        if next_open is not None:
            next_gap_pts = next_open - close_
            next_gap_pct = (next_open / close_ - 1.0) * 100.0
            # Continuation = next-day gap is in the same direction as expiry-day move
            expiry_dir = "UP" if (close_ - open_) > 0 else "DOWN" if (close_ - open_) < 0 else "FLAT"
            next_dir   = "UP" if next_gap_pts > 0 else "DOWN" if next_gap_pts < 0 else "FLAT"
            if expiry_dir == "FLAT" or next_dir == "FLAT":
                next_gap_continuation = "FLAT"
            elif expiry_dir == next_dir:
                next_gap_continuation = "CONTINUATION"
            else:
                next_gap_continuation = "REVERSAL"

        enriched.append({
            "symbol":          r["symbol"],
            "expiry_type":     r["expiry_type"],
            "inside_date":     r["inside_date"],
            "expiry_date":     r["expiry_date"],
            "inside_low":      inside_low,
            "inside_high":     inside_high,
            "open":            open_,
            "high":            day_high,
            "low":             day_low,
            "close":           close_,
            "first_break_h_time": r["first_break_high_time"],
            "first_break_l_time": r["first_break_low_time"],
            "path_class":      r["path_class"],
            # Q1
            "gap_dir":              gap_dir,
            "gap_pts":              round(gap_pts, 2),
            # Q2
            "post_gap_high_excursion_pts": round(post_gap_high_excursion, 2),
            "post_gap_low_excursion_pts":  round(post_gap_low_excursion,  2),
            "post_gap_oc_pts":             round(post_gap_oc, 2),
            "post_gap_oc_pct":             round((close_ / open_ - 1.0) * 100.0, 3),
            # Q3
            "close_at_extreme":   close_at_extreme,
            "close_to_high_dist": round(close_to_high_dist, 2),
            "close_to_low_dist":  round(close_to_low_dist,  2),
            # Q4
            "next_trading_day":      next_td.isoformat() if next_td else None,
            "next_open":             round(next_open, 2) if next_open else None,
            "next_gap_pts":          round(next_gap_pts, 2) if next_gap_pts is not None else None,
            "next_gap_pct":          round(next_gap_pct, 3) if next_gap_pct is not None else None,
            "next_gap_continuation": next_gap_continuation,
        })

    # Per-case narratives
    log("\n" + "=" * 70)
    log("PER-CASE — Q1/Q2/Q3/Q4 ANSWERS")
    log("=" * 70)
    for r in enriched:
        log("")
        log(f"--- {r['symbol']} {r['expiry_type'].upper()} expiry {r['expiry_date']} (inside {r['inside_date']}) ---")
        log(f"  Inside bar: {r['inside_low']:.2f} - {r['inside_high']:.2f}")
        log(f"  Expiry day: O={r['open']:.2f} H={r['high']:.2f} L={r['low']:.2f} C={r['close']:.2f} | path={r['path_class']}")
        log(f"  Q1 GAP: {r['gap_dir']} (gap_pts={r['gap_pts']:.2f}, first_break_h={r['first_break_h_time'] or '-'}, first_break_l={r['first_break_l_time'] or '-'})")
        log(f"  Q2 POST-GAP: high_excursion={r['post_gap_high_excursion_pts']:+.2f}  low_excursion={r['post_gap_low_excursion_pts']:+.2f}  OC={r['post_gap_oc_pts']:+.2f}pts ({r['post_gap_oc_pct']:+.3f}%)")
        log(f"  Q3 CLOSE: {r['close_at_extreme']} (dist_to_high={r['close_to_high_dist']:.2f}, dist_to_low={r['close_to_low_dist']:.2f})")
        log(f"  Q4 NEXT-DAY: next_open={r['next_open']} on {r['next_trading_day']}, gap={r['next_gap_pts']}pts ({r['next_gap_pct']:+.3f}%) | direction={r['next_gap_continuation']}")

    # Aggregates
    log("\n" + "=" * 70)
    log("AGGREGATES")
    log("=" * 70)

    # Q1: Gap distribution
    log("\nQ1 — GAP DISTRIBUTION (expiry-day open vs inside-bar)")
    gap_counts = defaultdict(int)
    for r in enriched:
        gap_counts[r["gap_dir"]] += 1
    for k, v in sorted(gap_counts.items(), key=lambda x: -x[1]):
        log(f"  {k}: {v}/{len(enriched)} ({v/len(enriched)*100:.0f}%)")

    # Of those that broke at 09:15 — how many were gaps?
    log("\n  Of cases where first break = 09:15, gap distribution:")
    g915 = [r for r in enriched if (r["first_break_h_time"] == "09:15" or r["first_break_l_time"] == "09:15")]
    for k in ["GAP_UP", "GAP_DOWN", "INSIDE"]:
        cnt = sum(1 for r in g915 if r["gap_dir"] == k)
        log(f"    {k}: {cnt}/{len(g915)}")

    # Q2: Post-gap excursion stats
    log("\nQ2 — POST-GAP MOVE (only gap cases)")
    gap_up_rows   = [r for r in enriched if r["gap_dir"] == "GAP_UP"]
    gap_down_rows = [r for r in enriched if r["gap_dir"] == "GAP_DOWN"]
    if gap_up_rows:
        log(f"  GAP_UP cases (N={len(gap_up_rows)}):")
        for r in gap_up_rows:
            log(f"    {r['symbol']} {r['expiry_date']}: gap={r['gap_pts']:.2f}pts | post-gap excursion: high+{r['post_gap_high_excursion_pts']:.2f} / low-{r['post_gap_low_excursion_pts']:.2f} | close vs open: {r['post_gap_oc_pts']:+.2f}pts ({r['post_gap_oc_pct']:+.3f}%)")
        avg_post_gap_oc = sum(r["post_gap_oc_pts"] for r in gap_up_rows) / len(gap_up_rows)
        avg_post_gap_high_exc = sum(r["post_gap_high_excursion_pts"] for r in gap_up_rows) / len(gap_up_rows)
        log(f"    Mean post-gap OC: {avg_post_gap_oc:+.2f} pts")
        log(f"    Mean post-gap high excursion: {avg_post_gap_high_exc:.2f} pts (peak above gap-up open)")
    if gap_down_rows:
        log(f"  GAP_DOWN cases (N={len(gap_down_rows)}):")
        for r in gap_down_rows:
            log(f"    {r['symbol']} {r['expiry_date']}: gap={r['gap_pts']:.2f}pts | post-gap: high+{r['post_gap_high_excursion_pts']:.2f} / low-{r['post_gap_low_excursion_pts']:.2f} | OC: {r['post_gap_oc_pts']:+.2f}pts ({r['post_gap_oc_pct']:+.3f}%)")
        avg_post_gap_oc = sum(r["post_gap_oc_pts"] for r in gap_down_rows) / len(gap_down_rows)
        avg_post_gap_low_exc = sum(r["post_gap_low_excursion_pts"] for r in gap_down_rows) / len(gap_down_rows)
        log(f"    Mean post-gap OC: {avg_post_gap_oc:+.2f} pts")
        log(f"    Mean post-gap low excursion: {avg_post_gap_low_exc:.2f} pts (peak below gap-down open)")

    # Q3: Close at extreme
    log("\nQ3 — CLOSE WITHIN +/-25pts OF DAY EXTREME")
    close_counts = defaultdict(int)
    for r in enriched:
        close_counts[r["close_at_extreme"]] += 1
    for k in ["AT_HIGH", "AT_LOW", "TIGHT_RANGE", "MID"]:
        cnt = close_counts.get(k, 0)
        log(f"  {k}: {cnt}/{len(enriched)} ({cnt/len(enriched)*100:.0f}%)")

    # Q4: Next-day continuation
    log("\nQ4 — NEXT-DAY GAP DIRECTION VS EXPIRY-DAY MOVE")
    cont_counts = defaultdict(int)
    for r in enriched:
        if r["next_gap_continuation"]:
            cont_counts[r["next_gap_continuation"]] += 1
    for k in ["CONTINUATION", "REVERSAL", "FLAT"]:
        cnt = cont_counts.get(k, 0)
        log(f"  {k}: {cnt}/{len(enriched)} ({cnt/len(enriched)*100:.0f}%)")

    # Cross: of cases that closed AT_HIGH or AT_LOW, did next day continue?
    log("\nQ4 cross — of cases that closed AT_HIGH or AT_LOW, next-day direction:")
    at_extreme = [r for r in enriched if r["close_at_extreme"] in ("AT_HIGH", "AT_LOW")]
    for k in ["CONTINUATION", "REVERSAL", "FLAT"]:
        cnt = sum(1 for r in at_extreme if r["next_gap_continuation"] == k)
        log(f"  {k}: {cnt}/{len(at_extreme)}")

    # Of GAP_UP/GAP_DOWN cases, did next day continue?
    log("\nQ4 cross — of GAP_UP cases, next-day direction:")
    for k in ["CONTINUATION", "REVERSAL", "FLAT"]:
        cnt = sum(1 for r in gap_up_rows if r["next_gap_continuation"] == k)
        log(f"  {k}: {cnt}/{len(gap_up_rows)}")
    log("\nQ4 cross — of GAP_DOWN cases, next-day direction:")
    for k in ["CONTINUATION", "REVERSAL", "FLAT"]:
        cnt = sum(1 for r in gap_down_rows if r["next_gap_continuation"] == k)
        log(f"  {k}: {cnt}/{len(gap_down_rows)}")

    # Write CSV
    log("\n" + "=" * 70)
    log("WRITING CSV")
    log("=" * 70)
    if enriched:
        with open(OUTPUT_CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(enriched[0].keys()))
            w.writeheader()
            for r in enriched:
                w.writerow(r)
        log(f"  Wrote {len(enriched)} rows to {OUTPUT_CSV}")

    log("\nStage 2 complete.")

if __name__ == "__main__":
    main()
