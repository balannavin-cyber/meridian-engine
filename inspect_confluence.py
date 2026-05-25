"""
inspect_confluence.py — read confluence.jsonl and report.

Usage:
    python inspect_confluence.py
    python inspect_confluence.py confluence.jsonl
    python inspect_confluence.py --grep 2026-05-15T11:26
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter


p = argparse.ArgumentParser()
p.add_argument("path", nargs="?", default="confluence.jsonl")
p.add_argument("--grep", default=None,
               help="Show full records whose ts starts with this prefix. "
                    "Example: --grep 2026-05-15T11:26 for a 1-minute window.")
args = p.parse_args()


def main() -> int:
    total = 0
    has_htf_zone = 0
    has_intraday_zone = 0
    has_both = 0
    has_only_intraday = 0
    has_only_htf = 0
    has_neither = 0

    htf_aligned_blocked = 0       # HTF-aligned action but trade_allowed=false
    htf_opposed_blocked = 0       # HTF-opposed action and trade_allowed=false
    htf_opposed_passed = 0        # HTF-opposed action and trade_allowed=true
    htf_aligned_passed = 0
    htf_dir_dist = Counter()
    action_dist = Counter()

    matches = []

    with open(args.path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1

            sources = [z.get("source") for z in r.get("containing_zones", [])]
            has_h = "htf" in sources
            has_i = "intraday" in sources
            if has_h:
                has_htf_zone += 1
            if has_i:
                has_intraday_zone += 1
            if has_h and has_i:
                has_both += 1
            elif has_i and not has_h:
                has_only_intraday += 1
            elif has_h and not has_i:
                has_only_htf += 1
            else:
                has_neither += 1

            s = r.get("summary", {})
            htf_dir_dist[s.get("dominant_htf_direction")] += 1
            action_dist[r.get("action")] += 1

            aligned = s.get("htf_aligned_with_action")
            allowed = bool(r.get("trade_allowed"))
            if aligned is True and not allowed:
                htf_aligned_blocked += 1
            elif aligned is True and allowed:
                htf_aligned_passed += 1
            elif aligned is False and not allowed:
                htf_opposed_blocked += 1
            elif aligned is False and allowed:
                htf_opposed_passed += 1

            # Optional grep
            if args.grep and r.get("ts", "").startswith(args.grep):
                matches.append(r)

    if args.grep:
        if not matches:
            print(f"No records found with ts starting '{args.grep}'.")
            print(f"Hint: format is 2026-05-15T11:26 (UTC). "
                  f"Subtract 5h30m from your IST time.")
            return 0
        print(f"Found {len(matches)} record(s) matching '{args.grep}':\n")
        for m in matches:
            print(json.dumps(m, indent=2, default=str))
            print()
        return 0

    print(f"File: {args.path}")
    print(f"Total records: {total:,}")
    print()
    print(f"Containment by zone source:")
    print(f"  Has at least 1 HTF (W/D/H) zone:    {has_htf_zone:>5,}  "
          f"({has_htf_zone/total*100 if total else 0:>5.1f}%)")
    print(f"  Has at least 1 intraday zone:       {has_intraday_zone:>5,}  "
          f"({has_intraday_zone/total*100 if total else 0:>5.1f}%)")
    print(f"  Has BOTH HTF + intraday:            {has_both:>5,}  "
          f"({has_both/total*100 if total else 0:>5.1f}%)")
    print(f"  Has only intraday (no HTF):         {has_only_intraday:>5,}  "
          f"({has_only_intraday/total*100 if total else 0:>5.1f}%)")
    print(f"  Has only HTF (no intraday):         {has_only_htf:>5,}  "
          f"({has_only_htf/total*100 if total else 0:>5.1f}%)")
    print(f"  Has neither (no man's land):        {has_neither:>5,}  "
          f"({has_neither/total*100 if total else 0:>5.1f}%)")
    print()
    print(f"Dominant HTF direction distribution:")
    for k, v in htf_dir_dist.most_common():
        print(f"  {str(k):<8}  {v:>5,}  ({v/total*100 if total else 0:>5.1f}%)")
    print()
    print(f"signal_snapshots.action distribution:")
    for k, v in action_dist.most_common():
        print(f"  {str(k):<14}  {v:>5,}  ({v/total*100 if total else 0:>5.1f}%)")
    print()
    print(f"HTF-action alignment vs trade_allowed (only rows where alignment defined):")
    print(f"  HTF-aligned    + traded:    {htf_aligned_passed:>5,}")
    print(f"  HTF-aligned    + blocked:   {htf_aligned_blocked:>5,}")
    print(f"  HTF-opposed    + traded:    {htf_opposed_passed:>5,}")
    print(f"  HTF-opposed    + blocked:   {htf_opposed_blocked:>5,}")
    aligned_total = htf_aligned_passed + htf_aligned_blocked
    opposed_total = htf_opposed_passed + htf_opposed_blocked
    if aligned_total:
        ar = htf_aligned_passed / aligned_total * 100
        print(f"  → Of HTF-ALIGNED setups, MERDIAN traded {ar:.1f}% "
              f"({htf_aligned_passed}/{aligned_total})")
    if opposed_total:
        opr = htf_opposed_passed / opposed_total * 100
        print(f"  → Of HTF-OPPOSED setups, MERDIAN traded {opr:.1f}% "
              f"({htf_opposed_passed}/{opposed_total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
