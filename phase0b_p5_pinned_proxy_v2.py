#!/usr/bin/env python3
"""
phase0b_p5_pinned_proxy_v2.py — S30 P3b re-run of ADR-002 v2 P5 PINNED feasibility test.

Differences from v1 (S29 INCONCLUSIVE N=3, ADR-009 §Open-follow-ups S30):
  1. RAW-cohort exclusion. v1 joined against `gamma_metrics` rows from Mar 8 →
     May 7 2026 where `net_gex` was stored in raw rupees (pre-S27 cf66fa9 fix)
     AND `flip_level` was stuck at deep-ITM (pre-S27 TD-NEW-2 walk-from-ATM
     fix). The unit-invariant columns (`regime`, `gamma_concentration`) are
     usable on these rows, but `flip_distance_pct` is structurally corrupt
     because `flip_level` was broken. Including them pollutes the
     NOT-PROXY-PINNED bucket. v2 filters them at load time via
     `abs(net_gex) > 1e9` — unit-robust, also catches future regressions.
     Pre-Mar 8 2026 cohort (33K rows, Apr 2025 → Mar 7 2026) is CR-correct
     and research-usable.
  2. ADR-009 §Phase 1 S29 sub-rule wired into verdict. v1 reported median
     P&L per bucket but the automated verdict ignored it. v2 adds the
     "both buckets median ≤ 0 → FAIL" rule — a dimension that fails to
     produce a positive-median bucket cannot survive overhead/slippage as
     a gate, even if WR difference is statistically significant.
  3. Per-month enrichment diagnostic. v2 prints how many signals enriched
     per trade-month to surface era-boundary join failures (Rule 20) if
     they exist. v1 had no such instrumentation.

ADR-002 v2 P5 (PINNED regime distinct from LONG/SHORT_GAMMA in outcome) is the
hypothesis under test. Full P5 requires ENH-80 per-strike GEX for the
`local_gex_cluster_cr` qualifier. Until ENH-80 builds, v1/v2 test a PROXY:

  PROXY-PINNED state:
    gamma_concentration >= P75 per-symbol
    AND |flip_distance_pct| < 0.5%
    AND regime != 'NO_FLIP'

If proxy-PINNED shows distinct outcome from non-proxy-PINNED, ENH-80 build is
justified (proper PINNED can only refine, not refute, the proxy result). If
proxy-PINNED shows no differential, P5 itself is suspect before paying ENH-80
build cost.

Run:
    python phase0b_p5_pinned_proxy_v2.py
"""
# S30_P3B_V2 — RAW-exclusion + ADR-009 §S29 median-FAIL + per-month enrichment diagnostic
from __future__ import annotations

import math
import os
import re
import sys
from collections import Counter
from datetime import datetime, date, timezone, timedelta

from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore


# ============================================================================
# Constants
# ============================================================================

SPOT_INSTRUMENT_ID = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}
INSTRUMENT_TO_SYMBOL = {v: k for k, v in SPOT_INSTRUMENT_ID.items()}
IST_TZ_OFFSET = timedelta(hours=5, minutes=30)
EXIT_OFFSET_MINUTES = 30
PATTERNS_IN_SCOPE = {"BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"}
DATE_START = "2025-04-01"
DATE_END = "2026-05-15"

# PINNED proxy thresholds
PROXY_FLIP_DIST_MAX_PCT = 0.5

# v2: RAW-range exclusion threshold. Cr-correct rows have |net_gex| < ~10M
# (typical 1K-10M Cr); RAW-rupee rows are 1e9+. Threshold at 1e9 is the
# unambiguous boundary; legitimate AMBIGUOUS rows (1e7-1e9) on SENSEX
# high-event days are retained.
RAW_NET_GEX_THRESHOLD = 1e9

_MICROSECOND_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


