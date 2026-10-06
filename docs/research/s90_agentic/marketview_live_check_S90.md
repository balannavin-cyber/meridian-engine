# Marketview — first live-session check (S90, 2026-10-05, 10:27–10:40 IST)

Read through the built-in browser, signed in as the operator. All six board tabs on both symbols, plus Home, Context, Structure, Health, Settings. Values were checked against the rows the page itself fetched (captured from its own requests), not by eye. Gamma clock at first read: run `ts` 10:20 IST; chain clock 10:25 IST.

## Findings, most serious first

| # | Where | What | Evidence |
|---|---|---|---|
| **MV-1** | Home → FLOWS line | **Dealer-flow direction is inverted against the board's own legend, 3 of 3 readings.** Legend (Overview): positive Γ = dealers hedge *against* moves; negative = *with* moves. NIFTY net **+84,719 Cr** (long γ) showed `−1 %: SELL 847 · +1 %: BUY 847`; NIFTY net **−10.3L Cr** (short γ, next cycle) showed `−1 %: BUY 10,336 · +1 %: SELL`; SENSEX net **−1.1L Cr** (short γ) showed `−1 %: BUY 1,113 · +1 %: SELL`. A long-γ book buys a fall; a short-γ book sells it. Magnitude = |net| × 1 % in all three. | page text at 10:27 and 10:38 |
| **MV-2** | Header FLIP + narrative, both symbols | **Mixed clocks put spot and flip on opposite sides.** FLIP is L3 (`v_gex_repriced_flip`, chain clock 10:25, its own spot 22,499.3); SPOT and the ladder are `gamma_metrics` (10:20 run, spot 22,550.85). Header read "FLIP 22,548 · +0.22 % from spot" while the ladder drew FLIP 22,548.2 **below** SPOT 22,550.9. SENSEX the same (+0.20 % vs a flip below spot). Structural: the gamma row is one cycle behind the chain (TD-S82-NEW-2), so this recurs whenever spot moves between cycles. | captured rows: `gamma_metrics.ts 04:50:07`, `v_gex_repriced_flip.ts 04:55:06`, `flip_minus_spot 48.9` |
| **MV-3** | Context header MAX PAIN | **Distance sign inverted.** NIFTY 22,600 vs spot 22,550.85 shown **−0.2 %** (Board OI tab: **+0.22 % above spot**); SENSEX 72,500 vs 72,215 shown **−0.4 %**. MAX Γ on the same strip has the right sign (+0.7 %). | page text |
| **MV-4** | Health | **OVERALL CRITICAL is mostly the checker, not the system.** Every 5-minute writer is fresh (chain, gamma, vol, spot, WCB, state, momentum, flow ≤ 5 min). The 5 "stale": `detect_ict_patterns_runner.py` 3d at cadence **5m** (it is an EOD job, `20/22 10` UTC); `compile_market_environment_local.py` and `accrue_expiry_outcomes.py` 4d at 24h (last run 10-01; 10-02 holiday + weekend — no calendar in the check); `merdian_pipeline_alert_daemon` 116d (host "Navin"); `build_ict_htf_zones.py` 19d (unscheduled orphan, Guardrails §6). `ingest_breadth_from_ticks.py` shows host **local**; it runs on AWS (crontab lines 12, 46). | page text 10:29:52 |
| **MV-5** | Gamma tab | **Label says "share of net γ"; the number is share of gross.** NIFTY 22,500 bar −10.2L ÷ gross 85.7L = 11.9 % ✓; ÷ net 0.85L would be ~1,200 %. Header correctly says "of gross". | `v_gex_abs_exposure` row |
| **MV-6** | `v_gex_max_pain` | **Intermittent failure.** One HTTP **500 after 3,282 ms** (NIFTY, retried 200 at 1,283 ms); SENSEX Home OI line read **"no max pain"** on one cycle while Context showed 72,500. | resource timings |
| **MV-7** | Context breadth (NIFTY) | **Breadth may be partial today — not asserted.** WCB 24.6 BEARISH, **coverage 23.9 %**, adv 24.0 %, while Market Breadth reads **55 % adv, A/D 1.20 (690/575)**. SENSEX WCB coverage 63.6 %. Health top errors: `ingest_breadth_from_ticks.py` SKIPPED_NO_INPUT ×41 in 24h. Needs a feed check on the box. | page text |
| MV-8 | SENSEX corridor, 10:20 run | Degenerate: put wall = call wall = **72,500**, put wall **above** spot (`put_wall_sigma +0.093`, `BELOW_FLOOR`), rendered "72,500–72,500 · 0.00 % wide". Next cycle normal (72,000–72,500). A view property (walls are argmax within the band, no side constraint), not a render bug. | `v_gex_strike_walls` row |

## Checked and correct

