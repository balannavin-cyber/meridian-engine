#!/usr/bin/env python3
"""Extract the backfill's OWN solver into sens/bs_backfill_copy.py, verbatim.

MR-PIN2 step 3. READ-ONLY on the engine tree; writes exactly one file,
sens/bs_backfill_copy.py.

WHY NOT IMPORT: backfill_hist_greeks.py runs module-level code -- load_dotenv()
(:40-44) and a requests-based get() helper -- so importing it would load .env and
could open a connection. It is therefore parsed as TEXT with ast and never executed.

The design (v2, sha256 a9d0b7c5...ad612e) assumed core/bs_engine.py; the backfill does
not call it (conventions.md). Operator clarification 2026-11-20: the re-solve uses the
backfill's own functions and constants. This script is how they are obtained.

VERIFICATION, two independent checks:
  1. For every segment, ast.get_source_segment() is compared byte for byte against an
     INDEPENDENTLY derived slice -- the source re-encoded to UTF-8, line offsets
     recomputed, and (lineno, col_offset, end_lineno, end_col_offset) applied to the
     bytes. If the two derivations disagree, nothing is written and exit is non-zero.
  2. The WRITTEN file is re-parsed and every Name it loads that is neither bound in the
     file nor a Python builtin is listed. A non-empty list means the copy cannot run on
     its own: the file is still written so it can be read, but the run says FAIL and
     exits non-zero.
"""
import ast
import builtins
import hashlib
import sys
from pathlib import Path

SRC = Path("/home/ssm-user/meridian-engine/backfill_hist_greeks.py")
OUT = Path(__file__).resolve().parent / "bs_backfill_copy.py"

# (kind, name) -- kind 'def' FunctionDef, 'assign' module-level Assign by first target,
# 'import' Import by alias asname, 'try' the Try block that DEFINES a given name.
TARGETS = [
    ("import", "np"),            # import numpy as np                      :37
    ("import", "math"),          # needed by _norm_cdf_np                  (see NOTE)
    ("assign", "R_FLAT"),        # flat rate 0.065                         :47
    ("assign", "SQRT_2PI"),      # used by norm_pdf                        :48
    ("assign", "IV_LO"),         # IV_LO, IV_HI, IV_TOL, IV_MX (one stmt)  :51
    ("def", "_norm_cdf_np"),     # no-scipy fallback, needed by norm_cdf   :67-71
    ("try", "norm_cdf"),         # norm_cdf is DEFINED inside a try/except :74-80
    ("def", "norm_pdf"),         #                                         :83-84
    ("def", "bs_price_vec"),     #                                         :87-101
    ("def", "bs_gamma_vec"),     #                                         :104-111
    ("def", "implied_vol_vec"),  #                                         :114-155
]


def independent_slice(src_text, node):
    """Re-derive the node's text from byte offsets, without ast.get_source_segment."""
    lines = src_text.splitlines(keepends=True)
    byte_lines = [l.encode("utf-8") for l in lines]
    starts, acc = [], 0
    for bl in byte_lines:
        starts.append(acc)
        acc += len(bl)
    blob = b"".join(byte_lines)
    a = starts[node.lineno - 1] + node.col_offset
    b = starts[node.end_lineno - 1] + node.end_col_offset
    return blob[a:b].decode("utf-8")


def _import_binds(node, name):
    return any(a.asname == name or a.name.split(".")[0] == name for a in node.names)


def find(tree, kind, name):
    """Module-level lookup. Returns (node, where) or (None, None)."""
    for node in tree.body:
        if kind == "def" and isinstance(node, ast.FunctionDef) and node.name == name:
            return node, "module"
        if kind == "assign" and isinstance(node, ast.Assign):
            tgts = []
            for t in node.targets:
                if isinstance(t, ast.Name):
                    tgts.append(t.id)
                elif isinstance(t, ast.Tuple):
                    tgts += [e.id for e in t.elts if isinstance(e, ast.Name)]
            if name in tgts:
                return node, "module"
        if kind == "import" and isinstance(node, ast.Import) and _import_binds(node, name):
            return node, "module"
        if kind == "try" and isinstance(node, ast.Try):
            if name in {n.name for n in ast.walk(node)
                        if isinstance(n, ast.FunctionDef)}:
                return node, "module"
    # Not at module level. For an import, say where it actually is: the backfill
    # imports math INSIDE _norm_cdf_np (:69), not at the top of the file. The nested
    # statement is copied verbatim to module level, which is harmless (the function
    # keeps its own copy) and makes the name resolvable for check 2.
    if kind == "import":
        for outer in tree.body:
            if not isinstance(outer, (ast.FunctionDef, ast.Try, ast.ClassDef)):
                continue
            for n in ast.walk(outer):
                if isinstance(n, ast.Import) and _import_binds(n, name):
                    label = getattr(outer, "name", type(outer).__name__)
                    return n, f"nested in {label}"
    return None, None


