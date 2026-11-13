"""Tape live L2 runner, Phase A: the 5-minute loop (docs/tape/L2_live_runner_plan.md sections 3, 5, 7, 12). FILE-ONLY, READ-ONLY.

Per grid point T (every 5 minutes, 09:20-15:30 IST for labels; the loop runs from the start time to 15:45): wake at T + lag, list the
three object prefixes, fetch what is new, journal it (arrival_log.csv, fsync per row), feed the LiveDay in the order cli replay uses
(subscriptions, then segments by symbol, key, name), wait for the chain run of T (bounded), run the cycle, write the same files as
`cli replay`, commit state.json, heartbeat, metrics. The runner core touches exactly two interfaces (live_sources): an object source
and a chain source; it never knows which it has. It never writes to S3 or the database; there is no code path that could.

Crash-safe restart: the journal and state.json (written last, atomically) are the only memory. A restart feeds the journalled objects
of committed cycles back in their original cycle order, restores the emitted state from the committed delta files, redoes a cycle
that was journalled but not committed, and continues at the current grid point; grid points that passed meanwhile are recorded as
missed and never back-filled (L0 plan O-2). live_run_id is the per-symbol rebuild epoch of writer.py (plan section 4); the rebuild
epochs are Phase B.

Exit codes: 0 done / killed / stopped / no session; 1 unexpected error; 2 refused at start (cli); 3 memory (MemoryError or soft cap)
or disk floor. Standard library plus the tape packages only.
"""
import csv
import gzip
import io
import json
import os
import re
import shutil
import time
from datetime import datetime, timedelta, timezone

from merdian_compute.tape import cycle, replay, special
from services.tape_live import rules, wall_source, writer
from services.tape_live.live_sources import SourceError, scrub
from services.tape_offline.cycle_day import peak_mb

IST = timezone(timedelta(hours=5, minutes=30))
SYMBOLS = writer.SYMBOLS
GRID_FIRST, GRID_LAST = writer.GRID_FIRST, writer.GRID_LAST
END_T = 15 * 60 + 45
SLICE_S = 5.0
JCOLS = ("kind", "key", "size", "etag", "s3_last_modified", "first_seen_utc", "at", "cycle")
METRIC_COLS = ("day", "T", "wake_utc", "cycle_end_utc", "wall_s", "cpu_self_s", "cpu_children_s", "peak_rss_mb", "rss_mb",
               "s3_list_s", "s3_list_calls", "s3_get_s", "s3_gets", "s3_bytes", "db_s", "db_calls", "db_rows", "chain_wait_s",
               "ready_lag_s_NIFTY", "ready_lag_s_SENSEX", "rebuilds", "rebuild_s", "reemit_rows", "late_segments", "missed_grid_points",
               "run_grew", "errors")
ERR_KINDS = ("s3_list", "s3_get", "md5", "db", "chain_timeout", "other")


def _hm(m):
    return "%02d:%02d" % (m // 60, m % 60)


def _hhmm(m):
    return "%02d%02d" % (m // 60, m % 60)


def day_epoch(day):
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST).timestamp()


def as_of_utc(day, m):
    d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST) + timedelta(minutes=m)
    return d.astimezone(timezone.utc).isoformat()


