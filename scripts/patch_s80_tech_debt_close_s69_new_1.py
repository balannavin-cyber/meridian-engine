#!/usr/bin/env python3
"""patch_s80_tech_debt_close_s69_new_1.py

S80 doc-close -- docs/registers/tech_debt.md: TD-S69-NEW-1 Active -> Resolved.

AN EXTRACT-AND-RELOCATE, not a splice. The block is lifted VERBATIM from
between its own heading and TD-S69-NEW-2's, two lines are rewritten (the
heading and the Status row), a closure block is appended, and the result is
re-inserted under "## Resolved (audit trail)". Nothing in the body is retyped.

WHY IT MOVES AT ALL. The register's S29 precedent (TD-061) is that a resolved
entry's BODY moves, not merely its heading changes -- leaving a CLOSED heading
in Active debt reproduces the exact defect TD-S80-NEW-19 files.

WHAT THE CLOSURE RECORDS. The entry arrived in a self-contradictory state:
heading "RESOLVED S71 by measurement", Status row "OPEN -- P0 into S70",
unreconciled since S71. The closure states BOTH prior readings rather than
picking one, because both were held by real readers on 2026-09-22 and the
entry supported each.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchors, verbatim-move assertion, line conservation, _PRE_S80_CLOSE backup,
dry-run default (--apply).
"""
import argparse, pathlib, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "registers" / "tech_debt.md")
MARKER = "CLOSED S80 2026-09-22 by the EBS resize"

H1 = ("### TD-S69-NEW-1 (S1 priority — **RESOLVED S71 by measurement; root-cause row "
      "was wrong**) — MERDIAN AWS EC2 root volume is 7.6 GB and hit 100% on 2026-08-12, "
      "cascading into a feed crash + `.env` corruption + a silently-failed breadth cron; "
      "the journal cap only delays recurrence")

H2 = ("### TD-S69-NEW-2 (S1 priority) — `scripts/eod_health_check.py` returned `[OK]` on "
      "2026-08-12 while pin/accel, the M5 detector and the GEX read path were all broken: "
      "it asserts on none of them")

RESOLVED_HEADING = "## Resolved (audit trail)"

OLD_STATUS = ("| **Status** | **OPEN — P0 into S70.** The cleanup bought headroom; "
              "it did not raise the ceiling. |")

NEW_HEADING = ("### TD-S69-NEW-1 (S1 priority — **CLOSED S80 2026-09-22 by the EBS resize**; "
               "entered S80 in a self-contradictory state, see TD-S80-NEW-19) — MERDIAN AWS "
               "EC2 root volume is 7.6 GB and hit 100% on 2026-08-12, cascading into a feed "
               "crash + `.env` corruption + a silently-failed breadth cron; the journal cap "
               "only delays recurrence")

NEW_STATUS = ("| **Status** | **CLOSED — Session 80, 2026-09-22.** Root volume "
              "`vol-09b957d7f294beba0` grown **8 GiB gp2 → 30 GiB gp3**; filesystem now "
              "29 G with 24 G free (20%). **The remedy is the one this entry's own "
              "*Proper fix* row named in August.** See the closure block below — this "
              "entry was carrying two contradictory statuses when it was closed. |")

