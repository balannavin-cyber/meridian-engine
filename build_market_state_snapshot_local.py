#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


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
        order: str = "ts.desc",
        limit: int = 1,
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{table}"
        params: Dict[str, str] = {"select": "*", "order": order, "limit": str(limit)}
        if filters:
            params.update(filters)

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected response for table={table}: {data}")
        return data

    def upsert(self, table: str, payload: Dict[str, Any], on_conflict: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{table}"
        headers = dict(self.headers)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        response = requests.post(
            f"{url}?on_conflict={on_conflict}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return {}
        return rows[0]


def first_row_or_none(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return rows[0] if rows else None


def fetch_symbol_row(client: SupabaseRestClient, table: str, symbol: str) -> Optional[Dict[str, Any]]:
    try:
        return first_row_or_none(client.select(table, filters={"symbol": f"eq.{symbol}"}))
    except Exception:
        return None


def fetch_global_row(client: SupabaseRestClient, table: str) -> Optional[Dict[str, Any]]:
    try:
        return first_row_or_none(client.select(table))
    except Exception:
        return None


def fetch_wcb_row(client: SupabaseRestClient, symbol: str) -> Optional[Dict[str, Any]]:
    try:
        return first_row_or_none(
            client.select(
                "weighted_constituent_breadth_snapshots",
                filters={"index_symbol": f"eq.{symbol}"},
            )
        )
    except Exception:
        return None


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        x = float(value)
        if math.isnan(x) or math.isinf(x):
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


def build_gamma_features(gamma_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    D-06 normalization:
    - flip_distance_pct is the canonical field for all downstream decision logic
    - flip_distance_points is retained as the raw point-distance diagnostic
    - flip_distance is preserved for backward compatibility, but should be treated
      as secondary/debug only
    """
    flip_distance_points = to_float(gamma_row.get("flip_distance"))
    flip_distance_pct = to_float(gamma_row.get("flip_distance_pct"))

    return {
        "gamma_regime": gamma_row.get("regime"),
        "net_gex": gamma_row.get("net_gex"),
        "gamma_concentration": gamma_row.get("gamma_concentration"),
        "flip_level": gamma_row.get("flip_level"),
        "flip_distance": flip_distance_points,
        "flip_distance_points": flip_distance_points,
        "flip_distance_pct": flip_distance_pct,
        "flip_distance_canonical": flip_distance_pct,
        "flip_distance_canonical_unit": "pct",
        "straddle_atm": gamma_row.get("straddle_atm"),
        "straddle_slope": gamma_row.get("straddle_slope"),
        "source_table": "gamma_metrics",
        "raw_ref_ts": gamma_row.get("ts"),
    }


def build_breadth_features(breadth_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "breadth_regime": breadth_row.get("breadth_regime") if breadth_row else None,
        "breadth_score": breadth_row.get("breadth_score") if breadth_row else None,
        "advances": breadth_row.get("advances") if breadth_row else None,
        "declines": breadth_row.get("declines") if breadth_row else None,
        "up_4pct": breadth_row.get("up_4pct") if breadth_row else None,
        "down_4pct": breadth_row.get("down_4pct") if breadth_row else None,
        "pct_above_10dma": breadth_row.get("pct_above_10dma") if breadth_row else None,
        "pct_above_20dma": breadth_row.get("pct_above_20dma") if breadth_row else None,
        "pct_above_40dma": breadth_row.get("pct_above_40dma") if breadth_row else None,
        "pct_10gt20": breadth_row.get("pct_10gt20") if breadth_row else None,
        "pct_20gt40": breadth_row.get("pct_20gt40") if breadth_row else None,
        "universe_count": breadth_row.get("universe_count") if breadth_row else None,
        "source_table": "latest_market_breadth_intraday" if breadth_row else None,
        "raw_ref_ts": breadth_row.get("ts") if breadth_row else None,
    }


def build_volatility_features(volatility_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "volatility_regime": volatility_row.get("volatility_regime") if volatility_row else None,
        "india_vix": volatility_row.get("india_vix") if volatility_row else None,
        "vix_change": volatility_row.get("vix_change") if volatility_row else None,
        "vix_regime": volatility_row.get("vix_regime") if volatility_row else None,
        "atm_strike": volatility_row.get("atm_strike") if volatility_row else None,
        "atm_call_iv": volatility_row.get("atm_call_iv") if volatility_row else None,
        "atm_put_iv": volatility_row.get("atm_put_iv") if volatility_row else None,
        "atm_iv_avg": volatility_row.get("atm_iv_avg") if volatility_row else None,
        "iv_skew": volatility_row.get("iv_skew") if volatility_row else None,
        "source_table": "volatility_snapshots" if volatility_row else None,
        "raw_ref_ts": volatility_row.get("ts") if volatility_row else None,
    }


def build_momentum_features(momentum_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "momentum_regime": momentum_row.get("momentum_regime") if momentum_row else None,
        "ret_session": momentum_row.get("ret_session") if momentum_row else None,
        "ret_30m": momentum_row.get("ret_30m") if momentum_row else None,
        "ret_60m": momentum_row.get("ret_60m") if momentum_row else None,
        "vwap_slope": momentum_row.get("vwap_slope") if momentum_row else None,
        "source_table": "momentum_snapshots" if momentum_row else None,
        "raw_ref_ts": momentum_row.get("ts") if momentum_row else None,
    }


def build_wcb_features(symbol: str, wcb_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not wcb_row:
        return None

    matched_weight_pct = to_float(wcb_row.get("active_weight_pct"))
    raw = wcb_row.get("raw")
    if matched_weight_pct is None and isinstance(raw, dict):
        matched_weight_pct = to_float(raw.get("active_weight_total"))

    raw_obj = wcb_row.get("raw")
    missing_symbols = raw_obj.get("missing_intraday", []) if isinstance(raw_obj, dict) else []

    return {
        "symbol": symbol,
        "snapshot_ts": wcb_row.get("ts"),
        "wcb_score": wcb_row.get("wcb_score"),
        "wcb_regime": wcb_row.get("wcb_regime"),
        "matched_constituents": to_int(wcb_row.get("constituent_count")),
        "expected_constituents": to_int(wcb_row.get("constituent_count")),
        "matched_weight_pct": matched_weight_pct,
        "missing_symbols": missing_symbols,
        "phase": "WCB_PHASE_1",
        "weights_mode": "TOP10_OFFICIAL_PLUS_RESIDUAL_PLACEHOLDER",
        "is_partial": matched_weight_pct is not None and matched_weight_pct < 100.0,
        "source_table": "weighted_constituent_breadth_snapshots",
    }


def main() -> None:
    load_environment()

    if len(sys.argv) != 2:
        raise RuntimeError("Usage: python build_market_state_snapshot_local.py NIFTY|SENSEX")

    symbol = sys.argv[1].strip().upper()
    if symbol not in {"NIFTY", "SENSEX"}:
        raise RuntimeError("Usage: python build_market_state_snapshot_local.py NIFTY|SENSEX")

    supabase_url = require_env("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not supabase_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY")

    client = SupabaseRestClient(supabase_url, supabase_key)

    gamma_row = fetch_symbol_row(client, "gamma_metrics", symbol)
    if not gamma_row:
        raise RuntimeError(f"No gamma row found for {symbol}")

    volatility_row = fetch_symbol_row(client, "volatility_snapshots", symbol)
    momentum_row = fetch_symbol_row(client, "momentum_snapshots", symbol)

    breadth_row = fetch_global_row(client, "latest_market_breadth_intraday")
    if not breadth_row:
        breadth_row = fetch_global_row(client, "market_breadth_intraday")

    wcb_row = fetch_wcb_row(client, symbol)

    payload = {
        "ts": gamma_row.get("ts"),
        "symbol": symbol,
        "spot": gamma_row.get("spot"),
        "futures_price": gamma_row.get("futures_price"),
        "basis": gamma_row.get("basis"),
        "basis_pct": gamma_row.get("basis_pct"),
        "expiry_date": gamma_row.get("expiry_date"),
        "expiry_type": gamma_row.get("expiry_type"),
        "dte": gamma_row.get("dte"),
        "gamma_run_id": gamma_row.get("run_id"),
        "gamma_features": build_gamma_features(gamma_row),
        "breadth_features": build_breadth_features(breadth_row),
        "volatility_features": build_volatility_features(volatility_row),
        "momentum_features": build_momentum_features(momentum_row),
        "wcb_features": build_wcb_features(symbol, wcb_row),
        "raw": {
            "builder": "build_market_state_snapshot_local.py",
            "builder_version": "D06_FLIP_DISTANCE_PCT_CANONICAL_V1",
            "gamma_source_table": "gamma_metrics",
            "breadth_source_table": "latest_market_breadth_intraday" if breadth_row else None,
            "volatility_source_table": "volatility_snapshots" if volatility_row else None,
            "momentum_source_table": "momentum_snapshots" if momentum_row else None,
            "wcb_source_table": "weighted_constituent_breadth_snapshots" if wcb_row else None,
            "d06_flip_distance_policy": {
                "canonical_field": "flip_distance_pct",
                "secondary_debug_field": "flip_distance_points",
                "backward_compat_field": "flip_distance",
            },
            "built_at_utc": utc_now_iso(),
        },
    }

    upserted = client.upsert("market_state_snapshots", payload, on_conflict="symbol,ts")

    print("=" * 72)
    print("MERDIAN - Local Python build_market_state_snapshot")
    print("=" * 72)
    print(f"Symbol: {symbol}")
    print("-" * 72)
    print("Market state snapshot upsert complete.")
    print(f"Upserted ID:              {upserted.get('id')}")
    print(f"Snapshot TS:              {upserted.get('ts')}")
    print(f"Symbol:                   {upserted.get('symbol')}")
    print(f"WCB attached:             {'YES' if payload.get('wcb_features') else 'NO'}")

    gamma_features = payload.get("gamma_features") or {}
    print(f"Gamma regime:             {gamma_features.get('gamma_regime')}")
    print(f"Flip distance pct:        {gamma_features.get('flip_distance_pct')}")
    print(f"Flip distance points:     {gamma_features.get('flip_distance_points')}")

    wcb_features = payload.get("wcb_features") or {}
    print(f"WCB regime:               {wcb_features.get('wcb_regime')}")
    print(f"WCB score:                {wcb_features.get('wcb_score')}")
    print(f"WCB matched weight pct:   {wcb_features.get('matched_weight_pct')}")
    print("=" * 72)


if __name__ == "__main__":
    main()