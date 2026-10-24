#!/usr/bin/env python3
"""S100 R3 (TD-S97-NEW-3): the orchestrator monitor flags a HUNG run -- offline, with controls and mutants.

The defect: the orchestrator inserts its ledger row at start and fills finished_at at the end. The
look-back probe (created_at within LOOKBACK_MIN) skips an unfinished row as in progress (S97-J), and
the row then ages out of the look-back, so a run that never finishes is never seen. The fix is a
second probe -- unfinished rows started more than HUNG_MIN ago today -- under its own key.

Rule 0: every cell names what would make it fail, and five mutants prove each part load-bearing:
the probe consulted at all (M1), its own key (M2), per-key UNKNOWN (M3), the day bound (M4), the age
threshold (M5). A mutant whose named cells all still pass means those cells assert nothing.

OFFLINE AND SAFE: the monitor is loaded from source with Telegram blanked BEFORE import, every send
is a counting stub, every ledger read is injected or `requests.get` is mocked. No database, network,
clock or credential. Nothing prints an environment value (Rule 19).
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile
import types
import unittest.mock as mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MONITOR = REPO / "monitor_orchestrator_health.py"
RUNNER = REPO / "run_merdian_shadow_runner_aws.py"
sys.path.insert(0, str(REPO))
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""
os.environ.setdefault("SUPABASE_URL", "https://offline.invalid")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "offline-dummy-not-a-credential")

UTC = timezone.utc
REAL_CRONTAB = ("*/5 03-09 * * 1-5 cd /home/ssm-user/meridian-engine && source .env && "
                "python3 run_merdian_shadow_runner_aws.py >> logs/orchestrator.log 2>&1\n")
IN = datetime(2026, 10, 26, 5, 0, tzinfo=UTC)            # Monday 10:30 IST, inside the band
OFF = datetime(2026, 10, 26, 12, 40, tzinfo=UTC)         # Monday 18:10 IST, outside
OK_RUN = [{"exit_code": 0, "finished_at": "2026-10-26T04:57:10+00:00", "duration_ms": 130000,
           "created_at": "2026-10-26T04:55:01+00:00"}]
HUNG_ROW = [{"exit_code": None, "finished_at": None, "exit_reason": "RUNNING",
             "started_at": "2026-10-26T04:50:01.123000+00:00", "created_at": "2026-10-26T04:50:01+00:00"}]
BAD_RUN = [{"exit_code": 1, "finished_at": "2026-10-26T04:57:10+00:00", "duration_ms": 900,
            "created_at": "2026-10-26T04:55:01+00:00"}]


class Fail(Exception):
    pass


def load(src: str, name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(MONITOR)
    sys.modules[name] = mod
    exec(compile(src, str(MONITOR), "exec"), mod.__dict__)
    return mod


def replay(H, start, seq, *, window=None):
    """One fresh HealthMonitor per tick, as cron runs it. seq items: (lookback_token, hung_token),
    tokens 'OK' / 'NONE' / 'FAILED' / 'ERR' and 'HUNG' / 'CLEAR' / 'ERR'. Returns sends."""
    sent = []
    state = Path(tempfile.mkdtemp(prefix="s100_r3_")) / "monitor_alert_state.json"
    win = window or H.parse_orchestrator_window(REAL_CRONTAB)
    for i, (lb, hg) in enumerate(seq):
        def fetch(_t=lb):
            if _t == "ERR":
                raise H.QueryFailed("simulated")
            return {"OK": OK_RUN, "NONE": [], "FAILED": BAD_RUN}[_t]

        def fetch_hung(_t=hg):
            if _t == "ERR":
                raise H.QueryFailed("simulated")
            return HUNG_ROW if _t == "HUNG" else []
        H.HealthMonitor(now_utc=start + timedelta(minutes=i),
                        send=lambda lv, m, c: sent.append((lv, m)) or True,
                        is_trading_day=lambda: True, window=win, state_path=state,
                        fetch_rows=fetch, fetch_hung_rows=fetch_hung).run()
    return sent


def cells(H) -> list[tuple[str, bool, str]]:
    out = []

    def chk(name, ok, fails_if):
        out.append((name, bool(ok), fails_if))

    def mon(now=IN, rows=OK_RUN, hung=HUNG_ROW):
        return H.HealthMonitor(now_utc=now, send=lambda *a: True, is_trading_day=lambda: True,
                               window=H.parse_orchestrator_window(REAL_CRONTAB),
                               state_path=Path(tempfile.mkdtemp()) / "s.json",
                               fetch_rows=lambda: rows, fetch_hung_rows=lambda: hung)

    hk = getattr(H, "HUNG_CONDITION_KEY", None)
    # control: the look-back probe alone does NOT see an unfinished row (S97-J), so a hang needs
    # the second probe -- this is what makes T1 a test of the fix and not of the old probe.
    conds, _ = mon(rows=HUNG_ROW, hung=[]).check_orchestrator_failures()
    chk("C0 control: look-back probe alone raises nothing on an unfinished row", conds == {},
        "S97-J reverted (an in-progress row reads FAILED again)")
    c, ok = mon().check_hung_runs()
    chk("T1 hung row -> CRITICAL under orchestrator_hung", ok and list(c) == ["orchestrator_hung"]
        and c["orchestrator_hung"][0] == "CRITICAL", "key or level wrong, or probe not read")
    c, ok = mon(hung=[]).check_hung_runs()
    chk("T2 no unfinished row -> no hung condition", ok and c == {}, "condition raised with nothing hung")
    s = replay(H, IN, [("OK", "HUNG")] * 20)
    chk("T3 20 in-band ticks hung, cycles healthy -> exactly 1 CRITICAL HUNG send",
        len(s) == 1 and s[0][0] == "CRITICAL" and s[0][1].startswith("Orchestrator run HUNG"),
        "hang unseen (0 sends) or not deduped")
    s = replay(H, IN, [("OK", "HUNG")] * 5 + [("OK", "CLEAR")] * H.HOLDDOWN_TICKS)
    ms = [m for _, m in s]
    chk("T5 hang clears -> RECOVERED: orchestrator_hung after the hold-down",
        len(ms) == 2 and ms[0].startswith("Orchestrator run HUNG") and ms[1] == "RECOVERED: orchestrator_hung",
        "no RECOVERED, wrong key, or extra sends")
    s = replay(H, IN, [("OK", "HUNG")] * 3 + [("OK", "ERR")] * 12)
    chk("T6 hung probe unreadable 12 ticks -> no RECOVERED", not any(m.startswith("RECOVERED") for _, m in s),
        "an unread probe counted as a clear tick")
    s = replay(H, IN, [("OK", "HUNG")] * 3 + [("OK", "CLEAR")] * 12)
    chk("T6c control: the same 12 ticks read clear -> 1 RECOVERED",
        sum(m.startswith("RECOVERED") for _, m in s) == 1, "hold-down never fires, so T6 measures nothing")
    s = replay(H, IN, [("ERR", "HUNG")] * 3)
    chk("T7 look-back probe unreadable, hang observed -> the hang still pages",
        len(s) == 1 and s[0][1].startswith("Orchestrator run HUNG"), "one probe's failure silences the other")
    s = replay(H, IN, [("FAILED", "CLEAR")] * 3 + [("ERR", "CLEAR")] * 12)
    chk("T8 look-back unreadable 12 ticks over an active failure -> no RECOVERED (scenario 11 holds)",
        not any(m.startswith("RECOVERED") for _, m in s), "per-key UNKNOWN lost for the old key")
    s = replay(H, OFF, [("NONE", "HUNG")] * 20)
    chk("T9 hang outside the band -> 0 sends", s == [], "the hung probe bypasses the gate")
    # T10: the query the probe really sends.
    m = H.HealthMonitor(now_utc=datetime(2026, 10, 26, 5, 9, 30, tzinfo=UTC), send=lambda *a: True,
                        is_trading_day=lambda: True, window=H.parse_orchestrator_window(REAL_CRONTAB),
                        state_path=Path(tempfile.mkdtemp()) / "s.json")
    resp = mock.Mock(status_code=200); resp.json.return_value = []
    with mock.patch.object(H.requests, "get", return_value=resp) as get:
        m._fetch_hung_rows_http() if hasattr(m, "_fetch_hung_rows_http") else None
    url = get.call_args.args[0] if get.call_args else ""
    chk("T10 query: orchestrator rows, finished_at null, started 6+ min ago, today only",
        "script_name=eq.run_merdian_shadow_runner_aws.py" in url and "finished_at=is.null" in url
        and "started_at=lt.2026-10-26T05:03:30&" in url and "started_at=gte.2026-10-26T00:00:00&" in url,
        "filter missing, threshold or day bound wrong")
    wait = int(re.search(r"^CYCLE_WAIT_S = (\d+)", RUNNER.read_text(encoding="utf-8"), re.M).group(1))
    chk("T11 HUNG_MIN clears the longest healthy run (wait + 184.4 s) and pages within 2 cycles",
        getattr(H, "HUNG_MIN", 0) * 60 > wait + 184.4 and getattr(H, "HUNG_MIN", 99) < 10,  # 184.4 s = max run 10-06 -> 10-23 (10-16, S100 read)
        "threshold inside a healthy run (false CRITICALs) or later than two cycles")
    # T12: default wiring -- an injected look-back ledger never lets the hung probe reach the network.
    with mock.patch.object(H.requests, "get", side_effect=Fail("network")) as get:
        H.HealthMonitor(now_utc=IN, send=lambda *a: True, is_trading_day=lambda: True,
                        window=H.parse_orchestrator_window(REAL_CRONTAB),
                        state_path=Path(tempfile.mkdtemp()) / "s.json", fetch_rows=lambda: OK_RUN).run()
    bare = H.HealthMonitor(now_utc=IN, send=lambda *a: True, is_trading_day=lambda: True,
                           window=H.parse_orchestrator_window(REAL_CRONTAB), state_path=Path(tempfile.mkdtemp()) / "s.json")
    chk("T12 injected ledger -> hung probe offline; bare monitor -> the HTTP probe",
        get.call_count == 0 and getattr(bare._fetch_hung_rows, "__name__", "") == "_fetch_hung_rows_http",
        "a test could reach the network, or production never runs the probe")
    m = mon(now=datetime(2026, 10, 26, 5, 9, 30, tzinfo=UTC)); c, _ = m.check_hung_runs()
    chk("T13 message carries the age: started 04:50:01, now 05:09:30 -> 19 min",
        "no finish after 19 min" in (c.get(hk or "", ("", "", {}))[1]), "age wrong or not stated")
    return out


MUTANTS = {
    "M1 hung probe never consulted": (
        "        hung, hung_ok = self.check_hung_runs()                # S100_R3_HUNG\n",
        "        hung, hung_ok = {}, True\n",
        {"T3 20 in-band ticks hung, cycles healthy -> exactly 1 CRITICAL HUNG send",
         "T5 hang clears -> RECOVERED: orchestrator_hung after the hold-down",
         "T7 look-back probe unreadable, hang observed -> the hang still pages"}),
    "M2 hang shares the look-back key": (
        "HUNG_CONDITION_KEY = 'orchestrator_hung'\n", "HUNG_CONDITION_KEY = 'orchestrator_unhealthy'\n",
        {"T1 hung row -> CRITICAL under orchestrator_hung",
         "T5 hang clears -> RECOVERED: orchestrator_hung after the hold-down"}),
    "M3 UNKNOWN keys tick clear": (
        "set(state.keys()) - set(conditions) - unknown", "set(state.keys()) - set(conditions)",
        {"T6 hung probe unreadable 12 ticks -> no RECOVERED",
         "T8 look-back unreadable 12 ticks over an active failure -> no RECOVERED (scenario 11 holds)"}),
    "M4 no day bound": (
        "&started_at=gte.{day0}", "",
        {"T10 query: orchestrator rows, finished_at null, started 6+ min ago, today only"}),
    "M5 no age threshold": (
        "older = (base - timedelta(minutes=HUNG_MIN)).isoformat()", "older = base.isoformat()",
        {"T10 query: orchestrator rows, finished_at null, started 6+ min ago, today only"}),
}


def main() -> int:
    src = MONITOR.read_text(encoding="utf-8-sig")
    if "S100_R3_HUNG" not in src:
        print("MONITOR HUNG RUN FAIL: monitor_orchestrator_health.py lacks S100_R3_HUNG"); return 1
    with contextlib.redirect_stdout(io.StringIO()):     # the monitor logs every tick; keep the verdict readable
        res = cells(load(src, "mon_s100_r3"))
    fails = [(n, f) for n, ok, f in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for i, (mname, (old, new, must_fail)) in enumerate(MUTANTS.items()):
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if src.count(old) != 1:
            not_applied.append(mname); continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                mres = {n: ok for n, ok, _ in cells(load(src.replace(old, new, 1), f"mon_s100_r3_m{i}"))}
        except Exception as e:                                # a crash is a kill, not a pass
            mres = {n: False for n in must_fail}; print(f"  ({mname} raised {type(e).__name__}: {e})")
        survivors += [f"{mname}: {n}" for n in must_fail if mres.get(n, True)]
    for n, ok, f in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   (fails if: {f})"))
    killed = sum(len(v[2]) for k, v in MUTANTS.items() if k not in not_applied) - len(survivors)
    print(f"  cells {len(res)}, failing {len(fails)}; mutants {len(MUTANTS)}, not applied {len(not_applied)}, "
          f"mutant cells killed {killed}, surviving {len(survivors)} (must be 0)")
    for s in not_applied: print(f"  MUTANT NOT APPLIED: {s}")
    for s in unknown: print(f"  MUTANT NAMES NO CELL: {s}")
    for s in survivors: print(f"  MUTANT SURVIVED: {s}")
    if fails or survivors or not_applied or unknown:
        print("MONITOR HUNG RUN FAIL"); return 1
    print("MONITOR HUNG RUN ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
