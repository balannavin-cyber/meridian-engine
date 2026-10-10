# P2 — Dealer-side check: design note and pre-registration (DRAFT for operator review)

| Field | Value |
|---|---|
| **Status** | **PRE-REGISTERED.** Committed with its scorer and extract SQL **before** Part 1, the first query that reads any position value. Its `git hash-object` is recorded in the result doc. After commit, any edit to §4 or §5 voids this note, and a new pre-registration is required. Part 0 ran 2026-10-10 08:30–08:34 IST; it read schema, coverage and policies only (§3a). |
| **Track item** | Roadmap §2.1 **P2**, order 1st (ruling **S94-A**, `docs/research/s92_parity/rulings_s94.md`) |
| **Risk class** | **RO**. Reads only, through `bin/roq.sh` (`merdian_ro`). Writes nothing to the database. |
| **Repo path on commit** | `docs/research/s94_priority/P2_dealer_side_design_2026-10-10.md` |

## 1. The question

Every exposure number on the board carries a sign. Positive `gex_cr` is labelled *dampening*, and
negative is labelled *amplifying* (ADR-015, sign convention unchanged from ADR-014 §2.3). The
arithmetic is CE gamma counted **positive** and PE gamma counted **negative**. That reads as
**dealer** gamma only if the dealer side is **net long calls and net short puts**. ADR-015 says so
itself: the stored quantity is *"positioning gamma, not dealer gamma"*, and the two coincide only
under a stylised dealer fact. (ADR-015's prose states that fact as *"dealers short calls and long
puts"*. That is the inverted gloss owed as a ruling under P6 carry 7. This note follows the
arithmetic, not the gloss.)

**P2 asks one question:** in NSE's daily participant-wise open interest, does the category that
plausibly stands in for dealers hold the position the board's sign assumes?

## 2. What the data can and cannot answer — stated before measuring

| Limit | Consequence |
|---|---|
| **NSE only.** Participant-wise OI comes from NSE (NSCCL); BSE publishes no equivalent (S63, ENH-115 scope resolution). | **P2 covers NIFTY's sign only. SENSEX is untestable by this route**, and the result must not be extended to it. |
| **Index-option aggregate, not per underlying.** The NSE file reports index options summed across all NSE index option underlyings. *This is to be confirmed in Part 0 from the stored columns, not assumed.* | P2 tests the **aggregate** index-option book. NIFTY is one constituent of it. If Part 0 shows a per-underlying split exists, the note is amended **before** commit. |
| **Daily, end of day, no strikes, no expiries.** | **Sign only, not magnitude, and not by strike.** P2 cannot say *where* the dealer is long or short, so it cannot validate the per-strike map, the flip or the walls. |
| **Contract counts, not gamma.** | A far-OTM contract counts the same as an ATM one. P2 tests the sign of **net contract position**, which is a necessary condition for the gamma sign, not a sufficient one. |
| **Nobody is labelled "dealer".** The categories are Client, DII, FII and Pro (plus TOTAL). | The proxy has to be chosen **before** measuring (§4). |

So P2 can **refute** the sign convention cleanly, if the proxy holds the opposite position. A
pass, though, only shows that the sign is **consistent** with the aggregate book. It does not
validate any number on the board.

## 3. Part 0 — preconditions, read-only, before this note is committed

Part 0 reads schema and coverage only. It does **not** read any position value, so running it
does not count as having seen outcomes.

1. **Schema.** Read `information_schema.columns` for `participant_oi_daily` and
   `v_participant_oi_latest`. Record every column name and type. Confirm, or correct, §2 row 2
   (per-underlying split, yes or no) and the units.
2. **Readability (TD-S81-NEW-16).** Run a row count as `merdian_ro`. It must be **> 0**; a zero
   is the silent-RLS shape and blocks P2 until it is resolved. Control: the same count on a
   table `merdian_ro` is known to read (`gamma_metrics`), run in the same execution.
3. **Coverage.** Min and max trade date, count of distinct dates, and count of rows per
   participant category per date. The expectation, from S63, is about **270 days from
   2025-05-28** plus forward accrual, **5 rows per date** (4 categories + TOTAL).
4. **Rule 13.** Check `public.data_contamination_ranges` for any range that names this table.
5. **The sign in code.** On the box, find the line where the per-strike writer signs PE gamma:
   `grep -rn "gamma_put\|gex_cr" --include=*.py . | grep -v test | head -40`. Record the file and
   line in §1, so the convention P2 tests is the one the code actually applies.

Part 0's outputs are recorded in §3a, and §4 and §5 are adjusted if Part 0 requires it. **Then** the note is committed.

## 3a. Part 0 results (2026-10-10, operator-run, `bin/roq.sh` unless stated)

