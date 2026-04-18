#!/usr/bin/env python3
"""
experiment_23b_sweep_htf_confluence.py
=========================================
Experiment 23b: Liquidity Sweep into HTF Zone — Confluence Reversal

Refinement of Experiment 23 which showed 17.8% WR for naked PDL sweeps.

Today's NIFTY trade showed the correct setup:
  1. Morning PDL sweep (price below D PDL 24,136)
  2. Price reaches W PDH zone 24,054-24,094 (HTF demand nearby)  ← key
  3. Rejection from that zone (close > open, bullish bar)          ← key
  4. Close back above PDL = entry

Hypothesis:
  When a PDL sweep lands INTO or NEAR a W zone (BULL_OB/BULL_FVG/PDH),
  the reversal WR is significantly higher than naked sweeps.

  Similarly for PDH sweeps into BEAR_OB/BEAR_FVG/PDL zones.

Confluence definition:
  - Sweep low must be within CONFLUENCE_PCT of a W zone boundary
  - OR sweep low must be inside a W zone

Tables:
  hist_spot_bars_1m    — 1-min bars for sweep detection
  hist_ict_htf_zones   — W zones for confluence check
  hist_market_state    — regime context + ret_30m
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime

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

MIN_SWEEP_PCT   = 0.0003  # 0.03% minimum sweep below PDL
MAX_BARS_RETURN = 5
CONFLUENCE_PCT  = 0.005   # 0.5% — sweep low within this % of W zone


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


def is_confluent_with_w_zone(sweep_extreme, w_zones, spot):
    """Check if sweep extreme is near or inside a weekly zone."""
    for z in w_zones:
        # Inside zone
        if z["low"] <= sweep_extreme <= z["high"]:
            return True, z["pattern"]
        # Within CONFLUENCE_PCT of zone boundary
        dist = min(abs(sweep_extreme - z["high"]),
                   abs(sweep_extreme - z["low"]))
        if dist / spot <= CONFLUENCE_PCT:
            return True, z["pattern"]
    return False, None


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 23b: Sweep into HTF Zone Confluence")
    log("=" * 65)

    # ── Step 1: Load PDL/PDH + W zones ──────────────────────────────────
    log("\nStep 1: Loading HTF zones...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low,timeframe",
        order="as_of_date"
    )
    log(f"  {len(raw_zones)} total zone rows")

    pdlevels  = defaultdict(dict)
    w_zones   = defaultdict(list)  # Weekly BULL/BEAR zones for confluence

    for z in raw_zones:
        key = (z["as_of_date"], z["symbol"])
        pt  = z["pattern_type"]
        tf  = z["timeframe"]

        if pt == "PDL" and tf == "D":
            pdlevels[key]["pdl"] = float(z["zone_low"])
        elif pt == "PDH" and tf == "D":
            pdlevels[key]["pdh"] = float(z["zone_high"])

        # Weekly demand zones (for bull sweep confluence)
        if tf == "W" and pt in ("BULL_OB", "BULL_FVG", "PDH"):
            w_zones[key].append({
                "high":    float(z["zone_high"]),
                "low":     float(z["zone_low"]),
                "pattern": pt,
                "type":    "demand",
            })
        # Weekly supply zones (for bear sweep confluence)
        if tf == "W" and pt in ("BEAR_OB", "BEAR_FVG", "PDL"):
            w_zones[key].append({
                "high":    float(z["zone_high"]),
                "low":     float(z["zone_low"]),
                "pattern": pt,
                "type":    "supply",
            })

    # ── Step 2: Load market state ────────────────────────────────────────
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,breadth_regime,"
        "iv_regime,ret_session,ret_30m",
        order="bar_ts"
    )
    log(f"  {len(mkt_rows)} rows")

    mkt_idx = {}
    for r in mkt_rows:
        mkt_idx[(r["trade_date"], r["symbol"], get_mins(r["bar_ts"]))] = r

    # ── Step 3: Load 1-min bars ──────────────────────────────────────────
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

    # ── Step 4: Detect sweeps + confluence ───────────────────────────────
    log("\nStep 4: Detecting sweeps with HTF confluence...")

    signals = []
    seen    = set()

    for (trade_date, symbol), bars in sorted(spot_by.items()):
        morning = [b for b in bars if is_morning(b["bar_ts"])]
        if not morning:
            continue

        lvl   = pdlevels.get((trade_date, symbol), {})
        pdl   = lvl.get("pdl")
        pdh   = lvl.get("pdh")
        wzones = w_zones.get((trade_date, symbol), [])

        demand_zones = [z for z in wzones if z["type"] == "demand"]
        supply_zones = [z for z in wzones if z["type"] == "supply"]

        # ── Bull sweep ───────────────────────────────────────────────────
        if pdl:
            swept = False
            sweep_bar_idx = None
            sweep_low = None

            for i, bar in enumerate(morning):
                close = float(bar["close"])
                low   = float(bar["low"])

                if not swept and close < pdl * (1 - MIN_SWEEP_PCT):
                    swept         = True
                    sweep_bar_idx = i
                    sweep_low     = low
                    continue

                if swept and close > pdl:
                    bars_to_return = i - sweep_bar_idx
                    if bars_to_return > MAX_BARS_RETURN:
                        swept = False
                        continue

                    # Check W zone confluence at sweep low
                    confluent, conf_pattern = is_confluent_with_w_zone(
                        sweep_low, demand_zones, pdl)

                    bar_ts = bar["bar_ts"]
                    mins   = get_mins(bar_ts)
                    mkt    = mkt_idx.get((trade_date, symbol, mins))
                    if not mkt:
                        for dm in [-1,1,-2,2]:
                            mkt = mkt_idx.get((trade_date, symbol, mins+dm))
                            if mkt: break

                    sk = (trade_date, symbol, "BULL", round(sweep_low,0))
                    if sk not in seen:
                        seen.add(sk)
                        ret_30m = float(mkt["ret_30m"]) if mkt and mkt.get("ret_30m") else None
                        win_30m = ret_30m > 0 if ret_30m is not None else None
                        sweep_depth = (pdl - sweep_low) / pdl * 100

                        signals.append({
                            "type":           "BULL_SWEEP",
                            "confluent":      confluent,
                            "conf_pattern":   conf_pattern,
                            "trade_date":     trade_date,
                            "symbol":         symbol,
                            "sweep_low":      sweep_low,
                            "sweep_depth_pct": sweep_depth,
                            "bars_to_return": bars_to_return,
                            "gamma_regime":   mkt.get("gamma_regime") if mkt else None,
                            "breadth_regime": mkt.get("breadth_regime") if mkt else None,
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
                    swept         = True
                    sweep_bar_idx = i
                    sweep_high    = high
                    continue

                if swept and close < pdh:
                    bars_to_return = i - sweep_bar_idx
                    if bars_to_return > MAX_BARS_RETURN:
                        swept = False
                        continue

                    confluent, conf_pattern = is_confluent_with_w_zone(
                        sweep_high, supply_zones, pdh)

                    bar_ts = bar["bar_ts"]
                    mins   = get_mins(bar_ts)
                    mkt    = mkt_idx.get((trade_date, symbol, mins))
                    if not mkt:
                        for dm in [-1,1,-2,2]:
                            mkt = mkt_idx.get((trade_date, symbol, mins+dm))
                            if mkt: break

                    sk = (trade_date, symbol, "BEAR", round(sweep_high,0))
                    if sk not in seen:
                        seen.add(sk)
                        ret_30m = float(mkt["ret_30m"]) if mkt and mkt.get("ret_30m") else None
                        win_30m = ret_30m < 0 if ret_30m is not None else None
                        sweep_depth = (sweep_high - pdh) / pdh * 100

                        signals.append({
                            "type":           "BEAR_SWEEP",
                            "confluent":      confluent,
                            "conf_pattern":   conf_pattern,
                            "trade_date":     trade_date,
                            "symbol":         symbol,
                            "sweep_high":     sweep_high,
                            "sweep_depth_pct": sweep_depth,
                            "bars_to_return": bars_to_return,
                            "gamma_regime":   mkt.get("gamma_regime") if mkt else None,
                            "breadth_regime": mkt.get("breadth_regime") if mkt else None,
                            "ret_session":    float(mkt["ret_session"]) if mkt and mkt.get("ret_session") else None,
                            "ret_30m":        ret_30m,
                            "win_30m":        win_30m,
                        })
                    swept = False

    log(f"  Total sweeps: {len(signals)}")
    bull = [s for s in signals if s["type"]=="BULL_SWEEP"]
    bear = [s for s in signals if s["type"]=="BEAR_SWEEP"]
    log(f"  Bull sweeps: {len(bull)} "
        f"(confluent: {sum(1 for s in bull if s['confluent'])})")
    log(f"  Bear sweeps: {len(bear)} "
        f"(confluent: {sum(1 for s in bear if s['confluent'])})")

    # ── Step 5: Results ──────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("RESULTS")
    log("=" * 65)

    def analyse(group, label, direction):
        with_ret = [s for s in group if s["win_30m"] is not None]
        if not with_ret:
            log(f"\n  {label}: NO DATA")
            return None, None

        conf_s   = [s for s in with_ret if s["confluent"]]
        noconf_s = [s for s in with_ret if not s["confluent"]]

        def stats(subset, sublabel):
            if not subset:
                return None
            wins = sum(1 for s in subset if s["win_30m"])
            n    = len(subset)
            wrate = wins / n * 100
            avg  = sum(s["ret_30m"] for s in subset) / n
            log(f"  {sublabel} (N={n}): {wrate:.1f}% WR | avg ret30m {avg:+.3f}%")
            return wrate, n

        log(f"\n  {label}:")
        c_result  = stats(conf_s,   "  WITH W zone confluence   ")
        nc_result = stats(noconf_s, "  WITHOUT W zone confluence")

        if c_result and nc_result:
            lift = c_result[0] - nc_result[0]
            log(f"  Confluence lift: {lift:+.1f}pp")

        # By momentum alignment for confluent signals
        if conf_s:
            aligned = [s for s in conf_s
                      if s.get("ret_session") is not None and
                      ((direction == "BUY_CE" and float(s["ret_session"]) > 0.05) or
                       (direction == "BUY_PE" and float(s["ret_session"]) < -0.05))]
            if aligned:
                aw = sum(1 for s in aligned if s["win_30m"])
                log(f"  Confluent + momentum aligned (N={len(aligned)}): "
                    f"{wr(aw,len(aligned)):.1f}% WR")

        return c_result, nc_result

    def wr(w, n):
        return w/n*100 if n > 0 else 0

    bull_c, bull_nc = analyse(bull, "BULL SWEEP (BUY_CE)", "BUY_CE")
    bear_c, bear_nc = analyse(bear, "BEAR SWEEP (BUY_PE)", "BUY_PE")

    # ── Verdict ──────────────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("VERDICT")
    log("=" * 65)

    if not signals:
        log("\n  ZERO sweeps — data issue")
        return

    def verdict(result, label):
        if not result or not result[0]:
            log(f"\n  {label}: INSUFFICIENT DATA")
            return
        wrate, n = result
        log(f"\n  {label}: {wrate:.1f}% WR (N={n})")
        if wrate >= 70 and n >= 10:
            log(f"  -> STRONG EDGE: Build ENH-54 sweep reversal detector")
            log(f"     Gate: PDL/PDH sweep + W zone confluence + close back")
        elif wrate >= 60 and n >= 8:
            log(f"  -> MODERATE EDGE: Shadow test before live")
        elif wrate >= 55 and n >= 5:
            log(f"  -> WEAK EDGE: Needs more data. Monitor live occurrences.")
        else:
            log(f"  -> NO EDGE: Even with W zone confluence, sweep reversal fails")

    verdict(bull_c, "BULL SWEEP + W zone confluence")
    verdict(bear_c, "BEAR SWEEP + W zone confluence")

    if bull_c and bull_nc and bull_c[0] and bull_nc[0]:
        lift = bull_c[0] - bull_nc[0]
        log(f"\n  W zone confluence adds {lift:+.1f}pp to bull sweep reversal")
        if lift >= 15:
            log(f"  -> Zone confluence is the KEY differentiator")
            log(f"     Naked sweeps (23): 17.8% WR")
            log(f"     Confluent sweeps (23b): {bull_c[0]:.1f}% WR")

    log("\nExperiment 23b complete.")


if __name__ == "__main__":
    main()
