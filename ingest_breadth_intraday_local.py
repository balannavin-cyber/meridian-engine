from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    from core.supabase_client import supabase_client  # type: ignore
except Exception:
    supabase_client = None  # type: ignore

try:
    from core.dhan_client import dhan_client  # type: ignore
except Exception:
    dhan_client = None  # type: ignore

try:
    import core.supabase_client as supabase_module  # type: ignore
except Exception:
    supabase_module = None  # type: ignore

try:
    import core.dhan_client as dhan_module  # type: ignore
except Exception:
    dhan_module = None  # type: ignore


PAGE_SIZE = 1000
LTP_CHUNK_SIZE = 50
SLEEP_BETWEEN_CHUNKS_SEC = 1.25
MAX_429_RETRIES = 3
BACKOFF_SCHEDULE_SEC = [2.0, 5.0, 10.0]
UPSERT_BATCH_SIZE = 500

UNIVERSE_TABLE = "dhan_scrip_map"
UNIVERSE_ORDER_BY = "ticker"

UNIVERSE_FILTER_CANDIDATES = [
    {"exchange": "NSE", "is_active": True},
    {"exchange_segment": "NSE", "is_active": True},
    {"exchange": "NSE"},
    {"exchange_segment": "NSE"},
    {},
]

TARGET_TABLE = "equity_intraday_last"
BREADTH_RPC_NAME = "build_market_breadth_intraday"


class LtpHttpError(Exception):
    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        self.message = message or f"HTTP {status_code}"
        super().__init__(self.message)


class ConfigurationError(Exception):
    pass


@dataclass
class UniverseRow:
    ticker: str
    dhan_security_id: str


@dataclass
class FetchStats:
    requested_ids: int = 0
    received_ids: int = 0
    missing_ids: int = 0
    batch_400_count: int = 0
    batch_429_count: int = 0
    other_error_count: int = 0


def log(msg: str) -> None:
    print(msg, flush=True)


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


def sb_select(
    client: Any,
    table: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = PAGE_SIZE,
    offset: int = 0,
    order: Optional[str] = None,
    ascending: bool = True,
) -> List[Dict[str, Any]]:
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
                    price = safe_float(sec_data.get("last_price"))
                    if price is not None:
                        result[str(sec_id)] = price

    return result


def dhan_get_ltp(client: Any, security_ids: List[str]) -> Dict[str, float]:
    try:
        if hasattr(client, "get_ltp"):
            payload = client.get_ltp(security_ids)
        elif hasattr(dhan_module, "get_ltp"):
            payload = dhan_module.get_ltp(security_ids)  # type: ignore
        else:
            raise ConfigurationError("Dhan client does not expose get_ltp()")
        return parse_ltp_payload(payload)
    except Exception as exc:
        status_code = extract_status_code(exc)
        if status_code is not None:
            raise LtpHttpError(status_code=status_code, message=str(exc)) from exc
        raise


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


def load_universe_page(client: Any, offset: int, filters: Dict[str, Any]) -> List[UniverseRow]:
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
        try:
            while True:
                page = load_universe_page(client, offset=offset, filters=filters)
                log(f"Universe page fetched | offset={offset} | rows={len(page)}")
                if not page:
                    break
                all_rows.extend(page)
                if len(page) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
        except Exception as exc:
            log(f"Universe load attempt failed for filters={filters}: {exc}")
            continue

        if all_rows:
            deduped: List[UniverseRow] = []
            seen = set()
            for row in all_rows:
                if row.ticker in seen:
                    continue
                seen.add(row.ticker)
                deduped.append(row)
            return deduped

    raise RuntimeError("Could not load mapped NSE universe from Supabase")


