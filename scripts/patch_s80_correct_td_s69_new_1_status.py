#!/usr/bin/env python3
"""patch_s80_correct_td_s69_new_1_status.py

S80 doc-close -- CORRECTION pass across two already-applied files.

WHAT WENT WRONG. The S80 incident document records TD-S69-NEW-1 as "open at P0
since the 2026-08-12 disk-full incident". That claim was carried into
Deployment Topology §S80 (twice) and the Assumption Register's S80 cross-ref
list (once) without checking tech_debt.md.

WHAT THE REGISTER ACTUALLY SAYS -- and it says two things:

  heading  (tech_debt.md:2063)  "RESOLVED S71 by measurement; root-cause row
                                 was wrong"
  Status row (tech_debt.md:2085) "OPEN -- P0 into S70. The cleanup bought
                                 headroom; it did not raise the ceiling."

Both have stood unreconciled since S71. The incident document read the Status
row; a later reading took the heading. **Neither claim was safe, because the
entry supports both.** This is the TD-061 shape the register codified against
at S29 ("TD body-state must match footer-claim", Topology section 7.2), in
violation for four sessions, and it produced two opposite readings of one file
on one day.

THREE substitutions across TWO files, each count==1. Both files were applied
earlier in this same doc-close; this corrects them in place rather than
reverting, because the surrounding sections are correct and a revert would
discard them.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchors, growth assertion, _PRE_S80_CORR backup per file, dry-run default.
"""
import argparse, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
TOPOLOGY = HERE / "docs" / "registers" / "MERDIAN_Deployment_Topology.md"
ASSUMPTION = HERE / "docs" / "registers" / "MERDIAN_Assumption_Register.md"

MARKER = "The entry contradicts itself."

# ---- Topology, substitution 1: the section 80.8 closure paragraph ----------

T_OLD_1 = ("**TD-S69-NEW-1 is CLOSED by the resize** — open at P0 since 2026-08-12, "
           "whose own recorded conclusion was that the `SystemMaxUse=200M` journal cap "
           "*\"only delays recurrence\"* and that the volume needed growing. "
           "**It predicted this incident and named the fix.**")

T_NEW_1 = r"""**TD-S69-NEW-1 is CLOSED by the resize** — and the state it was in when S80 opened is itself a finding. **The entry contradicts itself.** Its heading reads *"**RESOLVED S71 by measurement; root-cause row was wrong**"*; its Status row, eighteen lines below, reads *"**OPEN — P0 into S70.** The cleanup bought headroom; it did not raise the ceiling."* Both have stood, unreconciled, since S71.

**That contradiction produced two opposite readings of the same file on the same day.** The S80 incident document read the Status row and recorded the item as *"open at P0 since the 2026-08-12 disk-full incident"*; a second reading took the heading and concluded it had been closed at S71. Neither claim was safe, and neither reader was careless — **the entry supports both**. This is the **TD-061 shape**, and this register codified the rule against it at **S29** (§7.2, *"TD body-state must match footer-claim"*, filed as a Doc Protocol v4 candidate rule). It has been in violation for four sessions. Filed as **TD-S80-NEW-19**.

**What the entry got right, on either reading:** its *Proper fix* row named **"Grow the EBS root volume"** first, and its *Workaround* row recorded the `SystemMaxUse=200M` journal cap as explicitly **partial** — *"The cleanup bought headroom; it did not raise the ceiling."* **The remedy applied on 2026-09-22 is the one this entry specified in August.**

**Why it lapsed is the part worth carrying.** The S71 resolution rested on §S71.4's ~17 MB/day measurement, which was **correct for its regime** and was invalidated by a consumer installed 2026-09-06 (**D.37.8**). **A resolved item has no watcher** — when its premise expired, nothing fired. That is the argument for item 2 above: discipline does not reopen a closed item whose premise has changed; only a live check does."""

# ---- Topology, substitution 2: the section footer clause -------------------

T_OLD_2 = ("**TD-S69-NEW-1 CLOSED**, P0 since 2026-08-12, having predicted this "
           "incident and named its fix.")

T_NEW_2 = ("**TD-S69-NEW-1 CLOSED** — and found on arrival in a **self-contradictory "
           "state**, its heading reading `RESOLVED S71 by measurement` against a Status "
           "row reading `OPEN — P0 into S70`, unreconciled since S71 and the reason two "
           "readers reached opposite conclusions about it on the same day; the TD-061 "
           "shape this register codified against at S29, filed as **TD-S80-NEW-19**. "
           "Its *Proper fix* row named **\"Grow the EBS root volume\"** in August and "
           "that is the remedy applied here; **its S71 closure lapsed because a resolved "
           "item has no watcher** when its premise expires (D.37.8).")

# ---- Assumption Register, substitution 3: the S80 cross-ref clause ---------

A_OLD = ("**§S69** (the 2026-08-12 disk incident and TD-S69-NEW-1, open at P0 since)")

A_NEW = ("**§S69** (the 2026-08-12 disk incident and TD-S69-NEW-1, whose heading has read "
         "`RESOLVED S71` against a Status row reading `OPEN — P0` since S71 — "
         "**TD-S80-NEW-19**)")

JOBS = [
    (TOPOLOGY, [("1. Topology §S80.8 closure paragraph", T_OLD_1, T_NEW_1),
                ("2. Topology §S80 footer clause", T_OLD_2, T_NEW_2)]),
    (ASSUMPTION, [("3. Assumption Register S80 cross-ref", A_OLD, A_NEW)]),
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

    if MARKER in text:
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

    # the inherited claim must be gone from this file
    for dead in ("open at P0 since 2026-08-12", "P0 since 2026-08-12, having predicted"):
        if dead in patched:
            print(f"ABORT: superseded claim still present: {dead!r}", file=sys.stderr)
            return 1
    print("inherited 'open at P0' claim removed")

    if patched.count("TD-S80-NEW-19") < 1:
        print("ABORT: TD-S80-NEW-19 reference missing.", file=sys.stderr)
        return 1
    print(f"TD-S80-NEW-19 referenced {patched.count('TD-S80-NEW-19')}x")

    if not apply:
        print("DRY RUN -- no write.")
        return 0

    backup = path.with_name(path.name + "_PRE_S80_CORR")
    backup.write_bytes(raw)
    print(f"backup: {backup}")
    out = patched.replace("\n", eol) if eol != "\n" else patched
    path.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write; default is dry-run")
    ap.add_argument("--root", default=None,
                    help="override the repo root holding docs/registers/")
    args = ap.parse_args()

    jobs = JOBS
    if args.root:
        r = pathlib.Path(args.root)
        jobs = [(r / "docs" / "registers" / p.name, s) for p, s in JOBS]

    rc = 0
    for path, subs in jobs:
        rc = max(rc, process(path, subs, args.apply))
    if rc == 0 and not args.apply:
        print("\nBoth files clean. Re-run with --apply.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
