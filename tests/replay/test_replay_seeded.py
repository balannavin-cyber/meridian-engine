#!/usr/bin/env python3
"""S90 / AM-1 — seeded defects on a golden day (roadmap R1.6, "test the tests").

Each case takes a golden-day fixture, injects one defect in memory, and asserts that the
production runner (check_contracts_shadow.evaluate) reports it — and that the clean day does not.
Offline: no database, no network. Under CLAUDE.md rule 23 it is NOT any hour and not without a
memory ceiling — see the guard below; exit 2 means nothing was tested.
Run: ( ulimit -v 700000; python3 tests/replay/test_replay_seeded.py )

Cases 0-4 are the S90 set. Cases 5-11 are AM-2 / S91 (roadmap R1.6), specified in
scratch/s91/r16_plan_merged.txt with every cell pre-registered there before this file was run.

STAGE A note (AM-2 / S91, 2026-10-07) — tests only
--------------------------------------------------
This file does not edit check_contracts_shadow.py, replay_contracts.py, contracts.json or any
fixture under tests/golden/. Every Rule-0 control runs IN-PROCESS, as a contract copy or a
client subclass, never as a source edit:
  * "neuter the freshness branch" is expressed as freshness_sla_min = 600 — the branch then
    cannot fire, so the assertion must flip. Same manipulation, no edit.
  * "force in_range to return True" is expressed as rows = None, which is exactly what in_range
    does with None (check_contracts_shadow.py:66-67). Same manipulation, no edit.
Case 7a asserts TODAY'S behaviour — that one dropped cycle is NOT caught. That is the
pre-registration for Stage B (continuity check + floored `since`), not attempted here.

Cuts taken from the merged plan (they are load-bearing; see its RECONCILIATIONS):
  case 5 truncates the chain at >= 14:35 IST  (plan v1 cut after 14:00 and is correct there)
  case 6 is depth-1 on 2026-08-27 with the derived band [325, 450]  (plan v1 used [394,394] on 10-01)
  case 8 cuts spot at >= 15:09:00 IST, dropping the 15:09:03 row  (plan v1 kept it, so v1's
         15:10 cell is OK and this file's is MISSING — one row, 1.01 min against a 5-min SLA)
"""
from __future__ import annotations


# ---- CLAUDE.md rule 23 guard (ruling S91-A) — no override flag ---------------------------
# Deliberately ahead of every other import, and self-contained (its imports are function-local
# and cheap) so the guard can be exec'd on its own without loading a fixture — which is how it
# was shown to fire for each of its two reasons separately.
def _rule23_refusal():
    """The refusal this run earns under rule 23, or None if it may proceed.

    Fires when RLIMIT_AS is unlimited — a memory regression then OOM-kills the box instead of
    failing the suite (TD-S91-NEW-7: ~0.9 GB per fixture client, two kills on 2026-10-07) —
    or when the IST clock is inside the blocked weekday window 08:30 <= t < 15:40, where the
    suite contends with the live capture chain. Half-open at the top: runnable AT 15:40.
    """
    import resource
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if resource.getrlimit(resource.RLIMIT_AS)[0] == resource.RLIM_INFINITY:
        return "REFUSED: rule 23 — run under ( ulimit -v 700000; … )"
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    if now.weekday() < 5 and 830 <= now.hour * 100 + now.minute < 1540:
        return "REFUSED: rule 23 — fixture suite blocked 08:30–15:40 IST on weekdays"
    return None


_refusal = _rule23_refusal()
if _refusal:
    import sys as _sys

    print(_refusal)
    _sys.exit(2)

import gc
import json
import sys
from collections import Counter
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
GOLDEN = {"2026-10-01": DAY, "2026-08-27": ROOT / "tests" / "golden" / "2026-08-27_SENSEX"}
CHAIN, GEX, GAMMA, SPOT = ("option_chain_snapshots:SENSEX", "gex_strike_snapshots:SENSEX",
                           "gamma_metrics:SENSEX", "market_spot_snapshots:SENSEX")