CLOSURE = r"""

**Closure block — Session 80, 2026-09-22.**

**What closed it.** The 2026-09-22 disk-full access lockout forced the action this entry had specified since August. Root volume `vol-09b957d7f294beba0` grown **8 GiB gp2 → 30 GiB gp3** (3000 IOPS, 125 MiB/s), snapshot `snap-0e111e3c1d5cd1f93` taken first, EIP verified as a true Elastic IP before any instance state change, `growpart`/`resize2fs` run by cloud-init on boot. **29 G total, 5.6 G used, 24 G free.** Full account in Deployment Topology **§S80**.

**The entry was in two states at once, and both were read.** Its heading said *"**RESOLVED S71 by measurement; root-cause row was wrong**"*. Its Status row, eighteen lines below, said *"**OPEN — P0 into S70.** The cleanup bought headroom; it did not raise the ceiling."* **Both stood unreconciled from S71 to S80.** On 2026-09-22 the incident document read the Status row and recorded the item as *"open at P0 since 2026-08-12"*; the doc-close read the heading and recorded it as closed at S71. The first reading propagated into Deployment Topology §S80 twice and the Assumption Register once before it was caught, and needed a correction pass. **Neither reader was careless — the entry supported both.** Filed as **TD-S80-NEW-19**; it is the **TD-061 shape** this project codified against at **S29** (*"TD body-state must match footer-claim"*) and never promoted from a candidate rule.

**Why the S71 resolution lapsed, which is the part worth carrying forward.** It rested on §S71.4's measurement of **~17 MB/day ≈ 100 days headroom**, and on §S73.E's reading that free space was *rising* at 65% / 2.8 G. **Neither was wrong when taken.** Both measured a regime that ended on **2026-09-06** — the day a new consumer was installed, and the same day §S73.E's measurement was taken. Actual growth over the following sixteen days was **~150 MB/day, roughly 9×**. **A resolved item has no watcher**: when its premise expired, nothing fired, because closed items are not monitored — they are closed. See Assumption Register **D.37.8**.

**This is the argument for TD-S80-NEW-18**, filed S1 at the same doc-close. Review discipline does not reopen a closed item whose premise has changed; only a live check does. The condition was measurable in the system for sixteen days and read by nothing.

**What remains open after this closure.** The resize bought a known interval, not an answer: **~1.76 GB of the 2.5 GB that filled the volume is still unattributed** (**TD-S80-NEW-15**), so 24 GB at the measured rate is about five months. The associated retention question this entry raised — DB-side limits on `market_ticks` and `gex_strike_snapshots` — is **not** closed here and was never the binding constraint: §S71.5 measured `gex_strike_snapshots` at **438 MB, tenth largest**, which is why ADR-021's refusal to prune it stands.

**Cross-ref.** Deployment Topology §S69 (the 2026-08-12 incident that filed this), §S71.4 and §S73.E (the superseded readings), §S80 (the closure) · Assumption Register **D.37.1–.10** · TD-S80-NEW-15, **TD-S80-NEW-18**, TD-S80-NEW-19 · TD-S73-NEW-1 (CLOSED S80 by the logrotate widening) · ADR-021 (pruning rejected as the view fix).
"""


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
        print("IDEMPOTENT: marker already present. Nothing to do.")
        return 0

    norm = text.replace("\r\n", "\n")

    for label, needle in (("TD-S69-NEW-1 heading", H1),
                          ("TD-S69-NEW-2 heading", H2),
                          ("Resolved heading", RESOLVED_HEADING)):
        c = norm.count(needle)
        print(f"[{label}] count == {c} (must be 1)")
        if c != 1:
            print(f"ABORT: {label} not unique.", file=sys.stderr)
            return 1

    i1, i2, ir = norm.index(H1), norm.index(H2), norm.index(RESOLVED_HEADING)
    if not i1 < i2 < ir:
        print(f"ABORT: expected H1 < H2 < Resolved; got {i1} {i2} {ir}.", file=sys.stderr)
        return 1
    print("block sits in Active debt, above the Resolved section")

    block = norm[i1:i2]
    print(f"extracted block: {len(block)} bytes, {block.count(chr(10))} lines")

    if OLD_STATUS not in block:
        print("ABORT: the OPEN status row is not inside the extracted block.", file=sys.stderr)
        return 1
    if "Grow the EBS root volume" not in block:
        print("ABORT: extracted block does not carry its Proper fix text.", file=sys.stderr)
        return 1
    print("block identified by its own content (OPEN status row + Proper fix)")

    # rewrite exactly two lines, then append the closure
    moved = block.replace(H1, NEW_HEADING, 1).replace(OLD_STATUS, NEW_STATUS, 1)
    if moved == block:
        print("ABORT: rewrite changed nothing.", file=sys.stderr)
        return 1
    body_before = block.replace(H1, "").replace(OLD_STATUS, "")
    body_after = moved.replace(NEW_HEADING, "").replace(NEW_STATUS, "")
    if body_before != body_after:
        print("ABORT: block body changed beyond the two rewritten lines.", file=sys.stderr)
        return 1
    print("body verbatim: only the heading and Status rows differ")

    moved = moved.rstrip("\n") + "\n" + CLOSURE.rstrip("\n") + "\n\n"

    # remove from Active debt, then re-locate the Resolved heading and insert
    cut = norm[:i1] + norm[i2:]
    ir2 = cut.index(RESOLVED_HEADING) + len(RESOLVED_HEADING)
    patched = cut[:ir2] + "\n\n" + moved.rstrip("\n") + "\n" + cut[ir2:]

    expected = moved.count("\n") + 2 - block.count("\n") - 1
    got = patched.count("\n") - norm.count("\n")
    print(f"line delta expected {expected}, got {got}")
    if expected != got:
        print("ABORT: line delta mismatch.", file=sys.stderr)
        return 1

    if len(patched) <= len(norm):
        print("ABORT: file did not grow.", file=sys.stderr)
        return 1
    print(f"byte delta (normalised): +{len(patched) - len(norm)}")

    # the entry must now live below the Resolved heading, and only there
    if patched.count(NEW_HEADING) != 1:
        print("ABORT: relocated heading not present exactly once.", file=sys.stderr)
        return 1
    if H1 in patched:
        print("ABORT: the old contradictory heading survives.", file=sys.stderr)
        return 1
    if OLD_STATUS in patched:
        print("ABORT: the old OPEN status row survives.", file=sys.stderr)
        return 1
    ir3 = patched.index(RESOLVED_HEADING)
    if not patched.index(NEW_HEADING) > ir3:
        print("ABORT: entry is not below the Resolved heading.", file=sys.stderr)
        return 1
    print("entry relocated below '## Resolved (audit trail)'; old heading and status gone")

    if patched.count(H2) != 1 or patched.index(H2) > ir3:
        print("ABORT: TD-S69-NEW-2 disturbed or displaced.", file=sys.stderr)
        return 1
    print("TD-S69-NEW-2 intact and still in Active debt")

    for token in ("TD-S80-NEW-19", "TD-S80-NEW-18", "D.37.8", "vol-09b957d7f294beba0"):
        if token not in patched[patched.index(NEW_HEADING):]:
            print(f"ABORT: closure block missing {token}.", file=sys.stderr)
            return 1
    print("closure block carries its cross-refs")

    if not args.apply:
        print("\nDRY RUN -- no write. Re-run with --apply.")
        return 0

    backup = target.with_name(target.name + "_PRE_S80_CLOSE")
    backup.write_bytes(raw)
    print(f"backup: {backup}")

    out = patched.replace("\n", eol) if eol != "\n" else patched
    target.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
