"""Assert every cross-reference in the two ADR drafts resolves to a real target.

Companion to check_s6_verbatim.py. Three ADR-026 rulings emptied open items at
S85 and each time left ADR-027 asserting something false, in text that read
perfectly plausibly -- caught by grep, not by care. This makes it mechanical.

CLASSIFICATION (the load-bearing part). Every candidate token is classified by
the qualifier immediately preceding it:

  LOCAL-QUALIFIED  "ADR-026 §8.1"   -> must exist in the NAMED draft
  EXTERNAL         "ADR-023 D1",    -> belongs to another document. Reported,
                   "inventory.md §4"   NEVER resolved locally. Without this,
                   "S84 §D.40.1"       "ADR-023 D1" silently resolves against
                                       ADR-026's own D1 -- the wrong-citation
                                       class this checker exists to catch.
  BARE             "§6", "V9", "G3" -> must exist in THIS draft or its sibling

Usage:
    check_xrefs.py --selftest    seed 4 defects into temp copies, assert caught
    check_xrefs.py               check the real drafts
Exit 0 = clean. Exit 1 = dangling refs (or a selftest miss). Read-only on the
real drafts; --selftest writes only to a tempdir.
"""
import argparse
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

BASE = Path("/home/ssm-user/meridian-cc/docs/research/s85_rag")
REAL = {
    "ADR-026": Path("/home/ssm-user/meridian-cc/docs/decisions/ADR-026-docs-retrieval-index.md"),
    "ADR-027": BASE / "ADR-027-DRAFT-doc-close-drafting-and-verification.md",
    "ADR-028": Path("/home/ssm-user/meridian-cc/docs/decisions/ADR-028-claude-md-split.md"),
}
LOCAL_IDS = {"ADR-026", "ADR-027", "ADR-028"}

# ---- definitions: what each draft DECLARES -----------------------------
DEFS = {
    "section": [re.compile(r"^#{2,4}\s+(\d+(?:\.\d+)?)[.\s]")],
    # D\d+, not D\d: ADR-028 declares D8-D12, and a single-digit pattern
    # matches NEITHER the declaration nor a reference to D10/D11/D12 -- so the
    # collision rule would have reported 0 for labels it could not see. A check
    # that cannot see its subject is not a check.
    "decision": [re.compile(r"\*\*(D\d+)\s*[—-]")],
    "guard": [re.compile(r"\*\*(G\d[a-c]?)\s*[—-]")],
    # A table-row declaration is a row whose FIRST cell is the token:
    # "| **V0** | ...". Matching "**V0**" anywhere in a row is wrong -- ADR-026's
    # Lane A/B tables carry bolded V/G tokens in their Gate column as
    # REFERENCES, and the loose pattern read those as declarations, producing a
    # false V0/V8/V9 collision on the first real run of the collision rule.
    "test": [re.compile(r"^\|\s*\*\*(T\d)\*\*\s*\|")],
    "arm": [re.compile(r"^\|\s*\*\*(S-\d[ab]?)\*\*\s*\|")],
    "vcheck": [re.compile(r"^\|\s*\*\*(V\d)\*\*\s*\|")],
    "crit": [re.compile(r"^#{3,4}\s+(A\d(?:-secondary)?)\s*[—-]")],
    "step": [re.compile(r"^\|\s*\*\*(A-\d{1,2}|B-\d[ab]?)\*\*\s*\|")],
}

# ---- references: what each draft CITES ---------------------------------
TOKEN_RX = [
    ("section", re.compile(r"§\s*(\d+(?:\.\d+)?)\b")),
    ("decision", re.compile(r"\b(D\d+)\b")),
    ("guard", re.compile(r"\b(G[1-8][a-c]?)\b")),
    ("test", re.compile(r"\b(T[1-9])\b")),
    ("arm", re.compile(r"\b(S-\d[ab]?)\b")),
    ("vcheck", re.compile(r"\b(V\d{1,2})\b")),
    ("crit", re.compile(r"\b(A[1-9](?:-secondary)?)\b")),
    ("step", re.compile(r"\b(A-\d{1,2}|B-\d[ab]?)\b")),
]

# A foreign ADR id, or a named/filed document, immediately before the token.
QUAL_LOCAL = re.compile(r"(ADR-0(?:26|27|28))\W{0,3}$")
QUAL_FOREIGN_ADR = re.compile(r"(ADR-0\d\d)\W{0,3}$")
# NOTE: a bare session marker (S84, S85) is deliberately NOT a qualifier here.
# It was, and it produced a FALSE EXTERNAL: "FINDING S85 — G3's ..." classified
# the local G3 as belonging to another document, silently skipping the check --
# a check that does not fire. Session markers only ever precede "§D.N.N" refs,
# which the section regex cannot match anyway (it requires a digit after §).
QUAL_DOC = re.compile(
    r"([\w./-]+\.(?:md|txt)|Deployment Topology|Doc Protocol(?: v\d)?|"
    r"Assumption Register|Decision Index|System Map|Enhancement Register|"
    r"Experiment Compendium)\W{0,4}$")


