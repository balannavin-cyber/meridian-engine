import json
import os
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.supabase_client import SupabaseClient


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LABEL_HORIZON = "NEXT_5_SNAPSHOTS"
FORWARD_UNIQUE_SNAPSHOTS = 5


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _load_env_from_file() -> Dict[str, str]:
    env_path = BASE_DIR / ".env"
    values: Dict[str, str] = {}

    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line:
            continue
        if line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def _get_supabase_credentials() -> Dict[str, str]:
    file_env = _load_env_from_file()

    supabase_url = os.getenv("SUPABASE_URL") or file_env.get("SUPABASE_URL") or ""
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or file_env.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    anon_key = os.getenv("SUPABASE_ANON_KEY") or file_env.get("SUPABASE_ANON_KEY") or ""

    api_key = service_key or anon_key

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL not found in environment or .env")

    if not api_key:
        raise RuntimeError(
            "Need SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in environment or .env"
        )

    return {
        "url": supabase_url.rstrip("/"),
        "api_key": api_key,
    }


def _insert_data_quality_event(
    event_type: str,
    severity: str,
    symbol: Optional[str],
    ticker: Optional[str],
    pipeline: str,
    detail: Dict[str, Any],
    notes: str,
) -> None:
    creds = _get_supabase_credentials()

    url = f"{creds['url']}/rest/v1/data_quality_events"
    headers = {
        "apikey": creds["api_key"],
        "Authorization": f"Bearer {creds['api_key']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    payload = [{
        "event_ts": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": severity,
        "symbol": symbol,
        "ticker": ticker,
        "pipeline": pipeline,
        "detail": detail,
        "resolved": False,
        "notes": notes,
    }]

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()


def _fetch_recent_signals(sb: SupabaseClient, limit: int = 200) -> List[Dict[str, Any]]:
    return sb.select(
        table="signal_snapshots",
        order="created_at.desc",
        limit=limit,
    )


def _already_labeled_ids(sb: SupabaseClient, horizon: str) -> set:
    rows = sb.select(
        table="signal_labels",
        filters={"label_horizon": f"eq.{horizon}"},
        order="created_at.desc",
        limit=5000,
    )
    return {
        row.get("signal_snapshot_id")
        for row in rows
        if row.get("signal_snapshot_id") is not None
    }


