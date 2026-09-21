# M1 era 2 -- decay on mid and on last, and the divergence between them

Generated 2026-09-21. Read-only.

## Cohort, and the two N's

Measured cycles: **22**. Excluded: **10**. Paired (mid, last) stamp-legs: **321**.

These are different units and must not be conflated:

- the **decay curve** is per CYCLE, so era 2 is THIN and marked so;
- the **divergence** is per STAMP -- two prices at the same instant -- so its N is 321, which is not thin. This is the quantity the era-1 error bar needs.

## Two windows, and the hole between them

| window | source | span | note |
|---|---|---|---|
| W1 | `historical_option_chain_snapshots` | 2026-03-16 .. 2026-06-03 | |
| -- | *none* | 2026-06-04 .. 2026-08-23 | **no premium exists.** `gex_strike_snapshots` is the only per-strike source and carries NO price column (ADR-015, 14 cols). |
| W2 | `option_chain_snapshots` | 2026-08-24 .. 2026-09-11 | post-CAS (ADR-022): F&O continuous trade ends 15:15, index derivatives run to 15:40, so a 15:25 option stamp is real but the UNDERLYING is mid-auction. |

### Divergence by window -- checked BEFORE pooling

Percentage points of the decay ratio, `decay(last) - decay(mid)`. Positive means the last-trade price makes decay look LARGER than the two-sided quote does.

| window | symbol | state | N | P05 | P25 | median | P75 | P95 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| W1 | NIFTY | pooled | 129 | -0.3 | -0.1 | +0.0 | +0.1 | +0.4 |
| W1 | NIFTY | tested | 111 | -0.3 | -0.1 | +0.0 | +0.1 | +0.4 |
| W1 | NIFTY | untested | 18* | -0.2 | -0.1 | -0.0 | +0.0 | +0.2 |
| W1 | SENSEX | pooled | 120 | -0.4 | -0.0 | +0.0 | +0.1 | +0.6 |
| W1 | SENSEX | tested | 105 | -0.5 | -0.1 | +0.0 | +0.1 | +0.6 |
| W1 | SENSEX | untested | 15* | -0.1 | -0.0 | +0.0 | +0.0 | +0.1 |
| W2 | NIFTY | pooled | 36 | -0.3 | -0.1 | +0.0 | +0.1 | +0.2 |
| W2 | NIFTY | tested | 30 | -0.3 | -0.1 | -0.0 | +0.1 | +0.3 |
| W2 | NIFTY | untested | 6* | -0.3 | -0.1 | +0.0 | +0.1 | +0.1 |
| W2 | SENSEX | pooled | 36 | -0.1 | -0.0 | +0.1 | +0.2 | +1.0 |
| W2 | SENSEX | tested | 30 | -6.3 | -0.0 | +0.1 | +0.2 | +1.7 |
| W2 | SENSEX | untested | 6* | -0.0 | -0.0 | +0.0 | +0.2 | +0.9 |

## E2.A  Divergence by Day-N and state -- the era-1 error bar

The spread widens as an option decays, so this is reported per stamp.

