#!/usr/bin/env python3
"""
patch_s71_cas_corrections.py -- Session 71, Canon-v3

Closes TD-S70-NEW-2 (capture_cas_close.py Guard 3 over-fitted + bar-slot
assertion too narrow) and TD-S70-NEW-3 (backfill_cas_close_from_daily.py
batch capture_ts collision).

TD-S70-NEW-2:
  Guard 3 tested close != open as a proxy for "settled". D.28.3 refuted it:
  close == open means the auction settled at the price the index was already
  frozen at -- the common case on a quiet close. It rejected 10 of 28
  symbol-days that were already correct. Replaced with: accept the flat bar,
  mark it provisional, let backfill_cas_close_from_daily.py reconcile it
  against the daily endpoint the next morning (the daily endpoint does not
  publish same-day, verified 2026-08-21 18:32 IST, so a same-day authority
  cross-check is not available -- provisional-then-reconcile is the only
  shape that works).
  Bar-slot assertion widened 15:29 -> {15:29, 15:34}: sessions 2026-08-03/04/05
  place the last bar at 15:34; the exchange window differed in the first CAS
  week. The assertion keeps its job -- refuse a bar of unknown provenance --
  but over a known-good set rather than a single slot.

TD-S70-NEW-3:
  capture_ts computed once before the write loop. Correct for
  capture_cas_close.py (two rows, one instant); wrong for a backfill writing
  many sessions in one pass -- 14 rows collided on (symbol, ts, source_table)
  with 23505. Derive ts per row from that row's bar_ist.

Run:
  python patch_s71_cas_corrections.py            # dry-run (default)
  python patch_s71_cas_corrections.py --apply
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MARKER = "# S71-CAS-CORRECTIONS"
BACKUP_SUFFIX = "_PRE_S71"


# -- Canon-v3 IO ------------------------------------------------------------

def read_source(path: Path):
    """Return (text_lf, had_bom, predominant_eol)."""
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


# -- capture_cas_close.py ---------------------------------------------------

CCC_EDITS = [
    (
        "docstring Guard 3",
        """  3. Settled-vs-frozen check: a genuine settled bar has close != open.
     If close == open the auction result has not landed yet; exit
     SKIPPED_NO_INPUT so a later manual run can retry. Never write a
     frozen value as the close (ADR-001: a plausible wrong close is worse
     than a missing one).""",
        """  3. Flat-bar provisional marking (S71, TD-S70-NEW-2). A flat 15:29 bar
     (close == open) is NOT evidence the auction has not landed -- it is
     the common case on a quiet close, where the auction settles at the
     price the index was already frozen at. The original guard rejected
     10 of 28 symbol-days that already held the correct settled close
     (Assumption Register D.28.3). Dhan's daily endpoint is the authority
     but does not publish same-day (verified 2026-08-21 18:32 IST), so no
     same-day cross-check exists. The bar is therefore WRITTEN and marked
     flat_bar_provisional=true in raw; backfill_cas_close_from_daily.py
     reconciles it against the daily close on the next run and reports any
     MISMATCH without auto-correcting.""",
    ),
    (
        "CAS_CLOSE_BAR slots",
        """# The bar we expect back. Assertion, not a preference.
CAS_CLOSE_BAR   = (15, 29)""",
        """# The bar we expect back. Assertion, not a preference.
CAS_CLOSE_BAR   = (15, 29)