def as_of(cycle_ist: str, date: str = DATE, offset_min: int = 4) -> datetime:
    """UTC as-of for an IST cycle, read at cycle + 4 min — replay_contracts.AS_OF_OFFSET."""
    t = datetime.fromisoformat(f"{date}T{cycle_ist}:00").replace(tzinfo=IST)
    return (t + timedelta(minutes=offset_min)).astimezone(timezone.utc)


def client(date: str) -> FixtureClient:
    return FixtureClient([GOLDEN[date]])


def score(sb, when, contracts=None, edges=None):
    """(final, own, detail): final[p] -> status; own[p] -> (status, reason); detail[p] -> checks."""
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


def with_fields(contracts, product, **fields):
    """A copy of `contracts` with one product's top-level contract fields replaced.
    Contract copies only — contracts.json is never written."""
    return [({**c, **fields} if c["product"] == product else c) for c in contracts]


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
    """Depth reduction: keep only the n rows nearest that cycle's spot, every cycle. The
    expiry, the cadence and the spot series are untouched, so only the row count moves."""
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


def rows_per_cycle(sb, table):
    return sorted(set(Counter(r["ts"] for r in sb.tables[table]).values()))


def free(*clients):
    """Drop each case's fixture before the next one loads. A FixtureClient holds every
    row of its golden day as a dict plus a sorted-view cache (~0.9 GB measured for a
    dozen of them), and this file is step 2/6 of run_offline.sh on a 1.9 GB box, so a
    client that outlives its case is what OOM-kills the suite. Callers del their own
    names; this drops the last reference and collects."""
    for c in clients:
        c.tables.clear()
        c._sorted.clear()
    gc.collect()


fails = 0
def check(name, cond, got):
    global fails
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {got}")
    fails += 0 if cond else 1


xfails = 0
def xcheck(name, cond, got, why):
    """A cell the merged plan pre-registered that the code does not produce. Recorded as a
    disagreement together with its re-derivation; NEVER resolved by editing the expectation
    (CLAUDE.md Rule 0 clause 3). `cond` is the plan's assertion, not a corrected one."""
    global xfails
    print(f"{'XPASS' if cond else 'XFAIL'}  {name}  {got}  [{why}]")
    xfails += 1


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
free(sb); del sb

# ============================================================ R1.6, the four owed cases
# Every expectation below was derived from the runner's arithmetic and written into
# scratch/s91/r16_plan_merged.txt BEFORE this file was run. own_status fails on
# age_min > freshness_sla_min (strict), and replay reads at cycle + 4 min; so for cadence 5 /
# SLA 10 the age at cycle T+4 with the last write at T-5k is 4 + 5k: k=1 -> 8.9 OK,
# k=2 -> 13.9 MISSING.

# ---------------------------------------------------------------------------------------
# 5. TRUNCATED TAIL — shape: TD-S72-NEW-8, row "Symptom" (cross-ref TD-S69-NEW-2):
#    "no continuity assertion: a session that started on time and stopped 80 minutes early
#    passed the health check", because min_rows was a FLOOR (60) against an observed norm of
#    379/390 and a first->last range check cannot see a truncated tail.
#    STATED, NOT RECONCILED: the roadmap calls this "the 08-20 shape", but the instances
#    TD-S72-NEW-8 measures are 2026-07-31 (302 rows, ending 08:42 UTC) and 2026-08-17 (297,
#    ending 08:39). It records no 08-20 instance, and 2026-08-20 is not a frozen golden day.
#    This reproduces the SHAPE on 2026-10-01; it is not a replay of 08-20.
# ---------------------------------------------------------------------------------------
sb5 = client("2026-10-01")
n_chain_full = len(sb5.tables["option_chain_snapshots"])
keep(sb5, "option_chain_snapshots", lambda r: minute(r) < f"{DATE}T09:05")  # drop >= 14:35 IST
n_chain_cut = len(sb5.tables["option_chain_snapshots"])
cyc_cut = len({r["ts"] for r in sb5.tables["option_chain_snapshots"]})
newest5 = max(r["ts"] for r in sb5.tables["option_chain_snapshots"])
check("5 seed: newest surviving chain cycle is 14:30 IST (09:00Z)",
      newest5.startswith(f"{DATE}T09:00"), newest5[:19])

