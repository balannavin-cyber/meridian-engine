#!/usr/bin/env bash
# lookback_v5 PART 5 -- the data-pull loop. Read-only: every read through bin/roq.sh
# as merdian_ro. Writes nothing outside docs/research/pin_proof/lookback_v5/.
# Modelled on lookback_v4/run_part0a.sh: same stop rules, same stdin handling, same
# COMPUTED finish marker.
#
# Per symbol (NIFTY then SENSEX) and per date in sessions_<SYM>.txt:
#   1. substitute __IID__ __SYM__ __D__   (psql -v does not work via roq)
#   2. plain EXPLAIN, never ANALYZE   -> plans/explain_<SYM>_<day>.txt
#   3. gate_explain.py BY PATH (not copied, not edited); a FAIL stops the run and the
#      query for that day is never issued
#   4. sleep 5
#   5. the query, timed              -> out/_qD_<SYM>_<day>.txt
#   6. sleep 5
#
# STOP, no retry, at the FIRST of: gate FAIL, roq non-zero rc, non-empty stderr, a
# query over MAX_S seconds, or r1 != legs_sum (a row cap). A day with r0 = 0 is logged
# OK_EMPTY and the loop CONTINUES -- an empty day is a finding about the data, not an
# error in the pull, and stopping on it would end the run on the first gap.
#
# r1 != legs_sum is the row-cap guard. n_legs (in R0) and the R1 rows come from the
# same `legs` CTE, so they can only disagree if something truncated the result set.
# That is exactly the failure a transport or client limit produces, and it is silent.
#
# Every python and roq invocation runs under ( ulimit -v 700000 ) per Rule 23 and takes
# stdin from /dev/null: the day loop is a `while read` fed by redirection, so a child
# that read stdin would eat the rest of the day list and the run would end early
# looking merely short.
#
# RESTART SAFETY: refuses to start if out/_pull_run.log exists, unless RESUME=1, in
# which case days already logged OK or OK_EMPTY are skipped and the log is APPENDED.
# Without this a second start would silently truncate the log of a run in progress.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROQ="$HERE/../../../../bin/roq.sh"
GATE="$HERE/../gamma_inputs/sens/gate_explain.py"
TPL="$HERE/sql/qD_day.sql.tpl"
LOG="$HERE/out/_pull_run.log"
MAX_S=10
VLIM=700000

mkdir -p "$HERE/plans" "$HERE/out"

NIFTY_IID=9992f600-51b3-4009-b487-f878692a0bc5
SENSEX_IID=73a1390a-30c9-46d6-9d3f-5f03c3f5ad71

RESUME="${RESUME:-0}"
if [ -e "$LOG" ] && [ "$RESUME" != "1" ]; then
  printf 'run_pull: %s already exists. Refusing to start.\n' "$LOG" >&2
  printf '  Re-run with RESUME=1 to skip days already logged OK/OK_EMPTY and append.\n' >&2
  exit 2
fi

DONE="$HERE/out/_pull_done.txt"
: > "$DONE"
if [ "$RESUME" = "1" ] && [ -e "$LOG" ]; then
  awk '$1=="OK"||$1=="OK_EMPTY"{print $2"_"$3}' "$LOG" | sort -u > "$DONE"
  printf 'RESUME: %s day(s) already complete, skipping those\n' "$(wc -l < "$DONE")" \
    >> "$LOG"
else
  : > "$LOG"
fi

n_total=0
for sym in NIFTY SENSEX; do
  n_total=$(( n_total + $(wc -l < "$HERE/sessions_${sym}.txt") ))
done

n_ok=0; n_empty=0; n_skip=0; n_try=0; stopped=0
start_all=$(date +%s)

