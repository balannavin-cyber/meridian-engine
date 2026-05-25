"""
experiment_50b_fvg_on_ob_velocity_v2.py  --  Session 16 item 4

EXPERIMENT 50b v2 -- Pre-FVG velocity vs cluster-FVG WR (BIDIRECTIONAL, REFRAMED)

Background
----------
Original Exp 50b (Session 15) tested whether the BULL-only Exp 50 inversion
(cluster WR < standalone WR) was driven by exhaustion: tight (OB,FVG)
coupling implies fast pre-FVG velocity, FVG forms over-extended, fails
more often. Verdict was MARGINAL on BULL-only data with `ret_30m` column
as outcome.

Two findings reframe the experiment for Session 16:

1) Exp 50 v2 (Session 16 item 3) showed the original "monotonic inversion"
   was a methodology artefact of the broken `ret_30m` column (~5% agreement
   with locally-computed forward return on two independent cohorts). On
   bidirectional data with locally-computed outcome, BULL shows cluster
   *outperformance* (+8.3pp at 60min/0.50%), BEAR shows neither effect.
   There is no inversion to explain.

2) ret_30m column is broken; outcome must be locally-computed.

Reframed question (Exp 50b v2)
------------------------------
Does pre-FVG velocity moderate cluster-FVG WR *symmetrically* across
directions? i.e. does fast pre-FVG velocity produce different outcomes
regardless of whether the cluster is BULL or BEAR?

  - SYMMETRIC effect (DECREASING both sides): tight clusters fail more
    on both sides -> exhaustion / over-extension thesis is real and
    direction-agnostic. Potentially actionable filter.
  - SYMMETRIC effect (INCREASING both sides): tight clusters succeed
    more on both sides -> displacement / momentum thesis. Potentially
    actionable filter (opposite direction from exhaustion).
  - ASYMMETRIC (DECREASING one side, INCREASING the other): velocity
    has direction-conditional effect -> regime artefact, not a structural
    rule. File as TD-056-adjacent finding.
  - FLAT (no clear direction either side): velocity is noise.

Methodology corrections vs original (same as Exp 50 v2)
-------------------------------------------------------
1) OUTCOME METRIC: locally-computed T+30m return from hist_spot_bars_5m
   (Rule 20 era-aware), not hist_pattern_signals.ret_30m.
2) compute_wr_ev is direction-aware (intent = +1 BULL, -1 BEAR). Original
   was hardcoded BULL.
3) Quartile-power thresholds bumped: per-direction N=78 at headline
   means ~19 per quartile -- min cell N for vote raised to 40 (10 per
   quartile) so only well-powered cells count.

Cluster definition + velocity
-----------------------------
Reuses Exp 50 v2 cluster construction. For each cluster pair:
    velocity_pts_per_min = abs(fvg_mid - ob_mid) / delta_min
where delta_min = (fvg_ts - ob_ts) in minutes.

Author: Session 16, item 4.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from supabase import create_client


# --- Constants (mirror Exp 50 v2) --------------------------------------------
PAGE_SIZE = 1000
START_DATE = "2025-04-01"
END_DATE = "2026-04-30"
SYMBOLS = ["NIFTY", "SENSEX"]

SWEEP_LOOKBACK_MIN = [30, 60, 120]
SWEEP_PROXIMITY_PCT = [0.20, 0.50, 1.00]

HEADLINE_LOOKBACK_MIN = 60
HEADLINE_PROXIMITY_PCT = 0.50

N_QUARTILES = 4
# Per-direction split halves N: bumped thresholds vs original
MIN_CELL_N_FOR_QUARTILES = 24  # 6 per quartile minimum
MIN_CELL_N_FOR_VOTE = 40       # 10 per quartile for robustness vote
TOLERANCE_PP = 1.0             # WR swing > 1pp to count as DEC/INC; else FLAT


# --- Rule 20 era-aware helpers -----------------------------------------------
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
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


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


def get_price_ref(row):
    """Zone midpoint as price reference."""
    zl, zh = row.get("zone_low"), row.get("zone_high")
    if zl is None or zh is None:
        return None
    try:
        return (float(zl) + float(zh)) / 2.0
    except (TypeError, ValueError):
        return None


def fetch_signals(sb, pattern_types, start, end):
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


def enrich_with_local_t30m(sb, fvg_rows, symbols, date_min, date_max):
    """Mutates fvg_rows: sets r['computed_ret_30m_pct'] when computable.
    Returns (n_enriched, n_nomatch, n_eos, n_gap)."""
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
    for r in fvg_rows:
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
        r["computed_ret_30m_pct"] = (exit_ - entry) / entry * 100.0
        n_e += 1
    return n_e, n_nm, n_eos, n_gap


# --- Cluster pair construction ------------------------------------------------
def find_cluster_pairs(fvg_rows, ob_by_sym, lookback_min, prox_pct):
    """Returns list of dicts: {fvg, ob, delta_min, velocity, direction}."""
    pairs = []
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
            continue
        sym = fvg.get("symbol")
        candidates = [o for o in ob_by_sym.get(sym, [])
                      if fvg_dir in (o.get("pattern_type") or "")]
        best = None
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
            if fvg_dir == "BULL" and ob_ref > fvg_ref:
                continue
            if fvg_dir == "BEAR" and ob_ref < fvg_ref:
                continue
            if abs(ob_ref - fvg_ref) / fvg_ref * 100.0 > prox_pct:
                continue
            if best is None or delta_min < best["delta_min"]:
                best = {"ob": ob, "delta_min": delta_min, "ob_ref": ob_ref}
        if best is None or best["delta_min"] <= 0:
            continue
        velocity = abs(fvg_ref - best["ob_ref"]) / best["delta_min"]
        pairs.append({
            "fvg": fvg,
            "ob": best["ob"],
            "delta_min": best["delta_min"],
            "velocity": velocity,
            "direction": fvg_dir,
        })
    return pairs


# --- Quartile machinery + direction-aware metrics ----------------------------
def quantile_splits(values, n=4):
    if not values:
        return []
    sv = sorted(values)
    return [sv[min(max(i * len(sv) // n, 0), len(sv) - 1)] for i in range(1, n)]


def assign_quartile(value, splits):
    for i, s in enumerate(splits):
        if value <= s:
            return i
    return len(splits)


def compute_wr_ev(rows, direction):
    """Direction-aware. rows are FVG signal dicts.
    Win = computed_ret_30m_pct * intent > 0."""
    intent = +1 if direction == "BULL" else -1
    n_with = wins = 0
    ev_sum = 0.0
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
        return 0, 0.0, 0.0
    return n_with, wins / n_with * 100.0, ev_sum / n_with


def classify_swing(wrs, tol=TOLERANCE_PP):
    """Returns 'DECREASING' / 'INCREASING' / 'FLAT'."""
    if len(wrs) < 2:
        return "FLAT"
    swing = wrs[0] - wrs[-1]
    if swing > tol:
        return "DECREASING"
    if -swing > tol:
        return "INCREASING"
    return "FLAT"


# --- Main ---------------------------------------------------------------------
def main():
    sb = get_client()
    print("=" * 96)
    print("EXPERIMENT 50b v2  --  Pre-FVG velocity vs cluster WR (BIDIRECTIONAL, REFRAMED)")
    print(f"Run at: {datetime.now(IST).isoformat(timespec='seconds')}")
    print("=" * 96)
    print(f"Window         : {START_DATE} .. {END_DATE}")
    print(f"Sweep          : lookback={SWEEP_LOOKBACK_MIN} min, proximity={SWEEP_PROXIMITY_PCT}%")
    print(f"Headline cell  : lookback={HEADLINE_LOOKBACK_MIN}min, proximity={HEADLINE_PROXIMITY_PCT}%")
    print(f"Quartile thresholds (per direction): "
          f"min N={MIN_CELL_N_FOR_QUARTILES} for breakdown, "
          f"min N={MIN_CELL_N_FOR_VOTE} for sweep vote")
    print(f"Outcome metric : locally-computed T+30m return (Rule 20)")
    print(f"Reframed test  : per-direction WR-vs-velocity direction; symmetric"
          f" effect actionable")
    print()

    # Fetch + enrich
    print("[INFO] fetching FVG signals ...")
    fvg_rows = fetch_signals(sb, ["BULL_FVG", "BEAR_FVG"], START_DATE, END_DATE)
    print(f"[INFO] fetched {len(fvg_rows)} FVG signals "
          f"({dict(Counter(r.get('pattern_type') for r in fvg_rows))})")
    print("[INFO] fetching OB signals ...")
    ob_rows = fetch_signals(sb, ["BULL_OB", "BEAR_OB"], START_DATE, END_DATE)
    print(f"[INFO] fetched {len(ob_rows)} OB signals "
          f"({dict(Counter(r.get('pattern_type') for r in ob_rows))})")
    print()
    if not fvg_rows or not ob_rows:
        sys.exit("[FATAL] insufficient signals.")

    n_e, n_nm, n_eos, n_gap = enrich_with_local_t30m(
        sb, fvg_rows, SYMBOLS, START_DATE, END_DATE
    )
    print(f"[INFO] FVG enrichment: {n_e} enriched, {n_nm} no-match, "
          f"{n_eos} eos-skipped, {n_gap} bar-gap-skipped")
    print()

    ob_by_sym = defaultdict(list)
    for r in ob_rows:
        ob_by_sym[r["symbol"]].append(r)
    for sym in ob_by_sym:
        ob_by_sym[sym].sort(key=lambda x: x.get("bar_ts") or "")

    # ================= HEADLINE per direction =================
    print("=" * 96)
    print(f"HEADLINE  --  lookback={HEADLINE_LOOKBACK_MIN}min, "
          f"proximity={HEADLINE_PROXIMITY_PCT}%")
    print("=" * 96)
    headline_pairs = find_cluster_pairs(
        fvg_rows, ob_by_sym, HEADLINE_LOOKBACK_MIN, HEADLINE_PROXIMITY_PCT
    )
    headline_dirs = {}  # direction -> swing classification
    for direction in ("BULL", "BEAR"):
        side_pairs = [p for p in headline_pairs if p["direction"] == direction]
        n = len(side_pairs)
        print(f"\n  {direction}: {n} cluster pairs")
        if n < MIN_CELL_N_FOR_QUARTILES:
            print(f"    [WARN] N={n} < {MIN_CELL_N_FOR_QUARTILES}; "
                  f"insufficient for quartile breakdown")
            headline_dirs[direction] = None
            continue
        velocities = [p["velocity"] for p in side_pairs]
        splits = quantile_splits(velocities, N_QUARTILES)
        print(f"    Velocity (pts/min): "
              f"min={min(velocities):.3f}  med={sorted(velocities)[n//2]:.3f}  "
              f"max={max(velocities):.3f}")
        print(f"    Quartile splits: {[f'{s:.3f}' for s in splits]}")
        print()
        bucket_rows = defaultdict(list)
        bucket_velocities = defaultdict(list)
        for p in side_pairs:
            q = assign_quartile(p["velocity"], splits)
            bucket_rows[q].append(p["fvg"])
            bucket_velocities[q].append(p["velocity"])
        print(f"    {'Quartile':<10} {'Vel range':<22} {'N':>4} {'WR':>7} {'EV_30m':>10}")
        wrs = []
        for q in range(N_QUARTILES):
            rows = bucket_rows.get(q, [])
            vs = bucket_velocities.get(q, [])
            if not rows:
                continue
            n_q, wr_q, ev_q = compute_wr_ev(rows, direction)
            wrs.append(wr_q)
            v_range = f"{min(vs):.3f}-{max(vs):.3f}" if vs else "-"
            print(f"    Q{q+1:<9} {v_range:<22} {n_q:>4} {wr_q:>6.1f}% {ev_q:>+9.3f}%")
        if len(wrs) >= 2:
            swing = wrs[0] - wrs[-1]
            d = classify_swing(wrs)
            headline_dirs[direction] = d
            print(f"    Swing Q1->Q{len(wrs)}: {wrs[0]:.1f}% -> {wrs[-1]:.1f}% "
                  f"({swing:+.1f}pp) -> {d}")
        else:
            headline_dirs[direction] = None

    # ================= SWEEP per direction =================
    print()
    print("=" * 96)
    print("SWEEP  --  WR-vs-velocity direction per cell, per side")
    print("=" * 96)
    print(f"{'Lookback':>9} {'Prox%':>7} {'Dir':<5} {'N_pairs':>8} "
          f"{'WR_Q1':>7} {'WR_Qn':>9} {'Swing':>9} {'Direction':<14}")
    print("-" * 96)
    cell_results = []  # list of {lb, px, dir, n, wr_q1, wr_qn, swing, label, voting}
    for lb in SWEEP_LOOKBACK_MIN:
        for px in SWEEP_PROXIMITY_PCT:
            pairs = find_cluster_pairs(fvg_rows, ob_by_sym, lb, px)
            for direction in ("BULL", "BEAR"):
                side_pairs = [p for p in pairs if p["direction"] == direction]
                n_pairs = len(side_pairs)
                voting = n_pairs >= MIN_CELL_N_FOR_VOTE
                if n_pairs < MIN_CELL_N_FOR_QUARTILES:
                    print(f"{lb:>9} {px:>6.2f}% {direction:<5} {n_pairs:>8} "
                          f"{'-':>7} {'-':>9} {'-':>9} {'(too few)':<14}")
                    cell_results.append({
                        "lb": lb, "px": px, "dir": direction, "n": n_pairs,
                        "wr_q1": None, "wr_qn": None, "swing": None,
                        "label": None, "voting": False,
                    })
                    continue
                velocities = [p["velocity"] for p in side_pairs]
                splits = quantile_splits(velocities, N_QUARTILES)
                bucket_rows = defaultdict(list)
                for p in side_pairs:
                    q = assign_quartile(p["velocity"], splits)
                    bucket_rows[q].append(p["fvg"])
                wrs = []
                for q in range(N_QUARTILES):
                    rows = bucket_rows.get(q, [])
                    if not rows:
                        wrs.append(None)
                        continue
                    _, wr_q, _ = compute_wr_ev(rows, direction)
                    wrs.append(wr_q)
                valid = [w for w in wrs if w is not None]
                if len(valid) < 2:
                    print(f"{lb:>9} {px:>6.2f}% {direction:<5} {n_pairs:>8} "
                          f"{'-':>7} {'-':>9} {'-':>9} {'(no q-spread)':<14}")
                    cell_results.append({
                        "lb": lb, "px": px, "dir": direction, "n": n_pairs,
                        "wr_q1": None, "wr_qn": None, "swing": None,
                        "label": None, "voting": False,
                    })
                    continue
                wr_q1 = valid[0]
                wr_qn = valid[-1]
                swing = wr_q1 - wr_qn
                label = classify_swing(valid)
                mark = "  *" if voting else ""
                print(f"{lb:>9} {px:>6.2f}% {direction:<5} {n_pairs:>8} "
                      f"{wr_q1:>6.1f}% {wr_qn:>8.1f}% {swing:>+8.1f}pp "
                      f"{label:<10}{mark}")
                cell_results.append({
                    "lb": lb, "px": px, "dir": direction, "n": n_pairs,
                    "wr_q1": wr_q1, "wr_qn": wr_qn, "swing": swing,
                    "label": label, "voting": voting,
                })
    print()
    print(f"(* = cell counts toward robustness vote -- N_pairs >= {MIN_CELL_N_FOR_VOTE})")
    print()

    # ================= ROBUSTNESS VOTE per direction =================
    print("=" * 96)
    print("ROBUSTNESS VOTE  --  per direction, voting cells only")
    print("=" * 96)
    votes = {}  # direction -> {DECREASING, INCREASING, FLAT, total}
    for direction in ("BULL", "BEAR"):
        v_cells = [c for c in cell_results
                   if c["dir"] == direction and c["voting"] and c["label"] is not None]
        n_total = len(v_cells)
        n_dec = sum(1 for c in v_cells if c["label"] == "DECREASING")
        n_inc = sum(1 for c in v_cells if c["label"] == "INCREASING")
        n_flat = sum(1 for c in v_cells if c["label"] == "FLAT")
        votes[direction] = {
            "total": n_total, "dec": n_dec, "inc": n_inc, "flat": n_flat,
        }
        print(f"\n  {direction}:")
        print(f"    Voting cells (N>={MIN_CELL_N_FOR_VOTE}): {n_total}")
        if n_total > 0:
            print(f"      DECREASING: {n_dec} ({n_dec/n_total*100:.0f}%)")
            print(f"      INCREASING: {n_inc} ({n_inc/n_total*100:.0f}%)")
            print(f"      FLAT      : {n_flat} ({n_flat/n_total*100:.0f}%)")

    # ================= VERDICT =================
    print()
    print("=" * 96)
    print("VERDICT")
    print("=" * 96)
    if votes["BULL"]["total"] == 0 or votes["BEAR"]["total"] == 0:
        print("INSUFFICIENT DATA -- one or both directions have no voting cells.")
        print("Possible action: lower MIN_CELL_N_FOR_VOTE or expand date range.")
        return

    def dominant(v):
        """Return ('DECREASING'|'INCREASING'|'FLAT'|'MIXED', share)."""
        if v["total"] == 0:
            return None, 0.0
        labels = [("DECREASING", v["dec"]), ("INCREASING", v["inc"]),
                  ("FLAT", v["flat"])]
        labels.sort(key=lambda x: -x[1])
        top, top_n = labels[0]
        share = top_n / v["total"]
        if share < 0.6:
            return "MIXED", share
        return top, share

    bull_label, bull_share = dominant(votes["BULL"])
    bear_label, bear_share = dominant(votes["BEAR"])
    print(f"BULL dominant: {bull_label} ({bull_share*100:.0f}% of voting cells)")
    print(f"BEAR dominant: {bear_label} ({bear_share*100:.0f}% of voting cells)")
    headline_bull = headline_dirs.get("BULL")
    headline_bear = headline_dirs.get("BEAR")
    print(f"Headline cell BULL: {headline_bull or 'N/A'}")
    print(f"Headline cell BEAR: {headline_bear or 'N/A'}")
    print()

    # Verdict logic
    if bull_label == bear_label and bull_label in ("DECREASING", "INCREASING"):
        if headline_bull == bull_label and headline_bear == bear_label:
            verdict = "SYMMETRIC PASS"
        else:
            verdict = "SYMMETRIC MARGINAL"
    elif (bull_label, bear_label) in (
        ("DECREASING", "INCREASING"), ("INCREASING", "DECREASING")
    ):
        verdict = "ASYMMETRIC"
    elif bull_label == "FLAT" and bear_label == "FLAT":
        verdict = "FAIL (no effect)"
    else:
        verdict = "FAIL (mixed/inconclusive)"

    print(f"VERDICT: {verdict}")
    print()
    if verdict == "SYMMETRIC PASS":
        if bull_label == "DECREASING":
            print("Interpretation: pre-FVG velocity is anti-predictive on BOTH sides.")
            print("Fast cluster setups (high pts/min between OB and FVG) underperform")
            print("slow cluster setups, regardless of direction. Exhaustion thesis")
            print("supported symmetrically -- file as ENH candidate (skip cluster-FVG")
            print("when pre-FVG velocity > threshold T) for shadow validation.")
        else:
            print("Interpretation: pre-FVG velocity is predictive on BOTH sides.")
            print("Fast cluster setups (high pts/min) outperform slow ones, regardless")
            print("of direction. Displacement/momentum thesis. File as ENH candidate")
            print("(prioritise cluster-FVG when pre-FVG velocity > threshold T).")
    elif verdict == "SYMMETRIC MARGINAL":
        print("Interpretation: sweep agrees on direction but headline cell does not")
        print("clean up. Effect is real but not strong at the canonical (60/0.50%)")
        print("cell. Could test alternative headline cells before filing as ENH.")
    elif verdict == "ASYMMETRIC":
        print("Interpretation: velocity has direction-conditional effect. NOT a")
        print("structural rule. Most likely a market-regime artefact (TD-056 family)")
        print("-- BULL/BEAR clusters in the same time window experience opposite")
        print("velocity-WR relationships because they fire at structurally different")
        print("phases of the regime. File as TD/Compendium finding; do not act.")
    elif verdict.startswith("FAIL"):
        print("Interpretation: pre-FVG velocity is not a useful filter on this data.")
        print("Either velocity is genuinely noise, or the effect (if any) is too")
        print("subtle to detect at this N. Park; do not act.")


if __name__ == "__main__":
    main()
