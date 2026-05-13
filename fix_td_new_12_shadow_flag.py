"""
fix_td_new_12_shadow_flag.py — S28 TD-NEW-12 patch

Defect:
  AWS-side `compute_gamma_metrics_local.py` writes to production
  `gamma_metrics` table instead of `gamma_metrics_shadow`. The shadow
  table exists in Supabase but has been empty since deployment because
  the script hardcodes the target table name. Result: AWS shadow
  runner double-writes the same (symbol, ts) row that Local writes,
  with UPSERT race condition determining which value persists.
  `evaluate_shadow_vs_live.py` (per Topology §6.5) has been silently
  broken — comparing populated `gamma_metrics` against empty
  `gamma_metrics_shadow` returns no meaningful evaluation.

Surfaced:
  Session 28 2026-05-12, while investigating TD-080 (failed to reproduce
  today). The `gamma_metrics_shadow` count-rows-today query returned 0,
  but AWS-side `compute_gamma_metrics_local.py` ran cleanly 75x per
  symbol per day with `actual_writes: {"gamma_metrics": 1}` in
  script_execution_log. Cross-checked: AWS shadow runner invocation at
  line 479 of `run_merdian_shadow_runner.py` passes no flag; script
  hardcodes `SUPABASE.table("gamma_metrics")` at lines 495 + 768.

Severity:
  S2 — data integrity preserved (idempotent UPSERT, same code both
  sides at cf66fa9), but architectural invariant violated. Becomes S1
  the moment Local and AWS diverge in code or behavior.

Fix:
  Add `--shadow` flag handling at module level (before parse_args).
  Substitute hardcoded "gamma_metrics" string with TARGET_TABLE
  variable at three sites:
    1. fetch_prior_gamma_metrics SELECT (~line 495)
    2. upsert_gamma_metrics UPSERT  (~line 768)
    3. ExecutionLog expected_writes dict literal (~line 853)
  Optionally also: record_write() instrumentation calls.

Canonical patch pattern (matches S27 TD-NEW-2 + TD-NEW-3):
  - BOM-safe read via read_bytes() + decode('utf-8-sig')
  - EOL detection + preservation on write
  - ast.parse() self-validation before write
  - _PRE_TD-NEW-12.py backup (refuse overwrite if exists)
  - _PATCHED.py output (operator renames to canonical after diff review)
  - Idempotency guards on each substitution
  - Verification pass: list any remaining `"gamma_metrics"` literal
    occurrences for operator review
"""

import ast
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "compute_gamma_metrics_local.py"


# ====================================================================
# Insertion: TARGET_TABLE block before parse_args definition.
# Anchor on exact parse_args signature (confirmed via inspect.getsource
# in S28 — single match in file).
# ====================================================================

OLD_PARSE_ARGS_ANCHOR = "def parse_args(argv: list[str]) -> tuple[str, Optional[str], str]:"

NEW_INSERTION_BEFORE = """# TD-NEW-12 (S28): shadow-vs-live table separation.
# AWS shadow runner passes --shadow to redirect writes to gamma_metrics_shadow.
# Local invocations omit it and write to gamma_metrics.
# Reads (fetch_prior_gamma_metrics) ALSO redirected — shadow pipeline reads its own history.
USE_SHADOW = "--shadow" in sys.argv
if USE_SHADOW:
    sys.argv = [a for a in sys.argv if a != "--shadow"]
TARGET_TABLE = "gamma_metrics_shadow" if USE_SHADOW else "gamma_metrics"


def parse_args(argv: list[str]) -> tuple[str, Optional[str], str]:"""


# ====================================================================
# Substitutions: literal "gamma_metrics" -> TARGET_TABLE at production sites.
# Each substitution is exact-match and idempotent-guarded.
# ====================================================================

SUBSTITUTIONS = [
    # SELECT site (fetch_prior_gamma_metrics + any other reads)
    ('SUPABASE.table("gamma_metrics")', 'SUPABASE.table(TARGET_TABLE)'),
    # ExecutionLog expected_writes dict literal
    ('expected_writes={"gamma_metrics": 1}', 'expected_writes={TARGET_TABLE: 1}'),
    # ExecutionLog record_write() instrumentation
    ('record_write("gamma_metrics",', 'record_write(TARGET_TABLE,'),
]


