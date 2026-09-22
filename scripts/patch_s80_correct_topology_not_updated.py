#!/usr/bin/env python3
"""patch_s80_correct_topology_not_updated.py

S80 doc-close -- CORRECTION pass across three already-applied files.

WHAT WENT WRONG. Three S80 records assert that Deployment Topology was not
updated this session, because when each was written the session had produced
only database and script work, which moved no boundary. The 2026-09-22
disk-full access lockout then moved the root volume (8 GiB gp2 -> 30 GiB gp3),
the logrotate scope and the boot kernel, and required a manual feed start.
Deployment Topology carries a full section S80. All three claims are now false.

  Decision Index  :144   "**Deployment Topology deliberately NOT updated** ..."
  CURRENT.md      :23    "**Deployment Topology NOT updated** ..."
  session_log.md  :1     "**Deployment Topology deliberately NOT updated** ..."

Each was true of the work in front of it and false of the session. This is the
same shape as TD-S80-NEW-14 -- an edit landing without the register's own
self-description moving with it -- making it the third instance inside a
doc-close that files two entries about exactly that.

A FOURTH SITE WAS CAUGHT BEFORE IT LANDED. The System Map's section S80 made
the same claim and was amended before it was applied.

THE DECISION INDEX TRAP, recorded because count==1 is what protects against it:
line 142 (the S79 footer) carries a nearly identical sentence differing by one
word -- "no host, cron," against S80's "no host, cron line,". The S79 sentence
is CORRECT and must survive. Each anchor here carries its full trailing clause,
and each file asserts what must still be present afterwards, not only what must
be gone.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchors, survivor assertions, _PRE_S80_CORR2 backup per file, dry-run default.
"""
import argparse, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
INDEX = HERE / "docs" / "decisions" / "MERDIAN_Decision_Index.md"
CURRENT = HERE / "docs" / "session_notes" / "CURRENT.md"
SESSLOG = HERE / "docs" / "session_notes" / "session_log.md"

MARKER = "Deployment Topology UPDATED — §S80"

# ---- Decision Index :144 ---------------------------------------------------

I_OLD = ("**Deployment Topology deliberately NOT updated** — no host, cron line, systemd "
         "unit, token path or Local↔AWS boundary moved, and the two patched scripts run "
         "exactly where they already ran.")

I_NEW = ("**Deployment Topology UPDATED — §S80.** The database and script work moved no "
         "host, cron line, systemd unit, token path or Local↔AWS boundary, and the two "
         "patched scripts run exactly where they already ran. **The session moved topology "
         "regardless**: the **2026-09-22 disk-full access lockout** resized the root volume "
         "**8 GiB gp2 → 30 GiB gp3**, widened the logrotate scope, discharged the kernel "
         "risk carried since S71, and left the feed needing a manual start — with **both** "
         "documented access paths, SSM and Instance Connect, failing together because each "
         "requires the volume that failed. **An earlier version of this footer read "
         "\"deliberately NOT updated\"** — true of the work in front of it, false of the "
         "session — and is corrected here rather than left to be read as current.")

# the S79 footer one line above says almost the same thing and is CORRECT
I_SURVIVES = ("**Deployment Topology deliberately NOT updated** — no host, cron, systemd "
              "unit, token path or Local↔AWS boundary moved; three database views are not "
              "a boundary change")

# ---- CURRENT.md :23 --------------------------------------------------------

C_OLD = ("**Deployment Topology NOT updated** — nothing moved host, cron line, systemd "
         "unit, token path or Local↔AWS boundary.")

C_NEW = ("**Deployment Topology UPDATED — §S80.** The build moved no host, cron line, "
         "systemd unit, token path or Local↔AWS boundary; **the session did** — the "
         "**2026-09-22 disk-full access lockout** resized the root volume **8 GiB gp2 → "
         "30 GiB gp3**, widened the logrotate scope, discharged the S71 kernel risk and "
         "left the feed needing a manual start. This line previously read *\"NOT "
         "updated\"*, which was true of the build and false of the session.")

# ---- session_log.md :1 -----------------------------------------------------

S_OLD = ("**Deployment Topology deliberately NOT updated** — no host, cron line, systemd "
         "unit, token path or Local↔AWS boundary moved.")

S_NEW = ("**Deployment Topology UPDATED — §S80**, though the database and script work moved "
         "no host, cron line, systemd unit, token path or Local↔AWS boundary: the "
         "**2026-09-22 disk-full access lockout** resized the root volume **8 GiB gp2 → "
         "30 GiB gp3**, widened the logrotate scope, discharged the kernel risk carried "
         "since S71 and left the feed needing a manual start, with SSM and Instance Connect "
         "failing **together** because each requires the volume that failed. This entry "
         "previously read *\"deliberately NOT updated\"* — true of the build, false of the "
         "session.")

JOBS = [
    (INDEX,   [("Decision Index S80 footer", I_OLD, I_NEW)], [I_SURVIVES]),
    (CURRENT, [("CURRENT.md S80 Ledger", C_OLD, C_NEW)], []),
    (SESSLOG, [("session_log.md S80 entry", S_OLD, S_NEW)], []),
]


def process(path: pathlib.Path, subs, survivors, apply: bool) -> int:
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

    if MARKER in text:
        print("IDEMPOTENT: correction already present. Skipping.")
        return 0

    norm = text.replace("\r\n", "\n")

    # anything that must still be there afterwards, checked BEFORE as well
    for s in survivors:
        c = norm.count(s)
        print(f"[survivor] present before: {c} (must be 1) — {s[:58]}…")
        if c != 1:
            print("ABORT: survivor text not found before patching.", file=sys.stderr)
            return 1

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

    for label, old, _ in subs:
        if old in patched:
            print(f"ABORT: superseded claim survives for {label}.", file=sys.stderr)
            return 1
    print("superseded S80 claim removed")

    for s in survivors:
        c = patched.count(s)
        print(f"[survivor] present after: {c} (must be 1)")
        if c != 1:
            print("ABORT: survivor text disturbed — the S79 footer must not be touched.",
                  file=sys.stderr)
            return 1

    if patched.count(MARKER) != 1:
        print("ABORT: correction not inserted exactly once.", file=sys.stderr)
        return 1
    if "8 GiB gp2 → 30 GiB gp3" not in patched:
        print("ABORT: the volume change is not stated.", file=sys.stderr)
        return 1
    print("correction present once and states the volume change")

    if not apply:
        print("DRY RUN -- no write.")
        return 0

    backup = path.with_name(path.name + "_PRE_S80_CORR2")
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
    for path, subs, survivors in JOBS:
        rc = max(rc, process(path, subs, survivors, args.apply))
    if rc == 0 and not args.apply:
        print("\nAll three files clean. Re-run with --apply.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
