# MERDIAN — Hedgewall parity specification

**Date:** 2026-09-14 (Session 78) · **Status:** DRAFT for operator review
**Scope:** every layer on hedgewall.in, resolved to a source table, a computation, a
horizon and a build status.
**§2.5** adds measured features from SpotGamma, Volland and SqueezeMetrics that Hedgewall
itself does not carry. They sit outside the build order by design.

Every source claim in this document was measured in S78 against the live database, or is
cited to the register that measured it. Nothing is inferred from a table name. Where a
figure comes from a prior session it is cited; where it was measured today it is marked
**(S78)**.

This is the document that did not exist. `build_readiness_2026-09-09.md` states what the
data is and explicitly refuses to recommend. `ADR-017` states how the console should
behave. `ENH-110` ships the console. No document mapped Hedgewall's surface onto them.

---

## 0. The one-paragraph answer

Fourteen layers. **Nine are computable today at full live cadence.** Four more are
computable but only over 61/62 days because they need `delta`, which exists only in the
chain-snapshot tier. One — flip — exists but is unsound and must be rebuilt before it is
displayed. Per-strike gamma history is **near-continuous from 2025-04-01 to now**, which
is better than the S78 brief assumed: the 58-session mid-2026 hole is a gap in the *chain*
tables only, and `gex_strike_snapshots` covers it.

---

## 1. Source inventory — what each tier actually holds

Five tiers carry a strike dimension. They do not overlap cleanly and they do not count the
same things.

| tier | span | cadence | per-strike fields | greeks |
|---|---|---|---|---|
| `hist_option_bars_1m` (GFDL vendor) | 2025-04-01 → 2026-05-07 | 1-min, 376/day | OHLC, volume, **oi**, 14 expiries/min | **none** — declared, never written |
| `hist_option_greeks_1m` (MERDIAN solve) | 2025-04-01 → 2026-03-30 | 1-min, 193/192 days | **iv, gamma**, `r_used` | iv + gamma only, **no delta** |
| `historical_option_chain_snapshots` (HOCS) | 2026-03-16 → 2026-06-03 | 9/day → 64–68/day | ltp, bid, ask, oi, **iv, delta, gamma, theta, vega**, spot | full |
| `gex_strike_snapshots` (GSS) | 2026-05-25 → present | 74–84/day | `gamma_call`, `gamma_put`, `oi_total_calls`, `oi_total_puts`, `gex_cr`, spot | gamma split CE/PE |
| `option_chain_snapshots` (OCS) | 2026-08-24 → present | ~86/day | as HOCS | full |

**Measured S78:**

- GFDL vendor file `GFDLNFO_BACKADJUSTED_01042025.csv` — **9 columns**, uniform across all
  175,304 rows: `Ticker, Date, Time, Open, High, Low, Close, Volume, Open Interest`.
  1,112 tickers, 11 expiries, 376 minutes 09:15:59 → 15:30:59. **No IV, no greeks.**
  The greeks were never delivered; they were not dropped at load.
- `hist_option_bars_1m` at 2025-06-02 09:20 UTC: 812 rows, `iv/delta/gamma/theta/vega/
  heston_v0` all null, **14 distinct expiries in that one minute**.
- `hist_option_greeks_1m` same minute: 339 rows, `iv` on 327, **2 distinct expiries**.
- `historical_option_chain_snapshots`: NIFTY 47 days / 1,625,801 rows / `delta` 96.2 %;
  SENSEX 48 days / 1,585,714 rows / 95.8 %. `delta_written == iv_written` exactly on both.
- `option_chain_snapshots`: NIFTY 15 days / 511,768 rows / **100.0 %**; SENSEX 15 days /
  394,144 rows / **100.0 %**.
- `gex_strike_snapshots`: 1,503,503 rows; NIFTY 7,371 and SENSEX 11,116 rows on 2026-09-11.

### 1.1 The three exclusions

- **Three Breeze-backfill days** carry no spot, no greeks, no bid/ask: NIFTY 2026-04-16,
  SENSEX 2026-04-16 (`breeze_backfill_s35`), SENSEX 2026-06-03 (`breeze_backfill_s44`).
  SENSEX 2026-04-16 additionally has **no `oi`** and supports no layer at all.
- **`v_oi_prev_close_snapshots`** cannot prove absence on an empty day (HTTP 500 at ~8.3 s
  on every scope tried) and is excluded from the data inventory by method rule 6.
