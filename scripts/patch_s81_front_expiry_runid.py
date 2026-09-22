#!/usr/bin/env python3
"""S81 -- resolve the FRONT expiry's run_id, not the newest-written row.

WHY
  ingest_option_chain_local.py writes W1, commits it, then appends the S80
  extra expiries.  All of them share ONE `ts` -- `snapshot_ts = utc_now_iso()`
  is computed once at line 449 and passed unchanged to both the W1 call (457)
  and the extra-expiry call (548).  They do NOT share `created_at`, which is a
  database-side default and is therefore LATER for the extra pass.

  Two selectors order by exactly the column that differs:

    run_merdian_shadow_runner_aws.py   fetch_latest_run_ids()
    compute_options_flow_local.py      fetch_latest_runs_per_symbol()

  The moment EXPIRY_DEPTH goes above 1, both hand their consumers W2's
  run_id.  Silently: each run_id is still single-expiry, so TD-S79-NEW-12's
  guard sees one expiry and returns W2's date without raising.  gamma,
  volatility and options flow would all compute on the wrong contract, and
  every gamma-derived surface would follow -- gex_strike_snapshots,
  gamma_metrics, ENH-120/121/122/125/126, the Pine overlay, Positioning.

  Ordering by `ts.desc,expiry_date.asc` takes the latest snapshot and, within
  it, the front expiry.  At depth 1 there is exactly one expiry per (symbol,
  ts), so old and new selectors resolve to the SAME run_id -- the change is
  provably inert until the depth flip, which is what makes it safe to deploy
  ahead of it.

  core/supabase_client._normalize_order returns a string verbatim when it
  ends in `.asc`/`.desc`, so the multi-column order passes through unaltered;
  compute_options_flow_local builds raw PostgREST params, so it passes through
  there too.  Verified from source before writing this patch.

NO ">= today" GUARD, deliberately, and unlike the views.
  v_max_pain_by_strike and v_oi_rotation_since_open restrict front expiry to
  `expiry_date >= today` with no fallback, because for a display read failing
  to absent is correct.  It is WRONG here: the ingest never writes past
  expiries, and a no-fallback guard in the orchestrator converts an edge case
  into a compute outage -- no run_id means gamma does not run at all.

TWO-PHASE BY CONSTRUCTION.
  Phase 1 validates EVERY target and keeps the patched bytes in memory.
  Phase 2 writes only if every target validated.  A single-phase loop would
  write file 1, abort on file 2, and leave the runner and options flow on
  DIFFERENT selectors -- the exact split this change exists to prevent --
  while the summary claimed nothing had been modified.

USAGE
  python3 scripts/patch_s81_front_expiry_runid.py            # dry run
  python3 scripts/patch_s81_front_expiry_runid.py --apply
"""
from __future__ import annotations

import ast
import py_compile
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/ssm-user/meridian-cc")
MARKER = "S81-FRONT-EXPIRY-RUNID"
BACKUP_SUFFIX = "_PRE_S81"
BOM = b"\xef\xbb\xbf"

RUNNER_OLD = '''                    order="created_at.desc",
'''
RUNNER_NEW = '''                    # S81-FRONT-EXPIRY-RUNID -- was order="created_at.desc".
                    # W1 and the S80 extra expiries share ONE ts (ingest sets
                    # snapshot_ts once and reuses it) but NOT created_at, which
                    # is a DB default and is therefore LATER for the extra
                    # pass. Ordering by created_at.desc would hand every
                    # downstream compute W2's run_id the moment EXPIRY_DEPTH
                    # exceeds 1 -- silently, with no guard tripping, because
                    # each run_id is still single-expiry.
                    #
                    # NO ">= today" guard here, deliberately, and unlike the
                    # views. The ingest never writes past expiries, and a
                    # no-fallback guard in the orchestrator turns an edge case
                    # into a compute outage: no run_id means gamma does not run
                    # at all. Failing to absent is right for a display read; it
                    # is wrong for the thing that feeds the whole compute chain.
                    order="ts.desc,expiry_date.asc",
'''

FLOW_OLD = '''                "order": "created_at.desc",
'''
FLOW_NEW = '''                # S81-FRONT-EXPIRY-RUNID -- was "order": "created_at.desc".
                # W1 and the S80 extra expiries share ONE ts but NOT
                # created_at (a DB default, later for the extra pass), so
                # created_at.desc selects W2 once EXPIRY_DEPTH exceeds 1.
                # This picks the latest snapshot, then its front expiry.
                #
                # NO ">= today" guard, deliberately, and unlike the views:
                # the ingest never writes past expiries, and a no-fallback
                # guard here would convert an edge case into a compute
                # outage rather than a display gap.
                "order": "ts.desc,expiry_date.asc",
'''

TARGETS = [
    {
        "path": ROOT / "run_merdian_shadow_runner_aws.py",
        "old": RUNNER_OLD,
        "new": RUNNER_NEW,
        "symbols": ["fetch_latest_run_ids", "execute_pipeline"],
    },
    {
        "path": ROOT / "compute_options_flow_local.py",
        "old": FLOW_OLD,
        "new": FLOW_NEW,
        "symbols": ["fetch_latest_runs_per_symbol", "fetch_rows_for_run_id", "main"],
    },
]


