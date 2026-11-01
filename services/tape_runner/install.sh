#!/usr/bin/env bash
# MERIDIAN tape runner (T0) installer. Run by the operator, from the retail box clone:
#   cd ~/meridian-tape-dev && sudo bash services/tape_runner/install.sh
# Installs the code at the clone's HEAD, the unit and the timer; enables + starts the TIMER only.
# Never starts the service, never runs during market hours, never creates or modifies the venv,
# never reads the contents of /etc/tape/*.env (existence checks only).
set -euo pipefail

APP_ROOT=/var/lib/tape/app
VENV_PY=/var/lib/tape/venv/bin/python
UNIT_DIR=/etc/systemd/system
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { echo "INSTALL REFUSED: $*" >&2; exit 2; }

# 1. root, and not during market hours (Mon-Fri 08:30-15:45 IST)
[ "$(id -u)" -eq 0 ] || die "run with sudo"
ist=$(TZ=Asia/Kolkata date +%u/%H%M); dow=${ist%%/*}; hhmm=$((10#${ist##*/}))
if [ "$dow" -le 5 ] && [ "$hhmm" -ge 830 ] && [ "$hhmm" -lt 1545 ]; then
  die "market hours (Mon-Fri 08:30-15:45 IST); install after 15:45 or at the weekend"
fi

# 2. preconditions (existence only -- contents are never read)
id tape >/dev/null 2>&1 || die "user tape does not exist"
for f in /etc/tape/kite_api.env /etc/tape/kite_token.env /etc/tape/aws.env; do
  [ -f "$f" ] || die "missing $f"
done
[ -x "$VENV_PY" ] || die "missing $VENV_PY (the venv is provisioned separately; install.sh does not create it)"
sudo -u tape "$VENV_PY" - "$HERE/requirements.txt" <<'PY' || die "venv check failed"
import sys
from importlib.metadata import version
want = {}
for line in open(sys.argv[1]):
    line = line.split("#")[0].strip()
    if "==" in line:
        n, v = line.split("==")
        want[n.strip()] = v.strip()
import kiteconnect, boto3  # noqa: F401
bad = {n: (version(n), v) for n, v in want.items() if version(n) != v}
for n, v in want.items():
    print("venv %s==%s" % (n, version(n)))
if bad:
    print("VERSION MISMATCH (installed, pinned): %s" % bad)
    sys.exit(1)
PY

# 3. code at the clone's HEAD (committed content only) -> /var/lib/tape/app/<sha>, current -> it
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
G=(git -c safe.directory="$REPO" -C "$REPO")
[ -z "$("${G[@]}" status --porcelain -- services)" ] || die "uncommitted changes under services/ in $REPO"
SHA="$("${G[@]}" rev-parse --short=12 HEAD)"
DEST="$APP_ROOT/$SHA"
install -d -o root -g root -m 755 "$APP_ROOT"
if [ ! -d "$DEST" ]; then
  install -d -o root -g root -m 755 "$DEST.tmp"
  "${G[@]}" archive HEAD services | tar -x -C "$DEST.tmp"
  chown -R root:root "$DEST.tmp"; chmod -R u=rwX,go=rX "$DEST.tmp"
  mv "$DEST.tmp" "$DEST"
fi
ln -sfn "$DEST" "$APP_ROOT/current.new" && mv -T "$APP_ROOT/current.new" "$APP_ROOT/current"
echo "app $APP_ROOT/current -> $(readlink "$APP_ROOT/current")"
sudo -u tape env PYTHONPATH="$APP_ROOT/current" "$VENV_PY" -c "import services.tape_runner.recorder" \
  || die "the installed code does not import as user tape"

# 4. working directories
for d in spool state manifest; do
  install -d -o tape -g tape -m 700 "/var/lib/tape/$d"
done

# 5. unit + timer; enable/start the TIMER only
install -o root -g root -m 644 "$HERE/tape-runner.service" "$UNIT_DIR/tape-runner.service"
install -o root -g root -m 644 "$HERE/tape-runner.timer" "$UNIT_DIR/tape-runner.timer"
systemctl daemon-reload
systemd-analyze verify "$UNIT_DIR/tape-runner.service" "$UNIT_DIR/tape-runner.timer"
systemctl enable --now tape-runner.timer
systemctl list-timers tape-runner.timer --no-pager
echo "INSTALL OK sha=$SHA (service NOT started; the timer starts it at 08:50 IST on weekdays)"
