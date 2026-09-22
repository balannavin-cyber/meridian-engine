# CASE-2026-09-22 — Disk-full access lockout: every documented way in needed the thing that failed

| Field | Value |
|---|---|
| Date | 2026-09-22 |
| Session | Session 80 |
| Host | `i-0878c118835386ec2` (meridian-server, t3.small, eu-north-1b) |
| Volume | `vol-09b957d7f294beba0` — 8 GiB gp2 → **30 GiB gp3** |
| Snapshot | `snap-0e111e3c1d5cd1f93` ("pre-resize 2026-09-22"), taken before any restart |
| Outcome | Recovered. ~40 min of capture lost, ~48 min upper bound on the feed. |
| Type | Single-event case study. Not an ADR — no architectural decision was taken. |

---

## 1. The finding that outlives the incident

**Every documented access path to this host requires the root volume to be writable.**

| Path | Failure | Why |
|---|---|---|
| SSM Session Manager | `TargetNotConnected` | `amazon-ssm-agent` **is a snap on the root volume** |
| EC2 Instance Connect | `Error establishing SSH connection` | must **write** an ephemeral public key to the host |
| Run Command | unavailable | same agent |

This is one property, not two coincident failures. A host whose recovery paths all depend on the resource that fails has no recovery path.

**The surviving route is MALPHA's key-auth SSH, and it survives precisely because it needs no write** — key auth reads an already-present `authorized_keys`. That path exists from the 2026-04-15 token-sync work (Topology §S71.1), is contrary to the SSM-only access model §1 records, and **was not reachable when it was needed**, so a stop/start was taken as second choice. It remains the correct first attempt.

**`describe-instance-status` reported `running / ok / ok` throughout.** Instance health and access health are independent, and the green check is the first thing anyone consults.

## 2. Timeline — measured from the database, not the console

The console's last pre-recovery entry is `systemd-journald … No space left on device` at **04:12:21 UTC (09:42:21 IST)**. **That is not the onset.**

| Event | IST | Source |
|---|---|---|
| Feed delivering, `coverage_pct = 100.0` continuously | 09:11:04 → **09:27:03** | `breadth_intraday_history` |
| Last breadth write | **09:27:03** | `breadth_intraday_history` |
| Last spot write | **09:29:04** | `market_spot_snapshots` |
| *journald logs its own failure* | 09:42:21 | console output |
| Writers resume; feed still dark (`coverage_pct = 0.0`) | **10:09:04** | both relations |
| Feed restored by hand | **10:17:03** | coverage returns to 100.0 |

- **Onset ~09:28 IST — fourteen minutes before the console stamp.** journald records when *journald* noticed, and journald was itself a casualty.
- **Cron layer dark ~40 minutes**, consistent across both writers.
- **Feed dark ≤48 minutes, not the 66 first recorded.** The 03:40 UTC timer *did* fire and the feed delivered for sixteen minutes.
- **09:28–10:08 is UNOBSERVABLE.** The writer that would have recorded the feed's state was down with the box. The observer failed with the thing observed.
- **`index_futures_snapshots` lost 09:30–10:05 permanently** — it captures a live LTP with no historical equivalent, so unlike the other relations this gap cannot be backfilled. `basis_context_snapshots` carries it.

## 3. Recovery, in the order worth reusing

1. **Snapshot first** — completed before any restart. This is the rollback for step 4.
2. **Grow the volume online.** No instance state change, no downtime for this step.
3. **Verify the IP is a true Elastic IP before touching instance state** — `13.63.27.85` / `eipalloc-032ba083824b3ae47`. Dhan and ICICI both whitelist it; an auto-assigned IP would have been lost on stop and broken both.
4. **Stop/start.** `Stopping` hung several minutes, expected on a full disk. Back `Running`, 3/3 checks.
5. **cloud-init ran `growpart` and `resize2fs` unaided.** 29 G, 5.6 G used, 24 G free.

**A t3.small → t3.medium change was deliberately not bundled**, so a failed boot would have had one variable rather than two.

**A risk carried four sessions was discharged here.** The running kernel was `6.8.0-1052-aws` while `/boot/vmlinuz` pointed at 1061 under `GRUB_FORCE_PARTUUID` initrdless boot (§S71.4, carried unchanged by §S72.G). It booted clean; `systemctl --failed` → 0. It had been carried precisely because nobody wanted to reboot to find out.

**`.env` survived** — `ZERODHA_ACCESS_TOKEN` 1, `DHAN_API_TOKEN` 1, `<` count **0**. No repeat of 2026-08-12, when a full-disk `sed -i` wrote `<real-token>` into line 24 and the unquoted `<` broke every subsequent `.env` source.

