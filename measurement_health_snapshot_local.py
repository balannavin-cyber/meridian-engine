from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


def print_banner(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()
    if required and not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


class SupabaseRestClient:
    def __init__(self) -> None:
        load_dotenv(ENV_FILE, override=True)
        self.base_url = get_env("SUPABASE_URL").rstrip("/")
        self.api_key = get_env("SUPABASE_SERVICE_ROLE_KEY")

        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def select(
        self,
        table: str,
        select_cols: str = "*",
        filters: Dict[str, str] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/{table}"
        params: Dict[str, str] = {"select": select_cols}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = str(limit)

        response = requests.get(url, headers=self.headers, params=params, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Supabase SELECT failed | table={table} | HTTP {response.status_code} | response={response.text}"
            )
        return response.json()

    def insert(self, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/v1/{table}"
        headers = dict(self.headers)
        headers["Prefer"] = "return=representation"

        response = requests.post(url, headers=headers, json=[row], timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Supabase INSERT failed | table={table} | HTTP {response.status_code} | response={response.text}"
            )

        data = response.json()
        if not data:
            raise RuntimeError("Supabase INSERT returned no rows")
        return data[0]


def age_minutes(ts_value: Any) -> Optional[float]:
    dt = parse_dt(ts_value)
    if dt is None:
        return None
    delta = utc_now() - dt
    return round(delta.total_seconds() / 60.0, 2)


def freshness_status(minutes: Optional[float], green_max: float, yellow_max: float) -> str:
    if minutes is None:
        return "NO_TS"
    if minutes <= green_max:
        return "FRESH"
    if minutes <= yellow_max:
        return "STALE"
    return "CRITICAL"


def latest_row(client: SupabaseRestClient, table: str, order: str = "ts.desc") -> Optional[Dict[str, Any]]:
    rows = client.select(table=table, select_cols="*", order=order, limit=1)
    return rows[0] if rows else None


def row_count(client: SupabaseRestClient, table: str) -> int:
    rows = client.select(table=table, select_cols="id", limit=100000)
    return len(rows)


def latest_rows_by_symbol(client: SupabaseRestClient, table: str, symbols: List[str], order: str = "ts.desc") -> Dict[str, Optional[Dict[str, Any]]]:
    out: Dict[str, Optional[Dict[str, Any]]] = {}
    for symbol in symbols:
        rows = client.select(
            table=table,
            select_cols="*",
            filters={"symbol": f"eq.{symbol}"},
            order=order,
            limit=1,
        )
        out[symbol] = rows[0] if rows else None
    return out


def build_volatility_status(client: SupabaseRestClient) -> Dict[str, Any]:
    latest = latest_rows_by_symbol(client, "volatility_snapshots", ["NIFTY", "SENSEX"])
    summary = {}
    worst = "FRESH"

    for symbol, row in latest.items():
        ts = row.get("ts") if row else None
        age = age_minutes(ts)
        status = freshness_status(age, green_max=15, yellow_max=120)
        if status == "CRITICAL":
            worst = "CRITICAL"
        elif status == "STALE" and worst != "CRITICAL":
            worst = "STALE"

        summary[symbol] = {
            "latest_ts": ts,
            "age_minutes": age,
            "status": status,
            "vix_percentile": row.get("vix_percentile") if row else None,
            "vix_regime": row.get("vix_regime") if row else None,
            "atm_iv_avg": row.get("atm_iv_avg") if row else None,
        }

    return {"module_status": worst, "symbols": summary}


def build_wcb_status(client: SupabaseRestClient) -> Dict[str, Any]:
    latest = latest_row(client, "weighted_constituent_breadth_snapshots", order="ts.desc,created_at.desc")
    ts = latest.get("ts") if latest else None
    age = age_minutes(ts)
    status = freshness_status(age, green_max=30, yellow_max=1440)

    return {
        "module_status": status,
        "latest_ts": ts,
        "age_minutes": age,
        "wcb_score": latest.get("wcb_score") if latest else None,
        "wcb_regime": latest.get("wcb_regime") if latest else None,
        "constituent_count": latest.get("constituent_count") if latest else None,
    }


def build_futures_status(client: SupabaseRestClient) -> Dict[str, Any]:
    latest = latest_rows_by_symbol(client, "index_futures_snapshots", ["NIFTY", "SENSEX"])
    summary = {}
    worst = "FRESH"

    for symbol, row in latest.items():
        ts = row.get("ts") if row else None
        age = age_minutes(ts)
        status = freshness_status(age, green_max=10, yellow_max=60)
        if status == "CRITICAL":
            worst = "CRITICAL"
        elif status == "STALE" and worst != "CRITICAL":
            worst = "STALE"

        summary[symbol] = {
            "latest_ts": ts,
            "age_minutes": age,
            "status": status,
            "futures_price": row.get("futures_price") if row else None,
        }

    return {"module_status": worst, "symbols": summary}


def build_gamma_status(client: SupabaseRestClient) -> Dict[str, Any]:
    latest = latest_rows_by_symbol(client, "gamma_metrics", ["NIFTY", "SENSEX"])
    summary = {}
    worst = "FRESH"

    for symbol, row in latest.items():
        ts = row.get("ts") if row else None
        age = age_minutes(ts)
        status = freshness_status(age, green_max=15, yellow_max=120)
        if status == "CRITICAL":
            worst = "CRITICAL"
        elif status == "STALE" and worst != "CRITICAL":
            worst = "STALE"

        summary[symbol] = {
            "latest_ts": ts,
            "age_minutes": age,
            "status": status,
            "regime": row.get("regime") if row else None,
            "flip_distance_pct": row.get("flip_distance_pct") if row else None,
            "gamma_concentration": row.get("gamma_concentration") if row else None,
        }

    counts = client.select(
        table="gamma_metrics",
        select_cols="symbol,flip_distance,flip_distance_pct",
        limit=100000,
    )

    by_symbol: Dict[str, Dict[str, int]] = {
        "NIFTY": {"rows": 0, "rows_with_flip_distance": 0, "rows_with_flip_distance_pct": 0},
        "SENSEX": {"rows": 0, "rows_with_flip_distance": 0, "rows_with_flip_distance_pct": 0},
    }

    for row in counts:
        symbol = row.get("symbol")
        if symbol not in by_symbol:
            continue
        by_symbol[symbol]["rows"] += 1
        if row.get("flip_distance") is not None:
            by_symbol[symbol]["rows_with_flip_distance"] += 1
        if row.get("flip_distance_pct") is not None:
            by_symbol[symbol]["rows_with_flip_distance_pct"] += 1

    return {"module_status": worst, "symbols": summary, "coverage": by_symbol}


def build_momentum_status(client: SupabaseRestClient) -> Dict[str, Any]:
    latest = latest_rows_by_symbol(client, "momentum_snapshots", ["NIFTY", "SENSEX"])
    summary = {}
    worst = "FRESH"

    for symbol, row in latest.items():
        ts = row.get("ts") if row else None
        age = age_minutes(ts)
        status = freshness_status(age, green_max=10, yellow_max=60)
        if status == "CRITICAL":
            worst = "CRITICAL"
        elif status == "STALE" and worst != "CRITICAL":
            worst = "STALE"

        summary[symbol] = {
            "latest_ts": ts,
            "age_minutes": age,
            "status": status,
            "ret_session": row.get("ret_session") if row else None,
            "ret_30m": row.get("ret_30m") if row else None,
            "ret_60m": row.get("ret_60m") if row else None,
            "momentum_regime": row.get("momentum_regime") if row else None,
            "source": row.get("source") if row else None,
        }

    counts = client.select(
        table="momentum_snapshots",
        select_cols="symbol,ret_session,ret_30m,ret_60m,momentum_regime",
        limit=100000,
    )

    by_symbol: Dict[str, Dict[str, int]] = {
        "NIFTY": {"rows": 0, "rows_with_ret_session": 0, "rows_with_ret_30m": 0, "rows_with_ret_60m": 0, "rows_with_momentum_regime": 0},
        "SENSEX": {"rows": 0, "rows_with_ret_session": 0, "rows_with_ret_30m": 0, "rows_with_ret_60m": 0, "rows_with_momentum_regime": 0},
    }

    for row in counts:
        symbol = row.get("symbol")
        if symbol not in by_symbol:
            continue
        by_symbol[symbol]["rows"] += 1
        if row.get("ret_session") is not None:
            by_symbol[symbol]["rows_with_ret_session"] += 1
        if row.get("ret_30m") is not None:
            by_symbol[symbol]["rows_with_ret_30m"] += 1
        if row.get("ret_60m") is not None:
            by_symbol[symbol]["rows_with_ret_60m"] += 1
        if row.get("momentum_regime") is not None:
            by_symbol[symbol]["rows_with_momentum_regime"] += 1

    return {"module_status": worst, "symbols": summary, "coverage": by_symbol}


def build_regret_log_status(client: SupabaseRestClient) -> Dict[str, Any]:
    latest = latest_row(client, "signal_regret_log_v1", order="signal_ts.desc")
    ts = latest.get("signal_ts") if latest else None
    age = age_minutes(ts)
    status = freshness_status(age, green_max=1440, yellow_max=10080)

    total_rows = row_count(client, "signal_regret_log_v1")

    return {
        "module_status": status,
        "latest_signal_ts": ts,
        "age_minutes": age,
        "rows": total_rows,
        "latest_symbol": latest.get("symbol") if latest else None,
        "latest_regret_label_15m": latest.get("regret_label_15m") if latest else None,
    }


def build_regret_analytics_status(client: SupabaseRestClient) -> Dict[str, Any]:
    latest = latest_row(client, "signal_regret_analytics_v2", order="computed_at.desc")
    ts = latest.get("computed_at") if latest else None
    age = age_minutes(ts)
    status = freshness_status(age, green_max=1440, yellow_max=10080)

    total_rows = row_count(client, "signal_regret_analytics_v2")

    return {
        "module_status": status,
        "latest_computed_at": ts,
        "age_minutes": age,
        "rows": total_rows,
        "latest_symbol": latest.get("symbol") if latest else None,
        "latest_direction_bias": latest.get("direction_bias") if latest else None,
    }


def combine_overall_status(modules: List[Dict[str, Any]]) -> str:
    statuses = [m.get("module_status") for m in modules]
    if "CRITICAL" in statuses:
        return "CRITICAL"
    if "STALE" in statuses or "NO_TS" in statuses:
        return "STALE"
    return "HEALTHY"


def run() -> None:
    print_banner("MERDIAN - Measurement Health Snapshot")
    print(f"Started at UTC: {utc_now_iso()}")
    print("-" * 72)

    load_dotenv(ENV_FILE, override=True)
    client = SupabaseRestClient()

    volatility_status = build_volatility_status(client)
    wcb_status = build_wcb_status(client)
    futures_status = build_futures_status(client)
    gamma_status = build_gamma_status(client)
    momentum_status = build_momentum_status(client)
    regret_log_status = build_regret_log_status(client)
    regret_analytics_status = build_regret_analytics_status(client)

    modules = [
        volatility_status,
        wcb_status,
        futures_status,
        gamma_status,
        momentum_status,
        regret_log_status,
        regret_analytics_status,
    ]

    overall_status = combine_overall_status(modules)

    overall_summary = {
        "built_at_utc": utc_now_iso(),
        "modules_checked": [
            "volatility",
            "wcb",
            "futures",
            "gamma",
            "momentum",
            "regret_log",
            "regret_analytics_v2",
        ],
    }

    row = {
        "ts": utc_now_iso(),
        "overall_status": overall_status,
        "overall_summary": overall_summary,
        "volatility_status": volatility_status,
        "wcb_status": wcb_status,
        "futures_status": futures_status,
        "gamma_status": gamma_status,
        "momentum_status": momentum_status,
        "regret_log_status": regret_log_status,
        "regret_analytics_status": regret_analytics_status,
        "source": "measurement_health_snapshot_local",
    }

    print("Health row preview:")
    print(json.dumps(row, indent=2, default=str))
    print("-" * 72)

    inserted = client.insert("measurement_health_snapshots", row)

    print("Inserted rows: 1")
    print(f"Inserted ts: {inserted.get('ts')}")
    print(f"Inserted overall_status: {inserted.get('overall_status')}")
    print(f"Inserted created_at: {inserted.get('created_at')}")
    print_banner("MERDIAN - Measurement Health Snapshot Completed")


if __name__ == "__main__":
    run()