# Tape scoring — harness with planted truth + H-A / H-B scoring code, hashed before first use (plan)

Worktree `C:\wt-tape-c`, branch `tape/scoring` from engine `main` `0b29f9e`. Planned on Opus 2026-11-03; build on
Sonnet in the same session after approval (no `/clear`).

**Pre-registration v0.2** (sha256 `71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800`) is not in this
repo. Its binding text is the prompt's restatement; this plan implements it literally. Where the restatement leaves a
quantity undefined, this plan gives the **first definition**. Each one is marked **[DEF-n]**, and each goes into the hash
with the code. Where this plan departs from the prompt, the item is marked **[OVR-n]** and carries its reason.

**Scope.** I never connect to the database, read `.env`, run the extract, or run the scorer on anything except the
planted fixtures. The code is stdlib only and Windows-safe. Nothing in it is imported by `services/tape_runner/` or
shipped by `install.sh`.

---

## 0. Housekeeping (measured 2026-11-03, before any code)

```
PASS git status --porcelain empty
PASS git log --oneline -1 = 0b29f9e Merge tape/t1-db: tape_* sidecar, contracts, loader (956ff7b)
PASS git remote -v: origin = meridian-engine (never pushed) ; tape-staging = meridian-tape-staging (tape/* only)
     core.autocrlf = true  (matters for the hashes, see 1.2)    Python 3.12.10 (Local)
```

## 1.1 Where the inputs are (read from code, quoted)

| Input | Relation / columns (authority) | Notes that bind the scorer |
|---|---|---|
| Tape cycles | `tape_strike_cycle`: `symbol, trading_day, expiry, strike, leg, ts_ist, buy_cum, sell_cum, uncl_cum, gap_cum, first_seen_ts_ist, run_id` (`services/tape_db/tape_schema.py:46-61`; CSV origin `merdian_compute/tape/cycle.py:17 CYCLE_COLS`) | Bin T holds minutes `T-5 <= m < T` (`cycle.py:6-9`), grid 09:20…15:30. Rows exist only from `first_seen_ts_ist`, never zero-filled before it. `leg ∈ {CE, PE, FUT}`, and FUT rows have NULL strike/expiry. `*_cum` accumulate from the strike-leg's first bin (= since 09:15 for open-subscribed strikes, since subscription otherwise). |
| Tape candidates | `tape_events`: `symbol, trading_day, expiry, strike, leg, kind, ts_ist, side, magnitude` (`tape_schema.py:62-70`; `events.py:28`) | `kind ∈ {CONC, THIN}`. CONC is stamped at the second bin's T, with `side ∈ {buy, sell, flat}`. THIN is stamped at the close of its second minute (m+1), with `side ∈ {bid, ask}` (`events.py:7-16, 85, 113`). CONC needs ≥ 12 prior bins (`MIN_PRIOR`), so its earliest stamp is about 10:25 for strikes subscribed at the open. |
| Chain events | `tape_chain_events`: `symbol, trading_day, expiry, kind, ts_ist, strike, merged_n` (`tape_schema.py:71-78`; `chain_events.py:25`) | Counted only. Already ≥ 10:00 and front expiry. Merged with the 900 s anchor on the counted event (`chain_events.py:14-15, 144-157`). **Never re-merged.** |
| Chain runs | `tape_chain_runs`: `symbol, trading_day, expiry, ts_ist, chain_run_id, leader_strike, call_wall, put_wall, net_sign, in_window` (`tape_schema.py:79-86`) | One row per (symbol, front expiry, run ts), pre-10:00 runs included (`in_window = false`). Ties go to the lowest strike (`chain_events.py:15`). |
| Daily report | `tape_daily_report`: `symbol, trading_day, classified_share_late, report, g3` (`tape_schema.py:90-99`) | `g3 = g3_report.symbols[S]`, and `g3.verdict_detail.late.share_pct` is the 10:00–15:30 classified share (`minute.py:14-17, 241-245`). `report` = the full raw `daily_report_<day>.json`, and `report.restarts` is a list (`recorder.py:820`). |
| Tape minutes | `tape_minute`: `symbol, trading_day, minute_ist` (`tape_schema.py:35-45`) | Used for completeness only. A row exists only for a minute with a packet (T1b plan §0). |
| Per-strike chain | `gex_strike_snapshots`: `run_id, symbol, ts, expiry_date, strike, gamma_call, gamma_put, oi_call, oi_put, gex_cr` (schema v2, `sql/2026-05-25_enh80_schema_v2_migration.sql:28-39`; `merdian_reference.json → tables.gex_strike_snapshots.columns_live_s75`) | **`gamma_call` / `gamma_put` exist** (the v1 single `gamma` was dropped). A run_id is single-expiry, and all expiries of one ingest share one `ts`, so the front expiry is the min `expiry_date` at `ts` (`scripts/patch_s81_front_expiry_runid.py`). `ts` is a true timestamptz (S89). |
| Priced move | `gamma_metrics`: `run_id, symbol, ts, expiry_date, straddle_atm` (`merdian_reference.json → tables.gamma_metrics.columns_live_s75`; written `compute_gamma_metrics_local.py:417-429`) | `straddle_atm = CE ltp + PE ltp at the ATM strike`, in index points (`merdian_compute/gamma.py:335-356`). The table is unique on `(symbol, ts)` and carries `run_id`. **Paired by `run_id` = the front run's id, never by `(symbol, ts)`.** A mismatch excludes the cycle and is counted (it would reveal a non-front gamma row). |
| 1-minute spot | `hist_spot_bars_1m`: `instrument_id, trade_date, bar_ts, open, high, low, close` (written by `capture_spot_1m_v2.py:481-494`) | Keyed by **`instrument_id`**, not symbol: NIFTY `9992f600-51b3-4009-b487-f878692a0bc5`, SENSEX `73a1390a-30c9-46d6-9d3f-5f03c3f5ad71` (`capture_spot_1m_v2.py:110-123`). `bar_ts` = the bar's **start** minute as true UTC (`:346`, `from_ts_ist.astimezone(utc)`). **It has highs and lows.** Historic rows in this table were IST-clock-as-UTC (S61), so the scorer runs a clock check (§1.3). |
| Expiry close / pin | No stored per-run pin exists for history: `v_gex_strike_pin_zone` is latest-run scoped (S69). | Close = `close` of the 15:29 bar of `hist_spot_bars_1m`. Pin = computed from `gex_strike_snapshots` [DEF-7]. |

