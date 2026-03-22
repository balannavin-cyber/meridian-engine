from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from core.supabase_client import SupabaseClient


SOURCE_TABLE = "shadow_state_signal_snapshots"
OUTCOME_TABLE = "shadow_state_signal_outcomes"
SPOT_TABLE = "market_spot_snapshots"
UTC = timezone.utc


@dataclass
class SpotPoint:
    ts: datetime
    spot: float


def parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def pct_move(points: Optional[float], entry_spot: float) -> Optional[float]:
    if points is None:
        return None
    if entry_spot == 0:
        return None
    return (points / entry_spot) * 100.0


def outcome_label(action: str, move_points: Optional[float]) -> Optional[str]:
    if move_points is None:
        return None

    a = (action or "DO_NOTHING").upper()

    if a == "BUY_CE":
        if move_points > 0:
            return "WIN"
        if move_points < 0:
            return "LOSS"
        return "FLAT"

    if a == "BUY_PE":
        if move_points < 0:
            return "WIN"
        if move_points > 0:
            return "LOSS"
        return "FLAT"

    if a == "DO_NOTHING":
        return "N/A"

    return None


def fetch_spot_points_for_symbol(sb: SupabaseClient, symbol: str) -> List[SpotPoint]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    page_size = 1000

    while True:
        batch = sb.select(
            table=SPOT_TABLE,
            filters={"symbol": f"eq.{symbol}"},
            limit=page_size,
            offset=offset,
            order="ts.asc",
            ascending=True,
        )

        if not batch:
            break

        rows.extend(batch)

        if len(batch) < page_size:
            break

        offset += page_size

    out: List[SpotPoint] = []
    for row in rows:
        ts_raw = row.get("ts")
        spot_raw = row.get("spot")

        if ts_raw is None or spot_raw is None:
            continue

        spot_val = to_float(spot_raw)
        if spot_val is None:
            continue

        try:
            out.append(SpotPoint(ts=parse_ts(ts_raw), spot=spot_val))
        except Exception:
            continue

    return out


def find_entry_point(spot_points: List[SpotPoint], signal_ts: str) -> Optional[SpotPoint]:
    signal_dt = parse_ts(signal_ts)

    for point in spot_points:
        if point.ts >= signal_dt:
            return point

    return None


def find_first_point_at_or_after(
    spot_points: List[SpotPoint],
    target_dt: datetime,
) -> Optional[SpotPoint]:
    for point in spot_points:
        if point.ts >= target_dt:
            return point
    return None


def compute_horizon_moves(
    spot_points: List[SpotPoint],
    signal_ts: str,
    entry_point: SpotPoint,
) -> Dict[str, Any]:
    signal_dt = parse_ts(signal_ts)

    p15 = find_first_point_at_or_after(spot_points, signal_dt + timedelta(minutes=15))
    p30 = find_first_point_at_or_after(spot_points, signal_dt + timedelta(minutes=30))
    p60 = find_first_point_at_or_after(spot_points, signal_dt + timedelta(minutes=60))

    signal_date = signal_dt.date()
    peod: Optional[SpotPoint] = None
    for point in spot_points:
        if point.ts.date() == signal_date and point.ts >= signal_dt:
            peod = point

    entry_spot = entry_point.spot

    move_15m = (p15.spot - entry_spot) if p15 else None
    move_30m = (p30.spot - entry_spot) if p30 else None
    move_60m = (p60.spot - entry_spot) if p60 else None
    move_eod = (peod.spot - entry_spot) if peod else None

    return {
        "outcome_15m_spot": p15.spot if p15 else None,
        "outcome_30m_spot": p30.spot if p30 else None,
        "outcome_60m_spot": p60.spot if p60 else None,
        "outcome_eod_spot": peod.spot if peod else None,
        "move_15m_points": move_15m,
        "move_30m_points": move_30m,
        "move_60m_points": move_60m,
        "move_eod_points": move_eod,
        "move_15m_pct": pct_move(move_15m, entry_spot),
        "move_30m_pct": pct_move(move_30m, entry_spot),
        "move_60m_pct": pct_move(move_60m, entry_spot),
        "move_eod_pct": pct_move(move_eod, entry_spot),
        "horizon_15m_ts": p15.ts.isoformat() if p15 else None,
        "horizon_30m_ts": p30.ts.isoformat() if p30 else None,
        "horizon_60m_ts": p60.ts.isoformat() if p60 else None,
        "horizon_eod_ts": peod.ts.isoformat() if peod else None,
    }


