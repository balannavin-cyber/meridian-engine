#!/usr/bin/env python3
r"""
fix_td071_zone_pipeline_order.py

TD-071 — fix expire_old_zones() ordering and behavior.

Spec (locked Session 21, 2026-05-06):
  1. Move expire_old_zones() from BEFORE upserts to AFTER recheck_breached_zones().
     Old order: expire -> upsert(W) -> upsert(D) -> recheck
     New order: upsert(W) -> upsert(D) -> recheck -> expire
     This restores the canonical pipeline so expire-by-date sweeps the post-recheck
     state instead of operating on the previous run's stale data.
  2. Widen expire_old_zones() to be status-agnostic, so BREACHED zones past
     valid_to also become EXPIRED. Date is the semantic check, not status.
  3. Restrict expire_old_zones() to W and D timeframes only. H (intraday) zones
     use 1-day validity and a different expiry basis (deferred — see TD-050).
  4. Add idempotency guard so already-EXPIRED rows are not rewritten.

Backward-compat:
  - For ACTIVE zones with valid_to < today: behavior is identical (still expired).
  - For BREACHED zones with valid_to < today: now expires (was: stayed BREACHED).
  - For H zones: now never touched by this function (was: expired daily).

Stacked-patch note: this patch operates on the post-TD-070 canonical
build_ict_htf_zones.py. Anchors used here are independent of TD-070's changes
(detect_weekly_zones() body) — no collision.

v3 patch canon:
  - read_bytes() + decode('utf-8-sig') for BOM
  - normalize CRLF -> LF before anchor match
  - ast.parse() validate before write
  - idempotency guard (TD071_PATCH_MARKER)
  - write_bytes(text.encode(enc)) to preserve LF
  - emits a _PATCHED_TD071.py file; operator renames to canonical post-review.

Usage:
    python fix_td071_zone_pipeline_order.py [--in PATH] [--out PATH] [--check]

Exit codes:
    0  success / already patched (idempotent)
    2  source not found / unreadable
    3  anchor blocks not found (file content drifted)
    4  ast.parse failed on patched output
    5  other
"""

from __future__ import annotations
import argparse
import ast
import sys
from pathlib import Path

DEFAULT_IN = r"C:\GammaEnginePython\build_ict_htf_zones.py"

# Marker that proves the patch has been applied (idempotency check).
TD071_PATCH_MARKER = "TD-071 (Session 21)"

# ---------- Anchor 1: expire_old_zones() function body (full replace) ----

OLD_EXPIRE_FN = '''\
def expire_old_zones(sb, symbol, today, dry_run=False):
    """
    Mark zones with valid_to < today as EXPIRED.
    """
    if dry_run:
        log("  DRY RUN — would expire old zones")
        return

    try:
        sb.table("ict_htf_zones").update({
            "status": "EXPIRED",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("symbol", symbol).lt(
            "valid_to", str(today)
        ).eq("status", "ACTIVE").execute()
        log(f"  Expired old {symbol} zones before {today}")
    except Exception as e:
        log(f"  Warning: could not expire old zones: {e}")
'''

NEW_EXPIRE_FN = '''\
def expire_old_zones(sb, symbol, today, dry_run=False):
    """
    Mark W and D zones with valid_to < today as EXPIRED.

    TD-071 (Session 21, 2026-05-06):
      - Widened from ACTIVE-only to status-agnostic. BREACHED zones past
        valid_to now correctly transition to EXPIRED instead of staying
        BREACHED forever (date is the semantic check, not status).
      - Restricted to W and D timeframes. H (intraday) zones use 1-day
        validity (valid_to = trade_date); their expiry basis is unclear
        and intentionally not handled here. See TD-050.
      - Added .neq("status", "EXPIRED") idempotency guard so rerunning
        does not bump updated_at on already-expired rows.
    """
    if dry_run:
        log("  DRY RUN — would expire old W/D zones (status-agnostic)")
        return

    try:
        sb.table("ict_htf_zones").update({
            "status": "EXPIRED",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("symbol", symbol).lt(
            "valid_to", str(today)
        ).in_(
            "timeframe", ["W", "D"]
        ).neq(
            "status", "EXPIRED"
        ).execute()
        log(f"  Expired old W/D {symbol} zones before {today}")
    except Exception as e:
        log(f"  Warning: could not expire old zones: {e}")
'''

# ---------- Anchor 2: pipeline order in main() — remove leading expire ----

OLD_PIPELINE_PRE_EXPIRE = '''\
        expire_old_zones(sb, symbol, target_date, dry_run)

        lookback_days = max(WEEKLY_LOOKBACK * 7 + 7, DAILY_LOOKBACK + 3)
'''

