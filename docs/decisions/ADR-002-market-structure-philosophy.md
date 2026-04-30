# ADR-002 — Market Structure Philosophy: force over direction, zones over points, scale over time

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-04-28 |
| **Session** | Session 12 — gamma dashboard analysis + philosophy formalisation |
| **Supersedes** | None — companion to ADR-001 |
| **Related ENH** | ENH-75 · ENH-76 · ENH-77 · ENH-78 · ENH-79 · ENH-80 (proposed) · ENH-81 (proposed) |
| **Related TD** | Appendix D (GammaEngine_Master_V15.1) — binary regime assumption gap |
| **Triggered by** | Analysis of external gamma dashboard built by successful options writer. Session 12. |

---

## Context

Session 12 analysed a production gamma dashboard built by an options writer with a multi-year live track record. The comparison against MERDIAN's Gamma Engine surfaced a set of architectural and philosophical gaps that are not bugs — they are missing conceptual layers. This ADR formalises those principles as settled architectural commitments so they are not rediscovered piecemeal in future sessions.

The six structural principles below were derived from three sources:
1. The options writer's dashboard — what a practitioner with real P&L stakes chose to build and display.
2. MERDIAN's Appendix D assumption register — the gaps already documented but not yet addressed.
3. The capital scaling reality — how the strategy must evolve as AUM grows.

These are not feature requests. They are the philosophical axioms that should govern every design decision in the gamma layer and signal engine going forward.

---

## The Six Principles

### P1 — Markets are zones, not points

The gamma flip is not a strike. It is a zone where dealer behaviour changes character. The pin is not a strike. It is a cluster of strikes where gravitational force is concentrated. Acceleration does not begin at one number — it builds across a range of strikes as multiple writers are forced to hedge simultaneously.

**What this means in practice:** Every structural feature — flip level, pin zone, acceleration zone, max gamma — should be stored and displayed as a zone `(level, lower_bound, upper_bound)`, not as a single scalar. A flip at 24,301 is meaningless without knowing that the zone where dealer behaviour actually transitions spans roughly 24,250–24,350. Treating it as a point produces false precision and wrong trade decisions at the boundary.

**Current MERDIAN gap:** `flip_level`, `gamma_concentration` stored as scalars. No zone widths computed or stored anywhere.

---

### P2 — Direction is minimum viable information. Force is the actual edge.

Knowing that dealers will buy is not an edge. Knowing they must buy ₹14,467 Cr if spot moves +1% — that is an edge. Force tells you whether a support level will hold or will be steamrolled. Without force, every structural level looks equally significant. With force, you know which ones have mechanical backing sufficient to matter at your trade size.

The options writer's dealer flow simulator answers exactly this: for a given spot move, how many Crore of futures must dealers transact to rehedge? This is not a probabilistic estimate — it is a deterministic calculation derived from the GEX gradient (delta of net GEX with respect to spot). The number changes the quality of every trade decision.

**What this means in practice:** The gamma engine should output a force field, not just a regime label. For every 0.5% spot move scenario (up and down), the engine should compute estimated dealer hedge flow in Cr. This becomes an input to position sizing — a high-force support level warrants more size than a low-force one.

**Current MERDIAN gap:** No dealer flow magnitude computed anywhere. `gamma_regime = LONG_GAMMA` tells you direction of dampening. It says nothing about magnitude.

---

### P3 — Know where sellers panic

Options writers (short gamma) are hedged and comfortable as long as spot stays within their expected range. The flip is where that comfort zone ends. Above the flip, short-call writers face unlimited delta exposure and must buy futures to hedge as spot rises — which pushes spot higher, which forces more buying. This is not a probabilistic signal. It is a deterministic cascade triggered by trapped positioning.

The edge is knowing: (a) where the trapped short-gamma positioning is concentrated, (b) how large it is in Crore, and (c) how far spot is from that trigger. Once the trigger fires, the cascade is largely mechanical. This is the highest-quality directional signal available in the options market — not a prediction, but a physics equation.

**What this means in practice:** MERDIAN needs the full per-strike GEX histogram stored as a time-series (see Section: GEX Weekly Storage). The acceleration zone (strikes above the flip where short-gamma sellers are trapped) should be a first-class output of the gamma engine, not a derived inference. The magnitude of trapped positioning at the flip — not just its existence — determines whether the cascade, if triggered, is a 50-point move or a 300-point move.

**Current MERDIAN gap:** `flip_level` is stored. The magnitude of trapped positioning at the flip is not computed. No per-strike GEX time-series exists. Acceleration zone is not a named engine output.

---

### P4 — The regime has velocity, not just position

A GEX regime snapshot is a location reading. The trajectory of that regime — which direction is it moving and how fast — is a separate and often more valuable signal.

Max gamma migrating from 24,600 to 24,200 over a session tells you the gravitational centre is drifting down. Net GEX falling from −976 Cr to −14,323 Cr tells you the force is accelerating, not merely present. A regime moving toward spot is materially different from a regime spot is already inside. The direction of the GEX structure is itself a trading signal — independent of what the current snapshot says.

**What this means in practice:** The gamma engine should compute and store `max_gamma_strike_delta` (change in max gamma strike vs N periods ago) and `gex_velocity` (rate of change of net GEX). These become features in the signal engine alongside the static regime. A falling max gamma strike combined with bearish directional bias is a stronger signal than either alone.

**Current MERDIAN gap:** No historical GEX fields computed. All gamma features are point-in-time snapshots with no derivative terms.

---

### P5 — Local context beats aggregate signal

Net GEX can be negative (SHORT_GAMMA — dealers amplify moves; bearish aggregate regime) while the local GEX cluster around current spot is deeply positive (pin gravity active right where price lives). These are simultaneously true and point in opposite directions.

The market does not respond to the aggregate net GEX number. It responds to what is happening at the strikes nearest current spot. A session where net GEX is −1,000 Cr but spot sits inside a +5,000 Cr local positive cluster will behave like a pinned session — not like a SHORT_GAMMA amplification session. MERDIAN's binary LONG/SHORT regime based on net GEX sign misclassifies this entire session type.

**What this means in practice:** The gamma regime requires a third state: `PINNED`. Criteria: spot is within a positive local GEX cluster of sufficient magnitude, regardless of net GEX sign. The threshold for "sufficient magnitude" must be determined empirically — this is Experiment 23 (designed but not yet run). Until Exp 23 is run, the binary regime remains in place with this gap explicitly flagged.

**Current MERDIAN gap:** Documented in GammaEngine_Master_V15.1 Appendix D (D.2): "Binary LONG/SHORT regime based on net_gex sign. No consideration of distance from flip." Experiment 23 is the validation path. The PINNED state is the architectural response.

---

### P6 — DTE is a force multiplier, not a risk flag

The same spot at 24,000, with the same GEX of X Crore, on DTE=5 vs DTE=1 is a physically different situation. On DTE=5, the gamma structure is thick and slow — large OI, gradual hedging needs, wide dealer tolerance bands. On DTE=1, gamma is near-infinite at ATM — tiny spot moves require massive delta hedges, cascade probability is non-linear, the force equation is categorically different.

MERDIAN currently uses DTE as a binary execution gate (`min_dte_threshold = 2` — do not trade below 2 DTE). That is the right risk rule for naked options buying. But DTE should also appear in the force calculation: the same GEX magnitude means more force as expiry approaches. The structural signals P1–P5 are all DTE-dependent in magnitude even when their direction is unchanged.

**What this means in practice:** DTE should enter the gamma engine as a continuous modifier on force outputs, not only as a binary gate on execution. The dealer flow simulator (P2) should output DTE-adjusted flow Crore. The force multiplier curve should be estimated from historical data (this is a future experiment).

**Current MERDIAN gap:** DTE appears only in signal engine execution gating. Not present in gamma metrics as a force modifier. The `dte` field exists in `gamma_metrics` DDL — it is stored but not used beyond the gate.

---

## Capital Scaling Roadmap

MERDIAN's strategy must evolve as AUM grows. This is not optional — it is a structural constraint imposed by market microstructure. The roadmap below is the architectural commitment for how the strategy layer expands. Signal engine design at every phase must be forward-compatible with the next phase.

### Phase 1 — Directional naked options buying (current)

**Strategy:** BUY_CE / BUY_PE. Long options, defined risk (premium paid), unlimited upside.

**Capacity ceiling:** Approximately 25,000 lots on any single name before market impact becomes material. At this scale, bid-ask spread width and slippage on entry/exit consume a meaningful fraction of edge. Execution quality degrades non-linearly beyond this threshold.

**What MERDIAN needs here:** Direction signal (existing), force context (P2 — to size correctly relative to structural backing), zone awareness (P1 — to set strikes intelligently), local regime (P5 — to avoid entering on a structurally misclassified session).

### Phase 2 — Debit spreads

**Strategy:** Bull call spreads / bear put spreads. Defined risk, defined reward. Reduced premium outlay vs naked, reduced upside — but slippage spreads across two legs in the same direction, and bid-ask width impact is partially offset by the credit leg.

**Trigger:** When naked options approach the ~25,000 lot capacity ceiling, or when IV is elevated enough that buying naked premium is structurally unfavourable.

**What MERDIAN needs additionally:** Strike selection engine — where to put the long leg (near ATM, structural level), where to put the short leg (at the first resistance zone, pin zone upper bound). P1 (zones) becomes directly load-bearing: the short strike of a spread should land at a structural resistance, not an arbitrary round number.

### Phase 3 — Defined-risk selling (credit strategies)

**Strategy:** Short options with defined risk — credit spreads, iron condors, ratio spreads with defined tail exposure. NOT naked short options.

**Trigger:** When total AUM makes the risk/reward profile of defined-risk selling superior to directional buying, and when MERDIAN has sufficient structural intelligence to know where to sell safely.

**What MERDIAN needs additionally:** All six principles (P1–P6) become mandatory, not optional. An options seller lives and dies by knowing where the pin is (P1), how much force is present (P2), where sellers are trapped and cascades originate (P3), which direction the structure is migrating (P4), what the local vs aggregate regime says about where it is safe to sell (P5), and how DTE changes the force profile of any short position (P6). The gamma dashboard analysed in Session 12 is a Phase 3 tool — built by a seller who needed all of this to survive. MERDIAN at Phase 3 must have equivalent structural intelligence as a minimum viable requirement.

**Important:** Defined-risk selling is NOT a complexity jump from directional buying — it is a capability jump that requires the full GEX structure intelligence described in this ADR. Do not attempt Phase 3 until Experiments 23, and the per-strike GEX time-series (see below), are live and validated.

---

## GEX Weekly Time-Series: Decision to Store

**Decision: Store per-strike GEX at the same 5-minute cadence as the existing options ingestion pipeline, for the full duration of each weekly/monthly expiry cycle.**

### Rationale

The per-strike GEX time-series is the foundational data layer for Principles P2, P3, P4, and P5. Without it:
- Force calculations (P2) can only be done on the current snapshot — no context.
- Acceleration zone magnitude (P3) is computable but not stored for historical analysis or experiments.
- Regime velocity (P4) is impossible — there is no prior state to diff against.
- Local vs net GEX divergence (P5) — specifically, how often it occurs and what the outcome is — cannot be empirically tested. Experiment 23 requires this data.

OI accumulates through the week. The GEX at any strike on Monday morning is structurally different from the GEX at the same strike on Wednesday afternoon. This is not a marginal difference — OI can increase 5–10x from Monday to Thursday on heavily traded strikes. The structural intelligence of the system is proportional to how much of this accumulation trajectory it can see. A single snapshot at session start misses the entire build.

The data is nearly free. `option_chain_snapshots` already stores per-strike gamma and OI at every 5-minute run. Per-strike GEX is `gamma × OI × spot²`. The aggregation step is a single additional compute pass, not new data collection.

### Schema (proposed — ENH-80)

```sql
CREATE TABLE IF NOT EXISTS public.gex_strike_snapshots (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid NOT NULL,          -- matches gamma_metrics.run_id
    symbol          text NOT NULL,
    ts              timestamptz NOT NULL,
    expiry_date     date NOT NULL,
    dte             integer NOT NULL,
    strike          numeric NOT NULL,
    gex_cr          numeric,               -- gamma × OI × spot² / 1e7 (Crore)
    oi              bigint,
    gamma           numeric,
    spot            numeric,
    is_local_max    boolean,               -- true if local GEX maximum (pin candidate)
    is_flip_zone    boolean,               -- true if GEX sign change at this strike
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_gss_symbol_ts   ON public.gex_strike_snapshots (symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_gss_symbol_exp  ON public.gex_strike_snapshots (symbol, expiry_date, ts DESC);
CREATE INDEX IF NOT EXISTS idx_gss_run_id      ON public.gex_strike_snapshots (run_id);
```

### Derived metrics (stored in gamma_metrics, ENH-81 proposed)

| Field | Definition |
|---|---|
| `max_gamma_strike` | Strike with highest absolute GEX at this snapshot |
| `max_gamma_strike_delta` | Change in max_gamma_strike vs prior snapshot (points) |
| `gex_velocity` | Change in net_gex vs prior snapshot (Cr/run) |
| `local_gex_cluster` | Sum of positive GEX within ±200 pts of spot (Cr) |
| `accel_zone_lower` | Lower bound of acceleration zone (first strike above flip with negative GEX) |
| `accel_zone_upper` | Upper bound of acceleration zone (last strike with sustained negative GEX before GEX flattens) |
| `dealer_flow_down_05` | Dealer Cr flow if spot moves −0.5% (negative = sell) |
| `dealer_flow_up_05`  | Dealer Cr flow if spot moves +0.5% (positive = buy) |
| `dealer_flow_down_10` | Dealer Cr flow if spot moves −1.0% |
| `dealer_flow_up_10`  | Dealer Cr flow if spot moves +1.0% |

---

## Build implications — proposed ENH items

| Principle | Gap | Proposed ENH | Priority |
|---|---|---|---|
| P1 — Zones not points | Flip/pin stored as scalars | ENH-80: Add zone bounds to gamma_metrics. Compute lower/upper for flip zone and pin zone. | Medium |
| P2 — Force not direction | No dealer flow magnitude | ENH-81: Dealer flow simulator in gamma engine. Four scenarios (±0.5%, ±1.0%). Stored in gamma_metrics. | High |
| P3 — Trapped seller positioning | No per-strike GEX time-series | ENH-80: `gex_strike_snapshots` table (schema above). Populate from existing option_chain_snapshots compute pass. | High |
| P4 — Regime velocity | No historical GEX derivative terms | ENH-81: Add `max_gamma_strike_delta` and `gex_velocity` to gamma_metrics. Requires ENH-80 first (needs prior row). | Medium |
| P5 — Local vs net divergence | Binary LONG/SHORT regime | Experiment 23 first. ENH-82 (proposed): PINNED regime state. Post-Exp 23 validation. | High (Exp first) |
| P6 — DTE force multiplier | DTE not in force calculation | ENH-83 (proposed): DTE-adjusted dealer flow output. Post Phase 1.5. | Low — future |
| Capital scaling — Phase 2 | No spread strike selection | Phase 5 per roadmap — do not build ahead of time | Frozen |
| Capital scaling — Phase 3 | Full GEX structure needed | Blocked until P1–P5 all implemented and validated live | Frozen |
| GEX weekly storage | No per-strike time-series | ENH-80 (same as P3) | High |

---

## Consequences

**Positive:**
- Every future gamma engine design decision has a philosophical anchor. P1–P6 are the checklist: does this feature tell us something about zones (P1), force (P2), trapped positioning (P3), regime velocity (P4), local vs aggregate context (P5), or DTE-adjusted force (P6)? If not, it probably isn't load-bearing.
- The capital scaling roadmap is explicit and settled. Phase 3 design work cannot start without Phase 1.5 and the full GEX structure layer (ENH-80/81/82) live and validated. This prevents premature complexity.
- Experiment 23 is now unambiguously the next research priority after ENH-75/76/77 build work. It is the empirical validation of P5 and the prerequisite for ENH-82.
- The GEX weekly time-series decision is made — not deferred as a "nice to have." Storage cost is negligible; research and signal value is high.

**Negative:**
- ENH-80/81 add compute cost to the 5-minute runner. Per-strike GEX across ~100 strikes is ~100 rows per run per symbol. At 78 runs/day × 2 symbols × ~100 rows = ~15,600 rows/day. Manageable, but Supabase write budget should be monitored.
- The PINNED regime (P5/ENH-82) cannot be implemented until Experiment 23 is run and the threshold is empirically set. Operating on the binary regime in the interim means the known misclassification risk persists.
- Phase 3 (defined-risk selling) is explicitly locked behind multiple gates. This is correct — but it means the capital scaling roadmap has a hard sequencing constraint that cannot be accelerated by skipping validation steps.

---

## What this ADR does NOT decide

- Specific thresholds for what constitutes a "positive local GEX cluster" sufficient for PINNED regime. That is Experiment 23's output.
- The DTE force multiplier curve shape (P6). That requires historical data and a future experiment.
- Spread strike selection logic (Phase 2). Frozen until Phase 5.
- Any specific trade structure for defined-risk selling (Phase 3). Frozen until P1–P5 are live and validated.

---

## Governance language

> *"Direction tells you which way to lean. Force tells you whether to bet. Zones tell you where the physics actually lives. And the regime you're in right now is not the regime you'll be in at expiry — because the structure migrates."*

---

## Relationship to other documents

- **ADR-001:** Governs gate validity (stability + truth). This ADR governs what the gamma layer should *compute*, not how it should be *validated*. Complementary.
- **GammaEngine_Master_V15.1 Appendix D:** The assumption register. P5 directly addresses D.2 (binary regime). P6 directly addresses the DTE gate assumption. P2 addresses the absence of force magnitude. This ADR is the committed architectural response to the gaps Appendix D documented as "validation required."
- **MERDIAN_Enhancement_Register:** ENH-80/81/82/83 to be added. Sequencing: ENH-75 (live detection) → ENH-80 (per-strike GEX table) → ENH-81 (force metrics) → Exp 23 → ENH-82 (PINNED regime) → ENH-83 (DTE multiplier, Phase 1.5+).

---

*ADR-002 — 2026-04-28 — Session 12. Market structure philosophy formalised from gamma dashboard analysis. Six principles, capital scaling roadmap, and GEX weekly storage decision settled.*
