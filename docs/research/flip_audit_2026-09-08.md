# `gamma_metrics.flip_level` — end-to-end audit

**Date measured:** 2026-09-08 · **Scope:** construction, population, consumers, price behaviour
**Access:** PostgREST service-role only. No `psql`, no DB password, no arbitrary-SQL RPC.

Every number below names the query or file that produced it. Where a count is zero it is
written as zero. No fixes, backfills or recommendations appear anywhere in this document.

---

## PART A — construction

Source: `/home/ssm-user/meridian-engine/compute_gamma_metrics_local.py`, read at commit
`83818e6`. Line numbers cited are from that file.

### What feeds the computation

`flip_level` is computed once per run at line 949, from a single argument pair:

```
L946  strike_map = build_strike_exposure_map(option_rows, spot)
L949  flip_level = compute_flip_level(strike_map, spot)
```

`strike_map` is `{strike: signed_GEX_in_Crore}`, summed over both option types at that strike.
Two filters run upstream of it, and both discard a large share of the chain:

- **`filter_usable_option_rows` (L210)** keeps only rows where `gamma != 0.0 and oi > 0.0`.
- **`signed_gamma_exposure` (L114–133)** returns `0.0` for any row where `gamma == 0`,
  `oi <= 0`, or `spot <= 0`; and — the TD-NEW-2 Part A guard at L128–130 — returns `0.0` for
  any strike more than 5% from spot whose `|gamma| > 5e-5`. Surviving rows become
  `gamma * oi * spot² / 1e7`, negated for `PE`.

Measured on four real chains (`GET /option_chain_snapshots` and
`/historical_option_chain_snapshots` for one `run_id`, then the production functions re-run
in-process):

| symbol | date | raw chain rows | rows surviving `filter_usable_option_rows` | distinct strikes in `strike_map` |
|---|---|---:|---:|---:|
| NIFTY | 2026-09-07 | 454 | 113 | 87 |
| NIFTY | 2026-04-21 | 502 | 112 | 83 |
| SENSEX | 2026-09-07 | 340 | 160 | 122 |
| SENSEX | 2026-04-21 | 494 | 187 | 129 |

### The two branches

`compute_flip_level` (L338–436) selects a branch on the sign of `net_gex`, where
`net_gex = sum(strike_map.values())` (L386).

**LONG gamma, `net_gex >= 0` — cumulative walk from ATM (L393–436).**
It first builds a running cumulative sum of signed GEX from the *lowest* strike upward, so
`cum[i]` is the total exposure of every strike at or below `strikes[i]`. It locates the ATM
index (nearest strike to spot, L399) and then walks **outward in both directions** from that
index, looking for the first sign change in the *cumulative* series — downward at L402–416,
upward at L418–432. Each direction contributes at most one candidate and then `break`s. The
returned value is whichever candidate is nearer spot (L436). Crossings are linearly
interpolated between the two bracketing strikes.

**SHORT gamma, `net_gex < 0` — per-strike sign boundary (L303–335, called at L390).**
This does not use a cumulative sum at all. It looks at each strike's **own** signed GEX and
finds every point where consecutive significant strikes change sign. Unlike the LONG branch it
collects *all* such crossings across the whole chain, then returns the one nearest spot (L335).

The docstring at L304–311 states the reason for the split: under negative net gamma the
cumulative series never crosses zero near spot — it is negative throughout — so the cumulative
walk falls through to a deep-tail level. The recorded case is SENSEX 2026-07-01, cumulative
result ~71,500 against spot ~76,900.

**Legacy path, `spot is None or spot <= 0` (L364–384).** A third behaviour, preserved for
callers that pass no spot: a bottom-up cumulative walk returning the **first** zero-crossing
found from the lowest strike upward, with no reference to spot at all. L355 records that
production passes spot, so this path is not taken by the writer.

### What `_FLIP_DOMINANCE_EPS_FRAC` excludes

`_FLIP_DOMINANCE_EPS_FRAC = 0.01` (L300). Inside the SHORT branch only (L316–317), it drops
every strike whose `|signed GEX|` is below 1% of the single largest `|signed GEX|` in that
chain, before any sign-change search runs. The comment at L297–299 states the purpose: to stop
one tiny opposite-sign strike from creating a false sign boundary.

Measured on the same four chains — the floor removes between 29% and 63% of the strikes that
reached `strike_map`:

| symbol | date | strikes in map | clear the 1% floor | excluded by the floor | max abs GEX (Cr) | resulting eps (Cr) |
|---|---|---:|---:|---:|---:|---:|
| NIFTY | 2026-09-07 | 87 | 35 | **52** | 1,467,142 | 14,671 |
| NIFTY | 2026-04-21 | 83 | 33 | **50** | 1,012,997 | 10,130 |
| SENSEX | 2026-09-07 | 122 | 66 | **56** | 96,819 | 968 |
| SENSEX | 2026-04-21 | 129 | 91 | **38** | 45,770 | 458 |

The floor is relative to the peak strike of that chain, so it moves run to run. Strikes with
exactly `0.0` GEX: zero on all four chains measured.

### When the function returns NULL

Enumerated from the code paths, all of which return `None`:

| # | condition | line |
|---|---|---|
| 1 | `strike_map` is empty | L357–358 |
| 2 | fewer than 2 distinct strikes | L361–362 |
| 3 | legacy path, no cumulative zero-crossing anywhere in the chain | L384 |
| 4 | legacy path, a crossing exists but the interpolation denominator is 0 | L380–381 |
| 5 | SHORT branch, every strike has `\|GEX\| == 0` | L314–315 |
| 6 | SHORT branch, fewer than 2 strikes clear the 1% dominance floor | L318–319 |
| 7 | SHORT branch, no sign change among the surviving strikes | L333–334 |
| 8 | LONG branch, no cumulative sign change in either direction from ATM | L434–435 |

A NULL propagates: L951–956 sets `flip_distance` and `flip_distance_pct` to `None`;
`determine_gamma_zone` (L542–544) returns `None`; `determine_regime` (L536–538) returns the
string `"NO_FLIP"` rather than `LONG_GAMMA`/`SHORT_GAMMA`.

### Derived fields

```
L955  flip_distance     = spot - flip_level          # signed, positive when flip is below spot
L956  flip_distance_pct = abs(flip_distance)/spot*100  # unsigned
L958  gamma_zone        = determine_gamma_zone(flip_distance_pct)
```

`gamma_zone` thresholds (L542–549): `< 0.5` → `HIGH_GAMMA`, `< 1.5` → `MID_GAMMA`, else
`LOW_GAMMA`. Because `flip_distance_pct` is an absolute value, `gamma_zone` cannot distinguish
a flip above spot from one below.

### Can the two branches return levels on opposite sides of spot?

**Yes, and they do on real chains.** Only one branch executes per run, so this was tested by
re-running the production functions in-process over the same `strike_map` and forcing each
branch. Read-only; nothing was written.

| symbol | date | spot | net_gex (Cr) | production | LONG branch | SHORT branch | legacy path |
|---|---|---:|---:|---:|---:|---:|---:|
| NIFTY | 2026-09-04 | 23,873 | +2,208,813 | 24,071 | 24,071 (**above**, 0.83%) | 23,873 (**below**, 0.00%) | 24,071 |
| NIFTY | 2026-09-07 | 23,898 | −1,984,901 | 23,979 | None | 23,979 (above, 0.34%) | None |
| NIFTY | 2026-06-02 | 23,256 | −2,763,525 | 23,430 | None | 23,430 (above, 0.75%) | None |
| NIFTY | 2026-04-21 | 24,434 | +2,070,596 | 24,480 | 24,480 (**above**, 0.19%) | 24,343 (**below**, 0.37%) | 24,480 |
| SENSEX | 2026-09-04 | 76,153 | −64,579 | 76,589 | None | 76,589 (above, 0.57%) | None |
| SENSEX | 2026-09-07 | 76,515 | −314,580 | 76,870 | None | 76,870 (above, 0.46%) | None |
| SENSEX | 2026-06-02 | 73,835 | −202,487 | 74,461 | None | 74,461 (above, 0.85%) | None |
| SENSEX | 2026-04-21 | 78,819 | +82,510 | 80,927 | 80,927 (**above**, 2.67%) | 78,515 (**below**, 0.39%) | 80,927 |

Three of the eight chains put the two branches on opposite sides of spot. On SENSEX 2026-04-21
they are **2,412 index points apart** — the LONG branch returns a level 2.67% above spot while
the SHORT branch returns one 0.39% below it. Which of the two is written depends entirely on
the sign of `net_gex`, a quantity that can pass through zero between consecutive five-minute
runs.

Two further observations from the same table, stated as measured:

- On all four chains where `net_gex < 0`, the LONG branch returns `None` — there is no
  cumulative sign change in either direction from ATM. This is the condition the S63 docstring
  describes.
- On NIFTY 2026-09-04 the SHORT branch returns 23,873.0, which equals the spot passed to it to
  the displayed precision (0.00% away).
- On all four chains where the LONG branch returns a value, the legacy bottom-up path returns
  the identical number.

---

## PART B — population and stability

### Scope of the table

```
GET /gamma_metrics?select=ts&order=ts.asc&limit=1   -> 2026-06-09T10:55:05.326819+00:00
GET /gamma_metrics?select=ts&order=ts.desc&limit=1  -> 2026-09-08T05:50:06.189303+00:00
```

`gamma_metrics` holds three months. Months were probed from 2026-05 to 2026-10 — one either
side of that range — and 2026-05 and 2026-10 return zero rows for both symbols, so the range
is not an artefact of where the probe started.

The sibling table `hist_gamma_metrics` carries the earlier period and also has a `flip_level`
column, measured for scope only:

```
GET /hist_gamma_metrics?select=trade_date&order=trade_date.asc|desc&limit=1
   -> 2025-04-01 .. 2026-03-30
GET /hist_gamma_metrics?select=*&limit=0            Prefer: count=exact -> */182461
GET /hist_gamma_metrics?select=*&limit=0&flip_level=not.is.null   count=exact -> */128884
```

Everything below is `gamma_metrics`, the table named in the audit. `hist_gamma_metrics` was
not analysed further.

### Method note

Presence of a non-null `flip_level` in each month was established with a scoped `limit=1`
probe returning real rows or a real empty list, never with `count=planned`. All counts below
are `count=exact`; none fell back to `planned`. **Unresolved cells: zero** — the run asserts
`res['unresolved'] == []` before any aggregation, and it printed `[]`.

### Rows and non-null `flip_level`, per month per symbol

```
GET /gamma_metrics?select=*&limit=0&ts=gte.<month>&ts=lt.<next>&symbol=eq.<sym>
    Prefer: count=exact                                    -> rows
  + &flip_level=not.is.null                                -> non-null flip_level
```

The `(flip_level - spot)/spot*100` range was computed client-side by paging every non-null
row of the month (`order=ts.asc`, `limit=1000`, offset paging), so `n` below is the exact
number of rows the min/max was taken over.

| month | symbol | rows | non-null flip_level | null | n for pct | min (flip−spot)/spot % | max % |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026-05 | NIFTY | 0 | 0 | 0 | 0 | — | — |
| 2026-05 | SENSEX | 0 | 0 | 0 | 0 | — | — |
| 2026-06 | NIFTY | 837 | 726 | 111 | 726 | -15.66 | 7.96 |
| 2026-06 | SENSEX | 799 | 734 | 65 | 734 | -9.85 | 8.48 |
| 2026-07 | NIFTY | 1,893 | 1,844 | 49 | 1,844 | -1.91 | 6.19 |
| 2026-07 | SENSEX | 1,893 | 1,888 | 5 | 1,888 | -7.21 | 7.66 |
| 2026-08 | NIFTY | 1,709 | 1,709 | 0 | 1,709 | -1.28 | 7.76 |
| 2026-08 | SENSEX | 1,708 | 1,707 | 1 | 1,707 | -2.05 | 6.65 |
| 2026-09 | NIFTY | 448 | 447 | 1 | 447 | -0.36 | 7.97 |
| 2026-09 | SENSEX | 445 | 444 | 1 | 444 | -1.18 | 4.88 |
| 2026-10 | NIFTY | 0 | 0 | 0 | 0 | — | — |
| 2026-10 | SENSEX | 0 | 0 | 0 | 0 | — | — |

Two things are visible in the last two columns. The flip is written **above** spot far more
often than below — every month's maximum is positive and between +4.88% and +8.48% — and the
extremes are large: 2026-06 NIFTY reaches **−15.66%** below spot, which on a ~23,900 index is
roughly 3,700 points.

Null `flip_level` is concentrated in the earliest month. 2026-06 NIFTY: 111 null of 837;
2026-08 NIFTY: zero null of 1,709.

### Within-session stability

66 sessions in `gamma_metrics` were enumerated by day-scoped `limit=1` probe
(2026-06-09 .. 2026-09-08). 20 were sampled evenly across that list. For each, every run of
the session was paged in `ts` order and consecutive non-null `flip_level` values compared.

| session | symbol | runs | runs with non-null flip | distinct flip values | largest jump between consecutive runs | times flip crossed spot | regimes seen |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-06-09 | NIFTY | 1 | 1 | 1 | — | 0 | SHORT_GAMMA |
| 2026-06-09 | SENSEX | 0 | 0 | 0 | — | 0 | — |
| 2026-06-12 | NIFTY | 16 | 10 | 10 | 53 | 0 | LONG_GAMMA, NO_FLIP |
| 2026-06-12 | SENSEX | 16 | 13 | 13 | 8,486 | 1 | LONG_GAMMA, NO_FLIP, SHORT_GAMMA |
| 2026-06-18 | NIFTY | 83 | 83 | 77 | 242 | 2 | LONG_GAMMA |
| 2026-06-18 | SENSEX | 83 | 71 | 63 | 6,240 | 15 | LONG_GAMMA, NO_FLIP, SHORT_GAMMA |
| 2026-06-23 | NIFTY | 83 | 59 | 54 | 441 | 5 | LONG_GAMMA, NO_FLIP |
| 2026-06-23 | SENSEX | 83 | 83 | 77 | 7,300 | 2 | LONG_GAMMA, SHORT_GAMMA |
| 2026-06-29 | NIFTY | 84 | 66 | 66 | 308 | 0 | LONG_GAMMA, NO_FLIP |
| 2026-06-29 | SENSEX | 84 | 74 | 74 | 1,288 | 0 | LONG_GAMMA, NO_FLIP |
| 2026-07-02 | NIFTY | 83 | 79 | 75 | 780 | 3 | LONG_GAMMA, NO_FLIP, SHORT_GAMMA |
| 2026-07-02 | SENSEX | 83 | 78 | 72 | 6,254 | 18 | LONG_GAMMA, NO_FLIP, SHORT_GAMMA |
| 2026-07-08 | NIFTY | 83 | 83 | 80 | 172 | 2 | LONG_GAMMA |
| 2026-07-08 | SENSEX | 84 | 84 | 78 | 608 | 2 | LONG_GAMMA, SHORT_GAMMA |
| 2026-07-13 | NIFTY | 82 | 82 | 79 | 568 | 24 | LONG_GAMMA, SHORT_GAMMA |
| 2026-07-13 | SENSEX | 82 | 82 | 76 | 2,547 | 18 | LONG_GAMMA, SHORT_GAMMA |
| 2026-07-16 | NIFTY | 83 | 83 | 79 | 73 | 0 | LONG_GAMMA |
| 2026-07-16 | SENSEX | 83 | 83 | 77 | 1,313 | 19 | LONG_GAMMA, SHORT_GAMMA |
| 2026-07-22 | NIFTY | 83 | 83 | 79 | 63 | 0 | LONG_GAMMA |
| 2026-07-22 | SENSEX | 83 | 83 | 77 | 368 | 2 | LONG_GAMMA |
| 2026-07-27 | NIFTY | 82 | 82 | 77 | 1,191 | 4 | LONG_GAMMA, SHORT_GAMMA |
| 2026-07-27 | SENSEX | 83 | 83 | 76 | 3,112 | 2 | LONG_GAMMA, SHORT_GAMMA |
| 2026-07-31 | NIFTY | 68 | 68 | 64 | 711 | 4 | LONG_GAMMA, SHORT_GAMMA |
| 2026-07-31 | SENSEX | 68 | 68 | 62 | 2,822 | 5 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-05 | NIFTY | 82 | 82 | 78 | 139 | 2 | LONG_GAMMA |
| 2026-08-05 | SENSEX | 83 | 83 | 79 | 1,063 | 2 | LONG_GAMMA |
| 2026-08-10 | NIFTY | 82 | 82 | 78 | 396 | 2 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-10 | SENSEX | 82 | 82 | 78 | 2,308 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-14 | NIFTY | 84 | 84 | 79 | 351 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-14 | SENSEX | 83 | 83 | 78 | 5,101 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-19 | NIFTY | 83 | 83 | 78 | 1,330 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-19 | SENSEX | 83 | 83 | 78 | 2,806 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-25 | NIFTY | 83 | 83 | 77 | 703 | 2 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-25 | SENSEX | 83 | 83 | 78 | 2,488 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-28 | NIFTY | 83 | 83 | 77 | 959 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-08-28 | SENSEX | 83 | 83 | 77 | 4,724 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-09-03 | NIFTY | 83 | 83 | 79 | 947 | 0 | LONG_GAMMA, SHORT_GAMMA |
| 2026-09-03 | SENSEX | 83 | 82 | 76 | 2,234 | 2 | LONG_GAMMA, NO_FLIP, SHORT_GAMMA |
| 2026-09-08 | NIFTY | 35 | 35 | 30 | 764 | 2 | LONG_GAMMA, SHORT_GAMMA |
| 2026-09-08 | SENSEX | 35 | 35 | 30 | 232 | 0 | LONG_GAMMA |

### Summary of the 19 sampled sessions with 10 or more non-null runs

(2026-06-09 is excluded from these summaries: it holds 1 run for NIFTY and zero rows for
SENSEX, so a jump between consecutive runs does not exist for it.)

| | NIFTY | SENSEX |
|---|---|---|
| sessions summarised | 19 | 19 |
| distinct flip values ÷ non-null runs — median | 0.949 | 0.928 |
| distinct flip values ÷ non-null runs — range | 0.857 – 1.000 | 0.857 – 1.000 |
| sessions where every run produced a different flip value | 2 | 2 |
| per-session largest jump — median | 441 pts | 2,547 pts |
| per-session largest jump — range | 53 – 1,330 pts | 232 – 8,486 pts |
| times per session the flip crossed from one side of spot to the other — median | 2 | 2 |
| the same — maximum | 24 of 82 runs (2026-07-13) | 19 of 83 runs (2026-07-16) |
| sessions with zero side changes | 8 | 7 |

Nearly every run produces a value not seen before in that session — the median ratio of
distinct values to non-null runs is 0.95 (NIFTY) and 0.93 (SENSEX), and on two sessions per
symbol it is exactly 1.000.

### Jump sizes restricted to genuinely adjacent runs

The per-session maxima above compare consecutive **rows**, and some pairs are not five
minutes apart — the largest SENSEX figure in that column, 8,486 points on 2026-06-12, spans
07:45 to 08:30, a 45-minute gap on a day with only 16 runs. Recomputing over only those pairs
whose timestamps are **6 minutes or less** apart removes that confound:

| | NIFTY | SENSEX |
|---|---:|---:|
| adjacent run-pairs measured | 1,352 | 1,379 |
| median jump | **10 pts** | **41 pts** |
| 90th percentile jump | 97 pts | 449 pts |
| largest jump | **1,330 pts** | **7,300 pts** |

The two largest, both across a true five-minute step:

```
NIFTY  2026-08-19  04:40:06 -> 04:45:06  (5.0 min)  flip 25,499.8 -> 24,170.2
SENSEX 2026-06-23  03:40:09 -> 03:45:07  (5.0 min)  flip 78,725.0 -> 71,424.7
```

So the typical five-minute step is small — 10 points on NIFTY, 41 on SENSEX — and the tail is
not: the largest single five-minute move is 1,330 points on NIFTY and 7,300 on SENSEX. On the
SENSEX case the level moved roughly 9.5% of the index in one cycle.

`regime` changes within a session as well. Of the 20 sampled sessions, both `LONG_GAMMA` and
`SHORT_GAMMA` appear inside the same session on **11** NIFTY sessions and **15** SENSEX
sessions; `NO_FLIP` appears on **4** NIFTY and **5** SENSEX sessions. Because the branch is
selected on the sign of `net_gex`, each `LONG_GAMMA`↔`SHORT_GAMMA` change inside a session is
also a change of which of the two Part A algorithms produced the number.