| Check | Result |
|---|---|
| Schema | `participant_oi_daily`: `id, exchange, trade_date, participant`, futures index/stock long/short, **`opt_idx_call_long, opt_idx_put_long, opt_idx_call_short, opt_idx_put_short`**, the stock-option legs, `total_long, total_short, source, created_at`. **No per-underlying column, so §2 row 2 is confirmed**: index options are one aggregate. Units are **not** stated in the schema; the NSE source file reports contracts, but that is **unverified here** and the verdict does not depend on it (§4 compares signs only). |
| Readability | **Before:** `merdian_ro` read **0** rows, against a control of 1000 (`gamma_metrics`, capped). Cause measured: `relrowsecurity = t` with **zero policies** on both `participant_oi_daily` and `data_contamination_ranges`. **Fix:** operator DDL `sql/2026-10-10_s94_merdian_ro_read_policies.sql` (one `SELECT` policy per table for `merdian_ro`, per ADR-031 D6). **After:** 1,700 and 1. |
| Coverage | 2025-05-28 → 2026-10-09; **340** distinct dates; **1,700** rows; exchange `NSE` only; Client / DII / FII / Pro / TOTAL each 340 rows over 340 dates; **0** dates without exactly 5 rows. |
| Rule 13 | 1 registry row: `BREADTH-STALE-REF-2026-03-27`, breadth fields only, 2026-03-27 → 2026-04-23. Its `affected_tables` does **not** include `participant_oi_daily`. **No overlap.** (The registry itself was unreadable to `merdian_ro` before this fix, so it is filed as **TD-S94-NEW-1**.) |
| Sign in code | `compute_gamma_metrics_local.py:133`: `return -base if option_type == "PE" else base`. CE gamma is counted **+** and PE gamma **−**. Read as dealer gamma, that means dealer **net long calls, net short puts**, which is exactly what §4 tests. |

**Integrity assertion added by Part 0, fixed at commit.** Every contract has a buyer and a seller,
so for **TOTAL** on every date, `opt_idx_call_long = opt_idx_call_short` and
`opt_idx_put_long = opt_idx_put_short`. Separately, the four categories must sum to TOTAL on each
of the four legs. The scorer asserts both before scoring. If either fails on any date, P2 **stops
and reports**: it neither drops the date nor adjusts anything.

## 4. Definitions (fixed at commit)

For participant category *k* on trade date *d*, in index options:

- `net_call(k,d) = call_long − call_short`
- `net_put(k,d)  = put_long − put_short`

**Board convention holds for k on d** ⟺ `net_call > 0` **and** `net_put < 0`.
**Board convention inverted for k on d** ⟺ `net_call < 0` **and** `net_put > 0`.
Anything else is **mixed**. An exact zero counts as mixed.

**Dealer proxy, fixed before measuring:**
- **Primary: Pro.** Proprietary trading members are the category that contains exchange market
  makers and prop desks.
- **Secondary: Pro + FII, summed.** FII is the other large option writer in public commentary.
  This is stated as a hypothesis, not as a fact.
- **Reported descriptively, not scored:** Client, DII, and each category alone.

## 5. Verdict rule (fixed at commit)

The window is **all trade dates in `participant_oi_daily` from its first date through
2026-10-09** (the last session before this note). Part 0 measured this as **2025-05-28 → 2026-10-09, n = 340**;
the scorer asserts n = 340. Nothing is fitted, so there is no
calibration/holdout split. The thresholds below are fixed here and are not tuned.

Let *h* be the share of dates on which the convention **holds** for the primary proxy, with a
Wilson 95 % interval.

| Outcome | Rule | Meaning |
|---|---|---|
| **CONSISTENT** | lower bound of *h* ≥ 0.80 | The aggregate book is consistent with the board's sign. Assumption Register row → *VALIDATED (aggregate, NSE, sign only)* |
| **INVERTED** | lower bound of the **inverted** share ≥ 0.80 | The board's dealer reading is backwards. Assumption Register row → *REFUTED*, and a ruling is required before any sign-dependent work (P5–P7) |
| **REGIME-DEPENDENT** | neither of the above | The sign holds on some days and not others. Report the split by DTE bucket and by 5-day spot trend, as **reporting strata only**, never as a selection. Any conditional claim is a **new** pre-registration. |

Why 0.80: the convention is used every cycle with no regime switch, so it is only usable as a
standing assumption if it holds on at least four days in five. Any lower and a standing sign is
wrong often enough to matter. This threshold is set from the use, not from the data.

The secondary proxy is reported with the same three-way rule. If primary and secondary disagree, the
verdict is **REGIME-DEPENDENT**, and the result doc says so.

## 6. Outputs

- Part 0: recorded in §3a above.
- `p2/part1_extract.sql`, committed with this note. It is a `COPY … TO STDOUT CSV HEADER` of
  `trade_date, participant` and the four `opt_idx_*` legs, for dates ≤ 2026-10-09, run through `bin/roq.sh`.
- `p2/part1_extract_2026-10-10.csv`: its output, committed with the result.
- `p2/p2_score.py`, committed with this note. Standard library only, run as `python3 -I`. It
  asserts n = 340 dates × 5 categories and the §3a integrity checks, then computes §4/§5. It
  prints the verdict and a per-category table, and exits non-zero if any assertion fails.
- `P2_dealer_side_result_<date>.md`: the verdict, the table, and the limits from §2 repeated.

## 7. What P2 does not do

It does not change any sign, view, writer or board element. It does not test SENSEX. It does
not validate the per-strike map, the flip or the walls. It does not use OI changes or OI × price
classification (that is the target's four-case grid, which is off the track).
