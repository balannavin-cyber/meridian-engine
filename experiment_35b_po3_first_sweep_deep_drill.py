#!/usr/bin/env python3
"""
experiment_35b_po3_first_sweep_deep_drill.py
MERDIAN Experiment 35B — PO3 First Sweep: Deep Drill

Origin:
    Exp 35 PARTIAL PASS showed:
      PDH first-sweep + gap-up OPEN → 74.3% bearish EOD WR (N=35)
      PDL first-sweep + gap-down OPEN → 67.6% bullish EOD WR (N=37)

    Three unanswered questions this experiment addresses:

    Q1 — Return trajectory:
         Does the edge manifest immediately after the sweep or does it
         take time? Measure T+30m, T+60m, T+120m, T+180m, EOD.
         If edge is front-loaded (T+30m already strong), entry timing
         is right after rejection confirmation.
         If edge is back-loaded (T+60m+ stronger), earlier entries
         are premature and the session plays out slowly.

    Q2 — Reversal speed as filter:
         Fast rejection (T+1/T+2 bars = 5–10 min) = sharp institutional
         defence of the level. Slow rejection (T+5/T+6 bars = 25–30 min)
         = grinding, less decisive. Does speed predict continuation WR?

    Q3 — Failure mode analysis:
         What characterises the sessions where PO3 predicted direction
         but EOD moved the wrong way?
         Sub-classify losing sessions by: gamma regime at open,
         gap size, sweep depth, DTE (expiry proximity).
         Goal: find a filter that removes the 25–33% losses.

Scope (replicating Exp 35 best config):
    - OPEN window only (09:15–10:00 IST)
    - Gap context required (gap-up for PDH / gap-down for PDL)
    - Both NIFTY and SENSEX
    - Sweep: wick >= PDH/PDL * (1 ± 0.0005), reversal within 6 bars

Additional data joined per event:
    - gamma_regime at session open (from market_spot_session_markers
      or hist_pattern_signals — whichever is available)
    - Gap size in points and percent
    - DTE (0/1/2/3+) — expiry proximity effect

TD-029 workaround: bar_ts stored as IST labeled +00:00.
Pagination: 1000 rows/request hard cap.

Run from: C:\\GammaEnginePython
Usage  : python experiment_35b_po3_first_sweep_deep_drill.py

Session: 11  (2026-04-28)
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta

from dotenv import load_dotenv
from supabase import create_client

# ── Environment ───────────────────────────────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# ── Parameters (replicate Exp 35 best config) ─────────────────────────────────
SWEEP_THRESHOLD    = 0.0005
REVERSAL_THRESHOLD = 0.001
REVERSAL_MAX_BARS  = 6
OPEN_END           = (10, 0)     # 09:15–10:00 IST only

# Trajectory horizons (in 5m bars from rejection bar)
HORIZONS = {
    "T+30m":  6,
    "T+60m":  12,
    "T+120m": 24,
    "T+180m": 36,
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_ts(ts_str: str) -> datetime:
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


def bar_minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def pct(v: float) -> str:
    return f"{v:.1%}"


def mean(lst):
    return sum(lst) / len(lst) if lst else None


def median(lst):
    if not lst:
        return None
    s = sorted(lst)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n//2 - 1] + s[n//2]) / 2


# ── Data fetchers ─────────────────────────────────────────────────────────────
def fetch_bars_by_date(instrument_id: str, label: str) -> dict:
    print(f"  [{label}] Fetching 5m bars...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp = (
            supabase.table("hist_spot_bars_5m")
            .select("bar_ts,open,high,low,close")
            .eq("instrument_id", instrument_id)
            .order("bar_ts")
            .range(page, page + 999)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        page += 1000

    by_date = defaultdict(list)
    for bar in rows:
        dt = parse_ts(bar["bar_ts"])
        t  = bar_minutes(dt)
        if 9*60+15 <= t <= 15*60+30:
            bar["_dt"]   = dt
            bar["_date"] = dt.date().isoformat()
            by_date[bar["_date"]].append(bar)

    for d in by_date:
        by_date[d].sort(key=lambda b: b["_dt"])

    total = sum(len(v) for v in by_date.values())
    print(f" {total} bars / {len(by_date)} sessions")
    return dict(by_date)


def fetch_zones(symbol: str) -> dict:
    print(f"  [{symbol}] Fetching D PDH/PDL zones...", end="", flush=True)
    resp = (
        supabase.table("hist_ict_htf_zones")
        .select("as_of_date,pattern_type,zone_high,zone_low")
        .eq("symbol", symbol)
        .eq("timeframe", "D")
        .in_("pattern_type", ["PDH", "PDL"])
        .execute()
    )
    zones = defaultdict(dict)
    for row in (resp.data or []):
        d  = row["as_of_date"][:10]
        pt = row["pattern_type"]
        if pt == "PDH":
            zones[d]["PDH"] = float(row["zone_high"])
        else:
            val = row.get("zone_low") or row.get("zone_high")
            zones[d]["PDL"] = float(val)
    print(f" {len(zones)} dates")
    return dict(zones)


def fetch_session_markers(symbol: str) -> dict:
    """
    Returns {date_str: {gamma_regime, dte, ...}} from market_spot_session_markers.
    Falls back to empty dict if table unavailable or columns differ.
    """
    print(f"  [{symbol}] Fetching session markers...", end="", flush=True)
    try:
        resp = (
            supabase.table("market_spot_session_markers")
            .select("trade_date,gamma_regime,dte")
            .eq("symbol", symbol)
            .execute()
        )
        result = {}
        for row in (resp.data or []):
            d = row["trade_date"][:10]
            result[d] = {
                "gamma_regime": row.get("gamma_regime"),
                "dte":          row.get("dte"),
            }
        print(f" {len(result)} sessions")
        return result
    except Exception as e:
        print(f" unavailable ({e}) — skipping context enrichment")
        return {}


# ── Core detection (Exp 35 best config) ──────────────────────────────────────
def detect_events(symbol: str, bars_by_date: dict, zones: dict,
                  session_markers: dict) -> list:
    """
    Detects first PDH/PDL sweep events with full return trajectory.
    Returns list of event dicts with:
      - Basic: symbol, date, type, direction
      - Sweep: sweep_pct, bars_to_rev, sweep_bar_t
      - Context: gap_pct, gap_pts, gamma_regime, dte
      - Returns: ret_30m, ret_60m, ret_120m, ret_180m, ret_eod
      - Wins: win at each horizon (in reversal direction)
      - Failure flags (populated for losing trades)
    """
    cutoff = OPEN_END[0] * 60 + OPEN_END[1]
    events = []

    sorted_dates = sorted(bars_by_date.keys())

    # Build prior-day close map for gap calculation
    prior_close = {}
    for i, d in enumerate(sorted_dates):
        if i > 0:
            prev_bars = bars_by_date.get(sorted_dates[i-1], [])
            if prev_bars:
                prior_close[d] = float(prev_bars[-1]["close"])

    for session_date in sorted_dates:
        if session_date not in zones:
            continue

        day_bars     = bars_by_date[session_date]
        n            = len(day_bars)
        if n < 8:
            continue

        z            = zones[session_date]
        pdh          = z.get("PDH")
        pdl          = z.get("PDL")
        session_open = float(day_bars[0]["open"])
        session_eod  = float(day_bars[-1]["close"])
        session_ret  = (session_eod - session_open) / session_open

        # Gap calculation
        prev_cls      = prior_close.get(session_date)
        gap_pct       = (session_open - prev_cls) / prev_cls if prev_cls else None
        gap_pts       = (session_open - prev_cls) if prev_cls else None

        # Context from session markers
        ctx           = session_markers.get(session_date, {})
        gamma_regime  = ctx.get("gamma_regime")
        dte           = ctx.get("dte")

        pdh_found = False
        pdl_found = False

        for i, bar in enumerate(day_bars):
            t = bar_minutes(bar["_dt"])
            if t >= cutoff:
                break

            high = float(bar["high"])
            low  = float(bar["low"])

            # ── PDH first sweep ───────────────────────────────────────────────
            if not pdh_found and pdh and high >= pdh * (1 + SWEEP_THRESHOLD):
                for j in range(i + 1, min(i + REVERSAL_MAX_BARS + 1, n)):
                    if float(day_bars[j]["close"]) <= pdh * (1 - REVERSAL_THRESHOLD):
                        gap_up    = session_open >= pdh * 0.999
                        if not gap_up:
                            pdh_found = True
                            break  # no gap context — skip per Exp 35 config

                        rev_close  = float(day_bars[j]["close"])
                        bars_to_rev = j - i
                        sweep_pct  = (high - pdh) / pdh * 100

                        # Return trajectory from rejection bar close
                        rets = {}
                        for horizon, offset in HORIZONS.items():
                            idx = j + offset
                            if idx < n:
                                rets[horizon] = (float(day_bars[idx]["close"]) - rev_close) / rev_close
                            else:
                                rets[horizon] = None

                        # EOD return
                        eod_ret  = session_ret
                        eod_win  = eod_ret < 0

                        events.append({
                            "symbol":       symbol,
                            "date":         session_date,
                            "type":         "PDH",
                            "direction":    "BEARISH",
                            "sweep_pct":    sweep_pct,
                            "bars_to_rev":  bars_to_rev,
                            "gap_pct":      gap_pct,
                            "gap_pts":      gap_pts,
                            "gamma_regime": gamma_regime,
                            "dte":          dte,
                            "ret_30m":      rets.get("T+30m"),
                            "ret_60m":      rets.get("T+60m"),
                            "ret_120m":     rets.get("T+120m"),
                            "ret_180m":     rets.get("T+180m"),
                            "ret_eod":      eod_ret,
                            # Win = bearish continuation
                            "win_30m":      rets.get("T+30m") is not None and rets["T+30m"] < -0.001,
                            "win_60m":      rets.get("T+60m") is not None and rets["T+60m"] < -0.002,
                            "win_120m":     rets.get("T+120m") is not None and rets["T+120m"] < -0.003,
                            "win_180m":     rets.get("T+180m") is not None and rets["T+180m"] < -0.003,
                            "win_eod":      eod_win,
                        })
                        pdh_found = True
                        break

            # ── PDL first sweep ───────────────────────────────────────────────
            if not pdl_found and pdl and low <= pdl * (1 - SWEEP_THRESHOLD):
                for j in range(i + 1, min(i + REVERSAL_MAX_BARS + 1, n)):
                    if float(day_bars[j]["close"]) >= pdl * (1 + REVERSAL_THRESHOLD):
                        gap_down  = session_open <= pdl * 1.001
                        if not gap_down:
                            pdl_found = True
                            break

                        rev_close   = float(day_bars[j]["close"])
                        bars_to_rev = j - i
                        sweep_pct   = (pdl - low) / pdl * 100

                        rets = {}
                        for horizon, offset in HORIZONS.items():
                            idx = j + offset
                            if idx < n:
                                rets[horizon] = (float(day_bars[idx]["close"]) - rev_close) / rev_close
                            else:
                                rets[horizon] = None

                        eod_ret = session_ret
                        eod_win = eod_ret > 0

                        events.append({
                            "symbol":       symbol,
                            "date":         session_date,
                            "type":         "PDL",
                            "direction":    "BULLISH",
                            "sweep_pct":    sweep_pct,
                            "bars_to_rev":  bars_to_rev,
                            "gap_pct":      gap_pct,
                            "gap_pts":      gap_pts,
                            "gamma_regime": gamma_regime,
                            "dte":          dte,
                            "ret_30m":      rets.get("T+30m"),
                            "ret_60m":      rets.get("T+60m"),
                            "ret_120m":     rets.get("T+120m"),
                            "ret_180m":     rets.get("T+180m"),
                            "ret_eod":      eod_ret,
                            # Win = bullish continuation
                            "win_30m":      rets.get("T+30m") is not None and rets["T+30m"] > 0.001,
                            "win_60m":      rets.get("T+60m") is not None and rets["T+60m"] > 0.002,
                            "win_120m":     rets.get("T+120m") is not None and rets["T+120m"] > 0.003,
                            "win_180m":     rets.get("T+180m") is not None and rets["T+180m"] > 0.003,
                            "win_eod":      eod_win,
                        })
                        pdl_found = True
                        break

            if pdh_found and pdl_found:
                break

    return events


# ── Reporting ─────────────────────────────────────────────────────────────────
def section(label: str):
    print(f"\n{'─' * 65}")
    print(f"  {label}")
    print(f"{'─' * 65}")


def wr_line(events, win_key, label, n_min=5):
    valid = [e for e in events if e.get(win_key) is not None]
    n = len(valid)
    if n < n_min:
        print(f"  {label:<50}  N={n:>3}  (insufficient)")
        return None
    wr  = sum(1 for e in valid if e[win_key]) / n
    ret_key = win_key.replace("win_", "ret_")
    rets = [e[ret_key] for e in valid if e.get(ret_key) is not None]
    avg  = mean(rets)
    med  = median(rets)
    avg_str = f"{avg:.3%}" if avg is not None else "n/a"
    med_str = f"{med:.3%}" if med is not None else "n/a"
    print(f"  {label:<50}  N={n:>3}  WR={pct(wr)}  mean={avg_str}  median={med_str}")
    return wr


def trajectory_table(events, label):
    """Print full return trajectory for a group of events."""
    print(f"\n  [{label}] Return trajectory:")
    print(f"  {'Horizon':<10}  {'N':>4}  {'WR':>7}  {'Mean ret':>10}  {'Median ret':>11}  {'Mean|win':>10}  {'Mean|lose':>11}")
    print(f"  {'-'*10}  {'-'*4}  {'-'*7}  {'-'*10}  {'-'*11}  {'-'*10}  {'-'*11}")

    for horizon, win_key in [
        ("T+30m",  "win_30m"),
        ("T+60m",  "win_60m"),
        ("T+120m", "win_120m"),
        ("T+180m", "win_180m"),
        ("EOD",    "win_eod"),
    ]:
        ret_key = win_key.replace("win_", "ret_")
        valid   = [e for e in events if e.get(win_key) is not None]
        n       = len(valid)
        if n == 0:
            print(f"  {horizon:<10}  {0:>4}  {'n/a':>7}")
            continue

        wr   = sum(1 for e in valid if e[win_key]) / n
        rets = [e[ret_key] for e in valid if e.get(ret_key) is not None]
        avg  = mean(rets)
        med  = median(rets)

        wins  = [e[ret_key] for e in valid if e[win_key] and e.get(ret_key) is not None]
        loses = [e[ret_key] for e in valid if not e[win_key] and e.get(ret_key) is not None]

        avg_str  = f"{avg:.3%}"  if avg  is not None else "n/a"
        med_str  = f"{med:.3%}"  if med  is not None else "n/a"
        w_str    = f"{mean(wins):.3%}"  if wins  else "n/a"
        l_str    = f"{mean(loses):.3%}" if loses else "n/a"

        print(f"  {horizon:<10}  {n:>4}  {pct(wr):>7}  {avg_str:>10}  {med_str:>11}  {w_str:>10}  {l_str:>11}")


def print_results(all_events):
    pdh = [e for e in all_events if e["type"] == "PDH"]
    pdl = [e for e in all_events if e["type"] == "PDL"]

    # ── Q1: Return trajectory ─────────────────────────────────────────────────
    section("Q1 — RETURN TRAJECTORY (from rejection bar close)")
    trajectory_table(pdh, "PDH sweeps → bearish")
    trajectory_table(pdl, "PDL sweeps → bullish")

    # ── Q2: Reversal speed ────────────────────────────────────────────────────
    section("Q2 — REVERSAL SPEED as filter (EOD WR by bars-to-reversal)")
    print()
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        print(f"  {label}:")
        for speed in range(1, REVERSAL_MAX_BARS + 1):
            sub = [e for e in ev_list if e["bars_to_rev"] == speed]
            wr_line(sub, "win_eod", f"  {label} T+{speed} bar ({speed*5}min reversal)", n_min=3)

    # Fast (T+1/T+2) vs slow (T+5/T+6)
    section("Q2 — FAST vs SLOW REJECTION (EOD + trajectory)")
    pdh_fast = [e for e in pdh if e["bars_to_rev"] <= 2]
    pdh_slow = [e for e in pdh if e["bars_to_rev"] >= 5]
    pdl_fast = [e for e in pdl if e["bars_to_rev"] <= 2]
    pdl_slow = [e for e in pdl if e["bars_to_rev"] >= 5]

    trajectory_table(pdh_fast, "PDH FAST rejection (≤10 min)")
    trajectory_table(pdh_slow, "PDH SLOW rejection (≥25 min)")
    trajectory_table(pdl_fast, "PDL FAST rejection (≤10 min)")
    trajectory_table(pdl_slow, "PDL SLOW rejection (≥25 min)")

    # ── Q3: Failure mode analysis ─────────────────────────────────────────────
    section("Q3 — FAILURE MODE ANALYSIS (EOD losers)")
    pdh_wins  = [e for e in pdh if e["win_eod"]]
    pdh_loses = [e for e in pdh if not e["win_eod"]]
    pdl_wins  = [e for e in pdl if e["win_eod"]]
    pdl_loses = [e for e in pdl if not e["win_eod"]]

    def compare_attr(wins, loses, key, label):
        w_vals = [e[key] for e in wins  if e.get(key) is not None]
        l_vals = [e[key] for e in loses if e.get(key) is not None]
        if not w_vals or not l_vals:
            return
        w_avg = mean(w_vals)
        l_avg = mean(l_vals)
        print(f"  {label:<35}  wins={w_avg:.4f}  loses={l_avg:.4f}  diff={l_avg-w_avg:+.4f}")

    print(f"\n  PDH (N wins={len(pdh_wins)}, N loses={len(pdh_loses)}):")
    compare_attr(pdh_wins, pdh_loses, "gap_pct",    "Gap size (%)")
    compare_attr(pdh_wins, pdh_loses, "sweep_pct",  "Sweep depth (%)")
    compare_attr(pdh_wins, pdh_loses, "bars_to_rev","Bars to reversal")

    print(f"\n  PDL (N wins={len(pdl_wins)}, N loses={len(pdl_loses)}):")
    compare_attr(pdl_wins, pdl_loses, "gap_pct",    "Gap size (%)")
    compare_attr(pdl_wins, pdl_loses, "sweep_pct",  "Sweep depth (%)")
    compare_attr(pdl_wins, pdl_loses, "bars_to_rev","Bars to reversal")

    # Gamma regime breakdown
    section("Q3 — FAILURE BY GAMMA REGIME")
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        print(f"\n  {label}:")
        regimes = set(e["gamma_regime"] for e in ev_list if e.get("gamma_regime"))
        if not regimes:
            print("  (no gamma_regime data — market_spot_session_markers unavailable)")
            continue
        for regime in sorted(regimes):
            sub = [e for e in ev_list if e.get("gamma_regime") == regime]
            wr_line(sub, "win_eod", f"  {label} {regime}", n_min=3)

    # DTE breakdown
    section("Q3 — FAILURE BY DTE (expiry proximity)")
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        print(f"\n  {label}:")
        dtes = sorted(set(e["dte"] for e in ev_list if e.get("dte") is not None))
        if not dtes:
            print("  (no DTE data — market_spot_session_markers unavailable)")
            continue
        for dte in dtes:
            sub = [e for e in ev_list if e.get("dte") == dte]
            wr_line(sub, "win_eod", f"  {label} DTE={dte}", n_min=3)

    # Sweep depth × EOD WR
    section("Q3 — SWEEP DEPTH × EOD WR")
    for lo, hi, lbl in [(0.05, 0.10, "0.05–0.10%"),
                         (0.10, 0.20, "0.10–0.20%"),
                         (0.20, 99.,  ">0.20%")]:
        sub_p = [e for e in pdh if lo <= e["sweep_pct"] < hi]
        sub_l = [e for e in pdl if lo <= e["sweep_pct"] < hi]
        if sub_p: wr_line(sub_p, "win_eod", f"PDH {lbl}", n_min=3)
        if sub_l: wr_line(sub_l, "win_eod", f"PDL {lbl}", n_min=3)

    # Gap size buckets
    section("Q3 — GAP SIZE × EOD WR")
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        with_gap = [e for e in ev_list if e.get("gap_pct") is not None]
        if not with_gap:
            continue
        small  = [e for e in with_gap if abs(e["gap_pct"]) < 0.002]
        medium = [e for e in with_gap if 0.002 <= abs(e["gap_pct"]) < 0.005]
        large  = [e for e in with_gap if abs(e["gap_pct"]) >= 0.005]
        if small:  wr_line(small,  "win_eod", f"{label} small gap  (<0.2%)", n_min=3)
        if medium: wr_line(medium, "win_eod", f"{label} medium gap (0.2–0.5%)", n_min=3)
        if large:  wr_line(large,  "win_eod", f"{label} large gap  (>0.5%)", n_min=3)

    # ── Losing trade dates ────────────────────────────────────────────────────
    section("Q3 — LOSING TRADE DATES (for manual review)")
    print(f"\n  PDH losers ({len(pdh_loses)} sessions):")
    for e in sorted(pdh_loses, key=lambda x: x["date"]):
        print(f"    {e['date']}  {e['symbol']:<8}  "
              f"sweep={e['sweep_pct']:.2f}%  "
              f"rev={e['bars_to_rev']}bars  "
              f"gap={e['gap_pct']:.3%}" if e.get('gap_pct') else
              f"    {e['date']}  {e['symbol']:<8}  "
              f"sweep={e['sweep_pct']:.2f}%  "
              f"rev={e['bars_to_rev']}bars")

    print(f"\n  PDL losers ({len(pdl_loses)} sessions):")
    for e in sorted(pdl_loses, key=lambda x: x["date"]):
        print(f"    {e['date']}  {e['symbol']:<8}  "
              f"sweep={e['sweep_pct']:.2f}%  "
              f"rev={e['bars_to_rev']}bars  "
              f"gap={e['gap_pct']:.3%}" if e.get('gap_pct') else
              f"    {e['date']}  {e['symbol']:<8}  "
              f"sweep={e['sweep_pct']:.2f}%  "
              f"rev={e['bars_to_rev']}bars")

    # ── Summary ───────────────────────────────────────────────────────────────
    section("SUMMARY — KEY FINDINGS")
    print()
    total = len(all_events)
    pdh_wr = sum(1 for e in pdh if e["win_eod"]) / len(pdh) if pdh else 0
    pdl_wr = sum(1 for e in pdl if e["win_eod"]) / len(pdl) if pdl else 0
    print(f"  Total events      : {total} (PDH={len(pdh)}, PDL={len(pdl)})")
    print(f"  PDH EOD WR        : {pct(pdh_wr)}  (Exp 35 baseline: 74.3%)")
    print(f"  PDL EOD WR        : {pct(pdl_wr)}  (Exp 35 baseline: 67.6%)")
    print()
    print("  Interpret trajectory table to answer:")
    print("  → Which horizon (T+30m/60m/120m/180m/EOD) has the strongest WR?")
    print("     Front-loaded = enter immediately after rejection confirmation")
    print("     Back-loaded  = trend unfolds slowly, wider stop needed")
    print()
    print("  Interpret reversal speed section to answer:")
    print("  → Does fast (≤10min) rejection predict stronger continuation?")
    print("     If yes: T+1/T+2 bar reversal = higher conviction entry filter")
    print()
    print("  Interpret failure mode section to answer:")
    print("  → What gamma/DTE/gap/depth context characterises the losers?")
    print("     That context becomes the BLOCK condition for live signals")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 35B — PO3 First Sweep: Deep Drill               ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Config (replicating Exp 35 best config):")
    print(f"  OPEN window only    : 09:15–{OPEN_END[0]:02d}:{OPEN_END[1]:02d} IST")
    print(f"  Gap context required: YES")
    print(f"  Sweep threshold     : >= {SWEEP_THRESHOLD*100:.2f}% beyond PDH/PDL")
    print(f"  Reversal window     : <= {REVERSAL_MAX_BARS} bars ({REVERSAL_MAX_BARS*5} min)")
    print(f"  Horizons measured   : T+30m, T+60m, T+120m, T+180m, EOD")
    print()

    all_events = []
    for symbol, instrument_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars_by_date    = fetch_bars_by_date(instrument_id, symbol)
        zones           = fetch_zones(symbol)
        session_markers = fetch_session_markers(symbol)

        events = detect_events(symbol, bars_by_date, zones, session_markers)
        pdh_n  = sum(1 for e in events if e["type"] == "PDH")
        pdl_n  = sum(1 for e in events if e["type"] == "PDL")
        print(f"  Events: PDH={pdh_n}  PDL={pdl_n}  total={len(events)}")
        all_events.extend(events)

    if not all_events:
        print("\nNO EVENTS DETECTED. Verify PDH/PDL zones and bar coverage.")
        sys.exit(1)

    print_results(all_events)


if __name__ == "__main__":
    main()
