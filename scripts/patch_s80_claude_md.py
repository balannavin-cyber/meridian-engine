#!/usr/bin/env python3
"""patch_s80_claude_md.py

S80 doc-close -- CLAUDE.md governance footer, plus a three-site correction.

CLAUDE.md gets two substitutions:
  1. An ADR-025 settled-decisions bullet, appended after ADR-024's (the last
     bullet in the list, written at S79).
  2. A v1.52 version footer, prepended above v1.51.

v1.51 IS THE ONLY VERSION FOOTER IN THE FILE. It is dated 2026-09-07, the S74
close. S75, S76, S77, S78 and S79 added none -- so the file's own version stamp
has been five sessions stale while its bullet list gained content at S79. The
v1.52 footer says so, because a gap that closes silently teaches nothing.

THE CORRECTION, across three files. Three S80 records state that ADR-024 has
"no CLAUDE.md footer". **It has one** -- CLAUDE.md:378, written at S79, naming
ADR-024 and superseding D.33.8. What ADR-024 lacks is the `## Governance
language` SECTION INSIDE THE ADR FILE, which is what Rule 11.3 gates on.

That makes the finding sharper, not softer: S79 wrote the bullet the gate
should have blocked, then recorded in the Decision Index that it had written
none. The gate was BYPASSED, not unmet -- and the remedy is 024's governance
section, not a second bullet.

NOT CORRECTED, DELIBERATELY: Decision Index :146. That sentence sits inside the
"Prior maintenance: Session 79" clause and is S79's own claim, preserved
verbatim. Rewriting it would edit S79's statement rather than record that it
was wrong. The S80 stamp above it carries the correction, per this project's
annotate-don't-rewrite convention.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchors, _PRE_S80_GOV backup per file, dry-run default (--apply).
"""
import argparse, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
CLAUDE = HERE / "CLAUDE.md"
INDEX = HERE / "docs" / "decisions" / "MERDIAN_Decision_Index.md"
CURRENT = HERE / "docs" / "session_notes" / "CURRENT.md"
SESSLOG = HERE / "docs" / "session_notes" / "session_log.md"

MARKER = "Session 80, ADR-025"

# ---- CLAUDE.md 1: the ADR-025 bullet ---------------------------------------

C_OLD_1 = ("Supersedes **§D.33.8**, whose 99.1 % / 99.4 % measurement stands and whose "
           "reading does not.")

C_NEW_1 = C_OLD_1 + "\n" + (
    "- ✅ **Parity is a set of dispositions, not a count of builds — a layer counts as BUILT "
    "only when it RENDERS, and a layer outside the fourteen does not count at all "
    "(Session 80, ADR-025).** **D1** the programme is complete when every one of the fourteen "
    "Hedgewall-parity layers carries a recorded disposition — BUILT · PENDING · "
    "BLOCKED-ON-DECISION · BLOCKED-ON-DATA · DECLINED-ON-EVIDENCE — **not** when all fourteen "
    "are built, which makes stopping early a *result* rather than a failure and is what lets "
    "L3's refusal at S79 count as progress. **D2** BUILT requires all four of: it computes "
    "against the live database and its output has been read; it is run-scoped and "
    "EXPLAIN-verified per **ADR-021**; **it is visible on at least one operator surface**; and "
    "it has an ENH entry with its DDL committed under `sql/`. Each clause is earned from a "
    "specific failure — clause 2 from the unscoped view that crossed the PostgREST 8 s ceiling "
    "at 1.06M rows and silently emptied the Pine overlay for weeks, clause 3 because the spec's "
    "own §3 excludes *\"Marketview iteration cycles\"* from its effort numbers which is exactly "
    "how five computed-but-invisible views accumulated, clause 4 because **TD-S79-NEW-3** "
    "records `sql/` as a superseded rebuild source so a view living only in the database is one "
    "`DROP` from unrecoverable. **Agreement with the reference is NOT required for BUILT** — "
    "that is a separate, optional, per-layer validation. **D5** an off-spec layer files to spec "
    "§2.5 as an extension and **does not count toward parity**, because otherwise the criterion "
    "is unfalsifiable: a layer can always be added and progress reported against it. "
    "**Measured at S80: BUILT = 2 of 14** (L1, L2) — not the three or five a register count "
    "suggests — so the next work is **rendering ENH-120 / ENH-121 / ENH-122**, which would be "
    "the first operator-surface change since ENH-81 at S37. ENH-123 / ENH-124 shipped the same "
    "session and are parked as **L19**: applied, granted, unrendered, uncounted. "
    "**Amendment A** records that capture depth shipped as a module constant against this ADR's "
    "own ruling — a parameter read that fails *open* would raise expiry depth silently on a "
    "cycle whose consumers assume one expiry, so **a constant is the right instrument for a "
    "safety interlock and a parameter for a tuning knob** — and files five self-corrections in "
    "ADR-024 §A9 form."
)

