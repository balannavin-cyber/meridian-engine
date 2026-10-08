#!/usr/bin/env python3
"""
patch_s92_contract_gate_dedupe.py -- S92, TD-S91-NEW-13 + TD-S91-NEW-14.

WHAT, in validate_compute_contracts.py only
  13: a trading-day gate (exit 0 before any check on a non-trading day) and a
      30-minute PER-KEY dedupe around all four send sites. Both halves REUSE
      6a5c0e2's helpers -- monitor_orchestrator_health._default_is_trading_day,
      .AlertState, .DEDUPE_MIN -- imported lazily, never re-implemented
      (CLAUDE.md rule 18: never roll a new inline calendar gate).
  14: the :170 message said "skipping this cycle". The script skips nothing, so
      the text now states what actually happens. NO skip control is added --
      that is the other half of the TD and needs its own ruling.

THE "NOTHING CONSUMES IT" CLAIM -- ENUMERATED, not inferred from the crontab
  The first draft of the :170 text asserted "nothing consumes its exit code" on
  the strength of aws_crontab.txt and `crontab -l` alone. That is exactly the
  TD-S91-NEW-2 site-7 scope gap (a grep scoped to the crontab could not see a
  script reached as an orchestrator STEP). Walked before keeping the text:
    - orchestrator step list: run_merdian_shadow_runner_aws.py execute_pipeline
      builds `steps` at :230-287. validate_compute_contracts.py is NOT in it.
      (compute_basis_context_local.py IS, at :273 -- so the step list was read,
      not assumed empty.)
    - shell wrappers / units: `grep -rl` over the engine tree for *.sh, *.py,
      *.service, *.timer, *.conf matches ONE file -- the script itself.
    - systemd: no unit under /etc/systemd/system references it.
    - other crontabs: /var/spool/cron/crontabs holds only `ssm-user`, and
      /etc/cron.d holds only e2scrub_all; no match in /etc/crontab or
      /etc/cron.{daily,hourly}.
    - the log: `logs/contract_check.log` appears only on the cron line that
      writes it. Nothing reads it.
  So the claim HOLDS, and the text now states the measured form -- "no scheduled
  consumer reads its exit code" -- rather than a universal.
  WHAT THIS CANNOT SEE, stated with the verdict: a dynamically constructed
  invocation (no literal filename to grep), and the Local Windows Task Scheduler,
  which is not visible from this host. The second is bounded by the script's own
  `sys.path.insert(0, '/home/ssm-user/meridian-engine')` at :23 -- a Linux path,
  so it is AWS-only by construction.

ENCODING -- this target is the BOM case
  validate_compute_contracts.py carries a UTF-8 BOM (measured: bytes 0-2 are
  EF BB BF). read_bytes + decode('utf-8-sig') and write_bytes(enc='utf-8-sig')
  round-trips it; Path.read_text('utf-8') + ast.parse would fail on U+FEFF.
  It also holds PRE-EXISTING mojibake ('\\u00e2\\u20ac\\u201d' for an em dash, at
  :3 and :171, and '\\u00e2\\u201a\\u00b9' for a rupee sign at :107). Operator
  instruction: LEAVE THE MOJIBAKE ALONE. This script touches none of it, with one
  unavoidable consequence stated plainly: the :171 instance sits inside the
  message string that TD-S91-NEW-14 requires be rewritten, so it goes with the
  sentence. The :3 and :107 instances are untouched, and the count is asserted
  (2 -> 1) rather than hoped for. Anchors spell the mojibake as \\u escapes so
  this patch file stays pure ASCII.

CANON-V3 (.claude/rules/python-writers.md)
  read_bytes + decode('utf-8-sig') | BOM round-tripped via enc | predominant EOL
  restored on write | anchors matched in LF-space | every anchor count==1 or
  ABORT | ast.parse gate before write | <name>_PRE_S92 backup | dry-run default,
  --apply required | ONE idempotency marker gating the whole entry | summary
  COMPUTED from the per-edit results, never a literal.

USAGE
  python3 scratch/s92/patch_s92_contract_gate_dedupe.py            # dry run
  python3 scratch/s92/patch_s92_contract_gate_dedupe.py --apply

ROLLBACK
  cp validate_compute_contracts.py_PRE_S92 validate_compute_contracts.py
  or: git checkout -- validate_compute_contracts.py   (pre-commit)
  or: git revert <sha>                                (post-commit; no DDL, no
      state migration -- logs/contract_alert_state.json is created by the new
      code and is inert if the code is reverted; delete it if you want it gone)
"""
from __future__ import annotations

