# Engine-side note for the OFL stream — anchoring the tape on the Board pin (S105, 2026-11-07)

Answers to the four questions in the OFL aside, plus what measuring at the pin would add. Sources: ENH-125 (`v_gex_strike_rank`), ENH-133 (`gex_cycle_history` / `v_pin_board`), ENH-124 / S80.B (`v_gex_pin_maxpain`, `gex_pin_maxpain_history`), S94 rulings (P1, S94-B/C), P2 result, manual v0.4 §2.6 / §3.2.

## 1. Pin identity

- The Board **PIN (γ-conc)** tile (e.g. `25,000 · 11.0 % of gross · dampening`) is `v_gex_strike_rank` rank 1: strikes ordered by `abs(gex_cr)` within the latest γ run; the tile shows `share_of_abs`, whose argmax is the same strike. The γ run is single-expiry by construction (`infer_expiry_date()` raises on more than one), so front expiry is implicit.
- **Board PIN ≡ rank 1 ≡ T1b `leader_strike` on the same `run_id`.** Anchor by `run_id`, never by nearest timestamp.
- **Two other "pins" exist and are different objects — do not anchor on them:** the **PIN BAND** (`v_gex_strike_pin_zone`, the τ-weighted zone, `peak_pin_strike` = argmax of *positive* `gex_cr` within the τ walk; sign-filtered, can disagree with the tile — manual F-13), and `gex_pin_maxpain_history` (11,795 runs), which stores the band peak, not the tile pin.

## 2. "Price moves to and through the pin" — engine pre-registers it (P1d), not the tape

- P1 (S94, n = 85 NIFTY) tested where the day's high/low lands; it did not test touch-and-cross. Per S94-C a new claim is a new pre-registration.
- Engine stream will pre-register **P1d**: unit = (symbol, run) with pin at signed distance d from spot, |d| ≥ 1 step; outcome = touch / through within 30 min, 60 min, to 15:14 IST; **null = the mirror strike at spot − d** on the same path (paired, no σ definition needed); strata for reporting only: DTE 0/1/2+, |d| in steps, LEAD < 1 pt, PIN STATE. Source: Board pin recomputed per run from `gex_strike_snapshots` (2026-05-25 →), spot from `hist_spot_bars_1m` scoped 09:15–15:14 IST (the 15:14–15:29 hole and the CAS bar are by design, see S105 live reads §5).
- Pre-declared caveat: NIFTY 0-DTE is the one cell where pin ≡ max pain runs 13.9 % (ENH-124); a result confined there is expiry pinning, not "price moves to the pin".
- **P1d decides H-C's December slot:** NO → the pin label stays display-only; YES → its base rate is H-C's threshold.

## 3. The pin's intraday clock — read `gex_cycle_history`

- "Pin moved from K0" and any event clock read **`gex_cycle_history`** (ENH-133: per-cycle leader, `held_for_cycles`, LEADER TODAY segments; `v_pin_board` sits on it), so `/tape` and the Board never disagree about when the pin moved.
- The tape's per-run `leader_strike` stays as the recorded copy; the pre-registration asserts `leader_strike = gex_cycle_history` leader per cycle and excludes (and counts) mismatches.
- ENH-133 rows are **revisable until reconciled** after the close: live labels use live rows; December scoring uses reconciled rows only.
- The pin updates per γ run (5-min, after its own chain run, S98-B); tape bins are 1-min. Join by cycle.

## 4. What would make a flow label at the pin misleading

- **Small LEAD** — the leader hops between #1 and #2 when the lead is under ~1 pt. Label flow at the pin only when PIN STATE is STABLE / LOCKED; under SHIFTING show "pin contested" and label both top-2. No new threshold.
- **0-DTE** — concentration collapses to ATM; HIT / ABSORBED fire by construction. Suppress the pin label at DTE 0 or print the stratum on it.
- **The pin is sign-blind** (gross |γ|); the leader can be amplifying. Carry the sign (the tile already prints dampening / amplifying) or the reading inverts.
- **Pin ≡ wall** is common (the `≡ CALL OI WALL` pill). Rule a precedence so one strike-leg is never labelled twice; the Board's ≡ convention is the model.
- The **−0.4 σ max-pain offset** is a distance, never a definition; never call max pain "the pin" on `/tape`. The PIN BAND, if ever drawn, is named as such.

## 5. What measuring at the pin adds that the walls cannot

- **Walls** are raw OI with no sign. Tape at a wall answers *does the level hold* (a level test, P1's family).
- **The pin** is the only Board level with a **sign**, i.e. a claim about hedging *direction*. Tape at the pin answers *which way do hedgers lean when price is here*. Expected, if the Board's sign is right:

| Pin sign | Hedger behaviour as spot approaches | Expected tape label at the pin |
|---|---|---|
| Dampening (dealers long γ) | sell the rally / buy the dip — against the move | **ABSORBED** (CONC hit, book holds); resting imbalance against the move; price reaches and stalls |
| Amplifying (dealers short γ) | buy the rally / sell the dip — with the move | **HIT** (CONC + THIN-ask); resting imbalance with the move; price goes through |

- "More action" is the wrong axis — |γ| is the same either way; the axis is flow **with vs against** the move, which ABSORBED vs HIT already encodes.
- **Not vice versa:** the Board cannot confirm the tape (it has no flow). The board predicts, the tape checks. An off-diagonal (ABSORBED at an amplifying pin, HIT at a dampening one) means the sign is wrong for that regime — the P2 finding, now testable intraday without NSE's participant file.
- This makes the better **H-C** a 2 × 2 — pin sign × tape label at approach, on cycles where spot comes within one step of the pin, null = label independent of sign, H-B's machinery. P1d (is the pin a destination) and the 2 × 2 (what happens on arrival) are separate questions.

## 6. Recommendation and order

1. Add the pin label to `/tape`, display-only, with the ≡ precedence and 0-DTE suppression above. No pipeline change (`leader_strike` is already in the rows).
2. **Overlap read first (this week):** how often the pin sits on a wall, from `gex_cycle_history` × wall history. If it is a wall most of the time the pin label is a relabel and the 2 × 2 runs on the existing wall rows with the sign joined; if usually a third strike, it is new coverage. Note the pin sits near the money and walls OTM, so the pin is visited far more often — more power, more ATM noise; stratify, don't pool.
3. Engine stream pre-registers P1d now (hash before the first query).
4. Pre-register the 2 × 2 as H-C only if the overlap is low enough that the pin is a third location on most sessions, and after P1d reports.
