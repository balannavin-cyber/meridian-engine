"""
td056_regime_partition_v1.py  --  Session 16 item 6 (+ Exp 15/16 stress test)

TD-056  --  Bull-skew investigation by ret_session sign partition
                 PLUS Exp 15/16 BEAR_OB / BULL_OB headline stress test

Two questions, one script
-------------------------

Q1 (TD-056 closure):
  Is the bull-skew in hist_pattern_signals (NIFTY 1.83x BULL/BEAR FVG ratio,
  SENSEX 1.26x) regime-driven (correct behaviour: detector finds more bullish
  patterns in up-sessions) or detector-driven (asymmetry independent of
  market regime)?

  Method:
    - Partition all FVG signals (60d) by ret_session sign:
        DOWN  : ret_session < -0.05%
        FLAT  : -0.05% <= ret_session <= +0.05%
        UP    : ret_session > +0.05%
    - Compute BULL_FVG / BEAR_FVG count in each bucket per symbol.
    - DECISION:
        Ratio inverts (BULL > BEAR in UP, BEAR > BULL in DOWN)
            -> regime-driven, close TD-056 as correct behaviour.
        Ratio stays bull-skewed (BULL > BEAR in BOTH UP and DOWN)
            -> detector-driven, file follow-up TD with diagnosis.

Q2 (Exp 15/16 stress test):
  Does the spot-side WR for BEAR_OB and BULL_OB on the now-symmetric
  hist_pattern_signals data replicate Exp 15's headline numbers (BEAR_OB
  N=36 94.4% WR, BULL_OB N=44 86.4% WR), or has the magnitude collapsed
  on cleaner methodology?

  Method:
    - Same Exp 41 v2 mechanics: locally-computed T+30m forward return
      from hist_spot_bars_5m, era-aware Rule 20 timestamp handling.
    - For BULL_OB: win = ret_pct > 0 (price up).
    - For BEAR_OB: win = ret_pct < 0 (price down).
    - Pooled WR + per-regime WR (DOWN/FLAT/UP) per symbol per direction.

  Decision rule (qualitative):
    Pooled WR within ~5pp of Exp 15 number       -> headline survives, option
                                                    audit (Check B) still
                                                    needed but spot signal
                                                    is real at magnitude.
    Pooled WR 60-70%                             -> signal real, magnitude
                                                    inflated by N or option
                                                    overlay. File audit TD.
    Pooled WR <60%                               -> headline collapses. The
                                                    Exp 15 numbers were
                                                    small-N artefact or
                                                    option-side phenomenon.

  In all three cases, regime split shows whether the result is
  regime-dependent.

Window: last 60 trading days (matches TD-056 carry-forward scope).

Author: Session 16, item 6.
"""

from __future__ import annotations

import os
import sys
import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean, median

from dotenv import load_dotenv
from supabase import create_client


# --- Constants ---------------------------------------------------------------
PAGE_SIZE = 1000
LOOKBACK_TRADING_DAYS = 60
SYMBOLS = ["NIFTY", "SENSEX"]

# ENH-44 alignment threshold (per merdian_reference.json L2502)
RET_SESSION_FLAT_PCT = 0.05  # |ret_session| <= 0.05% -> FLAT regime

PATTERNS = ["BULL_FVG", "BEAR_FVG", "BULL_OB", "BEAR_OB"]

# Exp 15 headline numbers for stress-test comparison
EXP15_HEADLINE = {
    "BEAR_OB": {"N": 36, "WR_pct": 94.4},
    "BULL_OB": {"N": 44, "WR_pct": 86.4},
}


# --- Rule 20 era-aware helpers -----------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))
ERA_BOUNDARY = "2026-04-07"


def to_ist_naive(ts_aware, trade_date_str):
    if trade_date_str < ERA_BOUNDARY:
        return ts_aware.replace(tzinfo=None)
    return ts_aware.astimezone(IST).replace(tzinfo=None)


def parse_ts(s):
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    if isinstance(s, str):
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        sys.exit("Missing SUPABASE_URL or SUPABASE_*_KEY in .env")
    return create_client(url, key)


def fetch_all(qb, page=PAGE_SIZE, hard_cap=200_000):
    rows, start = [], 0
    while True:
        chunk = qb.range(start, start + page - 1).execute().data or []
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        start += page
        if start > hard_cap:
            return rows


# --- Date window discovery ---------------------------------------------------
def fetch_recent_trading_dates(sb, symbol, n):
    rows = fetch_all(
        sb.table("hist_spot_bars_5m")
          .select("trade_date")
          .eq("symbol", symbol)
          .order("trade_date", desc=True)
          .limit(n * 100)
    )
    seen, out = set(), []
    for r in rows:
        td = r.get("trade_date")
        if td and td not in seen:
            seen.add(td)
            out.append(td)
            if len(out) == n:
                break
    return sorted(out)  # ascending so we have date_min..date_max


