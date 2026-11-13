"""Tape live writer W, replay-mode core (docs/tape/L0_plan.md sections 2 and 6; spec s2-s3).

PURE: stdlib only, no clock, no randomness, no file or network I/O. Segment lines come in through an injected
``reader(symbol, name) -> iterable of raw bytes lines``; the CLI (services/tape_live/cli.py) owns every file.

Processing (plan decision 1, option B with a rebuild path):
  * T1a is CARRIED: one merdian_compute.tape.replay.SymbolReplay per symbol, fed with exactly the call sequence of
    services/tape_offline/process_day.process_symbol (segments in order_segments order; end_group(previous HHMM) only when a
    new HHMM group starts; feed() per non-empty line; the same gzip error handling). replay.py is not changed.
  * The view at cycle T flushes a COPY (copy.deepcopy(rp).finish()), so the carried replay keeps its heap and watermark.
  * T1b is re-run on the day so far through the same CSV string round trip as cycle_day (minute.render_csv ->
    csv.DictReader -> cycle.build_cycle -> events.candidates); cycle rows are kept for T' <= T and events for ts_ist <= T.
  * REBUILD (the batch path, once) when a segment arrives that sorts before the last one fed for its symbol (a late segment
    or a collision variant of a closed group): that symbol, at once. Or when a new subscriptions file changes the token map:
    ruling R-F step one (docs/tape/L2_rebuild_scope_plan.md), ONLY the symbols whose own filtered map changed (the map
    SymbolReplay keeps, replay.py:171), at the start of the next cycle; a dirty symbol's segments are absorbed until then, so a
    symbol dirty from both triggers in one cycle is rebuilt once.
Outputs per cycle: upserts and deletes against the previously emitted state (so a provisional row or event that later
changes or disappears is corrected), the wall rows, and labels. Labels are insert-only, first label wins (spec s3).

Epochs (docs/tape/L2_live_runner_plan.md section 4, Phase B): live_run_id is a per-symbol REBUILD EPOCH,
epoch_id(day, symbol, code_sha, n). n starts at 0 and is bumped by every rebuild of that symbol (late_segment, subscriptions)
and, ruling Q-1, by a cycle whose delta would delete a row of that symbol without a rebuild (trigger "drop"). After a bump every
cycle, events and wall row of the symbol is re-sent under the new id, so "U lines only + the newest-run filter" equals "U and D
applied" at every cycle (newest_epoch_view). The DB-shaped deltas carry as_of = the grid time (UTC) of the cycle that last
changed the row's data or id. Labels are never filtered: their id is the epoch they were written in, provenance only. D lines
are file-only: no statement is ever built from them.
"""
import copy
import csv
import io
import json
import uuid
import zlib

from merdian_compute.tape import cycle, events, minute, replay
from services.tape_live import dbshape, rules

SYMBOLS = ("NIFTY", "SENSEX")
GRID_FIRST, GRID_LAST = cycle.FIRST_T, cycle.LAST_T
CYCLE_HEADER = ",".join(cycle.CYCLE_COLS)
EVENT_HEADER = ",".join(events.EVENT_COLS)
PROV = ("as_of", "live_run_id", "code_sha")
WALL_COLS = ("symbol", "trading_day", "expiry", "ts_ist", "chain_run_id", "chain_run_ts", "call_wall", "put_wall",
             "call_wall_oi_call", "put_wall_oi_put") + PROV
LABEL_COLS = ("symbol", "trading_day", "ts_ist", "wall", "rule_version", "strike", "leg", "label", "partial", "reason",
              "flags") + PROV


DB_DELTA = ("tape_live_cycle", "tape_live_events", "tape_live_wall")


def epoch_id(day, sym, code_sha, n):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "meridian-tape-live:%s:%s:%s:%d" % (day, sym, code_sha, n)))


def _nkey(table, trading_day, symbol):
    return (trading_day, symbol)


