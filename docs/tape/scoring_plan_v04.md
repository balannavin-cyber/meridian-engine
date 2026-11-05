# Tape scoring v0.4 — the diff to the v0.2 scoring plan (plan; nothing built yet)

**PREREG v0.4 OK.** `docs/tape/tape_preregistration_v0.4.md` in this worktree has sha256
`b45477d36eba6930ab41171a3405c10cf6ecb0bd1fbb04b52d09a5c2129acd57`, as briefed (staging `main` `f481d9c`). Worktree
`C:\wt-tape-v04`, branch `tape/scoring-v04`, base `be197b3` (it carries `93c0196` / `4004662`, the v0.2 scorer and
ledger). Read: v0.4; `docs/tape/scoring_plan.md` (v0.2 plan, cited below as **P2 §n**); `docs/tape/scoring_hashes.md`;
`services/tape_scoring/*`; `tests/tape_scoring/gen_fixture.py`; `tests/test_tape_scoring.py`;
`tests/tape_scoring_mutants.py`; `tests/run_offline.sh:209-213`.

The changes implement v0.4 §1 (S over a trailing window; R window; window-coverage reporting), §2 (sign-change
count), §3 (per-label reporting; T4 descriptive) and §6 (the defect). **No §5 value changes.** The decision functions
(`decide_ha`, `decide_hb`, `combine`) are untouched.

---

## 0. Three scope findings the operator must rule on before the build (§7 lists them as decisions)

**F-1. The hashed extract cannot feed v0.4's S.** v0.4 §1 builds S from `buy_5` / `sell_5` / `uncl_5` of the six bins
stamped T−25…T. The hashed `scoring_extract.sql:244-247` SELECTs only `buy_cum, sell_cum, uncl_cum, gap_cum` from
`tape_strike_cycle`. The DB relation carries the 5-minute columns (`services/tape_db/tape_schema.py:52-53`: `buy_5`,
`sell_5`, `uncl_5`, `gap_5`). So `scoring_extract.sql` **must change**: add `buy_5, sell_5, uncl_5, gap_5` to the
`tape_strike_cycle` SELECT. The cum columns stay, unread for S, as briefed. This is still a pure single-relation SELECT;
`sc-extract-pure` keeps passing; `run_extract.sh` derives its header check from the SELECT list (`run_extract.sh:325`),
so it does not change. `scoring_extract.sql` gets a **new sha256**.

**F-2. T4 needs Kite OI per strike-leg, and neither tape relation's extract carries it.**
- `tape_minute` carries it in the DB: `oi` (bigint), with `role`, `opt_type`, `strike`, `expiry` (`tape_schema.py:35-45`). The extract SELECTs only `symbol, trading_day, minute_ist, run_id` (`scoring_extract.sql:269-272`).
- `tape_strike_cycle` carries `oi_last` and `oi_delta_5` (`tape_schema.py:57`), at 5-minute grain.

So a tape relation does carry OI per strike-leg, and the brief's STOP condition does not trigger. **Recommended source:
`tape_minute.oi`** (minute grain), with the `tape_minute` SELECT extended to
`symbol, trading_day, role, opt_type, strike, expiry, minute_ist, oi, run_id`.

`oi_last` is not recommended for two reasons:
- At 5-minute grain a T4 is stamped at a bin end T. The E2 it would cover is stamped at the run, T + ≈ 6 s (exploration B.1). The T4 lead is then ≈ 0.1 min for every covered event by construction.
- The planted guard "T4 1 min before E2" cannot be expressed on that grain.

The exploration's 1.1-min median came from minute data (`E2_tape_oi_lead.csv`).

Cost: `tape_minute` is 57–67 k rows per day, the same rows as today with five more columns. Whether that SELECT fits
`roq.sh`'s 30 s `statement_timeout` is **UNVERIFIED** (S89 measured 85 k rows of `option_chain_snapshots` at ≈ 10.5 s; the
extract pre-check would fail loudly, not silently). Completeness (DEF-2) keeps reading `minute_ist` from the same rows.

