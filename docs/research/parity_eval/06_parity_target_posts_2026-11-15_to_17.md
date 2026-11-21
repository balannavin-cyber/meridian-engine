# The parity target's author: posts 2026-11-15 to 2026-11-17, read against the futures OI lane (MR-FOI)

Engine / futures OI lane. Read Wed 2026-11-18 ~07:00 IST through the operator's Chrome, on the author's X profile (Posts tab, logged in as the operator). **Rules nothing, reopens nothing.** Continues `claude/parity_eval/05_parity_target_updates_2026-11-15_synthesis.md`, whose read stopped at 2026-11-15 ~11:40 IST. Everything below is the author's own statement; nothing was seen inside the product.

## 0. How this was read, and its limits

- 22 posts dated after the previous read (11-15 ~21:16 IST to 11-17 ~16:43 IST). Fewer than the 25 asked for: the earlier ones are already in 05_.
- Text only, and only the first ~300 characters of each post. Images, replies, quoted posts and anything behind "Show more" were not read. The 11-17 ~16:15 post ("you won't be able to unsee this") is image-only.
- Product pricing (a basic and a pro plan from Rs 1,499 a month, posted 11-17) is noted, not analysed.

## 1. Futures OI statements in these posts

| When (IST) | Statement |
|---|---|
| 11-17 ~12:12 | "We have just moved from short covering to long build up." |
| 11-17 ~12:13 | Unusual volume on the ITM put side from 11:00; at 12:00 volume surged, "exactly the point the futures became long build up". "Data matters. Price moves due to positioning." |
| 11-17 ~14:27 | Unusual volume at 13:15 with large positive delta on the 25400 call. Says delta is printed at the close of the candle, so the move could be acted on when volume appears. |
| 11-16 ~13:40 | Futures premium +25.3 points against a usual +33.2 for this stage of expiry: "pay attention to the deviation". |

Other posts: the Straddle Decay Clock (actual against usual premium decay by minute; a 25,300 straddle called at about Rs 181 against an actual close of Rs 176.1), P&L posts (self-reported), strike and wall commentary, a pinned header image reading "You already have the open interest. This is the layer underneath it."

## 2. Against what the lane has tested

| His statement | Our test | Status |
|---|---|---|
| Price × futures OI class as a read | Stage 1 (30-min continuation, design period 2025-04 to 2026-03) | **Null.** NIFTY S −0.35 bp (one-sided lower bound −2.08), SENSEX −1.51 bp (−3.14); rule 8a NOT MET on both. Holdout sealed. |
| The class combined with unusual volume and initiated delta (11-17 posts) | none | **Not tested.** His live use is the combination, not the class alone. |
| Futures as a hedge footprint | M1, M2 (`futoi_M1_M2_prereg_2026-11-17.md`) | Our thesis, not his. M1 scored 2026-11-17/18: NOT DETECTED (38 events); M2 pending. |
| Basis against its usual level for the stage of expiry (11-16) | none | **Not tested.** M2 tests the change in basis against spot moves scaled by γ, not the level against a norm. |
| Unusual volume, aggressor tagging, OI after buyer-led bursts (05_ H4) | tape lane | Not covered by the futures lane. |
| Straddle decay, actual against usual | none | Not a futures item; not tested. |

Reading, not a ruling: his public use of futures OI is descriptive and confirmed by other layers. Stage 1's null says the class alone did not predict on our design period, which does not conflict with that.

## 3. Candidates for the next pre-registration (operator's call; none started)

1. **Basis level against the usual level for days to expiry.** Norm built from the vendor and Fyers futures history on the design period only (futures data after 2026-03-30 stays sealed under Stage 1); deviation then tested against forward spot and basis moves. Needs its own pre-registration, a sealed holdout, and a stated null.
2. **Class × unusual volume × initiated delta as a combination.** Substrate is the tape lane's minute data and tagged days from 2026-11-05; operator-only first.

Tests 3-6 of the lane's own list (retention, SENSEX γ in NIFTY futures, ∂Δ/∂σ and ∂Δ/∂t flows, participant nowcast) stay conditional on M1 or M2 showing the mechanism.
