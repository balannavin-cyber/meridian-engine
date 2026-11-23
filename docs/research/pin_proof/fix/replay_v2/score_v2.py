#!/usr/bin/env python3
"""Pin live replay v2 -- score ONE symbol-day and emit one JSON record per run.

Read-only. No database, no vendor call. Writes nothing (stdout only).

Reuses UNCHANGED:
  fix/replay/score_replay.py   -- V2 (v2_scores), the leg loader's conventions, _g
  lookback_v5/analyze_v5.py    -- compute_run (F = T_g_flat, K = T_g), pick, nearest_mult
  replay_v2/constructions_v2.py -- VS, FV (new, self-tested)

MEMORY: one symbol-day at a time; every per-strike map (_rows, g, g_flat, sigma_k and
the local score dicts) is dropped as soon as the run's record is built. The box has
1,910 MB and no swap. load_runs / measures / main of analyze_v5 are never called.

Diagnostics stored per run, market runs included, all of them per the design:
  R   median over strikes within 1 % of spot with BOTH vendor gammas > 0 of
      gamma_call / gamma_put.  None when no such strike exists -- not 1.0.
  BL  share of open interest in the strike set carried on legs with oi > 0 AND a blank
      or zero vendor gamma.
  FB  (compute_run's forward - S) in strike steps.
  DTE calendar days to expiry, bucketed 0 / 1 / 2 / 3+.
  IVA age of atm_iv_avg in minutes (from the qV pull; None when no row).
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "replay"))
sys.path.insert(0, str(HERE.parent.parent / "lookback_v5"))

from score_replay import _g, v2_scores            # noqa: E402
from constructions_v2 import vs_scores, fv_scores  # noqa: E402
from analyze_v5 import compute_run, nearest_mult, pick  # noqa: E402

STEP = {"NIFTY": 50.0, "SENSEX": 100.0}


def seg(hhmm: str) -> str:
    if hhmm < "09:15":
        return "pre"
    if hhmm <= "15:29":
        return "market"
    return "post"


def load_vol(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("V0|"):
            j = json.loads(raw.split("|", 1)[1])
            out[j["run_id"]] = j
    return out


def score_day(chain: Path, vol: Path):
    vmap = load_vol(vol)
    r0: dict[str, dict] = {}
    legs: dict[str, dict] = {}
    for raw in chain.read_text(encoding="utf-8").splitlines():
        if not raw or "|" not in raw:
            continue
        tag, pay = raw.split("|", 1)
        j = json.loads(pay)
        if tag == "R0":
            r0[j["run_id"]] = j
        elif tag == "R1":
            e = legs.setdefault(j["run_id"], {}).setdefault(
                float(j["strike"]),
                {"c_gamma": None, "p_gamma": None, "c_oi": 0.0, "p_oi": 0.0,
                 "c_px": 0.0, "p_px": 0.0, "nonpos": 0})
            oi = float(j["oi"]) if j.get("oi") not in (None, "") else 0.0
            px = float(j["ltp"]) if j.get("ltp") not in (None, "") else 0.0
            if j["ot"] == "CE":
                e["c_gamma"], e["c_oi"], e["c_px"] = j.get("gamma"), oi, px
            elif j["ot"] == "PE":
                e["p_gamma"], e["p_oi"], e["p_px"] = j.get("gamma"), oi, px
            else:
                raise SystemExit(f"unknown option_type {j['ot']!r} in {chain}")
            if oi > 0 and px <= 0:
                e["nonpos"] += 1

    recs = []
    for run_id, meta in r0.items():
        sym = meta["sym"]
        step = STEP[sym]
        allrows = legs.get(run_id, {})
        S = float(meta["spot_min"]) if meta.get("spot_min") else 0.0
        ts_ist = meta["ts_ist"]
        d_ist, clock = ts_ist.split(" ")
        tname = clock[:5]
        v = vmap.get(run_id, {})
        iv = v.get("atm_iv_avg")
        iv = float(iv) if iv not in (None, "") else None
        iva = v.get("iva_min")
        iva = float(iva) if iva not in (None, "") else None

        rec = {
            "sym": sym, "day": meta["d"], "run_id": run_id, "ts_ist": ts_ist,
            "tname": tname, "segment": seg(tname), "expiry": meta["expiry"],
            "dte_gm": meta["dte"], "S": S,
            "spot_ambiguous": (meta["spot_min"] != meta["spot_max"]),
            "tot_oi_call": meta["tot_oi_call"], "tot_oi_put": meta["tot_oi_put"],
            "n_legs_chain": meta["n_legs_chain"],
            "has_board_row": meta["has_board_row"],
            "B": float(meta["board_pin"]) if meta.get("board_pin") else None,
            "call_wall": float(meta["call_wall"]) if meta.get("call_wall") else None,
            "put_wall": float(meta["put_wall"]) if meta.get("put_wall") else None,
            "atm_iv_avg": iv, "IVA": iva,
            "legs_oi_pos_ltp_nonpos": sum(e["nonpos"] for e in allrows.values()),
            "n_legs_band": len(allrows),
            "atm": nearest_mult(S, step) if S > 0 else None,
        }

        rows = {K: e for K, e in allrows.items() if e["c_oi"] > 0 or e["p_oi"] > 0}
        rec["n_strikes"] = len(rows)
        if S <= 0 or not rows:
            rec.update({"valid": False, "reason": "no_spot" if S <= 0 else "no_strikes",
                        "V2": None, "VS": None, "FV": None, "F": None, "K": None})
            recs.append(rec)
            continue

        # ---- diagnostics that need no solve ----
        ratios = [_g(e["c_gamma"]) / _g(e["p_gamma"]) for K, e in rows.items()
                  if abs(K / S - 1.0) <= 0.01
                  and _g(e["c_gamma"]) > 0 and _g(e["p_gamma"]) > 0]
        rec["R"] = statistics.median(ratios) if ratios else None
        rec["R_n"] = len(ratios)
        oi_tot = oi_bl = 0.0
        for e in rows.values():
            if e["c_oi"] > 0:
                oi_tot += e["c_oi"]
                if _g(e["c_gamma"]) <= 0:
                    oi_bl += e["c_oi"]
            if e["p_oi"] > 0:
                oi_tot += e["p_oi"]
                if _g(e["p_gamma"]) <= 0:
                    oi_bl += e["p_oi"]
        rec["BL"] = (oi_bl / oi_tot) if oi_tot > 0 else None

        # ---- compute_run owns F, K, the forward and T ----
        cr = compute_run(sym, d_ist, tname, S, meta["expiry"], rows, [])
        rec["t_min"] = cr["t_min"]
        rec["dte_cal"] = cr["dte_cal"]
        rec["DTE"] = str(cr["dte_cal"]) if cr["dte_cal"] <= 2 else "3+"
        rec["valid"] = bool(cr["valid"])
        rec["reason"] = cr["reason"]
        rec["n_fallback"] = cr.get("n_fallback", 0)
        rec["sigma_atm"] = cr.get("sigma_atm")
        rec["F_fwd"] = cr.get("F")
        rec["FB"] = ((cr["F"] - S) / step) if cr.get("F") else None
        if cr["valid"]:
            rec["F"], rec["F_lead"] = cr["T_g_flat"], cr["T_g_flat_lead"]
            rec["K"], rec["K_lead"] = cr["T_g"], cr["T_g_lead"]
            rec["K_share"] = cr["T_g_share"]
        else:
            rec["F"] = rec["K"] = None
            rec["F_lead"] = rec["K_lead"] = rec["K_share"] = None

        # ---- V2, VS, FV need no solve, so they score even on an invalid run ----
        p, _, ld = pick(v2_scores(rows), S)
        rec["V2"], rec["V2_lead"] = p, ld
        p, _, ld = pick(vs_scores(rows), S)
        rec["VS"], rec["VS_lead"] = p, ld
        sf, st = fv_scores(rows, S, iv, cr["t_min"])
        rec["FV_status"] = st
        if st == "OK":
            p, _, ld = pick(sf, S)
            rec["FV"], rec["FV_lead"] = p, ld
        else:
            rec["FV"], rec["FV_lead"] = None, None

        for k in ("_rows", "g", "g_flat", "sigma_k"):
            cr.pop(k, None)
        del cr, sf
        recs.append(rec)
    return recs


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: score_v2.py <chain_pull.txt> <vol_pull.txt>")
    for r in score_day(Path(sys.argv[1]), Path(sys.argv[2])):
        print(json.dumps(r, default=str))
