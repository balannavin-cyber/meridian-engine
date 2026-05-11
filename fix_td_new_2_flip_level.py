"""
fix_td_new_2_flip_level.py

TD-NEW-2 patch: fix flip_level regression starting 2026-05-08 caused by spurious
deep-ITM CE gamma values from Dhan and a bottom-up cumulative-walk algorithm
that resolves to the first (often spurious) zero-crossing.

Two-part defense:
  Part A — signed_gamma_exposure() rejects rows where a strike >5% from spot
           returns gamma > 5e-5 (legitimate deep-ITM gamma is near zero).
  Part B — compute_flip_level() walks outward from ATM in both directions and
           returns the zero-crossing closest to spot, which is the operationally
           meaningful flip.

Pattern: writes _PRE_TD-NEW-2.py backup, then writes _PATCHED.py for dry-run
inspection. Operator manually renames PATCHED -> canonical after replay
verification passes.

Per CLAUDE.md:
  - BOM-safe read (read_bytes + decode utf-8-sig)
  - EOL detection + preservation on write
  - ast.parse self-validation before write
  - write_bytes to avoid Windows LF->CRLF silent conversion
"""

from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOURCE_PATH = Path(r"C:\GammaEnginePython\compute_gamma_metrics_local.py")
BACKUP_PATH = Path(r"C:\GammaEnginePython\compute_gamma_metrics_local_PRE_TD-NEW-2.py")
PATCHED_PATH = Path(r"C:\GammaEnginePython\compute_gamma_metrics_local_PATCHED.py")


# ---------------------------------------------------------------------------
# Edit 1: signed_gamma_exposure — Part A input sanity guard
# ---------------------------------------------------------------------------

OLD_SIGNED_GAMMA = """def signed_gamma_exposure(row: dict[str, Any], spot: float) -> float:
    gamma = to_float(row.get("gamma"))
    oi = to_float(row.get("oi"))
    option_type = str(row.get("option_type", "")).upper()

    if gamma == 0.0 or oi <= 0.0 or spot <= 0.0:
        return 0.0

    base = gamma * oi * (spot ** 2)
    return -base if option_type == "PE" else base"""

NEW_SIGNED_GAMMA = """def signed_gamma_exposure(row: dict[str, Any], spot: float) -> float:
    gamma = to_float(row.get("gamma"))
    oi = to_float(row.get("oi"))
    option_type = str(row.get("option_type", "")).upper()
    strike = to_float(row.get("strike"))

    if gamma == 0.0 or oi <= 0.0 or spot <= 0.0:
        return 0.0

    # TD-NEW-2 Part A: reject deep-ITM rows with spurious gamma.
    # Options >5% from spot should have near-zero gamma in reality.
    # Threshold 5e-5 is ~5x typical ATM gamma; well outside legitimate
    # deep-ITM values. Dhan started returning gamma=7e-5 at strike 21,250
    # CE with spot 24,200 on 2026-05-08, polluting the flip-level walk.
    if strike > 0 and abs(strike - spot) / spot > 0.05:
        if abs(gamma) > 5e-5:
            return 0.0

    base = gamma * oi * (spot ** 2)
    return -base if option_type == "PE" else base"""


# ---------------------------------------------------------------------------
# Edit 2: compute_flip_level — Part B walk-from-ATM algorithm
# ---------------------------------------------------------------------------

OLD_COMPUTE_FLIP = """def compute_flip_level(strike_map: dict[float, float]) -> float | None:
    if not strike_map:
        return None

    strikes = sorted(strike_map.keys())
    cumulative_points: list[tuple[float, float]] = []

    running = 0.0
    for strike in strikes:
        running += strike_map[strike]
        cumulative_points.append((strike, running))

    if len(cumulative_points) < 2:
        return None

    for i in range(1, len(cumulative_points)):
        strike_prev, cum_prev = cumulative_points[i - 1]
        strike_curr, cum_curr = cumulative_points[i]

        if cum_prev == 0.0:
            return strike_prev
        if cum_curr == 0.0:
            return strike_curr

        if (cum_prev < 0.0 < cum_curr) or (cum_prev > 0.0 > cum_curr):
            denom = cum_curr - cum_prev
            if denom == 0:
                return None
            frac = -cum_prev / denom
            return strike_prev + frac * (strike_curr - strike_prev)"""

