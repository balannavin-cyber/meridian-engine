"""
experiment_50_fvg_on_ob_cluster_v2.py  --  Session 16 item 3

EXPERIMENT 50 v2 -- FVG-on-OB Cluster vs Standalone FVG (BIDIRECTIONAL)

Background
----------
Original Exp 50 (Session 15) ran a 3x3 sweep (lookback x proximity) on
hist_pattern_signals data, but the table contained 0 BEAR_FVG signals at
the time -- the BEAR side of the structure had no signals to classify.
Verdict was "FAIL with anomaly" with monotonic INVERSION of ICT's
prediction (cluster WR < standalone WR) on BULL-only data.

Session 15 patches landed: hist_pattern_signals.BEAR_FVG 0 -> 795. Exp 50
v2 re-runs the same hypothesis test on now-symmetric data:
  - 3 lookback x 3 proximity x 2 direction = 18 cells (vs 9 originally).
  - Bidirectional: BULL_FVG-on-BULL_OB AND BEAR_FVG-on-BEAR_OB tested.

Two methodology corrections vs the original
-------------------------------------------
1) OUTCOME METRIC: locally-computed T+30m forward return from
   hist_spot_bars_5m (Exp 41 v2 mechanics, era-aware Rule 20).
   The original used hist_pattern_signals.ret_30m sign as outcome. Exp 41
   v2 (Session 16 item 1) found that column agrees with locally-computed
   forward return on only 4.7% of rows (24/509 within 1bp), with 35.3%
   NULL fraction. Cluster-vs-standalone *delta* may still be meaningful
   under that noise (both buckets see the same noisy column), but a
   locally-computed metric is the authoritative answer.
   This script reports both, with cross-check agreement at the header.

2) DROP EV-RATIO GATE per Session 16 prompt. PASS criterion is now:
       WR_delta >= 5pp  AND  N_cluster >= 30
   (Original gate added EV_30m ratio >= 1.3x, which is mis-calibrated
    when both EVs are tiny negatives -- ratio of two near-zeros is
    arbitrary.)

ret_60m and ret_eod outputs dropped (TD-054 ret_60m uniformly 0;
TD-055 ret_eod column does not exist).

Cluster definition (unchanged from original)
--------------------------------------------
For each FVG signal at time T_fvg, find an OB signal at time T_ob:
  - same symbol
  - T_ob < T_fvg
  - T_fvg - T_ob <= LOOKBACK_MIN
  - same direction (BULL_FVG vs BULL_OB, or BEAR_FVG vs BEAR_OB)
  - structurally aligned: BULL OB below FVG, BEAR OB above FVG
  - |OB_mid - FVG_mid| / FVG_mid * 100 <= PROXIMITY_PCT
Price reference uses (zone_low + zone_high) / 2 (zone midpoint).

Outputs
-------
Stdout, paste-back friendly. Sweep table, headline cell detail,
robustness vote per direction, and a CSV cohort dump of the enriched
FVG signals for downstream Exp 50b velocity testing.

Author: Session 16, item 3.
"""

from __future__ import annotations

import os
import sys
import csv
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from statistics import mean

from dotenv import load_dotenv
from supabase import create_client


# --- Constants (unchanged from original) --------------------------------------
PAGE_SIZE = 1000
START_DATE = "2025-04-01"
END_DATE = "2026-04-30"
SYMBOLS = ["NIFTY", "SENSEX"]

SWEEP_LOOKBACK_MIN = [30, 60, 120]
SWEEP_PROXIMITY_PCT = [0.20, 0.50, 1.00]

HEADLINE_LOOKBACK_MIN = 60
HEADLINE_PROXIMITY_PCT = 0.50

# PASS gate per Session 16 prompt (EV-ratio dropped)
WR_DELTA_BAR_PP = 5.0
N_CLUSTER_FLOOR = 30


# --- Rule 20 era-aware helpers ------------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))
ERA_BOUNDARY = "2026-04-07"  # exclusive: < uses Rule 16; >= uses astimezone(IST)


def to_ist_naive(ts_aware, trade_date_str):
    """Convert a stored aware datetime to IST-naive, era-correct per Rule 20."""
    if trade_date_str < ERA_BOUNDARY:
        return ts_aware.replace(tzinfo=None)
    return ts_aware.astimezone(IST).replace(tzinfo=None)


