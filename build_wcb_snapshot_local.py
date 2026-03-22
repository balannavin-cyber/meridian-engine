from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.supabase_client import SupabaseClient
from gamma_engine_retry_utils import retry_call


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def to_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes", "y"}:
        return True
    if text in {"false", "f", "0", "no", "n"}:
        return False
    return None


def normalize_index_symbol(value: str) -> str:
    text = str(value).strip().upper()
    if text not in {"NIFTY", "SENSEX"}:
        raise RuntimeError(f"Unsupported index_symbol: {value}")
    return text


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_pct(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return (numerator / denominator) * 100.0


def classify_wcb_regime(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 60:
        return "BULLISH"
    if score <= 40:
        return "BEARISH"
    return "TRANSITION"


def fetch_active_weights(sb: SupabaseClient, index_symbol: str) -> List[Dict[str, Any]]:
    return retry_call(
        lambda: sb.select(
            table="index_constituent_weights",
            filters={
                "index_symbol": f"eq.{index_symbol}",
                "is_active": "eq.True",
            },
            order="weight_pct.desc",
            limit=500,
        ),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label=f"select active weights for {index_symbol}",
    )


def fetch_latest_intraday_prices(sb: SupabaseClient, tickers: List[str]) -> List[Dict[str, Any]]:
    if not tickers:
        return []

    in_payload = "(" + ",".join(tickers) + ")"

    return retry_call(
        lambda: sb.select(
            table="equity_intraday_last",
            filters={"ticker": f"in.{in_payload}"},
            limit=5000,
        ),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label="select equity_intraday_last for WCB basket",
    )


def fetch_daily_breadth_rows(sb: SupabaseClient, tickers: List[str]) -> List[Dict[str, Any]]:
    if not tickers:
        return []

    in_payload = "(" + ",".join(tickers) + ")"

    return retry_call(
        lambda: sb.select(
            table="breadth_indicators_daily",
            filters={"ticker": f"in.{in_payload}"},
            limit=5000,
        ),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label="select breadth_indicators_daily for WCB basket",
    )


def fetch_latest_market_breadth_intraday(sb: SupabaseClient) -> Optional[Dict[str, Any]]:
    rows = retry_call(
        lambda: sb.select(
            table="latest_market_breadth_intraday",
            order="ts.desc",
            limit=1,
        ),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label="select latest_market_breadth_intraday",
    )
    return rows[0] if rows else None


def build_price_map(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker:
            out[ticker] = row
    return out


def build_daily_map(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue

        existing = out.get(ticker)
        if existing is None:
            out[ticker] = row
            continue

        existing_td = str(existing.get("trade_date") or "")
        new_td = str(row.get("trade_date") or "")
        if new_td >= existing_td:
            out[ticker] = row

    return out


def compute_wcb_snapshot(
    *,
    index_symbol: str,
    weights_rows: List[Dict[str, Any]],
    intraday_rows: List[Dict[str, Any]],
    daily_rows: List[Dict[str, Any]],
    latest_breadth_row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    intraday_map = build_price_map(intraday_rows)
    daily_map = build_daily_map(daily_rows)

    active_weight_total = 0.0

    adv_w = 0.0
    dec_w = 0.0
    unchanged_w = 0.0

    up4_w = 0.0
    down4_w = 0.0

    above10_w = 0.0
    above20_w = 0.0
    above40_w = 0.0
    gt10_20_w = 0.0
    gt20_40_w = 0.0

    missing_intraday: List[str] = []
    missing_daily: List[str] = []
    constituent_debug: List[Dict[str, Any]] = []

    for row in weights_rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        company_name = row.get("company_name")
        weight_pct = to_float(row.get("weight_pct"))

        if not ticker or weight_pct is None:
            continue

        intraday = intraday_map.get(ticker)
        daily = daily_map.get(ticker)

        if intraday is None:
            missing_intraday.append(ticker)
            continue

        if daily is None:
            missing_daily.append(ticker)
            continue

        last_price = to_float(intraday.get("last_price"))
        prev_close = to_float(daily.get("prev_close"))

        dma10 = to_float(daily.get("dma10"))
        dma20 = to_float(daily.get("dma20"))
        dma40 = to_float(daily.get("dma40"))

        above_10 = to_bool(daily.get("above_10"))
        above_20 = to_bool(daily.get("above_20"))
        above_40 = to_bool(daily.get("above_40"))
        dma10_gt_20 = to_bool(daily.get("dma10_gt_20"))
        dma20_gt_40 = to_bool(daily.get("dma20_gt_40"))

        if last_price is None or prev_close is None or prev_close == 0:
            missing_daily.append(ticker)
            continue

        active_weight_total += weight_pct

        pct_change = ((last_price / prev_close) - 1.0) * 100.0

        if pct_change > 0:
            adv_w += weight_pct
        elif pct_change < 0:
            dec_w += weight_pct
        else:
            unchanged_w += weight_pct

        # IMPORTANT: intraday ±4% should be derived from live pct_change,
        # not from historical daily flags.
        if pct_change >= 4.0:
            up4_w += weight_pct
        if pct_change <= -4.0:
            down4_w += weight_pct

        if above_10 is True:
            above10_w += weight_pct
        if above_20 is True:
            above20_w += weight_pct
        if above_40 is True:
            above40_w += weight_pct
        if dma10_gt_20 is True:
            gt10_20_w += weight_pct
        if dma20_gt_40 is True:
            gt20_40_w += weight_pct

        constituent_debug.append(
            {
                "ticker": ticker,
                "company_name": company_name,
                "weight_pct": weight_pct,
                "trade_date": daily.get("trade_date"),
                "last_price": last_price,
                "prev_close": prev_close,
                "pct_change": pct_change,
                "dma10": dma10,
                "dma20": dma20,
                "dma40": dma40,
                "above_10": above_10,
                "above_20": above_20,
                "above_40": above_40,
                "dma10_gt_20": dma10_gt_20,
                "dma20_gt_40": dma20_gt_40,
                "intraday_flag_up4": pct_change >= 4.0,
                "intraday_flag_dn4": pct_change <= -4.0,
            }
        )

    weighted_advances_pct = safe_pct(adv_w, active_weight_total)
    weighted_declines_pct = safe_pct(dec_w, active_weight_total)
    weighted_unchanged_pct = safe_pct(unchanged_w, active_weight_total)

    weighted_up_4pct_pct = safe_pct(up4_w, active_weight_total)
    weighted_down_4pct_pct = safe_pct(down4_w, active_weight_total)

    weighted_pct_above_10dma = safe_pct(above10_w, active_weight_total)
    weighted_pct_above_20dma = safe_pct(above20_w, active_weight_total)
    weighted_pct_above_40dma = safe_pct(above40_w, active_weight_total)
    weighted_pct_10gt20 = safe_pct(gt10_20_w, active_weight_total)
    weighted_pct_20gt40 = safe_pct(gt20_40_w, active_weight_total)

    score_components = [
        weighted_advances_pct,
        weighted_pct_above_10dma,
        weighted_pct_above_20dma,
        weighted_pct_above_40dma,
        weighted_pct_10gt20,
        weighted_pct_20gt40,
    ]
    valid_components = [x for x in score_components if x is not None]
    wcb_score = sum(valid_components) / len(valid_components) if valid_components else None
    wcb_regime = classify_wcb_regime(wcb_score)

    snapshot_ts = (
        latest_breadth_row.get("ts")
        if latest_breadth_row and latest_breadth_row.get("ts") is not None
        else now_utc_iso()
    )

    return {
        "ts": snapshot_ts,
        "index_symbol": index_symbol,
        "constituent_count": len(constituent_debug),
        "active_weight_pct": active_weight_total,
        "weighted_advances_pct": weighted_advances_pct,
        "weighted_declines_pct": weighted_declines_pct,
        "weighted_unchanged_pct": weighted_unchanged_pct,
        "weighted_up_4pct_pct": weighted_up_4pct_pct,
        "weighted_down_4pct_pct": weighted_down_4pct_pct,
        "weighted_pct_above_10dma": weighted_pct_above_10dma,
        "weighted_pct_above_20dma": weighted_pct_above_20dma,
        "weighted_pct_above_40dma": weighted_pct_above_40dma,
        "weighted_pct_10gt20": weighted_pct_10gt20,
        "weighted_pct_20gt40": weighted_pct_20gt40,
        "wcb_score": wcb_score,
        "wcb_regime": wcb_regime,
        "source_table": "latest_market_breadth_intraday",
        "raw": {
            "seeded_weight_rows": len(weights_rows),
            "active_weight_total": active_weight_total,
            "missing_intraday": missing_intraday,
            "missing_daily": missing_daily,
            "latest_market_breadth_intraday": latest_breadth_row,
            "constituents_used": constituent_debug,
        },
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: python .\\build_wcb_snapshot_local.py <NIFTY|SENSEX>")

    index_symbol = normalize_index_symbol(sys.argv[1])

    print("=" * 72)
    print("MERDIAN - Local Python build_wcb_snapshot")
    print("=" * 72)
    print(f"Index symbol: {index_symbol}")
    print("-" * 72)

    sb = SupabaseClient()

    weights_rows = fetch_active_weights(sb, index_symbol)
    if not weights_rows:
        raise RuntimeError(f"No active constituent weights found for {index_symbol}")

    print(f"Active weight rows fetched: {len(weights_rows)}")

    tickers = [str(row["ticker"]).strip().upper() for row in weights_rows if row.get("ticker")]
    intraday_rows = fetch_latest_intraday_prices(sb, tickers)
    daily_rows = fetch_daily_breadth_rows(sb, tickers)
    latest_breadth_row = fetch_latest_market_breadth_intraday(sb)

    print(f"Intraday rows fetched: {len(intraday_rows)}")
    print(f"Daily breadth rows fetched: {len(daily_rows)}")

    snapshot_row = compute_wcb_snapshot(
        index_symbol=index_symbol,
        weights_rows=weights_rows,
        intraday_rows=intraday_rows,
        daily_rows=daily_rows,
        latest_breadth_row=latest_breadth_row,
    )

    print("-" * 72)
    print("Computed WCB snapshot:")
    print(json.dumps(snapshot_row, default=str, indent=2))

    print("-" * 72)
    print("Writing WCB snapshot to Supabase...")

    inserted = retry_call(
        lambda: sb.upsert(
            table="weighted_constituent_breadth_snapshots",
            rows=[snapshot_row],
            on_conflict="index_symbol,ts",
        ),
        attempts=3,
        delay_seconds=5.0,
        backoff_multiplier=1.5,
        label=f"upsert weighted_constituent_breadth_snapshots for {index_symbol}",
    )

    inserted_count = len(inserted) if isinstance(inserted, list) else 1
    print(f"Inserted rows returned by Supabase: {inserted_count}")
    print("BUILD WCB SNAPSHOT COMPLETED")


if __name__ == "__main__":
    main()