#!/usr/bin/env bash
# =====================================================================
# run_day.sh <YYYY-MM-DD> -- produce the pin monitor's line for one day.
#
# Read-only. Everything it writes stays under this directory. It holds the
# three refusals and runs the self-test first; the reading is
# pin_monitor_day.py's and the measure is pin_monitor_lib.py's.
#
# REFUSALS, in order:
#   R-a  a date before 2026-11-25, or not a real canonical date (PREREG:
#        forward only, no back-fill)
#   R-b  a date already present in pin_monitor.csv (one line per symbol-day,
#        never rewritten)
#   R-c  before 16:30 IST of that date -- the 15:29 bar is the CAS settled
#        close written by capture_cas_close.py on cron 16:20 IST (ADR-022;
#        operator ruling R3, which replaces the PREREG's 15:40)
#   R-d  a failing self-test (PREREG: re-run whenever the script changes)
#
# "Already recorded" is checked BEFORE "too early" so that both refusals can be
# exercised without a clock override: the earlier order left R-b unreachable on
# any date R-c already refuses. A refusal that cannot be made to fire is not a
# refusal (CLAUDE.md rule 0).
#
# PIN_MONITOR_CSV_FOR_TEST overrides the csv path. It exists ONLY so the R-b
# refusal can be exercised against a scratch file instead of the real register.
# While it is set the script is INCAPABLE of measuring anything: it runs the
# three date refusals, prints "TEST MODE: refusals only" and exits before the
# self-test, before any database read and before any write, and it declines
# --explain as well. So the hook can only ever refuse more, never less.
#
# Every run is under `ulimit -v 700000` with python3 -B and no .pyc, and the
# whole run is tee'd to a log, because terminal scrollback is not an archive.
#
# AFTER the tee pipeline closes, it writes the day folder's SHA256SUMS over
# every file there except SHA256SUMS -- the completed log included -- and then
# verifies it with `sha256sum -c`, printing the OK and FAILED counts. The
# manifest cannot be built by the reader: tee still holds the log open at that
# point, so the log would be hashed mid-write and the verify would fail daily.
#
# usage:  ./run_day.sh 2026-11-25
#         ./run_day.sh --explain      the plain EXPLAIN gate, reads no rows
# =====================================================================
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

# TEST MODE: the hook can only narrow what this script may do -- see the header.
if [ -n "${PIN_MONITOR_CSV_FOR_TEST:-}" ]; then
  TEST_MODE=1
  CSV="$PIN_MONITOR_CSV_FOR_TEST"
else
  TEST_MODE=0
  CSV="$HERE/pin_monitor.csv"
fi

FIRST_DAY="2026-11-25"
NOT_BEFORE="16:30:00"
VLIMIT=700000

die() { printf 'run_day: REFUSED -- %s\n' "$*" >&2; exit 2; }

[ $# -eq 1 ] || die "usage: run_day.sh <YYYY-MM-DD> | --explain"

run_selftest() {
  printf 'run_day: self-test\n'
  ( ulimit -v "$VLIMIT"
    cd "$HERE"
    PYTHONDONTWRITEBYTECODE=1 python3 -B selftest_pin_monitor.py
  ) || die "self-test FAILED -- no day is measured until it passes"
}

if [ "$1" = "--explain" ]; then
  if [ "$TEST_MODE" -eq 1 ]; then
    die "PIN_MONITOR_CSV_FOR_TEST is set, so this run may only check refusals;
     --explain opens a database connection. Unset the variable to gate plans."
  fi
  run_selftest
  ( ulimit -v "$VLIMIT"
    cd "$HERE"
    PYTHONDONTWRITEBYTECODE=1 python3 -B pin_monitor_day.py --explain
  )
  exit $?
fi

DAY="$1"

# ---- R-a: shape, and not before the first recorded day
printf '%s' "$DAY" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' \
  || die "date must be YYYY-MM-DD, got '$DAY'"
# date -d validates the calendar (2026-11-31 is rejected here, not later)
date -d "$DAY" +%F >/dev/null 2>&1 || die "'$DAY' is not a real date"
[ "$(date -d "$DAY" +%F)" = "$DAY" ] || die "'$DAY' is not a canonical date"
if [ "$DAY" \< "$FIRST_DAY" ]; then
  die "$DAY is before the first recorded day $FIRST_DAY -- the monitor is forward only"
fi

# ---- R-b: not already recorded
if [ -f "$CSV" ] && cut -d, -f1 "$CSV" | grep -qx "$DAY"; then
  die "$DAY is already in $(basename "$CSV") -- a recorded day is never rewritten"
fi

# ---- R-c: not before 16:30 IST of that date.
# ISO timestamps compare correctly as strings, so no arithmetic is needed.
NOW_IST="$(TZ=Asia/Kolkata date +%Y-%m-%dT%H:%M:%S)"
GATE="${DAY}T${NOT_BEFORE}"
if [ "$NOW_IST" \< "$GATE" ]; then
  die "it is $NOW_IST IST; this day may not be measured before $GATE IST
     (the 15:29 bar is the CAS settled close, cron 16:20 IST)"
fi

# ---- TEST MODE stops here: refusals checked, nothing measured.
if [ "$TEST_MODE" -eq 1 ]; then
  printf 'run_day: TEST MODE: refusals only -- PIN_MONITOR_CSV_FOR_TEST=%s\n' "$CSV"
  printf 'run_day: %s passed R-a, R-b and R-c. No self-test, no database read, no write.\n' "$DAY"
  exit 0
fi

# ---- R-d
run_selftest

mkdir -p "$HERE/$DAY"
LOG="$HERE/$DAY/run_day_$(TZ=Asia/Kolkata date +%Y%m%d_%H%M).log"
printf 'run_day: %s  (now %s IST)  log %s\n' "$DAY" "$NOW_IST" "$(basename "$LOG")"

set +e
( ulimit -v "$VLIMIT"
  cd "$HERE"
  PYTHONDONTWRITEBYTECODE=1 python3 -B pin_monitor_day.py "$DAY"
) 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}
set -e

# ---- the day folder's manifest, built AFTER the tee pipeline has closed.
# Doing this inside the reader would hash this log while tee still held it open,
# so `sha256sum -c` would fail on the log on every single day. The completed log
# is included; SHA256SUMS itself is not. Built even when the reader failed, so
# whatever partial raw reads exist are still fixed to a hash.
MANIFEST_RC=0
if [ -d "$HERE/$DAY" ]; then
  (
    cd "$HERE/$DAY"
    find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%P\n' \
      | LC_ALL=C sort | tr '\n' '\0' | xargs -0 -r sha256sum > SHA256SUMS
  )
  CHECK="$(cd "$HERE/$DAY" && sha256sum -c SHA256SUMS 2>&1)" || MANIFEST_RC=1
  NOK=$(printf '%s\n' "$CHECK" | grep -c ': OK$'    || true)
  NBAD=$(printf '%s\n' "$CHECK" | grep -c ': FAILED' || true)
  printf 'run_day: SHA256SUMS %s OK, %s FAILED\n' "$NOK" "$NBAD"
  if [ "$NBAD" -ne 0 ] || [ "$MANIFEST_RC" -ne 0 ]; then
    printf '%s\n' "$CHECK" | grep ': FAILED' >&2 || true
    printf 'run_day: MANIFEST VERIFY FAILED -- the day folder is not fixed to a hash\n' >&2
    if [ "$RC" -eq 0 ]; then RC=4; fi   # an `&& RC=4` would exit under set -e
  fi
fi

printf 'run_day: exit %s\n' "$RC"
exit "$RC"
