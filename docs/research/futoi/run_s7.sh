#!/bin/sh
# Phase 5: section 7 descriptives.
#
# Two extractions section 7 needs and no earlier phase pulled:
#   (a) SENSEX spot, and the SENSEX chain at each session close   -> item 7.1
#   (b) put-call pairs at the three strikes nearest spot, at every
#       M2 window boundary                                        -> item 7.3
# Both are per-session loops and both are RESUMABLE: a session already present
# in the output file is skipped, so an interrupted run is re-entered, not
# restarted. One query at a time; nothing after 2026-03-30 is read.
#
# EXIT-STATUS DISCIPLINE (A1). /bin/sh has no PIPESTATUS, so NO pipeline carries
# a status anywhere in this script. Each roq call writes its \set prelude plus
# the SQL into a temp file, is invoked with that file as an ARGUMENT (no pipe),
# writes stdout to a second temp file, and has its own rc tested. Rows are
# appended to the output only on rc=0, so a failed or timed-out query can never
# contribute a truncated row set -- it is recorded as
# "QUERY FAILED: <d> rc=<rc>" in the err log instead.
#
# Same gating as M1/M2: --score, self-test and controls.csv re-checked inside
# futoi_s7.py, refusal on STOPPED.md.
#
# Usage:  run_s7.sh [--extract-only]
#           --extract-only  does both extractions, reports coverage, and exits
#                           before the scoring step.
set -eu
cd "$(dirname "$0")/../../.."
ROQ=./bin/roq.sh
D=docs/research/futoi
NIFTY=9992f600-51b3-4009-b487-f878692a0bc5
SENSEX=73a1390a-30c9-46d6-9d3f-5f03c3f5ad71
LO=2025-04-01
HI=2026-03-30
TS=$(date -u +%Y%m%d_%H%M)

EXTRACT_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --extract-only) EXTRACT_ONLY=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

SQLTMP=$(mktemp "${TMPDIR:-/tmp}/s7.sql.XXXXXX")
OUTTMP=$(mktemp "${TMPDIR:-/tmp}/s7.out.XXXXXX")
SEENTMP=$(mktemp "${TMPDIR:-/tmp}/s7.seen.XXXXXX")
cleanup() { rm -f "$SQLTMP" "$OUTTMP" "$SEENTMP"; }
trap cleanup EXIT

echo "=== phase 5: section 7 descriptives ==="
if [ -f "$D/STOPPED.md" ]; then
  echo "STOPPED.md is present -- a control failed. Refusing to run section 7."
  exit 2
fi
if [ ! -s "$D/data/sessions.txt" ]; then
  echo "data/sessions.txt absent -- run the extraction phase first."
  exit 2
fi

# ---- A6: what M2 kept, and proof that column 1 of m2_sessions.csv is the date
echo "--- data/m2_sessions.csv ---"
if [ ! -s "$D/data/m2_sessions.csv" ]; then
  echo "absent -- M2 has not been scored. Refusing: item 7.3 needs its sessions."
  exit 2
fi
echo "wc -l: $(wc -l < "$D/data/m2_sessions.csv")   (1 header + one row per session)"
echo "head -2:"
head -2 "$D/data/m2_sessions.csv" | sed 's/^/    /'
M2COL1=$(head -1 "$D/data/m2_sessions.csv" | cut -d, -f1)
if [ "$M2COL1" != "trade_date" ]; then
  echo "column 1 header is '$M2COL1', not 'trade_date' -- refusing to key on it."
  exit 2
fi
M2FIRST=$(sed -n '2p' "$D/data/m2_sessions.csv" | cut -d, -f1)
case "$M2FIRST" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
  *) echo "column 1 first value '$M2FIRST' is not a YYYY-MM-DD date -- refusing."; exit 2 ;;
esac
echo "column 1 confirmed: header '$M2COL1', first value '$M2FIRST' parses as a date."