**F-3. The guards and mutants live outside the paths I may change.** The brief allows `tests/tape_scoring/`. But the 19
guards, `EXPECTED_PARAMS` and `GUARDS` are in `tests/test_tape_scoring.py`, and the 29 mutants in
`tests/tape_scoring_mutants.py`. `ha-clock`, `ha-delta` and `ha-s-definition` must be re-run against the new S,
`sc-params` must list the new literals, and the mutant list must grow. **Both files must be edited.** Moving the suite
under `tests/tape_scoring/` would change two run_offline.sh paths and the mutant harness's COPY list for no gain.
Recommended: allow edits to these two files.

**F-4 (a literal the brief names but PARAMS does not hold).** The brief's `e2_oi_move_frac` does not exist in
`score.py`. The E2 5 % lives in `merdian_compute/tape/chain_events.py:23` (`OI_PCT = 5`), on the chain side. T4 needs it
in the scorer. Proposed: `"e2_oi_move_pct": 5` in `PARAMS`, listed by `sc-params-v04` with value 5. A unit check asserts
it equals `chain_events.OI_PCT`, so the two cannot drift. That is a **third** new key beside `s_window_min` and
`s_window_bins`. Its value is the §5 "E2 OI move ≥ 5 %" literal, so no §5 value changes.

---

## 1. Diff to the v0.2 plan, by section

### P2 §1.1 (inputs) → changes
| Input | v0.2 | v0.4 |
|---|---|---|
| Tape cycles | `buy_cum, sell_cum, uncl_cum, gap_cum` read for S | **`buy_5, sell_5, uncl_5, gap_5` read for S** (F-1); cum columns extracted, not read |
| Tape minutes | `minute_ist` (completeness only) | + `role, opt_type, strike, expiry, oi` for T4 (F-2); completeness unchanged |
| everything else | — | unchanged |

### P2 §1.2 (files and hashes)
Hashed files unchanged in kind: `scoring_extract.sql` (**changes**, F-1/F-2), `run_extract.sh` (**unchanged**, still
hashed and re-listed), `score.py` (**changes**), `wilcoxon.py` (**unchanged**). The tester files change (F-3).

### P2 §1.3 (definitions pinned) — replaced paragraphs

**Clock reconciliation.** Unchanged: G = floor5(run ts); tape row stamped G covers [G−5, G); v0.4 §1 states the same.

**S (replaces the v0.2 paragraph).** For a cycle at grid point G, the window legs are the CE/PE rows of the front expiry
with a `tape_strike_cycle` row at `ts_ist` ∈ {G−25, G−20, …, G} (six stamps, `s_window_bins = 6`,
`s_window_min = 30`). The window **strike set** is still the strikes with a row at G (P2 §1.3 "Front expiry and window",
unchanged). For each window strike and leg:
- Buy = Σ `buy_5` over the six stamps present, Sell = Σ `sell_5`, Uncl = Σ `uncl_5`, Gap = Σ `gap_5`.
- A strike-leg with only some of the six rows contributes the rows present.

Then:
- D₃₀ = −Σ (γ_call·(Buy_CE − Sell_CE) + γ_put·(Buy_PE − Sell_PE)), with γ the run's `gamma_call` / `gamma_put`. A missing chain row or a NULL γ contributes 0 from that leg, counted.
- Share = Σ(Buy+Sell) ÷ Σ(Buy+Sell+Uncl) over window legs and the six bins; gap is in neither, and its total is reported.
- S is undefined (counted by reason) when the denominator is 0, when share < 50 % (`2·(b+s) < (b+s+u)`; exactly 50 % is defined), or when D₃₀ = 0 (`d_zero`).

`buy_cum` / `sell_cum` are not read for S anywhere (asserted by `ha-s-window`). The pin's S_pin (H-A secondary) uses the
same trailing-window construction restricted to the pin strike: one S definition, one function.

**R(T) (replaces).** R(T) = (max `high` − min `low`) over bars labelled m with **G_T ≤ m ≤ G_T + 29**, where G_T =
hm(run ts) (the run minute; m0 = hm(t_dt), **was** hm + 1, the §6 defect), **excluding the 15:29 bar always**, ÷
`straddle_atm`. "Present" counts only bars that may enter the range: the 15:29 bar never counts towards the 25.
`r_horizon_min = 30` and `r_min_bars = 25` are unchanged.

