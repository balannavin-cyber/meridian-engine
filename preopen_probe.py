#!/usr/bin/env python3
"""preopen_probe.py -- R4 (TD-S97-NEW-5, TD-S97-NEW-6; ruling S100-E): one access check at 09:09 IST.

Scheduled: `39 3 * * 1-5` UTC (09:09 IST), one minute before merdian-wsfeed-start.timer (03:40 UTC) and six
before the open. It answers ONE question -- can MERIDIAN reach its two brokers right now -- and pages if not:

  Dhan   option-chain expiry list (where token expiry shows first in the chain ingest), marketfeed LTP for
         NIFTY / SENSEX, and a one-minute intraday request on the previous trading day's 15:20-15:30 bars.
         Each failure is classified from the raw text: 806 / DH-902 -> SUBSCRIPTION (the 2026-10-21 Data API
         lapse); 401 / DH-901 / "token invalid|expired" -> TOKEN; anything else -> ERROR. One retry after
         RETRY_S on a non-auth, non-subscription error, so a single 5xx blip does not page.
  Kite   `profile()` with the box's ZERODHA_* credentials -- the same call bin/wsfeed_preflight.sh makes at
         09:10, so a failure here is the feed failing one minute early, while there is time to act.

What it does NOT page on: whether the pre-open print has landed. At 09:09 it may not have (the operator's
window is 09:08-09:12), so that line is information only -- NIFTY / SENSEX LTP against the previous close --
in the message and the ledger notes. Data-freshness alarms belong to the contract check, not here.

Ledger: one script_execution_log row per run (SUCCESS / HOLIDAY_GATE exit 0; TOKEN_EXPIRED or DATA_ERROR
exit 1). Sender: telegram_utils.send_critical, which since S97-I (44b8b96) delivers and logs any refusal.
Nothing here prints an environment value (Rule 19); broker error text is truncated and never includes a
request header.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

SCRIPT_NAME = "preopen_probe.py"
IST = timezone(timedelta(hours=5, minutes=30))
INDEX = {"NIFTY": 13, "SENSEX": 51}          # Dhan IDX_I security ids (ingest_option_chain_local UNDERLYING_MAP)
RETRY_S = 5
MAX_ERR = 200


def classify(err: Exception) -> str:
    """SUBSCRIPTION / TOKEN / ERROR from the broker's own words."""
    msg = str(err)
    low = msg.lower()
    if "806" in msg or "dh-902" in low:
        return "SUBSCRIPTION"
    if ("401" in msg or "unauthorized" in low or "dh-901" in low
            or ("token" in low and ("invalid" in low or "expired" in low))):
        return "TOKEN"
    return "ERROR"


def _attempt(fn: Callable[[], Any], sleep: Callable[[float], None]) -> tuple[bool, Any, str]:
    """(ok, value, class). One retry, only for a plain ERROR."""
    try:
        return True, fn(), ""
    except Exception as e:                                   # noqa: BLE001
        cls = classify(e)
        if cls != "ERROR":
            return False, f"{cls}: {str(e)[:MAX_ERR]}", cls
        sleep(RETRY_S)
        try:
            return True, fn(), ""
        except Exception as e2:                              # noqa: BLE001
            cls2 = classify(e2)
            return False, f"{cls2}: {str(e2)[:MAX_ERR]}", cls2


def _ltp_of(resp: dict, sec_id: int) -> Optional[float]:
    try:
        v = (resp.get("data") or {}).get("IDX_I", {}).get(str(sec_id), {})
        p = v.get("last_price")
        return float(p) if p is not None else None
    except Exception:                                         # noqa: BLE001
        return None


