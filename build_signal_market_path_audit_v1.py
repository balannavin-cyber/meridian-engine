from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
TARGET_TABLE = "signal_market_path_audit_v1"
MAX_MINUTE_OFFSET = 60


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


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def normalize_action(action: str | None) -> str:
    value = (action or "").strip().upper()
    if value in {"BUY_CE", "BUY_PE", "DO_NOTHING"}:
        return value
    return value or "UNKNOWN"


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


def get_signal_confidence(signal_row: dict[str, Any]) -> float | None:
    candidates = [
        signal_row.get("confidence"),
        signal_row.get("confidence_score"),
        signal_row.get("composite_conviction"),
        signal_row.get("score"),
    ]
    for value in candidates:
        parsed = to_float(value)
        if parsed is not None:
            return parsed
    return None


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


def fetch_pending_signals(client: SupabaseRestClient, limit: int = 5000) -> list[dict[str, Any]]:
    existing_ids = fetch_existing_signal_ids(client)

    signals = client.select(
        table="signal_snapshots",
        select_cols="*",
        order="ts.asc",
        limit=limit,
    )

    pending: list[dict[str, Any]] = []
    for row in signals:
        sid = row.get("id")
        if sid is None:
            continue
        if int(sid) not in existing_ids:
            pending.append(row)

    return pending


def fetch_spot_window(
    client: SupabaseRestClient, symbol: str, start_dt: datetime, end_dt: datetime
) -> list[dict[str, Any]]:
    return client.select(
        table="market_spot_snapshots",
        select_cols="ts,spot",
        filters=[
            f"symbol=eq.{symbol}",
            f"ts=gte.{start_dt.isoformat()}",
            f"ts=lte.{end_dt.isoformat()}",
        ],
        order="ts.asc",
        limit=5000,
    )


def fetch_futures_window(
    client: SupabaseRestClient, symbol: str, start_dt: datetime, end_dt: datetime
) -> list[dict[str, Any]]:
    return client.select(
        table="index_futures_snapshots",
        select_cols="ts,futures_price,basis",
        filters=[
            f"symbol=eq.{symbol}",
            f"ts=gte.{start_dt.isoformat()}",
            f"ts=lte.{end_dt.isoformat()}",
        ],
        order="ts.asc",
        limit=5000,
    )


def first_row_at_or_after(rows: list[dict[str, Any]], target_dt: datetime) -> dict[str, Any] | None:
    for row in rows:
        ts = parse_dt(row.get("ts"))
        if ts is not None and ts >= target_dt:
            return row
    return None


def compute_move(entry: float | None, outcome: float | None) -> float | None:
    if entry is None or outcome is None:
        return None
    return outcome - entry


def compute_pct(entry: float | None, outcome: float | None) -> float | None:
    if entry in (None, 0) or outcome is None:
        return None
    return ((outcome - entry) / entry) * 100.0