- **`volatility_snapshots` is single-expiry** — one row per `(ts, symbol)` on all 46,853
  rows, and it silently switches expiry class (NIFTY 560 MONTHLY timestamps 2026-03-25 →
  04-13; SENSEX 674 across 2026-03-20 → 05-27). It cannot serve a term structure.

### 1.2 Greek horizon, stated once

| capability | horizon | why |
|---|---|---|
| per-strike **gamma + oi** | **299 days** per symbol, 2025-04-01 → present | greeks_1m ⋈ bars_1m, then HOCS, then GSS |
| per-strike **delta / theta / vega** | **61 NIFTY / 62 SENSEX days** | only HOCS + OCS carry them |
| **14-expiry** cross-sectional OI | 2025-04-01 → 2026-05-07 | bars_1m only |
| **2-expiry** IV term slope | 2025-04-01 → 2026-03-30 | greeks_1m only |

---

## 2. The fourteen layers

Status key: **BUILT** — running in production · **PARTIAL** — substrate exists, no
consumer · **ABSENT** — nothing built · **UNSOUND** — built but must not be displayed.

### L1 · Gamma density per strike, OI-weighted — **BUILT**

| | |
|---|---|
| Source | `gex_strike_snapshots.gex_cr` (live), `option_chain_snapshots` (recompute) |
| Compute | `gamma × oi × spot² / 1e7`, PE negated; deep-ITM guard drops \|K−S\|/S > 5 % with \|γ\| > 5e-5 |
| Horizon | 299 d |
| Built by | **ENH-80 SHIPPED (S37)**, ADR-015 schema v2 |
| Displayed | Marketview GEX-by-strike histogram |
| Left to do | Nothing |

### L2 · Pin zone — **BUILT**

| | |
|---|---|
| Source | `v_gex_strike_pin_zone` over GSS |
| Compute | τ-weighted concentration band, `tau_pin` from `merdian_parameters` (`pin.tau.{symbol}`) |
| Horizon | 2026-05-25 → present (GSS span) |
| Built by | **ENH-81 SHIPPED (S37)** |
| Displayed | Marketview ReferenceArea band + Pine overlay box |
| Left to do | Nothing |

### L3 · Flip level — **UNSOUND, must be rebuilt before display**

| | |
|---|---|
| Current source | `gamma_metrics.flip_level`, `compute_gamma_metrics_local.py:949` |
| Defect | `flip_audit_2026-09-08.md`: the **value** gates nothing; the two branches return levels on opposite sides of spot on the same chain; median 5-min step 10 pts NIFTY / 41 SENSEX, **max 1,330 / 7,300**; price spends zero minutes within 0.1 % of the open flip on 43 of 63 NIFTY and 38 of 63 SENSEX sessions |
| Gate impact | **presence** gates `trade_allowed` on only **3.3 % NIFTY / 1.5 % SENSEX** of cycles (`NO_FLIP`). The 73.4 % / 62.9 % `LONG_GAMMA` share is gated on `net_gex >= 0` — a **separate, unruled** decision |
| Hedgewall's version | zero-gamma crossing of net GEX, recomputed per tick |
| Rebuild | cumulative `SUM(gex_cr) OVER (ORDER BY strike)` from GSS; linear interpolation at the sign change; **new column alongside `flip_level`, not a mutation** — five consumers read the current construct |
| Effort | ~0.5 day (one view + one writer field + Marketview wiring) |

### L4 · Call wall — **ABSENT**

| | |
|---|---|
| Source | `gex_strike_snapshots.oi_total_calls` + `gamma_call`; `option_chain_snapshots` where `option_type='CE'` |
| Compute | `argmax(oi_total_calls)` above spot, and separately `argmax(gamma_call × oi_total_calls)` — the two differ and both are worth rendering |
| Horizon | 299 d (OI) / 299 d (gamma-weighted) |
| ENH | **none** — file one |
| Effort | ~2 h (one SQL view + Marketview marker) |

### L5 · Put wall — **ABSENT**

As L4 on `oi_total_puts` / `gamma_put`, below spot. Same view, same effort. File with L4 as
one ENH.

### L6 · Net-vs-absolute GEX regime — **BUILT**

| | |
|---|---|
| Source | `gamma_metrics.net_gex` (Cr, `/1e7` per TD-NEW-3), `regime` |
| Compute | `SUM(gex_cr)` vs `SUM(ABS(gex_cr))`; ratio is the dampening-vs-amplifying read |
| Horizon | 299 d |
| Displayed | Marketview REGIME card, `v_dealer_flow_sim` |
| Left to do | The **absolute** leg is not surfaced — only net. ~1 h to add the ratio |