def main():
    if not TARGET.exists():
        sys.exit(f"FATAL: {TARGET} not found. Run from C:\\GammaEnginePython\\.")

    raw = TARGET.read_bytes()
    text = raw.decode("utf-8-sig")

    # --- Detect EOL convention (preserve on write) ---
    crlf_count = raw.count(b"\r\n")
    lf_only = raw.count(b"\n") - crlf_count
    eol = "\r\n" if crlf_count > lf_only else "\n"

    # --- Normalize to LF for matching ---
    text_lf = text.replace("\r\n", "\n")

    # --- Idempotency guard ---
    if "USE_SHADOW" in text_lf or "TARGET_TABLE" in text_lf:
        sys.exit("ALREADY PATCHED: USE_SHADOW / TARGET_TABLE already present. Aborting.")

    # --- Anchor presence + uniqueness check for insertion ---
    if OLD_PARSE_ARGS_ANCHOR not in text_lf:
        sys.exit("FATAL: parse_args signature anchor not found. File may have drifted.")
    if text_lf.count(OLD_PARSE_ARGS_ANCHOR) > 1:
        sys.exit("FATAL: multiple matches for parse_args signature.")

    # --- Apply insertion ---
    text_new = text_lf.replace(OLD_PARSE_ARGS_ANCHOR, NEW_INSERTION_BEFORE, 1)

    # --- Apply substitutions ---
    substitution_counts = []
    for old, new in SUBSTITUTIONS:
        count = text_new.count(old)
        substitution_counts.append((old, count))
        if count == 0:
            print(f"WARN: substitution OLD pattern not found (may be optional): {old!r}")
            continue
        text_new = text_new.replace(old, new)

    # --- AST validate ---
    try:
        ast.parse(text_new)
    except SyntaxError as e:
        sys.exit(f"AST PARSE FAILED: {e}")

    # --- Backup BEFORE writing PATCHED ---
    backup = TARGET.with_name(TARGET.stem + "_PRE_TD-NEW-12.py")
    if backup.exists():
        sys.exit(f"REFUSING to overwrite existing backup {backup.name}")
    backup.write_bytes(raw)

    # --- Restore EOL on write ---
    text_out = text_new.replace("\n", eol) if eol == "\r\n" else text_new
    out = TARGET.with_name(TARGET.stem + "_PATCHED.py")
    out.write_bytes(text_out.encode("utf-8"))

    print(f"OK: backup       -> {backup.name}")
    print(f"OK: patched      -> {out.name}")
    print(f"EOL preserved    -> {'CRLF' if eol == chr(13) + chr(10) else 'LF'}")
    print()
    print("Substitution counts:")
    for old, count in substitution_counts:
        print(f"  {count}x  {old[:60]!r}{'...' if len(old) > 60 else ''}")
    print()

    # --- Verification: remaining literal "gamma_metrics" occurrences ---
    print("Remaining \"gamma_metrics\" literal occurrences in PATCHED (for operator review):")
    for i, line in enumerate(text_out.splitlines(), 1):
        if '"gamma_metrics"' in line and "gamma_metrics_shadow" not in line and "TARGET_TABLE" not in line:
            print(f"  L{i}: {line.strip()[:100]}")
    print()
    print("Above lines are docstrings, comments, or string-literal references that may be intentional.")
    print("Review and decide if any need conversion to TARGET_TABLE.")
    print()
    print("Next steps:")
    print(f"  1. Review diff:")
    print(f"       fc.exe /T compute_gamma_metrics_local.py compute_gamma_metrics_local_PATCHED.py")
    print(f"     OR")
    print(f"       git diff --no-index compute_gamma_metrics_local.py compute_gamma_metrics_local_PATCHED.py")
    print(f"  2. Promote to canonical:")
    print(f"       Move-Item -Force compute_gamma_metrics_local_PATCHED.py compute_gamma_metrics_local.py")
    print(f"  3. Smoke test WITHOUT --shadow (writes to gamma_metrics — Local default):")
    print(f"       python compute_gamma_metrics_local.py <run_id>")
    print(f"       SQL: SELECT * FROM gamma_metrics WHERE run_id = '<run_id>';")
    print(f"  4. Smoke test WITH --shadow (writes to gamma_metrics_shadow — AWS path):")
    print(f"       python compute_gamma_metrics_local.py <run_id> --shadow")
    print(f"       SQL: SELECT * FROM gamma_metrics_shadow WHERE run_id = '<run_id>';")
    print(f"  5. Confirm script_execution_log row for #4 shows actual_writes: {{gamma_metrics_shadow: 1}}")
    print(f"  6. Commit + push. Then edit run_merdian_shadow_runner.py line 479 to append \"--shadow\".")


if __name__ == "__main__":
    main()