def build_rows_for_signal(client: SupabaseRestClient, signal_row: dict[str, Any]) -> list[dict[str, Any]]:
    signal_id = signal_row.get("id")
    symbol = signal_row.get("symbol")
    signal_ts = parse_dt(signal_row.get("ts"))
    signal_action = normalize_action(signal_row.get("action"))
    direction_bias = signal_row.get("direction_bias")
    confidence_score = get_signal_confidence(signal_row)

    if signal_id is None or not symbol or signal_ts is None:
        return []

    window_end = signal_ts + timedelta(minutes=MAX_MINUTE_OFFSET + 2)

    spot_rows = fetch_spot_window(client, symbol, signal_ts, window_end)
    futures_rows = fetch_futures_window(client, symbol, signal_ts, window_end)

    entry_spot_row = first_row_at_or_after(spot_rows, signal_ts)
    entry_futures_row = first_row_at_or_after(futures_rows, signal_ts)

    if entry_spot_row is None:
        return []

    entry_spot = to_float(entry_spot_row.get("spot"))
    entry_spot_ts = parse_dt(entry_spot_row.get("ts"))

    entry_futures = to_float(entry_futures_row.get("futures_price")) if entry_futures_row else None
    entry_futures_ts = parse_dt(entry_futures_row.get("ts")) if entry_futures_row else None
    entry_basis = to_float(entry_futures_row.get("basis")) if entry_futures_row else None

    rows: list[dict[str, Any]] = []

    for minute_offset in range(0, MAX_MINUTE_OFFSET + 1):
        target_dt = signal_ts + timedelta(minutes=minute_offset)

        spot_row = first_row_at_or_after(spot_rows, target_dt)
        fut_row = first_row_at_or_after(futures_rows, target_dt)

        spot_val = to_float(spot_row.get("spot")) if spot_row else None
        spot_source_ts = parse_dt(spot_row.get("ts")) if spot_row else None

        futures_val = to_float(fut_row.get("futures_price")) if fut_row else None
        basis_val = to_float(fut_row.get("basis")) if fut_row else None
        futures_source_ts = parse_dt(fut_row.get("ts")) if fut_row else None

        row = {
            "signal_snapshot_id": int(signal_id),
            "symbol": symbol,
            "signal_ts": signal_ts.isoformat(),
            "signal_action": signal_action,
            "direction_bias": direction_bias,
            "confidence_score": confidence_score,

            "minute_offset": minute_offset,
            "path_ts": target_dt.isoformat(),

            "entry_spot": entry_spot,
            "spot": spot_val,
            "spot_move_points": compute_move(entry_spot, spot_val),
            "spot_move_pct": compute_pct(entry_spot, spot_val),

            "entry_futures": entry_futures,
            "futures_price": futures_val,
            "futures_move_points": compute_move(entry_futures, futures_val),
            "futures_move_pct": compute_pct(entry_futures, futures_val),

            "entry_basis": entry_basis,
            "basis": basis_val,
            "basis_change_points": compute_move(entry_basis, basis_val),

            "spot_source_ts": spot_source_ts.isoformat() if spot_source_ts else None,
            "futures_source_ts": futures_source_ts.isoformat() if futures_source_ts else None,

            "evaluation_source_spot": "market_spot_snapshots",
            "evaluation_source_futures": "index_futures_snapshots",

            "raw": {
                "builder_ts_utc": utc_now_iso(),
                "entry_spot_ts": entry_spot_ts.isoformat() if entry_spot_ts else None,
                "entry_futures_ts": entry_futures_ts.isoformat() if entry_futures_ts else None,
            },
        }
        rows.append(row)

    return rows


def main() -> None:
    print_banner("MERDIAN - Build Signal Market Path Audit V1")
    print(f"Target table: {TARGET_TABLE}")
    print(f"Started at UTC: {utc_now_iso()}")
    print(f"Max minute offset: {MAX_MINUTE_OFFSET}")
    print("-" * 72)

    client = SupabaseRestClient()

    pending_signals = fetch_pending_signals(client, limit=5000)
    print(f"Pending signals: {len(pending_signals)}")

    total_rows = 0
    skipped = 0

    for idx, signal_row in enumerate(pending_signals, start=1):
        signal_id = signal_row.get("id")
        try:
            built_rows = build_rows_for_signal(client, signal_row)
            if not built_rows:
                skipped += 1
                print(f"[{idx}/{len(pending_signals)}] Skipped signal id={signal_id} | no usable entry spot")
                continue

            inserted = client.upsert(
                table=TARGET_TABLE,
                rows=built_rows,
                on_conflict="signal_snapshot_id,minute_offset",
            )
            total_rows += len(inserted)
            print(f"[{idx}/{len(pending_signals)}] Upserted signal id={signal_id} | rows={len(inserted)}")

        except Exception as exc:
            skipped += 1
            print(f"[{idx}/{len(pending_signals)}] Skipped signal id={signal_id} | reason={exc}")

    print("-" * 72)
    print(f"Signals skipped: {skipped}")
    print(f"Total path rows upserted: {total_rows}")

    print_banner("MERDIAN - Signal Market Path Audit V1 Completed")


if __name__ == "__main__":
    main()