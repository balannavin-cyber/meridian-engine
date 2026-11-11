"""Tape live: the ONE place that learns the two wall strikes (docs/tape/L0_plan.md section 4; spec s3).

Chain-side access in services/tape_live/ happens here and nowhere else (asserted by tests/test_tape_live.py). It reads only what a wall
needs: per run, the front expiry, the call wall (largest oi_call), the put wall (largest oi_put) and those two OI values.
The definitions are merdian_compute.tape.chain_events.build_runs, the same code that made the offline chain runs, so the live
wall and the scored wall cannot be defined twice.

  L0  runs_from_snapshot_csv: the gex_strike_snapshots export CSVs (run_id, symbol, ts, expiry_date, strike, oi_call, oi_put,
      gex_cr), as the T1b chain step reads them.
      runs_from_chain_runs_csv: the final chain_runs.csv of the offline chain step (walls only; verify_day uses it).
  L2  one SELECT on gex_strike_snapshots, front expiry, behind the same function shape (not built).

Timestamp width (docs/tape/L0_ts_width_plan.md). Postgres drops trailing zeros from a timestamptz, so a snapshot ts arrives with a
fraction of 0 to 6 digits; Python 3.10 fromisoformat accepts only 0, 3 or 6 (3.11+ accept all). chain_events.parse_ts is shared with
the scoring chain and is not edited here: every snapshot row goes through norm_snapshot_ts first, via the one build_runs below,
which is the ONLY call of chain_events.build_runs in services/tape_live/ (asserted by guard live-ts-width). A later live reader
(L2) builds its rows and calls this build_runs, so it inherits the normaliser.

Grid rule (the scorer's reconciliation): the run used for grid point T is the latest run whose timestamp, floored to the
5-minute grid, is <= T.
"""
import csv
import re
from datetime import datetime, timedelta, timezone

from merdian_compute.tape import chain_events

# The only shape seen in 130,954 exported values (2026-11-02..06): T separator, UTC offset written +00:00, fraction optional.
# Anything else (Z, +00, a space separator, surrounding whitespace) is refused: it would crash Python 3.10 or hide a new wire.
SNAP_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?([+-]\d{2}:\d{2})$")


def _k(v):
    return "" if v is None else chain_events._k(v)


def norm_snapshot_ts(s):
    """One gex_strike_snapshots ts -> the same instant with a fraction of 0 or 6 digits.

    Pads the fraction on the right with zeros (.4396 -> .439600); never truncates, never rounds. Pure string work, so the
    result does not depend on the interpreter. Raises ValueError on a fraction wider than 6 digits and on any other shape.
    """
    m = SNAP_TS_RE.match(s)
    if m is None:
        raise ValueError("snapshot ts %r: not YYYY-MM-DDTHH:MM:SS[.f]+HH:MM" % (s,))
    frac = m.group(2)
    if frac is None:
        return s
    if len(frac) > 6:
        raise ValueError("snapshot ts %r: fraction wider than 6 digits (never rounded)" % (s,))
    return "%s.%s%s" % (m.group(1), frac.ljust(6, "0"), m.group(3))


def build_runs(rows, day):
    """The ONLY call of chain_events.build_runs in services/tape_live/: normalises every row's ts first. -> (by symbol, counters)."""
    return chain_events.build_runs([dict(r, ts=norm_snapshot_ts(r["ts"])) for r in rows], day)


def runs_from_snapshot_csv(paths, day):
    """-> {symbol: [run dicts of strings, in time order]}."""
    rows = []
    for p in paths:
        with open(p, encoding="utf-8", newline="") as fh:
            rows += list(csv.DictReader(fh))
    return runs_from_rows(rows, day)


def runs_from_rows(rows, day):
    """rows: dicts with the export columns. -> {symbol: [run dicts of strings, in time order]} (the L0 and L2 shared tail)."""
    by_sym, _cnt = build_runs(rows, day)
    out = {}
    for sym in sorted(by_sym):
        lst = []
        for r in by_sym[sym]:
            cw, pw = r["call_wall"], r["put_wall"]
            lst.append({"symbol": sym, "expiry": r["expiry"], "ts_ist": r["ts_ist"], "run_id": r["run_id"],
                        "call_wall": _k(cw), "put_wall": _k(pw),
                        "call_wall_oi_call": "" if cw is None else str(r["strikes"][cw][0]),
                        "put_wall_oi_put": "" if pw is None else str(r["strikes"][pw][1])})
        out[sym] = lst
    return out


def runs_from_chain_runs_csv(path):
    """The final chain runs (walls, no OI) -> {symbol: [run dicts]} in file order (time order per symbol)."""
    out = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["symbol"], []).append({
                "symbol": r["symbol"], "expiry": r["expiry"], "ts_ist": r["ts_ist"], "run_id": r["run_id"],
                "call_wall": r["call_wall"], "put_wall": r["put_wall"], "call_wall_oi_call": "", "put_wall_oi_put": ""})
    return out


