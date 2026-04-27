"""
Experiment 33 — Inside-bar Day Before Expiry

Hypothesis:
  When trading day D-1 forms a strict inside bar (D-1 high < D-2 high AND
  D-1 low > D-2 low) and day D is a NIFTY/SENSEX expiry, day D exhibits
  characteristic behaviour driven by options writers having short the wings
  the prior day. Expected: range contraction, drift to inside-bar mid,
  pin near max-pain, suppressed realised vol.

Setup:
  - NIFTY + SENSEX, separately analysed
  - Both weekly + monthly expiries, classified separately
  - Strict inside-bar definition (full containment, no equality)
  - Expiry days detected from option_chain_snapshots (where DTE=0 was observed)
  - TZ-aware per TD-029 (era-boundary on hist_spot_bars_1m for trade_date < 2026-04-07)

Outputs:
  - experiment_33_candidates.csv — every inside-bar-before-expiry case
  - experiment_33_controls.csv  — control sets (expiry without inside-bar, inside-bar without expiry)
  - Console: aggregate stats per group + control comparisons

Author: Session 10 close, 2026-04-27
"""

import os
import sys
import csv
import calendar
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

START_DATE = date(2025, 4, 1)
END_DATE   = date(2026, 4, 24)   # last full session in our data

SYMBOLS = ["NIFTY", "SENSEX"]
ERA_BOUNDARY = date(2026, 4, 7)  # TD-029: pre-boundary rows have IST stored as UTC

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CANDIDATES_CSV = os.path.join(OUTPUT_DIR, "experiment_33_candidates.csv")
CONTROLS_CSV   = os.path.join(OUTPUT_DIR, "experiment_33_controls.csv")

# ---------------------------------------------------------------------------
# CONNECT
# ---------------------------------------------------------------------------

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ---------------------------------------------------------------------------
# STEP 1 — Discover instrument_id per symbol
# ---------------------------------------------------------------------------

def get_instruments():
    """Returns dict keyed by symbol with id and weekly_expiry_dow."""
    log("Discovering instruments for NIFTY and SENSEX...")
    res = sb.table("instruments").select("id, symbol, weekly_expiry_dow").execute()
    out = {}
    for row in res.data:
        sym = (row.get("symbol") or "").upper()
        if "NIFTY" in sym and "BANK" not in sym and out.get("NIFTY") is None:
            out["NIFTY"] = {"id": row["id"], "weekly_expiry_dow": row["weekly_expiry_dow"]}
        elif "SENSEX" in sym and out.get("SENSEX") is None:
            out["SENSEX"] = {"id": row["id"], "weekly_expiry_dow": row["weekly_expiry_dow"]}
    log(f"  NIFTY: id={out.get('NIFTY', {}).get('id')}, weekly_expiry_dow={out.get('NIFTY', {}).get('weekly_expiry_dow')}")
    log(f"  SENSEX: id={out.get('SENSEX', {}).get('id')}, weekly_expiry_dow={out.get('SENSEX', {}).get('weekly_expiry_dow')}")
    if "NIFTY" not in out or "SENSEX" not in out:
        raise RuntimeError("Could not resolve NIFTY and SENSEX in 'instruments' table.")
    return out

# ---------------------------------------------------------------------------
# STEP 2 — Discover expiry days per symbol from option_chain_snapshots
# ---------------------------------------------------------------------------

# Expiry regime change cutover. Pre-cutover: NIFTY Thu, SENSEX Tue.
# Post-cutover: NIFTY Tue, SENSEX Thu. ISO weekday convention (Mon=1..Sun=7).
EXPIRY_REGIME_CUTOVER = date(2025, 9, 1)

def expiry_iso_dow_for(symbol, d):
    """Return ISO weekday (1=Mon..7=Sun) for the given symbol on the given date."""
    pre_cutover = d < EXPIRY_REGIME_CUTOVER
    if symbol == "NIFTY":
        return 4 if pre_cutover else 2   # Thu pre, Tue post
    elif symbol == "SENSEX":
        return 2 if pre_cutover else 4   # Tue pre, Thu post
    raise ValueError(f"Unknown symbol: {symbol}")

