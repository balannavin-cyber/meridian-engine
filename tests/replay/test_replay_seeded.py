#!/usr/bin/env python3
"""S90 / AM-1 — seeded defects on a golden day (roadmap R1.6, "test the tests").

Each case takes the 2026-10-01 SENSEX fixture, injects one defect in memory, and asserts that the
production runner (check_contracts_shadow.evaluate) reports it — and that the clean day does not.
Offline: no database, no network. Run: python3 tests/replay/test_replay_seeded.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests" / "replay"))
import check_contracts_shadow as runner  # noqa: E402
import replay_contracts as R  # noqa: E402
from fixture_client import FixtureClient  # noqa: E402

DAY = ROOT / "tests" / "golden" / "2026-10-01_SENSEX"
AS_OF = datetime(2026, 10, 1, 6, 4, tzinfo=timezone.utc)  # 11:34 IST, cycle 11:30
spec = json.loads((ROOT / "tests" / "replay" / "contracts.json").read_text())
CONTRACTS = [R.fixture_scope(c) for c in spec["contracts"]
             if c["relation_name"] in {"option_chain_snapshots", "gex_strike_snapshots", "gamma_metrics",
                                       "market_spot_snapshots"} and c.get("scope_symbol") == "SENSEX"]
NAMES = {c["product"] for c in CONTRACTS}
EDGES = [tuple(e) for e in spec["lineage"] if e[0] in NAMES and e[1] in NAMES]
TD, PD = R.offline_calendar()
NOW = datetime.now(timezone.utc)


def run(sb):
    final, own, _ = runner.evaluate(sb, CONTRACTS, EDGES, AS_OF, NOW, TD, PD)
    return {p: s for p, (s, _) in final.items()}, {p: s for p, (s, _) in own.items()}


def rows_between(sb, table, lo, hi):
    return [r for r in sb.tables[table] if lo <= r["ts"][:19] < hi]


fails = 0
def check(name, cond, got):
    global fails
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {got}")
    fails += 0 if cond else 1


# 0. clean day: everything OK
final, own = run(FixtureClient([DAY]))
check("clean day all OK", set(final.values()) == {"OK"}, final)

# 1. frozen chain (the 10-02 shape): spot identical across the last 4 cycles -> chain STALE, dependants STALE
sb = FixtureClient([DAY])
for r in rows_between(sb, "option_chain_snapshots", "2026-10-01T05:40", "2026-10-01T06:04"):
    r["spot"] = "72000.0"
final, own = run(sb)
check("frozen chain -> chain STALE", own["option_chain_snapshots:SENSEX"] == "STALE", own["option_chain_snapshots:SENSEX"])
check("frozen chain -> gamma STALE (lineage)", final["gamma_metrics:SENSEX"] == "STALE", final["gamma_metrics:SENSEX"])
check("frozen chain -> strike GEX STALE (lineage)", final["gex_strike_snapshots:SENSEX"] == "STALE", final["gex_strike_snapshots:SENSEX"])

# 2. dropped compute cycles: gamma rows gone for the last 20 min -> gamma MISSING (freshness)
sb = FixtureClient([DAY])
sb.tables["gamma_metrics"] = [r for r in sb.tables["gamma_metrics"] if r["ts"][:19] < "2026-10-01T05:44"]
final, own = run(sb)
check("dropped gamma cycles -> MISSING", own["gamma_metrics:SENSEX"] == "MISSING", own["gamma_metrics:SENSEX"])
check("dropped gamma -> chain unaffected", own["option_chain_snapshots:SENSEX"] == "OK", own["option_chain_snapshots:SENSEX"])

# 3. partial chain: a second expiry leaks into the front-only cycle -> DEGRADED (shape)
sb = FixtureClient([DAY])
newest = max(r["ts"] for r in sb.tables["option_chain_snapshots"] if r["ts"][:19] < "2026-10-01T06:04")
for r in sb.tables["option_chain_snapshots"]:
    if r["ts"] == newest and r["option_type"] == "PE":
        r["expiry_date"] = "2026-10-08"
final, own = run(sb)
check("two expiries in a front-only cycle -> DEGRADED", own["option_chain_snapshots:SENSEX"] == "DEGRADED", own["option_chain_snapshots:SENSEX"])

# 4. holiday: same rows, scored on a closed day -> CLOSED, never STALE/MISSING
final, _, _ = runner.evaluate(FixtureClient([DAY]), CONTRACTS, EDGES,
                           datetime(2026, 10, 2, 6, 4, tzinfo=timezone.utc), NOW, TD, PD)
check("closed day -> all CLOSED", {s for s, _ in final.values()} == {"CLOSED"}, {p: s for p, (s, _) in final.items()})

print("SEEDED " + ("ALL PASS" if fails == 0 else f"{fails} FAIL"))
sys.exit(1 if fails else 0)
