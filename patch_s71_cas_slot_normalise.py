#!/usr/bin/env python3
"""
patch_s71_cas_slot_normalise.py -- Session 71, Canon-v3 (follow-up to
patch_s71_cas_corrections.py)

Fixes two defects surfaced by the 2026-08-03 dry-run.

(1) STORAGE-KEY LEAK (substantive). patch_s71_cas_corrections.py widened the
    accepted bar slot to {15:29, 15:34} because the exchange window differed in
    the first CAS week. But capture_cas_close.py derives hist_spot_bars_1m.bar_ts
    from the vendor's ACTUAL bar timestamp, so a 15:34 bar would be stored at
    15:34 -- while S70's daily-endpoint backfill already wrote 08-03/04/05 into
    the 15:29 slot, and backfill_cas_close_from_daily.py::fetch_existing_close_bars
    reads ONLY the 15:29 slot (CLOSE_BAR_IST).

    Net effect if left alone: an apply-mode run on 08-03/04/05 writes a SECOND
    closing bar per session; max(bar_ts) shifts to 15:34, silently changing what
    every daily-close consumer reads; and the reconciler cannot see the 15:34 bar,
    so it reports MISSING and writes a 15:29 duplicate on top.

    Fix: the accepted slot set governs ACCEPTANCE; the canonical slot governs
    STORAGE. bar_ts is always written at CAS_CLOSE_BAR (15:29) whichever
    known-good slot the vendor returned. The true vendor slot is already
    recorded as raw.bar_slot_ist, so provenance is not lost.

(2) MESSAGE HARDCODE (cosmetic). The [PROVISIONAL] line said "flat 15:29 bar"
    while printing a 15:34 bar. Uses the real slot now.

Run:
  python patch_s71_cas_slot_normalise.py            # dry-run (default)
  python patch_s71_cas_slot_normalise.py --apply
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
TARGET = "capture_cas_close.py"
MARKER = "# S71-CAS-SLOT-NORMALISE"
REQUIRED_PRIOR = "# S71-CAS-CORRECTIONS"
BACKUP_SUFFIX = "_PRE_S71B"


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
        "provisional message true slot",
        """            bar["provisional_flat"] = (bar["close"] == bar["open"])
            if bar["provisional_flat"]:
                print(f"  [PROVISIONAL] {symbol}: flat 15:29 bar "
                      f"(O=C={bar['close']:.2f}) -- written, pending daily "
                      f"reconciliation")
                provisional.append(symbol)""",
        """            bar["provisional_flat"] = (bar["close"] == bar["open"])
            if bar["provisional_flat"]:
                print(f"  [PROVISIONAL] {symbol}: flat "
                      f"{bar_ist.strftime('%H:%M')} bar "
                      f"(O=C={bar['close']:.2f}) -- written, pending daily "
                      f"reconciliation")
                provisional.append(symbol)""",
    ),
    (
        "canonical storage slot",
        """    bar_rows = []
    for symbol, bar in bars.items():
        bar_ts_utc = datetime.fromtimestamp(
            bar["timestamp"], IST).astimezone(timezone.utc).isoformat()""",
        """    bar_rows = []
    for symbol, bar in bars.items():
        # S71: the accepted-slot SET governs acceptance; the canonical slot
        # governs STORAGE. Writing a 15:34 bar at 15:34 would put a second
        # closing bar in sessions the S70 daily backfill already wrote at
        # 15:29, shift max(bar_ts) for those sessions, and make the row
        # invisible to backfill_cas_close_from_daily.py (which reads the
        # 15:29 slot only). True vendor slot is preserved in
        # raw.bar_slot_ist.
        bar_ts_utc = (
            datetime.combine(trade_day, datetime.min.time(), IST)
            .replace(hour=CAS_CLOSE_BAR[0], minute=CAS_CLOSE_BAR[1])
            .astimezone(timezone.utc).isoformat()
        )""",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default is dry-run)")
    args = ap.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"patch_s71_cas_slot_normalise.py  [{mode}]")
    print(f"  base: {BASE}\n")

    path = BASE / TARGET
    if not path.exists():
        raise SystemExit(f"MISSING: {path}")

    print(f"--- {TARGET} ---")
    text, had_bom, eol = read_source(path)
    before = len(path.read_bytes())
    print(f"  before: {before}B  bom={had_bom}  "
          f"eol={'CRLF' if eol == chr(13)+chr(10) else 'LF'}")

    if REQUIRED_PRIOR not in text:
        raise SystemExit(
            f"PRECONDITION FAIL: {REQUIRED_PRIOR} not found. "
            f"Run patch_s71_cas_corrections.py --apply first.")
    print(f"  precondition OK ({REQUIRED_PRIOR} present)")

    if MARKER in text:
        print("  SKIP: idempotency marker present, already patched.")
        return 0

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
