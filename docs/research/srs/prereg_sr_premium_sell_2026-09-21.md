# Pre-registration v3 — Weekly-Cycle Premium Engine (DRAFT)

| Field | Value |
|---|---|
| **Status** | DRAFT v3 — supersedes v1/v2 (same day). ENH ID to be assigned by operator. |
| **Stage** | **Measure** only. §9 (Claude Code exploration brief) runs **before** any parameter here is frozen. |
| **Capital** | ₹20,00,000 (simulated) · **R = 2 % = ₹40,000 per setup, hard** |
| **Unit of trade** | One **weekly expiry cycle** per symbol = one setup |

**Changes from v2:**
- ICT zones are replaced by **plain daily/weekly support and resistance**. ICT becomes an optional tag only.
- The unit of trade is now the **weekly cycle**, and the position is **built through the week**.
- The **opposite-side decision** is the core rule set (§4).
- Exit on **70–80 % premium captured by day 3–4**.
- Stops are on a **1H close** (positional), not 5m.

---

## 0. Reference practitioner — what could be extracted

Source: @AshwinBadri2 (Ashwin Badrinath). He is building **Hedgewall**, the parity target in `MERDIAN_Hedgewall_Parity_Spec.md`. X blocks automated reading, so only search-indexed post snippets were available, not the full 2025-09 → 2026-09 timeline. What those snippets show:

| Observed | Translation into this design |
|---|---|
| Starts small, lets the market reveal itself, and **sizes up as the thesis strengthens or is challenged**. No need to be right on the first entry. | §3 cycle builder: pilot, then confirm-driven adds. **Not** adds on price movement alone (Exp 2c prior). |
| Core thesis on his big weeks: the market does not need to move. Stated context: **net GEX strongly positive, HHI balanced vs its own 30-day history at that DTE**. | §4 T2 range-lock trigger for selling the second side; GEX + HHI percentile as the regime tag. |
| Has run long futures averaged down against heavy short calls, and exited early when call premiums spiked — well before his planned stop. | Premium behaviour is an exit input (§5.3 IV-expansion exit). Futures legs are **excluded**: they break the §1 invariant. |
| Treats monthly expiry under **CAS** as a casino: deep-OTM calls ran 30×+ into settlement. | Hard rule: **never hold into the expiry-day CAS window** (ADR-022). |
| Scale: ~₹25Cr deployed, monthly ROI ~6.5 %. | ~12× leverage of the ₹20L here. His sizing is **not** transferable; his structure logic is. |

**Gap to close:** the operator reads the full timeline, or pastes 5–10 specific threads covering entry → adjust → exit on one week. That would let §3–§5 be checked against an actual position log rather than snippets.

---

## 1. Risk backbone — carried from v2, unchanged

```
cash        = Σ premium received − Σ premium paid − costs    (since setup open)
floor       = min over terminal spot S of Σ payoff(open legs, S)
worst_case  = cash + floor
INVARIANT   worst_case ≥ −R      checked before EVERY action; lots = max satisfying it
```

- Every short leg is covered by a same-type, same-expiry long wing of equal quantity. That makes 2 % hard through gaps and events.
- **Key property for §4:** an iron condor can only lose on one side at expiry, so floor = −max(W_put, W_call) × qty.
- Adding the opposite side **adds credit without lowering the floor**, so it **improves** worst_case.
- The opposite-side decision is therefore **purely an edge question, never a risk-budget question**. The only cost is path risk if the position has to be closed early.

---

## 2. Levels — plain support / resistance, mechanical

Computed each evening from spot bars (5m resampled to D and W; IST-labelled +00:00, so use `replace(tzinfo=None)`).

| Level source | Rule | Weight |
|---|---|---|
| Weekly swing pivot | Fractal high/low, 2 bars each side, last 52 weeks | 3 |
| Prior week high / low | | 2 |
| Daily swing pivot | Fractal, 2 bars each side, last 60 sessions | 1 |
| Prior day high / low | | 1 |
| Round number | NIFTY multiples of 500, SENSEX multiples of 1,000 | 1 |
| Touches | Each prior daily bar whose wick entered the zone and closed back out | +1 each, cap 3 |

