#!/usr/bin/env python3
"""S100 R4 (ruling S100-F; TD-S80-NEW-17): the wsfeed retry timer and the deduped preflight alert -- offline.

The defect: merdian-wsfeed.service gives up after StartLimitBurst=3 preflight failures ~10 s apart and nothing
starts it again that session (10-15 and 10-19: 03:40:03-03:40:26 UTC). The fix: bin/wsfeed_retry.sh, run every
5 min by merdian-wsfeed-retry.timer, starts the feed between 03:45 and 09:55 UTC if it is not active; and the
preflight / OnFailure alerts are deduped to one Telegram send per 30 min, so the retry cannot flood the chat.

The real scripts run in a temp engine directory (MERDIAN_ENGINE_DIR) with `systemctl`, `curl`, `date` and
`python3` stubbed on PATH. No network, no systemd, no credential (the .env holds dummy values).
Mutants M1-M4 each remove one part; a mutant whose named cells all pass means those cells assert nothing.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = ["bin/wsfeed_alert.sh", "bin/wsfeed_preflight.sh", "bin/wsfeed_retry.sh"]
UNITS = REPO / "deploy" / "systemd"
EPOCH = 1_793_000_000

STUBS = {
    "date": '#!/usr/bin/env bash\nfor a in "$@"; do case "$a" in +%s) echo "$FAKE_EPOCH"; exit 0;; '
            '+%H%M) echo "$FAKE_HHMM"; exit 0;; esac; done\necho "2026-10-26T03:50:00Z"\n',
    "systemctl": '#!/usr/bin/env bash\necho "$*" >> "$STUB_LOG/systemctl"\n'
                 'if [ "$1" = "is-active" ]; then exit "${FAKE_ACTIVE:-3}"; fi\nexit 0\n',
    "curl": '#!/usr/bin/env bash\necho "curl" >> "$STUB_LOG/curl"\nexit 0\n',
    "python3": '#!/usr/bin/env bash\ncat >/dev/null\necho "preflight FAIL: stub" >&2\nexit 1\n',
}


def sandbox(sources: dict[str, str]) -> Path:
    d = Path(tempfile.mkdtemp(prefix="s100_wsfeed_"))
    (d / "bin").mkdir(); (d / "logs").mkdir(); (d / "stub").mkdir(); (d / "rec").mkdir()
    for rel, text in sources.items():
        p = d / rel; p.write_text(text); p.chmod(0o755)
    (d / ".env").write_text("TELEGRAM_BOT_TOKEN=dummy-not-a-token\nTELEGRAM_CHAT_ID=0\n"
                            "ZERODHA_API_KEY=x\nZERODHA_ACCESS_TOKEN=y\n")
    for name, body in STUBS.items():
        p = d / "stub" / name; p.write_text(body); p.chmod(0o755)
    return d


def sh(d: Path, script: str, *args, hhmm="0350", epoch=EPOCH, active=3, env_extra=None):
    env = {"PATH": f"{d/'stub'}:/usr/bin:/bin", "MERDIAN_ENGINE_DIR": str(d), "STUB_LOG": str(d / "rec"),
           "FAKE_HHMM": hhmm, "FAKE_EPOCH": str(epoch), "FAKE_ACTIVE": str(active), "HOME": str(d)}
    env.update(env_extra or {})
    return subprocess.run(["bash", str(d / script), *args], env=env, capture_output=True, text=True, timeout=20)


def count(d: Path, name: str) -> int:
    p = d / "rec" / name
    return len(p.read_text().splitlines()) if p.exists() else 0


def lines(d: Path, name: str) -> list[str]:
    p = d / "rec" / name
    return p.read_text().splitlines() if p.exists() else []


def age_stamp(d: Path) -> None:
    """Pin the dedupe stamp's mtime to EPOCH, if the code under test wrote one (a mutant may not)."""
    p = d / "logs" / ".wsfeed_alert_sent"
    if p.exists():
        os.utime(p, (EPOCH, EPOCH))


