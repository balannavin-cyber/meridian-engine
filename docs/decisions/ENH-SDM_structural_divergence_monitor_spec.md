# ENH-SDM — Structural Divergence Monitor — Specification (AS-BUILT)

| Field | Value |
|---|---|
| Document | `ENH-SDM_structural_divergence_monitor_spec.md` |
| Location | `docs/decisions/` |
| Status | **P2 BUILT** — writer authored + wired + proven (S60). Observability-first / display-not-gate. Signal/modes gated on forward-cohort N. |
| Origin | ADR-018 D4 (rebuild of retired SMDM's defensible primitives); ADR-019 (port-not-retire governance). Primitives corrected to gamma-centric per CASE-2026-06-02 (S58). |
| Writer | `compute_structural_divergence_local.py` (commit `4bd3bf5`) |
| Table | `structural_divergence_snapshots` (+ `_replay`, ADR-008 mirror). DDL `sql/2026-06-22_enh_sdm_structural_divergence_snapshots.sql` (S58). |
| Orchestration | AWS, `run_merdian_shadow_runner_aws.py`, after `build_market_state_snapshot`, before `build_trade_signal` (commit `8cec587`). Non-fatal (failed_steps tally). |
| Supersedes | SMDM (`compute_smdm_local.py` + `smdm_snapshots`), retired ADR-018 D3. |

---

## 1. Purpose

A per-symbol, per-cycle **observability monitor** of gamma-centric structural-divergence
primitives. It records the conditions that, on CASE-2026-06-02, aligned to force short
covering on a weekly expiry. **It does not gate, route, or size anything.** Per S37
doctrine (display-not-gate) and ADR-009 (cohort-translation), a single validated case
justifies *measuring* the conditions, not *acting* on them. The cohort accrues forward;
signal/modes are unlocked only when N is sufficient (or the backward Greeks study lands —
TD-S58-NEW-1).

## 2. Data sources

Reads `gamma_metrics` only (latest + prior + session-open), plus nothing else at P2.
Confirmed source columns: `ts`, `symbol`, `expiry_date`, `dte`, `spot`, `net_gex`,
`gamma_concentration`, `straddle_atm`, `straddle_velocity`, `regime`, `pin_risk_score`.

- **latest** — most recent `gamma_metrics` row for the symbol (`order ts.desc limit 2` → row 0).
- **prior** — the row before it (`limit 2` → row 1). Absent on the first cycle of a session → rate/delta fields NULL.
- **session-open** — first `gamma_metrics` row whose `ts` (IST) falls on the latest row's IST date. Anchor for `straddle_collapse_pct`. Absent → collapse NULL.

## 3. Primitives (sourced to CASE-2026-06-02)

| Column | Definition | Case threshold |
|---|---|---|
| `pin_risk_rate` | `(pin_now − pin_prior) / gap_min × 30` — per-30-min rate. `gap_min` from the two rows' `ts`. | > 10 / 30-min = rehedge cascade |
| `straddle_collapse_pct` | `(straddle_open − straddle_now) / straddle_open × 100` — cumulative collapse from session-open straddle. Deliberately NOT latest-vs-prior (that is `gamma_metrics.straddle_velocity`). | > 25% = setup; > 35% = high-prob |
| `gamma_concentration_delta` | `conc_now − conc_prior`. | conc > 0.5 localized; > 0.6 high |
| `regime_flip` | `"{prior}->{latest}"` when `regime` changed this tick, else `"NONE"`. | NO_FLIP→LONG_GAMMA = shorts covered |
| `three_wick_reversal` | **NULL — DEFERRED TO P3.** Needs spot OHLC candles (three red + upper wicks); outside the P2 data scope (gamma_metrics latest+prior+spot). Tracked in `raw.three_wick_status`. | three red wicks at high conc = covering trigger |

Carried direct from the latest `gamma_metrics` row: `pin_risk_score`, `straddle_atm`,
`gamma_concentration`, `net_gex`, `regime`, `spot`, `expiry_date`, `dte`.

## 4. Classifier fields (AS-BUILT definitions — derived from CASE-2026-06-02, ratified S60)

The S57 spec that first named these was authored to outputs and never committed, so the
enum value-sets had no canonical source. The definitions below are the as-built ones and
are the canonical reference going forward.

### `phase` — escalation ladder (priority order)
| Value | Condition |
|---|---|
| `FLIP` | `regime_flip != "NONE"` (regime transitioned this tick) |
| `CASCADE` | else if `pin_risk_rate > 10` (rehedge cascade) |
| `CONCENTRATED` | else if `gamma_concentration > 0.5` (localized supply) |
| `STABLE` | else |

### `direction` — dealer posture (NOT a price prediction)
Deliberately describes dealer behavior, not a buy/sell lean — honest for display-not-gate.
| Value | Condition |
|---|---|
| `TRANSITION` | `regime_flip != "NONE"` |
| `AMPLIFYING` | regime contains `SHORT` (dealers amplify → expansion risk) |
| `DAMPENING` | regime contains `LONG` (dealers dampen → mean-revert/pin) |
| `NEUTRAL` | NO_FLIP / unknown |

### `sdm_score` — integer count of aligned conditions (0–4 now; 0–5 at P3)
`+1` each: `pin_risk_rate > 10`; `gamma_concentration > 0.5`; `straddle_collapse_pct > 25`;
`regime_flip != "NONE"`. (`three_wick_reversal` adds the 5th at P3.) A **count, not a tuned
weight** — deliberately honest for a monitor.

### `divergence_mode` — held `"OBSERVE"` at P2
Offensive (fade the engineered settlement reversal) / defensive (stand-aside) modes are
gated on forward-cohort N per S58. Emitting a tradeable mode pre-cohort would violate
display-not-gate. Hard-coded `"OBSERVE"` until N is reached.

## 5. Governance flags

- `source_stale_floored` (boolean) — ADR-018 D2 recency-floor on the gamma read. For a
  monitor the row is still emitted when stale, *flagged* (not nulled): a gate-reader drops
  it, a display-reader greys it. Env override `MERDIAN_SDM_RECENCY_FLOOR_MIN` (default 15).
- `raw` (jsonb) — builder, builder_version (`ENH_SDM_P2_V1`), input ts's, gap_min,
  straddle_open anchor, thresholds, `three_wick_status=DEFERRED_P3_needs_OHLC`,
  `display_not_gate=true`.

## 6. Write contract

One row per symbol per cycle, UPSERT on `(symbol, ts)`; `ts` = the latest gamma row's `ts`
(1:1 alignment). `run_id` carried from the gamma row. `id`/`created_at` DB defaults.
ExecutionLog: `expected_writes={"structural_divergence_snapshots": 1}`; exit reasons
SKIPPED_NO_INPUT (no gamma row), DATA_ERROR (fetch/upsert failure), SUCCESS.

## 7. Orchestrator placement & safety

Two tuples in `execute_pipeline`'s step list, after the SENSEX market_state tuple, before
the NIFTY trade_signal tuple. `run_compute_step` catches non-zero/timeout/exception and
returns False without raising; `execute_pipeline` iterates with a `failed_steps` tally (no
abort-on-first-failure). So a SDM failure logs FAILED and the signal steps still fire —
display-not-gate honored; the monitor can never take down the production compute chain.

## 8. Validation status & roadmap

- **Mechanically proven (S60):** writer runs clean both symbols, all columns populate,
  session-open anchor reads per-symbol, recency-floor flags correctly, `divergence_mode:OBSERVE`,
  `three_wick_reversal:null`. (Proven on 06-26 data, since purged as holiday noise — TD-S60-NEW-4.)
- **Live cohort accrual:** begins at the next real open. First true validation is rows
  every 5 min with `source_stale_floored:false` and rates/collapse moving intraday.
- **P3 (next build):** `three_wick_reversal` — requires a spot-OHLC bars source.
- **Backward study (blocked):** N→~50 needs the purchased-chain Greeks solve (TD-S58-NEW-1;
  0.00% Greeks across all 12 months). Gates ENH-SDM ever becoming a *signal*.
- **Modes (gated):** offensive/defensive unlocked only on sufficient forward N + ADR-009
  out-of-sample net-of-costs holdout on post-ban data.

## 9. Lineage

SMDM (`compute_smdm_local.py`, `smdm_snapshots`) retired ADR-018 D3 (Exp 9 NEUTRAL +
redundant gamma-squeeze scalar). Salvaged: `compute_straddle_velocity` concept (now
`straddle_collapse_pct` anchored differently). Dropped: STOP_HUNT/SQUEEZE/GAMMA_PINNING
narrative scoring; `otm_oi_velocity` (never built). breadth/OI/VWAP primitives from ADR-018
D4's first list deferred as candidate secondary primitives (the validated case is gamma-centric).

---

*ENH-SDM spec — AS-BUILT S60 (2026-06-26). Committed to close the S57 spec-debt (authored to outputs, never versioned) and ratify the classifier enums. Writer `4bd3bf5`, wiring `8cec587`. Display-not-gate; cohort accrues forward.*
