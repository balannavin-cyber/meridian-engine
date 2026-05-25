"""
s31_direction_bias_v5_eval.py — backtest structure-first direction logic.

Reads working_back.jsonl events, refetches the HTF + intraday zones
containing spot at each event_ts (using the CORRECTED valid_to-IS-NULL
predicate), applies v5 logic, compares against:
  - actual move direction (UP/DOWN ground truth)
  - V4 direction_bias from signal_snapshots (live decision)

v5 logic (ICT canon, touch-fires):
  1. If any zone contains spot at event_ts:
       Pick structurally-dominant zone:
         primary sort: timeframe priority (W > D > H > 5m intraday)
         tiebreak 1:   tightest zone (smallest width)
         tiebreak 2:   midpoint closest to spot
       direction_bias = sign of dominant zone's direction
  2. If no zone contains spot:
       Fall back to V4 momentum:
         sign(ret_session) if not None
         else sign(ret_15m + ret_30m) score
         else NEUTRAL

LIVE DATA ONLY. No backfilled fields read.

Usage:
    python s31_direction_bias_v5_eval.py
    python s31_direction_bias_v5_eval.py --path working_back.jsonl
    python s31_direction_bias_v5_eval.py --tradeable-only
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
    if isinstance(ts, str):
        ts = parse_ts(ts)
    return ts.astimezone(IST).date().isoformat() if ts else ""


# ── Zone fetch (corrected valid_to-IS-NULL predicate) ────────────────

def fetch_intraday_zones(symbol, trade_date):
    return (SB.table("ict_zones")
            .select("id,pattern_type,direction,zone_low,zone_high,"
                    "ict_tier,detected_at_ts,broken_at_ts,status")
            .eq("symbol", symbol).eq("trade_date", trade_date)
            .execute().data) or []


def fetch_htf_zones(symbol, trade_date):
    """Corrected: accept valid_to IS NULL (indefinite validity)."""
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
            zc = dict(z)
            zc["source"] = "intraday"
            zc["timeframe"] = "5m"  # intraday detector emits at 5m
            out.append(zc)
    for z in htf:
        if htf_valid_at(z, event_ts) and contains(z, spot):
            zc = dict(z)
            zc["source"] = "htf"
            out.append(zc)
    return out


# ── V5 logic ─────────────────────────────────────────────────────────

def infer_direction_bias_v5(spot, containing, signal_row):
    """v5: structure-first; V4 momentum as fallback.
    Returns (direction_bias, reason, source_layer).
    source_layer ∈ {'HTF_STRUCTURE','INTRADAY_STRUCTURE','MOMENTUM_FALLBACK','NEUTRAL_NOSIGNAL'}
    """
    if containing:
        def key(z):
            tf = z.get("timeframe", "5m")
            rank = TF_RANK.get(tf, 9)
            try:
                zl = float(z["zone_low"])
                zh = float(z["zone_high"])
            except (TypeError, ValueError, KeyError):
                return (rank, 1e9, 1e9)
            width = zh - zl
            mid = (zl + zh) / 2
            dist = abs(spot - mid)
            return (rank, width, dist)
        best = min(containing, key=key)
        dir_ = int(best.get("direction") or 0)
        tf = best.get("timeframe", "?")
        pt = best.get("pattern_type", "?")
        layer = "HTF_STRUCTURE" if best.get("source") == "htf" else "INTRADAY_STRUCTURE"
        if dir_ == 1:
            return "BULLISH", f"Spot in {tf} {pt}", layer
        if dir_ == -1:
            return "BEARISH", f"Spot in {tf} {pt}", layer
        return "NEUTRAL", f"Spot in {pt} direction=0", layer

    # V4 fallback: momentum
    if signal_row:
        raw = signal_row.get("raw") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}
        ret_session = raw.get("ret_session") if isinstance(raw, dict) else None
        try:
            if ret_session is not None:
                rs = float(ret_session)
                if rs > 0: return "BULLISH", f"ret_session={rs:.4f}", "MOMENTUM_FALLBACK"
                if rs < 0: return "BEARISH", f"ret_session={rs:.4f}", "MOMENTUM_FALLBACK"
        except (TypeError, ValueError):
            pass

    return "NEUTRAL", "No structure, no momentum", "NEUTRAL_NOSIGNAL"


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

    # Pre-fetch zones per (symbol, date) — cohort can have many events per day
    print(f"Pre-fetching zones per day ...")
    zones_cache = {}
    needed = set()
    for e in events:
        d = ist_date(e["event_ts"])
        if d:
            needed.add((e["symbol"], d))
    for i, (sym, d) in enumerate(sorted(needed), 1):
        if i % 30 == 0:
            print(f"  {i}/{len(needed)}")
        intra = fetch_intraday_zones(sym, d)
        htf = fetch_htf_zones(sym, d)
        zones_cache[(sym, d)] = (intra, htf)
    print(f"  Cached zones for {len(needed)} (symbol, date) pairs")
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
        intra, htf = zones_cache.get((e["symbol"], d), ([], []))
        containing = containing_zones_at(intra, htf, event_ts, spot)
        signal = fetch_signal_near(e["symbol"], event_ts)
        v5_dir, v5_reason, v5_layer = infer_direction_bias_v5(spot, containing, signal)
        v4_dir = (signal.get("direction_bias") or "MISSING").upper() if signal else "NOSIGNAL"

        # Map to expected direction by move
        move_dir = e["direction"]  # 'UP' or 'DOWN'
        expected = "BULLISH" if move_dir == "UP" else "BEARISH"

        rows.append({
            "event_ts": e["event_ts"],
            "symbol": e["symbol"],
            "move_dir": move_dir,
            "expected": expected,
            "tradeable": bool(e.get("was_tradeable")),
            "v5_dir": v5_dir,
            "v5_layer": v5_layer,
            "v5_reason": v5_reason,
            "v4_dir": v4_dir,
            "n_containing": len(containing),
            "dte_bucket": e.get("dte_bucket"),
        })

    print(f"  Done. Evaluated {len(rows)} events.")
    print()

    # ── Reports ──────────────────────────────────────────────────────
    total = len(rows)
    tradeable = [r for r in rows if r["tradeable"]]
    nontradeable = [r for r in rows if not r["tradeable"]]

    def correct(r, version):
        return r[f"{version}_dir"] == r["expected"]

    def wrong(r, version):
        return r[f"{version}_dir"] in ("BULLISH", "BEARISH") and r[f"{version}_dir"] != r["expected"]

    def neutral_or_missing(r, version):
        return r[f"{version}_dir"] in ("NEUTRAL", "MISSING", "NOSIGNAL", "UNKNOWN")

    def report_section(label, group):
        if not group:
            print(f"  {label}: N=0")
            return
        n = len(group)
        v5_right = sum(1 for r in group if correct(r, "v5"))
        v5_wrong = sum(1 for r in group if wrong(r, "v5"))
        v5_neut = sum(1 for r in group if neutral_or_missing(r, "v5"))
        v4_right = sum(1 for r in group if correct(r, "v4"))
        v4_wrong = sum(1 for r in group if wrong(r, "v4"))
        v4_neut = sum(1 for r in group if neutral_or_missing(r, "v4"))
        print(f"  {label} (N={n}):")
        print(f"    v5: correct={v5_right} ({v5_right/n*100:>5.1f}%)  "
              f"wrong={v5_wrong} ({v5_wrong/n*100:>5.1f}%)  "
              f"neutral/none={v5_neut} ({v5_neut/n*100:>5.1f}%)")
        print(f"    v4: correct={v4_right} ({v4_right/n*100:>5.1f}%)  "
              f"wrong={v4_wrong} ({v4_wrong/n*100:>5.1f}%)  "
              f"neutral/none={v4_neut} ({v4_neut/n*100:>5.1f}%)")
        delta = v5_right - v4_right
        delta_pct = (v5_right - v4_right) / n * 100 if n else 0
        print(f"    Δ correct: {delta:+d} events ({delta_pct:+.1f}pp)")

    print("=" * 78)
    print("ALL EVENTS (760-event cohort)")
    print("=" * 78)
    report_section("All", rows)
    print()
    report_section("UP moves",   [r for r in rows if r["move_dir"] == "UP"])
    report_section("DOWN moves", [r for r in rows if r["move_dir"] == "DOWN"])
    print()

    print("=" * 78)
    print("TRADEABLE SUBSET (the moves that paid)")
    print("=" * 78)
    report_section("Tradeable", tradeable)
    print()
    report_section("Tradeable UP",   [r for r in tradeable if r["move_dir"] == "UP"])
    report_section("Tradeable DOWN", [r for r in tradeable if r["move_dir"] == "DOWN"])
    print()

    # ── v5 source layer breakdown ─────────────────────────────────────
    print("=" * 78)
    print("v5 SOURCE LAYER BREAKDOWN (where did v5 get its direction?)")
    print("=" * 78)
    for label, group in (("All", rows), ("Tradeable", tradeable)):
        layers = Counter(r["v5_layer"] for r in group)
        print(f"  {label} (N={len(group)}):")
        for k, c in layers.most_common():
            correct_in_layer = sum(1 for r in group
                                    if r["v5_layer"] == k and correct(r, "v5"))
            print(f"    {k:<22} N={c:>5}  v5_correct={correct_in_layer:>4} "
                  f"({correct_in_layer/c*100 if c else 0:>5.1f}%)")
        print()

    # ── v5 vs v4 agreement matrix ─────────────────────────────────────
    print("=" * 78)
    print("v5 vs v4 DISAGREEMENT — when they disagree, who's right?")
    print("=" * 78)
    for label, group in (("All", rows), ("Tradeable", tradeable)):
        agree = sum(1 for r in group if r["v5_dir"] == r["v4_dir"])
        disagree = [r for r in group if r["v5_dir"] != r["v4_dir"]]
        v5_right_on_disagreement = sum(1 for r in disagree if correct(r, "v5"))
        v4_right_on_disagreement = sum(1 for r in disagree if correct(r, "v4"))
        both_wrong = len(disagree) - v5_right_on_disagreement - v4_right_on_disagreement
        n = len(group)
        print(f"  {label} (N={n}):")
        print(f"    v5 == v4: {agree:>5} ({agree/n*100 if n else 0:>5.1f}%)")
        print(f"    disagree: {len(disagree):>5} ({len(disagree)/n*100 if n else 0:>5.1f}%)")
        if disagree:
            nd = len(disagree)
            print(f"      → v5 correct: {v5_right_on_disagreement} "
                  f"({v5_right_on_disagreement/nd*100:.1f}%)")
            print(f"      → v4 correct: {v4_right_on_disagreement} "
                  f"({v4_right_on_disagreement/nd*100:.1f}%)")
            print(f"      → both wrong/neutral: {both_wrong} "
                  f"({both_wrong/nd*100:.1f}%)")
        print()

    # ── DTE bucket breakdown on tradeable ─────────────────────────────
    print("=" * 78)
    print("Tradeable subset by DTE bucket")
    print("=" * 78)
    by_dte = defaultdict(list)
    for r in tradeable:
        by_dte[r.get("dte_bucket", "UNK")].append(r)
    for k in ("0", "1", "2", "3+", "UNK"):
        if k not in by_dte: continue
        report_section(f"DTE={k}", by_dte[k])
    print()

    # ── Pass/fail decision gate per operator spec ─────────────────────
    print("=" * 78)
    print("DECISION GATE (per spec)")
    print("=" * 78)
    tu = [r for r in tradeable if r["move_dir"] == "UP"]
    td = [r for r in tradeable if r["move_dir"] == "DOWN"]
    if tu:
        rate_u = sum(1 for r in tu if correct(r, "v5")) / len(tu) * 100
    else:
        rate_u = 0
    if td:
        rate_d = sum(1 for r in td if correct(r, "v5")) / len(td) * 100
    else:
        rate_d = 0
    print(f"  Tradeable UP correctness:   v5={rate_u:.1f}%   target ≥70%   "
          f"→ {'PASS' if rate_u >= 70 else 'FAIL'}")
    print(f"  Tradeable DOWN correctness: v5={rate_d:.1f}%   target ≥70%   "
          f"→ {'PASS' if rate_d >= 70 else 'FAIL'}")
    if rate_u >= 70 and rate_d >= 70:
        print(f"  → BOTH PASS. v5 ready for replay validation, then deploy.")
    elif rate_u >= 70 or rate_d >= 70:
        print(f"  → ASYMMETRIC. One bar met, one not. Investigate.")
    else:
        print(f"  → BOTH FAIL. Structure-first assumption is not enough. "
              f"Redesign needed.")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
