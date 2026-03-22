import os
import sys
import json
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from gamma_engine_retry_utils import retry_call


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment.")

HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}

IST = timezone(timedelta(hours=5, minutes=30))

SESSION_START_HOUR = 9
SESSION_START_MINUTE = 15
SESSION_END_HOUR = 15
SESSION_END_MINUTE = 30

SYMBOL_CONFIG = {
    "NIFTY": {
        "strike_step": 50,
    },
    "SENSEX": {
        "strike_step": 100,
    },
}

MOMENTUM_SOURCE = "momentum_engine_v4_6"

LOOKBACK_WINDOWS = {
    "ret_5m": 5,
    "ret_15m": 15,
    "ret_30m": 30,
}

LOOKBACK_TOLERANCE_MINUTES = {
    5: 7,
    15: 10,
    30: 15,
}

PREVIOUS_BUCKET_MAX_GAP_MINUTES = 10


def log(msg: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def rest_get(table_or_view: str, params: dict):
    def _call():
        url = f"{SUPABASE_URL}/rest/v1/{table_or_view}"
        resp = requests.get(url, headers=HEADERS, params=params, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"GET {table_or_view} failed {resp.status_code}: {resp.text}")
        return resp.json()

    return retry_call(
        _call,
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label=f"GET {table_or_view}",
    )


def rest_post(table: str, payload):
    def _call():
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = dict(HEADERS)
        headers["Prefer"] = "return=representation"
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"POST {table} failed {resp.status_code}: {resp.text}")
        return resp.json()

    return retry_call(
        _call,
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label=f"POST {table}",
    )


def to_float(x, default=None):
    if x is None:
        return default
    try:
        return float(x)
    except Exception:
        return default


def to_int(x, default=None):
    if x is None:
        return default
    try:
        return int(round(float(x)))
    except Exception:
        return default


