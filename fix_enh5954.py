"""
MERDIAN ENH-59 + ENH-54 doc patches — Track C, doc-only.

ENH-59 — Add STEP 1.6 (Patch Script Syntax Gate) to Change Protocol.
         Formalizes the already-enforced rule that every fix_*.py patch
         script must ast.parse() its target file before writing.
         Also flips ENH-59 register status PROPOSED → COMPLETE.

ENH-54 — Mark HTF Sweep Reversal Trade Mode as REJECTED in register.
         Experiments 23 / 23b / 23c killed the hypothesis.
         Evidence: Exp 23 17-19% WR on sweep reversal setups.
         This is already established (per resume header
         "DO NOT REOPEN: sweep reversal (ENH-54)"); just updates the
         register to reflect the decision.

Usage:
  python fix_enh5954.py --dry-run     # show deltas, write nothing
  python fix_enh5954.py               # apply
  python fix_enh5954.py --no-backup   # skip .bak files
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


# ----------------------------------------------------------------------
# ENH-59: Change Protocol STEP 1.6 insertion
# ----------------------------------------------------------------------

CP_OLD = """---

### STEP 1.5 — Pre-Commit Sanity (Track A only)

Before committing, confirm all four:

```
☐ No hardcoded Windows paths in files destined for AWS
☐ No print/debug statements left in production code
☐ No .env values hardcoded in any file
☐ File is complete (full replacement, not a fragment)
```

---

### STEP 2 — Commit Format (MANDATORY)
"""


CP_NEW = """---

### STEP 1.5 — Pre-Commit Sanity (Track A only)

Before committing, confirm all four:

```
☐ No hardcoded Windows paths in files destined for AWS
☐ No print/debug statements left in production code
☐ No .env values hardcoded in any file
☐ File is complete (full replacement, not a fragment)
```

---

### STEP 1.6 — Patch Script Syntax Gate (ENH-59) — Track A only

Any `fix_*.py` / `patch_*.py` / `update_*.py` script that rewrites another
.py file on disk MUST validate the result's AST before writing. This is
non-optional.

```
☐ Script reads target file
☐ Script applies edits in memory
☐ Script calls ast.parse(patched_text) BEFORE writing
☐ If SyntaxError: print error to stderr and sys.exit(non-zero) — do NOT write
☐ Script also validates its OWN AST on startup (ast.parse(__file__))
```

**Why:** force_wire_breadth.py (2026-04-16) inserted code at wrong indent
depth. Script exited cleanly; IndentationError surfaced only at next
restart, would have disabled the entire pipeline.

**Reference implementations:** fix_enh6061.py, update_registers_enh5355.py,
fix_runner_indent.py, fix_atm_option_build.py, fix_expiry_lookup.py.

---

### STEP 2 — Commit Format (MANDATORY)
"""


# ----------------------------------------------------------------------
# ENH-59 register entry: PROPOSED → COMPLETE
# ----------------------------------------------------------------------

ENH59_OLD = """### ENH-59: Patch script syntax validation rule

| Field | Detail |
|---|---|
| Status | **PROPOSED -- process rule** (was V18H_v2 OI-13) |
| Added | 2026-04-17 |
| Priority | MEDIUM |
| Trigger | force_wire_breadth.py (2026-04-16 session) inserted a code block at wrong indent depth in run_option_snapshot_intraday_runner.py. Script exited cleanly at market close; IndentationError only surfaced at next session restart, would have disabled the entire pipeline. |
| Rule | Every `fix_*.py` patch script MUST call `ast.parse(target_file.read_text())` before writing the target file. If SyntaxError: print error and `sys.exit(1)`. |
| Build | Add to MERDIAN_Change_Protocol.md as new STEP 1.6 (Patch script syntax gate) at next protocol increment. |
| Applied informally | fix_runner_indent.py (2026-04-17), fix_atm_option_build.py, fix_expiry_lookup.py all already include `ast.parse()` validation. Rule is enforced in practice; formal protocol inclusion pending. |
"""


ENH59_NEW = """### ENH-59: Patch script syntax validation rule

| Field | Detail |
|---|---|
| Status | **COMPLETE** — 2026-04-19 |
| Completed | 2026-04-19 |
| Added | 2026-04-17 |
| Priority | MEDIUM |
| Trigger | force_wire_breadth.py (2026-04-16 session) inserted a code block at wrong indent depth in run_option_snapshot_intraday_runner.py. Script exited cleanly at market close; IndentationError only surfaced at next session restart, would have disabled the entire pipeline. |
| Rule | Every `fix_*.py` / `patch_*.py` / `update_*.py` script MUST call `ast.parse(patched_text)` on the in-memory result before writing the target file. If SyntaxError: print error to stderr and `sys.exit(non-zero)`. Script must also validate its own AST on startup. |
| Resolution | Added to MERDIAN_Change_Protocol_v1.md as STEP 1.6 (Patch Script Syntax Gate). Enforced for all patch scripts from 2026-04-19 forward. |
| Reference implementations | fix_enh6061.py, update_registers_enh5355.py, fix_runner_indent.py, fix_atm_option_build.py, fix_expiry_lookup.py. |
"""


# ----------------------------------------------------------------------
# ENH-54: mark REJECTED
# ----------------------------------------------------------------------

ENH54_OLD = """### ENH-54: HTF Sweep Reversal Trade Mode

| Field | Detail |
|---|---|
| Status | **PROPOSED — experiment required before build** |
| Added | 2026-04-15 |
| Priority | Tier 2 — post Phase 4B stable |
| Gate | Experiment 17 (backtest) must validate edge before any build |
| Depends on | ENH-49 (Phase 4B live), hist_ict_htf_zones (breach-filtered, live) |
"""


ENH54_NEW = """### ENH-54: HTF Sweep Reversal Trade Mode

