#!/usr/bin/env python3
"""Writes tests/tape_live/off_golden_56bf055.json: what the runner leaves, flag off, at commit 56bf055 (stage 2b guard live-2b-off).

  TAPE_RULE23_OVERRIDE_R1=1 python tests/tape_live/make_off_golden.py [--commit 56bf055] [--out PATH]

The commit is exported with `git -c core.autocrlf=false archive` into a clean temp dir (no working-tree line-ending conversion), the
export's OWN tests/test_tape_live.py is imported, and its fixture run `cli_live_fake("eq_psql")` (cli live, S3 + psql path through
the fake shell, sim clock, code sha pinned to TEST_SHA) is hashed: every non-timing output file, the heartbeat and state.json key
sets and the live_metrics.csv header. The expected value is the OLD tree's output, never the code under test's. Read-only on git,
no database, no network.
"""
import argparse
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
        files = {}
        for rel in tl._files(dd):
            if rel not in tl.TIMING_FILES:
                with open(os.path.join(dd, rel), "rb") as fh:
                    files[rel] = hashlib.sha256(fh.read()).hexdigest()
        with open(os.path.join(dd, "heartbeat.json"), encoding="utf-8") as fh:
            hb = sorted(json.load(fh))
        with open(os.path.join(dd, "state.json"), encoding="utf-8") as fh:
            st = sorted(json.load(fh))
        with open(os.path.join(dd, "live_metrics.csv"), encoding="utf-8") as fh:
            header = fh.readline().rstrip("\n").split(",")
        doc = {"commit": full, "day": tl.DAY, "test_sha": tl.TEST_SHA, "files": dict(sorted(files.items())),
               "heartbeat_keys": hb, "state_keys": st, "metrics_header": header}
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print("wrote %s: commit %s, %d files, %d heartbeat keys, %d state keys, %d metric columns" % (
            a.out, full, len(files), len(hb), len(st), len(header)))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
