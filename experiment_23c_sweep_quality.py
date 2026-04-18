#!/usr/bin/env python3
"""
experiment_23c_sweep_quality.py
=================================
Experiment 23c: Sweep Reversal — Quality Filters

Experiments 23 and 23b showed 17-19% WR for mechanical sweep detection.
Hypothesis: the edge exists but only in HIGH QUALITY setups.

Quality dimensions tested:
  1. Zone age — younger zones more likely unmitigated (proxy for first touch)
  2. Wick quality — long lower wick, close near high of rejection bar
  3. Zone boundary precision — how close sweep extreme was to zone entry
  4. Displacement — clean momentum bars after signal bar

Methodology:
  - Re-use sweep detection from Exp 23/23b (PDL/PDH sweep + W zone confluence)
  - Score each sweep on quality dimensions
  - Compare WR: HIGH quality (3-4 dims) vs MEDIUM (2) vs LOW (0-1)

Phase 2 note (not implemented here):
  Once HTF edge confirmed, LTF (5m/1m) entry refinement is the next build:
  CHoCH + LTF OB inside HTF zone = precise entry with tight stop.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime, timedelta

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PAGE_SIZE    = 1000

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

MIN_SWEEP_PCT    = 0.0003   # minimum sweep depth
MAX_BARS_RETURN  = 5
CONFLUENCE_PCT   = 0.005    # W zone proximity

# Quality thresholds
WICK_RATIO_MIN   = 0.40     # lower wick >= 40% of bar range
CLOSE_POS_MIN    = 0.60     # close in top 40% of bar range
ZONE_AGE_MAX     = 10       # zone <= 10 trading days old = "fresh"
PRECISION_MAX    = 0.002    # sweep extreme within 0.2% of zone boundary


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_all(sb, table, select, filters=None, order=None):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select)
        if filters:
            for f in filters:
                method, *args = f
                q = getattr(q, method)(*args)
        if order:
            q = q.order(order)
        q = q.range(offset, offset + PAGE_SIZE - 1)
        for attempt in range(3):
            try:
                rows = q.execute().data
                break
            except Exception as e:
                if attempt == 2:
                    log(f"  ERROR: {e}")
                    return all_rows
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def get_mins(bar_ts_str):
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        return dt.hour * 60 + dt.minute
    except:
        return 0


def is_morning(bar_ts_str):
    m = get_mins(bar_ts_str)
    return (9*60+15) <= m <= (10*60+30)


def wick_quality(bar, direction="bull"):
    """Score wick quality of rejection bar."""
    h = float(bar["high"])
    l = float(bar["low"])
    o = float(bar["open"])
    c = float(bar["close"])
    rng = h - l
    if rng < 0.0001:
        return {"quality": False, "wick_ratio": 0, "close_pos": 0}

    if direction == "bull":
        lower_wick = min(o, c) - l
        wick_ratio = lower_wick / rng
        close_pos  = (c - l) / rng
        is_bullish = c > o
        quality    = (wick_ratio >= WICK_RATIO_MIN and
                     close_pos >= CLOSE_POS_MIN and
                     is_bullish)
    else:
        upper_wick = h - max(o, c)
        wick_ratio = upper_wick / rng
        close_pos  = (h - c) / rng  # close near low of range
        is_bearish = c < o
        quality    = (wick_ratio >= WICK_RATIO_MIN and
                     close_pos >= CLOSE_POS_MIN and
                     is_bearish)

    return {"quality": quality, "wick_ratio": wick_ratio, "close_pos": close_pos}


def zone_precision(sweep_extreme, zone_entry_level, ref_price):
    """How precisely did sweep touch zone entry level?"""
    dist_pct = abs(sweep_extreme - zone_entry_level) / ref_price
    return dist_pct <= PRECISION_MAX, dist_pct


def check_displacement(bars_after, direction="bull", n=3):
    """Do next n bars show clean displacement?"""
    if len(bars_after) < 2:
        return False
    closes = [float(b["close"]) for b in bars_after[:n]]
    if direction == "bull":
        return all(closes[i] > closes[i-1] for i in range(1, len(closes)))
    else:
        return all(closes[i] < closes[i-1] for i in range(1, len(closes)))


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 23c: Sweep Reversal Quality Filters")
    log("=" * 65)

    # ── Step 1: Load zones ───────────────────────────────────────────────
    log("\nStep 1: Loading zones...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low,timeframe",
        order="as_of_date"
    )
    log(f"  {len(raw_zones)} zone rows")

    pdlevels = defaultdict(dict)
    w_demand = defaultdict(list)  # weekly demand zones
    w_supply = defaultdict(list)  # weekly supply zones

    for z in raw_zones:
        key = (z["as_of_date"], z["symbol"])
        pt  = z["pattern_type"]
        tf  = z["timeframe"]

        if pt == "PDL" and tf == "D":
            pdlevels[key]["pdl"] = float(z["zone_low"])
        elif pt == "PDH" and tf == "D":
            pdlevels[key]["pdh"] = float(z["zone_high"])

        if tf == "W":
            entry = {
                "high":     float(z["zone_high"]),
                "low":      float(z["zone_low"]),
                "pattern":  pt,
                "as_of":    z["as_of_date"],
            }
            if pt in ("BULL_OB","BULL_FVG","PDH"):
                w_demand[key].append(entry)
            elif pt in ("BEAR_OB","BEAR_FVG","PDL"):
                w_supply[key].append(entry)

    # ── Step 2: Market state ─────────────────────────────────────────────
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,breadth_regime,"
        "ret_session,ret_30m",
        order="bar_ts"
    )
    log(f"  {len(mkt_rows)} rows")

    mkt_idx = {}
    for r in mkt_rows:
        mkt_idx[(r["trade_date"], r["symbol"], get_mins(r["bar_ts"]))] = r

    # ── Step 3: Spot bars ────────────────────────────────────────────────
    log("\nStep 3: Loading 1-min spot bars...")
    spot_by = defaultdict(list)
    for symbol, inst_id in INSTRUMENTS.items():
        rows = fetch_all(
            sb, "hist_spot_bars_1m",
            "trade_date,bar_ts,open,high,low,close",
            filters=[("eq","instrument_id",inst_id),
                     ("eq","is_pre_market",False)],
            order="bar_ts"
        )
        for r in rows:
            spot_by[(r["trade_date"], symbol)].append(r)
        log(f"  {symbol}: {len(rows)} bars")

    # ── Step 4: Detect + score sweeps ────────────────────────────────────
    log("\nStep 4: Detecting sweeps with quality scoring...")

    signals = []
    seen    = set()

    for (trade_date, symbol), bars in sorted(spot_by.items()):
        morning = [b for b in bars if is_morning(b["bar_ts"])]
        if not morning:
            continue

        all_today = bars  # full day for displacement check
        lvl    = pdlevels.get((trade_date, symbol), {})
        pdl    = lvl.get("pdl")
        pdh    = lvl.get("pdh")
        demand = w_demand.get((trade_date, symbol), [])
        supply = w_supply.get((trade_date, symbol), [])

        # Parse trade_date for zone age calc
        try:
            td = datetime.strptime(trade_date, "%Y-%m-%d").date()
        except:
            continue

        def get_mkt(bar_ts):
            mins = get_mins(bar_ts)
            m = mkt_idx.get((trade_date, symbol, mins))
            if not m:
                for dm in [-1,1,-2,2]:
                    m = mkt_idx.get((trade_date, symbol, mins+dm))
                    if m: break
            return m

        def find_confluent_zone(sweep_extreme, zones, ref):
            """Find closest W zone and return zone + precision."""
            best_zone = None
            best_dist = 999
            for z in zones:
                # Inside zone
                if z["low"] <= sweep_extreme <= z["high"]:
                    dist = 0
                    if dist < best_dist:
                        best_dist = dist
                        best_zone = z
                else:
                    dist = min(abs(sweep_extreme - z["high"]),
                               abs(sweep_extreme - z["low"])) / ref
                    if dist <= CONFLUENCE_PCT and dist < best_dist:
                        best_dist = dist
                        best_zone = z
            return best_zone, best_dist

        def zone_age(z):
            """Days between zone formation and today."""
            try:
                zd = datetime.strptime(z["as_of"], "%Y-%m-%d").date()
                return (td - zd).days
            except:
                return 999

        # ── Bull sweep ───────────────────────────────────────────────────
        if pdl:
            swept = False
            sweep_bar_idx = None
            sweep_low = None

            for i, bar in enumerate(morning):
                close = float(bar["close"])
                low   = float(bar["low"])

                if not swept and close < pdl * (1 - MIN_SWEEP_PCT):
                    swept = True
                    sweep_bar_idx = i
                    sweep_low = low
                    continue

                if swept and close > pdl:
                    bars_to_return = i - sweep_bar_idx
                    if bars_to_return > MAX_BARS_RETURN:
                        swept = False
                        continue

                    sk = (trade_date, symbol, "BULL", round(sweep_low, 0))
                    if sk in seen:
                        swept = False
                        continue
                    seen.add(sk)

                    # Find confluent W zone
                    conf_zone, conf_dist = find_confluent_zone(
                        sweep_low, demand, pdl)

                    # Quality scores
                    wq = wick_quality(bar, "bull")

                    # Zone age (freshness proxy for unmitigated)
                    age = zone_age(conf_zone) if conf_zone else 999

                    # Zone boundary precision
                    if conf_zone:
                        zone_entry = conf_zone["low"]  # entry = bottom of demand zone
                        precise, prec_dist = zone_precision(sweep_low, zone_entry, pdl)
                    else:
                        precise, prec_dist = False, 1.0

                    # Displacement (bars after signal bar)
                    signal_idx = next((j for j, b in enumerate(all_today)
                                      if b["bar_ts"] == bar["bar_ts"]), None)
                    if signal_idx is not None:
                        bars_after = all_today[signal_idx+1:signal_idx+4]
                        displaced  = check_displacement(bars_after, "bull")
                    else:
                        displaced = False

                    # Quality score 0-4
                    score = sum([
                        wq["quality"],      # wick quality
                        age <= ZONE_AGE_MAX, # fresh zone
                        precise,            # precise touch
                        displaced,          # clean displacement
                    ])

                    mkt = get_mkt(bar["bar_ts"])
                    ret_30m = float(mkt["ret_30m"]) if mkt and mkt.get("ret_30m") else None
                    win_30m = ret_30m > 0 if ret_30m is not None else None

                    signals.append({
                        "type":           "BULL",
                        "trade_date":     trade_date,
                        "symbol":         symbol,
                        "sweep_low":      sweep_low,
                        "sweep_depth":    (pdl - sweep_low) / pdl * 100,
                        "bars_to_return": bars_to_return,
                        "confluent":      conf_zone is not None,
                        "conf_dist":      conf_dist,
                        "conf_pattern":   conf_zone["pattern"] if conf_zone else None,
                        "zone_age":       age,
                        "wick_quality":   wq["quality"],
                        "wick_ratio":     wq["wick_ratio"],
                        "close_pos":      wq["close_pos"],
                        "precise":        precise,
                        "prec_dist":      prec_dist,
                        "displaced":      displaced,
                        "quality_score":  score,
                        "gamma_regime":   mkt.get("gamma_regime") if mkt else None,
                        "ret_session":    float(mkt["ret_session"]) if mkt and mkt.get("ret_session") else None,
                        "ret_30m":        ret_30m,
                        "win_30m":        win_30m,
                    })
                    swept = False

        # ── Bear sweep ───────────────────────────────────────────────────
        if pdh:
            swept = False
            sweep_bar_idx = None
            sweep_high = None

            for i, bar in enumerate(morning):
                close = float(bar["close"])
                high  = float(bar["high"])

                if not swept and close > pdh * (1 + MIN_SWEEP_PCT):
                    swept = True
                    sweep_bar_idx = i
                    sweep_high = high
                    continue

                if swept and close < pdh:
                    bars_to_return = i - sweep_bar_idx
                    if bars_to_return > MAX_BARS_RETURN:
                        swept = False
                        continue

                    sk = (trade_date, symbol, "BEAR", round(sweep_high, 0))
                    if sk in seen:
                        swept = False
                        continue
                    seen.add(sk)

                    conf_zone, conf_dist = find_confluent_zone(
                        sweep_high, supply, pdh)
                    wq     = wick_quality(bar, "bear")
                    age    = zone_age(conf_zone) if conf_zone else 999

                    if conf_zone:
                        zone_entry = conf_zone["high"]
                        precise, prec_dist = zone_precision(sweep_high, zone_entry, pdh)
                    else:
                        precise, prec_dist = False, 1.0

                    signal_idx = next((j for j, b in enumerate(all_today)
                                      if b["bar_ts"] == bar["bar_ts"]), None)
                    if signal_idx is not None:
                        bars_after = all_today[signal_idx+1:signal_idx+4]
                        displaced  = check_displacement(bars_after, "bear")
                    else:
                        displaced = False

                    score = sum([
                        wq["quality"],
                        age <= ZONE_AGE_MAX,
                        precise,
                        displaced,
                    ])

                    mkt = get_mkt(bar["bar_ts"])
                    ret_30m = float(mkt["ret_30m"]) if mkt and mkt.get("ret_30m") else None
                    win_30m = ret_30m < 0 if ret_30m is not None else None

                    signals.append({
                        "type":           "BEAR",
                        "trade_date":     trade_date,
                        "symbol":         symbol,
                        "sweep_high":     sweep_high,
                        "sweep_depth":    (sweep_high - pdh) / pdh * 100,
                        "bars_to_return": bars_to_return,
                        "confluent":      conf_zone is not None,
                        "conf_dist":      conf_dist,
                        "conf_pattern":   conf_zone["pattern"] if conf_zone else None,
                        "zone_age":       age,
                        "wick_quality":   wq["quality"],
                        "wick_ratio":     wq["wick_ratio"],
                        "close_pos":      wq["close_pos"],
                        "precise":        precise,
                        "prec_dist":      prec_dist,
                        "displaced":      displaced,
                        "quality_score":  score,
                        "gamma_regime":   mkt.get("gamma_regime") if mkt else None,
                        "ret_session":    float(mkt["ret_session"]) if mkt and mkt.get("ret_session") else None,
                        "ret_30m":        ret_30m,
                        "win_30m":        win_30m,
                    })
                    swept = False

    log(f"  Total sweeps: {len(signals)}")

    # ── Step 5: Results by quality score ────────────────────────────────
    log("\n" + "=" * 65)
    log("RESULTS BY QUALITY SCORE")
    log("=" * 65)

    for sweep_type in ["BULL","BEAR"]:
        direction = "BUY_CE" if sweep_type == "BULL" else "BUY_PE"
        group = [s for s in signals if s["type"] == sweep_type]
        with_ret = [s for s in group if s["win_30m"] is not None]
        log(f"\n{'─'*55}")
        log(f"{sweep_type} SWEEP ({direction}) — {len(group)} total, "
            f"{len(with_ret)} with outcome")

        if not with_ret:
            log("  NO DATA")
            continue

        # Overall
        wins = sum(1 for s in with_ret if s["win_30m"])
        log(f"  Overall WR: {wins/len(with_ret)*100:.1f}%")

        # By quality score
        log(f"\n  {'Score':<8} {'N':>4} {'WR':>8} {'Wick%':>7} "
            f"{'Fresh%':>7} {'Precise%':>9} {'Disp%':>7}")
        log(f"  {'-'*55}")

        for score in [4, 3, 2, 1, 0]:
            sub = [s for s in with_ret if s["quality_score"] == score]
            if not sub:
                continue
            sw = sum(1 for s in sub if s["win_30m"])
            wrate = sw / len(sub) * 100
            wick_pct  = sum(1 for s in sub if s["wick_quality"]) / len(sub) * 100
            fresh_pct = sum(1 for s in sub if s["zone_age"] <= ZONE_AGE_MAX) / len(sub) * 100
            prec_pct  = sum(1 for s in sub if s["precise"]) / len(sub) * 100
            disp_pct  = sum(1 for s in sub if s["displaced"]) / len(sub) * 100
            log(f"  {score}/4{'':<5} {len(sub):>4} {wrate:>7.1f}% "
                f"{wick_pct:>6.0f}% {fresh_pct:>6.0f}% "
                f"{prec_pct:>8.0f}% {disp_pct:>6.0f}%")

        # Individual quality dimension contribution
        log(f"\n  Individual quality dimension WR:")
        dims = [
            ("wick_quality", "Wick quality"),
            ("zone_age_fresh", "Zone fresh (<=10d)"),
            ("precise", "Precise touch"),
            ("displaced", "Clean displacement"),
        ]
        for dim_key, dim_label in dims:
            if dim_key == "zone_age_fresh":
                yes = [s for s in with_ret if s["zone_age"] <= ZONE_AGE_MAX]
                no  = [s for s in with_ret if s["zone_age"] >  ZONE_AGE_MAX]
            else:
                yes = [s for s in with_ret if s.get(dim_key)]
                no  = [s for s in with_ret if not s.get(dim_key)]

            if yes:
                yw = sum(1 for s in yes if s["win_30m"])
                log(f"    {dim_label:<25} YES: {yw/len(yes)*100:.1f}% (N={len(yes)})  "
                    f"NO: {sum(1 for s in no if s['win_30m'])/len(no)*100 if no else 0:.1f}% (N={len(no)})")

    # ── Verdict ──────────────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("VERDICT")
    log("=" * 65)

    for sweep_type in ["BULL","BEAR"]:
        group = [s for s in signals
                if s["type"] == sweep_type and s["win_30m"] is not None]
        if not group:
            continue

        high_q = [s for s in group if s["quality_score"] >= 3]
        if not high_q:
            log(f"\n  {sweep_type}: No high-quality (3+/4) setups found")
            continue

        hw = sum(1 for s in high_q if s["win_30m"])
        hwr = hw / len(high_q) * 100

        log(f"\n  {sweep_type} HIGH QUALITY (3-4/4): {hwr:.1f}% WR (N={len(high_q)})")

        if hwr >= 70 and len(high_q) >= 8:
            log(f"  -> STRONG EDGE CONFIRMED")
            log(f"     Quality filters unlock the sweep reversal edge")
            log(f"     Build ENH-54 with quality gates:")
            log(f"       1. W zone confluence required")
            log(f"       2. Wick quality required (ratio >= {WICK_RATIO_MIN})")
            log(f"       3. Zone age <= {ZONE_AGE_MAX} days preferred")
            log(f"       4. Displacement confirmation preferred")
            log(f"     Phase 2: LTF entry (5m CHoCH) after HTF confirms")
        elif hwr >= 60 and len(high_q) >= 5:
            log(f"  -> MODERATE EDGE: Shadow test + more live data needed")
        else:
            log(f"  -> INSUFFICIENT EDGE at quality score 3+/4")
            log(f"     Quality filters don't rescue the sweep reversal pattern")
            log(f"     Today's trade was likely a discretionary outlier")

    log(f"\n  Quality dimension summary:")
    log(f"    WICK_RATIO_MIN:  {WICK_RATIO_MIN} (lower wick >= {WICK_RATIO_MIN*100:.0f}% of range)")
    log(f"    ZONE_AGE_MAX:    {ZONE_AGE_MAX} trading days")
    log(f"    PRECISION_MAX:   {PRECISION_MAX*100:.1f}% from zone entry")
    log(f"    DISPLACEMENT:    3 consecutive bars in direction")

    log("\nExperiment 23c complete.")


if __name__ == "__main__":
    main()