def run(now_utc: datetime, *, dhan_factory: Callable[[], Any], kite_factory: Callable[[], Any],
        send: Callable[[str, dict], bool], is_trading_day: Callable[[], bool],
        prev_trading_day: Callable[[str], str], log: Any,
        sleep: Callable[[float], None] = time.sleep) -> int:
    """Return the process exit code. Every path ends in exactly one ledger finalisation."""
    ist = now_utc.astimezone(IST)
    try:
        open_today = is_trading_day()
    except Exception as e:                                    # noqa: BLE001 -- fail open, as the shared gate does
        print(f"[GATE] calendar unavailable ({e}); probing anyway")
        open_today = True
    if not open_today:
        print("[GATE] not a trading day -- no probe")
        return log.exit_with_reason("HOLIDAY_GATE", exit_code=0)

    results: dict[str, tuple[bool, str]] = {}
    info: list[str] = []
    classes: list[str] = []

    # ---- Dhan ----
    try:
        dhan = dhan_factory()
    except Exception as e:                                    # noqa: BLE001
        dhan = None
        results["Dhan client"] = (False, f"ERROR: {str(e)[:MAX_ERR]}"); classes.append("ERROR")
    if dhan is not None:
        ok, val, cls = _attempt(lambda: dhan.get_expiry_list(underlying_scrip=INDEX["NIFTY"], underlying_seg="IDX_I"), sleep)
        if ok and not (isinstance(val, dict) and isinstance(val.get("data"), list) and val["data"]):
            ok, val, cls = False, f"ERROR: empty expiry list {str(val)[:MAX_ERR]}", "ERROR"
        results["Dhan option chain (expiry list)"] = (ok, "ok" if ok else val); classes += [cls] if not ok else []

        ok, ltp, cls = _attempt(lambda: dhan.get_ltp(list(INDEX.values()), exchange_segment="IDX_I"), sleep)
        if ok and _ltp_of(ltp, INDEX["NIFTY"]) is None:
            ok, ltp, cls = False, f"ERROR: no NIFTY price {str(ltp)[:MAX_ERR]}", "ERROR"
        results["Dhan LTP"] = (ok, "ok" if ok else ltp); classes += [cls] if not ok else []

        prev = prev_trading_day(ist.date().isoformat())
        payload = {"securityId": str(INDEX["NIFTY"]), "exchangeSegment": "IDX_I", "instrument": "INDEX",
                   "interval": "1", "oi": False,
                   "fromDate": f"{prev} 15:20:00", "toDate": f"{prev} 15:30:00"}
        ok, bars, cls = _attempt(lambda: dhan._post("/v2/charts/intraday", payload), sleep)
        closes = bars.get("close") if ok and isinstance(bars, dict) else None
        if ok and not closes:
            ok, bars, cls = False, f"ERROR: no intraday bars for {prev} {str(bars)[:MAX_ERR]}", "ERROR"
        results["Dhan intraday"] = (ok, "ok" if ok else bars); classes += [cls] if not ok else []

        if results["Dhan LTP"][0] and closes:
            last, prev_close = _ltp_of(ltp, INDEX["NIFTY"]), float(closes[-1])
            moved = abs(last - prev_close) >= 0.01
            info.append(f"NIFTY LTP {last:.2f} vs {prev} close {prev_close:.2f}: "
                        f"{'pre-open print in' if moved else 'pre-open print not yet in'} (information only)")

    # ---- Kite ----
    try:
        prof = kite_factory().profile()
        results["Kite token (profile)"] = (True, "ok")
        uid = (prof or {}).get("user_id") if isinstance(prof, dict) else None
        if uid:
            info.append("Kite user verified")
    except Exception as e:                                    # noqa: BLE001
        cls = classify(e) if classify(e) != "ERROR" else "TOKEN"   # profile() failing IS the preflight failure
        results["Kite token (profile)"] = (False, f"{cls}: {str(e)[:MAX_ERR]}"); classes.append(cls)

    failed = {k: v for k, (ok, v) in results.items() if not ok}
    lines = [f"{k}: {'OK' if ok else 'FAIL - ' + v}" for k, (ok, v) in results.items()]
    summary = "; ".join(lines + info)
    print(f"[PROBE] {ist:%Y-%m-%d %H:%M} IST  " + summary)
    if not failed:
        return log.complete(notes=summary[:1000])

    head = (f"Pre-open access check {ist:%H:%M} IST FAILED: {', '.join(failed)}. "
            "The 09:15 session will not capture from a failed broker.")
    delivered = send(head, {"checks": " | ".join(lines), "info": " | ".join(info) or "-"})
    print(f"[SENT] CRITICAL pre-open probe (delivered={bool(delivered)})")
    reason = ("TOKEN_EXPIRED" if "TOKEN" in classes                 # S100_SUBSCRIPTION_LAPSED: token first --
              else "SUBSCRIPTION_LAPSED" if "SUBSCRIPTION" in classes  # a dead Kite token is the actionable one
              else "DATA_ERROR")
    return log.exit_with_reason(reason, exit_code=1, notes=summary[:1000],
                                error_message=" | ".join(f"{k}: {v}" for k, v in failed.items())[:1000])


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    from core.execution_log import ExecutionLog
    from core.dhan_client import DhanClient
    from core.trading_calendar_gate import is_trading_day_today, previous_trading_day
    from telegram_utils import send_critical

    def kite_factory():
        from kiteconnect import KiteConnect
        k = KiteConnect(api_key=os.environ["ZERODHA_API_KEY"])
        k.set_access_token(os.environ["ZERODHA_ACCESS_TOKEN"])
        return k

    if "--check" in sys.argv[1:]:
        # Operator verification: real broker calls, any day, NO page and NO ledger row -- prints the verdict.
        class _Print:
            def complete(self, notes=None): print("[CHECK] verdict SUCCESS"); return 0
            def exit_with_reason(self, reason, exit_code=0, notes=None, error_message=None):
                print(f"[CHECK] verdict {reason} exit {exit_code}" + (f" | {error_message}" if error_message else ""))
                return exit_code
        return run(datetime.now(timezone.utc), dhan_factory=DhanClient, kite_factory=kite_factory,
                   send=lambda m, c: print(f"[CHECK] would page: {m} | {c}") or True,
                   is_trading_day=lambda: True, prev_trading_day=lambda d: previous_trading_day(d)[0], log=_Print())
    log = ExecutionLog(script_name=SCRIPT_NAME, expected_writes={})
    return run(datetime.now(timezone.utc), dhan_factory=DhanClient, kite_factory=kite_factory,
               send=lambda m, c: send_critical(m, context=c), is_trading_day=is_trading_day_today,
               prev_trading_day=lambda d: previous_trading_day(d)[0], log=log)


if __name__ == "__main__":
    sys.exit(main())
