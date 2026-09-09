# S75 — Capture (2026-09-08 → 2026-09-09)

| Field | Value |
|---|---|
| Document | `docs/session_notes/capture_s75.md` |
| Type | **Session capture.** Written so the next session inherits the findings without re-deriving them. Not a doc-close: no register has been spliced from it. |
| HEAD at open | `83818e6` |
| Commits | `a9f102e` (data inventory + flip audit A–B), `0db92e6` (flip audit C), `8a37dbc` (flip audit D), `b2dfd25` (iv availability). |
| Session shape | Measurement only. Four research artefacts plus one probe script. **No production code changed, nothing scheduled, nothing disabled.** |
| Registers touched | **None.** |

---

## 0. TL;DR

Four measurement documents written to `docs/research/`. The substantive finding is that
**`gamma_metrics` is a 90-day rolling window, trimmed by a pg_cron job that calls a
database function with no caller anywhere in the repo** — so every AWS-host scheduling
surface reads clean while rows disappear daily.

The mechanism is **confirmed**, not hypothesised: the operator read `cron.job` and
`pg_proc.prosrc` directly in the Supabase SQL editor. Three further findings fell out of
that same read, all new, one of them a live defect.

---

## 1. `gamma_metrics` retention — **CONFIRMED MECHANISM**

### The job

```
pg_cron jobid 19, active, schedule "30 12 * * *"      -- 12:30 UTC daily
command:  select public.cleanup_gamma_engine_data();
```

### What the function deletes

From `pg_proc.prosrc`, four statements across three tables:

| table | rule |
|---|---|
| `option_chain_snapshots` | `created_at < now() - interval '90 days'` — hard delete |
| `option_chain_snapshots` | between 90 days and 14 days ago, deletes **every row except** `extract(hour from created_at)=10 AND extract(minute from created_at)=0` |
| `raw_ingest_log` | `ts < now() - interval '14 days'` |
| `gamma_metrics` | `created_at < now() - interval '90 days'` |

### The predicate is `created_at`, not `ts` — and they diverge

This is the part a reader will get wrong if they reason from `ts`, which is the column
every research query in this session used:

```
GET /gamma_metrics?select=ts,created_at,symbol&order=ts.asc&limit=4
  ts 2026-06-10T10:55:05.214937Z | created_at 2026-06-11T04:01:34.107443Z | SENSEX
  ts 2026-06-11T04:11:10.184867Z | created_at 2026-06-11T04:12:22.886648Z | SENSEX
  ts 2026-06-12T04:21:15.312224Z | created_at 2026-06-12T04:55:11.987994Z | SENSEX
```

The oldest row's `created_at` is **a full day later than its `ts`**. Rows are trimmed on
when they were written, not on the cycle they describe, so the visible `ts` boundary lags
the actual cut and is not a clean 90 days.

### The three-point age series, now fully explained

| when | `min(ts)` | rows on 2026-06-09 | total | oldest-row age by `ts` |
|---|---|---:|---:|---:|
| 2026-09-08 ~07:00 UTC (flip audit) | `2026-06-09T10:55:05.326819Z` | 1 | 9,746 | 91 d |
| 2026-09-08 ~17:40 UTC (iv sweep) | `2026-06-10T10:55:05.214937Z` | **0** | 9,807 | 90 d |
| 2026-09-09 00:04 UTC (probe run 1) | `2026-06-10T10:55:05.214937Z` | 0 | 9,807 | **91 d** |

The 12:30 UTC schedule sits exactly between the first two measurements. The 09-08 run cut
`created_at < 2026-06-10T12:30`, which removed the 2026-06-09 row and spared the
2026-06-10 row because that row's `created_at` is `2026-06-11T04:01` — after the cutoff.
The 00:04 UTC reading on 09-09 is unchanged because the job had not yet run that day.

I had recorded the 91→90→91 series as evidence *against* a daily 90-day trim. It is not:
it is exactly what a `created_at`-keyed 90-day trim at 12:30 UTC produces when read
through `ts`.

### A falsifiable prediction for the next run

At 12:30 UTC on 2026-09-09 the cutoff becomes `created_at < 2026-06-11T12:30`. The
current oldest row (`created_at 2026-06-11T04:01:34`) falls inside that, so `min(ts)`
should advance to `2026-06-11T04:11:10`. If it does not, the rule has changed.

---

## 2. The four AWS liveness surfaces — all clean, and that is the point

These stay recorded because they are **why the answer was database-side**. A future
session that searches the host and finds nothing should not conclude nothing deletes.

