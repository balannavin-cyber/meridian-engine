# Part A1 — code read: where a blank gamma can enter

Read-only. No database access in this section. Paths are relative to the engine tree
`/home/ssm-user/meridian-engine` (Rule 24: this session is rooted in `~/meridian-cc`;
the engine tree was read, never written).

**Naming correction to the prompt.** `compute_gamma_metrics_local.py` contains no
`signed_gex_vec`. Its scalar equivalent is `signed_gamma_exposure`, and since S101 it
does not live in that file either: it was moved byte-identical to
`merdian_compute/gamma.py` and re-imported under the same name
(`compute_gamma_metrics_local.py:26-58`). `signed_gex_vec` is the **vectorised twin**
in `backfill_hist_greeks.py:158-166`, which belongs to Part B. Both are read below.

---

## (a) How vendor per-leg gamma and iv reach `option_chain_snapshots`

`ingest_option_chain_local.py`, in `extract_option_rows`:

```
282            greeks = option_raw.get("greeks") or {}
...
306                "iv": to_float(option_raw.get("implied_volatility")),
308                "gamma": to_float(greeks.get("gamma")),
```

Two different sources: **`iv` is a top-level vendor key**, `gamma` is nested under
`greeks`. The coercion is `to_float` (`:174-180`):

```
174 def to_float(value: Any) -> float | None:
175     if value is None:
176         return None
177     try:
178         return float(value)
179     except Exception:
180         return None
```

So at the ingest boundary:

| vendor state | stored in `option_chain_snapshots.gamma` |
|---|---|
| key missing, or JSON `null` | `NULL` |
| non-numeric / unparseable | `NULL` |
| literal `0` | `0` — **passed through, not nulled** |
| a number | that number |

There is **no** coercion of `0` to `NULL` and none of `NULL` to `0`. A missing
`greeks` object degrades to `{}` (`:282`), which makes `greeks.get("gamma")` return
`None` and so stores `NULL` — a distinct outcome from a vendor-sent `0`.

A leg absent from the vendor payload gets **no row at all** (`:278-280`: the `ce` /
`pe` block is skipped when it is not a dict), so "leg missing" and "leg present with
blank gamma" are distinguishable in the stored data.

Rows are inserted unmodified at `:551`.

## (b) The deep-ITM guard — exact condition and effect

`merdian_compute/gamma.py:36-55`:

```
 42     if gamma == 0.0 or oi <= 0.0 or spot <= 0.0:
 43         return 0.0
...
 50     if strike > 0 and abs(strike - spot) / spot > 0.05:
 51         if abs(gamma) > 5e-5:
 52             return 0.0
 54     base = gamma * oi * (spot ** 2) / 1e7
 55     return -base if option_type == "PE" else base
```

The guard fires when the strike is **more than 5 % from spot** *and* the vendor's
`|gamma| > 5e-5`. Its effect is confined to the **return value of this function** — the
leg's contribution to `gex_cr` becomes `0.0`. It does **not** alter, null, or flag the
leg anywhere else. Note `to_float` here is `merdian_compute/gamma.py:17-23`, whose
default is **`0.0`**, not `None`: a chain `NULL` gamma arrives at `:42` as `0.0` and
returns at `:43`.

The vectorised twin, `backfill_hist_greeks.py:158-166`, uses the same three constants
(`ITM_DIST = 0.05`, `ITM_GAMMA = 5e-5`, `CR_SCALE = 1e7`, `:54-56`) and adds an explicit
`~np.isnan(gamma)` term. **Their equivalence is asserted here only by reading, and
Rule 0 clause 4 says that is not an assertion.** No test in the tree compares the two
on shared inputs; the file's own header claims equivalence to a third implementation
(`measure_rate_sensitivity.py`) in prose at `:9-14`.

## (c) The exact rule that makes `gamma_call` / `gamma_put` NULL

`merdian_compute/gamma.py`, `build_gss_rows` (`:674-752`) — this is the only writer of
those two columns:

```
711         gamma_raw = to_float(row.get("gamma"))
...
719             "gamma_call": None,
720             "gamma_put": None,
...
725             if bucket["gamma_call"] is None and gamma_raw != 0.0:
726                 bucket["gamma_call"] = gamma_raw
...
729             if bucket["gamma_put"] is None and gamma_raw != 0.0:
730                 bucket["gamma_put"] = gamma_raw
```

The bucket initialises to `None` and is overwritten **only** when `gamma_raw != 0.0`.
Because `to_float` defaults to `0.0` (`:17-23`), the rule is:

| chain `gamma` | `gex_strike_snapshots.gamma_call` / `_put` |
|---|---|
| `NULL` | `NULL` — via `to_float` → `0.0` → fails `!= 0.0` |
| `0` | `NULL` — fails `!= 0.0` |
| `> 0` | that value |
| leg has no chain row | `NULL` (bucket never touched for that side) |

**Three distinct upstream states collapse to one stored `NULL`.** This is why Stage 1
could observe "NULL, never 0" in `gex_strike_snapshots` (`preconditions.md` C5) — the
column is incapable of holding a 0. It is also independent of which side of spot the
strike sits on: nothing in `build_gss_rows` reads spot when deciding NULL, so the
structured NULL pattern Stage 1 found (`gamma_call` absent below spot) must originate
**upstream of this rule**. A2/A3 test exactly that.

Note the `and bucket[...] is None` clause: **first non-zero leg wins**. With one row per
`(strike, option_type)` per run this never arbitrates, but it is a silent first-write-wins
if a run ever carries a duplicate leg.

## (d) How `gex_cr` treats a NULL or rejected leg

`:722` accumulates `bucket["gex_cr"] += gex_contrib` where `gex_contrib` is
`signed_gamma_exposure(row, spot)` (`:712`). Both a NULL-gamma leg (via `:42-43`) and a
guard-rejected leg (via `:50-52`) contribute exactly `0.0`. So:

- `gex_cr` is a **sum over whichever legs survived**, with absent legs counted as zero
  — the one-legged quantity Stage 1 documents.
- **The asymmetry that matters:** a guard-rejected leg still has its gamma **stored** in
  `gamma_call` / `gamma_put` (the guard is inside `signed_gamma_exposure`, after
  `:711` has already captured `gamma_raw`). So a strike can show two positive stored
  gammas and `gex_cr = 0`. That is a measurable signature, counted in A3/R6.
- `:735-736` drops a strike only when `oi_call = 0 AND oi_put = 0 AND gex_cr = 0.0`, so
  a strike with OI and no usable gamma **is written**, carrying `gex_cr = 0`.

## (e) Is the raw vendor response stored?

**Yes.** `ingest_option_chain_local.py:311`:

```
311                "raw": option_raw,
```

`option_raw` is the vendor's entire per-leg object, and `greeks` is one of its keys
(`:282` reads it from the same object). It lands in `option_chain_snapshots.raw`
(`jsonb`). A4 is therefore measurable from storage alone, with no live capture.

---

## One Rule 0 observation, incidental to this task

`compute_gamma_metrics_local.py:582` declares

```
582         expected_writes={TARGET_TABLE: 1, GSS_TARGET_TABLE: 1},  # ENH-80 (S37) v2
```

`gex_strike_snapshots` receives one row **per strike** — measured here at 142–213 rows
per run (R0 ÷ runs). `_compute_contract_met` tests `actual < expected`
(`core/execution_log.py:297-303`), so this floor of 1 passes on 213 writes and on 1,
and cannot distinguish a full per-strike write from a single-strike write. This is
Rule 0 clause 1's named shape (`{"ict_htf_zones": 1}`), in a second script. Not acted
on in this read-only session; recorded for the register.
