# S104 session prompt (carry-forward from S103, written 2026-10-31 ~09:11 IST; commands appendix added 09:20)

Read first, in this order: `claude/S103_close_inputs.md` (state, facts, Monday checks, TDs to file), `claude/adr032_f0_k1_k3_records_2026-10-31.md` (K1/K2/K3 + S1 record), `claude/adr032_fallback_plan_S103.md`, `claude/adr032_s5_s6_impact_study_S103.md`, `claude/rulings_s103.md` + `claude/rulings_s103_addendum_rounds_2_3.md`. **All commands and queries named below are in the Appendix at the end of this file.**

Standing rules from the operator: session close is when he says "we close" — do not remind; read the project docs before asking him to check anything; never mention sleep/rest or suggest pausing; rollbacks go in a separate message from the forward step, as refusing blocks; one step at a time with hashes; tracker §2.2 order first (agentic harness Stages 3–6 stay ON HOLD per S99-D).

## Actions, in order

1. **Close the ADR-032 S1 database state (first).** At 09:11 the comments were all NULL except `gex_cr`, which had just been restored to its original sign note. Ask for the output of the 8-column comment read (Appendix A1) before assuming anything. If still NULL: step B = paste the committed `sql/2026-10-31_s103_adr032_s1_unit_comments.sql` (repo, project `claude/2026-10-31_s103_adr032_s1_unit_comments.sql`, or Downloads) into the SQL editor and run it; step C = Appendix A3 (`adr032_comments = 8` and `gex_cr_unit_and_sign_note = true`). If `gex_cr` is NULL again, run A2 first (the S1 pre-check refuses otherwise). The superseded first rollback block must never be run again; the only valid S1 rollback is Appendix A4. Record the result in the F0 record.
2. **Local pull check:** all four trees were at `8b58e54` at 09:06; confirm nothing moved.
3. **Monday 2026-11-02 live checks** (S103_close_inputs §5), reading the first full session after the s103v deploy. Run no fixture suite 08:30–15:40 IST on weekdays (rule 23); deploy window weekdays 16:30→07:45 IST (S90-J).
4. **CC sweeps (read-only), not yet started:** step 1 = Appendix A6 (upload, hashes begin `3729e9ac…` engine / `c9343152…` retail). Steps 2+ (box fetch to `~/meridian-cc/scratch/s103_sweep/`, the retail box for the retail prompt, Claude Code in tmux, Phase 1 blind, Phase 2 diff against the study) are NOT yet written as commands; produce them one at a time. Their output gates ADR-032 S2: who else reads the Γ objects, the retail repos' use of the unit, the `service_role` reader of `wcb_signal_validation_v2` / `latest_signal_snapshots`.
5. **Tuesday 2026-11-03:** read the S103-C expiry branch before 15:30; build S103-B (board leg roll) after 15:40.
6. **Tracker §2.2 remainder:** B2 remainder (R5/R38 live reads), BS-1 credential rotations and port 22 (operator actions; TD-S101-NEW-10, TD-S99-NEW-1), B3 chain data correctness, TD-S101-NEW-4 other half (`recent_max_strikes` second prior-row read unbounded), manual option B timing (owed ruling).
7. **ADR-032 build** — only after launch and the sweeps: S2a–S2c per the fallback plan; after each stage re-run the K3 queries (A5) and compare to the F0 record; rule the emergency lever then (proposed: valid only at S2b–S2c; from S3 the recovery is the SQL wrapper revert). The dated unit-break row is written at S2c when T exists.
8. **Doc-close of S103 (only when the operator says):** merge the addendum into `rulings_s103.md`; file the TDs and the §D.57 items listed in S103_close_inputs §4; update the register, `CURRENT.md`, `session_log.md`.

## Open questions needing the operator
- Launch date (given as "maybe in 10 days"; exact date unknown).
- Identity of the `service_role` reader of `wcb_signal_validation_v2` / `latest_signal_snapshots` (candidates: the Lovable apps Live Sheet Sync, Market Breadth View, Sheet Sync Live, or a sheet-sync script).
- Wording of the Pine overlay labels (S103-S) when that round is built.

---

# Appendix — commands and queries (exact text used in S103)

## A1. Read the 8 S1 comment states (read-only)
```sql
select c.relname as tbl, a.attname as col, col_description(c.oid, a.attnum) as comment
from pg_class c
join pg_namespace s on s.oid = c.relnamespace and s.nspname = 'public'
join pg_attribute a on a.attrelid = c.oid and not a.attisdropped
where (c.relname, a.attname) in (
  ('gex_strike_snapshots','gex_cr'), ('gamma_metrics','net_gex'),
  ('gex_cycle_history','net_gex'), ('gex_cycle_history','gamma_at_pin'),
  ('gex_pin_maxpain_history','peak_pin_gex_cr'),
  ('signal_snapshots','net_gex'), ('structural_divergence_snapshots','net_gex'),
  ('hist_gamma_metrics','net_gex'))
order by 1, 2;
```
Applied state = all 8 start `ADR-032:`; `gex_cr` ends with the original sign note.

