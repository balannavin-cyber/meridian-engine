#!/usr/bin/env python3
"""gamma_metrics_tail_probe.py — watchdog on the gamma_metrics retention rule.

THE RULE THIS WATCHES
---------------------
`gamma_metrics` is a 90-day rolling window. It is trimmed by pg_cron, not by anything on
the AWS host:

    pg_cron jobid 19, active, schedule "30 12 * * *"   -- 12:30 UTC daily
    command:  select public.cleanup_gamma_engine_data();

That function (read from pg_proc.prosrc) deletes from four places; the one that matters
here is:

    gamma_metrics  WHERE created_at < now() - interval '90 days'

The predicate is **created_at, not ts**, and the two diverge — the oldest surviving row
has ts 2026-06-10T10:55 against created_at 2026-06-11T04:01. Rows are trimmed on when
they were written, not on the cycle they describe, so the visible `ts` boundary lags the
actual cut and is not a clean 90 days. Reasoning about retention from `ts` gives the
wrong boundary.

No `.py` or `.sh` in meridian-engine deletes from `gamma_metrics`, and neither crontab,
systemd timers, systemd ExecStart lines nor the orchestrator child list does either.
`cleanup_gamma_engine_data` has zero callers in the repo. All of that is consistent: the
deleter lives inside the database, where no filesystem search can see it. The `cron`
schema is not reachable through PostgREST (PGRST205), so inspecting the job or the
function requires the Supabase SQL editor.

WHY IT STILL EXISTS
-------------------
Not to investigate — the mechanism is known. To detect the rule **changing**: a Supabase
migration, an edited function body, an altered schedule, or a job that stops running.
Run it when a document's gamma_metrics row counts fail to reproduce, or after any
migration.

WHAT IT DOES
------------
Appends one dated block to docs/research/gamma_metrics_tail_<YYYY-MM-DD>.md containing:
  * min(ts) and max(ts)
  * total row count
  * per-day row counts for the first 10 calendar days from min(ts)
  * the age in days of the oldest row

The age is read through `ts`, so under the current rule it oscillates between roughly 90
and 91 days rather than holding constant: it drops when the 12:30 UTC job runs and climbs
again at midnight. A sustained climb past that band, or a total row count that stops
growing on a trading day, is the signal worth acting on.

DISCIPLINE
----------
  * READ-ONLY. Only HTTP GETs. It never calls cleanup_gamma_engine_data, which deletes.
  * count=exact only. `count=planned` with a not.is.null filter over an all-NULL column
    returns a planner floor of 1, which is not a row; that trap has bitten this project.
  * A 57014 is never recorded as an absence. Any timeout aborts the run with a non-zero
    exit rather than writing a number that reads like a measurement.
  * Never prints or writes credentials.

NOT SCHEDULED. Deliberately operator-invoked. See docs/research/README.md.
"""
import datetime as dt
import os
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = "/home/ssm-user/meridian-engine/.env"
TABLE = "gamma_metrics"
FIRST_N_DAYS = 10
OUT_DIR = Path(__file__).resolve().parent


class Unresolved(Exception):
    """A probe returned something that is neither a value nor a real empty result."""


def load_creds():
    v = dotenv_values(ENV_PATH)
    url, key = v.get("SUPABASE_URL"), v.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit(f"FATAL: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in {ENV_PATH}")
    return url.rstrip("/"), {"apikey": key, "Authorization": f"Bearer {key}"}


def get(url, headers, params, prefer=None, timeout=45):
    h = dict(headers)
    if prefer:
        h["Prefer"] = prefer
    r = requests.get(f"{url}/rest/v1/{TABLE}", headers=h, params=params, timeout=timeout)
    if r.status_code not in (200, 206):
        raise Unresolved(f"HTTP {r.status_code} on params={params!r}: {r.text[:200]}")
    return r


def bound(url, headers, direction):
    r = get(url, headers, [("select", "ts"), ("order", f"ts.{direction}"), ("limit", "1")])
    rows = r.json()
    return rows[0]["ts"] if rows else None


def exact_count(url, headers, params):
    r = get(url, headers, params + [("select", "*"), ("limit", "0")], prefer="count=exact")
    tail = r.headers.get("Content-Range", "").split("/")[-1]
    if not tail.isdigit():
        raise Unresolved(f"count=exact gave no integer: Content-Range={r.headers.get('Content-Range')!r}")
    return int(tail)


def main():
    url, headers = load_creds()
    now = dt.datetime.now(dt.timezone.utc)

    try:
        ts_min = bound(url, headers, "asc")
        ts_max = bound(url, headers, "desc")
        if ts_min is None:
            raise Unresolved(f"{TABLE} returned zero rows for the min(ts) probe")
        total = exact_count(url, headers, [])
        day0 = dt.date.fromisoformat(ts_min[:10])
        per_day = []
        for i in range(FIRST_N_DAYS):
            d = day0 + dt.timedelta(days=i)
            n = exact_count(url, headers, [("ts", f"gte.{d.isoformat()}"),
                                           ("ts", f"lt.{(d + dt.timedelta(days=1)).isoformat()}")])
            per_day.append((d, n))
    except Unresolved as e:
        print(f"UNRESOLVED — nothing written. {e}", file=sys.stderr)
        return 2
    except requests.RequestException as e:
        print(f"UNRESOLVED — nothing written. transport: {e}", file=sys.stderr)
        return 2

    age_days = (now.date() - day0).days
    out = OUT_DIR / f"gamma_metrics_tail_{now.date().isoformat()}.md"
    new_file = not out.exists()

    lines = []
    if new_file:
        lines += [f"# `{TABLE}` tail measurements — {now.date().isoformat()}", "",
                  "Appended by `gamma_metrics_tail_probe.py`. One block per run.",
                  "All counts are `count=exact`. Read-only.", ""]
    lines += [
        "---", "",
        f"## Run at {now.isoformat()}", "",
        f"- `min(ts)` = `{ts_min}`",
        f"- `max(ts)` = `{ts_max}`",
        f"- total rows (`count=exact`) = **{total:,}**",
        f"- oldest row age at run time = **{age_days} days**",
        "",
        f"First {FIRST_N_DAYS} calendar days from `min(ts)`:", "",
        "| date | rows |", "|---|---:|",
    ]
    lines += [f"| {d.isoformat()} | {n:,} |" for d, n in per_day]
    lines += ["", "Queries:", "```",
              f"GET /{TABLE}?select=ts&order=ts.asc|desc&limit=1",
              f"GET /{TABLE}?select=*&limit=0                      Prefer: count=exact",
              f"GET /{TABLE}?select=*&limit=0&ts=gte.<d>&ts=lt.<d+1>  Prefer: count=exact",
              "```", ""]

    with out.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"{'created' if new_file else 'appended to'} {out}")
    print(f"min(ts)={ts_min}  total={total:,}  oldest_row_age={age_days}d")
    for d, n in per_day:
        print(f"  {d} {n:>6,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