for cycle, want in (("14:30", "OK"), ("14:35", "OK"), ("14:40", "MISSING"),
                    ("14:45", "MISSING"), ("15:25", "MISSING")):
    final, own, detail = score(sb5, as_of(cycle))
    check(f"5 truncated tail: chain own {want} at {cycle}", own[CHAIN][0] == want,
          f"{own[CHAIN][0]} age={detail[CHAIN].get('age_min')}")

final, own, detail = score(sb5, as_of("14:40"))
check("5 lineage at 14:40: gamma final STALE", final[GAMMA] == "STALE", final[GAMMA])
check("5 lineage at 14:40: strike GEX final STALE", final[GEX] == "STALE", final[GEX])
check("5 lineage at 14:40: dependants' OWN status uncontaminated",
      (own[GAMMA][0], own[GEX][0]) == ("OK", "OK"), (own[GAMMA][0], own[GEX][0]))
final, own, detail = score(sb5, as_of("15:25"))
check("5 lineage at 15:25: dependants final STALE while own OK (own age 8.88 < SLA 10)",
      (final[GAMMA], final[GEX], own[GAMMA][0], own[GEX][0]) == ("STALE", "STALE", "OK", "OK"),
      f"final {final[GAMMA]}/{final[GEX]} own {own[GAMMA][0]}/{own[GEX][0]} gamma_age={detail[GAMMA].get('age_min')}")
check("5 spot untouched by a chain defect (no lineage edge into spot)", own[SPOT][0] == "OK", own[SPOT][0])

# CONTROL (a) — the in-process form of neutering the freshness branch.
_, own_sla, _ = score(sb5, as_of("15:25"), contracts=with_fields(CONTRACTS, CHAIN, freshness_sla_min=600))
check("5 CONTROL positive isolation: SLA 600 returns the chain to OK at 15:25 — so the MISSING "
      "came from freshness, not presence or calendar", own_sla[CHAIN][0] == "OK", own_sla[CHAIN][0])

# CONTROL (d) — the old FLOOR-style check still PASSES on the same seeded day, at the same
# moment the contract reads MISSING. That simultaneity is the floor's blindness. If this ever
# fails the case has stopped demonstrating it and must be re-derived, never re-tuned.
span5 = (runner.parse_ts(newest5) - runner.parse_ts(min(r["ts"] for r in sb5.tables["option_chain_snapshots"]))).total_seconds() / 60.0
check("5 CONTROL the floor is blind: rows >= 60 AND first->last span >= 300 min, at the same "
      "moment the contract reads MISSING", n_chain_cut >= 60 and span5 >= 300,
      f"{n_chain_cut} rows / {cyc_cut} cycles of {n_chain_full}, span {span5:.0f}min")

free(sb5); del sb5

# ---------------------------------------------------------------------------------------
# 6. DEPTH-1 CHAIN, on 2026-08-27 — Option A: the band lives in this test, not in
#    fixture_scope. Band derived from scale, not picked round: live SENSEX chain [650,900]
#    covers 2 expiries; the fixtures hold 1; measured front-only rows/cycle 392 (08-27) and
#    394 (10-01); 394*2 = 788 sits inside [650,900], so the halved band [325,450] is
#    consistent with the live band rather than a fresh guess. Depth-1 yields 2 — outside by
#    two orders of magnitude, so the gate scores the quantity and not the margin.
# ---------------------------------------------------------------------------------------
BAND = [325, 450]
CB = chain_rows_band(CONTRACTS, BAND)
sb6 = nearest_per_cycle(client("2026-08-27"), "option_chain_snapshots", 2)
check("6 seed: depth-1 chain is 2 rows/cycle (CE+PE of the one nearest strike)",
      rows_per_cycle(sb6, "option_chain_snapshots") == [2], rows_per_cycle(sb6, "option_chain_snapshots"))