## A2. Step A — restore the original gex_cr sign note (only if gex_cr is NULL; refuses otherwise)
```sql
BEGIN;
SET LOCAL lock_timeout = '3s';
DO $$
BEGIN
  IF col_description('public.gex_strike_snapshots'::regclass,
       (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.gex_strike_snapshots'::regclass AND attname = 'gex_cr')) IS NOT NULL
  THEN RAISE EXCEPTION 'REFUSE: gex_cr already carries a comment'; END IF;
  COMMENT ON COLUMN public.gex_strike_snapshots.gex_cr IS
    'Signed Cr. Positive=dampening (dealer long). Negative=amplifying (dealer short).';
END $$;
SELECT col_description('public.gex_strike_snapshots'::regclass,
  (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.gex_strike_snapshots'::regclass AND attname = 'gex_cr')) AS gex_cr_comment;
COMMIT;
```
Original text: `Signed Cr. Positive=dampening (dealer long). Negative=amplifying (dealer short).`

## A3. Step C — verify S1 (separate execution after the apply)
```sql
select
  (select count(*) from pg_description d
    where d.classoid = 'pg_class'::regclass and d.objsubid > 0 and d.description like 'ADR-032:%') as adr032_comments,
  (col_description('public.gex_strike_snapshots'::regclass,
     (select attnum from pg_attribute where attrelid = 'public.gex_strike_snapshots'::regclass and attname = 'gex_cr'))
   like 'ADR-032:%Signed Cr. Positive=dampening (dealer long). Negative=amplifying (dealer short).') as gex_cr_unit_and_sign_note;
```
Pass: `adr032_comments = 8`, `gex_cr_unit_and_sign_note = true`. (Optional data-untouched check: `select count(*) from public.gex_strike_snapshots where symbol in ('NIFTY','SENSEX') and ts >= '2026-10-30 00:00+05:30' and ts < '2026-10-31 00:00+05:30'` = 23080.)

## A4. The ONLY valid S1 rollback (restores the gex_cr sign note exactly; removes only comments still starting "ADR-032:")
```sql
BEGIN;
SET LOCAL lock_timeout = '3s';
DO $$
DECLARE r record; n int := 0;
BEGIN
  FOR r IN SELECT * FROM (VALUES
    ('gamma_metrics','net_gex'),('gex_cycle_history','net_gex'),('gex_cycle_history','gamma_at_pin'),
    ('gex_pin_maxpain_history','peak_pin_gex_cr'),('signal_snapshots','net_gex'),
    ('structural_divergence_snapshots','net_gex'),('hist_gamma_metrics','net_gex')) v(t,c)
  LOOP
    IF (SELECT col_description(format('public.%I', r.t)::regclass::oid, a.attnum)
          FROM pg_attribute a WHERE a.attrelid = format('public.%I', r.t)::regclass AND a.attname = r.c) LIKE 'ADR-032:%'
    THEN EXECUTE format('COMMENT ON COLUMN public.%I.%I IS NULL', r.t, r.c); n := n + 1; END IF;
  END LOOP;
  IF (SELECT col_description('public.gex_strike_snapshots'::regclass, a.attnum)
        FROM pg_attribute a WHERE a.attrelid = 'public.gex_strike_snapshots'::regclass AND a.attname = 'gex_cr') LIKE 'ADR-032:%'
  THEN COMMENT ON COLUMN public.gex_strike_snapshots.gex_cr IS
       'Signed Cr. Positive=dampening (dealer long). Negative=amplifying (dealer short).';
       n := n + 1; END IF;
  RAISE NOTICE 'comments reverted: %', n;
END $$;
SELECT (SELECT count(*) FROM pg_description d WHERE d.classoid = 'pg_class'::regclass AND d.objsubid > 0 AND d.description LIKE 'ADR-032:%') AS adr032_comments_left,
       col_description('public.gex_strike_snapshots'::regclass,
         (SELECT attnum FROM pg_attribute WHERE attrelid = 'public.gex_strike_snapshots'::regclass AND attname = 'gex_cr')) AS gex_cr_comment;
COMMIT;
```
Pass after a rollback: `adr032_comments_left = 0` and `gex_cr_comment` = the original sign note. **Do not run any older rollback text.** (The first version had no `gex_cr_comment` column and NULLed `gex_cr`; running it after the apply removed all 8 comments at ~09:0x on 2026-10-31.)