def discover_expiry_days(symbol, weekly_dow_unused, daily_ohlc):
    """
    Returns dict: {expiry_date_obj: 'weekly' | 'monthly'}

    Era-aware calendar rule:
      - Pre-2025-09-01: NIFTY=Thu (ISO 4), SENSEX=Tue (ISO 2)
      - 2025-09-01 onwards: NIFTY=Tue (ISO 2), SENSEX=Thu (ISO 4)
      - Monthly = latest expiry-day-of-week occurrence in calendar month

    Validation:
      - hist_atm_option_bars_5m WHERE dte=0 (sparse but ground-truth where present)
      - option_chain_snapshots ts_date == expiry_date (recent April fill-in)
    """
    log(f"Discovering expiry days for {symbol} (era-aware calendar rule)...")

    # Step 1: candidate dates from era-aware calendar rule, filtered to actual trading days
    candidates = sorted([d for d in daily_ohlc.keys()
                         if d.isoweekday() == expiry_iso_dow_for(symbol, d)])
    log(f"  Calendar-rule candidates (cutover={EXPIRY_REGIME_CUTOVER}): {len(candidates)}")

    # Step 2: classify weekly vs monthly (latest expiry-DOW in each calendar month = monthly)
    by_month = defaultdict(list)
    for d in candidates:
        by_month[(d.year, d.month)].append(d)
    classified = {}
    for (yr, mo), days in by_month.items():
        days.sort()
        for d in days[:-1]:
            classified[d] = "weekly"
        if days:
            classified[days[-1]] = "monthly"

    # Step 3: validate against hist_atm_option_bars_5m dte=0 (sparse ground-truth)
    log(f"  Validating against hist_atm_option_bars_5m (dte=0)...")
    hist_atm_expiries = set()
    page_size = 1000
    offset = 0
    while True:
        res = (sb.table("hist_atm_option_bars_5m")
                 .select("trade_date")
                 .eq("symbol", symbol).eq("dte", 0)
                 .gte("trade_date", START_DATE.isoformat())
                 .lte("trade_date", END_DATE.isoformat())
                 .range(offset, offset + page_size - 1).execute())
        if not res.data:
            break
        for row in res.data:
            td = row["trade_date"]
            if isinstance(td, str): td = date.fromisoformat(td)
            hist_atm_expiries.add(td)
        offset += len(res.data)
        if len(res.data) < page_size:
            break
    in_calendar     = hist_atm_expiries & set(classified.keys())
    not_in_calendar = sorted(hist_atm_expiries - set(classified.keys()))
    log(f"    hist_atm dte=0 confirmed: {len(hist_atm_expiries)}")
    log(f"      matches calendar rule: {len(in_calendar)} of {len(hist_atm_expiries)}")
    if not_in_calendar:
        log(f"      special-case dates (not in calendar): {not_in_calendar}")
        # Add special-case dates as 'weekly' (they're real expiries even if off-cycle)
        for d in not_in_calendar:
            if d not in classified:
                classified[d] = "weekly"

    # Step 4: option_chain_snapshots fill-in for the recent April window
    log(f"  Fill-in from option_chain_snapshots (recent window)...")
    snap_expiries = set()
    offset = 0
    while True:
        res = (sb.table("option_chain_snapshots")
                 .select("ts, expiry_date, symbol")
                 .eq("symbol", symbol)
                 .gte("ts", START_DATE.isoformat())
                 .lte("ts", (END_DATE + timedelta(days=1)).isoformat())
                 .range(offset, offset + page_size - 1).execute())
        if not res.data:
            break
        for row in res.data:
            ts = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
            ts_ist = ts.astimezone(tz=timezone(timedelta(hours=5, minutes=30)))
            ts_date = ts_ist.date()
            exp_date = row["expiry_date"]
            if isinstance(exp_date, str): exp_date = date.fromisoformat(exp_date)
            if ts_date == exp_date:
                snap_expiries.add(exp_date)
        offset += len(res.data)
        if len(res.data) < page_size:
            break
    new_from_snap = snap_expiries - set(classified.keys())
    if new_from_snap:
        log(f"    new from option_chain not in calendar: {sorted(new_from_snap)}")
        for d in new_from_snap:
            classified[d] = "weekly"

    # Step 5: re-run monthly classification across the full set (in case special-cases shifted it)
    by_month = defaultdict(list)
    for d in classified.keys():
        by_month[(d.year, d.month)].append(d)
    final = {}
    for (yr, mo), days in by_month.items():
        days.sort()
        for d in days[:-1]:
            final[d] = "weekly"
        if days:
            final[days[-1]] = "monthly"

    monthly_count = sum(1 for v in final.values() if v == "monthly")
    weekly_count  = sum(1 for v in final.values() if v == "weekly")
    log(f"  Final: {weekly_count} weekly, {monthly_count} monthly (total {weekly_count+monthly_count})")

    sorted_classified = sorted(final.items())
    if len(sorted_classified) >= 6:
        log(f"    First 3: {[(d.isoformat(), t) for d, t in sorted_classified[:3]]}")
        log(f"    Last 3:  {[(d.isoformat(), t) for d, t in sorted_classified[-3:]]}")

    return final

