"""Tape live stage 2b: the database writer (docs/tape/L2_live_runner_plan.md section 16; the build plan is _l2_logs/2b_writer_plan.md).

Standard library plus the tape packages. No process and no network access here: every statement is rendered completely as text
before a transaction opens, and the only thing that leaves this module is that text, handed to a sink (services/tape_live/
live_sources.PsqlWriteSink, the one module with process code). Upsert-only: a removal line of a delta file is never turned into a
statement, and the names of the removal privileges exist in this module only in PRIV_PROBE, the privilege probe of the
start-up check. The write role cannot remove rows (grants); the newest-epoch rule of plan section 4 hides rows an epoch left behind.

Per cycle the writer sends exactly the rows whose value differs from what it believes the table holds (its model: the rows of every
script that committed). After a skipped write those rows are simply still different, so the next cycle sends them again; nothing
is computed inside a transaction and there is no retry loop. Rows are sent in batches of N per statement, one transaction per cycle
for all four tables, one psql process per cycle.

Stop (ruling R8-D, carried across days by R8-I): no further statement; the runner keeps producing files. The latch is the root file
<out>/WRITE_LATCH.json (never inside a day directory), written atomically before the day's informational WRITE_STOPPED sentinel.
It stays until `cli write-clear` removes it, so a stop on day D keeps the writer stopped on D+1 and later. A re-dated test run
(R8-A) has its own latch file and never reads, writes or clears the real one.
"""
import csv
import io
import json
import os
import re
import statistics
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from merdian_compute.tape import cycle as tape_cycle
from services.tape_live import ddl, dbshape, writer

IST = timezone(timedelta(hours=5, minutes=30))
TABLES = ("tape_live_cycle", "tape_live_events", "tape_live_wall", "tape_live_label")
COLUMNS = dict((t, tuple(dbshape.COLUMNS[t])) for t in TABLES)
_DDL = dict((t, (cols, pk, uq)) for t, cols, pk, uq, _ck in ddl.tables())
TYPES = dict((t, dict((c, ty) for c, ty, _nn in _DDL[t][0])) for t in TABLES)
NOTNULL = dict((t, set(c for c, _ty, nn in _DDL[t][0] if nn)) for t in TABLES)
# the columns of the conflict key: the primary key, or events' grain unique (events has no primary key)
KEY_COLS = dict((t, tuple(_DDL[t][1] or _DDL[t][2])) for t in TABLES)
GRAIN_COLS = tuple(_DDL["tape_live_cycle"][2])
CONSTRAINT = dict((t, t + ("_pk" if _DDL[t][1] else "_grain_uq")) for t in TABLES[:3])
IDX = dict((t, dict((c, i) for i, c in enumerate(COLUMNS[t]))) for t in TABLES)
PROV = ("as_of", "live_run_id", "code_sha")

REDATE_ENV = "TAPE_LIVE_TEST_REDATE"
LATCH_NAME, LATCH_REDATE = "WRITE_LATCH.json", "WRITE_LATCH.redate.json"
CLEAR_STALE_S = 600           # write-clear: a heartbeat younger than this counts as a running runner (healthy gap <= about 300 s)
BATCH_ROWS = 500
OVERRUN_S = 300.0
# a rebuild trigger is one of these; any other trigger in the epoch log is a within-epoch removal bump (plan section 4)
REBUILD_TRIGGERS = ("late_segment", "subscriptions")
# Item 7a, ruling R9-B: on a drop bump cycle, stop only if the excess of wall_s over the median of the window is above the median
# (REL_EXCESS_7A x median) AND above MIN_EXCESS_S_7A seconds; the window is the cycles from the 09:20 grid point on, current included.
FROM_T_7A = tape_cycle.FIRST_T      # 560 = 09:20 IST: pre-open cycles never enter the median
MIN_CYCLES_7A = 6                   # cycles in that window, the current one included, before 7a can stop
REL_EXCESS_7A = 1.0
MIN_EXCESS_S_7A = 30.0

# The privileges the start-up check reads. Whatever the write role must NOT hold sits here, and nowhere else in this module.
PRIV_PROBE = ("DELETE", "TRUNCATE", "INSERT", "UPDATE")
P_REMOVAL, P_WRITE, P_CHANGE = PRIV_PROBE[:2], PRIV_PROBE[2], PRIV_PROBE[3]

