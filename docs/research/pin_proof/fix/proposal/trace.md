<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/proposal/trace.md -->

# Dependency and precision trace for an engine proposal

Read-only. No code, SQL, view, table or Board change. Trees `~/meridian-engine` and
`~/meridian-connect/src`. Where the source does not settle something it is written
**NOT ESTABLISHED**; nothing below is inferred.

---

## PART A.1 — readers, by class

Classes: **GATE** (can block or allow a signal or trade), **SIZE/CONFIDENCE** (changes
a number attached to a signal), **LABEL** (text or display only), **STORED ONLY**.

### GATE

| file:line | expression | what it does |
|---|---|---|
| `build_trade_signal_local.py:605-611` | `elif gamma_regime == "LONG_GAMMA": … trade_allowed = False` | blocks the trade. Comment: "ENH-35 validated 2026-04-11: LONG_GAMMA signals 47.7% accuracy at N=24,579 — structurally below random." |
| `build_trade_signal_local.py:612-618` | `elif gamma_regime == "NO_FLIP": … trade_allowed = False` | blocks the trade. "NO_FLIP gated — no gamma flip reference (ENH-35)" |

`gamma_regime` is `gamma_metrics.regime`: `build_market_state_snapshot_local.py:190`
`"gamma_regime": gamma_row.get("regime")`, read back at
`build_trade_signal_local.py:435` (`state.get("gamma_features")`) and resolved by
`get_gamma_regime` at `:235-236`.

**Only `gamma_metrics.regime` gates.** No GATE reader was found for `gamma_zone`,
`flip_level`, `flip_distance`, `flip_distance_pct`, `net_gex`, `gamma_concentration`,
`max_gamma_strike`, `pin_risk_score`, `gex_cycle_history.pin_state` / `conviction` /
`pin_leader_strike`, `v_gex_strike_rank` or `v_gex_strike_pin_zone`.

### SIZE/CONFIDENCE

| file:line | expression | effect |
|---|---|---|
| `build_trade_signal_local.py:601-604` | `if gamma_regime == "SHORT_GAMMA": … if direction_bias in {"BULLISH","BEARISH"}: confidence += 8.0` | +8 confidence |
| `build_trade_signal_local.py:622-626` | `if gamma_concentration is not None: if gamma_concentration >= 0.25: … confidence += 4.0` | +4 confidence |
| `build_shadow_signal_v3_local.py:233-236` | `if gamma_regime == "SHORT_GAMMA": bearish_points += 1; bullish_points += 1` | moves both point tallies |

### LABEL

| file:line | expression | effect |
|---|---|---|
| `build_trade_signal_local.py:559` | `reasons.append(f"Gamma regime is {gamma_regime}")` | reason text |
| `build_trade_signal_local.py:623, 626` | concentration "supportive" / "low" | reason/caution text |
| `build_trade_signal_local.py:630-637` | `flip_distance_pct < 0.5 / < 1.5 / else` → three cautions | caution text only; **no confidence change and no gate** |
| `build_shadow_signal_v3_local.py:237-241` | LONG_GAMMA / NO_FLIP → `cautions` / `reasons` only | text; **not a gate in v3** |
| `build_market_state_snapshot_local.py:467-468` | prints `gamma_regime`, `flip_distance_pct` | console |
| `generate_pine_overlay.py:214-235` | reads `v_gex_strike_pin_zone` (`pin_lower, pin_upper, n_strikes, total_pin_gex_cr, peak_pin_gex_cr, peak_pin_strike, tau_used, ts, expiry_date`) | draws the Pine overlay band |
| `compile_market_environment_local.py:189` | `select ts,spot,net_gex,gamma_concentration,regime,max_gamma_strike,expiry_date` | Lens 1 of the ambient snapshot. Header `:8`: "Display-not-gate (ADR-002 v2 D.19.3); touches no live routing." |

### STORED ONLY

`build_trade_signal_local.py:541-546` reads `net_gex`, `gamma_concentration`,
`flip_level`, `flip_distance`, `straddle_atm`, `straddle_slope` under the comment
`# --- Gamma fields for output ---`; of these only `gamma_concentration` and
`flip_distance_pct` are used again (above). `flip_level`, `flip_distance` and
`net_gex` are carried to the output row and nothing else.

