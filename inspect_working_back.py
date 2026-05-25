"""
inspect_working_back.py — aggregate report on working_back.jsonl events.

Reports:
  - Total events by (symbol, magnitude tier, direction)
  - Tradeable rate by (tier, direction)
  - Observability chain: of N events, how many at each layer
    L1 (HTF saw it) → L2 (intraday saw it) → L3 (signal direction aligned)
    → L4 (gates passed)
  - By DTE bucket (0, 1, 2, 3+)
  - Whipsaw analysis
  - Where the chain breaks: most common drop points

Usage:
    python inspect_working_back.py
    python inspect_working_back.py working_back.jsonl
    python inspect_working_back.py --grep 2026-05-15T05:56
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict


p = argparse.ArgumentParser()
p.add_argument("path", nargs="?", default="working_back.jsonl")
p.add_argument("--grep", default=None,
               help="Show full records whose event_ts starts with prefix")
p.add_argument("--tradeable-only", action="store_true",
               help="Restrict to tradeable events (atm 30m P&L ≥ 20%)")
args = p.parse_args()


def main():
    events = []
    with open(args.path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if args.grep:
        matches = [e for e in events if e["event_ts"].startswith(args.grep)]
        if not matches:
            print(f"No events with event_ts starting '{args.grep}'.")
            return 0
        for m in matches:
            print(json.dumps(m, indent=2, default=str)); print()
        return 0

    if args.tradeable_only:
        before = len(events)
        events = [e for e in events if e.get("was_tradeable")]
        print(f"Filter: tradeable-only — kept {len(events):,}/{before:,}")
        print()

    total = len(events)
    print(f"File: {args.path}")
    print(f"Total events: {total:,}")
    print()

    # ── By symbol × tier × direction ──────────────────────────────────
    print("Events by (symbol, magnitude tier, direction):")
    by_bucket = Counter()
    for e in events:
        by_bucket[(e["symbol"], e.get("magnitude_tier"), e["direction"])] += 1
    for (sym, tier, dir_), n in sorted(by_bucket.items(),
                                       key=lambda x: (x[0][0], -(x[0][1] or 0), x[0][2])):
        print(f"  {sym:<7} ≥{tier}pts {dir_:<4}: {n:>4}")
    print()

    # ── Tradeable rate ────────────────────────────────────────────────
    print("Tradeable rate (ATM 30m P&L ≥ 20%) by (symbol, tier, direction):")
    bucket_total = Counter()
    bucket_tradeable = Counter()
    for e in events:
        key = (e["symbol"], e.get("magnitude_tier"), e["direction"])
        bucket_total[key] += 1
        if e.get("was_tradeable"):
            bucket_tradeable[key] += 1
    for key in sorted(bucket_total,
                      key=lambda x: (x[0], -(x[1] or 0), x[2])):
        sym, tier, dir_ = key
        t = bucket_total[key]; tr = bucket_tradeable[key]
        pct = tr / t * 100 if t else 0
        print(f"  {sym:<7} ≥{tier}pts {dir_:<4}: {tr:>4}/{t:<4} ({pct:>5.1f}%)")
    print()

    # ── Whipsaw analysis ──────────────────────────────────────────────
    n_whip = sum(1 for e in events if e.get("was_whipsaw"))
    n_whip_tradeable = sum(1 for e in events
                            if e.get("was_whipsaw") and e.get("was_tradeable"))
    print(f"Whipsaw events (max_adverse > 0.5 × abs(net_move)): "
          f"{n_whip:,}/{total:,} ({n_whip/total*100 if total else 0:.1f}%)")
    print(f"  of those, also tradeable: {n_whip_tradeable:,}")
    print()

    # ── DTE bucket ────────────────────────────────────────────────────
    print("Events by DTE bucket × tradeable:")
    by_dte = defaultdict(lambda: {"total": 0, "tradeable": 0})
    for e in events:
        b = e.get("dte_bucket", "UNK")
        by_dte[b]["total"] += 1
        if e.get("was_tradeable"):
            by_dte[b]["tradeable"] += 1
    for dte_b in ("0", "1", "2", "3+", "UNK"):
        if dte_b not in by_dte: continue
        d = by_dte[dte_b]
        pct = d["tradeable"] / d["total"] * 100 if d["total"] else 0
        print(f"  DTE={dte_b:<4} total={d['total']:>4}  "
              f"tradeable={d['tradeable']:>4} ({pct:>5.1f}%)")
    print()

    # ── Observability chain ───────────────────────────────────────────
    print("Observability chain — how many events did MERDIAN see?")
    print()
    print("  Layer                                  N      pct")
    print("  ---------------------------------- ----- ------")
    L1 = sum(1 for e in events if e["layers"].get("L1_htf_aligned"))
    L2 = sum(1 for e in events if e["layers"].get("L2_intraday_aligned"))
    L3 = sum(1 for e in events if e["layers"].get("L3_signal_aligned"))
    L4 = sum(1 for e in events if e["layers"].get("L4_trade_allowed"))
    pct = lambda x: f"{x/total*100 if total else 0:>5.1f}%"
    print(f"  L1: HTF zone matching direction  {L1:>5} {pct(L1)}")
    print(f"  L2: intraday zone in [t-15, t]    {L2:>5} {pct(L2)}")
    print(f"  L3: direction_bias aligned        {L3:>5} {pct(L3)}")
    print(f"  L4: trade_allowed + action match  {L4:>5} {pct(L4)}")
    print()

    # Layer-chain combinations: where does the chain break?
    print("Layer-chain combinations (L1L2L3L4):")
    combo = Counter()
    for e in events:
        l = e["layers"]
        key = (
            "✓" if l.get("L1_htf_aligned") else "·",
            "✓" if l.get("L2_intraday_aligned") else "·",
            "✓" if l.get("L3_signal_aligned") else "·",
            "✓" if l.get("L4_trade_allowed") else "·",
        )
        combo[key] += 1
    for key, n in combo.most_common():
        bar = "#" * min(50, n * 50 // max(1, total))
        print(f"  L1={key[0]} L2={key[1]} L3={key[2]} L4={key[3]}  "
              f"{n:>5}  {bar}")
    print()

    # Tradeable subset chain — the most important table
    tradeable = [e for e in events if e.get("was_tradeable")]
    if tradeable:
        print(f"Tradeable subset only (N={len(tradeable):,}):")
        print(f"  Layer                                  N      pct")
        print(f"  ---------------------------------- ----- ------")
        L1t = sum(1 for e in tradeable if e["layers"].get("L1_htf_aligned"))
        L2t = sum(1 for e in tradeable if e["layers"].get("L2_intraday_aligned"))
        L3t = sum(1 for e in tradeable if e["layers"].get("L3_signal_aligned"))
        L4t = sum(1 for e in tradeable if e["layers"].get("L4_trade_allowed"))
        nt = len(tradeable)
        ptc = lambda x: f"{x/nt*100 if nt else 0:>5.1f}%"
        print(f"  L1: HTF aligned                   {L1t:>5} {ptc(L1t)}")
        print(f"  L2: intraday aligned              {L2t:>5} {ptc(L2t)}")
        print(f"  L3: direction_bias aligned        {L3t:>5} {ptc(L3t)}")
        print(f"  L4: gates passed (TRADED)         {L4t:>5} {ptc(L4t)}")
        print()
        print(f"  → Of {nt} tradeable moves, MERDIAN traded {L4t} ({ptc(L4t)})")
        print()

    # MERDIAN direction analysis on tradeable
    if tradeable:
        print(f"On tradeable moves, what was MERDIAN's direction_bias?")
        dir_dist = Counter()
        for e in tradeable:
            dir_dist[e["layers"].get("merdian_direction_bias", "NONE")] += 1
        for k, n in dir_dist.most_common():
            print(f"  direction_bias={k or 'NULL':<10}  {n:>5}  "
                  f"({n/len(tradeable)*100 if tradeable else 0:>5.1f}%)")
        print()

        print(f"On tradeable moves, what was MERDIAN's action?")
        act_dist = Counter()
        for e in tradeable:
            act_dist[e["layers"].get("merdian_action", "NONE")] += 1
        for k, n in act_dist.most_common():
            print(f"  action={k or 'NULL':<14}  {n:>5}  "
                  f"({n/len(tradeable)*100 if tradeable else 0:>5.1f}%)")
        print()

    # ── Headline P&L if MERDIAN had taken every tradeable move ─────────
    if tradeable:
        total_pnl_pct = sum(e["option"]["atm_pnl_30m_pct"]
                            for e in tradeable
                            if e.get("option") is not None)
        total_pnl_peak_pct = sum(e["option"]["atm_pnl_peak_pct"]
                                  for e in tradeable
                                  if e.get("option") is not None)
        actual_pnl_pct = sum(e["option"]["atm_pnl_30m_pct"]
                              for e in tradeable
                              if e.get("option") is not None
                              and e["layers"].get("L4_trade_allowed"))
        print(f"Counterfactual aggregate P&L (sum of pct moves):")
        print(f"  All tradeable @ 30m hold: {total_pnl_pct:>+10.1f}%")
        print(f"  All tradeable @ peak:     {total_pnl_peak_pct:>+10.1f}%")
        print(f"  Only MERDIAN-traded:      {actual_pnl_pct:>+10.1f}%")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