import ast
import difflib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGET = REPO / "validate_compute_contracts.py"
BACKUP = TARGET.with_name(TARGET.name + "_PRE_S92")
MARKER = "S92-CONTRACT-GATE"

# The mojibake, as escapes, so this file is ASCII. U+00E2 U+20AC U+201D.
MOJI_EMDASH = "â€”"

# ---- edit 1: Path import ----------------------------------------------------
E1_OLD = """from datetime import datetime, timedelta
from typing import Dict, Tuple
"""
E1_NEW = """from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple
"""

# ---- edit 2: the gate + dedupe helpers --------------------------------------
E2_OLD = """except ImportError:
    def send_alert(*args, **kwargs): return False
    def send_critical(*args, **kwargs): return False
    def send_warning(*args, **kwargs): return False

SUPABASE_URL = os.getenv('SUPABASE_URL')
"""
E2_NEW = """except ImportError:
    def send_alert(*args, **kwargs): return False
    def send_critical(*args, **kwargs): return False
    def send_warning(*args, **kwargs): return False

# ---- S92-CONTRACT-GATE: trading-day gate + per-key send dedupe --------------------
# TD-S91-NEW-13. Both halves REUSE the helpers 6a5c0e2 added to
# monitor_orchestrator_health.py rather than re-implementing them (CLAUDE.md rule 18:
# never roll a new inline calendar gate).
#
# They are imported LAZILY, inside the functions below, for two reasons that are not
# style: monitor_orchestrator_health calls load_dotenv() and sys.path.insert() at
# MODULE scope, and an ImportError must not be able to stop this validator alerting.
#
# The crontab window gate the monitor needed is already supplied here by this script's
# own cron line (4,9,...,59 03-09 * * 1-5), so only the calendar gate and the dedupe
# are added. Nothing here changes which contracts are checked or their thresholds.

_DEDUPE_FALLBACK_MIN = 30  # used only if monitor_orchestrator_health.DEDUPE_MIN is unreadable
_STATE_PATH = Path(__file__).resolve().parent / 'logs' / 'contract_alert_state.json'


def _is_trading_day() -> bool:
    \"\"\"6a5c0e2's gate helper, with the core gate as a second try.

    FAIL-OPEN, and the direction is deliberate: this gate only ever SUPPRESSES
    sends, so failing open keeps a live alert audible. Rule 18's warning that a
    gate over a wrong calendar is worse than no gate is about gates that suppress
    COMPUTE; this one suppresses only notification.
    \"\"\"
    try:
        from monitor_orchestrator_health import _default_is_trading_day
        return _default_is_trading_day()
    except Exception as e:  # noqa: BLE001
        print(f'[GATE] monitor helper unavailable ({e}); trying the core gate directly')
    try:
        from core.trading_calendar_gate import is_trading_day_today
        return is_trading_day_today()
    except Exception as e:  # noqa: BLE001
        print(f'[GATE] calendar gate unavailable ({e}); failing open (treat as trading day)')
        return True


def _dedupe_min() -> int:
    try:
        from monitor_orchestrator_health import DEDUPE_MIN
        return int(DEDUPE_MIN)
    except Exception:  # noqa: BLE001
        return _DEDUPE_FALLBACK_MIN


def _load_state():
    \"\"\"6a5c0e2's AlertState: per-key records, atomic write, fresh interpreter per run.

    Returns None if it cannot be loaded, and _send_deduped then sends WITHOUT dedupe
    rather than going quiet -- a broken state file must not silence the channel.
    \"\"\"
    try:
        from monitor_orchestrator_health import AlertState
        return AlertState(_STATE_PATH).load()
    except Exception as e:  # noqa: BLE001
        print(f'[DEDUPE] state unavailable ({e}); sending without dedupe this run')
        return None


def _send_deduped(state, key: str, sender, message: str, context: dict) -> bool:
    \"\"\"30-minute dedupe around ONE send site, keyed PER CONTRACT.

    PER-KEY, not one merged key, and that differs from 6a5c0e2 on purpose. The
    monitor merged its two conditions because they were one fault with one remedy
    flapping between two names at a */1 cadence. These four sites are different
    contracts with different remedies -- a stale chain and a duplicate run_id are
    not one incident -- and this script runs */5, so merging would hide whichever
    arrived second. No hold-down either: there is no RECOVERED message here to
    manufacture, which is what the hold-down existed to prevent.

    State is recorded on ATTEMPT, matching _emit's behaviour in the monitor: a
    delivery failure is logged, not retried into a loop.
    \"\"\"
    now = datetime.utcnow()
    if state is None:
        return bool(sender(message, context=context))

    rec = state.data.get(key)
    if rec is not None:
        try:
            age_min = (now - datetime.fromisoformat(rec['last_sent'])).total_seconds() / 60.0
        except Exception:  # noqa: BLE001
            age_min = None  # corrupt record: treat as new, never suppress forever
        if age_min is not None and age_min < _dedupe_min():
            print(f'[DEDUPE] {key} suppressed: last sent {age_min:.0f}m ago, '
                  f're-notify at {_dedupe_min()}m')
            return False

    first_seen = (rec or {}).get('first_seen') or now.isoformat()
    sends = int((rec or {}).get('sends', 0)) + 1
    state.data[key] = {'first_seen': first_seen, 'last_sent': now.isoformat(),
                       'sends': sends, 'clear_streak': 0, 'variant': None}
    ctx = dict(context, first_seen=first_seen, sends=sends)
    if sends > 1:
        message = f'{message} (still failing)'
    ok = bool(sender(message, context=ctx))
    print(f'[SENT] {key}: {message} (delivered={ok})')
    return ok


SUPABASE_URL = os.getenv('SUPABASE_URL')
"""

