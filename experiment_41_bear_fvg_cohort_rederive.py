"""
Exp 41/41b BEAR_FVG cohort re-derive  --  Session 16, item 1
============================================================

Purpose
-------
Compute N, WR, mean/median return, and expectancy for BEAR_FVG signals on the
now-populated `hist_pattern_signals` table (post Session 15 fix that took
BEAR_FVG count from 0 to 795). This is the empirical baseline for the stash
adjudication (Session 16 item 2).

Original stash claim (per fix_bear_fvg_detection.py docstring, Session 15):
    N = 225, WR = 11.5%, expectancy = -30.7%
    -> rationale for stashing BEAR_FVG-as-SKIP routing in build_trade_signal_local.py

This script re-derives on the now-symmetric data and prints a side-by-side
adjudication preview at the bottom.

Rule 20 compliance
------------------
Era boundary 2026-04-07. Pre-boundary: bar_ts.replace(tzinfo=None).
Post-boundary: bar_ts.astimezone(IST).replace(tzinfo=None). Both yield
IST-naive datetimes that are mutually comparable for index lookup.

Forward return is computed locally from hist_spot_bars_5m (do NOT trust
ret_30m blindly -- we cross-check it). Per Session 11 ret_30m_scale_warning,
the column is stored as percentage points (0.1351 = 0.1351%), so it should
agree with our locally-computed ret_pct directly.

Outcome metric
--------------
For BEAR_FVG, the "win" condition is bearish-bias materialisation:
    win_short = T+30m close < signal-bar close  (i.e. ret_pct < 0)

Mean / median forward return reported in %. EV reported both signed
(price-side) and short-flipped (bearish-bias EV = -mean).

Output
------
Stdout, paste-back friendly. Also writes a CSV cohort dump to
exp41_bear_fvg_cohort_<timestamp>.csv for inspection.
"""

from __future__ import annotations
import os
import sys
import csv
from datetime import datetime, timezone, timedelta
from statistics import mean, median
from supabase import create_client
from dotenv import load_dotenv

# --- Rule 20 era-aware helper -------------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))
ERA_BOUNDARY = "2026-04-07"  # exclusive: < uses Rule 16; >= uses astimezone(IST)


def to_ist_naive(ts_aware, trade_date_str):
    """Convert a stored aware datetime to IST-naive, era-correct per Rule 20."""
    if trade_date_str < ERA_BOUNDARY:
        return ts_aware.replace(tzinfo=None)                  # Rule 16 (legacy)
    return ts_aware.astimezone(IST).replace(tzinfo=None)      # post-04-07 (true UTC)