# ---------------------------------------------------------------------------
# STEP 3 — Build daily OHLC from hist_spot_bars_1m, TZ-aware per TD-029
# ---------------------------------------------------------------------------

def build_daily_ohlc(instrument_id, symbol):
    """
    Returns dict: {trade_date_obj: {open, high, low, close}}
    TZ-aware: pre-2026-04-07 rows are IST-stored-as-UTC, post are correct UTC.
    """
    log(f"Building daily OHLC for {symbol}...")

    # Pull all 1m bars in window with TZ-aware bar_ts handling.
    # Supabase REST default cap is 1000 rows per request — paginate accordingly.
    PAGE_SIZE = 1000
    offset = 0
    bars_by_date = defaultdict(list)
    pages_read = 0
    while True:
        res = (sb.table("hist_spot_bars_1m")
                 .select("bar_ts, trade_date, open, high, low, close, is_pre_market")
                 .eq("instrument_id", instrument_id)
                 .eq("is_pre_market", False)
                 .gte("trade_date", START_DATE.isoformat())
                 .lte("trade_date", END_DATE.isoformat())
                 .order("bar_ts")
                 .range(offset, offset + PAGE_SIZE - 1)
                 .execute())
        if not res.data:
            break
        for row in res.data:
            td = date.fromisoformat(row["trade_date"]) if isinstance(row["trade_date"], str) else row["trade_date"]
            bts_str = row["bar_ts"]
            bts = datetime.fromisoformat(bts_str.replace("Z", "+00:00"))
            # TD-029 era-boundary fix: pre-2026-04-07 has IST stored under UTC tzinfo
            if td < ERA_BOUNDARY:
                bts_ist = bts.replace(tzinfo=None)
            else:
                bts_ist = bts.astimezone(tz=timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)
            # Filter to regular session (09:15 - 15:30 IST)
            if not (bts_ist.hour > 9 or (bts_ist.hour == 9 and bts_ist.minute >= 15)):
                continue
            if not (bts_ist.hour < 15 or (bts_ist.hour == 15 and bts_ist.minute <= 30)):
                continue
            bars_by_date[td].append({
                "ts_ist": bts_ist,
                "open":   float(row["open"]),
                "high":   float(row["high"]),
                "low":    float(row["low"]),
                "close":  float(row["close"]),
            })
        rows_returned = len(res.data)
        offset += rows_returned
        pages_read += 1
        if pages_read % 50 == 0:
            log(f"    {pages_read} pages, {offset} rows so far...")
        if rows_returned < PAGE_SIZE:
            break

    log(f"  Read {offset} 1m bars over {pages_read} pages")

    # Aggregate to daily OHLC
    daily = {}
    for td, bars in bars_by_date.items():
        if not bars:
            continue
        bars.sort(key=lambda b: b["ts_ist"])
        daily[td] = {
            "open":  bars[0]["open"],
            "high":  max(b["high"] for b in bars),
            "low":   min(b["low"]  for b in bars),
            "close": bars[-1]["close"],
            "n_bars": len(bars),
        }
    log(f"  Built {len(daily)} daily OHLC rows for {symbol}")
    return daily, bars_by_date

