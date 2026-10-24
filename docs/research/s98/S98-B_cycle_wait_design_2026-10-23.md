# S98-B — the runner computes its own cycle's chain run (design note, DRAFT for the operator's yes)

> **Amendment notes (added at the S98 + S99 doc-close, Session 100, 2026-10-24; the body below is unedited).**
> 1. **D3 as built:** the timeout exits 1 with reason **`SKIPPED_NO_INPUT`**, not `STALE_INPUT` (ruling S98-E.1;
>    `STALE_INPUT` is not in `VALID_EXIT_REASONS`, §D.52.6). Read every `STALE_INPUT` below as `SKIPPED_NO_INPUT`.
> 2. **D2 as installed:** the closing cycles are a second cron line **appended after** the existing runner line (S98-E.1),
>    not an edit of it. Installed 2026-10-23 (backup `~/crontab.bak-S98B-2026-10-23`); runner lines now 13 and 69.
> 3. **§5 step 1 superseded** by the box route (ruling S99-A): commit in `~/meridian-cc`, push, `git pull --ff-only` in
>    `~/meridian-engine` and on Local, four-way blob hash. Delivered as **`2edd25f`**.
> 4. **S98-E.1's expected monitor window "03:10–10:00 UTC" was wrong;** `parse_orchestrator_window` returns 03:00–09:55
>    UTC, (180, 595, 5, {1..5}), before and after the add (ruling S99-B; §D.53.3).
> 5. **R47 verified 2026-10-23 18:05 IST:** `chk_exit_reason_valid` lists 11 members and `core/execution_log.py`
>    `VALID_EXIT_REASONS` lists the same 11 — no drift; exactly one constraint references `exit_reason`.
> 6. **Test as built:** `tests/test_runner_cycle_wait.py` T1–T9, mutants M / R / Z (8 mutant cells, 0 survivors), wired as
>    `tests/run_offline.sh` step 14 (now 14 of 15 after `3706435`).

Ruling S98-B (2026-10-23 06:27 IST): ship TD-S97-NEW-4 fix (a) **coupled** with γ on the close. Measured since then
(R41): **every γ cycle computes the previous cycle's chain run** — 76/76 rows per symbol on 2026-10-23 have
`created_at − ts` = 303–318 s. So the fix is not an age rule on run_ids; it is the runner waiting for **its own**
cycle's run. One change removes four symptoms.

| Symptom | Today | After |
|---|---|---|
| Board one γ run behind (D2-8, R6) | γ ts lags chain by 5 min, always | γ ts = the cycle's chain ts |
| First cycle reuses yesterday's run (TD-S97-NEW-4 (i)) | 08:30 cycle writes yesterday's 15:40 row (39/41 days) | 08:30 cycle waits for 08:30's chain |
| No γ on the close (R6, eval A3) | last γ = 15:20 chain; 15:40 written next morning | γ on 15:30 / 15:35 / 15:40 the same day |
| Total outage reads as success (TD-S97-NEW-4, 10-21) | reuses the last run all day, SUCCESS | no current run → exit 1, a true alarm |

Out of scope (stays open): TD-S97-NEW-4 (b), the ledger's `expected_writes={}` / `actual_writes {}` (the runner's
contract cannot fail); the `run_ingest.sh` `set -e` / unreachable `rc=$?` defect (new, found in this read).

## 1. What the code does now (read 2026-10-23 17:12 IST, tree `c3fc35c`)

- `run_merdian_shadow_runner_aws.py` `fetch_latest_run_ids()` (:89–137): per symbol, newest front-expiry row of
  `option_chain_snapshots` (`order="ts.desc,expiry_date.asc"`, limit 1), **no age guard by design** (:117–122). Missing
  symbol → omitted, the other computed (:366–372). No row at all → exit 1 `SKIPPED_NO_INPUT` (:358–364).
- `ingest_option_chain_local.py` mints `snapshot_ts` and the front `run_id` at :470–471, inserts the front leg in
  **one** `sb.insert` (:513), then the extra-expiry legs with the same `ts` and their own run_ids (:570–594).
- Cron (UTC): ingest NIFTY and SENSEX as separate concurrent lines at `0,5,…,55 03`, `*/5 04-09`, and
  **`0,5,10 10`** (15:30 / 15:35 / 15:40 IST); runner `*/5 03-09` (08:30–15:25 IST) — the **same minute** as the
  ingest it reads. Ledger 10:05 IST: γ NIFTY ran 10:05:08–:14, that cycle's NIFTY ingest finished 10:05:15.

## 2. The change

### 2.1 Runner: wait for the cycle's own run (one function replaced, one constant)

`fetch_latest_run_ids(sb)` → `fetch_cycle_run_ids(sb, now_utc)`:

1. `cycle_floor` = `now_utc` floored to the 5-minute boundary (the cron minute this cycle belongs to).
2. Per symbol, the same query as today **plus** `ts=gte.<cycle_floor>`, same ordering, limit 1.
3. Poll every `POLL_S = 5` s until every symbol has a row or `CYCLE_WAIT_S = 120` s have passed.
   The front leg is inserted in one request, so its rows appear together; ordering by `expiry_date.asc` keeps the
   front leg even after the extra legs land with the same `ts`.
