#!/usr/bin/env python3
"""S101 A1 — transitive purity map for the retail compute surface.

Static (AST) analysis only; nothing in the analysed modules is imported or run.

For every top-level function/class in the analysed files:
  * DIRECT impurity  = references a module-level name whose binding is impure
                       (an impure import, or a global whose initialiser is impure),
                       a forbidden builtin (open/print/input/exec/eval/__import__),
                       a clock read (.now/.today/.utcnow/time.time/...),
                       or an import statement inside the body.
  * CALL CLOSURE     = every top-level function of the same file it references,
                       transitively, plus cross-file edges for imported functions
                       of analysed files (e.g. core.pin_state.derive).
  * PURE             = no direct impurity anywhere in the closure.

Usage:  python3 -I s101_purity_map.py [--root TREE]              table of the TARGETS; exit 0
        python3 -I s101_purity_map.py [--root TREE] --selftest   controls + mutants; exit 1 on any miss
TREE defaults to the repo this script sits in (its parent's parent).
"""
from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path

ROOT = (Path(sys.argv[sys.argv.index("--root") + 1]).resolve() if "--root" in sys.argv
        else Path(__file__).resolve().parent.parent)

FILES = {
    "cgm": "compute_gamma_metrics_local.py",
    "wgh": "write_gex_cycle_history_local.py",
    "pin": "core/pin_state.py",
    "par": "core/parameters.py",
    "cal": "core/trading_calendar_gate.py",
    "mcg": "merdian_compute/gamma.py",   # S101: after the extraction the pure code lives here
    "mcc": "merdian_compute/cycle.py",
}
# module path -> file key, for cross-file edges
MODULE_KEY = {"core.pin_state": "pin", "core.parameters": "par",
              "core.trading_calendar_gate": "cal",
              "merdian_compute.gamma": "mcg", "merdian_compute.cycle": "mcc"}

# Stdlib modules whose names are pure when used (clock attrs are caught separately).
PURE_MODULES = {
    "__future__", "re", "math", "dataclasses", "typing", "datetime", "statistics",
    "collections", "bisect", "functools", "itertools", "operator", "enum", "decimal",
    "fractions", "zoneinfo", "types",
}
FORBIDDEN_BUILTINS = {"open", "print", "input", "exec", "eval", "__import__", "breakpoint"}
CLOCK_ATTRS = {"now", "today", "utcnow", "time", "monotonic", "perf_counter", "sleep",
               "time_ns", "localtime", "gmtime"}

TARGETS = [
    ("cgm", n) for n in [
        "signed_gamma_exposure", "filter_usable_option_rows", "infer_symbol", "infer_spot",
        "infer_expiry_date", "infer_ts", "infer_strike_step", "compute_net_gex",
        "build_strike_exposure_map", "compute_gamma_concentration",
        "_flip_short_gamma_perstrike", "compute_flip_level", "find_atm_strike",
        "compute_straddle_atm", "compute_straddle_slope", "compute_expansion_probability",
        "determine_regime", "determine_gamma_zone", "compute_straddle_velocity",
        "compute_otm_oi_velocity", "compute_otm_oi_snapshot", "compute_max_gamma_strike",
        "compute_pin_risk_score", "compute_gamma_metrics", "build_gss_rows",
        "GammaMetricsResult",
    ]
] + [
    ("wgh", n) for n in ["trading_days_to_expiry", "boost", "conviction_for",
                         "derive_rank_fields", "_norm_frac", "_ist_date"]
] + [("pin", "derive")] + [("mcg", "prepare_gamma_inputs"), ("mcg", "compute_gamma_core")]


class Module:
    def __init__(self, key: str, rel: str, src: str | None = None):
        self.key, self.rel = key, rel
        self.src = src if src is not None else (ROOT / rel).read_text()
        self.tree = ast.parse(self.src)
        self.defs: dict[str, ast.AST] = {}
        self.imports: dict[str, str] = {}      # local name -> "module" or "module.attr"
        self.globals_init: dict[str, ast.AST] = {}
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.defs[node.name] = node
            elif isinstance(node, ast.Import):
                for a in node.names:
                    self.imports[a.asname or a.name.split(".")[0]] = a.name
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    self.imports[a.asname or a.name] = f"{node.module}.{a.name}"
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name) and node.value is not None:
                        self.globals_init[t.id] = node.value
            elif isinstance(node, ast.Try):
                # top-level try/except import blocks
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Import):
                        for a in sub.names:
                            self.imports[a.asname or a.name.split(".")[0]] = a.name
                    elif isinstance(sub, ast.ImportFrom):
                        for a in sub.names:
                            self.imports[a.asname or a.name] = f"{sub.module}.{a.name}"


