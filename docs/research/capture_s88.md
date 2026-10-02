# MERDIAN capture — Session 88 (2026-10-01)

> Session capture. §1 only at the time of writing; later sections are appended, never
> inserted above an existing one, so the path:line citations below stay resolvable.
>
> **Citation discipline.** Every figure in §1 and §2 carries the `scratch/` path and line it
> was read from. Nothing here was written from memory or from the operator's prompt. The one
> exception is §2.4, which is **operator-measured** through the Supabase editor and is
> labelled as such throughout — this session could not run it, because `merdian_ro` cannot
> `SET ROLE anon`. The cited `scratch/s88_l9/*.out` and `scratch/s88_design/*.out` files are frozen —
> written once, never edited above a cited line — which is the condition that makes a line
> citation stable at all (CLAUDE.md, §D.40.6).

---

## §1 L9 stage-1 max-pain — SENSEX expiry-day replication (2026-10-01)

### §1.1 Scope

> **This is a SENSEX replication of the S82 SENSEX PASS under expiry-day conditions; it does
> NOT close TD-S80-NEW-1 — the NIFTY arm remains owed (next NIFTY expiry Tue 2026-10-06).**

The scope statement is reproduced verbatim as given. **The 2026-10-06 date arrived
operator-supplied and has since been measured; it is correct.** At NIFTY's own latest
`option_chain_snapshots` ts, 2026-10-01 15:40:05 IST, the ladder is leg 1 = `2026-10-06`,
leg 2 = `2026-10-13` (`scratch/s88_design/nifty_front_expiry.out:5-6`), and resolving front
expiry by exactly the rule the live view uses returns `2026-10-06`
(`nifty_front_expiry.out:13`). `trading_calendar` carries 2026-10-06 as
`is_open = true, is_special_session = false` (`nifty_front_expiry.out:21`), so it is a
scheduleable session rather than a date the calendar would reject.

SENSEX's own second leg was `2026-10-08` in all three runs (`scratch/s88_l9/run1.out:23`,
`run2.out:24`, `run3.out:24`) — a different symbol's ladder, recorded so the two are not
confused.

`view_dte` read `0` in all three runs (`run1.out:26`, `run2.out:27`, `run3.out:27`), so the
expiry-day condition the replication claims is measured, not assumed.

### §1.2 Instrument — rebuilt, not reused

**The S82 two-armed instrument does not exist in this working tree.** `prereg.out:22` records
the finding. Searches that came back empty: `CAPTURED_BASELINE` across `scratch/` returns only
`tech_debt.md` backups; there is no `scratch/s82*` directory; no `.sql` under `scratch/`
mentions `max_pain` except the S83 L10 term-structure surface; and
`git log --all --diff-filter=A -- '*max_pain*'` lists only the four files already in `sql/`.
So the instrument was **rebuilt**, and this section says so rather than implying continuity
with S82 that does not exist.

Sources of the reconstruction, as recorded in `prereg.out`:

| Part | Source | sha256 |
|---|---|---|
| arm (b) body | `sql/2026-09-22_s81_v_max_pain_by_strike_CAPTURED_BASELINE.sql` | `4092ec19…33122a12` |
| arm (b) comparison form | §4b of `sql/2026-09-22_s81_v_max_pain_by_strike_latest_ts_retrofit.sql` | `c73441ef…05b736e30f` |
| arm (a) body | the **live** view, `pg_get_viewdef(public.v_max_pain_by_strike, true)` | captured to `scratch/s88_l9/_live_viewdef.sql` |

Arm (b) was recovered rather than re-derived: §4b of the retrofit file already carries the
baseline body inlined for exactly this comparison, commented out and unused since S81.

Built artefacts:

| File | sha256 | lines | cited at |
|---|---|---|---|
| `scratch/s88_l9/l9_rebuilt_source.sql` | `4dfd035601cb9ac1cdc927c703e3354514fd18213c679fd2b1ff26e4e0b2e6f1` | 342 | `prereg.out:17-18` |
| `scratch/s88_l9/l9_sensex.sql` | `9311db9111c8187297ec3d840f4598e75060eed25ca029a4533cfa68b8f0b0ce` | 342 | `prereg.out:14-15` |

**The diff between them is two lines, both in the `scope` CTE** —
`scratch/s88_l9/diff_source_to_sensex.out:7-10`:

```diff
-    SELECT 'NIFTY'::text  AS sym,
-           NULL::date     AS expect_w1
+    SELECT 'SENSEX'::text    AS sym,
+           DATE '2026-10-01' AS expect_w1
```

Those are `l9_rebuilt_source.sql:31-32` and `l9_sensex.sql:31-32`. Nothing else differs. The
source template's `NULL` `expect_w1` makes its own precondition false by construction, so the
template cannot be run as a test — deliberate, so that a run always carries a hand-supplied
W1 date rather than inheriting one.

*(`diff_source_to_sensex.out:1-2` are the `diff` header's mtimes, so that file's own hash is
not stable across regeneration. The two cited SQL files are the durable record.)*

### §1.3 Pre-registration

`scratch/s88_l9/prereg.out` — sha256
`5d20b95ba5553fb7eff586c7ae3bd8670f7bb8ee96765e6313785c40071994bf`, verified before each of
the three runs (`run1.out:9`, `run2.out:9`, `run3.out:9`).

**Verdict order, in words** (`prereg.out:65-70`), evaluated in exactly this sequence:

1. Precondition (P1 ∧ P2 ∧ P3) false → **NO-TEST**
2. Any tie count at minimum `total_pain` > 1 → **NO-TEST**
3. Arm A not 0/0 → **FAIL**
4. Arm B 0/0 → **NO-TEST**
5. Otherwise → **PASS**

So PASS requires all four: precondition holds, no body has a tie at the minimum, arm A is 0
in both directions, and arm B is non-zero. **Arm B 0/0 is NO-TEST, never PASS** — without
arm B, arm A passes even if the expiry filter does nothing.

**Two operator rulings were made before the stamp, and both were made before any OI or
expiry data had been read.** The only database access preceding the stamp was the
`pg_get_viewdef` call — catalog text only, no OI, no counts, no expiry data
(`prereg.out:31`). This matters: neither ruling could have been shaped by the numbers it
would go on to judge.

- **Ruling 1 — the tie clause gates both arms, and all three bodies are counted**
  (`prereg.out:76`). `max_pain_strike` is chosen by `row_number()` with no tie-break column,
  in the live view, in the captured baseline and therefore in the hand-pinned copy. A tie at
  the minimum can fake **arm A** (two evaluations of identical data breaking the tie
  differently — a FAIL for a reason the check does not name) and equally fake **arm B**
  (baseline and live breaking it differently makes `max_pain_strike` differ on every row — a
  PASS for a reason that is not the expiry mixture). The clause is evaluated before either
  arm is read, counts the hand-pinned body, the baseline body **and the live view**, and the
  three counts reach the output regardless.
- **Ruling 2 — P3 accepted as written** (`prereg.out:43`). P3 asserts that the
  independently derived leg 1 — min expiry at the latest `ts` with *no* horizon filter — is
  also 2026-10-01. It is an addition to the two clauses originally specified. Without it,
  P1 and P2 can both hold on a ladder of `{already-expired, 2026-10-01}`, and the mechanism
  block's "W2" would then be the front week itself: every W1-vs-W2 figure mislabelled while
  reading perfectly plausibly. P3 can only refuse a run, never manufacture a pass.

### §1.4 Results — one row per run

| Run | view `ts` IST | Precond | Ties hp/old/live | Arm A ↔ | Arm B ↔ | W2>W1 CE/PE | max_pain view/base/hand-pin | VERDICT |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-01 12:45:07 | true | 1 / 1 / 1 | 0 / 0 | 197 / 197 | 2 / 4 | 72200 / 72200 / 72200 | **PASS** |
| 2 | 2026-10-01 14:55:06 | true | 1 / 1 / 1 | 0 / 0 | 197 / 197 | 3 / 9 | 71800 / 71800 / 71800 | **PASS** |
| 3 | 2026-10-01 15:30:06 | true | 1 / 1 / 1 | 0 / 0 | 197 / 197 | 4 / 12 | 71900 / 71900 / 71900 | **PASS** |

Citations, by column and run (run 1 / run 2 / run 3):

| Column | run1.out | run2.out | run3.out |
|---|---|---|---|
| view `ts` IST | `:17` | `:18` | `:18` |
| P1 / P2 / P3 | `:28-30` | `:29-31` | `:29-31` |
| `PRECONDITION_OK` | `:31` | `:32` | `:32` |
| Arm A both ways | `:32-33` | `:33-34` | `:33-34` |
| Arm B both ways | `:34-35` | `:35-36` | `:35-36` |
| Ties hp / old / live | `:39-41` | `:40-42` | `:40-42` |
| W2>W1 CE / PE | `:46-47` | `:47-48` | `:47-48` |
| max_pain view / base / hand-pin | `:52-54` | `:53-55` | `:53-55` |
| VERDICT | `:55` | `:56` | `:56` |

