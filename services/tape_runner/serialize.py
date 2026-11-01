"""Packet / control record -> one ndjson line. Every key Kite supplied is kept verbatim (plan D-2).

Timestamps. kiteconnect's ticker builds ``last_trade_time`` / ``exchange_timestamp`` with naive
``datetime.fromtimestamp(epoch)``, i.e. in THIS PROCESS's local zone (Etc/UTC on the box unless TZ is
set). Labelling that naive value +05:30 would shift it by 5h30 (the TD-029 shape). ``naive.timestamp()``
is the exact inverse of ``fromtimestamp`` in the same process zone, so the epoch is recovered first and
then rendered in IST. Aware datetimes are converted. Output is ISO-8601 with +05:30.
"""
import json
from datetime import date, datetime

from .clock import IST, ist_iso


def to_ist_iso(v):
    if v.tzinfo is None:
        return datetime.fromtimestamp(v.timestamp(), IST).isoformat()
    return v.astimezone(IST).isoformat()


def iso_to_epoch(s):
    return datetime.fromisoformat(s).timestamp()


def jsonable(v):
    if isinstance(v, datetime):
        return to_ist_iso(v)
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, bytes):
        return v.hex()
    return v


def packet_record(pkt, sym, role, recv_ns):
    rec = {"k": "pkt", "sym": sym, "role": role, "recv_ns": recv_ns, "recv_ist": ist_iso(recv_ns)}
    for key, val in pkt.items():
        if key in rec:
            key = "kite_" + key
        rec[key] = jsonable(val)
    return rec


def ctl_record(ctl, recv_ns, **detail):
    rec = {"k": "ctl", "ctl": ctl, "recv_ns": recv_ns, "recv_ist": ist_iso(recv_ns)}
    for key, val in detail.items():
        rec[key] = jsonable(val)
    return rec


def dumps(rec):
    return json.dumps(rec, separators=(",", ":"), default=str)


def skew_seconds(rec):
    """recv_ns minus exchange_timestamp in seconds, AFTER the IST conversion (reads the serialised
    string back). None when the record carries no exchange_timestamp."""
    ts = rec.get("exchange_timestamp")
    if not isinstance(ts, str):
        return None
    return rec["recv_ns"] / 1e9 - iso_to_epoch(ts)