# ---- edit 3: carry the state on the validator -------------------------------
E3_OLD = """    def __init__(self):
        self.ts = datetime.utcnow()
        self.violations = []
        self.passed = []
"""
E3_NEW = """    def __init__(self):
        self.ts = datetime.utcnow()
        self.violations = []
        self.passed = []
        self.state = _load_state()   # S92: None is tolerated, see _send_deduped
"""

# ---- edit 4: send site 1, stale option chain --------------------------------
E4_OLD = """                send_warning(msg, context={'threshold_min': 5})
"""
E4_NEW = """                _send_deduped(self.state, 'contract_option_chain_stale',
                              send_warning, msg, {'threshold_min': 5})
"""

# ---- edit 5: send site 2, stale spot ----------------------------------------
E5_OLD = """                send_warning(msg, context={'threshold_min': 1, 'table': 'market_spot_snapshots'})
"""
E5_NEW = """                _send_deduped(self.state, 'contract_spot_stale', send_warning, msg,
                              {'threshold_min': 1, 'table': 'market_spot_snapshots'})
"""

# ---- edit 6: send site 3, duplicate run_id ----------------------------------
E6_OLD = """                send_critical(msg, context={
                    'last_run_id': rows[0]['run_id'],
                    'last_created_at': rows[0]['created_at'],
                    'prev_created_at': rows[1]['created_at']
                })
"""
E6_NEW = """                _send_deduped(self.state, 'contract_duplicate_run_id', send_critical, msg, {
                    'last_run_id': rows[0]['run_id'],
                    'last_created_at': rows[0]['created_at'],
                    'prev_created_at': rows[1]['created_at']
                })
"""