# ---- CLAUDE.md 2: the v1.52 version footer ---------------------------------

C_OLD_2 = "*CLAUDE.md v1.51 — 2026-09-07 (Session 74 close)."

C_NEW_2 = (
    "*CLAUDE.md v1.52 — 2026-09-22 (Session 80 close). **v1.51 was the only version footer in "
    "this file, and it is dated the S74 close — S75, S76, S77, S78 and S79 each added none, so "
    "the file's own version stamp stood five sessions stale while its bullet list gained "
    "content at S79.** Recorded rather than quietly closed. **ADRs_NEW=1 — ADR-025**, the "
    "parity acceptance criterion, drafted **before the next layer was built** as TD-S79-NEW-22 "
    "required; **ADRs_AMENDED=1 — ADR-025 Amendment A**, same session, which records a "
    "deviation against the ADR's own ruling rather than hiding one. One settled-decision bullet "
    "added (above). **The uncomfortable measurement is the point: BUILT = 2 of 14.** Five views "
    "compute and none renders. **Shipped:** ENH-123 `v_gex_max_pain` and ENH-124 "
    "`v_gex_pin_maxpain`, both **off-spec and parked as L19**, plus `gex_pin_maxpain_history` "
    "and `backfill_pin_maxpain_runs()` — the table exists because ADR-021's latest-run scoping "
    "makes the pin band unreadable historically from the view, the caveat §S69 wrote down and "
    "S80 paid. **New empirical finding over 11,795 runs: the pin↔max-pain gap is a stable "
    "−0.4σ**, medians −0.32 to −0.66 across both symbols, every DTE and every session hour, "
    "never changing sign; exact coincidence 1.2–5.4 % everywhere except **NIFTY at 0 DTE, "
    "13.9 %**, with SENSEX at 0 DTE *not* elevated. Whether that predicts anything is "
    "**UNANSWERED by design** — ADR-009 territory, ENH-97 the warning. **TD-S79-NEW-12 CLOSED**: "
    "`infer_expiry_date()` raises instead of taking `min()` of a set it assumed was a singleton, "
    "and shipped **before** the ingest change because it converts silent corruption into a "
    "crash. Ingest capture depth measured on the vendor tier and shipped at **stage 0, depth 1, "
    "provably inert**, then **verified inert the next morning by a paired check** — a grep that "
    "returns 0 whether the guard held or the job never ran is not a check. **The last morning "
    "was an incident:** the root volume hit 100 % and removed **both** documented access paths "
    "at once, because the SSM agent is a snap on the failed volume and Instance Connect must "
    "write a key to it, while `describe-instance-status` read `running / ok / ok` throughout. "
    "Volume grown **8 GiB gp2 → 30 GiB gp3**; the S71 kernel risk discharged by the reboot; "
    "logrotate widened, closing TD-S73-NEW-1. **Onset was measured from the database at ~09:28 "
    "IST, fourteen minutes before the journald stamp** — journald records when journald "
    "noticed, and journald was itself a casualty. **~1.76 GB of the growth is still "
    "unattributed**, so the resize is a five-month delay until it is found (TD-S80-NEW-15), and "
    "**TD-S80-NEW-18 is filed S1**: nothing polls disk headroom, and the condition was visible "
    "for sixteen days and read by nothing. **The lesson worth keeping is why TD-S69-NEW-1 "
    "lapsed** — it was resolved at S71 on a measurement correct for its regime, and **a "
    "resolved item has no watcher**, so when its premise expired on 2026-09-06 nothing fired. "
    "Discipline does not reopen a closed item; only a live check does. **Filed:** "
    "TD-S80-NEW-1..19 (−6 withdrawn before filing). **Closed:** TD-S79-NEW-12, TD-S69-NEW-1, "
    "TD-S73-NEW-1. **Three corrections were applied to this session's own doc-close output** — "
    "an inherited *\"open at P0\"* status, a *\"Topology not updated\"* claim true of the build "
    "and false of the session, and this one about ADR-024's footer. **Assumption Register "
    "§D.37** opened with 10 rows, four of which correct the incident document. "
    "**§7.2's deploy-direction inversion remains UNRATIFIED for a fifth consecutive session**, "
    "and S80 is the session that priced it: two patch scripts ran against `~/meridian-engine`, "
    "the production tree, before the operator's instruction to read PK corrected it. Version "
    "footer history for v1.50 and earlier: `docs/registers/CLAUDE_history.md`.*\n\n"
    + C_OLD_2
)

