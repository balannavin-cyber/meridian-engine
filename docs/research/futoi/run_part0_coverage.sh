#!/bin/sh
# Part 0 step 3 driver: per-month chain coverage, one month per query.
set -eu
cd "$(dirname "$0")/../../.."
ROQ=./bin/roq.sh
NIFTY=9992f600-51b3-4009-b487-f878692a0bc5
OUT=docs/research/futoi/data/part0_coverage_chain.csv
: > "$OUT"
first=1
for ym in 2025-04 2025-05 2025-06 2025-07 2025-08 2025-09 2025-10 2025-11 2025-12 2026-01 2026-02 2026-03; do
  lo="$ym-01"
  hi=$(date -d "$lo +1 month -1 day" +%F)
  [ "$ym" = "2026-03" ] && hi=2026-03-30     # window ends 2026-03-30 (prereg §2)
  [ "$ym" = "2025-04" ] && lo=2025-04-01
  res=$( { printf "\\set nifty '%s'\n\\set ym '%s'\n\\set lo '%s'\n\\set hi '%s'\n" "$NIFTY" "$ym" "$lo" "$hi"; \
           cat docs/research/futoi/sql/part0_coverage_chain.sql; } | "$ROQ" )
  if [ $first -eq 1 ]; then printf '%s\n' "$res" >> "$OUT"; first=0
  else printf '%s\n' "$res" | tail -n +2 >> "$OUT"; fi
  printf '%s\n' "$res" | tail -n +2
done