**`straddle_atm` exists**, so the plan does not stop at §1.1.

## 1.2 Files and the hashes

| File | Role | Hashed |
|---|---|---|
| `services/tape_scoring/__init__.py` | empty (needs a `.gitignore` negation like `!services/tape_db/__init__.py`, S68) | no |
| `services/tape_scoring/scoring_extract.sql` | nine pure SELECTs, one per relation, each preceded by `-- @relation <name>` | **yes** |
| `services/tape_scoring/run_extract.sh` | box-side loop: for each relation and day it prepends `\pset format csv`, `\pset footer off`, `\set d '<day>'`, `\set t0 …`, `\set t1 …`, pipes one statement to `bin/roq.sh`, writes `<relation>/<day>.csv`, checks rc = 0 and the header, and writes `manifest.tsv` (sha256 per file) **[OVR-1]** | **yes** |
| `services/tape_scoring/score.py` | pure functions + CLI | **yes** |
| `services/tape_scoring/wilcoxon.py` | exact one-sided signed-rank test | **yes** |
| `docs/tape/scoring_hashes.md` | the ledger entry | — |
| `tests/tape_scoring/gen_fixture.py`, `tests/test_tape_scoring.py`, `tests/tape_scoring_mutants.py` | tester | no |

**[OVR-1] Why a fourth hashed file.** `bin/roq.sh` prints aligned text, has no psql-variable flag, and refuses `COPY`
(`bin/roq.sh:112-128`). CSV therefore has to come from psql meta-commands in the input stream. The 30 s
`statement_timeout` and the ~2.7 s per-connection cost (S89) argue for one call per relation per day. The day range
cannot be a literal in a file hashed before the range is known, so it enters as psql variables (`:'d'`, `:'t0'`,
`:'t1'`). The runner decides which rows are extracted, so it is hashed too.

