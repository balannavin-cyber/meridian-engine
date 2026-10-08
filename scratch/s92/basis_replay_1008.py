#!/usr/bin/env python3
"""S92 build #2, step 4c: replay all 84 of 2026-10-08's basis runs through the
PATCHED compute_basis_context_local.main().

Not a model of the code -- the real main() is driven, with fetch_recent_futures
returning the rows the live run actually saw, rendered in the exact PostgREST
wire form (validated at string level: stored 312290 -> '.31229', 555900 ->
'.5559', both confirmed against the wire).

TYPE FIDELITY: the CSV carries numerics as strings; PostgREST returns them as
JSON numbers. They are converted to float (empty -> None, matching a JSON null)
so main() sees the same types the live run saw. Left as strings, any arithmetic
on them could raise and surface as a spurious DATA_ERROR -- which is exactly the
signal being measured, so the confound would be indistinguishable from the
result.

Nothing live is written: fetch/upsert/ExecutionLog stubbed AND a process-wide
socket block installed before import, proven by a control call.
"""
import csv, importlib.util, socket, sys
from collections import Counter
from pathlib import Path

REPO = Path("/home/ssm-user/meridian-cc")
sys.path.insert(0, str(REPO))

def _blocked(*a, **k): raise AssertionError("NETWORK BLOCKED (socket-level)")
socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
try:
    socket.create_connection(("127.0.0.1", 9)); CTL = "NOT BLOCKED -- invalid"
except AssertionError:
    CTL = "blocked"
except Exception as e:
    CTL = f"blocked ({type(e).__name__})"
print(f"socket block control: {CTL}")

class NetGuard:
    def __getattr__(self, n):
        def boom(*a, **k): raise AssertionError(f"NETWORK BLOCKED: requests.{n}")
        return boom

class FakeLog:
    last = None
    def __init__(self, **kw): pass
    def exit_with_reason(self, reason, exit_code=0, notes=None, error_message=None):
        FakeLog.last = (reason, exit_code); return exit_code
    def record_write(self, t, n): pass
    def complete(self, notes=None):
        FakeLog.last = ("SUCCESS", 0); return 0

def load():
    spec = importlib.util.spec_from_file_location(
        "cbc_replay", str(REPO / "compute_basis_context_local.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["cbc_replay"] = m
    spec.loader.exec_module(m)
    m.requests = NetGuard()
    m.ExecutionLog = FakeLog
    m.supabase_upsert = lambda table, rows, on_conflict, timeout=60: rows
    return m

def num(v):
    """CSV string -> float, or None for '' (what a JSON null arrives as)."""
    if v is None or v == "":
        return None
    return float(v)

def mkrow(ts, spot, fut, basis, bpct):
    return {"ts": ts, "symbol": "X", "spot_price": num(spot),
            "futures_price": num(fut), "basis": num(basis),
            "basis_pct": num(bpct)}

rows_in = [r for r in csv.DictReader(open(REPO / "scratch/s92/basis_replay_1008.csv"))
           if r.get("run_ist")]
print(f"runs in fixture: {len(rows_in)}")
# prove the conversion actually happened, rather than asserting it in a comment
_s = next((r for r in rows_in if r["row0_spot"]), None)
if _s:
    _r = mkrow(_s["row0_wire"], _s["row0_spot"], _s["row0_fut"],
               _s["row0_basis"], _s["row0_basis_pct"])
    print("type check: spot_price is %s, basis_pct is %s"
          % (type(_r["spot_price"]).__name__, type(_r["basis_pct"]).__name__))

mod = load()
today, replayed = Counter(), Counter()
changed = []
for r in rows_in:
    today[r["today_reason"]] += 1
    rows = []
    if r["row0_wire"]:
        rows.append(mkrow(r["row0_wire"], r["row0_spot"], r["row0_fut"],
                          r["row0_basis"], r["row0_basis_pct"]))
        if r["prev_wire"]:
            rows.append(mkrow(r["prev_wire"], r["prev_spot"], r["prev_fut"],
                              r["prev_basis"], r["prev_basis_pct"]))
    FakeLog.last = None
    mod.fetch_recent_futures = (lambda _s, _rows=rows: list(_rows))
    rc = mod.main()
    reason, code = FakeLog.last or ("(none)", rc)
    replayed[reason] += 1
    if reason != r["today_reason"] or str(code) != r["today_exit"]:
        changed.append((r["run_ist"], r["today_reason"], r["today_exit"],
                        reason, code, r["row0_wire"]))

print()
print("%-20s %8s %10s" % ("exit_reason", "TODAY", "REPLAYED"))
for k in sorted(set(today) | set(replayed)):
    print("%-20s %8d %10d" % (k, today[k], replayed[k]))
print()
print(f"runs whose reason or exit code changed: {len(changed)}")
for ist, t_r, t_c, n_r, n_c, wire in changed:
    print(f"  {ist}  {t_r}/{t_c} -> {n_r}/{n_c}  rows[0]={wire}")
print()
print("DATA_ERROR after patch: %d (target 0)" % replayed["DATA_ERROR"])
print("SKIPPED_NO_INPUT after patch: %d (must stay 12)" % replayed["SKIPPED_NO_INPUT"])
ok = replayed["DATA_ERROR"] == 0 and replayed["SKIPPED_NO_INPUT"] == 12
print("REPLAY " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
