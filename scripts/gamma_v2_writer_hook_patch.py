#!/usr/bin/env python3
"""gamma_v2_writer_hook_patch.py -- ADR-033: add the V2 hook to compute_gamma_metrics_local.py.

AUTHORED, NOT APPROVED FOR APPLY. Run from the repo root of a worktree, never on the box.
  python -B scripts/gamma_v2_writer_hook_patch.py            dry run: shows what would change, writes nothing
  python -B scripts/gamma_v2_writer_hook_patch.py --apply    writes the file
  python -B scripts/gamma_v2_writer_hook_patch.py --revert   removes the three insertions (rollback)

Three insertions, no deletion, no change to any V1 statement:
  1. an optional import of gamma_v2_writer (a failed import leaves V1 untouched),
  2. one line that keeps a reference to the chain rows V1 has just read,
  3. the hook call after the V1 writes, inside try/except, changing no exit code.
Guards: every anchor must occur exactly once; refuses if the hook is already present;
keeps the file's line endings (LF or CRLF) byte for byte elsewhere.
"""
import sys

PATH = "compute_gamma_metrics_local.py"
MARK = "ADR-033 V2 hook"

A1 = "from core.execution_log import ExecutionLog\n"
I1 = (
    "try:  # ADR-033 V2 hook (optional; a failed import must not affect V1)\n"
    "    import gamma_v2_writer\n"
    "except Exception as _v2_import_error:  # noqa: BLE001\n"
    "    gamma_v2_writer = None\n"
    "_V2_STASH: dict = {}  # ADR-033 V2 hook: the chain rows of this run, for the hook only\n"
)
A2 = "    option_rows_raw = fetch_option_chain_rows(run_id, expected_symbol=expected_symbol)\n"
I2 = "    _V2_STASH[\"rows\"] = option_rows_raw  # ADR-033 V2 hook: V1 does not read this\n"
A3 = "    print(f\"gex_strike_snapshots_rows_written={gss_n}\")\n"
I3 = (
    "    try:  # ADR-033 V2 hook: after the V1 writes; time-bounded; never raises; never changes the exit code\n"
    "        if gamma_v2_writer is not None:\n"
    "            _v2_status = gamma_v2_writer.write_v2_bounded(\n"
    "                SUPABASE, _V2_STASH.get(\"rows\"), run_id=result.run_id, symbol=result.symbol, ts=result.ts,\n"
    "                expiry_date=result.expiry_date,\n"
    "                dte=(result.gss_rows[0].get(\"dte\") if result.gss_rows else None),\n"
    "                spot=result.spot, shadow=USE_SHADOW)\n"
    "            print(f\"gamma_v2_status={_v2_status}\")\n"
    "    except Exception as _v2_error:  # noqa: BLE001  # ADR-033 V2 hook\n"
    "        print(f\"gamma_v2_status=HOOK_ERROR {type(_v2_error).__name__}: {_v2_error}\", file=sys.stderr)\n"
)


def main() -> int:
    mode = "apply" if "--apply" in sys.argv else "revert" if "--revert" in sys.argv else "dry"
    raw = open(PATH, "rb").read()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    if mode == "revert":
        new = text
        for ins in (I1, I2, I3):
            if new.count(ins) != 1:
                print(f"STOP: insertion not found exactly once; nothing changed"); return 2
            new = new.replace(ins, "")
    else:
        if MARK in text:
            print("STOP: the hook is already present; nothing changed"); return 2
        new = text
        for anchor, ins in ((A1, I1), (A2, I2), (A3, I3)):
            n = new.count(anchor)
            if n != 1:
                print(f"STOP: anchor found {n} times (must be 1): {anchor.strip()[:70]!r}; nothing changed"); return 2
            new = new.replace(anchor, anchor + ins)
        if "import sys" not in text:
            print("STOP: the file does not import sys; nothing changed"); return 2
    added = len(new.splitlines()) - len(text.splitlines())
    print(f"{PATH}: {'+' if added >= 0 else ''}{added} lines, line endings {'CRLF' if crlf else 'LF'}, mode {mode}")
    if mode == "dry":
        print("dry run: nothing written. Re-run with --apply."); return 0
    out = new.replace("\n", "\r\n") if crlf else new
    open(PATH, "wb").write(out.encode("utf-8"))
    print("written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
