# Operator rulings — Session 92

Single source for S92 rulings. Other documents point here and do not restate them —
a ruling transcribed into a second place is a ruling that can drift out of agreement
with itself.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S92-A** | 2026-10-08 07:01 IST | Where parity closes (**amends S90-D**) | **Parity closes on ADR-025 D1 plus the P6 render pass**: every one of the fourteen layers carries a final disposition, the board renders every BUILT layer, and ADR-025 receives its closing amendment. **R2.4 (screenshot parity fixtures, scored per field) stays inside parity** as the ADR-025 D3 reference check. **R2.2, R2.3, R2.5 and R2.6 move post-parity.** Harness / agentic work is paused until parity closes; operational items continue. | S90-D tied parity close to the Stage 2 exit (golden days green on every deploy, parity fixture scores reported, one past day replays exactly). At 2026-10-08 only R2.1 had started in Stage 2, so a paused harness would have left parity unable to close under S90-D. The parity programme's own criterion (ADR-025 D1/D2) needs none of R2.2/R2.3/R2.5/R2.6. |
| **S92-B** | 2026-10-08 (ops track) | `SKIPPED_NO_INPUT` exit code (TD-S91-NEW-15) | In `compute_basis_context_local.py` a `SKIPPED_NO_INPUT` step **exits 0**; `exit_reason` stays `SKIPPED_NO_INPUT` and `error_message` is kept. **Scope: this call site only.** | Futures capture starts 09:30 IST and the orchestrator 08:30 IST, so with `LOOKBACK_MIN=30` the first 12 cycles of every trading day had no input and failed the whole cycle (no partial-success grading). Measured 2026-10-07: 12 cycles, 08:31–09:26 IST. Applied by `e0b9d03`. |
| **S92-C** | 2026-10-08 17:06 IST | L7/L8 badge | The S89 badge "PROVISIONAL -- T1 pending 10-07" is replaced by **"PROVISIONAL -- flow-vs-book (D-4) not built"** in both view COMMENTs and on every surface rendering them. | T1 PASSED 2026-10-07 on the A5 arm (ENH-98 S91 block), so the S89 text is false; the one remaining gap in L7/L8 scope is D-4. |
| **S92-D** | 2026-10-08 17:06 IST | Pin tab read path | Marketview reads pin history through a **thin view `v_pin_board`** (one session, front leg, pin / concentration columns only, `security_invoker = false`, `anon=r`). **`gex_cycle_history`'s ACL is not changed** — anon stays denied on the table. | The table's own DDL withholds anon deliberately, and with RLS off a table grant would be the whole boundary (TD-S81-NEW-2). `sql/2026-10-08_s92_v_pin_board.sql`. |
| **S92-E** | 2026-10-08 17:06 IST | D-4 vs PPC-1 | **D-4 (flow-vs-book classification) is recorded as an ADR-025 D3 deviation and stays in PPC-1, post-parity.** L7/L8 close on the second-order greek views (`v_gex_greeks_l2_strike` / `_net`) once rendered. | D-4's input, a previous-close ΔOI baseline, is PPC-1 — parked post-parity at S89. Un-parking it would put a new data product inside parity. |
| **S92-F** | 2026-10-08 17:06 IST | L12 disposition | **L12 is BUILT once the Pin tab ships**, on HHI (ENH-122) + rank (ENH-125) + pin state and conviction stage 1 (ENH-133, D-5c). The ranked-**pressure** leg stays DECLINED-ON-EVIDENCE (D-5a) and is recorded as a D3 deviation. Conviction stage 2 (30-session HHI percentile) is not a BUILT condition. | ADR-025 has one disposition per layer; L12 is the first layer with one leg declined and the rest built. Stage 2 needs ~6 weeks of `gex_cycle_history`. |
| **S92-G** | 2026-10-09 07:03 IST | L13 read path | **The OI tab reads `v_oi_rotation_since_open` (ENH-127)** and the client-side since-first-γ-run recompute is deleted — one implementation, not two. Anchor is the first chain snapshot at or after 09:15 IST; the change is shown per side (calls, puts), in quantity, on the chain clock, with the view's freshness and presence states surfaced (`n/c`, never 0). | ADR-025 C5 item 3 asked for one or the other, not both. The view was already live and anon-readable; measured as anon **19.1 ms**, index scans only. |
| **S92-H** | 2026-10-09 07:19 IST | SENSEX L13 | **SENSEX L13 stays "n/a" (`ΔOI · n/a (SENSEX · TD-S84-NEW-4)`) and is not fetched; L13 is BUILT on NIFTY.** Recorded as L13's **ADR-025 D3 deviation**. A SENSEX guard is post-parity, under TD-S84-NEW-4. | The SENSEX 09:15 anchor can come from a stale vendor row (−48.7M on 72,300 CE, 2026-09-25). A size cut-off would be a band with no measurement behind it; showing it raw would put a known artefact on the board. One clean session (10-08) does not close the TD. |
| **S92-I** | 2026-10-09 09:08 IST | Post-parity priority track | **Eight items form the operator's priority to-do, followed to conclusion once parity is closed** (it is: ADR-025 Amendment D, `579d273`): P1 level test · P2 dealer-side check · P3 invariants + independent recompute (R2.2/R2.3) · P4 Greeks evidence · P5 PPC-1 · P6 DEX standing book · P7 flow leg for DEX / ∂Δ/∂σ / ∂Δ/∂t (absorbs D-4) · P8 ∂Δ/∂t every cycle on expiry day (only if P4 shows predictive value). Each ends DONE with evidence or DECLINED-ON-EVIDENCE. Tracked in `agentic_layer_roadmap_S90.md` §2.1. | Triage of the 2026-10-09 upgrade-candidate list: the items that test MERIDIAN's premises (P1, P2, P4), protect its numbers (P3), or complete the exposure set GEX → DEX / ∂Δ/∂σ / ∂Δ/∂t with its flow leg (P5–P8). P8 amends L78-3 only by its own ruling. |
| **S92-J** | 2026-10-09 09:41 IST | Optional 3D view | **The operator's 3D experiment (`lab-3d`, `78fb26e`) is published to Marketview as an OPTIONAL view at `/board/3d`; the 2D board stays the default and unchanged.** Conditions: (a) its data comes from ONE database view, `v_gex_strike_terrain` (`sql/2026-10-09_s92_v_gex_strike_terrain.sql`) — no raw-table reads and no client-side recompute (the S92-G principle); (b) three.js loads only when `/board/3d` opens (lazy route); (c) a one-time guard, `mv_lovable_guard_lab3d.sh`, allows exactly the four packages, the route and the two new files, and nothing else; (d) γ in lower case, never vanna/charm (L78-1). Outside parity (ADR-025 D5); display-only. | Operator, 2026-10-09: "3 and 4 can be done right away". Closes TD-S92-NEW-2's proper fix by construction. |

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
- **S92-B is now in this file** (row above), recorded at the 2026-10-09 doc-close; it was ruled on the
  ops track and first cited only from `e0b9d03`.
