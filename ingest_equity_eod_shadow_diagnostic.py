#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import math
import os
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


IST = timezone(timedelta(hours=5, minutes=30))


def load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def today_ist() -> date:
    return datetime.now(IST).date()


def safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def print_header(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


class SupabaseRestClient:
    def __init__(self, url: str, service_role_key: str) -> None:
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def select(
        self,
        table: str,
        filters: Optional[Dict[str, str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        columns: str = "*",
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{table}"
        params: Dict[str, str] = {"select": columns}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = str(limit)

        response = requests.get(url, headers=self.headers, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected response for {table}: {data}")
        return data

    def insert_many(self, table: str, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        url = f"{self.base_url}/{table}"
        response = requests.post(url, headers=self.headers, json=rows, timeout=120)
        response.raise_for_status()

    def upsert_many(self, table: str, rows: List[Dict[str, Any]], on_conflict: str) -> None:
        if not rows:
            return
        url = f"{self.base_url}/{table}?on_conflict={on_conflict}"
        headers = dict(self.headers)
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        response = requests.post(url, headers=headers, json=rows, timeout=180)
        response.raise_for_status()


def classify_error(http_status: Optional[int], error_code: Optional[str], error_message: Optional[str]) -> str:
    if http_status == 429 or error_code == "DH-904":
        return "RATE_LIMIT"
    if http_status == 401 or error_code == "DH-901":
        return "AUTH"
    if http_status == 400 or error_code == "DH-905":
        return "BAD_REQUEST"
    if error_message and "timed out" in error_message.lower():
        return "TIMEOUT"
    return "OTHER_ERROR"


def fetch_active_nse_universe(client: SupabaseRestClient) -> List[Dict[str, Any]]:
    return client.select(
        "dhan_scrip_map",
        filters={
            "exchange": "eq.NSE",
            "is_active": "eq.true",
        },
        order="ticker.asc",
        columns="ticker,dhan_security_id,exchange,is_active",
    )


def build_dhan_headers() -> Dict[str, str]:
    client_id = require_env("DHAN_CLIENT_ID")
    access_token = require_env("DHAN_API_TOKEN")
    return {
        "access-token": access_token,
        "client-id": client_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def fetch_historical_candles(
    security_id: str,
    start_date: date,
    end_date: date,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[int], Optional[str], Optional[str], Optional[str]]:
    """
    Returns:
      candles, http_status, error_type, error_code, error_message
    """
    historical_url = require_env("DHAN_HISTORICAL_URL")
    headers = build_dhan_headers()

    payload = {
        "securityId": str(security_id),
        "exchangeSegment": "NSE_EQ",
        "instrument": "EQUITY",
        "expiryCode": 0,
        "fromDate": start_date.isoformat(),
        "toDate": end_date.isoformat(),
        "oi": False,
        "interval": "1D",
    }

    try:
        response = requests.post(historical_url, headers=headers, json=payload, timeout=60)
        http_status = response.status_code

        if response.status_code != 200:
            try:
                err = response.json()
            except Exception:
                err = {}
            return (
                None,
                http_status,
                err.get("errorType"),
                err.get("errorCode"),
                err.get("errorMessage") or response.text,
            )

        data = response.json()
        candles = data.get("data") or data.get("candles") or data.get("results") or []

        if not isinstance(candles, list):
            return None, http_status, "MalformedResponse", None, f"Unexpected candle payload: {data}"

        return candles, http_status, None, None, None

    except requests.Timeout as e:
        return None, None, "Timeout", None, str(e)
    except Exception as e:
        return None, None, "Exception", None, str(e)


def normalize_candle_rows(ticker: str, security_id: str, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for c in candles:
        ts_raw = c.get("start_Time") or c.get("startTime") or c.get("timestamp") or c.get("time")
        open_ = c.get("open")
        high = c.get("high")
        low = c.get("low")
        close = c.get("close")
        volume = c.get("volume")

        if ts_raw is None:
            continue

        # Dhan can return timestamp strings or epoch values.
        trade_date: Optional[date] = None
        if isinstance(ts_raw, (int, float)):
            trade_date = datetime.fromtimestamp(ts_raw, tz=timezone.utc).date()
        else:
            ts_str = str(ts_raw).replace("Z", "+00:00")
            try:
                trade_date = datetime.fromisoformat(ts_str).date()
            except Exception:
                try:
                    trade_date = datetime.strptime(ts_str[:10], "%Y-%m-%d").date()
                except Exception:
                    trade_date = None

        if trade_date is None:
            continue

        rows.append(
            {
                "ticker": ticker,
                "trade_date": trade_date.isoformat(),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "dhan_security_id": str(security_id),
                "source": "DHAN_SHADOW_DIAGNOSTIC",
            }
        )

    return rows


def chunked(items: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def main() -> None:
    load_environment()

    supabase_url = require_env("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not supabase_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY")

    client = SupabaseRestClient(supabase_url, supabase_key)

    batch_size = env_int("EOD_SHADOW_BATCH_SIZE", 50)
    inter_request_sleep_sec = env_float("EOD_SHADOW_REQUEST_SLEEP_SEC", 0.0)
    inter_batch_sleep_sec = env_float("EOD_SHADOW_BATCH_SLEEP_SEC", 0.0)
    max_batches = env_int("EOD_SHADOW_MAX_BATCHES", 0)  # 0 = all batches
    write_shadow_candles = os.getenv("EOD_SHADOW_WRITE_CANDLES", "false").strip().lower() == "true"

    from_date = date(2025, 8, 17)
    to_date = today_ist()

    universe = fetch_active_nse_universe(client)
    if not universe:
        raise RuntimeError("No active NSE universe found in dhan_scrip_map")

    run_id = str(uuid.uuid4())
    batches = chunked(universe, batch_size)
    if max_batches > 0:
        batches = batches[:max_batches]

    print_header("MERDIAN - Shadow Diagnostic EOD Ingest")
    print(f"Run ID           : {run_id}")
    print(f"Date window      : {from_date} -> {to_date}")
    print(f"Universe size    : {len(universe)}")
    print(f"Batch size       : {batch_size}")
    print(f"Batches to run   : {len(batches)}")
    print(f"Write candles    : {write_shadow_candles}")
    print(f"Req sleep (sec)  : {inter_request_sleep_sec}")
    print(f"Batch sleep (sec): {inter_batch_sleep_sec}")
    print("-" * 72)

    total_ok = 0
    total_fail = 0
    total_candles_raw = 0
    total_candles_upserted = 0
    audit_rows: List[Dict[str, Any]] = []

    for batch_no, batch in enumerate(batches, start=1):
        batch_offset = (batch_no - 1) * batch_size
        batch_ok = 0
        batch_fail = 0
        batch_candles_raw = 0
        batch_candles_upserted = 0

        print("=" * 72)
        print(f"BATCH {batch_no} | offset={batch_offset} | tickers={len(batch)}")
        print("=" * 72)

        shadow_candle_rows: List[Dict[str, Any]] = []

        for item in batch:
            ticker = item["ticker"]
            security_id = str(item["dhan_security_id"])
            request_started_at = utc_now()
            t0 = time.time()

            candles, http_status, error_type, error_code, error_message = fetch_historical_candles(
                security_id=security_id,
                start_date=from_date,
                end_date=to_date,
            )

            request_finished_at = utc_now()
            duration_ms = int(round((time.time() - t0) * 1000))

            candles_raw = 0
            candles_upserted = 0
            outcome_class = "UNKNOWN"
            notes = None

            if candles is not None:
                candles_raw = len(candles)
                normalized = normalize_candle_rows(ticker, security_id, candles)
                candles_upserted = len(normalized)
                batch_candles_raw += candles_raw
                batch_candles_upserted += candles_upserted
                total_candles_raw += candles_raw
                total_candles_upserted += candles_upserted

                if write_shadow_candles and normalized:
                    shadow_candle_rows.extend(normalized)

                if candles_raw == 0:
                    outcome_class = "EMPTY"
                    batch_fail += 1
                    total_fail += 1
                    print(f"[EMPTY] {ticker} | security_id={security_id} | candles_raw=0")
                else:
                    outcome_class = "OK"
                    batch_ok += 1
                    total_ok += 1
                    print(
                        f"[OK] {ticker} | security_id={security_id} | "
                        f"candles_raw={candles_raw} | candles_upserted={candles_upserted}"
                    )
            else:
                outcome_class = classify_error(http_status, error_code, error_message)
                batch_fail += 1
                total_fail += 1
                print(
                    f"[FAIL] {ticker} | security_id={security_id} | "
                    f"http_status={http_status} | error_type={error_type} | "
                    f"error_code={error_code} | error_message={error_message}"
                )

            audit_rows.append(
                {
                    "run_id": run_id,
                    "batch_no": batch_no,
                    "batch_offset": batch_offset,
                    "ticker": ticker,
                    "security_id": security_id,
                    "trade_date_from": from_date.isoformat(),
                    "trade_date_to": to_date.isoformat(),
                    "request_started_at": request_started_at.isoformat(),
                    "request_finished_at": request_finished_at.isoformat(),
                    "http_status": http_status,
                    "error_type": error_type,
                    "error_code": error_code,
                    "error_message": error_message,
                    "candles_raw": candles_raw,
                    "candles_upserted": candles_upserted,
                    "outcome_class": outcome_class,
                    "duration_ms": duration_ms,
                    "notes": notes,
                }
            )

            if inter_request_sleep_sec > 0:
                time.sleep(inter_request_sleep_sec)

        client.insert_many("equity_eod_shadow_audit", audit_rows[-len(batch):])

        if write_shadow_candles and shadow_candle_rows:
            client.upsert_many(
                "equity_eod",
                shadow_candle_rows,
                on_conflict="ticker,trade_date",
            )

        print("-" * 72)
        print(
            f"BATCH {batch_no} SUMMARY | "
            f"ok={batch_ok} | fail={batch_fail} | "
            f"candles_raw={batch_candles_raw} | candles_upserted={batch_candles_upserted}"
        )

        if inter_batch_sleep_sec > 0 and batch_no < len(batches):
            time.sleep(inter_batch_sleep_sec)

    print("=" * 72)
    print("FINAL SUMMARY")
    print("=" * 72)
    print(f"Run ID             : {run_id}")
    print(f"Batches processed  : {len(batches)}")
    print(f"Total OK           : {total_ok}")
    print(f"Total FAIL         : {total_fail}")
    print(f"Total candles raw  : {total_candles_raw}")
    print(f"Total candles upserted: {total_candles_upserted}")
    print("=" * 72)


if __name__ == "__main__":
    main()