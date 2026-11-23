# Part B results — is the own-solved history clean enough to carry the look-back?

Read-only. Every read through `bin/roq.sh` as `merdian_ro`, every run under
`( ulimit -v 700000; … )`. No write, no vendor call, no outcome computed. Queries in
`queries/`, raw payloads in `_partB_raw.txt`, aggregation in `analyze_partB.py` →
`_partB_agg.txt`, timings in `_partB_run.log`.

**Rule 13 preflight — PASS, no exclusion** (`queries/q08_contamination_partB.sql`,
`_q08.txt`). Four ranges in `public.data_contamination_ranges`; none names
`hist_option_greeks_1m`, `hist_option_bars_1m` or `hist_spot_bars_1m`. The only one
overlapping the window, `BREADTH-STALE-REF-2026-03-27` (2026-03-27 → 2026-04-23), names
breadth / signal / `gamma_metrics` relations and breadth fields. `symbols` is NULL on
three of the four, which per S100-J means every symbol; immaterial here since none is in
relation scope.

**Market-hours procedure.** EXPLAIN (no ANALYZE) first, gate = no sequential scan on a
`hist_*` relation and no scan estimated over ~20,000 rows; then one query per symbol-day,
5 s sleep, stop at the first timeout or any query over 10 s, no retry. The gate **passed**
(`queries/explain_qB_NIFTY_2025-04-01.txt`): Index Only Scan on
`hist_option_bars_1m` via `idx_hist_option_chain_snap` (est 675), Index Only Scan on
`hist_option_greeks_1m` via `uniq_hist_greeks_row` (est 2,325), Index Scan on
`hist_spot_bars_1m` via `idx_hist_spot_ts` (est 1). **24 of 24 queries ran, 3.13–4.13 s
each, zero timeouts, zero stops.**

---

## B1 — the sample

12 monthly sample days per symbol, chosen as the first `DONE` day of each month in
`hist_greeks_backfill_log` with `rows_written > 0` (`_q01.txt`), window 2025-04-01 to
2026-03-30. Three minutes each: 10:00, 12:30, 15:00, taking the bar at second `:59`.

**All 72 minutes resolved at offset 0 from `:59`** — the `±120 s` tolerance was never
drawn on, so the "or nearest within 2 minutes" clause is untested by this data. No NULL
spot, no NULL expiry. `dte` 1–6, **no 0-DTE minute**, consistent with B0 rule 4 making
expiry days `SKIPPED_EXPIRY`.

Spot came from `hist_spot_bars_1m.close` at the same `bar_ts`, which is the relation the
backfill itself used (B0, `:412-417`).

The backfill log for the window: NIFTY 194 `DONE` days + 53 `SKIPPED_EXPIRY`, 8,596,818
rows, 376,297 with NULL `iv`; SENSEX 193 `DONE` + 52 `SKIPPED_EXPIRY`, 10,653,668 rows,
150,424 NULL `iv`.

## B2 — coverage by leg

Legs in `hist_option_bars_1m` with `oi > 0`, front expiry, at the 36 sampled minutes per
symbol, matched to `hist_option_greeks_1m` on
`(instrument_id, bar_ts, strike, option_type, expiry_date)`.

| symbol | legs oi>0 | γ > 0 | γ NULL | γ = 0 | no greeks row | % legs γ>0 | % **OI** γ>0 |
|---|---|---|---|---|---|---|---|
| NIFTY | 4,251 | 4,058 | 193 | **0** | **0** | 95.46 | **99.30** |
| SENSEX | 5,631 | 5,588 | 43 | **0** | **0** | 99.24 | **99.82** |

Two zeros carry information:

- **`no greeks row` = 0.** Every bars leg with open interest has a greeks row. B0 rule 5
  would withhold a row for a leg with `close ≤ 0`; no such leg has OI, matching Part A's
  finding that every leg with OI also has a price.
- **`γ = 0` = 0.** The own solve never writes a literal zero — unlike the vendor, whose
  blank *is* a zero (Part A). Here a failure is a NULL (B0 rule 8). So on this store,
  NULL and 0 are not confusable, and the Part A ambiguity does not recur.

**Every NULL is ITM.** By bucket (counts pooled over all sampled minutes):

| symbol | leg | OTM | ITM 0–1 % | ITM 1–2 % | ITM 2–5 % | ITM > 5 % |
|---|---|---|---|---|---|---|
| NIFTY | CE | 0 / 1,542 | 0 / 180 | 8 / 169 | 18 / 156 | 0 / 20 |
| NIFTY | PE | 0 / 1,595 | 11 / 181 | 54 / 170 | 83 / 195 | 19 / 43 |
| SENSEX | CE | 0 / 2,317 | 0 / 284 | 4 / 110 | 8 / 22 | 0 / 2 |
| SENSEX | PE | 0 / 2,381 | 0 / 293 | 21 / 163 | 10 / 59 | — |

