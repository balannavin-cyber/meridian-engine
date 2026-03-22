from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# ============================================================================
# MERDIAN - Build Signal Regret Log V1
# ----------------------------------------------------------------------------
# Purpose:
#   Evaluate DO_NOTHING signals across spot, futures, and execution-style
#   option contracts (CE lower / PE higher).
#
# Reads from:
#   public.signal_snapshots
#   public.market_spot_snapshots
#   public.index_futures_snapshots
#   public.option_execution_price_history
#
# Writes to:
#   public.signal_regret_log_v1
#
# Notes:
#   - This version processes DO_NOTHING signals only.
#   - Uses nearest available point at or after each horizon target.
#   - Option logic uses asymmetric strike selection:
#       CE = closest lower strike
#       PE = next higher strike
#   - Option price history source is assumed to be
#       source = 'dhan_execution_capture_v2'
# ============================================================================


if load_dotenv is not None:
    load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

REQUEST_TIMEOUT_SECONDS = 30
SIGNAL_LIMIT = 500

STRIKE_STEP = {
    "NIFTY": 50,
    "SENSEX": 100,
}


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
    confidence_score: Optional[float]
    direction_bias: Optional[str]
    entry_spot: Optional[float]


@dataclass
class PricePoint:
    ts: str
    value: float


@dataclass
class OptionPoint:
    ts: str
    ltp: float
    expiry_date: Optional[str]


def require_env(name: str, value: str) -> str:
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def print_header() -> None:
    print("=" * 72)
    print("MERDIAN - Build Signal Regret Log V1")
    print("=" * 72)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pct_move(entry: Optional[float], later: Optional[float]) -> Optional[float]:
    if entry is None or later is None or entry == 0:
        return None
    return ((later - entry) / entry) * 100.0


def abs_move(entry: Optional[float], later: Optional[float]) -> Optional[float]:
    if entry is None or later is None:
        return None
    return later - entry


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


def fetch_do_nothing_signals() -> List[SignalRecord]:
    rows = supabase_get(
        "signal_snapshots",
        {
            "select": "id,symbol,ts,action,confidence_score,direction_bias,spot",
            "action": "eq.DO_NOTHING",
            "order": "ts.desc",
            "limit": str(SIGNAL_LIMIT),
        },
    )

    signals: List[SignalRecord] = []
    for row in rows:
        signal_id = row.get("id")
        symbol = row.get("symbol")
        signal_ts = row.get("ts")
        signal_action = row.get("action")

        if signal_id is None or not symbol or not signal_ts or not signal_action:
            continue

        signals.append(
            SignalRecord(
                signal_id=int(signal_id),
                symbol=str(symbol),
                signal_ts=str(signal_ts),
                signal_action=str(signal_action),
                confidence_score=parse_float(row.get("confidence_score")),
                direction_bias=(str(row.get("direction_bias")).strip().upper() if row.get("direction_bias") is not None else None),
                entry_spot=parse_float(row.get("spot")),
            )
        )

    print(f"[INFO] DO_NOTHING signals fetched: {len(signals)}")
    return signals


def first_point_at_or_after_price(series: List[PricePoint], target_dt: datetime) -> Optional[PricePoint]:
    for point in series:
        if parse_dt(point.ts) >= target_dt:
            return point
    return None


def first_point_at_or_after_option(series: List[OptionPoint], target_dt: datetime) -> Optional[OptionPoint]:
    for point in series:
        if parse_dt(point.ts) >= target_dt:
            return point
    return None


def fetch_spot_series(symbol: str, signal_ts: str) -> List[PricePoint]:
    signal_dt = parse_dt(signal_ts)
    end_dt = signal_dt + timedelta(minutes=60)

    rows = supabase_get(
        "market_spot_snapshots",
        {
            "select": "ts,spot",
            "symbol": f"eq.{symbol}",
            "ts": f"gte.{signal_dt.isoformat()}",
            "order": "ts.asc",
            "limit": "5000",
        },
    )

    series: List[PricePoint] = []
    for row in rows:
        ts = row.get("ts")
        spot = parse_float(row.get("spot"))
        if not ts or spot is None:
            continue
        if parse_dt(str(ts)) > end_dt:
            continue
        series.append(PricePoint(ts=str(ts), value=spot))

    return series


