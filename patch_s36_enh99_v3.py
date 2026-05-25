"""
patch_s36_enh99_v3.py - MERDIAN ENH-99 v3 (regex-anchored RETRY_UTILS only)

v2 outcome: INGEST + JANITOR LIVE-applied successfully. RETRY_UTILS still
            failed with "ANCHOR STILL NOT FOUND" after LF normalization.
            Diagnostic showed file content looks byte-identical to anchor
            in first 400 chars but mismatch exists somewhere later in the
            function body (whitespace drift, non-ASCII char, or similar).

v3 fix:     Switch to regex matching `def retry_call( ... raise RuntimeError(...)`
            spanning the whole function. Doesn't care about internal whitespace
            differences. Replaces entire function body atomically.

Scope:      RETRY_UTILS only. INGEST + JANITOR already shipped via v2 (idempotency
            guards in v2 would have skipped re-application; v3 doesn't touch them).

Pattern:    Same v3 canonical IO helpers from v2 (BOM + LF-normalized + EOL-preserved).
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(r"C:\GammaEnginePython")
RETRY_UTILS = REPO / "gamma_engine_retry_utils.py"

SESSION_TAG = "S36"


def read_text_bom_safe(path: Path) -> tuple[str, str, str]:
    raw = path.read_bytes()
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    text = raw.decode(encoding)
    if b"\r\n" in raw:
        eol = "\r\n"
    elif b"\r" in raw and b"\n" not in raw:
        eol = "\r"
    else:
        eol = "\n"
    text_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    return text_lf, encoding, eol


def write_text_preserve_eol(path: Path, text_lf: str, encoding: str, eol: str) -> None:
    text_out = text_lf.replace("\n", eol) if eol != "\n" else text_lf
    path.write_bytes(text_out.encode(encoding))


def ast_validate(text: str, label: str) -> None:
    try:
        ast.parse(text)
    except SyntaxError as e:
        raise SystemExit(f"[AST FAIL] {label}: {e}")


def backup(path: Path) -> Path:
    backup_path = path.with_name(path.stem + f"_PRE_{SESSION_TAG}" + path.suffix)
    backup_path.write_bytes(path.read_bytes())
    return backup_path


# Regex: match `def retry_call(` through the FIRST `raise RuntimeError(...)` after it.
# DOTALL lets `.*?` span newlines.
# Non-greedy ensures we stop at the first raise, not bleed into other functions.
RETRY_CALL_FUNC_RE = re.compile(
    r"def retry_call\(.*?raise RuntimeError\([^)]*\)",
    re.DOTALL,
)

RETRY_UTILS_NEW_FUNC = '''def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    delay_seconds: float = 5.0,
    backoff_multiplier: float = 1.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    retry_predicate: Callable[[Exception], bool] | None = None,
    label: str = "operation",
) -> T:
    """Retry a callable on exception.

    retry_predicate (ENH-99 S36): optional callable inspecting the exception
    to gate retry. If returns False, the exception re-raises immediately
    without burning remaining retry budget. Used to distinguish transient
    429 rate-limits (retry long) from terminal 401 auth failures (fail fast).
    """
    last_exc = None
    current_delay = delay_seconds
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_exceptions as exc:
            last_exc = exc
            # ENH-99: predicate-gated retry -- bail fast on non-retryable errors
            if retry_predicate is not None and not retry_predicate(exc):
                print(
                    f"[retry_call] {label} failed on attempt {attempt}/{attempts} "
                    f"with error: {exc}. Predicate returned False -- failing fast."
                )
                raise
            if attempt >= attempts:
                break
            print(
                f"[retry_call] {label} failed on attempt {attempt}/{attempts} "
                f"with error: {exc}. Retrying in {current_delay:.1f}s..."
            )
            time.sleep(current_delay)
            current_delay *= backoff_multiplier if backoff_multiplier > 0 else 1.0
    if last_exc is not None:
        # ENH-99: final-failure tag -- daily audit greps for this
        print(
            f"[RETRY_BURN_DOWN] {label} exhausted {attempts} attempts. "
            f"Final exc: {last_exc}"
        )
        raise last_exc
    raise RuntimeError(f"{label} failed unexpectedly without captured exception")'''


def patch_retry_utils(dry_run: bool) -> dict:
    text_lf, enc, eol = read_text_bom_safe(RETRY_UTILS)
    result = {"file": str(RETRY_UTILS), "applied": False, "reason": "", "eol": repr(eol)}

    if "retry_predicate" in text_lf:
        result["reason"] = "ALREADY PATCHED (retry_predicate kwarg present)"
        return result

    matches = RETRY_CALL_FUNC_RE.findall(text_lf)
    if len(matches) != 1:
        result["reason"] = f"REGEX MATCHED {len(matches)} times (expected 1)"
        result["text_lf_full"] = text_lf
        return result

    new_text_lf = RETRY_CALL_FUNC_RE.sub(RETRY_UTILS_NEW_FUNC, text_lf, count=1)
    ast_validate(new_text_lf, RETRY_UTILS.name)

    if dry_run:
        result["reason"] = "DRY-RUN ok -- regex matched 1 function, replacement staged"
        result["bytes_delta"] = len(new_text_lf) - len(text_lf)
        result["matched_chars"] = len(matches[0])
        return result

    backup_path = backup(RETRY_UTILS)
    write_text_preserve_eol(RETRY_UTILS, new_text_lf, enc, eol)
    result["applied"] = True
    result["backup"] = str(backup_path)
    result["bytes_delta"] = len(new_text_lf) - len(text_lf)
    result["matched_chars"] = len(matches[0])
    return result


def verify() -> int:
    failures = []
    text_lf, _, _ = read_text_bom_safe(RETRY_UTILS)
    if "retry_predicate" not in text_lf:
        failures.append("retry_utils: retry_predicate kwarg missing")
    if "RETRY_BURN_DOWN" not in text_lf:
        failures.append("retry_utils: RETRY_BURN_DOWN telemetry missing")
    ast_validate(text_lf, RETRY_UTILS.name)

    if failures:
        print("VERIFY FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("VERIFY OK -- RETRY_UTILS patched correctly")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="ENH-99 v3 patch -- RETRY_UTILS only, regex anchor")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    if args.verify:
        return verify()

    started = datetime.now()
    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"[patch_s36_enh99_v3] {mode} start at {started.isoformat(timespec='seconds')}")
    print(f"[patch_s36_enh99_v3] REPO={REPO}")
    print()

    r = patch_retry_utils(args.dry_run)
    applied = r.get("applied", False)
    ok = applied or "DRY-RUN ok" in r.get("reason", "") or "ALREADY" in r.get("reason", "")
    marker = "[OK]" if ok else "[--]"
    print(f"{marker} [RETRY_UTILS] {r}")

    elapsed = (datetime.now() - started).total_seconds()
    print(f"\n[patch_s36_enh99_v3] elapsed={elapsed:.2f}s")

    if not args.dry_run and applied:
        print("\nNext steps:")
        print("  1. python patch_s36_enh99_v3.py --verify")
        print("  2. python -c \"from gamma_engine_retry_utils import retry_call; print('import ok')\"")
        print("  3. python -c \"import ingest_option_chain_local; print('ingest import ok')\"")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
