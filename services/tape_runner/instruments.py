"""Instrument resolution and the grow-only option window.

For each symbol: index token from ``kite.ltp`` (the response wins over the expected constant);
options = segment *-OPT with name == SYMBOL at the minimum expiry >= today (the front weekly; on
expiry day that is today); future = segment *-FUT, minimum expiry >= today. Windows count LISTED
strikes, not points, so the 50/100-point grids need no constant.
"""
from datetime import date, datetime

from . import config


def _as_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and len(v) >= 10:
        return datetime.strptime(v[:10], "%Y-%m-%d").date()
    return None


class Inst:
    __slots__ = ("token", "sym", "role", "strike", "opt_type", "tradingsymbol", "expiry")

    def __init__(self, token, sym, role, strike=None, opt_type=None, tradingsymbol=None, expiry=None):
        self.token = int(token)
        self.sym = sym
        self.role = role
        self.strike = strike
        self.opt_type = opt_type
        self.tradingsymbol = tradingsymbol
        self.expiry = expiry

    def meta(self):
        return {"token": self.token, "sym": self.sym, "role": self.role, "strike": self.strike,
                "opt_type": self.opt_type, "tradingsymbol": self.tradingsymbol, "expiry": self.expiry}


class SymbolUniverse:
    def __init__(self, sym, index, future, options, index_ltp, half_window):
        self.sym = sym
        self.index = index
        self.future = future
        self.options = options                       # (strike, opt_type) -> Inst
        self.strikes = sorted({k[0] for k in options})
        self.index_ltp = index_ltp
        self.half_window = half_window

    def atm_pos(self, price):
        if not self.strikes or price is None:
            return None
        best = 0
        for i, k in enumerate(self.strikes):
            if abs(k - price) < abs(self.strikes[best] - price):
                best = i
        return best

    def window_tokens(self, centre_pos):
        lo = max(0, centre_pos - self.half_window)
        hi = min(len(self.strikes), centre_pos + self.half_window + 1)
        out = []
        for k in self.strikes[lo:hi]:
            for ot in ("CE", "PE"):
                inst = self.options.get((k, ot))
                if inst is not None:
                    out.append(inst)
        return out

    def band_tokens(self, atm_pos, band):
        lo = max(0, atm_pos - band)
        hi = min(len(self.strikes), atm_pos + band + 1)
        return {self.options[(k, ot)].token for k in self.strikes[lo:hi] for ot in ("CE", "PE")
                if (k, ot) in self.options}


class Universe:
    def __init__(self, symbols):
        self.symbols = symbols                       # sym -> SymbolUniverse
        self.by_token = {}
        for su in symbols.values():
            for inst in [su.index, su.future] + list(su.options.values()):
                if inst is not None:
                    self.by_token[inst.token] = inst


def resolve(kite, today, log=None, symbols=None):
    log = log or (lambda msg: None)
    symbols = symbols or config.SYMBOLS
    keys = [c["ltp_key"] for c in symbols.values()]
    ltp = kite.ltp(keys)
    out = {}
    dumps = {}
    for sym, cfg in symbols.items():
        q = ltp[cfg["ltp_key"]]
        idx_token = int(q["instrument_token"])
        if idx_token != cfg["expected_index_token"]:
            log("INDEX_TOKEN_MISMATCH sym=%s got=%d expected=%d (response wins)"
                % (sym, idx_token, cfg["expected_index_token"]))
        exch = cfg["exchange"]
        if exch not in dumps:
            dumps[exch] = kite.instruments(exch)
        rows = [r for r in dumps[exch] if r.get("name") == sym]
        opts = [r for r in rows if str(r.get("segment", "")).endswith("-OPT")
                and _as_date(r.get("expiry")) is not None and _as_date(r.get("expiry")) >= today]
        futs = [r for r in rows if str(r.get("segment", "")).endswith("-FUT")
                and _as_date(r.get("expiry")) is not None and _as_date(r.get("expiry")) >= today]
        if not opts or not futs:
            raise RuntimeError("RESOLVE_EMPTY sym=%s opts=%d futs=%d" % (sym, len(opts), len(futs)))
        front = min(_as_date(r["expiry"]) for r in opts)
        fut_exp = min(_as_date(r["expiry"]) for r in futs)
        fut_row = sorted((r for r in futs if _as_date(r["expiry"]) == fut_exp),
                         key=lambda r: int(r["instrument_token"]))[0]
        options = {}
        for r in opts:
            if _as_date(r["expiry"]) != front:
                continue
            ot = r.get("instrument_type")
            if ot not in ("CE", "PE"):
                continue
            k = float(r["strike"])
            options[(k, ot)] = Inst(r["instrument_token"], sym, "OPT", k, ot, r.get("tradingsymbol"),
                                    front.isoformat())
        index = Inst(idx_token, sym, "IDX", tradingsymbol=cfg["ltp_key"])
        future = Inst(fut_row["instrument_token"], sym, "FUT", tradingsymbol=fut_row.get("tradingsymbol"),
                      expiry=fut_exp.isoformat())
        out[sym] = SymbolUniverse(sym, index, future, options, float(q["last_price"]), cfg["half_window"])
        log("RESOLVED sym=%s index=%d future=%s front_expiry=%s strikes=%d"
            % (sym, idx_token, future.tradingsymbol, front.isoformat(), len(out[sym].strikes)))
    return Universe(out)
