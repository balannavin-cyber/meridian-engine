#!/usr/bin/env bash
# mp7_run.sh -- M-P7 extract runner. Pre-registered with MP7_flow_badge_prereg_2026-10-11.md.
# Runs Part 0 (Rule 13, live control) once and Parts 1a/1b (status, cycles) for every calendar date
# 2026-08-24 .. 2026-10-09, through bin/roq.sh (merdian_ro, read-only, 30 s statement timeout).
# Writes ONLY under $OUT (default ~/mp7_out), never into a git tree. A non-trading date returns
# NOT_SESSION rows and an empty cycles file; that is data, not an error.
# Usage (from ~/meridian-cc):  bash docs/research/s96_priority/p7/mp7/mp7_run.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROQ="${ROQ:-$HOME/meridian-cc/bin/roq.sh}"
OUT="${OUT:-$HOME/mp7_out}"
[ -x "$ROQ" ] || { echo "mp7: roq not found at $ROQ" >&2; exit 2; }
mkdir -p "$OUT/status" "$OUT/cycles"
"$ROQ" "$HERE/mp7_part0_rule13.sql"  > "$OUT/part0a_rule13.csv"
"$ROQ" "$HERE/mp7_control_live.sql"  > "$OUT/part0b_control_live.csv"
d=2026-08-24
while [ "$d" != "2026-10-10" ]; do
  { printf "\\set d '%s'\n" "$d"; cat "$HERE/mp7_status.sql"; } | "$ROQ" > "$OUT/status/$d.csv"
  { printf "\\set d '%s'\n" "$d"; cat "$HERE/mp7_cycles.sql"; } | "$ROQ" > "$OUT/cycles/$d.csv"
  printf '%s status=%s cycles=%s\n' "$d" \
    "$(($(wc -l < "$OUT/status/$d.csv") - 1))" "$(($(wc -l < "$OUT/cycles/$d.csv") - 1))"
  d=$(date -I -d "$d + 1 day")
done
( cd "$OUT" && find . -name '*.csv' -type f | sort | xargs sha256sum ) > "$OUT/SHA256SUMS"
echo "mp7: done; $(wc -l < "$OUT/SHA256SUMS") files hashed in $OUT/SHA256SUMS"
