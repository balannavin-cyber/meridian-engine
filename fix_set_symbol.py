"""
fix_set_symbol.py — one-shot patcher that inserts ExecutionLog.set_symbol()
into core/execution_log.py at the correct indentation.

Rationale: the ExecutionLog class uses 4-space indentation for method bodies.
Manual paste of the patch text landed at the wrong column (IndentationError at
`def set_symbol` line 187). This script:

  1. Reads core/execution_log.py
  2. Checks whether set_symbol is already present (idempotent no-op if so)
  3. Finds the end of the record_write() method
  4. Inserts a correctly-indented set_symbol() definition after it
  5. ast.parse validates the patched source before writing
  6. Writes only if validation passes

Usage:
    python fix_set_symbol.py

Governance: conforms to V18H rule `patch_script_syntax_validation` -- all
fix_*.py scripts must end with ast.parse() validation.
"""
from __future__ import annotations

import ast
import shutil
import sys
from pathlib import Path


TARGET = Path("core/execution_log.py")
BACKUP = Path("core/execution_log.py.bak_set_symbol")


# Exact method text as it should appear in the file. Body at 8 spaces
# (class body = 4 spaces, method body = 8 spaces).
NEW_METHOD = '''    def set_symbol(self, symbol: str | None) -> None:
        """
        Update the symbol on this invocation's log row.

        For run_id-contract scripts (compute_gamma_metrics_local.py,
        compute_volatility_metrics_local.py, build_momentum_features_local.py)
        that only discover symbol after the first Supabase read. Best-effort:
        failures are logged to stderr but never raised -- the instrumentation
        layer must not break the calling script.

        Safe to call multiple times. Safe to call with None (no-op).
        Post-finalise calls are silently ignored.
        """
        if self._finalised:
            return
        if symbol is None:
            return
        self.symbol = symbol

        if not _SUPABASE_URL or not _SUPABASE_KEY:
            return

        try:
            r = requests.patch(
                f"{_SUPABASE_URL}/rest/v1/script_execution_log",
                headers=self._headers,
                params={"invocation_id": f"eq.{self.invocation_id}"},
                json={"symbol": symbol},
                timeout=10,
            )
            if r.status_code >= 300:
                self._warn(
                    f"set_symbol PATCH failed: status={r.status_code} "
                    f"body={r.text[:200]}"
                )
        except Exception as e:
            self._warn(f"set_symbol PATCH exception: {e}")

'''


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} not found. Run from C:\\GammaEnginePython", file=sys.stderr)
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Idempotence check
    if "def set_symbol(" in src:
        print("[SKIP] set_symbol already present. No changes made.")
        # Still validate existing file parses, surface problems to operator.
        try:
            ast.parse(src)
            print("[OK] Existing file parses cleanly.")
            return 0
        except SyntaxError as e:
            print(f"[ERROR] Existing file has SyntaxError: {e}", file=sys.stderr)
            print("         Manual paste likely broke indentation. Restore from"
                  " execution_log.py.bak_set_symbol if it exists, or from git.",
                  file=sys.stderr)
            return 1

    # Anchor: find the END of record_write() by locating the next def at
    # the same indent level. We want to insert between the two.
    lines = src.splitlines(keepends=True)

    record_write_idx = None
    for i, line in enumerate(lines):
        if line.startswith("    def record_write("):
            record_write_idx = i
            break

    if record_write_idx is None:
        print("[ERROR] Could not find `    def record_write(` in file.", file=sys.stderr)
        print("         File may have drifted from Session 2 reference. Aborting.",
              file=sys.stderr)
        return 1

    # Find the line that starts the next method at the same indent.
    insert_idx = None
    for j in range(record_write_idx + 1, len(lines)):
        line = lines[j]
        # Next method at class-body indent (4 spaces + def).
        if line.startswith("    def "):
            insert_idx = j
            break

    if insert_idx is None:
        print("[ERROR] Could not find method following record_write(). Aborting.",
              file=sys.stderr)
        return 1

    # Backup the original before touching it.
    shutil.copy2(TARGET, BACKUP)
    print(f"[INFO] Backed up original to {BACKUP}")

    # Splice in the new method.
    patched_lines = lines[:insert_idx] + [NEW_METHOD] + lines[insert_idx:]
    patched_src = "".join(patched_lines)

    # Governance rule: ast.parse validate BEFORE writing.
    try:
        ast.parse(patched_src)
    except SyntaxError as e:
        print(f"[FAIL] Patched source has SyntaxError: {e}", file=sys.stderr)
        print(f"         NOT writing file. Original preserved at {TARGET}.",
              file=sys.stderr)
        print(f"         Backup at {BACKUP} for reference.", file=sys.stderr)
        return 1

    # Also confirm the class has the method as an attribute -- catches
    # cases where ast.parse is happy but the method landed at module scope.
    tree = ast.parse(patched_src)
    found_in_class = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ExecutionLog":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == "set_symbol":
                    found_in_class = True
                    break
    if not found_in_class:
        print("[FAIL] set_symbol parsed OK but is NOT inside ExecutionLog class.",
              file=sys.stderr)
        print(f"         NOT writing file. Backup at {BACKUP}.", file=sys.stderr)
        return 1

    TARGET.write_text(patched_src, encoding="utf-8")
    print(f"[OK] {TARGET} patched. set_symbol inserted after record_write.")
    print(f"[OK] ast.parse passed. Method confirmed inside ExecutionLog class.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