## A5. K3 control-total queries (results must equal the F0 record after every ADR-032 stage; sessions 26–30 Oct 2026 are fixed history)
Part 1 (two big tables):
```sql
select 'gex_strike_snapshots' as tbl, symbol,
       (ts at time zone 'Asia/Kolkata')::date as ist_date,
       count(*) as n, sum(gex_cr::numeric)::text as sum_val, max(ts) as max_ts
from public.gex_strike_snapshots
where symbol in ('NIFTY','SENSEX')
  and ts >= '2026-10-26 00:00+05:30' and ts < '2026-10-31 00:00+05:30'
group by 2,3
union all
select 'gamma_metrics', symbol,
       (ts at time zone 'Asia/Kolkata')::date,
       count(*), sum(net_gex::numeric)::text, max(ts)
from public.gamma_metrics
where symbol in ('NIFTY','SENSEX')
  and ts >= '2026-10-26 00:00+05:30' and ts < '2026-10-31 00:00+05:30'
group by 2,3
order by 1,2,3;
```
Part 2 (other Γ tables; `market_state_snapshots` compared by md5 of its stored JSON):
```sql
select 'gex_cycle_history.net_gex' as tbl, symbol, (ts at time zone 'Asia/Kolkata')::date as ist_date,
       count(*) as n, sum(net_gex::numeric)::text as sum_val, max(ts) as max_ts
from public.gex_cycle_history
where symbol in ('NIFTY','SENSEX') and ts >= '2026-10-26 00:00+05:30' and ts < '2026-10-31 00:00+05:30'
group by 2,3
union all
select 'gex_cycle_history.gamma_at_pin', symbol, (ts at time zone 'Asia/Kolkata')::date,
       count(*), sum(gamma_at_pin::numeric)::text, max(ts)
from public.gex_cycle_history
where symbol in ('NIFTY','SENSEX') and ts >= '2026-10-26 00:00+05:30' and ts < '2026-10-31 00:00+05:30'
group by 2,3
union all
select 'gex_pin_maxpain_history.peak_pin_gex_cr', symbol, (ts at time zone 'Asia/Kolkata')::date,
       count(*), sum(peak_pin_gex_cr::numeric)::text, max(ts)
from public.gex_pin_maxpain_history
where symbol in ('NIFTY','SENSEX') and ts >= '2026-10-26 00:00+05:30' and ts < '2026-10-31 00:00+05:30'
group by 2,3
union all
select 'signal_snapshots.net_gex', symbol, (ts at time zone 'Asia/Kolkata')::date,
       count(*), sum(net_gex::numeric)::text, max(ts)
from public.signal_snapshots
where symbol in ('NIFTY','SENSEX') and ts >= '2026-10-26 00:00+05:30' and ts < '2026-10-31 00:00+05:30'
group by 2,3
union all
select 'structural_divergence_snapshots.net_gex', symbol, (ts at time zone 'Asia/Kolkata')::date,
       count(*), sum(net_gex::numeric)::text, max(ts)
from public.structural_divergence_snapshots
where symbol in ('NIFTY','SENSEX') and ts >= '2026-10-26 00:00+05:30' and ts < '2026-10-31 00:00+05:30'
group by 2,3
union all
select 'market_state_snapshots.gamma_features(md5)', symbol, (ts at time zone 'Asia/Kolkata')::date,
       count(*), md5(string_agg(gamma_features::text, '|' order by id)), max(ts)
from public.market_state_snapshots
where symbol in ('NIFTY','SENSEX') and ts >= '2026-10-26 00:00+05:30' and ts < '2026-10-31 00:00+05:30'
group by 2,3
order by 1,2,3;
```
(The pin table returns no rows in this window by design; its real K3 is the whole-table total:)
```sql
select symbol, count(*) as n, sum(peak_pin_gex_cr::numeric)::text as sum_val,
       md5(string_agg(id::text || ':' || coalesce(peak_pin_gex_cr::text,''), '|' order by id)) as row_md5
from public.gex_pin_maxpain_history group by symbol order by symbol;
```

## A6. CC sweeps, step 1 — upload the two prompt files (PowerShell; assumes Downloads)
```powershell
$e = "$HOME\Downloads\cc_prompt_adr032_sweep_engine_box.md"
$r = "$HOME\Downloads\cc_prompt_adr032_sweep_retail_box.md"
(Get-FileHash $e -Algorithm SHA256).Hash.ToLower()
(Get-FileHash $r -Algorithm SHA256).Hash.ToLower()
aws s3 cp $e s3://meridian-engine-deploy/s103/cc_prompt_adr032_sweep_engine_box.md
aws s3 cp $r s3://meridian-engine-deploy/s103/cc_prompt_adr032_sweep_retail_box.md
```
Hashes must begin `3729e9ac…` (engine) and `c9343152…` (retail). Status at 09:20: NOT yet run by the operator.

## A7. Box route for committing a file to the engine repo (pattern used for `4e14a1d` and `8b58e54`)
PowerShell: `Get-FileHash` the file, `aws s3 cp` it to `s3://meridian-engine-deploy/s103/`. Box (`~/meridian-cc`): refuse unless `HEAD` equals the expected parent; `aws s3 cp` to `scratch/`; refuse on sha256 mismatch; refuse if the target exists; `cp` into place; write the message to `scratch/msg_*.txt` (ending with the attribution trailer lines the session was given); `git add -- <path>` then `git commit -F scratch/msg_*.txt -- <path>` then `git push origin HEAD:main`; then `cd ~/meridian-engine && git pull --ff-only`; Local: `cd C:\GammaEnginePython; git pull --ff-only; git rev-parse HEAD`. All four heads must be identical (compare the git hash, not file hashes, on Local: line-ending settings can alter checked-out files).
