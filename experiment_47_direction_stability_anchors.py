"""
experiment_47_direction_stability_anchors.py

EXPERIMENT 47 — Direction Stability via Slower Anchor (subsumes Exp 43)

Question:
    If the V4 direction logic in build_trade_signal_local.py used `ret_30m` (or
    `ret_60m`) instead of `ret_session` as its directional anchor, would intraday
    flip rate drop materially without hurting per-pattern WR?

Approach:
    Counterfactual replay on hist_pattern_signals last 12 months. For each pattern
    row, compute the "would-have-fired direction" under three policies:
        Policy A: sign of ret_session at signal time (CURRENT V4 behaviour proxy)
        Policy B: sign of ret_30m at signal time (slower anchor)
        Policy C: sign of ret_60m at signal time (slower still)

    For each policy, count same-session direction sign changes (flips) and compute
    per-pattern WR + EV.

Decision rule:
    Ship the slower anchor if its WR >= ret_session WR within +/-2pp AND it
    produces >= 30% fewer same-session flips.

Rules applied:
    Rule 14: ret_30m / ret_60m / ret_session stored as percentage points - divide
             by 100 before treating as decimal. Sign convention used directly here.
    Rule 15: Supabase pagination max page_size=1000.
    Rule 16: hist_spot_bars_5m bar_ts uses replace(tzinfo=None) - not used here
             since we read hist_pattern_signals.

Output:
    Prints a Compendium-shaped block to stdout. No DB writes.

Author: Session 15 batch.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, date

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000  # Rule 15
START_DATE = "2025-04-01"
END_DATE = "2026-04-30"


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def discover_columns(sb, table: str) -> list[str]:
    """One-shot column discovery via a LIMIT 1 query."""
    try:
        r = sb.table(table).select("*").limit(1).execute()
        if r.data:
            return list(r.data[0].keys())
    except Exception as e:
        print(f"[WARN] could not discover columns for {table}: {e}", file=sys.stderr)
    return []


def fetch_pattern_signals(sb, start_date: str, end_date: str) -> list[dict]:
    """Page through hist_pattern_signals between dates. Rule 15 compliant."""
    rows: list[dict] = []
    offset = 0
    # Try common ts column names; the row dict will tell us which is real.
    ts_col_candidates = ["signal_ts", "ts", "entry_ts", "detected_ts", "bar_ts"]
    cols = discover_columns(sb, "hist_pattern_signals")
    ts_col = next((c for c in ts_col_candidates if c in cols), None)
    if ts_col is None:
        print(f"[FATAL] no recognisable ts column in hist_pattern_signals. cols={cols}",
              file=sys.stderr)
        sys.exit(2)
    print(f"[INFO] using ts column: {ts_col}")

    while True:
        q = (
            sb.table("hist_pattern_signals")
            .select("*")
            .gte(ts_col, f"{start_date}T00:00:00+00:00")
            .lte(ts_col, f"{end_date}T23:59:59+00:00")
            .order(ts_col)
            .range(offset, offset + PAGE_SIZE - 1)
        )
        r = q.execute()
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 200_000:
            print(f"[WARN] safety break at offset {offset}", file=sys.stderr)
            break
    return rows, ts_col


def sign(x):
    if x is None:
        return 0
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def policy_direction(row: dict, anchor: str) -> int:
    """Returns +1/-1/0 for the direction implied by the chosen anchor.
    Rule 14: values are percentage points; sign is what matters here so no /100 needed."""
    v = row.get(anchor)
    return sign(v)


def pattern_intent(row: dict) -> int:
    """+1 if pattern is bull-side, -1 if bear-side, 0 if unknown."""
    ptype = (row.get("pattern_type") or "").upper()
    if "BULL" in ptype or ptype in ("JUDAS_BULL", "BOS_BULL"):
        return +1
    if "BEAR" in ptype or ptype in ("JUDAS_BEAR", "BOS_BEAR"):
        return -1
    return 0


def is_win(row: dict) -> bool | None:
    """Compute win/loss using ret_30m sign vs pattern intent.
    Rule 14: ret_30m is percentage points - sign comparison only, no division needed.
    Returns None if outcome can't be determined."""
    ret30 = row.get("ret_30m")
    if ret30 is None:
        return None
    intent = pattern_intent(row)
    if intent == 0:
        return None
    if intent > 0:
        return ret30 > 0
    return ret30 < 0


def to_session_key(ts_value, symbol: str) -> tuple[str, str]:
    """Group rows into (symbol, session_date) buckets."""
    if isinstance(ts_value, str):
        # Strip trailing Z / offset; we only need the date portion.
        try:
            dt = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.fromisoformat(ts_value[:19])
    elif isinstance(ts_value, datetime):
        dt = ts_value
    else:
        return (symbol, "UNKNOWN")
    return (symbol, dt.date().isoformat())