| symbol | leg | state | stamp | N | P05 | P25 | median | P75 | P95 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| NIFTY | OTM_CE | pooled | D1 | 11* | -0.3 | -0.2 | +0.0 | +0.2 | +0.2 |
| NIFTY | OTM_CE | pooled | D2 | 10* | -0.3 | -0.1 | -0.1 | +0.1 | +0.4 |
| NIFTY | OTM_CE | pooled | D3 | 10* | -0.3 | -0.1 | -0.0 | +0.1 | +0.1 |
| NIFTY | OTM_CE | pooled | D4 | 9* | -0.1 | -0.1 | -0.0 | -0.0 | +0.0 |
| NIFTY | OTM_CE | pooled | D5 | 4* | -0.1 | -0.1 | +0.0 | +0.0 | +0.0 |
| NIFTY | OTM_CE | pooled | EXP1300 | 11* | -1.6 | -0.1 | -0.0 | +0.0 | +0.1 |
| NIFTY | OTM_CE | untested | D1 | 4* | -0.2 | -0.1 | +0.0 | +0.0 | +0.2 |
| NIFTY | OTM_CE | untested | D2 | 4* | -0.3 | -0.2 | -0.1 | -0.1 | +0.2 |
| NIFTY | OTM_CE | untested | D3 | 3* | -0.0 | -0.0 | +0.0 | +0.1 | +0.1 |
| NIFTY | OTM_CE | untested | D4 | 3* | -0.0 | -0.0 | +0.0 | +0.0 | +0.0 |
| NIFTY | OTM_CE | untested | D5 | 1* | -0.1 | -0.1 | -0.1 | -0.1 | -0.1 |
| NIFTY | OTM_CE | untested | EXP1300 | 4* | -0.0 | -0.0 | +0.0 | +0.0 | +0.1 |
| NIFTY | OTM_CE | tested | D1 | 7* | -0.3 | -0.1 | +0.0 | +0.1 | +0.2 |
| NIFTY | OTM_CE | tested | D2 | 6* | -0.1 | -0.1 | -0.0 | +0.1 | +0.4 |
| NIFTY | OTM_CE | tested | D3 | 7* | -0.3 | -0.1 | -0.1 | +0.1 | +0.1 |
| NIFTY | OTM_CE | tested | D4 | 6* | -0.1 | -0.1 | -0.1 | -0.0 | -0.0 |
| NIFTY | OTM_CE | tested | D5 | 3* | -0.1 | -0.1 | +0.0 | +0.0 | +0.0 |
| NIFTY | OTM_CE | tested | EXP1300 | 7* | -1.6 | -0.1 | -0.0 | -0.0 | +0.1 |
| NIFTY | OTM_PE | pooled | D1 | 11* | -0.3 | -0.1 | +0.1 | +0.1 | +0.2 |
| NIFTY | OTM_PE | pooled | D2 | 10* | -0.1 | -0.0 | +0.1 | +0.1 | +0.3 |
| NIFTY | OTM_PE | pooled | D3 | 10* | -0.8 | -0.0 | +0.0 | +0.1 | +0.2 |
| NIFTY | OTM_PE | pooled | D4 | 9* | -0.7 | -0.0 | -0.0 | +0.1 | +0.5 |
| NIFTY | OTM_PE | pooled | D5 | 4* | -0.1 | +0.0 | +0.1 | +0.1 | +2.1 |
| NIFTY | OTM_PE | pooled | EXP1300 | 11* | -2.2 | -0.0 | +0.0 | +0.2 | +4.0 |
| NIFTY | OTM_PE | untested | D1 | 1* | -0.1 | -0.1 | -0.1 | -0.1 | -0.1 |
| NIFTY | OTM_PE | untested | D2 | 1* | -0.1 | -0.1 | -0.1 | -0.1 | -0.1 |
| NIFTY | OTM_PE | untested | D3 | 1* | -0.0 | -0.0 | -0.0 | -0.0 | -0.0 |
| NIFTY | OTM_PE | untested | D4 | 1* | -0.0 | -0.0 | -0.0 | -0.0 | -0.0 |
| NIFTY | OTM_PE | untested | EXP1300 | 1* | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| NIFTY | OTM_PE | tested | D1 | 10* | -0.3 | -0.1 | +0.1 | +0.1 | +0.2 |
| NIFTY | OTM_PE | tested | D2 | 9* | -0.0 | +0.1 | +0.1 | +0.1 | +0.3 |
| NIFTY | OTM_PE | tested | D3 | 9* | -0.8 | -0.0 | +0.0 | +0.1 | +0.2 |
| NIFTY | OTM_PE | tested | D4 | 8* | -0.7 | -0.0 | +0.0 | +0.1 | +0.5 |
| NIFTY | OTM_PE | tested | D5 | 4* | -0.1 | +0.0 | +0.1 | +0.1 | +2.1 |
| NIFTY | OTM_PE | tested | EXP1300 | 10* | -2.2 | -0.0 | -0.0 | +0.2 | +4.0 |
| NIFTY | STRADDLE | pooled | D1 | 11* | -0.1 | -0.0 | -0.0 | +0.0 | +0.2 |
| NIFTY | STRADDLE | pooled | D2 | 10* | -0.1 | +0.0 | +0.0 | +0.1 | +0.2 |
| NIFTY | STRADDLE | pooled | D3 | 10* | -0.3 | -0.1 | -0.0 | +0.1 | +0.4 |
| NIFTY | STRADDLE | pooled | D4 | 9* | -0.1 | -0.0 | +0.1 | +0.1 | +0.5 |
| NIFTY | STRADDLE | pooled | D5 | 4* | -0.3 | -0.1 | -0.1 | -0.1 | +0.0 |
| NIFTY | STRADDLE | pooled | EXP1300 | 11* | -0.3 | -0.0 | +0.1 | +0.2 | +0.5 |
| NIFTY | STRADDLE | tested | D1 | 11* | -0.1 | -0.0 | -0.0 | +0.0 | +0.2 |
| NIFTY | STRADDLE | tested | D2 | 10* | -0.1 | +0.0 | +0.0 | +0.1 | +0.2 |
| NIFTY | STRADDLE | tested | D3 | 10* | -0.3 | -0.1 | -0.0 | +0.1 | +0.4 |
| NIFTY | STRADDLE | tested | D4 | 9* | -0.1 | -0.0 | +0.1 | +0.1 | +0.5 |
| NIFTY | STRADDLE | tested | D5 | 4* | -0.3 | -0.1 | -0.1 | -0.1 | +0.0 |
| NIFTY | STRADDLE | tested | EXP1300 | 11* | -0.3 | -0.0 | +0.1 | +0.2 | +0.5 |
| SENSEX | OTM_CE | pooled | D1 | 10* | -0.5 | -0.1 | +0.1 | +0.5 | +0.9 |
| SENSEX | OTM_CE | pooled | D2 | 11* | -0.3 | -0.1 | -0.0 | +0.1 | +0.7 |
| SENSEX | OTM_CE | pooled | D3 | 10* | -0.2 | -0.1 | -0.0 | +0.0 | +0.1 |
| SENSEX | OTM_CE | pooled | D4 | 7* | -0.0 | -0.0 | -0.0 | +0.0 | +0.2 |
| SENSEX | OTM_CE | pooled | D5 | 5* | -0.0 | -0.0 | +0.0 | +0.0 | +0.0 |
| SENSEX | OTM_CE | pooled | EXP1300 | 9* | -16.1 | -0.0 | +0.0 | +0.0 | +0.0 |
| SENSEX | OTM_CE | untested | D1 | 3* | -0.1 | -0.1 | -0.0 | +0.9 | +0.9 |
| SENSEX | OTM_CE | untested | D2 | 3* | -0.1 | -0.1 | +0.0 | +0.2 | +0.2 |
| SENSEX | OTM_CE | untested | D3 | 3* | +0.0 | +0.0 | +0.0 | +0.1 | +0.1 |
| SENSEX | OTM_CE | untested | D4 | 3* | -0.0 | -0.0 | -0.0 | -0.0 | -0.0 |
| SENSEX | OTM_CE | untested | D5 | 2* | -0.0 | -0.0 | -0.0 | +0.0 | +0.0 |
| SENSEX | OTM_CE | untested | EXP1300 | 3* | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 |
| SENSEX | OTM_CE | tested | D1 | 7* | -0.5 | +0.1 | +0.1 | +0.1 | +0.7 |
| SENSEX | OTM_CE | tested | D2 | 8* | -0.3 | -0.1 | -0.0 | +0.0 | +0.7 |
| SENSEX | OTM_CE | tested | D3 | 7* | -0.2 | -0.1 | -0.1 | -0.0 | +0.1 |
| SENSEX | OTM_CE | tested | D4 | 4* | -0.0 | +0.0 | +0.0 | +0.0 | +0.2 |
| SENSEX | OTM_CE | tested | D5 | 3* | -0.0 | -0.0 | +0.0 | +0.0 | +0.0 |
| SENSEX | OTM_CE | tested | EXP1300 | 6* | -16.1 | -0.0 | -0.0 | +0.0 | +0.0 |
| SENSEX | OTM_PE | pooled | D1 | 10* | -0.4 | -0.2 | -0.1 | +0.4 | +0.6 |
| SENSEX | OTM_PE | pooled | D2 | 11* | -1.2 | -0.2 | +0.1 | +0.2 | +0.6 |
| SENSEX | OTM_PE | pooled | D3 | 10* | -7.4 | +0.0 | +0.1 | +0.2 | +1.7 |
| SENSEX | OTM_PE | pooled | D4 | 7* | -0.0 | +0.0 | +0.0 | +0.2 | +15.4 |
| SENSEX | OTM_PE | pooled | D5 | 5* | -6.3 | -0.0 | +0.0 | +0.0 | +0.8 |
| SENSEX | OTM_PE | pooled | EXP1300 | 9* | -9.3 | -0.0 | +0.0 | +0.1 | +0.4 |
| SENSEX | OTM_PE | untested | D1 | 1* | +0.6 | +0.6 | +0.6 | +0.6 | +0.6 |
| SENSEX | OTM_PE | untested | D2 | 1* | +0.1 | +0.1 | +0.1 | +0.1 | +0.1 |
| SENSEX | OTM_PE | untested | D3 | 1* | +0.1 | +0.1 | +0.1 | +0.1 | +0.1 |
| SENSEX | OTM_PE | untested | EXP1300 | 1* | -0.0 | -0.0 | -0.0 | -0.0 | -0.0 |
| SENSEX | OTM_PE | tested | D1 | 9* | -0.4 | -0.2 | -0.1 | +0.2 | +0.4 |
| SENSEX | OTM_PE | tested | D2 | 10* | -1.2 | -0.2 | +0.1 | +0.2 | +0.6 |
| SENSEX | OTM_PE | tested | D3 | 9* | -7.4 | +0.0 | +0.1 | +0.2 | +1.7 |
| SENSEX | OTM_PE | tested | D4 | 7* | -0.0 | +0.0 | +0.0 | +0.2 | +15.4 |
| SENSEX | OTM_PE | tested | D5 | 5* | -6.3 | -0.0 | +0.0 | +0.0 | +0.8 |
| SENSEX | OTM_PE | tested | EXP1300 | 8* | -9.3 | -0.0 | +0.0 | +0.1 | +0.4 |
| SENSEX | STRADDLE | pooled | D1 | 10* | -0.3 | +0.1 | +0.2 | +0.2 | +0.4 |
| SENSEX | STRADDLE | pooled | D2 | 11* | -0.4 | -0.1 | +0.1 | +0.1 | +0.3 |
| SENSEX | STRADDLE | pooled | D3 | 10* | -0.1 | +0.1 | +0.1 | +0.4 | +0.6 |
| SENSEX | STRADDLE | pooled | D4 | 7* | -0.3 | -0.0 | -0.0 | +0.2 | +0.4 |
| SENSEX | STRADDLE | pooled | D5 | 5* | -14.1 | +0.0 | +0.0 | +0.1 | +0.2 |
| SENSEX | STRADDLE | pooled | EXP1300 | 9* | -2.7 | -0.1 | -0.0 | +0.2 | +2.5 |
| SENSEX | STRADDLE | tested | D1 | 10* | -0.3 | +0.1 | +0.2 | +0.2 | +0.4 |
| SENSEX | STRADDLE | tested | D2 | 11* | -0.4 | -0.1 | +0.1 | +0.1 | +0.3 |
| SENSEX | STRADDLE | tested | D3 | 10* | -0.1 | +0.1 | +0.1 | +0.4 | +0.6 |
| SENSEX | STRADDLE | tested | D4 | 7* | -0.3 | -0.0 | -0.0 | +0.2 | +0.4 |
| SENSEX | STRADDLE | tested | D5 | 5* | -14.1 | +0.0 | +0.0 | +0.1 | +0.2 |
| SENSEX | STRADDLE | tested | EXP1300 | 9* | -2.7 | -0.1 | -0.0 | +0.2 | +2.5 |

