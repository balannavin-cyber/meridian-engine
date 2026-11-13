"""Tape live: render a row as the tape_live_* table will hold it (docs/tape/L2_live_runner_plan.md section 4, Phase B).

PURE: stdlib + the column authorities. The column order of the four tables is ddl.tables() (which takes the two copied tables
from services/tape_db/tape_schema.py), never retyped here. A copied-table row is ``trading_day`` followed by the L0 fields in
their CSV order (that is tape_schema's DB order: ``added`` then the renamed CSV columns), then ``as_of, live_run_id, code_sha``.
Empty field = NULL, as services/tape_db/load_day.convert reads it.

``trading_day`` is the IST calendar date of the row's ``ts_ist`` (never the UTC date): the stage-2b write policy is to check
trading_day = today (IST), so a UTC slip would refuse every write. A row whose IST date is not the run's day is refused here.
"""
import csv
import io
from datetime import datetime, timedelta, timezone

from services.tape_live import ddl

IST = timezone(timedelta(hours=5, minutes=30))
PROV = tuple(c for c, _t in ddl.PROV)
COLUMNS = dict((t, tuple(c for c, _ty, _nn in cols)) for t, cols, _pk, _uq, _ck in ddl.tables())
COPIED = ("tape_live_cycle", "tape_live_events")
DATA_N = dict((t, len(c) - len(PROV)) for t, c in COLUMNS.items())


def trading_day_of(ts):
    """ISO timestamp with offset -> the IST calendar date 'YYYY-MM-DD'."""
    return datetime.fromisoformat(ts).astimezone(IST).strftime("%Y-%m-%d")


def header(table, delta=False):
    return ",".join((("op",) if delta else ()) + COLUMNS[table])


def line(fields):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(fields)
    return buf.getvalue()[:-1]


def data_row(table, day, fields):
    """Data columns (no provenance) of a copied table from the L0 CSV fields (a list, in L0 column order)."""
    if table not in COPIED:
        raise ValueError("not a copied table: %s" % table)
    ts = fields[list(COLUMNS[table]).index("ts_ist") - 1]
    td = trading_day_of(ts)
    if td != day:
        raise ValueError("row ts_ist %s is IST date %s, not the run's day %s" % (ts, td, day))
    out = [td] + list(fields)
    if len(out) != DATA_N[table]:
        raise ValueError("%s: %d data fields, the DDL has %d" % (table, len(out), DATA_N[table]))
    return out


def dict_row(table, day, row):
    """Data columns (no provenance) of tape_live_wall / tape_live_label from a dict keyed by the DDL column names."""
    td = trading_day_of(row["ts_ist"])
    if td != day or row["trading_day"] != day:
        raise ValueError("row ts_ist %s is IST date %s, trading_day %s, run day %s" % (row["ts_ist"], td, row["trading_day"], day))
    return ["" if row[c] is None else str(row[c]) for c in COLUMNS[table][:DATA_N[table]]]


def full(data, as_of, live_run_id, code_sha):
    return list(data) + [as_of, live_run_id, code_sha]
