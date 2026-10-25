"""merdian_compute.pin — the ENH-133 pin-state ladder, pure (S101 C4).

S101_C4_PIN_PATH: the state names and key_for were moved byte-identical from core/pin_state.py;
derive_core is derive()'s null checks plus its ladder, cut verbatim. The thresholds that
core.pin_state.derive reads from merdian_parameters are arguments here, so retail passes
its own. No I/O, no env, no network, no DB.
"""

from __future__ import annotations

from typing import Optional

# The four states, in the order the ladder tests them. Mirrors the CHECK
# constraint in sql/2026-10-03_s89_gex_cycle_history.sql.
NO_PIN = "NO PIN"

SHIFTING = "SHIFTING"

LOCKED = "LOCKED"

STABLE = "STABLE"

VALID_STATES = frozenset({NO_PIN, SHIFTING, LOCKED, STABLE})

# Dot-key suffixes, per symbol. Kept as a tuple so a caller can pre-flight the
# whole set (see `missing_keys`) without duplicating the names.
_KEY_SUFFIXES = (
    "nopin_conc_floor",
    "stable_held_for",
    "locked_held_for",
    "locked_ratio_max",
)

def key_for(suffix: str, symbol: str) -> str:
    """The ADR-016 dot-key for one threshold, e.g. pin_state.stable_held_for.NIFTY."""
    return f"pin_state.{suffix}.{symbol}"


def derive_core(
    held_for_cycles: Optional[int],
    runnerup_share_ratio: Optional[float],
    conc_top1_share: Optional[float],
    *,
    nopin_conc_floor: float,
    stable_held_for: float,
    locked_held_for: float,
    locked_ratio_max: float,
) -> tuple[Optional[str], Optional[str]]:
    """(pin_state, reason) from the inputs and the four thresholds. First match wins:
    conc < nopin_conc_floor -> NO PIN; held < stable_held_for -> SHIFTING;
    held >= locked_held_for and ratio <= locked_ratio_max -> LOCKED; else STABLE.
    A NULL conc or held returns (None, reason); a NULL ratio degrades LOCKED to STABLE.
    """
    # Inputs first. A NULL input is not a missing parameter and must not be
    # reported as one — the two have different fixes.
    if conc_top1_share is None:
        return None, "null input: conc_top1_share"
    if held_for_cycles is None:
        return None, "null input: held_for_cycles"

    if conc_top1_share < nopin_conc_floor:
        return NO_PIN, None

    if held_for_cycles < stable_held_for:
        return SHIFTING, None

    # LOCKED needs BOTH a long streak and a clear lead. runnerup_share_ratio
    # NULL cannot satisfy "<= max", so it falls through to STABLE rather than
    # being treated as 0 — a NULL ratio is a gap, never a zero.
    if (
        held_for_cycles >= locked_held_for
        and runnerup_share_ratio is not None
        and runnerup_share_ratio <= locked_ratio_max
    ):
        return LOCKED, None

    return STABLE, None
