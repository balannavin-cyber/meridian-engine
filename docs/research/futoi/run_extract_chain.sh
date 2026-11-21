#!/bin/sh
# Per-session chain extraction driver. One session per query (see the SQL header
# for why). Resumable: a session already present in the output is skipped.
set -eu
cd "$(dirname "$0")/../../.."
ROQ=./bin/roq.sh
SQL=docs/research/futoi/sql/extract_session_chain.sql
NIFTY=9992f600-51b3-4009-b487-f878692a0bc5
OUT=docs/research/futoi/data/session_chain.csv
ERR=docs/research/futoi/logs/extract_chain.err
: > "$ERR"
if [ ! -s "$OUT" ]; then
  printf 'tag,trade_date,hhmmss,expiry,exp_on_or_after,legs,legs_solved,net_gamma_oi,gross_gamma_oi,strike,option_type,oi,iv,r_used\n' > "$OUT"
fi
n=0
while read -r d; do
  if cut -d, -f2 "$OUT" | grep -qx "$d"; then continue; fi
  n=$((n+1))
  if ! { printf "\\set nifty '%s'\n\\set d '%s'\n" "$NIFTY" "$d"; cat "$SQL"; } \
       | "$ROQ" 2>>"$ERR" | tail -n +2 >> "$OUT"; then
    echo "QUERY FAILED: $d" >> "$ERR"
  fi
  [ $((n % 25)) -eq 0 ] && echo "  ... $n sessions queried ($d)"
done < docs/research/futoi/data/sessions.txt
echo "sessions queried this pass: $n"
echo "output rows: $(( $(wc -l < "$OUT") - 1 ))"
echo "distinct sessions in output: $(cut -d, -f2 "$OUT" | tail -n +2 | sort -u | wc -l)"
[ -s "$ERR" ] && { echo "--- stderr (first 20) ---"; head -20 "$ERR"; } || echo "stderr clean"
