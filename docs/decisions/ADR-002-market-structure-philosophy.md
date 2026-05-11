# ADR-002 v2 — Market Structure Philosophy: Force, Zones, Vol-Pricing, and the Buyer/Writer Inversion

| Field | Value |
|---|---|
| **Status** | Draft pending acceptance (replaces ADR-002 v1) |
| **Date** | 2026-05-11 |
| **Session** | Session 27 candidate — full rewrite of ADR-002 v1 (Session 12, 2026-04-28) |
| **Supersedes** | ADR-002 v1 (preserved in git history at `b46249e` and prior) |
| **Companion ADRs** | ADR-001 (gate validity), ADR-007 (V18F ICT pivot), ADR-009 (calibration discipline) |
| **Related ENH** | ENH-75 (done) · ENH-80 (refined scope) · ENH-81 (refined scope) · ENH-82 (Exp 23 dependent) · ENH-83 (deferred Phase 1.5+) · **ENH-84 NEW** (vol_analytics + RR ratio) · **ENH-85 NEW** (Vanna/Charm for Phase 3) |
| **Related TD** | TD-036 (confidence ceiling — partially addressed) · *new:* vol-pricing absent · *new:* sign-convention unaudited |
| **Triggered by** | Session 12 dashboard analysis + Session 27 re-read of source material (Twitter screenshots Apr 28–30, PDF article + dashboard panels) revealing material additions to v1 |

---

## Context

ADR-002 v1 (Session 12, 2026-04-28) formalised six market-structure principles distilled from observing a successful options writer's gamma dashboard. Session 27 revisited the source material — five Twitter screenshots with practitioner commentary across multiple expiry-week sessions, plus a more comprehensive dashboard article (the "Positioning Landscape" + "Projected Dealer Hedging Flow" + "Volatility Analytics" view set) — and identified six material additions to v1.

1. **The PDF article opens with five operational questions** the framework exists to answer. Four map to v1 principles; the fifth — *"When does IV stop matching realized movement?"* — has no analog in v1.
2. **The dashboard's Positioning Landscape view names five concrete strike-level metrics** (Gamma Wall, Short Strike For, Gradient Max, λ-Score, Hedged Long) that are more usable operationally than v1's generic zone-bound abstractions.
3. **The dashboard tracks Realized vs Implied Vol Ratio (RR) as a primary signal**, with explicit regime thresholds (RR > 1.2 favours buyers, RR < 0.85 favours sellers). v1 contains no vol-pricing principle.
4. **The dashboard exposes Vanna sensitivity** as a separate Greek with its own panel. v1 mentions only gamma. For Phase 3 writing this is non-optional — sellers blow up on vanna events, not gamma events.
5. **The Twitter commentary makes the buyer/writer inversion explicit:** *"if 23719 breaks, dealers are forced to sell futures — that's where panic enters the system."* The same structural data is read in mirrored directions by buyers and writers. v1 treated the framework as gamma-engine machinery without naming the inversion as a first-class architectural concept.
6. **v1 specifies columns and column names but no algorithms.** A practitioner inheriting v1 cannot reproduce the metrics. Methodology must be specified before build.

ADR-002 v2 is a full rewrite. The six v1 principles are preserved (with P5 refined for the PINNED-state operationalisation pathway). Two new principles are added: **P7 (vol pricing)** and **P8 (second-order Greeks for Phase 3)**. New scaffolding sections specify: the five-questions operational framing, the buyer/writer inversion as a first-class concept, the refined Positioning Landscape metrics, the volatility-analytics module, methodology requirements before build, Phase 0 calibration discipline, operational wisdom encoded as governance language, and explicit prerequisites for Phase 3 beyond P1–P8.

This is not architectural drift. v1 captured what the writer's dashboard surfaced about gamma. v2 captures what the writer's framework actually does end-to-end: **gamma + vol-pricing + buyer/writer-symmetric interpretation + operational execution discipline**.

---

## The Five Questions

The framework exists to answer five questions, in this priority order. Every feature must answer at least one. Features answering none are not load-bearing.

1. **Where are dealers likely trapped?** Trapped short-gamma positioning is the cascade trigger. Locating it (which strike, how much in Crore) is the highest-edge directional signal in the options market. *Mapped to P3.*
2. **When does IV stop matching realized movement?** Premium pricing is independent of structural direction. A correct directional call funded by overpriced premium is a losing trade for buyers; a correct call funded by underpriced premium is a losing trade for sellers. *Mapped to P7.*
3. **Is gamma dampening volatility or amplifying it?** LONG_GAMMA, SHORT_GAMMA, and PINNED regimes behave categorically differently. Misclassifying the regime is misclassifying the playbook. *Mapped to P5.*
4. **At what point does hedging flow become fuel for expansion?** The acceleration zone. Once spot breaches it, dealer hedging adds to the move rather than damping it. Mechanical, not probabilistic. *Mapped to P3 + P4.*
5. **When does a move become mechanically unstable?** Vanna events, IV-driven cascades, and DTE-amplified gamma stress create structural instability separate from directional view. These are the events where Phase 3 sellers blow up. *Mapped to P2 + P6 + P8.*

When designing or debugging any feature, the engineer asks: *"Which of the five questions does this answer?"* If the answer is "none," the feature is not load-bearing.

---

## The Eight Principles

### P1 — Markets are zones, not points