### L7 · Vanna — **PARTIAL**

| | |
|---|---|
| Source | `option_chain_snapshots` / HOCS — needs per-strike `delta` **and** `iv` |
| Compute | ∂δ/∂σ. ENH-98: *"extending to second-order is mechanical given the BS pricing infrastructure"* (`core/bs_engine.py`, ENH-33) |
| Horizon | **61 / 62 days** — `hist_option_greeks_1m` has no `delta` column, so this cannot be extended backward |
| ENH | **ENH-98 PROPOSED**, build deferred, blocked on *"Phase 2 deployment plan commitment"* |
| Blocker to clear | ENH-98's deferral was written when vanna had no Phase-1 consumer. Hedgewall parity **is** the consumer. The block is an operator decision, not data |
| Effort | ~0.5 day compute + storage decision (`gamma_metrics` columns vs `greeks_l2_analytics` table — ADR-015 minimum-sufficient-statistic doctrine argues for a separate table) |

### L8 · Charm — **PARTIAL**

As L7, ∂δ/∂t. Same source, same horizon, same ENH, same blocker. Ship with L7.

### L9 · IV term structure, front-weekly to far-month — **ABSENT**

| | |
|---|---|
| Source, live | `option_chain_snapshots` — full expiry ladder per cycle |
| Source, history | **`hist_option_greeks_1m` gives a 2-point slope over 299 d** (front vs next, measured S78). The full ladder is 61/62 d only |
| Compute | ATM strike per expiry → `GROUP BY expiry_date` → slope |
| Not usable | `volatility_snapshots` — single-expiry, confirmed |
| ENH | none. **ENH-12 is calendar *spreads*, a trade, not a panel** |
| Effort | ~3 h (one view + one chart). Highest value-per-hour on this list |

### L10 · IV surface, strike × expiry — **ABSENT**

| | |
|---|---|
| Source | `option_chain_snapshots` + HOCS |
| Compute | mesh over `(strike, expiry_date, iv)`; no fitting required for a render |
| Horizon | **61 / 62 days**, in two blocks with a hole 2026-06-04 → 2026-08-23 — must render the hole as absence, never interpolate |
| ENH | none |
| Effort | ~1 day (rotatable 3-D render is the cost, not the data) |

### L11 · Five-axis positioning radar — **ABSENT**

| | |
|---|---|
| Axes | gamma (L1), vanna (L7), charm (L8), IV term (L9), pin (L12) |
| Horizon | inherits the **61/62-day** floor from vanna/charm |
| ENH | none — ADR-002 v2's "Positioning Landscape five scalars" is the nearest prior art and should be checked for overlap before filing |
| Effort | ~0.5 day, and it is **last** — it is a composition of five layers, three of which do not exist |

### L12 · Pin conviction — ranked candidates + HHI — **ABSENT**

| | |
|---|---|
| Source | `gex_strike_snapshots` — `gex_cr` per strike |
| Compute | rank by \|gex_cr\|; concentration = `max(abs(gex))/sum(abs(gex))` — **this formula already exists** as `hist_gamma_metrics.gamma_concentration`, filled full-window at S62 and noted scale-invariant |
| Horizon | 299 d |
| ENH | none, but the substrate is built — this is a read, not a compute |
| Effort | ~3 h |

### L13 · OI rotation since open — **ABSENT (live), 299 d (history)**

| | |
|---|---|
| Source | `option_chain_snapshots.oi_change`, or `oi` minus session-open `oi` per strike |
| Compute | per strike, added vs unwound since 09:15 |
| Horizon | live unaffected by retention; **historical rotation has a 14-day horizon by construction** — jobid 19 thins OCS to one 10:00 UTC row per day after 14 days (currently DISABLED, TD-S76-NEW-2) |
| Scaffold | `v_oi_prev_close_snapshots` exists (ADR-015 §F1) but **cannot prove absence** and is excluded by data-inventory rule 6 — do not build on it |
| Effort | ~4 h |

### L14 · 30-session net-gamma river — **ABSENT (panel), data 299 d**

