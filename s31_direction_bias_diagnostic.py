"""
s31_direction_bias_diagnostic.py — find which input to direction_bias
is responsible for the 54% wrong-direction rate on tradeable moves.

Reads working_back.jsonl, finds the 208 tradeable events, for each:
  - Locates the nearest signal_snapshots row within ±5 min
  - Extracts: direction_bias, momentum_direction, breadth_regime,
    wcb_regime, ret_session, gamma_regime, confidence_score, raw
  - Compares against the actual move direction

Reports:
  1. wcb_regime NULL rate at tradeable events (is TD-035 still active?)
  2. momentum_direction vs actual move direction confusion matrix
  3. ret_session value distribution at tradeable events (sign vs move)
  4. Cross-tabs: direction_bias × momentum_direction × actual move
  5. The "where the call went wrong" decomposition

Usage:
    python s31_direction_bias_diagnostic.py
    python s31_direction_bias_diagnostic.py working_back.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
_MS_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")
SIGNAL_LOOKUP_MIN = 5


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
p.add_argument("path", nargs="?", default="working_back.jsonl")
args = p.parse_args()


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
    if s.endswith("+00"): s = s[:-3] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ── Probe signal_snapshots column inventory once ─────────────────────

def get_columns():
    """Fetch a single row; return list of present column names."""
    rows = (SB.table("signal_snapshots")
            .select("*").limit(1).execute().data) or []
    if not rows:
        return []
    return list(rows[0].keys())


def fetch_signal_row(symbol, event_ts):
    """Find signal_snapshots row within ±5min of event_ts.
    Returns the closest row with ALL columns, or None."""
    lo = (event_ts - timedelta(minutes=SIGNAL_LOOKUP_MIN)).isoformat()
    hi = (event_ts + timedelta(minutes=SIGNAL_LOOKUP_MIN)).isoformat()
    try:
        rows = (SB.table("signal_snapshots")
                .select("*")
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


def get_nested(row, key):
    """Try top-level then raw JSONB."""
    if key in row and row[key] is not None:
        return row[key]
    raw = row.get("raw")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = None
    if isinstance(raw, dict):
        return raw.get(key)
    return None


# ── Main ─────────────────────────────────────────────────────────────

def main():
    # Load tradeable events
    events = []
    with open(args.path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                r = json.loads(line)
                if r.get("was_tradeable"):
                    events.append(r)
            except json.JSONDecodeError:
                continue
    print(f"Loaded {len(events)} tradeable events from {args.path}")
    if not events:
        return 0

    # Probe columns
    cols = get_columns()
    print(f"signal_snapshots top-level columns: {len(cols)}")
    direction_relevant = [c for c in cols if any(
        k in c.lower() for k in ["direction", "momentum", "breadth",
                                  "regime", "ret_", "wcb", "confidence",
                                  "v4", "bias"])]
    print(f"Direction-relevant columns present: {direction_relevant}")
    print()

    # Enrich each event with the signal_snapshots row
    enriched = []
    print(f"Fetching signal rows for {len(events)} events ...")
    for i, e in enumerate(events, 1):
        if i % 50 == 0:
            print(f"  {i}/{len(events)}")
        ts = parse_ts(e["event_ts"])
        if ts is None: continue
        row = fetch_signal_row(e["symbol"], ts)
        if row is None: continue
        e["_signal"] = row
        enriched.append(e)
    print(f"  Resolved {len(enriched)}/{len(events)} events to signal rows")
    print()

    # ── 1. wcb_regime NULL rate (TD-035 check) ────────────────────────
    wcb_null = sum(1 for e in enriched if get_nested(e["_signal"], "wcb_regime") is None)
    print(f"=" * 78)
    print(f"1. TD-035 CHECK — wcb_regime NULL rate")
    print(f"=" * 78)
    print(f"  Tradeable events with wcb_regime=NULL: "
          f"{wcb_null}/{len(enriched)} "
          f"({wcb_null/len(enriched)*100 if enriched else 0:.1f}%)")
    if wcb_null == len(enriched):
        print(f"  → TD-035 ACTIVE. wcb_regime never populated at any tradeable event.")
    elif wcb_null > len(enriched) * 0.9:
        print(f"  → TD-035 mostly active. wcb_regime missing on >90% of tradeable events.")
    elif wcb_null > 0:
        print(f"  → wcb_regime intermittent. Inspect.")
    else:
        print(f"  → wcb_regime always populated.")
    print()

    # ── 2. momentum_direction × actual move direction ────────────────
    print(f"=" * 78)
    print(f"2. momentum_direction × actual move direction")
    print(f"=" * 78)
    confusion = defaultdict(Counter)
    for e in enriched:
        mom = get_nested(e["_signal"], "momentum_direction") or "MISSING"
        act = e["direction"]
        confusion[act][str(mom).upper()] += 1
    print(f"{'Actual move':<14}{'BULLISH':>10}{'BEARISH':>10}{'NEUTRAL':>10}"
          f"{'MISSING':>10}{'OTHER':>10}")
    for act in ("UP", "DOWN"):
        c = confusion[act]
        other = sum(v for k, v in c.items()
                    if k not in ("BULLISH", "BEARISH", "NEUTRAL", "MISSING"))
        print(f"{act:<14}{c.get('BULLISH', 0):>10}{c.get('BEARISH', 0):>10}"
              f"{c.get('NEUTRAL', 0):>10}{c.get('MISSING', 0):>10}{other:>10}")
    print()
    # Read: of UP moves, what % had BULLISH momentum_direction?
    up_n = sum(confusion["UP"].values())
    dn_n = sum(confusion["DOWN"].values())
    if up_n:
        print(f"  UP moves with momentum_direction=BULLISH: "
              f"{confusion['UP'].get('BULLISH', 0)}/{up_n} "
              f"({confusion['UP'].get('BULLISH', 0)/up_n*100:.1f}%)")
    if dn_n:
        print(f"  DOWN moves with momentum_direction=BEARISH: "
              f"{confusion['DOWN'].get('BEARISH', 0)}/{dn_n} "
              f"({confusion['DOWN'].get('BEARISH', 0)/dn_n*100:.1f}%)")
    print()

    # ── 3. ret_session distribution ──────────────────────────────────
    print(f"=" * 78)
    print(f"3. ret_session at tradeable events (the V4 numerical input)")
    print(f"=" * 78)
    up_rets, dn_rets = [], []
    for e in enriched:
        r = get_nested(e["_signal"], "ret_session")
        if r is None: continue
        try:
            r = float(r)
        except (TypeError, ValueError):
            continue
        if e["direction"] == "UP": up_rets.append(r)
        else: dn_rets.append(r)
    def stats(xs):
        if not xs: return "(none)"
        return (f"N={len(xs):>3}  mean={statistics.mean(xs):>+7.3f}  "
                f"median={statistics.median(xs):>+7.3f}  "
                f"min={min(xs):>+7.3f}  max={max(xs):>+7.3f}")
    print(f"  On UP-move events:   {stats(up_rets)}")
    print(f"  On DOWN-move events: {stats(dn_rets)}")
    if up_rets:
        neg_at_up = sum(1 for r in up_rets if r < 0)
        print(f"  UP moves where ret_session was NEGATIVE: "
              f"{neg_at_up}/{len(up_rets)} "
              f"({neg_at_up/len(up_rets)*100:.1f}%)")
    if dn_rets:
        pos_at_dn = sum(1 for r in dn_rets if r > 0)
        print(f"  DOWN moves where ret_session was POSITIVE: "
              f"{pos_at_dn}/{len(dn_rets)} "
              f"({pos_at_dn/len(dn_rets)*100:.1f}%)")
    print()

    # ── 4. direction_bias × actual move ──────────────────────────────
    print(f"=" * 78)
    print(f"4. direction_bias × actual move direction")
    print(f"=" * 78)
    bias_conf = defaultdict(Counter)
    for e in enriched:
        b = (get_nested(e["_signal"], "direction_bias") or "MISSING").upper()
        bias_conf[e["direction"]][b] += 1
    print(f"{'Actual move':<14}{'BULLISH':>10}{'BEARISH':>10}{'NEUTRAL':>10}"
          f"{'MISSING':>10}")
    for act in ("UP", "DOWN"):
        c = bias_conf[act]
        print(f"{act:<14}{c.get('BULLISH', 0):>10}{c.get('BEARISH', 0):>10}"
              f"{c.get('NEUTRAL', 0):>10}{c.get('MISSING', 0):>10}")
    up_n = sum(bias_conf["UP"].values())
    dn_n = sum(bias_conf["DOWN"].values())
    print()
    if up_n:
        wr_up = bias_conf["UP"].get("BULLISH", 0) / up_n * 100
        print(f"  UP moves where direction_bias was correct (BULLISH): "
              f"{bias_conf['UP'].get('BULLISH', 0)}/{up_n} ({wr_up:.1f}%)")
    if dn_n:
        wr_dn = bias_conf["DOWN"].get("BEARISH", 0) / dn_n * 100
        print(f"  DOWN moves where direction_bias was correct (BEARISH): "
              f"{bias_conf['DOWN'].get('BEARISH', 0)}/{dn_n} ({wr_dn:.1f}%)")
    print()

    # ── 5. Decomposition: where did the call go wrong? ───────────────
    print(f"=" * 78)
    print(f"5. Decomposition — direction_bias × momentum_direction × move")
    print(f"=" * 78)
    triplets = Counter()
    for e in enriched:
        db = (get_nested(e["_signal"], "direction_bias") or "MISSING").upper()
        md = (get_nested(e["_signal"], "momentum_direction") or "MISSING").upper()
        triplets[(e["direction"], md, db)] += 1
    print(f"  Actual move | momentum_direction | direction_bias | N | %")
    print(f"  " + "-" * 70)
    total = sum(triplets.values())
    for key, n in sorted(triplets.items(), key=lambda x: -x[1]):
        act, md, db = key
        print(f"  {act:<12} {md:<19} {db:<15} {n:>4} "
              f"{n/total*100 if total else 0:>5.1f}%")
    print()

    # ── 6. Where does momentum_direction itself come from? ───────────
    print(f"=" * 78)
    print(f"6. raw JSONB inspection — what's inside one tradeable event")
    print(f"=" * 78)
    if enriched:
        sample = enriched[0]
        sig = sample["_signal"]
        raw = sig.get("raw")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = None
        if isinstance(raw, dict):
            print(f"  Event: {sample['event_ts']} {sample['symbol']} "
                  f"{sample['direction']} {sample['net_move_pts']}pts")
            print(f"  raw JSONB keys (filter to direction-relevant):")
            for k in sorted(raw.keys()):
                if any(s in k.lower() for s in
                       ["direction", "momentum", "breadth", "regime",
                        "ret_", "wcb", "v4", "bias", "confidence"]):
                    print(f"    {k}: {raw[k]}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
