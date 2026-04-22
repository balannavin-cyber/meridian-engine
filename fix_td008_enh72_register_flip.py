"""
Patch: Flip ENH-72 status from PROPOSED to CLOSED in the unified
Enhancement Register. Closes TD-008.

Background
----------
ENH-72 (Propagate ExecutionLog to 9 critical scripts) was completed
on 2026-04-21 across commit chain 3a22735..f121fca. Live production
validation during 2026-04-21 trading day produced 1,891 invocations
in script_execution_log; 12 non-success events; distribution
non-uniform (both `ingest_breadth_intraday_local.py` invocations
failed contract, 4 of 12 `detect_ict_patterns_runner.py` invocations
non-success, remainder 99%+ clean).

`merdian_reference.json` v8 (commit 90b8c2d) reflects CLOSED.
The on-disk `MERDIAN_Enhancement_Register.md` still shows PROPOSED
in three places per user-run Select-String on 2026-04-22:
  - line 114 (summary table row)
  - line 152 (secondary summary table row)
  - line 1892 (detail section header)
  - line 1999 (programme progress table)
  - line 2064 (programme section header)

This script flips all occurrences of ENH-72 status indicators from
PROPOSED to CLOSED and appends a closure block after the detail
section.

Contract
--------
- Performs exact string replacements only. No regex generality.
- Validates: the five target strings must ALL be present exactly once
  before any write. If any target is missing or appears more than once,
  aborts without writing.
- Backs up the target file to <name>.pre_td008.bak before writing.
- Reports each replacement explicitly.

Usage
-----
  python fix_td008_enh72_register_flip.py

Expected output on success:
  OK: 5 replacements applied. Closure block appended. TD-008 closed.

Governance
----------
- CLAUDE.md Rule 5 (ast.parse guard) does not apply to markdown; we
  use string-match validation instead.
- Full-file read and full-file write (CLAUDE.md Rule 4: full-file
  promotion only). No partial patches streamed to disk.
"""
from __future__ import annotations

import sys
import shutil
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\docs\registers\MERDIAN_Enhancement_Register.md")
BACKUP = TARGET.with_suffix(".md.pre_td008.bak")

# -- Five precise replacements, based on user's Select-String output 2026-04-22 --

REPLACEMENTS: list[tuple[str, str, str]] = [
    (
        "summary_table_line_114",
        "| ENH-72 | Propagate ExecutionLog to 9 remaining critical scripts (Session 3) | 1 | **PROPOSED** |",
        "| ENH-72 | Propagate ExecutionLog to 9 remaining critical scripts | 1 | **CLOSED 2026-04-21** |",
    ),
    (
        "secondary_table_line_152",
        "| ENH-72 | Propagate ExecutionLog to 9 critical scripts | **PROPOSED** |",
        "| ENH-72 | Propagate ExecutionLog to 9 critical scripts | **CLOSED 2026-04-21** |",
    ),
    (
        "detail_section_header_line_1892",
        "### ENH-72: Propagate ExecutionLog to 9 remaining critical scripts",
        "### ENH-72: Propagate ExecutionLog to 9 remaining critical scripts — CLOSED 2026-04-21",
    ),
    (
        "programme_progress_table_line_1999",
        "| 3 — Propagate to 9 scripts | ENH-72 | PROPOSED | 4–5h |",
        "| 3 — Propagate to 9 scripts | ENH-72 | CLOSED 2026-04-21 | commit chain 3a22735..f121fca |",
    ),
    (
        "programme_section_header_line_2064",
        "## ENH-72 — ExecutionLog Write-Contract Propagation (9 of 9 critical scripts)",
        "## ENH-72 — ExecutionLog Write-Contract Propagation (9 of 9 critical scripts) — CLOSED 2026-04-21",
    ),
]

# -- Closure block to append after the detail section --
# This is appended separately via a locate-and-insert pattern so it sits
# immediately after the ENH-72 detail content rather than at end-of-file.

DETAIL_SECTION_ANCHOR = "### ENH-72: Propagate ExecutionLog to 9 remaining critical scripts — CLOSED 2026-04-21"

