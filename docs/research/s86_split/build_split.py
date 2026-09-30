"""S86 ADR-028 phase 2: build the split, with TWO gates and rerun safety.

  conservation   - every content line of the old CLAUDE.md has exactly one home
  pointer-target - every location core's prose NAMES actually contains what it claims

Attempt 1 passed conservation and was still wrong: it moved Rules 18-23 to
CLAUDE_history.md while core's disambiguator said python-writers.md. Gate 2
exists for that, and is proved able to fire by a negative control.

RERUN SAFETY (both learned the hard way):
  * The source is ALWAYS the HEAD blob, never the working tree. Reading the tree
    would make a second run build a split OF THE SPLIT.
  * Nothing is written until the working tree is proved byte-identical to HEAD,
    because the history append is not idempotent and conservation cannot see a
    duplicated block - it only checks presence.

  python3 build_split.py --negative-control   # must FAIL gate 2
  python3 build_split.py                      # must PASS both gates
"""
import re, json, sys, shutil, pathlib, subprocess
from collections import Counter

REPO = pathlib.Path("/home/ssm-user/meridian-cc")
PERSIST = pathlib.Path("/home/ssm-user/s86_test/s86_split")
NEG = "--negative-control" in sys.argv
TRACKED = ["CLAUDE.md", "docs/registers/CLAUDE_history.md"]


def git(*args, binary=False):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)
    assert r.returncode == 0, f"git {' '.join(args)} failed: {r.stderr.decode()[:300]}"
    return r.stdout if binary else r.stdout.decode("utf-8")


SRC_COMMIT = "6bba0ce"          # the PRE-SPLIT commit. Never HEAD.


def src_blob(path):
    """The authoritative source: the pre-split commit, pinned literally.

    This was `HEAD:` until S86. That was correct only while HEAD still pointed
    at the pre-split commit; once the split was committed, HEAD:CLAUDE.md became
    the split CORE, so a re-run would have built a split OF THE SPLIT - the
    exact failure HEAD-sourcing was introduced to prevent. The pre-emit guard
    could not catch it either, because after the commit the tree matches HEAD
    and the guard passes.
    """
    return git("show", f"{SRC_COMMIT}:{path}").replace("﻿", "")


def assert_tree_pristine():
    """Two separate preconditions, deliberately not conflated.

    SOURCE is pinned to SRC_COMMIT's blobs and is independent of HEAD.
    TREE must still match HEAD before any write, because the history emit
    replaces the file wholesale from the pinned seed and a half-built tree
    would be overwritten without record.
    """
    head = git("rev-parse", "--short", "HEAD").strip()
    dirty = []
    for p in TRACKED:
        r = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "HEAD", "--", p])
        if r.returncode != 0:
            dirty.append(p)
    if dirty:
        raise SystemExit(
            f"ABORT - reset first. These differ from HEAD ({head}): {dirty}\n"
            "  git -C ~/meridian-cc checkout -- " + " ".join(TRACKED) + "\n"
            "  git -C ~/meridian-cc clean -nd .claude/rules .claude/skills   # inspect\n"
            "  git -C ~/meridian-cc clean -fd .claude/rules .claude/skills   # then remove")
    # prove the pinned source blobs are readable and are NOT HEAD's, when they differ
    for p in TRACKED:
        git("cat-file", "-e", f"{SRC_COMMIT}:{p}")
    print(f"pre-emit guard: source pinned at {SRC_COMMIT}; "
          f"tree byte-identical to HEAD ({head})")


