#!/usr/bin/env python3
"""S90 / AM-1 — seeded defects on a golden day (roadmap R1.6, "test the tests").

Each case takes the 2026-10-01 SENSEX fixture, injects one defect in memory, and asserts that the
production runner (check_contracts_shadow.evaluate) reports it — and that the clean day does not.
Offline: no database, no network. Run: python3 tests/replay/test_replay_seeded.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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


# ---------------------------------------------------------------- cases 5-11 helpers
IST = ZoneInfo("Asia/Kolkata")
DATE = "2026-10-01"
CHAIN, GEX, GAMMA, SPOT = ("option_chain_snapshots:SENSEX", "gex_strike_snapshots:SENSEX",
                           "gamma_metrics:SENSEX", "market_spot_snapshots:SENSEX")


def as_of(cycle_ist: str, offset_min: int = 4) -> datetime:
    """UTC as-of for an IST cycle, read at cycle + 4 min — replay_contracts.AS_OF_OFFSET."""
    t = datetime.fromisoformat(f"{DATE}T{cycle_ist}:00").replace(tzinfo=IST)
    return (t + timedelta(minutes=offset_min)).astimezone(timezone.utc)


def score(sb, when, contracts=None, edges=None):
    """(final, own, detail) as plain dicts: own[p] -> (status, reason)."""
    cs = CONTRACTS if contracts is None else contracts
    es = EDGES if edges is None else edges
    final, own, detail = runner.evaluate(sb, cs, es, when, NOW, TD, PD)
    return ({p: s for p, (s, _) in final.items()}, own, detail)


def keep(sb, table, pred):
    sb.tables[table] = [r for r in sb.tables[table] if pred(r)]
    sb._sorted.clear()  # the client caches sorted views per (table, col, eqs)
    return sb


def minute(r):
    return r["ts"][:16]


def chain_rows_band(contracts, band):
    """The chain contract with its row band restored (fixture_scope sets it to None)."""
    out = []
    for c in contracts:
        if c["relation_name"] == "option_chain_snapshots":
            exp = dict(c.get("expected_per_cycle") or {}); exp["rows"] = band
            c = {**c, "expected_per_cycle": exp}
        out.append(c)
    return out


def nearest_per_cycle(sb, table, n):
    """Depth-1 shape: keep only the n rows nearest that cycle's spot, every cycle."""
    by = {}
    for r in sb.tables[table]:
        by.setdefault(r["ts"], []).append(r)
    out = []
    for _, rows in by.items():
        spot = max(float(r["spot"]) for r in rows)
        out.extend(sorted(rows, key=lambda r: abs(float(r["strike"]) - spot))[:n])
    sb.tables[table] = out
    sb._sorted.clear()
    return sb


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

# ============================================================ R1.6, the four owed cases
# Expectations below were derived from the runner's arithmetic BEFORE being run, and are
# recorded in scratch/s91/r16_plan.txt. own_status fails on age_min > freshness_sla_min
# (strict), and replay reads at cycle + 4 min; so for cadence 5 / SLA 10 the age at
# cycle T+4 with the last write at T-5k is 4 + 5k: k=1 -> 8.9 OK, k=2 -> 13.9 MISSING.

# 5. truncated tail (the 08-20 / 07-31 shape, tech_debt.md:3071): the chain writer stops
#    ~80 min early having written a plausible row count, which a FLOOR cannot see.
sb = FixtureClient([DAY])
n_chain_full = len(sb.tables["option_chain_snapshots"])
keep(sb, "option_chain_snapshots", lambda r: minute(r) <= f"{DATE}T08:30")  # 14:00 IST
n_chain_cut = len(sb.tables["option_chain_snapshots"])
cyc_cut = len({r["ts"] for r in sb.tables["option_chain_snapshots"]})
for cycle, want in (("14:00", "OK"), ("14:05", "OK"), ("14:10", "MISSING")):
    final, own, detail = score(sb, as_of(cycle))
    check(f"truncated tail: chain own {want} at {cycle}", own[CHAIN][0] == want,
          f"{own[CHAIN][0]} age={detail[CHAIN].get('age_min')}")
final, own, detail = score(sb, as_of("14:10"))
check("truncated tail: gamma final STALE by lineage", final[GAMMA] == "STALE", final[GAMMA])
check("truncated tail: strike GEX final STALE by lineage", final[GEX] == "STALE", final[GEX])
check("truncated tail: dependants' OWN status uncontaminated",
      (own[GAMMA][0], own[GEX][0]) == ("OK", "OK"), (own[GAMMA][0], own[GEX][0]))
