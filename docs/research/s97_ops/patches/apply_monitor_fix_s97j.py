"""S97-J: monitor_orchestrator_health.py -- an in-progress ledger row is not a failure.
Run from the repo root. Edits TWO files, one anchor each; nothing is written unless every anchor matches once.

Evidence (2026-10-21, 84 orchestrator rows, bin/roq.sh, 2026-10-22 04:33 IST): script_execution_log rows are
created within 1.5 s of started_at and finished >= 100.8 s later (avg run 132.7 s = 44.2 % of the 5-min cycle).
The old check `row.get('exit_code') != 0` reads exit_code None (run still in progress) as FAILED, which matched
43.7 % of in-band minutes on 2026-10-12 (177 FAILED / 405). A finished row with a non-zero exit_code still alarms.
"""
import hashlib

EDITS = {
    "monitor_orchestrator_health.py": [(
        "        for row in rows:\n"
        "            if row.get('exit_code') != 0:\n",
        "        # S97-J: a row the orchestrator inserted at start and has not finished yet\n"
        "        # (exit_code and finished_at both NULL) is IN PROGRESS, not failed. Measured\n"
        "        # 2026-10-21: rows are created within 1.5 s of start and finished >= 100.8 s later,\n"
        "        # so `None != 0` read ~44 % of in-band minutes as FAILED. A finished non-zero\n"
        "        # exit_code still alarms. A run that HANGS is not detected here (5-min look-back).\n"
        "        finished = [r for r in rows\n"
        "                    if not (r.get('exit_code') is None and r.get('finished_at') is None)]\n"
        "        for row in finished:\n"
        "            if row.get('exit_code') != 0:\n",
    )],
    "tests/test_monitor_orchestrator_gate.py": [(
        "print(f\"\\nMONITOR GATE ",
        "print('\\n--- scenario 12 (S97-J): an in-progress ledger row is not a failure ---')\n"
        "IN_PROGRESS = [{'exit_code': None, 'duration_ms': None, 'finished_at': None,\n"
        "                'created_at': '2026-10-07T05:00:01'}]\n"
        "DONE_BAD = [{'exit_code': 1, 'duration_ms': 157547, 'finished_at': '2026-10-07T05:02:39',\n"
        "             'created_at': '2026-10-07T05:00:01'}]\n"
        "ROWS['IN_PROGRESS'] = IN_PROGRESS\n"
        "ROWS['MIXED'] = IN_PROGRESS + OK_RUN\n"
        "ROWS['MIXED_BAD'] = IN_PROGRESS + DONE_BAD\n"
        "\n"
        "\n"
        "def conditions_for(rows):\n"
        "    tmp = tempfile.mkdtemp(prefix='s97j_monitor_state_')\n"
        "    mon = H.HealthMonitor(now_utc=IN, send=lambda *a: True, is_trading_day=lambda: True,\n"
        "                          window=WINDOW, state_path=Path(tmp) / 'monitor_alert_state.json',\n"
        "                          fetch_rows=lambda: rows)\n"
        "    conds, probe_ok = mon.check_orchestrator_failures()\n"
        "    return sorted(conds), probe_ok\n"
        "\n"
        "\n"
        "# control: the predicate this fix replaces DOES fire on the in-progress row, so the cells\n"
        "# below measure the fix and not a row that could never alarm.\n"
        "check('control: old predicate (exit_code != 0) fires on an in-progress row',\n"
        "      IN_PROGRESS[0].get('exit_code') != 0, True)\n"
        "check('in-progress row only -> no condition, probe ok',\n"
        "      conditions_for(ROWS['IN_PROGRESS']), ([], True))\n"
        "check('in-progress + finished OK -> no condition',\n"
        "      conditions_for(ROWS['MIXED']), ([], True))\n"
        "check('in-progress + finished exit_code 1 -> condition raised',\n"
        "      conditions_for(ROWS['MIXED_BAD']), ([KEY], True))\n"
        "check('15 in-session ticks all in progress -> 0 sends',\n"
        "      len(replay(IN, ['IN_PROGRESS'] * 15)), 0)\n"
        "# control: the same 15 ticks reading FAILED do send, so the 0 above is the fix.\n"
        "check('control: the same 15 ticks FAILED -> sends > 0',\n"
        "      len(replay(IN, ['FAILED'] * 15)) > 0, True)\n"
        "\n"
        "print(f\"\\nMONITOR GATE ",
    )],
}

prepared = []
for path, edits in EDITS.items():
    raw = open(path, "rb").read()
    crlf = b"\r\n" in raw
    s = raw.decode("utf-8").replace("\r\n", "\n")
    before = s.count("\n")
    for old, new in edits:
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"STOPPED - anchor in {path} found {n} times (need 1); NO file changed")
        s = s.replace(old, new)
    out = (s.replace("\n", "\r\n") if crlf else s).encode("utf-8")
    prepared.append((path, out, crlf, before, s.count("\n")))

for path, out, crlf, before, after in prepared:
    open(path, "wb").write(out)
    print(f"{path}: eol={'CRLF' if crlf else 'LF'} lines {before} -> {after} "
          f"(+{after - before}) sha256_12={hashlib.sha256(out).hexdigest()[:12]}")
print("APPLIED S97-J")
