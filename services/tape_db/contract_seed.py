#!/usr/bin/env python3
"""Tape T1-db: compute the ADR-031 D1 contract rows for the tape sidecar from ONE processed day, and write the SQL
(docs/tape/T1_db_plan.md section 1.3). Expected values are computed here from the files, never recalled.

  python services/tape_db/contract_seed.py --day 2026-11-02 --out <out_> --cyc <cyc_> --chain <chain_>\\events
      --session <day>\\session --sql sql/2026-11-03_tape_t1db_contracts.sql

Read-only on its inputs (the same manifest verification as load_day.py). No .env, no network, no database.

What check_contracts_shadow.py can evaluate for a daily product (cadence_min >= 1440), and therefore what each row
carries -- everything else is NOT_COMPUTED and said so in change_reason:
  presence + "loaded within one trading day" (time_col trading_day, freshness_sla_min 1440 -> allowed 1 day behind),
  rows on the newest trading_day inside expected_per_cycle.rows.
  NOT the 20:00 IST deadline, NOT rows per minute == subscribed instruments, NOT movement (skipped for daily).
"""
import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from merdian_compute.tape import cycle, replay  # noqa: E402
from services.tape_db import load_day, tape_schema as S  # noqa: E402

SYMBOLS = ("NIFTY", "SENSEX")
CALENDAR = {"NIFTY": "NSE_FO", "SENSEX": "BSE_FO"}
BINS = (cycle.LAST_T - cycle.FIRST_T) // cycle.STEP + 1   # 5-minute bins 09:20..15:30 = 75
GRAIN = {
    "tape_minute": ["symbol", "trading_day", "instrument_token", "minute_ist"],
    "tape_strike_cycle": ["symbol", "trading_day", "instrument_token", "ts_ist"],
    "tape_events": ["symbol", "trading_day", "expiry", "strike", "leg", "kind", "ts_ist", "side"],
    "tape_chain_events": ["symbol", "trading_day", "expiry", "kind", "ts_ist", "strike"],
    "tape_chain_runs": ["symbol", "trading_day", "expiry", "ts_ist"],
    "tape_daily_report": ["symbol", "trading_day"],
}
LINEAGE = (("tape_strike_cycle", "tape_minute"), ("tape_events", "tape_strike_cycle"),
           ("tape_chain_events", "tape_chain_runs"))
NOT_COMPUTED = ("NOT_COMPUTED by check_contracts_shadow.py for a daily product: the 20:00 IST load deadline "
                "(freshness is whole trading days only); movement (skipped when cadence_min >= 1440)")


def hm_min(s):
    return int(s[0:2]) * 60 + int(s[3:5])


def subscribed(session, day):
    """{sym: {token: earliest added_minute (minutes since midnight)}} over the union of every subscriptions file."""
    d = None
    for c in (os.path.join(session, day), session):
        if os.path.isdir(c) and any(replay.SUB_RE.match(n) for n in os.listdir(c)):
            d = c
            break
    if d is None:
        raise load_day.Refused(3, "INPUT FAIL: no subscriptions_*.json under %s" % session)
    out, files = {}, []
    for n in sorted(os.listdir(d)):
        if not replay.SUB_RE.match(n):
            continue
        p = os.path.join(d, n)
        files.append({"path": "session/%s" % n, "sha256": load_day.sha256_file(p)})
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
        for r in doc.get("tokens") or []:
            tok, sym, am = int(r["token"]), r.get("sym"), r.get("added_minute")
            m = hm_min(am) if am else 0
            cur = out.setdefault(sym, {}).get(tok)
            out[sym][tok] = m if cur is None else min(cur, m)
    return out, files


