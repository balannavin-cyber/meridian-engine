# Brief addendum — M8, M9, M10

Read-only, same rules as `claude_code_brief_srs_exploration.md` §0–§2 (GET-only
`_get()` choke point, per-leg staleness rejection, clock anchors, DTE indexing,
era separation, vol-regime split on every table). Nothing here changes those.

Each of these can independently kill a load-bearing assumption in the
pre-registration, and each is cheaper than M2. Run in the order given.

**Before starting:** report the state of the era-1 re-sweep and the era-2 sweep.
If either is still running or failed, say so — do not start M8 on top of them.

---

## M10 — Constant σ versus constant percent (run first; stage 1 costs nothing)

The pre-reg picks strikes at 1% from spot. At the measured IV terciles
(NIFTY 10.01 / 13.30, SENSEX 9.91 / 12.69) the same 1% is a very different
σ-distance in a calm week than a wild one. If outcomes depend on σ-distance
rather than on percent, the strike rule is wrong.

**Stage 1 — free, from `.m1_era1_cycles.json`:**
- Every measured cycle already carries `sigma_d` and the strike actually used.
  Compute each cycle's σ-distance = |K − spot_ref| / σ_daily.
- Bucket cycles into σ-distance terciles and re-run the M1.E threshold shares
  within each bucket, pooled state, by DTE.
- **The question:** does the ≥50/60/70/80 share vary monotonically with
  σ-distance? Report the spread between the top and bottom tercile at DTE 1.

**Stage 2 — only if stage 1 shows a spread wider than 10 percentage points:**
- Re-fetch at constant-σ strikes (K = spot ± 1.0 σ_daily, grid-rounded away)
  and compare directly against the constant-1% result on the same cycles.

**Prior:** the 1% strike underperforms in the low-IV tercile, where 1% is a
larger σ-distance and therefore cheaper premium for the same nominal distance.

**Stop condition:** if stage 1 shows no spread, record it and skip stage 2.

---

## M9 — Does the pin hold?

The whole GEX layer of the design assumes price is drawn toward concentrated
gamma. M3 measures expected versus realised *move*, which is a different claim.
This tests the pin directly, and it must beat a control to count.

**Per cycle, per symbol:**
- Compute the **max-gamma strike** at Day-1 10:30, at Day-3 close, and at
  1 DTE. Era 1: via the measured join — gamma from `hist_option_greeks_1m`,
  OI from `hist_option_bars_1m`, on `(instrument_id, bar_ts, expiry_date,
  strike, option_type)`, which the Data Inventory licenses at 60/60 hit rate.
  Era 2: `gex_strike_snapshots` where it exists.
- Record the expiry settlement level.
- Compute `|settlement − max_gamma_strike|` in σ_daily.

**The control is what makes it a measurement.** Compare against
`|settlement − spot_at_same_stamp|`, also in σ_daily. A pin claim means the
max-gamma strike forecasts settlement **better than current spot does**. If it
does not, there is no pin effect in this data, whatever the level looks like on
a chart.

**Report:**
- median and P75 of both distances, per symbol, per stamp (Day-1 / Day-3 / 1 DTE)
- the share of cycles where max-gamma beat spot
- whether the advantage grows as DTE falls — his stated claim is that the pull
  strengthens into expiry
- coverage: how many cycles had a computable max-gamma strike at each stamp
  (era 1 sidecar days are 193 NIFTY / 192 SENSEX, so expect gaps — report them
  rather than dropping them silently)

**No prior.** This is the open question, and a negative result is as valuable as
a positive one.

**Stop condition:** if fewer than 30 cycles per symbol have a computable
max-gamma strike, report INSUFFICIENT and do not report a verdict.

---

## M8 — Does the second wing earn its keep?

The pre-registration assumes a 1:1 covered spread. The reference books are
**net long the wing** at 1.2–2× the short quantity, bought at 8–12% of the
credit. Those are different instruments and only one of them is currently
measurable.

**Strikes, per cycle, at Day-1 10:30:**
- short `S` = the existing ~1% OTM strike (already cached)
- **near wing** = `S ± 0.75 σ_daily`, grid-rounded away from spot
- **far wing** = `S ± 2.5 σ_daily`, grid-rounded away — this approximates the
  3–5.6% total distance observed in the reference books

**Structures to price, per side, per cycle:**

| id | construction |
|---|---|
| N | naked short (M1's existing measurement) |
| S-near | short 1 / long 1 near wing |
| S-far | short 1 / long 1 far wing |
| R2 | short 1 / long 2 far wings |
| R3 | short 1 / long 3 far wings |

Track each at every existing stamp to expiry-day 13:00.

**Normalise before comparing.** Each structure has a different max loss, so
report P&L **per unit of its own maximum loss**, not in rupees. A ratio that
makes more money on more risk is not better.

**The decomposition that matters:** the reference books' far breakevens sit at
−23.8% and +12.9% *within a week*, moves that essentially do not occur. So if
R2 or R3 beats S-far, the advantage cannot be coming from expiry payoff — it
must come from intra-week mark-to-market on the wing. Split each structure's
P&L into:
- short-leg contribution
- wing contribution at expiry
- wing contribution from intra-week MTM (peak wing value during the cycle
  minus its value at expiry)

If the wing's whole value is MTM that was never harvested, the ratio is a
comfort purchase and should be reported as one.

**Also report:**
- wing cost as a share of credit collected, per structure, per regime — the
  reference figure is 8–12%
- the left tail: P25 and minimum per structure, which is where the ratio should
  earn its keep if it earns it anywhere
- feasibility at ₹20L: lots affordable per structure under a ₹40,000 cap, so a
  structure that only works at institutional size is flagged as such

**Prior:** R2 beats S-far on the left tail and loses to it on the median. If it
beats it on both, re-check the pricing before believing it.

**Stop condition:** if the far wing's price is below the tick size on more than
20% of cycles, the structure is not investable at that distance — report and
narrow the wing before continuing.

---

## Deliverables

One file per measurement under `research/srs/`, committed and pushed
individually, with the headline counts printed to the terminal in five lines or
fewer. Full tables to the file only.

Claim-ledger rows throughout. State what would falsify each result before
reporting it.
