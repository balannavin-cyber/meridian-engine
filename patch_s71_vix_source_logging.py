#!/usr/bin/env python3
"""
patch_s71_vix_source_logging.py -- Session 71, Canon-v3

Closes TD-S70-NEW-5: load_vix_history_rows() selects silently among three
candidate tables and logs nothing.

The function iterates ["india_vix_daily", "india_vix_history",
"vix_percentile_reference"], swallows every exception with a bare `continue`,
keeps whichever result is longest, and never records which table answered or
how many rows it returned. Two of the three are empty and the third is frozen
at 2026-03-11. Everything downstream ran, reported success, and scored
vix_percentile against a five-month-old reference distribution
(Assumption Register D.28.5).

This patch adds observability ONLY. No selection behaviour changes:
  - per-candidate probe result recorded, including swallowed exception type
  - resolved source + row count + date range + age emitted on every call
  - WARN when the newest row is older than VIX_HISTORY_MAX_AGE_DAYS
  - WARN when a candidate returned exactly the PostgREST page cap, which is
    the tell for a silently truncated read

The last of these is deliberate. sb.select() is called with limit=5000 and NO
order clause, while PostgREST hard-caps at 1000 rows per request -- and
india_vix_history holds 1,782. If the resolved source reports rows at the cap,
the read is truncated and the 252-day percentile window is anchored somewhere
other than the table's newest rows. That is a separate defect from the missing
writer (TD-S70-NEW-4); this patch is instrumented to expose it rather than
assume it, per ADR-009: measure before filing.

Run:
  python patch_s71_vix_source_logging.py            # dry-run (default)
  python patch_s71_vix_source_logging.py --apply
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
TARGET = "compute_volatility_metrics_local.py"
MARKER = "# S71-VIX-SOURCE-LOGGING"
BACKUP_SUFFIX = "_PRE_S71"


def read_source(path: Path):
    raw = path.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    eol = "\r\n" if crlf >= lf_only else "\n"
    return text.replace("\r\n", "\n"), had_bom, eol


def write_source(path: Path, text_lf: str, had_bom: bool, eol: str) -> int:
    out = text_lf.replace("\n", eol) if eol != "\n" else text_lf
    data = out.encode("utf-8")
    if had_bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)
    return len(data)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ANCHOR FAIL [{label}]: expected count==1, got {n}")
    print(f"  anchor OK  [{label}]")
    return text.replace(old, new, 1)


EDITS = [
    (
        "staleness constant",
        """def load_vix_history_rows(sb: SupabaseClient) -> List[Tuple[date, float]]:""",
        """# S71 (TD-S70-NEW-5). Age bound on the VIX reference distribution. 7 calendar
# days tolerates a long weekend plus a holiday; anything beyond that means the
# history table has stopped being written and vix_percentile is being scored
# against a distribution that no longer describes the market.
VIX_HISTORY_MAX_AGE_DAYS = 7

# PostgREST returns at most this many rows per request regardless of the limit
# parameter. A candidate reporting exactly this count was truncated.
VIX_PAGE_CAP = 1000


