import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.supabase_client import SupabaseClient


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _fetch_signal_labels(sb: SupabaseClient, limit: int = 5000) -> List[Dict[str, Any]]:
    return sb.select(
        table="signal_labels",
        order="created_at.desc",
        limit=limit,
    )


def _safe_avg(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _init_bucket() -> Dict[str, Any]:
    return {
        "count": 0,
        "labels": defaultdict(int),
        "spot_return_values": [],
        "label_score_values": [],
        "max_favorable_values": [],
        "max_adverse_values": [],
    }


def _finalize_bucket(bucket: Dict[str, Any]) -> Dict[str, Any]:
    labels_dict = dict(sorted(bucket["labels"].items(), key=lambda x: x[0]))

    return {
        "count": bucket["count"],
        "labels": labels_dict,
        "avg_spot_return_pct": _safe_avg(bucket["spot_return_values"]),
        "avg_label_score": _safe_avg(bucket["label_score_values"]),
        "avg_max_favorable_move_pct": _safe_avg(bucket["max_favorable_values"]),
        "avg_max_adverse_move_pct": _safe_avg(bucket["max_adverse_values"]),
    }


def main() -> None:
    print("=" * 72)
    print("Gamma Engine - Evaluate Signal Labels")
    print("=" * 72)

    sb = SupabaseClient()
    rows = _fetch_signal_labels(sb, limit=5000)

    print(f"Signal labels fetched: {len(rows)}")
    print("-" * 72)

    overall_bucket = _init_bucket()
    by_horizon: Dict[str, Dict[str, Any]] = defaultdict(_init_bucket)
    by_symbol: Dict[str, Dict[str, Any]] = defaultdict(_init_bucket)
    by_horizon_symbol: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(_init_bucket))

    for row in rows:
        horizon = row.get("label_horizon") or "UNKNOWN"
        symbol = row.get("symbol") or "UNKNOWN"
        label = row.get("label") or "UNKNOWN"

        spot_return_pct = _to_float(row.get("spot_return_pct"))
        label_score = _to_float(row.get("label_score"))
        max_favorable = _to_float(row.get("max_favorable_move_pct"))
        max_adverse = _to_float(row.get("max_adverse_move_pct"))

        for bucket in (
            overall_bucket,
            by_horizon[horizon],
            by_symbol[symbol],
            by_horizon_symbol[horizon][symbol],
        ):
            bucket["count"] += 1
            bucket["labels"][label] += 1

            if spot_return_pct is not None:
                bucket["spot_return_values"].append(spot_return_pct)
            if label_score is not None:
                bucket["label_score_values"].append(label_score)
            if max_favorable is not None:
                bucket["max_favorable_values"].append(max_favorable)
            if max_adverse is not None:
                bucket["max_adverse_values"].append(max_adverse)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": _finalize_bucket(overall_bucket),
        "by_horizon": {},
        "by_symbol": {},
        "by_horizon_symbol": {},
    }

    for horizon, bucket in sorted(by_horizon.items()):
        summary["by_horizon"][horizon] = _finalize_bucket(bucket)

    for symbol, bucket in sorted(by_symbol.items()):
        summary["by_symbol"][symbol] = _finalize_bucket(bucket)

    for horizon, symbol_map in sorted(by_horizon_symbol.items()):
        summary["by_horizon_symbol"][horizon] = {}
        for symbol, bucket in sorted(symbol_map.items()):
            summary["by_horizon_symbol"][horizon][symbol] = _finalize_bucket(bucket)

    print("OVERALL SUMMARY")
    print(json.dumps(summary["overall"], indent=2))

    print("-" * 72)
    print("BY HORIZON")
    print(json.dumps(summary["by_horizon"], indent=2))

    print("-" * 72)
    print("BY SYMBOL")
    print(json.dumps(summary["by_symbol"], indent=2))

    out_file = DATA_DIR / "signal_label_evaluation_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("-" * 72)
    print(f"Summary saved to: {out_file}")
    print("EVALUATE SIGNAL LABELS COMPLETED")


if __name__ == "__main__":
    main()