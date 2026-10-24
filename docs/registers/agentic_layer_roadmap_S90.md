# MERIDIAN — roadmap to an intelligent, agentic MERIDIAN (v2, 2026-10-05)

**Status: v2.16 — LIVE TRACKER, at `docs/registers/` from S95 (ruling S95-E) (S90 / Agentic MERIDIAN Session 1; the AM-1 post-close delta folded in at AM-2 / S91, 2026-10-07).** Stages 0–2 are ruled inside parity (S90-D) and ADR-031 is accepted (S90-C); this file is the single progress record. **S92-I (2026-10-09): parity closed; §2.1 holds the operator's post-parity priority track (P1–P8), followed to conclusion** for the agentic layer, and the Doc Protocol files point here rather than restating it. Items outside Stages 0–2 remain proposals; nothing here is a pre-registration. v1 (same path, earlier on 2026-10-05) answered the operator's seven-point sketch. v2 folds in the harness discussion that followed: ingest, compute and assumption harnesses; redundancy; the agent harness; staged build with exit tests; a tracker. The product is not named here, per the standing rule.

**Goal, in the operator's words:** an intelligent, agentic MERIDIAN that is self-learning, efficient, cost-effective and LLM-independent.

**Inputs:** v1 of this doc · `ADR-030` / `claude/ENH-133_schema_proposal_S89.md` · `claude/parity_dovetail_and_post_parity_plan_S89.md` · `claude/s89_1001_ladder_replay_findings.md` · `MERDIAN_Assumption_Register.md` · `tech_debt.md` (TD-081, TD-S82-NEW-3, TD-S69-NEW-2, TD-S89-NEW-1, TD-NEW-7, TD-NEW-L, TD-S53-NEW-5, ENH-83 write-path gap) · ADR-009, ADR-016, ADR-017, ADR-018, ADR-020, ADR-023, ADR-025, ADR-029 · `runbook_update_kite_flow.md` · `CLAUDE_history.md` S22 (Kite recovery path).

---

## How to use this doc

- **§1** is the shape and the principles. Read once.
- **§2** says where to start. The first five items, in order.
- **§3** is the stage plan. Every work item has an ID, an exit test and a status.
- **§4** is the scoreboard: numbers measurable from the database that show progress without anyone's say-so.
- **§5–§9** are the design detail behind the stages.
- **§10** lists the rulings owed.
- **§11** is the risk register for building on a live system, and the controls each item must meet before it starts.
- **Update rule:** the Status and Session columns in §3, and the Current column in §4, are updated whenever an item moves. A stage is DONE only when its exit test has evidence attached (commit, query output, or doc path).

---

## 1. Shape and principles

### 1.1 One system, eight layers, each only as good as the one beneath it

```
 Stage 6  Paper book → advisor agent                                   ▲ consumers
 Stage 5  Agent harness → watcher → commentator → reviewer             │
 Stage 4  Assumption harness + facts layer (state, events, base rates) │
 Stage 3  Redundancy (Kite hot standby) + history hygiene              │
 Stage 2  COMPUTE HARNESS   ── parity closes here ──                   │
 Stage 1  INGEST HARNESS                                               │
 Stage 0  SPINE: contracts · status · provenance · ledger · as_of      ▼ foundation
```

Stages 0–2 serve parity directly (admission by ruling A-5). Stages 3+ are post-parity. **Amended S92-A (2026-10-08):** parity now closes on ADR-025 D1 + the P6 render pass, not at the Stage 2 exit; of Stage 2 only R2.4 stays inside parity (`docs/research/s92_parity/rulings_s92.md`). **Parity CLOSED 2026-10-09** (ADR-025 Amendment D); the S92-A pause on harness work ends, and R2.2/R2.3/R2.5/R2.6 and Stages 3+ proceed as post-parity work. Stage 3 and Stage 4 can run in parallel. Stage 3b (global context: SPX, crude, US 10Y, US 30Y) starts after R0.8, R1.8 and R1.9, and its admission into the state vector waits for the Stage 4 event study (R3.12).

### 1.2 The four goals and what delivers each

| Goal | Delivered by | Measured by (§4) |
|---|---|---|
| **Intelligent** | Facts layer (state vector, events, base rates with n) built on verified data; commentary that says what changed and what it has meant | Calibration score per read word; commentary checker pass rate |
| **Self-learning** | Nightly labelling and as-of rebuild of base rates; assumption monitor; weekly review agent; **rules change only by stamped ruling** | Base rates with n ≥ minimum; assumption checks run; amendments proposed vs stamped |
| **Efficient, cost-effective** | Deterministic first (no model where code will do); models called on events only; routing (ADR-029); caching; compact facts payloads | Model cost/day; calls/day/symbol; share of Home lines produced without a model; cache hit rate |
| **LLM-independent** | Own thin model adapter; no rules in prompts; template fallback for every model output; eval set per model | Swap test: second model passes the same eval set |

### 1.3 Principles (all harnesses, now and later)

1. **Deterministic core, model at the edges.** Every number, state, event and base rate is versioned code. A model writes sentences, triages and proposes; it never computes a number and never changes a rule.
2. **Contracts before checks.** Every data product declares grain, expected cardinality, freshness SLA, required inputs and owner. Checks are generated from contracts by one runner, not hand-written per table. A new symbol or source becomes configuration.
3. **One status vocabulary, carried down the lineage.** OK / DEGRADED / STALE / MISSING, plus CLOSED for a source that is not expected to move now (its own session is shut). A layer's status is the worst of its required inputs; CLOSED is not a failure.
4. **Degrade the read, never fake it.** Missing shows as missing all the way to the screen. No stale fallback, no NULL-as-zero (D.26.6, D.28.5, ADR-023 D1).
5. **Provenance on every row:** source, `run_id`, code sha, config version, check results.
6. **Pure, replayable computation.** Output = f(inputs, code version, config version, `as_of`). No wall-clock time or "latest" views inside compute. Backfill and live share one code path.
7. **Rules as effective-dated data** (`merdian_parameters`, ADR-016). Replaying a day uses the rules as they were that day.
8. **The observer is independent of the observed.** Different host and credential chain. Write-and-flag; checks never block capture.
9. **Test the tests.** Every check has a fixture where it must fire (Loop D).
10. **SLOs and error budgets, not alert-per-blip.** One incident per root cause.
11. **One append-only ledger with correlation IDs.** Extend what exists; don't add a fifth log.
12. **Shadow before promote, for everything:** checks, rules, feeds, models (Measure → Validate → Shadow → Promote, generalised).
13. **Agents coordinate through the fact store, not by talking to each other.**
14. **No order tool, ever. No model ever places an order.**

---

## 2. Where to start

Today ENH-133 applies (≥ 16:00 IST). The first five items, in order. Each is small, and each is either a prerequisite for everything else or something already owed.

