"""
Experiment 33 — Analyser

Reads experiment_33_candidates.csv and produces per-case narrative of expiry-day
intraday path for each (inside-bar D-1, expiry D) candidate.

For each case, computes:
  - Break magnitude (high break and low break, in points and %)
  - Time of first break (high and low)
  - Whether the break sustained to close, reversed, or whipsawed
  - Peak excursion above inside_high, peak excursion below inside_low
  - Time of day's high and time of day's low
  - Path classification: clean_break_high / clean_break_low / whipsaw_high_then_low /
    whipsaw_low_then_high / pin (no break) / break_then_close_inside

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
CANDIDATES_CSV = os.path.join(WORKING_DIR, "experiment_33_candidates.csv")
OUTPUT_CSV     = os.path.join(WORKING_DIR, "experiment_33_analysis.csv")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ---------------------------------------------------------------------------
# Load instrument_id mapping
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
# Pull intraday 1m bars for one symbol on one date
# ---------------------------------------------------------------------------

def get_intraday_bars(instrument_id, symbol, target_date):
    PAGE_SIZE = 1000
    offset = 0
    bars = []
    while True:
        res = (sb.table("hist_spot_bars_1m")
                 .select("bar_ts, trade_date, open, high, low, close, is_pre_market")
                 .eq("instrument_id", instrument_id)
                 .eq("trade_date", target_date.isoformat())
                 .eq("is_pre_market", False)
                 .order("bar_ts")
                 .range(offset, offset + PAGE_SIZE - 1).execute())
        if not res.data:
            break
        for row in res.data:
            bts = datetime.fromisoformat(row["bar_ts"].replace("Z", "+00:00"))
            if target_date < ERA_BOUNDARY:
                bts_ist = bts.replace(tzinfo=None)
            else:
                bts_ist = bts.astimezone(tz=timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)
            if not (bts_ist.hour > 9 or (bts_ist.hour == 9 and bts_ist.minute >= 15)):
                continue
            if not (bts_ist.hour < 15 or (bts_ist.hour == 15 and bts_ist.minute <= 30)):
                continue
            bars.append({
                "ts_ist": bts_ist,
                "open":   float(row["open"]),
                "high":   float(row["high"]),
                "low":    float(row["low"]),
                "close":  float(row["close"]),
            })
        offset += len(res.data)
        if len(res.data) < PAGE_SIZE:
            break
    bars.sort(key=lambda b: b["ts_ist"])
    return bars

# ---------------------------------------------------------------------------
# Characterise expiry-day intraday journey
# ---------------------------------------------------------------------------

def characterise_intraday(bars, inside_high, inside_low):
    """
    Build a detailed picture of the expiry-day intraday path
    relative to the inside bar's H/L.
    """
    if not bars:
        return None

    open_   = bars[0]["open"]
    close_  = bars[-1]["close"]
    day_h   = max(b["high"] for b in bars)
    day_l   = min(b["low"]  for b in bars)
    inside_range = inside_high - inside_low
    inside_mid   = (inside_high + inside_low) / 2.0

    # Excursion magnitudes
    excursion_above = max(0.0, day_h - inside_high)
    excursion_below = max(0.0, inside_low - day_l)

    # Walk bars to find: first break high, first break low, sustained-or-reversed
    first_break_high = None
    first_break_low  = None
    for b in bars:
        if first_break_high is None and b["high"] > inside_high:
            first_break_high = b["ts_ist"]
        if first_break_low is None and b["low"] < inside_low:
            first_break_low = b["ts_ist"]
        if first_break_high and first_break_low:
            break

    # After the first break, did price return inside? Did it break the other side too?
    # We track the state machine: what happened first, second, etc.
    state_path = []   # list of (time, event) for narrative
    cur_state = "inside"
    for b in bars:
        if b["high"] > inside_high and cur_state != "above":
            state_path.append((b["ts_ist"], "broke_above"))
            cur_state = "above"
        elif b["low"] < inside_low and cur_state != "below":
            state_path.append((b["ts_ist"], "broke_below"))
            cur_state = "below"
        elif (inside_low <= b["low"] and b["high"] <= inside_high) and cur_state != "inside":
            state_path.append((b["ts_ist"], "back_inside"))
            cur_state = "inside"

    # Final close position
    if close_ > inside_high:
        close_position = "above"
    elif close_ < inside_low:
        close_position = "below"
    else:
        close_position = "inside"

    # Path classification
    broke_high = first_break_high is not None
    broke_low  = first_break_low  is not None
    if not broke_high and not broke_low:
        path_class = "PIN_no_break"
    elif broke_high and not broke_low:
        if close_position == "above":
            path_class = "BREAK_HIGH_sustained"
        else:
            path_class = "BREAK_HIGH_failed"
    elif broke_low and not broke_high:
        if close_position == "below":
            path_class = "BREAK_LOW_sustained"
        else:
            path_class = "BREAK_LOW_failed"
    else:
        # Both broke. Order matters.
        if first_break_high < first_break_low:
            if close_position == "below":
                path_class = "WHIPSAW_high_then_low_close_below"
            elif close_position == "above":
                path_class = "WHIPSAW_high_then_low_close_above"
            else:
                path_class = "WHIPSAW_high_then_low_close_inside"
        else:
            if close_position == "above":
                path_class = "WHIPSAW_low_then_high_close_above"
            elif close_position == "below":
                path_class = "WHIPSAW_low_then_high_close_below"
            else:
                path_class = "WHIPSAW_low_then_high_close_inside"

    # Time of day's high and low
    time_day_high = None
    time_day_low  = None
    for b in bars:
        if time_day_high is None and b["high"] == day_h:
            time_day_high = b["ts_ist"]
        if time_day_low is None and b["low"] == day_l:
            time_day_low = b["ts_ist"]

    return {
        "open":              open_,
        "close":             close_,
        "day_high":          day_h,
        "day_low":           day_l,
        "day_range":         day_h - day_l,
        "day_range_pct_inside": (day_h - day_l) / inside_range * 100.0 if inside_range > 0 else None,
        "oc_pct":            (close_ / open_ - 1.0) * 100.0,
        "excursion_above":   excursion_above,
        "excursion_above_pct": excursion_above / inside_high * 100.0 if inside_high > 0 else None,
        "excursion_below":   excursion_below,
        "excursion_below_pct": excursion_below / inside_low * 100.0 if inside_low > 0 else None,
        "first_break_high_time": first_break_high.strftime("%H:%M") if first_break_high else None,
        "first_break_low_time":  first_break_low.strftime("%H:%M")  if first_break_low  else None,
        "time_day_high":         time_day_high.strftime("%H:%M") if time_day_high else None,
        "time_day_low":          time_day_low.strftime("%H:%M")  if time_day_low  else None,
        "close_position":        close_position,
        "path_class":            path_class,
        "state_transitions":     len(state_path),
        "state_path_str":        " > ".join(f"{t.strftime('%H:%M')}:{e}" for t, e in state_path[:6]),
    }

# ---------------------------------------------------------------------------
# Read candidates CSV
# ---------------------------------------------------------------------------

def read_candidates():
    if not os.path.exists(CANDIDATES_CSV):
        raise FileNotFoundError(f"Run experiment_33 first to produce {CANDIDATES_CSV}")
    rows = []
    with open(CANDIDATES_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log("=" * 70)
    log("Experiment 33 — Per-Case Intraday Analysis")
    log("=" * 70)

    instrument_ids = load_instrument_ids()
    candidates = read_candidates()
    log(f"Loaded {len(candidates)} candidates from {CANDIDATES_CSV}")

    enriched = []
    for cand in candidates:
        symbol = cand["symbol"]
        expiry_date = date.fromisoformat(cand["expiry_date"])
        inside_high = float(cand["inside_high"])
        inside_low  = float(cand["inside_low"])

        bars = get_intraday_bars(instrument_ids[symbol], symbol, expiry_date)
        if not bars:
            log(f"  WARNING: no bars for {symbol} {expiry_date} — skipping")
            continue

        char = characterise_intraday(bars, inside_high, inside_low)
        if not char:
            continue

        row = {
            "symbol":       symbol,
            "expiry_type":  cand["expiry_type"],
            "inside_date":  cand["inside_bar_date"],
            "expiry_date":  cand["expiry_date"],
            "inside_high":  round(inside_high, 2),
            "inside_low":   round(inside_low,  2),
            "inside_range": round(inside_high - inside_low, 2),
            "open":         round(char["open"],     2),
            "close":        round(char["close"],    2),
            "day_high":     round(char["day_high"], 2),
            "day_low":      round(char["day_low"],  2),
            "oc_pct":       round(char["oc_pct"],   3),
            "day_range":    round(char["day_range"],   2),
            "day_range_pct_inside": round(char["day_range_pct_inside"], 0) if char["day_range_pct_inside"] else None,
            "excursion_above":      round(char["excursion_above"], 2),
            "excursion_below":      round(char["excursion_below"], 2),
            "excursion_above_pct":  round(char["excursion_above_pct"], 3) if char["excursion_above_pct"] else 0.0,
            "excursion_below_pct":  round(char["excursion_below_pct"], 3) if char["excursion_below_pct"] else 0.0,
            "first_break_high_time": char["first_break_high_time"],
            "first_break_low_time":  char["first_break_low_time"],
            "time_day_high":         char["time_day_high"],
            "time_day_low":          char["time_day_low"],
            "close_position":        char["close_position"],
            "path_class":            char["path_class"],
            "state_transitions":     char["state_transitions"],
            "state_path":            char["state_path_str"],
        }
        enriched.append(row)

    # Per-case narrative output
    log("\n" + "=" * 70)
    log("PER-CASE NARRATIVES")
    log("=" * 70)
    for r in enriched:
        log("")
        log(f"--- {r['symbol']} {r['expiry_type'].upper()} expiry {r['expiry_date']} (inside-bar {r['inside_date']}) ---")
        log(f"  Inside bar: {r['inside_low']:.2f} - {r['inside_high']:.2f}  (range {r['inside_range']:.2f})")
        log(f"  Expiry day: O={r['open']:.2f} H={r['day_high']:.2f} L={r['day_low']:.2f} C={r['close']:.2f}  OC%={r['oc_pct']:+.3f}%")
        log(f"  Range:      {r['day_range']:.2f} pts ({r['day_range_pct_inside']}% of inside)")
        log(f"  Excursion above inside_high: {r['excursion_above']:.2f} pts ({r['excursion_above_pct']:+.3f}%)")
        log(f"  Excursion below inside_low:  {r['excursion_below']:.2f} pts ({r['excursion_below_pct']:+.3f}%)")
        log(f"  First break high: {r['first_break_high_time'] or '-'}, first break low: {r['first_break_low_time'] or '-'}")
        log(f"  Day's high time: {r['time_day_high']}, day's low time: {r['time_day_low']}")
        log(f"  Close position: {r['close_position'].upper()}  |  Path: {r['path_class']}")
        log(f"  State transitions: {r['state_transitions']} | path: {r['state_path']}")

    # Aggregate by symbol/expiry_type
    log("\n" + "=" * 70)
    log("AGGREGATE BY GROUP")
    log("=" * 70)
    groups = defaultdict(list)
    for r in enriched:
        groups[(r["symbol"], r["expiry_type"])].append(r)
    for (sym, et), rows in sorted(groups.items()):
        log(f"\n{sym} {et.upper()} (N={len(rows)})")
        path_counts = defaultdict(int)
        for r in rows:
            path_counts[r["path_class"]] += 1
        for pc, cnt in sorted(path_counts.items(), key=lambda x: -x[1]):
            log(f"  {pc}: {cnt}")

        # Time-of-day stats for first breaks
        early_break    = sum(1 for r in rows if r["first_break_high_time"] and r["first_break_high_time"] < "11:00")
        morning_break  = sum(1 for r in rows if r["first_break_high_time"] and "11:00" <= r["first_break_high_time"] < "13:00")
        afternoon_break = sum(1 for r in rows if r["first_break_high_time"] and r["first_break_high_time"] >= "13:00")
        log(f"  First high break timing: early(<11)={early_break} mid(11-13)={morning_break} late(>=13)={afternoon_break}")

        avg_excursion_above = sum(r["excursion_above"] for r in rows) / len(rows)
        avg_excursion_below = sum(r["excursion_below"] for r in rows) / len(rows)
        log(f"  Mean excursion above inside_high: {avg_excursion_above:.2f} pts")
        log(f"  Mean excursion below inside_low:  {avg_excursion_below:.2f} pts")

    # Write enriched CSV
    log("\n" + "=" * 70)
    log("WRITING ENRICHED CSV")
    log("=" * 70)
    if enriched:
        with open(OUTPUT_CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(enriched[0].keys()))
            w.writeheader()
            for r in enriched:
                w.writerow(r)
        log(f"  Wrote {len(enriched)} rows to {OUTPUT_CSV}")
    log("\nAnalysis complete.")

if __name__ == "__main__":
    main()
