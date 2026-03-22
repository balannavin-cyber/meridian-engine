from __future__ import annotations

import math
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
# MERDIAN - Build Option Outcome Analytics V1
# ----------------------------------------------------------------------------
# Purpose:
#   Aggregate option_execution_outcomes_v1 into symbol/action analytics.
#
# Writes to:
#   public.option_outcome_analytics_v1
#
# Current grouping:
#   (symbol, signal_action)
#
# Notes:
#   - This is the first analytics layer.
#   - It assumes option_execution_outcomes_v1 already contains per-signal rows.
#   - If there are no outcome rows yet, the script exits cleanly.
# ============================================================================


if load_dotenv is not None:
    load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

REQUEST_TIMEOUT_SECONDS = 30
FETCH_LIMIT = 5000


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
    print("MERDIAN - Build Option Outcome Analytics V1")
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


def median_or_none(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(statistics.median(values))


def mean_or_none(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(statistics.mean(values))


def win_rate_pct(values: List[float]) -> Optional[float]:
    if not values:
        return None
    wins = sum(1 for x in values if x > 0)
    return (wins / len(values)) * 100.0


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


def fetch_outcome_rows() -> List[Dict[str, Any]]:
    rows = supabase_get(
        "option_execution_outcomes_v1",
        {
            "select": "*",
            "order": "signal_ts.desc",
            "limit": str(FETCH_LIMIT),
        },
    )
    print(f"[INFO] Outcome rows fetched: {len(rows)}")
    return rows


def build_analytics_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for row in rows:
        symbol = row.get("symbol")
        signal_action = row.get("signal_action")
        if not symbol or not signal_action:
            continue
        grouped[(str(symbol), str(signal_action))].append(row)

    output_rows: List[Dict[str, Any]] = []

    for (symbol, signal_action), items in grouped.items():
        move_15 = [x for x in (parse_float(r.get("move_15m_pct")) for r in items) if x is not None]
        move_30 = [x for x in (parse_float(r.get("move_30m_pct")) for r in items) if x is not None]
        move_60 = [x for x in (parse_float(r.get("move_60m_pct")) for r in items) if x is not None]

        mfe_60 = [x for x in (parse_float(r.get("mfe_60m")) for r in items) if x is not None]
        mae_60 = [x for x in (parse_float(r.get("mae_60m")) for r in items) if x is not None]
        time_profit = [
            x for x in (parse_float(r.get("time_to_first_profit_min")) for r in items)
            if x is not None
        ]

        analytics_row = {
            "symbol": symbol,
            "signal_action": signal_action,
            "sample_size": len(items),
            "win_rate_15m": win_rate_pct(move_15),
            "win_rate_30m": win_rate_pct(move_30),
            "win_rate_60m": win_rate_pct(move_60),
            "avg_move_15m_pct": mean_or_none(move_15),
            "avg_move_30m_pct": mean_or_none(move_30),
            "avg_move_60m_pct": mean_or_none(move_60),
            "median_move_15m_pct": median_or_none(move_15),
            "median_move_30m_pct": median_or_none(move_30),
            "median_move_60m_pct": median_or_none(move_60),
            "avg_mfe_60m": mean_or_none(mfe_60),
            "avg_mae_60m": mean_or_none(mae_60),
            "median_time_to_first_profit_min": median_or_none(time_profit),
            "computed_at": now_utc_iso(),
            "source": "build_option_outcome_analytics_v1",
            "raw": {
                "signals_in_group": len(items),
                "count_move_15m_pct": len(move_15),
                "count_move_30m_pct": len(move_30),
                "count_move_60m_pct": len(move_60),
                "count_mfe_60m": len(mfe_60),
                "count_mae_60m": len(mae_60),
                "count_time_to_first_profit_min": len(time_profit),
            },
        }

        output_rows.append(analytics_row)

        print(
            f"[ROW] symbol={symbol} | action={signal_action} | sample_size={len(items)}"
        )

    return output_rows


def main() -> int:
    print_header()

    require_env("SUPABASE_URL", SUPABASE_URL)
    require_env("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_SERVICE_ROLE_KEY)

    outcome_rows = fetch_outcome_rows()
    if not outcome_rows:
        print("[DONE] No option execution outcome rows exist yet.")
        return 0

    analytics_rows = build_analytics_rows(outcome_rows)
    print(f"[INFO] Analytics rows built: {len(analytics_rows)}")

    if not analytics_rows:
        print("[DONE] No analytics rows to upsert.")
        return 0

    supabase_post_upsert(
        "option_outcome_analytics_v1",
        analytics_rows,
        on_conflict="symbol,signal_action",
    )
    print(f"[DONE] Rows upserted: {len(analytics_rows)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise