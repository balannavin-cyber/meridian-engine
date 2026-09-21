# M9 -- does the pin hold?

Generated 2026-09-21. Read-only, era 1 (2025-04-01 .. 2026-03-30), 102 candidate cycles.

## What would falsify a positive result

A pin claim is **not** "settlement lands near the max-gamma strike" -- settlement lands near spot, and spot is near the max-gamma strike, so that statement is nearly self-satisfying. The claim is that the max-gamma strike forecasts settlement **better than current spot does**, at the same stamp. A beat-share near 50% is no pin effect, whatever a chart looks like.

## Which max-gamma strike, and why not the stored one

Absolute gamma concentration -- `argmax_K sum(|gamma| * OI)` over CE and PE -- **not** MERDIAN's `gamma_metrics.max_gamma_strike`. ADR-024 Amendment A (S79) establishes that the stored column is the max NET-long-gamma strike and that its offset from spot is *arithmetic from OI imbalance, not positioning*: under put-call parity call and put gamma are equal at a strike, so the sign of `gex_cr` is set by which side is OTM, which flips at spot. Testing the pin against that quantity would test a tautology.

Settlement is a **proxy**: the spot close at the 15:25 anchor on expiry day. Official weekly settlement is a 30-minute VWAP the database does not carry. Era 1 is entirely pre-CAS (ADR-022 effective 2026-08-03), so 15:25 is inside normal continuous trading throughout.

## M9.A  Distance to settlement, in sigma_daily

| symbol | stamp | N | median gamma | P75 gamma | median spot | P75 spot | gamma beats spot | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| NIFTY | Day1_1030 | 51 | 1.41 | 2.22 | 1.16 | 2.42 | 47% | spot better or equal |
| NIFTY | Day3_close | 48 | 0.86 | 1.23 | 0.86 | 1.22 | 48% | spot better or equal |
| NIFTY | DTE1_close | 48 | 0.72 | 1.09 | 0.67 | 1.07 | 48% | spot better or equal |
| SENSEX | Day1_1030 | 51 | 1.38 | 2.40 | 1.18 | 2.42 | 53% | gamma better |
| SENSEX | Day3_close | 47 | 0.93 | 1.43 | 0.85 | 1.41 | 43% | spot better or equal |
| SENSEX | DTE1_close | 50 | 0.60 | 1.03 | 0.68 | 1.03 | 46% | spot better or equal |

`N*` marks a cell below the brief's stop condition of 30 cycles; those report INSUFFICIENT and carry no verdict.

## M9.B  Does the advantage grow as DTE falls?

The reference claim is that the pull strengthens into expiry. That predicts the beat-share rising from Day-1 through Day-3 to 1 DTE.

| symbol | Day1_1030 | Day3_close | DTE1_close | rising? |
|---|---:|---:|---:|---|
| NIFTY | 47% | 48% | 48% | yes |
| SENSEX | 53% | 43% | 46% | NO |

## Coverage -- stamps that could not be computed

| reason | count |
|---|---:|
| Day3_close: no greeks rows in anchor window | 6 |
| DTE1_close: no greeks rows in anchor window | 4 |

The greeks sidecar covers 193 of 247 NIFTY and 192 of 246 SENSEX era-1 trading days, so missing stamps are expected. They are counted here rather than dropped.