def compute_mfe_mae_60m(
    action: str,
    spot_points: List[SpotPoint],
    signal_ts: str,
    entry_point: SpotPoint,
) -> Dict[str, Optional[float]]:
    signal_dt = parse_ts(signal_ts)
    end_dt = signal_dt + timedelta(minutes=60)

    window = [p for p in spot_points if p.ts >= signal_dt and p.ts <= end_dt]
    if not window:
        return {"mfe_points_60m": None, "mae_points_60m": None}

    entry_spot = entry_point.spot
    action = (action or "DO_NOTHING").upper()

    diffs = [p.spot - entry_spot for p in window]

    if action == "BUY_CE":
        mfe = max(diffs) if diffs else None
        mae = min(diffs) if diffs else None
        return {
            "mfe_points_60m": mfe,
            "mae_points_60m": mae,
        }

    if action == "BUY_PE":
        inverted = [-d for d in diffs]
        mfe = max(inverted) if inverted else None
        mae = min(inverted) if inverted else None
        return {
            "mfe_points_60m": mfe,
            "mae_points_60m": mae,
        }

    return {
        "mfe_points_60m": None,
        "mae_points_60m": None,
    }


def get_existing_ids(sb: SupabaseClient) -> Set[int]:
    existing: Set[int] = set()
    offset = 0
    page_size = 1000

    while True:
        rows = sb.select(
            table=OUTCOME_TABLE,
            limit=page_size,
            offset=offset,
            order="signal_ts",
            ascending=False,
        )
        if not rows:
            break

        for row in rows:
            source_id = row.get("shadow_state_signal_snapshot_id")
            if source_id is not None:
                try:
                    existing.add(int(source_id))
                except Exception:
                    pass

        if len(rows) < page_size:
            break

        offset += page_size

    return existing


