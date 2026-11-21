# Request to the engine stream from the tape stream: stage 2b (Sat 2026-11-14, MR-OFL8)

From: tape stream (MR-OFL8). For: engine stream. Read with `rulings_s105_tape_w.md` (your ruling), `rulings_mr_ofl8.md` (R8-A to R8-G), `2b_writer_plan.md`, `Q1_upsert_gate_plan.md`, `tape_stage_2a_record_2026-11-12.md`. Nothing here is applied without the operator's approval; you author the SQL, the operator applies it. No secret goes into chat, the repo, `/tmp` or a log.

## Where the tape stream is

- Phase B (`56bf0558e53c59772a316688bb7219233f3466d5`, `tape/live-l2`) is installed on the production box, file-only, `CPUQuota=100%`, timer disabled. Box suite, Python 3.10 guards and a recorded-day rehearsal all PASS (2026-11-14).
- The 2b writer (the first code that writes as `tape_w`) is not built yet. Plan: `2b_writer_plan.md`. It writes one psql script per 5-minute cycle: `BEGIN; SET LOCAL standard_conforming_strings = on; SET LOCAL lock_timeout = '5s';` multi-row `INSERT ... ON CONFLICT` statements of N rows (N = 500 provisionally, 100 to 2,000 after calibration) for cycle, events, wall, then label with `ON CONFLICT DO NOTHING`; `COMMIT;`. One connection, never concurrent with another `tape_w` session of the runner. No DELETE, ever.
- Before the first live 2b day there is an upsert-time gate: a recorded day (2026-11-06) replayed on the box under a simulated clock with `trading_day` and every `timestamptz` shifted to that day's date, run on a **Saturday** (Sunday spare), writing as `tape_w` into the real tables. Earliest Saturday: 2026-11-21. The operator deletes those rows afterwards as `postgres`.
- Measured volumes for 2026-11-06 on the box: 104,822 rows re-sent over the day; largest single cycle 11,893 rows; base state about 15,525 cycle + event rows.

## What we need from you

| # | Item | Needed by |
|---|---|---|
| 1 | **`tape_w` password script** (your ruling 7: generated on the box as `tapelive`, umask 077, SCRAM verifier only printed). The file is `/etc/tape-live/tape-w.env`, mode 600, and the variable must be named **`TAPE_LIVE_W_DSN`** (operator ruling Q-op-14); value in the same `postgresql://` form as the read-only DSN, direct pooler session, `sslmode=require`. `tapelive` (uid 997) and `/etc/tape-live/` (root, 755) exist. Then V2, V3, V5 and the login proof. | Before the 2b build is installed on the box (the week of 2026-11-16 at the earliest) |
| 2 | **Cleanup SQL for the gate rows:** delete from `tape_live_cycle`, `tape_live_events`, `tape_live_wall`, `tape_live_label` where `trading_day` = the gate date, as `postgres`, with a row count per table before and after, and a guard that refuses if the date is a trading day or a special session. It is run between gate runs and before Monday's open. | Before the Saturday gate |
| 3 | **`pg_stat_statements` read** for `tape_w`'s statements, to be run by the operator as `postgres` before and after a gate run (no reset of the shared view): calls, total, mean and max execution time, rows, per statement. | Before the Saturday gate |
| 4 | **Lock-wait sampling query** on `pg_stat_activity` (`usename = 'tape_w'`, `wait_event_type = 'Lock'`) for the operator to run during the heavy part of the gate. | Before the Saturday gate |

## Questions

| # | Question | Why it matters |
|---|---|---|
| E-1 | Does the session pooler pass through to psql, unchanged: SQLSTATE 53300 (connection limit), 57014, 55P03, 42501, 25P03; the `INSERT 0 n` command tags; and `\timing` output? Is the server PostgreSQL 15 or newer? | The writer classifies every failure by SQLSTATE and reads row counts from the tags. `ON CONFLICT ON CONSTRAINT tape_live_events_grain_uq` relies on NULLS NOT DISTINCT. |
| E-2 | Is the RLS "today" exactly `(now() AT TIME ZONE 'Asia/Kolkata')::date`? The runner's final write is at about 15:46 IST. For the Saturday gate, rows carry `trading_day` = that Saturday, `ts_ist` and `as_of` shifted to that date (so some are later than `now()`), and `expiry` unshifted (earlier than `trading_day` for one symbol). Does any CHECK, trigger or policy refuse such rows? | A refusal stops the gate at the first cycle. |
| E-3 | **Token remap (`tape_live_cycle_grain_uq`).** When a strike gets a new `instrument_token` at the same (symbol, trading_day, expiry, strike, leg, ts_ist), the new row would violate `tape_live_cycle_grain_uq`, so the writer withholds it, counts it once per key per day and lists it in `db_withheld.csv`. The old token's row stays under its old epoch id. After that symbol's next epoch bump, readers of the newest epoch (rule R6-H) no longer see that grain at all. What should readers see, and do you want a remedy (for example a second statement that upserts on the grain constraint)? | **Needed before the first live 2b day.** Without an answer a strike can vanish from `/tape` for the rest of the day. |
| E-4 | `data_contracts`: the 8 rows go in on the writer-start day after the first cycle writes both symbols (your ruling 6). The Saturday gate writes rows before that day and they are deleted again. Confirm the contract checker cannot see or alert on them, and that the provisional `expected_per_cycle` ceilings allow a cycle of about 12,000 rows on a bump. | False alerts, or a ceiling breach on the first bump. |
| E-5 | Limits on the write path: any pooler or project limit on statement text size (a 2,000-row multi-row INSERT), on transaction duration, or on a transaction of about 12,000 rows across four tables? `statement_timeout` 15 s is per statement; the writer targets 5 s per statement and 30 s for the largest cycle. | Sets the batch size range. |
| E-6 | The DDL comment on `as_of` says "writer clock, UTC". It is the grid time of the cycle that last changed the row, and after a skipped write a row is sent later than its `as_of`. Wording only. | Reader expectations. |

## Still open from earlier (yours)

- Bucket-scoped S3 policy for the box role (it still carries `AmazonS3FullAccess`).
- The parity-target engine note (`engine_note_parity_target_observed_2026-11-12.md`).
- Register items in `rulings_s105_tape_w.md` (no PK on `tape_live_events`; two unique rules on `tape_live_cycle`).
