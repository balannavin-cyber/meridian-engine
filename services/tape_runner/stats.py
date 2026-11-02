"""Per-day counters for the heartbeat, the state file and the daily report (amendment A-2).

Persisted each minute to state/<date>.json so a mid-day restart resumes the day's report.
Clock skew is kept as a 0.1 s histogram per symbol (bounded memory at ~10^7 packets/day).
"""
from . import clock as clk
from . import config
from . import session

SKEW_BIN = 0.1


def _skew_bin(s):
    if abs(s) <= 600:
        return round(round(s / SKEW_BIN) * SKEW_BIN, 1)
    return float(round(s))


class DayStats:
    def __init__(self, day, symbols):
        self.day = day
        self.symbols = list(symbols)
        self.packets = {s: 0 for s in self.symbols}
        self.ppm = {s: {} for s in self.symbols}                # minute -> {IDX, FUT, ATM3}
        self.last_ns = {s: None for s in self.symbols}
        self.gaps10 = {s: [] for s in self.symbols}
        self.gaps60 = {s: [] for s in self.symbols}
        self.skew_hist = {s: {} for s in self.symbols}          # bin -> count
        self.skew_max = {s: None for s in self.symbols}
        self.skew_min = {s: None for s in self.symbols}
        self.skew_stale = {s: 0 for s in self.symbols}
        self.subscribed_count = {s: {} for s in self.symbols}   # minute -> count
        # Connection counters. Each is the count of ONE event in the control-line log (docs/tape/T0_1_plan.md s3):
        self.connects = 0             # on_connect calls          == ctl "connect" lines
        self.reconnects = 0           # connects after the first  == ctl "connect" lines with first=false
        self.reconnect_attempts = 0   # on_reconnect callbacks    == ctl "reconnect" lines (the library omits each outage's first retry)
        self.disconnects = 0          # on_close calls LOGGED     == ctl "disconnect" lines
        self.close_at_stop = 0        # on_close after our own shutdown began: not logged, so counted apart
        self.watchdog_trips = 0       # silence-watchdog reconnect attempts == ctl "watchdog" lines
        self.watchdog_errors = 0      # attempts whose force_reconnect raised
        self.watchdog = []            # bounded list of {ts_ist, age_s, ok}
        self.unknown_tokens = 0
        self.spool_hwm = 0
        self.restarts = []
        self.closed = None
        self.closed_check = None
        win = session.window(day)
        self._start_ns = clk.ist_ns(day, win["session_start"])     # gap accounting window (not persisted)
        self._end_ns = clk.ist_ns(day, win["session_end"])

    # -- packets -----------------------------------------------------------------------
    def on_packet(self, sym, role, in_band, recv_ns, skew_s, exch_day):
        self.packets[sym] += 1
        m = clk.ist_hm(recv_ns)
        row = self.ppm[sym].setdefault(m, {"IDX": 0, "FUT": 0, "ATM3": 0, "ALL": 0})
        row["ALL"] += 1
        if role in ("IDX", "FUT"):
            row[role] += 1
        elif in_band:
            row["ATM3"] += 1
        self._gap(sym, recv_ns)
        self.last_ns[sym] = recv_ns
        if skew_s is not None:
            if exch_day != self.day:
                self.skew_stale[sym] += 1
            else:
                b = _skew_bin(skew_s)
                h = self.skew_hist[sym]
                h[b] = h.get(b, 0) + 1
                if self.skew_max[sym] is None or skew_s > self.skew_max[sym]:
                    self.skew_max[sym] = skew_s
                if self.skew_min[sym] is None or skew_s < self.skew_min[sym]:
                    self.skew_min[sym] = skew_s

    def _gap(self, sym, now_ns, final=False):
        start, end = self._start_ns, self._end_ns
        if now_ns <= start:
            return
        now_c = min(now_ns, end)
        prev = self.last_ns[sym]
        prev_c = start if prev is None or prev < start else prev
        if prev_c >= end:
            return
        gap = (now_c - prev_c) / clk.NS
        if gap > config.GAP_SHORT_S:
            g = {"from": clk.ist_iso(prev_c), "to": clk.ist_iso(now_c), "seconds": round(gap, 3)}
            if final:
                g["open_at_end"] = True
            self.gaps10[sym].append(g)
            if gap > config.GAP_LONG_S:
                self.gaps60[sym].append(g)

    def close_gaps(self, now_ns):
        """At stop: a symbol silent until 15:30 gets its trailing gap."""
        for s in self.symbols:
            self._gap(s, now_ns, final=True)

    def note_subscribed(self, sym, minute, count):
        self.subscribed_count[sym][minute] = count

    def note_spool(self, nbytes):
        if nbytes > self.spool_hwm:
            self.spool_hwm = nbytes

    # -- skew ------------------------------------------------------------------------
    def skew_summary(self, sym):
        h = self.skew_hist[sym]
        n = sum(h.values())
        out = {"n": n, "median_s": None, "max_s": self.skew_max[sym], "min_s": self.skew_min[sym],
               "stale_excluded": self.skew_stale[sym]}
        if n:
            half = (n + 1) // 2
            acc = 0
            for b in sorted(h):
                acc += h[b]
                if acc >= half:
                    out["median_s"] = b
                    break
        out["verdict"] = skew_verdict(out["median_s"])
        return out

    # -- persistence -------------------------------------------------------------------
    def to_dict(self):
        d = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        d["skew_hist"] = {s: {str(k): v for k, v in h.items()} for s, h in self.skew_hist.items()}
        return d

    @classmethod
    def from_dict(cls, d):
        st = cls(d["day"], d["symbols"])
        for k, v in d.items():
            if k == "skew_hist":
                st.skew_hist = {s: {float(b): c for b, c in h.items()} for s, h in v.items()}
            elif hasattr(st, k):
                setattr(st, k, v)
        return st


def skew_verdict(median_s):
    """Plan correction 3: a median outside [0, 3] s, or negative, means the UTC->IST conversion is
    wrong. None (no same-day packets) cannot exercise the check and says so."""
    if median_s is None:
        return "NOT_EXERCISED"
    if median_s < 0 or median_s > 3:
        return "FAIL"
    return "OK"