# ---------------------------------------------------------------------------
# STEP 4 — Identify inside-bar days (strict)
# ---------------------------------------------------------------------------

def find_inside_bars(daily_ohlc):
    """
    Returns dict: {date_d_minus_1: {prior_day, this_day_data}} for strict inside bars.
    Strict: today.high < yday.high AND today.low > yday.low.
    """
    sorted_dates = sorted(daily_ohlc.keys())
    inside_bars = {}
    for i in range(1, len(sorted_dates)):
        td = sorted_dates[i]
        td_prev = sorted_dates[i - 1]
        d  = daily_ohlc[td]
        dp = daily_ohlc[td_prev]
        if d["high"] < dp["high"] and d["low"] > dp["low"]:
            inside_bars[td] = {
                "prior_date":  td_prev,
                "prior_high":  dp["high"],
                "prior_low":   dp["low"],
                "inside_high": d["high"],
                "inside_low":  d["low"],
                "inside_open": d["open"],
                "inside_close": d["close"],
            }
    return inside_bars

# ---------------------------------------------------------------------------
# STEP 5 — Classify inside-bar Mondays as: followed by expiry, not followed by expiry
# ---------------------------------------------------------------------------

def next_trading_day(d, daily_ohlc):
    """Return the next date in daily_ohlc after d, or None."""
    sorted_dates = sorted(daily_ohlc.keys())
    for sd in sorted_dates:
        if sd > d:
            return sd
    return None

def characterise_expiry_day(expiry_date, expiry_type, inside_high, inside_low, daily_ohlc, bars_by_date):
    """
    Build the characterisation row for an expiry day given inside-bar boundaries.
    """
    if expiry_date not in daily_ohlc:
        return None
    e = daily_ohlc[expiry_date]
    inside_mid   = (inside_high + inside_low) / 2.0
    inside_range = inside_high - inside_low

    # Where did spot close vs inside bar?
    if e["close"] > inside_high:
        close_position = "above_inside_high"
    elif e["close"] < inside_low:
        close_position = "below_inside_low"
    else:
        close_position = "inside_bar"

    # Did spot break inside high or inside low intraday?
    bars = bars_by_date.get(expiry_date, [])
    bars_sorted = sorted(bars, key=lambda b: b["ts_ist"])
    broke_high = any(b["high"] > inside_high for b in bars_sorted)
    broke_low  = any(b["low"]  < inside_low  for b in bars_sorted)

    time_high_break = None
    time_low_break  = None
    for b in bars_sorted:
        if time_high_break is None and b["high"] > inside_high:
            time_high_break = b["ts_ist"].strftime("%H:%M")
        if time_low_break is None and b["low"] < inside_low:
            time_low_break = b["ts_ist"].strftime("%H:%M")

    # Time of day's high and day's low
    time_of_day_high = None
    time_of_day_low  = None
    if bars_sorted:
        max_h = max(b["high"] for b in bars_sorted)
        min_l = min(b["low"]  for b in bars_sorted)
        for b in bars_sorted:
            if time_of_day_high is None and b["high"] == max_h:
                time_of_day_high = b["ts_ist"].strftime("%H:%M")
            if time_of_day_low is None and b["low"] == min_l:
                time_of_day_low = b["ts_ist"].strftime("%H:%M")

    return {
        "expiry_type": expiry_type,
        "expiry_open":   e["open"],
        "expiry_high":   e["high"],
        "expiry_low":    e["low"],
        "expiry_close":  e["close"],
        "expiry_oc_pct": (e["close"] / e["open"] - 1.0) * 100.0,
        "expiry_range":  e["high"] - e["low"],
        "expiry_range_pct_of_inside": ((e["high"] - e["low"]) / inside_range * 100.0) if inside_range > 0 else None,
        "inside_mid":    inside_mid,
        "close_vs_mid_pct": (e["close"] / inside_mid - 1.0) * 100.0,
        "close_position": close_position,
        "broke_inside_high": broke_high,
        "broke_inside_low":  broke_low,
        "broke_both":        broke_high and broke_low,
        "broke_neither":     (not broke_high) and (not broke_low),
        "time_first_break_high": time_high_break,
        "time_first_break_low":  time_low_break,
        "time_of_day_high": time_of_day_high,
        "time_of_day_low":  time_of_day_low,
    }