raw = SRC.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
src = raw.decode("utf-8")
tree = ast.parse(src)

segs, ok_all, notes = [], True, []
print(f"source   : {SRC}")
print(f"sha256   : {sha}")
print(f"bytes    : {len(raw)}")
print()
print("kind|name|lines|chars|where|get_source_segment_vs_independent_slice")
for kind, name in TARGETS:
    node, where = find(tree, kind, name)
    if node is None:
        print(f"{kind}|{name}|-|-|-|NOT FOUND")
        ok_all = False
        continue
    a = ast.get_source_segment(src, node)
    b = independent_slice(src, node)
    same = (a is not None) and (a == b)
    ok_all = ok_all and same
    print(f"{kind}|{name}|{node.lineno}-{node.end_lineno}|{len(a) if a else 0}|"
          f"{where}|{'EQUAL' if same else 'DIFFER'}")
    if where != "module":
        notes.append(f"{kind} {name} was NOT at module level: found {where} "
                     f"at :{node.lineno}; statement copied verbatim as-is.")
    segs.append((kind, name, node.lineno, node.end_lineno, a))

if notes:
    print()
    print("### NOTES")
    for n in notes:
        print("# " + n)

if not ok_all:
    print("\nFAIL: a segment was not found or the two derivations disagree. "
          "Nothing written.")
    sys.exit(2)

# segments in source order, so definitions precede their users
segs.sort(key=lambda s: s[2])

hdr = [
    '"""bs_backfill_copy.py -- the backfill\'s OWN Black-Scholes solver, extracted verbatim.',
    "",
    "GENERATED by sens/extract_bs_copy.py. DO NOT EDIT BY HAND.",
    "",
    f"source : {SRC}",
    f"sha256 : {sha}",
    f"bytes  : {len(raw)}",
    "",
    "Every block below is the exact ast.get_source_segment() text of a node in that file,",
    "verified byte for byte against an independently derived byte-offset slice. Line",
    "ranges in the source:",
]
for kind, name, l0, l1, _ in segs:
    hdr.append(f"  {kind:6s} {name:16s} :{l0}-{l1}")
hdr += [
    "",
    "NOT extracted, and why: _norm_cdf_vec (:61-64) is dead code, referenced by no solve",
    "path; signed_gex_vec (:158-166) is the deep-ITM guard, which runs only on the",
    "aggregate strike map and never on the stored sidecar rows (:306-318).",
    "",
    "core/bs_engine.py is NOT used here: the backfill never calls it (conventions.md).",
    '"""',
    "",
]

body = "\n".join(hdr) + "\n"
for kind, name, l0, l1, text in segs:
    body += f"\n# ---- {kind} {name}  (source :{l0}-{l1}) ----\n{text}\n"

OUT.write_text(body, encoding="utf-8")
print()
print(f"written  : {OUT}")
print(f"out bytes: {len(body.encode('utf-8'))}")
print(f"out sha  : {hashlib.sha256(body.encode('utf-8')).hexdigest()}")


# ---- check 2: does the written copy resolve every name it loads? ----
def bound_names(tree_):
    out = set()
    for n in ast.walk(tree_):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
            a = getattr(n, "args", None)
            if a is not None:
                for arg in (list(getattr(a, "posonlyargs", [])) + list(a.args)
                            + list(a.kwonlyargs)):
                    out.add(arg.arg)
                for v in (a.vararg, a.kwarg):
                    if v is not None:
                        out.add(v.arg)
        elif isinstance(n, ast.Import):
            for al in n.names:
                out.add(al.asname or al.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            for al in n.names:
                out.add(al.asname or al.name)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, ast.Global) or isinstance(n, ast.Nonlocal):
            out.update(n.names)
    return out


written = OUT.read_text(encoding="utf-8")
wtree = ast.parse(written)
defined = bound_names(wtree)
loaded = {n.id for n in ast.walk(wtree)
          if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
unresolved = sorted(loaded - defined - set(dir(builtins)))

print()
print("### check 2 -- free names in the written copy")
print(f"names loaded: {len(loaded)}, bound in file: {len(defined)}")
if unresolved:
    print("unresolved: " + ", ".join(unresolved))
    print("FAIL: the copy loads names it does not bind. File written so it can be "
          "read, but it cannot run standalone.")
    sys.exit(3)
print("unresolved: none")
print("ALL SEGMENTS EQUAL; COPY RESOLVES EVERY NAME IT LOADS")