# ------------------------------------------------------------------ paths ---
PATHS = {
 "python-writers.md": ['"**/*.py"', '"patch_*.py"', '"scripts/**/*.py"'],
 "sql-views.md": ['"sql/**/*.sql"', '"**/*.sql"'],
 "registers.md": ['"docs/registers/**/*.md"', '"docs/decisions/**/*.md"', '"docs/**/*.json"'],
 "schedulers.md": ['"**/*.bat"', '"**/*.ps1"', '"**/crontab*"', '"deploy/systemd/**"',
                   '"docs/registers/aws_crontab*.txt"'],
 "data-access.md": ['"**/*.py"', '"docs/registers/MERDIAN_Data_Inventory.md"'],
 "research.md": ['"docs/research/**/*.md"', '"experiment_*.py"',
                 '"docs/registers/MERDIAN_Experiment_Compendium*.md"'],
 "pine.md": ['"**/*.pine"', '"generate_pine_overlay*.py"'],
 "ops-shell.md": ['"**/*.sh"', '"bin/**"'],
}
TITLES = {
 "python-writers.md": "Python writers and patch scripts",
 "sql-views.md": "SQL and derived views",
 "registers.md": "Registers, documents and repository layout",
 "schedulers.md": "Schedulers, crontabs and services",
 "data-access.md": "Data access: vendors, timezones and source tables",
 "research.md": "Research, cohorts and calibration",
 "pine.md": "Pine v6 overlays",
 "ops-shell.md": "Shell and remote-host operations",
}
SK = {
 "doc-close": ("Run MERDIAN's end-of-session documentation close: update CURRENT.md, "
   "session_log.md, tech_debt.md, merdian_reference.json, the Enhancement Register and "
   "the Decision Index, then commit with the MERDIAN: [OPS] prefix. Use when the session "
   "is ending or the user asks to close out, file TDs, or update the registers.",
   "Session-end documentation close"),
 "merdian-runbooks": ("Find and follow the MERDIAN runbook for a recurring operation - "
   "token rotation, runner restart, backfill, hash mismatch, DhanError 401, calendar rows, "
   "emergency stop, disk-full lockout. Use when the user asks how to perform an "
   "operational procedure, or when a runner, token or feed needs recovery.",
   "MERDIAN runbooks"),
}

# --------------------------------------------------------------- ownership ---
def build_owners(L, variant):
    N = len(L)
    OWNER = {}
    def own(rng, dest):
        for i in rng:
            assert i not in OWNER, f"line {i} double-owned: {OWNER[i]} vs {dest}"
            OWNER[i] = dest

    own(range(1, 28), "core")
    own([28, 29, 30, 31, 44, 45, 46, 47, 48], "core")
    own(range(32, 44), "skill:merdian-runbooks")
    own(range(49, 67), "core")
    own(range(67, 110), "core")          # Rules 0-19, never cut (ruling d)
    own(range(110, 141), "core")
    own([141, 142, 143, 144, 171, 172, 173], "core")
    own(range(174, 226), "rule:registers.md")   # project file layout (plan gap)
    own(range(226, 241), "core")
    own([400, 401, 402, 435, 436], "core")
    own(range(403, 435), "rule:research.md")

    # --- the corrected extraction. variant "attempt1" omits it on purpose. ---
    if variant == "corrected":
        own(range(482, 500), "rule:python-writers.md")   # Rule 18 (B6) + snippet VERBATIM
        own(range(501, 507), "rule:python-writers.md")   # Rule 19 (B7) + grep fence
        own(range(519, 544), "rule:python-writers.md")   # Rule 20 (B8) + era table + helper
        own(range(582, 591), "core")                     # Rule 21 - session-invariant
        own([612], "core")                               # Rule 22 - session-invariant
        own([632], "rule:registers.md")                  # Rule 23
        own([791], "rule:pine.md")                       # R-i PDH/PDL idiom
        own([669], "rule:ops-shell.md")                  # #15 heredoc
        own([944], "rule:ops-shell.md")                  # #82 nano paste

    own([i for i in range(437, 1012) if i not in OWNER], "history")
    own([i for i in range(1052, N + 1) if i not in OWNER], "history")

    AP = {145:"core",146:"core",147:"core",148:"core",152:"core",155:"core",
          156:"core",157:"core",158:"core",
          149:"rule:python-writers.md",162:"rule:python-writers.md",
          163:"rule:python-writers.md",169:"rule:python-writers.md",
          150:"rule:registers.md",
          151:"rule:schedulers.md",167:"rule:schedulers.md",
          168:"rule:schedulers.md",170:"rule:schedulers.md",
          153:"rule:data-access.md",159:"rule:data-access.md",
          160:"rule:data-access.md",161:"rule:data-access.md",
          164:"rule:data-access.md",166:"rule:data-access.md",
          154:"rule:research.md",165:"rule:research.md"}
    assert set(AP) == set(range(145, 171))
    for i, d in AP.items(): own([i], d)

    drops = []
    for i in list(range(241, 400)) + list(range(1012, 1052)):
        s = L[i - 1]
        if re.match(r"^- ", s):
            d, ids, f, q = dispose(s)
            own([i], "drop" if d == "drop" else d)
            if d == "drop": drops.append((i, f, q, s))
        else:
            own([i], "core")

    missing = [i for i in range(1, N + 1) if i not in OWNER]
    assert not missing, f"unowned lines: {missing[:20]}"
    return OWNER, drops

