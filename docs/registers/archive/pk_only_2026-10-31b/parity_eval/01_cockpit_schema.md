# Parity target — live terminal: the `cockpit` payload (schema + method statements)

Captured 2026-10-13 ~07:50 IST, pre-open. Source: the terminal's own data call for one index, `cockpit/<SYMBOL>`
(response recorded from the app's own request; no credential handled). Example values are FINNIFTY, last session
12 Oct, as-of 15:40 IST, `is_stale=true`, `market_open=false`. Schema is the same for every index (one call per index).

## Top level
symbol · spot · expiry (front) · hours_to_expiry · is_expiry_day · atm_iv (fraction) · fetched_at · as_of · is_stale ·
market_open · as_of_ts · stale_since · snapshot{previous_day_date, baseline_absent_strikes[], rows_in_chain}

## Two GEX engines, side by side (the "flow vs book" idea is structural, not a panel)
- `engines.india_standing_flip` — **standing OI** (all OI on the front expiry, now): total_gex_cr, flip_level +
  flip_status (IN_RANGE…) + flip_bound, **zero_gamma_level** + status + **roots count**, `gamma_curve` (128 spot
  points × net GEX — "Cr per 1% move, if spot stood at each price"), max_gamma_strike, call_wall, put_wall.
- `engines.india_doi` — **ΔOI since the baseline close** (dealer-classified): total/call/put gex, flip, zero gamma,
  max_gamma_strike, **quality** (GOOD…), **theta_dominated** (bool), both_legs_down_pct, legs_down_pct, warning,
  **hhi_gamma** + **hhi_regime** (balanced…).
- `convergence` — state (same_sign…), signal_a = standing (net, gross, **net_to_gross**), signal_b = ΔOI flow
  (+ baseline_date, has_baseline, usable, classification_quality). Each signal carries basis, engine, sign_convention
  = `india`, reference sentence, **unit = cr_per_1pct_move**, **t_norm_baseline_days = 5**.

**Unit statement (E-1 lead):** every GEX figure is "₹ Cr per 1% move". MERIDIAN's `gex_cr` is γ·OI·S²/1e7 with no
×0.01. Their NIFTY net 12 Oct close = +10.92K Cr; MERIDIAN's NIFTY figures have run ~10⁵–10⁶ "Cr". Hypothesis to
test at the same minute: ratio ≈ 100 (per-1% factor) × any OI-unit factor (they state OI in **shares**). Not yet tested.

## Regime
label (POSITIVE_GAMMA…) · source = india_standing_flip · has_signal · usable · flip_level · distance_to_flip_pct ·
max_gamma_strike · distance_to_max_gamma_pct.

## Pin — two objects
- `pin_risk`: score, probability, pin_strike, pin_window_pts, narrative; components {distance, strength, time, regime,
  distance_pct, **sigma_band_pts**}.
- `pin_conviction`: pin_strike, raw_top_strike, score (0–100), strength, score_band_lo/hi, raw_score, saturated,
  strength_ceiling_cr (25 on FINNIFTY), **gamma_basis = delta_oi** (pin is ranked on the ΔOI book, not standing),
  **margin**, **state** (STABLE…) + **state_held_seconds**, runner_up{strike, score}, top_5[], **pressure_by_strike
  {strikes, P}**, narrative; components {gamma_at_top, distance_pts, hours_to_expiry, **time_amplifier =
  time_amplifier_expiry × time_amplifier_tod**, sigma_pts}. → the "time boost" splits into an expiry term and a
  **time-of-day** term (FINNIFTY at 15 DTE: expiry 1.0, tod 1.495).

## Delta
- `dex`: call/put/net_dex_cr (standing OI), flow_* (oi_change, this session vs previous close), lot_size.
- `delta_positioning` (vs previous close) and `delta_positioning_intraday` (since today's first snapshot):
  per side {long_buildup, short_buildup, short_cover, long_unwind, unclassified} in Cr, net_initiated_cr,
  classified_doi_shares / total_doi_shares → **classified_share**. Basis: "oi_change × delta, signed by the
  dealer_positioning class". → this is the **D-4 four-case** MERIDIAN declined (S96-I), live and quantified.
- `delta_positioning_prev_session`.

## Flows / second order
- `flows.moves[6]` (hedge ladder ±0.5/1/2 %).
- `charm`: "change in gamma exposure over time (**not charm**)" — decay[6] horizons, by_strike call/put/net.
- `vanna`: "change in gamma exposure with IV (**not vanna**)" — shifts[31] (−15…+15 IV pts), by_strike.
- `charm_exposure`: "Rs Cr of delta, change over one day", horizon 24 h, per strike + total.
- `vanna_exposure`: "Rs Cr of delta per +1 IV point", per strike + total.
  → they label the gamma-sensitivities "not charm/vanna" and carry the delta-sensitivities separately — the same
  naming discipline as MERIDIAN's L78-1 (∂Δ/∂t, ∂Γ/∂t …).

## Per strike (64 strikes on FINNIFTY; window around spot)
india_doi, call/put_gex, call/put/net_dex, dex flow + initiated (session and intraday), **call/put_class** (+ intraday),
call/put_oi, oi_change (+ intraday), volume, ltp, ltp_change, **iv**, **delta**, gamma, decay, dealer_long,
dealer_short, call/put_gex_doi.

## Order book (MERIDIAN has nothing like this)
per strike bid/ask/qty/delta for both legs; `resting.call_balance / put_balance` = (resting buy − resting sell)/sum,
per strike and total, "at this tick".

## Other endpoints seen on load
me · me/workspace · settings/status · live/vix · live/<SYM> · cockpit/<SYM>(?peek=1 for non-focused indices) ·
gex_daily_history/<SYM> · gex_by_expiry/<SYM> · gex_by_strike_expiry/<SYM> · density_intraday/<SYM> ·
density_intraday/<SYM>/dates?days=30 · updates.json · build.json. Auth: Cognito (ap-south-1). Front end: Next.js.
