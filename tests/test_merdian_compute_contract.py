#!/usr/bin/env python3
"""S101 A5 — offline step 25: the contract retail-meridian depends on (retail scope §1.3 item 3).

Retail computes the Board core on each subscriber's own chain by calling merdian_compute
directly -- never a writer. Since S101 C2 that is ONE composed call, exactly what the live writer
runs: compute_gamma_core(**prepare_gamma_inputs(rows, run_id, expected_symbol=SYM), run_type=...,
prior_row=..., spot_vs_range=..., vix=..., recent_max_strikes=...). This test calls it that way
and pins two things:

  1. SIGNATURES of the exported surface (str(inspect.signature)), plus the field order of
     GammaMetricsResult. A rename, a new required parameter, a changed default or a changed
     annotation fails here BEFORE retail finds it in production.
  2. OUTPUTS against PRODUCTION, not against itself. For every frozen gamma_metrics row of
     every golden day whose chain run is frozen too, compute_gamma_core is run on that chain
     (rows' ts / created_at in PostgREST ISO form, as the live writer receives them) and its
     result compared with the value production wrote:
        net_gex, gamma_concentration, flip_level, flip_distance_pct, gamma_zone, regime,
        straddle_atm, straddle_slope, expansion_probability, max_gamma_strike, spot
     -- every row, equal within rel/abs 1e-9 (measured S101: 313/313 on all eleven).
     pin_risk_score is pinned on the rows whose 5 prior cycles are all inside the frozen day,
     with recent_max_strikes = those 5 prior rows' max_gamma_strike. Production's
     fetch_recent_max_gamma_strikes has NO date bound (lt ts, last 5), so its window crosses
     the session boundary; a row with fewer than 5 in-day priors would be compared against a
     window the fixture does not hold. Those rows are excluded BY RULE, and the test asserts
     the exclusion is exactly the first 5 cycles of each day -- it cannot silently grow.
     straddle_velocity is pinned on every row but each day's first, with prior_row =
     {"straddle_atm": the previous frozen row's value} (production's prior row is the latest
     earlier gamma row, which for a day's first cycle is the previous session's; measured
     307/307).

WHAT MAKES IT FAIL (Rule 0, proved by the mutants below, each in its own interpreter on a
copy of the package): M1 Crore divisor 1e7 -> 1.0000001e7 (net_gex); M2 flip dominance floor
0.01 -> 0.5 (flip_level); M3 pin-risk concentration weight 0.30 -> 0.31 (pin_risk_score);
M4 a parameter renamed (signature); M5 a GammaMetricsResult field reordered (fields);
M6 one statement inside compute_gamma_core (flip_distance_pct x100.0 -> x100.1);
M7 the ATM-IV average in derive_atm_iv (/ 2.0 -> / 2.001).

  3. WALL INPUT (S101 C3): merdian_compute.volatility.derive_atm_iv on each golden chain (rows in
     strike order, as the writer selects them) vs production's frozen volatility_snapshots row of
     the same run (source_run_id): atm_strike, atm_call_iv, atm_put_iv, atm_iv_avg, iv_skew --
     every row equal (measured 313 rows x 5 fields).

  4. PIN PATH (S101 C4): the golden days hold no gex_cycle_history, so nothing here is pinned
     against production rows. Pinned instead: the signatures of derive_core,
     trading_days_between and held_for_cycles_next, and the ruled S89 ladder at every threshold
     boundary (equality is the side the rule text names), the NULL-input reasons, the NULL-ratio
     degrade, the carry-forward cases, and a fail-open calendar count. M8 flips the NO PIN test
     `<` -> `<=`; M9 the carry-forward increment.
Loads all six golden days: same rule-23 class as step 12. Stdlib only, run under -I.
"""
from __future__ import annotations

import csv
import gzip
import inspect
import io
import math
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden"

