# Producer/consumer time-coupling audit — 2026-09-07

**Scope.** Every executable line in `docs/registers/aws_crontab.txt` and every unit in `deploy/systemd/`, their write targets, and the read windows of every consumer of those targets. Plus a separate sweep of self-reported health/quality verdict columns and whether anything reads them.

**Defect class under audit.** A scheduled job writes rows at wall-clock time `T`. A downstream script reads a hardcoded window `[A,B]`. `T` has moved outside `[A,B]`. The mismatch is silent because the consumer finds no rows rather than erroring.

**Method.** Producer times are computed from the crontab expression only. Consumer windows are established by reading source. Comments and docstrings are NOT treated as evidence — they were wrong in two of the three cases that motivated this audit. `merdian_reference.json` schema entries are NOT treated as evidence. Script liveness is established from cron and systemd, never from filename. No database was queried; no `.env` was read; nothing was modified.

**Status legend.** `BROKEN` = producer write time provably outside consumer read window. `AT-RISK` = window holds today but has no derivation binding it to the producer, so it drifts silently on the next schedule change. `OK` = window derived from, or verified against, the producer's actual time. `NO-WRITER` = consumer reads a table with no scheduled producer.

---

## Section 1 — Producer inventory

`docs/registers/aws_crontab.txt` contains 37 non-blank non-comment lines. Line 1 is the `SHELL=/bin/bash` directive, not a job. **36 executable job lines**, matching the stated count.

IST = UTC + 05:30 throughout.

### 1.1 Crontab jobs

| # | Cron expression (UTC) | Script | First → last fire (IST) |
|---|---|---|---|
| 1 | `5 3 * * 1-5` | `refresh_dhan_token.py` | 08:35 |
| 2 | `41 3 * * 1-5` | `capture_market_spot_snapshot_local.py` | 09:11 |
| 3 | `*/1 03,04,05,06,07,08,09 * * 1-5` | `capture_spot_1m_v2.py` | 08:30 → **15:29** |
| 4 | `0,5,…,55 03 * * 1-5` | `run_ingest.sh NIFTY FULL` | 08:30 → 09:25 |
| 5 | `0,5,…,55 03 * * 1-5` | `run_ingest.sh SENSEX FULL` | 08:30 → 09:25 |
| 6 | `*/5 04,05,06,07,08,09 * * 1-5` | `run_ingest.sh NIFTY FULL` | 09:30 → 15:25 |
| 7 | `*/5 04,05,06,07,08,09 * * 1-5` | `run_ingest.sh SENSEX FULL` | 09:30 → 15:25 |
| 8 | `*/5 04,05,06,07,08,09 * * 1-5` | `capture_index_futures_snapshot_local.py NIFTY` | 09:30 → 15:25 |
| 9 | `*/5 04,05,06,07,08,09 * * 1-5` | `capture_index_futures_snapshot_local.py SENSEX` | 09:30 → 15:25 |
| 10 | `*/5 03,04,…,09 * * 1-5` | `build_wcb_snapshot_local.py` | 08:30 → **15:25** |
| 11 | `*/1 03,04,…,09 * * 1-5` | `ingest_breadth_from_ticks.py` | 08:30 → 15:29 |
| 12 | `30 10 * * 1-5` | `capture_postmarket_1600.py` | 16:00 |
| 13 | `*/5 03-09 * * 1-5` | `run_merdian_shadow_runner_aws.py` | 08:30 → **15:25** |
| 14 | `*/1 * * * *` | `monitor_orchestrator_health.py` | every minute, all days |
| 15 | `*/1 * * * *` | `refresh_health_dashboard.py` | every minute, all days |
| 16 | `*/2 03-09 * * 1-5` | `enforce_orchestrator_timeout.py` | 08:30 → 15:28 |
| 17 | `4,9,…,59 03-09 * * 1-5` | `validate_compute_contracts.py` | 08:34 → 15:29 |
| 18 | `30 02 * * 1-5` | `seed_trading_calendar.py` | 08:00 |
| 19 | `35 3 * * 1-5` | `refresh_equity_intraday_last.py` | 09:05 |
| 20 | `40 10 * * 1-5` | `build_market_spot_session_markers.py` | 16:10 |
| 21 | `0 14 * * 1-5` | `ingest_participant_positioning.py` | 19:30 |
| 22 | `30 15 * * 1-5` | `ingest_participant_positioning.py` | 21:00 |
| 23 | `0 16 * * 1-5` | `compile_market_environment_local.py` | 21:30 |
| 24 | `55 3 * * 1-5` | `relate_ambient_to_open_local.py` | 09:25 |
| 25 | `15 16 * * 1-5` | `accrue_expiry_outcomes.py` | 21:45 |
| 26 | `40 10 * * 1-5` | `run_equity_eod_until_done.py` | 16:10 |
| 27 | `20 10 * * 1-5` | `detect_ict_patterns_runner.py NIFTY` | 15:50 |
| 28 | `22 10 * * 1-5` | `detect_ict_patterns_runner.py SENSEX` | 15:52 |
| 29 | `50 10 * * 1-5` | `capture_cas_close.py` | 16:20 |
| 30 | `0,5,10 10 * * 1-5` | `capture_index_futures_snapshot_local.py NIFTY` | 15:30, 15:35, 15:40 |
| 31 | `0,5,10 10 * * 1-5` | `capture_index_futures_snapshot_local.py SENSEX` | 15:30, 15:35, 15:40 |
| 32 | `0,5,10 10 * * 1-5` | `run_ingest.sh NIFTY FULL` | 15:30, 15:35, 15:40 |
| 33 | `0,5,10 10 * * 1-5` | `run_ingest.sh SENSEX FULL` | 15:30, 15:35, 15:40 |
| 34 | `0-10 10 * * 1-5` | `ingest_breadth_from_ticks.py` | 15:30 → 15:40, every minute |
| 35 | `30 01 1,15 * *` | `reload_dhan_scripmaster.py --apply` | 07:00, 1st & 15th, **any weekday** |
| 36 | `52 10 * * 1-5` | `generate_pine_overlay.py` | 16:22 |

Note on #35: day-of-week is `*`, so cron's DOM/DOW OR-semantics do not apply — it fires on the 1st and 15th regardless of weekday, including weekends when no other job runs.

### 1.2 systemd units (`deploy/systemd/`)

| Unit | Type | Schedule | Effect |
|---|---|---|---|
| `merdian-wsfeed-start.timer` | timer | `Mon-Fri 03:40 UTC` | starts `merdian-wsfeed.service` at **09:10 IST** |
| `merdian-wsfeed.service` | simple, `Restart=always` | 09:10 → 15:35 IST | runs `ws_feed_zerodha.py`; `ExecStartPre=bin/wsfeed_preflight.sh` |
| `merdian-wsfeed-stop.timer` | timer | `Mon-Fri 10:05 UTC` | triggers stop at **15:35 IST** |
| `merdian-wsfeed-stop.service` | oneshot | — | `systemctl stop merdian-wsfeed.service` |
| `merdian-wsfeed-alert.service` | oneshot | `OnFailure=` of wsfeed | runs `bin/wsfeed_alert.sh` |

This is a **second scheduling surface**. Nothing in the crontab references it, and a producer/consumer audit scoped to `crontab -l` alone would not see that the tick feed stops at 15:35 IST.

---

## Section 2 — What each producer writes

### 2.1 Capture layer

| Script | Writes | Timestamp col & basis | Internal gate that can suppress the write |
|---|---|---|---|
| `refresh_dhan_token.py` | `system_config` (PATCH, `:221-226`) | `updated_at` = the literal 4-char string `"now()"` `:218` | 90-second idempotency skip `:126`; no market/holiday gate |
| `capture_market_spot_snapshot_local.py` | `market_spot_snapshots` (INSERT, `:286`) | `ts` = `datetime.now(timezone.utc)` `:83-84,:205` — real UTC | holiday gate only `:277-279`; **no hours gate** |
| `capture_spot_1m_v2.py` | `market_spot_snapshots` `:445`; `hist_spot_bars_1m` upsert on `instrument_id,bar_ts` `:466`; `script_execution_log` | `ts` real UTC `:330`; `bar_ts` real UTC minute-truncated `:329`; `trade_date` IST date `:324` | **`MARKET_CLOSE_GUARD = dtime(15,15)` `:99`**, enforced `:345` → `OFF_HOURS`, no rows; holiday gate `:360`; filler-bar skip `:246-260` |
| `run_ingest.sh` → `ingest_option_chain_local.py` | `option_chain_snapshots` (INSERT, `:443`); `script_execution_log` | `ts` = real UTC `:82-83,:401`, one value per cycle | holiday gate `:507-512`; **no hours gate**; empty-expiry `DATA_ERROR` `:358` |
| `capture_index_futures_snapshot_local.py` | `index_futures_snapshots` (INSERT, `:436`) | `ts` = real UTC `:86-87,:345` | **none — no holiday gate, no hours gate**; runs and inserts at any hour, any day |
| `build_wcb_snapshot_local.py` | `weighted_constituent_breadth_snapshots` upsert on `index_symbol,ts` `:462-466` | `ts` **copied from the breadth row it read** `:353-357`, falling back to real UTC | none |
| `ingest_breadth_from_ticks.py` | `breadth_intraday_history` (always, `:291-300`); `market_breadth_intraday` upsert on `ts,universe_id` (**conditional**, `:251`); `script_execution_log` | `ts` real UTC `:88,:235,:292`; `trade_date` IST `:89` | no wall-clock gate; `MIN_COVERAGE_PCT = 50.0` `:46` suppresses only the `market_breadth_intraday` write `:233` |
| `capture_postmarket_1600.py` | **nothing of its own** — wrapper `:36-41` for `run_market_close_capture_once.py`, which runs `capture_market_spot_snapshot_local.py` (`:54`) and `capture_index_futures_snapshot_local.py` (`:55`) | — | **none**; the "1600" is filename convention only, not enforced in code |
| `ws_feed_zerodha.py` (systemd) | `market_ticks` (`TICKS_TABLE` `:83`, POST `:138`) | `ts` = `datetime.now(utc).astimezone(IST)` `:118-119,:428` — correct instant, IST offset; one value shared per batch, so it is *ingest* time not exchange tick time (`exchange_timestamp` is not carried, `:439-457`) | no wall-clock gate at all; start/stop is entirely external (systemd); `MIN_UNIVERSE=100` floor `:99` exits 3 `:512-518` |

---

## Section 3 — Broken and at-risk couplings

Ordered by severity. Each is stated as: producer time → consumer window → why the mismatch is silent.

### F-01 `BROKEN` — futures basis is computed against a spot feed that stopped 25 minutes earlier

- **Producer.** `capture_spot_1m_v2.py` writes `market_spot_snapshots`, but its internal `MARKET_CLOSE_GUARD = dtime(15,15)` (`capture_spot_1m_v2.py:99`, enforced `:345`) makes **15:15 IST the last write**, even though cron keeps firing it to 15:29.
- **Consumer.** `capture_index_futures_snapshot_local.py:144-152` — `fetch_latest_spot()` queries `market_spot_snapshots` with `{"order": "ts.desc", "limit": "1"}` and **no time filter of any kind. UNBOUNDED.** The returned `spot` is used to compute `basis` at `:370`.
- **Mismatch.** Crontab lines 30–31 fire this consumer at **15:30, 15:35 and 15:40 IST** (`0,5,10 10 * * 1-5`). At 15:40 the newest available spot row is from 15:15 — **25 minutes stale**.
- **Why silent.** An unbounded `order+limit 1` read can never return zero rows, so the described failure mode inverts: instead of finding nothing and erroring, it finds something and is wrong. There is no recency floor on this read. Three `index_futures_snapshots` rows per symbol per day carry a `basis` computed against a stale spot, and nothing marks them.
- Same unbounded read is also exercised at **16:00 IST** via `capture_postmarket_1600.py` → `run_market_close_capture_once.py:55`.

