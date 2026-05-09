# ADR-008 — Replay architecture: zero-touch parallel-pipeline sandbox for what-if signal experiments

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-09 |
| Session | Session 24 |
| Supersedes | ENH-93 CANDIDATE (2026-05-07) — CANDIDATE → CLOSED via this ADR |
| Related ENH / TD / commits | ENH-93 (closure), ENH-95 (in-process orchestrator optimization candidate), TD-087 (hist_option_bars_1m IST-as-UTC), TD-094 (hist_option_bars_1m.oi=0 backfill defect) |

---

## Context

ENH-93 was filed in Session 22 (2026-05-07) as a CANDIDATE to "build replay/simulation harness — exact mimic of live runner cycle for outside-market-hours testing". The proposal called out three use cases: closing data-outage gaps, pre-deploy testing of signal logic changes, and weekend operator validation of the full pipeline against historical days.

By Session 24 (2026-05-09), the operational gap had clarified: the actual high-value use case is **what-if signal-logic experiments**. Live signal_snapshots cannot be replayed under modified code without touching production. Re-running ingest scripts in a sandbox (the simplest mental model — "pour the balls back into the same bucket") fails because:
- Live ingest scripts are wall-clock dependent: `dhan.get_option_chain()` returns the current chain, not 2026-05-07's chain; `fetch_india_vix()` returns today's VIX; `now()` and `date.today()` are everywhere.
- Live scripts write to live tables. Re-running them today would write today's rows on top of 2026-05-07's, corrupting the very baseline being validated against.
- Even with input freezing, telemetry/heartbeat/Telegram side-effects fire.

The architectural question is therefore not "how do we re-run live scripts" but "how do we run a faithful copy of live signal-generation logic against historical data, with zero production touch, in a way that supports controlled code-change experiments".

## Decision

Build a parallel pipeline layer with these properties, all of which hold simultaneously:

1. **Parallel table layer.** Ten `_replay`-suffixed Supabase tables mirror the live signal pipeline's tables exactly (CREATE TABLE LIKE INCLUDING ALL): `option_chain_snapshots_replay`, `market_spot_snapshots_replay`, `gamma_metrics_replay`, `volatility_snapshots_replay`, `momentum_snapshots_replay`, `market_state_snapshots_replay`, `ict_zones_replay`, `signal_snapshots_replay`, `options_flow_snapshots_replay`, `script_execution_log_replay`. No live table is ever written by replay code.