## E2.B  Decay curve on MID (primary) -- per cycle, THIN

| symbol | leg | state | stamp | N | P25 | median | P75 | median on LAST |
|---|---|---|---|---:|---:|---:|---:|---:|
| NIFTY | OTM_CE | pooled | D1 | 11* | -19.9 | 8.0 | 20.8 | 8.2 |
| NIFTY | OTM_CE | pooled | D2 | 10* | -11.4 | 45.5 | 65.6 | 45.4 |
| NIFTY | OTM_CE | pooled | D3 | 10* | 20.3 | 31.0 | 79.1 | 31.1 |
| NIFTY | OTM_CE | pooled | D4 | 9* | 57.7 | 90.2 | 94.3 | 90.2 |
| NIFTY | OTM_CE | pooled | D5 | 4* | 99.2 | 99.6 | 99.6 | 99.5 |
| NIFTY | OTM_CE | pooled | EXP1300 | 11* | 69.8 | 98.9 | 99.3 | 99.0 |
| NIFTY | OTM_CE | untested | D1 | 4* | 6.9 | 9.4 | 9.4 | 9.3 |
| NIFTY | OTM_CE | untested | D2 | 4* | 64.1 | 65.6 | 65.6 | 65.5 |
| NIFTY | OTM_CE | untested | D3 | 3* | 54.3 | 83.3 | 94.0 | 83.3 |
| NIFTY | OTM_CE | untested | D4 | 3* | 90.2 | 94.8 | 99.8 | 94.8 |
| NIFTY | OTM_CE | untested | D5 | 1* | 99.2 | 99.2 | 99.2 | 99.2 |
| NIFTY | OTM_CE | untested | EXP1300 | 4* | 99.3 | 99.6 | 99.6 | 99.6 |
| NIFTY | OTM_CE | tested | D1 | 7* | -19.9 | 8.0 | 17.7 | 8.2 |
| NIFTY | OTM_CE | tested | D2 | 6* | -16.7 | -11.4 | 51.7 | -11.5 |
| NIFTY | OTM_CE | tested | D3 | 7* | 20.3 | 28.6 | 31.0 | 28.4 |
| NIFTY | OTM_CE | tested | D4 | 6* | 47.7 | 57.7 | 94.1 | 57.6 |
| NIFTY | OTM_CE | tested | D5 | 3* | 72.9 | 99.6 | 99.9 | 99.5 |
| NIFTY | OTM_CE | tested | EXP1300 | 7* | 69.8 | 93.3 | 98.9 | 93.2 |
| NIFTY | OTM_PE | pooled | D1 | 11* | -10.4 | 14.0 | 29.5 | 13.7 |
| NIFTY | OTM_PE | pooled | D2 | 10* | -72.6 | -6.8 | 65.7 | -6.7 |
| NIFTY | OTM_PE | pooled | D3 | 10* | -38.6 | 59.2 | 71.7 | 59.2 |
| NIFTY | OTM_PE | pooled | D4 | 9* | -40.2 | 67.6 | 88.1 | 67.6 |
| NIFTY | OTM_PE | pooled | D5 | 4* | -113.8 | 72.2 | 72.2 | 72.3 |
| NIFTY | OTM_PE | pooled | EXP1300 | 11* | 28.1 | 68.2 | 99.3 | 68.3 |
| NIFTY | OTM_PE | untested | D1 | 1* | 47.8 | 47.8 | 47.8 | 47.7 |
| NIFTY | OTM_PE | untested | D2 | 1* | 65.7 | 65.7 | 65.7 | 65.6 |
| NIFTY | OTM_PE | untested | D3 | 1* | 88.3 | 88.3 | 88.3 | 88.3 |
| NIFTY | OTM_PE | untested | D4 | 1* | 97.4 | 97.4 | 97.4 | 97.4 |
| NIFTY | OTM_PE | untested | EXP1300 | 1* | 99.6 | 99.6 | 99.6 | 99.6 |
| NIFTY | OTM_PE | tested | D1 | 10* | -10.4 | 11.4 | 21.5 | 11.2 |
| NIFTY | OTM_PE | tested | D2 | 9* | -72.6 | -6.8 | 59.5 | -6.7 |
| NIFTY | OTM_PE | tested | D3 | 9* | -38.6 | 59.2 | 70.5 | 59.2 |
| NIFTY | OTM_PE | tested | D4 | 8* | -40.2 | 67.6 | 74.1 | 67.6 |
| NIFTY | OTM_PE | tested | D5 | 4* | -113.8 | 72.2 | 72.2 | 72.3 |
| NIFTY | OTM_PE | tested | EXP1300 | 10* | 28.1 | 50.0 | 98.9 | 50.2 |
| NIFTY | STRADDLE | pooled | D1 | 11* | 2.1 | 4.3 | 6.4 | 4.2 |
| NIFTY | STRADDLE | pooled | D2 | 10* | 3.6 | 9.2 | 17.9 | 9.2 |
| NIFTY | STRADDLE | pooled | D3 | 10* | 20.1 | 24.1 | 29.7 | 24.1 |
| NIFTY | STRADDLE | pooled | D4 | 9* | 10.9 | 39.1 | 41.4 | 39.0 |
| NIFTY | STRADDLE | pooled | D5 | 4* | -19.3 | 8.3 | 8.3 | 8.3 |
| NIFTY | STRADDLE | pooled | EXP1300 | 11* | -11.0 | 32.6 | 40.5 | 32.7 |
| NIFTY | STRADDLE | tested | D1 | 11* | 2.1 | 4.3 | 6.4 | 4.2 |
| NIFTY | STRADDLE | tested | D2 | 10* | 3.6 | 9.2 | 17.9 | 9.2 |
| NIFTY | STRADDLE | tested | D3 | 10* | 20.1 | 24.1 | 29.7 | 24.1 |
| NIFTY | STRADDLE | tested | D4 | 9* | 10.9 | 39.1 | 41.4 | 39.0 |
| NIFTY | STRADDLE | tested | D5 | 4* | -19.3 | 8.3 | 8.3 | 8.3 |
| NIFTY | STRADDLE | tested | EXP1300 | 11* | -11.0 | 32.6 | 40.5 | 32.7 |
| SENSEX | OTM_CE | pooled | D1 | 10* | -1.9 | 15.8 | 28.8 | 16.7 |
| SENSEX | OTM_CE | pooled | D2 | 11* | -2.1 | 59.0 | 81.1 | 59.2 |
| SENSEX | OTM_CE | pooled | D3 | 10* | 33.5 | 55.3 | 89.0 | 55.2 |
| SENSEX | OTM_CE | pooled | D4 | 7* | 96.0 | 96.8 | 97.2 | 96.8 |
| SENSEX | OTM_CE | pooled | D5 | 5* | 99.8 | 100.0 | 100.0 | 100.0 |
| SENSEX | OTM_CE | pooled | EXP1300 | 9* | 96.8 | 98.9 | 99.4 | 98.9 |
| SENSEX | OTM_CE | untested | D1 | 3* | 15.8 | 19.9 | 45.0 | 19.8 |
| SENSEX | OTM_CE | untested | D2 | 3* | 57.3 | 59.0 | 81.4 | 59.2 |
| SENSEX | OTM_CE | untested | D3 | 3* | 87.5 | 89.0 | 96.9 | 89.1 |
| SENSEX | OTM_CE | untested | D4 | 3* | 96.0 | 96.8 | 99.3 | 96.8 |
| SENSEX | OTM_CE | untested | D5 | 2* | 99.8 | 99.8 | 100.0 | 99.8 |
| SENSEX | OTM_CE | untested | EXP1300 | 3* | 98.3 | 98.9 | 99.6 | 98.9 |
| SENSEX | OTM_CE | tested | D1 | 7* | -1.9 | 10.2 | 20.8 | 10.9 |
| SENSEX | OTM_CE | tested | D2 | 8* | -2.1 | 62.1 | 78.0 | 62.0 |
| SENSEX | OTM_CE | tested | D3 | 7* | 33.5 | 39.7 | 55.3 | 39.6 |
| SENSEX | OTM_CE | tested | D4 | 4* | 70.6 | 97.2 | 97.2 | 97.2 |
| SENSEX | OTM_CE | tested | D5 | 3* | 99.5 | 100.0 | 100.0 | 100.0 |
| SENSEX | OTM_CE | tested | EXP1300 | 6* | 76.4 | 96.8 | 99.4 | 96.8 |
| SENSEX | OTM_PE | pooled | D1 | 10* | -21.5 | 0.8 | 15.7 | 0.8 |
| SENSEX | OTM_PE | pooled | D2 | 11* | -51.3 | -8.4 | 65.2 | -8.5 |
| SENSEX | OTM_PE | pooled | D3 | 10* | -73.7 | 66.5 | 91.4 | 66.6 |
| SENSEX | OTM_PE | pooled | D4 | 7* | -124.2 | 55.4 | 85.3 | 55.6 |
| SENSEX | OTM_PE | pooled | D5 | 5* | -8.2 | 100.0 | 100.0 | 100.0 |
| SENSEX | OTM_PE | pooled | EXP1300 | 9* | 35.7 | 93.1 | 99.2 | 93.1 |
| SENSEX | OTM_PE | untested | D1 | 1* | 2.2 | 2.2 | 2.2 | 2.9 |
| SENSEX | OTM_PE | untested | D2 | 1* | 85.5 | 85.5 | 85.5 | 85.6 |
| SENSEX | OTM_PE | untested | D3 | 1* | 95.7 | 95.7 | 95.7 | 95.7 |
| SENSEX | OTM_PE | untested | EXP1300 | 1* | 99.6 | 99.6 | 99.6 | 99.6 |
| SENSEX | OTM_PE | tested | D1 | 9* | -21.5 | 0.8 | 15.7 | 0.8 |
| SENSEX | OTM_PE | tested | D2 | 10* | -51.3 | -22.1 | 64.0 | -21.5 |
| SENSEX | OTM_PE | tested | D3 | 9* | -73.7 | 66.5 | 90.9 | 66.6 |
| SENSEX | OTM_PE | tested | D4 | 7* | -124.2 | 55.4 | 85.3 | 55.6 |
| SENSEX | OTM_PE | tested | D5 | 5* | -8.2 | 100.0 | 100.0 | 100.0 |
| SENSEX | OTM_PE | tested | EXP1300 | 8* | 35.7 | 93.1 | 97.7 | 93.1 |
| SENSEX | STRADDLE | pooled | D1 | 10* | -2.4 | 2.8 | 7.9 | 2.8 |
| SENSEX | STRADDLE | pooled | D2 | 11* | -5.3 | 9.5 | 19.5 | 9.6 |
| SENSEX | STRADDLE | pooled | D3 | 10* | -20.4 | 15.2 | 42.6 | 15.3 |
| SENSEX | STRADDLE | pooled | D4 | 7* | 2.5 | 45.4 | 50.3 | 45.3 |
| SENSEX | STRADDLE | pooled | D5 | 5* | 9.3 | 48.6 | 55.8 | 48.7 |
| SENSEX | STRADDLE | pooled | EXP1300 | 9* | -49.3 | 47.0 | 56.2 | 47.1 |
| SENSEX | STRADDLE | tested | D1 | 10* | -2.4 | 2.8 | 7.9 | 2.8 |
| SENSEX | STRADDLE | tested | D2 | 11* | -5.3 | 9.5 | 19.5 | 9.6 |
| SENSEX | STRADDLE | tested | D3 | 10* | -20.4 | 15.2 | 42.6 | 15.3 |
| SENSEX | STRADDLE | tested | D4 | 7* | 2.5 | 45.4 | 50.3 | 45.3 |
| SENSEX | STRADDLE | tested | D5 | 5* | 9.3 | 48.6 | 55.8 | 48.7 |
| SENSEX | STRADDLE | tested | EXP1300 | 9* | -49.3 | 47.0 | 56.2 | 47.1 |