def parse_ts(ts_value):
    if ts_value is None:
        return None
    if isinstance(ts_value, datetime):
        return ts_value
    s = str(ts_value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def minutes_between(ts_a, ts_b):
    dt_a = parse_ts(ts_a)
    dt_b = parse_ts(ts_b)
    if dt_a is None or dt_b is None:
        return None
    return abs((dt_a - dt_b).total_seconds()) / 60.0


def round_to_step(value: float, step: int) -> int:
    return int(round(value / step) * step)


def normalize_option_type(value: str) -> str:
    if value is None:
        return ""
    v = str(value).strip().upper()
    if v in ("CE", "CALL", "C"):
        return "CE"
    if v in ("PE", "PUT", "P"):
        return "PE"
    return v


def first_non_null(*values):
    for v in values:
        if v is not None:
            return v
    return None


def extract_average_price(row: dict):
    raw = row.get("raw")
    if raw is None:
        raw = row.get("raw_json")

    raw_dict = None
    if isinstance(raw, dict):
        raw_dict = raw
    elif isinstance(raw, str):
        try:
            raw_dict = json.loads(raw)
        except Exception:
            raw_dict = None

    if raw_dict:
        avg = first_non_null(
            raw_dict.get("average_price"),
            raw_dict.get("avg_price"),
            raw_dict.get("AveragePrice"),
            raw_dict.get("averagePrice"),
        )
        avg = to_float(avg)
        if avg is not None:
            return avg

    avg = first_non_null(
        row.get("average_price"),
        row.get("avg_price"),
        row.get("AveragePrice"),
    )
    avg = to_float(avg)
    if avg is not None:
        return avg

    return to_float(row.get("ltp"))


def get_latest_gamma_row(symbol: str):
    rows = rest_get(
        "gamma_metrics",
        {
            "symbol": f"eq.{symbol}",
            "select": "ts,symbol,expiry_date,spot,straddle_atm,run_id",
            "order": "ts.desc",
            "limit": 1,
        },
    )
    return rows[0] if rows else None


def get_latest_breadth_rows():
    rows = rest_get(
        "market_breadth_intraday",
        {
            "select": "ts,breadth_score,advances,declines",
            "order": "ts.desc",
            "limit": 2,
        },
    )
    latest = rows[0] if len(rows) >= 1 else None
    previous = rows[1] if len(rows) >= 2 else None
    return latest, previous


def get_latest_option_chain_rows(symbol: str, expiry_date: str):
    rows = rest_get(
        "option_chain_snapshots",
        {
            "symbol": f"eq.{symbol}",
            "expiry_date": f"eq.{expiry_date}",
            "select": "*",
            "order": "ts.desc",
            "limit": 5000,
        },
    )
    if not rows:
        return []

    latest_ts = rows[0].get("ts")
    return [r for r in rows if r.get("ts") == latest_ts]


def get_recent_option_chain_ts(symbol: str, expiry_date: str, limit_rows: int = 5000):
    rows = rest_get(
        "option_chain_snapshots",
        {
            "symbol": f"eq.{symbol}",
            "expiry_date": f"eq.{expiry_date}",
            "select": "ts",
            "order": "ts.desc",
            "limit": limit_rows,
        },
    )
    seen = set()
    ordered = []
    for r in rows:
        ts = r.get("ts")
        if ts and ts not in seen:
            seen.add(ts)
            ordered.append(ts)
    return ordered


def get_option_chain_bucket(symbol: str, expiry_date: str, bucket_ts: str):
    rows = rest_get(
        "option_chain_snapshots",
        {
            "symbol": f"eq.{symbol}",
            "expiry_date": f"eq.{expiry_date}",
            "ts": f"eq.{bucket_ts}",
            "select": "*",
            "limit": 5000,
        },
    )
    return rows


def choose_atm_strike(rows: list, spot: float, strike_step: int):
    if spot is None or not rows:
        return None

    rounded_atm = round_to_step(spot, strike_step)

    strikes = {}
    for r in rows:
        strike = to_float(r.get("strike"))
        opt_type = normalize_option_type(r.get("option_type"))
        if strike is None or opt_type not in ("CE", "PE"):
            continue
        strikes.setdefault(strike, set()).add(opt_type)

    candidate_strikes = [s for s, types in strikes.items() if "CE" in types and "PE" in types]
    if not candidate_strikes:
        return None

    candidate_strikes.sort(key=lambda s: abs(s - rounded_atm))
    return candidate_strikes[0]


def extract_ce_pe(rows: list, atm_strike: float):
    ce_row = None
    pe_row = None
    for r in rows:
        strike = to_float(r.get("strike"))
        opt_type = normalize_option_type(r.get("option_type"))
        if strike == atm_strike and opt_type == "CE":
            ce_row = r
        elif strike == atm_strike and opt_type == "PE":
            pe_row = r
    return ce_row, pe_row


def build_straddle_metrics(rows: list, fixed_atm_strike: float):
    if not rows:
        return None

    latest_ts = rows[0].get("ts")
    ce_row, pe_row = extract_ce_pe(rows, fixed_atm_strike)
    if not ce_row or not pe_row:
        return None

    ce_ltp = to_float(ce_row.get("ltp"), 0.0)
    pe_ltp = to_float(pe_row.get("ltp"), 0.0)
    ce_avg = extract_average_price(ce_row)
    pe_avg = extract_average_price(pe_row)

    if ce_avg is None:
        ce_avg = ce_ltp
    if pe_avg is None:
        pe_avg = pe_ltp

    straddle_price = ce_ltp + pe_ltp
    average_price_sum = ce_avg + pe_avg

    return {
        "atm_strike": fixed_atm_strike,
        "straddle_price": straddle_price,
        "average_price_sum": average_price_sum,
        "ts": latest_ts,
        "ce_ltp": ce_ltp,
        "pe_ltp": pe_ltp,
        "ce_avg": ce_avg,
        "pe_avg": pe_avg,
    }


def find_best_past_bucket_ts(symbol: str, expiry_date: str, target_minutes_ago: int):
    timestamps = get_recent_option_chain_ts(symbol, expiry_date)
    if len(timestamps) < 2:
        return None

    current_ts = parse_ts(timestamps[0])
    if current_ts is None:
        return None

    target_ts = current_ts - timedelta(minutes=target_minutes_ago)
    tolerance = LOOKBACK_TOLERANCE_MINUTES.get(target_minutes_ago, 10)

    best_ts_str = None
    best_abs_diff_seconds = None

    for ts_str in timestamps[1:]:
        dt = parse_ts(ts_str)
        if dt is None:
            continue

        abs_diff_seconds = abs((dt - target_ts).total_seconds())
        if best_abs_diff_seconds is None or abs_diff_seconds < best_abs_diff_seconds:
            best_abs_diff_seconds = abs_diff_seconds
            best_ts_str = ts_str

    if best_ts_str is None:
        return None

    if best_abs_diff_seconds is not None and best_abs_diff_seconds > tolerance * 60:
        return None

    return best_ts_str


def get_immediate_previous_bucket_ts(symbol: str, expiry_date: str):
    timestamps = get_recent_option_chain_ts(symbol, expiry_date)
    if len(timestamps) < 2:
        return None

    current_ts = timestamps[0]
    previous_ts = timestamps[1]

    gap_minutes = minutes_between(current_ts, previous_ts)
    if gap_minutes is None:
        return None

    if gap_minutes > PREVIOUS_BUCKET_MAX_GAP_MINUTES:
        return None

    return previous_ts


def pct_change(new_value: float, old_value: float):
    if old_value is None or old_value == 0:
        return None
    return ((new_value - old_value) / old_value) * 100.0


def simple_delta(new_value: float, old_value: float):
    if new_value is None or old_value is None:
        return None
    return new_value - old_value


def get_session_bounds_utc_for_ts(ts_value: str):
    current_utc = parse_ts(ts_value)
    if current_utc is None:
        return None, None

    current_ist = current_utc.astimezone(IST)

    session_start_ist = current_ist.replace(
        hour=SESSION_START_HOUR,
        minute=SESSION_START_MINUTE,
        second=0,
        microsecond=0,
    )
    session_end_ist = current_ist.replace(
        hour=SESSION_END_HOUR,
        minute=SESSION_END_MINUTE,
        second=0,
        microsecond=0,
    )

    return session_start_ist.astimezone(timezone.utc), session_end_ist.astimezone(timezone.utc)


def get_session_momentum_rows(symbol: str, current_ts: str):
    session_start_utc, session_end_utc = get_session_bounds_utc_for_ts(current_ts)
    if session_start_utc is None or session_end_utc is None:
        return []

    rows = rest_get(
        "momentum_snapshots",
        {
            "symbol": f"eq.{symbol}",
            "ts": f"gte.{session_start_utc.isoformat()}",
            "select": "ts,session_vwap,created_at,source",
            "order": "created_at.asc",
            "limit": 500,
        },
    )

    filtered = []
    current_dt = parse_ts(current_ts)
    for row in rows:
        row_ts = parse_ts(row.get("ts"))
        if row_ts is None or current_dt is None:
            continue
        if row_ts >= current_dt:
            continue
        if row_ts > session_end_utc:
            continue
        filtered.append(row)

    filtered.sort(
        key=lambda r: (
            parse_ts(r.get("ts")) or datetime.min.replace(tzinfo=timezone.utc),
            parse_ts(r.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc),
        )
    )

    deduped_by_ts = {}
    ordered_keys = []

    for row in filtered:
        ts_key = row.get("ts")
        if ts_key not in deduped_by_ts:
            ordered_keys.append(ts_key)
        deduped_by_ts[ts_key] = row

    return [deduped_by_ts[k] for k in ordered_keys]


def compute_session_vwap(symbol: str, current_ts: str, current_straddle_price: float):
    session_rows = get_session_momentum_rows(symbol, current_ts)

    if not session_rows:
        return current_straddle_price, 0, None

    previous_row = session_rows[-1]
    previous_session_vwap = to_float(previous_row.get("session_vwap"))
    prior_count = len(session_rows)

    if previous_session_vwap is None:
        return current_straddle_price, prior_count, previous_row

    new_session_vwap = ((previous_session_vwap * prior_count) + current_straddle_price) / (prior_count + 1)
    return new_session_vwap, prior_count, previous_row


def build_momentum_row(symbol: str):
    if symbol not in SYMBOL_CONFIG:
        raise ValueError(f"Unsupported symbol: {symbol}")

    strike_step = SYMBOL_CONFIG[symbol]["strike_step"]

    gamma_row = get_latest_gamma_row(symbol)
    if not gamma_row:
        raise RuntimeError(f"No gamma_metrics row found for {symbol}")

    expiry_date = gamma_row.get("expiry_date")
    spot = to_float(gamma_row.get("spot"))
    if expiry_date is None or spot is None:
        raise RuntimeError(f"Gamma row missing expiry_date/spot for {symbol}: {gamma_row}")

    latest_chain_rows = get_latest_option_chain_rows(symbol, expiry_date)
    if not latest_chain_rows:
        raise RuntimeError(f"No option_chain_snapshots rows found for {symbol} {expiry_date}")

    fixed_atm_strike = choose_atm_strike(latest_chain_rows, spot, strike_step)
    if fixed_atm_strike is None:
        raise RuntimeError(f"Could not determine ATM strike for {symbol}")

    latest_metrics = build_straddle_metrics(latest_chain_rows, fixed_atm_strike)
    if not latest_metrics:
        raise RuntimeError(f"Could not derive latest ATM straddle metrics for {symbol}")

    current_bucket_ts = latest_metrics["ts"]
    straddle_price = latest_metrics["straddle_price"]

    session_vwap, prior_session_count, previous_momentum = compute_session_vwap(
        symbol=symbol,
        current_ts=current_bucket_ts,
        current_straddle_price=straddle_price,
    )

    if session_vwap is None or session_vwap == 0:
        price_vs_vwap_pct = None
    else:
        price_vs_vwap_pct = ((straddle_price - session_vwap) / session_vwap) * 100.0

    ret_values = {}
    ret_debug = {}

    for col, mins in LOOKBACK_WINDOWS.items():
        past_ts = find_best_past_bucket_ts(symbol, expiry_date, mins)

        if past_ts is None:
            ret_values[col] = None
            ret_debug[col] = {
                "bucket_ts": None,
                "past_price": None,
            }
            continue

        bucket_rows = get_option_chain_bucket(symbol, expiry_date, past_ts)
        past_metrics = build_straddle_metrics(bucket_rows, fixed_atm_strike)

        if past_metrics and past_metrics["straddle_price"] not in (None, 0):
            ret_values[col] = pct_change(straddle_price, past_metrics["straddle_price"])
            ret_debug[col] = {
                "bucket_ts": past_ts,
                "past_price": past_metrics["straddle_price"],
            }
        else:
            ret_values[col] = None
            ret_debug[col] = {
                "bucket_ts": past_ts,
                "past_price": None,
            }

    previous_bucket_ts = get_immediate_previous_bucket_ts(symbol, expiry_date)
    atm_straddle_change = None
    prev_bucket_price = None

    if previous_bucket_ts is not None:
        prev_rows = get_option_chain_bucket(symbol, expiry_date, previous_bucket_ts)
        prev_metrics = build_straddle_metrics(prev_rows, fixed_atm_strike)
        if prev_metrics and prev_metrics["straddle_price"] is not None:
            prev_bucket_price = prev_metrics["straddle_price"]
            atm_straddle_change = straddle_price - prev_bucket_price

    vwap_slope = None
    previous_momentum_ts = None

    if previous_momentum:
        previous_momentum_ts = previous_momentum.get("ts")
        prev_vwap = to_float(previous_momentum.get("session_vwap"))
        if prev_vwap is not None and session_vwap is not None:
            vwap_slope = session_vwap - prev_vwap

    breadth_latest, breadth_previous = get_latest_breadth_rows()

    breadth_score_change = None
    ad_delta = None

    if breadth_latest and breadth_previous:
        latest_breadth_score = to_float(breadth_latest.get("breadth_score"))
        prev_breadth_score = to_float(breadth_previous.get("breadth_score"))
        breadth_score_change = simple_delta(latest_breadth_score, prev_breadth_score)

        latest_adv = to_int(breadth_latest.get("advances"), 0)
        latest_dec = to_int(breadth_latest.get("declines"), 0)
        prev_adv = to_int(breadth_previous.get("advances"), 0)
        prev_dec = to_int(breadth_previous.get("declines"), 0)

        latest_ad = latest_adv - latest_dec
        prev_ad = prev_adv - prev_dec
        ad_delta = latest_ad - prev_ad

    row = {
        "ts": current_bucket_ts,
        "symbol": symbol,
        "ret_5m": round(ret_values["ret_5m"], 4) if ret_values["ret_5m"] is not None else None,
        "ret_15m": round(ret_values["ret_15m"], 4) if ret_values["ret_15m"] is not None else None,
        "ret_30m": round(ret_values["ret_30m"], 4) if ret_values["ret_30m"] is not None else None,
        "breadth_score_change": round(breadth_score_change, 4) if breadth_score_change is not None else None,
        "ad_delta": int(ad_delta) if ad_delta is not None else None,
        "price_vs_vwap_pct": round(price_vs_vwap_pct, 4) if price_vs_vwap_pct is not None else None,
        "vwap_slope": round(vwap_slope, 4) if vwap_slope is not None else None,
        "atm_straddle_change": round(atm_straddle_change, 4) if atm_straddle_change is not None else None,
        "session_vwap": round(session_vwap, 4) if session_vwap is not None else None,
        "source": MOMENTUM_SOURCE,
    }

    debug = {
        "symbol": symbol,
        "expiry_date": expiry_date,
        "spot": spot,
        "atm_strike": fixed_atm_strike,
        "current_bucket_ts": current_bucket_ts,
        "straddle_price": straddle_price,
        "straddle_session_vwap": session_vwap,
        "price_vs_vwap_pct": price_vs_vwap_pct,
        "ret_5m": ret_values["ret_5m"],
        "ret_15m": ret_values["ret_15m"],
        "ret_30m": ret_values["ret_30m"],
        "ret_debug": ret_debug,
        "breadth_score_change": breadth_score_change,
        "ad_delta": ad_delta,
        "previous_momentum_ts": previous_momentum_ts,
        "prior_session_count": prior_session_count,
        "vwap_slope": vwap_slope,
        "previous_bucket_ts": previous_bucket_ts,
        "previous_bucket_price": prev_bucket_price,
        "atm_straddle_change": atm_straddle_change,
        "ts": current_bucket_ts,
        "source": MOMENTUM_SOURCE,
    }

    return row, debug


def main():
    if len(sys.argv) > 1:
        symbols = [sys.argv[1].strip().upper()]
    else:
        symbols = ["NIFTY", "SENSEX"]

    all_rows = []

    for symbol in symbols:
        log(f"Building momentum v4.6 for {symbol} ...")
        row, debug = build_momentum_row(symbol)

        log(f"{symbol} debug:")
        print(json.dumps(debug, indent=2, default=str))

        inserted = rest_post("momentum_snapshots", [row])
        all_rows.extend(inserted)

        log(f"Inserted momentum row for {symbol}")

    log("Done.")
    print(json.dumps(all_rows, indent=2, default=str))


if __name__ == "__main__":
    main()