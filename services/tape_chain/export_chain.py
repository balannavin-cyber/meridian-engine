#!/usr/bin/env python3
"""Tape T1b chain export: one symbol, one IST day of gex_strike_snapshots -> CSV + sha256 sidecar. OPERATOR-RUN.

  python -m services.tape_chain.export_chain --symbol NIFTY --day 2026-11-02 [--out-root C:\\tape_data] [--force]

Writes <out-root>\\chain_<day>\\gex_strike_snapshots_<SYMBOL>.csv and <same>.sha256 ("<hex>  <name>").
SELECT only: one table, read through the engine's own client (core.supabase_client.SupabaseClient.select, which
loads SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY from the engine .env). No write call of any kind, no other table.
Paging is 1000 rows a request (CLAUDE.md rule 15) until a short batch or a row past the day's end.
"""
import argparse
import csv
import hashlib
import os
import re
import sys
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path[:0] = [_ROOT]

TABLE = "gex_strike_snapshots"
COLUMNS = "run_id,symbol,ts,expiry_date,strike,oi_call,oi_put,gex_cr"
HEADER = COLUMNS.split(",")
ORDER = "ts.asc,expiry_date.asc,strike.asc,run_id.asc"
PAGE = 1000
IST = timezone(timedelta(hours=5, minutes=30))


def fetch_day(client, symbol, day):
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST)
    end = start + timedelta(days=1)
    rows, offset, past_end = [], 0, 0
    while True:
        batch = client.select(TABLE, columns=COLUMNS,
                              filters={"symbol": "eq." + symbol, "ts": "gte." + start.isoformat()},
                              order=ORDER, limit=PAGE, offset=offset)
        for r in batch:
            if datetime.fromisoformat(str(r["ts"])) >= end:
                past_end += 1
            else:
                rows.append(r)
        offset += PAGE
        if len(batch) < PAGE or past_end:
            return rows, past_end


def main(argv=None):
    ap = argparse.ArgumentParser(prog="export_chain", description=__doc__.split("\n")[0])
    ap.add_argument("--symbol", required=True, choices=("NIFTY", "SENSEX"))
    ap.add_argument("--day", required=True)
    ap.add_argument("--out-root", default="C:\\tape_data")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.day):
        print("--day must be YYYY-MM-DD", file=sys.stderr)
        return 2
    d = os.path.join(args.out_root, "chain_" + args.day)
    name = "gex_strike_snapshots_%s.csv" % args.symbol
    path = os.path.join(d, name)
    if os.path.exists(path) and not args.force:
        print("refusing to overwrite %s (use --force)" % path, file=sys.stderr)
        return 2
    from core.supabase_client import SupabaseClient
    rows, past_end = fetch_day(SupabaseClient(), args.symbol, args.day)
    if not rows:
        print("no rows for %s on %s; nothing written" % (args.symbol, args.day), file=sys.stderr)
        return 2
    os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(HEADER)
        for r in rows:
            w.writerow(["" if r.get(c) is None else r[c] for c in HEADER])
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    with open(path + ".sha256", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("%s  %s\n" % (digest, name))
    ts = sorted(str(r["ts"]) for r in rows)
    print("EXPORT OK %s %s: %d rows, %d runs, %d expiries, first ts %s, last ts %s, %d rows past the day discarded"
          % (args.symbol, args.day, len(rows), len({r["ts"] for r in rows}), len({r["expiry_date"] for r in rows}),
             ts[0], ts[-1], past_end))
    print("sha256 %s -> %s" % (digest, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