def parse_ts(s):
    """ISO-8601 parser tolerant of trailing 'Z'."""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


# --- Supabase pagination ------------------------------------------------------
def fetch_all(qb, page=PAGE_SIZE, hard_cap=500_000):
    rows, start = [], 0
    while True:
        chunk = qb.range(start, start + page - 1).execute().data or []
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        start += page
        if start > hard_cap:
            return rows


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


# --- Signal price reference ---------------------------------------------------
def get_price_ref(row):
    """Zone midpoint as price reference. hist_pattern_signals always has
    zone_low / zone_high (per UNIQUE INDEX on the table)."""
    zl, zh = row.get("zone_low"), row.get("zone_high")
    if zl is None or zh is None:
        return None
    try:
        return (float(zl) + float(zh)) / 2.0
    except (TypeError, ValueError):
        return None


# --- Local T+30m forward return enrichment (Exp 41 v2 mechanics) -------------
def enrich_with_local_t30m(sb, fvg_rows, symbols, date_min, date_max):
    """For each FVG row, set r['computed_ret_30m_pct'] if computable.
    Mutates fvg_rows in place. Returns (n_enriched, n_skipped_nomatch,
    n_skipped_eos, n_skipped_gap)."""
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

    n_enriched = n_nomatch = n_eos = n_gap = 0
    for r in fvg_rows:
        sym = r.get("symbol")
        td = r.get("trade_date")
        bar_ts_str = r.get("bar_ts")
        if not (sym and td and bar_ts_str):
            n_nomatch += 1
            continue
        day_bars = bars_by_sym_date.get((sym, td), [])
        if not day_bars:
            n_nomatch += 1
            continue
        sig_ist = to_ist_naive(parse_ts(bar_ts_str), td)
        idx = None
        for i, (b_ist, _) in enumerate(day_bars):
            if b_ist == sig_ist:
                idx = i
                break
        if idx is None:
            n_nomatch += 1
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
        r["computed_ret_30m_pct"] = (exit_ - entry) / entry * 100.0
        n_enriched += 1
    return n_enriched, n_nomatch, n_eos, n_gap