for cycle in ("09:15", "12:00", "15:25"):
    final, own, detail = score(sb6, as_of(cycle, "2026-08-27"), contracts=CB)
    check(f"6 depth-1 chain own DEGRADED at {cycle}", own[CHAIN][0] == "DEGRADED",
          f"{own[CHAIN][0]} rows={detail[CHAIN].get('rows_at_newest')}")

final, own, detail = score(sb6, as_of("12:00", "2026-08-27"), contracts=CB)
check("6 reason names the row band and nothing else",
      f"rows 2 outside {BAND}" in (own[CHAIN][1] or "") and "unchanged across" not in (own[CHAIN][1] or ""),
      own[CHAIN][1])
check("6 expiries still in range, so DEGRADED has exactly one cause",
      detail[CHAIN].get("expiries_at_newest") == 1, detail[CHAIN].get("expiries_at_newest"))
check("6 movement abstains: own is DEGRADED, never STALE", own[CHAIN][0] == "DEGRADED", own[CHAIN][0])
check("6 lineage: dependants final DEGRADED while their own status is OK",
      (final[GAMMA], final[GEX], own[GAMMA][0], own[GEX][0]) == ("DEGRADED", "DEGRADED", "OK", "OK"),
      f"final {final[GAMMA]}/{final[GEX]} own {own[GAMMA][0]}/{own[GEX][0]}")

# CONTROL (a) — D1 asserted: today's replay contract (rows=None) cannot see this at all.
_, own_mask, det_mask = score(sb6, as_of("12:00", "2026-08-27"))
check("6 CONTROL D1 masking: the same seed reads OK under fixture_scope's rows=None "
      "(replay_contracts.py:75) — the harness could not detect depth loss before this case",
      own_mask[CHAIN][0] == "OK", f"{own_mask[CHAIN][0]} rows={det_mask[CHAIN].get('rows_at_newest')}")

# CONTROL (b) — not a tautology: the clean day passes the same band.
sb6c = client("2026-08-27")
_, own_c6, det_c6 = score(sb6c, as_of("12:00", "2026-08-27"), contracts=CB)
check(f"6 CONTROL not a tautology: CLEAN 08-27 reads OK under the same {BAND} band",
      own_c6[CHAIN][0] == "OK", f"{own_c6[CHAIN][0]} rows={det_c6[CHAIN].get('rows_at_newest')}")
free(sb6, sb6c); del sb6, sb6c

# ---------------------------------------------------------------------------------------
# 6a. THE POSITIVE TWIN — the same depth reduction on gex_strike IS caught today, because its
#     band [100,200] is NOT nulled by fixture_scope. This is what makes 6's OK-under-rows=None
#     attributable to the override alone rather than to a broken shape check.
# ---------------------------------------------------------------------------------------
sb6a = nearest_per_cycle(client("2026-08-27"), "gex_strike_snapshots", 10)
final, own, detail = score(sb6a, as_of("12:00", "2026-08-27"))
check("6a depth-10 strike GEX own DEGRADED (its band is live, not nulled)",
      own[GEX][0] == "DEGRADED", f"{own[GEX][0]} rows={detail[GEX].get('rows_at_newest')}")
check("6a reason names rows 10 outside [100, 200]", "rows 10 outside [100, 200]" in (own[GEX][1] or ""), own[GEX][1])
check("6a strike GEX NOT STALE: gex_cr still varies, so movement abstains",
      "unchanged across" not in (own[GEX][1] or ""), own[GEX][1])
