#!/usr/bin/env bash
# fixture stand-in for bin/roq.sh: same prelude and psql flags, local fixture DB
if [ $# -gt 0 ]; then SQL=$(cat "$1"); else SQL=$(cat); fi
{ printf 'SET default_transaction_read_only = on;\n'; printf "SET statement_timeout = '30s';\n"; printf '%s\n' "$SQL"; } \
 | su postgres -c "psql -X -q -v ON_ERROR_STOP=1 -P format=aligned -P footer=on -P pager=off -d mp7"