Clock guards, all PASS: 12:49:13 against the 12:15 window (`run1.out:5`), 14:57:24 against
14:30 (`run2.out:5`), 15:34:32 against 15:15 (`run3.out:5`). Instrument hash verified at each
run (`run1.out:7`, `run2.out:7`, `run3.out:7`); no edits between runs. Each run is reported on
its own verdict; none is picked over another.

### §1.5 Reading — observations, bounded

**Arm B saturates at 197/197 and therefore cannot register how much the mixture grew.**
197/197 is *every* row, in all three runs (`run1.out:34-35`, `run2.out:35-36`,
`run3.out:35-36`). `total_pain` is a sum over the whole strike ladder, so any non-zero
perturbation at any strike moves every candidate's value, and the differing-row count tops
out. The growth is carried by the **mechanism block, not the row count**: shared strikes
where W2 OI exceeds W1 went 2+4 = **6** (`run1.out:46-47`) → 3+9 = **12**
(`run2.out:47-48`) → 4+12 = **16** (`run3.out:47-48`), while arm B sat still at 197/197
throughout. A verdict that read only the arm count would have reported these three runs as
identical.

**W2-only strikes were 0 in every run** (`run1.out:44`, `run2.out:45`, `run3.out:45`), so the
baseline's candidate-strike set equals the view's; W2 is a subset of W1 on this instrument.

**The mixture moved `total_pain` on every row and never moved `max_pain_strike`.** All three
bodies agree on the level within each run — 72200 (`run1.out:52-54`), 71800
(`run2.out:53-55`), 71900 (`run3.out:53-55`). Combined with W2-only = 0 and
`max_pain_strike` agreeing, the candidate sets and the level are identical across bodies, and
`side` is a pure function of those two — so all 197 differing rows differ in `total_pain`
alone. The 72200 → 71800 → 71900 walk is the market across the session, not a divergence
between bodies.

**Bounds, stated rather than left to inference.** One symbol. One expiry day. Three
snapshots. Arm B fired in all three, so the filter was exercised and these are tests rather
than NO-TESTs — but the defect's observable reach on this data is confined to `total_pain`,
and nothing here establishes what it does when W2 carries strikes W1 does not, when the
ladder is deeper than two legs, or on NIFTY.

### §1.6 For the doc-close — NOT written yet

Two lines are owed at close. They are named here so they are not lost, and neither has been
written: **no register was touched by this session.**

- **`docs/registers/tech_debt.md`, TD-S80-NEW-1 Status row** — add: SENSEX expiry-day
  replication of the stage-1 two-armed test PASSED ×3 on 2026-10-01 (12:45:07 / 14:55:06 /
  15:30:06 IST), instrument `scratch/s88_l9/l9_sensex.sql`
  `9311db91…68b8f0b0ce`, pre-registration `prereg.out` `5d20b95b…40071994bf`, detail in
  `docs/research/capture_s88.md` §1; **the NIFTY arm remains owed, next NIFTY expiry
  2026-10-06 — measured, `scratch/s88_design/nifty_front_expiry.out:5,13,21`.** Cite by entry
  ID and row name, not by line — `tech_debt.md` files new entries at the top.
- **System Map, §S88 line** — L9 stage-1 max-pain SENSEX expiry-day replication: 3 runs,
  3 PASS, arm A 0/0 and arm B 197/197 throughout; mixture measured on `total_pain` only,
  `max_pain_strike` unmoved; rebuilt instrument, S82's does not exist in the tree.

---

## §2 Parity board design — columns for the operator's four additions (R1–R4), measured 2026-10-01

### §2.1 Why

The operator approved design A–G at 13:04 IST with four additions: **R1** change marks on
spot, VIX and the other levels; **R2** futures with basis and its change versus the previous
session; **R3** the pre-market open; **R4** the gap up/down. Their source tables sit **outside
the 18-object render contract**, so none of their columns was covered by an existing binding.
They were therefore measured. Everything in §2.2–§2.3 carries the `scratch/s88_design/*.out`
path and line it was read from; §2.4 is operator-measured and labelled so.

### §2.2 Columns and access

| Table | Columns needed | RLS | anon SELECT |
|---|---|---|---|
| `index_futures_snapshots` | `ts` (`cols.out:40`), `symbol` (`:41`), `futures_price` (`:46`), `spot_price` (`:45`), `basis` (`:47`), `basis_pct` (`:48`), `contract_symbol` (`:42`), `expiry_date` (`:43`) | **off** (`cols.out:89`) | **yes** (`cols.out:148`) |
| `market_spot_snapshots` | all 8: `id, created_at, ts, symbol, spot, source_table, source_id, raw` (`cols.out:70-77`) | **off** (`cols.out:91`) | **yes** (`cols.out:150`) |
| `market_spot_session_markers` | all 18 (`cols.out:52-69`), incl. `prev_close_spot`, `premarket_ref_ts/_spot`, `open_0915_ts/_spot`, `close_1530_ts/_spot`, `gap_open_pct`, `capture_quality` | **on** (`cols.out:90`) | **yes** (`cols.out:149`) |

`market_spot_snapshots` has **0 policies** (`cols.out:100`). `market_spot_session_markers` has
**one** policy, `market_spot_session_markers_anon_read`, `TO anon`, SELECT, permissive,
`USING true` (`cols.out:99`, `cols.out:107`).

`source_table` values in the 09:00–09:20 IST window, both days:

| Day | `dhan_idx_i` | `dhan_charts_intraday` |
|---|---|---|
| 2026-10-01 | 09:11:03 only (`cols.out:222`, rows `:204`/`:209`) | 09:16:02 → 09:19:04, 8 rows (`cols.out:221`, rows `:205-208`/`:210-213`) |
| 2026-09-30 | 09:11:04 (`cols.out:262-263`) | 09:16:04 → 09:19:03 (`cols.out:264-271`) |

**`merdian_ro` is blind to `market_spot_session_markers` — TD-S81-NEW-16.** The read returned
**0 rows** (`cols.out:232`). That is not empty: the 3c2 control reads the **same two dates**
from a non-RLS table and returns **362 / 361** rows for 09-30 and **237 / 237** for 10-01
(`cols.out:240-243`). The zero is a property of the reader. Consequence for the board:
`prev_close_spot`, `open_0915_spot` and `premarket_ref_spot` exist as columns but their
**population is unmeasurable by this session's reader** — which is why §2.4 exists.

### §2.3 Findings

**(a) The pre-open print is `dhan_idx_i` at 09:11:03–04 IST on both days, both symbols.**
2026-09-30: NIFTY and SENSEX at 09:11:04 (`cols.out:262`, `:263`). 2026-10-01: both at
09:11:03 (`cols.out:280`, `:281`). **No `market_spot_snapshots` row exists between 09:00 and
09:11 on either day** — both 09:00–09:20 windows returned 10 rows against `LIMIT 20`, so
neither was truncated, and the window totals 2 + 8 = 10 (`cols.out:221-222`), with the
earliest row on each day at 09:11 (`cols.out:204`/`:209` today, `:262-263` previous).
n = 2 sessions; no mechanism is claimed *from this data*. See §2.5 (iii), where the register
supplies one.

**(b) No 09:15 row exists.** The first post-open row is the **09:16 `dhan_charts_intraday`
bar**, whose top-level `spot` carries `ohlc_close`; the bar's open is `raw->>'ohlc_open'`
(`cols.out:205`, full key list `cols.out:221`). A consumer reading `spot` at 09:16 gets the
bar **close**, and the open is one level down in jsonb under a different key, on a row stamped
a minute after the open.

**(c) The futures rows are the October monthly, not the options weekly.** NIFTY
`expiry_date` 2026-10-27, SENSEX 2026-10-29, both sessions (`cols.out:192-195`), while
SENSEX's option front expiry that day was 2026-10-01 (§1.4). **The two are different ladders
and must not be joined as one.** A **16:00:06 post-close row exists** on 09-30 — NIFTY
`basis` **79.54999999999927**, SENSEX **519.7100000000064** (`cols.out:192`, `:193`); the
operator's 79.55 / 519.71 are those values rounded. Because that row is post-close, **R2's
previous-session baseline must be the last row at or before 15:30**, not the last row of the
day. `expiry_type` is **empty on all four sampled rows** (`cols.out:192-195`), so contract
identity comes from `contract_symbol` + `expiry_date`; note the SENSEX value carries a
**double space**, `SENSEX OCT  FUT`.

**(d) `gamma_metrics` `vix` is 13.49 for both symbols at the identical ts** 2026-09-30
15:40:05 (`cols.out:251`, `:252`) — one series written against two symbol rows. Expected if
it means India VIX for both; indistinguishable by this reading from a SENSEX row carrying a
NIFTY-derived value.

**(e) `anon` holds `MAINTAIN` beyond `SELECT` on two of the three tables** —
`index_futures_snapshots` (`cols.out:125`) and `market_spot_snapshots` (`cols.out:135`), while
`market_spot_session_markers` has `SELECT` only (`cols.out:130`). **Grant hygiene, not an open
door:** `anon` holds no write privilege on any of the three.

**(f) `merdian_reference.json` Rule 17 is stale on the column point.** The rule
(`governance_rules.rule_17_market_spot_session_markers_column_mismatch.rule`) states
*"`open_0915` does not exist in production. Live column is `open_0915_ts`."* Measured: a column
named `open_0915` indeed does not exist, so the first clause holds — but **`open_0915_spot`
exists too** (`cols.out:60`), alongside `prev_close_spot` (`:56`), `premarket_ref_spot` (`:58`)
and `gap_open_pct` (`:65`). The rule names `open_0915_ts` as *the* live column, singular, and
that is the stale part: the price and the gap are both present as columns. Whether they are
*populated* is §2.4's question, not this one. The same rule also appears as Rule 17 in
`CLAUDE.md`; a correction has to land in both.

### §2.4 OPERATOR-MEASURED — Supabase editor, not this session

> **OPERATOR-MEASURED.** Single run, `SET LOCAL ROLE anon`, ~13:25 IST 2026-10-01, Supabase
> SQL editor. **This session could not run it:** `merdian_ro` cannot `SET ROLE anon`
> (`permission denied`), which is why §2.2's anon column is privilege-and-policy state rather
> than an exercised read. These figures carry **no `scratch/` citation** and are reproduced as
> reported.

- `role_now` = **anon** — the acting role selected beside the counts, in the same result set.
- `index_futures_snapshots` returned **5 rows**.
- `market_spot_session_markers` returned rows for **2026-09-30 only, none for 2026-10-01.**

| 09-30 | `prev_close_spot` | `premarket_ref_ts` | `premarket_ref_spot` | `open_0915_ts` | `open_0915_spot` | `gap_open_pct` |
|---|---|---|---|---|---|---|
| NIFTY | 22716.2 | 03:41:04 UTC (09:11:04 IST) | 22665.0 | 03:46:04 UTC (09:16:04 IST) | 22664.5 | −0.2276 |
| SENSEX | 72529.07 | — | 72441.15 | — | 72458.02 | −0.0980 |

`capture_quality` = **`MISSING_CLOSE_1530`** on both — **a value absent from the vocabulary
`merdian_reference.json` records** (`tables.market_spot_session_markers.critical_rule` lists
`FULL | PARTIAL_OPEN_ONLY | PREMARKET_ONLY | POSTMARKET_ONLY | MISSING`).

**Three cross-checks between §2.4 and this session's measurements, all exact to the digit:**

1. `premarket_ref_ts` 09:11:04 IST and `premarket_ref_spot` 22665.0 / 72441.15 match the
   09-30 `dhan_idx_i` rows at `cols.out:262` / `:263` exactly. **`premarket_ref` is the 09:11
   `dhan_idx_i` print.**
2. `open_0915_ts` 09:16:04 IST and `open_0915_spot` 22664.5 / 72458.02 match the 09-30
   **09:16 `dhan_charts_intraday`** rows at `cols.out:264` / `:265` exactly. **`open_0915` is
   the 09:16 bar**, not a 09:15 row — consistent with (b), which found no 09:15 row exists.
3. `gap_open_pct` reproduces from the pair: (22664.5 − 22716.2) / 22716.2 × 100 = −0.22759…
   against the reported **−0.2276**. **So `gap_open_pct` is computed off `open_0915_spot`**,
   and by cross-check 2 that price is the 09:16 bar's `ohlc_close` (`cols.out:205`, `:221`).

### §2.5 Open — stated as questions

The four questions are recorded as the operator framed them. **Three of them have since been
answered from the repo, and the answers are given under each; the framing predates those
reads and is kept so the reasoning is legible.** Nothing below was measured against the
database by this session.

**(i) Is `open_0915_spot` the 09:16 bar's close rather than its open — and if so, is
`gap_open_pct` computed off the wrong price?**
*Mechanism identified.* `merdian_reference.json` `change_log` S60 (2026-06-26) records
`c9c2ab3` setting *"`get_open_0915` window 09:15:00-09:18:00 for dhan end-of-minute
stamping"*. On both measured days the first row in that window is the 09:16 bar, whose
top-level `spot` is `ohlc_close` (`cols.out:205`, `:221`) — and §2.4 cross-check 2 confirms
`open_0915_spot` equals that row's `spot` exactly. So the chain is established: window →
09:16 row → `ohlc_close`. **What remains open is narrower and is a design question, not a
measurement one: is taking the bar's close intended, or should it be `raw->>'ohlc_open'`?**
The window comment shows the author knew the stamp was end-of-minute; it does not show
whether the close-vs-open choice was deliberate.

**(ii) When does the markers writer write the day's row?**
*Direction answered, current schedule NOT confirmed.* The same S60 `change_log` entry records
*"cron 40 10 \* \* 1-5 (16:10 IST) added on MERDIAN AWS"* for the markers fix — **after the
15:30 close**, which is the operator's hypothesis and matches §2.4's measurement that no
10-01 row existed at ~13:25 IST. **But the register's own AWS cron inventory does not carry
the markers writer at all:** `aws_cron.entries[4]` holds `40 10 * * 1-5` labelled
**`MERDIAN_EOD`** (`run_equity_eod_until_done.py`), and **no** `aws_cron` entry mentions
markers. So the change log and the inventory disagree about what owns that slot, and neither
can be preferred from the repo alone — confirming it needs `crontab -l` on AWS, outside this
session's scope. **The TD-S60-NEW-1 shape the operator named is the right reference:** that
incident was exactly a frontend `prev_close_spot` reading a 21-day-stale markers baseline
(74346.17 against a real prev close of 76991.22), per the same entry.

**(iii) Why does the pre-open land at 09:11, not the exchange's ~09:08?**
**Answered.** `merdian_reference.json` `change_log` S74 (2026-09-07) records *"the capture
cron moved 09:08->09:11 on 2026-08-24"*, with `get_premarket_ref` re-anchored to
`[09:00:00, 09:14:59]` by `7bb1779` precisely because both prior windows closed before the
only candidate row, leaving `premarket_ref` NULL and `capture_quality` reading `MISSING` for
11 sessions; it records the writer live at **09:11:03**. **This supersedes
`scratch/s88_design/cols.out:367`**, which stated that no mechanism was offered — true of
what had been measured at that point, and no longer true now the register has been read.

**(iv) What writes `MISSING_CLOSE_1530`, and why is the 15:30 close missing?**
**Answered, and already filed.** `build_market_spot_session_markers.py:255` returns it, from
`derive_capture_quality` (`:238-264`), which can return **eleven** values. `close_1530` is
structurally unobtainable for three independent reasons, so **`COMPLETE` is unreachable and
the field moves `MISSING` → `MISSING_CLOSE_1530` and stops** — and nothing reads the field
either way (`docs/audits/coupling_audit_2026-09-07.md:502-504`, `:612`). This is **TD-S74-NEW-5**
(`docs/registers/tech_debt.md`, cited by entry ID, not line). Separately, the register's
vocabulary is wrong in **both** directions against the code's eleven values: it invents
`FULL`, and omits `COMPLETE`, `MISSING_CLOSE_1530`, `MISSING_OPEN_0915`, `MISSING_POSTMARKET`,
`MISSING_PREMARKET`, `OPEN_CLOSE_ONLY` and `PREMARKET_AND_OPEN_ONLY`. Four of its five entries
are real.

**The probe that answers (i) and (ii) — `scratch/s88_design/markers_check`, OWED, NOT YET
RUN.** It must do two things this session could not: read `market_spot_session_markers`
**through the anon path in a single execution** carrying `current_user` beside its rows, and
compare `open_0915_spot` against **both** `raw->>'ohlc_open'` and `spot` for the same bar, so
the close-vs-open question is settled by a comparison rather than by inference from matching
digits. For (ii) it must sample `created_at` on markers rows across several sessions —
`created_at` is the writer's own clock (`cols.out:53`) and is the only in-database evidence of
when the row landed.

### §2.6 For the doc-close — not written now

No register was touched. Three lines are owed:

- **A TD for (i) and (ii), once `markers_check` has run** — not before. (iii) and (iv) need no
  new TD: (iii) is explained in the S74 `change_log`, and (iv) is already **TD-S74-NEW-5**.
