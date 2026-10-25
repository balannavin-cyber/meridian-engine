"""ENH-133 — the pin-state machine. THE single home.

RULED 2026-10-03 (`docs/research/s89_rulings/rulings_s89.md`, writer spec §7.0,
reconciler spec §3.2): this module is the only implementation of the pin-state
ladder. `write_gex_cycle_history_local.py` and
`reconcile_gex_cycle_history_session_local.py` both IMPORT it; neither carries
its own copy.

Why that matters rather than being tidy: two implementations of one rule is the
shape ADR-020 was written for — the calendar gate said "no row -> allow" while
the seeder said "no row -> closed", and every unseeded weekend read as a trading
day for ~6 consumers since S60. And a parity claim between two copies is
asserted only by a test that compares them, never by a comment (Rule 0 clause
4). With one home the comparison question does not arise.

THRESHOLDS ARE READ, NEVER HARDCODED. They live in `merdian_parameters`
(ADR-016) under dot-keys and are fetched with `core.parameters.get_parameter_num`
with NO default. A missing key returns (None, reason) — never a substituted
default. Absence is not a verdict.

NOTE, measured 2026-10-03: `merdian_parameters` holds 0 rows and the ADR-016
write path (`merdian_calibrate.py`) is absent from the tree — TD-S89-NEW-2. The
seed is `sql/2026-10-03_s89_seed_pin_state_params.sql`, authored-not-applied.
Until it is applied, every call here returns (None, "missing parameter key: ...")
which is the correct behaviour, not a failure.
"""

from __future__ import annotations

from typing import Optional

from core.parameters import ParameterNotFoundError, get_parameter_num

# S101_C4_PIN_PATH: the ladder's ONE implementation is now merdian_compute.pin.derive_core (pure);
# derive() below reads the thresholds and delegates to it -- still a single home, ruling S89
# holds. The state names and key_for moved with it and are re-imported unchanged.
from merdian_compute.pin import (  # noqa: E402,F401
    NO_PIN,
    SHIFTING,
    LOCKED,
    STABLE,
    VALID_STATES,
    _KEY_SUFFIXES,
    key_for,
    derive_core,
)

def missing_keys(symbol: str) -> list[str]:
    """Which of this symbol's four threshold keys cannot be resolved.

    A pre-flight helper for the acceptance tests and for a writer that wants to
    report the whole gap rather than the first hole. Not used by `derive`, which
    short-circuits on the first missing key by design.
    """
    missing: list[str] = []
    for suffix in _KEY_SUFFIXES:
        key = key_for(suffix, symbol)
        try:
            get_parameter_num(key)
        except ParameterNotFoundError:
            missing.append(key)
    return missing


def derive(
    symbol: str,
    held_for_cycles: Optional[int],
    runnerup_share_ratio: Optional[float],
    conc_top1_share: Optional[float],
) -> tuple[Optional[str], Optional[str]]:
    """Return (pin_state, pin_state_reason).

    Exactly one of the two is non-None:
      * a state, with reason None, when the inputs the ladder needs resolved;
      * None with a reason ONLY when `conc_top1_share` or `held_for_cycles` is
        NULL, or a threshold key is missing. A NULL `runnerup_share_ratio` is
        NOT an error — it degrades LOCKED to STABLE.

    The deliberate edge that follows: a ladder with a single ranked strike has
    no rank 2, so `runnerup_share_ratio` is NULL and the pin reads STABLE,
    never LOCKED. "No runner-up" is treated as "cannot confirm a lock" — the
    conservative call — rather than as "maximally locked" (ratio -> 0), which
    is the other defensible reading. RECORDED CHOICE, provisional, revisitable
    at D-6 calibration; the alternative is on record rather than lost to the
    implementation.

    FIRST MATCH WINS, in this order:
        conc_top1_share < nopin_conc_floor                     -> NO PIN
        held_for_cycles < stable_held_for                       -> SHIFTING
        held_for_cycles >= locked_held_for
            and runnerup_share_ratio <= locked_ratio_max        -> LOCKED
        otherwise                                              -> STABLE

    The order is load-bearing and is not an implementation detail: NO PIN is
    tested first so a ladder with no dominant strike can never be reported
    LOCKED on a long streak, and SHIFTING precedes LOCKED so a short streak
    cannot lock on a tight runner-up ratio alone.
    """
    # Inputs first. A NULL input is not a missing parameter and must not be
    # reported as one — the two have different fixes.
    if conc_top1_share is None:
        return None, "null input: conc_top1_share"
    if held_for_cycles is None:
        return None, "null input: held_for_cycles"

    try:
        nopin_conc_floor = get_parameter_num(key_for("nopin_conc_floor", symbol))
        stable_held_for = get_parameter_num(key_for("stable_held_for", symbol))
        locked_held_for = get_parameter_num(key_for("locked_held_for", symbol))
        locked_ratio_max = get_parameter_num(key_for("locked_ratio_max", symbol))
    except ParameterNotFoundError as e:
        # The exception carries the key; prefer it over reconstructing a name.
        key = str(e).strip("'\"") or "<unknown>"
        return None, f"missing parameter key: {key}"

    return derive_core(
        held_for_cycles,
        runnerup_share_ratio,
        conc_top1_share,
        nopin_conc_floor=nopin_conc_floor,
        stable_held_for=stable_held_for,
        locked_held_for=locked_held_for,
        locked_ratio_max=locked_ratio_max,
    )