# ---------------------------------------------------------------------------
# STEP 6 — Run the experiment for one symbol
# ---------------------------------------------------------------------------

def run_for_symbol(symbol, instrument_meta):
    log(f"\n{'='*60}\nRunning Experiment 33 for {symbol}\n{'='*60}")

    instrument_id = instrument_meta["id"]
    weekly_dow    = instrument_meta["weekly_expiry_dow"]

    # Build daily OHLC first (we need the trading-day list for expiry classification)
    daily_ohlc, bars_by_date = build_daily_ohlc(instrument_id, symbol)
    expiry_days = discover_expiry_days(symbol, weekly_dow, daily_ohlc)
    inside_bars = find_inside_bars(daily_ohlc)
    log(f"  Found {len(inside_bars)} strict inside-bar days for {symbol}")

    candidates = []   # inside-bar D-1 + expiry D
    control_a  = []   # expiry days without inside-bar D-1
    control_b  = []   # inside-bar days without expiry D+1

    for ib_date, ib in inside_bars.items():
        next_td = next_trading_day(ib_date, daily_ohlc)
        if next_td is None:
            continue
        if next_td in expiry_days:
            ch = characterise_expiry_day(
                next_td, expiry_days[next_td],
                ib["inside_high"], ib["inside_low"],
                daily_ohlc, bars_by_date,
            )
            if ch:
                candidates.append({
                    "symbol": symbol,
                    "inside_bar_date": ib_date.isoformat(),
                    "prior_date":      ib["prior_date"].isoformat(),
                    "expiry_date":     next_td.isoformat(),
                    "prior_high":      ib["prior_high"],
                    "prior_low":       ib["prior_low"],
                    "inside_high":     ib["inside_high"],
                    "inside_low":      ib["inside_low"],
                    "inside_range":    ib["inside_high"] - ib["inside_low"],
                    "inside_range_pct": (ib["inside_high"] - ib["inside_low"]) / ((ib["inside_high"] + ib["inside_low"]) / 2.0) * 100.0,
                    **ch,
                })
        else:
            control_b.append({
                "symbol": symbol,
                "inside_bar_date": ib_date.isoformat(),
                "next_td":         next_td.isoformat(),
                "next_td_is_expiry": False,
                "inside_high":     ib["inside_high"],
                "inside_low":      ib["inside_low"],
            })

    # Control A: expiry days where D-1 was NOT an inside bar
    for exp_date, exp_type in expiry_days.items():
        if exp_date not in daily_ohlc:
            continue
        sorted_dates = sorted(daily_ohlc.keys())
        idx = sorted_dates.index(exp_date) if exp_date in sorted_dates else -1
        if idx <= 0:
            continue
        prior_td = sorted_dates[idx - 1]
        if prior_td in inside_bars:
            continue   # already counted as candidate
        # Use prior_td as the "would-be inside bar" for measurement, but flag as not-inside
        prior = daily_ohlc[prior_td]
        ch = characterise_expiry_day(
            exp_date, exp_type,
            prior["high"], prior["low"],
            daily_ohlc, bars_by_date,
        )
        if ch:
            control_a.append({
                "symbol": symbol,
                "expiry_date": exp_date.isoformat(),
                "expiry_type": exp_type,
                "prior_date":  prior_td.isoformat(),
                "prior_high":  prior["high"],
                "prior_low":   prior["low"],
                **ch,
            })

    return candidates, control_a, control_b

# ---------------------------------------------------------------------------
# STEP 7 — Aggregate stats helpers
# ---------------------------------------------------------------------------