# ---------------------------------------------- settled-bullet classifier ---
IDRE = re.compile(r"\b(TD-[A-Za-z0-9-]+|ADR-\d{3}|ENH-\d+|§D\.\d+(?:\.\d+)?|C-\d+|CASE-[\d-]+)\b")
CORE_PAT = re.compile(r"cannot fail|is not a check|not a check\b|measured, never|never by name|"
 r"COMPUTED, and computed|never recalled|expected value handed|a check that|"
 r"proven with a control|assert|verification|UNMEASURABLE BY THIS METHOD|real empty list|"
 r"does not fix the mechanism|has a half-life|a count taken at one moment|ONE execution|"
 r"Derive a gate's threshold|line citation is stable|carry their owning document|"
 r"Absence is not a verdict", re.I)
SQL_PAT = re.compile(r"\bview\b|GRANT|COMMENT ON|PostgREST|\bRLS\b|\banon\b|sql/|EXPLAIN|"
 r"MATERIALIZED|statement_timeout|CTE|latest.run|DEFAULT PRIVILEGES|57014|max.pain|gex_|argmax", re.I)
PY_PAT = re.compile(r"ast\.parse|py_compile|patch script|read_bytes|write_bytes|str_replace|"
 r"writer|detector|\.py\b|ExecutionLog|expected_writes|recency floor|fail-open|fail-soft|helper", re.I)
REG_PAT = re.compile(r"tech_debt|register|Doc Protocol|session_log|CURRENT\.md|footer|citation|"
 r"Decision Index|line citation", re.I)
SCHED_PAT = re.compile(r"cron|crontab|systemd|Task Scheduler|timer|SHELL=|flock|KillSignal|"
 r"logrotate|pythonw|battery", re.I)
RESEARCH_PAT = re.compile(r"cohort|holdout|WR\b|win rate|N≥|N>=|edge|backtest|Exp \d|experiment|"
 r"binomial|ADR-009|calibration|DTE|retest|primitive", re.I)
DATA_PAT = re.compile(r"bar_ts|IST|UTC|timezone|vendor|chain|expiry|ltp|hist_|ingest|"
 r"trading_calendar|CAS|close_1530", re.I)
RECORD_PAT = re.compile(r"\b(ACCEPTED|SHIPPED|CLOSED|RESOLVED|PROPOSED|SUPERSEDED|REJECTED|"
 r"ANSWERED|IMPLEMENTED|REFUTED|VALIDATED|RETIRED|DONE|BUILT \+ DEPLOYED|CONFIRMED|"
 r"AMENDMENT [A-Z]|Amendment [A-Z]|DISABLED|REVERTED|REFRAMED|FILED)\b")

def norm(s): return " ".join(s.replace("`", "").replace("*", "").split()).lower()
CORPUS, NCORPUS = {}, {}
for p in (REPO / "docs").rglob("*"):
    if p.suffix in (".md", ".json") and p.is_file() and "CLAUDE_history" not in p.name:
        try:
            t = p.read_text(errors="replace")
            CORPUS[str(p.relative_to(REPO))] = t
            NCORPUS[str(p.relative_to(REPO))] = norm(t)
        except Exception: pass

