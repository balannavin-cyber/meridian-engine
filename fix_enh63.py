"""
MERDIAN ENH-63 patch -- detect_ict_patterns_runner.py (v3).
Track A. ASCII patch source, operates on UTF-8 target.

Two changes:
1. Delete duplicate section. Anchors confirmed against actual bytes of
   the target file (user's dump, 2026-04-19):
     - keep line: "    # -- ENH-38v2 end ----..." (marks end of V2 block,
       last line we keep before the cut)
     - cut starts at the NEXT line (blank / duplicate begins)
     - cut ends at the line ABOVE the surviving tail
     - surviving tail line (unique): '    log(f"ICT detector complete
       [{symbol}]")' -- keep this and everything after
2. Add _EXPIRY_INDEX_CACHE at module scope after HOURLY_ZONE_WINDOW...
3. Wrap build_expiry_index_simple call with cache lookup.

Implementation: find the line indexes of the two boundary anchors, then
splice. Avoids fragile dash-run matching entirely.
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


# Line-precise anchors (rstrip'd, no trailing newline in the string).
V2_END_LINE = "    # -- ENH-38v2 end ----------------------------------------------------------"
V1_HEADER_LINE = "    # -- ENH-38: write Kelly lots to active ict_zones --------------------"
MAIN_TAIL_LINE = '    log(f"ICT detector complete [{symbol}]")'


CACHE_DECL_OLD = (
    "# Hour boundary check: run 1H zone builder if within first 3 minutes of hour\n"
    "HOURLY_ZONE_WINDOW_MINUTES = 3\n"
)

CACHE_DECL_NEW = (
    "# Hour boundary check: run 1H zone builder if within first 3 minutes of hour\n"
    "HOURLY_ZONE_WINDOW_MINUTES = 3\n"
    "\n"
    "# ENH-63: process-lifetime cache for expiry index.\n"
    "# build_expiry_index_simple issues 12 paginated Supabase queries per call.\n"
    "# Expiry dates are near-static -- per-process caching (vs per-cycle rebuild)\n"
    "# cuts daily query volume from ~1,728 to 1 per symbol.\n"
    "_EXPIRY_INDEX_CACHE: dict = {}\n"
)


CACHE_CALL_OLD = (
    "        try:\n"
    "            _expiry_idx = build_expiry_index_simple(sb, inst_id)\n"
    "            _next_exp   = nearest_expiry_db(trade_date, _expiry_idx)\n"
    "            _dte_days   = (_next_exp - trade_date).days if _next_exp else 2\n"
    "        except Exception:\n"
    "            _dte_days = 2   # conservative fallback\n"
)

CACHE_CALL_NEW = (
    "        try:\n"
    "            _expiry_idx = _EXPIRY_INDEX_CACHE.get(inst_id)\n"
    "            if _expiry_idx is None:\n"
    "                _expiry_idx = build_expiry_index_simple(sb, inst_id)\n"
    "                _EXPIRY_INDEX_CACHE[inst_id] = _expiry_idx\n"
    "            _next_exp = nearest_expiry_db(trade_date, _expiry_idx)\n"
    "            _dte_days = (_next_exp - trade_date).days if _next_exp else 2\n"
    "        except Exception:\n"
    "            _dte_days = 2   # conservative fallback\n"
)


def splice_duplicate(text: str) -> tuple[str, dict]:
    """
    Find the three line anchors and return text with the duplicate block
    spliced out. Keeps everything up to and including V2_END_LINE, keeps
    everything from MAIN_TAIL_LINE onward, discards what's between.
    """
    lines = text.splitlines(keepends=True)

    v2_line_idx = None
    v1_header_idx = None
    main_tail_idx = None

    for i, raw in enumerate(lines):
        line = raw.rstrip("\r\n")
        if line == V2_END_LINE and v2_line_idx is None:
            v2_line_idx = i
        elif line == V1_HEADER_LINE and v1_header_idx is None:
            v1_header_idx = i
        elif line == MAIN_TAIL_LINE and main_tail_idx is None:
            main_tail_idx = i

    info = {
        "v2_line_idx": v2_line_idx,
        "v1_header_idx": v1_header_idx,
        "main_tail_idx": main_tail_idx,
        "total_lines": len(lines),
    }

    if v2_line_idx is None:
        raise RuntimeError(f"V2 end line not found: {V2_END_LINE!r}")
    if v1_header_idx is None:
        raise RuntimeError(f"V1 header line not found: {V1_HEADER_LINE!r}")
    if main_tail_idx is None:
        raise RuntimeError(f"Main tail line not found: {MAIN_TAIL_LINE!r}")

    # Ordering sanity: v2 < v1 < main_tail
    if not (v2_line_idx < v1_header_idx < main_tail_idx):
        raise RuntimeError(
            f"Unexpected line order: v2={v2_line_idx+1}, v1={v1_header_idx+1}, "
            f"main_tail={main_tail_idx+1}"
        )

    # Require exactly one of each
    for anchor, name in [(V2_END_LINE, "V2_END_LINE"),
                         (V1_HEADER_LINE, "V1_HEADER_LINE"),
                         (MAIN_TAIL_LINE, "MAIN_TAIL_LINE")]:
        count = sum(1 for raw in lines if raw.rstrip("\r\n") == anchor)
        if count != 1:
            raise RuntimeError(f"{name} occurs {count} times (need 1)")

    # Keep lines[0 .. v2_line_idx] inclusive.
    # Keep lines[main_tail_idx .. end].
    # Everything between is the duplicate + V1 block.
    kept_head = lines[: v2_line_idx + 1]
    kept_tail = lines[main_tail_idx:]

    # Ensure there's a blank line between V2 end and the tail for
    # visual separation. The V2_END_LINE itself ends with \n so we
    # just prepend "\n" to the tail.
    result = "".join(kept_head) + "\n" + "".join(kept_tail)
    info["deleted_lines"] = main_tail_idx - (v2_line_idx + 1)
    return result, info


def apply_patch(text: str) -> tuple[str, dict]:
    if "_EXPIRY_INDEX_CACHE" in text:
        raise RuntimeError("ENH-63 already applied (cache decl present).")

    patched, info = splice_duplicate(text)

    if CACHE_DECL_OLD not in patched:
        raise RuntimeError("Cache-decl anchor not found.")
    if patched.count(CACHE_DECL_OLD) != 1:
        raise RuntimeError(
            f"Cache-decl anchor matched {patched.count(CACHE_DECL_OLD)} times."
        )
    patched = patched.replace(CACHE_DECL_OLD, CACHE_DECL_NEW, 1)

    if CACHE_CALL_OLD not in patched:
        raise RuntimeError("Cache-call anchor not found (build_expiry_index_simple).")
    if patched.count(CACHE_CALL_OLD) != 1:
        raise RuntimeError(
            f"Cache-call anchor matched {patched.count(CACHE_CALL_OLD)} times."
        )
    patched = patched.replace(CACHE_CALL_OLD, CACHE_CALL_NEW, 1)

    return patched, info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="detect_ict_patterns_runner.py")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax: {e}", file=sys.stderr)
        return 1

    target = Path(args.target)
    if not target.exists():
        print(f"FAIL: target not found: {target.resolve()}", file=sys.stderr)
        return 2

    original = target.read_text(encoding="utf-8")

    try:
        ast.parse(original)
    except SyntaxError as e:
        print(f"FAIL: target has SyntaxError: {e}", file=sys.stderr)
        return 3

    try:
        patched, info = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 4

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"FAIL: patched file SyntaxError: {e}", file=sys.stderr)
        return 5

    # Structural post-checks
    for needle, label in [
        ("_EXPIRY_INDEX_CACHE: dict = {}", "cache declaration"),
        ("_EXPIRY_INDEX_CACHE.get(inst_id)", "cache lookup"),
        ("_EXPIRY_INDEX_CACHE[inst_id] = _expiry_idx", "cache store"),
    ]:
        if needle not in patched:
            print(f"FAIL: missing: {label}", file=sys.stderr)
            return 6

    if V1_HEADER_LINE in patched:
        print("FAIL: legacy V1 Kelly header still present", file=sys.stderr)
        return 7

    # V2 end marker must remain, exactly once
    if patched.count("# -- ENH-38v2 end --") != 1:
        print("FAIL: V2 end marker not unique post-patch", file=sys.stderr)
        return 8

    # Exactly ONE "Session start: expire prior zones" block in result
    dup_count = patched.count("Session start: expire prior zones")
    if dup_count != 1:
        print(f"FAIL: 'Session start' count = {dup_count}, expected 1",
              file=sys.stderr)
        return 9

    # Exactly three compute_kelly_lots calls in result (T1, T2, T3, IV-aware)
    kelly_calls = patched.count("compute_kelly_lots(_current_capital,")
    if kelly_calls != 3:
        print(f"FAIL: compute_kelly_lots call count = {kelly_calls}, expected 3",
              file=sys.stderr)
        return 10

    orig_lines = original.count("\n")
    new_lines = patched.count("\n")

    print(f"target:   {target.resolve()}")
    print(f"mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:   {'off' if args.no_backup else 'on'}")
    print(f"size:     {len(original)} -> {len(patched)} bytes "
          f"({len(patched)-len(original):+d})")
    print(f"lines:    {orig_lines} -> {new_lines} ({new_lines-orig_lines:+d})")
    print(f"anchors:  V2 end @ line {info['v2_line_idx']+1}, "
          f"V1 header @ line {info['v1_header_idx']+1}, "
          f"main tail @ line {info['main_tail_idx']+1}")
    print(f"spliced:  {info['deleted_lines']} duplicate lines removed")
    print()
    print("Edits:")
    print("  [ENH-63/1] Deleted duplicate Kelly block + repeated main body")
    print("  [ENH-63/2] Added _EXPIRY_INDEX_CACHE at module scope")
    print("  [ENH-63/3] Wrapped build_expiry_index_simple with cache lookup")

    if args.dry_run:
        print()
        print("DRY RUN - nothing written.")
        return 0

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre_enh63.bak")
        shutil.copy2(target, backup)
        print(f"backup:   {backup.name}")

    target.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
