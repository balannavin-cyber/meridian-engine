#!/usr/bin/env bash
# D1 (engine lane e1-e3-e10): the operator's single named manual command for a Dhan
# token login. Thin wrapper only -- cron and the dashboard button keep calling
# refresh_dhan_token.py directly; this just runs it and prints what the exit code
# means. The 300s spacing guard (E10, inside refresh_dhan_token.py itself) is what
# actually protects a double-run; this script adds no logic of its own.
#
# CC must never execute this script. It performs a real Dhan login when run on a
# host with a real .env; it exists for the operator to run by hand.
set -uo pipefail

ENGINE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ENGINE_DIR" || exit 1

# /usr/bin/python3, matching the interpreter cron uses for this same script
# (docs/registers/aws_crontab.txt: "50 2 * * 1-5 ... /usr/bin/python3 refresh_dhan_token.py").
/usr/bin/python3 refresh_dhan_token.py
rc=$?

case "$rc" in
  0) echo "dhan_login: OK (0) -- token refreshed" ;;
  2) echo "dhan_login: RATE-LIMITED by Dhan (2) -- a token was issued within the last 2 minutes; the one in .env is probably good. Do not retry for 5 minutes." ;;
  3) echo "dhan_login: REFUSED by the 300s spacing guard (3) -- see seconds remaining above" ;;
  *) echo "dhan_login: FAILED (exit $rc)" ;;
esac

exit "$rc"
