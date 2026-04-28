"""
MERDIAN dashboard created_at tiebreak fix (v3).
Track A, not BREAKING. ASCII-only, anchored on function bodies for
unambiguous match.
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


# fetch_signal: the long select list, ending with the order+limit chain.
FETCH_SIGNAL_OLD = '''def fetch_signal(sym):
    r = _q(lambda: sb.table("signal_snapshots")
        .select("ts,action,trade_allowed,confidence_score,spot,atm_strike,"
                "expiry_date,dte,atm_iv_avg,gamma_regime,breadth_regime,"
                "india_vix,ict_pattern,ict_tier,ict_mtf_context,"
                "ict_lots_t1,ict_lots_t2,ict_lots_t3")
        .eq("symbol", sym).order("ts", desc=True).limit(1).execute().data)
    return r[0] if r else None'''

FETCH_SIGNAL_NEW = '''def fetch_signal(sym):
    r = _q(lambda: sb.table("signal_snapshots")
        .select("ts,action,trade_allowed,confidence_score,spot,atm_strike,"
                "expiry_date,dte,atm_iv_avg,gamma_regime,breadth_regime,"
                "india_vix,ict_pattern,ict_tier,ict_mtf_context,"
                "ict_lots_t1,ict_lots_t2,ict_lots_t3")
        .eq("symbol", sym).order("ts", desc=True).order("created_at", desc=True).limit(1).execute().data)
    return r[0] if r else None'''


# fetch_spot: short, distinctive two-field select.
FETCH_SPOT_OLD = '''def fetch_spot(sym):
    r = _q(lambda: sb.table("signal_snapshots")
        .select("spot,ts").eq("symbol", sym)
        .order("ts", desc=True).limit(1).execute().data)
    return r[0] if r else None'''

FETCH_SPOT_NEW = '''def fetch_spot(sym):
    r = _q(lambda: sb.table("signal_snapshots")
        .select("spot,ts").eq("symbol", sym)
        .order("ts", desc=True).order("created_at", desc=True).limit(1).execute().data)
    return r[0] if r else None'''


def apply_patch(text: str) -> str:
    if 'order("created_at", desc=True)' in text:
        raise RuntimeError("Dashboard already patched.")

    sig_hits = text.count(FETCH_SIGNAL_OLD)
    spot_hits = text.count(FETCH_SPOT_OLD)

    if sig_hits != 1:
        raise RuntimeError(f"fetch_signal anchor: {sig_hits} hits (need 1)")
    if spot_hits != 1:
        raise RuntimeError(f"fetch_spot anchor: {spot_hits} hits (need 1)")

    text = text.replace(FETCH_SIGNAL_OLD, FETCH_SIGNAL_NEW, 1)
    text = text.replace(FETCH_SPOT_OLD, FETCH_SPOT_NEW, 1)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="merdian_signal_dashboard.py")
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
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 4

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"FAIL: patched SyntaxError: {e}", file=sys.stderr)
        return 5

    sites = patched.count('order("created_at", desc=True)')
    if sites != 2:
        print(f"FAIL: expected 2 tiebreak sites, got {sites}", file=sys.stderr)
        return 6

    print(f"target:   {target.resolve()}")
    print(f"mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:   {'off' if args.no_backup else 'on'}")
    print(f"size:     {len(original)} -> {len(patched)} (+{len(patched)-len(original)})")
    print(f"sites:    {sites}")
    print()
    print("Edits:")
    print("  fetch_signal(): add .order('created_at', desc=True)")
    print("  fetch_spot():   add .order('created_at', desc=True)")

    if args.dry_run:
        print()
        print("DRY RUN - nothing written.")
        return 0

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre_tiebreak.bak")
        shutil.copy2(target, backup)
        print(f"backup:   {backup.name}")

    target.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
