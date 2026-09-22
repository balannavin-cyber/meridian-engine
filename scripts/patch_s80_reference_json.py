#!/usr/bin/env python3
"""patch_s80_reference_json.py

S80 doc-close -- merdian_reference.json.

FOUR substitutions, each count==1:
  1. change_log gains an S80 entry at index 0 (newest-first).
  2. "version"              v57 -> v58
  3. "last_updated_session" Session 79 -> Session 80
  4. "last_updated_date"    2026-09-16 -> 2026-09-22

TD-S76-NEW-16 IS THE REASON THIS SCRIPT NAMES ITS TARGETS SO PRECISELY.
This file carries TWO version counters and TWO change_log arrays, and a
previous session bumped the wrong one:

    .version        = "v57"  .change_log        = 21 entries, newest S79   <- LIVE
    ._meta.version  = "v52"  ._meta.change_log  = 29 entries, newest S66   <- FROZEN

`_meta` has not moved since S66 -- thirteen sessions. **This pass bumps the
TOP-LEVEL pair only and leaves `_meta` exactly as found.** That asymmetry is
deliberate, not an oversight: reconciling the two arrays is a separate decision
about which is canonical, and silently bumping `_meta` here would repeat the
defect TD-S76-NEW-16 records. The two counters are distinguishable by
indentation -- `._meta.version` is 4-space indented, `.version` is 2-space --
and the anchors below rely on that.

A SPLICE, NOT A ROUND-TRIP. json.load/json.dump would reformat all 5,423 lines
and bury a four-line change in a whole-file diff. The entry is rendered with
json.dumps and indented to match, and the result is validated by parsing the
PATCHED text -- which is a stronger check than any byte assertion: the file
either is valid JSON with 22 change_log entries or the script aborts.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchors, JSON-parse validation, _PRE_S80_DOCCLOSE backup, dry-run default.
"""
import argparse, json, pathlib, sys

DEFAULT_TARGET = pathlib.Path(__file__).resolve().parent.parent / "merdian_reference.json"
MARKER = '"session": "S80"'

A_VERSION = ('  "version": "v57",', '  "version": "v58",')
A_SESSION = ('  "last_updated_session": "Session 79",',
             '  "last_updated_session": "Session 80",')
A_DATE = ('  "last_updated_date": "2026-09-16",',
          '  "last_updated_date": "2026-09-22",')

CL_ANCHOR = '  "change_log": [\n    {\n      "session": "S79",'

ENTRY = {
    "session": "S80",
    "date": "2026-09-19/22",
    "type": (
        "The parity acceptance criterion, two off-spec layers that made the case for it, "
        "and a disk-full access lockout on the last morning. CODE AND SQL CHANGED: two views "
        "(sql/2026-09-22_s80_v_gex_max_pain.sql = ENH-123, sql/2026-09-22_s80_v_gex_pin_maxpain.sql "
        "= ENH-124), one table (gex_pin_maxpain_history, 11,795 rows), one plpgsql function "
        "(backfill_pin_maxpain_runs), and two production Python scripts patched "
        "(compute_gamma_metrics_local.py single-expiry guard; ingest_option_chain_local.py "
        "capture-depth scaffold at stage 0). One superseded function DROPPED "
        "(backfill_pin_maxpain(text,date)). ADRs_NEW=1 (ADR-025); ADRs_AMENDED=1 (ADR-025 "
        "Amendment A, same session). INFRASTRUCTURE CHANGED: EC2 root volume "
        "vol-09b957d7f294beba0 grown 8 GiB gp2 -> 30 GiB gp3 after a 100% fill, logrotate scope "
        "widened, the kernel risk carried since S71 discharged by the reboot."
    ),
    "summary": (
        "ADR-025 IS THE SESSION'S PRODUCT. D1 parity is achieved when every one of the fourteen "
        "layers carries a disposition, not when all fourteen are built, so stopping early is a "
        "result. D2 BUILT requires all four of: computes and has been read; run-scoped and "
        "EXPLAIN-verified per ADR-021; VISIBLE ON AN OPERATOR SURFACE; ENH entry with DDL "
        "committed under sql/. D3 Hedgewall binds. D4 DECLINED-ON-EVIDENCE completes a layer and "
        "stays distinct from the two BLOCKED classes. D5 an off-spec layer does not count toward "
        "parity. MEASURED DISPOSITION: BUILT = 2 of 14 (L1, L2) -- not the three or five a "
        "register count suggests. Five views compute and none renders, so the board reorders to "
        "rendering ENH-120/121/122, which would be the first operator-surface change since ENH-81 "
        "at S37. ENH-123/ENH-124 are NOT parity layers: max pain appears nowhere in the fourteen "
        "or the build order, and both park as L19 under spec 2.5 -- applied, granted, unrendered, "
        "uncounted. Equivalence gate PASSED and it is a real cross-check: NIFTY 23,300 / SENSEX "
        "74,400 from both v_gex_max_pain and the S40 v_max_pain_by_strike, different base tables, "
        "different pivots, snapshots 20 minutes apart. Freshness floor proven CAN FIRE under "
        "BEGIN/ROLLBACK: stale_floor_min_used 30 -> 20 -> 99999 with is_fresh flipping false -> "
        "true at an unchanged age of 895.6 min. v_gex_pin_maxpain emits a distance and NO verdict "
        "-- no tolerance constant, per TD-S79-NEW-21's measure-then-parameterise ruling. "
        "NEW EMPIRICAL FINDING over 11,795 runs: the pin<->max-pain gap is a stable -0.4 sigma, "
        "medians -0.32 to -0.66 across both symbols, every DTE and every session hour, never "
        "changing sign -- max pain sits systematically BELOW peak gamma. Exact strike coincidence "
        "1.2-5.4% everywhere EXCEPT NIFTY at 0 DTE, 13.9% (164/1,182), while SENSEX at 0 DTE is "
        "NOT elevated (3.4%) -- NIFTY expiry day, not expiry day generically. max_pain_in_pin_band "
        "is non-selective at 20.8-42.1% and does not rank the same cells (TD-S80-NEW-3). Whether "
        "coincidence predicts anything is UNANSWERED by design -- ADR-009 pre-registration "
        "territory, with ENH-97 the standing warning. TD-S79-NEW-12 CLOSED: infer_expiry_date() "
        "raises on multi-expiry input instead of taking min() of a set it assumed was a singleton; "
        "shipped BEFORE the ingest change because it converts silent corruption into a crash. "
        "L9 ingest depth measured on the vendor tier: day-level hist_option_bars_1m holds 21 "
        "expiries; NIFTY W1 67.8% / monthly 18.8% / W2 5.2% / Dec quarterly 3.4% / W3 0.47%; "
        "SENSEX W1 97.25% / W2 2.65%. The SELECTION rule matters more than the count -- "
        "chronological [0:4] yields 92.28% and no curve. Ruling: NIFTY 4 selected (94.45%), "
        "SENSEX 2 (99.90%). The spec's 'full expiry ladder per cycle' is REFUTED: "
        "option_chain_snapshots holds one expiry per cycle across all 2,923 cycles ever written; "
        ":327 returns the ladder and :365 discards it. Shipped as stage 0, depth 1, provably "
        "inert, and VERIFIED live next morning 08:53 IST -- grep 'S80 extra expiries' = 0 paired "
        "with a row-side count that CAN fail (max_exp = 1, 3 runs per symbol). "
        "TD-S79-NEW-1 escalated: the expiry-day sigma overstatement is time-varying (0.982 at "
        "09:00 IST -> 0.203 at 15:00 IST) and HIDES an intraday effect -- the 0-DTE gap looks flat "
        "under day-sigma and more than doubles under correct sigma. "
        "DISK-FULL ACCESS LOCKOUT 2026-09-22: root filesystem hit 100% and removed BOTH documented "
        "access paths at once -- SSM Session Manager (agent is a snap on the failed volume) and EC2 "
        "Instance Connect (must write a key to the host) -- while describe-instance-status reported "
        "running/ok/ok throughout. Onset measured from the database at ~09:28 IST, FOURTEEN MINUTES "
        "before the journald console stamp; cron layer dark ~40 min; feed dark bounded at <=48 min "
        "with the interval 09:28-10:08 named UNOBSERVABLE because the writer that would record it "
        "was down too. index_futures_snapshots lost 09:30-10:05 with no historical equivalent to "
        "backfill from. Recovery: snapshot snap-0e111e3c1d5cd1f93 first, grow online, verify the "
        "EIP is a true Elastic IP before any state change (Dhan and ICICI whitelist it), then "
        "stop/start; cloud-init ran growpart/resize2fs unaided. t3.medium deliberately NOT bundled. "
        "TD-S69-NEW-1 CLOSED by the resize -- and found in a SELF-CONTRADICTORY state, heading "
        "'RESOLVED S71' against a Status row 'OPEN -- P0 into S70', unreconciled since S71, which "
        "caused two readers to reach opposite conclusions on the same day (TD-S80-NEW-19). The "
        "~150 MB/day consumer is still UNIDENTIFIED: Claude Code measures 738 MB not the ~1.0 GB "
        "first recorded (236 MB of that block is pip site-packages, 57 MB pip cache), which is "
        "under a third, leaving ~1.76 GB unattributed -- so the resize is a five-month delay until "
        "it is found (TD-S80-NEW-15)."
    ),
    "docs_updated": (
        "docs/registers/tech_debt.md (TD-S80-NEW-1..13 filed in the main pass, -6 WITHDRAWN before "
        "filing; TD-S79-NEW-1 annotated in place with the S80 sigma measurement; TD-S79-NEW-12 "
        "moved to Resolved with a closure block; then the incident pass added TD-S80-NEW-14..19 "
        "and moved TD-S69-NEW-1 to Resolved -- body relocated VERBATIM, only its heading and "
        "Status rows rewritten). docs/registers/MERDIAN_Enhancement_Register.md (ENH-123/ENH-124 "
        "summary rows + Part 4 detail blocks; scope bound ENH-01..ENH-122 -> ..ENH-124; two stale "
        "TD-S79-NEW-14 EXPLAIN clauses annotated rather than rewritten, per the register's "
        "as-filed convention -- the residual is TD-S80-NEW-14). docs/decisions/"
        "ADR-025-parity-acceptance-criterion.md (Amendment A appended: A1 capture depth shipped as "
        "a module constant against this ADR's own ruling, with the reason and the condition for "
        "moving it; A2 five self-corrections in ADR-024 A9 form; A3 D2 clause 4 registration "
        "status). docs/decisions/MERDIAN_Decision_Index.md (ADR-025 row prepended; reserved-table "
        "next-free marker advanced ADR-025+ -> ADR-026+, so the S74 consumed-ID defect does not "
        "recur; S80 footer; maintenance clause restamped IN PLACE per TD-S73-NEW-11). "
        "docs/registers/MERDIAN_System_Map.md (section S80 -- the two views, the history table and "
        "why it had to exist, the two patched scripts, three new scripts). "
        "docs/registers/MERDIAN_Deployment_Topology.md (section S80 -- FIRST TOPOLOGY SECTION SINCE "
        "S76: the volume resize, the access-path property, the measured timeline, the logrotate "
        "widening closing TD-S73-NEW-1, the kernel risk discharged, and what remains unexplained). "
        "docs/registers/MERDIAN_Assumption_Register.md (section D.37 opened, 10 rows -- 4 CONFIRMED, "
        "4 REFUTED, 1 VALIDATED-as-regime-dependent, 1 NOT ESTABLISHED; four of them correct the "
        "incident document itself; plus the S80 update-log paragraph). docs/session_notes/CURRENT.md "
        "(S80 block; S79 re-emitted VERBATIM as Previous session; S78 MOVED verbatim to "
        "CURRENT_history.md in the same pass, with history growth asserted equal to what CURRENT "
        "lost). docs/registers/CURRENT_history.md (S78 block received). "
        "docs/session_notes/session_log.md (S80 entry prepended, newest-first, single line). "
        "CORRECTION PASSES, recorded because they are part of the record: the inherited claim that "
        "TD-S69-NEW-1 was 'open at P0 since 2026-08-12' propagated into Topology twice and the "
        "Assumption Register once before it was caught, and was corrected in place; and the claim "
        "that Deployment Topology was NOT updated this session -- true of the build, false of the "
        "session -- was corrected in Decision Index, CURRENT.md and session_log.md, having been "
        "caught in the System Map before it landed."
    ),
    "git_state": (
        "Work commits: 85dfad2 (the S80 SQL objects registered under sql/) and b094fa2 (ADR-025 "
        "plus the two patched production scripts and their patch/probe scripts). THE DOC-CLOSE "
        "COMMIT IS NOT YET MADE AT THE TIME THIS ENTRY WAS WRITTEN -- it follows this file, and "
        "its hash is therefore absent here by construction, which is the convention artefact "
        "TD-S69-NEW-7 established: a session's doc-close commit cannot appear inside the docs it "
        "commits. All doc-close edits were applied in ~/meridian-cc, the agent tree, which no "
        "crontab line and no systemd unit references (S73.A) -- NOT in ~/meridian-engine. Two "
        "earlier S80 patch scripts DID run against the production tree before the operator's "
        "instruction to read PK corrected it; that is ADR-025 Amendment A A2 item 5 and "
        "TD-S80-NEW-12. Cross-tier verification is by git hash-object, never byte size, per C-15: "
        "core.autocrlf=true makes every text file differ Local<->EC2 by exactly its line count."
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write; default is dry-run")
    ap.add_argument("--target", default=str(DEFAULT_TARGET))
    args = ap.parse_args()

    target = pathlib.Path(args.target)
    print(f"target: {target}")
    if not target.is_file():
        print("ABORT: target not found.", file=sys.stderr)
        return 1

    raw = target.read_bytes()
    text = raw.decode("utf-8-sig")
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    eol = "\r\n" if crlf > lf_only else "\n"
    print(f"baseline: {text.count(chr(10))} newlines, {len(raw)} bytes")
    print(f"EOL: CRLF={crlf} LF={lf_only} -> {'CRLF' if crlf > lf_only else 'LF'}; BOM={had_bom}")

    if MARKER in text:
        print("IDEMPOTENT: an S80 change_log entry already exists. Nothing to do.")
        return 0

    norm = text.replace("\r\n", "\n")

    before = json.loads(norm)
    n_before = len(before["change_log"])
    meta_v_before = before["_meta"]["version"]
    meta_cl_before = len(before["_meta"]["change_log"])
    print(f"parses as JSON: change_log={n_before} entries, .version={before['version']!r}")
    print(f"  _meta.version={meta_v_before!r}, _meta.change_log={meta_cl_before} entries "
          f"(newest {before['_meta']['change_log'][0].get('session')!r}) -- NOT TOUCHED")

    rendered = json.dumps(ENTRY, ensure_ascii=False, indent=2)
    block = "\n".join("    " + ln for ln in rendered.split("\n"))
    cl_new = '  "change_log": [\n' + block + ",\n    {\n      \"session\": \"S79\","

    subs = [("1. change_log S80 entry", CL_ANCHOR, cl_new),
            ("2. version v57 -> v58", *A_VERSION),
            ("3. last_updated_session", *A_SESSION),
            ("4. last_updated_date", *A_DATE)]

    patched = norm
    for label, old, new in subs:
        c = patched.count(old)
        print(f"[{label}] anchor count == {c} (must be 1)")
        if c != 1:
            print(f"ABORT: anchor not unique for {label}.", file=sys.stderr)
            return 1
        patched = patched.replace(old, new, 1)

    # the real check: the patched text must still be valid JSON
    try:
        after = json.loads(patched)
    except Exception as e:
        print(f"ABORT: patched text is not valid JSON: {e}", file=sys.stderr)
        return 1
    print("patched text parses as JSON")

    checks = [
        ("change_log length", len(after["change_log"]), n_before + 1),
        ("change_log[0].session", after["change_log"][0]["session"], "S80"),
        ("change_log[1].session", after["change_log"][1]["session"], "S79"),
        ("version", after["version"], "v58"),
        ("last_updated_session", after["last_updated_session"], "Session 80"),
        ("last_updated_date", after["last_updated_date"], "2026-09-22"),
        ("_meta.version UNCHANGED", after["_meta"]["version"], meta_v_before),
        ("_meta.change_log UNCHANGED", len(after["_meta"]["change_log"]), meta_cl_before),
    ]
    ok = True
    for label, got, want in checks:
        flag = "OK " if got == want else "FAIL"
        print(f"  [{flag}] {label}: {got!r} (want {want!r})")
        ok = ok and got == want
    if not ok:
        print("ABORT: post-parse assertions failed.", file=sys.stderr)
        return 1

    # every pre-existing entry must survive untouched
    if after["change_log"][1:] != before["change_log"]:
        print("ABORT: a pre-existing change_log entry was modified.", file=sys.stderr)
        return 1
    print("all 21 pre-existing change_log entries byte-identical")

    for k in ("session", "date", "type", "summary", "docs_updated", "git_state"):
        if k not in after["change_log"][0]:
            print(f"ABORT: new entry missing field {k}.", file=sys.stderr)
            return 1
    print("new entry carries the full six-field shape")
    print(f"byte delta (normalised): +{len(patched) - len(norm)}")

    if not args.apply:
        print("\nDRY RUN -- no write. Re-run with --apply.")
        return 0

    backup = target.with_name(target.name + "_PRE_S80_DOCCLOSE")
    backup.write_bytes(raw)
    print(f"backup: {backup}")

    out = patched.replace("\n", eol) if eol != "\n" else patched
    target.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