- **Clustering:** merge levels within **0.2 σ_daily** into one zone `[low, high]`. Strength = sum of weights. A zone is tradeable at **strength ≥ 4** (tunable in §9).
- **Polarity:** a zone broken on a daily close flips role (support ↔ resistance). This is standard S/R practice, not ICT.
- **Tags only:** ICT zones, ENH-120 walls. A level that coincides with a wall is recorded as `wall_confluence = true` and **measured**, not required.

**Events on levels (1H bars):**
- **Test-and-hold:** a 1H bar trades into the zone and closes back out on the original side.
- **Break:** a 1H close beyond the zone by more than **0.25 σ_daily**.

---

## 3. The cycle builder — how a week is traded

NIFTY cycle = Wednesday after expiry → the next Tuesday expiry. SENSEX = Friday → Thursday. Day numbers count trading days from cycle open.

### 3.1 Cycle-open map (expiry-day evening)
Record:
- the S/R zones (§2);
- **EM** = expected move = ATM straddle of the new weekly at the Day-1 close (or 10:30);
- ATM IV, and IV − RV (5-day realised);
- net GEX sign, wall corridor, HHI percentile vs the 30-day same-DTE history. **Parity gap:** that series is not built yet (ENH-122 note) — tag NULL until it exists.

### 3.2 Pilot — Day 1 or 2, **40 % of R**
Take the **first test-and-hold** of a tradeable zone:
- support hold → **bull put spread**;
- resistance hold → **bear call spread**.