def find_quote(b, ids):
    nb = norm(b); W = 60
    wins = [nb[i:i + W] for i in range(0, max(1, len(nb) - W + 1), 10)]
    cands = [f for f in NCORPUS if any(i in CORPUS[f] for i in ids)] or list(NCORPUS)
    for f in cands:
        for w in wins:
            if w in NCORPUS[f]:
                j = NCORPUS[f].find(w)
                return f, NCORPUS[f][max(0, j - 40):j + W + 60]
    return None, None

def dispose(b):
    ids = IDRE.findall(b)
    if CORE_PAT.search(b): return "core", ids, None, None
    if RECORD_PAT.search(b) and ids:
        f, q = find_quote(b, ids)
        return ("drop", ids, f, q) if f else ("history", ids, None, None)
    for pat, fn in ((SQL_PAT, "sql-views.md"), (SCHED_PAT, "schedulers.md"),
                    (RESEARCH_PAT, "research.md"), (DATA_PAT, "data-access.md"),
                    (PY_PAT, "python-writers.md"), (REG_PAT, "registers.md")):
        if pat.search(b): return f"rule:{fn}", ids, None, None
    f, q = find_quote(b, ids)
    return ("drop", ids, f, q) if f else ("history", ids, None, None)

# ------------------------------------------------------------------ emit ----
def disambiguator(variant):
    if variant == "attempt1":
        loc = ("> EOL handling and the module-import grep — lives in "
               "`.claude/rules/python-writers.md`,\n"
               "> together with Rules 20–23; renumbering and citation re-pointing are deferred.")
    else:
        loc = ("> EOL handling and the module-import grep — lives in "
               "`.claude/rules/python-writers.md`,\n"
               "> with **Rule 20** beside them. **Rules 21 and 22** are session-invariant and stay\n"
               "> in this file; **Rule 23** is in `.claude/rules/registers.md`. Renumbering and\n"
               "> citation re-pointing are deferred to phase 3.")
    return ["",
      "> **Two rules are numbered 18 and 19.** The hard rules above are the `trading_calendar`",
      "> trust-anchor (18) and the `.env`-tracing ban (19). A second, older pair — patch-script",
      loc, ""]

POINTERS = ["", "---", "", "## Where the rest of this file went", "",
 "This file was split at Session 86 (ADR-028). Nothing was rewritten; content was relocated.",
 "",
 "- **Path-scoped rules** — `.claude/rules/*.md`. Each declares `paths:` frontmatter and loads",
 "  only when a matching file is read: `python-writers.md`, `sql-views.md`, `registers.md`,",
 "  `schedulers.md`, `data-access.md`, `research.md`, `pine.md`, `ops-shell.md`.",
 "- **Skills** — `.claude/skills/doc-close/` and `.claude/skills/merdian-runbooks/`.",
 "",
 "**Session history is not loaded.** The 23 `Session NN engineering discoveries` blocks and all",
 "version footers live in `docs/registers/CLAUDE_history.md`. Open it when you need one of",
 "these, and cite by session number, never by line:",
 "",
 "| If you need… | Session block |", "|---|---|",
 "| patch-script encoding / EOL / BOM history | S11 ext, S14 |",
 "| timezone and bar-era handling | S11, S15, S22 |",
 "| Supabase / PostgREST limits and schema drift | S28, S29, S35 |",
 "| cohort, holdout and gate-transfer reasoning | S26, S31-B (carries S30), S33 |",
 "| chain-data tier transition and held-strike PnL | S33, S34, S35 |",
 "| Pine v6 ergonomics | S31-B, S41 |",
 "| read-path scoping, recency floors, CAS timing | S69, S70 |",
 "| fail-open corollary and cross-tier identity | S71, S72 |",
 "",
 "*CLAUDE.md v1.57 — 2026-09-30 (Session 86). Split per ADR-028: core + 8 path-scoped rules +",
 "2 skills + history. Verbatim relocation only; no rule text was edited. Predecessor footers:",
 "`docs/registers/CLAUDE_history.md`.*"]

