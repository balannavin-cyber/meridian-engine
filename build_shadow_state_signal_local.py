from __future__ import annotations

import sys
from typing import Any, Dict, Optional

from core.supabase_client import SupabaseClient


def normalize_symbol(value: str) -> str:
    s = value.strip().upper()
    if s not in {"NIFTY", "SENSEX"}:
        raise RuntimeError("Symbol must be NIFTY or SENSEX")
    return s


def get_latest_signal_state(sb: SupabaseClient, symbol: str) -> Dict[str, Any]:
    rows = sb.select(
        table="signal_state_snapshots",
        filters={"symbol": f"eq.{symbol}"},
        order="created_at.desc",
        limit=1,
    )
    if not rows:
        raise RuntimeError(f"No signal_state_snapshots row found for symbol={symbol}")
    return rows[0]


def decide_shadow_action(
    gamma_bias: Optional[str],
    gamma_zone: Optional[str],
    volatility_pressure: Optional[str],
    basis_pressure: Optional[str],
    breadth_strength: Optional[str],
    momentum_alignment: Optional[str],
    wcb_confirmation: Optional[str],
    composite_direction: Optional[str],
    composite_conviction: Optional[str],
    signal_state: Optional[str],
) -> Dict[str, str]:
    gamma_bias = (gamma_bias or "").upper()
    gamma_zone = (gamma_zone or "").upper()
    volatility_pressure = (volatility_pressure or "").upper()
    basis_pressure = (basis_pressure or "").upper()
    breadth_strength = (breadth_strength or "").upper()
    momentum_alignment = (momentum_alignment or "").upper()
    wcb_confirmation = (wcb_confirmation or "").upper()
    composite_direction = (composite_direction or "").upper()
    composite_conviction = (composite_conviction or "").upper()
    signal_state = (signal_state or "").upper()

    action = "DO_NOTHING"
    confidence = "LOW"
    rationale_parts = []

    rationale_parts.append(f"signal_state={signal_state or 'UNKNOWN'}")
    rationale_parts.append(f"composite_direction={composite_direction or 'UNKNOWN'}")
    rationale_parts.append(f"composite_conviction={composite_conviction or 'UNKNOWN'}")
    rationale_parts.append(f"gamma_bias={gamma_bias or 'UNKNOWN'}")
    rationale_parts.append(f"volatility_pressure={volatility_pressure or 'UNKNOWN'}")
    rationale_parts.append(f"basis_pressure={basis_pressure or 'UNKNOWN'}")
    rationale_parts.append(f"breadth_strength={breadth_strength or 'UNKNOWN'}")
    rationale_parts.append(f"momentum_alignment={momentum_alignment or 'UNKNOWN'}")
    rationale_parts.append(f"wcb_confirmation={wcb_confirmation or 'UNKNOWN'}")

    bullish_confirmation = 0
    bearish_confirmation = 0

    if breadth_strength in {"BULLISH", "STRONG_BULLISH"}:
        bullish_confirmation += 1
    elif breadth_strength in {"BEARISH", "STRONG_BEARISH"}:
        bearish_confirmation += 1

    if momentum_alignment == "UP_ALIGNED":
        bullish_confirmation += 1
    elif momentum_alignment == "DOWN_ALIGNED":
        bearish_confirmation += 1

    if wcb_confirmation == "CONFIRMS_UP":
        bullish_confirmation += 1
    elif wcb_confirmation == "CONFIRMS_DOWN":
        bearish_confirmation += 1

    if basis_pressure in {"POSITIVE_BASIS", "STRONG_POSITIVE_BASIS"}:
        bullish_confirmation += 1
    elif basis_pressure in {"NEGATIVE_BASIS", "STRONG_NEGATIVE_BASIS"}:
        bearish_confirmation += 1

    if (
        composite_direction == "UP"
        and composite_conviction in {"MEDIUM", "HIGH"}
        and gamma_bias in {"EXPANSION_READY", "EXPANSION_BIASED"}
        and volatility_pressure in {"EXPANSION_PRESSURE", "EXPANSION_PRESSURE_HIGH", "VOL_STRESS_BUILDING"}
        and bullish_confirmation >= 2
    ):
        action = "BUY_CE"
        confidence = "HIGH" if composite_conviction == "HIGH" else "MEDIUM"
        rationale_parts.append("Bullish expansion setup confirmed.")
        return {
            "shadow_action": action,
            "shadow_confidence": confidence,
            "shadow_rationale": " | ".join(rationale_parts),
        }

    if (
        composite_direction == "DOWN"
        and composite_conviction in {"MEDIUM", "HIGH"}
        and gamma_bias in {"EXPANSION_READY", "EXPANSION_BIASED", "LONG_GAMMA_DRIFT_RISK"}
        and bearish_confirmation >= 2
    ):
        action = "BUY_PE"
        confidence = "HIGH" if composite_conviction == "HIGH" else "MEDIUM"
        rationale_parts.append("Bearish structure confirmed.")
        return {
            "shadow_action": action,
            "shadow_confidence": confidence,
            "shadow_rationale": " | ".join(rationale_parts),
        }

    if signal_state == "NEUTRAL_EXPANSION_WATCH":
        action = "DO_NOTHING"
        confidence = "LOW"
        rationale_parts.append("Expansion watch only; direction not confirmed.")
        return {
            "shadow_action": action,
            "shadow_confidence": confidence,
            "shadow_rationale": " | ".join(rationale_parts),
        }

    if signal_state.startswith("BULLISH_DRIFT"):
        action = "BUY_CE"
        confidence = "LOW" if composite_conviction == "LOW" else "MEDIUM"
        rationale_parts.append("Bullish drift setup.")
        return {
            "shadow_action": action,
            "shadow_confidence": confidence,
            "shadow_rationale": " | ".join(rationale_parts),
        }

    if signal_state.startswith("BEARISH_DRIFT"):
        action = "BUY_PE"
        confidence = "LOW" if composite_conviction == "LOW" else "MEDIUM"
        rationale_parts.append("Bearish drift setup.")
        return {
            "shadow_action": action,
            "shadow_confidence": confidence,
            "shadow_rationale": " | ".join(rationale_parts),
        }

    rationale_parts.append("No clear shadow edge.")
    return {
        "shadow_action": action,
        "shadow_confidence": confidence,
        "shadow_rationale": " | ".join(rationale_parts),
    }


