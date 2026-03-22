from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
SOURCE_TABLE = "option_execution_snapshots"
TARGET_TABLE = "option_execution_path_audit_v1"
MAX_MINUTE_OFFSET = 60


def print_banner(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "+00:00"


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


def parse_dt(value: Any) -> datetime | None:
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


def compute_move(entry: float | None, outcome: float | None) -> float | None:
    if entry is None or outcome is None:
        return None
    return outcome - entry


def compute_pct(entry: float | None, outcome: float | None) -> float | None:
    if entry in (None, 0) or outcome is None:
        return None
    return ((outcome - entry) / entry) * 100.0


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


def fetch_pending_execution_rows(client: SupabaseRestClient, limit: int = 5000) -> list[dict[str, Any]]:
    existing_ids = fetch_existing_signal_ids(client)

    rows = client.select(
        table=SOURCE_TABLE,
        select_cols="*",
        order="signal_snapshot_id.asc",
        limit=limit,
    )

    pending = []
    for row in rows:
        sid = row.get("signal_snapshot_id")
        if sid is None:
            continue
        sid = int(sid)
        if sid not in existing_ids:
            pending.append(row)

    return pending


def fetch_chain_window(
    client: SupabaseRestClient, symbol: str, signal_ts: str, limit: int = 5000
) -> list[dict[str, Any]]:
    return client.select(
        table="option_chain_snapshots",
        select_cols="ts,symbol,strike,option_type,ltp,iv",
        filters=[
            f"symbol=eq.{symbol}",
            f"ts=gte.{signal_ts}",
        ],
        order="ts.asc",
        limit=limit,
    )


def latest_row_at_or_after(
    rows: list[dict[str, Any]],
    target_dt: datetime,
    strike: int,
    option_type: str,
) -> dict[str, Any] | None:
    option_type = option_type.upper()
    for row in rows:
        ts = parse_dt(row.get("ts"))
        if ts is None or ts < target_dt:
            continue
        if int(float(row.get("strike"))) != int(strike):
            continue
        if str(row.get("option_type", "")).upper() != option_type:
            continue
        return row
    return None


def build_rows_for_signal(client: SupabaseRestClient, src_row: dict[str, Any]) -> list[dict[str, Any]]:
    signal_snapshot_id = int(src_row["signal_snapshot_id"])
    symbol = str(src_row["symbol"]).upper().strip()
    signal_ts = str(src_row["signal_ts"])
    signal_dt = parse_dt(signal_ts)
    if signal_dt is None:
        return []

    spot = to_float(src_row.get("spot"))
    ce_strike = int(float(src_row["ce_strike"]))
    pe_strike = int(float(src_row["pe_strike"]))

    entry_ce_price = to_float(src_row.get("ce_price"))
    entry_pe_price = to_float(src_row.get("pe_price"))

    chain_rows = fetch_chain_window(client, symbol, signal_ts, limit=5000)
    if not chain_rows:
        return []

    built_rows: list[dict[str, Any]] = []

    for minute_offset in range(0, MAX_MINUTE_OFFSET + 1):
        target_dt = signal_dt + timedelta(minutes=minute_offset)

        ce_row = latest_row_at_or_after(chain_rows, target_dt, ce_strike, "CE")
        pe_row = latest_row_at_or_after(chain_rows, target_dt, pe_strike, "PE")

        ce_price = to_float(ce_row.get("ltp")) if ce_row else None
        pe_price = to_float(pe_row.get("ltp")) if pe_row else None

        ce_iv = to_float(ce_row.get("iv")) if ce_row else None
        pe_iv = to_float(pe_row.get("iv")) if pe_row else None

        chain_ts = None
        if ce_row and ce_row.get("ts"):
            chain_ts = ce_row.get("ts")
        elif pe_row and pe_row.get("ts"):
            chain_ts = pe_row.get("ts")

        built_rows.append({
            "signal_snapshot_id": signal_snapshot_id,
            "symbol": symbol,
            "signal_ts": signal_ts,
            "minute_offset": minute_offset,
            "path_ts": target_dt.isoformat(),

            "spot": spot,

            "ce_strike": ce_strike,
            "pe_strike": pe_strike,

            "entry_ce_price": entry_ce_price,
            "entry_pe_price": entry_pe_price,

            "ce_price": ce_price,
            "pe_price": pe_price,

            "ce_move_points": compute_move(entry_ce_price, ce_price),
            "pe_move_points": compute_move(entry_pe_price, pe_price),

            "ce_move_pct": compute_pct(entry_ce_price, ce_price),
            "pe_move_pct": compute_pct(entry_pe_price, pe_price),

            "ce_iv": ce_iv,
            "pe_iv": pe_iv,

            "chain_ts": chain_ts,
        })

    return built_rows


def main() -> None:
    print_banner("MERDIAN - Build Option Execution Path Audit V1")
    print(f"Source table: {SOURCE_TABLE}")
    print(f"Target table: {TARGET_TABLE}")
    print(f"Started at UTC: {utc_now_iso()}")
    print(f"Max minute offset: {MAX_MINUTE_OFFSET}")
    print("-" * 72)

    client = SupabaseRestClient()

    pending_rows = fetch_pending_execution_rows(client, limit=5000)
    print(f"Pending execution snapshots: {len(pending_rows)}")

    total_rows = 0
    skipped = 0

    for idx, src_row in enumerate(pending_rows, start=1):
        signal_id = src_row.get("signal_snapshot_id")
        try:
            built_rows = build_rows_for_signal(client, src_row)
            if not built_rows:
                skipped += 1
                print(f"[{idx}/{len(pending_rows)}] Skipped signal id={signal_id} | no option path rows")
                continue

            inserted = client.upsert(
                table=TARGET_TABLE,
                rows=built_rows,
                on_conflict="signal_snapshot_id,minute_offset",
            )
            total_rows += len(inserted)
            print(f"[{idx}/{len(pending_rows)}] Upserted signal id={signal_id} | rows={len(inserted)}")

        except Exception as exc:
            skipped += 1
            print(f"[{idx}/{len(pending_rows)}] Skipped signal id={signal_id} | reason={exc}")

    print("-" * 72)
    print(f"Signals skipped: {skipped}")
    print(f"Total path rows upserted: {total_rows}")

    print_banner("MERDIAN - Option Execution Path Audit V1 Completed")


if __name__ == "__main__":
    main()