check("6a chain and gamma own OK (only gex_strike was seeded)",
      (own[CHAIN][0], own[GAMMA][0]) == ("OK", "OK"), (own[CHAIN][0], own[GAMMA][0]))
free(sb6a); del sb6a

# ---------------------------------------------------------------------------------------
# 7a. ONE DROPPED CYCLE MID-SESSION — asserts TODAY'S behaviour: NOT CAUGHT. Freshness cannot
#     see it (SLA 10 is 2x cadence 5), shape reads only the newest cycle, movement still
#     differs. Stage B adds the continuity check and flips this to DEGRADED.
# ---------------------------------------------------------------------------------------
sb7 = keep(client("2026-10-01"), "option_chain_snapshots", lambda r: minute(r) != f"{DATE}T06:30")  # 12:00 IST
for cycle in ("12:00", "12:05", "12:10"):
    final, own, detail = score(sb7, as_of(cycle))
    check(f"7a NOT CAUGHT today: chain own OK at {cycle}", own[CHAIN][0] == "OK",
          f"{own[CHAIN][0]} age={detail[CHAIN].get('age_min')}")
    check(f"7a movement window still full at {cycle}: movement_points == 4",
          detail[CHAIN].get("movement_points") == 4, detail[CHAIN].get("movement_points"))
final, own, detail = score(sb7, as_of("12:05"))
check("7a dependants unaffected too — there is nothing to inherit",
      (final[GAMMA], final[GEX]) == ("OK", "OK"), (final[GAMMA], final[GEX]))
free(sb7); del sb7

# ---------------------------------------------------------------------------------------
# 7b. THE BOUNDARY — two consecutive dropped cycles IS caught. This pins where the edge is, so
#     a later SLA change has to move a failing assertion rather than quietly widen the blind spot.
# ---------------------------------------------------------------------------------------
sb7b = keep(client("2026-10-01"), "option_chain_snapshots",
            lambda r: minute(r) not in (f"{DATE}T06:30", f"{DATE}T06:35"))
final, own, detail = score(sb7b, as_of("12:05"))
check("7b two consecutive dropped cycles -> chain own MISSING at 12:05",
      own[CHAIN][0] == "MISSING", f"{own[CHAIN][0]} age={detail[CHAIN].get('age_min')}")
check("7b and the dependants go STALE by lineage",
      (final[GAMMA], final[GEX]) == ("STALE", "STALE"), (final[GAMMA], final[GEX]))
free(sb7b); del sb7b

# ---------------------------------------------------------------------------------------
# 8. SPOT FEED DIES AT 15:09 — the session-end clamp must not hide it. S90-L gave spot
#    session_end_ist 15:15 so the ADR-022 CAS guard stopping capture at ~15:15 no longer raised
#    a false MISSING at 15:20/15:25 (README.md:25). What that leaves open, and this case
#    answers, is whether a feed that really died can now hide behind it.
#    Cut: drop every spot row with ts >= 15:09:00 IST (09:39:00Z) -> newest 15:08:03 IST.
# ---------------------------------------------------------------------------------------
sb8 = keep(client("2026-10-01"), "market_spot_snapshots", lambda r: minute(r) < f"{DATE}T09:39")
last_spot = max(r["ts"] for r in sb8.tables["market_spot_snapshots"])
check("8 seed: newest surviving spot row is 15:08:03 IST (09:38:03Z)",
      last_spot.startswith(f"{DATE}T09:38:03"), last_spot[:19])

CLAMP_OFF = with_fields(CONTRACTS, SPOT, session_end_ist=None)

for cycle, want in (("15:00", "OK"), ("15:05", "OK"), ("15:10", "MISSING"),
                    ("15:15", "MISSING"), ("15:20", "MISSING"), ("15:25", "MISSING")):
    _, own, detail = score(sb8, as_of(cycle))
    check(f"8 seeded, clamp ON: spot own {want} at {cycle}", own[SPOT][0] == want,
          f"{own[SPOT][0]} age={detail[SPOT].get('age_min')}")

