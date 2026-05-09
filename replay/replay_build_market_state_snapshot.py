"""
replay.replay_build_market_state_snapshot — Replay mirror of build_market_state_snapshot_local.py.

Differences from build_market_state_snapshot_local.py:
  1. Reads gamma_metrics_replay, volatility_snapshots_replay, momentum_snapshots_replay 
     filtered by ts <= replay_ts (mirrors live "latest at or before" semantics).
  2. Reads market_breadth_intraday LIVE filtered by replay_date + ts <= replay_ts.
  3. Reads weighted_constituent_breadth_snapshots LIVE filtered by index_symbol + ts <= replay_ts.
  4. Writes market_state_snapshots_replay (UPSERT on symbol, ts).
  5. CLI: --replay-ts, --symbol.

Live impact: ZERO writes to live. READS from market_breadth_intraday and
weighted_constituent_breadth_snapshots (immutable past data — same pattern as OI lift).

Author: Session 24 (2026-05-09)
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from replay.replay_clock import parse_replay_ts, replay_today_ist, to_iso_utc
from replay.replay_execution_log import ExecutionLog


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

    def select_raw(
        self,
        table: str,
        params: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{table}"
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected response for table={table}")
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
        return rows[0] if rows else {}


def fetch_replay_upstream_row(
    client: SupabaseRestClient,
    table: str,
    symbol: str,
    replay_ts_iso: str,
    symbol_field: str = "symbol",
) -> Optional[Dict[str, Any]]:
    """Read latest row at-or-before replay_ts from a _replay table."""
    try:
        rows = client.select_raw(
            table,
            {
                "select": "*",
                symbol_field: f"eq.{symbol}",
                "ts": f"lte.{replay_ts_iso}",
                "order": "ts.desc",
                "limit": "1",
            },
        )
        return rows[0] if rows else None
    except Exception:
        return None


def fetch_live_breadth_row(
    client: SupabaseRestClient,
    replay_date_iso: str,
    replay_ts_iso: str,
) -> Optional[Dict[str, Any]]:
    """Read live market_breadth_intraday for replay_date, latest at-or-before replay_ts."""
    try:
        rows = client.select_raw(
            "market_breadth_intraday",
            {
                "select": "*",
                "ts": f"lte.{replay_ts_iso}",
                "ts": f"gte.{replay_date_iso}T00:00:00Z",
                "order": "ts.desc",
                "limit": "1",
            },
        )
        # NOTE: PostgREST allows duplicate keys but only the last wins. We need 2 ts filters.
        # Workaround: use ts=lte.X AND ts=gte.Y via separate logic.
    except Exception:
        return None
    # Alternative: filter date in Python
    try:
        rows = client.select_raw(
            "market_breadth_intraday",
            {
                "select": "*",
                "ts": f"lte.{replay_ts_iso}",
                "order": "ts.desc",
                "limit": "20",
            },
        )
    except Exception:
        return None
    for row in rows or []:
        ts_str = row.get("ts", "")
        if ts_str.startswith(replay_date_iso):
            return row
    return None


def fetch_live_wcb_row(
    client: SupabaseRestClient,
    symbol: str,
    replay_ts_iso: str,
) -> Optional[Dict[str, Any]]:
    """Read live weighted_constituent_breadth_snapshots for index_symbol at-or-before replay_ts."""
    try:
        rows = client.select_raw(
            "weighted_constituent_breadth_snapshots",
            {
                "select": "*",
                "index_symbol": f"eq.{symbol}",
                "ts": f"lte.{replay_ts_iso}",
                "order": "ts.desc",
                "limit": "1",
            },
        )
        return rows[0] if rows else None
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
        "source_table": "gamma_metrics_replay",
        "raw_ref_ts": gamma_row.get("ts"),
    }


def build_breadth_features(breadth_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not breadth_row:
        return {
            "breadth_regime": None, "breadth_score": None, "advances": None, "declines": None,
            "up_4pct": None, "down_4pct": None, "pct_above_10dma": None, "pct_above_20dma": None,
            "pct_above_40dma": None, "pct_10gt20": None, "pct_20gt40": None, "universe_count": None,
            "source_table": None, "raw_ref_ts": None,
        }
    return {
        "breadth_regime": breadth_row.get("breadth_regime"),
        "breadth_score": breadth_row.get("breadth_score"),
        "advances": breadth_row.get("advances"),
        "declines": breadth_row.get("declines"),
        "up_4pct": breadth_row.get("up_4pct"),
        "down_4pct": breadth_row.get("down_4pct"),
        "pct_above_10dma": breadth_row.get("pct_above_10dma"),
        "pct_above_20dma": breadth_row.get("pct_above_20dma"),
        "pct_above_40dma": breadth_row.get("pct_above_40dma"),
        "pct_10gt20": breadth_row.get("pct_10gt20"),
        "pct_20gt40": breadth_row.get("pct_20gt40"),
        "universe_count": breadth_row.get("universe_count"),
        "source_table": "market_breadth_intraday",
        "raw_ref_ts": breadth_row.get("ts"),
    }


def build_volatility_features(volatility_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not volatility_row:
        return {
            "volatility_regime": None, "india_vix": None, "vix_change": None, "vix_regime": None,
            "atm_strike": None, "atm_call_iv": None, "atm_put_iv": None, "atm_iv_avg": None,
            "iv_skew": None, "source_table": None, "raw_ref_ts": None,
        }
    return {
        "volatility_regime": volatility_row.get("volatility_regime"),
        "india_vix": volatility_row.get("india_vix"),
        "vix_change": volatility_row.get("vix_change"),
        "vix_regime": volatility_row.get("vix_regime"),
        "atm_strike": volatility_row.get("atm_strike"),
        "atm_call_iv": volatility_row.get("atm_call_iv"),
        "atm_put_iv": volatility_row.get("atm_put_iv"),
        "atm_iv_avg": volatility_row.get("atm_iv_avg"),
        "iv_skew": volatility_row.get("iv_skew"),
        "source_table": "volatility_snapshots_replay",
        "raw_ref_ts": volatility_row.get("ts"),
    }


def build_momentum_features(momentum_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not momentum_row:
        return {
            "momentum_regime": None, "ret_session": None, "ret_30m": None, "ret_60m": None,
            "vwap_slope": None, "source_table": None, "raw_ref_ts": None,
        }
    return {
        "momentum_regime": momentum_row.get("momentum_regime"),
        "ret_session": momentum_row.get("ret_session"),
        "ret_30m": momentum_row.get("ret_30m"),
        "ret_60m": momentum_row.get("ret_60m"),
        "vwap_slope": momentum_row.get("vwap_slope"),
        "source_table": "momentum_snapshots_replay",
        "raw_ref_ts": momentum_row.get("ts"),
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


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="replay_build_market_state_snapshot")
    parser.add_argument("--replay-ts", required=True)
    parser.add_argument("--symbol", required=True, choices=["NIFTY", "SENSEX"])
    return parser.parse_args(argv)


def main() -> int:
    load_dotenv()
    try:
        args = parse_args(sys.argv[1:])
    except SystemExit:
        raise

    try:
        replay_ts = parse_replay_ts(args.replay_ts)
    except ValueError as e:
        print(f"[ERROR] Invalid --replay-ts: {e}", file=sys.stderr)
        return 2

    symbol = args.symbol.upper()
    replay_date = replay_today_ist(replay_ts)
    replay_ts_iso = to_iso_utc(replay_ts)
    replay_date_iso = replay_date.isoformat()

    log = ExecutionLog(
        script_name="replay_build_market_state_snapshot.py",
        expected_writes={"market_state_snapshots_replay": 1},
        symbol=symbol,
        notes=f"6-component JSONB state replay_ts={args.replay_ts}",
    )

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )
    if not supabase_url:
        return log.exit_with_reason("DEPENDENCY_MISSING", 1, error_message="SUPABASE_URL missing")
    if not supabase_key:
        return log.exit_with_reason("DEPENDENCY_MISSING", 1, error_message="SUPABASE keys missing")

    try:
        client = SupabaseRestClient(supabase_url, supabase_key)
    except Exception as e:
        return log.exit_with_reason("DEPENDENCY_MISSING", 1, error_message=f"SupabaseRestClient init failed: {e}")

    print("=" * 72)
    print("MERDIAN REPLAY - replay_build_market_state_snapshot")
    print("=" * 72)
    print(f"replay_ts={args.replay_ts}")
    print(f"replay_date={replay_date}")
    print(f"symbol={symbol}")

    # gamma_metrics_replay is REQUIRED upstream
    try:
        gamma_row = fetch_replay_upstream_row(client, "gamma_metrics_replay", symbol, replay_ts_iso)
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"gamma_metrics_replay fetch failed: {e}")

    if not gamma_row:
        return log.exit_with_reason(
            "SKIPPED_NO_INPUT", 1,
            error_message=f"No gamma_metrics_replay row for {symbol} at/before {replay_ts_iso}. "
                          "Upstream replay_compute_gamma_metrics has not produced output."
        )

    # Optional sources
    volatility_row = fetch_replay_upstream_row(client, "volatility_snapshots_replay", symbol, replay_ts_iso)
    momentum_row = fetch_replay_upstream_row(client, "momentum_snapshots_replay", symbol, replay_ts_iso)
    breadth_row = fetch_live_breadth_row(client, replay_date_iso, replay_ts_iso)
    wcb_row = fetch_live_wcb_row(client, symbol, replay_ts_iso)

    degraded_inputs = []
    if not volatility_row:
        degraded_inputs.append("vol")
    if not momentum_row:
        degraded_inputs.append("mom")
    if not breadth_row:
        degraded_inputs.append("breadth")
    if not wcb_row:
        degraded_inputs.append("wcb")

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
            "builder": "replay_build_market_state_snapshot.py",
            "builder_version": "REPLAY_V1",
            "gamma_source_table": "gamma_metrics_replay",
            "volatility_source_table": "volatility_snapshots_replay" if volatility_row else None,
            "momentum_source_table": "momentum_snapshots_replay" if momentum_row else None,
            "breadth_source_table": "market_breadth_intraday" if breadth_row else None,
            "wcb_source_table": "weighted_constituent_breadth_snapshots" if wcb_row else None,
            "replay_date": replay_date_iso,
            "replay_ts": replay_ts_iso,
            "degraded_inputs": degraded_inputs,
            "built_at_utc": utc_now_iso(),
        },
    }

    try:
        upserted = client.upsert("market_state_snapshots_replay", payload, on_conflict="symbol,ts")
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"market_state_snapshots_replay upsert failed: {e}")

    print(f"upserted_id={upserted.get('id')}")
    print(f"ts={upserted.get('ts')}")
    print(f"gamma_regime={payload['gamma_features'].get('gamma_regime')}")
    print(f"flip_distance_pct={payload['gamma_features'].get('flip_distance_pct')}")
    print(f"breadth_regime={payload['breadth_features'].get('breadth_regime')}")
    print(f"vix_regime={payload['volatility_features'].get('vix_regime')}")
    print(f"momentum_regime={payload['momentum_features'].get('momentum_regime')}")
    print(f"wcb_attached={'YES' if payload.get('wcb_features') else 'NO'}")
    print(f"degraded_inputs={degraded_inputs}")

    log.record_write("market_state_snapshots_replay", 1)
    completion_notes = None
    if degraded_inputs:
        completion_notes = f"replay_ts={args.replay_ts} degraded={','.join(degraded_inputs)}"
    return log.complete(notes=completion_notes)


if __name__ == "__main__":
    sys.exit(main())