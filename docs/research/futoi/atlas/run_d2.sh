#!/bin/sh
# Study D2 extraction: OI at the wall strike over the 30 minutes before the
# approach. Band 0.15 % only. ONE QUERY PER APPROACH LEG (79 legs), each with
# its own window (approach_min-30, approach_min] and only that leg's strike and
# option type -- a call wall is read as CE, a put wall as PE.
#
# roq.sh is fed on STDIN, one session per query, at the pinned 30 s
# statement_timeout, never raised. No pipeline carries an exit status: each
# query's SQL is built into a temp file, roq's own rc is tested, and rows are
# appended only on rc=0. A failed or timed-out query is recorded as
# "QUERY FAILED: <label> rc=<rc>" in the err log and contributes nothing.
#
# Resumable: a leg already present in the output (trade_date + option_type +
# strike) is skipped.
set -eu
cd "$(dirname "$0")"
ROQ=../../../../bin/roq.sh
NIFTY=9992f600-51b3-4009-b487-f878692a0bc5
BAND=0.15
OUT=data/d2_wall_oi_${BAND}.csv
ERR=logs/extract_d2_${BAND}.err
SQL=sql/extract_wall_oi_d2.sql
ARGS=logs/.d2_args_${BAND}.txt

[ -x "$ROQ" ] || { echo "roq.sh not found at $ROQ"; exit 2; }
if [ ! -s "$OUT" ]; then
  printf 'trade_date,win_from,approach_min,expiry,option_type,strike,bars,oi_first,oi_last,d_oi_wall_30\n' > "$OUT"
  : > "$ERR"
fi

# one line per approach leg: date|expiry|kcall|kput|side|opt|strike|t0|t1
python3 - "$BAND" > "$ARGS" <<'PY'
import csv, sys
band = sys.argv[1]
walls = {r["trade_date"]: r for r in csv.DictReader(open("data/walls.csv"))}
rows = [r for r in csv.DictReader(open("data/approaches_%s.csv" % band))
        if r["approached"] == "True"]
for r in sorted(rows, key=lambda x: (x["trade_date"], x["side"])):
    w = walls[r["trade_date"]]
    m = int(r["approach_min"])
    if r["side"] == "call":
        kc, kp, opt, k = w["call_wall"], -1, "CE", w["call_wall"]
    else:
        kc, kp, opt, k = -1, w["put_wall"], "PE", w["put_wall"]
    print("%s|%s|%s|%s|%s|%s|%s|%02d:%02d:59|%02d:%02d:59"
          % (r["trade_date"], w["expiry"], kc, kp, r["side"], opt, k,
             (m - 30) // 60, (m - 30) % 60, m // 60, m % 60))
PY

TOTAL=$(wc -l < "$ARGS")
echo "approach legs at band ${BAND} %: $TOTAL"

TMP=$(mktemp "${TMPDIR:-/tmp}/d2.sql.XXXXXX")
RES=$(mktemp "${TMPDIR:-/tmp}/d2.out.XXXXXX")
cleanup() { rm -f "$TMP" "$RES"; }
trap cleanup EXIT

n=0; done_n=0; fail=0; skip=0
while IFS='|' read -r D EXP KC KP SIDE OPT K T0 T1; do
  n=$((n+1))
  if awk -F, -v d="$D" -v o="$OPT" 'NR>1 && $1==d && $5==o {found=1} END {exit !found}' "$OUT"; then
    skip=$((skip+1)); continue
  fi
  printf "\\set nifty '%s'\n\\set d '%s'\n\\set expiry '%s'\n\\set kcall '%s'\n\\set kput '%s'\n\\set t0 '%s'\n\\set t1 '%s'\n" \
         "$NIFTY" "$D" "$EXP" "$KC" "$KP" "$T0" "$T1" > "$TMP"
  cat "$SQL" >> "$TMP"
  rc=0
  "$ROQ" < "$TMP" > "$RES" 2>>"$ERR" || rc=$?
  if [ "$rc" -eq 0 ]; then
    tail -n +2 "$RES" >> "$OUT"
    done_n=$((done_n+1))
  else
    echo "QUERY FAILED: $D $OPT $K rc=$rc" >> "$ERR"
    fail=$((fail+1))
  fi
  if [ $((n % 10)) -eq 0 ]; then
    echo "  ... $n/$TOTAL legs ($done_n ok, $fail failed, $skip skipped) last $D $OPT"
  fi
done < "$ARGS"

echo "legs queried this pass: $done_n"
echo "legs skipped (already present): $skip"
echo "queries that failed: $fail"
echo "rows in output: $(( $(wc -l < "$OUT") - 1 ))"
if [ -s "$ERR" ]; then
  echo "--- stderr, first 10 lines ---"
  head -10 "$ERR" | sed 's/^/    /'
  echo "timeout lines: $(grep -c 'statement timeout' "$ERR" || true)"
else
  echo "stderr clean; timeouts: 0"
fi
echo "--- legs with bars < 25 (flagged, KEPT) ---"
awk -F, 'NR>1 && $7+0 < 25 {printf "    %s %s strike %s bars %s\n", $1, $5, $6, $7}' "$OUT"
echo "count with bars < 25: $(awk -F, 'NR>1 && $7+0 < 25' "$OUT" | wc -l)"