### F-02 `BROKEN` — WCB stops five minutes before the breadth it consumes stops being produced

- **Producer.** `ingest_breadth_from_ticks.py` writes `market_breadth_intraday` through **15:40 IST** (crontab line 34, `0-10 10 * * 1-5`).
- **Consumer.** `build_wcb_snapshot_local.py` reads `latest_market_breadth_intraday` (`:127-133`) and runs on `*/5 03-09` (line 10) — **last fire 15:25 IST**. There is no hour-10 line for WCB.
- **Mismatch.** Every breadth row written between 15:26 and 15:40 IST is never read by WCB. `weighted_constituent_breadth_snapshots` ends the session at 15:25 while its input runs 15 minutes longer.
- **Why silent.** The consumer simply isn't running; nothing asserts that WCB's last row covers breadth's last row.

### F-03 `BROKEN` — the tick producer is stopped five minutes before its consumer stops reading

- **Producer.** `ws_feed_zerodha.py` writes `market_ticks`. It is stopped by `merdian-wsfeed-stop.timer` at `10:05 UTC` = **15:35 IST**.
- **Consumer.** `ingest_breadth_from_ticks.py:90` reads `market_ticks` over a rolling `TICK_WINDOW_MINUTES = 10` (`:43`) window ending at `now`. Crontab line 34 runs it **every minute from 15:30 to 15:40 IST**.
- **Mismatch.** The runs at 15:36–15:40 read a window whose tail is empty by construction; the tick set shrinks each minute until the 15:40 run sees only 15:30–15:35.
- **Why silent.** Coverage falls below `MIN_COVERAGE_PCT = 50.0` (`:46`), which suppresses the `market_breadth_intraday` write (`:233`) — but `breadth_intraday_history` is written **unconditionally** (`:128`, `:228`), so degraded rows keep landing. The suppression is a silent skip, not an error.
- These two facts live on different scheduling surfaces: the stop time is in `deploy/systemd/merdian-wsfeed-stop.timer`, the read cadence is in the crontab. Neither file references the other.

### F-04 `BROKEN` — `equity_intraday_last` is refreshed once at 09:05 and read all day with no floor

- **Producer.** `refresh_equity_intraday_last.py`, crontab line 19, **09:05 IST, once per weekday**. It upserts in place, so the table holds exactly one generation.
- **Consumers, both unbounded.**
  - `build_wcb_snapshot_local.py:94-99` — `filters={"ticker": f"in.{...}"}`, `limit=5000`, **no `ts` or `trade_date` filter**; the value is consumed as live price at `:260`.
  - `ingest_breadth_from_ticks.py:160-162` — `.select("ticker,last_price").range(...)`, **no filter, no order, no time bound**.
- **Mismatch.** If the 09:05 job fails or is skipped, both consumers silently use the previous session's baseline — the exact shape of the S59 incident (breadth reading BULLISH on a down day off a frozen prev-close). The freshness guard added after S59 lives in `scripts/eod_health_check.py`; **it was never added to either consumer**.
- **Why silent.** Unbounded reads always return rows. Neither consumer compares the row's `ts` against anything.
- Note also a naming/semantics trap in `ingest_breadth_from_ticks.py`: the variable is `prev_closes` (`:154`) and the docstring says "prior day close" (`:11`), but the column actually selected is **`last_price`** (`:161`).

### F-05 `AT-RISK` — WCB stamps its own row with a timestamp it copied from upstream, and upserts on it

- `build_wcb_snapshot_local.py:353-357` sets `snapshot_ts` to the `ts` of the `latest_market_breadth_intraday` row it just read, falling back to `now_utc_iso()` only if that row is missing. The upsert conflict key is `(index_symbol, ts)` (`:466`).
- **Consequence.** If breadth is frozen, every subsequent WCB run resolves to the *same* conflict key and **overwrites the same row instead of appending**. A stalled upstream therefore produces a `weighted_constituent_breadth_snapshots` table that looks quiet rather than one that looks stuck, and the snapshot's own `ts` reports the upstream time, not the time the snapshot was computed. There is no column recording when WCB actually ran.

### F-06 `AT-RISK` — cron window is 14 minutes wider than the guard it feeds

- `capture_spot_1m_v2.py` runs `*/1` through **15:29 IST** (line 3) but writes nothing after **15:15 IST** because of `MARKET_CLOSE_GUARD` (`:99`). Fourteen runs per day take the `OFF_HOURS` path (`:350-356`) and write only a `script_execution_log` row.
- Not data loss — the 15:29 settled-close bar is deliberately handled by `capture_cas_close.py` at 16:20 IST. Recorded because the schedule and the guard are two independent declarations of the same boundary with nothing binding them, and because **the docstring `:36-39` and the guard comment `:341-343` both still say 15:30/15:31 while the code says 15:15**.

### F-07 `AT-RISK` — `capture_index_futures_snapshot_local.py` has no holiday gate and no hours gate

- Verified absent across `capture_once()` (`:401-440`): no `trading_calendar` check, no market-hours comparison. Every other capture script in this layer has at least the holiday gate.
- It will insert `index_futures_snapshots` rows on any day it is invoked, including a holiday, using whatever `market_spot_snapshots` row is newest — which on a holiday is the previous session's close.

### F-08 `AT-RISK` — host-local `datetime.now()` used for a date filter

- `capture_index_futures_snapshot_local.py:90-91` — `today_iso_local()` uses **naive `datetime.now()`**, i.e. host OS timezone, and feeds the scripmaster contract filter `SM_EXPIRY_DATE >= today` (`:175`).
- Same shape in `ws_feed_zerodha.py:272` — `date.today()`, naive, driving the expiry window `:299` and `:312`.
- Currently harmless because both run inside 04:00–10:10 UTC where the UTC and IST dates agree. It breaks for any invocation after 18:30 IST — which `capture_postmarket_1600.py` does not reach, but a manual or re-timed run would.

### F-09 `AT-RISK` (unverifiable from source) — token sync writes a literal `"now()"` string

- `refresh_dhan_token.py:216-220` PATCHes `system_config` with `{"config_value": ..., "updated_at": "now()", ...}`. `"now()"` is sent as a four-character JSON **string**, not a SQL function call.
- Whether Postgres accepts it depends on the declared type of `updated_at`, which cannot be settled without the DDL or the database — both out of scope here. If the column is `timestamptz`, `'now()'` is not valid input syntax (bare `'now'` is; `'now()'` is not) and the PATCH would 400.
- **The failure would be silent either way**: the request is inside `try/except Exception` (`:207`, `:231-232`) and a non-2xx only prints a warning (`:227-230`). A cross-host consumer reading `system_config` for the token would then see a stale value with no signal. Flagged for verification, not asserted.

### F-10 `NO-WRITER` — 19 `build_ict_primitives*` variants, none scheduled

- `build_ict_primitives*.py` matches **19 files**. Zero appear in `docs/registers/aws_crontab.txt`, and zero are invoked by any other Python file in the repo (the only cross-references are docstrings and self-references inside the variants themselves).
- Liveness established from cron and systemd, per instruction — not from filename. The conclusion is not "which one is live" but **none is live**: `ict_primitives` and `ict_primitive_outcomes` have no scheduled producer and are frozen at whatever the last manual backfill wrote.

### F-11 `AT-RISK` — `run_ingest.sh` cannot report its own failure

- `run_ingest.sh:4` sets `set -eo pipefail`. `rc=$?` at `:18` and the END log line at `:19` are therefore **unreachable on failure** — a non-zero exit from `ingest_option_chain_local.py` at `:17` terminates the shell first.
- A failed ingest leaves a START line and no END line, so the log distinguishes failure from success only by absence. Four crontab lines (4, 5, 6, 7 and 32, 33) route through this wrapper.

### F-12 `AT-RISK` — universe membership requires two independent boolean columns

- `ws_feed_zerodha.py:366-372` filters `breadth_universe_members` on **both** `is_active=eq.true` **and** `active=eq.true`. A ticker with either column null or false silently leaves the universe.
- The read is otherwise **unbounded** — no date filter — so a stale membership table is consumed without complaint. The only backstop is `MIN_UNIVERSE=100` (`:99`), which catches a collapse to near-zero but not a partial erosion.

### F-13 `BROKEN` — `market_spot_session_markers.close_1530` is unreachable for two independent reasons, and `capture_quality` can never read `COMPLETE`

This is the case that motivated the audit, and the half that was fixed today is not the half that is still broken.

- **Consumer window.** `build_market_spot_session_markers.py:173-178` — `get_close_1530()` reads `market_spot_snapshots` where `ts` is between **15:29:00 and 15:30:59 IST**.
- **Cause 1 — no producer writes a `ts` in that window.** `capture_spot_1m_v2.py` stops at 15:15 IST (`:99`). `capture_market_spot_snapshot_local.py` runs only at 09:11 and (via the postmarket wrapper) 16:00. Nothing else writes `market_spot_snapshots` intraday. The window is empty by construction.
- **Cause 2 — the one row that carries the settled close is stamped with its own run time, not the bar time.** `capture_cas_close.py:366` sets `capture_ts = datetime.now(IST).astimezone(timezone.utc)` and assigns it to `"ts"` at `:373`. The bar's real slot survives only inside the JSON payload as `raw.bar_ts_ist` (`:384`) and `raw.bar_slot_ist` (`:394`). So the CAS row's `ts` is ~16:20 IST, not 15:29 — it would miss the window even if the ordering were right.
- **Cause 3 — the ordering is also wrong.** `build_market_spot_session_markers.py` runs at **16:10 IST** (crontab line 20); `capture_cas_close.py` runs at **16:20 IST** (line 29). The marker job reads ten minutes before the settled close is written, every day.
- **Why silent.** `get_close_1530()` returns `None`; `derive_capture_quality()` (`:238-264`) simply routes to a different enum value; the row is still upserted (`:330-331`, `:405`). No exception, no non-zero exit — `build_market_spot_session_markers.py` has no `ExecutionLog` at all, so not even a `script_execution_log` row records it.

**On the eleven sessions.** The source comment at `:148-154` records the *premarket* half: the pre-open auction close became random 09:08–09:10 on 2026-09-07 and the capture cron moved 09:08 → 09:11 on 2026-08-24, so `premarket_ref` was NULL from 2026-08-24 onward — eleven sessions of `capture_quality = MISSING`. That half was fixed today by re-anchoring the window to 09:00:00–09:14:59 (`:155-159`).

**The fix changes the symptom, not the state.** Trace `derive_capture_quality` (`:238-264`) for both cases:

| | premarket | open_0915 | close_1530 | postmarket | result |
|---|---|---|---|---|---|
| Before today | False | True | **False** | True | no named branch matches → falls through to `return "MISSING"` `:264` |
| After today's fix | True | True | **False** | True | matches `:254-255` → `return "MISSING_CLOSE_1530"` |

