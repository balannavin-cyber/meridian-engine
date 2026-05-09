"""
ENH-93 Replay Harness — Chain Reconstructor.

Purpose:
  Reconstruct option_chain_snapshots_replay + market_spot_snapshots_replay
  for one replay date by reading hist_option_bars_1m + hist_spot_bars_1m,
  computing IV via inverse Black-Scholes Newton-Raphson, and writing rows
  in the same schema as the live tables.

Inputs:
  - replay_date (CLI arg, YYYY-MM-DD)
  - .env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

Outputs:
  - Rows in market_spot_snapshots_replay (one per 5-min boundary per symbol)
  - Rows in option_chain_snapshots_replay (one per boundary x symbol x strike x CE/PE)
  - Returns dict {boundary_ts_iso: {symbol: run_id_uuid_str}} for orchestrator

Live impact: ZERO writes to live. Reads live `option_chain_snapshots` for OI lift 
(see TD-094) and `instruments` for symbol metadata. Reads hist_* for OHLC.

Author: Session 23 + Session 24 (2026-05-08/09)
"""
from __future__ import annotations

import math
import os
import sys
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import requests
from dotenv import load_dotenv

from replay.replay_clock import IST, UTC, parse_replay_ts


RISK_FREE_RATE = 0.065
IV_CONVERGENCE_TOL = 0.001
IV_MAX_ITERATIONS = 100
IV_LOWER_BOUND = 0.001
IV_UPPER_BOUND = 10.0

BOUNDARY_START_IST = dt_time(9, 15)
BOUNDARY_END_IST = dt_time(15, 30)
BOUNDARY_INTERVAL_MIN = 5

UPSERT_BATCH_SIZE = 500


def _load_env() -> Tuple[str, str]:
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=base_dir / ".env")
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url:
        raise RuntimeError("SUPABASE_URL missing from .env")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing from .env")
    return url.rstrip("/"), key


def _sb_headers(key: str) -> Dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _sb_get(url: str, key: str, path: str, params: str = "") -> List[Dict[str, Any]]:
    full = f"{url}/rest/v1/{path}{'?' + params if params else ''}"
    resp = requests.get(full, headers=_sb_headers(key), timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"GET {path} failed {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _sb_insert_batch(url: str, key: str, table: str, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    full = f"{url}/rest/v1/{table}"
    headers = {**_sb_headers(key), "Prefer": "return=minimal"}
    inserted = 0
    for i in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[i:i + UPSERT_BATCH_SIZE]
        resp = requests.post(full, headers=headers, json=batch, timeout=60)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"INSERT {table} failed {resp.status_code}: {resp.text[:300]}")
        inserted += len(batch)
    return inserted


def _norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _bs_price(spot: float, strike: float, t_years: float, r: float, sigma: float, opt: str) -> float:
    if t_years <= 1e-6 or sigma <= 1e-6:
        return max(spot - strike, 0) if opt == "CE" else max(strike - spot, 0)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t_years) / (sigma * math.sqrt(t_years))
    d2 = d1 - sigma * math.sqrt(t_years)
    if opt == "CE":
        return spot * _norm_cdf(d1) - strike * math.exp(-r * t_years) * _norm_cdf(d2)
    return strike * math.exp(-r * t_years) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def _bs_gamma(spot: float, strike: float, t_years: float, r: float, sigma: float) -> float:
    if t_years <= 1e-6 or sigma <= 1e-6 or spot <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t_years) / (sigma * math.sqrt(t_years))
    return _norm_pdf(d1) / (spot * sigma * math.sqrt(t_years))


def _implied_vol(spot: float, strike: float, t_years: float, r: float, price: float, opt: str) -> Optional[float]:
    if t_years <= 1e-6 or price <= 0:
        return None
    intrinsic = max(spot - strike, 0) if opt == "CE" else max(strike - spot, 0)
    if price <= intrinsic + 0.01:
        return None
    lo, hi = IV_LOWER_BOUND, IV_UPPER_BOUND
    for _ in range(IV_MAX_ITERATIONS):
        mid = (lo + hi) / 2
        p = _bs_price(spot, strike, t_years, r, mid, opt)
        if abs(p - price) < IV_CONVERGENCE_TOL:
            return mid
        if p < price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _get_instrument(url: str, key: str, symbol: str) -> Dict[str, Any]:
    rows = _sb_get(url, key, "instruments", f"symbol=eq.{symbol}&select=id,symbol,strike_step,weekly_expiry_dow")
    if not rows:
        raise RuntimeError(f"No instrument row for symbol={symbol}")
    return rows[0]