for sym in NIFTY SENSEX; do
  [ "$stopped" -eq 1 ] && break
  if [ "$sym" = NIFTY ]; then iid=$NIFTY_IID; else iid=$SENSEX_IID; fi

  while read -r d; do
    [ "$stopped" -eq 1 ] && break
    [ -z "${d:-}" ] && continue
    if grep -qxF "${sym}_${d}" "$DONE" 2>/dev/null; then
      n_skip=$((n_skip + 1)); continue
    fi
    n_try=$((n_try + 1))
    sql="$HERE/out/_qD_${sym}_${d}.sql"
    esql="$HERE/out/_qD_${sym}_${d}_explain.sql"
    plan="$HERE/plans/explain_${sym}_${d}.txt"
    out="$HERE/out/_qD_${sym}_${d}.txt"
    err="$HERE/out/_qD_${sym}_${d}.err"

    sed -e "s/__IID__/$iid/g" -e "s/__SYM__/$sym/g" -e "s/__D__/$d/g" "$TPL" > "$sql"
    sed -e 's/^WITH tgt AS/EXPLAIN WITH tgt AS/' "$sql" > "$esql"
    if ! grep -q '^EXPLAIN WITH tgt AS' "$esql"; then
      printf 'STOP %s %s - r0=- r1=- legs_sum=- explain-prefix-not-applied\n' \
        "$sym" "$d" >> "$LOG"
      stopped=1; break
    fi

    # ---- EXPLAIN gate, BEFORE the query ----
    ( ulimit -v "$VLIM"; "$ROQ" "$esql" ) > "$plan" 2>&1 < /dev/null
    if ! ( ulimit -v "$VLIM"; PYTHONDONTWRITEBYTECODE=1 python3 -B "$GATE" "$plan" ) \
         > "$HERE/out/_gate_${sym}_${d}.txt" 2>&1 < /dev/null; then
      printf 'STOP %s %s - r0=- r1=- legs_sum=- explain-gate-FAIL: %s\n' "$sym" "$d" \
        "$(tr '\n' ' ' < "$HERE/out/_gate_${sym}_${d}.txt")" >> "$LOG"
      stopped=1; break
    fi

    sleep 5

    # ---- the query, timed ----
    t0=$(date +%s.%N)
    ( ulimit -v "$VLIM"; "$ROQ" "$sql" ) > "$out" 2> "$err" < /dev/null
    rc=$?
    t1=$(date +%s.%N)
    el=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.3f", b-a}')
    r0=$(grep -c '^R0|' "$out" 2>/dev/null); r0=${r0:-0}
    r1=$(grep -c '^R1|' "$out" 2>/dev/null); r1=${r1:-0}
    ls=$( ( ulimit -v "$VLIM"; PYTHONDONTWRITEBYTECODE=1 python3 -B -c "
import json,sys
t=0
for l in open(sys.argv[1]):
    if l.startswith('R0|'):
        t += json.loads(l.split('|',1)[1])['n_legs']
print(t)
" "$out" ) 2>/dev/null < /dev/null )
    ls=${ls:-ERR}

    if [ "$rc" -ne 0 ]; then
      printf 'STOP %s %s %s r0=%s r1=%s legs_sum=%s roq-rc=%s: %s\n' "$sym" "$d" \
        "$el" "$r0" "$r1" "$ls" "$rc" \
        "$(tr '\n' ' ' < "$err" | cut -c1-200)" >> "$LOG"
      stopped=1; break
    fi
    if [ -s "$err" ]; then
      printf 'STOP %s %s %s r0=%s r1=%s legs_sum=%s stderr-not-empty: %s\n' "$sym" \
        "$d" "$el" "$r0" "$r1" "$ls" \
        "$(tr '\n' ' ' < "$err" | cut -c1-200)" >> "$LOG"
      stopped=1; break
    fi
    if awk -v e="$el" -v m="$MAX_S" 'BEGIN{exit !(e > m)}'; then
      printf 'STOP %s %s %s r0=%s r1=%s legs_sum=%s over-%ss\n' "$sym" "$d" "$el" \
        "$r0" "$r1" "$ls" "$MAX_S" >> "$LOG"
      stopped=1; break
    fi
    if [ "$r1" != "$ls" ]; then
      printf 'STOP %s %s %s r0=%s r1=%s legs_sum=%s row-cap-r1!=legs_sum\n' "$sym" \
        "$d" "$el" "$r0" "$r1" "$ls" >> "$LOG"
      stopped=1; break
    fi

    if [ "$r0" -eq 0 ]; then
      printf 'OK_EMPTY %s %s %s r0=%s r1=%s legs_sum=%s\n' "$sym" "$d" "$el" \
        "$r0" "$r1" "$ls" >> "$LOG"
      n_empty=$((n_empty + 1))
    else
      printf 'OK %s %s %s r0=%s r1=%s legs_sum=%s\n' "$sym" "$d" "$el" \
        "$r0" "$r1" "$ls" >> "$LOG"
      n_ok=$((n_ok + 1))
    fi
    sleep 5
  done < "$HERE/sessions_${sym}.txt"
done

# The marker is COMPUTED against the full day count, never a literal: it appears only
# when every day of both symbols is accounted for as OK, OK_EMPTY or a resumed skip.
n_acc=$((n_ok + n_empty + n_skip))
if [ "$n_acc" -eq "$n_total" ] && [ "$stopped" -eq 0 ]; then
  printf 'ALL %s DONE\n' "$n_total" >> "$LOG"
else
  printf 'INCOMPLETE %s of %s accounted (ok=%s empty=%s skipped=%s attempted=%s stopped=%s)\n' \
    "$n_acc" "$n_total" "$n_ok" "$n_empty" "$n_skip" "$n_try" "$stopped" >> "$LOG"
fi
printf 'run_pull: ok=%s empty=%s skipped=%s of %s days in %ss; log %s\n' \
  "$n_ok" "$n_empty" "$n_skip" "$n_total" "$(( $(date +%s) - start_all ))" "$LOG"
exit 0
