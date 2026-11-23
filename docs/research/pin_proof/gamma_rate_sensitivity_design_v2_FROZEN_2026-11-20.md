# Gamma rate sensitivity: design (v2, FROZEN 2026-11-20, MR-PIN2 step 2)

**Lane:** engine (Board pin, gamma inputs). **Status:** FROZEN. The operator confirmed §3 G1, §8 and §10 on 2026-11-20 15:45 IST ("lets go"). The input hashes in §2 come from the step 1 box check (2026-11-20 ~15:54 IST). This file is frozen by its sha256, recorded outside it (MR-PIN2 close inputs and the run prompt). A later change is a new version with its own hash; a result produced under this version stays tied to it.
Written before any Fyers price is used.
**Read with:** `MR_PIN1_close_inputs.md` §1-§2, `cc_prompt_gamma_inputs_check.md` (Part B), box `gamma_inputs/BLOCKED.txt` (FUTURES CONTRACT RULE; Part H section at line 248, file sha256 7da800ef48c4916f2ab1015cdf088e0ecf001be2d5719062c6b5ac55eddec24c).
**Authorises nothing for the Board or production.** It decides only which gamma the pin look-back (pre-registration v2) uses.

## 1. Claim under test

Part B found the own-solved history (`hist_option_greeks_1m`, flat r = 6.5 %) fails the call/put gamma ratio test: NIFTY 5 of 12 days and SENSEX 6 of 12 days have a median ratio inside [0.95, 1.05]; failing days are 5.7 % to 21.8 % from parity.

**Claim:** the flat rate is the main cause. If the forward each option is solved against is taken from the market (Fyers near-month futures), call and put at one strike should solve to nearly one IV, so one gamma.

**The claim fails if** re-solving with the futures-implied rate does not bring at least 10 of 12 days per symbol into [0.95, 1.05] (criterion §7). Other causes named in Part B (bar closes instead of mids, no intraday decay, calendar-day T) stay untested by this design.

## 2. Inputs (fixed)

- **Minutes:** the 72 Part H minutes: the 24 Part B sample symbol-days (12 per symbol) x 10:00, 12:30, 15:00 IST. Day set is all 12 days per symbol (72 of 72 have F).
- **F:** the Fyers close already fetched in `_partH_raw.txt` (sha256 ba52678f0d90667ce261b8c562dd08e02ca20253575d63f4083279d672323ac0, 292,619 bytes), not re-queried. The selected contract per minute must equal the selection in `_partH_analysis.txt` (sha256 83a5bf8e7cd411b9e3222a5ebc1c68d131055037dfe6448a87a2b9de0abdc5ee). Contract and exclusions exactly as the FUTURES CONTRACT RULE in `BLOCKED.txt`: exact-instant bar, no neighbour fill; smallest expiry_date >= IST trade date; missing F excluded and counted; fut_dte < 3 excluded and counted (**untested by this data**: every sampled minute has fut_dte 22-30, so the expected count is 0).
- **S:** `hist_spot_bars_1m` close at the same IST-labelled bar_ts (:59 of the sampled minute).
- **Option legs:** front expiry as Part B B1; the backfill's own conventions as written in `partB_code.md` (sha256 d02077fc0b50450d5375e6d3717d240edce2e502046172599dbacb00094c201a): spot `hist_spot_bars_1m.close` at the same bar_ts as the option bar; `R_FLAT = 0.065`; T = calendar days / 365, whole days, no intraday decay; solved price = bar `close`, never a mid. The re-solve calls `core/bs_engine.py` the way `backfill_hist_greeks.py` does; it does not re-implement Black-Scholes.
- **Spot check (done at freeze):** the backfill's spot is `hist_spot_bars_1m` at the same bar_ts, so the stop rule "backfill spot differs from S" does not trigger.

## 3. Gates (both before r changes; neither reads a re-solved outcome)

**G0, reproduce Part B.** From stored gamma, recompute the per-day median call/put gamma ratio within 1 % of spot by Part B's own B3 definition (read the B3 query in `gamma_inputs/queries/` and `partB_results.md` and use the same definition). In-band days must equal Part B exactly: NIFTY 5 of 12, SENSEX 6 of 12. Any difference: stop; we would be testing a different sample.

**G1, replicate the solve at r = 0.065.** First read and report the stored numeric type and precision of `iv` and `gamma` (information_schema, plus the significant figures seen in the sampled rows). Then re-solve every leg in the ratio set at r = 0.065 with the backfill's conventions. Per symbol, both must hold:
- **Legs:** on at least 99 % of legs, |gamma_resolved / gamma_stored − 1| <= 0.5 % and |IV_resolved − IV_stored| <= 0.05 vol points.
- **Statistic:** on every one of the symbol's 12 days, the per-day median call/put gamma ratio from the re-solve is within 0.005 of the stored one.

*Derivation:* the smallest effect to be explained is 5.7 % from parity (0.057 on the ratio); replication error must sit about ten times below it. 0.5 % on a leg is the rounding limit if gamma is stored to three significant figures. The tested statistic is a per-day median, so the every-day gate is placed on the median, not on every leg: one odd leg cannot move a median and should not stop the run.
Also reported: the 10 worst legs (always), solver failures (count). If the stored columns are full precision and legs still miss by about 0.5 %, that is reported as a convention mismatch, whether or not the gate passes.
**If G1 fails:** stop. No r changes. The operator rules whether to fix the replication (no sensitivity outcome has been seen) or take the fallback (§10).

## 4. Rate per minute (two steps)

