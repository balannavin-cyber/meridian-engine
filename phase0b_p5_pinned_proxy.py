#!/usr/bin/env python3
"""
phase0b_p5_pinned_proxy.py — ADR-002 v2 P5 PINNED principle feasibility test.

ADR-002 v2 P5: PINNED regime (spot pinned near gamma wall, low movement
expected) is empirically distinct from LONG_GAMMA / SHORT_GAMMA in outcome
distribution. Per D.10.7, Phase 0b confirms by retroactive cohort tagging.

Full P5 test requires ENH-80 (per-strike GEX table) for local_gex_cluster_cr
which is the proper PINNED qualifier. Until ENH-80 builds, we test with a
PROXY signal constructed from existing gamma_metrics columns:

  PROXY-PINNED state:
    gamma_concentration >= P75    (gamma packed at few strikes, suggesting
                                    spot is being pulled to a wall)
    AND |flip_distance_pct| < 0.5%   (spot close to flip level, characteristic
                                       of pin behavior)
    AND regime IN ('LONG_GAMMA', 'SHORT_GAMMA') AND NOT NO_FLIP
                                    (only meaningful when flip level exists)

If proxy-PINNED shows distinct outcome from non-proxy-PINNED, ENH-80 build is
justified (the proper PINNED definition can only refine, not refute, the
proxy result). If proxy-PINNED shows no differential, P5 itself becomes
suspect even before paying ENH-80 build cost.

Method:
  Same cohort (hist_pattern_signals) + outcome (option P&L T+30m) as
  phase0b_rr_conditional_wr.py.
  Add per-signal join to gamma_metrics for the proxy classification.
  Binary partition: PROXY-PINNED vs NOT-PROXY-PINNED.
  Tests: 2x2 chi-sq on WR + Welch's t-test on mean P&L.

Run:
    python phase0b_p5_pinned_proxy.py
"""
from __future__ import annotations

import math
import os
import random
import re
import sys
from datetime import datetime, date, time, timezone, timedelta

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

# PINNED proxy thresholds (calibrated to bottom 25% by hand on empirical distribution).
PROXY_FLIP_DIST_MAX_PCT = 0.5   # |flip_distance_pct| < this counts as "near wall"

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
    """{(symbol, floored_real_utc_ts): {gamma_concentration, flip_distance_pct, regime}}"""
    print(f"[2/3] Fetching gamma_metrics...")
    q = (sb.table("gamma_metrics")
         .select("symbol, ts, gamma_concentration, flip_distance_pct, regime")
         .gte("ts", DATE_START).lte("ts", DATE_END))
    rows = _paginated_fetch(q)
    out: dict[tuple[str, datetime], dict] = {}
    for r in rows:
        try: ts = _floor_to_5min(_ts_from_str(r["ts"]))
        except (KeyError, ValueError): continue
        out[(r["symbol"], ts)] = {
            "gamma_concentration": r.get("gamma_concentration"),
            "flip_distance_pct": r.get("flip_distance_pct"),
            "regime": r.get("regime"),
        }
    print(f"      → {len(out)} gamma_metrics rows")
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
    for sig in signals:
        try: bar_ts_ist = _ts_from_str(sig["bar_ts"])
        except (KeyError, ValueError): continue
        symbol = sig["symbol"]
        pattern = sig["pattern_type"]
        direction = sig.get("direction")
        bar_ts_real_utc = (bar_ts_ist.replace(tzinfo=None) - IST_TZ_OFFSET).replace(tzinfo=timezone.utc)
        gm = gm_map.get((symbol, _floor_to_5min(bar_ts_real_utc)))
        if gm is None:
            skipped_no_gm += 1
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

    print(f"Processed: {len(enriched)} signals (skipped: {skipped_no_prices} no-prices, {skipped_no_gm} no-gamma_metrics)\n")

    pinned = [s for s in enriched if s["proxy_pinned"]]
    notpinned = [s for s in enriched if not s["proxy_pinned"]]

    print("=" * 78)
    print("PHASE 0b (c) — P5 PROXY-PINNED FEASIBILITY TEST")
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

    print(f"\n--- Statistical tests ---")
    print(f"  WR differential:   χ² = {chi2:.2f}, p ≈ {p_chi:.3f}")
    print(f"  P&L differential:  Δ = {mp - mnp:+.2f}pp, t = {t:.2f}, p ≈ {p_t:.4f}")

    print(f"\n--- Verdict ---")
    wr_sig = p_chi < 0.05
    ev_sig = p_t < 0.05
    direction_distinct = abs(mp - mnp) > 3.0  # ≥3pp materially distinct

    print(f"  PROXY-PINNED outcome distribution distinct?     {'YES' if direction_distinct else 'NO'} (|ΔP&L| = {abs(mp - mnp):.2f}pp)")
    print(f"  WR differential statistically significant?      {'YES' if wr_sig else 'NO'}")
    print(f"  P&L differential statistically significant?     {'YES' if ev_sig else 'NO'}")
    pass_test = direction_distinct and (wr_sig or ev_sig)
    print(f"\n  VERDICT: {'PASS — P5 proxy shows signal; ENH-80 build justified for proper PINNED measurement' if pass_test else 'FAIL — even proxy PINNED has no differential; P5 itself suspect before paying ENH-80 cost'}")
    print(f"\n  NOTE: This is a PROXY test. Full P5 requires ENH-80 per-strike GEX.")
    print(f"        PASS here is necessary but not sufficient for P5 truth;")
    print(f"        FAIL here likely refutes P5 even before ENH-80 build cost.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
