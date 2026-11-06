"""Tape live verify step V (spec s5; docs/tape/L0_plan.md section 8 O-6). Consistency only.

After the offline day is final, recompute every label from the FINAL cycle rows, event rows and chain runs with the same
rule_version, and compare it with the stored as-seen label. One summary per symbol-day (labels compared, matched, match %,
missing) and every difference with ONE cause, the first that applies:
  rule_drift         the stored flags, labelled again, do not give the stored label (page vs Python, or a changed rule)
  chain_run_differs  the live wall row names another chain run or other walls than the final run for that grid point
  late_segment       a segment whose 5-minute slot starts before T arrived after cycle T (from the replay manifest)
  partial_cycle      the stored flags differ from the final flags and none of the above holds (data at the frontier)
  other              anything else
It says nothing about whether a wall held or broke; that needs data this step never reads.

verify() is pure. run() reads the files named on the command line (the CLI passes them) and writes verify_report.json/.txt.
Exit 0 every difference is explained (no rule_drift, no other); 1 otherwise; 2 input error.
"""
import csv
import json
import os

from merdian_compute.tape import cycle
from services.tape_live import rules, wall_source

CAUSES = ("rule_drift", "chain_run_differs", "late_segment", "partial_cycle", "other")


def _hm(m):
    return "%02d:%02d" % (m // 60, m % 60)


def _num(s):
    return None if s in (None, "") else float(s)


def _walls_differ(lw, fw):
    if (lw is None) != (fw is None):
        return True
    if lw is None:
        return False
    return (lw["chain_run_id"] != fw["chain_run_id"] or _num(lw["call_wall"]) != _num(fw["call_wall"])
            or _num(lw["put_wall"]) != _num(fw["put_wall"]))


def _cause(stored, final_flags, live_wall, final_wall, late, sym, tm):
    sf = json.loads(stored["flags"])
    st = (stored["label"], stored["partial"] == "true", stored["reason"])
    if tuple(rules.label_wall(sf)) != st:
        return "rule_drift"
    if _walls_differ(live_wall, final_wall):
        return "chain_run_differs"
    for l in late:
        h = int(l["hhmm"][:2]) * 60 + int(l["hhmm"][3:])
        if l["symbol"] == sym and h < tm < l["arrived"]:
            return "late_segment"
    if sf != final_flags:
        return "partial_cycle"
    return "other"


def verify(day, stored, live_walls, final_rows, final_events, final_runs, late):
    """stored: label rows (dicts of strings); live_walls: {(symbol, ts_ist): wall row}; final_rows / final_events: dicts of
    strings as the offline CSVs render them; final_runs: {symbol: runs} from wall_source; late: manifest late_segments."""
    by_c, by_e = {}, {}
    for r in final_rows:
        by_c.setdefault(r["symbol"], []).append(r)
    for r in final_events:
        by_e.setdefault(r["symbol"], []).append(r)
    st = {(r["symbol"], r["ts_ist"], r["wall"]): r for r in stored if r["rule_version"] == rules.RULE_VERSION}
    syms = sorted(set(by_c) | {k[0] for k in st})
    diffs, summary = [], {}
    for sym in syms:
        s = {"compared": 0, "matched": 0, "missing": 0, "differences": {c: 0 for c in CAUSES}, "labels": {}}
        for tm in range(cycle.FIRST_T, cycle.LAST_T + 1, cycle.STEP):
            T = cycle.ts_of(day, tm)
            fw = wall_source.wall_row(final_runs.get(sym, []), day, _hm(tm))
            for wall in ("call", "put"):
                ff = rules.derive_flags(by_c.get(sym, []), by_e.get(sym, []), fw, T, wall)
                fl = tuple(rules.label_wall(ff))
                row = st.get((sym, T, wall))
                if row is None:
                    s["missing"] += 1
                    continue
                s["compared"] += 1
                s["labels"][row["label"]] = s["labels"].get(row["label"], 0) + 1
                got = (row["label"], row["partial"] == "true", row["reason"])
                if got == fl:
                    s["matched"] += 1
                    continue
                cause = _cause(row, ff, live_walls.get((sym, T)), fw, late, sym, tm)
                s["differences"][cause] += 1
                diffs.append({"symbol": sym, "trading_day": day, "ts_ist": T, "wall": wall, "cause": cause,
                              "stored": {"label": got[0], "partial": got[1], "reason": got[2]},
                              "final": {"label": fl[0], "partial": fl[1], "reason": fl[2]},
                              "flags_changed": sorted(k for k, v in json.loads(row["flags"]).items() if ff.get(k) != v)})
        s["match_pct"] = round(100.0 * s["matched"] / s["compared"], 2) if s["compared"] else None
        s["labels"] = dict(sorted(s["labels"].items()))
        summary[sym] = s
    tot = {"compared": sum(v["compared"] for v in summary.values()), "matched": sum(v["matched"] for v in summary.values()),
           "missing": sum(v["missing"] for v in summary.values()), "differences": len(diffs),
           "by_cause": {c: sum(v["differences"][c] for v in summary.values()) for c in CAUSES}}
    unexplained = tot["by_cause"]["rule_drift"] + tot["by_cause"]["other"]
    return {"schema": "tape_live_verify_v1", "day": day, "rule_version": rules.RULE_VERSION, "symbols": summary,
            "totals": tot, "differences": diffs, "verdict": "EXPLAINED" if not unexplained else "UNEXPLAINED"}


def _csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def render_text(rep):
    L = ["MERIDIAN tape live - verify for %s (rules %s): display only, never scored" % (rep["day"], rep["rule_version"]), ""]
    for sym, s in rep["symbols"].items():
        L.append("%s: %d/%d labels match (%s %%), %d grid points without a stored label; differences %s; labels %s" % (
            sym, s["matched"], s["compared"], s["match_pct"], s["missing"],
            json.dumps({k: v for k, v in s["differences"].items() if v}, sort_keys=True), json.dumps(s["labels"], sort_keys=True)))
    L.append("")
    for d in rep["differences"]:
        L.append("  %s %s %-4s %-17s stored %s%s final %s%s  changed %s" % (
            d["symbol"], d["ts_ist"][11:16], d["wall"], d["cause"], d["stored"]["label"], "*" if d["stored"]["partial"] else "",
            d["final"]["label"], "*" if d["final"]["partial"] else "", ",".join(d["flags_changed"])))
    L.append("VERIFY %s (%d differences, %d unexplained)" % (
        rep["verdict"], rep["totals"]["differences"], rep["totals"]["by_cause"]["rule_drift"] + rep["totals"]["by_cause"]["other"]))
    return "\n".join(L) + "\n"


def run(day, live_dir, final_cycle, final_events, final_chain_runs, report_dir):
    stored = _csv(os.path.join(live_dir, "tape_live_label.csv"))
    walls = {(r["symbol"], r["ts_ist"]): r for r in _csv(os.path.join(live_dir, "tape_live_wall.csv"))}
    with open(os.path.join(live_dir, "run_manifest.json"), encoding="utf-8") as fh:
        late = json.load(fh).get("late_segments", [])
    rep = verify(day, stored, walls, _csv(final_cycle), _csv(final_events),
                 wall_source.runs_from_chain_runs_csv(final_chain_runs), late)
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, "verify_report.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    text = render_text(rep)
    with open(os.path.join(report_dir, "verify_report.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text, end="")
    return 0 if rep["verdict"] == "EXPLAINED" else 1