def newest_epoch_view(tables):
    """The newest-run filter (operator ruling R6-H; 2b and the page implement the same rule). tables: {table: (header, rows)}.
    Per (trading_day, symbol) the newest epoch is the live_run_id of the row with the latest as_of across tape_live_cycle,
    tape_live_events and tape_live_wall TAKEN TOGETHER (a bump re-sends every row of the symbol at the bump cycle, so the latest
    as_of carries the newest epoch even when one table has no row of it, e.g. every event vanished in the rebuild). Only rows
    with that id are kept, in all three tables. tape_live_label is never filtered. -> {table: rows}."""
    idx = dict((t, tuple(h.index(c) for c in ("trading_day", "symbol", "as_of", "live_run_id"))) for t, (h, _r) in tables.items())
    newest = {}
    for t in DB_DELTA:
        if t not in tables:
            continue
        i_d, i_s, i_a, i_r = idx[t]
        for r in tables[t][1]:
            k = _nkey(t, r[i_d], r[i_s])
            if k not in newest or r[i_a] > newest[k][0]:
                newest[k] = (r[i_a], r[i_r])
    out = {}
    for t, (_h, rows) in tables.items():
        if t == "tape_live_label":
            out[t] = list(rows)
            continue
        i_d, i_s, i_a, i_r = idx[t]
        out[t] = [r for r in rows if r[i_r] == newest[_nkey(t, r[i_d], r[i_s])][1]]
    return out


def _fields(text_line):
    return next(csv.reader([text_line]))


def _db_key(table, f):
    """f: full DB fields. The key the writer keeps per table (the L0 key; the PK / grain of the DDL for each table)."""
    if table == "tape_live_cycle":
        return (f[1], f[5], f[7])                 # symbol, instrument_token, ts_ist (+ trading_day, constant per run)
    if table == "tape_live_events":
        return tuple(f[1:8])                      # symbol, expiry, strike, leg, kind, ts_ist, side
    return (f[0], f[3])                           # wall: symbol, ts_ist (one front expiry per grid point)


def apply_db_deltas(texts):
    """DB-shaped delta files (cycles/*.db.csv), in cycle order -> {table: {key: full fields}} with D applied. File to memory
    only (restart); nothing here or anywhere builds a statement from a D line."""
    st = dict((t, {}) for t in DB_DELTA)
    by_header = dict((dbshape.header(t, delta=True), t) for t in DB_DELTA)
    for text in texts:
        rows = list(csv.reader(io.StringIO(text)))
        t = by_header[",".join(rows[0])]
        for r in rows[1:]:
            if r[0] == "U":
                st[t][_db_key(t, r[1:])] = r[1:]
            elif r[0] == "D":
                st[t].pop(_db_key(t, r[1:]), None)
    return st


def added_minutes(items):
    """[(subscriptions file name, parsed json)] -> {token: 'HH:MM'}: the first added_minute per token, files in
    replay.sub_sort_key order (the rule of services/tape_offline/cycle_day.read_added)."""
    added = {}
    for name, doc in sorted(items, key=lambda it: replay.sub_sort_key(it[0])):
        for row in doc.get("tokens", []):
            try:
                tok = int(row["token"])
            except (KeyError, TypeError, ValueError):
                continue
            if tok not in added and row.get("added_minute"):
                added[tok] = row["added_minute"]
    return added


def _ckey(line):
    f = line.split(",")
    return (f[0], f[4], f[6])                     # symbol, token, T (the instrument-token key)


def _ekey(line):
    return tuple(line.split(",", 7)[:7])          # symbol .. side; the detail JSON is the only quoted field and comes last


def _csort(line):
    f = line.split(",")
    return (f[0], f[1] or "", float(f[2] or 0.0), f[3], f[6])        # cycle.build_cycle's row order


def _esort(line):
    f = line.split(",", 7)
    return (f[0], f[1] or "", float(f[2] or 0.0), f[3], f[4], f[5], f[6])   # events.candidates' order


def _keyed(text, keyf):
    lines = text.split("\n")[1:]
    return {keyf(l): l for l in lines if l}


def render_state(state, header, sortf):
    return "\n".join([header] + sorted(state.values(), key=sortf)) + "\n"


def _delta(old, new, header):
    out = []
    for k, line in sorted(new.items()):
        if old.get(k) != line:
            out.append("U," + line)
    for k in sorted(set(old) - set(new)):
        out.append("D," + old[k])
    return ("op," + header + "\n" + "\n".join(out) + "\n") if out else None