## Excluded cycles

| window/symbol | expiry | days | why |
|---|---|---:|---|
| W1/NIFTY | 2026-03-24 | 4 | left-truncated: the window starts mid-cycle and the preceding expiry is outside it, so day-1 is unverifiable |
| W1/NIFTY | 2026-03-30 | 2 | front expiry unknown on 2026-03-30: cycle ended at the gap |
| W1/SENSEX | 2026-03-19 | 1 | front expiry unknown on 2026-03-17: cycle ended at the gap |
| W1/SENSEX | 2026-04-02 | 1 | front expiry unknown on 2026-03-30: cycle ended at the gap |
| W1/SENSEX | 2026-06-04 | 3 | cycle ends 2026-06-02, not on its expiry 2026-06-04 (truncated by the window or by missing data) |
| W1/SENSEX | 2026-03-25 | 4 | Day-1 10:30 ATM_CE mid: stale 37m > 10m budget |
| W2/NIFTY | 2026-08-25 | 2 | left-truncated: the window starts mid-cycle and the preceding expiry is outside it, so day-1 is unverifiable |
| W2/NIFTY | 2026-09-15 | 3 | cycle ends 2026-09-11, not on its expiry 2026-09-15 (truncated by the window or by missing data) |
| W2/SENSEX | 2026-08-27 | 4 | left-truncated: the window starts mid-cycle and the preceding expiry is outside it, so day-1 is unverifiable |
| W2/SENSEX | 2026-09-17 | 1 | cycle ends 2026-09-11, not on its expiry 2026-09-17 (truncated by the window or by missing data) |