# --- Signal + bar fetch ------------------------------------------------------
def fetch_signals(sb, pattern_types, date_min, date_max):
    rows = []
    offset = 0
    while True:
        r = (sb.table("hist_pattern_signals").select("*")
             .in_("pattern_type", pattern_types)
             .gte("trade_date", date_min)
             .lte("trade_date", date_max)
             .order("bar_ts")
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 200_000:
            break
    return rows


def enrich_with_local_t30m(sb, sigs, symbols, date_min, date_max):
    """Mutates sigs: sets r['computed_ret_30m_pct'] when computable."""
    print(f"[INFO] loading 5m bars per symbol ...")
    bars_by_sym_date = {}
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
            bars_by_sym_date.setdefault((sym, b["trade_date"]), []).append(
                (ist, float(b["close"]))
            )
        n_bars = sum(len(v) for k, v in bars_by_sym_date.items() if k[0] == sym)
        n_days = sum(1 for k in bars_by_sym_date if k[0] == sym)
        print(f"[INFO]   {sym}: {n_bars} bars across {n_days} days")

    n_e = n_nm = n_eos = n_gap = 0
    for r in sigs:
        sym = r.get("symbol")
        td = r.get("trade_date")
        bar_ts_str = r.get("bar_ts")
        if not (sym and td and bar_ts_str):
            n_nm += 1
            continue
        day_bars = bars_by_sym_date.get((sym, td), [])
        if not day_bars:
            n_nm += 1
            continue
        sig_ist = to_ist_naive(parse_ts(bar_ts_str), td)
        idx = None
        for i, (b_ist, _) in enumerate(day_bars):
            if b_ist == sig_ist:
                idx = i
                break
        if idx is None:
            n_nm += 1
            continue
        t30 = idx + 6
        if t30 >= len(day_bars):
            n_eos += 1
            continue
        if day_bars[t30][0] != sig_ist + timedelta(minutes=30):
            n_gap += 1
            continue
        entry = day_bars[idx][1]
        exit_ = day_bars[t30][1]
        r["computed_ret_30m_pct"] = (exit_ - entry) / entry * 100.0
        n_e += 1
    return n_e, n_nm, n_eos, n_gap


# --- Regime classification ---------------------------------------------------
def regime_of(ret_session_pct):
    """Classify a signal by ret_session sign with FLAT band per ENH-44."""
    if ret_session_pct is None:
        return None
    try:
        v = float(ret_session_pct)
    except (TypeError, ValueError):
        return None
    if v > RET_SESSION_FLAT_PCT:
        return "UP"
    if v < -RET_SESSION_FLAT_PCT:
        return "DOWN"
    return "FLAT"


# --- WR / EV computation -----------------------------------------------------
def compute_wr_ev(rows, intent):
    """intent = +1 for BULL win definition (ret > 0), -1 for BEAR (ret < 0)."""
    n = wins = 0
    rets = []
    for r in rows:
        rp = r.get("computed_ret_30m_pct")
        if rp is None:
            continue
        n += 1
        rets.append(rp)
        if rp * intent > 0:
            wins += 1
    if n == 0:
        return {"n": 0, "wr": 0.0, "ev": 0.0, "mean": 0.0, "median": 0.0}
    return {
        "n": n,
        "wr": wins / n * 100.0,
        "ev": (sum(rets) / n) * intent,
        "mean": sum(rets) / n,
        "median": sorted(rets)[len(rets) // 2],
    }


# --- Main --------------------------------------------------------------------
def main():
    sb = get_client()

    print("=" * 96)
    print("TD-056 + Exp 15/16 STRESS TEST  --  ret_session regime partition")
    print(f"Run at: {datetime.now(IST).isoformat(timespec='seconds')}")
    print("=" * 96)
    print(f"Window           : last {LOOKBACK_TRADING_DAYS} trading days per symbol")
    print(f"FLAT band        : |ret_session| <= {RET_SESSION_FLAT_PCT}% (per ENH-44)")
    print(f"Patterns         : {', '.join(PATTERNS)}")
    print(f"Outcome metric   : locally-computed T+30m return (Rule 20)")
    print()

    # Determine common date window (intersection of both symbols)
    date_windows = {}
    for sym in SYMBOLS:
        dates = fetch_recent_trading_dates(sb, sym, LOOKBACK_TRADING_DAYS)
        date_windows[sym] = dates
        print(f"[INFO] {sym}: {len(dates)} trading days, "
              f"{dates[0] if dates else 'n/a'} -> {dates[-1] if dates else 'n/a'}")
    if not all(date_windows[s] for s in SYMBOLS):
        sys.exit("[FATAL] missing dates for one or more symbols.")
    date_min = min(date_windows[s][0] for s in SYMBOLS)
    date_max = max(date_windows[s][-1] for s in SYMBOLS)
    print(f"[INFO] combined window: {date_min} -> {date_max}")
    print()

    # Fetch signals
    print(f"[INFO] fetching signals for patterns {PATTERNS} ...")
    sigs = fetch_signals(sb, PATTERNS, date_min, date_max)
    print(f"[INFO] fetched {len(sigs)} rows")
    by_pat = defaultdict(int)
    for s in sigs:
        by_pat[s.get("pattern_type")] += 1
    for p in PATTERNS:
        print(f"[INFO]   {p}: {by_pat[p]}")
    print()

    # Filter sigs to common symbols
    sigs = [s for s in sigs if s.get("symbol") in SYMBOLS]

    # Enrich with locally-computed T+30m forward return
    n_e, n_nm, n_eos, n_gap = enrich_with_local_t30m(sb, sigs, SYMBOLS, date_min, date_max)
    print(f"[INFO] enrichment: {n_e} enriched, {n_nm} no-match, "
          f"{n_eos} eos-skipped, {n_gap} bar-gap-skipped")
    print()

    # Classify regime per signal
    n_no_regime = 0
    for s in sigs:
        r = regime_of(s.get("ret_session"))
        s["_regime"] = r
        if r is None:
            n_no_regime += 1
    print(f"[INFO] {n_no_regime} signals have NULL ret_session (excluded from regime split)")
    print()

    # ============================================================
    # Q1: TD-056 -- BULL_FVG vs BEAR_FVG count by regime per symbol
    # ============================================================
    print("=" * 96)
    print("Q1: TD-056 BULL_FVG vs BEAR_FVG count by ret_session regime")
    print("=" * 96)
    print()
    print(f"{'Symbol':<8} {'Regime':<6} {'BULL_FVG':>10} {'BEAR_FVG':>10} "
          f"{'Ratio (B/Be)':>14} {'Verdict':<24}")
    print("-" * 96)

    td056_rows = []
    for sym in SYMBOLS:
        for regime in ("UP", "FLAT", "DOWN"):
            bull_n = sum(1 for s in sigs
                         if s["symbol"] == sym
                         and s.get("pattern_type") == "BULL_FVG"
                         and s["_regime"] == regime)
            bear_n = sum(1 for s in sigs
                         if s["symbol"] == sym
                         and s.get("pattern_type") == "BEAR_FVG"
                         and s["_regime"] == regime)
            if bear_n == 0:
                ratio_str = f"{bull_n}:0 (inf)" if bull_n > 0 else "0:0"
            else:
                ratio = bull_n / bear_n
                ratio_str = f"{ratio:.2f}x"
            # Per-row interpretation
            if regime == "UP" and bull_n > bear_n:
                verdict = "OK (bull regime)"
            elif regime == "DOWN" and bear_n > bull_n:
                verdict = "OK (bear regime)"
            elif regime == "DOWN" and bull_n > bear_n:
                verdict = "ANOMALY (bull-skew in DOWN)"
            elif regime == "UP" and bear_n > bull_n:
                verdict = "ANOMALY (bear-skew in UP)"
            else:
                verdict = "(flat / unclear)"
            print(f"{sym:<8} {regime:<6} {bull_n:>10} {bear_n:>10} "
                  f"{ratio_str:>14} {verdict:<24}")
            td056_rows.append({
                "symbol": sym, "regime": regime,
                "bull_fvg": bull_n, "bear_fvg": bear_n,
            })
        print()

    # TD-056 verdict
    print("=" * 96)
    print("TD-056 VERDICT")
    print("=" * 96)
    verdicts = {}
    for sym in SYMBOLS:
        up = next((r for r in td056_rows if r["symbol"] == sym and r["regime"] == "UP"), None)
        down = next((r for r in td056_rows if r["symbol"] == sym and r["regime"] == "DOWN"), None)
        if up and down:
            up_inv = up["bull_fvg"] > up["bear_fvg"]
            down_inv = down["bear_fvg"] > down["bull_fvg"]
            if up_inv and down_inv:
                v = "REGIME-DRIVEN (correct) -- close TD-056"
            elif up_inv and not down_inv:
                v = ("PARTIAL ANOMALY -- bull-skew in DOWN regime; "
                     "file follow-up TD")
            elif not up_inv and down_inv:
                v = "INVERSE ANOMALY (bear-skew in UP) -- file follow-up TD"
            else:
                v = "BIDIRECTIONAL ANOMALY -- file follow-up TD"
            verdicts[sym] = v
        else:
            verdicts[sym] = "INSUFFICIENT DATA"
        print(f"  {sym}: {verdicts[sym]}")
    print()

    # ============================================================
    # Q2: Exp 15/16 stress test -- BULL_OB / BEAR_OB WR by regime
    # ============================================================
    print("=" * 96)
    print("Q2: Exp 15/16 STRESS TEST  --  BULL_OB / BEAR_OB WR by regime")
    print("=" * 96)
    print()
    print("Exp 15 headline:")
    for p, h in EXP15_HEADLINE.items():
        print(f"  {p}: N={h['N']}, WR={h['WR_pct']}% (option-PnL based)")
    print()
    print("This stress test computes spot-side T+30m WR on the same patterns")
    print("over the last 60 trading days, partitioned by ret_session regime.")
    print()

    for direction_pat, intent in (("BULL_OB", +1), ("BEAR_OB", -1)):
        print(f"--- {direction_pat} (win = ret * {intent:+d} > 0) ---")
        # Pooled
        rows = [s for s in sigs if s.get("pattern_type") == direction_pat]
        m = compute_wr_ev(rows, intent)
        print(f"  POOLED: N={m['n']:>4}  WR={m['wr']:>5.1f}%  "
              f"mean ret={m['mean']:+.3f}%  median={m['median']:+.3f}%  "
              f"EV(intent)={m['ev']:+.3f}%")
        # Per symbol
        for sym in SYMBOLS:
            rs = [s for s in rows if s["symbol"] == sym]
            ms = compute_wr_ev(rs, intent)
            print(f"  {sym:<8}: N={ms['n']:>4}  WR={ms['wr']:>5.1f}%  "
                  f"mean ret={ms['mean']:+.3f}%  EV(intent)={ms['ev']:+.3f}%")
        # By regime (pooled symbols)
        for regime in ("UP", "FLAT", "DOWN"):
            rr = [s for s in rows if s["_regime"] == regime]
            mr = compute_wr_ev(rr, intent)
            print(f"  {regime:<6}  : N={mr['n']:>4}  WR={mr['wr']:>5.1f}%  "
                  f"mean ret={mr['mean']:+.3f}%  EV(intent)={mr['ev']:+.3f}%")
        # Stress-test verdict
        exp15_wr = EXP15_HEADLINE[direction_pat]["WR_pct"]
        delta_pp = m['wr'] - exp15_wr
        if abs(delta_pp) < 5:
            stress_verdict = "HEADLINE SURVIVES (within 5pp)"
        elif m['wr'] >= 60:
            stress_verdict = ("MAGNITUDE DEFLATED -- signal real, "
                              "Exp 15 number inflated; option audit owed")
        else:
            stress_verdict = ("HEADLINE COLLAPSES -- spot signal near-noise; "
                              "Exp 15 numbers must have been option-overlay or "
                              "small-N artefacts")
        print(f"  Exp 15 delta : {delta_pp:+.1f}pp -- {stress_verdict}")
        print()

    # ============================================================
    # Q1+Q2 cross-link: BULL_FVG/BEAR_FVG WR by regime, for completeness
    # ============================================================
    print("=" * 96)
    print("CROSS-LINK: BULL_FVG / BEAR_FVG WR by regime (Item 1 carry-forward refresh)")
    print("=" * 96)
    print()
    for direction_pat, intent in (("BULL_FVG", +1), ("BEAR_FVG", -1)):
        print(f"--- {direction_pat} (win = ret * {intent:+d} > 0) ---")
        rows = [s for s in sigs if s.get("pattern_type") == direction_pat]
        m = compute_wr_ev(rows, intent)
        print(f"  POOLED  : N={m['n']:>4}  WR={m['wr']:>5.1f}%  "
              f"mean={m['mean']:+.3f}%  EV(intent)={m['ev']:+.3f}%")
        for regime in ("UP", "FLAT", "DOWN"):
            rr = [s for s in rows if s["_regime"] == regime]
            mr = compute_wr_ev(rr, intent)
            print(f"  {regime:<6}  : N={mr['n']:>4}  WR={mr['wr']:>5.1f}%  "
                  f"mean={mr['mean']:+.3f}%  EV(intent)={mr['ev']:+.3f}%")
        print()

    # ============================================================
    # CSV dump
    # ============================================================
    stamp = datetime.now(IST).strftime("%Y%m%d_%H%M")
    csv_path = f"td056_regime_partition_{stamp}.csv"
    fields = ["id", "symbol", "trade_date", "bar_ts", "pattern_type",
              "direction", "ret_session", "_regime", "computed_ret_30m_pct"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sigs:
            w.writerow(r)
    print(f"Cohort CSV: {csv_path}  ({len(sigs)} rows)")
    print()

    print("=" * 96)
    print("SESSION 16 ITEM 6 + STRESS TEST  --  end")
    print("=" * 96)


if __name__ == "__main__":
    main()