def apply_deltas(texts):
    """Per-cycle delta files, in cycle order -> (cycle state text, events state text), rendered like the offline CSVs."""
    st = {CYCLE_HEADER: {}, EVENT_HEADER: {}}
    kf = {CYCLE_HEADER: _ckey, EVENT_HEADER: _ekey}
    for text in texts:
        lines = text.split("\n")
        header = lines[0][3:]
        s = st[header]
        for l in lines[1:]:
            if not l:
                continue
            op, line = l[0], l[2:]
            if op == "U":
                s[kf[header](line)] = line
            else:
                s.pop(kf[header](line), None)
    return render_state(st[CYCLE_HEADER], CYCLE_HEADER, _csort), render_state(st[EVENT_HEADER], EVENT_HEADER, _esort)


class LiveDay:
    def __init__(self, day, reader, win=None, code_sha=""):
        self.day, self.reader, self.win = day, reader, win
        self.code_sha = code_sha
        self.epoch = dict((s, 0) for s in SYMBOLS)
        self.epoch_log, self._bumped = [], set()
        self.db = dict((t, {}) for t in DB_DELTA)        # {table: {key: full DB fields}}: the emitted DB state
        self._parsed = dict((t, {}) for t in DB_DELTA[:2])
        self.last_reemit = 0
        self.subs, self.meta, self.conflicts, self.added = [], {}, [], {}
        self.known = {s: [] for s in SYMBOLS}
        self.rp, self.cur, self.last = {}, {}, {}
        self.dirty = {}                    # {symbol: why}: rebuilt at the start of the next cycle
        self.bad_files, self.rebuilds, self.late = [], [], []
        self.state_c, self.state_e = {}, {}
        self.labels, self.walls = {}, {}

    # -- intake ----------------------------------------------------------------------------------------
    def add_subscriptions(self, name, doc, at):
        self.subs.append((name, doc))
        meta, self.conflicts = replay.build_token_map(self.subs)
        self.added = added_minutes(self.subs)
        if meta != self.meta:
            old, self.meta = self.meta, meta
            for sym in SYMBOLS:
                if sym in self.rp and self._filtered(meta, sym) != self._filtered(old, sym):
                    self.dirty[sym] = {"trigger": "subscriptions", "at": at, "file": name}

    def _filtered(self, meta, sym):
        """The token map a replay of sym keeps: read off SymbolReplay itself (replay.py:171), never a second copy of the filter.
        Equal filtered maps <=> a rebuild would give an identical replay (strikes and sidx derive from it)."""
        return replay.SymbolReplay(sym, self.day, meta, self.win).meta

    def add_segment(self, sym, name, at):
        """at: the cycle minute at which the segment became available."""
        key = replay.parse_seg_name(name)
        if key is None or name in self.known[sym]:
            return
        hhmm_min = int(key[0][:2]) * 60 + int(key[0][2:])
        if at > hhmm_min + 5:
            self.late.append({"symbol": sym, "segment": name, "hhmm": "%s:%s" % (key[0][:2], key[0][2:]), "arrived": at})
        self.known[sym].append(name)
        if sym in self.dirty:
            return
        if sym in self.last and (key, name) < self.last[sym]:
            self._rebuild_sym(sym, {"trigger": "late_segment", "at": at, "file": "%s/%s" % (sym, name)})
            return
        self._feed(sym, name)

    def _new_replay(self, sym):
        return replay.SymbolReplay(sym, self.day, self.meta, self.win)

    def _feed(self, sym, name):
        if sym not in self.rp:
            self.rp[sym] = self._new_replay(sym)
        hhmm = replay.parse_seg_name(name)[0]
        if self.cur.get(sym) is not None and hhmm != self.cur[sym]:
            self.rp[sym].end_group(self.cur[sym])
        self.cur[sym] = hhmm
        self.last[sym] = (replay.parse_seg_name(name), name)
        rp = self.rp[sym]
        try:
            for raw in self.reader(sym, name):
                raw = raw.rstrip(b"\r\n")
                if not raw:
                    continue
                rp.feed(raw)
        except (EOFError, OSError, zlib.error) as exc:
            self.bad_files.append({"file": "%s/%s" % (sym, name), "error": type(exc).__name__})

    # -- epochs --------------------------------------------------------------------------------------
    def live_run_id(self, sym):
        return epoch_id(self.day, sym, self.code_sha, self.epoch[sym])

    def epochs(self):
        return dict((s, [epoch_id(self.day, s, self.code_sha, n) for n in range(self.epoch[s] + 1)]) for s in SYMBOLS)

    def _bump(self, sym, trigger, at):
        self.epoch[sym] += 1
        self._bumped.add(sym)
        self.epoch_log.append({"symbol": sym, "trigger": trigger, "at": at, "n": self.epoch[sym], "id": self.live_run_id(sym),
                               "reemit_rows": 0})

    def _rebuild_sym(self, sym, why):
        self.rebuilds.append(dict(why, symbol=sym))
        self._bump(sym, why["trigger"], why["at"])
        self.rp.pop(sym, None)
        self.cur.pop(sym, None)
        self.last.pop(sym, None)
        self.bad_files = [b for b in self.bad_files if not b["file"].startswith(sym + "/")]
        for name in replay.order_segments(self.known[sym]):
            self._feed(sym, name)

    def _rebuild_dirty(self):
        dirty, self.dirty = self.dirty, {}
        for sym in SYMBOLS:
            if sym in dirty:
                self._rebuild_sym(sym, dirty[sym])

    def rebuild_dirty(self):
        """Public: rebuild the symbols whose token map changed (the start of a cycle; restart catch-up)."""
        self._rebuild_dirty()

    # -- restart ---------------------------------------------------------------------------------------
    def restore(self, c_text, e_text, db_texts, wall_rows, label_rows, st):
        """Put back the state emitted up to the committed cycle: L0 state texts, DB delta texts (cycles/*.db.csv in order),
        wall and label rows (the files), and the counters of state.json. Rebuilds and bumps during catch-up are recovery: the
        epochs, rebuilds, late and bad_files of the committed state replace them."""
        self.state_c, self.state_e = _keyed(c_text, _ckey), _keyed(e_text, _ekey)
        self.db = apply_db_deltas(db_texts)
        self._parsed = dict((t, {}) for t in DB_DELTA[:2])
        for r in wall_rows:
            self.walls[(r["symbol"], r["ts_ist"])] = r
        self.load_labels(label_rows)
        self.rebuilds, self.late, self.bad_files = st["rebuilds"], st["late"], st["bad_files"]
        self.epoch = dict((s, int(st["epoch"][s])) for s in SYMBOLS)
        self.epoch_log, self._bumped = st["epoch_log"], set()

    # -- labels ----------------------------------------------------------------------------------------
    def load_labels(self, rows):
        for r in rows:
            self._insert_label((r["symbol"], r["trading_day"], r["ts_ist"], r["wall"], r["rule_version"]), r)

    def _insert_label(self, key, row):
        if key in self.labels:
            return
        self.labels[key] = row

    # -- one cycle -------------------------------------------------------------------------------------
    def cycle(self, tm, walls, as_of):
        """tm: grid minute of this cycle (labels only for GRID_FIRST <= tm <= GRID_LAST), or None for the final cycle (no
        truncation, no labels). walls: {symbol: wall row or None} from wall_source. Returns the two delta texts (or None)."""
        if self.dirty:
            self._rebuild_dirty()
        rows = []
        for sym in SYMBOLS:
            if sym in self.rp:
                rows += copy.deepcopy(self.rp[sym]).finish()["rows"]
        res = cycle.build_cycle(csv.DictReader(io.StringIO(minute.render_csv(rows))), self.added)
        crow, ev = res["rows"], events.candidates(res["tokens"])
        T = None
        if tm is not None:
            T = cycle.ts_of(self.day, tm)
            crow = [r for r in crow if r["T"] <= T]
            ev = [e for e in ev if e[5] <= T]
        c_text, e_text = cycle.render_cycle_csv(crow), events.render_events_csv(ev)
        new_c, new_e = _keyed(c_text, _ckey), _keyed(e_text, _ekey)
        for sym in SYMBOLS:                       # ruling Q-1: a deletion without a rebuild bumps the symbol's epoch
            if sym in self._bumped:
                continue
            if any(k[0] == sym and k not in new_c for k in self.state_c) or \
                    any(k[0] == sym and k not in new_e for k in self.state_e):
                self._bump(sym, "drop", tm if tm is not None else "final")
        out = {"cycle": _delta(self.state_c, new_c, CYCLE_HEADER), "events": _delta(self.state_e, new_e, EVENT_HEADER)}
        self.state_c, self.state_e = new_c, new_e
        if T is not None and GRID_FIRST <= tm <= GRID_LAST:
            self._label(T, walls, c_text, e_text, as_of)
        out["db"] = self._db_cycle(as_of)
        self._bumped = set()
        return out

    def _db_rows(self, table, state):
        cache, rows = self._parsed[table], {}
        for line in state.values():
            data = cache.get(line)
            if data is None:
                data = cache[line] = dbshape.data_row(table, self.day, _fields(line))
            rows[_db_key(table, data + ["", "", ""])] = data
        if len(cache) > 2 * len(state) + 1000:            # drop the parse cache of lines no longer in the state
            live = set(state.values())
            for line in [l for l in cache if l not in live]:
                del cache[line]
        return rows

    def _db_cycle(self, as_of):
        """The DB-shaped delta of this cycle per table (text or None); updates self.db and the re-emit counters."""
        new = {"tape_live_cycle": self._db_rows("tape_live_cycle", self.state_c),
               "tape_live_events": self._db_rows("tape_live_events", self.state_e),
               "tape_live_wall": dict(((r["symbol"], r["ts_ist"]), dbshape.dict_row("tape_live_wall", self.day, r))
                                      for r in self.walls.values())}
        out, reemit = {}, dict((s, 0) for s in SYMBOLS)
        for t in DB_DELTA:
            old, cur, lines = self.db[t], {}, []
            for k in sorted(new[t]):
                data = new[t][k]
                rid = self.live_run_id(data[1] if t != "tape_live_wall" else data[0])
                prev = old.get(k)
                if prev is not None and prev[:-3] == data and prev[-2] == rid:
                    cur[k] = prev
                    continue
                if prev is not None and prev[:-3] == data:
                    reemit[data[1] if t != "tape_live_wall" else data[0]] += 1
                cur[k] = dbshape.full(data, as_of, rid, self.code_sha)
                lines.append("U," + dbshape.line(cur[k]))
            for k in sorted(set(old) - set(cur)):
                lines.append("D," + dbshape.line(old[k]))
            self.db[t] = cur
            out[t] = (dbshape.header(t, delta=True) + "\n" + "\n".join(lines) + "\n") if lines else None
        for k, f in self.db["tape_live_wall"].items():
            self.walls[k] = dict(zip(WALL_COLS, f))
        for e in self.epoch_log:
            if e["symbol"] in self._bumped and e["n"] == self.epoch[e["symbol"]]:
                e["reemit_rows"] += reemit[e["symbol"]]
        self.last_reemit = sum(reemit.values())
        return out

    def _label(self, T, walls, c_text, e_text, as_of):
        by_c, by_e = {}, {}
        for r in csv.DictReader(io.StringIO(c_text)):
            by_c.setdefault(r["symbol"], []).append(r)
        for r in csv.DictReader(io.StringIO(e_text)):
            by_e.setdefault(r["symbol"], []).append(r)
        for sym in SYMBOLS:
            if not self.known[sym]:
                continue
            prov = {"as_of": as_of, "live_run_id": self.live_run_id(sym), "code_sha": self.code_sha}
            w = walls.get(sym)
            if w is not None:
                self.walls[(sym, T)] = dict(w, **prov)
            for wall in ("call", "put"):
                f = rules.derive_flags(by_c.get(sym, []), by_e.get(sym, []), w, T, wall)
                label, partial, reason = rules.label_wall(f)
                key = (sym, self.day, T, wall, rules.RULE_VERSION)
                self._insert_label(key, dict({
                    "symbol": sym, "trading_day": self.day, "ts_ist": T, "wall": wall, "rule_version": rules.RULE_VERSION,
                    "strike": "" if w is None else w[rules.WALL_COL[wall]], "leg": rules.LEG[wall], "label": label,
                    "partial": "true" if partial else "false", "reason": reason,
                    "flags": json.dumps(f, sort_keys=True, separators=(",", ":"))}, **prov))

    # -- final state -----------------------------------------------------------------------------------
    def state_cycle_csv(self):
        return render_state(self.state_c, CYCLE_HEADER, _csort)

    def state_events_csv(self):
        return render_state(self.state_e, EVENT_HEADER, _esort)

    def db_state_csv(self, table):
        """The DB-shaped state of one table (header = the DDL columns), rows in key order."""
        if table == "tape_live_label":
            rows = [dbshape.full(dbshape.dict_row(table, self.day, self.labels[k]), *[self.labels[k][c] for c in PROV])
                    for k in sorted(self.labels)]
        else:
            rows = [self.db[table][k] for k in sorted(self.db[table])]
        return "\n".join([dbshape.header(table)] + [dbshape.line(r) for r in rows]) + "\n"
