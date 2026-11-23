# Pin behaviour study v4: Step 0 result (2026-11-21, MR-PIN2)

**Study:** `claude/pin/pin_behaviour_study_v4_FROZEN_2026-11-20.md`, sha256 69ca96868709df554ea42eb632e44903a0b83b56e9d38c08c682929974c41338. **Prompt:** `claude/pin/cc_prompt_pin_behaviour_A_step0.md`.
**Box output:** `~/meridian-cc/docs/research/pin_proof/lookback_v4/` (coverage.md sha256 81ed1f41…1e15, walls.md 33d85352…e7de, step0_disk_checks.txt f9a8d0ec…3f5a, SHA256SUMS a83e6d77…2878 over 715 files). Finished 2026-11-21 ~07:20 IST. Figures below are as printed by Claude Code.
Read-only. 80 of 80 spot and option coverage queries and 27 of 27 expiry-day queries OK; every EXPLAIN gate passed; slowest query 2.909 s; no retry. Nothing outside `lookback_v4/` was written; no git write.

## Coverage (0a)

| | NIFTY | SENSEX |
|---|---|---|
| Option bars, contiguous | 2025-04-01 to 2026-03-30 | 2025-04-01 to 2026-03-30 |
| Stray option-bar days after that | 1 (2026-05-07) | 2 (2026-05-04, 2026-05-07) |
| Spot sessions in the window to 2026-11-19 | 406 | 405 |
| Sessions with option bars at 12:30 | 247 (246 exact, 1 within ±120 s) | 247 (245 exact, 2 within ±120 s) |
| Sessions without option bars | 159 | 159 |
| Last spot bar | 15:30:59 on 247 sessions; about 09:58-09:59 on the other 159 | 15:30:59 on 245, 15:29:59 on 1; early on 159 |
| Distinct front expiry dates | 54 | 55 (2026-01-15 is not a session) |
| Expiry days with the expiring contract's bars at 10:00 and 15:00 | 53 of 54 | 52 of 54 |

- **The usable history is 247 sessions per symbol, 2025-04-01 to 2026-03-30 (twelve months), not to November 2026.** The 159 sessions without option bars are the same 159 whose stored spot ends before 10:00: one upstream cause (the history backfill stops at 2026-03-30).
- The stored spot runs to 15:30:59 inside the usable window. The 15:14-15:29 hole recorded for the live path does not apply to this history.
- Expiry days are covered (the backfill skipped greeks on expiry day, not bars).
- SENSEX 2025-04-28 has option bars at 12:30 and no spot bar in the session window.
- Consequences for v4: the case days 2026-11-18 and 2026-11-19 are not in this history; M7's cut-off (2026-03-31) now covers the whole usable window; no later sessions remain as a holdout for the parked predictive test.

## Contamination (0b)

Four ranges in `data_contamination_ranges`; none names `hist_option_bars_1m` or `hist_spot_bars_1m`. Nothing excluded. (HOLIDAY-FROZEN-CHAIN names 2026-10-02, a non-session and outside the usable window.)

## Stored OI moves intraday (0c)

On the 24 sample days: total OI identical at 10:00, 12:30 and 15:00 on 0 of 12 days per symbol. Median absolute change 10:00 to 15:00 as a share of the 10:00 total: NIFTY calls 17.5 %, puts 17.8 %; SENSEX calls 26.7 %, puts 13.3 %. Every comparable strike changes (median 27 of 27 NIFTY, 46 of 46 SENSEX). Pins built from this history are intraday objects.

## Gamma robustness of the pin strike (0d), 36 minutes per symbol, none on an expiry day

| Same strike under in-study gamma and stored OTM-leg gamma | NIFTY | SENSEX |
|---|---|---|
| T (textbook, both sides added) | 33 of 36 = 91.7 % | 35 of 36 = 97.2 % |
| N (Board's rule) | 35 of 36 = 97.2 % | 30 of 36 = 83.3 % |

- Median ratio of in-study gamma to stored OTM-leg gamma at the ATM strike: NIFTY 1.0099 (0.8075 to 1.1612), SENSEX 0.9990 (0.8163 to 1.1517).
- Disagreements run up to 20 strike steps. Claude Code reads them as near-ties in the argmax, not a gamma scale error. Not yet examined minute by minute.
- **v4 §4 0d: T agreement is under 95 % on NIFTY, so Prompt B waits for the operator's ruling on which gamma the study uses.**
- Limit: the in-study gamma uses one volatility for all strikes (no smile); the stored OTM-leg gamma uses each strike's own solved volatility. They differ most away from the money.
- Strike step confirmed: NIFTY 50, SENSEX 100.

## Wall rule (0e)

`public.v_gex_strike_walls`, `sql/2026-09-15_s79_v_gex_strike_walls.sql:47` (S79, ENH-120): put wall = strike with the largest `oi_put`, call wall = strike with the largest `oi_call`, among strikes with |strike − spot| <= band × σ, band default 1.5 (parameter `wall.band.<symbol>`), σ = spot × atm_iv/100 × √(max(dte, 1)/252). Raw OI, not gamma-weighted. Zero-OI strikes cannot win. Corridor state INSIDE / ABOVE_CEILING / BELOW_FLOOR / UNDEFINED.
- **No tie-break is specified** (`array_agg(strike ORDER BY oi DESC)[1]`): two strikes tied on OI resolve arbitrarily. A Board finding for the discrepancy list.
- **Not verified as the live view** (Rule 25 md5 not taken; Step 0 allowed no database call for this part). `public.latest_gamma_walls` appears in grant lists and has no definition in `sql/`.
- This differs from the fallback written in v4 §2 (walls on their own side of the ATM strike). v4 says to use the Board's rule; Prompt B uses this one, with the study's tie-break (nearer to spot, then lower strike) stated.

## Open before Prompt B

1. Operator ruling on the study's gamma (0d).
2. Rule 25 check of `v_gex_strike_walls` (one catalog read, in Prompt B).
3. v4's window wording ("to 2026-11-19") is read as "every session with option bars": 2025-04-01 to 2026-03-30, plus the three stray May 2026 days reported separately.