TEMPLATES = {
    "tape_live_cycle": "INSERT INTO public.tape_live_cycle (%s) VALUES\n%s\n%s;",
    "tape_live_events": "INSERT INTO public.tape_live_events (%s) VALUES\n%s\n%s;",
    "tape_live_wall": "INSERT INTO public.tape_live_wall (%s) VALUES\n%s\n%s;",
    "tape_live_label": "INSERT INTO public.tape_live_label (%s) VALUES\n%s\n%s;",
}
CONFLICT_UPSERT = "ON CONFLICT ON CONSTRAINT %s DO UPDATE SET %s"
CONFLICT_FIRST_WINS = "ON CONFLICT DO NOTHING"
SCRIPT_HEAD = ("\\set ON_ERROR_STOP 1\n\\set VERBOSITY sqlstate\n\\timing on\nBEGIN;\n"
               "SET LOCAL standard_conforming_strings = on;\nSET LOCAL lock_timeout = '5s';\n")
SCRIPT_TAIL = "COMMIT;\n"

# SQLSTATE -> category. 23505 can only be the cycle grain unique (every other key is a conflict target, labels are first-wins).
STATE_CATEGORY = {"57014": "statement_timeout", "55P03": "lock", "40P01": "lock", "25P03": "idle_tx_timeout",
                  "42501": "rls_refused", "53300": "connection_limit", "23505": "unique"}
SQLSTATE_RE = re.compile(r"ERROR:\s+([0-9A-Z]{5})\b")
# The ONE connect-time text that means the role's connection limit: the PostgreSQL server's own refusal for the write role.
# Any other failure with no SQLSTATE (a pooler's message included) is a plain connect failure.
CONN_LIMIT_TEXT = 'FATAL:  too many connections for role "tape_w"'
SKIP_TIER = ("statement_timeout", "lock", "connect")
WERR = ("statement_timeout", "lock", "idle_tx_timeout", "rls_refused", "connection_limit", "connect", "other")

METRIC_COLS = tuple("%s_%s" % (p, t.replace("tape_live_", "")) for t in TABLES
                    for p in ("up_s", "up_max_stmt_s", "up_rows", "up_stmts")) + (
    "up_label_skipped", "cycle_grain_uq_violations", "up_proc_s", "write_state") + tuple("werr_" + w for w in WERR)


def latch_path(out, redate):
    return os.path.join(out, LATCH_REDATE if redate else LATCH_NAME)


def read_latch(out, redate):
    """None when there is no latch; the latch dict when there is one; a fail-closed 'latch_unreadable' latch when it cannot be parsed."""
    p = latch_path(out, redate)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            lt = json.load(fh)
        if not isinstance(lt, dict) or not lt.get("reason"):
            raise ValueError("not a latch")
    except (OSError, ValueError):
        return {"reason": "latch_unreadable", "category": "latch_unreadable", "at": None, "day": None, "set_utc": None}
    return lt


class Refused(Exception):
    """The write set cannot be rendered or is not safe to send: the writer stops with this reason."""

    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


def now_ist():
    """The writer's local today (an aware IST datetime). The one seam the guards replace."""
    return datetime.now(IST)


# ------------------------------------------------------------------------------------------- start-up
def _check_sql():
    parts = ["SELECT 'role', current_user, NULL, NULL",
             "SELECT 'super', CASE WHEN rolsuper THEN 't' ELSE 'f' END, NULL, NULL FROM pg_roles WHERE rolname = current_user",
             "SELECT 'bypassrls', CASE WHEN rolbypassrls THEN 't' ELSE 'f' END, NULL, NULL FROM pg_roles WHERE rolname = current_user",
             "SELECT 'scs', current_setting('standard_conforming_strings'), NULL, NULL",
             "SELECT 'ist_date', ((now() AT TIME ZONE 'Asia/Kolkata')::date)::text, NULL, NULL"]
    for t in TABLES:
        for p in PRIV_PROBE:
            parts.append("SELECT 'priv', '%s', '%s', CASE WHEN has_table_privilege(current_user, 'public.%s', '%s') "
                         "THEN 't' ELSE 'f' END" % (t, p, t, p))
    return "\nUNION ALL ".join(parts) + ";\n"


CHECK_SQL = _check_sql()


def parse_check(text):
    """The start-up check's csv -> {name: value, 'priv': {(table, privilege): 't' | 'f'}}."""
    out = {"priv": {}}
    for r in csv.reader(io.StringIO(text)):
        if not r:
            continue
        if r[0] == "priv" and len(r) >= 4:
            out["priv"][(r[1], r[2])] = r[3]
        elif len(r) >= 2:
            out[r[0]] = r[1]
    return out


def startup_verdict(chk, ro_user, day, local_today, redate):
    """-> None when the role and the day are fit to write, else the reason text. ro_user: the read role's name (or None)."""
    role = chk.get("role")
    if role != "tape_w":
        return "the connected role is not the write role"
    if ro_user is not None and role == ro_user:
        return "the write role is the same role as the read connection"
    if chk.get("super") != "f" or chk.get("bypassrls") != "f":
        return "the write role is a superuser or bypasses row-level security"
    for t in TABLES:
        for p in P_REMOVAL:
            if chk["priv"].get((t, p)) != "f":
                return "the write role holds a removal privilege on %s" % t
        if chk["priv"].get((t, P_WRITE)) != "t":
            return "the write role lacks the write privilege on %s" % t
        if t != "tape_live_label" and chk["priv"].get((t, P_CHANGE)) != "t":
            return "the write role lacks the change privilege on %s" % t
    if chk.get("scs") != "on":
        return "standard_conforming_strings is not on"
    target = local_today if redate else day      # re-dated: the target is today; otherwise the run day must be today
    if chk.get("ist_date") != target:
        return "the server date is not the date the run is written for"
    if local_today != target:
        return "the local date is not the date the run is written for"
    return None


def redate_refusal(day, clock, db_write, env_value, today):
    """The conditions of the test-only re-dating (ruling R8-A, option B). -> None when all hold, else the reason text."""
    if clock != "sim":
        return "re-dating needs the simulated clock"
    if not db_write:
        return "re-dating needs the write flag"
    if env_value != day:
        return "re-dating needs its environment variable set to the run day"
    if not day < today.isoformat():
        return "re-dating needs a run day before today"
    if today.weekday() < 5:
        return "re-dating runs on a Saturday or Sunday only"
    return None


# ------------------------------------------------------------------------------------------- literals
# (value, type, the text the server prints for `SELECT '<value>'::<type>::text` under TIME ZONE 'UTC'), by hand.
LITERAL_CASES = (
    ("it's", "text", "it's"), ("back\\slash", "text", "back\\slash"), ("a,b;c", "text", "a,b;c"),
    ("line1\nline2", "text", "line1\nline2"), ("ünï☃", "text", "ünï☃"),
    ("$$x$$ --c /*d*/", "text", "$$x$$ --c /*d*/"), ("'' ; semi; --", "text", "'' ; semi; --"),
    ("  pad and trail  ", "text", "  pad and trail  "), ("tab\there", "text", "tab\there"), ("q\"uote", "text", "q\"uote"),
    ("24000.0", "numeric", "24000.0"), ("9", "bigint", "9"), ("2026-11-06", "date", "2026-11-06"),
    ("2026-11-06T09:20:00+05:30", "timestamptz", "2026-11-06 03:50:00+00"), ("true", "boolean", "true"),
    ('{"b":1,"aa":2}', "jsonb", '{"b": 1, "aa": 2}'))


def lit(value, ty, notnull=False):
    """One value as a literal of its DDL type. An empty field is NULL (plan section 4), except in a NOT NULL column, where it is
    the empty string: a label's reason and an event's side are empty for most rows and NOT NULL in the DDL."""
    if value is None or value == "":
        return ("''::" + ty) if notnull else "NULL"
    if "\x00" in value:
        raise Refused("other")
    return "'" + value.replace("'", "''") + "'::" + ty


def literal_script():
    sel = "".join("SELECT %s::text;\n" % lit(v, ty) for v, ty, _e in LITERAL_CASES)
    return ("\\set ON_ERROR_STOP 1\nBEGIN READ ONLY;\nSET LOCAL TIME ZONE 'UTC';\nSET LOCAL standard_conforming_strings = on;\n"
            + sel + "ROLLBACK;\n")


