"""
check_a_exp15_gated_replication_v1.py  --  Session 16 item 8 (Check A)

CHECK A  --  Does Exp 15/20's gated-subset edge replicate on
locally-computed spot-side T+30m WR?

Why this script exists
----------------------
TD-056 + Exp 15/16 stress test (item 6) showed that on UNGATED, CONTEXT-BLIND
data, BULL_OB / BEAR_OB / BULL_FVG / BEAR_FVG are coin flips at T+30m
(48-51% pooled WR, EV ~0). This was used by some readings to claim Exp 15-16
"collapse." That claim was overreach: Exp 15-16 measured a GATED, MTF-CONTEXT-
AWARE subset using OPTION-PNL, not the ungated universe with spot-side return.

The two test cohorts are not comparable. Operator (correctly) demanded we
test the gated subset directly before drawing conclusions.

This script does that. It reconstructs the two filters Exp 15/20 used:
  (1) ENH-44 alignment (per merdian_reference.json L2502)
       BUY_CE + ret_session > +0.05% = ALIGNED
       BUY_PE + ret_session < -0.05% = ALIGNED
  (2) MTF context (HIGH/MEDIUM/LOW) reconstructed by joining to
       hist_ict_htf_zones at trade_date

Then computes spot-side T+30m WR (Exp 41 mechanics, locally-computed) for
each cell of (pattern x alignment x mtf_context). Compares against published
Exp 15/10c/20 numbers.

Replication targets (published, against which today's run is judged)
--------------------------------------------------------------------
Exp 20 (MOM_YES pooled):
  ALIGNED   = 60.9% WR  (N=2138)
  OPPOSED   = 38.3% WR  (N=2275)
  NEUTRAL   = 47.6% WR  (N=311)

Exp 10c (BULL_OB by MTF):
  BULL_OB | MEDIUM = 90% WR (N=45)
  BULL_OB | HIGH   = 100% WR (N=18)
  BULL_OB | LOW    = 88% WR (N=38)

Exp 15 (BULL_OB by MTF context, smaller cohort):
  BULL_OB | MEDIUM = 77.3% WR (N=22)
  BULL_OB | HIGH   = 46.7% WR (N=15)
  BULL_OB | LOW    = 64.3% WR (N=196 across all patterns)

Decision logic
--------------
For each replication target:
  WITHIN 5pp of published   -> SURVIVES
  5-15pp deflation          -> DEFLATED (signal real, magnitude lower)
  >15pp deflation OR < 55%  -> COLLAPSES (signal not in cleaner data)

Three possible outcomes:
  A) ALIGNED + MTF both replicate. Framework intact, magnitudes maybe lower.
     Item 6's ungated-coin-flip finding is fully consistent: framework's edge
     comes from gating, not raw direction. Continue building.
  B) Alignment replicates, MTF doesn't (or vice versa).
     One filter works, other was illusion. Architecture decision needed.
  C) Neither replicates.
     Production system rests on inflated numbers across the board.
     Stop building until methodology is rebuilt.

Window: full available range. Rule 20 era-aware throughout.

Author: Session 16, item 8 (Check A).
"""

from __future__ import annotations

import os
import sys
import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean

from dotenv import load_dotenv
from supabase import create_client


# --- Constants ---------------------------------------------------------------
PAGE_SIZE = 1000
SYMBOLS = ["NIFTY", "SENSEX"]
PATTERNS = ["BULL_OB", "BEAR_OB", "BULL_FVG", "BEAR_FVG"]

# ENH-44 alignment threshold (per merdian_reference.json L2502)
RET_SESSION_FLAT_PCT = 0.05  # |ret_session| <= 0.05% -> NEUTRAL


# --- Rule 20 era-aware helpers ----------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))
ERA_BOUNDARY = "2026-04-07"


def to_ist_naive(ts_aware, trade_date_str):
    if trade_date_str < ERA_BOUNDARY:
        return ts_aware.replace(tzinfo=None)
    return ts_aware.astimezone(IST).replace(tzinfo=None)


