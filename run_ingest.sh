#!/bin/bash
# run_ingest.sh — MERDIAN option-chain ingest wrapper (reconstructed S55 2026-06-17)
# cron: cd /home/ssm-user/meridian-engine && bash run_ingest.sh <SYMBOL> <MODE>
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [[ -f .env ]]; then
    set -a; set +u; source .env; set -u 2>/dev/null || true; set +a
else
    echo "[run_ingest.sh] ERROR: .env not found in $SCRIPT_DIR" >&2; exit 1
fi
SYMBOL="${1:?run_ingest.sh: missing SYMBOL (NIFTY|SENSEX)}"
MODE="${2:-FULL}"
echo "============================================================"
echo "[run_ingest.sh] $(date -u +%Y-%m-%dT%H:%M:%SZ) START symbol=$SYMBOL mode=$MODE"
echo "============================================================"
python3 ingest_option_chain_local.py "$SYMBOL" "$MODE"
rc=$?
echo "[run_ingest.sh] $(date -u +%Y-%m-%dT%H:%M:%SZ) END symbol=$SYMBOL mode=$MODE rc=$rc"
exit $rc