**0.0 % in the OTM bucket, both legs, both symbols.** The bisection fails only where the
price is intrinsic-dominated, which is the same place the vendor blacks out (Part A) and
for the same reason. This is the mechanism behind B4's result, below.

## B3 — call against put at one strike

Strikes carrying **both** a call γ > 0 and a put γ > 0; ratio = call γ / put γ. Pooled
over all sampled minutes:

| symbol | band | strikes | γ p10 | γ **median** | γ p90 | iv p10 | iv **median** | iv p90 |
|---|---|---|---|---|---|---|---|---|
| NIFTY | within 1 % | 350 | 0.8289 | **0.9749** | 1.1123 | 0.8800 | **1.0555** | 1.3669 |
| NIFTY | 1–3 % | 429 | 0.8968 | **1.0165** | 1.7166 | 0.7796 | 1.0481 | 1.4624 |
| SENSEX | within 1 % | 579 | 0.8127 | **0.9806** | 1.1004 | 0.8838 | **1.0269** | 1.3475 |
| SENSEX | 1–3 % | 300 | 0.9260 | **1.0032** | 1.1345 | 0.8311 | 1.0090 | 1.3782 |

In theory a call and a put at one strike **share one gamma**; these are solved
independently from each leg's own close, so the spread is entirely solver and input
error. The pooled medians sit inside [0.95, 1.05] on both symbols, but the **p10–p90
spread is ±11 % to ±19 %** within 1 % of spot, and the iv medians above 1 say calls solve
to a higher IV than puts at the same strike — the signature B0 predicted from a flat
`r = 6.5 %` with no market forward.

### Per-day median, within 1 % of spot — the gate input

| day | NIFTY | in band | day | SENSEX | in band |
|---|---|---|---|---|---|
| 2025-04-01 | 0.8976 | NO | 2025-04-02 | 0.9819 | YES |
| 2025-05-02 | 1.1066 | NO | 2025-05-02 | 1.1340 | NO |
| 2025-06-02 | 0.9641 | YES | 2025-06-02 | 1.0030 | YES |
| 2025-07-01 | 0.9428 | NO | 2025-07-02 | 1.0613 | NO |
| 2025-08-01 | 1.0883 | NO | 2025-08-01 | 1.0830 | NO |
| 2025-09-01 | 0.8817 | NO | 2025-09-01 | 0.8380 | NO |
| 2025-10-01 | 0.9090 | NO | 2025-10-03 | 0.9564 | YES |
| 2025-11-03 | 0.8116 | NO | 2025-11-03 | 0.7816 | NO |
| 2025-12-01 | 0.9898 | YES | 2025-12-01 | 0.8966 | NO |
| 2026-01-01 | 1.0427 | YES | 2026-01-02 | 0.9883 | YES |
| 2026-02-01 | 1.0203 | YES | 2026-02-01 | 1.0025 | YES |
| 2026-03-04 | 1.0094 | YES | 2026-03-02 | 0.9827 | YES |

**NIFTY 5 of 12, SENSEX 6 of 12** — both below the pre-registered 10 of 12. Of the 13
failing days (NIFTY 7, SENSEX 6), 8 are more than 10 % from parity (NIFTY 0.8976, 1.1066,
0.8817, 0.8116; SENSEX 1.1340, 0.8380, 0.7816, 0.8966) and 5 are within 10 % (NIFTY
0.9428, 1.0883, 0.9090; SENSEX 1.0613, 1.0830). Failing days lie between 5.7 % and
21.8 % from parity; the band edge is 5 %. Note the sign flips across months, so this is
not a fixed bias that a constant correction would remove.

## B4 — fillable share of open interest

A strike is fillable if at least one of its two legs has γ > 0.

| symbol | minutes | median % of OI fillable | worst minute |
|---|---|---|---|
| NIFTY | 36 | **100.00** | 100.00 (2025-04-01 10:00) |
| SENSEX | 36 | **100.00** | 100.00 (2025-04-02 10:00) |

### This is a 100 % cell, so it is treated as a defect report (Rule 0a clause 3)

**The "neither" branch never fires.** On **72 of 72** minutes
`strikes_fillable == strikes`: not one strike in the whole sample has both legs blank. So
`oi_neither = 0` is not a zero measured against a classifier that was exercised — the
`n_pos = 0` predicate was never satisfied, and the pre-registered 90 % worst-minute floor
was never approached. **A threshold of 99.99 % would have passed identically**, which
means this test discriminated nothing about the floor it names.