def fetch_futures_series(symbol: str, signal_ts: str) -> List[PricePoint]:
    signal_dt = parse_dt(signal_ts)
    end_dt = signal_dt + timedelta(minutes=60)

    rows = supabase_get(
        "index_futures_snapshots",
        {
            "select": "ts,futures_price",
            "symbol": f"eq.{symbol}",
            "ts": f"gte.{signal_dt.isoformat()}",
            "order": "ts.asc",
            "limit": "5000",
        },
    )

    series: List[PricePoint] = []
    for row in rows:
        ts = row.get("ts")
        px = parse_float(row.get("futures_price"))
        if not ts or px is None:
            continue
        if parse_dt(str(ts)) > end_dt:
            continue
        series.append(PricePoint(ts=str(ts), value=px))

    return series


def execution_strikes(symbol: str, spot: float) -> Tuple[float, float]:
    step = STRIKE_STEP[symbol]
    lower = math.floor(spot / step) * step
    upper = math.ceil(spot / step) * step
    return float(lower), float(upper)


def fetch_option_series(
    symbol: str,
    signal_ts: str,
    option_type: str,
    strike: float,
) -> List[OptionPoint]:
    signal_dt = parse_dt(signal_ts)
    end_dt = signal_dt + timedelta(minutes=60)

    rows = supabase_get(
        "option_execution_price_history",
        {
            "select": "ts,ltp,expiry_date",
            "symbol": f"eq.{symbol}",
            "option_type": f"eq.{option_type}",
            "strike": f"eq.{strike}",
            "source": "eq.dhan_execution_capture_v2",
            "ts": f"gte.{signal_dt.isoformat()}",
            "order": "ts.asc",
            "limit": "5000",
        },
    )

    series: List[OptionPoint] = []
    for row in rows:
        ts = row.get("ts")
        ltp = parse_float(row.get("ltp"))
        if not ts or ltp is None:
            continue
        if parse_dt(str(ts)) > end_dt:
            continue
        series.append(
            OptionPoint(
                ts=str(ts),
                ltp=ltp,
                expiry_date=(str(row.get("expiry_date")) if row.get("expiry_date") is not None else None),
            )
        )

    return series


def classify_regret(
    spot_move_pct: Optional[float],
    threshold_pct: float = 0.25,
) -> Optional[str]:
    if spot_move_pct is None:
        return None
    if spot_move_pct <= -threshold_pct:
        return "MISSED_BEARISH"
    if spot_move_pct >= threshold_pct:
        return "MISSED_BULLISH"
    return "JUSTIFIED_NO_TRADE"


