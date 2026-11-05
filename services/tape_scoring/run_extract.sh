#!/usr/bin/env bash
# run_extract.sh -- run scoring_extract.sql through bin/roq.sh (merdian_ro, SELECT only) into CSVs, one file per
# relation per trading day: <out>/<relation>/<day>.csv, plus <out>/manifest.tsv (sha256 per file).
# HASHED with score.py (docs/tape/scoring_plan.md section 1.2, OVR-1). Operator-run on the box; never run by the build session.
#
#   bash services/tape_scoring/run_extract.sh --from 2026-11-02 --to 2026-12-15 --out ~/tape_scoring/in \
#        [--s3 meridian-engine-deploy/tape_scoring/2026-11-02_2026-12-15/] [--roq /path/to/roq.sh]
#
# Order: (1) SELECT count(*) pre-check per relation for the FIRST trading day - refuses, naming the relation, on a zero
# count or a refused read (hist_spot_bars_1m is the relation never read as merdian_ro before); (2) extract every
# trading day (days = tape_daily_report rows in range); (3) manifest; (4) optional upload.
# Reads no .env and prints no credential.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
SQL="$HERE/scoring_extract.sql"
ROQ="${ROQ:-$HERE/../../bin/roq.sh}"
D0=""; D1=""; OUT=""; S3=""
RELS="tape_strike_cycle tape_events tape_chain_events tape_chain_runs tape_daily_report tape_minute gex_strike_snapshots gamma_metrics hist_spot_bars_1m tape_minute_oi"
# OPTIONAL relations (pre-registration v0.4 section 3; operator ruling 2026-11-05): last in RELS; a refused read, a missing count, a
# zero count or a failed day is "OPTIONAL SKIP" (no file written), never an abort. The scorer then reports T4 as NOT COMPUTED.
OPTIONAL_RELS="tape_minute_oi"
is_optional() { case " $OPTIONAL_RELS " in *" $1 "*) return 0 ;; esac; return 1; }
SKIPPED=""

usage() { echo "usage: run_extract.sh --from YYYY-MM-DD --to YYYY-MM-DD --out DIR [--s3 BUCKET/PREFIX/] [--roq PATH]" >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --from) D0="${2:-}"; shift 2 ;;
    --to)   D1="${2:-}"; shift 2 ;;
    --out)  OUT="${2:-}"; shift 2 ;;
    --s3)   S3="${2:-}"; shift 2 ;;
    --roq)  ROQ="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$D0" ] && [ -n "$D1" ] && [ -n "$OUT" ] || usage
[ -r "$SQL" ] || { echo "EXTRACT FAIL: cannot read $SQL" >&2; exit 2; }
[ -x "$ROQ" ] || [ -f "$ROQ" ] || { echo "EXTRACT FAIL: roq.sh not found at $ROQ" >&2; exit 2; }

# the statement tagged "-- @name <n>", up to its terminating ';'
stmt() { awk -v n="$1" '$1=="--" && $2=="@name" {on=($3==n); next} on {print; if ($0 ~ /;[ \t]*$/) exit}' "$SQL"; }
expected_header() { stmt "$1" | tr '\n' ' ' | sed -E 's/^ *SELECT +//; s/ +FROM .*$//; s/ *, */,/g'; }
next_day() { date -d "$1 + 1 day" +%F; }

# psql meta-commands, then one statement, to roq.sh on stdin (roq.sh forces aligned output; \pset format csv overrides it)
prelude() { printf '%s\n' '\pset format csv' '\pset footer off' "\\set d '$1'" "\\set d0 '$D0'" "\\set d1 '$D1'" \
                          "\\set t0 '$1 00:00:00+05:30'" "\\set t1 '$(next_day "$1") 00:00:00+05:30'"; }

DAYS=$( { prelude "$D0"; stmt days_list; } | "$ROQ" | tail -n +2 | cut -d, -f1 | sort -u )
[ -n "$DAYS" ] || { echo "EXTRACT FAIL: no tape_daily_report rows between $D0 and $D1" >&2; exit 1; }
FIRST=$(printf '%s\n' "$DAYS" | head -n 1)

for r in $RELS; do
  q=$(stmt "$r" | tr '\n' ' ' | sed -E 's/SELECT .* FROM /SELECT count(*) FROM /')
  if is_optional "$r"; then
    n=$( { prelude "$FIRST"; printf '%s\n' "$q"; } | "$ROQ" | sed -n 2p ) || n=""
    case "$n" in ''|*[!0-9]*|0) echo "PRECHECK OPTIONAL SKIP $r: count='$n' on $FIRST (T4 will be NOT COMPUTED)"; SKIPPED="$SKIPPED $r"; continue ;; esac
    echo "PRECHECK PASS $r day=$FIRST count=$n (optional)"
    continue
  fi
  n=$( { prelude "$FIRST"; printf '%s\n' "$q"; } | "$ROQ" | sed -n 2p ) || { echo "PRECHECK FAIL $r: read refused or errored" >&2; exit 1; }
  case "$n" in ''|*[!0-9]*) echo "PRECHECK FAIL $r: no count returned" >&2; exit 1 ;; esac
  [ "$n" -gt 0 ] || { echo "PRECHECK FAIL $r: count=0 on $FIRST" >&2; exit 1; }
  echo "PRECHECK PASS $r day=$FIRST count=$n"
done

for day in $DAYS; do
  for r in $RELS; do
    if is_optional "$r"; then
      case " $SKIPPED " in *" $r "*) continue ;; esac
      mkdir -p "$OUT/$r"
      f="$OUT/$r/$day.csv"; tmp="$f.part"
      if { prelude "$day"; stmt "$r"; } | "$ROQ" > "$tmp" && [ "$(head -n 1 "$tmp")" = "$(expected_header "$r")" ]; then
        mv "$tmp" "$f"; echo "EXTRACT PASS $r $day rows=$(( $(wc -l < "$f") - 1 )) (optional)"
      else
        rm -f "$tmp"; echo "EXTRACT OPTIONAL SKIP $r $day (no file; T4 NOT COMPUTED for this day)"
      fi
      continue
    fi
    mkdir -p "$OUT/$r"
    f="$OUT/$r/$day.csv"; tmp="$f.part"
    { prelude "$day"; stmt "$r"; } | "$ROQ" > "$tmp" || { echo "EXTRACT FAIL $r $day: roq.sh rc=$?" >&2; exit 1; }
    [ "$(head -n 1 "$tmp")" = "$(expected_header "$r")" ] || { echo "EXTRACT FAIL $r $day: header differs from the SELECT list" >&2; exit 1; }
    mv "$tmp" "$f"
    echo "EXTRACT PASS $r $day rows=$(( $(wc -l < "$f") - 1 ))"
  done
done

( cd "$OUT" && find . -name '*.csv' -type f | sed 's|^\./||' | LC_ALL=C sort | while read -r f; do
    printf '%s\t%s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "$f"; done ) > "$OUT/manifest.tsv"
echo "MANIFEST $(wc -l < "$OUT/manifest.tsv") files"

if [ -n "$S3" ]; then
  S3="${S3%/}/"
  if aws s3 cp --recursive "$OUT/" "s3://$S3" --only-show-errors; then
    echo "S3 PUT PASS s3://$S3"
  else
    echo "S3 PUT FAIL (credential cannot PutObject there?). Fallback: tar czf tape_scoring.tgz -C \"$OUT\" . and fetch it through the SSM session." >&2
    exit 1
  fi
fi
echo "EXTRACT DONE days=$(printf '%s\n' "$DAYS" | wc -l)"
