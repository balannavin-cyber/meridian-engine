"""
MERDIAN ENH-63 + ENH-64 register entries — Track C (docs-only).

Appends two new PROPOSED entries to the Enhancement Register, derived from
a cross-check of merdian_all_experiment_results.md and
MERDIAN_Experiment_Compendium_v1.md against existing register coverage.

ENH-63 — IV-scaled lot sizing multiplier in merdian_utils.
         Evidence: Experiment 5 (full year):
           BEAR_OB|HIGH_IV  +174.6% exp, 86% WR (N=22)
           BEAR_OB|MED_IV    +84.8% exp, 100% WR (N=11)
           BULL_FVG|LOW_IV   -14.3% exp,  0% WR (N=23)
         VIX>20 binary gate was already removed (commit annotations
         reference "ENH-35 + Experiment 5"). The intended replacement —
         IV-scaled sizing (0.5× / 1.0× / 1.5× by atm_iv regime) — is
         documented in Signal Rule Book v1.1 and session_log R-01 but
         not in merdian_utils.py nor consumed by the execution layer.

ENH-64 — Pre-pattern sequence features + refinements in ICT detector.
         Combines three findings from Experiments 8 and 10c / Compendium
         tier classification:
         - MOM_YES / IMP_WEK / NO_SWEEP filters elevate tier assignment
           (BEAR_OB|NO_SWEEP|MOM_YES|IMP_WEK +298% exp, 100% WR, N=6).
         - BEAR_OB AFTERNOON (13:00-14:30) hard skip (-24.7% exp, 17% WR).
         - BULL_FVG|LOW_IV downgrade to TIER3 / min sizing (0% WR, N=23).
         All three feed the same tier-classification pipeline.

Usage:
  python fix_enh6364.py --dry-run
  python fix_enh6364.py
  python fix_enh6364.py --no-backup
"""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import sys
from pathlib import Path


ENH63_BLOCK = """\
### ENH-63: IV-scaled lot sizing multiplier

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-19 |
| Priority | HIGH — direct execution-layer edge |
| Evidence | Experiment 5 (full year options P&L): BEAR_OB\\|HIGH_IV +174.6% exp 86% WR (N=22) vs BEAR_OB\\|MED_IV +84.8% exp 100% WR (N=11). BULL_FVG\\|LOW_IV -14.3% exp 0% WR (N=23). BULL_OB\\|HIGH +67.3% vs BULL_OB\\|MED +49.3%. HIGH_IV environments carry MORE edge, not less. |
| Prior context | VIX>20 binary gate was removed (build_trade_signal_local.py line annotation "ENH-35 + Experiment 5"). Intended replacement — IV-scaled lot sizing — is documented in Signal Rule Book v1.1 and session_log R-01 but never built. |
| Build | New helper in `merdian_utils.py`: `iv_size_multiplier(atm_iv: float, pattern: str) -> float`. Returns: atm_iv < 12 → 0.5; 12 ≤ atm_iv < 18 → 1.0; atm_iv ≥ 18 → 1.5. Exception: pattern == 'JUDAS_BULL' → always 1.0 (HIGH_IV degrades Judas edge per Exp 5). Apply in `detect_ict_patterns_runner.py` where `ict_lots_t1/t2/t3` are computed: multiply Kelly lot output by `iv_size_multiplier` then floor to int, min 1. |
| Schema change | None. atm_iv already in market_state_snapshots.volatility_features and signal_snapshots. |
| Flag gate | New env var `MERDIAN_IV_SIZING_V1` (default "0"). Flip to "1" after historical replay validates no regression in ict_zones.ict_lots_* distribution. |
| Validation | Historical replay against ict_zones rows written in last 4 weeks. Compare pre-/post-multiplier lot counts. Expected: 40-50% rows get 1.5× boost (HIGH_IV weeks), 10-15% get 0.5× reduction (LOW_IV periods — rare in current dataset). |
| Risk | If atm_iv is null or zero-ish, multiplier must default to 1.0 (no change). Guard in helper. |
| Depends on | ENH-38 (Kelly tiered sizing — live). |
| Blocks | Live promotion of Candidate A in session 2026-04-19 research handoff. |
"""


