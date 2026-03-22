import sys
import json
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
        return int(value)
    except Exception:
        return None


def _dedupe_strings(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _latest_market_state(sb: SupabaseClient, symbol: str) -> Dict[str, Any]:
    rows = sb.select(
        table="market_state_snapshots",
        filters={"symbol": f"eq.{symbol}"},
        order="created_at.desc",
        limit=1,
    )
    if not rows:
        raise RuntimeError(f"No market_state_snapshots rows found for symbol={symbol}")
    return rows[0]


def _classify_volatility_regime(
    atm_iv_avg: Optional[float],
    india_vix: Optional[float],
) -> str:
    if atm_iv_avg is None:
        return "UNKNOWN"

    if india_vix is None or india_vix <= 0:
        if atm_iv_avg >= 35:
            return "HIGH_IV"
        if atm_iv_avg >= 22:
            return "NORMAL_IV"
        return "LOW_IV"

    ratio = atm_iv_avg / india_vix

    if india_vix >= 25 or ratio >= 1.60:
        return "VERY_HIGH_IV"
    if india_vix >= 18 or ratio >= 1.35:
        return "HIGH_IV"
    if ratio <= 0.90 and india_vix < 15:
        return "LOW_IV"
    return "NORMAL_IV"


def _momentum_direction(
    ret_5m: Optional[float],
    ret_15m: Optional[float],
    ret_30m: Optional[float],
    price_vs_vwap_pct: Optional[float],
    atm_straddle_change: Optional[float],
    vwap_slope: Optional[float],
) -> str:
    bullish_points = 0
    bearish_points = 0

    for value in [ret_5m, ret_15m, ret_30m]:
        if value is None:
            continue
        if value > 0:
            bullish_points += 1
        elif value < 0:
            bearish_points += 1

    if price_vs_vwap_pct is not None:
        if price_vs_vwap_pct > 0:
            bullish_points += 1
        elif price_vs_vwap_pct < 0:
            bearish_points += 1

    if atm_straddle_change is not None:
        if atm_straddle_change > 0:
            bullish_points += 1
        elif atm_straddle_change < 0:
            bearish_points += 1

    if vwap_slope is not None:
        if vwap_slope > 0:
            bullish_points += 1
        elif vwap_slope < 0:
            bearish_points += 1

    if bullish_points >= bearish_points + 2 and bullish_points >= 3:
        return "BULLISH"
    if bearish_points >= bullish_points + 2 and bearish_points >= 3:
        return "BEARISH"
    return "NEUTRAL"


def _classify_alignment_regime(
    breadth_regime: Optional[str],
    momentum_direction: str,
) -> str:
    if breadth_regime not in ("BULLISH", "BEARISH"):
        return "UNCLEAR"

    if momentum_direction == "NEUTRAL":
        return "UNCLEAR"

    if breadth_regime == momentum_direction:
        return "ALIGNED"

    return "CONFLICT"


def _resolve_direction_bias(
    gamma_regime: Optional[str],
    breadth_regime: Optional[str],
    momentum_direction: str,
    gamma_concentration: Optional[float],
    flip_distance: Optional[float],
    spot: Optional[float],
) -> str:
    if breadth_regime not in ("BULLISH", "BEARISH"):
        return "NEUTRAL"

    if momentum_direction == "NEUTRAL":
        return "NEUTRAL"

    if breadth_regime != momentum_direction:
        return "NEUTRAL"

    distance_pct = None
    if flip_distance is not None and spot not in (None, 0):
        distance_pct = abs(flip_distance) / abs(spot) * 100.0

    if gamma_regime == "SHORT_GAMMA":
        return breadth_regime

    if gamma_regime == "LONG_GAMMA":
        if gamma_concentration is not None and gamma_concentration >= 0.22:
            return "NEUTRAL"
        if distance_pct is not None and distance_pct <= 0.50:
            return "NEUTRAL"
        return breadth_regime

    return breadth_regime


def _is_breadth_aligned(direction_bias: str, breadth_regime: Optional[str]) -> bool:
    if direction_bias == "BEARISH" and breadth_regime == "BEARISH":
        return True
    if direction_bias == "BULLISH" and breadth_regime == "BULLISH":
        return True
    return False


def _base_confidence(
    direction_bias: str,
    gamma_regime: Optional[str],
    breadth_regime: Optional[str],
    breadth_score: Optional[float],
    gamma_concentration: Optional[float],
    momentum_direction: str,
    alignment_regime: str,
) -> float:
    score = 50.0

    if gamma_regime == "SHORT_GAMMA":
        score += 8.0
    elif gamma_regime == "LONG_GAMMA":
        score -= 4.0

    if breadth_regime in ("BULLISH", "BEARISH"):
        score += 6.0
    elif breadth_regime == "TRANSITION":
        score -= 5.0

    if momentum_direction in ("BULLISH", "BEARISH"):
        score += 5.0
    else:
        score -= 4.0

    if alignment_regime == "ALIGNED":
        score += 4.0
    elif alignment_regime == "CONFLICT":
        score -= 8.0
    elif alignment_regime == "UNCLEAR":
        score -= 3.0

    if breadth_score is not None:
        if direction_bias == "BEARISH":
            if breadth_score <= 15:
                score += 6.0
            elif breadth_score <= 25:
                score += 4.0
            elif breadth_score >= 55:
                score -= 6.0
        elif direction_bias == "BULLISH":
            if breadth_score >= 85:
                score += 6.0
            elif breadth_score >= 75:
                score += 4.0
            elif breadth_score <= 45:
                score -= 6.0

    if gamma_concentration is not None:
        if gamma_concentration >= 0.20:
            score += 3.0
        elif gamma_concentration < 0.05:
            score -= 5.0

    return score


def _apply_vix_penalties(
    score: float,
    cautions: List[str],
    atm_iv_avg: Optional[float],
    india_vix: Optional[float],
    vix_regime: Optional[str],
    volatility_regime: str,
) -> float:
    if india_vix is not None:
        cautions.append(f"India VIX is {india_vix:.2f}")
    if vix_regime:
        cautions.append(f"India VIX regime is {vix_regime}")

    if india_vix is not None and india_vix >= 18:
        score -= 4.0
        cautions.append("India VIX is elevated")

    if india_vix is not None and india_vix >= 25:
        score -= 6.0
        cautions.append("India VIX indicates stress conditions")

    if atm_iv_avg is not None and india_vix is not None and india_vix > 0:
        ratio = atm_iv_avg / india_vix
        if ratio >= 1.60:
            score -= 8.0
            cautions.append("ATM IV is far above India VIX")
        elif ratio >= 1.35:
            score -= 5.0
            cautions.append("ATM IV is significantly above India VIX")

    if volatility_regime == "VERY_HIGH_IV":
        score -= 7.0
        cautions.append("Volatility regime is VERY_HIGH_IV")
    elif volatility_regime == "HIGH_IV":
        score -= 4.0
        cautions.append("Volatility regime is HIGH_IV")

    return score


def _apply_expiry_penalties(
    score: float,
    cautions: List[str],
    dte: Optional[int],
    expiry_type: Optional[str],
) -> float:
    if dte is None:
        return score

    if dte <= 1:
        score -= 12.0
        cautions.append("One-day-to-expiry raises gamma/theta risk")
    elif dte <= 2:
        score -= 7.0
        cautions.append("Very low DTE increases options-buy risk")

    if expiry_type == "WEEKLY":
        score -= 2.0
        cautions.append("Weekly expiry can be more volatile")

    return score


def _apply_structure_penalties(
    score: float,
    cautions: List[str],
    gamma_concentration: Optional[float],
    straddle_slope: Optional[float],
) -> float:
    if gamma_concentration is not None and gamma_concentration < 0.05:
        score -= 4.0
        cautions.append("Gamma concentration is weak")

    if straddle_slope is not None and abs(straddle_slope) < 10:
        score -= 2.0
        cautions.append("ATM straddle slope is relatively flat")

    return score


def _apply_gamma_context(
    score: float,
    reasons: List[str],
    cautions: List[str],
    *,
    gamma_regime: Optional[str],
    gamma_concentration: Optional[float],
    flip_distance: Optional[float],
    spot: Optional[float],
    straddle_slope: Optional[float],
) -> float:
    if gamma_regime is None:
        return score

    distance_pct = None
    if flip_distance is not None and spot not in (None, 0):
        distance_pct = abs(flip_distance) / abs(spot) * 100.0

    if gamma_regime == "SHORT_GAMMA":
        if distance_pct is not None and distance_pct <= 0.50:
            score += 5.0
            reasons.append("Spot is close to gamma flip under SHORT_GAMMA")
        elif distance_pct is not None and distance_pct >= 1.50:
            score -= 3.0
            cautions.append("Spot is relatively far from gamma flip")

        if gamma_concentration is not None and gamma_concentration >= 0.20:
            score += 3.0
            reasons.append("Gamma concentration is supportive")
        elif gamma_concentration is not None and gamma_concentration < 0.08:
            score -= 3.0
            cautions.append("Gamma concentration is not supportive")

        if straddle_slope is not None and straddle_slope > 10:
            score += 3.0
            reasons.append("ATM straddle is expanding")
        elif straddle_slope is not None and straddle_slope < -10:
            score -= 3.0
            cautions.append("ATM straddle is compressing")

    elif gamma_regime == "LONG_GAMMA":
        if distance_pct is not None and distance_pct <= 0.50:
            score -= 5.0
            cautions.append("Spot is close to gamma flip in LONG_GAMMA")
        elif distance_pct is not None and distance_pct >= 1.50:
            score += 1.0

        if gamma_concentration is not None and gamma_concentration >= 0.20:
            score -= 2.0
            cautions.append("High gamma concentration may reinforce pinning")
        elif gamma_concentration is not None and gamma_concentration < 0.08:
            score += 1.0

        if straddle_slope is not None and straddle_slope > 10:
            score += 1.0
        elif straddle_slope is not None and straddle_slope < -10:
            score -= 1.0

    return score


def _apply_momentum_context(
    score: float,
    reasons: List[str],
    cautions: List[str],
    *,
    ret_5m: Optional[float],
    ret_15m: Optional[float],
    ret_30m: Optional[float],
    price_vs_vwap_pct: Optional[float],
    atm_straddle_change: Optional[float],
    vwap_slope: Optional[float],
) -> float:
    confirmations = 0
    negatives = 0

    for label, value in [
        ("ret_5m", ret_5m),
        ("ret_15m", ret_15m),
        ("ret_30m", ret_30m),
    ]:
        if value is None:
            continue
        if value > 0:
            confirmations += 1
        elif value < 0:
            negatives += 1
            cautions.append(f"{label} shows premium compression")

    if price_vs_vwap_pct is not None:
        if price_vs_vwap_pct > 0:
            confirmations += 1
            reasons.append("ATM straddle is above session VWAP")
        elif price_vs_vwap_pct < 0:
            negatives += 1
            cautions.append("ATM straddle is below session VWAP")

    if atm_straddle_change is not None:
        if atm_straddle_change > 0:
            confirmations += 1
            reasons.append("ATM straddle increased vs previous bucket")
        elif atm_straddle_change < 0:
            negatives += 1
            cautions.append("ATM straddle decreased vs previous bucket")

    if vwap_slope is not None:
        if vwap_slope > 0:
            confirmations += 1
            reasons.append("Session VWAP slope is rising")
        elif vwap_slope < 0:
            negatives += 1
            cautions.append("Session VWAP slope is falling")

    if confirmations >= 4:
        score += 6.0
        reasons.append("Momentum confirms premium expansion")
    elif confirmations >= 2:
        score += 3.0
        reasons.append("Momentum is moderately supportive")

    if negatives >= 3:
        score -= 6.0
        cautions.append("Momentum shows broad premium compression")
    elif negatives >= 2:
        score -= 3.0

    return score


def _apply_alignment_context(
    score: float,
    reasons: List[str],
    cautions: List[str],
    *,
    alignment_regime: str,
    breadth_regime: Optional[str],
    momentum_direction: str,
) -> float:
    if alignment_regime == "ALIGNED":
        reasons.append("Breadth and momentum are aligned")
        score += 2.0
    elif alignment_regime == "CONFLICT":
        cautions.append(
            f"Breadth {breadth_regime} conflicts with momentum {momentum_direction}"
        )
        cautions.append("Premium expansion does not equal directional edge")
        score -= 6.0
    else:
        cautions.append("Breadth and momentum alignment is unclear")
        score -= 2.0

    return score


def _clamp_score(score: float) -> float:
    return max(0.0, min(100.0, round(score, 1)))


def _build_signal(symbol: str) -> Dict[str, Any]:
    sb = SupabaseClient()
    mss = _latest_market_state(sb, symbol)

    gamma_features = mss.get("gamma_features") or {}
    breadth_features = mss.get("breadth_features") or {}
    volatility_features = mss.get("volatility_features") or {}
    momentum_features = mss.get("momentum_features") or {}

    gamma_regime = gamma_features.get("regime")
    breadth_regime = breadth_features.get("breadth_regime")
    breadth_score = _to_float(breadth_features.get("breadth_score"))

    atm_strike = _to_int(volatility_features.get("atm_strike"))
    atm_call_iv = _to_float(volatility_features.get("atm_call_iv"))
    atm_put_iv = _to_float(volatility_features.get("atm_put_iv"))
    atm_iv_avg = _to_float(volatility_features.get("atm_iv_avg"))
    iv_skew = _to_float(volatility_features.get("iv_skew"))
    india_vix = _to_float(volatility_features.get("india_vix"))
    vix_change = _to_float(volatility_features.get("vix_change"))
    vix_regime = volatility_features.get("vix_regime")

    net_gex = _to_float(gamma_features.get("net_gex"))
    gamma_concentration = _to_float(gamma_features.get("gamma_concentration"))
    flip_level = _to_float(gamma_features.get("flip_level"))
    flip_distance = _to_float(gamma_features.get("flip_distance"))
    straddle_atm = _to_float(gamma_features.get("straddle_atm"))
    straddle_slope = _to_float(gamma_features.get("straddle_slope"))
    source_run_id = gamma_features.get("run_id") or volatility_features.get("source_run_id")

    ret_5m = _to_float(momentum_features.get("ret_5m"))
    ret_15m = _to_float(momentum_features.get("ret_15m"))
    ret_30m = _to_float(momentum_features.get("ret_30m"))
    price_vs_vwap_pct = _to_float(momentum_features.get("price_vs_vwap_pct"))
    vwap_slope = _to_float(momentum_features.get("vwap_slope"))
    atm_straddle_change = _to_float(momentum_features.get("atm_straddle_change"))

    expiry_date = mss.get("expiry_date")
    expiry_type = mss.get("expiry_type")
    dte = _to_int(mss.get("dte"))
    spot = _to_float(mss.get("spot"))

    market_state_ts = mss.get("ts")

    momentum_direction = _momentum_direction(
        ret_5m=ret_5m,
        ret_15m=ret_15m,
        ret_30m=ret_30m,
        price_vs_vwap_pct=price_vs_vwap_pct,
        atm_straddle_change=atm_straddle_change,
        vwap_slope=vwap_slope,
    )

    alignment_regime = _classify_alignment_regime(
        breadth_regime=breadth_regime,
        momentum_direction=momentum_direction,
    )

    direction_bias = _resolve_direction_bias(
        gamma_regime=gamma_regime,
        breadth_regime=breadth_regime,
        momentum_direction=momentum_direction,
        gamma_concentration=gamma_concentration,
        flip_distance=flip_distance,
        spot=spot,
    )

    breadth_aligned = _is_breadth_aligned(direction_bias, breadth_regime)
    volatility_regime = _classify_volatility_regime(atm_iv_avg, india_vix)

    reasons: List[str] = []
    cautions: List[str] = []

    if gamma_regime:
        reasons.append(f"Gamma regime is {gamma_regime}")
    if breadth_regime:
        reasons.append(f"Breadth regime is {breadth_regime}")
    if momentum_direction:
        reasons.append(f"Momentum direction is {momentum_direction}")
    reasons.append(f"Alignment regime is {alignment_regime}")
    if direction_bias != "NEUTRAL":
        reasons.append(f"Direction bias is {direction_bias}")

    score = _base_confidence(
        direction_bias=direction_bias,
        gamma_regime=gamma_regime,
        breadth_regime=breadth_regime,
        breadth_score=breadth_score,
        gamma_concentration=gamma_concentration,
        momentum_direction=momentum_direction,
        alignment_regime=alignment_regime,
    )

    score = _apply_gamma_context(
        score=score,
        reasons=reasons,
        cautions=cautions,
        gamma_regime=gamma_regime,
        gamma_concentration=gamma_concentration,
        flip_distance=flip_distance,
        spot=spot,
        straddle_slope=straddle_slope,
    )

    score = _apply_structure_penalties(
        score=score,
        cautions=cautions,
        gamma_concentration=gamma_concentration,
        straddle_slope=straddle_slope,
    )

    score = _apply_expiry_penalties(
        score=score,
        cautions=cautions,
        dte=dte,
        expiry_type=expiry_type,
    )

    score = _apply_vix_penalties(
        score=score,
        cautions=cautions,
        atm_iv_avg=atm_iv_avg,
        india_vix=india_vix,
        vix_regime=vix_regime,
        volatility_regime=volatility_regime,
    )

    score = _apply_momentum_context(
        score=score,
        reasons=reasons,
        cautions=cautions,
        ret_5m=ret_5m,
        ret_15m=ret_15m,
        ret_30m=ret_30m,
        price_vs_vwap_pct=price_vs_vwap_pct,
        atm_straddle_change=atm_straddle_change,
        vwap_slope=vwap_slope,
    )

    score = _apply_alignment_context(
        score=score,
        reasons=reasons,
        cautions=cautions,
        alignment_regime=alignment_regime,
        breadth_regime=breadth_regime,
        momentum_direction=momentum_direction,
    )

    trade_allowed = True

    if direction_bias == "NEUTRAL":
        trade_allowed = False
        cautions.append("No directional bias available")

    if alignment_regime == "CONFLICT":
        trade_allowed = False
        cautions.append("Direction is blocked by breadth-vs-momentum conflict")

    if not breadth_aligned:
        trade_allowed = False
        cautions.append("Gamma, breadth, and momentum are not aligned")

    if gamma_regime == "LONG_GAMMA":
        if gamma_concentration is not None and gamma_concentration >= 0.22:
            trade_allowed = False
            cautions.append("LONG_GAMMA with high concentration may reinforce pinning")
        if flip_distance is not None and spot not in (None, 0):
            distance_pct = abs(flip_distance) / abs(spot) * 100.0
            if distance_pct <= 0.50:
                trade_allowed = False
                cautions.append("LONG_GAMMA close to flip is not ideal for premium buying")

    if dte is not None and dte < 2:
        trade_allowed = False
        cautions.append("DTE gate blocks trade")

    if volatility_regime in ("HIGH_IV", "VERY_HIGH_IV"):
        trade_allowed = False
        cautions.append("IV is elevated for outright premium buying")

    if atm_iv_avg is not None and atm_iv_avg >= 35:
        cautions.append("ATM IV average is very high")

    if india_vix is not None and india_vix >= 18:
        cautions.append("High India VIX reduces options-buy attractiveness")

    confidence_score = _clamp_score(score)

    if trade_allowed and direction_bias == "BEARISH":
        action = "BUY_PE"
    elif trade_allowed and direction_bias == "BULLISH":
        action = "BUY_CE"
    else:
        action = "DO_NOTHING"

    if not trade_allowed:
        entry_quality = "NO_TRADE"
    elif confidence_score >= 75:
        entry_quality = "HIGH"
    elif confidence_score >= 60:
        entry_quality = "MEDIUM"
    else:
        entry_quality = "LOW"

    reasons = _dedupe_strings(reasons)
    cautions = _dedupe_strings(cautions)

    signal_row: Dict[str, Any] = {
        "ts": market_state_ts,
        "market_state_ts": market_state_ts,
        "symbol": symbol,
        "expiry_date": expiry_date,
        "expiry_type": expiry_type,
        "dte": dte,
        "spot": spot,
        "action": action,
        "trade_allowed": trade_allowed,
        "entry_quality": entry_quality,
        "direction_bias": direction_bias,
        "confidence_score": confidence_score,
        "gamma_regime": gamma_regime,
        "breadth_regime": breadth_regime,
        "breadth_score": breadth_score,
        "volatility_regime": volatility_regime,
        "atm_strike": atm_strike,
        "atm_call_iv": atm_call_iv,
        "atm_put_iv": atm_put_iv,
        "atm_iv_avg": atm_iv_avg,
        "iv_skew": iv_skew,
        "india_vix": india_vix,
        "vix_change": vix_change,
        "vix_regime": vix_regime,
        "net_gex": net_gex,
        "gamma_concentration": gamma_concentration,
        "flip_level": flip_level,
        "flip_distance": flip_distance,
        "straddle_atm": straddle_atm,
        "straddle_slope": straddle_slope,
        "source_run_id": source_run_id,
        "breadth_source_table": breadth_features.get("source_table"),
        "reasons": reasons,
        "cautions": cautions,
        "signal_source": "market_state_snapshots",
    }

    print("=" * 72)
    print("Gamma Engine - Signal Engine V4")
    print("=" * 72)
    print(f"Base dir: {BASE_DIR}")
    print(f"Symbol: {symbol}")
    print("-" * 72)
    print("Latest market state row:")
    print(json.dumps(mss, indent=2, default=str))
    print("-" * 72)
    print("Computed signal:")
    print(json.dumps(signal_row, indent=2, default=str))
    print("-" * 72)
    print(f"Derived momentum_direction (not persisted yet): {momentum_direction}")
    print(f"Derived alignment_regime (not persisted yet): {alignment_regime}")

    out_file = DATA_DIR / f"latest_trade_signal_{symbol}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                **signal_row,
                "momentum_direction_debug": momentum_direction,
                "alignment_regime_debug": alignment_regime,
            },
            f,
            indent=2,
            default=str,
        )

    print("-" * 72)
    print(f"Signal saved to: {out_file}")
    print("SIGNAL ENGINE V4 COMPLETED")

    return signal_row


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: python .\\build_trade_signal_local.py NIFTY")

    symbol = sys.argv[1].strip().upper()
    signal_row = _build_signal(symbol)

    sb = SupabaseClient()
    inserted = sb.insert("signal_snapshots", [signal_row])
    _ = inserted


if __name__ == "__main__":
    main()