# ---- edit 7: send site 4, the summary -- and TD-S91-NEW-14's message --------
E7_OLD = """            send_alert(
                'Compute contracts violated """ + MOJI_EMDASH + """ skipping this cycle',
                level='WARNING',
                context={'num_violations': len(self.violations)}
            )
"""
E7_NEW = """            # S92: TD-S91-NEW-14. The old text read 'skipping this cycle'. This
            # script skips NOTHING. It exits non-zero into
            # `>> logs/contract_check.log 2>&1`, and the orchestrator's cron line
            # (*/5 03-09 * * 1-5) is independent of this one
            # (4,9,...,59 03-09 * * 1-5), so the compute cycle runs regardless.
            #
            # 'no scheduled consumer' is the MEASURED form, and the enumeration
            # behind it is in scratch/s92/patch_s92_contract_gate_dedupe.py: the
            # orchestrator's step list (execute_pipeline, :230-287), shell
            # wrappers, systemd units, every crontab on the box and the log file
            # itself were all walked, not just the crontab. What that cannot see
            # is a dynamically constructed invocation.
            #
            # NO skip control was added, deliberately -- making the claim true is
            # a design change (a computed verdict needs a named, scheduled
            # consumer) and needs its own ruling. Do not do both halves silently.
            _send_deduped(
                self.state, 'contract_violations_summary',
                lambda m, context: send_alert(m, level='WARNING', context=context),
                'Compute contracts violated; the compute cycle runs anyway '
                '(advisory check -- no scheduled consumer reads its exit code)',
                {'num_violations': len(self.violations)},
            )
"""

# ---- edit 8: the entry point -- gate first, save state in a finally ---------
# NOTE, and this cost a dry run: line 183 of the target is a WHITESPACE-ONLY line
# ('    ', four spaces). Written as a triple-quoted literal it comes back as '',
# because trailing whitespace does not survive authoring -- and the anchor then
# reads count=0 against a file that has not drifted at all. The repr() dump of
# the on-disk bytes showed 183|'    ' correctly; the loss happened downstream of
# the dump, which is the half .claude/rules/python-writers.md does not spell out
# (it warns about console output collapsing blank lines, not about the literal).
# So this one anchor is JOINED FROM EXPLICIT PIECES, with the blank line named.
_WS4 = "    "
E8_OLD = "\n".join([
    "if __name__ == '__main__':",
    "    validator = ContractValidator()",
    "    success = validator.run()",
    _WS4,
    "    # Exit 0 if contracts pass, 1 if violated",
    "    sys.exit(0 if success else 1)",
    "",
])
E8_NEW = """if __name__ == '__main__':
    # S92: trading-day gate (TD-S91-NEW-13). Cron already scopes this script to
    # weekday 03-09 UTC, so the remaining flood window is a weekday HOLIDAY:
    # 84 runs x 2 surviving sends (run() short-circuits on the first failure)
    # = ~168 messages, next due Tue 2026-10-20. On a non-trading day there is
    # nothing to validate and nothing to report, so exit 0 before any check.
    if not _is_trading_day():
        print('[HOLIDAY GATE] Not a trading day -- no contract checks, no alerts.')
        sys.exit(0)

    validator = ContractValidator()
    try:
        success = validator.run()
    finally:
        # Save the dedupe record even if run() RAISED. Without the finally, an
        # exception after a send loses last_sent, and the next */5 run re-sends
        # the same condition immediately -- which is the flood this TD is about,
        # arriving by the one path the dedupe would not cover. A raise still
        # propagates: the exit status below is not reached.
        if validator.state is not None:
            validator.state.save()

    # Exit 0 if contracts pass, 1 if violated.
    # TD-S91-NEW-14: no scheduled consumer reads this exit code -- the
    # orchestrator's cron line is independent of this script's. It is advisory,
    # and the alert text now says so.
    sys.exit(0 if success else 1)
"""

