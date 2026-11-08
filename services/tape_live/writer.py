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
"""
import copy
import csv
import io
import json
import zlib

from merdian_compute.tape import cycle, events, minute, replay
from services.tape_live import rules

SYMBOLS = ("NIFTY", "SENSEX")
GRID_FIRST, GRID_LAST = cycle.FIRST_T, cycle.LAST_T
CYCLE_HEADER = ",".join(cycle.CYCLE_COLS)
EVENT_HEADER = ",".join(events.EVENT_COLS)
PROV = ("as_of", "live_run_id", "code_sha")
WALL_COLS = ("symbol", "trading_day", "expiry", "ts_ist", "chain_run_id", "chain_run_ts", "call_wall", "put_wall",
             "call_wall_oi_call", "put_wall_oi_put") + PROV
LABEL_COLS = ("symbol", "trading_day", "ts_ist", "wall", "rule_version", "strike", "leg", "label", "partial", "reason",
              "flags") + PROV


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
    def __init__(self, day, reader, win=None, live_run_id="", code_sha=""):
        self.day, self.reader, self.win = day, reader, win
        self.live_run_id, self.code_sha = live_run_id, code_sha
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

    def _rebuild_sym(self, sym, why):
        self.rebuilds.append(dict(why, symbol=sym))
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
        out = {"cycle": _delta(self.state_c, new_c, CYCLE_HEADER), "events": _delta(self.state_e, new_e, EVENT_HEADER)}
        self.state_c, self.state_e = new_c, new_e
        if T is not None and GRID_FIRST <= tm <= GRID_LAST:
            self._label(T, walls, c_text, e_text, as_of)
        return out

    def _label(self, T, walls, c_text, e_text, as_of):
        by_c, by_e = {}, {}
        for r in csv.DictReader(io.StringIO(c_text)):
            by_c.setdefault(r["symbol"], []).append(r)
        for r in csv.DictReader(io.StringIO(e_text)):
            by_e.setdefault(r["symbol"], []).append(r)
        prov = {"as_of": as_of, "live_run_id": self.live_run_id, "code_sha": self.code_sha}
        for sym in SYMBOLS:
            if not self.known[sym]:
                continue
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