- **Previous close, change and gap resolve across the 10-02 holiday:** prev 22,422 / 71,910 are the 10-01 16:00 prints; +128.9 / +467.4 and gap +0.55 % / +0.58 % recompute exactly. TD-S88-NEW-1's two-sessions-old close is **not** present.
- Priced move = `straddle_atm` (191.9 → ±0.85 %; 943.35 → ±1.30 %). Net/gross = 84,719 ÷ 8,571,532 = 0.0099. Contributing 106/116. Corridor = walls row. Basis = futures − its own spot.
- IV tab: two legs both symbols, backwardation, parity gaps shown, W1 forward vol blank (expected).
- Settings: 14 active parameters, values and reasons match the database read at 08:48.
- Placeholders as designed: Pin layer, Flows layer, γ ceiling/floor "pending"; SENSEX ΔOI "n/a".

## Not checked

Rendering pixels (text and data only), mobile layout, Structure signal semantics (BUY_PE every cycle 09:10–10:20 marked "D" — meaning of "D" not established), Gamma river per-day values.

## Re-check, 15:08–15:10 IST (before any fix applied)

Same method: built-in browser, signed in, values checked against the rows the page fetched. Gamma clock 15:05, chain clock 15:10.

### Still present

| # | Status | Evidence at re-check |
|---|---|---|
| MV-1 | **Persists** | NIFTY net **+2,53,636 Cr** (long γ) → `−1 %: SELL 2,536 · +1 %: BUY 2,536`; SENSEX net **+41,871 Cr** → `−1 %: SELL 419 · +1 %: BUY 419`. Both inverted against ADR-014 §2.3. Fix: `2026-10-05_s90_v_dealer_flow_sim_sign_fix.sql`. |
| MV-2 | **Persists (NIFTY)** | Header "FLIP 22,530 · +0.04 % from spot" with spot 22,535.0 — flip is below spot, so the sign is wrong. Board now also shows a **CLOCKS** card "γ 15:05 · chain 15:10 · 5 min apart", which makes the mix visible but does not remove it. Fix: patch (Board/Home/read.ts use one spot). |
| MV-3 | **Persists** | Context MAX PAIN NIFTY 22,550 shown **−0.1 %** (above spot 22,535); SENSEX 72,400 shown **−0.2 %**. Fix: patch (`state.ts:94`). |
| MV-4 | **Persists** | Health "11 healthy / 16 tracked"; same false stales (ICT runner at 5 m cadence, alert daemon). Fix: patch (`Health.tsx`); calendar-awareness still owed. |
| MV-5 | **Persists** | Gamma tab "10.2 % of net γ" (is share of gross). Fix: patch. |
| MV-6 | Not reproduced | `v_gex_max_pain` 200 in 888 ms on both symbols. Keep as intermittent. |

### New

| # | Where | What | Evidence |
|---|---|---|---|
| **MV-9** | Context → WCB card | **Inputs frozen all session while rows keep arriving.** `weighted_constituent_breadth_snapshots` newest row ts 09:38:03 UTC (15:08 IST) carries the same values as at 10:30: NIFTY 24.6 / adv 24.0 % / coverage 23.9 %; SENSEX 21.1 / adv 42.3 % / coverage 63.6 %. `market_breadth_intraday` moved over the same day (570/705, universe 1,314; `pct_above_*dma` NULL). The card shows no timestamp and `useWcbLatest` (`src/lib/queries.ts:490-510`) returns null on error, so a frozen or failing feed looks live. Supersedes MV-7's "not asserted": the writer is running on stale inputs. Needs a box check of its input (constituent ticks) after the close. | captured response bodies, 15:09 |
| MV-10 | Structure vs Board | **Signal stream and board are on different runs.** Signal NIFTY 15:05 row: `SHORT_GAMMA`, net −1,38,305, flip 22,535; Board γ row 15:00: net **+2,53,636 LONG**. `entry_quality` "D" and `trade_allowed=false` all day; `BUY_PE` every cycle to 14:55, then `DO_NOTHING`. Not asserted as a bug — the two read different run_ids/clocks — but an operator reading both sees contradictory regimes. | captured `signal_snapshots` |
| MV-11 | Context IV skew vs Board W1 | **Two ATM definitions.** Context IV-skew ATM 22,550; Board W1 ATM 22,500 (spot 22,535). One rounds to nearest strike, the other to nearest listed/floor. Cosmetic until a number is compared across them. | page text |
| MV-12 | Header flip vs engine flip | **Two flips differ widely**: engine `flip_level` NIFTY 23,063 vs L3 22,530; SENSEX 74,466 vs 72,194. Known by design (ADR-025 B7, two-flip); recorded so it is not re-raised as a defect. | captured rows |

### Fix inventory for ≥16:00 (unchanged)

The SQL fix (MV-1) and `s90_marketview_fixes.patch` (MV-2, MV-3, MV-4 partial, MV-5) remain valid against the live state seen at 15:10; nothing in the re-check changes them. MV-9 has no fix yet — it needs the input check first.

