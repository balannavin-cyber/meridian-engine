"""
diag_td056_raw_vs_tiered_counts.py
==================================
TD-056 Phase 1B closeout diagnostic.

Measures BULL_OB / BEAR_OB count asymmetry at THREE checkpoints, split by
session-direction regime, on the full-year hist_spot_bars_1m cohort.

PHASE 1B CADENCE: sliding-window detection matching Exp 15
(experiment_15_pure_ict_compounding.py L415-437):

    for pat_idx in range(10, len(bars)):
        if bar.bar_ts.time() >= POWER_HOUR: break
        window_bars = bars[max(0, pat_idx - 10) : pat_idx + 1]   # 11-bar trailing
        patterns = detector.detect(bars=window_bars, ...)
        for pat in patterns:
            dedupe by (bar_ts, pattern_type)
            count at C1, C2, C3

Phase 1A used a single per-session detect_obs call which structurally
undercounted by ~10x and gave N=24 raw OBs across 486 sessions.

Checkpoints
-----------
  C1_raw       OB returned by ICTDetector.detect() (wrapper applies
               POWER_HOUR gate internally; we count after dedupe)
  C2_post_tier same OBs counted again -- wrapper assigns tier inline
               (kept for symmetry with Phase 1A reports)
  C3_trades    after tier != SKIP filter (= the Exp 15 trade cohort)

Regime split (per-session)
--------------------------
  DOWN     session ret % = (close - open)/open * 100  <= -0.30%
  UP       >= +0.30%
  NEUTRAL  in between

Decision rule (Wilson 95% CI on bull-share at C1 raw)
-----------------------------------------------------
  CI upper bound <= 55%        -> H2 refuted     (raw symmetric or BEAR-leaning)
  CI lower bound >= 65%        -> H2 confirmed   (raw BULL-skewed)
  Otherwise + N >= thresholds  -> ambiguous; needs sub-split
  N below thresholds           -> insufficient

Run
---
    cd C:\\GammaEnginePython
    python diag_td056_raw_vs_tiered_counts.py
    # quick smoke (~1 min):
    python diag_td056_raw_vs_tiered_counts.py --limit-days 30

Output
------
    stdout: progress + final markdown table
    file  : C:\\GammaEnginePython\\diagnostics\\td056_<stamp>.md

Per CLAUDE.md
-------------
    Rule 15  Supabase paginates at 1000 rows; fetch_bars uses page_size=1000.
    Rule 16  hist_spot_bars_1m bar_ts is proper UTC; converted to IST-naive.
    Rule 21  caller should pipe to Tee-Object for archival.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------- Imports from the live detector ----------
sys.path.insert(0, str(Path(__file__).parent))
try:
    from detect_ict_patterns import (
        Bar,
        ICTDetector,
        POWER_HOUR,
    )
except ImportError as e:
    sys.exit(f"FATAL: cannot import from detect_ict_patterns -- run from "
             f"C:\\GammaEnginePython\\ ({e})")

# ---------- Constants ----------
IST = ZoneInfo("Asia/Kolkata")
SYMBOLS_DEFAULT = ["NIFTY", "SENSEX"]

# Canonical mapping from `instruments` table (verified Session 18 lookup).
# hist_spot_bars_1m.instrument_id is FK to instruments.id.
SYMBOL_TO_INSTRUMENT_ID = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

DOWN_THRESHOLD = -0.30   # session ret % <= this -> DOWN
UP_THRESHOLD   =  0.30   # session ret % >= this -> UP
                         # else -> NEUTRAL

OUT_DIR = Path(r"C:\GammaEnginePython\diagnostics")

# ---------- Supabase ----------
try:
    from supabase import create_client
except ImportError:
    sys.exit("FATAL: supabase-py not installed. pip install supabase")


def _load_dotenv() -> None:
    dotenv = Path(r"C:\GammaEnginePython\.env")
    if not dotenv.exists():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()
_url = os.environ.get("SUPABASE_URL")
_key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY"))
if not _url or not _key:
    sys.exit("FATAL: SUPABASE_URL or SUPABASE_(SERVICE_ROLE_)KEY not set")
sb = create_client(_url, _key)


# ---------- Helpers ----------
def to_ist_naive(ts) -> datetime:
    """
    Supabase timestamptz -> IST-naive datetime.
    detect_ict_patterns.time_zone_label treats naive datetimes as already-IST,
    so this gives consistent downstream behavior.
    """
    if isinstance(ts, str):
        # Supabase returns "2026-04-15T03:45:00+00:00" or similar
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        return ts
    return ts.astimezone(IST).replace(tzinfo=None)


def fetch_bars(symbol: str, day: date) -> list[Bar]:
    """
    Paginated 1m-bar fetch for one trading session per CLAUDE.md Rule 15.
    Empty list if the session has no rows (holiday / not-yet-captured).

    Schema (verified Session 18):
        hist_spot_bars_1m has instrument_id (UUID FK to instruments.id),
        not a symbol column. We translate via SYMBOL_TO_INSTRUMENT_ID.

    is_pre_market filter: excluded so detector sees only the cash-market
    session (09:15+). detect_obs's range(n-6) loop is symmetric on bar
    indices, so leaving pre-market bars in shifts the loop start without
    changing OB direction balance -- but the cleaner cohort is intraday
    only, matching how the live runner sees bars during 09:15-15:30.
    """
    instrument_id = SYMBOL_TO_INSTRUMENT_ID.get(symbol)
    if instrument_id is None:
        return []
    bars: list[Bar] = []
    page_size = 1000
    offset = 0
    while True:
        res = (
            sb.table("hist_spot_bars_1m")
            .select("bar_ts, open, high, low, close, trade_date, is_pre_market")
            .eq("instrument_id", instrument_id)
            .eq("trade_date", str(day))
            .eq("is_pre_market", False)
            .order("bar_ts")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = res.data or []
        for r in rows:
            try:
                bars.append(Bar(
                    bar_ts     = to_ist_naive(r["bar_ts"]),
                    open       = float(r["open"]),
                    high       = float(r["high"]),
                    low        = float(r["low"]),
                    close      = float(r["close"]),
                    trade_date = day,
                ))
            except (KeyError, TypeError, ValueError):
                continue
        if len(rows) < page_size:
            break
        offset += page_size
    return bars


def session_regime(bars: list[Bar]) -> str:
    """Classify session by total move from first bar's open to last bar's close."""
    if len(bars) < 2:
        return "UNKNOWN"
    open_px = bars[0].open
    close_px = bars[-1].close
    if open_px == 0:
        return "UNKNOWN"
    pct = 100.0 * (close_px - open_px) / open_px
    if pct <= DOWN_THRESHOLD:
        return "DOWN"
    if pct >= UP_THRESHOLD:
        return "UP"
    return "NEUTRAL"


def calendar_weekdays(start_d: date, end_d: date) -> list[date]:
    """Mon-Fri days in [start_d, end_d]. Holidays surface as empty fetches."""
    days = []
    cur = start_d
    while cur <= end_d:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


# ---------- Counters ----------
class CountTable:
    """
    checkpoint -> regime -> direction -> count
    Direction key: 'BULL' or 'BEAR'.
    Regime keys:   'DOWN', 'NEUTRAL', 'UP', 'UNKNOWN', 'ALL'.
    """
    def __init__(self) -> None:
        self._t: dict = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

    def inc(self, ckpt: str, regime: str, direction: str, n: int = 1) -> None:
        self._t[ckpt][regime][direction] += n
        if regime != "ALL":
            self._t[ckpt]["ALL"][direction] += n

    def get(self, ckpt: str, regime: str, direction: str) -> int:
        return self._t[ckpt][regime][direction]


# ---------- Core processing ----------
def process_session(
    symbol: str,
    day: date,
    table: CountTable,
    sessions_per_regime: dict,
) -> bool:
    """
    Returns True if the session was processed (non-empty bars).

    Cadence (matches Exp 15 experiment_15_pure_ict_compounding.py L415-437):
      - For each pat_idx in range(10, len(bars)):
          - break if bar.bar_ts.time() >= POWER_HOUR
          - window_bars = bars[max(0, pat_idx - 10) : pat_idx + 1]   # 11-bar trailing
          - patterns = detector.detect(bars=window_bars, atm_iv=None,
                                       htf_zones=[], prior_high=ph, prior_low=pl)
          - For each OB pattern returned, dedupe by (bar_ts, pattern_type):
              * count once at C1 raw
              * compute tier on this detection's seq features and count at C2
              * if tier != SKIP, count at C3
    Deduplication by (bar_ts, pattern_type) ensures the same physical OB,
    re-detected as the window slides forward, is counted once -- consistent
    with Exp 15's seen_bar_ts pattern at L409.
    """
    bars = fetch_bars(symbol, day)
    if len(bars) < 30:
        return False
    regime = session_regime(bars)
    sessions_per_regime[regime] = sessions_per_regime.get(regime, 0) + 1
    sessions_per_regime["ALL"] = sessions_per_regime.get("ALL", 0) + 1

    detector = ICTDetector(symbol=symbol)
    seen_ob_keys: set = set()       # dedupe set: (bar_ts, pattern_type)

    # Per-bar sliding window, matching Exp 15
    for pat_idx in range(10, len(bars)):
        bar = bars[pat_idx]
        if bar.bar_ts.time() >= POWER_HOUR:
            break
        start = max(0, pat_idx - 10)
        window_bars = bars[start: pat_idx + 1]

        # Run the full wrapper so POWER_HOUR + tier semantics match Exp 15
        # (htf_zones=[] -> mtf_context defaults to LOW; we don't read it).
        try:
            patterns = detector.detect(
                bars=window_bars,
                atm_iv=None,
                htf_zones=[],
                prior_high=None,
                prior_low=None,
            )
        except Exception:
            continue

        for pat in patterns:
            if pat.pattern_type not in ("BULL_OB", "BEAR_OB"):
                continue

            key = (pat.bar_ts, pat.pattern_type)
            if key in seen_ob_keys:
                continue
            seen_ob_keys.add(key)

            direction = "BULL" if pat.pattern_type == "BULL_OB" else "BEAR"
            tier = pat.ict_tier  # already computed inside the wrapper

            table.inc("C1_raw", regime, direction)
            table.inc("C2_post_tier", regime, direction)
            if tier != "SKIP":
                table.inc("C3_trades", regime, direction)

    return True


# ---------- Reporting ----------
def _ratio(b: int, r: int) -> float:
    if r == 0:
        return float("inf") if b > 0 else 0.0
    return b / r


def _ratio_str(b: int, r: int) -> str:
    if r == 0:
        return "inf" if b > 0 else "0.00x"
    return f"{b / r:.2f}x"


def _wilson_bull_share_ci(bull: int, bear: int, z: float = 1.96) -> tuple[float, float]:
    """
    Wilson score 95% CI for bull share = bull / (bull + bear).
    Returns (lo, hi) in [0, 1]. Returns (0, 1) if total is 0.
    """
    n = bull + bear
    if n == 0:
        return (0.0, 1.0)
    p = bull / n
    denom = 1.0 + (z * z) / n
    centre = (p + (z * z) / (2 * n)) / denom
    half = (z * ((p * (1 - p) / n + (z * z) / (4 * n * n)) ** 0.5)) / denom
    lo = max(0.0, centre - half)
    hi = min(1.0, centre + half)
    return (lo, hi)


# Minimum N gates for verdict reliability
MIN_N_FOR_VERDICT_BEAR = 10
MIN_N_FOR_VERDICT_TOTAL = 30


def render_markdown(
    table: CountTable,
    sessions_per_regime: dict,
    args,
    symbols: list,
) -> str:
    L = []
    L.append("# TD-056 Phase 1 -- raw vs tiered OB count diagnostic")
    L.append("")
    L.append(f"**Run:** {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    L.append(f"**Window:** {args.start} -> {args.end}")
    L.append(f"**Symbols:** {', '.join(symbols)}")
    L.append(f"**Sessions:** "
             f"{sessions_per_regime.get('ALL', 0)} total "
             f"({sessions_per_regime.get('DOWN', 0)} DOWN / "
             f"{sessions_per_regime.get('NEUTRAL', 0)} NEUTRAL / "
             f"{sessions_per_regime.get('UP', 0)} UP)")
    L.append(f"**Regime split:** DOWN <= {DOWN_THRESHOLD}% < NEUTRAL "
             f"< {UP_THRESHOLD}% <= UP")
    L.append("")
    L.append("## Counts by checkpoint x regime x direction")
    L.append("")
    L.append("| Checkpoint | Regime | BULL_OB | BEAR_OB | Bull/Bear |")
    L.append("|---|---|---:|---:|---:|")

    regimes = ["ALL", "DOWN", "NEUTRAL", "UP"]
    checkpoints = ["C1_raw", "C2_post_tier", "C3_trades"]

    for ckpt in checkpoints:
        for reg in regimes:
            b = table.get(ckpt, reg, "BULL")
            r = table.get(ckpt, reg, "BEAR")
            L.append(f"| {ckpt} | {reg} | {b} | {r} | {_ratio_str(b, r)} |")

    # ---- Interpretation ----
    L.append("")
    L.append("## Interpretation")
    L.append("")

    c1_d_b = table.get("C1_raw", "DOWN", "BULL")
    c1_d_r = table.get("C1_raw", "DOWN", "BEAR")
    c3_d_b = table.get("C3_trades", "DOWN", "BULL")
    c3_d_r = table.get("C3_trades", "DOWN", "BEAR")
    c1_d = _ratio(c1_d_b, c1_d_r)
    c3_d = _ratio(c3_d_b, c3_d_r)

    c1_all_b = table.get("C1_raw", "ALL", "BULL")
    c1_all_r = table.get("C1_raw", "ALL", "BEAR")
    c3_all_b = table.get("C3_trades", "ALL", "BULL")
    c3_all_r = table.get("C3_trades", "ALL", "BEAR")

    L.append(f"- **C1 raw, DOWN regime:** {_ratio_str(c1_d_b, c1_d_r)} "
             f"(BULL={c1_d_b}, BEAR={c1_d_r})")
    L.append(f"- **C3 trades, DOWN regime:** {_ratio_str(c3_d_b, c3_d_r)} "
             f"(BULL={c3_d_b}, BEAR={c3_d_r}) -- "
             f"TD-056 measured ~3.29x for NIFTY DOWN")
    L.append(f"- **C1 raw, ALL regimes:** {_ratio_str(c1_all_b, c1_all_r)} "
             f"(BULL={c1_all_b}, BEAR={c1_all_r})")
    L.append(f"- **C3 trades, ALL regimes:** {_ratio_str(c3_all_b, c3_all_r)} "
             f"(BULL={c3_all_b}, BEAR={c3_all_r}) -- "
             f"Exp 15 measured 49/25 = 1.96x")
    L.append("")

    # Wilson 95% CI on bull-share at C1 raw level (most diagnostic checkpoint)
    c1_d_lo, c1_d_hi = _wilson_bull_share_ci(c1_d_b, c1_d_r)
    c1_a_lo, c1_a_hi = _wilson_bull_share_ci(c1_all_b, c1_all_r)
    L.append(f"- **Bull-share Wilson 95% CI:**")
    L.append(f"  - C1 raw DOWN:  [{c1_d_lo*100:.1f}%, {c1_d_hi*100:.1f}%] "
             f"(point estimate {100*c1_d_b/(c1_d_b+c1_d_r) if (c1_d_b+c1_d_r) else 0:.1f}%)")
    L.append(f"  - C1 raw ALL:   [{c1_a_lo*100:.1f}%, {c1_a_hi*100:.1f}%] "
             f"(point estimate {100*c1_all_b/(c1_all_b+c1_all_r) if (c1_all_b+c1_all_r) else 0:.1f}%)")
    L.append("  - Symmetric (no skew) bull-share = 50%. CI containing 50% "
             "means we cannot reject symmetry at this N.")
    L.append("")

    # ---- N-gated verdict ----
    n_bear_total = c1_all_r
    n_total = c1_all_b + c1_all_r
    n_bear_down = c1_d_r
    n_down_total = c1_d_b + c1_d_r

    insufficient_total = (n_bear_total < MIN_N_FOR_VERDICT_BEAR
                          or n_total < MIN_N_FOR_VERDICT_TOTAL)
    insufficient_down = (n_bear_down < MIN_N_FOR_VERDICT_BEAR
                         or n_down_total < MIN_N_FOR_VERDICT_TOTAL)

    if insufficient_total or insufficient_down:
        L.append(f"**Verdict: INSUFFICIENT N for confident conclusion.**")
        L.append(f"")
        L.append(f"- Need >= {MIN_N_FOR_VERDICT_BEAR} BEAR_OB raw candidates "
                 f"and >= {MIN_N_FOR_VERDICT_TOTAL} total candidates "
                 f"in the regime under scrutiny.")
        L.append(f"- C1 raw ALL:  BEAR={n_bear_total} (need {MIN_N_FOR_VERDICT_BEAR}), "
                 f"total={n_total} (need {MIN_N_FOR_VERDICT_TOTAL})")
        L.append(f"- C1 raw DOWN: BEAR={n_bear_down} (need {MIN_N_FOR_VERDICT_BEAR}), "
                 f"total={n_down_total} (need {MIN_N_FOR_VERDICT_TOTAL})")
        L.append(f"")
        L.append(f"Re-run on a wider window. If running --limit-days, drop the flag.")
        L.append(f"")
        L.append(f"At observed counts, the C1 DOWN bull-share point estimate is "
                 f"{100*c1_d_b/(c1_d_b+c1_d_r) if (c1_d_b+c1_d_r) else 0:.1f}% "
                 f"with 95% CI [{c1_d_lo*100:.1f}%, {c1_d_hi*100:.1f}%]. The CI "
                 f"{'INCLUDES' if c1_d_lo <= 0.5 <= c1_d_hi else 'EXCLUDES'} "
                 f"symmetric (50%) -- so even with this small N, the data "
                 f"{'cannot' if c1_d_lo <= 0.5 <= c1_d_hi else 'can'} reject "
                 f"the null hypothesis of symmetric raw detection.")
    elif c1_d_hi <= 0.55:
        # Upper bound of CI <= 55% -> raw is symmetric or near-symmetric
        L.append("**Verdict: H2 refuted at raw level.** `detect_obs` produces "
                 "approximately symmetric BULL/BEAR candidates in DOWN regime "
                 f"(95% CI upper bound {c1_d_hi*100:.1f}%). The TD-056 "
                 "measured skew at the trade-cohort level is fully "
                 "explained by intentional, evidence-backed asymmetry in "
                 "`assign_tier`:")
        L.append("")
        L.append("- BEAR_OB AFTNOON -> SKIP (ENH-64, 17% WR, Exp 8)")
        L.append("- BEAR_OB IMP_STR -> SKIP (Exp 8 -7.4% expectancy)")
        L.append("- BULL_OB IMP_STR -> TIER2 (kept; expectancy still positive)")
        L.append("")
        L.append("**TD-056 reclassifies as 'measurement framing artifact, "
                 "not detector bug.'** Phase 2 patch not warranted. "
                 "Recommendation: close TD-056 with this finding documented "
                 "in tech_debt.md and CLAUDE.md (under Rule 22 cluster).")
    elif c1_d_lo >= 0.65:
        # Lower bound of CI >= 65% -> real raw asymmetry
        L.append("**Verdict: H2 confirmed at raw level.** `detect_obs` itself "
                 "produces directionally skewed candidates in DOWN regime "
                 f"(95% CI [{c1_d_lo*100:.1f}%, {c1_d_hi*100:.1f}%], "
                 "fully above 50%). Bug is upstream of `assign_tier`. "
                 "Drill targets:")
        L.append("")
        L.append("- 5-bar +/- 0.40% impulse threshold may interact "
                 "asymmetrically with directional volatility (bears move "
                 "faster than bulls, exit the 5-bar window).")
        L.append("- `seen` set first-come-first-served bar-index claim "
                 "between BEAR and BULL impulse loops.")
        L.append("- Lookback range `range(i, max(i-6, -1), -1)` candle-color "
                 "predicate `bars[j].close > bars[j].open` (BEAR) vs "
                 "`<` (BULL) -- structurally mirrored, but worth confirming "
                 "no off-by-one in DOWN-regime data.")
    else:
        L.append(f"**Verdict: ambiguous.** Bull-share CI [{c1_d_lo*100:.1f}%, "
                 f"{c1_d_hi*100:.1f}%] does not cleanly clear 55% (refute) or "
                 "65% (confirm). Need wider N or more granular split. Next phase:")
        L.append("")
        L.append("- Split C1 skew by `tz_label` (does the residual concentrate "
                 "in MORNING or AFTNOON?)")
        L.append("- Split C1 skew by `imp_str` (does it concentrate in "
                 "fast-move bars?)")
        L.append("- If concentrated, look for the asymmetric sub-condition.")

    L.append("")
    L.append("## Notes")
    L.append("")
    L.append("- `prior_high` and `prior_low` were not threaded through to "
             "`compute_sequence_features` -- they only feed `has_prior_sweep` "
             "which is informational, not consumed by `assign_tier`. Counts "
             "are unaffected.")
    L.append("- `atm_iv` was passed as None -- only `BULL_FVG` reads it in "
             "`assign_tier`. OB tier counts are unaffected.")
    L.append("- POWER_HOUR gate applied at C1 to match Exp 15 cohort scope "
             "(Exp 15's `time < POWER_HOUR` filter).")

    return "\n".join(L)


# ---------- Main ----------
def main() -> int:
    p = argparse.ArgumentParser()
    today = date.today()
    default_start = (today - timedelta(days=365)).isoformat()
    default_end   = (today - timedelta(days=1)).isoformat()
    p.add_argument("--start", default=default_start,
                   help=f"start date inclusive (default {default_start})")
    p.add_argument("--end", default=default_end,
                   help=f"end date inclusive (default {default_end})")
    p.add_argument("--symbols", default=",".join(SYMBOLS_DEFAULT),
                   help="comma-separated symbols (default NIFTY,SENSEX)")
    p.add_argument("--limit-days", type=int, default=None,
                   help="cap session days (for quick test runs)")
    p.add_argument("--progress-every", type=int, default=20)
    args = p.parse_args()

    start_d = date.fromisoformat(args.start)
    end_d   = date.fromisoformat(args.end)
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    days = calendar_weekdays(start_d, end_d)
    if args.limit_days:
        days = days[-args.limit_days:]
    print(f"[td056-diag] window {start_d} -> {end_d} | "
          f"{len(days)} weekdays | symbols {symbols}", flush=True)

    table = CountTable()
    sessions_per_regime: dict = {}
    processed = 0
    skipped_empty = 0

    for i, d in enumerate(days):
        for sym in symbols:
            try:
                ok = process_session(sym, d, table, sessions_per_regime)
                if ok:
                    processed += 1
                else:
                    skipped_empty += 1
            except Exception as e:
                print(f"[td056-diag]   WARN [{sym} {d}]: {e}",
                      file=sys.stderr, flush=True)

        if (i + 1) % args.progress_every == 0:
            print(f"[td056-diag]   ... day {i + 1}/{len(days)} "
                  f"({processed} sessions processed, "
                  f"{skipped_empty} empty/holiday)", flush=True)

    print(f"[td056-diag] done: {processed} sessions processed, "
          f"{skipped_empty} empty/holiday days", flush=True)
    md = render_markdown(table, sessions_per_regime, args, symbols)

    # Print to stdout (operator can scroll)
    print()
    print(md)

    # And persist
    stamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"td056_{stamp}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n[td056-diag] written: {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