The gamma flip is not a strike; it is a zone where dealer behaviour changes character. The pin is not a strike; it is a cluster of strikes where gravitational force concentrates. Acceleration does not begin at one number; it builds across a range as multiple writers are forced to hedge simultaneously. The strikes that matter are bounded ranges with characteristic widths, not single integers.

**Implementation.** Every structural feature — flip level, pin zone, acceleration zone, max gamma — is stored as `(level, lower_bound, upper_bound)` plus magnitude. The level remains useful as a display centroid; the bounds carry the truth. Zone width is computed empirically, not assigned by formula (see Methodology §1).

**Buyer use.** Don't enter on edge-of-zone — wait for full traversal. Wick-fakes at zone boundaries are the trap.
**Writer use.** Sell premium within pin-zone bounds. Reduce risk near edges.
**MERDIAN gap pre-v2.** `flip_level`, `gamma_concentration` stored as scalars. No zone widths anywhere.

---

### P2 — Direction is minimum viable. Force is the actual edge.

Knowing direction is not edge — direction is publicly available. Knowing **magnitude** — ₹14,467 Cr of forced dealer buying if spot moves +1% — is edge, because it tells you whether a support holds or gets steamrolled. Without force, every structural level looks equally significant. With force, you know which levels have mechanical backing sufficient to matter at your trade size.

