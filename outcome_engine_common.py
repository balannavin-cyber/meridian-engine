from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


UTC = timezone.utc


@dataclass
class SpotPoint:
    ts: datetime
    spot: float


def parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def safe_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    return None


def outcome_label(action: Optional[str], move_points: Optional[float], flat_threshold: float = 5.0) -> str:
    if not action or action == "DO_NOTHING":
        return "NO_TRADE"

    if move_points is None:
        return "PENDING"

    if abs(move_points) <= flat_threshold:
        return "FLAT"

    if action == "BUY_CE":
        return "WIN" if move_points > 0 else "LOSS"

    if action == "BUY_PE":
        return "WIN" if move_points < 0 else "LOSS"

    return "UNKNOWN"


def session_eod_cutoff(signal_ts: datetime) -> datetime:
    """
    15:30 IST = 10:00 UTC.
    """
    signal_day_utc = signal_ts.astimezone(UTC).date()
    return datetime(
        year=signal_day_utc.year,
        month=signal_day_utc.month,
        day=signal_day_utc.day,
        hour=10,
        minute=0,
        second=0,
        tzinfo=UTC,
    )


def _direct_select(
    sb: Any,
    table_name: str,
    params: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Bypass SupabaseClient.select() because that helper currently treats
    ts__gte / ts__lte like literal column names.
    """
    data = sb._request(
        method="GET",
        path=table_name,
        params=params,
    )
    return data if isinstance(data, list) else []


def fetch_spot_window(
    sb: Any,
    symbol: str,
    start_ts: datetime,
    end_ts: datetime,
) -> List[SpotPoint]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    page_size = 1000

    start_iso = start_ts.astimezone(UTC).isoformat()
    end_iso = end_ts.astimezone(UTC).isoformat()

    while True:
        params = {
            "select": "ts,spot",
            "symbol": f"eq.{symbol}",
            "and": f"(ts.gte.{start_iso},ts.lte.{end_iso})",
            "order": "ts.asc",
            "limit": str(page_size),
            "offset": str(offset),
        }

        batch = _direct_select(sb, "market_spot_snapshots", params)
        if not batch:
            break

        rows.extend(batch)

        if len(batch) < page_size:
            break

        offset += page_size

    points: List[SpotPoint] = []
    for row in rows:
        ts = parse_ts(row["ts"])
        spot = safe_float(row.get("spot"))
        if spot is not None:
            points.append(SpotPoint(ts=ts, spot=spot))

    points.sort(key=lambda x: x.ts)
    return points


def page_source_rows(
    sb: Any,
    table_name: str,
    since_ts: Optional[str] = None,
    limit_total: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch source rows ordered by ts.
    We intentionally avoid ts__gte filters here and filter in Python,
    because source row counts are currently small and this is safer.
    """
    offset = 0
    page_size = 500
    out: List[Dict[str, Any]] = []

    while True:
        batch = sb.select(
            table_name,
            limit=page_size,
            offset=offset,
            order="ts",
            ascending=True,
        )
        if not batch:
            break

        out.extend(batch)

        if len(batch) < page_size:
            break

        offset += page_size

    if since_ts:
        since_dt = parse_ts(since_ts)
        out = [row for row in out if parse_ts(row["ts"]) >= since_dt]

    if limit_total is not None:
        out = out[:limit_total]

    return out


def nearest_point_at_or_after(
    points: List[SpotPoint],
    target_ts: datetime,
    tolerance_minutes: int = 20,
) -> Optional[SpotPoint]:
    for p in points:
        if p.ts >= target_ts and (p.ts - target_ts) <= timedelta(minutes=tolerance_minutes):
            return p
    return None


def last_point_before_or_at(points: List[SpotPoint], target_ts: datetime) -> Optional[SpotPoint]:
    chosen: Optional[SpotPoint] = None
    for p in points:
        if p.ts <= target_ts:
            chosen = p
        else:
            break
    return chosen


def points_within_window(points: List[SpotPoint], start_ts: datetime, end_ts: datetime) -> List[SpotPoint]:
    return [p for p in points if start_ts <= p.ts <= end_ts]


def compute_mfe_mae_60m(
    action: Optional[str],
    entry_spot: float,
    points: List[SpotPoint],
    signal_ts: datetime,
) -> Dict[str, Optional[float]]:
    end_60m = signal_ts + timedelta(minutes=60)
    window_points = points_within_window(points, signal_ts, end_60m)

    if not window_points:
        return {"mfe_points_60m": None, "mae_points_60m": None}

    if action == "BUY_CE":
        favorable = max((p.spot - entry_spot) for p in window_points)
        adverse = max((entry_spot - p.spot) for p in window_points)
        return {
            "mfe_points_60m": favorable,
            "mae_points_60m": adverse,
        }

    if action == "BUY_PE":
        favorable = max((entry_spot - p.spot) for p in window_points)
        adverse = max((p.spot - entry_spot) for p in window_points)
        return {
            "mfe_points_60m": favorable,
            "mae_points_60m": adverse,
        }

    return {"mfe_points_60m": None, "mae_points_60m": None}


def pct_move(move_points: Optional[float], entry_spot: Optional[float]) -> Optional[float]:
    if move_points is None or entry_spot in (None, 0):
        return None
    try:
        return (move_points / float(entry_spot)) * 100.0
    except Exception:
        return None


def compute_horizon_moves(
    signal_ts: datetime,
    entry_spot: float,
    points: List[SpotPoint],
) -> Dict[str, Optional[float]]:
    target_15m = signal_ts + timedelta(minutes=15)
    target_30m = signal_ts + timedelta(minutes=30)
    target_60m = signal_ts + timedelta(minutes=60)
    target_eod = session_eod_cutoff(signal_ts)

    p15 = nearest_point_at_or_after(points, target_15m)
    p30 = nearest_point_at_or_after(points, target_30m)
    p60 = nearest_point_at_or_after(points, target_60m)
    peod = last_point_before_or_at(points, target_eod)

    move_15m = (p15.spot - entry_spot) if p15 else None
    move_30m = (p30.spot - entry_spot) if p30 else None
    move_60m = (p60.spot - entry_spot) if p60 else None
    move_eod = (peod.spot - entry_spot) if peod else None

    return {
        "outcome_15m_spot": p15.spot if p15 else None,
        "outcome_30m_spot": p30.spot if p30 else None,
        "outcome_60m_spot": p60.spot if p60 else None,
        "outcome_eod_spot": peod.spot if peod else None,
        "move_15m_points": move_15m,
        "move_30m_points": move_30m,
        "move_60m_points": move_60m,
        "move_eod_points": move_eod,
        "move_15m_pct": pct_move(move_15m, entry_spot),
        "move_30m_pct": pct_move(move_30m, entry_spot),
        "move_60m_pct": pct_move(move_60m, entry_spot),
        "move_eod_pct": pct_move(move_eod, entry_spot),
        "horizon_15m_ts": p15.ts.isoformat() if p15 else None,
        "horizon_30m_ts": p30.ts.isoformat() if p30 else None,
        "horizon_60m_ts": p60.ts.isoformat() if p60 else None,
        "horizon_eod_ts": peod.ts.isoformat() if peod else None,
    }


def evaluate_baseline_signal_row(sb: Any, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    signal_id = row.get("id")
    symbol = row.get("symbol")
    signal_ts_raw = row.get("ts")
    action = row.get("action")

    if signal_id is None or not symbol or not signal_ts_raw:
        return None

    signal_ts = parse_ts(signal_ts_raw)
    window_end = max(signal_ts + timedelta(minutes=70), session_eod_cutoff(signal_ts))
    points = fetch_spot_window(sb, symbol=symbol, start_ts=signal_ts, end_ts=window_end)

    if not points:
        return None

    entry_point = nearest_point_at_or_after(points, signal_ts, tolerance_minutes=20)
    if entry_point is None:
        entry_point = points[0]

    entry_spot = entry_point.spot
    moves = compute_horizon_moves(signal_ts=signal_ts, entry_spot=entry_spot, points=points)
    mfe_mae = compute_mfe_mae_60m(action=action, entry_spot=entry_spot, points=points, signal_ts=signal_ts)

    output = {
        "signal_id": signal_id,
        "signal_ts": signal_ts.isoformat(),
        "symbol": symbol,
        "action": action,
        "trade_allowed": safe_bool(row.get("trade_allowed")),
        "direction_bias": row.get("direction_bias"),
        "entry_quality": row.get("entry_quality"),
        "confidence_score": safe_float(row.get("confidence_score")),
        "entry_spot": entry_spot,
        "entry_reference_price": entry_spot,
        "outcome_15m_spot": moves["outcome_15m_spot"],
        "outcome_30m_spot": moves["outcome_30m_spot"],
        "outcome_60m_spot": moves["outcome_60m_spot"],
        "outcome_eod_spot": moves["outcome_eod_spot"],
        "move_15m_points": moves["move_15m_points"],
        "move_30m_points": moves["move_30m_points"],
        "move_60m_points": moves["move_60m_points"],
        "move_eod_points": moves["move_eod_points"],
        "move_15m_pct": moves["move_15m_pct"],
        "move_30m_pct": moves["move_30m_pct"],
        "move_60m_pct": moves["move_60m_pct"],
        "move_eod_pct": moves["move_eod_pct"],
        "outcome_label_15m": outcome_label(action, moves["move_15m_points"]),
        "outcome_label_30m": outcome_label(action, moves["move_30m_points"]),
        "outcome_label_60m": outcome_label(action, moves["move_60m_points"]),
        "outcome_label_eod": outcome_label(action, moves["move_eod_points"]),
        "mfe_points_60m": mfe_mae["mfe_points_60m"],
        "mae_points_60m": mfe_mae["mae_points_60m"],
        "outcome_policy_version": "spot_timeline_v1",
        "raw": {
            "evaluation_source": "market_spot_snapshots",
            "entry_spot_ts": entry_point.ts.isoformat(),
            "horizon_15m_ts": moves["horizon_15m_ts"],
            "horizon_30m_ts": moves["horizon_30m_ts"],
            "horizon_60m_ts": moves["horizon_60m_ts"],
            "horizon_eod_ts": moves["horizon_eod_ts"],
        },
    }

    return output


def evaluate_shadow_signal_row(sb: Any, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    shadow_signal_id = row.get("id")
    symbol = row.get("symbol")
    signal_ts_raw = row.get("ts")
    shadow_action = row.get("shadow_action")
    baseline_action = row.get("baseline_action")

    if shadow_signal_id is None or not symbol or not signal_ts_raw:
        return None

    signal_ts = parse_ts(signal_ts_raw)
    window_end = max(signal_ts + timedelta(minutes=70), session_eod_cutoff(signal_ts))
    points = fetch_spot_window(sb, symbol=symbol, start_ts=signal_ts, end_ts=window_end)

    if not points:
        return None

    entry_point = nearest_point_at_or_after(points, signal_ts, tolerance_minutes=20)
    if entry_point is None:
        entry_point = points[0]

    entry_spot = entry_point.spot
    moves = compute_horizon_moves(signal_ts=signal_ts, entry_spot=entry_spot, points=points)
    mfe_mae = compute_mfe_mae_60m(action=shadow_action, entry_spot=entry_spot, points=points, signal_ts=signal_ts)

    output = {
        "shadow_signal_id": shadow_signal_id,
        "shadow_policy_version": row.get("shadow_policy_version"),
        "signal_ts": signal_ts.isoformat(),
        "symbol": symbol,
        "baseline_action": baseline_action,
        "baseline_trade_allowed": safe_bool(row.get("baseline_trade_allowed")),
        "baseline_direction_bias": row.get("baseline_direction_bias"),
        "baseline_entry_quality": row.get("baseline_entry_quality"),
        "baseline_confidence_score": safe_float(row.get("baseline_confidence_score")),
        "shadow_action": shadow_action,
        "shadow_trade_allowed": safe_bool(row.get("shadow_trade_allowed")),
        "shadow_direction_bias": row.get("shadow_direction_bias"),
        "shadow_entry_quality": row.get("shadow_entry_quality"),
        "shadow_confidence_score": safe_float(row.get("shadow_confidence_score")),
        "shadow_delta_confidence": safe_float(row.get("shadow_delta_confidence")),
        "shadow_decision_changed": safe_bool(row.get("shadow_decision_changed")),
        "breadth_wcb_relationship": row.get("breadth_wcb_relationship"),
        "wcb_regime": row.get("wcb_regime"),
        "wcb_score": safe_float(row.get("wcb_score")),
        "wcb_alignment": row.get("wcb_alignment"),
        "wcb_weight_coverage_pct": safe_float(row.get("wcb_weight_coverage_pct")),
        "entry_spot": entry_spot,
        "entry_reference_price": entry_spot,
        "outcome_15m_spot": moves["outcome_15m_spot"],
        "outcome_30m_spot": moves["outcome_30m_spot"],
        "outcome_60m_spot": moves["outcome_60m_spot"],
        "outcome_eod_spot": moves["outcome_eod_spot"],
        "move_15m_points": moves["move_15m_points"],
        "move_30m_points": moves["move_30m_points"],
        "move_60m_points": moves["move_60m_points"],
        "move_eod_points": moves["move_eod_points"],
        "move_15m_pct": moves["move_15m_pct"],
        "move_30m_pct": moves["move_30m_pct"],
        "move_60m_pct": moves["move_60m_pct"],
        "move_eod_pct": moves["move_eod_pct"],
        "outcome_label_15m": outcome_label(shadow_action, moves["move_15m_points"]),
        "outcome_label_30m": outcome_label(shadow_action, moves["move_30m_points"]),
        "outcome_label_60m": outcome_label(shadow_action, moves["move_60m_points"]),
        "outcome_label_eod": outcome_label(shadow_action, moves["move_eod_points"]),
        "mfe_points_60m": mfe_mae["mfe_points_60m"],
        "mae_points_60m": mfe_mae["mae_points_60m"],
        "raw": {
            "evaluation_source": "market_spot_snapshots",
            "entry_spot_ts": entry_point.ts.isoformat(),
            "horizon_15m_ts": moves["horizon_15m_ts"],
            "horizon_30m_ts": moves["horizon_30m_ts"],
            "horizon_60m_ts": moves["horizon_60m_ts"],
            "horizon_eod_ts": moves["horizon_eod_ts"],
        },
    }

    return output