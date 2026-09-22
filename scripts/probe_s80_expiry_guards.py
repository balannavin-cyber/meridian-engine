#!/usr/bin/env python3
"""probe_s80_expiry_guards.py

Verification for the two S80 guards. Loads each function out of its source file
by AST and executes it in isolation -- no module import, so no credentials, no
network, no Supabase client. Tests the exact text on disk.

  1. compute_gamma_metrics_local.infer_expiry_date  (TD-S79-NEW-12)
     CAN FIRE: must RAISE on a multi-expiry run, not silently pick one.
  2. ingest_option_chain_local.select_expiries      (ADR-025)
     Must pick W1/W2 + monthlies, NOT the first N chronologically.

Host-agnostic: resolves both targets from <this script>/.. so it runs
identically on Local and on EC2. Exit 0 = all pass.
"""
import ast, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def load_fn(filename: str, fn_name: str, ns: dict | None = None):
    src = (ROOT / filename).read_text(encoding="utf-8-sig")
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == fn_name)
    scope = dict(ns or {})
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<probe>", "exec"), scope)
    return scope[fn_name]


def check(label: str, got, want) -> None:
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: {got}")
    if not ok:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


print(f"repo root: {ROOT}\n")

# ── 1. infer_expiry_date — TD-S79-NEW-12 ────────────────────────────────────
print("infer_expiry_date (TD-S79-NEW-12)")
infer = load_fn("compute_gamma_metrics_local.py", "infer_expiry_date", {"Any": object})

check("single expiry", infer([{"expiry_date": "2026-09-22"}]), "2026-09-22")
check("empty input", infer([]), None)
check("repeated same expiry",
      infer([{"expiry_date": "2026-09-22"}, {"expiry_date": "2026-09-22"}]), "2026-09-22")

try:
    bad = infer([{"expiry_date": "2026-09-22"}, {"expiry_date": "2026-09-29"}])
    print(f"  FAIL  CAN FIRE: no raise, returned {bad!r}")
    FAILURES.append("CANNOT FIRE -- multi-expiry run did not raise")
except RuntimeError as e:
    print(f"  PASS  CAN FIRE: {e}")

# ── 2. select_expiries — ADR-025 ────────────────────────────────────────────
print("\nselect_expiries (ADR-025)")
sel = load_fn("ingest_option_chain_local.py", "select_expiries")

# NIFTY-shaped: weeklies on Tue, monthly = last Tue of the month.
nifty = ["2026-09-22", "2026-09-29", "2026-10-06", "2026-10-13",
         "2026-10-20", "2026-10-27", "2026-11-24", "2026-12-29"]
check("NIFTY depth 1", sel(nifty, 1), ["2026-09-22"])
check("NIFTY depth 2", sel(nifty, 2), ["2026-09-22", "2026-09-29"])
check("NIFTY depth 3", sel(nifty, 3), ["2026-09-22", "2026-09-29", "2026-10-27"])
check("NIFTY depth 4", sel(nifty, 4),
      ["2026-09-22", "2026-09-29", "2026-10-27", "2026-11-24"])

# The whole point: depth 4 must NOT be the first four chronologically.
if sel(nifty, 4) == nifty[:4]:
    print("  FAIL  depth 4 collapsed to a chronological slice")
    FAILURES.append("depth 4 == first four chronologically")
else:
    print("  PASS  depth 4 is not a chronological slice")

# SENSEX-shaped: fewer expiries than requested -- must not pad or raise.
sensex = ["2026-09-24", "2026-10-01", "2026-10-08"]
check("SENSEX depth 2", sel(sensex, 2), ["2026-09-24", "2026-10-01"])
check("SENSEX depth 4 (short ladder)", sel(sensex, 4), sensex)

check("depth 0", sel(nifty, 0), [])
check("empty input", sel([], 4), [])

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S):")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("ALL PASS")