# ---- the three corrections -------------------------------------------------

I_OLD = ("**This pass wrote a CLAUDE.md governance footer for ADR-025 and deliberately wrote "
         "none for ADR-024**, because composing 024's is **authoring its governing sentence**, "
         "which is the operator decision S79 identified and left open. Writing 025's makes "
         "024's absence **more** visible, not less, which is the correct direction for a gap "
         "that has now survived two closes.")

I_NEW = ("**This pass wrote a CLAUDE.md governance footer for ADR-025. The ADR-024 half of this "
         "footer was wrong and is corrected here.** ADR-024 **does** have a CLAUDE.md "
         "settled-decisions bullet — `CLAUDE.md:378`, written at S79, naming the ADR and "
         "superseding §D.33.8. What it lacks is the **`## Governance language` section inside "
         "the ADR file**, which is what §11.3 actually gates on. So the gate was **bypassed, "
         "not unmet**: S79 wrote the bullet the gate should have blocked and then recorded in "
         "this Index that none had been written — which is why the prior-maintenance clause "
         "below still says so, preserved as S79's own claim rather than rewritten. **The remedy "
         "is not a second bullet; it is 024's governance section plus moving its parent Status "
         "off PROPOSED** — one operator decision, as S79 said. Filed under TD-S80-NEW-19 part (b).")

C_OLD = ("**ADR-024's Rule 11.3 gap — second consecutive close**: no `## Governance language` "
         "section, no CLAUDE.md footer, parent Status still PROPOSED against Amendment A's "
         "ACCEPTED.")

C_NEW = ("**ADR-024's Rule 11.3 gap — second consecutive close**: no `## Governance language` "
         "section **in the ADR file**, and the parent Status still PROPOSED against Amendment "
         "A's ACCEPTED. **Its CLAUDE.md bullet does exist** (`:378`, written S79), so the gate "
         "was **bypassed rather than unmet** — the remedy is 024's governance section, not a "
         "second bullet (TD-S80-NEW-19).")

S_OLD = ("ADR-024's Rule 11.3 gap for a **second consecutive close** — no `## Governance "
         "language` section, no CLAUDE.md footer, parent Status still PROPOSED against "
         "Amendment A's ACCEPTED, and this pass wrote a footer for ADR-025 and deliberately "
         "none for ADR-024, which makes the omission more visible rather than less;")

S_NEW = ("ADR-024's Rule 11.3 gap for a **second consecutive close** — no `## Governance "
         "language` section **in the ADR file**, parent Status still PROPOSED against Amendment "
         "A's ACCEPTED; **its CLAUDE.md settled-decisions bullet does exist** at `:378`, written "
         "S79, so the gate was **bypassed rather than unmet** and the remedy is 024's governance "
         "section rather than a second bullet (TD-S80-NEW-19);")