- **S92-C…F applied by** `sql/2026-10-03_s89_v_gex_greeks_l2.sql` (COMMENT restamp, V4 recomputed)
  and `sql/2026-10-08_s92_v_pin_board.sql`, and recorded in ADR-025 Amendment C, C6.
- **"BUILT once rendered" is not BUILT now.** L7, L8 and L12 stay PENDING in ADR-025 C4 until the
  Flows and Pin tabs read these views on the live board (D2 clause 3), measured as C3 was.
  *(Met 2026-10-09 — ADR-025 C7.)*
- **S92-G and S92-H applied by** `meridian-connect` `1deeb87` (live 2026-10-09 07:47 IST) and recorded in
  ADR-025 Amendment C, C7–C8. With them **every layer carries a final disposition: BUILT 13 of 14,
  L11 DECLINED, PENDING 0.**
- **Not rulings, recorded so they are not re-litigated:** the board's tab numbers were removed at the
  operator's request (keys 1–6 still switch tabs); the words *"Textbook charm"* / *"Textbook vanna"*
  were removed from the two ∂Δ detail texts (L78-1 forbids the labels; the explanations stand); γ is
  shown as γ wherever a CSS `uppercase` had rendered it as Γ (`PIN (γ-conc)`, `NET-LONG γ`, and
  the ∂ headings, which had read ∂Δ/∂T and ∂Δ/∂Σ). The operator's 3D experiment is preserved on `meridian-connect` branch `lab-3d` and is
  **outside parity** (TD-S92-NEW-2).
- **S92-I recorded in** the roadmap tracker §2.1 (P1–P8). It is a priority order, not a build authorisation: P5–P8 are LIVE items and meet §11.3 controls before they start; P8 needs its own ruling amending L78-3.
- **S92-J applied by** `sql/2026-10-09_s92_v_gex_strike_terrain.sql` (authored and tested on a synthetic fixture: max pain 28/28 against `gex_pin_maxpain_history`, ACL anon=r / merdian_ro=r, 90 ms), `docs/lovable_prompts/s92/lovable_prompt_lab3d_optional.md` and `mv_lovable_guard_lab3d.sh`. Live only after the view passes Section 4 on the database and the guard passes.
