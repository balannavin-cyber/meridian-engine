#!/usr/bin/env python3
"""S101 A4 — offline step 24: `import merdian_compute` is pure (retail scope §1.3).

Retail imports this package on its own box with its own credentials; importing it must not
read the environment, import a database / HTTP / dotenv client, or open a socket.

THE CHECK. A child interpreter (`-I`, EMPTY environment) installs three tripwires and then
imports the package:
  * env      -- os.environ is replaced by a mapping that raises on ANY read (get, [], in, iter);
  * import   -- a meta-path finder raises ImportError for supabase, postgrest, gotrue, httpx,
                requests, urllib3, dotenv and core (the engine's own I/O layer);
  * network  -- socket.socket.connect / connect_ex / create_connection / getaddrinfo raise.
It then calls one exported function (merdian_compute.gamma.compute_net_gex on two rows) so a
package that imports cleanly but fails on first use is not a pass. Exit 0 + "PURE" = pass.

WHAT MAKES IT FAIL (Rule 0, proved below, not assumed): each mutant is a copy of the real
package with ONE module-level line added; each must fail AND name its own tripwire:
  M1 os.getenv("SUPABASE_URL")        -> env      M2 from supabase import create_client -> import
  M3 import requests                  -> import   M4 socket.create_connection(...)       -> network
  M5 from dotenv import load_dotenv   -> import   M6 from core.config import *           -> import
The control (the unmodified package) must pass. Pure Python, no fixtures, no golden day:
same class as steps 8-10 and 13-23 for the rule 23 ceiling.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHILD = r'''
import sys
ROOT = sys.argv[1]
BLOCKED = ("supabase", "postgrest", "gotrue", "httpx", "requests", "urllib3", "dotenv", "core")

class _Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError(f"TRIPWIRE import: {name}")
        return None
sys.meta_path.insert(0, _Block())
for m in [m for m in sys.modules if m.split(".")[0] in BLOCKED]:
    del sys.modules[m]

import os
class _Env(dict):
    def _trip(self, *a, **k):
        raise RuntimeError(f"TRIPWIRE env: {a[:1]}")
    __getitem__ = get = __contains__ = __iter__ = keys = items = values = setdefault = _trip
os.environ = _Env()

import socket
def _net(*a, **k):
    raise OSError(f"TRIPWIRE network: {a[:1]}")
socket.socket.connect = socket.socket.connect_ex = _net
socket.create_connection = socket.getaddrinfo = _net

sys.path.insert(0, ROOT)
import merdian_compute
from merdian_compute import gamma, cycle
rows = [{"gamma": 0.001, "oi": 100, "option_type": "CE", "strike": 100.0},
        {"gamma": 0.001, "oi": 40, "option_type": "PE", "strike": 100.0}]
v = gamma.compute_net_gex(rows, 100.0)
assert abs(v - 0.001 * 60 * 100.0 ** 2 / 1e7) < 1e-15, v
assert cycle.boost(1.0) == min(cycle.BOOST_COEFF, cycle.BOOST_CAP)
bad = sorted(m for m in sys.modules if m.split(".")[0] in BLOCKED)
assert not bad, bad
print("PURE", sorted(m for m in sys.modules if m.startswith("merdian_compute")))
'''

MUTANTS = [
    ("M1 env read", "env", 'import os\n_M = os.getenv("SUPABASE_URL")\n'),
    ("M2 supabase client", "import", "from supabase import create_client\n"),
    ("M3 requests", "import", "import requests\n"),
    ("M4 socket", "network", 'import socket\nsocket.create_connection(("example.invalid", 443), 1)\n'),
    ("M5 dotenv", "import", "from dotenv import load_dotenv\n"),
    ("M6 engine core", "import", "from core.config import *  # noqa\n"),
]


def run(tree: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-I", "-c", CHILD, str(tree)], env={},
                       capture_output=True, text=True, timeout=60)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    fails = 0
    rc, out = run(ROOT)
    ok = rc == 0 and out.startswith("PURE")
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  control: real package imports pure  -> {out.splitlines()[-1][:120]}")

    for label, reason, line in MUTANTS:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            shutil.copytree(ROOT / "merdian_compute", t / "merdian_compute",
                            ignore=shutil.ignore_patterns("__pycache__"))
            g = t / "merdian_compute" / "gamma.py"
            src = g.read_text()
            anchor = "from __future__ import annotations\n"
            if src.count(anchor) != 1:
                print(f"FAIL  {label}: MUTANT NOT APPLIED (anchor count {src.count(anchor)})")
                fails += 1
                continue
            g.write_text(src.replace(anchor, anchor + line))
            rc, out = run(t)
        caught = rc != 0 and f"TRIPWIRE {reason}" in out
        fails += not caught
        tail = next((ln for ln in reversed(out.splitlines()) if "TRIPWIRE" in ln), out.splitlines()[-1] if out else "")
        print(f"{'PASS' if caught else 'FAIL'}  mutant {label:20} must trip {reason:8} -> {tail.strip()[:100]}")

    print(f"IMPORT PURITY {'ALL PASS' if not fails else f'FAIL ({fails})'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
