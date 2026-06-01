"""backfill_s41_p0a_columns_30d.py

S41 P0.a -- Historical backfill for gamma_metrics.{vix, max_gamma_strike,
pin_risk_score} columns. Reconstructs values for rows written before the
S41 P0.a writer deploy (2026-05-30).

Three phases (independent unless --phase is set):
  A. max_gamma_strike  -- argmax(positive gex_cr) per (symbol, ts) cycle,
                          read from gex_strike_snapshots, UPDATE gamma_metrics.
  B. vix               -- POST /v2/charts/intraday for INDIA VIX (security_id=21,
                          exchange_segment=IDX_I, instrument=INDEX, interval=5);
                          UPDATE gamma_metrics by 5-min bar window.
  C. pin_risk_score    -- recompute the FIX-1 additive-weighted formula against
                          each gamma_metrics row, using the just-backfilled
                          max_gamma_strike + 5-cycle lookback. UPDATE gamma_metrics.

Phase A is a prerequisite for Phase C (Phase C reads max_gamma_strike).
Phase B is independent. Default --phase ALL runs A -> B -> C.

Window:
  Phase A and Phase C are limited to the window where gex_strike_snapshots
  has data (writer shipped 2026-05-25 / S37). Phase B can cover the full
  --days window (default 30) via Dhan historical fetch.

Conventions:
  - Reads .env from the script's directory (same pattern as
    compute_gamma_metrics_local.py and capture_market_spot_snapshot.py).
  - Uses supabase-py table API for UPDATEs (PATCH-on-(symbol,ts) filter).
  - Reuses the FIX-1 pin_risk_score formula -- duplicated here intentionally
    so this backfill is a standalone artifact, not coupled to live writer
    refactors. If the writer formula evolves, this script must be updated
    in lockstep OR ADR-016 calibration via merdian_parameters takes over.
  - Dry-run by default; pass --apply to issue UPDATEs.

Usage:
  python backfill_s41_p0a_columns_30d.py                       # dry-run all 3 phases, 30 days
  python backfill_s41_p0a_columns_30d.py --apply               # execute all 3 phases
  python backfill_s41_p0a_columns_30d.py --apply --phase A     # max_gamma_strike only
  python backfill_s41_p0a_columns_30d.py --apply --phase B     # VIX only
  python backfill_s41_p0a_columns_30d.py --apply --phase C     # pin_risk_score only
  python backfill_s41_p0a_columns_30d.py --apply --days 7      # narrower window
  python backfill_s41_p0a_columns_30d.py --apply --symbol NIFTY  # one symbol only

Run from C:\\GammaEnginePython\\ on Local (same dir as compute_gamma_metrics_local.py).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import load_dotenv
from supabase import Client, create_client


# =====================================================================
# Config / env
# =====================================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "").strip()
DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN", "").strip()

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise SystemExit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from environment")

SUPABASE: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

DHAN_INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"
INDIA_VIX_SECURITY_ID = "21"
INDIA_VIX_SEGMENT = "IDX_I"

IST = timezone(timedelta(hours=5, minutes=30))


# =====================================================================
# Pin Risk Score formula (duplicated from compute_gamma_metrics_local.py
# post-FIX-1; keep these two in lockstep until ADR-016 calibration
# moves weights to merdian_parameters)
# =====================================================================

def compute_pin_risk_score_backfill(
    gamma_concentration: float | None,
    expansion_probability: float | None,
    spot: float,
    max_gamma_strike: float | None,
    strike_step: float | None,
    recent_max_strikes: list[float],
) -> float | None:
    """FIX-1 additive-weighted Pin Risk Score, 0-100. See compute_pin_risk_score
    in compute_gamma_metrics_local.py for full doctrine."""
    if gamma_concentration is None or expansion_probability is None:
        return None
    spot_proximity_factor: float | None = None
    if max_gamma_strike is not None and strike_step is not None and strike_step > 0 and spot > 0:
        spot_proximity_factor = max(0.0, 1.0 - (abs(spot - max_gamma_strike) / strike_step) / 3.0)
    sustained_time_factor: float | None = None
    if max_gamma_strike is not None and strike_step is not None and len(recent_max_strikes) >= 3:
        within_one_strike = sum(1 for s in recent_max_strikes if abs(s - max_gamma_strike) <= strike_step)
        sustained_time_factor = within_one_strike / len(recent_max_strikes)
    expansion_complement = 1.0 - (float(expansion_probability) / 100.0)
    components: list[tuple[float, float]] = []
    components.append((0.30, float(gamma_concentration)))
    if spot_proximity_factor is not None:
        components.append((0.30, spot_proximity_factor))
    if sustained_time_factor is not None:
        components.append((0.20, sustained_time_factor))
    components.append((0.20, expansion_complement))
    weight_total = sum(w for w, _ in components)
    if weight_total <= 0:
        return None
    score_01 = sum(w * v for w, v in components) / weight_total
    return round(max(0.0, min(100.0, 100.0 * score_01)), 2)


# =====================================================================
# Supabase helpers
# =====================================================================

def _rows(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    data = getattr(result, "data", None)
    return data if isinstance(data, list) else []


def paginated_select(table: str, columns: str, filters: list, page_size: int = 1000) -> list[dict[str, Any]]:
    """Paginated SELECT respecting Supabase 1000-row cap (Rule 15 / CLAUDE.md)."""
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        q = SUPABASE.table(table).select(columns)
        for f in filters:
            q = f(q)
        batch = _rows(q.order("ts", desc=False).range(offset, offset + page_size - 1).execute())
        if not batch:
            break
        out.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return out


def to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def parse_ts(s: str) -> datetime:
    """Normalize Supabase ts string to UTC datetime, handling variable microsecond precision (TD-NEW-13)."""
    import re
    t = s.replace("Z", "+00:00")
    m = re.match(r"^(.+)\.(\d+)(\+\d{2}:\d{2}|\-\d{2}:\d{2})$", t)
    if m:
        base, frac, tz = m.groups()
        frac = (frac + "000000")[:6]
        t = f"{base}.{frac}{tz}"
    return datetime.fromisoformat(t).astimezone(timezone.utc)


# =====================================================================
# Phase A -- max_gamma_strike backfill
# =====================================================================

def phase_a_max_gamma_strike(
    window_start: datetime,
    symbols: list[str],
    apply: bool,
) -> dict[tuple[str, str], float]:
    """Backfill gamma_metrics.max_gamma_strike from gex_strike_snapshots.

    Reads positive-GEX rows from gex_strike_snapshots in window, groups by
    (symbol, ts), picks argmax(gex_cr) per group (pin candidate convention,
    FIX-1 aligned). Returns per-cycle pin strikes for downstream Phase C.
    """
    print("=" * 72)
    print("PHASE A -- max_gamma_strike backfill")
    print("=" * 72)
    window_start_iso = window_start.isoformat()
    print(f"Reading gex_strike_snapshots: ts >= {window_start_iso}, gex_cr > 0, symbol in {symbols}")

    gss_rows: list[dict[str, Any]] = []
    for sym in symbols:
        rows = paginated_select(
            "gex_strike_snapshots",
            "symbol,ts,strike,gex_cr",
            [
                lambda q, s=sym: q.eq("symbol", s),
                lambda q, w=window_start_iso: q.gte("ts", w),
                lambda q: q.gt("gex_cr", 0),
            ],
        )
        gss_rows.extend(rows)
        print(f"  {sym}: {len(rows)} positive-GEX rows fetched")

    per_cycle: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in gss_rows:
        key = (str(r.get("symbol")), str(r.get("ts")))
        per_cycle[key].append(r)

    pin_strikes: dict[tuple[str, str], float] = {}
    for key, rows_in_cycle in per_cycle.items():
        top = max(rows_in_cycle, key=lambda r: to_float(r.get("gex_cr")))
        s = to_float(top.get("strike"))
        if s > 0:
            pin_strikes[key] = s

    print(f"Computed pin strikes for {len(pin_strikes)} (symbol, ts) cycles")

    if not apply:
        print(f"[DRY-RUN] Would UPDATE {len(pin_strikes)} gamma_metrics rows with max_gamma_strike")
        sample = list(pin_strikes.items())[:5]
        for (sym, ts), strike in sample:
            print(f"  {sym} {ts} -> max_gamma_strike={strike}")
        return pin_strikes

    updates = 0
    errors = 0
    for (sym, ts), strike in pin_strikes.items():
        try:
            res = (
                SUPABASE.table("gamma_metrics")
                .update({"max_gamma_strike": strike})
                .eq("symbol", sym)
                .eq("ts", ts)
                .execute()
            )
            if _rows(res):
                updates += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [ERROR] {sym} {ts}: {e}")
        if updates and updates % 200 == 0:
            print(f"  Progress: {updates} updates...")
    print(f"[APPLY] Phase A complete: {updates} rows updated, {errors} errors")
    return pin_strikes


# =====================================================================
# Phase B -- VIX backfill (Dhan v2/charts/intraday)
# =====================================================================

def phase_b_vix(
    window_start: datetime,
    window_end: datetime,
    apply: bool,
) -> int:
    """Backfill gamma_metrics.vix from Dhan v2/charts/intraday.

    INDIA VIX is index-wide -- the same bar value applies to all gamma_metrics
    rows (NIFTY + SENSEX) within that 5-min window.
    """
    print()
    print("=" * 72)
    print("PHASE B -- vix backfill")
    print("=" * 72)
    if not DHAN_API_TOKEN or not DHAN_CLIENT_ID:
        print("[SKIP] DHAN_API_TOKEN / DHAN_CLIENT_ID not set; cannot fetch historical VIX.")
        return 0

    # Dhan accepts "YYYY-MM-DD HH:MM:SS" in IST or "YYYY-MM-DD". Use IST date strings.
    from_str = window_start.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")
    to_str = window_end.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Fetching INDIA VIX intraday 5m: {from_str} -> {to_str}")

    payload = {
        "securityId": INDIA_VIX_SECURITY_ID,
        "exchangeSegment": INDIA_VIX_SEGMENT,
        "instrument": "INDEX",
        "interval": "5",
        "oi": False,
        "fromDate": from_str,
        "toDate": to_str,
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_API_TOKEN,
        "client-id": DHAN_CLIENT_ID,
    }

    try:
        resp = requests.post(DHAN_INTRADAY_URL, headers=headers, json=payload, timeout=30)
    except Exception as e:
        print(f"[ERROR] Dhan request failed: {e}")
        return 0

    if resp.status_code != 200:
        print(f"[ERROR] Dhan HTTP {resp.status_code}: {resp.text[:500]}")
        return 0

    body = resp.json()
    timestamps = body.get("timestamp") or body.get("start_Time") or []
    closes = body.get("close") or []
    if not timestamps or not closes or len(timestamps) != len(closes):
        print(f"[ERROR] Unexpected Dhan response shape. Keys: {list(body.keys())}")
        print(f"  ts_len={len(timestamps)}, close_len={len(closes)}")
        return 0

    print(f"Dhan returned {len(timestamps)} VIX bars")

    # Build (bar_ts_utc, vix_close) pairs. Dhan timestamps are unix-epoch seconds (UTC).
    bars: list[tuple[datetime, float]] = []
    for ts_val, close_val in zip(timestamps, closes):
        try:
            bar_dt = datetime.fromtimestamp(int(ts_val), tz=timezone.utc)
            bars.append((bar_dt, float(close_val)))
        except Exception:
            continue
    bars.sort(key=lambda x: x[0])
    if not bars:
        print("[ERROR] No parseable VIX bars")
        return 0

    print(f"Parsed {len(bars)} VIX bars, range: {bars[0][0].isoformat()} -> {bars[-1][0].isoformat()}")
    print(f"VIX value range: min={min(b[1] for b in bars):.2f}, max={max(b[1] for b in bars):.2f}")

    if not apply:
        print(f"[DRY-RUN] Would UPDATE gamma_metrics.vix across ~{len(bars)} 5-min windows")
        print(f"  Sample bars (first 3):")
        for b in bars[:3]:
            print(f"    {b[0].isoformat()} -> vix={b[1]}")
        return 0

    # For each bar, UPDATE gamma_metrics rows in [bar_ts, bar_ts + 5min) regardless of symbol.
    updates = 0
    errors = 0
    for bar_ts, vix_val in bars:
        bar_start_iso = bar_ts.isoformat()
        bar_end_iso = (bar_ts + timedelta(minutes=5)).isoformat()
        try:
            res = (
                SUPABASE.table("gamma_metrics")
                .update({"vix": vix_val})
                .gte("ts", bar_start_iso)
                .lt("ts", bar_end_iso)
                .execute()
            )
            n = len(_rows(res))
            updates += n
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [ERROR] bar {bar_ts.isoformat()}: {e}")
        if updates and updates % 500 == 0:
            print(f"  Progress: {updates} rows updated across bars...")
    print(f"[APPLY] Phase B complete: {updates} gamma_metrics rows updated, {errors} bar errors")
    return updates


# =====================================================================
# Phase C -- pin_risk_score backfill
# =====================================================================

def phase_c_pin_risk_score(
    window_start: datetime,
    symbols: list[str],
    pin_strikes: dict[tuple[str, str], float] | None,
    apply: bool,
) -> int:
    """Recompute pin_risk_score for historical gamma_metrics rows using FIX-1
    formula. Requires Phase A to have populated max_gamma_strike (or to be
    running in same invocation with --phase ALL)."""
    print()
    print("=" * 72)
    print("PHASE C -- pin_risk_score backfill")
    print("=" * 72)
    window_start_iso = window_start.isoformat()
    print(f"Reading gamma_metrics rows: ts >= {window_start_iso}, symbol in {symbols}")

    gm_rows: list[dict[str, Any]] = []
    for sym in symbols:
        rows = paginated_select(
            "gamma_metrics",
            "symbol,ts,spot,gamma_concentration,expansion_probability,max_gamma_strike",
            [
                lambda q, s=sym: q.eq("symbol", s),
                lambda q, w=window_start_iso: q.gte("ts", w),
            ],
        )
        gm_rows.extend(rows)
        print(f"  {sym}: {len(rows)} gamma_metrics rows")

    # If Phase A wasn't run this invocation, fetch pin_strikes from
    # gex_strike_snapshots so Phase C is standalone-capable.
    if pin_strikes is None:
        print("Phase A not in scope; deriving pin_strikes from gex_strike_snapshots...")
        gss_rows: list[dict[str, Any]] = []
        for sym in symbols:
            rows = paginated_select(
                "gex_strike_snapshots",
                "symbol,ts,strike,gex_cr",
                [
                    lambda q, s=sym: q.eq("symbol", s),
                    lambda q, w=window_start_iso: q.gte("ts", w),
                    lambda q: q.gt("gex_cr", 0),
                ],
            )
            gss_rows.extend(rows)
        per_cycle: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for r in gss_rows:
            per_cycle[(str(r.get("symbol")), str(r.get("ts")))].append(r)
        pin_strikes = {}
        for key, rs in per_cycle.items():
            top = max(rs, key=lambda r: to_float(r.get("gex_cr")))
            s = to_float(top.get("strike"))
            if s > 0:
                pin_strikes[key] = s
        print(f"  derived {len(pin_strikes)} pin strikes")

    # Need strike_step per (symbol, ts). Compute from gex_strike_snapshots
    # by loading ALL strikes (not just positive) and taking min positive diff.
    print("Computing strike_step per cycle from gex_strike_snapshots...")
    strike_step_cache: dict[tuple[str, str], float] = {}
    for sym in symbols:
        rows = paginated_select(
            "gex_strike_snapshots",
            "symbol,ts,strike",
            [
                lambda q, s=sym: q.eq("symbol", s),
                lambda q, w=window_start_iso: q.gte("ts", w),
            ],
        )
        by_cycle: dict[tuple[str, str], list[float]] = defaultdict(list)
        for r in rows:
            by_cycle[(str(r.get("symbol")), str(r.get("ts")))].append(to_float(r.get("strike")))
        for key, strikes in by_cycle.items():
            strikes_sorted = sorted(set(s for s in strikes if s > 0))
            if len(strikes_sorted) < 2:
                continue
            diffs = [strikes_sorted[i] - strikes_sorted[i - 1] for i in range(1, len(strikes_sorted))]
            diffs = [d for d in diffs if d > 0]
            if diffs:
                strike_step_cache[key] = min(diffs)
        print(f"  {sym}: strike_step inferred for {sum(1 for k in strike_step_cache if k[0] == sym)} cycles")

    # Build per-symbol sorted ts list for lookback.
    ts_by_symbol: dict[str, list[str]] = defaultdict(list)
    for (sym, ts) in pin_strikes.keys():
        ts_by_symbol[sym].append(ts)
    for sym in ts_by_symbol:
        ts_by_symbol[sym].sort()

    print(f"Recomputing pin_risk_score for {len(gm_rows)} gamma_metrics rows...")
    updates_planned = 0
    updates_applied = 0
    errors = 0
    sample_logged = 0

    for row in gm_rows:
        sym = str(row.get("symbol"))
        ts = str(row.get("ts"))
        gc = row.get("gamma_concentration")
        ep = row.get("expansion_probability")
        spot = to_float(row.get("spot"))
        # Use Phase A's pin_strikes value if available; falls back to row's
        # max_gamma_strike if Phase A wasn't run.
        mgs = pin_strikes.get((sym, ts), row.get("max_gamma_strike"))
        if mgs is not None:
            mgs = to_float(mgs)
        ss = strike_step_cache.get((sym, ts))

        # 5-cycle lookback over prior ts values for this symbol.
        sym_ts_list = ts_by_symbol.get(sym, [])
        prior_ts = [t for t in sym_ts_list if t < ts][-5:]
        recent_max_strikes = [pin_strikes[(sym, t)] for t in prior_ts if (sym, t) in pin_strikes]

        new_score = compute_pin_risk_score_backfill(
            gamma_concentration=gc,
            expansion_probability=ep,
            spot=spot,
            max_gamma_strike=mgs,
            strike_step=ss,
            recent_max_strikes=recent_max_strikes,
        )

        if new_score is None:
            continue
        updates_planned += 1

        if sample_logged < 5 and not apply:
            print(f"  sample: {sym} {ts} -> pin_risk_score={new_score} "
                  f"(mgs={mgs}, ss={ss}, sustained_n={len(recent_max_strikes)})")
            sample_logged += 1

        if apply:
            try:
                res = (
                    SUPABASE.table("gamma_metrics")
                    .update({"pin_risk_score": new_score})
                    .eq("symbol", sym)
                    .eq("ts", ts)
                    .execute()
                )
                if _rows(res):
                    updates_applied += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  [ERROR] {sym} {ts}: {e}")
            if updates_applied and updates_applied % 200 == 0:
                print(f"  Progress: {updates_applied}/{updates_planned} applied...")

    if apply:
        print(f"[APPLY] Phase C complete: {updates_applied} rows updated, {errors} errors")
    else:
        print(f"[DRY-RUN] Would UPDATE {updates_planned} gamma_metrics rows with pin_risk_score")
    return updates_planned if not apply else updates_applied


# =====================================================================
# Window auto-detection (for Phases A + C: gex_strike_snapshots floor)
# =====================================================================

def detect_gss_window_floor() -> datetime | None:
    """Find earliest gex_strike_snapshots ts; cap Phase A/C floor there."""
    try:
        res = SUPABASE.table("gex_strike_snapshots").select("ts").order("ts", desc=False).limit(1).execute()
        rows = _rows(res)
        if not rows:
            return None
        return parse_ts(str(rows[0]["ts"]))
    except Exception as e:
        print(f"[WARN] gex_strike_snapshots floor detection failed: {e}")
        return None


# =====================================================================
# Main
# =====================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="S41 P0.a 30-day backfill")
    parser.add_argument("--apply", action="store_true", help="Actually write UPDATEs (default: dry-run)")
    parser.add_argument("--phase", choices=["A", "B", "C", "ALL"], default="ALL")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days (default 30)")
    parser.add_argument("--symbol", choices=["NIFTY", "SENSEX", "BOTH"], default="BOTH")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    window_start_30d = now - timedelta(days=args.days)
    symbols = ["NIFTY", "SENSEX"] if args.symbol == "BOTH" else [args.symbol]

    print(f"Backfill window (Phase B / full): {window_start_30d.isoformat()} -> {now.isoformat()}")
    print(f"Symbols: {symbols}")
    print(f"Phase: {args.phase}")
    print(f"Apply mode: {args.apply}")
    print()

    # Phase A + C window: gex_strike_snapshots floor
    gss_floor = detect_gss_window_floor()
    if gss_floor:
        ac_window_start = max(window_start_30d, gss_floor)
        print(f"gex_strike_snapshots earliest ts: {gss_floor.isoformat()}")
        print(f"Phase A/C effective window: {ac_window_start.isoformat()} -> {now.isoformat()}")
    else:
        ac_window_start = window_start_30d
        print("gex_strike_snapshots empty or unreadable; Phase A/C may produce 0 updates")
    print()

    pin_strikes: dict[tuple[str, str], float] | None = None

    t0 = time.time()
    if args.phase in ("A", "ALL"):
        pin_strikes = phase_a_max_gamma_strike(ac_window_start, symbols, apply=args.apply)
    if args.phase in ("B", "ALL"):
        phase_b_vix(window_start_30d, now, apply=args.apply)
    if args.phase in ("C", "ALL"):
        phase_c_pin_risk_score(ac_window_start, symbols, pin_strikes, apply=args.apply)

    print()
    print(f"Total runtime: {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