## Fix log

| Time (IST) | Item | Applied | Verified |
|---|---|---|---|
| 15:39 | MV-1 | `2026-10-05_s90_v_dealer_flow_sim_sign_fix.sql` in the SQL editor (postgres); gate passed, committed. Evidence: NIFTY net +203,792, SENSEX net +86,005 — both `−2/−1/−0.5 % BUY · +0.5/+1/+2 % SELL`. | 15:40 Home (SENSEX): "−1 %: BUY 860 Cr · +1 %: SELL 860 Cr" = 1 % of +86,005, direction per ADR-014 §2.3. |
| 16:01 | MV-2, MV-3, MV-4 (partial), MV-5, MV-9 | `s90_marketview_deploy*.sh` on the box: two commits on 6617ff6 → **`6cdc0a1`** (main, not yet pushed to GitHub), built, rsynced, nginx reloaded. | 16:02–16:04, SENSEX: Board FLIP 72,234 "−0.11 % from spot" with spot 72,312.2, flip drawn below spot (MV-2 ✓). Context MAX PAIN 72,400 "+0.1 %" (MV-3 ✓). Gamma "7.2 % of gross \|γ\|", unit "share of gross \|γ\|" (MV-5 ✓). Health 15 tracked, alert daemon gone, ICT runner 24 h cadence (MV-4 partial ✓; after-hours CRITICAL with "outside trading hours" note is by design). WCB card shows "as of 15:23 · values unchanged since 15:40 (76 rows)" — see MV-9b. |
| 16:06 | MV-9b | `s90_mv9b_deploy.sh` → **`265ceb0`** (main, not yet pushed). | 16:07 Context (SENSEX): "as of 05/10 15:23 · values unchanged since 01/10 15:40 (76 rows)" — run not capped, so the change point is inside the window: values last changed **between the 01/10 15:35 and 15:40 rows**. |

**MV-9b — WCB frozen across sessions, not just today.** The unchanged run on SENSEX spans all 76 rows read, and its oldest row is 15:40 IST on a **previous** day (today's newest is 15:23 and today has ~74 rows from 09:15), i.e. 01 Oct, the last session. So the WCB headline values (21.1 / adv 42.3 % / coverage 63.6 %) have not changed since 01 Oct 15:40 (confirmed 16:07 after MV-9b: the run is not capped, so 15:40 is the actual start). The writer runs and stamps fresh `ts`, but its inputs are frozen. Root cause still open: needs the writer's input read on the box (after the close, roq.sh).

## Root causes found after the close (P5, 16:57 IST)

**MV-9 — CONFIRMED, two defects, neither in Marketview.** `build_wcb_snapshot_local.py:251-280` computes each constituent's move as `equity_intraday_last.last_price ÷ breadth_indicators_daily.prev_close`.
1. `equity_intraday_last` is **not intraday**. `refresh_equity_intraday_last.py` (cron `35 3 * * 1-5`, 09:05 IST, once) writes `last_price = Kite ohlc().close`, the **prior session's close** (`:125-140`); today 1,314 rows at 09:05:08, nothing after. HDFCBANK `last_price 721.2`.
2. `breadth_indicators_daily` has stalled: newest `trade_date` **2026-09-29** (815 tickers, inserted 10-02 17:35 IST); none for 09-30 or 10-01; last full day 09-24 (1,363). HDFCBANK's row: `trade_date 09-29, prev_close 722.7, close 708.7`. **RELIANCE has no row since 09-29**, so it drops to `missing_daily` — the NIFTY coverage of 23.9 % is weight lost this way.
So WCB "adv" = (a prior close) ÷ (an older close), fixed for the whole session. The 01-Oct-15:40 → 05-Oct identity is consistent with that but not fully explained (the 09-29 daily rows landed in between and should have moved it); leave it until the writer is re-run by hand with its debug output.
**Fix (needs a ruling — writer change, SC):** take the live price from `market_ticks` EQ (33,365 EQ ticks today; `ingest_breadth_from_ticks.py` already reads it), keep `equity_intraday_last` as what it now is — the prior close — and fix the EOD writer of `breadth_indicators_daily`. Until then the card's amber line is the honest state.

**MV-6 — probable cause.** `anon` has `statement_timeout = 3s`; the failure was a **500 after 3,282 ms** on `v_gex_max_pain`. Consistent with the view exceeding anon's timeout on a slow cycle. Not proven (needs the PostgREST error body); index or simplify the view, or cache its result per run.

| 19:01 | MV-9 root cause (R01-F9 part 1) | `build_wcb_snapshot_local.py` reads live LTP from `market_ticks` (EQ, last 10 min) over the prior close in `equity_intraday_last`; no tick => constituent drops out (ruling S90-G, `f7c7d9f`). | Offline test with fakes passes; live validation owed 2026-10-06 09:30 (ticks purged after close). |
