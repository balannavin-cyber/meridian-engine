# Operator rulings — Session 94

This is the single source for the S94 rulings. Other documents point here and do not restate
the rulings. A ruling copied into a second place is a ruling that can drift out of agreement
with itself.

This file sits beside `rulings_s92.md` and `rulings_s93.md` in this directory, so the post-parity
rulings stay together.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S94-A** | 2026-10-10 | The P2–P8 re-plan after P1 (**discharges S93-B**) | **Order: P2 → P4 → P1c → P3.** **HOLD: P5, P6 (the view apply included), P7.** They hold until P2 **and** P4 have reported. P6 is additionally held until the two owed rulings are made: S\* (the zero-Δ level) and vendor delta vs in-house Black–Scholes delta. **P8 stays gated on P4**, unchanged. Each item still ends DONE with evidence or DECLINED-ON-EVIDENCE (S92-I). | P1 returned **NO on both arms** (`P1_level_test_result_2026-10-09.md`). That is S92-I's decision point: *"if the levels do not beat the null, the operator re-plans everything below before more is built."* P1 rejected one claim only: that γ levels **locate** the day's high and low better than random strikes at the same σ-distance. It does not test the exposure signs (P2), direction (P4), the computation (P3), or regime → range (P1c). So those go ahead. P5, P6 and P7 are level-type or sign-dependent displays. They wait for evidence on the sign (P2) and on the Greeks (P4). P3 runs last of the four because P1's NO is not evidence of a computation defect: R2.4 already reported pin = MERIDIAN leader or top-5 in 20/26 fixtures, and net-GEX sign agreement in 17/21. |
| **S94-B** | 2026-10-10 | **P1c** added to the track | **P1c — γ regime → realised range.** Does positive net γ with high concentration go with a smaller realised range than other regimes, against a stated null? **RO, pre-registered before the first outcome query**, on existing history. P1's DTE stratum is folded into P1c's design as a **reporting** stratum (as in P1 §5.1). It is not a selection. | This is the claim the premium-selling style rests on, and it is untested here. The Assumption Register's dampening row reads *"VALIDATED indirectly"*, and that evidence comes from directional win rates (Exp 17/19), not from range. Roadmap §7.2 already lists it as a starter test card (*"Positive net-γ regime shows lower realised range than negative"*). Neither the parity target nor any other public tool reviewed in S94 publishes a validation of its levels or regimes. |
| **S94-C** | 2026-10-10 | P1b — a DTE-conditioned level test | **DEFERRED.** It is not on the track. The DTE stratum is carried inside P1c (S94-B). | P1's pattern (b) is post-hoc. A test of it would need a holdout made **only of sessions after 2026-10-09**. At about 2 DTE-0/1 sessions a week per symbol, n = 30 takes roughly 15 weeks, and it tests a claim that P1c makes less important. Per P1 pre-registration §1, a DTE-conditioned test is a **new** pre-registration if it is ever written, never an amendment. |
| **S94-D** | 2026-10-10 | A known limit, shown on the board | **The live board carries an evidence note on its levels:** *"Levels: P1 — location of the day's high/low not better than random strikes at the same σ (n = 85)."* It goes out as a layout-only Lovable pass under the S92 guard, verified on `/staging/` before it is promoted. The wording may be shortened to fit; its meaning may not change. | Settled decision: *"a consumer-facing artefact carries its own defects, or the defect becomes a finding."* The board shows pin, walls and top-3 levels. P1 now measures what they do not do. |
| **S94-E** | 2026-10-10 | Project-knowledge capacity | **The main sessions live with the current size (93.4 %).** The rest of the cleanup runs in a **parallel session** (`PK_cleanup_session_prompt.md`). That session has its own guardrails and does not touch the main session's docs. `tech_debt.md`, `merdian_reference.json` and the Enhancement Register stay read-only for it until this session's doc-close. | Measured in S94: 21 docs removed, and the meter fell 1,942,156 → **1,868,873**. That is 0.338 meter units per byte, measured on two batches. All 21 are recoverable from git. 14 were already in git. 7 were archived first at `0f1e5bc` (`docs/registers/archive/pk_only_2026-10-10/`; `sha256sum -c` 7/7 OK). Durable extracts of the three big registers need a generator and a doc-close amendment (rule 12 re-uploads them at every close). That is a separate concern. |

## Consequences recorded at ruling time

- **S93-B is discharged by S94-A.** `rulings_s93.md` is not edited. This row is the record.
- **Nothing is applied by these rulings.** The P6 view stays **AUTHORED — NOT APPLIED**. Its
  Section 4 checks, 4i included, stay unrun. **ENH-140 stays unfiled.**
- **Dev documents allowed now:** the P2 design note, the P4 pre-registration and the P1c
  pre-registration. Each pre-registration is committed, with its `git hash-object` recorded,
  **before** its first outcome query. **Not allowed:** P5, P6 and P7 dev documents, and any
  P8 work.
- **P2 scope, stated now so it is not discovered later.** NSE publishes participant-wise OI
  (client / pro / FII / DII) as **daily aggregates**, not per strike. P2 can therefore test the
  **aggregate** dealer-side sign, not the sign at each strike, and its design note must say so.
- **No ADR filed or amended. No `CLAUDE.md` rule added.** Rules 0–24 stand unchanged.