def iso_utc(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


DB_PARTS = (("tape_live_cycle", "cycle"), ("tape_live_events", "events"), ("tape_live_wall", "wall"))


def state_texts(ld):
    """{file name: text} of the state after a cycle, both shapes (cli replay writes the same files at its end)."""
    texts = {"tape_live_cycle.csv": ld.state_cycle_csv(), "tape_live_events.csv": ld.state_events_csv(),
             "tape_live_wall.csv": _rows_csv(writer.WALL_COLS, [ld.walls[k] for k in sorted(ld.walls)]),
             "tape_live_label.csv": _rows_csv(writer.LABEL_COLS, [ld.labels[k] for k in sorted(ld.labels)])}
    for t in ("tape_live_cycle", "tape_live_events", "tape_live_wall", "tape_live_label"):
        texts[t + ".db.csv"] = ld.db_state_csv(t)
    return texts


def delta_texts(name, d):
    """{file name: text or None} of one cycle's deltas, both shapes."""
    out = dict(("%s_%s.csv" % (name, part), d[part]) for part in ("cycle", "events"))
    for t, part in DB_PARTS:
        out["%s_%s.db.csv" % (name, part)] = d["db"][t]
    return out


def _rows_csv(cols, rows):
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(cols)
    for r in rows:
        wr.writerow([r[c] for c in cols])
    return buf.getvalue()


def _atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def default_rss_mb():
    try:
        with open("/proc/self/status", encoding="ascii") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except (OSError, ValueError):
        pass
    pk = peak_mb()
    return float(pk) if pk else 0.0


def _children_cpu():
    try:
        import resource
        r = resource.getrusage(resource.RUSAGE_CHILDREN)
        return r.ru_utime + r.ru_stime
    except (ImportError, OSError, ValueError):
        return 0.0


# ------------------------------------------------------------------------------------------- clocks
class RealClock:
    def now(self):
        return time.time()

    def sleep(self, s):
        time.sleep(max(0.0, s))


class SimClock:
    """Simulated time: sleep() advances it and runs the scheduled (epoch, function) events it passes."""
    last_now = None

    def __init__(self, start, events=()):
        self._now = float(start)
        self._events = sorted(events, key=lambda e: e[0])
        SimClock.last_now = self._now

    def now(self):
        return self._now

    def sleep(self, s):
        target = self._now + max(0.0, s)
        while self._events and self._events[0][0] <= target:
            t, fn = self._events.pop(0)
            self._now = max(self._now, t)
            fn()
        self._now = target
        SimClock.last_now = self._now


class Config:
    def __init__(self, day, out, code_sha, kill_file=None, lag=20.0, poll_s=15.0, wait_deadline_s=120.0, rss_cap_mb=600.0,
                 disk_floor_mb=1024.0, disk_stop_mb=200.0, end_t=END_T, max_pages=8):
        self.day, self.out, self.code_sha = day, out, code_sha
        self.kill_file = kill_file or os.path.join(out, "KILL")
        self.lag, self.poll_s, self.wait_deadline_s = lag, poll_s, wait_deadline_s
        self.rss_cap_mb, self.disk_floor_mb, self.disk_stop_mb = rss_cap_mb, disk_floor_mb, disk_stop_mb
        self.end_t, self.max_pages = end_t, max_pages
        self.term = {"hit": False}                      # set by the SIGTERM handler (real clock)


class _Stop(Exception):
    def __init__(self, rc):
        Exception.__init__(self, rc)
        self.rc = rc


# ------------------------------------------------------------------------------------------- chain polling (keyset)
class ChainPoller:
    """Reads one symbol's snapshot rows in keyset pages and keeps them in a RunAccumulator.

    The cursor is the full sort tuple of the last row read. Each poll first asks the source how many rows sort at or before the
    cursor and compares that with the rows held: a mismatch means a row was committed below the cursor after it had passed, so it is
    counted (chain_skipped) and the cursor goes back to the day start (the re-read is deduplicated on the unique key)."""

    def __init__(self, src, day, limit=wall_source.PAGE_LIMIT, max_pages=8, counters=None):
        self.src, self.day, self.limit, self.max_pages = src, day, limit, max_pages
        self.counters = counters if counters is not None else {}
        self.acc = wall_source.RunAccumulator(day)
        self.start = wall_source.day_start_cursor(day)
        self.cursor = dict((s, self.start) for s in SYMBOLS)

    def poll(self, sym, until):
        """-> the number of new rows. Raises SourceError; the cursor then stays where the last good page left it."""
        cur = self.cursor[sym]
        if cur != self.start:
            if self.src.count_upto(sym, cur, until) != self.acc.count_upto(sym, cur):
                self.counters["chain_skipped"] = self.counters.get("chain_skipped", 0) + 1
                cur = self.cursor[sym] = self.start
        new = 0
        for _ in range(self.max_pages):
            page = self.src.read_page(sym, cur, until, self.limit)
            new += self.acc.add(sym, page)
            if page:
                cur = self.cursor[sym] = wall_source.cursor_of(page[-1])
            if len(page) < self.limit:
                break
        return new


# ------------------------------------------------------------------------------------------- the runner
SEG_KEY = re.compile(r"^(NIFTY|SENSEX)/(\d{4}-\d{2}-\d{2})/(seg_\d{4}(?:_c\d+)?(?:_r\d+)?\.ndjson\.gz)$")
SUB_KEY = re.compile(r"^session/(\d{4}-\d{2}-\d{2})/(subscriptions_\d{6}(?:_\d+)?\.json)$")
DELTA_NAME = re.compile(r"^(\d{4})_(cycle|events)\.csv$")
DB_DELTA_NAME = re.compile(r"^(\d{4})_(cycle|events|wall)\.db\.csv$")


class Runner:
    def __init__(self, cfg, objs, chain, clock, hooks=None, rss_fn=None, redact=()):
        self.cfg, self.objs, self.chain, self.clock = cfg, objs, chain, clock
        self.hooks, self.rss_fn, self.redact = hooks or {}, rss_fn or default_rss_mb, tuple(redact)
        self.day = cfg.day
        self.t0 = day_epoch(cfg.day)
        self.ddir = os.path.join(cfg.out, cfg.day)
        self.live = os.path.join(self.ddir, "live")
        self.cdir = os.path.join(self.live, "cycles")
        self.rawdir = os.path.join(self.ddir, "raw")
        self.errors = dict((k, 0) for k in ERR_KINDS)
        self.last_error = ""
        self.peak_rss = 0.0
        self.rss = 0.0
        self.last_cycle = None
        self.last_wall = 0.0
        self.last_lag = 0.0
        self.journal, self.jkeys = [], set()
        self.pending = []
        self.missed = []
        self.counters = {}
        self.poller = ChainPoller(chain, cfg.day, max_pages=cfg.max_pages, counters=self.counters)
        self.ld = None
        self.last_t = None
        self.stats = None
        self.missed_now = 0
        self.cur_t = None

    # -- small helpers ---------------------------------------------------------------------------------
    def epoch(self, m):
        return self.t0 + m * 60

    def _hook(self, name, t):
        fn = self.hooks.get(name)
        if fn is not None:
            fn(t, self)

    def _log(self, text):
        with open(os.path.join(self.ddir, "runner.log"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("%s %s\n" % (iso_utc(self.clock.now()), scrub(text, self.redact)))

    def _err(self, kind, category):
        self.errors[kind] += 1
        self.last_error = "%s:%s" % (kind, category)
        if self.stats is not None:
            self.stats["errors"] += 1
        self._log("error " + self.last_error)

    def _hb(self, state):
        hb = {"state": state, "day": self.day, "last_cycle": self.last_cycle, "last_cycle_wall_s": round(self.last_wall, 3),
              "lag_s": round(self.last_lag, 3), "peak_rss_mb": round(self.peak_rss, 1), "rss_mb": round(self.rss, 1),
              "errors": dict(self.errors), "last_error": scrub(self.last_error, self.redact), "pid": os.getpid(),
              "code_sha": self.cfg.code_sha,
              "updated_utc": iso_utc(self.clock.now())}
        _atomic(os.path.join(self.ddir, "heartbeat.json"), json.dumps(hb, sort_keys=True).encode("utf-8"))

    def _stopped(self):
        return self.cfg.term["hit"] or os.path.exists(self.cfg.kill_file)

    def _sleep_until(self, target):
        """Sleep in short slices so the kill switch is seen. -> False when it was seen."""
        while True:
            if self._stopped():
                return False
            now = self.clock.now()
            if now >= target:
                return True
            self.clock.sleep(min(SLICE_S, target - now))

    def _check_rss(self):
        self.rss = float(self.rss_fn())
        self.peak_rss = max(self.peak_rss, self.rss)
        if self.rss > self.cfg.rss_cap_mb:
            self._hb("memory_cap")
            raise _Stop(3)

    def _check_disk(self, floor):
        free = shutil.disk_usage(self.cfg.out).free / 1048576.0
        if free < floor:
            self._hb("disk_floor")
            raise _Stop(3)

    # -- state files -----------------------------------------------------------------------------------
    def _state_path(self):
        return os.path.join(self.ddir, "state.json")

    def _load_state(self):
        try:
            with open(self._state_path(), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def _save_state(self, committed, done):
        st = {"committed": committed, "done": done, "missed": self.missed, "rebuilds": self.ld.rebuilds, "late": self.ld.late,
              "bad_files": self.ld.bad_files, "epoch": self.ld.epoch, "epoch_log": self.ld.epoch_log}
        _atomic(self._state_path(), (json.dumps(st, sort_keys=True, indent=1) + "\n").encode("utf-8"))

    def _write_state_files(self):
        for n, text in state_texts(self.ld).items():
            _atomic(os.path.join(self.live, n), text.encode("utf-8"))

    def _emit(self, name, d):
        os.makedirs(self.cdir, exist_ok=True)
        for n, text in delta_texts(name, d).items():
            p = os.path.join(self.cdir, n)
            if text:
                _atomic(p, text.encode("utf-8"))
            elif os.path.exists(p):
                os.remove(p)

    # -- journal ---------------------------------------------------------------------------------------
    def _journal_load(self):
        p = os.path.join(self.ddir, "arrival_log.csv")
        if not os.path.exists(p):
            return
        with open(p, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                r["at"] = int(r["at"]) if r["at"] != "" else None
                r["cycle"] = int(r["cycle"])
                self.journal.append(r)
                self.jkeys.add(r["key"])

    def _journal_add(self, kind, key, size, etag, last_modified, at, cycle_t):
        p = os.path.join(self.ddir, "arrival_log.csv")
        new = not os.path.exists(p)
        row = {"kind": kind, "key": key, "size": size, "etag": etag, "s3_last_modified": last_modified,
               "first_seen_utc": iso_utc(self.clock.now()), "at": at, "cycle": cycle_t}
        with open(p, "a", encoding="utf-8", newline="") as fh:
            wr = csv.writer(fh, lineterminator="\n")
            if new:
                wr.writerow(JCOLS)
            wr.writerow([("" if row[c] is None else row[c]) for c in JCOLS])
            fh.flush()
            os.fsync(fh.fileno())
        self.journal.append(row)
        self.jkeys.add(key)
        return row

    # -- intake ----------------------------------------------------------------------------------------
    def _cache_path(self, key):
        return os.path.join(self.rawdir, *key.split("/"))

    def _fetch(self, info):
        dest = self._cache_path(info.key)
        want = info.etag if re.match(r"^[0-9a-f]{32}$", info.etag) else None
        if os.path.exists(dest) and want is not None:
            with open(dest, "rb") as fh:
                if _md5(fh.read()) == want:
                    return True
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        t0 = time.perf_counter()
        try:
            self.objs.get(info.key, dest + ".part")
        except SourceError as exc:
            self._err("s3_get", exc.category)
            return False
        finally:
            self.stats["s3_get_s"] += time.perf_counter() - t0
        self.stats["s3_gets"] += 1
        with open(dest + ".part", "rb") as fh:
            body = fh.read()
        if want is not None and _md5(body) != want:
            os.remove(dest + ".part")
            self._err("md5", "mismatch")
            return False
        os.replace(dest + ".part", dest)
        self.stats["s3_bytes"] += len(body)
        return True

    def _intake(self, T):
        fresh = []
        for prefix in ("NIFTY/%s/" % self.day, "SENSEX/%s/" % self.day, "session/%s/" % self.day):
            t0 = time.perf_counter()
            try:
                infos = self.objs.list(prefix)
            except SourceError as exc:
                self._err("s3_list", exc.category)
                infos = []
            self.stats["s3_list_s"] += time.perf_counter() - t0
            self.stats["s3_list_calls"] += 1
            for info in infos:
                if info.key in self.jkeys:
                    continue
                ms, mu = SEG_KEY.match(info.key), SUB_KEY.match(info.key)
                if (ms is not None and ms.group(2) == self.day) or (mu is not None and mu.group(1) == self.day):
                    fresh.append(info)
                else:
                    self._journal_add("ignored", info.key, info.size, info.etag, info.last_modified, None, T)
        order = []
        for info in fresh:
            ms = SEG_KEY.match(info.key)
            if ms is None:
                order.append(((0, replay.sub_sort_key(info.key.rsplit("/", 1)[1])), info))
            else:
                name = ms.group(3)
                order.append(((1, SYMBOLS.index(ms.group(1)), replay.parse_seg_name(name), name), info))
        order.sort(key=lambda o: o[0])
        for _k, info in order:
            if self._fetch(info):
                kind = "segment" if SEG_KEY.match(info.key) else "subscriptions"
                self.pending.append(self._journal_add(kind, info.key, info.size, info.etag, info.last_modified, T, T))

    def _feed_entry(self, e):
        name = e["key"].rsplit("/", 1)[1]
        if e["kind"] == "subscriptions":
            try:
                with open(self._cache_path(e["key"]), encoding="utf-8") as fh:
                    doc = json.load(fh)
            except (OSError, ValueError):
                self._err("other", "unreadable_subscriptions")
                return
            self.ld.add_subscriptions(name, doc, e["at"])
        else:
            self.ld.add_segment(e["key"].split("/")[0], name, e["at"])

    def _feed_pending(self):
        batch, self.pending = self.pending, []
        for e in batch:
            self._feed_entry(e)
            self._check_rss()

    # -- chain -----------------------------------------------------------------------------------------
    def _poll(self, sym, now):
        t0 = time.perf_counter()
        try:
            self.stats["db_rows"] += self.poller.poll(sym, now)
        except SourceError as exc:
            self._err("db", exc.category)
        self.stats["db_s"] += time.perf_counter() - t0
        self.stats["db_calls"] += 1
        for run_id, ts in self.poller.acc.pop_new_runs(sym):
            key = "%s/%s" % (sym, run_id)
            if key not in self.jkeys:
                self._journal_add("chain_run", key, None, "", ts, None, self.cur_t)

    def _chain_wait(self, T):
        t_T = self.epoch(T)
        deadline = t_T + self.cfg.wait_deadline_s
        lag = dict((s, None) for s in SYMBOLS)
        t0 = time.perf_counter()
        polls = 0
        while True:
            now = self.clock.now()
            for s in SYMBOLS:
                if lag[s] is None:
                    self._poll(s, now)
                    if self.poller.acc.has_slot(s, T):
                        lag[s] = now - t_T
            polls += 1
            if all(v is not None for v in lag.values()) or now + self.cfg.poll_s > deadline or polls >= 8 or self._stopped():
                break
            self.clock.sleep(self.cfg.poll_s)
        self.stats["chain_wait_s"] += time.perf_counter() - t0
        self.stats["lag"] = lag
        runs = self.poller.acc.runs()
        return dict((s, wall_source.wall_row(runs.get(s, []), self.day, _hm(T))) for s in SYMBOLS)

    # -- one cycle -------------------------------------------------------------------------------------
    def _new_stats(self):
        return {"errors": 0, "s3_list_s": 0.0, "s3_list_calls": 0, "s3_get_s": 0.0, "s3_gets": 0, "s3_bytes": 0, "db_s": 0.0,
                "db_calls": 0, "db_rows": 0, "chain_wait_s": 0.0, "lag": dict((s, None) for s in SYMBOLS),
                "missed": self._take_missed()}

    def _take_missed(self):
        n, self.missed_now = self.missed_now, 0
        return n

    def _cycle(self, T):
        self.cur_t = T
        t_wake = self.clock.now()
        self.last_lag = t_wake - self.epoch(T)
        self.stats = self._new_stats()
        w0, c0, k0 = time.perf_counter(), time.process_time(), _children_cpu()
        self._hook("before_cycle", T)
        self._hb("cycling")
        n_reb = len(self.ld.rebuilds)          # before intake + feed: a late segment rebuilds inside the feed
        self._intake(T)
        self._hook("after_journal", T)
        rb0 = time.perf_counter()              # feed + cycle(); this cycle's chain wait (stats reset per cycle) is subtracted
        self._feed_pending()
        if T >= GRID_FIRST and not any(e["kind"] == "subscriptions" for e in self.journal):
            self._hb("no_session")
            raise _Stop(0)
        walls = {}
        if GRID_FIRST <= T <= GRID_LAST:
            walls = self._chain_wait(T)
        n_late = len(self.ld.late)
        if T >= GRID_FIRST:
            d = self.ld.cycle(T, walls, as_of_utc(self.day, T))
            self._emit(_hhmm(T), d)
            self.last_t = T
        rebuild_s = time.perf_counter() - rb0 - self.stats["chain_wait_s"]
        self._check_rss()
        if T >= GRID_FIRST:
            self._write_state_files()
        self._save_state(T, False)
        self.last_cycle = _hm(T)
        self.last_wall = time.perf_counter() - w0
        self._metrics(T, t_wake, w0, c0, k0, len(self.ld.rebuilds) - n_reb, rebuild_s, len(self.ld.late) - n_late,
                      self.ld.last_reemit if T >= GRID_FIRST else 0)
        self._hb("waiting")
        self._hook("after_cycle", T)

    def _metrics(self, T, t_wake, w0, c0, k0, n_reb, rebuild_s, n_late, reemit):
        s = self.stats
        p = os.path.join(self.ddir, "live_metrics.csv")
        new = not os.path.exists(p)
        row = {"day": self.day, "T": _hm(T), "wake_utc": iso_utc(t_wake), "cycle_end_utc": iso_utc(self.clock.now()),
               "wall_s": "%.3f" % (time.perf_counter() - w0), "cpu_self_s": "%.3f" % (time.process_time() - c0),
               "cpu_children_s": "%.3f" % (_children_cpu() - k0), "peak_rss_mb": "%.1f" % self.peak_rss,
               "rss_mb": "%.1f" % self.rss, "s3_list_s": "%.3f" % s["s3_list_s"], "s3_list_calls": s["s3_list_calls"],
               "s3_get_s": "%.3f" % s["s3_get_s"], "s3_gets": s["s3_gets"], "s3_bytes": s["s3_bytes"],
               "db_s": "%.3f" % s["db_s"], "db_calls": s["db_calls"], "db_rows": s["db_rows"],
               "chain_wait_s": "%.3f" % s["chain_wait_s"],
               "ready_lag_s_NIFTY": "" if s["lag"]["NIFTY"] is None else "%.1f" % s["lag"]["NIFTY"],
               "ready_lag_s_SENSEX": "" if s["lag"]["SENSEX"] is None else "%.1f" % s["lag"]["SENSEX"],
               "rebuilds": n_reb, "rebuild_s": "%.3f" % rebuild_s, "reemit_rows": reemit, "late_segments": n_late, "missed_grid_points": s["missed"],
               "run_grew": self.poller.acc.row_changed, "errors": s["errors"]}
        with open(p, "a", encoding="utf-8", newline="") as fh:
            wr = csv.writer(fh, lineterminator="\n")
            if new:
                wr.writerow(METRIC_COLS)
            wr.writerow([row[c] for c in METRIC_COLS])

    # -- start, restart --------------------------------------------------------------------------------
    def _reader(self, sym, name):
        with gzip.open(os.path.join(self.rawdir, sym, self.day, name), "rb") as fh:
            for line in fh:
                yield line

    def _new_liveday(self):
        w = special.special_window(self.day, None)
        return writer.LiveDay(self.day, self._reader, (w["open"], w["close"]) if w else None, code_sha=self.cfg.code_sha)

    def _restore(self, st):
        """Rebuild the LiveDay as the previous process left it at its committed cycle. -> committed (or None)."""
        committed = st.get("committed") if st else None
        self._journal_load()
        objs = [e for e in self.journal if e["kind"] in ("segment", "subscriptions")]
        done = [e for e in objs if committed is not None and e["cycle"] <= committed]
        self.pending = [e for e in objs if committed is None or e["cycle"] > committed]
        if done:
            by_cycle = {}
            for e in done:
                by_cycle.setdefault(e["cycle"], []).append(e)
            for T in range(min(by_cycle), committed + 1, 5):
                for e in by_cycle.get(T, []):
                    self._feed_entry(e)
                if T >= GRID_FIRST and self.ld.dirty:
                    self.ld.rebuild_dirty()
        if committed is None:
            return None
        texts, db_texts = [], []
        if os.path.isdir(self.cdir):
            for n in sorted(os.listdir(self.cdir)):
                for rx, out in ((DELTA_NAME, texts), (DB_DELTA_NAME, db_texts)):
                    m = rx.match(n)
                    if m and int(m.group(1)[:2]) * 60 + int(m.group(1)[2:]) <= committed:
                        with open(os.path.join(self.cdir, n), encoding="utf-8", newline="") as fh:
                            out.append(fh.read())
        c_text, e_text = writer.apply_deltas(texts)
        limit = cycle.ts_of(self.day, committed)
        rows = {}
        for fname in ("tape_live_wall.csv", "tape_live_label.csv"):
            p = os.path.join(self.live, fname)
            rows[fname] = []
            if os.path.exists(p):
                with open(p, encoding="utf-8", newline="") as fh:
                    rows[fname] = [r for r in csv.DictReader(fh) if r["ts_ist"] <= limit]
        self.ld.restore(c_text, e_text, db_texts, rows["tape_live_wall.csv"], rows["tape_live_label.csv"], st)
        self.missed = list(st.get("missed", []))
        return committed

    def _first_grid_point(self, committed):
        now_m = max(0, int((self.clock.now() - self.t0) // 60))
        t_now = now_m - now_m % 5
        if self.pending:
            return min(e["cycle"] for e in self.pending)
        return t_now if committed is None else max(committed + 5, t_now)

    def _finalize(self):
        d = self.ld.cycle(None, {}, as_of_utc(self.day, self.last_t if self.last_t is not None else GRID_LAST))
        self._emit("final", d)
        self._write_state_files()
        outputs = {}
        for dp, _ds, ns in os.walk(self.live):
            for n in ns:
                rel = os.path.relpath(os.path.join(dp, n), self.live).replace(os.sep, "/")
                if rel != "run_manifest.json":
                    with open(os.path.join(dp, n), "rb") as fh:
                        outputs[rel] = _sha256(fh.read())
        counts = {}
        for r in self.ld.labels.values():
            c = counts.setdefault(r["symbol"], {})
            c[r["label"]] = c.get(r["label"], 0) + 1
            if r["label"] == "NO_READ":
                c["NO_READ: " + r["reason"]] = c.get("NO_READ: " + r["reason"], 0) + 1
        man = {"schema": "tape_live_runner_manifest_v1", "args": {"day": self.day}, "code": {"git_sha": self.cfg.code_sha},
               "epochs": self.ld.epochs(), "epoch_log": self.ld.epoch_log, "rule_version": rules.RULE_VERSION,
               "outputs": dict(sorted(outputs.items())), "rebuilds": self.ld.rebuilds, "late_segments": self.ld.late,
               "bad_files": self.ld.bad_files, "token_map_conflicts": self.ld.conflicts, "missed_grid_points": self.missed,
               "label_counts": dict((s, dict(sorted(v.items()))) for s, v in sorted(counts.items()))}
        _atomic(os.path.join(self.live, "run_manifest.json"), (json.dumps(man, indent=1, sort_keys=True) + "\n").encode("utf-8"))
        self._save_state(self.cfg.end_t, True)

    def _run(self):
        os.makedirs(self.ddir, exist_ok=True)
        os.makedirs(self.live, exist_ok=True)
        st = self._load_state()
        if st is not None and st.get("done"):
            self._hb("done")
            return 0
        if self._stopped():
            self._hb("killed")
            return 0
        if special.special_window(self.day, None) is not None:
            self._hb("special_session_unsupported")
            return 0
        self._check_disk(self.cfg.disk_floor_mb)
        self.ld = self._new_liveday()
        committed = self._restore(st)
        T0 = self._first_grid_point(committed)
        prev = GRID_FIRST - 5 if committed is None else committed
        gone = set(t for t in range(prev + 5, T0, 5) if t >= GRID_FIRST)
        self.missed = sorted(set(self.missed) | gone)
        self.missed_now = len(gone)
        self._hb("starting")
        for T in range(T0, self.cfg.end_t + 1, 5):
            if not self._sleep_until(self.epoch(T) + self.cfg.lag):
                self._hb("stopped" if self.cfg.term["hit"] else "killed")
                return 0
            self._check_disk(self.cfg.disk_stop_mb)
            self._hook("after_wake", T)
            self._cycle(T)
        self._finalize()
        self._hb("done")
        return 0

    def run(self):
        try:
            return self._run()
        except _Stop as s:
            return s.rc
        except MemoryError:
            self.last_error = "memory"
            self._hb("memory_error")
            return 3
        except Exception as exc:  # noqa: BLE001 - recorded by type and place only; the message is never kept
            tb = exc.__traceback__
            while tb is not None and tb.tb_next is not None:
                tb = tb.tb_next
            where = "%s:%d" % (os.path.basename(tb.tb_frame.f_code.co_filename), tb.tb_lineno) if tb is not None else "?"
            self.last_error = "%s at %s" % (type(exc).__name__, where)
            self._log("fatal " + self.last_error)
            self._hb("error")
            return 1


def _md5(b):
    import hashlib
    return hashlib.md5(b).hexdigest()


def _sha256(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()


def run_day(cfg, objs, chain, clock, hooks=None, rss_fn=None, redact=()):
    """Run (or resume) one day. -> exit code."""
    return Runner(cfg, objs, chain, clock, hooks, rss_fn, redact).run()
