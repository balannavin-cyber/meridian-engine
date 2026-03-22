import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.supabase_client import SupabaseClient


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _select_latest_one(
    sb: SupabaseClient,
    table: str,
    filters: Optional[Dict[str, str]] = None,
    order: str = "ts.desc",
) -> Optional[Dict[str, Any]]:
    rows = sb.select(
        table=table,
        filters=filters or {},
        order=order,
        limit=1,
    )
    if not rows:
        return None
    return rows[0]


def _select_rows(
    sb: SupabaseClient,
    table: str,
    filters: Optional[Dict[str, str]] = None,
    order: str = "ts.desc",
    limit: int = 10,
) -> List[Dict[str, Any]]:
    return sb.select(
        table=table,
        filters=filters or {},
        order=order,
        limit=limit,
    )


def _fetch_latest_gamma_row(sb: SupabaseClient, symbol: str) -> Dict[str, Any]:
    row = _select_latest_one(
        sb,
        table="gamma_metrics",
        filters={"symbol": f"eq.{symbol}"},
        order="ts.desc",
    )
    if row is None:
        raise RuntimeError(f"No gamma_metrics row found for symbol={symbol}")
    return row


def _fetch_latest_volatility_row(sb: SupabaseClient, symbol: str) -> Optional[Dict[str, Any]]:
    return _select_latest_one(
        sb,
        table="volatility_snapshots",
        filters={"symbol": f"eq.{symbol}"},
        order="created_at.desc",
    )


def _fetch_latest_momentum_row_for_ts(
    sb: SupabaseClient,
    symbol: str,
    target_ts: str,
) -> Optional[Dict[str, Any]]:
    rows = _select_rows(
        sb,
        table="momentum_snapshots",
        filters={
            "symbol": f"eq.{symbol}",
            "ts": f"eq.{target_ts}",
        },
        order="created_at.desc",
        limit=10,
    )
    if rows:
        return rows[0]

    return _select_latest_one(
        sb,
        table="momentum_snapshots",
        filters={"symbol": f"eq.{symbol}"},
        order="created_at.desc",
    )


def _fetch_latest_breadth_row_for_ts(
    sb: SupabaseClient,
    target_ts: str,
) -> Optional[Dict[str, Any]]:
    row = _select_latest_one(
        sb,
        table="latest_market_breadth_intraday",
        filters=None,
        order="ts.desc",
    )
    if row is not None:
        row["_source_table"] = "latest_market_breadth_intraday"
        return row

    row = _select_latest_one(
        sb,
        table="market_breadth_intraday",
        filters=None,
        order="ts.desc",
    )
    if row is not None:
        row["_source_table"] = "market_breadth_intraday"
        return row

    return None


def _build_gamma_features(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ts": row.get("ts"),
        "regime": row.get("regime"),
        "run_id": row.get("run_id"),
        "net_gex": _to_float(row.get("net_gex")),
        "flip_level": _to_float(row.get("flip_level")),
        "straddle_atm": _to_float(row.get("straddle_atm")),
        "flip_distance": _to_float(row.get("flip_distance")),
        "straddle_slope": _to_float(row.get("straddle_slope")),
        "gamma_concentration": _to_float(row.get("gamma_concentration")),
    }


