# MR-PIN2 step 3 — STEP 0b/0c conventions, read from code and catalog

Read-only. Engine tree `/home/ssm-user/meridian-engine`; DB through `bin/roq.sh` as
`merdian_ro`. Design v2 FROZEN sha256 `a9d0b7c5…ad612e` (not held by this session).

## Which `bs_engine` functions the backfill calls — **NONE**

`backfill_hist_greeks.py` does **not import `core.bs_engine`** (no `bs_engine` token
anywhere in the file; its only numeric import is `numpy`, `:37`). It carries its own
vectorised copy and solves with:

- IV: `implied_vol_vec(P, spot, K, T, R_FLAT, is_call)` — `:301`, defined `:114-155`.
  Bisection `IV_LO=1e-4, IV_HI=5.0, IV_TOL=1e-3, IV_MX=100` (`:51`), bracket test
  `flo*fhi <= 0` (`:128`), returns `0.5*(lo+hi)` or the tol-hit `mid`; `nan` = no bracket.
- gamma: `bs_gamma_vec(spot, K, T, R_FLAT, sig)` — `:302`, defined `:104-111`;
  `:303` forces `gamma = nan` wherever `sig` is `nan`, so the two columns cannot disagree.
- `norm_cdf`: `scipy.special.erfc` when importable, else `0.5*(1+vectorize(math.erf)(…))`
  (`:74-80`, fallback `:67-71`). **scipy is absent on this box**, so the re-solve here uses
  the `math.erf` fallback. Which path the original write took is unknown; the two differ at
  ~1e-16 relative, far below the G1 tolerances.

`core/bs_engine.py` is the *other* implementation (`implied_vol:55`, `bs_gamma:48`,
`basis_implied_r:77-84`). It is never called by the backfill, so "semantics reproduced
VERBATIM" (`:9-14`) is prose, not an assertion — Rule 0 clause 4. **G1 below is the first
test that actually compares the stored numbers against a re-solve.**

## The four conventions — all four CONFIRMED, none contradicted

| convention | code | status |
|---|---|---|
| spot = `hist_spot_bars_1m.close` at the **same** `bar_ts` | `:265-274`, cache built `:412-417` | CONFIRMED |
| `R_FLAT = 0.065`, flat, no market forward | `:47`, used `:301-302`; `basis_implied_r` never called | CONFIRMED |
| `T` = calendar days / 365, **whole days**, no intraday decay | `:289-290` | CONFIRMED |
| solved price = the bar **close**, never a mid | `:286` filter, `:295` array | CONFIRMED |

Not conventions but binding on the re-solve: front expiry only, `min(expiry_date >= d)`
(`:277-280`); expiry-day minutes return `SKIP_EXPIRY` (`:284-285`); `iv` stored
`round(…, 6)`, `gamma` stored unrounded (`:311-312`); the deep-ITM guard
(`signed_gex_vec`, `:158-166`) runs only on the aggregate, **not** on the stored rows.

## Part B's exact B3 definition (the band, the pairing, the pooling)

From `queries/qB_day.sql.tpl:103-113` and `analyze_partB.py`:

- **Pairing** — self-join of the leg set on `(tname, strike)`, call row to put row, keeping
  only `c.is_call AND c.gamma > 0 AND p.gamma > 0`. Ratio = `c.gamma / p.gamma`
  (`:108`). Strikes where either leg is NULL are absent by construction.
- **Band** — `W1` = `abs(strike - spot)/spot <= 0.01` (within 1 %), `W1_3` = `<= 0.03`
  (`:105-107`). The gate input is `W1` only.
- **Pooling** — the per-day median pools the day's **three minutes' pairs into one list**
  and takes the median of the per-strike ratios; it is not a median of three per-minute
  medians. In-band = median in `[0.95, 1.05]`. Result reproduced as G0: NIFTY 5/12,
  SENSEX 6/12 (`partB_results.md:99-114`).

## 0c — catalog facts

`hist_option_greeks_1m.iv` and `.gamma` are **`numeric` with NULL precision and scale**
(unconstrained — full precision, no storage rounding); `strike` likewise. By contrast
`hist_option_bars_1m.close` is `numeric(10,2)` and its vendor `gamma` is `numeric(12,8)`.
Indexes used below: `uniq_hist_greeks_row (instrument_id, bar_ts, strike, expiry_date,
option_type)`, `hist_option_bars_unique (instrument_id, bar_ts, expiry_date, strike,
option_type)`, `idx_hist_option_chain_snap (instrument_id, trade_date, bar_ts)`,
`idx_hist_spot_ts (instrument_id, bar_ts DESC)`. Instrument ids: NIFTY
`9992f600-51b3-4009-b487-f878692a0bc5`, SENSEX `73a1390a-30c9-46d6-9d3f-5f03c3f5ad71`
(`_q0c.txt`).

**Rule 13 preflight — PASS, no exclusion.** Four ranges in
`public.data_contamination_ranges`; none names `hist_option_greeks_1m`,
`hist_option_bars_1m` or `hist_spot_bars_1m` (`_q0c.txt` C3). The only one overlapping the
2025-04→2026-03 window, `BREADTH-STALE-REF-2026-03-27`, names breadth / signal /
`gamma_metrics` relations. `symbols` NULL = every symbol (S100-J), immaterial here.

## Solver noise floor — IV_TOL = 1e-3

IV_TOL = 1e-3 is a tolerance on the price residual (rupees), not on sigma. The sigma error
it leaves on a leg is about IV_TOL / vega, with vega per unit sigma for that leg. The
earlier figure "about 0.1 vol points" was an advisor error and is withdrawn; no figure is
asserted here. analyze_sens.py computes 100 * IV_TOL / vega (vol points) for every leg in
the pair set at r = 0.065 and reports the median, p90 and max per symbol in gates.md and
results.md. The bisection also stops after IV_MX = 100 halvings of [IV_LO, IV_HI]; report
whether any leg returned at IV_MX rather than at the tolerance. This noise is present
identically before and after. Storage adds iv round(sig, 6) = 1e-4 vol points; gamma is
written from the unrounded sigma.

## Solver used for the re-solve (recorded clarification)

Design v2 (sha256
`a9d0b7c5c3dbfbd1739096a81c138cc7caefc5c094d454d28c3fd9d6ffad612e`) assumed the backfill
calls `core/bs_engine.py`; **it does not**. The design's binding aim is a re-solve with
exactly what the backfill used, so the re-solve uses the backfill's own `norm_cdf`,
`bs_gamma_vec`, `implied_vol_vec` and constants (`IV_LO`, `IV_HI`, `IV_TOL`, `IV_MX`), not
`core/bs_engine.py`. **Recorded by the operator 2026-11-20; no gate or threshold changes;
G1 tests the replication.**

**How they are obtained.** `backfill_hist_greeks.py` is **never imported or executed** — its
module-level code may call `load_dotenv()` (`:40-44`) and its `get()` helper opens HTTP
connections. Instead `extract_bs_copy.py` parses the file with `ast` (`python3 -B`) and
writes the exact `ast.get_source_segment` text of each needed function and constant
assignment into `sens/bs_backfill_copy.py`, with a header citing the source path, its
sha256 and each segment's line range, and a byte-for-byte check of every segment against an
independently re-derived slice of the source. `analyze_sens.py` imports the solver **only**
from `sens/bs_backfill_copy.py`.

Segments extracted, with the reason each is needed: `import numpy as np` (`:37`),
`R_FLAT` (`:47`), `SQRT_2PI` (`:48`), `IV_LO, IV_HI, IV_TOL, IV_MX` (`:51`), `norm_pdf`
(`:83-84`), `bs_price_vec` (`:87-101`), `bs_gamma_vec` (`:104-111`), `implied_vol_vec`
(`:114-155`). Two names beyond the clarification's list are extracted because `norm_cdf`
cannot run without them, and they are named here as required: **`_norm_cdf_np`** (`:67-71`),
the no-scipy fallback body, and the **`try/except` block at `:74-80`**, which is where
`norm_cdf` is *defined* — the definition is not a bare `def`, so the whole block is the
segment. `_norm_cdf_vec` (`:61-64`) is **not** extracted: it is dead code, unreferenced by
any solve path. `signed_gex_vec` (`:158-166`) is **not** extracted: the deep-ITM guard does
not touch the stored rows (`:306-318`).
