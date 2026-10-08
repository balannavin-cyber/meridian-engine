# Operator rulings — Session 92

Single source for S92 rulings. Other documents point here and do not restate them —
a ruling transcribed into a second place is a ruling that can drift out of agreement
with itself.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S92-A** | 2026-10-08 07:01 IST | Where parity closes (**amends S90-D**) | **Parity closes on ADR-025 D1 plus the P6 render pass**: every one of the fourteen layers carries a final disposition, the board renders every BUILT layer, and ADR-025 receives its closing amendment. **R2.4 (screenshot parity fixtures, scored per field) stays inside parity** as the ADR-025 D3 reference check. **R2.2, R2.3, R2.5 and R2.6 move post-parity.** Harness / agentic work is paused until parity closes; operational items continue. | S90-D tied parity close to the Stage 2 exit (golden days green on every deploy, parity fixture scores reported, one past day replays exactly). At 2026-10-08 only R2.1 had started in Stage 2, so a paused harness would have left parity unable to close under S90-D. The parity programme's own criterion (ADR-025 D1/D2) needs none of R2.2/R2.3/R2.5/R2.6. |
| **S92-C** | 2026-10-08 17:06 IST | L7/L8 badge | The S89 badge "PROVISIONAL -- T1 pending 10-07" is replaced by **"PROVISIONAL -- flow-vs-book (D-4) not built"** in both view COMMENTs and on every surface rendering them. | T1 PASSED 2026-10-07 on the A5 arm (ENH-98 S91 block), so the S89 text is false; the one remaining gap in L7/L8 scope is D-4. |
| **S92-D** | 2026-10-08 17:06 IST | Pin tab read path | Marketview reads pin history through a **thin view `v_pin_board`** (one session, front leg, pin / concentration columns only, `security_invoker = false`, `anon=r`). **`gex_cycle_history`'s ACL is not changed** — anon stays denied on the table. | The table's own DDL withholds anon deliberately, and with RLS off a table grant would be the whole boundary (TD-S81-NEW-2). `sql/2026-10-08_s92_v_pin_board.sql`. |
| **S92-E** | 2026-10-08 17:06 IST | D-4 vs PPC-1 | **D-4 (flow-vs-book classification) is recorded as an ADR-025 D3 deviation and stays in PPC-1, post-parity.** L7/L8 close on the second-order greek views (`v_gex_greeks_l2_strike` / `_net`) once rendered. | D-4's input, a previous-close ΔOI baseline, is PPC-1 — parked post-parity at S89. Un-parking it would put a new data product inside parity. |
| **S92-F** | 2026-10-08 17:06 IST | L12 disposition | **L12 is BUILT once the Pin tab ships**, on HHI (ENH-122) + rank (ENH-125) + pin state and conviction stage 1 (ENH-133, D-5c). The ranked-**pressure** leg stays DECLINED-ON-EVIDENCE (D-5a) and is recorded as a D3 deviation. Conviction stage 2 (30-session HHI percentile) is not a BUILT condition. | ADR-025 has one disposition per layer; L12 is the first layer with one leg declined and the rest built. Stage 2 needs ~6 weeks of `gex_cycle_history`. |

## Consequences recorded at ruling time

- **S90-D is amended, not deleted.** `docs/research/s90_agentic/rulings_s90.md` keeps S90-D as
  written; this file is where the amendment lives. Stages 0–1 work already deployed is unaffected.
- **R2.4's scores are reported, not a BUILT condition.** ADR-025 D2 states that agreement with the
  reference is not required for BUILT; S92-A keeps R2.4 as the D3 check without changing that. Any
  tolerance that would turn a fixture score into a gate needs its own ruling.
- **Not named by S92-A, recorded as the reading taken:** R2.1 (golden days) and R2.7 (tick freeze)
  keep their status and are no longer parity-close conditions. Operator to correct if that is not
  the intended reading.
- **Recorded in ADR-025 Amendment C** (C1), together with the clause-3 evidence the live board
  supplies (C2–C4).
- Roadmap tracker (`docs/research/s90_agentic/agentic_layer_roadmap_S90.md`) Stage 2 heading, exit
  line and the four moved items annotated to point here.
- **S92-B is not in this file.** It was ruled on the ops track (`SKIPPED_NO_INPUT` exits 0, commit
  `e0b9d03`) and is cited only from that commit; it belongs here and is owed at doc-close.
- **S92-C…F applied by** `sql/2026-10-03_s89_v_gex_greeks_l2.sql` (COMMENT restamp, V4 recomputed)
  and `sql/2026-10-08_s92_v_pin_board.sql`, and recorded in ADR-025 Amendment C, C6.
- **"BUILT once rendered" is not BUILT now.** L7, L8 and L12 stay PENDING in ADR-025 C4 until the
  Flows and Pin tabs read these views on the live board (D2 clause 3), measured as C3 was.