def parse_ts(s):
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    if isinstance(s, str):
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def parse_date(s):
    if s is None:
        return None
    if isinstance(s, str) and len(s) >= 10:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        sys.exit("Missing SUPABASE_URL or SUPABASE_*_KEY in .env")
    return create_client(url, key)


def fetch_all(qb, page=PAGE_SIZE, hard_cap=200_000):
    rows, start = [], 0
    while True:
        chunk = qb.range(start, start + page - 1).execute().data or []
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        start += page
        if start > hard_cap:
            return rows


# --- Signal + bar fetch -----------------------------------------------------
def fetch_signals(sb, pattern_types):
    rows = fetch_all(
        sb.table("hist_pattern_signals").select("*")
          .in_("pattern_type", pattern_types)
          .order("bar_ts")
    )
    return rows


def enrich_with_local_t30m(sb, sigs, symbols, date_min, date_max):
    """Mutates sigs: sets 'computed_ret_30m_pct' and 'entry_price'."""
    print(f"[INFO] loading 5m bars per symbol for forward-return enrichment ...")
    bars_by_sym_date = {}
    for sym in symbols:
        bars = fetch_all(
            sb.table("hist_spot_bars_5m")
              .select("bar_ts, close, trade_date")
              .eq("symbol", sym)
              .gte("trade_date", date_min)
              .lte("trade_date", date_max)
              .order("bar_ts")
        )
        for b in bars:
            ts_aware = parse_ts(b["bar_ts"])
            ist = to_ist_naive(ts_aware, b["trade_date"])
            bars_by_sym_date.setdefault((sym, b["trade_date"]), []).append(
                (ist, float(b["close"]))
            )
        n_bars = sum(len(v) for k, v in bars_by_sym_date.items() if k[0] == sym)
        n_days = sum(1 for k in bars_by_sym_date if k[0] == sym)
        print(f"[INFO]   {sym}: {n_bars} bars across {n_days} days")

    n_e = n_nm = n_eos = n_gap = 0
    for r in sigs:
        sym = r.get("symbol")
        td = r.get("trade_date")
        bar_ts_str = r.get("bar_ts")
        if not (sym and td and bar_ts_str):
            n_nm += 1
            continue
        day_bars = bars_by_sym_date.get((sym, td), [])
        if not day_bars:
            n_nm += 1
            continue
        sig_ist = to_ist_naive(parse_ts(bar_ts_str), td)
        idx = None
        for i, (b_ist, _) in enumerate(day_bars):
            if b_ist == sig_ist:
                idx = i
                break
        if idx is None:
            n_nm += 1
            continue
        t30 = idx + 6
        if t30 >= len(day_bars):
            n_eos += 1
            continue
        if day_bars[t30][0] != sig_ist + timedelta(minutes=30):
            n_gap += 1
            continue
        entry = day_bars[idx][1]
        exit_ = day_bars[t30][1]
        r["entry_price"] = entry
        r["computed_ret_30m_pct"] = (exit_ - entry) / entry * 100.0
        n_e += 1
    return n_e, n_nm, n_eos, n_gap


# --- Zone fetch + MTF computation -------------------------------------------
def fetch_all_active_zones(sb, symbol):
    return fetch_all(
        sb.table("hist_ict_htf_zones").select("*")
          .eq("symbol", symbol)
          .eq("status", "ACTIVE")
          .order("valid_from")
    )


def index_zones_for_mtf(zones):
    """Returns dict: (symbol, direction, timeframe) -> sorted list of (vf_date, zone_dict).
    Sorted ascending by valid_from for binary-search-like access."""
    idx = defaultdict(list)
    for z in zones:
        sym = z.get("symbol")
        try:
            d = int(z.get("direction") or 0)
        except (TypeError, ValueError):
            continue
        tf = (z.get("timeframe") or "").upper()
        if not sym or d == 0 or not tf:
            continue
        vf = parse_date(z.get("valid_from"))
        if vf is None:
            continue
        idx[(sym, d, tf)].append((vf, z))
    for k in idx:
        idx[k].sort(key=lambda x: x[0])
    return idx


