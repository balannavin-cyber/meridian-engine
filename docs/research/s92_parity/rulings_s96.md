# Operator rulings — Session 96

This is the single source for the S96 rulings. Other documents point here and do not restate
them. It sits beside `rulings_s92.md` … `rulings_s95.md` in this directory.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S96-A** | 2026-10-11 | P7 design (roadmap §2.1) | **The seven decisions of the P7 design note §7, as recommended.** D1 split into **P7a** (DEX flow, reads two live views, changes neither) and **P7b** (∂Δ/∂σ and ∂Δ/∂t flow). D2 P7b by a **per-leg base view** under L7/L8, gated by a before/after equality test (maintenance on a BUILT layer, S95-D). D3 unclassified flow **does not discharge D-4**: the L7/L8 badge is **amended, not retired**, to *"flow-vs-book shown on unclassified ΔOI; classification (D-4) not built"* — the exact board wording still needs the operator's yes before it goes live. D4 P5 stays front-expiry only. D5 the after-15:15 clock split between the DEX pair and the Δ-pair is recorded, not fixed in P7. D6 flagging ΔOI on volume-0 legs is folded into the TD-S95-NEW-1 call. D7 the SAME / OPPOSITE badge ships **only after M-P7**, under the defect-derived abstain rule; flow numbers may ship before it. | `docs/research/s96_priority/p7/P7_flow_vs_book_design_note_2026-10-11.md`. Operator: "D1-D7 as recco'ed, proposed" (2026-10-11 17:55 IST). |

| **S96-B** | 2026-10-11 | M-P7 verdict cut | **As drafted in the M-P7 pre-registration §7:** per symbol INCONCLUSIVE below **20** ANCHORED sessions; otherwise SPEAKS if the overall abstain share is **≤ 1/2**, else SILENT. BUILD the badge only if both symbols speak; DECLINED-ON-EVIDENCE if either is silent. Flow numbers ship regardless (S96-A D7). | Operator: "1 - 20 sessions" (2026-10-11 18:12 IST), before commit and before any flow was computed on real data. |

| **S96-C** | 2026-10-11 | P7a board form | **Bricks replace the switch,** on the DEX tiles and the ladder: one scale; **solid = held since the pre-open, light = added, dashed outline = removed** (so a shrink and a zero crossing are visible). **The remembered pre-open value comes from the database**: seven columns appended to `v_dex_flow_vs_book` (pre-open OI valued at the settled delta, per strike and per leg, plus the no-anchor term), never from the browser. **Wording:** *"now · from x at pre-open OI · ±y since hh:mm"* — "at pre-open OI", not "at 08:30", because the split is OI change only. **Division of labour:** Lovable owns the visual form; the data read, the wording, the three-mark rule, gaps-never-zero and no-dealer-claim are fixed, enforced by the guard and the `/staging/` read against SQL; a reworded surface comes back to the operator. The same marks may later become a board-wide convention for quantities that change through the day, by its own ruling. | Operator: "I'll go with all your recco … design is lovable prerogative — you supply the idea and rules" (2026-10-11 19:46 IST). Mockup and rationale in session S96. |

| **S96-D** | 2026-10-11 | Untraded-leg guard (TD-S95-NEW-1 (c)) | **G1** per cycle, the badge abstains when the share of front DEX gross on **S2** legs (volume 0 so far, oi > 0, `oi_change = oi`) is **≥ 2 %** (the geometric mean of unmarked max 0.06 % and marked min 69.01 %); S1 rejected as a live rule; excluding S2 legs rejected. **G2** computed in the DB as columns appended to `v_dex_flow_vs_book`: `leg_s2_gross_cr`, `leg_s2_gross_share`, `untraded_guard`. **G3** it gates the M-P7 badge only; the abstain reason string needs the operator's yes; DEX tiles and bricks unchanged. | `docs/research/s96_priority/guard/guard_survey_result_2026-10-11.md` (outputs pinned there; code 345d1b2). Operator: "G1-G3 as recco'ed" (2026-10-11 20:51 IST). |

## Consequences recorded at ruling time

- **Next:** the M-P7 pre-registration (`docs/research/s96_priority/p7/MP7_flow_badge_prereg_2026-10-11.md`),
  committed before its first query.
- **Owed at doc-close:** roadmap §2.1 P7 row (IN PROGRESS; P7a / P7b); this file's pointer in `CURRENT.md`.
- **Nothing is applied by this ruling.**
