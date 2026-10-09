# Operator rulings — Session 93

Single source for S93 rulings. Other documents point here and do not restate them —
a ruling transcribed into a second place is a ruling that can drift out of agreement
with itself.

Sits beside `rulings_s92.md` in this directory, which is named for the parity programme
S92 closed; S93 has no parity work and the path is kept only so the rulings files stay
together.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S93-A** | 2026-10-09 | P6 authored ahead of P1's decision point | **The P6 DEX standing book is authored, tested offline and committed BEFORE P1's result, and is NOT applied.** Commits `559aee3` (view + design note + offline test), `333fc33` (the test adopts `core.ts_parse`; first run), `71cd100` (wired in as `run_offline.sh` step 11/11). The state is as `559aee3` words it — *"AUTHOR ONLY: no CREATE/COMMENT/GRANT issued, nothing pushed, no fixture suite run"* — and as the design note's Status field words it: *"AUTHOR ONLY. Nothing in this note has been applied to the database."* **ENH-140 stays unfiled**, again in `559aee3`'s words: *"ENH-140 id checked free (highest ENH-139), drafted but deliberately NOT spliced into the register."* | Roadmap §2.1 already carried the sequencing this permits: *"P5 and P6 are independent of P1–P4 and may run alongside them."* So authoring P6 before P1 returned needed no new ruling; what needed recording is that **authoring is where it stopped** — the apply is gated on S93-B, not on P6's own readiness. Against this, the S92 close had written that the P6/P7 dev documents *"wait on P1 — operator sequencing, 2026-10-09"*; the operator's call on 2026-10-09 was to author and test P6 within that window while leaving the database untouched, which this row records rather than reconciles. |
| **S93-B** | — | The P2–P8 re-plan after P1 | **OWED, NOT RULED.** P1 returned **NO on both arms** (`62de679`; result doc `docs/research/s92_priority/P1_level_test_result_2026-10-09.md`), which is the S92-I decision point. The re-plan of P2–P8 is the operator's and has not been made. Recorded as open. | S92-I: each of P1–P8 ends DONE with evidence or DECLINED-ON-EVIDENCE, and the roadmap's decision point reads *"After P1: if the levels do not beat the null, the operator re-plans everything below before more is built."* |

## Consequences recorded at ruling time

- **Nothing further is built until S93-B, including the P6 view apply.** Recorded in
  `agentic_layer_roadmap_S90.md` §2.1 under Decision points. The authored view therefore
  has **no live object**, and its Section 4 checks — including 4i, the view against the
  independent Python recompute — are **unrun**. That is a consequence of S93-B being owed,
  not a gap in P6.
- **S93-A is a record, not a permission.** It does not authorise the apply and does not make
  P6 DONE. The roadmap §2.1 P6 row is set to **AUTHORED — NOT APPLIED** (S93-A; `559aee3`,
  `333fc33`, `71cd100`); apply gated on **S93-B**.
- **P1's verdict is not reopened by its descriptive observations.** The result doc records
  two post-hoc patterns and marks both as not claimable from that data; a DTE-conditioned
  test is a **new** pre-registration, never an amendment (pre-registration §1).
- **No ADR was filed this session and none was amended.** Neither S93-A nor S93-B is a new
  `CLAUDE.md` rule, so rules 0–24 stand unchanged.
