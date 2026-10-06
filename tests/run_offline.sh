#!/usr/bin/env bash
# S90 / AM-1 — every offline check in one command. No database, no network, any hour.
#   bash tests/run_offline.sh      -> exit 0 only if all three pass
set -uo pipefail
cd "$(dirname "$0")/.."
rc=0
echo "== 1/3 contract runner unit tests";   python3 tests/test_check_contracts_shadow.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 2/3 seeded defects on golden day"; python3 tests/replay/test_replay_seeded.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 3/3 replay vs pinned statuses";    python3 tests/replay/replay_contracts.py --check | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "OFFLINE $([ $rc -eq 0 ] && echo PASS || echo FAIL)"
exit $rc