def compute_mtf_context(signal, zone_idx):
    """Returns 'VERY_HIGH' (W) | 'HIGH' (D) | 'MEDIUM' (H) | 'LOW' (none).
    Strategy: for each TF in priority order, find most recent ACTIVE zone of
    same direction and check containment."""
    sym = signal.get("symbol")
    sig_dir = signal.get("direction")
    if sig_dir == "BUY_CE":
        zone_dir = +1
    elif sig_dir == "BUY_PE":
        zone_dir = -1
    else:
        return "LOW"
    entry = signal.get("entry_price")
    td = parse_date(signal.get("trade_date"))
    if entry is None or td is None:
        return "LOW"

    for tf, label in (("W", "VERY_HIGH"), ("D", "HIGH"), ("H", "MEDIUM")):
        zlist = zone_idx.get((sym, zone_dir, tf), [])
        # Find most recent valid_from <= td via simple linear scan from end
        # (zlist is small per (sym, dir, TF); typically <100 entries)
        best = None
        for vf, z in reversed(zlist):
            if vf <= td:
                best = z
                break
        if best is None:
            continue
        try:
            zlow = float(best.get("zone_low") or 0)
            zhigh = float(best.get("zone_high") or 0)
        except (TypeError, ValueError):
            continue
        if zlow == 0 and zhigh == 0:
            continue
        if zlow <= entry <= zhigh:
            return label
    return "LOW"


# --- Alignment computation --------------------------------------------------
def compute_alignment(signal):
    """Per ENH-44 (merdian_reference.json L2502)."""
    sig_dir = signal.get("direction")
    rs = signal.get("ret_session")
    if rs is None:
        return None
    try:
        rs = float(rs)
    except (TypeError, ValueError):
        return None
    if abs(rs) <= RET_SESSION_FLAT_PCT:
        return "NEUTRAL"
    if sig_dir == "BUY_CE":
        return "ALIGNED" if rs > RET_SESSION_FLAT_PCT else "OPPOSED"
    if sig_dir == "BUY_PE":
        return "ALIGNED" if rs < -RET_SESSION_FLAT_PCT else "OPPOSED"
    return None


# --- WR computation ---------------------------------------------------------
def wr_of(rows):
    """Win = computed_ret_30m_pct * direction_intent > 0."""
    n = wins = 0
    for r in rows:
        rp = r.get("computed_ret_30m_pct")
        if rp is None:
            continue
        sig_dir = r.get("direction")
        intent = +1 if sig_dir == "BUY_CE" else -1 if sig_dir == "BUY_PE" else 0
        if intent == 0:
            continue
        n += 1
        if rp * intent > 0:
            wins += 1
    if n == 0:
        return 0, 0.0
    return n, wins / n * 100.0


def ev_of(rows):
    """Mean ret aligned with direction intent."""
    rets = []
    for r in rows:
        rp = r.get("computed_ret_30m_pct")
        if rp is None:
            continue
        sig_dir = r.get("direction")
        intent = +1 if sig_dir == "BUY_CE" else -1 if sig_dir == "BUY_PE" else 0
        if intent == 0:
            continue
        rets.append(rp * intent)
    return mean(rets) if rets else 0.0


# --- Verdict labels ---------------------------------------------------------
def verdict_label(observed_wr, target_wr):
    delta = observed_wr - target_wr
    if abs(delta) <= 5:
        return f"SURVIVES ({delta:+.1f}pp)"
    if observed_wr >= 55 and delta >= -15:
        return f"DEFLATED ({delta:+.1f}pp)"
    return f"COLLAPSES ({delta:+.1f}pp)"


