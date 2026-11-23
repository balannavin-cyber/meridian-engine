#!/usr/bin/env bash
# MR-PIN2 step 3, STEP 1c/1d. Read-only: every read through bin/roq.sh as merdian_ro.
#
# Per symbol-day, in the fixed order NIFTY by date then SENSEX by date:
#   1. substitute literals into queries/qS_day.sql.tpl   (psql -v does not work via roq)
#   2. plain EXPLAIN (never ANALYZE) -> queries/explain_<sym>_<day>.txt
#   3. gate_explain.py; a FAIL stops the loop, no query is run for that day
#   4. the query itself -> _qS_<sym>_<day>.txt, timed
#   5. sleep 5
# STOP at the FIRST gate failure, roq error, timeout, or any query over 10 s. No retry.
# One line per day appended to _sens_run.log:
#   OK|FAIL|STOP sym day elapsed_s rows s0=<n> s1=<n>
# After the last day, and ONLY if all 24 are OK, 'ALL 24 DONE' is appended to the log
# file itself (not stdout). Step 2 may start only if that is the last line.
#
# The substituted per-day SQL goes to $TMP (session scratch), not into the repo: the
# template plus the symbol/day/iid triple reproduces it exactly.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROQ="$HERE/../../../../../bin/roq.sh"
TPL="$HERE/queries/qS_day.sql.tpl"
LOG="$HERE/_sens_run.log"
TMP="${TMPDIR:-/tmp}"
MAX_S=10

NIFTY_IID=9992f600-51b3-4009-b487-f878692a0bc5
SENSEX_IID=73a1390a-30c9-46d6-9d3f-5f03c3f5ad71

# Day sets fixed here, identical to analyze_partH.py DAYS (and Part B B1).
NIFTY_DAYS="2025-04-01 2025-05-02 2025-06-02 2025-07-01 2025-08-01 2025-09-01 \
2025-10-01 2025-11-03 2025-12-01 2026-01-01 2026-02-01 2026-03-04"
SENSEX_DAYS="2025-04-02 2025-05-02 2025-06-02 2025-07-02 2025-08-01 2025-09-01 \
2025-10-03 2025-11-03 2025-12-01 2026-01-02 2026-02-01 2026-03-02"

# ---- trial gate, recomputed from the plan on disk rather than recalled ----
TRIAL="$HERE/queries/explain_NIFTY_2025-04-01.txt"
if [ -f "$TRIAL" ]; then
  printf 'trial gate NIFTY 2025-04-01: %s\n' \
    "$(PYTHONDONTWRITEBYTECODE=1 python3 -B "$HERE/gate_explain.py" "$TRIAL" 2>&1 \
       | tr '\n' ' ')"
else
  printf 'trial gate NIFTY 2025-04-01: plan file absent\n'
fi

: > "$LOG"
n_ok=0; n_total=0; stopped=0

for sym in NIFTY SENSEX; do
  if [ "$sym" = NIFTY ]; then iid=$NIFTY_IID; days=$NIFTY_DAYS
  else iid=$SENSEX_IID; days=$SENSEX_DAYS; fi

  for d in $days; do
    [ "$stopped" -eq 1 ] && break
    n_total=$((n_total + 1))
    sql="$TMP/qS_${sym}_${d}.sql"
    esql="$TMP/qS_${sym}_${d}_explain.sql"
    plan="$HERE/queries/explain_${sym}_${d}.txt"
    out="$HERE/_qS_${sym}_${d}.txt"

    sed -e "s/__IID__/$iid/g" -e "s/__SYM__/$sym/g" -e "s/__D__/$d/g" "$TPL" > "$sql"
    sed -e 's/^WITH tgt/EXPLAIN WITH tgt/' "$sql" > "$esql"
    if ! grep -q '^EXPLAIN WITH tgt' "$esql"; then
      printf 'STOP %s %s - - explain-prefix-not-applied\n' "$sym" "$d" >> "$LOG"
      stopped=1; break
    fi

    # ---- 1c: EXPLAIN gate, before the query ----
    "$ROQ" "$esql" > "$plan" 2>&1
    if ! PYTHONDONTWRITEBYTECODE=1 python3 -B "$HERE/gate_explain.py" "$plan" \
         > "$TMP/gate_${sym}_${d}.txt" 2>&1; then
      printf 'STOP %s %s - - explain-gate-FAIL: %s\n' "$sym" "$d" \
        "$(tr '\n' ' ' < "$TMP/gate_${sym}_${d}.txt")" >> "$LOG"
      stopped=1; break
    fi

    # ---- 1d: the query, timed ----
    t0=$(date +%s.%N)
    "$ROQ" "$sql" > "$out" 2> "$HERE/_qS_${sym}_${d}.err"
    rc=$?
    t1=$(date +%s.%N)
    el=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.3f", b-a}')
    # grep -c prints 0 AND exits 1 on no match, so `|| echo 0` would print 0 twice.
    s0=$(grep -c '^S0|' "$out" 2>/dev/null); s0=${s0:-0}
    s1=$(grep -c '^S1|' "$out" 2>/dev/null); s1=${s1:-0}
    rows=$((s0 + s1))

    if [ "$rc" -ne 0 ]; then
      printf 'STOP %s %s %s %s s0=%s s1=%s roq-rc=%s\n' \
        "$sym" "$d" "$el" "$rows" "$s0" "$s1" "$rc" >> "$LOG"
      stopped=1; break
    fi
    if [ -s "$HERE/_qS_${sym}_${d}.err" ]; then
      printf 'STOP %s %s %s %s s0=%s s1=%s stderr-not-empty\n' \
        "$sym" "$d" "$el" "$rows" "$s0" "$s1" >> "$LOG"
      stopped=1; break
    fi
    if awk -v e="$el" -v m="$MAX_S" 'BEGIN{exit !(e > m)}'; then
      printf 'STOP %s %s %s %s s0=%s s1=%s over-%ss\n' \
        "$sym" "$d" "$el" "$rows" "$s0" "$s1" "$MAX_S" >> "$LOG"
      stopped=1; break
    fi
    # S0 is one row per target minute, so exactly 3; S1 must carry at least one leg.
    # A day that resolved 2 minutes, or 3 minutes with an empty band, is a FAIL, not a
    # thinner sample silently carried into the gates.
    if [ "$s0" -ne 3 ] || [ "$s1" -eq 0 ]; then
      printf 'FAIL %s %s %s %s s0=%s s1=%s\n' \
        "$sym" "$d" "$el" "$rows" "$s0" "$s1" >> "$LOG"
      stopped=1; break
    fi

    printf 'OK %s %s %s %s s0=%s s1=%s\n' \
      "$sym" "$d" "$el" "$rows" "$s0" "$s1" >> "$LOG"
    n_ok=$((n_ok + 1))
    sleep 5
  done
  [ "$stopped" -eq 1 ] && break
done

# The marker is a COMPUTED result, not a literal: it is appended only when all 24 days
# logged OK. Part H's loop wrote its marker to stdout instead of the log and the
# precondition had to be waived (BLOCKED.txt:249-253); this writes it to the file.
if [ "$n_ok" -eq 24 ] && [ "$stopped" -eq 0 ]; then
  printf 'ALL 24 DONE\n' >> "$LOG"
else
  printf 'INCOMPLETE %s of 24 OK, stopped=%s\n' "$n_ok" "$stopped" >> "$LOG"
fi
printf 'run_sens: %s of %s attempted days OK; log %s\n' "$n_ok" "$n_total" "$LOG"
exit 0