def parse_ts(s):
    """Parse ISO-8601 timestamp string; tolerate trailing 'Z'."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


# --- Supabase pagination (Bug B2 / Rule 11: 1000-row cap) ---------------------
def fetch_all(qb, page=1000):
    rows, start = [], 0
    while True:
        chunk = qb.range(start, start + page - 1).execute().data
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        start += page


# --- Main ---------------------------------------------------------------------
def main():
    load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
    )
    if not url or not key:
        sys.exit("Missing SUPABASE_URL or SUPABASE_*_KEY in .env")
    sb = create_client(url, key)

    print("=" * 72)
    print("EXP 41/41b BEAR_FVG cohort re-derive  --  Session 16 item 1")
    print(f"Run at: {datetime.now(IST).isoformat(timespec='seconds')}")
    print("=" * 72)

    # 1) Pull all BEAR_FVG signals
    print("\n[1/3] Pulling BEAR_FVG signals from hist_pattern_signals ...")
    sigs = fetch_all(
        sb.table("hist_pattern_signals")
          .select("id, symbol, bar_ts, trade_date, ret_30m, win_30m, direction, pattern_type")
          .eq("pattern_type", "BEAR_FVG")
          .order("bar_ts")
    )
    print(f"      -> {len(sigs)} BEAR_FVG signals pulled")
    if not sigs:
        sys.exit("ERROR: no BEAR_FVG signals -- Session 15 patches may not have landed.")

    # Direction sanity: BEAR_FVG should be BUY_PE
    dir_counts = {}
    for s in sigs:
        d = s.get("direction") or "NULL"
        dir_counts[d] = dir_counts.get(d, 0) + 1
    print(f"      direction distribution: {dir_counts}")
    if dir_counts.get("BUY_CE", 0) > 0:
        print(f"      WARN: {dir_counts['BUY_CE']} BEAR_FVG rows have direction=BUY_CE (data inconsistency)")

    symbols = sorted({s["symbol"] for s in sigs})
    date_min = min(s["trade_date"] for s in sigs)
    date_max = max(s["trade_date"] for s in sigs)
    print(f"      symbols    : {symbols}")
    print(f"      date range : {date_min} -> {date_max}")

    # 2) Load all 5m bars in [date_min, date_max] per symbol, build per-day arrays
    print("\n[2/3] Loading hist_spot_bars_5m bars per symbol ...")
    bars_by_sym_date = {}  # (symbol, trade_date) -> [(ist_naive_dt, close), ...]
    for sym in symbols:
        bars = fetch_all(
            sb.table("hist_spot_bars_5m")
              .select("bar_ts, close, trade_date")
              .eq("symbol", sym)
              .gte("trade_date", date_min)
              .lte("trade_date", date_max)
              .order("bar_ts")
        )
        for b in bars:
            ts_aware = parse_ts(b["bar_ts"])
            ist = to_ist_naive(ts_aware, b["trade_date"])
            bars_by_sym_date.setdefault((sym, b["trade_date"]), []).append((ist, float(b["close"])))
        n_bars = sum(len(v) for k, v in bars_by_sym_date.items() if k[0] == sym)
        n_days = sum(1 for k in bars_by_sym_date if k[0] == sym)
        print(f"      {sym}: {n_bars} bars across {n_days} days")

    # 3) Per signal: locate sig_ts in its day's bar list, take +6 close (T+30m)
    print("\n[3/3] Computing T+30m forward returns ...")
    cohort = []
    skipped_no_match = 0       # sig_ts not found in day bars
    skipped_no_t30 = 0         # +6 crosses session end
    skipped_bar_gap = 0        # +6 timestamp != sig_ts + 30min (bar gap)

    for s in sigs:
        key = (s["symbol"], s["trade_date"])
        day_bars = bars_by_sym_date.get(key, [])
        if not day_bars:
            skipped_no_match += 1
            continue

        sig_ist = to_ist_naive(parse_ts(s["bar_ts"]), s["trade_date"])

        idx = None
        for i, (b_ist, _) in enumerate(day_bars):
            if b_ist == sig_ist:
                idx = i
                break
        if idx is None:
            skipped_no_match += 1
            continue

        t30 = idx + 6
        if t30 >= len(day_bars):
            skipped_no_t30 += 1
            continue

        # Verify +6 by index actually corresponds to +30min (no missing bars)
        expected = sig_ist + timedelta(minutes=30)
        if day_bars[t30][0] != expected:
            skipped_bar_gap += 1
            continue

        entry = day_bars[idx][1]
        exit_ = day_bars[t30][1]
        ret_pct = (exit_ - entry) / entry * 100.0

        cohort.append({
            "symbol": s["symbol"],
            "trade_date": s["trade_date"],
            "bar_ts": s["bar_ts"],
            "direction": s.get("direction"),
            "entry": entry,
            "exit": exit_,
            "ret_pct": ret_pct,
            "table_ret_pct": float(s["ret_30m"]) if s.get("ret_30m") is not None else None,
            "table_win_30m": s.get("win_30m"),
            "win_short": ret_pct < 0,
        })

    print(f"      -> {len(cohort)} signals enriched")
    print(f"      -> {skipped_no_match} skipped (no bar match for sig_ts)")
    print(f"      -> {skipped_no_t30} skipped (T+30m crosses session end)")
    print(f"      -> {skipped_bar_gap} skipped (bar gap inside +30m window)")

    if not cohort:
        sys.exit("ERROR: no usable signals after enrichment.")

    # ---- Stats ---------------------------------------------------------------
    def report(rows, label):
        if not rows:
            print(f"\n{label}: N=0")
            return
        n = len(rows)
        wins = sum(1 for r in rows if r["win_short"])
        wr = wins / n * 100
        rets = [r["ret_pct"] for r in rows]
        m, med = mean(rets), median(rets)
        ev_short = -m
        # cross-check vs ret_30m column
        cc = [(r["ret_pct"], r["table_ret_pct"]) for r in rows if r["table_ret_pct"] is not None]
        if cc:
            agree = sum(1 for c, t in cc if abs(c - t) < 0.01)
            cc_str = f"{agree}/{len(cc)} ({agree/len(cc)*100:.1f}%) within 1bp"
        else:
            cc_str = "n/a (column null)"
        # cross-check vs win_30m column
        wc = [(r["win_short"], r["table_win_30m"]) for r in rows if r["table_win_30m"] is not None]
        if wc:
            wagree = sum(1 for c, t in wc if c == t)
            wc_str = f"{wagree}/{len(wc)} ({wagree/len(wc)*100:.1f}%) match"
        else:
            wc_str = "n/a (column null)"
        print(f"\n{label}")
        print(f"  N                = {n}")
        print(f"  WR (price down)  = {wr:.1f}%   (wins={wins})")
        print(f"  mean ret         = {m:+.3f}%")
        print(f"  median ret       = {med:+.3f}%")
        print(f"  EV (short-bias)  = {ev_short:+.3f}%   (= -mean ret)")
        print(f"  ret_30m agree    = {cc_str}")
        print(f"  win_30m agree    = {wc_str}")

    print("\n" + "=" * 72)
    print("RESULTS")
    print("=" * 72)
    report(cohort, "POOLED (all symbols, full date range)")
    for sym in symbols:
        report([r for r in cohort if r["symbol"] == sym], f"PER-SYMBOL: {sym}")

    # Recent 60d cut, in case the original stash claim was on a recency window
    cutoff = sorted({r["trade_date"] for r in cohort})[-60:][0] if len({r["trade_date"] for r in cohort}) >= 60 else None
    if cutoff:
        recent = [r for r in cohort if r["trade_date"] >= cutoff]
        report(recent, f"RECENT 60 trading days (>= {cutoff})")

    # ---- CSV dump ------------------------------------------------------------
    stamp = datetime.now(IST).strftime("%Y%m%d_%H%M")
    csv_path = f"exp41_bear_fvg_cohort_{stamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cohort[0].keys()))
        w.writeheader()
        for r in cohort:
            w.writerow(r)
    print(f"\nCohort CSV: {csv_path}  ({len(cohort)} rows)")

    # ---- Stash adjudication preview -----------------------------------------
    n = len(cohort)
    wins = sum(1 for r in cohort if r["win_short"])
    wr = wins / n * 100
    ev = -mean(r["ret_pct"] for r in cohort)
    print("\n" + "=" * 72)
    print("STASH ADJUDICATION PREVIEW (Session 16 item 2)")
    print("=" * 72)
    print("Original stash claim (fix_bear_fvg_detection.py docstring):")
    print("  N = 225,  WR = 11.5%,  expectancy = -30.7%")
    print()
    print("Re-derive on post-S15 bidirectional data (this script):")
    print(f"  N = {n},  WR(price down) = {wr:.1f}%,  EV(short-bias) = {ev:+.3f}%")
    print()
    print("Notes for adjudicator:")
    print("  1. Stash 'expectancy = -30.7%' unit unclear (price-side vs option-PnL).")
    print("     This script reports price-side EV in %. If the stash claim was on")
    print("     option-PnL terms, comparison must adjust for premium decay/delta.")
    print("  2. N disparity (225 vs ~795) reflects Session 15 BEAR_FVG fix.")
    print("     The original 225 was computed on whatever leaked through the")
    print("     pre-fix detector path; the 795 is the now-symmetric cohort.")
    print("  3. Decision rule per Session 16 prompt:")
    print("     WR within ~5pp of 11.5%  AND  EV directionally consistent")
    print("       -> ship stash with ADR-004 commit")
    print("     Otherwise -> drop stash, document in tech_debt.md as adjudication note.")


if __name__ == "__main__":
    main()