| | |
|---|---|
| Source | `gamma_metrics.net_gex` daily aggregate, or `hist_gamma_metrics` (canonical historical gamma series, S62; `net_gex` **UNSCALED ×1e7**, `bar_ts` IST-as-UTC `:59`) |
| Compute | daily net GEX + dampening/amplifying sign, price threaded |
| Horizon | **299 d — ten times the 30 sessions Hedgewall shows** |
| Caution | the unit convention differs between `gamma_metrics` (Cr) and `hist_gamma_metrics` (unscaled). TD-S30-CANDIDATE-1 cost seven sessions to this exact class |
| Effort | ~4 h |

---

## 2.5 Beyond parity — measured additions from SpotGamma, Volland, SqueezeMetrics

These are **not** Hedgewall layers. They are features the three comparable US/global
terminals carry that Hedgewall does not, which MERDIAN's measured data supports.

**They do not enter the §3 build order.** Parity first, extensions after. Interleaving
them is how a scoped plan becomes a wish list.

### L15 · SpotGamma key-level set — folds into L3/L12

| level | definition | source | horizon | marginal effort |
|---|---|---|---|---|
| **Large Gamma Strike, ranked** | strikes ranked by gamma, "large gamma strike 1" strongest | GSS, `ORDER BY abs(gex_cr)` | 299 d | ~0 — L12's view, different sort |
| **Absolute Gamma Strike** | largest \|gamma\| irrespective of sign | GSS | 299 d | ~0 |
| **Hedge Wall** | the strike where the largest **change** in gamma is detected | Δ(`gamma_call`+`gamma_put`) between GSS cycles | 299 d | ~1 h, same pass as L3 |
| **Volatility Trigger™** | early signal that conditions are shifting toward a higher-volatility regime; distinct from the zero-gamma flip | GSS cumulative gamma | 299 d | second field in the L3 view |

### L16 · Implied 1-day / 5-day move — **the longest history on this document**

| | |
|---|---|
| Source | `volatility_snapshots.atm_iv_avg` — 46,853 rows, **2025-04-01 → present**, 100 % populated all 18 months, both symbols |
| Compute | ATM IV → σ√(t/252) → expected range at 1 σ |
| Horizon | **18 months** — longer than any other layer specced here |
| Caveat | the relation is **single-expiry and silently switches expiry class** (§1.1). Any series must partition on `expiry_type` or it mixes two instruments |
| Effort | ~2 h |

### L17 · Volland view architecture — presentation, not new data

- **Greek switcher × dim switcher** — gamma/vanna/charm crossed with by-strike/by-term.
  The **by-term** axis is the addition: gamma by expiry, not only by strike. 299 d for
  gamma, 61/62 d for vanna/charm. Changes how L1/L7/L8/L9 render; adds no layer.
- **Permissive-strike classification** — green strikes act as support below price or
  resistance above; red are permissive, where price should have no problem moving. A sign
  test on GSS against spot. ~1 h, and a genuinely different idea from anything in §2.
- **Dealer vega** — *"not necessarily immediately hedged... but it can be the first
  indication of dealer stress."* `option_chain_snapshots.vega`, **61/62 d**.
- **Expiry-week charm mode** — charm is the most volatile indicator as expiration
  approaches and is the driving greek for same-day expiry hedging. India's weekly
  expiries make this ~52 events/year per index. Gated on L7/L8.

### L18 · FII/DII participant positioning — **India-native, no US equivalent**

| | |
|---|---|
| What | SqueezeMetrics' DIX infers institutional positioning from dark-pool short-sale prints. **India publishes participant-wise OI directly.** MERDIAN reads the real thing where DIX approximates it |
| Source | `participant_oi_daily`, `fii_dii_cash_daily`, `v_participant_oi_latest` — **ENH-115 SHIPPED S63**, 270-day backfill, daily AWS cron |
| Status | built, surfaced only inside the ENH-116 ambient layer — **no first-class panel** |
| Effort | ~3 h to surface |

**§2.5 total ≈ 11 h**, on top of §3's ~5 days.

---

## 3. Build order

Ordered by value-per-hour, with dependencies respected.

| # | layer | effort | why here |
|---|---|---:|---|
| 1 | **L3 flip rebuild** | 0.5 d | It is live and wrong. Everything else can wait; a displayed wrong level cannot |
| 2 | **L9 IV term slope** | 3 h | Cheapest real read on the list, and it has 299 d of 2-point history |
| 3 | **L4+L5 walls** | 2 h | One view, two markers, 299 d |
| 4 | **L12 pin conviction** | 3 h | Formula already exists and is filled full-window |
| 5 | **L6 absolute-GEX leg** | 1 h | One column on a card that already renders |
| 6 | **L14 gamma river** | 4 h | 299 d available; watch the unit convention |
| 7 | **L13 OI rotation** | 4 h | Live is easy; historical is bounded at 14 d and that must be said on the panel |
| 8 | **L7+L8 vanna/charm** | 0.5 d | Needs the ENH-98 deferral lifted first — an operator decision |
| 9 | **L10 IV surface** | 1 d | 61/62 d with a rendered hole |
| 10 | **L11 radar** | 0.5 d | Composition; last by construction |

