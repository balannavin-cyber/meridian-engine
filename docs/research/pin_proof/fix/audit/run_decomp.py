#!/usr/bin/env python3
"""POST-HOC decomposition re-run -- same as STAGE B plus B1/B2 over every symbol-day and write fix/audit/runs.csv.

Disk only. One symbol-day in memory at a time; audit_day drops every per-strike map
before returning. load_runs / measures / main of analyze_v5.py are never called.

One row per MARKET run (09:15-15:29 IST), including invalid runs with their reason.
I1 and I2 are stored as per-bucket COUNTS AND SUMS (JSON) so the report can pool them
exactly -- not as pre-divided shares, which cannot be re-weighted.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit import audit_day  # noqa: E402

CHAIN = HERE.parent / "replay_v2" / "chain"
OUT = HERE / "runs_decomp.csv"
IST = timezone(timedelta(hours=5, minutes=30))

COLS = [
    "sym", "day", "run_id", "ts_ist", "hhmm", "segment_ok", "expiry", "dte_cal",
    "DTE", "expiry_day", "time_bucket", "S", "F", "FB", "fb_bucket", "sigma_atm",
    "n_strikes", "valid", "reason",
    "GR", "GP", "GN", "NP", "NN", "NR",
    "N1_n", "N1_wrong", "N1_zero", "N1_w_gross", "N1_wrong_gross", "N1_zero_gross",
    "N1_cause_blank", "N1_cause_both",
    "ALL_n", "ALL_GR", "ALL_E_raw_P", "ALL_E_raw_N", "ALL_E_shape_P", "ALL_E_shape_N",
    "ALL_T_R", "ALL_T_P", "ALL_T_N", "ALL_T_err_P", "ALL_T_err_N",
    "ALL_T_signflip_P", "ALL_T_signflip_N", "ALL_T_R_big", "ALL_L1_P", "ALL_L1_N",
    "NOFB_n", "NOFB_GR", "NOFB_E_raw_P", "NOFB_E_raw_N", "NOFB_E_shape_P",
    "NOFB_E_shape_N", "NOFB_T_R", "NOFB_T_P", "NOFB_T_N", "NOFB_T_err_P",
    "NOFB_T_err_N", "NOFB_T_signflip_P", "NOFB_T_signflip_N", "NOFB_L1_P", "NOFB_L1_N",
    "ALL_E_raw_B1", "ALL_E_raw_B2", "ALL_E_shape_B1", "ALL_E_shape_B2",
    "ALL_T_B1", "ALL_T_B2", "ALL_T_err_B1", "ALL_T_err_B2",
    "ALL_L1_B1", "ALL_L1_B2", "GB1", "GB2", "NB1", "NB2",
    "NOFB_E_raw_B1", "NOFB_E_raw_B2", "NOFB_E_shape_B1", "NOFB_E_shape_B2",
    "NOFB_T_B1", "NOFB_T_B2", "NOFB_T_err_B1", "NOFB_T_err_B2",
    "NOFB_L1_B1", "NOFB_L1_B2",
    "N5_B1_pos", "N5_B2_pos", "N5_same_B1_pos", "N5_same_B2_pos",
    "N5_B1_abs", "N5_B2_abs", "N5_same_B1_abs", "N5_same_B2_abs",
    "N5_gap_B1_pos", "N5_gap_B2_pos", "N5_gap_B1_abs", "N5_gap_B2_abs",
    "N5_R_pos", "N5_P_pos", "N5_N_pos", "N5_same_P_pos", "N5_same_N_pos",
    "N5_gap_P_pos", "N5_gap_N_pos", "N5_lead_R_pos",
    "N5_R_abs", "N5_P_abs", "N5_N_abs", "N5_same_P_abs", "N5_same_N_abs",
    "N5_gap_P_abs", "N5_gap_N_abs", "N5_lead_R_abs",
    "K1_n_strikes", "K1_n_fallback", "K1_share_strikes", "K1_share_GR",
    "K1_n_gk_zero", "K1_share_strikes_gk_zero", "K1_share_GN_gk_zero",
    "gR_peak", "gN_peak", "rv2_K", "rv2_VS", "rv2_K_lead", "K_flag", "VS_flag",
    "G1", "G2", "G3",
    "I1_json", "I2_json",
]


def flat(r):
    o = {c: "" for c in COLS}
    o["sym"], o["day"], o["run_id"] = r["sym"], r["day"], r["run_id"]
    o["ts_ist"] = r["ts_ist"]
    o["valid"] = int(bool(r.get("valid")))
    o["reason"] = r.get("reason", "")
    if not r.get("valid"):
        return o
    for k in ("hhmm", "expiry", "dte_cal", "DTE", "expiry_day", "time_bucket",
              "S", "F", "FB", "fb_bucket", "sigma_atm", "n_strikes", "GR",
              "gR_peak", "gN_peak", "rv2_K", "rv2_VS", "rv2_K_lead",
              "K_flag", "VS_flag", "G1", "G2", "G3"):
        o[k] = r.get(k, "")
    o["segment_ok"] = 1
    for k, v in r["N1"].items():
        o[f"N1_{k}"] = v
    for scope in ("ALL", "NOFB"):
        d = r[scope]
        for k in ("n", "GR", "E_raw_P", "E_raw_N", "E_shape_P", "E_shape_N",
                  "T_R", "T_P", "T_N", "T_err_P", "T_err_N",
                  "T_signflip_P", "T_signflip_N", "L1_P", "L1_N",
                  "E_raw_B1", "E_raw_B2", "E_shape_B1", "E_shape_B2",
                  "T_B1", "T_B2", "T_err_B1", "T_err_B2", "L1_B1", "L1_B2"):
            if k in d:
                o[f"{scope}_{k}"] = d[k]
        if scope == "ALL":
            for k in ("GP", "GN", "NP", "NN", "NR", "GB1", "GB2", "NB1", "NB2"):
                o[k] = d.get(k, "")
            o["ALL_T_R_big"] = d.get("T_R_big", "")
    for k, v in r["N5"].items():
        o[f"N5_{k}"] = v
    for k, v in r["K1"].items():
        o[f"K1_{k}"] = v
    o["I1_json"] = json.dumps(r["I1"], separators=(",", ":"))
    o["I2_json"] = json.dumps(r["I2"], separators=(",", ":"), default=str)
    return o


def main() -> int:
    files = sorted(CHAIN.glob("out_*.txt"))
    t0 = time.time()
    n = 0
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for i, fp in enumerate(files, 1):
            recs = audit_day(fp)              # one symbol-day in memory
            for r in recs:
                w.writerow(flat(r))
                n += 1
            recs.clear()
            fh.flush()
            print(f"{i}/{len(files)} {fp.name} rows={n} "
                  f"elapsed={time.time()-t0:.1f}s", flush=True)
    end = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    (HERE / "DONE_DECOMP").write_text(
        f"rows={n}\nfiles={len(files)}\nend={end}\n"
        f"elapsed_s={time.time()-t0:.1f}\n", encoding="utf-8")
    print(f"DONE rows={n} files={len(files)} end={end}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
