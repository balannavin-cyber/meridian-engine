#!/usr/bin/env python3
"""patch_s80_docclose_topology.py

S80 doc-close, file 9 -- docs/registers/MERDIAN_Deployment_Topology.md

ONE substitution, count==1: a new "## §S80" section is appended at the tail,
anchored on the §S76 footer's closing clause.

THIS IS THE FIRST TOPOLOGY SECTION SINCE S76. S77, S78 and S79 each closed
without one, correctly -- nothing moved. S80 moves the root volume, the
logrotate scope and the boot kernel, so it gets a section. The other S80 work
(two views, a table, a function, two patched scripts) changed no boundary and
is recorded in System Map §S80, not here.

canon-v3: read_bytes, utf-8-sig, EOL detect/restore, BOM preserved, count==1
anchor, line delta computed FROM the replacement text, growth assertion,
_PRE_S80_DOCCLOSE backup, dry-run default (--apply).
"""
import argparse, pathlib, sys

DEFAULT_TARGET = (pathlib.Path(__file__).resolve().parent.parent
                  / "docs" / "registers" / "MERDIAN_Deployment_Topology.md")
MARKER = "## §S80"

OLD = ("TD-S73-NEW-10, still not fixed here.) Previous: Session 75, "
       "2026-09-08/09 (§S75).*")

