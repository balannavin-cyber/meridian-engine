"""
s31_exp41b_replication.py — replicate Exp 41B (E4 + E5) on current data.

The user's question: do old experimental findings replicate when we re-run
them with current zone identification + current data?

Test case: Exp 41B E4 (BEAR_OB MIDDAY + PO3_BEARISH) and E5 (BULL_OB
AFTERNOON + PO3_BULLISH). Originals:

  E4 NIFTY:  N=6  WR=83.3%  mean_win=20.6 pts  mean_loss=2.2 pts   EV=+16.8 pts
  E4 SENSEX: N=11 WR=90.9%  mean_win=133.7 pts mean_loss=55.3 pts  EV=+116.5 pts
  E4 Counter (BEAR_OB MIDDAY + PO3_BULLISH session): N=56 WR=50.0% (baseline noise)
  E5 SENSEX: N=19 WR=73.7%                                         EV=+35.5 pts

Replication methodology:
  - Cohort: 2026-03-23 to 2026-05-15 (same 8-wk window everyone's using)
  - Source: ict_zones (intraday detections); each row is one OB anchor event
  - MIDDAY: detected_at_ts time-of-day in [11:30, 13:30) IST
  - AFTERNOON: time-of-day in [13:30, 15:00) IST
  - PO3 lookup: po3_session_state by trade_date
  - Outcome: spot move from detected_at_ts to detected_at_ts + 30min,
    measured in spot points (Exp 41B native unit)
  - For BEAR_OB: win = spot dropped (move < 0)
  - For BULL_OB: win = spot rose (move > 0)

NOTE: ict_zones is sparse pre-2026-04-22 (TD-067 — no historical intraday
detector backfill). BEAR_OB was structurally zero pre-S31 5m-aggregation
fix (deployed 2026-05-17). Replication N will be much smaller than the
original Exp 41B cohort.

LIVE DATA ONLY. Reads from ict_zones, po3_session_state, hist_spot_bars_1m,
instruments. Does NOT read signal_snapshots.ict_pattern (backfilled).

Usage:
    python s31_exp41b_replication.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date as _date

from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
_MS_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")

START_DATE = "2026-03-23"
END_DATE   = "2026-05-15"
SYMBOLS    = ("NIFTY", "SENSEX")

MIDDAY_START_MIN    = 11 * 60 + 30   # 11:30 IST in mins
MIDDAY_END_MIN      = 13 * 60 + 30   # 13:30 IST
AFTERNOON_START_MIN = 13 * 60 + 30
AFTERNOON_END_MIN   = 15 * 60       # 15:00 IST

EXIT_OFFSET_MIN = 30
BAR_TOL_MIN     = 2


# ── Supabase ──────────────────────────────────────────────────────────

load_dotenv()
SB = create_client(
    os.getenv("SUPABASE_URL").strip(),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
)


# ── TS helpers ────────────────────────────────────────────────────────

def _norm_us(s):
    m = _MS_RE.search(s)
    if not m: return s
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6: return s
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MS_RE.sub(f".{frac6}{tz}", s)


def parse_ts(s):
    if not s: return None
    s = _norm_us(str(s).replace(" ", "T").replace("Z", "+00:00"))
    if s.endswith("+00"): s = s[:-3] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt


def ist_minute_of_day(ts_utc):
    """Return minute-of-day in IST (0-1439)."""
    ist = ts_utc.astimezone(IST)
    return ist.hour * 60 + ist.minute


def ist_date(ts_utc):
    return ts_utc.astimezone(IST).date().isoformat()


# ── Static fetches ────────────────────────────────────────────────────

def fetch_instrument_id(symbol):
    rows = (SB.table("instruments").select("id")
            .eq("symbol", symbol).limit(1).execute().data) or []
    return rows[0]["id"] if rows else None


def fetch_zones(symbol, pattern):
    """All ict_zones in cohort window for (symbol, pattern_type)."""
    rows = (SB.table("ict_zones")
            .select("id,trade_date,pattern_type,direction,zone_low,zone_high,"
                    "detected_at_ts,status")
            .eq("symbol", symbol).eq("pattern_type", pattern)
            .gte("trade_date", START_DATE).lte("trade_date", END_DATE)
            .order("detected_at_ts").execute().data) or []
    return rows


def fetch_po3_for_dates(symbol, dates):
    out = {}
    for d in dates:
        try:
            r = (SB.table("po3_session_state")
                 .select("po3_session_bias")
                 .eq("symbol", symbol).eq("trade_date", d)
                 .execute().data) or []
            out[d] = r[0]["po3_session_bias"] if r else "PO3_NONE"
        except Exception:
            out[d] = "PO3_NONE"
    return out


def fetch_bar_at(inst_id, target_ts):
    """Find 1-min bar closest to target_ts within ±BAR_TOL_MIN.
    Returns dict with open/high/low/close or None."""
    lo = (target_ts - timedelta(minutes=BAR_TOL_MIN)).isoformat()
    hi = (target_ts + timedelta(minutes=BAR_TOL_MIN)).isoformat()
    try:
        rows = (SB.table("hist_spot_bars_1m")
                .select("bar_ts,open,high,low,close")
                .eq("instrument_id", inst_id)
                .eq("is_pre_market", False)
                .gte("bar_ts", lo).lte("bar_ts", hi)
                .order("bar_ts").execute().data) or []
    except Exception:
        return None
    if not rows: return None
    best, best_d = None, None
    for r in rows:
        bt = parse_ts(r["bar_ts"])
        if bt is None: continue
        d = abs((bt - target_ts).total_seconds())
        if best_d is None or d < best_d:
            best_d, best = d, r
    return best


# ── Per-zone outcome ─────────────────────────────────────────────────

def compute_outcome(zone, inst_id, pattern_dir):
    """Return dict with detected_ts, entry_spot, exit_spot, move_pts, win.
    pattern_dir: -1 for BEAR_OB (win when move<0), +1 for BULL_OB (win when move>0).
    """
    det_ts = parse_ts(zone.get("detected_at_ts"))
    if det_ts is None: return None
    entry_bar = fetch_bar_at(inst_id, det_ts)
    if entry_bar is None: return None
    exit_bar  = fetch_bar_at(inst_id, det_ts + timedelta(minutes=EXIT_OFFSET_MIN))
    if exit_bar is None: return None
    try:
        es = float(entry_bar["close"])
        xs = float(exit_bar["close"])
    except (TypeError, ValueError):
        return None
    move = xs - es  # positive = up
    win = (move < 0) if pattern_dir < 0 else (move > 0)
    return {
        "detected_ts": det_ts,
        "entry_spot": es,
        "exit_spot": xs,
        "move_pts": move,
        "win": win,
    }


# ── Bucket aggregator ────────────────────────────────────────────────

def summarize(rows, pattern_dir):
    """Compute WR, mean win pts, mean loss pts, EV per trade.
    pattern_dir interpretation:
      -1 (BEAR_OB): win_pts = -move_pts (price fell, +abs(move))
                   loss_pts = +move_pts (price rose, +abs(move))
      +1 (BULL_OB): win_pts = +move_pts
                   loss_pts = -move_pts
    Both expressed as POSITIVE point magnitudes in the favorable / adverse direction.
    """
    n = len(rows)
    if n == 0:
        return None
    wins = [r for r in rows if r["win"]]
    losses = [r for r in rows if not r["win"]]
    nw, nl = len(wins), len(losses)
    wr = nw / n * 100 if n else 0
    if pattern_dir < 0:
        mw = sum(-r["move_pts"] for r in wins) / nw if nw else 0
        ml = sum(r["move_pts"] for r in losses) / nl if nl else 0
    else:
        mw = sum(r["move_pts"] for r in wins) / nw if nw else 0
        ml = sum(-r["move_pts"] for r in losses) / nl if nl else 0
    ev = (wr / 100) * mw - (1 - wr / 100) * ml
    return {"n": n, "wr": wr, "wins": nw, "losses": nl,
            "mean_win": mw, "mean_loss": ml, "ev": ev}


def fmt(b, label):
    if b is None:
        return f"  {label:<55} N=  0  (no priced events)"
    return (f"  {label:<55} "
            f"N={b['n']:>3}  WR={b['wr']:>5.1f}%  "
            f"win={b['mean_win']:>6.1f}pts  "
            f"loss={b['mean_loss']:>6.1f}pts  "
            f"EV={b['ev']:>+7.1f}pts")


# ── Test runner ──────────────────────────────────────────────────────

def run_test(label, pattern, pattern_dir, time_window, po3_required, original):
    """Test one Exp 41B condition.
    time_window: ('MIDDAY' or 'AFTERNOON')
    po3_required: 'PO3_BEARISH' | 'PO3_BULLISH' | None (for counter test)
    """
    print()
    print("=" * 100)
    print(f"TEST: {label}")
    print(f"  Pattern: {pattern}  Window: {time_window}  PO3 required: {po3_required}")
    print(f"  Original Exp 41B: {original}")
    print("=" * 100)

    if time_window == "MIDDAY":
        tw_start, tw_end = MIDDAY_START_MIN, MIDDAY_END_MIN
    else:
        tw_start, tw_end = AFTERNOON_START_MIN, AFTERNOON_END_MIN

    for symbol in SYMBOLS:
        inst_id = fetch_instrument_id(symbol)
        if inst_id is None:
            print(f"\n{symbol}: no instrument row, skipping")
            continue
        zones = fetch_zones(symbol, pattern)
        if not zones:
            print(f"\n{symbol}: no {pattern} zones in ict_zones for cohort window")
            continue

        # Filter by detected_at_ts time-of-day
        in_window = []
        for z in zones:
            det = parse_ts(z.get("detected_at_ts"))
            if det is None: continue
            m = ist_minute_of_day(det)
            if tw_start <= m < tw_end:
                in_window.append(z)
        if not in_window:
            print(f"\n{symbol}: {len(zones)} {pattern} zones but 0 fall inside "
                  f"{time_window} ({tw_start//60:02d}:{tw_start%60:02d}-"
                  f"{tw_end//60:02d}:{tw_end%60:02d} IST)")
            continue

        # Fetch PO3 for relevant dates
        dates = sorted({z["trade_date"] for z in in_window})
        po3 = fetch_po3_for_dates(symbol, dates)

        # Filter by PO3 condition
        if po3_required is None:
            filtered = in_window
            bucket_label = "ALL (any PO3)"
        elif po3_required == "ANY_NOT_MATCH":
            # the counter test: BEAR_OB MIDDAY + (PO3 != PO3_BEARISH)
            # In Exp 41B's framing, "Counter (PO3_BULLISH session)" specifically
            filtered = [z for z in in_window
                        if po3.get(z["trade_date"]) == "PO3_BULLISH"]
            bucket_label = "Counter (PO3_BULLISH)"
        else:
            filtered = [z for z in in_window
                        if po3.get(z["trade_date"]) == po3_required]
            bucket_label = po3_required

        if not filtered:
            print(f"\n{symbol}: {len(in_window)} {pattern} {time_window} zones "
                  f"but 0 on {po3_required or 'any'} days")
            continue

        # Compute outcomes
        outcomes = []
        for z in filtered:
            o = compute_outcome(z, inst_id, pattern_dir)
            if o is not None:
                outcomes.append(o)

        priced = len(outcomes)
        b = summarize(outcomes, pattern_dir)
        print(f"\n{symbol}:")
        print(f"  {pattern} detections in cohort: {len(zones)}")
        print(f"  In {time_window} window:        {len(in_window)}")
        print(f"  After PO3 filter ({bucket_label}): {len(filtered)}")
        print(f"  Priced (1m bar lookup OK):       {priced}")
        print(fmt(b, f"RESULT: {pattern} {time_window} + {bucket_label}"))


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("S31 Exp 41B replication test")
    print(f"Cohort: {START_DATE} to {END_DATE}")
    print()
    print("Re-runs three conditions from Exp 41B against current ict_zones detections:")
    print("  1. E4: BEAR_OB MIDDAY + PO3_BEARISH (the primary edge)")
    print("  2. Counter: BEAR_OB MIDDAY + PO3_BULLISH (the baseline-noise control)")
    print("  3. E5: BULL_OB AFTERNOON + PO3_BULLISH (the bullish-side edge)")

    # E4 — primary edge
    run_test(
        label="E4 — BEAR_OB MIDDAY + PO3_BEARISH",
        pattern="BEAR_OB", pattern_dir=-1,
        time_window="MIDDAY", po3_required="PO3_BEARISH",
        original="NIFTY N=6 WR 83.3% EV +16.8pts | SENSEX N=11 WR 90.9% EV +116.5pts",
    )

    # E4 counter — baseline noise control
    run_test(
        label="E4 Counter — BEAR_OB MIDDAY + PO3_BULLISH",
        pattern="BEAR_OB", pattern_dir=-1,
        time_window="MIDDAY", po3_required="ANY_NOT_MATCH",
        original="(BEAR_OB MIDDAY on PO3_BULLISH day) N=56 WR 50.0% (baseline noise)",
    )

    # E5 — bullish-side edge (SENSEX-only per Exp 41B)
    run_test(
        label="E5 — BULL_OB AFTERNOON + PO3_BULLISH",
        pattern="BULL_OB", pattern_dir=+1,
        time_window="AFTERNOON", po3_required="PO3_BULLISH",
        original="NIFTY N=12 WR 50% DISCARD | SENSEX N=19 WR 73.7% EV +35.5pts",
    )

    print()
    print("=" * 100)
    print("INTERPRETATION GUIDE")
    print("=" * 100)
    print("  Replication PASS:  Current data shows WR within 10pp of original AND EV same sign")
    print("  Replication FAIL:  WR differs >15pp OR EV opposite sign")
    print("  N-too-small:       Current cohort lacks enough detections to test")
    print()
    print("Caveats explicit:")
    print("  - ict_zones has 0 BEAR_OB pre-S31 5m-aggregation fix.")
    print("  - Intraday zones absent pre-2026-04-22 (TD-067 — no backfill detector).")
    print("  - Original Exp 41B ran on hist_pattern_signals (different cohort).")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