def emit(root, L, OWNER, variant, hist_seed):
    def lines_for(d): return [L[i - 1] for i in sorted(i for i, v in OWNER.items() if v == d)]
    core = []
    for s in lines_for("core"):
        core.append(s)
        if s.startswith("18. **`trading_calendar` is a trust-anchor"):
            core.extend(disambiguator(variant))
    core += POINTERS
    # Authorised tidy (AC1 amendment, S86): collapse runs of 2+ blank lines to one.
    # Whitespace only, core only. Gate 1 excludes blank lines as non-identity-bearing,
    # so conservation is unaffected - which is why this is a tidy and not an edit.
    tidy, prev_blank = [], False
    for s in core:
        blank = not s.strip()
        if blank and prev_blank:
            continue
        tidy.append(s)
        prev_blank = blank
    core = tidy
    (root / "CLAUDE.md").write_text("\n".join(core) + "\n", encoding="utf-8")

    rd = root / ".claude/rules"; rd.mkdir(parents=True, exist_ok=True)
    sizes = {}
    for fn, globs in PATHS.items():
        body = lines_for(f"rule:{fn}")
        out = ["---", "paths:"] + [f"  - {g}" for g in globs] + ["---", "",
               f"# {TITLES[fn]}", "",
               "Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028). Rule text is",
               "unchanged; only its location moved.", ""] + body + [""]
        (rd / fn).write_text("\n".join(out), encoding="utf-8")
        sizes[fn] = (len(out), len((rd / fn).read_bytes()), len(body))

    sd = root / ".claude/skills"
    for name, (desc, title) in SK.items():
        d = sd / name; d.mkdir(parents=True, exist_ok=True)
        body = lines_for(f"skill:{name}")
        out = ["---", f"name: {name}", f"description: {desc}", "---", "", f"# {title}", "",
               "Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028).", ""] + body + [""]
        (d / "SKILL.md").write_text("\n".join(out), encoding="utf-8")

    h = root / "docs/registers/CLAUDE_history.md"
    h.parent.mkdir(parents=True, exist_ok=True)
    add = ["", "", "---", "", "## Relocated from `CLAUDE.md` at Session 86 (ADR-028 split)", "",
      "Appended verbatim. The 23 `Session NN engineering discoveries` blocks, the",
      "`## v1.31 (Session 41)` block, all version footers, and the settled-decision bullets",
      "whose instruction no register was measured to carry. Nothing was edited.",
      ""] + lines_for("history") + [""]
    h.write_text(hist_seed + "\n".join(add), encoding="utf-8")
    return sizes

# ------------------------------------------------------------- gate 1 -------
# ---, |---|---|, ```, blank, and a fence marker carrying a language tag.
# ```python appears in several destinations because several hold python fences;
# a fence delimiter is a delimiter, not content.
STRUCTURAL = re.compile(r"^[-|`:\s]*$|^\s*(?:```|~~~)[A-Za-z0-9_+-]*\s*$")

def check_conservation(root, L, OWNER):
    dests = {"core": root / "CLAUDE.md",
             "history": root / "docs/registers/CLAUDE_history.md",
             **{f"rule:{fn}": root / ".claude/rules" / fn for fn in PATHS},
             **{f"skill:{n}": root / ".claude/skills" / n / "SKILL.md" for n in SK}}
    content = {k: v.read_text(encoding="utf-8-sig") for k, v in dests.items() if v.exists()}
    unacc, multi, skipped = [], [], 0
    for i in range(1, len(L) + 1):
        s, d = L[i - 1], OWNER[i]
        if d == "drop": continue
        if STRUCTURAL.match(s): skipped += 1; continue
        hits = [k for k, t in content.items() if s in t]
        if not hits: unacc.append((i, d, s[:80]))
        elif d not in hits: unacc.append((i, d, "WRONG-HOME: " + s[:66]))
        elif len(hits) > 1: multi.append((i, d, hits, s[:60]))
    return unacc, multi, skipped