def _fetch_future_snapshots(
    sb: SupabaseClient,
    symbol: str,
    signal_ts: Any,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    return sb.select(
        table="option_chain_snapshots",
        filters={
            "symbol": f"eq.{symbol}",
            "ts": f"gt.{signal_ts}",
        },
        order="ts.asc",
        limit=limit,
    )


def _dedupe_snapshot_path(rows: List[Dict[str, Any]], max_unique_snapshots: int) -> List[Dict[str, Any]]:
    seen = set()
    path = []

    for row in rows:
        ts = row.get("ts")
        if ts in seen:
            continue
        seen.add(ts)
        path.append(row)

        if len(path) >= max_unique_snapshots:
            break

    return path


def _raw_move_pct(entry_spot: float, future_spot: float) -> float:
    return ((future_spot - entry_spot) / entry_spot) * 100.0


def _compute_excursions(
    entry_spot: Optional[float],
    path_rows: List[Dict[str, Any]],
) -> Dict[str, Optional[float]]:
    if entry_spot is None or entry_spot == 0 or not path_rows:
        return {
            "max_favorable_move_pct": None,
            "max_adverse_move_pct": None,
        }

    raw_moves: List[float] = []

    for row in path_rows:
        spot = _to_float(row.get("spot"))
        if spot is None:
            continue
        raw_moves.append(_raw_move_pct(entry_spot, spot))

    if not raw_moves:
        return {
            "max_favorable_move_pct": None,
            "max_adverse_move_pct": None,
        }

    return {
        "max_favorable_move_pct": round(max(raw_moves), 4),
        "max_adverse_move_pct": round(min(raw_moves), 4),
    }


def _compute_label(
    action: Optional[str],
    entry_spot: Optional[float],
    exit_spot: Optional[float],
) -> Dict[str, Any]:
    if action is None or entry_spot is None or exit_spot is None or entry_spot == 0:
        return {
            "spot_return_pct": None,
            "label": "UNRESOLVED",
            "label_score": None,
            "notes": "Missing action, entry_spot, or exit_spot",
        }

    spot_return_pct = _raw_move_pct(entry_spot, exit_spot)

    if action == "BUY_CE":
        directional_return = spot_return_pct
    elif action == "BUY_PE":
        directional_return = -spot_return_pct
    elif action == "DO_NOTHING":
        directional_return = 0.0
    else:
        directional_return = 0.0

    if action == "DO_NOTHING":
        if abs(spot_return_pct) >= 0.75:
            label = "SKIPPED_MOVE"
            label_score = -0.5
            notes = "No-trade signal skipped a meaningful move over next 5 snapshots"
        else:
            label = "NEUTRAL"
            label_score = 0.0
            notes = "No-trade signal and no meaningful follow-through over next 5 snapshots"
    else:
        if directional_return >= 0.75:
            label = "GOOD"
            label_score = 1.0
            notes = "Signal direction aligned with move over next 5 snapshots"
        elif directional_return <= -0.75:
            label = "BAD"
            label_score = -1.0
            notes = "Signal direction opposed move over next 5 snapshots"
        else:
            label = "NEUTRAL"
            label_score = 0.0
            notes = "Move too small for a strong label over next 5 snapshots"

    return {
        "spot_return_pct": round(spot_return_pct, 4),
        "label": label,
        "label_score": label_score,
        "notes": notes,
    }


def main() -> None:
    print("=" * 72)
    print("Gamma Engine - Label Signal Outcomes")
    print("=" * 72)
    print(f"Horizon: {LABEL_HORIZON}")
    print(f"Forward unique snapshots: {FORWARD_UNIQUE_SNAPSHOTS}")
    print("-" * 72)

    sb = SupabaseClient()

    recent_signals = _fetch_recent_signals(sb, limit=200)
    labeled_ids = _already_labeled_ids(sb, LABEL_HORIZON)

    print(f"Recent signals fetched: {len(recent_signals)}")
    print(f"Already labeled for {LABEL_HORIZON}: {len(labeled_ids)}")

    rows_to_insert: List[Dict[str, Any]] = []
    skipped_existing = 0
    skipped_unresolved = 0
    unresolved_logged = 0
    sparse_logged = 0

    for signal in recent_signals:
        signal_id = signal.get("id")
        if signal_id in labeled_ids:
            skipped_existing += 1
            continue

        symbol = signal.get("symbol")
        action = signal.get("action")
        entry_ts = signal.get("ts")
        entry_spot = _to_float(signal.get("spot"))
        expiry_date = signal.get("expiry_date")

        if not symbol or entry_ts is None or entry_spot is None:
            skipped_unresolved += 1
            _insert_data_quality_event(
                event_type="unresolved_label",
                severity="warning",
                symbol=symbol,
                ticker=symbol,
                pipeline="label_signal_outcomes",
                detail={
                    "reason": "missing_symbol_or_entry_data",
                    "signal_snapshot_id": signal_id,
                    "label_horizon": LABEL_HORIZON,
                },
                notes="Could not label signal due to missing symbol or entry data",
            )
            unresolved_logged += 1
            continue

        future_rows_raw = _fetch_future_snapshots(sb, symbol, entry_ts, limit=500)
        future_rows = _dedupe_snapshot_path(future_rows_raw, FORWARD_UNIQUE_SNAPSHOTS)

        if not future_rows:
            skipped_unresolved += 1
            _insert_data_quality_event(
                event_type="unresolved_label",
                severity="warning",
                symbol=symbol,
                ticker=symbol,
                pipeline="label_signal_outcomes",
                detail={
                    "reason": "no_future_snapshots",
                    "signal_snapshot_id": signal_id,
                    "label_horizon": LABEL_HORIZON,
                    "entry_ts": entry_ts,
                },
                notes="Could not label signal because no future option-chain snapshots were found",
            )
            unresolved_logged += 1
            continue

        if len(future_rows) < FORWARD_UNIQUE_SNAPSHOTS:
            _insert_data_quality_event(
                event_type="sparse_forward_path",
                severity="warning",
                symbol=symbol,
                ticker=symbol,
                pipeline="label_signal_outcomes",
                detail={
                    "signal_snapshot_id": signal_id,
                    "label_horizon": LABEL_HORIZON,
                    "expected_unique_snapshots": FORWARD_UNIQUE_SNAPSHOTS,
                    "actual_unique_snapshots": len(future_rows),
                    "entry_ts": entry_ts,
                },
                notes="Future path shorter than expected for excursion-based labeling",
            )
            sparse_logged += 1

        final_exit = future_rows[-1]
        exit_ts = final_exit.get("ts")
        exit_spot = _to_float(final_exit.get("spot"))

        if exit_spot is None:
            skipped_unresolved += 1
            _insert_data_quality_event(
                event_type="unresolved_label",
                severity="warning",
                symbol=symbol,
                ticker=symbol,
                pipeline="label_signal_outcomes",
                detail={
                    "reason": "missing_exit_spot",
                    "signal_snapshot_id": signal_id,
                    "label_horizon": LABEL_HORIZON,
                    "entry_ts": entry_ts,
                },
                notes="Could not label signal because exit spot was missing",
            )
            unresolved_logged += 1
            continue

        computed = _compute_label(action, entry_spot, exit_spot)
        excursions = _compute_excursions(entry_spot, future_rows)

        label_row = {
            "signal_snapshot_id": signal_id,
            "symbol": symbol,
            "label_horizon": LABEL_HORIZON,
            "entry_ts": entry_ts,
            "expiry_date": expiry_date,
            "entry_spot": entry_spot,
            "exit_ts": exit_ts,
            "exit_spot": exit_spot,
            "spot_return_pct": computed["spot_return_pct"],
            "max_favorable_move_pct": excursions["max_favorable_move_pct"],
            "max_adverse_move_pct": excursions["max_adverse_move_pct"],
            "label": computed["label"],
            "label_score": computed["label_score"],
            "notes": computed["notes"],
        }

        rows_to_insert.append(label_row)

    print(f"Rows prepared for insert: {len(rows_to_insert)}")
    print(f"Skipped already labeled: {skipped_existing}")
    print(f"Skipped unresolved: {skipped_unresolved}")
    print(f"Unresolved events logged: {unresolved_logged}")
    print(f"Sparse-path events logged: {sparse_logged}")

    if rows_to_insert:
        inserted = sb.insert("signal_labels", rows_to_insert)
        inserted_count = len(inserted) if isinstance(inserted, list) else 1
    else:
        inserted_count = 0

    print("-" * 72)
    print(f"Inserted signal_labels rows returned by Supabase: {inserted_count}")

    summary = {
        "horizon": LABEL_HORIZON,
        "forward_unique_snapshots": FORWARD_UNIQUE_SNAPSHOTS,
        "recent_signals_fetched": len(recent_signals),
        "rows_prepared": len(rows_to_insert),
        "skipped_existing": skipped_existing,
        "skipped_unresolved": skipped_unresolved,
        "unresolved_logged": unresolved_logged,
        "sparse_logged": sparse_logged,
        "inserted_count": inserted_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    summary_file = DATA_DIR / "latest_signal_label_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"Summary saved to: {summary_file}")
    print("LABEL SIGNAL OUTCOMES COMPLETED")


if __name__ == "__main__":
    main()