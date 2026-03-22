from __future__ import annotations

import argparse
from typing import Any, Dict, List, Optional, Set

from core.supabase_client import SupabaseClient
from outcome_engine_common import evaluate_baseline_signal_row, page_source_rows


SOURCE_TABLE = "signal_snapshots"
OUTCOME_TABLE = "signal_outcomes"


def get_existing_signal_ids(sb: SupabaseClient) -> Set[int]:
    existing: Set[int] = set()
    offset = 0
    page_size = 1000

    while True:
        rows = sb.select(
            OUTCOME_TABLE,
            limit=page_size,
            offset=offset,
            order="signal_ts",
            ascending=False,
        )
        if not rows:
            break

        for row in rows:
            signal_id = row.get("signal_id")
            if signal_id is not None:
                try:
                    existing.add(int(signal_id))
                except Exception:
                    pass

        if len(rows) < page_size:
            break

        offset += page_size

    return existing


def build_outcomes(
    since_ts: Optional[str] = None,
    max_rows: Optional[int] = None,
    force_rebuild: bool = False,
) -> None:
    sb = SupabaseClient()

    print("=" * 72)
    print("MERDIAN - Build Signal Outcomes (spot timeline version)")
    print("=" * 72)
    print(f"Source table: {SOURCE_TABLE}")
    print(f"Outcome table: {OUTCOME_TABLE}")
    print("Evaluation source: market_spot_snapshots")
    print("-" * 72)

    source_rows = page_source_rows(
        sb=sb,
        table_name=SOURCE_TABLE,
        since_ts=since_ts,
        limit_total=max_rows,
    )

    print(f"Source rows fetched: {len(source_rows)}")

    existing_ids = set() if force_rebuild else get_existing_signal_ids(sb)
    if not force_rebuild:
        print(f"Existing signal_ids already in outcomes: {len(existing_ids)}")

    to_upsert: List[Dict[str, Any]] = []
    skipped_existing = 0
    failed = 0

    for row in source_rows:
        signal_id = row.get("id")
        if signal_id is None:
            failed += 1
            continue

        try:
            signal_id_int = int(signal_id)
        except Exception:
            failed += 1
            continue

        if not force_rebuild and signal_id_int in existing_ids:
            skipped_existing += 1
            continue

        outcome = evaluate_baseline_signal_row(sb, row)
        if outcome is None:
            failed += 1
            continue

        to_upsert.append(outcome)

    print(f"Prepared outcomes: {len(to_upsert)}")
    print(f"Skipped existing:  {skipped_existing}")
    print(f"Failed evaluate:   {failed}")

    if not to_upsert:
        print("No rows to write.")
        return

    batch_size = 200
    written = 0

    for i in range(0, len(to_upsert), batch_size):
        batch = to_upsert[i : i + batch_size]
        sb.upsert(
            OUTCOME_TABLE,
            batch,
            on_conflict="signal_id",
        )
        written += len(batch)
        print(f"Upserted batch {i // batch_size + 1}: {len(batch)} rows")

    print("-" * 72)
    print(f"Completed. Rows written: {written}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since-ts", type=str, default=None, help="ISO timestamp lower bound for signal ts")
    parser.add_argument("--max-rows", type=int, default=None, help="Limit number of source rows")
    parser.add_argument("--force-rebuild", action="store_true", help="Recompute even if outcome exists")
    args = parser.parse_args()

    build_outcomes(
        since_ts=args.since_ts,
        max_rows=args.max_rows,
        force_rebuild=args.force_rebuild,
    )


if __name__ == "__main__":
    main()