Searched with `/usr/bin/grep` throughout. **`grep` is a shell function in this
environment and filters recursive results** — under it a repo-wide search returned 49
files where the binary returned 81. Any recursive grep in a future session must use the
binary.

### Nothing in the repo deletes from `gamma_metrics`

Every `.py` and `.sh` in `meridian-engine` searched for `.delete(`, `DELETE FROM`,
`TRUNCATE`, `requests.delete`, `session.delete`. Every match resolves elsewhere:

| match | actual target |
|---|---|
| `build_hist_pattern_signals_5m.py:165` | `hist_pattern_signals` |
| `replay/replay_runner_for_date.py:107` | the nine `*_replay` tables — the list contains **`gamma_metrics_replay`**, a different table |
| `reload_dhan_scripmaster_from_csv.py:200` | `dhan_scrip_map` |
| `generate_pine_overlay*.py` | `box.delete` / `label.delete` — Pine drawing objects, not rows |
| `compute_volatility_metrics_local.py:358`, `scripts/eod_health_check.py:457`, `patch_s71_vix_source_logging.py:168`, `ws_feed_zerodha.py:619` | log strings containing "TRUNCATED", and a commented-out `-- DELETE FROM market_ticks` |

`archive_option_chain_history.py` reads `option_chain_snapshots` and inserts into
`historical_option_chain_snapshots` with **no delete step at all**.

### Nothing scheduled on the AWS host deletes it

| surface | result |
|---|---|
| `crontab -l` | 37 entries, 25 distinct scripts. Matching `delet\|cleanup\|archive\|prune\|purge\|retention\|gamma`: **zero** |
| `systemctl list-timers --all` | only `merdian-wsfeed-start.timer` and `merdian-wsfeed-stop.timer` |
| `/etc/systemd/system/*.service` ExecStart | `ws_feed_zerodha.py`, `wsfeed_alert.sh`, `systemctl stop merdian-wsfeed`, `oauth2-proxy`, OS services |
| orchestrator child list (`run_merdian_shadow_runner_aws.py` L181–254) | nine compute scripts, **zero** delete constructs |

Local Windows Task Scheduler and MALPHA were not searched and cannot be from this host.

---

## 3. `cleanup_gamma_engine_data` — **RESOLVED**

`POST /rpc/cleanup_gamma_engine_data` is published by PostgREST and has **zero callers in
the repo** (`/usr/bin/grep -rn` across all `.py`, `.sh`, `.sql`, docs). That is not an
orphan — it is invoked by pg_cron jobid 19, inside the database, where no filesystem
search can see it.

**It was not called from this session.** It deletes; the mandate was read-only. Its body
was read via `pg_proc.prosrc` in the Supabase SQL editor, which is the correct way to
inspect it.

The `cron` schema is not reachable through PostgREST — `job`, `job_run_details`,
`cron_job`, `cron.job` all return `PGRST205`. **Anything about pg_cron requires the SQL
editor.** That is the standing constraint, not a one-off.

---

## 4. Three further findings from the same read — all new

### 4.1 The retained daily `option_chain_snapshots` row is not the settled close

Beyond 14 days the function keeps exactly one snapshot per day, selected by
`extract(hour from created_at)=10 AND extract(minute from created_at)=0` — **10:00 UTC,
which is 15:30 IST.**

Corroborated in the data. The oldest surviving row sits precisely on that slot:

```
GET /option_chain_snapshots?select=ts,created_at&order=ts.asc&limit=3
  ts 2026-08-24T10:00:05.366368Z | created_at 2026-08-24T10:00:05.846824Z
```

That also explains the table's apparent 2026-08-24 lower bound recorded in
`data_inventory_2026-09-08.md`: it is the 14-day thinning boundary, not an ingest start.

**Why it matters:** ADR-022 established that the settled close is a Closing Auction
Session equilibrium price published after continuous trading ends, so a 15:30 IST
snapshot predates it. Every chain older than 14 days is therefore preserved at a
pre-settlement instant, and anything computing a daily close, settlement, or EOD
positioning from that retained row is reading an intraday snapshot.

**One number to check before this is written into a register.** The operator's note gives
the settled close as arriving 16:20 IST. `CLAUDE.md`'s ADR-022 summary puts the index's
settled level at ~15:35–15:40 IST with post-close 15:50–16:00, and S70 located the
settled value in the 15:29 IST bar. The finding holds under every one of those readings —
15:30 IST precedes them all — but the specific 16:20 figure should be reconciled against
ADR-022 itself rather than propagated from here.

### 4.2 pg_cron jobid 30 has a malformed header — live defect

```
jobid 30, active, schedule "38 3 * * 1-5"
  jsonb_build_object('Content-Type','application/json','<secret>')
```

