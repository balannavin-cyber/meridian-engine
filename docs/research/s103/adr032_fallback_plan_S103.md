# ADR-032 D2–D4 — fallback and recovery plan (DRAFT for ruling, S103, 2026-10-31)

Companion to `claude/adr032_s5_s6_impact_study_S103.md` (rulings S103-P…T: additive new per-1 % columns, dated unit break, no history
conversion). Purpose: **at every stage there is a named last-known-good state, a tripwire that says "stop", and a recovery that has
been written and rehearsed before the forward step is issued.** The system is close to launch; D1 (the per-1 % board display) is
already live, so **nothing launch-visible depends on D2–D5** — which is why this plan can afford to be strict.

## 1. Principles

1. **Additive, dark, then lit.** Every stage adds something beside the old thing; the old thing keeps working and keeps being
   read until a later stage retires it. The old columns, the old views and the board are not touched until S3, and the old columns
   are not removed before S5.
2. **Rollback is written before the forward step is issued.** For each step I produce its refusing rollback block, the verification
   that proves the restore, and the rehearsal — and I hand over the rollback in a **separate message** from the forward step
   (standing rule). This document describes recoveries in words and names; the paste-ready blocks are produced per step.
3. **A recovery is proved by an identity, not by a feeling:** a view or function is restored when its `md5(pg_get_viewdef)` /
   `md5(prosrc)` equals the captured value (study §4); code is restored when `git rev-parse` and `sha256sum` equal the tag;
   data is untouched when the control totals equal (K3).
4. **One change per stage, one stage per window, one observed session between stages.** No stage ends in a state nobody has watched
   across a market open.
5. **Writers change only in the S90-J window** (weekdays 16:30 → 07:45 IST, any time on weekends and holidays). The first live
   observation of a writer change is therefore a **Monday open**, with the weekend available to undo it.

## 2. The recovery kit — built once, before S1 (stage F0)