def compute(day, out, cyc, chain, session):
    mans = load_day.verify_manifests(day, out, cyc, chain, session)
    rows = load_day.build_all(day, out, cyc, chain, session, mans)
    subs, sub_files = subscribed(session, day)
    derived = {}
    for sym in SYMBOLS:
        toks = subs.get(sym, {})
        mrows = [r for r in rows["tape_minute"] if r["symbol"] == sym]
        d = {"subscribed_tokens": len(toks)}
        if mrows:
            mins = [hm_min(r["minute_ist"][11:16]) for r in mrows]
            lo, hi = min(mins), max(mins)
            ceil_m = sum(sum(1 for a in toks.values() if a <= m) for m in range(lo, hi + 1))
            d.update(minute_rows=len(mrows), minute_span=[lo, hi], minute_ceiling=ceil_m,
                     minute_rows_per_minute=round(len(mrows) / (hi - lo + 1), 3))
        d["cycle_rows"] = sum(1 for r in rows["tape_strike_cycle"] if r["symbol"] == sym)
        d["cycle_ceiling"] = BINS * len(toks)
        crow = [r for r in rows["tape_chain_runs"] if r["symbol"] == sym]
        d["chain_runs_rows"] = len(crow)
        d["daily_rows"] = sum(1 for r in rows["tape_daily_report"] if r["symbol"] == sym)
        d["events_rows"] = sum(1 for r in rows["tape_events"] if r["symbol"] == sym)
        d["chain_events_rows"] = sum(1 for r in rows["tape_chain_events"] if r["symbol"] == sym)
        derived[sym] = d
    # the chain-run ceiling is read from the chain export itself: one run per distinct (ts, expiry) group in the input
    parent = os.path.dirname(os.path.abspath(chain))
    for sym in SYMBOLS:
        p = os.path.join(parent, "gex_strike_snapshots_%s.csv" % sym)
        if os.path.isfile(p):
            import csv
            with open(p, encoding="utf-8", newline="") as fh:
                groups = {(r["ts"], r["expiry_date"]) for r in csv.DictReader(fh)}
            derived[sym]["chain_runs_ceiling"] = len(groups)
    problems = []
    for sym, d in derived.items():
        for got, cap in (("minute_rows", "minute_ceiling"), ("cycle_rows", "cycle_ceiling"),
                         ("chain_runs_rows", "chain_runs_ceiling")):
            if got in d and cap in d and d[got] > d[cap]:
                problems.append("%s %s=%d > %s=%d: the derivation is wrong, not the data" % (sym, got, d[got], cap, d[cap]))
    if problems:
        raise load_day.Refused(3, "SEED FAIL: " + "; ".join(problems))
    inputs = {k: v[1] for k, v in mans.items()}
    return derived, inputs, sub_files


def contracts(day, derived):
    out = []
    for sym in SYMBOLS:
        d = derived.get(sym)
        if not d:
            continue
        base = {"scope_symbol": sym, "scope_col": "symbol", "time_col": "trading_day", "cadence_min": 1440,
                "freshness_sla_min": 1440, "movement_cols": [], "movement_window_cycles": 3,
                "calendar": CALENDAR[sym], "tier": 3, "writer": S.WRITER, "access_rls": "ENABLED_WITH_RO_POLICY"}

        def row(rel, exp, reason):
            return dict(base, product="%s:%s" % (rel, sym), relation_name=rel, grain=GRAIN[rel],
                        expected_per_cycle=exp, change_reason="tape T1-db seed from day %s. %s %s." % (day, reason, NOT_COMPUTED))
        if "minute_ceiling" in d:
            out.append(row("tape_minute", {"rows": [1, d["minute_ceiling"]]},
                           "rows ceiling %d = sum over minutes %s of subscribed %s tokens (union of the day's "
                           "subscriptions files, added_minute <= m): a minute row exists only for a subscribed token. "
                           "Day %s measured %d rows. Lower bound 1 adds nothing beyond presence; rows per minute == "
                           "subscribed instruments is NOT_COMPUTED (the runner counts the whole day)"
                           % (d["minute_ceiling"], d["minute_span"], sym, day, d["minute_rows"])))
        out.append(row("tape_strike_cycle", {"rows": [1, d["cycle_ceiling"]]},
                       "rows ceiling %d = %d five-minute bins (09:20..15:30) x %d subscribed tokens; rows start at "
                       "first_seen_T so this is a ceiling. Day %s measured %d"
                       % (d["cycle_ceiling"], BINS, d["subscribed_tokens"], day, d["cycle_rows"])))
        out.append(row("tape_daily_report", {"rows": [1, 1]}, "exactly one row per symbol per trading day"))
        out.append(row("tape_events", {}, "no expected count: a zero-event day is valid, so freshness can read "
                       "MISSING after two consecutive zero-event trading days (registered because product_lineage "
                       "requires it). Day %s measured %d" % (day, d["events_rows"])))
        out.append(row("tape_chain_events", {}, "no expected count: a zero-event day is valid, so freshness can read "
                       "MISSING after two consecutive zero-event trading days (registered because product_lineage "
                       "requires it). Day %s measured %d" % (day, d["chain_events_rows"])))
        if "chain_runs_ceiling" in d:
            out.append(row("tape_chain_runs", {"rows": [1, d["chain_runs_ceiling"]]},
                           "rows ceiling %d = distinct (ts, expiry_date) groups in day %s gex_strike_snapshots_%s.csv "
                           "(one run per group, at most). Day %s measured %d"
                           % (d["chain_runs_ceiling"], day, sym, day, d["chain_runs_rows"])))
        else:
            out.append(row("tape_chain_runs", {}, "no chain export for %s on day %s: no expected count" % (sym, day)))
    return out