`MISSING` was the catch-all at `:264`, not a specific diagnosis — which is why it was uninformative. After the fix the column will name the remaining defect precisely. But `COMPLETE` (`:244-245`) requires all four, and `close_1530` is structurally unobtainable, so **the column moves from `MISSING` to `MISSING_CLOSE_1530` and stops there.** The three causes above are untouched, and the source comment does not mention the close half.

### F-14 `BROKEN` — the orchestrator health monitor watches a producer that writes no rows at all

- **Consumer.** `monitor_orchestrator_health.py:43-44` reads `script_execution_log` filtered `script_name=eq.run_merdian_shadow_runner_aws.py` with `created_at=gt.{now-5min}`.
- **Producer.** `run_merdian_shadow_runner_aws.py` imports `ExecutionLog` at `:59` and **never instantiates it**. The orchestrator writes no `script_execution_log` row under its own name. Its sixteen sub-steps each write their own rows under *their* script names, which this filter excludes.
- **Mismatch.** The query returns zero rows on every run — every minute, all day, every day.
- **Why silent.** Zero rows → `send_warning('Orchestrator not firing', ...)` (`:53-56`), severity **WARNING**. The exit code is computed at `:78` from alerts whose level is in `['CRITICAL','ERROR']` — **WARNING is not in that list**, so the process exits 0 (`:82-83`). A check that fires every minute and changes nothing.
- The compound effect: this is the only monitor of the orchestrator, and it is structurally incapable of observing it.

### F-15 `BROKEN` — the health dashboard's freshness column is pinned to STALE by a type error

- `refresh_health_dashboard.py:27` — `self.ts = datetime.utcnow()`, **naive**.
- `:40-42` — parses the DB timestamp as `datetime.fromisoformat(ts_str.replace('Z','+00:00'))`, which is **offset-aware** for any `timestamptz` column, then computes `self.ts - ts`.
- Subtracting an aware datetime from a naive one raises `TypeError`, caught by the bare `except` at `:43-44`, which returns the sentinel `999`.
- `:86` — `'FRESH' if minutes_old < 5 else 'STALE'`. `999` always loses.
- The four tables read (`script_execution_log` `:48`, `option_chain_snapshots`, `market_spot_snapshots`, `gamma_metrics` `:68-70`) all store offset-bearing timestamps — established from the writers: `capture_spot_1m_v2.py:330` and `ingest_option_chain_local.py:82-83` both emit `datetime.now(timezone.utc).isoformat()`, which carries `+00:00`.
- **Why silent.** `refresh_health_dashboard.py` has no alerting and no `sys.exit` (`:101-110`); it writes `status.json` and returns. Every table reads STALE forever, so STALE carries no information.
- Scoping note: if any of these columns were declared `timestamp without time zone`, PostgREST would return a naive string and that table alone would compute correctly. That cannot be settled without the DDL, which is out of scope here.

### F-16 `BROKEN` — the spot-freshness contract fails three times every day against a producer that stopped by design

- **Consumer.** `validate_compute_contracts.py:87-89` reads `market_spot_snapshots` with `ts=gt.{now - 1 minute}`.
- **Producer.** `capture_spot_1m_v2.py` writes its last `market_spot_snapshots` row at ~**15:15 IST** (`MARKET_CLOSE_GUARD` `:99`).
- **Consumer schedule.** Crontab line 17, minutes `4,9,…,59` of hours 03–09 UTC. The last three fires are 09:49, 09:54 and 09:59 UTC = **15:19, 15:24 and 15:29 IST**.
- **Mismatch.** Each of those three reads a one-minute window that begins after the last spot write. Zero rows every time.
- **Consequence, verified in source.** Zero rows → violation (`:100-105`) → `send_alert('Compute contracts violated — skipping this cycle', level='WARNING', ...)` (`:169-173`) → `return False` → `sys.exit(0 if success else 1)` (`:185`). **Three Telegram alerts and three non-zero exits per trading day, structurally, on a healthy system.**
- This is the inverse of a silent failure and just as corrosive: a channel that cries wolf daily stops being read. It is the same shape as the `merdian-wsfeed-alert` finding recorded in S71.

### F-17 `BROKEN` — a time-gated branch whose window the schedule never enters

- `detect_ict_patterns_runner.py:479-480` — `if now.hour == 9 and now.minute < 20: expire_prior_session_zones(sb, symbol, trade_date)`, evaluated on `now = now_ist()` (`:432`), i.e. **IST**.
- The script's only invokers are crontab lines 27 and 28, at 10:20 and 10:22 UTC = **15:50 and 15:52 IST**. It appears in no other cron line, in no systemd unit, and is not among the orchestrator's sixteen sub-steps.
- **`now.hour` is therefore always 15. The branch is unreachable, so `ict_zones` rows are never transitioned to `EXPIRED`.**
- **Why silent.** `expire_prior_session_zones` (`:387-397`) is the only writer of the `EXPIRED` status. Nothing asserts that stale ACTIVE rows get retired, so `ict_zones` accumulates ACTIVE rows indefinitely.
- Likely origin: the script was migrated off the Local Task Scheduler to the AWS crontab at S70 and re-timed for the CAS window (ADR-022 D1). The 09:00–09:20 branch was written for a schedule that no longer exists. Nothing in the file records the dependency.

### F-18 `BROKEN` — the power-hour exclusion is compared in UTC and can never fire

- `detect_ict_patterns.py:60` — `POWER_HOUR = dtime(15, 0)`, commented "no new signals after this", i.e. 15:00 **IST**.
- `:509` — `if bar.bar_ts.time() >= POWER_HOUR: continue`.
- `bar.bar_ts` is built by `datetime.fromisoformat(r["bar_ts"])` (`detect_ict_patterns_runner.py:228`) from `hist_spot_bars_1m.bar_ts`, which `capture_spot_1m_v2.py:329` writes as **real UTC**. `.time()` therefore returns the UTC wall clock with no conversion.
- 15:00 UTC is 20:30 IST. The session ends at 15:30 IST = 10:00 UTC. **No bar can ever satisfy the condition**, so every bar including the final ones is fed to the detector.
- The same module converts correctly elsewhere: `time_zone_label()` at `:179-184` does `ts.astimezone(ZoneInfo("Asia/Kolkata"))` before comparing the sibling constants `OPEN_START`/`MORNING_START`/`MIDDAY_START`/`AFTNOON_START`/`SESSION_END` (`:55-59`). **Two comparisons against the same family of constants, in one file, in two different timezones.**

### F-19 `BROKEN` — the ADR-005 producer change silently disconnected its consumer

- **Producer.** ADR-005 made D and W order blocks and fair-value gaps price-breach-only, written with `valid_to = None`. `build_ict_htf_zones.py` sets `valid_to=None` at twelve sites (`:333`, `:352`, `:374`, `:393`, `:472`, `:486`, `:522`, `:539`, `:610`, `:624`, `:651`, `:667`).
- **Consumer.** `detect_ict_patterns_runner.py:261-270` reads `ict_htf_zones` with `.eq("status","ACTIVE").lte("valid_from", trade_date).gte("valid_to", trade_date)` — verified at `:268`.
- **Mismatch.** PostgREST `gte` on a NULL column does not match. **Every D and W zone is invisible to this read.** Only 1H zones, which carry a real `valid_to` (`build_ict_htf_zones.py:1115`, `:1130`, `:1152`, `:1170`), survive the filter.
- **Why silent.** The query returns the 1H subset rather than nothing, so the runner proceeds with a plausible, smaller zone set. Nothing compares the count against what the builder wrote.
- **Inconsistent sibling consumer.** `generate_pine_overlay.py:552-556` reads the same table with `.eq("status","ACTIVE")` and **no validity filter at all** — so the Pine overlay renders D and W zones the signal path cannot see. Two consumers of one table disagree about which rows exist.
- `merdian_daily_audit.py:616-620` uses the same `.gte("valid_to", audit_date)` shape and FAILs when it finds nothing (`:621-626`) — a third reader, with the same defect, whose verdict exits 0 anyway (see F-25).

### F-20 `BROKEN` — the ICT detector runs thirty minutes before the settled close it needs is written

- **Consumer.** `detect_ict_patterns_runner.py:210-219` reads `hist_spot_bars_1m` for `trade_date = today`, at **15:50 / 15:52 IST**.
- **Producers of that table.** `capture_spot_1m_v2.py` writes bars up to the **15:14** bar and then stops (guard `:99`). `capture_cas_close.py` upserts the **15:29 settled-close bar** (`:437-438`, `bar_ts` canonicalised to 15:29 IST at `:420-424`) at **16:20 IST**.
- **Mismatch.** At 15:50 the session as stored ends at 15:14. The settled close arrives thirty minutes later. **The EOD ICT detector never sees the settled close**, and the daily high/low it derives — which become the next session's PDH/PDL — exclude the 15:14–15:29 range entirely.
- **Why silent.** The runner reads whatever bars exist. Its only floor is `len(bars) < 10` (`:493-500`); ~360 bars clear it comfortably.
- This is a consequence of ADR-022's two decisions being sequenced against each other rather than together: D1 re-timed the detector past the CAS window to 15:50, D2 placed the settled-close capture at 16:20. Each is correct alone.

### F-21 `AT-RISK` — ADR-023's recency floor exists in `generate_pine_overlay.py` but is calibrated so it cannot bind

ADR-023 D1 requires derived read paths to carry a recency floor that fails to **absent, never stale**, default 15 minutes. What is actually in the file:

| Floor | Value | file:line | Behaviour on breach |
|---|---|---|---|
| `INTRADAY_MAX_AGE_TRADING_DAYS` | 2 trading days | `:88`, checked `:165-166` | **FAILS** — drops the layer, `return []` `:175`. The only floor that withholds anything. |
| `POSITIONING_MAX_AGE_MIN` | **1440** (24 h) | `:91`, checked `:281-282` | **WARN ONLY** — prints to stderr `:283-289`, then `return out` `:292` with the stale pin/accel dict intact, rendered at `:617-619` |
| `SPOT_MAX_AGE_TRADING_DAYS` / `SPOT_MAX_AGE_MIN_INTRADAY` | 2 days / **240** min | `:115`, `:120`, checked `:510-532` | **WARN ONLY** — `return float(rows[0]["spot"])` at `:533` sits outside all three branches |

- **Why 1440 cannot bind.** The positioning data comes from `gamma_metrics` / `gex_strike_snapshots`, written by the orchestrator whose last run is **15:25 IST**. `generate_pine_overlay.py` runs at **16:22 IST** (crontab line 36). The data is **~57 minutes old on every single healthy run** — and 57 < 1440 by a factor of 25. The floor would not fire until the data were a full day old.
- ADR-023's own reasoning names this error shape: a floor calibrated against the writer's cadence rather than the consumer's. Here it is calibrated against neither.
- The `signal_snapshots` spot fallback (`:539-547`) carries **no floor at all** — it prints an unconditional "may be stale" advisory and returns the value.
- Net: the Pine overlay can still emit a file asserting current positioning off stale inputs, which is the exact artefact ADR-023 was written to prevent.

### F-22 `AT-RISK` — the duplicate-run contract is structurally incapable of firing

- `validate_compute_contracts.py:121` reads `gamma_metrics` with `order=created_at.desc&limit=2&select=run_id,created_at` — **no time filter and no symbol filter**.
- `:135` compares `rows[0]['run_id'] == rows[1]['run_id']`.
- The orchestrator invokes `compute_gamma_metrics_local.py` once per symbol with a **different `run_id` per symbol** (`run_merdian_shadow_runner_aws.py:181`, ids sourced per-symbol at `:101-107`). NIFTY and SENSEX rows therefore interleave in `gamma_metrics` and the two most recent rows differ by construction.
- Unbounded in time as well: on a fully stopped pipeline it compares two ancient rows and passes.