**Hashes are stable across checkouts.** With `core.autocrlf=true` the Windows working tree is CRLF and the box is LF, so
the same commit would produce two sha256 values. `.gitattributes` gets `services/tape_scoring/** text eol=lf`. The hash
check also refuses a hashed file that contains `\r`. The hash is then over raw bytes and is identical everywhere.

`scoring_hashes.md` holds: the sha256 of each of the four files; the pre-reg sha; the date; the head sha of the commit that
carries the files; and the sentence "no tape-vs-outcome query has run before this hash". The operator copies it beside
`tape_preregistration_v0.2.md` on `meridian-tape-staging` `main`.

**CLI.** `python -m services.tape_scoring.score --inputs <dir> --out <dir> [--fixture] [--rerun-defect "<text>"]`.
Writes `score_result.json` (canonical JSON, sorted keys, fixed float format), `score_report.txt` and `scoring_runs.json`.
Deterministic. Null seed = `int.from_bytes(sha256(score.py bytes)[:8], "big")`, recorded in the output. Per-symbol
streams use `random.Random(int.from_bytes(sha256(seed_bytes + symbol)[:8]))`, never `hash()`, which is randomised per
process.

## 1.3 Definitions pinned

**Arithmetic.** Every `gex_cr`, `gamma_*`, quantity, spot and straddle is parsed from its CSV string into a
`fractions.Fraction`. Every sign, sum, argmax, median and threshold comparison is therefore exact. Floats appear only in
the rendered output, at 6 dp. This is what makes `sc-sign-only` provable: scaling by 1000 is exact, so no
near-cancellation sign flip is possible.

**Clock reconciliation.** A run at `ts` T pairs with the tape grid point G = T floored to 5 minutes (10:05:21 → 10:05,
bin [10:00, 10:05)), so the tape content lies strictly before the chain snapshot. The output reports the floor-offset
distribution (T − G in seconds: min / median / max, plus a 30 s histogram). A run with no tape row at G is excluded and
counted. **[DEF-1] The clock rules are applied to G**: H-A takes 10:00 ≤ G ≤ 14:45, and "after 14:45" means G > 14:45.
The pre-reg names the cycle by the 5-minute clock. Applied to raw T, a run at 14:45:21 would be "after 14:45" and the
last cycle would silently drop.

**Front expiry and window.** The front expiry of a run is min `expiry_date` at its `ts` (in Python; the extract cannot
aggregate, see `sc-extract-pure`). The window at G is the set of strikes with a CE or PE `tape_strike_cycle` row at
`ts_ist = G` and `expiry` = the run's front expiry. Presence means subscribed. Tape rows of another expiry, and FUT
rows, are excluded and counted.

**U.** U = sign(Σ `gex_cr` over all front-run strikes), computed exactly. It is cross-checked against
`tape_chain_runs.net_sign`, and disagreements are counted and listed. U = 0 excludes the cycle, counted.

**S.** D = −Σ over window strikes (γ_call·(buy_cum_CE − sell_cum_CE) + γ_put·(buy_cum_PE − sell_cum_PE)) at G, with γ
the run's `gamma_call` / `gamma_put` at that strike. A window strike with no chain row, or a NULL γ, contributes 0 from
that leg, counted. Classified share = Σ(buy_cum + sell_cum) ÷ Σ(buy_cum + sell_cum + uncl_cum) over window legs, with
`gap_cum` in neither and its total reported. S is **undefined** when `2·(b+s) < (b+s+u)`, i.e. share < 50 %, or when
the denominator is 0. S = 0 (D = 0) is also excluded, counted. Exactly 50 % is defined.

**R(T).** R(T) = (max `high` − min `low`) over bars whose start label m satisfies T < m ≤ T + 30 min (30 labels for any
T), ÷ the paired run's `straddle_atm`. A cycle with fewer than 25 of the 30 bars is excluded, counted. So is a NULL or
≤ 0 straddle. **Clock check:** after conversion to IST, ≥ 95 % of a day's bars must have labels in 09:15–15:29.
Otherwise the day's spot is refused (it would be IST-labelled-UTC, as in S61) and every cycle on it is excluded,
counted, and listed.