def _floor5(ts):
    m = int(ts[11:13]) * 60 + int(ts[14:16])
    return m - m % 5


def wall_row(runs, day, hhmm):
    """runs: one symbol's runs in time order. -> the tape_live_wall row for grid point hhmm ('HH:MM'), or None."""
    tm = int(hhmm[:2]) * 60 + int(hhmm[3:5])
    best = None
    for r in runs:
        if _floor5(r["ts_ist"]) <= tm:
            best = r
        else:
            break
    if best is None:
        return None
    return {"symbol": best["symbol"], "trading_day": day, "expiry": best["expiry"], "ts_ist": "%sT%s:00+05:30" % (day, hhmm),
            "chain_run_id": best["run_id"], "chain_run_ts": best["ts_ist"], "call_wall": best["call_wall"],
            "put_wall": best["put_wall"], "call_wall_oi_call": best["call_wall_oi_call"],
            "put_wall_oi_put": best["put_wall_oi_put"]}


# ===================================================================== L2 live runner, Phase A (docs/tape/L2_live_runner_plan.md s6)
# The three queries the runner may send. Each is ONE read-only transaction with an 8 s statement timeout, an explicit column
# list (the count query selects count(*) and nothing else), the IST day bounds, an `until` bound and a strict keyset predicate on
# the full sort tuple (ts, expiry_date, strike, run_id): the table's unique key is (run_id, strike, expiry_date), so the tuple is
# unique and the order total; a strict `>` neither repeats a row nor skips one at a page boundary. Values arrive as psql
# variables (-v), never interpolated into the text. tests/test_tape_live.py (live-runner-bounded-sql) parses these constants.
PAGE_LIMIT = 5000
SNAP_COLS = ("run_id", "symbol", "ts", "expiry_date", "strike", "oi_call", "oi_put", "gex_cr")
WRITE_PRIVS_PROBE = "INSERT,UPDATE,DELETE,TRUNCATE"

SNAPSHOT_SQL = (
    "BEGIN TRANSACTION READ ONLY;\n"
    "SET LOCAL statement_timeout = '8s';\n"
    "SET LOCAL TIME ZONE 'UTC';\n"
    "SELECT run_id, symbol, ts, expiry_date, strike, oi_call, oi_put, gex_cr\n"
    "FROM public.gex_strike_snapshots\n"
    "WHERE symbol = :'sym'\n"
    "  AND ts >= (:'day')::date::timestamp AT TIME ZONE 'Asia/Kolkata'\n"
    "  AND ts < ((:'day')::date + 1)::timestamp AT TIME ZONE 'Asia/Kolkata'\n"
    "  AND ts <= (:'until')::timestamptz\n"
    "  AND (ts, expiry_date, strike, run_id::text) > ((:'k_ts')::timestamptz, (:'k_exp')::date, (:'k_strike')::numeric, :'k_run')\n"
    "ORDER BY ts, expiry_date, strike, run_id::text\n"
    "LIMIT 5000;\n"
    "COMMIT;\n")

COUNT_SQL = (
    "BEGIN TRANSACTION READ ONLY;\n"
    "SET LOCAL statement_timeout = '8s';\n"
    "SET LOCAL TIME ZONE 'UTC';\n"
    "SELECT count(*)\n"
    "FROM public.gex_strike_snapshots\n"
    "WHERE symbol = :'sym'\n"
    "  AND ts >= (:'day')::date::timestamp AT TIME ZONE 'Asia/Kolkata'\n"
    "  AND ts < ((:'day')::date + 1)::timestamp AT TIME ZONE 'Asia/Kolkata'\n"
    "  AND ts <= (:'until')::timestamptz\n"
    "  AND (ts, expiry_date, strike, run_id::text) <= ((:'k_ts')::timestamptz, (:'k_exp')::date, (:'k_strike')::numeric, :'k_run')\n"
    ";\n"
    "COMMIT;\n")

# Start-up refusal: who am I, is the session read-only, can this role write the table. Reads no relation.
CHECK_SQL = (
    "BEGIN TRANSACTION READ ONLY;\n"
    "SET LOCAL statement_timeout = '8s';\n"
    "SELECT current_user, current_setting('default_transaction_read_only'),\n"
    "  has_table_privilege(current_user, 'public.gex_strike_snapshots', :'privs');\n"
    "COMMIT;\n")

PSQL_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?\+00$")
IST = timezone(timedelta(hours=5, minutes=30))


def psql_ts(s):
    """psql text of a timestamptz under TIME ZONE 'UTC' ('2026-11-06 03:00:21.4396+00') -> the export shape
    ('2026-11-06T03:00:21.4396+00:00'). Strict: any other shape raises, nothing is guessed."""
    m = PSQL_TS_RE.match(s)
    if m is None:
        raise ValueError("database timestamp has an unexpected shape")
    return "%sT%s%s+00:00" % (m.group(1), m.group(2), "" if m.group(3) is None else "." + m.group(3))