def load_vix_history_rows(sb: SupabaseClient) -> List[Tuple[date, float]]:""",
    ),
    (
        "probe accumulators",
        """    candidates = ["india_vix_daily", "india_vix_history", "vix_percentile_reference"]
    parsed: List[Tuple[date, float]] = []

    for table_name in candidates:""",
        """    # S71 (TD-S70-NEW-5): a source-selection function must record which source
    # answered and how many rows it returned. Selection logic below is
    # UNCHANGED -- this is observability, not behaviour.
    candidates = ["india_vix_daily", "india_vix_history", "vix_percentile_reference"]
    parsed: List[Tuple[date, float]] = []
    resolved_source: Optional[str] = None
    probes: List[str] = []
    capped: List[str] = []

    for table_name in candidates:""",
    ),
    (
        "record swallowed exception",
        """                label=f"select {table_name}",
            )
        except Exception:
            continue""",
        """                label=f"select {table_name}",
            )
        except Exception as _vix_exc:
            # S71: was a bare `continue`. A swallowed exception must say what
            # it swallowed, or the fallback chain is indistinguishable from
            # an empty table.
            probes.append(f"{table_name}=ERROR:{type(_vix_exc).__name__}")
            continue""",
    ),
    (
        "raw row count",
        """        temp: List[Tuple[date, float]] = []
        for row in rows or []:""",
        """        _raw_n = len(rows or [])
        if _raw_n >= VIX_PAGE_CAP:
            capped.append(table_name)
        temp: List[Tuple[date, float]] = []
        for row in rows or []:""",
    ),
    (
        "record resolution",
        """        if len(temp) > len(parsed):
            parsed = temp""",
        """        probes.append(f"{table_name}=raw:{_raw_n}/usable:{len(temp)}")
        if len(temp) > len(parsed):
            parsed = temp
            resolved_source = table_name""",
    ),
    (
        "emit resolution",
        """    out = sorted(dedup.items(), key=lambda x: x[0])""",
        """    out = sorted(dedup.items(), key=lambda x: x[0])

    # S71 (TD-S70-NEW-5): emit the resolution on every call.
    _probe_str = ", ".join(probes) if probes else "none"
    if out:
        _oldest, _newest = out[0][0], out[-1][0]
        _age_days = (date.today() - _newest).days
        print(f"  [VIX-HISTORY] resolved={resolved_source} rows={len(out)} "
              f"range={_oldest}..{_newest} age_days={_age_days} "
              f"probes[{_probe_str}]")
        if _age_days > VIX_HISTORY_MAX_AGE_DAYS:
            print(f"  [WARN] [VIX-HISTORY] newest row {_newest} is {_age_days}d "
                  f"old (floor {VIX_HISTORY_MAX_AGE_DAYS}d). vix_percentile is "
                  f"scored against a stale reference distribution -- "
                  f"TD-S70-NEW-4 (no writer on the history table).")
    else:
        print(f"  [WARN] [VIX-HISTORY] no usable rows from any candidate; "
              f"probes[{_probe_str}]. vix_percentile will be None.")
    if capped:
        print(f"  [WARN] [VIX-HISTORY] candidate(s) {capped} returned the "
              f"PostgREST page cap ({VIX_PAGE_CAP}) -- the read is TRUNCATED "
              f"and, with no order clause, the retained rows are not "
              f"necessarily the newest. The percentile window may be anchored "
              f"far from the table's true tail.")""",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default is dry-run)")
    args = ap.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"patch_s71_vix_source_logging.py  [{mode}]")
    print(f"  base: {BASE}\n")

    path = BASE / TARGET
    if not path.exists():
        raise SystemExit(f"MISSING: {path}")

    print(f"--- {TARGET} ---")
    text, had_bom, eol = read_source(path)
    before = len(path.read_bytes())
    print(f"  before: {before}B  bom={had_bom}  "
          f"eol={'CRLF' if eol == chr(13)+chr(10) else 'LF'}")

    if MARKER in text:
        print("  SKIP: idempotency marker present, already patched.")
        return 0

    if "Optional" not in text.split("def load_vix_history_rows")[0]:
        raise SystemExit(
            "PRECONDITION FAIL: `Optional` not imported above the target "
            "function; the resolved_source annotation would NameError.")
    print("  precondition OK (Optional in scope)")

    for label, old, new in EDITS:
        text = replace_once(text, old, new, label)

    text = text.rstrip("\n") + f"\n\n{MARKER}\n"

    try:
        ast.parse(text)
        print("  ast.parse OK")
    except SyntaxError as e:
        raise SystemExit(f"AST FAIL: line {e.lineno}: {e.msg}")

    if args.apply:
        bak = path.with_name(path.stem + BACKUP_SUFFIX + path.suffix)
        shutil.copy2(path, bak)
        after = write_source(path, text, had_bom, eol)
        print(f"  backup: {bak.name}")
        print(f"  after:  {after}B  ({after - before:+d})")
    else:
        projected = len(
            ((text.replace("\n", eol) if eol != "\n" else text).encode("utf-8")))
        if had_bom:
            projected += 3
        print(f"  after:  {projected}B  ({projected - before:+d})  [not written]")
        print("\n  DRY-RUN. Re-run with --apply to write.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