def lineage(cons):
    have = {c["product"] for c in cons}
    edges = []
    for sym in SYMBOLS:
        for p, r in LINEAGE:
            a, b = "%s:%s" % (p, sym), "%s:%s" % (r, sym)
            if a in have and b in have:
                edges.append((a, b))
    return edges


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def arr(xs):
    return q("{" + ",".join(xs) + "}")


def render_sql(day, cons, edges, derived, inputs, sub_files):
    L = ["-- =====================================================================",
         "-- Tape T1-db: ADR-031 D1 contracts for the tape sidecar (docs/tape/T1_db_plan.md section 1.3).",
         "-- AUTHORED, NOT APPLIED. Written by services/tape_db/contract_seed.py from day %s;" % day,
         "-- every number below is computed from these files (sha256), never recalled:"]
    for k in ("out", "cyc", "chain"):
        L.append("--   %-5s run_manifest.json  %s" % (k, inputs[k]))
    for f in sub_files:
        L.append("--   %-38s %s" % (f["path"], f["sha256"]))
    L.append("-- Derivation per symbol (measured on the day, ceilings derived from the inputs):")
    for sym in sorted(derived):
        L.append("--   %s %s" % (sym, json.dumps(derived[sym], sort_keys=True)))
    L += ["-- Apply AFTER sql/2026-11-03_tape_t1db_sidecar.sql. SQL editor, postgres, ONE execution.",
          "-- Idempotent: ON CONFLICT DO NOTHING (an existing contract is never overwritten here).",
          "-- =====================================================================", "", "BEGIN;", "",
          "INSERT INTO public.data_contracts",
          "  (product, relation_name, scope_symbol, scope_col, time_col, grain, cadence_min, freshness_sla_min,"
          " expected_per_cycle, movement_cols, movement_window_cycles, calendar, tier, writer, access_rls, change_reason)",
          "VALUES"]
    vals = []
    for c in cons:
        vals.append("  (%s, %s, %s, %s, %s, %s, %d, %d, %s::jsonb, %s, %d, %s, %d, %s, %s, %s)" % (
            q(c["product"]), q(c["relation_name"]), q(c["scope_symbol"]), q(c["scope_col"]), q(c["time_col"]),
            arr(c["grain"]), c["cadence_min"], c["freshness_sla_min"], q(json.dumps(c["expected_per_cycle"], sort_keys=True)),
            arr(c["movement_cols"]), c["movement_window_cycles"], q(c["calendar"]), c["tier"], q(c["writer"]),
            q(c["access_rls"]), q(c["change_reason"])))
    L.append(",\n".join(vals))
    L.append("ON CONFLICT (product) DO NOTHING;")
    L += ["", "INSERT INTO public.product_lineage (product, requires) VALUES"]
    L.append(",\n".join("  (%s, %s)" % (q(a), q(b)) for a, b in edges))
    L += ["ON CONFLICT (product, requires) DO NOTHING;", "", "COMMIT;", "",
          "-- Evidence (last result set): expect %d contracts and %d edges." % (len(cons), len(edges)),
          "SELECT (SELECT count(*) FROM public.data_contracts WHERE writer = %s AND valid_to IS NULL) AS tape_contracts,"
          % q(S.WRITER),
          "       (SELECT count(*) FROM public.product_lineage WHERE product LIKE 'tape\\_%') AS tape_edges;", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="contract_seed")
    for k in ("--day", "--out", "--cyc", "--chain", "--session", "--sql"):
        ap.add_argument(k, required=True)
    a = ap.parse_args(argv)
    try:
        derived, inputs, sub_files = compute(a.day, *(os.path.abspath(p) for p in (a.out, a.cyc, a.chain, a.session)))
    except load_day.Refused as exc:
        print(str(exc))
        return exc.code
    cons = contracts(a.day, derived)
    edges = lineage(cons)
    text = render_sql(a.day, cons, edges, derived, inputs, sub_files)
    with open(a.sql, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    for sym in sorted(derived):
        print("%s %s" % (sym, json.dumps(derived[sym], sort_keys=True)))
    print("CONTRACT SEED WRITTEN %s (%d contracts, %d edges)" % (a.sql, len(cons), len(edges)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
