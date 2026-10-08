# Operator rulings — Session 92

Single source for S92 rulings. Other documents point here and do not restate them —
a ruling transcribed into a second place is a ruling that can drift out of agreement
with itself.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S92-A** | 2026-10-08 07:01 IST | Where parity closes (**amends S90-D**) | **Parity closes on ADR-025 D1 plus the P6 render pass**: every one of the fourteen layers carries a final disposition, the board renders every BUILT layer, and ADR-025 receives its closing amendment. **R2.4 (screenshot parity fixtures, scored per field) stays inside parity** as the ADR-025 D3 reference check. **R2.2, R2.3, R2.5 and R2.6 move post-parity.** Harness / agentic work is paused until parity closes; operational items continue. | S90-D tied parity close to the Stage 2 exit (golden days green on every deploy, parity fixture scores reported, one past day replays exactly). At 2026-10-08 only R2.1 had started in Stage 2, so a paused harness would have left parity unable to close under S90-D. The parity programme's own criterion (ADR-025 D1/D2) needs none of R2.2/R2.3/R2.5/R2.6. |

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