# ------------------------------------------------------------- helpers
# run_q <sqlfile> <outfile> <errfile> <label> <prelude>
# A1: no pipeline carries the status; output appended only on rc=0.
run_q() {
  _sql=$1; _out=$2; _err=$3; _label=$4; _prelude=$5
  # '%s\n', not '%s': the caller builds the prelude in a command substitution,
  # which STRIPS trailing newlines, so without this the last \set line would be
  # glued onto the SQL file's first line.
  printf '%s\n' "$_prelude" > "$SQLTMP"
  cat "$_sql" >> "$SQLTMP"
  _rc=0
  "$ROQ" < "$SQLTMP" > "$OUTTMP" 2>>"$_err" || _rc=$?
  if [ "$_rc" -eq 0 ]; then
    tail -n +2 "$OUTTMP" >> "$_out"
    return 0
  fi
  echo "QUERY FAILED: $_label rc=$_rc" >> "$_err"
  return 1
}

# A4: report expected / present / missing for a finished loop.
# Leaves the missing list in $SEENTMP's sibling file $1.missing for the caller.
report_coverage() {
  _exp=$1; _out=$2; _label=$3
  cut -d, -f1 "$_out" | tail -n +2 | sort -u > "$SEENTMP"
  _nexp=$(wc -l < "$_exp")
  _npres=$(wc -l < "$SEENTMP")
  echo "$_label sessions expected:            $_nexp"
  echo "$_label sessions present in output:   $_npres"
  _missing=$(comm -23 "$_exp" "$SEENTMP" || true)
  if [ -n "$_missing" ]; then
    echo "$_label sessions MISSING ($(printf '%s\n' "$_missing" | wc -l)):"
    printf '%s\n' "$_missing" | sed 's/^/    /'
  else
    echo "$_label sessions missing:            none"
  fi
  printf '%s' "$_missing" > "$_out.missing"
}

# ---------------------------------------------------------------- (a) SENSEX
# A2: write to .tmp, promote only on rc=0 AND a non-empty file.
if [ ! -s "$D/data/spot_bars_sensex.csv" ]; then
  echo "--- SENSEX spot bars ---"
  printf "\\set sensex '%s'\n\\set lo '%s'\n\\set hi '%s'\n" "$SENSEX" "$LO" "$HI" > "$SQLTMP"
  cat "$D/sql/extract_spot_sensex.sql" >> "$SQLTMP"
  rc=0
  "$ROQ" < "$SQLTMP" > "$D/data/spot_bars_sensex.csv.tmp" \
      2> "$D/logs/extract_spot_sensex.err" || rc=$?
  if [ "$rc" -eq 0 ] && [ -s "$D/data/spot_bars_sensex.csv.tmp" ]; then
    mv "$D/data/spot_bars_sensex.csv.tmp" "$D/data/spot_bars_sensex.csv"
    echo "SENSEX spot pull promoted."
  else
    echo "SENSEX spot pull failed rc=$rc or produced an empty file; NOT promoted."
    rm -f "$D/data/spot_bars_sensex.csv.tmp"
    exit 3
  fi
fi
echo "SENSEX spot rows: $(( $(wc -l < "$D/data/spot_bars_sensex.csv") - 1 ))"

SXOUT=$D/data/sensex_chain.csv
SXERR=$D/logs/extract_sensex_chain.err
if [ ! -s "$SXOUT" ]; then
  printf 'trade_date,hhmmss,expiry,exp_on_or_after,strike,option_type,oi,iv,r_used\n' > "$SXOUT"
  : > "$SXERR"
fi
echo "--- SENSEX chain at the close, per session (resumable) ---"
n=0
fails=0
while read -r d; do
  if cut -d, -f1 "$SXOUT" | grep -qx "$d"; then
    continue
  fi
  n=$((n+1))
  if run_q "$D/sql/extract_sensex_chain.sql" "$SXOUT" "$SXERR" "$d" \
           "$(printf "\\set sensex '%s'\n\\set d '%s'\n" "$SENSEX" "$d")"; then
    :
  else
    fails=$((fails+1))
  fi
  if [ $((n % 10)) -eq 0 ]; then                     # A3: if/then/fi, not && echo
    echo "  ... $n SENSEX sessions queried (last $d), $fails failed"
  fi
