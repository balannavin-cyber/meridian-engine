#!/usr/bin/env bash
# S90 / AM-1 — every offline check in one command. No database, no network, any hour.
#   bash tests/run_offline.sh      -> exit 0 only if all pass
set -uo pipefail
cd "$(dirname "$0")/.."
rc=0
echo "== 1/6 contract runner unit tests";   python3 tests/test_check_contracts_shadow.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 2/6 seeded defects on golden day"; python3 tests/replay/test_replay_seeded.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 3/6 replay vs pinned statuses";    python3 tests/replay/replay_contracts.py --check | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 4/6 ledger child runs (S90_CHILD_RUN)"; python3 tests/test_execution_log_child.py 2>/dev/null | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 5/6 CAS close slot pick (S90_CAS_SLOT_PICK)"; python3 tests/test_cas_close_slot_pick.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 6/6 CAS recon auto-correct (two sources)"; python3 tests/test_cas_recon_autocorrect.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "OFFLINE $([ $rc -eq 0 ] && echo PASS || echo FAIL)"
exit $rc