def _resolve_active_expiry(replay_date: date, weekly_expiry_dow: int) -> date:
    """
    Nearest weekly expiry >= replay_date.

    instruments.weekly_expiry_dow uses Postgres ISODOW convention (Mon=1..Sun=7):
      NIFTY=2 = Tuesday
      SENSEX=4 = Thursday

    Python's date.weekday() uses Mon=0..Sun=6, so we convert with -1.
    """
    target_python_weekday = (weekly_expiry_dow - 1) % 7
    days_ahead = (target_python_weekday - replay_date.weekday()) % 7
    return replay_date + timedelta(days=days_ahead)


def _check_replay_tables_empty(url: str, key: str, replay_date: date) -> None:
    """Idempotency guard. Refuse to write if rows already exist for replay_date."""
    date_str = replay_date.isoformat()
    spot_rows = _sb_get(
        url, key, "market_spot_snapshots_replay",
        f"ts=gte.{date_str}T00:00:00Z&ts=lte.{date_str}T23:59:59Z&select=id&limit=1"
    )
    if spot_rows:
        raise RuntimeError(
            f"market_spot_snapshots_replay already has rows for {replay_date}. "
            f"TRUNCATE the _replay tables before re-running."
        )
    chain_rows = _sb_get(
        url, key, "option_chain_snapshots_replay",
        f"ts=gte.{date_str}T00:00:00Z&ts=lte.{date_str}T23:59:59Z&select=id&limit=1"
    )
    if chain_rows:
        raise RuntimeError(
            f"option_chain_snapshots_replay already has rows for {replay_date}. "
            f"TRUNCATE the _replay tables before re-running."
        )


def _generate_boundaries(replay_date: date) -> List[datetime]:
    """5-min boundaries from 09:15 IST through 15:30 IST inclusive, in UTC."""
    boundaries = []
    current_ist = datetime.combine(replay_date, BOUNDARY_START_IST, tzinfo=IST)
    end_ist = datetime.combine(replay_date, BOUNDARY_END_IST, tzinfo=IST)
    while current_ist <= end_ist:
        boundaries.append(current_ist.astimezone(UTC))
        current_ist += timedelta(minutes=BOUNDARY_INTERVAL_MIN)
    return boundaries


def _parse_pg_timestamp(ts_str: str) -> Optional[datetime]:
    """
    Parse a PostgREST timestamp string into a UTC-aware datetime.

    PostgREST returns 'timestamp with time zone' in formats like:
      '2026-05-07 03:35:00+00'        (space separator, +00 short offset)
      '2026-05-07T03:35:00+00:00'     (T separator, full offset)
      '2026-05-07T03:35:00Z'          (Z suffix)

    All three normalize to a single UTC datetime.
    """
    if not ts_str:
        return None
    s = ts_str.strip().replace("Z", "+00:00").replace(" ", "T")
    if len(s) >= 3 and s[-3] in "+-" and ":" not in s[-3:]:
        s = s + ":00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def _fetch_hist_spot_bars(url: str, key: str, instrument_id: str, replay_date: date) -> Dict[datetime, float]:
    """Returns {bar_ts_utc_datetime: close_price}. Paginated by 1000."""
    out: Dict[datetime, float] = {}
    offset = 0
    while True:
        rows = _sb_get(
            url, key, "hist_spot_bars_1m",
            f"instrument_id=eq.{instrument_id}&trade_date=eq.{replay_date}"
            f"&select=bar_ts,close&limit=1000&offset={offset}"
        )
        for r in rows:
            ts = _parse_pg_timestamp(r["bar_ts"])
            if ts is not None:
                out[ts] = float(r["close"])
        if len(rows) < 1000:
            break
        offset += 1000
    return out