EDITS = [
    ("E1 pathlib import", E1_OLD, E1_NEW),
    ("E2 gate + dedupe helpers", E2_OLD, E2_NEW),
    ("E3 validator carries state", E3_OLD, E3_NEW),
    ("E4 send site :72 option_chain", E4_OLD, E4_NEW),
    ("E5 send site :104 spot", E5_OLD, E5_NEW),
    ("E6 send site :139 duplicate run_id", E6_OLD, E6_NEW),
    ("E7 send site :170 summary + TD-14 text", E7_OLD, E7_NEW),
    ("E8 entry point gate + state save", E8_OLD, E8_NEW),
]


def _parses(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    print("=" * 72)
    print(f"patch_s92_contract_gate_dedupe -- {'APPLY' if apply else 'DRY RUN'}")
    print("=" * 72)

    if not TARGET.exists():
        print(f"ABORT: target not found: {TARGET}")
        return 2

    raw = TARGET.read_bytes()
    has_bom = raw[:3] == b"\xef\xbb\xbf"
    enc = "utf-8-sig" if has_bom else "utf-8"
    src_raw = raw.decode("utf-8-sig")
    crlf = src_raw.count("\r\n")
    bare_lf = src_raw.count("\n") - crlf
    write_eol = "\r\n" if crlf >= bare_lf else "\n"
    print(f"  file      : {TARGET}")
    print(f"  bytes     : {len(raw)}")
    print(f"  bom       : {has_bom}  (enc={enc})  <- the BOM case")
    print(f"  eol       : crlf={crlf} bare_lf={bare_lf} -> write as "
          f"{'CRLF' if write_eol == chr(13) + chr(10) else 'LF'}")

    src_lf = src_raw.replace("\r\n", "\n")

    # mojibake census, by line, before anything is changed
    moji_lines = [i + 1 for i, ln in enumerate(src_lf.split("\n")) if MOJI_EMDASH in ln]
    print(f"  mojibake  : em-dash on lines {moji_lines} (count={len(moji_lines)}); "
          f"rupee-sign count={src_lf.count(chr(0x00e2) + chr(0x201a) + chr(0x00b9))}")

    # --- idempotency gate ----------------------------------------------------
    if MARKER in src_lf:
        print(f"  SKIP      : marker {MARKER!r} already present; nothing to do")
        print("\nRESULT: 0 of 8 edits need applying (already applied).")
        return 0

    # --- every anchor count==1, checked BEFORE any replacement ---------------
    bad = []
    for name, old, _new in EDITS:
        n = src_lf.count(old)
        print(f"  anchor    : {name:<40s} count={n}")
        if n != 1:
            bad.append((name, n))
    if bad:
        print("\nABORT: these anchors are not unique-and-present. Nothing written.")
        for name, n in bad:
            print(f"         {name}: count={n}")
        print("       0 -> the file drifted; re-dump its bytes with repr() and")
        print("            rebuild the anchor (never from console output).")
        print("       >1 -> the anchor is ambiguous and the edit would land twice.")
        return 2

    patched_lf = src_lf
    applied_edits = []
    for name, old, new in EDITS:
        before = patched_lf
        patched_lf = patched_lf.replace(old, new, 1)
        applied_edits.append((name, patched_lf != before))

    not_applied = [n for n, ok in applied_edits if not ok]
    if not_applied:
        print(f"ABORT: these edits were no-ops: {not_applied}. Nothing written.")
        return 2

    # --- ast gate on the patched text, before any write ---------------------
    try:
        ast.parse(patched_lf, filename=str(TARGET))
    except SyntaxError as e:
        print(f"ABORT: ast.parse failed on the patched text: {e}")
        return 2
    print(f"  ast.parse : OK on patched text ({len(patched_lf)} chars)")

    # --- mojibake accounting, measured not asserted -------------------------
    moji_before = src_lf.count(MOJI_EMDASH)
    moji_after = patched_lf.count(MOJI_EMDASH)
    print(f"  mojibake  : em-dash {moji_before} -> {moji_after} "
          f"(expect 2 -> 1; the :171 instance lives inside the message "
          f"TD-S91-NEW-14 requires rewritten, :3 untouched)")
    if moji_after != 1:
        print("ABORT: mojibake count is not the expected 1 after patching. "
              "Either :3 was touched or the message anchor moved. Nothing written.")
        return 2

    print("\n--- diff (unified, LF-space) ---")
    for line in difflib.unified_diff(
            src_lf.splitlines(True), patched_lf.splitlines(True),
            fromfile=f"a/{TARGET.name}", tofile=f"b/{TARGET.name}", n=2):
        sys.stdout.write(line)
    print("--- end diff ---\n")

    if not apply:
        print("DRY RUN: nothing written. Re-run with --apply.")
        print(f"RESULT: {sum(1 for _, ok in applied_edits if ok)} of {len(EDITS)} "
              f"edits would be applied; ast.parse OK; mojibake {moji_before} -> {moji_after}.")
        return 0

    if BACKUP.exists():
        print(f"  backup    : {BACKUP.name} already exists; left as-is")
    else:
        BACKUP.write_bytes(raw)
        print(f"  backup    : wrote {BACKUP.name} ({len(raw)} bytes)")

    out = patched_lf.replace("\n", write_eol) if write_eol == "\r\n" else patched_lf
    TARGET.write_bytes(out.encode(enc))

    # --- artefact identity check, not "exited zero" -------------------------
    nraw = TARGET.read_bytes()
    back = nraw.decode("utf-8-sig")
    checks = {
        "bom preserved": nraw[:3] == b"\xef\xbb\xbf",
        "marker present": MARKER in back,
        "gate called": "if not _is_trading_day():" in back,
        "state save in finally": "    finally:" in back,
        "1 def + 4 call sites": back.count("_send_deduped(") == 5,
        # NOT `"skipping this cycle" not in back`. That was the first form and it
        # failed on a CORRECT file: the E7 comment quotes the old text verbatim to
        # record what changed, so a bare substring test hits the documentation of
        # the fix. A wrong CHECK, not a wrong artefact -- and the replacement tests
        # the claim SITE, which is tighter than what it replaces, not looser.
        "old claim literal gone": ("'Compute contracts violated " + MOJI_EMDASH
                                   + " skipping this cycle'") not in back,
        "new message present": "the compute cycle runs anyway" in back,
        # TD-S91-NEW-14's other half: the text was changed and NO skip control was
        # added. Tested as "nothing that could consume an exit code appeared",
        # because that is what adding a skip control would require. Not
        # `"sys.exit(0)" in back` -- that string is the holiday gate and would be
        # true either way, so it could not fail for the reason it names.
        "no exit-code consumer added": not any(
            tok in back for tok in ("subprocess", "os.system", "os.popen",
                                    "returncode", "check_call", "check_output")),
        "mojibake em-dash == 1": back.count(MOJI_EMDASH) == 1,
        "ast reparses on disk": _parses(back),
    }
    for k, v in checks.items():
        print(f"  verify    : {k:<24s} {v}")
    print(f"  verify    : bytes {len(raw)} -> {len(nraw)}")
    ok = all(checks.values())
    print(f"\nRESULT: {sum(1 for _, a in applied_edits if a)} of {len(EDITS)} edits "
          f"applied; artefact checks {'ALL PASS' if ok else 'FAILED'}.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
