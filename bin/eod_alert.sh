#!/usr/bin/env bash
# S82-ENH129 -- EOD health-check alert. Deliberately NOT bin/wsfeed_alert.sh:
# that script writes logs/WSFEED_FAILED with `>`, so sharing it would let each
# subsystem silently clobber the other's sentinel and make "is the feed down?"
# unanswerable. Same shape, separate sentinel.
msg="${1:-eod_health_check failure}"
ts=$(date -u +%FT%TZ)
cd /home/ssm-user/meridian-engine || exit 0
line="$ts  ALERT: $msg"
echo "$line" | tee -a logs/EOD_HEALTH_ALERTS.log >&2
echo "$line" > logs/EOD_HEALTH_FAILED
set -a; . ./.env 2>/dev/null; set +a
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  curl -s -m 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" -d chat_id="${TELEGRAM_CHAT_ID}" -d text="[MERDIAN] $msg" >/dev/null || true
fi
exit 0