SIGNATURES = {
    "gamma.signed_gamma_exposure": "(row: 'dict[str, Any]', spot: 'float') -> 'float'",
    "gamma.filter_usable_option_rows": "(option_rows: 'list[dict[str, Any]]') -> 'list[dict[str, Any]]'",
    "gamma.infer_symbol": "(option_rows: 'list[dict[str, Any]]', expected_symbol: 'str | None' = None) -> 'str'",
    "gamma.infer_spot": "(option_rows: 'list[dict[str, Any]]') -> 'float'",
    "gamma.infer_expiry_date": "(option_rows: 'list[dict[str, Any]]') -> 'str | None'",
    "gamma.infer_ts": "(option_rows: 'list[dict[str, Any]]') -> 'str'",
    "gamma.infer_strike_step": "(option_rows: 'list[dict[str, Any]]') -> 'float | None'",
    "gamma.compute_net_gex": "(option_rows: 'list[dict[str, Any]]', spot: 'float') -> 'float'",
    "gamma.build_strike_exposure_map": "(option_rows: 'list[dict[str, Any]]', spot: 'float') -> 'dict[float, float]'",
    "gamma.compute_gamma_concentration": "(strike_map: 'dict[float, float]') -> 'float | None'",
    "gamma.compute_flip_level": "(strike_map: 'dict[float, float]', spot: 'float | None' = None) -> 'float | None'",
    "gamma.find_atm_strike": "(option_rows: 'list[dict[str, Any]]', spot: 'float') -> 'float | None'",
    "gamma.compute_straddle_atm": "(option_rows: 'list[dict[str, Any]]', spot: 'float') -> 'float | None'",
    "gamma.compute_straddle_slope": "(option_rows: 'list[dict[str, Any]]', spot: 'float') -> 'float | None'",
    "gamma.compute_expansion_probability": "(gamma_concentration: 'float | None', flip_distance_pct: 'float | None', net_gex: 'float') -> 'float | None'",
    "gamma.determine_regime": "(net_gex: 'float', flip_level: 'float | None') -> 'str'",
    "gamma.determine_gamma_zone": "(flip_distance_pct: 'float | None') -> 'str | None'",
    "gamma.compute_straddle_velocity": "(current_straddle: 'float | None', prior_row: 'dict[str, Any] | None') -> 'float | None'",
    "gamma.compute_otm_oi_velocity": "(option_rows: 'list[dict[str, Any]]', spot: 'float', prior_row: 'dict[str, Any] | None', otm_steps: 'int' = 2) -> 'float | None'",
    "gamma.compute_otm_oi_snapshot": "(option_rows: 'list[dict[str, Any]]', spot: 'float', otm_steps: 'int' = 2) -> 'float | None'",
    "gamma.compute_max_gamma_strike": "(strike_map: 'dict[float, float]') -> 'float | None'",
    "gamma.compute_pin_risk_score": "(gamma_concentration: 'float | None', expansion_probability: 'float | None', spot: 'float', max_gamma_strike: 'float | None', strike_step: 'float | None', recent_max_strikes: 'list[float]') -> 'float | None'",
    "gamma.build_gss_rows": "(option_rows_raw: 'list[dict[str, Any]]', spot: 'float', symbol: 'str', ts: 'str', expiry_date: 'str | None', run_id: 'str') -> 'list[dict[str, Any]]'",
    "gamma.prepare_gamma_inputs": "(option_rows_raw: 'list[dict[str, Any]]', run_id: 'str', expected_symbol: 'str | None' = None) -> 'dict[str, Any]'",
    "gamma.compute_gamma_core": "(*, run_id: 'str', symbol: 'str', spot: 'float', expiry_date: 'str | None', ts: 'str', option_rows_raw: 'list[dict[str, Any]]', option_rows: 'list[dict[str, Any]]', run_type: 'str', prior_row: 'dict[str, Any] | None', spot_vs_range: 'float | None', vix: 'float | None', recent_max_strikes: 'list[float]') -> 'GammaMetricsResult'",
    "volatility.parse_iso_date": "(value: 'Any') -> 'Optional[date]'",
    "volatility.parse_iso_dt": "(value: 'Any') -> 'Optional[datetime]'",
    "volatility.safe_float": "(value: 'Any') -> 'Optional[float]'",
    "volatility.get_expiry_type": "(expiry_date: 'date', symbol: 'str') -> 'str'",
    "volatility.get_strike_step": "(symbol: 'str') -> 'int'",
    "volatility.find_atm_strike": "(spot: 'float', symbol: 'str') -> 'int'",
    "volatility.find_row": "(rows: 'List[Dict[str, Any]]', strike: 'int', option_type: 'str') -> 'Optional[Dict[str, Any]]'",
    "volatility.derive_atm_iv": "(option_rows: 'List[Dict[str, Any]]', on_symbol: 'Optional[Callable[[str], Any]]' = None) -> 'dict[str, Any]'",
    "pin.derive_core": "(held_for_cycles: 'Optional[int]', runnerup_share_ratio: 'Optional[float]', conc_top1_share: 'Optional[float]', *, nopin_conc_floor: 'float', stable_held_for: 'float', locked_held_for: 'float', locked_ratio_max: 'float') -> 'tuple[Optional[str], Optional[str]]'",
    "cycle.trading_days_between": "(run_date: 'date', expiry: 'date', is_open: 'Callable[[str], bool]') -> 'int'",
    "cycle.held_for_cycles_next": "(state: 'str', leader: 'Optional[float]', prior_rows: 'list[dict[str, Any]]') -> 'Optional[int]'",
    "cycle.derive_rank_fields": "(rank_rows: 'list[dict[str, Any]]') -> 'dict[str, Any]'",
    "cycle.boost": "(t_days: 'float') -> 'float'",
    "cycle.conviction_for": "(runnerup_share_ratio: 'Optional[float]', t_days: 'Optional[int]', calendar_healthy: 'bool') -> 'tuple[Optional[float], Optional[str]]'",
}
RESULT_FIELDS = ["run_id", "symbol", "ts", "expiry_date", "spot", "net_gex", "gamma_concentration",
                 "flip_level", "flip_distance", "flip_distance_pct", "gamma_zone", "straddle_atm",
                 "straddle_slope", "regime", "expansion_probability", "straddle_velocity",
                 "otm_oi_velocity", "spot_vs_range", "run_type", "vix", "max_gamma_strike",
                 "pin_risk_score", "gss_rows"]
