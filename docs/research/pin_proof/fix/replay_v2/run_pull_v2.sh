#!/usr/bin/env bash
# Pin live replay v2 -- pull chain + volatility for every weekday 2026-08-25..2026-11-20,
# both symbols. Read-only; every read through bin/roq.sh as merdian_ro.
# Writes nothing outside fix/replay_v2/ (except that it READS the v1 pulls on disk).
#
# Both query shapes are already EXPLAIN-gated with literal bounds:
#   chain  fix/replay/sql/qR_day.sql.tpl   (gated in v1)
#   vol    replay_v2/sql/qV_day.sql.tpl    (gated in step 1, plan in sql/_t_qV_plan.txt)
# so they are not re-gated per day.
#
# One symbol-day per query, sleep 5 before EVERY query, STOP at the first error or any
# query over MAX_S seconds, no retry. A weekday with ZERO runs is logged OK_EMPTY and
# does NOT stop the loop. stdin is /dev/null on every child: the day loop is a
# `while read` fed by redirection.
#
# Chain pulls already on disk from v1 / the added day (2026-11-16..20, both symbols) are
# REUSED, not re-queried; each is verified non-empty and logged with reuse=chain.
#
# Marker is COMPUTED: ALL 128 DONE only when every one of the 64 weekdays x 2 symbols
# logged OK or OK_EMPTY.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROQ="$HERE/../../../../../bin/roq.sh"
TPL_C="$HERE/../replay/sql/qR_day.sql.tpl"
TPL_V="$HERE/sql/qV_day.sql.tpl"
V1DIR="$HERE/../replay"
ADDDIR="$HERE/../replay/added_2026-11-20"
LOG="$HERE/_pull_v2.log"
MAX_S=10
VLIM=700000

mkdir -p "$HERE/sql" "$HERE/chain" "$HERE/vol"

[ -x "$ROQ" ] || { echo "roq not executable at $ROQ" >&2; exit 2; }

