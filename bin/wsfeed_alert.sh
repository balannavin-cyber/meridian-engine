#!/usr/bin/env bash
# S100_WSFEED_RETRY (ruling S100-F): optional dedupe. With WSFEED_DEDUPE_S set (the preflight and the OnFailure
# unit set 1800), a Telegram send happens at most once per that many seconds, keyed on its OWN stamp file
# logs/.wsfeed_alert_sent -- not on logs/WSFEED_FAILED, which other callers (bin/disk_guard.sh) also write.
# Without it (disk_guard), behaviour is unchanged: every call sends. The log line and the sentinel are always
# written, so a suppressed alert is still on disk.
msg="${1:-merdian-wsfeed failure}"
ts=$(date -u +%FT%TZ)
cd "${MERDIAN_ENGINE_DIR:-/home/ssm-user/meridian-engine}" || exit 0
line="$ts  ALERT: $msg"
echo "$line" | tee -a logs/WSFEED_ALERTS.log >&2
echo "$line" > logs/WSFEED_FAILED
if [ -n "${WSFEED_DEDUPE_S:-}" ] && [ -f logs/.wsfeed_alert_sent ]; then
  age=$(( $(date +%s) - $(stat -c %Y logs/.wsfeed_alert_sent) ))
  if [ "$age" -lt "$WSFEED_DEDUPE_S" ]; then
    echo "$ts  SUPPRESSED (last send ${age}s ago < ${WSFEED_DEDUPE_S}s): $msg" >> logs/WSFEED_ALERTS.log
    exit 0
  fi
fi
set -a; . ./.env 2>/dev/null; set +a
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  [ -n "${WSFEED_DEDUPE_S:-}" ] && touch logs/.wsfeed_alert_sent
  curl -s -m 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" -d chat_id="${TELEGRAM_CHAT_ID}" -d text="[MERDIAN] $msg" >/dev/null || true
fi
exit 0
