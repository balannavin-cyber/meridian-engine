from __future__ import annotations

"""
backfill_basis_context.py  --  ENH-07 (B) historical cohort

Builds a historical basis-velocity cohort into hist_basis_context from the
1-minute bar tables, matching the LIVE compute_basis_context_local.py
taxonomy + deadbands so the two cohorts are label-comparable.

    python3 backfill_basis_context.py <from_date> <to_date> [--symbol NIFTY|SENSEX]
                                      [--window-min 15] [--dry-run] [--force]

Source-data facts established at S61 (gate queries) — see TD-S61-NEW-2:
  * hist_future_bars_1m.bar_ts is IST-CLOCK MISLABELED AS UTC (hours 9-15).
    hist_spot_bars_1m.bar_ts is TRUE UTC (hours 3-10). They are 5h30m apart.
    -> futures bar_ts is shifted -5h30m to true UTC BEFORE pairing.
  * front-month is per-symbol: NIFTY = contract_series 1 (expiry_date NULL),
    SENSEX = contract_series 0 (expiry_date populated). NIFTY has no expiry
    to verify "1 = nearest", so a liquidity preflight asserts series-1 is the
    most-traded series on sampled dates (fail loud unless --force).
  * joinable window is futures-bound (~2025-04-01 .. 2026-03-30); spot runs
    later but there is a ~3-month futures hole (Apr-Jun 2026) that live now
    fills forward.

1-min cadence (every paired minute), 15-min window. Velocity only within a
trade_date (no cross-session pairing). Read-only on source tables; writes
only hist_basis_context. ENH-72 ExecutionLog with valid exit_reason enums.
"""

import argparse
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from core.execution_log import ExecutionLog

UTC = timezone.utc
IST_SHIFT = timedelta(0)   # S61: hist_future_bars_1m AND hist_spot_bars_1m BOTH store
#                            IST-clock-as-UTC (verified: same HH band on the same
#                            trade_date). They are mutually consistent, so pairing
#                            uses raw bar_ts with NO shift. (Both differ from the
#                            true-UTC live index_futures_snapshots by +5h30m, which is
#                            irrelevant here since hist never crosses live.)
#                            See TD-S61-NEW-2 (corrected).

FRONT_SERIES = {"NIFTY": 1, "SENSEX": 0}
SYMBOLS = ["NIFTY", "SENSEX"]

WINDOW_MIN_DEFAULT = int(float(os.getenv("MERDIAN_BASIS_VELOCITY_WINDOW_MIN", "15")))
SPOT_DEADBAND_PCT = float(os.getenv("MERDIAN_BASIS_SPOT_DEADBAND_PCT", "0.0002"))
VEL_DEADBAND_PP = float(os.getenv("MERDIAN_BASIS_VEL_DEADBAND_PP", "0.005"))
LIQUIDITY_SAMPLE_DATES = 10


# ── helpers ──────────────────────────────────────────────────────────────
def to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        r = float(v)
        return None if (math.isnan(r) or math.isinf(r)) else r
    except Exception:
        return None


def parse_ts(v: Any) -> Optional[datetime]:
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


def get_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val


def sb_config(prefer: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
    url = get_env("SUPABASE_URL").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY fallback).")
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if prefer:
        h["Prefer"] = prefer
    return url, h


def sb_select(table: str, params: Dict[str, str], timeout: int = 90) -> List[Dict[str, Any]]:
    base, headers = sb_config(prefer="return=representation")
    resp = requests.get(f"{base}/rest/v1/{table}?{urlencode(params)}", headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"SELECT {table} {resp.status_code}: {resp.text}")
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"SELECT {table} unexpected type {type(data)}")
    return data