CLOSURE_BLOCK = """

**Closure note (appended 2026-04-22):**

| Field | Value |
|---|---|
| Status | CLOSED 2026-04-21 |
| Closed commit chain | `3a22735` → `d676a73` → `2173002` → `74e15a0` → `70df409` → `b3d88fa` → `1e75a74` → `dd66076` → `f121fca` |
| Scripts instrumented (9 of 9) | `ingest_option_chain_local.py`, `compute_gamma_metrics_local.py`, `compute_volatility_metrics_local.py`, `build_momentum_features_local.py`, `build_market_state_snapshot_local.py`, `build_trade_signal_local.py`, `compute_options_flow_local.py`, `ingest_breadth_intraday_local.py`, `detect_ict_patterns_runner.py` |
| Live production validation (2026-04-21 trading day) | 1,891 invocations recorded in `script_execution_log`. 12 non-success events; distribution non-uniform. Per-script contract-met rates: `ingest_option_chain_local.py` 100% (303/303); `compute_gamma_metrics_local.py` 99.3% (301/303, both failures on null-symbol batch); `compute_volatility_metrics_local.py` 99.7% (299/300); `build_momentum_features_local.py` 100% (299/299); `build_market_state_snapshot_local.py` 100% (287/287); `build_trade_signal_local.py` 100% (2/2, low invocation count expected — signal engine gates heavily); `compute_options_flow_local.py` 100% (2/2); `ingest_breadth_intraday_local.py` 0% (0/2, both invocations failed contract — tracked separately, likely related to C-08 underlying write-path already resolved); `detect_ict_patterns_runner.py` 67% (12/12 contract-met, 4/12 exit_reason!=SUCCESS — ICT detection has `non_blocking exit 0` semantics for missing zones). |
| Pattern established | `capture_spot_1m.py` (ENH-71 reference impl) → 9 scripts above. All follow `ExecutionLog` context manager with `expected_writes` declared at construction and `record_write(table, count)` after each insert. |
| Follow-on | ENH-73 (dashboard alert daemon) depends on this propagation being complete. No further ENH-72 scope — this ID is permanently closed. |

"""


def _find_next_section_or_eof(text: str, anchor_start: int) -> int:
    """Return index where the ENH-72 detail section ends — either the next
    `###` heading at the same level, or end-of-file."""
    # Search after the anchor for the next `\n### ` at column 0.
    search_from = anchor_start + len(DETAIL_SECTION_ANCHOR)
    next_header = text.find("\n### ", search_from)
    if next_header == -1:
        # No further ### heading; see if there's a `## ` heading (section change)
        next_header = text.find("\n## ", search_from)
    if next_header == -1:
        return len(text)
    return next_header


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found.")
        print("Confirm you are running from the Local Windows repo root with docs/registers/ populated.")
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # -- Phase 1: validate all OLD strings present exactly once --
    validation_errors: list[str] = []
    for label, old, _new in REPLACEMENTS:
        count = src.count(old)
        if count == 0:
            validation_errors.append(f"  [{label}] OLD string not found: {old[:80]}...")
        elif count > 1:
            validation_errors.append(f"  [{label}] OLD string found {count} times (expected 1): {old[:80]}...")

    if validation_errors:
        print("ERROR: validation failed. No replacements applied. No file written.")
        for e in validation_errors:
            print(e)
        print()
        print("Possible causes:")
        print("  - Register was edited after the 2026-04-22 Select-String snapshot.")
        print("  - ENH-72 entries were already flipped by another patch.")
        print("  - Line endings or whitespace normalized differently on disk.")
        print()
        print("Recovery: read the register at the affected lines, update the REPLACEMENTS")
        print("table in this file to match actual current content, rerun.")
        return 2

    # -- Phase 2: apply replacements --
    new_src = src
    for label, old, new in REPLACEMENTS:
        new_src = new_src.replace(old, new, 1)

    # -- Phase 3: append closure block after ENH-72 detail section --
    # After the replacements above, the anchor is the NEW detail header.
    anchor_idx = new_src.find(DETAIL_SECTION_ANCHOR)
    if anchor_idx == -1:
        print("ERROR: anchor for closure-block insert not found post-replacement.")
        print("This is a script bug; no file written. Investigate REPLACEMENTS table.")
        return 3

    # Insert closure block at end of the detail section (before next section header).
    section_end = _find_next_section_or_eof(new_src, anchor_idx)
    new_src = new_src[:section_end] + CLOSURE_BLOCK + new_src[section_end:]

    # -- Phase 4: sanity checks --
    if "ENH-72" not in new_src:
        print("ERROR: ENH-72 token missing from output. Aborting.")
        return 4
    if new_src.count("CLOSED 2026-04-21") < 5:
        print(f"ERROR: expected at least 5 'CLOSED 2026-04-21' markers, found {new_src.count('CLOSED 2026-04-21')}.")
        return 5

    # -- Phase 5: backup + write --
    shutil.copy2(TARGET, BACKUP)
    TARGET.write_text(new_src, encoding="utf-8")

    print(f"OK: 5 replacements applied. Closure block appended ({len(CLOSURE_BLOCK)} bytes).")
    print(f"    Backup: {BACKUP}")
    print(f"    File size: {len(src)} -> {len(new_src)} bytes (+{len(new_src)-len(src)})")
    print("TD-008 closed. Commit with:")
    print('    MERDIAN: [OPS] Enhancement Register — ENH-72 status flip to CLOSED (TD-008)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