**Why, mechanically:** B2 shows every γ NULL is ITM and **0.0 %** of OTM legs are NULL.
A strike's two legs are one ITM and one OTM (except exactly at spot), so the OTM leg
always solves and every strike keeps at least one γ. The 100 % is **structural, not
fortunate** — which is also why it cannot be read as evidence of a healthy solve.

**Control that the apparatus is not vacuous:** the same pipeline with the stricter
predicate (**both** legs solved) returns, over the same 72 minutes,
**min 26.73 % / median 50.81 % / max 75.85 %** of open interest
(`_partB_agg.txt`, B4 detail, column `pct_both`), and `strikes_both / strikes` of
**11.8 % to 49.5 %**. Same rows, same joins,
one clause changed, a very different answer — so the measurement machinery does
discriminate, and it is specifically the ≥1-leg predicate that is never violated.

## B5 — days per month — **MEASURED**

| | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Jan | Feb | Mar | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY probe | 14 | 17 | 17 | 18 | 15 | 17 | 17 | 15 | 17 | 16 | 17 | 14 | **194** |
| NIFTY log | 14 | 17 | 17 | 18 | 15 | 17 | 17 | 15 | 17 | 16 | 17 | 14 | 194 |
| SENSEX probe | 13 | 17 | 16 | 18 | 15 | 18 | 16 | 15 | 18 | 15 | 17 | 15 | **193** |
| SENSEX log | 13 | 17 | 16 | 18 | 15 | 18 | 16 | 15 | 18 | 15 | 17 | 15 | 193 |

24 of 24 symbol-months ran, 24 OK, **max 7.73 s**, no timeout, no stop. 730 calendar days
probed. The probe reads the **table**; the log row is `hist_greeks_backfill_log` and
records what the **writer believed it wrote** — they agree on every month, both symbols.

**`trade_date` vs the clock date of `bar_ts`: 0 disagreements** on the first row of every
day with rows. So for this store the TD-029-family labelling holds and the two columns
are interchangeable for day identity in this window.

**What the agreement does not establish.** The comparison is of **counts per month**, so
offsetting day differences would cancel: if the probe found a day the log lacks and the
log claimed a day the probe lacks in the same month, both numbers would still match. Day
identity was not compared set-against-set. The 0-disagreement result on
`trade_date`/`bar_ts` is also taken from **one row per day** — the first — not from every
row of the day.

### The gate was judged on the `Limit` node, not the scan beneath it

The first version of this probe tripped the EXPLAIN gate at `rows=42096`
(`queries/explain_qB5_NIFTY_2025-04_v1_outer_sort.txt`). That estimate belongs to the
Index Scan **without** its `Limit` — the number of rows matching one day's `bar_ts` range
— whereas the `Limit` directly above it estimates `rows=1` at `cost=1.37`, and the whole
month's plan costs 1,410. The scan is an index scan, never sequential. The gate was
therefore read at the `Limit` node, on the ruling that the operative estimate is the rows
the plan **returns** from that subtree, not the rows the unbounded scan would match —
**operator ruling (option 1), 2026-11-20.**

Three conditions were required before running and all three were checked mechanically
against `queries/explain_qB5_NIFTY_2025-04_v2.txt`: (a) a `Limit` over an Index Scan using
`idx_hist_greeks_instr_barts` whose `Index Cond` carries `instrument_id` and **both**
`bar_ts` bounds — MET; (b) no `Sort` and no `Bitmap` node — MET; (c) `Limit` estimate
`rows=1` — MET.

Condition (b) **failed on v1** because the template's outer `ORDER BY cal_day` added a
`Sort` over the 31 generated days. Rather than reinterpret the condition, the `ORDER BY`
was removed and day ordering moved into `analyze_partB5.py`; v1 is kept as the evidence
for why. The `ORDER BY g.bar_ts` **inside** the LATERAL remains — it is what the index
supplies for free and what makes `LIMIT 1` return the day's first bar rather than an
arbitrary one.

### Superseded: the earlier blocked state

The first form of this query aggregated a whole month of `hist_option_greeks_1m` per
instrument (~700k rows) and was rejected before running, correctly, as a violation of the
EXPLAIN gate. The replacement (`queries/qB5_month.sql.tpl`) is a day-existence probe:
`generate_series` over the month's calendar days with one
`LATERAL … ORDER BY bar_ts LIMIT 1` per day, reading at most one row per day.

**Its EXPLAIN trips the gate, and the trip looks like a flaw in the gate rather than in
the query** (`queries/explain_qB5_NIFTY_2025-04.txt`):

```
->  Limit  (cost=0.44..1.37 rows=1 width=12)
      ->  Index Scan using idx_hist_greeks_instr_barts on hist_option_greeks_1m g
            (cost=0.44..38958.52 rows=42096 width=12)
```