**H-A.** The population is per symbol: non-quarantined days, 10:00 ≤ G ≤ 14:45, S defined, U ≠ 0, R present. Primary
stratum U > 0: per day, agree = S > 0 and disagree = S < 0. A day qualifies only with ≥ 3 cycles in each group.
Δ = median R(disagree) − median R(agree), using the standard median (mean of the two middle values). Decision:
INSUFFICIENT if n < 20; YES if n ≥ 20 and median Δ ≥ 1/10 and p ≤ 1/10; NO otherwise. Overall: YES/YES → YES,
NO/NO → NO, else MIXED. Secondary, descriptive:

- **Agreement.** P(S = U) against p_S·p_U + (1−p_S)(1−p_U), reported twice: on the H-A population, and on all
  G ≥ 10:00 cycles. The latter is the "present in the secondary where allowed" case for G > 14:45.
- **U < 0 stratum.** The same Δ with the prediction reversed (Δ < 0 predicted), reported with its Wilcoxon p for
  Δ < 0, and no decision.
- **Pin [DEF-7].** Expiry days only (`trading_day` = the front expiry of the G = 14:15 run). Pin = the window strike
  with the largest **positive** `gex_cr` in that run, ties to the lowest strike; no positive strike means no pin,
  counted. S_pin = sign of D restricted to the pin strike's two legs, under the same 50 % rule at that strike.
  Agree = S_pin = U(14:15). Distance = |close(15:29 bar) − pin| in points, and ÷ `straddle_atm` of the 14:15 run.
  Reported per group (agree / disagree / undefined): n and median.

**Wilcoxon** (`wilcoxon.py`). Zeros are dropped (Wilcoxon 1945; the "wilcox" zero convention). Ties get average ranks.
W+ = the sum of the ranks of positive differences. One-sided p = P(W+ ≥ w+ | H0), from the **exact conditional
permutation distribution** (each rank's sign ±1 with probability ½, ties included), computed by DP over doubled ranks,
which are integers (Hollander, Wolfe & Chicken, *Nonparametric Statistical Methods*, 3rd ed., §3.1). For n > 60 the
normal approximation is used, with tie-corrected variance and continuity correction ½. The switch point and the method
used are in the output. Hand-computed cases (beliefs stated now, measured in the build):

| Case | d | n | w+ | p (exact, one-sided Δ > 0) |
|---|---|---|---|---|
| A | (0.5, 1.2, −0.3, 2.0, 0.9) | 5 | 14 | 2/32 = 0.0625 |
| B (tie) | (1, −2, 2, 3, 4, 5) | 6 | 18.5 | doubled ranks {2,5,5,8,10,12}; P(2W− ≤ 5) = 4/64 = 0.0625 (ordinal-rank mutant gives 3/64 or 5/64) |
| C (zero) | (0, 1, 2, 3, 4, 5, 6, 7, −8) | 8 | 28 | P(W− ≤ 8) = 25/256 = 0.09765625 (two-sided mutant 0.1953125) |

**Quarantine** (per symbol per day; a quarantined day is excluded from both hypotheses and listed with its reason):

- **[DEF-2] Completeness** = (distinct `minute_ist` in [09:15, 15:30) with any `tape_minute` row for the symbol) ÷ 375.
  Quarantined if `100·k < 95·375`, so 94.9 % is out and 95.0 % is in. **Pre-reg rule 4 named completeness without
  defining it. This is its first definition, and it goes in the hash.**
- **Late share** = `g3.verdict_detail.late.share_pct`. Quarantined if < 50, so 49.9 is out and 50.0 is in. It is
  cross-checked against the `classified_share_late` column, mismatches counted. **[DEF-3]** A NULL share, a special
  session (no `late` block), or **no `tape_daily_report` row** quarantines the day as `UNVERIFIABLE`. A data-quality
  rule that cannot be evaluated cannot be passed.
- **[DEF-4] Token restart.** The runner writes no reason in a restart record (`recorder.py:167-169`). The token-failure
  path saves `last_state = "TOKEN_FAIL"` before exiting (`recorder.py:332-334`), and the next process records it as
  `prev_state`. Quarantined if any `report.restarts[i]` has `prev_state == "TOKEN_FAIL"` and `process_start_ist` in
  [09:15, 15:30). The report is day-level, so both symbols are quarantined. A pre-open token failure is not mid-session.

**H-B labels** (the filtering T1b deferred). Tape events stamped before 10:00 are excluded and counted **[DEF-5]**: the
pre-reg excludes 09:15–10:00 from both hypotheses, and only THIN can fire then. For each remaining CONC/THIN on a CE/PE
leg, the **reference run** is the latest front run of the same symbol and day with `ts ≤` the event's `ts_ist`. Its
`call_wall` / `put_wall` come from `tape_chain_runs`. Its runner-up is the strike with the second-largest |`gex_cr`|
over all of that run's strikes (the same universe as T1b's leader), excluding the leader, ties to the lowest strike.

