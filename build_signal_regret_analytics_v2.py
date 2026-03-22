from __future__ import annotations

import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# ============================================================================
# MERDIAN - Build Signal Regret Analytics V2
# ----------------------------------------------------------------------------
# Purpose:
#   Aggregate deduped regret rows from signal_regret_log_v1_latest
#   into analytics by (symbol, direction_bias).
#
# Reads from:
#   public.signal_regret_log_v1_latest
#
# Writes to:
#   public.signal_regret_analytics_v2
#
# Improvements vs V1:
#   - Uses deduped regret base
#   - Adds horizon coverage percentages
# ============================================================================


if load_dotenv is not None:
    load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

REQUEST_TIMEOUT_SECONDS = 30
FETCH_LIMIT = 10000


class ConfigError(RuntimeError):
    pass


class SupabaseError(RuntimeError):
    pass


def require_env(name: str, value: str) -> str:
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def print_header() -> None:
    print("=" * 72)
    print("MERDIAN - Build Signal Regret Analytics V2")
    print("=" * 72)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def mean_or_none(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(statistics.mean(values))


def median_or_none(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(statistics.median(values))


def rate_for_label(labels: List[str], target: str) -> Optional[float]:
    if not labels:
        return None
    count = sum(1 for x in labels if x == target)
    return (count / len(labels)) * 100.0


def pct(part: int, whole: int) -> Optional[float]:
    if whole <= 0:
        return None
    return (part / whole) * 100.0


def get_supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def supabase_get(table: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.get(
        url,
        headers=get_supabase_headers(),
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise SupabaseError(
            f"GET {table} failed | status={response.status_code} | body={response.text}"
        )
    data = response.json()
    if not isinstance(data, list):
        raise SupabaseError(f"GET {table} returned unexpected payload: {data}")
    return data


def supabase_post_upsert(table: str, rows: List[Dict[str, Any]], on_conflict: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = get_supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates"
    response = requests.post(
        url,
        headers=headers,
        params={"on_conflict": on_conflict},
        json=rows,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise SupabaseError(
            f"POST upsert {table} failed | status={response.status_code} | body={response.text}"
        )


def fetch_regret_rows_latest() -> List[Dict[str, Any]]:
    rows = supabase_get(
        "signal_regret_log_v1_latest",
        {
            "select": "*",
            "order": "signal_ts.desc",
            "limit": str(FETCH_LIMIT),
        },
    )
    print(f"[INFO] Deduped regret rows fetched: {len(rows)}")
    return rows


def build_analytics_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for row in rows:
        symbol = row.get("symbol")
        direction_bias = row.get("direction_bias")
        if not symbol:
            continue
        bias = str(direction_bias).strip().upper() if direction_bias is not None else "UNKNOWN"
        grouped[(str(symbol), bias)].append(row)

    output_rows: List[Dict[str, Any]] = []

    for (symbol, direction_bias), items in grouped.items():
        confidence_scores = [
            x for x in (parse_float(r.get("confidence_score")) for r in items)
            if x is not None
        ]

        spot_15 = [x for x in (parse_float(r.get("spot_move_15m_pct")) for r in items) if x is not None]
        spot_30 = [x for x in (parse_float(r.get("spot_move_30m_pct")) for r in items) if x is not None]
        spot_60 = [x for x in (parse_float(r.get("spot_move_60m_pct")) for r in items) if x is not None]

        fut_15 = [x for x in (parse_float(r.get("futures_move_15m_pct")) for r in items) if x is not None]
        fut_30 = [x for x in (parse_float(r.get("futures_move_30m_pct")) for r in items) if x is not None]
        fut_60 = [x for x in (parse_float(r.get("futures_move_60m_pct")) for r in items) if x is not None]

        labels_15 = [str(x) for x in (r.get("regret_label_15m") for r in items) if x is not None and str(x).strip()]
        labels_30 = [str(x) for x in (r.get("regret_label_30m") for r in items) if x is not None and str(x).strip()]
        labels_60 = [str(x) for x in (r.get("regret_label_60m") for r in items) if x is not None and str(x).strip()]

        analytics_row = {
            "symbol": symbol,
            "direction_bias": direction_bias,
            "sample_size": len(items),

            "justified_no_trade_rate_15m": rate_for_label(labels_15, "JUSTIFIED_NO_TRADE"),
            "missed_bearish_rate_15m": rate_for_label(labels_15, "MISSED_BEARISH"),
            "missed_bullish_rate_15m": rate_for_label(labels_15, "MISSED_BULLISH"),

            "justified_no_trade_rate_30m": rate_for_label(labels_30, "JUSTIFIED_NO_TRADE"),
            "missed_bearish_rate_30m": rate_for_label(labels_30, "MISSED_BEARISH"),
            "missed_bullish_rate_30m": rate_for_label(labels_30, "MISSED_BULLISH"),

            "justified_no_trade_rate_60m": rate_for_label(labels_60, "JUSTIFIED_NO_TRADE"),
            "missed_bearish_rate_60m": rate_for_label(labels_60, "MISSED_BEARISH"),
            "missed_bullish_rate_60m": rate_for_label(labels_60, "MISSED_BULLISH"),

            "avg_confidence_score": mean_or_none(confidence_scores),

            "avg_spot_move_15m_pct": mean_or_none(spot_15),
            "avg_spot_move_30m_pct": mean_or_none(spot_30),
            "avg_spot_move_60m_pct": mean_or_none(spot_60),

            "median_spot_move_15m_pct": median_or_none(spot_15),
            "median_spot_move_30m_pct": median_or_none(spot_30),
            "median_spot_move_60m_pct": median_or_none(spot_60),

            "avg_futures_move_15m_pct": mean_or_none(fut_15),
            "avg_futures_move_30m_pct": mean_or_none(fut_30),
            "avg_futures_move_60m_pct": mean_or_none(fut_60),

            "median_futures_move_15m_pct": median_or_none(fut_15),
            "median_futures_move_30m_pct": median_or_none(fut_30),
            "median_futures_move_60m_pct": median_or_none(fut_60),

            "coverage_15m_pct": pct(len(labels_15), len(items)),
            "coverage_30m_pct": pct(len(labels_30), len(items)),
            "coverage_60m_pct": pct(len(labels_60), len(items)),

            "computed_at": now_utc_iso(),
            "source": "build_signal_regret_analytics_v2",
            "raw": {
                "signals_in_group": len(items),
                "count_confidence_score": len(confidence_scores),
                "count_spot_move_15m_pct": len(spot_15),
                "count_spot_move_30m_pct": len(spot_30),
                "count_spot_move_60m_pct": len(spot_60),
                "count_futures_move_15m_pct": len(fut_15),
                "count_futures_move_30m_pct": len(fut_30),
                "count_futures_move_60m_pct": len(fut_60),
                "count_regret_label_15m": len(labels_15),
                "count_regret_label_30m": len(labels_30),
                "count_regret_label_60m": len(labels_60),
            },
        }

        output_rows.append(analytics_row)

        print(
            f"[ROW] symbol={symbol} | direction_bias={direction_bias} | sample_size={len(items)}"
        )

    return output_rows


def main() -> int:
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)

    rows = fetch_regret_rows_latest()
    if not rows:
        print("[DONE] No deduped regret rows exist yet.")
        return 0

    analytics_rows = build_analytics_rows(rows)
    print(f"[INFO] Analytics rows built: {len(analytics_rows)}")

    if not analytics_rows:
        print("[DONE] No analytics rows to upsert.")
        return 0

    supabase_post_upsert(
        "signal_regret_analytics_v2",
        analytics_rows,
        on_conflict="symbol,direction_bias",
    )
    print(f"[DONE] Rows upserted: {len(analytics_rows)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise