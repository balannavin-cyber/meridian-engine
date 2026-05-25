"""
experiment_47b_backwards_anchor.py

EXPERIMENT 47b — Direction Stability via Backwards-Looking Slow Anchor

Why v1 (Exp 47) was invalid:
    Original Exp 47 used `ret_30m` from hist_pattern_signals as both POLICY
    variable and OUTCOME. Per Rule 14, ret_30m is the FORWARD-looking T+30m
    return AFTER signal entry. Using it as policy means we're using future
    data to decide direction -> tautological 100% WR.

The proper test:
    A "slower anchor" must be a BACKWARDS-looking signal -- something we know
    AT SIGNAL TIME. Compute that from hist_spot_bars_5m by walking backwards
    from the signal bar.

Method:
    1. Pull hist_pattern_signals last 12 months (NIFTY+SENSEX).
    2. For each signal, look up the corresponding bar in hist_spot_bars_5m
       at signal_ts. Walk backwards 6 bars (30m) and 12 bars (60m). Compute:
         ret_30m_back = (close[now] - close[6 bars ago]) / close[6 bars ago]
         ret_60m_back = (close[now] - close[12 bars ago]) / close[12 bars ago]
    3. Three policies:
         A: ret_session sign (current ENH-55 V4 anchor; backwards-looking)
         B: ret_30m_back sign (proposed slower anchor)
         C: ret_60m_back sign (proposed slower-still anchor)
    4. Outcome = ret_30m sign from hist_pattern_signals (Rule 14: forward-looking).
    5. For each policy:
         - Same-session direction-flip count
         - Per-pattern WR (rows where policy direction matches pattern intent
           AND ret_30m sign confirms the move)

Decision:
    PASS = policy WR >= ret_session WR within +/-2pp AND >= 30% flip reduction
    Bar coverage caveat: per diagnostic_bar_coverage_audit, recent days may
    have insufficient 5m history. Script counts and reports skipped rows.

Author: Session 15 batch v2.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000
START_DATE = "2025-04-01"
END_DATE = "2026-04-30"


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_pattern_signals(sb, start_date: str, end_date: str):
    rows = []
    offset = 0
    cols = sb.table("hist_pattern_signals").select("*").limit(1).execute().data
    if not cols:
        print("[FATAL] hist_pattern_signals empty?")
        sys.exit(2)
    sample = cols[0]
    ts_col = next((c for c in ("signal_ts", "ts", "entry_ts", "detected_ts", "bar_ts") if c in sample), None)
    if ts_col is None:
        print(f"[FATAL] no ts col in {sorted(sample.keys())}")
        sys.exit(2)
    while True:
        r = (sb.table("hist_pattern_signals").select("*")
             .gte(ts_col, f"{start_date}T00:00:00+00:00")
             .lte(ts_col, f"{end_date}T23:59:59+00:00")
             .order(ts_col)
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 200_000:
            break
    return rows, ts_col


def parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def fetch_5m_bars_window(sb, symbol: str, start_dt: datetime, end_dt: datetime):
    """Fetch 5m bars for symbol in [start_dt, end_dt]. Apply Rule 16."""
    rows = []
    offset = 0
    while True:
        r = (sb.table("hist_spot_bars_5m")
             .select("bar_ts, close")
             .eq("symbol", symbol)
             .gte("bar_ts", start_dt.isoformat())
             .lte("bar_ts", end_dt.isoformat())
             .order("bar_ts")
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 500_000:
            break
    out = []
    for row in rows:
        dt = parse_dt(row["bar_ts"])
        if dt is None:
            continue
        try:
            close = float(row["close"])
        except (TypeError, ValueError):
            continue
        out.append({"dt": dt, "close": close})
    return out


def sign(x):
    if x is None or x == 0:
        return 0
    return 1 if x > 0 else -1


def pattern_intent(row):
    p = (row.get("pattern_type") or "").upper()
    if "BULL" in p:
        return +1
    if "BEAR" in p:
        return -1
    return 0


def main():
    sb = get_client()
    print("=" * 88)
    print("EXPERIMENT 47b — DIRECTION STABILITY VIA BACKWARDS-LOOKING ANCHOR")
    print("=" * 88)
    print(f"Window: {START_DATE} .. {END_DATE}")
    print()

    print("[INFO] fetching hist_pattern_signals ...")
    sigs, ts_col = fetch_pattern_signals(sb, START_DATE, END_DATE)
    print(f"[INFO] {len(sigs)} signals fetched, ts_col={ts_col}")
    if not sigs:
        sys.exit(1)

    # Pre-fetch 5m bars per symbol for the whole window (one query per symbol)
    bars_by_symbol = {}
    for symbol in ("NIFTY", "SENSEX"):
        print(f"[INFO] fetching 5m bars for {symbol} ...")
        start_dt = datetime.fromisoformat(f"{START_DATE}T00:00:00")
        end_dt = datetime.fromisoformat(f"{END_DATE}T23:59:59")
        bars = fetch_5m_bars_window(sb, symbol, start_dt, end_dt)
        # Build lookup: list of (dt, close) sorted; we'll bisect
        bars.sort(key=lambda x: x["dt"])
        bars_by_symbol[symbol] = bars
        print(f"[INFO] {symbol}: {len(bars)} 5m bars")
    print()

    # Build a quick index per symbol: dt -> idx
    idx_by_symbol = {}
    for sym, bs in bars_by_symbol.items():
        idx_by_symbol[sym] = {b["dt"]: i for i, b in enumerate(bs)}

    skipped_no_match = 0
    skipped_short_history = 0
    enriched = []
    for row in sigs:
        sym = row.get("symbol")
        if sym not in bars_by_symbol:
            continue
        sig_dt = parse_dt(row.get(ts_col))
        if sig_dt is None:
            continue
        # Find nearest bar at or before sig_dt
        bs = bars_by_symbol[sym]
        # Use binary search via list traversal
        # Quick approach: walk backwards through bars_by_symbol for closest match
        # For efficiency at scale, we should bisect.
        import bisect
        keys = [b["dt"] for b in bs]
        pos = bisect.bisect_right(keys, sig_dt) - 1
        if pos < 0:
            skipped_no_match += 1
            continue
        if pos < 12:
            skipped_short_history += 1
            continue
        cur_close = bs[pos]["close"]
        close_6_ago = bs[pos - 6]["close"]
        close_12_ago = bs[pos - 12]["close"]
        ret_30m_back = (cur_close - close_6_ago) / close_6_ago * 100  # percentage points
        ret_60m_back = (cur_close - close_12_ago) / close_12_ago * 100
        row["_ret_30m_back"] = ret_30m_back
        row["_ret_60m_back"] = ret_60m_back
        row["_sig_dt"] = sig_dt
        enriched.append(row)

    print(f"[INFO] enriched {len(enriched)}/{len(sigs)} signals; skipped: "
          f"no_bar_match={skipped_no_match}, short_history={skipped_short_history}")
    print()

    if not enriched:
        print("[FATAL] no signals could be enriched with backwards-looking anchors.")
        sys.exit(1)

    # === Per-policy flip counts ===
    sessions = defaultdict(list)
    for r in enriched:
        key = (r.get("symbol"), r["_sig_dt"].date())
        sessions[key].append(r)

    policies = [
        ("ret_session",   lambda r: sign(r.get("ret_session"))),
        ("ret_30m_back",  lambda r: sign(r.get("_ret_30m_back"))),
        ("ret_60m_back",  lambda r: sign(r.get("_ret_60m_back"))),
    ]

    flips_per_policy = defaultdict(int)
    sessions_count = 0
    for sk, rs in sessions.items():
        sessions_count += 1
        rs.sort(key=lambda x: x["_sig_dt"])
        for label, fn in policies:
            prev = 0
            for r in rs:
                d = fn(r)
                if d == 0:
                    continue
                if prev != 0 and d != prev:
                    flips_per_policy[label] += 1
                prev = d

    print("--- Same-session flip count per policy ---")
    print(f"{'Policy':<16} {'Total flips':>12} {'Sessions':>10} {'Flips/session':>15}")
    base = flips_per_policy["ret_session"]
    for label, _ in policies:
        f = flips_per_policy[label]
        rate = f / sessions_count if sessions_count else 0
        marker = "  <- baseline" if label == "ret_session" else (
            f"  ({(base - f) / base * 100:+.1f}% vs baseline)" if base else ""
        )
        print(f"{label:<16} {f:>12} {sessions_count:>10} {rate:>15.3f}{marker}")
    print()

    # === Per-pattern WR per policy (proper: outcome = ret_30m forward) ===
    # WR = pattern_intent matches sign(ret_30m forward); but only count rows where
    # the policy direction matches pattern intent (i.e. policy "would have allowed").
    print("--- Per-pattern WR per policy (outcome = forward ret_30m sign) ---")
    print(f"{'Policy':<16} {'Pattern':<12} {'Allowed':>8} {'Won':>6} {'WR':>7}")
    per_pol_per_pat = defaultdict(lambda: defaultdict(lambda: {"allowed": 0, "won": 0}))
    for r in enriched:
        intent = pattern_intent(r)
        if intent == 0:
            continue
        ret30_fwd = r.get("ret_30m")
        if ret30_fwd is None:
            continue
        won = (intent > 0 and ret30_fwd > 0) or (intent < 0 and ret30_fwd < 0)
        ptype = r.get("pattern_type") or "UNKNOWN"
        for label, fn in policies:
            d = fn(r)
            if d != intent:
                continue
            b = per_pol_per_pat[label][ptype]
            b["allowed"] += 1
            if won:
                b["won"] += 1

    pattern_keys = sorted({p for inner in per_pol_per_pat.values() for p in inner})
    for label, _ in policies:
        for p in pattern_keys:
            b = per_pol_per_pat[label][p]
            if b["allowed"] == 0:
                continue
            wr = b["won"] / b["allowed"] * 100
            print(f"{label:<16} {p:<12} {b['allowed']:>8} {b['won']:>6} {wr:>6.1f}%")
        print()

    print("=" * 88)
    print("DECISION RULE:")
    print("  PASS = backwards anchor (ret_30m_back / ret_60m_back) WR >= ret_session WR")
    print("         within +/-2pp AND >= 30% flip reduction.")
    print("  Apply manually to tables above.")
    print("=" * 88)


if __name__ == "__main__":
    main()