def rows_from_psql_csv(text):
    """psql --csv -t output of SNAPSHOT_SQL -> [row dicts keyed by SNAP_COLS, ts in the export shape]."""
    out = []
    for r in csv.reader(text.splitlines()):
        if not r:
            continue
        if len(r) != len(SNAP_COLS):
            raise ValueError("database row has %d fields, expected %d" % (len(r), len(SNAP_COLS)))
        d = dict(zip(SNAP_COLS, r))
        d["ts"] = psql_ts(d["ts"])
        out.append(d)
    return out


def _dt(ts):
    return datetime.fromisoformat(norm_snapshot_ts(ts))


def row_key(r):
    """The sort tuple of a row (the keyset order)."""
    return (_dt(r["ts"]), r["expiry_date"], float(r["strike"]), r["run_id"])


def cursor_of(r):
    """A row's keyset cursor: the four strings the next page is asked to be strictly after."""
    return (r["ts"], r["expiry_date"], r["strike"], r["run_id"])


def cursor_key(c):
    return (_dt(c[0]), c[1], float(c[2]), c[3])


def day_start_cursor(day):
    return ("%sT00:00:00+05:30" % day, "0001-01-01", "-1", "")


def _slot(r):
    d = _dt(r["ts"]).astimezone(IST)
    m = d.hour * 60 + d.minute
    return m - m % 5


class RunAccumulator:
    """Every chain row read so far, deduplicated on the table's unique key (run_id, strike, expiry_date)."""

    def __init__(self, day):
        self.day = day
        self.rows = {}
        self.by_sym = {}
        self.slots = {}
        self.new_runs = {}
        self.seen_runs = set()
        self.row_changed = 0
        self.version = 0
        self._runs = (None, None)

    def add(self, sym, page):
        n = 0
        for r in page:
            k = (r["run_id"], r["expiry_date"], float(r["strike"]))
            old = self.rows.get(k)
            if old is not None:
                if old != r:
                    self.row_changed += 1
                    self.rows[k] = dict(r)
                    self.version += 1
                continue
            self.rows[k] = dict(r)
            self.by_sym.setdefault(sym, []).append(self.rows[k])
            self.slots.setdefault(sym, set()).add(_slot(r))
            rk = (sym, r["run_id"])
            if rk not in self.seen_runs:
                self.seen_runs.add(rk)
                self.new_runs.setdefault(sym, []).append((r["run_id"], r["ts"]))
            n += 1
        if n:
            self.version += 1
        return n

    def rows_of(self, sym):
        return list(self.by_sym.get(sym, []))

    def count_upto(self, sym, cursor):
        ck = cursor_key(cursor)
        return sum(1 for r in self.by_sym.get(sym, []) if row_key(r) <= ck)

    def has_slot(self, sym, minute):
        return minute in self.slots.get(sym, ())

    def pop_new_runs(self, sym):
        out, self.new_runs[sym] = self.new_runs.get(sym, []), []
        return out

    def runs(self):
        """{symbol: [run dicts]} through the one build_runs; rebuilt only when rows arrived."""
        if self._runs[0] != self.version:
            self._runs = (self.version, runs_from_rows([r for rs in self.by_sym.values() for r in rs], self.day))
        return self._runs[1]


class LocalChainSource:
    """Test and rehearsal source: the export CSVs, each row visible at its ts plus delay_fn(row) seconds (or visible_from(row) plus
    delay_fn(row) when given). read_page and count_upto have the semantics of SNAPSHOT_SQL and COUNT_SQL."""

    def __init__(self, paths, day, delay_fn=None, visible_from=None):
        self.delay_fn, self.visible_from = delay_fn, visible_from
        self.by_sym = {}
        for p in paths:
            with open(p, encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    if _dt(r["ts"]).astimezone(IST).strftime("%Y-%m-%d") != day:
                        continue
                    self.by_sym.setdefault(r["symbol"], []).append(dict((c, r[c]) for c in SNAP_COLS))
        self.keyed = {}
        for sym, rows in self.by_sym.items():
            ks = sorted(((row_key(r), r) for r in rows), key=lambda kr: kr[0])
            self.keyed[sym] = [(k, r, self._avail(k, r)) for k, r in ks]

    def _avail(self, k, r):
        base = k[0].timestamp() if self.visible_from is None else self.visible_from(r)
        return base + (self.delay_fn(r) if self.delay_fn else 0)

    def read_page(self, sym, cursor, until, limit):
        ck = cursor_key(cursor)
        out = []
        for k, r, av in self.keyed.get(sym, []):
            if k > ck and av <= until:
                out.append(dict(r))
                if len(out) >= limit:
                    break
        return out

    def count_upto(self, sym, cursor, until):
        ck = cursor_key(cursor)
        return sum(1 for k, _r, av in self.keyed.get(sym, []) if k <= ck and av <= until)
