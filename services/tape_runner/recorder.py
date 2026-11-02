"""The tape recorder: a timeline state machine evaluated at ``now`` (plan §3).

``step(now_ns)`` runs every due action and returns None (keep going) or an exit code. A restart at
11:00 therefore runs profile, resolve, connect and options at once and records from there. Ticker
callbacks (twisted thread in production, called directly in tests) share one lock with ``step``.

Kite calls made here: profile, instruments, ltp, quote, and the ticker. Nothing else.
"""
import json
import os
import re
import threading

from . import clock as clk
from . import config
from . import session
from .instruments import resolve
from .segments import SegmentWriter, spool_bytes
from .serialize import ctl_record, jsonable, packet_record, skew_seconds
from .stats import DayStats
from .uploader import Uploader

_SECRET_QS = re.compile(r"(access_token|api_key|enctoken)=[^&\s]*")


def _atomic_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, separators=(",", ":"), default=str)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _rest_ist_day(v):
    """Kite REST timestamps arrive as naive IST datetimes (quote); render the IST date."""
    if v is None:
        return None
    if hasattr(v, "tzinfo"):
        if v.tzinfo is not None:
            v = v.astimezone(clk.IST)
        return v.strftime("%Y-%m-%d")
    s = str(v)
    return s[:10] if len(s) >= 10 else None