CORE = ["net_gex", "gamma_concentration", "flip_level", "flip_distance_pct", "gamma_zone", "regime",
        "straddle_atm", "straddle_slope", "expansion_probability", "max_gamma_strike", "spot"]


def _ts(v: str) -> datetime:
    """psql CSV timestamp -> aware datetime (fraction padded for Python 3.10)."""
    v = v.replace(" ", "T", 1).replace("Z", "+00:00")
    if len(v) >= 3 and v[-3] in "+-" and v[-2:].isdigit():
        v += ":00"
    if "." in v:
        head, rest = v.split(".", 1)
        n = len(rest) - len(rest.lstrip("0123456789"))        # leading digits only
        v = f"{head}.{rest[:n][:6].ljust(6, '0')}{rest[n:]}"
    return datetime.fromisoformat(v)


def _same(a, b: str) -> bool:
    if b == "":
        return a is None
    if a is None:
        return False
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return str(a) == b


def check(root: Path) -> list[str]:
    sys.path.insert(0, str(root))
    from merdian_compute import cycle as Y, gamma as G   # noqa: E402
    mods = {"gamma": G, "cycle": Y}
    try:                                                  # S101 C3; absent on a C2-only tree
        from merdian_compute import volatility as VOL      # noqa: E402
        mods["volatility"] = VOL
    except ImportError:
        VOL = None
    try:                                                  # S101 C4
        from merdian_compute import pin as PIN             # noqa: E402
        mods["pin"] = PIN
    except ImportError:
        PIN = None
    errs: list[str] = []

    for key, want in SIGNATURES.items():
        m, n = key.split(".")
        if m not in mods:
            errs.append(f"signature {key}: module merdian_compute.{m} missing")
            continue
        got = str(inspect.signature(getattr(mods[m], n)))
        if got != want:
            errs.append(f"signature {key}: {got}")
    if list(G.GammaMetricsResult.__dataclass_fields__) != RESULT_FIELDS:
        errs.append(f"GammaMetricsResult fields {list(G.GammaMetricsResult.__dataclass_fields__)}")

    rows_core = rows_pin = rows_vel = rows_iv = excluded = 0
    if PIN is not None:                                   # 4. the pin path, against the ruled rule
        th = {"nopin_conc_floor": 0.10, "stable_held_for": 3, "locked_held_for": 6, "locked_ratio_max": 0.50}
        ladder = [  # (held, ratio, conc) -> (state, reason); thresholds th
            ((5, 0.2, 0.09), ("NO PIN", None)), ((5, 0.2, 0.10), ("STABLE", None)),   # conc == floor: not NO PIN; 5 >= 3; 5 < 6
            ((2, 0.2, 0.30), ("SHIFTING", None)), ((3, 0.2, 0.30), ("STABLE", None)),
            ((6, 0.50, 0.30), ("LOCKED", None)), ((6, 0.51, 0.30), ("STABLE", None)),
            ((5, 0.10, 0.30), ("STABLE", None)), ((9, None, 0.30), ("STABLE", None)),
            ((9, 0.1, None), (None, "null input: conc_top1_share")),
            ((None, 0.1, 0.3), (None, "null input: held_for_cycles")),
        ]
        for (h, r, c), want in ladder:
            got = PIN.derive_core(h, r, c, **th)
            if tuple(got) != want:
                errs.append(f"pin ladder {(h, r, c)}: got {got} want {want}")
        Y2 = mods["cycle"]
        carry = [("OPEN", 100.0, [], 1), ("OPEN", 100.0, [{"pin_leader_strike": 100, "held_for_cycles": 4}], 5),
                 ("OPEN", 100.0, [{"pin_leader_strike": 150, "held_for_cycles": 4}], 1),
                 ("OPEN", None, [], None), ("FROZEN", 100.0, [], None),
                 ("OPEN", 100.0, [{"pin_leader_strike": "100.0", "held_for_cycles": None}], 1)]
        for st, ld, rows, want in carry:
            got = Y2.held_for_cycles_next(st, ld, rows)
            if got != want:
                errs.append(f"carry-forward {(st, ld, rows)}: got {got} want {want}")
        from datetime import date as _d
        cal = {"2026-10-26": True, "2026-10-27": False, "2026-10-29": True}   # 10-28 has no row
        got = Y2.trading_days_between(_d(2026, 10, 25), _d(2026, 10, 29), lambda iso: cal.get(iso, True))
        if got != 3:   # 10-26 open, 10-27 closed, 10-28 no row = open (fail-open), 10-29 open
            errs.append(f"trading_days_between fail-open count: got {got} want 3")
    for day in sorted(p for p in GOLDEN.iterdir() if p.is_dir()):
        sym = day.name.split("_")[1]
        with gzip.open(day / "inputs" / "ocs.csv.gz", "rt", newline="") as g:
            ocs = list(csv.DictReader(io.StringIO(g.read())))
        by_run: dict[str, list] = {}
        for r in ocs:
            if r["symbol"] == sym:
                for c in ("ts", "created_at"):          # psql CSV form -> the ISO form PostgREST serves
                    r[c] = _ts(r[c]).isoformat() if r[c] else r[c]
                by_run.setdefault(r["run_id"], []).append(r)
        if VOL is not None:                               # 3. the wall input, per frozen volatility row
            with gzip.open(day / "inputs" / "volatility.csv.gz", "rt", newline="") as g:
                vol_rows = list(csv.DictReader(io.StringIO(g.read())))
            by_all: dict[str, list] = {}
            for r in ocs:
                by_all.setdefault(r["run_id"], []).append(r)
            for prod in vol_rows:
                chain = by_all.get(prod["source_run_id"])
                if not chain:
                    continue
                res = VOL.derive_atm_iv(sorted(chain, key=lambda r: float(r["strike"])))
                rows_iv += 1
                for f in ("atm_strike", "atm_call_iv", "atm_put_iv", "atm_iv_avg", "iv_skew"):
                    got = res.get(f) if res["error"] is None else None
                    if not _same(got, prod[f]):
                        errs.append(f"{day.name} {prod['ts']} {f}: got {got!r} production {prod[f]!r}")
        with gzip.open(day / "inputs" / "gamma_metrics.csv.gz", "rt", newline="") as g:
            gm = sorted(csv.DictReader(io.StringIO(g.read())), key=lambda r: _ts(r["ts"]))
        for i, prod in enumerate(gm):
            chain = by_run.get(prod["run_id"])
            if not chain:
                continue
            # --- the retail path: chain + its own history -> ONE composed call ------
            recent = [float(r["max_gamma_strike"]) for r in gm[max(0, i - 5):i] if r["max_gamma_strike"]]
            prior = ({"straddle_atm": float(gm[i - 1]["straddle_atm"]) if gm[i - 1]["straddle_atm"] else None}
                     if i > 0 else None)
            res = G.compute_gamma_core(**G.prepare_gamma_inputs(chain, prod["run_id"], expected_symbol=sym),
                                       run_type="FULL", prior_row=prior, spot_vs_range=None, vix=None,
                                       recent_max_strikes=recent)
            rows_core += 1
            for f in CORE:
                got = getattr(res, f)
                if not _same(got, prod[f]):
                    errs.append(f"{day.name} {prod['ts']} {f}: got {got!r} production {prod[f]!r}")
            if i > 0:
                rows_vel += 1
                if not _same(res.straddle_velocity, prod["straddle_velocity"]):
                    errs.append(f"{day.name} {prod['ts']} straddle_velocity: got {res.straddle_velocity!r} "
                                f"production {prod['straddle_velocity']!r}")
            if i < 5:
                excluded += 1
                continue
            if len(recent) != 5:
                errs.append(f"{day.name} row {i}: {len(recent)} priors with a non-empty max_gamma_strike, want 5")
            rows_pin += 1
            if not _same(res.pin_risk_score, prod["pin_risk_score"]):
                errs.append(f"{day.name} {prod['ts']} pin_risk_score: got {res.pin_risk_score!r} "
                            f"production {prod['pin_risk_score']!r}")
    if rows_core == 0 or rows_pin == 0 or rows_vel == 0 or rows_iv == 0:
        errs.append(f"nothing compared (core {rows_core}, pin {rows_pin}, velocity {rows_vel}, iv {rows_iv})")
    print(f"  signatures {len(SIGNATURES)} + result fields; core rows {rows_core} x {len(CORE)} fields; "
          f"pin rows {rows_pin} (excluded by rule {excluded}); straddle_velocity rows {rows_vel}; "
          f"ATM IV rows {rows_iv} x 5 fields")
    return errs


