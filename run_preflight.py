from __future__ import annotations

import os
import sys

from preflight_common import (
    StageResult,
    log,
    ensure_env_loaded,
    write_report,
    append_history,
)

# Import stages (we will build them next)
from stage0_env_contract import run_stage as stage0
from stage1_auth_smoke import run_stage as stage1
from stage2_db_contract import run_stage as stage2
from stage3_runner_drystart import run_stage as stage3


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)

    env_path = os.path.join(root_dir, ".env")

    log("========== MERDIAN PREFLIGHT START ==========")

    try:
        ensure_env_loaded(env_path)
    except Exception as e:
        log(f"FATAL: env load failed: {e}")
        return 1

    stages = [
        ("stage0_env_contract", stage0),
        ("stage1_auth_smoke", stage1),
        ("stage2_db_contract", stage2),
        ("stage3_runner_drystart", stage3),
    ]

    results = []
    overall_status = "PASS"

    for name, fn in stages:
        log(f"--- Running {name} ---")
        stage_result: StageResult = fn(root_dir)

        stage_result.finalize()
        results.append(stage_result.to_dict())

        if stage_result.status == "FAIL":
            overall_status = "FAIL"
            log(f"{name} FAILED")
        else:
            log(f"{name} PASSED")

    final_report = {
        "overall_status": overall_status,
        "stages": results
    }

    output_dir = os.path.join(base_dir, "output")
    write_report(os.path.join(output_dir, "latest_preflight_report.json"), final_report)
    append_history(os.path.join(output_dir, "preflight_history.jsonl"), final_report)

    log(f"========== PREFLIGHT {overall_status} ==========")

    return 0 if overall_status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())