NEW_PIPELINE_PRE_EXPIRE = '''\
        # TD-071 (Session 21): expire_old_zones moved to AFTER recheck.
        # Old order (expire-first) operated on stale data, leaving
        # BREACHED zones past valid_to permanently BREACHED. New order
        # is detect -> upsert(ACTIVE) -> recheck(price-breach) -> expire(date).

        lookback_days = max(WEEKLY_LOOKBACK * 7 + 7, DAILY_LOOKBACK + 3)
'''

# ---------- Anchor 3: pipeline order in main() — append trailing expire ----

OLD_PIPELINE_POST_RECHECK = '''\
        # TD-030 fix (reordered): recheck AFTER upserts so status=ACTIVE
        # upsert does not overwrite BREACHED set by recheck.
        recheck_breached_zones(sb, symbol, daily_ohlcv, str(target_date), dry_run)

    log(f"Done -- {total_written} total zones written to ict_htf_zones")
'''

NEW_PIPELINE_POST_RECHECK = '''\
        # TD-030 fix (reordered): recheck AFTER upserts so status=ACTIVE
        # upsert does not overwrite BREACHED set by recheck.
        recheck_breached_zones(sb, symbol, daily_ohlcv, str(target_date), dry_run)

        # TD-071 (Session 21): expire-by-date runs LAST, against ALL zones
        # (both ACTIVE and BREACHED). Restricted to W/D timeframes.
        expire_old_zones(sb, symbol, target_date, dry_run)

    log(f"Done -- {total_written} total zones written to ict_htf_zones")
'''

# ---------- Patch driver ----------


def _read_source(path: Path) -> tuple[str, str]:
    if not path.is_file():
        print(f"[ERROR] source not found: {path}", file=sys.stderr)
        sys.exit(2)
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    enc = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    text_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    return text_lf, enc


def _is_already_patched(text: str) -> bool:
    return TD071_PATCH_MARKER in text


def _verify_anchors(text: str) -> None:
    checks = [
        ("OLD_EXPIRE_FN", OLD_EXPIRE_FN),
        ("OLD_PIPELINE_PRE_EXPIRE", OLD_PIPELINE_PRE_EXPIRE),
        ("OLD_PIPELINE_POST_RECHECK", OLD_PIPELINE_POST_RECHECK),
    ]
    for name, anchor in checks:
        n = text.count(anchor)
        if n != 1:
            print(f"[ERROR] anchor {name} must appear exactly once, "
                  f"found {n}.", file=sys.stderr)
            sys.exit(3)


def _apply_patch(text: str) -> str:
    text = text.replace(OLD_EXPIRE_FN, NEW_EXPIRE_FN, 1)
    text = text.replace(OLD_PIPELINE_PRE_EXPIRE, NEW_PIPELINE_PRE_EXPIRE, 1)
    text = text.replace(OLD_PIPELINE_POST_RECHECK,
                        NEW_PIPELINE_POST_RECHECK, 1)
    return text


def _validate_python(text: str) -> None:
    try:
        ast.parse(text)
    except SyntaxError as e:
        print(f"[ERROR] ast.parse failed on patched text: {e}",
              file=sys.stderr)
        sys.exit(4)


def main() -> int:
    p = argparse.ArgumentParser(description="TD-071 patch")
    p.add_argument("--in",  dest="src",  default=DEFAULT_IN,
                   help=f"source file (default: {DEFAULT_IN})")
    p.add_argument("--out", dest="dst",  default=None,
                   help="output path (default: <src>_PATCHED_TD071.py)")
    p.add_argument("--check", action="store_true",
                   help="validate only; do not write")
    args = p.parse_args()

    src = Path(args.src)
    if args.dst is None:
        dst = src.with_name(src.stem + "_PATCHED_TD071.py")
    else:
        dst = Path(args.dst)

    text_lf, enc = _read_source(src)

    if _is_already_patched(text_lf):
        print(f"[OK] already patched ({TD071_PATCH_MARKER!r} present): "
              f"{src}")
        return 0

    _verify_anchors(text_lf)
    patched = _apply_patch(text_lf)

    if not _is_already_patched(patched):
        print("[ERROR] post-patch idempotency marker missing.",
              file=sys.stderr)
        return 5
    if OLD_EXPIRE_FN in patched:
        print("[ERROR] old expire_old_zones() body still present.",
              file=sys.stderr)
        return 5
    if OLD_PIPELINE_PRE_EXPIRE in patched:
        print("[ERROR] old pre-expire pipeline block still present.",
              file=sys.stderr)
        return 5
    if OLD_PIPELINE_POST_RECHECK in patched:
        print("[ERROR] old post-recheck pipeline block still present.",
              file=sys.stderr)
        return 5

    _validate_python(patched)

    if args.check:
        print("[OK] check: anchors found, patch would apply, ast.parse OK.")
        return 0

    dst.write_bytes(patched.encode(enc.replace("-sig", "")))
    print(f"[OK] wrote {dst}")
    print(f"     bytes:    {len(patched.encode('utf-8')):,}")
    print(f"     encoding: {enc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
