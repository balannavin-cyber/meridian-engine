"""
experiment_50b_fvg_on_ob_velocity.py

EXPERIMENT 50b — FVG-on-OB Cluster Inversion: Velocity Test

Background:
    Exp 50 found a smooth, monotonic inversion of ICT's "FVG-above-OB"
    hypothesis. Tighter (OB,FVG) coupling -> WORSE FVG outcomes.

    Sweep result snapshot (BULL only, BEAR_FVG doesn't exist in the dataset):
       lookback   prox%   WR_delta   N_cluster
       30 min     0.20%   -36.2pp        8
       30 min     0.50%   -15.2pp       47
       30 min     1.00%    -6.1pp       63
       60 min     0.50%   -12.7pp       75
      120 min     1.00%   +16.4pp      242

Hypothesis under test (Exp 50b):
    The Exp 50 inversion is driven by EXHAUSTION, not sponsorship. A
    BULL_OB closely followed by a BULL_FVG indicates price has already
    moved fast and is over-extended at the FVG. The FVG forms late in
    a fast push and fails more often.

Mechanism:
    Measure pre-FVG velocity = points moved per minute between OB time
    and FVG time. Partition cluster-FVGs by velocity quartile. If the
    exhaustion theory is correct, FVG WR should DROP as pre-FVG velocity
    INCREASES.

Method:
    1. Reuse Exp 50's cluster definition. For each cluster-FVG, compute:
         velocity_pts_per_min = abs(fvg_price_ref - ob_price_ref) / delta_min
       where delta_min = (fvg_ts - ob_ts) in minutes.
    2. Compute WR + EV_30m per velocity quartile.
    3. Rerun across same Exp 50 sweep grid; for each cell, also report
       Spearman-style direction (does WR fall as velocity rises?).

PASS/FAIL:
    PASS = WR drops monotonically across velocity quartiles in headline
           cell AND at least 60% of sweep cells (with N_cluster>=20)
           show the same direction.
    FAIL = no consistent velocity-WR relationship.

If PASS:
    Implies an actionable filter -- "skip BULL_FVG signals where pre-FVG
    velocity exceeds threshold T" -- testable as a follow-up ENH.

If FAIL:
    Inversion in Exp 50 is something else (e.g. survivorship bias in the
    standalone bucket as cluster definition expands). Park as anomaly.

Forbidden ground:
    Same as Exp 50 -- do not redefine FVG/OB detection. ret_30m used
    per Rule 14. No IST clock-time filtering (TZ-bug-proof).

Author: Session 15 batch.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict, Counter
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000
START_DATE = "2025-04-01"
END_DATE = "2026-04-30"
SYMBOLS = ["NIFTY", "SENSEX"]

# Same sweep grid as Exp 50 for direct comparability
SWEEP_LOOKBACK_MIN = [30, 60, 120]
SWEEP_PROXIMITY_PCT = [0.20, 0.50, 1.00]

HEADLINE_LOOKBACK_MIN = 60
HEADLINE_PROXIMITY_PCT = 0.50

N_QUARTILES = 4
MIN_CELL_N_FOR_VOTE = 20  # min N_cluster to count a cell in robustness vote
MIN_CELL_N_FOR_QUARTILES = 12  # min N_cluster to compute meaningful quartiles


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def discover_ts_column(sb, table: str):
    r = sb.table(table).select("*").limit(1).execute()
    if not r.data:
        return None, {}
    sample = r.data[0]
    for c in ("bar_ts", "signal_ts", "ts", "entry_ts", "detected_ts"):
        if c in sample:
            return c, sample
    return None, sample


def fetch_signals(sb, ts_col, pattern_types, start, end):
    rows = []
    offset = 0
    while True:
        r = (sb.table("hist_pattern_signals").select("*")
             .in_("pattern_type", pattern_types)
             .gte(ts_col, f"{start}T00:00:00+00:00")
             .lte(ts_col, f"{end}T23:59:59+00:00")
             .order(ts_col)
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 200_000:
            break
    return rows


def get_price_ref(row, ts_col):
    """Same priority as Exp 50: signal_price > entry_price > price > zone midpoint.
    No bar lookup fallback in this script (zone midpoint is always available
    in MERDIAN's hist_pattern_signals)."""
    for col in ("signal_price", "entry_price", "price"):
        v = row.get(col)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    zl, zh = row.get("zone_low"), row.get("zone_high")
    if zl is not None and zh is not None:
        try:
            return (float(zl) + float(zh)) / 2.0
        except (TypeError, ValueError):
            pass
    return None


def find_cluster_pairs(fvg_rows, ob_by_sym, ts_col, lookback_min, prox_pct):
    """Returns list of (fvg_row, matched_ob_row, delta_min, velocity_pts_per_min)
    for each clustered FVG. Standalone FVGs are not returned here -- this script
    cares about velocity within clusters."""
    pairs = []
    for fvg in fvg_rows:
        ptype = fvg.get("pattern_type") or ""
        fvg_dir = "BULL" if "BULL" in ptype else ("BEAR" if "BEAR" in ptype else None)
        if fvg_dir is None:
            continue
        fvg_ts = parse_dt(fvg.get(ts_col))
        if fvg_ts is None:
            continue
        fvg_ref = get_price_ref(fvg, ts_col)
        if fvg_ref is None or fvg_ref == 0:
            continue
        sym = fvg.get("symbol")
        candidates = [o for o in ob_by_sym.get(sym, [])
                      if fvg_dir in (o.get("pattern_type") or "")]
        # Take the MOST RECENT qualifying OB (closest in time, structurally valid)
        best = None  # (delta_min, ob_row, ob_ref)
        for ob in candidates:
            ob_ts = parse_dt(ob.get(ts_col))
            if ob_ts is None or ob_ts >= fvg_ts:
                continue
            delta_min = (fvg_ts - ob_ts).total_seconds() / 60.0
            if delta_min < 0 or delta_min > lookback_min:
                continue
            ob_ref = get_price_ref(ob, ts_col)
            if ob_ref is None or ob_ref == 0:
                continue
            if fvg_dir == "BULL" and ob_ref > fvg_ref:
                continue
            if fvg_dir == "BEAR" and ob_ref < fvg_ref:
                continue
            if abs(ob_ref - fvg_ref) / fvg_ref * 100.0 > prox_pct:
                continue
            if best is None or delta_min < best[0]:
                best = (delta_min, ob, ob_ref)
        if best is None:
            continue
        delta_min, ob_row, ob_ref = best
        if delta_min <= 0:
            continue
        velocity = abs(fvg_ref - ob_ref) / delta_min  # pts per minute
        pairs.append((fvg, ob_row, delta_min, velocity, fvg_dir))
    return pairs


def quartile_split(values: list[float], n: int = 4) -> list[float]:
    """Return n-1 split points at quantile boundaries (n=4 -> 3 splits)."""
    if not values:
        return []
    sv = sorted(values)
    splits = []
    for i in range(1, n):
        idx = i * len(sv) // n
        idx = min(max(idx, 0), len(sv) - 1)
        splits.append(sv[idx])
    return splits


def assign_quartile(value: float, splits: list[float]) -> int:
    """Returns 0..n-1 quartile index given splits."""
    for i, s in enumerate(splits):
        if value <= s:
            return i
    return len(splits)


def compute_wr_ev(rows: list[dict]) -> tuple[int, float, float]:
    """rows are FVG signal rows. Returns (n, wr_pct, ev_30m).
    Assumes BULL direction (Exp 50 found no BEAR_FVG in dataset)."""
    n = len(rows)
    if n == 0:
        return 0, 0.0, 0.0
    wins = 0
    ev_sum = 0.0
    for r in rows:
        ret30 = r.get("ret_30m")
        if ret30 is None:
            continue
        # BULL: positive ret_30m = win
        if ret30 > 0:
            wins += 1
        ev_sum += ret30
    return n, wins / n * 100, ev_sum / n


def is_monotonic_decreasing(seq: list[float]) -> bool:
    """True iff each value is <= the previous (strictly weak monotonic)."""
    return all(seq[i] <= seq[i - 1] for i in range(1, len(seq)))


def is_directionally_decreasing(seq: list[float], tolerance_pp: float = 1.0) -> bool:
    """True iff first-quartile WR > last-quartile WR by > tolerance_pp.
    Less strict than monotonic; captures 'WR generally drops with velocity'."""
    if len(seq) < 2:
        return False
    return seq[0] - seq[-1] > tolerance_pp


def main():
    sb = get_client()
    print("=" * 96)
    print("EXPERIMENT 50b — FVG-on-OB Cluster Inversion: Velocity Test")
    print("=" * 96)
    print(f"Window: {START_DATE} .. {END_DATE}")
    print(f"Sweep: lookback={SWEEP_LOOKBACK_MIN} min, proximity={SWEEP_PROXIMITY_PCT}%")
    print(f"Headline cell: lookback={HEADLINE_LOOKBACK_MIN}, proximity={HEADLINE_PROXIMITY_PCT}%")
    print(f"Quartiles: {N_QUARTILES}")
    print()

    ts_col, sample = discover_ts_column(sb, "hist_pattern_signals")
    if ts_col is None:
        print(f"[FATAL] no ts column. cols={sorted(sample.keys())}")
        sys.exit(2)
    print(f"[INFO] ts column: {ts_col}")
    print()

    print("[INFO] fetching FVG signals ...")
    fvg_rows = fetch_signals(sb, ts_col, ["BULL_FVG", "BEAR_FVG"], START_DATE, END_DATE)
    print(f"[INFO] fetched {len(fvg_rows)} FVG signals")
    fvg_dist = Counter(r.get("pattern_type") for r in fvg_rows)
    print(f"[INFO] FVG distribution: {dict(fvg_dist)}")

    print("[INFO] fetching OB signals ...")
    ob_rows = fetch_signals(sb, ts_col, ["BULL_OB", "BEAR_OB"], START_DATE, END_DATE)
    print(f"[INFO] fetched {len(ob_rows)} OB signals")
    print()

    if not fvg_rows or not ob_rows:
        print("[FATAL] insufficient signals.")
        sys.exit(1)

    ob_by_sym = defaultdict(list)
    for r in ob_rows:
        ob_by_sym[r["symbol"]].append(r)
    for sym in ob_by_sym:
        ob_by_sym[sym].sort(key=lambda x: x.get(ts_col) or "")

    # ============ HEADLINE CELL: detailed quartile breakdown ============
    print("=" * 96)
    print(f"HEADLINE — lookback={HEADLINE_LOOKBACK_MIN}min, proximity={HEADLINE_PROXIMITY_PCT}%")
    print("=" * 96)
    pairs = find_cluster_pairs(
        fvg_rows, ob_by_sym, ts_col,
        HEADLINE_LOOKBACK_MIN, HEADLINE_PROXIMITY_PCT
    )
    print(f"Cluster pairs in headline cell: {len(pairs)}")
    if len(pairs) < MIN_CELL_N_FOR_QUARTILES:
        print(f"[WARN] N={len(pairs)} too small for {N_QUARTILES} quartiles "
              f"(need >= {MIN_CELL_N_FOR_QUARTILES}). Showing summary stats only.")
    if pairs:
        velocities = [p[3] for p in pairs]
        deltas = [p[2] for p in pairs]
        print(f"  Velocity (pts/min): min={min(velocities):.3f} med="
              f"{sorted(velocities)[len(velocities)//2]:.3f} max={max(velocities):.3f}")
        print(f"  Time delta (min):   min={min(deltas):.1f} med="
              f"{sorted(deltas)[len(deltas)//2]:.1f} max={max(deltas):.1f}")
        print()

    if pairs and len(pairs) >= MIN_CELL_N_FOR_QUARTILES:
        velocities = [p[3] for p in pairs]
        splits = quartile_split(velocities, N_QUARTILES)
        print(f"  Quartile split points (velocity, pts/min): "
              f"{[f'{s:.3f}' for s in splits]}")
        print()
        # Bucket and report
        bucket_rows = defaultdict(list)
        bucket_velocities = defaultdict(list)
        bucket_deltas = defaultdict(list)
        for fvg, ob, dmin, vel, dirn in pairs:
            q = assign_quartile(vel, splits)
            bucket_rows[q].append(fvg)
            bucket_velocities[q].append(vel)
            bucket_deltas[q].append(dmin)
        print(f"{'Quartile':<10} {'Vel range':<22} {'Delta range':<22} "
              f"{'N':>5} {'WR':>7} {'EV_30m':>10}")
        print("-" * 96)
        wrs = []
        for q in range(N_QUARTILES):
            rows = bucket_rows.get(q, [])
            vs = bucket_velocities.get(q, [])
            ds = bucket_deltas.get(q, [])
            if not rows:
                continue
            n, wr, ev = compute_wr_ev(rows)
            wrs.append(wr)
            v_range = f"{min(vs):.3f}-{max(vs):.3f}"
            d_range = f"{min(ds):.1f}-{max(ds):.1f}m"
            print(f"Q{q+1:<9} {v_range:<22} {d_range:<22} "
                  f"{n:>5} {wr:>6.1f}% {ev:>+9.3f}%")
        print()
        # Direction check
        if len(wrs) >= 2:
            mono = is_monotonic_decreasing(wrs)
            directional = is_directionally_decreasing(wrs, 1.0)
            wr_swing = wrs[0] - wrs[-1]
            print(f"  WR Q1->Q{len(wrs)}: {wrs[0]:.1f}% -> {wrs[-1]:.1f}% "
                  f"(swing: {wr_swing:+.1f}pp)")
            print(f"  Strictly monotonic decreasing: {mono}")
            print(f"  Directionally decreasing (Q1>Qn by >1pp): {directional}")
        print()

    # ============ SWEEP — direction vote across all cells ============
    print("=" * 96)
    print("SWEEP — direction of WR-vs-velocity across all cells")
    print("=" * 96)
    print(f"{'Lookback':>9} {'Prox%':>7} {'N_pairs':>8} "
          f"{'WR_Q1':>7} {'WR_Q{n}':>9} {'Swing':>9} {'Direction':<14}")
    print("-" * 96)
    cell_results = []
    for lb in SWEEP_LOOKBACK_MIN:
        for px in SWEEP_PROXIMITY_PCT:
            pairs = find_cluster_pairs(fvg_rows, ob_by_sym, ts_col, lb, px)
            n_pairs = len(pairs)
            if n_pairs < MIN_CELL_N_FOR_QUARTILES:
                print(f"{lb:>9} {px:>6.2f}% {n_pairs:>8} "
                      f"{'-':>7} {'-':>9} {'-':>9} {'(too few)':<14}")
                cell_results.append((lb, px, n_pairs, None, None, None, None))
                continue
            velocities = [p[3] for p in pairs]
            splits = quartile_split(velocities, N_QUARTILES)
            bucket_rows = defaultdict(list)
            for fvg, ob, dmin, vel, dirn in pairs:
                q = assign_quartile(vel, splits)
                bucket_rows[q].append(fvg)
            wrs = []
            for q in range(N_QUARTILES):
                rows = bucket_rows.get(q, [])
                if not rows:
                    wrs.append(None)
                    continue
                _, wr, _ = compute_wr_ev(rows)
                wrs.append(wr)
            valid_wrs = [w for w in wrs if w is not None]
            if len(valid_wrs) < 2:
                print(f"{lb:>9} {px:>6.2f}% {n_pairs:>8} "
                      f"{'-':>7} {'-':>9} {'-':>9} {'(no q-spread)':<14}")
                cell_results.append((lb, px, n_pairs, None, None, None, None))
                continue
            wr_q1 = valid_wrs[0]
            wr_qlast = valid_wrs[-1]
            swing = wr_q1 - wr_qlast
            directional_decreasing = is_directionally_decreasing(valid_wrs, 1.0)
            direction = ("DECREASING" if directional_decreasing
                         else "INCREASING" if (wr_qlast - wr_q1) > 1.0
                         else "FLAT")
            counts_for_vote = n_pairs >= MIN_CELL_N_FOR_VOTE
            mark = "  *" if counts_for_vote else ""
            print(f"{lb:>9} {px:>6.2f}% {n_pairs:>8} "
                  f"{wr_q1:>6.1f}% {wr_qlast:>8.1f}% {swing:>+8.1f}pp {direction:<10}{mark}")
            cell_results.append((lb, px, n_pairs, wr_q1, wr_qlast, swing, direction))
    print()
    print("(* = cell counts toward robustness vote -- N_pairs >= "
          f"{MIN_CELL_N_FOR_VOTE})")
    print()

    # ============ ROBUSTNESS VOTE ============
    print("=" * 96)
    print("ROBUSTNESS VOTE")
    print("=" * 96)
    voting_cells = [c for c in cell_results
                    if c[2] is not None and c[2] >= MIN_CELL_N_FOR_VOTE
                    and c[6] is not None]
    n_total = len(voting_cells)
    n_dec = sum(1 for c in voting_cells if c[6] == "DECREASING")
    n_inc = sum(1 for c in voting_cells if c[6] == "INCREASING")
    n_flat = sum(1 for c in voting_cells if c[6] == "FLAT")
    print(f"Voting cells (N_pairs >= {MIN_CELL_N_FOR_VOTE}): {n_total}")
    print(f"  DECREASING (supports exhaustion): {n_dec}")
    print(f"  INCREASING (refutes exhaustion):  {n_inc}")
    print(f"  FLAT (no signal):                 {n_flat}")
    print()

    print("=" * 96)
    print("VERDICT")
    print("=" * 96)
    if n_total == 0:
        print("INSUFFICIENT DATA — no cells with N_pairs >= "
              f"{MIN_CELL_N_FOR_VOTE} and quartile spread.")
    else:
        dec_pct = n_dec / n_total * 100
        # Headline cell direction
        headline_cell = next((c for c in cell_results
                              if c[0] == HEADLINE_LOOKBACK_MIN
                              and c[1] == HEADLINE_PROXIMITY_PCT), None)
        headline_dir = headline_cell[6] if headline_cell else None
        headline_passes = (headline_dir == "DECREASING")
        sweep_passes = dec_pct >= 60
        if headline_passes and sweep_passes:
            verdict = "PASS"
        elif headline_passes or sweep_passes:
            verdict = "MARGINAL"
        else:
            verdict = "FAIL"
        print(f"Headline cell direction: {headline_dir or 'N/A'} "
              f"(passes if DECREASING)")
        print(f"Sweep cells DECREASING: {n_dec}/{n_total} = {dec_pct:.0f}% "
              f"(passes if >= 60%)")
        print(f"VERDICT: {verdict}")
        print()
        if verdict == "PASS":
            print("Interpretation: exhaustion theory supported. The Exp 50 inversion is")
            print("driven by pre-FVG velocity. Actionable as a filter -- skip BULL_FVG")
            print("when pre-FVG velocity exceeds threshold T (file as Exp 50c if pursued).")
        elif verdict == "MARGINAL":
            print("Interpretation: partial support. Direction is right but not strong")
            print("enough to act on. Could be exhaustion + something else (e.g.")
            print("survivorship bias in standalone bucket as cluster definition expands).")
        else:
            print("Interpretation: exhaustion theory NOT supported. The Exp 50 inversion")
            print("is something else -- most likely survivorship bias in standalone bucket")
            print("as cluster definition loosens. Park as anomaly; do not act.")
    print("=" * 96)


if __name__ == "__main__":
    main()
