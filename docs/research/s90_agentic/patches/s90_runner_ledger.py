import ast, pathlib, shutil, sys
APPLY = "--apply" in sys.argv
MARK = "S90_RUNNER_LEDGER"
P = "run_merdian_shadow_runner_aws.py"
EDITS = [
 ('    failed_steps: List[str] = []\n',
  '    failed_steps: List[str] = []\n'
  f'    LAST_FAILED_STEPS.clear()  # {MARK}\n'),
 ('            failed_steps.append(label)\n',
  '            failed_steps.append(label)\n'
  '            LAST_FAILED_STEPS.append(label)\n'),
 ('def main() -> int:\n',
  f'# {MARK} (ADR-031 D7.4, R01-F1): one script_execution_log row per cycle.\n'
  '# The ledger never blocks compute: any ledger error is logged and swallowed.\n'
  'LAST_FAILED_STEPS: List[str] = []\n\n\n'
  'def _ledger_open():\n'
  '    try:\n'
  '        return ExecutionLog(script_name="run_merdian_shadow_runner_aws.py", expected_writes={})\n'
  '    except Exception as e:\n'
  '        log_message(f"[LEDGER] open failed (compute continues): {e}", "WARN")\n'
  '        return None\n\n\n'
  'def _ledger_close(led, rc: int, reason: str, notes: str = "", error: str = "") -> int:\n'
  '    if led is not None:\n'
  '        try:\n'
  '            if reason == "SUCCESS":\n'
  '                led.complete(notes=notes or None)\n'
  '            else:\n'
  '                led.exit_with_reason(reason, exit_code=rc, notes=notes or None, error_message=error or None)\n'
  '        except Exception as e:\n'
  '            log_message(f"[LEDGER] close failed: {e}", "WARN")\n'
  '    return rc\n\n\n'
  'def main() -> int:\n'),
 ('    log_message("Shadow Runner starting (S46 Phase 2.c; TD-S54-NEW-1 per-symbol run_id)")\n',
  '    log_message("Shadow Runner starting (S46 Phase 2.c; TD-S54-NEW-1 per-symbol run_id)")\n'
  '    led = _ledger_open()\n'),
 ('        log_message("[HOLIDAY GATE] Market closed today -- orchestrator exiting (no compute).")\n        return 0\n',
  '        log_message("[HOLIDAY GATE] Market closed today -- orchestrator exiting (no compute).")\n'
  '        return _ledger_close(led, 0, "HOLIDAY_GATE")\n'),
 ('        log_message(f"Failed to initialize Supabase: {e}", "ERROR")\n        return 1\n',
  '        log_message(f"Failed to initialize Supabase: {e}", "ERROR")\n'
  '        return _ledger_close(led, 1, "DATA_ERROR", error=f"supabase init: {e}")\n'),
 ('            "WARN",\n        )\n        return 1\n',
  '            "WARN",\n        )\n'
  '        return _ledger_close(led, 1, "SKIPPED_NO_INPUT", error="no run_id for any symbol")\n'),
 ('        log_message("Shadow runner cycle complete (contract met)", "INFO")\n        return 0\n',
  '        log_message("Shadow runner cycle complete (contract met)", "INFO")\n'
  '        return _ledger_close(led, 0, "SUCCESS", notes=f"run_ids={run_ids}")\n'),
 ('        log_message("Shadow runner cycle failed (contract not met)", "ERROR")\n        return 1\n',
  '        log_message("Shadow runner cycle failed (contract not met)", "ERROR")\n'
  '        return _ledger_close(led, 1, "DATA_ERROR", notes=f"run_ids={run_ids}",\n'
  '                             error="failed steps: " + ", ".join(LAST_FAILED_STEPS))\n'),
]
p = pathlib.Path(P); raw = p.read_bytes(); bom = raw.startswith(b"\xef\xbb\xbf")
txt = raw.decode("utf-8-sig"); eol = "\r\n" if txt.count("\r\n") > txt.count("\n") / 2 else "\n"
t = txt.replace("\r\n", "\n")
if MARK in t:
    print(f"{P}: already patched - skip"); sys.exit(0)
for old, new in EDITS:
    n = t.count(old)
    if n != 1:
        print(f"{P}: anchor count {n} != 1 - ABORT:\n{old}"); sys.exit(1)
    t = t.replace(old, new)
ast.parse(t)
out = t.replace("\n", eol).encode("utf-8")
if bom: out = b"\xef\xbb\xbf" + out
if APPLY:
    shutil.copy2(p, p.with_name(p.name + "_PRE_S90"))
    p.write_bytes(out); print(f"{P}: APPLIED ({len(raw)} -> {len(out)} bytes)")
else:
    print(f"{P}: dry-run OK ({len(raw)} -> {len(out)} bytes)")
