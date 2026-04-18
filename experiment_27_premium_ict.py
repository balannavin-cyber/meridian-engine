#!/usr/bin/env python3
"""
experiment_27_premium_ict.py
==============================
Experiment 27: ICT Structural Concepts Applied to Option Premium Bars

Hypothesis:
  ATM option premium (PE/CE) has its own microstructure.
  ICT concepts (OBs, FVGs, sweeps) applied IN PREMIUM SPACE
  predict premium moves — independently of spot direction.

  Premium OB = last up-close candle before >= MIN_MOVE_PCT premium drop
               = zone where premium sellers absorbed buyers
               = if premium returns here, expect rejection (premium falls)

  Premium FVG = gap in premium (bar high < next bar low or vice versa)
               = imbalance = premium tends to fill it

  Premium Sweep = premium spikes above prior high then closes below
               = panic buyers absorbed = premium collapse coming

Theta normalisation:
  Premium has persistent downward drift from theta decay.
  We normalise by adding back estimated theta per bar:
    adjusted = raw + (|theta_per_min| * 5)  [5 min bar]
  This removes decay drift so structural patterns are cleaner.

Outcome metrics:
  ret_premium_30m = (pe_close_T30 - pe_close_T0) / pe_close_T0 * 100
  win_premium = premium moved in predicted direction at T+30m
  Also check: does premium OB rejection predict SPOT reversal?

Tables:
  hist_atm_option_bars_5m  — PE/CE OHLC per 5m bar
  hist_market_state         — spot ret_30m for cross-reference
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

# Pattern detection thresholds (in premium % terms)
MIN_OB_MOVE_PCT   = 1.0   # premium must drop >= 1% after OB candle
MIN_FVG_PCT       = 0.5   # gap must be >= 0.5% of premium
SWEEP_MIN_PCT     = 0.5   # sweep above prior high by >= 0.5%
APPROACH_PCT      = 0.015 # within 1.5% of zone = approaching

# Session filter
MORNING_ONLY = False  # Test all sessions


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


def get_session(bar_ts_str):
    m = get_mins(bar_ts_str)
    if m < 9*60+15:       return "PRE"
    elif m <= 10*60+30:   return "MORNING"
    elif m <= 13*60:      return "MIDDAY"
    elif m <= 14*60+30:   return "AFTERNOON"
    else:                 return "PRECLOSE"


def wr(w, n):
    return w/n*100 if n > 0 else 0


def theta_adjust(premium, theta_per_bar):
    """Add back theta decay to get theta-neutral premium."""
    if premium is None or theta_per_bar is None:
        return premium
    return premium + abs(theta_per_bar)


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 27: ICT Concepts in Option Premium Space")
    log("=" * 65)

    # ── Step 1: Load ATM option bars ─────────────────────────────────────
    log("\nStep 1: Loading hist_atm_option_bars_5m...")
    atm_rows = fetch_all(
        sb, "hist_atm_option_bars_5m",
        "trade_date,bar_ts,symbol,atm_strike,expiry_date,dte,"
        "pe_open,pe_high,pe_low,pe_close,pe_volume,pe_theta,"
        "ce_open,ce_high,ce_low,ce_close,ce_volume,ce_theta",
        order="bar_ts"
    )
    log(f"  {len(atm_rows)} ATM option bars")

    # ── Step 2: Load market state for spot outcome cross-reference ────────
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,gamma_regime,ret_session,ret_30m",
        order="bar_ts"
    )
    mkt_idx = {}
    for r in mkt_rows:
        mins   = get_mins(r["bar_ts"])
        bucket = (mins // 5) * 5
        mkt_idx[(r["trade_date"], r["symbol"], bucket)] = r

    def get_mkt(td, sym, bar_ts):
        mins   = get_mins(bar_ts)
        bucket = (mins // 5) * 5
        m = mkt_idx.get((td, sym, bucket))
        if not m:
            for db in [-5,5,-10,10]:
                m = mkt_idx.get((td, sym, bucket+db))
                if m: break
        return m or {}

    # ── Step 3: Group by day+symbol ──────────────────────────────────────
    log("\nStep 3: Grouping bars by day/symbol...")
    bars_by = defaultdict(list)
    for r in atm_rows:
        bars_by[(r["trade_date"], r["symbol"])].append(r)

    log(f"  {len(bars_by)} day/symbol pairs")

    # ── Step 4: Detect ICT patterns in premium space ─────────────────────
    log("\nStep 4: Detecting premium ICT patterns...")

    # Results storage
    signals = []
    seen    = set()

    for (trade_date, symbol), day_bars in sorted(bars_by.items()):
        day_bars = sorted(day_bars, key=lambda b: b["bar_ts"])
        n        = len(day_bars)

        # Build theta-adjusted close series for PE
        pe_adj = []
        ce_adj = []
        for bar in day_bars:
            pc = float(bar["pe_close"]) if bar.get("pe_close") else None
            cc = float(bar["ce_close"]) if bar.get("ce_close") else None
            pt = float(bar["pe_theta"]) if bar.get("pe_theta") else None
            ct = float(bar["ce_theta"]) if bar.get("ce_theta") else None
            # Theta per 5m bar = theta_per_day / 75 bars
            # pe_theta is already per day (negative), add back abs per bar
            pt_per_bar = abs(pt) / 75 if pt else 0
            ct_per_bar = abs(ct) / 75 if ct else 0
            pe_adj.append((pc + pt_per_bar) if pc else None)
            ce_adj.append((cc + ct_per_bar) if cc else None)

        # ── PE Premium OBs ───────────────────────────────────────────────
        # Last up-close bar before a >= MIN_OB_MOVE_PCT drop in premium
        for i in range(1, n - 1):
            bar    = day_bars[i]
            bar_ts = bar["bar_ts"]
            pc     = float(bar["pe_close"]) if bar.get("pe_close") else None
            po     = float(bar["pe_open"])  if bar.get("pe_open")  else None
            if not pc or not po or pc <= 0:
                continue

            # Up-close bar in premium
            if pc <= po:
                continue

            # Check if next bars show >= MIN_OB_MOVE_PCT drop
            future_closes = [
                float(day_bars[j]["pe_close"])
                for j in range(i+1, min(i+7, n))
                if day_bars[j].get("pe_close")
            ]
            if not future_closes:
                continue

            min_future = min(future_closes)
            drop_pct   = (pc - min_future) / pc * 100

            if drop_pct < MIN_OB_MOVE_PCT:
                continue

            # Valid PE premium OB formed
            # Now look for price returning to this zone
            zone_high = pc
            zone_low  = po
            session   = get_session(bar_ts)

            for j in range(i+4, n):  # skip immediate bars
                ret_bar    = day_bars[j]
                ret_ts     = ret_bar["bar_ts"]
                ret_pc     = float(ret_bar["pe_close"]) if ret_bar.get("pe_close") else None
                if not ret_pc:
                    continue

                # Is premium approaching or in the zone?
                in_zone    = zone_low <= ret_pc <= zone_high
                approaching = (ret_pc > zone_high and
                               (ret_pc - zone_high) / zone_high <= APPROACH_PCT)

                if not (in_zone or approaching):
                    continue

                # Signal: premium returned to OB zone
                sk = (trade_date, symbol, "PE_OB", round(zone_high,2), j)
                if sk in seen:
                    break  # one signal per zone
                seen.add(sk)

                # Outcome: does PE premium fall from here? (OB = supply = sell PE)
                future_from_signal = [
                    float(day_bars[k]["pe_close"])
                    for k in range(j+1, min(j+7, n))
                    if day_bars[k].get("pe_close")
                ]
                if not future_from_signal:
                    break

                # T+30m premium (6 bars = 30 min)
                t30_idx = j + 6
                pe_t30  = float(day_bars[t30_idx]["pe_close"]) if (
                    t30_idx < n and day_bars[t30_idx].get("pe_close")) else None

                ret_premium_30m = (pe_t30 - ret_pc) / ret_pc * 100 if pe_t30 and ret_pc > 0 else None
                # PE OB = supply = expect premium to FALL → win if ret_premium < 0
                win_premium = ret_premium_30m < 0 if ret_premium_30m is not None else None

                # Spot outcome
                mkt        = get_mkt(trade_date, symbol, ret_ts)
                ret_spot   = float(mkt["ret_30m"]) if mkt.get("ret_30m") else None
                # If PE premium falls, spot likely rising → win spot = ret_spot > 0
                win_spot   = ret_spot > 0 if ret_spot is not None else None

                signals.append({
                    "pattern":         "PE_OB",
                    "trade_date":      trade_date,
                    "symbol":          symbol,
                    "ob_ts":           bar_ts,
                    "signal_ts":       ret_ts,
                    "session":         get_session(ret_ts),
                    "zone_high":       zone_high,
                    "zone_low":        zone_low,
                    "ob_drop_pct":     drop_pct,
                    "premium_at_signal": ret_pc,
                    "ret_premium_30m": ret_premium_30m,
                    "win_premium":     win_premium,
                    "ret_spot_30m":    ret_spot,
                    "win_spot":        win_spot,
                    "gamma_regime":    mkt.get("gamma_regime","UNKNOWN"),
                })
                break  # one signal per zone return

        # ── PE Premium Sweeps ────────────────────────────────────────────
        # Premium spikes above recent high then closes below = absorption
        recent_high = None
        recent_high_ts = None

        for i in range(5, n):
            bar    = day_bars[i]
            bar_ts = bar["bar_ts"]
            pc     = float(bar["pe_close"]) if bar.get("pe_close") else None
            ph     = float(bar["pe_high"])  if bar.get("pe_high")  else None
            po     = float(bar["pe_open"])  if bar.get("pe_open")  else None
            if not pc or not ph or not po or pc <= 0:
                continue

            # Track rolling high of last 5 bars
            prior_closes = [
                float(day_bars[k]["pe_close"])
                for k in range(max(0,i-5), i)
                if day_bars[k].get("pe_close")
            ]
            if not prior_closes:
                continue
            prior_high = max(prior_closes)

            # Sweep: bar high exceeds prior high by SWEEP_MIN_PCT
            # AND bar closes BELOW prior high (rejection)
            if (ph > prior_high * (1 + SWEEP_MIN_PCT/100) and
                    pc < prior_high):

                sk = (trade_date, symbol, "PE_SWEEP", i)
                if sk in seen:
                    continue
                seen.add(sk)

                # Outcome at T+30m
                t30_idx = i + 6
                pe_t30  = float(day_bars[t30_idx]["pe_close"]) if (
                    t30_idx < n and day_bars[t30_idx].get("pe_close")) else None
                ret_premium_30m = (pe_t30 - pc) / pc * 100 if pe_t30 and pc > 0 else None
                win_premium = ret_premium_30m < 0 if ret_premium_30m is not None else None

                mkt       = get_mkt(trade_date, symbol, bar_ts)
                ret_spot  = float(mkt["ret_30m"]) if mkt.get("ret_30m") else None
                win_spot  = ret_spot > 0 if ret_spot is not None else None

                signals.append({
                    "pattern":         "PE_SWEEP",
                    "trade_date":      trade_date,
                    "symbol":          symbol,
                    "ob_ts":           bar_ts,
                    "signal_ts":       bar_ts,
                    "session":         get_session(bar_ts),
                    "zone_high":       ph,
                    "zone_low":        pc,
                    "ob_drop_pct":     (ph - pc) / ph * 100,
                    "premium_at_signal": pc,
                    "ret_premium_30m": ret_premium_30m,
                    "win_premium":     win_premium,
                    "ret_spot_30m":    ret_spot,
                    "win_spot":        win_spot,
                    "gamma_regime":    mkt.get("gamma_regime","UNKNOWN"),
                })

        # ── CE Premium OBs (bear equivalent) ────────────────────────────
        for i in range(1, n - 1):
            bar = day_bars[i]
            bar_ts = bar["bar_ts"]
            cc = float(bar["ce_close"]) if bar.get("ce_close") else None
            co = float(bar["ce_open"])  if bar.get("ce_open")  else None
            if not cc or not co or cc <= 0:
                continue
            if cc <= co:  # need up-close
                continue

            future_closes = [
                float(day_bars[j]["ce_close"])
                for j in range(i+1, min(i+7, n))
                if day_bars[j].get("ce_close")
            ]
            if not future_closes:
                continue
            drop_pct = (cc - min(future_closes)) / cc * 100
            if drop_pct < MIN_OB_MOVE_PCT:
                continue

            zone_high = cc
            zone_low  = co

            for j in range(i+4, n):
                ret_bar = day_bars[j]
                ret_ts  = ret_bar["bar_ts"]
                ret_cc  = float(ret_bar["ce_close"]) if ret_bar.get("ce_close") else None
                if not ret_cc:
                    continue

                in_zone    = zone_low <= ret_cc <= zone_high
                approaching = (ret_cc > zone_high and
                               (ret_cc - zone_high) / zone_high <= APPROACH_PCT)
                if not (in_zone or approaching):
                    continue

                sk = (trade_date, symbol, "CE_OB", round(zone_high,2), j)
                if sk in seen:
                    break
                seen.add(sk)

                t30_idx = j + 6
                ce_t30  = float(day_bars[t30_idx]["ce_close"]) if (
                    t30_idx < n and day_bars[t30_idx].get("ce_close")) else None
                ret_premium_30m = (ce_t30 - ret_cc) / ret_cc * 100 if ce_t30 and ret_cc > 0 else None
                win_premium = ret_premium_30m < 0 if ret_premium_30m is not None else None

                mkt      = get_mkt(trade_date, symbol, ret_ts)
                ret_spot = float(mkt["ret_30m"]) if mkt.get("ret_30m") else None
                win_spot = ret_spot < 0 if ret_spot is not None else None  # CE OB = spot falls

                signals.append({
                    "pattern":         "CE_OB",
                    "trade_date":      trade_date,
                    "symbol":          symbol,
                    "ob_ts":           bar_ts,
                    "signal_ts":       ret_ts,
                    "session":         get_session(ret_ts),
                    "zone_high":       zone_high,
                    "zone_low":        zone_low,
                    "ob_drop_pct":     drop_pct,
                    "premium_at_signal": ret_cc,
                    "ret_premium_30m": ret_premium_30m,
                    "win_premium":     win_premium,
                    "ret_spot_30m":    ret_spot,
                    "win_spot":        win_spot,
                    "gamma_regime":    mkt.get("gamma_regime","UNKNOWN"),
                })
                break

    log(f"  Total premium signals: {len(signals)}")
    by_pattern = defaultdict(list)
    for s in signals:
        by_pattern[s["pattern"]].append(s)
    for p, ss in sorted(by_pattern.items()):
        log(f"  {p}: {len(ss)}")

    # ── Step 5: Results ──────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("RESULTS")
    log("=" * 65)

    for pattern in ["PE_OB","PE_SWEEP","CE_OB"]:
        group = by_pattern.get(pattern, [])
        with_prem = [s for s in group if s["win_premium"] is not None]
        with_spot = [s for s in group if s["win_spot"] is not None]

        log(f"\n{'─'*55}")
        log(f"{pattern} (N={len(group)}, with outcome: {len(with_prem)})")

        if not with_prem:
            log("  NO DATA")
            continue

        # Overall premium WR
        pw = sum(1 for s in with_prem if s["win_premium"])
        avg_ret = sum(s["ret_premium_30m"] for s in with_prem) / len(with_prem)
        log(f"  Premium WR:  {wr(pw,len(with_prem)):.1f}% "
            f"| avg ret_premium_30m: {avg_ret:+.2f}%")

        # Spot WR (cross-reference)
        if with_spot:
            sw = sum(1 for s in with_spot if s["win_spot"])
            log(f"  Spot WR:     {wr(sw,len(with_spot)):.1f}% "
                f"(N={len(with_spot)}) — does premium signal predict spot?")

        # By session
        log(f"  By session:")
        sess_data = defaultdict(lambda: {"w":0,"n":0})
        for s in with_prem:
            sess_data[s["session"]]["w"] += s["win_premium"]
            sess_data[s["session"]]["n"] += 1
        for sess in ["MORNING","MIDDAY","AFTERNOON","PRECLOSE"]:
            b = sess_data.get(sess,{"w":0,"n":0})
            if b["n"] == 0: continue
            log(f"    {sess:<12}: {wr(b['w'],b['n']):.1f}% WR (N={b['n']})")

        # By gamma
        log(f"  By gamma:")
        gam_data = defaultdict(lambda: {"w":0,"n":0})
        for s in with_prem:
            gam_data[s["gamma_regime"]]["w"] += s["win_premium"]
            gam_data[s["gamma_regime"]]["n"] += 1
        for g in ["SHORT_GAMMA","LONG_GAMMA","NO_FLIP"]:
            b = gam_data.get(g,{"w":0,"n":0})
            if b["n"] == 0: continue
            log(f"    {g:<15}: {wr(b['w'],b['n']):.1f}% WR (N={b['n']})")

        # By OB strength (drop_pct)
        strong = [s for s in with_prem if s["ob_drop_pct"] >= 3.0]
        weak   = [s for s in with_prem if s["ob_drop_pct"] < 3.0]
        if strong:
            sw2 = sum(1 for s in strong if s["win_premium"])
            log(f"  Strong OB (drop >= 3%): {wr(sw2,len(strong)):.1f}% WR (N={len(strong)})")
        if weak:
            ww = sum(1 for s in weak if s["win_premium"])
            log(f"  Weak OB   (drop < 3%):  {wr(ww,len(weak)):.1f}% WR (N={len(weak)})")

    # ── Verdict ──────────────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("VERDICT")
    log("=" * 65)

    for pattern in ["PE_OB","PE_SWEEP","CE_OB"]:
        group = by_pattern.get(pattern, [])
        with_prem = [s for s in group if s["win_premium"] is not None]
        if not with_prem:
            log(f"\n  {pattern}: NO DATA")
            continue

        pw   = sum(1 for s in with_prem if s["win_premium"])
        wrate = wr(pw, len(with_prem))
        log(f"\n  {pattern}: {wrate:.1f}% premium WR (N={len(with_prem)})")

        if wrate >= 65 and len(with_prem) >= 20:
            log(f"  -> STRONG EDGE: Premium ICT has predictive power")
            log(f"     Build premium OB detector in signal pipeline")
            log(f"     Use as confluence signal alongside spot ICT zones")
        elif wrate >= 58 and len(with_prem) >= 10:
            log(f"  -> MODERATE EDGE: Shadow test + more data")
        elif len(with_prem) < 10:
            log(f"  -> INSUFFICIENT DATA (N={len(with_prem)})")
            log(f"     hist_atm_option_bars_5m may have limited coverage")
        else:
            log(f"  -> WEAK/NO EDGE: Premium structure not predictive")

    log(f"\n  Note: {len(signals)} total premium signals across {len(bars_by)} days")
    log(f"  If N is small, the ATM option bars may not cover all dates.")
    log(f"  Check coverage: python -c \"from dotenv import load_dotenv; "
        f"load_dotenv(); ...\"")

    log("\nExperiment 27 complete.")


if __name__ == "__main__":
    main()