**Total ≈ 5 working days** of build, excluding the Marketview iteration cycles, which run
through the existing Lovable → GitHub → AWS pipeline (`ENH-110` Phase 1, 3-line redeploy).

The one-day figure that has been quoted in conversation appears nowhere in the registers
and is not supported by this breakdown. The only effort number in project knowledge is
`build_readiness` §2.3 — **34.4 hours serial** for a 299-day per-strike GEX *backfill*,
which is a different activity and is not on this list.

---

## 4. Decisions the operator must make before building

1. **Lift the ENH-98 deferral.** It is blocked on *"Phase 2 deployment plan commitment"*
   because vanna/charm had no Phase-1 consumer when it was written. Hedgewall parity is
   that consumer. Nothing in the data blocks it.
2. **Rule on `LONG_GAMMA`.** Dropping `flip_level` from `determine_regime` moves ~3 % of
   cycles. The `net_gex >= 0` suppression moves ~70 % and has never been measured as a
   gate. These are two decisions and must not be taken as one.
3. **Storage for second-order greeks** — columns on `gamma_metrics` versus a
   `greeks_l2_analytics` table. ADR-015's minimum-sufficient-statistic doctrine argues for
   the separate table.
4. **jobid 19.** Re-enabling it deletes the history L14 needs and caps L13's historical
   window at 14 days. `raw_ingest_log` growth is still unmeasured and is the stated
   prerequisite (TD-S76-NEW-2).
5. **Display doctrine.** ADR-017 and the S37 *"GEX is context, not gate"* ruling both hold.
   Every layer above ships **display-only**; none routes a trade.

---

## 5. What this spec does not cover

- **Correctness.** Every source claim here is presence, population and span. Nothing
  asserts that a stored value is right.
- **The 2026-06-04 → 2026-08-23 chain hole.** GSS covers it for gamma; HOCS and OCS do not
  cover it at all, so any delta-dependent layer renders it as absence.
- **Rendering effort.** The Lovable iteration count is not estimable from here; S39 took
  six turns for the first console.
- **Vendor re-purchase.** Out of scope. The GFDL delivery carried no greeks (§1, measured
  from file), so delta/theta/vega before 2026-03-16 cannot be recovered from that source.
- **HIRO-class order flow.** SpotGamma's HIRO *"measures the net delta, or directional
  exposure, being transferred to dealers in real time"* from trade-level tape with buy/sell
  classification. MERDIAN captures **5-minute OI snapshots, not trades**.
  `options_flow_snapshots` and `oi_change` are the nearest proxy and are orders of
  magnitude coarser. This is a data-acquisition gap, not a compute one, and **no layer in
  this document closes it.**
- **DIX-class dark-pool positioning.** SqueezeMetrics' Dark Index is built on dark-pool
  short-sale volume via FINRA ATS reporting. **India has no equivalent public feed.** L18
  is the India-native substitute, not a reconstruction.
- **Conjunction research.** Whether a recurring combination of two or more of these
  metrics precedes a sharp move is a **research question with a falsification protocol**,
  not a display layer. It is deliberately deferred until the layers above are built and
  rendered, so the search runs over quantities that have been measured and looked at.
  Pre-registration under ADR-009 — target, cells and success criterion written before the
  first query. ENH-97 is the standing evidence for what happens otherwise: the 4-way
  regime gate returned **chi-sq 1.56, p≈0.30 on 1,968 signals**, and the salvage test
  failed on power with a bootstrap CI spanning zero.

---

*Sources: measured live S78 (2026-09-14) unless cited. Prior art —
`build_readiness_2026-09-09.md` §§1–6; `MERDIAN_Data_Inventory.md` (S78);
`flip_audit_2026-09-08.md`; `data_inventory_2026-09-08.md` §6; ADR-002 v2, ADR-015,
ADR-017; ENH-80, ENH-81, ENH-98, ENH-110, ENH-116; TD-S58-NEW-1, TD-S35-NEW-2,
TD-S76-NEW-2.*