_, own, detail = score(sb8, as_of("15:10"))
check("8 at 15:10 the clamp has NOT engaged (no judged_at_session_end) and it is already MISSING",
      "judged_at_session_end" not in detail[SPOT] and own[SPOT][0] == "MISSING",
      f"{own[SPOT][0]} {detail[SPOT]}")
for cycle in ("15:15", "15:20", "15:25"):
    _, own, detail = score(sb8, as_of(cycle))
    check(f"8 at {cycle} the MISSING is reached THROUGH the session-end branch",
          detail[SPOT].get("judged_at_session_end") == "15:15" and own[SPOT][0] == "MISSING",
          f"{own[SPOT][0]} {detail[SPOT]}")
check("8 no dependant moves: spot is not a `requires` of any edge in scope",
      not any(e[1] == SPOT for e in EDGES), [e for e in EDGES if e[1] == SPOT])

# THE PAIRED CONTROL — clean vs seeded, clamp ON vs OFF. Either half alone proves nothing:
# clean-OK alone is the pin already held, and seeded-MISSING alone could be any freshness failure.
clean8 = client("2026-10-01")
pair = {}
for tag, cl in (("clean", clean8), ("seeded", sb8)):
    for mode, cts in (("on", None), ("off", CLAMP_OFF)):
        for cycle in ("15:20", "15:25"):
            _, own, detail = score(cl, as_of(cycle), contracts=cts)
            pair[(tag, mode, cycle)] = (own[SPOT][0], detail[SPOT].get("age_min"))


def pair_row(tag, mode):
    return [pair[(tag, mode, c)][0] for c in ("15:20", "15:25")]


def pair_got(tag, mode):
    return {c: pair[(tag, mode, c)] for c in ("15:20", "15:25")}


check("8 CONTROL clean + clamp ON  -> OK at 15:20 and 15:25 (the false MISSING is removed)",
      pair_row("clean", "on") == ["OK", "OK"], pair_got("clean", "on"))
check("8 CONTROL clean + clamp OFF -> MISSING at 15:20 and 15:25 (README.md:25, the pre-clamp "
      "false alarm, reproduced)", pair_row("clean", "off") == ["MISSING", "MISSING"], pair_got("clean", "off"))
check("8 CONTROL seeded + clamp ON  -> MISSING at 15:20 and 15:25 (the clamp does NOT hide a "
      "real gap)", pair_row("seeded", "on") == ["MISSING", "MISSING"], pair_got("seeded", "on"))
check("8 CONTROL seeded + clamp OFF -> MISSING at 15:20 and 15:25 (the seeded verdict is "
      "independent of the clamp)", pair_row("seeded", "off") == ["MISSING", "MISSING"], pair_got("seeded", "off"))

# 8b. the 15:30 cycle. The merged plan states it is CLOSED, never MISSING: replay reads a cycle
#     at cycle + 4 min, so 15:30 is read at 15:34, past SESSION_CLOSE 15:30, and the calendar
#     branch (:274) returns before any read happens. Asserted rather than assumed, because it
#     is a real property — the LAST cycle of the day cannot report a feed death.
for label, cl in (("seeded-dead", sb8), ("clean", clean8)):
    _, own, detail = score(cl, as_of("15:30"))
    check(f"8b the 15:30 cycle is CLOSED, not MISSING ({label}) — read at 15:34 > SESSION_CLOSE",
          own[SPOT][0] == "CLOSED" and detail[SPOT] == {"calendar": "closed"},
          f"{own[SPOT][0]} {detail[SPOT]}")

# Case 9 contrasts its presence-MISSING against case 8's freshness-MISSING. Capture the
# two scalars it needs NOW, so case 8's client does not have to outlive case 8.
_, _o8, _d8 = score(sb8, as_of("15:20"))
FRESHNESS_MISSING_REASON = _o8[SPOT][1]
FRESHNESS_HAS_AGE = "age_min" in _d8[SPOT]
free(sb8, clean8); del sb8, clean8, _o8, _d8