class Recorder:
    def __init__(self, kite, ticker_factory, s3, clock, root=None, bucket=None, spool_cap=None,
                 threaded=False, secrets=(), log=None, symbols=None):
        self.kite = kite
        self.ticker_factory = ticker_factory
        self.clock = clock
        self.root = root or config.ROOT
        self.bucket = bucket or config.BUCKET
        self.spool_cap = config.SPOOL_CAP_BYTES if spool_cap is None else spool_cap
        self.threaded = threaded
        self.secrets = [s for s in secrets if s]
        self._log = log or (lambda msg: print("TAPE " + msg, flush=True))
        self.symbol_cfg = symbols or config.SYMBOLS
        self.symbols = list(self.symbol_cfg)

        self.start_ns = clock.now_ns()
        self.day = clk.ist_date(self.start_ns)
        self.win = session.window(self.day, log=self.log)      # today's timeline (special_sessions.json overrides)
        self._open_ns = clk.ist_ns(self.day, self.win["session_start"])
        self._close_ns = clk.ist_ns(self.day, self.win["session_end"])
        self.last_frame_ns = None        # any websocket frame, tick packet or 1-byte heartbeat (silence watchdog)
        self.frames_hb = 0
        self.frames_other = 0
        self._wd_step = 0
        self._wd_next_ns = 0
        self.pid = os.getpid()
        self.spool = os.path.join(self.root, "spool")
        self.state_dir = os.path.join(self.root, "state")
        self.manifest_dir = os.path.join(self.root, "manifest")
        for d in (self.spool, self.state_dir, self.manifest_dir):
            os.makedirs(d, exist_ok=True)
        self.heartbeat_path = os.path.join(self.root, "heartbeat.json")
        self.state_path = os.path.join(self.state_dir, self.day + ".json")

        self.lock = threading.RLock()
        self.uploader = Uploader(s3, self.bucket, self.spool, self.manifest_dir, log=self.log)
        self._spool_bytes = 0
        self.writer = SegmentWriter(self.spool, self.symbols, on_closed=self.uploader.enqueue,
                                    process_start_ns=self.start_ns, on_bytes=self._add_bytes,
                                    taken=self.uploader.is_taken)

        self.state = "WAITING"
        self.profiled = False
        self.universe = None
        self.ticker = None
        self.connected = False
        self.ever_connected = False
        self.fatal = None
        self.next_resolve_ns = 0
        self.last_idx_price = {}
        self.witness = {}
        self.band = {}
        self._last_minute = None
        self._subs_dirty = False
        self._subs_names = set()
        self._up_stop = threading.Event()
        self._up_thread = None
        self.stopping = False
        self.disconnected_since = None
        self.next_token_probe_ns = 0
        self.term_requested = False
        self.term_deadline_ns = None
        self._first_step = True
        self.connected_since = None

        self.subscribed = {}
        self.centre = {}
        self.options_on = False
        self.closed_checked = False
        self.report_written = False
        self.had_state = False
        self._upload_base = {}
        self.stats = DayStats(self.day, self.symbols)
        self._load_state()

        for path in self.writer.recover(self.start_ns):
            self.uploader.enqueue(path)
        self._spool_bytes = spool_bytes(self.spool)
        self.stats.note_spool(self._spool_bytes)
        if threaded:
            self._up_thread = threading.Thread(target=self.uploader.run, args=(clock, self._up_stop),
                                               name="tape-uploader", daemon=True)
            self._up_thread.start()

    # ------------------------------------------------------------------ utilities
    def log(self, msg):
        self._log(self._clean(msg))

    def _clean(self, s):
        s = str(s)
        for sec in self.secrets:
            s = s.replace(sec, "***")
        return _SECRET_QS.sub(r"\1=***", s)[:300]

    def _add_bytes(self, n):
        self._spool_bytes += n

    def _ctl_all(self, ctl, now, **detail):
        if self.stopping:
            return
        self.writer.write_all(ctl_record(ctl, now, **detail), now)

    # ------------------------------------------------------------------ state file
    def _load_state(self):
        if not os.path.exists(self.state_path):
            return
        with open(self.state_path, encoding="utf-8") as fh:
            st = json.load(fh)
        self.had_state = True
        self.stats = DayStats.from_dict(st["stats"])
        self.subscribed = {int(k): v for k, v in st.get("subs", {}).items()}
        self.centre = st.get("centre", {})
        self.options_on = st.get("options_on", False)
        self.closed_checked = st.get("closed_checked", False)
        self.report_written = st.get("report_written", False)
        self._upload_base = st.get("uploads_total", {})
        self.stats.restarts.append({"process_start_ist": clk.ist_iso(self.start_ns), "pid": self.pid,
                                    "prev_pid": st.get("pid"), "prev_state": st.get("last_state"),
                                    "prev_process_start_ist": st.get("process_start_ist")})

    def uploads_total(self):
        out = {}
        for src in (self._upload_base, self.uploader.counts):
            for k, c in src.items():
                t = out.setdefault(k, {"ok": 0, "retried": 0, "failed_attempts": 0})
                for f in t:
                    t[f] += c.get(f, 0)
        return out

    def _save_state(self):
        _atomic_json(self.state_path, {
            "stats": self.stats.to_dict(), "subs": {str(k): v for k, v in self.subscribed.items()},
            "centre": self.centre, "options_on": self.options_on, "closed_checked": self.closed_checked,
            "report_written": self.report_written, "uploads_total": self.uploads_total(),
            "last_state": self.state, "pid": self.pid, "process_start_ist": clk.ist_iso(self.start_ns)})

    def _heartbeat(self, now):
        hb = {
            "ts_ist": clk.ist_iso(now), "state": self.state, "pid": self.pid,
            "process_start_ist": clk.ist_iso(self.start_ns), "connected": self.connected,
            "packets_last_min": {}, "last_packet_ist": {},
            "n_subscribed": len(self.subscribed), "spool_bytes": self._spool_bytes,
            "upload_queue": len(self.uploader.pending()), "uploads": self.uploads_total(),
            "watchdog_trips": self.stats.watchdog_trips, "watchdog_errors": self.stats.watchdog_errors,
            "last_frame_age_s": None if self.last_frame_ns is None else round((now - self.last_frame_ns) / clk.NS, 1),
            "frames_hb": self.frames_hb, "frames_other": self.frames_other,
        }
        prev_min = clk.ist_hm(now - 60 * clk.NS)
        for s in self.symbols:
            hb["packets_last_min"][s] = self.stats.ppm[s].get(prev_min, {}).get("ALL", 0)
            ln = self.stats.last_ns[s]
            hb["last_packet_ist"][s] = clk.ist_iso(ln) if ln else None
        _atomic_json(self.heartbeat_path, hb)
        self._log("HB " + json.dumps({k: hb[k] for k in ("ts_ist", "state", "connected", "packets_last_min",
                                                         "n_subscribed", "spool_bytes", "upload_queue")},
                                     separators=(",", ":")))

    # ------------------------------------------------------------------ timeline
    def request_stop(self, *_):
        """SIGTERM handler body: only sets a flag (signal-safe); step() does the work."""
        self.term_requested = True

    def step(self, now):
        if self.term_requested:
            return self._terminate(now)
        if self.fatal:
            return self._fail(now, self.fatal)
        if self.stats.closed or self.report_written or clk.at(now, self.win["stop"]):
            return self._stop(now)
        if self._first_step:
            self._first_step = False
            if not clk.at(now, self.win["start"]):
                return self._early_exit(now)
        if not self.profiled:
            try:
                self.kite.profile()
            except Exception as exc:  # noqa: BLE001 -- the type only; a message could echo a token
                self.state = "TOKEN_FAIL"
                self.log("TOKEN_FAIL %s" % type(exc).__name__)
                self._heartbeat(now)
                self._save_state()
                return config.EXIT_TOKEN_FAIL
            self.profiled = True
        if self.universe is None and clk.at(now, self.win["resolve"]) and now >= self.next_resolve_ns:
            try:
                self.universe = resolve(self.kite, clk.ist_dt(now).date(), log=self.log, symbols=self.symbol_cfg)
            except Exception as exc:  # noqa: BLE001
                self.log("RESOLVE_FAIL %s" % type(exc).__name__)
                if clk.at(now, self.win["resolve_giveup"]):
                    self.state = "RESOLVE_FAIL"
                    self._heartbeat(now)
                    return config.EXIT_FAIL
                self.next_resolve_ns = now + config.RESOLVE_RETRY_S * clk.NS
        if self.universe is not None and self.ticker is None:
            self._start_ticker(now)
        if self._token_probe_due(now):
            code = self._token_probe(now)      # REST call made WITHOUT the recorder lock
            if code is not None:
                return code
        with self.lock:
            if (self.universe is not None and not self.options_on and self.connected
                    and clk.at(now, self.win["options"]) and self._witness_today()):
                self._open_options(now, "open_window")
            if (self.win["special"] and self.universe is not None and not self.options_on and self.connected
                    and now >= self._open_ns):
                # a special session may open with nothing dated today on the feed yet: do not lose its first minutes
                self._open_options(now, "special_open_forced")
            if (self.universe is not None and not self.closed_checked and clk.at(now, self.win["closed_check"])
                    and self._feed_settled(now)):
                code = self._closed_check(now)
                if code is not None:
                    return code
            minute = clk.ist_hm(now)
            if minute != self._last_minute:
                self._last_minute = minute
                self._minute(now)
            self._watchdog(now)
            self.writer.tick(now)
            self.writer.flush()
            self._flush_subs(now)
            if self._over_cap():
                return self._cap(now)
        if not self.threaded:
            self.uploader.process_once(now)
        return None

    def _start_ticker(self, now):
        self.disconnected_since = now
        t = self.ticker_factory()
        t.on_ticks = self.on_ticks
        t.on_connect = self.on_connect
        t.on_close = self.on_close
        t.on_error = self.on_error
        t.on_reconnect = self.on_reconnect
        t.on_noreconnect = self.on_noreconnect
        t.on_message = self.on_frame
        self.ticker = t
        t.connect(threaded=True)
        self.log("TICKER_CONNECTING")

    # ------------------------------------------------------------------ mid-session token (finding 3)
    def _token_probe_due(self, now):
        since = self.disconnected_since
        return (self.ticker is not None and not self.connected and since is not None
                and now - since > config.TOKEN_PROBE_AFTER_S * clk.NS and now >= self.next_token_probe_ns)

    def _token_probe(self, now):
        self.next_token_probe_ns = now + config.TOKEN_PROBE_EVERY_S * clk.NS
        try:
            self.kite.profile()
        except Exception as exc:  # noqa: BLE001 -- the type only
            name = type(exc).__name__
            if name in config.TOKEN_EXCEPTIONS:
                return self._token_dead(now, name)
            self.log("TOKEN_PROBE_INCONCLUSIVE %s (not a token error; still retrying)" % name)
            return None
        self.log("TOKEN_PROBE_OK (disconnected %ds; the ticker keeps reconnecting)"
                 % ((now - self.disconnected_since) // clk.NS))
        return None

    def _token_dead(self, now, name):
        """Token rejected mid-session: close segments, drain uploads (<= 60 s), heartbeat
        TOKEN_FAIL, exit 1 so systemd restarts the unit and re-reads /etc/tape/kite_token.env.
        The restart's own profile() exits 78 if the token is still bad."""
        self.log("TOKEN_FAIL_MIDSESSION %s" % name)
        if self.ticker is not None:
            try:
                self.ticker.close()
            except Exception:  # noqa: BLE001
                pass
        if self._up_thread is not None:
            self._up_stop.set()
            self._up_thread.join(timeout=120)
            self._up_thread = None
        with self.lock:
            self._ctl_all("error", now, code="TOKEN_FAIL", reason=name)
            self.stopping = True
            self.connected = False
            self.writer.close_all()
        self._drain(self.clock.now_ns() + config.TOKEN_FAIL_DRAIN_S * clk.NS)
        self.state = "TOKEN_FAIL"
        self._heartbeat(self.clock.now_ns())
        self._save_state()
        return config.EXIT_FAIL

    def _terminate(self, now):
        """SIGTERM (systemctl stop, shutdown): close segments, drain uploads <= 60 s, exit 0.
        No daily report: a later start the same day resumes the day from the state file."""
        self.log("SIGTERM -- closing segments, draining uploads (<= %ds)" % config.TERM_DRAIN_S)
        if self.ticker is not None:
            try:
                self.ticker.close()
            except Exception:  # noqa: BLE001
                pass
        if self._up_thread is not None:
            self._up_stop.set()
            self._up_thread.join(timeout=30)
            self._up_thread = None
        with self.lock:
            self._ctl_all("error", now, code="SIGTERM", reason="stop requested")
            self.stopping = True
            self.connected = False
            self.writer.close_all()
        self._drain(self.clock.now_ns() + config.TERM_DRAIN_S * clk.NS)
        left = self.uploader.pending()
        self.state = "STOPPED"
        self._heartbeat(self.clock.now_ns())
        self._save_state()
        self.log("STOP state=STOPPED uploads_left=%d" % len(left))
        return config.EXIT_OK

    def _early_exit(self, now):
        """Started before 08:50 IST (OnBootSec after a night-time boot): nothing is due, and this
        process's environment (token) was read too early to trust for the session. Ship any
        spool leftovers (<= 60 s), touch nothing at Kite, exit 0; the 08:50 timer starts a fresh
        process that reads /etc/tape/kite_token.env again."""
        self.log("EARLY_START before %s IST -- nothing due; the timer starts the session" % self.win["start"])
        self._drain(now + config.TERM_DRAIN_S * clk.NS)
        self.state = "EARLY_EXIT"
        self._heartbeat(self.clock.now_ns())
        return config.EXIT_OK

    def _over_cap(self):
        if self._spool_bytes <= self.spool_cap:
            return False
        self._spool_bytes = spool_bytes(self.spool)
        self.stats.note_spool(self._spool_bytes)
        return self._spool_bytes > self.spool_cap

    def _cap(self, now):
        self.log("SPOOL_CAP bytes=%d cap=%d" % (self._spool_bytes, self.spool_cap))
        try:
            self._ctl_all("error", now, code="SPOOL_CAP", reason="spool %d > cap %d" % (self._spool_bytes, self.spool_cap))
        finally:
            self.writer.abort_close()
        self.state = "SPOOL_CAP"
        self._heartbeat(now)
        self._save_state()
        return config.EXIT_SPOOL_CAP

    def _fail(self, now, reason):
        self.log("FATAL %s" % reason)
        with self.lock:
            try:
                self._ctl_all("error", now, code="FATAL", reason=self._clean(reason))
                self.writer.flush()
            except Exception:  # noqa: BLE001
                pass
        self.state = "FAILED"
        self._heartbeat(now)
        self._save_state()
        return config.EXIT_FAIL

    # ------------------------------------------------------------------ subscriptions
    def _subscribe(self, sym, insts, reason, now, centre=None, atm=None):
        new = [i for i in insts if i.token not in self.subscribed]
        if not new:
            return []
        minute = clk.ist_hm(now)
        for i in new:
            m = i.meta()
            m.update({"added_minute": minute, "reason": reason})
            self.subscribed[i.token] = m
        toks = [i.token for i in new]
        if self.connected and self.ticker is not None:
            try:
                self.ticker.subscribe(toks)
                self.ticker.set_mode(self.ticker.MODE_FULL, toks)
            except Exception as exc:  # noqa: BLE001 -- on_connect re-sends the full set
                self.log("SUBSCRIBE_SEND_FAIL %s" % type(exc).__name__)
        self.writer.write(sym, ctl_record("subscribe", now, tokens=toks, reason=reason,
                                          centre_strike=centre, atm_strike=atm), now)
        self.stats.note_subscribed(sym, minute, sum(1 for v in self.subscribed.values() if v["sym"] == sym))
        self._subs_dirty = True
        self.log("SUBSCRIBE sym=%s reason=%s added=%d total=%d" % (sym, reason, len(toks), len(self.subscribed)))
        return toks

    def _flush_subs(self, now):
        if not self._subs_dirty:
            return
        self._subs_dirty = False
        d = os.path.join(self.spool, "session", self.day)
        os.makedirs(d, exist_ok=True)
        base = "subscriptions_" + clk.ist_dt(now).strftime("%H%M%S")
        name, n = base, 1
        while name in self._subs_names or os.path.exists(os.path.join(d, name + ".json")):
            n += 1
            name = "%s_%d" % (base, n)
        self._subs_names.add(name)
        path = os.path.join(d, name + ".json")
        rows = sorted(self.subscribed.values(),
                      key=lambda m: (m["sym"], m["role"], m["strike"] or 0, m["opt_type"] or ""))
        _atomic_json(path, {"day": self.day, "written_ist": clk.ist_iso(now), "n": len(rows), "tokens": rows})
        self.uploader.enqueue(path)

    def _price_for(self, sym):
        su = self.universe.symbols[sym]
        try:
            q = self.kite.ltp([self.symbol_cfg[sym]["ltp_key"]])
            return float(q[self.symbol_cfg[sym]["ltp_key"]]["last_price"])
        except Exception as exc:  # noqa: BLE001
            self.log("LTP_FAIL %s (using last index packet)" % type(exc).__name__)
        p = self.last_idx_price.get(sym)
        return p if p is not None else su.index_ltp

    def _open_options(self, now, reason):
        for sym, su in self.universe.symbols.items():
            price = self._price_for(sym)
            pos = su.atm_pos(price)
            if pos is None:
                continue
            self.centre[sym] = su.strikes[pos]
            self.band[sym] = su.band_tokens(pos, config.ATM_BAND)
            self._subscribe(sym, su.window_tokens(pos), reason, now, centre=su.strikes[pos], atm=su.strikes[pos])
        self.options_on = True
        self.state = "RECORDING"
        self._flush_subs(now)

    def _grow(self, now):
        for sym, su in self.universe.symbols.items():
            price = self.last_idx_price.get(sym)
            pos = su.atm_pos(price)
            if pos is None:
                continue
            self.band[sym] = su.band_tokens(pos, config.ATM_BAND)
            if not self.options_on or sym not in self.centre:
                continue
            cpos = su.strikes.index(self.centre[sym]) if self.centre[sym] in su.strikes else pos
            if abs(pos - cpos) > config.GROW_THRESHOLD:
                self.centre[sym] = su.strikes[pos]
                self._subscribe(sym, su.window_tokens(pos), "grow", now, centre=su.strikes[pos], atm=su.strikes[pos])

    def _minute(self, now):
        if self.universe is not None:
            self._grow(now)
        self._spool_bytes = spool_bytes(self.spool)
        self.stats.note_spool(self._spool_bytes)
        self._heartbeat(now)
        self._save_state()

    # ------------------------------------------------------------------ closed day (plan D-4)
    def _feed_settled(self, now):
        """The closed check needs witnesses: only once the feed has been connected for
        CLOSED_CHECK_SETTLE_S (a start after 09:20 -- boot, restart, install -- must not judge
        an empty witness set; unchanged for the normal 08:55 connect)."""
        return (self.connected and self.connected_since is not None
                and now - self.connected_since >= config.CLOSED_CHECK_SETTLE_S * clk.NS)

    def _witness_today(self):
        return any(d == self.day for d in self.witness.values())

    def _closed_verdict(self, now):
        """CLOSED only on positive, two-source evidence (review 2026-11-01, item 4):
        1. no witness dated today (any today-dated index/future packet -> OPEN);
        2. for EVERY symbol both the index AND the future witness are present and stale -- a
           subscribe-time snapshot of one instrument is not enough;
        3. the REST quote independently confirms every index's last timestamp is stale -- a websocket
           that delivered the 08:55 snapshots and then stalled cannot close a trading day.
        Anything short of that is UNKNOWN: keep recording (absence is not a verdict). The check runs
        at the window's closed_check time (09:20; open+5 on a special day), never earlier."""
        if self._witness_today():
            return "OPEN", "packet"
        need = [(s, r) for s in self.symbols for r in ("IDX", "FUT")]
        missing = [k for k in need if k not in self.witness]
        if missing:
            return "UNKNOWN", "witness_missing:" + ",".join("%s/%s" % k for k in missing)
        try:
            keys = [c["ltp_key"] for c in self.symbol_cfg.values()]
            q = self.kite.quote(keys)
            days = []
            for k in keys:
                row = q.get(k) or {}
                d = _rest_ist_day(row.get("timestamp") or row.get("last_trade_time"))
                if d:
                    days.append(d)
        except Exception as exc:  # noqa: BLE001
            self.log("CLOSED_CHECK_QUOTE_FAIL %s" % type(exc).__name__)
            return "UNKNOWN", "quote_failed"
        if any(d == self.day for d in days):
            return "OPEN", "quote"
        if len(days) == len(keys):
            return "CLOSED", "packet+quote"
        return "UNKNOWN", "quote_incomplete"

    def _closed_check(self, now):
        self.closed_checked = True
        verdict, source = self._closed_verdict(now)
        wit = {"%s/%s" % k: v for k, v in sorted(self.witness.items())}
        self.stats.closed_check = {"verdict": verdict, "source": source, "witness_days": wit,
                                   "checked_ist": clk.ist_iso(now)}
        self.log("CLOSED_CHECK verdict=%s source=%s witnesses=%s" % (verdict, source, wit))
        if verdict == "CLOSED":
            d = os.path.join(self.spool, "session", self.day)
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, "CLOSED")
            _atomic_json(path, self.stats.closed_check)
            self.uploader.enqueue(path)
            self.stats.closed = self.stats.closed_check
            self.state = "CLOSED"
            return self._stop(now)
        if verdict == "UNKNOWN":
            self.log("CLOSED_CHECK_UNKNOWN -- recording continues (absence is not a verdict)")
        if not self.options_on:
            self._open_options(now, "closed_check_" + verdict.lower())
        return None

    # ------------------------------------------------------------------ ticker callbacks
    def on_connect(self, ws, response=None):
        with self.lock:
            now = self.clock.now_ns()
            first = not self.ever_connected
            self.connected = True
            self.connected_since = now
            self.disconnected_since = None
            self.ever_connected = True
            self._wd_step, self._wd_next_ns = 0, 0
            self.stats.connects += 1
            if not first:
                self.stats.reconnects += 1
            self._ctl_all("connect", now, pid=self.pid, process_start_ns=self.start_ns,
                          n_tokens=len(self.subscribed), first=first)
            if first and self.subscribed:
                for sym in self.symbols:
                    toks = [t for t, m in self.subscribed.items() if m["sym"] == sym]
                    if toks:
                        self.writer.write(sym, ctl_record("subscribe", now, tokens=toks, reason="restore"), now)
            if first and self.universe is not None:
                for sym, su in self.universe.symbols.items():
                    self._subscribe(sym, [su.index, su.future], "index_future", now)
            allt = sorted(self.subscribed)
            if allt:
                try:
                    ws.subscribe(allt)
                    ws.set_mode(ws.MODE_FULL, allt)
                except Exception as exc:  # noqa: BLE001
                    self.log("RESUBSCRIBE_FAIL %s" % type(exc).__name__)
            if self.state == "WAITING":
                self.state = "RECORDING"
            self._flush_subs(now)
        self.log("CONNECTED first=%s tokens=%d" % (first, len(self.subscribed)))

    def on_close(self, ws, code=None, reason=None):
        with self.lock:
            now = self.clock.now_ns()
            self.connected = False
            self.connected_since = None
            if self.disconnected_since is None:
                self.disconnected_since = now
            if self.stopping:
                self.stats.close_at_stop += 1     # our own shutdown close: no ctl line is written, so not a "disconnect"
            else:
                self.stats.disconnects += 1
            self._ctl_all("disconnect", now, code=code, reason=self._clean(reason))
        self.log("DISCONNECT code=%s" % code)

    def on_error(self, ws, code=None, reason=None):
        with self.lock:
            now = self.clock.now_ns()
            self._ctl_all("error", now, code=code, reason=self._clean(reason))
        self.log("WS_ERROR code=%s" % code)

    def on_reconnect(self, ws, attempt=None):
        with self.lock:
            now = self.clock.now_ns()
            self.stats.reconnect_attempts += 1
            self._ctl_all("reconnect", now, attempt=attempt)
        self.log("RECONNECT attempt=%s" % attempt)

    def on_noreconnect(self, ws):
        with self.lock:
            now = self.clock.now_ns()
            self._ctl_all("error", now, code="NORECONNECT", reason="reconnect attempts exhausted")
        self.fatal = "NORECONNECT"

    def on_ticks(self, ws, ticks):
        # the receive time is read INSIDE the lock (review finding 2): a time read before the lock
        # could be older than a rotation the main loop performs while this thread waits.
        with self.lock:
            now = self.clock.now_ns()
            if self.stopping:
                return
            self.last_frame_ns = now
            self._wd_step, self._wd_next_ns = 0, 0
            try:
                for pkt in ticks:
                    self._record(pkt, now)
            except Exception as exc:  # noqa: BLE001
                self.fatal = "ON_TICKS_%s" % type(exc).__name__

    def _record(self, pkt, now):
        inst = self.universe.by_token.get(pkt.get("instrument_token")) if self.universe else None
        if inst is None:
            self.stats.unknown_tokens += 1
            self.writer.write("_UNKNOWN", packet_record(pkt, None, None, now), now)
            return
        sym, role = inst.sym, inst.role
        rec = packet_record(pkt, sym, role, now)
        self.writer.write(sym, rec, now)
        ets = rec.get("exchange_timestamp")
        self.stats.on_packet(sym, role, inst.token in self.band.get(sym, ()), now, skew_seconds(rec),
                             ets[:10] if isinstance(ets, str) else None)
        if role == "IDX":
            if isinstance(pkt.get("last_price"), (int, float)):
                self.last_idx_price[sym] = pkt["last_price"]
            w = rec.get("exchange_timestamp") or rec.get("last_trade_time")
        elif role == "FUT":
            w = rec.get("last_trade_time") or rec.get("exchange_timestamp")
        else:
            return
        if isinstance(w, str):
            self.witness[(sym, role)] = w[:10]

    # ------------------------------------------------------------------ silence watchdog (T0.1)
    def on_frame(self, ws, payload=None, is_binary=None):
        """KiteTicker calls this for EVERY websocket frame (tick packets and 1-byte heartbeats). It only
        stamps the receive time: no lock, no parsing."""
        self.last_frame_ns = self.clock.now_ns()
        if is_binary and payload is not None and len(payload) <= 1:
            self.frames_hb += 1
        else:
            self.frames_other += 1
        self._wd_step, self._wd_next_ns = 0, 0

    def _watchdog(self, now):
        """Connected, inside the recording window, and silent for SILENCE_S -> force the socket closed so the
        library reconnects. Armed only while connected and between the session open and close: a quiet pre-open
        or a quiet post-close is not a fault. While the silence persists it retries under WD_BACKOFF_S; it never
        raises and never ends the process."""
        if not self.connected or self.ticker is None or now < self._open_ns or now > self._close_ns:
            return
        ref = max(self.last_frame_ns or 0, self.connected_since or 0, self._open_ns)
        threshold = max(config.SILENCE_MIN_S, config.SILENCE_S) * clk.NS
        if now - ref < threshold or now < self._wd_next_ns:
            return
        k = self._wd_step
        self._wd_step += 1
        self._wd_next_ns = now + config.WD_BACKOFF_S[min(k, len(config.WD_BACKOFF_S) - 1)] * clk.NS
        age = (now - ref) / clk.NS
        self.stats.watchdog_trips += 1
        self.log("WATCHDOG_TRIP age=%d n=%d" % (age, self.stats.watchdog_trips))
        ok = True
        try:
            self._ctl_all("watchdog", now, age_s=round(age, 1), attempt=k + 1)
        except Exception as exc:  # noqa: BLE001 -- the reconnect below must happen regardless
            self.log("WATCHDOG_CTL_FAIL %s" % type(exc).__name__)
        try:
            drop = getattr(self.ticker, "force_reconnect", None)
            if drop is None:
                raise RuntimeError("ticker has no force_reconnect")
            drop()
        except Exception as exc:  # noqa: BLE001 -- a watchdog failure must never stop recording
            ok = False
            self.stats.watchdog_errors += 1
            self.log("WATCHDOG_RECONNECT_FAIL %s (retrying in %ds)" % (
                type(exc).__name__, (self._wd_next_ns - now) // clk.NS))
        if len(self.stats.watchdog) < config.WD_TRIP_LIST_CAP:
            self.stats.watchdog.append({"ts_ist": clk.ist_iso(now), "age_s": round(age, 1), "ok": ok})

    # ------------------------------------------------------------------ stop
    def _drain(self, deadline_ns):
        while self.uploader.pending():
            now = self.clock.now_ns()
            if self.term_requested and self.term_deadline_ns is None:
                self.term_deadline_ns = now + config.TERM_DRAIN_S * clk.NS   # SIGTERM during a drain
            if now >= deadline_ns or (self.term_deadline_ns is not None and now >= self.term_deadline_ns):
                break
            self.uploader.process_once(now)
            if self.uploader.pending():
                self.clock.sleep(1)

    def _stop(self, now):
        if self.state not in ("CLOSED",):
            self.state = "STOPPING"
        if self.ticker is not None:
            try:
                self.ticker.close()
            except Exception:  # noqa: BLE001
                pass
        if self._up_thread is not None:
            self._up_stop.set()
            self._up_thread.join(timeout=120)
            self._up_thread = None
        with self.lock:
            self.stopping = True
            self.connected = False
            self.writer.close_all()
            recorded = self.had_state or self.ever_connected
            if recorded and not self.stats.closed:
                self.stats.close_gaps(now)
        deadline = max(now, clk.ist_ns(self.day, self.win["stop"])) + config.DRAIN_SECONDS * clk.NS
        self._drain(deadline)
        if recorded and not self.report_written:
            d = os.path.join(self.spool, "session", self.day)
            os.makedirs(d, exist_ok=True)
            rpath = os.path.join(d, "daily_report_%s.json" % self.day)
            _atomic_json(rpath, self.daily_report(self.clock.now_ns()))
            self.uploader.enqueue(rpath)
            self._drain(deadline)
            mpath = os.path.join(d, "MANIFEST.sha256")
            latest = {}
            for row in self.uploader.manifest_lines(self.day):
                latest[row["key"]] = row["sha256"]
            with open(mpath + ".tmp", "w", encoding="utf-8") as fh:
                for key in sorted(latest):
                    fh.write("%s  %s\n" % (latest[key], key))
            os.replace(mpath + ".tmp", mpath)
            self.uploader.enqueue(mpath)
            self._drain(deadline)
            self.report_written = True
        left = self.uploader.pending()
        if left:
            self.log("STOP uploads_left=%d (kept in spool; the next start re-ships them)" % len(left))
        if self.state != "CLOSED":
            self.state = "DONE"
        self._heartbeat(self.clock.now_ns())
        self._save_state()
        self.log("STOP state=%s" % self.state)
        return config.EXIT_OK

    def daily_report(self, now):
        up = self.uploads_total()
        failed = self.uploader.failed_by_prefix()
        for k, n in failed.items():
            up.setdefault(k, {"ok": 0, "retried": 0, "failed_attempts": 0})
        for k in up:
            up[k]["failed"] = failed.get(k, 0)
        st = self.stats
        syms = {}
        for s in self.symbols:
            ln = st.last_ns[s]
            syms[s] = {
                "packets": st.packets[s],
                "packets_per_minute": st.ppm[s],
                "feed_gaps_gt10s": st.gaps10[s],
                "feed_gaps_gt60s": st.gaps60[s],
                "reconnects": st.reconnects,
                "uploads": up.get(s, {"ok": 0, "retried": 0, "failed_attempts": 0, "failed": 0}),
                "spool_high_water_bytes": st.spool_hwm,
                "subscribed_count": st.subscribed_count[s],
                "last_packet_ist": clk.ist_iso(ln) if ln else None,
                "clock_skew": st.skew_summary(s),
            }
        return jsonable({
            "day": self.day, "generated_ist": clk.ist_iso(now), "phase": "T0",
            "process_start_ist": clk.ist_iso(self.start_ns), "classified": None,
            "closed": st.closed, "closed_check": st.closed_check, "restarts": st.restarts,
            "session": {"kind": "special" if self.win["special"] else "regular", "label": self.win["label"],
                        "open": self.win["session_start"], "close": self.win["session_end"]},
            "connects": st.connects, "reconnects": st.reconnects, "reconnect_attempts": st.reconnect_attempts,
            "disconnects": st.disconnects, "close_at_stop": st.close_at_stop,
            "watchdog_trips": st.watchdog_trips, "watchdog_errors": st.watchdog_errors, "watchdog": st.watchdog,
            "unknown_tokens": st.unknown_tokens,
            "late_records_this_process": self.writer.late_records,
            "torn_line_repairs_this_process": self.writer.torn_repairs,
            "spool_high_water_bytes": st.spool_hwm, "uploads": up,
            "n_subscribed": len(self.subscribed), "symbols": syms,
        })