The `rows=42096` my check read is the estimate for the Index Scan **without** the `Limit`
— how many rows match one day's range. The `Limit` immediately above it estimates
`rows=1` at `cost=1.37`, and the whole month's plan costs 1,410. The scan is an index
scan, not sequential. So the query reads ~31 index tuples plus 31 heap fetches per month,
which is what the gate exists to ensure, while the number the gate inspects describes
work the plan does not do.

Option 1 was taken: judge the `Limit` node's estimate, as recorded above. B5 is measured
and this section is kept only to show the route.

**Cross-check source.** `hist_greeks_backfill_log` (`_q01.txt`) records `DONE` days per
month with `rows_written > 0`:

| | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Jan | Feb | Mar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 14 | 17 | 17 | 18 | 15 | 17 | 17 | 15 | 17 | 16 | 17 | 14 |
| SENSEX | 13 | 17 | 16 | 18 | 15 | 18 | 16 | 15 | 18 | 15 | 17 | 15 |

This is the **writer's own log**, so it says what the writer believed it wrote, not what
the table holds — exactly the distinction B5 exists to close, which is why it is a
cross-check and not the answer.

---

## Verdicts

Thresholds fixed in the pre-registration before any number was seen: *usable as stored*
needs the within-1 % median γ ratio in [0.95, 1.05] on ≥ 10 of 12 days **and** median
fillable OI ≥ 95 % **and** worst minute ≥ 90 %.

**NIFTY — B: history usable with one gamma per strike.**
Ratio test FAIL (5 of 12 days in band, need ≥ 10). Fill test PASS (median 100.00 %,
worst 100.00 %).

**SENSEX — B: history usable with one gamma per strike.**
Ratio test FAIL (6 of 12 days in band, need ≥ 10). Fill test PASS (median 100.00 %,
worst 100.00 %).

Both land on the middle verdict, and both land there for a reason the thresholds did not
anticipate: the fill test passes **structurally** (B4 — the OTM leg always solves), while
the ratio test fails because the two legs at one strike disagree on 13 of the 24 sampled
days (NIFTY 7 of 12, SENSEX 6 of 12). The operational reading is the verdict's own wording: **take one gamma per strike**
— the OTM leg's — and do not treat the call's and the put's solved gammas as independent
measurements of the same quantity, because they demonstrably are not.

The OTM leg is chosen because it is the leg that solves, not because it was shown to be
more accurate. B3 shows the call and put gammas disagree by 6–22 % on the failing days;
it does not show which leg is right. Any look-back using this gamma carries an error of
that order, and a sensitivity run with the call/put average on strikes where both legs
solved is planned (restricted to those strikes, as B3 itself is).

Likeliest cause, from B0 and not tested here: a flat `r = 6.5 %` with no market forward,
while `core/bs_engine.py:77-84` provides `basis_implied_r` and the backfill never calls
it. A forward error moves call and put IV in opposite directions at one strike, which is
the shape B3 measures.

## What these tests could not see

- **72 minutes out of ~90,000 trading minutes in the window.** Three minutes on the
  first available day of each month. Nothing about intraday drift, the open, the close
  after 15:00, or any day that is not a month's first `DONE` day.
- **No expiry day at all.** B0 rule 4 removes them from the store, so the history cannot
  speak about 0-DTE, which is where pinning is strongest. 53 NIFTY and 52 SENSEX days in
  this window are `SKIPPED_EXPIRY`.
- **The ±120 s tolerance was never exercised** — every target minute hit exactly. A day
  with a gap at 10:00 would take a path this run never tested.
- **B3 conditions on both legs solving**, so it measures agreement only on the strikes
  where both worked — by construction, never on the ITM legs that failed. The disagreement
  on strikes where one leg is NULL is unmeasurable by this method.
- **B4 cannot fail on this data** (above). It reports a structural fact, not a quality
  margin.
- **`T` has no intraday decay** (B0), so 10:00 and 15:00 on one day share a `T`. Any
  error this induces is common to the three sampled minutes and invisible to a
  within-day comparison.
- **No comparison of the own solve against the vendor's own greeks**, leg for leg. The
  deep-ITM guard applies to `gex_strike_snapshots` and not to this store (B0), so the two
  are not comparable without accounting for it, and that accounting was not done.
- **The sampled days are the first `DONE` day of each month**, selected from the writer's
  log. B5 now checks the log against the table and they agree on every month — but **by
  count per month, not day-by-day**, so an offsetting pair of differences inside one month
  would cancel and leave the counts matching. The specific claim "the day this sample
  used is really in the table" is covered only for those 24 days, which the Part B runs
  themselves demonstrate by returning rows.
- **Nothing here relates a strike to later price.** No outcome, no pin accuracy, by
  instruction.