| # | Item | What it is | How recovery uses it |
|---|---|---|---|
| K1 | **Code tags** | annotated tag `adr032-pre` on engine `c11b564` (box route, `~/meridian-cc`); the board's rollback is the copy `promote` makes of live each time (live is `6f14a92`; its rollback target is `/var/www/marketview.bak-2f3c2f0`, proven identical before the switch) | a revert is a **new commit** on `main` pulled `--ff-only` (never a reset, never a force push); the tag is the comparison point |
| K2 | **Definitions snapshot** | one SQL file `sql/snapshots/adr032_pre_defs_<date>.sql` holding `pg_get_viewdef` / `pg_get_functiondef` for every Γ object (study §4 list, `p3b_sweep`, `backfill_pin_maxpain_runs`, `v_close_print`, the seven `_1pct` wrappers) plus each table's column list — committed to the engine repo, so a rebuild source exists in git | restoring any object = running its block from this file; proof = md5 equals study §4 |
| K3 | **Control totals of the past** | for each Γ table and each of the last 5 sessions, per symbol: `count(*)`, `sum(gex_cr)` / `sum(net_gex)`, `max(ts)`, saved as a text file | past rows are immutable under this plan: after **every** stage the totals for those dates must be byte-identical; a mismatch means a stage touched history — stop |
| K4 | **Crontab and registers** | `docs/registers/aws_crontab.txt` = the live crontab (verified at S102); no stage edits cron | nothing to restore; checked unchanged after each stage |
| K5 | **LKG ledger** | a short table in the session record: stage, time, git sha, md5 set, K3 checksum, who verified | the row above the failing stage is the target of any recovery |
| K6 | **Kill switch for the writer** | a **code constant** `GEX_1PCT_WRITE_ENABLED` (not a database parameter — risk #14 in the agentic roadmap §11: a parameter read can fail open), shipped `False`, flipped by a one-line commit | turns the new columns off in minutes without touching schema |
| K7 | **Rehearsal by transaction** | PostgreSQL DDL is transactional: each DDL block is first run as `BEGIN; … verification SELECTs …; ROLLBACK;` in **one** editor execution (the editor opens a new session per run), then run again ending in `COMMIT;` | shows the verification output before anything persists; `SET LOCAL lock_timeout = '3s'` makes a blocked `ALTER` fail instead of queuing behind a long transaction and stalling the capture writers |
| K8 | **Small-table copies before S5 only** | `CREATE TABLE … AS` copies of the old Γ columns for the small tables (≤ 184k rows each) | the only step with a data-shaped recovery; see S5 |

## 3. Stage ladder

| Stage | Change | Blast radius | Tripwire (stop and recover if…) | Recovery | Data lost / time |
|---|---|---|---|---|---|
| **F0** | the kit above; nothing changes | none | K3 or K2 cannot be produced | — | none |
| **S1** | SQL + docs only: unit COMMENTs on the Γ columns (none exist today); the dated unit-break record (one row per Γ column: "before T scale A, from T scale B", T unset until S2c); register and manual text; no code | metadata | the verification SELECT does not return the rows written | `COMMENT … IS NULL`; delete the rows; revert the docs commit | none / minutes |
| **S2a** | operator DDL: add **nullable** per-1 % columns (`gex_cr_1pct`, `net_gex_1pct`, `gamma_at_pin_1pct`, `peak_pin_gex_cr_1pct` — final list per S103-P) to the primary tables, inside the K7 transaction with `lock_timeout` | brief lock per table; `ADD COLUMN` without a default is metadata-only, even on `gex_strike_snapshots` (2.1M rows) | any `55P03` lock timeout (re-run later); capture rows per cycle drop; a wrapper or view changes shape | `DROP COLUMN` of the new columns only (same lock care); old columns never touched | none / minutes |
| **S2b** | **dark deploy**: the writer bundle (W1 + every formula copy W6 + the new invariants) with `GEX_1PCT_WRITE_ENABLED = False`; offline suite + golden replay 486/486 **bit-identical** before and after | the capture path (window only) | suite red; any golden-replay difference; the first live cycle's old columns differ from the day before's pattern | revert commit, pull `--ff-only`; `git rev-parse` = `adr032-pre` tree for the touched files | none / ~10 min |
| **S2c** | **light**: a one-line commit flips the constant `True`; the first valid `ts` of each new column is recorded as T in the S1 record | capture path (window only) | every cycle, every row: `new ≠ round(0.01 × old, tol)`; the new invariant (Σ strikes = net, per 1 %) fails; cycle lag (`created_at − ts`) median > baseline + 20 s or any run > 60 s; a writer ledger exit ≠ 0; the 14:00 ENH-133 cycle `57014`; row counts per cycle change | flip `False` (second one-line commit) **or** revert; new columns keep whatever was written (NULL after the flip) — harmless, T is re-registered | none (old columns authoritative) / ~10 min |
| **S3** | optional: repoint the seven `_1pct` wrappers from `col × 0.01` to the stored new columns, in **one** `BEGIN; DROP VIEW …; CREATE VIEW …; COMMIT;` (readers wait on the lock and then see the new definition: no gap). Needed because two wrappers are `SELECT t.*, …` over tables — `CREATE OR REPLACE` cannot insert a column in the middle. The other five wrap **views**: first append the per-1 % column to each source view (append-only `CREATE OR REPLACE`, allowed), then redefine the wrapper | the board reads these views | per-view identity `old × 0.01 = new` on **every** row of the latest run; the `/staging/` read; md5 re-capture | re-run the K2 block for each wrapper; md5 equals study §4 | none / minutes |
| **S4a** | `v_dealer_flow_sim` factor (`pct / 0.01` against the per-1 % column) | the Hedge tile | `flow_cr` at ±1 % ≠ ∓ per-1 % net on the same run | restore the K2 definition; md5 `166948d6…` | none / minutes |
| **S4b** | `p3b_sweep()` and P3a: recompute the new columns' invariant with a re-derived tolerance; the old invariant keeps running on the old columns | the nightly invariant job (`pg_cron` `p3b_invariants`) | a mutant that perturbs by 0.5 % must still FAIL; a run with `SWEEP_ERROR` | restore the K2 function; md5 `af57a99c…`; cron untouched | none / minutes |
| **S4c** | Pine overlay labels (`generate_pine_overlay.py`): per-1 % with the unit named | the TradingView overlay text | before/after diff on one run differs beyond the label | revert the commit | none / minutes |
| **S4d** | contract v3, goldens regenerated, retail re-pin | `merdian_compute` consumers | retail L1/L4 not bit-identical | **retail is never forced to move**: its engine pin stays at the old SHA until it chooses; the old contract version stays valid because the old columns and old function outputs are unchanged | none / n.a. |
| **S5** | retire old columns and old wrappers — **post-launch only, after a stated quiet period** | every reader of an old column | any reader still names an old column (the sweep's list is the checklist); `pg_stat_statements` shows calls | the only stage with a data-shaped recovery: old = new × 100 (exact to float precision, and the registered break says which rows), plus the K8 copies | none by design / ~hours |

## 4. Abort rules (stop-ship), decided before anyone is tired

- **Any tripwire in §3 = stop, recover to the last LKG row, and only then diagnose.** No forward repair on a live capture path.
- **No stage is started** unless the previous stage has been observed across one full market session with the tripwires clean, and
  K3 matches.
- **Proposed emergency lever (needs a ruling):** because capture-path changes are barred in market hours, flipping the dark/light
  constant to `False` is pre-authorised as the single permitted in-session action, by the operator, with the commit message
  `EMERGENCY ADR-032 flag off`. Everything else waits for the window.
- A failed K7 rehearsal is not retried "to see"; it is diagnosed offline.

## 5. What is deliberately not in this plan

- **No in-place factor change** and **no history conversion** (rulings S103-P, S103-Q).
- **No retail change** and no retirement of the legacy objects — both wait for the sweeps (the engine-box and retail-box CC prompts,
  `claude/cc_prompt_adr032_sweep_engine_box.md`, `…_retail_box.md`) and for the other Lovable apps on this database to be checked.

## 6. Launch gate (ruling owed: the launch date)

My recommendation: **run F0 and S1 now** (metadata and documents only, no capture path); **hold S2 onward until after launch**
unless at least **two full trading weeks** of quiet remain between the S2c flip and launch — D1 already gives users the corrected
numbers, and D2 adds capability, not correctness. If launch is nearer than that, the sweeps and this plan still pay for themselves:
the later change then starts from a checked inventory and a rehearsed recovery.
