# Step 9: amendment A1 to the frozen design (approved by the operator, Thu 2026-11-26)

Parent: PREREG.md (sha256 eef1981480b8cfb7b92e7396c50cb9ceae9e70f655557a0a33c8f7efbb4a73f0). Everything in the parent stands except what A1 changes. No outcome figure had been read when A1 was approved; the one look was unused.

Why: gex_cycle_history holds rows only from 2026-10-05 15:20 IST (NIFTY 2,772 rows, SENSEX 2,771, 34 days). The parent names it as the V1 source for net, the net peak, the top share, the HHI and dte over 2026-05-25 to 2026-11-25.

A1.1 Population (replaces section 2, first bullet). Runs in gex_run_v2 (stamp v2-1.2-gss) that have rows in gex_strike_snapshots under the same run_id. Expected 19,050. Runs in one table and not the other are counted and listed by date.

A1.2 V1 run-level figures are computed from V1's stored strike rows (replaces the V1 source of F1, F2, F3, F4, F5 and of dte). For each run, from its rows in gex_strike_snapshots:
- F1, F2 V1 net = the sum of gex_cr. F2's r = abs(net) / sum of abs gex_cr.
- F3 V1 net peak = the strike with the largest abs gex_cr; ties go to the strike nearer spot, then the lower strike; ties counted.
- F4 V1 net top share = max abs gex_cr / sum of abs gex_cr. F5 V1 net HHI = the sum of (abs gex_cr / sum of abs gex_cr) squared. Both are none when the sum is 0.
- dte = gex_strike_snapshots.dte of the run. It must be one value per run and equal gex_run_v2.dte; this joins C6 as a stop.
F3b, F6 and F7 already read gex_strike_snapshots and are unchanged. The V2 side of every figure is unchanged.

A1.3 Stored-value controls (replace C1 and C2 and the "like for like" clause of section 4). Reported before the figures, each as k of n with the failing runs listed (at most 30 printed, all in a file). None is a stop.
- C1a: the V1 net of A1.2 against gex_cycle_history.net_gex, +/- 0.01 Cr, on the runs that have a row there.
- C1b: the V1 net of A1.2 against gamma_metrics.net_gex, +/- 0.01 Cr, on the runs that have a row there under the same run_id. If the catalog shows gamma_metrics has no run_id, holds more than one row per run, or cannot be read within the query rules, C1b is reported as "not run" with the reason.
- C2: the V1 net peak of A1.2 against gex_cycle_history.pin_leader_strike, on the runs that have a row there.
- C7: the V1 top share of A1.2 against gex_cycle_history.conc_top1_share, and the V1 HHI against conc_hhi, on the runs that have a row there; equal means an absolute difference of 1e-6 or less; the median and maximum difference are also given. If they are not equal, F4 and F5 are still reported, labelled "computed from the strike rows; the stored column is defined differently", and the stored columns are not used.
The catalog step still reads the writer's source and the view definitions behind conc_top1_share and conc_hhi, as description.

A1.4 Limits added to section 8.
- Before 2026-10-05 no stored V1 run-level figure exists to check the A1.2 arithmetic against, other than gamma_metrics.net_gex for the net. The peak and the concentration arithmetic are checked on 34 days.
- The comparison is of V1's stored strike values against V2's, by one fixed arithmetic. It does not claim to reproduce what the Board displayed on a past date.

A1.5 Unchanged. Sections 3, 5 (strata and summaries), 7 and 9; the stops C3, C4 and C6; the self-test and its nine broken versions; one look.