def sb_select_paged(table: str, params: Dict[str, str], page: int = 1000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    offset = 0
    while True:
        p = dict(params, limit=str(page), offset=str(offset))
        batch = sb_select(table, p)
        out.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return out


def sb_upsert(table: str, rows: List[Dict[str, Any]], on_conflict: str, timeout: int = 90) -> int:
    if not rows:
        return 0
    base, headers = sb_config(prefer="resolution=merge-duplicates,return=minimal")
    resp = requests.post(f"{base}/rest/v1/{table}?on_conflict={on_conflict}", headers=headers, json=rows, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"UPSERT {table} {resp.status_code}: {resp.text}")
    return len(rows)


def classify(spot_delta: Optional[float], vel_pp: Optional[float], spot_now: Optional[float]) -> Optional[str]:
    if spot_delta is None or vel_pp is None or spot_now is None:
        return None
    eps = abs(spot_now) * SPOT_DEADBAND_PCT
    up, dn = spot_delta > eps, spot_delta < -eps
    exp, shr = vel_pp > VEL_DEADBAND_PP, vel_pp < -VEL_DEADBAND_PP
    if (not up and not dn) or (not exp and not shr):
        return "NEUTRAL"
    if up and exp:
        return "LONG_BUILD"
    if up and shr:
        return "WEAK_LONG"
    if dn and shr:
        return "SHORT_BUILD"
    if dn and exp:
        return "WEAK_SHORT"
    return "NEUTRAL"


# ── source access ────────────────────────────────────────────────────────
def resolve_instruments() -> Dict[str, str]:
    rows = sb_select("instruments", {"select": "id,symbol"})
    m = {r["symbol"]: r["id"] for r in rows if r.get("symbol") in SYMBOLS}
    missing = [s for s in SYMBOLS if s not in m]
    if missing:
        raise RuntimeError(f"instruments missing symbols: {missing}")
    return m


def trade_dates(iid: str, series: int, d0: str, d1: str) -> List[str]:
    rows = sb_select_paged("hist_future_bars_1m", {
        "select": "trade_date",
        "instrument_id": f"eq.{iid}",
        "contract_series": f"eq.{series}",
        "and": f"(trade_date.gte.{d0},trade_date.lte.{d1})",
        "order": "trade_date.asc",
    })
    return sorted({r["trade_date"] for r in rows if r.get("trade_date")})


def liquidity_preflight(symbol: str, iid: str, dates: List[str], force: bool) -> None:
    """NIFTY has no expiry to confirm series-1=nearest; assert it is the most
    traded series on a sample of dates. SENSEX has only series 0 -> trivial."""
    if symbol != "NIFTY":
        return
    if not dates:
        return
    step = max(1, len(dates) // LIQUIDITY_SAMPLE_DATES)
    sample = dates[::step][:LIQUIDITY_SAMPLE_DATES]
    violations = []
    for d in sample:
        rows = sb_select_paged("hist_future_bars_1m", {
            "select": "contract_series,volume",
            "instrument_id": f"eq.{iid}",
            "trade_date": f"eq.{d}",
        })
        vol = defaultdict(float)
        for r in rows:
            vol[r.get("contract_series")] += (to_float(r.get("volume")) or 0.0)
        if not vol:
            continue
        argmax = max(vol, key=vol.get)
        if argmax != FRONT_SERIES["NIFTY"]:
            violations.append((d, argmax, dict(vol)))
    if violations:
        msg = (f"LIQUIDITY GUARD FAILED for NIFTY on {len(violations)} sampled date(s): "
               f"series-{FRONT_SERIES['NIFTY']} was NOT the most-traded. Examples: {violations[:3]}")
        if not force:
            raise RuntimeError(msg + "  (re-run with --force to override after manual review)")
        print(f"[WARN] {msg}  -- proceeding due to --force")
    else:
        print(f"[OK] liquidity guard passed for NIFTY on {len(sample)} sampled dates "
              f"(series-{FRONT_SERIES['NIFTY']} is most-traded).")


def fetch_day_futures(iid: str, series: int, d: str) -> List[Dict[str, Any]]:
    return sb_select_paged("hist_future_bars_1m", {
        "select": "bar_ts,close,volume,oi,contract_series,expiry_date,is_pre_market",
        "instrument_id": f"eq.{iid}",
        "contract_series": f"eq.{series}",
        "trade_date": f"eq.{d}",
        "order": "bar_ts.asc",
    })


def fetch_day_spot(iid: str, d: str) -> Dict[datetime, float]:
    rows = sb_select_paged("hist_spot_bars_1m", {
        "select": "bar_ts,close,is_pre_market",
        "instrument_id": f"eq.{iid}",
        "trade_date": f"eq.{d}",
        "order": "bar_ts.asc",
    })
    out: Dict[datetime, float] = {}
    for r in rows:
        ts = parse_ts(r.get("bar_ts"))
        c = to_float(r.get("close"))
        if ts is not None and c is not None:
            out[ts] = c
    return out


# ── per-day compute ──────────────────────────────────────────────────────
def compute_day(symbol: str, series: int, d: str, fut_rows: List[Dict[str, Any]],
                spot_by_ts: Dict[datetime, float], window_min: int) -> List[Dict[str, Any]]:
    # build true-UTC basis series for the day
    basis_pct_by_ts: Dict[datetime, float] = {}
    spot_at_ts: Dict[datetime, float] = {}
    basis_at_ts: Dict[datetime, float] = {}
    expiry_by_ts: Dict[datetime, Any] = {}
    for r in fut_rows:
        raw_ts = parse_ts(r.get("bar_ts"))
        if raw_ts is None:
            continue
        true_ts = raw_ts - IST_SHIFT            # IST-mislabel correction
        fclose = to_float(r.get("close"))
        spot = spot_by_ts.get(true_ts)
        if fclose is None or spot is None or spot == 0:
            continue
        basis = fclose - spot
        basis_pct_by_ts[true_ts] = basis / spot * 100.0
        spot_at_ts[true_ts] = spot
        basis_at_ts[true_ts] = basis
        expiry_by_ts[true_ts] = r.get("expiry_date")

    win = timedelta(minutes=window_min)
    rows_out: List[Dict[str, Any]] = []
    for ts in sorted(basis_pct_by_ts.keys()):
        prev_ts = ts - win
        basis_pct_now = basis_pct_by_ts[ts]
        spot_now = spot_at_ts[ts]
        vel = spot_delta = basis_pct_prev = None
        win_actual = None
        if prev_ts in basis_pct_by_ts:          # same-day, exact minute
            basis_pct_prev = basis_pct_by_ts[prev_ts]
            vel = basis_pct_now - basis_pct_prev
            spot_delta = spot_now - spot_at_ts[prev_ts]
            win_actual = window_min
        label = classify(spot_delta, vel, spot_now)
        rows_out.append({
            "ts": ts.isoformat(),
            "symbol": symbol,
            "contract_series": series,
            "expiry_date": expiry_by_ts.get(ts),
            "basis": round(basis_at_ts[ts], 6),
            "basis_pct_now": round(basis_pct_now, 6),
            "basis_pct_prev": round(basis_pct_prev, 6) if basis_pct_prev is not None else None,
            "basis_velocity_pp": round(vel, 6) if vel is not None else None,
            "window_min": win_actual,
            "spot_now": round(spot_now, 6),
            "spot_delta": round(spot_delta, 6) if spot_delta is not None else None,
            "context_label": label,
            "source": "hist_backfill",
        })
    return rows_out


# ── main ─────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("from_date")
    ap.add_argument("to_date")
    ap.add_argument("--symbol", choices=SYMBOLS, default=None)
    ap.add_argument("--window-min", type=int, default=WINDOW_MIN_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    targets = [args.symbol] if args.symbol else SYMBOLS

    log = ExecutionLog(
        script_name="backfill_basis_context.py",
        expected_writes={"hist_basis_context": 1},
        symbol=args.symbol,
        notes=f"hist basis backfill {args.from_date}..{args.to_date} win={args.window_min} "
              f"symbols={'+'.join(targets)}{' DRY' if args.dry_run else ''}",
    )

    try:
        iids = resolve_instruments()
    except Exception as e:
        return log.exit_with_reason("DEPENDENCY_MISSING", exit_code=1, error_message=str(e))

    grand_total = 0
    per_symbol_written: Dict[str, int] = {}

    for symbol in targets:
        iid = iids[symbol]
        series = FRONT_SERIES[symbol]
        print(f"================ {symbol} (series {series}) ================")
        try:
            dates = trade_dates(iid, series, args.from_date, args.to_date)
        except Exception as e:
            return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                        error_message=f"{symbol} trade_dates failed: {e}")
        if not dates:
            print(f"  no futures trade_dates in range for {symbol}; skipping.")
            per_symbol_written[symbol] = 0
            continue
        print(f"  {len(dates)} trade dates ({dates[0]} .. {dates[-1]})")

        try:
            liquidity_preflight(symbol, iid, dates, args.force)
        except Exception as e:
            return log.exit_with_reason("DATA_ERROR", exit_code=1, error_message=str(e))

        written = 0
        for d in dates:
            try:
                fut = fetch_day_futures(iid, series, d)
                spot = fetch_day_spot(iid, d)
            except Exception as e:
                print(f"  [ERR] fetch {symbol} {d}: {e}")
                continue
            if not fut or not spot:
                continue
            rows = compute_day(symbol, series, d, fut, spot, args.window_min)
            if not rows:
                continue
            if args.dry_run:
                written += len(rows)
                continue
            try:
                # batch within the day (already < ~400 rows)
                written += sb_upsert("hist_basis_context", rows, on_conflict="symbol,ts")
            except Exception as e:
                print(f"  [ERR] upsert {symbol} {d}: {e}")
                continue
        labelled_note = ""
        print(f"  {symbol}: {written} rows {'(dry-run)' if args.dry_run else 'written'}{labelled_note}")
        per_symbol_written[symbol] = written
        grand_total += written

    if grand_total == 0:
        return log.exit_with_reason("SKIPPED_NO_INPUT", exit_code=1,
                                    error_message=f"no rows produced; per_symbol={per_symbol_written}")

    if not args.dry_run:
        log.record_write("hist_basis_context", grand_total)
    note = " ".join(f"{s}={n}" for s, n in per_symbol_written.items())
    print(f"DONE. total={grand_total} ({note})")
    return log.complete(notes=f"{note} total={grand_total}{' DRY' if args.dry_run else ''}")


if __name__ == "__main__":
    sys.exit(main())
