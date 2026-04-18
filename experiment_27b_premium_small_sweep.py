#!/usr/bin/env python3
"""
experiment_27b_premium_small_sweep.py
=======================================
Experiment 27b: Small PE Premium Sweep — Refined Signal

From Experiment 27:
  PE_SWEEP with small drop (<3%): 69.3% WR (N=316) — STRONG EDGE
  PE_SWEEP with large drop (>3%): 49.1% WR (N=9762) — NO EDGE

Hypothesis:
  A small, controlled PE premium sweep above a prior session high
  = institutional sellers absorbing liquidity at a premium resistance
  = premium collapses back = spot rises

  This is ICT "engineered liquidity" in premium space:
  - Large sweep = panic = random
  - Small sweep = controlled absorption = directional edge

Refinements vs Exp 27:
  1. Only first sweep per session (not every bar)
  2. Must sweep above PRIOR SESSION HIGH (not just prior 5 bars)
  3. Sweep size strictly < 2% (tighter than 3%)
  4. Close-back within 2 bars (quick rejection = stronger)
  5. Morning session only (our best session)
  6. Cross-reference with spot momentum and gamma regime

Also test:
  CE premium small sweep (spot falls) — symmetric signal
  Premium sweep + spot ICT zone confluence — combined signal
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

# Tight filters
MAX_SWEEP_PCT    = 0.02   # sweep must be < 2% above prior high
MIN_SWEEP_PCT    = 0.002  # sweep must be > 0.2% above prior high (meaningful)
MAX_BARS_RETURN  = 2      # must close back within 2 bars (quick rejection)


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


def is_morning(bar_ts_str):
    m = get_mins(bar_ts_str)
    return (9*60+15) <= m <= (10*60+30)


def wr(w, n):
    return w/n*100 if n > 0 else 0


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 27b: Small PE Premium Sweep — Refined Signal")
    log("=" * 65)

    # ── Step 1: Load ATM option bars ─────────────────────────────────────
    log("\nStep 1: Loading hist_atm_option_bars_5m...")
    atm_rows = fetch_all(
        sb, "hist_atm_option_bars_5m",
        "trade_date,bar_ts,symbol,atm_strike,"
        "pe_open,pe_high,pe_low,pe_close,"
        "ce_open,ce_high,ce_low,ce_close",
        order="bar_ts"
    )
    log(f"  {len(atm_rows)} ATM option bars")

    # ── Step 2: Market state ─────────────────────────────────────────────
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,gamma_regime,breadth_regime,"
        "ret_session,ret_30m",
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

    # ── Step 3: Load ICT pattern signals for confluence ───────────────────
    log("\nStep 3: Loading ICT pattern signals for confluence check...")
    ict_rows = fetch_all(
        sb, "hist_pattern_signals",
        "trade_date,symbol,bar_ts,pattern_type,direction,session"
    )
    # Index: (date, symbol) -> set of sessions with active ICT signal
    ict_by_date = defaultdict(set)
    for r in ict_rows:
        ict_by_date[(r["trade_date"], r["symbol"])].add(r["session"])

    # ── Step 4: Group bars by day ─────────────────────────────────────────
    bars_by = defaultdict(list)
    for r in atm_rows:
        bars_by[(r["trade_date"], r["symbol"])].append(r)

    # ── Step 5: Detect small sweeps ──────────────────────────────────────
    log("\nStep 4: Detecting small PE/CE sweeps...")

    signals = []

    for (trade_date, symbol), day_bars in sorted(bars_by.items()):
        day_bars = sorted(day_bars, key=lambda b: b["bar_ts"])
        n        = len(day_bars)

        # Get prior session high for PE and CE
        # (last bar of previous day or pre-market high)
        morning_bars = [b for b in day_bars if is_morning(b["bar_ts"])]
        non_morning  = [b for b in day_bars if not is_morning(b["bar_ts"])]

        if not morning_bars:
            continue

        # Prior session high = max PE close from non-morning bars yesterday
        # Proxy: use first 3 bars of today to establish session reference
        # Better: use yesterday's last bar
        # For now: use max of first 2 morning bars as the reference high
        # (price before any sweeps)

        # ── PE small sweeps ───────────────────────────────────────────────
        pe_swept_this_session = False

        for i in range(2, len(morning_bars)):
            bar    = morning_bars[i]
            bar_ts = bar["bar_ts"]

            ph = float(bar["pe_high"])  if bar.get("pe_high")  else None
            pc = float(bar["pe_close"]) if bar.get("pe_close") else None
            if not ph or not pc or pc <= 0:
                continue

            # Prior high = max close of earlier morning bars
            prior_closes = [
                float(morning_bars[k]["pe_close"])
                for k in range(0, i)
                if morning_bars[k].get("pe_close")
            ]
            if not prior_closes:
                continue
            prior_high = max(prior_closes)

            # Small sweep: high exceeds prior high by 0.2-2%
            # AND close is BELOW prior high (rejection)
            sweep_pct = (ph - prior_high) / prior_high
            if not (MIN_SWEEP_PCT <= sweep_pct <= MAX_SWEEP_PCT):
                continue
            if pc >= prior_high:
                continue

            # Only first sweep per morning session
            if pe_swept_this_session:
                continue
            pe_swept_this_session = True

            # T+30m premium outcome
            t30_idx = i + 6
            pe_t30  = float(morning_bars[t30_idx]["pe_close"]) if (
                t30_idx < len(morning_bars) and
                morning_bars[t30_idx].get("pe_close")) else None

            # Try full day bars if morning runs out
            if pe_t30 is None:
                bar_idx = next((j for j, b in enumerate(day_bars)
                               if b["bar_ts"] == bar_ts), None)
                if bar_idx is not None and bar_idx + 6 < n:
                    pe_t30 = float(day_bars[bar_idx+6]["pe_close"]) if \
                        day_bars[bar_idx+6].get("pe_close") else None

            ret_prem = (pe_t30 - pc) / pc * 100 if pe_t30 and pc > 0 else None
            win_prem = ret_prem < 0 if ret_prem is not None else None  # PE falls = win

            mkt      = get_mkt(trade_date, symbol, bar_ts)
            ret_spot = float(mkt["ret_30m"]) if mkt.get("ret_30m") else None
            win_spot = ret_spot > 0 if ret_spot is not None else None  # spot rises = win

            ret_sess  = float(mkt["ret_session"]) if mkt.get("ret_session") else None
            gamma     = mkt.get("gamma_regime","UNKNOWN")
            breadth   = mkt.get("breadth_regime","UNKNOWN")

            # ICT confluence: is there an active ICT signal in MORNING session?
            has_ict = "MORNING" in ict_by_date.get((trade_date, symbol), set())

            # Momentum: spot already rising into the PE sweep? (bullish context)
            mom_aligned = ret_sess is not None and ret_sess > 0.05

            signals.append({
                "type":         "PE_SMALL_SWEEP",
                "trade_date":   trade_date,
                "symbol":       symbol,
                "bar_ts":       bar_ts,
                "prior_high":   prior_high,
                "sweep_high":   ph,
                "sweep_pct":    sweep_pct * 100,
                "close_back":   pc,
                "gamma":        gamma,
                "breadth":      breadth,
                "ret_session":  ret_sess,
                "mom_aligned":  mom_aligned,
                "has_ict":      has_ict,
                "ret_prem_30m": ret_prem,
                "win_prem":     win_prem,
                "ret_spot_30m": ret_spot,
                "win_spot":     win_spot,
            })

        # ── CE small sweeps (symmetric) ───────────────────────────────────
        ce_swept_this_session = False

        for i in range(2, len(morning_bars)):
            bar    = morning_bars[i]
            bar_ts = bar["bar_ts"]

            ch = float(bar["ce_high"])  if bar.get("ce_high")  else None
            cc = float(bar["ce_close"]) if bar.get("ce_close") else None
            if not ch or not cc or cc <= 0:
                continue

            prior_closes = [
                float(morning_bars[k]["ce_close"])
                for k in range(0, i)
                if morning_bars[k].get("ce_close")
            ]
            if not prior_closes:
                continue
            prior_high = max(prior_closes)

            sweep_pct = (ch - prior_high) / prior_high
            if not (MIN_SWEEP_PCT <= sweep_pct <= MAX_SWEEP_PCT):
                continue
            if cc >= prior_high:
                continue

            if ce_swept_this_session:
                continue
            ce_swept_this_session = True

            t30_idx = i + 6
            ce_t30  = float(morning_bars[t30_idx]["ce_close"]) if (
                t30_idx < len(morning_bars) and
                morning_bars[t30_idx].get("ce_close")) else None

            if ce_t30 is None:
                bar_idx = next((j for j, b in enumerate(day_bars)
                               if b["bar_ts"] == bar_ts), None)
                if bar_idx is not None and bar_idx + 6 < n:
                    ce_t30 = float(day_bars[bar_idx+6]["ce_close"]) if \
                        day_bars[bar_idx+6].get("ce_close") else None

            ret_prem = (ce_t30 - cc) / cc * 100 if ce_t30 and cc > 0 else None
            win_prem = ret_prem < 0 if ret_prem is not None else None  # CE falls = win (spot falls)

            mkt      = get_mkt(trade_date, symbol, bar_ts)
            ret_spot = float(mkt["ret_30m"]) if mkt.get("ret_30m") else None
            win_spot = ret_spot < 0 if ret_spot is not None else None  # spot falls = win

            ret_sess  = float(mkt["ret_session"]) if mkt.get("ret_session") else None
            gamma     = mkt.get("gamma_regime","UNKNOWN")
            breadth   = mkt.get("breadth_regime","UNKNOWN")
            has_ict   = "MORNING" in ict_by_date.get((trade_date, symbol), set())
            mom_aligned = ret_sess is not None and ret_sess < -0.05

            signals.append({
                "type":         "CE_SMALL_SWEEP",
                "trade_date":   trade_date,
                "symbol":       symbol,
                "bar_ts":       bar_ts,
                "prior_high":   prior_high,
                "sweep_high":   ch,
                "sweep_pct":    sweep_pct * 100,
                "close_back":   cc,
                "gamma":        gamma,
                "breadth":      breadth,
                "ret_session":  ret_sess,
                "mom_aligned":  mom_aligned,
                "has_ict":      has_ict,
                "ret_prem_30m": ret_prem,
                "win_prem":     win_prem,
                "ret_spot_30m": ret_spot,
                "win_spot":     win_spot,
            })

    log(f"  PE small sweeps: {sum(1 for s in signals if s['type']=='PE_SMALL_SWEEP')}")
    log(f"  CE small sweeps: {sum(1 for s in signals if s['type']=='CE_SMALL_SWEEP')}")

    # ── Step 6: Results ──────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("RESULTS")
    log("=" * 65)

    for sweep_type in ["PE_SMALL_SWEEP","CE_SMALL_SWEEP"]:
        direction = "BUY_CE (spot rises)" if sweep_type == "PE_SMALL_SWEEP" else "BUY_PE (spot falls)"
        group = [s for s in signals if s["type"] == sweep_type]
        with_prem = [s for s in group if s["win_prem"] is not None]
        with_spot = [s for s in group if s["win_spot"] is not None]

        log(f"\n{'─'*60}")
        log(f"{sweep_type} → {direction}")
        log(f"Total: {len(group)} | With outcome: {len(with_prem)}")

        if not with_prem:
            log("  NO DATA")
            continue

        pw = sum(1 for s in with_prem if s["win_prem"])
        avg_ret = sum(s["ret_prem_30m"] for s in with_prem) / len(with_prem)
        log(f"\n  PREMIUM WR: {wr(pw,len(with_prem)):.1f}% | avg prem ret: {avg_ret:+.2f}%")

        if with_spot:
            sw = sum(1 for s in with_spot if s["win_spot"])
            log(f"  SPOT WR:    {wr(sw,len(with_spot)):.1f}% (N={len(with_spot)})")

        # By sweep size
        small = [s for s in with_prem if s["sweep_pct"] < 1.0]
        med   = [s for s in with_prem if 1.0 <= s["sweep_pct"] < 1.5]
        large = [s for s in with_prem if s["sweep_pct"] >= 1.5]
        log(f"\n  By sweep size:")
        for label, sub in [("0.2-1.0%", small), ("1.0-1.5%", med), ("1.5-2.0%", large)]:
            if not sub: continue
            sw2 = sum(1 for s in sub if s["win_prem"])
            log(f"    {label}: {wr(sw2,len(sub)):.1f}% WR (N={len(sub)})")

        # By gamma
        log(f"\n  By gamma:")
        by_g = defaultdict(lambda: {"w":0,"n":0})
        for s in with_prem:
            by_g[s["gamma"]]["w"] += s["win_prem"]
            by_g[s["gamma"]]["n"] += 1
        for g in ["SHORT_GAMMA","LONG_GAMMA","NO_FLIP"]:
            b = by_g.get(g,{"w":0,"n":0})
            if b["n"] == 0: continue
            log(f"    {g:<15}: {wr(b['w'],b['n']):.1f}% WR (N={b['n']})")

        # With momentum aligned
        mom = [s for s in with_prem if s["mom_aligned"]]
        no_mom = [s for s in with_prem if not s["mom_aligned"]]
        log(f"\n  Momentum aligned: {wr(sum(1 for s in mom if s['win_prem']),len(mom)):.1f}% WR (N={len(mom)})")
        log(f"  Momentum opposed: {wr(sum(1 for s in no_mom if s['win_prem']),len(no_mom)):.1f}% WR (N={len(no_mom)})")

        # With ICT confluence
        ict_yes = [s for s in with_prem if s["has_ict"]]
        ict_no  = [s for s in with_prem if not s["has_ict"]]
        log(f"\n  ICT zone active (confluence):")
        log(f"    WITH ICT:    {wr(sum(1 for s in ict_yes if s['win_prem']),len(ict_yes)):.1f}% WR (N={len(ict_yes)})")
        log(f"    WITHOUT ICT: {wr(sum(1 for s in ict_no if s['win_prem']),len(ict_no)):.1f}% WR (N={len(ict_no)})")

        # Best combination
        log(f"\n  Best combination (small sweep + mom aligned + ICT):")
        best = [s for s in with_prem
                if s["sweep_pct"] < 1.0
                and s["mom_aligned"]
                and s["has_ict"]]
        if best:
            bw = sum(1 for s in best if s["win_prem"])
            log(f"    {wr(bw,len(best)):.1f}% WR (N={len(best)})")
        else:
            log(f"    NO DATA for this combination")

    # ── Verdict ──────────────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("VERDICT")
    log("=" * 65)

    for sweep_type in ["PE_SMALL_SWEEP","CE_SMALL_SWEEP"]:
        group = [s for s in signals if s["type"] == sweep_type]
        with_prem = [s for s in group if s["win_prem"] is not None]
        if not with_prem:
            log(f"\n  {sweep_type}: NO DATA")
            continue

        pw    = sum(1 for s in with_prem if s["win_prem"])
        wrate = wr(pw, len(with_prem))
        n     = len(with_prem)

        # Spot WR
        with_spot = [s for s in group if s["win_spot"] is not None]
        spot_wr   = wr(sum(1 for s in with_spot if s["win_spot"]), len(with_spot))

        log(f"\n  {sweep_type}:")
        log(f"    Premium WR: {wrate:.1f}% (N={n})")
        log(f"    Spot WR:    {spot_wr:.1f}% (N={len(with_spot)})")

        if wrate >= 65 and n >= 20:
            log(f"  -> STRONG EDGE in premium space")
            log(f"     Build premium sweep detector in signal pipeline")
            if spot_wr >= 60:
                log(f"     BONUS: Also predicts spot direction ({spot_wr:.1f}% spot WR)")
                log(f"     -> Premium small sweep = leading indicator for spot")
            else:
                log(f"     Premium-only signal — trade premium directly")
        elif wrate >= 58 and n >= 10:
            log(f"  -> MODERATE EDGE — shadow test with live data")
        elif n < 15:
            log(f"  -> INSUFFICIENT DATA (N={n}) — need more sessions")
        else:
            log(f"  -> WEAK/NO EDGE ({wrate:.1f}%)")
            log(f"     Small sweep refinement did not improve over Exp 27")

    log("\n  Note: Premium sweep is independent of spot ICT zones.")
    log("  If edge confirmed, this becomes ENH-57: Premium Sweep Detector")
    log("  Signal: ATM PE small sweep (0.2-2%) + close back = BUY_CE")
    log("\nExperiment 27b complete.")


if __name__ == "__main__":
    main()
