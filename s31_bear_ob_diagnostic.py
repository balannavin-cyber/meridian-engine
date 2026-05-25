"""
s31_bear_ob_diagnostic.py — TD-S31-NEW-1 localization.

Replays the OB detection logic from detect_ict_patterns.py over one
full session's hist_spot_bars_1m, instrumented to log every bearish
and bullish impulse and what happens to it.

Purpose: identify why BEAR_OB emits zero rows over the 4-week
post-S20-deploy window (2026-05-04 onward) while BULL_OB emits a
handful and FVG emits symmetrically (201 BULL / 164 BEAR).

Output per session:
  Bearish impulse pipeline:
    A  bearish impulses (mv <= -0.40%)
    B  of A, at least one bullish anchor exists in lookback range
    C  of B, anchor not in seen set
    D  emitted as BEAR_OB (= C, since branches are mutually exclusive)
  Bullish impulse pipeline:
    A' bullish impulses (mv >= +0.40%)
    B' of A', at least one bearish anchor exists in lookback range
    C' of B', anchor not in seen set
    D' emitted as BULL_OB

Interpretation table:
  A=0      → impulses absent; market didn't move 0.40% in 5 min today
  A>0,B=0  → no bullish bars in lookback; needs lookback widening
             or pre-impulse repositioning
  A>0,B>0,C<B → seen-set blocking BEAR_OB after BULL_OB consumed shared bars
             (mathematically can't happen given strict candle-direction
             check, but instrumented to confirm)
  A>0,B>0,C>0,D<C → bug elsewhere (assignment ordering)

Usage:
    python s31_bear_ob_diagnostic.py --symbol SENSEX --date 2026-05-14
    python s31_bear_ob_diagnostic.py --symbol NIFTY  --date 2026-05-14
    python s31_bear_ob_diagnostic.py --symbol SENSEX --date-range 2026-05-04:2026-05-15
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta, date as _date

from dotenv import load_dotenv
from supabase import create_client

# ── Detector constants — mirror detect_ict_patterns.py exactly ───────

OB_MIN_MOVE_PCT = 0.40   # % impulse for OB qualification (5-bar move)
LOOKBACK_BARS   = 3      # from ICTDetector — diagnostic uses 6-bar OB lookback


# ── Bar dataclass — match detect_ict_patterns.Bar ────────────────────

@dataclass
class Bar:
    bar_ts: datetime
    open: float
    high: float
    low: float
    close: float


def pct(a: float, b: float) -> float:
    return 100.0 * (b - a) / a if a else 0.0


# ── 5-min aggregation (production fix candidate) ─────────────────────

def aggregate_1m_to_5m(bars_1m: list[Bar]) -> list[Bar]:
    """Aggregate 1-min Bar list into 5-min Bar list by floored absolute
    5-min boundary on each bar's bar_ts. OHLC: open=first, high=max,
    low=min, close=last. Drops buckets with fewer than 5 1-min bars to
    avoid partial-trailing noise.
    """
    from collections import defaultdict
    if not bars_1m:
        return []
    buckets: dict = defaultdict(list)
    for b in bars_1m:
        ts = b.bar_ts
        bucket_ts = ts.replace(
            minute=(ts.minute // 5) * 5,
            second=0,
            microsecond=0,
        )
        buckets[bucket_ts].append(b)
    out = []
    for bucket_ts in sorted(buckets):
        items = sorted(buckets[bucket_ts], key=lambda b: b.bar_ts)
        if len(items) < 5:
            continue
        out.append(Bar(
            bar_ts=bucket_ts,
            open=items[0].open,
            high=max(b.high for b in items),
            low=min(b.low for b in items),
            close=items[-1].close,
        ))
    return out


# ── Supabase fetch ───────────────────────────────────────────────────

def fetch_instrument_id(sb, symbol: str) -> str:
    """Look up instrument_id (uuid) from instruments table by symbol."""
    rows = (sb.table("instruments")
            .select("id")
            .eq("symbol", symbol)
            .limit(1)
            .execute().data)
    if not rows:
        raise RuntimeError(f"No instruments row for symbol={symbol}")
    return rows[0]["id"]


def fetch_bars(sb, instrument_id: str, trade_date: str) -> list[Bar]:
    """Pull hist_spot_bars_1m for one instrument_id × date. Returns chronological list."""
    rows = (sb.table("hist_spot_bars_1m")
            .select("bar_ts,open,high,low,close")
            .eq("instrument_id", instrument_id)
            .eq("trade_date", trade_date)
            .order("bar_ts")
            .execute().data)
    out = []
    for r in rows:
        bt = r["bar_ts"]
        if isinstance(bt, str):
            s = bt.replace(" ", "T").replace("+00", "+00:00")
            bt = datetime.fromisoformat(s)
        if bt.tzinfo is None:
            bt = bt.replace(tzinfo=timezone.utc)
        out.append(Bar(
            bar_ts=bt,
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
        ))
    return out


# ── Instrumented detector ────────────────────────────────────────────

def instrumented_detect_obs(bars: list[Bar], verbose: bool = False) -> dict:
    """Runs detect_obs logic over the full bar set with per-impulse tally."""
    n = len(bars)
    seen = set()

    stats = {
        "BEAR_OB": {"impulses": 0, "with_anchor": 0, "not_seen": 0, "emitted": 0,
                    "impulse_examples": [], "lookback_fail_examples": []},
        "BULL_OB": {"impulses": 0, "with_anchor": 0, "not_seen": 0, "emitted": 0,
                    "impulse_examples": [], "lookback_fail_examples": []},
    }

    if n < 7:
        return stats

    for i in range(n - 6):
        end_idx = min(i + 5, n - 1)
        mv = pct(bars[i].close, bars[end_idx].close)

        # ── BEAR_OB path: bearish impulse → look back for bullish anchor ─
        if mv <= -OB_MIN_MOVE_PCT:
            s = stats["BEAR_OB"]
            s["impulses"] += 1
            anchor_found = False
            anchor_j = None
            # Lookback: same as detect_obs in detect_ict_patterns.py
            for j in range(i, max(i - 6, -1), -1):
                if bars[j].close > bars[j].open:
                    anchor_found = True
                    anchor_j = j
                    break
            if anchor_found:
                s["with_anchor"] += 1
                if anchor_j not in seen:
                    s["not_seen"] += 1
                    seen.add(anchor_j)
                    s["emitted"] += 1
                    if len(s["impulse_examples"]) < 3:
                        s["impulse_examples"].append({
                            "i": i, "i_ts": bars[i].bar_ts,
                            "end_ts": bars[end_idx].bar_ts,
                            "mv_pct": round(mv, 3),
                            "anchor_j": anchor_j, "anchor_ts": bars[anchor_j].bar_ts,
                            "anchor_o": bars[anchor_j].open,
                            "anchor_c": bars[anchor_j].close,
                        })
            else:
                if len(s["lookback_fail_examples"]) < 5:
                    # Capture the lookback range candle directions
                    lookback_dirs = []
                    for j in range(i, max(i - 6, -1), -1):
                        d = ("BULL" if bars[j].close > bars[j].open
                             else "BEAR" if bars[j].close < bars[j].open
                             else "DOJI")
                        lookback_dirs.append(f"j={j}({d})")
                    s["lookback_fail_examples"].append({
                        "i": i, "i_ts": bars[i].bar_ts,
                        "mv_pct": round(mv, 3),
                        "lookback_dirs": lookback_dirs,
                    })

        # ── BULL_OB path: bullish impulse → look back for bearish anchor ─
        elif mv >= OB_MIN_MOVE_PCT:
            s = stats["BULL_OB"]
            s["impulses"] += 1
            anchor_found = False
            anchor_j = None
            for j in range(i, max(i - 6, -1), -1):
                if bars[j].close < bars[j].open:
                    anchor_found = True
                    anchor_j = j
                    break
            if anchor_found:
                s["with_anchor"] += 1
                if anchor_j not in seen:
                    s["not_seen"] += 1
                    seen.add(anchor_j)
                    s["emitted"] += 1
                    if len(s["impulse_examples"]) < 3:
                        s["impulse_examples"].append({
                            "i": i, "i_ts": bars[i].bar_ts,
                            "end_ts": bars[end_idx].bar_ts,
                            "mv_pct": round(mv, 3),
                            "anchor_j": anchor_j, "anchor_ts": bars[anchor_j].bar_ts,
                            "anchor_o": bars[anchor_j].open,
                            "anchor_c": bars[anchor_j].close,
                        })
            else:
                if len(s["lookback_fail_examples"]) < 5:
                    lookback_dirs = []
                    for j in range(i, max(i - 6, -1), -1):
                        d = ("BULL" if bars[j].close > bars[j].open
                             else "BEAR" if bars[j].close < bars[j].open
                             else "DOJI")
                        lookback_dirs.append(f"j={j}({d})")
                    s["lookback_fail_examples"].append({
                        "i": i, "i_ts": bars[i].bar_ts,
                        "mv_pct": round(mv, 3),
                        "lookback_dirs": lookback_dirs,
                    })

    return stats


def report_session(symbol: str, trade_date: str, bars: list[Bar], stats: dict) -> None:
    n = len(bars)
    n_bull_bars = sum(1 for b in bars if b.close > b.open)
    n_bear_bars = sum(1 for b in bars if b.close < b.open)
    n_doji = n - n_bull_bars - n_bear_bars

    session_move = pct(bars[0].open, bars[-1].close) if bars else 0.0

    print(f"\n{'=' * 78}")
    print(f"{symbol}  {trade_date}  ({n} bars, "
          f"session move {session_move:+.2f}%)")
    print(f"{'=' * 78}")
    print(f"Candle direction inventory: BULL={n_bull_bars}  "
          f"BEAR={n_bear_bars}  DOJI={n_doji}")
    print()
    print(f"{'Pattern':<10} {'Impulses':>10} {'WithAnchor':>11} "
          f"{'NotInSeen':>10} {'Emitted':>9}")
    print("-" * 78)
    for pat in ("BEAR_OB", "BULL_OB"):
        s = stats[pat]
        print(f"{pat:<10} {s['impulses']:>10} {s['with_anchor']:>11} "
              f"{s['not_seen']:>10} {s['emitted']:>9}")

    # Conversion-rate computation
    print()
    for pat in ("BEAR_OB", "BULL_OB"):
        s = stats[pat]
        if s["impulses"] == 0:
            print(f"{pat}: no impulses today.")
            continue
        anchor_rate = s["with_anchor"] / s["impulses"] * 100
        emit_rate = s["emitted"] / s["impulses"] * 100
        print(f"{pat}: impulse→anchor={anchor_rate:.1f}%  "
              f"impulse→emit={emit_rate:.1f}%")

    # Detail: lookback failures for BEAR_OB (the target pattern)
    bear_fails = stats["BEAR_OB"]["lookback_fail_examples"]
    if bear_fails:
        print()
        print("BEAR_OB lookback failures (sample of up to 5):")
        for ex in bear_fails:
            print(f"  i={ex['i']} ts={ex['i_ts']} mv={ex['mv_pct']}%  "
                  f"lookback={ex['lookback_dirs']}")

    # Detail: BEAR_OB successes (if any)
    bear_emits = stats["BEAR_OB"]["impulse_examples"]
    if bear_emits:
        print()
        print(f"BEAR_OB emissions (sample of up to 3):")
        for ex in bear_emits:
            print(f"  i={ex['i']} mv={ex['mv_pct']}%  "
                  f"anchor j={ex['anchor_j']} ts={ex['anchor_ts']} "
                  f"O={ex['anchor_o']} C={ex['anchor_c']}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True, choices=["NIFTY", "SENSEX"])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--date", help="Single trade_date YYYY-MM-DD")
    g.add_argument("--date-range",
                   help="YYYY-MM-DD:YYYY-MM-DD inclusive (loops sessions)")
    args = p.parse_args()

    load_dotenv()
    sb = create_client(
        os.getenv("SUPABASE_URL").strip(),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
    )

    if args.date:
        dates = [args.date]
    else:
        a, b = args.date_range.split(":")
        d0 = _date.fromisoformat(a)
        d1 = _date.fromisoformat(b)
        dates = []
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:  # Mon-Fri
                dates.append(cur.isoformat())
            cur += timedelta(days=1)

    print(f"BEAR_OB diagnostic — {args.symbol} over {len(dates)} session(s)")

    instrument_id = fetch_instrument_id(sb, args.symbol)
    print(f"Resolved {args.symbol} → instrument_id={instrument_id}")

    totals = {
        "BEAR_OB": Counter(),
        "BULL_OB": Counter(),
    }
    sessions_with_bear_impulse = 0
    sessions_with_bear_emit = 0

    for d in dates:
        bars_1m = fetch_bars(sb, instrument_id, d)
        bars = aggregate_1m_to_5m(bars_1m)
        if bars and not bars_1m:
            pass  # impossible but mypy-safe
        # Report aggregation transparency
        if bars_1m and not bars:
            print(f"\n{args.symbol} {d}: {len(bars_1m)} 1-min bars → "
                  f"0 5-min buckets (insufficient bars per bucket)")
            continue
        if not bars_1m:
            print(f"\n{args.symbol} {d}: no bars (holiday or no data)")
            continue
        stats = instrumented_detect_obs(bars)
        # Annotate the per-session header with aggregation context
        print(f"  (aggregated {len(bars_1m)} 1-min bars → {len(bars)} 5-min bars)")
        report_session(args.symbol, d, bars, stats)
        for pat in ("BEAR_OB", "BULL_OB"):
            for k, v in stats[pat].items():
                if isinstance(v, int):
                    totals[pat][k] += v
        if stats["BEAR_OB"]["impulses"] > 0:
            sessions_with_bear_impulse += 1
        if stats["BEAR_OB"]["emitted"] > 0:
            sessions_with_bear_emit += 1

    # Aggregate
    if len(dates) > 1:
        print(f"\n{'=' * 78}")
        print(f"AGGREGATE — {args.symbol}, {len(dates)} sessions")
        print(f"{'=' * 78}")
        print(f"Sessions with at least one bearish impulse: {sessions_with_bear_impulse}/{len(dates)}")
        print(f"Sessions that emitted a BEAR_OB:            {sessions_with_bear_emit}/{len(dates)}")
        print()
        print(f"{'Pattern':<10} {'Impulses':>10} {'WithAnchor':>11} "
              f"{'NotInSeen':>10} {'Emitted':>9}")
        print("-" * 78)
        for pat in ("BEAR_OB", "BULL_OB"):
            t = totals[pat]
            print(f"{pat:<10} {t['impulses']:>10} {t['with_anchor']:>11} "
                  f"{t['not_seen']:>10} {t['emitted']:>9}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
