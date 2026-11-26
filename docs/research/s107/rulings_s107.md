<!-- pk: lane=engine; git=meridian-engine:docs/research/s107/rulings_s107.md -->
# Rulings, engine session S107 (2026-11-21 → 2026-11-26)

Single source for the operator's rulings that bind the engine lane in S107. Most were given in the Board-pin
lane's chat and relayed; each line names where it is recorded. **Limit:** this file is compiled at the close from
the lane records in git and from the engine chat's record of 24–26 Nov. A ruling given in the engine chat before
24 Nov that is not in `docs/registers/intake/I002.md` is not captured here.

| # | When (IST) | Ruling | Recorded in |
|---|---|---|---|
| **S107-A** | 2026-11-22 12:03, 12:07 | The regime gate (`trade_allowed`) is a leftover of the Buy-CE / Buy-PE-only era. Registers that call it current are corrected. | I-002 row 11; AR §D.61.3 |
| **S107-B** | 2026-11-22 | The VS (gross) rule is the preferred pin methodology; a shadow view is authored. A Board switch is a separate decision. | I-002 row 1 |
| **S107-C** | 2026-11-23 | Root `.gitignore`: keep the repo-wide rule, add one negation block for `docs/research/` (engine's decision, operator may overrule; not overruled). | I-002 §2 |
| **S107-D** | 2026-11-23 20:48 | The ten-day shadow is dropped; a standing measurement discipline (the daily pin monitor) replaces it. | `docs/research/pin_proof/ruling_shadow_dropped_2026-11-23.md` |
| **S107-E** | 2026-11-24 | Fix gamma at the source, one gamma per strike; leave the Board Flip alone for now; unify on own-computed gammas later. The gross pin keeps the name "Pin". No resize of the production box. | `docs/research/pin_proof/MR_PIN3_close_inputs.md` §2; `claude/ofl/MR_OFL9_close_inputs.md` §1 |
| **S107-F** (R1) | 2026-11-25 09:19 | **Option D, versioned isolation.** V1 is untouched and named legacy. V2 lives in a new module and new tables. | ADR-033 D1, D2 |
| **S107-G** (R2, R3) | 2026-11-25 09:23 | **The Board Pin switches to the gross pin now.** The tile shows strike, share and lead; pin state and conviction sit under a line named "Net peak". | ADR-033 D7; ENH-149 |
| **S107-H** (R4) | 2026-11-25 09:19 | Regime, expansion probability, pin score and the dealer-flow simulation are labelled legacy / unvalidated now; removal is one later release. | ADR-033 D7 |
| **S107-I** (R5) | 2026-11-25 09:19 | Dealer-positioning wording: case by case; nothing changes meanwhile. | ADR-033 D7 |
| **S107-J** (R6) | 2026-11-25 09:19 | No V2 flip of any kind. The flip replacement study is parked until the build is done. | ADR-033 D3 |
| **S107-K** | 2026-11-25 09:35 | Backfill the V2 tables from stored per-strike rows: yes. Read-only access to the Board repo for the engine lane. A secret scan of the Board repo first (done: 320 commits, only the anon key in a tracked `.env`, no service key). | ADR-033 D6; `MR_PIN3_close_inputs.md` §2 |
| **S107-L** | 2026-11-25 09:48 | The pin lane's independent conformance check is approved. It covers authoring and fixture-day tests only; applying SQL, new tables, the writer hook, the backfill and Board changes each return to the operator. | `MR_PIN3_close_inputs.md` §2 |
| **S107-M** | 2026-11-25 18:50 | Order of work: tables, one-day backfill, the pin lane's check of that day, full backfill, the comparison of V1 against V2, then the operator's decision. The writer hook, the `p3b2` job, the `v_gex2_*` views and Board tiles wait on that decision. | `claude/pin/to_engine_LATEST.md` (19:00 version); ENH-150 |
| **S107-N** | 2026-11-25 19:50 | Every stored run stays in the V2 tables; no market-hours filter in the backfill; the comparison filters by clock time. (Pin lane's ruling at the operator's request.) | `docs/research/pin_proof/b2_backfill_check_result_2026-11-25.md` |
| **S107-O** | 2026-11-26 05:45 | **The Board moves to V2 by family in one release** (net gamma, strike exposure, concentration, Net peak, net river), each figure checked on staging against a database read. Not tile by tile. Nothing approved yet. | `claude/pin/to_engine_LATEST.md` (06:00 version) §3; ENH-150 |
| **S107-P** | 2026-11-26 05:45 | **Gate before the writer hook is put up for approval:** eight isolation and recovery checks, each shown with evidence. | as above; ENH-150 |
| **S107-Q** | 2026-11-26 05:45 | No Pin Band rebuild around the gross pin; no label changes. | as above |

**Not ruled, open with the operator:** whether ADR-033 moves from PROPOSED to ACCEPTED (it has been carried out in
part on step-by-step approvals; §9 of the ADR); whether the PUBLIC grants on `cron` and `net` objects are revoked
(TD-S107-NEW-3); whether the signal builder keeps running (TD-PIN2-NEW-10); the production box's memory
(TD-PIN2-NEW-12).
