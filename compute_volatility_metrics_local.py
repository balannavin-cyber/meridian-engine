import sys
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pprint import pprint
from typing import Any, Dict, List, Optional, Tuple

from core.supabase_client import SupabaseClient
from fetch_india_vix import fetch_india_vix
from gamma_engine_retry_utils import retry_call


IST = timezone(timedelta(hours=5, minutes=30))


def parse_iso_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return None


def parse_iso_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def get_expiry_type(expiry_date: date, symbol: str) -> str:
    if symbol.upper() == "NIFTY":
        return "WEEKLY" if expiry_date.weekday() == 1 else "MONTHLY"
    if symbol.upper() == "SENSEX":
        return "WEEKLY" if expiry_date.weekday() == 3 else "MONTHLY"
    return "UNKNOWN"


def get_strike_step(symbol: str) -> int:
    if symbol.upper() == "NIFTY":
        return 50
    if symbol.upper() == "SENSEX":
        return 100
    raise RuntimeError(f"Unsupported symbol: {symbol}")


def find_atm_strike(spot: float, symbol: str) -> int:
    step = get_strike_step(symbol)
    return int(round(float(spot) / step) * step)


def find_row(rows: List[Dict[str, Any]], strike: int, option_type: str) -> Optional[Dict[str, Any]]:
    for row in rows:
        try:
            row_strike = int(float(row.get("strike")))
        except Exception:
            continue

        row_option_type = str(row.get("option_type", "")).upper()
        if row_strike == strike and row_option_type == option_type.upper():
            return row
    return None


def classify_vix_level_regime(vix_value: Optional[float]) -> Optional[str]:
    if vix_value is None:
        return None
    if vix_value < 12:
        return "LOW"
    if vix_value < 18:
        return "NORMAL"
    if vix_value < 25:
        return "HIGH"
    return "PANIC"


def classify_vix_level_bucket(vix_value: Optional[float]) -> Optional[str]:
    if vix_value is None:
        return None

    if vix_value < 11:
        return "UNDER_11"
    if vix_value < 12:
        return "11_12"
    if vix_value < 13:
        return "12_13"
    if vix_value < 14:
        return "13_14"
    if vix_value < 15:
        return "14_15"
    if vix_value < 16:
        return "15_16"
    if vix_value < 17:
        return "16_17"
    if vix_value < 18:
        return "17_18"
    if vix_value < 19:
        return "18_19"
    if vix_value < 20:
        return "19_20"
    return "20_PLUS"


def classify_percentile_regime(percentile: Optional[float]) -> Optional[str]:
    if percentile is None:
        return None
    if percentile < 20:
        return "VERY_LOW"
    if percentile < 40:
        return "LOW"
    if percentile < 60:
        return "NORMAL"
    if percentile < 80:
        return "HIGH"
    return "EXTREME"


def classify_context_regime(percentile: Optional[float]) -> Optional[str]:
    if percentile is None:
        return None
    if percentile >= 80:
        return "HIGH_CONTEXT"
    if percentile <= 20:
        return "LOW_CONTEXT"
    return "NORMAL_CONTEXT"


def classify_intraday_velocity(
    vix_change_5m: Optional[float],
    vix_change_15m: Optional[float],
    vix_change_30m: Optional[float],
    vix_pct_change_since_open: Optional[float],
) -> Optional[str]:
    anchor = (
        vix_change_30m
        if vix_change_30m is not None
        else vix_change_15m
        if vix_change_15m is not None
        else vix_change_5m
    )

    if anchor is None and vix_pct_change_since_open is None:
        return None

    if (anchor is not None and anchor >= 0.75) or (vix_pct_change_since_open is not None and vix_pct_change_since_open >= 6.0):
        return "VIX_RISING_FAST"
    if anchor is not None and anchor > 0:
        return "VIX_RISING_SLOW"
    if (anchor is not None and anchor <= -0.75) or (vix_pct_change_since_open is not None and vix_pct_change_since_open <= -6.0):
        return "VIX_FALLING_FAST"
    if anchor is not None and anchor < 0:
        return "VIX_FALLING_SLOW"
    return "VIX_FLAT"