def check_literals(text):
    """-> the cases the server read differently from the expected text (empty = the server parsed every literal as written)."""
    got = [r[0] if r else "" for r in csv.reader(io.StringIO(text))]
    bad = []
    for i, (v, ty, want) in enumerate(LITERAL_CASES):
        if i >= len(got) or got[i] != want:
            bad.append((v, ty))
    if len(got) != len(LITERAL_CASES):
        bad.append(("count", str(len(got))))
    return bad


# ------------------------------------------------------------------------------------------- typed keys
_TS_RE = re.compile(r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d):(\d\d)(?:\.(\d{1,6}))?([+-])(\d\d):(\d\d)$")


def _instant(v):
    m = _TS_RE.match(v)
    if m is None:
        raise Refused("other")
    y, mo, d, h, mi, s = (int(x) for x in m.group(1, 2, 3, 4, 5, 6))
    us = int((m.group(7) or "").ljust(6, "0") or 0)
    off = timedelta(hours=int(m.group(9)), minutes=int(m.group(10)))
    tz = timezone(off if m.group(8) == "+" else -off)
    return datetime(y, mo, d, h, mi, s, us, tzinfo=tz).astimezone(timezone.utc)


def _norm(ty, v):
    if v is None or v == "":
        return None
    try:
        if ty == "numeric":
            return Decimal(v).normalize()
        if ty in ("bigint", "integer"):
            return int(v)
    except (InvalidOperation, ValueError):
        raise Refused("other")
    if ty == "timestamptz":
        return _instant(v)
    return v


def typed(t, row, cols):
    return tuple(_norm(TYPES[t][c], row[IDX[t][c]]) for c in cols)


def shift_row(t, row, today_iso, days):
    """The re-dated image of a row (test-only): trading_day = today, every timestamptz moved by the same whole days."""
    out = list(row)
    for c, i in IDX[t].items():
        if c == "trading_day":
            out[i] = today_iso
        elif TYPES[t][c] == "timestamptz" and out[i]:
            d = datetime.strptime(out[i][:10], "%Y-%m-%d") + timedelta(days=days)
            out[i] = d.strftime("%Y-%m-%d") + out[i][10:]
    return out


def classify(rc, err):
    """(return code, stderr bytes) -> a category. The text itself is dropped here, never stored."""
    if rc == 0:
        return "ok"
    if rc == 124:
        return "statement_timeout"
    text = (err or b"").decode("utf-8", "replace")
    m = SQLSTATE_RE.search(text)
    if m is not None:
        return STATE_CATEGORY.get(m.group(1), "other")
    if CONN_LIMIT_TEXT in text:
        return "connection_limit"
    return "connect"


_TIME_RE = re.compile(r"^Time:\s+([0-9.]+) ms")
_TAG_RE = re.compile(r"^[A-Z]+ 0 (\d+)$")


def parse_output(text):
    """psql's stdout of a script -> [(rows reported, ms)] for its row-writing statements, in order."""
    out, last = [], None
    for line in text.splitlines():
        m = _TAG_RE.match(line)
        if m is not None:
            last = [int(m.group(1)), None]
            out.append(last)
            continue
        t = _TIME_RE.match(line)
        if t is not None and last is not None and last[1] is None:
            last[1] = float(t.group(1))
            last = None
        elif line and not line.startswith(("Time", "Timing")):
            last = None
    return [(n, ms or 0.0) for n, ms in out]


