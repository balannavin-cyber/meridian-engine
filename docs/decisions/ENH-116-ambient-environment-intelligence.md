# ENH-116 — Ambient Environment Intelligence (Regime-Aware Context Layer)

| Field | Value |
|---|---|
| **Status** | PROPOSED |
| **Priority** | **P2 — build-deferred, substrate-gated.** BLOCKED-BY: SENSEX backfill completion (S62) + `expiry_outcomes` retroactive seed. Sequenced AFTER S63 doc-close (does not jump the documentation queue). Not P0/P1 (display-not-gate, touches no live routing, nothing breaks without it); not P3 (the enabling substrate was built this session — it is the natural next major capability once the mechanical backfill lands). |
| **Date proposed** | 2026-07-01 (S62) |
| **Tier** | context layer (display-not-gate per ADR-002 v2 §D.19.3 GEX-as-context framing) |
| **Cadence** | post-market compute (daily) + pre-market relate (light) — NOT intraday |
| **Governance** | new post-market batch → inherits ADR-018 (systemd-supervised + recency-floor). M→V→S→P; ADR-009 holdout net-of-costs before any weight. |
| **Enabling substrate** | TD-S58-NEW-1 historical GEX + concentration backfill (S62) — regime trajectories are not computable without it |
| **Related** | ADR-002 v2 (P4 regime-velocity, P5 local-vs-aggregate), ADR-017 (P4 confluence-is-bidirectional), ADR-018 (supervision), ENH-115 (FII/DII source), ENH-SDM (display-first playbook) |

---

## Context

MERDIAN is a point-in-time structural sensor: net GEX now, pin now, flip now, dealer flow now.
Every primitive is present-tense. ADR-002 v2 P4 named the missing dimension — "the regime has
velocity, not just position" — but scoped velocity as a within-session derivative. This ENH extends
regime-velocity across **nested timescales**: not "how fast is GEX moving this hour" but "what has
the positioning regime been building toward across the cycle, and does today's open confirm or
contradict it."

The same live structural read means opposite things in different environments. A long-gamma
23,950–24,000 pin in a *trend-up* environment is a coiling continuation setup; the identical pin in a
*distribution* environment is a mean-reversion magnet inside a range that wants to resolve lower.
MERDIAN today reads that pin **unconditionally**. This ENH gives it the ambient prior.

**Why buildable now and not before:** regime trajectories require history to diff against. The S62
GEX + concentration backfill (full-window, both symbols) is that history. This ENH is the assembly of
primitives MERDIAN already built (GEX history, concentration, dealer flow, breadth, the ENH-115
participant source) into the one dimension ADR-002 named but never reached.

---

## Architecture: three clocks + four lenses + post/pre split

### The post-market / pre-market separation (operator refinement S62)

All heavy work is backward-looking and settled by close. It must NOT sit on the open critical path.

- **Post-market compiler** (`compile_market_environment_local.py`) — runs after settlement, computes
  the full ambient state from now-complete data, writes tomorrow's `market_environment_snapshots`
  row. No time pressure; all-night re-run window; easy to supervise per ADR-018. On expiry days it
  ALSO appends the labeled `expiry_outcomes` event (see Phase A).
- **Pre-market reconciler** (`relate_ambient_to_open_local.py`) — tiny, fast, single responsibility:
  take last night's settled ambient row, join it to this morning's opening structure, emit the
  **session prior**. Milliseconds, no heavy compute, nothing that can hang the open. Mirrors the
  deliberate minimalism of `capture_premarket_0908.py`.

**Principle: compute at rest, relate at open.**

### The three clocks

- **Clock 1 — Positioning Regime (monthly/multi-week, computed daily).** Slow trajectory of dealer
  positioning across the current + prior expiry cycle.
- **Clock 2 — Cycle-So-Far (weekly/expiry-cycle, computed daily).** OI accumulation asymmetry through
  the current cycle + participant deltas leading into today. (OI can grow 5–10× Mon→Thu per ADR-002.)
- **Clock 3 — Session Open (intraday).** MERDIAN's existing live pin/flip/accel/dealer-flow read.
  UNCHANGED — now *interpreted against* Clocks 1+2 rather than in isolation.

### The four regime lenses (independent, cross-checking)

Each lens produces a regime read; their **pairwise divergences** are first-class outputs. Two
uncorrelated reads that can confirm or contradict is worth more than either alone.

1. **Gamma-positioning lens** — GEX regime persistence (fraction of last N sessions net-long-gamma),
   max-γ-strike drift, concentration trend (the S62-backfilled column's *first derivative across
   days* — literally did not exist before this session).