def classify_interday_velocity(
    vix_change_1d: Optional[float],
    vix_change_3d: Optional[float],
    vix_change_5d: Optional[float],
) -> Optional[str]:
    anchor = (
        vix_change_3d
        if vix_change_3d is not None
        else vix_change_1d
        if vix_change_1d is not None
        else vix_change_5d
    )

    if anchor is None:
        return None

    if anchor >= 1.5:
        return "VIX_UPTREND"
    if anchor > 0:
        return "VIX_UP_BIAS"
    if anchor <= -1.5:
        return "VIX_DOWNTREND"
    if anchor < 0:
        return "VIX_DOWN_BIAS"
    return "VIX_FLAT"


def classify_vix_direction(
    vix_change_5m: Optional[float],
    vix_change_15m: Optional[float],
    vix_change_30m: Optional[float],
    vix_change_day: Optional[float],
) -> Optional[str]:
    anchor = (
        vix_change_15m
        if vix_change_15m is not None
        else vix_change_5m
        if vix_change_5m is not None
        else vix_change_30m
        if vix_change_30m is not None
        else vix_change_day
    )

    if anchor is None:
        return None
    if anchor > 0:
        return "UP"
    if anchor < 0:
        return "DOWN"
    return "FLAT"


def compute_vix_slope(
    vix_change_30m: Optional[float],
    vix_change_15m: Optional[float],
    vix_change_5m: Optional[float],
) -> Optional[float]:
    if vix_change_30m is not None:
        return vix_change_30m / 30.0
    if vix_change_15m is not None:
        return vix_change_15m / 15.0
    if vix_change_5m is not None:
        return vix_change_5m / 5.0
    return None


def extract_history_date(row: Dict[str, Any]) -> Optional[date]:
    for key in ["trade_date", "date", "dt", "as_of_date", "day"]:
        if key in row and row[key] is not None:
            d = parse_iso_date(row[key])
            if d is not None:
                return d
    return None


def extract_history_vix(row: Dict[str, Any]) -> Optional[float]:
    for key in ["india_vix", "vix_close", "vix_value", "close", "close_value", "value", "last", "vix"]:
        if key in row and row[key] is not None:
            v = safe_float(row[key])
            if v is not None:
                return v
    return None


def load_vix_history_rows(sb: SupabaseClient) -> List[Tuple[date, float]]:
    candidates = ["india_vix_daily", "india_vix_history", "vix_percentile_reference"]
    parsed: List[Tuple[date, float]] = []

    for table_name in candidates:
        try:
            rows = retry_call(
                lambda: sb.select(
                    table=table_name,
                    limit=5000,
                ),
                attempts=3,
                delay_seconds=2.0,
                backoff_multiplier=1.5,
                label=f"select {table_name}",
            )
        except Exception:
            continue

        temp: List[Tuple[date, float]] = []
        for row in rows or []:
            d = extract_history_date(row)
            v = extract_history_vix(row)
            if d is not None and v is not None:
                temp.append((d, v))

        if len(temp) > len(parsed):
            parsed = temp

    dedup: Dict[date, float] = {}
    for d, v in parsed:
        dedup[d] = v

    out = sorted(dedup.items(), key=lambda x: x[0])
    return out


def percentile_of_last(values: List[float], current_value: float) -> Optional[float]:
    if not values:
        return None
    le_count = sum(1 for x in values if x <= current_value)
    return (le_count / len(values)) * 100.0


def compute_vix_percentile(history_rows: List[Tuple[date, float]], trade_date: date, current_vix: float) -> Optional[float]:
    eligible = [(d, v) for d, v in history_rows if d <= trade_date]
    if not eligible:
        return None

    last_252 = eligible[-252:]
    vals = [v for _, v in last_252]

    if not last_252 or last_252[-1][0] != trade_date:
        vals = vals[-251:] + [current_vix]

    return percentile_of_last(vals, current_vix)


def nearest_prior_history_value(history_rows: List[Tuple[date, float]], target_date: date) -> Optional[float]:
    eligible = [v for d, v in history_rows if d <= target_date]
    if not eligible:
        return None
    return eligible[-1]


def fetch_recent_volatility_rows(sb: SupabaseClient, symbol: str) -> List[Dict[str, Any]]:
    rows = retry_call(
        lambda: sb.select(
            table="volatility_snapshots",
            filters={"symbol": f"eq.{symbol}"},
            order="ts.desc",
            limit=500,
        ),
        attempts=3,
        delay_seconds=2.0,
        backoff_multiplier=1.5,
        label=f"select volatility_snapshots for {symbol}",
    )
    return rows or []


