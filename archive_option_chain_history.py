from __future__ import annotations

import os
import sys
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


# ============================================================
# MERDIAN - archive_option_chain_history.py
# Full-file replacement
#
# Purpose:
#   Archive one option-chain run_id from option_chain_snapshots
#   into historical_option_chain_snapshots
#
# Permanent repair in this version:
#   - idempotent: skips if run_id is already archived
#   - safe for repeated runner invocation
# ============================================================


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


def archived_run_exists(run_id: str) -> bool:
    """
    Return True if this run_id is already present in historical archive.
    """
    result = (
        SUPABASE.table("historical_option_chain_snapshots")
        .select("run_id")
        .eq("run_id", run_id)
        .limit(1)
        .execute()
    )
    rows = _rows(result)
    return len(rows) > 0


def fetch_source_rows(run_id: str, page_size: int = 1000) -> list[dict[str, Any]]:
    """
    Fetch all option_chain_snapshots rows for one run_id.
    """
    all_rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        result = (
            SUPABASE.table("option_chain_snapshots")
            .select("*")
            .eq("run_id", run_id)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = _rows(result)

        if not batch:
            break

        all_rows.extend(batch)

        if len(batch) < page_size:
            break

        offset += page_size

    return all_rows


def archive_run(run_id: str) -> None:
    if archived_run_exists(run_id):
        print(f"SKIP: run_id {run_id} already archived.")
        return

    source_rows = fetch_source_rows(run_id)

    if not source_rows:
        print(f"No option_chain_snapshots rows found for run_id={run_id}")
        return

    out_rows: list[dict[str, Any]] = []

    for row in source_rows:
        ts = row.get("ts") or row.get("created_at")

        out_rows.append(
            {
                "run_id": row.get("run_id"),
                "ts": ts,
                "symbol": row.get("symbol"),
                "expiry_date": row.get("expiry_date"),
                "strike": row.get("strike"),
                "option_type": row.get("option_type"),
                "ltp": row.get("ltp"),
                "bid": row.get("bid"),
                "ask": row.get("ask"),
                "oi": row.get("oi"),
                "oi_change": row.get("oi_change"),
                "volume": row.get("volume"),
                "iv": row.get("iv"),
                "delta": row.get("delta"),
                "gamma": row.get("gamma"),
                "theta": row.get("theta"),
                "vega": row.get("vega"),
                "spot": row.get("spot"),
                "dte": row.get("dte"),
                "raw": row.get("raw"),
                "source": "ingest_option_chain_local",
            }
        )

    SUPABASE.table("historical_option_chain_snapshots").insert(out_rows).execute()

    print(
        f"Archived {len(out_rows)} rows to historical_option_chain_snapshots for run_id={run_id}"
    )


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python archive_option_chain_history.py <run_id>")
        sys.exit(1)

    run_id = sys.argv[1].strip()
    if not run_id:
        print("Usage: python archive_option_chain_history.py <run_id>")
        sys.exit(1)

    archive_run(run_id)


if __name__ == "__main__":
    main()