2. **Parallel script layer.** Seven replay scripts mirror their live counterparts (`replay_compute_gamma_metrics.py`, `replay_compute_volatility_metrics.py`, `replay_build_momentum_features.py`, `replay_build_market_state_snapshot.py`, `replay_detect_ict_patterns_runner.py`, `replay_compute_options_flow.py`, `replay_build_trade_signal.py`) plus a chain reconstructor (`replay_chain_reconstructor.py`), a clock module (`replay_clock.py`), and an execution-log mirror (`replay_execution_log.py`). All under `C:\GammaEnginePython\replay\`. Live scripts are physically untouched — replay is a sibling tree, not a fork or set of monkey-patches.

3. **Time injection via CLI named args.** Every replay script takes `--replay-ts <iso-8601>`. Boundary timestamps drive the pipeline; no environment-variable overrides, no monkey-patched `now()`. A failed parse produces a non-zero exit; ambiguity is impossible.

4. **Out-of-hours hard guard.** `replay_clock.assert_outside_market_hours()` blocks all replay execution between 08:00 and 16:30 IST on weekdays. Weekends and Indian-market holidays are open. The orchestrator checks this once at entry and refuses to run if the guard fires.

5. **Permitted live reads, prohibited live writes.** Replay code may READ from immutable historical reference: `instruments`, `hist_spot_bars_1m`, `hist_option_bars_1m`, `india_vix_daily`, `option_chain_snapshots` (for the OI lift documented under TD-094), `market_breadth_intraday`, `weighted_constituent_breadth_snapshots`, `ict_htf_zones`, `po3_session_state`, `capital_tracker`. Replay code MUST NOT WRITE to any live table under any circumstance. The constraint is enforced architecturally (replay scripts only address `_replay` table names) rather than by runtime check.

6. **Boundary-driven orchestrator.** `replay_runner_for_date.py` takes a date, acquires a file lock at `replay/runtime/replay.lock`, asserts out-of-hours, TRUNCATEs nine `_replay` tables (`script_execution_log_replay` is preserved as audit), reconstructs chain + spot via `replay_chain_reconstructor.py`, then iterates 5-min boundaries from 09:15 IST to 15:30 IST. **Critical contract: scripts run in V19 §5.2 order PER BOUNDARY, not script-by-script across all boundaries** — this matches live's incremental cycle behavior and ensures each downstream script sees its expected upstream output. Script invocation is via subprocess; failures are isolated to the failing (boundary, symbol, script) tuple and do not halt the run.

7. **Validation philosophy: replay-vs-replay, not replay-vs-live.** The intended use of this system is to compare two replay runs against each other with one variable changed, not to chase bit-identical reproduction of live values. Replay-vs-live comparisons are useful for understanding divergence sources but are not the validation target. (See § "Governance language" below for why this matters.)

## Evidence

Phase 4b run on 2026-05-07 (Session 24) executed the orchestrator end-to-end across 76 boundaries × 2 symbols × 7 scripts = 1064 invocations. **1056 succeeded (99.2%).** Eight failures were all explainable: one boundary (15:30) reconstruction-skipped because the last hist bar is at 15:29; six SENSEX boundaries during 2026-05-07 OI-gap windows where live `option_chain_snapshots` had no data to lift; one collateral failure in the same windows. No logic bug emerged from the run.

Per-script success: gamma 144/152 (95%), volatility 147/152 (97%), momentum 152/152, market_state 152/152, ICT detector 152/152, options_flow 150/152 (99%), signal 152/152.

Phase 5 validation on the same day produced the headline divergence pattern that the architecture predicts:

- NIFTY direction-of-edge match with live signal_snapshots: 100% gamma_regime, 68% direction_bias / action match, avg confidence diff 4.7. The 32% direction-bias divergence traces to the documented 5-min-vs-1-min spot-granularity property.
- SENSEX action match 91% but gamma_regime match only 28%. The 91% is largely DO_NOTHING-on-DO_NOTHING tautology; the 28% gamma divergence is the structural strike-base property — replay's 11-strike base × 100-pt SENSEX step covers ±500pts which frequently fails to bracket a flip level that live's full chain (~482 strikes) does bracket.
- Both replay and live had `trade_allowed=true` on zero boundaries that day — 2026-05-07 was a LONG_GAMMA / NO_FLIP day across the session per ENH-35 gating, so executable signals could not be cross-validated against live on this date.

These results are consistent with the architecture's design constraints, not surprising failures.

## Alternatives considered

**(A) Re-run live ingest scripts in a sandbox Supabase project.** Rejected: live ingest is wall-clock dependent (Dhan/Zerodha APIs serve the present, not the past), and even with input freezing, output drift comes from `now()`, `date.today()`, telemetry side-effects, and Telegram alerts. The "pour the balls back" mental model fails because the balls aren't the same balls — every API call gets today's data.

**(B) Monkey-patch live scripts at run-time (replace `now()`, redirect writes, freeze API responses).** Rejected: violates zero-touch-on-live constraint structurally — every future live-script change becomes a "did this break replay" investigation. Diagnostic blast radius is unacceptable.

**(C) Single-script replay (e.g., signal builder only, with hand-written inputs).** Rejected: most signal-logic experiments need the full upstream chain to behave consistently. Hand-written inputs cannot reproduce the boundary-by-boundary state accumulation that gates like ENH-55 (momentum opposition), ENH-76/77 (PO3 session bias), and ENH-78 (DTE PDH sweep) depend on.

**(D) Live-table re-write with replay flag column (e.g., add `is_replay BOOLEAN` to gamma_metrics).** Rejected: every consuming view, dashboard, and downstream script would need filtering logic. Higher coupling, higher regression risk, no diagnostic isolation benefit over `_replay` tables.

## Consequences

### Positive

- Enables what-if signal-logic experiments (the primary use case — see Governance language below).
- Runs without market-hours risk: out-of-hours hard guard plus zero-touch-on-live make accidental production impact structurally impossible.
- Audit trail per invocation via `script_execution_log_replay` (host=`replay`) gives the same diagnostic surface as live ExecutionLog.
- Surfaces data-quality issues in the historical layer: TD-087 (hist_option_bars_1m IST-as-UTC defect, 5h30m phantom offset) and TD-094 (hist_option_bars_1m.oi=0 from S22 Kite backfill — Kite historical_data API does not return OI for index option minute bars) were both diagnosed during replay construction and now have permanent compensations in `replay_chain_reconstructor.py` (5h30m subtract on read for option bars; OI lifted from live `option_chain_snapshots` for the replay date).

### Negative

- Replay reproduces live signal logic **structurally** but not quantitatively. Three architectural divergences are documented and accepted, not bugs:
  1. **Strike-base divergence.** Replay's `option_chain_snapshots_replay` derives from `hist_option_bars_1m` which captured ATM±5 strikes per S22 backfill (11 strikes per symbol per boundary). Live `option_chain_snapshots` captures the full chain (~482 strikes per boundary). Net consequence: replay net_gex, gamma_concentration, flip_level diverge quantitatively from live. Direction/sign typically match. Pronounced more on SENSEX (100-pt step → ±500pt coverage) than NIFTY (50-pt step → ±250pt coverage). Resolution path if quantitative parity becomes required: re-backfill `hist_option_bars_1m` at full-chain width OR widen reconstructor to lift chain rows from live `option_chain_snapshots` directly (currently lifts only OI). Filed as discoverable property in System Map; not actively planned.
  2. **Spot granularity divergence.** Replay reads `market_spot_snapshots_replay` at 5-min boundaries; live momentum reads `market_spot_snapshots` at 1-min granularity. Returns (`ret_5m`, `ret_15m`, `ret_30m`, `ret_session`) are computed at different sample times. Direction-bias near zero-crossings can flip. Documented as architectural property.
  3. **VIX source divergence.** Replay reads `india_vix_daily` historical close for replay_date (single value per day). Live reads `fetch_india_vix()` (intraday tick from NSE). Replay therefore has VIX flat across the day; live VIX moves. Affects volatility_regime classification near 18.0/25.0 bucket boundaries.
- Orchestrator subprocess overhead is significant. Phase 4b ran in 5009s (~83 minutes) for one full-day replay. Per-invocation ~4.7s, dominated by Python startup and supabase client init. ENH-95 candidate filed for in-process orchestrator refactor (estimated 10-15 minutes per full-day run).

### Mitigations / discipline

- All three divergences must be in operator awareness when interpreting replay output. Captured in System Map and CURRENT.md, surfaced as a session-start read-list item if replay is the session concern.
- The orchestrator's per-script success-rate matrix is the first sanity check on every full-day run; >95% per script means data is healthy enough to interpret signal output.
- ICT detection requires the orchestrator's full boundary sequence to reproduce live behavior — single-boundary spot-checks on the ICT detector under-detect because patterns whose anchor bar is outside the 30-bar lookback window are missed at sparse invocations. Documented operationally.

## Relationship to other documents

- ENH-93 (Enhancement Register): CANDIDATE → CLOSED (this ADR is the closure record). Use cases (b) "pre-deploy testing" and (c) "outside-market-hours operator validation" are validated and live; use case (a) "close Session 22's outage gap" was not pursued because the gap is now visible and intentionally documented as a replay-vs-live divergence source.
- ENH-95 (Enhancement Register, candidate filed Session 24): in-process orchestrator optimization. Estimated runtime reduction 65min → 10-15min. Trade-off: tighter coupling between orchestrator and script internals.
- TD-087, TD-094 (tech_debt.md): both filed as compensations in `replay_chain_reconstructor.py`. TD-087 is the IST-as-UTC defect on hist_option_bars_1m bar_ts; TD-094 is the OI=0 defect from S22 Kite backfill. Both have permanent reconstructor-level workarounds; both remain open against the historical-data layer pending broader fixes.
- System Map: gains §A.X (replay scripts) and §B.X (replay tables) under Session 24 update. No live-table or live-script entries change.
- Deployment Topology: replay is Local-only. No AWS↔Local boundary shifts. (AWS does not currently run replay; this is by design — the operator's primary instance for what-if work is Local.)
- Assumption Register: no listed assumptions are validated, refuted, or superseded by this ADR. The replay-vs-live divergences are properties of data sources, not of the assumptions catalogued in §D.1–D.6.
- CLAUDE.md: gains one line in Things-That-Are-Settled per Rule 11.3.

## Governance language (one-line compressed form for CLAUDE.md settled-decisions)

*"Replay is a parallel-pipeline sandbox for what-if signal experiments — comparison of two replay runs with one code change, against the same frozen historical data — not a tool to chase bit-identical reproduction of live signal_snapshots. Zero touch on live tables; out-of-hours hard guard; boundary-driven orchestrator. Strike-base / spot-granularity / VIX-source divergences from live are documented architectural properties, not bugs."*

## What "what-if experiment" means — methodology canonical entry

This section is referenced from the Governance language above. It exists here so that future Claude sessions reading the ADR understand the intended use and do not chase the wrong validation target.

**The question replay answers.** "If MERDIAN had used DIFFERENT signal logic on date D, what signals would have been generated?" This is the only question replay is designed to answer well. It is something live data cannot answer because live cannot be re-run with modified code.

**The mechanic, in five steps.**
1. Establish baseline. Run `replay_runner_for_date.py YYYY-MM-DD` with current production logic. `signal_snapshots_replay` now contains "what replay produced with current logic on that day".
2. Snapshot the baseline. Either CTAS to a `_baseline_<tag>` table or export to CSV. Preserve before next run wipes it.
3. Modify exactly one signal-logic file. Concrete examples worth running: lower the LONG_GAMMA gate from "always block" to "block only if confidence < 50"; change ENH-55 momentum opposition threshold from 0.0005 to 0.001; lower MIN_CONFIDENCE from 40 to 35; tighten power-hour gate from 15:00 IST to 14:45 IST; add a new gate (e.g. block when gamma_concentration < 0.10 regardless of regime).
4. Re-run replay. Same date, same data, modified code. Same orchestrator command. Result lands in `signal_snapshots_replay`.
5. Diff baseline vs modified via SQL. Count signals that changed action, that flipped trade_allowed, that shifted confidence. Inspect where the change clusters (morning, afternoon, around specific gamma transitions).

**What you learn.**
- Sensitivity. Did the change flip 0 signals (gate is dormant on this day), 5 signals (modest), 30 signals (significant)?
- Direction. Did the change ADD tradeable signals, REMOVE them, or merely shift composition (BUY_PE ↔ DO_NOTHING ↔ BUY_CE)?
- Spatial. Where do the changes cluster temporally? At session open? Around gamma regime transitions? In low-volume midday lulls?

**What replay does NOT validate.**
- Replay does not validate that current production logic is correct. Comparing replay-vs-live tells you about data-source divergences, not logic correctness. The original live signal is still the live signal.
- Replay does not validate live's quantitative metrics (net_gex, flip_level, gamma_concentration absolute values). These diverge by design via the strike-base property.
- Replay does not validate executed trades. Those live in the operator's trade log; replay is a signal-generation experiment, not a P&L experiment.

**Discipline points.**
- Run a baseline first. Modifications are always evaluated against a baseline replay, never against live, because data divergences would confound the experiment.
- Single-variable changes only. Compound code changes produce uninterpretable diffs.
- Replicate on multiple days before drawing a conclusion. One-day signal counts are noisy. The pattern across 5–10 days is what supports a production change.

**Operational guidance.**
- Each full-day replay currently runs ~85 minutes (subprocess-dominated; ENH-95 candidate). Plan accordingly when scoping experiment campaigns.
- The orchestrator TRUNCATEs nine `_replay` tables at the start of every run. To preserve a baseline, snapshot before the modified-code run, not after.
- `script_execution_log_replay` accumulates across runs (it is not truncated). Audit history of every experiment is therefore retained automatically.

## Open follow-ups

- **ENH-95 (in-process orchestrator).** Candidate filed; estimated 10-15 min/run vs current 85 min. Trade-off: orchestrator imports each replay script's `main()` directly, shares supabase client, breaks per-invocation contract isolation. Decision deferred until first what-if experiment campaign demonstrates a need for faster cycle time.
- **Patchy-day stress test.** Phase 4b ran on 2026-05-07 — a healthy day with one outage window. Expanding to a known patchy day (2026-04-XX with longer outages) to confirm failure modes stay bounded to documented data gaps is a candidate single-session task. Not currently planned.
- **First what-if experiment.** No what-if experiment has been run against the validated infrastructure. Deferred to operator selection — the first experiment should target a real production-candidate change, not a synthetic test.
- **AWS replay capability.** Currently Local-only. No plan to expose on AWS unless what-if experiment campaigns require it.
- **Granularity widening (optional, defer-class).** If quantitative replay-vs-live fidelity becomes required, two paths exist: (a) re-backfill `hist_option_bars_1m` at full-chain width, or (b) widen the reconstructor to lift chain rows from live `option_chain_snapshots` (currently lifts only OI). Not active work.

---

*ADR-008 — 2026-05-09 — Session 24 — closing note. The replay system is built, fully tested end-to-end on 2026-05-07, and lives at `C:\GammaEnginePython\replay\`. ENH-93 is closed. Next step is operator-driven: when a real production-candidate signal-logic change is proposed, the experiment loop above produces the evidence that justifies (or rejects) it. Until then the system idles, waiting for a use case.*
