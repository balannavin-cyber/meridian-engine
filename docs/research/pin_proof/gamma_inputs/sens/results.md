# MR-PIN2 step 3 — results: does a futures-implied rate bring call and put gamma together?

Claim tested: the flat `r = 6.5 %` is the main cause of Part B's call/put gamma disagreement, and re-solving each leg at a rate implied by the Fyers near-month futures should bring the two together at one strike.

Read-only. No database write, no vendor call, no outcome computed — nothing here reads a price after a sampled minute. Gates in `gates.md`, conventions and the solver provenance in `conventions.md`, per-minute inputs in `per_minute.csv`, per-day numbers in `per_day.csv`.

## Verdicts

**SENS NIFTY FAIL: in-band before 5/12, after 5/12, left band 1, solver failures 0/700.**
**SENS SENSEX FAIL: in-band before 7/12, after 9/12, left band 0, solver failures 0/1158.**

r_m per symbol (% a year): NIFTY median 7.0113, min 2.8884, max 10.2403; SENSEX median 7.9545, min 1.7194, max 11.5076.

Flagged r_m outside [-5 %, +20 %]: none.

## Per day, verdict minutes (futures bar volume > 0)

### NIFTY — 36 of 36 minutes, 12 of 12 days

| day | v-mins | pairs | γ ratio before | γ ratio after | in band before | after | IV ratio before | IV ratio after |
|---|---|---|---|---|---|---|---|---|
| 2025-04-01 | 3 | 29 | 0.8976 | 0.9256 | NO | NO | 1.1696 | 1.1187 |
| 2025-05-02 | 3 | 29 | 1.1066 | 1.0700 | NO | NO | 0.8989 | 0.9314 |
| 2025-06-02 | 3 | 29 | 0.9641 | 0.9680 | YES | YES | 1.0392 | 1.0347 |
| 2025-07-01 | 3 | 30 | 0.9428 | 0.9252 | NO | NO | 1.0839 | 1.1126 |
| 2025-08-01 | 3 | 30 | 1.0883 | 1.0211 | NO | YES | 0.9051 | 0.9752 |
| 2025-09-01 | 3 | 24 | 0.8817 | 0.8808 | NO | NO | 1.3623 | 1.3558 |
| 2025-10-01 | 3 | 30 | 0.9090 | 0.9264 | NO | NO | 1.1566 | 1.1182 |
| 2025-11-03 | 3 | 28 | 0.8116 | 0.8296 | NO | NO | 1.4382 | 1.4044 |
| 2025-12-01 | 3 | 29 | 0.9898 | 0.9925 | YES | YES | 1.1917 | 1.1750 |
| 2026-01-01 | 3 | 32 | 1.0427 | 1.0791 | YES | NO | 0.9071 | 0.8650 |
| 2026-02-01 | 3 | 30 | 1.0203 | 1.0069 | YES | YES | 0.9781 | 0.9923 |
| 2026-03-04 | 3 | 30 | 1.0094 | 1.0160 | YES | YES | 0.9906 | 0.9841 |

### SENSEX — 26 of 36 minutes, 12 of 12 days

| day | v-mins | pairs | γ ratio before | γ ratio after | in band before | after | IV ratio before | IV ratio after |
|---|---|---|---|---|---|---|---|---|
| 2025-04-02 | 1 | 15 | 0.9823 | 1.0359 | YES | YES | 1.0209 | 0.9607 |
| 2025-05-02 | 2 | 32 | 1.0821 | 1.0591 | NO | NO | 0.8842 | 0.9297 |
| 2025-06-02 | 2 | 33 | 1.0277 | 1.0276 | YES | YES | 0.9530 | 0.9560 |
| 2025-07-02 | 1 | 16 | 1.0674 | 0.9928 | NO | YES | 0.9282 | 1.0098 |
| 2025-08-01 | 1 | 16 | 0.9778 | 0.9602 | YES | YES | 1.0276 | 1.0515 |
| 2025-09-01 | 2 | 32 | 0.8937 | 0.9336 | NO | NO | 1.2963 | 1.2013 |
| 2025-10-03 | 3 | 48 | 0.9564 | 1.0214 | YES | YES | 1.0635 | 0.9680 |
| 2025-11-03 | 2 | 33 | 0.7922 | 0.8362 | NO | NO | 1.3379 | 1.2564 |
| 2025-12-01 | 3 | 52 | 0.8966 | 0.9521 | NO | YES | 1.1882 | 1.0809 |
| 2026-01-02 | 3 | 50 | 0.9883 | 1.0205 | YES | YES | 1.0219 | 0.9602 |
| 2026-02-01 | 3 | 48 | 1.0025 | 1.0268 | YES | YES | 0.9974 | 0.9715 |
| 2026-03-02 | 3 | 48 | 0.9827 | 1.0029 | YES | YES | 1.0196 | 0.9970 |