# ------------------------------------------------------------- gate 2 -------
def pointer_claims(root):
    core = (root / "CLAUDE.md").read_text(encoding="utf-8-sig")
    R = root / ".claude/rules"
    claims = []
    if "`.claude/rules/python-writers.md`" in core:
        claims.append(("disambiguator -> python-writers.md", R / "python-writers.md",
                       ["**Bug B6 → Rule 18:**", "**Bug B7 → Rule 19:**"]))
    if "**Rule 20** beside them" in core:
        claims.append(("disambiguator -> Rule 20 in python-writers.md",
                       R / "python-writers.md", ["**Bug B8 → Rule 20:**"]))
    if "together with Rules 20–23" in core:
        claims.append(("disambiguator -> Rules 20-23 in python-writers.md",
                       R / "python-writers.md",
                       ["**Bug B8 → Rule 20:**", "**Rule 21 —", "**Rule 22 —", "**Rule 23 —"]))
    if "**Rules 21 and 22** are session-invariant and stay" in core:
        claims.append(("disambiguator -> Rules 21/22 in core", root / "CLAUDE.md",
                       ["**Rule 21 —", "**Rule 22 —"]))
    if "**Rule 23** is in `.claude/rules/registers.md`" in core:
        claims.append(("disambiguator -> Rule 23 in registers.md",
                       R / "registers.md", ["**Rule 23 —"]))
    for fn in PATHS:
        if f"`{fn}`" in core:
            claims.append((f"pointer list -> {fn}", R / fn, ["paths:"]))
    for n in SK:
        if f"`.claude/skills/{n}/`" in core:
            claims.append((f"pointer list -> skill {n}",
                           root / ".claude/skills" / n / "SKILL.md", [f"name: {n}"]))
    if "docs/registers/CLAUDE_history.md" in core:
        H = root / "docs/registers/CLAUDE_history.md"
        rows = re.findall(r"^\| [^|]+ \| ([^|]+) \|$", core, re.M)
        sess = {t.strip() for r in rows for t in r.split(",")} - {"Session block"}
        needed = []
        for s in sorted(sess):
            m = re.match(r"S(\d+)(-B)?", s.strip())
            if m:
                n = m.group(1)
                needed.append("## v1.31 (Session 41" if n == "41" else
                              f"## Session {n}{'-B' if m.group(2) else ''} engineering discoveries")
        claims.append(("topic index -> history blocks", H, sorted(set(needed))))
    return claims

def check_pointers(root):
    fails = []
    for label, path, needles in pointer_claims(root):
        if not path.exists():
            fails.append((label, str(path), "FILE MISSING")); continue
        t = path.read_text(encoding="utf-8-sig")
        for nd in needles:
            if nd not in t:
                fails.append((label, path.name, f"MISSING STRING: {nd!r}"))
    R = root / ".claude/rules"
    for fn in PATHS:
        p = R / fn
        if not p.exists():
            fails.append((f"reverse:{fn}", str(p), "FILE MISSING")); continue
        t = p.read_text(encoding="utf-8-sig")
        m = re.match(r"^---\npaths:\n((?:  - .+\n)+)---\n", t)
        if not m:
            fails.append((f"reverse:{fn}", fn, "paths: frontmatter absent or malformed"))
        elif not m.group(1).strip():
            fails.append((f"reverse:{fn}", fn, "paths: frontmatter EMPTY"))
        after = t.split("unchanged; only its location moved.\n", 1)
        if not (after[1].strip() if len(after) > 1 else ""):
            fails.append((f"reverse:{fn}", fn, "ZERO relocated items"))
    return fails