- CONC at `call_wall` on CE, or at `put_wall` on PE → **T1**.
- CONC at the runner-up, either leg → **T2**.
- THIN at a wall strike on that wall's leg with `side` = passive(leg) → **T3** (see §4, decision 1).
- One event can carry several labels. A CONC at any other strike gets no label.

**Matching, lead.** E1 at K matches T1 or T2 at K. E2-call / E2-put at K matches T1 or T3 at K (literal: the label's
leg is not required to equal the E2's side). The chain event's K must be a window strike at floor(T); otherwise it is
excluded and counted. Lead = T − t of the **latest** matching tape event with t in (T − 60 min, T], in minutes, exact.
No match means uncovered. Coverage = covered ÷ n. Median lead is taken over covered events.

**Null [DEF-6].** For each chain event, 100 strikes are drawn uniformly **with replacement** from the window at floor(T).
For a drawn strike k′, the predicate is the event's matching rule **with the role condition removed and the leg/side
condition kept**:

- E1: a CONC on either leg at k′.
- E2-call: a CONC on CE, or a THIN on CE with the passive side, at k′.
- E2-put: the same on PE.

Each is evaluated in (T − 60, T], with the nearest-preceding lead. Reason: the T1/T2/T3 roles hold only at the 1–3
role strikes of each run. A null that demanded the role at k′ would score ≈ 0 by construction, and "coverage > null 95th"
could not fail. That would test the label filter, not timing (Rule 0). The null therefore asks whether a qualifying
candidate occurs at a random window strike as often, and as early, as at K. That is conservative: the real side must
also satisfy the role.

**Bootstrap.** B = 1000 replicates. Each replicate resamples the symbol's non-quarantined days with replacement (same
count), and gives each chain event on those days **one** of its 100 draws, chosen uniformly from the stream. The real
statistic is computed on one K per event, so its null must be too; averaging all 100 draws would shrink the null spread
and make it easier to beat. Coverage_b and median-lead_b are computed per replicate. A replicate with no covered draw
contributes lead 0. Threshold = the 95th percentile by **nearest rank**, the ⌈0.95·B⌉-th order statistic.

**H-B decision** (per symbol; n = merged events in non-quarantined days and in the window), evaluated in order:

1. **INSUFFICIENT** if n < 300 or there are fewer than 15 non-quarantined days.
2. **NO** if median lead ≤ 5, or coverage < 1/2, or coverage ≤ null95_cov, or lead ≤ null95_lead. No covered event
   means NO.
3. **YES** if coverage ≥ 1/2 and lead ≥ 10 and coverage > null95_cov and lead > null95_lead.
4. **MARGINAL** if 5 < lead < 10.

Overall is combined as for H-A. The output also counts E2 events whose K is a **new** wall strike: under the pre-reg's
labels, K was not the wall at the tape event's time, so such events can match only if K held another role. This is
reported, not fixed.

**Run-once ledger [OVR-2].** The ledger is written to `--out/scoring_runs.json` **and** to the fixed path
`docs/tape/scoring_runs.json`, and a non-fixture run refuses if **either** records a prior run. Reason: a ledger kept
only "beside the output" is bypassed by choosing a new `--out`. `--rerun-defect "<text>"` permits exactly one re-run and
records the text. A third run refuses unconditionally.