### F-23 `AT-RISK` — the contract validator covers three of the ten tables the orchestrator writes, and short-circuits

- Checked: `option_chain_snapshots` (`:57`), `market_spot_snapshots` (`:89`), `gamma_metrics` (`:121`).
- Not checked, though the orchestrator's sixteen steps write them: `volatility_snapshots`, `momentum_snapshots`, `weighted_constituent_breadth_snapshots`, `market_state_snapshots`, `structural_divergence_snapshots`, `options_flow_snapshots`, `basis_context_snapshots`, `signal_snapshots`, `gex_strike_snapshots`.
- `:158-162` chains the three with `and`. Python short-circuits, so a failing option-chain check means the spot and duplicate checks **never execute** — and per F-16 the option-chain check is the one most likely to fail first on a real outage.

### F-24 `AT-RISK` — the S69 dead-constant bug recurs, unaudited, in the sibling detector

- `detect_ict_patterns_runner.py:77` defines `DETECTION_LOOKBACK = 90` with the comment "last 90 1-min bars (~1.5 hours of context)". A repo-wide grep returns `:77` as its **only** occurrence — it is never referenced.
- The slice actually passed to the detector is the inline literal `bars_5m[-30:]` at `:550`.
- This is byte-for-byte the shape S69 found and fixed in `build_ict_htf_zones.py` (`DAILY_LOOKBACK` defined, never referenced). Rule 22 — when a direction- or structure-asymmetric defect is found in one detector, audit its pair — was applied to the zone builders and **not** extended to this runner.

### F-25 `AT-RISK` — three operator-facing checks cannot express failure in an exit code

| Script | Verdict path | Exit code |
|---|---|---|
| `merdian_daily_audit.py` | overall FAIL printed `:801-802` and written to `audit_results_YYYYMMDD.json` `:805-820` | `main()` returns `log_handle.complete(...)` `:827`, and `ExecutionLog.complete` hardcodes `exit_code=0` (`core/execution_log.py:225-229`). **A FAIL verdict exits 0.** |
| `merdian_local_health_check.py` | `MISSING` / `DEGRADED_*` printed `:279-285` | `main()` never calls `sys.exit` (`:380`, `:428-429`) — always 0 |
| `run_preflight.py` | stage status | `sys.exit(0 if PASS else 1)` `:212`, but stage status is `PASS if failed == 0` (`preflight_common.py:111`) — **a WARN never fails a stage**, so every WARN-level finding exits 0 |

Each of these produces a correct verdict that no automated consumer can act on.

### F-26 `AT-RISK` — the local health check treats absence outside session hours as success

- `merdian_local_health_check.py:200-203` — when a table's latest row is `None`: `MISSING` only if `market_phase == "LIVE"` **and** `required_live`; otherwise `IDLE_OK`.
- `market_phase` is `LIVE` only between `MARKET_OPEN_IST = 09:15` (`:14`) and `MARKET_CLOSE_IST = 15:30` (`:15`), weekdays (`:103-104`, `:126-127`).
- So a table that is completely empty reads `IDLE_OK` — a pass — at every hour outside 09:15–15:30 IST and all weekend. Combined with the always-zero exit code (F-25), an empty database is indistinguishable from a healthy idle one.
- All seven of its reads are `order=ts.desc&limit=1` with **no time filter** (`:168-173`).

### F-27 `AT-RISK` — preflight passes on empty tables and skips its freshness check outside a hardcoded UTC window

- `stage2_db_contract.py:88-91`, `:106-124` — twelve tables are checked with `limit=1`; the check returns `True, f"Table {table} exists ({len(rows)} row(s) returned)"` even when `len(rows) == 0`. Only an HTTP 404 is detected (`:81-82`). **An empty table passes preflight.**
- `stage1_auth_smoke.py:179-192` — same shape on `trading_calendar`: zero rows still returns PASS.
- `stage2_db_contract.py:229-235` — `check_data_freshness` gates on `market_hours = (3 <= hour_utc <= 10)` (`:232`), a hardcoded UTC window, and returns **PASS "Outside market hours — freshness check not applicable"** otherwise. Preflight is by nature run before the session; the check is therefore skipped in exactly the circumstance it exists for.
- Inside the window, its three reads use `order+limit 1` with no time filter and a 600 s threshold (`:238-240`), and a breach returns WARN (`:261-262`) — which per F-25 does not change the exit code.

### F-28 `AT-RISK` — three scheduled writers have no holiday gate

Verified absent by reading each file:

| Script | Cron | Consequence on an NSE holiday |
|---|---|---|
| `capture_index_futures_snapshot_local.py` | lines 8, 9, 30, 31 | inserts `index_futures_snapshots` rows all day, with `basis` computed against the previous session's spot via the unbounded read in F-01 |
| `refresh_equity_intraday_last.py` | line 19 | overwrites the breadth prev-close baseline and re-stamps `ts` with a fresh time (`:127`) while `last_price` remains the prior session's close (`:131`) |
| `detect_ict_patterns_runner.py` | lines 27, 28 | runs the EOD detector; exits via the `len(bars) < 10` path (`:493-500`) and marks the run complete |

The `refresh_equity_intraday_last.py` case has a second edge: because `ts` records the **write** time and `last_price` records the **data** time, any freshness guard on `ts` — including the one added to `scripts/eod_health_check.py` after S59 — reports fresh whenever the job ran, regardless of what it wrote.

### F-29 `AT-RISK` — two ambient scripts pass a function where the gate expects an `ExecutionLog`

- `relate_ambient_to_open_local.py:138` and `accrue_expiry_outcomes.py:191` both call `assert_trading_day_or_exit(log=log)`, where `log` is the module-level logging **function** (`relate_ambient_to_open_local.py:43-44`).
- On a closed day the gate executes `log.exit_with_reason("HOLIDAY_GATE")` (`core/trading_calendar_gate.py:156`) → `AttributeError` on a function object.
- The gate is a no-op on open days, so this is latent until a holiday, when both scripts crash instead of exiting cleanly.

### F-30 `AT-RISK` — a late NSE publish loses that session's Lens 3 permanently

- `ingest_participant_positioning.py` runs at **19:30 and 21:00 IST** (crontab lines 21, 22). On an NSE 404 it exits `SKIPPED_NO_INPUT` with code 0 (`:173-176`) — correctly, since the source has not published.
- `compile_market_environment_local.py` runs at **21:30 IST** (line 23) and its Lens-3 freshness test is **exact equality**: `if latest != as_of.isoformat(): return {**null3, "_note": f"STALE participant board (latest {latest})"}` (`:384-385`). It abstains rather than fabricating a tilt — correct behaviour, and the right shape per ADR-018 D2.
- **The gap is that there is no retry after 21:00.** If NSE publishes at 22:00, no further ingest run exists that day and the compiler has already written its row. That session's Lens 3 is NULL permanently, and the daily ambient verdict is computed from L1+L2 only (`:313-321`).

### F-31 `AT-RISK` — the two 16:10 jobs collide, and the EOD sequence is ordered against itself

Crontab lines 20 and 26 both fire at `40 10` — `build_market_spot_session_markers.py` and `run_equity_eod_until_done.py` (the latter a sweep bounded only by `MAX_RUNS = 80`). Beyond contention, the post-close sequence as scheduled is:

| IST | Job | Reads something written later? |
|---|---|---|
| 15:50 / 15:52 | `detect_ict_patterns_runner.py` | **yes** — the 15:29 CAS bar (16:20). F-20 |
| 16:00 | `capture_postmarket_1600.py` | no |
| 16:10 | `build_market_spot_session_markers.py` | **yes** — the CAS spot row (16:20). F-13 |
| 16:10 | `run_equity_eod_until_done.py` | no |
| 16:20 | `capture_cas_close.py` | — (producer) |
| 16:22 | `generate_pine_overlay.py` | no, but consumes 15:25 positioning. F-21 |

**The settled close is written after both of the jobs that need it.** Moving `capture_cas_close.py` earlier is bounded below by the CAS publication itself; the two consumers are the movable side.

### F-32 `AT-RISK` — host-local `date.today()` used for date-scoped reads in files that use IST elsewhere

| Site | Call | Same file uses IST at |
|---|---|---|
| `merdian_live_dashboard.py:642` | `_today = str(_dt.date.today())`, feeds `ict_zones?trade_date=eq.` `:643-646` | `:253` builds the day boundary from `now_ist()` |
| `merdian_signal_dashboard.py:87` | `.eq("trade_date", str(date.today()))` on `ict_zones` | `:747` renders the page clock in IST |
| `merdian_signal_dashboard.py:114` | `.eq("trade_date", str(date.today()))` on `breadth_intraday_history` | as above |
| `stage2_db_contract.py:166` | `datetime.date.today().isoformat()`, feeds `trading_calendar?trade_date=eq.` `:167` | — |
| `ingest_equity_eod_local.py:263` | `date.today()`, feeds the 220-day fetch window `:263-266` | `:199` parses vendor bars with `tz=UTC` |
| `build_breadth_indicators_daily_local.py` | (via the above) | — |

On a UTC-clock host these agree with IST between 05:30 and 00:00 IST, which covers every scheduled invocation — so none is currently wrong. Each is a latent one-day error for any invocation after 18:30 IST, and the inconsistency inside single files means the convention is not being applied deliberately.

### F-33 `AT-RISK` — the flat-bar quality check passes silently on an empty page

