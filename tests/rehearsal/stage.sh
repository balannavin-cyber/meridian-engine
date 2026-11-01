#!/usr/bin/env bash
# Stage the T0 load rehearsal for user tape (operator, with sudo):
#   cd ~/meridian-tape-dev && sudo bash tests/rehearsal/stage.sh
# Copies the committed services/ and tests/rehearsal/ at the clone's HEAD to
# /var/lib/tape/rehearsal_app (root-owned, read-only for tape) and creates the rehearsal's own
# directories. Touches nothing of the production install (/var/lib/tape/app, spool, state, manifest,
# the unit or the timer). Refused Mon-Fri 08:30-15:45 IST.
set -euo pipefail
die() { echo "STAGE REFUSED: $*" >&2; exit 2; }
[ "$(id -u)" -eq 0 ] || die "run with sudo"
ist=$(TZ=Asia/Kolkata date +%u/%H%M); dow=${ist%%/*}; hhmm=$((10#${ist##*/}))
if [ "$dow" -le 5 ] && [ "$hhmm" -ge 830 ] && [ "$hhmm" -lt 1545 ]; then die "market hours"; fi
id tape >/dev/null 2>&1 || die "user tape does not exist"
[ -x /var/lib/tape/venv/bin/python ] || die "missing /var/lib/tape/venv"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
G=(git -c safe.directory="$REPO" -C "$REPO")
[ -z "$("${G[@]}" status --porcelain -- services tests/rehearsal)" ] || die "uncommitted changes under services/ or tests/rehearsal/"
DEST=/var/lib/tape/rehearsal_app
rm -rf "$DEST.new"
install -d -o root -g root -m 755 "$DEST.new"
"${G[@]}" archive HEAD services tests/rehearsal | tar -x -C "$DEST.new"
chown -R root:root "$DEST.new"; chmod -R u=rwX,go=rX "$DEST.new"
rm -rf "$DEST"; mv "$DEST.new" "$DEST"
for d in rehearsal_root rehearsal_keep rehearsal_out; do install -d -o tape -g tape -m 700 "/var/lib/tape/$d"; done
echo "STAGED $("${G[@]}" rev-parse --short=12 HEAD) -> $DEST"