def main():
    sb = get_client()
    print(f"[INFO] Exp 47 — fetching pattern signals {START_DATE} .. {END_DATE}")
    rows, ts_col = fetch_pattern_signals(sb, START_DATE, END_DATE)
    print(f"[INFO] fetched {len(rows)} pattern signal rows")

    if not rows:
        print("[FATAL] no rows returned. Aborting.")
        sys.exit(1)

    # Ensure required columns exist on first row
    sample = rows[0]
    needed = ["symbol", "pattern_type", "ret_30m"]
    missing = [c for c in needed if c not in sample]
    if missing:
        print(f"[FATAL] hist_pattern_signals missing columns: {missing}")
        print(f"[INFO] available columns: {sorted(sample.keys())}")
        sys.exit(2)

    has_ret_session = "ret_session" in sample
    has_ret_60m = "ret_60m" in sample
    print(f"[INFO] anchor availability: ret_session={has_ret_session} "
          f"ret_30m=True ret_60m={has_ret_60m}")

    policies = [("ret_30m", "ret_30m")]
    if has_ret_session:
        policies.insert(0, ("ret_session", "ret_session"))
    if has_ret_60m:
        policies.append(("ret_60m", "ret_60m"))

    # === Per-policy: count flips per session ===
    # For each (symbol, session_date), walk rows in ts order and count direction sign changes.
    session_rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        sym = r.get("symbol", "UNKNOWN")
        sk = to_session_key(r.get(ts_col), sym)
        session_rows[sk].append(r)

    flips_per_policy = defaultdict(int)
    sessions_per_policy = defaultdict(int)
    for sk, rs in session_rows.items():
        rs.sort(key=lambda x: x.get(ts_col) or "")
        for label, anchor in policies:
            sessions_per_policy[label] += 1
            prev = 0
            for r in rs:
                d = policy_direction(r, anchor)
                if d == 0:
                    continue
                if prev != 0 and d != prev:
                    flips_per_policy[label] += 1
                prev = d

    # === Per-policy WR + EV per pattern ===
    # WR = pattern intent direction matches ret_30m sign (Rule 14 sign only)
    # We're really asking: when the policy says "go long here", how often was that right?
    # Approach: filter rows where policy_direction == pattern_intent (i.e. the policy
    # would have allowed the trade). Compute WR/EV among those rows.
    per_policy_per_pattern = defaultdict(lambda: defaultdict(lambda: {"n": 0, "wins": 0, "sum_ret": 0.0}))
    for r in rows:
        intent = pattern_intent(r)
        if intent == 0:
            continue
        win = is_win(r)
        if win is None:
            continue
        ret30 = r.get("ret_30m") or 0.0  # percentage points
        # signed return aligned with intent
        signed_ret = ret30 if intent > 0 else -ret30
        ptype = r.get("pattern_type") or "UNKNOWN"
        for label, anchor in policies:
            d = policy_direction(r, anchor)
            if d != intent:
                continue  # this policy would have blocked the trade
            bucket = per_policy_per_pattern[label][ptype]
            bucket["n"] += 1
            bucket["wins"] += 1 if win else 0
            bucket["sum_ret"] += signed_ret

    # === Print ===
    print()
    print("=" * 76)
    print("EXPERIMENT 47 — DIRECTION STABILITY VIA SLOWER ANCHOR")
    print("=" * 76)
    print(f"Window: {START_DATE} .. {END_DATE}")
    print(f"Total rows: {len(rows)}, Sessions: {len(session_rows)}")
    print()
    print("--- Same-session flip count per policy ---")
    print(f"{'Policy':<14} {'Total flips':>13} {'Sessions':>10} {'Flips/session':>15}")
    baseline_flips = None
    for label, _ in policies:
        f = flips_per_policy[label]
        s = sessions_per_policy[label]
        rate = f / s if s else 0
        marker = ""
        if label == "ret_session":
            baseline_flips = f
            marker = "  <- baseline"
        elif baseline_flips is not None:
            reduction = (baseline_flips - f) / baseline_flips * 100 if baseline_flips else 0
            marker = f"  ({reduction:+.1f}% vs baseline)"
        print(f"{label:<14} {f:>13} {s:>10} {rate:>15.3f}{marker}")
    print()

    print("--- Per-pattern WR + EV per policy (only rows where policy direction matches pattern intent) ---")
    print(f"{'Policy':<14} {'Pattern':<14} {'N':>6} {'WR':>7} {'EV (pp)':>9} {'Total (pp)':>11}")
    pattern_keys = sorted({p for inner in per_policy_per_pattern.values() for p in inner})
    for label, _ in policies:
        for p in pattern_keys:
            b = per_policy_per_pattern[label][p]
            if b["n"] == 0:
                continue
            wr = b["wins"] / b["n"] * 100
            ev = b["sum_ret"] / b["n"]
            print(f"{label:<14} {p:<14} {b['n']:>6} {wr:>6.1f}% {ev:>9.3f} {b['sum_ret']:>11.2f}")
        print()

    print("=" * 76)
    print("DECISION RULE:")
    print("  PASS = slower anchor (ret_30m / ret_60m) achieves WR >= ret_session WR")
    print("         within +/-2pp AND >= 30% flip reduction")
    print("  Apply this manually to the table above; no auto-verdict here.")
    print("=" * 76)


if __name__ == "__main__":
    main()