def cells(sources: dict[str, str]) -> list[tuple[str, bool, str]]:
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    d = sandbox(sources)
    sh(d, "bin/wsfeed_alert.sh", "disk 81%"); sh(d, "bin/wsfeed_alert.sh", "disk 82%")
    chk("A1 no dedupe set (disk_guard) -> every call sends", count(d, "curl") == 2, "disk_guard alerts suppressed")
    d = sandbox(sources)
    sh(d, "bin/wsfeed_alert.sh", "x", env_extra={"WSFEED_DEDUPE_S": "1800"})
    age_stamp(d)
    sh(d, "bin/wsfeed_alert.sh", "y", epoch=EPOCH + 60, env_extra={"WSFEED_DEDUPE_S": "1800"})
    log = (d / "logs" / "WSFEED_ALERTS.log").read_text()
    chk("A2 dedupe: second alert 60 s later is suppressed but still logged",
        count(d, "curl") == 1 and "SUPPRESSED" in log and log.count("ALERT: ") == 2, "flood, or a silent drop")
    sh(d, "bin/wsfeed_alert.sh", "z", epoch=EPOCH + 1801, env_extra={"WSFEED_DEDUPE_S": "1800"})
    chk("A3 dedupe: after 1801 s it sends again", count(d, "curl") == 2, "one page per incident, forever")
    d = sandbox(sources)
    (d / ".env").write_text("")
    sh(d, "bin/wsfeed_alert.sh", "x", env_extra={"WSFEED_DEDUPE_S": "1800"})
    chk("A4 no Telegram credentials -> no send and no stamp (the next real send is not suppressed)",
        count(d, "curl") == 0 and not (d / "logs" / ".wsfeed_alert_sent").exists(), "a failed send suppresses the next")
    d = sandbox(sources)
    sh(d, "bin/wsfeed_preflight.sh"); age_stamp(d)
    r2 = sh(d, "bin/wsfeed_preflight.sh", epoch=EPOCH + 300)
    chk("P1 preflight failing twice 5 min apart -> one Telegram send, both exit 1",
        count(d, "curl") == 1 and r2.returncode == 1, "the retry timer floods the chat")
    for hhmm, active, want, name in [("0340", 3, [], "R1 03:40 UTC (the start timer's minute) -> retry does nothing"),
                                     ("1000", 3, [], "R4 10:00 UTC (stop timer owns the end) -> retry does nothing")]:
        d = sandbox(sources); sh(d, "bin/wsfeed_retry.sh", hhmm=hhmm, active=active)
        chk(name, lines(d, "systemctl") == want, "retry outside 03:45-09:55 UTC")
    d = sandbox(sources); sh(d, "bin/wsfeed_retry.sh", hhmm="0350", active=3)
    chk("R2 03:50 UTC, feed not active -> is-active, reset-failed, start",
        lines(d, "systemctl") == ["is-active --quiet merdian-wsfeed.service", "reset-failed merdian-wsfeed.service",
                                  "start --no-block merdian-wsfeed.service"], "a dead feed stays dead")
    d = sandbox(sources); sh(d, "bin/wsfeed_retry.sh", hhmm="0350", active=0)
    chk("R3 03:50 UTC, feed active -> no start", lines(d, "systemctl") == ["is-active --quiet merdian-wsfeed.service"],
        "a running feed is restarted every 5 min")
    d = sandbox(sources); sh(d, "bin/wsfeed_retry.sh", hhmm="0955", active=3)
    chk("R5 09:55 UTC, feed not active -> start (last retry of the band)",
        "start --no-block merdian-wsfeed.service" in lines(d, "systemctl"), "band ends early")
    unit = (UNITS / "merdian-wsfeed-alert.service").read_text()
    timer = (UNITS / "merdian-wsfeed-retry.timer").read_text()
    svc = (UNITS / "merdian-wsfeed-retry.service").read_text()
    chk("U1 units: OnFailure alert deduped 1800; retry timer Mon..Fri 03..09 every 5 min UTC; service runs the script",
        "Environment=WSFEED_DEDUPE_S=1800" in unit and "OnCalendar=Mon..Fri *-*-* 03..09:00/5:00 UTC" in timer
        and "ExecStart=/home/ssm-user/meridian-engine/bin/wsfeed_retry.sh" in svc, "units not as tested")
    return out


MUTANTS = {
    "M1 alert dedupe removed": ("bin/wsfeed_alert.sh",
        'if [ -n "${WSFEED_DEDUPE_S:-}" ] && [ -f logs/.wsfeed_alert_sent ]; then', "if false; then",
        {"A2 dedupe: second alert 60 s later is suppressed but still logged",
         "P1 preflight failing twice 5 min apart -> one Telegram send, both exit 1"}),
    "M2 retry band removed": ("bin/wsfeed_retry.sh",
        'if [ "$hhmm" -lt 345 ] || [ "$hhmm" -ge 1000 ]; then exit 0; fi', "true",
        {"R1 03:40 UTC (the start timer's minute) -> retry does nothing",
         "R4 10:00 UTC (stop timer owns the end) -> retry does nothing"}),
    "M3 is-active check removed": ("bin/wsfeed_retry.sh",
        "if systemctl is-active --quiet merdian-wsfeed.service; then exit 0; fi", "true",
        {"R3 03:50 UTC, feed active -> no start"}),
    "M4 preflight not deduped": ("bin/wsfeed_preflight.sh",
        "    WSFEED_DEDUPE_S=1800 bash bin/wsfeed_alert.sh", "    bash bin/wsfeed_alert.sh",
        {"P1 preflight failing twice 5 min apart -> one Telegram send, both exit 1"}),
}


def main() -> int:
    if not shutil.which("bash"):
        print("WSFEED RETRY FAIL: bash not found"); return 1
    src = {rel: (REPO / rel).read_text() for rel in SCRIPTS}
    if "S100_WSFEED_RETRY" not in src["bin/wsfeed_retry.sh"]:
        print("WSFEED RETRY FAIL: bin/wsfeed_retry.sh lacks S100_WSFEED_RETRY"); return 1
    res = cells(src)
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for mname, (rel, old, new, must_fail) in MUTANTS.items():
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if src[rel].count(old) != 1:
            not_applied.append(mname); continue
        mres = {n: ok for n, ok, _ in cells(dict(src, **{rel: src[rel].replace(old, new, 1)}))}
        survivors += [f"{mname}: {n}" for n in must_fail if mres.get(n, True)]
    for n, ok, f in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   (fails if: {f})"))
    killed = sum(len(v[3]) for k, v in MUTANTS.items() if k not in not_applied) - len(survivors)
    print(f"  cells {len(res)}, failing {len(fails)}; mutants {len(MUTANTS)}, not applied {len(not_applied)}, "
          f"mutant cells killed {killed}, surviving {len(survivors)} (must be 0)")
    for s in not_applied: print(f"  MUTANT NOT APPLIED: {s}")
    for s in unknown: print(f"  MUTANT NAMES NO CELL: {s}")
    for s in survivors: print(f"  MUTANT SURVIVED: {s}")
    if fails or survivors or not_applied or unknown:
        print("WSFEED RETRY FAIL"); return 1
    print("WSFEED RETRY ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
