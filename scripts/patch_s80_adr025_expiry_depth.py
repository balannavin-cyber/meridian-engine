#!/usr/bin/env python3
"""patch_s80_adr025_expiry_depth.py

S80 / ADR-025 -- per-symbol expiry capture depth for ingest_option_chain_local.py.

APPEND, NOT RESTRUCTURE. The existing front-expiry block is untouched: W1 is
fetched, extracted, written and ENH-71-logged exactly as today. A second pass
is appended for the extra expiries, so:
  * at depth 1 the new block never executes -- stage 1 is provably inert
  * W1 is already committed before M1/M2 are attempted; a failure in the extra
    pass cannot cost the front expiry
  * the stdout "Run ID:" contract and record_write stay bound to W1 alone
    (EXPECTED_FLOOR is calibrated on one expiry)

Each extra expiry gets its OWN run_id: infer_expiry_date() now raises on a
multi-expiry run (TD-S79-NEW-12, patched S80) and build_gss_rows stamps one
expiry scalar per run.

Host-agnostic: TARGET defaults to <this script>/../ingest_option_chain_local.py,
so the same file runs on Local and on EC2 with no arguments. --target overrides.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, ast.parse
gate, _PRE_S80_EXPIRY backup (matches .gitignore *_PRE_S*), dry-run default
(--apply), count==1 anchors, idempotency marker.
"""
import argparse, ast, pathlib, sys

DEFAULT_TARGET = pathlib.Path(__file__).resolve().parent.parent / "ingest_option_chain_local.py"
MARKER = "S80 / ADR-025"

OLD_1 = (
    'SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")\n'
    'SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()\n'
)

NEW_1 = (
    'SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")\n'
    'SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()\n'
    '\n'
    '\n'
    '# S80 / ADR-025: per-symbol expiry capture depth.\n'
    '# Measured, not assumed -- hist_option_bars_1m, full day 2025-06-02, every\n'
    '# contract at peak OI. NIFTY W1/W2/M1/M2 = 94.45% of OI at 0/7/21/56 DTE,\n'
    '# while W3 carries 0.47% against the Dec quarterly 3.4%, so chronological\n'
    '# slicing takes the worthless expiry and misses the valuable one. SENSEX W1\n'
    '# alone is 97.25% and W1+W2 is 99.90%; its monthlies are dead (0.089%), so\n'
    '# depth 2 is its final answer.\n'
    '#\n'
    '# Deliberately a constant, NOT merdian_parameters: ingest is the head of the\n'
    '# pipeline and must not acquire a network read that can fail or silently fall\n'
    '# back to a default indistinguishable from a successful read (TD-S79-NEW-2\n'
    '# shape). Rollout is by git pull -- canonical, auditable, one-line commits.\n'
    '#\n'
    '#   stage 1  {"NIFTY": 1, "SENSEX": 1}  inert, behaviour identical to S79\n'
    '#   stage 2  {"NIFTY": 2, "SENSEX": 2}  non-expiry day, after stage 1 verified\n'
    '#   stage 3  {"NIFTY": 4, "SENSEX": 2}  after a week of ENH-99 retry telemetry\n'
    'EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}\n'
    '\n'
    '# Seconds between sequential option-chain calls. core/dhan_client.py has NO\n'
    '# proactive spacing -- all 429 handling is reactive, via retry_call and\n'
    '# is_dhan_429. TD-080 is S1-recurring (S22/S28/S29), so space the calls\n'
    '# rather than provoke a 429 and lean on the retry.\n'
    'EXPIRY_CALL_SPACING_S = 3.0\n'
    '\n'
    '\n'
    'def select_expiries(future_expiries: list[str], depth: int) -> list[str]:\n'
    '    """W1..W2 then the last expiry of each successive calendar month.\n'
    '\n'
    '    depth 1 -> [W1]; 2 -> [W1, W2]; 3 -> [W1, W2, M1]; 4 -> [W1, W2, M1, M2].\n'
    '    `future_expiries` must be sorted ascending. A monthly is the last expiry\n'
    '    falling within a calendar month. Returns a deduplicated ascending list,\n'
    '    shorter than `depth` when the vendor offers fewer. ADR-025.\n'
    '    """\n'
    '    if depth <= 0 or not future_expiries:\n'
    '        return []\n'
    '    picked: list[str] = list(future_expiries[: min(depth, 2)])\n'
    '    if depth > 2:\n'
    '        last_of_month: dict[str, str] = {}\n'
    '        for e in future_expiries:\n'
    '            last_of_month[e[:7]] = e\n'
    '        for key in sorted(last_of_month):\n'
    '            if len(picked) >= depth:\n'
    '                break\n'
    '            if last_of_month[key] not in picked:\n'
    '                picked.append(last_of_month[key])\n'
    '    return sorted(dict.fromkeys(picked))\n'
)

