#!/usr/bin/env bash
# Score every non-empty symbol-day, ONE AT A TIME (memory: 1,910 MB, no swap).
# Read-only apart from scored/*.jsonl under replay_v2/. score_v2.py drops every
# per-strike map per run; nothing is held across days.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="$HERE/_score_v2.log"
: > "$LOG"
n=0; bad=0
while read -r st sym d rest; do
  [ "$st" = "OK" ] || continue
  c="$HERE/chain/out_${sym}_${d}.txt"; v="$HERE/vol/outv_${sym}_${d}.txt"
  o="$HERE/scored/${sym}_${d}.jsonl"
  ( ulimit -v 700000; PYTHONDONTWRITEBYTECODE=1 python3 -B "$HERE/score_v2.py" "$c" "$v" ) \
      > "$o" 2> "$HERE/scored/${sym}_${d}.err" < /dev/null
  rc=$?
  r=$(wc -l < "$o")
  if [ "$rc" -ne 0 ] || [ -s "$HERE/scored/${sym}_${d}.err" ]; then
    printf 'FAIL %s %s rc=%s %s\n' "$sym" "$d" "$rc" \
      "$(tr '\n' ' ' < "$HERE/scored/${sym}_${d}.err" | cut -c1-160)" >> "$LOG"
    bad=$((bad+1))
  else
    printf 'OK %s %s runs=%s\n' "$sym" "$d" "$r" >> "$LOG"
    n=$((n+1))
  fi
done < "$HERE/_pull_v2.log"
if [ "$bad" -eq 0 ]; then printf 'SCORED %s DONE\n' "$n" >> "$LOG"
else printf 'SCORING INCOMPLETE ok=%s fail=%s\n' "$n" "$bad" >> "$LOG"; fi
