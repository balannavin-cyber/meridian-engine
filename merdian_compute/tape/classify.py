"""Aggressor classification of recorded Kite packets (tape phase T0, design §2.3).

PURE: stdlib only, no clock, no randomness, no I/O. Not wired into the runner in T0.

Kite sends no per-trade feed, so a "trade" is the change of ``volume_traded`` between two
consecutive packets of ONE instrument. The caller keeps ``prev`` per instrument token.

classify(prev, pkt) -> Trade(qty, side, price)
  1. prev is None                      -> baseline: qty 0, side None (never a trade)
  2. dv = vol(pkt) - vol(prev) <= 0     -> qty 0, side None (no trade; a negative delta is a
                                           reset and the next delta is measured from pkt)
  3. quote AT THE PREVIOUS PACKET: bid = prev.depth.buy[0].price, ask = prev.depth.sell[0].price,
     p = pkt.last_price; a valid quote is 0 < bid <= ask:
       p >= ask -> BUY ; p <= bid -> SELL
       bid < p < ask: p > mid -> BUY ; p < mid -> SELL ; p == mid -> tick test against
       prev.last_price (> BUY, < SELL, == UNCL)
  4. anything else (no depth, a zero side, crossed quote, no price) -> UNCL WITH its quantity:
     counted, never dropped.

Trade.price is the price attributed to the delta (plan D-7): the average-traded-price identity
(atp*vol - atp_prev*vol_prev)/dv when both ATPs are present and the result is positive, else
last_price.
"""
from collections import namedtuple

BUY = "BUY"
SELL = "SELL"
UNCL = "UNCL"

Trade = namedtuple("Trade", ["qty", "side", "price"])

_NO_TRADE = Trade(0, None, None)


def _num(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return x


def _top(pkt, side):
    depth = pkt.get("depth") if isinstance(pkt, dict) else None
    if not isinstance(depth, dict):
        return None
    levels = depth.get(side)
    if not levels:
        return None
    lvl = levels[0]
    if not isinstance(lvl, dict):
        return None
    return _num(lvl.get("price"))


def _delta_price(prev, pkt, dv):
    atp0 = _num(prev.get("average_traded_price"))
    atp1 = _num(pkt.get("average_traded_price"))
    v0 = _num(prev.get("volume_traded"))
    v1 = _num(pkt.get("volume_traded"))
    if atp0 is not None and atp1 is not None and v0 is not None and v1 is not None and dv > 0:
        p = (atp1 * v1 - atp0 * v0) / dv
        if p > 0:
            return p
    return _num(pkt.get("last_price"))


def classify(prev, pkt):
    """Classify the volume between ``prev`` and ``pkt`` (same instrument)."""
    if prev is None:
        return _NO_TRADE
    v0 = _num(prev.get("volume_traded"))
    v1 = _num(pkt.get("volume_traded"))
    if v0 is None or v1 is None:
        return _NO_TRADE
    dv = int(v1 - v0)
    if dv <= 0:
        return _NO_TRADE
    price = _delta_price(prev, pkt, dv)
    p = _num(pkt.get("last_price"))
    bid = _top(prev, "buy")
    ask = _top(prev, "sell")
    if p is None or bid is None or ask is None or not (0 < bid <= ask):
        return Trade(dv, UNCL, price)
    if p >= ask:
        return Trade(dv, BUY, price)
    if p <= bid:
        return Trade(dv, SELL, price)
    mid = (bid + ask) / 2.0
    if p > mid:
        return Trade(dv, BUY, price)
    if p < mid:
        return Trade(dv, SELL, price)
    lp = _num(prev.get("last_price"))
    if lp is not None and p > lp:
        return Trade(dv, BUY, price)
    if lp is not None and p < lp:
        return Trade(dv, SELL, price)
    return Trade(dv, UNCL, price)


class MinuteAccumulator:
    """Per-minute buy/sell/uncl quantities, trades (deltas > 0) and vwap.

    Minute labels are supplied by the caller (from exchange_timestamp); the library never
    reads a clock. Invariant: buy_qty + sell_qty + uncl_qty == sum of positive deltas added.
    """

    def __init__(self):
        self._m = {}

    def add(self, minute, trade):
        if trade is None or trade.qty <= 0:
            return
        row = self._m.get(minute)
        if row is None:
            row = {"buy_qty": 0, "sell_qty": 0, "uncl_qty": 0, "trades": 0, "_pv": 0.0, "_pq": 0}
            self._m[minute] = row
        if trade.side == BUY:
            row["buy_qty"] += trade.qty
        elif trade.side == SELL:
            row["sell_qty"] += trade.qty
        else:
            row["uncl_qty"] += trade.qty
        row["trades"] += 1
        if trade.price is not None:
            row["_pv"] += trade.price * trade.qty
            row["_pq"] += trade.qty

    def minutes(self):
        out = {}
        for minute in sorted(self._m):
            r = self._m[minute]
            out[minute] = {
                "buy_qty": r["buy_qty"],
                "sell_qty": r["sell_qty"],
                "uncl_qty": r["uncl_qty"],
                "trades": r["trades"],
                "vwap": (r["_pv"] / r["_pq"]) if r["_pq"] else None,
            }
        return out

    def totals(self):
        t = {"buy_qty": 0, "sell_qty": 0, "uncl_qty": 0, "trades": 0}
        for r in self._m.values():
            for k in t:
                t[k] += r[k]
        return t
