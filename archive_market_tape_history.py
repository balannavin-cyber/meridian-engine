from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import create_client, Client


def _load_env() -> Client:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL not found in environment or .env")

    if not service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not found in environment or .env")

    if not supabase_url.startswith("http://") and not supabase_url.startswith("https://"):
        raise RuntimeError(
            f"SUPABASE_URL is invalid: {supabase_url!r}. It must start with https://"
        )

    return create_client(supabase_url, service_role_key)


SUPABASE: Client = _load_env()


def _rows(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    data = getattr(result, "data", None)
    if data is None:
        return []
    return data if isinstance(data, list) else []


def _iso_ts(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.isoformat()
    return str(value)


def _upsert_rows(table_name: str, rows: list[dict[str, Any]], on_conflict: str) -> None:
    if not rows:
        return
    SUPABASE.table(table_name).upsert(rows, on_conflict=on_conflict).execute()


def _latest_row_by_symbol(table_name: str, symbol: str) -> dict[str, Any] | None:
    result = (
        SUPABASE.table(table_name)
        .select("*")
        .eq("symbol", symbol)
        .order("ts", desc=True)
        .limit(1)
        .execute()
    )
    rows = _rows(result)
    return rows[0] if rows else None


def archive_spot() -> int:
    symbol_to_security = {
        "NIFTY": "13",
        "SENSEX": "51",
    }

    out_rows: list[dict[str, Any]] = []

    for symbol, security_id in symbol_to_security.items():
        row = _latest_row_by_symbol("market_spot_snapshots", symbol)
        if not row:
            print(f"[spot] No source row found for {symbol} in market_spot_snapshots")
            continue

        ts = _iso_ts(row.get("ts"))
        ltp = row.get("spot")
        if ltp is None:
            ltp = row.get("ltp")
        if ltp is None:
            ltp = row.get("price")

        if not ts or ltp is None:
            print(f"[spot] Skipping {symbol}: missing ts or price")
            continue

        out_rows.append(
            {
                "ts": ts,
                "symbol": symbol,
                "security_id": security_id,
                "segment": "IDX_I",
                "ltp": ltp,
                "source": "run_market_tape_1m",
            }
        )

    _upsert_rows(
        "historical_market_spot_1m",
        out_rows,
        on_conflict="symbol,ts",
    )

    return len(out_rows)


def archive_futures() -> int:
    out_rows: list[dict[str, Any]] = []

    for symbol in ("NIFTY", "SENSEX"):
        row = _latest_row_by_symbol("index_futures_snapshots", symbol)
        if not row:
            print(f"[futures] No source row found for {symbol} in index_futures_snapshots")
            continue

        ts = _iso_ts(row.get("ts"))
        if not ts:
            print(f"[futures] Skipping {symbol}: missing ts")
            continue

        security_id = row.get("security_id")
        if security_id is None:
            security_id = row.get("future_security_id")
        if security_id is None:
            security_id = row.get("contract_security_id")

        ltp = row.get("futures_price")
        if ltp is None:
            ltp = row.get("ltp")
        if ltp is None:
            ltp = row.get("price")

        out_rows.append(
            {
                "ts": ts,
                "symbol": symbol,
                "contract_code": row.get("contract_code") or row.get("contract") or row.get("display_name"),
                "security_id": str(security_id) if security_id is not None else None,
                "expiry_date": row.get("expiry_date"),
                "ltp": ltp,
                "open_interest": row.get("open_interest") or row.get("oi"),
                "volume": row.get("volume"),
                "basis": row.get("basis"),
                "basis_pct": row.get("basis_pct"),
                "source": "run_market_tape_1m",
            }
        )

    _upsert_rows(
        "historical_index_futures_1m",
        out_rows,
        on_conflict="symbol,ts",
    )

    return len(out_rows)


def main() -> None:
    spot_count = archive_spot()
    fut_count = archive_futures()
    print(
        f"Historical market tape archive complete. "
        f"spot_rows_upserted={spot_count}, futures_rows_upserted={fut_count}"
    )


if __name__ == "__main__":
    main()