MUTANTS = [
    ("M1 Crore divisor", "gamma.py", "(spot ** 2) / 1e7", "(spot ** 2) / 1.0000001e7", "net_gex"),
    ("M2 flip dominance floor", "gamma.py", "_FLIP_DOMINANCE_EPS_FRAC = 0.01", "_FLIP_DOMINANCE_EPS_FRAC = 0.5", "flip_level"),
    ("M3 pin-risk weight", "gamma.py", "components.append((0.30, float(gamma_concentration)))",
     "components.append((0.31, float(gamma_concentration)))", "pin_risk_score"),
    ("M4 parameter renamed", "cycle.py", "def boost(t_days: float) -> float:", "def boost(t: float) -> float:\n    t_days = t", "signature cycle.boost"),
    ("M5 result field order", "gamma.py", "    net_gex: float\n    gamma_concentration: float | None\n",
     "    gamma_concentration: float | None\n    net_gex: float\n", "GammaMetricsResult fields"),
    ("M6 statement in the core", "gamma.py", "flip_distance_pct = abs(flip_distance) / spot * 100.0 if spot > 0 else None",
     "flip_distance_pct = abs(flip_distance) / spot * 100.1 if spot > 0 else None", "flip_distance_pct"),
    ("M7 ATM IV average", "volatility.py", "atm_iv_avg = (atm_call_iv + atm_put_iv) / 2.0",
     "atm_iv_avg = (atm_call_iv + atm_put_iv) / 2.001", "atm_iv_avg"),
    ("M8 pin NO PIN boundary", "pin.py", "    if conc_top1_share < nopin_conc_floor:",
     "    if conc_top1_share <= nopin_conc_floor:", "pin ladder"),
    ("M9 carry-forward step", "cycle.py", '        return int(prev.get("held_for_cycles") or 0) + 1',
     '        return int(prev.get("held_for_cycles") or 0) + 2', "carry-forward"),
]