def declared(raw):
    out = defaultdict(set)
    for line in raw.splitlines():
        for kind, rxs in DEFS.items():
            for rx in rxs:
                for m in rx.finditer(line):
                    out[kind].add(m.group(1))
    return out


def classify(raw, start):
    """Return ('local', 'ADR-026') | ('external', qual) | ('bare', None)."""
    pre = raw[max(0, start - 60):start]
    pre = pre.replace("**", "").replace("`", "")
    m = QUAL_LOCAL.search(pre)
    if m:
        return "local", m.group(1)
    m = QUAL_FOREIGN_ADR.search(pre)
    if m:
        return "external", m.group(1)
    m = QUAL_DOC.search(pre)
    if m:
        return "external", m.group(1)
    return "bare", None


def collisions(decl, names, exempt=("section",)):
    """Tokens DECLARED in MORE THAN ONE document. A bare use is ambiguous.

    `exempt` kinds are skipped -- see the EXEMPTION comment in run_check:
    every document declares sections 1-9 by construction, so applying the rule
    to them would flag every bare section reference.

    D3 meant ADR-026's staleness floor and ADR-027's drafting agent at the same
    time until S85 renumbered ADR-027 to D4-D7. While that held, a bare "D3"
    resolved to whichever draft the reader happened to be in -- the S84
    wrong-citation shape, inside one document pair. S86 added a THIRD document
    and renumbered ADR-028 to D8-D12 for the same reason, which is why this is
    now an n-way test: the old two-name tuple unpack RAISED as soon as a third
    document arrived, and had it been written as a [:2] slice it would instead
    have gone on silently ignoring the new document -- loud beats lenient.
    """
    kinds = {k for n in names for k in decl[n]}
    out = set()
    for kind in kinds:
        if kind in exempt:
            continue
        seen = {}
        for n in names:
            for tok in decl[n].get(kind, set()):
                seen.setdefault(tok, []).append(n)
        for tok, owners in seen.items():
            if len(owners) > 1:
                out.add((kind, tok))
    return out


def run_check(paths, verbose=True):
    docs = {n: p.read_text(encoding="utf-8") for n, p in paths.items()}
    decl = {n: declared(r) for n, r in docs.items()}
    names = list(paths)
    collide = collisions(decl, names)
    collide_toks = {(k, t) for k, t in collide}

    dangling, external, ambiguous = set(), set(), set()
    checked = 0

    for name, raw in docs.items():
        others = [n for n in names if n != name]
        for kind, rx in TOKEN_RX:
            for m in rx.finditer(raw):
                tok = m.group(1)
                mode, qual = classify(raw, m.start())
                checked += 1
                if mode == "external":
                    external.add((name, qual, tok, kind))
                    continue
                if mode == "local":
                    if tok not in decl[qual].get(kind, set()):
                        dangling.add((name, f"{qual} {tok}", kind,
                                      f"not declared in {qual}"))
                    continue
                # --- COLLISION RULE, with one EXEMPTION -------------------
                # kind "section" is EXEMPT. Both drafts declare sections 1-9 by
                # construction, and a bare "§N" means "this document" by
                # convention -- so sections resolve LOCALLY ONLY, never to the
                # sibling. Without the exemption every bare § ref would read as
                # ambiguous and this check would be noise. The exemption is the
                # fix; qualifying the drafts' own § refs to silence it is not.
                if kind == "section":
                    if tok in decl[name].get(kind, set()):
                        continue
                    dangling.add((name, "§" + tok, kind,
                                  f"not a section of {name}"))
                    continue
                # A bare use of a NON-section token declared in BOTH drafts is
                # ambiguous: it resolves to whichever draft the reader is in.
                if (kind, tok) in collide_toks:
                    ambiguous.add((name, tok, kind,
                                   "declared in BOTH drafts; bare use is ambiguous"))
                    continue
                if tok in decl[name].get(kind, set()):
                    continue
                if any(tok in decl[o].get(kind, set()) for o in others):
                    continue
                dangling.add((name, tok, kind, "declared in no checked document"))

    if verbose:
        print("DECLARED TARGETS")
        for n in paths:
            for kind in ("section", "crit", "decision", "guard", "test",
                         "arm", "vcheck", "step"):
                items = sorted(decl[n].get(kind, ()))
                if items:
                    print(f"  {n} {kind:9} ({len(items):2}): {' '.join(items)}")
        print()
        print(f"EXTERNAL REFERENCES ({len(external)}) "
              f"-- reported, never resolved locally; eyeball these")
        for name, qual, tok, kind in sorted(external):
            print(f"  [{name}] {qual} -> {tok:10} ({kind})")
        print()
        print(f"COLLISIONS ({len(collide)}) -- tokens DECLARED in both drafts "
              f"(kind 'section' exempt by construction)")
        if collide:
            for kind, tok in sorted(collide):
                print(f"  {tok:10} ({kind})")
        else:
            print("  none -- every non-section label is declared in exactly "
                  "one draft")
        print()
        print(f"REFERENCES CHECKED: {checked}")
        bad = sorted(dangling) + sorted(ambiguous)
        if bad:
            print(f"\nRESULT: {len(dangling)} DANGLING, "
                  f"{len(ambiguous)} AMBIGUOUS\n")
            for src, tok, kind, why in bad:
                print(f"  [{src}] {tok:16} ({kind}) -- {why}")
        else:
            print("\nRESULT: ALL CROSS-REFERENCES RESOLVE, NO AMBIGUITY")
    return dangling | ambiguous, external, checked