- **`merdian_reference.json` — two corrections.** Rule 17's *"the live column is
  `open_0915_ts`"* is stale (§2.3 f); and
  `tables.market_spot_session_markers.critical_rule`'s `capture_quality` vocabulary must be
  replaced with the eleven values the code actually emits (§2.5 iv). The same Rule 17 text
  also lives in `CLAUDE.md` and both copies must move together.
- **Design doc §B.1a already carries these bindings** — `claude/parity_board_design.md`, in
  project knowledge. Not re-stated here; a binding transcribed into a second place is a
  binding that can drift out of agreement with itself.

---

## §3 `markers_check` — the markers schedule, the 09:16 bar, and the front end's previous close

> Appended below §2; nothing above this line moved. §3.1–§3.5 cite
> `scratch/s88_design/markers_check.out` (159 lines, sha256
> `1c6a303e8a93cf8ff441ec47aa3d68e4b8b9e919a2b111797ea566acc7399aa7`). §3.6 cites
> `scratch/s88_design/prevclose_check.out` (143 lines, sha256
> `9b3c8df780c6af1abf4acd918ae44a75aef6550a6ba4a8c1a8d5eb6320d9bc9c`).

### §3.1 Schedule

**The markers writer is scheduled.** `build_market_spot_session_markers.py` runs at
**16:10 IST, Monday to Friday**, from **cron line 24** — `40 10 * * 1-5` — and from nowhere
else (`markers_check.out:18`, `:46-47`). The host timezone is `Etc/UTC` and the crontab sets
neither `CRON_TZ` nor `TZ`, so the cron minute is UTC and IST = UTC + 5:30
(`markers_check.out:5-7`).

It is **not** in the shadow runner: `run_merdian_shadow_runner_aws.py` returns NO MATCH for
both `build_market_spot_session_markers` and `session_marker`, and its invoke list is 14
entries at `:196-269`, none of them the markers writer (`markers_check.out:36-44`).

**`MERDIAN_EOD` is a register label only** — the literal string appears nowhere in the
crontab (`markers_check.out:31-33`).

**16:10 IST is after the 15:30 close.** That single fact is what §3.5 turns on
(`markers_check.out:59-60`).

### §3.2 Correction to §2.5 (ii)

**Recorded here rather than by editing §2, so the reasoning stays legible and nothing above
this section moves.**

§2.5 (ii) reported the S60 `change_log` and the register's AWS cron inventory as
**disagreeing** about what owns the `40 10 * * 1-5` slot. **That framing was wrong.** They do
not disagree. **Two separate cron lines share that schedule** — line 24, the markers writer,
and line 30, `run_equity_eod_until_done.py` (`markers_check.out:18`, `:23`) — and
`aws_cron.entries[4]` describes line 30 while **omitting line 24** entirely
(`markers_check.out:50-57`).

So it is an **omission in `merdian_reference.json`, not a conflict**: the register is
incomplete, not wrong. The error was mine, in reading a single-entry inventory as exhaustive
and inferring a contradiction from its silence.

**Owed at doc-close:** add cron line 24 to `aws_cron` — the markers writer, 16:10 IST,
Mon–Fri, logging to `logs/marker.log`.

### §3.3 The 09:16 bar — `spot` is the close

Measured on all four 09:16 `dhan_charts_intraday` rows (both symbols, both sessions):
`spot = ohlc_close` on **4 of 4**, `bool_and = t`; `spot = ohlc_open` on **none**,
`bool_and = f`; and `ohlc_open <> ohlc_close` on **all 4**, so the test is **not vacuous**
(`markers_check.out:74-76`, `:79-81`).

This **closes the measurement half of §2.5 (i) by comparison rather than by matching
digits.** §2.4's operator-measured `open_0915_spot` of **22664.5** (NIFTY, 09-30) is that
bar's **close**; the same bar's **open is 22668.65**, 4.15 points away
(`markers_check.out:83-91`). `gap_open_pct` is therefore computed off the close: against
`prev_close_spot` 22716.2 the close gives **−0.2276** — the value §2.4 reports — and the open
would give **−0.2093**.

**Whether taking the bar close was intended stays a design question for the writer's owner.**
Nothing measured here answers it. The S60 `change_log` comment, *"for dhan end-of-minute
stamping"*, shows only that the author knew the **stamp** was end-of-minute
(`markers_check.out:92-96`).

### §3.4 The front end

The query — `lib/queries.ts:11-27`, `useSpotMarker(symbol)`: `.from("market_spot_session_markers")`,
`.select("*")`, `.eq("symbol", symbol)`, **`.order("trade_date_ist", { ascending: false })`**,
**`.limit(1)`**, `.maybeSingle()`, `staleTime` 30 s — and **no date filter of any kind**, so it
returns the single newest marker row for that symbol whatever date that is
(`markers_check.out:104-112`).

Consumers (`markers_check.out:114-127`): `state.ts:17` takes the marker inside `useMvData`,
which `state.ts:14` records as consumed by **every page**; `state.ts:34` derives `spot`;
`state.ts:35` reads `prev_close_spot`; `state.ts:36-37` compute `changeAbs` and `changePct`
from it. `ui.tsx:51-61` is `spotFromMarker`, a five-deep fallback —
`postmarket_ref_spot ?? close_1530_spot ?? open_0915_spot ?? premarket_ref_spot ?? prev_close_spot`.

### §3.5 DERIVED — not observed

**Labelled as derived.** The writer fires at 16:10 IST and the query takes the newest
`trade_date_ist` with no date filter, so during any session 09:15–15:30 IST **today's row
does not exist yet**, the front end reads the **previous session's** row, and that row's
`prev_close_spot` is the close of the session **before it**. The board's previous close during
a session is therefore **two sessions back — one session staler than correct** — and
`state.ts:36-37` compute the header change against it (`markers_check.out:133-141`).

Second-order, derived the same way and equally unobserved: `spotFromMarker` would, whenever
`g.spot` is absent, return the previous session's `postmarket_ref_spot` as the live spot,
making **both sides** of the change calculation stale at once (`markers_check.out:149-158`).

**This is the same read as TD-S60-NEW-1, bounded to one session rather than that incident's
21 days.** Nothing in §3.1–§3.5 watched the front end render a stale number.

### §3.6 The observation that converts the derivation

`scratch/s88_design/prevclose_check.out`. **Read stamp 2026-10-01 16:00:45 IST** for its
later sections (`prevclose_check.out:112`) — recorded because an earlier section of the same
file was read **before** the 16:00 capture landed and the two are therefore not comparable.

**Which row holds the settled close? Not a 15:29 or 15:30 row — none exists.** The
15:25–15:45 IST window on 09-30 returns **0 rows** (`prevclose_check.out:5`), which is the
same absence TD-S74-NEW-5 records as making `close_1530` unobtainable. The session tail ends
early: per-minute `dhan_charts_intraday` rows run to **15:14:03** for both symbols, then
**NIFTY alone** has a 15:15:04 row and SENSEX has none — an asymmetry of one minute between
the two series — and then nothing until 16:00 (`prevclose_check.out:60-64`, tail at `:95-107`).

**The row that holds the settled close is the 16:00:04 `dhan_idx_i` row**
(`prevclose_check.out:39`, `:122-123`). It is corroborated rather than asserted:
`index_futures_snapshots.spot_price` on its own 16:00:06 row carries the **identical** value
for both symbols, `c2_equals_c3 = t` (`prevclose_check.out:122-123`) — NIFTY 22620.45,
SENSEX 72480.29. Writer tails for 09-30, for contrast: `market_spot_snapshots` 16:00:04,
`gamma_metrics` 15:40:05, `index_futures_snapshots` 16:00:06 (`prevclose_check.out:55-56`).

**A correction inside the probe, recorded because it nearly became a finding.** A first
reading took the 15:15:04 row as the last of the session; a follow-up count found **3 rows
after it** (`prevclose_check.out:45-47`), and `8a`, labelled CORRECTION PROBE
(`prevclose_check.out:60-64`), named them. Had the count not been run, §3.6 would have
reported "the capture stops 15 minutes before the close and nothing follows" — true of the
window looked at, false of the day.

**Both candidate changes for 2026-10-01**, spot 22421.95 / 71909.7 at the 16:00:04 read
(`prevclose_check.out:131-132`, `:140-141`). `board_prev_close` is **operator-measured**
(§2.4), supplied to the query as a literal and labelled:

| Symbol | vs C1, the 15:15 bar | vs **C2, the 16:00 settled close — correct** | vs **BOARD**, 09-29's close | board overstatement |
|---|---|---|---|---|
| NIFTY | −0.8607 % | **−0.8775 %** | **−1.2953 %** | **−0.4178 pp** |
| SENSEX | −0.6944 % | **−0.7872 %** | **−0.8540 %** | **−0.0667 pp** |

