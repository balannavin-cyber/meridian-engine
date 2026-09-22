#!/usr/bin/env python3
"""patch_s80_td_s79_new_12_infer_expiry.py

TD-S79-NEW-12 + ADR-024 A10 item 3.

infer_expiry_date() returns expiries[0] from an unordered PostgREST result.
It is correct today only because runs_with_multiple_expiries = 0 -- a property
of the DATA that nothing asserts. This patch:
  (a) returns min(expiries)  -- correct by construction
  (b) raises on a multi-expiry run -- states the invariant, fails loud

PREREQUISITE for the S80 multi-expiry ingest change. Once the ingest can write
more than one expiry per cycle, an arbitrary pick silently corrupts
result.expiry_date -> dte (:1047) -> gex_strike_snapshots.dte -> ENH-120 sigma.

Host-agnostic: TARGET defaults to <this script>/../compute_gamma_metrics_local.py,
so the same file runs on Local and on EC2 with no arguments. --target overrides.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, ast.parse
gate, _PRE_S80 backup (matches .gitignore *_PRE_S*), dry-run default (--apply),
count==1 anchor, idempotency marker.
"""
import argparse, ast, pathlib, sys

DEFAULT_TARGET = pathlib.Path(__file__).resolve().parent.parent / "compute_gamma_metrics_local.py"
MARKER = "TD-S79-NEW-12 (S80)"

OLD = (
    'def infer_expiry_date(option_rows: list[dict[str, Any]]) -> str | None:\n'
    '    expiries = [str(r.get("expiry_date")) for r in option_rows if r.get("expiry_date")]\n'
    '    return expiries[0] if expiries else None\n'
)

NEW = (
    'def infer_expiry_date(option_rows: list[dict[str, Any]]) -> str | None:\n'
    '    # TD-S79-NEW-12 (S80): min() is correct by construction; the raise states the\n'
    '    # single-expiry invariant that previously held only as a property of the data.\n'
    '    # Required before ingest can write >1 expiry per cycle -- an arbitrary pick\n'
    '    # corrupts dte -> gex_strike_snapshots.dte -> ENH-120 sigma, silently.\n'
    '    expiries = {str(r.get("expiry_date")) for r in option_rows if r.get("expiry_date")}\n'
    '    if not expiries:\n'
    '        return None\n'
    '    if len(expiries) > 1:\n'
    '        raise RuntimeError(\n'
    '            f"option rows carry {len(expiries)} expiries {sorted(expiries)}; "\n'
    '            f"gamma metrics assume a single-expiry run (TD-S79-NEW-12)"\n'
    '        )\n'
    '    return min(expiries)\n'
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write; default is dry-run")
    ap.add_argument("--target", default=str(DEFAULT_TARGET),
                    help="file to patch (default: repo-root sibling of scripts/)")
    args = ap.parse_args()

    target = pathlib.Path(args.target)
    print(f"target: {target}")
    if not target.is_file():
        print(f"ABORT: target not found.", file=sys.stderr)
        return 1

    raw = target.read_bytes()
    text = raw.decode("utf-8-sig")
    had_bom = raw.startswith(b"\xef\xbb\xbf")

    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    eol = "\r\n" if crlf > lf_only else "\n"
    print(f"EOL: CRLF={crlf} LF={lf_only} -> predominant {'CRLF' if crlf > lf_only else 'LF'}; BOM={had_bom}")

    if MARKER in text:
        print("IDEMPOTENT: marker already present. Nothing to do.")
        return 0

    norm = text.replace("\r\n", "\n")

    n = norm.count(OLD)
    print(f"anchor count == {n} (must be 1)")
    if n != 1:
        print("ABORT: anchor not unique.", file=sys.stderr)
        return 1

    patched = norm.replace(OLD, NEW, 1)

    exp_delta = NEW.count("\n") - OLD.count("\n")
    got_delta = patched.count("\n") - norm.count("\n")
    print(f"line delta expected {exp_delta}, got {got_delta}")
    if exp_delta != got_delta:
        print("ABORT: line delta mismatch.", file=sys.stderr)
        return 1

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"ABORT: ast.parse failed: {e}", file=sys.stderr)
        return 1
    print("ast.parse OK")

    if not args.apply:
        print("\nDRY RUN -- no write. Re-run with --apply.")
        return 0

    backup = target.with_name(target.name + "_PRE_S80")
    backup.write_bytes(raw)
    print(f"backup: {backup}")

    out = patched.replace("\n", eol) if eol != "\n" else patched
    target.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
