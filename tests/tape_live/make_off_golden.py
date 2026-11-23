#!/usr/bin/env python3
"""Writes tests/tape_live/off_golden_56bf055.json: what the runner leaves, flag off, at commit 56bf055 (stage 2b guard live-2b-off).

  TAPE_RULE23_OVERRIDE_R1=1 python tests/tape_live/make_off_golden.py [--commit 56bf055] [--out PATH]

The commit is exported with `git -c core.autocrlf=false archive` into a clean temp dir (no working-tree line-ending conversion), the
export's OWN tests/test_tape_live.py is imported, and its fixture run `cli_live_fake("eq_psql")` (cli live, S3 + psql path through
the fake shell, sim clock, code sha pinned to TEST_SHA) is hashed: every non-timing output file, the heartbeat and state.json key
sets and the live_metrics.csv header. The expected value is the OLD tree's output, never the code under test's. Read-only on git,
no database, no network.

Form 2 (operator ruling 1, 2026-11-22): the compressed bytes of a raw .gz segment depend on the platform's zlib and gzip header
(the box writes OS byte 255 on Python 3.10.12; the fixture is generated on each host), so a raw .gz under raw/ is hashed by its
UNZIPPED content, and arrival_log.csv is hashed with its size and etag columns dropped (they are the compressed object's size and
md5). live-2b-off asserts those two columns separately, at run time, against the fixture's own files. Every other non-timing file
is hashed by its bytes. file_digests() is the one implementation both sides use; it is applied here to 56bf055's output only.
"""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FORM = 2
ARRIVAL = "arrival_log.csv"
ARRIVAL_DROPPED = ("size", "etag")


def _csv_text(rows):
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    for r in rows:
        wr.writerow(r)
    return buf.getvalue()


def arrival_without_size_etag(b):
    """arrival_log.csv bytes -> the same table with the size and etag columns removed, as bytes. Raises ValueError when either
    column is missing or the file does not round-trip through the csv module byte for byte (the remaining columns would then not
    be asserted in their written form)."""
    text = b.decode("utf-8")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        raise ValueError("%s is empty" % ARRIVAL)
    if _csv_text(rows) != text:
        raise ValueError("%s does not round-trip through csv byte for byte" % ARRIVAL)
    head = rows[0]
    missing = [c for c in ARRIVAL_DROPPED if c not in head]
    if missing:
        raise ValueError("%s has no %s column (header %s)" % (ARRIVAL, "/".join(missing), head))
    drop = set(head.index(c) for c in ARRIVAL_DROPPED)
    return _csv_text([[v for i, v in enumerate(r) if i not in drop] for r in rows]).encode("utf-8")


def file_digest(dd, rel):
    """sha256 of one output file in form 2: raw/**.gz unzipped, arrival_log.csv without size/etag, anything else as bytes."""
    with open(os.path.join(dd, *rel.split("/")), "rb") as fh:
        b = fh.read()
    if rel.startswith("raw/") and rel.endswith(".gz"):
        b = gzip.decompress(b)
    elif rel == ARRIVAL:
        b = arrival_without_size_etag(b)
    return hashlib.sha256(b).hexdigest()


def file_digests(dd, skip):
    """{relpath: form-2 sha256} over every file under dd except those named in skip (the timing files)."""
    rels = sorted(os.path.relpath(os.path.join(dp, n), dd).replace(os.sep, "/") for dp, _, ns in os.walk(dd) for n in ns)
    return dict((rel, file_digest(dd, rel)) for rel in rels if rel not in skip)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", default="56bf055")
    ap.add_argument("--out", default=os.path.join(REPO, "tests", "tape_live", "off_golden_56bf055.json"))
    a = ap.parse_args()
    full = subprocess.run(["git", "-C", REPO, "rev-parse", "--verify", a.commit + "^{commit}"], capture_output=True, text=True,
                          check=True, timeout=60).stdout.strip()
    tar = subprocess.run(["git", "-C", REPO, "-c", "core.autocrlf=false", "archive", "--format=tar", full], capture_output=True,
                         check=True, timeout=300).stdout
    tmp = tempfile.mkdtemp(prefix="off_golden_")
    try:
        with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
            tf.extractall(tmp)
        sys.argv = ["test_tape_live.py", "--root", tmp]
        sys.path.insert(0, tmp)
        sys.path.insert(0, os.path.join(tmp, "tests", "tape_live"))
        spec = importlib.util.spec_from_file_location("tl_export", os.path.join(tmp, "tests", "test_tape_live.py"))
        tl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tl)
        rc, root, fake, log, _left = tl.cli_live_fake("eq_psql")
        if rc != 0:
            print("the flag-off run at %s failed: rc=%s\n%s" % (full, rc, log[-800:]))
            return 1
        dd = os.path.join(root, tl.DAY)
        files = file_digests(dd, tl.TIMING_FILES)
        with open(os.path.join(dd, "heartbeat.json"), encoding="utf-8") as fh:
            hb = sorted(json.load(fh))
        with open(os.path.join(dd, "state.json"), encoding="utf-8") as fh:
            st = sorted(json.load(fh))
        with open(os.path.join(dd, "live_metrics.csv"), encoding="utf-8") as fh:
            header = fh.readline().rstrip("\n").split(",")
        doc = {"commit": full, "day": tl.DAY, "test_sha": tl.TEST_SHA, "form": FORM, "files": dict(sorted(files.items())),
               "heartbeat_keys": hb, "state_keys": st, "metrics_header": header}
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print("wrote %s: commit %s, form %d, %d files, %d heartbeat keys, %d state keys, %d metric columns" % (
            a.out, full, FORM, len(files), len(hb), len(st), len(header)))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
