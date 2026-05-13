"""
fix_td_new_4_dte_uses_ts.py — S28 TD-NEW-4 patch

Defect:
  upsert_gamma_metrics() in compute_gamma_metrics_local.py computes the
  `dte` payload field as:
      date.fromisoformat(result.expiry_date) - date.today()
  This is correct for live writes (result.ts ≈ now within seconds) but
  incorrect for ANY backfill — the historical `result.ts` and `date.today()`
  diverge, producing wrong DTE values on backfilled rows.

  Same class as TD-NEW-3 (silent unit bug): nothing in the live pipeline
  triggers it; surfaces only when rerunning historical data.

Surfaced:
  Session 28, during P1 broken-window backfill prep — inspection of
  upsert_gamma_metrics source after pivot from custom backfill script
  to bash-loop reuse of the live writer.

Severity:
  S2 latent backfill defect. No current live-pipeline impact.
  Future downstream consumers of DTE magnitude (ADR-002 v2 ENH-80/81
  DTE-adjusted force multiplier) would silently consume wrong values
  on any backfilled row.

Fix:
  Inject `_dte_from_ts(result)` helper at module level (above
  upsert_gamma_metrics). Helper derives the as-of date from result.ts
  in IST. Replace the inline payload computation with a call.

Canonical patch pattern:
  - BOM-safe read via read_bytes() + decode('utf-8-sig')
  - EOL detection + preservation on write
  - ast.parse() self-validation before write
  - _PRE_TD-NEW-4.py backup (refuse overwrite if exists)
  - _PATCHED.py output (operator renames to canonical after diff review)
  - Idempotency guards on each substitution
"""

import ast
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "compute_gamma_metrics_local.py"


OLD_PAYLOAD = '''        "dte": (
            (__import__("datetime").date.fromisoformat(result.expiry_date) -
             __import__("datetime").date.today()).days
            if result.expiry_date else None
        ),'''

NEW_PAYLOAD = '''        "dte": _dte_from_ts(result),'''


OLD_DEF = "def upsert_gamma_metrics(result: GammaMetricsResult) -> dict[str, Any]:"

NEW_DEF = '''def _dte_from_ts(result):
    """TD-NEW-4 (S28): compute DTE as (expiry - result.ts.date()) in IST.

    Replaces prior `date.today()` reference which silently broke backfill
    correctness. Live writes unaffected (result.ts is ~= now within seconds).
    Self-contained: local imports avoid module-level import changes.
    """
    if not result.expiry_date:
        return None
    from datetime import date as _date, datetime as _dt, timezone as _tz, timedelta as _td
    _IST = _tz(_td(hours=5, minutes=30))
    ts = result.ts
    if isinstance(ts, str):
        ts_dt = _dt.fromisoformat(ts.replace("Z", "+00:00"))
    else:
        ts_dt = ts
    if ts_dt.tzinfo is None:
        ts_dt = ts_dt.replace(tzinfo=_IST)
    as_of = ts_dt.astimezone(_IST).date()
    return (_date.fromisoformat(result.expiry_date) - as_of).days


def upsert_gamma_metrics(result: GammaMetricsResult) -> dict[str, Any]:'''


def main():
    if not TARGET.exists():
        sys.exit(f"FATAL: {TARGET} not found. Run from repo root.")

    raw = TARGET.read_bytes()
    text = raw.decode("utf-8-sig")

    # --- Detect EOL convention (preserve on write) ---
    crlf_count = raw.count(b"\r\n")
    lf_only = raw.count(b"\n") - crlf_count
    eol = "\r\n" if crlf_count > lf_only else "\n"

    # --- Normalize to LF for matching ---
    text_lf = text.replace("\r\n", "\n")

    # --- Idempotency guards ---
    if "_dte_from_ts" in text_lf:
        sys.exit("ALREADY PATCHED: _dte_from_ts helper present. Aborting.")

    if OLD_PAYLOAD not in text_lf:
        sys.exit("FATAL: payload OLD pattern not found. File may have drifted.")

    if OLD_DEF not in text_lf:
        sys.exit("FATAL: upsert_gamma_metrics signature not found.")

    if text_lf.count(OLD_DEF) > 1:
        sys.exit("FATAL: multiple matches for upsert_gamma_metrics signature.")

    if text_lf.count(OLD_PAYLOAD) > 1:
        sys.exit("FATAL: multiple matches for OLD payload pattern.")

    # --- Apply substitutions ---
    text2 = text_lf.replace(OLD_PAYLOAD, NEW_PAYLOAD, 1)
    text3 = text2.replace(OLD_DEF, NEW_DEF, 1)

    # --- AST validate (always LF for parse) ---
    try:
        ast.parse(text3)
    except SyntaxError as e:
        sys.exit(f"AST PARSE FAILED: {e}")

    # --- Backup BEFORE writing PATCHED ---
    backup = TARGET.with_name(TARGET.stem + "_PRE_TD-NEW-4.py")
    if backup.exists():
        sys.exit(f"REFUSING to overwrite existing backup {backup.name}")
    backup.write_bytes(raw)

    # --- Restore EOL on write ---
    text_out = text3.replace("\n", eol) if eol == "\r\n" else text3
    out = TARGET.with_name(TARGET.stem + "_PATCHED.py")
    out.write_bytes(text_out.encode("utf-8"))

    print(f"OK: backup       -> {backup.name}")
    print(f"OK: patched      -> {out.name}")
    print(f"EOL preserved    -> {'CRLF' if eol == chr(13) + chr(10) else 'LF'}")
    print()
    print("Next steps:")
    print(f"  1. Review diff:")
    print(f"       diff -u {TARGET.name} {out.name}")
    print(f"  2. Promote to canonical:")
    print(f"       mv {out.name} {TARGET.name}")
    print(f"  3. Smoke test on one historical run_id (broken window):")
    print(f"       python3 {TARGET.name} <run_id>")
    print(f"     Then verify gamma_metrics row has correct dte for that ts.")


if __name__ == "__main__":
    main()
