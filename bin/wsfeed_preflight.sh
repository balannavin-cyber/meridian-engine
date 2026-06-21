#!/usr/bin/env bash
# Refuse to start the feed unless the Zerodha token validates LIVE. Anti-silent-failure guard.
set -o pipefail
cd /home/ssm-user/meridian-engine
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
    bash bin/wsfeed_alert.sh "wsfeed PREFLIGHT FAILED $ts - Zerodha token invalid. Feed NOT started. Fix: refresh_kite_token.py on MALPHA -> sync -> sudo systemctl restart merdian-wsfeed"
    exit 1
fi