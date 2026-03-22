from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ============================================================================
# MERDIAN / Gamma Engine
# ingest_breadth_intraday_local.py
#
# Purpose
# -------
# 1. Load mapped active NSE breadth universe from Supabase
# 2. Fetch LTPs from Dhan in safe batches
# 3. Upsert latest prices into equity_intraday_last
# 4. Trigger build_market_breadth_intraday RPC
#
# Key design choices
# ------------------
# - Conservative chunk size (50)
# - Delay between chunks
# - 429 => retry same payload with backoff
# - 400 => split batch to isolate bad security IDs
# - Single bad ID => log and skip, continue partial recovery
#
# Notes
# -----
# This file is intentionally defensive because the current live blocker is:
# Dhan LTP fetch instability during breadth refresh.
# ============================================================================

# ---- Local project imports --------------------------------------------------
try:
    # Preferred pattern if modules expose singleton clients/instances
    from core.supabase_client import supabase_client  # type: ignore
except Exception:
    supabase_client = None  # type: ignore

try:
    # Preferred pattern if module exposes singleton client/instance
    from core.dhan_client import dhan_client  # type: ignore
except Exception:
    dhan_client = None  # type: ignore

try:
    # Fallback: import modules directly
    import core.supabase_client as supabase_module  # type: ignore
except Exception:
    supabase_module = None  # type: ignore

try:
    import core.dhan_client as dhan_module  # type: ignore
except Exception:
    dhan_module = None  # type: ignore


# ---- Runtime constants ------------------------------------------------------
PAGE_SIZE = 1000

# Start conservatively while stabilizing.
LTP_CHUNK_SIZE = 50

# Gentle pacing between successful calls.
SLEEP_BETWEEN_CHUNKS_SEC = 0.75

# 429 handling
MAX_429_RETRIES = 3
BACKOFF_SCHEDULE_SEC = [2.0, 5.0, 10.0]

# 400 isolation handling
MAX_SPLIT_DEPTH = 4

# Upsert batching
UPSERT_BATCH_SIZE = 500

# Universe query defaults
#
# These are the most likely current live fields based on project docs.
# If your live schema uses different field names, edit ONLY these constants.
UNIVERSE_TABLE = "dhan_scrip_map"
UNIVERSE_ORDER_BY = "ticker"

# The code will try a few filter variants because local client wrappers may
# differ in how they encode boolean/equality filters.
UNIVERSE_FILTER_CANDIDATES = [
    {"exchange": "NSE", "is_active": True},
    {"exchange_segment": "NSE", "is_active": True},
    {"exchange": "NSE"},
    {"exchange_segment": "NSE"},
    {},
]

# Target output table / RPC
TARGET_TABLE = "equity_intraday_last"
BREADTH_RPC_NAME = "build_market_breadth_intraday"

# Some clients may need this if previous close is unavailable from universe row.
DEFAULT_PREV_CLOSE = None


# ---- Exceptions -------------------------------------------------------------
class LtpHttpError(Exception):
    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        self.message = message or f"HTTP {status_code}"
        super().__init__(self.message)


class ConfigurationError(Exception):
    pass


# ---- Data structures --------------------------------------------------------
@dataclass
class UniverseRow:
    ticker: str
    dhan_security_id: str
    prev_close: Optional[float] = None


@dataclass
class FetchStats:
    requested_ids: int = 0
    received_ids: int = 0
    bad_ids: int = 0
    batch_400_count: int = 0
    batch_429_count: int = 0
    other_error_count: int = 0


# ---- Logging ----------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


# ---- Client resolution helpers ---------------------------------------------
def get_supabase_client() -> Any:
    if supabase_client is not None:
        return supabase_client
    if supabase_module is not None:
        if hasattr(supabase_module, "SupabaseClient"):
            return supabase_module.SupabaseClient()
        return supabase_module
    raise ConfigurationError("Could not import core.supabase_client")


def get_dhan_client() -> Any:
    if dhan_client is not None:
        return dhan_client
    if dhan_module is not None:
        if hasattr(dhan_module, "DhanClient"):
            return dhan_module.DhanClient()
        return dhan_module
    raise ConfigurationError("Could not import core.dhan_client")


# ---- Utility helpers --------------------------------------------------------
def chunked(items: Sequence[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), size):
        yield list(items[i:i + size])


def dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def normalize_security_ids(values: Iterable[Any]) -> List[str]:
    cleaned: List[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        cleaned.append(text)
    return dedupe_preserve_order(cleaned)


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Supabase wrappers ------------------------------------------------------
def sb_select(
    client: Any,
    table: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = PAGE_SIZE,
    offset: int = 0,
    order: Optional[str] = None,
    ascending: bool = True,
) -> List[Dict[str, Any]]:
    """
    Compatible wrapper around likely Supabase client variants.
    """
    if hasattr(client, "select"):
        return client.select(
            table=table,
            filters=filters or {},
            limit=limit,
            offset=offset,
            order=order,
            ascending=ascending,
        )

    if hasattr(client, "select_all"):
        # Less preferred fallback; emulate page slice if needed
        rows = client.select_all(table=table, filters=filters or {}, page_size=PAGE_SIZE)
        if order:
            rows = sorted(rows, key=lambda r: str(r.get(order, "")), reverse=not ascending)
        return rows[offset: offset + limit]

    raise ConfigurationError("Supabase client does not expose select/select_all")


def sb_upsert(
    client: Any,
    table: str,
    rows: List[Dict[str, Any]],
    on_conflict: str,
) -> Any:
    if hasattr(client, "upsert"):
        return client.upsert(table=table, rows=rows, on_conflict=on_conflict)
    raise ConfigurationError("Supabase client does not expose upsert()")


def sb_rpc(client: Any, function_name: str, params: Dict[str, Any]) -> Any:
    if hasattr(client, "rpc"):
        return client.rpc(function_name=function_name, params=params)
    raise ConfigurationError("Supabase client does not expose rpc()")


# ---- Dhan wrapper -----------------------------------------------------------
def extract_status_code(exc: Exception) -> Optional[int]:
    for attr in ("status_code", "response_status", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    text = str(exc)
    if "429" in text:
        return 429
    if "400" in text:
        return 400
    if "401" in text:
        return 401
    if "403" in text:
        return 403
    if "500" in text:
        return 500
    return None


def parse_ltp_payload(payload: Any) -> Dict[str, float]:
    """
    Convert likely Dhan payload shapes into:
        {security_id: ltp}
    """
    result: Dict[str, float] = {}

    if payload is None:
        return result

    # Case 1: already in the desired form
    if isinstance(payload, dict):
        # direct mapping: { "12345": 101.2 }
        direct_ok = True
        tmp: Dict[str, float] = {}
        for k, v in payload.items():
            if isinstance(v, (int, float, str)):
                price = safe_float(v)
                if price is None:
                    direct_ok = False
                    break
                tmp[str(k)] = price
            else:
                direct_ok = False
                break
        if direct_ok and tmp:
            return tmp

        # common envelopes
        for key in ("data", "ltp", "result", "response"):
            if key in payload:
                nested = parse_ltp_payload(payload[key])
                if nested:
                    return nested

        # dict of dicts: {"12345": {"last_price": 99.1}, ...}
        for k, v in payload.items():
            if isinstance(v, dict):
                for price_key in ("ltp", "last_price", "lastTradedPrice", "price", "LTP"):
                    if price_key in v:
                        price = safe_float(v.get(price_key))
                        if price is not None:
                            result[str(k)] = price
                            break
        if result:
            return result

    # Case 2: list of rows
    if isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict):
                continue
            sid = None
            for sid_key in ("security_id", "securityId", "dhan_security_id", "sec_id", "id"):
                if sid_key in row and row[sid_key] not in (None, ""):
                    sid = str(row[sid_key]).strip()
                    break
            if not sid:
                continue
            price = None
            for price_key in ("ltp", "last_price", "lastTradedPrice", "price", "LTP"):
                if price_key in row:
                    price = safe_float(row.get(price_key))
                    if price is not None:
                        break
            if sid and price is not None:
                result[sid] = price
        if result:
            return result

    return result


def dhan_get_ltp(client: Any, security_ids: List[str]) -> Dict[str, float]:
    """
    Wrapper around whatever get_ltp() form exists in core.dhan_client.
    Raises LtpHttpError with parsed status when possible.
    """
    try:
        if hasattr(client, "get_ltp"):
            payload = client.get_ltp(security_ids)
        elif hasattr(dhan_module, "get_ltp"):
            payload = dhan_module.get_ltp(security_ids)  # type: ignore
        else:
            raise ConfigurationError("Dhan client does not expose get_ltp()")
        parsed = parse_ltp_payload(payload)
        return parsed
    except Exception as exc:
        status_code = extract_status_code(exc)
        if status_code is not None:
            raise LtpHttpError(status_code=status_code, message=str(exc)) from exc
        raise


# ---- Universe loading -------------------------------------------------------
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

    prev_close = (
        safe_float(row.get("prev_close"))
        or safe_float(row.get("close"))
        or safe_float(row.get("previous_close"))
        or DEFAULT_PREV_CLOSE
    )

    return UniverseRow(
        ticker=ticker,
        dhan_security_id=security_id,
        prev_close=prev_close,
    )


def load_universe_page(
    client: Any,
    offset: int,
    filters: Dict[str, Any],
) -> List[UniverseRow]:
    rows = sb_select(
        client=client,
        table=UNIVERSE_TABLE,
        filters=filters,
        limit=PAGE_SIZE,
        offset=offset,
        order=UNIVERSE_ORDER_BY,
        ascending=True,
    )
    normalized: List[UniverseRow] = []
    for row in rows:
        item = normalize_universe_row(row)
        if item is not None:
            normalized.append(item)
    return normalized


def load_active_mapped_nse_universe(client: Any) -> List[UniverseRow]:
    for filters in UNIVERSE_FILTER_CANDIDATES:
        all_rows: List[UniverseRow] = []
        offset = 0
        page_num = 0
        try:
            while True:
                page = load_universe_page(client, offset=offset, filters=filters)
                raw_count = len(page)
                log(f"Universe page fetched | offset={offset} | rows={raw_count}")
                if not page:
                    break
                all_rows.extend(page)
                page_num += 1
                if raw_count < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
        except Exception as exc:
            log(f"Universe load attempt failed for filters={filters}: {exc}")
            continue

        if all_rows:
            # final dedupe by ticker, first occurrence wins
            deduped: List[UniverseRow] = []
            seen = set()
            for row in all_rows:
                if row.ticker in seen:
                    continue
                seen.add(row.ticker)
                deduped.append(row)
            return deduped

    raise RuntimeError(
        "Could not load mapped NSE universe from Supabase. "
        "Check UNIVERSE_TABLE / filter constants in this file."
    )


# ---- LTP fetching -----------------------------------------------------------
def fetch_ltp_with_retry(
    dhan: Any,
    security_ids: List[str],
    stats: FetchStats,
) -> Dict[str, float]:
    """
    Handles 429 only.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(MAX_429_RETRIES + 1):
        try:
            result = dhan_get_ltp(dhan, security_ids)
            return result
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
            raise
        except Exception as exc:
            last_exc = exc
            raise

    if last_exc:
        raise last_exc
    return {}


def fetch_ltp_isolating_bad_ids(
    dhan: Any,
    security_ids: List[str],
    stats: FetchStats,
    depth: int = 0,
) -> Tuple[Dict[str, float], List[str]]:
    """
    400 => split batch recursively
    429 => handled by retry logic in fetch_ltp_with_retry()
    Single-ID 400 => treat that ID as bad and continue
    """
    security_ids = normalize_security_ids(security_ids)
    if not security_ids:
        return {}, []

    try:
        prices = fetch_ltp_with_retry(dhan, security_ids, stats)
        return prices, []
    except LtpHttpError as exc:
        if exc.status_code == 400:
            stats.batch_400_count += 1

            # If already down to one ID, isolate and skip it.
            if len(security_ids) == 1:
                bad_id = security_ids[0]
                log(f"Bad security_id isolated | security_id={bad_id}")
                return {}, [bad_id]

            # If we hit split-depth ceiling, degrade to one-by-one isolation.
            if depth >= MAX_SPLIT_DEPTH:
                log(
                    f"Max split depth reached | depth={depth} | "
                    f"falling back to single-ID probes | batch_size={len(security_ids)}"
                )
                combined: Dict[str, float] = {}
                bad_ids: List[str] = []
                for sid in security_ids:
                    sub_prices, sub_bad = fetch_ltp_isolating_bad_ids(
                        dhan=dhan,
                        security_ids=[sid],
                        stats=stats,
                        depth=depth + 1,
                    )
                    combined.update(sub_prices)
                    bad_ids.extend(sub_bad)
                    time.sleep(0.2)
                return combined, bad_ids

            # Split batch and recurse
            mid = len(security_ids) // 2
            left = security_ids[:mid]
            right = security_ids[mid:]

            log(
                f"400 bad request | batch_size={len(security_ids)} | "
                f"depth={depth} | split={len(left)}+{len(right)}"
            )

            prices_left, bad_left = fetch_ltp_isolating_bad_ids(
                dhan=dhan,
                security_ids=left,
                stats=stats,
                depth=depth + 1,
            )
            time.sleep(0.25)
            prices_right, bad_right = fetch_ltp_isolating_bad_ids(
                dhan=dhan,
                security_ids=right,
                stats=stats,
                depth=depth + 1,
            )

            merged = {}
            merged.update(prices_left)
            merged.update(prices_right)
            return merged, bad_left + bad_right

        raise
    except Exception:
        raise


# ---- Upsert preparation -----------------------------------------------------
def build_upsert_rows(
    universe_rows: List[UniverseRow],
    price_by_security_id: Dict[str, float],
) -> List[Dict[str, Any]]:
    ts = utc_now_iso()
    rows: List[Dict[str, Any]] = []

    for row in universe_rows:
        price = price_by_security_id.get(row.dhan_security_id)
        if price is None:
            continue

        rows.append(
            {
                "ticker": row.ticker,
                "dhan_security_id": row.dhan_security_id,
                "ltp": price,
                "prev_close": row.prev_close,
                "ts": ts,
            }
        )

    return rows


# ---- Main run ---------------------------------------------------------------
def run() -> Dict[str, Any]:
    log("=" * 72)
    log("MERDIAN - Local Python ingest_breadth_intraday")
    log("=" * 72)

    sb = get_supabase_client()
    dhan = get_dhan_client()

    universe = load_active_mapped_nse_universe(sb)
    if not universe:
        raise RuntimeError("Mapped NSE universe is empty")

    log(f"Active mapped NSE tickers: {len(universe)}")

    security_ids = normalize_security_ids([row.dhan_security_id for row in universe])
    ticker_by_security_id = {row.dhan_security_id: row for row in universe}

    stats = FetchStats(requested_ids=len(security_ids))
    price_by_security_id: Dict[str, float] = {}
    bad_security_ids: List[str] = []

    chunks = list(chunked(security_ids, LTP_CHUNK_SIZE))
    total_chunks = len(chunks)

    for idx, chunk in enumerate(chunks, start=1):
        log(f"Fetching chunk {idx}/{total_chunks} | batch_size={len(chunk)}")
        try:
            prices, bad_ids = fetch_ltp_isolating_bad_ids(
                dhan=dhan,
                security_ids=chunk,
                stats=stats,
                depth=0,
            )
            price_by_security_id.update(prices)
            bad_security_ids.extend(bad_ids)

            log(
                f"Chunk done | chunk={idx}/{total_chunks} | "
                f"prices={len(prices)} | bad_ids={len(bad_ids)} | "
                f"cumulative_prices={len(price_by_security_id)}"
            )
        except LtpHttpError as exc:
            stats.other_error_count += 1
            log(
                f"Chunk failed hard | chunk={idx}/{total_chunks} | "
                f"status={exc.status_code} | message={exc.message}"
            )
        except Exception as exc:
            stats.other_error_count += 1
            log(f"Chunk failed hard | chunk={idx}/{total_chunks} | error={exc}")

        time.sleep(SLEEP_BETWEEN_CHUNKS_SEC)

    bad_security_ids = dedupe_preserve_order(bad_security_ids)
    stats.received_ids = len(price_by_security_id)
    stats.bad_ids = len(bad_security_ids)

    upsert_rows = build_upsert_rows(universe, price_by_security_id)
    log(f"Prepared rows for upsert: {len(upsert_rows)}")

    upserted_total = 0
    for batch in chunked(upsert_rows, UPSERT_BATCH_SIZE):
        sb_upsert(
            client=sb,
            table=TARGET_TABLE,
            rows=batch,
            on_conflict="ticker",
        )
        upserted_total += len(batch)
        log(f"Upserted rows: {upserted_total}/{len(upsert_rows)}")

    rpc_result = sb_rpc(sb, BREADTH_RPC_NAME, {})
    log(f"RPC executed: {BREADTH_RPC_NAME}")

    coverage = (len(upsert_rows) / len(universe)) if universe else 0.0

    log("-" * 72)
    log(f"Universe count:           {len(universe)}")
    log(f"Unique security IDs:      {len(security_ids)}")
    log(f"LTP received:             {stats.received_ids}")
    log(f"Rows upserted:            {upserted_total}")
    log(f"Coverage:                 {coverage:.2%}")
    log(f"400 batch count:          {stats.batch_400_count}")
    log(f"429 batch count:          {stats.batch_429_count}")
    log(f"Other error count:        {stats.other_error_count}")
    log(f"Bad security IDs isolated:{stats.bad_ids}")

    if bad_security_ids:
        preview = ", ".join(bad_security_ids[:20])
        more = "" if len(bad_security_ids) <= 20 else f" ... (+{len(bad_security_ids) - 20} more)"
        log(f"Bad security IDs:         {preview}{more}")

    log("=" * 72)

    return {
        "universe_count": len(universe),
        "unique_security_ids": len(security_ids),
        "ltp_received": stats.received_ids,
        "rows_upserted": upserted_total,
        "coverage_pct": round(coverage * 100.0, 2),
        "batch_400_count": stats.batch_400_count,
        "batch_429_count": stats.batch_429_count,
        "other_error_count": stats.other_error_count,
        "bad_security_ids": bad_security_ids,
        "rpc_result": rpc_result,
    }


def main() -> int:
    try:
        result = run()
        # Treat low coverage as non-crash for now; we want visibility first.
        # You can tighten this after live validation.
        if result["rows_upserted"] == 0:
            log("ERROR: No rows were upserted into equity_intraday_last")
            return 2
        return 0
    except Exception as exc:
        log(f"FATAL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())