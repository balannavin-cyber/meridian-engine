#!/usr/bin/env bash
# Refuse to start the feed unless the Zerodha token validates LIVE. Anti-silent-failure guard.
set -o pipefail
cd "${MERDIAN_ENGINE_DIR:-/home/ssm-user/meridian-engine}"   # S100_WSFEED_RETRY: overridable for tests only
set +u
set -a; . ./.env; set +a
set -u
if python3 - <<'PY'
import os, sys
from kiteconnect import KiteConnect
try:
    k = KiteConnect(api_key=os.environ["ZERODHA_API_KEY"])
    k.set_access_token(os.environ["ZERODHA_ACCESS_TOKEN"])
    p = k.profile()
    print("preflight OK:", p.get("user_id"))
    sys.exit(0)
except Exception as e:
    print("preflight FAIL:", e, file=sys.stderr); sys.exit(1)
PY
then
    rm -f logs/WSFEED_FAILED
    exit 0
else
    ts=$(date -u +%FT%TZ)
    # S100_WSFEED_RETRY: the retry timer re-runs this every 5 min while the token is bad -> one page per 30 min.
    WSFEED_DEDUPE_S=1800 bash bin/wsfeed_alert.sh "wsfeed PREFLIGHT FAILED $ts - Zerodha token invalid. Feed NOT started. Fix: refresh_kite_token.py on MALPHA -> sync; the feed retries every 5 min until 15:25 IST (no restart needed)"
    exit 1
fi