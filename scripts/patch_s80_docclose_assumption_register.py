#!/usr/bin/env python3
"""patch_s80_docclose_assumption_register.py  (rev 2 -- opens D.37)

S80 doc-close, file 8 of 10 -- docs/registers/MERDIAN_Assumption_Register.md

ONE substitution, count==1: §D.37 plus an S80 update-log paragraph are inserted
after the S79 update-log paragraph, which is the row they continue.

WHY §D.37 IS OPENED, AFTER REV 1 ARGUED AGAINST IT. Rev 1 held that S80 should
open no section, on S79's explicit precedent: its findings were already filed as
TDs and as ADR-024 §A9's self-corrections, so a section would have been a tenth
copy. That reasoning still governs the DOCUMENTATION findings and they are still
not copied here. It does not govern the 2026-09-22 disk-full access lockout,
which produced environment properties in the §D.34 mould that exist in no TD and
no ADR -- and four rows that correct the incident document itself and exist
nowhere else at all. A section is the right home for those; a pointer is not.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchor, line delta computed FROM the replacement text, growth assertion,
_PRE_S80_DOCCLOSE backup, dry-run default (--apply).
"""
import argparse, pathlib, re, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "registers" / "MERDIAN_Assumption_Register.md")
MARKER = "**Update log — Session 80"

OLD = ("Decision Index **S79 footer** · System Map **§S79** · "
       "TD-S75-NEW-1, TD-S75-NEW-2.")

