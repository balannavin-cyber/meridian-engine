"""
s31_p1_long_gamma_audit.py — TD-S30-NEW-5 closure (S31 P1).

Per-pattern × gamma_regime WR + P&L breakdown for ICT-tagged signals
in the post-S31-backfill cohort. Settles the question: does the
LONG_GAMMA gate in build_trade_signal_local.py systematically block
winners on OB cohorts, or is the gate correctly inverted?

Decision protocol per Assumption Register §D.13.1:
  - LONG_GAMMA WR > SHORT_GAMMA WR with N>=30 per bucket → env-disable
    LONG_GAMMA gate (set MERDIAN_LONG_GAMMA_BLOCK_DISABLE=1).
  - Otherwise → file rationale in tech_debt.md TD-S30-NEW-5 status update
    + D.13.4 follow-up. Decision must be made on live cohort evidence.

Methodology mirror of s30_gate_audit_and_ob_attachment.py Part A:
  - Cohort: ICT-tagged signal_snapshots, 8-week window default
  - Dedup: first per (symbol, IST date, ict_pattern, atm_strike)
  - Pricing: entry @ signal_ts, exit @ +30min via option_chain_snapshots
    OR historical_option_chain_snapshots (cutover 2026-05-04)
  - Win = pnl_pct > 0
  - WR with Wilson 95% CI

Run AFTER s31_ict_pattern_backfill.py --live, so the cohort reflects
S31 observational attachment (BULL_FVG +100pp / BEAR_FVG +83pp +
intraday OBs from post-2026-05-04 emission).

Usage:
    python s31_p1_long_gamma_audit.py
    python s31_p1_long_gamma_audit.py --start-date 2026-03-23 --end-date 2026-05-15
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
EXIT_OFFSET_MIN = 30
MATCH_TOL_MIN = 3
ARCHIVE_CUTOVER = datetime(2026, 5, 4, tzinfo=timezone.utc)
LIVE_TABLE = "option_chain_snapshots"
ARCHIVE_TABLE = "historical_option_chain_snapshots"

ICT_PATTERNS = ["BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"]
BULL_PATTERNS = {"BULL_OB", "BULL_FVG"}

_MS_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


# ── Args ──────────────────────────────────────────────────────────────

p = argparse.ArgumentParser()
p.add_argument("--start-date", default="2026-03-23")
p.add_argument("--end-date", default="2026-05-15")
p.add_argument("--symbols", default="NIFTY,SENSEX")
p.add_argument("--require-backfill-marker", action="store_true",
               help="Skip rows lacking raw->>'ict_pattern_backfilled' marker. "
                    "Use to restrict cohort to S31-backfilled rows only.")
args = p.parse_args()

SYMBOLS = [s.strip().upper() for s in args.symbols.split(",")]


# ── Supabase ─────────────────────────────────────────────────────────

load_dotenv()
SB = create_client(
    os.getenv("SUPABASE_URL").strip(),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip(),
)


# ── Helpers ──────────────────────────────────────────────────────────

def _norm_us(s):
    m = _MS_RE.search(s)
    if m is None:
        return s
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6:
        return s
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MS_RE.sub(f".{frac6}{tz}", s)


def parse_ts(s):
    if not s:
        return None
    s = _norm_us(s.replace(" ", "T").replace("Z", "+00:00"))
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


def has_backfill_marker(row):
    raw = row.get("raw") or {}
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            return False
    return raw.get("ict_pattern_backfilled") == "S31_observational"


def wilson_ci(wins, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - spread) / denom * 100,
            (centre + spread) / denom * 100)


# ── Cohort fetch ─────────────────────────────────────────────────────

def fetch_ict_tagged():
    out, page = [], 0
    PAGE = 1000
    cols = ("id,ts,symbol,spot,atm_strike,action,trade_allowed,"
            "expiry_date,ict_pattern,ict_tier,gamma_regime,"
            "direction_bias,raw")
    while True:
        rows = (SB.table("signal_snapshots")
                .select(cols)
                .in_("ict_pattern", ICT_PATTERNS)
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


def dedupe_first_per_setup(rows):
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: x.get("ts") or ""):
        if r.get("atm_strike") is None:
            continue
        d = ist_date(r["ts"])
        key = (r["symbol"], d, r["ict_pattern"], int(r["atm_strike"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


# ── Pricing ──────────────────────────────────────────────────────────

def _fetch_chain(table, sym, strike, opt_type, expiry, target_ts):
    lo = (target_ts - timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    hi = (target_ts + timedelta(minutes=MATCH_TOL_MIN)).isoformat()
    try:
        rows = (SB.table(table)
                .select("ts,ltp")
                .eq("symbol", sym).eq("strike", strike)
                .eq("option_type", opt_type).eq("expiry_date", expiry)
                .gte("ts", lo).lte("ts", hi)
                .order("ts").range(0, 99).execute().data)
    except Exception:
        return None
    if not rows:
        return None
    best, best_d = None, None
    for r in rows:
        rts = parse_ts(r["ts"])
        if rts is None:
            continue
        d = abs((rts - target_ts).total_seconds())
        if best_d is None or d < best_d:
            best_d, best = d, r
    return best


_CONVENTION = [None]  # mutable single-elem list for inner-fn write-through


def _fetch_chain_smart(sym, strike, opt_type, expiry, target_ts):
    primary = ARCHIVE_TABLE if target_ts < ARCHIVE_CUTOVER else LIVE_TABLE
    fb = LIVE_TABLE if primary == ARCHIVE_TABLE else ARCHIVE_TABLE
    r = _fetch_chain(primary, sym, strike, opt_type, expiry, target_ts)
    if r:
        return r
    return _fetch_chain(fb, sym, strike, opt_type, expiry, target_ts)


def price_setup(sig):
    sig_ts = parse_ts(sig["ts"])
    if sig_ts is None:
        return None
    sym, pat = sig["symbol"], sig["ict_pattern"]
    natural = "BUY_CE" if pat in BULL_PATTERNS else "BUY_PE"
    strike, expiry = sig.get("atm_strike"), sig.get("expiry_date")
    if strike is None or not expiry:
        return None

    # Convention detection (CE/PE vs CALL/PUT)
    if _CONVENTION[0]:
        ot = ("CE" if natural == "BUY_CE" else "PE") if _CONVENTION[0] == "CE/PE" \
             else ("CALL" if natural == "BUY_CE" else "PUT")
        cands = [ot]
    else:
        cands = ["CE" if natural == "BUY_CE" else "PE",
                 "CALL" if natural == "BUY_CE" else "PUT"]

    eb = None
    chosen_ot = None
    for ot in cands:
        r = _fetch_chain_smart(sym, int(strike), ot, str(expiry), sig_ts)
        if r:
            eb = r
            chosen_ot = ot
            if _CONVENTION[0] is None:
                _CONVENTION[0] = "CE/PE" if ot in ("CE", "PE") else "CALL/PUT"
            break
    if eb is None:
        return None

    xb = _fetch_chain_smart(sym, int(strike), chosen_ot, str(expiry),
                            sig_ts + timedelta(minutes=EXIT_OFFSET_MIN))
    if xb is None:
        return None

    try:
        epf, xpf = float(eb["ltp"]), float(xb["ltp"])
    except (TypeError, ValueError):
        return None
    if epf <= 0:
        return None

    return {
        "pnl_pct": (xpf - epf) / epf * 100,
        "win": xpf > epf,
        "entry_px": epf,
        "exit_px": xpf,
    }


# ── Stats ────────────────────────────────────────────────────────────

def summarize(group):
    if not group:
        return None
    pnls = sorted(g["pnl_pct"] for g in group)
    n = len(pnls)
    wins = sum(1 for g in group if g["win"])
    wr = wins / n * 100
    lo, hi = wilson_ci(wins, n)
    return {
        "n": n,
        "wr": wr,
        "wr_ci_lo": lo,
        "wr_ci_hi": hi,
        "mean": sum(pnls) / n,
        "median": pnls[n // 2],
    }


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print(f"S31 P1 LONG_GAMMA audit")
    print(f"Cohort: {args.start_date} → {args.end_date}  symbols={SYMBOLS}")
    print(f"Require backfill marker: {args.require_backfill_marker}")
    print()

    print(f"Fetching ICT-tagged signals ...", end=" ", flush=True)
    raw = fetch_ict_tagged()
    print(f"{len(raw):,}")

    if args.require_backfill_marker:
        before = len(raw)
        raw = [r for r in raw if has_backfill_marker(r)]
        print(f"  After backfill-marker filter: {len(raw):,} "
              f"(dropped {before - len(raw):,})")

    deduped = dedupe_first_per_setup(raw)
    print(f"After dedup (first per symbol×date×pattern×strike): {len(deduped):,}")
    print()

    print(f"Pricing {len(deduped):,} setups ...")
    enriched = []
    for i, sig in enumerate(deduped, 1):
        if i % 50 == 0:
            print(f"  ... {i:,}/{len(deduped):,}  priced={len(enriched):,}",
                  flush=True)
        p_ = price_setup(sig)
        if p_ is None:
            continue
        e = dict(sig)
        e.update(p_)
        enriched.append(e)
    print(f"  Priced {len(enriched):,}/{len(deduped):,}")
    print()

    if not enriched:
        print("No priced setups — cannot decide gate. Abort.")
        return 1

    # ── Per (pattern × gamma_regime) ──────────────────────────────────
    print("=" * 86)
    print(f"PER (ict_pattern × gamma_regime)")
    print("=" * 86)
    print(f"{'Pattern':<10} {'GammaRegime':<14} {'N':>5} {'WR%':>7} "
          f"{'CI_lo':>7} {'CI_hi':>7} {'Mean%':>8} {'Median%':>9}")
    print("-" * 86)

    buckets = defaultdict(list)
    for e in enriched:
        pat = e.get("ict_pattern") or "NONE"
        gr = e.get("gamma_regime") or "UNKNOWN"
        buckets[(pat, gr)].append(e)

    for pat in ICT_PATTERNS:
        for gr in ("LONG_GAMMA", "SHORT_GAMMA", "NO_FLIP", "UNKNOWN"):
            grp = buckets.get((pat, gr), [])
            s = summarize(grp)
            if s is None:
                print(f"{pat:<10} {gr:<14} {'-':>5} {'-':>7} {'-':>7} "
                      f"{'-':>7} {'-':>8} {'-':>9}")
                continue
            print(f"{pat:<10} {gr:<14} {s['n']:>5} {s['wr']:>6.1f}% "
                  f"{s['wr_ci_lo']:>6.1f}% {s['wr_ci_hi']:>6.1f}% "
                  f"{s['mean']:>+7.2f}% {s['median']:>+8.2f}%")
        print()

    # ── Decision table per D.13.1 ─────────────────────────────────────
    print("=" * 86)
    print(f"DECISION TABLE per D.13.1 — LONG_GAMMA vs SHORT_GAMMA by pattern")
    print("=" * 86)
    print(f"  Rule: env-disable LONG_GAMMA gate iff "
          f"LONG_WR > SHORT_WR with N>=30 per bucket")
    print()

    decisions = []
    for pat in ICT_PATTERNS:
        lg = summarize(buckets.get((pat, "LONG_GAMMA"), []))
        sg = summarize(buckets.get((pat, "SHORT_GAMMA"), []))
        line = f"  {pat:<10}: "
        if not lg or not sg:
            line += f"insufficient data (LG={lg['n'] if lg else 0}, "
            line += f"SG={sg['n'] if sg else 0}) — DEFER"
            decisions.append((pat, "DEFER"))
            print(line); continue
        if lg["n"] < 30 or sg["n"] < 30:
            line += (f"LG N={lg['n']} WR={lg['wr']:.1f}% vs "
                     f"SG N={sg['n']} WR={sg['wr']:.1f}%  "
                     f"— N<30 in one bucket → DEFER")
            decisions.append((pat, "DEFER"))
            print(line); continue
        if lg["wr"] > sg["wr"]:
            line += (f"LG N={lg['n']} WR={lg['wr']:.1f}% > "
                     f"SG N={sg['n']} WR={sg['wr']:.1f}%  "
                     f"→ DISABLE LONG_GAMMA gate")
            decisions.append((pat, "DISABLE"))
        else:
            line += (f"LG N={lg['n']} WR={lg['wr']:.1f}% <= "
                     f"SG N={sg['n']} WR={sg['wr']:.1f}%  "
                     f"→ KEEP gate enabled")
            decisions.append((pat, "KEEP"))
        print(line)

    print()
    # Aggregate across OB patterns specifically
    lg_ob = []
    sg_ob = []
    for pat in ("BULL_OB", "BEAR_OB"):
        lg_ob += buckets.get((pat, "LONG_GAMMA"), [])
        sg_ob += buckets.get((pat, "SHORT_GAMMA"), [])
    lg_s = summarize(lg_ob)
    sg_s = summarize(sg_ob)
    print("  Aggregate over OB cohort (BULL_OB + BEAR_OB):")
    if lg_s and sg_s:
        print(f"    LONG_GAMMA:  N={lg_s['n']:>4}  WR={lg_s['wr']:>5.1f}% "
              f"[{lg_s['wr_ci_lo']:>5.1f}-{lg_s['wr_ci_hi']:>5.1f}]  "
              f"Mean={lg_s['mean']:>+6.2f}%")
        print(f"    SHORT_GAMMA: N={sg_s['n']:>4}  WR={sg_s['wr']:>5.1f}% "
              f"[{sg_s['wr_ci_lo']:>5.1f}-{sg_s['wr_ci_hi']:>5.1f}]  "
              f"Mean={sg_s['mean']:>+6.2f}%")
        ok_n = (lg_s["n"] >= 30 and sg_s["n"] >= 30)
        if ok_n:
            if lg_s["wr"] > sg_s["wr"]:
                print(f"    ⇒ OB aggregate supports DISABLE LONG_GAMMA gate")
            else:
                print(f"    ⇒ OB aggregate supports KEEP gate enabled")
        else:
            print(f"    ⇒ N<30 in one bucket — OB aggregate DEFER")
    else:
        print(f"    Insufficient data on OB cohort.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
