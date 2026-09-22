#!/usr/bin/env python3
"""
patch_s80_final_sweep.py — S80 doc-close, final sweep. Four files.

1. CLAUDE.md
   (a) anti-pattern bullet: a multi-file patch script gates idempotency per
       file-entry, and prints a COMPUTED summary, never a literal one.
   (b) one clause appended to the v1.52 footer recording (a).
       Deliberately NOT v1.53 — this is the same doc-close, and minting a
       second footer would claim two closes in one session.

2. docs/registers/MERDIAN_Assumption_Register.md
   (a) D.29.5 supersession marker in the S76 `Was:` form — row NOT rewritten.
   (b) D.29.5 added to the S80 cross-ref line, which named D.29.6 and skipped
       it, which is why nothing linked the row to the incident.

3. docs/decisions/CASE-2026-09-22-disk-full-access-lockout.md
   (a) the runbook added to the cross-references
   (b) D.29.5 named alongside §D.37

4. docs/registers/merdian_reference.json
   docs_updated gains CLAUDE.md, the CASE file, the logrotate conf and the
   runbook. It currently names none of the four.

Canon-v3: read_bytes + utf-8-sig, predominant-EOL detect/restore, BOM
preserved, count==1 anchor assertions, line delta computed from the
replacement text, _PRE_S80 backup, dry-run default.

The JSON file is validated by json.loads and by asserting that no key other
than change_log[0].docs_updated moved.

This script is itself the first instance of the rule it adds: every
file-entry below carries its own idempotency gate, and the closing summary is
computed from the per-file results.
"""

import argparse
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path("/home/ssm-user/meridian-cc")

CLAUDE_MD = ROOT / "CLAUDE.md"
ASSUMPTION = ROOT / "docs/registers/MERDIAN_Assumption_Register.md"
CASEFILE = ROOT / "docs/decisions/CASE-2026-09-22-disk-full-access-lockout.md"
REFJSON = ROOT / "docs/registers/merdian_reference.json"

# ─────────────────────────────────────────────────────────────────────────────
# 1. CLAUDE.md
# ─────────────────────────────────────────────────────────────────────────────

CM_MARK = "gate is written per file-entry and omitted for some of them"

CM1_OLD = (
    "- ❌ Appending to a Windows batch file with `Add-Content` when there is an "
    "`exit /b` line — the appended line runs after `exit /b` and never executes. "
    "Always use string replacement to insert before the exit line. "
    "(Session 13 bat file patch.)"
)

CM1_NEW = CM1_OLD + (
    "\n- ❌ Writing a multi-file patch script whose idempotency gate is written per "
    "file-entry and omitted for some of them. The ungated entries fall through to the "
    "anchor check, which cannot find text its own successful edit removed — so a "
    "re-run reports **ABORT on a document that is correct**, and that abort is "
    "indistinguishable from a real one. Session 80: `patch_s80_claude_md.py` gated "
    "CLAUDE.md, CURRENT.md and session_log.md but not the Decision Index; "
    "`patch_s80_correct_td_s69_new_1_status.py` gated the Deployment Topology but not "
    "the Assumption Register. **Both documents were correct**, and the verification "
    "sweep that found them produced two wrong diagnoses in succession before the files "
    "themselves were read — first that `anchor count == 0` was a pass, then that it "
    "proved the edit never landed. Only the content settles it. **Every file-entry gets "
    "its own gate, and the script's closing summary is computed from the per-file "
    "results — never a literal.** Same session, same class: "
    "`patch_s80_correct_topology_not_updated.py` printed *\"All three files clean. "
    "Re-run with --apply.\"* immediately after all three files printed *Skipping*, "
    "because that line was a constant and not a computation. A summary that cannot "
    "report failure is the CAN FIRE / CANNOT FIRE rule applied to a patch script's own "
    "stdout. (Session 80, doc-close verification sweep.)"
)

CM2_OLD = (
    "two patch scripts ran against `~/meridian-engine`, the production tree, before the "
    "operator's instruction to read PK corrected it. Version footer history"
)