def latest_at_or_before(rows: List[Dict[str, Any]], target_ts: datetime) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_ts: Optional[datetime] = None

    for row in rows:
        row_ts = parse_iso_dt(row.get("ts") or row.get("created_at"))
        if row_ts is None:
            continue
        if row_ts <= target_ts:
            if best_ts is None or row_ts > best_ts:
                best = row
                best_ts = row_ts

    return best


def earliest_on_or_after(rows: List[Dict[str, Any]], target_ts: datetime) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_ts: Optional[datetime] = None

    for row in rows:
        row_ts = parse_iso_dt(row.get("ts") or row.get("created_at"))
        if row_ts is None:
            continue
        if row_ts >= target_ts:
            if best_ts is None or row_ts < best_ts:
                best = row
                best_ts = row_ts

    return best


def get_session_open_ts_utc(ref_ts: datetime) -> datetime:
    ref_ist = ref_ts.astimezone(IST)
    open_ist = datetime.combine(ref_ist.date(), dt_time(hour=9, minute=15), tzinfo=IST)
    return open_ist.astimezone(timezone.utc)


def compute_intraday_changes(
    recent_rows: List[Dict[str, Any]],
    current_ts: datetime,
    current_vix: float,
) -> Dict[str, Optional[float]]:
    target_5m = current_ts - timedelta(minutes=5)
    target_15m = current_ts - timedelta(minutes=15)
    target_30m = current_ts - timedelta(minutes=30)
    open_ts = get_session_open_ts_utc(current_ts)

    row_5m = latest_at_or_before(recent_rows, target_5m)
    row_15m = latest_at_or_before(recent_rows, target_15m)
    row_30m = latest_at_or_before(recent_rows, target_30m)

    open_row = earliest_on_or_after(recent_rows, open_ts)
    if open_row is None:
        same_day_rows = []
        for row in recent_rows:
            ts = parse_iso_dt(row.get("ts") or row.get("created_at"))
            if ts is not None and ts.date() == current_ts.date():
                same_day_rows.append((ts, row))
        if same_day_rows:
            same_day_rows.sort(key=lambda x: x[0])
            open_row = same_day_rows[0][1]

    vix_5m = safe_float(row_5m.get("india_vix")) if row_5m else None
    vix_15m = safe_float(row_15m.get("india_vix")) if row_15m else None
    vix_30m = safe_float(row_30m.get("india_vix")) if row_30m else None
    vix_open = safe_float(open_row.get("india_vix")) if open_row else None

    change_5m = current_vix - vix_5m if vix_5m is not None else None
    change_15m = current_vix - vix_15m if vix_15m is not None else None
    change_30m = current_vix - vix_30m if vix_30m is not None else None
    change_since_open = current_vix - vix_open if vix_open is not None else None
    pct_change_since_open = ((change_since_open / vix_open) * 100.0) if (change_since_open is not None and vix_open not in (None, 0)) else None

    return {
        "vix_change_5m": change_5m,
        "vix_change_15m": change_15m,
        "vix_change_30m": change_30m,
        "vix_change_since_open": change_since_open,
        "vix_pct_change_since_open": pct_change_since_open,
    }