So on this one session the board would have shown NIFTY down **1.2953 %** where the settled
figure is **0.8775 %** — the fall overstated by **0.4178 pp**, roughly **48 % too large**.
SENSEX's error is far smaller, **0.0667 pp**, because 09-29's and 09-30's closes happened to
sit near each other; **the size of the error is the gap between two consecutive closes and is
therefore unbounded, not characteristically small.**

Scope: one session pair, two symbols, one read. This observes the **inputs** — the schedule,
the query, and the three candidate closes — not the rendered page.

### §3.7 For the doc-close — not written now

- **A TD, S2 — Marketview header change is computed against a two-sessions-back close during
  every session.** Derived in §3.5 from the 16:10 IST schedule and the newest-row query;
  quantified in §3.6 at **−0.4178 pp** on NIFTY for 2026-10-01, with the error's size equal to
  the gap between two consecutive closes and so **unbounded in general**. Repair is allowed now
  under **ADR-025 B2**. **The fix belongs in the read layer** — resolve the previous trading
  session's settled close explicitly — **not in the writer's schedule**: moving the 16:10 job
  earlier cannot help, because the settled close it would need does not exist in
  `market_spot_snapshots` before 16:00 (§3.6).
- Carried from §3.2: **add cron line 24 to `aws_cron`** in `merdian_reference.json`.

---

## §4 SENSEX 2026-10-01 expiry-day move — EXPLORATORY (not pre-registered; no verdict)

> **EXPLORATORY.** No hypothesis was stamped before these numbers were read. Nothing in §4 is
> a verdict, and the quartile boundary in §4.5 was chosen **after** the ranges were seen.
> Appended below §3; §1–§3 untouched.

### §4.1 Inputs — sha256 computed at append time

| File | sha256 | lines |
|---|---|---|
| `scratch/s88_move/_p2_timeline.sql` | `ed9f88a2c55504cddc39e57d3518ea27bd7bb2a80c5b3e8d7749885176169eb5` | 119 |
| `scratch/s88_move/part1_timeline.out` | `eb079d3caf89cf0f9ec91d214969ac6b7f46104cfe9f3823bfef079d2c32b689` | 52 |
| `scratch/s88_move/_p3_baserate.sql` | `404e1f9fac16c1fae63764152a3f954347e1634aa30b7d64db64bf0746f83af7` | — |
| `scratch/s88_move/part2_baserate.out` | `a8084787fd2102508165e62b525b77c21dc0976d831d9c1bbe944a4c475ca758` | 68 |
| `scratch/s88_move/_p4_quartile.sql` | `10b2eaa7feee153f562959de14622cfb792346c1ea99ac1db3de467eb6f88b0b` | — |
| `scratch/s88_move/part2_quartile.out` | `617557cdbcb708cc99d609ed007795e823c4a403afc25ff31002e98639d59626` | 41 |
| `scratch/s88_move/_p5_expiry_baseline.sql` | `80861a6bb71a88ea92e75d06fd4ec245c845dc390f9722a2fde1b55ba35c99c7` | 290 |
| `scratch/s88_move/part2_expiry_baseline.out` | `fe8a777ed7c21c165346c54fa368aa15653e9f02cdc57b75ae6ad44f1326b996` | 70 |

`_p3_baserate.sql` and `_p4_quartile.sql` are listed because §4.5 cites their output; they were
not named in the request. All reads were `bin/roq.sh` as `merdian_ro`, bounded to one or two
IST session days per query. Both source tables have RLS on and are readable only via a
`merdian_ro_select` policy; a control read returned 80 `gamma_metrics` and 12,663
`gex_strike_snapshots` SENSEX rows for 2026-10-01, so no zero below is a reader artefact.

### §4.2 Why the measure was rebuilt

The first pass measured `straddle_vs_5d` — ATM straddle against the mean of the **prior five
calendar trading sessions** at the same 5-minute bucket. Those windows span `min_dte 0` to
`max_dte 6` (`part2_quartile.out:15-29`), so an expiry-day straddle was being divided by a
baseline mostly composed of non-expiry DTEs. The signature is in the output: the ratio read
**0.428–0.844, below 1 on all 16 eligible days** (`part2_baserate.out:47-63`). A measure that
cannot exceed 1 for structural reasons is reporting its own construction.

The rebuilt measure, `ratio_pct`, takes the straddle **as a fraction of spot** and compares it
to the same 5-minute bucket on the prior **expiry days only** (`dte = 0` and
`expiry_date = ts` IST date), with a **600 s** match rule on each prior cycle
(`part2_expiry_baseline.out:10-20`). It reads **0.684–1.497** and straddles 1
(`part2_expiry_baseline.out:25-41`) — the structural floor is gone.

Spot normalisation is a **small** correction, not the load-bearing part: `ratio_pts` against
`ratio_pct` differ by at most about 0.05 (10-01 1.286 vs 1.339; 09-17 1.348 vs 1.390), and no
ordering changes (`part2_expiry_baseline.out:25-41`).

### §4.3 Baseline depth per day — thin by construction at the start of the window

`gamma_metrics` SENSEX begins 2026-06-10, so the earliest expiry days have few or no prior
expiries to average. Stated rather than hidden (`part2_expiry_baseline.out:25-31`):

| Day | n prior expiries | Flag | Note |
|---|---|---|---|
| 2026-06-11 | **0** | NO BASELINE | first expiry day in the table; `ratio_pct` NULL (`:25`) |
| 2026-06-18 | **0** | NO BASELINE | its only prior, 06-11, **skipped at 1270 s** off-bucket by the 600 s rule (`:26`) |
| 2026-06-25 | 1 | THIN | `ratio_pct` 0.896 (`:27`) |
| 2026-07-02 | 2 | THIN | `ratio_pct` 1.066 (`:28`) |
| 2026-07-09 | 3 | — | (`:29`) |
| 2026-07-16 | 4 | — | (`:30`) |
| 2026-07-23 → 2026-10-01 | 5 | — | full depth (`:31-41`) |

`2026-06-11(1270s)` is the **only** skip anywhere in the set; every other prior cycle matched
its bucket within 600 s (`part2_expiry_baseline.out:25-30`). 2026-06-11 was also excluded from
the base-rate cohort in the first pass, on a computed rule — its nearest cycle to 09:20 is
09:41:10, 1270 s away, and it has 3 in-session spot rows (`part2_quartile.out:13`).

### §4.4 The 10-01 intraday series

Seven cycles, each against the prior five expiries **at that cycle's own bucket**, every pick
within 8 s of target (`part2_expiry_baseline.out:49-55`):

| Target IST | Cycle | Spot | Straddle | bps of spot | vix | Baseline pts | `ratio_pct` |
|---|---|---|---|---|---|---|---|
| 09:20 | 09:20:06 | 72356.79 | 449.00 | 62.05 | 13.88 | 349.07 | **1.339** |
| 10:15 | 10:15:06 | 72449.52 | 379.20 | 52.34 | 13.66 | 324.58 | 1.214 |
| 11:00 | 11:00:08 | 72428.41 | 367.00 | 50.67 | 13.62 | 315.73 | 1.209 |
| 12:00 | 12:00:08 | 72377.02 | 314.85 | 43.50 | 13.65 | 301.26 | 1.088 |
| 13:00 | 13:00:07 | **71590.87** | 417.30 | 58.29 | **14.86** | 288.97 | **1.519** |
| 14:00 | 14:00:07 | 71392.64 | 319.55 | 44.76 | 15.65 | 273.47 | 1.227 |
| 15:00 | 15:00:07 | 71865.61 | 220.10 | 30.63 | 14.60 | 262.48 | **0.876** |

The straddle was richer than prior expiries at **every** matched bucket except 15:00. The
13:00 peak of 1.519 is the cycle where spot had fallen to **71590.87** and vix had risen to
**14.86** (`part2_expiry_baseline.out:53`).

**The baseline decays 349.07 → 262.48 pts across the day** (`:49-55`), which is what makes
this a like-for-like comparison: the ratio is measured against prior expiries at the same time
of day, so it is not reading intraday theta.

For context, the day's range was **1238.56 pts / 1.7369 %**, high 72545.67 at 10:08:03, low
71307.11 at 14:05:04, bounded to 09:15–15:30 IST (`part1_timeline.out:41`) — the largest of
all 17 expiry days and 1.67× the next (`part2_baserate.out:47-48`). The in-session series
actually ends at 15:15:04, so that range omits 15:15–15:30 (`part1_timeline.out:41`, the §3.6
capture-tail finding).

### §4.5 Quartile result, with its caveats in the same paragraph