def _fetch_hist_option_bars(url: str, key: str, instrument_id: str, replay_date: date, expiry_date: date) -> List[Dict[str, Any]]:
    """All option bars for one instrument, one trade_date, one expiry. Paginated.
    Each row gets a parsed `bar_ts_dt` field added for fast datetime-keyed lookup.

    KNOWN DATA DEFECT (TD-087, related to TD-084):
    hist_option_bars_1m.bar_ts stores IST clock values with a UTC timezone tag.
    A bar at 09:15 IST market open is stored as '2026-05-07 09:15:00+00' instead
    of the correct '2026-05-07 03:45:00+00'. We compensate by subtracting 5h30m
    from each parsed timestamp to recover the true UTC instant.

    DO NOT apply this adjustment to hist_spot_bars_1m — that table stores correct UTC.
    """
    IST_OFFSET = timedelta(hours=5, minutes=30)
    out: List[Dict[str, Any]] = []
    offset = 0
    while True:
        rows = _sb_get(
            url, key, "hist_option_bars_1m",
            f"instrument_id=eq.{instrument_id}&trade_date=eq.{replay_date}"
            f"&expiry_date=eq.{expiry_date.isoformat()}"
            f"&select=bar_ts,strike,option_type,close,oi,volume,iv"
            f"&limit=1000&offset={offset}"
        )
        for r in rows:
            parsed = _parse_pg_timestamp(r["bar_ts"])
            r["bar_ts_dt"] = (parsed - IST_OFFSET) if parsed is not None else None
        out.extend(rows)
        if len(rows) < 1000:
            break
        offset += 1000
    return out


def _fetch_live_oi_for_replay(
    url: str,
    key: str,
    symbol: str,
    replay_date: date,
    replay_boundaries: List[datetime],
    tolerance_seconds: int = 150,
) -> Dict[Any, float]:
    """
    Lift OI per (replay_boundary, strike, option_type) from live option_chain_snapshots.

    Architectural note (TD-094): hist_option_bars_1m.oi is 0 across all rows from S22
    Kite backfill — Kite historical_data API does not return OI for index option minute
    bars. To make replay produce meaningful gamma_metrics, we lift OI from live
    option_chain_snapshots for the same (symbol, replay_date). This is a READ from live,
    permitted because past option_chain_snapshots is immutable. Live tables are NEVER
    written by the replay harness.

    Match strategy: live ts is rarely exactly on the 5-min boundary (live ingest fires
    seconds after the boundary). For each replay boundary, find live rows within
    +/-tolerance_seconds and use the closest match per (strike, option_type).

    Returns: {(boundary_utc, strike, option_type): oi}
    """
    out: Dict[Any, float] = {}

    date_str = replay_date.isoformat()
    offset = 0
    page_size = 1000

    live_rows: List[Dict[str, Any]] = []
    while True:
        rows = _sb_get(
            url, key, "option_chain_snapshots",
            f"symbol=eq.{symbol}"
            f"&ts=gte.{date_str}T00:00:00Z"
            f"&ts=lte.{date_str}T23:59:59Z"
            f"&select=ts,strike,option_type,oi"
            f"&limit={page_size}&offset={offset}"
        )
        if not rows:
            break
        live_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size

    if not live_rows:
        print(f"  [{symbol}] WARNING: no live option_chain_snapshots for {replay_date}; OI will be 0")
        return out

    live_parsed: List[tuple] = []
    for r in live_rows:
        parsed = _parse_pg_timestamp(r["ts"])
        if parsed is None:
            continue
        strike = float(r["strike"])
        opt_type = str(r["option_type"]).upper()
        oi = float(r["oi"]) if r.get("oi") is not None else 0.0
        live_parsed.append((parsed, strike, opt_type, oi))

    if not live_parsed:
        return out

    tolerance = timedelta(seconds=tolerance_seconds)
    matched_boundaries = 0
    for boundary in replay_boundaries:
        in_window = [
            (lp_ts, lp_strike, lp_opt, lp_oi)
            for (lp_ts, lp_strike, lp_opt, lp_oi) in live_parsed
            if abs(lp_ts - boundary) <= tolerance
        ]
        if not in_window:
            continue

        per_key: Dict[tuple, tuple] = {}
        for (lp_ts, lp_strike, lp_opt, lp_oi) in in_window:
            delta = abs((lp_ts - boundary).total_seconds())
            key_pair = (lp_strike, lp_opt)
            if key_pair not in per_key or delta < per_key[key_pair][0]:
                per_key[key_pair] = (delta, lp_ts, lp_oi)

        for (lp_strike, lp_opt), (_, _, lp_oi) in per_key.items():
            out[(boundary, lp_strike, lp_opt)] = lp_oi

        matched_boundaries += 1

    print(f"  [{symbol}] live OI lift: {len(live_rows)} live rows -> {len(out)} (boundary,strike,type) entries across {matched_boundaries}/{len(replay_boundaries)} boundaries")
    return out


