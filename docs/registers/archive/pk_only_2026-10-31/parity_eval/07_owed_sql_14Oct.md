# Owed SQL for Wed 14 Oct (Day-1 carry), drafted 13 Oct 19:20 IST

Read-only, each run alone through `bin/roq.sh` on EC2. Tables/columns from `merdian_reference.json`, `parity_render_contract.md`,
`R0.1_spine_inventory_S90.md`, `tech_debt.md` (TD-S54-NEW-2, TD-S88-NEW-1), ADR-009 prereg §8.

## What the docs already answer (H6, spot freeze)
- `market_spot_snapshots` in-session rows are `dhan_charts_intraday` 09:16–15:15 only; the next row is the 16:00:04 `dhan_idx_i` settled close.
  **15:16–15:59 is empty by design** (TD-S88-NEW-1, R0.1 P4). So this table cannot show a 15:25 "resume".
- `market_ticks` holds the current day only and is purged after the close (R0.1: 33k rows at 16:57, 0 at 19:00). **13 Oct ticks are gone.**
- TD-S54-NEW-2 (open as filed): the Marketview headline spot reads `option_chain_snapshots.spot`, not the 1-min table. If still true, the tile
  shows whatever spot the last chain row carried. Q1 tests that directly.

## Q1 — chain-row spot per ts, NIFTY, 13 Oct 15:05–15:50 IST (did chain rows after 15:20 still carry 22,702.1?)
```
cd ~/meridian-cc && printf '%s' "SELECT to_char(ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ts_ist, expiry_date, min(spot) AS spot_min, max(spot) AS spot_max, count(*) AS n_rows FROM public.option_chain_snapshots WHERE symbol = 'NIFTY' AND ts >= TIMESTAMPTZ '2026-10-13 09:35:00+00' AND ts < TIMESTAMPTZ '2026-10-13 10:20:00+00' GROUP BY ts, expiry_date ORDER BY ts, expiry_date;" | bin/roq.sh
```

## Q2 — 1-min spot table, NIFTY, same window (expect last in-session row 15:15, then 16:00 only)
```
cd ~/meridian-cc && printf '%s' "SELECT to_char(ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ts_ist, source_table, spot FROM public.market_spot_snapshots WHERE symbol = 'NIFTY' AND ts >= TIMESTAMPTZ '2026-10-13 09:35:00+00' AND ts < TIMESTAMPTZ '2026-10-13 10:35:00+00' ORDER BY ts;" | bin/roq.sh
```

## Q3 — futures rows, NIFTY, same window (column list not recorded in the reference; SELECT * by design)
```
cd ~/meridian-cc && printf '%s' "SELECT * FROM public.index_futures_snapshots WHERE symbol = 'NIFTY' AND ts >= TIMESTAMPTZ '2026-10-13 09:35:00+00' AND ts < TIMESTAMPTZ '2026-10-13 10:35:00+00' ORDER BY ts;" | bin/roq.sh
```

## Q4 — NIFTY per-strike OI, last chain run of 13 Oct, front expiry (F7 gap; pair with their 15:40 replay/OI read)
```
cd ~/meridian-cc && printf '%s' "WITH r AS (SELECT ts FROM public.option_chain_snapshots WHERE symbol = 'NIFTY' AND ts >= TIMESTAMPTZ '2026-10-13 03:30:00+00' AND ts < TIMESTAMPTZ '2026-10-13 11:00:00+00' ORDER BY ts DESC LIMIT 1), e AS (SELECT min(o.expiry_date) AS exp FROM public.option_chain_snapshots o JOIN r ON o.ts = r.ts WHERE o.symbol = 'NIFTY') SELECT to_char(o.ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ts_ist, o.expiry_date, o.strike, o.option_type, o.oi, o.oi_change, o.spot FROM public.option_chain_snapshots o JOIN r ON o.ts = r.ts JOIN e ON o.expiry_date = e.exp WHERE o.symbol = 'NIFTY' AND o.strike BETWEEN 22300 AND 23100 ORDER BY o.strike, o.option_type;" | bin/roq.sh
```

## Q5a — SENSEX per-strike net γ, γ run nearest 13:25 IST on 13 Oct (H5; their zero-γ 72,540 at 13:28)
```
cd ~/meridian-cc && printf '%s' "WITH r AS (SELECT run_id FROM public.gex_strike_snapshots WHERE symbol = 'SENSEX' AND ts >= TIMESTAMPTZ '2026-10-13 07:50:00+00' AND ts < TIMESTAMPTZ '2026-10-13 08:00:00+00' ORDER BY ts DESC LIMIT 1) SELECT to_char(g.ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ts_ist, g.expiry_date, g.dte, g.spot, g.strike, g.oi_call, g.oi_put, g.gamma_call, g.gamma_put, round(g.gex_cr, 0) AS gex_cr FROM public.gex_strike_snapshots g JOIN r ON g.run_id = r.run_id WHERE g.strike BETWEEN 71000 AND 74000 ORDER BY g.strike;" | bin/roq.sh
```

## Q5b — SENSEX chain IV/OI at the same minute (inputs to re-price the ENH-131 curve offline; the view keeps only the root)
```
cd ~/meridian-cc && printf '%s' "WITH r AS (SELECT ts FROM public.option_chain_snapshots WHERE symbol = 'SENSEX' AND expiry_date = DATE '2026-10-15' AND ts >= TIMESTAMPTZ '2026-10-13 07:50:00+00' AND ts < TIMESTAMPTZ '2026-10-13 08:00:00+00' ORDER BY ts DESC LIMIT 1) SELECT to_char(o.ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ts_ist, o.spot, o.strike, o.option_type, o.oi, o.iv, o.gamma, o.ltp FROM public.option_chain_snapshots o JOIN r ON o.ts = r.ts WHERE o.symbol = 'SENSEX' AND o.expiry_date = DATE '2026-10-15' AND o.strike BETWEEN 66000 AND 80000 ORDER BY o.strike, o.option_type;" | bin/roq.sh
```

## P7 L1 / L3 / L4
Use the blocks in `claude/live_read_pack_2026-10-12.md` unchanged. They are latest-only views, so tonight they would only repeat 13 Oct's settled
state; run them at ~09:30 Wed beside a board read, which is what the pack's PASS needs.