2. **Breadth lens** (operator-elevated S62) — constituent + overall breadth *trajectory* from
   `market_breadth_intraday` / `weighted_constituent_breadth_snapshots` / WCB composite: 5d/20d slopes
   of WCB, %>DMA, A/D. The **price-vs-breadth divergence** across the cycle is a top-tier regime tell,
   independent of gamma. Gamma = mechanical cage; breadth = fundamental pressure. When they agree the
   pin is fortress-grade; when they diverge the pin holds until it violently doesn't.
3. **Cycle-OI / participant lens** — call/put OI build asymmetry through the cycle + ENH-115 FII/DII/
   Pro deltas leading into today. EOD/daily regime tilt, NEVER an intraday trigger (per ENH-115).
4. **Macro-context lens** (operator-added S62, extensible) — cross-asset backdrop: USDINR, crude
   (Brent/WTI), gold, and slot for rates/global. Daily. A rupee breaking down + crude spiking is a
   risk-off tilt that reprices an index pin's break-direction odds. Explicitly a slow tilt, held to
   the same holdout bar; wired as one tilt among several, never standalone.

### The reconciliation layer (the actual product)

The value is the **single ambient statement** the four lenses reconcile into:

- **All lenses aligned** → high conviction. "Distribution monthly + put-walls building all cycle +
  narrowing breadth + FII shorts rising + risk-off macro + long-gamma pin at open = mean-revert inside
  the cage, breaks resolve down, break-odds elevated vs neutral."
- **Lenses diverge** → the most valuable flag. Monthly says distribution but cycle shows call-walls
  building and breadth broadening → regime may be turning → reduce conviction, the room is changing.
  This is ADR-017 P4 (confluence is bidirectional — confirms OR invalidates) generalized from
  within-session to across-cycle.

---

## The learning phase — expiry memory (three phases, N-gated)

The prize: detecting patterns from *past weekly/monthly expiries* — MERDIAN building a **memory** of
how expiries resolve under conditions like today's. Built as a labeled event-store queried for base
rates, NOT a prematurely-trained model.

- **Phase A (now/near) — the expiry event-store.** New `expiry_outcomes` table: one labeled row per
  weekly/monthly expiry capturing (a) the **ambient state going in** (Clock 1/2/3 reconciliation as of
  expiry morning) and (b) the **outcome** (pinned/broke, direction, magnitude, settlement vs open pin,
  accel-zone trigger). Seed retroactively from ~14 months of backfilled GEX + breadth + live-sourced
  expiry days. **Measure-layer only — it stores, it does not predict.**
- **Phase B (later) — the base-rate engine.** Conditional base rates over the store: "past expiries
  matching today (long-gamma-pinned + distribution-monthly + narrowing breadth + rising FII shorts)
  held 61%, broke down 31%, broke up 8%, median settlement −0.6% from open pin." Interpretable,
  falsifiable, degrades gracefully at small N ("weak prior, 6 cases"). No black box.
- **Phase C (much later, maybe never) — analog retrieval.** Only once base rates are stable:
  nearest-neighbor over the ambient feature vector ("5 most similar past expiries, how they resolved")
  or archetype clustering. Operator-facing, PROPOSES analogs, NEVER gates. The ENH-97 Phase-0b FAIL
  and retired SMDM are the reason for this discipline.

**Design principle: store the labeled event now, extract intelligence later, never let extraction
outrun sample size.** Not a predictor — a memory; intelligence is a query over memory that grows with N.

---

## View / Console Design (ADR-017 governed)

For an operator console the **view is the product** — a PM consumes a reconciled verdict with receipts
one click away, never the raw lens rows. ADR-017 discipline applies: Marketview = decisions, silence =
healthy, signal = loud, confluence is bidirectional. The ambient view sits **above** the existing live
structural cards, because the live pin/flip/accel read means nothing until the room is known.

### Tier 1 — The Ambient Verdict (headline, always visible, top of console)
One line, computed post-market and related at open: regime + alignment + session prior in plain
language.
> *"DISTRIBUTION · lenses ALIGNED · pin-hold base rate 61% (N=23) · breaks resolve DOWN · break-odds
> elevated vs neutral."*
It is a **headline, not a panel** — it reframes everything below it. This is the single line a PM needs
before anything else on the screen.

### Tier 2 — The Four-Lens Strip (the receipts, one glance below the verdict)
Four compact cells, each showing its lens's regime read **and its agreement/disagreement with the
others**. The critical visual is **divergence, not values** — state and color, not numbers:
- **Gamma-positioning:** `PERSISTENT LONG-γ` + max-γ drift arrow.
- **Breadth:** `NARROWING ⚠ diverging from gamma` — the flag that matters most.
- **Participant / OI:** `FII shorts rising · call-walls building` (tilt direction).
- **Macro:** `RISK-OFF · INR weak, crude up` (backdrop).
The strip's job is to make **alignment vs divergence** legible in half a second. All-aligned = trust the
cage. One-diverging = the room is changing, reduce conviction. (ADR-017 P4 made visual.)