def main() -> int:
    if "--check-root" in sys.argv:                       # child: one tree, print errors, exit 1 on any
        errs = check(Path(sys.argv[sys.argv.index("--check-root") + 1]))
        for e in errs[:5]:
            print("  ERR", e)
        print(f"  {len(errs)} contract errors")
        return 1 if errs else 0

    fails = 0
    r = subprocess.run([sys.executable, "-I", __file__, "--check-root", str(ROOT)], capture_output=True, text=True)
    print(r.stdout.rstrip())
    ok = r.returncode == 0
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  control: merdian_compute vs production golden rows")
    if not ok:
        print(r.stderr[-1500:])

    for label, rel, old, new, reason in MUTANTS:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            shutil.copytree(ROOT / "merdian_compute", t / "merdian_compute",
                            ignore=shutil.ignore_patterns("__pycache__"))
            (t / "tests").mkdir()
            (t / "tests" / "golden").symlink_to(GOLDEN)
            p = t / "merdian_compute" / rel
            s = p.read_text()
            if s.count(old) != 1:
                print(f"FAIL  {label}: MUTANT NOT APPLIED (anchor count {s.count(old)})")
                fails += 1
                continue
            p.write_text(s.replace(old, new))
            shutil.copy(__file__, t / "tests" / Path(__file__).name)
            r = subprocess.run([sys.executable, "-I", str(t / "tests" / Path(__file__).name),
                                "--check-root", str(t)], capture_output=True, text=True)
        caught = r.returncode == 1 and reason in r.stdout
        fails += not caught
        first = next((ln.strip() for ln in r.stdout.splitlines() if "ERR" in ln), r.stderr.strip()[-120:])
        print(f"{'PASS' if caught else 'FAIL'}  mutant {label:24} must break {reason:26} -> {first[:110]}")

    print(f"CONTRACT {'ALL PASS' if not fails else f'FAIL ({fails})'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
