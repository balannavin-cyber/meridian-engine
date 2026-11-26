
## 13. Hand-added at the S107 doc-close (2026-11-26) — NOT produced by the generator

**Read this first.** As section 12: written by hand, not by `scripts/build_data_inventory.py`. A regeneration will
drop it unless the generator's candidate set is extended. Every count below was printed by a statement the
operator ran on 2026-11-25 or 2026-11-26 and pasted, or by the backfill script's own log; the source is named on
each line. Decision and rule: `docs/decisions/ADR-033-gamma-v2-versioned-isolation.md`.

**The V2 relations** — RLS on; SELECT for `merdian_ro`; SELECT, INSERT, UPDATE for `service_role`; nothing for
`anon` or `authenticated`. Created 2026-11-25 (`sql/2026-11-25_s107_stepA_apply_ALL.sql`).

| Relation | Extent (measured) | Grain | Written by | Note |
|---|---|---|---|---|
| `gex_strike_v2` | **2,679,771 rows**; NIFTY 1,078,346, SENSEX 1,601,425; 2026-05-25 → 2026-11-25 | one row per run, expiry and strike with OI on a leg | `backfill_gamma_v2_from_gss.py` only (stamp `v2-1.2-gss`) | unique on (`run_id`, `strike`, `expiry_date`). Equal in count to `gex_strike_snapshots` per symbol at the time of the backfill: every stored row produced one V2 row |
| `gex_run_v2` | **19,050 rows**; NIFTY 9,553 (123 days), SENSEX 9,497 (124 days) | one row per run | as above | unique on (`run_id`, `symbol`, `expiry_date`); `n_dup_legs` NULL on backfilled rows (duplicate leg rows are not visible in stored rows) |
| `p3b2_invariant_checks` | 19,050 runs × checks V0–V5, plus 240 sweep rows | one row per run and check; one per sweep call | `p3b2_sweep`, by hand | V0, V2, V3, V4 OK on 19,050; V1 OK on 10,067, NOT_COMPUTED on 8,983; no FAIL |

**No live writer.** Rows for 2026-11-26 onward do not exist: the writer hook is authored and not approved
(ENH-150). A reader of these tables must not treat them as current.

**`gex_strike_snapshots` — what the backfill measured about it.** Size read 2026-11-25 19:54 IST, including that
day: NIFTY 9,553 runs and 1,078,346 rows over 123 days; SENSEX 9,497 runs and 1,601,425 rows over 124 days; first
day 2026-05-25 on both. The extra SENSEX day is 2026-06-11 (one SENSEX run, no NIFTY run). **No stored run has a
repeated strike, a missing or non-positive spot, or more than one expiry** (0 input errors over the full history).

**The run set is not constant.** 161 of 247 day-symbols do not have 83 runs:

| Period or kind | Runs per symbol per day |
|---|---|
| 2026-05-25 → 2026-06-17 | short or broken days, 1 to 74 |
| 2026-06-18 → 2026-10-23, ordinary days | 83, with many days at 81, 82 or 84, often on one symbol only |
| 2026-10-26 → 2026-11-25 | **87** on every day except 2026-11-17 (78) |
| Partial days | 2026-06-26 (15), 07-31 (68), 08-03 (73), 08-17 (64), 09-22 (74), 10-01 (80), 11-17 (78) |
| Single stray run | 2026-05-25, 06-05, 06-11 (SENSEX only), 10-02 |
| Weekdays with no run | 2026-05-28, 06-03, 06-04, 06-08, 09-14, 10-20, 10-21, 11-10, 11-24 — not checked against the holiday list |

A run between 15:21 and 15:39 IST exists on 75 of 123 NIFTY days and 74 of 124 SENSEX days. On 2026-08-27 the runs
are 08:35 to 15:20 at five-minute steps, then 15:40; the eight runs before 09:15 carry the previous session's OI
until the 09:20 run, and the 08:35–08:45 runs are identical in every figure
(`docs/research/pin_proof/b2_backfill_check_result_2026-11-25.md`). TD-PIN3-NEW-1.

**`option_chain_snapshots` — what the V1 check implies about it.** `p3b2` check V1 recomputes each strike from the
chain rows of the run. It could do so on 10,067 runs and not on 8,983. By arithmetic on the per-day sweep counts,
10,067 is exactly the number of stored runs from 2026-08-26 onward, so chain rows are absent for the runs of
2026-05-25 → 2026-08-25. **Derived from counts, not read per date.** It is consistent with two earlier records, neither re-read here:
the retention job (`pg_cron` jobid 19) thinned chain rows older than 14 days to one row a day until the operator
disabled it on 2026-09-09 (Topology §S76), and the pin lane's audit found that the runs of 2026-08-25 have no chain
legs (TD-PIN2-NEW-5).

**The `tape_live_*` tables (from the order-flow lane, read 2026-11-24).** 0 triggers, 0 foreign keys, 18 policy
rows (10 for `tape_w`, 8 reader). Read policies `merdian_ro_select` and `tape_ro_select` have `qual = true` on all
four tables, so test rows are readable until cleaned. `tape_live_label.reason` and `tape_live_events.side` are NOT
NULL and the live writer renders `''`; whether the offline path stores `''` too is not confirmed (STREAMS X3).
`as_of` column comments applied on all four (E-6).

*Hand-added section, S107 doc-close, 2026-11-26. Sources: `docs/research/s107/engine_to_pin_LATEST.md`;
`docs/registers/intake/I003.md`. Nothing above section 13 was edited.*