- `merdian_daily_audit.py:231-238` fetches `hist_spot_bars_1m` OHLC for the session window with **no `.limit()`**.
- If the page comes back empty, `flat = 0` (`:239`) and `flat_pct = 0.0` (`:240`), producing `status="PASS", actual="0%"` (`:280-286`).
- The only thing preventing a false PASS is the separate count check (F-2 in that file's own sequence) having already FAILed on `total < 365` — i.e. the guard depends on a different check firing first.

### F-34 `NO-WRITER` / `AT-RISK` — checks and subsystems with no scheduled invoker

- **`scripts/eod_health_check.py` has no scheduled invoker.** It appears in no crontab line and no systemd unit. This confirms the standing observation and is worth restating here because five of the findings above would be caught by it if it ran.
- **The shadow-state subsystem is unscheduled but still monitored.** `merdian_local_health_check.py` polls `signal_state_snapshots` (`:45`), `shadow_state_signal_snapshots` (`:51`) and `shadow_state_signal_outcomes` (`:57`) with 8/8/15-minute staleness thresholds. Their writers — `build_signal_state_snapshot_local.py`, `build_shadow_state_signal_local.py`, `build_shadow_state_signal_outcomes_local.py` — appear in **zero** crontab lines, and their two runner wrappers (`run_merdian_state_stack_once.py`, `run_shadow_state_pipeline_once.py`) are in no cron line and referenced by no other Python file. The health check will report these three degraded during every session, forever, at exit code 0 (F-25/F-26).

### F-35 `AT-RISK` — the futures contract resolver has no fallback and no execution log

- `capture_index_futures_snapshot_local.py:168-179` resolves contracts from `dhan_scripmaster` with `SM_EXPIRY_DATE >= today` and `limit 20`. If the scripmaster is stale, the filter matches nothing, no rows are written, and there is **no fallback path** — the crontab comment at line 35 records this producing zeroed `index_futures_snapshots` on 2026-08-28.
- Compounding: the script has **no `ExecutionLog`**, so a zero-write run leaves no `script_execution_log` row. The failure is invisible to `merdian_daily_audit.py`'s crash scan (`:518-523`) and to every other execution-log consumer.
- Its refresher, `reload_dhan_scripmaster.py`, runs only on the 1st and 15th (line 35), enforces its expiry gate on `FUTIDX` **only** — `OPTIDX` staleness is printed and never blocks (`:250`, `:253-254`) — and treats a post-swap live-count mismatch as a WARN that still returns 0 (`:376-379`).

### F-36 `AT-RISK` — one concept, two thresholds, two files

- `build_breadth_indicators_daily_local.py:33` — `COMPLETE_EOD_THRESHOLD_PCT = 95.0`, the gate that decides whether a date is complete enough to rebuild DMAs (`:203`), raising `RuntimeError` when no candidate qualifies (`:206-210`).
- `scripts/check_eod_coverage_freshness.py` — per the S67 record, its `--min-coverage-pct` default was moved to 92 against a true structural ceiling of 97.83%.
- The builder's gate and the guard that reports on the builder now disagree by three percentage points, and the builder's 95.0 sits only 2.83 points below a ceiling that no amount of correct operation can exceed.

### F-37 `AT-RISK` — `run_ingest.sh` cannot report its own failure; `refresh_equity_intraday_last.py` cannot be imported

- `run_ingest.sh:4` sets `set -eo pipefail`, making `rc=$?` (`:18`) and the END log line (`:19`) unreachable on failure. Six crontab lines route through this wrapper (4, 5, 6, 7, 32, 33). A failed ingest is distinguishable from a successful one only by the absence of a log line.
- `refresh_equity_intraday_last.py:165` contains a bare `PYEOF` token at module level — a leftover heredoc terminator. `raise SystemExit(main())` at `:164` fires first under direct execution, so cron is unaffected, but any `import refresh_equity_intraday_last` raises `NameError`.
- `refresh_equity_intraday_last.py:142-143` warns but does not block when it builds fewer than 1000 rows, against `expected_writes = 1300` (`:55`) and a hard abort only below 100 (`:105-108`). A baseline covering 8% of the universe is written with a warning.

---

## Section 4 — Verified NOT broken

Recorded so the audit is falsifiable, and because several of these have the shape that invites a false finding.

- **`core/trading_calendar_gate.py` resolves a missing row correctly.** Read at `:85-116`: a missing row is not defaulted to allow — it routes to `_resolve_absent_day()`, which defers to the V18E rule engine, the same authority `seed_trading_calendar.py` uses. Fail-open is preserved only for genuine errors (no creds `:90-92`, non-200 `:112`, exception `:113-116`). The ADR-020 contract collision is genuinely closed.
- **`capture_cas_close.py` separates tolerance from canonicalisation correctly.** It accepts `CAS_CLOSE_BAR_SLOTS = {(15,29),(15,34)}` (`:115`) at the boundary but always stores `bar_ts` at the canonical `CAS_CLOSE_BAR = (15,29)` (`:109`, applied `:420-424`), with provenance in `raw`. This is exactly the ADR-022 decision as written. Its bar-slot assertion also **fails** rather than warning (`:314-322`).
- **`compile_market_environment_local.py` Lens 3 fails closed.** A stale participant board returns all-NULL (`:384-385`) rather than a fabricated tilt, and `_participant_tilt` propagates `None` (`:283-285`) so `reconcile()` falls back to L1+L2. This is ADR-018 D2 implemented as intended.
- **`build_breadth_indicators_daily_local.py` will not rebuild off a stale date.** Its candidate set is bounded to the ten most recent dates (`:168`, `RECENT_EOD_CANDIDATE_DAYS = 10` `:34`) and it raises rather than falling back (`:206-210`).
- **`compile_market_environment_local.py` binds both ends of its time windows.** `_ts_window` (`:68-73`) injects an `lte.{UNTIL_ISO}` ceiling alongside every `gte`, so an `--as-of` backfill cannot stamp today's values onto historical rows. This is the S68 lesson correctly applied.
- **`build_wcb_snapshot_local.py` applies a recency floor to the DMA map.** `RECENCY_FLOOR_TRADING_DAYS = 3` (`:148`) drops stale tickers into `missing_daily` (`:196-199`) rather than serving them as current — the S67 fix, still in place. (It does **not** cover `equity_intraday_last`; see F-04.)
- **The option-chain freshness contract is correctly phased.** `validate_compute_contracts.py` fires at minutes `4,9,…` against ingest at minutes `0,5,…` with a 5-minute window — a 4-minute offset inside a 5-minute window. Tight, but derived correctly and currently satisfied at every fire including the last (09:59 UTC window covers the 09:55 UTC ingest).
- **`ingest_breadth_from_ticks.py` tick window matches its producer's cadence.** `TICK_WINDOW_MINUTES = 10` (`:43`) against a feed flushing every `BATCH_FLUSH_SECS = 2` (`ws_feed_zerodha.py:80`). The only mismatch is at the 15:35–15:40 tail (F-03).
- **`ws_feed_zerodha.py` timestamps are instant-correct.** `now_ist()` (`:118-119`) is `datetime.now(timezone.utc).astimezone(IST)` — an IST-offset string representing the correct instant, not IST-labelled-as-UTC. This is why `ingest_breadth_from_ticks.py:114`'s UTC `gte` filter lines up. Worth stating explicitly given the repo's history of the inverse bug.

---

## Section 5 — SQL views: scoping and consumers

Eleven distinct view names are defined across thirteen `CREATE VIEW` statements in `.sql` files, plus two proposal-only definitions inside an ADR.

**Scope limit stated up front.** This repo contains **no** TypeScript, JavaScript, JSX/TSX or HTML — verified: zero files outside `node_modules`. The Marketview frontend lives in the separate `meridian-connect` repo. Every "no consumer" verdict below therefore means *no consumer in this repo*, and cannot exclude the out-of-repo frontend.

### F-38 `AT-RISK` — three competing definitions of the GEX zone views, and which one is live cannot be established from source

| File | Scoping | τ handling |
|---|---|---|
| `sql/2026-05-25_enh81_v_gex_strike_pin_zone.sql:18` | **UNSCOPED** — `DISTINCT ON (run_id, symbol, expiry_date)` `:31` partitions per run, it does not select a latest run; every historical `run_id` produces rows | hardcoded `0.3` `:72` |
| `sql/..._PRE_S40.sql:18` | **UNSCOPED** `:25`, `:35`, `:64` | hardcoded `0.3` `:72`, label `0.3::numeric AS tau_used` `:82` |
| `sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql:26` | **LATEST RUN** via `latest_run` CTE `:28-32` | computation uses hardcoded `0.3` `:79`; `tau_used` separately resolves `get_parameter_num(...)` `:89` |
| `docs/research/s72_gex_view_fix.sql:65` | **LATEST RUN** via `CROSS JOIN LATERAL` over a literal symbol list `:66-77` | `COALESCE(get_parameter_num(...), 0.3)` `:116`, carried through the walk |

The accel view has the same four-way split (`:10`, `:10`, `:97`, `:179`).

Three concerns:

1. **The newest definition is not in `sql/`.** It is in `docs/research/`, and its own header at `:316-328` records that an earlier run of it was rolled back in its entirety. Nothing in the repo establishes which definition the live database holds.
2. **Two of the four are UNSCOPED** — these are the pre-S69 versions whose unbounded recursive walk crossed the PostgREST 8 s ceiling and silently dropped PIN/ACCEL from the Pine overlay. They remain on disk under `sql/`, which is where a future migration would look first.
3. **The S69 version still has the knob wired to a label.** `:79` applies the hardcoded `0.3` in the computation while `:89` reports `tau_used` from `get_parameter_num('pin.tau.' || symbol)`. Changing the parameter moves the displayed value and not the applied one — the exact defect S72 identified. The S72 file fixes it; the `sql/` file does not.

### F-39 `AT-RISK` — the S72 view replaces a time window with a hardcoded symbol window

`docs/research/s72_gex_view_fix.sql:70` and `:184` — `FROM (VALUES ('NIFTY'), ('SENSEX')) AS s(symbol)`. The file documents the hazard itself at `:27-31`: *"the symbol list is now a literal. A third symbol added later would be silently absent from both views."*

This is the same silent-omission shape as the time-window class under audit, in a different dimension: a hardcoded enumeration that a future producer can fall outside of, returning fewer rows rather than an error.

### F-40 `BROKEN` — the health check asserts the base table, never the read path that actually failed

- `scripts/eod_health_check.py:123` defines `GEX_VIEW_SYMBOLS = {"NIFTY","SENSEX"}`, but every request it issues (`:279-281`, `:287-289`) targets `GEX_TABLE = "gex_strike_snapshots"` (`:122`) — **the base table. Neither view is ever queried.**
- Both requests are `[("select","count")]` with **no time filter at all** — unbounded over all history.
- **Consequence.** The S69 outage was a `57014` timeout on `v_gex_strike_pin_zone` while `gex_strike_snapshots` was healthy and fresh. This check would have returned OK throughout, and still would: an unbounded count over a table with ~1.3 M rows cannot reach zero, so a completely frozen writer also passes.
- This is TD-S69-NEW-2 ("health checks must assert on the derived surfaces the operator consumes") still open, now located to the line.

### F-41 `NO-WRITER` / `AT-RISK` — five views have no consumer in this repo, and two carry DDL comments asserting consumers that do not exist

| View | Consumer found | DDL comment claims |
|---|---|---|
| `v_participant_oi_latest` `sql/2026-07-02_enh115_participant_positioning.sql:58` | **none** — the only repo-wide hit is its own DDL line | `:56-57` "Consumers (ENH-116 Lens 3) compare trade_date to the trading calendar". **Contradicted by source**: the Lens-3 reader is `compile_market_environment_local.py:352`, which queries the base table `participant_oi_daily` directly |
| `v_script_execution_health_30m` `sql/20260420_script_execution_log.sql:113` | **none** — only hit outside its DDL is a comment at `ingest_option_chain_local.py:74` | `:133` "Used by dashboard Pipeline Data Integrity card and alert daemon". **Unsupported by any source in this repo** |
| `v_dealer_flow_sim` `sql/2026-05-25_enh81_v_dealer_flow_sim.sql:30` | smoke probe only (`scripts/smoke/smoke_probe_marketview_surfaces.py:64`) | — |
| `v_oi_prev_close_snapshots` `sql/2026-05-25_v_oi_prev_close_snapshots.sql:36` | smoke probe only (`:65`); the "consumer pattern" at `:14-26` is inside a comment block | — |
| `v_merdian_parameter_audit` `sql/2026-05-26_enh83_merdian_parameters.sql:86` | smoke probe only (`:66`, `:71`) | `:108` claims a Settings-footer consumer — out-of-repo frontend, NOT ESTABLISHED |

`v_gex_classic` and `v_gex_oi_change` (`docs/decisions/ADR-002-market-structure-philosophy.md:291`, `:296`) have **no migration file at all** — proposal text that was never created.

Note `v_script_execution_health_30m` is the only view in the repo with a genuine rolling time bound (`where started_at > now() - interval '30 minutes'`, `:128`) and correct `contract_met` aggregation (`:117-119`). It is also the one nothing reads.

### F-42 `AT-RISK` — the validation views are unscoped over full table history

`wcb_signal_validation_v1` (`sql/meridian_wcb_validation_view_v1.sql:18`), `wcb_signal_validation_v2` (`:23`) and `shadow_signal_validation_v1` (`sql/meridian_shadow_validation_view_v1.sql:17`) each end `from public.<table> ss;` with **no `WHERE` clause of any kind** — no time bound, no `DISTINCT ON`, no interval.

A grep for `interval '`, `current_date`, `now() -`, `>= '20` and `::date` across all seven WCB/shadow/falsification query packs that consume them returns **zero hits**. Their only predicates are categorical (`where has_wcb = true`, `where breadth_wcb_relationship = 'CONFIRM_BEARISH'`). So every validation query aggregates the entire history of `signal_snapshots` — including the pre-ADR-009 cohorts, the ENH-55 window disabled at S26, and the gate-stack changes shipped at S30 — into one undifferentiated number. None of these views has a production Python consumer; they are analysis-pack only.

### Correctly scoped, for contrast

- `v_dealer_flow_sim:41-46` — `DISTINCT ON (symbol) … ORDER BY symbol, ts DESC`, a genuine latest-run scope (though with no freshness floor, so it returns the newest row however stale).
- `v_expiry_base_rates` `sql/2026-07-09_enh116_base_rates_live_cohort.sql:35` — `WHERE resolved IS NOT NULL AND source = 'expiry_memory_live'`. This deliberately excludes every seeded row: `backfill_expiry_outcomes.py:58` writes `expiry_memory_s62`, and only `accrue_expiry_outcomes.py:48` writes `expiry_memory_live`. The seed cohort is invisible **by design** (the seed is degenerate — all-RANGE by construction), and the view supersedes the unfiltered `sql/2026-07-03_enh116_phaseb_base_rates.sql:20`. Correct.
- `v_oi_prev_close_snapshots:45-47` binds an upper bound in IST (`< today`), though it has no lower bound.

### Reverse direction

No `v_`-prefixed name is queried from Python without a matching `CREATE VIEW` in the repo — the three reached from code (`v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`, `v_expiry_base_rates`) all have in-repo DDL.

However, **48 of the 71 database objects queried from Python have no DDL of any kind in this repo** — no `CREATE TABLE` and no `CREATE VIEW`. That includes `gamma_metrics`, `option_chain_snapshots`, `market_spot_snapshots`, `ict_zones`, `ict_htf_zones`, `signal_snapshots`, `market_spot_session_markers`, `equity_intraday_last`, `weighted_constituent_breadth_snapshots`, `trading_calendar` and the whole `hist_*` family. Whether any of them is a view rather than a table cannot be established from source. This is the structural reason the instruction not to trust `merdian_reference.json` bites: for two thirds of the schema, that file is the only written record, and it is known to be wrong in at least one place.

---

## Section 6 — Scope limits of this audit

Stated so the findings can be weighed, and so absence of a finding is not read as evidence of absence.

1. **The crontab register is provably incomplete.** `docs/registers/aws_crontab.txt` contains **no `@reboot` line**, yet `merdian_order_placer.py` is recorded elsewhere as an `@reboot`-scheduled HTTP service on this host. The register is a snapshot, not `crontab -l`, and at least one live entry is missing from it. Every producer statement in Section 1 is bounded by what the register contains.
2. **Only five systemd unit files exist in the repo.** Whether the live host carries additional units — the second scheduling surface identified at S72 — cannot be established from here.
3. **No database was queried.** Column types, actual row counts, and which of the three competing GEX view definitions is live are all outside what source can settle. Findings that depend on them are marked as such (F-09, F-15, F-38).
4. **The frontend is out of repo.** No `.ts`/`.tsx`/`.js`/`.html` files exist here. Every "nothing reads this" verdict is scoped to this repository and cannot exclude the Marketview frontend in `meridian-connect`.
5. **48 of 71 database objects queried from Python have no DDL in this repo.** For two-thirds of the schema there is no in-repo record of columns, types or even whether the object is a table or a view.
6. **Research and backfill scripts were excluded.** The producer inventory is the 36 crontab lines, the 5 systemd units, and their transitive invocations. The ~500 other root-level scripts were searched for consumers but not individually audited.

---

## Section 7 — Self-reported health and quality verdict columns

A column counts as **READ** only if some code filters on it, branches on it, aggregates it, or displays it. A writer setting it does not count. A `SELECT *` that returns it without acting on it does not count.

Established by direct search across `.py` and `.sql`. The frontend is out of repo (Section 6, limit 4), so no verdict below can exclude a Marketview consumer.

### F-43 `WRITE-ONLY` — `capture_quality` (`market_spot_session_markers`)

- **Writer.** `build_market_spot_session_markers.py:322`, value from `derive_capture_quality()` (`:238-264`). Eleven possible values: `COMPLETE`, `MISSING_POSTMARKET`, `MISSING_CLOSE_1530`, `MISSING_PREMARKET`, `MISSING_OPEN_0915`, four further partial states, and the catch-all `MISSING` at `:264`. Printed to stdout at `:394`.
- **Reader.** **None.** Every occurrence of the string `capture_quality` in the repo is inside the writer itself — `:151` (a comment), `:238`, `:279`, `:322`, `:394`. No filter, no branch, no aggregation, no SQL view.
- The eleven consecutive sessions of `MISSING` were therefore never going to surface: the column is computed carefully, written faithfully, and read by nothing. It became visible only because a human looked at the table. See F-13 for why the value was `MISSING` and why today's fix moves it to `MISSING_CLOSE_1530` rather than `COMPLETE`.

### F-44 `EFFECTIVELY WRITE-ONLY` — `contract_met` and `exit_reason` (`script_execution_log`)

Both have real readers. Neither reader is scheduled.

| Column | Genuine reads | Scheduled? |
|---|---|---|
| `exit_reason` | `merdian_pipeline_alert_daemon.py:260`, `:285` (branches on the value); `orphan_run_janitor.py:68` (filters `exit_reason=eq.RUNNING`); `sql/20260420_script_execution_log.sql:73` (`where exit_reason <> 'SUCCESS'`) | **no** |
| `contract_met` | `merdian_pipeline_alert_daemon.py:261`, `:286`, selected `:322`; aggregated by `v_script_execution_health_30m` (`sql/20260420_script_execution_log.sql:117-119`) | **no** |

- Neither `merdian_pipeline_alert_daemon.py` nor `orphan_run_janitor.py` appears in `docs/registers/aws_crontab.txt` — a search of that file for `daemon`, `janitor`, `watchdog` and `monitor` returns exactly one line, `monitor_orchestrator_health.py` (line 17). Neither has a systemd unit; the repo contains only the five wsfeed units.
- `v_script_execution_health_30m`, the other `contract_met` consumer, has **no consumer of its own** (F-41).
- `merdian_daily_audit.py:519` does select `script_name, exit_reason`, but its crash test filters on `exit_code` (`:520-522`), and its verdict exits 0 regardless (F-25).
- So the two richest quality signals the execution-log framework produces — did the script meet its declared write contract, and why did it stop — are computed on every run by every instrumented writer, and nothing in the running system consumes either.

### F-45 `READ BUT INERT` — `exit_code` (`script_execution_log`)

Genuinely read and branched on in three places, none of which can act:

| Reader | Branch | Why it cannot act |
|---|---|---|
| `monitor_orchestrator_health.py:59` | `row.get('exit_code') != 0` → CRITICAL | the query it runs returns zero rows always (F-14) |
| `refresh_health_dashboard.py:56` | `'OK' if exit_code == 0 else 'FAILED'` | writes `status.json`; no alert, no exit code (F-15) |
| `merdian_daily_audit.py:520-522` | `.neq("exit_code", 0)` crash scan | the audit exits 0 even on FAIL (F-25) |

### F-46 `WRITE-ONLY` — the per-lens provenance columns on `market_state_snapshots`

- **Writer.** `build_market_state_snapshot_local.py:430-434` writes `gamma_source_table`, `breadth_source_table`, `volatility_source_table`, `momentum_source_table`, `wcb_source_table`, each set to a table name **or `None` when that lens's row was absent**. That NULL is a genuine "this lens did not fire" verdict — precisely the ADR-018 D2 abstention signal, recorded per row.
- **Reader.** `wcb_signal_validation_v1` (`sql/meridian_wcb_validation_view_v1.sql:82-83`) and `v2` (`:104-106`) project `breadth_source_table` as an output column and never filter on it. Both views have no production Python consumer (F-41, F-42). `run_trade_signal_runner_v1.py:241` reads `breadth_source_table`, and that script is not in the crontab.
- `compute_structural_divergence_local.py:342` writes the same shape (`gamma_source_table`) with no reader found.

### F-47 `WRITE-ONLY` — `coverage_pct` (`breadth_intraday_history`)

- **Writer.** `ingest_breadth_from_ticks.py:299`, computed `:207`.
- **The gating happens before storage, not on the stored value.** `MIN_COVERAGE_PCT = 50.0` (`:46`) is applied at `:233` to the in-memory `coverage_pct`, deciding whether to write `market_breadth_intraday`. The value then lands in `breadth_intraday_history` as a record of what happened.
- **Reader of the stored column.** `merdian_signal_dashboard.py:689` reads it and `:714` renders `COV {cov:.0f}%` — display with **no comparison**. `:689` is `cov = latest.get("coverage_pct", 0) or 0`, so a missing or zero field renders `COV 0%` with no warning. No script filters or branches on the stored column.
- Worth flagging against the record: the S72 note that withdrew a claim here stated that the column exists **and that downstream already filters it**. The first half is confirmed (`:299`). The second half I cannot confirm — the only read found is a display. `check_eod_coverage_freshness.py:181` does apply `pct < args.min_coverage_pct`, but to a percentage it computes itself over `equity_eod`, not to this stored column. This is worth re-checking before the withdrawal is relied on.

### F-48 `WRITE-ONLY` — quality verdicts buried inside `raw` JSON

`capture_cas_close.py:393` writes `"flat_bar_provisional": bool(bar.get("provisional_flat"))` into the `raw` payload of `market_spot_snapshots`, alongside `cas_settled` (`:383`), `bar_ts_ist` (`:384`) and `bar_slot_ist` (`:394`). These are the only record that a settled-close bar was accepted despite being flat, and that the row's real bar slot differs from its `ts`.

Because they live inside a JSON blob rather than in columns, no consumer filters on them, and F-13 depends on exactly this: `bar_ts_ist` holds 15:29 while the `ts` column holds ~16:20, and the marker job queries the column.

### Columns that are genuinely read and acted on

For contrast, three verdict columns work as intended:

- **`status` on `ict_zones` / `ict_htf_zones`** — filtered at `build_trade_signal_local.py:975`, `detect_ict_patterns_runner.py:263`, `generate_pine_overlay.py:182` and `:553`, `merdian_daily_audit.py:618`. Caveat: for `ict_zones` the value `EXPIRED` is written only by `detect_ict_patterns_runner.py:392`, which sits behind the unreachable hour-9 branch (F-17). A repo-wide search confirms no other writer of `EXPIRED` for that table. The domain is effectively `{ACTIVE, BROKEN}`.
- **`source` on `expiry_outcomes`** — filtered by `v_expiry_base_rates` (`sql/2026-07-09_enh116_base_rates_live_cohort.sql:35`, `source = 'expiry_memory_live'`), which correctly excludes the degenerate seed cohort written as `expiry_memory_s62`.
- **`is_pre_market` on `hist_spot_bars_1m`** — filtered at `detect_ict_patterns_runner.py:212` and `merdian_daily_audit.py:216`, `:235`.

### The pattern

Of the seven self-reported verdict signals examined, **one has no reader at all** (`capture_quality`), **four have no reader that runs** (`contract_met`, `exit_reason`, the `*_source_table` provenance set, `coverage_pct`), and **one is read by three consumers none of which can act on it** (`exit_code`). The instrumentation is not missing — it is thorough, and it terminates. Every one of these columns is written on every run by code that took care to compute it correctly.

---

## Section 8 — Findings index

**59 findings.** 13 `BROKEN` (F-01, 02, 03, 04, 13, 14, 15, 16, 17, 18, 19, 20, 40) · 26 `AT-RISK` · 20 `NO-WRITER` / write-only / read-but-inert (F-10, 34, 41, 43–48, and F-49–59 added in Section 9 after the Section 7 commit).

### Producer writes outside consumer read window — the strict defect class

| ID | Producer → consumer | Severity |
|---|---|---|
| F-13 | CAS settled close (16:20) → session-marker `close_1530` window 15:29–15:31, job at 16:10 | BROKEN |
| F-20 | CAS settled-close bar (16:20) → ICT detector reading today's bars at 15:50 | BROKEN |
| F-16 | spot capture stops 15:15 → contract validator's 1-minute window at 15:19 / 15:24 / 15:29 | BROKEN |
| F-02 | breadth writes to 15:40 → WCB consumer's last run 15:25 | BROKEN |
| F-03 | tick feed stopped 15:35 (systemd) → breadth ingest reading to 15:40 (cron) | BROKEN |
| F-17 | detector scheduled 15:50 → `expire_prior_session_zones` gated to hour 9 | BROKEN |
| F-18 | `bar_ts` in UTC → `POWER_HOUR` 15:00 compared as UTC, never reached | BROKEN |
| F-19 | ADR-005 writes `valid_to = NULL` → consumer filters `.gte("valid_to", …)` | BROKEN |
| F-14 | orchestrator writes no `script_execution_log` row → monitor filters on its name | BROKEN |
| F-06 | cron runs to 15:29 → `MARKET_CLOSE_GUARD` stops writes at 15:15 | AT-RISK |
| F-30 | NSE publishes after 21:00 → no ingest retry, compiler already ran at 21:30 | AT-RISK |
| F-31 | EOD sequence: two jobs read what a later job writes | AT-RISK |

### Unbounded reads — the inverse failure: never zero rows, silently stale

| ID | Consumer | Producer |
|---|---|---|
| F-01 | `capture_index_futures_snapshot_local.py:144-152` spot for `basis` | spot stops 15:15, consumer runs to 15:40 |
| F-04 | `build_wcb_snapshot_local.py:94-99`, `ingest_breadth_from_ticks.py:160-162` | `equity_intraday_last`, refreshed once at 09:05 |
| F-05 | WCB stamps its own `ts` from upstream and upserts on it | frozen upstream → row overwritten, not appended |
| F-12 | `ws_feed_zerodha.py:366-372` universe membership | requires two independent boolean columns |
| F-21 | `generate_pine_overlay.py` positioning floor 1440 min, warn-only | data is ~57 min old on every healthy run |
| F-22 | `validate_compute_contracts.py:121` duplicate-run check | unbounded and structurally unable to fire |
| F-26 | `merdian_local_health_check.py:168-173` all seven reads | + `IDLE_OK` silent pass outside 09:15–15:30 |
| F-40 | `eod_health_check.py:279-289` GEX | base table, unbounded count, never the views |
| F-42 | WCB / shadow validation views | unscoped over full table history |

### Silent by construction — failures that cannot reach an operator

F-25 (three checks that cannot express failure in an exit code) · F-27 (preflight passes on empty tables, skips freshness outside a hardcoded UTC window) · F-15 (dashboard freshness pinned to STALE by a naive/aware type error) · F-23 (validator covers 3 of 10 tables, short-circuits) · F-33 (flat-bar check passes on an empty page) · F-35 (futures resolver has no fallback and no execution log) · F-37 (`run_ingest.sh` cannot report its own failure)

### No scheduled writer / no consumer

F-10 (19 `build_ict_primitives` variants, none scheduled) · F-34 (`eod_health_check.py` has no invoker; the shadow-state subsystem is unscheduled but still monitored) · F-41 (five views with no consumer, two carrying DDL comments asserting consumers that do not exist) · F-43 to F-48 (verdict columns, above)

### Correctness hazards adjacent to the class

F-07 (no holiday gate on futures capture) · F-08, F-32 (host-local `date.today()` for date-scoped reads in files that use IST elsewhere) · F-09 (`"now()"` written as a literal string) · F-11, F-37 (`set -eo pipefail` making the failure log unreachable; stray `PYEOF`) · F-24 (`DETECTION_LOOKBACK` dead constant — the S69 bug shape recurring, unaudited, in the sibling detector) · F-28 (three scheduled writers with no holiday gate) · F-29 (function passed where `ExecutionLog` expected → `AttributeError` on holidays) · F-36 (one concept, two thresholds, two files) · F-38, F-39 (three competing GEX view definitions; hardcoded symbol list)

### The two most load-bearing observations

1. **F-13 is half-fixed and the fixed half is not the broken half.** Today's change re-anchored `premarket_ref` to the market open. `close_1530` remains unobtainable for three independent reasons — no producer writes a `ts` in the window, the CAS row is stamped with its run time rather than its bar time, and the marker job runs ten minutes before the CAS capture. `capture_quality` will move from `MISSING` to `MISSING_CLOSE_1530` and stop there, and nothing reads it either way.

2. **The verdict columns are not missing — they terminate.** `capture_quality`, `contract_met`, `exit_reason`, the `*_source_table` provenance set and `coverage_pct` are all computed carefully on every run and consumed by nothing that runs. The system's self-knowledge is written down and never read. That is why an eleven-session defect surfaced by eye rather than by alarm.

---

## Section 9 — Post-commit sweep: further write-only verdict columns

**Provenance.** Sections 1–8 were committed as `584f854`. A broader automated verdict-column sweep, launched at the same time as the other five but slower to return, landed **after** that commit. This section records what it found. Everything below is additive: the sweep **contradicted nothing** in Section 7 — `capture_quality` write-only with no reader, `contract_met` and `exit_reason` read only by the unscheduled alert daemon and janitor, and `v_script_execution_health_30m` queried by no script were all independently reconfirmed.

The three items given particular weight below were re-verified by hand before recording, and one of them required correcting the framing (F-50).

Same standard as Section 7: a column counts as READ only if code filters on it, branches on it, aggregates it, or displays it. A writer setting it does not count; an incidental `select` that returns it without acting on it does not count.

### F-49 `WRITE-ONLY` — `data_quality_events`: four writers, zero readers, `resolved` never flipped

- **Writers.** Four scripts, each POST-only, each constructing the REST URL directly:
  - `log_data_quality_event_local.py:61` (URL), `:88` `severity` default `'warning'`, `:100` `"resolved": False`
  - `run_trade_signal_runner_v1.py:79`, `:90`, `:95`
  - `label_signal_outcomes_local.py:85`, `:96`, `:101`
  - `review_threshold_candidate_local.py:97`, `:108`, `:113`
- **Reader.** **None.** A repo-wide search for `data_quality_events` returns exactly four hits — the four POST URLs above. There is no GET, no `.select`, no filter, no view.
- **`resolved` is written `False` at all four sites and updated nowhere.** No code path flips it to true. The column records an intent to triage that no triage process exists to discharge.
- Distinguish from `expiry_outcomes.resolved` (`accrue_expiry_outcomes.py:161`, `backfill_expiry_outcomes.py:225`), which *is* read — `v_expiry_base_rates` filters `WHERE resolved IS NOT NULL`. Same column name, different table, opposite verdict.
- This is the purest instance of the Section 7 pattern: a dedicated data-quality event log, four distinct producers taking the trouble to emit into it, and no consumer at any point in its history.

### F-50 `WRITE-ONLY` — the `*_stale_floored` marker family, and a correction to how it bears on ADR-023

Three subsystems write a boolean recording that a recency floor fired. **No code anywhere filters, branches on, or aggregates any of them.**

| Column | Writer | Floor default |
|---|---|---|
| `market_state_snapshots.breadth_stale_floored` | `build_market_state_snapshot_local.py:435`, computed `:387` | `MERDIAN_BREADTH_RECENCY_FLOOR_MIN`, 15 min |
| `market_state_snapshots.wcb_stale_floored` | `:436`, computed `:394` | `MERDIAN_WCB_RECENCY_FLOOR_MIN`, 15 min |
| `signal_snapshots.options_flow_stale` | `build_trade_signal_local.py:907`, computed `:483-495` | `MERDIAN_FLOW_RECENCY_FLOOR_MIN`, 15 min |
| `signal_snapshots.basis_context_stale` | `:911`, computed `:517-526` | `MERDIAN_BASIS_RECENCY_FLOOR_MIN`, 15 min |
| `structural_divergence_snapshots.source_stale_floored` | `compute_structural_divergence_local.py:338`, also duplicated into `raw` `:358`, computed `:283` | `MERDIAN_SDM_RECENCY_FLOOR_MIN`, 15 min; DDL default `false` at `sql/2026-06-22_enh_sdm_structural_divergence_snapshots.sql:71` |

Every occurrence of `stale_floored` in the repo is a write site, the helper that computes it, a docstring, a `print`, or DDL. There are no reads.

**Correction to the framing.** These are not floors "stored as marks instead of being enforced" — that would understate two of them and overstate the third. Read the implementations and they split:

- **`build_market_state_snapshot_local.py` genuinely abstains.** `_apply_recency_floor` (`:117-123`) documents itself as treating an over-age row as **ABSENT**, and returns `(row_or_None, stale_bool)`. The row is dropped; the boolean is the audit trail of the drop. ADR-018 D2 is correctly implemented here.
- **`build_trade_signal_local.py` genuinely abstains.** `:492` sets `_flow = {}` and `:495` does the same on a parse failure, so every downstream `_flow.get(...)` at `:496-497` returns `None`. Same for basis at `:517-526`.
- **`compute_structural_divergence_local.py` does not, by design.** `:144` states it outright: *"for a display-not-gate monitor we FLAG staleness (source_stale_floored) rather than [abstaining]"*. Here the mark **is** the entire mechanism.

So the accurate finding is sharper than "the floors are only marks":

1. For the first two, the floors work. What is unread is the **evidence that they fired**. Nothing can answer "how often did the breadth floor abstain last month?" — which is precisely the calibration input ADR-023 D1 needs, and precisely what F-21 shows is missing when a floor is set to 1440 minutes against a consumer whose data is always ~57 minutes old. **The floors are enforced and unmeasurable.**
2. For the third, staleness is deliberately non-blocking and the only signal is a boolean nothing reads — so a silently stopped upstream feeding the structural-divergence monitor is invisible at both ends.

### F-51 `WRITE-ONLY` — `smdm_squeeze_alert`: hardcoded `None`, with a partial index built on a value it cannot hold

- **Writer.** `premium_outcome_writer.py:801` — `"smdm_squeeze_alert": None`, a literal. The sole writer; the value is never computed.
- **Column.** `sql/meridian_signal_premium_outcomes_v1.sql:75` — `smdm_squeeze_alert BOOLEAN`.
- **Index.** `:106-107` — `ON signal_premium_outcomes (smdm_squeeze_alert, action, symbol) WHERE smdm_squeeze_alert = TRUE`.
- **The index predicate can never be satisfied.** The only writer emits `None`, so no row will ever have `smdm_squeeze_alert = TRUE`. The index is permanently empty, is maintained on every insert, and serves no query — no code filters on the column.
- **Context.** SMDM was retired as built per ADR-018 D3, which explicitly dropped the STOP_HUNT/SQUEEZE flags. The writer hardcodes `None` because the subsystem that would have produced the value no longer exists. The column and its index are survivors of a retired subsystem that nothing removed.

### F-52 `WRITE-ONLY` — `measurement_health_snapshots`: an entire health table written once and read never

- **Writer.** `measurement_health_snapshot_local.py:435` — a single `client.insert("measurement_health_snapshots", row)`. The row carries `overall_status` (`:402`) plus seven per-module verdicts (`:419-426`): `volatility_status`, `futures_status`, `wcb_status`, `gamma_status`, `momentum_status`, `regret_log_status`, `regret_analytics_status`, each `'OK'` / `'STALE'` / `'CRITICAL'` from a worst-of roll-up (`:288-291`, `:368`).
- **Reader.** **None.** The table name appears exactly once in the entire repo — that insert. The `print` at `:439` reads back the insert's own return payload, not a query.
- A purpose-built health-verdict table, eight verdict fields, one write site, zero reads.

### F-53 `WRITE-ONLY` — `structural_divergence_snapshots`: three verdicts on a table nothing ever reads

- `divergence_mode` — `compute_structural_divergence_local.py:336`, hardcoded `'OBSERVE'`. The DDL admits `'OFFENSIVE_CONTEXT'` / `'DEFENSIVE_CONTEXT'` / `'NONE'` (`sql/2026-06-22_enh_sdm_structural_divergence_snapshots.sql:67`); none is ever written.
- `raw->>'three_wick_status'` — `:356`, constant `'DEFERRED_P3_needs_OHLC'`. Sibling `raw->>'display_not_gate'` = `True` at `:357`.
- `source_stale_floored` — see F-50.
- **Reader.** The table is never SELECTed by any script; the only access is the writer's own upsert at `:365`. Consistent with ADR-018 D4's "display-not-gate" intent — but the display consumer is the out-of-repo frontend, so within this repo the subsystem writes into a void.

### F-54 `WRITE-ONLY` — `structural_alerts`: three verdicts behind an existence check

- `score_confidence` — `detect_structural_manipulation.py:722`, set at `:462`, `:664`; `'FULL'` / `'PARTIAL'` / `NULL` when `dte != 0`.
- `squeeze_alert` — `:721`, `True` / `False`, forced `False` when `run_type == "PARTIAL"` (`:674`).
- `run_type` — `:718`, `'FULL'` / `'PARTIAL'`, argv-derived. It is part of `on_conflict="symbol,ts,run_type"` (`:791`) — a key, not a read.
- **Reader.** `structural_alerts` is read exactly once in the repo, `:234-239`, and that query is `select=id` — a row-existence check that never touches any of the three.

### F-55 `WRITE-ONLY` — the historical-ingest quality trio

- `hist_completeness_checks.flag_incomplete` — `hist_ingest_controller.py:468`, `:478` (`actual_bars < expected * 0.80`), inserted `:470`. **Reader: none.** The DDL comment at `sql/meridian_hist_ingest_schema_v1.sql:213` claims "flag_incomplete=TRUE triggers manual review"; no code implements it. Another DDL comment asserting a consumer that does not exist, as in F-41.
- `hist_completeness_checks.coverage_pct` — a DB-generated column (`sql/meridian_hist_ingest_schema_v1.sql:203-206`). **Reader: none** — the table is never SELECTed.
- `hist_ingest_rejects.reject_reason` — `hist_ingest_controller.py:284` (free text), bulk-upserted `:675`. **Reader: none** — write-only table.

### F-56 `WRITE-ONLY` — outcome and reconstruction verdicts

- `shadow_outcomes_v2.evaluation_status` — `evaluate_shadow_outcomes_local.py:240`, `:270`, `:309`, `:360`, inserted `:399`; values `'SKIPPED_NO_ENTRY'`, `'SKIPPED_INSUFFICIENT_HORIZON'`, `'EVALUATED'`. **Reader: none** — the table appears only at `:398-399`.
- `shadow_reconstruction.coverage_status` — `reconstruct_shadow_for_date_local_v3.py:463` via `classify_coverage()`, row field `:495`, printed `:473`, `:545`. **Reader: none** outside that file. Its literal value set is NOT ESTABLISHED from the call sites.
- `signal_premium_outcomes.data_source` — `premium_outcome_writer.py:815`, `'LIVE'` if `trade_date >= today - 7d` else `'BACKFILL_CHAIN'`; DDL default `'LIVE'` (`sql/meridian_signal_premium_outcomes_v1.sql:85`). **Reader: none.** This is a provenance verdict distinguishing live from backfilled measurement — exactly the discriminator any cohort analysis would need — and nothing filters on it.
- `signal_premium_outcomes.outcome_label` and `signal_outcomes.outcome_label_{15m,30m,60m,eod}` — `premium_outcome_writer.py:667`, `:796`; `outcome_engine_common.py:342-344`; `build_signal_outcome_audit_local.py:377-380`. The only reads are the writer displaying its own in-memory row (`:904`, `:921`) and `group by outcome_label_eod` in `sql/meridian_outcome_comparison_pack_v1.sql:65-79`, `:164`, `:183` — a file of loose `select` statements, not a view, executed by nothing in the repo.

### F-57 `WRITE-ONLY` — four columns that are selected but discarded

The incidental-`select` case: the column comes back in the payload and no code reads it off the row.

| Column | Writer | Apparent reader | Why it does not count |
|---|---|---|---|
| `gamma_metrics.run_type` | `compute_gamma_metrics_local.py:1083` | `detect_structural_manipulation.py:635` includes it in the `select` list | the value used at `:672`, `:674` is the **caller's own CLI `run_type`**; no `gamma_row.get("run_type")` exists anywhere |
| `breadth_ingest_state.last_status` | `ingest_equity_eod_local.py:83` (`'SEEDED_BY_PYTHON'`), `:250` | `:68` includes it in the `select` list | the caller at `:287-289` consumes only `cursor` and `limit_per_run` |
| `momentum_snapshots.source` | provenance defaults in `sql/2026-06-26_enh07b_hist_basis_context.sql:22` and siblings | selected at `compute_momentum_features_v2_local.py:143`, `measurement_health_snapshot_local.py:300` | the first never branches on it; the second copies it into `measurement_health_snapshots`, which nothing reads (F-52) |
| `hist_ingest_log.status` | `hist_ingest_controller.py:645`, `:797`, `:655`, `:679` | `:626-632` selects `id,status` and **prints** it at `:632` | display only — the dedup decision keys on `source_checksum`, not on `status`. Counts as READ under the Section 7 rule, but drives nothing. Three of its six CHECK-permitted values (`'COMPUTE_DONE'`, `'ARCHIVED'`, `'PARTIAL'`, `sql/meridian_hist_ingest_schema_v1.sql:153-161`) are never written by any Python |

### F-58 `WRITE-ONLY` — two WCB coverage verdicts, one of which duplicates a value that *is* read

- `signal_snapshots.wcb_weight_coverage_pct` — `build_trade_signal_local.py:891`; column added `sql/meridian_wcb_measurement_integration.sql:40`. **No Python reader.** It is referenced in `shadow_signal_validation_v1` (`sql/meridian_shadow_validation_view_v1.sql:54`) and aggregated in `sql/meridian_wcb_validation_summary_pack_v1.sql:93` — but no script queries that view (F-41, F-42) and the pack is loose SQL nothing executes.
- `market_state_snapshots.wcb_features->>'is_partial'` — `build_market_state_snapshot_local.py:276` (`matched_weight_pct < 100.0`); replay twin `replay/replay_build_market_state_snapshot.py:288`. **Reader: none** — a repo-wide search for `is_partial` returns only those two write sites.
- The contrast is instructive: the *upstream* value these derive from, `market_state_snapshots.wcb_features->>'matched_weight_pct'` (`build_market_state_snapshot_local.py:257-272`), **is** genuinely read and branched — `build_shadow_signal_local.py:128`, with confidence penalties at `< 85.0` and `< 95.0` (`:199-203`). The raw number is consumed; both derived verdicts computed from it are not.

### F-59 `WRITE-ONLY` — `market_environment_snapshots.regime_conditional_note`

- **Writer.** `compile_market_environment_local.py:503`, free text from `phaseb_note()` (`:452-462`) — the N-floored Phase-B base-rate receipt.
- **Reader.** None.
- Its siblings on the same row *are* read: `ambient_regime` and `lens_alignment` are selected and displayed by `relate_ambient_to_open_local.py:72-75`, `:109`, and filtered through `v_expiry_base_rates` at `compile_market_environment_local.py:443-444`. The note — the part that records *why* the verdict is what it is, and how much evidence stands behind it — is the part nothing reads.

### Columns the sweep confirmed are genuinely read

Recorded for balance, and because each is a working counter-example: `hist_greeks_backfill_log.status` (filtered `in.(DONE,SKIPPED_EXPIRY)` at `backfill_hist_greeks.py:377-378`, with a supporting index at `sql/2026-06-28_s62_hist_greeks_backfill_log.sql:20` — the one index in this section that serves a real query); `ict_primitive_outcomes.retest_status` (`audit_s33_enh103_falsification.py:100`, `:103`); `option_execution_price_history.source` (`build_option_execution_outcomes_v1.py:180`, `:274`); `signal_snapshots.entry_quality` (branched at `build_shadow_signal_local.py:116`, `:228`); `ict_htf_zones.status` (filtered at eight sites); `market_environment_snapshots.ambient_regime` / `lens_alignment`.

### Excluded — not database columns

Flagged so they are not mistaken for gaps. These verdicts live in JSON files or in-process state, not tables, and several **are** read: the `gamma_engine_*` heartbeat verdicts under `runtime/heartbeats/` (`gamma_engine_alert_daemon.py:16`, `:136`, `:179-192`, branched at `:512-598`); `merdian_daily_audit.py`'s `overall_status` (`:136`, `:760`, `:811`) which goes to `audit_results_YYYYMMDD.json` and into `script_execution_log.notes` at `:827`; `run_preflight.py:123-127` `overall_status`, read at `preflight_common.py:249` and driving the exit code at `:212`. Experiment-script `verdict` / `quality_score` / `wick_quality` locals are printed and never persisted.

### What Section 9 adds to the picture

Section 7 found the pattern in the execution-log framework and the session markers. This sweep shows it is not local to those: **eleven further findings covering roughly twenty-four columns across fourteen tables**, including two purpose-built quality tables (`data_quality_events`, `measurement_health_snapshots`) with zero reads in their entire history, a DDL comment asserting a manual-review trigger that no code implements (F-55), and an index maintained on every insert against a predicate no row can satisfy (F-51).

The `*_stale_floored` family (F-50) is the one that changes a live conclusion rather than adding to a list. The ADR-018 D2 abstentions are real and working. What does not exist is any way to observe them firing — which is the missing input to the ADR-023 D1 calibration problem recorded at F-21, where a floor sits at 1440 minutes against data that is ~57 minutes old on every healthy run, calibrated against nothing.
