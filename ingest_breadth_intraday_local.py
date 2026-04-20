from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


# =============================================================================
# Paths / env bootstrap
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

if load_dotenv is not None and ENV_FILE.exists():
    load_dotenv(ENV_FILE)

IST = timezone(timedelta(hours=5, minutes=30))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "").strip()
DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN", "").strip()

# Dhan market quote / LTP endpoint
DHAN_LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"

# Universe / batching
UNIVERSE_PAGE_SIZE = 1000

# Reduced from 50 → 25 to reduce per-request payload size and 429 pressure
LTP_BATCH_SIZE = 1000

# Inter-chunk sleep to stay within Dhan rate limits (seconds)
# At 25 per chunk, ~500 tickers = 20 chunks. 0.5s sleep = ~10s total overhead.
INTER_CHUNK_SLEEP_SEC = 0.5

# Retry / guard knobs
# Increased retries and backoff to handle persistent 429s
MAX_429_RETRIES = 4
BACKOFF_SCHEDULE_SEC = [2.0, 5.0, 10.0, 20.0]
MIN_COVERAGE_PCT = 95.0
MAX_STALENESS_MINUTES = 20

# Session window (IST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


# =============================================================================
# Exceptions / data classes
# =============================================================================

class ConfigurationError(RuntimeError):
    pass


class DhanError(RuntimeError):
    pass