def fetch_last_valid_vix_snapshot(sb: SupabaseClient, symbol: str) -> Optional[Dict[str, Any]]:
    rows = retry_call(
        lambda: sb.select(
            table="volatility_snapshots",
            filters={"symbol": f"eq.{symbol}", "india_vix": "not.is.null"},
            order="ts.desc",
            limit=1,
        ),
        attempts=3,
        delay_seconds=2.0,
        backoff_multiplier=1.5,
        label=f"fallback select volatility_snapshots for {symbol}",
    )
    if rows:
        return rows[0]
    return None


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: python .\\compute_volatility_metrics_local.py <run_id>")

    run_id = sys.argv[1]

    print("=" * 72)
    print("MERDIAN - Local Python compute_volatility_metrics")
    print("=" * 72)
    print(f"Run ID: {run_id}")
    print("-" * 72)

    sb = SupabaseClient()

    option_rows = retry_call(
        lambda: sb.select(
            table="option_chain_snapshots",
            filters={"run_id": f"eq.{run_id}"},
            order="strike.asc",
            limit=5000,
        ),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label=f"select option_chain_snapshots for run_id={run_id}",
    )

    if not option_rows:
        raise RuntimeError(f"No option_chain_snapshots rows found for run_id={run_id}")

    print(f"Fetched option rows: {len(option_rows)}")

    first = option_rows[0]
    symbol = str(first["symbol"]).upper()
    expiry_date = parse_iso_date(first.get("expiry_date"))
    ts_value = parse_iso_dt(first.get("ts") or first.get("created_at"))
    spot = safe_float(first.get("spot"))

    if expiry_date is None:
        raise RuntimeError("expiry_date missing from option rows")
    if ts_value is None:
        raise RuntimeError("ts missing from option rows")
    if spot is None:
        raise RuntimeError("spot missing from option rows")

    atm_strike = find_atm_strike(spot, symbol)

    ce_row = find_row(option_rows, atm_strike, "CE")
    pe_row = find_row(option_rows, atm_strike, "PE")

    if ce_row is None:
        raise RuntimeError(f"ATM CE row not found for symbol={symbol}, strike={atm_strike}")
    if pe_row is None:
        raise RuntimeError(f"ATM PE row not found for symbol={symbol}, strike={atm_strike}")

    atm_call_iv = safe_float(ce_row.get("iv"))
    atm_put_iv = safe_float(pe_row.get("iv"))

    if atm_call_iv is None:
        raise RuntimeError("ATM call IV missing")
    if atm_put_iv is None:
        raise RuntimeError("ATM put IV missing")

    atm_iv_avg = (atm_call_iv + atm_put_iv) / 2.0
    iv_skew = atm_put_iv - atm_call_iv

    today = datetime.now().date()
    dte = (expiry_date - today).days
    expiry_type = get_expiry_type(expiry_date, symbol)

    vix_payload: Dict[str, Any]
    stale_vix = False

    try:
        vix_payload = retry_call(
            lambda: fetch_india_vix(),
            attempts=3,
            delay_seconds=5.0,
            backoff_multiplier=1.5,
            label="fetch_india_vix",
        )
    except Exception as exc:
        fallback = fetch_last_valid_vix_snapshot(sb, symbol)
        if fallback is None:
            raise RuntimeError(f"Live VIX fetch failed and no fallback row available: {exc}") from exc

        stale_vix = True
        vix_payload = {
            "india_vix": safe_float(fallback.get("india_vix")),
            "vix_change": safe_float(fallback.get("vix_change")),
            "vix_regime": fallback.get("vix_regime"),
            "raw_vix_row": {
                "fallback_reason": str(exc),
                "fallback_source": "volatility_snapshots",
                "fallback_ts": fallback.get("ts"),
            },
        }

    india_vix = safe_float(vix_payload.get("india_vix"))
    vix_change = safe_float(vix_payload.get("vix_change"))
    vix_regime = vix_payload.get("vix_regime")

    if india_vix is None:
        raise RuntimeError("India VIX missing after fetch/fallback")

    history_rows = load_vix_history_rows(sb)
    vix_percentile = compute_vix_percentile(history_rows, ts_value.date(), india_vix)
    vix_percentile_regime = classify_percentile_regime(vix_percentile)
    vix_context_regime = classify_context_regime(vix_percentile)
    vix_level_bucket = classify_vix_level_bucket(india_vix)

    recent_vol_rows = fetch_recent_volatility_rows(sb, symbol)
    intraday = compute_intraday_changes(
        recent_rows=recent_vol_rows,
        current_ts=ts_value,
        current_vix=india_vix,
    )

    prev_1d = nearest_prior_history_value(history_rows, ts_value.date() - timedelta(days=1))
    prev_3d = nearest_prior_history_value(history_rows, ts_value.date() - timedelta(days=3))
    prev_5d = nearest_prior_history_value(history_rows, ts_value.date() - timedelta(days=5))

    vix_change_1d = (india_vix - prev_1d) if prev_1d is not None else None
    vix_change_3d = (india_vix - prev_3d) if prev_3d is not None else None
    vix_change_5d = (india_vix - prev_5d) if prev_5d is not None else None
    vix_pct_change_1d = ((vix_change_1d / prev_1d) * 100.0) if (vix_change_1d is not None and prev_1d not in (None, 0)) else None

    vix_intraday_velocity = classify_intraday_velocity(
        intraday["vix_change_5m"],
        intraday["vix_change_15m"],
        intraday["vix_change_30m"],
        intraday["vix_pct_change_since_open"],
    )

    vix_interday_velocity = classify_interday_velocity(
        vix_change_1d,
        vix_change_3d,
        vix_change_5d,
    )

    vix_direction = classify_vix_direction(
        intraday["vix_change_5m"],
        intraday["vix_change_15m"],
        intraday["vix_change_30m"],
        vix_change,
    )

    vix_slope = compute_vix_slope(
        intraday["vix_change_30m"],
        intraday["vix_change_15m"],
        intraday["vix_change_5m"],
    )

    atm_iv_vs_vix_spread = atm_iv_avg - india_vix if atm_iv_avg is not None else None

    volatility_row: Dict[str, Any] = {
        "ts": first["ts"],
        "symbol": symbol,
        "expiry_date": expiry_date.isoformat(),
        "expiry_type": expiry_type,
        "dte": dte,
        "spot": spot,
        "atm_strike": atm_strike,
        "atm_call_iv": atm_call_iv,
        "atm_put_iv": atm_put_iv,
        "atm_iv_avg": atm_iv_avg,
        "iv_skew": iv_skew,
        "source_run_id": run_id,
        "india_vix": india_vix,
        "vix_change": vix_change,
        "vix_regime": vix_regime or classify_vix_level_regime(india_vix),
        "vix_context_regime": vix_context_regime,
        "vix_level_bucket": vix_level_bucket,
        "vix_percentile": vix_percentile,
        "vix_change_5m": intraday["vix_change_5m"],
        "vix_change_15m": intraday["vix_change_15m"],
        "vix_change_30m": intraday["vix_change_30m"],
        "vix_change_since_open": intraday["vix_change_since_open"],
        "vix_pct_change_since_open": intraday["vix_pct_change_since_open"],
        "vix_intraday_velocity": vix_intraday_velocity,
        "vix_change_1d": vix_change_1d,
        "vix_change_3d": vix_change_3d,
        "vix_change_5d": vix_change_5d,
        "vix_pct_change_1d": vix_pct_change_1d,
        "vix_interday_velocity": vix_interday_velocity,
        "vix_percentile_regime": vix_percentile_regime,
        "vix_direction": vix_direction,
        "vix_slope": vix_slope,
        "atm_iv_vs_vix_spread": atm_iv_vs_vix_spread,
        "raw": {
            "atm_call_iv": atm_call_iv,
            "atm_put_iv": atm_put_iv,
            "atm_iv_avg": atm_iv_avg,
            "iv_skew": iv_skew,
            "atm_strike": atm_strike,
            "source_run_id": run_id,
            "india_vix": india_vix,
            "vix_change": vix_change,
            "vix_regime": vix_regime or classify_vix_level_regime(india_vix),
            "vix_percentile": vix_percentile,
            "vix_percentile_regime": vix_percentile_regime,
            "vix_context_regime": vix_context_regime,
            "vix_level_bucket": vix_level_bucket,
            "vix_direction": vix_direction,
            "vix_slope": vix_slope,
            "atm_iv_vs_vix_spread": atm_iv_vs_vix_spread,
            "vix_change_5m": intraday["vix_change_5m"],
            "vix_change_15m": intraday["vix_change_15m"],
            "vix_change_30m": intraday["vix_change_30m"],
            "vix_change_since_open": intraday["vix_change_since_open"],
            "vix_pct_change_since_open": intraday["vix_pct_change_since_open"],
            "vix_intraday_velocity": vix_intraday_velocity,
            "vix_change_1d": vix_change_1d,
            "vix_change_3d": vix_change_3d,
            "vix_change_5d": vix_change_5d,
            "vix_pct_change_1d": vix_pct_change_1d,
            "vix_interday_velocity": vix_interday_velocity,
            "stale_vix": stale_vix,
            "history_source_rows": len(history_rows),
            "nse_vix_row": vix_payload.get("raw_vix_row"),
        },
    }

    print("Computed volatility row:")
    pprint(volatility_row, sort_dicts=False)
    print("-" * 72)
    print("Writing volatility row to Supabase...")

    inserted = retry_call(
        lambda: sb.insert("volatility_snapshots", [volatility_row]),
        attempts=3,
        delay_seconds=3.0,
        backoff_multiplier=1.5,
        label=f"insert volatility_snapshots for run_id={run_id}",
    )

    inserted_count = len(inserted) if isinstance(inserted, list) else 1

    print(f"Inserted rows returned by Supabase: {inserted_count}")
    print("COMPUTE VOLATILITY METRICS COMPLETED")


if __name__ == "__main__":
    main()