def stats_for_group(rows, group_label):
    if not rows:
        log(f"  {group_label}: N=0 — no cases")
        return
    n = len(rows)
    mean_oc       = sum(r["expiry_oc_pct"]            for r in rows) / n
    mean_range_pc = sum(r["expiry_range_pct_of_inside"] for r in rows if r["expiry_range_pct_of_inside"] is not None)
    n_with_range  = sum(1 for r in rows if r["expiry_range_pct_of_inside"] is not None)
    if n_with_range > 0:
        mean_range_pc /= n_with_range
    closed_inside = sum(1 for r in rows if r["close_position"] == "inside_bar")
    closed_above  = sum(1 for r in rows if r["close_position"] == "above_inside_high")
    closed_below  = sum(1 for r in rows if r["close_position"] == "below_inside_low")
    broke_both    = sum(1 for r in rows if r["broke_both"])
    broke_neither = sum(1 for r in rows if r["broke_neither"])
    broke_high_only = sum(1 for r in rows if r["broke_inside_high"] and not r["broke_inside_low"])
    broke_low_only  = sum(1 for r in rows if r["broke_inside_low"]  and not r["broke_inside_high"])

    log(f"  {group_label}: N={n}")
    log(f"    Mean expiry-day open-to-close move: {mean_oc:+.3f}%")
    if n_with_range > 0:
        log(f"    Mean expiry-day range as % of inside-bar range: {mean_range_pc:.0f}% (n={n_with_range})")
    log(f"    Close position: inside_bar={closed_inside}, above={closed_above}, below={closed_below}")
    log(f"    Break: neither={broke_neither} (pin), both={broke_both} (whipsaw), high_only={broke_high_only}, low_only={broke_low_only}")

# ---------------------------------------------------------------------------
# STEP 8 — Write CSVs
# ---------------------------------------------------------------------------

def write_csv(path, rows):
    if not rows:
        log(f"  No rows for {path}")
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    log(f"  Wrote {len(rows)} rows to {path}")

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    log("=" * 60)
    log("Experiment 33 — Inside-bar Day Before Expiry")
    log("=" * 60)
    log(f"Window: {START_DATE} to {END_DATE}")
    log(f"Symbols: {SYMBOLS}")
    log(f"Inside-bar definition: STRICT (high < yday_high AND low > yday_low)")
    log("")

    instruments_meta = get_instruments()

    all_candidates = []
    all_control_a  = []
    all_control_b  = []
    for symbol in SYMBOLS:
        cands, ctrl_a, ctrl_b = run_for_symbol(symbol, instruments_meta[symbol])
        all_candidates.extend(cands)
        all_control_a.extend(ctrl_a)
        all_control_b.extend(ctrl_b)

    # Aggregate stats
    log("\n" + "=" * 60)
    log("AGGREGATE RESULTS")
    log("=" * 60)
    for symbol in SYMBOLS:
        log(f"\n--- {symbol} ---")
        for exp_type in ["weekly", "monthly"]:
            rows = [c for c in all_candidates if c["symbol"] == symbol and c["expiry_type"] == exp_type]
            stats_for_group(rows, f"{symbol} INSIDE-BAR + {exp_type.upper()} EXPIRY (test group)")
            ctrl_rows = [c for c in all_control_a if c["symbol"] == symbol and c["expiry_type"] == exp_type]
            stats_for_group(ctrl_rows, f"{symbol} NO-INSIDE-BAR + {exp_type.upper()} EXPIRY (control A)")
        log("")

    # Write CSVs
    log("\n" + "=" * 60)
    log("WRITING CSVS")
    log("=" * 60)
    write_csv(CANDIDATES_CSV, all_candidates)
    # Write controls separately — they have different schemas (A is expiry-day characterised, B is just inside-bar marker)
    CONTROL_A_CSV = CONTROLS_CSV.replace(".csv", "_A_expiry_no_inside.csv")
    CONTROL_B_CSV = CONTROLS_CSV.replace(".csv", "_B_inside_no_expiry.csv")
    write_csv(CONTROL_A_CSV, all_control_a)
    write_csv(CONTROL_B_CSV, all_control_b)

    log("\nExperiment 33 complete.")
    log(f"Inspect {CANDIDATES_CSV} for case-by-case detail.")

if __name__ == "__main__":
    main()
