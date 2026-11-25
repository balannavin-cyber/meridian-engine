# V2 rule conformance check (V-2): pre-registration

**Status:** FROZEN, Wed 2026-11-25. Approved by the operator 09:48 IST the same day.
**Lane:** pin (MR-PIN3). **PK path:** `claude/pin/v2_rule_conformance_prereg_FROZEN_2026-11-25.md`. **Git mirror owed:** `meridian-engine:docs/research/pin_proof/`.
**Authorises:** a test on saved fixture data. It authorises nothing in production, on the Board, or in the database.

## 1. Question

Does the engine's new code (`merdian_compute/gamma_v2.py`) compute exactly rule v1.1, and are the old code's outputs untouched?

This is a check of arithmetic and isolation. It does not ask whether the new figures are better, and it reads no price outcome.

## 2. What is under test

- **Code:** `merdian_compute/gamma_v2.py` at a commit the engine will name. The hash is recorded in the result, before the comparison is run.
- **Rule:** v1.1, quoted in section 3 exactly as the engine issued it on 25 Nov 2026. The version stamp on stored rows (step 11) is being changed from `v2-1.0` to `v2-1.1` at the pin lane's request. The stamp is not among the compared fields, so that change does not alter this check.

## 3. Rule v1.1, verbatim

> **V2 per-strike exposure, rule v1.1.**
>
> **Scope.** One map per symbol, expiry and run. A run whose chain rows carry more than one expiry is an error and has no V2 output. V2 runs only after V1 succeeds.
>
> **Spot.** S is the run's spot. From chain rows, S is the spot of the rows with spot > 0; all such rows of a run must carry the same value. If they carry more than one distinct value, the run is an error and has no V2 output. (V1 takes the first row with spot > 0 in read order, which is not a defined order.) From stored per-strike rows, S for each strike is that row's own spot.
>
> **Row set.** One output row per strike K > 0 with OI_c + OI_p > 0.
>
> 1. **Leg OI.** From chain rows, OI_c and OI_p are the sums of oi over that leg's rows; a missing or non-positive oi counts as 0. From stored rows, oi_call and oi_put are already the leg sums.
> 2. **Leg gamma.** From chain rows, the largest vendor gamma > 0 among that leg's rows; none if no row has gamma > 0. From stored rows, gamma_call or gamma_put when it is > 0; NULL or ≤ 0 is none. The handling of more than one row per leg was not part of the audited rule.
> 3. **Guard, per leg, before averaging.** If |K − S| > 0.05 × S and the leg's gamma > 5e-5, the leg has no gamma. Within 5 % of spot the guard never acts and this rule equals the audited one-gamma rule. Beyond 5 % the per-leg guard is an addition the audit did not test.
> 4. **Strike gamma.** gamma_strike is the mean when both legs have gamma after step 3; the one that has it when only one does; none otherwise. gamma_legs is both, call_only or put_only accordingly, and None when gamma_strike is none.
> 5. **Net exposure.** net_cr(K) = gamma_strike × (OI_c − OI_p) × S² / 1e7, in Crore. It is 0 when gamma_strike is none.
> 6. **Map membership.** in_map is true when at least one leg has gamma at step 2, before the guard. (Every output row already has OI_c + OI_p > 0.) A strike with net_cr exactly 0 stays in the map.
> 7. **Gross exposure and band.** gross_cr(K) = gamma_strike × (OI_c + OI_p) × S² / 1e7, in Crore, and 0 when gamma_strike is none. in_band is true when |K − S| ≤ 0.05 × S. The band set is the strikes with in_band true and gross_cr > 0.
> 8. **Edge arithmetic.** The two distance tests in steps 3 and 7 are done in exact decimal arithmetic on the strike and spot as given, not in floating point. They are complements: a strike is either in the band or beyond the guard distance.
> 9. **Run figures.**
>    - net_cr = sum of net_cr(K) over the map; 0 when the map is empty.
>    - net_top_share = max |net_cr(K)| / Σ |net_cr(K)| over the map; None when that sum is 0.
>    - gross_band_cr = sum of gross_cr(K) over the band set; 0 when the band set is empty.
>    - gross_top_share = max gross / gross_band_cr; None when the band set is empty.
>    - gross_hhi = Σ (gross_cr(K) / gross_band_cr)² over the band set; None when the band set is empty.
>    - n_map = number of strikes with in_map true.
>    - n_zero = number of those with net_cr exactly 0.
> 10. **Not produced.** No flip, regime, zone, expansion probability, max-gamma strike or pin-risk score.
> 11. **Stored** in gex_strike_v2 and gex_run_v2 only. No V1 column is written.

## 4. Inputs

Six golden fixture days in the engine repository, `tests/golden/<day>_<symbol>/inputs/`:

| Fixture | Expiry | dte | Expiry day | Chain runs | Stored per-strike runs | In both |
|---|---|---:|---|---:|---:|---:|
| 2026-08-27 NIFTY | 2026-09-01 | 5 | no | 81 | 78 | 78 |
| 2026-08-27 SENSEX | 2026-08-27 | 0 | yes | 81 | 78 | 78 |
| 2026-09-29 NIFTY | 2026-09-29 | 0 | yes | 81 | 78 | 78 |
| 2026-10-01 SENSEX | 2026-10-01 | 0 | yes | 81 | 77 | 77 |
| 2026-10-02 NIFTY | 2026-10-06 | 4 | no | 81 | 1 | 1 |
| 2026-10-02 SENSEX | 2026-10-08 | 6 | no | 81 | 1 | 1 |
| **Total** | | | | **486** | **313** | **313** |

Counts, expiries and dte are the engine's, from counting run ids and reading header fields. They are asserted at the start of the run (section 9).

- Chain file `ocs.csv.gz`: one row per leg, columns `id, ts, symbol, expiry_date, spot, strike, option_type, ltp, bid, ask, oi, oi_change, volume, iv, delta, gamma, theta, vega, raw, created_at, run_id`.
- Stored per-strike file `gex_strike.csv.gz`: columns `id, run_id, symbol, ts, expiry_date, dte, strike, spot, oi_call, oi_put, gex_cr, created_at, gamma_call, gamma_put`.
- Each fixture folder carries `MANIFEST.sha256`. Every input file is verified against it before it is read.

Headers and folder layout were confirmed by the pin lane on 25 Nov against `main` at `934fe44`. No data value was read.

## 5. The independent implementation

- Written by the pin lane from the text in section 3 only.
- Frozen, with its self-test, before the pin lane opens `gamma_v2.py` or any file the engine writes for V2. Its sha256 is recorded in the result.
- Python standard library only. Distance tests in exact decimal arithmetic on the values as given in the files.
- It is not run on the fixtures before the comparison.

## 6. Self-test, before the freeze of the implementation

Invented cases, each with a hand-computed expected result, covering at least:

1. Both legs with gamma, inside the band.
2. Call only; put only; neither.
3. A leg with gamma zero, a leg with gamma negative, a leg with gamma missing.
4. A leg with open interest and no gamma, the other leg with gamma (its open interest must count).
5. Guard removes one leg; guard removes both legs (strike stays in the map at exactly 0).
6. Gamma exactly 5e-5 beyond 5 % (not removed); gamma just above (removed).
7. A strike exactly on the 5 % edge (in band, guard does not act); one tick beyond.
8. Call open interest equal to put open interest (net exactly 0, in the map, counted in n_zero).
9. A strike with open interest zero on both legs (no output row).
10. More than one row on a leg (largest positive gamma, open interest summed).
11. A run with two expiries (error, no output); a run with two spot values (error, no output).
12. Empty map; empty band set (None and 0 as the rule states).
13. Run figures on a small hand-worked map: net, net top share, band total, gross top share, gross HHI.
14. The stored-row build giving the same result as the chain build on the same invented data.

Deliberately broken versions of the implementation, each of which must be caught by at least one case:

- M1 guard applied after averaging.
- M2 a missing gamma averaged in as zero.
- M3 put sign not negated in net.
- M4 negative vendor gamma used as given.
- M5 band test strict (<) instead of ≤.
- M6 guard test ≥ instead of >.
- M7 duplicate leg rows: gammas summed, or first row taken.
- M8 membership judged after the guard.
- M9 gross top share and HHI taken over the whole map.
- M10 distance tests in floating point (must differ on the edge case).
- M11 open interest on a no-gamma leg dropped.

The self-test must pass in full, and every broken version must fail, before the implementation is frozen.

## 7. The comparison

**V-2a, old outputs untouched.**
- `git diff 934fe44 <engine commit> -- merdian_compute/gamma.py` is empty.
- No other pre-existing file under `merdian_compute/` is changed by the engine commit.
- The repository's 313-row contract test passes unchanged at the engine commit.

**V-2b, new code equals the rule.** On all 486 chain runs, the engine's `build_v2_strike_rows` and `summarise_v2_run` against the independent implementation:

| Field | Agreement required |
|---|---|
| Set of strikes with an output row | exact |
| oi_call, oi_put | exact |
| in_map, in_band, gamma_legs | exact |
| gamma_strike | 1e-12 relative; None must match None |
| net_cr, gross_cr per strike | 1e-6 + 1e-9·\|v\| |
| run net_cr | 0.01 |
| run gross_band_cr | 0.01 |
| net_top_share, gross_top_share, gross_hhi | 1e-9; None must match None |
| n_map, n_zero | exact |
| Error runs (no output) | same runs on both sides |

**V-2c, chain build equals stored-row build.** On the 313 runs present in both files, the chain-built rows against the stored-row-built rows, same fields and tolerances, for the engine's pair of functions and for the independent pair.

## 8. Verdict

- **PASS:** V-2a, V-2b and V-2c all hold with no exception.
- **FAIL:** any difference in membership, flags or labels, or any value outside tolerance, in any part. One exception is a fail.

V-2c failing while V-2b passes is reported as a finding about the stored leg gammas (the open "precision provenance" item), and is still a fail of this check.

A mismatch is reported with fixture, run id, strike, field and both values. It is not explained away.

## 9. Reported whatever the verdict

- Engine commit hash; sha256 of the independent implementation and its self-test; manifest verification result per fixture.
- Run counts found against the table in section 4. If they are not 486 and 313 by fixture as listed, the check stops before any comparison.
- Counts over the 486 runs: strikes by gamma_legs (both, call_only, put_only, none); legs removed by the guard; strikes in the map with net exactly 0; legs with more than one row; strikes exactly on the 5 % edge; error runs.
- Any branch with a count of zero is named as covered by the self-test only. Known in advance: duplicate leg rows, multi-expiry runs, multi-spot runs.
- Expiry-day skew: 3 of 6 fixture days; 233 of the 313 V-2c runs. No fixture has dte 1, 2 or 3.

## 10. Conduct

- One look. Neither side edits its implementation after the comparison is seen, except under a new version and a new freeze.
- The engine runs nothing on the fixtures beyond its own self-test until the pin lane confirms its freeze.
- Build and self-test may be done in the pin lane's own workspace from the public repository. The recorded run is one command in the pin Claude Code session on the box, outside 08:30 to 15:40 IST, under `ulimit -v`, with `python3 -B`, in a folder under `docs/research/pin_proof/`. Its output is what the operator pastes as evidence.
- No database query, no vendor call, no production tree, no secret read.

## 11. What this check does not establish

- That the new figures are more accurate than the old.
- How much the new figures differ from the old on stored history.
- Agreement with the 60-day audit. That is a second check with its own pre-registration, after this one passes.
- Anything about a flip, a regime label, dealer positioning, or price behaviour.
- Behaviour on days with dte 1 to 3, beyond what the rule's arithmetic implies.

## 12. Changes after freeze

Any change to sections 3, 6, 7 or 8 voids this pre-registration and requires a new one, approved by the operator before any comparison is run.
