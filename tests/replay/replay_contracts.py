#!/usr/bin/env python3
"""S90 / AM-1 replay harness, v0 — score golden days with the production contract runner, offline.

Runs check_contracts_shadow.evaluate() — the same function the */5 cron runs — against each frozen
golden day (tests/golden/<date>_<SYMBOL>) through tests/replay/fixture_client.FixtureClient, at every
5-minute cycle 09:15–15:30 IST, and writes one status per product per cycle.

  python3 tests/replay/replay_contracts.py            # score all golden days, print a summary
  python3 tests/replay/replay_contracts.py --check    # compare with tests/replay/expected/*.csv; exit 1 on any difference
  python3 tests/replay/replay_contracts.py --pin      # (re)write the expected files — only after reading the summary

No database, no network, no credentials: runs at any hour, on the box or anywhere with the repo.
Scope (stated, not implied):
  * Products are limited to the relations frozen in the fixtures (chain, strike GEX, gamma, spot) for
    the fixture's own symbol. Everything else (WCB, daily EOD tables, cycle history, the other symbol)
    is out of scope here and is not scored.
  * The fixtures hold the FRONT expiry only (R2.1 freeze). fixture_scope() therefore scores the chain
    against 1 expiry with no row band; every other check runs exactly as in production.
  * Contracts come from tests/replay/contracts.json (the S90 seed as applied, incl. the SENSEX strike
    GEX widening). When the live contracts change, refresh it and re-pin deliberately.
  * Calendar: the V18E rule engine (trading_calendar.json), offline — the same authority the gate
    falls back to.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "replay"))

import check_contracts_shadow as runner  # noqa: E402
from fixture_client import FixtureClient, RELATIONS  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
HERE = Path(__file__).resolve().parent
EXPECTED = HERE / "expected"
# as-of inside each cycle: the live cron fires at :00/:05 and reads the cycle written ~10 s earlier;
# replay reads at cycle + 4 min so every write of that cycle is in and the next has not started.
AS_OF_OFFSET = timedelta(minutes=4)


def offline_calendar():
    from trading_calendar import get_session_config_for_date

    def is_trading_day(d: str) -> bool:
        return bool(get_session_config_for_date(d).is_open)

    def previous_trading_day(d: str, max_lookback: int = 10):
        from datetime import date
        x = date.fromisoformat(d)
        for _ in range(max_lookback):
            x -= timedelta(days=1)
            if is_trading_day(x.isoformat()):
                return x.isoformat(), "rule-engine"
        return (date.fromisoformat(d) - timedelta(days=1)).isoformat(), "fail-open:exhausted"

    return is_trading_day, previous_trading_day


def fixture_scope(c):
    """The R2.1 fixtures hold the FRONT expiry only, so the live chain contract (2 expiries,
    ~2x the rows) would read DEGRADED on every cycle and mask everything downstream. Replay
    scores the chain against what the fixture holds: 1 expiry, no row-count band. Every
    other check (presence, freshness, movement, calendar, lineage) runs as in production."""
    if c["relation_name"] != "option_chain_snapshots":
        return c
    exp = dict(c.get("expected_per_cycle") or {})
    exp["expiries"], exp["rows"] = [1, 1], None
    return {**c, "expected_per_cycle": exp, "_fixture_override": "front expiry only; no row band"}


def score_day(day_dir: Path, contracts_all, edges_all, is_trading_day, previous_trading_day):
    date_s, symbol = day_dir.name.split("_", 1)
    rels = set(RELATIONS.values())
    contracts = [fixture_scope(c) for c in contracts_all
                 if c["relation_name"] in rels and c.get("scope_symbol") == symbol]
    names = {c["product"] for c in contracts}
    edges = [(p, r) for p, r in edges_all if p in names and r in names]
    sb = FixtureClient([day_dir])
    rows = []
    t = datetime.fromisoformat(f"{date_s}T09:15:00").replace(tzinfo=IST)
    end = datetime.fromisoformat(f"{date_s}T15:30:00").replace(tzinfo=IST)
    now = datetime.now(timezone.utc)
    while t <= end:
        as_of = (t + AS_OF_OFFSET).astimezone(timezone.utc)
        final, own, _ = runner.evaluate(sb, contracts, edges, as_of, now, is_trading_day, previous_trading_day)
        for p, (s, r) in sorted(final.items()):
            rows.append({"cycle_ist": t.strftime("%H:%M"), "product": p, "status": s, "own": own[p][0],
                         "reason": (r or "").replace("\n", " ")})
        t += timedelta(minutes=5)
    return rows


def summarise(name, rows):
    from collections import Counter
    by = {}
    for r in rows:
        by.setdefault(r["product"], Counter())[r["status"]] += 1
    print(f"== {name}: {len({r['cycle_ist'] for r in rows})} cycles")
    for p, c in sorted(by.items()):
        print(f"   {p:<36} " + "  ".join(f"{k} {v}" for k, v in sorted(c.items())))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--pin", action="store_true")
    ap.add_argument("--day", default=None, help="one golden day directory name")
    a = ap.parse_args()

    spec = json.loads((HERE / "contracts.json").read_text())
    contracts, edges = spec["contracts"], [tuple(e) for e in spec["lineage"]]
    is_td, prev_td = offline_calendar()
    days = sorted(p for p in (ROOT / "tests" / "golden").iterdir() if p.is_dir() and (a.day in (None, p.name)))
    diffs = 0
    for d in days:
        rows = score_day(d, contracts, edges, is_td, prev_td)
        summarise(d.name, rows)
        f = EXPECTED / f"{d.name}.statuses.csv"
        cols = ["cycle_ist", "product", "status", "own", "reason"]
        if a.pin:
            EXPECTED.mkdir(exist_ok=True)
            with f.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
            print(f"   pinned {f.relative_to(ROOT)}")
        elif a.check:
            if not f.exists():
                print(f"   NO EXPECTED FILE {f.relative_to(ROOT)}"); diffs += 1; continue
            with f.open(newline="") as fh:
                exp = list(csv.DictReader(fh))
            got = [{k: r[k] for k in cols} for r in rows]
            bad = [(e, g) for e, g in zip(exp, got) if e != g]
            if len(exp) != len(got):
                print(f"   ROW COUNT {len(got)} != expected {len(exp)}"); diffs += 1
            for e, g in bad[:10]:
                print(f"   DIFF {g['cycle_ist']} {g['product']}: expected {e['status']}/{e['own']} got {g['status']}/{g['own']}")
            diffs += len(bad)
            print(f"   {'MATCH' if not bad and len(exp) == len(got) else 'MISMATCH'}")
    if a.check:
        print("REPLAY CHECK " + ("PASS" if diffs == 0 else f"FAIL ({diffs})"))
        return 0 if diffs == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
