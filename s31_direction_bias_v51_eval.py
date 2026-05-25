"""
s31_direction_bias_v51_eval.py — v5.1 with rejection/break detection.

Extends v5 by classifying the touch state of the dominant zone at
event_ts using the most recent complete 5-min bar:

  REJECTION → zone direction (zone holds, continuation)
    BEAR zone: bar.high >= zone_low AND bar.close < zone_low
    BULL zone: bar.low  <= zone_high AND bar.close > zone_high

  BREAK → INVERSE of zone direction (zone failed, reversal)
    BEAR zone: bar.close > zone_high  (closed above resistance)
    BULL zone: bar.close < zone_low   (closed below support)

  PENDING → zone direction (default, same as v5)
    bar.close inside [zone_low, zone_high]

LIVE DATA ONLY. Reads from hist_spot_bars_1m + signal_snapshots +
ict_zones + ict_htf_zones + instruments. No backfilled fields.

Usage:
    python s31_direction_bias_v51_eval.py
    python s31_direction_bias_v51_eval.py --tradeable-only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
TF_RANK = {"W": 0, "D": 1, "H": 2, "5m": 3, "1m": 4}
_MS_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")
SIGNAL_LOOKUP_MIN = 5
BAR_LOOKBACK_MIN = 30  # fetch 1-min bars in [event_ts - 30min, event_ts + 5min]
BAR_FORWARD_MIN = 5


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
p.add_argument("--path", default="working_back.jsonl")
p.add_argument("--tradeable-only", action="store_true")
args = p.parse_args()


# ── Supabase ──────────────────────────────────────────────────────────

load_dotenv()
SB = create_client(
    os.getenv("SUPABASE_URL").strip(),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
)


# ── TS helpers ───────────────────────────────────────────────────────

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


def ist_date(ts):
    if isinstance(ts, str): ts = parse_ts(ts)
    return ts.astimezone(IST).date().isoformat() if ts else ""


# ── Instrument cache ─────────────────────────────────────────────────

def fetch_instrument_id(symbol):
    rows = (SB.table("instruments")
            .select("id").eq("symbol", symbol).limit(1).execute().data)
    return rows[0]["id"] if rows else None


# ── Zone fetch (corrected predicates) ────────────────────────────────

def fetch_intraday_zones(symbol, trade_date):
    return (SB.table("ict_zones")
            .select("id,pattern_type,direction,zone_low,zone_high,"
                    "ict_tier,detected_at_ts,broken_at_ts,status")
            .eq("symbol", symbol).eq("trade_date", trade_date)
            .execute().data) or []


def fetch_htf_zones(symbol, trade_date):
    return (SB.table("ict_htf_zones")
            .select("id,timeframe,pattern_type,direction,zone_low,zone_high,"
                    "status,valid_from,valid_to")
            .eq("symbol", symbol)
            .lte("valid_from", trade_date)
            .or_(f"valid_to.is.null,valid_to.gte.{trade_date}")
            .execute().data) or []


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
        return float(zone["zone_low"]) <= spot <= float(zone["zone_high"])
    except (TypeError, ValueError, KeyError):
        return False


def containing_zones_at(intra, htf, event_ts, spot):
    out = []
    for z in intra:
        if intraday_valid_at(z, event_ts) and contains(z, spot):
            zc = dict(z); zc["source"] = "intraday"; zc["timeframe"] = "5m"
            out.append(zc)
    for z in htf:
        if htf_valid_at(z, event_ts) and contains(z, spot):
            zc = dict(z); zc["source"] = "htf"
            out.append(zc)
    return out


# ── 1-min bar fetch + 5-min aggregation ──────────────────────────────

def fetch_1m_bars(inst_id, trade_date):
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
        if bt is None: continue
        out.append({
            "bar_ts": bt,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low":  float(r["low"]),
            "close": float(r["close"]),
        })
    return out


def aggregate_1m_to_5m(bars_1m):
    if not bars_1m: return []
    buckets = defaultdict(list)
    for b in bars_1m:
        ts = b["bar_ts"]
        bucket_ts = ts.replace(
            minute=(ts.minute // 5) * 5,
            second=0,
            microsecond=0,
        )
        buckets[bucket_ts].append(b)
    out = []
    for bucket_ts in sorted(buckets):
        items = sorted(buckets[bucket_ts], key=lambda b: b["bar_ts"])
        if len(items) < 5: continue
        out.append({
            "bar_ts": bucket_ts,
            "open": items[0]["open"],
            "high": max(b["high"] for b in items),
            "low":  min(b["low"]  for b in items),
            "close": items[-1]["close"],
        })
    return out


def most_recent_5m_bar_before(bars_5m, event_ts):
    """Return the most recent 5-min bar whose bar_ts <= event_ts."""
    candidates = [b for b in bars_5m if b["bar_ts"] <= event_ts]
    if not candidates:
        return None
    return candidates[-1]


# ── Touch-state classifier ───────────────────────────────────────────

def classify_zone_touch(zone, recent_bar):
    """Classify the most recent 5-min bar's relationship to the zone.
    Returns 'REJECTION' | 'BREAK' | 'PENDING' | 'NO_BAR'.
    """
    if recent_bar is None:
        return "NO_BAR"
    try:
        zl = float(zone["zone_low"])
        zh = float(zone["zone_high"])
        c  = recent_bar["close"]
        h  = recent_bar["high"]
        l  = recent_bar["low"]
    except (KeyError, TypeError, ValueError):
        return "PENDING"

    direction = int(zone.get("direction") or 0)

    if direction == -1:  # BEAR zone (overhead resistance)
        if c < zl:
            return "REJECTION" if h >= zl else "PENDING"
        if c > zh:
            return "BREAK"
        return "PENDING"

    if direction == 1:  # BULL zone (support below)
        if c > zh:
            return "REJECTION" if l <= zh else "PENDING"
        if c < zl:
            return "BREAK"
        return "PENDING"

    return "PENDING"


# ── v5.1 direction logic ─────────────────────────────────────────────

def infer_direction_bias_v51(spot, containing, recent_5m_bar, signal_row):
    """v5.1: structure + touch-state.
    Returns (direction, reason, source_layer, touch_state).
    """
    if not containing:
        # V4 momentum fallback (same as v5)
        if signal_row:
            raw = signal_row.get("raw") or {}
            if isinstance(raw, str):
                try: raw = json.loads(raw)
                except Exception: raw = {}
            if isinstance(raw, dict):
                ret_session = raw.get("ret_session")
                try:
                    if ret_session is not None:
                        rs = float(ret_session)
                        if rs > 0:
                            return ("BULLISH", f"ret_session={rs:.4f}",
                                    "MOMENTUM_FALLBACK", "NONE")
                        if rs < 0:
                            return ("BEARISH", f"ret_session={rs:.4f}",
                                    "MOMENTUM_FALLBACK", "NONE")
                except (TypeError, ValueError):
                    pass
        return ("NEUTRAL", "No structure, no momentum",
                "NEUTRAL_NOSIGNAL", "NONE")

    # Pick dominant zone (same TF/tightest/closest cascade as v5)
    def key(z):
        tf = z.get("timeframe", "5m")
        rank = TF_RANK.get(tf, 9)
        try:
            zl = float(z["zone_low"])
            zh = float(z["zone_high"])
            width = zh - zl
            mid = (zl + zh) / 2
            dist = abs(spot - mid)
        except (TypeError, ValueError, KeyError):
            return (rank, 1e9, 1e9)
        return (rank, width, dist)

    best = min(containing, key=key)
    direction = int(best.get("direction") or 0)
    tf = best.get("timeframe", "?")
    pt = best.get("pattern_type", "?")
    layer = "HTF_STRUCTURE" if best.get("source") == "htf" else "INTRADAY_STRUCTURE"

    state = classify_zone_touch(best, recent_5m_bar)

    # Decision matrix
    if state == "REJECTION":
        if direction == 1:
            return ("BULLISH", f"{tf} {pt} REJECTION", layer, state)
        if direction == -1:
            return ("BEARISH", f"{tf} {pt} REJECTION", layer, state)
    elif state == "BREAK":
        # Zone failed → reverse direction
        if direction == 1:
            return ("BEARISH", f"{tf} {pt} BREAK (BULL zone failed)",
                    layer, state)
        if direction == -1:
            return ("BULLISH", f"{tf} {pt} BREAK (BEAR zone swept)",
                    layer, state)
    else:  # PENDING or NO_BAR
        if direction == 1:
            return ("BULLISH", f"{tf} {pt} {state}", layer, state)
        if direction == -1:
            return ("BEARISH", f"{tf} {pt} {state}", layer, state)

    return ("NEUTRAL", f"{tf} {pt} direction=0", layer, state)


# ── Signal lookup ────────────────────────────────────────────────────

def fetch_signal_near(symbol, event_ts):
    lo = (event_ts - timedelta(minutes=SIGNAL_LOOKUP_MIN)).isoformat()
    hi = (event_ts + timedelta(minutes=SIGNAL_LOOKUP_MIN)).isoformat()
    try:
        rows = (SB.table("signal_snapshots")
                .select("id,ts,direction_bias,action,trade_allowed,raw")
                .eq("symbol", symbol)
                .gte("ts", lo).lte("ts", hi)
                .order("ts").execute().data) or []
    except Exception:
        return None
    if not rows: return None
    best, best_d = None, None
    for r in rows:
        rts = parse_ts(r["ts"])
        if rts is None: continue
        d = abs((rts - event_ts).total_seconds())
        if best_d is None or d < best_d:
            best_d, best = d, r
    return best


# ── Main ─────────────────────────────────────────────────────────────

def main():
    # Load events
    events = []
    with open(args.path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    print(f"Loaded {len(events)} events from {args.path}")

    if args.tradeable_only:
        events = [e for e in events if e.get("was_tradeable")]
        print(f"After tradeable filter: {len(events)}")

    # Pre-fetch instrument IDs
    print("Fetching instrument IDs ...")
    symbols = sorted({e["symbol"] for e in events})
    inst_ids = {s: fetch_instrument_id(s) for s in symbols}
    print(f"  {inst_ids}")

    # Pre-fetch zones + 5-min bar cache per (symbol, date)
    print("Pre-fetching zones + 5-min bars per day ...")
    cache = {}  # (symbol, date) -> (intra, htf, bars_5m)
    needed = sorted({(e["symbol"], ist_date(e["event_ts"])) for e in events})
    for i, (sym, d) in enumerate(needed, 1):
        if i % 30 == 0:
            print(f"  {i}/{len(needed)}")
        intra = fetch_intraday_zones(sym, d)
        htf = fetch_htf_zones(sym, d)
        bars_1m = fetch_1m_bars(inst_ids[sym], d)
        bars_5m = aggregate_1m_to_5m(bars_1m)
        cache[(sym, d)] = (intra, htf, bars_5m)
    print(f"  Cached {len(needed)} (symbol, date) pairs")
    print()

    # Evaluate each event
    print(f"Evaluating {len(events)} events ...")
    rows = []
    for i, e in enumerate(events, 1):
        if i % 100 == 0:
            print(f"  {i}/{len(events)}")
        event_ts = parse_ts(e["event_ts"])
        if event_ts is None: continue
        spot = float(e["spot_at_t"])
        d = ist_date(event_ts)
        intra, htf, bars_5m = cache.get((e["symbol"], d), ([], [], []))
        containing = containing_zones_at(intra, htf, event_ts, spot)
        signal = fetch_signal_near(e["symbol"], event_ts)
        recent_bar = most_recent_5m_bar_before(bars_5m, event_ts)
        v51_dir, v51_reason, v51_layer, v51_state = infer_direction_bias_v51(
            spot, containing, recent_bar, signal)
        v4_dir = (signal.get("direction_bias") or "MISSING").upper() if signal else "NOSIGNAL"

        move_dir = e["direction"]
        expected = "BULLISH" if move_dir == "UP" else "BEARISH"

        rows.append({
            "event_ts": e["event_ts"],
            "symbol": e["symbol"],
            "move_dir": move_dir,
            "expected": expected,
            "tradeable": bool(e.get("was_tradeable")),
            "v51_dir": v51_dir,
            "v51_layer": v51_layer,
            "v51_state": v51_state,
            "v51_reason": v51_reason,
            "v4_dir": v4_dir,
            "n_containing": len(containing),
            "dte_bucket": e.get("dte_bucket"),
            "has_recent_bar": recent_bar is not None,
        })

    print(f"  Done. Evaluated {len(rows)} events.")
    print()

    # ── Reports ──────────────────────────────────────────────────────
    tradeable = [r for r in rows if r["tradeable"]]

    def correct(r, v):  return r[f"{v}_dir"] == r["expected"]
    def wrong(r, v):    return r[f"{v}_dir"] in ("BULLISH", "BEARISH") and r[f"{v}_dir"] != r["expected"]
    def neutral(r, v):  return r[f"{v}_dir"] in ("NEUTRAL", "MISSING", "NOSIGNAL", "UNKNOWN")

    def section(label, group):
        if not group:
            print(f"  {label}: N=0"); return
        n = len(group)
        v51_r = sum(1 for r in group if correct(r, "v51"))
        v51_w = sum(1 for r in group if wrong(r, "v51"))
        v51_n = sum(1 for r in group if neutral(r, "v51"))
        v4_r = sum(1 for r in group if correct(r, "v4"))
        v4_w = sum(1 for r in group if wrong(r, "v4"))
        v4_n = sum(1 for r in group if neutral(r, "v4"))
        print(f"  {label} (N={n}):")
        print(f"    v5.1: correct={v51_r} ({v51_r/n*100:>5.1f}%)  "
              f"wrong={v51_w} ({v51_w/n*100:>5.1f}%)  "
              f"neut={v51_n} ({v51_n/n*100:>5.1f}%)")
        print(f"    v4:   correct={v4_r} ({v4_r/n*100:>5.1f}%)  "
              f"wrong={v4_w} ({v4_w/n*100:>5.1f}%)  "
              f"neut={v4_n} ({v4_n/n*100:>5.1f}%)")
        delta = v51_r - v4_r
        print(f"    Δ correct: {delta:+d} events ({(v51_r-v4_r)/n*100:+.1f}pp)")

    print("=" * 78)
    print("ALL EVENTS (760)")
    print("=" * 78)
    section("All", rows)
    print()
    section("UP",   [r for r in rows if r["move_dir"] == "UP"])
    section("DOWN", [r for r in rows if r["move_dir"] == "DOWN"])
    print()

    print("=" * 78)
    print("TRADEABLE SUBSET")
    print("=" * 78)
    section("Tradeable", tradeable)
    print()
    section("Tradeable UP",   [r for r in tradeable if r["move_dir"] == "UP"])
    section("Tradeable DOWN", [r for r in tradeable if r["move_dir"] == "DOWN"])
    print()

    # ── Touch-state breakdown — THE NEW DIAGNOSTIC ────────────────────
    print("=" * 78)
    print("v5.1 TOUCH-STATE BREAKDOWN — does reject/break detection help?")
    print("=" * 78)
    for label, group in (("All", rows), ("Tradeable", tradeable)):
        states = Counter(r["v51_state"] for r in group)
        print(f"  {label} (N={len(group)}):")
        for state, n in states.most_common():
            grp = [r for r in group if r["v51_state"] == state]
            r_count = sum(1 for r in grp if correct(r, "v51"))
            print(f"    state={state:<11} N={n:>5}  "
                  f"v5.1_correct={r_count:>4} "
                  f"({r_count/n*100 if n else 0:>5.1f}%)")
        print()

    # ── Touch-state × move direction ──────────────────────────────────
    print("=" * 78)
    print("Touch-state × move direction (tradeable only)")
    print("=" * 78)
    for state in ("REJECTION", "BREAK", "PENDING", "NO_BAR"):
        for move in ("UP", "DOWN"):
            grp = [r for r in tradeable
                    if r["v51_state"] == state and r["move_dir"] == move]
            if not grp: continue
            n = len(grp)
            r_count = sum(1 for r in grp if correct(r, "v51"))
            print(f"  state={state:<11} move={move:<5}: N={n:>3}  "
                  f"v5.1_correct={r_count} "
                  f"({r_count/n*100 if n else 0:>5.1f}%)")
    print()

    # ── Decision gate ─────────────────────────────────────────────────
    print("=" * 78)
    print("DECISION GATE (per spec)")
    print("=" * 78)
    tu = [r for r in tradeable if r["move_dir"] == "UP"]
    td = [r for r in tradeable if r["move_dir"] == "DOWN"]
    rate_u = sum(1 for r in tu if correct(r, "v51")) / len(tu) * 100 if tu else 0
    rate_d = sum(1 for r in td if correct(r, "v51")) / len(td) * 100 if td else 0
    print(f"  Tradeable UP correctness:   v5.1={rate_u:.1f}%  v5=44.2%  v4=15.8%  "
          f"target ≥70% → {'PASS' if rate_u >= 70 else 'FAIL'}")
    print(f"  Tradeable DOWN correctness: v5.1={rate_d:.1f}%  v5=50.4%  v4=70.8%  "
          f"target ≥70% → {'PASS' if rate_d >= 70 else 'FAIL'}")
    if rate_u >= 70 and rate_d >= 70:
        print(f"  → BOTH PASS. v5.1 ready for replay validation.")
    elif rate_u >= 70 or rate_d >= 70:
        print(f"  → ASYMMETRIC. One bar met.")
    else:
        print(f"  → BOTH FAIL. Reject/break detection insufficient.")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
