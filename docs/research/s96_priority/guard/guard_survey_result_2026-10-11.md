# Untraded-leg guard survey — result (TD-S95-NEW-1 (c))

**Session:** S96 · **Date:** 2026-10-11 · **Ruled:** S96-D (`docs/research/s92_parity/rulings_s96.md`)
**Code:** `docs/research/s96_priority/guard/` at 345d1b2 (`guard_cycles.sql`, `guard_run.sh`, `guard_summary.py`)
**Run:** `~/meridian-cc`, 2026-10-11, under `ulimit -v 700000`, read-only through `bin/roq.sh`.

## Pinned outputs

| File | sha256 |
|---|---|
| `~/guard_out/SHA256SUMS` (45 per-date CSVs) | `fdf0bece0edb9b657a92e04542f5ea6af955e2a4b5aaa387738673566c3913df` |
| `~/guard_run.log` (46 lines) | `6005ea575aa64c46c3d7b6f13eb206ab24f2a6c3283d964f608c20e5b4adbea9` |
| `~/guard_summary.log` | `60aa45f3b77f16b2780592f37031a172f416b9538a3508f24454b4a257d1db13` |

## What was measured

For every front-expiry cycle from 09:15 to 15:15 IST, across 2026-08-26 to 2026-10-09 (the chain is not
kept before 08-26; see the M-P7 result for NO_FRONT on 08-24 and 08-25), the share of the front DEX gross
`Σ|δ·oi·spot/1e7|` that sits on suspect legs:

- **S1**: volume 0 so far (or NULL) on a leg with oi > 0.
- **S2**: S1 and `oi_change = oi`. All of today's OI is new, yet nothing traded.

Marked days are the TD-S95-NEW-1 days: SENSEX 2026-09-25, 09-28 and 09-29, where the M-P7 secondary showed
OPPOSITE on 205 of 216 cycles. NIFTY: 31 sessions. SENSEX: 31 sessions, 3 of them marked. Volume was never NULL.

## Result

Shares of the front DEX gross, by bucket. Unmarked max is the largest value on any unmarked cycle; marked min
is the smallest value on any marked cycle.

| Symbol | Signature | Bucket | Unmarked max | Marked min | |
|---|---|---|---|---|---|
| SENSEX | S2 | early 09:15–10:00 | 0.06 % (245 cycles) | 70.62 % (27) | separates |
| SENSEX | S2 | mid 10:00–14:30 | 0.02 % (1,509) | 69.01 % (162) | separates |
| SENSEX | S2 | late 14:30–15:15 | 0.02 % (252) | 70.05 % (27) | separates |
| SENSEX | S1 | early | 16.63 % | 70.62 % | separates, narrowly |
| SENSEX | S1 | mid | 1.63 % | 69.02 % | separates |
| SENSEX | S1 | late | 1.61 % | 70.06 % | separates |
| NIFTY | S2 | all | 0.00 % | — | |
| NIFTY | S1 | early | 11.69 % | — | |

Further detail:

- **Marked days, S2 gross median:** 97.69 %, 93.90 % and 70.50 %. **S2 OI share max:** 98.30 %, 93.70 % and 85.44 %. Unmarked S2 OI share max is 0.05 %.
- **S1 is almost identical to S2 on the marked days.** The defect is OI that appeared with no trade, not ordinary early-morning inactivity.
- **S2 legs do occur on normal days** (SENSEX 09-07 to 09-10 had 14–15 legs; 09-18 had 7), but never above 0.06 % of gross.
- **S1 on normal mornings reaches 16.63 % (SENSEX 10-09) and 11.69 % (NIFTY 09-25).** That is legitimate pre-trade OI, so S1 cannot be a live rule.

## Limits

- **The three marked days are consecutive, all SENSEX, and probably one vendor episode.** The gap is wide but rests on one event, not three independent ones.
- NIFTY has never shown the defect in the retention window, so the rule is untested there against a positive case.

## Threshold

The 2 % threshold was derived, not fitted: it is the geometric mean of the two edges,
√(0.06 × 69.01) = 2.03 %, rounded to 2 %. That puts it 33× above the unmarked max (2 / 0.06) and 34.5× below the
marked min (69.01 / 2). The alternatives weighed were 5 % (83× and 13.8×) and excluding the S2 legs rather than
abstaining. Exclusion was rejected: on the marked days it drops 70–99 % of gross and shows a remainder taken
from the same bad snapshot.

## Ruling (S96-D)

- **G1:** per cycle, abstain when the S2 share of front DEX gross is ≥ 2 %.
- **G2:** computed in the database as columns appended to `v_dex_flow_vs_book` (`leg_s2_gross_cr`, `leg_s2_gross_share`, `untraded_guard`). This is additive through `CREATE OR REPLACE`; the existing checks are re-run, and the share is recomputed independently against `guard_cycles.sql`.
- **G3:** it gates the M-P7 SAME / OPPOSITE badge only. The abstain reason string needs the operator's yes before it goes live. DEX tiles and bricks are unchanged.

Nothing is applied by this document.