# ---- day list: weekdays only, computed, never hand-listed ----
( ulimit -v "$VLIM"; PYTHONDONTWRITEBYTECODE=1 python3 -B -c "
from datetime import date, timedelta
d, b = date(2026,8,25), date(2026,11,20)
while d <= b:
    if d.weekday() < 5:
        print(d.isoformat(), (d+timedelta(days=1)).isoformat())
    d += timedelta(days=1)
" ) < /dev/null > "$HERE/_days_v2.txt"
NDAYS=$(wc -l < "$HERE/_days_v2.txt")
NEXP=$((NDAYS * 2))

: > "$LOG"
printf 'weekdays=%s symbol-days=%s\n' "$NDAYS" "$NEXP" >> "$LOG"

n_ok=0; n_empty=0; stopped=0
start=$(date +%s)

run_one () {            # $1 sym  $2 day  $3 day+1
  local sym="$1" d="$2" d1="$3"
  local csql="$HERE/sql/_c_${sym}_${d}.sql" vsql="$HERE/sql/_v_${sym}_${d}.sql"
  local cout="$HERE/chain/out_${sym}_${d}.txt" vout="$HERE/vol/outv_${sym}_${d}.txt"
  local cerr="$HERE/chain/out_${sym}_${d}.err" verr="$HERE/vol/outv_${sym}_${d}.err"
  local reuse="" el_c="-" el_v="-" r0=0 v0=0

  # ---- chain: reuse a v1 pull if one exists and is non-empty ----
  local src=""
  [ -s "$V1DIR/out_${sym}_${d}.txt" ] && src="$V1DIR/out_${sym}_${d}.txt"
  [ -s "$ADDDIR/out_${sym}_${d}.txt" ] && src="$ADDDIR/out_${sym}_${d}.txt"
  if [ -n "$src" ]; then
    cp -p "$src" "$cout"
    reuse="reuse=chain"
    r0=$(grep -c '^R0|' "$cout" 2>/dev/null); r0=${r0:-0}
  else
    sed -e "s/__SYM__/$sym/g" -e "s/__D__/$d/g" -e "s/__D1__/$d1/g" "$TPL_C" > "$csql"
    sleep 5
    local t0 t1
    t0=$(date +%s.%N)
    ( ulimit -v "$VLIM"; "$ROQ" "$csql" ) > "$cout" 2> "$cerr" < /dev/null
    local rc=$?
    t1=$(date +%s.%N)
    el_c=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.3f", b-a}')
    r0=$(grep -c '^R0|' "$cout" 2>/dev/null); r0=${r0:-0}
    if [ "$rc" -ne 0 ] || [ -s "$cerr" ]; then
      printf 'STOP %s %s chain rc=%s %s\n' "$sym" "$d" "$rc" \
        "$(tr '\n' ' ' < "$cerr" | cut -c1-160)" >> "$LOG"; return 1
    fi
    if awk -v e="$el_c" -v m="$MAX_S" 'BEGIN{exit !(e > m)}'; then
      printf 'STOP %s %s chain over-%ss el=%s\n' "$sym" "$d" "$MAX_S" "$el_c" >> "$LOG"
      return 1
    fi
  fi

  # ---- volatility: always pulled (skip only if already on disk, non-empty) ----
  if [ -s "$vout" ]; then
    v0=$(grep -c '^V0|' "$vout" 2>/dev/null); v0=${v0:-0}
    reuse="${reuse:+$reuse,}reuse=vol"
  else
    sed -e "s/__SYM__/$sym/g" -e "s/__D__/$d/g" -e "s/__D1__/$d1/g" "$TPL_V" > "$vsql"
    sleep 5
    local t2 t3
    t2=$(date +%s.%N)
    ( ulimit -v "$VLIM"; "$ROQ" "$vsql" ) > "$vout" 2> "$verr" < /dev/null
    local rc2=$?
    t3=$(date +%s.%N)
    el_v=$(awk -v a="$t2" -v b="$t3" 'BEGIN{printf "%.3f", b-a}')
    v0=$(grep -c '^V0|' "$vout" 2>/dev/null); v0=${v0:-0}
    if [ "$rc2" -ne 0 ] || [ -s "$verr" ]; then
      printf 'STOP %s %s vol rc=%s %s\n' "$sym" "$d" "$rc2" \
        "$(tr '\n' ' ' < "$verr" | cut -c1-160)" >> "$LOG"; return 1
    fi
    if awk -v e="$el_v" -v m="$MAX_S" 'BEGIN{exit !(e > m)}'; then
      printf 'STOP %s %s vol over-%ss el=%s\n' "$sym" "$d" "$MAX_S" "$el_v" >> "$LOG"
      return 1
    fi
  fi

  # A weekday with zero runs is a finding, not an error.
  if [ "$r0" -eq 0 ]; then
    printf 'OK_EMPTY %s %s r0=0 v0=%s c=%s v=%s %s\n' "$sym" "$d" "$v0" "$el_c" \
      "$el_v" "$reuse" >> "$LOG"
    n_empty=$((n_empty + 1)); return 0
  fi
  printf 'OK %s %s r0=%s v0=%s c=%s v=%s %s\n' "$sym" "$d" "$r0" "$v0" "$el_c" \
    "$el_v" "$reuse" >> "$LOG"
  n_ok=$((n_ok + 1)); return 0
}

while read -r d d1; do
  [ "$stopped" -eq 1 ] && break
  [ -z "${d:-}" ] && continue
  for sym in NIFTY SENSEX; do
    [ "$stopped" -eq 1 ] && break
    run_one "$sym" "$d" "$d1" || { stopped=1; break; }
  done
done < "$HERE/_days_v2.txt"

n_acc=$((n_ok + n_empty))
if [ "$n_acc" -eq "$NEXP" ] && [ "$stopped" -eq 0 ]; then
  printf 'ALL %s DONE\n' "$NEXP" >> "$LOG"
else
  printf 'INCOMPLETE %s of %s accounted (ok=%s empty=%s stopped=%s)\n' \
    "$n_acc" "$NEXP" "$n_ok" "$n_empty" "$stopped" >> "$LOG"
fi
printf 'run_pull_v2: ok=%s empty=%s of %s in %ss\n' "$n_ok" "$n_empty" "$NEXP" \
  "$(( $(date +%s) - start ))"
exit 0
