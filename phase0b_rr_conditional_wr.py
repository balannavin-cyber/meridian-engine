#!/usr/bin/env python3
"""
phase0b_rr_conditional_wr.py — ADR-002 v2 Phase 0b feasibility test.

The build/pivot question:
    Does RR regime (HIGH / FAIR / LOW / COMPRESSED) move signal WR materially?

If yes (statistically significant differential + direction matches ADR-002 v2
P7 prediction) → PASS → commit to ENH-80 + downstream build.
If no → FAIL → ENH-97 pivots to logging-only; ENH-80 build deferred.

Cohort (chosen per Phase 0b methodology decision S29):
    hist_pattern_signals — 5m batched, 6,318 rows, full year. The 5m-batch
    cohort has known translation risk to live-cohort behavior per D.9.3, but
    it is the only year-scale signal history available. Phase 0b is a
    feasibility check, not a deployment proof; PASS here builds confidence
    to commit ENH-80, doesn't itself prove production lift.

Outcome metric (chosen per TD-054 + Exp 15 pattern):
    Locally-computed option P&L (NOT hist_pattern_signals.ret_30m which is
    documented broken). Read ATM CE/PE close from hist_atm_option_bars_5m
    at signal bar_ts (entry) and signal bar_ts + 30min (exit). WIN = P&L > 0.

Pattern → option type mapping:
    BULL_OB, BULL_FVG → BUY_CE (positive P&L on upward spot move)
    BEAR_OB, BEAR_FVG → BUY_PE (positive P&L on downward spot move)

Refs:
- ADR-002 v2 §P7 (vol-pricing principle, falsification commitment)
- ENH-97 §Falsification criterion
- Assumption Register §D.10.1 (RR ratio independent edge LIVE pending Phase 0b)
- Assumption Register §D.9.3 (cohort-translation lesson)
- TD-054 (hist_pattern_signals.ret_30m broken; outcome computed locally)

Run:
    python phase0b_rr_conditional_wr.py
"""
from __future__ import annotations

import math
import os
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

EXIT_OFFSET_MINUTES = 30   # T+30m exit per Exp 15 convention
PATTERNS_IN_SCOPE = {"BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"}

DATE_START = "2025-04-01"
DATE_END = "2026-05-15"

# ============================================================================
# Helpers
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
    """Yield all rows via .range() pagination."""
    out: list[dict] = []
    offset = 0
    while True:
        resp = query_builder.range(offset, offset + page_size - 1).execute()
        rows = resp.data or []
        if not rows:
            break
        out.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return out


# ============================================================================
# Data fetchers
# ============================================================================

def fetch_signals(sb: Client) -> list[dict]:
    """All hist_pattern_signals in scope. Returns raw rows."""
    print(f"[1/3] Fetching hist_pattern_signals {DATE_START}..{DATE_END}...")
    q = (
        sb.table("hist_pattern_signals")
        .select("trade_date, symbol, bar_ts, pattern_type, direction")
        .gte("trade_date", DATE_START)
        .lte("trade_date", DATE_END)
        .in_("pattern_type", list(PATTERNS_IN_SCOPE))
        .order("bar_ts")
    )
    rows = _paginated_fetch(q)
    print(f"      → {len(rows)} signals")
    return rows


def fetch_vol_analytics_map(sb: Client) -> dict[tuple[str, datetime], dict]:
    """
    {(symbol, floored_real_utc): {rr_regime, rr_ratio, implied_vol_atm}}.
    Real-UTC ts because vol_analytics convention (write_ts from backfill).
    """
    print(f"[2/3] Fetching vol_analytics map...")
    q = (
        sb.table("vol_analytics")
        .select("symbol, ts, rr_regime, rr_ratio, implied_vol_atm")
        .gte("ts", DATE_START)
        .lte("ts", DATE_END)
    )
    rows = _paginated_fetch(q)
    out: dict[tuple[str, datetime], dict] = {}
    for r in rows:
        try:
            ts = _floor_to_5min(_ts_from_str(r["ts"]))
        except (KeyError, ValueError):
            continue
        out[(r["symbol"], ts)] = {
            "rr_regime": r.get("rr_regime"),
            "rr_ratio": r.get("rr_ratio"),
            "implied_vol_atm": r.get("implied_vol_atm"),
        }
    print(f"      → {len(out)} regime-tagged (symbol, ts) keys")
    return out


