# Pre-registration v4 — Weekly-Cycle Premium Engine (DRAFT)

| Field | Value |
|---|---|
| **Status** | DRAFT v4 — supersedes v1/v2/v3 (same day). ENH ID to be assigned by operator. |
| **Stage** | **Measure** only. The exploration brief runs **before** any parameter here is frozen. |
| **Capital** | ₹20,00,000 (simulated) · **R = 2 % = ₹40,000 per setup, hard** |
| **Unit of trade** | One **weekly expiry cycle** per symbol = one setup |

**What changed from v3.** A 500-post extract of @AshwinBadri2 (2026-03-06 → 2026-09-21) contradicted four things v3 asserted. Each is now either a measured arm or a corrected rule:

| v3 said | Evidence | v4 |
|---|---|---|
| Harvest at 75 % of credit | He books at ~50 %, and sometimes on a positioning read instead of a % | §5.1 — band swept 50/60/70/80, plus an extraction-exhausted exit |
| Wing bought at entry | He sells first and buys wings **after** premium collapses | §1.3 — two arms, W-ENTRY vs W-DEFER, measured |
| Adds go on the same short strike | He layers *different* legs onto a core | §3.3 — layered adds; averaging into a loser is banned outright |
| No vega term anywhere | Vega is his single most expensive recorded loss (₹1Cr+) | §1.4 — net vega constraint |

---

## 0. Reference practitioner — evidence base

Source: 500 posts, 2026-03-06 → 2026-09-21. This is a **partial window** — the requested 2025-09 → 2026-03 period is absent and 500 is likely an extraction cap. Treat everything below as evidence about one trader in one regime, not as validation.

### 0.1 "Risk-defined" here means over-hedged, not spread-hedged

- *"Even if you're non directional, you have to have your payoff in such a way where these overnight risks should work in favour of you"* (Mar 9)
- *"Futures short. Weekly straddle on. Put credit spread stacked. Monthly puts sold. All of it over hedged with weekly options… Overnight risk should work for you, not against you."* (Mar 11)
- *"Carrying over 7000 lots of hedges over the weekend which is definitely hurting the profitability big time but any gaps my positions becomes risk free"* (Mar 20)
- *"I'm not driven by returns. I'm driven by the fear of losing control… If risk is defined and respected, returns become a byproduct."* (Mar 24)

Outcomes he states: a position that *"went massively wrong directionally and… still refused to lose more than 0.5 %"* on ₹11.5Cr (Sep 2); one fully specified payoff at max ₹24L / defined stop ₹7.5L / exit 15:14 (Aug 18).

**Design consequence:** v3's floor of −R is the *minimum* bar. Over-hedging (floor ≥ 0 at the tails) is a distinct objective that costs theta. It enters as **Arm OH** (§4).

### 0.2 Hedge timing is the affordability mechanism

- *"I have booked my overnight positions in the morning in profit and have taken a short gamma position. After an hour or so, I have bought the hedges post the premiums have collapsed."* (Apr 7)
- *"I will look to buy some cheap weekly wings around 2PM for a peaceful weekend!"* (Jun 12)

A wing bought after decay costs a fraction of one bought at entry — that is what makes carrying surplus wings viable. The cost is an unhedged window. **Measured, not assumed:** §1.3 and brief M6.

### 0.3 How he builds

- *"I start small, let the market reveal itself, and keep sizing as the thesis either strengthens or needs to be challenged… the ability to adapt, change my view, fight the market when necessary, and still stay alive"* (Aug 21)
- *"Started with synthetic longs + CE shorts. Added more CEs, averaged the synthetic longs, and layered in some put shorts."* (Aug 19)
- Opened the May series as a bull call spread with bi-weekly CE shorts, then *"converted my bull call into a ratio spread as I shorted additional inflated CE"* (Apr 28–29)

He sells into **inflated premium** — *"used the upmove to short additional shorts"* (Aug 31) — not at a level per se.

### 0.4 Three recorded losses, three distinct mechanisms

| Date | Size | Mechanism | Rule it produces |
|---|---|---|---|
| Apr 13 | ₹1Cr+ | Negative vega into a volatile regime before a holiday. *"No matter how well hedged you think you are… your hedges won't respond the way you expect. They lag."* Intent was flat vega via a smaller straddle and heavier strangle; it still failed. | §1.4 vega constraint |
| Jun 3 | ₹11.5L | Averaged into a losing synthetic long. *"I averaged into the position in the morning, expecting a response. It never came. The moment PDL broke and sustained, I exited everything."* | §3.4 no averaging |
| Apr 24 | ₹6L | Execution only — 950 lots, throttled API market orders, ₹3L to exit and ₹3L more shifting put hedges | §6 liquidity cap; not binding at ₹20L |

