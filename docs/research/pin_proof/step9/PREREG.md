# Step 9: old against new gamma figures on stored history, pre-registration (FROZEN 2026-11-26)

**Status:** FROZEN, Thu 2026-11-26, about 06:00 IST, MR-PIN4, on the operator's messages of 05:45 IST ("I would go with your considered view on all counts") and 05:57 IST ("I'll go with your ruling having considered the advisor's note"). Text is draft r3 (`old_vs_new_prereg_DRAFT_2026-11-25.md`) with this status block and the heading of section 9 changed; nothing else. No outcome figure had been read at freeze.
**Tracker:** Goal 2, step 9. Step 10 (the operator's decision) follows the result.
**Authorises:** one read-only run on the box. Nothing on the Board, no writer, no job, no view.

## 1. Question

On every stored run, how far does each V2 figure (rule v1.2, `gex_strike_v2`, `gex_run_v2`) move from the V1 figure it would replace? This is a report of distances. There is no threshold on the size of a change: V1 is known to drop legs, so a large change is not a failure. The only pass/fail items are the integrity stops in section 6. It reads no price outcome.

## 2. Population (counts from the engine's B3 note, 26 Nov 05:10 IST; no outcome)

- Runs present in both `gex_run_v2` (stamp `v2-1.2-gss`) and `gex_cycle_history`, joined on `run_id` and symbol. Runs in one table and not the other are counted and listed by date.
- B3 wrote 2026-05-25 to 2026-11-25: NIFTY 9,553 runs over 123 days; SENSEX 9,497 runs over 124 days; 19,050 runs and 2,679,771 strike rows in all; 0 input-error runs.
- Run counts vary by day (161 of 247 day-symbols are not 83; 87 per day from 26 Oct). Sets are chosen by clock time only. Nothing here assumes a run count.

## 2a. Gates already passed (cited here, not re-run)

| Gate | Evidence |
|---|---|
| V1 code untouched by V2 | V-2a, at three commits (`v2_rule_conformance_*`) |
| V2 arithmetic equals the rule | V-2b: 486 chain runs, 0 mismatches; B2: 156 of 156 runs |
| Completeness | 19,050 of 19,050 stored runs have V2 rows; row counts equal V1's per symbol |
| Strike rows reconcile to the run figure | `p3b2` V2 check: 19,050 of 19,050, largest difference 7.5e-9 |
| Gross pin: live view equals the V2 table | `p3b2` V4 check: 19,050 of 19,050. The view is the method that won the replay, and the rule's guard never acts within 5 % of spot, so research parity holds for the gross pin |
| Stored rows hold what V2 needs, where the chain still exists | `p3b2` V1 check: V2 rebuilt from the chain equals V2 from stored rows on 10,067 of 10,067 runs; V-2c on 313 runs |

Not yet shown, and reported by this run: research parity for net figures beyond 5 % of spot (the guard, section 4 F7), and whether the 8,983 runs with no chain were written the same way as the checked ones (section 5, provenance).

## 3. Sets (by clock time)

The run's clock time is `gex_strike_snapshots.ts` of that `run_id` in Asia/Kolkata, truncated to the minute.
- **Main:** 09:15 to 15:30 inclusive (ruled, section 9). Split into three fixed windows for the time-of-day report: 09:15 to 10:59, 11:00 to 13:59, 14:00 to 15:30.
- **Pre-open:** before 09:15. **Post-close:** after 15:30. Each is reported on its own and never pooled with the main set.
- The 09:15 run stays in the main set and is also printed as one extra line on its own (on 27 Aug it carried the previous day's OI; V1 and V2 read the same inputs, so this does not bias the difference).

## 4. Figures, per run (V1 read from V1's own tables; V2 from `gex_strike_v2` and `gex_run_v2`)

Unit for every exposure: crore per 100 % move, the stored unit (ADR-032). The Board's per-1 % figure is 0.01 times this. Shares and HHI have no unit.

| # | Figure | V1 source | V2 source | Reported per run |
|---|---|---|---|---|
| F1 | Net exposure | `gex_cycle_history.net_gex` | run `net_cr` | V2 − V1 in Cr; abs(V2 − V1) / abs(V1) when V1 ≠ 0 (V1 = 0 counted separately) |
| F2 | Sign of net | sign of F1 V1 | sign of F1 V2 | 3 × 3 table (negative, zero, positive), shown overall and by how far V1's net is from zero: r = abs(net) / sum of abs strike net, in fixed bins under 1 %, 1 to 5 %, 5 % or more. V2's r is reported beside it |
| F3 | Net peak strike (largest absolute) | `gex_cycle_history.pin_leader_strike` | strike with the largest abs `net_cr(K)` over the map; ties go to the strike nearer spot, then the lower strike; ties counted | same or not; distance in strike steps (NIFTY 50, SENSEX 100) |
| F3b | Largest positive net strike | strike with the largest `gex_cr` > 0 in `gex_strike_snapshots`, same tie rule; none if no positive strike | the same on `net_cr(K)` in `gex_strike_v2` | same or not; distance in strike steps; runs where one side has none counted |
| F4 | Net top share | `gex_cycle_history.conc_top1_share` | run `net_top_share` | V2 − V1 in percentage points |
| F5 | Net HHI | `gex_cycle_history.conc_hhi` | sum of (abs `net_cr(K)` / sum of abs `net_cr`) squared over the map, from `gex_strike_v2` | V2 − V1 |
| F6 | Strike level | `gex_strike_snapshots.gex_cr` | `gex_strike_v2` `net_cr(K)` | strikes in both / V1 only / V2 only; strikes whose sign changes; strikes with V1 zero or null and V2 not zero, and the reverse; exposure-weighted change W = sum of abs(V2 − V1) / sum of abs(V1) over the union of strikes, a missing row counting as 0 |
| F7 | The guard beyond 5 % (new in the rule, not tested in the replay) | from `gex_strike_snapshots`: legs with stored gamma > 5e-5 at a strike more than 5 % from spot | | legs removed (k of legs with gamma); share of the run's sum of abs `gex_cr` that sits at strikes where a leg was removed; F1 and W recomputed over strikes within 5 % only, beside the full figures |

**Not compared:** the flip (V2 produces none); walls and max pain (open interest only, unchanged); gross concentration (V1 has no gross figure other than the pin view, which already equals V2, section 2a).

**F4 and F5 are like for like only if** V1's stored values are max abs `gex_cr` / sum of abs `gex_cr`, and the sum of squared shares, over the same strikes as the run's stored rows. The definitions are read from the catalog before any outcome query. If either is not, the pair is printed side by side and marked "not like for like", with no difference computed.

## 5. Summaries

- **Strata:** symbol; set and main-set window (section 3); dte from `gex_cycle_history.dte` (0, 1 to 2, 3 or more); V1 chain-check status from `p3b2_invariant_checks`, `check_id = 'V1'` (OK or NOT_COMPUTED); schedule period (before 26 Oct, from 26 Oct); provenance period (below). Each stratum is shown alone, plus symbol × set × dte.
- **Provenance period:** the engine reports the dates on which the code that writes `gex_strike_snapshots` changed between 2026-05-25 and 2026-11-25. Those dates are written into the run record before any outcome query and split the history into writer periods. For each period: runs, runs with the chain check OK, runs NOT_COMPUTED. A period that has no checked run is marked **"unverified provenance"**, permanently, in the result and in the research record. If the engine reports no change, there is one period.
- **What each cell shows:** the number of runs and days. For F1, F4, F5 and W: median, 90th and 99th percentile and maximum, of the signed and the absolute difference. Fixed bins for the F1 relative change and for W: under 1 %, 1 to 10 %, 10 to 50 %, 50 % or more (k of n). For F2, F3, F3b, F7 and the F6 counts: k of n.
- **Day level:** runs within a day are not independent, and days from 26 Oct hold more runs, so every main-set cell is also shown per day: the day's median, then the median and maximum over days. Day level is shown twice: over all days, and over days with at least 37 main-set runs; the shorter days are listed by date and symbol with their count (ruled, section 9). The 10 days with the largest median F1 relative change are listed by date, symbol and dte, as description only.

## 6. Controls, reported before the figures (Rule 0)

- **C1, the V1 sum:** `net_gex` against the sum of `gex_cr` for the same run (ADR-015, ±0.01 Cr). Failing runs are counted and listed.
- **C2, the V1 peak:** `pin_leader_strike` against the largest abs `gex_cr` recomputed from `gex_strike_snapshots` with the same tie rule. Differing runs are counted; F3 is reported against both.
- **C3, the V2 sum (stop):** run `net_cr` against the sum of `net_cr(K)` (±0.01 Cr). Any failure stops the run.
- **C4, the known day (stop):** on 2026-08-27, the V2 values read by this run for the 156 fixture runs must equal `b2_expected_2026-08-27.json` (sha256 `d99aa037…7dffa`) within the B2 limits.
- **C6, run identity (stop):** for every run, the symbol, expiry and timestamp of the V2 rows equal those of the V1 rows with the same `run_id`. Any mismatch stops the run and is listed.
- **C5, self-test before any database read:** two invented runs with hand-worked F1 to F7, plus broken versions that must each be caught: V1 and V2 swapped; the put side not negated; abs left off the peak; abs wrongly applied to the positive-strike figure; a V2-only strike dropped from the union; a pre-open run counted in the main set; a 15:30 run sent to post-close; a NOT_COMPUTED run put in the OK stratum; a run with r exactly 1 % put in the lower bin. All nine must be caught.

## 7. Conduct

- Runs only after the engine's writer-change dates are in.
- On the box in `~/meridian-cc`, folder `docs/research/pin_proof/step9/`, through `bin/roq.sh` as `merdian_ro`.
- Catalog first: the columns of `gex_run_v2`, `gex_strike_v2`, `gex_cycle_history`, `gex_strike_snapshots` and `p3b2_invariant_checks`, and the definitions behind F4 and F5, printed before any data.
- Query rules: plain EXPLAIN gate; one symbol-day per query; aggregation done in the query, at most 100 rows back; 5 s sleeps; stop at the first error or any query over 10 s.
- Run rules: `ulimit -v 700000`; `python3 -B`; outside 08:30 to 15:40 IST Mon to Fri; never at the same time as the monitor's run in that tree.
- One look: the summary is produced once. Nothing in sections 3 to 6 changes after a figure is seen; a change is a new pre-registration.
- The raw per-run files and the summary are hashed and committed by branch and PR. Files over 40 KB stay on the box, with their hashes in the commit.

## 8. What this does not establish

- Which figure is right, or that any figure predicts price.
- That the stored rows match the chain on runs where the chain is gone; the provenance report narrows this and does not remove it.
- Anything about dealer positioning or the flip.

## 9. Rulings (operator, 26 Nov 2026)

1. **Boundary:** main set 09:15 to 15:30 IST inclusive, by run clock time.
2. **Threshold:** none on the size of any change. Integrity stops only: C3, C4, C6.
3. **When:** Thu 26 Nov, after the monitor run, once the engine's writer-change dates are in; otherwise the next evening.
4. **Partial days:** run-level figures use every run; day-level figures are shown over all days and over days with at least 37 main-set runs.
