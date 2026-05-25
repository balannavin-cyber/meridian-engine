"""
patch_s36_enh99.py - MERDIAN ENH-99 Capture-layer 429 resilience + orphan janitor

Session: S36 (2026-05-25)
Closes:  TD-080 (Dhan 429 retry layer, recurring S22+S28+S29 = 3 occurrences)
Ships:   ENH-99 PROPOSED -> SHIPPED

Empirical baseline (queried S36):
  - 2026-05-14: 99 cycles failed with error_code 805 'Too many requests'.
    Existing retry budget 3 attempts x 5s x 1.5x = ~24s. Insufficient vs
    Dhan's ~60s rate window.
  - 2026-05-07: 151 cycles failed with error_code 808 (TOKEN_EXPIRED, 401).
    Pre-S29 instrumentation; root cause fixed S29 via pull_token_from_supabase
    atomic write + readback + dhan_token_probe_log. Zero post-S29 401s in
    11 instrumented days. Mode B explicitly OUT OF SCOPE.
  - 2026-05-04 + 2026-05-22: 2 orphan RUNNING rows. Process killed mid-run,
    never wrote terminal state. Janitor handles.

Three code changes + one new file:
  1. gamma_engine_retry_utils.py - add retry_predicate kwarg + RETRY_BURN_DOWN
     telemetry tag.
  2. ingest_option_chain_local.py - add is_dhan_429() helper, update 2 Dhan
     retry_call sites with longer budget (attempts=6, delay_seconds=15.0)
     + retry_predicate=is_dhan_429.
  3. (NEW) orphan_run_janitor.py - standalone helper closing stale RUNNING rows.

CHECK constraint workaround:
  script_execution_log.exit_reason has chk_exit_reason_valid CHECK constraint
  that excludes 'ORPHANED'. Janitor closes orphans with exit_reason='DATA_ERROR'
  (existing valid value) + notes prefix 'ORPHAN_RECOVERED: age_min=N'. Daily
  audit greps notes LIKE 'ORPHAN_RECOVERED%' to count orphan recoveries per day.

Pattern: canonical v3 patch script per S27 fix_f3_*_v3.py:
  - BOM-safe read via read_bytes() + decode('utf-8-sig')
  - write_bytes(text.encode(enc)) preserves line endings (no Windows LF->CRLF)
  - ast.parse() self-validation before write
  - _PRE_S36.py snapshots before any write
  - Idempotency guards: each substitution checks for marker before applying
  - Dry-run flag

Usage:
    python patch_s36_enh99.py --dry-run    # preview, no writes
    python patch_s36_enh99.py              # apply patches
    python patch_s36_enh99.py --verify     # post-patch verification only

Deferred (separate patch, needs audit-script visibility):
  - merdian_daily_audit.py thresholds:
      dhan_429_storm_threshold_warn: 10 (cycles/day with 429 in error_message)
      dhan_429_storm_threshold_fail: 30
      orphan_running_threshold_warn: 1 (any orphan is suspicious)
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from datetime import datetime
from pathlib import Path

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------

REPO = Path(r"C:\GammaEnginePython")
RETRY_UTILS = REPO / "gamma_engine_retry_utils.py"
INGEST = REPO / "ingest_option_chain_local.py"
JANITOR_NEW = REPO / "orphan_run_janitor.py"

SESSION_TAG = "S36"


# -----------------------------------------------------------------------------
# v3 file IO helpers (canonical pattern)
# -----------------------------------------------------------------------------

def read_text_bom_safe(path: Path) -> tuple[str, str]:
    """Read file as text, BOM-safe. Returns (text, encoding_used)."""
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    return raw.decode("utf-8"), "utf-8"


def write_text_preserve_eol(path: Path, text: str, encoding: str) -> None:
    """Write file as text bytes, avoiding Windows LF->CRLF auto-conversion."""
    path.write_bytes(text.encode(encoding))


def ast_validate(text: str, label: str) -> None:
    """Parse Python source to validate; SystemExit on syntax error."""
    try:
        ast.parse(text)
    except SyntaxError as e:
        raise SystemExit(f"[AST FAIL] {label}: {e}")


def backup(path: Path) -> Path:
    """Snapshot pre-patch state to _PRE_S36 sibling."""
    backup_path = path.with_name(path.stem + f"_PRE_{SESSION_TAG}" + path.suffix)
    backup_path.write_bytes(path.read_bytes())
    return backup_path


# -----------------------------------------------------------------------------
# Patch 1: gamma_engine_retry_utils.py
#   - add retry_predicate kwarg
#   - add RETRY_BURN_DOWN telemetry on final failure
# -----------------------------------------------------------------------------

RETRY_UTILS_OLD_FUNC = '''def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    delay_seconds: float = 5.0,
    backoff_multiplier: float = 1.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    label: str = "operation",
) -> T:
    last_exc = None
    current_delay = delay_seconds
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_exceptions as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            print(
                f"[retry_call] {label} failed on attempt {attempt}/{attempts} "
                f"with error: {exc}. Retrying in {current_delay:.1f}s..."
            )
            time.sleep(current_delay)
            current_delay *= backoff_multiplier if backoff_multiplier > 0 else 1.0
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"{label} failed unexpectedly without captured exception")'''

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
    """Patch gamma_engine_retry_utils.py -- add retry_predicate + telemetry."""
    text, enc = read_text_bom_safe(RETRY_UTILS)
    result = {"file": str(RETRY_UTILS), "applied": False, "reason": ""}

    # Idempotency guard
    if "retry_predicate" in text:
        result["reason"] = "ALREADY PATCHED (retry_predicate kwarg present)"
        return result

    if RETRY_UTILS_OLD_FUNC not in text:
        result["reason"] = "ANCHOR NOT FOUND -- function body did not match verbatim"
        return result

    new_text = text.replace(RETRY_UTILS_OLD_FUNC, RETRY_UTILS_NEW_FUNC, 1)
    ast_validate(new_text, RETRY_UTILS.name)

    if dry_run:
        result["reason"] = "DRY-RUN ok -- 1 substitution staged"
        result["bytes_delta"] = len(new_text) - len(text)
        return result

    backup_path = backup(RETRY_UTILS)
    write_text_preserve_eol(RETRY_UTILS, new_text, enc)
    result["applied"] = True
    result["backup"] = str(backup_path)
    result["bytes_delta"] = len(new_text) - len(text)
    return result


# -----------------------------------------------------------------------------
# Patch 2: ingest_option_chain_local.py
#   - add is_dhan_429() helper after retry import
#   - update 2 Dhan retry_call sites (NOT supabase site at ~line 417)
# -----------------------------------------------------------------------------

INGEST_HELPER_ANCHOR_OLD = "from gamma_engine_retry_utils import retry_call"

INGEST_HELPER_ANCHOR_NEW = '''from gamma_engine_retry_utils import retry_call


def is_dhan_429(exc: Exception) -> bool:
    """ENH-99 (S36): retry predicate -- True only for Dhan rate-limit (429).

    Dhan signals 429 via 'status=429' substring in the exception message OR
    error_code '805' in the response body. Any other failure (401 auth, 404
    not_found, network, parse) returns False so retry_call fails fast.
    """
    msg = str(exc)
    return "status=429" in msg or '"805"' in msg'''


# Regex pattern matching Dhan retry_call sites only (anchored on lambda: dhan.*)
# This deliberately EXCLUDES the supabase retry at line ~417 because its lambda
# targets supabase.table(...).insert(...), not dhan.<method>(...).
# DOTALL lets [^()]*? span newlines within the lambda's argument list.
DHAN_RETRY_PATTERN = re.compile(
    r"(retry_call\(\s*\n"
    r"\s*lambda:\s*dhan\.\w+\([^()]*?\)\s*,\s*)\n"
    r"(\s*)attempts=3,\s*\n"
    r"\s*delay_seconds=5\.0,\s*\n"
    r"\s*backoff_multiplier=1\.5,\s*\n",
    re.MULTILINE | re.DOTALL,
)


def dhan_retry_replacement(m: re.Match) -> str:
    """Build replacement preserving lambda block + original indentation."""
    lambda_block = m.group(1)
    indent = m.group(2)
    return (
        f"{lambda_block}\n"
        f"{indent}attempts=6,\n"
        f"{indent}delay_seconds=15.0,\n"
        f"{indent}backoff_multiplier=1.5,\n"
        f"{indent}retry_predicate=is_dhan_429,\n"
    )


def patch_ingest(dry_run: bool) -> dict:
    """Patch ingest_option_chain_local.py -- helper + Dhan retry config bump."""
    text, enc = read_text_bom_safe(INGEST)
    result = {"file": str(INGEST), "applied": False, "reason": ""}

    # Idempotency guard
    if "def is_dhan_429" in text:
        result["reason"] = "ALREADY PATCHED (is_dhan_429 helper present)"
        return result

    # Edit 1: helper insertion
    if INGEST_HELPER_ANCHOR_OLD not in text:
        result["reason"] = "ANCHOR NOT FOUND -- retry import line missing"
        return result
    n_anchor = text.count(INGEST_HELPER_ANCHOR_OLD)
    if n_anchor != 1:
        result["reason"] = f"ANCHOR AMBIGUOUS -- import line appears {n_anchor} times"
        return result

    new_text = text.replace(INGEST_HELPER_ANCHOR_OLD, INGEST_HELPER_ANCHOR_NEW, 1)

    # Edit 2: Dhan retry_call site rewrites
    matches_before = len(DHAN_RETRY_PATTERN.findall(new_text))
    new_text = DHAN_RETRY_PATTERN.sub(dhan_retry_replacement, new_text)
    matches_after = len(DHAN_RETRY_PATTERN.findall(new_text))
    sites_patched = matches_before - matches_after

    if sites_patched < 2:
        result["reason"] = (
            f"EXPECTED 2 Dhan retry sites, patched {sites_patched}. "
            f"Pattern may not match actual line shape. "
            f"Paste lines 310-360 of ingest_option_chain_local.py for diagnosis."
        )
        return result

    ast_validate(new_text, INGEST.name)

    if dry_run:
        result["reason"] = (
            f"DRY-RUN ok -- helper + {sites_patched} Dhan retry sites staged"
        )
        result["bytes_delta"] = len(new_text) - len(text)
        result["sites_patched"] = sites_patched
        return result

    backup_path = backup(INGEST)
    write_text_preserve_eol(INGEST, new_text, enc)
    result["applied"] = True
    result["backup"] = str(backup_path)
    result["bytes_delta"] = len(new_text) - len(text)
    result["sites_patched"] = sites_patched
    return result


# -----------------------------------------------------------------------------
# Patch 3: NEW file -- orphan_run_janitor.py
# -----------------------------------------------------------------------------

ORPHAN_JANITOR_SRC = '''"""
orphan_run_janitor.py -- close stale RUNNING rows in script_execution_log

