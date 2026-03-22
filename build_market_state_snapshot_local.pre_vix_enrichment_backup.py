#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MERDIAN - build_market_state_snapshot_local.py

Purpose
-------
Build the latest market state snapshot for a symbol by combining:
- gamma metrics
- equal breadth
- volatility
- momentum
- WCB (measurement-only integration)

This version correctly reads WCB from:
- weighted_constituent_breadth_snapshots.index_symbol

Important
---------
This script does NOT modify signal logic.
It only expands the market-state measurement layer.

Architecture
------------
- Python runs locally
- data is read from and written to Supabase cloud

Usage
-----
python build_market_state_snapshot_local.py NIFTY
python build_market_state_snapshot_local.py SENSEX
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


# ============================================================
# ENV / CONFIG
# ============================================================

def load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# SUPABASE REST CLIENT
# ============================================================

class SupabaseRestClient:
    def __init__(self, url: str, api_key: str) -> None:
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
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
        if response.status_code >= 300:
            raise RuntimeError(
                f"Supabase select failed | table={table} | status={response.status_code} | body={response.text}"
            )

        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected select response for table={table}: {data}")
        return data

    def insert(self, table: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{table}"
        response = requests.post(url, headers=self.headers, data=json.dumps(payload), timeout=60)
        if response.status_code >= 300:
            raise RuntimeError(
                f"Supabase insert failed | table={table} | status={response.status_code} | body={response.text}"
            )

        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected insert response for table={table}: {data}")
        return data


# ============================================================
# HELPERS
# ============================================================

def normalize_symbol(user_symbol: str) -> str:
    value = user_symbol.strip().upper()
    if value not in {"NIFTY", "SENSEX"}:
        raise ValueError("Symbol must be NIFTY or SENSEX")
    return value


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        x = float(value)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: clean_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def first_non_empty(row: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return None


def select_latest_by_symbol(
    client: SupabaseRestClient,
    table: str,
    symbol_column: str,
    symbol_value: str,
    columns: str = "*",
) -> Optional[Dict[str, Any]]:
    rows = client.select(
        table=table,
        columns=columns,
        filters={symbol_column: f"eq.{symbol_value}"},
        order="ts.desc",
        limit=1,
    )
    if not rows:
        return None
    return rows[0]


def select_latest_any(
    client: SupabaseRestClient,
    table: str,
    columns: str = "*",
) -> Optional[Dict[str, Any]]:
    rows = client.select(
        table=table,
        columns=columns,
        order="ts.desc",
        limit=1,
    )
    if not rows:
        return None
    return rows[0]


def normalize_wcb_regime(raw_regime: Optional[str]) -> Optional[str]:
    if not raw_regime:
        return None

    value = raw_regime.strip().upper()

    mapping = {
        "STRONG_BULL": "STRONG_BULLISH",
        "BULL": "BULLISH",
        "NEUTRAL": "NEUTRAL",
        "TRANSITION": "NEUTRAL",
        "BEAR": "BEARISH",
        "STRONG_BEAR": "STRONG_BEARISH",
        "STRONG_BULLISH": "STRONG_BULLISH",
        "BULLISH": "BULLISH",
        "BEARISH": "BEARISH",
        "STRONG_BEARISH": "STRONG_BEARISH",
    }

    return mapping.get(value, value)


def extract_missing_symbols_from_wcb_raw(wcb_row: Dict[str, Any]) -> List[str]:
    raw = wcb_row.get("raw")
    if not isinstance(raw, dict):
        return []

    missing_intraday = raw.get("missing_intraday")
    if isinstance(missing_intraday, list):
        return [str(x) for x in missing_intraday if x is not None]

    return []


def extract_expected_constituents_from_wcb_raw(wcb_row: Dict[str, Any]) -> Optional[int]:
    raw = wcb_row.get("raw")
    if not isinstance(raw, dict):
        return None

    seeded_weight_rows = raw.get("seeded_weight_rows")
    return to_int(seeded_weight_rows)


def build_wcb_features(symbol: str, wcb_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not wcb_row:
        return None

    matched_constituents = to_int(wcb_row.get("constituent_count"))
    expected_constituents = extract_expected_constituents_from_wcb_raw(wcb_row)
    matched_weight_pct = to_float(wcb_row.get("active_weight_pct"))
    missing_symbols = extract_missing_symbols_from_wcb_raw(wcb_row)
    wcb_score = to_float(wcb_row.get("wcb_score"))
    wcb_regime = normalize_wcb_regime(wcb_row.get("wcb_regime"))
    snapshot_ts = wcb_row.get("ts")

    weights_mode = "TOP10_OFFICIAL_PLUS_RESIDUAL_PLACEHOLDER"

    is_partial = False
    if matched_weight_pct is not None and matched_weight_pct < 100.0:
        is_partial = True
    if missing_symbols:
        is_partial = True

    return clean_json(
        {
            "symbol": symbol,
            "snapshot_ts": snapshot_ts,
            "wcb_score": wcb_score,
            "wcb_regime": wcb_regime,
            "matched_constituents": matched_constituents,
            "expected_constituents": expected_constituents,
            "matched_weight_pct": matched_weight_pct,
            "missing_symbols": missing_symbols,
            "phase": "WCB_PHASE_1",
            "weights_mode": weights_mode,
            "is_partial": is_partial,
            "source_table": "weighted_constituent_breadth_snapshots",
        }
    )


def build_market_state_raw(
    gamma_table: str,
    breadth_table: str,
    volatility_table: str,
    momentum_table: str,
    wcb_attached: bool,
) -> Dict[str, Any]:
    return clean_json(
        {
            "builder": "build_market_state_snapshot_local.py",
            "builder_version": "WCB_MEASUREMENT_V2",
            "gamma_source_table": gamma_table,
            "breadth_source_table": breadth_table,
            "volatility_source_table": volatility_table,
            "momentum_source_table": momentum_table,
            "wcb_source_table": "weighted_constituent_breadth_snapshots" if wcb_attached else None,
            "built_at_utc": utc_now_iso(),
        }
    )


# ============================================================
# FETCHERS
# ============================================================

def fetch_latest_gamma(client: SupabaseRestClient, symbol: str) -> Tuple[str, Dict[str, Any]]:
    row = select_latest_by_symbol(client, "gamma_metrics", "symbol", symbol)
    if not row:
        raise RuntimeError(f"No gamma row found for symbol={symbol}")
    return "gamma_metrics", row


def fetch_latest_volatility(client: SupabaseRestClient, symbol: str) -> Tuple[str, Dict[str, Any]]:
    row = select_latest_by_symbol(client, "volatility_snapshots", "symbol", symbol)
    if not row:
        raise RuntimeError(f"No volatility row found for symbol={symbol}")
    return "volatility_snapshots", row


def fetch_latest_momentum(client: SupabaseRestClient, symbol: str) -> Tuple[str, Dict[str, Any]]:
    # Current working table in your environment
    row = select_latest_by_symbol(client, "momentum_snapshots", "symbol", symbol)
    if row:
        return "momentum_snapshots", row

    # Fallback if naming changes later
    row = select_latest_by_symbol(client, "momentum_features", "symbol", symbol)
    if row:
        return "momentum_features", row

    raise RuntimeError(f"No momentum row found for symbol={symbol}")


def fetch_latest_breadth(client: SupabaseRestClient) -> Tuple[str, Dict[str, Any]]:
    # Your current environment already showed this table works
    row = select_latest_any(client, "latest_market_breadth_intraday")
    if row:
        return "latest_market_breadth_intraday", row

    # Supabase hint suggested this may also exist in some environments
    row = select_latest_any(client, "latest_market_breadth_nse")
    if row:
        return "latest_market_breadth_nse", row

    # Final fallback
    row = select_latest_any(client, "market_breadth_intraday")
    if row:
        return "market_breadth_intraday", row

    raise RuntimeError("No breadth row found in latest_market_breadth_intraday / latest_market_breadth_nse / market_breadth_intraday")


def fetch_latest_wcb(client: SupabaseRestClient, symbol: str) -> Optional[Dict[str, Any]]:
    row = select_latest_by_symbol(client, "weighted_constituent_breadth_snapshots", "index_symbol", symbol)
    if row:
        return row

    print(f"[WARN] No WCB row found for symbol={symbol}. Continuing with wcb_features = null.")
    return None


# ============================================================
# BUILD + INSERT
# ============================================================

def build_payload(
    symbol: str,
    gamma_row: Dict[str, Any],
    gamma_table: str,
    breadth_row: Dict[str, Any],
    breadth_table: str,
    volatility_row: Dict[str, Any],
    volatility_table: str,
    momentum_row: Dict[str, Any],
    momentum_table: str,
    wcb_row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    ts = first_non_empty(gamma_row, ["ts", "created_at"]) or utc_now_iso()
    spot = to_float(first_non_empty(gamma_row, ["spot", "underlying_spot", "index_spot"]))
    futures_price = to_float(first_non_empty(gamma_row, ["futures_price"]))
    basis = to_float(first_non_empty(gamma_row, ["basis"]))
    basis_pct = to_float(first_non_empty(gamma_row, ["basis_pct"]))
    expiry_date = first_non_empty(gamma_row, ["expiry_date"])
    expiry_type = first_non_empty(gamma_row, ["expiry_type"])
    dte = to_int(first_non_empty(gamma_row, ["dte"]))
    gamma_run_id = first_non_empty(gamma_row, ["run_id", "gamma_run_id", "source_run_id"])

    gamma_features = clean_json(
        {
            "gamma_regime": first_non_empty(gamma_row, ["gamma_regime"]),
            "net_gex": to_float(first_non_empty(gamma_row, ["net_gex"])),
            "gamma_concentration": to_float(first_non_empty(gamma_row, ["gamma_concentration"])),
            "flip_level": to_float(first_non_empty(gamma_row, ["flip_level"])),
            "flip_distance": to_float(first_non_empty(gamma_row, ["flip_distance"])),
            "flip_distance_pct": to_float(first_non_empty(gamma_row, ["flip_distance_pct"])),
            "straddle_atm": to_float(first_non_empty(gamma_row, ["straddle_atm"])),
            "straddle_slope": to_float(first_non_empty(gamma_row, ["straddle_slope"])),
            "source_table": gamma_table,
            "raw_ref_ts": first_non_empty(gamma_row, ["ts", "created_at"]),
        }
    )

    breadth_features = clean_json(
        {
            "breadth_regime": first_non_empty(breadth_row, ["breadth_regime", "regime"]),
            "breadth_score": to_float(first_non_empty(breadth_row, ["breadth_score", "score"])),
            "advances": to_int(first_non_empty(breadth_row, ["advances"])),
            "declines": to_int(first_non_empty(breadth_row, ["declines"])),
            "up_4pct": to_int(first_non_empty(breadth_row, ["up_4pct"])),
            "down_4pct": to_int(first_non_empty(breadth_row, ["down_4pct"])),
            "pct_above_10dma": to_float(first_non_empty(breadth_row, ["pct_above_10dma"])),
            "pct_above_20dma": to_float(first_non_empty(breadth_row, ["pct_above_20dma"])),
            "pct_above_40dma": to_float(first_non_empty(breadth_row, ["pct_above_40dma"])),
            "pct_10gt20": to_float(first_non_empty(breadth_row, ["pct_10gt20"])),
            "pct_20gt40": to_float(first_non_empty(breadth_row, ["pct_20gt40"])),
            "universe_count": to_int(first_non_empty(breadth_row, ["universe_count"])),
            "source_table": breadth_table,
            "raw_ref_ts": first_non_empty(breadth_row, ["ts", "created_at"]),
        }
    )

    volatility_features = clean_json(
        {
            "volatility_regime": first_non_empty(volatility_row, ["volatility_regime", "iv_regime", "regime"]),
            "india_vix": to_float(first_non_empty(volatility_row, ["india_vix"])),
            "vix_change": to_float(first_non_empty(volatility_row, ["vix_change"])),
            "vix_regime": first_non_empty(volatility_row, ["vix_regime"]),
            "atm_strike": to_int(first_non_empty(volatility_row, ["atm_strike"])),
            "atm_call_iv": to_float(first_non_empty(volatility_row, ["atm_call_iv"])),
            "atm_put_iv": to_float(first_non_empty(volatility_row, ["atm_put_iv"])),
            "atm_iv_avg": to_float(first_non_empty(volatility_row, ["atm_iv_avg"])),
            "iv_skew": to_float(first_non_empty(volatility_row, ["iv_skew"])),
            "source_table": volatility_table,
            "raw_ref_ts": first_non_empty(volatility_row, ["ts", "created_at"]),
        }
    )

    momentum_features = clean_json(
        {
            "momentum_regime": first_non_empty(momentum_row, ["momentum_regime", "regime"]),
            "ret_session": to_float(first_non_empty(momentum_row, ["ret_session"])),
            "ret_30m": to_float(first_non_empty(momentum_row, ["ret_30m"])),
            "ret_60m": to_float(first_non_empty(momentum_row, ["ret_60m"])),
            "vwap_slope": to_float(first_non_empty(momentum_row, ["vwap_slope"])),
            "source_table": momentum_table,
            "raw_ref_ts": first_non_empty(momentum_row, ["ts", "created_at"]),
        }
    )

    wcb_features = build_wcb_features(symbol, wcb_row)

    raw_payload = build_market_state_raw(
        gamma_table=gamma_table,
        breadth_table=breadth_table,
        volatility_table=volatility_table,
        momentum_table=momentum_table,
        wcb_attached=(wcb_features is not None),
    )

    payload = clean_json(
        {
            "ts": ts,
            "symbol": symbol,
            "spot": spot,
            "futures_price": futures_price,
            "basis": basis,
            "basis_pct": basis_pct,
            "expiry_date": expiry_date,
            "expiry_type": expiry_type,
            "dte": dte,
            "gamma_run_id": gamma_run_id,
            "gamma_features": gamma_features,
            "breadth_features": breadth_features,
            "volatility_features": volatility_features,
            "momentum_features": momentum_features,
            "wcb_features": wcb_features,
            "raw": raw_payload,
        }
    )

    return payload


def main() -> None:
    load_environment()

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python build_market_state_snapshot_local.py NIFTY|SENSEX")

    symbol = normalize_symbol(sys.argv[1])

    supabase_url = require_env("SUPABASE_URL")
    service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    if service_role:
        api_key = service_role
    elif anon_key:
        api_key = anon_key
    else:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY")

    client = SupabaseRestClient(supabase_url, api_key)

    print("=" * 72)
    print("MERDIAN - Local Python build_market_state_snapshot")
    print("=" * 72)
    print(f"Symbol: {symbol}")
    print("-" * 72)

    gamma_table, gamma_row = fetch_latest_gamma(client, symbol)
    print(f"Gamma source table:       {gamma_table}")

    breadth_table, breadth_row = fetch_latest_breadth(client)
    print(f"Breadth source table:     {breadth_table}")

    volatility_table, volatility_row = fetch_latest_volatility(client, symbol)
    print(f"Volatility source table:  {volatility_table}")

    momentum_table, momentum_row = fetch_latest_momentum(client, symbol)
    print(f"Momentum source table:    {momentum_table}")

    wcb_row = fetch_latest_wcb(client, symbol)
    print(f"WCB source table:         {'weighted_constituent_breadth_snapshots' if wcb_row else 'NONE'}")

    payload = build_payload(
        symbol=symbol,
        gamma_row=gamma_row,
        gamma_table=gamma_table,
        breadth_row=breadth_row,
        breadth_table=breadth_table,
        volatility_row=volatility_row,
        volatility_table=volatility_table,
        momentum_row=momentum_row,
        momentum_table=momentum_table,
        wcb_row=wcb_row,
    )

    inserted = client.insert("market_state_snapshots", payload)
    inserted_row = inserted[0] if inserted else {}

    print("-" * 72)
    print("Market state snapshot inserted successfully.")
    print(f"Inserted ID:              {inserted_row.get('id')}")
    print(f"Snapshot TS:              {inserted_row.get('ts')}")
    print(f"Symbol:                   {inserted_row.get('symbol')}")
    print(f"WCB attached:             {'YES' if payload.get('wcb_features') else 'NO'}")

    wcb_features = payload.get("wcb_features") or {}
    print(f"WCB regime:               {wcb_features.get('wcb_regime')}")
    print(f"WCB score:                {wcb_features.get('wcb_score')}")
    print(f"WCB matched weight pct:   {wcb_features.get('matched_weight_pct')}")
    print("=" * 72)


if __name__ == "__main__":
    main()