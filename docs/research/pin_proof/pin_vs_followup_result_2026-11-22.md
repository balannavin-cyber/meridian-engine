<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/pin_vs_followup_result_2026-11-22.md -->
# VS follow-up: result, 2026-11-22

Session MR-PIN2. Prompt: `cc_prompt_pin_vs_followup.md`. Run 2026-11-22 07:37–07:50 IST, read-only. POST-HOC diagnostics on the replay v2 data (`pin_live_replay_v2_result_2026-11-21.md`) plus one new read (pin band). No pass marks. Nothing here is authorised for the Board or production.

Source: the Claude Code screen print. Full text on the engine box: `~/meridian-cc/docs/research/pin_proof/fix/followup/followup.md`, 173 lines, sha256 `9c11af12d79da5906e7afa8bbf6f36ad32f1f3b531e616182f286fc99c8ebdf4`.

## A1. Expiry days one by one (market runs; clear lead = K's lead ≥ 5 %)

| Symbol | Expiry days | Pooled VS = K, clear lead | Pooled V2 = K, clear lead | VS = K, all valid | Lowest single day (VS, clear lead) | Median abs(VS − S), steps | Median abs(B − S), steps |
|---|---|---|---|---|---|---|---|
| NIFTY | 12 | 98.7 % (766/776) | 97.6 % (757/776) | 97.5 % (862/884) | 92.1 % (58/63), 2026-10-27 | 0.45 | 1.44 (B on 506/884 runs) |
| SENSEX | 13 | 98.9 % (738/746) | 96.5 % (720/746) | 96.4 % (929/964) | 87.0 % (40/46), 2026-08-27 | 0.73 | 2.27 (B on 520/964 runs) |

VS is at 100 % of clear-lead runs on 7 of 12 NIFTY and 10 of 13 SENSEX expiry days. SENSEX 2026-11-19: VS 100.0 % (59/59), V2 98.3 %.

## A2. Near-ties (K's lead < 5 %), all 58 days, market runs

| Symbol | Runs | VS = K | abs(VS − K) ≤ 1 step | ≤ 2 steps | Max | VS is K's first or second strike by K's own score |
|---|---|---|---|---|---|---|
| NIFTY | 585 | 87.9 % (514) | 89.4 % | 97.8 % | 8 steps | 99.8 % (584/585) |
| SENSEX | 576 | 91.1 % (525) | 94.1 % | 96.0 % | 10 steps | 99.7 % (574/576) |

## A3. SENSEX 2026-11-19 (expiry day), 75 market runs

- Outside the stored corridor [put wall, call wall]: B 2 of 75, VS 0 of 75, K 0 of 75.
- Pin changes: B 32, VS 19, K 19. Frozen runs: 17 of 75 (22.7 %).
- On the sampled frozen runs (10:00, 10:45–11:30, 12:00, 12:30, 12:45) VS and K read 82,000 or 82,500 while on the unfrozen runs between them they read 82,200 or 82,300: the frozen runs move the gross pin too.

## A4. Days where VS misses a day mark (95 % clear lead, 85 % all valid)

NIFTY 2026-08-27 (all valid 83.8 %), 2026-09-28 (clear 89.5 %, all 66.2 %), 2026-10-27 (clear 92.1 %); SENSEX 2026-08-26 (64.9 %), 2026-08-27 (clear 87.0 %, all 81.1 %). All UNSEEN, none with a frozen run; where VS and K differ the median gap is 1–2 steps.

## B. The pin band

- Definition: `public.v_gex_strike_pin_zone`, `~/meridian-engine/sql/2026-10-26_s101_v_gex_strike_pin_zone_live_captured.sql:30`. The band starts at the strike with the largest **positive** `gex_cr` (`:81`) and walks outward strike by strike while each neighbour has `gex_cr > 0` and `gex_cr ≥ tau × peak` (`:112`); `tau` = parameter `pin.tau.<symbol>`, default 0.3 (`:79`). `pin_lower` / `pin_upper` are the ends of that walk (`:118-119`).
- So the band is built on the netted quantity, around the net-long peak, not around the pin. A strike with negative `gex_cr` can never be inside it.
- History: `gex_pin_maxpain_history` has `pin_lower` and `pin_upper` per `run_id`, but returned 0 rows for both symbols on 2026-11-16 to 2026-11-20. Its extent is unmeasured (the only plan for a whole-table min/max was a sequential scan, not run). `gex_cycle_history` stores no band.
- Therefore VS against the band is NOT MEASURED. The band was not reconstructed.

## Reading

1. Expiry day: VS keeps its agreement with the ruled pin, day by day, not only pooled.
2. Near-ties: when VS and the ruled pin differ, VS is almost always on the ruled pin's runner-up.
3. Thursday 19 Nov, SENSEX: against the walls, the gross pin never left the corridor. The day's churn is partly frozen-OI runs, which move any pin.
4. The Board's "pin outside its band" on that day is not addressed by VS. By its definition the band follows the netted net-long peak; a gross pin near spot has no reason to sit inside it. This is an inference from the view's rule, not a measurement.
