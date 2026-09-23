#!/usr/bin/env bash
# =====================================================================
# roq.sh -- READ-ONLY query helper for the MERDIAN Postgres (Supabase).
# Session 81 (2026-09-23).
#
# PURPOSE
#   Lets a session run verification queries itself instead of handing SQL
#   to the operator to paste into the Supabase editor. Every S79/S80/S81
#   "verify this against the database" step goes through here.
#
# ROLE
#   Connects as `merdian_ro`, a login with SELECT only. The role is the
#   real enforcement; everything below is belt-and-braces on top of it.
#
# CREDENTIAL  (Rule 19 -- never printed, echoed, logged or committed)
#   $HOME/.merdian_ro_env, mode 600, OUTSIDE every git tree.
#   One line:  MERDIAN_RO_DSN=<uri>
#   It is sourced ONLY inside a subshell. The URI is decomposed into libpq
#   PG* environment variables, so the connection string NEVER appears in
#   argv and therefore never in `ps` or shell history. psql is invoked with
#   no connection argument at all.
#
# SAFETY, in order of strength
#   1. The role cannot write. This is the guarantee; the rest is defence.
#   2. PGOPTIONS sets default_transaction_read_only=on and
#      statement_timeout=30s as backend startup options -- applied before
#      any statement, silently, and impossible to forget.
#   3. The same two settings are re-issued as an explicit SQL prelude, so
#      they hold even if a pooler strips startup options.
#   4. A write-verb guard refuses the query client-side if INSERT / UPDATE
#      / DELETE / TRUNCATE / DROP / ALTER / CREATE / GRANT / REVOKE / COPY
#      appears outside a comment or string literal.
#   statement_timeout means a mistake FAILS rather than hangs.
#
# USAGE
#   roq.sh < query.sql
#   roq.sh query.sql
#   printf '%s' 'SELECT 1;' | roq.sh
#   roq.sh --skip-verb-guard          (see below)
#
#   --skip-verb-guard disables ONLY item 4. Its sole purpose is to prove
#   items 1-3 actually work, by sending a known write and watching the
#   SERVER refuse it. Verifying the braces requires removing the belt.
#   It cannot make the role writable.
#
# OUTPUT
#   Normal queries print aligned. EXPLAIN is detected and printed with
#   tuples-only/unaligned so the plan passes through exactly as the server
#   emitted it, with no border, padding or footer added.
#
# EXIT CODES
#   0 ok | 2 usage / credential / guard refusal | other = psql's own
# =====================================================================
set -euo pipefail

CRED="${MERDIAN_RO_ENV_FILE:-$HOME/.merdian_ro_env}"
PROG=roq

die() { printf '%s: %s\n' "$PROG" "$*" >&2; exit 2; }

usage() {
  sed -n '2,/^# ====/p' "$0" | sed -e 's/^# \{0,1\}//' -e '$d'
}

SKIP_GUARD=0
SQL_FILE=""

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)          usage; exit 0 ;;
    --skip-verb-guard)  SKIP_GUARD=1; shift ;;
    -f|--file)          SQL_FILE="${2:-}"; [ -n "$SQL_FILE" ] || die "-f needs a path"; shift 2 ;;
    --)                 shift; [ $# -gt 0 ] && SQL_FILE="$1"; break ;;
    -*)                 die "unknown option: $1" ;;
    *)                  SQL_FILE="$1"; shift ;;
  esac
done

command -v psql >/dev/null 2>&1 || die "psql not found -- install postgresql-client"

# ---- credential: presence and permissions (contents never read here) ----
[ -f "$CRED" ] || die "credential file not found at \$HOME/.merdian_ro_env"
[ -r "$CRED" ] || die "credential file not readable"
CRED_MODE=$(stat -c '%a' "$CRED")
case "$CRED_MODE" in
  600|400) ;;
  *) die "credential file mode is $CRED_MODE; expected 600 -- refusing to use it" ;;
esac

# ---- read the SQL ----
if [ -n "$SQL_FILE" ]; then
  [ -r "$SQL_FILE" ] || die "cannot read SQL file: $SQL_FILE"
  SQL=$(cat -- "$SQL_FILE")
else
  [ ! -t 0 ] || die "no SQL given -- pass a file argument or pipe SQL on stdin"
  SQL=$(cat)
fi
[ -n "${SQL//[[:space:]]/}" ] || die "empty SQL"

# ---- strip comments and string literals, for inspection only ----
# Order: block comments, then line comments, then single-quoted strings.
# Over-stripping is safe: the stripped text is used ONLY to classify the
# query, never to execute it.
STRIPPED=$(printf '%s' "$SQL" \
  | sed -z -e 's|/\*[^*]*\*\+\([^/*][^*]*\*\+\)*/| |g' \
  | sed    -e 's/--.*$//' \
  | sed    -e "s/'[^']*'/ /g")