# --- Signal fetch -------------------------------------------------------------
def fetch_signals(sb, pattern_types, start, end):
    """Fetch hist_pattern_signals for given pattern_types over date window.
    Uses bar_ts as the timestamp column (confirmed schema)."""
    rows = []
    offset = 0
    while True:
        r = (sb.table("hist_pattern_signals").select("*")
             .in_("pattern_type", pattern_types)
             .gte("bar_ts", f"{start}T00:00:00+00:00")
             .lte("bar_ts", f"{end}T23:59:59+00:00")
             .order("bar_ts")
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 200_000:
            break
    return rows


# --- Cluster classification (unchanged from original, parametrised) ----------
def classify_fvgs(fvg_rows, ob_by_sym, lookback_min, prox_pct):
    """Returns (cluster_rows, standalone_rows, skipped_no_price)."""
    cluster, standalone = [], []
    skipped = 0
    for fvg in fvg_rows:
        ptype = fvg.get("pattern_type") or ""
        fvg_dir = "BULL" if "BULL" in ptype else ("BEAR" if "BEAR" in ptype else None)
        if fvg_dir is None:
            continue
        fvg_ts = parse_ts(fvg.get("bar_ts"))
        if fvg_ts is None:
            continue
        fvg_ref = get_price_ref(fvg)
        if fvg_ref is None or fvg_ref == 0:
            skipped += 1
            continue
        sym = fvg.get("symbol")
        candidates = [o for o in ob_by_sym.get(sym, [])
                      if fvg_dir in (o.get("pattern_type") or "")]
        matched = False
        for ob in candidates:
            ob_ts = parse_ts(ob.get("bar_ts"))
            if ob_ts is None or ob_ts >= fvg_ts:
                continue
            delta_min = (fvg_ts - ob_ts).total_seconds() / 60.0
            if delta_min < 0 or delta_min > lookback_min:
                continue
            ob_ref = get_price_ref(ob)
            if ob_ref is None or ob_ref == 0:
                continue
            # Structural ordering
            if fvg_dir == "BULL" and ob_ref > fvg_ref:
                continue
            if fvg_dir == "BEAR" and ob_ref < fvg_ref:
                continue
            # Proximity
            if abs(ob_ref - fvg_ref) / fvg_ref * 100.0 > prox_pct:
                continue
            matched = True
            break
        (cluster if matched else standalone).append(fvg)
    return cluster, standalone, skipped


# --- Metrics (locally-computed return) ---------------------------------------
def compute_metrics(rows, direction):
    """Per-bucket metrics. direction in ('BULL','BEAR'). Win = local
    forward return aligned with direction."""
    n_total = len(rows)
    if n_total == 0:
        return {"n": 0, "n_with_outcome": 0, "wr": 0.0, "ev30": 0.0}
    intent = +1 if direction == "BULL" else -1
    wins = 0
    ev_sum = 0.0
    n_with = 0
    for r in rows:
        rp = r.get("computed_ret_30m_pct")
        if rp is None:
            continue
        n_with += 1
        signed = rp * intent
        if signed > 0:
            wins += 1
        ev_sum += signed
    if n_with == 0:
        return {"n": n_total, "n_with_outcome": 0, "wr": 0.0, "ev30": 0.0}
    return {
        "n": n_total,
        "n_with_outcome": n_with,
        "wr": wins / n_with * 100.0,
        "ev30": ev_sum / n_with,
    }


def compute_table_column_agreement(fvg_rows):
    """Cross-check: how many FVG rows have table ret_30m within 1bp of
    locally-computed ret_30m? Mirrors Exp 41 v2 cross-check."""
    cc = []
    for r in fvg_rows:
        comp = r.get("computed_ret_30m_pct")
        tab = r.get("ret_30m")
        if comp is None or tab is None:
            continue
        try:
            cc.append((comp, float(tab)))
        except (TypeError, ValueError):
            continue
    if not cc:
        return None
    agree = sum(1 for c, t in cc if abs(c - t) < 0.01)
    return {
        "n_compared": len(cc),
        "n_agree": agree,
        "agree_pct": agree / len(cc) * 100.0,
        "n_total": len(fvg_rows),
        "n_table_null": sum(1 for r in fvg_rows if r.get("ret_30m") is None),
    }


# --- Main ---------------------------------------------------------------------
def main():
    sb = get_client()
    print("=" * 96)
    print("EXPERIMENT 50 v2  --  FVG-on-OB Cluster vs Standalone FVG (BIDIRECTIONAL)")
    print(f"Run at: {datetime.now(IST).isoformat(timespec='seconds')}")
    print("=" * 96)
    print(f"Window         : {START_DATE} .. {END_DATE}")
    print(f"Sweep          : lookback={SWEEP_LOOKBACK_MIN} min, proximity={SWEEP_PROXIMITY_PCT}%")
    print(f"Headline cell  : lookback={HEADLINE_LOOKBACK_MIN}min, proximity={HEADLINE_PROXIMITY_PCT}%")
    print(f"PASS gate (v2) : WR_delta >= {WR_DELTA_BAR_PP}pp AND N_cluster >= {N_CLUSTER_FLOOR}")
    print(f"Outcome metric : locally-computed T+30m return from hist_spot_bars_5m (Rule 20)")
    print()

    # Fetch FVG + OB signals
    print("[INFO] fetching FVG signals ...")
    fvg_rows = fetch_signals(sb, ["BULL_FVG", "BEAR_FVG"], START_DATE, END_DATE)
    print(f"[INFO] fetched {len(fvg_rows)} FVG signals")
    fvg_dist = Counter(r.get("pattern_type") for r in fvg_rows)
    print(f"[INFO] FVG distribution: {dict(fvg_dist)}")

    print("[INFO] fetching OB signals ...")
    ob_rows = fetch_signals(sb, ["BULL_OB", "BEAR_OB"], START_DATE, END_DATE)
    print(f"[INFO] fetched {len(ob_rows)} OB signals")
    ob_dist = Counter(r.get("pattern_type") for r in ob_rows)
    print(f"[INFO] OB distribution: {dict(ob_dist)}")
    print()

    if not fvg_rows or not ob_rows:
        sys.exit("[FATAL] insufficient signals.")

    # Enrich FVG rows with locally-computed T+30m return
    n_e, n_nm, n_eos, n_gap = enrich_with_local_t30m(
        sb, fvg_rows, SYMBOLS, START_DATE, END_DATE
    )
    print(f"[INFO] FVG enrichment: {n_e} enriched, {n_nm} no-match, "
          f"{n_eos} eos-skipped, {n_gap} bar-gap-skipped")
    print()

    # Cross-check ret_30m column agreement (column-integrity finding)
    cc = compute_table_column_agreement(fvg_rows)
    if cc:
        print(f"[CROSS-CHECK] table.ret_30m vs computed_ret_30m_pct:")
        print(f"             {cc['n_agree']}/{cc['n_compared']} "
              f"({cc['agree_pct']:.1f}%) within 1bp; "
              f"{cc['n_table_null']}/{cc['n_total']} table rows have NULL ret_30m")
    print()

    # Index OB by symbol
    ob_by_sym = defaultdict(list)
    for r in ob_rows:
        ob_by_sym[r["symbol"]].append(r)
    for sym in ob_by_sym:
        ob_by_sym[sym].sort(key=lambda x: x.get("bar_ts") or "")

    # ============ FULL SWEEP ============
    print("=" * 96)
    print("RESULTS  --  full sweep")
    print("=" * 96)
    print(f"{'Lookback':>9} {'Prox%':>7} {'Dir':<5} {'Bucket':<11} "
          f"{'N':>6} {'Nout':>6} {'WR':>7} {'EV_30m':>9}")
    print("-" * 96)

    cells = {}  # (lookback, prox) -> {direction -> {bucket -> metrics}}
    for lookback_min in SWEEP_LOOKBACK_MIN:
        for prox_pct in SWEEP_PROXIMITY_PCT:
            cluster, standalone, _ = classify_fvgs(
                fvg_rows, ob_by_sym, lookback_min, prox_pct
            )
            cell = {}
            for direction in ("BULL", "BEAR"):
                cell[direction] = {}
                for bucket_name, rows in (
                    ("standalone", [r for r in standalone
                                    if direction in (r.get("pattern_type") or "")]),
                    ("cluster",    [r for r in cluster
                                    if direction in (r.get("pattern_type") or "")]),
                ):
                    m = compute_metrics(rows, direction)
                    cell[direction][bucket_name] = m
                    if m["n"] == 0:
                        continue
                    print(f"{lookback_min:>9} {prox_pct:>6.2f}% {direction:<5} "
                          f"{bucket_name:<11} {m['n']:>6} {m['n_with_outcome']:>6} "
                          f"{m['wr']:>6.1f}% {m['ev30']:>+8.3f}%")
            cells[(lookback_min, prox_pct)] = cell
            print()

    # ============ HEADLINE ============
    print("=" * 96)
    print(f"HEADLINE  --  lookback={HEADLINE_LOOKBACK_MIN}min, "
          f"proximity={HEADLINE_PROXIMITY_PCT}%")
    print("=" * 96)
    headline = cells.get((HEADLINE_LOOKBACK_MIN, HEADLINE_PROXIMITY_PCT))
    if headline is None:
        print("[WARN] headline cell not in sweep grid")
    else:
        for direction in ("BULL", "BEAR"):
            sa = headline[direction]["standalone"]
            cl = headline[direction]["cluster"]
            if sa["n_with_outcome"] == 0 or cl["n_with_outcome"] == 0:
                print(f"  {direction}: insufficient data "
                      f"(standalone N_out={sa['n_with_outcome']}, "
                      f"cluster N_out={cl['n_with_outcome']})")
                continue
            wr_diff = cl["wr"] - sa["wr"]
            ev_diff = cl["ev30"] - sa["ev30"]
            print(f"  {direction}:")
            print(f"    Standalone : N={sa['n']:>5} N_out={sa['n_with_outcome']:>5} "
                  f"WR={sa['wr']:>5.1f}%  EV_30m={sa['ev30']:>+6.3f}%")
            print(f"    Cluster    : N={cl['n']:>5} N_out={cl['n_with_outcome']:>5} "
                  f"WR={cl['wr']:>5.1f}%  EV_30m={cl['ev30']:>+6.3f}%")
            print(f"    Delta      : WR {wr_diff:>+5.1f}pp,  EV_30m "
                  f"{ev_diff:>+6.3f}pp")
            wr_ok = wr_diff >= WR_DELTA_BAR_PP
            n_ok = cl["n_with_outcome"] >= N_CLUSTER_FLOOR
            verdict = "PASS" if (wr_ok and n_ok) else "FAIL"
            print(f"    Verdict    : {verdict}  "
                  f"(WR {'PASS' if wr_ok else 'FAIL'} "
                  f"{wr_diff:+.1f}pp vs +{WR_DELTA_BAR_PP}pp; "
                  f"N {'PASS' if n_ok else 'FAIL'} "
                  f"{cl['n_with_outcome']} vs {N_CLUSTER_FLOOR})")
            print()

    # ============ ROBUSTNESS ============
    print("=" * 96)
    print("ROBUSTNESS  --  cell-by-cell verdict (PASS = WR_delta >= 5pp AND N_cluster >= 30)")
    print("=" * 96)
    print(f"{'Lookback':>9} {'Prox%':>7} {'Dir':<5} {'WR_sa':>7} {'WR_cl':>7} "
          f"{'WR_delta':>9} {'N_cl':>6} {'verdict':<10}")
    print("-" * 96)
    pass_count = {"BULL": 0, "BEAR": 0}
    eval_count = {"BULL": 0, "BEAR": 0}
    for (lb, px), cell in sorted(cells.items()):
        for direction in ("BULL", "BEAR"):
            sa = cell[direction]["standalone"]
            cl = cell[direction]["cluster"]
            if sa["n_with_outcome"] == 0 or cl["n_with_outcome"] == 0:
                continue
            eval_count[direction] += 1
            wr_diff = cl["wr"] - sa["wr"]
            wr_ok = wr_diff >= WR_DELTA_BAR_PP
            n_ok = cl["n_with_outcome"] >= N_CLUSTER_FLOOR
            cell_pass = wr_ok and n_ok
            if cell_pass:
                pass_count[direction] += 1
            print(f"{lb:>9} {px:>6.2f}% {direction:<5} "
                  f"{sa['wr']:>6.1f}% {cl['wr']:>6.1f}% "
                  f"{wr_diff:>+8.1f}pp {cl['n_with_outcome']:>6} "
                  f"{('PASS' if cell_pass else 'FAIL'):<10}")
    print()
    print("=" * 96)
    print("VERDICT")
    print("=" * 96)
    for direction in ("BULL", "BEAR"):
        n_eval = eval_count[direction]
        n_pass = pass_count[direction]
        if n_eval == 0:
            print(f"  {direction}: no evaluable cells")
            continue
        print(f"  {direction}: {n_pass}/{n_eval} cells PASS "
              f"(WR_delta >= {WR_DELTA_BAR_PP}pp AND N_cluster >= {N_CLUSTER_FLOOR})")
    print()
    print("Interpretation:")
    print(f"  Most cells PASS for a direction      -> cluster effect robust on that side.")
    print(f"  Only headline cell PASSes            -> threshold-fragile, treat as hint.")
    print(f"  Cells FAIL across grid               -> ICT PD Array hypothesis not")
    print(f"                                          replicated; standalone vs cluster")
    print(f"                                          not predictive in MERDIAN data.")
    print(f"  BULL passes / BEAR fails (or vice)   -> directional asymmetry; market regime")
    print(f"                                          or filter-side artefact.")
    print()

    # ============ CSV cohort dump (for Exp 50b reuse) ============
    stamp = datetime.now(IST).strftime("%Y%m%d_%H%M")
    csv_path = f"exp50_v2_fvg_cohort_{stamp}.csv"
    fields = ["id", "symbol", "trade_date", "bar_ts", "pattern_type", "direction",
              "zone_low", "zone_high", "ret_30m", "computed_ret_30m_pct", "win_30m"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in fvg_rows:
            w.writerow(r)
    print(f"Cohort CSV: {csv_path}  ({len(fvg_rows)} FVG rows, "
          f"{n_e} enriched with local T+30m)")


if __name__ == "__main__":
    main()