MODS = {k: Module(k, r) for k, r in FILES.items() if (ROOT / r).exists() or k not in ("mcg", "mcc")}


def resolve(key: str, name: str) -> tuple[str, str]:
    """Where key:name is DEFINED: in the file itself, or -- on a tree after the S101 extraction --
    in the analysed module the file imports it from. Works on 7b91d1a and on later trees."""
    mod = MODS[key]
    if name in mod.defs:
        return key, name
    target = mod.imports.get(name, "")
    for m, k in MODULE_KEY.items():
        if target.startswith(m + ".") and k in MODS and target[len(m) + 1:] in MODS[k].defs:
            return k, target[len(m) + 1:]
    raise KeyError(f"{key}:{name}")


def import_impure(target: str) -> tuple[bool, str | None]:
    """Is an imported binding impure? Returns (impure, cross_file_edge)."""
    root = target.split(".")[0]
    for mod, key in MODULE_KEY.items():
        if target.startswith(mod + ".") and key in MODS:
            attr = target[len(mod) + 1:]
            if attr in MODS[key].defs:
                return False, f"{key}:{attr}"      # judged by closure, not here
            return False, None                       # e.g. exception class / constant
    if root in PURE_MODULES:
        return False, None
    return True, None


def names_in(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def local_bindings(fn: ast.AST) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not fn:
            out.add(n.name)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
    return out


def local_imports(fn: ast.AST) -> dict[str, str]:
    """Names bound by import statements inside a function body -> imported target."""
    out: dict[str, str] = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Import):
            for a in n.names:
                out[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                out[a.asname or a.name] = f"{n.module}.{a.name}"
    return out


_global_memo: dict[tuple[str, str], list[str]] = {}


def global_reasons(mod: Module, name: str, seen: frozenset = frozenset()) -> list[str]:
    """Impurity reasons for a module-level ASSIGNED global (via its initialiser)."""
    k = (mod.key, name)
    if k in _global_memo:
        return _global_memo[k]
    if k in seen:
        return []
    reasons: list[str] = []
    init = mod.globals_init[name]
    for ref in names_in(init):
        if ref in mod.imports:
            imp, _ = import_impure(mod.imports[ref])
            if imp:
                reasons.append(f"global {name} <- {mod.imports[ref]}")
        elif ref in mod.globals_init:
            reasons += global_reasons(mod, ref, seen | {k})
        elif ref in mod.defs:
            # a global initialised by calling a local function: judge that function
            reasons += [f"global {name} <- {ref}()"] if closure(mod.key, ref)[1] else []
    _global_memo[k] = reasons
    return reasons


_direct_memo: dict[tuple[str, str], tuple[list[str], set[str]]] = {}


def direct(key: str, name: str) -> tuple[list[str], set[str]]:
    """(direct impurity reasons, edges as 'key:name')."""
    k = (key, name)
    if k in _direct_memo:
        return _direct_memo[k]
    _direct_memo[k] = ([], set())          # cycle guard
    mod = MODS[key]
    fn = mod.defs[name]
    locs = local_bindings(fn)
    reasons: list[str] = []
    edges: set[str] = set()
    limps = local_imports(fn)
    for lname, target in limps.items():
        imp, edge = import_impure(target)
        if imp:
            reasons.append(f"local import {target}")
        if edge:
            edges.add(edge)
    locs = locs | set(limps)
    for n in ast.walk(fn):
        if isinstance(n, ast.Attribute) and n.attr in CLOCK_ATTRS:
            reasons.append(f"clock .{n.attr} (line {n.lineno})")
        if isinstance(n, ast.Global):
            reasons.append(f"global statement (line {n.lineno})")
    for ref in sorted(names_in(fn) - locs):
        if ref in mod.defs and ref != name:
            edges.add(f"{key}:{ref}")
        elif ref in mod.imports:
            imp, edge = import_impure(mod.imports[ref])
            if imp:
                reasons.append(f"uses {ref} ({mod.imports[ref]})")
            if edge:
                edges.add(edge)
        elif ref in mod.globals_init:
            reasons += global_reasons(mod, ref)
        elif ref in FORBIDDEN_BUILTINS:
            reasons.append(f"builtin {ref}()")
        elif hasattr(builtins, ref) or ref == name:
            pass
        else:
            reasons.append(f"UNRESOLVED name {ref}")
    _direct_memo[k] = (sorted(set(reasons)), edges)
    return _direct_memo[k]


def closure(key: str, name: str) -> tuple[list[str], list[str]]:
    """(sorted closure 'key:name' excluding self, impurity reasons with provenance)."""
    key, name = resolve(key, name)
    seen, stack, reasons = set(), [f"{key}:{name}"], []
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        k, n = cur.split(":")
        r, e = direct(k, n)
        reasons += [f"{n}: {x}" if cur != f"{key}:{name}" else x for x in r]
        stack += sorted(e - seen)
    seen.discard(f"{key}:{name}")
    return sorted(seen), sorted(set(reasons))


def _reset(mods: dict[str, Module]) -> None:
    global MODS
    MODS = mods
    _global_memo.clear()
    _direct_memo.clear()


def _inject(key: str, fname: str, stmt: str) -> dict[str, Module]:
    """Copy of MODS with `stmt` inserted as the first statement of fname, wherever it is defined."""
    key, fname = resolve(key, fname)
    base = Module(key, FILES[key])
    tree = ast.parse(base.src)
    fn = next(n for n in tree.body if getattr(n, "name", None) == fname)
    fn.body.insert(0, ast.parse(stmt).body[0])
    mods = {k: Module(k, r) for k, r in FILES.items() if k in MODS}
    mods[key] = Module(key, FILES[key], src=ast.unparse(tree))
    return mods


def selftest() -> int:
    """Controls on the real source + mutants that must flip a pure function to impure."""
    real = {k: Module(k, r) for k, r in FILES.items() if k in MODS}
    fails = 0

    def verdict(key, name):
        return "PURE" if not closure(key, name)[1] else "IMPURE"

    _reset(real)
    controls = [("cgm", "fetch_option_chain_rows", "IMPURE"), ("cgm", "upsert_gamma_metrics", "IMPURE"),
                ("cgm", "fetch_india_vix", "IMPURE"), ("cgm", "main", "IMPURE"),
                ("cal", "is_trading_day", "IMPURE"), ("par", "get_parameter_num", "IMPURE"),
                ("cgm", "to_float", "PURE"), ("cgm", "determine_regime", "PURE"),
                ("cgm", "compute_flip_level", "PURE"), ("wgh", "boost", "PURE")]
    for key, name, want in controls:
        got = verdict(key, name)
        ok = got == want
        fails += not ok
        print(f"CONTROL {key}:{name:30} want {want:6} got {got:6} {'ok' if ok else 'FAIL'}")

    mutants = [
        ("M1 os.getenv",        "cgm", "compute_flip_level", "_m = os.getenv('X')", "compute_flip_level"),
        ("M2 clock",            "cgm", "compute_flip_level", "_m = datetime.now()", "compute_flip_level"),
        ("M3 SUPABASE global",  "cgm", "compute_flip_level", "_m = SUPABASE", "compute_flip_level"),
        ("M4 local net import", "cgm", "compute_flip_level", "import requests", "compute_flip_level"),
        ("M5 print",            "cgm", "compute_flip_level", "print('x')", "compute_flip_level"),
        ("M6 via callee",       "cgm", "_flip_short_gamma_perstrike", "_m = os.getenv('X')", "compute_flip_level"),
        ("M7 unresolved name",  "cgm", "compute_flip_level", "_m = not_defined_anywhere", "compute_flip_level"),
        ("M8 two hops (wgh)",   "wgh", "boost", "_m = SUPABASE", "conviction_for"),
    ]
    for label, key, inj_fn, stmt, judged in mutants:
        _reset(real)
        _reset(_inject(key, inj_fn, stmt))
        got = verdict(key, judged)
        ok = got == "IMPURE"
        fails += not ok
        print(f"MUTANT  {label:22} inject {inj_fn} -> judge {judged:22} got {got:6} {'caught' if ok else 'NOT CAUGHT'}")
    _reset(real)
    print(f"SELFTEST {'PASS' if not fails else 'FAIL'} ({fails} failing)")
    return 1 if fails else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    rows = []
    for key, name in TARGETS:
        if key not in MODS:
            continue                                  # package targets on a tree without the package
        try:
            k2, _ = resolve(key, name)
        except KeyError:
            print(f"MISSING target {key}:{name}")
            return 1
        cl, rs = closure(key, name)
        rows.append((k2, name, cl, rs))
    print(f"{'file':4} {'function':32} {'pure':4}  closure  /  impurity")
    for key, name, cl, rs in rows:
        print(f"{key:4} {name:32} {'YES' if not rs else 'NO':4}  "
              f"[{', '.join(c.split(':')[1] if c.startswith(key + ':') else c for c in cl) or '-'}]")
        for r in rs:
            print(f"{'':42}! {r}")
    pure = [n for k, n, _, rs in rows if not rs]
    impure = [f"{k}:{n}" for k, n, _, rs in rows if rs]
    print(f"\nPURE {len(pure)} / {len(rows)}")
    print("IMPURE: " + (", ".join(impure) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
