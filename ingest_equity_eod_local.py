import json
import os
import sys
import time
from datetime import date, datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN", "")
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
JOB_NAME = os.getenv("JOB_NAME", "equity_eod")
DEFAULT_LIMIT_PER_RUN = int(os.getenv("DEFAULT_LIMIT_PER_RUN", "30"))
DHAN_FROM_DAYS_BACK = int(os.getenv("DHAN_FROM_DAYS_BACK", "220"))
DHAN_HISTORICAL_URL = os.getenv(
    "DHAN_HISTORICAL_URL",
    "https://api.dhan.co/v2/charts/historical",
)

# Safety controls
EOD_SAFE_LAG_DAYS = int(os.getenv("EOD_SAFE_LAG_DAYS", "1"))  # default = T-1
EOD_INTER_REQUEST_SLEEP_SEC = float(os.getenv("EOD_INTER_REQUEST_SLEEP_SEC", "0.20"))
EOD_RATE_LIMIT_RETRIES = int(os.getenv("EOD_RATE_LIMIT_RETRIES", "4"))
EOD_RATE_LIMIT_SLEEP_SEC = float(os.getenv("EOD_RATE_LIMIT_SLEEP_SEC", "2.0"))

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY or not DHAN_API_TOKEN:
    print("ERROR: Missing SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or DHAN_API_TOKEN in .env")
    sys.exit(1)

SUPABASE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def jdump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def http_get(url: str, headers: Dict[str, str], params: Optional[Dict[str, Any]] = None) -> requests.Response:
    r = requests.get(url, headers=headers, params=params, timeout=60)
    r.raise_for_status()
    return r


def supabase_table_url(table_name: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table_name}"


def get_ingest_state(job_name: str) -> Dict[str, Any]:
    url = supabase_table_url("breadth_ingest_state")
    params = {
        "select": "job_name,cursor,limit_per_run,last_run_at,last_status,last_error,updated_at",
        "job_name": f"eq.{job_name}",
        "limit": "1",
    }
    r = http_get(url, SUPABASE_HEADERS, params=params)
    data = r.json()

    if isinstance(data, list) and len(data) == 1:
        return data[0]

    seed_row = {
        "job_name": job_name,
        "cursor": 0,
        "limit_per_run": DEFAULT_LIMIT_PER_RUN,
        "last_run_at": None,
        "last_status": "SEEDED_BY_PYTHON",
        "last_error": None,
        "updated_at": utc_now_iso(),
    }
    upsert_rows("breadth_ingest_state", [seed_row], on_conflict="job_name")
    return seed_row


def get_ticker_batch(cursor: int, limit_per_run: int) -> List[Dict[str, Any]]:
    url = supabase_table_url("dhan_scrip_map")
    params = {
        "select": "ticker,dhan_security_id",
        "exchange": "eq.NSE",
        "is_active": "eq.true",
        "dhan_security_id": "not.is.null",
        "order": "ticker.asc",
        "offset": str(cursor),
        "limit": str(limit_per_run),
    }
    r = http_get(url, SUPABASE_HEADERS, params=params)
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f"dhan_scrip_map response is not a list: {jdump(data)}")
    return data


def fetch_dhan_daily_once(security_id: str, from_date: str, to_date: str) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "access-token": DHAN_API_TOKEN,
    }
    if DHAN_CLIENT_ID:
        headers["client-id"] = DHAN_CLIENT_ID

    body = {
        "securityId": str(security_id),
        "exchangeSegment": "NSE_EQ",
        "instrument": "EQUITY",
        "expiryCode": 0,
        "oi": False,
        "fromDate": from_date,
        "toDate": to_date,
    }

    r = requests.post(DHAN_HISTORICAL_URL, headers=headers, json=body, timeout=60)
    text = r.text

    if r.status_code == 429:
        raise RuntimeError(f"Dhan HTTP 429: {text[:500]}")

    if not r.ok:
        raise RuntimeError(f"Dhan HTTP {r.status_code}: {text[:500]}")

    try:
        return r.json()
    except Exception as e:
        raise RuntimeError(f"Dhan returned non-JSON response for securityId={security_id}: {e}") from e


