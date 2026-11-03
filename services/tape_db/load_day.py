#!/usr/bin/env python3
"""Tape T1-db loader: one processed day -> the six tape_* sidecar tables (docs/tape/T1_db_plan.md section 1.4).

  python services/tape_db/load_day.py --day 2026-11-02 --out C:\\tape_data\\out_2026-11-02
      --cyc C:\\tape_data\\cyc_2026-11-02 --chain C:\\tape_data\\chain_2026-11-02\\events
      --session C:\\tape_data\\2026-11-02\\session [--replace]

Steps: verify the three run_manifest.json files against the files on disk (refuse before any client call); parse;
refuse an existing day unless --replace (then record superseded run_ids and delete the day table by table); insert in
batches of <= 1,000; read back count(*) per table for the day and compare with the CSV row counts; one ledger row
(script_execution_log, via core.execution_log, kind=run, product=tape_day).

Exit 0 all LOAD PASS; 1 LOAD FAIL (a count mismatch or a failed write); 2 usage / refused (day exists, no git sha);
3 manifest or input refused (nothing touched).

Writes ONLY the tape_* tables named in tape_schema.ORDER (script_execution_log is written by ExecutionLog). Reads only
local files and count / run_id of those tables. Never combines a tape-side and a chain-side relation
(pre-registration v0.2). core.supabase_client and core.execution_log load .env at import, so they are imported
inside main() and only when no client / ledger is injected (tests inject fakes).
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from merdian_compute.tape import replay  # noqa: E402
from services.tape_db import tape_schema as S  # noqa: E402

SCRIPT = "load_day.py"
BATCH = 1000
PAGE = 1000
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Refused(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


# ------------------------------------------------------------------------------------------- manifests
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _read_manifest(d, label):
    p = os.path.join(d, "run_manifest.json")
    if not os.path.isfile(p):
        raise Refused(3, "MANIFEST FAIL %s: no run_manifest.json in %s" % (label, d))
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh), sha256_file(p)
    except ValueError as exc:
        raise Refused(3, "MANIFEST FAIL %s: unreadable run_manifest.json: %s" % (label, exc))


def _session_file(session, day, name):
    for p in (os.path.join(session, day, name), os.path.join(session, name)):
        if os.path.isfile(p):
            return p
    return None


def verify_manifests(day, out, cyc, chain, session):
    """Return {label: (manifest, manifest_sha256)}. Raises Refused(3) on the first set of problems."""
    mans = {}
    problems = []
    for label, d in (("out", out), ("cyc", cyc), ("chain", chain)):
        man, msha = _read_manifest(d, label)
        mans[label] = (man, msha)
        if (man.get("args") or {}).get("day") != day:
            problems.append("%s: manifest day %r != --day %s" % (label, (man.get("args") or {}).get("day"), day))
        for name, want in sorted((man.get("outputs") or {}).items()):
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                problems.append("%s: output %s missing" % (label, name))
            elif sha256_file(p) != want:
                problems.append("%s: output %s sha256 mismatch" % (label, name))
    want_out = {"out": ("tape_minute.csv", "g3_report.json"), "cyc": ("tape_strike_cycle.csv", "tape_events.csv"),
                "chain": ("chain_events.csv", "chain_runs.csv")}
    for label, names in want_out.items():
        for n in names:
            if n not in (mans[label][0].get("outputs") or {}):
                problems.append("%s: manifest does not list %s" % (label, n))
    # inputs: T1a session files, T1b cycle in/ + session/, chain exports in the parent of --chain
    for e in mans["out"][0].get("inputs") or []:
        path = e.get("path", "")
        pre = "session/%s/" % day
        if path.startswith(pre):
            p = _session_file(session, day, path[len(pre):])
            if p is None:
                problems.append("out: input %s not found under --session" % path)
            elif sha256_file(p) != e.get("sha256"):
                problems.append("out: input %s sha256 mismatch" % path)
    for e in mans["cyc"][0].get("inputs") or []:
        path = e.get("path", "")
        if path == "in/tape_minute.csv":
            p = os.path.join(out, "tape_minute.csv")
        elif path.startswith("session/"):
            p = _session_file(session, day, path[len("session/"):])
        else:
            p = None
        if p is None or not os.path.isfile(p):
            problems.append("cyc: input %s not found" % path)
        elif sha256_file(p) != e.get("sha256"):
            problems.append("cyc: input %s sha256 mismatch (cycle was not built from these files)" % path)
    parent = os.path.dirname(os.path.abspath(chain))
    for e in mans["chain"][0].get("inputs") or []:
        p = os.path.join(parent, e.get("path", ""))
        if not os.path.isfile(p):
            problems.append("chain: input %s not found in %s" % (e.get("path"), parent))
        elif sha256_file(p) != e.get("sha256"):
            problems.append("chain: input %s sha256 mismatch" % e.get("path"))
    if problems:
        raise Refused(3, "MANIFEST FAIL (%d problems): %s" % (len(problems), "; ".join(problems[:10])))
    return mans


# ------------------------------------------------------------------------------------------- typed rows
def convert(typ, v):
    if v is None or v == "":
        return None
    if typ in ("bigint", "integer", "smallint"):
        return int(v)
    if typ == "double precision":
        return float(v)
    if typ == "boolean":
        if v in ("1", "true", "t"):
            return True
        if v in ("0", "false", "f"):
            return False
        raise ValueError("not a boolean: %r" % v)
    if typ == "jsonb":
        return json.loads(v)
    return v  # text, numeric (exact text), date, timestamptz, uuid


def _read_csv(path, cols):
    with open(path, encoding="utf-8", newline="") as fh:
        text = fh.read()
    rd = csv.reader(io.StringIO(text))
    header = next(rd, None)
    if header is None or tuple(header) != tuple(cols):
        raise Refused(3, "INPUT FAIL %s: header %s != %s" % (os.path.basename(path), header, list(cols)))
    return [dict(zip(cols, r)) for r in rd if r]


def csv_rows(table, path, day):
    t = S.TABLES[table]
    types = S.db_types(table)
    out = []
    for raw in _read_csv(path, t["cols"]):
        row = {}
        for c in t["cols"]:
            dbc = t["rename"].get(c, c)
            v = raw[c]
            if table == "tape_minute" and c == "minute":
                v = "%sT%s:00+05:30" % (day, v)
            row[dbc] = convert(types[dbc], v)
        if "trading_day" in t["added"]:
            row["trading_day"] = day
        elif row.get("trading_day") != day:
            raise Refused(3, "INPUT FAIL %s: row day %r != --day %s" % (t["csv"], row.get("trading_day"), day))
        out.append(row)
    return out


def daily_rows(day, out, session, t1a_manifest):
    with open(os.path.join(out, "g3_report.json"), encoding="utf-8") as fh:
        g3 = json.load(fh)
    rp = _session_file(session, day, "daily_report_%s.json" % day)
    listed = any(e.get("path") == "session/%s/daily_report_%s.json" % (day, day)
                 for e in t1a_manifest.get("inputs") or [])
    report = None
    if rp is not None:
        if not listed:
            raise Refused(3, "INPUT FAIL daily_report_%s.json exists but the T1a manifest does not list it" % day)
        with open(rp, encoding="utf-8") as fh:
            report = json.load(fh)
    rows = []
    for sym, sec in sorted((g3.get("symbols") or {}).items()):
        rs = ((report or {}).get("symbols") or {}).get(sym) or {}
        up = rs.get("uploads") or {}
        segs = [e for e in t1a_manifest.get("inputs") or []
                if e.get("path", "").startswith("%s/%s/" % (sym, day))
                and replay.parse_seg_name(e["path"].rsplit("/", 1)[-1]) is not None]
        det = sec.get("verdict_detail") or {}

        def ln(v):
            return len(v) if isinstance(v, (list, dict)) else v

        rows.append({
            "symbol": sym, "trading_day": day, "completeness_pct": None,
            "gaps_gt_10s": ln(rs.get("feed_gaps_gt10s")), "gaps_gt_60s": ln(rs.get("feed_gaps_gt60s")),
            "packets": rs.get("packets"), "segments": len(segs),
            "uploads_ok": up.get("ok"), "uploads_retried": up.get("retried"), "uploads_failed": up.get("failed"),
            "skew_median_s": (rs.get("clock_skew") or {}).get("median_s"),
            "connects": None, "reconnects": ln((report or {}).get("reconnects")),
            "disconnects": ln((report or {}).get("disconnects")), "watchdog_trips": None, "frame_errors": None,
            "g3_verdict": sec.get("verdict"),
            "classified_share_early": (det.get("early") or {}).get("share_pct"),
            "classified_share_late": (det.get("late") or {}).get("share_pct"),
            "report": report, "g3": sec})
    return rows


def build_all(day, out, cyc, chain, session, mans):
    dirs = {"out": out, "cyc": cyc, "chain": chain}
    rows = {}
    for table in S.ORDER:
        if table == "tape_daily_report":
            rows[table] = daily_rows(day, out, session, mans["out"][0])
        else:
            t = S.TABLES[table]
            rows[table] = csv_rows(table, os.path.join(dirs[t["src"]], t["csv"]), day)
    return rows


# ------------------------------------------------------------------------------------------- client I/O
def count_exact(client, table, filters):
    if hasattr(client, "count_exact"):
        return client.count_exact(table, filters)
    import requests
    h = dict(client.headers)
    h["Prefer"] = "count=exact"
    h["Range"] = "0-0"
    params = {"select": "run_id", **{k: client._normalize_filter_value(v) for k, v in filters.items()}}
    r = requests.get(client._url(table), headers=h, params=params, timeout=60)
    r.raise_for_status()
    return int(r.headers["Content-Range"].split("/")[-1])


def distinct_run_ids(client, table, day):
    seen, off = set(), 0
    while True:
        page = client.select(table, columns="run_id", filters={"trading_day": "eq.%s" % day},
                             order="run_id", limit=PAGE, offset=off)
        seen.update(str(r["run_id"]) for r in page)
        off += len(page)
        if len(page) < PAGE:
            return sorted(seen)


def git_info():
    def git(*a):
        try:
            r = subprocess.run(["git", "-C", _ROOT] + list(a), capture_output=True, text=True, timeout=30)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    sha = git("rev-parse", "HEAD")
    st = git("status", "--porcelain", "--", "services/tape_db", "merdian_compute/tape", "sql")
    return sha, (None if st is None else bool(st))


def _default_client():
    from core.supabase_client import SupabaseClient
    return SupabaseClient()


def _default_ledger(**kw):
    from core.execution_log import ExecutionLog
    return ExecutionLog(**kw)


# ------------------------------------------------------------------------------------------- main
def main(argv=None, client=None, ledger_factory=None, git=None):
    """client / ledger_factory / git are injected by tests only; production passes nothing."""
    ap = argparse.ArgumentParser(prog="load_day", description=__doc__.split("\n")[0])
    ap.add_argument("--day", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cyc", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args(argv)
    day = a.day
    if not DAY_RE.match(day):
        print("REFUSED: bad --day %r" % day)
        return 2
    out, cyc, chain, session = (os.path.abspath(p) for p in (a.out, a.cyc, a.chain, a.session))

    # 1-2. manifests and parse: no client call before this succeeds
    try:
        mans = verify_manifests(day, out, cyc, chain, session)
        for label in ("out", "cyc", "chain"):
            print("MANIFEST PASS %s sha256=%s" % (label, mans[label][1]))
        rows = build_all(day, out, cyc, chain, session, mans)
    except Refused as exc:
        print(str(exc))
        print("LOAD REFUSED (exit %d): nothing was read from or written to the database" % exc.code)
        return exc.code
    csv_n = {t: len(rows[t]) for t in S.ORDER}
    for t in S.ORDER:
        print("PARSED %s rows=%d" % (t, csv_n[t]))

    code_sha, dirty = (git or git_info)()
    if not code_sha or not re.match(r"^[0-9a-f]{40}$", code_sha):
        print("REFUSED: cannot read git rev-parse HEAD (code_sha is NOT NULL and never typed)")
        return 2

    if client is None:
        client = _default_client()

    # 3. existing day
    existing = {}
    for t in S.ORDER:
        existing[t] = count_exact(client, t, {"trading_day": "eq.%s" % day})
        print("EXISTING %s rows=%d" % (t, existing[t]))
    if any(existing.values()) and not a.replace:
        print("REFUSED: trading_day %s already loaded (use --replace); 0 writes" % day)
        return 2

    # 4. ledger
    run_id = str(uuid.uuid4())
    loaded_at = datetime.now(timezone.utc).isoformat()
    ledger = (ledger_factory or _default_ledger)(
        script_name=SCRIPT, expected_writes=dict(csv_n), symbol=None, run_id=run_id, product_relation="tape_day",
        notes="tape T1-db load day=%s" % day)
    notes = {"day": day, "run_id": run_id, "code_sha": code_sha, "dirty": dirty, "replace": bool(a.replace),
             "manifests": {k: {"sha256": v[1], "code": v[0].get("code")} for k, v in mans.items()},
             "csv_rows": csv_n, "superseded_run_ids": {}}
    prov = {"run_id": run_id, "code_sha": code_sha, "source": S.SOURCE, "config_version": None,
            "loaded_at": loaded_at}
    fails = []
    try:
        # 5. replace
        if a.replace and any(existing.values()):
            for t in S.ORDER:
                if existing[t]:
                    ids = distinct_run_ids(client, t, day)
                    notes["superseded_run_ids"][t] = ids
                    print("SUPERSEDED %s run_ids=%s" % (t, ids))
            for t in S.ORDER:
                if existing[t]:
                    client.delete(t, {"trading_day": "eq.%s" % day})
                    left = count_exact(client, t, {"trading_day": "eq.%s" % day})
                    print("DELETE %s trading_day=%s left=%d" % (t, day, left))
                    if left:
                        fails.append("%s: %d rows left after delete" % (t, left))
            if fails:
                raise RuntimeError("; ".join(fails))
        # 6. insert
        for t in S.ORDER:
            cols = S.db_columns(t)
            body = [dict({c: r.get(c) for c in cols if c not in prov}, **prov) for r in rows[t]]
            nb = 0
            for i in range(0, len(body), BATCH):
                client.insert(t, body[i:i + BATCH])
                nb += 1
            ledger.record_write(t, len(body))
            print("INSERT %s rows=%d batches=%d" % (t, len(body), nb))
        # 7. read back
        got = {}
        for t in S.ORDER:
            got[t] = count_exact(client, t, {"trading_day": "eq.%s" % day})
            if got[t] == csv_n[t]:
                print("LOAD PASS %s rows=%d == csv=%d" % (t, got[t], csv_n[t]))
            else:
                print("LOAD FAIL %s rows=%d != csv=%d" % (t, got[t], csv_n[t]))
                fails.append("%s rows=%d != csv=%d" % (t, got[t], csv_n[t]))
        notes["db_rows"] = got
    except Exception as exc:  # a failed write is a LOAD FAIL, recorded, never swallowed
        fails.append("%s: %s" % (type(exc).__name__, str(exc)[:500]))
        print("LOAD FAIL %s" % fails[-1])
    notes["fails"] = fails
    if fails:
        ledger.exit_with_reason("DATA_ERROR", exit_code=1, notes=json.dumps(notes, sort_keys=True),
                                error_message="; ".join(fails))
        print("TAPE T1-DB LOAD FAIL day=%s run_id=%s" % (day, run_id))
        return 1
    ledger.complete(notes=json.dumps(notes, sort_keys=True))
    print("TAPE T1-DB LOAD PASS day=%s run_id=%s code_sha=%s" % (day, run_id, code_sha))
    return 0


if __name__ == "__main__":
    sys.exit(main())