class LtpHttpError(DhanError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class CalendarSkip(SystemExit):
    """
    Raised when the calendar or session guard determines we should not run.
    Inherits from SystemExit so it exits with code 0 — a SKIP is not an error.
    The runner must not treat this as a cycle failure.
    """
    def __init__(self, reason: str) -> None:
        super().__init__(0)
        self.reason = reason


@dataclass
class UniverseRow:
    ticker: str
    dhan_security_id: str


@dataclass
class FetchStats:
    universe_count: int = 0
    unique_security_ids: int = 0
    received_ids: int = 0
    rows_upserted: int = 0
    coverage_pct: float = 0.0
    batch_400_count: int = 0
    batch_429_count: int = 0
    batch_other_error_count: int = 0


# =============================================================================
# Logging helpers
# =============================================================================

def log(msg: str) -> None:
    print(msg, flush=True)


def require_env(name: str, value: str) -> None:
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")


# =============================================================================
# Supabase REST helpers
# =============================================================================

def supabase_headers() -> Dict[str, str]:
    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def supabase_get(path: str, params: Optional[Dict[str, str]] = None) -> Any:
    url = f"{SUPABASE_URL}{path}"
    resp = requests.get(url, headers=supabase_headers(), params=params, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Supabase GET failed | status={resp.status_code} | path={path} | response={resp.text}"
        )
    if not resp.text.strip():
        return []
    return resp.json()


def supabase_post(
    path: str,
    payload: Any,
    *,
    params: Optional[Dict[str, str]] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Any:
    headers = supabase_headers()
    if extra_headers:
        headers.update(extra_headers)

    url = f"{SUPABASE_URL}{path}"
    resp = requests.post(url, headers=headers, params=params, json=payload, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Supabase POST failed | status={resp.status_code} | path={path} | response={resp.text}"
        )
    if not resp.text.strip():
        return []
    try:
        return resp.json()
    except Exception:
        return resp.text


# =============================================================================
# Trading calendar / session guards
# =============================================================================

def now_ist() -> datetime:
    return datetime.now(tz=IST)


def current_trade_date_ist() -> str:
    return now_ist().strftime("%Y-%m-%d")


def is_market_open_window(now_dt: datetime) -> bool:
    hhmm = now_dt.hour * 60 + now_dt.minute
    market_open = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
    market_close = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE
    return market_open <= hhmm <= market_close


def get_calendar_row(trade_date: str) -> Optional[Dict[str, Any]]:
    rows = supabase_get(
        "/rest/v1/trading_calendar",
        params={
            "select": "trade_date,is_open,is_special_session,open_time,close_time,final_eod_ltp_time,holiday_name,notes",
            "trade_date": f"eq.{trade_date}",
            "limit": "1",
        },
    )
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def enforce_calendar_and_session_guards() -> None:
    """
    Guard 1 (calendar) + Guard 2 (session window).

    SKIP conditions exit with code 0 via CalendarSkip — they are not errors.
    The runner must not retry on a clean skip.
    """
    trade_date = current_trade_date_ist()
    row = get_calendar_row(trade_date)

    if not row:
        log("Calendar is_open: False")
        log("Holiday name: No calendar row")
        log("Notes: No trading_calendar row found")
        log("Session state: HOLIDAY")
        log("SKIP: Trading calendar marks today as closed.")
        raise CalendarSkip("No trading_calendar row for today")

    is_open = bool(row.get("is_open"))
    holiday_name = row.get("holiday_name")
    notes = row.get("notes")

    log(f"Calendar is_open: {is_open}")
    log(f"Holiday name: {holiday_name}")
    log(f"Notes: {notes}")

    if not is_open:
        log("Session state: HOLIDAY")
        log("SKIP: Trading calendar marks today as closed.")
        raise CalendarSkip(f"Holiday: {holiday_name}")

    now_dt = now_ist()
    if not is_market_open_window(now_dt):
        state = "PREOPEN" if now_dt.hour < MARKET_OPEN_HOUR or (
            now_dt.hour == MARKET_OPEN_HOUR and now_dt.minute < MARKET_OPEN_MINUTE
        ) else "AFTER_MARKET"
        log(f"Session state: {state}")
        log(f"SKIP: Session state {state} is outside MARKET_OPEN window.")
        raise CalendarSkip(f"Outside market hours: {state}")

    log("Session state: MARKET_OPEN")


# =============================================================================
# Universe loading
# =============================================================================

def normalize_universe_row(row: Dict[str, Any]) -> Optional[UniverseRow]:
    ticker = str(row.get("ticker") or row.get("symbol") or "").strip().upper()
    security_id = str(
        row.get("dhan_security_id")
        or row.get("security_id")
        or row.get("securityId")
        or ""
    ).strip()

    if not ticker or not security_id:
        return None

    return UniverseRow(
        ticker=ticker,
        dhan_security_id=security_id,
    )


def load_active_mapped_nse_universe() -> List[UniverseRow]:
    all_rows: List[UniverseRow] = []
    offset = 0

    while True:
        rows = supabase_get(
            "/rest/v1/breadth_universe_members",
            params={
                "select": "ticker,dhan_security_id,exchange_segment,is_active",
                "is_active": "eq.true",
                "exchange_segment": "eq.NSE",
                "dhan_security_id": "not.is.null",
                "limit": str(UNIVERSE_PAGE_SIZE),
                "offset": str(offset),
                "order": "ticker.asc",
            },
        )

        if not isinstance(rows, list):
            raise RuntimeError("Unexpected universe response from Supabase")

        log(f"Universe page fetched | offset={offset} | rows={len(rows)}")

        if not rows:
            break

        for row in rows:
            normalized = normalize_universe_row(row)
            if normalized:
                all_rows.append(normalized)

        if len(rows) < UNIVERSE_PAGE_SIZE:
            break

        offset += UNIVERSE_PAGE_SIZE

    if all_rows:
        seen = set()
        deduped: List[UniverseRow] = []
        for row in all_rows:
            if row.ticker in seen:
                continue
            seen.add(row.ticker)
            deduped.append(row)
        return deduped

    raise RuntimeError("Could not load mapped NSE universe from Supabase")


# =============================================================================
# Dhan LTP helpers
# =============================================================================

def dhan_headers() -> Dict[str, str]:
    require_env("DHAN_CLIENT_ID", DHAN_CLIENT_ID)
    require_env("DHAN_API_TOKEN", DHAN_API_TOKEN)
    return {
        "access-token": DHAN_API_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def extract_status_code(exc: Exception) -> Optional[int]:
    text = str(exc)
    marker = "status="
    idx = text.find(marker)
    if idx >= 0:
        idx += len(marker)
        digits = []
        while idx < len(text) and text[idx].isdigit():
            digits.append(text[idx])
            idx += 1
        if digits:
            try:
                return int("".join(digits))
            except Exception:
                return None
    return None


def parse_ltp_payload(payload: Any) -> Dict[str, float]:
    result: Dict[str, float] = {}

    if payload is None:
        return result

    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        data_block = payload["data"]
        for _, segment_map in data_block.items():
            if not isinstance(segment_map, dict):
                continue
            for sec_id, sec_data in segment_map.items():
                if isinstance(sec_data, dict):
                    price = sec_data.get("last_price")
                    if price is None:
                        price = sec_data.get("ltp")
                    try:
                        if price is not None:
                            result[str(sec_id)] = float(price)
                    except Exception:
                        continue

    return result


def dhan_get_ltp(security_ids: List[str]) -> Dict[str, float]:
    normalized_ids: List[int] = []
    for x in security_ids:
        text = str(x).strip()
        if not text:
            continue
        try:
            normalized_ids.append(int(text))
        except ValueError as exc:
            raise ValueError(f"Invalid security ID for Dhan LTP request: {x}") from exc

    if not normalized_ids:
        return {}

    payload = {
        "NSE": normalized_ids
    }

    try:
        response = requests.post(
            DHAN_LTP_URL,
            headers=dhan_headers(),
            json=payload,
            timeout=60,
        )
    except requests.RequestException as exc:
        raise DhanError(f"Dhan request transport failure | path=/v2/marketfeed/ltp | detail={exc}") from exc

    body_text = response.text
    if response.status_code >= 400:
        raise LtpHttpError(
            status_code=response.status_code,
            message=(
                f"Dhan HTTP error | status={response.status_code} | "
                f"path=/v2/marketfeed/ltp | response={body_text}"
            ),
        )

    try:
        parsed = response.json()
    except Exception as exc:
        raise DhanError(f"Could not parse Dhan LTP JSON | body={body_text}") from exc

    if not isinstance(parsed, dict):
        raise DhanError(f"Unexpected Dhan LTP payload type: {type(parsed)}")

    status = str(parsed.get("status", "")).lower()
    if status == "failed":
        raise LtpHttpError(
            status_code=response.status_code if response.status_code else 400,
            message=(
                f"Dhan non-success payload | status={response.status_code} | "
                f"path=/v2/marketfeed/ltp | response={body_text}"
            ),
        )

    return parse_ltp_payload(parsed)


def fetch_ltp_with_retry(
    security_ids: List[str],
    stats: FetchStats,
) -> Dict[str, float]:
    last_exc: Optional[Exception] = None

    for attempt in range(MAX_429_RETRIES + 1):
        try:
            return dhan_get_ltp(security_ids)
        except LtpHttpError as exc:
            if exc.status_code == 429:
                stats.batch_429_count += 1
                last_exc = exc
                if attempt >= MAX_429_RETRIES:
                    raise
                delay = BACKOFF_SCHEDULE_SEC[min(attempt, len(BACKOFF_SCHEDULE_SEC) - 1)]
                log(
                    f"429 rate limit | batch_size={len(security_ids)} | "
                    f"attempt={attempt + 1}/{MAX_429_RETRIES + 1} | sleep={delay:.1f}s"
                )
                time.sleep(delay)
                continue

            if exc.status_code == 400:
                stats.batch_400_count += 1
            else:
                stats.batch_other_error_count += 1
            raise
        except Exception as exc:
            last_exc = exc
            stats.batch_other_error_count += 1
            raise

    if last_exc:
        raise last_exc
    return {}


# =============================================================================
# Staleness guard
# =============================================================================

def get_latest_equity_intraday_ts() -> Optional[datetime]:
    rows = supabase_get(
        "/rest/v1/equity_intraday_last",
        params={
            "select": "ts",
            "order": "ts.desc",
            "limit": "1",
        },
    )
    if not isinstance(rows, list) or not rows:
        return None

    ts_val = rows[0].get("ts")
    if not ts_val:
        return None

    try:
        return datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
    except Exception:
        return None


def enforce_staleness_guard_before_write() -> None:
    latest_ts = get_latest_equity_intraday_ts()
    if latest_ts is None:
        return

    age = datetime.now(timezone.utc) - latest_ts.astimezone(timezone.utc)
    if age > timedelta(minutes=MAX_STALENESS_MINUTES):
        raise RuntimeError(
            f"SKIP: Stale snapshot detected in equity_intraday_last | age_minutes={age.total_seconds() / 60:.2f}"
        )


# =============================================================================
# Upsert + RPC
# =============================================================================

def build_rows_for_upsert(universe_rows: List[UniverseRow], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    ts_now = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []

    for row in universe_rows:
        price = prices.get(str(row.dhan_security_id))
        if price is None:
            continue

        rows.append(
            {
                "ticker": row.ticker,
                "dhan_security_id": row.dhan_security_id,
                "last_price": price,
                "ts": ts_now,
                "raw": {
                    "source": "dhan_marketfeed_ltp",
                    "exchange_segment": "NSE",
                    "security_id": row.dhan_security_id,
                    "ticker": row.ticker,
                },
            }
        )

    return rows


def upsert_equity_intraday_last(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    result = supabase_post(
        "/rest/v1/equity_intraday_last",
        rows,
        params={"on_conflict": "ticker"},
        extra_headers={
            "Prefer": "resolution=merge-duplicates,return=representation"
        },
    )

    if isinstance(result, list):
        return len(result)
    return 0


def call_build_market_breadth_intraday() -> None:
    supabase_post("/rest/v1/rpc/build_market_breadth_intraday", {})


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    print("=" * 72)
    print("MERDIAN - Local Python ingest_breadth_intraday")
    print("=" * 72)

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)
    require_env("DHAN_CLIENT_ID", DHAN_CLIENT_ID)
    require_env("DHAN_API_TOKEN", DHAN_API_TOKEN)

    # Guard 1 + Guard 2
    enforce_calendar_and_session_guards()

    # Load universe
    universe_rows = load_active_mapped_nse_universe()
    stats = FetchStats()
    stats.universe_count = len(universe_rows)

    unique_ids = sorted({row.dhan_security_id for row in universe_rows})
    stats.unique_security_ids = len(unique_ids)

    log(f"Active mapped NSE tickers: {stats.universe_count}")
    log(f"LTP batch size: {LTP_BATCH_SIZE} | inter-chunk sleep: {INTER_CHUNK_SLEEP_SEC}s")

    # Fetch in chunks
    all_prices: Dict[str, float] = {}
    total_chunks = math.ceil(len(unique_ids) / LTP_BATCH_SIZE)

    for i in range(total_chunks):
        start = i * LTP_BATCH_SIZE
        end = start + LTP_BATCH_SIZE
        chunk_ids = unique_ids[start:end]
        log(f"Fetching chunk {i + 1}/{total_chunks} | batch_size={len(chunk_ids)}")

        try:
            prices = fetch_ltp_with_retry(chunk_ids, stats)
            all_prices.update(prices)
        except LtpHttpError as exc:
            log(
                f"Chunk failed hard | chunk={i + 1}/{total_chunks} | "
                f"status={exc.status_code} | detail={exc}"
            )
        except Exception as exc:
            stats.batch_other_error_count += 1
            log(f"Chunk failed hard | chunk={i + 1}/{total_chunks} | detail={exc}")

        # Inter-chunk sleep to avoid rate limit accumulation across chunks
        if i < total_chunks - 1:
            time.sleep(INTER_CHUNK_SLEEP_SEC)

    stats.received_ids = len(all_prices)

    # Guard 3 — coverage
    if stats.unique_security_ids > 0:
        stats.coverage_pct = round((stats.received_ids / stats.unique_security_ids) * 100.0, 2)
    else:
        stats.coverage_pct = 0.0

    if stats.coverage_pct < MIN_COVERAGE_PCT:
        log("Prepared rows for upsert: 0")
        call_build_market_breadth_intraday()
        log("-" * 72)
        log(f"Universe count:      {stats.universe_count}")
        log(f"Unique security IDs: {stats.unique_security_ids}")
        log(f"LTP received:        {stats.received_ids}")
        log("Missing IDs:         0")
        log("Rows upserted:       0")
        log(f"Coverage:            {stats.coverage_pct:.2f}%")
        log(f"400 batch count:     {stats.batch_400_count}")
        log(f"429 batch count:     {stats.batch_429_count}")
        log(f"Other error count:   {stats.batch_other_error_count}")
        print("=" * 72)
        raise RuntimeError(
            f"ERROR: Coverage below threshold | coverage={stats.coverage_pct:.2f}% | "
            f"required={MIN_COVERAGE_PCT:.2f}%"
        )

    # Build rows
    rows = build_rows_for_upsert(universe_rows, all_prices)
    log(f"Prepared rows for upsert: {len(rows)}")

    # Guard 4 — stale existing snapshot
    enforce_staleness_guard_before_write()

    # Upsert + RPC
    rows_upserted = upsert_equity_intraday_last(rows)
    stats.rows_upserted = rows_upserted

    call_build_market_breadth_intraday()
    log("RPC executed: build_market_breadth_intraday")
    log("-" * 72)
    log(f"Universe count:      {stats.universe_count}")
    log(f"Unique security IDs: {stats.unique_security_ids}")
    log(f"LTP received:        {stats.received_ids}")
    log("Missing IDs:         0")
    log(f"Rows upserted:       {stats.rows_upserted}")
    log(f"Coverage:            {stats.coverage_pct:.2f}%")
    log(f"400 batch count:     {stats.batch_400_count}")
    log(f"429 batch count:     {stats.batch_429_count}")
    log(f"Other error count:   {stats.batch_other_error_count}")
    print("=" * 72)

    if stats.rows_upserted == 0:
        raise RuntimeError("ERROR: No rows were upserted into equity_intraday_last")

    return 0


if __name__ == "__main__":
    main()
