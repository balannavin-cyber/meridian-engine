#!/usr/bin/env python3
"""backfill_gamma_v2_from_gss.py -- ADR-033 D6: fill the V2 tables from STORED per-strike rows.

AUTHORED, NOT APPROVED TO RUN. Box only, as the engine user, from the repo root, after the
V2 tables exist and after the second check. Never 08:30-15:40 IST Mon-Fri (it refuses).

  ( ulimit -v 700000; python3 -B backfill_gamma_v2_from_gss.py --from 2026-11-20 --to 2026-11-20 )
        dry run (the default): reads, computes, prints counts, WRITES NOTHING.
  ( ulimit -v 700000; python3 -B backfill_gamma_v2_from_gss.py --from 2026-11-20 --to 2026-11-20 --apply )
        writes gex_strike_v2 and gex_run_v2 only.

What it does, per IST day and symbol:
  - lists the day's runs from gamma_metrics (one row per run);
  - skips a run that already has a gex_run_v2 row (live or backfilled): it never overwrites;
  - reads that run's gex_strike_snapshots rows and builds V2 with
    merdian_compute.gamma_v2.build_v2_strike_rows_from_gss (rule v1.2, stored-row form);
  - inserts with ON CONFLICT DO NOTHING, stamped rule_version 'v2-1.2-gss', n_dup_legs NULL
    (duplicate chain leg rows are not visible in stored rows).
A run the rule calls an input error (repeated strike, bad spot, two expiries) gets no V2 rows
and is counted. Reads: gamma_metrics, gex_strike_snapshots, gex_run_v2. Writes: the two V2 tables.

ROLLBACK (operator, SQL editor), for a day range:
  DELETE FROM public.gex_strike_v2 WHERE rule_version = 'v2-1.2-gss' AND ts >= '<from> 00:00+05:30' AND ts < '<to+1> 00:00+05:30';
  DELETE FROM public.gex_run_v2    WHERE rule_version = 'v2-1.2-gss' AND ts >= '<from> 00:00+05:30' AND ts < '<to+1> 00:00+05:30';
VERIFY after a run (read-only): per day, backfilled runs = runs in gamma_metrics minus live runs minus input-error runs:
  SELECT (ts AT TIME ZONE 'Asia/Kolkata')::date AS d, symbol, rule_version, count(*) AS runs FROM public.gex_run_v2 GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timedelta, time as dtime
from typing import Any
from zoneinfo import ZoneInfo

from merdian_compute import gamma_v2

IST = ZoneInfo("Asia/Kolkata")
PAGE = 1000
CHUNK = 500


def market_hours_now(now: datetime | None = None) -> bool:
    n = (now or datetime.now(IST)).astimezone(IST)
    return n.weekday() < 5 and dtime(8, 30) <= n.time() <= dtime(15, 40)


def _page(query_factory) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    start = 0
    while True:
        rows = query_factory().range(start, start + PAGE - 1).execute().data or []
        out.extend(rows)
        if len(rows) < PAGE:
            return out
        start += PAGE


def day_bounds(d: date) -> tuple[str, str]:
    lo = datetime.combine(d, dtime(0, 0), IST)
    return lo.isoformat(), (lo + timedelta(days=1)).isoformat()


def backfill_day(client: Any, d: date, symbols: list[str], apply: bool, pause: float) -> dict[str, int]:
    lo, hi = day_bounds(d)
    c = {"runs": 0, "already": 0, "no_rows": 0, "input_error": 0, "built": 0, "strike_rows": 0, "written_runs": 0}
    for sym in symbols:
        runs = _page(lambda: client.table("gamma_metrics").select("run_id,symbol,ts,expiry_date")
                     .eq("symbol", sym).gte("ts", lo).lt("ts", hi).order("ts").order("run_id"))
        done = {r["run_id"] for r in _page(lambda: client.table("gex_run_v2").select("run_id")
                                           .eq("symbol", sym).gte("ts", lo).lt("ts", hi).order("run_id"))}
        seen: set[str] = set()
        for run in runs:
            rid = run["run_id"]
            if not rid or rid in seen:
                continue
            seen.add(rid)
            c["runs"] += 1
            if rid in done:
                c["already"] += 1
                continue
            gss = _page(lambda: client.table("gex_strike_snapshots")
                        .select("run_id,symbol,ts,expiry_date,dte,strike,spot,oi_call,oi_put,gamma_call,gamma_put")
                        .eq("run_id", rid).eq("symbol", sym).order("strike").order("id"))
            if not gss:
                c["no_rows"] += 1
                continue
            try:
                srows = gamma_v2.build_v2_strike_rows_from_gss(gss)
            except gamma_v2.V2InputError as e:
                c["input_error"] += 1
                print(f"  input error, no V2 output: {d} {sym} run_id={rid}: {e}")
                continue
            spot_by_strike = {float(g["strike"]): g["spot"] for g in gss}
            head = gss[0]
            ident = {"run_id": rid, "symbol": sym, "ts": head["ts"], "expiry_date": head["expiry_date"], "dte": head.get("dte")}
            strike_payload = [{**ident, "spot": spot_by_strike[r["strike"]], **r, "rule_version": gamma_v2.RULE_VERSION_GSS} for r in srows]
            run_payload = {**ident, "spot": head["spot"], **gamma_v2.summarise_v2_run(srows),
                           "n_dup_legs": None, "rule_version": gamma_v2.RULE_VERSION_GSS}
            c["built"] += 1
            c["strike_rows"] += len(strike_payload)
            if apply:
                for i in range(0, len(strike_payload), CHUNK):
                    client.table("gex_strike_v2").upsert(strike_payload[i:i + CHUNK], on_conflict="run_id,strike,expiry_date",
                                                          ignore_duplicates=True).execute()
                client.table("gex_run_v2").upsert(run_payload, on_conflict="run_id,symbol,expiry_date",
                                                   ignore_duplicates=True).execute()
                c["written_runs"] += 1
                time.sleep(pause)
    return c


def main(argv: list[str] | None = None, client: Any = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill V2 exposure from stored gex_strike_snapshots rows (dry run unless --apply).")
    ap.add_argument("--from", dest="d_from", required=True)
    ap.add_argument("--to", dest="d_to", required=True)
    ap.add_argument("--symbol", action="append", choices=["NIFTY", "SENSEX"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--pause", type=float, default=0.2, help="seconds between runs when writing")
    ap.add_argument("--max-days", type=int, default=10, help="refuse a longer range in one invocation")
    a = ap.parse_args(argv)
    d0, d1 = date.fromisoformat(a.d_from), date.fromisoformat(a.d_to)
    if d1 < d0:
        print("REFUSED: --to is before --from"); return 2
    if (d1 - d0).days + 1 > a.max_days:
        print(f"REFUSED: range is longer than --max-days {a.max_days}"); return 2
    if d1 >= datetime.now(IST).date():
        print("REFUSED: the range must end before today (IST); today's runs are the live writer's"); return 2
    if market_hours_now():
        print("REFUSED: 08:30-15:40 IST on a weekday"); return 2
    if client is None:
        import os
        from dotenv import load_dotenv
        from supabase import create_client
        load_dotenv()
        client = create_client(os.environ["SUPABASE_URL"].strip().strip('"').strip("'"),
                               os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip().strip('"').strip("'"))
    symbols = a.symbol or ["NIFTY", "SENSEX"]
    print(f"mode={'APPLY' if a.apply else 'DRY RUN (nothing is written)'} rule_version={gamma_v2.RULE_VERSION_GSS} symbols={symbols}")
    total: dict[str, int] = {}
    d = d0
    while d <= d1:
        c = backfill_day(client, d, symbols, a.apply, a.pause)
        print(f"{d} " + " ".join(f"{k}={v}" for k, v in c.items()))
        for k, v in c.items():
            total[k] = total.get(k, 0) + v
        d += timedelta(days=1)
    print("TOTAL " + " ".join(f"{k}={v}" for k, v in total.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