def fetch_ltp_with_retry(
    dhan: Any,
    security_ids: List[str],
    stats: FetchStats,
) -> Dict[str, float]:
    last_exc: Optional[Exception] = None

    for attempt in range(MAX_429_RETRIES + 1):
        try:
            return dhan_get_ltp(dhan, security_ids)
        except LtpHttpError as exc:
            if exc.status_code == 429:
                stats.batch_429_count += 1
                last_exc = exc
                if attempt >= MAX_429_RETRIES:
                    raise
                delay = BACKOFF_SCHEDULE_SEC[min(attempt, len(BACKOFF_SCHEDULE_SEC) - 1)]
                log(
                    f"429 rate limit | batch_size={len(security_ids)} | "
                    f"attempt={attempt + 1}/{MAX_429_RETRIES + 1} | sleep={delay:.1f}s | "
                    f"detail={exc.message}"
                )
                time.sleep(delay)
                continue
            if exc.status_code == 400:
                stats.batch_400_count += 1
            raise
        except Exception as exc:
            last_exc = exc
            raise

    if last_exc:
        raise last_exc
    return {}


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
                "last_price": price,
                "ts": ts,
            }
        )

    return rows


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
    stats = FetchStats(requested_ids=len(security_ids))
    price_by_security_id: Dict[str, float] = {}
    missing_security_ids: List[str] = []

    chunks = list(chunked(security_ids, LTP_CHUNK_SIZE))
    total_chunks = len(chunks)

    for idx, chunk in enumerate(chunks, start=1):
        log(f"Fetching chunk {idx}/{total_chunks} | batch_size={len(chunk)}")

        try:
            prices = fetch_ltp_with_retry(
                dhan=dhan,
                security_ids=chunk,
                stats=stats,
            )
            price_by_security_id.update(prices)

            returned_ids = set(prices.keys())
            requested_ids = set(chunk)
            missing_ids = sorted(requested_ids - returned_ids)

            if missing_ids:
                missing_security_ids.extend(missing_ids)
                preview = ", ".join(missing_ids[:10])
                more = "" if len(missing_ids) <= 10 else f" ... (+{len(missing_ids) - 10} more)"
                log(
                    f"Chunk partial | chunk={idx}/{total_chunks} | "
                    f"requested={len(chunk)} | received={len(prices)} | "
                    f"missing={len(missing_ids)} | missing_ids={preview}{more}"
                )
            else:
                log(
                    f"Chunk done | chunk={idx}/{total_chunks} | "
                    f"requested={len(chunk)} | received={len(prices)} | "
                    f"cumulative_prices={len(price_by_security_id)}"
                )

        except LtpHttpError as exc:
            stats.other_error_count += 1
            log(
                f"Chunk failed hard | chunk={idx}/{total_chunks} | "
                f"status={exc.status_code} | detail={exc.message}"
            )
        except Exception as exc:
            stats.other_error_count += 1
            log(f"Chunk failed hard | chunk={idx}/{total_chunks} | error={exc}")

        time.sleep(SLEEP_BETWEEN_CHUNKS_SEC)

    missing_security_ids = dedupe_preserve_order(missing_security_ids)
    stats.received_ids = len(price_by_security_id)
    stats.missing_ids = len(missing_security_ids)

    upsert_rows = build_upsert_rows(universe, price_by_security_id)
    log(f"Prepared rows for upsert: {len(upsert_rows)}")

    if upsert_rows:
        log(f"Upsert sample row keys: {list(upsert_rows[0].keys())}")
        log(f"Upsert sample row: {json.dumps(upsert_rows[0], default=str)}")

    upserted_total = 0
    for batch_no, batch in enumerate(chunked(upsert_rows, UPSERT_BATCH_SIZE), start=1):
        try:
            sb_upsert(
                client=sb,
                table=TARGET_TABLE,
                rows=batch,
                on_conflict="ticker",
            )
        except Exception as exc:
            log(f"UPSERT FAILED | batch_no={batch_no} | batch_size={len(batch)}")
            if batch:
                log(f"UPSERT FAILED | first_row_keys={list(batch[0].keys())}")
                log(f"UPSERT FAILED | first_row={json.dumps(batch[0], default=str)}")
            raise

        upserted_total += len(batch)
        log(f"Upserted rows: {upserted_total}/{len(upsert_rows)}")

    rpc_result = sb_rpc(sb, BREADTH_RPC_NAME, {})
    log(f"RPC executed: {BREADTH_RPC_NAME}")

    coverage = (len(upsert_rows) / len(universe)) if universe else 0.0

    log("-" * 72)
    log(f"Universe count:      {len(universe)}")
    log(f"Unique security IDs: {len(security_ids)}")
    log(f"LTP received:        {stats.received_ids}")
    log(f"Missing IDs:         {stats.missing_ids}")
    log(f"Rows upserted:       {upserted_total}")
    log(f"Coverage:            {coverage:.2%}")
    log(f"400 batch count:     {stats.batch_400_count}")
    log(f"429 batch count:     {stats.batch_429_count}")
    log(f"Other error count:   {stats.other_error_count}")

    if missing_security_ids:
        preview = ", ".join(missing_security_ids[:20])
        more = "" if len(missing_security_ids) <= 20 else f" ... (+{len(missing_security_ids) - 20} more)"
        log(f"Missing security IDs:{preview}{more}")

    log("=" * 72)

    return {
        "universe_count": len(universe),
        "unique_security_ids": len(security_ids),
        "ltp_received": stats.received_ids,
        "missing_ids": stats.missing_ids,
        "rows_upserted": upserted_total,
        "coverage_pct": round(coverage * 100.0, 2),
        "batch_400_count": stats.batch_400_count,
        "batch_429_count": stats.batch_429_count,
        "other_error_count": stats.other_error_count,
        "missing_security_ids": missing_security_ids,
        "rpc_result": rpc_result,
    }


def main() -> int:
    try:
        result = run()
        if result.get("rows_upserted", 0) == 0:
            log("ERROR: No rows were upserted into equity_intraday_last")
            return 2
        return 0
    except Exception as exc:
        log(f"FATAL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())