# the control: the old floor-style check still PASSES on the same seeded day, at the same
# moment the contract reads MISSING. If this ever fails the case no longer demonstrates
# the floor's blindness and must be re-derived, not re-tuned.
check("truncated tail: CONTROL a >=60-row floor still passes (floor is blind)",
      n_chain_cut >= 60 and cyc_cut >= 60, f"{n_chain_cut} rows / {cyc_cut} cycles kept of {n_chain_full}")

# 6a. depth-1 day on strike GEX: 161 rows/cycle -> 10. Row band [100,200] is live here.
sb = nearest_per_cycle(FixtureClient([DAY]), "gex_strike_snapshots", 10)
final, own, detail = score(sb, AS_OF)
check("depth-1: strike GEX own DEGRADED", own[GEX][0] == "DEGRADED",
      f"{own[GEX][0]} rows={detail[GEX].get('rows_at_newest')}")
check("depth-1: reason names the row band", "rows 10 outside" in (own[GEX][1] or ""), own[GEX][1])
check("depth-1: movement abstains (gex_cr still varies, so not STALE)",
      "unchanged across" not in (own[GEX][1] or ""), own[GEX][1])
check("depth-1: chain and gamma unaffected", (own[CHAIN][0], own[GAMMA][0]) == ("OK", "OK"),
      (own[CHAIN][0], own[GAMMA][0]))

# 6b. the same shape on the CHAIN is invisible in replay, because fixture_scope() sets
#     rows -> None. (i) asserts the masking; (ii) is its control — the check works, only
#     the override hides it. Without (ii), (i) cannot be told from a broken shape check.
sb = nearest_per_cycle(FixtureClient([DAY]), "option_chain_snapshots", 10)
_, own, detail = score(sb, AS_OF)
check("depth-1 chain: (i) MASKED by fixture_scope rows=None", own[CHAIN][0] == "OK",
      f"{own[CHAIN][0]} rows={detail[CHAIN].get('rows_at_newest')}")
_, own2, _ = score(sb, AS_OF, contracts=chain_rows_band(CONTRACTS, [394, 394]))
check("depth-1 chain: (ii) CONTROL with the measured band [394,394] -> DEGRADED",
      own2[CHAIN][0] == "DEGRADED", own2[CHAIN][0])

# 7. a dropped cycle mid-session. The honest answer: ONE dropped cycle is inside the SLA
#    and is NOT caught. The test pins the boundary so a later SLA change has to move a
#    failing assertion rather than quietly widen the blind spot.
sb = keep(FixtureClient([DAY]), "option_chain_snapshots", lambda r: minute(r) != f"{DATE}T06:30")
_, own, detail = score(sb, as_of("12:00"))  # 12:00 IST cycle absent
check("1 dropped cycle: NOT caught, own OK (age ~8.9 <= SLA 10)", own[CHAIN][0] == "OK",
      f"{own[CHAIN][0]} age={detail[CHAIN].get('age_min')}")
_, own, detail = score(sb, as_of("12:05"))  # the hole now sits inside the movement window
check("1 dropped cycle: movement window still has its 4 points",
      detail[CHAIN].get("movement_points") == 4, detail[CHAIN].get("movement_points"))
sb = keep(FixtureClient([DAY]), "option_chain_snapshots",
          lambda r: minute(r) not in (f"{DATE}T06:30", f"{DATE}T06:35"))
_, own, detail = score(sb, as_of("12:05"))
check("2 dropped cycles: CAUGHT, own MISSING (age ~13.9 > SLA 10)", own[CHAIN][0] == "MISSING",
      f"{own[CHAIN][0]} age={detail[CHAIN].get('age_min')}")

# 8. spot death at 15:09. S90-L gave spot session_end_ist 15:15 so the ADR-022 CAS guard
#    stopping capture at ~15:15 no longer raised a false MISSING at 15:20/15:25. The
#    question that leaves open is whether a feed that really died can hide behind it.
sb = keep(FixtureClient([DAY]), "market_spot_snapshots", lambda r: minute(r) <= f"{DATE}T09:39")
last_spot = max(r["ts"] for r in sb.tables["market_spot_snapshots"])
_, own, detail = score(sb, as_of("15:10"))
check("spot death 15:09: own OK at 15:10 (age ~4.9, inside SLA 5 — the boundary)",
      own[SPOT][0] == "OK", f"{own[SPOT][0]} age={detail[SPOT].get('age_min')} last={last_spot[:19]}")