**Short strike** = the furthest of:
- (a) spot ± 1 % (operator's floor);
- (b) the zone's far edge ± 0.25 σ_daily, so the level sits *between* spot and the strike;
- (c) spot ± 0.8 × EM.

The level is the protection; 1 % is only the minimum. **Wing** at the first ENH-120 wall within 0.5–1.5 σ_daily beyond the short strike, else short ± 0.75 σ_daily. Size by the invariant.

### 3.3 Build — Days 1–3, **+30 % / +30 % of R**
An add is allowed only when **thesis confirmation** holds — at least 2 of 3:
1. the level has held on every 1H close since the pilot;
2. realised move since cycle open < 50 % of EM (the week is quieter than priced);
3. the straddle has decayed faster than linear time decay (IV not expanding).

Adds go on the **same short strike** (more of a working structure), or one strike nearer only if the level has held for a full session. Price movement alone is **never** an add trigger.

---

## 4. Selling the opposite side — the core decision

Sell the opposite-side spread when **any one** trigger fires and **no** blocker is present.

| ID | Trigger | Logic |
|---|---|---|
| **T1 — opposite-level rejection** | Spot rallies (falls) into a tradeable resistance (support) zone and a 1H bar closes back out | The range has now been demonstrated from both ends; sell the side the market just rejected |
| **T2 — range lock** (Ashwin's thesis) | By Day 2 close: realised move < 40 % of EM, **and** both nearest zones outside ±0.8 EM have held, **and** net GEX > 0 with spot inside the wall corridor | Market pinned between two levels in a dampening regime; premium on both sides is mispriced high |
| **T3 — spent side** | First side has captured ≥ 50 % of its credit and its short delta ≤ 0.10 | That side's remaining premium is not worth its gamma; recycle the thesis on the other side at ≥ 1 % from spot, if a level backs it |
| **T4 — flip** (from v2) | First side **breaks** (§2 break) | Close the tested short, keep its long wing as the runner, sell the opposite side ≥ 1 % beyond spot behind the broken level (now flipped in role). Runner rules as v2 §2.3 |

| Blocker | Why |
|---|---|
| Net GEX < 0 **and** spot outside the wall corridor | Amplifying regime — ranges fail |
| ATM straddle up day-over-day **and** IV − RV widening | Vol expansion — the market is re-pricing risk upward |
| Scheduled event before expiry (RBI, Budget, results, Fed) | Binary gap; range logic invalid |
| Nearest opposite zone within 0.5 EM of spot | No room — the short would sit inside the expected move |
| Day ≥ 4 of the cycle | Not enough time to earn the credit against expiry gamma |

**Opposite-side sizing:**
- Quantity equals the first side's, or less, so that net position delta stays within ±0.15 per lot-equivalent.
- The invariant still governs, and per §1 it can only be satisfied **more** easily.

---

## 5. Exits

| # | Rule |
|---|---|
| 5.1 | **Harvest:** total captured ≥ **75 %** of total credit collected → **close everything**. Operator band 70–80 %; §9 M1 sets the value. |
| 5.2 | **Tested-side defence:** §2 break → T4 flip. At most 2 flips per cycle. |
| 5.3 | **IV-expansion exit:** straddle > 1.25× its cycle low **and** spot within 0.5 σ_daily of a short strike → close that side, whatever its P&L (lesson from the practitioner, §0). |
| 5.4 | **Time stop:** end of Day 3 with captured < 30 % **and** any short strike within 0.5 σ_daily → close all. The week has not paid; don't carry gamma into expiry for it. |
| 5.5 | **Expiry-day hard close:** everything flat by **14:00 IST** on expiry day. Never into CAS (ADR-022), never into settlement STT. |

---

## 6. Book-level rules
- NIFTY and SENSEX are highly correlated, so **same-direction setups on both indices count as one bet**. Combined open R across them ≤ **3 %**, not 4 %.
- Maximum one setup per symbol per cycle, and at most 2 symbols.
- Strike liquidity: short and wing must both be in the top-20 OI strikes of that expiry.

---

## 7. What MERDIAN contributes, and in what role

| Input | Role |
|---|---|
| Spot bars (5m → 1H / D / W) | Levels, events, realised move |
| `volatility_snapshots.atm_iv_avg` (18 months) | EM, σ, IV − RV |
| ATM straddle (`gamma_metrics.straddle_atm`) | EM; vol-expansion blocker and exit |
| ENH-120 walls + `corridor_state` | Wing placement; T2 condition; blocker |
| `gamma_metrics` net GEX sign | T2 condition; blocker — **measured first in §9**, gate only if it passes |
| ENH-122 HHI | Tag now; percentile series is a parity gap |
| `hist_option_bars_1m` / HOCS / GSS / OCS | All leg pricing |
| ICT zones | **Tag only** |
| `flip_level` | **Excluded** (TD-S79-NEW-15…21) |

**Governance:** GEX appears in T2 and in a blocker. That is a gate, and ADR-024 does not authorise one yet. So the backtest runs **two arms**:
- **G0:** GEX conditions removed from T2 and the blocker.
- **G1:** GEX conditions applied.

G1 is only adoptable if it beats G0 on train **and** holdout. This keeps "GEX-as-context-not-gate" honest until measured.

---

## 8. Acceptance (unit = cycle)

| Metric | Pass |
|---|---|
| Cycles per cell, train / holdout | ≥ 30 each (≈ 45 NIFTY weekly cycles in train — **cells must stay coarse**) |
| Expectancy per cycle in R, after costs, 1-pt slippage per leg | > 0 on train **and** holdout |
| Realised worst cycle | ≤ 1.05 R; any breach is an audit item |
| Max drawdown, ₹20L path | ≤ 10 % |
| Opposite side (§4) | Cycles with T1–T3 fired vs the same cycles single-sided (counterfactual): mean P&L improves, drawdown does not worsen |
| G1 vs G0 | G1 adopted only if it wins on both periods |

Train 2025-04 → 2026-02 (1m bars); holdout 2026-03 and post-April (≈5m chain sources) as separate cohorts.

---

## 9. Exploration first — see `claude_code_brief_srs_exploration.md`

Every threshold above is a hypothesis. The brief measures the five that matter most before this pre-reg is frozen:
- the decay curve (when is 75 % actually reached);
- S/R hold rates in σ;
- EM vs realised by regime;
- opposite-side trigger outcomes;
- put/call skew.
