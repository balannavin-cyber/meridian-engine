# CC prompt: gamma inputs check (origin of blank legs + is the own-solved history clean)

Box: MERIDIAN engine EC2, SSM shell, user ssm-user. Normal mode, not plan mode.
Read-only. Part B reads the large `hist_*` tables: on a trading day run it before 09:00 IST or after 15:40 IST.

Start:

```
cd ~/meridian-cc && git pull --ff-only && claude
```

Paste:

```
Read-only research task: gamma inputs check, two parts. It comes before the pin look-back and decides what gamma the look-back may use. Do not write to the database. Do not edit any tracked file. Do not commit. Do not call any vendor API. Do not compute anything that relates a strike to later price (no outcomes).

Rules: read the database only through bin/roq.sh as merdian_ro. Stage 1 lessons: roq takes a SQL file; psql -v variables did not work, substitute literals; statement_timeout is 30 s, so aggregate in SQL and loop by day or by minute; psql unaligned output has a "(N rows)" footer. Every python or roq run under ( ulimit -v 700000; ... ). Never cat, grep or source .env. Write all output under docs/research/pin_proof/gamma_inputs/ (create it). Before any query on a relation, read its columns from information_schema.columns and its indexes from pg_indexes, and filter on indexed columns. A query that times out or errors is written as UNMEASURED with the error, never as zero and never as "none". If merdian_ro cannot read a relation, write it to gamma_inputs/BLOCKED.txt and carry on. If the IST clock passes 09:00 on a trading day before Part B is finished, stop Part B, say so, and write what is done.

Context from Stage 1 (docs/research/pin_proof/stage1/preconditions.md, read it): in gex_strike_snapshots, gamma_call is NULL on strikes below spot and gamma_put is NULL on strikes above spot (20 to 60% of rows per month), never 0; stored gex_cr treats a NULL leg as 0. The engine note of 2026-11-18 says about 13% of NIFTY legs and 28% of SENSEX legs carry open interest and no vendor gamma. Nobody has traced where the blank comes from.

PART A. Where does the blank gamma come from?

A1. Code read, no database. Read ingest_option_chain_local.py, compute_gamma_metrics_local.py (signed_gex_vec and the deep-ITM guard) and whichever script writes gex_strike_snapshots (find it; say which). Write to gamma_inputs/partA_code.md, with file and line numbers: (a) how the vendor's per-leg gamma and iv reach option_chain_snapshots, and any coercion of null, 0 or missing; (b) the exact deep-ITM guard condition and what it does to the leg; (c) the exact rule that makes gamma_call or gamma_put NULL in gex_strike_snapshots; (d) how gex_cr treats a NULL or rejected leg; (e) whether the raw vendor response is stored anywhere (a raw column, a file, a log). Quote at most the few lines that carry each rule.

A2. Chain rows. Days 2026-11-16, 11-17, 11-18, 11-19, NIFTY and SENSEX separately. Runs: front-expiry runs from gamma_metrics (run_id, expiry_date), joined to option_chain_snapshots on run_id and expiry_date. For every leg compute in-the-money depth m: calls (spot - strike)/spot, puts (strike - spot)/spot. Buckets: OTM (m < 0), ITM 0 to 1%, 1 to 2%, 2 to 5%, over 5%. Per symbol, option_type and bucket report: legs; legs with oi > 0; and among legs with oi > 0 the counts with gamma NULL, gamma = 0, gamma > 0; the same three for iv; legs with ltp > 0; legs with bid > 0 and ask > 0. Then the key cell: legs with oi > 0 AND ltp > 0 AND (gamma is NULL or gamma = 0), by bucket, with the same split for iv.

A3. Chain against the strike table. Same runs. Join gex_strike_snapshots to the chain on run_id and strike. Cross-tabulate, per symbol: chain call gamma state (NULL / 0 / > 0 / no chain row) against gex_strike_snapshots.gamma_call state (NULL / > 0); the same for puts. Report the count of legs where the chain has gamma > 0 and the strike table has NULL, by ITM bucket, and say which rule from A1 explains them. Also count strikes where both strike-table gammas are > 0 and gex_cr = 0.

A4. If A1(e) found stored raw vendor responses, read 3 of them for one run and report whether the vendor's own payload carries gamma for a leg that is blank in the chain table. If none is stored, write UNMEASURED and one line on what a live capture would need. Do not make the capture.

Verdict line per symbol, one of:
"A: blank is in the chain rows as stored (vendor or ingest; A4 says which or UNMEASURED)"
"A: blank is created after the chain rows (writer/compute), rule <x>"
"A: mixed" with the split in legs and in share of open interest.

PART B. Is the own-solved history clean enough to carry the look-back?

Relations: hist_option_greeks_1m (our own solve: iv, gamma) and hist_option_bars_1m (vendor bars: OHLC, volume, oi; greek columns never written). Join key measured in the Data Inventory: instrument_id, bar_ts, expiry_date, strike, option_type. hist bar_ts is IST clock time labelled as UTC, at second :59; do not convert it, read it as IST clock time. Window 2025-04-01 to 2026-03-30.

B0. Code read. Read backfill_hist_greeks.py (and core/bs_engine.py where it is called). Write to gamma_inputs/partB_code.md with line numbers: the underlying price and where it comes from; the rate and whether the forward is spot grown at that rate or taken from the market; the time-to-expiry convention; which price is solved (close, mid); every rule that rejects or skips a leg (deep-ITM reject, no price, failed bisection, expiry filter) and whether a rejected leg is written as NULL, 0 or not written; which expiries are solved.

B1. Sample. Per symbol, the first trading day of each month that has rows in hist_option_greeks_1m (12 days each), at three clock minutes: 10:00, 12:30, 15:00 (take the bar at :59 of that minute, or the nearest within 2 minutes; say which). Front expiry only (the nearest expiry_date on or after that day in the greeks table). Find spot for each sampled minute from the relation the backfill used (B0) and say which.

B2. Coverage by leg. For each sampled minute: legs in bars with oi > 0; of those, legs with a greeks row with gamma > 0; gamma NULL; gamma = 0; no greeks row. Split by option_type and by the same ITM buckets as A2. Report as counts and as share of open interest.

B3. Call against put at one strike. For strikes carrying both a call gamma > 0 and a put gamma > 0: ratio call gamma / put gamma. Report median, p10 and p90 per symbol, for strikes within 1% of spot and for 1 to 3%, pooled and per sampled day. Same for call iv / put iv.

B4. Fillable share. A strike is fillable if at least one of its two legs has gamma > 0 (a call and a put at one strike share one gamma, so one leg can serve both). Per symbol and sampled minute: share of total open interest (calls plus puts, front expiry) sitting on fillable strikes; on strikes with both gammas; on strikes with neither. Report the median and the worst minute.

B5. Days. Count distinct trading days per month with any front-expiry greeks row, per symbol, if it runs inside the timeout by looping month by month; otherwise UNMEASURED.

Verdict line per symbol, thresholds fixed here before any number is seen:
"B: history usable as stored" if median call/put gamma ratio within 1% of spot is between 0.95 and 1.05 on at least 10 of 12 days AND median fillable open-interest share is at least 95% AND the worst minute is at least 90%.
"B: history usable with one gamma per strike" if the fillable test passes and the ratio test does not.
"B: history not usable, re-solve needed" otherwise, with the failing number.

Output: gamma_inputs/partA_code.md, partA_results.md, partB_code.md, partB_results.md, the SQL used under gamma_inputs/queries/, and a SHA256SUMS manifest verified with sha256sum -c. In each results file, say plainly what each test could not see. At the very end print to the screen only: the two Part A verdict lines, the two Part B verdict lines, the A2 key cell per symbol (ITM legs with oi and price but no gamma, count and share of open interest), the B3 medians, the B4 median and worst, every UNMEASURED item, and confirmation that no tracked file changed. Keep the screen print under 40 lines.
```