`services/tape_scoring/score.py:101-103` selects `gamma_call, gamma_put, oi_call,
oi_put, gex_cr` from `gex_strike_snapshots` and `straddle_atm` from `gamma_metrics`;
its header `:11-12` states "Sign only: no gex_cr / gamma magnitude and no D value
reaches the output".

`gex_cycle_history.pin_state` / `conviction` / `pin_leader_strike`: no engine reader
found on a live path other than the writer itself
(`write_gex_cycle_history_local.py:383, 393, 396`) and the Board (A.4).

## PART A.2 — are the GATE / SIZE readers scheduled?

| file | scheduled | how |
|---|---|---|
| `build_trade_signal_local.py` | **YES** | not its own cron line; invoked by the orchestrator `run_merdian_shadow_runner_aws.py:444` (NIFTY) and `:449` (SENSEX). The orchestrator runs on `crontab -l` lines 13 (`*/5 03-09 * * 1-5`) and 69 (`0,5,10 10 * * 1-5`), i.e. 08:30–15:29 IST plus three catch-ups. |
| `build_shadow_signal_v3_local.py` | **NOT ESTABLISHED** | absent from `crontab -l` and from the orchestrator's step list. The only invocation found in the tree is `run_option_snapshot_intraday_runner.py:519`, and whether **that** runner is scheduled is NOT ESTABLISHED — it appears in no crontab line read here. |

**Host named by the files' own headers / the registers: NOT ESTABLISHED for
`build_trade_signal_local.py`** — its header carries ENH history, not a host. The
crontab that runs the orchestrator is the AWS box's (`cd /home/ssm-user/meridian-engine`),
and CLAUDE.md's environment table names AWS `/home/ssm-user/meridian-engine` as
SHADOW and Local `C:\GammaEnginePython` as PRIMARY LIVE; which of the two is the
signal builder's runner is not stated in the file.

## PART A.3 — the "routes nothing" comment

`sql/2026-09-22_s81_v_gex_strike_rank.sql:258`, closing sentence of `COMMENT ON VIEW`:

> `Display-only per the S37 GEX-as-context-not-gate ruling; it routes nothing.`

**Does A.1 contradict it?** The claim is about **`v_gex_strike_rank`** specifically.
On that object: **no contradiction** — every reader found (`write_gex_cycle_history_local.py:152`,
`merdian_compute/cycle.py:62-102`, the Board) is a writer-of-history or display.

But the wider phrase "GEX-as-context-not-gate" **is** contradicted for a sibling
quantity: `gamma_metrics.regime` — derived from `net_gex` and `flip_level` by
`merdian_compute/gamma.py:425-430` `determine_regime(net_gex, flip_level)` — sets
`trade_allowed = False` at `build_trade_signal_local.py:611` and `:618`. So a GEX-derived
label does gate, even though the ranked view does not.

## PART A.4 — Board tiles (`~/meridian-connect/src`)

All tile definitions are in `src/components/board/LadderPanel.tsx`; the fetches are in
`src/lib/board.ts`.