# ====================================== 9-11: check paths that had never fired on a fixture
# ---------------------------------------------------------------------------------------
# 9. PRESENCE -> MISSING, told apart from FRESHNESS -> MISSING. Two branches
#    (check_contracts_shadow.py:93 vs :120) that both report MISSING and have never been
#    distinguished on a fixture.
# ---------------------------------------------------------------------------------------
sb9 = keep(client("2026-10-01"), "market_spot_snapshots", lambda r: False)
_, own9, det9 = score(sb9, AS_OF)
check("9 no row for the scope at all -> own MISSING", own9[SPOT][0] == "MISSING", own9[SPOT][0])
check("9 checks is exactly {'presence': False}", det9[SPOT] == {"presence": False}, det9[SPOT])
check("9 reason is the presence reason", own9[SPOT][1] == "no row for scope", own9[SPOT][1])
check("9 and no age_min was recorded, so this MISSING is not a staleness story",
      "age_min" not in det9[SPOT], det9[SPOT])
check("9 the two MISSINGs are distinguishable: presence reason != freshness reason",
      own9[SPOT][1] != FRESHNESS_MISSING_REASON and FRESHNESS_HAS_AGE,
      (own9[SPOT][1], FRESHNESS_MISSING_REASON))
free(sb9); del sb9

# ---------------------------------------------------------------------------------------
# 10. UNKNOWN, a latest-only product judged in the past (check_contracts_shadow.py:269). No
#     frozen relation can reach that branch — all four carry ts or run_id in grain — so the
#     CONTRACT is synthetic; the fixture is not.
# ---------------------------------------------------------------------------------------
P10 = "synthetic_latest_only:SENSEX"
latest_only = {**next(c for c in CONTRACTS if c["product"] == GAMMA), "product": P10, "grain": ["symbol"]}
sb10 = client("2026-10-01")
_, own10, det10 = score(sb10, AS_OF, contracts=[latest_only], edges=[])
check("10 latest-only product, historical as_of -> UNKNOWN", own10[P10][0] == "UNKNOWN", own10[P10][0])
check("10 reason says why", own10[P10][1] == "latest-only product; cannot be judged as of a past time",
      own10[P10][1])
check("10 checks {'history': False}", det10[P10] == {"history": False}, det10[P10])
check("10 and it is NOT reported OK", own10[P10][0] != "OK", own10[P10][0])
free(sb10); del sb10

# ---------------------------------------------------------------------------------------
# 11. UNKNOWN, a check that cannot run (check_contracts_shadow.py:284-285). A client subclass,
#     not a fixture change. The comment there says "a check that cannot run is UNKNOWN, never
#     OK" and it has had no test.
# ---------------------------------------------------------------------------------------
class Exploding(FixtureClient):
    """Loads the fixture normally, then refuses every read."""
    def select(self, *a, **k):
        raise RuntimeError("seeded read failure")


sb11 = Exploding([DAY])
_, own11, _ = score(sb11, AS_OF)
P11 = (CHAIN, GEX, GAMMA, SPOT)
check("11 a raising client -> every product UNKNOWN, never OK",
      all(own11[p][0] == "UNKNOWN" for p in P11), {p: own11[p][0] for p in P11})
check("11 reason begins 'check failed:'",
      all((own11[p][1] or "").startswith("check failed:") for p in P11), own11[CHAIN][1])
check("11 and nothing is OK or CLOSED",
      not any(own11[p][0] in ("OK", "CLOSED") for p in P11), {p: own11[p][0] for p in P11})
free(sb11); del sb11

print("SEEDED " + ("ALL PASS" if fails == 0 else f"{fails} FAIL")
      + (f" ({xfails} XFAIL)" if xfails else ""))
sys.exit(1 if fails else 0)