Also: stopped out at ₹14.8L, re-entered the same thesis, closed +₹16L (Jul 7) → §5.6 re-entry is permitted.

### 0.5 Not transferable
₹20–25Cr margin and 950–7,000-lot clips — execution is his binding constraint and is not yours at ₹20L. His toolkit is also **wider** than this pre-reg's: FVG, PDL, VWAP, VAH, VPOC, absorption *and* GEX. Plain S/R here is a deliberate simplification for testability, not a claim that levels alone are what he trades.

---

## 1. Risk backbone

```
cash        = Σ premium received − Σ premium paid − costs    (since setup open)
floor       = min over terminal spot S of Σ payoff(open legs, S)
worst_case  = cash + floor
INVARIANT   worst_case ≥ −R      checked before EVERY action; lots = max satisfying it
```

### 1.1 Properties
- Every short leg is covered by a same-type, same-expiry long wing of equal or greater quantity → 2 % holds through gaps and events.
- A condor can only lose on one side at expiry, so `floor = −max(W_put, W_call) × qty`.
- Adding the opposite side **adds credit without lowering the floor** → it can only improve `worst_case`. The opposite-side decision is therefore an edge question, never a budget question.

### 1.2 Same expiry only — what is excluded and why
- **Calendars / diagonals** (his 24000 PE May/June, 25000 PE Sep/Dec): the far leg's value at the near expiry is **model-dependent**, so `floor` stops being a payoff number and becomes a vol-surface estimate. The 2 % guarantee would be an assumption, not an identity. **Excluded from v4; a separate pre-reg if wanted.**
- **Futures / synthetic legs:** unbounded floor. Excluded.

### 1.3 Wing timing — TWO ARMS, measured
| Arm | Rule |
|---|---|
| **W-ENTRY** | Wing bought with the short. Invariant holds continuously. |
| **W-DEFER** | Short sold first; wing bought when the short's premium has decayed ≥ 30 %, **or** by 14:00 the same session, whichever is first. Between the two, the position is naked. |

W-DEFER is admissible **only** under a strict cap: the deferred quantity is sized so that a **3 σ_daily adverse gap, unhedged, still costs ≤ R**. That is a much smaller clip than the hedged size — the whole point of M6 is to price the trade-off (cheaper wing vs smaller position).

**No overnight naked exposure, ever.** A wing not filled by 14:00 forces the short closed.

### 1.4 Vega constraint — new, from the Apr 13 loss
- Net vega per setup is computed at every action and recorded.
- **Hard rule:** a setup may not hold net negative vega when *both* IV − RV(5d) is narrowing **and** the ATM straddle has risen day-over-day. Flatten vega by buying nearer wings, or cut size.
- **Holiday/weekend rule:** before any non-trading gap of ≥ 2 days, net vega must be ≥ 0 or the setup is closed. His case was a holiday; the hedges lagged; the intent to be vega-flat did not survive the move.
- Vega is a **constraint**, not a signal. Nothing is entered because of it.

---

## 2. Levels — plain support / resistance, mechanical

Computed each evening from spot bars (5m resampled to 1H/D/W; IST-labelled +00:00, so `replace(tzinfo=None)`).

| Source | Rule | Weight |
|---|---|---|
| Weekly swing pivot | Fractal high/low, 2 bars each side, last 52 weeks | 3 |
| Prior week high / low | | 2 |
| Daily swing pivot | Fractal, 2 bars each side, last 60 sessions | 1 |
| Prior day high / low | | 1 |
| Round number | NIFTY ×500, SENSEX ×1,000 | 1 |
| Touches | Each prior daily bar whose wick entered the zone and closed back out | +1 each, cap 3 |

- **Cluster:** merge levels within 0.2 σ_daily into one zone. Strength = Σ weights. Tradeable at **strength ≥ 4** (swept in M2).
- **Polarity:** a zone broken on a daily close flips role.
- **Tags only, never required:** ICT zones, ENH-120 walls (`wall_confluence`).

**Events, on 1H bars:** *test-and-hold* = trades into the zone, closes back out on the original side. *Break* = 1H close beyond the zone by > 0.25 σ_daily.

