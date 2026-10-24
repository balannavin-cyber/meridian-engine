#!/usr/bin/env python3
"""S100 R4 (ruling S100-E): preopen_probe.py -- the 09:09 IST broker access check -- offline, with controls and mutants.

Every collaborator is a stub: the Dhan client, the Kite client, the sender, the calendar and the ledger. No
network, no database, no credential; the probe module is loaded from source so mutants can be applied.

Rule 0 -- what each cell would catch:
  P1  a healthy morning pages (noise)                     P6  one 5xx blip pages (no retry)
  P2  the 10-21 subscription lapse (806 / DH-902) is not named SUBSCRIPTION, or not paged
  P3  a Dhan token failure is not TOKEN_EXPIRED           P7  "pre-open print not yet in" pages (it is info only)
  P4  a Kite token failure is not paged                   P8  the info line is absent or wrong
  P5  a holiday probes and pages                          P9  an undelivered page reads as success
  P10 an auth failure is retried (it never recovers in 5 s; a retry only delays the page)
Mutants M1-M6 each remove one of these; a mutant whose named cells all pass means those cells assert nothing.
"""
from __future__ import annotations

import contextlib
import io
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "preopen_probe.py"
NOW = datetime(2026, 10, 26, 3, 39, 5, tzinfo=timezone.utc)      # Mon 09:09:05 IST
PREV = "2026-10-23"


def load(src: str, name: str) -> types.ModuleType:
    mod = types.ModuleType(name); mod.__file__ = str(PROBE); sys.modules[name] = mod
    exec(compile(src, str(PROBE), "exec"), mod.__dict__)
    return mod


class Ledger:
    def __init__(self): self.final = None
    def complete(self, notes=None): self.final = ("SUCCESS", 0, notes, None); return 0
    def exit_with_reason(self, reason, exit_code=0, notes=None, error_message=None):
        self.final = (reason, exit_code, notes, error_message); return exit_code


class Dhan:
    """fail: {'expiry'|'ltp'|'intraday': [exc, exc, ...]} raised in order, then succeed."""
    def __init__(self, fail=None, ltp=22811.35, close=22811.35):
        self.fail = {k: list(v) for k, v in (fail or {}).items()}; self.calls = []
        self.ltp, self.close = ltp, close
    def _maybe(self, k):
        self.calls.append(k)
        if self.fail.get(k):
            raise self.fail[k].pop(0)
    def get_expiry_list(self, underlying_scrip, underlying_seg):
        self._maybe("expiry"); return {"data": ["2026-10-27"], "status": "success"}
    def get_ltp(self, ids, exchange_segment):
        self._maybe("ltp"); return {"data": {"IDX_I": {"13": {"last_price": self.ltp}, "51": {"last_price": 73709.69}}}}
    def _post(self, path, payload):
        assert path == "/v2/charts/intraday" and payload["fromDate"].startswith(PREV)
        self._maybe("intraday"); return {"close": [22800.0, self.close]}


class Kite:
    def __init__(self, exc=None): self.exc = exc; self.calls = 0
    def profile(self):
        self.calls += 1
        if self.exc: raise self.exc
        return {"user_id": "XX0000"}


def case(P, *, dhan=None, kite=None, trading=True, send_ok=True):
    dhan = dhan or Dhan(); kite = kite or Kite(); sent = []; led = Ledger(); sleeps = []
    with contextlib.redirect_stdout(io.StringIO()) as out:
        rc = P.run(NOW, dhan_factory=lambda: dhan, kite_factory=lambda: kite,
                   send=lambda m, c: sent.append((m, c)) or send_ok, is_trading_day=lambda: trading,
                   prev_trading_day=lambda d: PREV, log=led, sleep=sleeps.append)
    return rc, sent, led.final, dhan, kite, sleeps, out.getvalue()