| # | Item | Why first |
|---|---|---|
| 1 | **R0.1 Spine inventory** (RO) — read-only pass: which tables carry `run_id` / source; what `script_execution_log`, ENH-71 `record_write`, the ADR-029 ledger and `merdian_parameters` actually hold; which compute paths use wall-clock time or latest-only views | No DDL. Turns "build the spine" into a precise gap list. Several spine pieces already exist and must be extended, not duplicated |
| 2 | **R0.4 ENH-133 apply + acceptance test** (LIVE, already ruled), including the stored 10-02 rows landing `is_trading_session=false` | Already scheduled. It is the first live instance of write-and-flag, and the first seeded-defect proof (Loop D #1) |
| 3 | **R0.2 Spine ADR draft** (RO) — contracts, status vocabulary, provenance, ledger consolidation, effective-dating via `merdian_parameters` | Everything after Stage 0 depends on these conventions; an ADR stops each stage re-inventing them |
| 4 | **R1.0 Operational prerequisites** (LIVE) — TD-NEW-7 (Kite token propagation automated) and TD-NEW-L (process supervision) | Without them the ingest harness reports the same outage every morning, and a Kite backup fails on the same morning as the primary |
| 5 | **R1.1 Contract registry + generated-check runner v0, in shadow** (SC) (report only), covering expected set, continuity, freshness-and-movement | Absorbs TD-S82-NEW-3 and TD-S69-NEW-2. Shadow first: it reports, it blocks nothing |

**R2.1 (freeze golden days)** is cheap and independent (OFF); it can start alongside any of these.

**Go/no-go:** RO and OFF items may start now. SC and LIVE items start only after rulings A-5 and A-8 and only when their class's controls (§11.3) are met. R0.4 is the exception: already ruled and scheduled.


### 2.1 Post-parity priority track — operator ruling S92-I (2026-10-09)

**Starts now:** parity closed at `meridian-engine` `579d273` (ADR-025 Amendment D). These eight items
are the operator's priority to-do and are **followed to conclusion**: each ends **DONE** with evidence
or **DECLINED-ON-EVIDENCE**, never left open. They run ahead of the rest of §3 unless the operator
says otherwise. Risk classes and the §11.3 controls apply as for any other item. Ruling text:
`docs/research/s92_parity/rulings_s92.md` (S92-I).

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| **P1** | **Level test** — how often the day's high / low lands within X pts (or Yσ) of a top-3 positive-γ strike, the pin, or a wall, against a null of random strikes at the same distance | RO | `gex_strike_snapshots` (from 2026-05-25), ADR-009 | Pre-registration committed **before** the first query; result table with the null | **DONE — A-NIFTY NO, B-NIFTY NO (levels do not beat the null); result doc `docs/research/s92_priority/P1_level_test_result_2026-10-09.md`** (pre-registration `docs/research/s92_priority/P1_level_test_prereg_2026-10-09.md`, hash `7a708a64c4bb73f0712a6d6e78f92a5d411a8ece`, accepted 09:16 IST) | S93 |
| **P1c** | **γ regime → realised range** — does positive net γ with high concentration go with a smaller realised range than other regimes, against a stated null? DTE as a reporting stratum only | RO | `gamma_metrics` / `hist_gamma_metrics`, `gex_strike_snapshots`, Assumption Register (dampening row), §7.2 starter card | Pre-registration committed **before** the first outcome query; result table with the null | **DONE — INCONCLUSIVE** (`c17e30d`; pre-registration `abde07ca`): NIFTY holdout pinned-positive n = 6 < 8 | S94 |
| **P2** | **Dealer-side check** — the dealer-short assumption behind every exposure sign, tested daily against NSE participant-wise OI (client / pro / FII / DII) | RO | ENH-115 (`participant_oi_daily`), Assumption Register | Per-day agreement table; register row updated | **DONE — REGIME-DEPENDENT** (`2dbf8a4`; pre-registration v2 `7342cacd`, `c920832`; v1 `f425f171` STOPPED on a mis-specified integrity gate, no verdict). NSE aggregate, sign only | S94 |
| **P3** | **Invariants and independent recompute** | SC | **= R2.2 + R2.3** (§3 Stage 2; their rows carry the status) | As R2.2 and R2.3 | **DONE (S97)** — **P3a DONE** (S95): PASS on the golden days under `ulimit -v 700000`, wired as `run_offline.sh` step 12/12 (`882df80`; its PE-sign mutant fixed). **P3b BUILT and tested, apply owed** (ruling S96-H): `public.p3b_sweep()` under `pg_cron`, shadow only, P3a's checks and tolerances; fixture PASS against P3a on the six golden days (0 mismatches, 24/24 mutants); real volume 2026-10-09 in 1,902 ms with I1–I4 n_fail 0 (`df84404`, `c549dfa`, `324f85c`; `docs/research/s96_priority/p3b/`). DDL `sql/2026-10-12_s96_p3b_invariant_checks.sql`. **P3b DONE (S97, ENH-145):** applied by the operator after the 2026-10-12 close; Section A's A-V row exact (17:36 IST); Section B exact on T4c's window, 09:00–15:30 IST (154 runs, 12 rows incl. I6; §D.51.1); `pg_cron` sweeps 2026-10-13 → 10-19 at 96 a day, 0 `SWEEP_ERROR`, 162–166 runs checked a day, **0 check FAIL**; 10-20 (holiday) and 10-21 (no data) heartbeat rows only, 0 runs (§D.51.7). Rulings `docs/research/s92_parity/rulings_s97.md` | S94, S95, S96, S97 |
| **P4** | **Greeks evidence** — replay ∂Δ/∂σ and ∂Δ/∂t from 2026-05-25 (as R2.4 replayed γ), then a pre-registered test: does the sign of ∂Δ/∂t at 10:15 on expiry days predict the 10:15 → close direction? | RO | ENH-98 views, ENH-131 repricer, R2.4 replay method | Pre-registration; replay table; result. n ≈ 19 expiries per symbol, so **indicative** | **PRE-REGISTERED, ACCRUING** (`cde0e0b`, `0a8af475`): re-anchored to **dte 1** (chain IV/delta only from 2026-08-24; L8 skips dte 0); scored at n = 20 per symbol (~13 weeks) | S94 |
| **P5** | **PPC-1** — previous-close OI baseline per strike | LIVE | PPC-1 (parked post-parity, S92-E) | Baseline row per strike per session, checked against the chain over several sessions | **DONE — LIVE 2026-10-11** (ruling S95-B): `v_oi_since_preopen` (**ENH-142**, `21d3142` / `47989ed`). Anchor = the session's pre-open row; measured over 26 changeovers per symbol (`docs/research/s95_priority/p5/`); Section 4 PASS, 4d = the probe-1 values | S94, S95 |
| **P6** | **DEX standing book** plus zero-Δ strike, on the board | LIVE | delta / OI / spot already in the chain; Lovable kit `docs/lovable_prompts/s92/` | View + ENH entry + DDL in `sql/`; board read as ADR-025 C7 was | **DONE** — view LIVE 2026-10-10 (ENH-140); **board read DONE** S95 (`392256a`); **S\*** `v_dex_repriced_zero` (**ENH-141**) pre-registered `7bfafb49`, scored APPLY, LIVE, on the board (`858cb46`) | S93, S94, S95 |
| **P7** | **Flow leg** for DEX, ∂Δ/∂σ and ∂Δ/∂t (absorbs ENH-98 **D-4**, the L7/L8 D3 deviation) | LIVE | P5, P6 | Flow-vs-book shown on the board; L7/L8 badge *"flow-vs-book (D-4) not built"* retired | **DONE (S97 live read)** — built and live S96. P7a `v_dex_flow_vs_book` (**ENH-143**, S96-A/C/D/E): flow bricks (`62f5c55`), untraded-leg guard (S96-D), SAME / OPPOSITE badge after M-P7 scored BUILD (`9321c57`; board `c81b700`). P7b: per-leg base `v_gex_greeks_l2_leg` under L7/L8 (S96-F, C5 bit-for-bit, `b3c5066`) and `v_delta_drift_flow_vs_book` (**ENH-144**, S96-G, `334ba38`), bricks on the two Δ tiles (`804d684`). **D-4 DECLINED-ON-EVIDENCE** (S96-I): the L7/L8 badge is amended, not retired — a permanent ADR-025 D3 deviation (`docs/research/s96_priority/p7/D4_classification_design_note_2026-10-12.md`). **Live read DONE 2026-10-12 09:54–10:01 IST** (`docs/research/s96_priority/p7/live_read_pack_2026-10-12.md`): L1–L4 equal on both symbols on matching runs | S94, S95, S96, S97 |
| **P8** | **∂Δ/∂t every cycle at dte 1** (re-scoped S95-G from "on expiry day") | LIVE | **P4 must show predictive value**; a ruling amending L78-3 | Per-cycle values at dte 1 on the board — or DECLINED-ON-EVIDENCE if P4 does not | **RE-SCOPED to dte 1** (ruling S95-G): per-cycle ∂Δ/∂t on the last day L8 computes. NOT STARTED — gated on P4 (unchanged) | S94, S95 |

**Decision points.** After **P1**: if the levels do not beat the null, the operator re-plans everything
below before more is built. After **P4**: if ∂Δ/∂t does not predict, **P8 is DECLINED-ON-EVIDENCE**
and ∂Δ/∂σ / ∂Δ/∂t stay display-only.

**2026-10-09: P1 returned NO on both arms. 2026-10-10: re-planned by ruling S94-A**
(`docs/research/s92_parity/rulings_s94.md`, which discharges S93-B): **P2 → P4 → P1c → P3**; **P5, P6
(apply included), P7 HOLD** until P2 and P4 report; P8 gated on P4. P1c added (S94-B); a DTE-conditioned
level test (P1b) deferred (S94-C). The board carries an evidence note on its levels (S94-D).** **Amended the same day by S94-G:** P5 and P6
released from the P4 hold; P7 held until P6 is live; P8 needs re-scope. Results: P2 REGIME-DEPENDENT, P1c
INCONCLUSIVE, P4 accruing. **S96 (2026-10-12):** P7 built and live, D-4 declined (S96-I), DONE on the first market-hours read; P3b built and tested (S96-H), apply owed. **S97 (2026-10-12 → 10-23):** P7 DONE on the live read; P3b applied and read on seven sessions of sweeps, so **P3 DONE**. P4 accruing; P8 gated on P4. **S98–S99 (2026-10-23 → 24):** §2.1 unchanged, except that P4 lost the SENSEX dte-1 session of 2026-10-21 to the Dhan Data API lapse (not back-fillable under P4 §6; S98-D); P4 accruing.

**Order.** ~~P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8. P5 and P6 are independent of P1–P4 and may run
alongside them.~~ **Superseded by S94-A:** P1 (DONE) → P2 → P4 → P1c → P3; P5 / P6 / P7 held; P8 gated on P4.

**Not on this track (triaged medium or low, 2026-10-09):** ΔOI × price four-case, volume ≥ OI, book
split by expiry, per-strike exposure through the session, price × time surfaces, 1-min flow cadence,
stock F&O. Longer-horizon, not on this track: R2.6 then a replay scrubber, 5-year 1-min history,
the agentic position layer; a regulatory check runs in parallel before anything is shown to others.

### 2.2 Open work — the single list (S99-C, 2026-10-24)

**Every open item has one home, and this is it** for everything that is not parked. Built from pass 1 (S98-A, `claude/s98_reconciliation_table.md` → committed with the S98 doc-close) and pass 2 (S99-C, `docs/research/s99/reconciliation_pass2.md`, all 364 open `tech_debt.md` entries). A TD keeps its full text in `tech_debt.md`; this list says what is next. **Order (S98-A §3, S99-E):** B1 → BS-1 → B2 → B3 → B4 → B5 → B6, then BR and the rest of BS before any retail build; BO and BD one session each when the market is shut. **After the list:** retail (§2.3) → agentic (§3 Stages 3–6, ON HOLD, S99-D) → the signal / ICT stream (68 items parked, pass 2 §3.9; ranked after agentic, S99-G). §2.1 (P4 accruing, P8 gated) runs alongside.

| Band | Item | What | TDs | Status |
|---|---|---|---|---|
| B1 | **R1 + R41 (S98-B)** | γ runner waits for its own cycle's chain run; closing cycles 15:30 / 15:35 / 15:40 | TD-S97-NEW-4, TD-S82-NEW-1, TD-S82-NEW-2; re-measure TD-S80-NEW-9, TD-S78-NEW-8 | DEPLOYED `2edd25f` 2026-10-23; live PASS read Mon 2026-10-26 after 15:45 IST |
| B1 | **R2 + R21** | WCB writer: "COMPLETED" with no row; holiday placeholder rows; stray no-symbol cron line; 16:00 futures leg exits 1 on holidays; weight / threshold drift | TD-S97-NEW-9, -10, -8 (absorbs TD-S81-NEW-13), TD-S41-NEW-5 | **PART DONE `3706435`** (S99-H / S99-I): TD-S97-NEW-8, -9, -10 CLOSED, live check Mon 2026-10-26 08:31 and 15:40 IST; OPEN: the 16:00 futures leg on holidays, TD-S41-NEW-5 |
| B1 | **R3** | monitor cannot see a hung orchestrator run | TD-S97-NEW-3 | OPEN |
| B1 | **R4** | one 08:25 IST pre-open probe: Dhan subscription + Kite token; feed silence and heartbeat; preflight gives up after ~23 s (10-15, 10-19) | TD-S97-NEW-5, -6 (absorbs TD-S91-NEW-3, TD-S71-NEW-10, TD-S69-NEW-6, TD-NEW-7), TD-S86-NEW-2, -3, TD-S91-NEW-17, TD-NEW-C, TD-NEW-9, TD-S80-NEW-17 | OPEN; Kite automated login = operator ruling |
| B1 | **R40, R42–R44** | breadth writer overlap and NULL status; monitor window takes the first cron line; SKIPPED_NO_INPUT labelled benign / crash | —  (pass 1 rows; S98 build read) | OPEN — read first |
| B1 | **R48, R49** (S100-B) | `run_ingest.sh` `set -e` makes its `rc=$?` unreachable; the monitor alarms on `exit_code` alone, so any skip that exits 1 pages CRITICAL (behaviour, recorded so a "benign" skip is never given exit 1 unknowingly) | — (S98 build read) | OPEN |
| B1 | **Ledger and capture trust** | off-box `equity_eod` cursor writer; Dhan 500 drops a cycle; basis context cron hour; token held from construction; hand-rolled ledger inserts; breadth guard only in the health check; ingest contract too permissive | TD-S90-NEW-14 (absorbs TD-S91-NEW-16), TD-S81-NEW-11, TD-S81-NEW-12, TD-S81-NEW-20, TD-S77-NEW-8 (absorbs TD-023), TD-S74-NEW-4, TD-082 | OPEN |
| BS1 | **Credential rotations (S99-E)** | Dhan token anon-readable window: rotation decision and log review; `.env` printed to a transcript: rotate | TD-S81-NEW-1, TD-S71-NEW-11 | OPEN — operator actions |
| B2 | **R5 + R38** | closing session: official close printed from the 15:40 chain spot; no "LIVE" on a held value; CLOSED state; basis from the displayed spot; SPOT label from the bar window | R5 (absorbs TD-S91-NEW-18, TD-S90-NEW-13, TD-S74-NEW-3, TD-S74-NEW-5), R38 (absorbs TD-S54-NEW-2) | OPEN — TD halves first; labels in B5 |
| B2 | **R20** | board prev-close read (10-22 "prev close missing" after the row existed) | TD-S97-NEW-13 | OPEN — re-scoped S98-D |
| B3 | **R7 + OI readers** | same-minute OI read on our data; vendor OI on untraded legs; L13 anchor on stale vendor rows | TD-S95-NEW-1 (residual), TD-S84-NEW-4 | OPEN — read |
| B3 | **R8** | front-future basis jumps | — | OPEN — read |
| B3 | **R10 + flip family** | repriced root between same-sign strikes; flip gate degenerate; repriced vs landmark; cumulative vs `flip_level`; SENSEX 1.0 % vs 34.3 % | TD-S79-NEW-15, -16, -17, -18 | OPEN — read |
| B3 | **R18** | prev close and spot per surface at the open (F-4 figures) | TD-S88-NEW-1 | OPEN — read |
| B3 | **R16 + R36** | tab not re-polling γ views; Pin tab leader / reconciled state | TD-S97-NEW-19 | OPEN — evidence 2026-10-23 |
| B3 | **Chain data correctness** | zero IV in `atm_iv_avg`; depth-2 single expiry; far-wing / ITM IV; SENSEX no γ on ~30 % of strikes; `gex_cr` filter split; deep-ITM γ constant; ltp below intrinsic | TD-S83-NEW-2, -3, -4, -5, TD-S79-NEW-8, TD-S75-NEW-1, -2, TD-S71-NEW-13 | OPEN — read |
| B4 | **R9** | Health page CRITICAL; untrack the ICT writer; SUBSCRIPTION class | TD-S97-NEW-21 (absorbs TD-S77-NEW-14, TD-017) | OPEN |
| B4 | **R19** | breadth daily gaps and gate | TD-S97-NEW-11, -12, TD-S91-NEW-5 | OPEN |
| B4 | **R22** | calendar repair: missing 01-15, 01-26, 03-03, 05-28; "Normal trading day" on closed 06-26 / 09-14 / 11-24; 03-31 name (read 2026-10-24) | TD-S97-NEW-14, TD-S81-NEW-7, TD-S41-NEW-1 | OPEN — operator SQL |
| B4 | **R23** | symbol column on `data_contamination_ranges`; `merdian_ro` visibility | TD-S97-NEW-15, TD-S94-NEW-1 | OPEN — operator DDL |
| B4 | **R24** | Marketview backup retention | TD-S97-NEW-16 | OPEN |
| B4 | **Pass-2 misses** (S100) | open by their own Status, excluded by pass 2's keyword test: V18E engine weekend-before-special-session order; TD-S69-NEW-1 heading / Status contradiction (part b); ICT cohort row counts; CAS close capture fixed, not closed | TD-S82-NEW-4, TD-S80-NEW-19, TD-S76-NEW-17, TD-S90-NEW-12 | OPEN — disposition owed |
| B4 | **R34 + R35** | legacy Context / Structure pages; two IV skews | — | OPEN — ruling: retire or align |
| B4 | TD-S96-NEW-2 | the planner estimates 1 row for a day of `gex_strike_snapshots` selected by `ts` alone | — | OPEN |
| B4 | TD-S94-NEW-2 | `bin/roq.sh`'s write-verb guard refuses `COPY (SELECT …) TO STDOUT`, which is a read | — | OPEN |
| B4 | TD-S93-NEW-1 | `run_offline.sh`'s `PIPESTATUS` idiom is positional, so inserting any command between a pipeline and its te… | — | OPEN |
| B4 | TD-S91-NEW-2 | SEVEN more unpadded `fromisoformat` sites, one now fixed, and ~40 copies of the same padding with no shared… | — | OPEN |
| B4 | TD-S91-NEW-4 | `ws_feed_zerodha.log` stamps UTC time under an "IST" label | — | OPEN |
| B4 | TD-S90-NEW-1 | `dhan_scrip_map` is never re-synced against the scrip master, so every NSE series change leaves a dead secu… | — | OPEN |
| B4 | TD-S90-NEW-3 | about 26 calendar gates are still inline copies, not `core/trading_calendar_gate.py` | — | OPEN |
| B4 | TD-S90-NEW-5 | `v_gex_max_pain` fails intermittently at about anon's 3-second statement timeout | — | OPEN |
| B4 | TD-S90-NEW-9 | every `roq.sh` connection warns of a collation version mismatch | — | OPEN |
| B4 | TD-S83-NEW-6 | `.gitignore` covers `*.log` but not rotated logs or `status.json`, so the widened logrotate scope produces… | — | OPEN |
| B4 | TD-S81-NEW-4 | `v_dealer_flow_sim` is the third ADR-021 sibling and was never scoped; it returns 57014 on any unfiltered read | — | OPEN |
| B4 | TD-S81-NEW-6 | `v_max_pain_by_strike.max_pain` has a non-deterministic tie-break | — | OPEN |
| B4 | TD-S79-NEW-6 | three untracked scratch files sit in the production tree | — | OPEN |
| B4 | TD-S79-NEW-9 | `pin_risk_score`'s proximity component is ABSENT, not depressed, so the score silently changes basis betwee… | — | OPEN |
| B4 | TD-S79-NEW-21 | `_FLIP_DOMINANCE_EPS_FRAC` is a hardcoded magic number on a live operator surface, and it is relative to th… | — | OPEN |
| B4 | TD-S78-NEW-2 | 67 backup artefacts are tracked in git with no retention rule, and `.gitignore` cannot remove them because… | — | OPEN |
| B4 | TD-S76-NEW-2 | `pg_cron jobid 19` disabled as a stop-gap: `gamma_metrics` now grows past its 90-day window, and the stated… | — | OPEN |
| B4 | TD-S73-NEW-2 | a literal Windows path exists as a directory on the Linux host and something writes into it daily | — | OPEN |
| B4 | TD-S72-NEW-4 | `gex_strike_snapshots` carries a duplicate index and a third that is redundant against the composite | — | OPEN |
| B4 | TD-S71-NEW-3 | the VIX history read has no `ORDER BY`; its correctness depends on unspecified row ordering | — | OPEN |
| B4 | TD-S71-NEW-5 | `run_ingest.sh` `set -eo pipefail` makes its own `END … rc=` line unreachable on failure | — | OPEN |
| B4 | TD-S71-NEW-8 | `capture_premarket_0908.py` is an orphan whose filename encodes an instant that ceases to exist on 2026-09-07 | — | OPEN |
| B4 | TD-S71-NEW-12 | `.gitignore` `*_PRE_S*` silently swallows the crontab backups it was never written for | — | OPEN |
| B4 | TD-S70-NEW-4 | `india_vix_history` has no writer and has been frozen at 2026-03-11 for five months; `vix_percentile` is sc… | — | OPEN |
| B4 | TD-S69-NEW-3 | `fetch_positioning_landscape` has no ADR-018 D2 recency floor; the ADR-021 speed fix converts a loud timeou… | — | OPEN |
| B4 | TD-S60-NEW-5 | `core/config.py` hardcodes Windows `BASE_DIR = C:\GammaEnginePython`; loads `.env` from a path that doesn't… | — | OPEN |
| B4 | TD-S38-NEW-2 | Dead `TIMEOUT_LIVE_DEFAULT` + `TIMEOUT_SHADOW_DEFAULT` constants in `run_option_snapshot_intraday_runner.py` | — | OPEN |
| B4 | TD-005 | `option_execution_price_history` table marked DEPRECATED but not yet DROPPED | — | OPEN |
| B4 | TD-007 | `is_pre_market` column in `hist_spot_bars_1m` is vestigial | — | OPEN |
| B4 | TD-009 | `.bak` file debris in `docs/registers/` | — | OPEN |
| B4 | TD-025 | `build_spot_bars_mtf.py` re-aggregates full history every run (compute waste) | — | OPEN |
| B5 | **R14 + R33** | dealer claims on the Hedge tile, flows read, Home card 4, Net Γ drawer; upper-case Γ literals | TD-S97-NEW-17 (absorbs manual F-1, F-7) | OPEN — wording |
| B5 | **R15** | draw the ∂Δ flow gap (G25) as G19 is drawn | TD-S97-NEW-18 | OPEN — wording |
| B5 | **R17** | pocket word: keep it, add the net sign | — | OPEN — ruling |
| B5 | **R11 + R39** | board consistency: degenerate corridor, SPOT ≡ FLIP, read text vs PIN wall, CLOCKS absent; "gap filled" when it is not | TD-S90-NEW-6, TD-S90-NEW-7, TD-S81-NEW-9 | OPEN |
| B5 | TD-S84-NEW-7 | the UI labels `flip_distance_pct` as sigma, so a spot-to-flip distance is rendered as a volatility band | — | OPEN |
| B5 | TD-S84-NEW-6 | two max pains over different substrates, agreeing on strike and disagreeing on everything else; which is ca… | — | OPEN |
| B5 | TD-S39-NEW-5 | Marketview "stale {N}s" badge contradicts 300s threshold setting — needs live-day verification | — | OPEN |
| B6 | **R12** | three-state regime (short / at the flip / long), pre-registered | — | OPEN |
| B6 | **R13** | pin hysteresis and tie state, pre-registered | — | OPEN |
| B6 | TD-S80-NEW-1 | the ingest discards the expiry ladder the vendor returns, so no multi-expiry IV exists at any timestamp and… | — | OPEN |
| B6 | TD-S79-NEW-1 | `GREATEST(dte, 1)` overstates σ on expiry day, so the moneyness band is widest on the day it most needs to… | — | OPEN |
| BS | **TD-S99-NEW-1** | an AWS access key ID is committed in the public repo (no secret key found); redact, then rotate or rewrite history | — | OPEN — operator's call |
| BS | TD-S92-NEW-4 | the S92 views grant `authenticated` more than `SELECT`, through default privileges | — | OPEN · retail |
| BS | TD-S90-NEW-8 | Marketview Settings is read-only since S90-E; the authenticated write route, `changed_by` and `config_versi… | — | OPEN · retail |
| BS | TD-S90-NEW-10 | unused Breeze credentials remain in `.env` | — | OPEN · retail |
| BS | TD-S89-NEW-5 | the Marketview bundle reached internet scanners while `:80` served it un-gated, so every anon-readable rela… | — | OPEN · retail |
| BS | TD-S89-NEW-4 | TCP 80 is still open to the world at the security group; the `:80` hardening makes the port answer only red… | — | OPEN · retail |
| BS | TD-S84-NEW-5 | `anon` holds `MAINTAIN` beyond `SELECT` on three objects created before the S81 default-privileges fix | — | OPEN · retail |
| BS | TD-S81-NEW-2 | anon SELECT is still far broader than the 23 relations the frontend consumes | — | OPEN · retail |
| BS | TD-S81-NEW-3 | nothing asserts that the anon revoke is still in force; item 3 of the S81 fix is trusted rather than verified | — | OPEN · retail |
| BS | TD-S81-NEW-16 | `merdian_ro` reads zero rows, silently, from 57 RLS-enabled tables, and a FAIL was reported to the operator… | — | OPEN · retail |
| BS | TD-S39-NEW-3 | `.env` containing live MERIDIAN Supabase anon key committed to public GitHub repo `balannavin-cyber1/meridi… | — | OPEN · retail |
| BS | TD-S39-NEW-4 | Orphan AWS Security Group `launch-wizard-2` not attached to any EC2 instance — cleanup pending | — | OPEN · retail |
| BR | TD-S92-NEW-6 | the Marketview build box has no bun and Lovable updates only `bun.lock`, so a dependency change breaks the… | — | OPEN · retail |
| BR | TD-S92-NEW-3 | `sql/2026-10-03_s89_v_gex_greeks_l2.sql` says its V2 probe is "committed with this file", and it is not in git | — | OPEN · retail |
| BR | TD-S84-NEW-3 | three views ship a `COMMENT ON VIEW` in `sql/` that was never executed live, and one ships its `GRANT` comm… | — | OPEN · retail |
| BR | TD-S84-NEW-2 | `gamma_metrics` has no `CREATE TABLE` anywhere in `sql/`, an ADR-025 D2 clause 4 gap on the most-read objec… | — | OPEN · retail |
| BR | TD-S84-NEW-1 | the `sql/` file does not reproduce the live `merdian_ro` grant on two of the three S83 views, so a rebuild… | — | OPEN · retail |
| BR | TD-S81-NEW-5 | `sql/` is not a true rebuild source, and the divergence runs in BOTH directions | — | OPEN · retail |
| BR | TD-S81-NEW-8 | `~/redeploy_marketview.sh` builds from a stale May-27 clone, not the tree the live bundle comes from | — | OPEN · retail |
| BR | TD-S80-NEW-16 | `/etc/logrotate.d/meridian` exists only on the box: third instance of on-box-only infrastructure after the… | — | OPEN · retail |
| BO | TD-S80-NEW-15 | ~1.76 GB of the 2.5 GB that filled the root volume is unattributed, so the resize is a delay of known lengt… | — | OPEN |
| BO | TD-S73-NEW-1 | `shadow_runner.log` is a 262 MB live log at repo root, outside logrotate's scope, while its cron line's vis… | — | OPEN |
| BO | TD-S73-NEW-6 | `eod_health_check.py` has no scheduled invoker; the fourth instance of the class, and TD-S72-NEW-7's premis… | — | OPEN |
| BO | TD-S71-NEW-14 | `dhan_scripmaster` has no scheduled reload, and futures contract resolution has no fallback: the table sile… | — | OPEN |
| BO | TD-S69-NEW-2 | `scripts/eod_health_check.py` returned `[OK]` on 2026-08-12 while pin/accel, the M5 detector and the GEX re… | — | OPEN |
| BO | TD-S53-NEW-5 | S52 observability monitors report false state (both directions) + watchdog shares the patient's failure chain | — | OPEN |
| BO | TD-NEW-B | `pg_cron` job failures invisible by default — needs polling daemon or session-start gate | — | OPEN |
| BO | TD-027 | `merdian_pipeline_alert_daemon` scope drifted from name | — | OPEN |
| BO | TD-028 | `merdian_pm.py` silently fails on unknown process name | — | OPEN |
| BD | TD-S94-NEW-3 | an apply copied out of the terminal landed only Section 1 of the DEX view, the editor said Success, and the… | — | OPEN |
| BD | TD-S87-NEW-2 | `check_xrefs` cannot see `AC29-n` labels or `§5a`/`§5b` references, and its document map is hard-coded, so… | — | OPEN |
| BD | TD-S87-NEW-5 | `session_log.md` carried 11 entries against a documented "newest 10", so an earlier doc-close skipped the r… | — | OPEN |
| BD | TD-S86-NEW-1 | the S74 Doc Protocol v4 Rule 7 amendment never reached `MERDIAN_Documentation_Protocol_v4.md`, so two docum… | — | OPEN |
| BD | TD-S83-NEW-7 | two register errata, one of which was itself misattributed in this session's own capture | — | OPEN |
| BD | TD-S81-NEW-15 | the register says `merdian_order_placer.py` runs from an `@reboot` cron line; neither the line nor the proc… | — | OPEN |
| BD | TD-S80-NEW-4 | the documented commit-message pattern emits a BOM, and one shipped inside a commit subject this session | — | OPEN |
| BD | TD-S80-NEW-7 | `gex_pin_maxpain_history` is a Rule 10 schema-affecting table with no ADR of its own | — | OPEN |
| BD | TD-S80-NEW-12 | the deploy-direction correction has been drafted and UNRATIFIED since S73, and S80 acted against the topolo… | — | OPEN |
| BD | TD-S80-NEW-14 | `tech_debt.md` closed TD-S79-NEW-14 and left three references to it stale one file over | — | OPEN |
| BD | TD-S79-NEW-5 | the deploy-direction inversion, third and fourth instances: two independent commits of identical content in… | — | OPEN |
| BD | TD-S79-NEW-7 | the S74 Doc Protocol amendment cites a rule number belonging to a different rule, and amends a rule the nam… | — | OPEN |
| BD | TD-S79-NEW-11 | ADR-017 Principle 6 is right about the bug and wrong about the cause: it is a DTE difference, not a symbol… | — | OPEN |
| BD | TD-S79-NEW-24 | Doc Protocol v4 Rule 11.3's governance-footer obligation is unenforced, and compliance cannot be counted be… | — | OPEN |
| BD | TD-S79-NEW-25 | there is no project-knowledge manifest, so Rule 12 compliance is undetectable by construction | — | OPEN |
| BD | TD-S79-NEW-26 | Rule 12's re-upload list omits five of the documents the session-end checklist requires to be updated, so f… | — | OPEN |
| BD | TD-S78-NEW-1 | the session-date convention is unspecified in Doc Protocol v4, and the only format v4 does specify cannot e… | — | OPEN |
| BD | TD-S78-NEW-3 | project knowledge round-trips LF to CRLF, so the Rule 12 hash comparison cannot distinguish an identical fi… | — | OPEN |
| BD | TD-S77-NEW-4 | `/patch_*.py` is gitignored, so not one patch script in MERIDIAN's history is in version control | — | OPEN |
| BD | TD-S77-NEW-7 | `script_execution_log.host` is not evidence of which machine ran a script | — | OPEN |
| BD | TD-S76-NEW-11 | F-82: nine of eighteen `ADR-004` line citations in the S76 audit were wrong, in four distinct ways, and eve… | — | OPEN |
| BD | TD-S76-NEW-12 | Rule 7 splice-discipline defect in S75's own doc-close: the Topology splice anchored on the wrong footer an… | — | OPEN |
| BD | TD-S76-NEW-15 | Doc Protocol v4 asserts `CURRENT.md` is mixed-EOL and must be edited in binary mode; measured, it is pure L… | — | OPEN |
| BD | TD-S76-NEW-16 | `merdian_reference.json`'s own version control is unreliable: two `change_log` arrays ten sessions apart, a… | — | OPEN |
| BD | TD-S76-NEW-21 | ADR-004's Amendments A and B are absent from the Decision Index entirely, and Amendment C's new marker make… | — | OPEN |
| BD | TD-S76-NEW-22 | Session Management Rule 5 specifies a twelve-field session-log block; the log abandoned it ~2026-04-07 and… | — | OPEN |
| BD | TD-S76-NEW-23 | the production checkout `~/meridian-engine` sat 22 commits behind `origin/main` at the S76 close, having ne… | — | OPEN |
| BD | TD-S75-NEW-4 | ADR-002 v2's build sequence and the Enhancement Register use ENH-80..85 for different things; the register… | — | OPEN |
| BD | TD-S73-NEW-10 | the System Map and Deployment Topology `## Update log` tables are frozen at Session 67 while both files rec… | — | OPEN |
| BD | TD-S73-NEW-7 | the Claude Code permission model is verb-shaped, not effect-shaped, and the config itself is untracked | — | OPEN |
| BD | TD-S73-NEW-9 | approved diffs are not hunk-independent, and a partial application produced a quieter failure than the defe… | — | OPEN |
| BD | TD-S72-NEW-12 | byte-size comparison across storage tiers is invalid under `core.autocrlf=true`; Doc Protocol v4's four-tie… | — | OPEN |
| BD | TD-S71-NEW-1 | `merdian_reference.json` does not cover the files and tables the register's own read-rule points at | — | OPEN |
| BD | TD-S70-NEW-1 | `CURRENT.md` is 661 KB of which 98% is superseded session blocks, and it is read second at every session open | — | OPEN |
| BD | TD-S57-NEW-3 | Enhancement Register has a dual structure with conflicting per-ENH status | — | OPEN |
| BD | TD-S46-NEW-2 | S3 deployment automation wrapper scripts (reduce manual workflow) | — | OPEN |
| BD | TD-015 | `run_preflight.py` 4-stage preflight system is undocumented; reinvented as one-off | — | OPEN |
| BD | TD-021 | Two undocumented operational conventions surfaced during Session 8 | — | OPEN |
| BD | TD-037 | Schema column-name inconsistency across timestamp-bearing tables | — | OPEN |
| BD | TD-053 | CLAUDE.md Rule 16 needs era-aware addendum (post-04-07 era) | — | OPEN |

**Parked from pass 1 (S98-A):** R25 hover-to-explain · R26 √τ-normalised GEX (absorbs TD-S75-NEW-3) · R27 γ ceiling / floor slot · R28 pin history write-once (a design constraint) · R29 new substrates (P8 gate) · R30 settlement probability (declined for now). **Done in pass 1:** R37 (S98-C, 2026-10-23), R45 (S98-B patch), R46 (ruled acceptable).

### 2.3 Retail (broker-connect) — scoping, not started (S99-F, 2026-10-24)

The end state: a user connects their own broker account; MERIDIAN computes on that user's data and shows it to that user only. MERIDIAN's own licensed feed is never shared. Not started; it follows §2.2.

| Gate | Question | State |
|---|---|---|
| **G1** | Regulatory: does a descriptive, no-recommendation product need SEBI registration (RA Regulations as amended 2024)? | **OPEN** — with the operator's securities counsel (Claude Doc "MERIDIAN — Product brief for securities counsel"). Operator's position: permitted while no levels, entries or targets are given. Fallback if counsel says otherwise: RA registration |
| **G2** | Data licensing: is a computation on a user's own broker data, served only to that user, redistribution? | **RULED** (S99-F): no. Each broker's API terms checked at build |
| **G3** | MERIDIAN's own feed | **RULED** (S99-F): never shared |
| **G4** | Architecture and capacity | **RULED** (S99-F): elastic; start small; build to grow, not a behemoth |

**Prerequisites before any retail build:** R1–R5 and R11 (pass 1), every BS and BR row in §2.2. Pass 1 R32 lives here.


---

## 3. Stage plan and tracker

**ON HOLD (S99-D, 2026-10-24): Stages 3, 3b, 4, 5 and 6** — agentic MERIDIAN waits until §2.2 is done. Stage 0–2 jobs already live keep running as maintenance (R0.3, R0.4, R1.2 in shadow, R1.5, R2.1, R2.7); a break in one is a §2.2 item; no new Stage 0–2 build. The signal / ICT stream ranks after agentic (S99-G).

**Risk class** (controls for each in §11.3): **RO** read-only (reads the live database or docs, changes nothing) · **OFF** offline (works on copies or after the close, writes only its own artefacts) · **SC** sidecar (new tables or processes beside the live path; live path untouched) · **LIVE** touches the capture or write path, schema of live tables, token flow, or Home.

**Status values:** NOT STARTED · IN PROGRESS · DONE (evidence linked) · DECLINED-ON-EVIDENCE · BLOCKED (reason).
**IDs** are roadmap-local (R*stage*.*n*). An item becomes an ENH or TD entry in the registers when it is ruled in; record that ID in the Item column.

### Stage 0 — Spine

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| R0.1 | Spine inventory (read-only) | RO | — | Doc listing what exists and the gap list | **DONE** — `docs/research/s90_agentic/R0.1_spine_inventory_S90.md` (gap list §8 maps to R0.3/R0.5/R0.6/R0.7/R0.8/R1.9; P1 `p1_catalog_s90.out`, P4/P5 after close). Findings R01-F1…F9; F1 (runner writes no exec-log row) still needs the box log | S90 |
| R0.2 | Spine ADR: contracts, status vocabulary, provenance, ledger, effective-dating | RO | ADR-016, ADR-023, ADR-030 | ADR drafted and ruled | **IN PROGRESS** — drafted: `docs/decisions/ADR-031-spine-contracts-status-provenance-ledger.md` (D1 contracts, D2 status enum incl. NOT_COMPUTED/UNKNOWN, D3 provenance, D4 as-of config + closed write path, D5 calendars, D6 new-table access, D7 one ledger). **Ruled: accepted (S90-C)**; D4.3 ruled S90-E (revoke now). Number provisional until doc-close | S90 |
| R0.3 | Provenance columns (`run_id`, `source`, `code_sha`, `config_version`) on capture tables | LIVE | ENH-133 already carries `run_id`, `chain_ts` | Every new row carries them; coverage query = 100 % | **DEPLOYED `ca79717` 2026-10-06 04:53 IST (operator chose pre-market)** — via run_id (ADR-031 D3a, ruling S90-I): ExecutionLog writes `run_id`/`product`/`status`; ingest, gamma, volatility wired (`docs/research/s90_agentic/patches/patch_r07_ledger.py`, tested offline); coverage view `v_provenance_coverage_daily`. **`df80dec`:** each extra expiry leg now writes **its own ledger row** (`log_child_run`, ADR-031 D3a/D7) — the chain measured **52 % traced** because one `run_id` covered N legs, so the coverage view could not reach 100 % by construction; `tests/test_execution_log_child.py` offline. **Verify 100 % on 2026-10-07 after 09:30** | S90 |
| R0.4 | ENH-133 apply + acceptance test | LIVE | ADR-030, ENH-133 proposal §9 | 100 % per-symbol `ts` coverage; holiday rows flagged (`session_gate_state = FROZEN` in the applied DDL) | **IN PROGRESS** — applied 2026-10-05 ~17:05 IST, scope by ruling S90-A (`docs/research/s90_agentic/rulings_s90.md`): table + 8 pin-state params live; **accepted on the empty table**: P3 (jobid 19 off and not naming the table; 8 keys `numeric`; read-back 12), P2 X1, X2 (40 cols = DDL), X3, X5, A(a) 35/35. **X4 failed then fixed:** RLS was ON with 0 policies (enabled at the SQL editor's run-time prompt) and `authenticated=rm` (default privileges), though the DDL enables neither — corrected by `2026-10-05_s90_enh133_rls_fix.sql` (RLS off; ACL postgres/service_role/merdian_ro=r). Front leg only (S90-B). **Wired (ruling S90-F):** writer in the runner after gamma+vol, off switch `ENH133_WRITER_ENABLED`, 57014 bounded retry (`5ac0ed0`); manual writes 17:53 (SENSEX OK; NIFTY 57014 then OK) — values match the board; EOD reconciler run clean then scheduled `55 10 * * 1-5` (`be36d48`, crontab = mirror). First live cycle 2026-10-06 09:15. **Remaining:** G1–G3, A(c)–A(e), R1–R6 on live rows | S90 |
| R0.5 | Status vocabulary as one enum, plus a lineage declaration (which product needs which inputs) | SC | — | Enum in schema; lineage table seeded for core products | **DRAFTED, not applied** — `docs/research/s90_agentic/2026-10-05_s90_DRAFT_r05_r11_status_contracts.sql` (enum `merdian_status`, `product_lineage`, 12 edges). A-8/A-5 ruled (S90-C/D); apply file `2026-10-05_s90_apply_S90E_r05_r11.sql` | S90 |
| R0.6 | Effective-dated config: finish ADR-016's write path | SC | `merdian_parameters` (read API exists, write side missing — ENH-83 gap in `tech_debt.md`) | A key written, read back and superseded with `change_reason` | **IN PROGRESS** — D4.1 as-of read `get_parameter_num(key, as_of)` (20:26 IST, gate: agrees with the 1-arg read on all active keys); proven on `pin.tau.NIFTY` history (0.30→0.25→0.30, 1 s before each change reads the prior value). D4.3 write path closed to anon (S90-E). Remaining: authenticated write route for Settings; `config_version` on written rows (D3) | S90 |
| R0.7 | Unified ledger: consolidate runs, checks, gaps, incidents, rulings, model calls under one `run_id`-keyed table | LIVE | `script_execution_log`, ENH-71 `record_write`, ADR-029 ledger | One query traces a Home read to its capture run | **IN PROGRESS** — D7.3: `merdian_ro` read policies on `script_execution_log` + `merdian_parameters` (18:02 IST); D7.4: orchestrator writes one row per cycle (`6e13a7f`, R01-F1). D7.1/D7.5 DEPLOYED 2026-10-06 04:47–04:53 IST: columns + `v_run_trace` + `v_provenance_coverage_daily` (SQL), ExecutionLog + ingest/gamma/vol/cycle-history writer (`ca79717`); first row: `check_contracts_shadow.py` kind=run status=OK git_sha=ca79717. Remaining after: fold the ADR-029 file ledger | S90 |
| R0.8 | Instrument calendar in every contract (session hours, time zone, holidays per instrument) and the CLOSED status | SC | R0.5, `trading_calendar` (liveness-checked per ENH-133 §4) | A US holiday and the US overnight both show CLOSED, not STALE | **IN PROGRESS** — closed days are rows: belt 10-20/11-10 (SQL), seeder writes `is_open=false` for every closed day without overwriting (`82619f8`, 12 new of 14 over 45 days); CLOSED is a status in `cycle_health` (R1.2). Gate routing for `ingest_option_chain_local.py:293` and `capture_spot_1m_v2.py:265` DEPLOYED `ca79717` 2026-10-06 04:53 IST (`docs/research/s90_agentic/patches/patch_r08_gates.py`, tested: absent 10-02 → closed, gate failure → old fail-open path). Remaining: per-instrument calendars (Stage 3b); ~26 other inline gates (S68 count). Note: 2026-11-08 Muhurat written CLOSED per the engine (TD-S82-NEW-4); self-heals via merge when the engine is fixed | S90 |

**Stage 0 exit:** R0.2 ruled; R0.3 coverage 100 % for new rows; R0.4 accepted.

### Stage 1 — Ingest harness

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| R1.0 | Operational prerequisites: token propagation automated; process supervision | LIVE | TD-NEW-7, TD-NEW-L, ADR-018 | No manual `sed`; supervisor restarts a killed feed | NOT STARTED | |
| R1.1 | `data_contracts` registry seeded for core products (chain per symbol, spot, ticks, strike GEX, cycle history) | SC | R0.2 | Rows exist; runner reads them | **DRAFTED, not applied** — same file: `data_contracts` (14 products, numbers from P4 as A-11 proposals) + `cycle_health` sink; RLS on + `merdian_ro` policy per ADR-031 D6 | S90 |
| R1.2 | Generated-check runner: expected set, continuity (not first→last range), freshness **and movement**, depth, chain spot vs WebSocket spot | SC | TD-081, TD-S82-NEW-3, TD-S69-NEW-2, TD-S89-NEW-1 | Runs every cycle in shadow; writes `cycle_health` | **IN PROGRESS — in shadow.** `check_contracts_shadow.py` + `tests/` committed `f9d155d`; first `--write` 2026-10-05 17:45 IST (14 `cycle_health` rows, read back by `merdian_ro`); scheduled `*/5 3-10 * * 1-5`, timeout 240, commit `6f9403f`, live crontab = mirror. Live-read check as of 15:10 IST: chain/spot/gamma/strike GEX OK, WCB STALE, `gex_cycle_history` MISSING. History read (`--as-of`, runner v3.1 `b869894`, ~9 s/run): 10-02 all intraday CLOSED (calendar rule engine); 09-29 chain/spot/gamma/strike GEX OK; WCB STALE on 09-29 and 08-27 too (defect predates S90); 08-27 chain DEGRADED (1 expiry — second leg added later; flagged "contract applied retroactively": contracts are not versioned, PK = product). Exit needs a sample week with no false status. **`2e66d4f`:** the runner clamps freshness to the product’s own `data_contracts.session_end_ist` (spot **15:15**), which removes the false MISSING at 15:20 / 15:25 that replay found — ruling **S90-L** | S90 |
| R1.3 | Write-and-flag `cycle_health` per symbol per cycle; explicit MISSING rows for gaps | SC | ADR-030 | No silent gaps in a sample week | NOT STARTED | |
| R1.4 | Failure ladder: bounded retry inside the cycle window, parallel-endpoint probe, failover hook (used in Stage 3) | LIVE | §5.1 | Ladder exercised on a seeded failure | NOT STARTED | |
| R1.5 | Alert classes and an SLO per product; deduplicated, one incident per root cause | SC | ADR-017 P3 | Two weeks of SLO reporting | **IN PROGRESS** — views `v_cycle_health_daily` (status mix, `slo_ok_pct` excl. CLOSED, minutes not OK, latest reason) and `v_run_ledger_daily` (runs/failed/contract missed/latest error per script), security_invoker, `merdian_ro` only (2026-10-05 20:18 IST). First read surfaced today's real failures: option-chain ingest 4 (incl. `TOKEN_EXPIRED` Dhan 401), basis context 17, breadth-from-ticks 41 skips. SLO clock starts 2026-10-06 | S90 |
| R1.6 | Loop D: seeded bad days (10-02 holiday, a dropped-cycle day, a depth-1 day, a truncated tail like 08-20) | OFF | AC29-2 style | Every check has fired on its fixture | **IN PROGRESS** — fired on real days via `--as-of`: CLOSED (10-02), STALE/movement (WCB), DEGRADED/shape (08-27 chain), MISSING/presence (`gex_cycle_history` pre-apply), UNKNOWN (latest-only in the past); fixtures for these days frozen (R2.1). **Now run against the fixture files too:** `tests/replay/test_replay_seeded.py` (`a80176e`) seeds defects into golden 2026-10-01 SENSEX and asserts each is caught — frozen chain → **STALE** (plus lineage), dropped gamma cycles → **MISSING**, a second expiry → **DEGRADED**, a closed day → **CLOSED**, the clean day → **all OK**. **Still owed:** a truncated tail (the 08-20 shape), a depth-1 day, a dropped cycle mid-session, and spot death at 15:09 → MISSING | S90 |
| R1.7 | Status on Home (per symbol: OK / DEGRADED / STALE / MISSING, since when) | LIVE | ADR-017 | Visible; MISSING renders as "No read since hh:mm" | NOT STARTED | |
| R1.8 | Source tiers (core / context / research) in the contract, with an SLO per tier; a Tier 2 failure drops its context line and never degrades the core read | SC | §5.3 | Seeded Tier 2 outage leaves the core read OK | NOT STARTED | |
| R1.10 | Scrip-map sync: after each 1st/15th `swap_dhan_scripmaster()`, match every active NSE `dhan_scrip_map` row to the master by symbol (segment E, any series); remap on one unambiguous match; a `gap` ledger row (ADR-031 D7) on zero or several; contract check: active map ids absent from the master = 0 | SC | DH-905, TD-S90-NEW-1, R01-F12 | Two reloads pass with 0 unmapped and no silent keep | **NOT STARTED** — by-hand cure done 2026-10-05/06: 28 remapped, 4 deactivated, 0 unmapped (`docs/research/s90_agentic/DH-905_scrip_map_remap_S90.md`, `sql/2026-10-06_s90_dh905_scrip_map_remap.sql`) | S90 |
| R1.9 | Capacity budget: rows/day and storage growth per source, cycle compute time against the 5-minute window, box headroom | RO | `inventory.md` §4, jobid 19 | Budget table; every onboarding states its cost against it | IN PROGRESS — baseline in R0.1 §7 + P4: DB 35 GB, OCS 2.2 GB (+871 MB in 12 days, retention off), ~80 k OCS rows/symbol/day, 80–84 cycles/day; box disk 26 %, 1.46 GB RAM available; `market_ticks` holds one day | S90 |

**Stage 1 exit:** every check proven on its fixture; two weeks of SLO reporting; status visible on Home.

### Stage 2 — Compute harness (~~parity closes here~~ — **amended S92-A**: parity closes on ADR-025 D1 + the P6 render pass; R2.4 stays in parity; R2.2/R2.3/R2.5/R2.6 post-parity — `docs/research/s92_parity/rulings_s92.md`, ADR-025 Amendment C1)

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| R2.1 | Golden days frozen (10-01 SENSEX, 09-29 NIFTY, 08-27, a holiday), with a diff run on every deploy | OFF | Testing Protocol Gate 4 | Diff runs in the deploy path; green | **IN PROGRESS** — golden day #1 (10-01 SENSEX) designed: `docs/research/s90_agentic/R2.1_golden_day_1_design_S90.md`; **frozen 2026-10-05 17:26 IST**: 5 relations (chain 31,914 rows), 3.6 MB, `MANIFEST.sha256`, at `~/meridian-cc/tests/golden/2026-10-01_SENSEX/`; replay SQL re-run byte-identical to S89 (deterministic). committed **`37e9174`** (`~/meridian-cc` → origin/main; 18 files incl. `.gitignore` negation for `tests/golden/**/*.csv|*.txt`). **golden days #2–#6 frozen `e528a8d`** (09-29 NIFTY, 08-27 NIFTY/SENSEX, 10-02 NIFTY/SENSEX holiday): 6 fixtures, 20 MB. **Replay harness v0 (`a80176e`):** `tests/replay/replay_contracts.py --check` replays the contract runner at every 5-minute cycle of all six golden days against pinned statuses — combined `sha256 abdd2b16…` (`cat tests/replay/expected/*.statuses.csv | sha256sum`, recomputed 2026-10-07 and matching), **re-pinned at `2e66d4f` with exactly 8 cells MISSING → OK** (4 open days × the 15:20 / 15:25 slots) — and `tests/run_offline.sh` runs **6 suites** with no database and no network. **Still NOT a hard deploy gate** | S90 |
| R2.2 | Invariants: shares sum to 1, leader = 100 %, HHI ∈ [1/n, 1], flip between sign-change strikes, put-call parity on chain prices | SC | §6 | Invariant table populated per cycle | **DONE as §2.1 P3** (P3a S95, P3b S97: `p3b_invariant_checks` per γ run, ENH-145); status lives in the P3 row | S92, S95, S97 |
| R2.3 | Independent recompute of key numbers (a second, simple implementation, e.g. the 10-01 replay SQL for the ladder) | SC | `ladder_replay_1001.sql` | Agreement report per cycle | **DONE as §2.1 P3** (I2 per-strike recompute from the chain, a third implementation beside the writer and P3a; P3b S97); status lives in the P3 row | S92, S95, S97 |
| R2.4 | Screenshot parity fixtures (~60), scored per field | OFF | ADR-025 D3 | Fixture score per field reported | **REPORTED 2026-10-09 (S92)** — 65 reference-dashboard screenshots inventoried, **40 scored fixtures**, 199 field scores, reference values read twice blind (186/199 identical); MERIDIAN side replayed as-of each anchor from `gex_strike_snapshots` / `gamma_metrics`. Pin = MERIDIAN leader or top-5 in 20/26; net GEX sign 17/21; HHI ≈2× in the reference (window denominator). `docs/research/s92_parity/r24/`. Reported, not gating (ADR-025 C1) | S92 |
| R2.5 | Input contracts per computed layer: NOT_COMPUTED with reason when inputs fail; status propagates down the lineage | LIVE | R0.5 | Seeded missing input → NOT_COMPUTED reaches Home | NOT STARTED — **POST-PARITY (S92-A)** | S92 |
| R2.6 | Purity: remove wall-clock time and latest-only reads from compute paths; `as_of` on every read function | LIVE | ENH-134 | One past day replays bit-for-bit | NOT STARTED — **POST-PARITY (S92-A)** | S92 |
| R2.7 | Tick freeze: copy `market_ticks` to fixtures before the hourly prune, so tick-based writers (WCB, breadth) can be tested and replayed after the close | SC | R1.9, R2.6, TD-S90-NEW-4 | A day of ticks on disk; a tick-based writer replays from them | **IN PROGRESS** — `scripts/freeze_market_ticks.sh` deployed `47c795c` then `8f0007f`: cron `*/5 3-10 * * 1-5` through `bin/roq.sh` to `~/merdian_fixtures/ticks/<IST date>/ticks_<HHMM>_<HHMM>.csv.gz`, **10-day retention**, `gap=1` logged when the window has to be clipped. Cadence set by measurement: **353k rows / 8 MB per 15 min at the open, ~20 s of a 30 s statement timeout**, so 15 minutes was cut to 5. **Names the purge TD-S90-NEW-4 asked for: `pg_cron` jobid 46 deletes `market_ticks` older than 1 hour.** **Nothing consumes the frozen ticks yet** | S90 |

**Stage 2 exit:** golden days green on every deploy; parity fixture scores reported; one past day replays exactly. ~~**Parity closes here.**~~ **Amended S92-A (2026-10-08): parity no longer closes at this exit** — only R2.4 remains a parity item; the rest of Stage 2 is post-parity and paused with the harness work until parity closes.

### Stage 3 — Redundancy and history hygiene (post-parity; parallel with Stage 4) — **ON HOLD (S99-D, 2026-10-24)**

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| R3.1 | Verify Kite BFO coverage and per-connection instrument limits for the SENSEX chain (~400 contracts per expiry) | RO | — | Written finding | NOT STARTED | |
| R3.2 | Second live chain per symbol from the other broker, hot standby, in shadow | SC | R1.0, R1.4 | Both feeds writing, source recorded | NOT STARTED | |
| R3.3 | One in-house IV and Greeks engine applied to both feeds | SC | — | Matches the primary's Greeks within band on golden days | NOT STARTED | |
| R3.4 | Reconciliation period: leader, top-5, HHI, flip agreement per cycle | SC | Loop B | N weeks within bands | NOT STARTED | |
| R3.5 | Failover enabled per symbol per cycle by health score; never mix sources within one cycle's chain | LIVE | R1.4 | Rehearsed on a seeded outage | NOT STARTED | |
| R3.6 | End-of-day bhavcopy OI reconciliation | SC | Loop B | Daily report | NOT STARTED | |
| R3.7 | Score every historical day; quarantine the bad ones before any base rate is built | OFF | R1.2 runner on history | Quarantine list stamped | NOT STARTED | |

**Stage 3 exit:** feeds agree within bands for N weeks; failover rehearsed; quarantine list stamped.

### Stage 3b — Global context sources (post-parity; after R0.8, R1.8, R1.9) — **ON HOLD (S99-D, 2026-10-24)**

Scope as stated by the operator: SPX, crude, US 10Y and US 30Y, **as context to the Indian market**, not as traded instruments. Each goes through the onboarding checklist (§5.3).

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| R3.8 | Onboarding cards for SPX, crude, US 10Y, US 30Y (purpose, tier, calendar, vendor, licence, capacity, assumption card) | RO | §5.3 | Four cards ruled (A-12) | NOT STARTED | |
| R3.9 | Find and qualify a reliable source for each (existing brokers are not assumed to carry them): uptime record, revision behaviour of prints, latency, licence terms and cost; shadow period proves it | RO | — | Written finding | NOT STARTED | |
| R3.10 | Capture in shadow as Tier 2, with CLOSED handling and as-of joins to the Indian cycle | SC | R0.8, R1.8 | N weeks of capture; no false STALE on US closures | NOT STARTED | |
| R3.11 | Context features as-of each Indian cycle (e.g. SPX and crude change since the previous Indian close; yield change overnight; age of each print) | SC | §8.5 | Features in history with their print age | NOT STARTED | |
| R3.12 | Event study: does the context change what core events mean (e.g. a pin or flip-crossing outcome after a large overnight SPX move)? | OFF | R4.6, §8.5 | Result with n; candidate dimension admitted or DECLINED-ON-EVIDENCE | NOT STARTED | |

### Stage 4 — Assumption harness and facts layer — **ON HOLD (S99-D, 2026-10-24)**

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| R4.1 | Assumption test cards for each testable register row (claim, metric, pass band, cadence, data) | RO | Assumption Register | Cards written for the starter set (§7.2) | NOT STARTED | |
| R4.2 | `assumption_checks` table and scheduled runner; out-of-band → register row UNDER REVIEW | SC | R0.7 | One full monthly cycle run | NOT STARTED | |
| R4.3 | Calibration of each read word (LOCKED, accelerating, …) against outcomes | OFF | §6 | Reliability per state reported | NOT STARTED | |
| R4.4 | State vector v1 (8 dimensions, measured bands) | SC | §8.1 | Computed per cycle into history | NOT STARTED | |
| R4.5 | Event grammar v1 stamped; event detector | SC | §8.2 | Events table populated | NOT STARTED | |
| R4.6 | Event study on clean history: outcomes with n and interval; "insufficient history" below minimum n | OFF | §8.3, R3.7 | Base-rate tables, rebuilt nightly as-of | NOT STARTED | |
| R4.7 | Facts payload schema v1 — the one object Home, the access layer and agents all consume | LIVE | §9.3 | Schema stamped; Home reads it | NOT STARTED | |

**Stage 4 exit:** base rates exist with n and intervals; assumption monitor has run one monthly cycle; payload schema stamped.

### Stage 5 — Agent harness, then agents in order of risk — **ON HOLD (S99-D, 2026-10-24)**

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| R5.1 | Access layer: Python library with the six read functions, then MCP v1 as a thin wrapper | SC | §9.1 | Both return identical results on golden days | NOT STARTED | |
| R5.2 | Model adapter (own internal message/tool format, one translator per vendor) with ADR-029 routing | OFF | ADR-029 | Two vendors callable through one interface | NOT STARTED | |
| R5.3 | Context recipes as versioned code; stable prefix for caching; budget per section; hashed facts payload | OFF | R4.7 | Recipes in repo; cache hit rate reported | NOT STARTED | |
| R5.4 | Loop controller: explicit states, step/token/time budgets, stop conditions, checkpoint, human gates | OFF | — | Budgets enforced in a forced-overrun test | NOT STARTED | |
| R5.5 | Eval sets from golden days, per agent; template fallback for every model output | OFF | R2.1 | Eval suite runs on any prompt or model change | NOT STARTED | |
| R5.6 | Agent 1 — Watcher (off-box): triage, TD-class match, daily integrity note | SC | R1.*, R0.7 | Triage matches the operator's over N incidents | NOT STARTED | |
| R5.7 | Agent 2 — Commentator: lines 1–3 from templates live; line 4 conditional; model synthesis in shadow | LIVE | §9.2 | Checker pass for N sessions before synthesis is shown | NOT STARTED | |
| R5.8 | Agent 3 — Reviewer (weekly): wrong commentaries (confident-wrong first), clustered; PROPOSED amendments | OFF | R5.7 running | First weekly review delivered | NOT STARTED | |
| R5.9 | Swap test: a second model passes the commentator's eval set | OFF | R5.2, R5.5 | Pass recorded | NOT STARTED | |

**Stage 5 exit:** watcher matches operator triage over N incidents; commentary passes the checker for N sessions; swap test passed.

### Stage 6 — Paper book, then the advisor — **ON HOLD (S99-D, 2026-10-24)**

| ID | Item | Risk | Builds on / absorbs | Exit evidence | Status | Session |
|---|---|---|---|---|---|---|
| R6.1 | Paper-trading pass criteria per playbook, set before the first paper week | RO | ruling A-6 | Stamped | NOT STARTED | |
| R6.2 | Paper book with plan-at-entry; fills at bid/ask + 0.15 % slippage | SC | ENH-48 | First paper week logged | NOT STARTED | |
| R6.3 | Agent 4 — Advisor in paper: hold / reduce / roll / hedge against the entry plan | SC | R6.2 | Advice logged against every paper position | NOT STARTED | |
| R6.4 | Live, manual execution, advisor advising | LIVE | N ≥ 30 per playbook (ADR-009) | Ruling | NOT STARTED | |

**Stage 6 exit:** per playbook, N ≥ 30 paper trades judged against the pre-set criteria. Automation (ENH-50) only by separate ADR, if ever.

---

## 4. Scoreboard (measurable, not claimed)

Each metric is a query. "Proposed target" values are proposals for ruling A-11.

| Stage | Metric | Definition | Proposed target | Current |
|---|---|---|---|---|
| 0 | Provenance coverage | % of new capture/compute rows with `run_id` + `source` + `code_sha` | 100 % | — |
| 0 | Traceability | A sampled Home read traces to its capture run via the ledger | yes | — |
| 1 | Ingest SLO | % of in-session cycles OK, per symbol per product | ≥ 98 % | — |
| 1 | Checks proven | Checks that have fired on a seeded fixture / total checks | 100 % | — |
| 1 | Silent gaps | Cycles with no row and no MISSING marker | 0 | — |
| 1 | Detection latency | Minutes from failure to status change | ≤ 1 cycle | — |
| 1 | SLO by tier | % of expected cycles OK, per tier (CLOSED excluded from the denominator) | Tier 1 ≥ 98 %; Tier 2 ≥ 95 % | — |
| 1 | Capacity headroom | Storage growth/month; p95 cycle compute time / 5-minute window; free RAM | compute ≤ 50 % of window | 2026-10-05: disk 7.3/29 G; RAM 1.46 G avail; compute time not yet measured |
| 2 | Golden-day diff | Fields differing from frozen expected | 0 (or explained) | — |
| 2 | Parity fixture agreement | % of fixture fields within tolerance | set at A-5 | — |
| 2 | Replay exactness | Past days replayed bit-for-bit / attempted | 100 % | — |
| 3 | Cross-feed agreement | % of cycles where leader and top-5 set match across brokers | ≥ 95 % | — |
| 3 | History cleanliness | Days scored; days quarantined | all scored | — |
| 4 | Assumption coverage | Testable register rows with a test card / testable rows | rising | — |
| 4 | Base-rate depth | Events with n ≥ minimum | rising | — |
| 4 | Calibration | Reliability per read word | per word | — |
| 5 | Model cost/day | From the ledger | budget set at A-11 | — |
| 5 | Model calls/day/symbol | Commentary synthesis calls | ~20–40 | — |
| 5 | Deterministic share | Home lines produced without a model | ≥ 75 % | — |
| 5 | Checker pass rate | Model commentaries passing the facts checker | ≥ 99 % | — |
| 5 | Swap test | Second model passes the eval set | pass | — |
| 6 | Plan adherence | Paper trades with a complete plan at entry | 100 % | — |
| 6 | N per playbook | Paper trades per playbook | ≥ 30 | — |

---

## 5. Ingest harness — design

### 5.1 When something hasn't come down

**Rule:** degrade the read, never fake it.

Every cycle, per symbol per source, gets one status:

| Status | Meaning |
|---|---|
| **OK** | Complete and fresh from the primary source |
| **DEGRADED** | Partial, or answered by the secondary source; usable with a flag |
| **STALE** | Rows arrived but nothing moved (10-02) |
| **MISSING** | Nothing usable; an explicit gap row is written |
| **CLOSED** | The source's own session is shut (US overnight, a US holiday, MCX closed); expected, not a failure |

**Failure ladder:**
1. **Detect inside the cycle:** expected set, continuity, freshness and movement.
2. **Retry with a time limit,** inside the cycle window only. Probe the parallel endpoint before concluding the vendor is down (failures are per endpoint, not per vendor — S22).
3. **Fail over** to the secondary source if one exists; record which source answered and how many rows it returned (D.28.5).
4. **Otherwise write MISSING.** Each computed layer checks its own minimum inputs; Home shows "No read since hh:mm".
5. **Alert by class and persistence:**
   - one missed cycle is logged;
   - three in a row, or a failure at session open, pages;
   - auth or token failure pages immediately.
6. **Recover after the fact.** Backfill what is recoverable (spot and per-strike OHLC/OI from Kite), marked `source=backfill`. The Dhan full chain is not recoverable; that gap stays permanent and flagged.
7. **Log every gap** to the ledger; the watcher triages from it.

| Failure class | Detect | Immediate response | Recovery |
|---|---|---|---|
| Token or auth | 401/403; `profile()` pre-flight at 09:10 | Page now; switch to secondary | TD-NEW-7 |
| Endpoint 429/500 | Status codes, latency | Bounded retry, then secondary | Backfill if possible |
| Partial chain | Expected-set check | DEGRADED; layers check their own minimums | — |
| Stale but plausible | Spot or OI not moving vs WebSocket | STALE; no read | TD-S89-NEW-1 class |
| Process dead | Supervisor, heartbeat | Restart once; page on second failure | TD-NEW-L |
| Box down | Off-box heartbeat | Page | Disk-full runbook class |

### 5.2 Redundancy through Kite

Today each symbol's chain has one source: Dhan for SENSEX options and spot, Zerodha for the NIFTY chain and breadth. Kite backfill is the recovery path, but cannot rebuild a full chain.

- **Hot standby, not cold.** Both feeds run all the time. Cold failover fails when needed; hot standby also gives Loop B every cycle.
- **In-house IV and Greeks** applied to both feeds (Kite supplies prices, OI and depth, not Greeks). Removes dependence on Dhan's Greeks and makes the feeds comparable.
- **Never mix sources within one cycle's chain.** Pick per cycle per symbol by health score; record the choice.
- **Prove before trusting:** side-by-side reconciliation for N weeks, then failover.
- **Independence over a second broker:** two brokers on one box and one token chain share failure modes (09-22 disk-full lockout). TD-NEW-7 and TD-NEW-L come first.
- **First check:** Kite BFO coverage and per-connection instrument limits (R3.1). Unverified.

### 5.3 Adding a source — onboarding checklist

No source is ingested until its card is complete and ruled. The card:

| Field | Question |
|---|---|
| Purpose and consumer | Which layer, state-vector dimension or commentary line uses it, and what hypothesis does it serve? No consumer, no ingestion |
| Tier | 1 core · 2 context · 3 research |
| Calendar | Session hours, time zone, holidays; what CLOSED means for it |
| Cadence | Tick, 1-minute, 5-minute, daily print; how it joins the 5-minute Indian cycle (as-of, with print age) |
| Source reliability, vendor and licence | Uptime record, how often prints are revised, latency, cost, terms, rate limits; existing broker or new account |
| Capacity cost | Rows/day, storage/month, compute per cycle, against R1.9 |
| Failure behaviour | What the read does without it (Tier 2: drop the context line only) |
| Assumption card | The relationship it assumes (e.g. SPX overnight gap affects the Indian open) and how often that is re-tested |
| Shadow period | How long it is captured before any consumer may read it |

**Global context set (operator's current scope).** SPX, crude, US 10Y and US 30Y as **Tier 2 context** for the Indian market:
- **Calendars:** US cash and bond markets are mostly shut during the Indian session; equity index futures and crude trade most of the day. The card for each must say which instrument is captured (cash index, future or yield) because that decides when it is CLOSED.
- **Relevant reading:** mostly the overnight change into 09:15 IST and any move during the Indian afternoon, as-of each cycle with the age of the last print shown.
- **Source:** a reliable source has to be found; the existing brokers are not assumed to carry these. R3.9 qualifies candidates on uptime, print revisions, latency, licence and cost.
- **Use on Home:** at most one context line ("Overnight: SPX −1.2 %, crude +2.0 %, US 10Y +8 bp"), shown only if its print is fresh, and never mixed into the core read until R3.12 admits it.


### 5.4 Purchased historic data

"Training" here means deepening the evidence, not fine-tuning a model: more history behind the base rates (R4.6), the assumption checks (R4.2), calibration (R4.3), the playbook replay tests (R1–R8) and the agents' eval sets (R5.5). Fine-tuning a model would cut against LLM independence and is not planned. A purchased dataset is onboarded like any source (§5.3) as Tier 3 research, with these additions:

| Requirement | Why |
|---|---|
| **One import path, same normalisation as live**, provenance `source=<vendor>` | Base rates must not mix two definitions of the same number |
| **Greeks recomputed by the in-house engine (R3.3)** | Vendor history may lack Greeks or compute them differently |
| **Overlap reconciliation** against MERIDIAN's own captured days (`option_chain_snapshots` from 2026-08-24, `gex_strike_snapshots` from 2026-05-25) before any use | Proves the vendor's numbers match ours where both exist |
| **Scored and quarantined (R3.7)** like our own history | Bad vendor days must not enter the event study |
| **Train / holdout split by date, stamped before the first query** (ADR-009) | Prevents learning from the window used to judge |
| **Storage decided against R1.9** — likely off the box (separate database or files) | Years of chain history will not fit a t3.small |
| **Licence terms** recorded on the onboarding card | Some vendors restrict derived use |

Earliest sensible point: after Stage 2 (replay is exact) and R3.3 (own Greeks), so imported history goes through the same verified path as live data.
---

## 6. Compute harness — design

Data can be right and the read wrong.

1. **Golden days.** Frozen inputs, frozen expected outputs, diff on every change.
2. **Invariants.** Shares sum to 1; leader = 100 %; HHI ∈ [1/n, 1]; the flip lies between the strikes where the cumulative sign changes; put-call parity on chain prices catches bad LTPs before they reach IV.
3. **Independent recompute.** A second, simpler implementation of key numbers. If two independent paths disagree, one is wrong.
4. **Parity fixtures.** The ~60 parity-target screenshots carry numbers at known timestamps; score agreement per field. 10-01 is the first entry: leader and top-5 set match; 72,500 is +21–29 off.
5. **Input contracts and status propagation.** NOT_COMPUTED with reason, carried to Home.
6. **Purity.** `as_of` everywhere; no wall-clock time inside compute.
7. **Calibration** (Stage 4): does each read word mean what it says? Nightly scoring per state.
8. **Commentary checker** (Stage 5): every number in a commentary must appear in its facts payload; states must match; certainty words blocked; on failure the template shows instead.

---

## 7. Assumption harness — design

### 7.1 Three different questions

1. **Implementation:** does the code do what the spec says? (Compute harness.)
2. **Validity:** is the spec true of the market?
3. **Drift:** is it still true?

The Assumption Register is the right vehicle (LIVE / VALIDATED / REFUTED, Measure → Validate → Shadow → Promote). The gap is that rows are re-tested only when a session happens to. D.27.3 already rejected the idea that an external change surfaces through the system's own telemetry.

### 7.2 Starter test cards

| Assumption | Test | Cadence |
|---|---|---|
| Dealer sign convention (long calls, short puts) | Positive net-γ regime shows lower realised range than negative | Monthly |
| Pin states mean something (D.10.7, LIVE) | Settle distance to pin vs a random nearby strike | Monthly |
| Measured bands (ADR-016) | Recompute percentiles; flag distribution shift | Monthly |
| Time boost `2.53·T^−0.5` | Refit; new coefficient inside old interval? | Monthly |
| Lot size, expiry weekday, contract specs | Exchange instrument master | Daily |
| IV model inputs (rate, dividend) | Synthetic forward vs futures | Daily |
| Parity agreement | Fixture scores per field | Per new screenshot |

### 7.3 Guards against curve-fitting

- **Re-tuning is not refuting.** Re-tuning a parameter is routine and pre-registered; refuting a structural assumption needs an ADR.
- **Never re-tune on the data that raised the flag.** Confirm on a later held-out window.

---

## 8. Facts layer — the change engine

### 8.1 State vector (8 dimensions, our measured bands, versioned)

| # | Dimension | From |
|---|---|---|
| 1 | Regime: net γ band and its trend | L6, L14 |
| 2 | Location: spot vs flip, walls, pin band | L3, L4/L5, L1/L2 |
| 3 | Pin: state, held-for, runner-up margin | L2, L12, ENH-133 |
| 4 | Concentration: HHI vs time-of-day percentile | L12, ENH-133 |
| 5 | Flow: today vs book sign; call writing/covering, put writing/unwinding as a share of standing OI | L13, D-4 |
| 6 | Vol: ATM IV change, realised/implied ratio | L9/L10 |
| 7 | Clock: DTE, time bucket (pre-10:00, mid-session, post-14:30, post-15:15) | calendar |
| 8 | Momentum: spot move over 15/30 minutes in σ units | spot |

### 8.2 Event grammar (about 15 transitions, defined in code, versioned)

- leader step (count and direction within N minutes);
- leader turns net SHORT/LONG;
- pin state change;
- HHI band crossing;
- spot crosses the flip or a wall;
- put wall ≈ flip;
- flow sign flips and persists ≥ 3 cycles;
- covering ≥ x % of book;
- put writing ≥ y % of book;
- covering + put writing + call writing ≈ 0 in the same cycle (the 10-01 reversal signature);
- put long-unwind without put writing (the 10-01 false floor);
- auction window entered.

### 8.3 Event study

For each event × context (regime, DTE, time bucket): forward return over 15/30/60 minutes and to the close; realised range; continuation probability; adverse excursion. All with n and an interval. Below minimum n: "insufficient history" (ADR-020). Rebuilt nightly as-of, on quarantine-clean history only (R3.7).

| Source | Window | Supports |
|---|---|---|
| `hist_gamma_metrics` | 1-minute, both symbols, 2025-04 → 2026-03 | gamma-based events |
| `gex_strike_snapshots` | per-strike, from 2026-05-25 | ladder, pin, concentration |
| `option_chain_snapshots` | from 2026-08-24 | flow and classification |
| `gex_cycle_history` | from 2026-10-05, indefinite | everything, going forward |

### 8.4 Playbook map v1 (hand-written, stamped, tested through R1–R8)

| Conditions | Structure |
|---|---|
| Pin LOCKED/STABLE, HHI balanced or higher, positive γ, mid-session | Pin-centred (fly/straddle at pin) |
| Walls intact, positive γ, T−5…T−2 | Wall shorts |
| Dispersed / NO PIN | Defined-risk or ratio |
| Negative γ, leader SHORT, accelerating, flow SAME | Trend-follow or stand aside |
| Post-15:15 | No new risk |

A learned tree may propose splits later; it must validate walk-forward and pass ruling. Never self-modifying live.

### 8.5 Extension point: new dimensions enter only through the event study

The eight dimensions are not closed, but a ninth (for example *global context*: overnight SPX, crude and yield moves) is admitted only when the event study shows it changes the outcome of existing events, with n and an interval, on a held-out window. Until then a context source may appear on Home as a labelled context line, never inside the state, the events, the base rates or the playbook match. A dimension that does not earn its place is recorded DECLINED-ON-EVIDENCE, as the pressure leg was (D-5a).

---

## 9. Agent harness and agents

### 9.1 Access layer

Six read-only functions, first as a Python library, then wrapped as MCP v1 (stdio on the box). Each wraps a view; no free-form SQL tool; no order tool.

| Function | Returns |
|---|---|
| `get_state(symbol, as_of)` | State vector for one cycle |
| `get_ladder(symbol, as_of, n)` | Leader, top-n, % of leader, net Γ sign |
| `get_events(symbol, from, to)` | Detected events |
| `get_base_rates(event, context)` | Event-study outcomes with n and interval |
| `get_health(window)` | Status and integrity flags |
| `get_paper_book()` | Paper positions, Greeks, P&L vs plan |

MCP matters for consistency and agent access, not throughput. Remote access (authenticated HTTPS) is a separate decision (A-3). RAM budget: t3.small, ~1.1 GB free, no swap.

### 9.2 Commentary box on Home

Four lines per symbol, refreshed per cycle or on event:
1. **State** — template from the state vector.
2. **What changed** — events in the last 15 minutes, ranked by historical consequence.
3. **What it has meant** — base rate with n, or "insufficient history".
4. **Playbook match** — "conditions match …", conditional, not an instruction. A verb only after ruling A-2 and only for playbooks that passed their R-test. In paper mode, a labelled paper action.

Optional model synthesis (2–3 sentences) on events only (~20–40 calls/day/symbol), shadow first, logged with facts hash and model id.

**What it would have said on 2026-10-01** (replay CSV; thresholds chosen after looking; base rates pending):
- **12:25** — Accelerating. Spot 72,118, −260 in 25 min. Pin broken: leader 72,400 → 72,300 → 72,000; new leader net SHORT. Calls written every cycle since 12:10, no put writing. *Continuation; no stop signal.*
- **12:40** — Pause, not a floor. Flow turned positive at 12:35, but mostly put holders booking (3.7M long-unwind against 0.41M put writing). *Support needs put writing.*
- **13:00** — Selling slowing. Spot 71,591, −786 since 12:00. Flow positive three cycles while price fell; covering 1.2M; HHI 0.058, the day's low. *Stop adding calls; not a reversal.*
- **13:10** — First defence: put writing 1.7M then 3.7M after a +152 bounce. *Not yet a turn.*
- **13:45** — Grinding lower. Defence failed; calls written on most cycles (2.0–2.4M at 13:25–13:30 and 13:45); leader 71,700 → 71,500 (SHORT). *Risk for call sellers is a squeeze.*
- **14:10** — Reversal conditions. After the 71,302 low: call writing ~0, covering 1.1M and put writing 2.4M in one cycle; confirmed 14:15 (1.7M + 4.2M). *Exit or hedge short calls.*
- **14:35** — Leader back to 72,000; covering 5.0M, the day's largest.
- **15:10** — Pin locking at 72,000: runner-up 62 %, 46 % at 15:15, 40 % at 15:20; HHI 0.121 rising to 0.198 by 15:20. Auction from 15:15. *Readings after 15:15 are unreliable.*

### 9.3 Facts payload

One versioned JSON schema per symbol per cycle: state vector, last-15-minute events, base rates with n, status and flags, paper position and its plan when open. Home, the access layer, the commentator and the advisor all consume it. Hashed and logged with every model output.

### 9.4 Agents

| # | Agent | Trigger | Reads | Writes | Order rationale |
|---|---|---|---|---|---|
| 1 | Watcher (off-box) | every 15 min + end of day | health, ledger, registers | integrity note, draft TD entries | Read-only, judged against operator triage |
| 2 | Commentator | on event | facts payload | `commentary_log` (shadow first) | Templates carry it; model is optional |
| 3 | Reviewer | weekly | labelled commentaries, paper trades, operator notes | PROPOSED amendments | Needs labels to exist |
| 4 | Advisor | per cycle with a position open | position plan + events | paper advice | Highest stakes |

Agents never write production, never change a rule, never place an order. They do not converse with each other.

### 9.5 Self-learning, defined so it cannot overfit

1. **Every cycle:** detect and say (templates), facts hashed and logged.
2. **Nightly, automatic:** label each commentary and event with what happened next; rebuild base rates as-of; run due assumption checks.
3. **Weekly, reviewer agent:** wrong commentaries (confident-wrong first), clustered; operator's paper trades and deviation notes as labels; PROPOSED amendments.
4. **Operator:** stamps or rejects. The only path by which a threshold, event or playbook changes.

### 9.6 Cost and LLM independence, concretely

- **Cost:** deterministic first; model on events only; routing (cheap model for triage, strong for synthesis); stable prompt prefix for caching; compact payloads; every call in the ledger with tokens and cost; a daily budget with an alert.
- **Independence:** own thin adapter (no heavy agent framework); capability matrix per model; pinned versions; eval set per agent; template fallback; **no rules in prompts**, so a model swap cannot silently change strategy; the swap test (R5.9) as an exit criterion.

### 9.7 Anti-patterns

- Framework-first agent build.
- Hand-written checks per table.
- Silent fallbacks.
- A harness sharing the patient's host or token chain.
- Logs without correlation IDs.
- Non-determinism in compute (wall-clock time, unordered reads, "latest" views).
- Rules living in prompts.

---

## 10. Rulings owed (none chosen here)

| # | Ruling |
|---|---|
| A-1 | Adopt "deterministic core, model at the edges, rules change only by ruling" as an ADR |
| A-2 | Reconcile parity plan §1.3 (descriptive read) with ADR-017 P2 ("what to do now"): when line 4 may carry a verb |
| A-3 | Access layer: MCP v1 scope (six read-only functions) and hosting (stdio on the box vs authenticated remote) |
| A-4 | Watcher agent host (independent of the box) and paging policy |
| A-5 | Admit Stages 0–2 (spine, ingest harness, compute harness incl. parity fixtures) into parity scope |
| A-6 | Paper-trading pass criteria per playbook, set before the first paper week |
| A-7 | Item 6 of the original sketch was blank — intended content? |
| A-8 | Spine ADR (R0.2): contracts, status vocabulary, provenance, ledger consolidation |
| A-9 | Kite redundancy scope (R3.*): hot standby per symbol, in-house Greeks, reconciliation length |
| A-10 | Assumption monitor: starter test cards and cadence (§7.2) |
| A-11 | Scoreboard targets (§4) and each stage's N values |
| A-12 | Global context set (SPX, crude, US 10Y, US 30Y) as Tier 2 context: approve the four onboarding cards (R3.8) |
| A-13 | Adopt §11's risk classes and controls as standing rules for this roadmap |

---

## 11. Building on a live system — risks and controls

### 11.1 Risk register

| # | Danger | How it would happen here | Mitigation |
|---|---|---|---|
| 1 | **Breaking capture; permanent data loss** | An ingest change fails mid-session; the Dhan full chain cannot be backfilled | Harness runs beside capture, never inside it. Capture changes only as additive, interlocked steps (ADR-025 A1 constant pattern). Deploy after 16:00 IST, `--ff-only`, written rollback |
| 2 | **Starving the box** | Checks, history scoring or a second feed exhaust CPU, RAM or disk on a t3.small with ~1.1 GB free (09-22 disk-full lockout) | Capacity budget (R1.9) before adding load. Heavy jobs after the close or off-box. Timeouts on every job. Disk-growth alarm |
| 3 | **Migrations on hot tables** | A lock during the session; a new table without its `merdian_ro` policy reads silently empty, or is exposed (09-22 anon-privilege case) | Additive migrations only. Applied after the close. RLS policy in the same migration. Post-apply check: `merdian_ro` can read, anon cannot. **S90 evidence:** ENH-133 came up with RLS on and 0 policies though its DDL enables none — the Supabase SQL editor offered to enable RLS on the new table at run time and that option was taken. Only the post-apply check caught the mismatch. So every new-table DDL states its RLS intent explicitly (`ENABLE` + a `merdian_ro` policy, or `DISABLE`), the editor prompt is answered to match the DDL, and the post-apply check always runs |
| 4 | **A new write path hiding loss** | An upsert masks per-symbol write loss (TD-S54-NEW-1) | Per-symbol coverage audit after every cutover |
| 5 | **The harness misleading** | False alarms train the operator to ignore alerts; checks that cannot fail make everything green | Shadow and report-only first. Loop D proof per check. SLO-based alerting |
| 6 | **The harness failing silently** | The checker dies and the last status shown is OK; a gate fails open (D.26.1) | Checker heartbeat watched off-box. No fresh status → **UNKNOWN**, never OK. Gates fail to absent |
| 7 | **Home changing mid-session** | A new status or commentary line is misread during a live trade | New Home elements launch labelled "shadow", deployed after the close, beside the existing view. Advice stays in paper |
| 8 | **Kite standby disturbing breadth** | The Zerodha WebSocket already subscribes ~2,200 instruments; adding the SENSEX chain may hit per-connection limits | R3.1 verifies limits first. Separate connection and supervisor. Shadow first |
| 9 | **Credentials and attack surface** | New vendors, agent host, MCP server, more tokens | Read-only role everywhere. Separate credentials per agent host. No secrets in agent context. No order tool, ever. Vendor security in the onboarding card |
| 10 | **Agents** | Injected text through data or docs; runaway cost; writing where they shouldn't | Read-only agents. All data treated as untrusted. Daily cost cap with alert. Every call in the ledger |
| 11 | **Corrupting history** | Quarantining good days, or fixing history in place | Never mutate stored history. Quarantine is a reversible, stamped flag table with a reason |
| 12 | **Parity slipping** | Roadmap work crowds out parity | Only Stages 0–2 inside parity (A-5). Everything else waits for parity close |
| 13 | **"Done" without evidence** | A row reads SHIPPED while the artefact is absent (ENH-83 write-path gap) | No DONE without linked evidence |
| 14 | **No way back** | A live change misbehaves and cannot be switched off | Every LIVE item names its off switch and rollback before shipping. Safety interlocks use a code constant, not a database parameter, because a parameter read can fail open |

### 11.2 Three rules that cover most of it

1. **Sidecar, not surgery.** New things run beside the live path until proven.
2. **Additive, after the close, reversible.** Every live change is additive, deployed after 16:00 IST, and has a named rollback.
3. **Unknown is not OK.** Every check and every new feed proves itself in shadow before anyone or anything reads it.

### 11.3 Controls by risk class

An item may start only when its class's controls are met. Each class includes the controls of the classes above it.

| Class | Controls |
|---|---|
| _Deploy timing (S90-J)_ | RO / OFF / SC changes and Marketview via staging deploy any time; only LIVE waits for the window |
| **RO** | Through `bin/roq.sh` (`merdian_ro`); bounded probes in market hours; no `.env` or credential read; nothing written to the live database |
| **OFF** | RO controls, plus: runs on copies or after the close; timeouts; writes only its own artefacts (docs, fixture files, its own tables) |
| **SC** | OFF controls, plus: new tables or processes only, live path untouched; additive migration with RLS policy in the same migration and post-apply read/anon check; capacity cost stated against R1.9; heartbeat; shadow before any consumer reads it; named off switch |
| **LIVE** | SC controls, plus: operator ruling before start; deploy only in the S90-J window (weekdays 16:30 → 07:45 IST, any time on weekends and holidays) by push and `git pull --ff-only` from the operator's terminal; never edit under `~/meridian-engine` directly; interlock constant where it gates capture; golden-day and seeded-day tests green before deploy; per-symbol coverage audit after cutover; written rollback |

---

## Change history

| Version | Date | Change |
|---|---|---|
| v1 | 2026-10-05 | Answer to the seven-point sketch: MCP, integrity loops, change engine, accuracy loops, commentary, paper trading, phases 0–4 |
| v2.16 | 2026-10-24 | **S98 + S99 close (run in S100):** §2.2 R2 + R21 PART DONE (`3706435`); R48, R49 added to B1 (S100-B); TD-S99-NEW-1 added to BS; "Pass-2 misses" row in B4; §2.1 P4 lost-session note. Rulings `docs/research/s92_parity/rulings_s98.md`, `rulings_s99.md`, `rulings_s100.md` |
| v2.15 | 2026-10-24 | **S99 one stream:** §2.2 single list (pass 1 S98-A + pass 2 S99-C, 154 open TDs homed, 46 closed), §2.3 retail scoping (S99-F); Stages 3–6 ON HOLD (S99-D); signal / ICT stream after agentic (S99-G). Rulings `docs/research/s92_parity/rulings_s99.md` |
| v2.14 | 2026-10-23 | **S97 close:** P7 DONE (live read 2026-10-12); P3b applied and read → **P3 DONE** (ENH-145); R2.2 / R2.3 rows point to P3. Rulings `docs/research/s92_parity/rulings_s97.md` |
| v2.13 | 2026-10-12 | **S96 close:** P7 BUILT AND LIVE (ENH-143, ENH-144; S96-A…G), D-4 DECLINED-ON-EVIDENCE (S96-I), DONE on the first market-hours read; P3 → P3b BUILT and tested (S96-H), apply owed. Rulings `docs/research/s92_parity/rulings_s96.md` |
| v2.12 | 2026-10-11 | **S95 close:** P3a DONE (P3b awaits approval); P5 DONE (ENH-142); P6 DONE incl. board and S\* (ENH-141); P7 unblocked; P8 re-scoped to dte 1 (S95-G). File moved to `docs/registers/` (S95-E) |
| v2.11 | 2026-10-10 | **S94 close:** P6 → IN PROGRESS, view LIVE and verified, ENH-140 filed, board read owed. P3a test committed, not run |
| v2.10 | 2026-10-10 | **S94, later:** P2 → DONE (REGIME-DEPENDENT), P1c → DONE (INCONCLUSIVE), P4 → PRE-REGISTERED/ACCRUING at dte 1, P3 → IN PROGRESS (P3a). **S94-G** releases P5/P6, holds P7 behind P6, flags P8 for re-scope; S94-H (S\* own view), S94-I (vendor delta) |
| v2.9 | 2026-10-10 | **S94:** §2.1 re-planned by ruling **S94-A** (discharges S93-B): order P2 → P4 → P1c → P3; P5/P6/P7 HOLD; P8 gated. **P1c** added (S94-B); P1b deferred (S94-C); board evidence note (S94-D). Rulings: `docs/research/s92_parity/rulings_s94.md` |
| v2.8 | 2026-10-07 | **AM-1 post-close delta, folded in at AM-2 / S91:** R0.3 per-leg ledger rows (`df80dec`), R1.2 per-product session end (`2e66d4f`, ruling **S90-L**), R1.6 seeded-defect tests against the fixtures (`a80176e`), R2.1 replay harness v0 + `tests/run_offline.sh` (`a80176e`, re-pinned at `2e66d4f`), **new R2.7 tick freeze** (`47c795c` / `8f0007f`, which answers TD-S90-NEW-4). Rulings **S90-K / -L / -M** recorded in `rulings_s90.md`; §11.3 S90-J line unchanged |
| v2.7 | 2026-10-06 | AM-1 doc-close: DH-905 cured by hand (R01-F12; series changes reissue Dhan IDs), R1.10 scrip-map sync added; tracker becomes the canonical progress record (hybrid close, Doc Protocol v5 DRAFT) |
| v2.6 | 2026-10-05 | R01-F10/F11 fixed: EOD sweep one full lap (`2de6282`), EOD dates in IST + one-time +1-day migration of `equity_eod`/`breadth_indicators_daily` (S90-H); DMAs rebuilt to 2026-10-01 |
| v2.5 | 2026-10-05 | S90 evening: rulings S90-C…G; R0.5/R1.1 applied; R1.2 in shadow (cron); ENH-133 writer + reconciler live; R0.7 D7.3/D7.4; golden days #1–#6; WCB writer fixed (S90-G) |
| v2.4 | 2026-10-05 | Tracker (S90): R0.1 DONE, R0.4 applied and accepted on the empty table (RLS defect found by the post-apply check and corrected), R1.9 baseline; R0.4 exit wording aligned to the applied DDL (`session_gate_state`) |
| v2.3 | 2026-10-05 | §5.4 purchased historic data: what "training" means here, import requirements, earliest point |
| v2.2 | 2026-10-05 | Risk register for building on a live system (§11): 14 risks with mitigations, three rules, controls by risk class; Risk column (RO / OFF / SC / LIVE) on every work item; go/no-go rule in §2; R3.9 reworded to finding and qualifying a reliable source; ruling A-13 |
| v2.1 | 2026-10-05 | Breadth and depth of ingestion: CLOSED status and instrument calendars (R0.8); source tiers and SLO per tier (R1.8); capacity budget (R1.9); onboarding checklist (§5.3); Stage 3b global context sources, SPX/crude/US 10Y/US 30Y as context (R3.8–R3.12); new dimensions only through the event study (§8.5); scoreboard rows; ruling A-12 |
| v2 | 2026-10-05 | Harness discussion folded in: principles; ingest, compute and assumption harnesses; Kite redundancy; agent harness; Stages 0–6 replace phases 0–4; work-item tracker; scoreboard; where to start; rulings A-8…A-11. 15:10 figures corrected from the replay CSV |