done < "$D/data/sessions.txt"
echo "SENSEX sessions queried this pass:  $n"
echo "SENSEX queries that failed:         $fails"
echo "SENSEX chain rows:                  $(( $(wc -l < "$SXOUT") - 1 ))"
if [ -s "$SXERR" ]; then
  echo "  SENSEX stderr, first 10 lines:"
  head -10 "$SXERR" | sed 's/^/    /'
else
  echo "  SENSEX stderr clean"
fi
# A4: SENSEX coverage is REPORT ONLY. A NIFTY session with no SENSEX chain rows
# is a real absence, not a query failure -- item 7.1 counts and lists them too.
report_coverage "$D/data/sessions.txt" "$SXOUT" "SENSEX"
echo "SENSEX coverage is reported only; a missing session is not an error here."

# ---------------------------------------------------------------- (b) PCP legs
PCOUT=$D/data/pcp_legs.csv
PCERR=$D/logs/extract_pcp_legs.err
if [ ! -s "$PCOUT" ]; then
  printf 'trade_date,hhmmss,expiry,strike,c,p,r_used,spot,rk\n' > "$PCOUT"
  : > "$PCERR"
fi
cut -d, -f1 "$D/data/m2_sessions.csv" | tail -n +2 | sort -u > "$D/data/pcp_sessions.txt"
echo "--- put-call pairs at the 3 strikes nearest spot, per session (resumable) ---"
echo "sessions to cover (the sessions M2 kept): $(wc -l < "$D/data/pcp_sessions.txt")"
n=0
fails=0
while read -r d; do
  if cut -d, -f1 "$PCOUT" | grep -qx "$d"; then
    continue
  fi
  n=$((n+1))
  if run_q "$D/sql/extract_pcp_legs.sql" "$PCOUT" "$PCERR" "$d" \
           "$(printf "\\set nifty '%s'\n\\set d '%s'\n" "$NIFTY" "$d")"; then
    :
  else
    fails=$((fails+1))
  fi
  if [ $((n % 10)) -eq 0 ]; then
    echo "  ... $n PCP sessions queried (last $d), $fails failed"
  fi
done < "$D/data/pcp_sessions.txt"
echo "PCP sessions queried this pass:     $n"
echo "PCP queries that failed:            $fails"
echo "PCP leg rows:                       $(( $(wc -l < "$PCOUT") - 1 ))"
if [ -s "$PCERR" ]; then
  echo "  PCP stderr, first 10 lines:"
  head -10 "$PCERR" | sed 's/^/    /'
else
  echo "  PCP stderr clean"
fi
# A4: every session M2 kept must be present. Item 7.3 compares against M2's own
# windows, so a gap here would silently shrink the comparison.
report_coverage "$D/data/pcp_sessions.txt" "$PCOUT" "PCP"
if [ -s "$PCOUT.missing" ]; then
  echo "REFUSING to score: $(wc -l < "$PCOUT.missing") of the sessions M2 kept have"
  echo "no PCP legs. Item 7.3 would compare a shrunken subset against M2's windows."
  exit 3
fi

# A5
if [ "$EXTRACT_ONLY" -eq 1 ]; then
  echo "extract-only: not scoring"
  exit 0
fi

# ---------------------------------------------------------------- score
echo "--- section 7 descriptives ---"
rc=0
( ulimit -v 700000; python3 "$D/futoi_s7.py" --score ) > "$D/logs/s7_$TS.log" 2>&1 || rc=$?
cat "$D/logs/s7_$TS.log"
echo "s7 exit=$rc"
exit $rc
