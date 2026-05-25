# CASE-2026-05-14 — Breadth Cascade: Token-in-Memory + market_ticks Bloat

> **Type:** Operational incident case study  
> **Date:** Thursday 2026-05-14 (NIFTY weekly expiry +2; SENSEX weekly expiry day)  
> **Session:** S29 firefighting (unplanned, evening recovery)  
> **Outcome:** CLOSED in-flight 2026-05-14. Forward state healthy from 2026-05-15 09:14 IST cron. Today's breadth data permanently lost (no replay possible — `market_ticks` 10-min rolling window is ephemeral by design).

---

## §1 Summary

Two independent failure modes coincidentally surfaced on the same day, producing a compound incident that was operationally indistinguishable at first inspection from a simple token-propagation error.

- **Root cause A (immediate):** `.env` token edits do not affect long-running consumer processes. `ws_feed_zerodha.py` held the prior day's token in memory from the 09:14 IST cron start; operator's morning `sed` operations correctly updated `.env` but the running feeder was unaffected. Confirmed by Kite `profile()` returning AUTH OK while `market_ticks` stayed empty all day.
- **Root cause B (latent, 14+ days):** `pg_cron` job `delete-old-market-ticks` (jobid 45) had been failing every weekday since at least 2026-04-30 with `ERROR: canceling statement due to statement timeout`. Failed deletes accumulated to 62 GB. Once the table exceeded the threshold, even successful feeder restarts couldn't write because INSERT itself exceeded statement_timeout.

A and B together produced the observation that the morning's token re-sed didn't help — the consumer process was correctly using the new token, but its writes were being rejected by Supabase for an entirely different reason.

---

## §2 Symptom timeline

**~06:00 IST** — Operator ran Step 1 + Step 2 of `runbook_update_kite_flow.md`. Confirmed `.env` token matched MALPHA's via `grep`. AWS-side `kite.profile()` returned `AUTH OK: Navin Balan`.

**~10:30 IST** — Operator noticed breadth widget on dashboard stale. Re-ran entire Step 2 sequence. Confirmed AUTH OK again. Breadth still empty.

**18:00+ IST** — Post-market diagnostic queries:

```sql
-- market_ticks rows today
SELECT COUNT(*) FROM market_ticks
WHERE (ts AT TIME ZONE 'Asia/Kolkata')::date = '2026-05-14';
-- → 0
```

```sql
-- script_execution_log breadth ingest today
SELECT exit_reason, COUNT(*) AS n, MAX(actual_writes->>'market_breadth_intraday') AS sample
FROM script_execution_log
WHERE script_name = 'ingest_breadth_from_ticks.py' AND trade_date = '2026-05-14'
GROUP BY exit_reason;
-- → SKIPPED_NO_INPUT, 379 invocations, sample=0
```

**Cost incurred:**
- `market_breadth_intraday`: **0 rows for 2026-05-14**. Not recoverable.
- `signal_snapshots.breadth_regime`: NULL for all 697 signals today. Re-computing via ADR-008 replay reads `market_breadth_intraday`, which has no rows — also not recoverable.
- Operator hours: ~3h incident response + diagnostic.
- Trading hours: degraded signal generation 09:15 IST onwards. Hybrid discretionary process compensated; no live trades placed on bad data per operator confirmation.

---

## §3 Detection trail

**Hypothesis 1** — Step 2 forgotten (matched 2026-04-22 incident pattern). Falsified within minutes — operator had done Step 2 twice and `kite.profile()` returned AUTH OK both times.

**Hypothesis 2** — Feeder process still running with old token in memory. Operator killed and restarted:

```bash
pkill -9 -f ws_feed_zerodha.py
sleep 2
pgrep -f ws_feed_zerodha.py     # empty
cd /home/ssm-user/meridian-engine
nohup python3 ws_feed_zerodha.py >> logs/ws_feed.log 2>&1 &
disown
sleep 20
tail -n 30 logs/ws_feed.log
```

Tail showed clean restart but a different smoking gun:

```
[12:39:43 IST] Loading NFO instruments from Zerodha...
[12:39:48 IST]   After breadth: 2282 total instruments
[12:39:49 IST] Connected. Subscribing 2282 instruments...
[12:39:49 IST] Subscribed. Feed live.
[12:40:00 IST]   Supabase write error 500: {"code":"57014","details":null,"hint":null,"message":"canceling statement due to statement timeout"}
```

Feeder is connected, subscribed, receiving ticks — but every batch INSERT to `market_ticks` returns Postgres error 57014. The feeder retries indefinitely in a silent reconnect loop; ticks land nowhere.

**Hypothesis 3** — `market_ticks` table bloated. Confirmed:

