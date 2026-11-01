"""Clock protocol and IST helpers. Every time decision in the runner goes through an injected clock."""
import time
from datetime import datetime, timedelta, timezone

from . import config

IST = timezone(timedelta(hours=5, minutes=30))
NS = 1_000_000_000


class SystemClock:
    def now_ns(self):
        return time.time_ns()

    def sleep(self, seconds):
        time.sleep(seconds)


def ist_dt(ns):
    return datetime.fromtimestamp(ns / NS, IST)


def ist_iso(ns):
    # microsecond precision, explicit +05:30
    s, rem = divmod(ns, NS)
    return datetime.fromtimestamp(s, IST).replace(microsecond=rem // 1000).isoformat()


def ist_date(ns):
    return ist_dt(ns).strftime("%Y-%m-%d")


def ist_hm(ns):
    return ist_dt(ns).strftime("%H:%M")


def ist_ns(date_str, hms):
    """'2026-11-02', '09:19:59.9' -> epoch ns (exact for up to 9 fractional digits)."""
    parts = hms.split(":")
    h, m = int(parts[0]), int(parts[1])
    sec = parts[2] if len(parts) > 2 else "0"
    whole, _, frac = sec.partition(".")
    base = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=h, minute=m, second=int(whole), tzinfo=IST)
    return int(base.timestamp()) * NS + int((frac + "000000000")[:9])


def seg_start_ns(ns):
    # IST = UTC+05:30 is a whole number of 5-minute blocks, so epoch flooring is IST-aligned.
    step = config.SEG_SECONDS * NS
    return (ns // step) * step


def seg_label(ns):
    return ist_dt(seg_start_ns(ns)).strftime("%H%M")


def at(ns, hm):
    """True when IST wall time of ns is at or after 'HH:MM' on the same IST date."""
    return ns >= ist_ns(ist_date(ns), hm)
