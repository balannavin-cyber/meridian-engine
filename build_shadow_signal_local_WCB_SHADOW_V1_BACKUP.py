import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.supabase_client import SupabaseClient


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SHADOW_POLICY_VERSION = "WCB_SHADOW_V1"


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


def _normalize_regime(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    mapping = {
        "BULL": "BULLISH",
        "STRONG_BULL": "STRONG_BULLISH",
        "BEAR": "BEARISH",
        "STRONG_BEAR": "STRONG_BEARISH",
        "TRANSITION": "NEUTRAL",
    }
    return mapping.get(text, text)


def _classify_breadth_wcb_relationship(
    breadth_regime: Optional[str],
    wcb_regime: Optional[str],
) -> str:
    breadth = _normalize_regime(breadth_regime)
    wcb = _normalize_regime(wcb_regime)

    if breadth is None or wcb is None:
        return "UNKNOWN"

    if breadth == "BULLISH" and wcb in ("BULLISH", "STRONG_BULLISH"):
        return "CONFIRM_BULLISH"
    if breadth == "BEARISH" and wcb in ("BEARISH", "STRONG_BEARISH"):
        return "CONFIRM_BEARISH"
    if breadth == "BULLISH" and wcb in ("BEARISH", "STRONG_BEARISH"):
        return "DIVERGENT_BREADTH_BULL_WCB_BEAR"
    if breadth == "BEARISH" and wcb in ("BULLISH", "STRONG_BULLISH"):
        return "DIVERGENT_BREADTH_BEAR_WCB_BULL"
    if wcb == "NEUTRAL":
        return "WCB_NEUTRAL"
    return "MIXED"


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


def _latest_baseline_signal(sb: SupabaseClient, symbol: str) -> Dict[str, Any]:
    rows = sb.select(
        table="signal_snapshots",
        filters={"symbol": f"eq.{symbol}"},
        order="created_at.desc",
        limit=1,
    )
    if not rows:
        raise RuntimeError(f"No signal_snapshots rows found for symbol={symbol}")
    return rows[0]


def _derive_shadow_from_baseline(
    baseline_signal: Dict[str, Any],
    market_state: Dict[str, Any],
) -> Dict[str, Any]:
    baseline_action = baseline_signal.get("action")
    baseline_trade_allowed = baseline_signal.get("trade_allowed")
    baseline_entry_quality = baseline_signal.get("entry_quality")
    baseline_direction_bias = baseline_signal.get("direction_bias")
    baseline_confidence_score = _to_float(baseline_signal.get("confidence_score")) or 0.0

    breadth_regime = _normalize_regime(baseline_signal.get("breadth_regime"))
    breadth_score = _to_float(baseline_signal.get("breadth_score"))
    gamma_regime = _normalize_regime(baseline_signal.get("gamma_regime"))
    volatility_regime = _normalize_regime(baseline_signal.get("volatility_regime"))

    wcb_features = market_state.get("wcb_features") or {}
    wcb_regime = _normalize_regime(wcb_features.get("wcb_regime"))
    wcb_score = _to_float(wcb_features.get("wcb_score"))
    wcb_weight_coverage_pct = _to_float(wcb_features.get("matched_weight_pct"))
    wcb_alignment = _normalize_regime(baseline_signal.get("wcb_alignment"))
    if wcb_alignment is None:
        wcb_alignment = "UNAVAILABLE"

    breadth_wcb_relationship = _classify_breadth_wcb_relationship(
        breadth_regime=breadth_regime,
        wcb_regime=wcb_regime,
    )

    reasons: List[str] = []
    cautions: List[str] = []

    reasons.append(f"Shadow policy version is {SHADOW_POLICY_VERSION}")
    reasons.append(f"Baseline action is {baseline_action}")
    reasons.append(f"Baseline direction bias is {baseline_direction_bias}")

    shadow_confidence = baseline_confidence_score
    shadow_direction_bias = baseline_direction_bias
    shadow_trade_allowed = bool(baseline_trade_allowed)
    shadow_action = baseline_action
    shadow_entry_quality = baseline_entry_quality

    if wcb_regime is not None:
        reasons.append(f"WCB regime observed as {wcb_regime}")
    else:
        cautions.append("WCB regime unavailable in market state")

    if wcb_weight_coverage_pct is not None:
        reasons.append(f"WCB coverage is {round(wcb_weight_coverage_pct, 2)}%")

    if breadth_wcb_relationship == "CONFIRM_BEARISH":
        shadow_confidence += 5.0
        reasons.append("Breadth and WCB jointly confirm bearishness")
    elif breadth_wcb_relationship == "CONFIRM_BULLISH":
        shadow_confidence += 5.0
        reasons.append("Breadth and WCB jointly confirm bullishness")
    elif breadth_wcb_relationship in (
        "DIVERGENT_BREADTH_BULL_WCB_BEAR",
        "DIVERGENT_BREADTH_BEAR_WCB_BULL",
    ):
        shadow_confidence -= 8.0
        cautions.append("Breadth and WCB diverge")

        if baseline_direction_bias in ("BULLISH", "BEARISH") and baseline_confidence_score < 70.0:
            shadow_direction_bias = "NEUTRAL"
            shadow_trade_allowed = False
            shadow_action = "DO_NOTHING"
            shadow_entry_quality = "NO_TRADE"
            cautions.append("Shadow policy neutralized directional bias due to WCB divergence")
    elif breadth_wcb_relationship == "WCB_NEUTRAL":
        shadow_confidence -= 2.0
        cautions.append("WCB is neutral")
    elif breadth_wcb_relationship == "UNKNOWN":
        cautions.append("Breadth/WCB relationship unavailable")

    if wcb_weight_coverage_pct is not None:
        if wcb_weight_coverage_pct < 85.0:
            shadow_confidence -= 4.0
            cautions.append("WCB coverage is weak")
        elif wcb_weight_coverage_pct < 95.0:
            shadow_confidence -= 2.0
            cautions.append("WCB coverage is partial")

    shadow_confidence = max(0.0, min(100.0, round(shadow_confidence, 1)))

    if shadow_trade_allowed:
        if shadow_confidence >= 75:
            shadow_entry_quality = "HIGH"
        elif shadow_confidence >= 60:
            shadow_entry_quality = "MEDIUM"
        else:
            shadow_entry_quality = "LOW"
    else:
        shadow_entry_quality = "NO_TRADE"

    shadow_decision_changed = (
        shadow_action != baseline_action
        or shadow_trade_allowed != baseline_trade_allowed
        or shadow_direction_bias != baseline_direction_bias
    )

    reasons = _dedupe_strings(reasons)
    cautions = _dedupe_strings(cautions)

    return {
        "shadow_action": shadow_action,
        "shadow_trade_allowed": shadow_trade_allowed,
        "shadow_entry_quality": shadow_entry_quality,
        "shadow_direction_bias": shadow_direction_bias,
        "shadow_confidence_score": shadow_confidence,
        "shadow_delta_confidence": round(shadow_confidence - baseline_confidence_score, 1),
        "shadow_decision_changed": shadow_decision_changed,
        "breadth_wcb_relationship": breadth_wcb_relationship,
        "wcb_regime": wcb_regime,
        "wcb_score": wcb_score,
        "wcb_alignment": wcb_alignment,
        "wcb_weight_coverage_pct": wcb_weight_coverage_pct,
        "gamma_regime": gamma_regime,
        "breadth_regime": breadth_regime,
        "breadth_score": breadth_score,
        "volatility_regime": volatility_regime,
        "reasons": reasons,
        "cautions": cautions,
    }


def _build_shadow_row(symbol: str) -> Dict[str, Any]:
    sb = SupabaseClient()

    market_state = _latest_market_state(sb, symbol)
    baseline_signal = _latest_baseline_signal(sb, symbol)

    derived = _derive_shadow_from_baseline(
        baseline_signal=baseline_signal,
        market_state=market_state,
    )

    row: Dict[str, Any] = {
        "ts": baseline_signal.get("ts"),
        "market_state_ts": market_state.get("ts"),
        "symbol": symbol,
        "expiry_date": baseline_signal.get("expiry_date"),
        "expiry_type": baseline_signal.get("expiry_type"),
        "dte": _to_int(baseline_signal.get("dte")),
        "spot": _to_float(baseline_signal.get("spot")),

        "baseline_signal_id": _to_int(baseline_signal.get("id")),
        "baseline_action": baseline_signal.get("action"),
        "baseline_trade_allowed": baseline_signal.get("trade_allowed"),
        "baseline_entry_quality": baseline_signal.get("entry_quality"),
        "baseline_direction_bias": baseline_signal.get("direction_bias"),
        "baseline_confidence_score": _to_float(baseline_signal.get("confidence_score")),

        "shadow_action": derived["shadow_action"],
        "shadow_trade_allowed": derived["shadow_trade_allowed"],
        "shadow_entry_quality": derived["shadow_entry_quality"],
        "shadow_direction_bias": derived["shadow_direction_bias"],
        "shadow_confidence_score": derived["shadow_confidence_score"],

        "shadow_delta_confidence": derived["shadow_delta_confidence"],
        "shadow_decision_changed": derived["shadow_decision_changed"],

        "gamma_regime": derived["gamma_regime"],
        "breadth_regime": derived["breadth_regime"],
        "breadth_score": derived["breadth_score"],
        "volatility_regime": derived["volatility_regime"],

        "wcb_regime": derived["wcb_regime"],
        "wcb_score": derived["wcb_score"],
        "wcb_alignment": derived["wcb_alignment"],
        "wcb_weight_coverage_pct": derived["wcb_weight_coverage_pct"],
        "breadth_wcb_relationship": derived["breadth_wcb_relationship"],

        "shadow_policy_version": SHADOW_POLICY_VERSION,
        "reasons": derived["reasons"],
        "cautions": derived["cautions"],
        "raw": {
            "baseline_signal_created_at": baseline_signal.get("created_at"),
            "market_state_created_at": market_state.get("created_at"),
            "wcb_features": market_state.get("wcb_features"),
            "source": "build_shadow_signal_local.py",
        },
    }

    print("=" * 72)
    print("MERDIAN - Shadow Signal Engine")
    print("=" * 72)
    print(f"Symbol: {symbol}")
    print("-" * 72)
    print("Baseline signal:")
    print(json.dumps(baseline_signal, indent=2, default=str))
    print("-" * 72)
    print("Derived shadow row:")
    print(json.dumps(row, indent=2, default=str))
    print("-" * 72)

    out_file = DATA_DIR / f"latest_shadow_signal_{symbol}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(row, f, indent=2, default=str)

    print(f"Shadow signal saved to: {out_file}")
    print("SHADOW SIGNAL ENGINE COMPLETED")
    print("=" * 72)

    return row


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: python .\\build_shadow_signal_local.py NIFTY")

    symbol = sys.argv[1].strip().upper()
    if symbol not in ("NIFTY", "SENSEX"):
        raise RuntimeError("Symbol must be NIFTY or SENSEX")

    row = _build_shadow_row(symbol)

    sb = SupabaseClient()
    inserted = sb.insert("shadow_signal_snapshots", [row])
    _ = inserted


if __name__ == "__main__":
    main()