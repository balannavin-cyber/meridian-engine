"""
s31_confluence_emitter.py — multi-timeframe zone confluence per signal row.

Reads BOTH ict_zones (intraday) and ict_htf_zones (W/D/H), reconstructs
validity at each signal_ts via timestamp predicates, emits the FULL list
of zones containing spot at that moment. No single-zone selection. No
tier filter. No direction filter. No status filter (uses
timestamp-based reconstruction instead).

LIVE DATA ONLY:
  - ict_zones — written cycle-by-cycle by detect_ict_patterns_runner.py
  - ict_htf_zones — written by build_ict_htf_zones.py
  - signal_snapshots — written cycle-by-cycle by build_trade_signal_local.py
  Reads ts, symbol, spot, direction_bias, action, trade_allowed, atm_strike
  from signal_snapshots. Does NOT read ict_pattern (the backfilled field).

Output: JSONL file (one JSON record per line) for grep/jq/manual inspection.

Each output record:
{
  "id": <signal_snapshots.id>,
  "ts": "<UTC iso>",
  "symbol": "NIFTY|SENSEX",
  "spot": float,
  "direction_bias": "<BULLISH|BEARISH|NEUTRAL|UNKNOWN>",
  "action": "<BUY_CE|BUY_PE|DO_NOTHING>",
  "trade_allowed": bool,
  "atm_strike": int,
  "containing_zones": [
    {
      "source": "intraday|htf",
      "timeframe": "5m|H|D|W",
      "pattern_type": "BULL_OB|BEAR_OB|BULL_FVG|BEAR_FVG|JUDAS_BULL",
      "direction": 1 | -1,
      "zone_low": float, "zone_high": float, "width": float,
      "distance_to_mid_pct": float,  // signed: + = spot above mid
      "ict_tier": "TIER1|TIER2|TIER3|SKIP|NULL",
      "detected_at_ts": "<UTC iso>",
      "age_minutes": int,
      "zone_id": "<uuid>"
    },
    ...
  ],
  "summary": {
    "bull_zone_count": int,
    "bear_zone_count": int,
    "total_zone_count": int,
    "dominant_htf_direction": "BULL|BEAR|MIXED|NONE",
    "highest_tf_present": "W|D|H|5m|NONE",
    "tightest_zone_pattern": "<pattern>|NONE",
    "tightest_zone_timeframe": "<tf>|NONE",
    "htf_aligned_with_action": bool | null
  }
}

Usage (Local):
    python s31_confluence_emitter.py
    python s31_confluence_emitter.py --start-date 2026-04-15 --end-date 2026-05-15
    python s31_confluence_emitter.py --symbol NIFTY
    python s31_confluence_emitter.py --output confluence_2026-05.jsonl

Then inspect:
    # Count rows with no containing zone (MERDIAN saw nothing here)
    grep '"total_zone_count": 0' confluence.jsonl | wc -l

    # Find rows where intraday direction conflicts with HTF
    jq 'select(.summary.htf_aligned_with_action == false)' confluence.jsonl

    # Find your manual-trade timestamps in the confluence stream
    grep '2026-05-15T05:56' confluence.jsonl | jq .

    # Histogram of confluence counts
    jq -r '.summary.total_zone_count' confluence.jsonl | sort | uniq -c
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date as _date

from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
TF_RANK = {"W": 0, "D": 1, "H": 2, "5m": 3, "1m": 4}
_MS_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
p.add_argument("--start-date", default="2026-03-23")
p.add_argument("--end-date",   default="2026-05-15")
p.add_argument("--symbols",    default="NIFTY,SENSEX")
p.add_argument("--output",     default="confluence.jsonl")
args = p.parse_args()

SYMBOLS = [s.strip().upper() for s in args.symbols.split(",")]


# ── Supabase ──────────────────────────────────────────────────────────

load_dotenv()
SB = create_client(
    os.getenv("SUPABASE_URL").strip(),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
)


# ── TS helpers ────────────────────────────────────────────────────────

def _norm_us(s):
    m = _MS_RE.search(s)
    if not m:
        return s
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6:
        return s
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MS_RE.sub(f".{frac6}{tz}", s)


def parse_ts(s):
    if not s:
        return None
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


def ist_date(ts_str):
    dt = parse_ts(ts_str)
    return dt.astimezone(IST).date().isoformat() if dt else ""


# ── Fetch ─────────────────────────────────────────────────────────────

def fetch_signals(symbol):
    out, page = [], 0
    PAGE = 1000
    cols = ("id,ts,symbol,spot,direction_bias,action,trade_allowed,atm_strike")
    while True:
        rows = (SB.table("signal_snapshots")
                .select(cols)
                .eq("symbol", symbol)
                .gte("ts", f"{args.start_date}T00:00:00+00:00")
                .lte("ts", f"{args.end_date}T23:59:59+00:00")
                .order("ts")
                .range(page * PAGE, (page + 1) * PAGE - 1)
                .execute().data)
        if not rows:
            break
        out.extend(rows)
        if len(rows) < PAGE:
            break
        page += 1
    return out


def fetch_intraday_zones(symbol, trade_date):
    """All intraday zones for symbol × date. Status not filtered — we
    reconstruct validity by timestamp."""
    return (SB.table("ict_zones")
            .select("id,pattern_type,direction,zone_low,zone_high,"
                    "ict_tier,mtf_context,detected_at_ts,broken_at_ts,status")
            .eq("symbol", symbol)
            .eq("trade_date", trade_date)
            .execute().data) or []


def fetch_htf_zones(symbol, trade_date):
    """HTF zones (W/D/H) valid for this trade_date.

    valid_to predicate accepts NULL — many ACTIVE zones have indefinite
    validity (no terminal expiry until BREACHED). Excluding NULL via
    .gte('valid_to', ...) silently dropped 80%+ of ACTIVE zones in earlier
    versions of this script. Use .or_() to accept (valid_to IS NULL) OR
    (valid_to >= trade_date)."""
    return (SB.table("ict_htf_zones")
            .select("id,timeframe,pattern_type,direction,zone_low,zone_high,"
                    "status,valid_from,valid_to,source_bar_date")
            .eq("symbol", symbol)
            .lte("valid_from", trade_date)
            .or_(f"valid_to.is.null,valid_to.gte.{trade_date}")
            .execute().data) or []


# ── Containment + summary ────────────────────────────────────────────

def intraday_valid_at(zone, signal_ts):
    """Intraday zone validity at signal_ts via timestamp reconstruction."""
    det = parse_ts(zone.get("detected_at_ts"))
    if det is None or det > signal_ts:
        return False
    brk = parse_ts(zone.get("broken_at_ts"))
    if brk is not None and brk <= signal_ts:
        return False
    return True


def htf_valid_at(zone, signal_ts):
    """HTF zone validity at signal_ts. Conservative: include if
    status='ACTIVE' OR (status='BREACHED' AND breach is after signal_ts).
    ict_htf_zones doesn't have a broken_at_ts column on every row; rely
    on status + valid_from/valid_to predicate as primary."""
    # valid_from/valid_to already filtered in query; trust status here
    return zone.get("status") in ("ACTIVE", "BREACHED")


def contains(zone, spot):
    try:
        zl = float(zone["zone_low"])
        zh = float(zone["zone_high"])
    except (TypeError, ValueError, KeyError):
        return False
    return zl <= spot <= zh


def emit_zone(zone, spot, signal_ts, source, default_tf):
    zl = float(zone["zone_low"])
    zh = float(zone["zone_high"])
    width = zh - zl
    mid = (zl + zh) / 2
    dist_pct = (spot - mid) / mid * 100 if mid else 0.0
    det = parse_ts(zone.get("detected_at_ts"))
    age = int((signal_ts - det).total_seconds() / 60) if det else None
    tf = zone.get("timeframe") or default_tf
    return {
        "source": source,
        "timeframe": tf,
        "pattern_type": zone["pattern_type"],
        "direction": int(zone.get("direction") or 0),
        "zone_low": round(zl, 2),
        "zone_high": round(zh, 2),
        "width": round(width, 2),
        "distance_to_mid_pct": round(dist_pct, 3),
        "ict_tier": zone.get("ict_tier"),
        "mtf_context": zone.get("mtf_context"),
        "detected_at_ts": (zone.get("detected_at_ts") or "")[:19],
        "age_minutes": age,
        "zone_id": zone.get("id"),
        "status": zone.get("status"),
    }


def compute_summary(zones, signal_action):
    bulls = [z for z in zones if z["direction"] == 1]
    bears = [z for z in zones if z["direction"] == -1]

    # HTF-only zones (W/D/H) for dominant direction
    htf_only = [z for z in zones if z["source"] == "htf"]
    htf_bulls = sum(1 for z in htf_only if z["direction"] == 1)
    htf_bears = sum(1 for z in htf_only if z["direction"] == -1)
    if not htf_only:
        dom = "NONE"
    elif htf_bulls > htf_bears:
        dom = "BULL"
    elif htf_bears > htf_bulls:
        dom = "BEAR"
    else:
        dom = "MIXED"

    # Highest timeframe present
    if zones:
        tf_present = sorted(set(z["timeframe"] for z in zones),
                            key=lambda t: TF_RANK.get(t, 99))
        highest = tf_present[0]
    else:
        highest = "NONE"

    # Tightest containing zone
    if zones:
        tightest = min(zones, key=lambda z: z["width"])
        tight_pat = tightest["pattern_type"]
        tight_tf = tightest["timeframe"]
    else:
        tight_pat = "NONE"
        tight_tf = "NONE"

    # HTF-aligned with action?
    aligned = None
    if dom != "NONE" and signal_action in ("BUY_CE", "BUY_PE"):
        action_dir = 1 if signal_action == "BUY_CE" else -1
        dom_dir = 1 if dom == "BULL" else (-1 if dom == "BEAR" else 0)
        if dom_dir != 0:
            aligned = (action_dir == dom_dir)

    return {
        "bull_zone_count": len(bulls),
        "bear_zone_count": len(bears),
        "total_zone_count": len(zones),
        "htf_bull_count": htf_bulls,
        "htf_bear_count": htf_bears,
        "dominant_htf_direction": dom,
        "highest_tf_present": highest,
        "tightest_zone_pattern": tight_pat,
        "tightest_zone_timeframe": tight_tf,
        "htf_aligned_with_action": aligned,
    }


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print(f"S31 confluence emitter")
    print(f"Cohort: {args.start_date} → {args.end_date}  symbols={SYMBOLS}")
    print(f"Output: {args.output}")
    print(f"Data sources: ict_zones + ict_htf_zones + signal_snapshots "
          f"(LIVE only; ict_pattern column NOT read)")
    print()

    out_f = open(args.output, "w", encoding="utf-8")
    total_written = 0
    histogram = defaultdict(int)

    try:
        for symbol in SYMBOLS:
            print(f"=== {symbol} ===")
            sigs = fetch_signals(symbol)
            print(f"  signal_snapshots rows: {len(sigs):,}")
            if not sigs:
                continue

            # Group signals by IST trade_date
            sigs_by_date = defaultdict(list)
            for r in sigs:
                d = ist_date(r["ts"])
                if d:
                    sigs_by_date[d].append(r)

            # Per-day, fetch zones once
            for d in sorted(sigs_by_date):
                intra = fetch_intraday_zones(symbol, d)
                htf = fetch_htf_zones(symbol, d)
                day_rows = sigs_by_date[d]

                for r in day_rows:
                    signal_ts = parse_ts(r["ts"])
                    if signal_ts is None:
                        continue
                    spot = float(r.get("spot") or 0)
                    if spot <= 0:
                        continue

                    # Intraday: timestamp-validity reconstruction
                    intra_match = []
                    for z in intra:
                        if not intraday_valid_at(z, signal_ts):
                            continue
                        if not contains(z, spot):
                            continue
                        intra_match.append(
                            emit_zone(z, spot, signal_ts,
                                      source="intraday", default_tf="5m")
                        )

                    # HTF: valid_from/valid_to + status filter, then containment
                    htf_match = []
                    for z in htf:
                        if not htf_valid_at(z, signal_ts):
                            continue
                        if not contains(z, spot):
                            continue
                        htf_match.append(
                            emit_zone(z, spot, signal_ts,
                                      source="htf",
                                      default_tf=z.get("timeframe") or "?")
                        )

                    all_zones = intra_match + htf_match
                    summary = compute_summary(all_zones, r.get("action"))

                    record = {
                        "id": r["id"],
                        "ts": (r.get("ts") or "")[:19],
                        "ts_ist": (signal_ts.astimezone(IST).isoformat()[:19]),
                        "symbol": r["symbol"],
                        "spot": spot,
                        "direction_bias": r.get("direction_bias"),
                        "action": r.get("action"),
                        "trade_allowed": r.get("trade_allowed"),
                        "atm_strike": r.get("atm_strike"),
                        "containing_zones": all_zones,
                        "summary": summary,
                    }
                    out_f.write(json.dumps(record, default=str) + "\n")
                    total_written += 1
                    histogram[summary["total_zone_count"]] += 1

                if len(day_rows) > 0:
                    print(f"    {d}: {len(day_rows):>4} signals  "
                          f"(intraday zones={len(intra):>3}  "
                          f"htf zones={len(htf):>3})")
            print()
    finally:
        out_f.close()

    # Summary stats
    print("=" * 78)
    print(f"Wrote {total_written:,} records to {args.output}")
    print()
    print("Confluence count distribution (zones containing spot at signal_ts):")
    for cnt in sorted(histogram):
        bar = "#" * min(60, histogram[cnt] // max(1, total_written // 60))
        print(f"  {cnt} zones: {histogram[cnt]:>5}  {bar}")
    print()
    print("Quick inspection commands:")
    print(f"  # Rows where MERDIAN saw nothing:")
    print(f"  grep '\"total_zone_count\": 0' {args.output} | wc -l")
    print(f"  # Rows with HTF zone present (W/D/H containment):")
    print(f"  jq 'select(.summary.dominant_htf_direction != \"NONE\")' "
          f"{args.output} | head -100")
    print(f"  # Rows where signal action opposes dominant HTF direction:")
    print(f"  jq 'select(.summary.htf_aligned_with_action == false)' "
          f"{args.output} | wc -l")
    print(f"  # Inspect a specific timestamp (replace YYYY-MM-DDTHH:MM):")
    print(f"  grep '2026-05-15T05:56' {args.output} | jq .")
    return 0


if __name__ == "__main__":
    sys.exit(main())
