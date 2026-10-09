"""
core.ts_parse — the single PostgREST timestamp parser.

WHY THIS EXISTS
    PostgREST trims trailing zeros from the microsecond fraction, so a stored
    `555900` arrives on the wire as `.5559`. Python 3.10's
    `datetime.fromisoformat` accepts a fraction of EXACTLY 0, 3 or 6 digits and
    raises `ValueError` on widths 1, 2, 4 and 5; 3.11+ is permissive. The box is
    **3.10.12** (measured), so ~9.91 % of timestamps are unparseable by a bare
    `fromisoformat` — P(width ∈ {1,2,4,5}) = 0.09 + 0.009 + 9e-5 + 9e-6.

    `grep -rn "ljust(6"` found ~40 independent copies of this padding across the
    repo and **`core/` held none** — the only `fromisoformat` in `core/` was
    `trading_calendar_gate.py:174`, on a date-only string. TD-S91-NEW-1 and
    TD-S91-NEW-2 both said in their own docstrings that one shared `core/`
    helper was the right fix and deliberately was not that change. This is that
    change.

THERE ARE TWO WIRES, NOT ONE — added S93, measured, see `norm_offset`
    PostgREST renders a UTC `timestamptz` as `+00:00`. **psql renders it as
    `+00`** — a TWO-digit offset — and `bin/roq.sh` is psql, so golden fixtures
    and CSV exports produced through it carry that form. (Measured on one:
    `tests/golden/2026-10-01_SENSEX`. Every psql export is expected to carry it,
    but only that fixture was checked.)
    Python 3.10's `fromisoformat` rejects it, and `FRAC_RE`'s lookahead requires
    a four-digit offset, so before S93 this module returned **None** on it: the
    fraction went unpadded AND the string went unparsed. Measured 2026-10-09 on
    `tests/golden/2026-10-01_SENSEX` — `'2026-10-01 03:30:07.358252+00'` and
    `'2026-10-01 09:45:00+00'` both returned None, the second with no fraction at
    all, which is how it is known to be the offset and not the padding.

    This mattered because the silence is the contract (see `parse_pg_ts` below):
    a module calling itself *the* shared parser while returning None on the form
    its own export tool produces hands every adopting site a None it is then free
    to skip. `tests/test_dex_recompute.py` was the first site to adopt the helper
    from a fixture rather than from the wire, and it is where this surfaced.

NOTHING HERE IS NEW LOGIC, WITH ONE EXCEPTION STATED AS SUCH: `norm_offset` is
new (S93). Everything else is LIFTED, with provenance:
    `FRAC_RE`    verbatim from `write_gex_cycle_history_local.py:80` (bcadfa6),
                 which took it verbatim from `check_contracts_shadow.py:177`.
                 Four live copies agree on this pattern character for character;
                 it is not re-derived here, because a re-derivation that differed
                 by one character would be a new defect wearing a fixed one's name.
    `norm_frac`  the body of `write_gex_cycle_history_local._norm_frac:83-98`
                 (bcadfa6) and `build_market_spot_session_markers._norm_frac:34-58`
                 (b48532e), which are byte-identical to each other.
    `parse_pg_ts` the padding above wrapped in the EXISTING contract of
                 `compute_basis_context_local.parse_ts:61-71` — `if not value`,
                 naive → assume UTC, then `astimezone(UTC)`, and
                 `except → None`. Only the `norm_frac` call is added.

A WARNING FOR WHOEVER ADOPTS THIS NEXT — the sites are NOT interchangeable
    `parse_pg_ts` **normalises to UTC**. `build_market_spot_session_markers.parse_ts`
    (site 2) deliberately does NOT: it returns the datetime with its original
    offset and has no naive-input branch. Swapping `parse_pg_ts` in there would
    be a silent behaviour change, not a refactor. Adopt `norm_frac` at such a
    site and leave its own wrapper alone, or read the callers first.
    `write_gex_cycle_history._ist_date` converts to **IST** and takes `.date()`,
    which is a third contract again.

WHAT THIS DOES NOT DO
    A fraction wider than 6 digits does not match `FRAC_RE` (the lookahead fails
    at every backtrack), so it is passed through unpadded and `fromisoformat`
    raises → `None`. Postgres never emits more than 6, so this is a
    does-not-arise case rather than a handled one, and the test asserts the
    `None` so the behaviour is recorded rather than assumed.

    A compact four-digit offset (`+0000`) is still NOT normalised. Neither wire
    emits it — PostgREST gives `+00:00`, psql gives `+00` — so handling it would
    widen past what has been measured, which is the error `norm_offset`'s own
    scope note exists to avoid. It remains interpreter-defined pass-through and
    `tests/test_ts_parse_core.py` records it with `measured()`, not `check()`.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

__all__ = ["FRAC_RE", "OFFSET_HH_RE", "norm_frac", "norm_offset", "parse_pg_ts"]

UTC = timezone.utc

# Verbatim from write_gex_cycle_history_local.py:80 / check_contracts_shadow.py:177.
FRAC_RE = re.compile(r"\.(\d{1,6})(?=[+-]\d{2}:?\d{2}$|Z$|$)")

# S93, new here. A trailing two-digit offset, and ONLY when a real HH:MM time sits
# immediately before it. The time prefix is not decoration: `([+-]\d{2})$` alone
# also matches the tail of a BARE DATE, turning `2026-10-08` into
# `2026-10-08:00` (measured 2026-10-09, not inferred). That form then
# `fromisoformat`s to the SAME instant, 2026-10-08 00:00:00 — so the corruption is
# invisible to any test that compares parsed values, and only the string-level
# assertion on `norm_offset` itself catches it
# (`tests/test_ts_parse_core.py` cell 10).
OFFSET_HH_RE = re.compile(r"(\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?)([+-]\d{2})$")


def norm_frac(ts_iso: str) -> str:
    """Pad the microsecond fraction of an ISO-8601 string to 6 digits.

    Widths 1-6 are padded with trailing zeros; a string with no fraction is
    returned unchanged (and parses fine). Padding, never stripping: `.6` must
    become 600000 microseconds, not 6, so the two are not interchangeable and
    the test asserts the exact microsecond value.

    Note on ordering: callers replace a trailing `Z` with `+00:00` BEFORE
    calling this, which makes the `Z$` branch of the lookahead vestigial on
    that path. It is kept because the pattern is shared verbatim with three
    other live copies, and a local "tidy-up" would fork it.
    """
    return FRAC_RE.sub(lambda m: "." + m.group(1).ljust(6, "0"), ts_iso)


def norm_offset(ts_iso: str) -> str:
    """Expand a trailing two-digit UTC offset to `[+-]HH:MM`. S93.

    `+00` -> `+00:00`, `+05` -> `+05:00`. This is psql's rendering of a
    `timestamptz` (`bin/roq.sh`, and the `tests/golden/2026-10-01_SENSEX` fixture
    measured in the module docstring); PostgREST's `+00:00` is already in the
    target form and is returned unchanged.

    WIDENING ONLY, by construction rather than by hope. The pattern is anchored
    at `$` and requires a two-digit offset, so it cannot match `+00:00`,
    `+05:30`, `+0000`, a naive string, or a bare date — i.e. it cannot match any
    string a previous `fromisoformat` accepted, because 3.10 accepted none of
    the forms this adds. Nothing that parsed before parses differently.

    CALLED BEFORE `norm_frac`, and the order is load-bearing: `FRAC_RE`'s
    lookahead demands a four-digit offset, so on `...358252+00` the fraction
    would not pad either. Fixing the offset first is what lets the existing
    padding apply to this wire at all.

    SCOPE, stated so the next widening is a decision and not a drift: only the
    form measured on 2026-10-09 is handled. `+0000` is not (see the module
    docstring), and a seconds-bearing offset (`+05:30:30`) is not — Postgres
    emits neither for these columns.
    """
    return OFFSET_HH_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}:00", ts_iso)


def parse_pg_ts(value: Any) -> Optional[datetime]:
    """A PostgREST or psql timestamp string -> aware datetime in UTC, or None.

    Handles: fraction widths 0-6, a trailing `Z`, a `±HH:MM` offset, a psql
    `±HH` offset (S93), and a naive string (assumed UTC). Returns None for None,
    '', a non-timestamp, and anything `fromisoformat` rejects after
    normalisation.

    The `except -> None` is deliberate and inherited from the call sites: their
    callers test for None rather than catching, so bad input must come back as
    None rather than raising. That also means a parse failure here is SILENT by
    design — `compute_basis_context_local` records it as `no_rows`, which is
    indistinguishable in the log from a genuinely absent row. If you need to
    tell those apart, test the return against the input, not the log.
    """
    if not value:
        return None
    try:
        text = norm_frac(norm_offset(str(value).replace("Z", "+00:00")))
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:  # noqa: BLE001 — None-on-bad-input is the contract
        return None