def fetch_atm_option_map(sb: Client) -> dict[tuple[str, datetime], dict]:
    """
    {(symbol, bar_ts_ist_as_utc): {atm_strike, ce_close, pe_close, expiry_date}}.
    Picks smallest expiry_date >= trade_date per (symbol, bar_ts) — current-week.
    Bar_ts is IST-as-UTC per hist_atm_option_bars_5m convention.
    """
    print(f"[3/3] Fetching hist_atm_option_bars_5m...")
    q = (
        sb.table("hist_atm_option_bars_5m")
        .select("instrument_id, bar_ts, expiry_date, atm_strike, ce_close, pe_close")
        .gte("bar_ts", DATE_START)
        .lte("bar_ts", DATE_END)
    )
    rows = _paginated_fetch(q)
    # Group by (symbol, bar_ts), pick smallest expiry >= signal's trade_date.
    # Trade_date derived from bar_ts (IST clock date).
    grouped: dict[tuple[str, datetime], list[dict]] = {}
    for r in rows:
        symbol = INSTRUMENT_TO_SYMBOL.get(r.get("instrument_id"))
        if symbol is None:
            continue
        try:
            bar_ts = _ts_from_str(r["bar_ts"])
        except (KeyError, ValueError):
            continue
        grouped.setdefault((symbol, bar_ts), []).append(r)

    out: dict[tuple[str, datetime], dict] = {}
    for (symbol, bar_ts), candidates in grouped.items():
        # Trade date = IST clock date = the date part of bar_ts (which is IST-as-UTC)
        trade_date = bar_ts.date()
        eligible = []
        for c in candidates:
            try:
                exp = date.fromisoformat(str(c["expiry_date"]))
            except (KeyError, ValueError, TypeError):
                continue
            if exp >= trade_date:
                eligible.append((exp, c))
        if not eligible:
            continue
        eligible.sort(key=lambda x: x[0])
        chosen = eligible[0][1]
        out[(symbol, bar_ts)] = {
            "atm_strike": chosen.get("atm_strike"),
            "ce_close": chosen.get("ce_close"),
            "pe_close": chosen.get("pe_close"),
            "expiry_date": chosen.get("expiry_date"),
        }
    print(f"      → {len(out)} (symbol, bar_ts) keys with current-week expiry")
    return out


# ============================================================================
# Per-signal outcome attribution
# ============================================================================

def process_signal(
    signal: dict,
    vol_map: dict,
    atm_map: dict,
) -> dict | None:
    """Returns enriched signal dict with regime + pnl_pct + win, or None if skipped."""
    try:
        bar_ts_ist = _ts_from_str(signal["bar_ts"])
    except (KeyError, ValueError):
        return None
    symbol = signal["symbol"]
    pattern = signal["pattern_type"]
    direction = signal.get("direction")

    # rr_regime tagging — convert IST-as-UTC to real-UTC for vol_analytics lookup
    bar_ts_real_utc = (bar_ts_ist.replace(tzinfo=None) - IST_TZ_OFFSET).replace(
        tzinfo=timezone.utc
    )
    floored_real_utc = _floor_to_5min(bar_ts_real_utc)
    vol = vol_map.get((symbol, floored_real_utc))
    rr_regime = vol.get("rr_regime") if vol else None

    # Entry and exit option prices
    entry_bar = atm_map.get((symbol, bar_ts_ist))
    exit_bar_ts = bar_ts_ist + timedelta(minutes=EXIT_OFFSET_MINUTES)
    exit_bar = atm_map.get((symbol, exit_bar_ts))

    if entry_bar is None or exit_bar is None:
        return None

    # Option type from direction (fallback: derive from pattern)
    if direction == "BUY_CE":
        entry_price = entry_bar.get("ce_close")
        exit_price = exit_bar.get("ce_close")
    elif direction == "BUY_PE":
        entry_price = entry_bar.get("pe_close")
        exit_price = exit_bar.get("pe_close")
    elif pattern in ("BULL_OB", "BULL_FVG"):
        entry_price = entry_bar.get("ce_close")
        exit_price = exit_bar.get("ce_close")
    else:  # BEAR_OB, BEAR_FVG
        entry_price = entry_bar.get("pe_close")
        exit_price = exit_bar.get("pe_close")

    if entry_price is None or exit_price is None:
        return None
    try:
        entry_f = float(entry_price)
        exit_f = float(exit_price)
    except (TypeError, ValueError):
        return None
    if entry_f <= 0:
        return None

    pnl_pct = (exit_f - entry_f) / entry_f * 100.0
    return {
        "symbol": symbol,
        "pattern": pattern,
        "rr_regime": rr_regime,
        "pnl_pct": pnl_pct,
        "win": pnl_pct > 0,
    }