---

## 3. The cycle builder

NIFTY cycle = day after expiry → next expiry; SENSEX likewise. **Expiry weekday is read from the data, never hardcoded.** Day numbers count trading days from cycle open.

### 3.1 Cycle-open map
Record: S/R zones · **EM** = ATM straddle at Day-1 10:30 · ATM IV and IV − RV(5d) · net GEX sign · wall corridor · HHI (percentile vs 30-day same-DTE history is a **parity gap** — NULL until built) · PCR.

### 3.2 Pilot — Day 1–2, **40 % of R**
First test-and-hold of a tradeable zone: support → bull put spread; resistance → bear call spread.

**Short strike** = the furthest of (a) spot ± 1 % (operator floor), (b) the zone's far edge ± 0.25 σ_daily so the level sits between spot and the strike, (c) spot ± 0.8 × EM.

**Wing** at the first ENH-120 wall within 0.5–1.5 σ_daily beyond the short strike, else short ± 0.75 σ_daily. Timing per §1.3.

### 3.3 Build — Days 1–3, **+30 % / +30 % of R** — REWRITTEN
An add requires **thesis confirmation**, at least 2 of 3:
1. the level has held on every 1H close since the pilot;
2. realised move since cycle open < 50 % of EM;
3. the straddle has decayed faster than linear time decay.

**An add is a new layer, not more of the same strike.** In priority order:
1. **Opposite side** (§4), if any trigger fires — it adds credit without touching the floor;
2. **A further strike on the same side**, one zone beyond the pilot's short, as a second spread;
3. **More of the pilot's strike** — only if the level has held a full session *and* premium is richer than at pilot entry.

Never an add on price movement alone. Never an add to improve an average.

### 3.4 Banned — from the Jun 3 loss
**No averaging into a losing leg.** If the structure is under water because the level is being tested, the permitted actions are: hold, flip (§4 T4), or close. Adding lots at a better price to lower the average is prohibited, in every arm.

---

## 4. Selling the opposite side

Fire on **any one** trigger with **no** blocker present.

| ID | Trigger |
|---|---|
| **T1 — opposite-level rejection** | Spot rallies (falls) into a tradeable resistance (support) zone and a 1H bar closes back out |
| **T2 — range lock** | By Day-2 close: realised < 40 % of EM, both nearest zones outside ±0.8 EM have held, net GEX > 0, spot inside the wall corridor |
| **T3 — spent side** | First side has captured ≥ 50 % of credit and its short delta ≤ 0.10 → recycle at ≥ 1 % from spot behind a level |
| **T4 — flip** | First side **breaks** → close the tested short, keep its wing as the runner, sell the opposite side ≥ 1 % beyond spot behind the broken (now flipped) level |
| **T5 — positioning divergence** *(new, Aug 27)* | Price falls **while** net GEX rises and HHI falls sharply, with PCR < 0.7 → sell puts. *His stated cue: "HHI moved from 0.85 to 0.13… Net Gamma didn't flip negative. It actually kept rising as the market fell. PCR sitting at 0.57. That's my cue for mean reversion."* Pure G1 — it does not exist in G0. |

| Blocker | Why |
|---|---|
| Net GEX < 0 **and** spot outside the wall corridor | Amplifying regime |
| ATM straddle up d/d **and** IV − RV widening | Vol expansion |
| Scheduled event before expiry | Binary gap |
| Nearest opposite zone within 0.5 EM of spot | No room |
| Day ≥ 4 of cycle | Not enough time against expiry gamma |
| §1.4 vega constraint would be breached | Vega |

**Sizing:** quantity ≤ the first side's, net position delta within ±0.15 per lot-equivalent.

**Side asymmetry (Jul 31):** positive gamma above spot absorbs rallies into a grind; negative gamma below spot accelerates declines. Put-selling and call-selling are therefore **not** mirror images — every result is reported per side, never pooled.

---

## 5. Exits

