from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
TARGET_TABLE = "option_execution_price_history"


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


def strike_step_for_symbol(symbol: str) -> int:
    symbol = symbol.upper().strip()
    if symbol == "NIFTY":
        return 50
    if symbol == "SENSEX":
        return 100
    raise RuntimeError(f"Unsupported symbol: {symbol}")


def focused_execution_strikes(symbol: str, spot: float) -> tuple[list[int], list[int]]:
    """
    Focused execution set:
    - CE lower strike and one lower-beyond
    - PE upper strike and one upper-beyond
    """
    step = strike_step_for_symbol(symbol)

    lower = int(math.floor(spot / step) * step)
    upper = int(math.ceil(spot / step) * step)

    ce_strikes = sorted(set([lower, lower - step]))
    pe_strikes = sorted(set([upper, upper + step]))

    return ce_strikes, pe_strikes


def fetch_latest_spots(client: SupabaseRestClient) -> dict[str, float]:
    rows = client.select(
        table="market_spot_snapshots",
        select_cols="symbol,ts,spot",
        order="ts.desc",
        limit=20,
    )

    latest: dict[str, float] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper().strip()
        spot = to_float(row.get("spot"))
        if not symbol or spot is None:
            continue
        if symbol not in latest:
            latest[symbol] = spot

    required = ["NIFTY", "SENSEX"]
    missing = [s for s in required if s not in latest]
    if missing:
        raise RuntimeError(f"Missing latest spot for: {', '.join(missing)}")

    return latest


def fetch_latest_signal_metadata(client: SupabaseRestClient) -> dict[str, dict[str, Any]]:
    """
    Use latest signal snapshot per symbol to get front expiry_date.
    This keeps execution-history aligned with the current front signal context.
    """
    rows = client.select(
        table="signal_snapshots",
        select_cols="symbol,ts,expiry_date",
        order="ts.desc",
        limit=20,
    )

    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper().strip()
        if not symbol:
            continue
        if symbol not in latest:
            latest[symbol] = row

    required = ["NIFTY", "SENSEX"]
    missing = [s for s in required if s not in latest]
    if missing:
        raise RuntimeError(f"Missing latest signal metadata for: {', '.join(missing)}")

    return latest


def fetch_chain_bucket(client: SupabaseRestClient, symbol: str) -> list[dict[str, Any]]:
    """
    Pull recent option-chain rows and keep only the newest timestamp bucket.
    """
    rows = client.select(
        table="option_chain_snapshots",
        select_cols="symbol,ts,expiry_date,strike,option_type,ltp,iv",
        filters=[f"symbol=eq.{symbol}"],
        order="ts.desc",
        limit=1000,
    )
    if not rows:
        return []

    latest_ts = rows[0].get("ts")
    bucket = [r for r in rows if r.get("ts") == latest_ts]
    return bucket


def build_history_rows_for_symbol(
    symbol: str,
    spot: float,
    signal_meta: dict[str, Any],
    chain_bucket: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ce_strikes, pe_strikes = focused_execution_strikes(symbol, spot)

    target_expiry = signal_meta.get("expiry_date")
    if target_expiry is not None:
        filtered_bucket = [r for r in chain_bucket if r.get("expiry_date") == target_expiry]
        if filtered_bucket:
            chain_bucket = filtered_bucket

    if not chain_bucket:
        return []

    bucket_ts = chain_bucket[0].get("ts")

    out_rows: list[dict[str, Any]] = []

    for strike in ce_strikes:
        row = next(
            (
                r for r in chain_bucket
                if int(float(r.get("strike"))) == strike
                and str(r.get("option_type", "")).upper() == "CE"
            ),
            None,
        )
        if row is None:
            continue

        out_rows.append({
            "symbol": symbol,
            "ts": bucket_ts,
            "expiry_date": row.get("expiry_date"),
            "strike": strike,
            "option_type": "CE",
            "ltp": to_float(row.get("ltp")),
            "iv": to_float(row.get("iv")),
            "spot": spot,
            "source": "dhan_execution_capture",
        })

    for strike in pe_strikes:
        row = next(
            (
                r for r in chain_bucket
                if int(float(r.get("strike"))) == strike
                and str(r.get("option_type", "")).upper() == "PE"
            ),
            None,
        )
        if row is None:
            continue

        out_rows.append({
            "symbol": symbol,
            "ts": bucket_ts,
            "expiry_date": row.get("expiry_date"),
            "strike": strike,
            "option_type": "PE",
            "ltp": to_float(row.get("ltp")),
            "iv": to_float(row.get("iv")),
            "spot": spot,
            "source": "dhan_execution_capture",
        })

    return out_rows


def main() -> None:
    print_banner("MERDIAN - Ingest Option Execution Price History V1")
    print(f"Target table: {TARGET_TABLE}")
    print(f"Started at UTC: {utc_now_iso()}")
    print("-" * 72)

    client = SupabaseRestClient()

    latest_spots = fetch_latest_spots(client)
    latest_signal_meta = fetch_latest_signal_metadata(client)

    print(f"Latest spots: {latest_spots}")
    print("-" * 72)

    all_rows: list[dict[str, Any]] = []

    for symbol in ["NIFTY", "SENSEX"]:
        try:
            spot = latest_spots[symbol]
            signal_meta = latest_signal_meta[symbol]
            bucket = fetch_chain_bucket(client, symbol)

            if not bucket:
                print(f"{symbol}: no option-chain bucket found")
                continue

            built_rows = build_history_rows_for_symbol(symbol, spot, signal_meta, bucket)
            all_rows.extend(built_rows)

            ce_strikes, pe_strikes = focused_execution_strikes(symbol, spot)
            print(
                f"{symbol}: spot={spot} | "
                f"CE strikes={ce_strikes} | PE strikes={pe_strikes} | "
                f"rows_prepared={len(built_rows)}"
            )

        except Exception as exc:
            print(f"{symbol}: ERROR | {exc}")

    print("-" * 72)
    print(f"Prepared rows total: {len(all_rows)}")

    if all_rows:
        inserted = client.upsert(
            table=TARGET_TABLE,
            rows=all_rows,
            on_conflict="symbol,ts,expiry_date,strike,option_type",
        )
        print(f"Rows upserted: {len(inserted)}")
    else:
        print("No rows upserted.")

    print_banner("MERDIAN - Option Execution Price History V1 Completed")


if __name__ == "__main__":
    main()