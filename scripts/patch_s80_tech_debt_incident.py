#!/usr/bin/env python3
"""patch_s80_tech_debt_incident.py

S80 doc-close -- docs/registers/tech_debt.md, entries TD-S80-NEW-14..19.

ONE substitution, count==1: six entries are inserted immediately before the
TD-S79-NEW-1 heading, which is the first entry after TD-S80-NEW-13's block.
Active debt is newest-first and TD-S80-NEW-1..13 already sit at its head, so
this lands 14..19 in numeric order behind them rather than against the grain.

FIVE OF THE SIX COME FROM THE 2026-09-22 DISK-FULL ACCESS LOCKOUT. The sixth
(-14) is the Enhancement Register staleness carried from earlier in this same
doc-close.

NOT DONE HERE, DELIBERATELY:
  * TD-S69-NEW-1's move from Active debt to Resolved -- an extract-and-relocate,
    structurally different from an insert, and given its own script.
  * TD-S80-NEW-12's strengthening. The incident gives it a second and heavier
    instance, but its body has not been read from the live file, and anchoring
    on unread text is what produced this session's last correction. It is
    cross-referenced from -18 and -19 and strengthened when visible.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchor, line delta computed FROM the replacement text, growth assertion,
_PRE_S80_INCIDENT backup, dry-run default (--apply).
"""
import argparse, pathlib, re, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "registers" / "tech_debt.md")
MARKER = "### TD-S80-NEW-14"

OLD = ("### TD-S79-NEW-1 (S2 priority) — `GREATEST(dte, 1)` overstates σ on expiry day, "
       "so the moneyness band is widest on the day it most needs to bind")