4. Return the symbols found. Logged per cycle: `cycle_floor`, wait used, symbols found, symbols missing.

`main()`:
- **Some symbols found** → compute those; WARN for the missing (unchanged behaviour).
- **None found within 120 s** → **no fallback to an older run**; exit **1** with a new reason **`STALE_INPUT`**
  ("no chain run at or after <cycle_floor> for any symbol"). The monitor already alarms on a finished non-zero exit.
- Holiday gate unchanged and first.

**Why 120 s:** the measured cycle is ~132 s of compute (mean 10-21) inside 300 s; front ingest normally lands by
:15 s; 120 s leaves room for Dhan 429 retries (`attempts=6`) and still ends every cycle ~45 s before the next.

### 2.2 Cron: three closing cycles (capture path)

Add one line, matching ingest lines 47/48:
`0,5,10 10 * * 1-5 cd /home/ssm-user/meridian-engine && source <env> && python3 run_merdian_shadow_runner_aws.py >> logs/orchestrator.log 2>&1`
→ γ on the 15:30, 15:35 and **15:40** chain runs, the same day. The downstream symbol-keyed steps run three more
times after 15:30 (display only; nothing routes on them).

## 3. Effects to expect, and who reads them

- `gamma_metrics.ts` semantics unchanged (chain `ts`); rows simply arrive ~5 min earlier relative to the market.
- No more next-morning 15:40 rows; the same-day 15:40 row replaces it (upsert on `(symbol, ts)` is idempotent).
- Board CLOCKS should read `γ hh:mm` = `chain hh:mm` once the tab has re-polled (R16 is separate).
- ENH-133 history, P3b sweep, contract check, ACL: no schema or view change. P4: reads chain runs directly —
  unaffected. Monitor: runner rows land ~10–20 s later in the minute and three more per day; `LOOKBACK_MIN = 7` and the
  in-band gate need a read to confirm 15:30–15:40 cycles cannot produce an off-band false alarm (§5 item 4).

## 4. Test (offline, before deploy; out of hours under `ulimit -v 700000`)

New `tests/test_runner_cycle_wait.py` — `sb.select` mocked with time-sequenced results, `time.sleep` patched:

| # | Case | Expected | Control for |
|---|---|---|---|
| T1 | current run appears on the 3rd poll | returns it; waited 10 s | the wait works |
| T2 | only the previous cycle's run exists | after 120 s: exit 1 `STALE_INPUT`, pipeline **not** called | today's bug (would compute the old run) |
| T3 | 08:30, newest row is yesterday 15:40 | exit 1 `STALE_INPUT`, no γ written | TD-S97-NEW-4 (i) |
| T4 | NIFTY current, SENSEX none | computes NIFTY only, WARN | unchanged partial behaviour |
| T5 | `cycle_floor` at 10:04:59 / 10:05:00 / 10:05:01 | 10:00 / 10:05 / 10:05 | boundary |
| T6 | extra-expiry leg lands after the front leg, same ts | front run_id returned | the S81 ordering survives |
| M | mutant: drop the `ts=gte` filter | T2 and T3 FAIL | the test can fail for the named reason |

Wired as `run_offline.sh` step 14/14. Full suite PASS required (the S90-J "green replay/golden check").

## 5. Deploy (S90-J window, 16:30 → 07:45 IST) and rollback

1. Code on **Local**, commit, push; `git pull --ff-only` on both box trees; three-way hash equal.
2. `crontab -l > ~/crontab.bak-S98B-<date>` **then** add the one line; `crontab -l | grep -c run_merdian_shadow_runner_aws.py` = 2.
3. Nothing runs until 08:30 next trading day (Monday 2026-10-26).
4. Before deploy, read `monitor_orchestrator_health.py`'s in-band window; if it ends before 15:40, decide whether
   the three closing cycles are in-band (alarmed) or not.

**Rollback (refusing block, only if the live check fails):** `git revert <commit>` on Local → push → pull on both
trees; `crontab ~/crontab.bak-S98B-<date>`; verify `crontab -l | grep -c run_merdian_shadow_runner_aws.py` = 1.

## 6. Live PASS (Monday 2026-10-26)

| Check | PASS |
|---|---|
| `gamma_metrics` `created_at − ts` median per symbol | < 60 s (today 307 / 315 s) |
| Rows with IST `created_at` date > IST `ts` date, from 10-26 | 0 |
| γ rows at 15:30, 15:35, 15:40 IST on 10-26, created the same day | 3 per symbol |
| 08:30 ledger row | `run_ids` are 10-26 runs (not 10-23 15:40) |
| Runner exits non-zero | 0 on a healthy day; any `STALE_INPUT` read against the ingest ledger before calling it a defect |

## 7. Decisions for the operator

- D1 `CYCLE_WAIT_S` = 120 s (recommended) — or 60 s (faster cycles, more `STALE_INPUT` on a slow Dhan minute).
- D2 Closing cycles 15:30 / 15:35 / 15:40 (recommended) — or 15:40 only.
- D3 Timeout → exit 1 `STALE_INPUT`, no fallback (recommended; the 10-21 alarm) — or fall back to the previous run
  with a WARN (keeps γ flowing on a slow ingest, keeps the 10-21 blind spot).
