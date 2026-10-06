"""S90 ruling S90-F — wire ENH-133 writer into the live runner; 57014 retry in the writer.
Canon-v3: read_bytes + utf-8-sig, EOL preserved, count==1 anchors, idempotency marker,
ast.parse gate, _PRE_S90 backup, dry-run default, --apply to write."""
import ast, pathlib, shutil, sys
APPLY = "--apply" in sys.argv
MARK = "S90_ENH133_WIRE"

def patch(path, edits):
    p = pathlib.Path(path); raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf"); txt = raw.decode("utf-8-sig")
    eol = "\r\n" if txt.count("\r\n") > txt.count("\n") / 2 else "\n"
    t = txt.replace("\r\n", "\n")
    if MARK in t:
        print(f"{path}: already patched ({MARK}) — skip"); return True
    for old, new in edits:
        n = t.count(old)
        if n != 1:
            print(f"{path}: anchor count {n} != 1 — ABORT\n---\n{old}\n---"); return False
        t = t.replace(old, new)
    ast.parse(t)
    out = t.replace("\n", eol).encode("utf-8")
    if bom: out = b"\xef\xbb\xbf" + out
    if APPLY:
        shutil.copy2(p, p.with_name(p.name + "_PRE_S90"))
        p.write_bytes(out); print(f"{path}: APPLIED ({len(raw)} -> {len(out)} bytes)")
    else:
        print(f"{path}: dry-run OK ({len(raw)} -> {len(out)} bytes)")
    return True

runner = [
 ('SYMBOLS: List[str] = ["NIFTY", "SENSEX"]\n',
  'SYMBOLS: List[str] = ["NIFTY", "SENSEX"]\n\n'
  f'# {MARK} (ruling S90-F, ADR-030): per-cycle layer history. OFF SWITCH: set False.\n'
  '# A code constant, not a parameter: a parameter read can fail open (roadmap risk 14).\n'
  'ENH133_WRITER_ENABLED: bool = True\n'),
 ('            f"compute_volatility_metrics {symbol}",\n            60,\n        ))\n\n',
  '            f"compute_volatility_metrics {symbol}",\n            60,\n        ))\n\n'
  f'    # {MARK}: after gamma AND volatility (v_gex_strike_rank / v_gex_strike_walls read\n'
  '    # volatility_snapshots), before the symbol-keyed steps. Non-fatal like every step.\n'
  '    if ENH133_WRITER_ENABLED:\n'
  '        for symbol, run_id in run_ids.items():\n'
  '            steps.append((\n'
  '                ["python3", "write_gex_cycle_history_local.py", run_id],\n'
  '                f"write_gex_cycle_history {symbol}",\n'
  '                90,\n'
  '            ))\n\n'),
]
writer = [
 ('import os\nimport sys\n', 'import os\nimport sys\nimport time\n'),
 ('    try:\n        rows = [build_row(leg, calendar_healthy) for leg in legs]\n'
  '    except Exception as e:\n        return log.exit_with_reason("DATA_ERROR", exit_code=1,\n'
  '                                    error_message=f"build_row failed: {e}")\n',
  f'    # {MARK}: bounded retry on statement timeout (57014) only. S90 first live run:\n'
  '    # NIFTY build_row hit 57014 on a cold view read and passed on the next attempt.\n'
  '    rows, last_err, attempts = None, None, 0\n'
  '    for attempts in range(1, 4):\n'
  '        try:\n'
  '            rows = [build_row(leg, calendar_healthy) for leg in legs]\n'
  '            break\n'
  '        except Exception as e:\n'
  '            last_err = e\n'
  '            if "57014" not in str(e):\n'
  '                break\n'
  '            time.sleep(3)\n'
  '    if rows is None:\n'
  '        return log.exit_with_reason("DATA_ERROR", exit_code=1,\n'
  '                                    error_message=f"build_row failed after {attempts} attempt(s): {last_err}")\n'),
]
ok = patch("run_merdian_shadow_runner_aws.py", runner) and patch("write_gex_cycle_history_local.py", writer)
sys.exit(0 if ok else 1)