CM2_NEW = (
    "two patch scripts ran against `~/meridian-engine`, the production tree, before the "
    "operator's instruction to read PK corrected it. **One anti-pattern bullet was added "
    "above after this footer was first written** — a multi-file patch script gates "
    "idempotency per file-entry and computes its closing summary rather than printing a "
    "literal. It is recorded as a canon-v3 rule gap rather than a TD because the rule, "
    "not the artefact, is what was missing, and both scripts that exposed it have already "
    "run and will not run again. **A second correction landed in the same sweep:** "
    "`§D.29.5` of the Assumption Register still read REFUTED against *\"the fix is to grow "
    "the volume\"* on the morning the volume was grown, and the S80 cross-ref line named "
    "D.29.6 while skipping it. Version footer history"
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Assumption Register
# ─────────────────────────────────────────────────────────────────────────────

AR_MARK = "SUPERSEDED IN PART 2026-09-22 (S80)"

AR1_OLD = (
    "Growth measured ~17 MB/day ≈ 100 days headroom, so the filed urgency was also "
    "wrong. | Resolved by measurement: **78% → 66%** with no resize, no DB retention "
    "decision, ADR-015's research asset untouched. The durable fix was a logrotate rule "
    "that had never existed. |"
)

AR1_NEW = (
    "Growth measured ~17 MB/day ≈ 100 days headroom, so the filed urgency was also "
    "wrong. | Resolved by measurement: **78% → 66%** with no resize, no DB retention "
    "decision, ADR-015's research asset untouched. The durable fix was a logrotate rule "
    "that had never existed. **SUPERSEDED IN PART 2026-09-22 (S80).** *Was:* one REFUTED "
    "verdict over an assumption carrying two clauses. **The occupancy clause stands "
    "refuted permanently** — `market_ticks` and `gex_strike_snapshots` are Supabase "
    "tables and never occupied an EC2 root volume, and no measurement can change that. "
    "**The fix clause is no longer refuted:** the volume was grown **8 GiB gp2 → 30 "
    "GiB gp3** in the disk-full access lockout, so this row read as a standing refutation "
    "of the thing that was actually done. **And the ~17 MB/day ≈ 100 days figure is "
    "the measurement whose expiry the incident turned on** — correct for its regime, "
    "invalidated by a consumer installed 2026-09-06, with nothing watching because the "
    "item it closed had no watcher. Row deliberately not rewritten, per the S76 "
    "superseded-marker convention. See **§D.37**, Deployment Topology **§S80**, "
    "`CASE-2026-09-22-disk-full-access-lockout.md`, `runbook_recover_disk_full_lockout.md`, "
    "TD-S80-NEW-15. |"
)

AR2_OLD = (
    "· D.29.6, D.30.1, D.30.4/.5, D.31.1/.8, D.32.1/.2, D.33.8, D.34, "
    "D.35.20/.24/.25/.26 ·"
)

AR2_NEW = (
    "· **D.29.5** (superseded in part by this session — its fix clause, not its "
    "occupancy clause; see the row), D.29.6, D.30.1, D.30.4/.5, D.31.1/.8, D.32.1/.2, "
    "D.33.8, D.34, D.35.20/.24/.25/.26 ·"
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. CASE file
# ─────────────────────────────────────────────────────────────────────────────

CASE_MARK = "runbook_recover_disk_full_lockout.md"

CS1_OLD = "Assumption Register **§D.37** (10 rows)"
CS1_NEW = (
    "Assumption Register **§D.37** (10 rows) and **§D.29.5** (the S69-era "
    "assumption whose fix clause this incident un-refuted)"
)

CS2_OLD = "`docs/registers/logrotate_meridian.conf` (the config, now in the repo)"
CS2_NEW = (
    "`docs/registers/logrotate_meridian.conf` (the config, now in the repo) · "
    "`docs/runbooks/runbook_recover_disk_full_lockout.md` (§3 as a procedure — "
    "this file is the record of one event, that one is what to do during the next)"
)

# ─────────────────────────────────────────────────────────────────────────────
# 4. merdian_reference.json  (docs_updated only)
# ─────────────────────────────────────────────────────────────────────────────

RJ_MARK = "runbook_recover_disk_full_lockout.md"

RJ_OLD = (
    "was corrected in Decision Index, CURRENT.md and session_log.md, having been caught "
    "in the System Map before it landed."
)

RJ_NEW = (
    "was corrected in Decision Index, CURRENT.md and session_log.md, having been caught "
    "in the System Map before it landed. FINAL SWEEP -- four files this entry did not "
    "name when first written, three of which were already on disk: CLAUDE.md (one "
    "settled-decisions bullet for ADR-025, version footer v1.52 ending five sessions of "
    "no stamp, and one anti-pattern bullet added in the sweep itself); "
    "docs/decisions/CASE-2026-09-22-disk-full-access-lockout.md (the incident record, "
    "with the timeline measured from the database rather than the console and a "
    "four-row table of claims this incident refuted); "
    "docs/registers/logrotate_meridian.conf (the on-box config brought into the repo, "
    "leaving twenty systemd units and three timers still outside it -- TD-S80-NEW-16); "
    "and docs/runbooks/runbook_recover_disk_full_lockout.md (NEW -- the CLAUDE.md "
    "session-end checklist requires a runbook for any operational procedure the operator "
    "had to work out by hand, and nothing in the session had named it). Also in the "
    "sweep: Assumption Register D.29.5 marked SUPERSEDED IN PART, its occupancy clause "
    "standing and its fix clause un-refuted by the resize, row not rewritten per the S76 "
    "convention, and D.29.5 added to the S80 cross-ref line which had named D.29.6 and "
    "skipped it."
)

# ─────────────────────────────────────────────────────────────────────────────

PLAN = [
    (CLAUDE_MD, CM_MARK, [
        ("1a. CLAUDE.md anti-pattern bullet", CM1_OLD, CM1_NEW),
        ("1b. CLAUDE.md v1.52 footer clause", CM2_OLD, CM2_NEW),
    ]),
    (ASSUMPTION, AR_MARK, [
        ("2a. D.29.5 supersession marker", AR1_OLD, AR1_NEW),
        ("2b. D.29.5 into the S80 cross-ref", AR2_OLD, AR2_NEW),
    ]),
    (CASEFILE, CASE_MARK, [
        ("3a. CASE cross-ref: D.29.5", CS1_OLD, CS1_NEW),
        ("3b. CASE cross-ref: the runbook", CS2_OLD, CS2_NEW),
    ]),
    (REFJSON, RJ_MARK, [
        ("4. reference_json docs_updated", RJ_OLD, RJ_NEW),
    ]),
]


def detect_eol(text: str):
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return ("\r\n" if crlf > lf else "\n"), crlf, lf


def process(path: pathlib.Path, marker: str, subs, apply: bool) -> str:
    """Returns one of: 'wrote', 'clean', 'idempotent', 'abort'."""
    print(f"\n=== {path.name} ===")
    if not path.is_file():
        print(f"ABORT: not found: {path}", file=sys.stderr)
        return "abort"

    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    eol, crlf, lf = detect_eol(text)
    print(f"baseline: {text.count(chr(10))} newlines, {len(raw)} bytes; "
          f"EOL: CRLF={crlf} LF={lf} -> {'CRLF' if eol == chr(13)+chr(10) else 'LF'}; BOM={bom}")

    # ── per-file idempotency gate. Every entry has one. That is the rule. ──
    if marker in text:
        print(f"IDEMPOTENT: marker present ({marker[:48]}...). Skipping.")
        return "idempotent"

    norm = text.replace("\r\n", "\n")
    patched = norm
    delta = 0

    for label, old, new in subs:
        n = patched.count(old)
        print(f"[{label}] anchor count == {n} (must be 1)")
        if n != 1:
            print(f"ABORT: anchor not unique for {label}.", file=sys.stderr)
            return "abort"
        patched = patched.replace(old, new, 1)
        delta += new.count("\n") - old.count("\n")

    got = patched.count("\n") - norm.count("\n")
    print(f"line delta expected {delta}, got {got}")
    if got != delta:
        print("ABORT: line delta mismatch.", file=sys.stderr)
        return "abort"

    if marker not in patched:
        print("ABORT: idempotency marker absent from the patched text.", file=sys.stderr)
        return "abort"

    # ── JSON gets a parse gate and a no-collateral-damage assertion ──
    if path.suffix == ".json":
        try:
            before = json.loads(norm)
            after = json.loads(patched)
        except json.JSONDecodeError as exc:
            print(f"ABORT: JSON no longer parses: {exc}", file=sys.stderr)
            return "abort"
        b0 = dict(before["change_log"][0])
        a0 = dict(after["change_log"][0])
        if b0.pop("docs_updated", None) == a0.pop("docs_updated", None):
            print("ABORT: docs_updated did not change.", file=sys.stderr)
            return "abort"
        if b0 != a0:
            print("ABORT: a field other than docs_updated moved in change_log[0].", file=sys.stderr)
            return "abort"
        if before["change_log"][1:] != after["change_log"][1:]:
            print("ABORT: a pre-existing change_log entry was modified.", file=sys.stderr)
            return "abort"
        for k in before:
            if k != "change_log" and before[k] != after[k]:
                print(f"ABORT: top-level key {k!r} moved.", file=sys.stderr)
                return "abort"
        print("JSON parses; only change_log[0].docs_updated moved.")

    if not apply:
        print("DRY RUN: clean. Re-run with --apply to write THIS file.")
        return "clean"

    out = patched.replace("\n", eol) if eol != "\n" else patched
    data = out.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    backup = path.with_suffix(path.suffix + "_PRE_S80_FINAL_SWEEP")
    shutil.copy2(path, backup)
    path.write_bytes(data)
    print(f"backup  {backup}")
    print(f"WROTE   {path}")
    return "wrote"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    results = [(p.name, process(p, m, s, args.apply)) for p, m, s in PLAN]

    # ── computed summary. Not a literal. That is the other half of the rule. ──
    print("\n" + "=" * 62)
    for name, status in results:
        print(f"  {status.upper():<11} {name}")
    tally = {k: sum(1 for _, s in results if s == k)
             for k in ("wrote", "clean", "idempotent", "abort")}
    print(f"  --> wrote {tally['wrote']} · clean {tally['clean']} · "
          f"idempotent {tally['idempotent']} · abort {tally['abort']} "
          f"of {len(results)} files")
    if tally["abort"]:
        print("  RESULT: at least one file aborted. Nothing downstream should proceed.")
        return 1
    if tally["clean"] and not args.apply:
        print(f"  RESULT: {tally['clean']} file(s) ready. Re-run with --apply.")
    elif not tally["clean"] and not tally["wrote"]:
        print("  RESULT: nothing to do; every file already carries its marker.")
    else:
        print("  RESULT: all requested writes completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