# ------------------------------------------------------------------ main ----
# SOURCE IS THE PINNED PRE-SPLIT COMMIT, never HEAD and never the working tree.
src_text = src_blob("CLAUDE.md")
hist_seed = src_blob("docs/registers/CLAUDE_history.md")
L = src_text.split("\n")
print(f"source: {SRC_COMMIT}:CLAUDE.md  {len(L)} lines, {len(src_text.encode()):,} B")
# the pin must not silently resolve to the split core
assert "## Session 14 engineering discoveries" in src_text, \
    f"{SRC_COMMIT}:CLAUDE.md does not look pre-split - discovery blocks absent"
assert len(L) == 1174, f"expected 1174 source lines, got {len(L)}"

if NEG:
    stage = pathlib.Path("/tmp/s86_negctl"); shutil.rmtree(stage, ignore_errors=True)
    (stage / "docs/registers").mkdir(parents=True)
    OWNER, drops = build_owners(L, "attempt1")
    emit(stage, L, OWNER, "attempt1", hist_seed)
    unacc, multi, skipped = check_conservation(stage, L, OWNER)
    fails = check_pointers(stage)
    print("=== NEGATIVE CONTROL: attempt-1 ownership, staged in /tmp/s86_negctl from HEAD ===")
    print(f"gate 1 conservation: unaccounted={len(unacc)} multi={len(multi)} "
          f"structural-skipped={skipped}")
    print(f"gate 2 pointer-target FAILURES: {len(fails)}")
    for f in fails: print("   FAIL", f)
    assert fails, "CONTROL DID NOT FIRE - gate 2 cannot detect the known defect; it is not a check"
    print(f"\nCONTROL OK: gate 2 fires ({len(fails)} failures) on the known-bad state.")
    sys.exit(0)

assert_tree_pristine()
OWNER, drops = build_owners(L, "corrected")
print(f"owners assigned for all {len(L)} lines")
print("  " + json.dumps(Counter(OWNER.values()), indent=1))
sizes = emit(REPO, L, OWNER, "corrected", hist_seed)
unacc, multi, skipped = check_conservation(REPO, L, OWNER)
fails = check_pointers(REPO)
core_p = REPO / "CLAUDE.md"
cl, cb = len(core_p.read_text().split("\n")), len(core_p.read_bytes())

print(f"\nGATE 1 conservation: unaccounted={len(unacc)} multi-homed={len(multi)} "
      f"(structural skipped={skipped}, register-duplicate drops={len(drops)})")
for t in unacc[:12]: print("   UNACCOUNTED", t)
for t in multi[:12]: print("   MULTI", t)
print(f"GATE 2 pointer-target: failures={len(fails)}")
for f in fails: print("   FAIL", f)
print(f"\nAC1: core {cl} lines / {cb:,} B (bounds 200 / 40,960) -> "
      f"lines {'PASS' if cl <= 200 else 'FAIL'}, bytes {'PASS' if cb <= 40960 else 'FAIL'}")
for fn, (l, b, n) in sorted(sizes.items(), key=lambda x: -x[1][1]):
    print(f"  {fn:22} {l:>4} lines {b:>7,} B  ({n} relocated)")
hb = (REPO / "docs/registers/CLAUDE_history.md")
print(f"  CLAUDE_history.md   {len(hist_seed.encode()):,} B -> {len(hb.read_bytes()):,} B")
json.dump(dict(owners=dict(Counter(OWNER.values())), unaccounted=unacc, multi=multi,
               pointer_fails=fails, core_lines=cl, core_bytes=cb, sizes=sizes,
               drops=len(drops), structural_skipped=skipped),
          open(PERSIST / "scripts/build_result.json", "w"), indent=1, default=str)
(PERSIST / "scripts/drops.json").write_text(json.dumps(drops, indent=1))
assert not unacc, "GATE 1 FAILED: unaccounted lines"
assert not multi, "GATE 1 FAILED: multi-homed lines"
assert not fails, "GATE 2 FAILED: pointer targets"
print("\nboth gates PASS")