ENH64_BLOCK = """\
### ENH-64: Pre-pattern sequence features + afternoon skip + FVG low-IV downgrade

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-19 |
| Priority | MEDIUM-HIGH — tier classifier becomes evidence-driven |
| Scope | Three composable refinements to the ICT tier-classification pipeline. Bundled because all feed `ict_zones.ict_tier` / `ict_size_mult` in `detect_ict_patterns_runner.py`. |
| Sub-rule 1 — Sequence features | Add 3-bar lookback computation in detector. New fields in ict_zones: `seq_mom_yes` (2+ counter-direction bars before OB), `seq_imp_wek` (cumulative preceding impulse < 0.3%), `seq_no_sweep` (no liquidity grab in prior 5 bars). |
| Sub-rule 1 — Evidence | Exp 8: BEAR_OB\\|NO_SWEEP\\|MOM_YES\\|IMP_WEK = +298% exp 100% WR (N=6). BEAR_OB\\|MOM_YES alone +187% (N=10) vs MOM_NO +59% (N=19). BEAR_OB\\|IMP_WEK +132% (N=23) vs IMP_STR -7.4% (N=6). Momentum alignment is the single strongest filter for BEAR_OB (+83.6pp lift). |
| Sub-rule 1 — Tier promotion | If pattern ∈ {BEAR_OB, BULL_OB} AND seq_mom_yes AND seq_imp_wek AND seq_no_sweep → promote to TIER1 regardless of MTF context. If any single sub-feature missing → default MTF tier logic. |
| Sub-rule 1 — Inversion | BULL_FVG: MOM_NO better than MOM_YES (+30% vs +9%). For FVG patterns, INVERT momentum filter. Flag `seq_mom_inverted = True` for FVG. |
| Sub-rule 2 — BEAR_OB afternoon skip | If pattern == BEAR_OB AND detect_ts IST hour ∈ [13, 14] → `ict_tier = SKIP`, `ict_size_mult = 0`. Evidence: BEAR_OB\\|AFTERNOON (13:00-14:30) -24.7% exp 17% WR. Signal Rule Book v1.1 Rule 1 (NEW). |
| Sub-rule 3 — BULL_FVG low-IV downgrade | If pattern == BULL_FVG AND atm_iv < 12 → force `ict_tier = TIER3` (min sizing). Evidence: BULL_FVG\\|LOW 0% WR N=23, -14.3% exp. Compose with ENH-63 multiplier (0.5× TIER3 → effectively minimum viable lot). |
| Schema change | ict_zones +3 nullable columns: seq_mom_yes BOOLEAN, seq_imp_wek BOOLEAN, seq_no_sweep BOOLEAN. Backfill NULL for historical rows — only forward-applied. |
| Flag gate | New env var `MERDIAN_SEQ_TIER_V1` (default "0"). |
| Validation | Historical replay against hist_pattern_signals.signal_v4 = true rows. Compare tier distribution pre-/post-change. Expected: 5-10% of BEAR_OB/BULL_OB rows promote to TIER1 (+300% sizing). 100% of afternoon BEAR_OB rows get SKIP (was TIER3 min). BULL_FVG LOW_IV rows — sparse in live data, cosmetic for now. |
| Depends on | ENH-37 (ICT detector — live), ENH-38 (Kelly sizing — live). |
| Could unblock | Refined Signal Rule Book v2.0 once this and ENH-63 ship. |
"""


# ----------------------------------------------------------------------
# Insertion logic
# ----------------------------------------------------------------------

def apply_patch(text: str) -> str:
    """
    Insert ENH-63 and ENH-64 after the highest-numbered existing ENH-NN
    section. Robust to whether ENH-60/61/62 are already in the file.
    """
    # Find all ENH-NN section headers
    matches = list(re.finditer(r"^### ENH-(\d+):", text, re.MULTILINE))
    if not matches:
        raise RuntimeError("No ENH-NN section headers found in register")

    # Refuse to double-patch
    if "### ENH-63:" in text or "### ENH-64:" in text:
        raise RuntimeError(
            "ENH-63 or ENH-64 already present in register. Refusing to "
            "double-patch."
        )

    # Pick the match with the highest ENH number
    highest = max(matches, key=lambda m: int(m.group(1)))
    highest_id = int(highest.group(1))
    section_start = highest.start()

    # Find the end of this section: either the next "### ENH-" header or
    # the end of file. We want to insert AFTER the whole section, which
    # ends at the next "### ENH-" header OR at a terminator like
    # "*End of v8 section.*" or end-of-file.
    next_header_match = re.search(
        r"\n### ENH-\d+:", text[highest.end():]
    )
    if next_header_match:
        section_end = highest.end() + next_header_match.start() + 1  # +1 keeps the newline
    else:
        # Look for the "*End of v8 section.*" footer or end of file
        footer_match = re.search(r"\n\*End of v\d+ section\.\*", text)
        if footer_match:
            section_end = footer_match.start() + 1
        else:
            section_end = len(text)

    # Insert: "\n---\n\nENH63\n\n---\n\nENH64\n\n---\n\n" right before section_end
    insertion = (
        "\n---\n\n"
        + ENH63_BLOCK.rstrip()
        + "\n\n---\n\n"
        + ENH64_BLOCK.rstrip()
        + "\n\n---\n\n"
    )

    return text[:section_end].rstrip() + "\n\n" + insertion + text[section_end:].lstrip()


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--enh-register",
        default="docs/registers/MERDIAN_Enhancement_Register_v7.md",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    # ENH-59 self-compliance
    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax: {e}", file=sys.stderr)
        return 1

    p = Path(args.enh_register)
    if not p.exists():
        print(f"FAIL: not found: {p.resolve()}", file=sys.stderr)
        return 2

    original = p.read_text(encoding="utf-8")

    try:
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 3

    # Post-patch sanity
    for needle, label in [
        ("### ENH-63: IV-scaled lot sizing multiplier", "ENH-63 header"),
        ("### ENH-64: Pre-pattern sequence features", "ENH-64 header"),
        ("**PROPOSED**", "PROPOSED status markers"),
    ]:
        if needle not in patched:
            print(f"FAIL: post-patch check — {label}", file=sys.stderr)
            return 4

    print(f"target:   {p.resolve()}")
    print(f"mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:   {'off' if args.no_backup else 'on'}")
    print(f"size:     {len(original)} bytes → {len(patched)} bytes "
          f"(+{len(patched)-len(original)})")
    print()
    print("Added:")
    print("  [ENH-63] IV-scaled lot sizing multiplier (PROPOSED)")
    print("  [ENH-64] Pre-pattern sequence features + afternoon skip + FVG low-IV (PROPOSED)")

    if args.dry_run:
        print()
        print("DRY RUN — nothing written.")
        return 0

    if not args.no_backup:
        shutil.copy2(p, p.with_suffix(p.suffix + ".pre_enh6364.bak"))
        print(f"backup:   {p.name}.pre_enh6364.bak")

    p.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