| # | Rule |
|---|---|
| 5.1 | **Harvest — swept, not fixed.** Close everything at captured ≥ **H** of total credit. **H ∈ {50, 60, 70, 80} %**, set by M1. v3's 75 % was an assumption; the practitioner books ~50 %. |
| 5.2 | **Extraction exhausted** *(new, Sep 1)*. Close when HHI ≤ 0.25 and remaining credit ≤ 20 % of collected, whatever H says — *"barely anything left to extract"*. G1 only. |
| 5.3 | **Tested-side defence:** §2 break → T4 flip. Max 2 flips per cycle. |
| 5.4 | **IV-expansion exit:** straddle > 1.25× its cycle low **and** spot within 0.5 σ_daily of a short strike → close that side regardless of P&L. |
| 5.5 | **Time stop:** end of Day 3 with captured < 30 % **and** any short within 0.5 σ_daily → close all. |
| 5.6 | **Re-entry** *(new, Jul 7)*. After a stop or flip, the original thesis may be re-entered **once** if the level is reclaimed on a 1H close. Counts against the same R; no fresh budget. |
| 5.7 | **Expiry-day hard close: flat by 14:00 IST.** Never into CAS (ADR-022). His Aug 25 record: 24250 CE 2.5 → 86.3 (34.5×), 24300 CE 1.2 → 40 (33.3×) in the CAS window. |

---

## 6. Book rules
- NIFTY and SENSEX same-direction setups count as **one bet**: combined open R ≤ **3 %**.
- One setup per symbol per cycle, max 2 symbols.
- Short and wing both in the top-20 OI strikes of that expiry.
- **Slippage reality:** his volume-footprint post (Jul 9) shows stops filling through liquidity voids, and ₹3L lost exiting 950 lots. Not binding at ₹20L, but the reason §8 tests slippage out to 2 points.

---

## 7. MERDIAN inputs

| Input | Role |
|---|---|
| Spot bars 5m → 1H/D/W | Levels, events, realised move |
| `volatility_snapshots.atm_iv_avg` (18 mo) | EM, σ_daily, IV − RV |
| `gamma_metrics.straddle_atm` | EM; vol-expansion blocker and 5.4 |
| ENH-120 walls + `corridor_state` | Wing placement; T2; blocker |
| `gamma_metrics` net GEX | T2, T5, blocker — **G1 only** |
| ENH-122 HHI | T5, 5.2 — **G1 only**; percentile series is a parity gap |
| Option chain PCR | T5 |
| Greeks (vega) | §1.4 constraint |
| `hist_option_bars_1m` / HOCS / GSS / OCS | All leg pricing |
| ICT zones | Tag only |
| `flip_level` | **Excluded** (TD-S79-NEW-15…21) |

**Governance.** GEX and HHI now appear in T2, T5, 5.2 and a blocker — that is a gate, and ADR-024 authorises none. Two arms therefore run throughout:
- **G0** — all GEX/HHI conditions removed (T5 and 5.2 do not exist).
- **G1** — applied.

G1 is adoptable only if it beats G0 on train **and** holdout.

---

## 8. Arms and acceptance (unit = cycle)

**Arms:** {W-ENTRY, W-DEFER} × {G0, G1} × H ∈ {50,60,70,80} — plus **Arm OH (over-hedged)** run separately: surplus wings carried so `floor ≥ 0`, tested only on W-DEFER × G1 × best H, to price what his weekend-hedge posture costs and returns.

| Metric | Pass |
|---|---|
| Cycles per cell, train / holdout | ≥ 30 each — **cells must stay coarse** (~45 NIFTY cycles in train) |
| Expectancy per cycle in R, after costs, 1-pt slippage | > 0 on train **and** holdout |
| Realised worst cycle | ≤ 1.05 R; any breach is an audit item |
| Max drawdown, ₹20L path | ≤ 10 % |
| W-DEFER vs W-ENTRY | W-DEFER adopted only if wing saving exceeds the gap cost **and** worst cycle stays ≤ 1.05 R |
| Opposite side | T1–T3, T5 cycles vs the same cycles single-sided: mean P&L improves, drawdown does not worsen |
| G1 vs G0 | G1 wins on both periods |
| Arm OH | Reported, not gated — it is a different objective, not a better version of the same one |

**Every table is additionally split by vol regime** (ATM IV tercile at cycle open). *"That phase was brutal - low vol, no follow through. Now it's a completely different regime, almost 2x volatility"* (Mar 19) — pooling across regimes hides the thing that decides the outcome.

Train 2025-04 → 2026-02 (1m bars); holdout 2026-03 and post-April (~5m chain sources) as **separate cohorts**.

---

## 9. Not authorised
No production code, order placement, or gate. A pass moves to **Validate** (live-runtime cohort, N ≥ 30, ADR-019), then **Shadow**.
