#!/usr/bin/env python3
"""EXPLAIN gate for MR-PIN2 step 3. Read-only; writes nothing.

Usage: python3 -B gate_explain.py <plan_file>
Exit 0 = PASS, 1 = FAIL. Prints one verdict line plus every offending node.

WHAT MAKES IT FAIL (stated so the check is not documentation -- Rule 0):
  * an empty plan file, a plan containing 'ERROR', or a plan with ZERO scan nodes
    -> 'no plan parsed'. Without this clause a failed EXPLAIN would yield no offending
    node and the gate would print PASS on nothing at all;
  * any node whose name contains 'Seq Scan'  -> a sequential scan on any relation;
  * any SCAN node whose own rows= estimate exceeds 20000.
A plan with only index scans, all estimates <= 20000, passes. A plan that reached a
hist_* relation without an index would print 'Seq Scan on hist_option_bars_1m' and fail
on the second clause; a correctly-indexed plan whose predicate was too wide (a whole day
rather than a 240 s window) would fail on the third.

LIMIT NOTE: Part B's operator ruling (option 1, 2026-11-20, partB_results.md:176-185)
reads the estimate at a Limit node rather than at the unbounded scan beneath it. That
ruling is NOT applied silently here: a scan under a Limit is reported with its Limit's
estimate alongside its own, and the gate still judges the scan's own number. If that
ever fails, the ruling is invoked explicitly in the run log, never by this script.
"""
import re
import sys
from pathlib import Path

LIMIT = 20000
SCAN = re.compile(r"\b((?:Seq|Index Only|Index|Bitmap Heap|Bitmap Index|CTE|Subquery|"
                  r"Function|Values|Sample|Tid|Foreign|Custom)\s+Scan)\b")
ROWS = re.compile(r"\brows=(\d+)")

plan = Path(sys.argv[1]).read_text(encoding="utf-8")
fails, scans, limits = [], 0, []
for raw in plan.splitlines():
    line = raw.strip()
    if line.startswith("->"):
        line = line[2:].strip()
    if line.startswith("Limit"):
        m = ROWS.search(line)
        limits.append(m.group(1) if m else "?")
    m = SCAN.search(line)
    if not m:
        continue
    scans += 1
    node = m.group(1)
    r = ROWS.search(line)
    est = int(r.group(1)) if r else -1
    if "Seq Scan" in node:
        fails.append(f"SEQ SCAN: {line}")
    elif est > LIMIT:
        fails.append(f"ROWS {est} > {LIMIT}: {line}")

if not plan.strip() or "ERROR" in plan or scans == 0:
    print(f"scan nodes: {scans}; bytes: {len(plan)}; "
          f"ERROR token: {'yes' if 'ERROR' in plan else 'no'}")
    print("GATE FAIL: no plan parsed")
    sys.exit(1)

print(f"scan nodes: {scans}; Limit estimates seen: {','.join(limits) or 'none'}")
for f in fails:
    print("  FAIL " + f)
print("GATE " + ("PASS" if not fails else "FAIL"))
sys.exit(0 if not fails else 1)