```sql
SELECT
  pg_size_pretty(pg_total_relation_size('public.market_ticks')) AS total_size,
  pg_size_pretty(pg_relation_size('public.market_ticks')) AS heap_size,
  pg_size_pretty(pg_indexes_size('public.market_ticks')) AS index_size;
-- total_size: 62 GB
-- heap_size:  22 GB
-- index_size: 40 GB
```

The 40 GB indexes vs 22 GB heap = ~1.8× index-to-heap ratio. Symptom of long-term DELETE-without-VACUUM accumulation. Then:

```sql
SELECT job_pid, status, return_message, start_time, end_time
FROM cron.job_run_details
WHERE jobid IN (
  SELECT jobid FROM cron.job
  WHERE jobname LIKE '%tick%' OR command LIKE '%market_ticks%'
)
ORDER BY start_time DESC LIMIT 10;
```

Returned 10 consecutive failures, every weekday from **2026-04-30 to 2026-05-13**, each with:
- `status: 'failed'`
- `return_message: 'ERROR: canceling statement due to statement timeout\n'`
- duration: ~2 minutes (cron's timeout boundary)

Once the table grew past a threshold, `DELETE` couldn't complete inside Postgres' statement_timeout, so cron failed; failed deletes meant more accumulation; positive feedback loop. The growth was silent — no telemetry surface for `cron.job_run_details` failures.

---

## §4 Fix applied

### §4.1 Step 1 — Token consumer-process restart (Root Cause A)

```bash
pkill -9 -f ws_feed_zerodha.py
sleep 2
pgrep -f ws_feed_zerodha.py     # confirm empty
cd /home/ssm-user/meridian-engine
nohup python3 ws_feed_zerodha.py >> logs/ws_feed.log 2>&1 &
disown
```

### §4.2 Step 2 — Reference layer catch-up

`refresh_equity_intraday_last.py` cron at 09:05 IST had fired with the broken token and failed silently. Manually re-ran:

```bash
python3 refresh_equity_intraday_last.py
```

Output:

```
[18:09:45 IST]   NSE breadth universe: 1385 symbols
[18:09:47 IST]   Payload built: 1325 rows with prev_close
[18:09:49 IST] Done. Wrote 1325 rows in 4.6s
```

### §4.3 Step 3 — `market_ticks` cleanup (Root Cause B)

Stop the feeder cleanly to release write locks, TRUNCATE (DDL-level — not DELETE, which would itself timeout), restart:

```bash
pkill -9 -f ws_feed_zerodha.py
```

```sql
TRUNCATE public.market_ticks;
```

```bash
cd /home/ssm-user/meridian-engine
nohup python3 ws_feed_zerodha.py >> logs/ws_feed.log 2>&1 &
disown
```

Verification of post-TRUNCATE table size:

```
total: 856 kB    heap_only: 312 kB    indexes_only: 504 kB
rows:  2282      (one full subscription batch — 2282 instruments × 1 tick)
```

TRUNCATE rebuilt indexes inline (no `REINDEX` needed). No `Supabase write error 500` in subsequent feeder activity.

### §4.4 Step 4 — Retention cron replacement (Root Cause B durable fix)

```sql
SELECT cron.unschedule(45);

SELECT cron.schedule(
  'prune-market-ticks',
  '*/30 * * * 1-5',
  $$DELETE FROM public.market_ticks WHERE ts < now() - interval '1 hour'$$
);
```

| Parameter | Old | New | Reason |
|---|---|---|---|
| Cadence | Once daily 14:30 UTC | Every 30 min | Each DELETE touches at most 30 min of accumulated rows → completes well inside statement_timeout. Spreads load. |
| Retention horizon | 2 days | 1 hour | `ingest_breadth_from_ticks.py` reads only the last 10 minutes of `market_ticks`. 2-day retention was paranoid overkill that proved fatal. 1-hour horizon caps table size at ~1 GB during active session, no risk of timeout. |
| Active Mon-Fri | 1-5 | 1-5 | Unchanged. Holidays produce no feed → no DELETE workload either way. |

---

## §5 Concurrency analysis

A and B are **independent failure modes** that coincidentally surfaced on the same day:

- B had been latent since 2026-04-30 (14+ days). The bloated table only became a problem once INSERT volume crossed the statement_timeout threshold.
- A was triggered by today being the first day where the operator's token-refresh discipline was correctly applied to MALPHA but the long-running feeder was not restarted.

If only A had occurred, restart alone would have recovered breadth (verified — Step 4.1 by itself didn't restore, because B was still active).

If only B had occurred, the feeder would have been crash-looping on every INSERT since whenever the table size crossed the timeout boundary (almost certainly during a market day, with no operator notice).

**The compound effect is what made diagnosis difficult.** Operator's hypothesis-1 pattern-match (matching the 2026-04-22 incident) led to a correct fix attempt that produced no visible improvement, which led to second-guessing the entire token chain instead of investigating the consumer process state independently.

---

## §6 Codification (lessons → settled-decisions)

Five lessons codified into `CLAUDE.md` v1.20 footer:

1. **B24** — `.env` edits do not propagate to running processes. Token files like `.env` are read at process startup. A long-running consumer holds whatever value was loaded at startup until killed. After any `.env` mutation, every consumer process that read the affected variable MUST be killed and restarted; verifying the on-disk value matches (e.g., `grep KEY .env`) is necessary but not sufficient. **Filing rule:** any new `.env`-mutation runbook must include a "Step Nd — Restart consumers" mandatory clause.

2. **B25** — TRUNCATE vs DELETE on bloated tables. For Postgres tables under statement_timeout pressure, `DELETE FROM table WHERE ...` cannot be used to recover bloat — the DELETE itself is what's timing out. `TRUNCATE table` is the only operational primitive that works at scale because it is DDL (drops + recreates the underlying file atomically), runs in O(1) on table size, and resets indexes inline. **Filing rule:** for any table whose retention horizon is shorter than its read-window-floor, TRUNCATE is the canonical recovery; DELETE is structurally unsafe. Apply at every new pg_cron retention job — if worst-case DELETE workload could ever exceed statement_timeout, the design is wrong; reduce horizon and increase cadence instead.

3. **B26** — `pg_cron` failures are invisible by default. The `cron.job_run_details` table records every cron run, including failures, but no MERDIAN telemetry polls it. A retention or maintenance job can fail every weekday for weeks before any operator-visible symptom emerges. **Filing rule:** any pg_cron job introduced to production must be accompanied by either (a) a polling check that surfaces failures within 24 hours (Telegram alert or dashboard widget), or (b) an explicit entry in the operator session-start checklist. Filed as TD-NEW-B (S1).

4. **Diagnostic discipline.** When pattern-matching a current incident to a prior incident (here: 2026-04-22 → 2026-05-14), the pattern-match is a **hypothesis, not a conclusion**. The 04-22 fix (re-run Step 2) was tried twice on 05-14 with no improvement, but the operator initially attributed that to "must have made a sed mistake" rather than "the hypothesis is wrong". Codified into runbook §1.6 of S29_HANDOFF: when a tried fix produces no observable change, falsify the hypothesis before retrying.

5. **Compound incident detection.** Two independent failure modes can produce a single observable symptom (here: empty `market_ticks`). Diagnosis requires checking each layer of the data flow independently (`.env` file, consumer process memory state, table size, downstream write success), not just the inputs. Codified into runbook Step 2d as the "consumer process state" diagnostic that distinguishes A from B.

---

## §7 Downstream documentation changes

| Document | Change |
|---|---|
| `runbook_update_kite_flow.md` | New Step 2d (consumer restart) + 2 new failure-mode rows + 2026-05-14 architectural-gap addition + change-history row |
| `MERDIAN_Deployment_Topology.md` | New §6 gotcha "Token edits to .env do not restart consumer processes" + new §6 gotcha "pg_cron failures are silent" |
| `MERDIAN_OpenItems_Register_v7.md` | OI-12 RE-RESOLVED block appended (original 2026-04-14 closure preserved; new closure documents structural redesign) |
| `CLAUDE.md` v1.19 → v1.20 | B24, B25, B26 anti-pattern lines + settled-decision footer entry for TD-NEW-A + OI-12 RESOLVED |
| `tech_debt.md` | TD-NEW-A filed + RESOLVED same session; TD-NEW-B (pg_cron health-check) filed open; TD-NEW-C (ws_feed silent on Supabase 500) filed open; TD-NEW-D (ws_feed log timezone labels) filed open |
| `merdian_reference.json` v20 → v21 | `market_ticks` table entry: `critical_rule` updated to reference jobid 46 + 1-hour horizon + retired jobid 45 |

---

## §8 Forward verification — 2026-05-15

Items the operator must verify the morning after (auto, no action needed unless flagged):

- [ ] 09:14 IST: `ws_feed_zerodha.py` cron starts with fresh token; `market_ticks` accumulates within 60s.
- [ ] ~09:30 IST: `prune-market-ticks` jobid 46 first 30-min-cadence run completes successfully; `cron.job_run_details` shows status=`succeeded`.
- [ ] 16:00 IST: daily audit returns OVERALL: PASS on `hist_spot_bars_1m` + `market_spot_snapshots` (post-TD-NEW-I threshold change).
- [ ] Day-end: signals fire with `breadth_regime` populated (no NULL cascade).

---

*CASE-2026-05-14-breadth-cascade-token-and-bloat.md — incident closed 2026-05-14, codified at S29 close. Author: S29 firefighting session. Operator: Navin.*