| tile / panel | title shown | unit label shown | reads |
|---|---|---|---|
| Pin | `Pin (γ-conc)` | `strike · share of gross` | `v_gex_strike_rank` rank 1; lead = (share₁ − share₂) × 100 (`:22`) |
| Pin (positioning tab) | `Pin (γ-conc)` | `strike · share of gross \|γ\|` | `v_gex_strike_rank` rank 1 (ENH-125) (`:38`) |
| Runner-up | `Runner-up` | `strike · ratio to #1` | `v_gex_strike_rank` rank 2; ratio = share₂ ÷ share₁ (`gex_cycle_history.runnerup_share_ratio`) (`:39`) |
| Lead | `Lead` | `share points` | (share₁ − share₂) × 100 from `v_gex_strike_rank` (`:40`) |
| PIN BAND | `Pin band` | `strikes` | `v_gex_strike_pin_zone.pin_lower / pin_upper` (ENH-81) (`:44`) |
| Corridor | `Corridor` | `strikes` | `v_gex_strike_walls.put_wall, call_wall, corridor_state` (`:21`) |
| Call OI wall | `Call OI wall` | `strike` | `v_gex_strike_walls.call_wall` (`:33`) |
| Put OI wall | `Put OI wall` | `strike` | `v_gex_strike_walls.put_wall` (`:34`) |
| Net gamma | `Net Γ` | `₹ Cr per 1 % move` | `v_gex_abs_exposure_1pct.net_gex_cr_1pct` (`:19`, `:27`) |
| Gross gamma | `Gross \|Γ\|` | `₹ Cr per 1 % move` | `v_gex_abs_exposure_1pct.abs_gex_cr_1pct` (`:26`) |
| Top-strike share | `Top-strike share` | `share of gross \|γ\| (max \|γ\| ÷ Σ\|γ\|)` | `v_gex_concentration.hhi_net`, splits `hhi_call`, `hhi_put` (`:25`) |
| Net-long gamma strike | `Net-long γ strike` | `strike` | `gamma_metrics.max_gamma_strike` (`:29`) |
| Pin state | `Pin state` | `NO PIN · SHIFTING · STABLE · LOCKED` | `gex_cycle_history.pin_state` via `core/pin_state.py` at write time (`:41`) |
| Conviction | `Conviction` | `number (stage 1)` | `gex_cycle_history.conviction` (`:42`) |
| Legacy pin-risk | `Legacy pin-risk score` | `/100` | `gamma_metrics.pin_risk_score` (`:47`) |
| Flip | `Flip` | `index points` | **`v_gex_repriced_flip.flip`** — NOT `gamma_metrics.flip_level` (`:20`) |

**Regime / gamma_zone: no tile.** `gamma_metrics.gamma_zone` appears nowhere in
`src/`. A `regime` string is rendered by `src/components/NarrativeModal.tsx:22-27,
41, 94` and `src/components/AmbientTrajectory.tsx:14`, but that is the **ambient**
regime (`src/lib/queries.ts:316`, "Latest ambient regime snapshot"), not
`gamma_metrics.regime`. Whether the two are the same string is **NOT ESTABLISHED**.

Every tile's own `src` field reads `"sql/ file · COMMENT not live"`.

## PART A.5 — the ±1.5 σ window in `v_gex_strike_walls`

σ is **not** an input column; it is computed in the view, `sql/2026-09-15_s79_v_gex_strike_walls.sql:126-127`:

```sql
126:               (h.spot * v.atm_iv_avg::numeric / 100.0
127:                       * sqrt(GREATEST(h.dte, 1)::numeric / 252.0))::numeric AS sigma,
```

`v.atm_iv_avg` comes from a `LEFT JOIN LATERAL` on **`volatility_snapshots`**
(`:130-138`): the newest row for that symbol with `vs.ts <= h.ts` and
`atm_iv_avg IS NOT NULL`, ordered `vs.ts DESC LIMIT 1`, **with no age bound**. The
band multiplier is `COALESCE(get_parameter_num('wall.band.'||symbol), 1.5)` (`:114`);
both parameters read 1.5 live. Header `:18` states the same formula.

---

## PART B.1 — where the vendor gamma is read, and what is written

`ingest_option_chain_local.py`:

```python
282:            greeks = option_raw.get("greeks") or {}
308:                "gamma": to_float(greeks.get("gamma")),
174: def to_float(value: Any) -> float | None:
175:     if value is None:
176:         return None
177:     try:
178:         return float(value)
179:     except Exception:
180:         return None
```

- **No rounding anywhere.** `to_float` is a bare `float()` with no `round`, no
  quantisation and no scaling.
- **No `or 0` on gamma.** The only `or` is `option_raw.get("greeks") or {}` (`:282`),
  which defaults a missing *greeks block* to an empty dict.
- **When the vendor field is absent or null, `to_float` returns `None`**, so the row
  carries Python `None` → SQL `NULL`. A vendor literal `0` passes through as `0.0`.
  The two are therefore distinguishable at the ingest boundary; Part A of the earlier
  audit measured that in practice the vendor sends a literal `0` and never a null.
- Same treatment for `delta` `:307`, `theta` `:309`, `vega` `:310`, and
  `iv` `:306` (from `option_raw.get("implied_volatility")`, not from `greeks`).

