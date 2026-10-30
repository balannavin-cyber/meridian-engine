#!/usr/bin/env python3
"""S102_R48 -- run_ingest.sh reports the ingest's exit code on its END line and exits with it.

Runs a COPY of run_ingest.sh in a temp dir with a stub .env (one dummy line; the real .env is never
read, rule 19) and a stub ingest_option_chain_local.py that exits with STUB_RC. For each rc the
wrapper must (a) exit rc and (b) print `END symbol=NIFTY mode=FULL rc=<rc>`.
Mutant M1 = the pre-S102 wrapper (`python3 ...` then `rc=$?` under `set -e`): the rc != 0 cells must
FAIL on (b) -- the END line never prints -- while rc = 0 still passes. Stdlib only, no network.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "run_ingest.sh")
FIXED = b'rc=0\npython3 ingest_option_chain_local.py "$SYMBOL" "$MODE" || rc=$?\n'
OLD = b'python3 ingest_option_chain_local.py "$SYMBOL" "$MODE"\nrc=$?\n'
STUB = "import os, sys\nprint('stub ingest', sys.argv[1:])\nsys.exit(int(os.environ['STUB_RC']))\n"
RCS = (0, 1, 2)


def run(script_bytes, rc):
    d = tempfile.mkdtemp(prefix="s102_r48_")
    try:
        with open(os.path.join(d, "run_ingest.sh"), "wb") as f:
            f.write(script_bytes)
        with open(os.path.join(d, ".env"), "w") as f:
            f.write("S102_R48_STUB=1\n")
        with open(os.path.join(d, "ingest_option_chain_local.py"), "w") as f:
            f.write(STUB)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "STUB_RC": str(rc)}
        p = subprocess.run(["bash", os.path.join(d, "run_ingest.sh"), "NIFTY", "FULL"],
                           capture_output=True, text=True, env=env, timeout=30)
        return p.returncode, p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def cells(script_bytes):
    out = []
    for rc in RCS:
        code, so = run(script_bytes, rc)
        out.append((rc, code == rc, f"END symbol=NIFTY mode=FULL rc={rc}" in so))
    return out


def main():
    src = open(SRC, "rb").read()
    ok = True
    if src.count(FIXED) != 1:
        print("FAIL: the fixed capture line is not in run_ingest.sh exactly once")
        return 1
    for rc, exit_ok, end_ok in cells(src):
        print(f"fixed rc={rc}: exit {'PASS' if exit_ok else 'FAIL'}, END line {'PASS' if end_ok else 'FAIL'}")
        ok &= exit_ok and end_ok
    m1 = src.replace(FIXED, OLD, 1)
    m_ok = True
    for rc, exit_ok, end_ok in cells(m1):
        expect_end = rc == 0
        caught = end_ok == expect_end and exit_ok
        print(f"M1 rc={rc}: exit {'ok' if exit_ok else 'BAD'}, END line {'present' if end_ok else 'absent'}"
              f" -> {'as expected' if caught else 'NOT CAUGHT'}")
        m_ok &= caught
    ok &= m_ok
    print(f"run_ingest rc: {'PASS' if ok else 'FAIL'} (3 cells + mutant M1)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
