# Engine-stream answer to `engine_request_tape_2b_2026-11-14.md` (2026-11-14)

Basis: docs read (request, `rulings_s105_tape_w.md`, `2b_writer_plan.md`, `rulings_mr_ofl5_addendum_2026-11-09.md`). Nothing below was run against the database. UNVERIFIED = the docs do not show it; the read that settles it is given.

## E-3 token remap (deadline: before the first live 2b day)

Facts (docs): cycle PK `(symbol, trading_day, instrument_token, ts_ist)`; second unique `tape_live_cycle_grain_uq (symbol, trading_day, expiry, strike, leg, ts_ist)`; the writer's conflict target is the PK only. A remapped row (new token, same grain, same ts_ist) therefore raises 23505 on the grain constraint. `tape_w` holds table-level UPDATE on cycle. No DELETE.

Options:
1. **Withhold and count (as built).** After the symbol's next epoch bump the old-epoch row is the only row for that grain, and R6-H readers drop it. The strike vanishes from `/tape` for the rest of the day.
2. **Second statement, upsert on the grain constraint (recommended).** The writer already holds a model of every DB row, so it can split the write set: rows whose grain exists in the model under a different token go to `INSERT ... ON CONFLICT ON CONSTRAINT tape_live_cycle_grain_uq DO UPDATE SET instrument_token = EXCLUDED.instrument_token, live_run_id = EXCLUDED.live_run_id, <all other columns> = EXCLUDED.<col>`. One statement cannot carry two conflict targets, hence two statements in the same transaction. The row keeps one place per grain and moves into the newest epoch, so readers see it. No grant change (UPDATE exists); RLS UPDATE policy is the same `today` rule. The PK column `instrument_token` is rewritten: safe only if no foreign key references the cycle PK (UNVERIFIED; read 1 below).
3. **Readers show the gap.** Fallback if the tape stream rejects 2: `/tape` marks the strike "remapped, no row", and the count stays on the metrics page.