`jsonb_build_object` takes alternating key/value arguments. Three arguments means the
secret is passed as a **key with no value**. Every other job in the list uses the correct
`'x-cron-secret','<secret>'` form. Whatever endpoint jobid 30 calls is being invoked
without an authenticating header, on a weekday 03:38 UTC schedule, and has been.

Not investigated further this session and **not changed**.

### 4.3 The cron secret is stored in plaintext in ~20 job commands

`cron.job.command` holds the shared secret in cleartext in roughly twenty rows. Any role
that can read `cron.job` can read it. **The value is deliberately not reproduced in this
file, in any commit message, or in any research document** — per Rule 19, it is referred
to only as `<secret>`.

Recorded as an exposure, not acted on.

---

## 5. The tail probe is a watchdog, not an investigation

`docs/research/gamma_metrics_tail_probe.py` was written before the mechanism was known.
Its purpose is now different: **it detects the retention rule changing.**

It records `min(ts)`, `max(ts)`, total rows, per-day counts for the first 10 days, and the
oldest row's age, appending a dated block to
`docs/research/gamma_metrics_tail_<YYYY-MM-DD>.md`. Read-only, no arguments, exits
non-zero without writing if any probe fails to resolve.

```bash
python3 /home/ssm-user/meridian-cc/docs/research/gamma_metrics_tail_probe.py
```

**Not scheduled, deliberately.** Run it when the rule is in question — after a Supabase
migration, or when a document's `gamma_metrics` row counts fail to reproduce. Run 1 is
recorded in `docs/research/gamma_metrics_tail_2026-09-09.md`; §1's prediction for the
12:30 UTC run on 09-09 is the first thing it can check.

Read through `ts`, the oldest-row age oscillates between roughly 90 and 91 days under the
current rule — dropping when the 12:30 UTC job runs, climbing again at midnight. A
sustained climb past that band, or a total row count that stops growing on a trading day,
is the signal worth acting on. The script's docstring and `docs/research/README.md` both
name jobid 19 and the `created_at` predicate.

---

## 6. Artefacts produced

| file | what it establishes |
|---|---|
| `docs/research/data_inventory_2026-09-08.md` | 222 relations; per-strike GEX COMPUTABLE NOW on 299/356 NIFTY and 299/355 SENSEX trading days; COMPUTABLE AFTER DERIVATION is **zero** every month because iv and gamma are never separated |
| `docs/research/flip_audit_2026-09-08.md` | `flip_level` construction, stability, consumers, price behaviour. The **value** gates nothing; its **presence** gates `trade_allowed` on 76.7% of NIFTY and 64.4% of SENSEX cycles via `regime` |
| `docs/research/iv_availability_2026-09-08.md` | exact column lists; the 21 VIX-dependent columns in `volatility_snapshots` are zero across all eleven months 2025-04→2026-02, first non-null `2026-03-09T08:49:45` |
| `docs/research/gamma_metrics_tail_probe.py`, `README.md` | the §5 watchdog and how to run it |

---

## 7. Watch items for the next session

1. **§1's prediction** — after 12:30 UTC on 2026-09-09, `min(ts)` should be
   `2026-06-11T04:11:10`. If not, the rule changed.
2. **jobid 30's malformed header (§4.2)** is a live defect on a weekday schedule. Needs an
   owner: identify the endpoint, establish whether the call is failing or silently
   succeeding unauthenticated.
3. **The 16:20 IST figure in §4.1** needs reconciling against ADR-022 directly.
4. **`gamma_metrics` and `option_chain_snapshots` are moving windows.** Any document
   quoting their month-by-month row counts is a snapshot. The flip audit's Part B table
   for 2026-06 will not reproduce — it was measured when 2026-06-09 still held a row.
5. **`gex_strike_snapshots` and `volatility_snapshots` were not checked for trimming.**
   Neither appears in jobid 19's function body, but no other job's body was read. No claim
   is made about them.
6. **`created_at` vs `ts`** — retention keys on `created_at` and the two diverge by up to a
   day. Any future retention reasoning must use `created_at`.

---

## 8. Git state at capture

```
b2dfd25  S75: iv / straddle / volatility column availability
8a37dbc  S75: flip audit part D - price behaviour at flip_level
0db92e6  S75: flip audit part C - consumers and liveness
a9f102e  S75: data inventory; flip audit parts A-B
83818e6  S74 doc-close: nine registers, CLAUDE.md split, PIN answered NO
```

Uncommitted at the time of writing: `docs/research/gamma_metrics_tail_probe.py`,
`docs/research/README.md`, `docs/research/gamma_metrics_tail_2026-09-09.md`, and this file.