### Tier 3 — The Expiry Memory panel (expiry days / on demand — the Phase-B/C payoff)
The capability that separates MERDIAN from every other GEX dashboard. A distribution readout:
> *"Past expiries matching today's ambient (N=23): held 61% · broke down 31% · broke up 8% · median
> settlement −0.6% from open pin."*
Plus a **"show analogs" affordance** (Phase C): the 5 most similar past expiries with dates and how each
resolved — a desk trusts a base rate far more when it can click through to the specific precedents.

### Salience rule (ADR-017 P3)
The console is **boring on aligned days and loud on divergent ones**. When all four lenses align, the
strip is muted — no news, trust the structure. When a lens **diverges**, its cell lights up and the
verdict line carries the caveat. A divergent day is exactly when a PM's default read is most likely
wrong — so that is when the console must interrupt.

### Explicitly NOT shown (ADR-017 P1 three-filter)
No raw slopes or per-lens numeric tables on the face (they live in a drill-down modal). No intraday
flicker of the slow lenses — they are daily; ticking them would imply false precision and violate the
not-intraday rule. The headline carries the verdict; the numbers are one click away, never on top.



### `market_environment_snapshots` (post-market compiler output; one row per symbol per date)

```sql
CREATE TABLE IF NOT EXISTS public.market_environment_snapshots (
    id                         bigserial PRIMARY KEY,
    symbol                     text NOT NULL,
    as_of_date                 date NOT NULL,        -- the settled session this summarizes
    for_session_date           date NOT NULL,        -- the NEXT session this contexts

    -- Lens 1: gamma-positioning
    gex_regime_persistence_20d numeric,              -- frac of last 20 sessions net-long-gamma [0..1]
    max_gamma_strike_drift_5d  numeric,              -- signed pts/session drift of max-γ strike
    concentration_trend_5d     numeric,              -- signed slope of daily gamma_concentration
    net_gex_regime             text,                 -- POSITIVE_γ | NEGATIVE_γ | MIXED

    -- Lens 2: breadth trajectory
    wcb_slope_5d               numeric,
    pct_above_20dma_slope_5d   numeric,
    price_vs_breadth_div       text,                 -- CONFIRM | BEARISH_DIV | BULLISH_DIV | NEUTRAL

    -- Lens 3: cycle-OI / participant (ENH-115 inputs; NULL until that source is supervised)
    cycle_oi_call_put_asym     numeric,              -- +ve = call-side (ceiling) building
    fii_index_fut_ls_delta_5d  numeric,
    pro_options_imbalance      numeric,

    -- Lens 4: macro context (extensible; NULL until sources wired)
    usdinr_trend_5d            numeric,
    crude_trend_5d             numeric,
    gold_trend_5d              numeric,
    macro_tilt                 text,                 -- RISK_ON | RISK_OFF | NEUTRAL

    -- Reconciliation
    ambient_regime             text,                 -- TREND_UP|TREND_DOWN|RANGE|DISTRIBUTION|ACCUMULATION|UNSTABLE
    lens_alignment             text,                 -- ALIGNED | DIVERGENT
    session_prior              text,                 -- structured prose statement (pre-market reconciler fills relate-part)
    regime_conditional_note    text,                 -- Phase-B base-rate string when available

    source                     text NOT NULL DEFAULT 'ambient_compiler_s62',
    created_at                 timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uniq_env_row UNIQUE (symbol, for_session_date, source)
);
CREATE INDEX IF NOT EXISTS idx_env_for_session ON public.market_environment_snapshots (for_session_date);
```

### `expiry_outcomes` (Phase-A labeled event-store; one row per expiry)

```sql
CREATE TABLE IF NOT EXISTS public.expiry_outcomes (
    id                       bigserial PRIMARY KEY,
    symbol                   text NOT NULL,
    expiry_date              date NOT NULL,
    expiry_type              text NOT NULL,          -- WEEKLY | MONTHLY

    -- ambient state going IN (snapshot of the four lenses as of expiry morning)
    ambient_regime           text,
    lens_alignment           text,
    gex_regime_persistence   numeric,
    concentration_at_open     numeric,
    breadth_div_at_open      text,
    participant_tilt         text,
    macro_tilt               text,
    open_pin_strike          numeric,
    open_flip_level          numeric,
    open_pin_risk_score      numeric,

    -- OUTCOME (labeled at settlement)
    resolved                 text,                   -- PINNED | BROKE_UP | BROKE_DOWN
    settlement_vs_open_pin_pct numeric,
    intraday_range_pct       numeric,
    accel_zone_triggered     boolean,

    source                   text NOT NULL DEFAULT 'expiry_memory_s62',
    created_at               timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_expiry_type CHECK (expiry_type IN ('WEEKLY','MONTHLY')),
    CONSTRAINT chk_resolved CHECK (resolved IN ('PINNED','BROKE_UP','BROKE_DOWN')),
    CONSTRAINT uniq_expiry_event UNIQUE (symbol, expiry_date, source)
);
CREATE INDEX IF NOT EXISTS idx_expiry_regime ON public.expiry_outcomes (symbol, ambient_regime, resolved);
```

---

## M→V→S→P validation plan

- **Measure.** Build both writers. `market_environment_snapshots` accrues a forward cohort;
  `expiry_outcomes` is seeded retroactively from S62 backfilled history (~14 months, ~60 weekly + ~14
  monthly expiries per symbol) then accrues forward. DISPLAY-ONLY on the Marketview console (ADR-017)
  as a new top ambient panel. **Touches no signal routing.**
- **Validate.** ADR-009 holdout: split the seeded expiry cohort, compute regime-conditional pin-hold /
  break-direction base rates on train, confirm they hold on the out-of-sample holdout **net of costs**.
  Each lens validated independently before its divergence flags are trusted. B29 cohort-translation:
  re-validate before any promotion.
- **Shadow.** Once base rates hold on holdout, run the ambient prior in shadow alongside live signals —
  log what it *would* have advised vs what happened, accruing a live forward cohort. Still display-not-
  gate.
- **Promote.** ONLY if the shadow cohort proves the ambient prior adds edge net-of-costs at N≥30 per
  regime cell does it earn any routing weight — and even then as a position-size modifier, never a
  hard gate. Macro + participant lenses held to the same bar individually.

**Non-negotiable:** the environment layer's first year is a display + a forward cohort. The seductive
failure — build classifier, see it "work" on recent days, wire it to routing — is the ENH-97 Phase-0b
graveyard. Patience is the whole difference between a context engine and a curve-fit.

---

## Build sequence (proposed)

1. **Schemas** — `market_environment_snapshots` + `expiry_outcomes` DDL (review → Supabase editor).
2. **`compile_market_environment_local.py`** — post-market compiler, Lenses 1+2 first (gamma + breadth;
   both have live data). Lenses 3+4 write NULL until their sources are supervised.
3. **Seed `expiry_outcomes`** retroactively from S62 backfilled history (Measure artifact).
4. **`relate_ambient_to_open_local.py`** — pre-market reconciler (light join → session prior).
5. **Marketview ambient panel** (ADR-017) — display-first headline above the live structural read.
6. **ENH-115 participant source** (Lens 3) — supervised per ADR-018; wired as tilt.
7. **Macro source** (Lens 4) — USDINR/crude/gold daily; wired as tilt.
8. **Phase-B base-rate engine** — conditional base rates over `expiry_outcomes` once N supports it.
9. **Phase-C analog retrieval** — deferred; operator-facing; never a gate.

## Explicitly NOT in scope
- No intraday wiring of any slow lens (participant/macro/breadth-trajectory are daily context).
- No signal-routing gate until holdout + shadow prove edge net-of-costs (ADR-009 / B29).
- No premature ML — Phase C is analog retrieval at stable N, operator-facing, deferred.
- No new pre-open critical-path compute — heavy work is post-market by construction.

## Register integration (S63 doc-close)
Part 1 status-table row: `| ENH-116 | Ambient Environment Intelligence | context | **PROPOSED (P2)** |`.
Scope row bump to ENH-01..ENH-116. Change Log entry. Cross-ref ADR-002 v2 (P4/P5), ADR-017 (P4/P3/P1),
ADR-018, ENH-115, ENH-SDM. This is a SEPARATE doc (`ENH-116-ambient-environment-intelligence.md`) plus
the register row — mirrors the ADR/CASE separate-doc convention.

## Open questions for operator
- Weekly-vs-monthly expiry: separate `expiry_outcomes` regimes, or pooled with `expiry_type` as a
  feature? (Leaning pooled-with-feature; monthly N is small.)
- Macro data source: which feed for USDINR/crude/gold EOD (Dhan? separate)? — determines Lens-4 timing.
- Is there a fifth lens (rates term-structure, global indices overnight) to reserve schema slots for now?