**The feed needed a human.** It was `inactive (dead)`, not `failed`, so §S69's `reset-failed` canon did not apply. `merdian-wsfeed-start.timer` is `Persistent=false`, so a start missed while the host was wedged never replayed.

## 4. Why nothing warned anyone

The volume went from 4.9 GB (2026-09-06) to 100% (2026-09-22) — **sixteen days, ~150 MB/day, measurable throughout** — and produced no signal until both access paths failed.

Nothing polls disk headroom. `eod_health_check.py` asserts on data freshness and continuity, not on the host it runs on. **TD-S69-NEW-2's *Proper fix* row already named "(d) disk headroom on the box"** and that clause was never built. This is §6.11's pg_cron blind spot at a second surface: a condition recorded continuously and read by nothing.

**And the item that predicted this had been closed.** TD-S69-NEW-1 was resolved at S71 on §S71.4's measurement of ~17 MB/day ≈ 100 days headroom — **correct for its regime**, invalidated by a consumer installed 2026-09-06, the same day §S73.E measured free space *rising*. **A resolved item has no watcher.** When its premise expired, nothing fired. Discipline does not reopen a closed item; only a live check does.

## 5. Corrections this incident forced

Four claims were recorded and then refuted by measurement. They are listed because the first version of this record contained all four.

| Claim | Corrected to |
|---|---|
| Outage began 09:42 IST | **~09:28** — the console stamp is journald noticing, not the disk filling |
| Feed down from its 03:40 UTC timer, up to 66 min | Timer fired; feed delivered 09:11–09:27; **≤48 min**, interior unobservable |
| `~/.local` + `~/.claude` + `~/.cache` ≈ 1.0 GB, all Claude Code | **738 MB** is Claude Code; 236 MB is pip site-packages and 57 MB pip cache |
| TD-S69-NEW-1 open at P0 since 2026-08-12 | The entry says **both** — heading `RESOLVED S71`, Status row `OPEN — P0` — unreconciled since S71 (**TD-S80-NEW-19**) |

The last one caused two readers to reach opposite conclusions from the same file on the same day, and propagated into three documents before it was caught.

## 6. What is still open

| # | Item | Filed |
|---|---|---|
| 1 | **~1.76 GB of the 2.5 GB growth is unattributed.** 24 GB at the measured rate is ~5 months. `du` on `/var/lib`, `/var/log`, both repo trees; `lsof +L1` **before** the next restart, not after. | TD-S80-NEW-15 |
| 2 | **No disk guard.** Daily check firing the existing `wsfeed_alert.sh` Telegram path past 80%. **Build this first.** | TD-S80-NEW-18 (S1) |
| 3 | `/etc/logrotate.d/meridian` now in `docs/registers/`; **twenty systemd units and three timers still are not** | TD-S80-NEW-16, §S74.B |
| 4 | `Persistent=true` on the wsfeed start timer — decision owed, with the out-of-hours case | TD-S80-NEW-17 |
| 5 | Instance type, with a measurement — MALPHA is t3.medium on 30 GiB for one `grep` and one `ssh` a day | Topology §S80.3 |
| 6 | Whether this is the second or third failure of its class — **not settled**; 2026-05-14's 62 GB was Supabase, a different resource | D.37.10 |

## 7. Cross-references

Deployment Topology **§S80** (full account), §S69 (the 2026-08-12 predecessor), §S71.1 (the MALPHA SSH path), §S71.4 / §S73.E (the superseded headroom readings), §S72.B (the timer property), §6.11 (the pg_cron blind spot this repeats) · Assumption Register **§D.37** (10 rows) and **§D.29.5** (the S69-era assumption whose fix clause this incident un-refuted) · `tech_debt.md` TD-S69-NEW-1 (CLOSED), TD-S73-NEW-1 (CLOSED), TD-S80-NEW-15..19 · System Map §S80 (the database half of this session, which did not contribute) · `docs/registers/logrotate_meridian.conf` (the config, now in the repo) · `docs/runbooks/runbook_recover_disk_full_lockout.md` (§3 as a procedure — this file is the record of one event, that one is what to do during the next) · CASE-2026-05-14-breadth-cascade-token-and-bloat.md (the shape this follows).

**The S80 ingest change did not contribute.** `EXPIRY_DEPTH` shipped at depth 1 with the extra pass unreachable; `grep -c "S80 extra expiries"` on `cron.log` returns **0** for the whole day; and the growth predates the patch by two weeks.
