# Target · Delta · positioning — NIFTY, since open, front expiry (13 Oct), read 12:46 IST via page text
Headline: Bullish · Initiated +1,77,533 Cr · 99 % · biggest move put short buildup +88,546 Cr
Readings: State +38,168 (calls outweigh puts) · Flow −77,988 (puts outweigh calls) · Initiated +1,77,533 (long Δ, bullish)
Split: bearish 2,237 Cr (1 %) | bullish 1,79,770 Cr (99 %) · 100 % of ΔOI could be read · 32,89,51,415 shares

| strike | call class | call ΔOI | call init Δ Cr | put class | put ΔOI | put init Δ Cr | net Cr |
|---|---|---|---|---|---|---|---|
| 23,050 | short buildup | +9,77,210 | −11 | long unwind | −29,835 | · | −11 |
| 23,000 | short buildup | +66,45,795 | −103 | long unwind | −1,86,290 | · | −103 |
| 22,950 | short buildup | +14,47,745 | −25 | long unwind | −46,735 | +104 | +79 |
| 22,900 | short buildup | +16,22,595 | −36 | long unwind | −1,53,270 | +345 | +308 |
| 22,850 | short buildup | +15,75,145 | −49 | long unwind | −15,535 | · | −49 |
| 22,800 | short buildup | +11,27,490 | −56 | long unwind | −1,76,410 | +387 | +331 |
| 22,750 | short buildup | +52,11,570 | −439 | short buildup | +1,12,320 | +240 | −199 |
| 22,700 | short buildup | +82,09,110 | −1,428 | short buildup | +17,15,805 | +3,509 | +2,082 |
| 22,650 | **long buildup** | +1,11,28,520 | +4,002 | short buildup | +19,83,670 | +3,744 | +7,746 |
| 22,600 | **long buildup** | +2,17,54,005 | +15,209 | short buildup | +85,61,605 | +13,466 | +28,675 |
| 22,550 | **long buildup** | +1,79,67,170 | +20,519 | short buildup | +2,09,54,895 | +23,298 | +43,817 |
| 22,500 | **long buildup** | +56,35,045 | +8,871 | short buildup | +3,94,11,125 | +26,787 | +35,657 |
| 22,450 | short cover | −24,13,645 | +4,531 | short buildup | +2,32,69,155 | +8,953 | +13,483 |
| 22,400 | short cover | −69,86,655 | +14,153 | short buildup | +2,42,20,105 | +5,259 | +19,411 |
| 22,350 | short cover | −58,43,825 | +12,482 | short buildup | +94,86,165 | +1,212 | +13,694 |
| 22,300 | short cover | −32,72,100 | +7,092 | short buildup | +1,12,58,975 | +924 | +8,016 |
| 22,250 | short cover | −5,35,730 | +1,165 | short buildup | +54,25,875 | +303 | +1,468 |
| 22,200 | short cover | −5,71,545 | +1,258 | short buildup | +61,69,020 | +249 | +1,507 |
| 22,150 | short cover | −24,115 | +53 | short buildup | +32,18,670 | +101 | +154 |
| 22,100 | short cover | −1,12,255 | +248 | short buildup | +45,60,010 | +119 | +367 |
| 22,050 | long buildup | +2,080 | · | short buildup | +18,66,150 | +36 | +36 |
| **all** | | 12,38,52,040 abs | **+87,727** | | 20,50,99,375 abs | **+89,806** | **+1,77,533** |

## What the table shows (for the D-4 comparison)
- **Every call strike from 22,500 to 22,650 is classed "long buildup"** (OI up and premium up → buyers opened). These four strikes
  carry +48,601 Cr of the +87,727 call total. The 0DTE ATM calls are classed as *bought*, so the strikes that look like
  call writing by OI alone are read as bullish because the premium rose with spot.
- ITM calls 22,100–22,450 are "short cover" (OI down, premium up), also bullish: another +40,982 Cr.
- OTM calls ≥ 22,700 are "short buildup" (bearish) but tiny in Δ (−2,147 Cr total): far-OTM 0DTE deltas are near zero.
- **Every put strike ≤ 22,750 is "short buildup"** (puts written): +89,806 Cr bullish.
- So the 99 % bullish verdict is built from **three legs that all depend on the premium-change sign on 0DTE**: put writing, ATM
  call buying, ITM call short-cover. On an up-drifting expiry day, premium-up on calls near spot is mechanical (Δ × move), so
  "long buildup" on ATM calls may be partly a price effect, not who opened. This is the TD-S95-NEW-1 untraded-leg / premium-sign
  objection made concrete: **the classifier's input (premium change) is correlated with the direction it outputs.**
- Flow (ΔOI × Δ, no side) is **−77,988** — puts outweigh calls. Unsigned, the ΔOI says put Δ was added. Signing it by class turns
  it into bullish. The verdict depends on that sign convention (put writers = bullish).
- Test this suggests for MERIDIAN (candidate, not proposed): recompute their class at each strike with the premium change net of
  Δ × spot move (i.e. the residual), and see how much of the 99 % survives.

## 12:56 re-read (page text)
Initiated **+1,82,923** (99 %; split ▼2,144 / ▲1,85,067) · State +37,269 · Flow −80,253 · read 100 % · 33,43,25,940 shares.
Classes at 22,500–22,650 are unchanged (calls long buildup, puts short buildup); call total +90,269, put total +92,654.

### Their method statement (footnote, verbatim in substance)
- STATE and FLOW: OI × Δ (Flow: ΔOI × Δ since 09:15), every contract counted as bought (calls +, puts −). They have no side
  behind the sign: they name the heavier leg, not a direction.
- INITIATED: ΔOI × Δ signed by the class read from **ΔOI and the premium move**. Long buildup and short cover take the leg's Δ
  sign; short buildup and long unwind take the opposite. Only Initiated names a direction.
- READ = share of |ΔOI| the engine could classify. Units: Cr of Δ-notional (Δ × OI shares × spot). "A read from ΔOI and price,
  not from trades."

### Their own trade-side pane disagrees with the verdict
**Delta · aggressor** (same screen, 12:56): **Δ balance −3 % "sold Δ" since first tick**; calls +3 % buy−sell; **puts +7 %
buy−sell**; resting book +73 % / +66 % (call / put) at 12:56; 100 % of volume classified. Method: per strike per minute, the
volume goes to the side of the last trade vs the bid/ask midpoint; Δ-weighted; "coarse".
→ **Aggressors net *bought* puts (+7 %) and net *sold* Δ (−3 %)**, while the OI + premium classifier calls every put strike
"short buildup" and the day 99 % bullish. Their own trade tape and their positioning verdict point opposite ways, on one screen,
with no reconciliation shown. This is the clearest evidence so far for the S96-I decline: classification from ΔOI + premium sign
is not the same as who traded.
