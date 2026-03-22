from __future__ import annotations

import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
TARGET_TABLE = "option_execution_snapshots"


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


def strike_step_for_symbol(symbol: str) -> int:
    symbol = (symbol or "").upper().strip()
    if symbol == "NIFTY":
        return 50
    if symbol == "SENSEX":
        return 100
    raise RuntimeError(f"Unsupported symbol for strike step: {symbol}")


def execution_strikes(symbol: str, spot: float) -> tuple[int, int]:
    """
    Execution-layer asymmetric strikes:
    - CE = closest lower strike
    - PE = next higher strike
    If spot is exactly on a strike, both become that strike.
    """
    step = strike_step_for_symbol(symbol)
    lower_strike = int(math.floor(spot / step) * step)
    upper_strike = int(math.ceil(spot / step) * step)
    return lower_strike, upper_strike


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

    rows = client.select(
        table="signal_snapshots",
        select_cols="id,symbol,ts,spot,atm_strike",
        order="ts.asc",
        limit=limit,
    )

    pending = []
    for row in rows:
        sid = row.get("id")
        if sid is None:
            continue
        sid = int(sid)
        if sid not in existing_ids:
            pending.append(row)

    return pending


def fetch_option_chain_window(
    client: SupabaseRestClient, symbol: str, signal_ts: str, limit: int = 1000
) -> list[dict[str, Any]]:
    rows = client.select(
        table="option_chain_snapshots",
        select_cols="ts,symbol,strike,option_type,ltp,iv",
        filters=[
            f"symbol=eq.{symbol}",
            f"ts=lte.{signal_ts}",
        ],
        order="ts.desc",
        limit=limit,
    )
    return rows


def latest_chain_bucket(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    latest_ts = rows[0].get("ts")
    return [r for r in rows if r.get("ts") == latest_ts]


def match_option_row(bucket: list[dict[str, Any]], strike: int, option_type: str) -> dict[str, Any] | None:
    option_type = option_type.upper()
    return next(
        (
            r for r in bucket
            if int(float(r.get("strike"))) == strike
            and str(r.get("option_type", "")).upper() == option_type
        ),
        None,
    )


def build_snapshot_row(client: SupabaseRestClient, signal_row: dict[str, Any]) -> dict[str, Any] | None:
    signal_snapshot_id = int(signal_row["id"])
    symbol = str(signal_row["symbol"]).upper().strip()
    signal_ts = str(signal_row["ts"])
    spot = to_float(signal_row.get("spot"))

    if spot is None:
        return None

    ce_strike, pe_strike = execution_strikes(symbol, spot)

    chain_rows = fetch_option_chain_window(client, symbol, signal_ts, limit=1000)
    if not chain_rows:
        return None

    bucket = latest_chain_bucket(chain_rows)
    if not bucket:
        return None

    ce_row = match_option_row(bucket, ce_strike, "CE")
    pe_row = match_option_row(bucket, pe_strike, "PE")

    if ce_row is None and pe_row is None:
        return None

    chain_ts = bucket[0].get("ts")

    row = {
        "signal_snapshot_id": signal_snapshot_id,
        "symbol": symbol,
        "signal_ts": signal_ts,
        "spot": spot,
        "ce_strike": ce_strike,
        "pe_strike": pe_strike,
        "ce_price": to_float(ce_row.get("ltp")) if ce_row else None,
        "pe_price": to_float(pe_row.get("ltp")) if pe_row else None,
        "ce_iv": to_float(ce_row.get("iv")) if ce_row else None,
        "pe_iv": to_float(pe_row.get("iv")) if pe_row else None,
        "chain_ts": chain_ts,
    }

    return row


def main() -> None:
    print_banner("MERDIAN - Build Option Execution Snapshots V1")
    print(f"Target table: {TARGET_TABLE}")
    print(f"Started at UTC: {utc_now_iso()}")
    print("-" * 72)

    client = SupabaseRestClient()

    pending_signals = fetch_pending_signals(client, limit=5000)
    print(f"Pending signals: {len(pending_signals)}")

    rows_to_upsert: list[dict[str, Any]] = []
    skipped = 0

    for idx, signal_row in enumerate(pending_signals, start=1):
        signal_id = signal_row.get("id")
        try:
            built = build_snapshot_row(client, signal_row)
            if built is None:
                skipped += 1
                print(f"[{idx}/{len(pending_signals)}] Skipped signal id={signal_id} | no execution snapshot found")
                continue

            rows_to_upsert.append(built)
            print(
                f"[{idx}/{len(pending_signals)}] Prepared signal id={signal_id} | "
                f"symbol={built['symbol']} | ce_strike={built['ce_strike']} | pe_strike={built['pe_strike']}"
            )

        except Exception as exc:
            skipped += 1
            print(f"[{idx}/{len(pending_signals)}] Skipped signal id={signal_id} | reason={exc}")

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

    print_banner("MERDIAN - Option Execution Snapshots V1 Completed")


if __name__ == "__main__":
    main()