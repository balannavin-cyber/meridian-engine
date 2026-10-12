# P7 — live market-hours read pack (S96, for the first session with the S96 tiles live)

**Purpose.** This read is P7's last step to DONE (ruling S96-I). Read the board in the operator's Chrome against SQL
taken at the same moment, after the first post-open cycles have landed (about 09:30 IST). Each query prints its run's
timestamp so the board and SQL are known to be on the same run. Run each on EC2 through `bin/roq.sh`, one at a time.

**Dry run, 2026-10-12 08:04 IST (pre-open):** all four ran. Each returned the 2026-10-09 settled or 15:40 figures
already on record, to the unit (DEX −8,289 / +87,880 / −96,170; flow −87,565, SAME on both symbols; Δ pair 6,089.82 /
−9,796.95 and 1,086.93 / −1,259.07). So the pack reads the right columns.

## L1 — DEX book, front leg (the DEX Net / Call / Put big numbers)

```
cd ~/meridian-cc && printf '%s' "SELECT DISTINCT symbol, expiry_date, to_char(settled_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS settled_ist, round(leg_net_dex_cr::numeric, 0) AS net, round(leg_call_dex_cr::numeric, 0) AS call, round(leg_put_dex_cr::numeric, 0) AS put, leg_gap_oi_qty FROM public.v_dex_standing_book WHERE leg_n = 1 ORDER BY symbol;" | bin/roq.sh
```

## L2 — S\* (the zero-Δ tile and dotted rule)

```
cd ~/meridian-cc && printf '%s' "SELECT symbol, to_char(ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ts_ist, front_expiry, round(spot::numeric, 1) AS spot, status, round(zero_delta::numeric, 1) AS zero_delta, round(zero_minus_spot::numeric, 1) AS above_spot, round(zero_sigma::numeric, 3) AS zero_sigma FROM public.v_dex_repriced_zero ORDER BY symbol;" | bin/roq.sh
```

## L3 — DEX flow bricks and the SAME / OPPOSITE badge

```
cd ~/meridian-cc && printf '%s' "SELECT DISTINCT symbol, expiry_date, to_char(anchor_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI') AS since, to_char(settled_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS settled_ist, flow_window, round(leg_net_preopen_dex_cr::numeric, 0) AS net_pre, round(leg_net_flow_cr::numeric, 0) AS net_flow, round(leg_call_preopen_dex_cr::numeric, 0) AS call_pre, round(leg_call_flow_cr::numeric, 0) AS call_flow, round(leg_put_preopen_dex_cr::numeric, 0) AS put_pre, round(leg_put_flow_cr::numeric, 0) AS put_flow, leg_gap_d_oi_qty, leg_no_anchor_oi_qty, flow_book_badge, flow_book_abstain_code FROM public.v_dex_flow_vs_book ORDER BY symbol;" | bin/roq.sh
```

## L4 — ∂Δ/∂σ and ∂Δ/∂t flow (`iv_book` / `t_book` are those tiles' big numbers)

```
cd ~/meridian-cc && printf '%s' "SELECT DISTINCT symbol, to_char(ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ts_ist, to_char(anchor_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI') AS since, flow_window, status, round(leg_iv_book_cr::numeric, 2) AS iv_book, round(leg_iv_preopen_cr::numeric, 2) AS iv_pre, round(leg_iv_flow_cr::numeric, 2) AS iv_flow, round(leg_t_book_cr::numeric, 2) AS t_book, round(leg_t_preopen_cr::numeric, 2) AS t_pre, round(leg_t_flow_cr::numeric, 2) AS t_flow, leg_gap_d_oi_qty, leg_no_anchor_oi_qty FROM public.v_delta_drift_flow_vs_book ORDER BY symbol;" | bin/roq.sh
```

## PASS

- Each tile equals its SQL value, as the board rounds it.
- Each sub-line's "from x at pre-open OI · y since hh:mm" equals the `*_pre`, `*_flow` and `since` columns.
- The DEX Net chip matches `flow_book_badge`:
  - SAME → "flow since hh:mm · same sign as book";
  - OPPOSITE → "flow since hh:mm · against book";
  - ABSTAIN → no chip, and the reason line for the code.
- L3 or L4 returning no rows, or `flow_window` not SESSION, means the correct board shows `no flow before 09:15`.
  That is a pass, not a defect.
- When the read passes, the roadmap §2.1 P7 row goes to **DONE** with this read as its evidence.