def is_rate_limit_message(msg: str) -> bool:
    msg_l = msg.lower()
    return (
        "dh-904" in msg_l
        or "rate_limit" in msg_l
        or "too many requests" in msg_l
        or "429" in msg_l
    )


def fetch_dhan_daily(security_id: str, from_date: str, to_date: str) -> Dict[str, Any]:
    last_err: Optional[str] = None

    for attempt in range(1, EOD_RATE_LIMIT_RETRIES + 1):
        try:
            return fetch_dhan_daily_once(security_id, from_date, to_date)
        except Exception as e:
            msg = str(e)
            last_err = msg

            if is_rate_limit_message(msg) and attempt < EOD_RATE_LIMIT_RETRIES:
                sleep_for = EOD_RATE_LIMIT_SLEEP_SEC * attempt
                time.sleep(sleep_for)
                continue

            raise RuntimeError(last_err)

    raise RuntimeError(last_err or "Unknown Dhan historical fetch failure")


def parse_dhan_daily(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    open_arr = data.get("open") or data.get("data", {}).get("open") or []
    high_arr = data.get("high") or data.get("data", {}).get("high") or []
    low_arr = data.get("low") or data.get("data", {}).get("low") or []
    close_arr = data.get("close") or data.get("data", {}).get("close") or []
    volume_arr = data.get("volume") or data.get("data", {}).get("volume") or []
    ts_arr = data.get("timestamp") or data.get("data", {}).get("timestamp") or []

    n = min(len(open_arr), len(high_arr), len(low_arr), len(close_arr), len(ts_arr))
    rows: List[Dict[str, Any]] = []

    for i in range(n):
        try:
            trade_date = datetime.fromtimestamp(int(ts_arr[i]), tz=UTC).date().isoformat()
            row = {
                "trade_date": trade_date,
                "open": float(open_arr[i]) if open_arr[i] is not None else None,
                "high": float(high_arr[i]) if high_arr[i] is not None else None,
                "low": float(low_arr[i]) if low_arr[i] is not None else None,
                "close": float(close_arr[i]) if close_arr[i] is not None else None,
                "volume": int(volume_arr[i]) if i < len(volume_arr) and volume_arr[i] is not None else None,
            }
            rows.append(row)
        except Exception:
            continue

    return rows


def dedupe_equity_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        key = (str(row["ticker"]), str(row["trade_date"]))
        deduped[key] = row
    return list(deduped.values())


def upsert_rows(table_name: str, rows: List[Dict[str, Any]], on_conflict: str) -> None:
    if not rows:
        return

    url = supabase_table_url(table_name)
    headers = dict(SUPABASE_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"

    params = {"on_conflict": on_conflict}
    r = requests.post(url, headers=headers, params=params, json=rows, timeout=120)

    if not r.ok:
        raise RuntimeError(f"Supabase upsert into {table_name} failed: HTTP {r.status_code} {r.text[:1000]}")


def update_state(
    job_name: str,
    next_cursor: int,
    limit_per_run: int,
    status: str,
    failures: List[Dict[str, Any]],
) -> None:
    row = {
        "job_name": job_name,
        "cursor": next_cursor,
        "limit_per_run": limit_per_run,
        "last_run_at": utc_now_iso(),
        "last_status": status,
        "last_error": json.dumps(failures[:5]) if failures else None,
        "updated_at": utc_now_iso(),
    }
    upsert_rows("breadth_ingest_state", [row], on_conflict="job_name")


def compute_date_window() -> Tuple[str, str]:
    """
    Critical fix:
    do NOT query Dhan historical through 'today' by default.
    Use T-1 (or more conservative lag if configured).
    """
    today_dt = date.today()
    safe_to_dt = today_dt - timedelta(days=max(EOD_SAFE_LAG_DAYS, 1))
    from_dt = safe_to_dt - timedelta(days=DHAN_FROM_DAYS_BACK)
    return from_dt.isoformat(), safe_to_dt.isoformat()


def is_auth_failure_message(msg: str) -> bool:
    msg_l = msg.lower()
    return (
        "dh-901" in msg_l
        or "invalid_authentication" in msg_l
        or "access token is invalid or expired" in msg_l
        or "client id or user generated access token is invalid or expired" in msg_l
    )


def main() -> None:
    print("=" * 72)
    print("Gamma Engine - Local Python ingest_equity_eod")
    print("=" * 72)

    from_date, to_date = compute_date_window()
    print(f"Date window: {from_date} -> {to_date}")

    state = get_ingest_state(JOB_NAME)
    cursor = int(state.get("cursor", 0))
    limit_per_run = int(state.get("limit_per_run", DEFAULT_LIMIT_PER_RUN))

    print(f"Job name      : {JOB_NAME}")
    print(f"Cursor        : {cursor}")
    print(f"Limit per run : {limit_per_run}")

    tickers = get_ticker_batch(cursor, limit_per_run)
    print(f"Tickers fetched: {len(tickers)}")

    processed = 0
    candles_upserted = 0
    failures: List[Dict[str, Any]] = []

    for item in tickers:
        ticker = item.get("ticker")
        security_id = item.get("dhan_security_id")

        processed += 1

        try:
            raw = fetch_dhan_daily(str(security_id), from_date, to_date)
            rows = parse_dhan_daily(raw)

            final_rows: List[Dict[str, Any]] = []
            for r in rows:
                final_rows.append(
                    {
                        "ticker": ticker,
                        "trade_date": r["trade_date"],
                        "open": r["open"],
                        "high": r["high"],
                        "low": r["low"],
                        "close": r["close"],
                        "volume": r["volume"],
                    }
                )

            final_rows = dedupe_equity_rows(final_rows)
            upsert_rows("equity_eod", final_rows, on_conflict="ticker,trade_date")

            candles_upserted += len(final_rows)
            print(
                f"[OK] {ticker} | security_id={security_id} | "
                f"candles_raw={len(rows)} | candles_upserted={len(final_rows)}"
            )

        except Exception as e:
            failures.append(
                {
                    "ticker": ticker,
                    "security_id": str(security_id),
                    "error": str(e),
                }
            )
            print(f"[ERR] {ticker} | security_id={security_id} | {e}")

        if EOD_INTER_REQUEST_SLEEP_SEC > 0:
            time.sleep(EOD_INTER_REQUEST_SLEEP_SEC)

    all_failed_due_to_auth = (
        len(tickers) > 0
        and len(failures) == len(tickers)
        and all(is_auth_failure_message(f["error"]) for f in failures)
    )

    any_auth_failure = any(is_auth_failure_message(f["error"]) for f in failures)

    if all_failed_due_to_auth:
        next_cursor = cursor
        status = "AUTH_FAILED_NO_CURSOR_ADVANCE"
    elif any_auth_failure:
        next_cursor = cursor
        status = "AUTH_PARTIAL_NO_CURSOR_ADVANCE"
    else:
        next_cursor = 0 if len(tickers) < limit_per_run else cursor + limit_per_run
        status = "PARTIAL_OK" if failures else "OK"

    update_state(
        job_name=JOB_NAME,
        next_cursor=next_cursor,
        limit_per_run=limit_per_run,
        status=status,
        failures=failures,
    )

    print("-" * 72)
    print("Run complete")
    print(f"Processed       : {processed}")
    print(f"Candles upserted: {candles_upserted}")
    print(f"Failures        : {len(failures)}")
    print(f"Next cursor     : {next_cursor}")
    print(f"Status          : {status}")

    if failures:
        print("Sample failures:")
        print(jdump(failures[:5]))


if __name__ == "__main__":
    main()