def _normalize_microseconds(ts_str: str) -> str:
    m = _MICROSECOND_RE.search(ts_str)
    if m is None: return ts_str
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6: return ts_str
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MICROSECOND_RE.sub(f".{frac6}{tz}", ts_str)


def _ts_from_str(ts_str: str) -> datetime:
    return datetime.fromisoformat(_normalize_microseconds(ts_str.replace("Z", "+00:00")))


def _floor_to_5min(ts: datetime) -> datetime:
    return ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)


def _load_supabase_client() -> Client:
    load_dotenv(override=False)
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        raise RuntimeError("SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def _paginated_fetch(query_builder, page_size: int = 1000) -> list[dict]:
    out, offset = [], 0
    while True:
        resp = query_builder.range(offset, offset + page_size - 1).execute()
        rows = resp.data or []
        if not rows: break
        out.extend(rows)
        if len(rows) < page_size: break
        offset += page_size
    return out


def fetch_signals(sb: Client) -> list[dict]:
    print(f"[1/3] Fetching hist_pattern_signals...")
    q = (sb.table("hist_pattern_signals")
         .select("trade_date, symbol, bar_ts, pattern_type, direction")
         .gte("trade_date", DATE_START).lte("trade_date", DATE_END)
         .in_("pattern_type", list(PATTERNS_IN_SCOPE))
         .order("bar_ts"))
    rows = _paginated_fetch(q)
    print(f"      → {len(rows)} signals")
    return rows


def fetch_gamma_metrics_map(sb: Client) -> dict[tuple[str, datetime], dict]:
    """{(symbol, floored_real_utc_ts): {gamma_concentration, flip_distance_pct, regime}}

    v2: excludes RAW-range rows (|net_gex| > 1e9) at load time. These are
    pre-S27 cf66fa9 broken-cohort rows where flip_level is also broken
    (pre-S27 TD-NEW-2 walk-from-ATM fix), making the PROXY-PINNED criterion
    structurally meaningless on them. Excluding via magnitude (not date)
    makes the filter robust to any future regression.
    """
    print(f"[2/3] Fetching gamma_metrics (v2: RAW exclusion enabled)...")
    q = (sb.table("gamma_metrics")
         .select("symbol, ts, gamma_concentration, flip_distance_pct, regime, net_gex")
         .gte("ts", DATE_START).lte("ts", DATE_END))
    rows = _paginated_fetch(q)
    out: dict[tuple[str, datetime], dict] = {}
    skipped_raw = 0
    for r in rows:
        # v2: RAW-range exclusion
        try:
            ng = r.get("net_gex")
            if ng is not None and abs(float(ng)) > RAW_NET_GEX_THRESHOLD:
                skipped_raw += 1
                continue
        except (TypeError, ValueError):
            pass
        try: ts = _floor_to_5min(_ts_from_str(r["ts"]))
        except (KeyError, ValueError): continue
        out[(r["symbol"], ts)] = {
            "gamma_concentration": r.get("gamma_concentration"),
            "flip_distance_pct": r.get("flip_distance_pct"),
            "regime": r.get("regime"),
        }
    print(f"      → {len(out)} gamma_metrics rows (CR-clean)")
    if skipped_raw:
        print(f"      → {skipped_raw} RAW-range rows excluded (pre-S27 cf66fa9 broken-cohort)")
    return out


def fetch_atm_option_map(sb: Client) -> dict[tuple[str, datetime], dict]:
    print(f"[3/3] Fetching hist_atm_option_bars_5m...")
    q = (sb.table("hist_atm_option_bars_5m")
         .select("instrument_id, bar_ts, expiry_date, atm_strike, ce_close, pe_close")
         .gte("bar_ts", DATE_START).lte("bar_ts", DATE_END))
    rows = _paginated_fetch(q)
    grouped: dict[tuple[str, datetime], list[dict]] = {}
    for r in rows:
        symbol = INSTRUMENT_TO_SYMBOL.get(r.get("instrument_id"))
        if symbol is None: continue
        try: bar_ts = _ts_from_str(r["bar_ts"])
        except (KeyError, ValueError): continue
        grouped.setdefault((symbol, bar_ts), []).append(r)
    out: dict[tuple[str, datetime], dict] = {}
    for (symbol, bar_ts), candidates in grouped.items():
        trade_date = bar_ts.date()
        eligible = []
        for c in candidates:
            try: exp = date.fromisoformat(str(c["expiry_date"]))
            except (KeyError, ValueError, TypeError): continue
            if exp >= trade_date: eligible.append((exp, c))
        if not eligible: continue
        eligible.sort(key=lambda x: x[0])
        out[(symbol, bar_ts)] = eligible[0][1]
    print(f"      → {len(out)} current-week ATM bars")
    return out


def _percentile(values: list[float], pct: float) -> float:
    if not values: return 0.0
    s = sorted(values)
    idx = int(pct * len(s))
    return s[min(idx, len(s) - 1)]


def main() -> int:
    sb = _load_supabase_client()
    signals = fetch_signals(sb)
    gm_map = fetch_gamma_metrics_map(sb)
    atm_map = fetch_atm_option_map(sb)

    # Compute P75 threshold for gamma_concentration empirically (per symbol)
    gc_by_symbol: dict[str, list[float]] = {"NIFTY": [], "SENSEX": []}
    for (sym, _), v in gm_map.items():
        gc = v.get("gamma_concentration")
        if gc is not None:
            try: gc_by_symbol[sym].append(float(gc))
            except (TypeError, ValueError): pass
    gc_p75 = {sym: _percentile(vals, 0.75) for sym, vals in gc_by_symbol.items()}
    print(f"\nGamma concentration P75 thresholds: NIFTY={gc_p75.get('NIFTY', 0):.4f}, SENSEX={gc_p75.get('SENSEX', 0):.4f}")
    print(f"PROXY-PINNED criteria: gamma_concentration >= P75 AND |flip_distance_pct| < {PROXY_FLIP_DIST_MAX_PCT}% AND regime != NO_FLIP\n")

    # Process signals
    enriched = []
    skipped_no_prices = skipped_no_gm = 0
    # v2: per-month enrichment counters (surfaces era-boundary join failures)
    month_signals = Counter()
    month_enriched = Counter()
    month_skipped_no_gm = Counter()

    for sig in signals:
        try: bar_ts_ist = _ts_from_str(sig["bar_ts"])
        except (KeyError, ValueError): continue
        month_key = bar_ts_ist.strftime("%Y-%m")
        month_signals[month_key] += 1
        symbol = sig["symbol"]
        pattern = sig["pattern_type"]
        direction = sig.get("direction")
        bar_ts_real_utc = (bar_ts_ist.replace(tzinfo=None) - IST_TZ_OFFSET).replace(tzinfo=timezone.utc)
        gm = gm_map.get((symbol, _floor_to_5min(bar_ts_real_utc)))
        if gm is None:
            skipped_no_gm += 1
            month_skipped_no_gm[month_key] += 1
            continue
        entry_bar = atm_map.get((symbol, bar_ts_ist))
        exit_bar = atm_map.get((symbol, bar_ts_ist + timedelta(minutes=EXIT_OFFSET_MINUTES)))
        if entry_bar is None or exit_bar is None:
            skipped_no_prices += 1
            continue
        if direction == "BUY_CE": ep, xp = entry_bar.get("ce_close"), exit_bar.get("ce_close")
        elif direction == "BUY_PE": ep, xp = entry_bar.get("pe_close"), exit_bar.get("pe_close")
        elif pattern in ("BULL_OB", "BULL_FVG"): ep, xp = entry_bar.get("ce_close"), exit_bar.get("ce_close")
        else: ep, xp = entry_bar.get("pe_close"), exit_bar.get("pe_close")
        if ep is None or xp is None: continue
        try: epf, xpf = float(ep), float(xp)
        except (TypeError, ValueError): continue
        if epf <= 0: continue
        pnl = (xpf - epf) / epf * 100

        # PROXY-PINNED classification
        gc = gm.get("gamma_concentration")
        fdp = gm.get("flip_distance_pct")
        regime = gm.get("regime")
        proxy_pinned = False
        if gc is not None and fdp is not None and regime is not None:
            try:
                gc_f = float(gc); fdp_f = abs(float(fdp))
                proxy_pinned = (gc_f >= gc_p75.get(symbol, 1.0)
                                and fdp_f < PROXY_FLIP_DIST_MAX_PCT
                                and regime != "NO_FLIP")
            except (TypeError, ValueError): pass

        enriched.append({
            "symbol": symbol, "pattern": pattern, "pnl_pct": pnl, "win": pnl > 0,
            "proxy_pinned": proxy_pinned, "gamma_regime": regime,
        })
        month_enriched[month_key] += 1

    print(f"Processed: {len(enriched)} signals (skipped: {skipped_no_prices} no-prices, {skipped_no_gm} no-gamma_metrics)\n")

    # v2: per-month enrichment diagnostic (era-boundary canary)
    print("--- Per-month enrichment (era-boundary canary) ---")
    print(f"{'Month':<10} {'Signals':>10} {'Enriched':>10} {'No-GM':>10} {'Enrich%':>9}")
    print("-" * 53)
    for month in sorted(month_signals.keys()):
        sigs = month_signals[month]
        enr = month_enriched[month]
        nogm = month_skipped_no_gm[month]
        pct = (enr / sigs * 100) if sigs else 0.0
        print(f"{month:<10} {sigs:>10} {enr:>10} {nogm:>10} {pct:>8.1f}%")
    print()

    pinned = [s for s in enriched if s["proxy_pinned"]]
    notpinned = [s for s in enriched if not s["proxy_pinned"]]

    print("=" * 78)
    print("PHASE 0b — P5 PROXY-PINNED FEASIBILITY TEST (v2, S30 P3b)")
    print("=" * 78)
    print(f"\n{'Bucket':<22} {'N':>6} {'Wins':>6} {'WR':>8} {'Mean P&L':>10} {'Median':>10}")
    print("-" * 66)
    for label, bucket in [("PROXY-PINNED", pinned), ("NOT-PROXY-PINNED", notpinned)]:
        n = len(bucket)
        wins = sum(1 for s in bucket if s["win"])
        wr = wins / n * 100 if n else 0
        pnls = [s["pnl_pct"] for s in bucket]
        m = sum(pnls) / n if n else 0
        median = sorted(pnls)[n // 2] if pnls else 0
        print(f"{label:<22} {n:>6} {wins:>6} {wr:>7.1f}% {m:>+8.2f}% {median:>+8.2f}%")

    # Per-regime breakdown
    print(f"\n--- Per gamma_regime breakdown (orthogonality check) ---")
    for gr in ["LONG_GAMMA", "SHORT_GAMMA", "NO_FLIP"]:
        bucket_p = [s for s in pinned if s["gamma_regime"] == gr]
        bucket_np = [s for s in notpinned if s["gamma_regime"] == gr]
        for label, b in [(f"{gr} PINNED", bucket_p), (f"{gr} not-pinned", bucket_np)]:
            n = len(b)
            if n < 10: continue
            wins = sum(1 for s in b if s["win"])
            wr = wins / n * 100
            pnls = [s["pnl_pct"] for s in b]
            m = sum(pnls) / n
            print(f"{label:<26} N={n:>5} WR={wr:>5.1f}% P&L={m:>+7.2f}%")

    # Tests
    p_wins = sum(1 for s in pinned if s["win"])
    np_wins = sum(1 for s in notpinned if s["win"])
    p_n, np_n = len(pinned), len(notpinned)

    if p_n == 0 or np_n == 0:
        print("\n*** Insufficient cohort for statistical test ***")
        return 1

    # 2x2 chi-sq
    total_w = p_wins + np_wins
    total_n = p_n + np_n
    overall_wr = total_w / total_n
    chi2 = 0
    for obs, exp in [(p_wins, p_n * overall_wr), (p_n - p_wins, p_n * (1 - overall_wr)),
                      (np_wins, np_n * overall_wr), (np_n - np_wins, np_n * (1 - overall_wr))]:
        if exp > 0: chi2 += (obs - exp) ** 2 / exp
    p_chi = 0.01 if chi2 > 6.635 else 0.05 if chi2 > 3.841 else 0.10 if chi2 > 2.706 else 0.30

    # Welch's t
    p_pnls = [s["pnl_pct"] for s in pinned]
    np_pnls = [s["pnl_pct"] for s in notpinned]
    mp, mnp = sum(p_pnls) / p_n, sum(np_pnls) / np_n
    sp = math.sqrt(sum((v - mp) ** 2 for v in p_pnls) / (p_n - 1)) if p_n > 1 else 0
    snp = math.sqrt(sum((v - mnp) ** 2 for v in np_pnls) / (np_n - 1)) if np_n > 1 else 0
    se = math.sqrt(sp ** 2 / p_n + snp ** 2 / np_n)
    t = (mp - mnp) / se if se > 0 else 0
    p_t = 2 * 0.5 * math.erfc(abs(t) / math.sqrt(2))

    # v2: medians for ADR-009 §S29 sub-rule
    p_median = sorted(p_pnls)[p_n // 2] if p_pnls else 0.0
    np_median = sorted(np_pnls)[np_n // 2] if np_pnls else 0.0
    both_median_neg = (p_median <= 0) and (np_median <= 0)

    print(f"\n--- Statistical tests ---")
    print(f"  WR differential:   χ² = {chi2:.2f}, p ≈ {p_chi:.3f}")
    print(f"  P&L differential:  Δ = {mp - mnp:+.2f}pp, t = {t:.2f}, p ≈ {p_t:.4f}")
    print(f"  Cohort medians:    PROXY-PINNED = {p_median:+.2f}%, NOT-PINNED = {np_median:+.2f}%")

    print(f"\n--- Verdict ---")
    wr_sig = p_chi < 0.05
    ev_sig = p_t < 0.05
    direction_distinct = abs(mp - mnp) > 3.0  # ≥3pp materially distinct

    print(f"  PROXY-PINNED outcome distribution distinct?     {'YES' if direction_distinct else 'NO'} (|ΔP&L| = {abs(mp - mnp):.2f}pp)")
    print(f"  WR differential statistically significant?      {'YES' if wr_sig else 'NO'}")
    print(f"  P&L differential statistically significant?     {'YES' if ev_sig else 'NO'}")
    print(f"  Both buckets median ≤ 0 (ADR-009 §S29 sub-rule)?{'YES — FAIL override' if both_median_neg else 'NO'}")

    # v2: pass requires median-positive in at least one bucket (ADR-009 §Phase 1 S29)
    pass_test = direction_distinct and (wr_sig or ev_sig) and not both_median_neg

    if pass_test:
        verdict = "PASS — P5 proxy shows signal; ENH-80 build justified for proper PINNED measurement"
    elif both_median_neg:
        verdict = "FAIL — both buckets median-negative per ADR-009 §S29 sub-rule; dimension dead as gate"
    else:
        verdict = "FAIL — proxy PINNED has no differential; P5 itself suspect before paying ENH-80 cost"

    print(f"\n  VERDICT: {verdict}")
    print(f"\n  NOTE: This is a PROXY test. Full P5 requires ENH-80 per-strike GEX.")
    print(f"        PASS here is necessary but not sufficient for P5 truth;")
    print(f"        FAIL here likely refutes P5 even before ENH-80 build cost.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
