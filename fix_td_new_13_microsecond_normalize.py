"""
fix_td_new_13_microsecond_normalize.py — S28 TD-NEW-13 patch

Defect:
  `_dte_from_ts` helper in compute_gamma_metrics_local.py (added by
  TD-NEW-4) calls `datetime.fromisoformat(ts)` directly on Supabase ts
  string. Python 3.10's stdlib accepts only 3 or 6 microsecond digits;
  Supabase serializes with variable precision (2, 4, 5, 7 digits common).

  Python 3.12 (Local Windows) is permissive — accepts arbitrary precision.
  Python 3.10 (AWS Linux) raises `ValueError: Invalid isoformat string`.

Surfaced:
  Session 28 backfill loop on AWS, 2026-05-13. 60 of 587 broken-window
  cycles failed with "Invalid isoformat string" errors — all timestamps
  with non-6-digit microsecond fields. Live path was unaffected because
  fresh-from-broker writes always have consistent microsecond precision
  in the runtime that captured them.

Severity:
  S2 — backfill correctness only. Live writes unaffected.

Fix:
  Normalize microseconds to exactly 6 digits via regex before calling
  fromisoformat(). Pad short fractions with zeros; truncate long ones.

Canonical patch pattern:
  - BOM-safe read via read_bytes() + decode('utf-8-sig')
  - EOL detection + preservation on write
  - ast.parse() self-validation before write
  - _PRE_TD-NEW-13.py backup
  - Idempotency guard
"""

import ast
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "compute_gamma_metrics_local.py"


OLD = '''    if isinstance(ts, str):
        ts_dt = _dt.fromisoformat(ts.replace("Z", "+00:00"))
    else:
        ts_dt = ts'''

NEW = '''    if isinstance(ts, str):
        # TD-NEW-13 (S28): normalize microseconds to 6 digits for Python 3.10 compat.
        # AWS runs Python 3.10 which rejects non-3/6-digit microseconds in fromisoformat.
        # Supabase serializes with variable precision (2-7 digits).
        import re as _re
        _ts = ts.replace("Z", "+00:00")
        _m = _re.match(r"^(.+)\\.(\\d+)(\\+\\d{2}:\\d{2}|\\-\\d{2}:\\d{2})$", _ts)
        if _m:
            _base, _frac, _tz = _m.groups()
            _frac = (_frac + "000000")[:6]
            _ts = f"{_base}.{_frac}{_tz}"
        ts_dt = _dt.fromisoformat(_ts)
    else:
        ts_dt = ts'''


def main():
    if not TARGET.exists():
        sys.exit(f"FATAL: {TARGET} not found")

    raw = TARGET.read_bytes()
    text = raw.decode("utf-8-sig")

    crlf_count = raw.count(b"\r\n")
    lf_only = raw.count(b"\n") - crlf_count
    eol = "\r\n" if crlf_count > lf_only else "\n"

    text_lf = text.replace("\r\n", "\n")

    if "TD-NEW-13" in text_lf:
        sys.exit("ALREADY PATCHED: TD-NEW-13 marker present. Aborting.")

    if OLD not in text_lf:
        sys.exit("FATAL: OLD pattern not found. File may have drifted.")

    if text_lf.count(OLD) > 1:
        sys.exit("FATAL: multiple matches for OLD pattern.")

    text_new = text_lf.replace(OLD, NEW, 1)

    try:
        ast.parse(text_new)
    except SyntaxError as e:
        sys.exit(f"AST PARSE FAILED: {e}")

    backup = TARGET.with_name(TARGET.stem + "_PRE_TD-NEW-13.py")
    if backup.exists():
        sys.exit(f"REFUSING to overwrite existing backup {backup.name}")
    backup.write_bytes(raw)

    text_out = text_new.replace("\n", eol) if eol == "\r\n" else text_new
    out = TARGET.with_name(TARGET.stem + "_PATCHED.py")
    out.write_bytes(text_out.encode("utf-8"))

    print(f"OK: backup       -> {backup.name}")
    print(f"OK: patched      -> {out.name}")
    print(f"EOL preserved    -> {'CRLF' if eol == chr(13) + chr(10) else 'LF'}")


if __name__ == "__main__":
    main()
