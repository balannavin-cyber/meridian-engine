#!/usr/bin/env bash
# MERDIAN disk guard - TD-S80-NEW-18.
#
# WHAT MAKES THIS FAIL (Rule 0): root-filesystem block-use or inode-use crossing
# DISK_GUARD_WARN_PCT / DISK_GUARD_CRIT_PCT. The 2026-09-22 outage was exactly
# that - 4.9 GB on 2026-09-06 to 100% on 2026-09-22, ~150 MB/day, measurable the
# whole time and read by nothing. A run over threshold sends Telegram AND exits
# non-zero; a run under threshold is silent and exits 0. Either way it writes ONE
# log line, which is what separates "guard ran and held" from "guard never ran".
#
# DELIBERATE NON-DEPENDENCIES (S53: a monitor must not share the failure chain of
# what it watches). No Supabase, no Python, no venv, no ingest, no feed. bash +
# coreutils + curl only. It does not call bin/wsfeed_alert.sh: that script
# overwrites logs/WSFEED_FAILED, which wsfeed_preflight.sh:21 treats as a feed
# sentinel, and it always exits 0 so a caller cannot learn whether the send
# landed. This reuses its TRANSPORT (same .env, same two variable names, same
# endpoint) and keeps its own verdict.
#
# NO set -e / set -u / pipefail, on purpose. A guard that aborts on an unset
# variable or a non-zero df is a guard that cannot fire. Every value is defaulted
# and validated explicitly instead.

MOUNT="${DISK_GUARD_MOUNT:-/}"
WARN_PCT="${DISK_GUARD_WARN_PCT:-80}"
CRIT_PCT="${DISK_GUARD_CRIT_PCT:-90}"
ENGINE_DIR="${DISK_GUARD_ENGINE_DIR:-/home/ssm-user/meridian-engine}"
ENV_FILE="${DISK_GUARD_ENV_FILE:-$ENGINE_DIR/.env}"
LOG_FILE="${DISK_GUARD_LOG:-$ENGINE_DIR/logs/disk_guard.log}"

TS="$(date -u +%FT%TZ)"
HOST="$(hostname 2>/dev/null)"
[ -n "$HOST" ] || HOST="unknown-host"

# --- measure -----------------------------------------------------------------
# df -P forces single-line POSIX output, so a long device name cannot wrap the
# columns and shift the field we read.
blocks_pct="$(df -P "$MOUNT" 2>/dev/null | awk 'NR==2 {gsub(/%/,"",$5); print $5}')"
avail_h="$(df -Ph "$MOUNT" 2>/dev/null | awk 'NR==2 {print $4}')"
size_h="$(df -Ph "$MOUNT" 2>/dev/null | awk 'NR==2 {print $2}')"
inodes_pct="$(df -iP "$MOUNT" 2>/dev/null | awk 'NR==2 {gsub(/%/,"",$5); print $5}')"

is_int() { case "${1:-}" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }

# An unreadable block percentage is itself a failure - report it, do not assume OK.
if ! is_int "$blocks_pct"; then
  blocks_pct=""
fi
# Filesystems that do not track inodes report "-". That is absence, not zero.
if ! is_int "$inodes_pct"; then
  inodes_pct=""
fi
[ -n "$avail_h" ] || avail_h="?"
[ -n "$size_h" ]  || size_h="?"

# --- classify ----------------------------------------------------------------
# Verdict is the worst of the two dimensions. Inode exhaustion blocks writes
# exactly as block exhaustion does, so it carries the same thresholds.
verdict="OK"
rc=0
reasons=""

grade() { # $1=label $2=pct
  local label="$1" pct="$2"
  is_int "$pct" || return 0
  if [ "$pct" -ge "$CRIT_PCT" ]; then
    verdict="CRIT"; rc=2; reasons="${reasons}${reasons:+, }${label} ${pct}% >= ${CRIT_PCT}%"
  elif [ "$pct" -ge "$WARN_PCT" ]; then
    [ "$verdict" = "CRIT" ] || { verdict="WARN"; rc=1; }
    reasons="${reasons}${reasons:+, }${label} ${pct}% >= ${WARN_PCT}%"
  fi
}

grade "blocks" "$blocks_pct"
grade "inodes" "$inodes_pct"

if [ -z "$blocks_pct" ]; then
  verdict="UNREADABLE"; rc=3
  reasons="df gave no usable block percentage for ${MOUNT}"
fi

# --- alert -------------------------------------------------------------------
# Sourced in a subshell so the token never enters this script's environment.
# set +u is required: .env line 21 contains a literal $4 (Rule 19 note).
# curl gets -s with stderr discarded and NOT -S, because curl's error text
# includes the request URL, and the bot token is in the URL path.
send_telegram() {
  local text="$1"
  (
    set +u
    # shellcheck disable=SC1090
    . "$ENV_FILE" >/dev/null 2>&1
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
      printf 'skipped:no-credentials'
      exit 0
    fi
    code="$(curl -s -m 15 -o /dev/null -w '%{http_code}' \
      "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${text}" 2>/dev/null)"
    [ -n "$code" ] || code="000"
    if [ "$code" = "200" ]; then printf 'sent:200'; else printf 'failed:%s' "$code"; fi
  )
}

alert="none"
if [ "$rc" -ne 0 ]; then
  msg="[MERDIAN] DISK ${verdict} on ${HOST} ${MOUNT} - ${reasons}. blocks ${blocks_pct:-?}% of ${size_h}, ${avail_h} free, inodes ${inodes_pct:-n/a}%. TD-S80-NEW-18."
  alert="$(send_telegram "$msg")"
  [ -n "$alert" ] || alert="failed:no-result"
fi

# --- log ---------------------------------------------------------------------
# Written LAST and never gated on: on a genuinely full volume this append fails,
# and the alert must already have gone out. The line is the CAN-FIRE/CANNOT-FIRE
# pairing - its presence proves the guard ran, its absence proves it did not.
line="${TS} disk_guard mount=${MOUNT} blocks=${blocks_pct:-?}% inodes=${inodes_pct:-n/a}% avail=${avail_h} size=${size_h} warn=${WARN_PCT} crit=${CRIT_PCT} verdict=${verdict} alert=${alert}"
printf '%s\n' "$line" >> "$LOG_FILE" 2>/dev/null || true

exit "$rc"
