#!/usr/bin/env bash
# Make the one-off special-session timers in UNIT_DIR equal the calendar: write one per date >= TODAY (IST),
# remove every tape-runner-special-*.timer that is past or no longer in the calendar. The weekday timer and
# the service unit are never touched. Called by install.sh; parameters come from the environment so a test
# can point it at a temp directory and a fake systemctl.
#   UNIT_DIR CALENDAR TODAY SESSION_PY PYBIN [SYSTEMCTL]
set -euo pipefail
: "${UNIT_DIR:?}" "${CALENDAR:?}" "${TODAY:?}" "${SESSION_PY:?}" "${PYBIN:?}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

"$PYBIN" -I "$SESSION_PY" --calendar "$CALENDAR" --emit-timers "$tmp" --today "$TODAY" >/dev/null

changed=0
shopt -s nullglob
for f in "$UNIT_DIR"/tape-runner-special-*.timer; do
  n="$(basename "$f")"
  if [ ! -e "$tmp/$n" ]; then
    "$SYSTEMCTL" disable --now "$n" || true
    rm -f "$f"
    echo "special timer removed: $n"
    changed=1
  fi
done
want=()
for f in "$tmp"/tape-runner-special-*.timer; do
  n="$(basename "$f")"
  if ! cmp -s "$f" "$UNIT_DIR/$n" 2>/dev/null; then
    install -m 644 "$f" "$UNIT_DIR/$n"
    echo "special timer written: $n"
    changed=1
  fi
  want+=("$n")
done
[ "$changed" -eq 0 ] || "$SYSTEMCTL" daemon-reload
for n in ${want[@]+"${want[@]}"}; do
  "$SYSTEMCTL" enable --now "$n"
done
echo "special timers in place: ${#want[@]}"
