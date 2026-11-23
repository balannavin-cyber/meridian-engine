# Part B0 — code read: how the own-solved history was produced

Read-only. No database access in this section. `backfill_hist_greeks.py` and
`core/bs_engine.py` in the engine tree `/home/ssm-user/meridian-engine`.

`hist_option_greeks_1m` is a **sidecar**: the vendor table `hist_option_bars_1m` is
never written by this script (`:6-7`), and its own greek columns (`iv`, `delta`,
`gamma`, `theta`, `vega`, `heston_*`) are left as the vendor delivered them.

## Underlying price, and where it comes from

`hist_spot_bars_1m.close` at **the same `bar_ts`** as the option bar, fetched a whole
day at a time (`:412-417`, `spot_map_for_date`) and passed in as `spot_cache`:

```
412 def spot_map_for_date(iid, d):  # spot-cache v1
414     rows = get("hist_spot_bars_1m",
415                {"select": "bar_ts,close", "instrument_id": f"eq.{iid}",
416                 "trade_date": f"eq.{d}", "order": "bar_ts.asc"})
417     return {r["bar_ts"]: float(r["close"]) for r in rows}
```

```
266         if raw_bts not in spot_cache:
267             return None, None, None
268         spot = spot_cache[raw_bts]
```

**A minute with no spot bar yields no greeks rows at all** (`:266-267` returns before
any solve). The fallback path when no cache is passed reads the same relation one bar at
a time (`:270-274`).

## Rate, and whether the forward is spot grown at that rate or taken from the market

Flat **`R_FLAT = 0.065`** (`:47`), passed as `r` into the Black-Scholes functions
(`:301-302`). The forward is therefore **spot grown at 6.5 %**, implicit in `d1`:

```
109     d1[ok] = (np.log(S / K[ok]) + (r + 0.5 * sig[ok] * sig[ok]) * T) / (sig[ok] * sq)
```

**No market forward is read.** `core/bs_engine.py:77-84` provides
`basis_implied_r(futures, spot, T) = ln(F/S)/T` for exactly this purpose and
`backfill_hist_greeks.py` **does not call it** — it does not import `core.bs_engine` at
all, carrying its own vectorised copy instead. So the futures basis is available and
unused, and the solved IV absorbs whatever the true carry was.

This is the one input that bears directly on B3: a wrong `r` shifts a call's and a put's
solved IV in *opposite* directions at the same strike, because the call is helped and the
put hurt by the same forward error. A call/put gamma ratio away from 1 is the visible
consequence.

## Time to expiry

Calendar days over 365 (`:289-290`):

```
289     dte = (datetime.fromisoformat(expiry).date() - datetime.fromisoformat(d).date()).days
290     T = dte / 365.0
```

Whole days only — **`T` does not decay intraday**, so 10:00 and 15:00 on the same day are
solved with the identical `T`. `EXPIRY_T_FLOOR_MIN = 5` is declared at `:57` and **never
referenced anywhere in the file** (dead constant). `bs_engine.py:17` states the same
calendar-days/365 convention.

## Which price is solved

**`close`**, never a mid (`:261` selects it, `:295` builds the array):

```
286     chain = [r for r in orows if r.get("expiry_date") == expiry and float(r.get("close") or 0) > 0]
295     P = np.array([float(r["close"]) for r in chain])
```

`hist_option_bars_1m` carries no bid/ask columns, so a mid was not an option.

## Every rule that rejects or skips a leg, and what it writes

| # | rule | line | written as |
|---|---|---|---|
| 1 | no option bars at this `bar_ts` | `:259-262` | **no row** |
| 2 | `bar_ts` absent from the spot cache | `:266-267` | **no row** |
| 3 | no expiry on or after the trade date | `:277-279` | **no row** |
| 4 | **expiry == trade date (0-DTE)** | `:284-285` | **whole DAY skipped** — returns `"SKIP_EXPIRY"`, the day's loop `break`s (`:436-438`) and logs `SKIPPED_EXPIRY` (`:446`) |
| 5 | leg's `close` is NULL or ≤ 0 | `:286` | **no row** |
| 6 | fewer than 6 legs on the front expiry | `:287-288` | **no row** |
| 7 | `T <= 0` | `:291-292` | **no row** |
| 8 | **bisection found no bracket** (`flo*fhi > 0`) | `:128-130`, `:152` | **row written, `iv` NULL and `gamma` NULL** (`:311-312`) |

Only rule 8 produces a row. Everything else produces **absence**, which is why B2 must
count "no greeks row" separately from "gamma NULL" — they are different failures.

```
311             "iv": None if np.isnan(sig[i]) else round(float(sig[i]), 6),
312             "gamma": None if np.isnan(gamma[i]) else float(gamma[i]),
```

`iv` is rounded to 6 dp; `gamma` is stored at full float precision. Note rule 8's
consequence: `gamma` is NULL **exactly** when `iv` is NULL (`:303` forces the pairing),
so the two columns cannot disagree about whether a leg solved.

**The deep-ITM guard is NOT applied to the stored rows.** `signed_gex_vec` (`:158-166`)
runs only on the aggregate strike map used to validate against live `gamma_metrics`
(`:316-318`), after the sidecar rows have already been built at `:306-314`. So
`hist_option_greeks_1m.gamma` contains the raw solve, with no 5 %/5e-5 rejection — unlike
`gex_strike_snapshots`, where A1(b)/(d) showed the guard zeroing `gex_cr`. **The two
stores are not comparable leg-for-leg without accounting for this.**

## Which expiries are solved

**The front expiry only**, defined as `min(expiry_date >= trade_date)`:

```
277     exps = [r["expiry_date"] for r in orows if r.get("expiry_date") and r["expiry_date"] >= d]
280     expiry = min(exps)
286     chain = [r for r in orows if r.get("expiry_date") == expiry and ...]
```

So every row in `hist_option_greeks_1m` is a front-expiry row **by construction**, and a
`WHERE expiry_date = <front>` filter on that table is documentation rather than a
restriction. Combined with rule 4, **expiry days are absent entirely** — the history has
no 0-DTE coverage, by design, on the stated ground that 0-DTE flat-vol net GEX is
"numerically unreconstructible intraday" (`:281-283`).

## One unasserted equivalence, carried forward from A1(b)

The file's header claims its semantics are "reproduced VERBATIM from
`measure_rate_sensitivity.py`" and validated at "sign 99 % / magnitude 0.96x /
sign-regime 95 %" (`:9-14`), and `:12-14` says the scalar bisection "is the equivalence
reference, not the production solver". Both claims are **prose in a docstring**. The
`--validate` gate at `:327-372` re-runs the vectorised solver against live `gamma_metrics`
and prints the table, but it is a **manual** entrypoint: nothing in the write path calls
it, and `run_backfill` (`:420-463`) proceeds whether or not it was ever run. Rule 0
clause 4 applies — a parity claim between two implementations is asserted only by a test
that compares them.
