"""
experiment_44_inverted_hammer_cascade.py

EXPERIMENT 44 — Intraday Inverted Hammer Reversal After Cascade

Question:
    Does an inverted hammer after a sustained intraday cascade, followed by a
    non-violating range test, predict a reversal large enough to be tradeable
    at T+30m / T+60m / EOD? Run both the bearish-cascade (long-side reversal)
    AND bullish-cascade mirror (short-side reversal) sides separately.

Bearish-side hypothesis (long entry):
    1. Spot drops >= X% from session open within last N bars.
    2. Candle K is inverted hammer:
         - high-wick >= 2 * body
         - body in lower 1/3 of bar range
         - close near low (close within 25% of low)
    3. Candle K+1 retests range of K (touches near K's low) but does NOT close
       below K's low.
    4. Entry at K+2 open. Measure T+30m, T+60m, EOD return.

Bullish-side hypothesis (short entry — MIRROR):
    1. Spot rises >= X% from session open within last N bars.
    2. Candle K is bearish-hammer/shooting-star:
         - low-wick >= 2 * body
         - body in upper 1/3 of bar range
         - close near high (close within 25% of high)
    3. Candle K+1 retests range of K (touches near K's high) but does NOT close
       above K's high.
    4. Entry at K+2 open. Measure T+30m, T+60m, EOD return.

Sweep:
    X (cascade magnitude): {0.3%, 0.5%, 0.7%, 1.0%}
    N (lookback bars):     {10, 15, 20}

Data source:
    hist_spot_bars_5m, NIFTY + SENSEX, 12 months, IST 09:15-15:30 in-session.

Rules applied:
    Rule 15: page_size=1000.
    Rule 16: replace(tzinfo=None) on bar_ts.
    Bug B4: no is_pre_market column - filter by time.

PASS criterion:
    WR >= 70% AND N >= 30 events per side per symbol.
    Compare against existing edges: BEAR_OB MIDDAY+PO3 (88.2% N=17), E1 PDH
    first-sweep (93.3% N=15) — must beat baseline.

Forbidden ground:
    Do NOT cherry-pick threshold values - report the full sweep.
    Do NOT mix bearish + bullish samples - independent hypotheses.

Author: Session 15 batch.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time, date as date_t

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000
START_DATE = "2025-04-01"
END_DATE = "2026-04-30"
SYMBOLS = ["NIFTY", "SENSEX"]
CASCADE_PCTS = [0.3, 0.5, 0.7, 1.0]
LOOKBACK_BARS = [10, 15, 20]
WICK_BODY_RATIO = 2.0
BODY_FRACTION = 1.0 / 3.0
CLOSE_NEAR_FRAC = 0.25  # close within 25% of high (or low) of bar
RETEST_TOL_FRAC = 0.10  # K+1 must touch within this fraction of K range


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_5m_bars(sb, symbol: str, start: str, end: str) -> list[dict]:
    """All 5m bars for symbol between dates. Apply Rule 16 + in-session filter."""
    out: list[dict] = []
    offset = 0
    while True:
        r = (sb.table("hist_spot_bars_5m")
             .select("bar_ts, open, high, low, close, symbol")
             .eq("symbol", symbol)
             .gte("bar_ts", f"{start}T00:00:00+00:00")
             .lte("bar_ts", f"{end}T23:59:59+00:00")
             .order("bar_ts")
             .range(offset, offset + PAGE_SIZE - 1)
             .execute())
        batch = r.data or []
        if not batch:
            break
        out.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 500_000:
            print(f"[WARN] safety break at {offset}", file=sys.stderr)
            break
    # Rule 16 + in-session
    cleaned = []
    for b in out:
        try:
            dt = datetime.fromisoformat(b["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            continue
        t = dt.time()
        if not (dt_time(9, 15) <= t <= dt_time(15, 30)):
            continue
        b["_dt"] = dt
        try:
            b["open"] = float(b["open"])
            b["high"] = float(b["high"])
            b["low"] = float(b["low"])
            b["close"] = float(b["close"])
        except (TypeError, ValueError):
            continue
        cleaned.append(b)
    return cleaned


def group_by_session(bars: list[dict]) -> dict[date_t, list[dict]]:
    g: dict[date_t, list[dict]] = defaultdict(list)
    for b in bars:
        g[b["_dt"].date()].append(b)
    for k in g:
        g[k].sort(key=lambda x: x["_dt"])
    return g


def is_inverted_hammer(b: dict) -> bool:
    """Body in lower 1/3, high wick >= 2*body, close near low."""
    rng = b["high"] - b["low"]
    if rng <= 0:
        return False
    body = abs(b["close"] - b["open"])
    if body <= 0:
        body = rng * 0.01  # treat doji-ish as tiny body to allow wick math
    body_top = max(b["open"], b["close"])
    body_bottom = min(b["open"], b["close"])
    upper_wick = b["high"] - body_top
    if upper_wick < WICK_BODY_RATIO * body:
        return False
    # Body in lower 1/3
    if body_top > b["low"] + rng * BODY_FRACTION:
        return False
    # Close near low
    if (b["close"] - b["low"]) > rng * CLOSE_NEAR_FRAC:
        return False
    return True


def is_shooting_star(b: dict) -> bool:
    """Mirror: body in upper 1/3, low wick >= 2*body, close near high."""
    rng = b["high"] - b["low"]
    if rng <= 0:
        return False
    body = abs(b["close"] - b["open"])
    if body <= 0:
        body = rng * 0.01
    body_top = max(b["open"], b["close"])
    body_bottom = min(b["open"], b["close"])
    lower_wick = body_bottom - b["low"]
    if lower_wick < WICK_BODY_RATIO * body:
        return False
    # Body in upper 1/3
    if body_bottom < b["high"] - rng * BODY_FRACTION:
        return False
    # Close near high
    if (b["high"] - b["close"]) > rng * CLOSE_NEAR_FRAC:
        return False
    return True


def find_setups_in_session(session_bars: list[dict], cascade_pct: float, lookback: int):
    """Yield (k_idx, side, entry_idx, k_bar, k1_bar, k2_bar) tuples for the session."""
    # Need at least lookback + 3 bars
    if len(session_bars) < lookback + 3:
        return
    open_price = session_bars[0]["open"]
    for k in range(lookback, len(session_bars) - 2):
        bar_k = session_bars[k]
        # === Bearish-side (long entry on inverted hammer after cascade DOWN) ===
        # Cascade: low(k) drop from session open exceeds cascade_pct
        drop_pct = (open_price - bar_k["low"]) / open_price * 100
        if drop_pct >= cascade_pct and is_inverted_hammer(bar_k):
            bar_k1 = session_bars[k + 1]
            # Retest within tol of k's low
            tol = (bar_k["high"] - bar_k["low"]) * RETEST_TOL_FRAC
            retest_touched = bar_k1["low"] <= bar_k["low"] + tol
            no_close_below = bar_k1["close"] >= bar_k["low"]
            if retest_touched and no_close_below:
                bar_k2 = session_bars[k + 2]
                yield (k, "BEAR_CASCADE_LONG", k + 2, bar_k, bar_k1, bar_k2)
        # === Bullish-side (short entry on shooting star after cascade UP) ===
        rise_pct = (bar_k["high"] - open_price) / open_price * 100
        if rise_pct >= cascade_pct and is_shooting_star(bar_k):
            bar_k1 = session_bars[k + 1]
            tol = (bar_k["high"] - bar_k["low"]) * RETEST_TOL_FRAC
            retest_touched = bar_k1["high"] >= bar_k["high"] - tol
            no_close_above = bar_k1["close"] <= bar_k["high"]
            if retest_touched and no_close_above:
                bar_k2 = session_bars[k + 2]
                yield (k, "BULL_CASCADE_SHORT", k + 2, bar_k, bar_k1, bar_k2)


def measure_returns(session_bars: list[dict], entry_idx: int, side: str) -> dict:
    """Return T+30m (6 bars), T+60m (12 bars), EOD returns in pct.
    BEAR_CASCADE_LONG: positive = up move (good).
    BULL_CASCADE_SHORT: positive = down move (good).
    """
    entry = session_bars[entry_idx]
    entry_price = entry["open"]
    out = {}
    for label, n_bars in [("ret_30m", 6), ("ret_60m", 12)]:
        target_idx = entry_idx + n_bars
        if target_idx < len(session_bars):
            target_price = session_bars[target_idx]["close"]
        else:
            target_price = session_bars[-1]["close"]
        raw_pct = (target_price - entry_price) / entry_price * 100
        # Sign-align for the side
        signed = raw_pct if side == "BEAR_CASCADE_LONG" else -raw_pct
        out[label] = signed
    eod_close = session_bars[-1]["close"]
    raw_eod = (eod_close - entry_price) / entry_price * 100
    out["ret_eod"] = raw_eod if side == "BEAR_CASCADE_LONG" else -raw_eod
    return out


def main():
    sb = get_client()

    # Header
    print("=" * 76)
    print("EXPERIMENT 44 — INVERTED HAMMER REVERSAL AFTER CASCADE")
    print("=" * 76)
    print(f"Window: {START_DATE} .. {END_DATE}")
    print(f"Cascade thresholds: {CASCADE_PCTS}, Lookbacks: {LOOKBACK_BARS}")
    print()

    # Load bars per symbol once, reuse across sweep
    all_bars_by_symbol: dict[str, dict[date_t, list[dict]]] = {}
    for sym in SYMBOLS:
        print(f"[INFO] fetching {sym} 5m bars ...")
        bars = fetch_5m_bars(sb, sym, START_DATE, END_DATE)
        sessions = group_by_session(bars)
        all_bars_by_symbol[sym] = sessions
        print(f"[INFO] {sym}: {len(bars)} bars across {len(sessions)} sessions")

    # Sweep grid
    print()
    print(f"{'Sym':<8} {'Cascade%':>9} {'Lookback':>9} {'Side':<22} {'N':>5} "
          f"{'WR_30m':>7} {'EV_30m':>7} {'WR_60m':>7} {'EV_60m':>7} "
          f"{'WR_EOD':>7} {'EV_EOD':>7}")
    print("-" * 76)

    summary_rows = []
    for sym in SYMBOLS:
        sessions = all_bars_by_symbol[sym]
        for cas in CASCADE_PCTS:
            for lb in LOOKBACK_BARS:
                # Per (sym, cas, lb): tally per side
                per_side = defaultdict(list)  # side -> list of return dicts
                for sess_date, sb_list in sessions.items():
                    for setup in find_setups_in_session(sb_list, cas, lb):
                        k_idx, side, entry_idx, _, _, _ = setup
                        rets = measure_returns(sb_list, entry_idx, side)
                        per_side[side].append(rets)
                for side in ("BEAR_CASCADE_LONG", "BULL_CASCADE_SHORT"):
                    rs = per_side.get(side, [])
                    n = len(rs)
                    if n == 0:
                        continue
                    wr30 = sum(1 for r in rs if r["ret_30m"] > 0) / n * 100
                    ev30 = sum(r["ret_30m"] for r in rs) / n
                    wr60 = sum(1 for r in rs if r["ret_60m"] > 0) / n * 100
                    ev60 = sum(r["ret_60m"] for r in rs) / n
                    wreod = sum(1 for r in rs if r["ret_eod"] > 0) / n * 100
                    eveod = sum(r["ret_eod"] for r in rs) / n
                    print(f"{sym:<8} {cas:>9.1f} {lb:>9} {side:<22} {n:>5} "
                          f"{wr30:>6.1f}% {ev30:>+6.2f}% {wr60:>6.1f}% {ev60:>+6.2f}% "
                          f"{wreod:>6.1f}% {eveod:>+6.2f}%")
                    summary_rows.append({
                        "sym": sym, "cas": cas, "lb": lb, "side": side,
                        "n": n, "wr30": wr30, "ev30": ev30,
                        "wr60": wr60, "ev60": ev60,
                        "wreod": wreod, "eveod": eveod,
                    })
        print()

    # PASS-criterion check
    print("=" * 76)
    print("PASS-CRITERION CHECK (WR>=70% AND N>=30 at any horizon, per side per symbol)")
    print("=" * 76)
    candidates = []
    for r in summary_rows:
        if r["n"] < 30:
            continue
        for h in ("30m", "60m", "eod"):
            wr = r[f"wr{'30' if h == '30m' else '60' if h == '60m' else 'eod'}"]
            if wr >= 70:
                candidates.append((r, h, wr))
    if not candidates:
        print("No (sym,cas,lb,side,horizon) cell meets WR>=70 AND N>=30. Verdict: FAIL.")
    else:
        for r, h, wr in candidates:
            print(f"  {r['sym']} cascade={r['cas']}% lookback={r['lb']} side={r['side']} "
                  f"horizon={h} N={r['n']} WR={wr:.1f}% EV_eod={r['eveod']:+.2f}%")
        print("Verdict: PASS or MARGINAL. Inspect cells above; ensure not concentrated in one regime.")
    print("=" * 76)


if __name__ == "__main__":
    main()