def _build_volatility_features(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if row is None:
        return {}

    return {
        "ts": row.get("ts"),
        "iv_skew": _to_float(row.get("iv_skew")),
        "india_vix": _to_float(row.get("india_vix")),
        "atm_iv_avg": _to_float(row.get("atm_iv_avg")),
        "atm_put_iv": _to_float(row.get("atm_put_iv")),
        "atm_strike": _to_int(row.get("atm_strike")),
        "vix_change": _to_float(row.get("vix_change")),
        "vix_regime": row.get("vix_regime"),
        "atm_call_iv": _to_float(row.get("atm_call_iv")),
        "source_run_id": row.get("source_run_id"),
        "expiry_type": row.get("expiry_type"),
        "dte": _to_int(row.get("dte")),
        "created_at": row.get("created_at"),
    }


def _build_breadth_features(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if row is None:
        return {}

    return {
        "ts": row.get("ts"),
        "up_4pct": _to_int(row.get("up_4pct")),
        "advances": _to_int(row.get("advances")),
        "declines": _to_int(row.get("declines")),
        "down_4pct": _to_int(row.get("down_4pct")),
        "pct_10gt20": _to_float(row.get("pct_10gt20")),
        "pct_20gt40": _to_float(row.get("pct_20gt40")),
        "universe_id": row.get("universe_id"),
        "source_table": row.get("_source_table"),
        "breadth_score": _to_float(row.get("breadth_score")),
        "breadth_regime": row.get("breadth_regime"),
        "universe_count": _to_int(row.get("universe_count")),
        "pct_above_10dma": _to_float(row.get("pct_above_10dma")),
        "pct_above_20dma": _to_float(row.get("pct_above_20dma")),
        "pct_above_40dma": _to_float(row.get("pct_above_40dma")),
    }


def _build_momentum_features(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if row is None:
        return {}

    return {
        "ts": row.get("ts"),
        "ret_5m": _to_float(row.get("ret_5m")),
        "ret_15m": _to_float(row.get("ret_15m")),
        "ret_30m": _to_float(row.get("ret_30m")),
        "breadth_score_change": _to_float(row.get("breadth_score_change")),
        "ad_delta": _to_int(row.get("ad_delta")),
        "price_vs_vwap_pct": _to_float(row.get("price_vs_vwap_pct")),
        "vwap_slope": _to_float(row.get("vwap_slope")),
        "atm_straddle_change": _to_float(row.get("atm_straddle_change")),
        "session_vwap": _to_float(row.get("session_vwap")),
        "source": row.get("source"),
        "source_table": "momentum_snapshots",
        "created_at": row.get("created_at"),
    }


def _write_preview_file(symbol: str, payload: Dict[str, Any]) -> Path:
    out_file = DATA_DIR / f"latest_market_state_{symbol}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return out_file


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: python .\\build_market_state_snapshot_local.py NIFTY")

    symbol = sys.argv[1].strip().upper()

    print("=" * 72)
    print("Gamma Engine - Local Python build_market_state_snapshot")
    print("=" * 72)
    print(f"Symbol: {symbol}")
    print("-" * 72)

    sb = SupabaseClient()

    gamma_row = _fetch_latest_gamma_row(sb, symbol)
    gamma_ts = gamma_row.get("ts")

    volatility_row = _fetch_latest_volatility_row(sb, symbol)
    breadth_row = _fetch_latest_breadth_row_for_ts(sb, gamma_ts)
    momentum_row = _fetch_latest_momentum_row_for_ts(sb, symbol, gamma_ts)

    market_state_row = {
        "ts": gamma_row.get("ts"),
        "symbol": gamma_row.get("symbol"),
        "spot": _to_float(gamma_row.get("spot")),
        "futures_price": None,
        "basis": None,
        "basis_pct": None,
        "expiry_date": gamma_row.get("expiry_date"),
        "expiry_type": volatility_row.get("expiry_type") if volatility_row else None,
        "dte": _to_int(volatility_row.get("dte")) if volatility_row else None,
        "gamma_run_id": gamma_row.get("run_id"),
        "gamma_features": _build_gamma_features(gamma_row),
        "breadth_features": _build_breadth_features(breadth_row),
        "volatility_features": _build_volatility_features(volatility_row),
        "momentum_features": _build_momentum_features(momentum_row),
        "raw": {
            "gamma_row": gamma_row,
            "breadth_row": breadth_row,
            "volatility_row": volatility_row,
            "momentum_row": momentum_row,
        },
    }

    print("Computed market state row:")
    print(json.dumps(market_state_row, indent=2, default=str))

    print("-" * 72)
    print("Writing market state row to Supabase...")

    inserted = sb.insert("market_state_snapshots", [market_state_row])
    inserted_count = len(inserted) if isinstance(inserted, list) else 1

    print(f"Inserted rows returned by Supabase: {inserted_count}")

    out_file = _write_preview_file(symbol, market_state_row)
    print(f"Saved preview to: {out_file}")
    print("BUILD MARKET STATE SNAPSHOT COMPLETED")


if __name__ == "__main__":
    main()