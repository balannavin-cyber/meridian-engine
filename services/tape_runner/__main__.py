"""python -m services.tape_runner [--smoke]

Real dependencies (kiteconnect, boto3) are imported here only, lazily, so the offline tests never
need them. Exit codes: 0 done/closed, 1 failure (systemd restarts), 75 spool cap, 78 token/env.
os._exit is used so the twisted reactor thread cannot hold the process open.
"""
import os
import sys
import time

from . import config
from .clock import SystemClock


def _log(msg):
    print("TAPE " + msg, flush=True)


def _env():
    missing = [n for n in config.ENV_REQUIRED if not os.environ.get(n)]
    if missing:
        _log("ENV_MISSING %s" % ",".join(missing))  # names only, never values
        return None
    return os.environ[config.ENV_API_KEY], os.environ[config.ENV_ACCESS_TOKEN]


def _kite(api_key, token):
    from kiteconnect import KiteConnect, KiteTicker  # noqa: lazy, production only
    kite = KiteConnect(api_key=api_key, timeout=15)
    kite.set_access_token(token)

    def ticker_factory():
        return KiteTicker(api_key, token, reconnect=True, reconnect_max_tries=300, reconnect_max_delay=60)
    return kite, ticker_factory


def _s3():
    import boto3  # noqa: lazy, production only
    from botocore.config import Config
    return boto3.client("s3", region_name=os.environ[config.ENV_AWS[2]], config=Config(
        retries={"mode": "standard", "max_attempts": 3}, connect_timeout=5, read_timeout=30))


def main(argv):
    creds = _env()
    if creds is None:
        return config.EXIT_TOKEN_FAIL
    api_key, token = creds
    clock = SystemClock()
    kite, ticker_factory = _kite(api_key, token)
    if "--smoke" in argv:
        from .smoke import run_smoke
        return run_smoke(kite, ticker_factory, clock, wait_s=60)

    from .recorder import Recorder
    rec = Recorder(kite, ticker_factory, _s3(), clock, threaded=True, secrets=(api_key, token), log=_log)
    _log("START pid=%d day=%s bucket=%s" % (os.getpid(), rec.day, rec.bucket))
    try:
        while True:
            code = rec.step(clock.now_ns())
            if code is not None:
                return code
            time.sleep(1.0 - (time.time() % 1.0))
    except Exception as exc:  # noqa: BLE001
        _log("UNHANDLED %s" % type(exc).__name__)
        try:
            rec.writer.flush()
        except Exception:  # noqa: BLE001
            pass
        return config.EXIT_FAIL


if __name__ == "__main__":
    code = main(sys.argv[1:])
    sys.stdout.flush()
    os._exit(code)