ENTRIES = r"""### TD-S80-NEW-14 (S3 priority) — `tech_debt.md` closed TD-S79-NEW-14 and left three references to it stale one file over

| Field | Value |
|---|---|
| **Priority** | **S3.** No behaviour depends on it. It is filed because it is the third instance of a shape this register keeps recording. |
| **Discovered** | Session 80 (2026-09-22), while writing ENH-123/124 into the Enhancement Register. |
| **Component** | `docs/registers/MERDIAN_Enhancement_Register.md` |
| **Symptom** | Three places still assert the EXPLAIN is outstanding — ENH-121's *"3d EXPLAIN outstanding - TD-S79-NEW-14"*, ENH-122's *"3f EXPLAIN outstanding"*, and a file-tail bullet — while `tech_debt.md` records TD-S79-NEW-14 **RESOLVED at S79** on an `Index Only Scan` with no base-table scan. |
| **Root cause** | S79 closed the item in one register and did not sweep the others. **This is the TD-S76-NEW-12 shape:** an edit landing without the register's own self-description moving with it. S76 recorded three instances in one close and called it *"a pattern, not three accidents"*. |
| **Proper fix** | Applied at this doc-close as **annotation, not rewrite** — the as-filed text is kept and a CORRECTION note appended, per the register's convention that an entry records what was believed before it was measured. The residual is that the convention **has no sweep step**: nothing looks for other files asserting a closed item is open. |
| **Cost to fix** | Minutes for the instance; the sweep step is a protocol question. |
| **Blocked by** | nothing. |
| **Cross-ref** | TD-S76-NEW-12 · TD-S76-NEW-13..17 (the same class) · TD-S79-NEW-14 (RESOLVED S79, transcript-only evidence) · TD-S80-NEW-19 (the same shape inside a single entry). |
| **Status** | **OPEN.** Instance annotated at the S80 doc-close; the missing sweep step is the real item. |

### TD-S80-NEW-15 (S2 priority) — ~1.76 GB of the 2.5 GB that filled the root volume is unattributed, so the resize is a delay of known length rather than a fix

| Field | Value |
|---|---|
| **Priority** | **S2.** The volume is at 20% and the immediate risk is gone. The item is that **nobody can say what fills it**, and 24 GB at the measured rate is about five months. |
| **Discovered** | Session 80 (2026-09-22), after the disk-full access lockout. |
| **Component** | `i-0878c118835386ec2` root volume `vol-09b957d7f294beba0` · `~/.local` · `~/.claude` · `/var/lib` · `/var/log` |
| **Symptom** | Growth measured **4.9 GB at S73 (2026-09-06) → 7.6 GB ceiling (2026-09-22)** — ~2.5 GB in sixteen days, **~150 MB/day**. |
| **Root cause** | **Not established.** The leading candidate was recorded as *"~/.local 872 MB + ~/.claude 102 MB + ~/.cache 57 MB ≈ 1.0 GB, all Claude Code"*. **Measured, that attribution is wrong on two of three terms** — `.local/share/claude` 636 M + `.claude` 102 M = **738 MB is Claude Code**; `.local/lib/python3.10` **236 M is pip user site-packages** (the engine's own dependencies) and `.cache/pip` **57 M is pip's HTTP cache**. At ~46 MB/day that is **under a third** of the rate, leaving **~1.76 GB unexplained**. The reboot returned ~1.5 GB, which points at **deleted-but-still-open files**; `lsof +L1` after the restart is empty, so it cannot be attributed retroactively. |
| **Proper fix** | `du -x` on `/var/lib`, `/var/log` and both repo trees, and an `lsof +L1` **before** the next restart rather than after. Then decide whether 30 GiB is the right size or the growth is the defect. |
| **Cost to fix** | ~30 min of measurement; the remedy depends on what it finds. |
| **Blocked by** | nothing. |
| **Cross-ref** | Deployment Topology §S80.7 · Assumption Register **D.37.7** (the corrected attribution) and **D.37.8** (why §S71.4's headroom estimate lapsed) · TD-S69-NEW-1 (the ceiling item, closed by the resize) · TD-S73-NEW-1 (`shadow_runner.log`, closed by the logrotate widening) · TD-S73-NEW-2 (the `C:\GammaEnginePython\heartbeats/` writer, still unidentified). |
| **Status** | **OPEN.** Note that **78 MB of the measured Claude Code footprint is `~/.claude/projects/-home-ssm-user-meridian-cc`** — agent transcripts, which grow every session including this one. The agent tree is not free. |

### TD-S80-NEW-16 (S3 priority) — `/etc/logrotate.d/meridian` exists only on the box: third instance of on-box-only infrastructure after the crontab and the systemd units

| Field | Value |
|---|---|
| **Priority** | **S3.** Nothing breaks. A disaster rebuild silently loses log rotation, which is how the volume filled in the first place. |
| **Discovered** | Session 80 (2026-09-22), on widening the rotation scope. |
| **Component** | `/etc/logrotate.d/meridian` on `i-0878c118835386ec2` |
| **Symptom** | The config was edited this session — scope widened from `cron.log` + `logs/*.log` to `/home/ssm-user/meridian-engine/*.log` + `logs/*.log`, which is what finally caught a **313,728,377-byte** `shadow_runner.log`. The edit has **no diff, no review and no presence in a fresh clone**, and its backup `.PRE_20260922` sits beside it on the same volume. |
| **Root cause** | Same as the crontab before S68 and the systemd units still: infrastructure that lives only where it runs. **§S68 solved this for the crontab** by committing `docs/registers/aws_crontab.txt`; **§S74.B recorded the identical gap for twenty systemd units and three timers** and it was never closed. |
| **Proper fix** | Copy the live file to `docs/registers/logrotate_meridian.conf` and commit it, per the S68 precedent — noting §S68 needed a `.gitignore` negation to land `aws_crontab.txt`, so check `git check-ignore -v` rather than trusting an empty `git status`. Close the systemd half in the same pass or it becomes a fourth instance. |
| **Cost to fix** | Minutes. |
| **Blocked by** | nothing. |
| **Cross-ref** | Deployment Topology §S68 (the crontab precedent) · §S74.B (the systemd units, open) · §S80.6 · TD-S72-NEW-14 (no canonical tracked crontab source) · TD-S73-NEW-1 (CLOSED by this session's widening). |
| **Status** | **OPEN.** |

### TD-S80-NEW-17 (S3 priority) — `merdian-wsfeed-start.timer` is `Persistent=false`, so a start missed while the host is wedged needs a human

| Field | Value |
|---|---|
| **Priority** | **S3.** It is a decision, not a defect — but it cost ~34 minutes of feed on 2026-09-22 and will cost the same again. |
| **Discovered** | Property recorded at **S72.B**; consequence measured at Session 80 (2026-09-22). |
| **Component** | `/etc/systemd/system/merdian-wsfeed-start.timer` |
| **Symptom** | The 03:40 UTC start **fired normally** at 09:10 IST and the feed delivered until the box wedged at ~09:28. On recovery the service was **`inactive (dead)`, not `failed`** — so `systemctl reset-failed` (the §S69 recovery canon) was neither needed nor sufficient — and because the timer is start-only and non-persistent, **nothing retried**. It was started by hand at 10:16 IST. |
| **Root cause** | `Persistent=false` means a missed activation is not replayed on the next boot. Correct for a timer whose window has passed; wrong for one whose job should be running for the rest of the session. |
| **Proper fix** | **Decide, do not default.** `Persistent=true` would have restarted the feed at 10:09 unattended — but it also fires a start on **any** boot, including one after `merdian-wsfeed-stop.timer` has legitimately run at 10:05 UTC, which would start a feed outside market hours. The alternative is a recovery unit conditioned on market hours. Either way the unit file must then be version-controlled (TD-S80-NEW-16). |
| **Cost to fix** | ~30 min including the out-of-hours case. |
| **Blocked by** | TD-S80-NEW-16 in practice — changing an unversioned unit file repeats §S74.B. |
| **Cross-ref** | Deployment Topology §S72.B (the property) · §S80.5 (the consequence) · Assumption Register **D.37.4** · §S69 (`reset-failed` + `kill -9` canon, which did not apply here). |
| **Status** | **OPEN — decision owed.** |

### TD-S80-NEW-18 (S1 priority) — there is no disk guard: the condition that took the box down was visible in the system for sixteen days and invisible to the operator

| Field | Value |
|---|---|
| **Priority** | **S1. This is the failure class, and it is the only item here that would have prevented the outage.** |
| **Discovered** | Session 80 (2026-09-22). |
| **Component** | `i-0878c118835386ec2` · `scripts/eod_health_check.py` · `bin/wsfeed_alert.sh` (the existing Telegram path) |
| **Symptom** | Root filesystem climbed from 4.9 GB (2026-09-06) to 100% (2026-09-22) — **sixteen days, ~150 MB/day, entirely measurable throughout** — and produced no signal of any kind until both access paths failed at once. |
| **Root cause** | Nothing polls disk headroom. `eod_health_check.py` asserts on data freshness and continuity and **not on the host it runs on**; TD-S69-NEW-2's *Proper fix* row already named *"(d) disk headroom on the box"* and that clause was never built. **This is §6.11's pg_cron blind spot at a second surface** — a condition recorded continuously by the system and read by nothing. |
| **Proper fix** | A daily check firing the **existing** `wsfeed_alert.sh` Telegram path past 80%, and a second threshold at 90%. It must be a **live check, not a review item**: the whole lesson of TD-S69-NEW-1 is that a *resolved* entry has no watcher, so when its ~17 MB/day premise lapsed on 2026-09-06 nothing fired (**D.37.8**). Discipline does not reopen a closed item; only a check does. |
| **Cost to fix** | ~1 hour. The alert transport already exists and is proven. |
| **Blocked by** | nothing. **This should be the first thing built next session.** |
| **Cross-ref** | TD-S69-NEW-1 (closed by the resize; its premise lapsed unwatched) · TD-S69-NEW-2 clause (d), never built · TD-S80-NEW-15 (what to measure) · Deployment Topology §6.11, §S80.1, §S80.8 item 2 · Assumption Register **D.37.3** (a green `describe-instance-status` is not reachability), **D.37.8**. |
| **Status** | **OPEN — P0 into S81.** |

### TD-S80-NEW-19 (S2 priority) — TD-S69-NEW-1's heading says RESOLVED and its Status row says OPEN, and on 2026-09-22 two readers reached opposite conclusions from it

| Field | Value |
|---|---|
| **Priority** | **S2.** A register entry that supports contradictory readings is worse than a missing one, because both readers believe they checked. |
| **Discovered** | Session 80 (2026-09-22), when an incident document and a doc-close pass disagreed about the same item on the same day. |
| **Component** | `docs/registers/tech_debt.md` — TD-S69-NEW-1 |
| **Symptom** | Heading: *"(S1 priority — **RESOLVED S71 by measurement; root-cause row was wrong**)"*. Status row, eighteen lines below: *"**OPEN — P0 into S70.** The cleanup bought headroom; it did not raise the ceiling."* **Both have stood unreconciled since S71.** The S80 incident document read the Status row and recorded *"open at P0 since 2026-08-12"*; the doc-close read the heading and recorded it as closed at S71. **The inherited claim propagated into Deployment Topology §S80 twice and the Assumption Register once before it was caught**, and required a correction pass. |
| **Root cause** | S71 annotated the heading on a new measurement and **did not move the Status row**. This is the **TD-061 shape**, which this project codified against at **S29** — *"TD body-state must match footer-claim"*, recorded in Deployment Topology §7.2 as a Doc Protocol v4 candidate rule and **never made into one**. In violation for four sessions. |
| **Proper fix** | Two parts. **(a)** The instance: TD-S69-NEW-1 moves to Resolved with a closure block stating both prior states — done in this doc-close, separately. **(b)** The rule: promote the S29 candidate to an actual Doc Protocol rule, or add a mechanical check that a heading containing RESOLVED/CLOSED cannot coexist with a Status row containing OPEN. **The check is trivial and the rule has been a candidate for fifty-one sessions.** |
| **Cost to fix** | (a) done. (b) ~30 min for a grep-based check; the protocol amendment is an operator decision. |
| **Blocked by** | nothing. |
| **Cross-ref** | TD-S69-NEW-1 (the instance) · TD-061 / TD-063 (S29, the original shape) · Deployment Topology §7.2 *"TD body-state must match footer-claim"*, §S80.8 · Assumption Register **D.37.8** · TD-S80-NEW-14 (the same shape across files rather than within one entry) · TD-S76-NEW-12. |
| **Status** | **OPEN — part (a) closed at this doc-close, part (b) is the item.** |

"""

