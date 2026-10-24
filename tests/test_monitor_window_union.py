#!/usr/bin/env python3
"""S100 R42 (ruling S100-C): the orchestrator monitor's window is the union of EVERY runner crontab line,
when that union is one uniform-step run on one set of weekdays -- offline, with controls and mutants.

The defect: parse_orchestrator_window returned the FIRST matching line silently. The S98-B closing cycles
are a second line (0,5,10 10 = 15:30/15:35/15:40 IST), so they were never in the monitor band, and a
second line inserted ABOVE the first would have collapsed the band to that line alone (S99-B's negative
control read (600, 610)). The alert daemon S98-E.1 relied on for the closing cycles has not run since
2026-06-11 (box read 2026-10-24), so nothing watched them.

Expected values are computed, not recalled (Rule 0): W1 parses the committed docs/registers/aws_crontab.txt
(refreshed from `crontab -l` at 3706435) and checks it against an independent expansion written here.

Mutants: M1 the union disabled (first line wins again), M2 the uniform-step check removed, M3 the weekday
check removed. A mutant whose named cells all still pass means those cells assert nothing.
OFFLINE AND SAFE: Telegram blanked before import; every send a stub; no database or network.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MONITOR = REPO / "monitor_orchestrator_health.py"
CRONTAB = REPO / "docs" / "registers" / "aws_crontab.txt"
sys.path.insert(0, str(REPO))
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""
os.environ.setdefault("SUPABASE_URL", "https://offline.invalid")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "offline-dummy-not-a-credential")
UTC = timezone.utc
SCRIPT = "run_merdian_shadow_runner_aws.py"
TAIL = f" cd /home/ssm-user/meridian-engine && source .env && python3 {SCRIPT} >> logs/orchestrator.log 2>&1"
MAIN = "*/5 03-09 * * 1-5" + TAIL
CLOSE = "0,5,10 10 * * 1-5" + TAIL


def load(src: str, name: str) -> types.ModuleType:
    mod = types.ModuleType(name); mod.__file__ = str(MONITOR); sys.modules[name] = mod
    exec(compile(src, str(MONITOR), "exec"), mod.__dict__)
    return mod


def independent_starts(text: str) -> list[int]:
    """Minute-of-day starts of every enabled runner line, expanded without the module's code."""
    def ex(f, lo, hi):
        out = set()
        for p in f.split(","):
            st = 1
            if "/" in p:
                p, s = p.split("/"); st = int(s)
            if p == "*": a, b = lo, hi
            elif "-" in p: a, b = (int(x) for x in p.split("-"))
            else: a = b = int(p)
            out |= set(range(a, b + 1, st))
        return out
    S = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or SCRIPT not in line:
            continue
        m, h = line.split()[:2]
        S |= {hh * 60 + mm for hh in ex(h, 0, 23) for mm in ex(m, 0, 59)}
    return sorted(S)


def shape(w):
    return (w.first_start_min, w.last_start_min, w.step_min, tuple(sorted(w.dows)))


