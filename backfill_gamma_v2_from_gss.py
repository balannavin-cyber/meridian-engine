#!/usr/bin/env python3
"""backfill_gamma_v2_from_gss.py -- ADR-033 D6: fill the V2 tables from STORED per-strike rows.

AUTHORED, NOT APPROVED TO RUN. Box only, as the engine user, from the repo root, after the
V2 tables exist and after the second check. Never 08:30-15:40 IST Mon-Fri (it refuses).

  ( ulimit -v 700000; python3 -B backfill_gamma_v2_from_gss.py --from 2026-11-20 --to 2026-11-20 )
        dry run (the default): reads, computes, prints counts, WRITES NOTHING.
  ( ulimit -v 700000; python3 -B backfill_gamma_v2_from_gss.py --from 2026-11-20 --to 2026-11-20 --apply )
        writes gex_strike_v2 and gex_run_v2 only.

What it does, per IST day and symbol:
  - reads the day's gex_strike_snapshots rows, 1,000 per request, ordered by ts then id
    (about a dozen requests), and groups them by run_id in memory;
  - skips a run that already has a gex_run_v2 row (live or backfilled): it never overwrites;
  - builds V2 per run with merdian_compute.gamma_v2.build_v2_strike_rows_from_gss
    (rule v1.2, stored-row form);
  - writes the day's strike rows 500 per request, pausing --pause seconds between requests,
    then the day's run rows, all with ON CONFLICT DO NOTHING, stamped rule_version
    'v2-1.2-gss', n_dup_legs NULL (duplicate chain leg rows are not visible in stored rows).
Safe to interrupt and run again: a run row is written only after its strike rows, so a
run without a run row is redone and its existing strike rows are left as they are.
A run the rule calls an input error (repeated strike, bad spot, two expiries) gets no V2 rows
is counted and is listed at the end under INPUT ERROR RUNS. Reads: gex_strike_snapshots, gex_run_v2. Writes: the two V2 tables.

ROLLBACK (operator, SQL editor), for a day range:
  DELETE FROM public.gex_strike_v2 WHERE rule_version = 'v2-1.2-gss' AND ts >= '<from> 00:00+05:30' AND ts < '<to+1> 00:00+05:30';
  DELETE FROM public.gex_run_v2    WHERE rule_version = 'v2-1.2-gss' AND ts >= '<from> 00:00+05:30' AND ts < '<to+1> 00:00+05:30';
VERIFY after a run (read-only): per day, backfilled runs = runs with stored rows minus live runs minus input-error runs:
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


def backfill_day(client: Any, d: date, symbols: list[str], apply: bool, pause: float, errors: list[str]) -> dict[str, int]:
    """One IST day. Reads the day's stored rows page by page (about a dozen requests per symbol),
    groups them by run in memory, builds V2 per run, writes the day's strike rows in chunks and
    then the day's run rows. A run row is written only after its strike rows, so a run with a
    gex_run_v2 row is complete; an interrupted day is simply redone (ON CONFLICT DO NOTHING)."""
    lo, hi = day_bounds(d)
    c = {"runs": 0, "already": 0, "input_error": 0, "built": 0, "strike_rows": 0, "written_runs": 0, "read_rows": 0}
    for sym in symbols:
        gss_day = _page(lambda: client.table("gex_strike_snapshots")
                        .select("id,run_id,symbol,ts,expiry_date,dte,strike,spot,oi_call,oi_put,gamma_call,gamma_put")
                        .eq("symbol", sym).gte("ts", lo).lt("ts", hi).order("ts").order("id"))
        c["read_rows"] += len(gss_day)
        done = {r["run_id"] for r in _page(lambda: client.table("gex_run_v2").select("run_id,id")
                                           .eq("symbol", sym).gte("ts", lo).lt("ts", hi).order("id"))}
        by_run: dict[str, list[dict[str, Any]]] = {}
        for g in gss_day:
            if g.get("run_id"):
                by_run.setdefault(g["run_id"], []).append(g)
        strike_payload: list[dict[str, Any]] = []
        run_payload: list[dict[str, Any]] = []
        for rid, gss in by_run.items():
            c["runs"] += 1
            if rid in done:
                c["already"] += 1
                continue
            try:
                srows = gamma_v2.build_v2_strike_rows_from_gss(gss)
            except gamma_v2.V2InputError as e:
                c["input_error"] += 1
                errors.append(f"{d} {sym} run_id={rid}: {e}")
                continue
            spot_by_strike = {float(g["strike"]): g["spot"] for g in gss if g.get("strike") is not None}
            head = gss[0]
            ident = {"run_id": rid, "symbol": sym, "ts": head["ts"], "expiry_date": head["expiry_date"], "dte": head.get("dte")}
            strike_payload.extend({**ident, "spot": spot_by_strike[r["strike"]], **r, "rule_version": gamma_v2.RULE_VERSION_GSS} for r in srows)
            run_payload.append({**ident, "spot": head["spot"], **gamma_v2.summarise_v2_run(srows),
                                "n_dup_legs": None, "rule_version": gamma_v2.RULE_VERSION_GSS})
            c["built"] += 1
            c["strike_rows"] += len(srows)
        if apply and run_payload:
            for i in range(0, len(strike_payload), CHUNK):
                client.table("gex_strike_v2").upsert(strike_payload[i:i + CHUNK], on_conflict="run_id,strike,expiry_date",
                                                      ignore_duplicates=True).execute()
                time.sleep(pause)
            for i in range(0, len(run_payload), CHUNK):
                client.table("gex_run_v2").upsert(run_payload[i:i + CHUNK], on_conflict="run_id,symbol,expiry_date",
                                                   ignore_duplicates=True).execute()
            c["written_runs"] += len(run_payload)
    return c


def main(argv: list[str] | None = None, client: Any = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill V2 exposure from stored gex_strike_snapshots rows (dry run unless --apply).")
    ap.add_argument("--from", dest="d_from", required=True)
    ap.add_argument("--to", dest="d_to", required=True)
    ap.add_argument("--symbol", action="append", choices=["NIFTY", "SENSEX"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--pause", type=float, default=0.2, help="seconds between runs when writing")
    ap.add_argument("--max-days", type=int, default=10, help="refuse a longer range in one invocation (raise it on purpose for the full history)")
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
    errors: list[str] = []
    t0 = time.time()
    d = d0
    while d <= d1:
        if market_hours_now():
            print("STOPPED: 08:30 IST reached on a weekday. Run again later; finished days are skipped."); break
        c = backfill_day(client, d, symbols, a.apply, a.pause, errors)
        print(f"{d} " + " ".join(f"{k}={v}" for k, v in c.items()) + f" elapsed_s={int(time.time() - t0)}", flush=True)
        for k, v in c.items():
            total[k] = total.get(k, 0) + v
        d += timedelta(days=1)
    print("TOTAL " + " ".join(f"{k}={v}" for k, v in total.items()) + f" elapsed_s={int(time.time() - t0)}")
    print(f"INPUT ERROR RUNS: {len(errors)}")
    for e in errors:
        print("  " + e)
    print("BACKFILL " + ("APPLY" if a.apply else "DRY RUN") + " FINISHED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
