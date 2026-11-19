# C1: does the sign of the day's futures OI change predict the next session? Pre-registration (v3)

| Field | Value |
|---|---|
| **Status** | **Accepted by the operator 2026-11-19.** Becomes PRE-REGISTERED when its `git hash-object` is recorded before the first outcome query. |
| **Lane** | Futures OI dimension (MR-FOI), operator-only. Mints no ADR, TD or ENH ID. |
| **Risk class** | RO. Writes nothing to the database. Reads only the hashed export files in §2. |
| **Origin** | Candidate 1 of the exploration atlas on 2025-04-01..2026-03-30 (`claude/futoi/futoi_atlas_readout_2026-11-19.md`). Chosen after many cuts, so its in-sample size is overstated. This test is the one confirmation; it is not re-run with changed settings. |
| **Looks** | Design period: explored without limit (atlas). Test period: **one look**, this document, once. |
| **Operator rulings (2026-11-19)** | Test ends at the last session with three contracts (2026-08-25). Near-contract read through October, separate, no verdict. Data by download, not by granting access. **No cost threshold at this stage**: the verdict is about the sign only; size is reported against the typical daily move. |
| **Exposure note (2026-11-19, before hashing)** | A trial export pasted into the drafting chat contained raw daily closes and OI for 11 test sessions, **2026-04-01..2026-04-20**. The drafting assistant saw them. No statistic was computed from them, and nothing in this document was changed because of them (the claim, test, window and controls were fixed in v2 before the file was seen). Recorded so a reader can weigh it. |

## 1. Claim

On a session where total NIFTY futures OI rises from the prior close to the close, the next session's return is lower than on a session where it falls, whatever the direction of the price move.

In-sample (design period, no futures-expiry days): −39.1 bp, week-block 95 % CI [−62.8, −16.8]. The claim tested here is the **sign** only.

## 2. Data

- **Source:** `public.fyers_futures_bars_1m`, NIFTY, exported by the operator to two CSV files of **one row per contract per session** (the last bar at or before 15:29 IST, with its time), hashed (`sha256sum`) before any read:
  - **File A (main test):** sessions 2026-02-25..2026-08-25.
  - **File B (near-contract read):** sessions 2026-08-26..2026-10-29.
  Validated against the vendor series on the design period: same unit, same minute, close OI equal 246/246 (`claude/futoi/futoi_fyers_oi_validation_2026-11-18.md`).
- **Clock:** Fyers `ts` is real UTC, exported already converted to IST. Nothing after 15:29 IST is used.
- **Contract rank:** on session d, rank contracts with `expiry_date >= d` by expiry; series 1, 2, 3 = ranks 1-3.
- **F(d):** OI of series 1 + 2 + 3 at the close of d. Missing if any is missing.
- **P(d):** series-1 close price at the close of d.
- **Test window:** sessions d from **2026-04-01** with F(d), F(d−1), P(d), P(d+1) present and **d+1 ≤ 2026-08-25** (last session with three contracts in the table, measured 2026-11-19). Sessions before 2026-04-01 in File A are used only for trailing values in §7.
- **Futures expiry:** from the file's own `expiry_date`. The expiry session and the session after are **excluded**, and counted.

## 3. Variables

- **dF(d) = F(d) − F(d−1).** Sign only. dF = 0 is excluded and counted.
- **Outcome r(d) = ln P(d+1) − ln P(d)**, in bp, also shown in NIFTY points at P(d).
- No other conditioning in the main test. The price move's sign is not used.

## 4. Test (fixed)

- **Effect:** E = mean r(d) over dF(d) > 0 minus mean r(d) over dF(d) < 0.
- **Interval:** percentile bootstrap resampling whole ISO calendar weeks, 10,000 resamples, seed 20261119.
- **H1:** E < 0. One-sided, α = 0.05: the 95th percentile of the bootstrap distribution of E is below 0.

**Verdict:** bound below 0 → **SIGN CONFIRMED**. Otherwise → **NOT CONFIRMED**.

**Size, reported beside the verdict, no threshold:** E in bp and in points, and E divided by the design period's mean absolute daily return (computed from the vendor series 2025-04-01..2026-03-30 before the test file is read, and written into the result doc first). A SIGN CONFIRMED verdict does not say the effect is worth trading; cost is assessed separately, later, before any use.

## 5. Power, stated before data

Expected about 90–100 sessions after exclusions. On the design period the week-block half-width at 218 sessions was about 23 bp; at ~95 it scales to roughly 34 bp. A true −40 bp would very likely be detected; a true −20 bp probably would not. NOT CONFIRMED is therefore recorded as **NOT CONFIRMED (underpowered against −20 bp)**, not as "absent".

## 6. Controls, before any outcome is computed (each must be able to fail)

- **K0 files:** print both files' sha256 and compare with the hashes recorded at export. Stop on mismatch.
- **K1 window:** first and last session used, count, sessions excluded by reason. Stop if any session after 2026-08-25 is read for the main test.
- **K2 close bar:** the close bar is at 15:29 for all three series on ≥ 95 % of window sessions (from the exported bar time); print the count and the sessions where not.
- **K3 rank:** sessions with fewer than three contracts `expiry_date >= d`; print them.
- **K4 planted signal:** with r(d) shuffled across weeks, E is near 0; with −20 bp added to r(d) on dF > 0 sessions only, E recovers about −20 bp.

Any failure stops the run before §4.

## 7. Separate reads, no verdict (each in its own table, never pooled into the main number)

1. **Near contract (F1) alone**, same definitions, 2026-04-01..2026-10-29 (File A + File B), expiry days excluded.
2. **Regime**: the main contrast within terciles of trailing 20-session realised volatility and of trailing 20-session return, both from data up to the prior close only, cut points fixed **from the design period**.
3. **Per calendar month.**

A final table shows the main test and reads 1-3 side by side, for reading only.

## 8. Limits

- Selected from many cuts on one year; even SIGN CONFIRMED is one confirmation on about five months.
- No cost threshold: a confirmed sign is not a trading result.
- OI is a stock; the claim is about the next session's return, not who trades.
- Fyers data only; the live engine has no futures OI capture after 2026-10-29. Live use would need one.
- This spends 2026-04..2026-08 (and, for F1, to 2026-10) of the futures holdout for this claim.
- See the exposure note above.

## 9. Export (operator, Supabase SQL editor with the row limit removed, then Export as CSV)

File A:
```sql
select distinct on ((ts at time zone 'Asia/Kolkata')::date, expiry_date) underlying, symbol, expiry_date, (ts at time zone 'Asia/Kolkata')::date as d, (ts at time zone 'Asia/Kolkata') as close_ts_ist, close, oi from fyers_futures_bars_1m where underlying = 'NIFTY' and (ts at time zone 'Asia/Kolkata')::time <= '15:29' and (ts at time zone 'Asia/Kolkata')::date between '2026-02-25' and '2026-08-25' order by (ts at time zone 'Asia/Kolkata')::date, expiry_date, ts desc;
```
File B: the same with dates `'2026-08-26' and '2026-10-29'`. Neither file is to be pasted or uploaded into a chat.
