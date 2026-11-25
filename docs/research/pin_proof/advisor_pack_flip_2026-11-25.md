# MERIDIAN advisor pack: the Flip, its dependencies, and the dealer-side study

**Prepared:** Wed 25 Nov 2026, pin lane (MR-PIN3), for the outside advisor.
**Purpose:** the three things the advisor asked for before judging whether versioned isolation (the advisor's Option D) is feasible: the dependency boundary of the legacy flip block, the Board Flip's definition, and the P2 methodology.

## 0. How to read this pack

- **Source.** Code and SQL are quoted from the engine repository, `main` at commit `934fe44` (24 Nov 2026), read on 25 Nov. P2 is quoted from its design and result documents in the same repository.
- **Not verified.** That the views live in the database match the repository files byte for byte. That the deployed Board is built from the Board source tree that was searched.
- **Status.** Nothing described as "proposed" or "draft" is built or authorised. The operator has not ruled on scope.
- **Corrections to the earlier note the advisor saw.** Two, both in section 3: the Board Flip is not independent of vendor gamma, and "three of five gates failed" needs its detail. One in section 5: the "23 of 340" line was incomplete.

---

## 1. ADR-033 and the proposed change: where it stands

**ADR-033 does not exist yet.** The engine stream is drafting it. What exists is a draft rule for the corrected strike map, version 0.2, quoted below as the engine wrote it. It is not final.

> **G2 per-strike exposure (draft v0.2).** For one run with spot S > 0, and each strike K > 0, using the raw chain rows:
> 1. **Leg OI.** OI_c and OI_p are the sums of oi over that leg's rows; a missing or non-positive oi counts as 0.
> 2. **Leg gamma.** g_c and g_p are the largest vendor gamma > 0 among that leg's rows. If no row has gamma > 0, the leg has no gamma.
> 3. **Guard, per leg, before averaging.** If |K − S| / S > 0.05 and the leg's gamma > 5e-5, the leg has no gamma.
> 4. **Strike gamma.** gamma_strike = (g_c + g_p) / 2 when both legs have gamma; the one that has it when only one does; none otherwise.
> 5. **Exposure.** gex_cr(K) = gamma_strike × (OI_c − OI_p) × S² / 1e7, in Crore. If gamma_strike is none, gex_cr(K) = 0.
> 6. **Map membership.** K is in the map when at least one leg has gamma at step 2 and OI_c + OI_p > 0. Its value may be exactly 0, and it stays in the map.
> 7. **Derived.** net_gex = sum of the map; gamma_concentration = max |v| / Σ |v|. Flip, regime, max-gamma strike, expansion and pin-risk functions are unchanged and read this map.
> 8. **Stored.** gex_cr is the step-5 value; gamma_strike is the step-4 value (NULL when none); gamma_call and gamma_put are unchanged.

**Step 7 is the point in dispute.** As drafted, the corrected map would be fed into the unchanged legacy flip, regime, expansion and pin-score functions. Three scopes are on the table:

| Scope | What it does | Status |
|---|---|---|
| A (engine draft) | Legacy functions read the corrected map; one break date in all series | Drafted, on hold |
| B | Corrected map for exposure, net and concentration; legacy functions stay on the old map | Withdrawn by the pin lane: one stored row would mix a new net with an old regime |
| D (advisor) | Legacy block untouched in its own columns; corrected map written to new versioned columns and views; no flip promoted until validated | Under consideration; feasibility not yet put to the engine |

**Gross pin.** Separate from all of this. It is gamma_strike × (OI_c + OI_p) × S² / 1e7 within 5 % of spot, largest value wins. It needs no sign convention. A live view exists (`v_gex_strike_rank_gross`), nothing on the Board reads it yet, and a daily forward monitor starts 25 Nov.

---

## 2. Dependency boundary of the legacy flip block

### 2.1 The code, verbatim (`merdian_compute/gamma.py`)

**Per-leg signed exposure, with the deep in-the-money guard:**

```python
def signed_gamma_exposure(row: dict[str, Any], spot: float) -> float:
    gamma = to_float(row.get("gamma"))
    oi = to_float(row.get("oi"))
    option_type = str(row.get("option_type", "")).upper()
    strike = to_float(row.get("strike"))

    if gamma == 0.0 or oi <= 0.0 or spot <= 0.0:
        return 0.0

    # TD-NEW-2 Part A: reject deep-ITM rows with spurious gamma.
    # Options >5% from spot should have near-zero gamma in reality.
    # Threshold 5e-5 is ~5x typical ATM gamma; well outside legitimate
    # deep-ITM values. Dhan started returning gamma=7e-5 at strike 21,250
    # CE with spot 24,200 on 2026-05-08, polluting the flip-level walk.
    if strike > 0 and abs(strike - spot) / spot > 0.05:
        if abs(gamma) > 5e-5:
            return 0.0

    base = gamma * oi * (spot ** 2) / 1e7  # TD-NEW-3: store in Crore
    return -base if option_type == "PE" else base
```

**Usable-row filter and the strike map:**

```python
def filter_usable_option_rows(option_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable: list[dict[str, Any]] = []
    for row in option_rows:
        gamma = to_float(row.get("gamma"))
        oi = to_float(row.get("oi"))
        if gamma != 0.0 and oi > 0.0:
            usable.append(row)
    return usable

def compute_net_gex(option_rows: list[dict[str, Any]], spot: float) -> float:
    return sum(signed_gamma_exposure(r, spot) for r in option_rows)


def build_strike_exposure_map(option_rows: list[dict[str, Any]], spot: float) -> dict[float, float]:
    strike_map: dict[float, float] = {}
    for row in option_rows:
        strike = to_float(row.get("strike"))
        if strike <= 0:
            continue
        strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot)
    return dict(sorted(strike_map.items(), key=lambda x: x[0]))


def compute_gamma_concentration(strike_map: dict[float, float]) -> float | None:
    if not strike_map:
        return None

    total_abs = sum(abs(v) for v in strike_map.values())
    if total_abs <= 0:
        return None

    max_abs = max(abs(v) for v in strike_map.values())
    return max_abs / total_abs if max_abs > 0 else None
```

**The legacy flip (two constructions, chosen by the sign of the map's sum):**

```python
# TD-S62-NEW (S63) dominance floor for the SHORT-gamma per-strike walk:
# ignore strikes whose |GEX| is a negligible fraction of the peak, so a single
# tiny opposite-sign strike cannot create a false sign boundary. 0.01 = 1%.
_FLIP_DOMINANCE_EPS_FRAC = 0.01


def _flip_short_gamma_perstrike(strikes: list[float], strike_map: dict[float, float], spot: float) -> float | None:
    """TD-S62-NEW: per-strike signed-GEX sign boundary nearest spot.

    Used only under NEGATIVE gamma, where the cumulative-from-min_strike sum
    has no near-spot zero-crossing (net is negative) and the legacy walk falls
    through to a spurious deep-tail level (SENSEX 2026-07-01: ~71,500 vs spot
    ~76,900). The per-strike sign boundary is the operative pit->wall level
    near spot (StockMojo Gamma Flip 76,847 / Net-GEX-Cross 76,812).
    """
    values = [strike_map[s] for s in strikes]
    max_abs = max(abs(v) for v in values)
    if max_abs <= 0.0:
        return None
    eps = _FLIP_DOMINANCE_EPS_FRAC * max_abs
    sig = [(s, v) for s, v in zip(strikes, values) if abs(v) >= eps]
    if len(sig) < 2:
        return None
    crossings: list[float] = []
    for i in range(1, len(sig)):
        s_prev, v_prev = sig[i - 1]
        s_curr, v_curr = sig[i]
        if v_prev == 0.0:
            crossings.append(s_prev)
        elif v_curr == 0.0:
            crossings.append(s_curr)
        elif (v_prev < 0.0 < v_curr) or (v_prev > 0.0 > v_curr):
            denom = v_curr - v_prev
            if denom != 0.0:
                frac = -v_prev / denom
                crossings.append(s_prev + frac * (s_curr - s_prev))
    if not crossings:
        return None
    return min(crossings, key=lambda x: abs(x - spot))


def compute_flip_level(strike_map: dict[float, float], spot: float | None = None) -> float | None:
    """Find the operational gamma flip strike.

    Regime-conditional (TD-S62-NEW, S63):
      * net_gex >= 0 (LONG gamma): the cumulative-from-min_strike walk-from-ATM
        introduced by TD-NEW-2 Part B -- UNCHANGED. This path already resolves
        near spot on clean data (SENSEX 2026-07-01 healthy: 76,975 / 77,453).
      * net_gex <  0 (SHORT gamma): the per-strike sign boundary nearest spot
        (_flip_short_gamma_perstrike). The cumulative walk has no near-spot
        crossing under NEGATIVE gamma and returns a spurious deep-tail level;
        the per-strike boundary is the operative near-spot flip.

    net_gex == sum(strike_map.values()); no signature change. LONG-gamma cycles
    run the identical code they ran before this patch -- zero regression by
    construction.

    spot=None keeps the legacy bottom-up cumulative walk for backward
    compatibility with callers that don't pass spot (production passes spot).
    """
    if not strike_map:
        return None

    strikes = sorted(strike_map.keys())
    if len(strikes) < 2:
        return None

    # Legacy fallback: caller didn't supply spot. Preserve original behavior.
    if spot is None or spot <= 0:
        running = 0.0
        cumulative_points: list[tuple[float, float]] = []
        for strike in strikes:
            running += strike_map[strike]
            cumulative_points.append((strike, running))
        for i in range(1, len(cumulative_points)):
            strike_prev, cum_prev = cumulative_points[i - 1]
            strike_curr, cum_curr = cumulative_points[i]
            if cum_prev == 0.0:
                return strike_prev
            if cum_curr == 0.0:
                return strike_curr
            if (cum_prev < 0.0 < cum_curr) or (cum_prev > 0.0 > cum_curr):
                denom = cum_curr - cum_prev
                if denom == 0:
                    return None
                frac = -cum_prev / denom
                return strike_prev + frac * (strike_curr - strike_prev)
        return None

    net_gex = sum(strike_map.values())

    # SHORT gamma: per-strike sign boundary (TD-S62-NEW).
    if net_gex < 0.0:
        return _flip_short_gamma_perstrike(strikes, strike_map, spot)

    # LONG gamma: unchanged cumulative walk-from-ATM (TD-NEW-2 Part B).
    cumulative_points = []
    running = 0.0
    for strike in strikes:
        running += strike_map[strike]
        cumulative_points.append((strike, running))

    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    candidates: list[float] = []

    for i in range(atm_idx, 0, -1):
        strike_curr, cum_curr = cumulative_points[i]
        strike_prev, cum_prev = cumulative_points[i - 1]
        if cum_prev == 0.0:
            candidates.append(strike_prev)
            break
        if cum_curr == 0.0:
            candidates.append(strike_curr)
            break
        if (cum_prev < 0.0 < cum_curr) or (cum_prev > 0.0 > cum_curr):
            denom = cum_curr - cum_prev
            if denom != 0:
                frac = -cum_prev / denom
                candidates.append(strike_prev + frac * (strike_curr - strike_prev))
            break

    for i in range(atm_idx, len(cumulative_points) - 1):
        strike_curr, cum_curr = cumulative_points[i]
        strike_next, cum_next = cumulative_points[i + 1]
        if cum_curr == 0.0:
            candidates.append(strike_curr)
            break
        if cum_next == 0.0:
            candidates.append(strike_next)
            break
        if (cum_curr < 0.0 < cum_next) or (cum_curr > 0.0 > cum_next):
            denom = cum_next - cum_curr
            if denom != 0:
                frac = -cum_curr / denom
                candidates.append(strike_curr + frac * (strike_next - strike_curr))
            break

    if not candidates:
        return None
    return min(candidates, key=lambda x: abs(x - spot))
```

**Expansion probability, regime, gamma zone:**

```python
def compute_expansion_probability(
    gamma_concentration: float | None,
    flip_distance_pct: float | None,
    net_gex: float,
) -> float | None:
    if gamma_concentration is None:
        return None

    score = 45.0 if net_gex < 0 else 20.0

    if gamma_concentration >= 0.25:
        score += 20.0
    elif gamma_concentration >= 0.15:
        score += 12.0
    else:
        score += 5.0

    if flip_distance_pct is not None:
        if flip_distance_pct < 0.5:
            score += 20.0
        elif flip_distance_pct < 1.5:
            score += 10.0
        else:
            score += 2.0

    return max(0.0, min(100.0, score))


def determine_regime(net_gex: float, flip_level: float | None) -> str:
    if flip_level is None:
        return "NO_FLIP"
    return "LONG_GAMMA" if net_gex >= 0 else "SHORT_GAMMA"


def determine_gamma_zone(flip_distance_pct: float | None) -> str | None:
    if flip_distance_pct is None:
        return None
    if flip_distance_pct < 0.5:
        return "HIGH_GAMMA"
    if flip_distance_pct < 1.5:
        return "MID_GAMMA"
    return "LOW_GAMMA"
```

**Max-gamma strike and pin-risk score:**

```python
def compute_max_gamma_strike(strike_map: dict[float, float]) -> float | None:
    """S41 P0.a FIX-1 -- strike with maximum POSITIVE gex_cr (PIN candidate).

    Pin Risk Score requires the strike where dealers are LONG gamma
    (positive net gex_cr); these strikes are the operative magnets for
    spot pinning. Amplifying strikes (negative gex_cr) are the OPPOSITE
    force -- they accelerate spot away from themselves, not toward them.

    Aligns with the ENH-81 v_gex_strike_pin_zone SQL view convention which
    filters `WHERE gex_cr > 0` before identifying the peak. Marketview
    surfaces this same value as 'MAX gamma STRIKE' / 'STRONGEST DAMPEN'.

    Returns None when no positive-GEX strike exists in the map -- an
    extreme SHORT_GAMMA regime where dealers have no long-gamma anchor;
    pin semantics undefined. compute_pin_risk_score handles this via
    its existing renormalization path (spot_proximity_factor dropped).

    Tie-break: lower strike wins (sorted ascending key iteration).
    """
    if not strike_map:
        return None
    positive_strikes = {k: v for k, v in strike_map.items() if v > 0}
    if not positive_strikes:
        return None
    return max(positive_strikes.items(), key=lambda kv: kv[1])[0]


def compute_pin_risk_score(
    gamma_concentration: float | None,
    expansion_probability: float | None,
    spot: float,
    max_gamma_strike: float | None,
    strike_step: float | None,
    recent_max_strikes: list[float],
) -> float | None:
    """S41 P0.a -- additive-weighted Pin Risk Score, 0-100.

    Weights (operator-confirmed S41):
        gamma_concentration       weight 0.30 (0-1 input)
        spot_proximity_factor     weight 0.30 (0-1 derived)
        sustained_time_factor     weight 0.20 (0-1 derived; dropped + renorm if N<3)
        (1 - expansion_prob/100)  weight 0.20 (0-1 derived)

    Renormalization: if sustained_time_factor is unavailable (N<3 prior
    cycles) OR spot_proximity_factor is unavailable (missing strike data),
    the corresponding weight is dropped and remaining weights are
    re-normalized to sum to 1.0. This preserves comparability across
    cycles with varying history depth.

    None propagation: if gamma_concentration OR expansion_probability is
    None, the score is None -- these are core positioning measures with
    no reasonable default.

    Output: 0-100 rounded to 2 decimals, clamped at boundaries.
    """
    if gamma_concentration is None or expansion_probability is None:
        return None

    # spot_proximity_factor: 1 at max-gamma-strike, decays linearly to 0 at
    # 3 strike-steps away. Strike-step normalization handles NIFTY 50pt vs
    # SENSEX 100pt without hardcoding.
    spot_proximity_factor: float | None = None
    if (
        max_gamma_strike is not None
        and strike_step is not None
        and strike_step > 0
        and spot > 0
    ):
        proximity_distance_strikes = abs(spot - max_gamma_strike) / strike_step
        spot_proximity_factor = max(0.0, 1.0 - proximity_distance_strikes / 3.0)

    # sustained_time_factor: fraction of last N prior cycles where the
    # max-gamma strike was within +/- 1 strike-step of CURRENT max-gamma
    # strike. Requires N>=3 prior cycles for the factor to be meaningful
    # (15-min window minimum given 5-min cadence).
    sustained_time_factor: float | None = None
    if (
        max_gamma_strike is not None
        and strike_step is not None
        and len(recent_max_strikes) >= 3
    ):
        within_one_strike = sum(
            1 for s in recent_max_strikes if abs(s - max_gamma_strike) <= strike_step
        )
        sustained_time_factor = within_one_strike / len(recent_max_strikes)

    # expansion_probability is stored 0-100 by compute_expansion_probability;
    # complement gives 0-1 contraction-likelihood (high = pin-supportive).
    expansion_complement = 1.0 - (float(expansion_probability) / 100.0)

    # Assemble components and renormalize over available weights.
    components: list[tuple[float, float]] = []  # (weight, value)
    components.append((0.30, float(gamma_concentration)))
    if spot_proximity_factor is not None:
        components.append((0.30, spot_proximity_factor))
    if sustained_time_factor is not None:
        components.append((0.20, sustained_time_factor))
    components.append((0.20, expansion_complement))

    weight_total = sum(w for w, _ in components)
    if weight_total <= 0:
        return None
    score_01 = sum(w * v for w, v in components) / weight_total
    score_100 = 100.0 * score_01
    return round(max(0.0, min(100.0, score_100)), 2)
```

**The one place they are wired together (`compute_gamma_core`, body):**

```python
    strike_map = build_strike_exposure_map(option_rows, spot)
    net_gex = compute_net_gex(option_rows, spot)
    gamma_concentration = compute_gamma_concentration(strike_map)
    flip_level = compute_flip_level(strike_map, spot)

    if flip_level is None:
        flip_distance = None
        flip_distance_pct = None
    else:
        flip_distance = spot - flip_level
        flip_distance_pct = abs(flip_distance) / spot * 100.0 if spot > 0 else None

    gamma_zone = determine_gamma_zone(flip_distance_pct)
    straddle_atm = compute_straddle_atm(option_rows, spot)
    straddle_slope = compute_straddle_slope(option_rows, spot)
    expansion_probability = compute_expansion_probability(gamma_concentration, flip_distance_pct, net_gex)
    regime = determine_regime(net_gex, flip_level)

    # ENH-80 (S37) v2 — per-strike GEX row build (ADR-015 schema v2).
    gss_rows = build_gss_rows(option_rows_raw, spot, symbol, ts, expiry_date, run_id)

    # V18B: velocity and range fields
    straddle_velocity = compute_straddle_velocity(straddle_atm, prior_row)
    otm_oi_velocity = compute_otm_oi_velocity(option_rows, spot, prior_row)

    # S41 P0.a -- India VIX + max_gamma_strike + Pin Risk Score.
    # VIX is live-fetched (Dhan); failure returns None silently.
    # max_gamma_strike derived from in-memory strike_map (no Supabase round-trip).
    # Pin Risk Score requires sustained-time factor: queries last 5 cycles of
    # gex_strike_snapshots BEFORE current ts (current cycle not yet persisted).
    max_gamma_strike = compute_max_gamma_strike(strike_map)
    strike_step = infer_strike_step(option_rows)
    pin_risk_score = compute_pin_risk_score(
        gamma_concentration=gamma_concentration,
        expansion_probability=expansion_probability,
        spot=spot,
        max_gamma_strike=max_gamma_strike,
        strike_step=strike_step,
        recent_max_strikes=recent_max_strikes,
    )
```

### 2.2 What the code establishes

1. **One strike map feeds everything.** `strike_map` is built once from the usable rows and passed to concentration, flip and max-gamma strike. `net_gex` is computed from the same rows. Regime, expansion and pin score derive from those.
2. **The usable filter drops any leg with gamma = 0 or OI ≤ 0.** So open interest on a leg whose vendor gamma is zero never enters the map or the net.
3. **The stored per-strike rows are built from the raw rows, not the usable rows** (`build_gss_rows(option_rows_raw, …)`). The values agree because the exposure function zeroes the same legs.
4. **Regime does not use the flip's value, only whether it is empty.** `determine_regime` returns `NO_FLIP` when the flip is None, otherwise the sign of net gamma.
5. **Expansion probability is a hand-set point score.** Base 45 or 20 by the sign of net gamma, plus 20/12/5 by concentration band, plus 20/10/2 by distance to the flip. No fitted or tested basis appears in the code.
6. **The pin-risk score is a weighted sum with fixed weights** (0.30 concentration, 0.30 spot proximity, 0.20 persistence, 0.20 one minus expansion). The code comment records the weights as "operator-confirmed S41".
7. **The short-gamma flip path was introduced to match a third-party display on one day.** The docstring cites SENSEX 2026-07-01 and two external figures as its reference.
8. **`compute_gamma_core` is a pure function.** A second map could be built beside the first inside it. Whether that leaves every legacy output bit-identical is for the engine to confirm; it has not been asked yet.

### 2.3 Inputs the pin score takes from outside the function

Per the engine stream's description on 25 Nov (not re-read from the caller's source here):

- `strike_step`: smallest gap between strikes of the usable rows.
- `recent_max_strikes`: read from `gex_strike_snapshots` for the symbol, rows before the current run with `gex_cr > 0`, newest first, limit 1,250 rows, grouped by timestamp, five newest groups, the strike with the largest `gex_cr` in each. No session bound and no expiry filter. Empty on any read error.

### 2.4 Who consumes the legacy outputs

**Engine code, scheduled or running** (register entry S75.D, established 8 Sep 2026 from the crontab, the orchestrator child list, systemd units and running processes, not from file names):

- `compute_gamma_metrics_local.py` (writer)
- `build_market_state_snapshot_local.py`
- `build_trade_signal_local.py`
- `accrue_expiry_outcomes.py`
- `relate_ambient_to_open_local.py`

The same entry records that 76 of the 81 files mentioning these fields are on no scheduling surface. The engine stream's search on 25 Nov added, as readers of the pin-risk score: `structural_divergence_snapshots`, the ambient environment view (ENH-116), and `backfill_expiry_outcomes`.

**`trade_allowed`.** The signal builder still runs from the crontab and still writes it (`NO_FLIP` and `LONG_GAMMA` set it false; S75.D measured that as 76.7 % of NIFTY and 64.4 % of SENSEX cycles). Evidence of 24–25 Nov: the alert daemon, signal dashboard, trade logger and order placer are present on the box but not scheduled and not running; the alert daemon last ran on 11 Jun 2026; all 19 Windows scheduled tasks are disabled. On 23 Nov the stored field was false on 173 rows and true on 1. So the gate is computed and stored, and nothing found acts on it.

**Database views** (catalog reads of 24–25 Nov, full dependency tree and column-level records):

| Reads from the legacy block | Views |
|---|---|
| `flip_level`, `net_gex`, `regime`, `gamma_concentration`, `expansion_probability` from `gamma_metrics` | `latest_gamma_metrics`, `latest_gamma_metrics_v2`, `latest_signal_inputs`, `latest_signal_inputs_v2`, `latest_signal_intraday`, `latest_signal_v1`, `latest_signal_v1_gated`, `latest_signal_v2`, `latest_signal`, `signal_outcome_research_v1`, `signal_outcome_research_v2`, `v_gamma_metrics_1pct` |
| `flip_level` and `net_gex` together | `v_dealer_flow_sim` |
| `net_gex` only | `v_gex_net_gamma_river`, `v_gex_net_gamma_river_1pct` |
| Stored copy, per cycle | `gex_cycle_history` carries `flip_level`, `gamma_regime`, `net_gex` beside `repriced_flip_level`; `v_pin_board` passes all of them through |

**Per-strike exposure (`gex_cr`) readers**, which any change to the strike map reaches: `v_gex_strike_rank`, `v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`, `v_gex_concentration`, `v_gex_abs_exposure` (+`_1pct`), `v_gex_strike_terrain` (+`_1pct`), `v_gex_strike_snapshots_1pct`. Not affected, because they read open interest only: `v_gex_strike_walls`, `v_gex_max_pain`.

**Board source** (search of `.ts` and `.tsx` files, 24–25 Nov; source tree only):

| What the Board shows | Source | Where |
|---|---|---|
| Pin score, probability, timeline; narrative branches at score ≥ 75 | `gamma_metrics.pin_risk_score` | `lib/queries.ts:386`, `marketview/sections.tsx`, `marketview/ui.tsx`, `NarrativeModal.tsx`, `AmbientTrajectory.tsx`, `Positioning.tsx` |
| Regime wording | `regime` | `NarrativeModal.tsx:26`, `marketview/sections.tsx:306` |
| Dealer flow simulation | `v_dealer_flow_sim` | `lib/board.ts:236,240`, `lib/queries.ts:279,288` |
| Net gamma river | `v_gex_net_gamma_river_1pct` | `lib/board.ts:371` |
| Pin strike, state, conviction | `v_pin_board`, `v_gex_strike_rank`, `gex_cycle_history` directly | `lib/board.ts`, `pages/Board.tsx`, `pages/Home.tsx`, `pages/TapeFlowBook.tsx`, `lib/tapePin.ts` |

No hit in the Board source for any `latest_signal*`, `latest_gamma_metrics*` or `signal_outcome_research*` view.

**Live invariant check.** A database function (`p3b_sweep`, version p3b-v1.2) runs every five minutes in market hours. It recomputes each strike's exposure from the chain with the legacy per-leg rule and fails on a difference above 1e-6 + 1e-9·|v|. It also checks that the per-strike sum equals stored net gamma and that the top-strike share equals stored concentration.

**Other gamma computations found in the database, outside `gamma.py`:**

- `latest_net_gamma_by_strike` and three views on it compute net gamma per strike directly from the chain's per-leg vendor gamma. No reader found in the engine repo; two of the four had zero hits in the Board source and two were not searched by name.
- `insert_option_chain_batch`, a database function, fills net gamma, concentration and flip through `compute_gamma_metrics_for_run` and `compute_gamma_flip_for_run`. Only the service role can execute it. No caller found in the engine repo. No row from it on 23 Nov.

### 2.5 The dealer flow simulation, verbatim

File `sql/2026-10-05_s90_v_dealer_flow_sim_sign_fix.sql`. Its header says "AUTHORED, NOT APPLIED"; whether it was later applied is not established here.

```sql
CREATE OR REPLACE VIEW public.v_dealer_flow_sim AS
WITH scenarios AS (
  SELECT * FROM (VALUES
    (-0.02::numeric,  '-2.0%'::text),
    (-0.01,           '-1.0%'),
    (-0.005,          '-0.5%'),
    ( 0.005,          '+0.5%'),
    ( 0.01,           '+1.0%'),
    ( 0.02,           '+2.0%')
  ) AS s(pct, label)
),
latest_per_symbol AS (
  SELECT DISTINCT ON (symbol)
    run_id, symbol, expiry_date, ts, spot
  FROM gex_strike_snapshots
  ORDER BY symbol, ts DESC
),
ctx AS (
  SELECT
    l.symbol, l.run_id, l.expiry_date, l.ts, l.spot,
    gm.net_gex, gm.flip_level
  FROM latest_per_symbol l
  JOIN gamma_metrics gm
    ON gm.run_id = l.run_id AND gm.symbol = l.symbol
)
SELECT
  c.run_id, c.symbol, c.expiry_date, c.ts,
  s.label                                         AS scenario,
  s.pct                                           AS spot_pct,
  ROUND((c.spot * (1 + s.pct))::numeric, 2)       AS perturbed_spot,
  c.net_gex,
  ROUND((-c.net_gex * s.pct)::numeric, 2)         AS flow_cr,      -- S90: hedge flow = -Gamma * dS
  CASE WHEN (-c.net_gex * s.pct) < 0 THEN 'SELL' ELSE 'BUY' END AS direction,
  CASE
    WHEN c.flip_level IS NULL THEN false
    WHEN s.pct < 0 AND c.spot > c.flip_level
         AND c.spot * (1 + s.pct) <= c.flip_level THEN true
    WHEN s.pct > 0 AND c.spot < c.flip_level
         AND c.spot * (1 + s.pct) >= c.flip_level THEN true
    ELSE false
  END                                             AS crosses_flip
FROM ctx c
CROSS JOIN scenarios s
ORDER BY c.symbol, s.pct;
```

It joins the latest per-strike run to `gamma_metrics` by run and reads `net_gex` and `flip_level` from the same row. Under scope B those two would come from different maps.

---

## 3. The Board Flip (`v_gex_repriced_flip`)

File `sql/2026-09-25_s83_v_gex_repriced_flip.sql` (ENH-131, shipped 25 Sep 2026).

### 3.1 The view, verbatim

```sql
CREATE OR REPLACE VIEW public.v_gex_repriced_flip AS
WITH RECURSIVE symbols AS (
        -- S72 FIX 2 skip scan. Symbols derived, never a literal list.
        SELECT (SELECT min(o.symbol) FROM option_chain_snapshots o) AS symbol
        UNION ALL
        SELECT (SELECT min(o.symbol)
                  FROM option_chain_snapshots o
                 WHERE o.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), latest AS (
        -- ADR-021 run scoping: one index seek per symbol through
        -- idx_ocs_ts_symbol_expiry (ts DESC, symbol, expiry_date).
        -- NOT max(ts) GROUP BY symbol. NEVER created_at: ingest reuses
        -- one snapshot_ts per cycle but created_at is a DB-side default
        -- and is later for the extra expiry pass, so ordering by it
        -- hands back W2 (S81, 89bc83e).
        SELECT s.symbol, lt.ts AS latest_ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT o.ts
                 FROM option_chain_snapshots o
                WHERE o.symbol = s.symbol
                ORDER BY o.ts DESC
                LIMIT 1
          ) lt
         WHERE s.symbol IS NOT NULL
     ), front AS (
        -- Front expiry = the nearest listed expiry IN THAT SNAPSHOT.
        -- Capture stage 1 holds W1 and W2; only W1 is repriced, so the
        -- comparison is like-for-like against a front-expiry net.
        SELECT l.symbol, l.latest_ts AS ts,
               min(o.expiry_date) AS front_expiry
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
         GROUP BY l.symbol, l.latest_ts
     ), scoped AS (
        SELECT f.symbol, f.ts, f.front_expiry,
               o.strike, o.option_type, o.iv, o.oi, o.gamma, o.spot
          FROM front f
          JOIN option_chain_snapshots o
            ON o.symbol = f.symbol AND o.ts = f.ts
           AND o.expiry_date = f.front_expiry
     ), hdr AS (
        -- T is EXACT SECONDS to 15:30 IST on the front expiry, over a
        -- 365-day year. This is Gate 5 convention (b). dte 0 is NOT
        -- floored: S62 settled that expiry-day 0-DTE gamma exposure is
        -- numerically unreconstructible, so it is marked and skipped.
        SELECT s.symbol, s.ts, s.front_expiry,
               max(s.spot) AS spot,
               (s.front_expiry
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.front_expiry + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.front_expiry
     ), legs AS (
        -- R1 FROZEN LEG SET, evaluated once at the OBSERVED spot.
        -- iv > 0 is required because sigma is a divisor; it removed no
        -- leg on any of the five gate arms.
        SELECT s.symbol, s.ts,
               s.strike::double precision       AS k,
               s.option_type,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi
          FROM scoped s
          JOIN hdr h ON h.symbol = s.symbol AND h.ts = s.ts
         WHERE s.oi > 0
           AND s.gamma IS NOT NULL AND s.gamma <> 0
           AND s.iv > 0
           AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                    AND abs(s.gamma) > 5e-5)
     ), futwin AS (
        -- NO LOOK-AHEAD. Futures rows for this symbol from 09:20 IST on
        -- the ts date through ts INCLUSIVE. One index range scan per
        -- symbol through idx_index_futures_snapshots_symbol_ts.
        SELECT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM hdr h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        -- Front-month FUTURE at ts, which is not always the option
        -- front expiry: min expiry on or after the IST date of ts.
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
        -- Per-cycle carry r_fut(t) = ln(F/S) / T_f, with T_f taken from
        -- THAT ROW OWN ts, not from the snapshot ts. F and S come from
        -- the same row, so the two are contemporaneous by construction.
        SELECT w.symbol, w.ts,
               ( ln(w.futures_price / w.spot_price)
                 / (EXTRACT(epoch FROM
                      (((w.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                       - w.fut_ts)) / (365.0 * 86400.0))
               )::double precision AS r_fut
          FROM futwin w
          JOIN futfront f
            ON f.symbol = w.symbol AND f.ts = w.ts
           AND f.fut_expiry = w.expiry_date
         WHERE w.fut_ts < ((w.expiry_date + time '15:30')
                           AT TIME ZONE 'Asia/Kolkata')
     ), rstats AS (
        -- r_sess is the MEDIAN, and the p10-p90 band is published beside
        -- it because Gate 5 clause (i) is a sweep over that band, not a
        -- point estimate. Fewer than 6 rows is UNMEASURABLE, never
        -- substituted with a default.
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess,
               percentile_cont(0.10) WITHIN GROUP (ORDER BY r_fut) AS r_p10,
               percentile_cont(0.90) WITHIN GROUP (ORDER BY r_fut) AS r_p90
          FROM rrows
         GROUP BY symbol, ts
     ), atm AS (
        -- House ATM grid: round(spot / step) * step, step 50 for NIFTY
        -- and 100 for SENSEX, matching
        -- compute_volatility_metrics_local.py:86-88 and :624. This is a
        -- GRID strike and may not be listed; when it is not, atm_iv is
        -- NULL and sigma_1d is NULL rather than sliding to a neighbour.
        SELECT h.symbol, h.ts,
               round(h.spot
                     / (CASE WHEN h.symbol = 'NIFTY' THEN 50 ELSE 100 END))
                 * (CASE WHEN h.symbol = 'NIFTY' THEN 50 ELSE 100 END)
                 AS atm_strike
          FROM hdr h
     ), atmiv AS (
        -- NULLIF(iv, 0): a zero iv abstains. Same deviation recorded in
        -- the L9 view, for the same reason.
        SELECT q.symbol, q.ts, q.atm_strike,
               CASE WHEN q.ce_iv > 0 AND q.pe_iv > 0
                    THEN (q.ce_iv + q.pe_iv) / 2.0
               END AS atm_iv
          FROM (
            SELECT a.symbol, a.ts, a.atm_strike,
                   NULLIF(max(CASE WHEN s.option_type = 'CE' THEN s.iv END), 0)
                     AS ce_iv,
                   NULLIF(max(CASE WHEN s.option_type = 'PE' THEN s.iv END), 0)
                     AS pe_iv
              FROM atm a
              LEFT JOIN scoped s
                ON s.symbol = a.symbol AND s.ts = a.ts
               AND s.strike = a.atm_strike
             GROUP BY a.symbol, a.ts, a.atm_strike
          ) q
     ), base AS (
        SELECT h.symbol, h.ts, h.front_expiry, h.spot, h.dte, h.t_years,
               r.n_r_rows, r.r_sess, r.r_p10, r.r_p90,
               v.atm_iv,
               (h.spot * v.atm_iv / 100.0 * sqrt(1.0 / 365.0))::double precision
                 AS sigma_1d
          FROM hdr h
          LEFT JOIN rstats r ON r.symbol = h.symbol AND r.ts = h.ts
          LEFT JOIN atmiv  v ON v.symbol = h.symbol AND v.ts = h.ts
     ), evalset AS (
        -- Only rows that can carry a number reach the sweep. dte 0 and a
        -- thin r window drop out here and are labelled in status.
        SELECT b.symbol, b.ts, b.spot::double precision AS spot,
               b.t_years, b.r_sess
          FROM base b
         WHERE b.dte > 0 AND b.t_years > 0
           AND b.n_r_rows >= 6 AND b.r_sess IS NOT NULL
     ), grid AS (
        -- 201 points, 0.1 pct steps, plus or minus 10 pct of spot.
        SELECT e.symbol, e.ts, g.i,
               e.spot * (1.0 + (g.i - 100) * 0.001) AS s_grid
          FROM evalset e
          CROSS JOIN generate_series(0, 200) AS g(i)
     ), gexcurve AS (
        -- TotalGEX(S). gamma = n(d1) / (S sigma sqrt(T)),
        -- d1 = (ln(S/K) + (r + sigma^2 / 2) T) / (sigma sqrt(T)).
        -- Per leg: gamma * oi * S^2 / 1e7, PE negated, matching
        -- signed_gamma_exposure() exactly except that gamma is BS
        -- rather than vendor. Division by 1e7 is the Crore convention
        -- (TD-NEW-3).
        SELECT gr.symbol, gr.ts, gr.i, gr.s_grid,
               sum(
                 (CASE WHEN l.option_type = 'PE' THEN -1.0 ELSE 1.0 END)
                 * ( exp(-0.5 * power(
                       ( ln(gr.s_grid / l.k)
                         + (e.r_sess + 0.5 * power(l.sigma, 2)) * e.t_years )
                       / (l.sigma * sqrt(e.t_years)), 2))
                     / sqrt(2.0 * pi()) )
                   / (gr.s_grid * l.sigma * sqrt(e.t_years))
                 * l.oi * power(gr.s_grid, 2) / 1e7
               ) AS total_gex
          FROM grid gr
          JOIN evalset e ON e.symbol = gr.symbol AND e.ts = gr.ts
          JOIN legs   l  ON l.symbol = gr.symbol AND l.ts = gr.ts
         GROUP BY gr.symbol, gr.ts, gr.i, gr.s_grid
     ), adj AS (
        SELECT c.symbol, c.ts, c.s_grid, c.total_gex,
               lag(c.s_grid)    OVER (PARTITION BY c.symbol, c.ts
                                      ORDER BY c.i) AS prev_s,
               lag(c.total_gex) OVER (PARTITION BY c.symbol, c.ts
                                      ORDER BY c.i) AS prev_g
          FROM gexcurve c
     ), crossings AS (
        -- Linear interpolation between adjacent grid points, exactly as
        -- the gate script computed it.
        SELECT a.symbol, a.ts,
               a.prev_s + (a.s_grid - a.prev_s)
                        * (0.0 - a.prev_g) / (a.total_gex - a.prev_g)
                 AS s_star,
               CASE WHEN a.prev_g < 0 THEN 'neg->pos' ELSE 'pos->neg' END
                 AS flip_direction
          FROM adj a
         WHERE a.prev_g IS NOT NULL
           AND ((a.prev_g < 0) <> (a.total_gex < 0))
           AND a.total_gex <> a.prev_g
     ), counted AS (
        SELECT b.symbol, b.ts,
               count(x.s_star)::integer AS n_cross_full_grid,
               CASE WHEN b.sigma_1d IS NULL THEN NULL
                    ELSE count(x.s_star) FILTER (
                           WHERE abs(x.s_star - b.spot) <= 2.0 * b.sigma_1d
                         )::integer
               END AS n_cross_within_2sigma
          FROM base b
          LEFT JOIN crossings x ON x.symbol = b.symbol AND x.ts = b.ts
         GROUP BY b.symbol, b.ts, b.sigma_1d
     ), nearest AS (
        SELECT DISTINCT ON (x.symbol, x.ts)
               x.symbol, x.ts, x.s_star, x.flip_direction
          FROM crossings x
          JOIN base b ON b.symbol = x.symbol AND b.ts = x.ts
         ORDER BY x.symbol, x.ts, abs(x.s_star - b.spot)
     )
SELECT
    b.symbol,
    b.ts,
    b.spot,
    b.front_expiry,
    (b.t_years * 365.0)                          AS t_days,
    b.r_sess,
    b.r_p10,
    b.r_p90,
    COALESCE(b.n_r_rows, 0)                      AS n_r_rows,
    b.atm_iv,
    b.sigma_1d,
    n.s_star                                     AS flip,
    n.flip_direction,
    (n.s_star - b.spot)                          AS flip_minus_spot,
    CASE WHEN b.sigma_1d IS NULL OR b.sigma_1d = 0 THEN NULL
         ELSE (n.s_star - b.spot) / b.sigma_1d
    END                                          AS flip_sigma,
    c.n_cross_within_2sigma,
    c.n_cross_full_grid,
    -- Precedence is deliberate. S62 first: an expiry-day cycle is
    -- skipped whatever else is true of it.
    CASE WHEN b.dte = 0                 THEN 'SKIPPED_EXPIRY'
         WHEN COALESCE(b.n_r_rows, 0) < 6 THEN 'UNMEASURABLE_R'
         WHEN n.s_star IS NULL          THEN 'NO_CROSSING'
         ELSE 'OK'
    END                                          AS status
  FROM base b
  LEFT JOIN nearest n ON n.symbol = b.symbol AND n.ts = b.ts
  LEFT JOIN counted c ON c.symbol = b.symbol AND c.ts = b.ts;
```

### 3.2 Answers to the advisor's four questions

**Multiple roots.** Every sign change of TotalGEX on the grid is kept in `crossings`. The published `flip` is the crossing nearest spot. Two counts are published beside it: `n_cross_full_grid` and `n_cross_within_2sigma`. There is no "multiple crossings" status; a run with several crossings reports `OK` with the nearest one. The file's own caveat records one gate arm with a second crossing 9.4 % from spot that appeared and disappeared with the time convention.

**Implied-vol inputs.** The vendor's per-leg `iv` from the chain, divided by 100, held fixed per strike across the whole sweep (sticky strike). Call and put at the same strike each use their own iv. No smoothing and no own solve. A zero iv drops the leg.

**Expiry day.** Not a numerical failure and not an absent crossing. The view refuses by rule: `dte = 0` returns status `SKIPPED_EXPIRY` with a NULL flip, citing an earlier finding (S62) that expiry-day gamma exposure is "numerically unreconstructible". Measured consequence (register S88): on a six-day expiry cohort the flip was NULL on all 90 cells.

**Acceptance gates.** Five, recorded in the file header, three failed:

| Gate | Result | What it tested |
|---|---|---|
| 1 | Passed | Rebuilt stored per-strike exposure from stored gammas and OI; matched to 1.1e-10 Cr |
| 2 | Failed, mis-specified | Repriced net vs stored net at 1 %; missed by 19.3 / 19.7 %. Net over gross was 0.0095 to 0.341, so it scored cancellation |
| 3 | Failed, 1 of 3 arms | Stability of the nearest crossing across r in {0, 0.065, 0.10} and three time conventions |
| 4 | Failed, 1 of 4 arms | Same with single-cycle futures carry; its band was about 19 times too narrow |
| 5 | Passed, 5 of 5 arms | Stability inside 0.25 of a one-day sigma across the measured r band and three time conventions; basis for shipping |

Gate 5 is five timestamps between 18 and 24 Sep 2026. It tests that the level is stable to its own parameters. It does not test that the level means anything for price.

**The "circular gate" is a different, earlier gate** (tech-debt entry TD-S79-NEW-15, 16 Sep 2026, a pre-build measurement). It asked whether positive net gamma coincides with spot above the repriced flip. Because the repriced flip is defined as the zero of TotalGEX and TotalGEX was monotone through it, the two statements are the same proposition; they matched on 42 of 42 NIFTY and 41 of 42 SENSEX cases. What that gate actually measured was whether repriced gamma reproduces the sign of the vendor's net: 87.5 % NIFTY, 88.2 % SENSEX. The same entry records the legacy flip on that gate: 20.8 % NIFTY (n = 5,096) and 25.1 % SENSEX (n = 5,149), against independence baselines of 28.8 % and 40.3 %.

**The view's own stated standing.** Its comment says it is display only, "routes nothing, gates nothing, and makes NO PREDICTIVE CLAIM", and that whether price is attracted to, repelled by or indifferent to the level is unmeasured.

### 3.3 Correction: the Board Flip is not independent of vendor gamma

The earlier note said the Board Flip is free of the vendor-gamma problems. That was wrong. The view does not use the vendor gamma's **value**, but it uses it to choose **which legs are included**:

```sql
WHERE s.oi > 0
  AND s.gamma IS NOT NULL AND s.gamma <> 0
  AND s.iv > 0
  AND NOT (abs(s.strike - h.spot) / h.spot > 0.05 AND abs(s.gamma) > 5e-5)
```

So a leg whose vendor gamma is zero is dropped from the repricing, with its open interest. The gamma pipeline audit found the vendor sends a literal zero on 31 to 32 % of in-the-money legs that hold open interest. Those legs are missing from the Board Flip in the same way they are missing from the legacy net. The file reports how many legs the deep in-the-money guard removed on the gate arms (31, 0, 32, 0, 20) but not how many the `gamma <> 0` condition removed. The size of the effect on the flip has not been measured.

The view's header says it "shares no code, no column and no input" with the legacy flip. On the leg-selection point that statement is not accurate.

### 3.4 Other properties that matter for a replacement

- Front expiry only.
- Grid: 201 points, ±10 % of spot, 0.1 % steps, linear interpolation.
- Carry rate: session median of ln(F/S)/T from futures last-trade prices, no look-ahead; fewer than six rows gives `UNMEASURABLE_R`.
- The leg set is frozen at the observed spot.
- Gross fidelity of repriced vs vendor exposure on the gate arms: 3.4 %, 10.9 % and 4.7 %; it failed its 5 % threshold on the SENSEX one-day arm.
- Existing statuses: `OK`, `SKIPPED_EXPIRY`, `UNMEASURABLE_R`, `NO_CROSSING`.
- Latest run only. History exists only where `gex_cycle_history` has stored `repriced_flip_level` per cycle. That table began in October 2026; the first date of that column was not checked.

### 3.5 Consumers

`write_gex_cycle_history_local.py` (stores it per cycle), `acceptance_enh133_local.py`, and the Board (the source imports a `useRepricedFlip` hook; the exact file and tile were not traced). A related view, `v_dex_repriced_zero`, exists for delta exposure and was not examined.

---

## 4. Evidence on what is wrong with the inputs

From the gamma pipeline audit of 22 Nov 2026 and the pin fix scope document:

- The vendor sends a gamma of literal 0, never a null, on 31 to 32 % of in-the-money legs with open interest.
- Vendor gamma arrives on a five-decimal lattice. On SENSEX, 33 to 44 % of open interest sits on legs with gamma below 0.00010.
- Production's total net gamma disagrees in sign with the audit's reference on 9.87 % (NIFTY) and 8.57 % (SENSEX) of runs with a clearly non-zero total, and on 21.83 % and 16.51 % of all runs.
- On about a third of runs the total is under 5 % of gross.
- How often the regime label itself differs was not measured.
- The guard threshold (5e-5) is one literal for both indices; register entry TD-S75-NEW-2 records it as about 3.2 times stricter on SENSEX.
- The engine's trace of 25 Nov: on the long-gamma path, a strike with exactly zero exposure inside the crossing interval moves the interpolated flip, and leading zero-valued strikes can produce a far-tail flip where there would otherwise be none.

---

## 5. P2: the dealer-side study

Files `docs/research/s94_priority/P2_dealer_side_design_2026-10-10.md` and `P2_dealer_side_result_2026-10-10.md`. Pre-registered; version 1 stopped on a mis-specified integrity gate with no verdict, version 2 was scored on the same extract.

### 5.1 The question

The board counts call gamma positive and put gamma negative. Read as dealer gamma, that assumes the dealer side is net long calls and net short puts. P2 asked whether, in NSE's daily participant-wise open interest, the category standing in for dealers holds that position.

### 5.2 Data and definitions

- NSE participant-wise open interest, daily, 2025-05-28 to 2026-10-09, 340 dates, four categories (Client, DII, FII, Pro) plus TOTAL.
- Index options are one aggregate across all NSE index underlyings. No strikes, no expiries, contract counts only.
- For category k on date d: net_call = call_long − call_short; net_put = put_long − put_short.
- **Holds:** net_call > 0 and net_put < 0. **Inverted:** net_call < 0 and net_put > 0. Anything else is **mixed**.
- Dealer proxy, fixed before measuring: primary **Pro**; secondary **Pro + FII**. Client, DII and FII alone are descriptive.
- Verdict rule, fixed before measuring: CONSISTENT if the Wilson 95 % lower bound of the "holds" share is at least 0.80; INVERTED if the lower bound of the "inverted" share is at least 0.80; otherwise REGIME-DEPENDENT.

### 5.3 Result, as scored

| Group | Holds | Inverted | Mixed | Holds 95 % | Inverted 95 % | Verdict |
|---|---:|---:|---:|---|---|---|
| Pro (primary) | 23 | 113 | 204 | [0.045, 0.099] | [0.284, 0.384] | REGIME-DEPENDENT |
| Pro + FII (secondary) | 0 | 231 | 109 | [0.000, 0.011] | [0.628, 0.727] | REGIME-DEPENDENT |
| Client (descriptive) | 226 | 0 | 114 | [0.613, 0.713] | [0.000, 0.011] | — |
| DII (descriptive) | 0 | 12 | 328 | [0.000, 0.011] | [0.020, 0.061] | — |
| FII (descriptive) | 0 | 255 | 85 | [0.000, 0.011] | [0.701, 0.793] | — |

**Verdict: REGIME-DEPENDENT.**

**Correction to the earlier note.** It quoted only "23 of 340". The fuller picture is that the primary proxy held the assumed position on 23 dates, the opposite on 113, and was mixed on 204. Neither proxy reached the 0.80 bar in either direction.

### 5.4 Limits stated in the result

1. Open interest carries from day to day, so the 340 dates are not independent and every interval above is too narrow. No statement stronger than REGIME-DEPENDENT can be made.
2. NSE only, so NIFTY only. SENSEX is untested.
3. The aggregate covers all NSE index underlyings, not NIFTY alone.
4. It is the sign of net contract counts, not gamma. It says nothing about per-strike positioning, the flip, the walls or magnitudes.
5. "Dealer" is a proxy. NSE labels no one a dealer.

### 5.5 Descriptive observations the result records as not claimable

- Client held the board's assumed position on 226 of 340 dates and the opposite on none.
- The board's sign looks more like the client book than like either dealer proxy, consistent with the project's own earlier statement (ADR-015) that the stored quantity is "positioning gamma, not dealer gamma". Because of limit 1 this is not evidence that the sign is inverted.

### 5.6 Still owed from P2

- The split by days to expiry and by five-day spot trend, as reporting strata only. Not produced.
- A ruling on whether the board keeps the words "dampening" and "amplifying". The record of ruling S94-F is that the board keeps those labels with the P2 caveat in the net gamma explanation.

### 5.7 A related test

P1c (October 2026) asked whether positive net gamma with high concentration goes with a smaller realised range. Result: inconclusive. The NIFTY holdout had 6 qualifying cases against a required 8.

---

## 6. What is decided and what is open

**Decided by the operator:**
- The pin is the gross peak (21 Nov), computed with one vendor gamma per strike (22 Nov).
- Gross gamma, net gamma and dealer-positioning interpretation are three separate layers; improving the first two does not validate the third (22 Nov).
- The ten-day shadow for the pin was dropped in favour of a standing daily monitor (23–24 Nov).
- The Board's Flip is left alone for now; unify on own-computed gammas later (24 Nov).

**Open:**
1. Scope of the gamma source fix: A, B or D.
2. Whether the legacy regime, expansion probability, pin score and dealer flow simulation are labelled, suppressed or left on the Board.
3. Whether to start a pre-registered study of a replacement flip or of the full repriced gamma curve, and with which candidates.
4. Whether pin state and conviction follow the gross pin or stay on the net peak.

**Not measured anywhere in the record:**
- Whether price behaves differently on either side of either flip.
- The effect of the `gamma <> 0` leg filter on the Board Flip.
- The effect of the vendor's per-leg implied vol on the Board Flip.
- How often the regime label would differ under a corrected net.
