# 70_tests_and_fixtures — every test, fixture and golden file embedding a Γ value (prompt §3 item 7)

`tests/run_offline.sh` has **30 steps as of S103**. Rule 23 binds: no run between 08:30 and 15:40
IST, and always under `( ulimit -v 700000; … )`. **This sweep did not run the suite** (prompt §1
forbids it). Everything below is read from source.

## 1. Steps that assert something about a Γ value

| step | file | what it asserts about Γ | scale assumed |
|---|---|---|---|
| **11/30** | `tests/test_dex_recompute.py` | `CR = 1e7` (`:174`); `base = gamma * oi * (spot ** 2) / CR` (`:351`). Its name says DEX, but **it recomputes the GAMMA formula too**. Tolerance `TOL_CR = 1e-6` (`:175`), checked at `:443`, `:530`, with the failure text at `:532` naming "the /1e7 scaling". | **A**, absolute tolerance in scale-A crore |
| **12/30** | `tests/test_p3a_invariants.py` | **I1** `sum(gex_strike.gex_cr) == gamma_metrics.net_gex`, `abs <= 0.01 Cr` (`:67`). **I2** `gex_cr == independent recompute`, `abs <= 1e-6 + 1e-9*rel` (`:86`), recompute at `:38`. **I4** `gamma_concentration == max\|gex_cr\|/sum\|gex_cr\|`, `abs <= 1e-6` (`:74`). Beliefs are stated at `:6-15` **before** the first run, per rule 0. | **A**, both tolerances absolute |
| **25/30** | `tests/test_merdian_compute_contract.py` | Runs `compute_gamma_core(**prepare_gamma_inputs(...))` against production golden rows; compares `net_gex`, `gamma_concentration`, `flip_level`, … within `rel/abs 1e-9` (`:19`, `:136`). Pins the full signature of `gamma.compute_net_gex`, `determine_regime`, `compute_expansion_probability` (`:71-92`). | **A** |
| **30/30** | `tests/test_gamma_prior_row.py` | S103 / TD-S101-NEW-3,-4 — the gamma writer's prior-row read selects **raw** and is bounded to the IST session. Touches the Γ read path, asserts nothing about the unit. | n/a |
| 2, 3 | `tests/replay/test_replay_seeded.py`, `tests/replay/replay_contracts.py --check` | seeded defects + pinned statuses on golden days. One Γ-token hit in the seeded test; the pinned artefacts are status strings. | n/a |
| 24/30 | `tests/test_merdian_compute_import_purity.py` | `merdian_compute` imports nothing with I/O. Mentions Γ names only as the package's surface. | n/a |

Steps 1, 4–10, 13–23, 26–29 contain no Γ token.

## 2. The mutant that stops firing if the unit line is edited

`tests/test_merdian_compute_contract.py:264`:
```python
("M1 Crore divisor", "gamma.py", "(spot ** 2) / 1e7", "(spot ** 2) / 1.0000001e7", "net_gex"),
```
M1 is a **source-text substitution**: it copies the package, replaces the literal string
`(spot ** 2) / 1e7` with `(spot ** 2) / 1.0000001e7`, and requires the contract test to FAIL.

That anchor is the exact text of `merdian_compute/gamma.py:54`. If that line is edited in any way
— to `* 0.01`, to `/ 1e5`, to a named constant, or merely reformatted — **the substitution matches
nothing, the mutated copy is identical to the original, the contract test passes, and M1 reports
that the mutant did not fail**. Whether that is reported as a mutant failure or silently swallowed
depends on how the harness treats a no-op substitution; either way the check no longer tests the
divisor. This is CLAUDE.md rule 0 clause 1's shape — a check that cannot fail for the reason it
names. Four more mutants in the same list share the anchor-fragility property (M2 flip dominance
floor, M5 result-field order at `:269-270`).

The other direction is sound: step 12's I2 at `:38` recomputes the formula **independently** from
the raw chain rather than matching source text, so it would catch a real change in the computed
value. Its seeded mutant `:132` nudges a `gex_cr` by `+0.05` and requires I1 and I2 to fail —
which works at scale A, where `0.05` exceeds the `0.01` I1 band. **At scale B (`×0.01`) a `+0.05`
nudge is 100× larger relative to the data, so the mutant still fires; but the I1 band of
`0.01 Cr` absolute becomes 100× looser relative to the quantity it bounds.** The tolerance is the
thing that would need re-deriving, not the mutant.

## 3. Golden fixtures that embed Γ values

Six golden days, both symbols. Every one holds Γ values at **scale A**.

| fixture | Γ column | rows (gz lines) |
|---|---|---|
| `tests/golden/2026-08-27_NIFTY/inputs/gex_strike.csv.gz` | `gex_cr` | header `id,run_id,symbol,ts,expiry_date,dte,strike,spot,oi_call,oi_put,gex_cr,created_at,gamma_call,gamma_put` |
| `tests/golden/2026-08-27_SENSEX/inputs/gex_strike.csv.gz` | `gex_cr` | 248 matching lines |
| `tests/golden/2026-09-29_NIFTY/inputs/gex_strike.csv.gz` | `gex_cr` | 48 |
| `tests/golden/2026-10-01_SENSEX/inputs/gex_strike.csv.gz` | `gex_cr` | 211 |
| `tests/golden/2026-10-02_NIFTY/inputs/gex_strike.csv.gz` | `gex_cr` | — |
| `tests/golden/2026-10-02_SENSEX/inputs/gex_strike.csv.gz` | `gex_cr` | — |
| `tests/golden/*/inputs/gamma_metrics.csv.gz` (6) | `net_gex`, `gamma_concentration` | header `id,ts,symbol,expiry_date,spot,net_gex,gamma_concentration,flip_level,…` |
| `tests/golden/*/inputs/ocs.csv.gz` (6) | `gamma` (per-option, the INPUT) | header `…,oi,oi_change,volume,iv,delta,gamma,theta,vega,raw,…` |

These are **production rows exported verbatim**, so they carry whatever the writer stored on
those dates — scale A. Changing the stored unit (ADR-032 D2) would make every one of them a
mixed-era fixture unless re-exported, and steps 11, 12 and 25 all read them.

`2026-10-02` is the Gandhi Jayanti frozen-book day CLAUDE.md records (TD-S89-NEW-1): nominal row
and `ts` counts, `distinct_spot = 1`. It is in the golden set deliberately.

## 4. The golden query that is already on a different convention

`tests/golden/2026-10-01_SENSEX/queries/ladder_replay_1001.sql` — see
`50_outbound_and_constants.md` §2(c). Its stated formula is
`gamma * oi * lot * spot^2 * 0.01 / 1e7`: **per-1 %, times a lot factor**, published as
`gamma_load` / `gex_abs`. It sits in the same golden directory as `gex_strike.csv.gz`, whose
`gex_cr` is per-100 % with no lot factor. Two conventions, one fixture directory. Recorded as
found; which one is intended is not this sweep's call.

## 5. Expected-output files

`tests/replay/expected/{2026-08-27_NIFTY,2026-08-27_SENSEX,2026-09-29_NIFTY,2026-10-01_SENSEX,2026-10-02_NIFTY,2026-10-02_SENSEX}.statuses.csv`
— 76 Γ-token lines each. These are **contract status strings** (per CLAUDE.md ADR-031's one enum),
not Γ magnitudes. A unit change does not move them unless it moves a contract verdict.

`docs/research/s93_priority/p6/expected/dex_standing_book_1001_SENSEX.csv` — written by step 11
itself (`run_offline.sh:76-78` records that step 11 is the one non-read-only step). Δ-type.

## 6. No test anywhere asserts the unit of a Γ size

Measured: of the 30 suite steps, 4 touch a Γ value (§1). Each asserts **internal consistency**
(`sum == net`, `recompute == stored`, `concentration == top-1 share`) — all of which hold under
*any* uniform scale. **Not one asserts that the stored value means "₹ crore per 100 % move",**
and none exercises:
- the `_1pct` wrapper views (no test reads the database at all),
- `generate_pine_overlay.py`'s `/1000` + `"K Cr"` render,
- `crLakh` / `lad` / `lak` and their `1e5` branch,
- `v_dealer_flow_sim`'s `−net_gex × pct`,
- the `queries.ts` alias layer that renames `*_1pct` back to the scale-A names.

Because the invariants are scale-free, **the whole suite would pass unchanged if every Γ value in
the system were multiplied by any constant**, provided it were multiplied consistently. That is
the correct property for an internal-consistency suite; it is stated here because it means the
suite is not the control for a unit change.