def build_regret_row(signal: SignalRecord) -> Optional[Dict[str, Any]]:
    if signal.symbol not in STRIKE_STEP:
        return None

    signal_dt = parse_dt(signal.signal_ts)

    spot_series = fetch_spot_series(signal.symbol, signal.signal_ts)
    futures_series = fetch_futures_series(signal.symbol, signal.signal_ts)

    if not spot_series:
        return None

    spot_entry = spot_series[0]
    entry_spot = signal.entry_spot if signal.entry_spot is not None else spot_entry.value

    lower_strike, upper_strike = execution_strikes(signal.symbol, entry_spot)

    ce_series = fetch_option_series(signal.symbol, signal.signal_ts, "CE", lower_strike)
    pe_series = fetch_option_series(signal.symbol, signal.signal_ts, "PE", upper_strike)

    spot_15 = first_point_at_or_after_price(spot_series, signal_dt + timedelta(minutes=15))
    spot_30 = first_point_at_or_after_price(spot_series, signal_dt + timedelta(minutes=30))
    spot_60 = first_point_at_or_after_price(spot_series, signal_dt + timedelta(minutes=60))

    fut_entry = futures_series[0].value if futures_series else None
    fut_15 = first_point_at_or_after_price(futures_series, signal_dt + timedelta(minutes=15)) if futures_series else None
    fut_30 = first_point_at_or_after_price(futures_series, signal_dt + timedelta(minutes=30)) if futures_series else None
    fut_60 = first_point_at_or_after_price(futures_series, signal_dt + timedelta(minutes=60)) if futures_series else None

    ce_entry = ce_series[0] if ce_series else None
    ce_15 = first_point_at_or_after_option(ce_series, signal_dt + timedelta(minutes=15)) if ce_series else None
    ce_30 = first_point_at_or_after_option(ce_series, signal_dt + timedelta(minutes=30)) if ce_series else None
    ce_60 = first_point_at_or_after_option(ce_series, signal_dt + timedelta(minutes=60)) if ce_series else None

    pe_entry = pe_series[0] if pe_series else None
    pe_15 = first_point_at_or_after_option(pe_series, signal_dt + timedelta(minutes=15)) if pe_series else None
    pe_30 = first_point_at_or_after_option(pe_series, signal_dt + timedelta(minutes=30)) if pe_series else None
    pe_60 = first_point_at_or_after_option(pe_series, signal_dt + timedelta(minutes=60)) if pe_series else None

    spot_15_val = spot_15.value if spot_15 else None
    spot_30_val = spot_30.value if spot_30 else None
    spot_60_val = spot_60.value if spot_60 else None

    fut_15_val = fut_15.value if fut_15 else None
    fut_30_val = fut_30.value if fut_30 else None
    fut_60_val = fut_60.value if fut_60 else None

    ce_entry_ltp = ce_entry.ltp if ce_entry else None
    ce_15_ltp = ce_15.ltp if ce_15 else None
    ce_30_ltp = ce_30.ltp if ce_30 else None
    ce_60_ltp = ce_60.ltp if ce_60 else None

    pe_entry_ltp = pe_entry.ltp if pe_entry else None
    pe_15_ltp = pe_15.ltp if pe_15 else None
    pe_30_ltp = pe_30.ltp if pe_30 else None
    pe_60_ltp = pe_60.ltp if pe_60 else None

    spot_move_15 = abs_move(entry_spot, spot_15_val)
    spot_move_30 = abs_move(entry_spot, spot_30_val)
    spot_move_60 = abs_move(entry_spot, spot_60_val)

    spot_move_15_pct = pct_move(entry_spot, spot_15_val)
    spot_move_30_pct = pct_move(entry_spot, spot_30_val)
    spot_move_60_pct = pct_move(entry_spot, spot_60_val)

    futures_move_15 = abs_move(fut_entry, fut_15_val)
    futures_move_30 = abs_move(fut_entry, fut_30_val)
    futures_move_60 = abs_move(fut_entry, fut_60_val)

    futures_move_15_pct = pct_move(fut_entry, fut_15_val)
    futures_move_30_pct = pct_move(fut_entry, fut_30_val)
    futures_move_60_pct = pct_move(fut_entry, fut_60_val)

    ce_move_15 = abs_move(ce_entry_ltp, ce_15_ltp)
    ce_move_30 = abs_move(ce_entry_ltp, ce_30_ltp)
    ce_move_60 = abs_move(ce_entry_ltp, ce_60_ltp)

    ce_move_15_pct = pct_move(ce_entry_ltp, ce_15_ltp)
    ce_move_30_pct = pct_move(ce_entry_ltp, ce_30_ltp)
    ce_move_60_pct = pct_move(ce_entry_ltp, ce_60_ltp)

    pe_move_15 = abs_move(pe_entry_ltp, pe_15_ltp)
    pe_move_30 = abs_move(pe_entry_ltp, pe_30_ltp)
    pe_move_60 = abs_move(pe_entry_ltp, pe_60_ltp)

    pe_move_15_pct = pct_move(pe_entry_ltp, pe_15_ltp)
    pe_move_30_pct = pct_move(pe_entry_ltp, pe_30_ltp)
    pe_move_60_pct = pct_move(pe_entry_ltp, pe_60_ltp)

    row = {
        "signal_id": signal.signal_id,
        "symbol": signal.symbol,
        "signal_ts": signal.signal_ts,
        "signal_action": signal.signal_action,
        "confidence_score": signal.confidence_score,
        "direction_bias": signal.direction_bias,
        "entry_spot": entry_spot,
        "entry_futures": fut_entry,
        "ce_strike": lower_strike,
        "pe_strike": upper_strike,
        "ce_expiry_date": ce_entry.expiry_date if ce_entry else None,
        "pe_expiry_date": pe_entry.expiry_date if pe_entry else None,
        "spot_15m": spot_15_val,
        "spot_30m": spot_30_val,
        "spot_60m": spot_60_val,
        "futures_15m": fut_15_val,
        "futures_30m": fut_30_val,
        "futures_60m": fut_60_val,
        "ce_entry_ltp": ce_entry_ltp,
        "ce_15m_ltp": ce_15_ltp,
        "ce_30m_ltp": ce_30_ltp,
        "ce_60m_ltp": ce_60_ltp,
        "pe_entry_ltp": pe_entry_ltp,
        "pe_15m_ltp": pe_15_ltp,
        "pe_30m_ltp": pe_30_ltp,
        "pe_60m_ltp": pe_60_ltp,
        "spot_move_15m": spot_move_15,
        "spot_move_30m": spot_move_30,
        "spot_move_60m": spot_move_60,
        "spot_move_15m_pct": spot_move_15_pct,
        "spot_move_30m_pct": spot_move_30_pct,
        "spot_move_60m_pct": spot_move_60_pct,
        "futures_move_15m": futures_move_15,
        "futures_move_30m": futures_move_30,
        "futures_move_60m": futures_move_60,
        "futures_move_15m_pct": futures_move_15_pct,
        "futures_move_30m_pct": futures_move_30_pct,
        "futures_move_60m_pct": futures_move_60_pct,
        "ce_move_15m": ce_move_15,
        "ce_move_30m": ce_move_30,
        "ce_move_60m": ce_move_60,
        "ce_move_15m_pct": ce_move_15_pct,
        "ce_move_30m_pct": ce_move_30_pct,
        "ce_move_60m_pct": ce_move_60_pct,
        "pe_move_15m": pe_move_15,
        "pe_move_30m": pe_move_30,
        "pe_move_60m": pe_move_60,
        "pe_move_15m_pct": pe_move_15_pct,
        "pe_move_30m_pct": pe_move_30_pct,
        "pe_move_60m_pct": pe_move_60_pct,
        "regret_label_15m": classify_regret(spot_move_15_pct),
        "regret_label_30m": classify_regret(spot_move_30_pct),
        "regret_label_60m": classify_regret(spot_move_60_pct),
        "source": "build_signal_regret_log_v1",
        "raw": {
            "built_at_utc": now_utc_iso(),
            "spot_points": len(spot_series),
            "futures_points": len(futures_series),
            "ce_points": len(ce_series),
            "pe_points": len(pe_series),
            "ce_entry_ts": ce_entry.ts if ce_entry else None,
            "pe_entry_ts": pe_entry.ts if pe_entry else None,
            "spot_entry_ts": spot_entry.ts if spot_entry else None,
        },
    }

    return row


def main() -> int:
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)

    signals = fetch_do_nothing_signals()
    if not signals:
        print("[DONE] No DO_NOTHING signals found.")
        return 0

    output_rows: List[Dict[str, Any]] = []
    skipped = 0

    for signal in signals:
        row = build_regret_row(signal)
        if row is None:
            skipped += 1
            continue

        output_rows.append(row)
        print(
            f"[ROW] signal_id={signal.signal_id} | symbol={signal.symbol} | ts={signal.signal_ts}"
        )

    print(f"[INFO] Regret rows built: {len(output_rows)}")
    print(f"[INFO] Skipped: {skipped}")

    if not output_rows:
        print("[DONE] No regret rows to upsert.")
        return 0

    supabase_post_upsert(
        "signal_regret_log_v1",
        output_rows,
        on_conflict="signal_id",
    )

    print(f"[DONE] Rows upserted: {len(output_rows)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise