#!/usr/bin/env python3
"""Scores the T0.1 rehearsal scenarios (docs/tape/T0_1_plan.md section 4). P1-P6 stay in verify_rehearsal.py,
unchanged.

  P7  python3 run_rehearsal.py --schedule 2x:6m --silence 120:40            (socket silent 40 s, no close)
      python3 verify_p7_p8.py --scenario silent --run <out>/<id>
  P8  python3 run_rehearsal.py --schedule 2x:9m --special --terminate-after 450
      python3 verify_p7_p8.py --scenario special --run <out>/<id>

P7 passes only when ALL hold: exactly one watchdog trip; detection delay (trip - last pre-silence packet) in
[15, 20] s; control lines in order watchdog < disconnect < connect; packets resume; every token's rehearsal_seq
contiguous and equal to what was sent (no loss, no duplicate); daily report: trips 1, errors 0, connects 2,
disconnects 1; exit 0.
P8 passes only when ALL hold: the SESSION line shows the calendar's window (start = open-25 min, closed check =
open+5, stop = close+10); the closed check ran at open+5 min (not earlier) with verdict OPEN; exit 0; packets
were recorded; no watchdog trip on the continuous feed.
Last line: "REHEARSAL P7|P8 VERDICT PASS|FAIL|INCOMPLETE". Exit 0 / 1 / 3. A criterion that cannot be measured is
INCOMPLETE, never a pass.
"""
import argparse
import glob
import gzip
import json
import os
import re
import sys

SEG_RE = re.compile(r"^seg_(\d{4})(?:_c\d+)?(?:_r\d+)?\.ndjson\.gz$")


def secs(hms):
    h, m, s = (int(x) for x in hms.split(":"))
    return h * 3600 + m * 60 + s


def hm_secs(hm):
    h, m = (int(x) for x in hm.split(":"))
    return h * 3600 + m * 60


def scan_keep(keep, day, sent):
    """Streams every kept segment line by line (a 6-minute 2x run is ~280k packets: holding the records
    would not fit the 700 MB virtual-memory limit). Keeps only what the checks read: NIFTY packet receive
    times, every ctl line, and a per-token sequence bitmap."""
    pk, ctl = [], []
    seen = {t: bytearray(n) for t, n in sent.items()}
    dup = unknown = beyond = 0
    for sym in ("NIFTY", "SENSEX"):
        d = os.path.join(keep, sym, day)
        for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not SEG_RE.match(name):
                continue
            with gzip.open(os.path.join(d, name), "rt", encoding="utf-8") as fh:
                for line in fh:
                    if '"k":"ctl"' in line:
                        if sym == "NIFTY":
                            r = json.loads(line)
                            ctl.append((r["recv_ns"], r["ctl"], r))
                        continue
                    if '"k":"pkt"' not in line:
                        continue
                    r = json.loads(line)
                    if sym == "NIFTY":
                        pk.append(r["recv_ns"])
                    arr = seen.get(r["instrument_token"])
                    seq = r.get("rehearsal_seq")
                    if arr is None:
                        unknown += 1
                    elif seq is None or seq >= len(arr):
                        beyond += 1
                    elif arr[seq]:
                        dup += 1
                    else:
                        arr[seq] = 1
    missing = sum(len(a) - sum(a) for a in seen.values())
    return sorted(pk), ctl, {"missing": missing, "dup": dup, "unknown": unknown, "beyond": beyond,
                             "tokens": len(sent), "sent": sum(sent.values())}


def p7(run_dir, run, res):
    keep = os.path.join(run["keep"], run["prefix"])
    day = run["day"]
    sent = {int(k): v for k, v in json.load(open(os.path.join(run_dir, "sent.json"))).items()}
    pk, ctl, seqres = scan_keep(keep, day, sent)
    if len(pk) < 100:
        res.append(("packets recorded", None, "only %d NIFTY packets kept" % len(pk)))
        return
    gaps = sorted(((b - a, a, b) for a, b in zip(pk, pk[1:])), reverse=True)
    gap, last_pre, first_post = gaps[0]
    wd = [c for c in ctl if c[1] == "watchdog"]
    dis = [c for c in ctl if c[1] == "disconnect"]
    con = [c for c in ctl if c[1] == "connect" and not c[2].get("first")]
    res.append(("exactly one watchdog trip", len(wd) == 1, "ctl watchdog lines: %d" % len(wd)))
    delay = (wd[0][0] - last_pre) / 1e9 if wd else None
    res.append(("detection delay in [15, 20] s", delay is not None and 15 <= delay <= 20,
                "last packet -> trip: %s s (largest gap %.1f s)" % (None if delay is None else round(delay, 2), gap / 1e9)))
    ordered = bool(wd and dis and con) and wd[0][0] <= dis[0][0] < con[0][0] <= first_post
    res.append(("order watchdog < disconnect < connect < first packet after", ordered,
                "watchdog %d, disconnect %d, connect %d" % (len(wd), len(dis), len(con))))
    res.append(("packets resume", first_post > last_pre and (pk[-1] - first_post) / 1e9 > 30,
                "recording continued %.0f s after the reconnect" % ((pk[-1] - first_post) / 1e9)))
    s = seqres
    res.append(("every token's sequence contiguous, none lost or duplicated",
                s["missing"] == 0 and s["dup"] == 0 and s["unknown"] == 0 and s["beyond"] == 0,
                "sent %d packets over %d tokens; missing %d, duplicated %d, unknown-token %d, beyond-sent %d"
                % (s["sent"], s["tokens"], s["missing"], s["dup"], s["unknown"], s["beyond"])))
    rp = os.path.join(keep, "session", day, "daily_report_%s.json" % day)
    if not os.path.exists(rp):
        res.append(("daily report", None, "missing %s" % rp))
    else:
        d = json.load(open(rp))
        want = (d.get("watchdog_trips"), d.get("watchdog_errors"), d.get("connects"), d.get("disconnects"))
        res.append(("daily report trips/errors/connects/disconnects == 1/0/2/1", want == (1, 0, 2, 1), str(want)))


def p8(run_dir, run, res):
    log = open(os.path.join(run_dir, "driver.log")).read().splitlines()
    ses = [l for l in log if " TAPE SESSION " in l]
    if not ses:
        res.append(("SESSION line", None, "no SESSION line in driver.log"))
        return
    kv = dict(x.split("=", 1) for x in ses[0].split(" TAPE SESSION ", 1)[1].split())
    open_s = hm_secs(run["start_ist"][11:16]) + 60
    close_hm = run["stop_ist"][11:16]
    want = (kv.get("kind"), hm_secs(kv["open"]), hm_secs(kv["start"]), hm_secs(kv["closed_check"]), hm_secs(kv["stop"]))
    exp = ("special", open_s, open_s - 25 * 60, open_s + 5 * 60, hm_secs(close_hm) + 10 * 60)
    res.append(("calendar window drives the timeline", want == exp, "got %s expected %s" % (want, exp)))
    cc = [l for l in log if "CLOSED_CHECK verdict=" in l]
    if len(cc) != 1:
        res.append(("one closed check", None if not cc else False, "%d CLOSED_CHECK lines" % len(cc)))
    else:
        t = secs(cc[0].split()[0])
        res.append(("closed check at open+5 min, never earlier", open_s + 300 <= t <= open_s + 306,
                    "ran at %s, open+5m = %02d:%02d:00" % (cc[0].split()[0], (open_s + 300) // 3600, (open_s + 300) % 3600 // 60)))
        res.append(("closed check verdict OPEN", "verdict=OPEN" in cc[0], cc[0].split("TAPE ", 1)[1][:80]))
    res.append(("exit 0", any("REHEARSAL DONE exit=0" in l for l in log), "driver.log"))
    res.append(("no early start", not any("EARLY_START" in l for l in log), ""))
    hbp = os.path.join(run_dir, "heartbeats.ndjson")
    hbs = [json.loads(l) for l in open(hbp)] if os.path.exists(hbp) else []
    last = hbs[-1] if hbs else {}
    res.append(("packets recorded, no watchdog trip on a continuous feed",
                bool(hbs) and last.get("watchdog_trips") == 0 and any(h.get("packets_last_min", {}).get("NIFTY", 0) > 0 for h in hbs),
                "last heartbeat watchdog_trips=%s" % last.get("watchdog_trips")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True, choices=("silent", "special"))
    ap.add_argument("--run")
    ap.add_argument("--out-root", default="/var/lib/tape/rehearsal_out")
    a = ap.parse_args()
    run_dir = a.run or sorted(glob.glob(os.path.join(a.out_root, "*")))[-1]
    run = json.load(open(os.path.join(run_dir, "run.json")))
    name = "P7" if a.scenario == "silent" else "P8"
    res = []
    (p7 if a.scenario == "silent" else p8)(run_dir, run, res)
    bad = incomplete = 0
    for n, ok, detail in res:
        print("%s %s: %s" % ({True: "PASS", False: "FAIL", None: "NOT EVALUATED"}[ok], n, detail))
        bad += ok is False
        incomplete += ok is None
    verdict = "FAIL" if bad else ("INCOMPLETE" if incomplete or not res else "PASS")
    print("REHEARSAL %s VERDICT %s" % (name, verdict))
    return {"PASS": 0, "FAIL": 1, "INCOMPLETE": 3}[verdict]


if __name__ == "__main__":
    sys.exit(main())
