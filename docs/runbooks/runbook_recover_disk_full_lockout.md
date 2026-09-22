# Runbook — recover from a root-volume-full access lockout (EC2)

| Field | Value |
|---|---|
| Established | Session 80, 2026-09-22 |
| Applies to | `i-0878c118835386ec2` (meridian-server, eu-north-1b) and any MERDIAN EC2 host |
| Source | First execution, 2026-09-22. See `CASE-2026-09-22-disk-full-access-lockout.md` for the event record and the measured timeline. |
| Executed end-to-end | **Yes, once** — 2026-09-22, ~09:28 → 10:17 IST. |

---

## The property that makes this different from every other runbook

**Every documented access path to this host requires the root volume to be writable.**

| Path | Fails as | Why |
|---|---|---|
| SSM Session Manager | `TargetNotConnected` | `amazon-ssm-agent` is a **snap on the root volume** |
| EC2 Instance Connect | `Error establishing SSH connection` | must **write** an ephemeral public key to the host |
| Run Command | unavailable | same agent |

This is one property, not three coincident failures. **Do not spend time cycling between them** — if one fails this way, all three will.

**`describe-instance-status` reads `running / ok / ok` throughout.** Instance health and access health are independent. The green check is the first thing anyone consults and it says nothing about whether you can get in.

---

## Symptoms

- SSM returns `TargetNotConnected`; Instance Connect returns `Error establishing SSH connection`
- Console `Get system log` last entry is `systemd-journald … No space left on device`
- Writers stop: no new rows in `market_spot_snapshots`, `breadth_intraday_history`
- Instance status checks stay green

**The console timestamp is not the onset.** journald records when *journald* noticed, and journald is itself a casualty. On 2026-09-22 the console stamp was 09:42:21 IST and the true onset, measured from the last database write, was **~09:28** — fourteen minutes earlier. Take the onset from the data, not the log.

---

## Procedure

### 0. Try MALPHA's key-auth SSH first

`ssh` from MALPHA using the key pair from the 2026-04-15 token-sync work (Topology §S71.1). **It survives this failure precisely because it needs no write** — key auth reads an already-present `authorized_keys`.

It is contrary to the SSM-only access model the Topology §1 records, and on 2026-09-22 it **was not reachable when it was needed**, which is why a stop/start was taken instead. It remains the correct first attempt: if it works, you get a shell without a state change, and steps 3–4 become unnecessary.

### 1. Snapshot before anything else

Take an EBS snapshot of the root volume and **wait for it to complete** before any restart. This is the rollback for step 4 and there is no other one.

2026-09-22: `snap-0e111e3c1d5cd1f93`, tagged `pre-resize 2026-09-22`.

### 2. Grow the volume online

Modify the volume in the EC2 console or via CLI. No instance state change and no downtime for this step. 2026-09-22: **8 GiB gp2 → 30 GiB gp3**.

Size it for the measured growth rate, not for the current shortfall. At ~150 MB/day, 24 GB of headroom is ~5 months — which is a delay, not a fix, until the consumer is identified (TD-S80-NEW-15).

### 3. Verify the public IP is a true Elastic IP — BEFORE touching instance state

```
aws ec2 describe-addresses --filters "Name=instance-id,Values=<instance-id>"
```

2026-09-22: `13.63.27.85` / `eipalloc-032ba083824b3ae47`. **Dhan and ICICI both whitelist this address.** An auto-assigned public IP is lost on stop and both vendor connections break on restart — a second incident on top of the first, discovered only when the feed fails to authenticate.

**If this returns nothing, stop.** Allocate and associate an Elastic IP before proceeding, or the stop/start will cost more than the lockout.

### 4. Stop, then start

Not reboot — the instance must be stopped and started for the resize to be picked up cleanly and for the agent to re-register.

**`Stopping` hangs for several minutes on a full disk.** This is expected. Do not force-stop unless it exceeds ~10 minutes.

Wait for `Running` and 3/3 status checks.

### 5. Confirm the filesystem grew

cloud-init runs `growpart` and `resize2fs` unaided on boot — no manual intervention was needed in 2026-09-22. Verify:

```
df -h /
```

2026-09-22 post-boot: 29 G total, 5.6 G used, 24 G free.

### 6. Check `.env` survived

```
grep -c ZERODHA_ACCESS_TOKEN ~/meridian-engine/.env
grep -c DHAN_API_TOKEN ~/meridian-engine/.env
grep -c '<' ~/meridian-engine/.env
```

