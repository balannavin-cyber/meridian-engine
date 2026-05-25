"""
s31_working_back_test.py — reverse-engineer realized moves to ICT structure.

For every 1-min bar in the cohort, check the forward 30-min window for a
spot move ≥ threshold. Find the move-onset (first qualifying bar), dedup
overlapping onsets, then for each event:
  1. Compute excursion (net move, max favorable, max adverse, whipsaw flag)
  2. Compute realized ATM option P&L (30-min hold + peak-of-window)
  3. Compute observability layers L1-L4:
       L1: HTF confluence had a zone matching move direction at event_ts
       L2: intraday detector had a zone matching direction in [t-15, t]
       L3: MERDIAN signal_snapshots direction_bias aligned with move
       L4: MERDIAN allowed the trade (trade_allowed=true + action matches)
  4. Capture structure snapshots at t-15, t-10, t-5, t-0 minutes

LIVE DATA ONLY. Does NOT read signal_snapshots.ict_pattern (backfilled).
Reads: hist_spot_bars_1m, signal_snapshots(direction_bias, action,
trade_allowed, atm_strike, expiry_date, dte), ict_zones, ict_htf_zones,
option_chain_snapshots + historical_option_chain_snapshots, instruments.

Move thresholds (locked spec):
  NIFTY:  50 / 100 / 150 pts
  SENSEX: 150 / 300 / 500 pts
Detection threshold = lowest tier (50 NIFTY, 150 SENSEX);
aggregate report buckets by tier.

Tradeable filter: ATM option 30-min hold P&L ≥ 20% across all DTEs.

Usage:
    python s31_working_back_test.py
    python s31_working_back_test.py --start-date 2026-04-22 --end-date 2026-05-15
    python s31_working_back_test.py --symbol NIFTY --output nifty_only.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date as _date

from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
TF_RANK = {"W": 0, "D": 1, "H": 2, "5m": 3, "1m": 4}
_MS_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")

# Locked thresholds
THRESHOLDS = {
    "NIFTY":  {"tiers": [50, 100, 150], "detect": 50},
    "SENSEX": {"tiers": [150, 300, 500], "detect": 150},
}
WINDOW_MIN = 30
DEDUP_MIN  = 15
LOOKBACK_MIN_SNAPSHOTS = [15, 10, 5, 0]
CHAIN_TOL_MIN = 3
SIGNAL_LOOKUP_MIN = 5  # find signal_snapshots row within ±5min of event_ts
TRADEABLE_THRESHOLD_PCT = 20.0
ARCHIVE_CUTOVER = datetime(2026, 5, 4, tzinfo=timezone.utc)
LIVE_CHAIN = "option_chain_snapshots"
ARCHIVE_CHAIN = "historical_option_chain_snapshots"


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
p.add_argument("--start-date", default="2026-03-23")
p.add_argument("--end-date",   default="2026-05-15")
p.add_argument("--symbols",    default="NIFTY,SENSEX")
p.add_argument("--output",     default="working_back.jsonl")
args = p.parse_args()

SYMBOLS = [s.strip().upper() for s in args.symbols.split(",")]


# ── Supabase ──────────────────────────────────────────────────────────

load_dotenv()
SB = create_client(
    os.getenv("SUPABASE_URL").strip(),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
)


# ── Helpers ──────────────────────────────────────────────────────────

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
    if s.endswith("+00"):
        s = s[:-3] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def ist_date(ts):
    if isinstance(ts, str):
        ts = parse_ts(ts)
    return ts.astimezone(IST).date().isoformat() if ts else ""


@dataclass
class Bar:
    bar_ts: datetime
    open: float
    high: float
    low: float
    close: float


# ── Static lookups ───────────────────────────────────────────────────

def fetch_instrument(symbol):
    rows = (SB.table("instruments")
            .select("id,lot_size,strike_step")
            .eq("symbol", symbol).limit(1).execute().data)
    if not rows:
        raise RuntimeError(f"No instruments row for {symbol}")
    return rows[0]


# ── Data fetch ───────────────────────────────────────────────────────

def fetch_bars(inst_id, trade_date) -> list[Bar]:
    rows = (SB.table("hist_spot_bars_1m")
            .select("bar_ts,open,high,low,close")
            .eq("instrument_id", inst_id)
            .eq("trade_date", trade_date)
            .eq("is_pre_market", False)
            .order("bar_ts")
            .execute().data) or []
    out = []
    for r in rows:
        bt = parse_ts(r["bar_ts"])
        if bt is None:
            continue
        out.append(Bar(
            bar_ts=bt,
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
        ))
    return out


def fetch_intraday_zones(symbol, trade_date):
    return (SB.table("ict_zones")
            .select("id,pattern_type,direction,zone_low,zone_high,"
                    "ict_tier,mtf_context,detected_at_ts,broken_at_ts,status")
            .eq("symbol", symbol).eq("trade_date", trade_date)
            .execute().data) or []


def fetch_htf_zones(symbol, trade_date):
    return (SB.table("ict_htf_zones")
            .select("id,timeframe,pattern_type,direction,zone_low,zone_high,"
                    "status,valid_from,valid_to,source_bar_date")
            .eq("symbol", symbol)
            .lte("valid_from", trade_date)
            .or_(f"valid_to.is.null,valid_to.gte.{trade_date}")
            .execute().data) or []


def fetch_signal_near(symbol, event_ts):
    """Find signal_snapshots row within ±SIGNAL_LOOKUP_MIN of event_ts.
    Returns the closest row, or None."""
    lo = (event_ts - timedelta(minutes=SIGNAL_LOOKUP_MIN)).isoformat()
    hi = (event_ts + timedelta(minutes=SIGNAL_LOOKUP_MIN)).isoformat()
    try:
        rows = (SB.table("signal_snapshots")
                .select("id,ts,direction_bias,action,trade_allowed,"
                        "atm_strike,expiry_date,dte,gamma_regime")
                .eq("symbol", symbol)
                .gte("ts", lo).lte("ts", hi)
                .order("ts").execute().data) or []
    except Exception:
        return None
    if not rows:
        return None
    # Closest to event_ts
    best, best_d = None, None
    for r in rows:
        rts = parse_ts(r["ts"])
        if rts is None: continue
        d = abs((rts - event_ts).total_seconds())
        if best_d is None or d < best_d:
            best_d, best = d, r
    return best


def _fetch_chain_at(table, sym, strike, opt_type, expiry, target_ts):
    lo = (target_ts - timedelta(minutes=CHAIN_TOL_MIN)).isoformat()
    hi = (target_ts + timedelta(minutes=CHAIN_TOL_MIN)).isoformat()
    try:
        rows = (SB.table(table)
                .select("ts,ltp")
                .eq("symbol", sym).eq("strike", strike)
                .eq("option_type", opt_type).eq("expiry_date", expiry)
                .gte("ts", lo).lte("ts", hi)
                .order("ts").range(0, 99).execute().data) or []
    except Exception:
        return None
    if not rows: return None
    best, best_d = None, None
    for r in rows:
        rts = parse_ts(r["ts"])
        if rts is None: continue
        d = abs((rts - target_ts).total_seconds())
        if best_d is None or d < best_d:
            best_d, best = d, r
    return best


def fetch_chain_at(sym, strike, opt_type, expiry, target_ts):
    primary = ARCHIVE_CHAIN if target_ts < ARCHIVE_CUTOVER else LIVE_CHAIN
    fb = LIVE_CHAIN if primary == ARCHIVE_CHAIN else ARCHIVE_CHAIN
    r = _fetch_chain_at(primary, sym, strike, opt_type, expiry, target_ts)
    if r: return r
    return _fetch_chain_at(fb, sym, strike, opt_type, expiry, target_ts)


def fetch_chain_range(sym, strike, opt_type, expiry, t_start, t_end):
    """Fetch ALL chain rows in [t_start, t_end]. Used to find peak LTP."""
    rows_all = []
    for table in (LIVE_CHAIN, ARCHIVE_CHAIN):
        try:
            rows = (SB.table(table)
                    .select("ts,ltp")
                    .eq("symbol", sym).eq("strike", strike)
                    .eq("option_type", opt_type).eq("expiry_date", expiry)
                    .gte("ts", t_start.isoformat())
                    .lte("ts", t_end.isoformat())
                    .order("ts").range(0, 999).execute().data) or []
            rows_all.extend(rows)
        except Exception:
            pass
    return rows_all


# ── Zone validity at arbitrary t ─────────────────────────────────────

def intraday_valid_at(zone, t):
    det = parse_ts(zone.get("detected_at_ts"))
    if det is None or det > t: return False
    brk = parse_ts(zone.get("broken_at_ts"))
    if brk is not None and brk <= t: return False
    return True


def htf_valid_at(zone, t):
    return zone.get("status") in ("ACTIVE", "BREACHED")


def contains(zone, spot):
    try:
        zl = float(zone["zone_low"])
        zh = float(zone["zone_high"])
    except (TypeError, ValueError, KeyError):
        return False
    return zl <= spot <= zh


def confluence_at(intraday_zones, htf_zones, t, spot):
    """Return (containing_zones_list, summary) at time t for given spot."""
    out = []
    for z in intraday_zones:
        if intraday_valid_at(z, t) and contains(z, spot):
            out.append({"source": "intraday",
                        "pattern_type": z["pattern_type"],
                        "direction": int(z.get("direction") or 0),
                        "ict_tier": z.get("ict_tier")})
    for z in htf_zones:
        if htf_valid_at(z, t) and contains(z, spot):
            out.append({"source": "htf",
                        "timeframe": z.get("timeframe"),
                        "pattern_type": z["pattern_type"],
                        "direction": int(z.get("direction") or 0)})
    bulls = sum(1 for z in out if z["direction"] == 1)
    bears = sum(1 for z in out if z["direction"] == -1)
    htf_bulls = sum(1 for z in out if z["source"] == "htf" and z["direction"] == 1)
    htf_bears = sum(1 for z in out if z["source"] == "htf" and z["direction"] == -1)
    if htf_bulls + htf_bears == 0:
        dom = "NONE"
    elif htf_bulls > htf_bears:
        dom = "BULL"
    elif htf_bears > htf_bulls:
        dom = "BEAR"
    else:
        dom = "MIXED"
    return out, {
        "bull_zone_count": bulls,
        "bear_zone_count": bears,
        "total_zone_count": len(out),
        "dominant_htf_direction": dom,
        "htf_bull_count": htf_bulls,
        "htf_bear_count": htf_bears,
    }


# ── Move detection ───────────────────────────────────────────────────

def detect_moves(bars: list[Bar], threshold_pts: float) -> list[dict]:
    """Find onset events. Forward 30-min window from each bar; if absolute
    net move ≥ threshold, qualifying. Dedup overlapping onsets within
    DEDUP_MIN minutes."""
    n = len(bars)
    if n < 30: return []

    events = []
    last_onset_idx = -10000
    DEDUP_BARS = DEDUP_MIN  # 1-min bars

    for i in range(n - 1):
        # Find bar nearest to i + WINDOW_MIN minutes ahead
        target_ts = bars[i].bar_ts + timedelta(minutes=WINDOW_MIN)
        # Walk forward to find the bar closest to target_ts
        j = i + 1
        while j < n and bars[j].bar_ts < target_ts:
            j += 1
        if j >= n:
            break  # window extends past available data
        # Use bar[j] (the first bar at or after target_ts) as the t+30 reference
        net_move = bars[j].close - bars[i].close
        if abs(net_move) < threshold_pts:
            continue
        # Dedup
        if i - last_onset_idx < DEDUP_BARS:
            continue
        # Compute max favorable / adverse in [i, j]
        if net_move > 0:
            max_fav = max(b.high for b in bars[i:j + 1]) - bars[i].close
            max_adv = bars[i].close - min(b.low for b in bars[i:j + 1])
        else:
            max_fav = bars[i].close - min(b.low for b in bars[i:j + 1])
            max_adv = max(b.high for b in bars[i:j + 1]) - bars[i].close
        events.append({
            "onset_idx": i,
            "exit_idx": j,
            "ts": bars[i].bar_ts,
            "ts_t30": bars[j].bar_ts,
            "spot_at_t": bars[i].close,
            "spot_at_t30": bars[j].close,
            "net_move_pts": round(net_move, 2),
            "max_favorable_pts": round(max_fav, 2),
            "max_adverse_pts": round(max_adv, 2),
            "direction": "UP" if net_move > 0 else "DOWN",
        })
        last_onset_idx = i

    return events


# ── Magnitude bucketing ──────────────────────────────────────────────

def magnitude_tier(symbol, abs_pts):
    tiers = sorted(THRESHOLDS[symbol]["tiers"], reverse=True)
    for t in tiers:
        if abs_pts >= t:
            return t
    return None  # below detection threshold (shouldn't happen)


def dte_bucket(dte):
    if dte is None: return "UNK"
    if dte == 0: return "0"
    if dte == 1: return "1"
    if dte == 2: return "2"
    return "3+"


# ── Observability layers ─────────────────────────────────────────────

def compute_layers(event, intraday_zones, htf_zones, signal_row):
    move_dir = 1 if event["direction"] == "UP" else -1
    natural_action = "BUY_CE" if move_dir == 1 else "BUY_PE"
    event_ts = event["ts"]

    # L1: HTF confluence aligned with move direction at event_ts
    _, summary_t0 = confluence_at(intraday_zones, htf_zones, event_ts,
                                  event["spot_at_t"])
    htf_dom = summary_t0["dominant_htf_direction"]
    L1 = (htf_dom == "BULL" and move_dir == 1) or \
         (htf_dom == "BEAR" and move_dir == -1)

    # L2: intraday detector saw a zone matching direction in [t-15min, t]
    L2 = False
    for z in intraday_zones:
        det = parse_ts(z.get("detected_at_ts"))
        if det is None: continue
        if det > event_ts: continue
        if det < event_ts - timedelta(minutes=15): continue
        # Check spot at det was inside zone (approximation: spot at event)
        if int(z.get("direction") or 0) != move_dir: continue
        L2 = True
        break

    # L3: signal_snapshots direction_bias aligned at event_ts
    L3 = False
    L4 = False
    merdian_action = None
    merdian_trade_allowed = None
    direction_bias = None
    gamma_regime = None
    if signal_row:
        direction_bias = (signal_row.get("direction_bias") or "").upper()
        merdian_action = signal_row.get("action")
        merdian_trade_allowed = bool(signal_row.get("trade_allowed"))
        gamma_regime = signal_row.get("gamma_regime")
        if (direction_bias == "BULLISH" and move_dir == 1) or \
           (direction_bias == "BEARISH" and move_dir == -1):
            L3 = True
        if L3 and merdian_action == natural_action and merdian_trade_allowed:
            L4 = True

    return {
        "L1_htf_aligned": L1,
        "L2_intraday_aligned": L2,
        "L3_signal_aligned": L3,
        "L4_trade_allowed": L4,
        "natural_action": natural_action,
        "merdian_action": merdian_action,
        "merdian_trade_allowed": merdian_trade_allowed,
        "merdian_direction_bias": direction_bias,
        "merdian_gamma_regime": gamma_regime,
        "htf_dominant_at_event": htf_dom,
    }


# ── Option P&L ───────────────────────────────────────────────────────

def compute_option_pnl(symbol, event, signal_row):
    """Return entry, exit_30m, peak_premium, pnl_30m_pct, pnl_peak_pct,
    dte, strike, expiry. None on any failure."""
    if not signal_row:
        return None
    strike = signal_row.get("atm_strike")
    expiry = signal_row.get("expiry_date")
    dte = signal_row.get("dte")
    if strike is None or not expiry:
        return None

    opt_type = "CE" if event["direction"] == "UP" else "PE"
    event_ts = event["ts"]
    exit_ts = event["ts_t30"]

    entry = fetch_chain_at(symbol, int(strike), opt_type, str(expiry),
                           event_ts)
    if entry is None or entry.get("ltp") is None:
        return None
    try:
        entry_ltp = float(entry["ltp"])
    except (TypeError, ValueError):
        return None
    if entry_ltp <= 0:
        return None

    exit_ = fetch_chain_at(symbol, int(strike), opt_type, str(expiry),
                           exit_ts)
    if exit_ is None or exit_.get("ltp") is None:
        return None
    try:
        exit_ltp = float(exit_["ltp"])
    except (TypeError, ValueError):
        return None

    # Peak in window
    range_rows = fetch_chain_range(symbol, int(strike), opt_type, str(expiry),
                                   event_ts, exit_ts)
    peak_ltp = entry_ltp
    for r in range_rows:
        try:
            v = float(r["ltp"])
            if v > peak_ltp:
                peak_ltp = v
        except (TypeError, ValueError):
            continue

    return {
        "atm_strike": int(strike),
        "expiry_date": str(expiry),
        "dte": dte,
        "opt_type": opt_type,
        "entry_premium": round(entry_ltp, 2),
        "exit_premium_30m": round(exit_ltp, 2),
        "peak_premium": round(peak_ltp, 2),
        "atm_pnl_30m_pct": round((exit_ltp - entry_ltp) / entry_ltp * 100, 2),
        "atm_pnl_peak_pct": round((peak_ltp - entry_ltp) / entry_ltp * 100, 2),
    }


# ── Structure snapshots ──────────────────────────────────────────────

def structure_snapshots(intraday_zones, htf_zones, event_ts, spot_at_t):
    out = {}
    for back in LOOKBACK_MIN_SNAPSHOTS:
        t = event_ts - timedelta(minutes=back)
        _, summary = confluence_at(intraday_zones, htf_zones, t, spot_at_t)
        out[f"t_minus_{back}"] = summary
    return out


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print(f"S31 working-back test")
    print(f"Cohort: {args.start_date} → {args.end_date}  symbols={SYMBOLS}")
    print(f"Output: {args.output}")
    print(f"Detect thresholds: NIFTY ≥{THRESHOLDS['NIFTY']['detect']}pts, "
          f"SENSEX ≥{THRESHOLDS['SENSEX']['detect']}pts")
    print(f"Window={WINDOW_MIN}min  Dedup={DEDUP_MIN}min  "
          f"Tradeable={TRADEABLE_THRESHOLD_PCT}%")
    print()

    out_f = open(args.output, "w", encoding="utf-8")
    total_events = 0
    events_by_bucket = Counter()
    pricing_success = 0
    pricing_failure = 0

    try:
        for symbol in SYMBOLS:
            print(f"=== {symbol} ===")
            inst = fetch_instrument(symbol)
            inst_id = inst["id"]

            # Iterate trade_dates
            start_d = _date.fromisoformat(args.start_date)
            end_d = _date.fromisoformat(args.end_date)
            cur = start_d
            while cur <= end_d:
                if cur.weekday() < 5:  # Mon-Fri
                    bars = fetch_bars(inst_id, cur.isoformat())
                    if len(bars) >= 30:
                        intra = fetch_intraday_zones(symbol, cur.isoformat())
                        htf = fetch_htf_zones(symbol, cur.isoformat())
                        events = detect_moves(bars,
                                              THRESHOLDS[symbol]["detect"])
                        if events:
                            print(f"  {cur.isoformat()}: {len(bars)} bars  "
                                  f"intra={len(intra)} htf={len(htf)}  "
                                  f"events={len(events)}")
                        for ev in events:
                            sig = fetch_signal_near(symbol, ev["ts"])
                            layers = compute_layers(ev, intra, htf, sig)
                            pnl = compute_option_pnl(symbol, ev, sig)
                            if pnl:
                                pricing_success += 1
                            else:
                                pricing_failure += 1
                            snaps = structure_snapshots(intra, htf, ev["ts"],
                                                        ev["spot_at_t"])

                            abs_pts = abs(ev["net_move_pts"])
                            tier = magnitude_tier(symbol, abs_pts)
                            was_whipsaw = (ev["max_adverse_pts"] >
                                           0.5 * abs_pts)

                            tradeable = (pnl is not None and
                                         pnl["atm_pnl_30m_pct"] >=
                                         TRADEABLE_THRESHOLD_PCT)

                            record = {
                                "event_ts": ev["ts"].isoformat(),
                                "event_ts_ist": ev["ts"].astimezone(IST).isoformat()[:19],
                                "exit_ts": ev["ts_t30"].isoformat(),
                                "symbol": symbol,
                                "direction": ev["direction"],
                                "spot_at_t": ev["spot_at_t"],
                                "spot_at_t30": ev["spot_at_t30"],
                                "net_move_pts": ev["net_move_pts"],
                                "max_favorable_pts": ev["max_favorable_pts"],
                                "max_adverse_pts": ev["max_adverse_pts"],
                                "magnitude_tier": tier,
                                "was_whipsaw": was_whipsaw,
                                "was_tradeable": tradeable,
                                "option": pnl,
                                "dte_bucket": dte_bucket(pnl["dte"] if pnl else None),
                                "layers": layers,
                                "structure_snapshots": snaps,
                                "signal_snapshot_id": sig["id"] if sig else None,
                            }
                            out_f.write(json.dumps(record, default=str) + "\n")
                            total_events += 1
                            events_by_bucket[(symbol, tier, ev["direction"])] += 1
                cur += timedelta(days=1)
            print()
    finally:
        out_f.close()

    print("=" * 78)
    print(f"Wrote {total_events:,} events to {args.output}")
    print(f"Pricing success: {pricing_success:,}  failure: {pricing_failure:,}")
    print()
    print(f"Events by (symbol, tier, direction):")
    for (sym, tier, dir_), n in sorted(events_by_bucket.items()):
        print(f"  {sym:<7} ≥{tier}pts {dir_:<4}: {n:>4}")
    print()
    print("Inspect with:")
    print(f"  python inspect_working_back.py {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
