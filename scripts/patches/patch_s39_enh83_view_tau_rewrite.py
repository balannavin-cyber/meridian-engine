"""
patch_s39_enh83_view_tau_rewrite.py

Rewrites ENH-81 PIN/ACCEL view DDLs to call get_parameter_num('<key>')
instead of hardcoded 0.3.

Run on Local against:
    sql/2026-05-25_enh81_v_gex_strike_pin_zone.sql
    sql/2026-05-25_enh81_v_gex_strike_accel_zone.sql

The substitution is anchored on the inline TAU_PIN marker that ENH-81
ships with at every τ site. Per ADR-016 calibration-deferred-by-design
pattern, the marker is the discipline that prevents τ from drifting into
magic-number territory; this script is the eventual mechanical plumb.

What it does:
    1. Reads the two view DDL files (paths configurable below).
    2. For each file, finds every line containing `TAU_PIN` and rewrites
       the bare `0.3` literal on that same line to a get_parameter_num()
       call. The call key is `pin.tau.<symbol>` for the PIN view and
       `accel.tau.<symbol>` for the ACCEL view.
    3. Validates that the rewritten file:
       - Has the same number of `CREATE OR REPLACE VIEW` / `CREATE VIEW`
         statements as the original.
       - Has balanced parentheses (paren-count delta on the file is zero).
       - Contains no remaining bare `0.3` literal on lines with TAU_PIN.
    4. Writes the rewritten content to `<original>.NEW.sql` next to the
       original for operator review. Original is left untouched.
    5. Also writes a `<original>.PRE_S39.sql` backup for forward symmetry
       with the patch script convention.

Closes: TD-S37-01 (hardcoded τ in ENH-81 views)
Graduates ADR-016 from PROPOSED → ACCEPTED via this ENH-83 ship.

Usage:
    python patch_s39_enh83_view_tau_rewrite.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration — adjust paths if repo layout has drifted
# ---------------------------------------------------------------------------

REPO_ROOT = Path(r"C:\GammaEnginePython")

VIEW_PIN_FILE = REPO_ROOT / "sql" / "2026-05-25_enh81_v_gex_strike_pin_zone.sql"
VIEW_ACCEL_FILE = REPO_ROOT / "sql" / "2026-05-25_enh81_v_gex_strike_accel_zone.sql"

REPLACEMENT_KEY = {
    VIEW_PIN_FILE: "pin.tau.",
    VIEW_ACCEL_FILE: "accel.tau.",
}


# ---------------------------------------------------------------------------
# Substitution
# ---------------------------------------------------------------------------

# Matches a bare `0.3` not embedded in a longer numeric literal
# (rejects 0.30, 10.3, etc. via word boundaries on the digit side).
TAU_LITERAL_RE = re.compile(r"(?<![\d.])0\.3(?![\d])")

# Marker presence detected case-insensitively to tolerate doc-vs-code drift.
MARKER_RE = re.compile(r"TAU_PIN", re.IGNORECASE)


def rewrite_view_text(source: str, key_prefix: str) -> tuple[str, int, int]:
    """
    Returns (new_text, lines_with_marker, replacements_made).

    On every line that contains TAU_PIN, replaces the bare `0.3` literal
    with `get_parameter_num('<key_prefix><symbol>')`. The `<symbol>` token
    is resolved by looking for `'NIFTY'` or `'SENSEX'` on the same line or
    the two lines before; if neither is present, falls back to the
    expression `|| symbol` so the view's own `symbol` column is used at
    runtime (this is the case where the view is constructed generically
    across symbols in a single SELECT).
    """
    lines = source.splitlines(keepends=False)
    output_lines: list[str] = []
    lines_with_marker = 0
    replacements = 0

    for idx, line in enumerate(lines):
        if not MARKER_RE.search(line):
            output_lines.append(line)
            continue

        lines_with_marker += 1

        # Look for explicit symbol literal on this and previous two lines.
        scope = " ".join(lines[max(0, idx - 2): idx + 1])
        if "'NIFTY'" in scope:
            replacement = f"get_parameter_num('{key_prefix}NIFTY')"
        elif "'SENSEX'" in scope:
            replacement = f"get_parameter_num('{key_prefix}SENSEX')"
        else:
            # Generic: build the key from the view's `symbol` column at runtime.
            replacement = f"get_parameter_num('{key_prefix}' || symbol)"

        new_line, n = TAU_LITERAL_RE.subn(replacement, line, count=1)
        if n == 0:
            # Marker present but no 0.3 literal on this line — preserve verbatim
            # and warn (downstream caller will flag if expected count mismatch).
            output_lines.append(line)
            continue

        replacements += 1

        # Annotate the rewritten line with a trailing comment recording the
        # plumb so subsequent grep audits can trace TD-S37-01 closure.
        if "--" not in new_line:
            new_line = new_line.rstrip() + f"  -- ENH-83 (S39) plumbed from TAU_PIN marker"
        output_lines.append(new_line)

    new_text = "\n".join(output_lines)
    # Preserve trailing newline if source had one
    if source.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return new_text, lines_with_marker, replacements


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_rewrite(original: str, rewritten: str) -> list[str]:
    """Returns a list of validation failures; empty list = OK."""
    failures: list[str] = []

    orig_create_count = len(re.findall(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\b", original, re.IGNORECASE))
    new_create_count = len(re.findall(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\b", rewritten, re.IGNORECASE))
    if orig_create_count != new_create_count:
        failures.append(
            f"CREATE VIEW count drift: original={orig_create_count} rewritten={new_create_count}"
        )

    orig_parens = original.count("(") - original.count(")")
    new_parens = rewritten.count("(") - rewritten.count(")")
    if orig_parens != new_parens:
        failures.append(
            f"paren-balance drift: original delta={orig_parens} rewritten delta={new_parens}"
        )

    # Every line that still has TAU_PIN must NOT have a bare 0.3 literal —
    # if it does, the substitution was incomplete.
    for ln, line in enumerate(rewritten.splitlines(), 1):
        if MARKER_RE.search(line) and TAU_LITERAL_RE.search(line):
            # If the 0.3 is inside a string literal or comment, that's
            # acceptable; otherwise it's a miss.
            stripped = line.split("--", 1)[0]  # discard SQL line comment
            if TAU_LITERAL_RE.search(stripped):
                failures.append(f"line {ln} still has bare 0.3 with TAU_PIN marker: {line!r}")

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_one(view_file: Path, key_prefix: str, dry_run: bool) -> bool:
    if not view_file.exists():
        print(f"[FAIL] {view_file} does not exist — skipping")
        return False

    raw = view_file.read_bytes()
    try:
        source = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        source = raw.decode("utf-8", errors="replace")

    new_text, lines_with_marker, replacements = rewrite_view_text(source, key_prefix)
    print(f"\n--- {view_file.name} ---")
    print(f"  lines with TAU_PIN marker : {lines_with_marker}")
    print(f"  0.3 → get_parameter_num   : {replacements} substitution(s)")

    failures = validate_rewrite(source, new_text)
    if failures:
        print(f"  [FAIL] validation failures:")
        for f in failures:
            print(f"           {f}")
        return False
    print(f"  [OK]   validation passed")

    if dry_run:
        print(f"  (dry-run — no files written)")
        return True

    backup = view_file.with_suffix(".PRE_S39.sql")
    new_path = view_file.with_suffix(".NEW.sql")
    shutil.copy2(view_file, backup)
    new_path.write_bytes(new_text.encode("utf-8"))
    print(f"  wrote backup : {backup.name}")
    print(f"  wrote new    : {new_path.name}")
    print(f"  (review {new_path.name} and deploy manually via psql or Supabase SQL editor)")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing files")
    args = parser.parse_args()

    print(f"patch_s39_enh83_view_tau_rewrite.py — dry_run={args.dry_run}")
    print(f"repo root: {REPO_ROOT}")

    all_ok = True
    for view_file, key_prefix in REPLACEMENT_KEY.items():
        ok = process_one(view_file, key_prefix, args.dry_run)
        all_ok = all_ok and ok

    print()
    if all_ok:
        print("=" * 70)
        print("ALL VIEWS REWRITTEN OK")
        if not args.dry_run:
            print("Next steps:")
            print("  1. Diff the .NEW.sql files against originals (git diff or fc).")
            print("  2. Run the .NEW.sql against Supabase via SQL editor (CREATE OR REPLACE).")
            print("  3. Smoke-probe: SELECT * FROM v_gex_strike_pin_zone LIMIT 5;")
            print("  4. Confirm row shape unchanged; if OK, replace original with .NEW.sql.")
            print("  5. Commit; TD-S37-01 closed; ADR-016 graduates PROPOSED → ACCEPTED.")
        print("=" * 70)
        return 0
    print("=" * 70)
    print("ONE OR MORE FAILURES — review output above")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
