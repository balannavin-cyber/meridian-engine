"""Synthetic Kite for the T0 load rehearsal. NOT shipped by install.sh (tests/ is never installed).

SyntheticKite   -- profile / instruments / ltp / quote with a NIFTY + SENSEX universe that resolves
                   to the real 148-token subscription (82 NIFTY + 62 SENSEX options, 2 indexes, 2
                   futures) through the runner's own resolver.
SyntheticTicker -- plugs into the real Recorder in place of kiteconnect.KiteTicker: same attribute
                   callbacks, subscribe / set_mode / close, connect(threaded=True) starts a thread named
                   'ticker' that calls on_connect and then on_ticks with batches every 100 ms.

Packets are kiteconnect-shaped dicts (full mode: 5+5 depth levels for options/futures; the 32-byte
index shape for indexes) with naive datetimes built by datetime.fromtimestamp exactly as the real
ticker builds them (process zone; the unit sets TZ=Asia/Kolkata). Every packet carries
  rehearsal_seq   -- per-token, 0, 1, 2 ... with no gaps (the recorder stores unknown keys verbatim)
  rehearsal_batch -- the id of the on_ticks call that delivered it.

Load: 1x = 58,000 packets per symbol per 5-minute segment (the open rate measured on this box,
T0 review item 6), i.e. 193.3 packets/s per symbol, 386.7/s in total. The schedule is a list of
(multiplier, seconds) phases; the emitter computes the packets due from elapsed time, so a stalled
on_ticks call is followed by a larger batch, never by lost load.
"""
import random
import threading
import time
from datetime import date, datetime, timedelta

PKTS_PER_SYMBOL_PER_SEG_1X = 58_000
SEG_S = 300
TICK_S = 0.1
INDEX = {"NIFTY": (256265, 25000.0, "NSE:NIFTY 50"), "SENSEX": (265, 80000.0, "BSE:SENSEX")}
GRID = {"NIFTY": (22000, 50, 121, "NFO"), "SENSEX": (70000, 100, 201, "BFO")}


def rate_per_symbol(mult):
    return mult * PKTS_PER_SYMBOL_PER_SEG_1X / SEG_S


class SyntheticKite:
    def __init__(self, today=None):
        self.today = today or date.today()
        self._dumps = None

    def profile(self):
        return {"user_id": "REHEARSAL"}

    def _build(self):
        front = self.today + timedelta(days=3)
        nxt = front + timedelta(days=7)
        fut = self.today + timedelta(days=25)
        out = {"NFO": [], "BFO": []}
        t = 5_000_000
        for sym, (k0, step, n, exch) in GRID.items():
            for exp in (front, nxt):
                for i in range(n):
                    k = k0 + step * i
                    for ot in ("CE", "PE"):
                        t += 1
                        out[exch].append({"instrument_token": t, "name": sym, "segment": exch + "-OPT",
                                          "exchange": exch, "instrument_type": ot, "strike": float(k),
                                          "expiry": exp, "tradingsymbol": "%s%s%d%s" % (sym, exp.strftime("%y%m%d"), k, ot),
                                          "lot_size": 75, "tick_size": 0.05, "last_price": 0.0})
            t += 1
            out[exch].append({"instrument_token": t, "name": sym, "segment": exch + "-FUT", "exchange": exch,
                              "instrument_type": "FUT", "strike": 0.0, "expiry": fut,
                              "tradingsymbol": "%sFUT" % sym, "lot_size": 75, "tick_size": 0.05, "last_price": 0.0})
        return out

    def instruments(self, exch):
        if self._dumps is None:
            self._dumps = self._build()
        return [dict(r) for r in self._dumps[exch]]

    def ltp(self, keys):
        by_key = {v[2]: v for v in INDEX.values()}
        return {k: {"instrument_token": by_key[k][0], "last_price": by_key[k][1]} for k in keys}

    def quote(self, keys):
        now = datetime.now()
        return {k: {"timestamp": now, "last_trade_time": now} for k in keys}