def build_shadow_row(signal_state_row: Dict[str, Any]) -> Dict[str, Any]:
    gamma_bias = signal_state_row.get("gamma_bias")
    gamma_zone = signal_state_row.get("gamma_zone")
    volatility_pressure = signal_state_row.get("volatility_pressure")
    basis_pressure = signal_state_row.get("basis_pressure")
    breadth_strength = signal_state_row.get("breadth_strength")
    momentum_alignment = signal_state_row.get("momentum_alignment")
    wcb_confirmation = signal_state_row.get("wcb_confirmation")
    composite_direction = signal_state_row.get("composite_direction")
    composite_conviction = signal_state_row.get("composite_conviction")
    signal_state = signal_state_row.get("signal_state")

    decision = decide_shadow_action(
        gamma_bias=gamma_bias,
        gamma_zone=gamma_zone,
        volatility_pressure=volatility_pressure,
        basis_pressure=basis_pressure,
        breadth_strength=breadth_strength,
        momentum_alignment=momentum_alignment,
        wcb_confirmation=wcb_confirmation,
        composite_direction=composite_direction,
        composite_conviction=composite_conviction,
        signal_state=signal_state,
    )

    return {
        "ts": signal_state_row["ts"],
        "symbol": signal_state_row["symbol"],
        "signal_state_snapshot_id": signal_state_row["id"],
        "gamma_bias": gamma_bias,
        "gamma_zone": gamma_zone,
        "volatility_pressure": volatility_pressure,
        "basis_pressure": basis_pressure,
        "breadth_strength": breadth_strength,
        "momentum_alignment": momentum_alignment,
        "wcb_confirmation": wcb_confirmation,
        "composite_direction": composite_direction,
        "composite_conviction": composite_conviction,
        "signal_state": signal_state,
        "shadow_action": decision["shadow_action"],
        "shadow_confidence": decision["shadow_confidence"],
        "shadow_rationale": decision["shadow_rationale"],
        "raw": {
            "builder": "build_shadow_state_signal_local.py",
            "builder_version": "SHADOW_STATE_SIGNAL_V1",
            "source_signal_state_created_at": signal_state_row.get("created_at"),
        },
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: python .\\build_shadow_state_signal_local.py <NIFTY|SENSEX>")

    symbol = normalize_symbol(sys.argv[1])

    print("=" * 72)
    print("MERDIAN - Local Python build_shadow_state_signal")
    print("=" * 72)
    print(f"Symbol: {symbol}")
    print("-" * 72)

    sb = SupabaseClient()

    signal_state_row = get_latest_signal_state(sb, symbol)
    print(f"Signal state row id:      {signal_state_row.get('id')}")
    print(f"Signal state created_at:  {signal_state_row.get('created_at')}")

    shadow_row = build_shadow_row(signal_state_row)

    print("-" * 72)
    print("Derived shadow decision:")
    print(f"gamma_bias:              {shadow_row['gamma_bias']}")
    print(f"gamma_zone:              {shadow_row['gamma_zone']}")
    print(f"volatility_pressure:     {shadow_row['volatility_pressure']}")
    print(f"basis_pressure:          {shadow_row['basis_pressure']}")
    print(f"breadth_strength:        {shadow_row['breadth_strength']}")
    print(f"momentum_alignment:      {shadow_row['momentum_alignment']}")
    print(f"wcb_confirmation:        {shadow_row['wcb_confirmation']}")
    print(f"composite_direction:     {shadow_row['composite_direction']}")
    print(f"composite_conviction:    {shadow_row['composite_conviction']}")
    print(f"signal_state:            {shadow_row['signal_state']}")
    print(f"shadow_action:           {shadow_row['shadow_action']}")
    print(f"shadow_confidence:       {shadow_row['shadow_confidence']}")
    print(f"shadow_rationale:        {shadow_row['shadow_rationale']}")

    inserted = sb.insert("shadow_state_signal_snapshots", [shadow_row])
    inserted_id = inserted[0].get("id") if inserted else None

    print("-" * 72)
    print("Shadow state signal snapshot inserted successfully.")
    print(f"Inserted ID:             {inserted_id}")


if __name__ == "__main__":
    main()