Note the clock subtlety: hm(run ts) for a run at G:06 is G. So the window is bars G…G+29 = [G:00, G+30:00), v0.4 §1
literally. The spot clock check (≥ 95 % of bars in 09:15–15:29) is unchanged.

**Rule-0a statement (replaces "R reads only bars with label > T").** R reads only bars with label ≥ hm(T). That is the
outcome, by design. The bar labelled hm(T) starts at G:00, about 6 s before the run's ts, so the outcome window begins
≈ 6 s before the snapshot. That is v0.4's literal [T, T+30), and the unit check is re-pinned to it. S reads only tape
stamps ≤ G ≤ T (unchanged).

**H-A secondary — added.** `s_sign_changes_1000_1445` per symbol-day = the number of adjacent pairs, in G order among
cycles with 600 ≤ G ≤ 885 and S defined, whose S differs. Reported beside the exploration median 2.5. No decision.

**Subscribed-window coverage — added (descriptive).** Per cycle:
- `call_wall_in_window` / `put_wall_in_window`: the run's `tape_chain_runs` wall strike is in the window strike set at G;
- `gexabs_share_in_window` = Σ|`gex_cr`| over window strikes ÷ Σ|`gex_cr`| over all front-run strikes, exact, rendered at 6 dp.

Per symbol-day: the medians of the three (a boolean's median over cycles reported as the fraction True, with its n).

This is a ratio of magnitudes, so it is scale-invariant; `sc-sign-only` gains a cell asserting it is unchanged under the
×1000 scaling. The `score.py` docstring line "no gex_cr magnitude reaches the output" becomes "no gex_cr magnitude, only
the scale-free window share, reaches the output".

**H-B per-label — added (descriptive).** Two views per symbol, beside the pooled figures (which are unchanged and alone
feed `decide_hb`):
- **attribution:** each covered event is attributed to the label set of the tape event that set its pooled lead (`T1`, `T2`, `T3`, or a multi-label set such as `T1+T2`). Per attribution class: covered count and median lead. The classes' covered counts sum to the pooled covered count. `hb-per-label` asserts it.
- **any-label:** for each label L, over events whose kind admits L (MATCH), coverage = the fraction with an L-labelled event at K in (T−60, T], and the median of the nearest L lead.

**T4 OI_MOVE — added (descriptive; never in MATCH, never in `idx`).** Source: `tape_minute.oi` per (strike, leg), front
expiry, CE/PE (F-2). For a strike-leg and a 5-minute cycle [G, G+5):
- **base** = `oi` of the latest minute row with label < G;
- the **first** minute m ∈ [G, G+5) with `100·|oi_m − base| ≥ e2_oi_move_pct·base` (and base > 0) fires one T4, stamped **(m+1):00**, when the minute's OI is known;
- at most one T4 per strike-leg per cycle.

A T4 is retained only if its strike is the reference run's call wall (CE leg) or put wall (PE leg). The reference run is
the latest front run with ts ≤ the stamp, as for T1–T3 (P2 §1.3). Reported per symbol: for merged E2-call (E2-put) events
at window strike K, the coverage by a CE (PE) T4 at K in (T−60, T], and the median nearest-preceding lead, n stated.
Events ≥ 10:00 only (DEF-5 analogue). Stored in its own index, so no code path from T4 reaches `_lead_us(d["idx"], …)`.

**Descriptive block isolation.** `run()` builds the result as today, then calls one function `descriptive(day_data)`
that returns `result["descriptive"]`. No decision function takes an argument derived from it, and the guard proves it.

**Pre-registered literals.** `PARAMS` gains `s_window_min: 30`, `s_window_bins: 6` and, per F-4, `e2_oi_move_pct: 5`.
`PREREG_SHA` becomes v0.4 `b45477d3…acd57`. Report header: "pre-registration v0.4".

**Hash check (replaces).** `check_hashes` reads the **last** ledger entry: the block after the last heading
`## Entry ... pre-registration v0.4`. It requires that block to name `PREREG_SHA` and to list all four files with
matching sha256. A ledger holding only the v0.2 entry, or a v0.4 entry with the v0.2 hashes, is refused (rc 3,
`HASH MISMATCH`). v0.2's parser took the **first** regex match in the file, which after appending would have been the
old entry.

### P2 §1.4 (extract)
Two SELECT lists grow (F-1, F-2). Nothing else changes: no join, aggregate, function or clock filter.

### P2 §2 (build) → this plan's §3–§4.

---

## 2. The four changes in code (`services/tape_scoring/score.py`)

| # | Where | Change |
|---|---|---|
| 1 | `spot_range` (`:285-290`) | `m0 = hm(t_dt)`; bars `m0 … m0+29`, skipping label 929; count only those |
| 2 | `tape_sign` (`:251-282`), cycle loader in `score_day_symbol` (`:369-380`) | rows keyed by stamp; per (strike, leg) sum `buy_5/sell_5/uncl_5/gap_5` over stamps G−25…G; same S / share / d_zero logic; cum columns no longer parsed into the S path |
| 3 | `score_day_symbol` + new `descriptive()` | window coverage per cycle; sign-change count; per-label attribution + any-label; T4 from `tape_minute` |
| 4 | `PARAMS`, `PREREG_SHA`, `COLS`, `check_hashes`, `render_report` | two to three literals (F-4), v0.4 sha, the new SELECT columns (F-1, F-2), last-entry ledger parse |

`hb_symbol`, `ha_symbol`, `decide_*`, `combine`, the null, the bootstrap, the seed stream, quarantine, run-once and the
trigger are unchanged. One check on the seed: `seed_bytes()` hashes `score.py` itself, so the null stream changes with
the file. That is the existing design; the hashed file fixes the stream.

---

## 3. Fixture changes (`tests/tape_scoring/gen_fixture.py`)

**Bins instead of one cum row.** `Plan.rows()` now emits, for each planted cycle G, the six stamps G−25…G for every
subscribed strike-leg. Contributions are accumulated in a dict keyed (strike, leg, stamp) and summed, so overlapping
windows of close runs add rather than collide. `buy_cum`/`sell_cum` are written as an **independent planted cumulative
series**: `Plan.add_run(..., S=..., S_cum=...)`, with `S_cum` defaulting to S. That makes the cumulative sign a separate
planted fact.

The designated leg carries the window net across the six bins (net split as planted). `uncl_5` carries the planted share
on the same leg. FUT rows are emitted on every stamp and must be ignored.

**New planted scenarios (each states its truth, computed in the generator, never read off a run):**
1. **R edges:** a cycle whose extreme high sits in the bar labelled G (included), and one whose extreme sits at G+30 (excluded). Expected R = planted range ÷ straddle, computed in the generator to 6 dp.
2. **15:29:** a G = 900 cycle with bars 900…914 present and an extreme high on bar 929. Expected R ignores it, and the 15:29 bar does not count towards 25. A second cycle has 24 regular bars plus the 15:29 bar and must be excluded (`cycle_r_bars_lt_min`).
3. **S window ≠ S cum:** on a chosen set of cycles (every third in the omnibus), `S_cum = −S`.
4. **Five vs six bins:** one cycle whose net sits in bin G−25 only, planted so S over six bins = +1 and over five = −1 (the other five bins net the opposite, smaller).
5. **Partial strikes:** one strike with rows at only 4 of the 6 stamps (G−15…G); its contribution is planted and included in the expected D₃₀ sign.
6. **Share 49 / 51:** two cycles at window share 49 % (undefined) and 51 % (defined), with the cumulative share planted on the other side of 50 %, so a cumulative-share mutant flips both.
7. **d_zero:** a cycle with window net 0 and share 100 %; counted as `cycle_s_undefined_d_zero`.
8. **T4 vs T1:** an E2-call at K = call wall at T. A T1 (CONC on CE at K) is stamped at T−10 min, and a CE `oi` step of +6 % at K in the minute that ends at T−1 min (a T4 stamped T−60 s). Expected: H-B lead 10 min (T1), T4 lead 1 min under `descriptive` only.
9. **Walls outside the window:** a day with `unsub` containing the call wall strike. Expected: `call_wall_in_window` False on its cycles; `gexabs_share_in_window` = the planted share (computed from the planted `gex_cr`).

`tape_minute` rows gain `role, opt_type, strike, expiry, oi` (F-2). Completeness rows are unchanged in count. The layout
is still parsed from `scoring_extract.sql`, so the generator can only write what the extract emits.

---

## 4. Guards and mutants

Existing 19 guards stay. `sc-params` becomes `sc-params-v04` (same body plus the new literals). `ha-clock`, `ha-delta`,
`ha-s-definition` and `sc-sign-only` run on the new fixture and the new S. New guards (each must fail for the reason it
names):

| Guard | PASS (planted truth) | Mutant(s), each ×5 with control |
|---|---|---|
| `ha-r-window` | R equals the planted range over bars G…G+29 to 6 dp; the G+30 extreme excluded; the G extreme included; the 15:29 extreme excluded; the 24+1 cycle excluded | M-SC-R-ONE-BAR-LATE (`m0 = hm(t_dt) + 1`), M-SC-R-INCLUDES-1529 (the 929 skip removed) |
| `ha-s-window` | S = the planted trailing-30 sign on every cycle and ≠ the planted cumulative sign on the chosen cycles; 4-of-6 strike included; 49 % undefined, 51 % defined on window volume; d_zero counted | M-SC-S-CUMULATIVE (S read from `buy_cum`/`sell_cum`), M-SC-S-FIVE-BINS (stamps G−20…G), M-SC-S-SHARE-CUMULATIVE (share from the cum columns) |
| `hb-per-label` | attribution classes sum to the pooled covered count; each planted event's class = its planted label | M-SC-LABELS-POOLED-ONLY (every event attributed to the pooled bucket) |
| `hb-t4-separate` | pooled H-B lead for the planted E2 = 10 min (T1); T4 lead 1 min under `descriptive` only; T4 absent from MATCH and `idx` | M-SC-T4-IN-MATCH-SET (T4 entries added to `idx` and `"T4"` to E2's MATCH) |
| `sc-descriptive-isolated` | the verdict JSON (`H_A`, `H_B`, per-symbol `H_A` / `H_B` minus the descriptive block) is byte-identical when `descriptive()` is replaced by one returning `{}` | M-SC-VERDICT-READS-DESCRIPTIVE (`decide_hb` fed a coverage taken from the descriptive T4 figure) |
| `sc-params-v04` | `PARAMS` == the §5 literals with v0.2 values + `s_window_min=30`, `s_window_bins=6`, `e2_oi_move_pct=5` (F-4); `r_horizon_min=30`, `r_min_bars=25` | M-SC-DELTA-009 (`ha_min_median_delta` 1/10 → 9/100); the existing M-SC-PARAM-CHANGED re-pointed here |

`sc-hash-check` gains three cells:
- a tree whose ledger has a v0.4 entry for the current files passes (control);
- a ledger with only a v0.2-style entry is refused;
- a v0.4 entry listing stale hashes is refused.

`make_tree()` writes the v0.4 entry format. The existing mutant M-SC-HASH-SKIPPED still targets it.

Unit checks added:
- `e2_oi_move_pct == chain_events.OI_PCT`;
- the Rule-0a R check re-pinned to label ≥ hm(T);
- a T4 stamp at (m+1):00, never m:00 (one-character mutant shape).

**Counts.** Guards 19 → **24**. Mutants 29 → **38** (+9: R ×2, S ×3, labels, T4, descriptive, delta). The existing
mutants are re-anchored where their target line text moves, and each anchor must match exactly once or the harness
reports MUTANT NOT APPLIED (a FAIL). `tests/run_offline.sh` stays at **40 steps**; lines 212–213 change their labels
from `(19)` / `(29 x5` to `(24)` / `(38 x5`.

**Rule 23.** On Windows `resource` is absent, so the `ulimit -v` clause cannot be enforced here. That is the same as v0.2
and is stated in the report. Inside 08:30–15:45 IST the two suites run only under `TAPE_RULE23_OVERRIDE_R1=1`
(operator ruling R-1, Local). The full `run_offline.sh` is not run in-window.

---

## 5. Ledger (`docs/tape/scoring_hashes.md`, appended; the v0.2 entry stays verbatim)

```
## Entry 2026-11-05 — pre-registration v0.4
Pre-registration v0.4 sha256: `b45477d36eba6930ab41171a3405c10cf6ecb0bd1fbb04b52d09a5c2129acd57`
Head sha of the commit that carries the four hashed files (branch `tape/scoring-v04`): `<code-commit sha>`
| services/tape_scoring/scoring_extract.sql | <new> |   (changed: tape_strike_cycle +buy_5,sell_5,uncl_5,gap_5; tape_minute +role,opt_type,strike,expiry,oi)
| services/tape_scoring/run_extract.sh | e586dfb7... | (unchanged)
| services/tape_scoring/score.py | <new> |
| services/tape_scoring/wilcoxon.py | e4dbace5... | (unchanged)
<the v0.4 §6 defect paragraph, verbatim>
No tape-vs-outcome query has run on a confirmatory day before this hash.
```
Two commits, as in v0.2: (1) code + tests + plan; (2) the ledger naming (1)'s sha. `sc-hash-check` on a non-fixture run
then verifies against this entry. The operator copies the ledger beside v0.4 on staging `main`.

---

## 6. Evidence the build will report
Files and commits; `tape/scoring-v04` pushed to tape-staging only (never origin, no force), head sha; the guard table
with each mutant's 5/5 line; run_offline.sh count before/after; the three changed/unchanged sha256s and the ledger entry
verbatim; the `--fixture` CLI run output; what was not verified; slips. Commit message as briefed.

## 7. Decisions for the operator
1. **F-1:** add `buy_5, sell_5, uncl_5, gap_5` to the `tape_strike_cycle` SELECT. Required by v0.4 §1; no alternative.
2. **F-2:** T4 source = `tape_minute.oi`, extending the `tape_minute` SELECT with `role, opt_type, strike, expiry, oi` (recommended), or `tape_strike_cycle.oi_last` (5-minute grain; lead ≈ 0.1 min by construction; the planted 1-min guard cannot be built).
3. **F-3:** permission to edit `tests/test_tape_scoring.py` and `tests/tape_scoring_mutants.py`.
4. **F-4:** `e2_oi_move_pct: 5` as a third new `PARAMS` key (listed by `sc-params-v04`), or reuse `chain_events.OI_PCT` by import (which would add a `merdian_compute` import to the hashed scorer; not recommended).

---

## 8. Operator rulings (2026-11-05) and what they changed

| # | Ruling | Effect on the build |
|---|---|---|
| 1 | F-1 approved | `tape_strike_cycle` SELECT gains `buy_5, sell_5, uncl_5, gap_5` |
| 2 | F-2 approved **with a condition**: `tape_minute.oi` feeds T4 only as an OPTIONAL input; absent -> `descriptive.t4 = "NOT COMPUTED (no tape_minute input)"` and every verdict byte-identical (guard + mutant); put the SELECT last if `run_extract.sh` aborts on the first failure; confirm the `oi` column and type | `oi` is `bigint` in `tape_minute` (`services/tape_db/tape_schema.py:43`). **Deviation, stated:** the condition could not be met by extending the existing `tape_minute` SELECT, for two reasons. First, `tape_minute.minute_ist` feeds completeness (DEF-2), so an absent `tape_minute` file quarantines the day and the verdicts change. Second, `run_extract.sh` runs relations in its own `RELS` order (`run_extract.sh:19`), not file order, and aborts on any failure (`set -euo pipefail`; `exit 1` at `:51-53`, `:61-62`), so "last in the file" changes nothing. Built instead: a **separate pure SELECT `-- @name tape_minute_oi`** over `public.tape_minute` (`symbol, trading_day, role, opt_type, strike, expiry, minute_ist, oi, run_id`), last in `scoring_extract.sql` **and** last in `RELS`, on an **optional path in `run_extract.sh`**: a refused read, a missing or zero count, or a failed day prints `OPTIONAL SKIP` and writes no file; it never aborts. `tape_minute` (completeness) is unchanged. So `run_extract.sh` changes and is re-hashed (the plan had said unchanged). |
| 3 | F-3 approved (edit `tests/test_tape_scoring.py`, `tests/tape_scoring_mutants.py`) | both edited; the mutant harness COPY list gains `merdian_compute/tape/chain_events.py` (read by `ast`, never imported) |
| 4 | F-4 approved: `e2_oi_move_pct = 5`; unit check against `chain_events.OI_PCT` in the test file only; no import in `score.py` | `u_oi_pct` reads `OI_PCT` with `ast` and also asserts `score.py` imports nothing from `merdian_compute` |
| 5 | Hash-check change approved; add `M-SC-HASH-FIRST-ENTRY` and a ledger-with-both-entries cell | `check_hashes` reads the last `## Entry` block and requires `PREREG_SHA` in it; `sc-hash-check` cells: current v0.4 entry passes; **both entries (stale v0.2 first, current v0.4 last) passes**; v0.2-only refused; v0.4-with-stale-hashes refused; one byte in each of the four files refused |

## 9. Build record (2026-11-05)

**Final counts.** Guards 19 -> **25**:
- `sc-params` renamed `sc-params-v04`;
- new: `ha-r-window`, `ha-s-window`, `hb-per-label`, `hb-t4-separate`, `sc-descriptive-isolated`, and `sc-t4-optional` (ruling 2).

Unit checks 17 -> **21**:
- `u_lookahead` re-pinned to labels hm(T)..hm(T)+29;
- new: `u_oi_pct` (2 cells) and `u_t4_stamp` (2 cells).

Mutants 29 -> **40**, each caught ×5 with 5/5 controls:
- `M-SC-R-ONE-BAR-LATE`, `M-SC-R-INCLUDES-1529`, `M-SC-S-CUMULATIVE`, `M-SC-S-FIVE-BINS`, `M-SC-S-SHARE-CUMULATIVE`, `M-SC-LABELS-POOLED-ONLY`, `M-SC-T4-IN-MATCH-SET`, `M-SC-VERDICT-READS-DESCRIPTIVE`, `M-SC-DELTA-009`, `M-SC-T4-ABSENT-AS-ZERO`, `M-SC-HASH-FIRST-ENTRY`;
- `M-SC-PARAM-CHANGED` re-pointed to `sc-params-v04`.

`tests/run_offline.sh`: **40 steps before, 40 after**. Only the labels of steps 39/40 change, `(19)` -> `(25)` and `(29 x5` -> `(40 x5`.

**Each new mutant fails for the reason it names** (the failing cells were printed per mutant, not just the exit code):
- R-ONE-BAR-LATE breaks the "T included" and "T+30 excluded" cells.
- R-INCLUDES-1529 breaks the "15:29 excluded" and "24 + 15:29 excluded" cells.
- S-CUMULATIVE flips 600/630 and both share cells.
- S-FIVE-BINS flips 690 only.
- S-SHARE-CUMULATIVE flips 750/780 only.
- LABELS-POOLED-ONLY breaks attribution `{'pooled': 3}`.
- T4-IN-MATCH-SET makes the H-B lead 1 instead of 10.
- VERDICT-READS-DESCRIPTIVE breaks byte-identity.
- DELTA-009 breaks the parameter diff.
- T4-ABSENT-AS-ZERO gives coverage 0 instead of NOT COMPUTED.
- HASH-FIRST-ENTRY refuses the current and the both-entries ledgers.

**Planted fixture beliefs, measured.**
- **Omnibus planted:** H-A YES, H-B YES, as stated in its docstring. Every third H-A cycle now carries a cumulative sign opposite to its window sign.
- **Omnibus `--null`:** H-B NO; H-A is unaffected, since `--null` moves only tape events, and stays YES.

**Additions beyond the plan, stated.**
- `sc-t4-optional` also runs `run_extract.sh` under bash against a fake `roq.sh`. A failing optional statement gives exit 0, `OPTIONAL SKIP` and no file, and the rest is extracted. A failing required relation gives exit 1. The control extracts the optional relation.
- `sc-descriptive-isolated` carries the "walls outside the window" planted day: call wall unsubscribed gives an in-window fraction of 0 and a |gex| share of 84/85, computed from the planted `gex_cr`.
- `counts.gap_cum_total` is renamed `gap_window_total`, because the gap reported is now the window's.