## PART B.2 — is the raw vendor response stored?

**Yes.** `ingest_option_chain_local.py:311` `"raw": option_raw` — the whole per-leg
vendor object is written to `option_chain_snapshots.raw` (`jsonb`, ordinal 19).

Scope stated: this is the **per-leg** object, not the whole HTTP response. Whether the
full response envelope is persisted anywhere is **NOT ESTABLISHED**.

## PART B.3 — catalog

| table | column | data_type | numeric_precision | numeric_scale |
|---|---|---|---|---|
| `option_chain_snapshots` | `gamma` | numeric | (null) | (null) |
| `option_chain_snapshots` | `iv` | numeric | (null) | (null) |
| `option_chain_snapshots` | `delta` | numeric | (null) | (null) |
| `option_chain_snapshots` | `vega` | numeric | (null) | (null) |
| `gex_strike_snapshots` | `gamma_call` | double precision | 53 | (null) |
| `gex_strike_snapshots` | `gamma_put` | double precision | 53 | (null) |
| `gex_strike_snapshots` | `gex_cr` | numeric | (null) | (null) |

The four `option_chain_snapshots` columns and `gex_cr` are **unconstrained `numeric`**
— no declared precision or scale, so the stored value keeps the scale it arrived with
and "decimal places present" is a meaningful question for them. `gamma_call` /
`gamma_put` are binary **`double precision`**, where it is not.

## PART B.4 — decimal places actually present

Latest run per symbol, by `run_id` (plan: `Index Scan using idx_ocs_run_id`, estimate
1,141 rows, no Seq Scan; 2.73 s).

| run_id | symbol | leg | bucket | legs |
|---|---|---|---|---|
| `612692d1…5501` | NIFTY | CE | dp=4 | 3 |
| | | CE | dp=5 | 43 |
| | | CE | zero | 230 |
| | | PE | dp=3 | 1 |
| | | PE | dp=4 | 3 |
| | | PE | dp=5 | 115 |
| | | PE | zero | 157 |
| `e7793aef…2c03` | SENSEX | CE | dp=4 | 3 |
| | | CE | dp=5 | 55 |
| | | CE | zero | 197 |
| | | PE | dp=4 | 9 |
| | | PE | dp=5 | 142 |
| | | PE | zero | 104 |

- **`gamma IS NULL`: 0 legs on both runs, both option types.**
- **`gamma = 0`: 230 CE + 157 PE (NIFTY), 197 CE + 104 PE (SENSEX).**
- The maximum decimal places present is **5**. The dp=3 and dp=4 rows are
  trailing-zero suppression of a 5-dp lattice value (e.g. `0.00120` stored as
  `0.0012`), not extra precision.
- The question is meaningful here because the column is unconstrained `numeric`; it
  would **not** be meaningful for `gex_strike_snapshots.gamma_call/gamma_put`, which
  are `double precision`.

## PART B.5 — where a vendor 0 becomes NULL

`merdian_compute/gamma.py:719-730`, inside `build_gss_rows`:

```python
719:            "gamma_call": None,
720:            "gamma_put": None,
…
723:        if opt_type == "CE":
724:            bucket["oi_call"] += oi
725:            if bucket["gamma_call"] is None and gamma_raw != 0.0:
726:                bucket["gamma_call"] = gamma_raw
727:        elif opt_type == "PE":
728:            bucket["oi_put"] += oi
729:            if bucket["gamma_put"] is None and gamma_raw != 0.0:
730:                bucket["gamma_put"] = gamma_raw
```

Both fields are initialised `None` (`:719-720`) and are only overwritten when
`gamma_raw != 0.0`. A vendor `0` therefore leaves the field at `None` and is written
to `gex_strike_snapshots` as **NULL** — the chain stores `0`, the strike table stores
`NULL`, and the two are not distinguishable downstream of this line.

`gamma_raw` is read at `:711` `gamma_raw = to_float(row.get("gamma"))`, and the
exposure contribution at `:712` `gex_contrib = signed_gamma_exposure(row, spot)`,
whose own first exit (`:42`) returns `0.0` when `gamma == 0.0`.
