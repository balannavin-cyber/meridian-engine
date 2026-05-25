"""
experiment_50_fvg_on_ob_cluster.py

EXPERIMENT 50 — FVG-on-OB Cluster vs Standalone FVG

Hypothesis (ICT PD Array Matrix):
    A BULL_FVG that forms immediately above a recent BULL_OB has higher
    WR/EV than a standalone BULL_FVG. Mirror for BEAR side (BEAR_FVG
    immediately below a recent BEAR_OB).

    Theory: the OB represents institutional sponsorship; an FVG forming
    in the same direction shortly after price leaves the OB confirms
    displacement (aggressive institutional buying/selling). The OB acts
    as a secondary support/resistance layer below/above the FVG, making
    the structure a higher-confluence setup than a standalone FVG.

Cluster definition:
    CLUSTER BULL_FVG: a BULL_FVG signal at time T_fvg where there exists
    a BULL_OB signal at time T_ob such that:
        - same symbol
        - T_ob < T_fvg
        - T_fvg - T_ob <= LOOKBACK_MIN (sweep over 30/60/120 min)
        - OB price reference < FVG price reference (structurally below)
        - |OB_ref - FVG_ref| / FVG_ref * 100 <= PROXIMITY_PCT
          (sweep over 0.20%/0.50%/1.00%)

    CLUSTER BEAR_FVG: mirror — BEAR_FVG with BEAR_OB above, same time
    and proximity criteria.

Standalone:
    FVG signals that don't satisfy any cluster relationship.

Outcome metric (per Rule 14):
    ret_30m / ret_60m / ret_eod from hist_pattern_signals — forward-looking
    percentage points after signal entry. Sign-aligned to direction
    (BULL: positive = win; BEAR: negative = win).

PASS criterion:
    Cluster WR >= Standalone WR + 5pp
    AND Cluster EV_30m >= Standalone EV_30m * 1.3
    AND N_cluster >= 30
    Robust if the relationship holds across most (LOOKBACK, PROXIMITY) cells.

TZ note:
    Uses bar_ts purely for ordering and time-delta arithmetic. No IST
    clock-time filtering, so the post-04-07 TZ era issue is irrelevant.

Forbidden ground:
    Do not redefine FVG or OB detection — use hist_pattern_signals as-is.
    Do not adjust thresholds post-hoc; the sweep IS the robustness check.

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

# Sweep grid for robustness
SWEEP_LOOKBACK_MIN = [30, 60, 120]
SWEEP_PROXIMITY_PCT = [0.20, 0.50, 1.00]

# Default cell for the headline summary (used in PASS-criterion check)
HEADLINE_LOOKBACK_MIN = 60
HEADLINE_PROXIMITY_PCT = 0.50


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


def discover_ts_column(sb, table: str) -> tuple[str | None, dict]:
    r = sb.table(table).select("*").limit(1).execute()
    if not r.data:
        return None, {}
    sample = r.data[0]
    for c in ("bar_ts", "signal_ts", "ts", "entry_ts", "detected_ts"):
        if c in sample:
            return c, sample
    return None, sample


def fetch_signals(sb, ts_col: str, pattern_types: list[str], start: str, end: str) -> list[dict]:
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


def fetch_5m_close_lookup(sb, symbol: str, start: str, end: str) -> dict:
    """Returns {bar_ts_str: close_float} for the symbol over the window."""
    out = {}
    offset = 0
    while True:
        r = (sb.table("hist_spot_bars_5m").select("bar_ts, close")
             .eq("symbol", symbol)
             .gte("bar_ts", f"{start}T00:00:00+00:00")
             .lte("bar_ts", f"{end}T23:59:59+00:00")
             .order("bar_ts")
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        for row in batch:
            try:
                out[row["bar_ts"]] = float(row["close"])
            except (TypeError, ValueError, KeyError):
                continue
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 500_000:
            break
    return out


def get_price_ref(row: dict, bar_lookup: dict, ts_col: str) -> float | None:
    """Best available price reference for a signal row.
    Priority: signal_price > entry_price > price > zone midpoint > 5m close lookup.
    """
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
    sym = row.get("symbol")
    bar_ts = row.get(ts_col)
    if sym and bar_ts and sym in bar_lookup:
        return bar_lookup[sym].get(bar_ts)
    return None


def classify_fvgs(fvg_rows: list[dict], ob_by_sym: dict, ts_col: str,
                  bar_lookup: dict, lookback_min: int, prox_pct: float):
    """Returns (cluster_rows, standalone_rows, skipped_no_price).
    Each grouped further by direction internally is up to caller; here we
    return flat lists of FVG rows.
    """
    cluster = []
    standalone = []
    skipped = 0
    for fvg in fvg_rows:
        ptype = fvg.get("pattern_type") or ""
        fvg_dir = "BULL" if "BULL" in ptype else ("BEAR" if "BEAR" in ptype else None)
        if fvg_dir is None:
            continue
        fvg_ts = parse_dt(fvg.get(ts_col))
        if fvg_ts is None:
            continue
        fvg_ref = get_price_ref(fvg, bar_lookup, ts_col)
        if fvg_ref is None:
            skipped += 1
            continue
        sym = fvg.get("symbol")
        candidates = [o for o in ob_by_sym.get(sym, [])
                      if fvg_dir in (o.get("pattern_type") or "")]
        matched = False
        for ob in candidates:
            ob_ts = parse_dt(ob.get(ts_col))
            if ob_ts is None or ob_ts >= fvg_ts:
                continue
            delta_min = (fvg_ts - ob_ts).total_seconds() / 60.0
            if delta_min < 0 or delta_min > lookback_min:
                continue
            ob_ref = get_price_ref(ob, bar_lookup, ts_col)
            if ob_ref is None:
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


def compute_metrics(rows: list[dict], direction: str, has_eod: bool) -> dict:
    """Per-bucket metrics. direction in ('BULL','BEAR')."""
    n = len(rows)
    if n == 0:
        return {"n": 0}
    intent = +1 if direction == "BULL" else -1
    wins = 0
    ev30_sum = 0.0
    ev60_sum = 0.0
    eveod_sum = 0.0
    for r in rows:
        ret30 = r.get("ret_30m")
        if ret30 is None:
            continue
        signed30 = ret30 * intent
        if signed30 > 0:
            wins += 1
        ev30_sum += signed30
        ret60 = r.get("ret_60m")
        if ret60 is not None:
            ev60_sum += ret60 * intent
        if has_eod:
            ret_eod = r.get("ret_eod")
            if ret_eod is not None:
                eveod_sum += ret_eod * intent
    wr = wins / n * 100
    return {
        "n": n,
        "wr": wr,
        "ev30": ev30_sum / n,
        "ev60": ev60_sum / n,
        "eveod": (eveod_sum / n) if has_eod else None,
    }


def main():
    sb = get_client()
    print("=" * 92)
    print("EXPERIMENT 50 — FVG-on-OB Cluster vs Standalone FVG")
    print("=" * 92)
    print(f"Window: {START_DATE} .. {END_DATE}")
    print(f"Sweep: lookback={SWEEP_LOOKBACK_MIN} min, proximity={SWEEP_PROXIMITY_PCT}%")
    print(f"Headline cell: lookback={HEADLINE_LOOKBACK_MIN}, proximity={HEADLINE_PROXIMITY_PCT}%")
    print()

    ts_col, sample = discover_ts_column(sb, "hist_pattern_signals")
    if ts_col is None:
        print(f"[FATAL] no ts column. cols={sorted(sample.keys())}")
        sys.exit(2)
    print(f"[INFO] ts column: {ts_col}")
    has_eod = "ret_eod" in sample
    print(f"[INFO] ret_eod column: {'present' if has_eod else 'absent'}")
    print()

    print("[INFO] fetching FVG signals ...")
    fvg_rows = fetch_signals(sb, ts_col, ["BULL_FVG", "BEAR_FVG"], START_DATE, END_DATE)
    print(f"[INFO] fetched {len(fvg_rows)} FVG signals")
    fvg_dist = Counter(r.get("pattern_type") for r in fvg_rows)
    print(f"[INFO] FVG pattern distribution: {dict(fvg_dist)}")
    print()

    print("[INFO] fetching OB signals ...")
    ob_rows = fetch_signals(sb, ts_col, ["BULL_OB", "BEAR_OB"], START_DATE, END_DATE)
    print(f"[INFO] fetched {len(ob_rows)} OB signals")
    ob_dist = Counter(r.get("pattern_type") for r in ob_rows)
    print(f"[INFO] OB pattern distribution: {dict(ob_dist)}")
    print()

    if not fvg_rows or not ob_rows:
        print("[FATAL] insufficient signals.")
        sys.exit(1)

    # Decide if we need the bar lookup based on column availability
    needs_bars = not any(c in sample for c in ("signal_price", "entry_price", "price"))
    has_zone_cols = "zone_low" in sample and "zone_high" in sample
    bar_lookup = {}
    if needs_bars and not has_zone_cols:
        print("[INFO] no signal price columns and no zone bounds -- fetching 5m bars for lookup ...")
        for sym in SYMBOLS:
            bar_lookup[sym] = fetch_5m_close_lookup(sb, sym, START_DATE, END_DATE)
            print(f"[INFO]   {sym}: {len(bar_lookup[sym])} bars indexed")
    elif needs_bars and has_zone_cols:
        print("[INFO] using zone_low/zone_high midpoint as price reference")
    else:
        present = [c for c in ("signal_price", "entry_price", "price") if c in sample]
        print(f"[INFO] using signal price column: {present[0]}")
    print()

    # Index OB rows by symbol, sorted by ts
    ob_by_sym = defaultdict(list)
    for r in ob_rows:
        ob_by_sym[r["symbol"]].append(r)
    for sym in ob_by_sym:
        ob_by_sym[sym].sort(key=lambda x: x.get(ts_col) or "")

    # ============ SWEEP ============
    print("=" * 92)
    print("RESULTS — full sweep")
    print("=" * 92)
    print(f"{'Lookback':>9} {'Prox%':>7} {'Dir':<5} {'Bucket':<11} "
          f"{'N':>6} {'WR':>7} {'EV_30m':>9} {'EV_60m':>9} {'EV_eod':>9}")
    print("-" * 92)

    cells: dict = {}  # (lookback, prox) -> {direction -> {bucket -> metrics}}
    for lookback_min in SWEEP_LOOKBACK_MIN:
        for prox_pct in SWEEP_PROXIMITY_PCT:
            cluster, standalone, skipped = classify_fvgs(
                fvg_rows, ob_by_sym, ts_col, bar_lookup, lookback_min, prox_pct
            )
            cell = {}
            for direction in ("BULL", "BEAR"):
                cell[direction] = {}
                for bucket_name, rows in (
                    ("standalone", [r for r in standalone if direction in (r.get("pattern_type") or "")]),
                    ("cluster",    [r for r in cluster if direction in (r.get("pattern_type") or "")]),
                ):
                    m = compute_metrics(rows, direction, has_eod)
                    cell[direction][bucket_name] = m
                    if m["n"] == 0:
                        continue
                    eod_str = (f"{m['eveod']:>+8.3f}%" if m.get("eveod") is not None else "    N/A  ")
                    print(f"{lookback_min:>9} {prox_pct:>6.2f}% {direction:<5} {bucket_name:<11} "
                          f"{m['n']:>6} {m['wr']:>6.1f}% {m['ev30']:>+8.3f}% {m['ev60']:>+8.3f}% {eod_str}")
            cells[(lookback_min, prox_pct)] = cell
            print()

    # ============ HEADLINE COMPARISON + PASS CHECK ============
    print("=" * 92)
    print(f"HEADLINE — lookback={HEADLINE_LOOKBACK_MIN}min, proximity={HEADLINE_PROXIMITY_PCT}%")
    print("=" * 92)
    headline = cells.get((HEADLINE_LOOKBACK_MIN, HEADLINE_PROXIMITY_PCT))
    if headline is None:
        print("[WARN] headline cell not in sweep grid")
    else:
        for direction in ("BULL", "BEAR"):
            sa = headline[direction]["standalone"]
            cl = headline[direction]["cluster"]
            if sa["n"] == 0 or cl["n"] == 0:
                print(f"  {direction}: insufficient data (standalone N={sa['n']}, cluster N={cl['n']})")
                continue
            wr_diff = cl["wr"] - sa["wr"]
            ev_ratio = cl["ev30"] / sa["ev30"] if sa["ev30"] != 0 else float("inf")
            print(f"  {direction}:")
            print(f"    Standalone: N={sa['n']:>5} WR={sa['wr']:>5.1f}% "
                  f"EV_30m={sa['ev30']:>+6.3f}% EV_60m={sa['ev60']:>+6.3f}%")
            print(f"    Cluster:    N={cl['n']:>5} WR={cl['wr']:>5.1f}% "
                  f"EV_30m={cl['ev30']:>+6.3f}% EV_60m={cl['ev60']:>+6.3f}%")
            print(f"    Delta:      WR {wr_diff:>+5.1f}pp, EV_30m ratio {ev_ratio:>+5.2f}x")
            verdict_parts = []
            wr_ok = wr_diff >= 5
            ev_ok = ev_ratio >= 1.3
            n_ok = cl["n"] >= 30
            verdict_parts.append(f"WR {'PASS' if wr_ok else 'FAIL'} ({wr_diff:+.1f}pp vs +5pp bar)")
            verdict_parts.append(f"EV {'PASS' if ev_ok else 'FAIL'} ({ev_ratio:.2f}x vs 1.3x bar)")
            verdict_parts.append(f"N {'PASS' if n_ok else 'FAIL'} ({cl['n']} vs 30 bar)")
            verdict = "PASS" if (wr_ok and ev_ok and n_ok) else "FAIL"
            print(f"    Verdict:    {verdict} -- {'; '.join(verdict_parts)}")
            print()

    # ============ ROBUSTNESS — verdict per cell ============
    print("=" * 92)
    print("ROBUSTNESS — does the cluster effect survive across the sweep grid?")
    print("=" * 92)
    print(f"{'Lookback':>9} {'Prox%':>7} {'Dir':<5} {'WR delta':>10} {'EV ratio':>10} {'N_cl':>6} {'cell verdict':<14}")
    print("-" * 92)
    pass_count = {"BULL": 0, "BEAR": 0}
    eval_count = {"BULL": 0, "BEAR": 0}
    for (lb, px), cell in cells.items():
        for direction in ("BULL", "BEAR"):
            sa = cell[direction]["standalone"]
            cl = cell[direction]["cluster"]
            if sa["n"] == 0 or cl["n"] == 0:
                continue
            eval_count[direction] += 1
            wr_diff = cl["wr"] - sa["wr"]
            ev_ratio = cl["ev30"] / sa["ev30"] if sa["ev30"] != 0 else float("inf")
            wr_ok = wr_diff >= 5
            ev_ok = ev_ratio >= 1.3
            n_ok = cl["n"] >= 30
            cell_pass = wr_ok and ev_ok and n_ok
            if cell_pass:
                pass_count[direction] += 1
            print(f"{lb:>9} {px:>6.2f}% {direction:<5} "
                  f"{wr_diff:>+9.1f}pp {ev_ratio:>+9.2f}x {cl['n']:>6} "
                  f"{('PASS' if cell_pass else 'FAIL'):<14}")
    print()
    for direction in ("BULL", "BEAR"):
        n_eval = eval_count[direction]
        n_pass = pass_count[direction]
        print(f"  {direction}: {n_pass}/{n_eval} cells PASS the (WR+5pp, EV*1.3, N>=30) bar")
    print()
    print("=" * 92)
    print("INTERPRETATION:")
    print("  - If most cells PASS for a direction, the cluster effect is robust;")
    print("    consider an ENH that promotes cluster-FVG sizing over standalone.")
    print("  - If only the headline cell PASSes and surrounding cells FAIL, the")
    print("    effect is threshold-fragile -- treat as a hint, not an edge.")
    print("  - If cells FAIL across the grid, ICT's hierarchy doesn't replicate")
    print("    in MERDIAN's data; standalone vs cluster is not predictive here.")
    print("=" * 92)


if __name__ == "__main__":
    main()