1. r_m = ln(F / S) / T_fut, T_fut = (expiry_date − IST trade date) / 365, once per minute. r is a net carry figure (dividends inside), in % a year.
2. Re-solve every leg of that minute at T_opt (the backfill's own T, whole calendar days / 365) with r_m. Same price, same S, same T_opt; only r changes.

Using T_opt in step 1 would inflate r about 4x to 23x. T_fut and T_opt are both whole-day counts, matching the backfill. The whole-day T_fut ignores the part of the day already gone; at fut_dte 22-30 that moves r by at most about 1/22 of itself (about 0.3 points at 6.5 %). Disclosed, not corrected (the rule in `BLOCKED.txt` stands).

## 5. Pairs and measures

- **Pair set:** strikes within 1 % of spot carrying call gamma > 0 and put gamma > 0 in stored history (Part B B3). Fixed before the re-solve; the after-measure uses exactly the same pairs. A leg that fails to solve at r_m drops its pair; failures are counted per minute.
- **Per day:** median ratio call gamma / put gamma over the day's pairs, before (stored) and after (r_m). Same for call IV / put IV.
- **Also reported, no verdict:** the 1-3 % band, before and after; per-minute medians (72 rows); r_m per minute with futures volume and the zero-volume flag; r_m median, min, max per symbol. Any r_m outside −5 % to +20 % a year is flagged, not excluded.

## 6. Control (descriptive, no verdict)

**C-flat:** re-solve with one flat rate per symbol equal to the median of that symbol's r_m over its verdict minutes (§8). If C-flat closes the gap about as well as per-minute r_m, the cause is the level of 6.5 %, not the day-to-day forward, and a production fix could be a better flat rate rather than a market forward. If C-flat does clearly worse, the forward has to be read per day or minute.

## 7. Pass criterion (per symbol; Part B's threshold unchanged)

On the symbol's **verdict minutes** (§8), **PASS** if, after the re-solve:
1. at least 10 of 12 days have a median ratio in [0.95, 1.05] (with n < 12 days: out-of-band days <= floor(2n / 12)), and
2. no day in band before is out of band after (before and after measured on the same minutes), and
3. solver failures are at most 5 % of the symbol's legs (otherwise the symbol is UNMEASURED, not FAIL).

Otherwise **FAIL**, with the failing number.

## 8. Zero-volume rule (confirmed 2026-11-20)

10 of 36 SENSEX minutes have a zero-volume futures bar (7 at 12:30, 2 at 15:00, 1 at 10:00). NIFTY has none. A zero-volume bar is a carried-forward price; a 0.1 % error in F moves r about 1.5 points at 25 days.

- **Verdict minutes:** minutes whose futures bar has volume > 0. NIFTY 36 of 36; SENSEX 26 of 36. The SENSEX verdict is taken on these 26 only. A day keeps the minutes it has left; a day with none left drops out.
- **Why:** a failure caused by stale futures prints would not be a failure of the claim (Rule 0: a check must fail for the reason it names). The exclusion is by volume, fixed here before any price is used, so it cannot select on outcome.
- **Guard:** if fewer than 10 SENSEX days have a verdict minute, SENSEX is UNMEASURED.
- **All-72 report:** run and reported beside the verdict report, with no verdict. If the two disagree for SENSEX, that is recorded as a finding about the futures source.
- **What the rule cannot see:** a bar with small non-zero volume can also carry an old price; volume > 0 is not proof of a fresh print.

## 9. Run discipline

Box, Claude Code, read-only via `bin/roq.sh` as `merdian_ro`; after 15:40 IST on a trading day, or on a weekend; every run under `ulimit -v 700000`; `python3 -B`. EXPLAIN gate before each query (no ANALYZE; fail on any sequential scan or scan estimate over 20,000; literal bounds). One symbol-day per query (3 minutes, legs within 3 % of spot, front expiry: S, the price the backfill solved, stored iv and gamma). 5 s sleep. Stop at the first failure or any query over 10 s; no retry. The completion marker is written to the same log file the precondition reads. Output under `gamma_inputs/sens/`. G0 and G1 are written and printed before any r_m is computed.

## 10. What each result authorises (per symbol; symbols are never pooled)

- **PASS:** the look-back for that symbol may use gamma re-solved with a futures-implied rate. How r is supplied across the look-back window, and the size of that re-solve, are set in pre-registration v2, not here.
- **FAIL:** the fallback agreed in MR-PIN1 for that symbol: flat 6.5 % gamma, one gamma per strike (OTM leg), with the 6-22 % call/put error disclosed; the forward-rate fix goes into the production gamma scoping. The other Part B candidates are recorded as untested.
- **A SENSEX FAIL is recorded as** "not shown with this futures source", not "the rate is not the cause". SENSEX futures are thin; the options-implied forward (operator's option 3) stays the untested route for it.
- **UNMEASURED:** treated as FAIL for the look-back (fallback), and recorded as unmeasured.
- **G0 or G1 fail:** stop; operator rules.
- **If the symbols split,** each takes its own result. The look-back may then run on different gamma definitions per symbol; the symbols are not compared or pooled.
- Nothing here changes a table, view, writer or Board label.

## 11. What this cannot see

- Whether the OTM leg's gamma (the one the look-back uses) is closer to true after the re-solve. Parity of call and put gamma is evidence the forward is right; it is not a direct measure of either leg.
- Lumpy dividends: r_m is straight-line carry to the futures expiry, applied to a shorter option expiry.
- SENSEX alignment rests on the 2025-05-02 test plus two unambiguous minutes in the 2026-03-02 re-check (one flat minute not independently confirmed).
- Stale option prices (bar close, not mid) remain in both before and after.