Expect `1`, `1`, **`0`**. These three counts are safe under Rule 19 because they print no values.

The `<` count is the one that matters. On 2026-08-12 a full-disk `sed -i` wrote a literal `<real-token>` into line 24 and the unquoted `<` broke every subsequent `.env` source. A truncated write during a disk-full event is the exact condition that produces this.

Note separately that line 21 (`BREEZE_API_SECRET`) contains a literal `$4` that detonates under `set -u` — bracket any `.env` source with `set +u`.

### 7. Start the feed by hand

**The feed does not come back on its own.** After a lockout it is `inactive (dead)`, **not** `failed`, so §S69's `systemctl reset-failed` canon does not apply — there is nothing in a failed state to reset. And `merdian-wsfeed-start.timer` is `Persistent=false`, so a start missed while the host was wedged is never replayed.

```
systemctl status merdian-wsfeed.service
systemctl start merdian-wsfeed.service
```

Confirm from the data, not the unit: `breadth_intraday_history.coverage_pct` should return to `100.0`. On 2026-09-22 writers resumed at 10:09 IST while the feed was still dark at `coverage_pct = 0.0`, and only reached 100.0 at 10:17 after a manual start. **A running writer is not a running feed.**

### 8. Confirm nothing else is in a failed state

```
systemctl --failed
```

Expect `0 loaded units listed`. 2026-09-22 returned clean, which also discharged the kernel risk carried since S71 — the running kernel was `6.8.0-1052-aws` against a `/boot/vmlinuz` pointing at 1061 under `GRUB_FORCE_PARTUUID` initrdless boot (§S71.4, carried unchanged by §S72.G). It had been carried for four sessions precisely because nobody wanted to reboot to find out.

---

## After recovery — do these in the same session

1. **Find what filled it, before the next restart.** `lsof +L1` reports deleted-but-held files and **its output is lost on restart**, so run it now, not later. Then `du` on `/var/lib`, `/var/log` and both repo trees. 2026-09-22 left **~1.76 GB of 2.5 GB unattributed** (TD-S80-NEW-15).
2. **Record the data gaps.** Identify which relations can be backfilled and which cannot. `index_futures_snapshots` captures a live LTP with no historical equivalent — its gap is permanent; `basis_context_snapshots` carries it.
3. **Do not bundle an instance-type change with the recovery.** A failed boot should have one variable, not two. 2026-09-22 deliberately left t3.small → t3.medium for a separate decision (Topology §S80.3).

---

## What this runbook does not cover

- **Prevention.** Nothing polls disk headroom. `eod_health_check.py` asserts on data freshness and continuity, not on the host it runs on. The 2026-09-22 condition was measurable for sixteen days and read by nothing. The guard is **TD-S80-NEW-18**, filed S1 and not yet built.
- **A host with no Elastic IP.** Step 3 stops the procedure rather than working around it.
- **Recovery without MALPHA and without console access.** If step 0 fails and the AWS console is also unavailable, this runbook has no path.

---

## Related

- `CASE-2026-09-22-disk-full-access-lockout.md` — the event record, the measured timeline, and the four claims this incident refuted
- `MERDIAN_Deployment_Topology.md` **§S80** (full account) · **§S69** (the 2026-08-12 predecessor) · **§S71.1** (the MALPHA SSH path) · **§S71.4 / §S73.E** (the superseded headroom readings) · **§S72.B** (the timer property)
- `MERDIAN_Assumption_Register.md` **§D.37** (10 rows) · **§D.29.5** (superseded in part by this incident)
- `tech_debt.md` — TD-S80-NEW-15 (unattributed growth), TD-S80-NEW-16 (units outside git), TD-S80-NEW-17 (`Persistent=true` decision owed), TD-S80-NEW-18 (the disk guard)
- `runbook_disaster_rebuild.md` — for a host that cannot be recovered at all
- `runbook_emergency_stop.md` · `runbook_recover_dhan_401.md` · `runbook_resolve_hash_mismatch.md`
- `docs/registers/logrotate_meridian.conf` — the widened rotation scope, closing TD-S73-NEW-1

---

## Update obligation

This runbook has been executed end-to-end exactly once, on the event that produced it. **The next execution is also a documentation event** — every gap or correction encountered must be back-filled here in the same session.
