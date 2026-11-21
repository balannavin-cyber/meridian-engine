# Findings — parity target vs MERIDIAN (running)

## F1 — Their GEX is time-normalised: GEX = γ · OI · S² · 1% / 1e7 · √(τ / 5 d)  — MEASURED, exact
- NIFTY, 12 Oct close, strikes 22,300–22,500, both legs (10 values): their `call_gex` / `put_gex` divided by
  γ · OI(shares) · S² · 0.01 / 1e7 = **0.44726 on every leg**; √(hours_to_expiry / 24 / 5) = √(24.0045/120) =
  **0.44726**. Matches to 5 decimals.
- Inputs as carried in their payload: `gamma` (one value per strike, both legs), OI in **lakh shares** in the
  per-strike arrays (UI shows shares: 170.97 → 17.10M), S = spot, τ = **calendar hours to 15:40 IST** on expiry day.
- `t_norm_baseline_days = 5` in every signal block is the normaliser: gamma exposure is scaled to what it would be
  at 5 days to expiry, so a 0-DTE book does not dwarf a 5-DTE one. At τ = 5 d the factor is 1; at τ → 0 it → 0.
- **Consequence for MERIDIAN (E-1):** MERIDIAN `gex_cr` = γ · oi · S² / 1e7 — no 1 % factor, no √(τ/5). The two
  differ by 100 × √(5/τ) × (OI-unit factor), the last pending query 5. **No figure of theirs is comparable to ours
  without this transform, and the factor changes every minute towards expiry.** Every R2.4 net-GEX magnitude
  comparison needs re-reading through it (the sign comparison is unaffected — the factor is positive).
- **Design question for us:** a √τ-normalised GEX makes regime size comparable across DTE and stops expiry-day
  numbers exploding; ours explodes into expiry by construction. Candidate: carry both (raw and τ-normalised), label
  the unit, never mix.

## F2 — Their flip = zero of the net-GEX-vs-spot curve (since 15 Sep) — STATED + OBSERVED
- What's new, 15 Sep: flip = "the spot at which the book's net gamma is zero", the regime sign's own calculation;
  the strike-axis running total retired; sessions under the old method are left out of the charts.
- Payload: UI FLIP = `zero_gamma_level` (+ status, **roots count**), from `gamma_curve` (128 spots). The separate
  `flip_level` field (22,558.9 vs UI 22,296.9) is not what is displayed.
- = ENH-131's construction (repriced zero-gamma over a spot grid). Our S84 L3 "D3 deviation" no longer stands as
  written; the R2.4 flip finding (reference always lower, median 407 pts, vs the **legacy** `flip_level`) was
  measured against their retired construction. Same-moment check pending (query 2).
- Their curve is √τ-normalised (F1); the zero crossing is unaffected by a positive scale factor **only if** τ is
  held constant across the spot grid — it is, so the root is comparable with ours.

## F3 — Concentration over a fixed 72-strike window (since 23 Sep) — STATED + OBSERVED
- HHI by expiry shows 72 strikes per expiry; What's new 23 Sep: "covers a fixed number of strikes". Their `hhi_gamma`
  sits in `india_doi` (the **ΔOI** book), regime word balanced/dispersed/compressed at 0.10 / 0.25.
- Explains R2.4's ≈2.09× HHI ratio (theirs window-denominated, ours every strike in the run). Also: theirs is
  on the ΔOI book, ours on the standing book — two differences, not one.

## F4 — Their pin is ranked on the ΔOI book; time amplifier = expiry term × time-of-day term — OBSERVED
- `pin_conviction.gamma_basis = delta_oi`. Pressure = "Γ × distance decay around spot × time amplifier".
- `time_amplifier = time_amplifier_expiry × time_amplifier_tod`; at 15:40 tod = 1.495 on both indices;
  expiry term 2.469 at τ = 24 h, 1.653 at 72 h. Fit from intraday rows owed.
- Pin tab shows SETTLEMENT probability ("21 % within ±50 pts at expiry") and "By tomorrow +363 % change in Γ at
  the pin" — a forward projection we do not have.

## F5 — The D-4 four-case is live in theirs and quantified — OBSERVED
- `delta_positioning` (vs previous close) and `_intraday` (since first snapshot): per side long_buildup,
  short_buildup, short_cover, long_unwind, unclassified (Cr of delta), classified_share (0.997 FINNIFTY),
  per-strike `call_class` / `put_class`. Signed "by the dealer_positioning class". MERIDIAN declined D-4 on
  evidence (S96-I); their classification quality and theta_dominated / legs_down flags are the guards they use.

## F7 — First same-day pair: 12 Oct close (theirs 15:40 IST; ours γ-run 15:20 IST, chain 15:40 IST)
MERIDIAN read through `roq.sh` pre-open 13 Oct (latest-only views still on 12 Oct). **Not the same minute on the
γ clock**: MERIDIAN's last γ run of 12 Oct is **09:50 UTC = 15:20 IST** (spot 22,316.85); theirs is 15:40
(22,363.35). The flip view is on the chain clock (15:40) and is a true same-minute pair.