OLD_2 = (
    '    print("INGEST OPTION CHAIN COMPLETED")\n'
    '    return log.complete()\n'
)

NEW_2 = (
    '    # S80 / ADR-025 -- extra forward expiries, appended after W1 is committed.\n'
    '    _depth = EXPIRY_DEPTH.get(symbol.upper(), 1)\n'
    '    if _depth > 1:\n'
    '        import time as _time\n'
    '        _sorted = sorted({str(e) for e in future_expiries})\n'
    '        if _sorted and _sorted[0] != str(future_expiries[0]):\n'
    '            print(\n'
    '                f"WARN: vendor expiry list NOT sorted -- "\n'
    '                f"raw[0]={future_expiries[0]} sorted[0]={_sorted[0]}"\n'
    '            )\n'
    '        _extra = [e for e in select_expiries(_sorted, _depth) if e != expiry_date]\n'
    '        print(f"S80 extra expiries (depth={_depth}): {_extra}")\n'
    '        _captured: list[str] = []\n'
    '        _failed: list[str] = []\n'
    '        _extra_rows = 0\n'
    '        for _ed in _extra:\n'
    '            _time.sleep(EXPIRY_CALL_SPACING_S)\n'
    '            try:\n'
    '                _resp = retry_call(\n'
    '                    lambda ed=_ed: dhan.get_option_chain(\n'
    '                        underlying_scrip=underlying["UnderlyingScrip"],\n'
    '                        underlying_seg=underlying["UnderlyingSeg"],\n'
    '                        expiry=ed,\n'
    '                    ),\n'
    '                    attempts=6,\n'
    '                    delay_seconds=15.0,\n'
    '                    backoff_multiplier=1.5,\n'
    '                    retry_predicate=is_dhan_429,\n'
    '                    label=f"{symbol} get_option_chain {_ed}",\n'
    '                )\n'
    '                _rid = str(uuid.uuid4())\n'
    '                _rows = extract_option_rows(\n'
    '                    symbol=symbol,\n'
    '                    expiry_date=_ed,\n'
    '                    snapshot_ts=snapshot_ts,\n'
    '                    run_id=_rid,\n'
    '                    spot=spot,\n'
    '                    option_chain_response=_resp,\n'
    '                    mode=mode,\n'
    '                )\n'
    '                if not _rows:\n'
    '                    print(f"  {_ed}: 0 rows -- skipped")\n'
    '                    _failed.append(_ed)\n'
    '                    continue\n'
    '                retry_call(\n'
    '                    lambda r=_rows: sb.insert("option_chain_snapshots", r),\n'
    '                    attempts=3,\n'
    '                    delay_seconds=5.0,\n'
    '                    backoff_multiplier=1.5,\n'
    '                    label=f"{symbol} insert extra expiry {_ed}",\n'
    '                )\n'
    '                _captured.append(_ed)\n'
    '                _extra_rows += len(_rows)\n'
    '                print(f"  {_ed}: run_id={_rid} rows={len(_rows)} OK")\n'
    '            except Exception as _e:\n'
    '                print(f"  {_ed}: FAILED {type(_e).__name__}: {_e}")\n'
    '                _failed.append(_ed)\n'
    '        print(\n'
    '            f"S80 extra expiries captured={_captured} "\n'
    '            f"failed={_failed} rows={_extra_rows}"\n'
    '        )\n'
    '\n'
    '    print("INGEST OPTION CHAIN COMPLETED")\n'
    '    return log.complete()\n'
)

SUBS = [("constants + select_expiries", OLD_1, NEW_1),
        ("extra-expiry capture block", OLD_2, NEW_2)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write; default is dry-run")
    ap.add_argument("--target", default=str(DEFAULT_TARGET),
                    help="file to patch (default: repo-root sibling of scripts/)")
    args = ap.parse_args()

    target = pathlib.Path(args.target)
    print(f"target: {target}")
    if not target.is_file():
        print("ABORT: target not found.", file=sys.stderr)
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
    patched = norm
    total_expected = 0

    for label, old, new in SUBS:
        n = patched.count(old)
        print(f"[{label}] anchor count == {n} (must be 1)")
        if n != 1:
            print(f"ABORT: anchor not unique for {label}.", file=sys.stderr)
            return 1
        patched = patched.replace(old, new, 1)
        total_expected += new.count("\n") - old.count("\n")

    got = patched.count("\n") - norm.count("\n")
    print(f"line delta expected {total_expected}, got {got}")
    if total_expected != got:
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

    backup = target.with_name(target.name + "_PRE_S80_EXPIRY")
    backup.write_bytes(raw)
    print(f"backup: {backup}")

    out = patched.replace("\n", eol) if eol != "\n" else patched
    target.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
