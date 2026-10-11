#!/usr/bin/env bash
# guard_run.sh -- S96 / TD-S95-NEW-1 (c) survey runner. READ-ONLY through bin/roq.sh (merdian_ro, 30 s timeout).
# Writes only under $OUT (default ~/guard_out). Usage (from ~/meridian-cc):
#   bash docs/research/s96_priority/guard/guard_run.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROQ="${ROQ:-$HOME/meridian-cc/bin/roq.sh}"
OUT="${OUT:-$HOME/guard_out}"
[ -x "$ROQ" ] || { echo "guard: roq not found at $ROQ" >&2; exit 2; }
mkdir -p "$OUT"
d=2026-08-26
while [ "$d" != "2026-10-10" ]; do
  { printf "\\set d '%s'\n" "$d"; cat "$HERE/guard_cycles.sql"; } | "$ROQ" > "$OUT/$d.csv"
  printf '%s rows=%s\n' "$d" "$(($(wc -l < "$OUT/$d.csv") - 1))"
  d=$(date -I -d "$d + 1 day")
done
( cd "$OUT" && sha256sum 2026-*.csv ) > "$OUT/SHA256SUMS"
echo "guard: done; $(wc -l < "$OUT/SHA256SUMS") files hashed"