**MERIDIAN `gex_cr` unit, recomputed:** 22,500 strike = (γc·OIc − γp·OIp)·S²/1e7 with OI in **shares** →
1,045,178 = stored 1,045,177.6. So ours = γ · OI(shares) · S² / 1e7 — **no 1 % factor, no √τ term**.
Theirs (F1) = ours × 0.01 × √(τ/5 d), plus a **single γ per strike** (one IV per strike) where ours uses the
vendor's separate CE and PE gammas, **stored at 3 significant figures** (0.00135 / 0.00138).

| item | MERIDIAN | target | read |
|---|---|---|---|
| NIFTY net GEX → their units | 1,721,363 → **7,751** (15:20) | **10,974** (15:40) | different moment; settle live |
| NIFTY gross → their units · net/gross | 10,421,547 → 46,929 · **0.165** | 38,945 · **0.282** | as above |
| SENSEX net → their units | 477,664 → **3,709** | **3,417** | within 8.5 % across 20 min |
| SENSEX gross · net/gross | 13,059 · **0.284** | 12,141 · **0.281** | net/gross agrees to 0.003 |
| **NIFTY flip (same minute, 15:40 chain)** | **22,273.7** (OK, neg→pos, 1 crossing) | **22,296.9** (OK, 1 root) | **−23 pts (0.10 %)** |
| **SENSEX flip (same minute)** | **71,380.4** | **71,536.4** | **−156 pts (0.22 %)** |
| NIFTY walls put / call | 22,300 / **22,600** | 22,300 / **22,500** | call wall differs — method (below) |
| SENSEX walls put / call | **70,000 / 73,000** | **71,500 / 72,000** | method (below) |
| NIFTY pin · state | 22,500 · SHIFTING · conv 0.09 | 22,350 · STABLE · 72 | construct differs (D-5a) |
| SENSEX pin · state | 72,500 · STABLE · 49 cycles | 71,900 · STABLE · 1,288 s | construct differs |
| NIFTY HHI | 0.058 (`conc_hhi`) | 0.103 (ΔOI book, 72 strikes) | book + window differ |
| SENSEX HHI | 0.031 | 0.101 | as above |
| NIFTY max pain | 22,400 | 22,400 | **agree** |

**Walls — their method, measured from their own per-strike arrays:** call wall = argmax **call GEX** over the
window (NIFTY 22,500 at 5,527.7 Cr, while max call OI is 22,600 at 18.23M); put wall = argmin **put GEX**
(22,300; max put OI below spot is 22,000). SENSEX identical pattern (72,000 / 71,500 vs OI 74,000 / 70,000).
→ The target uses exactly the **gamma-weighted** wall S79 measured and rejected ("collapses to ATM"): theirs sit
+0.6 % / −0.3 % from spot. MERIDIAN's ENH-120 raw-OI-in-band walls are the written-OI edges. **Two different
objects with one name.** The board-design E-3 "γ ceiling / floor" slot is where theirs belongs; do not relabel ours.

**NIFTY OI disagrees materially strike by strike** (ours 15:20 vs theirs 15:40): 22,500 CE 20.43M vs 17.10M;
22,400 CE 17.49M vs 12.45M; 22,300 PE 15.90M vs 10.59M (ratios 0.67–0.84, not constant). Twenty minutes does not
plausibly explain a 30 % fall. Source or snapshot difference — the first live same-minute read settles it. SENSEX
gross agrees within 7 %, which points at the NIFTY source specifically.

## F6 — Things they have that MERIDIAN has no substrate for
- Resting order book per strike (bid/ask/qty), `resting balance` per strike and total, and an **Aggressor**
  timeline (buy−sell)/(buy+sell) per interval.
- RV 10/20/30/60D close-to-close beside ATM IV (IV − RV spread).
- Volume ÷ OI rank with a positioning word per strike ("Unusual volume").
- BANKNIFTY, FINNIFTY, MIDCPNIFTY.
- Full-session replay scrubber on every pane; 30-session histories.
- Broker-token monitoring with a phone call if the connection drops before the open.
- **Added 2026-11-15 (vendor statements, unverified; detail in `05_parity_target_updates_2026-11-15_synthesis.md`):**
  - Futures OI build-up classification (price × futures OI: long build-up, short build-up, short covering, long unwinding), intraday and per-minute, announced 2026-11-15. MERIDIAN has no substrate read yet (05 doc §5).
  - Unusual-volume bursts against a strike's own normal pace, with a published validation (62 % lift over chance, buyer-led bursts followed by OI falling 5 : 1). MERIDIAN's tape recorder is the only substrate.
  - An option-volume view combining OI and volume in one number (definition unread).