# ---- Rule 0: prove the checker CAN fire -------------------------------
SEEDS = [
    ("dangling section", "\n\nSeeded defect: see ADR-026 §9.9 for detail.\n"),
    ("undeclared vcheck", "\n\nSeeded defect: enforced as V10.\n"),
    ("foreign ADR, colliding token",
     "\n\nSeeded defect: per ADR-023 D1 the floor binds the consumer.\n"),
    ("novel foreign ADR, colliding token",
     "\n\nSeeded defect: per ADR-099 D1 this must not resolve locally.\n"),
]

# Seeded into the ADR-027 copy: a DUPLICATE declaration of a token ADR-026
# already declares, plus a bare use of it. Tests the collision rule directly --
# this is the D3-in-both-drafts shape the S85 renumber removed.
SEED_DUP = ("\n\n**G1 — seeded duplicate declaration.** "
            "A bare use follows: G1 governs nothing here.\n")

# S86: the SAME shape one document further out. ADR-028 declares D8-D12; this
# seeds a duplicate D8 declaration into the ADR-026 copy, which must surface as a
# COLLISION. It is the case the renumber exists to prevent, and it also proves the
# n-way generalisation of collisions() fires -- the old pair-only form could not
# have compared ADR-026 against ADR-028 at all.
SEED_DUP_D8 = ("\n\n**D8 — seeded duplicate declaration.** "
               "A bare use follows: D8 governs nothing here.\n")


def selftest():
    n_seeds = len(SEEDS) + 2  # + the G1 and D8 duplicate-declaration seeds
    print("=" * 66)
    print(f"SELFTEST -- seeding {n_seeds} defects into temp copies "
          "(real drafts untouched)")
    print("=" * 66)
    with tempfile.TemporaryDirectory(prefix="xref_selftest_") as td:
        tmp = {}
        for n, p in REAL.items():
            q = Path(td) / p.name
            shutil.copy2(p, q)
            tmp[n] = q
        target = tmp["ADR-026"]
        with target.open("a", encoding="utf-8") as fh:
            for _, text in SEEDS:
                fh.write(text)
        # the duplicate-declaration seed goes in the OTHER draft
        with tmp["ADR-027"].open("a", encoding="utf-8") as fh:
            fh.write(SEED_DUP)
        # ...and the D8 duplicate into ADR-026, colliding with ADR-028's D8
        with target.open("a", encoding="utf-8") as fh:
            fh.write(SEED_DUP_D8)

        dangling, external, _ = run_check(tmp, verbose=False)
        decl_t = {n: declared(p.read_text(encoding="utf-8"))
                  for n, p in tmp.items()}
        collide_t = collisions(decl_t, list(tmp))

        want = {
            "dangling section":
                any(t == "ADR-026 9.9" for _, t, _, _ in dangling),
            "undeclared vcheck":
                any(t == "V10" for _, t, _, _ in dangling),
            "foreign ADR, colliding token":
                ("ADR-026", "ADR-023", "D1", "decision") in external,
            "novel foreign ADR, colliding token":
                ("ADR-026", "ADR-099", "D1", "decision") in external,
            "duplicate declaration -> COLLISION detected":
                ("guard", "G1") in collide_t,
            "bare use of colliding token -> AMBIGUOUS":
                any(t == "G1" and "BOTH drafts" in why
                    for _, t, _, why in dangling),
            "D8 declared in a THIRD document -> COLLISION":
                ("decision", "D8") in collide_t,
            "bare D8 with the collision live -> AMBIGUOUS":
                any(t == "D8" and "BOTH drafts" in why
                    for _, t, _, why in dangling),
        }
        # The two foreign arms must ALSO not have resolved locally:
        leaked = any(t.endswith("D1") and "ADR-0" in t
                     for _, t, _, _ in dangling)

        for label, ok in want.items():
            print(f"  [{'CAUGHT' if ok else 'MISSED'}] {label}")
        print(f"  [{'OK' if not leaked else 'LEAK'}] "
              f"foreign D1 not silently resolved as local")

        if all(want.values()) and not leaked:
            print(f"\nSELFTEST: PASS -- the checker can fire on all "
                  f"{len(want)} seeded defects\n")
            return 0
        print("\nSELFTEST: FAIL -- checker cannot detect a defect it claims to\n")
        return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    d, _, _ = run_check(REAL)
    sys.exit(1 if d else 0)
