#!/usr/bin/env bash
# freeze_market_ticks.sh — S90 / AM-1 sidecar (TD-S90-NEW-4, roadmap testing harness).
#
# WHY: market_ticks is pruned by pg_cron jobid 46 (`*/30 * * * 1-5`,
#   DELETE ... WHERE ts < now() - interval '1 hour'; Deployment Topology §S75),
#   so at any moment the table holds roughly the last 60-90 minutes and nothing
#   tick-based (WCB, breadth) can be replayed or tested after the fact.
#   This copies the ticks to gzipped CSV chunks on the box before they are pruned.
#
# WHAT: every run exports ticks with ts in [previous end, now - 1 min) via
#   bin/roq.sh (merdian_ro, read-only, 30 s statement timeout) to
#   $TICK_FIXTURE_DIR/<IST date>/ticks_<HHMM>_<HHMM>.csv.gz and logs one line.
#   The window never starts more than 65 minutes back (older rows are already
#   pruned); when it has to be clipped, the log line says gap=1.
#
# RISK CLASS: SC. Read-only on the database; writes only its own files.
#   Off switch: comment out its crontab line. Retention: 10 days of directories.
#
# CRON (UTC): */5 3-10 * * 1-5  (09:00-16:15 IST, inside jobid 46's 60-minute horizon)
set -euo pipefail

HERE=$(cd "$(dirname "$0")/.." && pwd)
ROQ=${ROQ:-$HERE/bin/roq.sh}
ROOT=${TICK_FIXTURE_DIR:-$HOME/merdian_fixtures/ticks}
STATE=$ROOT/.last_end
mkdir -p "$ROOT"

now_s=$(date -u +%s)
end_s=$(( (now_s - 60) / 60 * 60 ))
floor_s=$(( end_s - 65 * 60 ))
start_s=$floor_s
gap=0
if [ -f "$STATE" ]; then
  prev=$(cat "$STATE")
  if [ "$prev" -ge "$floor_s" ] 2>/dev/null; then start_s=$prev
  elif [ "$(TZ=Asia/Kolkata date -d "@$prev" +%F 2>/dev/null)" = "$(TZ=Asia/Kolkata date -d "@$end_s" +%F)" ]; then gap=1  # same IST day: ticks between prev and floor were pruned unseen
  fi
fi
[ "$start_s" -lt "$end_s" ] || { echo "$(date -u +%FT%TZ) nothing to do (start >= end)"; exit 0; }

iso() { date -u -d "@$1" +%Y-%m-%dT%H:%M:%SZ; }
ist() { TZ=Asia/Kolkata date -d "@$1" "$2"; }
day=$(ist "$end_s" +%F)
dir=$ROOT/$day
mkdir -p "$dir"
f=$dir/ticks_$(ist "$start_s" +%H%M)_$(ist "$end_s" +%H%M).csv

{
  printf '\\pset pager off\n\\pset format csv\n\\pset footer off\n'
  printf "SELECT * FROM public.market_ticks WHERE ts >= '%s' AND ts < '%s' ORDER BY id;\n" "$(iso "$start_s")" "$(iso "$end_s")"
} | "$ROQ" > "$f.tmp"

rows=$(( $(wc -l < "$f.tmp") - 1 ))
[ "$rows" -lt 0 ] && rows=0
gzip -9c "$f.tmp" > "$f.gz"
rm -f "$f.tmp"
echo "$end_s" > "$STATE"
echo "$(date -u +%FT%TZ) window=$(iso "$start_s")..$(iso "$end_s") rows=$rows bytes=$(wc -c < "$f.gz") gap=$gap file=$f.gz"

find "$ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +10 -exec rm -rf {} +