def cells(P) -> list[tuple[str, bool, str]]:
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    rc, sent, fin, *_ = case(P, dhan=Dhan(ltp=22850.0))
    chk("P1 all access OK -> no page, SUCCESS exit 0", rc == 0 and sent == [] and fin[0] == "SUCCESS", "a healthy morning pages")
    rc, sent, fin, *_ = case(P, dhan=Dhan(fail={"expiry": [RuntimeError("Dhan HTTP error | status=400 | 806 DH-902 Data APIs not subscribed")]}))
    chk("P2 Dhan 806 / DH-902 -> one page naming SUBSCRIPTION, DATA_ERROR exit 1",
        rc == 1 and len(sent) == 1 and "SUBSCRIPTION" in sent[0][1]["checks"] and "806" in sent[0][1]["checks"]
        and fin[0] == "DATA_ERROR", "the 10-21 lapse unnamed or unpaged")
    rc, sent, fin, *_ = case(P, dhan=Dhan(fail={"ltp": [RuntimeError("Dhan HTTP error | status=401 | Unauthorized DH-901")]}))
    chk("P3 Dhan 401 -> TOKEN in the page, TOKEN_EXPIRED exit 1",
        rc == 1 and len(sent) == 1 and "TOKEN" in sent[0][1]["checks"] and fin[0] == "TOKEN_EXPIRED", "token failure misclassified")
    rc, sent, fin, _, kite, *_ = case(P, kite=Kite(RuntimeError("Incorrect `api_key` or `access_token`.")))
    chk("P4 Kite profile() fails -> page names Kite, TOKEN_EXPIRED exit 1",
        rc == 1 and len(sent) == 1 and "Kite token" in sent[0][0] and kite.calls == 1 and fin[0] == "TOKEN_EXPIRED",
        "a dead Kite token is found only at the 09:10 preflight")
    rc, sent, fin, dhan, kite, *_ = case(P, trading=False)
    chk("P5 holiday -> no broker call, no page, HOLIDAY_GATE exit 0",
        rc == 0 and sent == [] and dhan.calls == [] and kite.calls == 0 and fin[0] == "HOLIDAY_GATE", "holiday probes or pages")
    rc, sent, fin, dhan, _, sleeps, _ = case(P, dhan=Dhan(fail={"expiry": [RuntimeError("Dhan HTTP error | status=502 | Bad Gateway")]}))
    chk("P6 one 5xx blip -> retried once after RETRY_S, no page",
        rc == 0 and sent == [] and dhan.calls.count("expiry") == 2 and sleeps == [P.RETRY_S], "a blip pages")
    rc, sent, fin, *_ = case(P, dhan=Dhan(ltp=22811.35, close=22811.35))
    chk("P7 pre-open print not yet in (LTP == prev close) -> NOT paged", rc == 0 and sent == [], "info treated as a failure")
    chk("P8 the info line says 'not yet in' and is in the ledger notes",
        fin is not None and "pre-open print not yet in" in (fin[2] or ""), "info line absent or wrong")
    rc, sent, fin, *_, so = case(P, kite=Kite(RuntimeError("Incorrect `api_key` or `access_token`.")), send_ok=False)
    chk("P9 undelivered page -> still exit 1, logged delivered=False", rc == 1 and "delivered=False" in so,
        "an undelivered page reads as success")
    rc, sent, fin, dhan, _, sleeps, _ = case(P, dhan=Dhan(fail={"expiry": [RuntimeError("status=400 | 806 DH-902")] * 2}))
    chk("P10 auth / subscription failures are not retried", dhan.calls.count("expiry") == 1 and sleeps == [],
        "a retry delays the page by RETRY_S for nothing")
    return out


MUTANTS = {
    "M1 806 not recognised": ('    if "806" in msg or "dh-902" in low:\n', '    if False:\n',
                              {"P2 Dhan 806 / DH-902 -> one page naming SUBSCRIPTION, DATA_ERROR exit 1"}),
    "M2 info pages": ('    if not failed:\n', '    if not failed and not any("not yet" in i for i in info):\n',
                      {"P7 pre-open print not yet in (LTP == prev close) -> NOT paged"}),
    "M3 no retry": ('        sleep(RETRY_S)\n        try:\n            return True, fn(), ""\n',
                    '        sleep(RETRY_S)\n        try:\n            raise e\n',
                    {"P6 one 5xx blip -> retried once after RETRY_S, no page"}),
    "M4 no holiday gate": ('    if not open_today:\n', '    if False:\n',
                           {"P5 holiday -> no broker call, no page, HOLIDAY_GATE exit 0"}),
    "M6 info line dropped": ('            info.append(f"NIFTY LTP', '            (lambda *a: None)(f"NIFTY LTP',
                             {"P8 the info line says 'not yet in' and is in the ledger notes"}),
    "M5 Kite not checked": ('        prof = kite_factory().profile()\n', '        prof = {}\n',
                            {"P4 Kite profile() fails -> page names Kite, TOKEN_EXPIRED exit 1",
                             "P9 undelivered page -> still exit 1, logged delivered=False"}),
}


def main() -> int:
    src = PROBE.read_text(encoding="utf-8-sig")
    res = cells(load(src, "probe_s100_r4"))
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for i, (mname, (old, new, must_fail)) in enumerate(MUTANTS.items()):
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if src.count(old) != 1:
            not_applied.append(mname); continue
        try:
            mres = {n: ok for n, ok, _ in cells(load(src.replace(old, new, 1), f"probe_s100_r4_m{i}"))}
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
        print("PREOPEN PROBE FAIL"); return 1
    print("PREOPEN PROBE ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