Decision owed from the tape stream: semantics (the old token's row is replaced, not kept beside the new one). Engine view: option 2 is allowed under the S105 grants; it must not be built until read 1 shows no FK/trigger on the four tables, and the Saturday gate must include one deliberate remap row so the second statement is proven before a live day.

## E-1 pooler and server version

- Pooler: Supavisor, session mode, `aws-1-ap-southeast-2.pooler.supabase.com:5432` (docs). A session-mode pooler holds one backend per client, so backend ErrorResponse (SQLSTATE) and CommandComplete (`INSERT 0 n`) messages are forwarded by design. **UNVERIFIED on this project.** Supavisor also raises its own errors (pool or client limits) that are not Postgres SQLSTATEs; the writer must treat an error with no SQLSTATE as `connect`, not as 53300.
- 53300: `CONNECTION LIMIT 2` is enforced by Postgres, so a third `tape_w` session gets 53300 from the backend, unless Supavisor's own pool limit answers first. UNVERIFIED; settled by a three-session probe after the login proof.
- Server version: not in the docs. Inference: the grain constraints were read as `UNIQUE NULLS NOT DISTINCT`, which needs PG 15+. Confirm with read 1 (`server_version_num`).
- Probes that need no write (as `merdian_ro` through the pooler, `psql -X`, `\set VERBOSITY verbose`, `\timing on`): `select 1/0;` gives 22012; `set statement_timeout=100; select pg_sleep(1);` gives 57014. After the login proof, as `tape_w`: `delete from public.tape_live_label where false;` gives 42501 (privilege check precedes the WHERE). 25P03, 55P03 and 40P01 are left to the gate (two sessions needed).

## E-2 RLS "today" and the re-dated Saturday rows

- Ruling 3 states the policy expression as `trading_day = (now() AT TIME ZONE 'Asia/Kolkata')::date` on `tape_w_select/insert/update` (cycle, events, wall) and `tape_w_insert` (label). The 10-policy `pg_policies` read-back was never pasted (addendum §5), so the stored text is UNVERIFIED. Read 1 closes it.
- The policy tests `trading_day` only. Saturday rows with `trading_day` = that Saturday pass on that Saturday. `ts_ist`, `as_of` later than `now()` and `expiry < trading_day` are not tested by anything in the docs. Only known CHECKs: label `wall`, `leg`, `label` values; cycle/events `leg IN ('CE','PE')`. Whether other CHECKs or triggers exist is UNVERIFIED; read 1.
- `now()` is transaction start, so the 15:46 IST final write is inside the day. IST midnight is untested (plan §14).

## E-4 `data_contracts`

- Ruling 6: the 8 rows go in on the writer-start day after both symbols have rows. Before that, the tape products have no contract row, so a checker that iterates `data_contracts` has nothing to alert on for gate rows. Whether any other check compares tables to contracts is UNVERIFIED: `grep -rln expected_per_cycle ~/meridian-engine --include=*.py` and read what it does with `rows [min,max]`.
- Ceilings (recommendation, provisional): `rows.min = 0` on cycle, events and wall, because the writer sends changes only and a quiet cycle can be a handful of rows; a nonzero min would raise a false MISSING. `rows.max` must clear a restart or bump cycle: base state about 15,525 rows, largest observed cycle 11,893. Start at 30,000 on cycle, then tighten from `cycle_health` (ruling 6). If the checker counts per symbol, halve nothing: keep the same figure until read.

## E-5 write-path size limits

- Postgres has no statement-size limit below 1 GB. The binding limits are `statement_timeout 15s` per statement and `lock_timeout 5s` (SET LOCAL). Supavisor message-size limits: UNVERIFIED.
- A 12,000-row cycle at N=500 is 24 statements in one transaction; `idle_in_transaction_session_timeout 10s` is safe only while psql streams without pauses. Keep N=500; raise to 1,000 only if the gate shows max statement time under 2 s (deliverable 3).

## E-6 DDL comment

Replace `as_of (writer clock, UTC)` (ddl.py:81) with:
`as_of: tape-live cycle at which this row's value last changed (timestamptz instant). Not the send time: a row sent late after a skipped write or restart keeps its original as_of.`
List the columns carrying the old text first (read 2). The comment is applied as `COMMENT ON COLUMN public.<table>.as_of IS '<text>';` by the engine stream, one per table that has it.

## Reads (read-only, SQL editor or `merdian_ro`)

Read 1, version, constraints, triggers, foreign keys, policies:
```sql
select 'ver' k, 'server' t, current_setting('server_version_num') n, version() d
union all select 'con', conrelid::regclass::text, conname::text, pg_get_constraintdef(oid)
  from pg_constraint where conrelid in ('public.tape_live_cycle'::regclass,'public.tape_live_events'::regclass,'public.tape_live_wall'::regclass,'public.tape_live_label'::regclass)
  or confrelid in ('public.tape_live_cycle'::regclass,'public.tape_live_events'::regclass,'public.tape_live_wall'::regclass,'public.tape_live_label'::regclass)
union all select 'trg', tgrelid::regclass::text, tgname::text, pg_get_triggerdef(oid)
  from pg_trigger where not tgisinternal and tgrelid in ('public.tape_live_cycle'::regclass,'public.tape_live_events'::regclass,'public.tape_live_wall'::regclass,'public.tape_live_label'::regclass)
union all select 'pol', tablename::text, policyname::text, 'cmd='||cmd||' roles='||roles::text||' qual='||coalesce(qual,'')||' check='||coalesce(with_check,'')
  from pg_policies where tablename like 'tape_live_%'
order by 1,2,3;
```
Expect 10 `pol` rows for `tape_w_*`.

Read 2, columns carrying `as_of` and their comments:
```sql
select c.relname, a.attname, col_description(c.oid, a.attnum) as comment
from pg_attribute a join pg_class c on c.oid = a.attrelid
where c.relname like 'tape_live_%' and a.attname = 'as_of' and not a.attisdropped;
```

## Deliverables

**(1) `tape_w` password script**: `tape_w_password.py` (delivered with this answer). Run as `tapelive` after `/etc/tape-live/` exists. Gap found: `/etc/tape-live/` is root 755, so `tapelive` cannot create the file. Root pre-creates it once:
`sudo install -m 600 -o tapelive -g tapelive /dev/null /etc/tape-live/tape-w.env`
The script refuses if the file is absent, not owned by the user, not mode 600, or non-empty (rotation needs `--rotate`). It derives host, port, db, query and the `.<ref>` suffix from `TAPE_LIVE_RO_DSN` without printing them, writes `TAPE_LIVE_W_DSN=` with a 40-character alphanumeric password, and prints only `ALTER ROLE tape_w PASSWORD '<SCRAM-SHA-256 verifier>';` for the operator. Tested here against a temporary file: mode 600, the stored key matches the password, the second run refused. Not tested against the real pooler: the login proof does that.

**(2) Gate-row cleanup** (as `postgres`; edit the date only):
```sql
begin;
set local statement_timeout = '120s';
do $$
declare
  d date := date '2026-11-21';  -- EDIT: gate date
  t text; b bigint; a bigint; ob bigint; oa bigint;
  tabs text[] := array['tape_live_cycle','tape_live_events','tape_live_wall','tape_live_label'];
begin
  if extract(isodow from d) not in (6,7) then
    raise exception 'REFUSED: % is a weekday', d;
  end if;
  foreach t in array tabs loop
    execute format('select count(*) from public.%I where trading_day = $1', t) into b using d;
    execute format('select count(*) from public.%I where trading_day <> $1', t) into ob using d;
    execute format('delete from public.%I where trading_day = $1', t) using d;
    execute format('select count(*) from public.%I where trading_day = $1', t) into a using d;
    execute format('select count(*) from public.%I where trading_day <> $1', t) into oa using d;
    if oa <> ob then raise exception 'REFUSED: other days changed in % (% -> %)', t, ob, oa; end if;
    raise notice '% | gate day before % after % | other days before % after %', t, b, a, ob, oa;
  end loop;
end $$;
commit;
```
Special-session guard: the weekday refusal covers Saturday and Sunday only. A special Saturday or Sunday session is not covered; the calendar table name is not in the docs. Find it with `select table_name from information_schema.tables where table_schema='public' and table_name ilike '%calendar%' or table_name ilike '%holiday%';` and the guard gets one more line once named. Until then the operator checks the date against the exchange circular.

**(3) `pg_stat_statements` read** (run before and after a gate run; subtract by hand; no reset):
```sql
select s.calls, round(s.total_exec_time::numeric,1) as total_ms, round(s.mean_exec_time::numeric,2) as mean_ms,
       round(s.max_exec_time::numeric,1) as max_ms, s.rows, left(regexp_replace(s.query,'\s+',' ','g'),110) as q
from pg_stat_statements s join pg_roles r on r.oid = s.userid
where r.rolname = 'tape_w' order by s.total_exec_time desc limit 30;
```
Multi-row VALUES lists of different lengths can appear as separate entries.

**(4) Lock-wait sampling** (repeat during the heavy cycles; `\watch 1` in psql as `postgres`):
```sql
select now() at time zone 'Asia/Kolkata' as ts_ist, pid, state, wait_event, now() - query_start as running,
       pg_blocking_pids(pid) as blocked_by, left(query,80) as q
from pg_stat_activity where usename = 'tape_w' and wait_event_type = 'Lock';
```

## Still owed from the engine stream
- `pg_policies` read-back for S105 (read 1), V1/V4, then V2, V3, V5 and the login proof after the password step.
- Bucket-scoped S3 policy for the box role, the parity-target engine note, `merdian_ro` `default_transaction_read_only` (R-2): unchanged, not touched here.