NEW_COMPUTE_FLIP = '''def compute_flip_level(strike_map: dict[float, float], spot: float | None = None) -> float | None:
    """Find the operational gamma flip strike.

    TD-NEW-2 Part B: walk outward from ATM in both directions and return the
    zero-crossing closest to spot. The original bottom-up walk returned the
    first zero-crossing from min_strike, which is fragile to spurious
    contributions at deep-ITM strikes (see 2026-05-08 regression where a
    single bad row at strike 21,250 made flip_level resolve to 21,250 instead
    of the real ~24,800).

    spot parameter is keyword-optional for backward compatibility with any
    caller that hasn't been updated; when omitted, falls back to the legacy
    bottom-up walk. New code should pass spot.
    """
    if not strike_map:
        return None

    strikes = sorted(strike_map.keys())
    cumulative_points: list[tuple[float, float]] = []

    running = 0.0
    for strike in strikes:
        running += strike_map[strike]
        cumulative_points.append((strike, running))

    if len(cumulative_points) < 2:
        return None

    # Legacy fallback: caller didn't supply spot. Preserve original behavior.
    if spot is None or spot <= 0:
        for i in range(1, len(cumulative_points)):
            strike_prev, cum_prev = cumulative_points[i - 1]
            strike_curr, cum_curr = cumulative_points[i]
            if cum_prev == 0.0:
                return strike_prev
            if cum_curr == 0.0:
                return strike_curr
            if (cum_prev < 0.0 < cum_curr) or (cum_prev > 0.0 > cum_curr):
                denom = cum_curr - cum_prev
                if denom == 0:
                    return None
                frac = -cum_prev / denom
                return strike_prev + frac * (strike_curr - strike_prev)
        return None

    # Walk-from-ATM: collect candidate flip strikes on both sides of spot,
    # return the one closest to spot (operational flip definition).
    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    candidates: list[float] = []

    # Walk downward from ATM toward min_strike
    for i in range(atm_idx, 0, -1):
        strike_curr, cum_curr = cumulative_points[i]
        strike_prev, cum_prev = cumulative_points[i - 1]
        if cum_prev == 0.0:
            candidates.append(strike_prev)
            break
        if cum_curr == 0.0:
            candidates.append(strike_curr)
            break
        if (cum_prev < 0.0 < cum_curr) or (cum_prev > 0.0 > cum_curr):
            denom = cum_curr - cum_prev
            if denom != 0:
                frac = -cum_prev / denom
                candidates.append(strike_prev + frac * (strike_curr - strike_prev))
            break

    # Walk upward from ATM toward max_strike
    for i in range(atm_idx, len(cumulative_points) - 1):
        strike_curr, cum_curr = cumulative_points[i]
        strike_next, cum_next = cumulative_points[i + 1]
        if cum_curr == 0.0:
            candidates.append(strike_curr)
            break
        if cum_next == 0.0:
            candidates.append(strike_next)
            break
        if (cum_curr < 0.0 < cum_next) or (cum_curr > 0.0 > cum_next):
            denom = cum_next - cum_curr
            if denom != 0:
                frac = -cum_curr / denom
                candidates.append(strike_curr + frac * (strike_next - strike_curr))
            break

    if not candidates:
        return None
    return min(candidates, key=lambda x: abs(x - spot))'''


# ---------------------------------------------------------------------------
# Edit 3: call site update at the orchestrator inside compute_gamma_metrics
# ---------------------------------------------------------------------------

OLD_CALL_SITE = "    flip_level = compute_flip_level(strike_map)"
NEW_CALL_SITE = "    flip_level = compute_flip_level(strike_map, spot)"


# ---------------------------------------------------------------------------
# IO helpers — BOM-safe read, EOL detection, byte-safe write
# ---------------------------------------------------------------------------