def named_symbols(src: str) -> set[str]:
    """Top-level function / class names present in the source.

    S64: ast.parse alone is insufficient. A str_replace can swallow a `def`
    header and leave an orphaned body that parses clean and NameErrors only at
    runtime. Assert the names exist, not merely that the file parses.
    """
    out: set[str] = set()
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
    return out


def validate(target: dict) -> dict:
    """Phase 1. Validates one target and returns a plan. Writes NOTHING.

    plan = {status: OK|SKIP|ABORT, name, detail, path, out_bytes, eol_note}
    """
    path: Path = target["path"]
    name = path.name
    plan = {"status": "ABORT", "name": name, "detail": "", "path": path,
            "out_bytes": None, "eol_note": ""}

    if not path.exists():
        plan["detail"] = "file not found"
        return plan

    raw = path.read_bytes()

    # --- BOM: detect on the RAW bytes and re-emit it if present. Reading with
    # --- utf-8-sig and writing utf-8 silently DROPS a BOM.
    has_bom = raw.startswith(BOM)
    src_raw = raw.decode("utf-8-sig")

    # --- EOL: canon-v3 / Rule 18. Match in LF space, restore the predominant
    # --- ending on write. Report the counts so a normalisation of a
    # --- mixed-EOL file cannot happen silently.
    crlf = src_raw.count("\r\n")
    bare_lf = src_raw.count("\n") - crlf
    write_eol = "\r\n" if crlf >= bare_lf else "\n"
    mixed = crlf > 0 and bare_lf > 0
    plan["eol_note"] = (
        f"bom={'yes' if has_bom else 'no'} crlf={crlf} bare_lf={bare_lf} "
        f"write_eol={'CRLF' if write_eol == chr(13) + chr(10) else 'LF'}"
        + ("  *** MIXED EOL: write WILL normalise ***" if mixed else "")
    )

    src_lf = src_raw.replace("\r\n", "\n")

    # --- per-file idempotency gate. S80: EVERY entry gets its own gate, or a
    # --- re-run reports ABORT on a file that is already correct, and that
    # --- abort is indistinguishable from a real one.
    if MARKER in src_lf:
        plan["status"] = "SKIP"
        plan["detail"] = "marker already present, nothing to do"
        return plan

    n = src_lf.count(target["old"])
    if n != 1:
        plan["detail"] = f"anchor count == {n}, expected exactly 1"
        return plan

    patched_lf = src_lf.replace(target["old"], target["new"])
    if patched_lf == src_lf:
        plan["detail"] = "replacement produced no change"
        return plan

    try:
        ast.parse(patched_lf)
    except SyntaxError as e:
        plan["detail"] = f"ast.parse failed: {e}"
        return plan

    lost = named_symbols(src_lf) - named_symbols(patched_lf)
    if lost:
        plan["detail"] = f"symbols LOST by the edit: {sorted(lost)}"
        return plan
    after = named_symbols(patched_lf)
    missing = [s for s in target["symbols"] if s not in after]
    if missing:
        plan["detail"] = f"required symbols absent after edit: {missing}"
        return plan

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8", newline="\n") as tf:
        tf.write(patched_lf)
        tmp = Path(tf.name)
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        plan["detail"] = f"py_compile failed: {e}"
        return plan
    finally:
        tmp.unlink(missing_ok=True)

    if MARKER not in patched_lf:
        plan["detail"] = "marker missing from patched text"
        return plan

    out_text = patched_lf.replace("\n", write_eol) if write_eol == "\r\n" else patched_lf
    out_bytes = out_text.encode("utf-8")
    if has_bom:
        out_bytes = BOM + out_bytes

    plan["status"] = "OK"
    plan["out_bytes"] = out_bytes
    plan["detail"] = "anchor 1, parse OK, compile OK, symbols intact"
    return plan


def main() -> int:
    apply = "--apply" in sys.argv
    print("=" * 74)
    print(f"S81 front-expiry run_id patch -- {'APPLY' if apply else 'DRY RUN'}")
    print("=" * 74)

    # ---- PHASE 1: validate everything, write nothing ----------------------
    plans = [validate(t) for t in TARGETS]
    for p in plans:
        print(f"  [{p['status']}] {p['name']}: {p['detail']}")
        print(f"          {p['eol_note']}")

    n_abort = sum(1 for p in plans if p["status"] == "ABORT")
    n_ok = sum(1 for p in plans if p["status"] == "OK")
    n_skip = sum(1 for p in plans if p["status"] == "SKIP")

    print("-" * 74)
    if n_abort:
        print(f"  files={len(plans)} ok={n_ok} skipped={n_skip} aborted={n_abort}")
        print("  RESULT: ABORTED in phase 1. NOTHING was written, by construction.")
        return 1

    if not apply:
        print(f"  files={len(plans)} would_patch={n_ok} skipped={n_skip}")
        print("  RESULT: dry run clean. Re-run with --apply.")
        return 0

    # ---- PHASE 2: write only now that every target validated --------------
    written: list[str] = []
    for p in plans:
        if p["status"] != "OK":
            continue
        path: Path = p["path"]
        backup = path.with_name(path.stem + BACKUP_SUFFIX + path.suffix)
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(p["out_bytes"])
        written.append(path.name)
        print(f"  WROTE {path.name} (backup {backup.name})")

    # summary computed from what was ACTUALLY written, never a literal (S80)
    print("-" * 74)
    print(f"  files={len(plans)} written={len(written)} skipped={n_skip} aborted=0")
    print(f"  RESULT: applied to {written if written else 'NOTHING'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