for cycle in ("15:15", "15:20", "15:25"):
    _, own, detail = score(sb, as_of(cycle))
    check(f"spot death 15:09: own MISSING at {cycle}", own[SPOT][0] == "MISSING",
          f"{own[SPOT][0]} age={detail[SPOT].get('age_min')}")
    check(f"spot death 15:09: reached THROUGH the session-end branch at {cycle}",
          detail[SPOT].get("judged_at_session_end") == "15:15", detail[SPOT].get("judged_at_session_end"))
# the control: the clean fixture at the very same as-ofs reads OK. Seeded MISSING and
# clean OK at identical as-ofs is the proof that the session-end fix did not blind the
# check; either half alone proves nothing.
clean = FixtureClient([DAY])
for cycle in ("15:15", "15:20", "15:25"):
    _, own, detail = score(clean, as_of(cycle))
    check(f"spot death 15:09: CONTROL clean day own OK at {cycle}", own[SPOT][0] == "OK",
          f"{own[SPOT][0]} age={detail[SPOT].get('age_min')}")
# 8b. the 15:30 cycle, and a CORRECTION to the expectation this test was written with.
#     r16_plan.txt predicted MISSING at 15:30 too. It is CLOSED, on both the seeded and
#     the clean day, and the measurement is right: replay reads a cycle at cycle + 4 min,
#     so the 15:30 cycle is read at 15:34, past SESSION_CLOSE 15:30, and the calendar
#     branch (:274) returns before any read happens. The pinned expected files already
#     carry CLOSED at 15:30 for all four products. Asserted rather than dropped, because
#     it is a real property: the LAST cycle of the day cannot report a feed death.
for label, client in (("seeded-dead", sb), ("clean", clean)):
    _, own, detail = score(client, as_of("15:30"))
    check(f"15:30 cycle is CLOSED, not MISSING ({label}) — read at 15:34 > SESSION_CLOSE",
          own[SPOT][0] == "CLOSED" and detail[SPOT] == {"calendar": "closed"},
          f"{own[SPOT][0]} {detail[SPOT]}")

# ====================================== 9-11: check paths that had never fired on a fixture
# 9. presence -> MISSING, told apart from freshness -> MISSING. Different branches
#    (check_contracts_shadow.py:94 vs :120) that both report MISSING.
sb = keep(FixtureClient([DAY]), "market_spot_snapshots", lambda r: False)
_, own, detail = score(sb, AS_OF)
check("presence: no row for scope -> own MISSING", own[SPOT][0] == "MISSING", own[SPOT][0])
check("presence: via the presence branch, not an age reason",
      detail[SPOT] == {"presence": False} and "min old" not in (own[SPOT][1] or ""),
      (detail[SPOT], own[SPOT][1]))

# 10. UNKNOWN, latest-only product judged in the past (:269). No frozen relation can
#     exercise it — all four carry ts or run_id in grain — so the contract is synthetic.
latest_only = {**next(c for c in CONTRACTS if c["product"] == GAMMA),
               "product": "synthetic_latest_only:SENSEX", "grain": ["symbol"]}
_, own, detail = score(FixtureClient([DAY]), AS_OF, contracts=[latest_only], edges=[])
p = "synthetic_latest_only:SENSEX"
check("latest-only product in the past -> UNKNOWN", own[p][0] == "UNKNOWN", own[p][0])
check("latest-only: says why, and records no history", detail[p] == {"history": False}
      and "latest-only" in (own[p][1] or ""), (detail[p], own[p][1]))

# 11. UNKNOWN, a check that cannot run (:284) — an exception must never become OK.
class Exploding(FixtureClient):
    def select(self, *a, **k):
        raise RuntimeError("seeded read failure")

_, own, _ = score(Exploding([DAY]), AS_OF)
check("a check that cannot run -> UNKNOWN, never OK",
      all(own[p][0] == "UNKNOWN" for p in (CHAIN, GEX, GAMMA, SPOT)),
      {p: own[p][0] for p in (CHAIN, GEX, GAMMA, SPOT)})
check("a check that cannot run: reason names the failure",
      (own[CHAIN][1] or "").startswith("check failed:"), own[CHAIN][1])

print("SEEDED " + ("ALL PASS" if fails == 0 else f"{fails} FAIL"))
sys.exit(1 if fails else 0)