# ---- write-verb guard (belt; the role is the braces) ----
if [ "$SKIP_GUARD" -eq 0 ]; then
  if printf '%s' "$STRIPPED" | grep -Eiqw 'insert|update|delete|truncate|drop|alter|create|grant|revoke|copy'; then
    VERB=$(printf '%s' "$STRIPPED" \
           | grep -Eiow 'insert|update|delete|truncate|drop|alter|create|grant|revoke|copy' \
           | head -1)
    die "write verb '$VERB' found outside a comment -- refused.
     The merdian_ro role cannot write in any case; this guard is
     belt-and-braces. Use --skip-verb-guard only to demonstrate that the
     server itself refuses the statement."
  fi
fi

# ---- EXPLAIN detection: pass the plan through unaltered ----
if printf '%s' "$STRIPPED" | grep -Eiq '^[[:space:]]*explain([[:space:]]|\()'; then
  FMT=(-P format=unaligned -P tuples_only=on -P footer=off)
else
  FMT=(-P format=aligned -P footer=on)
fi

ERR=$(mktemp "${TMPDIR:-/tmp}/roq.err.XXXXXX")
chmod 600 "$ERR"
cleanup() { rm -f "$ERR"; }
trap cleanup EXIT

RC=0
(
  set -euo pipefail

  # ---- the ONLY place the DSN exists ----
  # shellcheck disable=SC1090
  . "$CRED"
  [ -n "${MERDIAN_RO_DSN:-}" ] || { printf '%s: MERDIAN_RO_DSN missing from credential file\n' "$PROG" >&2; exit 2; }

  # Decompose the URI into libpq PG* variables so nothing lands in argv.
  raw="$MERDIAN_RO_DSN"
  rest="${raw#postgresql://}"; rest="${rest#postgres://}"

  qs=""
  case "$rest" in *\?*) qs="${rest#*\?}"; rest="${rest%%\?*}" ;; esac

  userinfo=""; hostdb="$rest"
  case "$rest" in *@*) userinfo="${rest%%@*}"; hostdb="${rest#*@}" ;; esac

  hostport="$hostdb"; dbname=""
  case "$hostdb" in */*) hostport="${hostdb%%/*}"; dbname="${hostdb#*/}" ;; esac

  u="$userinfo"; p=""
  case "$userinfo" in *:*) u="${userinfo%%:*}"; p="${userinfo#*:}" ;; esac

  # IPv6 literals arrive as [::1]:5432
  case "$hostport" in
    \[*\]*) h="${hostport%%\]*}"; h="${h#\[}"; pr="${hostport#*\]}"; pr="${pr#:}" ;;
    *:*)    h="${hostport%%:*}";  pr="${hostport##*:}" ;;
    *)      h="$hostport";        pr="" ;;
  esac

  # percent-decoding, per RFC 3986
  ud() { local s="${1//+/ }"; printf '%b' "${s//%/\\x}"; }
  u=$(ud "$u"); p=$(ud "$p"); dbname=$(ud "$dbname")

  sslmode=""; extra_opts=""
  IFS='&' read -r -a _kv <<<"$qs"
  for kv in "${_kv[@]:-}"; do
    case "$kv" in
      sslmode=*) sslmode=$(ud "${kv#sslmode=}") ;;
      options=*) extra_opts=$(ud "${kv#options=}") ;;
    esac
  done

  export PGUSER="$u"
  export PGPASSWORD="$p"
  export PGHOST="$h"
  export PGPORT="${pr:-5432}"
  export PGDATABASE="${dbname:-postgres}"
  export PGSSLMODE="${sslmode:-require}"
  export PGCONNECT_TIMEOUT=15
  export PGAPPNAME="merdian-roq"
  # Belt 2: enforced by the backend at connection start, before any statement.
  export PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=30s ${extra_opts}"

  # The DSN itself must not be inherited by psql.
  unset MERDIAN_RO_DSN raw rest qs userinfo hostdb hostport u p h pr dbname sslmode extra_opts

  # Belt 3: re-issued as SQL, so it survives a pooler that drops PGOPTIONS.
  {
    printf 'SET default_transaction_read_only = on;\n'
    printf "SET statement_timeout = '30s';\n"
    printf '%s\n' "$SQL"
  } | psql -X -q -v ON_ERROR_STOP=1 "${FMT[@]}" -P pager=off
) 2>"$ERR" || RC=$?

# ---- redact defensively before anything reaches stderr (Rule 19) ----
if [ -s "$ERR" ]; then
  ROQ_CRED_FILE="$CRED" awk '
    function lit(str, needle,   out, i) {
      if (needle == "") return str
      out = ""
      while ((i = index(str, needle)) > 0) {
        out = out substr(str, 1, i-1) "[REDACTED]"
        str = substr(str, i + length(needle))
      }
      return out str
    }
    BEGIN {
      f = ENVIRON["ROQ_CRED_FILE"]
      while ((getline l < f) > 0) {
        if (sub(/^MERDIAN_RO_DSN=/, "", l)) {
          gsub(/^["'"'"']|["'"'"']$/, "", l)
          dsn = l
          if (match(dsn, /:\/\/[^@]*@/)) {
            ui = substr(dsn, RSTART+3, RLENGTH-4)
            if (index(ui, ":") > 0) pw = substr(ui, index(ui, ":")+1)
          }
        }
      }
      close(f)
    }
    { print lit(lit($0, dsn), pw) }
  ' "$ERR" >&2
fi

exit "$RC"