## All 72 minutes — descriptive, no verdict

| sym | in band before | in band after |
|---|---|---|
| NIFTY | 5/12 | 5/12 |
| SENSEX | 6/12 | 8/12 |

SENSEX verdict-minute and all-72 readings agree on whether the 10-of-12 bar is met.

## Control C-flat — one flat rate per symbol, no verdict

| sym | C-flat r (% a year) | in-band days on verdict minutes |
|---|---|---|
| NIFTY | 7.0113 | 4/12 |
| SENSEX | 8.4309 | 7/12 |

C-flat separates *having a market-derived level* from *having it per minute*: if C-flat scores like r_m, the per-minute basis carried no information the single median level did not.

## The 1–3 % band — descriptive, no verdict

| sym | pairs | pooled γ ratio before | after | in-band days before | after |
|---|---|---|---|---|---|
| NIFTY | 429 | 1.0474 | 1.0276 | 5/12 | 6/12 |
| SENSEX | 300 | 1.0066 | 1.0021 | 9/12 | 12/12 |

## IV_TOL noise floor

| sym | pair-set legs | vol points p50 | p90 | max | returned on budget rather than tolerance |
|---|---|---|---|---|---|
| NIFTY | 700 | 0.0001 | 0.0002 | 0.0008 | 0 of 700 |
| SENSEX | 1158 | 0.0000 | 0.0001 | 0.0001 | 0 of 1158 |

## What this test could not see

- **OTM-leg truth.** The pair set conditions on **both** legs having solved, so it measures agreement only where both worked — never on the ITM legs that returned NULL (Part B B2: every NULL is ITM, 0.0 % of OTM legs are NULL). Bringing a call and a put together says nothing about which of the two is right; Part B's verdict (take the OTM leg's gamma) chose that leg because it is the leg that solves, not because it was shown to be more accurate. This test does not change that.
- **Lumpy dividends.** `r_m = ln(F/S)/T_fut` is a **net carry** figure with dividends inside it (`core/bs_engine.py:77-84`; FUTURES CONTRACT RULE, `BLOCKED.txt:235-237`). It is not a risk-free rate. Index dividends arrive in lumps, so a single `r_m` spreads a discrete ex-dividend step evenly across `T_fut`; near-month futures over an ex-dividend-heavy stretch carry a basis this model cannot decompose into rate and yield.
- **SENSEX alignment.** Per the PART H section (`BLOCKED.txt:280-283`), the offset-0 rule stands by operator decision, but SENSEX 2026-03-02 10:00 is **not independently confirmed** (SENSEX26MARFUT is 80880.50 at both offset 0 and +60, so that minute's F is the same either way, and the alignment re-check was INCONCLUSIVE on it). SENSEX alignment rests on the 2025-05-02 two-day test plus two unambiguous minutes. Every SENSEX number above carries that caveat.
- **Stale bar closes.** F is a one-minute bar close, and a zero-volume bar is a stale print carrying a stale basis — 10 of the 72 minutes, all SENSEX. Those minutes are excluded from the verdict but reported in 3f. The option legs have the same exposure and no volume filter at all: `hist_option_bars_1m` carries no bid/ask, so a thin strike's `close` may be an old print, and the solve cannot tell that from a quote.
- **`T` does not decay intraday** (`backfill_hist_greeks.py:289-290`), so 10:00 and 15:00 on one day share a `T_opt`. Any error that induces is common to the three sampled minutes and invisible to a within-day comparison.
- **Solver resolution.** `IV_TOL = 1e-3` is a tolerance on the price residual, so the σ it resolves to is `≈ IV_TOL / vega` and varies by leg; the measured distribution is in the table above. This noise is present identically in the before and after numbers, so it does not bias the comparison, but it bounds how small a real change the test can distinguish.
- **72 minutes of ~90,000.** Three minutes on the first available `DONE` day of each month, no expiry day at all (`SKIP_EXPIRY`), nothing about the open, the close after 15:00, or intraday drift.
- **One rate per minute, applied to every leg.** A single `r_m` cannot represent a term structure or a strike-dependent funding effect, and the re-solve changes `r` only — spot, price, `T` and the band are held fixed by construction, which is the point, but it also means any residual disagreement is attributed to 'not the rate' without identifying what it is.

## UNMEASURED

- The `fut_dte < 3` exclusion never fired on this sample (Part H: fut_dte 22–30), so it is untested by this data.
- `next contract used` is judged only inside the six sampled windows, so its zero is not independent evidence that the nearer contract always had a bar (`BLOCKED.txt:259-261`).