JOBS = [
    (CLAUDE,  [("1. ADR-025 settled-decisions bullet", C_OLD_1, C_NEW_1),
               ("2. v1.52 version footer", C_OLD_2, C_NEW_2)]),
    (INDEX,   [("3. Decision Index S80 footer", I_OLD, I_NEW)]),
    (CURRENT, [("4. CURRENT.md Carry row", C_OLD, C_NEW)]),
    (SESSLOG, [("5. session_log.md S80 entry", S_OLD, S_NEW)]),
]


def process(path: pathlib.Path, subs, apply: bool) -> int:
    print(f"\n=== {path.name} ===")
    if not path.is_file():
        print(f"ABORT: not found: {path}", file=sys.stderr)
        return 1

    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    eol = "\r\n" if crlf > lf_only else "\n"
    print(f"baseline: {text.count(chr(10))} newlines, {len(raw)} bytes; "
          f"EOL={'CRLF' if crlf > lf_only else 'LF'}; BOM={had_bom}")

    if MARKER in text and path == CLAUDE:
        print("IDEMPOTENT: ADR-025 bullet already present. Skipping.")
        return 0
    if path != CLAUDE and "bypassed rather than unmet" in text:
        print("IDEMPOTENT: correction already present. Skipping.")
        return 0

    norm = text.replace("\r\n", "\n")
    patched = norm
    expected = 0
    for label, old, new in subs:
        n = patched.count(old)
        print(f"[{label}] anchor count == {n} (must be 1)")
        if n != 1:
            print(f"ABORT: anchor not unique for {label}.", file=sys.stderr)
            return 1
        patched = patched.replace(old, new, 1)
        expected += new.count("\n") - old.count("\n")

    got = patched.count("\n") - norm.count("\n")
    print(f"line delta expected {expected}, got {got}")
    if expected != got:
        print("ABORT: line delta mismatch.", file=sys.stderr)
        return 1
    if len(patched) <= len(norm):
        print("ABORT: file did not grow.", file=sys.stderr)
        return 1
    print(f"byte delta (normalised): +{len(patched) - len(norm)}")

    if path == CLAUDE:
        if patched.count("(Session 80, ADR-025)") != 1:
            print("ABORT: ADR-025 bullet not inserted exactly once.", file=sys.stderr)
            return 1
        if patched.count("*CLAUDE.md v1.52") != 1:
            print("ABORT: v1.52 footer not inserted exactly once.", file=sys.stderr)
            return 1
        if patched.count("*CLAUDE.md v1.51") != 1:
            print("ABORT: v1.51 footer disturbed.", file=sys.stderr)
            return 1
        if patched.index("*CLAUDE.md v1.52") > patched.index("*CLAUDE.md v1.51"):
            print("ABORT: v1.52 must precede v1.51 (newest-first).", file=sys.stderr)
            return 1
        # ADR-024's bullet, the anchor, must survive
        if patched.count("Supersedes **§D.33.8**") != 1:
            print("ABORT: ADR-024's bullet disturbed.", file=sys.stderr)
            return 1
        print("bullet + v1.52 present once; v1.51 and ADR-024's bullet intact")
    else:
        if "no CLAUDE.md footer" in patched and path != INDEX:
            print("ABORT: superseded claim survives.", file=sys.stderr)
            return 1
        if path == INDEX:
            # :146 is S79's preserved claim and MUST remain
            c = patched.count("so no CLAUDE.md footer was written")
            print(f"S79 prior-maintenance claim preserved: {c} (must be 1)")
            if c != 1:
                print("ABORT: S79's own claim must not be rewritten.", file=sys.stderr)
                return 1
        print("correction applied")

    if not apply:
        print("DRY RUN -- no write.")
        return 0

    backup = path.with_name(path.name + "_PRE_S80_GOV")
    backup.write_bytes(raw)
    print(f"backup: {backup}")
    out = patched.replace("\n", eol) if eol != "\n" else patched
    path.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write; default is dry-run")
    args = ap.parse_args()
    rc = 0
    for path, subs in JOBS:
        rc = max(rc, process(path, subs, args.apply))
    if rc == 0 and not args.apply:
        print("\nAll four files clean. Re-run with --apply.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