With eligibility and the quartile boundary carried over **unchanged** — same 16 days,
`ntile(4)` over range descending, only the parameter swapped — the median `ratio_pct` is
**1.200 on top-quartile-range days against 0.941 on the rest**
(`part2_expiry_baseline.out:67-68`), the same direction the old measure gave (0.593 vs 0.498,
`part2_quartile.out:38-39`). **And that number should not be relied on.** It rests on
**n = 4 against n = 12**; the top quartile's `min_n_prior_expiries` is **1**
(`part2_expiry_baseline.out:67`) — 06-25 sits in that group on a single-expiry baseline and
its own `ratio_pct` is **0.896**, below 1 and against the group's direction; REST carries a
ratio on only **11 of 12** days (`:68`), because 06-18 is eligible under the unchanged rule yet
has no baseline; the relationship is **not monotone** — the two largest `ratio_pct` values in
the whole set, **1.497 on 08-06** and **1.390 on 09-17**, are both in REST, and 08-06's range
of 246.60 pts was the **second smallest of all 17 days**
(`part2_expiry_baseline.out:33`, `:39`; ranges at `part2_baserate.out:62`, `:55`); the quartile
boundary was chosen **after** the ranges were seen; and **no significance was computed**, on
six parameters read at once with no correction.

### §4.6 Conclusion

**The morning straddle richness stood out on 2026-10-01, but across 16 expiry days it does not
separate large-range expiry days from the rest.**

### §4.7 Next step — PROPOSAL, not stamped

**This is a proposal. Nothing here is pre-registered, and no threshold is in force.** A
`ratio_pct` threshold, with its direction and its decision rule, fixed and stamped **before
2026-10-08**; evaluation restricted to days carrying **≥ 5 prior expiries**, which excludes
2026-06-11 through 2026-07-16 by the depths in §4.3. Note what that costs: of the 16 eligible
days, five have fewer than five priors, so the usable set today is 11 and two of the four
current top-quartile days leave it. **That argues for accumulating sessions rather than
re-cutting these.**

---

## §5 All-layers reconstruction on SENSEX expiry days — EXPLORATORY (not pre-registered; no verdict)

> **EXPLORATORY.** No hypothesis was stamped. Nothing in §5 is a verdict or a trading
> reading. Appended below §4; §1–§4 untouched. All artefact sha256 computed at append time.

### §5.1 Inventory and history depth

Object names taken from `MERDIAN_Enhancement_Register.md:142-153` and the detail blocks, never
guessed. Existence confirmed in `scratch/s88_move/part5_inventory.out`
(`9815e45f5abcf0bede1aebc4ab8684901c9ecc0d5b1309c75b2c8b01af40c507`).

| Layer | Object | Scalars taken | History depth, measured |
|---|---|---|---|
| L2 pin zone | `v_gex_strike_pin_zone` | peak_pin_strike, pin band | **1 ts** |
| L3 (ENH-131) | `v_gex_repriced_flip` | flip, flip_minus_spot, flip_sigma, status | **1 ts** |
| L6 (ENH-121) | `v_gex_abs_exposure` | net_gex_cr, abs_gex_cr | **1 ts** |
| L9 (ENH-130) | `v_iv_term_structure` | term_slope, is_back, dte | **1 ts** |
| L10 (ENH-132) | `v_iv_surface` | leg_skew_98, leg_status | **1 ts** |
| L12 (ENH-122) | `v_gex_concentration` | hhi_net, top_strike_net | **1 ts** |
| L12 (ENH-125) | `v_gex_strike_rank` | rank-1 strike, share_of_abs, iv_fresh | **1 ts** |
| L13 (ENH-127) | `v_oi_rotation_since_open` | ce/pe_oi_delta_qty | **1 ts** |
| max pain | `v_max_pain_by_strike`, `v_gex_max_pain`, `v_gex_pin_maxpain` | max_pain_strike, corridor_state | **1 ts** each |
| L14 (ENH-126) | `v_gex_net_gamma_river` | daily net_gex_cr, gamma_side | **30 ts / 30 days** |

**L1 gamma density — NOT FOUND** as a distinct object; per-strike `gamma_call`/`gamma_put`
exist in `gex_strike_snapshots`, no density view. Skipped rather than substituted.

**Eleven of twelve per-cycle views return exactly ONE distinct `ts`** — measured, not inferred
from the view text (`part5_depth.out:4,10,16,22,28,34,40,46,52,58,64`; sha
`2b2a8d51d616d9a8b0b890d5e26cf57ba6acb9fcb51e9e6ec1af833f38c2aad5`). Only
`v_gex_net_gamma_river` carries history (`:70`), and it covers all six cohort days (`:101-106`).

**Three stores read 0 rows, and that is not empty.** `gex_pin_maxpain_history`,
`participant_oi_daily` and `fii_dii_cash_daily` have **RLS on with ZERO policies**
(`part5_depth.out:112-114`) while `reltuples` estimates **10,930 / 1,630 / 33** rows. Zero
policies means **`anon` cannot read them either**, so L18 (ENH-115) is unmeasurable here and
`gex_pin_maxpain_history` is unreachable by the front end.

### §5.2 The as-of method, and the parity record

Because the layers are latest-only, each shipped body was reused with **one added line** inside
its `latest` CTE lateral — `AND <alias>.ts <= :'AS_OF'::timestamptz` — and nothing else.
**No metric was reimplemented**, so there is no hand-written parity claim to defend. Record:
`part5_parityC.out`, 169 lines, `e0cabcbb1e57cb0c23ad8794fda0570f6ccba94d94e6b85d44a431463731be78`.

Diffs are 1 added / 0 removed per body (`:20,:31,:42,:114,:125,:136`). Admitted bodies:

| Body | sha256 of the ASOF file |
|---|---|
| `v_gex_repriced_flip__ASOF.sql` | `585afbeac32c9511f8037a91522b4965cd5e0029c4a35bdb5e82564755450836` |
| `v_iv_term_structure__ASOF.sql` | `20750847b0da8e64ad2e93bba125a1e13cf64ccd0eaa6b887af48eb373ab1ced` |
| `v_iv_surface__ASOF.sql` | `93a6ab8ae3cac447d02cfb178245b46ac41ab3ffce44848b9763514e2b026f6b` |
| `v_gex_abs_exposure__ASOF.sql` | `2bbeddb081589957ec2cec2aa0f61eceae49fb2f50f405aa1a3b505a7dc5d63e` |
| `v_gex_concentration__ASOF.sql` | `3794fd9b2f4fa168a8793dea2e1f2111a8974bf36885ce171ebc74e656d1747c` |
| `v_gex_strike_rank__ASOF.sql` | `d3af390749302334ae79490a49be94d4f8c8def5236ebdd29d70956546d971c5` |

Each was gated on **three computed conditions** — parity sha equal at the view's own ts, control
output differing at an earlier AS_OF, and the returned `ts` **selected by column name** equal to
the AS_OF. All six **ADMITTED** (`part5_parityC.out:80-82`, `:165-171`). The control is what
makes the parity PASS a result rather than a tautology: without it, an inert parameter would
also pass.

**A `now()`-dependence would defeat a same-ts parity test** — it passes today and is wrong on
past days. Scanned: **0 hits** for `now()`, `current_date`, `current_timestamp`,
`localtimestamp`, `clock_timestamp`, `statement_timestamp`, `transaction_timestamp`,
`timeofday`, `CURRENT_TIME` in all six bodies, and **0 non-builtin function names**, so no
user-defined function can hide one (`part5_parityC.out:49-53`, `:114,:125,:136`). Every date
expression is `ts`-derived.

`v_gex_strike_rank`'s second lateral needed no separate bound: `:62` reads
`vs.ts <= h.ts`, and `h.ts` traces to the line-18 CTE via `:32`, so pinning AS_OF moves it too
(`part5_parityC.out:138-143`).

**THE UTC/IST CAST TRAP, and it would have been silent.** The spine first emitted its as-of
timestamps through `to_char(ts AT TIME ZONE 'Asia/Kolkata', …)` — IST wall-clock strings with
**no offset**. The `roq.sh` session timezone is **UTC** (measured), so
`'2026-10-01 11:30:07.908159'::timestamptz` reads as **11:30 UTC = 17:00 IST** — later than
every run that day. **Every bucket would have pinned the same last run of the day, and all 15
buckets per day would have looked plausible and identical.** Fixed by emitting `ts::text`,
which carries `+00`, as `gex_ts_raw` / `chain_ts_raw`. **The proof the fix took is that all 540
layer cells matched on exact `ts` equality (§5.3): under the bug every one would have
mismatched.** Spine: `_p9_spine.sql`
`5b2dd098bf29a630885d2e070e0066d74572d8f45ff101f06c3293e8ab7ff2fe`.

