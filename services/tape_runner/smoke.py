"""--smoke: profile -> resolve -> subscription list size -> one 60 s connection -> packet count and
clock skew. Writes nothing to the spool or S3.

Exit 0: connected and subscribed (0 packets on a closed day is a PASS).
Exit 3: CLOCK SKEW FAIL -- median (recv_ns - exchange_timestamp) outside [0, 3] s, or negative, after
        the UTC->IST conversion: the conversion is wrong.
Exit 4: no connect, or subscribe failed.  Exit 78: profile failed (token).
Exit 5: S3 FAIL -- one real PutObject to _smoke/<UTC timestamp>.txt in the real bucket and region, with
        the runner's own parameters (ContentMD5, SSE-S3), did not return ETag == local md5. The S3 check
        runs first and is reported even when the Kite part fails. GetObject/HeadObject are never used (A-3).
"""
import base64
import hashlib
import os
import socket
import threading
from datetime import datetime, timezone

from . import clock as clk
from . import config
from .instruments import resolve
from .serialize import packet_record, skew_seconds
from .stats import DayStats


def s3_check(s3, bucket, region, clock, out=print):
    """One real PutObject, verified exactly as the uploader verifies (ETag == md5 hex)."""
    utc = datetime.fromtimestamp(clock.now_ns() / 1e9, timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = "_smoke/%s.txt" % utc
    body = ("MERIDIAN tape T0 smoke %s host=%s pid=%d\n" % (utc, socket.gethostname(), os.getpid())).encode()
    md5 = hashlib.md5(body)
    try:
        resp = s3.put_object(Bucket=bucket, Key=key, Body=body, ServerSideEncryption="AES256",
                             ContentMD5=base64.b64encode(md5.digest()).decode("ascii"))
    except Exception as exc:  # noqa: BLE001 -- error code only, never credentials
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "") if hasattr(exc, "response") else ""
        out("SMOKE S3 FAIL bucket=%s region=%s key=%s error=%s %s" % (bucket, region, key, type(exc).__name__, code))
        return False
    etag = str((resp or {}).get("ETag", "")).strip('"')
    if etag == md5.hexdigest():
        out("SMOKE S3 PASS bucket=%s region=%s key=%s etag=%s == md5" % (bucket, region, key, etag))
        return True
    out("SMOKE S3 FAIL bucket=%s region=%s key=%s etag=%s != md5=%s" % (bucket, region, key, etag, md5.hexdigest()))
    return False


def run_smoke(kite, ticker_factory, clock, wait_s=60, out=print, s3=None, bucket=None, region=None):
    now = clock.now_ns()
    day = clk.ist_date(now)
    s3_ok = True
    if s3 is not None:
        s3_ok = s3_check(s3, bucket or config.BUCKET, region, clock, out)
    code = _run_kite(kite, ticker_factory, clock, wait_s, out, now, day)
    if code == 0 and not s3_ok:
        out("SMOKE FAIL: S3 -- Monday's uploads would fail; fix the key, bucket or region before 08:50")
        return 5
    return code


def _run_kite(kite, ticker_factory, clock, wait_s, out, now, day):
    try:
        kite.profile()
    except Exception as exc:  # noqa: BLE001
        out("SMOKE TOKEN_FAIL %s" % type(exc).__name__)
        return config.EXIT_TOKEN_FAIL
    out("SMOKE profile OK")
    try:
        uni = resolve(kite, clk.ist_dt(now).date(), log=lambda m: out("SMOKE " + m))
    except Exception as exc:  # noqa: BLE001 -- the type only
        out("SMOKE FAIL: RESOLVE %s" % type(exc).__name__)
        return 4
    tokens = []
    for sym, su in uni.symbols.items():
        pos = su.atm_pos(su.index_ltp)
        win = su.window_tokens(pos)
        tokens += [su.index.token, su.future.token] + [i.token for i in win]
        out("SMOKE %s ltp=%s atm=%s window_tokens=%d (+index +future)" % (sym, su.index_ltp, su.strikes[pos], len(win)))
    out("SMOKE subscription list size=%d" % len(tokens))

    stats = DayStats(day, list(uni.symbols))
    state = {"connected": False, "subscribed": False, "packets": 0, "err": None}
    done = threading.Event()
    lock = threading.Lock()

    def on_connect(ws, response=None):
        state["connected"] = True
        try:
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)
            state["subscribed"] = True
        except Exception as exc:  # noqa: BLE001
            state["err"] = "SUBSCRIBE_%s" % type(exc).__name__

    def on_ticks(ws, ticks):
        t = clock.now_ns()
        with lock:
            for pkt in ticks:
                inst = uni.by_token.get(pkt.get("instrument_token"))
                if inst is None:
                    continue
                rec = packet_record(pkt, inst.sym, inst.role, t)
                ets = rec.get("exchange_timestamp")
                stats.on_packet(inst.sym, inst.role, False, t, skew_seconds(rec),
                                ets[:10] if isinstance(ets, str) else None)
                state["packets"] += 1

    def on_close(ws, code=None, reason=None):
        out("SMOKE ws closed code=%s" % code)

    def on_error(ws, code=None, reason=None):
        state["err"] = "WS_ERROR_%s" % code

    t = ticker_factory()
    t.on_connect = on_connect
    t.on_ticks = on_ticks
    t.on_close = on_close
    t.on_error = on_error
    t.connect(threaded=True)
    done.wait(wait_s) if wait_s else None
    try:
        t.close()
    except Exception:  # noqa: BLE001
        pass

    out("SMOKE connected=%s subscribed=%s packets=%d%s" % (
        state["connected"], state["subscribed"], state["packets"],
        (" error=%s" % state["err"]) if state["err"] else ""))
    skew_fail = False
    for sym in uni.symbols:
        sk = stats.skew_summary(sym)
        out("SMOKE CLOCK_SKEW %s n=%d median_s=%s max_s=%s min_s=%s stale_excluded=%d verdict=%s" % (
            sym, sk["n"], sk["median_s"], _r(sk["max_s"]), _r(sk["min_s"]), sk["stale_excluded"], sk["verdict"]))
        if sk["verdict"] == "NOT_EXERCISED":
            out("SMOKE CLOCK_SKEW %s not exercised: no packet dated today (closed day); the conversion is "
                "pinned by the offline test, re-run the smoke on a trading day to measure it" % sym)
        if sk["verdict"] == "FAIL":
            skew_fail = True
    if skew_fail:
        out("!" * 72)
        out("SMOKE FAIL: CLOCK SKEW -- median recv-minus-exchange outside [0, 3] s. The UTC->IST")
        out("conversion of exchange_timestamp is WRONG. Do not run the recorder until fixed.")
        out("!" * 72)
        return 3
    if not (state["connected"] and state["subscribed"]):
        out("SMOKE FAIL: connect/subscribe did not succeed")
        return 4
    out("SMOKE PASS")
    return 0


def _r(x):
    return None if x is None else round(x, 3)