# ------------------------------------------------------------------------------------------- the writer
class DbWriter:
    def __init__(self, sink, day, batch_rows, out_day, shift=None):
        self.sink, self.day, self.n, self.out_day = sink, day, max(1, int(batch_rows)), out_day
        self.out_root, self.redate, self.latch_day = os.path.dirname(os.path.abspath(out_day)), shift is not None, None
        self.today_iso, self.days = shift if shift else (day, 0)
        self.model = dict((t, {}) for t in TABLES)       # what the table holds: {writer key: full row}
        self.labels = set()
        self.grain, self.held = {}, {}                   # cycle grain (typed) -> primary key (typed), and back
        self.skips, self.stopped, self.db_written = 0, None, None
        self.state, self.withheld, self.walls_seen = "none", {}, []    # withheld: typed cycle grain -> its text
        self.cur = self._zero()
        self.cols = METRIC_COLS

    # -- state ----------------------------------------------------------------------------------------
    def _zero(self):
        z = dict((c, 0) for c in METRIC_COLS)
        for c in METRIC_COLS:
            if c.startswith(("up_s_", "up_max_stmt_s_")):
                z[c] = 0.0
        z["up_proc_s"], z["write_state"] = 0.0, "none"
        return z

    def start(self, st, live_dir, fresh):
        """Restore the persisted latch and counters; rebuild the model from the delta files up to the last committed write."""
        st = st or {}
        self.skips = int(st.get("write_skips", 0))
        self.db_written = st.get("db_written")
        lt = read_latch(self.out_root, self.redate)
        if lt is not None:
            self.stopped = dict((k, lt.get(k)) for k in ("reason", "category", "at"))
            self.latch_day, self.state = lt.get("day"), "stopped"
            self._sentinel()
        p = os.path.join(live_dir, "db_withheld.csv")
        if os.path.exists(p):
            with open(p, encoding="utf-8", newline="") as fh:
                for r in list(csv.reader(fh))[1:]:
                    self.withheld[tuple(_norm(TYPES["tape_live_cycle"][c], v) for c, v in zip(GRAIN_COLS, r))] = r
        if not fresh and self.db_written is not None:
            self._rebuild(live_dir)

    def _rebuild(self, live_dir):
        lim = None if self.db_written == "final" else int(self.db_written)
        cdir = os.path.join(live_dir, "cycles")
        names = sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []
        for fn in names:
            m = re.match(r"^(\d{4}|final)_(cycle|events|wall)\.db\.csv$", fn)
            if m is None:
                continue
            if m.group(1) != "final" and lim is not None and int(m.group(1)[:2]) * 60 + int(m.group(1)[2:]) > lim:
                continue
            if m.group(1) == "final" and lim is not None:
                continue
            t = "tape_live_" + m.group(2)
            with open(os.path.join(cdir, fn), encoding="utf-8", newline="") as fh:
                for r in list(csv.reader(fh))[1:]:
                    if r and r[0] == "U":
                        if t == "tape_live_cycle" and self._is_withheld(r[1:]):
                            continue                  # it never reached the table: the model must not hold it
                        self.model[t][writer._db_key(t, r[1:])] = r[1:]
        for r in self.model["tape_live_cycle"].values():
            self._hold(typed("tape_live_cycle", r, KEY_COLS["tape_live_cycle"]), typed("tape_live_cycle", r, GRAIN_COLS), self.grain, self.held)
        p = os.path.join(live_dir, "tape_live_label.db.csv")
        if os.path.exists(p):
            limit = None if lim is None else tape_cycle.ts_of(self.day, lim)
            with open(p, encoding="utf-8", newline="") as fh:
                for r in list(csv.reader(fh))[1:]:
                    if r and (limit is None or r[2] <= limit):
                        self.labels.add(tuple(r[:5]))

    def _is_withheld(self, row):
        """Whether this cycle row is one the writer withheld: its grain is listed AND its token is the listed one (the row that
        holds that grain in the table has another token and stays in the model)."""
        w = self.withheld.get(typed("tape_live_cycle", row, GRAIN_COLS))
        return w is not None and _norm("bigint", w[-1]) == _norm("bigint", row[IDX["tape_live_cycle"]["instrument_token"]])

    @staticmethod
    def _hold(pk, g, grain, held):
        old = held.get(pk)
        if old is not None and old != g and grain.get(old) == pk:
            del grain[old]
        grain[g], held[pk] = pk, g

    def persist(self):
        return {"write_skips": self.skips, "db_written": self.db_written}

    def status(self):
        out = {"state": self.state, "reason": (self.stopped or {}).get("reason"), "skips": self.skips,
               "db_written": self.db_written}
        if self.stopped:
            out["latch_day"], out["carried"] = self.latch_day, self.latch_day != self.day
        return out

    def row(self):
        c = self.cur
        out = {}
        for k in METRIC_COLS:
            v = c[k]
            if k == "up_proc_s":
                out[k] = "%.6f" % v
            elif k.startswith(("up_s_", "up_max_stmt_s_")):
                out[k] = "%.3f" % v
            else:
                out[k] = v
        out["write_state"] = self.state
        return out

    def _sentinel(self):
        os.makedirs(self.out_day, exist_ok=True)
        with open(os.path.join(self.out_day, "WRITE_STOPPED"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(self.stopped, sort_keys=True) + "\n")

    def _stop(self, reason, category, at):
        self.stopped = {"reason": reason, "category": category, "at": at}
        self.state, self.latch_day = "stopped", self.day
        self._latch()
        self._sentinel()

    def _latch(self):
        """The root latch, atomically (a temporary file, then a rename), before the sentinel."""
        pth = latch_path(self.out_root, self.redate)
        tmp = os.path.join(self.out_root, "." + os.path.basename(pth) + ".tmp")
        try:
            os.makedirs(self.out_root, exist_ok=True)
            body = dict(self.stopped, day=self.day, set_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(body, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, pth)
        except OSError:
            # Disk full or permission: the run must go on (the files are still produced). The writer stays stopped in memory, the
            # sentinel is still written by the caller, and the heartbeat says the latch is NOT on disk: a restart would not see it.
            self.stopped = dict(self.stopped, reason="latch_write_failed", cause=self.stopped["reason"])
            try:
                os.remove(tmp)
            except OSError:
                pass

    def _count(self, cat):
        self.cur["werr_" + cat] += 1

    # -- one cycle --------------------------------------------------------------------------------------
    def cycle(self, T, ld, missed, ignore_missed):
        """T: the grid minute (an int) or 'final'. ld: the LiveDay after its cycle (None before the first grid point)."""
        self.cur = self._zero()
        if self.stopped:
            self.state = "stopped"
            return
        if missed and not ignore_missed:
            self._stop("missed_grid_point", "missed_grid_point", T)
            return
        if ld is None:
            self.state = "none"
            return
        try:
            plan = self._plan(ld)
        except Refused as exc:
            self._count("other")
            self._stop(exc.reason, "other", T)
            return
        if not any(plan["batches"]):
            self.state = "none"
            self.db_written = T
            return
        script = SCRIPT_HEAD + "\n".join(s for _t, s, _n in plan["stmts"]) + "\n" + SCRIPT_TAIL
        t0 = time.perf_counter()
        _rc, out, cat = self.sink.run_script(script, classify)
        self.cur["up_proc_s"] = time.perf_counter() - t0
        if cat != "ok":
            self._failed(cat, T)
            return
        res = parse_output(out)
        if len(res) != len(plan["stmts"]):
            self._count("other")
            self._stop("other", "other", T)
            return
        sent_l = 0
        for (t, _s, nrows), (n_rep, ms) in zip(plan["stmts"], res):
            sh = t.replace("tape_live_", "")
            self.cur["up_s_" + sh] += ms / 1000.0
            self.cur["up_max_stmt_s_" + sh] = max(self.cur["up_max_stmt_s_" + sh], ms / 1000.0)
            self.cur["up_rows_" + sh] += nrows
            self.cur["up_stmts_" + sh] += 1
            if t == "tape_live_label":
                sent_l += nrows - n_rep
        self.cur["up_label_skipped"] = sent_l
        for t, rows in plan["keep"].items():
            for k, r in rows:
                self.model[t][k] = r
        self.labels.update(k for k, _r in plan["new_labels"])
        self.grain, self.held = plan["grain"], plan["held"]
        self.db_written = T
        self.state = "sent"

    def _failed(self, cat, T):
        if cat == "unique":
            self.cur["cycle_grain_uq_violations"] += 1
            self._stop("cycle_grain_uq_unpredicted", "unique", T)
        elif cat in SKIP_TIER:
            self._count(cat)
            self.skips += 1
            self.state = "skipped"
            if self.skips >= 2:
                self._stop("second_skip", cat, T)
        else:
            self._count(cat)
            self._stop(cat, cat, T)

    def end_cycle(self, T, wall_s, lag, epoch_log):
        """After the cycle's write: the overrun and item-7a (R9-B) stops. wall_s: this cycle's seconds so far; lag: its start lag.
        walls_seen is the 7a window: wall_s of the cycles from FROM_T_7A on, in memory only (a restart starts it empty)."""
        if self.stopped:
            return
        if isinstance(T, int) and T >= FROM_T_7A:
            self.walls_seen.append(wall_s)
        if lag + wall_s > OVERRUN_S:
            self._stop("overrun", "overrun", T)
            return
        if len(self.walls_seen) >= MIN_CYCLES_7A and isinstance(T, int) and any(
                e.get("at") == T and e.get("trigger") not in REBUILD_TRIGGERS for e in epoch_log):
            med = statistics.median(self.walls_seen)
            excess = wall_s - med
            if excess > REL_EXCESS_7A * med and excess > MIN_EXCESS_S_7A:
                self._stop("item_7a_drop_bump", "item_7a", T)

    # -- planning ---------------------------------------------------------------------------------------
    def _label_row(self, lab):
        return dbshape.full(dbshape.dict_row("tape_live_label", self.day, lab), *[lab[c] for c in PROV])

    def _plan(self, ld):
        per = {}
        for t in TABLES[:3]:
            per[t] = [(k, r) for k, r in sorted(ld.db[t].items()) if self.model[t].get(k) != r]
        new_labels = [(k, self._label_row(lab)) for k, lab in sorted(ld.labels.items()) if k not in self.labels]
        per["tape_live_label"] = new_labels
        # a conflict key repeated inside one write set (by typed value) would fail the whole statement: never send it
        dup = []
        for t, rows in per.items():
            seen = set()
            for _k, r in rows:
                tk = typed(t, r, KEY_COLS[t])
                if tk in seen:
                    dup.append((t, repr(tk)))
                seen.add(tk)
        if dup:
            self._write_list("db_dupkeys.csv", ("table", "key"), dup)
            raise Refused("dup_conflict_key")
        # the cycle grain unique, simulated in statement order against the model and the rest of this write set
        grain, held = dict(self.grain), dict(self.held)
        keep_c, fresh_keys = [], []
        for k, r in per["tape_live_cycle"]:
            pk, g = typed("tape_live_cycle", r, KEY_COLS["tape_live_cycle"]), typed("tape_live_cycle", r, GRAIN_COLS)
            holder = grain.get(g)
            if holder is not None and holder != pk:
                if g not in self.withheld:
                    fresh_keys.append((g, [r[IDX["tape_live_cycle"][c]] for c in GRAIN_COLS] + [r[IDX["tape_live_cycle"]["instrument_token"]]]))
                continue
            self._hold(pk, g, grain, held)
            keep_c.append((k, r))
        if fresh_keys:
            self._note_withheld(fresh_keys)
        keep = {"tape_live_cycle": keep_c, "tape_live_events": per["tape_live_events"], "tape_live_wall": per["tape_live_wall"],
                "tape_live_label": new_labels}
        stmts = []
        for t in TABLES:
            rows = keep[t]
            for i in range(0, len(rows), self.n):
                chunk = rows[i:i + self.n]
                vals = ",\n".join("(" + ", ".join(lit(v, TYPES[t][c], c in NOTNULL[t]) for c, v in zip(COLUMNS[t], self._out(t, r))) + ")"
                                  for _k, r in chunk)
                if t == "tape_live_label":
                    cf = CONFLICT_FIRST_WINS
                else:
                    keyset = set(KEY_COLS[t])
                    cf = CONFLICT_UPSERT % (CONSTRAINT[t], ", ".join("%s = EXCLUDED.%s" % (c, c) for c in COLUMNS[t] if c not in keyset))
                stmts.append((t, TEMPLATES[t] % (", ".join(COLUMNS[t]), vals, cf), len(chunk)))
        return {"batches": [keep[t] for t in TABLES], "stmts": stmts, "keep": dict((t, keep[t]) for t in TABLES[:3]),
                "new_labels": new_labels if keep["tape_live_label"] else [], "grain": grain, "held": held}

    def _out(self, t, r):
        return shift_row(t, r, self.today_iso, self.days) if self.days or self.today_iso != self.day else r

    def _note_withheld(self, fresh):
        for g, text in fresh:
            self.withheld[g] = text
            self.cur["cycle_grain_uq_violations"] += 1
        self._write_list("db_withheld.csv", GRAIN_COLS + ("instrument_token",), sorted(self.withheld.values()))

    def _write_list(self, name, header, rows):
        d = os.path.join(self.out_day, "live")
        os.makedirs(d, exist_ok=True)
        buf = io.StringIO()
        wr = csv.writer(buf, lineterminator="\n")
        wr.writerow(header)
        wr.writerows(rows)
        with open(os.path.join(d, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(buf.getvalue())