Cost note, measured not assumed: bounding the four nearest-cycle laterals to the cell's own IST
day took the plan from `cost=6972256.49..6972271.59` with a `Seq Scan on
index_futures_snapshots` to `cost=757332.23..757347.33` with **no sequential scan** — a 9.2×
reduction. The unbounded draft is kept as `_p9_spine_v0_UNBOUNDED.sql`
(`25cad8b6a10fa92e0002eda5834ff0a1622de8e69c1df80fe9e7e3115b825620`) so the diff is reviewable.

### §5.3 Grid coverage

`part5_spine.csv` (`a963ec567db3968b274f3487d5b6f6f2d24786eb01a6db07014be2860946881f`) and
`part5_grid.csv`, 90 rows × 45 columns
(`f136af347fd563c31b0f9473e17b2bfed96f28e4a25f8d89f3be7225c4cb164b`). Six expiry days ×
fifteen 15-minute buckets 09:30–13:00 IST.

- **Spine: 90/90 cells admitted on all four feeds** — `gamma_metrics`, `gex_strike_snapshots`,
  `option_chain_snapshots`, `index_futures_snapshots` — under the same-IST-date **and** ≤360 s
  rule. **No STALE cell anywhere.**
- **Layers: 540/540 cells admitted**, each on exact equality between the `ts` the view returned
  (selected by name) and the spine's raw `ts` for that cell, **and** on the spine having marked
  that feed OK. **Zero rejected.**
- `ratio_n_prior_expiries = 5` on all 90; `iv_fresh = true` and `atm_iv_age_min = 0.0` on all 90.

**L3 and L10 are empty on all 90 cells, by design.** `status = 'SKIPPED_EXPIRY'` throughout,
and the branch is explicit in the shipped bodies: **`v_gex_repriced_flip:232`** and
**`v_iv_surface:131`**, both `WHEN dte = 0 THEN 'SKIPPED_EXPIRY'::text`. Every day in this
cohort is dte 0. **That is the view refusing, not the parameterisation failing** — and it is the
settled 0-DTE reconstruction rule doing what it says.

**L9 `term_slope` is usable on 30 of 90 cells** — 2026-09-24 and 2026-10-01 only, 15/15 each.
The four earlier days carry `is_back = true` for leg 1, i.e. a **single-expiry chain**: the
pre-depth-raise state TD-S80-NEW-1 describes. Excluded from scoring; it cannot be ranked
against six days.

Every other metric is **15/15 on all six days**.

### §5.4 Scoring

`part5_extremes.out`, 90 lines,
`3740ea57cb83dac14cc341f8fb0603bea8e380e3269420c603ca582954f185aa`. Leave-one-out: a
day-bucket-metric cell is EXTREME when it is **uniquely** highest or lowest of the six days at
that same bucket; a tied extreme is not scored.

**Two confounds were removed, both before scoring and both recorded in the output.**

1. **Price levels rank by date, not behaviour.** SENSEX traded ~77k on 08-27 and ~72k on
   10-01, so `spot`, `straddle_atm` in points, `legacy_flip`, `basis` in points, `net_gex` and
   the raw L6 Crore values would have put 10-01 at LOW in **every** bucket by construction.
   Dropped from scoring, retained in the grid (`part5_extremes.out:17-21`).
2. **`d_oi_tilt_ce_over_pe` dropped from SET B.** The tilt is re-anchored at each cell's own
   ATM, so its change since 09:30 compares **different strike sets** whenever spot moves —
   the same confound §3/`_p7` was built to remove. The level stays in SET A, where one moment
   is unaffected (`part5_extremes.out:22-26`).

**SET A — 9 scale-free levels × 12 buckets. Chance 9 × 2/6 = 3.00 per bucket, 36.0 per day.**

| Day | total | mean/bucket |
|---|---|---|
| 2026-08-27 | **60** | 5.00 |
| 2026-09-17 | 40 | 3.33 |
| 2026-09-24 | 38 | 3.17 |
| **2026-10-01** | **34** | 2.83 |
| 2026-09-03 | 32 | 2.67 |
| 2026-09-10 | **12** | 1.00 |

**SET B — 9 deltas since each day's own 09:30 cell × 11 buckets. Chance 3.00 per bucket, 33.0
per day.** 09:30 is excluded because every delta is 0 there and all six days tie.

| Day | total | mean/bucket |
|---|---|---|
| 2026-08-27 | **48** | 4.36 |
| 2026-09-03 | 39 | 3.55 |
| **2026-10-01** | **38** | 3.45 |
| 2026-09-24 | 36 | 3.27 |
| 2026-09-17 | 28 | 2.55 |
| 2026-09-10 | **8** | 0.73 |

Internal consistency checked rather than assumed: SET A totals sum to **216 = 9 × 12 × 2**;
SET B to **197 = 9 × 11 × 2 − 1 tie**. The totals are **fixed by construction**, so only the
distribution across days carries anything.

**10-01 is below chance on SET A and 5 above on SET B. It is not the standout in either.
08-27 is the most extreme day in both.** Ties: 0 in SET A, 1 in SET B.

**10-01 first-and-sustained extremes.** SET A: `vix` and `basis_pct` HIGH from **09:30 for all
12 buckets**; `oi_tilt_ce_over_pe` LOW from 10:45 for 3; the other six never ran 2 consecutive.
SET B: `d_spot_pct` HIGH from **10:45** (run 5); `d_straddle_ratio_pct` LOW from 09:45 (3) and
`d_vix` LOW from 09:45 (4); and `d_L12_hhi_net`, `d_L12r_share_of_abs`,
`d_gamma_concentration_gm` **all first go extreme at 10:45**, run 2 each.

**The 10:45 co-occurrence** — four of nine SET B metrics first extreme at the same bucket, with
`d_spot_pct` turning HIGH there too — is recorded as co-occurrence at one bucket on one day.
No mechanism is offered and none is implied.

Two of the flags deserve their qualification stated:

- **`vix` HIGH for all 12 buckets is a level, not a move.** 10-01 simply carried the highest
  VIX of the six days all morning; it says nothing about intraday behaviour.
- **`basis_pct` HIGH all morning is a futures-calendar artefact, not a positioning signal.**
  The futures leg is the **October monthly** (SENSEX 2026-10-29, §2.3 c) while the option front
  expiry is 2026-10-01, so `basis_pct` is dominated by **days to the futures expiry**, which
  differs across the six cohort days by where each sits in its own monthly cycle. It is not
  comparable across days as a positioning measure and should not be read as one.

### §5.5 Fixed-strike tilt and the daily river

The fixed-strike work is §3's, carried here for completeness: `part3_window.out`
(`dfb18337c8c98c21b841552d552c19fa98cb911c59dff4231ea1f38e5b8985f4`) and `part4_fixed.out`
(`eaff1e8c11b0d8129ced35837f870f7c255b778d9406b1bfdbfbfa5f09f9b8d5`), instruments
`_p6_window.sql` (`38c9dad8eef2f6d82758d2c9b9dac8e86db279370cdbf4a849d4515920b05ff4`) and
`_p7_fixed_strikes.sql` (`f0ca6f148bd7e64f53953bd3e2281aff7cd002a087de4fdf797a0146d69e6be6`).

On the **fixed** 11:30 anchor carried to 12:15, 10-01 was the **only** one of the six days where
both near sets moved calls up and puts down together: near_below calls **+1.7393 %** / puts
**−0.9439 %**, near_above calls **+1.7972 %** / puts **−1.2785 %** of that day's 11:30
front-expiry OI (`part4_fixed.out:45`). Whole-ladder calls **+4.7963 %**, puts **−3.0065 %** —
the largest put reduction of either sign in the cohort. The comparison is complete on all six
days: `ladder_strikes_1130` equals `strikes_matched_whole` and `min_n_matched_in_any_set` is 3
everywhere (`part4_fixed.out:40-45`).

**L14, the one layer with real history.** `v_gex_net_gamma_river` daily net gamma on the six
days: −5,709,653 / −3,416,573 / +5,004,964 / −1,827,956 / +1,116,952 / **+9,547,961**
(`part5_depth.out:101-106`), all `session_complete = true`. **10-01's +9.55M is the largest of
the six and the only value above +5M**, with `n_runs` 80 against 83 on the other five. Recorded
as a whole-session aggregate; it is **not** a pre-12:15 reading and cannot support one.

### §5.6 Conclusion

**On the built layers, 2026-10-01 was not distinguishable from the other five SENSEX expiry
days before 12:15 IST.** It sat **below** the chance line on SET A (34 against 36) and 5 above
on SET B (38 against 33), while **08-27 was the most extreme day in both sets** (60 and 48).