def read_source(path: Path) -> tuple[str, str]:
    """Read file as text with BOM stripped. Returns (text_lf, predominant_eol)."""
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    raw_bytes = path.read_bytes()
    text = raw_bytes.decode("utf-8-sig")  # strips BOM if present
    # Detect EOL
    crlf_count = text.count("\r\n")
    lf_count = text.count("\n") - crlf_count
    predominant = "\r\n" if crlf_count > lf_count else "\n"
    # Normalize to LF for in-memory editing
    text_lf = text.replace("\r\n", "\n")
    return text_lf, predominant


def write_with_eol(path: Path, text_lf: str, eol: str) -> None:
    """Write text with the requested EOL, as bytes (avoids Windows CRLF coercion)."""
    final_text = text_lf.replace("\n", eol) if eol != "\n" else text_lf
    path.write_bytes(final_text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Patch application
# ---------------------------------------------------------------------------

def apply_edit(text: str, old: str, new: str, label: str) -> str:
    """Replace exactly one occurrence of `old` with `new`. Fail otherwise."""
    count = text.count(old)
    if count == 0:
        raise RuntimeError(
            f"Edit {label}: pattern not found. Source may have drifted from expected layout."
        )
    if count > 1:
        raise RuntimeError(
            f"Edit {label}: pattern matched {count} times, expected exactly 1."
        )
    return text.replace(old, new, 1)


def main() -> int:
    print(f"[TD-NEW-2 patch] Source: {SOURCE_PATH}")

    if not SOURCE_PATH.exists():
        print(f"ERROR: source not found: {SOURCE_PATH}", file=sys.stderr)
        return 2

    text_lf, eol = read_source(SOURCE_PATH)
    eol_label = "CRLF" if eol == "\r\n" else "LF"
    print(f"[TD-NEW-2 patch] Read {len(text_lf):,} chars, EOL={eol_label}")

    # Apply three edits
    try:
        text_lf = apply_edit(text_lf, OLD_SIGNED_GAMMA, NEW_SIGNED_GAMMA, "1 signed_gamma_exposure")
        print("[TD-NEW-2 patch] Edit 1 applied: signed_gamma_exposure +sanity guard")

        text_lf = apply_edit(text_lf, OLD_COMPUTE_FLIP, NEW_COMPUTE_FLIP, "2 compute_flip_level")
        print("[TD-NEW-2 patch] Edit 2 applied: compute_flip_level walk-from-ATM")

        text_lf = apply_edit(text_lf, OLD_CALL_SITE, NEW_CALL_SITE, "3 call site")
        print("[TD-NEW-2 patch] Edit 3 applied: call site now passes spot")
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    # Self-validate via ast.parse
    try:
        ast.parse(text_lf, filename=str(PATCHED_PATH))
        print("[TD-NEW-2 patch] ast.parse OK")
    except SyntaxError as exc:
        print(f"ERROR: patched source fails ast.parse: {exc}", file=sys.stderr)
        return 4

    # Backup original (only if not already present — keeps the first canonical backup)
    if not BACKUP_PATH.exists():
        shutil.copy2(SOURCE_PATH, BACKUP_PATH)
        print(f"[TD-NEW-2 patch] Backup written: {BACKUP_PATH.name}")
    else:
        print(f"[TD-NEW-2 patch] Backup already exists, preserved: {BACKUP_PATH.name}")

    # Write patched file
    write_with_eol(PATCHED_PATH, text_lf, eol)
    print(f"[TD-NEW-2 patch] Patched file written: {PATCHED_PATH.name}")
    print()
    print("Next steps:")
    print(f"  1. Inspect diff:  fc {SOURCE_PATH.name} {PATCHED_PATH.name}")
    print(f"  2. Replay 2026-05-07 09:30 IST cycle against PATCHED (expect no regression)")
    print(f"  3. Replay 2026-05-08 09:30 IST cycle against PATCHED (expect realistic flip)")
    print(f"  4. If both pass: ren {PATCHED_PATH.name} {SOURCE_PATH.name}")
    print(f"  5. Backfill gamma_metrics for 2026-05-08 onwards via replay_compute_gamma_metrics.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
