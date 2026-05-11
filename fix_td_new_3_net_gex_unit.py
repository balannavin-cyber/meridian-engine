"""
fix_td_new_3_net_gex_unit.py

TD-NEW-3 patch: standardise net_gex storage to Crore (rupees / 1e7).

Three writer files have identical signed_gamma_exposure / signed_gex functions
that produce raw rupees (gamma * oi * spot^2) without the Crore conversion.
This causes net_gex values to be stored at ~10^13 magnitude when the
operational scale is thousands of Crore.

Audit (today): all downstream consumers of net_gex are sign-only checks
(regime classification, expansion_probability branch, structural manipulation
gate). No magnitude thresholds exist. Therefore unit conversion is
non-disruptive — gates continue to work identically; only display/audit
values change to operationally meaningful Crore.

Three files, three identical-style edits:
  1. compute_gamma_metrics_local.py — line 120 (already carries TD-NEW-2 A+B)
  2. replay/replay_compute_gamma_metrics.py — line 88
  3. backfill_gamma_metrics.py — line 83 (no spaces around operators)

Pattern: writes _PRE_TD-NEW-3.py backup, then _PATCHED.py for inspection.
Operator manually renames after verification.

Per CLAUDE.md: BOM-safe read, EOL preservation, ast.parse validation.
"""

from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Targets — three writer files, each with one exact-match edit
# ---------------------------------------------------------------------------

class PatchTarget(NamedTuple):
    source: Path
    backup: Path
    patched: Path
    label: str
    old_str: str
    new_str: str


TARGETS = [
    PatchTarget(
        source=Path(r"C:\GammaEnginePython\compute_gamma_metrics_local.py"),
        backup=Path(r"C:\GammaEnginePython\compute_gamma_metrics_local_PRE_TD-NEW-3.py"),
        patched=Path(r"C:\GammaEnginePython\compute_gamma_metrics_local_PATCHED.py"),
        label="compute_gamma_metrics_local.py (live writer)",
        old_str="    base = gamma * oi * (spot ** 2)",
        new_str="    base = gamma * oi * (spot ** 2) / 1e7  # TD-NEW-3: store in Crore",
    ),
    PatchTarget(
        source=Path(r"C:\GammaEnginePython\replay\replay_compute_gamma_metrics.py"),
        backup=Path(r"C:\GammaEnginePython\replay\replay_compute_gamma_metrics_PRE_TD-NEW-3.py"),
        patched=Path(r"C:\GammaEnginePython\replay\replay_compute_gamma_metrics_PATCHED.py"),
        label="replay/replay_compute_gamma_metrics.py (replay writer)",
        old_str="    base = gamma * oi * (spot ** 2)",
        new_str="    base = gamma * oi * (spot ** 2) / 1e7  # TD-NEW-3: store in Crore",
    ),
    PatchTarget(
        source=Path(r"C:\GammaEnginePython\backfill_gamma_metrics.py"),
        backup=Path(r"C:\GammaEnginePython\backfill_gamma_metrics_PRE_TD-NEW-3.py"),
        patched=Path(r"C:\GammaEnginePython\backfill_gamma_metrics_PATCHED.py"),
        label="backfill_gamma_metrics.py (historical writer)",
        old_str="    base=gamma*oi*(spot**2)",
        new_str="    base=gamma*oi*(spot**2)/1e7  # TD-NEW-3: store in Crore",
    ),
]


# ---------------------------------------------------------------------------
# IO helpers — BOM-safe, EOL-preserving
# ---------------------------------------------------------------------------

def read_source(path: Path) -> tuple[str, str]:
    """Return (text_lf_normalized, predominant_eol)."""
    if not path.exists():
        raise FileNotFoundError(f"Source not found: {path}")
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    eol = "\r\n" if crlf > lf else "\n"
    text_lf = text.replace("\r\n", "\n")
    return text_lf, eol


def write_with_eol(path: Path, text_lf: str, eol: str) -> None:
    final = text_lf.replace("\n", eol) if eol != "\n" else text_lf
    path.write_bytes(final.encode("utf-8"))


def apply_single_edit(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        raise RuntimeError(f"{label}: pattern not found. Source drifted?")
    if count > 1:
        raise RuntimeError(f"{label}: pattern matched {count} times, expected 1.")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Per-file patch
# ---------------------------------------------------------------------------

def patch_one(target: PatchTarget) -> bool:
    print(f"\n[TD-NEW-3] {target.label}")
    if not target.source.exists():
        print(f"  ERROR: source missing: {target.source}", file=sys.stderr)
        return False

    text_lf, eol = read_source(target.source)
    eol_label = "CRLF" if eol == "\r\n" else "LF"
    print(f"  Read {len(text_lf):,} chars, EOL={eol_label}")

    try:
        patched_text = apply_single_edit(text_lf, target.old_str, target.new_str, target.label)
        print("  Edit applied: +/1e7 Crore conversion")
    except RuntimeError as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return False

    # ast.parse self-validation
    try:
        ast.parse(patched_text, filename=str(target.patched))
        print("  ast.parse OK")
    except SyntaxError as exc:
        print(f"  ERROR: patched source fails ast.parse: {exc}", file=sys.stderr)
        return False

    # Backup (preserve first canonical backup if already present)
    if not target.backup.exists():
        shutil.copy2(target.source, target.backup)
        print(f"  Backup: {target.backup.name}")
    else:
        print(f"  Backup already exists, preserved: {target.backup.name}")

    # Write patched
    write_with_eol(target.patched, patched_text, eol)
    print(f"  Patched: {target.patched.name}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("TD-NEW-3 patch: net_gex unit standardisation to Crore")
    print("=" * 64)

    results = [patch_one(t) for t in TARGETS]
    if not all(results):
        print("\nERROR: one or more patches failed. Inspect output above.",
              file=sys.stderr)
        return 3

    print()
    print("=" * 64)
    print("All three files patched successfully.")
    print()
    print("Next steps:")
    print("  1. Inspect diffs (optional):")
    for t in TARGETS:
        print(f"       fc {t.source.name} {t.patched.name}")
    print("  2. Run verification:  python verify_td_new_3_net_gex_unit.py")
    print("  3. If verification OK, rename PATCHED -> canonical for each file:")
    for t in TARGETS:
        print(f"       del {t.source.name} && ren {t.patched.name} {t.source.name}")
    print("  4. Restart supervisor to pick up patched code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