**And the extremes score does not track range.** Measured this session
(`part6_0827_range.out`, `980209b028d1534df4c9360f39dbe34b0e0943bebc0db974be63ac17bfa1b3d4`):
**2026-08-27's in-session range was 547.15 pts / 0.7093 %, high 77689.84 at 09:16:02, low
77142.69 at 14:09:02 — rank 5 of the 17 expiry days**, and **44 % of 10-01's 1238.56 pts**. So
the day that scored *most* unusual on the layers had a middling range, and the day with by far
the largest range scored unremarkably. 09-10, the least extreme day on both sets (12 and 8), is
rank 15 of 17 by range (287.46) — the only end of the relationship that lines up.

**Correction to anything resting on 08-27 as a large-range day: it is not one.** §5.4's tables
are unchanged by this; what changes is that no reading of them may treat 08-27's high score as
"the big day also looked big on the layers". It did not have a big day.

Three further limits, stated rather than left to inference:

1. **The two layers built for vol structure refuse on this cohort.** L3 and L10 are
   `SKIPPED_EXPIRY` on all 90 cells by design, and L9 has two days. **Any expiry-day claim
   resting on L3, L9 or L10 is currently unsupportable from the built layers**, and that is a
   property of the layers' own design decision, not of this measurement.
2. **n = 6, one symbol, one 3½-hour window**, and the leave-one-out has no spare degrees of
   freedom — a day 1–2 flags off chance is noise.
3. **Nothing here was pre-registered.** The metric sets, the bucket grid and the two confound
   exclusions were all chosen after looking at the data, and two of them were chosen *because*
   of what the first pass showed.

---

## §6 Doc-close obligations — what splices where

Every edit below **splices from this file**. No content is to be re-derived at edit time.

> **One source named in the S88 close instruction does not exist in the tree.** There is no
> `carry_forward` artefact: the only matches are `PRE_*` register backups that happen to contain
> the word, and `docs/session_notes/S69_incident_carryforward.md`, which is S69 and unrelated.
> So §6 cannot splice from "carry_forward §5–§8". It is built instead from the obligations this
> capture itself records — §1.6, §2.6, §3.2, §3.7, §4.7 and §5 — plus the specifics in the
> operator's close instruction. **Stated rather than silently substituted.**

| Destination | Splice source | Notes |
|---|---|---|
| `tech_debt.md` | §5.1, §3.5–§3.7, §1.6 | **Grep before minting.** (i) the three RLS-on/zero-policy tables (§5.1); (ii) the Marketview header prev-close defect (§3.5–§3.7). Cite an existing entry if found, else `TD-S88-NEW-n`. **Update TD-S80-NEW-1** with the SENSEX PASS ×3 row and the owed NIFTY arm (2026-10-06, measured §1.1). **No TD for `legacy flip_level`** — covered by L3. Cite by entry ID + row name, never by line |
| `MERDIAN_Assumption_Register.md` | §5.2, §5.3, §2.4, §3.3 | New **§D rows, measured-this-session only**: L3/L10 refuse at dte 0 by design (`:232`/`:131`); `roq.sh` session TZ = **UTC**; the parity views are latest-`ts`-only (11 of 12); `open_0915_spot` is the **09:16 bar's close** |
| `MERDIAN_Enhancement_Register.md` | §5.1, §5.2, §5.3 | **Six candidates as PROPOSED, operator to rule, no build authorised.** Check for existing IDs first: GEX/IV history table; as-of functions for the latest-only views; a dte-0 mode for L3/L10; `sql_guard.sh`; a `sql-reviewer` subagent (shadow only, ADR-029); a move-forensics skill |
| `CURRENT.md` | §1.4, §4.6, §5.6, §6 | S88 block written after the outgoing *Previous* block is moved to `CURRENT_history.md` **verbatim**, with **byte equality asserted** |
| `session_log.md` | §1.4, §4.6, §5.6 | One line: date · git hash · concern · outcome. Then roll to the newest 10 entries |
| `merdian_reference.json` | §2.3 f, §2.5 iv, §3.1–§3.2 | Rule 17's *"the live column is `open_0915_ts`"* is stale — `open_0915_spot`, `prev_close_spot`, `gap_open_pct` all exist; replace the `capture_quality` vocabulary with the **eleven** values the code emits; **add `aws_cron` line 24** — the markers writer, `40 10 * * 1-5`, **16:10 IST** |
| `CLAUDE.md` | §5.6, §6 | Footer bump + the Rule 17 copy correction. **This file is at the repo root, outside `docs/` — operator confirmation required before the edit** |
| `MERDIAN_System_Map.md` | §5.3, §5.4, §5.6 | One **§S88** line |
| `MERDIAN_Decision_Index.md` | — | **No new ADR this session.** Nothing to index |
| `docs/research/s88_rule_lines_PROPOSED.md` | §5.2, §5.4, §3.6, §5.1 | The candidate rule lines, **PROPOSED only**. They are operator rules and do **not** go into `.claude/rules/` |
| `docs/session_notes/S89_dev_starter.md` | §1.1, §4.7, §5.6 | Dated items, build queue, rulings owed |

**Ordering note.** The `doc-close` skill's order is load-bearing: TDs are filed before the
Assumption Register, which is filed before the Enhancement Register, because later steps cite
the IDs the earlier ones mint. `tech_debt.md` files new entries at the **top**, so every line
number in it decays on the next filing — cite it by entry ID plus row name.

**What this session did NOT establish, and must not be written as if it had.** L3, L9 and L10
cannot support an expiry-day claim (§5.3). 10-01 was not distinguishable on the built layers
before 12:15 (§5.6). 08-27, the highest-scoring day, has a **rank-5-of-17** range (§5.6). The
`+9.55M` river value is a whole-session aggregate, not a pre-12:15 reading (§5.5).

---

*Session capture — S88, 2026-10-01, closed 2026-10-02. §1 and §4's L9 arms are pre-registered
and gated; §2, §3 and §5 are exploratory and labelled so in their own headings. §6 was written
before any register edit so that every subsequent update splices from one verified source. The
two layers built for vol structure refuse on the cohort this session asked about, and that
refusal is by design.*

### §5.7 Correction to §5.3 and §5.6 — the dte-0 refusal was already documented, and L10's is only partial

Two things in §5.3 are wrong as written, found while sourcing the phrase *"the settled 0-DTE
reconstruction rule"* for the Assumption Register. Both are recorded here rather than edited in
place, so the original claim and its correction stay visible.

**1. The rule is citable, and the per-view behaviour was already written down at S83.** §5.3
presents the `SKIPPED_EXPIRY` refusal as though this session established it. It did not:

- `.claude/rules/sql-views.md:20` (S62, 2026-07-01) carries the reconstruction discipline —
  expiry-day 0-DTE flat-vol `net_gex` is **numerically unreconstructible** intraday, so expiry
  days are live-sourced and the backfill emits an explicit logged `SKIPPED_EXPIRY`, never a
  T-floor.
- **`MERDIAN_System_Map.md:1963-1976` already documents the per-view behaviour**, under the
  heading *"dte-0 behaviour DIFFERS BY VIEW and must not be generalised. Verified per file, not
  assumed."* So §5.3's measurement is a **re-measurement that confirms the record**, not a
  discovery. Stated because the opposite framing takes credit the register already holds.

**2. L10 does not refuse wholesale — it skips PARTIALLY, and this session did not take what it
keeps.** The System Map records that a dte-0 leg carries `leg_status = 'SKIPPED_EXPIRY'` with
`iv`, `iv_over_atm`, `leg_atm_iv` and `leg_skew_98` withheld, **while `ce_iv` and `pe_iv` are
KEPT so the degradation stays inspectable**. §5.3's *"L10 is empty on all 90 cells"* is therefore
too strong: what is empty is **`leg_skew_98`**, the one scalar this session selected. `ce_iv` and
`pe_iv` were available on all 90 cells and were **not** fetched. **L10 is not unusable on this
cohort; it is unusable for the metric that was asked of it**, and a different question — raw
per-side IV rather than a skew — could have been answered. That is a limitation of the selection,
not of the layer.

**L3's refusal is wholesale and the §5.3 statement stands for it:** `status = 'SKIPPED_EXPIRY'`
with `flip` NULL, per S62.

**L9's reading is unchanged and now corroborated:** the System Map records that L9 **does not
skip** — a dte-0 front leg is kept with `front_is_0dte = true` as a *display flag only*. That
matches the grid, where `front_is_0dte = true` on all 90 cells while `term_slope` is NULL on 60
of them. So the 60 NULLs are **not** a dte-0 skip; they are the single-expiry chain of the four
earlier days, as §5.3 says.

**Consequence for §5.6's limit 1.** "The two layers built for vol structure refuse on this
cohort" should read: **L3 refuses wholesale; L10 withholds its skew but publishes raw per-side
IV; L9 publishes throughout and was limited by chain depth, not by any refusal.** The conclusion
in §5.6 is unaffected — no L3, L9 or L10 scalar entered the scoring — but the reason differs per
layer and must not be generalised, which is precisely what the System Map heading warns against.