ENH-99 (S36) -- Component 2 of capture-layer resilience.

Scans script_execution_log for rows with:
  - exit_reason='RUNNING'
  - started_at older than --threshold-minutes (default 5)

Closes them with:
  - exit_reason='DATA_ERROR' (existing chk_exit_reason_valid CHECK valid value;
    'ORPHANED' is NOT in the constraint -- see ENH-99 patch script header)
  - exit_code=137 (SIGKILL convention)
  - finished_at=now()
  - duration_ms=age_in_ms
  - notes='ORPHAN_RECOVERED: age_min=<N>'  <- daily audit greps this prefix

Cadence: run at intraday session start (~09:14 IST, before first ingest cycle)
via Task Scheduler. Manual invocation idempotent.

Empirical baseline S36: 2 orphans in 8 weeks (2026-05-04, 2026-05-22).
Daily warn threshold (deferred to merdian_daily_audit.py): 1 per day.

Filed under TD-080 closure path. See ENH-99 + runbook_dhan_capture_failures.md.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]

DEFAULT_THRESHOLD_MINUTES = 5


def find_orphans(sb, script_filter: str | None, threshold_minutes: int) -> list[dict]:
    """Return list of stale RUNNING rows older than threshold_minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    q = (
        sb.table("script_execution_log")
        .select("id, script_name, started_at, host, symbol, trade_date")
        .eq("exit_reason", "RUNNING")
        .lt("started_at", cutoff.isoformat())
    )
    if script_filter:
        q = q.eq("script_name", script_filter)
    resp = q.execute()
    return resp.data or []


def close_orphan(sb, row: dict) -> dict:
    """Close a single orphan row. Returns merged payload."""
    started_at = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age_min = int((now - started_at).total_seconds() / 60)
    age_ms = int((now - started_at).total_seconds() * 1000)
    notes = f"ORPHAN_RECOVERED: age_min={age_min}"
    payload = {
        "exit_reason": "DATA_ERROR",
        "exit_code": 137,
        "finished_at": now.isoformat(),
        "duration_ms": age_ms,
        "notes": notes,
    }
    sb.table("script_execution_log").update(payload).eq("id", row["id"]).execute()
    return {**row, **payload}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\\n\\n")[0])
    ap.add_argument("--script", default=None,
                    help="filter to specific script_name (default: all)")
    ap.add_argument("--threshold-minutes", type=int, default=DEFAULT_THRESHOLD_MINUTES,
                    help=f"min age to close (default: {DEFAULT_THRESHOLD_MINUTES})")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; do not UPDATE")
    args = ap.parse_args()

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    orphans = find_orphans(sb, args.script, args.threshold_minutes)

    print(f"[orphan_run_janitor] found {len(orphans)} stale RUNNING row(s) "
          f"older than {args.threshold_minutes}min")

    if not orphans:
        return 0

    for r in orphans:
        print(f"  - id={r['id']} script={r['script_name']} "
              f"started_at={r['started_at']} symbol={r.get('symbol')} "
              f"trade_date={r.get('trade_date')}")

    if args.dry_run:
        print("[orphan_run_janitor] DRY-RUN -- no rows updated")
        return 0

    for r in orphans:
        closed = close_orphan(sb, r)
        print(f"  CLOSED id={closed['id']} notes={closed['notes']}")

    print(f"[orphan_run_janitor] closed {len(orphans)} orphan(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def write_janitor(dry_run: bool) -> dict:
    """Write new orphan_run_janitor.py file."""
    result = {"file": str(JANITOR_NEW), "applied": False, "reason": ""}

    if JANITOR_NEW.exists():
        existing, _ = read_text_bom_safe(JANITOR_NEW)
        if "ENH-99" in existing:
            result["reason"] = "ALREADY EXISTS with ENH-99 marker"
            return result
        result["reason"] = "FILE EXISTS without ENH-99 marker -- manual review"
        return result

    ast_validate(ORPHAN_JANITOR_SRC, JANITOR_NEW.name)

    if dry_run:
        result["reason"] = f"DRY-RUN ok -- would create {len(ORPHAN_JANITOR_SRC)} bytes"
        return result

    write_text_preserve_eol(JANITOR_NEW, ORPHAN_JANITOR_SRC, "utf-8")
    result["applied"] = True
    result["bytes"] = len(ORPHAN_JANITOR_SRC)
    return result


# -----------------------------------------------------------------------------
# Post-patch verification
# -----------------------------------------------------------------------------

def verify() -> int:
    """Confirm all three components present and AST-valid."""
    failures = []

    # retry_utils checks
    text, _ = read_text_bom_safe(RETRY_UTILS)
    if "retry_predicate" not in text:
        failures.append("retry_utils: retry_predicate kwarg missing")
    if "RETRY_BURN_DOWN" not in text:
        failures.append("retry_utils: RETRY_BURN_DOWN telemetry missing")
    ast_validate(text, RETRY_UTILS.name)

    # ingest checks
    text, _ = read_text_bom_safe(INGEST)
    if "def is_dhan_429" not in text:
        failures.append("ingest: is_dhan_429 helper missing")
    if "retry_predicate=is_dhan_429" not in text:
        failures.append("ingest: retry_predicate=is_dhan_429 not wired at call sites")
    if "attempts=6" not in text:
        failures.append("ingest: attempts=6 retry budget extension missing")
    if "delay_seconds=15.0" not in text:
        failures.append("ingest: delay_seconds=15.0 retry base delay missing")
    ast_validate(text, INGEST.name)

    # janitor checks
    if not JANITOR_NEW.exists():
        failures.append("orphan_run_janitor.py: missing")
    else:
        janitor_text, _ = read_text_bom_safe(JANITOR_NEW)
        ast_validate(janitor_text, JANITOR_NEW.name)
        if "ORPHAN_RECOVERED" not in janitor_text:
            failures.append("orphan_run_janitor.py: ORPHAN_RECOVERED notes prefix missing")

    if failures:
        print("VERIFY FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("VERIFY OK -- all three ENH-99 components present and AST-valid")
    return 0


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="preview only -- no file writes")
    ap.add_argument("--verify", action="store_true",
                    help="post-patch verification only")
    args = ap.parse_args()

    if args.verify:
        return verify()

    started = datetime.now()
    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"[patch_s36_enh99] {mode} start at {started.isoformat(timespec='seconds')}")
    print(f"[patch_s36_enh99] REPO={REPO}")
    print()

    results = [
        ("RETRY_UTILS", patch_retry_utils(args.dry_run)),
        ("INGEST", patch_ingest(args.dry_run)),
        ("JANITOR", write_janitor(args.dry_run)),
    ]

    print()
    for label, r in results:
        applied = r.get("applied", False)
        marker = "[OK]" if applied or "DRY-RUN ok" in r.get("reason", "") or "ALREADY" in r.get("reason", "") else "[--]"
        print(f"{marker} [{label}] {r}")

    elapsed = (datetime.now() - started).total_seconds()
    print(f"\n[patch_s36_enh99] elapsed={elapsed:.2f}s")

    if not args.dry_run:
        print("\nNext steps:")
        print("  1. python patch_s36_enh99.py --verify")
        print("  2. python -c \"import ingest_option_chain_local; print('import ok')\"")
        print("  3. Monitor next live cycle for [RETRY_BURN_DOWN] tags in stderr")
        print("  4. Optional: python orphan_run_janitor.py --dry-run  # confirm helper")
        print("  5. Optional: register MERDIAN_Orphan_Janitor task at 09:14 IST daily")

    # Non-zero exit if any patch failed (anchor missing etc), zero otherwise
    any_failed = any(
        not r.get("applied", False)
        and "ALREADY" not in r.get("reason", "")
        and "DRY-RUN ok" not in r.get("reason", "")
        for _, r in results
    )
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
