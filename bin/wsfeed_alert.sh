#!/usr/bin/env bash
msg="${1:-merdian-wsfeed failure}"
ts=$(date -u +%FT%TZ)
cd /home/ssm-user/meridian-engine || exit 0
line="$ts  ALERT: $msg"
echo "$line" | tee -a logs/WSFEED_ALERTS.log >&2
echo "$line" > logs/WSFEED_FAILED
set -a; . ./.env 2>/dev/null; set +a
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  curl -s -m 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" -d chat_id="${TELEGRAM_CHAT_ID}" -d text="[MERDIAN] $msg" >/dev/null || true
fi
exit 0
