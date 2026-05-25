#!/usr/bin/env python3
"""
phase0b_compressed_veto.py — Salvage thesis for ENH-97.

Phase 0b RR 4-way regime test (phase0b_rr_conditional_wr.py) returned FAIL on
strict ADR-002 v2 P7 (chi-sq p=0.30 on WR, no significant differential). But
COMPRESSED regime showed -3.3% mean P&L vs +10%-ish for other regimes —
suggesting binary COMPRESSED-veto gate has EV-filter value even if 4-way WR
gate doesn't.

This script tests: does COMPRESSED-veto have statistically significant
EV-lift over not-vetoing? If yes, ENH-97 ships as a 1-bit gate
(COMPRESSED → block; else → allow) instead of the original 4-way scheme.

Method:
  Same cohort, regime tagging, option P&L attribution as phase0b_rr_conditional_wr.py.
  Binary partition: COMPRESSED-only vs union(HIGH, FAIR, LOW).
  Tests:
    (1) 2x2 chi-square on WR differential
    (2) Welch's t-test on mean P&L differential
    (3) Bootstrap CI on EV gap

Run:
    python phase0b_compressed_veto.py
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
# Constants (identical to phase0b_rr_conditional_wr.py)
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
BOOTSTRAP_ITER = 5000


# ============================================================================
# Reused helpers
# ============================================================================

_MICROSECOND_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


def _normalize_microseconds(ts_str: str) -> str:
    m = _MICROSECOND_RE.search(ts_str)
    if m is None:
        return ts_str
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6:
        return ts_str
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MICROSECOND_RE.sub(f".{frac6}{tz}", ts_str)


def _ts_from_str(ts_str: str) -> datetime:
    norm = _normalize_microseconds(ts_str.replace("Z", "+00:00"))
    return datetime.fromisoformat(norm)


def _floor_to_5min(ts: datetime) -> datetime:
    return ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)


def _load_supabase_client() -> Client:
    load_dotenv(override=False)
    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
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


# ============================================================================
# Data fetchers (reused)
# ============================================================================

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


def fetch_vol_analytics_map(sb: Client) -> dict[tuple[str, datetime], str]:
    print(f"[2/3] Fetching vol_analytics map...")
    q = (sb.table("vol_analytics").select("symbol, ts, rr_regime")
         .gte("ts", DATE_START).lte("ts", DATE_END))
    rows = _paginated_fetch(q)
    out: dict[tuple[str, datetime], str] = {}
    for r in rows:
        try: ts = _floor_to_5min(_ts_from_str(r["ts"]))
        except (KeyError, ValueError): continue
        if r.get("rr_regime"):
            out[(r["symbol"], ts)] = r["rr_regime"]
    print(f"      → {len(out)} regime-tagged keys")
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


def process_signal(signal, vol_map, atm_map):
    try: bar_ts_ist = _ts_from_str(signal["bar_ts"])
    except (KeyError, ValueError): return None
    symbol = signal["symbol"]
    pattern = signal["pattern_type"]
    direction = signal.get("direction")
    bar_ts_real_utc = (bar_ts_ist.replace(tzinfo=None) - IST_TZ_OFFSET).replace(tzinfo=timezone.utc)
    rr_regime = vol_map.get((symbol, _floor_to_5min(bar_ts_real_utc)))
    entry_bar = atm_map.get((symbol, bar_ts_ist))
    exit_bar = atm_map.get((symbol, bar_ts_ist + timedelta(minutes=EXIT_OFFSET_MINUTES)))
    if entry_bar is None or exit_bar is None: return None

    if direction == "BUY_CE":
        entry_price, exit_price = entry_bar.get("ce_close"), exit_bar.get("ce_close")
    elif direction == "BUY_PE":
        entry_price, exit_price = entry_bar.get("pe_close"), exit_bar.get("pe_close")
    elif pattern in ("BULL_OB", "BULL_FVG"):
        entry_price, exit_price = entry_bar.get("ce_close"), exit_bar.get("ce_close")
    else:
        entry_price, exit_price = entry_bar.get("pe_close"), exit_bar.get("pe_close")
    if entry_price is None or exit_price is None: return None
    try: entry_f, exit_f = float(entry_price), float(exit_price)
    except (TypeError, ValueError): return None
    if entry_f <= 0: return None

    pnl_pct = (exit_f - entry_f) / entry_f * 100.0
    return {"symbol": symbol, "pattern": pattern, "rr_regime": rr_regime,
            "pnl_pct": pnl_pct, "win": pnl_pct > 0}


# ============================================================================
# Statistical tests
# ============================================================================

def mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n == 0: return (0.0, 0.0)
    m = sum(values) / n
    if n == 1: return (m, 0.0)
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    return (m, math.sqrt(var))


def welch_t_test(a: list[float], b: list[float]) -> tuple[float, float, float]:
    """Returns (t_stat, df, p_value_approx). p approximation via two-tailed normal at high df."""
    ma, sa = mean_std(a); mb, sb = mean_std(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2: return (0.0, 0.0, 1.0)
    se = math.sqrt(sa ** 2 / na + sb ** 2 / nb)
    if se == 0: return (0.0, 0.0, 1.0)
    t = (ma - mb) / se
    # Welch-Satterthwaite df
    num = (sa ** 2 / na + sb ** 2 / nb) ** 2
    denom = ((sa ** 2 / na) ** 2 / (na - 1)) + ((sb ** 2 / nb) ** 2 / (nb - 1))
    df = num / denom if denom > 0 else min(na, nb) - 1
    # Two-tailed p approximation via normal (valid for df > 30)
    z = abs(t)
    p_one_tail = 0.5 * math.erfc(z / math.sqrt(2))
    return (t, df, 2 * p_one_tail)


def bootstrap_diff(a: list[float], b: list[float], n_iter: int = BOOTSTRAP_ITER) -> tuple[float, float, float]:
    """Bootstrap 95% CI on (mean(a) - mean(b))."""
    if not a or not b: return (0.0, 0.0, 0.0)
    random.seed(42)
    diffs = []
    for _ in range(n_iter):
        sample_a = [a[random.randrange(len(a))] for _ in range(len(a))]
        sample_b = [b[random.randrange(len(b))] for _ in range(len(b))]
        diffs.append(sum(sample_a) / len(sample_a) - sum(sample_b) / len(sample_b))
    diffs.sort()
    point = sum(a) / len(a) - sum(b) / len(b)
    lo = diffs[int(0.025 * n_iter)]
    hi = diffs[int(0.975 * n_iter)]
    return (point, lo, hi)


def chi_sq_2x2(a_wins: int, a_n: int, b_wins: int, b_n: int) -> tuple[float, float]:
    """2x2 chi-square. Returns (chi2, p_approx)."""
    total_w = a_wins + b_wins
    total_n = a_n + b_n
    if total_n == 0 or total_w == 0 or total_w == total_n: return (0.0, 1.0)
    p = total_w / total_n
    exp_aw, exp_al = a_n * p, a_n * (1 - p)
    exp_bw, exp_bl = b_n * p, b_n * (1 - p)
    chi2 = 0.0
    for obs, exp in [(a_wins, exp_aw), (a_n - a_wins, exp_al),
                      (b_wins, exp_bw), (b_n - b_wins, exp_bl)]:
        if exp > 0: chi2 += (obs - exp) ** 2 / exp
    # df=1 critical values
    if chi2 > 6.635: p_approx = 0.01
    elif chi2 > 3.841: p_approx = 0.05
    elif chi2 > 2.706: p_approx = 0.10
    else: p_approx = 0.30
    return (chi2, p_approx)


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    sb = _load_supabase_client()
    signals = fetch_signals(sb)
    if not signals: print("No signals."); return 1
    vol_map = fetch_vol_analytics_map(sb)
    atm_map = fetch_atm_option_map(sb)

    enriched = []
    for sig in signals:
        r = process_signal(sig, vol_map, atm_map)
        if r is not None and r["rr_regime"] is not None:
            enriched.append(r)

    print(f"\n→ {len(enriched)} regime-tagged signals with P&L attributed\n")

    compressed = [s for s in enriched if s["rr_regime"] == "COMPRESSED"]
    other = [s for s in enriched if s["rr_regime"] != "COMPRESSED"]

    print("=" * 78)
    print("PHASE 0b (b) — COMPRESSED-VETO SALVAGE TEST")
    print("=" * 78)
    print(f"\n{'Bucket':<20} {'N':>6} {'Wins':>6} {'WR':>8} {'Mean P&L':>10} {'Median':>10} {'Stdev':>10}")
    print("-" * 78)

    for label, bucket in [("COMPRESSED (veto)", compressed), ("NOT-COMPRESSED", other)]:
        n = len(bucket)
        wins = sum(1 for s in bucket if s["win"])
        wr = wins / n * 100 if n else 0
        pnls = [s["pnl_pct"] for s in bucket]
        m, std = mean_std(pnls)
        median = sorted(pnls)[n // 2] if pnls else 0
        print(f"{label:<20} {n:>6} {wins:>6} {wr:>7.1f}% {m:>+8.2f}% {median:>+8.2f}% {std:>+8.2f}%")

    # Tests
    c_wins = sum(1 for s in compressed if s["win"])
    o_wins = sum(1 for s in other if s["win"])
    chi2, p_chi = chi_sq_2x2(c_wins, len(compressed), o_wins, len(other))

    c_pnls = [s["pnl_pct"] for s in compressed]
    o_pnls = [s["pnl_pct"] for s in other]
    t, df, p_t = welch_t_test(o_pnls, c_pnls)  # other - compressed (positive = other better)
    point, lo, hi = bootstrap_diff(o_pnls, c_pnls)

    print(f"\n--- WR differential (chi-sq 2x2) ---")
    print(f"  χ² = {chi2:.2f},  p ≈ {p_chi:.3f}")
    wr_sig = p_chi < 0.05

    print(f"\n--- Mean P&L differential (Welch's t-test) ---")
    print(f"  Δ(other − compressed) = {point:+.2f}pp")
    print(f"  95% bootstrap CI: [{lo:+.2f}, {hi:+.2f}]pp")
    print(f"  t = {t:.2f}, df ≈ {df:.0f}, p ≈ {p_t:.4f}")
    ev_sig = p_t < 0.05
    ci_excludes_zero = (lo > 0) or (hi < 0)

    print(f"\n--- Verdict ---")
    print(f"  WR differential significant (p<0.05):           {'YES' if wr_sig else 'NO'}")
    print(f"  Mean P&L differential significant (t-test):     {'YES' if ev_sig else 'NO'}")
    print(f"  Bootstrap 95% CI on EV gap excludes zero:       {'YES' if ci_excludes_zero else 'NO'}")
    print(f"  EV improvement from vetoing COMPRESSED:         {point:+.2f}pp per trade")
    if len(compressed) > 0 and len(other) > 0:
        c_ev = sum(c_pnls) / len(c_pnls)
        o_ev = sum(o_pnls) / len(o_pnls)
        print(f"    (COMPRESSED EV={c_ev:+.2f}%, OTHER EV={o_ev:+.2f}%)")

    pass_test = ev_sig and ci_excludes_zero and point > 0
    print(f"\n  VERDICT: {'PASS — ship ENH-97 as 1-bit COMPRESSED-veto gate' if pass_test else 'FAIL — even binary veto lacks edge; full pivot to logging-only'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
