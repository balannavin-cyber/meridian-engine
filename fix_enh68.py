"""
ENH-68 (tactical, Option B): Runner re-reads .env at the start of every cycle.

Problem (root cause of today's 60-minute outage from 11:26 to 12:26 IST):
  run_option_snapshot_intraday_runner.py loads environment variables once at
  process startup. Child scripts (ingest_option_chain_local.py, etc) spawn
  fresh processes each cycle and therefore see the current .env -- but the
  runner process itself holds its DHAN_API_TOKEN snapshot in memory. When
  refresh_dhan_token.py rewrites .env mid-session, runner does not see it.

  That does not matter today because the runner currently does not read the
  token directly -- it's the child scripts that call Dhan. However:
    (a) The runner does execute its own Telegram alert via urllib, reading
        TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID from os.environ on each send;
        if those are ever rotated mid-session, current behaviour is stale.
    (b) Any future code in the runner that reads env (logging, feature flags,
        capital caps, etc) would inherit the same bug.
    (c) When Option D (core/live_config.py) lands, having a clean "env was
        reloaded at N:NN" log-line for every cycle provides an audit trail
        for config rotation events.

  Most importantly: this fix stops today's exact bug class. Tomorrow, if a
  token refresh happens during market hours, the runner's *next* cycle
  (<=5 minutes later) will spawn children with the new token without any
  human intervention. No more stop/start rituals.

Fix:
  1. Import load_dotenv at top of module (alongside existing imports).
  2. At the top of run_full_cycle(), before any child dispatch, call
     load_dotenv(override=True, dotenv_path=BASE_DIR / ".env") and log the
     reload event (so we have an audit trail).
  3. If python-dotenv is unavailable for some reason, log a warning but do
     not fail -- graceful degradation.

Strategic direction:
  This is a tactical stopgap. Session 5 of the re-engineering programme
  introduces core/live_config.py which replaces per-cycle reload with
  per-access TTL-cached reads. When that lands, this patch is removed.
  The ExecutionLog (Session 2) will record the reload event structurally.

Target: run_option_snapshot_intraday_runner.py
Validation: ast.parse() on patched file, plus structural marker count.
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


TARGET_DEFAULT = r"C:\GammaEnginePython\run_option_snapshot_intraday_runner.py"


# ---------------------------------------------------------------------------
# Edit 1: Add dotenv import near existing stdlib imports. Anchor is the
# "from pathlib import Path" line. We insert an import just after
# "from zoneinfo import ZoneInfo" because that is already the last
# stdlib/third-party import before the project-local imports start.
# ---------------------------------------------------------------------------

EDIT1_OLD = '''from zoneinfo import ZoneInfo

from trading_calendar import ('''

EDIT1_NEW = '''from zoneinfo import ZoneInfo

try:
    # ENH-68 tactical: per-cycle env reload. See run_full_cycle().
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    _load_dotenv = None  # Graceful degradation; we warn once at first use.

from trading_calendar import ('''


# ---------------------------------------------------------------------------
# Edit 2: Insert env reload call at the top of run_full_cycle(), before the
# "CYCLE START" log banner. We anchor on the exact three lines that open the
# function so the placement is unambiguous.
# ---------------------------------------------------------------------------

EDIT2_OLD = '''def run_full_cycle() -> None:
    cycle_started = now_ist()
    log("==================================================")
    log("CYCLE START")
    log("==================================================")'''

EDIT2_NEW = '''def run_full_cycle() -> None:
    cycle_started = now_ist()

    # ── ENH-68 tactical: reload .env at the top of every cycle ──────────────
    # Root cause of 2026-04-20 11:26-12:26 outage: runner process held a
    # stale DHAN_API_TOKEN snapshot after refresh_dhan_token.py rewrote .env
    # mid-session. Reloading here picks up any rotated credentials / flags
    # within <=5 minutes of the .env change, with no runner restart needed.
    # Strategic replacement (Session 5): core/live_config.py. Remove then.
    if _load_dotenv is not None:
        try:
            _load_dotenv(dotenv_path=str(BASE_DIR / ".env"), override=True)
            log("ENH-68: .env reloaded for this cycle (override=True)")
        except Exception as _reload_exc:
            log(f"ENH-68: .env reload failed (non-blocking): {_reload_exc}")
    else:
        log("ENH-68: python-dotenv not installed; .env reload skipped")
    # ── End ENH-68 reload ───────────────────────────────────────────────────

    log("==================================================")
    log("CYCLE START")
    log("==================================================")'''


def apply_patch(text: str) -> str:
    # Idempotence guard: the tag "ENH-68" should not already be in the file.
    if "ENH-68" in text:
        raise RuntimeError("ENH-68 marker already present in file. Refusing to re-patch.")

    c1 = text.count(EDIT1_OLD)
    if c1 != 1:
        raise RuntimeError(f"Edit 1 (import) anchor matched {c1} times (need exactly 1).")
    text = text.replace(EDIT1_OLD, EDIT1_NEW, 1)

    c2 = text.count(EDIT2_OLD)
    if c2 != 1:
        raise RuntimeError(f"Edit 2 (reload call) anchor matched {c2} times (need exactly 1).")
    text = text.replace(EDIT2_OLD, EDIT2_NEW, 1)

    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    # Self-syntax check
    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax: {e}", file=sys.stderr)
        return 1

    target = Path(args.target)
    if not target.exists():
        print(f"FAIL: target not found: {target.resolve()}", file=sys.stderr)
        return 2

    # Read with utf-8-sig so a leading BOM is stripped on read.
    original = target.read_text(encoding="utf-8-sig")
    had_bom = target.read_bytes().startswith(b"\xef\xbb\xbf")

    try:
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 3

    # Syntax check on patched content before writing.
    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"FAIL: patched file does not parse: {e}", file=sys.stderr)
        return 4

    # Structural sanity.
    enh68_count = patched.count("ENH-68")
    if enh68_count < 4:
        print(
            f"FAIL: expected >=4 ENH-68 markers in patched file, found {enh68_count}",
            file=sys.stderr,
        )
        return 5

    orig_lines = original.count("\n")
    new_lines = patched.count("\n")

    print(f"target:   {target.resolve()}")
    print(f"mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:   {'off' if args.no_backup else 'on'}")
    print(f"BOM:      {'present -> will strip' if had_bom else 'none'}")
    print(f"size:     {len(original)} -> {len(patched)} bytes ({len(patched)-len(original):+d})")
    print(f"lines:    {orig_lines} -> {new_lines} ({new_lines-orig_lines:+d})")
    print()
    print("Edits:")
    print("  [ENH-68/1] Import:  from dotenv import load_dotenv (as _load_dotenv)")
    print("  [ENH-68/2] Runtime: reload .env at top of run_full_cycle()")

    if args.dry_run:
        print()
        print("DRY RUN - nothing written.")
        return 0

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre_enh68.bak")
        shutil.copy2(target, backup)
        print(f"backup:   {backup.name}")

    target.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