**Trigger.** Computed from `tape_daily_report` days: met if both indices have ≥ 6 recorded expiry days
(`trading_day` = the front expiry of that day's runs), or there are ≥ 30 distinct trading days. Printed. Unmet means
the run refuses.

**Hash check.** A non-fixture run recomputes the four sha256 values and refuses with the diff if any differs from
`scoring_hashes.md`.

**`--fixture`** skips the hash check, the ledger and the trigger. It **refuses unless** `--inputs` holds the
`FIXTURE_TRUTH.json` that `gen_fixture.py` writes, and a non-fixture run refuses if that file is present. So `--fixture`
cannot be used to skip the gates on real data.

**Pre-registered literals** live in one `PARAMS` dict in `score.py`: 10:00, 14:45, 3, 20, 1/10, 1/10, 50 %, 30 min,
25 bars, 300, 15, 1/2, 10, 5, 60 min, 100, 1000, 95, 95 % completeness, 50 % share, 6, 30, and the Wilcoxon switch at 60.
The guard `sc-params` asserts every name and value.

**No lookahead (Rule 0a), asserted in unit checks.** S at T reads only the tape row at G ≤ T. Labels read only runs with
`ts ≤` the tape event. Leads read only tape events with t ≤ T. R reads only bars with label > T. Each check is an
assertion on constructed rows that a one-character mutant (`<` ↔ `<=`) breaks.

## 1.4 Extract (`scoring_extract.sql`), per relation

Each SELECT reads one relation and filters by day only. Tape tables use `trading_day = :'d'`. Engine tables use
`ts >= :'t0' AND ts < :'t1'` (IST day bounds). `hist_spot_bars_1m` uses `bar_ts >= :'t0' AND bar_ts < :'t1'` and
`instrument_id IN (<two uuids>)`. Every SELECT also filters `symbol IN ('NIFTY','SENSEX')` where the relation has a
symbol column. The columns are those in §1.1, plus `run_id` on the tape tables, so the output records which load each
day came from. **[OVR-3]** No clock or front-expiry filter is applied in SQL. The clock rules live in `score.py` only,
where the guards can mutate them. A filter in SQL would sit where no guard reaches.

---

## 2. Build (Sonnet) — tester first

`gen_fixture.py` writes the extract layout (`<relation>/<day>.csv`) and `FIXTURE_TRUTH.json` for 32 days per symbol,
which meets the 30-day trigger. It plants everything §2 of the prompt lists. Decision boundaries (n = 19 / 20, effect
0.09 / 0.10, p = 0.11, 299 events, 14 days, lead 5.0 / 7) are planted as **separate small scenarios** passed through the
same public functions, so the end-to-end fixture stays one realistic dataset. The generator self-checks its truth with
an independent reference (brute-force 2ⁿ Wilcoxon, `statistics.median`) before writing.

The guards are the prompt's 18, plus **`sc-params`** (M-SC-PARAM-CHANGED), for 19. Every mutant has a 5× control. The
mutant harness copies T1-db's (exact-string patch, applied exactly once, control must pass). Added unit checks:
lookahead ×4, Wilcoxon brute-force agreement n ≤ 12, the normal switch at 61, the CSV timestamp parser
(`+00`, `+05:30`, `+0530`), the clock check, and `FIXTURE_TRUTH` refusal in both directions.
`tests/run_offline.sh` 38 → 40 (`39/40 tape scoring guards`, `40/40 tape scoring mutants --repeat 5`).
**Rule 23:** a build inside 08:30–15:40 IST runs the two new suites under the R-1 Local override, as T1-db did. The full
`run_offline.sh` is not run in-window.

## 3. Operator commands (finalised in the build report)

1. **Extract (not now).** On the box, in `~/meridian-cc`:
   `git fetch https://github.com/balannavin-cyber/meridian-tape-staging.git tape/scoring`, then
   `git show FETCH_HEAD:services/tape_scoring/{scoring_extract.sql,run_extract.sh}` into `~/tape_scoring/`,
   `sha256sum` against the ledger, and `bash run_extract.sh --from <d0> --to <d1> --out ~/tape_scoring/in`. Expect one
   `EXTRACT PASS <relation> <day> rows=<n>` line each, then `manifest.tsv`.
2. **Fixture run on Local:** `python tests/tape_scoring/gen_fixture.py --out <scratch>` followed by
   `python -m services.tape_scoring.score --inputs <scratch> --out <scratch>\out --fixture`.
3. **The one real run.** Not before the trigger (about mid-December), and from the hashed head only.

## 4. Open decisions for the operator

1. **T3 passive side.** The prompt proposes CE wall = `ask` and PE wall = `bid`. **I conclude `ask` on both legs.** A
   wall is written open interest. The E2 that a T3 must lead is the wall's OI changing, and wall decay is writers buying
   back, which lifts offers. The passive side consumed is therefore the **ask** of whichever option is the wall.
   Reading the put's bid as "support" maps the option book onto spot direction, but demand for puts (their bid) is
   bearish, not support. **Approve ask/ask, or rule CE ask / PE bid.** Either way the choice is a literal in the hash.
2. **[DEF-6] null predicate** and **[DEF-3] unverifiable ⇒ quarantined**: approve or overrule.
3. **CSVs from the box to Local.** No mechanism is recorded in `docs/runbooks/`. The tape box writes to
   `s3://meridian-tape-raw` (`services/tape_runner/config.py:10`), but whether the `roq.sh` host can write there is
   unverified. Say how files move once, and I will capture it as a runbook.
4. **Unverified access.** Whether `merdian_ro` can read `gex_strike_snapshots`, `gamma_metrics` and
   `hist_spot_bars_1m` is not measured (Rule 17 shows it can be refused by RLS). The extract runner refuses an empty
   day, and a one-line `SELECT count(*)` pre-check per relation belongs before the real extract.

---

## 5. Operator rulings on §4 (2026-11-03) and what they changed

| # | Ruling | Effect |
|---|---|---|
| R-3 | T3 passive side = **ask on both legs** (wall = written OI; the lead under test is wall decay, i.e. writers buying back and consuming offers). The CE-ask / PE-bid reading is **rejected**. A later change is pre-reg v0.3, not a parameter edit. | `PARAMS["passive_side"] = {"CE": "ask", "PE": "ask"}` |
| DEF-6, DEF-3 | approved | as §1.3 |
| DEF-1, 2, 4, 5, 7, OVR-1, 2, 3 | approved as written | as §1.2 / §1.3 |
| Transport | The production box holds MERIDIAN-account AWS credentials for the engine deploy bucket **`meridian-engine-deploy`** (`docs/runbooks/runbook_aws_cli_file_operations.md`; Deployment Topology S101/S104 use `s3://meridian-engine-deploy/<session>/`). `run_extract.sh --s3 <bucket>/tape_scoring/<d0>_<d1>/` uploads the CSV tree + `manifest.tsv`; Local pulls with `aws s3 sync`. **Whether the box credential can `PutObject` there is not verified by this session** (no network). If it cannot: `tar czf` of the tree through the SSM session is the fallback. | `run_extract.sh --s3`; `score.py` verifies `manifest.tsv` on a real run |
| Pre-check | `run_extract.sh` starts with `SELECT count(*)` per relation for the first day and refuses, naming the relation, if a count is 0 or the read is refused. `hist_spot_bars_1m` is the unmeasured read. | in `run_extract.sh` |

---

## 6. Build record (2026-11-03, same session; built on Sonnet after the operator's GO)

| File | Role |
|---|---|
| `services/tape_scoring/score.py` | the scorer: `PARAMS` (every pre-registered literal), exact `Fraction` arithmetic, H-A, H-B, quarantine, gates, CLI |
| `services/tape_scoring/wilcoxon.py` | exact one-sided signed-rank (DP over doubled midranks), normal above n = 60, no scipy |
| `services/tape_scoring/scoring_extract.sql` | ten tagged pure SELECTs (nine relations + the day list); columns == what `score.py` reads (asserted) |
| `services/tape_scoring/run_extract.sh` | box-side runner: count pre-check, one `bin/roq.sh` call per relation per day, header check, `manifest.tsv`, optional `--s3` |
| `tests/tape_scoring/gen_fixture.py`, `tests/test_tape_scoring.py`, `tests/tape_scoring_mutants.py` | planted-truth generator (column layout read from the SQL), 19 guards + 17 unit checks, 29 mutants |
| `docs/tape/scoring_hashes.md` | the ledger (written in the commit after the code commit) |
| `.gitattributes`, `.gitignore`, `tests/run_offline.sh` | `services/tape_scoring/** eol=lf`; `__init__.py` negation (S68); suite 38 -> 40 steps |

### 6.1 Beliefs stated before measuring, and what was measured

| Belief | Measured | Consequence |
|---|---|---|
| Wilcoxon A / B / C: p = 1/16, 1/16, 25/256; B's W+ = 18.5 | brute-force enumeration agreed on all three; the tied-ranks mutant gives 3/64 as predicted | none |
| Omnibus fixture: H-A YES both, H-B YES both | H-A YES (Δ = 3/20 every day, 198 population cycles = 22 x 9); H-B YES | none |
| Omnibus coverage 12/14 | **measured 1.0**: a neighbouring same-K tape event inside the 60-minute window matches too (that is the pre-registered rule), and the median lead was 10.67, too close to the 10-minute line to be a clean YES | **fixture changed, scorer not**: a fourth event kind sits at a strike with no tape events (unmatched by construction), planted leads 20..34. Measured: coverage 11/14 = 0.786, median lead 14.17 (the nearest preceding event, not the planted one), null95 0.39 / 5.2 min |
| `--null` fixture gives NO | NO on both symbols, and a null clause fired (NIFTY coverage 0.526 passes the absolute 1/2 and is stopped by the null95 0.705) | none |
| P(real run reads walls from `tape_chain_runs`) | **would have read none.** `tape_chain_runs.ts_ist` is rendered with whole seconds (`chain_events.py` strftime) while `gex_strike_snapshots.ts` may carry a fraction; a microsecond join finds no wall, so no T1 and no T3, with only a counter to show it | joined on the whole second; fixture engine timestamps now carry `.123456`; **mutant 29** `M-SC-RUNS-JOIN-MICROSECOND` is caught by `hb-labels` |

### 6.2 Slips and deviations

- **95.0 % completeness is not representable on 375 minutes.** 356 minutes = 94.93 % (quarantined), 357 = 95.2 % (kept). The rule is the integer test `100*k < 95*375`.
- **The "p = 0.11" scenario measures p = 0.108** by an independent DP over integer ranks (band 0.105..0.115), not exactly 0.11.
- **Mutants are 29, not 27** (the prompt's 26 + `sc-params` + the join mutant). Guards are 19 (the prompt's 18 + `sc-params`).
- **The mutant harness runs only the targeted guard per mutant** (the control runs the whole suite x5), so 29 x 5 stays minutes, not an hour. A catch must be a clean FAIL with no `EXCEPTION`.
- **No cross-check of walls against `oi_call` / `oi_put` of `gex_strike_snapshots`** (the columns are extracted but unused). `runs_without_chain_runs_row`, `chain_run_id_mismatch` and `net_sign_vs_U_mismatch` are counted instead.
- **`tape_events` before 10:00 are excluded and counted (DEF-5);** the 09:20..09:55 grid cycles exist and are excluded by the clock rule, not dropped at load.
- **Rule 23:** built inside 08:30..15:45 IST on a weekday; every suite ran under `TAPE_RULE23_OVERRIDE_R1=1` (ruling R-1, Local). `tests/run_offline.sh` was not run end to end in-window.
- **`run_extract.sh` was exercised against a stub `roq.sh` only** (no database, no psql): count pre-check, zero-count refusal naming `hist_spot_bars_1m`, header check, 18-file manifest. It has never run against the real `bin/roq.sh`.

### 6.3 Not verified (said once, here)

- That `\pset format csv` placed in the stream overrides `roq.sh`'s `-P format=aligned`, that `:'d'` interpolation survives `roq.sh`'s `printf '%s\n' "$SQL"`, and `roq.sh`'s write-verb guard against the SQL text (none of the guarded words appear outside comments).
- That `merdian_ro` can read `hist_spot_bars_1m` and the `tape_*` relations; that a day of `gex_strike_snapshots` fits the 30 s `statement_timeout` (a timeout fails the extract loudly; nothing partial is kept).
- That the box credential can `PutObject` to `s3://meridian-engine-deploy/tape_scoring/...`. Fallback: `tar czf` through the SSM session.
- The scorer's wall-clock and memory on 30 real days (the omnibus, 22 days x 2 symbols, scores in about 5 s; real days have far more `gex_strike_snapshots` rows, loaded one day at a time).
- That `psql` prints `timestamptz` with an offset (the parser refuses a timestamp without one, so a bare timestamp fails loudly rather than being read as UTC).