# --- Main -------------------------------------------------------------------
def main():
    sb = get_client()

    print("=" * 96)
    print("CHECK A  --  Exp 15/20 gated-subset replication on locally-computed T+30m")
    print(f"Run at: {datetime.now(IST).isoformat(timespec='seconds')}")
    print("=" * 96)
    print(f"Patterns        : {PATTERNS}")
    print(f"Alignment rule  : ENH-44 (merdian_reference.json L2502)")
    print(f"  ALIGNED   : BUY_CE + ret_session > +{RET_SESSION_FLAT_PCT}%  OR")
    print(f"              BUY_PE + ret_session < -{RET_SESSION_FLAT_PCT}%")
    print(f"  OPPOSED   : opposite of above")
    print(f"  NEUTRAL   : |ret_session| <= {RET_SESSION_FLAT_PCT}%")
    print(f"MTF context     : zone containment join to hist_ict_htf_zones")
    print(f"  VERY_HIGH : entry_price inside same-direction W zone")
    print(f"  HIGH      : same with D zone (no W match)")
    print(f"  MEDIUM    : same with H zone (no D or W match)")
    print(f"  LOW       : none of the above")
    print(f"Outcome metric  : locally-computed T+30m return (Rule 20)")
    print()

    # Fetch signals
    print(f"[INFO] fetching signals ...")
    sigs = fetch_signals(sb, PATTERNS)
    print(f"[INFO] fetched {len(sigs)} signal rows")
    by_p = defaultdict(int)
    for s in sigs:
        by_p[s.get("pattern_type")] += 1
    for p in PATTERNS:
        print(f"[INFO]   {p}: {by_p[p]}")
    sigs = [s for s in sigs if s.get("symbol") in SYMBOLS]
    print(f"[INFO] after symbol filter: {len(sigs)}")
    print()

    # Date range
    dates = sorted({s["trade_date"] for s in sigs if s.get("trade_date")})
    if not dates:
        sys.exit("[FATAL] no trade_date on signals")
    date_min, date_max = dates[0], dates[-1]
    print(f"[INFO] date range: {date_min} -> {date_max}")
    print()

    # Enrich with locally-computed forward return + entry_price
    n_e, n_nm, n_eos, n_gap = enrich_with_local_t30m(
        sb, sigs, SYMBOLS, date_min, date_max
    )
    print(f"[INFO] enrichment: {n_e} enriched, {n_nm} no-match, "
          f"{n_eos} eos-skipped, {n_gap} bar-gap-skipped")
    print()

    # Fetch zones + index
    all_zones = []
    for sym in SYMBOLS:
        zs = fetch_all_active_zones(sb, sym)
        print(f"[INFO] {sym}: {len(zs)} ACTIVE zones from hist_ict_htf_zones")
        all_zones.extend(zs)
    zone_idx = index_zones_for_mtf(all_zones)
    print(f"[INFO] zone index keyed by (symbol, direction, timeframe): "
          f"{len(zone_idx)} groups")
    print()

    # Compute alignment + mtf_context per signal
    n_no_align = 0
    n_no_entry = 0
    for s in sigs:
        s["_alignment"] = compute_alignment(s)
        if s["_alignment"] is None:
            n_no_align += 1
        if s.get("entry_price") is None:
            n_no_entry += 1
            s["_mtf"] = "LOW"
        else:
            s["_mtf"] = compute_mtf_context(s, zone_idx)
    print(f"[INFO] {n_no_align} signals lack alignment (NULL ret_session)")
    print(f"[INFO] {n_no_entry} signals lack entry_price (no bar match) -> MTF=LOW")
    print()

    # Filter to enriched + alignment-classified rows for the analysis
    valid = [s for s in sigs
             if s.get("computed_ret_30m_pct") is not None
             and s["_alignment"] is not None]
    print(f"[INFO] valid cohort for analysis: {len(valid)} signals")
    print()

    # ============================================================
    # TABLE 1 -- Pattern x Alignment (replicates Exp 20)
    # ============================================================
    print("=" * 96)
    print("TABLE 1: Pattern x Alignment WR  (replicates Exp 20 MOM_YES)")
    print("=" * 96)
    print(f"{'Pattern':<10} {'Alignment':<10} {'N':>5} {'WR':>7} {'EV':>9}")
    print("-" * 96)
    for pat in PATTERNS:
        for align in ("ALIGNED", "NEUTRAL", "OPPOSED"):
            rows = [s for s in valid
                    if s.get("pattern_type") == pat and s["_alignment"] == align]
            n, wr = wr_of(rows)
            ev = ev_of(rows)
            print(f"{pat:<10} {align:<10} {n:>5} {wr:>6.1f}% {ev:>+8.3f}%")
        print()

    # Pooled across all patterns
    print("POOLED ACROSS ALL PATTERNS:")
    print(f"{'Alignment':<10} {'N':>5} {'WR':>7} {'EV':>9}  Exp 20 target  Verdict")
    print("-" * 96)
    exp20_targets = {"ALIGNED": 60.9, "OPPOSED": 38.3, "NEUTRAL": 47.6}
    for align in ("ALIGNED", "NEUTRAL", "OPPOSED"):
        rows = [s for s in valid if s["_alignment"] == align]
        n, wr = wr_of(rows)
        ev = ev_of(rows)
        target = exp20_targets[align]
        v = verdict_label(wr, target)
        print(f"{align:<10} {n:>5} {wr:>6.1f}% {ev:>+8.3f}%       "
              f"{target:>5.1f}%      {v}")
    print()

    # ============================================================
    # TABLE 2 -- Pattern x MTF Context (replicates Exp 10c / Exp 15)
    # ============================================================
    print("=" * 96)
    print("TABLE 2: Pattern x MTF Context WR  (replicates Exp 10c / Exp 15)")
    print("=" * 96)
    print(f"{'Pattern':<10} {'Context':<11} {'N':>5} {'WR':>7} {'EV':>9}")
    print("-" * 96)
    for pat in PATTERNS:
        for ctx in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW"):
            rows = [s for s in valid
                    if s.get("pattern_type") == pat and s["_mtf"] == ctx]
            n, wr = wr_of(rows)
            ev = ev_of(rows)
            print(f"{pat:<10} {ctx:<11} {n:>5} {wr:>6.1f}% {ev:>+8.3f}%")
        print()

    # Headline cells vs Exp 10c/15 targets
    print("HEADLINE CELLS vs Exp 10c / Exp 15 published numbers:")
    print(f"{'Cell':<28} {'N':>5} {'WR':>7}  {'Exp target':<16} {'Verdict':<24}")
    print("-" * 96)
    headline_targets = [
        ("BULL_OB | MEDIUM",   "BULL_OB",  "MEDIUM",    90.0, "Exp 10c (N=45)"),
        ("BULL_OB | HIGH",     "BULL_OB",  "HIGH",     100.0, "Exp 10c (N=18)"),
        ("BULL_OB | LOW",      "BULL_OB",  "LOW",       88.0, "Exp 10c (N=38)"),
        ("BULL_OB | MEDIUM v2","BULL_OB",  "MEDIUM",    77.3, "Exp 15 (N=22)"),
    ]
    for label, pat, ctx, target, source in headline_targets:
        rows = [s for s in valid
                if s.get("pattern_type") == pat and s["_mtf"] == ctx]
        n, wr = wr_of(rows)
        if n == 0:
            v = "(no data)"
        else:
            v = verdict_label(wr, target)
        print(f"{label:<28} {n:>5} {wr:>6.1f}%  {target:>5.1f}% {source:<10}  {v}")
    print()

    # ============================================================
    # TABLE 3 -- ALIGNED + MEDIUM (the fully gated subset)
    # ============================================================
    print("=" * 96)
    print("TABLE 3: ALIGNED + MTF combined gating (the Exp 15-style gated subset)")
    print("=" * 96)
    print(f"{'Pattern':<10} {'Context':<11} {'N':>5} {'WR':>7} {'EV':>9}  "
          f"(ALIGNED only)")
    print("-" * 96)
    for pat in PATTERNS:
        for ctx in ("VERY_HIGH", "HIGH", "MEDIUM", "LOW"):
            rows = [s for s in valid
                    if s.get("pattern_type") == pat
                    and s["_mtf"] == ctx
                    and s["_alignment"] == "ALIGNED"]
            n, wr = wr_of(rows)
            ev = ev_of(rows)
            print(f"{pat:<10} {ctx:<11} {n:>5} {wr:>6.1f}% {ev:>+8.3f}%")
        print()

    # ============================================================
    # OVERALL VERDICT
    # ============================================================
    print("=" * 96)
    print("OVERALL VERDICT")
    print("=" * 96)
    # Aligned pooled
    aligned_pooled = [s for s in valid if s["_alignment"] == "ALIGNED"]
    n_a, wr_a = wr_of(aligned_pooled)
    opposed_pooled = [s for s in valid if s["_alignment"] == "OPPOSED"]
    n_o, wr_o = wr_of(opposed_pooled)
    align_lift = wr_a - wr_o
    align_target_lift = 60.9 - 38.3  # = 22.6pp per Exp 20
    print(f"\nALIGNMENT FILTER:")
    print(f"  ALIGNED pooled  : N={n_a}, WR={wr_a:.1f}%  (Exp 20 target 60.9%)")
    print(f"  OPPOSED pooled  : N={n_o}, WR={wr_o:.1f}%  (Exp 20 target 38.3%)")
    print(f"  Lift            : {align_lift:+.1f}pp  (Exp 20 target +22.6pp)")
    align_replicates = align_lift >= 15  # generous: 2/3 of published lift
    print(f"  Replicates?     : {'YES' if align_replicates else 'NO'} "
          f"(threshold: lift >= 15pp)")

    # MTF MEDIUM cells
    print(f"\nMTF CONTEXT FILTER:")
    bull_ob_med = [s for s in valid
                   if s.get("pattern_type") == "BULL_OB" and s["_mtf"] == "MEDIUM"]
    n_bm, wr_bm = wr_of(bull_ob_med)
    bull_ob_low = [s for s in valid
                   if s.get("pattern_type") == "BULL_OB" and s["_mtf"] == "LOW"]
    n_bl, wr_bl = wr_of(bull_ob_low)
    mtf_lift = wr_bm - wr_bl if n_bm > 0 and n_bl > 0 else 0
    print(f"  BULL_OB|MEDIUM  : N={n_bm}, WR={wr_bm:.1f}%  "
          f"(Exp 10c 90%, Exp 15 77.3%)")
    print(f"  BULL_OB|LOW     : N={n_bl}, WR={wr_bl:.1f}%  (Exp 10c 88%)")
    print(f"  MEDIUM lift     : {mtf_lift:+.1f}pp")
    mtf_replicates = wr_bm >= 65 and n_bm >= 20  # lower bar: >=65% on N>=20
    print(f"  Replicates?     : {'YES' if mtf_replicates else 'NO'} "
          f"(threshold: BULL_OB|MEDIUM WR>=65% on N>=20)")

    # Combined verdict
    print(f"\nCOMBINED VERDICT:")
    if align_replicates and mtf_replicates:
        verdict = ("OUTCOME A -- BOTH FILTERS REPLICATE. Framework intact. "
                   "Magnitudes may be lower than published but the gating "
                   "rules deliver edge. Continue building.")
    elif align_replicates and not mtf_replicates:
        verdict = ("OUTCOME B-1 -- ALIGNMENT REPLICATES, MTF DOES NOT. "
                   "ENH-44 momentum gate is real; ENH-37 MTF context is "
                   "suspect. Architecture decision needed: keep ENH-44, "
                   "review ENH-37/MTF claims.")
    elif not align_replicates and mtf_replicates:
        verdict = ("OUTCOME B-2 -- MTF REPLICATES, ALIGNMENT DOES NOT. "
                   "Unexpected; alignment was the strongest single filter "
                   "per Exp 20. Investigate before drawing conclusions.")
    else:
        verdict = ("OUTCOME C -- NEITHER FILTER REPLICATES. Production system "
                   "rests on inflated numbers across the board. STOP building. "
                   "Methodology audit of options_pnl table required before "
                   "any further confidence in published results.")
    print(verdict)
    print()

    # CSV dump
    stamp = datetime.now(IST).strftime("%Y%m%d_%H%M")
    csv_path = f"check_a_exp15_replication_{stamp}.csv"
    fields = ["id", "symbol", "trade_date", "bar_ts", "pattern_type",
              "direction", "ret_session", "_alignment", "_mtf", "entry_price",
              "computed_ret_30m_pct"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in valid:
            w.writerow(r)
    print(f"Cohort CSV: {csv_path}  ({len(valid)} rows)")
    print()
    print("=" * 96)
    print("CHECK A  --  end")
    print("=" * 96)


if __name__ == "__main__":
    main()