**Implementation.** Dealer flow simulator runs each cycle, computing forced hedge flow in Crore **and contract count** for six scenarios: ±0.5%, ±1.0%, ±2.0% spot moves (expanded from v1's four). Stored on `gamma_metrics`. Trajectory indicator per scenario (BUY/SELL/NEUTRAL — does this move cross max-gamma into NEUTRAL, cross flip into opposite regime?) precomputed for gate consumption.

**Buyer use.** Sizing input. High-force tailwind → larger position. Low-force setup → standard or smaller.
**Writer use.** Risk gate. High-force adverse scenarios → reduce or close positions. Force-aware position sizing on credit strategies.
**MERDIAN gap pre-v2.** No dealer flow magnitude computed.

---

### P3 — Know where sellers panic

Options writers are short gamma. They are hedged and comfortable while spot stays in their expected range. The flip is where that comfort ends. Above the flip, short-call writers face unlimited delta exposure and must buy futures as spot rises — pushing spot higher, forcing more buying. Below the pin, short-put writers face the mirror. This is not a probabilistic signal — it is a deterministic cascade once trapped positioning is triggered.

The edge is knowing (a) where trapped positioning is concentrated, (b) how large it is in Crore, and (c) how far spot is from the trigger. Once the trigger fires, the cascade is mechanical.

**Implementation.** Three named scalar fields on `gamma_metrics`:
- `gamma_wall_strike` — peak strike of dealer-long-gamma cluster (pin gravity anchor)
- `short_strike_for_strike` — peak strike of dealer-short-gamma cluster (cascade ignition point)
- `gradient_max_strike` — strike of steepest GEX slope (maximum-force-per-tick location)

**Buyer use (HIGHEST PRIORITY for Phase 1).** The writer's *"if 23719 breaks, panic enters the system"* is the buyer's entry trigger inverted. Trade the cascade direction once spot crosses `short_strike_for_strike`. This is the single highest-conviction directional setup available from gamma intelligence.
**Writer use.** Avoid net-short positions in the cascade direction. Sit out cascade-vulnerable days.
**MERDIAN gap pre-v2.** `flip_level` stored. No magnitude of trapped positioning. No per-strike GEX time-series. Acceleration zone not a named engine output.

---

### P4 — The regime has velocity

A gamma snapshot is a location reading. Trajectory — direction and rate — is a separate and often more valuable signal. Max gamma migrating from 24,600 to 24,200 over a session means the gravitational centre is drifting down. Net GEX falling from −976 Cr to −14,323 Cr means the force is accelerating, not merely present. A regime moving toward spot is materially different from one spot is already inside.

**Implementation.** `max_gamma_strike_delta` (change vs N periods) and `gex_velocity` (rate of change) on `gamma_metrics`. **Plus two parallel time-series views** of per-strike GEX (new in v2):
- **Classic GEX** — cumulative positioning (where is the structural pin?)
- **OI-Change GEX** — today's net positioning delta (which way is positioning migrating right now?)

The two views answer different questions and must both be available. The PDF source dashboard explicitly maintains both panels.

**Buyer use.** Structure migrating toward your direction + zone breach = compound signal. Trade larger.
**Writer use.** Structure migrating away from your sold strikes = early warning. Roll or close.
**MERDIAN gap pre-v2.** No historical GEX derivative terms. No OI-change GEX view at all.

---

### P5 — Local context beats aggregate signal

Net GEX can be negative (aggregate SHORT_GAMMA) while local GEX around current spot is deeply positive (pin gravity active right where price lives). These are simultaneously true and point in opposite directions. The market does not respond to net GEX — it responds to GEX at strikes near current spot. A session where net is −1,000 Cr but spot sits inside a +5,000 Cr local positive cluster behaves like a pinned session, not a SHORT_GAMMA amplification session. The binary regime based on net-GEX sign misclassifies this entire session type.

**Implementation.** Third regime state — `PINNED`. Criteria: spot within a positive local-GEX cluster of sufficient magnitude, regardless of net-GEX sign. Threshold determined empirically by Experiment 23 (currently blocked on per-strike GEX time-series; unblocked by ENH-80). Pre-Exp-23 advisory field: `local_gex_cluster_cr` (sum of positive GEX within ±200 pts of spot) — visible to operator, not yet gate-binding.

**Buyer use.** PINNED days are blocked-momentum days. Don't fight the pin — wait for breach or session end.
**Writer use.** PINNED days are premium-collection days. Optimal short-straddle environment.
**MERDIAN gap pre-v2.** Binary LONG/SHORT regime. PINNED state architecturally specified but unbuilt.

---

### P6 — DTE is a force multiplier, not a risk flag

Same spot, same GEX, on DTE=5 vs DTE=1 is a physically different situation. DTE=5: gamma structure is thick and slow — large OI, gradual hedging, wide dealer tolerance. DTE=1: gamma near-infinite at ATM — tiny moves require massive delta hedges, cascade probability non-linear. DTE should appear in the force calculation as a continuous multiplier, not just as a binary execution gate.

**Implementation.** Dealer flow simulator output is DTE-weighted. ENH-83 specifies the curve, fitted from historical data once enough DTE-varied per-strike GEX accumulates. Deferred Phase 1.5+.

**Buyer use.** DTE-1 with high force is an *enhanced* setup, not a categorically rejected one. The DTE-1 gate should not be blanket. (Today, Session 26, this gate blocked every NIFTY signal on a clean −1.47% trend day.)
**Writer use.** Phase 3 sellers must size by DTE-adjusted force. The same naked short option behaves catastrophically differently DTE=1 vs DTE=5.
**MERDIAN gap pre-v2.** DTE is binary execution gate only.

---

### P7 — Vol pricing is independent of direction (NEW)

A correct directional call funded by overpriced premium is a losing trade for buyers. A correct call funded by underpriced premium is a losing trade for sellers. **Vol pricing is the second axis of edge after direction**, and it operates independently. The structural directional intelligence (P1–P6) tells you which way to lean. The vol-pricing dimension (P7) tells you whether to lean in via premium-buying or premium-selling — and whether to lean in at all.

**Implementation.** Realized vs Implied Vol Ratio (RR) computed each cycle. Stored on new `vol_analytics` table (schema below). Regime thresholds:

| RR Range | Interpretation | Buyer disposition | Writer disposition |
|---|---|---|---|
| RR > 1.2 | Realized > implied → vol underpriced | **Favourable — premium underpaid** | Adverse |
| 0.85 ≤ RR ≤ 1.2 | Fair-priced | Neutral | Neutral |
| 0.4 ≤ RR < 0.85 | Vol overpriced | Adverse | **Favourable — premium overcollected** |
| RR < 0.4 | Deeply compressed — likely event premium | Variable — check event calendar | Variable |

Realized vol from 15-min rolling spot return on `market_spot_snapshots`. Implied vol from ATM straddle on near-expiry chain. 30-min and 60-min realized vols stored as auxiliary windows for sensitivity analysis. Primary signal uses 15-min.

**Buyer use (CRITICAL for Phase 1).** Don't enter premium-buying signals when RR < 0.85. This is the largest single missing filter on today's signal stack. The Session 26 audit (-1.47% NIFTY trend day, 256 BUY_PE signals, 0 traded) had no vol-pricing context anywhere; conversely the gate stack could be approving direction at adverse vol pricing on other days without operator awareness. ENH-84 makes this visible.
**Writer use.** Don't sell premium when RR > 1.2.
**MERDIAN gap pre-v2.** No vol-pricing context anywhere. Premium decision implicit in gate stack, never explicit.

---

### P8 — Second-order Greeks (Phase 3 prerequisite) (NEW)

For Phase 1 buyers, gamma is the dominant force. For Phase 3 writers, **vanna** (`dδ/dIV`) and **charm** (`dδ/dt`) are how positions blow up. A short straddle near the pin is perfectly safe at constant IV and catastrophic if IV spikes 30% on an event — vanna pushes delta in the spike direction, dealers rehedge in the spike direction, the cascade amplifies. Pure gamma intelligence misses this entire failure mode.

**Implementation.** ENH-85 (new) — aggregate vanna and charm at each cycle, stored on `gamma_metrics`. Phase 3 gate stack consumes both. Phase 1/2 consume vanna as a risk advisory only; charm is Phase 3-only.

**Buyer use.** Mostly informational. Heavy negative vanna + rising IV = potential cascade entry signal (the writer's *"if 23719 breaks"* scenario is partly vanna-driven).
**Writer use (MANDATORY for Phase 3).** Vanna-aware position sizing. Vanna-stop loss rules. Vanna event calendar (Fed, RBI, budget).
**MERDIAN gap pre-v2.** No second-order Greeks computed.

---

## The Buyer/Writer Inversion (NEW first-class concept)

ADR-002 v1 read as gamma-engine machinery for Phase 3 enablement. v2 makes explicit what was implicit: **the same structural intelligence is read in mirrored directions by buyers and writers.**

| Structural fact | Writer reads it as | Buyer reads it as |
|---|---|---|
| Spot inside pin zone | Premium-collection opportunity | Blocked-momentum day, wait for breach |
| Spot near `short_strike_for_strike` | Risk-trigger line | Cascade entry signal |
| Spot crosses `short_strike_for_strike` | Stop loss, close positions | Highest-conviction directional entry |
| `local_gex_cluster_cr` strongly positive | Safe-to-sell zone | Pin gravity blocks trades |
| RR > 1.2 | Adverse, hold off | Premium underpaid, lean in |
| RR < 0.85 | Premium overcollected, sell aggressively | Adverse, hold off |
| `gamma_wall_strike` above spot | Sell premium above this strike | Take profit if long approaches |
| Acceleration zone breach | Hedging panic, cut size | Cascade ignition, scale up |
| Rising vanna into event | Lethal — close all short premium | Potential cascade fuel — lean in cautiously |

**Architectural consequence.** The gamma layer is one set of computed metrics. **The signal layer reads them through different lenses depending on strategy mode** (currently Phase 1 buyer; eventually Phase 2 spread; eventually Phase 3 writer). Therefore:

- The data layer (per-strike GEX, force scenarios, RR, vanna) is shared infrastructure.
- The gate stack has a strategy-mode parameter. Phase 1 mode reads with buyer polarity; Phase 3 mode reads with writer polarity.
- Phase 2 (spreads) is mixed — long leg reads with buyer polarity, short leg with writer polarity.

This eliminates a category error v1 risked: building "writer's intelligence" and treating it as Phase 3-only. **The intelligence is universal. Only the interpretation flips.**

**Today (Session 27), MERDIAN is in Phase 1 (buyer) mode. The most immediate value from ADR-002 v2 is the buyer-polarity reading of the writer's structural metrics.** Specifically: cascade-entry detection (P3 inversion), RR-aware premium-buying filter (P7), and PINNED-day blocked-momentum recognition (P5 inversion).

---

## Positioning Landscape — refined metric set

ADR-002 v1 specified zone bounds. v2 specifies **five named scalar metrics** that are operationally more usable, drawn from the PDF dashboard's Positioning Landscape view:

| Metric | Definition | Stored as | Behavioural meaning |
|---|---|---|---|
| `hedged_long_cr` | Total dealer-long-gamma in Crore | `gamma_metrics` column | How much structural pin force is currently active |
| `gamma_wall_strike` | Peak strike of dealer-long-gamma cluster | `gamma_metrics` column | Specific strike pin gravity anchors to |
| `short_strike_for_strike` | Peak strike of dealer-short-gamma cluster | `gamma_metrics` column | Specific strike where cascade ignites |
| `gradient_max_strike` | Strike with steepest GEX slope | `gamma_metrics` column | Maximum-force-per-tick location |
| `lambda_score_pct` | Composite positioning-health metric (MERDIAN-fit, see Methodology §4) | `gamma_metrics` column | Single-number summary of structural fitness |

Zone bounds from v1 (`flip_zone_lower/upper`, `pin_zone_lower/upper`, `accel_zone_lower/upper`) are **retained** as auxiliary fields for display and edge-case detection, but the five named scalars above are the **primary consumption surface** for the gate stack. Scalars are easier to reason about, easier to gate-condition, and map directly to operator language.

---

## Dealer Flow Simulator — expanded scenario grid

v1 specified four scenarios with Cr only. v2 expands to six scenarios with contract counts, notional Cr, and trajectory indicator each:

| Scenario | Move | Output: Δ contracts | Output: notional Cr | Output: trajectory |
|---|---|---|---|---|
| `dealer_flow_down_2` | −2.0% | integer | numeric | BUY / SELL / NEUTRAL |
| `dealer_flow_down_1` | −1.0% | integer | numeric | BUY / SELL / NEUTRAL |
| `dealer_flow_down_05` | −0.5% | integer | numeric | BUY / SELL / NEUTRAL |
| `dealer_flow_up_05` | +0.5% | integer | numeric | BUY / SELL / NEUTRAL |
| `dealer_flow_up_1` | +1.0% | integer | numeric | BUY / SELL / NEUTRAL |
| `dealer_flow_up_2` | +2.0% | integer | numeric | BUY / SELL / NEUTRAL |

Six scenarios capture the full force-decay profile from the dashboard. Contract counts inform execution sizing (lot equivalents). Trajectory indicator flags regime transitions (move crosses max-gamma → NEUTRAL; move crosses flip → opposite regime; move crosses `short_strike_for_strike` → cascade ignition).

---

## Volatility Analytics — new module

```sql
CREATE TABLE IF NOT EXISTS public.vol_analytics (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              uuid NOT NULL,
    symbol              text NOT NULL,
    ts                  timestamptz NOT NULL,
    realized_vol_15m    numeric,    -- annualized 15-min rolling realized vol
    realized_vol_30m    numeric,    -- 30-min rolling (cross-check)
    realized_vol_60m    numeric,    -- 60-min rolling (cross-check)
    implied_vol_atm     numeric,    -- ATM straddle implied vol
    rr_ratio            numeric,    -- realized_15m / implied_atm (primary)
    rr_regime           text,       -- HIGH | FAIR | LOW | COMPRESSED
    created_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vol_symbol_ts ON public.vol_analytics (symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_vol_run_id    ON public.vol_analytics (run_id);
```

Cadence: every 5 minutes, same as `gamma_metrics`. Compute path: realized vol from `market_spot_snapshots` rolling window; implied vol from ATM straddle on near-expiry option chain at cycle time. Annualisation: √252.

Implementation tracked as **ENH-84** (new).

---

## Schema — additions to gamma_metrics

```sql
-- Positioning Landscape scalars
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS hedged_long_cr           numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS gamma_wall_strike        numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS short_strike_for_strike  numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS gradient_max_strike      numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS lambda_score_pct         numeric;

-- Local-context and velocity
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS local_gex_cluster_cr     numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS gex_velocity             numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS max_gamma_strike_delta   numeric;

-- 6 force scenarios (replaces v1's 4)
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS dealer_flow_down_2_cr        numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS dealer_flow_down_2_ctr       integer;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS dealer_flow_down_2_traj      text;
-- (repeat triple for down_1, down_05, up_05, up_1, up_2)

-- Zone bounds (auxiliary, retained from v1)
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS flip_zone_lower    numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS flip_zone_upper    numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS pin_zone_lower     numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS pin_zone_upper     numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS accel_zone_lower   numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS accel_zone_upper   numeric;

-- Phase 3 prerequisites (ENH-85)
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS aggregate_vanna    numeric;
ALTER TABLE public.gamma_metrics ADD COLUMN IF NOT EXISTS aggregate_charm    numeric;

-- Regime updated to include PINNED via Exp 23 outcome
-- (existing `regime` column gains PINNED enum value on ENH-82 deploy)
```

Per-strike snapshot table `gex_strike_snapshots` (from v1 ENH-80) unchanged. Two views computed atop:

```sql
-- Classic GEX (cumulative positioning per strike)
CREATE OR REPLACE VIEW v_gex_classic AS
SELECT symbol, ts, strike, gex_cr, is_local_max, is_flip_zone
FROM gex_strike_snapshots;

-- OI-Change GEX (today's net positioning delta per strike vs prior session close)
CREATE OR REPLACE VIEW v_gex_oi_change AS
SELECT g.symbol, g.ts, g.strike,
       g.gex_cr - prev.gex_cr AS gex_delta_cr,
       g.oi - prev.oi          AS oi_delta
FROM gex_strike_snapshots g
JOIN gex_strike_snapshots prev
  ON prev.symbol = g.symbol
 AND prev.strike = g.strike
 AND prev.ts = (
   SELECT MAX(ts) FROM gex_strike_snapshots
   WHERE symbol = g.symbol AND strike = g.strike AND ts < g.ts::date
 );
```

---

## Methodology — required specifications before build

v1 specified columns and column names but no algorithms. v2 requires the following formula specifications **before any compute code lands.**

### §1 Zone-bound definition

Pick **one** definition. Phase 0 calibration determines which:

- **Option A:** Symmetric ±N points around centroid, where `N = k × ATM_IV × √(DTE/365) × spot` (volatility-adjusted band)
- **Option B:** First strike either side of centroid with absolute GEX above empirical threshold
- **Option C:** OI-weighted percentile band (strikes containing 50% of GEX magnitude around centroid)
- **Option D:** Sustained-sign run (band ends where 3+ consecutive strikes flip sign)

Working hypothesis: **Option D** for `accel_zone` (cleanest cascade-trigger definition) and **Option C** for `pin_zone` (best centroid-of-gravity behaviour). Final selection per Phase 0b.

### §2 Dealer-flow simulator assumption stack

Explicit parameters required:

| Parameter | Default assumption | Sensitivity required |
|---|---|---|
| Dealer position fraction of OI | 0.75 | Test {0.60, 0.70, 0.80, 0.90} |
| Hedge-ratio model | Delta-neutral first pass, gamma-aware second pass | Document as known idealisation |
| Aggregation across writers | Homogeneous within strike | Test heterogeneous cluster model post-Phase 0 |
| Hedge-execution latency | Instant | Document — empirically calibrate post-Phase 1 deploy |

Run dealer-flow output across the 4-point assumption grid on a representative session. Report max-min spread on `dealer_flow_up_1` as a percentage of mean. **Acceptance:** spread < 30% → gate-consumable; 15–30% → advisory only; > 30% → demote, do not build until methodology refined.

### §3 Sign-convention audit (MANDATORY — pre-ENH-80 gate)

**~2 hours.** Identify 3 publicly-documented NIFTY sessions with known GEX state (SpotGamma equivalents, options-writer Twitter posts, the Apr 28/29/30 dashboard screenshots in this ADR's source material). Compute MERDIAN's `net_gex` and `gamma_regime` on those sessions using the existing pipeline. Compare verdict.

- If MERDIAN agrees with external reference → safe to proceed with ENH-80.
- If MERDIAN inverts on any of the three → **entire downstream gamma-layer is upside-down**; fix sign convention before building anything atop it.

This is the lowest-cost, highest-asymmetry check in the build. **Phase 0a gate.**

### §4 λ-score formula

The PDF dashboard exposes `λ-Score` as a composite without disclosing the formula. v2 specifies MERDIAN's own derivation: weighted linear combination fit against historical session-outcome target (e.g., absolute return / max-drawdown / pin-distance-from-EOD), with component features:

- `(gamma_wall_strike − spot) / spot` — pin proximity
- `hedged_long_cr / |net_gex|` — pin force ratio
- `local_gex_cluster_cr / total_gex_cr` — local concentration ratio
- `rr_ratio` — vol pricing
- `flip_zone_upper − flip_zone_lower` — flip-band width

Coefficients fit on 6 months of MERDIAN data once accumulated. Refit quarterly. **λ-Score is MERDIAN's own composite — not a clone of the writer's number.**

### §5 RR-ratio realized-vol window

Primary window: 15-minute rolling annualised realised vol. Auxiliary windows: 30-min and 60-min stored for sensitivity. ENH-84 stores all three; gate logic consumes the 15-min by default.

---

## Phase 0 — Calibration before build

ADR-002 v2 is distilled from an externally-validated practitioner system, not engineered from scratch. The principles are accepted; the parameters and integration must be MERDIAN-specific.

**Phase 0 is therefore calibration, not validation.** It runs in ~3–4 sessions before the first ENH-80 schema lands.

### Phase 0a — Sign-convention audit (Methodology §3)
**~2 hours.** Gate on this passing before any ENH-80 work.

### Phase 0b — Overlay calibration study
**~1–2 sessions.** Compute v2 metrics retroactively from `option_chain_snapshots` (data already available, no new ingestion). Tag every historical signal with the would-be gamma overlay. Test:

- Does **PINNED state** (computed retroactively per `local_gex_cluster_cr` threshold candidates) correctly identify sessions where MERDIAN was confused about regime? Target: ≥ 5 confirmed mislabeled sessions identified retrospectively.
- Does **RR < 0.85** correctly predict the days where premium-buying signals underperformed despite correct direction? Conditional WR difference between RR<0.85 and RR>1.2 strata on completed BUY signals.
- Does `gamma_wall_strike` distance correctly explain PINNED-blocked-momentum days? Confirm no-movement days had spot inside `pin_zone_lower/upper`.
- Does `short_strike_for_strike` proximity correlate with cascade-day outcomes? On confirmed cascade events in 12-month lookback, what was spot's distance to `short_strike_for_strike` at signal time?

Output: a calibrated answer to **"with this overlay in place, would we have made or saved money on N existing signals?"** — quantified gate decision per principle.

### Phase 0c — Methodology selection study (Methodology §1, §2)
**~1 session.** Run zone-definition Options A/B/C/D side-by-side on backfill. Pick the option with strongest WR differential between "spot inside zone" vs "spot outside zone." Same for dealer-flow assumption stack — confirm sensitivity within tolerance.

### Phase 0 outcome
Each Phase 0 step produces a go/no-go decision per principle. ENH-80/81/84/85 sequence locks in only on features that pass calibration. **This delays first schema landing by ~3–4 sessions but reduces wasted build work on features that don't survive calibration.**

---

## Capital Scaling Roadmap (refined)

### Phase 1 — Directional naked options buying (current)

- **Strategy:** BUY_CE / BUY_PE. Long premium, defined risk.
- **Capacity ceiling:** ~25,000 lots single name before market impact.
- **What ADR-002 v2 adds to Phase 1:**
  - RR-aware entry (P7) — single largest immediate filter improvement
  - Buyer-polarity reading of structural metrics (P1–P5)
  - Force-aware sizing (P2)
  - Cascade-entry detection (P3 — the highest-edge new signal class for buyers)
- **Operational on day 1 of build deployment.** This is not a Phase 3-deferred capability.

### Phase 2 — Debit spreads

- **Strategy:** Bull call spreads / bear put spreads.
- **Trigger:** Naked approaching capacity ceiling OR IV elevated enough that naked premium is structurally unfavourable.
- **What ADR-002 v2 adds:** Strike selection becomes load-bearing. Short leg lands at `gamma_wall_strike` (sell into the pin). Long leg lands at structural support inside flip zone.

### Phase 3 — Defined-risk credit selling

- **Strategy:** Credit spreads, iron condors, ratio spreads with defined tails. NOT naked short options.
- **Trigger:** AUM makes defined-risk selling superior to directional buying.
- **What ADR-002 v2 adds:** All **eight** principles mandatory. Phase 3 cannot deploy without P1–P8 live. Vanna and charm (P8) are non-optional — naked or near-naked short positions blow up on vanna events, not gamma events.

**Phase 3 prerequisites beyond ADR-002 (NEW explicit naming):**

This ADR does NOT alone unlock Phase 3. Four parallel build tracks must also complete:

| Track | What's needed | Current state |
|---|---|---|
| **Risk framework** | Per-trade max-loss model, per-day max-delta budget, vega budget, vanna budget, gamma-on-expiry blow-up scenarios | None exist today |
| **Execution layer** | Multi-leg Dhan order routing for credit strategies | Currently single-leg only |
| **Margin model** | SPAN+ELM margin computation. Capital allocator must understand short-premium margin (different branch from buying) | Buy-side allocator only |
| **Tax model** | Credit-selling has different STCG / positional classification with different effective tax. Per-strategy tax model needed for P&L truth | Single buy-side tax model |

**Phase 3 design begins only when all four tracks + ADR-002 P1–P8 are live.** This sequencing cannot be accelerated by skipping validation steps.

---

## GEX Weekly Time-Series (preserved)

Store per-strike GEX at 5-min cadence on `gex_strike_snapshots` for the full expiry cycle. Two views (Classic, OI-Change) computed atop. ~15,600 rows/day across NIFTY+SENSEX. Storage cost negligible; research and signal value high.

OI accumulates through the week. GEX at any strike on Monday is structurally different from Wednesday. Single snapshot at session start misses the entire build trajectory. **The time-series is the foundational data layer for P1–P5 in operation, and the prerequisite for Experiment 23.**

---

## Build Sequencing

```
Phase 0 Calibration (~3–4 sessions)
  ├─ §3 sign audit — MANDATORY GATE
  ├─ §1 zone-formula selection
  ├─ §2 assumption sensitivity
  └─ Phase 0b overlay-calibration outcomes
              │
              ▼
ENH-80 — per-strike GEX table + Classic/OI-Change views (~2–3 sessions)
              │
              ▼
ENH-84 — vol_analytics + RR (~1–2 sessions)   ← slots here because cheap & high-value
              │
              ▼
ENH-81 — gamma_metrics scalars + force simulator (~2–3 sessions)
              │
              ▼
Experiment 23 — PINNED threshold validation (~1–2 sessions)
              │
              ▼
ENH-82 — PINNED regime integration (~1–2 sessions)
              │
              ▼
Buyer-polarity gate stack integration (~2–3 sessions)   ← Phase 1 operational deployment
              │
              ▼
ENH-85 — Vanna/Charm computation (Phase 3 prep) — defer until Phase 2 imminent
ENH-83 — DTE force multiplier curve fitting — defer Phase 1.5+
```

**Estimated to Phase 1 deployment of full v2 buyer-polarity intelligence: ~12–15 sessions.**
Phase 3 prerequisites (ENH-85 + 4 parallel tracks) add ~10–15 more.

---

## Operational Hygiene Requirements

Every new feature must satisfy:

| Requirement | Specification |
|---|---|
| **Latency budget** | Pre-build profile on 10 historical batches. p99 latency reported. Must fit within 5-min cycle with 30% margin. |
| **Null handling** | Every gate consuming a v2 field declares its null-handling explicitly. Default: NULL → field-not-available → revert to legacy scalar gate. Never fail-closed silently. |
| **Shadow rollout** | Every new gate ships dual-track: production path on existing gate stack, shadow path on v2 gate stack, comparison view weekly. Promotion criterion: shadow outperforms live on rolling 30-day metric by meaningful margin. ADR-009 invoked. |
| **Decay monitoring** | Each v2 signal class has 30 / 90 / 180-day rolling P&L attribution. Threshold-driven kill-switch on sustained underperformance. |
| **Frequency floor** | Cascade signal class (P3 `short_strike_for_strike` breach) requires N ≥ 30 historical events in lookback for meaningful WR estimate. Verify before deploy. |
| **Source citation** | Every gate consuming v2 fields cites the answering question (1–5) and principle (P1–P8) in source code header. |

---

## Falsification Criteria

If a calibration study or live data refutes a principle empirically, **demote or remove it.** Record the outcome in a successor ADR.

| Principle | Falsification criterion |
|---|---|
| **P1 zones** | Phase 0b: zone-bucketing produces no WR differential above continuous distance |
| **P2 force** | Force magnitude has no marginal predictive power on T+30m return after controlling for direction + breadth + IV |
| **P3 trapped positioning** | Acceleration-zone touches do not produce statistically different outcomes than ICT zone touches alone |
| **P4 velocity** | `gex_velocity` adds no marginal edge above static `gamma_regime` in any multi-horizon configuration tested |
| **P5 PINNED** | Fewer than 10 confirmed mislabeled sessions in 12-month lookback (rarity-deprioritise) |
| **P6 DTE multiplier** | DTE-bucketed force scenarios produce same outcome distribution as DTE-unaware ones |
| **P7 RR vol pricing** | RR regime has no predictive power on BUY/PE outcome conditional on direction correctness |
| **P8 Second-order Greeks** | Vanna/charm contribute no marginal predictive power on Phase 3 backtest (apply only when Phase 3 backtest exists) |

---

## Operational Wisdom (Governance Language)

Encoded from the source material's practitioner commentary. To be cited in code comments, runbook prefaces, and case-study analyses:

> **"Price will lie. Positioning won't."**
> When chart action and gamma structure conflict, trust the structure. Mechanical hedge requirements are deterministic; price action is noisy aggregation that can be event-distorted or temporarily mispriced. Apr 29 FOMC example: price rallied, positioning didn't shift, NIFTY fell 130 pts later. Positioning was right.

> **"Not trading the level, just watching how price reacts around it."**
> Levels are not entry triggers. Price *behaviour* around levels — clean breaks, failed retests, sharp reclaim, slow drift — is the entry trigger. The gate stack must consume zone-touch *qualified by behaviour*, not zone-touch alone.

> **"Less about being right, more about having quick hands to actually execute."**
> Latency is not a downstream concern. On expiry days the structure may be correct and the move may be unavailable because the cascade resolves in seconds. The architecture must serve speed of action. Connects to TD-061/062/063 (single-instance enforcement, process discipline).

> **"A strategy that only survives screenshots and hindsight is useless."**
> All v2 features must pass forward-test, not just backtest. Shadow-rollout framework is mandatory. ADR-009 (calibration discipline) applies.

> **"Dense backend. Minimal output. Clear decisions."**
> The five questions answered. The dealer flow simulator says BUY or SELL or NEUTRAL. The RR regime is HIGH or FAIR or LOW. The cascade trigger is CROSSED or NOT. Signals to the operator are categorical. Backend complexity is invisible above the surface.

---

## Prior Art and Methodological Divergence

v1 cited no external literature. v2 records:

| Concept | Standard reference | MERDIAN methodology |
|---|---|---|
| Per-strike GEX formula | `gamma × OI × spot² × 100` (SpotGamma, SqueezeMetrics convention) | Same. Verify in §3 sign audit. |
| Dealer-positioning sign flip | Calls = dealer-short = negative gamma; Puts = dealer-short = positive gamma (standard convention) | Verify in §3 audit. |
| Acceleration zone terminology | "Gamma desert" / "negative gamma cliff" in some literatures | MERDIAN uses "acceleration zone" matching source dashboard |
| Pin zone vs max pain | Max pain is OI-only; pin zone is GEX-weighted | MERDIAN uses GEX-weighted (more precise — captures dealer hedge force, not just contract count) |
| Realized vol annualisation | 252-trading-day convention | Same — √252 factor from intraday window |
| Implied vol source | ATM straddle for ATM IV; full-chain skew for surface analytics | MERDIAN uses ATM straddle for primary IV; chain skew is post-v2 scope |
| Vanna/Charm computation | Black-Scholes analytic Greeks at each strike, aggregated | Same — derived from `option_chain_snapshots` gamma/delta/theta |
| RR ratio thresholds | Practitioner convention varies (some use 1.0/0.7, others 1.2/0.85) | MERDIAN uses 1.2/0.85 matching source dashboard |

Phase 0a §3 sign audit catches inversions before downstream build.

---

## Consequences

**Positive:**

- Buyer-polarity intelligence operational from Phase 1, not deferred to Phase 3.
- Five-question operational framing makes "feature load-bearing?" test concrete.
- RR ratio (P7) is the single most impactful immediate addition — vol-pricing context is currently entirely absent.
- Phase 0 calibration discipline prevents wasted build on features that don't survive empirical check.
- Capital scaling roadmap unchanged but with explicit Phase 3 prerequisites (4 parallel tracks) named.
- Buyer/writer inversion is named as first-class architectural concept — eliminates v1's implicit category error.

**Negative:**

- Phase 0 delays first schema landing by ~3–4 sessions.
- v2 adds ~20 fields across `gamma_metrics`, one new table (`vol_analytics`), two views — schema bloat monitored.
- Per-cycle compute increases substantially (latency budget tracking mandatory per Operational Hygiene §1).
- Phase 3 prerequisites now explicit at 4 parallel tracks — capital-scaling roadmap timeline elongates.

**Net:** trade ~3–4 sessions of calibration for ~10–15 sessions of avoided wasted build. The buyer-polarity Phase 1 operational deployment alone justifies the v2 commitment; Phase 3 unlock is the strategic upside.

---

## What ADR-002 v2 does NOT decide

- Exact `lambda_score_pct` coefficient values (fit in Phase 0b)
- Specific PINNED threshold for `local_gex_cluster_cr` (Experiment 23)
- DTE force-multiplier curve shape (post Phase 1.5)
- Phase 3 specific trade structures (frozen until P1–P8 live + 4 parallel tracks complete)
- Vanna/charm specific Phase 3 gate thresholds (deferred until Phase 2 imminent)
- Realized-vol primary-window selection (15-min is default; revisit post-Phase 0b)

---

## Governance Quote

> *"Direction tells you which way to lean. Force tells you whether to bet. Vol-pricing tells you which premium-side to be on. Zones tell you where the physics actually lives. Positioning tells you what the market means even when price is lying. And the regime you're in right now is not the regime you'll be in at expiry — because the structure migrates and the second-order Greeks rewrite the rulebook."*

---

## Relationship to Other Documents

- **ADR-001** — Governs gate validity (stability + truth). Complementary: this ADR governs what the gamma layer should *compute*; ADR-001 governs how it should be *validated*.
- **ADR-007 (V18F ICT pivot)** — Orthogonal. ADR-007 governs signal-layer triggers (ICT). ADR-002 v2 governs structural intelligence layer (gamma + vol). Both apply concurrently. P5 PINNED integrates with ADR-007 signal stack via the buyer/writer polarity dispatch.
- **ADR-009 (calibration discipline)** — Invoked explicitly per Operational Hygiene §3 (shadow rollout). Every v2-consuming gate must satisfy ADR-009 shadow-vs-live calibration.
- **MERDIAN_Enhancement_Register** — ENH-80, ENH-81, ENH-82, ENH-83 carried from v1 with refined scope. **ENH-84** (vol_analytics + RR) new. **ENH-85** (vanna/charm Phase 3 prep) new.
- **GammaEngine_Master_V15.1 Appendix D** — Superseded by this ADR v2 across all gamma-layer principles. D.2 binary-regime gap → P5 PINNED. D's distance-from-flip gap → P1 zones. D's no-force gap → P2.
- **Source material** — Twitter screenshots from successful options writer (Session 12 Apr 28 multiple posts + Session 27 Apr 30 cascade-detection example "if 23719 breaks"). PDF article *"The real edge is building a framework that tells you why the move should happen before price gets there"* with positioning landscape + dealer flow + vol analytics + vanna panels. Internal Session 26 audit (Mon 2026-05-11) — 0/289 signals allowed on clean trend-down day — provides the operational case for v2 (vol-pricing + zone-aware gating + cascade detection would have changed the outcome).
- **MERDIAN_Documentation_Protocol_v4** — This document conforms.

---

*ADR-002 v2 — 2026-05-11 — Session 27 candidate. Full rewrite of ADR-002 v1 (Session 12, 2026-04-28). Six principles preserved; two new principles (P7 vol-pricing, P8 second-order Greeks); operational framing inverted to five-questions-led; buyer/writer polarity inversion named as first-class architectural concept; Positioning Landscape refined to five named scalars; expanded six-scenario dealer-flow simulator; new vol_analytics module; methodology requirements specified before build; Phase 0 calibration discipline introduced; capital-scaling roadmap preserved with refined Phase 3 prerequisites (four parallel tracks named).*