def cells(H) -> list[tuple[str, bool, str]]:
    out = []

    def chk(name, ok, fails_if):
        out.append((name, bool(ok), fails_if))

    def raises(text):
        try:
            H.parse_orchestrator_window(text); return False
        except ValueError:
            return True

    live = CRONTAB.read_text(encoding="utf-8")
    st = independent_starts(live)
    exp = (st[0], st[-1], st[1] - st[0], (1, 2, 3, 4, 5))
    chk("W0 independent expansion of the committed crontab: 2 lines, one 5-min run 03:00-10:10 UTC",
        len([l for l in live.splitlines() if SCRIPT in l and not l.strip().startswith("#")]) == 2
        and len({b - a for a, b in zip(st, st[1:])}) == 1 and exp[:3] == (180, 610, 5),
        "the committed crontab changed -- re-derive before trusting W1")
    chk("W1 live crontab -> union window (180, 610, 5, Mon-Fri)", shape(H.parse_orchestrator_window(live)) == exp,
        "first line only (595) or wrong union")
    chk("W2 control: the main line alone -> (180, 595, 5) = S99-B's baseline",
        shape(H.parse_orchestrator_window(MAIN)) == (180, 595, 5, (1, 2, 3, 4, 5)), "single-line path changed")
    chk("W3 order does not matter: closing line above the main line -> (180, 610)",
        shape(H.parse_orchestrator_window(CLOSE + "\n" + MAIN))[:2] == (180, 610),
        "the old first-match collapse (600, 610) is back")
    chk("W4 a gap between lines raises (03-05 and 08-09)",
        raises("*/5 03-05 * * 1-5" + TAIL + "\n*/5 08-09 * * 1-5" + TAIL), "a gap would read 'not firing' inside it")
    chk("W5 a mixed step raises (*/5 03-09 then 0,30 10)",
        raises(MAIN + "\n0,30 10 * * 1-5" + TAIL), "15-min / 30-min holes read as missed cycles")
    chk("W6 lines on different weekdays raise", raises(MAIN + "\n0,5,10 10 * * 1-6" + TAIL),
        "Saturday closing cycles alarm all Saturday")
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        w = H.resolve_window("*/5 03-05 * * 1-5" + TAIL + "\n*/5 08-09 * * 1-5" + TAIL)
    chk("W7 an unparseable union falls back to DEFAULT_WINDOW, loudly", w is H.DEFAULT_WINDOW and "[WINDOW]" in buf.getvalue(),
        "silent fallback, or no fallback")
    win = H.parse_orchestrator_window(live)
    mon = datetime(2026, 10, 26, tzinfo=UTC)
    chk("W8 band covers the closing cycles: 09:58 and 10:12 UTC in, 10:15 out",
        H.in_alert_window(mon.replace(hour=9, minute=58), win)[0] and H.in_alert_window(mon.replace(hour=10, minute=12), win)[0]
        and not H.in_alert_window(mon.replace(hour=10, minute=15), win)[0], "closing cycles outside the band")
    chk("W9 one irregular line parses exactly as before ('0,5 3-9' -> 180, 545, step 5)",
        shape(H.parse_orchestrator_window("0,5 3-9 * * 1-5" + TAIL)) == (180, 545, 5, (1, 2, 3, 4, 5)),
        "the single-line path was changed by the union")

    def sends(window, now, rows):
        sent = []
        with contextlib.redirect_stdout(io.StringIO()):
            H.HealthMonitor(now_utc=now, send=lambda lv, m, c: sent.append((lv, m)) or True,
                            is_trading_day=lambda: True, window=window,
                            state_path=Path(tempfile.mkdtemp()) / "s.json",
                            fetch_rows=lambda: rows).run()
        return sent
    t = mon.replace(hour=10, minute=12)
    chk("W10 closing cycles missing at 10:12 UTC -> 'Orchestrator not firing' is sent",
        [m for _, m in sends(win, t, [])] == ["Orchestrator not firing"], "closing cycles unmonitored")
    chk("W10c control: with the main-line window the same tick sends nothing (gated)",
        sends(H.parse_orchestrator_window(MAIN), t, []) == [], "W10 would pass for a reason other than the union")
    return out


MUTANTS = {
    "M1 first line wins again": (
        "    if len(parsed) == 1:\n        return parsed[0][0]\n",
        "    if len(parsed) >= 1:\n        return parsed[0][0]\n",
        {"W1 live crontab -> union window (180, 610, 5, Mon-Fri)",
         "W3 order does not matter: closing line above the main line -> (180, 610)",
         "W8 band covers the closing cycles: 09:58 and 10:12 UTC in, 10:15 out",
         "W10 closing cycles missing at 10:12 UTC -> 'Orchestrator not firing' is sent"}),
    "M2 no uniform-step check": (
        "    if len(gaps) != 1:\n", "    if False:\n",
        {"W4 a gap between lines raises (03-05 and 08-09)", "W5 a mixed step raises (*/5 03-09 then 0,30 10)",
         "W7 an unparseable union falls back to DEFAULT_WINDOW, loudly"}),
    "M3 no weekday check": (
        "    if len(dow_sets) != 1:\n", "    if False:\n",
        {"W6 lines on different weekdays raise"}),
}


def main() -> int:
    src = MONITOR.read_text(encoding="utf-8-sig")
    if "S100_R42_UNION" not in src:
        print("MONITOR WINDOW UNION FAIL: monitor_orchestrator_health.py lacks S100_R42_UNION"); return 1
    res = cells(load(src, "mon_s100_r42"))
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for i, (mname, (old, new, must_fail)) in enumerate(MUTANTS.items()):
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if src.count(old) != 1:
            not_applied.append(mname); continue
        try:
            mres = {n: ok for n, ok, _ in cells(load(src.replace(old, new, 1), f"mon_s100_r42_m{i}"))}
        except Exception as e:
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
        print("MONITOR WINDOW UNION FAIL"); return 1
    print("MONITOR WINDOW UNION ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