| Field | Detail |
|---|---|
| Status | **REJECTED** — 2026-04-19 |
| Rejected | 2026-04-19 (closing this session; decided 2026-04-17/18 per V18H_v2) |
| Added | 2026-04-15 |
| Priority | Tier 2 — was post Phase 4B stable |
| Original gate | Experiment 17 (backtest) must validate edge before any build |
| Reason for rejection | Experiments 23 / 23b / 23c (2026-04-17/18 V18H_v2 session) tested sweep reversal across the full year. Baseline 17-19% WR. 23b HTF confluence filter: no lift. 23c quality filter: no lift. Hypothesis rejected. Discretionary trades remain possible (the 2026-04-17 live NIFTY BUY_CE sweep reversal was a manual call), but the pattern does not generalize into an automated signal. |
| Do not revisit without | New evidence and a distinct experimental setup; simple variants already tested. |
| Depends on | ENH-49 (Phase 4B live), hist_ict_htf_zones (breach-filtered, live) |
"""


# ----------------------------------------------------------------------
# Edit machinery
# ----------------------------------------------------------------------

def apply_change_protocol(text: str) -> str:
    if CP_OLD not in text:
        raise RuntimeError(
            "Change Protocol insertion point not found. Expected STEP 1.5 "
            "block followed by STEP 2. File may already be patched or may "
            "have diverged from v1 baseline."
        )
    return text.replace(CP_OLD, CP_NEW, 1)


def apply_enh_register(text: str) -> str:
    if ENH59_OLD not in text:
        raise RuntimeError(
            "ENH-59 register entry (PROPOSED) not found. Already patched or "
            "register has diverged."
        )
    if ENH54_OLD not in text:
        raise RuntimeError(
            "ENH-54 register entry (PROPOSED) not found. Already patched or "
            "register has diverged."
        )
    text = text.replace(ENH59_OLD, ENH59_NEW, 1)
    text = text.replace(ENH54_OLD, ENH54_NEW, 1)
    return text


def process_file(path: Path, transformer, dry_run: bool, backup: bool) -> tuple[int, int]:
    original = path.read_text(encoding="utf-8")
    patched = transformer(original)
    if not dry_run:
        if backup:
            shutil.copy2(path, path.with_suffix(path.suffix + ".pre_enh5954.bak"))
        path.write_text(patched, encoding="utf-8")
    return len(original), len(patched)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--change-protocol",
                    default="docs/operational/MERDIAN_Change_Protocol_v1.md",
                    help="path to Change Protocol")
    ap.add_argument("--enh-register",
                    default="docs/registers/MERDIAN_Enhancement_Register_v7.md",
                    help="path to Enhancement Register")
    ap.add_argument("--dry-run", action="store_true",
                    help="show deltas, write nothing")
    ap.add_argument("--no-backup", action="store_true",
                    help="skip .bak files")
    args = ap.parse_args()

    # ENH-59 self-compliance: validate our own AST
    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax check: {e}", file=sys.stderr)
        return 1

    cp = Path(args.change_protocol)
    er = Path(args.enh_register)

    # If default CP path doesn't exist, try project root as fallback
    if not cp.exists():
        fallback = Path("MERDIAN_Change_Protocol_v1.md")
        if fallback.exists():
            cp = fallback

    for p, label in ((cp, "Change Protocol"), (er, "Enhancement Register")):
        if not p.exists():
            print(f"FAIL: {label} not found: {p.resolve()}", file=sys.stderr)
            return 2

    print(f"Change Protocol:       {cp.resolve()}")
    print(f"Enhancement Register:  {er.resolve()}")
    print(f"mode:                  {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backups:               {'off' if args.no_backup else 'on'}")
    print()

    try:
        cp_before, cp_after = process_file(cp, apply_change_protocol,
                                           args.dry_run, not args.no_backup)
        er_before, er_after = process_file(er, apply_enh_register,
                                           args.dry_run, not args.no_backup)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 3

    print(f"Change Protocol:       {cp_before:>6} → {cp_after:>6} bytes  (+{cp_after-cp_before})")
    print(f"Enhancement Register:  {er_before:>6} → {er_after:>6} bytes  (+{er_after-er_before})")
    print()
    print("Edits:")
    print("  [ENH-59] Added STEP 1.6 (Patch Script Syntax Gate) to Change Protocol")
    print("  [ENH-59] Register status: PROPOSED → COMPLETE")
    print("  [ENH-54] Register status: PROPOSED → REJECTED")

    # Post-patch verification (on the already-written or in-memory patched text)
    if not args.dry_run:
        er_final = er.read_text(encoding="utf-8")
        for marker, label in [
            ("STEP 1.6 — Patch Script Syntax Gate (ENH-59)", "STEP 1.6 present in CP"),
            ("**COMPLETE** — 2026-04-19", "ENH-59 marked COMPLETE"),
            ("**REJECTED** — 2026-04-19", "ENH-54 marked REJECTED"),
        ]:
            source = cp.read_text(encoding="utf-8") + er_final
            if marker in source:
                print(f"  [OK] {label}")
            else:
                print(f"  [FAIL] {label}", file=sys.stderr)
                return 4

    if args.dry_run:
        print()
        print("DRY RUN — nothing written. Re-run without --dry-run to apply.")
    else:
        print()
        print("APPLIED.")
        if not args.no_backup:
            print(f"Backups: {cp.name}.pre_enh5954.bak, {er.name}.pre_enh5954.bak")

    return 0


if __name__ == "__main__":
    sys.exit(main())