NEW = ENTRIES + OLD


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

    before = len(re.findall(r"^### TD-S80-NEW-\d+", norm, re.M))
    print(f"TD-S80-NEW headings before: {before} (expect 13)")
    if before != 13:
        print(f"ABORT: expected 13 existing S80 headings, found {before}.", file=sys.stderr)
        return 1

    n = norm.count(OLD)
    print(f"[TD-S79-NEW-1 heading] anchor count == {n} (must be 1)")
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

    after = len(re.findall(r"^### TD-S80-NEW-\d+", patched, re.M))
    print(f"TD-S80-NEW headings after: {after} (must be 19)")
    if after != 19:
        print("ABORT: heading count wrong.", file=sys.stderr)
        return 1

    for i in range(14, 20):
        c = len(re.findall(rf"^### TD-S80-NEW-{i} ", patched, re.M))
        print(f"  TD-S80-NEW-{i}: {c}")
        if c != 1:
            print(f"ABORT: TD-S80-NEW-{i} not present exactly once.", file=sys.stderr)
            return 1

    # numeric order at the head of Active debt
    order = [int(m) for m in re.findall(r"^### TD-S80-NEW-(\d+)", patched, re.M)]
    print(f"S80 heading order: {order}")
    if order != sorted(order):
        print("ABORT: S80 headings are not in numeric order.", file=sys.stderr)
        return 1

    if patched.count(OLD) != 1:
        print("ABORT: TD-S79-NEW-1 heading disturbed.", file=sys.stderr)
        return 1
    print("TD-S79-NEW-1 heading intact and immediately follows")

    # each new entry carries a Status row
    seg = patched[patched.index("### TD-S80-NEW-14"):patched.index(OLD)]
    rows = seg.count("| **Status** |")
    print(f"Status rows across the six new entries: {rows} (must be 6)")
    if rows != 6:
        print("ABORT: a new entry is missing its Status row.", file=sys.stderr)
        return 1

    if not args.apply:
        print("\nDRY RUN -- no write. Re-run with --apply.")
        return 0

    backup = target.with_name(target.name + "_PRE_S80_INCIDENT")
    backup.write_bytes(raw)
    print(f"backup: {backup}")

    out = patched.replace("\n", eol) if eol != "\n" else patched
    target.write_bytes((b"\xef\xbb\xbf" if had_bom else b"") + out.encode("utf-8"))
    print(f"WROTE {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