NEW = OLD + r"""

---

## §S80 — Session 80 (2026-09-22): the root volume was too small, and every way in needed it

**First Topology section since §S76.** S77, S78 and S79 each closed without one and were right to — nothing moved. This one moves the **root volume**, the **logrotate scope** and the **boot kernel**, and it resolves a standing risk carried since S71.

The session's other work — two views, a table, a plpgsql function, two patched Python scripts — **changed no boundary at all** and is recorded in **System Map §S80**. Nothing in it bears on this section, and in particular **the S80 ingest change did not contribute to the disk event**: `EXPIRY_DEPTH` shipped at depth 1 with the extra pass unreachable, `grep -c "S80 extra expiries"` on `cron.log` returns **0** for the whole day, and the growth predates the patch by two weeks.

### S80.1 — The failure: a full root disk removes every documented way in

Root filesystem on `i-0878c118835386ec2` reached **100%**. Both access paths failed together:

| Path | Failure | Why |
|---|---|---|
| **SSM Session Manager** | `TargetNotConnected` | `amazon-ssm-agent` **is a snap on the root volume** (D.29.6 records it as the sole access path) |
| **EC2 Instance Connect** | `Error establishing SSH connection` | Instance Connect must **write** an ephemeral public key onto the host |
| Run Command | unavailable | same agent |

**This is one property, not two coincident failures: every documented access path requires the resource that failed.** Filed as **D.37.1**.

**`describe-instance-status` reported `running / ok / ok` throughout.** Both status checks passed while nothing could reach the box — instance health and access health are independent, and the green check is the first thing anyone consults (**D.37.3**).

**The surviving path is MALPHA's key-auth SSH**, and it survives *because it needs no write* — key auth reads an already-present `authorized_keys`. That path exists from the 2026-04-15 token-sync work (**§S71.1**), is contrary to the SSM-only access model **§1** records, and **was not reachable at the time**, so the stop/start was taken as second choice. **It remains the correct first attempt and should be documented as such** (**D.37.2**).

### S80.2 — Timeline, measured from the database rather than the console

The console's last pre-recovery entry is `systemd-journald … No space left on device` at **04:12:21 UTC (09:42:21 IST)**. **That is not the onset.**

| Event | IST | Source |
|---|---|---|
| Feed delivering, `coverage_pct = 100.0` continuously | 09:11:04 → **09:27:03** | `breadth_intraday_history` |
| Last breadth write | **09:27:03** | `breadth_intraday_history` |
| Last spot write | **09:29:04** | `market_spot_snapshots` |
| *(journald logs its own failure)* | 09:42:21 | console output |
| Writers resume; feed still dark (`coverage_pct = 0.0`) | **10:09:04** | both relations |
| Feed restored by hand | **10:17:03** | `breadth_intraday_history` returns to 100.0 |

**Onset is ~09:28 IST — fourteen minutes before the console stamp.** journald records when *journald* noticed, and journald is itself a casualty, so it is the wrong instrument for onset (**D.37.5**).

**Cron-layer dark: ~09:28 → 10:09, about 40 minutes**, consistent across both writers.

**Feed dark: upper bound 09:28 → 10:16 ≈ 48 minutes, not the 66 first recorded** — the 03:40 UTC timer *did* fire and the feed delivered for sixteen minutes. **The interval 09:28–10:08 is UNOBSERVABLE**, because the writer that would have recorded the feed's state was down with the box (**D.37.6**).

**`index_futures_snapshots` lost its whole morning window** — first row today **10:10 IST** against a `*/5 04-09` UTC cron that should have started at 09:30. The rate since is correct. This matters more than the equivalent gap elsewhere: the script captures a **live LTP with no historical equivalent** (§S71.D), so those minutes are unrecoverable and `basis_context_snapshots` carries the hole.

### S80.3 — Root volume resized, and the EIP was verified before anything was stopped

| Item | Before | After |
|---|---|---|
| Volume `vol-09b957d7f294beba0` | **8 GiB gp2** | **30 GiB gp3**, 3000 IOPS, 125 MiB/s |
| Filesystem | 7.6 G, 100% | **29 G, 5.6 G used, 24 G free (20%)** |
| Resize downtime | — | **none for the volume modification itself** |

**Order of operations, and it is the part worth reusing:**

1. **Snapshot first** — `snap-0e111e3c1d5cd1f93` (*"pre-resize 2026-09-22"*), **completed before any restart**. This was the rollback for step 4.
2. **Grow the volume online**, no instance state change.
3. **Verify the IP is a true Elastic IP before touching instance state** — `13.63.27.85` / `eipalloc-032ba083824b3ae47`. **Dhan and ICICI both whitelist that address**; an auto-assigned IP would have been lost on stop and broken both whitelists, and the recovery would have gone through MALPHA instead.
4. **Stop/start**, deliberately, during market hours. `Stopping` hung several minutes — expected on a full disk. Returned `Running`, 3/3 checks.
5. **cloud-init ran `growpart` and `resize2fs` on boot unaided.**

**A t3.small → t3.medium change was deliberately NOT bundled into this restart**, so a failed boot would have had one variable rather than two. The instance-type question is carried, with a measurement owed — noting that **MALPHA is already t3.medium on a 30 GiB gp3 root for a job that does one `grep` and one `ssh` a day**, while the box running the entire pipeline was t3.small on 8 GiB. **The capacity is in the wrong place.**

**Cooldown:** no further volume modification until ~15:52 IST.

### S80.4 — A risk carried since S71 was discharged by this boot

**§S71.4** recorded: running kernel `6.8.0-1052-aws` while `/boot/vmlinuz` pointed at **1061**, so *"the next reboot boots a kernel this instance has never booted"*, under `GRUB_FORCE_PARTUUID` initrdless boot. **§S72.G carried it forward unchanged.**

**That reboot happened, and it booted clean.** `systemctl --failed` → **0 units**. The risk is **CLOSED**. It was discharged by an unplanned restart rather than a planned one, which is worth noting: the risk had been carried for four sessions precisely because nobody wanted to reboot to find out.

**`.env` survived intact** — `ZERODHA_ACCESS_TOKEN` 1, `DHAN_API_TOKEN` 1, and a `<` count of **0**. No repeat of the 2026-08-12 corruption, where a full-disk `sed -i` wrote the literal placeholder `<real-token>` into line 24 and the unquoted `<` then broke every subsequent `.env` source (§S69). Cron layer confirmed firing on recovery — `run_ingest.sh NIFTY FULL` rc=0 at 04:45:09Z, 472 rows — and **`SHELL=/bin/bash` is still crontab line 1** (the S53 root cause).

### S80.5 — `merdian-wsfeed` needed a human, and the unit file says why

The service was **`inactive (dead)`, not `failed`** — so `systemctl reset-failed` (the §S69 recovery canon) was not required and would have done nothing. It was started by hand: preflight exit 0, token valid, **single PID 1202**.

**It needed a hand because `merdian-wsfeed-start.timer` is `Persistent=false`.** §S72.B recorded that property; S80 measured its consequence — the 03:40 UTC start fired normally, the feed died with the box, and because the timer is start-only and non-persistent **nothing retried on recovery** (**D.37.4**). Whether it should become `Persistent=true` is an open decision: a persistent timer would have restarted the feed automatically at 10:09, but it would also fire a start on any boot, including one after the stop timer has legitimately run.

### S80.6 — logrotate scope widened, closing TD-S73-NEW-1

| | Before | After |
|---|---|---|
| `/etc/logrotate.d/meridian` covers | `cron.log`, `logs/*.log` | **`/home/ssm-user/meridian-engine/*.log`** + `logs/*.log` |
| `shadow_runner.log` | **outside scope** — 274 MB at S73, **313,728,377 bytes** at S80 | rotated; `.1` gzipped to **~15 MB** |

**This closes TD-S73-NEW-1**, open since 2026-09-06: an unbounded repo-root writer whose crontab line redirects to `logs/orchestrator.log` — a correctly-rotated decoy — while an internal handler wrote to a hardcoded repo-root path that logrotate's two globs never reached.

**Backup:** `/etc/logrotate.d/meridian.PRE_20260922`.

**Still outside scope:** `~/meridian-engine/C:\GammaEnginePython\heartbeats/` (TD-S73-NEW-2) — the directory whose *name* is a Windows path string, writer still unidentified.

**New exposure, and it is the third instance of one shape.** `/etc/logrotate.d/meridian` **lives only on the box**. §S68 brought the crontab under version control at `docs/registers/aws_crontab.txt` for exactly this reason; **§S74.B** recorded the same gap for the twenty systemd units and it was never closed. The logrotate config now joins them. **Copy it to `docs/registers/` beside `aws_crontab.txt`, per the S68 precedent.**

### S80.7 — What is NOT explained, and why the resize is not yet a fix

Growth measured **4.9 GB at S73 (2026-09-06) → 7.6 GB ceiling (2026-09-22)**: ~2.5 GB in sixteen days, **~150 MB/day**.

`du -x -d 2` on the leading candidate, and it **corrects the attribution**:

| Block | Size | Attribution |
|---|---|---|
| `.local/share/claude` | 636 M | Claude Code version retention |
| `.claude` | 102 M | Claude Code state — **78 M of it `projects/-home-ssm-user-meridian-cc`**, agent transcripts, growing per session |
| `.local/lib/python3.10` | 236 M | **pip user site-packages — the engine's own dependencies, NOT Claude** |
| `.cache/pip` | 57 M | **pip's HTTP cache, NOT Claude** |

**Claude Code is ≈738 MB, not the ~1.0 GB first recorded** — about **46 MB/day**, **under a third** of the measured rate. **~1.76 GB remains unattributed** (**D.37.7**). The reboot returning ~1.5 GB points at **deleted-but-still-open files**, and `lsof +L1` after the restart is empty, so it cannot be attributed retroactively.

**Until the remaining 1.76 GB is found, the resize is a delay of known length, not a fix** — 24 GB at 150 MB/day is about five months.

**Two readings are superseded, and neither was wrong when taken.** **§S71.4** concluded *"No EBS resize required"* on *"~17 MB/day ≈ 100 days headroom"*, and **§S73.E** recorded free space **rising** at 65% / 2.8 G. Both measured a regime that ended on **2026-09-06** — the day Claude Code was installed, and the same day §S73.E's measurement was taken. The new consumer arrived at roughly **9×** the rate those estimates were built on. **An extrapolation is only as durable as the consumer set it was measured over, and neither reading stated its consumer set** (**D.37.8**). A reader arriving at §S71.4 must not take *"no resize required"* as current.

### S80.8 — Owed, and named so it is not lost

| # | Item |
|---|---|
| 1 | **Find the ~1.76 GB.** `du` on `/var/lib`, `/var/log`, and the two repo trees. Without it the resize has a five-month clock on it. |
| 2 | **A disk guard.** A daily check firing the existing `wsfeed_alert.sh` Telegram path past 80%. **This is the actual failure class** — the condition was visible in the system for sixteen days and invisible to the operator, which is §6.11's pg_cron gap at a second surface. |
| 3 | **Version-control `/etc/logrotate.d/meridian`** into `docs/registers/`, per S68. Third instance of on-box-only config after the crontab (closed) and the systemd units (§S74.B, open). |
| 4 | **Decide `Persistent=true`** on `merdian-wsfeed-start.timer`. |
| 5 | **Revisit the instance type with a measurement**, and the MALPHA/MERDIAN capacity inversion with it. |
| 6 | **Quantify today's data gap in Supabase** and establish what is backfillable — futures is the part that is not. |

**TD-S69-NEW-1 is CLOSED by the resize** — open at P0 since 2026-08-12, whose own recorded conclusion was that the `SystemMaxUse=200M` journal cap *"only delays recurrence"* and that the volume needed growing. **It predicted this incident and named the fix.** Whether 2026-09-22 is the second or third failure of its class is **not settled**: two EBS exhaustions are documented (08-12, 09-22), §S71.4 was pressure without outage, and 2026-05-14's 62 GB was **Supabase `market_ticks` — a different resource on a different volume** (**D.37.10**).

*Deployment Topology updated Session 80, 2026-09-22 (§S80 — **first Topology section since §S76**; root volume `vol-09b957d7f294beba0` **8 GiB gp2 → 30 GiB gp3** after a 100% fill removed **both** documented access paths at once, SSM and Instance Connect together, because the SSM agent is a snap on the failed volume and Instance Connect must write a key to it — one property, not two failures, and `describe-instance-status` read `running / ok / ok` throughout; MALPHA key-auth SSH identified as the surviving path precisely because it needs no write, and recorded as the correct first attempt next time; **onset measured from the database at ~09:28 IST, fourteen minutes before the journald console stamp**, with the cron layer dark ~40 minutes and the feed's dark window bounded at ≤48 minutes and its interior **named unobservable** rather than estimated; `index_futures_snapshots` lost 09:30–10:05 with **no historical equivalent to backfill from**; snapshot-then-grow-then-verify-EIP-then-restart recorded as the reusable order, with the t3.medium change **deliberately not bundled**; the **S71 kernel risk discharged** — 1061 booted clean, 0 failed units, `.env` intact with no repeat of the 08-12 `sed` corruption; `merdian-wsfeed` found `inactive (dead)` not `failed` and started by hand because its start timer is `Persistent=false`; **logrotate scope widened, closing TD-S73-NEW-1** and gzipping a 313 MB `shadow_runner.log`, while the config itself becomes the **third** instance of on-box-only infrastructure after the crontab and the twenty systemd units; and the ~150 MB/day consumer **still unidentified** — Claude Code measured at **738 MB not ~1.0 GB**, under a third of it, leaving ~1.76 GB unattributed and the resize a five-month delay until it is found. **§S71.4's "No EBS resize required" and §S73.E's rising-free-space reading are superseded as regime-dependent, not wrong.** **TD-S69-NEW-1 CLOSED**, P0 since 2026-08-12, having predicted this incident and named its fix. The S80 database and script work changed no boundary and is in System Map §S80; the ingest change is measured to have contributed nothing.) Previous: Session 76, 2026-09-09/10 (§S76).*"""


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

    n = norm.count(OLD)
    print(f"[S76 footer tail] anchor count == {n} (must be 1)")
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

    checks = [
        ("S80 section heading", patched.count("## §S80 — Session 80"), 1),
        ("S80.1", patched.count("### S80.1"), 1),
        ("S80.2", patched.count("### S80.2"), 1),
        ("S80.3", patched.count("### S80.3"), 1),
        ("S80.4", patched.count("### S80.4"), 1),
        ("S80.5", patched.count("### S80.5"), 1),
        ("S80.6", patched.count("### S80.6"), 1),
        ("S80.7", patched.count("### S80.7"), 1),
        ("S80.8", patched.count("### S80.8"), 1),
        ("S80 footer", patched.count("*Deployment Topology updated Session 80"), 1),
        ("S76 section intact", patched.count("## §S76 — Session 76"), 1),
        ("S76 footer intact", patched.count("*Deployment Topology updated Session 76"), 1),
    ]
    ok = True
    for label, got_v, want in checks:
        flag = "OK " if got_v == want else "FAIL"
        print(f"  [{flag}] {label}: {got_v} (want {want})")
        ok = ok and got_v == want
    if not ok:
        print("ABORT: structural assertions failed.", file=sys.stderr)
        return 1

    tail = patched.rstrip()
    if not tail.endswith("Previous: Session 76, 2026-09-09/10 (§S76).*"):
        print("ABORT: S80 section is not at the file tail.", file=sys.stderr)
        return 1
    print("S80 section is last in the file")

    # the volume identity must appear, and only in the new section
    for token in ("vol-09b957d7f294beba0", "snap-0e111e3c1d5cd1f93"):
        c = patched.count(token)
        print(f"{token}: {c}")
        if c < 1:
            print(f"ABORT: {token} missing.", file=sys.stderr)
            return 1

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