# ============================================================================
# Aggregation + statistics
# ============================================================================

def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval — robust at small N."""
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (max(0.0, centre - spread) * 100, min(1.0, centre + spread) * 100)


def chi_square_test(table: dict[str, tuple[int, int]]) -> tuple[float, float]:
    """
    table: {regime: (wins, n)}. Returns (chi2_stat, p_value_approx).
    2x4 contingency table: regime × {win, loss}.
    """
    total_wins = sum(w for w, _ in table.values())
    total_n = sum(n for _, n in table.values())
    if total_n == 0:
        return (0.0, 1.0)
    overall_wr = total_wins / total_n
    chi2 = 0.0
    df = 0
    for regime, (w, n) in table.items():
        if n == 0:
            continue
        exp_w = n * overall_wr
        exp_l = n * (1 - overall_wr)
        if exp_w > 0:
            chi2 += (w - exp_w) ** 2 / exp_w
        if exp_l > 0:
            chi2 += ((n - w) - exp_l) ** 2 / exp_l
        df += 1
    df = max(df - 1, 1)
    # Approximation: rough p-value from chi-square distribution.
    # Use survival function approximation valid for df 1-3.
    # Better: scipy.stats.chi2.sf — but to keep deps light, hand-compute.
    # For df=3 (4 regimes), critical values: 7.815 (p=0.05), 11.345 (p=0.01).
    if df == 3:
        if chi2 > 11.345: p_approx = 0.005
        elif chi2 > 7.815: p_approx = 0.03
        elif chi2 > 6.251: p_approx = 0.10
        else: p_approx = 0.30
    elif df == 2:
        if chi2 > 9.21: p_approx = 0.005
        elif chi2 > 5.991: p_approx = 0.03
        elif chi2 > 4.605: p_approx = 0.10
        else: p_approx = 0.30
    else:
        if chi2 > 6.635: p_approx = 0.005
        elif chi2 > 3.841: p_approx = 0.03
        elif chi2 > 2.706: p_approx = 0.10
        else: p_approx = 0.30
    return (chi2, p_approx)


def summarise(enriched: list[dict]) -> None:
    print()
    print("=" * 78)
    print("PHASE 0b RR CONDITIONAL WR — RESULTS")
    print("=" * 78)
    n_total = len(enriched)
    n_tagged = sum(1 for s in enriched if s["rr_regime"] is not None)
    print(f"Signals attributed (entry+exit option prices found): {n_total}")
    print(f"  of which regime-tagged: {n_tagged}")
    print(f"  untagged (no vol_analytics row at signal_ts): {n_total - n_tagged}")
    if n_tagged == 0:
        print("\n*** No regime-tagged signals — Phase 0b inconclusive. ***")
        return

    # Overall WR baseline
    overall_wins = sum(1 for s in enriched if s["rr_regime"] is not None and s["win"])
    overall_wr = overall_wins / n_tagged * 100
    print(f"\nOverall WR (regime-tagged cohort): {overall_wr:.1f}% (N={n_tagged})")

    # Per-regime table
    regimes_order = ["HIGH", "FAIR", "LOW", "COMPRESSED"]
    print(f"\n{'Regime':<12} {'N':>6} {'Wins':>6} {'WR':>8} {'95% CI':>18} {'vs Baseline':>14} {'Mean P&L':>10}")
    print("-" * 78)
    table_for_chi = {}
    for regime in regimes_order:
        bucket = [s for s in enriched if s["rr_regime"] == regime]
        n = len(bucket)
        if n == 0:
            print(f"{regime:<12} {0:>6} {0:>6} {'—':>8} {'—':>18} {'—':>14} {'—':>10}")
            continue
        wins = sum(1 for s in bucket if s["win"])
        wr = wins / n * 100
        ci_lo, ci_hi = wilson_ci(wins, n)
        diff = wr - overall_wr
        mean_pnl = sum(s["pnl_pct"] for s in bucket) / n
        sign = "+" if diff >= 0 else ""
        print(f"{regime:<12} {n:>6} {wins:>6} {wr:>7.1f}% [{ci_lo:>5.1f}, {ci_hi:>5.1f}] {sign}{diff:>6.1f}pp     {mean_pnl:>+8.2f}%")
        table_for_chi[regime] = (wins, n)

    chi2, p = chi_square_test(table_for_chi)
    print(f"\nChi-square test:  χ² = {chi2:.2f},  p ≈ {p:.3f}")

    # Per-pattern breakdown for diagnostic colour
    print(f"\n--- Per-pattern × regime breakdown ---")
    patterns = ["BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"]
    print(f"{'Pattern':<12} {'Regime':<12} {'N':>5} {'WR':>7} {'Mean P&L':>10}")
    print("-" * 50)
    for pat in patterns:
        for regime in regimes_order:
            bucket = [s for s in enriched if s["pattern"] == pat and s["rr_regime"] == regime]
            n = len(bucket)
            if n == 0:
                continue
            wins = sum(1 for s in bucket if s["win"])
            wr = wins / n * 100
            mean_pnl = sum(s["pnl_pct"] for s in bucket) / n
            print(f"{pat:<12} {regime:<12} {n:>5} {wr:>6.1f}% {mean_pnl:>+8.2f}%")

    # Directional check vs ADR-002 v2 P7 prediction
    print(f"\n--- Verdict (per ADR-002 v2 §P7 falsification commitment) ---")
    high_wr = table_for_chi.get("HIGH", (0, 0))
    low_wr = table_for_chi.get("LOW", (0, 0))
    compressed_wr = table_for_chi.get("COMPRESSED", (0, 0))

    sig_pass = p < 0.05
    high_above = (high_wr[1] >= 30) and ((high_wr[0] / high_wr[1] * 100) > overall_wr) if high_wr[1] > 0 else False
    low_below = (low_wr[1] >= 30) and ((low_wr[0] / low_wr[1] * 100) < overall_wr) if low_wr[1] > 0 else False
    comp_below = (compressed_wr[1] >= 30) and ((compressed_wr[0] / compressed_wr[1] * 100) < overall_wr) if compressed_wr[1] > 0 else False

    print(f"  Statistical significance (p < 0.05):  {'YES' if sig_pass else 'NO'}  (p≈{p:.3f})")
    print(f"  HIGH regime outperforms baseline:     {'YES' if high_above else 'NO'}")
    print(f"  LOW regime underperforms baseline:    {'YES' if low_below else 'NO'}")
    print(f"  COMPRESSED underperforms baseline:    {'YES' if comp_below else 'NO'}")

    direction_ok = high_above and (low_below or comp_below)
    pass_test = sig_pass and direction_ok
    print(f"\n  VERDICT: {'PASS — proceed to ENH-80 build' if pass_test else 'FAIL — ENH-97 pivots to logging-only; ENH-80 deferred'}")
    print("=" * 78)


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    sb = _load_supabase_client()
    signals = fetch_signals(sb)
    if not signals:
        print("No signals in scope. Aborting.")
        return 1
    vol_map = fetch_vol_analytics_map(sb)
    atm_map = fetch_atm_option_map(sb)

    enriched: list[dict] = []
    skipped_no_prices = 0
    for sig in signals:
        result = process_signal(sig, vol_map, atm_map)
        if result is None:
            skipped_no_prices += 1
            continue
        enriched.append(result)

    print(f"\nProcessed {len(signals)} signals: "
          f"{len(enriched)} attributed, {skipped_no_prices} skipped (missing entry/exit prices)")
    summarise(enriched)
    return 0


if __name__ == "__main__":
    sys.exit(main())