class SyntheticTicker:
    MODE_FULL = "full"

    def __init__(self, universe_tokens, schedule, metrics, batch_log=None, seed=1):
        """universe_tokens: token -> (sym, role, ref_price); schedule: [(mult, seconds), ...]."""
        self.universe = universe_tokens
        self.schedule = schedule
        self.metrics = metrics
        self.batch_log = batch_log
        self.rnd = random.Random(seed)
        self.on_ticks = self.on_connect = self.on_close = self.on_error = None
        self.on_reconnect = self.on_noreconnect = None
        self._lock = threading.Lock()
        self.subscribed = {"NIFTY": [], "SENSEX": []}
        self._sub_set = set()
        self.seq = {}
        self.vol = {}
        self._rr = {"NIFTY": 0, "SENSEX": 0}
        self._stop = threading.Event()
        self.thread = None
        self.done = threading.Event()
        self.batch_id = 0

    # -- KiteTicker surface ------------------------------------------------------------
    def connect(self, threaded=True, **kw):
        self.thread = threading.Thread(target=self._run, name="ticker", daemon=True)
        self.thread.start()

    def subscribe(self, tokens):
        with self._lock:
            for t in tokens:
                if t in self._sub_set or t not in self.universe:
                    continue
                self._sub_set.add(t)
                self.subscribed[self.universe[t][0]].append(t)
                self.seq.setdefault(t, 0)
                self.vol.setdefault(t, 1_000_000)
        return True

    def set_mode(self, mode, tokens):
        return True

    def unsubscribe(self, tokens):
        raise AssertionError("the recorder must never unsubscribe")

    def close(self, *a):
        self._stop.set()

    def stop(self):
        self._stop.set()

    # -- packets -----------------------------------------------------------------------
    def _packet(self, tok, now_s):
        sym, role, ref = self.universe[tok]
        seq = self.seq[tok]
        self.seq[tok] = seq + 1
        ts = datetime.fromtimestamp(int(now_s))
        p = round(ref * (1 + self.rnd.uniform(-0.002, 0.002)), 2)
        if role == "IDX":
            return {"tradable": False, "mode": "full", "instrument_token": tok, "last_price": p,
                    "ohlc": {"high": p, "low": p, "open": p, "close": p}, "change": 0.1,
                    "exchange_timestamp": ts, "rehearsal_seq": seq, "rehearsal_batch": self.batch_id}
        dv = self.rnd.choice((0, 25, 50, 75, 150, 300))
        self.vol[tok] += dv
        r = self.rnd
        return {"tradable": True, "mode": "full", "instrument_token": tok, "last_price": p,
                "last_traded_quantity": dv or 75, "average_traded_price": p, "volume_traded": self.vol[tok],
                "total_buy_quantity": r.randint(1, 10 ** 6), "total_sell_quantity": r.randint(1, 10 ** 6),
                "ohlc": {"open": p, "high": p, "low": p, "close": p}, "change": 0.1,
                "last_trade_time": ts, "oi": r.randint(1, 10 ** 7), "oi_day_high": 1, "oi_day_low": 1,
                "exchange_timestamp": ts,
                "depth": {"buy": [{"quantity": r.randint(1, 9999), "price": round(p - 0.05 * (k + 1), 2),
                                   "orders": r.randint(1, 50)} for k in range(5)],
                          "sell": [{"quantity": r.randint(1, 9999), "price": round(p + 0.05 * (k + 1), 2),
                                    "orders": r.randint(1, 50)} for k in range(5)]},
                "rehearsal_seq": seq, "rehearsal_batch": self.batch_id}

    def _mult_at(self, elapsed):
        acc = 0.0
        for mult, secs in self.schedule:
            acc += secs
            if elapsed < acc:
                return mult
        return None

    def _run(self):
        self.on_connect(self, {"rehearsal": True})
        t_start = time.monotonic()
        owed = {"NIFTY": 0.0, "SENSEX": 0.0}
        last = t_start
        while not self._stop.is_set():
            now = time.monotonic()
            mult = self._mult_at(now - t_start)
            if mult is None:
                break
            dt = now - last
            last = now
            batch, counts = [], {}
            now_s = time.time()
            with self._lock:
                full = len(self._sub_set) >= 148
                for sym in ("NIFTY", "SENSEX"):
                    toks = self.subscribed[sym]
                    if not toks:
                        continue
                    # full rate once the whole window is subscribed; 1 pkt/s per token before that
                    owed[sym] += (rate_per_symbol(mult) if full else len(toks)) * dt
                    n = int(owed[sym])
                    owed[sym] -= n
                    for _ in range(n):
                        i = self._rr[sym] % len(toks)
                        self._rr[sym] += 1
                        batch.append(self._packet(toks[i], now_s))
                    counts[sym] = n
            if batch:
                t0 = time.time_ns()
                c0 = time.perf_counter()
                self.on_ticks(self, batch)
                stall = time.perf_counter() - c0
                t1 = time.time_ns()
                self.metrics.on_ticks_call(stall, len(batch), mult)
                if self.batch_log is not None:
                    self.batch_log.write('{"b":%d,"t0":%d,"t1":%d,"n":{"NIFTY":%d,"SENSEX":%d},"m":%g}\n'
                                         % (self.batch_id, t0, t1, counts.get("NIFTY", 0),
                                            counts.get("SENSEX", 0), mult))
                self.batch_id += 1
            sleep = TICK_S - (time.monotonic() - now)
            if sleep > 0:
                self._stop.wait(sleep)
        self.done.set()


def universe_tokens(kite, today):
    """token -> (sym, role, ref_price) for every instrument the recorder can subscribe."""
    out = {}
    for sym, (tok, px, _key) in INDEX.items():
        out[tok] = (sym, "IDX", px)
    for exch in ("NFO", "BFO"):
        for r in kite.instruments(exch):
            if r["segment"].endswith("-FUT"):
                out[r["instrument_token"]] = (r["name"], "FUT", INDEX[r["name"]][1])
            else:
                k = r["strike"]
                px = max(5.0, abs(INDEX[r["name"]][1] - k) * 0.1 + 50.0)
                out[r["instrument_token"]] = (r["name"], "OPT", px)
    return out