# S71 (TD-S70-NEW-2): the assertion accepts a known-good SET of slots, not a
# single one. Sessions 2026-08-03/04/05 placed the last bar at 15:34 -- the
# exchange/vendor window differed in the first CAS week. Refusing a bar of
# unknown provenance is still the job; the set is what "known" means.
CAS_CLOSE_BAR_SLOTS = {(15, 29), (15, 34)}""",
    ),
    (
        "Guard 2 membership",
        """            # Guard 2 -- bar-timestamp assertion.
            if (bar_ist.hour, bar_ist.minute) != CAS_CLOSE_BAR:
                msg = (f"{symbol}: last bar is {bar_ist.strftime('%H:%M')} IST, "
                       f"expected {CAS_CLOSE_BAR[0]:02d}:{CAS_CLOSE_BAR[1]:02d} "
                       f"-- vendor bar shape changed, refusing to write")""",
        """            # Guard 2 -- bar-timestamp assertion (S71: known-good slot set).
            if (bar_ist.hour, bar_ist.minute) not in CAS_CLOSE_BAR_SLOTS:
                _slots = ", ".join(f"{h:02d}:{m:02d}"
                                   for h, m in sorted(CAS_CLOSE_BAR_SLOTS))
                msg = (f"{symbol}: last bar is {bar_ist.strftime('%H:%M')} IST, "
                       f"expected one of {{{_slots}}} "
                       f"-- vendor bar shape changed, refusing to write")""",
    ),
    (
        "Guard 3 provisional",
        """            # Guard 3 -- settled vs still-frozen.
            if bar["close"] == bar["open"]:
                msg = (f"{symbol}: 15:29 bar still frozen "
                       f"(O=C={bar['close']:.2f}); auction result not landed")
                print(f"  [REJECT] {msg}")
                rejects.append(f"{symbol}:frozen")
                continue

            bars[symbol] = bar""",
        """            # Guard 3 -- S71 (TD-S70-NEW-2). A flat bar is settled-at-the-frozen
            # -price, not unsettled. Write it, mark it provisional, and let
            # the next-day daily reconciliation confirm or flag it.
            bar["provisional_flat"] = (bar["close"] == bar["open"])
            if bar["provisional_flat"]:
                print(f"  [PROVISIONAL] {symbol}: flat 15:29 bar "
                      f"(O=C={bar['close']:.2f}) -- written, pending daily "
                      f"reconciliation")
                provisional.append(symbol)

            bars[symbol] = bar""",
    ),
    (
        "provisional list init",
        """    auth_failed = False
    rejects: List[str] = []""",
        """    auth_failed = False
    rejects: List[str] = []
    provisional: List[str] = []   # S71: flat bars written pending daily recon""",
    ),
    (
        "raw provisional flag",
        """                "settled_move":     round(bar["close"] - bar["open"], 4),""",
        """                "settled_move":     round(bar["close"] - bar["open"], 4),
                "flat_bar_provisional": bool(bar.get("provisional_flat")),
                "bar_slot_ist":     bar_ist.strftime("%H:%M"),""",
    ),
    (
        "provisional summary",
        """    if rejects:
        print(f"  NOTE: {len(rejects)} symbol(s) rejected: {rejects}")""",
        """    if rejects:
        print(f"  NOTE: {len(rejects)} symbol(s) rejected: {rejects}")
    if provisional:
        print(f"  NOTE: {len(provisional)} flat bar(s) written PROVISIONAL: "
              f"{provisional} -- run backfill_cas_close_from_daily.py "
              f"tomorrow to reconcile.")""",
    ),
]


# -- backfill_cas_close_from_daily.py ---------------------------------------

BF_EDITS = [
    (
        "drop batch capture_ts",
        """    bar_rows: List[Dict] = []
    snap_rows: List[Dict] = []
    capture_ts = datetime.now(IST).astimezone(timezone.utc).isoformat()""",
        """    bar_rows: List[Dict] = []
    snap_rows: List[Dict] = []
    # S71 (TD-S70-NEW-3): ts is derived PER ROW from that row's bar_ist.
    # A single batch capture_ts collided on the (symbol, ts, source_table)
    # unique key -- 14 rows, one instant, 23505. The run's own wall-clock
    # is already preserved in market_spot_snapshots.created_at (row-birth).""",
    ),
    (
        "per-row snapshot ts",
        """        snap_rows.append({
            "ts":           capture_ts,""",
        """        snap_rows.append({
            "ts":           bar_ist.astimezone(timezone.utc).isoformat(),""",
    ),
]


TARGETS = [
    ("capture_cas_close.py", CCC_EDITS),
    ("backfill_cas_close_from_daily.py", BF_EDITS),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default is dry-run)")
    args = ap.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"patch_s71_cas_corrections.py  [{mode}]")
    print(f"  base: {BASE}\n")

    results = []

    for fname, edits in TARGETS:
        path = BASE / fname
        print(f"--- {fname} ---")
        if not path.exists():
            raise SystemExit(f"MISSING: {path}")

        text, had_bom, eol = read_source(path)
        before = len(path.read_bytes())
        print(f"  before: {before}B  bom={had_bom}  "
              f"eol={'CRLF' if eol == chr(13)+chr(10) else 'LF'}")

        if MARKER in text:
            print("  SKIP: idempotency marker present, already patched.\n")
            continue

        for label, old, new in edits:
            text = replace_once(text, old, new, label)

        text = text.rstrip("\n") + f"\n\n{MARKER}\n"

        try:
            ast.parse(text)
            print("  ast.parse OK")
        except SyntaxError as e:
            raise SystemExit(f"AST FAIL in {fname}: line {e.lineno}: {e.msg}")

        if args.apply:
            bak = path.with_name(path.stem + BACKUP_SUFFIX + path.suffix)
            shutil.copy2(path, bak)
            after = write_source(path, text, had_bom, eol)
            print(f"  backup: {bak.name}")
            print(f"  after:  {after}B  ({after - before:+d})\n")
            results.append((fname, before, after))
        else:
            projected = len(
                ((text.replace("\n", eol) if eol != "\n" else text)
                 .encode("utf-8")))
            if had_bom:
                projected += 3
            print(f"  after:  {projected}B  ({projected - before:+d})  "
                  f"[not written]\n")
            results.append((fname, before, projected))

    print("=" * 62)
    for fname, b, a in results:
        print(f"  {fname:36s} {b:>7d} -> {a:>7d}  ({a - b:+d})")
    if not args.apply:
        print("\n  DRY-RUN. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
