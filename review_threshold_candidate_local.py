import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from core.supabase_client import SupabaseClient


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "signal_threshold"
MODEL_VERSION = "v1"

MIN_LABEL_SAMPLE_FOR_REVIEW = 30
MIN_AVG_SCORE_FOR_PROMOTION = 0.10


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _safe_avg(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


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
            "No Supabase API key found. Need SUPABASE_SERVICE_ROLE_KEY "
            "or SUPABASE_ANON_KEY in environment or .env"
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


def fetch_signal_labels(sb: SupabaseClient) -> List[Dict]:
    return sb.select(
        table="signal_labels",
        order="created_at.desc",
        limit=5000,
    )


def evaluate(rows: List[Dict]) -> Dict[str, Any]:
    overall = {
        "count": 0,
        "labels": defaultdict(int),
        "returns": [],
        "scores": [],
    }

    by_symbol = defaultdict(lambda: {
        "count": 0,
        "labels": defaultdict(int),
        "returns": [],
        "scores": [],
    })

    by_horizon = defaultdict(lambda: {
        "count": 0,
        "labels": defaultdict(int),
        "returns": [],
        "scores": [],
    })

    for r in rows:
        symbol = r.get("symbol")
        horizon = r.get("label_horizon")
        label = r.get("label")

        ret = _to_float(r.get("spot_return_pct"))
        score = _to_float(r.get("label_score"))

        overall["count"] += 1
        overall["labels"][label] += 1

        if ret is not None:
            overall["returns"].append(ret)

        if score is not None:
            overall["scores"].append(score)

        s = by_symbol[symbol]
        s["count"] += 1
        s["labels"][label] += 1
        if ret is not None:
            s["returns"].append(ret)
        if score is not None:
            s["scores"].append(score)

        h = by_horizon[horizon]
        h["count"] += 1
        h["labels"][label] += 1
        if ret is not None:
            h["returns"].append(ret)
        if score is not None:
            h["scores"].append(score)

    def finalize(bucket: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "count": bucket["count"],
            "labels": dict(bucket["labels"]),
            "avg_return": _safe_avg(bucket["returns"]),
            "avg_score": _safe_avg(bucket["scores"]),
        }

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "overall": finalize(overall),
        "by_symbol": {},
        "by_horizon": {},
    }

    for k, v in by_symbol.items():
        result["by_symbol"][k] = finalize(v)

    for k, v in by_horizon.items():
        result["by_horizon"][k] = finalize(v)

    return result


def assess_promotability(summary: Dict[str, Any]) -> Dict[str, Any]:
    overall = summary.get("overall", {})
    count = int(overall.get("count") or 0)
    avg_score = _to_float(overall.get("avg_score"))
    labels = overall.get("labels", {}) or {}

    good_count = int(labels.get("GOOD", 0))
    bad_count = int(labels.get("BAD", 0))
    skipped_count = int(labels.get("SKIPPED_MOVE", 0))
    neutral_count = int(labels.get("NEUTRAL", 0))

    reasons: List[str] = []

    if count < MIN_LABEL_SAMPLE_FOR_REVIEW:
        reasons.append(f"label sample too small: {count} < {MIN_LABEL_SAMPLE_FOR_REVIEW}")

    if avg_score is None:
        reasons.append("avg_score is missing")
    elif avg_score < MIN_AVG_SCORE_FOR_PROMOTION:
        reasons.append(f"avg_score too low: {avg_score} < {MIN_AVG_SCORE_FOR_PROMOTION}")

    if good_count == 0:
        reasons.append("no GOOD labels observed")

    promotable = len(reasons) == 0

    return {
        "promotable": promotable,
        "reasons": reasons,
        "metrics": {
            "count": count,
            "avg_score": avg_score,
            "good_count": good_count,
            "bad_count": bad_count,
            "neutral_count": neutral_count,
            "skipped_move_count": skipped_count,
        }
    }


def update_model_registry_via_rest(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    creds = _get_supabase_credentials()

    url = (
        f"{creds['url']}/rest/v1/model_registry"
        f"?model_name=eq.{MODEL_NAME}&version=eq.{MODEL_VERSION}"
    )

    headers = {
        "apikey": creds["api_key"],
        "Authorization": f"Bearer {creds['api_key']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    payload = {
        "eval_summary": summary
    }

    response = requests.patch(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    try:
        return response.json()
    except Exception:
        return []


def main() -> None:
    print("=" * 70)
    print("Gamma Engine - Threshold Candidate Review")
    print("=" * 70)

    sb = SupabaseClient()

    rows = fetch_signal_labels(sb)
    print(f"Signal labels fetched: {len(rows)}")

    summary = evaluate(rows)
    promotion_assessment = assess_promotability(summary)
    summary["promotion_assessment"] = promotion_assessment

    print("-" * 70)
    print("Evaluation Summary")
    print(json.dumps(summary, indent=2))

    out_file = DATA_DIR / "threshold_candidate_review.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("-" * 70)
    print(f"Saved local review file: {out_file}")

    metrics = promotion_assessment["metrics"]
    reasons = promotion_assessment["reasons"]

    low_sample_logged = 0
    not_promotable_logged = 0

    if metrics["count"] < MIN_LABEL_SAMPLE_FOR_REVIEW:
        _insert_data_quality_event(
            event_type="low_label_sample",
            severity="warning",
            symbol=None,
            ticker=None,
            pipeline="threshold_review",
            detail={
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "actual_label_count": metrics["count"],
                "minimum_required": MIN_LABEL_SAMPLE_FOR_REVIEW,
            },
            notes="Threshold review sample is too small for promotion consideration",
        )
        low_sample_logged += 1

    if not promotion_assessment["promotable"]:
        _insert_data_quality_event(
            event_type="candidate_not_promotable",
            severity="warning",
            symbol=None,
            ticker=None,
            pipeline="threshold_review",
            detail={
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "reasons": reasons,
                "metrics": metrics,
            },
            notes="Candidate model failed promotion checks",
        )
        not_promotable_logged += 1

    updated_rows = update_model_registry_via_rest(summary)

    print("-" * 70)
    print(f"Low-sample events logged: {low_sample_logged}")
    print(f"Not-promotable events logged: {not_promotable_logged}")
    print(f"model_registry eval_summary updated | rows returned: {len(updated_rows)}")
    print("THRESHOLD REVIEW COMPLETED")


if __name__ == "__main__":
    main()