def _reconstruct_symbol(
    url: str,
    key: str,
    symbol: str,
    replay_date: date,
    boundaries: List[datetime],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
    """
    Returns:
      spot_rows: payloads for market_spot_snapshots_replay
      chain_rows: payloads for option_chain_snapshots_replay
      run_id_map: {boundary_ts_iso: run_id} for this symbol
    """
    instrument = _get_instrument(url, key, symbol)
    instrument_id = instrument["id"]
    weekly_expiry_dow = int(instrument["weekly_expiry_dow"])

    expiry_date = _resolve_active_expiry(replay_date, weekly_expiry_dow)
    print(f"  [{symbol}] instrument_id={instrument_id[:8]}... expiry={expiry_date} (dow={weekly_expiry_dow})")

    spot_map = _fetch_hist_spot_bars(url, key, instrument_id, replay_date)
    print(f"  [{symbol}] hist spot bars: {len(spot_map)}")

    if not spot_map:
        print(f"  [{symbol}] WARNING: no hist_spot_bars_1m for {replay_date}, skipping symbol")
        return [], [], {}

    option_bars = _fetch_hist_option_bars(url, key, instrument_id, replay_date, expiry_date)
    print(f"  [{symbol}] hist option bars: {len(option_bars)}")
    if not option_bars:
        print(f"  [{symbol}] WARNING: no hist_option_bars_1m for {replay_date}/{expiry_date}, skipping symbol")
        return [], [], {}

    # TD-094: lift OI from live option_chain_snapshots since hist OI is uniformly 0
    live_oi_lookup = _fetch_live_oi_for_replay(url, key, symbol, replay_date, boundaries)

    # Group option bars by parsed bar_ts datetime for fast boundary lookup
    bars_by_ts: Dict[datetime, List[Dict[str, Any]]] = {}
    for r in option_bars:
        ts_dt = r.get("bar_ts_dt")
        if ts_dt is not None:
            bars_by_ts.setdefault(ts_dt, []).append(r)

    spot_rows: List[Dict[str, Any]] = []
    chain_rows: List[Dict[str, Any]] = []
    run_id_map: Dict[str, str] = {}

    expiry_dt_utc = datetime.combine(expiry_date, dt_time(15, 30), tzinfo=IST).astimezone(UTC)

    boundaries_skipped = 0
    boundaries_emitted = 0

    for boundary_utc in boundaries:
        boundary_iso = boundary_utc.isoformat()

        # Direct datetime lookup — both maps keyed by parsed UTC datetime
        spot_close = spot_map.get(boundary_utc)
        if spot_close is None:
            boundaries_skipped += 1
            continue

        option_bars_at_boundary = bars_by_ts.get(boundary_utc, [])
        if not option_bars_at_boundary:
            boundaries_skipped += 1
            continue

        # Time to expiry in years (decimal)
        t_years = max((expiry_dt_utc - boundary_utc).total_seconds() / (365.25 * 24 * 3600), 1e-6)

        # Generate one run_id for this (symbol, boundary)
        run_id = str(uuid4())
        run_id_map[boundary_iso] = run_id

        # Spot snapshot row
        spot_rows.append({
            "ts": boundary_iso,
            "symbol": symbol,
            "spot": float(spot_close),
            "source_table": "replay",
            "source_id": f"hist_spot_bars_1m:{boundary_iso}",
            "raw": {
                "reconstructed_by": "replay_chain_reconstructor.py",
                "replay_date": replay_date.isoformat(),
                "boundary_iso": boundary_iso,
            },
        })

        # Option chain rows for this boundary
        for ob in option_bars_at_boundary:
            strike = float(ob["strike"])
            opt_type = str(ob["option_type"]).upper()
            close = float(ob["close"])
            # TD-094: use live OI lift; hist OI is 0 from S22 Kite backfill
            oi = live_oi_lookup.get((boundary_utc, strike, opt_type), 0.0)
            volume = float(ob["volume"]) if ob.get("volume") is not None else 0.0

            # Use stored IV if present and >0, else reconstruct
            stored_iv = ob.get("iv")
            if stored_iv is not None and float(stored_iv) > 0:
                iv = float(stored_iv)
            else:
                iv = _implied_vol(spot_close, strike, t_years, RISK_FREE_RATE, close, opt_type)

            # Compute gamma greek (needed by compute_gamma_metrics_local downstream)
            gamma = _bs_gamma(spot_close, strike, t_years, RISK_FREE_RATE, iv) if (iv and iv > 0) else None

            chain_rows.append({
                "ts": boundary_iso,
                "symbol": symbol,
                "expiry_date": expiry_date.isoformat(),
                "spot": float(spot_close),
                "strike": strike,
                "option_type": opt_type,
                "ltp": close,
                "bid": None,
                "ask": None,
                "oi": oi,
                "oi_change": None,
                "volume": volume,
                "iv": iv,
                "delta": None,
                "gamma": gamma,
                "theta": None,
                "vega": None,
                "raw": {
                    "reconstructed_by": "replay_chain_reconstructor.py",
                    "iv_source": "hist" if (stored_iv is not None and float(stored_iv) > 0) else "newton_raphson",
                    "oi_source": "live_option_chain_snapshots_lifted",
                    "replay_date": replay_date.isoformat(),
                },
                "run_id": run_id,
            })

        boundaries_emitted += 1

    print(f"  [{symbol}] boundaries: emitted={boundaries_emitted} skipped={boundaries_skipped}")
    print(f"  [{symbol}] rows: spot={len(spot_rows)} chain={len(chain_rows)}")

    return spot_rows, chain_rows, run_id_map


def reconstruct(replay_date: date) -> Dict[str, Dict[str, str]]:
    """Main entry point. Reconstructs spot + chain for replay_date for both symbols."""
    print("=" * 72)
    print(f"REPLAY CHAIN RECONSTRUCTOR — {replay_date}")
    print("=" * 72)

    url, key = _load_env()

    _check_replay_tables_empty(url, key, replay_date)

    boundaries = _generate_boundaries(replay_date)
    print(f"Boundaries (5-min, 09:15-15:30 IST): {len(boundaries)}")

    all_spot: List[Dict[str, Any]] = []
    all_chain: List[Dict[str, Any]] = []
    run_id_by_boundary: Dict[str, Dict[str, str]] = {}

    for symbol in ["NIFTY", "SENSEX"]:
        spot_rows, chain_rows, sym_run_id_map = _reconstruct_symbol(
            url, key, symbol, replay_date, boundaries
        )
        all_spot.extend(spot_rows)
        all_chain.extend(chain_rows)
        for boundary_iso, run_id in sym_run_id_map.items():
            run_id_by_boundary.setdefault(boundary_iso, {})[symbol] = run_id

    print("-" * 72)
    print(f"Total rows to write — spot: {len(all_spot)}, chain: {len(all_chain)}")

    spot_inserted = _sb_insert_batch(url, key, "market_spot_snapshots_replay", all_spot)
    print(f"Inserted into market_spot_snapshots_replay: {spot_inserted}")

    chain_inserted = _sb_insert_batch(url, key, "option_chain_snapshots_replay", all_chain)
    print(f"Inserted into option_chain_snapshots_replay: {chain_inserted}")

    print("-" * 72)
    print(f"Boundaries with both symbols populated: "
          f"{sum(1 for b in run_id_by_boundary.values() if len(b) == 2)}")
    print(f"Boundaries with only one symbol:        "
          f"{sum(1 for b in run_id_by_boundary.values() if len(b) == 1)}")
    print("RECONSTRUCTION COMPLETE")
    print("=" * 72)

    return run_id_by_boundary


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m replay.replay_chain_reconstructor YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        replay_date = date.fromisoformat(sys.argv[1])
    except ValueError as e:
        print(f"Invalid date: {e}", file=sys.stderr)
        return 2

    if replay_date >= datetime.now(IST).date():
        print(f"Refusing to reconstruct for date {replay_date}: must be in the past", file=sys.stderr)
        return 2

    try:
        run_id_map = reconstruct(replay_date)
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    print(f"\nRun ID map summary: {len(run_id_map)} boundaries, "
          f"first={list(run_id_map.keys())[0] if run_id_map else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())