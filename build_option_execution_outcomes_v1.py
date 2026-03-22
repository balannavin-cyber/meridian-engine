from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# ============================================================================
# MERDIAN - Build Option Execution Outcomes V1
# ----------------------------------------------------------------------------
# Purpose:
#   Evaluate BUY_CE / BUY_PE signals using:
#     - signal_snapshots
#     - option_execution_snapshots
#     - option_execution_price_history
#
# Writes to:
#   public.option_execution_outcomes_v1
#
# Notes:
#   - This version evaluates actionable option entries only: BUY_CE, BUY_PE
#   - DO_NOTHING rows are skipped in this version
#   - Uses nearest available option price at/after each target horizon
#   - Filters to signals that occur on or after the first live V2 option capture
# ============================================================================


if load_dotenv is not None:
    load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

REQUEST_TIMEOUT_SECONDS = 30
SIGNAL_LIMIT = 500


class ConfigError(RuntimeError):
    pass


class SupabaseError(RuntimeError):
    pass


@dataclass
class SignalRecord:
    signal_id: int
    symbol: str
    signal_ts: str
    signal_action: str
    entry_spot: Optional[float]


@dataclass
class ExecutionSnapshot:
    symbol: str
    signal_ts: str
    spot: Optional[float]
    ce_strike: Optional[float]
    pe_strike: Optional[float]


@dataclass
class PricePoint:
    ts: str
    ltp: float
    spot: Optional[float]
    expiry_date: Optional[str]


def require_env(name: str, value: str) -> str:
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def print_header() -> None:
    print("=" * 72)
    print("MERDIAN - Build Option Execution Outcomes V1")
    print("=" * 72)


def parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def supabase_get(table: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.get(
        url,
        headers=get_supabase_headers(),
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise SupabaseError(
            f"GET {table} failed | status={response.status_code} | body={response.text}"
        )
    data = response.json()
    if not isinstance(data, list):
        raise SupabaseError(f"GET {table} returned unexpected payload: {data}")
    return data


def supabase_post_upsert(table: str, rows: List[Dict[str, Any]], on_conflict: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = get_supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates"
    response = requests.post(
        url,
        headers=headers,
        params={"on_conflict": on_conflict},
        json=rows,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise SupabaseError(
            f"POST upsert {table} failed | status={response.status_code} | body={response.text}"
        )


def infer_signal_action(row: Dict[str, Any]) -> Optional[str]:
    for key in ("signal_action", "action", "trade_action", "shadow_action"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def infer_signal_spot(row: Dict[str, Any]) -> Optional[float]:
    for key in ("spot_price", "spot", "entry_spot"):
        value = parse_float(row.get(key))
        if value is not None:
            return value
    return None


def infer_signal_ts(row: Dict[str, Any]) -> Optional[str]:
    for key in ("signal_ts", "ts", "created_at"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def fetch_first_v2_ts() -> Optional[str]:
    rows = supabase_get(
        "option_execution_price_history",
        {
            "select": "ts",
            "source": "eq.dhan_execution_capture_v2",
            "order": "ts.asc",
            "limit": "1",
        },
    )
    if not rows:
        return None
    ts = rows[0].get("ts")
    return str(ts) if ts else None


def fetch_actionable_signals(first_v2_ts: str) -> List[SignalRecord]:
    rows = supabase_get(
        "signal_snapshots",
        {
            "select": "*",
            "ts": f"gte.{first_v2_ts}",
            "order": "ts.desc",
            "limit": str(SIGNAL_LIMIT),
        },
    )

    signals: List[SignalRecord] = []
    for row in rows:
        signal_id = row.get("id")
        symbol = row.get("symbol")
        signal_ts = infer_signal_ts(row)
        signal_action = infer_signal_action(row)
        entry_spot = infer_signal_spot(row)

        if signal_id is None or not symbol or not signal_ts or not signal_action:
            continue

        if signal_action not in ("BUY_CE", "BUY_PE"):
            continue

        if parse_dt(signal_ts) < parse_dt(first_v2_ts):
            continue

        signals.append(
            SignalRecord(
                signal_id=int(signal_id),
                symbol=str(symbol),
                signal_ts=str(signal_ts),
                signal_action=signal_action,
                entry_spot=entry_spot,
            )
        )

    print(f"[INFO] First V2 option capture ts: {first_v2_ts}")
    print(f"[INFO] Eligible BUY_CE/BUY_PE signals since V2 start: {len(signals)}")
    return signals


def fetch_execution_snapshot(symbol: str, signal_ts: str) -> Optional[ExecutionSnapshot]:
    rows = supabase_get(
        "option_execution_snapshots",
        {
            "select": "symbol,signal_ts,spot,ce_strike,pe_strike",
            "symbol": f"eq.{symbol}",
            "signal_ts": f"eq.{signal_ts}",
            "limit": "1",
        },
    )

    if not rows:
        return None

    row = rows[0]
    return ExecutionSnapshot(
        symbol=str(row["symbol"]),
        signal_ts=str(row["signal_ts"]),
        spot=parse_float(row.get("spot")),
        ce_strike=parse_float(row.get("ce_strike")),
        pe_strike=parse_float(row.get("pe_strike")),
    )


def fetch_price_series(
    symbol: str,
    option_type: str,
    strike: float,
    signal_ts: str,
) -> List[PricePoint]:
    signal_dt = parse_dt(signal_ts)
    end_dt = signal_dt + timedelta(minutes=60)

    rows = supabase_get(
        "option_execution_price_history",
        {
            "select": "ts,ltp,spot,expiry_date",
            "symbol": f"eq.{symbol}",
            "option_type": f"eq.{option_type}",
            "strike": f"eq.{strike}",
            "source": "eq.dhan_execution_capture_v2",
            "ts": f"gte.{signal_dt.isoformat()}",
            "order": "ts.asc",
            "limit": "5000",
        },
    )

    series: List[PricePoint] = []
    for row in rows:
        ts = row.get("ts")
        ltp = parse_float(row.get("ltp"))
        if not ts or ltp is None:
            continue

        ts_dt = parse_dt(str(ts))
        if ts_dt > end_dt:
            continue

        series.append(
            PricePoint(
                ts=str(ts),
                ltp=ltp,
                spot=parse_float(row.get("spot")),
                expiry_date=row.get("expiry_date"),
            )
        )

    return series


def first_point_at_or_after(series: List[PricePoint], target_dt: datetime) -> Optional[PricePoint]:
    for point in series:
        if parse_dt(point.ts) >= target_dt:
            return point
    return None


def compute_time_to_first_profit(series: List[PricePoint], entry_ltp: float, signal_dt: datetime) -> Optional[float]:
    for point in series[1:]:
        if point.ltp > entry_ltp:
            delta = parse_dt(point.ts) - signal_dt
            return delta.total_seconds() / 60.0
    return None


def build_outcome_row(signal: SignalRecord, snap: ExecutionSnapshot, series: List[PricePoint]) -> Optional[Dict[str, Any]]:
    if not series:
        return None

    signal_dt = parse_dt(signal.signal_ts)

    entry_point = series[0]
    entry_ltp = entry_point.ltp

    horizon_15 = first_point_at_or_after(series, signal_dt + timedelta(minutes=15))
    horizon_30 = first_point_at_or_after(series, signal_dt + timedelta(minutes=30))
    horizon_60 = first_point_at_or_after(series, signal_dt + timedelta(minutes=60))

    max_ltp = max(p.ltp for p in series)
    min_ltp = min(p.ltp for p in series)

    entry_option_type = "CE" if signal.signal_action == "BUY_CE" else "PE"
    entry_strike = snap.ce_strike if entry_option_type == "CE" else snap.pe_strike
    entry_expiry_date = entry_point.expiry_date

    move_15 = (horizon_15.ltp - entry_ltp) if horizon_15 else None
    move_30 = (horizon_30.ltp - entry_ltp) if horizon_30 else None
    move_60 = (horizon_60.ltp - entry_ltp) if horizon_60 else None

    move_15_pct = ((move_15 / entry_ltp) * 100.0) if move_15 is not None and entry_ltp else None
    move_30_pct = ((move_30 / entry_ltp) * 100.0) if move_30 is not None and entry_ltp else None
    move_60_pct = ((move_60 / entry_ltp) * 100.0) if move_60 is not None and entry_ltp else None

    time_to_first_profit = compute_time_to_first_profit(series, entry_ltp, signal_dt)

    row = {
        "signal_id": signal.signal_id,
        "symbol": signal.symbol,
        "signal_ts": signal.signal_ts,
        "signal_action": signal.signal_action,
        "entry_spot": signal.entry_spot if signal.entry_spot is not None else snap.spot,
        "entry_option_type": entry_option_type,
        "entry_strike": entry_strike,
        "entry_expiry_date": entry_expiry_date,
        "entry_option_ltp": entry_ltp,
        "outcome_15m_ltp": horizon_15.ltp if horizon_15 else None,
        "outcome_30m_ltp": horizon_30.ltp if horizon_30 else None,
        "outcome_60m_ltp": horizon_60.ltp if horizon_60 else None,
        "move_15m": move_15,
        "move_30m": move_30,
        "move_60m": move_60,
        "move_15m_pct": move_15_pct,
        "move_30m_pct": move_30_pct,
        "move_60m_pct": move_60_pct,
        "max_ltp_60m": max_ltp,
        "min_ltp_60m": min_ltp,
        "mfe_60m": max_ltp - entry_ltp,
        "mae_60m": min_ltp - entry_ltp,
        "time_to_first_profit_min": time_to_first_profit,
        "source": "build_option_execution_outcomes_v1",
        "raw": {
            "series_points": len(series),
            "entry_ts": entry_point.ts,
            "horizon_15_ts": horizon_15.ts if horizon_15 else None,
            "horizon_30_ts": horizon_30.ts if horizon_30 else None,
            "horizon_60_ts": horizon_60.ts if horizon_60 else None,
        },
    }
    return row


def main() -> int:
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)

    first_v2_ts = fetch_first_v2_ts()
    if not first_v2_ts:
        print("[DONE] No V2 option execution history exists yet.")
        return 0

    signals = fetch_actionable_signals(first_v2_ts)

    output_rows: List[Dict[str, Any]] = []
    skipped_no_snap = 0
    skipped_no_series = 0

    for signal in signals:
        snap = fetch_execution_snapshot(signal.symbol, signal.signal_ts)
        if snap is None:
            skipped_no_snap += 1
            continue

        option_type = "CE" if signal.signal_action == "BUY_CE" else "PE"
        strike = snap.ce_strike if option_type == "CE" else snap.pe_strike

        if strike is None:
            skipped_no_series += 1
            continue

        series = fetch_price_series(
            signal.symbol,
            option_type,
            strike,
            signal.signal_ts,
        )

        row = build_outcome_row(signal, snap, series)
        if row is None:
            skipped_no_series += 1
            continue

        output_rows.append(row)
        print(
            f"[ROW] signal_id={signal.signal_id} | symbol={signal.symbol} | "
            f"action={signal.signal_action} | strike={strike} | points={len(series)}"
        )

    print(f"[INFO] Outcome rows built: {len(output_rows)}")
    print(f"[INFO] Skipped - no execution snapshot: {skipped_no_snap}")
    print(f"[INFO] Skipped - no price series: {skipped_no_series}")

    if output_rows:
        supabase_post_upsert(
            "option_execution_outcomes_v1",
            output_rows,
            on_conflict="signal_id",
        )
        print(f"[DONE] Rows upserted: {len(output_rows)}")
    else:
        print("[DONE] No eligible post-V2 actionable signals to upsert yet.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise