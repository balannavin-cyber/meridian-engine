# Engine study: how the vendor chain computes greeks, and what the market forward says (DRAFT, 2026-11-19)

**For:** the engine lane. **Written in:** MR-FOI3 (Session 95). **Status:** study design, DRAFT. A measurement, not a pre-registered test: no verdict words, no thresholds passed or failed. Nothing here designs or authorises a fix; G1/G2/G3 in `claude/engine_note_pin_basis_and_vendor_greeks_2026-11-18.md` §6 stay as options.
**Who runs what:** the operator runs the SQL below in the SQL editor. Claude does not run SQL on production. Each query reads about 70,000 to 140,000 chain rows through the `run_id` index and returns under 40 rows.

## 1. Question

The engine note found that the vendor's call IV and put IV at one strike disagree (ratio 0.73 to 1.06 across 5 to 18 Nov), and inferred a vendor forward of spot plus about 10 % a year. That 10 % came from a fit. This study measures the vendor's three conventions directly from stored rows, then sets them beside the market:

1. **Time to expiry:** calendar time or trading days; to 15:30, to midnight, or whole days.
2. **Forward and rate:** spot grown at a fixed rate, or the futures price, or something else.
3. **Market forward:** what near-the-money call minus put, and the futures price, give for the same minute.
4. **Call/put IV equality:** how much of the gap closes when one market forward is used for the whole chain.

## 2. What the vendors publish

- **Dhan:** a community post by Dhan staff says Black-Scholes with IV as the volatility input; no rate, dividend or underlying (spot or futures) is given; it mentions converting theta with 252 trading days, which is why the time convention is measured and not assumed. The API docs list greeks and IV per leg and give no method. (https://madefortrade.in/t/learn-how-are-option-greeks-calculated-on-dhan-know-more/9653, https://dhanhq.co/docs/v2/option-chain/)
- **Fyers:** the live option-chain call returns `iv`, `delta`, `gamma`, `theta`, `vega` per leg when `greeks=1` is sent, at most 50 strikes each side, plus a futures price field `fp` on the underlying row. No model or rate is stated. (https://fyers.in/api-docs/v3/api/market-data/option-chain/)
- **Fyers stored tables:** `fyers_chain_bars_3m` is open, high, low, close, volume, oi, source (MR-FOI1 §1). No greeks. Query F1 confirms the same for `fyers_chain_bars_1m`. So Fyers greeks exist only on a live call; the history we loaded cannot answer this.

## 3. Method (Dhan, from `option_chain_snapshots`)

All steps use closed forms, so they run as plain SQL with no solver. Runs are picked through `gamma_metrics` (front expiry, 10:00 to 10:30 IST, 5 to 18 Nov) and joined to the chain on `run_id`.

**A. Time to expiry.** In Black-Scholes, vega ÷ gamma = S² · σ · T, whatever the rate or forward. So each leg gives the vendor's T on its own: T = 100 · vega ÷ (gamma · S² · σ), with vega per one volatility point. Query Q2 prints it in days (×365) beside four candidates: calendar days to 15:30 on expiry day, to midnight, the whole-day date difference, and weekdays left. A morning and an afternoon window show whether T runs down within the day. 13 Nov (Friday, Tuesday expiry: 4 calendar days, 2 weekdays) separates calendar from trading-day counting.
*Can fail:* if no candidate matches within the p10 to p90 spread, the convention is none of these. If the figure is 100 times off, vega is per unit, not per point.

**B. Vendor forward and rate.** Gamma also fixes |d1|: φ(d1) = gamma · S · σ · √T. The sign comes from delta. Then F_vendor = K · exp(d1·σ·√T − σ²T/2) and rate = ln(F_vendor ÷ S) ÷ T. Query Q3 does this on legs with |delta| in 0.15 to 0.40 or 0.60 to 0.85 (near the money the inversion is unstable).
*How to read it:* a rate that is the same on every day, with calls and puts agreeing, means spot grown at a fixed rate (net of any dividend assumption). A rate that moves from day to day and tracks the futures basis means the vendor uses a futures price. Calls and puts disagreeing means the model is not one forward per chain.
*Second route, independent of d1:* near the money, (call IV − put IV) × vega ≈ −(F_vendor − F_market). Q4 prints the vendor forward by this route. The two routes should agree to within a few points; if they do not, one of the assumptions (Black-Scholes, one T) is wrong.

**C. Market forward.** Q4, same runs: (i) parity forward = strike + call − put, mid prices where both sides are quoted, median over strikes within 0.4 % of spot; (ii) futures basis from `index_futures_snapshots` within 150 s, and the same scaled by time to the option expiry over time to the futures expiry (straight-line carry). The scaled futures figure and the parity figure are two market readings of one quantity.
*Can fail:* if they differ by more than a few points, either prices are stale or straight-line scaling is too crude (dividends are lumpy), and the fix cannot take the futures price as its forward without a check.

**D. Call/put IV equality.** Defining the forward from a strike's own call and put makes its two IVs equal by construction, so that cannot be the test. Q5 sets the forward from the near-the-money band only (within 0.4 %), then tests the strikes outside it (0.4 % to 1.5 %): parity residual in points, converted to volatility points by dividing by vega (first-order), beside the vendor's own call/put IV gap at the same strikes and the share of residuals inside half the quoted spreads. The same is repeated with the scaled futures forward.
*Can fail:* large residuals outside the spreads mean one forward does not fit the chain as stored (stale last-traded prices, wide quotes), and an own-solve needs stale-price handling before it can promise equal IVs.
*Exact version, engine lane, after 15:40 on the box:* replay the same runs with `core/bs_engine.py`, forward from the market, one IV per leg, and report |call IV − put IV| per strike. That is §6.4 of the engine note; Q5 is its solver-free preview.

**E. Fyers.** Needs a live capture, because no stored Fyers row has greeks: one call per index with `greeks=1` at a clock minute that matches a Dhan chain run, saved to a file on Local (`C:\fyers_test`, the daily login is already a manual step), then A to D on that file. Also record `fp`. Two or three captures on one day are enough to read the convention. Not started; needs the operator's go-ahead and a small script.

**Other brokers.** Upstox has an option-greek endpoint (https://upstox.com/developer/api-documentation/option-greek); its method was not looked up. Kite Connect quotes carry no greeks as far as I know (not checked this session). Worth a capture only if the operator wants a third comparison.

## 4. The rate question, plainly

An option is priced off the level the market sets today for the index on expiry day: spot plus the cost of carrying it there, less dividends. That level is the forward. It is cost of carry, not a forecast.

A vendor who does not read that level builds it: spot × e^(rate × time). If the rate is wrong for the day, the forward is wrong, calls look cheap and puts dear (or the reverse), and the two IVs at one strike split. That is the tilt in the engine note.

If the forward is read from the market instead (futures price, or call minus put plus strike near the money), no rate is assumed for it. Interest, dividends and any stress are already inside the market's number, and it moves by itself when RBI changes policy. Nobody maintains a rate parameter.

A rate is still needed for one small thing: discounting the premium from expiry day to today. On a five-day option that factor is about 0.9991. In the forward it multiplies only call minus put (tens of points near the money), so a one-percentage-point error in the rate moves the forward by under 0.01 point. Ignoring discounting altogether moved the forward by about 0.2 point in the planted check (§6). A fixed 6.5 % left untouched for years would do.

## 5. What the result will and will not settle

- Settles: the vendor's T convention; whether its forward is spot-plus-rate or futures-based, and the rate; how far that forward sits from the market's on each of the nine days; whether one market forward closes the call/put gap in the stored prices.
- Does not settle: which fix to build (G1, G2 or G3); the ranking-basis question (R1 to R4); anything about Fyers until part E is captured; the back expiry (the queries read the front expiry only, because that is what `gamma_metrics` computes).
- Assumed, checked by Q1: `gamma_metrics.run_id` equals the chain `run_id`. If Q1 shows `n_legs = 0`, the join is wrong and Q2 to Q5 would return nothing; stop there.
- Not verified: that `option_chain_snapshots.spot` is the vendor's own underlying price at that instant; the unit of vendor vega (Q2 shows it); whether mid prices or last-traded prices are what the vendor solves on.

## 6. Check of the method (done before sending)

The five queries were run on a local scratch Postgres 16 against a synthetic chain built with known answers: vendor = Black-Scholes on spot at 10 % with calendar time to 15:30; market forward = spot −8.0 (NIFTY 18 Nov), +6.0 (NIFTY 13 Nov), −49.0 (SENSEX 18 Nov). Recovered: T ratio to calendar-15:30 = 1.0000 on all six day-windows; rate 10.00 % on all three days; vendor carry by the d1 route 36.0 / 29.7 / 27.3 points against 36.0 / 29.6 / 27.2 by the gap route; parity forward −8.0 / +6.0 / −49.0; scaled futures the same. This shows the algebra and the SQL are right on clean data. It says nothing about production data quality.

## 7. SQL (operator runs; one statement per block)

**Q1. Join and coverage check.** Expect about 7 runs per symbol per day and `n_legs` in the hundreds.

```sql
select g.symbol, (g.ts at time zone 'Asia/Kolkata')::date as d, g.expiry_date,
       count(distinct g.run_id) as n_runs,
       count(o.run_id) as n_legs,
       count(*) filter (where o.iv > 0) as n_iv,
       count(*) filter (where o.gamma > 0) as n_gamma,
       count(*) filter (where o.vega > 0) as n_vega,
       count(*) filter (where o.delta is not null and o.delta <> 0) as n_delta,
       count(*) filter (where o.bid > 0 and o.ask > 0) as n_two_sided
from gamma_metrics g
left join option_chain_snapshots o on o.run_id = g.run_id and o.expiry_date = g.expiry_date
where g.ts >= '2026-11-05 00:00+05:30' and g.ts < '2026-11-19 00:00+05:30'
  and (g.ts at time zone 'Asia/Kolkata')::time between '10:00' and '10:30'
group by g.symbol, (g.ts at time zone 'Asia/Kolkata')::date, g.expiry_date
order by g.symbol, d;
```

**Q2. Vendor time to expiry.**

```sql
with runs as (
  select symbol, run_id, expiry_date,
         case when (ts at time zone 'Asia/Kolkata')::time < '12:00' then 'am' else 'pm' end as win
  from gamma_metrics
  where ts >= '2026-11-05 00:00+05:30' and ts < '2026-11-19 00:00+05:30'
    and ((ts at time zone 'Asia/Kolkata')::time between '10:00' and '10:30'
      or (ts at time zone 'Asia/Kolkata')::time between '14:30' and '15:00')
), legs as (
  select o.symbol, (o.ts at time zone 'Asia/Kolkata')::date as d, r.win, o.expiry_date,
         100.0 * o.vega::float8 / (o.gamma::float8 * o.spot::float8 * o.spot::float8 * (o.iv::float8 / 100)) * 365 as tv_days,
         extract(epoch from ((o.expiry_date + time '15:30') at time zone 'Asia/Kolkata') - o.ts) / 86400.0 as cal_days
  from option_chain_snapshots o
  join runs r on r.run_id = o.run_id and r.expiry_date = o.expiry_date
  where o.iv > 0 and o.gamma > 0 and o.vega > 0
    and abs(o.strike / o.spot - 1) <= 0.02
)
select symbol, d, win, expiry_date, count(*) as n_legs,
       round(percentile_cont(0.1) within group (order by tv_days)::numeric, 3) as tv_days_p10,
       round(percentile_cont(0.5) within group (order by tv_days)::numeric, 3) as tv_days_p50,
       round(percentile_cont(0.9) within group (order by tv_days)::numeric, 3) as tv_days_p90,
       round(avg(cal_days)::numeric, 3) as cal_days_to_1530,
       round(avg(cal_days)::numeric + 0.354, 3) as cal_days_to_midnight,
       (expiry_date - d) as date_diff_days,
       (select count(*) from generate_series(d + 1, expiry_date, interval '1 day') g where extract(isodow from g) < 6) as weekdays_left,
       round((percentile_cont(0.5) within group (order by tv_days / cal_days))::numeric, 4) as ratio_to_cal_1530
from legs
group by symbol, d, win, expiry_date
order by symbol, d, win;
```

**Q3. Vendor forward and rate (d1 route).**

```sql
with runs as (
  select symbol, run_id, expiry_date
  from gamma_metrics
  where ts >= '2026-11-05 00:00+05:30' and ts < '2026-11-19 00:00+05:30'
    and (ts at time zone 'Asia/Kolkata')::time between '10:00' and '10:30'
), legs as (
  select o.symbol, (o.ts at time zone 'Asia/Kolkata')::date as d, o.expiry_date, o.option_type as cp,
         o.spot::float8 as s, o.strike::float8 as k, o.iv::float8 / 100 as sig,
         o.delta::float8 as delta, o.gamma::float8 as gamma,
         100.0 * o.vega::float8 / (o.gamma::float8 * o.spot::float8 * o.spot::float8 * (o.iv::float8 / 100)) as tv,
         extract(epoch from ((o.expiry_date + time '15:30') at time zone 'Asia/Kolkata') - o.ts) / 86400.0 / 365 as tcal
  from option_chain_snapshots o
  join runs r on r.run_id = o.run_id and r.expiry_date = o.expiry_date
  where o.iv > 0 and o.gamma > 0 and o.vega > 0
    and (abs(o.delta) between 0.15 and 0.40 or abs(o.delta) between 0.60 and 0.85)
), d1 as (
  select *, gamma * s * sig * sqrt(tv) * 2.5066282746 as phi_ratio,
         case when (cp = 'CE' and delta > 0.5) or (cp = 'PE' and delta > -0.5) then 1 else -1 end as sgn
  from legs
), fv as (
  select *, k * exp(sgn * sqrt(-2 * ln(phi_ratio)) * sig * sqrt(tv) - sig * sig * tv / 2) as f_vendor
  from d1
  where phi_ratio > 0 and phi_ratio < 1
)
select symbol, d, expiry_date, count(*) as n_legs,
       round((percentile_cont(0.5) within group (order by f_vendor - s) filter (where cp = 'CE'))::numeric, 1) as vendor_carry_pts_calls,
       round((percentile_cont(0.5) within group (order by f_vendor - s) filter (where cp = 'PE'))::numeric, 1) as vendor_carry_pts_puts,
       round((percentile_cont(0.1) within group (order by f_vendor - s))::numeric, 1) as carry_pts_p10,
       round((percentile_cont(0.9) within group (order by f_vendor - s))::numeric, 1) as carry_pts_p90,
       round((100 * percentile_cont(0.5) within group (order by ln(f_vendor / s) / tv))::numeric, 2) as rate_pct_on_vendor_t,
       round((100 * percentile_cont(0.5) within group (order by ln(f_vendor / s) / tcal))::numeric, 2) as rate_pct_on_calendar_t
from fv
group by symbol, d, expiry_date
order by symbol, d;
```

**Q4. Market forward (parity, futures) and vendor forward (gap route).**

```sql
with runs as (
  select symbol, run_id, expiry_date
  from gamma_metrics
  where ts >= '2026-11-05 00:00+05:30' and ts < '2026-11-19 00:00+05:30'
    and (ts at time zone 'Asia/Kolkata')::time between '10:00' and '10:30'
), legs as (
  select o.symbol, o.run_id, o.ts, o.expiry_date, o.option_type as cp,
         o.spot::float8 as s, o.strike::float8 as k,
         case when o.bid > 0 and o.ask >= o.bid then (o.bid + o.ask)::float8 / 2 else o.ltp::float8 end as px,
         o.iv::float8 as iv, o.vega::float8 as vega
  from option_chain_snapshots o
  join runs r on r.run_id = o.run_id and r.expiry_date = o.expiry_date
  where o.ltp > 0 and abs(o.strike / o.spot - 1) <= 0.004
), pairs as (
  select c.symbol, c.run_id, c.ts, c.expiry_date, c.s, c.k,
         c.k + c.px - p.px as f_pcp,
         c.iv as iv_c, p.iv as iv_p,
         c.k + c.px - p.px - (c.iv - p.iv) * (c.vega + p.vega) / 2 as f_vendor_gap
  from legs c
  join legs p on p.run_id = c.run_id and p.k = c.k and p.cp = 'PE'
  where c.cp = 'CE' and c.iv > 0 and p.iv > 0 and c.vega > 0 and p.vega > 0
), per_run as (
  select symbol, run_id, min(ts) as ts, expiry_date, avg(s) as s, count(*) as n_strikes,
         percentile_cont(0.5) within group (order by f_pcp) as f_pcp,
         percentile_cont(0.5) within group (order by f_vendor_gap) as f_vendor_gap,
         percentile_cont(0.5) within group (order by iv_c / iv_p) as iv_ratio
  from pairs
  group by symbol, run_id, expiry_date
), with_fut as (
  select r.*, f.basis::float8 as fut_basis, f.expiry_date as fut_expiry,
         f.basis::float8
           * extract(epoch from ((r.expiry_date + time '15:30') at time zone 'Asia/Kolkata') - r.ts)
           / nullif(extract(epoch from ((f.expiry_date + time '15:30') at time zone 'Asia/Kolkata') - r.ts), 0) as fut_basis_scaled
  from per_run r
  left join lateral (
    select i.basis, i.expiry_date
    from index_futures_snapshots i
    where i.symbol = r.symbol and i.ts between r.ts - interval '150 seconds' and r.ts + interval '150 seconds'
    order by abs(extract(epoch from i.ts - r.ts))
    limit 1
  ) f on true
)
select symbol, (ts at time zone 'Asia/Kolkata')::date as d, expiry_date, count(*) as n_runs,
       round(avg(n_strikes), 1) as strikes_per_run,
       round((percentile_cont(0.5) within group (order by f_pcp - s))::numeric, 1) as parity_fwd_minus_spot_pts,
       round((percentile_cont(0.5) within group (order by f_vendor_gap - s))::numeric, 1) as vendor_fwd_minus_spot_pts_gap_route,
       round((percentile_cont(0.5) within group (order by iv_ratio))::numeric, 3) as call_iv_over_put_iv,
       count(fut_basis) as n_runs_with_future,
       min(fut_expiry) as fut_expiry,
       round((percentile_cont(0.5) within group (order by fut_basis))::numeric, 1) as fut_basis_pts,
       round((percentile_cont(0.5) within group (order by fut_basis_scaled))::numeric, 1) as fut_basis_scaled_to_option_expiry_pts
from with_fut
group by symbol, (ts at time zone 'Asia/Kolkata')::date, expiry_date
order by symbol, d;
```

**Q5. One forward for the whole chain: call/put gap outside the band.**

```sql
with runs as (
  select symbol, run_id, expiry_date
  from gamma_metrics
  where ts >= '2026-11-05 00:00+05:30' and ts < '2026-11-19 00:00+05:30'
    and (ts at time zone 'Asia/Kolkata')::time between '10:00' and '10:30'
), legs as (
  select o.symbol, o.run_id, o.ts, o.expiry_date, o.option_type as cp,
         o.spot::float8 as s, o.strike::float8 as k,
         (o.bid + o.ask)::float8 / 2 as mid, (o.ask - o.bid)::float8 as spread,
         o.iv::float8 as iv, o.vega::float8 as vega
  from option_chain_snapshots o
  join runs r on r.run_id = o.run_id and r.expiry_date = o.expiry_date
  where o.bid > 0 and o.ask >= o.bid and o.iv > 0 and o.vega > 0
    and abs(o.strike / o.spot - 1) <= 0.015
), pairs as (
  select c.symbol, c.run_id, c.ts, c.expiry_date, c.s, c.k,
         abs(c.k / c.s - 1) <= 0.004 as in_atm_band,
         c.k + c.mid - p.mid as f_k,
         (c.spread + p.spread) / 2 as tol_pts,
         (c.vega + p.vega) / 2 as vega_pt,
         abs(c.iv - p.iv) as vendor_gap_volpts
  from legs c
  join legs p on p.run_id = c.run_id and p.k = c.k and p.cp = 'PE'
  where c.cp = 'CE'
), fwd as (
  select run_id, percentile_cont(0.5) within group (order by f_k) as f_hat
  from pairs
  where in_atm_band
  group by run_id
), fut as (
  select r.run_id,
         r.s + f.basis::float8
           * extract(epoch from ((r.expiry_date + time '15:30') at time zone 'Asia/Kolkata') - r.ts)
           / nullif(extract(epoch from ((f.expiry_date + time '15:30') at time zone 'Asia/Kolkata') - r.ts), 0) as f_fut
  from (select run_id, symbol, expiry_date, min(ts) as ts, avg(s) as s from pairs group by 1, 2, 3) r
  join lateral (
    select i.basis, i.expiry_date
    from index_futures_snapshots i
    where i.symbol = r.symbol and i.ts between r.ts - interval '150 seconds' and r.ts + interval '150 seconds'
    order by abs(extract(epoch from i.ts - r.ts))
    limit 1
  ) f on true
), resid as (
  select p.symbol, (p.ts at time zone 'Asia/Kolkata')::date as d, p.expiry_date,
         abs(p.f_k - w.f_hat) as e_pts, p.tol_pts, p.vega_pt, p.vendor_gap_volpts,
         abs(p.f_k - u.f_fut) as e_fut_pts
  from pairs p
  join fwd w on w.run_id = p.run_id
  left join fut u on u.run_id = p.run_id
  where not p.in_atm_band
)
select symbol, d, expiry_date, count(*) as n_test_pairs,
       round((percentile_cont(0.5) within group (order by vendor_gap_volpts))::numeric, 2) as vendor_call_put_iv_gap_volpts_p50,
       round((percentile_cont(0.5) within group (order by e_pts / vega_pt))::numeric, 2) as parity_fwd_gap_volpts_p50,
       round((percentile_cont(0.9) within group (order by e_pts / vega_pt))::numeric, 2) as parity_fwd_gap_volpts_p90,
       round((percentile_cont(0.5) within group (order by e_pts))::numeric, 2) as parity_fwd_resid_pts_p50,
       round((100.0 * count(*) filter (where e_pts <= tol_pts) / count(*))::numeric, 1) as pct_within_half_spreads,
       count(e_fut_pts) as n_pairs_with_future,
       round((percentile_cont(0.5) within group (order by e_fut_pts / vega_pt))::numeric, 2) as futures_fwd_gap_volpts_p50,
       round((percentile_cont(0.5) within group (order by e_fut_pts))::numeric, 2) as futures_fwd_resid_pts_p50
from resid
group by symbol, d, expiry_date
order by symbol, d;
```

**F1. Fyers stored chain columns.**

```sql
select table_name, column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name like 'fyers_chain_bars%'
order by table_name, ordinal_position;
```

**Results:** none yet. To be pasted by the operator and recorded here.
