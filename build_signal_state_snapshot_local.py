from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


def print_banner(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()
    if required and not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        x = float(value)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


class SupabaseRestClient:
    def __init__(self) -> None:
        load_dotenv(ENV_FILE, override=True)
        self.base_url = get_env("SUPABASE_URL").rstrip("/")
        self.api_key = get_env("SUPABASE_SERVICE_ROLE_KEY")

        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def latest_state(self, symbol: str) -> dict[str, Any]:
        url = f"{self.base_url}/rest/v1/market_state_snapshots"
        params = {
            "select": "*",
            "symbol": f"eq.{symbol}",
            "order": "created_at.desc",
            "limit": "1",
        }
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise RuntimeError(f"No market state found for symbol={symbol}")
        return data[0]

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/rest/v1/signal_state_snapshots"
        headers = dict(self.headers)
        headers["Prefer"] = "return=representation"
        response = requests.post(url, headers=headers, json=[row], timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise RuntimeError("Insert returned no rows")
        return data[0]


# ============================================================================
# SIGNAL LOGIC V2.1
# ============================================================================

def derive_gamma_bias(gamma_features: dict[str, Any]) -> str:
    regime = str(gamma_features.get("gamma_regime") or "").upper()

    if regime == "LONG_GAMMA":
        return "MEAN_REVERSION"
    if regime == "SHORT_GAMMA":
        return "TREND_AMPLIFICATION"

    return "UNKNOWN"


def derive_gamma_zone(gamma_features: dict[str, Any]) -> str | None:
    flip_pct = to_float(gamma_features.get("flip_distance_pct"))

    if flip_pct is None:
        return None
    if flip_pct < 1.0:
        return "NEAR_FLIP"
    if flip_pct < 3.0:
        return "MID_ZONE"
    return "FAR_FROM_FLIP"


def derive_breadth_strength(breadth_features: dict[str, Any]) -> str:
    regime = breadth_features.get("breadth_regime")
    score = to_float(breadth_features.get("breadth_score"))

    if regime is None and score is None:
        return "UNAVAILABLE"

    regime_text = str(regime or "").upper()

    if "BULL" in regime_text:
        return "BULLISH"
    if "BEAR" in regime_text:
        return "BEARISH"

    if score is not None:
        if score >= 60:
            return "BULLISH"
        if score <= 40:
            return "BEARISH"

    return "NEUTRAL"


def derive_wcb_confirmation(wcb_features: dict[str, Any], breadth_strength: str) -> str:
    wcb_regime = str(wcb_features.get("wcb_regime") or "").upper()

    if not wcb_regime:
        return "UNAVAILABLE"

    if "BULL" in wcb_regime and breadth_strength == "BULLISH":
        return "CONFIRMS_UP"
    if "BEAR" in wcb_regime and breadth_strength == "BEARISH":
        return "CONFIRMS_DOWN"

    if "BULL" in wcb_regime:
        return "BULLISH"
    if "BEAR" in wcb_regime:
        return "BEARISH"

    return "UNAVAILABLE"


def derive_momentum_alignment(momentum_features: dict[str, Any]) -> tuple[str, str | None]:
    regime = str(momentum_features.get("momentum_regime") or "").upper()

    if regime == "UP":
        return "UP_ALIGNED", "UP"
    if regime == "DOWN":
        return "DOWN_ALIGNED", "DOWN"
    if regime == "MIXED":
        return "NEUTRAL", "MIXED"

    return "NEUTRAL", None


def derive_basis_pressure(basis_pct: float | None) -> str | None:
    if basis_pct is None:
        return None
    if basis_pct >= 0.10:
        return "POSITIVE_BASIS"
    if basis_pct <= -0.10:
        return "NEGATIVE_BASIS"
    return "FLAT_BASIS"


def derive_volatility_pressure(volatility_features: dict[str, Any]) -> str | None:
    vix_context_regime = str(volatility_features.get("vix_context_regime") or "").upper()
    vix_direction = str(volatility_features.get("vix_direction") or "").upper()
    vix_intraday_velocity = str(volatility_features.get("vix_intraday_velocity") or "").upper()
    atm_iv_vs_vix_spread = to_float(volatility_features.get("atm_iv_vs_vix_spread"))

    if vix_context_regime == "HIGH_CONTEXT" and "RISING" in vix_intraday_velocity:
        return "EXPANSION_PRESSURE"
    if vix_context_regime == "HIGH_CONTEXT" and "FALLING" in vix_intraday_velocity:
        return "VOL_EASING"
    if vix_direction == "UP" and atm_iv_vs_vix_spread is not None and atm_iv_vs_vix_spread > 5:
        return "VOL_STRESS_BUILDING"
    if vix_direction == "DOWN":
        return "VOL_EASING"
    return None


def derive_composite_direction(
    gamma_bias: str,
    momentum_alignment: str,
    breadth_strength: str,
) -> str:
    if (
        gamma_bias == "TREND_AMPLIFICATION"
        and momentum_alignment == "DOWN_ALIGNED"
        and breadth_strength == "BEARISH"
    ):
        return "DOWN"

    if (
        gamma_bias == "TREND_AMPLIFICATION"
        and momentum_alignment == "UP_ALIGNED"
        and breadth_strength == "BULLISH"
    ):
        return "UP"

    if momentum_alignment == "DOWN_ALIGNED" and breadth_strength == "BEARISH":
        return "DOWN"

    if momentum_alignment == "UP_ALIGNED" and breadth_strength == "BULLISH":
        return "UP"

    return "NEUTRAL"


def derive_conviction(
    wcb_confirmation: str,
    breadth_strength: str,
    gamma_bias: str,
) -> str:
    if (
        gamma_bias == "TREND_AMPLIFICATION"
        and (
            wcb_confirmation == "CONFIRMS_DOWN"
            or wcb_confirmation == "CONFIRMS_UP"
        )
        and breadth_strength in {"BULLISH", "BEARISH"}
    ):
        return "HIGH"

    if breadth_strength in {"BULLISH", "BEARISH"}:
        return "MEDIUM"

    return "LOW"


def derive_signal_state(direction: str, conviction: str) -> str:
    if direction == "DOWN" and conviction in {"HIGH", "MEDIUM"}:
        return "SELL_SIGNAL"
    if direction == "UP" and conviction in {"HIGH", "MEDIUM"}:
        return "BUY_SIGNAL"
    return "NEUTRAL_STATE"


# ============================================================================
# MAIN
# ============================================================================

def run(symbol: str) -> None:
    print_banner("MERDIAN - Signal State Builder V2.1")
    print(f"Symbol: {symbol}")
    print("-" * 72)

    client = SupabaseRestClient()
    state = client.latest_state(symbol)

    gamma = state.get("gamma_features") or {}
    breadth = state.get("breadth_features") or {}
    wcb = state.get("wcb_features") or {}
    momentum = state.get("momentum_features") or {}
    volatility = state.get("volatility_features") or {}

    gamma_bias = derive_gamma_bias(gamma)
    gamma_zone = derive_gamma_zone(gamma)

    breadth_strength = derive_breadth_strength(breadth)
    breadth_regime = breadth.get("breadth_regime")
    breadth_score = to_float(breadth.get("breadth_score"))

    wcb_confirmation = derive_wcb_confirmation(wcb, breadth_strength)

    momentum_alignment, momentum_regime = derive_momentum_alignment(momentum)

    basis_pct = to_float(state.get("basis_pct"))
    basis_pressure = derive_basis_pressure(basis_pct)

    vix_context_regime = volatility.get("vix_context_regime")
    vix_direction = volatility.get("vix_direction")
    volatility_pressure = derive_volatility_pressure(volatility)

    composite_direction = derive_composite_direction(
        gamma_bias=gamma_bias,
        momentum_alignment=momentum_alignment,
        breadth_strength=breadth_strength,
    )

    composite_conviction = derive_conviction(
        wcb_confirmation=wcb_confirmation,
        breadth_strength=breadth_strength,
        gamma_bias=gamma_bias,
    )

    signal_state = derive_signal_state(
        direction=composite_direction,
        conviction=composite_conviction,
    )

    print("Derived signal state:")
    print(f"market_state_id:       {state.get('id')}")
    print(f"gamma_bias:            {gamma_bias}")
    print(f"gamma_zone:            {gamma_zone}")
    print(f"volatility_pressure:   {volatility_pressure}")
    print(f"vix_context_regime:    {vix_context_regime}")
    print(f"vix_direction:         {vix_direction}")
    print(f"basis_pressure:        {basis_pressure}")
    print(f"basis_pct:             {basis_pct}")
    print(f"breadth_strength:      {breadth_strength}")
    print(f"breadth_regime:        {breadth_regime}")
    print(f"breadth_score:         {breadth_score}")
    print(f"momentum_alignment:    {momentum_alignment}")
    print(f"momentum_regime:       {momentum_regime}")
    print(f"wcb_confirmation:      {wcb_confirmation}")
    print(f"composite_direction:   {composite_direction}")
    print(f"composite_conviction:  {composite_conviction}")
    print(f"signal_state:          {signal_state}")

    row = {
        "ts": state["ts"],
        "symbol": symbol,
        "market_state_id": to_int(state.get("id")),
        "gamma_bias": gamma_bias,
        "gamma_zone": gamma_zone,
        "volatility_pressure": volatility_pressure,
        "vix_context_regime": vix_context_regime,
        "vix_direction": vix_direction,
        "basis_pressure": basis_pressure,
        "basis_pct": basis_pct,
        "breadth_strength": breadth_strength,
        "breadth_regime": breadth_regime,
        "breadth_score": breadth_score,
        "momentum_alignment": momentum_alignment,
        "momentum_regime": momentum_regime,
        "wcb_confirmation": wcb_confirmation,
        "composite_direction": composite_direction,
        "composite_conviction": composite_conviction,
        "signal_state": signal_state,
        "raw": {
            "builder": "SIGNAL_STATE_V2_1",
            "builder_ts_utc": utc_now_iso(),
            "source_state_created_at": state.get("created_at"),
            "gamma_features": gamma,
            "breadth_features": breadth,
            "wcb_features": wcb,
            "momentum_features": momentum,
            "volatility_features": volatility,
        },
    }

    inserted = client.insert(row)

    print("-" * 72)
    print("Inserted signal state:")
    print(json.dumps(inserted, indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python build_signal_state_snapshot_local.py <NIFTY|SENSEX>")
        sys.exit(1)

    run(sys.argv[1].upper())