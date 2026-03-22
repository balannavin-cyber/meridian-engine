from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
SOURCE_TABLE = "signal_market_path_audit_v1"
TARGET_TABLE = "signal_market_outcome_audit_v1"


def print_banner(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


class SupabaseRestClient:
    def __init__(self) -> None:
        load_dotenv(ENV_FILE, override=True)
        self.base_url = get_env("SUPABASE_URL").rstrip("/")
        self.api_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            or os.getenv("SUPABASE_ANON_KEY", "").strip()
        )
        if not self.api_key:
            raise RuntimeError(
                "Missing SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY in .env"
            )

        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def select(
        self,
        table: str,
        select_cols: str = "*",
        filters: list[str] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/{table}"
        params: dict[str, str] = {"select": select_cols}

        if filters:
            for f in filters:
                key, value = f.split("=", 1)
                params[key] = value

        if order:
            params["order"] = order

        if limit is not None:
            params["limit"] = str(limit)

        response = requests.get(url, headers=self.headers, params=params, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Supabase SELECT failed | table={table} | "
                f"HTTP {response.status_code} | response={response.text}"
            )
        return response.json()

    def upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/{table}"
        headers = dict(self.headers)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        response = requests.post(
            url,
            headers=headers,
            params={"on_conflict": on_conflict},
            json=rows,
            timeout=120,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Supabase UPSERT failed | table={table} | "
                f"HTTP {response.status_code} | response={response.text}"
            )
        return response.json()


def compute_pct(entry: float | None, outcome: float | None) -> float | None:
    if entry in (None, 0) or outcome is None:
        return None
    return ((outcome - entry) / entry) * 100.0


def get_row_by_minute(rows: list[dict[str, Any]], minute_offset: int) -> dict[str, Any] | None:
    for row in rows:
        if row.get("minute_offset") == minute_offset:
            return row
    return None


def first_favorable_minute(rows: list[dict[str, Any]], action: str, field: str) -> int | None:
    for row in rows:
        move = to_float(row.get(field))
        minute = row.get("minute_offset")
        if move is None or minute is None:
            continue
        if action == "BUY_CE" and move > 0:
            return int(minute)
        if action == "BUY_PE" and move < 0:
            return int(minute)
    return None


def first_adverse_minute(rows: list[dict[str, Any]], action: str, field: str) -> int | None:
    for row in rows:
        move = to_float(row.get(field))
        minute = row.get("minute_offset")
        if move is None or minute is None:
            continue
        if action == "BUY_CE" and move < 0:
            return int(minute)
        if action == "BUY_PE" and move > 0:
            return int(minute)
    return None


def compute_mfe_mae(rows: list[dict[str, Any]], action: str, field: str) -> tuple[float | None, float | None]:
    values = [to_float(r.get(field)) for r in rows]
    values = [v for v in values if v is not None]

    if not values:
        return None, None

    if action == "BUY_CE":
        return max(values), min(values)
    if action == "BUY_PE":
        favorable = [-v for v in values]
        return max(favorable), min(favorable)
    return None, None


def fetch_existing_signal_ids(client: SupabaseRestClient) -> set[int]:
    rows = client.select(
        table=TARGET_TABLE,
        select_cols="signal_snapshot_id",
        order="signal_snapshot_id.desc",
        limit=100000,
    )
    return {
        int(row["signal_snapshot_id"])
        for row in rows
        if row.get("signal_snapshot_id") is not None
    }


def fetch_pending_signal_ids(client: SupabaseRestClient) -> list[int]:
    existing_ids = fetch_existing_signal_ids(client)

    rows = client.select(
        table=SOURCE_TABLE,
        select_cols="signal_snapshot_id",
        order="signal_snapshot_id.asc",
        limit=100000,
    )

    seen = []
    seen_set = set()
    for row in rows:
        sid = row.get("signal_snapshot_id")
        if sid is None:
            continue
        sid = int(sid)
        if sid not in seen_set:
            seen.append(sid)
            seen_set.add(sid)

    return [sid for sid in seen if sid not in existing_ids]


def fetch_path_rows_for_signal(client: SupabaseRestClient, signal_snapshot_id: int) -> list[dict[str, Any]]:
    return client.select(
        table=SOURCE_TABLE,
        select_cols="*",
        filters=[f"signal_snapshot_id=eq.{signal_snapshot_id}"],
        order="minute_offset.asc",
        limit=200,
    )


def build_outcome_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None

    r0 = rows[0]
    signal_snapshot_id = int(r0["signal_snapshot_id"])
    symbol = r0["symbol"]
    signal_ts = r0["signal_ts"]
    signal_action = r0["signal_action"]
    direction_bias = r0.get("direction_bias")
    confidence_score = to_float(r0.get("confidence_score"))

    entry_spot = to_float(r0.get("entry_spot"))
    entry_futures = to_float(r0.get("entry_futures"))
    entry_basis = to_float(r0.get("entry_basis"))

    r15 = get_row_by_minute(rows, 15)
    r30 = get_row_by_minute(rows, 30)
    r60 = get_row_by_minute(rows, 60)

    spot_15m = to_float(r15.get("spot")) if r15 else None
    spot_30m = to_float(r30.get("spot")) if r30 else None
    spot_60m = to_float(r60.get("spot")) if r60 else None

    futures_15m = to_float(r15.get("futures_price")) if r15 else None
    futures_30m = to_float(r30.get("futures_price")) if r30 else None
    futures_60m = to_float(r60.get("futures_price")) if r60 else None

    basis_15m = to_float(r15.get("basis")) if r15 else None
    basis_30m = to_float(r30.get("basis")) if r30 else None
    basis_60m = to_float(r60.get("basis")) if r60 else None

    spot_mfe_60m, spot_mae_60m = compute_mfe_mae(rows, signal_action, "spot_move_points")
    futures_mfe_60m, futures_mae_60m = compute_mfe_mae(rows, signal_action, "futures_move_points")

    return {
        "signal_snapshot_id": signal_snapshot_id,
        "symbol": symbol,
        "signal_ts": signal_ts,
        "signal_action": signal_action,
        "direction_bias": direction_bias,
        "confidence_score": confidence_score,

        "entry_spot": entry_spot,
        "entry_futures": entry_futures,
        "entry_basis": entry_basis,

        "spot_15m": spot_15m,
        "spot_30m": spot_30m,
        "spot_60m": spot_60m,
        "futures_15m": futures_15m,
        "futures_30m": futures_30m,
        "futures_60m": futures_60m,
        "basis_15m": basis_15m,
        "basis_30m": basis_30m,
        "basis_60m": basis_60m,

        "spot_move_15m_points": to_float(r15.get("spot_move_points")) if r15 else None,
        "spot_move_30m_points": to_float(r30.get("spot_move_points")) if r30 else None,
        "spot_move_60m_points": to_float(r60.get("spot_move_points")) if r60 else None,

        "futures_move_15m_points": to_float(r15.get("futures_move_points")) if r15 else None,
        "futures_move_30m_points": to_float(r30.get("futures_move_points")) if r30 else None,
        "futures_move_60m_points": to_float(r60.get("futures_move_points")) if r60 else None,

        "basis_change_15m_points": to_float(r15.get("basis_change_points")) if r15 else None,
        "basis_change_30m_points": to_float(r30.get("basis_change_points")) if r30 else None,
        "basis_change_60m_points": to_float(r60.get("basis_change_points")) if r60 else None,

        "spot_move_15m_pct": compute_pct(entry_spot, spot_15m),
        "spot_move_30m_pct": compute_pct(entry_spot, spot_30m),
        "spot_move_60m_pct": compute_pct(entry_spot, spot_60m),

        "futures_move_15m_pct": compute_pct(entry_futures, futures_15m),
        "futures_move_30m_pct": compute_pct(entry_futures, futures_30m),
        "futures_move_60m_pct": compute_pct(entry_futures, futures_60m),

        "spot_mfe_60m_points": spot_mfe_60m,
        "spot_mae_60m_points": spot_mae_60m,
        "futures_mfe_60m_points": futures_mfe_60m,
        "futures_mae_60m_points": futures_mae_60m,

        "first_favorable_spot_minute": first_favorable_minute(rows, signal_action, "spot_move_points"),
        "first_adverse_spot_minute": first_adverse_minute(rows, signal_action, "spot_move_points"),
        "first_favorable_futures_minute": first_favorable_minute(rows, signal_action, "futures_move_points"),
        "first_adverse_futures_minute": first_adverse_minute(rows, signal_action, "futures_move_points"),

        "raw": {
            "builder_ts_utc": utc_now_iso(),
            "source_path_rows": len(rows),
        },
    }


def main() -> None:
    print_banner("MERDIAN - Build Signal Market Outcome Audit V1")
    print(f"Source table: {SOURCE_TABLE}")
    print(f"Target table: {TARGET_TABLE}")
    print(f"Started at UTC: {utc_now_iso()}")
    print("-" * 72)

    client = SupabaseRestClient()

    pending_signal_ids = fetch_pending_signal_ids(client)
    print(f"Pending signals: {len(pending_signal_ids)}")

    rows_to_upsert: list[dict[str, Any]] = []
    skipped = 0

    for idx, signal_id in enumerate(pending_signal_ids, start=1):
        try:
            path_rows = fetch_path_rows_for_signal(client, signal_id)
            outcome_row = build_outcome_row(path_rows)
            if outcome_row is None:
                skipped += 1
                print(f"[{idx}/{len(pending_signal_ids)}] Skipped signal id={signal_id}")
                continue
            rows_to_upsert.append(outcome_row)
            print(f"[{idx}/{len(pending_signal_ids)}] Prepared signal id={signal_id}")
        except Exception as exc:
            skipped += 1
            print(f"[{idx}/{len(pending_signal_ids)}] Skipped signal id={signal_id} | reason={exc}")

    print("-" * 72)
    print(f"Prepared rows: {len(rows_to_upsert)}")
    print(f"Skipped: {skipped}")

    if rows_to_upsert:
        inserted = client.upsert(
            table=TARGET_TABLE,
            rows=rows_to_upsert,
            on_conflict="signal_snapshot_id",
        )
        print(f"Rows upserted: {len(inserted)}")
    else:
        print("No rows upserted.")

    print_banner("MERDIAN - Signal Market Outcome Audit V1 Completed")


if __name__ == "__main__":
    main()