NEW = OLD + r"""

### D.37 — Session 80: the disk-full access lockout, and five claims the incident record got wrong (2026-09-22)

Environment properties in the §D.34 mould, plus the corrections measured while establishing them. Every row attributed *[measured here]* / *[committed doc]* / *[operator]*. The four REFUTED rows correct the S80 incident document, which was written from console output and inference before the database was queried.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| **D.37.1** | A full root disk kills **SSM Session Manager and EC2 Instance Connect together**, not one or the other | **CONFIRMED** *[measured here]* | Both failed simultaneously during the lockout — SSM `TargetNotConnected`, Instance Connect `Error establishing SSH connection`. Mechanism: `amazon-ssm-agent` **is a snap on the root volume** (already recorded at D.29.6 as the sole access path), and Instance Connect must **write** an ephemeral public key onto the host. **Both access paths require the resource they would be used to repair.** This is not two coincident failures; it is one property. |
| **D.37.2** | MALPHA's key-auth SSH is the surviving path **precisely because it needs no write** | **CONFIRMED** *[committed doc + measured here]* | §S71.1 records the MALPHA→MERDIAN SSH key and `authorized_keys` entry, both dated 2026-04-15. Key auth reads an already-present file; nothing is written to the full disk. It was the **first-choice** recovery route (hop to MALPHA, `growpart`/`resize2fs` live, no restart) and was unavailable at the time, so the stop/start was taken as second choice. The route remains correct and should be the documented first attempt next time. |
| **D.37.3** | `describe-instance-status` reporting `running / ok / ok` means the instance is reachable | **REFUTED** *[measured here]* | It reported `running / ok / ok` **throughout the lockout**. Both status checks passed while neither access path worked. **Instance health and access health are independent properties**, and the green check is the thing most likely to be consulted first. |
| **D.37.4** | `Persistent=false` on `merdian-wsfeed-start.timer` is a configuration detail | **CONFIRMED as consequential** *[committed doc + measured here]* | §S72.B recorded the property. S80 measured what it costs: the 03:40 UTC start **fired normally** at 09:10 IST, the feed died with the box, and because the timer is start-only and non-persistent **nothing retried** — the feed needed a human at 10:16 IST. A missed start on a wedged host is not recovered by recovery. |
| **D.37.5** | The outage began at **09:42 IST** (the 04:12:21 UTC journald `No space left on device` stamp) | **REFUTED** *[measured here]* | Last pre-outage writes: `breadth_intraday_history` **09:27:03**, `market_spot_snapshots` **09:29:04**. Neither wrote again until **10:09**. The cron layer had therefore stopped **~09:28**, **fourteen minutes before** the console stamp. **journald's message records when journald noticed, not when the disk filled** — and journald is itself a casualty, so it is the wrong instrument for onset. |
| **D.37.6** | *"The feed was down from its 03:40 UTC timer … up to 66 minutes of `market_ticks` and breadth"* | **REFUTED** *[measured here]* | `breadth_intraday_history` carries `coverage_pct = 100.0` **continuously from 09:11:04 to 09:27:03 IST** — the timer fired and the feed delivered for sixteen minutes. Upper bound on feed-dark is **09:28 → 10:16 ≈ 48 minutes**, not 66. **The interval 09:28–10:08 is UNOBSERVABLE**: the writer that would have recorded the feed's state was down with the box. Measured facts are delivering at 09:27, confirmed dark at 10:09 (rows present, coverage 0.0), restored 10:17. **The observer failed with the thing observed** — a shape worth naming, because it is why the death time reads as inferable when it is not. |
| **D.37.7** | *"`~/.local` 872 MB + `~/.claude` 102 MB + `~/.cache` 57 MB ≈ 1.0 GB, all Claude Code"* | **REFUTED on two of three terms** *[measured here]* | `du -x -d 2`: **`.local/share/claude` 636 MB + `.claude` 102 MB = 738 MB is Claude Code.** `.local/lib/python3.10` **236 MB is pip user site-packages** — the engine's own dependencies — and `.cache/pip` **57 MB is pip's HTTP cache**. Neither is Claude. At ~46 MB/day over sixteen days that is **under a third** of the measured ~150 MB/day, leaving **~1.76 GB unattributed**. **The resize is therefore not yet demonstrated to be a fix rather than a delay**, and the reboot returning ~1.5 GB points at deleted-but-still-open files as where the remainder went. |
| **D.37.8** | §S71.4's *"No EBS resize required"* on *"~17 MB/day ≈ 100 days headroom"*, and §S73.E's reading that free space was **rising** | **VALIDATED-as-regime-dependent** *[committed doc + measured here]* | **Neither was wrong when taken.** Both measured a regime that ended on **2026-09-06** — the day Claude Code was installed, and the same day §S73.E's 65 % / 2.8 G measurement was taken. The new consumer arrived at roughly **9×** the rate those estimates were built on. **An extrapolation is only as durable as the consumer set it was measured over, and neither reading stated its consumer set.** A headroom figure with no inventory beside it has an expiry date nobody can see — the D.30.1 shape (*a performance claim stated without its table size*) applied to disk. |
| **D.37.9** | `journalctl -u <unit>` returning `-- No entries --` means nothing was recorded | **REFUTED** *[measured here]* | It returned `-- No entries --` **with the hint** *"You are currently not seeing messages from other users and the system. Users in groups 'adm', 'systemd-journal' can see all messages."* That is **refusal, not absence** — the CANNOT-FIRE shape. The feed's death time was one step from being filed as unmeasurable on the strength of it. Any `journalctl` read on this host is run with privilege or it is not evidence. |
| **D.37.10** | The 2026-09-22 lockout is the **third** failure of its class | **NOT ESTABLISHED** *[measured here]* | Two EBS root-disk **exhaustions** are documented: 2026-08-12 (§S69) and 2026-09-22. §S71.4 records disk *pressure* managed to 66 % without an outage, and the 2026-05-14 62 GB event was **Supabase `market_ticks`, a different resource on a different volume**. Whether the count is two or three depends on whether "class" means EBS exhaustion or disk-capacity events generally. **Recorded as unsettled rather than asserted either way** — the count is used to argue recurrence, so it should be defined before it is quoted. |

**The row that matters most is D.37.1, and it is a design property rather than an incident detail.** Every documented access path to `i-0878c118835386ec2` depends on the root volume being writable. The one path that does not — key-auth SSH from MALPHA — exists by accident of the 2026-04-15 token-sync work (§S71.1), is contrary to the SSM-only access model §1 records, and was not reachable when it was needed. **A host whose recovery paths all require the resource that fails is a host with no recovery path.**

**Update log — Session 80 (2026-09-19→22):** **§D.37 added (10 rows — 4 CONFIRMED, 4 REFUTED, 1 VALIDATED-as-regime-dependent, 1 NOT ESTABLISHED).** All ten come from the 2026-09-22 disk-full access lockout; **four of them correct the incident document itself**, which was written from console output and inference before the database was queried, and they exist in no TD and no ADR.

**On the documentation half of this session, no section was opened, deliberately** — the same call S79 made and for the same reason. S80's measurements are filed as **TD-S80-NEW-1..14** and its five self-corrections as **ADR-025 Amendment A §A2**, in the §A9 form this register's D.30–D.36 sections established. A section for those would be a **tenth** copy of one session's material, which is the cost **TD-S73-NEW-8** records. **No pre-existing row was touched, superseded or deleted this pass.**

**What is recorded here about the documentation half, because it exists in no single entry:** the archive reflex is now on its **third consecutive session**, and the arithmetic across them is the finding rather than any one instance. ADR-024 **§A9** filed **eight** self-corrections at S79 and named four of them one reflex — *reasoning from the archive when the source was available*. ADR-025 **§A2** files **five** at S80 and **four of those five are the same reflex**: the minimum of a `LIMIT 20` sample read as the minimum of a set (**and this one is TD-S79-NEW-12's own shape, committed hours after patching the guard for it**); a run count three days stale read as current; a stale sentence in `CURRENT.md` read as a missing commit; and a cross-tier `sha256` comparison that **C-15 names an invalid instrument in a document that had already been read**. Against D.31's *"evidence that was available and not read"*, D.32.1–.2's *"a value derived once, carried forward as fact"*, and D.35.20/.24/.25/.26's *"settled against an object adjacent to the claim"*, this is **one error class across six sessions**, not six error classes. **It is not decaying.** **D.37.5, .6, .7 and .9 are the same class arriving from the operations side** — a console stamp read as onset, a timer assumed not to have fired, an attribution carried from a `du` nobody ran, and a permission refusal read as absence. The remedy every instance points at is identical and cheap in every one: **read the source before asserting about it.**

**The fifth S80 self-correction is a different and worse shape, and is named separately so it is not absorbed into the pattern above.** A topology claim — that `~/meridian-cc` would *"re-invert the deploy direction"* — was asserted **without reading `MERDIAN_Deployment_Topology.md`**, when **§S73.A** establishes the agent tree for precisely the opposite reason: so agent work happens on EC2 **without touching production**. The consequence was not theoretical. **Both S80 patch scripts ran against `~/meridian-engine`, the production tree**, until the operator's instruction to read PK first corrected it. Where the archive reflex produces a wrong *number*, this produced a wrong *action* on the tree the whole two-tree topology exists to protect — and it is the strongest available argument for ratifying the **deploy-direction inversion**, now **unratified for a fifth consecutive session** (§S73.B). A correction carried five sessions as a note is a correction the next reader will act against.

**One standing assumption is escalated by measurement without needing a row of its own.** **TD-S79-NEW-1** recorded that `GREATEST(dte,1)` overstates σ on expiry day. S80 measures that the overstatement is **time-varying, not a fixed bias** — **0.982 at 09:00 IST falling to 0.203 at 15:00 IST** — and, more consequentially, that it **hides** an effect rather than merely inflating one: under day-σ the 0-DTE pin↔max-pain gap looks **flat across the session**, and under the correct σ it **more than doubles**. A caveat that changes the *shape* of a finding is not a footnote. **The correction is carried in the data, not in prose** — `v_gex_pin_maxpain` emits `sigma_overstated_expiry_day` as a **column**, so it travels with the row instead of depending on a reader remembering this register.

Cross-refs: **ADR-025** (D1–D5, the parity acceptance criterion) · **ADR-025 Amendment A** §A1 (capture depth shipped as a constant against its own ruling, with the condition for moving it), §A2 (the five self-corrections), §A3 (D2 clause 4 discharged, Rule 10 not) · **ADR-024 §A9** (the eight this continues from) · **ADR-021** (why `gex_pin_maxpain_history` had to exist) · **ADR-023** (the fails-to-absent obligation the constant-over-parameter choice turns on) · **ADR-009** (the pre-registration governing whether pin↔max-pain coincidence predicts anything — UNANSWERED by design) · **C-15** (`git hash-object`, never `sha256`, across tiers) · **§S69** (the 2026-08-12 disk incident and TD-S69-NEW-1, open at P0 since) · **§S71.1** (the MALPHA SSH path D.37.2 turns on) · **§S71.4 / §S73.E** (the superseded headroom readings) · **§S72.B** (the timer property D.37.4 measures) · **§S73.A / §S73.B** (the agent tree, and the unratified deploy direction) · D.29.6, D.30.1, D.30.4/.5, D.31.1/.8, D.32.1/.2, D.33.8, D.34, D.35.20/.24/.25/.26 · TD-S69-NEW-1, TD-S79-NEW-1, TD-S79-NEW-12, TD-S79-NEW-21, TD-S73-NEW-8 · TD-S80-NEW-1..14 · Decision Index **S80 footer** · System Map **§S80** · Deployment Topology **§S80** · `CASE-2026-09-22-disk-full-access-lockout.md`."""


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

    sections = sorted({int(m) for m in re.findall(r"D\.(\d{1,2})\s*—", norm)})
    print(f"§D sections before: highest is D.{sections[-1]}")
    if sections[-1] != 36:
        print(f"ABORT: expected D.36 to be highest; found D.{sections[-1]}. "
              f"Another session may have opened D.37 already.", file=sys.stderr)
        return 1

    n = norm.count(OLD)
    print(f"[S79 update-log tail] anchor count == {n} (must be 1)")
    if n != 1:
        print("ABORT: anchor not unique.", file=sys.stderr)
        return 1

    patched = norm.replace(OLD, NEW, 1)

    expected = NEW.count("\n") - OLD.count("\n")
    got = patched.count("\n") - norm.count("\n")
    print(f"line delta expected {expected}, got {got}")
    if expected != got:
        print("ABORT: line delta mismatch.", file=sys.stderr)
        return 1

    if len(patched) <= len(norm):
        print("ABORT: file did not grow.", file=sys.stderr)
        return 1
    print(f"byte delta (normalised): +{len(patched) - len(norm)}")

    after = sorted({int(m) for m in re.findall(r"D\.(\d{1,2})\s*—", patched)})
    print(f"§D sections after: highest is D.{after[-1]} (must be 37)")
    if after[-1] != 37:
        print("ABORT: D.37 not opened.", file=sys.stderr)
        return 1
    if set(after) - set(sections) != {37}:
        print(f"ABORT: unexpected section change {set(after) - set(sections)}", file=sys.stderr)
        return 1
    print("D.37 opened; no other section disturbed")

    rows = len(re.findall(r"\|\s\*\*D\.37\.\d+\*\*\s\|", patched))
    print(f"D.37 rows: {rows} (must be 10)")
    if rows != 10:
        print("ABORT: D.37 row count wrong.", file=sys.stderr)
        return 1

    if patched.count(MARKER) != 1:
        print("ABORT: S80 update log not inserted exactly once.", file=sys.stderr)
        return 1

    prior = len(re.findall(r"\*\*Update log — Session \d+", norm))
    now = len(re.findall(r"\*\*Update log — Session \d+", patched))
    print(f"update-log paragraphs: {prior} -> {now} (must be +1)")
    if now != prior + 1:
        print("ABORT: update-log count did not advance by exactly 1.", file=sys.stderr)
        return 1

    i79 = patched.index("**Update log — Session 79")
    i37 = patched.index("### D.37 —")
    i80 = patched.index(MARKER)
    if not i79 < i37 < i80:
        print("ABORT: expected order S79 log, then D.37, then S80 log.", file=sys.stderr)
        return 1
    print("order intact: S79 update log -> D.37 -> S80 update log")

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