def fetch_source_rows(
    sb: SupabaseClient,
    since_ts: Optional[str] = None,
    max_rows: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    page_size = 500

    while True:
        filters: Dict[str, str] = {}
        if since_ts:
            filters["ts"] = f"gte.{since_ts}"

        batch = sb.select(
            table=SOURCE_TABLE,
            filters=filters if filters else None,
            limit=page_size,
            offset=offset,
            order="ts.asc",
            ascending=True,
        )

        if not batch:
            break

        rows.extend(batch)

        if max_rows is not None and len(rows) >= max_rows:
            rows = rows[:max_rows]
            break

        if len(batch) < page_size:
            break

        offset += page_size

    return rows


def evaluate_shadow_state_row(sb: SupabaseClient, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    source_id = row.get("id")
    symbol = row.get("symbol")
    signal_ts = row.get("ts")
    action = row.get("shadow_action")
    confidence = row.get("shadow_confidence")

    if source_id is None or not symbol or not signal_ts:
        return None

    action = str(action or "DO_NOTHING").upper()

    spot_points = fetch_spot_points_for_symbol(sb, str(symbol))
    if not spot_points:
        return None

    entry_point = find_entry_point(spot_points, str(signal_ts))
    if entry_point is None:
        return None

    moves = compute_horizon_moves(
        spot_points=spot_points,
        signal_ts=str(signal_ts),
        entry_point=entry_point,
    )

    mfe_mae = compute_mfe_mae_60m(
        action=action,
        spot_points=spot_points,
        signal_ts=str(signal_ts),
        entry_point=entry_point,
    )

    return {
        "shadow_state_signal_snapshot_id": int(source_id),
        "symbol": symbol,
        "signal_ts": signal_ts,
        "action": action,
        "confidence": confidence,
        "entry_spot": entry_point.spot,
        "outcome_15m_spot": moves["outcome_15m_spot"],
        "outcome_30m_spot": moves["outcome_30m_spot"],
        "outcome_60m_spot": moves["outcome_60m_spot"],
        "outcome_eod_spot": moves["outcome_eod_spot"],
        "move_15m_points": moves["move_15m_points"],
        "move_30m_points": moves["move_30m_points"],
        "move_60m_points": moves["move_60m_points"],
        "move_eod_points": moves["move_eod_points"],
        "move_15m_pct": moves["move_15m_pct"],
        "move_30m_pct": moves["move_30m_pct"],
        "move_60m_pct": moves["move_60m_pct"],
        "move_eod_pct": moves["move_eod_pct"],
        "outcome_label_15m": outcome_label(action, moves["move_15m_points"]),
        "outcome_label_30m": outcome_label(action, moves["move_30m_points"]),
        "outcome_label_60m": outcome_label(action, moves["move_60m_points"]),
        "outcome_label_eod": outcome_label(action, moves["move_eod_points"]),
        "horizon_15m_ts": moves["horizon_15m_ts"],
        "horizon_30m_ts": moves["horizon_30m_ts"],
        "horizon_60m_ts": moves["horizon_60m_ts"],
        "horizon_eod_ts": moves["horizon_eod_ts"],
        "mfe_points_60m": mfe_mae["mfe_points_60m"],
        "mae_points_60m": mfe_mae["mae_points_60m"],
        "raw": {
            "builder": "build_shadow_state_signal_outcomes_local.py",
            "builder_version": "SHADOW_STATE_SIGNAL_OUTCOME_V1",
            "evaluation_source": "market_spot_snapshots",
            "source_signal_state_shadow_created_at": row.get("created_at"),
            "signal_state": row.get("signal_state"),
            "composite_direction": row.get("composite_direction"),
            "composite_conviction": row.get("composite_conviction"),
            "entry_spot_ts": entry_point.ts.isoformat(),
            "horizon_15m_ts": moves["horizon_15m_ts"],
            "horizon_30m_ts": moves["horizon_30m_ts"],
            "horizon_60m_ts": moves["horizon_60m_ts"],
            "horizon_eod_ts": moves["horizon_eod_ts"],
        },
    }


def build_outcomes(
    since_ts: Optional[str] = None,
    max_rows: Optional[int] = None,
    force_rebuild: bool = False,
) -> None:
    sb = SupabaseClient()

    print("=" * 72)
    print("MERDIAN - Build Shadow State Signal Outcomes")
    print("=" * 72)
    print(f"Source table: {SOURCE_TABLE}")
    print(f"Outcome table: {OUTCOME_TABLE}")
    print("Evaluation source: market_spot_snapshots")
    print("-" * 72)

    source_rows = fetch_source_rows(
        sb=sb,
        since_ts=since_ts,
        max_rows=max_rows,
    )

    print(f"Source rows fetched: {len(source_rows)}")

    existing_ids = set() if force_rebuild else get_existing_ids(sb)
    if not force_rebuild:
        print(f"Existing source ids already in outcomes: {len(existing_ids)}")

    to_upsert: List[Dict[str, Any]] = []
    skipped_existing = 0
    failed = 0

    for row in source_rows:
        source_id = row.get("id")
        if source_id is None:
            failed += 1
            continue

        try:
            source_id_int = int(source_id)
        except Exception:
            failed += 1
            continue

        if not force_rebuild and source_id_int in existing_ids:
            skipped_existing += 1
            continue

        outcome = evaluate_shadow_state_row(sb, row)
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
            on_conflict="shadow_state_signal_snapshot_id",
        )
        written += len(batch)
        print(f"Upserted batch {i // batch_size + 1}: {len(batch)} rows")

    print("-" * 72)
    print(f"Completed. Rows written: {written}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since-ts", type=str, default=None, help="ISO timestamp lower bound for source ts")
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