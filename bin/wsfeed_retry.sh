#!/usr/bin/env bash
# S100_WSFEED_RETRY (ruling S100-F; TD-S80-NEW-17). Run by merdian-wsfeed-retry.timer every 5 min, Mon-Fri.
# merdian-wsfeed.service gives up after StartLimitBurst=3 preflight failures ~10 s apart (measured 10-15 and
# 10-19: 03:40:03-03:40:26 UTC, then never again that session). Between 03:45 and 09:55 UTC this starts it
# again if it is not active, so a Kite token fixed mid-morning starts the feed within 5 min, with no manual
# restart. Outside that band it does nothing: before 03:45 the 03:40 timer owns the start; from 10:00 the
# 10:05 stop timer owns the end. The preflight still decides whether the feed runs; this only re-asks.
set -u
cd "${MERDIAN_ENGINE_DIR:-/home/ssm-user/meridian-engine}" || exit 0
hhmm=$((10#$(date -u +%H%M)))
if [ "$hhmm" -lt 345 ] || [ "$hhmm" -ge 1000 ]; then exit 0; fi
if systemctl is-active --quiet merdian-wsfeed.service; then exit 0; fi
echo "$(date -u +%FT%TZ)  retry: merdian-wsfeed not active -> reset-failed + start" >> logs/WSFEED_RETRY.log
systemctl reset-failed merdian-wsfeed.service >/dev/null 2>&1 || true
systemctl start --no-block merdian-wsfeed.service >> logs/WSFEED_RETRY.log 2>&1 || true
exit 0
