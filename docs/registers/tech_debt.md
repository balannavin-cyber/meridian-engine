# MERDIAN Technical Debt Register

**Purpose:** A single living markdown file for *known broken-ish things* that aren't blocking but shouldn't be forgotten. This file fills the gap between:

- **C-N (critical)** in `merdian_reference.json` → must fix before next live session
- **ENH-N (enhancement)** in `Enhancement_Register.md` → forward-looking proposal, may never be built
- **Session-local tasks** in `session_log.md` → don't persist past today
- **Tech debt (this file)** → persistent, known, has a workaround, will be paid down when convenient

If an item doesn't fit those four buckets, it doesn't get tracked.

---

## How to use this file

1. **Add an item** when you discover a real issue mid-session that has a workaround and isn't blocking. Use the template below.
2. **Update an item** when the workaround changes, severity changes, or you learn more about root cause.
3. **Close an item** when fixed — move it to the `# Resolved (audit trail)` section at the bottom with the closing commit hash. Never delete.
4. **Promote** to C-N if it becomes blocking, or to ENH-N if it grows into a real enhancement.

---

## Severity scale

| Sev | Meaning | Response time |
|---|---|---|
| **S1** | Production-impacting workaround in place. Fix this sprint. | Within 5 sessions |
| **S2** | Non-blocking but degrades a real user-facing or research workflow. | Within 15 sessions |
| **S3** | Cosmetic, performance-tolerable, or affects only edge cases. | When convenient |
| **S4** | Anti-pattern flagged for future refactor. No active impact. | Aspirational |

---

## Item template

```markdown
### TD-<NNN> — <one-line title>

| | |
|---|---|
| **Severity** | S1 / S2 / S3 / S4 |
| **Discovered** | YYYY-MM-DD (session/appendix ref) |
| **Component** | <file path or table or system area> |
| **Symptom** | What you observe when this hits |
| **Root cause** | What we believe causes it (or "unknown") |
| **Workaround** | What is currently being done to live with it |
| **Proper fix** | What the real fix looks like |
| **Cost to fix** | <est sessions or hours> |
| **Blocked by** | <ENH-N, TD-N, or "nothing"> |
| **Owner check-in** | <date when last reviewed> |
```

---

## Active debt

> Items below are illustrative seeds based on the project state I've read.
> Audit and adjust before committing — replace with the real current state.

### TD-S66-NEW-1 (S1 priority) — `ingest_equity_eod_local.py` reads `DHAN_API_TOKEN` once at module load (L18 global) → a run that crosses a token rotation authenticates with a token that rotated underneath it and 401s the whole sweep

| Field | Value |
|---|---|
| **Priority** | S1 (this is the ROOT cause of the S66 breadth/DMA freeze — a load-time token capture strands the equity sweep silently). |
| **Discovered** | Session 66 (2026-07-09), diagnosing why ~91% of `breadth_indicators_daily` is stranded at 06-04. |
| **Symptom** | `breadth_ingest_state.last_status=PARTIAL_OK` at 11:58 with a wall of `DH-901` "access token invalid or expired" 401s, while the *same* `.env` token probed 200 on `/v2/marketfeed/ltp`, `/v2/optionchain/expirylist` AND `/v2/charts/historical` (RELIANCE candles through 07-08) minutes earlier and later. Token healthy; the failing run held a stale one. |
| **Root cause** | `DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN", "")` at module load (L18), used in the request header (L113). The token is captured once at import and never re-read; a long-lived run (or one that started before the 01:19/03:05 daily rotation) sends a token that has since rotated. The Dhan token/URL/refresh pipeline is otherwise HEALTHY — `pull_token_from_supabase.py` refreshes daily (probe 200, `.env` atomic-write + readback), `refresh_dhan_token.py` (03:05 self-mint) writes Supabase too. |
| **Fix** | Read the token at USE, not at import — pull from Supabase `system_config` (the source the probe trusts) or re-read `.env` per request cycle, so a mid-run rotation can't strand the sweep. This is the durable fix; every Dhan writer that reads a load-time `.env` global has the same latent bug. |
| **Workaround** | Re-run `ingest_equity_eod_local.py` after a token rotation (a fresh process reads the current `.env`); the manual 26-lap re-run this session cleared auth (0×401). |
| **Status** | OPEN (S66) — root-caused + reproduced; read-at-use fix carried to S67. |

### TD-S66-NEW-2 (S1 priority) — `build_daily_map` (`build_wcb_snapshot_local.py`) has no recency floor: its `>=`-max selection silently serves month-old per-ticker DMAs as "current" and reports 98.3% coverage over a 91%-stale table (violates ADR-018 D2)

| Field | Value |
|---|---|
| **Priority** | S1 (this is why the freeze stayed INVISIBLE — a stale-serving reader with a falsely-reassuring coverage number). |
| **Discovered** | Session 66 (2026-07-09). |
| **Symptom** | The Marketview WCB / %-above-DMA panel rendered `coverage 98.3%` and normal-looking `>10/20/40DMA` figures while ~1,211/1,383 constituents' DMAs were frozen at 2026-06-04. Tell in the data: constituent `above_10/20/40` flags computed on the 06-04 `prev_close`, not the live `last_price` (HDFCBANK `last_price 829.3` above all DMAs yet all flags `false` vs `prev_close 754.2`). |
| **Root cause** | `build_daily_map` keeps each ticker's row with the max `trade_date` (`if new_td >= existing_td`) with NO lower bound. If `breadth_indicators_daily` has no row past 06-04 for a ticker, the map serves the 06-04 row as "latest," so every downstream weighted-DMA stat is computed on stale rows — and the ticker still counts toward "coverage." ADR-018 D2 mandates a recency-floor guard on breadth readers so a silent stall self-flags STALE; this reader has none. |
| **Fix** | Add a recency floor: drop any ticker whose newest daily row is older than N trading days off the `breadth_indicators_daily` frontier into `missing_daily` (so the snapshot reports honest coverage and flags STALE) rather than silently weighting a month-old close. |
| **Workaround** | None; the panel is untrustworthy for the stale window. A/D breadth (tick-derived) is unaffected and remains live. |
| **Status** | OPEN (S66) — carried to S67. |

### TD-S66-NEW-3 (S1 priority) — `check_eod_coverage_freshness.py` (shipped S66, `5de5c85`) measures table-MAX trade_date, not per-ticker coverage % — it reads green over a table where 91% of tickers are a month stale

| Field | Value |
|---|---|
| **Priority** | S1 (the guard we just shipped has the wrong denominator for the S66 failure class). |
| **Discovered** | Session 66 (2026-07-09), immediately after shipping the S65-tuned guard. |
| **Symptom** | The tuned guard reads `breadth_indicators_daily` / `equity_eod` MAX trade_date (07-05/07-06, within the 3td lag tolerance → RESULT OK) while a coverage histogram shows 1,211/1,383 tickers stranded at 06-04. A table-max read cannot see a per-ticker coverage collapse. |
| **Root cause** | The S65 tune correctly fixed the denominator for a *uniform* freeze (whole-table max date) but the S66 freeze is a *per-ticker coverage* collapse — a partial-population failure the table-max metric is structurally blind to. |
| **Fix** | Add a per-ticker coverage dimension: fraction of the active universe whose newest `breadth_indicators_daily` row is within N trading days of the frontier; FAIL if that fraction < threshold. This is complementary to the shipped table-max/staleness checks, not a replacement. |
| **Workaround** | Run the coverage-bucket query manually (`CASE WHEN mx>=… THEN 'fresh' WHEN mx='2026-06-04' THEN 'stranded'`). |
| **Status** | OPEN (S66) — carried to S67; supersedes the "guard closes this class" assumption. |

### TD-S66-NEW-4 (S1 priority) — the per-ticker DMA builder that writes `breadth_indicators_daily` is frozen since 06-04 (distinct writer, NOT yet identified; NOT `ingest_equity_eod`)

| Field | Value |
|---|---|
| **Priority** | S1 (the ACTUAL Lens-2 unfreeze — re-fetching EOD candles does not touch this table). |
| **Discovered** | Session 66 (2026-07-09). |
| **Symptom** | For RELIANCE, `equity_eod` max = 07-06 but `breadth_indicators_daily` max = 06-04. Re-running `ingest_equity_eod_local.py` (which fetches EOD candles) 26× drained only ~49 of 1,260 stranded tickers — because the DMA table is written by a different step that has not run for the stranded set since 06-04. |
| **Root cause** | `equity_eod` (raw OHLC candles) and `breadth_indicators_daily` (per-ticker DMA10/20/40 + prev_close + above-flags) are DECOUPLED. `build_wcb_snapshot_local.py` reads `breadth_indicators_daily` (per-ticker via `ticker in (...)`), so Lens-2 stays frozen no matter how many EOD candle laps run. The writer that computes `breadth_indicators_daily` from `equity_eod` was NOT identified this session (the grep for its writer was not completed before the session halt). |
| **Fix** | Identify the `breadth_indicators_daily` per-ticker DMA writer (grep `~/meridian-engine/*.py` for insert/upsert into `breadth_indicators_daily`, excluding `build_wcb`), determine why it's dead since 06-04 (likely not cron'd on AWS, or died in the 06-04 window), revive it, and let it rebuild DMAs over the now-fresher `equity_eod` candles. |
| **Workaround** | None; Lens-2 / WCB DMA breadth is untrustworthy until this runs. |
| **Status** | OPEN (S66) — the primary S67 item. |

### TD-S66-NEW-5 (S2 priority) — `equity_eod` frontier stuck at 07-06 even for tickers the Dhan API serves through 07-08 (recent-day writes not extending max date)

| Field | Value |
|---|---|
| **Priority** | S2 (secondary to NEW-4; the raw candle layer isn't fully current either). |
| **Discovered** | Session 66 (2026-07-09). |
| **Symptom** | A direct POST to `/v2/charts/historical` returns RELIANCE candles through 07-08, and the 26-lap ingest re-run reported `candles_upserted` with `Failures 0` — yet `equity_eod` max for RELIANCE = 07-06. The stored frontier is not advancing to what the API serves. |
| **Root cause** | Not diagnosed (session halted before the universe-wide `equity_eod` frontier query — which errored on a hallucinated `trade_date` column name, `equity_eod` uses different column names). Candidate: the `DHAN_FROM_DAYS_BACK=220` window writes historical bars but the recent-end candle is being dropped, or the upsert isn't extending the max date. Loops back to this-morning's 07-03/07-06 lag thread but with the API now proven to have the data. |
| **Fix** | Confirm `equity_eod`'s actual column names (`information_schema`), then diagnose why the recent trading days aren't landing despite a 200 candle response. |
| **Workaround** | None yet. |
| **Status** | OPEN (S66) — carried to S67. |

### TD-S65-NEW-1 (S3 priority) — `check_eod_coverage_freshness.py` EOD-coverage guard mis-tuned (denominator = nominal ~1,385 universe over a 5-day window → `/1` false-OK); should be the active-universe / latest-EOD-date ticker count (~1,159) measured off the last *trading* day with a ~3-day Dhan-lag tolerance

| Field | Value |
|---|---|
| **Priority** | S3 (guard-correctness, display-not-gate — the ingest is correct; only the freshness check mis-reports). |
| **Discovered** | Session 65 (2026-07-07), while diagnosing why 07-03/07-06 were absent from `equity_eod`. |
| **Symptom** | The coverage/freshness guard reported a `/1` false-OK: it divided against a mis-set denominator (the nominal ~1,385 universe) and measured staleness over a ~5-day window, so it neither caught a real multi-day freeze nor tolerated Dhan's normal 1–3-day publish-lag. |
| **Root cause** | The denominator and staleness window were guessed (~1,385 / 5 days). The *achievable* universe ceiling is ~**1,159 active** (the DMA layer rebuilt clean at 100% of active to 07-02); `COMPLETE_EOD_THRESHOLD_PCT=95` is correct because it measures against the active universe. Separately, the 07-03/07-06 `equity_eod` hole is **Dhan-side EOD publish-lag, not a bug** — `compute_date_window()` is correct (T−1 lookback `to = today−1`, `from = to−220`; on 07-07 the window includes 07-03/07-06; no lower-bound pin, no cursor exclusion) and the hole self-heals on the next EOD run. |
| **Fix (teed up, not finalized)** | Tune `check_eod_coverage_freshness.py`: denominator = the active-universe / latest-EOD-date ticker count (~1,159, read live — not a hard-coded 1,385); measure staleness off the last *trading* day; set tolerance to ~3 days so it swallows Dhan's normal publish-lag but still fires on a genuine multi-day freeze. Replaces the 1,385/5-day guesses that produced the `/1` false-OK. |
| **Workaround** | None needed — the ingest (`compute_date_window` + the EOD writer) is correct; the guard only mis-reports. The 07-03/07-06 hole self-heals on the next `MERDIAN_EOD` 16:10 cron run or a manual sweep. |
| **Status** | CLOSED (S66, `5de5c85`) — guard tuned (live ~1,159 ceiling / last-settled-trading-day / 3td Dhan-lag / fail-loud on unresolvable denominator) + proven green on live 07-08. NOTE: the shipped guard reads table-MAX not per-ticker coverage, so it is blind to the S66 per-ticker DMA freeze — that gap is TD-S66-NEW-3. |

### TD-S62-NEW (S2 priority) — SENSEX `compute_flip_level` resolves to a spurious deep-tail flip (~−6.75%/−7.11%) under NEGATIVE_γ; StockMojo parity isolates it as the sole outlier — RESOLVED (S63, `dc63bb3`)

| Field | Value |
|---|---|
| **Severity** | S2 (a headline dashboard number is materially wrong on short-γ SENSEX boards; misleading, not a data-corruption or pipeline break) |
| **Filed** | 2026-07-01 (Session 62) |
| **Component** | `compute_gamma_metrics_local.py::compute_flip_level` (ATM-outward cumulative-GEX walk) |
| **Symptom** | On the 2026-07-02-eve monthly SENSEX board (NEGATIVE_γ), the live dash showed `flip_level` **71,754.95 (−6.75% from spot)** at 10:57 and **71,529.03 (−7.11%)** at 14:16 — ~5,000 pts below spot (~76,850). StockMojo (independent GEX engine) put the real **Gamma Flip at 76,847** / **Net-GEX-Cross at 76,812**, i.e. near spot. |
| **Cross-engine parity (isolates the bug)** | Every OTHER reading matches StockMojo exactly at the same timestamps: regime NEGATIVE_γ (agree); accel zone **76,300–76,900** (exact); strongest amplify **76,500** (exact); call-wall / max-γ **77,000–77,500** (same cluster; MERDIAN names 77,500, StockMojo Call Wall 77,000 — both peaks inside the one long-γ wall, immaterial). The flip is the **sole** divergent field → confirmed MERDIAN-side bug, not data/chain/regime. |
| **Root cause** | In a NEGATIVE_γ regime the near-spot region is a **uniform short-gamma pit** (76,300–76,900 all negative) with no internal zero-crossing; the only long-γ wall (77,000+) sits **above** spot. `compute_flip_level` walks outward from ATM and returns the crossing nearest spot, but with no near crossing on either side it **falls through to a spurious deep-tail zero (~71,500)** far below, instead of the operative pit→wall boundary at 77,000. Deterministic (recomputes wrong every cycle; both timestamps ~5,300 pts low). Confirmed by reading the walk logic + the StockMojo per-strike bar chart (red pit 76,200–76,900, green wall 77,000+, curve crosses zero ~76,850). |
| **Impact** | Display-only today (GEX-as-context-not-gate; flip does not route trades), but a −6.75% flip presented as a precise level is actively misleading on exactly the short-γ boards where break-direction matters most. Related in kind to the S41/2026-05-08 deep-strike flip regression (single bad far strike anchoring the walk) — same failure family, different trigger. |
| **Workaround** | Read the flip skeptically on NEGATIVE_γ boards; trust StockMojo / the near-spot pit→wall structure over the emitted far number until fixed. |
| **Proper fix** | Two-part: (a) **near-spot sign-change walk** (StockMojo-style — scan outward for the first cumulative-GEX sign change on each side, take the nearest; should catch the 77,000 wall above spot); (b) a **"flip ill-defined under short-γ" display guard** — when regime is NEGATIVE_γ and no clean near-spot crossing exists, label/suppress rather than emit a far actionable level (e.g. "flip: ill-defined (short-γ; wall 77,000 above)"). Per-strike arithmetic confirmation (which deep strike the walk latches onto) deferred until after the SENSEX backfill (now complete) so the DB is not queried mid-write. |
| **Cost to fix** | ~1 session (walk rewrite + guard + cross-symbol re-validation; the S37/ENH-81 flip family and the S41 deep-strike guard are prior art). |
| **Related** | S41 cross-vendor StockMojo note (flip_level cumulative-zero vs per-strike sign-change); 2026-05-08 deep-strike flip regression; GEX-as-context-not-gate (ADR-002 v2 / S37); ENH-116 (the ambient layer would label short-γ boards as expansion-favored, pin/flip unreliable). |
| **Resolution** | **RESOLVED S63, commit `dc63bb3`** (`MERDIAN: [FIX] TD-S62-NEW regime-conditional compute_flip_level`). Deployed to AWS production: the ATM-outward walk now does a **near-spot sign-change scan** (takes the first cumulative-GEX sign change on each side, nearest spot — catches the 77,000 pit→wall boundary above spot) plus a **short-γ display guard** (under NEGATIVE_γ with no clean near-spot crossing, the flip is labelled ill-defined rather than emitting a spurious deep-tail level). SENSEX flip now resolves near-spot; **StockMojo cross-engine parity confirms** (the flip was the sole divergent field, all others already matched). Per-strike arithmetic confirmation was the deferred vehicle; the parity + deployment close the item. |

### TD-S62-NEW-2 (S3 priority) — SENSEX historical `gamma_concentration` unfilled for 2026-01-19 (SSLError mid-solve during the full-window backfill); one-line resume filed

**RESOLVED Session 64 (2026-07-04).** The operator ran the one-line resume `python run_fullwindow.py --symbol SENSEX --months 2026-01`; SENSEX 2026-01-19 `gamma_concentration` is now filled full-window — **375/375 bars, 0 null, concentration 0.0563–0.1136** (verified against the live `hist_gamma_metrics` row). The full-window historical gamma substrate is COMPLETE for both symbols with no remaining gaps; the ENH-116 expiry-memory SENSEX-backfill precondition is fully clear (not just “close enough”). Kept in place per the S63 RESOLVED-in-place precedent; nothing to re-run.

| Field | Value |
|---|---|
| **Severity** | S3 (a single missing day in a completed full-window backfill; trivially resumable) |
| **Filed** | 2026-07-01 (Session 62) |
| **Component** | `run_fullwindow.py` / `backfill_hist_greeks.py` (SENSEX 2026-01); `hist_gamma_metrics.gamma_concentration` |
| **Symptom** | During the ~19h SENSEX full-window run, **2026-01-19 hit `SSLError: HTTPSConnectionPool(host='…supabase.co') Max retries`** mid-solve (a transient Supabase connection drop). The run logged the ERROR and **continued** to 2026-01-20 onward (by design — a single-day network blip should not abort a 12-month job), so 2026-01-19 has no `DONE` log row and its per-strike sidecar + `gamma_concentration` are unfilled. All other SENSEX days completed (`ALL DONE symbol=SENSEX total 1145.4 min`). |
| **Root cause** | Transient TLS/connection drop to Supabase during one day's solve; not a data or logic defect. The wrapper's per-day resume granularity means the loss is bounded to exactly that one day. |
| **Impact** | One trading day of SENSEX `gamma_concentration` is NULL where it should be filled (2026-01-19 was a non-expiry Monday). Negligible for aggregate/regime work; matters only if that specific day is analyzed. |
| **Workaround** | Treat SENSEX historical concentration as complete except 2026-01-19 until resumed. |
| **Proper fix** | One-line resume (skips the 20 already-DONE Jan days, solves+fills only 2026-01-19): `python run_fullwindow.py --symbol SENSEX --months 2026-01`. Run when not mid-live-feed / not during a doc-close. |
| **Cost to fix** | ~2 minutes (single-day recompute). |
| **Related** | TD-S58-NEW-1 (RESOLVED — the parent backfill); `run_fullwindow.py` resume design; the deliberate loud-log-but-continue-on-transient-blip behaviour. |

### TD-S61-NEW-1 (S2 priority) — `build_trade_signal_local.py::_fetch_options_flow()` had no recency floor → ENH-02/04 confidence modifiers fired off a ~24-day-stale row; CLOSED

| Field | Value |
|---|---|
| **Severity** | S2 (live confidence modifiers running on stale data; no crash, silent mis-scoring) |
| **Filed / Closed** | 2026-06-27 (Session 61) — NEW + CLOSED same session (commits `8ddbc78` + `d16986c`) |
| **Component** | `build_trade_signal_local.py::_fetch_options_flow()` reading `options_flow_snapshots` |
| **Symptom** | `compute_options_flow_local.py` was orphaned at the S49 migration (never re-homed in the AWS orchestrator), so `options_flow_snapshots` stopped advancing; the newest row was ~24 days old. `_fetch_options_flow()` read it with no freshness guard, so the ENH-02/04 modifiers (±3/4/5 on `pcr_regime`/`skew_regime`/`flow_regime`) were applied to every live BUY signal off that stale row. |
| **Root cause** | Two-part: (a) the writer was orphaned (S49 migration-scope gap, same family as the ADR-019 orphans); (b) the reader carried no ADR-018 D2 recency floor. |
| **Fix** | (a) `compute_options_flow_local.py` re-homed into `run_merdian_shadow_runner_aws.py execute_pipeline` at the canonical options_flow slot; (b) ADR-018 D2 floor added to `_fetch_options_flow()` — `MERDIAN_FLOW_RECENCY_FLOOR_MIN` (default 15 min); stale → modifiers suppressed. Commits `8ddbc78` + `d16986c` (canon-v3, `_PRE_S61`). |
| **Related** | ADR-018 D2 (recency-floor on all signal readers); ADR-019 (S49 migration orphans); ENH-02; TD-S57-NEW-2 (the feed-side floor analogue). |

### TD-S61-NEW-2 (S3 priority) — hist bar timestamp pairing: the −5h30m futures shift was wrong; both bar tables are IST-clock-as-UTC → ZERO shift; CLOSED

| Field | Value |
|---|---|
| **Severity** | S3 (research-substrate correctness; surfaced + fixed during the ENH-07 B backfill, no production impact) |
| **Filed / Closed** | 2026-06-27 (Session 61) — NEW + CLOSED same session |
| **Component** | `hist_future_bars_1m` × `hist_spot_bars_1m` pairing in `backfill_basis_context.py` |
| **Symptom** | Pairing futures bars to spot bars with the assumed −5h30m futures→true-UTC shift yielded only ~14% matches (~269 pairs/day). |
| **Root cause** | The −5h30m assumption (carried from the TD-087 vendor-chain note) was wrong for these two tables. A UTC-forced diagnostic showed BOTH tables store **IST-clock-as-UTC** (hours 9–15) and are mutually consistent, so no shift is needed. |
| **Fix** | Pair on the raw bar_ts with **zero shift** → ~99% match (~376 pairs/day, e.g. 1,879 over 5 days). Read-time only; source unchanged. Also catalogued the per-symbol `contract_series` wart (NIFTY 1/2/3 expiry-NULL vs SENSEX 0 expiry-populated) — handled in the front-month selector. |
| **Related** | TD-087 (the −5h30m vendor-chain note this refines for bar-pairing); ENH-07 B; CLAUDE.md v1.38 settled bullet. |

### TD-S61-NEW-3 (S4 priority) — `merdian_reference.json` vestigial `_meta` header stale (v38/S55) alongside the live top-level header; resynced

| Field | Value |
|---|---|
| **Severity** | S4 (cosmetic/confusing; the live top-level header `version`/`last_updated_session`/`change_log` is correct and current) |
| **Filed** | 2026-06-27 (Session 61) |
| **Component** | `merdian_reference.json` `_meta` object |
| **Symptom** | The file has TWO header blocks: the maintained top-level (`version`, `last_updated_session`, `change_log`) and a vestigial `_meta` (`version`, `last_updated`, `_meta.change_log`) that stopped being updated ~S55 (read v38/S55 while the body was current at v39/S60). A reader inspecting `_meta` alone would mis-judge the file 5 sessions stale. |
| **Fix** | `_meta.version` / `_meta.last_updated_by_session` resynced to the top-level at the S61 close. Proper fix (deferred): retire the duplicate `_meta` header or generate it from the top-level. |
| **Related** | Doc Protocol v4 Rule 12 (doc re-upload / drift hygiene). |

### TD-S60-NEW-1 (S2 priority) — Marketview spot header showed phantom SENSEX +4.34%/+3228pts; root cause = stalled `market_spot_session_markers` writer (21-day-stale prev_close baseline); CLOSED

| | |
|---|---|
| **Severity** | S2 (false-but-plausible headline number on the live dashboard; DB/engine clean) |
| **Discovered** | 2026-06-26 (Session 60) |
| **Component** | `build_market_spot_session_markers.py` (writer); `meridian-connect` `pages/Marketview.tsx:716` `prev_close_spot` via `lib/queries.ts useSpotMarker` → table `market_spot_session_markers` (frontend reader) |
| **Symptom** | Header read SENSEX +4.34% (+3228 pts) on a real ~+0.76% day; the % baseline was a frozen `prev_close_spot=74346.17` from 2026-06-04 (verified real prev close 76,991.22). |
| **Root cause** | The marker writer stalled after 2026-06-04 (unscheduled post-AWS-migration). The frontend reads the newest `market_spot_session_markers` row's `prev_close_spot`; with no fresh marker since 06-04 it read a 21-day-stale baseline. Recurring C-09/ADR-001 shape — a stale reference silently invalidating correct data. |
| **Workaround / Fix** | CLOSED. (1) None-guard on postmarket-ts deref (`4f676e1`); (2) backfilled markers 06-05→06-25; (3) cron added `40 10 * * 1-5` (16:10 IST, house-style no-flock); (4) marker freshness guard added to `scripts/eod_health_check.py` (`5066d81`, proven OK 06-25 / FAIL on an empty date); (5) `get_open_0915` window widened 09:15:00–09:18:00 for dhan end-of-minute stamping + `get_prev_close_spot` walks back up to 7 days (Monday-reads-Sunday bug), `c9c2ab3`. |
| **Proper fix** | Done. Durability now guarded by the freshness check (FAILs if the baseline goes stale again). |
| **Cost to fix** | ~1 session (closed same session). |
| **Blocked by** | nothing. |
| **Related** | C-09 / ADR-001 (stale-reference family); TD-S59-NEW-1 (same family, different path — breadth prev-close); ENH-SDM (marker is preserved on holidays, derived compute is not — see TD-S60-NEW-4). |

### TD-S60-NEW-2 (S1 priority) — `trading_calendar.json` held 2-of-15 NSE-2026 equity holidays (one misdated) → `trading_calendar` mismarked every holiday `is_open=true` since ~April → pipeline ran the full compute chain on Muharram; CLOSED AT SOURCE + orchestrator gate belt

| | |
|---|---|
| **Severity** | S1 (the holiday trust-anchor for the whole system was wrong; every gate fail-opens on it, so all gates were silently defeated; plausible-but-invalid rows written into production compute tables on every weekday holiday). |
| **Discovered** | 2026-06-26 (Session 60) |
| **Component** | `trading_calendar.json` (source of truth, read by V18E rule engine `trading_calendar.py`); `trading_calendar` table (seeded by `seed_trading_calendar.py`); `run_merdian_shadow_runner_aws.py` (ran with no holiday gate). |
| **Symptom** | Full compute chain (gamma→volatility→momentum→WCB→market_state→SDM→trade_signal) ran on Muharram 2026-06-26 (`PIPELINE COMPLETE` 03:51 UTC, 7 gamma rows/symbol) on a closed market. `SELECT is_open FROM trading_calendar WHERE trade_date='2026-06-26'` = true. |
| **Root cause** | `trading_calendar.json` `holidays` list held only 2 of 15 NSE-2026 equity holidays — and one was misdated (Good Friday as 04-18 vs real 04-03). So `get_session_config_for_date` correctly closed weekends (Rule 1) but every weekday holiday returned `is_open=true`. The table inherited it; every holiday gate (incl. the proven marker-writer gate) trusted it and passed on closed days. Verbatim C-09/ADR-001 at the trust-anchor level. |
| **Workaround / Fix** | CLOSED. Regenerated `trading_calendar.json` to the 15 official NSE-2026 equity holidays (verified via web_fetch of the official Zerodha/NSE holiday calendar: 01-15, 01-26, 03-03, 03-26, 03-31, 04-03, 04-14, 05-01, 05-28, 06-26, 09-14, 10-02, 10-20, 11-10, 11-24; + Nov-8 Muhurat special session; dropped 2025 + settlement/weekend contaminants), commit `bafddc2`. Reseeded `seed_trading_calendar.py --days 220`; explicit UPDATE flipped the stale `is_open=true` holiday rows to false (seeder only writes open days, can't self-correct false-positives). Verified 06-26 closed / 06-29 (Mon) open. BELT: orchestrator holiday gate added (`af74d0c`), proven live firing on Muharram; then cut over to the shared helper (TD-S60-NEW-3). |
| **Proper fix** | Done at source. `seed_trading_calendar.py` now propagates the correct JSON forward; the gate guards against a future recurrence. |
| **Cost to fix** | ~1 session (closed same session). |
| **Blocked by** | nothing. |
| **Related** | C-09 / ADR-001; TD-S60-NEW-3 (shared gate helper); TD-S60-NEW-4 (holiday-noise repair); CLAUDE.md Rule 18 (calendar trust-anchor, S60). |

### TD-S60-NEW-3 (S2 priority) — no shared holiday-gate helper (~30 entrypoints each roll their own `is_open` check); BUILT `core/trading_calendar_gate.py` + orchestrator CUT OVER; ~28 migrations remain

| | |
|---|---|
| **Severity** | S2 (duplication/portability debt; the orchestrator gap let TD-S60-NEW-2 happen; one wrong inline copy can silently fail-open). |
| **Discovered** | 2026-06-26 (Session 60) |
| **Component** | `core/trading_calendar_gate.py` (NEW); `run_merdian_shadow_runner_aws.py` (cut over); ~28 other entrypoints with bespoke inline gates (+ archaeology `fix_capture_spot_holiday_gate.py`, `fix_merdian_start_calendar.py`). |
| **Symptom** | Holiday gating was added piecemeal entrypoint-by-entrypoint as each was caught firing on a holiday; the orchestrator never got its turn; ~30 scripts each carry their own `trading_calendar` check. |
| **Root cause** | No single shared gate. v1 of the helper (commit `2d1375c`) routed through `core.supabase_client`/`core.config.get_settings()` and silently fail-opened on AWS (smoke-test F/F/F caught it — surfaced TD-S60-NEW-5). |
| **Workaround / Fix** | PARTIAL (built + orchestrator cut over). v2 (`3b3b8ee`) is self-sufficient: own `load_dotenv()` + raw `requests` + `os.getenv`, bypassing `core.config`; fail-open at every branch; smoke-tested F/T/F (06-26 closed, 06-29 open, 06-26 closed) with no fail-open warnings. Exposes `is_trading_day_today()`, `is_trading_day(iso)`, `assert_trading_day_or_exit(log=None)`. Orchestrator cut over (`38a82ff`, −36/+2 lines) and re-proven firing on Muharram via the helper. Marker writer deliberately left on its own working inline gate. |
| **Proper fix** | Migrate the remaining ~28 bespoke gates onto the helper incrementally, each with its own test (a Friday big-bang over 30 gates is the Monday-failure risk). |
| **Cost to fix** | ~2-3 sessions for the full migration sweep (incremental). |
| **Blocked by** | nothing (helper is live). TD-S60-NEW-5 (`core.config` path) should be fixed before any gate is allowed to route through `core.config`. |
| **Related** | TD-S60-NEW-2 (the gap this closes); TD-S60-NEW-5 (why v2 bypasses core.config); CLAUDE.md Rule 18 (import the helper, don't roll inline). |

### TD-S60-NEW-4 (S2 priority) — holiday-noise compute rows on 2026-06-26 (pre-gate + SDM-test runs); CLOSED via scoped single-date DELETE

| | |
|---|---|
| **Severity** | S2 (plausible-but-invalid rows in production compute tables on a closed day; would pollute any cohort/backtest not holiday-filtered, including ENH-SDM's forward cohort baseline). |
| **Discovered** | 2026-06-26 (Session 60) |
| **Component** | `gamma_metrics`, `market_state_snapshots`, `volatility_snapshots`, `momentum_snapshots`, `signal_snapshots`, `structural_divergence_snapshots`. |
| **Symptom** | Compute rows written on Muharram (the calendar/gate bug). Per-date probe proved ALL contaminated rows were on 2026-06-26 only — no earlier holiday carried rows (the pipeline predates running this loudly), no real trading day leaked. |
| **Root cause** | TD-S60-NEW-2 (no holiday gate over a wrong calendar) let the chain run on the holiday. |
| **Workaround / Fix** | CLOSED. Scoped single-date DELETE (operator-approved counts: gamma 30, market_state 30, volatility 30, momentum 29, signal 34, structural_divergence 16; RETURNING matched exactly), verified 0 remaining. `market_spot_snapshots` (0 rows — holiday feed correctly didn't capture; the rows seen earlier in-session were 06-25 data, 376/symbol) and `market_spot_session_markers` (2 rows) legitimately preserved: capture on a holiday is fine, derived compute is not. |
| **Proper fix** | Done. The gate (TD-S60-NEW-2/3) prevents recurrence. |
| **Cost to fix** | ~0.5 session (closed same session). |
| **Blocked by** | nothing. |
| **Related** | TD-S60-NEW-2/3 (gate that prevents recurrence); ENH-SDM (cohort starts clean Monday). Note for backlog: ~8 past 2026 weekday holidays (Apr–Jun) ran the chain while the calendar was wrong — those older cohorts should be filtered against the corrected calendar before use (no rows existed for them in the compute tables probed this session, but any future backfill spanning them must filter). |

### TD-S60-NEW-5 (S2 priority) — `core/config.py` hardcodes Windows `BASE_DIR = C:\GammaEnginePython`; loads `.env` from a path that doesn't exist on AWS; FILED

| | |
|---|---|
| **Severity** | S2 (latent portability landmine; masked today because callers self-load or export env, but any clean `core.config`-routed invocation on AWS raises). |
| **Discovered** | 2026-06-26 (Session 60, during the TD-S60-NEW-3 helper smoke-test) |
| **Component** | `core/config.py` — `BASE_DIR = Path(r"C:\GammaEnginePython")`; `ENV_FILE = BASE_DIR / ".env"`; `load_dotenv(ENV_FILE)` is a no-op on AWS. |
| **Symptom** | `get_settings()` raises `Missing required environment variable: SUPABASE_URL` on a clean AWS invocation (proven: the v1 gate via `SupabaseClient` fail-opened F/F/F because `get_settings()` found no creds). Every `core.config`/`SupabaseClient`-routed script on AWS is silently dependent on env being loaded by some other prior `load_dotenv()`. |
| **Root cause** | Hardcoded Windows path in `core/config.py`. |
| **Workaround** | Scripts self-load `.env` (`load_dotenv()`) or rely on exported env; the S60 gate helper deliberately bypasses `core.config` for exactly this reason. |
| **Proper fix** | Derive `BASE_DIR` from `__file__` (repo root relative to `core/`), not a hardcoded OS path. |
| **Cost to fix** | ~30 min, but it's load-bearing (used everywhere) so it needs a careful test pass — not a Friday change. |
| **Blocked by** | nothing. |
| **Related** | TD-S60-NEW-3 (surfaced it; the gate helper bypasses core.config because of it). |


### TD-S59-NEW-1 (S1 priority) — breadth read BULLISH 882/428 on a 0.37-A/D down day; root cause = frozen `equity_intraday_last` (missing AWS cron); FIX APPLIED + guarded

| Field | Value |
|---|---|
| **Severity** | S1 (production-impacting: breadth card was directionally inverted on a hard down day; operator is the integration layer) |
| **Filed** | 2026-06-24 (Session 59) |
| **Status** | **FIX APPLIED + GUARDED 2026-06-24.** Live-verify pending on next directional session. |
| **Component** | `equity_intraday_last` (prev-close reference; refreshed by `refresh_equity_intraday_last.py`, MERDIAN AWS, Kite `ohlc()`) → `ingest_breadth_from_ticks.py` → `market_breadth_intraday` + `breadth_intraday_history` → Marketview breadth card, `build_market_state_snapshot_local.py`, signal builder |
| **Symptom** | 23-Jun (down day, NIFTY −1.1%) `market_breadth_intraday` read advances ~882 / declines ~428, score ~34, BULLISH all session, never flipped. VRD intraday A/D at the same close: 534 / 1,437, A/D 0.37. `cron.log` looked healthy (1,384 prev-closes matched) — writer "succeeded" against stale values. |
| **Root cause** | **CONFIRMED: stale prev-close reference caused by a MISSING AWS cron.** `diagnose_breadth_correctness.py` Part A: newest `equity_intraday_last.ts` was 2026-05-20T03:35 UTC, bulk at 2026-02-22 — refresh column frozen ~5 weeks. `crontab -l \| grep refresh_equity_intraday_last` returned EMPTY — the `35 3 * * 1-5` refresher line was never carried onto the AWS-only host. Breadth compared today's LTPs against a months-old baseline below current levels → most names mark "advancing" regardless of direction → permanent bullish skew, inverted on down days. **Verbatim re-run of C-09 / ADR-001** (Session 7); `runbook_update_kite_flow.md` pre-documents it. |
| **Candidates ruled out** | #2 coverage — NOT the cause (diagnostic's initial 0/1385 was a bare-`symbol` vs `NSE:`-prefixed `ticker` key artifact; writer matched 1,384/1,385; `norm_sym()` fix → 1385/1385). #3 epsilon / #4 score↔count — moot once the baseline is months stale. |
| **Relationship to feed outage** | Independent second defect. TD-S48-NEW-1 / S57–S58 fixed the live-tick input (`market_ticks`). `equity_intraday_last` is the *other* breadth input and was dead since 2026-05-20 — which is why 23-Jun read BULLISH despite the S58-verified-live feed. |
| **Column-semantics learning** | `equity_intraday_last` has BOTH `ts` and `created_at`. The refresher upserts `ON CONFLICT DO UPDATE` touching `last_price` + **`ts`**; `created_at` is row-birth (`DEFAULT now()`, never moves on upsert). **Freshness MUST be measured on `ts`, not `created_at`** (verified S59 by direct read: `ts` newest = today, `created_at` newest = 2026-05-20). Codified Assumption Register §D.25. |
| **Fix applied (2026-06-24)** | (1) Re-added cron on MERDIAN AWS: `35 3 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 refresh_equity_intraday_last.py >> logs/refresh_equity_intraday_last.log 2>&1` (UTC slot = 09:05 IST, fires AFTER the 03:00 UTC MALPHA→AWS token sync). Cron verified present and **self-fired 03:35 UTC 06-24** (maiden timed run confirmed via `eod_health_check --date 2026-06-24` REFERENCE FRESHNESS = OK, refreshed 03:35 UTC). (2) Manual repopulate post-08:30 IST: `kite.profile()` OK OV0782, 1,316–1,317 rows written, no auth error. (3) Verified by direct read: `equity_intraday_last.ts` newest = today. The 05:10 IST first-attempt auth failure was an off-hours expired token (before the 03:00 UTC sync), proven by the 05:16 success. |
| **Impact** | Breadth card + all breadth-derived reads inverted/untrustworthy ~2026-05-20 → 2026-06-24. ENH-SDM **P2 compute writer is gamma-centric** (gamma_metrics + spot bars) → not hard-gated; interpretation must not lean on breadth until live-verified. |
| **Durability guard** | `scripts/eod_health_check.py` REFERENCE FRESHNESS section added (commit `6b58587`): checks `equity_intraday_last.ts` was refreshed for the audited `--date`, FAIL if not (anchored to date, not wall-clock). Proven live on `--date 2026-06-22` → FAIL STALE BASELINE; `--date 2026-06-23/24` → OK. Closes the silent-5-week-freeze hole. |
| **Proper-fix tail (open)** | (a) 68-row `ohlc()` tail — refresh resolves 1,317/1,385; ~68 names Kite `ohlc()` doesn't return still carry 2026-02-22 rows (e.g. `NSE:ROADSTAR` NULL `last_price` — delisted/renamed); chase via `breadth_universe_members.nse_symbol/nse_status`. (b) exec_log FAILURE path broken — see TD-S59-NEW-2. |
| **Live-verify** | Next directional session: compare the breadth card to VRD on a real move. If it tracks → RESOLVED. |
| **Related** | C-09 / ADR-001; `runbook_update_kite_flow.md`; TD-S48-NEW-1 (feed liveness — distinct input); TD-S57-NEW-2 / ADR-018 D2 (recency-floor for the feed, not the reference table); TD-S59-NEW-2; ENH-SDM. |

### TD-S59-NEW-2 (S3 priority) — `refresh_equity_intraday_last.py` FAILURE-path exec_log write violates `chk_exit_reason_valid` → failures are invisible; CLOSED

> **CLOSED 2026-06-27 (S61, commit `3533d22`).** The operator's #1. A module-level `_classify_exit_reason(ok, err)` now maps the FAILURE branch to a valid `chk_exit_reason_valid` member — `TOKEN_EXPIRED` on `api_key`/`access_token` errors, else `DATA_ERROR` — with the free-text detail routed to `error_message`; the `eod_health_check` negative-hours cosmetic was folded in. canon-v3, `_PRE_S61`. This closes the silent-failure hole that masked the S59 5-week breadth freeze (no exec_log row was being written on failure).

| Field | Value |
|---|---|
| **Severity** | S3 (telemetry defect; no active data impact, but it masked TD-S59-NEW-1 for ~5 weeks) |
| **Filed** | 2026-06-24 (Session 59) |
| **Status** | **CLOSED 2026-06-27 (S61, `3533d22`)** — module-level `_classify_exit_reason(ok, err)` → `TOKEN_EXPIRED`/`DATA_ERROR`, detail → `error_message`; `eod_health_check` negative-hours folded in. canon-v3, `_PRE_S61`. |
| **Component** | `refresh_equity_intraday_last.py` exec_log write on the FAILURE branch → `script_execution_log` (constraint `chk_exit_reason_valid`) |
| **Symptom** | On the 05:10 IST manual run (expired-token failure), the exec_log INSERT was rejected: `new row for relation "script_execution_log" violates check constraint "chk_exit_reason_valid" (23514)`. The failing row carried `exit_reason = "prev_close refresh via Kite ohlc()"` / error `Incorrect api_key or access_token.` — `exit_reason` not in the constraint's closed set, so the FAILURE row never persists. |
| **Root cause** | The script writes a free-text string into `exit_reason` on failure rather than one of the constraint's allowed enum values (same class as TD-083 / TD-NEW-J). Success path uses a valid value; failure path does not. |
| **Impact** | Failures of this cron leave NO exec_log row. Combined with no alerting on this job, that is exactly why the 2026-05-20→2026-06-24 freeze ran silently — there was nothing to detect. |
| **Workaround** | None — failures are silent by construction. |
| **Proper fix** | Map the FAILURE branch's `exit_reason` to a valid member of the `chk_exit_reason_valid` set (read the constraint definition first; do not guess the allowed values), keeping the free-text detail in `error_message`. ~15 min. Bundle with the TD-S59-NEW-1 freshness guard already shipped. Also fold the `eod_health_check` negative-hours cosmetic (when newest `ts` is after the audited date the FAIL line prints "−N h before session"). |
| **Related** | TD-S59-NEW-1 (the silent freeze this masked); TD-083 / TD-NEW-J (same exit_reason closed-set class); TD-NEW-B (job-failure alerting gap). |

### TD-S59-NEW-3 (S2 priority) — daily ICT PDL silently dropped on down-close days (fresh PDH/PDL proximity-filtered against prior-day close); FIXED

| Field | Value |
|---|---|
| **Severity** | S2 (wrong/missing ICT level on the chart — degrades a real decision surface; not a capture/correctness outage) |
| **Filed** | 2026-06-24 (Session 59) |
| **Status** | **FIXED 2026-06-24** (commit `2b40a4b`). Verified: D PDL now ACTIVE for 06-24. |
| **Component** | `build_ict_htf_zones.py` daily write path (call site ~804–846) — `filter_breached_zones()` applied to the freshly-built daily PDH/PDL pair (Local job, Windows Task Scheduler) |
| **Symptom** | Right pane (ICT-only, PDH/PDL toggle ON) showed PDH but no PDL for NIFTY 06-24. `ict_htf_zones` had `D PDH 24123-24143 ACTIVE` but no `D PDL` row; W PDH present, W PDL absent — PDH survives, PDL culled, asymmetrically. |
| **Root cause** | `filter_breached_zones` computes `current_spot = daily_ohlcv[last_date]["close"]`. On the pre-open production run (03:19) `last_date` = prior day, so `current_spot` = **prior-day CLOSE**. A PDL is built from prior-day LOW±10; on a down day the prior close sits inside/below the new PDL band, so the support reads "already breached" and is dropped on arrival. Proven against 06-24: close 23,793 vs new PDL top 23,796 — a 3-point cull. PDH (far above spot) survives. The TD-031 fix had already exempted OB/FVG from this filter ("written unconditionally") but explicitly left PDH/PDL filtered — that exemption was the bug. |
| **Diagnosis note** | Long detour (treated correct data as corrupt) before locating it. The decisive tell, missed early: the `--dry-run` *wrote* a PDL (`would write… NIFTY D PDL 23776-23796`) while the DB had none → write-time filter, not bad data. The data (`hist_spot_bars_1m`), the symbol→id map (`instruments`), the date logic, and the aggregation were all correct. |
| **Fix applied** | Daily PDH/PDL now written unconditionally — `_d_pdl = [z for z in d_zones if z["pattern_type"] in ("PDH","PDL")]` (no `filter_breached_zones`). `detect_daily_zones` emits exactly one PDH + one PDL per run (single prior day, no loop), so the proximity prune is unnecessary here. **Weekly left filtered** — `detect_weekly_zones` loops the lookback and emits many PDH/PDL, so it still needs the nearest-2 prune. Patch `patch_s59_daily_pdl_unconditional.py` (canon-v3, backup `build_ict_htf_zones_PRE_S59.py`), commit `2b40a4b`, Local only. |
| **Verify** | Post-fix re-run wrote `D PDL 23776.25-23796.25 => ACTIVE` for 06-24 (build verify block + `_pdlstatus.py` confirmed). Historical PDLs stay EXPIRED (dropped at their own build time; not backfilled — past sessions). |
| **Open tail** | Weekly PDL exhibits the same shape if it ever surfaces (separate, more careful fix — can't simply remove the weekly filter). `datetime.utcnow()` DeprecationWarning at lines 652/662/734 (harmless now; `datetime.now(timezone.utc)` later). |
| **Related** | TD-031 (OB/FVG unconditional-write precedent this extends); ADR-001 / TD-S59-NEW-1 (same shape: a stale/wrong reference price silently invalidating correct data). |

### TD-S57-NEW-3 (S3 priority) — Enhancement Register has a dual structure with conflicting per-ENH status

| Field | Value |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-06-19 (Session 57) |
| **Component** | `docs/registers/MERDIAN_Enhancement_Register.md` (+ stale duplicate `MERDIAN_Enhancement_Register_v5.md`) |
| **Symptom** | The register layers a newer Part 1–6 structure on top of a legacy Tier/Summary-Table structure that was never reconciled, so the same ENH can carry two different statuses. Surfaced S57: ENH-02 (PCR) and ENH-07 (basis rate) read **COMPLETE** in Part 1 but **IN PROGRESS** in their Part 4 detail blocks and the legacy "Full Register" tables. The Part 4 detail is authoritative (ENH-02 writer built-but-orphaned by the S49 Local-disable; ENH-07 unbuilt) — the `v7=COMPLETE` flags were a stale bulk-flip. Corrected ENH-02/07 to IN PROGRESS this session, but the structural duplication remains. |
| **Root cause** | The v7 unified rewrite + subsequent per-session appends left the legacy `## Summary Table` (~L956) + `## Summary Table — Full Register` (~L1407) + Tier 1–4 sections alongside the canonical Part 1 status summary; no single source of truth for status. Plus `MERDIAN_Enhancement_Register_v5.md` (max ENH-42, no last-updated) is a stale duplicate file that should not exist. |
| **Workaround** | Treat Part 1 + Part 4 as authoritative; ignore the legacy tables. |
| **Proper fix** | Collapse to a single status source (Part 1 ↔ Part 4 cross-checked), delete the legacy `Summary Table` / `Full Register` / Tier tables (or mark them ARCHIVE-only), and delete the stale `MERDIAN_Enhancement_Register_v5.md`. Bigger than an inline edit — a dedicated register-reconciliation pass. |
| **Cost to fix** | ~0.5–1 session (status reconciliation audit across ~114 ENHs + table removal + duplicate-file delete). |
| **Blocked by** | Nothing. |
| **Related** | Surfaced during the S57 ENH-02/07 fold + ENH-115/ENH-SDM filing. |

### TD-S57-NEW-1 (S2 priority) — enable/cut over the S56-built `systemd` units onto MALPHA (ADR-018 D1)
> **S58 (2026-06-22) — CLOSED-VERIFIED. Host corrected: the units target MERDIAN AWS (`User=ssm-user`, `/home/ssm-user/meridian-engine`), not MALPHA — ADR-018 D1's MALPHA was wrong.** Units enabled + cut over onto AWS (cp → daemon-reload → `enable --now` both timers; no manual screen to retire). Monday open verified: timer fired 03:40:01 UTC, service active(running), preflight OK OV0782, single PID 452985, 2213 instruments, zero 403s. Closes TD-NEW-K/L/M.

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-19 (Session 57) |
| **Component** | `ws_feed_zerodha.py` + the S56 `deploy/systemd/` units (5) + wsfeed preflight + wsfeed alert (commits `afe8112`/`30cca59`/`b627914`); canonical host = MALPHA; WCB cron entry |
| **Symptom** | The supervision units exist (built+committed S56) but were never enabled — the feed ran unsupervised in a detached `screen` on AWS for 23 days holding an expired Zerodha token, 403-looping, with nothing to restart it or alarm. WCB cron arg defect compounds it. |
| **Root cause** | S56 built the `systemd` units + preflight + alert for rebuild-safety but never cut the live feed over to them; the feed kept running unsupervised on AWS (TD-NEW-L) with no single-instance enforcement (TD-NEW-M) and the Zerodha session split across two hosts (feed on AWS, token on MALPHA). |
| **Workaround** | Live feed restored in-session (manual screen restart); not durable. |
| **Proper fix** | ADR-018 D1 — **enable/cut over the existing S56 `deploy/systemd/` units onto MALPHA** and verify (`Restart=on-failure` + single-instance + journald), one host owns the Zerodha session end-to-end; fix the WCB cron argument in the same pass. NOT a build — the units are authored and git-tracked; the gap is cutover + verify. Closes TD-NEW-L + TD-NEW-M; mitigates TD-NEW-K. |
| **Cost to fix** | ~0.5 session (enable the existing units on MALPHA + cron fix + verify a clean restart + a forced-kill auto-recovery; no authoring). |
| **Blocked by** | Nothing. |
| **Related** | ADR-018 (D1), TD-S48-NEW-1 (the outage this prevents recurring), TD-NEW-K/L/M (S29), TD-S57-NEW-2 (D2 reader guard). |

### TD-S57-NEW-2 (S2 priority) — breadth/divergence readers have no recency floor; a dead feed reads as "working" (ADR-018 D2)
> **S58 (2026-06-22) — CLOSED-VERIFIED.** Guard live on Local + AWS (patch `f922524`). Monday open: orchestrator built market_state every cycle, zero `recency-floor STALE` lines, newest breadth ts seconds-old (04:03:05 UTC), WCB attached. Sweep confirmed `build_market_state_snapshot_local.py` is the only live latest-row breadth consumer (momentum reads a window; replay mirrors excluded by design). Closes the 35-session-old **TD-081** (no data-freshness guard, S22).

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-19 (Session 57) |
| **Component** | every reader of `market_breadth_intraday` / `weighted_constituent_breadth_snapshots` / (future) `structural_divergence_snapshots` — the `fetch_latest_row` no-recency-floor path |
| **Symptom** | `fetch_latest_row` serves the last good row indefinitely with no staleness check — the reason a 23-day-dead breadth feed read as healthy. |
| **Root cause** | No recency floor on the latest-row fetch; a silent upstream stop is invisible to consumers. |
| **Workaround** | None — silent by construction. |
| **Proper fix** | ADR-018 D2 — apply a recency floor on `fetch_latest_row` for every breadth/divergence reader so an upstream stop self-flags STALE within one cycle. MANDATORY; hard precondition for ENH-SDM shipping. |
| **Cost to fix** | ~0.5 session (one guard helper, applied at each reader site). |
| **Blocked by** | Nothing. |
| **Related** | ADR-018 (D2), TD-S57-NEW-1 (D1), ENH-SDM (consumer that requires this guard). |

### TD-S55-NEW-1 (S2 priority) — volatility compute read-path queried dead table compute_volatility_metrics (S48 fixed the write, left the reads)

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed / Closed** | 2026-06-17 (Session 55) — CLOSED same session, commit e6fba1b |
| **Component** | compute_volatility_metrics_local.py — fetch_recent_volatility_rows (L351), fetch_last_valid_vix_snapshot (L454), provenance label (L671) |
| **Symptom** | Every cycle both reads 404 (PGRST205) on table compute_volatility_metrics; graceful handler returns [] so the script exits OK and still inserts — but every volatility row written with EMPTY intraday-change context (5m/15m/30m VIX deltas, velocity, slope) and a non-functional stale-VIX fallback. |
| **Root cause** | S48 corrected the WRITE path (TARGET_TABLE) but left two hardcoded READ references + one provenance label pointing at the dead pre-ADR-006 table name. Masked by the IV=0 / 404 graceful fallback. |
| **Fix** | Canon-v3 patch repointed both reads + two log labels + provenance to production volatility_snapshots (reads stay on prod per TD-NEW-12). Post-fix: no 404, history_source_rows=1000 both symbols. |
| **Caveat** | Pre-fix volatility rows carry blank intraday-change context — not backfillable from live VIX; forward-only correctness. Note in any research consuming those fields. |
| **Blocked by** | Nothing — closed. |

### TD-S54-NEW-1 (S1 priority) — SENSEX compute (volatility/gamma/market_state) silently under-writes ~½ of cycles
> **RESOLVED (code) Session 55 (2026-06-17), commit 1889604.** Structural root cause in run_merdian_shadow_runner_aws.py: fetch_latest_run_id() returned ONE run_id/cycle (limit=1) but a run_id maps to a SINGLE symbol ingest; gamma+volatility infer symbol from the chain, so each cycle computed only whichever symbol ingest landed last (exit 0, logged OK). Proof: 44+23=67, approx 68 cycles/day. Fix: per-symbol run_id resolution (fetch_latest_run_ids); gamma+volatility run once per symbol. gamma read path verified clean. DATA verification pending: 2026-06-17 is first full day on fixed code; confirm at EOD SENSEX distinct-ts approx NIFTY approx 68 before final close.

| Field | Value |
|---|---|
| **Severity** | S1 |
| **Filed** | 2026-06-16 (Session 54) |
| **Component** | compute_volatility_metrics_local.py (+ gamma/market_state writers; identical row counts) and the orchestrator per-symbol loop in run_merdian_shadow_runner_aws.py |
| **Symptom** | On 2026-06-15 (first full post-fix day) volatility_snapshots / gamma_metrics / market_state_snapshots each held NIFTY 44 / SENSEX 23 distinct-ts despite BOTH symbols capturing 68 distinct option_chain ts/hr. Hour-08 probe: 12 orchestrator cycles ALL log `compute_volatility_metrics OK` with advancing ts, but volatility_snapshots hour-08 = NIFTY 11 / SENSEX 1; SENSEX option_chain hour-08 = 12 distinct clean ts (capture fine). |
| **Diagnostics done** | Ruled out (SQL): capture (SENSEX chain has 12 distinct clean ts/hr); morning-only fix-window damage (deficit spread across all hours); non-advancing-ts/upsert-merge collapse (the single surviving SENSEX hour-08 row carried a CORRECT mid-hour ts 08:35:07 matching its chain ts, and total_rows == distinct_ts for both symbols). Four SQL hypotheses each falsified by the next probe — SQL has reached its limit. |
| **Root cause** | UNKNOWN — in CODE, not data. SENSEX compute writes are LOST silently within cycles the pipeline logs as COMPLETE. Candidate mechanisms: a shared run_id / variable where the NIFTY pass overwrites the SENSEX pass within one cycle, or a conditional that skips the SENSEX write. Echoes the S48 "SENSEX gamma not updating" pattern. |
| **Unmasked by** | The S53 volatility insert→upsert (on_conflict=symbol,ts) correctly stopped the 409 crashes, but for SENSEX it converted a loud failure into a silent merge — turning a pre-existing defect into a quiet row deficit instead of a crash. The fix is still correct (NIFTY benefits, no crashes); it just exposed this. |
| **Workaround** | None. NIFTY compute is unaffected; SENSEX intraday compute coverage is ~½ density. Read SENSEX spot truth from market_spot_snapshots (capture is clean). |
| **Proper fix** | Code trace next session: read the SENSEX write path in compute_volatility_metrics_local.py and the orchestrator's per-symbol loop; instrument the SENSEX write with run_id + symbol + ts logging; confirm whether SENSEX writes occur-then-overwrite or are conditionally skipped; fix the loop/variable. Then re-run a single-day recompute and confirm SENSEX distinct-ts ≈ NIFTY ≈ ~68. |
| **Cost to fix** | 1 session (focused code trace + fix + single-day recompute verification) |
| **Blocked by** | Nothing |

### TD-S54-NEW-2 (S3 priority) — Marketview headline SPOT reads coarse option_chain_snapshots.spot, lags the fresh 1-min spot table

| Field | Value |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-06-16 (Session 54) |
| **Component** | merdian_live_dashboard.py:369 (Marketview / meridian-connect, Lovable) |
| **Symptom** | Marketview headline SPOT froze / lagged (e.g. showed 23,957.4 from a 03:55 chain row while real spot was 23,940 and the 1-min table 23,943.9 at 04:07). Pre-open it briefly showed a junk value (24,261) from a stale pre-gate chain spot. |
| **Root cause** | Line 369 reads headline spot from `option_chain_snapshots.spot` (the spot embedded at last chain-fetch — coarse, ingest-cadence-lagged) while the intraday chart reads fresh 1-min `market_spot_snapshots`. Two display sources at two freshnesses. DB is correct throughout; this is a frontend source-choice inconsistency, not a data bug. |
| **Workaround** | NEW-4 (`*/5` ingest) shrank the lag from ~30 min worst-case to ≤5 min by keeping option_chain_snapshots fresh. Read true spot from market_spot_snapshots / TV for live decisions. |
| **Proper fix** | Point the headline-spot read at `market_spot_snapshots` (1-min). The strike grid may keep the chain's spot (it is the spot GEX was computed against — correct there); only the big headline number should switch. Marketview/Lovable frontend deploy; batch with the /health status.json wiring pass. |
| **Cost to fix** | Small (one frontend line + Lovable→GitHub→AWS deploy); batch with other Marketview frontend work |
| **Blocked by** | Nothing (frontend deploy) |

### TD-S54-NEW-3 (S2 priority) — postmarket 16:00 IST capture (capture_postmarket_1600.py) failing daily
> **RESOLVED Session 55 (2026-06-17), commit 5b92433.** Wrapper logged only result.stderr so empty-stderr child failures produced a blank reason; rewritten to always emit exit code + stderr + stdout tail. Real failure was the futures SyntaxError (NEW-6) cascading the prerequisite gate (same root cause). Fully closes when NEW-6 contract-resolution lands.

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-16 (Session 54) |
| **Component** | capture_postmarket_1600.py (AWS cron, 16:00 IST) |
| **Symptom** | Has FAILED daily since ≥2026-05-19; error reason blank since 2026-06-10. Ran on 2026-06-15 but still failed. |
| **Root cause** | Unknown — long-standing, predates the S53 blackout; surfaced during the S54 audit as a separate standing failure. Blank error reason suggests a swallowed exception or a logging gap on the failure path. |
| **Workaround** | Postmarket snapshot not captured at 16:00; downstream consumers of the postmarket row are stale for that window. |
| **Proper fix** | Read the failure path; restore a non-blank exit_reason; diagnose the actual exception; fix. Likely independent of the cron/compute issues. |
| **Cost to fix** | 1 session (diagnose + fix + verify next postmarket run) |
| **Blocked by** | Nothing |

### TD-S54-NEW-4 (S3 priority) — preflight false-green: V18A-03 checks calendar-row-exists but not open_time IS NOT NULL
> **RESOLVED Session 55 (2026-06-17), commits eb052d0 + c2910e8.** Seeder half: built seed_trading_calendar.py (rule-engine-driven, full-schema idempotent upsert, skips weekends/holidays), cron 02:30 UTC daily; manual insert retired. Preflight half: V18A-03 now selects open_time and gates PASS on open_time present (FAIL points at seeder); stage-2 8/0/0/0 PASS, LIVE CANARY ALLOWED.

| Field | Value |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-06-16 (Session 54) |
| **Component** | run_preflight.py (V18A-03 check) + the trading_calendar seeder |
| **Symptom** | On 2026-06-15 a manually-inserted trading_calendar row passed preflight stage2 but capture still skipped because the holiday gate requires open_time IS NOT NULL and the row had open_time NULL. Preflight reported green on a state that the capture gate rejected. |
| **Root cause** | V18A-03 checks only that a calendar row exists, not that open_time is populated; and the calendar seeder doesn't pre-populate open_time ahead of the trading day. The two gates disagree on what 'ready' means. |
| **Workaround** | After inserting/seeding a calendar row, also `UPDATE trading_calendar SET open_time='09:15:00'` for the day; verify capture gate opens, not just preflight. |
| **Proper fix** | (a) extend V18A-03 to require open_time IS NOT NULL (align preflight with the capture gate); and (b) have the calendar seeder pre-populate open_time so the manual step is unnecessary. |
| **Cost to fix** | Small (one preflight check + seeder tweak) |
| **Blocked by** | Nothing |

### TD-S53-NEW-5 (S2 priority) — S52 observability monitors report false state (both directions) + watchdog shares the patient's failure chain
> **UPDATED Session 55 (2026-06-17); env-independence half ALREADY satisfied, 2 logic bugs remain, OPEN.** All monitors load env via load_dotenv() (absolute-path), NOT the source .env chain. Remaining: (a) 999-on-empty clamp in refresh_health_dashboard.py get_minutes_old (returns 999 on any exception incl empty ts, false STALE); (b) monitor_orchestrator_health.py + refresh_health_dashboard.py query a script_execution_log row the orchestrator NEVER writes, permanent false no-orchestrator. A/B (decide rested): (A) self-instrument orchestrator with per-cycle ExecutionLog row (schema-safe, duration_ms=bigint) vs (B) repoint monitors at volatility_snapshots.ts. Fold Dhan-token 26h staleness monitor here.

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-12 (Session 53) |
| **Component** | refresh_health_dashboard.py (999 age-clamp), monitor_orchestrator_health.py (false-negative orchestrator check), all four S52 monitors (shared `source .env` chain) |
| **Symptom** | Monitors report unreliable state in both directions: refresh_health_dashboard.py clamps age to 999 and reports STALE on tables that are actually fresh; monitor_orchestrator_health.py reports 'no orchestrator in last 5 min' (false-negative) after a confirmed run. Architecturally, all four monitors load env via the same `cd … && source .env` chain as the capture layer, so in S53 they died together with what they were supposed to watch (watchdog + patient). |
| **Root cause** | 999 age-clamp logic + an over-strict/incorrect freshness window in the orchestrator check; plus a design flaw — monitors must not share the env-loading failure chain of the systems they monitor. |
| **Workaround** | Do NOT trust the monitor labels — verify health via cron.log + Supabase row freshness directly. (The S53 SHELL fix resurrected the monitors, but their false-state logic is unfixed.) |
| **Proper fix** | Fix the 999 age-clamp and the orchestrator-freshness window; re-architect monitor env-loading to be independent of the `source .env` chain they watch (e.g. bash-shebang self-sourcing or absolute-path env injection). |
| **Cost to fix** | 1 session (monitor logic fixes + watchdog independence) |
| **Blocked by** | Nothing |

### TD-S53-NEW-6 (S2 priority) — futures capture script SyntaxError (Windows-path backslash in f-string) keeps futures dark on AWS
> **PARSE-FIXED Session 55 (2026-06-17), commit 66f8252; futures still DARK pending scripmaster reload.** Three Windows-path sites (L50 DEBUG_DIR + L246/L253 relative_to f-strings); canon-v3 patch repointed DEBUG_DIR to script-dir + mkdir, dropped both relative_to calls. Futures now PARSES + RUNS on AWS (EC2 Python <=3.11). NEW open sub-issue: contract resolution fails, dhan_scripmaster STALE (no June index futures; latest NIFTY/SENSEX expiry 2026-05-26/27); resolver correct; reload_dhan_scripmaster_from_csv.py is a non-atomic delete-then-reload from a LOCAL Windows CSV with interactive prompt, never ported to AWS. Next session: port loader, reload, verify June contracts, uncomment 2 futures cron lines. Futures cron stays COMMENTED.

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-12 (Session 53) |
| **Component** | capture_index_futures_snapshot_local.py (lines 246 + 253) |
| **Symptom** | Hard SyntaxError: `path.relative_to(Path(r'C:\GammaEnginePython'))` — a backslash inside an f-string expression plus a Windows path reference; the script has never run on AWS. Its two cron lines were commented out in S53 so futures capture is DARK. |
| **Root cause** | Backslash inside an f-string expression (illegal pre-3.12) + a hardcoded Windows path that has no meaning on the Linux AWS host. |
| **Workaround** | Two futures cron lines remain commented — index_futures_snapshots is intentionally empty/dark; this is the one known capture gap, by design, pending the fix. |
| **Proper fix** | Drop the `relative_to(Path(r'C:\...'))` Windows-path reference; emit the path plainly (e.g. `print(f"...{path}")`). Deploy via Local→S3→EC2, then uncomment the two cron lines and verify a futures snapshot lands. |
| **Cost to fix** | Small (one-file fix + deploy + uncomment 2 cron lines) |
| **Blocked by** | Nothing |

### TD-S48-NEW-1 — Breadth table `market_breadth_intraday` stale 4h+ despite orchestrator OK
> **S57 (2026-06-19) — RE-DIAGNOSED → CLOSED-DECISION (implementation carries to S58).** The S55 contradiction is resolved: `ws_feed_zerodha.py` was NOT absent — it was running on **AWS** (not MALPHA as documented), since 06-11, in a detached `screen`, holding an **expired Zerodha token**, silently **403-looping**, writing zero-coverage rows into breadth_intraday_history while market_breadth_intraday + WCB stayed dead. That is why market_ticks read empty yet breadth "worked" through 06-11 (it was writing hollow rows, not real coverage). Remediated live: token refreshed on MALPHA → `kite.profile()`=`OK: Navin Balan OV0782` → stale AWS PID 259620 `kill -9` → clean restart (2213 instruments, Feed live, no 403s). Decision recorded as **ADR-018**: D1 feed under `systemd` on MALPHA (single host owns the Zerodha session) + WCB cron arg fix; D2 mandatory recency-floor guard on all breadth readers so a silent stop self-flags STALE. Diagnosis + decision CLOSE; the implementation (systemd unit + WCB cron + recency-floor) carries forward as TD-S57-NEW-1 + TD-S57-NEW-2, graded like NEW-6 (parse-fixed / resolution-open).
> **RE-DIAGNOSED Session 55 (2026-06-17); original causal fields were WRONG, still OPEN.** NOT build_wcb_snapshot_local.py (that is a CONSUMER: reads latest_market_breadth_intraday, writes weighted_constituent_breadth_snapshots). Actual chain: ws_feed_zerodha.py (MALPHA) -> market_ticks -> ingest_breadth_from_ticks.py (AWS) -> breadth_intraday_history -> market_breadth_intraday. breadth_intraday_history nonzero-coverage through 06-11 then 0 from 06-12; consumer SKIPPED_NO_INPUT x2427 since 06-11; ws_feed_zerodha.py ABSENT from MALPHA filesystem (find / empty) though ZERODHA tokens present in .env. CONTRADICTION: market_ticks empty 06-09 onward yet breadth worked through 06-11, so the simple missing-feed chain does not fully reconcile. The one closing read next session: what does ingest_breadth_from_ticks.py SELECT as its tick source. Then restore feed under systemd (missing supervision is the lesson) + harden silent SKIPPED path (TD-NEW-C). No trading impact (regime context, ungated).

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-10 (Session 48) |
| **Component** | `build_wcb_snapshot_local.py` (AWS) writes to `market_breadth_intraday` |
| **Symptom** | Table shows last_update=2026-06-10T05:25:39 IST (10:55 IST); current time 15:28 IST; 4h 32m stale. Orchestrator log shows `build_wcb_snapshot NIFTY OK` and `build_wcb_snapshot SENSEX OK` every 5-min boundary (most recent 09:45:51 UTC = 15:15 IST). Either write failing silently or UNIQUE constraint blocking inserts. |
| **Root cause** | Unknown — requires investigation: (1) script compute succeeds but upsert fails silently, (2) UNIQUE(universe_id, ts) constraint collision if script tries to re-insert same timestamp, (3) table schema mismatch (no symbol column), or (4) Supabase connection issue during write. |
| **Workaround** | Breadth displayed on dashboard shows stale state. WCB regime BEARISH and score -8.1 from 10:55 IST; no impact on current decisions (regime context only, not gated). Monitor for degradation if breadth>1h stale. |
| **Proper fix** | (Phase 1) Check build_wcb_snapshot_local.py upsert call for silent failures (wrap in try-catch with error logging). (Phase 2) Verify Supabase connection/credentials during write. (Phase 3) Check if UNIQUE constraint exists and is colliding (select count DISTINCT(universe_id, ts) vs total row count). (Phase 4) Verify script actually computes new values or returns cached. |
| **Cost to fix** | 1-2 sessions (investigation + logging + fix + verification) |
| **Blocked by** | Nothing |
| **Owner check-in** | 2026-06-10 (S48 filed) |

---

### TD-S46-NEW-1 — Breeze backfill mechanism for futures/ATM/IV/VIX snapshots (addresses TD-NEW-14 30+ day gaps)

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-06 (Session 46) |
| **Symptom** | Four supplementary tables (`iv_context_snapshots`, `hist_atm_option_bars_5m`, `index_futures_snapshots`, `india_vix_daily`) have been empty for 30+ days per TD-NEW-14 diagnostic; dependent writers or ingestion pipelines appear inactive or missing |
| **Root cause** | Writers for these tables either (1) don't exist yet, (2) are not scheduled, or (3) have been deactivated without documentation. No evidence in `script_execution_log` of execution attempts. |
| **Workaround** | Queries reference these tables but fall back to NULL or COALESCE defaults; Marketview card degradation to basic gamma-only attributes when these tables are empty. Backfill dependency structure: can proceed independently from other writers. |
| **Proper fix** | **Phase 1:** Diagnostic search for source scripts (locate `build_iv_context_snapshots.py`, `build_atm_option_bars_5m.py`, `build_futures_snapshots.py`, `build_vix_daily.py` OR confirm deprecation). **Phase 2:** If scripts found, verify scheduling + credentials. If missing, design backfill via Breeze `get_historical_data_v2(stock_code, from_date, to_date, segment, exch_tsym)` API (ICICI Direct backend — replaces vendor purchase + Kite ATM±N cap + Zerodha rolling limitations). **Phase 3:** Deploy `backfill_*_via_breeze.py` suite + 30-day recovery + integration test. |
| **Cost to fix** | 2-3 sessions (diagnostic + design + build + test) |
| **Blocked by** | Nothing |
| **Related** | TD-NEW-14 (original discovery); ADR-013 (Breeze as historical source); ENH-109 (Breeze graduation) |
| **Owner check-in** | 2026-06-06 (S46 filed) |

---

### TD-S46-NEW-2 — S3 deployment automation wrapper scripts (reduce manual workflow)

| Field | Value |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-06-06 (Session 46) |
| **Symptom** | AWS S3 deployment requires manual 6-step workflow (Local upload, AWS pull, verification); multiple commands to remember; non-idempotent if interrupted mid-cycle; no audit trail in log output |
| **Root cause** | S3 transfer vector is recent (S46); no wrapper automation exists; manual `aws s3 cp` commands require full context awareness + error handling |
| **Workaround** | Follow `MERDIAN_AWS_S3_Deployment_Mechanism_S46.md` documented workflow; `git pull` on AWS for code files; S3 only for non-git binary/vendor files or out-of-band backfill scripts |
| **Proper fix** | Create two idempotent wrapper scripts: **(1) `deploy_to_aws.ps1` (Local Windows)** — uploads core/ + orchestrator to S3, verifies S3 checksums, SSH signals AWS pull (single atomic operation, safe-to-retry). **(2) `pull_from_s3.sh` (AWS EC2 bash)** — pulls core/ + orchestrator from S3, verifies checksums, makes executable, restarts systemd/cron if needed (single atomic operation, safe-to-retry). Both should log start/end timestamps + action counts to `shadow_runner.log` for audit. Estimated 60-90 min total. |
| **Cost to fix** | 1 session (build + test on live EC2) |
| **Blocked by** | Nothing |
| **Related** | MERDIAN_AWS_S3_Deployment_Mechanism_S46.md (documentation); ADR-006 AWS migration scope (deployment layer); ENH-113 Phase 2.c AWS shadow runner |
| **Owner check-in** | 2026-06-06 (S46 filed as convenience enhancement) |

---

### TD-NEW-14 — Four ingestion tables empty for 30+ days: `iv_context_snapshots`, `hist_atm_option_bars_5m`, `index_futures_snapshots`, `india_vix_daily`

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-02 (Session 43) |
| **Symptom** | During 2026-06-02 short-covering pattern analysis, attempted to join four supplementary tables to `gamma_metrics` for the full attribute set (IV skew, futures basis, ATM option volumes, VIX). All four tables returned 0 rows for 2026-06-02 and all dates in the prior 30 days. Diagnostic queries confirmed: `iv_context_snapshots` COUNT=0 for 2026-06-02 ± 30d; `hist_atm_option_bars_5m` COUNT=0 for 2026-06-02 ± 30d; `index_futures_snapshots` COUNT=0 for 2026-06-02 ± 30d; `india_vix_daily` COUNT=0 for 2026-06-02 ± 30d. Impact: Marketview case-file analysis degraded to gamma-only attributes (net_gex, pin_risk, straddle_atm, regime, gamma_concentration) — missing IV regime, skew, basis, VIX context that would enrich pattern recognition and validation. |
| **Root cause** | Likely one of three: (a) Ingestion writers (`build_iv_context_snapshots.py`, `build_atm_option_bars_5m.py`, `build_futures_snapshots.py`, `build_vix_daily.py`) are not running or are silently failing to write rows; (b) Ingestion schedule is disabled or not triggered (Task Scheduler, AWS cron, or manual); (c) Schema changes, API credential rotation, or data source migration broke upstream collection without alerting. No evidence in `script_execution_log` of these writers failing — absence of evidence suggests they may not be running at all. |
| **Workaround** | Document case files with gamma-only attributes (status quo for 2026-06-02 case). Use supplementary web queries or manual TradingView snapshots if IV/VIX/basis context needed for a specific analysis. Upgrade to full-join results once tables are populated. |
| **Proper fix** | **Phase 1 (diagnostic):** Verify ingestion writers exist, are registered in Task Scheduler / AWS cron, and have run logs in `script_execution_log` for the past 30 days. If missing, locate source scripts or disable table references pending rebuild. **Phase 2 (validation):** Once writers confirmed running, verify they're writing to correct tables (not staging tables, not wrong schema). Confirm API tokens/credentials for data sources (NSE, Zerodha, external VIX feed) are valid and pulling fresh data. **Phase 3 (backfill):** 30-day historical backfill once writers confirmed. |
| **Impact** | Medium — analysis capability degraded but not blocked. Case files can still stand on gamma mechanics alone. Forward-looking case files will lack full attribute context until resolved. |
| **Related** | ENH-110 (Consolidated marketview build — likely encompasses these table builds as sub-task); ADR-002 (market structure philosophy — IV skew, basis, VIX regime are P7 attributes per ADR-002 §P7); 2026-06-02 short-covering case file (triggered discovery). |
| **Owner check-in** | 2026-06-02 (filed) |

---

### TD-S41-NEW-1 — `trading_calendar` table lacks NSE holiday pre-population; Bakri Id 2026-05-28 had no row at all

| Field | Value |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-06-01 (Session 41) |
| **Symptom** | `trading_calendar` table missing rows for NSE holidays. Specifically observed: 2026-05-28 (Bakri Id) had no row in `trading_calendar` — neither marked as holiday nor as trading day. This violates ENH-66 doctrine which expects every calendar date to have a row with `is_trading_day` flag set correctly. Downstream impact: any writer that branches on `trading_calendar.is_trading_day` defaults to unknown behavior; some writers may proceed as if it's a trading day and fail to fetch market data, generating spurious CRASH rows in `script_execution_log`. |
| **Workaround** | Manually insert missing rows when discovered: `INSERT INTO trading_calendar (trade_date, is_trading_day, holiday_name) VALUES ('2026-05-28', FALSE, 'Bakri Id') ON CONFLICT (trade_date) DO UPDATE SET is_trading_day=FALSE, holiday_name='Bakri Id'`. Cumulative miss list across the year requires manual reconstruction. |
| **Root cause** | `merdian_start.py.ensure_calendar_row()` ensures the CURRENT date's row exists at script start, but only after the writers have already attempted to run. Holidays are pre-known NSE/BSE-published lists but MERDIAN doesn't ingest them. |
| **Proper fix** | Two paths: (a) annual NSE holiday calendar pre-populate via NSE API / static config — `merdian_calendar_seed.py` runs once per year inserting full year of holiday rows; (b) amend `merdian_start.py.ensure_calendar_row()` to consult an NSE holiday API at row-create time and stamp `is_trading_day=FALSE` for holidays before any writer runs. Path (a) is cheaper and more predictable. |
| **Impact** | Low — affects holiday days when most writers gracefully fail anyway. Cosmetic CRASH rows in `script_execution_log` on holiday boundaries. |
| **Related** | TD-S41-NEW-2 (Dhan token refresh on holidays — related symptom of same calendar-blind-spot class), ENH-66 (calendar doctrine), `merdian_start.py.ensure_calendar_row()`. |

---

### TD-S41-NEW-2 — Dhan token refresh suppressed across NSE holidays; cross-host single-point-of-failure where Local is sole refresh path
> **DOWNGRADED S2->S3 Session 55 (2026-06-17).** AWS-primary Dhan token refresh confirmed WORKING: system_config.dhan_api_token refreshed 06-16 03:23 UTC (~20h fresh); consumers all read DHAN_API_TOKEN from .env, so the cron target refresh_dhan_token.py (the .env writer) is CORRECT (refresh_dhan_token_aws.py writes only Supabase and would starve them). Removed the redundant source .env from the token cron line (was the dash-killable blackout pattern; script self-loads via load_dotenv). Residual: optional >26h staleness monitor, fold into NEW-5.

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-01 (Session 41) |
| **Symptom** | Dhan token refresh task on Local Windows didn't fire on 2026-05-28 (Bakri Id) because operator's workstation was off. AWS-side `pull_token_from_supabase.py` probed at 03:05 Thu UTC successfully against the Wed-refreshed token — ~15 min before expiry. Had AWS probed any later post-expiry, AWS would have failed silently on stale token (Mode B 401 pattern from S29 firefighting). Cross-host single-point-of-failure: Local Windows is sole refresh path; AWS only pulls and consumes, never refreshes. Cross-host architecture has worked for ~50 trading days but Bakri Id surfaced the holiday edge case. |
| **Workaround** | None active. Discovered via post-hoc `dhan_token_probe_log` diagnostic confirming Local missed Thu refresh; AWS's Thu probe scraped just-in-time pre-expiry. |
| **Root cause** | Two-layer: (a) Local refresh task is computer-state-dependent — workstation off = no refresh; (b) AWS lacks refresh capability — it only pulls from Supabase. The architecture assumes Local will fire daily but doesn't validate this against the actual refresh schedule. Holiday boundaries (Bakri Id, etc.) are operationally where Local is most likely to be off. **NOT a regression of S29 Mode B fix** — S29 fixed the case where Local DID refresh but the running process held stale token; S41 surfaces the orthogonal case where Local DIDN'T refresh at all. Both are different failure modes of the cross-host single-refresher architecture. |
| **Proper fix** | Two-stage: **interim** WAKETOWRUN=true on Local Task Scheduler task (forces system wake on schedule) + AWS-side heartbeat staleness check (`pull_token_from_supabase.py` extended to fail loudly if pulled token's `last_refreshed_at` is >18 hours stale instead of silent-consume); **architectural** ADR-006 AWS migration of refresh logic — `refresh_dhan_token.py` runs on AWS at canonical hour against Supabase-stored credentials. ADR-006 was already drafted-blocked-on-TD-080; this finding materially elevates urgency. |
| **Impact** | High potential. Has not yet caused production failure but the cross-host arch's failure mode is "AWS consumes stale token past expiry on a holiday morning while Local is off" — would Mode-B-401 every AWS-side writer until operator manually intervenes. |
| **Related** | TD-080 (Dhan token refresh failure mode reframed S25, blocks ADR-006 unblock criteria); ADR-006 (AWS migration scope draft, urgency elevated by this finding); §D.21.3 (IMDSv2 attached-SG check codification — generalization of cross-host audit discipline); `pull_token_from_supabase.py` (consumer needs staleness check addition). |

---

### TD-S41-NEW-3 — `merdian_reference.json` schema drift surfaced via 3-strike SQL guess pattern on `script_execution_log` + `dhan_token_probe_log`

| Field | Value |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-06-01 (Session 41) |
| **Symptom** | Twice in Session 41, SQL composition against ops tables required multiple guess-and-retry cycles to find correct column names: `script_execution_log` (created_at vs ts vs ts_utc) + `dhan_token_probe_log` (status vs verdict vs event). Each cycle wasted 1-2 minutes on 42703 "column does not exist" errors. The cost-driver is `merdian_reference.json` being stale relative to actual `information_schema.columns` — the JSON serves as Claude's "where to look" but doesn't always reflect what's actually present. |
| **Workaround** | Discipline: before composing SQL against any ops table, run `SELECT column_name FROM information_schema.columns WHERE table_name='<x>'` first. Cheap (one round-trip) but disciplined-only — Claude tends to guess from JSON. |
| **Root cause** | `merdian_reference.json` is updated session-close only; intermediate schema changes (column adds, renames, drops) accumulate before being reflected. Lovable auto-scaffold + manual ALTER statements compound the drift. JSON is also human-curated at close — easy to miss columns that were added mid-session via DDL. |
| **Proper fix** | **Path A** systemic audit script `verify_reference_schema.py` runs at session-open, compares `merdian_reference.json` against live `information_schema.columns` for every table in JSON, reports drift; operator addresses before any SQL composition. **Path B** kill JSON-as-schema-source — Claude always queries `information_schema.columns` first regardless of JSON; JSON becomes purely human reference. **Path C** auto-regenerate JSON tables section from `information_schema.columns` at session close. Path A is cheapest; Path C is most durable. |
| **Impact** | Low — cosmetic time-waste on schema-guess loops. Compounds in long sessions. |
| **Related** | `merdian_reference.json` (the drift target), `information_schema.columns` (the source of truth), Session 39 D.21.3 IMDSv2 attached-SG check (analogous discipline — "always verify the actual state, not the cached belief"). |

---

### TD-S41-NEW-5 — WCB writer 17% NIFTY active-weight degradation (pagination cap) + regime threshold disagreement Python 60/40 vs SQL 62.5/37.5

| Field | Value |
|---|---|
| **Severity** | S2 |
| **Filed** | 2026-06-01 (Session 41) |
| **Symptom** | Two sub-findings discovered during Health dashboard build + WCB instrumentation work: **Sub-A** WCB writer (`build_wcb_snapshot_local.py`) shows 17% active-weight degradation on NIFTY — `coverage` reads 83.2% vs expected 100%. Root cause: `fetch_daily_breadth_rows()` paginates 50 tickers × ~150 history rows per ticker > 5000 PostgREST default limit; the trailing 11 tickers' history rows fall off the page. 11 missing constituents: SBIN, SBILIFE, SHRIRAMFIN, SUNPHARMA, TATACONSUM, TATASTEEL, TECHM, TITAN, ULTRACEMCO, WIPRO, TCS. RELIANCE shows `trade_date=2026-04-06` stale because its history rows are at the page boundary. SENSEX unaffected (30-ticker basket × ~150 rows = 4500 < 5000 limit). **Sub-B** Regime threshold disagreement between `classify_wcb_regime()` Python (`bullish ≥ 60`, `bearish ≤ 40`, else `transition`) and `compute_breadth_regime()` SQL function (`bullish ≥ 62.5`, `bearish ≤ 37.5`, else `transition`). Both produce `TRANSITION` today (51.5 falls in both ranges) but boundary cases (60-62.5 or 37.5-40) would disagree. |
| **Workaround** | Sub-A: live WCB scores reading slightly under-weighted; NIFTY shows TRANSITION 51.5/100 today, but with 17% missing weight the true score could be 50-65 range. Not actionable from operator-side. Sub-B: rely on Python writer's classification as canonical (it's what populates `weighted_constituent_breadth_snapshots.regime`); SQL function is unused downstream. |
| **Root cause** | Sub-A: `fetch_daily_breadth_rows()` uses default PostgREST pagination (1000 rows per page) and 5000 row hard cap; with 50 tickers × ~150 history rows = 7,500 expected rows, the call returns 5000 → trailing tickers fall off. Sub-B: Python and SQL functions were written at different sessions and drifted; no enforcement mechanism for parity. |
| **Proper fix** | **Sub-A** add `gte('trade_date', N_days_ago)` server-side filter where N=20 (typical lookback) to reduce per-ticker row count from ~150 to ~20; 50 × 20 = 1,000 rows fits in single page. Alternative is explicit pagination with `range(0, 9999).limit(10000)`. **Sub-B** Path A align Python to SQL 62.5/37.5 thresholds (fast closure, ~5 min); Path B align SQL to Python 60/40 (depends on whether SQL function is consumed anywhere — `pg_proc` audit didn't find consumers); Path C call SQL function from Python directly (cleanest, single source of truth). Path A is fastest; Path C is most durable. |
| **Impact** | Sub-A: WCB card reads slightly under-weighted on NIFTY; coverage shows 83.2% which is the symptom. Sub-B: boundary-case regime classifications could flip across Python/SQL boundary. |
| **Related** | `build_wcb_snapshot_local.py` (Sub-A target), `classify_wcb_regime()` Python helper (Sub-B target), `compute_breadth_regime()` SQL function (Sub-B target — verify consumers via `pg_proc` query before deleting), `weighted_constituent_breadth_snapshots.regime` column (final destination), `fetch_daily_breadth_rows()` (Sub-A root). |

---

### TD-S40-NEW-1 — Patch script `patch_s40_enh83_view_tau_rewrite.py` initial v1 contained cp1252-incompatible Unicode minus-sign — REMEDIATED same-session

| | |
|---|---|
| **Severity** | S4 (cosmetic — surfaced during dry-run only; ASCII-clean v2 deployed before any live application; preserved here for audit-trail visibility per Doc Protocol v4 Rule 8 same-session NEW+RESOLVED pattern) |
| **Filed** | 2026-05-29 (Session 40 — discovered during dry-run when Python interpreter on operator's Windows cp1252 console encoding rejected the minus-sign character `−` (U+2212) embedded in a comment string; replaced with ASCII hyphen `-` (U+002D) for cp1252 compatibility) |
| **Symptom** | Initial v1 dry-run of `patch_s40_enh83_view_tau_rewrite.py` failed with `UnicodeEncodeError: 'charmap' codec can't encode character '\\u2212'` on the operator's PowerShell console (Windows cp1252 default). Patch logic itself was correct; encoding incompatibility prevented even reaching the AST-validate step. |
| **Workaround in place** | REMEDIATED same-session by replacing the single offending `−` (U+2212) with `-` (U+002D) in the comment block at module top + re-running dry-run → PASS → live → PASS. v2 ASCII-clean script applied successfully to both view DDL files. |
| **Root cause** | Patch script authoring habit picked up Unicode minus-sign from copy-paste of mathematical-typography source material; Windows PowerShell default cp1252 console encoding cannot render U+2212; should have used ASCII hyphen from the start for Windows-side patch scripts. |
| **Proper fix** | Already done — script preserved on disk as ASCII-clean v2 + cp1252-clean Unicode literal review applied to any future patch scripts authored for operator Windows environment (codify as patch-script ASCII-only discipline; or alternatively run patches under `chcp 65001` UTF-8 PowerShell context). |
| **Impact if not fixed (recurrence)** | Recurrent if future patch scripts authored with Unicode-typography characters; pattern is silent until dry-run fails, but easy to surface — every patch script run starts with a dry-run round so encoding bugs surface before live application. Low recurrence risk; trivial fix when it does. |
| **Related** | `patch_s40_enh83_view_tau_rewrite.py` v1 (encoding bug) → v2 (ASCII-clean, APPLIED); CLAUDE.md patch-script protocol (codified S29 — `read_bytes() + decode('utf-8-sig')` + `write_bytes(text.encode(enc))`; this TD adds an ASCII-only authoring corollary for Windows-side patch scripts). |

---

### TD-S40-NEW-2 — `update_parameter()` SECURITY DEFINER RPC violated `chk_valid_from_to` CHECK constraint because `merdian_parameters.valid_to` column had `DEFAULT now()` — DISCOVERED + FIXED same-session

| | |
|---|---|
| **Severity** | S3 (DISCOVERED + FIXED same-session — filed for audit-trail visibility per Doc Protocol v4 Rule 8 same-session NEW+RESOLVED pattern; high-leverage codification for future Lovable scaffold audits) |
| **Filed** | 2026-05-29 (Session 40 — discovered during TD-S37-01 closure round-trip smoke-fire when calibration console attempted a `pin.tau.NIFTY` parameter update via the RPC and received PostgreSQL CHECK violation error) |
| **Symptom** | `SELECT update_parameter('pin.tau.NIFTY', 'S40 round-trip test', p_value_num := 0.25, p_changed_by := 'operator')` returned `ERROR:  new row for relation "merdian_parameters" violates check constraint "chk_valid_from_to" DETAIL:  Failing row contains (..., valid_from=2026-05-29 ..., valid_to=2026-05-29 ..., ...)`. Both `valid_from` and `valid_to` had identical timestamps on the new row, violating the CHECK `valid_from < valid_to OR valid_to IS NULL`. |
| **Workaround in place** | RESOLVED via `ALTER TABLE public.merdian_parameters ALTER COLUMN valid_to DROP DEFAULT;`. Verified round-trip 0.30→0.25→0.30 on `pin.tau.NIFTY` post-fix; clean temporal chain confirmed (1st row valid_to=null; 2nd row 1st gets valid_to=t1 + new row valid_from=t1 valid_to=null; 3rd row 2nd gets valid_to=t2 + new row valid_from=t2 valid_to=null). |
| **Root cause** | Lovable's auto-scaffold for `merdian_parameters` (S39) gave `valid_to` column `DEFAULT now()`. PostgreSQL `now()` returns transaction-timestamp (not statement-timestamp), which is identical across all calls within a single transaction. `update_parameter`'s atomic close-old-row + insert-new-row pattern runs both statements inside one transaction; the new row inherits `valid_to = now()` from the column default, which equals `valid_from` (also `now()`); CHECK rejects. Lovable's DEFAULT choice was reasonable for SELECT-time inserts (single statement, single now()), but broken for multi-statement atomic transactions where rows need to differentiate by transaction-time. |
| **Proper fix** | Already done — `ALTER TABLE ... ALTER COLUMN valid_to DROP DEFAULT;` is the canonical fix. Codified as Assumption Register §D.22.1: any column intended to differentiate rows by transaction-time within a single transaction must NOT carry `DEFAULT now()` or any statement-timestamp-equivalent default; subsequent Lovable schema scaffolds for temporal-immutable tables require pre-deploy `information_schema.columns` audit for `column_default IS NOT NULL AND column_default LIKE '%now()%'` on any column whose semantics span multiple rows within one transaction. |
| **Impact if not fixed (recurrence)** | Will recur on every future Lovable schema scaffold that introduces a temporal-immutable column with a `now()` default. Same audit pattern (`information_schema.columns` + the SQL filter above) catches it pre-deploy in <30s. Filed S3 because the surface area is bounded (only Lovable-scaffolded tables with multi-statement RPC writers), but the failure mode is silent until a write attempt (no error log on table creation, no operator-visible symptom until the first update attempt). |
| **Related** | TD-S37-01 closure smoke-fire (which surfaced this bug); §D.22.1 Assumption Register S40 (Lovable temporal-immutable column DEFAULT audit pattern); ENH-110 Phase 1 backend (S39 — the Lovable scaffold that introduced the defective DEFAULT); `update_parameter` RPC definition (still correct as designed; the column DEFAULT was the bug, not the RPC body). |

---

### TD-S40-NEW-3 — TradingView Pine overlay extension for PIN + ACCEL zones — deferred pending full file review

| | |
|---|---|
| **Severity** | S2 (operator-visible workflow gap — Pine overlay currently shows only ICT zones, not PIN/ACCEL gamma-positioning zones; operator manually cross-references Marketview dashboard with TradingView chart, losing the in-chart visual confluence the ICT layer already provides) |
| **Filed** | 2026-05-29 (Session 40 — operator asked about getting latest ICT + PIN + ACCEL zones onto TradingView; `merdian_ict_htf_zones.pine` regenerated 2026-05-29 08:46 IST but TV showing stale 2026-05-26 zones; PIN/ACCEL not currently in Pine overlay at all) |
| **Symptom** | `generate_pine_overlay.py` (505 lines, ICT-only) reads `ict_htf_zones` and writes a Pine v6 overlay file rendering zone boxes per timeframe. It does NOT read `v_gex_strike_pin_zone` or `v_gex_strike_accel_zone` (ENH-81 views shipped S37) and therefore does not render PIN/ACCEL zones as Pine box overlays. Operator's TradingView chart can show ICT structure but not the dealer-positioning context that Marketview surfaces in the Pin Zone / Accel Zone tiles. |
| **Workaround in place** | None — operator visually cross-references Marketview dashboard with TradingView chart. The two PIN/ACCEL strikes per symbol are small enough to remember during a session but the visual confluence benefit (\"is spot inside the pin zone right now?\") is lost. |
| **Root cause** | `generate_pine_overlay.py` predates ENH-81 (S37); no extension was authored when ENH-81 shipped because operator's S37 priorities were Lovable dashboard + Pine overlay + 7-canonical-file doc-close. S37 close noted Pine overlay PIN/ACCEL deferred per operator threshold (\"when I find I'm mentally computing PIN/ACCEL against ICT zones during a trade\") — that threshold reached S40 when operator asked for the extension explicitly. |
| **Proper fix** | Extend `generate_pine_overlay.py` with two new fetch functions (`fetch_pin_zone(sb, symbol)` + `fetch_accel_zone(sb, symbol)` reading `v_gex_strike_pin_zone` + `v_gex_strike_accel_zone` for latest run_id per symbol) + Pine-template box rendering for each zone (semi-transparent fill + label at zone-edge per S37 ENH-81 v2 Pine ergonomic patterns); chain into existing `_pine_render()` pipeline; preserve existing ICT zone output. Estimated 30-40 min including dry-run + smoke-fire + operator preview iteration. Carry-forward to S41. |
| **Impact if not fixed** | Operator continues cross-referencing manually. Cost is mental overhead during a trade (look at TradingView for structure, look at Marketview for positioning, hold both in head while deciding). For a single trade per session this is manageable; for a high-cadence session it's friction. Cost compounds as operator's pin/accel reading discipline strengthens — the more useful the PIN/ACCEL signal becomes operationally, the higher the cost of NOT having it in-chart. |
| **Related** | ENH-81 views shipped S37 (`v_gex_strike_pin_zone` + `v_gex_strike_accel_zone`); ENH-81 v2 Pine ergonomic patterns from S37 (zone-edge label anchors + single-strike widening); `generate_pine_overlay.py` source 505 lines at S40 review; S40 carry-forward P2 (operator session priority); ADR-017 P6 distance×time salience for PIN/ACCEL surfacing (which this TD enables in-chart). |

---

### TD-S39-NEW-1 — Lovable auto-scaffold granted anon role FULL privileges (DELETE/INSERT/UPDATE/TRUNCATE/REFERENCES/TRIGGER/SELECT) on every consumed table+view instead of SELECT-only — REMEDIATED same-session

| | |
|---|---|
| **Severity** | S2 (REMEDIATED same-session — filed for audit-trail visibility per Doc Protocol v4 Rule 8 same-session NEW+RESOLVED pattern) |
| **Filed** | 2026-05-27 (Session 39 — discovered post-RLS-triplet application via 13-row anon-grants audit returning 91 rows = 7 privilege types × 13 surfaces; should have been 13 rows SELECT only) |
| **Symptom** | After applying `2026-05-26_enh110_rls_triplets.sql` to 8 tables + 5 views in live MERDIAN Supabase, verification query `SELECT table_name, privilege_type FROM information_schema.role_table_grants WHERE grantee='anon' AND table_schema='public' AND table_name IN (...)` returned 91 rows showing anon held `DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE` on every consumed table+view. Threat model: anon key ships in browser bundle (publicly visible in any deployed dashboard via DevTools); with these grants any anon-key holder could `DELETE FROM gex_strike_snapshots` or `TRUNCATE signal_snapshots` via PostgREST regardless of RLS policies (RLS filters rows, GRANT lets role attempt operation). Counts pre-remediation: gex_strike_snapshots 44953 / gamma_metrics 39317 / signal_snapshots 9695 / ict_zones 439 / market_breadth_intraday 2790 / po3_session_state 42 / market_spot_session_markers 96 / merdian_parameters 11 — all live data intact, no exploitation observed before remediation. |
| **Workaround in place** | REMEDIATED via PL/pgSQL DO block `FOREACH t IN ARRAY tables LOOP EXECUTE format('REVOKE ALL ON public.%I FROM anon', t); EXECUTE format('GRANT SELECT ON public.%I TO anon', t); END LOOP` across all 13 surfaces. Post-remediation grants audit returned 13 rows all `privilege_type=SELECT`. Vulnerability window closed before any exploitation. |
| **Root cause** | Lovable's auto-scaffold behavior for tables it consumes — when Lovable connects to an existing Supabase project and references tables, it auto-issues `GRANT ALL ON public.<table> TO anon` without prompting and without surfacing in the Lovable UI. The RLS triplet pattern (`ALTER TABLE ENABLE RLS + CREATE POLICY FOR SELECT TO anon USING (true) + GRANT SELECT ON ... TO anon`) is operationally insufficient when applied AFTER Lovable has already granted ALL — the policy filters rows on SELECT but the prior grant lets DELETE/UPDATE/TRUNCATE through. |
| **Proper fix** | (a) Add pre-deploy hygiene check to ENH-110 Phase 2+ workflow: after every Lovable schema operation against the live MERDIAN Supabase, run anon-grants audit and apply `REVOKE ALL + GRANT SELECT` remediation; (b) consider documenting RLS-triplet pattern in operator runbook as "ALTER TABLE ENABLE RLS + DROP POLICY IF EXISTS + CREATE POLICY + **REVOKE ALL FROM anon** + GRANT SELECT TO anon" — the REVOKE step before GRANT SELECT is what protects against Lovable's prior ALL grant; (c) longer-term: separate Lovable-isolated Supabase project for development with sync mechanism to live, so Lovable never touches live anon grants directly. ~30-60 min for (a) + (b); separate ENH for (c). |
| **Impact if not fixed (recurrence)** | Same exposure pattern will recur on every Lovable schema operation that touches live MERDIAN Supabase — ENH-110 Phase 2 confluence detection writer + ENH-111/112 wiring + future ENH-110 phase work all run through Lovable and will re-issue the GRANT ALL pattern. Filed at S2 not S3 because exposure window per occurrence is hours-to-days until next audit, and the failure mode is silent (no error log, no Lovable warning, no operator-visible symptom until exploitation). |
| **Related** | TD-S37-03 (Lovable anon-key brittleness — RLS misconfiguration produces silent empty datasets; same family of Lovable-platform-trust issue), §D.21.1 + §D.21.2 Assumption Register S39 (Lovable auto-grant safety REFUTED + anon-key-in-public-repo trust model VALIDATED), ENH-110 Phase 1 backend ship (S39 — the deployment that surfaced this), CLAUDE.md S39 settled-decisions footer. |

---

### TD-S39-NEW-2 — Marketview hero chart label collision residual at dense ICT-zone band area near spot

| | |
|---|---|
| **Severity** | S3 (cosmetic — does not affect data correctness or operator decisions, only readability at high-density band areas) |
| **Filed** | 2026-05-27 (Session 39 — operator-visible during browser verification of Marketview at http://13.63.27.85/marketview post-Lovable Turn 6 final polish) |
| **Symptom** | Marketview hero chart renders ICT zone labels TIER2 BULL_FVG / TIER2 BEAR_FVG / TIER1 BULL_OB / SKIP BULL_FVG inside the band fills. Lovable's Turn 5 polish staggered PIN/ACCEL/max γ labels with 16px gap (resolved their collision), but ICT zone label-vs-label collision within the dense band area near spot still occurs. Example: NIFTY 23,922.6 spot with stacked labels "TIER2 BULL_FVG / TIER2 BULL_FVG" at adjacent overlapping bands. SENSEX 75,922.22 spot has 4-label stack TIER2 BULL / TIER2 / TIER / SKIP all visually overlapping inside the BULL_FVG cluster. |
| **Workaround in place** | None — operator can still read individual zone bounds from the ICT zones nearest-10 panel (which renders cleanly as a list); hero chart labels are supplementary. |
| **Root cause** | Lovable's polish pass for label stagger was scoped to PIN/ACCEL/max γ labels which fire at distinct strike values; ICT zone labels fire at zone midpoints which cluster within 50-100pt bands; same 16px stagger logic would need to apply to zone-label collision detection in addition. |
| **Proper fix** | Lovable Turn 7 prompt: extend label stagger logic to ICT zone labels — when two zone labels' midpoints are within 0.5% of each other on Y-axis, alternate left/right horizontal anchor or stack vertically with 16px gap. Or simpler: show only nearest-3 zone labels on chart (rendering the full nearest-10 in the side panel still). ~5 min Lovable prompt. |
| **Impact if not fixed** | Cosmetic. Operator-visible but does not affect decision quality — band fills + nearest-10 panel convey the information cleanly without labels. Defer until next Lovable polish session. |
| **Related** | ENH-110 Phase 1 SHIPPED S39 (Marketview UI), Lovable Turn 5 polish prompt (which staggered PIN/ACCEL/max γ labels successfully), ADR-017 Operator Console Design Principles P5 motion-replaces-timestamps (zone labels are static so this principle doesn't help). |

---

### TD-S39-NEW-3 — `.env` containing live MERDIAN Supabase anon key committed to public GitHub repo `balannavin-cyber1/meridian-connect` by Lovable

| | |
|---|---|
| **Severity** | S3 (hygiene — anon key is public-by-design and ships in browser bundle anyway; threat model bounded by RLS policies which post-S39 grant anon SELECT-only; not an active vulnerability but bad practice) |
| **Filed** | 2026-05-27 (Session 39 — surfaced during Lovable Turn 3 commit `6b95ded Added Supabase client init` review on github.com/balannavin-cyber1/meridian-connect/blob/main/.env) |
| **Symptom** | Lovable Turn 3 committed `.env` to repo root containing `VITE_SUPABASE_URL=https://kilmcowcikwdhvdxwofi.supabase.co` + `VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (full anon JWT) without prompting and without adding to `.gitignore`. Repo is public on GitHub. Any visitor to repo URL can read both values. |
| **Workaround in place** | (a) Anon key is public-by-design — it ships in the React bundle inlined at Vite build time via `import.meta.env.VITE_SUPABASE_URL/ANON_KEY` and is therefore visible to anyone who opens DevTools on the deployed dashboard; making the key visible on GitHub adds no incremental exposure. (b) Post-S39 RLS remediation grants anon SELECT only — worst-case exploitation is reading the data already visible to anyone with the dashboard URL. (c) `.env.local` placed on AWS at `/home/ssm-user/merdian-marketview/.env.local` (chmod 600, gitignored) ensures Vite picks up correct keys regardless of what's in committed `.env`. |
| **Root cause** | Lovable's auto-commit of `.env` is default behavior when it detects env-var usage in code — it doesn't gitignore env files by default. Differs from standard Vite scaffold which gitignores `.env*.local` patterns by default. |
| **Proper fix** | Operator local action: `cd <local clone> && git rm --cached .env && echo '.env' >> .gitignore && git commit -m "chore: gitignore .env, remove committed env file" && git push`. Lovable can update `.gitignore` (already attempted in Turn 5 polish — `e59c0ef Added env files to .gitignore` landed) but Lovable's git environment can't issue `git rm --cached` for already-committed files; operator workstation needed for the removal commit. ~5 min operator action. |
| **Impact if not fixed** | None operational. Hygiene-only — future security audit might flag, and key rotation costs +1 step (must also update committed `.env` if not yet removed from git history). Filed at S3 because trust model is sound but practice is sloppy. |
| **Related** | TD-S39-NEW-1 (Lovable auto-grant exposure — same family of Lovable-platform-trust issue), §D.21.2 Assumption Register S39 (anon-key-in-public-repo trust model VALIDATED — exposure is acceptable given RLS boundary, just bad practice), Lovable's gitignore commit `e59c0ef` from Turn 5 (committed gitignore additions but didn't remove already-committed `.env`). |

---

### TD-S39-NEW-4 — Orphan AWS Security Group `launch-wizard-2` not attached to any EC2 instance — cleanup pending

| | |
|---|---|
| **Severity** | S4 (cosmetic — no operational impact; orphan SG visible in AWS console but unattached) |
| **Filed** | 2026-05-27 (Session 39 — surfaced during AWS networking debug arc when operator was editing wrong SG for hours) |
| **Symptom** | AWS Security Group `launch-wizard-2` exists in eu-north-1 console alongside `launch-wizard-1` (which IS attached to MERDIAN EC2 `i-0878c118835386ec2`). Operator spent hours editing `launch-wizard-2` inbound rules expecting `13.63.27.85:80` to become reachable from external networks; no effect because launch-wizard-2 was orphan/unattached. Resolution via IMDSv2 token query `curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/security-groups` returned `launch-wizard-1` confirming the attached SG; adding TCP 80 from 0.0.0.0/0 to launch-wizard-1 instantly resolved the connectivity issue. |
| **Workaround in place** | Operator now editing correct SG `launch-wizard-1`. `launch-wizard-2` remains orphan in console but unattached so its rules have no effect on any instance. |
| **Root cause** | AWS launch-wizard flow creates a new SG per wizard run if operator selects "Create security group" instead of "Select existing"; multiple wizard runs over time leave behind orphan SGs with `launch-wizard-N` naming pattern, visually indistinguishable from active SGs in the console list. |
| **Proper fix** | Delete `launch-wizard-2` from AWS EC2 Security Groups console (verify zero attachments first via `aws ec2 describe-instances --filters Name=instance.group-id,Values=<sg-id>`). ~2 min operator action. |
| **Impact if not fixed** | Cosmetic. Risk is recurrence of S39's debug pattern — future SG edits to launch-wizard-2 will have no effect and waste time. The IMDSv2 token query is now in operator memory as canonical attached-SG check so recurrence risk is bounded. |
| **Related** | §D.21.3 Assumption Register S39 (nginx default :80 inbound is sufficient for SG without verifying which SG is attached — REFUTED), ENH-110 Phase 1 AWS hosting infrastructure S39, MERDIAN_Deployment_Topology §1 (will gain note about IMDSv2 attached-SG verification pattern at S40 doc maintenance pass). |

---

### TD-S39-NEW-5 — Marketview "stale {N}s" badge contradicts 300s threshold setting — needs live-day verification

| | |
|---|---|
| **Severity** | S3 (verification-pending — could be legitimate genuine staleness post-market or display threshold not applying; impacts only operator's trust in freshness indicator) |
| **Filed** | 2026-05-27 (Session 39 — operator-visible during browser verification of Marketview at 03:36 IST post-market on a post-market data point) |
| **Symptom** | Marketview header strip shows badge "stale 612s" / "stale 314s" / "stale 295s" across multiple post-market browser refreshes on NIFTY view despite Lovable Turn 5 polish setting stale threshold from 60s → 300s and switching the canonical freshness clock from `market_state_ts` to `signal_snapshots.ts`. If signal_snapshots.ts genuinely is 10+ minutes stale post-market (market closes 15:30 IST, browser refresh at 15:35-15:55+ IST IST during S39), the badge is correctly firing as genuine staleness. If the 300s threshold is not actually applying (Lovable's change didn't reach this code path), the badge is firing spuriously at 5-10 min post-cycle window. Browser console + Network tab during operator session did not surface a clear answer. |
| **Workaround in place** | Operator-visible but not blocking — operator can interpret the badge as "data is N seconds stale, judge whether N is acceptable for current use case" without trusting the threshold semantics. |
| **Root cause** | Unknown without live-day verification. Three hypotheses: (a) threshold change applied but signal_snapshots.ts is genuinely 5-10 min stale during late-day windows because intraday cycles fire on 5-min cadence — within 300s threshold for the most-recent-cycle window but spilling over between cycles (legitimate); (b) Lovable's threshold change applied to wrong code path and the original 60s threshold still drives the badge logic; (c) threshold change applied but uses `Date.now()` vs `signal_snapshots.ts` in wrong direction (sign-flip) so it shows stale-when-fresh. Need live-day Network tab + JS console inspection to discriminate. |
| **Proper fix** | (a) S40+ live-day verification during 10:00-15:30 IST trading hours when cycles are firing every 5 min — observe whether badge stays under 300s during active cycles vs fires only after market close; (b) if badge stays under 300s during trading hours → label as legitimate post-market staleness, possibly update wording to "post-cycle Ns" or hide entirely outside market hours; (c) if badge fires spuriously during trading hours → Lovable Turn 7 prompt for debug + fix. ~15 min live-day observation + 0-15 min Lovable prompt. |
| **Impact if not fixed** | Operator-visible noise without operational impact during trading hours (operator interprets badge value not threshold semantics). Filed at S3 because reliable freshness indicator is a Phase 2 confluence-decision-quality property — operator needs to trust the badge for ENH-110 Phase 2 confluence detection rollout. |
| **Related** | ENH-110 Phase 1 Lovable Turn 5 polish prompt S39 (stale threshold 60s→300s + canonical clock signal_snapshots.ts), ADR-017 Operator Console Design Principles P5 motion-replaces-timestamps (badge is the motion-replacement-for-timestamp pattern; needs to be reliable to satisfy principle), Marketview surface at http://13.63.27.85/marketview. |

---

### TD-S38-NEW-1 — `MERDIAN_Intraday_Supervisor_Start` multi-trigger XML settings quirk blocks `Set-ScheduledTask` settings update

| | |
|---|---|
| **Severity** | S4 |
| **Filed** | 2026-05-26 (Session 38 — surfaced during TD-061 final long-tail closure review) |
| **Symptom** | `MERDIAN_Intraday_Supervisor_Start` (Weekly Mon-Fri 08:00 IST + AtLogon = two triggers) is the one task in the 20-task MERDIAN_* set without `Hidden=$true + MultipleInstances=IgnoreNew` applied via PowerShell `Set-ScheduledTask -Settings <obj>`. S29 `migrate_to_pythonw.ps1` v2 settings pass failed on this task only due to multi-trigger XML quirk in PowerShell where the cmdlet couldn't apply Settings cleanly to a multi-trigger task. Result: 19/20 tasks hardened, 1/20 retains loose settings. |
| **Workaround in place** | Task functions correctly otherwise; settings looseness affects only window-flash count and parallel-instance behavior — supervisor is by nature single-instance via internal lockfile so no operational impact today. Documented as known limitation in Topology §7.2. |
| **Root cause** | PowerShell `Set-ScheduledTask -Settings <CIM>` against a task with two triggers (Weekly + AtLogon) doesn't reconcile the `<Settings>` block cleanly — XML structure expects single-trigger or supports applications via full `Register-ScheduledTask -Xml` overwrite. Workaround documented in Topology §7.2 Note: build full Register-ScheduledTask XML + Force overwrite. |
| **Proper fix** | Build full `Register-ScheduledTask -Xml` with corrected `<Settings>` block + `-Force` overwrite. ~30 min when next operating on this task. Alternative: split into two separate tasks (one Weekly + one AtLogon) so each is single-trigger. |
| **Impact if not fixed** | None operational. Cosmetic — last 5% of TD-061 hardening. The task is PowerShell-by-design (`merdian_morning_start.ps1`) so cannot migrate to pythonw regardless. Filed for completeness only. |
| **Related** | TD-061 (RESOLVED-FINAL S38 — this is one of the 4 remaining non-pythonw tasks, the 1 with loose settings), Topology §7.2 (canonical 20-task inventory), CLAUDE.md v1.20 (S29 codification of the XML quirk as known limitation). |

---

### TD-S38-NEW-2 — Dead `TIMEOUT_LIVE_DEFAULT` + `TIMEOUT_SHADOW_DEFAULT` constants in `run_option_snapshot_intraday_runner.py`

| | |
|---|---|
| **Severity** | S4 |
| **Filed** | 2026-05-26 (Session 38 — surfaced during P6 read of runner source for Intraday_Session_Start migration decision) |
| **Symptom** | `run_option_snapshot_intraday_runner.py` lines 30-31 declare module-level constants `TIMEOUT_LIVE_DEFAULT = 240` and `TIMEOUT_SHADOW_DEFAULT = 180`; these constants are **never referenced anywhere in the file**. `grep -n TIMEOUT_LIVE_DEFAULT run_option_snapshot_intraday_runner.py` returns only the declaration line. |
| **Workaround in place** | None needed — dead constants have zero runtime impact. They appear to be leftover from an earlier iteration where per-step timeouts were computed from these defaults; the current code uses explicit per-step timeouts `TIMEOUT_BREADTH=300 / TIMEOUT_WCB=180 / TIMEOUT_INGEST=240 / TIMEOUT_ARCHIVE=180 / TIMEOUT_GAMMA=240 / TIMEOUT_VOL=240 / TIMEOUT_MOMENTUM=240 / TIMEOUT_STATE=240 / TIMEOUT_SIGNAL=240 / TIMEOUT_SHADOW_SIGNAL=180` instead. |
| **Root cause** | Refactor leftover — likely from a transition where timeouts were per-pipeline (live vs shadow) to per-step. The defaults survived the refactor unreferenced. |
| **Proper fix** | Either (a) delete the 2 dead lines, or (b) wire them to per-step timeouts that share the same value (e.g. `TIMEOUT_INGEST = TIMEOUT_LIVE_DEFAULT`) so the relationship is explicit. ~5 min in next writer refactor. |
| **Impact if not fixed** | None operational. Cosmetic code hygiene. Discovery cost is in the wasted grep when future Claude reads the file expecting these constants to drive behavior. |
| **Related** | TD-061 (RESOLVED-FINAL S38 — TD-S38-NEW-2 surfaced during the runner source read that informed Intraday_Session_Start migration option A vs B decision), `run_option_snapshot_intraday_runner.py` is the 5-min intraday cycle orchestrator (heartbeat of live pipeline). |

---

### TD-S38-NEW-3 — `ict_primitives × gamma_metrics` LATERAL joins need canonical helper view

| | |
|---|---|
| **Severity** | S3 |
| **Filed** | 2026-05-26 (Session 38 — recurrent correctness bug across Exp 53/53b/53c arc) |
| **Symptom** | Two independent correctness bugs surfaced when writing LATERAL joins between `ict_primitives` and `gamma_metrics` for research queries: (a) **Exp 53 v1 formation-anchor bug** — used `p.level` as formation anchor for proximity computation; `level` is NULL for ALL zone primitives (OB/FVG) which use `zone_low + zone_high`. Q-Disco-8 confirmed 0 of 1098 BEAR_FVG / 0 of 142 BEAR_OB / 0 of 1053 BULL_FVG / 0 of 189 BULL_OB populate `level`. Fix required `COALESCE(p.level, (p.zone_low + p.zone_high) / 2.0)`. (b) **Exp 53b/c classifier bin collision** — when `gamma_metrics.flip_level IS NULL` (NO_FLIP regime rows), proximity_pct computation returns NULL; the bin classifier put both `flip_proximity_pct IS NULL` rows AND `regime = 'NO_FLIP'` rows into the same `no_flip_data` bucket; turned out the bucket also accidentally caught rows where LATERAL matched gamma but flip_level was null. Required splitting `no_flip_regime` (intentional NULL via NO_FLIP) from `no_gamma_data` (missed LATERAL match). |
| **Workaround in place** | Both bugs fixed in-flight via SQL rewrites within session — Exp 53 final query uses `COALESCE` on level; Exp 53c uses split bin classifier `no_flip_regime` vs `no_gamma_data`. Future research queries that join these tables risk re-discovering both bugs. |
| **Root cause** | Schema conventions: (a) zone primitives store bounds not midpoint; level scalar is for point primitives (SWEEP); future ICT primitive types may add other anchor conventions. (b) Lateral predicate on `gamma_metrics.flip_level IS NOT NULL` is the cleanest filter but easy to forget; `regime = 'NO_FLIP'` rows still have positioning context (gamma_concentration etc.) just no flip-derived columns. |
| **Proper fix** | Create canonical helper view `v_ict_primitive_gamma_context` joining `ict_primitives` to `gamma_metrics` once with: (a) `COALESCE(level, (zone_low+zone_high)/2.0) AS formation_anchor` materialized; (b) `LEFT JOIN LATERAL` with `INTERVAL '2 hours'` lookback (handles M5 backward + H/D forward conventions); (c) explicit `regime` column passed through; (d) computed proximity columns for common anchors (flip_level, max_gamma_strike when ENH-80 cohort grows). Research queries then select from the view + apply filters per cohort. ~1-2 hour design + ship. |
| **Impact if not fixed** | Future research queries will re-discover one or both bugs. Cost is per-occurrence diagnostic time (Exp 53 arc spent ~1 hour on the two bugs across the 3 iterations). Filed at S3 because pattern is recurrent across research-tier work. |
| **Related** | Exp 53/53b/53c arc (S38 — surfaced the recurrence), ADR-004 Wave 1 (ict_primitives + ict_primitive_outcomes schema), ADR-002 v2 P5 PINNED state (NO_FLIP regime semantics), TD-S30-NEW-3 OB attachment broken at signal-builder layer (different but adjacent — same family of join-correctness issue at consumer side). |

---

### TD-S37-01 — Hardcoded τ_pin = τ_accel = 0.3 in ENH-81 SQL views; formalize as `merdian_parameters` lookup when ENH-83 builds

**RESOLVED Session 40 (2026-05-29).** Full closure block is in the **Resolved (audit trail)** section below. Two ENH-81 view DDLs (`v_gex_strike_pin_zone` + `v_gex_strike_accel_zone`) patched via `patch_s40_enh83_view_tau_rewrite.py` (BOM-safe, predominant-EOL preservation, AST-validate, `_PRE_S40.sql` backups, idempotency guard, ASCII-clean): two surgical replacements of `0.3::numeric AS tau_pin` → `get_parameter_num('pin.tau.'||p.symbol)::numeric AS tau_used` and `0.3::numeric AS tau_accel` → `get_parameter_num('accel.tau.'||p.symbol)::numeric AS tau_used`. Both view DDLs re-applied via Supabase SQL editor → smoke-fire SQL verified `tau_used = 0.30` rendered correctly in both views for NIFTY + SENSEX cross-symbol against live `merdian_parameters` rows. `// TAU_PIN — swap for ENH-83 lookup` markers removed from view bodies. Calibration round-trip 0.30→0.25→0.30 verified via the now-functional `update_parameter` RPC (TD-S40-NEW-2 fix landed in same session to make this round-trip possible).

| | |
|---|---|
| **Filed** | 2026-05-25 (Session 37 — ENH-81 Positioning Landscape SHIPPED with hardcoded prominence threshold per ADR-016 build deferral). |
| **Severity** | S3 (correctness is fine at single-cohort scale; calibration brittleness shows up only when cohort grows or regime changes enough that 0.3 stops being the right τ). |
| **Symptom** | Three ENH-81 SQL views (`v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`, `v_dealer_flow_sim`) carry the prominence-around-peak threshold τ = 0.3 inline in CASE expressions and recursive CTE bounds. No parameter-table lookup; no audit trail on the value; no per-symbol calibration capability. |
| **Root cause** | ADR-016 parameter calibration pattern PROPOSED S37 but build deferred per operator — hardcoded τ=0.3 is sufficient for current single-cohort use. ENH-81 ships with `// TAU_PIN — swap for ENH-83 lookup` markers at every site in the view DDLs, recording the future plumb-point mechanically. |
| **Workaround** | Marker pattern is the workaround. Every site that reads τ has the inline comment; grep for `TAU_PIN` returns every site that must be touched when ENH-83 graduates. Prevents τ from drifting into magic-number territory while keeping the calibration build queued. |
| **Owner** | Navin / Claude — ENH-83 calibration console build is the canonical closure path. |
| **Fix path** | (1) ADR-016 graduates from PROPOSED to ACCEPTED when N grows enough for cohort-driven recalibration to become useful. (2) ENH-83 build (~half-day): `merdian_parameters` table DDL + `core/parameters.py` TTL-cached read API + `merdian_calibrate.py` CLI + 7 unit tests + bootstrap seeds for `pin_zone.tau.NIFTY`, `pin_zone.tau.SENSEX`, `accel_zone.tau.NIFTY`, `accel_zone.tau.SENSEX`. (3) ENH-81 view DDLs updated to call `get_parameter('pin_zone.tau.<symbol>')` instead of literal `0.3`; markers removed. |
| **Lessons** | Calibration-deferred-by-design pattern works iff the deferral is marked mechanically at every value-site. `// TAU_PIN — swap for ENH-83 lookup` comments are the discipline that prevents 6-12 month archaeology when the plumb finally happens. Codified §D.19.1 + ADR-016 + Doc Protocol v4 candidate Rule N+1. |
| **Related** | ADR-016 PROPOSED (parent decision), ENH-83 (target build — graduated PROPOSED→SHIPPED S39 via Lovable-scaffolded `merdian_parameters` + S39 trimmed ALTER); ENH-81 (views consuming τ — now reading from `merdian_parameters` runtime); D.19.1 (minimum-sufficient-statistic at write layer / derivations in views); D.22.1 (Lovable `valid_to DEFAULT now()` REFUTED-S40 — surfaced by this TD's closure smoke-fire). |

### TD-S37-02 — §F1 dealer-vs-positioning GEX split scaffolded via `v_oi_prev_close_snapshots` view; writer integration deferred

| | |
|---|---|
| **Filed** | 2026-05-25 (Session 37 — `v_oi_prev_close_snapshots` view shipped as scaffold for future dealer-vs-positioning research per ADR-015 §F1; writer integration into `gex_strike_snapshots` deferred). |
| **Severity** | S3 (research-grade dimension not consumed by production; no impact on display layer or operator workflow at S37 close). |
| **Symptom** | ADR-015 §F1 specifies dealer-vs-positioning GEX split as a future write-layer extension; current `gex_strike_snapshots` schema does not carry the dealer-vs-positioning breakdown per strike. `v_oi_prev_close_snapshots` view computes OI-change-per-strike-per-day from `option_chain_snapshots` as a proxy substrate for dealer-flow research but is not wired into the writer. |
| **Root cause** | Two open design questions blocked the writer integration: (a) sign convention for dealer-vs-positioning at the per-strike row level — same row carries both writer's perspective (sold to dealer = liability + dealer hedges by buying stock = positive dealer-side gamma) and positioning perspective (held by buyer = no hedge needed); the per-strike split has two-axis ambiguity not present in net GEX; (b) OI-change history wiring — `v_oi_prev_close_snapshots` provides one day's worth of OI delta but multi-day persistence vs intraday rotation requires window definition. |
| **Workaround** | View ships as scaffold-only; consumers can join `v_oi_prev_close_snapshots` against `gex_strike_snapshots` ad-hoc for prototype dealer-flow research; production-grade integration deferred until both design questions resolve. |
| **Owner** | Navin / Claude — design decision required on sign convention + OI-change window definition before writer build. |
| **Fix path** | (1) Operator decision on whether dealer-vs-positioning split warrants own columns vs sibling table vs computed view. (2) Sign convention specification (suggested: positive `dealer_gex_cr` = dealer-net-long-gamma = dampening contribution; negative = dealer-net-short-gamma = amplifying contribution). (3) OI-change window definition (suggested: prev-close OI as baseline, intraday delta computed against baseline). (4) Writer extension or sibling-table writer. (5) Pine overlay + Lovable dashboard exposure (deferred per GEX-as-context-not-gate per D.19.3). |
| **Lessons** | When a design specification has a clear research substrate but unresolved schema-level ambiguity, ship the substrate (view) and defer the schema decision; document the ambiguity in the TD for future operator resolution. Avoids the failure mode of shipping a schema decision that needs reversal under N+1 weeks of research evidence. |
| **Related** | ADR-015 §F1 (parent specification), ADR-002 v2 P5 (PINNED state), D.19.3 (GEX-as-context-not-gate — dealer-vs-positioning is research-grade not gate-grade). |

### TD-S37-03 — Lovable anon-key brittleness: RLS misconfiguration produces silent empty datasets, not auth errors

| | |
|---|---|
| **Filed** | 2026-05-25 (Session 37 — Lovable dashboard build surfaced RLS-vs-anon-key interaction class). |
| **Severity** | S3 (production dashboard is live and correct after RLS triplet shipped per-table; the failure mode is for future view deploys, not current consumer state). |
| **Symptom** | Lovable client uses Supabase `anon` key directly. When a new table/view is deployed without the RLS triplet (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `CREATE POLICY ... FOR SELECT TO anon USING (true)` + `GRANT SELECT ... TO anon`), the dashboard shows empty datasets — no errors, no auth warnings, no telemetry. The failure mode is silent and looks identical to "the query has no matching rows," which is the failure mode operator is trained to look for first when data is missing. |
| **Root cause** | PostgREST + Supabase RLS default-deny semantics: an anon-key request against a table with no policy and no grant returns 200 OK with empty array `[]` (the rows the anon role can see — zero by default). The dashboard receives a well-formed empty response and renders "no data" rather than surfacing the misconfiguration. |
| **Workaround** | Document the exact three-line RLS triplet inline in commit message for every new public-facing table/view. Smoke-test via direct anon-key probe (`curl -H "apikey: <ANON_KEY>" ... | jq length` should return non-zero before deploying any new view to Lovable). |
| **Owner** | Navin / Claude — operational discipline at deploy time, not a code-level fix. |
| **Fix path** | (1) Per-table RLS+GRANT triplet documented inline in commit message at deploy time (S37 pattern). (2) Optional: extend `merdian_daily_audit.py` with a Lovable-anon probe check — N row counts on each known public view via anon key; if any returns 0 unexpectedly, raise WARN. (3) Optional: PostgREST schema-level audit query enumerating all tables/views with anon SELECT grant but no RLS policy (or vice versa) — possible drift detector. |
| **Lessons** | Read-only consumer-facing dashboards on Supabase fail silently on RLS misconfiguration. The fix is operational discipline (documented RLS triplet + smoke-test) not a code-level diagnostic. Codified §D.19.3 + S37 settled-decisions Lovable RLS pattern bullet. Pattern generalizes — any new anon-key-consuming surface (future Pine-overlay-as-API, future external dashboards) needs the same triplet + smoke-test discipline. |
| **Related** | D.19.3 (GEX-as-context-not-gate / Lovable display layer), ENH-81 (the dashboard whose deploy surfaced this), B19 (anti-pattern bugs ship in N silent siblings — the silent-empty-response failure mode generalizes to other anon-key consumers). |

### TD-S36-NEW-1 — `gamma_metrics` Apr-early-May 2026 row gap (residual from TD-S30-CANDIDATE-1 cleanup)

| | |
|---|---|
| **Filed** | 2026-05-25 (Session 36 — surfaced during TD-S30-CANDIDATE-1 closure as the residual that could not be recomputed). |
| **Severity** | S3 (architectural gap not blocking — affects historical magnitude analysis on a ~10-week window only; no consumer relies on this window for live decision-making). |
| **Component** | `gamma_metrics` table — Apr-early-May 2026 window (specifically `ts >= '2026-04-01' AND ts < '2026-05-12'`); upstream dependency `hist_option_bars_1m` (vendor tier, sparse post-Apr-2026 per TD-S35-NEW-1 strike-coverage limit). |
| **Symptom** | ~4,300 rows in the Apr-early-May 2026 window were DELETEd at S36 close as confirmed raw-rupee gaps (live writer pre-S27 wrote in raw rupees; that window cannot be recomputed because vendor `hist_option_bars_1m` is sparse post-Apr-2026 — backfill execution returns 0 chain bars on these dates). Post-S36 cleanup: `gamma_metrics` rows in this window are missing entirely, not present-but-wrong. |
| **Root cause** | Compositional — pre-S27 live writer wrote raw-rupees here (D.18.1 lesson source) AND vendor coverage drops at the same boundary (TD-S35-NEW-1 / D.17.2 lesson source). Recomputable only via an alternate post-Apr-2026 chain-data source. |
| **Workaround** | (a) Cohort analyses on `gamma_metrics` exclude the Apr-early-May 2026 window explicitly. (b) HOCS dual-source-reader pattern from ENH-106 v8 could theoretically be ported to `compute_gamma_metrics_local`, but cycles/day cost is higher than reading from vendor 1m bars. |
| **Proper fix** | Same recovery path as TD-S35-NEW-1 — graduate Breeze full-chain historical data via ADR-013 + ENH-109. Once ADR-013 graduates (n≥3 successful Breeze-tier backfills accumulated), this gap is closeable by running `backfill_gamma_metrics_to_main.py` against a Breeze-sourced chain table (or HOCS extension covering this window). Cost ~0.5 session within the Breeze-fallback validation cycle. |
| **Cost to fix** | ~0.5 session inside Breeze graduation cycle; standalone fix not warranted. |
| **Blocked by** | TD-S35-NEW-1 / ADR-013 graduation. |
| **Owner check-in** | 2026-05-25 (S36) — filed at session close. |

---

### TD-S36-NEW-2 — `MERDIAN_Dhan_Token_Refresh` Task Scheduler task not instrumented to `script_execution_log`

| | |
|---|---|
| **Filed** | 2026-05-25 (Session 36 — surfaced during ENH-99 failure-shape diagnosis on `script_execution_log`). |
| **Severity** | S3 (operational visibility gap — token-refresh script runs daily but its lifecycle is invisible to the daily audit pipeline that scans `script_execution_log`; the `dhan_token_probe_log` instrumentation S29 captures post-refresh probe results but not script-execution lifecycle). |
| **Component** | `pull_token_from_supabase.py` (Local) — invoked by `MERDIAN_Dhan_Token_Refresh` Task Scheduler task. |
| **Symptom** | Script does not emit `script_execution_log` rows on start/exit. Daily audit cannot detect: (a) task fired but script crashed at import; (b) task did not fire due to Task Scheduler state; (c) script ran but did not produce expected `dhan_token_probe_log` entry. Currently audit relies solely on `dhan_token_probe_log` populated downstream, which is fragile (it cannot distinguish "task didn't fire" from "task fired but probe write failed"). |
| **Root cause** | Script predates the `script_execution_log` instrumentation pattern; never retrofitted. |
| **Workaround** | (a) `dhan_token_probe_log` view `v_dhan_token_probe_today` serves as a partial proxy — if today's probe row is missing, something is wrong upstream. (b) Manual Task Scheduler History inspection. |
| **Proper fix** | Add standard `script_execution_log` start/end instrumentation pattern at top + bottom of `pull_token_from_supabase.py` matching the convention used by `capture_spot_1m_v2.py`, `ingest_option_chain_local.py`, etc. ~30 min including `_PRE_S37.py` backup + AST validation + smoke-fire test. |
| **Cost to fix** | ~30 min next time operating on the token-refresh path. |
| **Blocked by** | Nothing. |
| **Owner check-in** | 2026-05-25 (S36) — filed at session close. |

---

### TD-S36-NEW-3 — `dhan_token_probe_log` forward-only from 2026-05-10 (pre-S29 token incidents invisible)

| | |
|---|---|
| **Filed** | 2026-05-25 (Session 36 — surfaced during ENH-99 failure-shape diagnosis on Mode B 401 history). |
| **Severity** | S4 (documentation-only gap — the table was instrumented S26 commit `718ef39` for forward visibility, not as a historical reconstruction tool; pre-S29 incidents like the 2026-05-07 storm referenced in D.18.2 are visible only via `script_execution_log.exit_reason='TOKEN_EXPIRED'` rows). |
| **Component** | `dhan_token_probe_log` table — first probe row 2026-05-10 20:28 IST. |
| **Symptom** | Any query against `dhan_token_probe_log` looking for token-health history before 2026-05-10 returns empty. Cohort analysis of "how many 401 incidents pre-S29" must use `script_execution_log` alone. |
| **Root cause** | S26 instrumentation was forward-only by design — probe logs the result of `pull_token_from_supabase.py` execution; pre-deployment, the probe didn't exist. |
| **Workaround** | Use `script_execution_log.exit_reason='TOKEN_EXPIRED'` and `error_message LIKE '%401%'` filters for pre-2026-05-10 history; correlation across symbol/script paths must be done manually. |
| **Proper fix** | None warranted — historical reconstruction would require synthesizing probe-log rows from `script_execution_log` records, which is more work than the analytical value justifies. Documentation-only — file as known gap in System Map §B.10. |
| **Cost to fix** | N/A — accepted as architectural design of forward-only instrumentation. |
| **Blocked by** | Nothing. |
| **Owner check-in** | 2026-05-25 (S36) — filed at session close. |

---

### TD-S36-NEW-4 — `script_execution_log.duration_ms` is int4; orphan-recovery durations exceeding ~24 days overflow on PG write
> **RESOLVED Session 55 (2026-06-17).** ALTER TABLE script_execution_log ALTER COLUMN duration_ms TYPE bigint (int4->int8 widening, non-destructive; confirmed bigint). Latent overflow removed; schema now safe for NEW-5 option-A orchestrator self-instrumentation.

| | |
|---|---|
| **Filed** | 2026-05-25 (Session 36 — surfaced during `orphan_run_janitor.py` v3 smoke-fire as PG `22003 numeric_value_out_of_range` errors). |
| **Severity** | S3 (operational pattern works around it via write-time clamp at `2^31 - 1`; schema-level fix is straightforward but non-urgent). |
| **Component** | `script_execution_log.duration_ms` schema column type (PG `int4` / `INTEGER` per `information_schema.columns`). |
| **Symptom** | Any writer computing `(now - started_at)` in milliseconds and writing to `duration_ms` will hit PG `22003 numeric_value_out_of_range` for durations > `2^31 - 1 = 2,147,483,647 ms` ≈ 24.85 days. Affects any script that started, blocked > 24 days, and tries to write its own duration at end — and any janitor / cleanup logic computing the same delta. |
| **Root cause** | Schema choice predates the long-running script reality; int4 is sufficient for normal-cadence scripts (max few-hour durations) but underflows on stuck/orphaned long-duration runs. |
| **Workaround** | Write-time clamp at `2^31 - 1` (codified §D.18.4 + applied in `orphan_run_janitor.py` v3): `age_ms = min(int((now - started_at).total_seconds() * 1000), 2_147_483_647)`. Any new writer in similar shape should apply the same clamp. |
| **Proper fix** | `ALTER TABLE script_execution_log ALTER COLUMN duration_ms TYPE bigint USING duration_ms::bigint;` — int4 → int8. DDL change is straightforward; backfill is identity (no data transformation needed). One-shot migration ~5min wallclock. Update writer convention thereafter to drop the clamp. |
| **Cost to fix** | ~30 min including migration + verification + writer convention update. Not urgent — clamp pattern works. |
| **Blocked by** | Nothing. |
| **Owner check-in** | 2026-05-25 (S36) — filed at session close. |

---
### TD-S35-NEW-1 — `historical_option_chain_snapshots` strike-coverage structural limit on MERDIAN-ingest tier

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 35) |
| **Severity** | S2 |
| **Component** | `historical_option_chain_snapshots` (HOCS, post-Apr-2026 chain data); `ingest_option_chain_local.py` (live writer producing HOCS rows). |
| **Symptom** | Post-S35 full recompute on the v8 dual-source reader recovered 317/541 (58%) post-Apr-2026 retests to non-NULL `option_pnl_*`; +14 via Breeze 2026-04-16 surgical fill = 331/541. Of remaining 210 NULL post-Apr retests: 132 are level primitives (PDH/PDL/PWH/PWL/PMH/PML — direction=NONE, architecturally exempt). True residual ≈75 zone-primitive retest NULLs spread across post-Apr-2026 dates. Diagnostic partition by `formation_atm_status` shows the failures predominantly `formation_OK_retest_FAIL` or `formation_TOTAL_FAIL` for primitives whose spot drift from formation to retest exceeded the live writer's strike capture window. |
| **Root cause** | `ingest_option_chain_local.py` captures an **ATM±N strike window per 5-min cycle** (N a constant in the writer — observably ~10-15 strikes either side of running ATM based on HOCS row counts). When a primitive forms at spot X and is retested at spot X + ΔX such that the held-strike (the ATM strike at formation) falls outside the ATM±N window at retest moment, the live writer never captured that strike's 5-min snapshot at retest_5m. The chain prefetch in `_prefetch_chain_for_primitives` (ENH-106 v8 path) finds no row for (held_strike, retest_5m) in HOCS — premium lookup returns NULL → outcome columns NULL. This is a property of the live writer's capture configuration, not a defect of the reader. |
| **Impact** | (a) Permanent ceiling on post-Apr-2026 cohort coverage from MERDIAN-ingest tier alone; ~75 retests across the post-Apr-2026 window (~14% of the 541-retest cohort) in the long-spot-drift regime. (b) ADR-012 spot-anchored SL doctrine validation cohort unaffected (n=65 W+D+H zone retests clears n≥50 threshold). (c) Phase 3 GEX time-series build per ADR-002 v2 affected if it requires dense full-chain history. (d) Selection-research arc per D.16.2 / ENH-108 unaffected in spirit but the missed primitives represent a non-random sample (large-drift trades). |
| **Workaround** | (a) Restrict cohort analyses to retests where formation and retest spot are within roughly ±2%. (b) Surgical Breeze backfill per affected (date, strike, expiry, opt_type) tuple via `fill_2026_04_16_breeze_v3.py` analog. (c) Accept the residual as architectural limit of MERDIAN-ingest tier and document in cohort summaries. |
| **Proper fix** | Two paths: (1) **Widen the live writer's strike window** in `ingest_option_chain_local.py` from ATM±N to ATM±2N or symbol-aware ATM±(N + spot_volatility×factor); ~1 session investigation + writer patch + 2-3 weeks observation; storage cost roughly doubles for HOCS (~5.3 GB instead of 2.67 GB). (2) **Graduate Breeze rollingoption / get_historical_data_v2 to canonical historical backfill source** per ADR-013 PROPOSED + ENH-109; replaces MERDIAN-ingest tier as the post-Apr-2026 canonical, retains live writer only for real-time intraday consumption. Cost ~2-3 sessions (Breeze fetcher build + scheduler + verification cohort). |
| **Cost to fix** | Path 1: ~1-1.5 sessions + ongoing storage. Path 2: ~2-3 sessions + ongoing Breeze quota management (5000 calls/day). |
| **Blocked by** | Path 1 unblocked. Path 2 blocked on ADR-013 acceptance + n≥3 successful Breeze-tier backfills. |
| **Owner check-in** | 2026-05-24 (S35) — filed at session close; decision deferred to S36+. |

---

### TD-S35-NEW-2 — Pre-Apr-2026 vendor uncatalogued in System Map (critical institutional knowledge at risk)

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 35) |
| **Severity** | S1 |
| **Component** | `hist_option_bars_1m` (54.8M rows pre-Apr-2026); `hist_atm_option_bars_5m` (vendor aggregation source); `hist_spot_bars_5m` + `hist_spot_bars_1m` (pre-Apr vendor spot data); `MERDIAN_System_Map.md` (documentation gap). |
| **Symptom** | The pre-2026-04-01 chain history in `hist_option_bars_1m` (54.8M rows / paid through 2026-04-07) was discovered by S35 diagnostic to be vendor-purchased ("we paid for it" per operator) but the vendor identity, contract terms, renewal cadence, refresh cadence, data format spec, exchange-mappings (`stock_code` conventions), and contact details are NOT documented in MERDIAN_System_Map.md or MERDIAN_Deployment_Topology.md. Currently this is the only known retail-accessible source for full-chain SENSEX history >2 years; the source is critical for all pre-Apr-2026 cohort work (every prior ENH-100/103/106 study + ADR-009 holdout splits + ADR-011 chain-table held-strike doctrine + S33 retest-cohort validation depends on it). |
| **Root cause** | Documentation gap — the vendor was integrated when MERDIAN was younger and the cataloguing discipline that produced System Map / Topology was not yet established. Through 5+ sessions of working with this table, the vendor identity has been referenced verbally between Navin and Claude but never written down. Bus-factor of one. |
| **Impact** | (a) Knowledge-loss risk: vendor identity, contract terms, refresh cadence not preserved anywhere outside operator memory; renewal cycle / contract end-date unknown to the documented system. (b) Any future investigation of "why did `hist_option_bars_1m` stop updating?" or "can we extend the contract?" requires operator manual recall. (c) ADR-013 PROPOSED (Breeze canonical historical backfill) — its rationale and replacement-cost analysis cannot be made cleanly without documenting what's being replaced. (d) If operator becomes unavailable, future Claude sessions will have to re-derive the vendor identity from external context, which may not be possible. |
| **Workaround** | None — the gap is documentation, not code. |
| **Proper fix** | Add a vendor catalog section to `MERDIAN_System_Map.md` (or new `MERDIAN_Vendor_Registry.md` if scope warrants): vendor identity, contract terms, refresh / delivery cadence, data format spec, `stock_code` mappings, contact info, renewal date, contingency / replacement options (ENH-109 Breeze graduation). Per Doc Protocol v4 Rule 7 (System Map currency). |
| **Cost to fix** | ~15-30 min operator time to dictate vendor details; ~30 min Claude time to write the catalog entry. |
| **Blocked by** | Operator availability for the dictation session. |
| **Owner check-in** | 2026-05-24 (S35) — filed at session close; S36+ scheduling. |

---

### TD-S35-NEW-3 — SENSEX symbology on ICICI Breeze API: `stock_code="BSESEN"` not `"SENSEX"`, undocumented in Breeze public docs

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 35) |
| **Severity** | S4 |
| **Component** | ICICI Breeze API (`breeze-connect` SDK ≥1.0.69); `fill_2026_04_16_breeze_v3.py` (S35 backfill script); future SENSEX-on-Breeze consumers. |
| **Symptom** | During S35 Breeze surgical fill of 2026-04-16 chain gap, NIFTY worked with `stock_code="NIFTY" exchange_code="NFO"` returning full chain data; SENSEX returned empty `Success=[]` with `Status=200` (not an error, just no data) for every (`stock_code`, `exchange_code`) combination tested in the obvious mapping space. Empirical 6-variant probe (`SENSEX/BFO`, `SENSEX/NFO`, `SNSXIN/BFO`, `BSXSEN/BFO`, `BSESEN/BFO`, `BSESNS/BFO`) found `stock_code="BSESEN"` with `exchange_code="BFO"` as the only working combination — returns the expected ~30-strike full chain. The string `BSESEN` is not present in Breeze's official documentation pages (`api.icicidirect.com/breezeapi/documents/`) or any public ICICI Direct integration material that operator or Claude could locate. |
| **Root cause** | ICICI Direct internal symbology — `BSESEN` is the BSE-internal symbol for the SENSEX index option series on the Breeze API surface. Vendor-internal naming with documentation gap on Breeze's side. |
| **Impact** | (a) Any future SENSEX-on-Breeze code-path will hit the same dead end without the empirical knowledge. (b) ADR-013 (Breeze canonical historical backfill) when it graduates to canonical will need this codified. (c) If Breeze deprecates or renames `BSESEN`, MERDIAN's Breeze paths break silently (returns empty Success not error). |
| **Workaround** | None — the working value is `BSESEN`; no alternative path. |
| **Proper fix** | Add a "Breeze symbology" section to MERDIAN_System_Map.md (or `MERDIAN_Deployment_Topology.md` §Breeze) codifying: NIFTY=`NIFTY`/`NFO`, SENSEX=`BSESEN`/`BFO`. Update `fill_2026_04_16_breeze_v3.py` `SCOPE` constant docstring to flag the symbol mapping as TD-S35-NEW-3-canon. Add to any future Breeze fetcher script (ENH-109) the mapping as a `BREEZE_SYMBOL_MAP` constant at module top. |
| **Cost to fix** | ~10 min documentation; ~5 min code-comment addition. |
| **Blocked by** | Nothing. |
| **Owner check-in** | 2026-05-24 (S35) — filed at session close. |

---

### TD-S35-NEW-4 — `build_ict_primitives.py` writer is INSERT-only on `ict_primitive_outcomes`; schema column additions do not backfill existing rows

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 35) |
| **Severity** | S3 |
| **Component** | `build_ict_primitives.py` (`upsert_outcomes` function); `ict_primitive_outcomes` table schema-add workflow. |
| **Symptom** | S35 verification of ENH-106 v8 dual-source reader and ADR-012 v9 SL writer both required separate manual `DELETE FROM ict_primitive_outcomes WHERE primitive_id IN (...)` SQL operations on the test cells before re-running the writer — because the writer's `upsert_outcomes` function is INSERT-only with existence-check semantics: rows whose `primitive_id` already exist in the outcomes table are skipped silently (logged as "inserted 0 outcomes"), so newly-added schema columns on those existing rows never get populated. For the v8 single-cell test on 2026-05-14 NIFTY M5, the writer ran cleanly, logged "inserted 0 outcomes," and the freshly computed `option_pnl_source` + `option_pnl_*` columns silently never landed in DB. Same issue blocked ADR-012 v9 verification until similar DELETE was run on the same cell. |
| **Root cause** | `upsert_outcomes` was written with INSERT-only idempotency semantics for compose-with-detector recompute workflows; the assumption was that an existing outcome row is canonical and should not be touched (preserving order of arrival of detections during streaming/batch runs). The assumption breaks when *new schema columns* are added — the existing row has NULL on the new column, the writer skips the row, and the column never populates. Fundamentally a column-add-without-upsert anti-pattern in the writer architecture. |
| **Impact** | (a) Every schema-add session (ENH-100 v3, ENH-103 v6, ENH-106 v8, ADR-012 v9) requires either TRUNCATE + full recompute (~30-60 min wallclock) OR per-cohort DELETE + targeted recompute as a manual step before populated rows appear. (b) Confusing during verification — "inserted 0 outcomes" log is misleading when intent was "update existing rows with new schema columns." (c) Existing 19,571 S35 outcomes do not have v9 sl_* columns populated until S36 TRUNCATE-and-rebuild executes. |
| **Workaround** | Manual DELETE before recompute on the affected cohort; for full schema-add deployment, TRUNCATE + full backfill. |
| **Proper fix** | Three options: (a) **Switch `upsert_outcomes` to UPSERT semantics on schema-stable columns** — explicit `INSERT ... ON CONFLICT (primitive_id) DO UPDATE SET <changed_cols>`; preserves idempotency for compose-with-detector workflows while allowing schema-add backfills. (b) **Add a "force_update" mode** — `MERDIAN_OUTCOMES_FORCE_UPDATE=1` env flag that switches the writer to UPDATE-or-INSERT for the duration of a session; sticks with INSERT-only default. (c) **Add a separate `backfill_outcomes_columns.py` helper** that re-computes only the new columns via SQL UPDATE join, bypassing the writer entirely. Option (c) is the lightest-weight + matches existing pattern of one-off backfill helpers. |
| **Cost to fix** | (a) ~1 session writer refactor + comprehensive smoke testing. (b) ~30 min env-flag + branch in upsert_outcomes. (c) ~1-2 hour helper script per schema-add (no writer change). |
| **Blocked by** | Nothing structurally; design decision needed. Option (c) is lowest-risk for S36 ADR-012 v9 cohort population (do TRUNCATE + full recompute as plan-of-record, defer fix to follow-on session). |
| **Owner check-in** | 2026-05-24 (S35) — filed at session close. |

---

### TD-S34-NEW-4 — `hist_option_bars_1m` post-2026-04-01 coverage gap (vendor → MERDIAN-ingest tier transition)

| | |
|---|---|
| **Filed** | 2026-05-24 (Session 34) |
| **Severity** | S2 |
| **Component** | `hist_option_bars_1m` chain table (54.8M rows pre-Apr-2026); MERDIAN chain ingest pipeline (post-Apr-2026 writer path, location TBD). |
| **Symptom** | Two-query diagnostic on S34 backtest (SL-fix on 7-day retest cohort) returned ZERO rows for both NIFTY and SENSEX on all nine probed post-2026-04-01 dates: 2026-04-01, 04-07, 04-09, 04-13, 04-16, 04-24, 05-12, 05-14, 05-18. Pre-2026-04-01 dates in the same cohort (2025-05-08 through 2026-01-20) returned full chain data — entry premium, intraday walk, EOD close all populated. The 22-row retest cohort assembled from `ict_primitive_outcomes.first_retest_ts` on ≥1% move-days collapsed to 7 usable rows; the 15 lost rows all fall in the post-Apr-2026 window. |
| **Root cause (operator framing 2026-05-24)** | Pre-Apr-2026 chain data is **vendor-purchased** — full, validated, dense across the 12-month window the operator paid for and verified. Post-Apr-2026 chain data is **MERDIAN-ingested** via a different writer path (location TBD — either a separate table/schema not under the same name, or a partial ingestion failure into `hist_option_bars_1m`). The "MERDIAN failed to ingest entirely" framing cannot be the full picture — plenty of full-ingestion days have been observed post-Apr-2026 elsewhere in the system (S29-S33 cohort work consumed data from that window). The gap is therefore *either* a storage-path mismatch (post-Apr-2026 chain data lives in a sibling table/location and `hist_option_bars_1m` writer was never extended to the new ingest tier) *or* partial-ingest failure scoped to a subset of dates within the writer's actual coverage. Initial framing of "Kite token expiry on MALPHA (TD-080-adjacent)" was incorrect — corrected per operator 2026-05-24. |
| **Impact** | (a) Backtest cohorts spanning the tier transition are artifically truncated — any retest cohort or primitive-outcomes consumer that touches post-Apr-2026 dates loses option-PnL columns silently. (b) ADR-009 holdout windows that include post-Apr-2026 lose their option-PnL anchor for affected primitives. (c) ENH-103/106 v7 outcomes for any primitive retested post-Apr-2026 are NULL on the 5 option-PnL columns — the affected cohort size is not yet quantified. (d) S34 spot-anchored SL doctrine validation (n=7) cannot expand to n≥50 until the gap closes — directly blocks the doctrine's promotion from "finding" to "validated rule." |
| **Workaround** | Restrict backtests and cohort selection to `trade_date <= '2026-03-30'` until the gap is diagnosed and closed. Document the transition date in any cohort summary so consumers of derived stats know they're operating on a truncated window. |
| **Proper fix** | Three sub-steps: (1) **Diagnose the tier transition** — locate where post-Apr-2026 chain data actually lives (separate table name? separate schema? in-process writer that targets `hist_option_bars_1m` but fails on specific dates?). Inspect MERDIAN chain-ingest writer code-paths + scheduler history + DB schema for sibling tables. (2) **Unify the storage** — if data lives elsewhere, migrate or shadow-write to `hist_option_bars_1m` so the canonical chain table reflects the full window. If partial-ingest, fix the failure mode + backfill missing dates via `backfill_option_zerodha_OI_FIXED.py` analog. (3) **Re-run ENH-106 v7 outcomes pass** against primitives retested in the post-Apr-2026 window to populate the option-PnL columns. |
| **Cost to fix** | ~1 session diagnostic (locate the post-Apr-2026 data) + ~1 session unification/backfill + ~30 min compute for outcomes recompute. Total 1-2 sessions assuming no surprise complications during diagnostic. |
| **Blocked by** | Nothing structurally; diagnostic can begin immediately. If diagnostic reveals MALPHA Zerodha token issues for the ingest path, work merges with TD-NEW-7 (token automation, S29+). |
| **Owner check-in** | 2026-05-24 — pending S35+ schedule. |
| **Resolution (S35 2026-05-24)** | **CLOSED-MECHANICAL.** Diagnosis confirmed two-tier architecture: pre-Apr-2026 chain lives in `hist_option_bars_1m` (vendor-purchased, 54.8M rows, uncatalogued vendor — filed as TD-S35-NEW-2); post-Apr-2026 chain lives in **`historical_option_chain_snapshots` (HOCS)** — 2.67M rows / 2.67 GB / 41 trading days at 5-min cadence keyed on `symbol` text not `instrument_id` uuid, `ltp` not `close`, written by `ingest_option_chain_local.py`. Calendar overlap clean on the boundary (NIFTY HOCS first expiry 2026-03-24 / SENSEX 2026-03-19; vendor last expiry 2026-04-07 NIFTY / 2026-04-02 SENSEX). Writer-side fix: `ENH-106 (S35) v8` adds boundary 2026-04-01 UTC + per-tuple split routing (pre→vendor 1m / post→HOCS 5m / mixed→both); `v8.1` UNION'd expiry calendars; `v8.2` swapped HOCS pagination for RPC `get_hocs_distinct_expiries(text)` + `(symbol, expiry_date)` covering index (sub-100ms vs 9-15 min). New audit column `option_pnl_source TEXT` values `vendor_hist_1m` / `merdian_hist_5m` / NULL. Full recompute S35: 19,571 outcomes (NIFTY 8,925 + SENSEX 10,646) in 2,107s; 1,716,572 pre bars + 49,204 post cycles across 2,773 (strike, expiry, type) tuples. 2026-04-16 single-day true gap filled via Breeze surgical write (107,630 HOCS rows: NIFTY 61,899 + SENSEX 45,731). Post-Apr retest cohort recovery 317/541 mechanical + 14 Breeze 04-16 = 331/541. Zone-primitive denominator (excluding 132 architecturally-exempt level primitives — direction=NONE, no CE/PE mapping): 331/409 = **81% recovery**. Residual 75 NULL post-Apr zone-primitive retests attributed to HOCS strike-coverage structural limit (`ingest_option_chain_local` captures ATM±N strike window, retests with large spot drift miss held-strike); filed as TD-S35-NEW-1. Earlier "Kite token expiry on MALPHA (TD-080-adjacent)" framing remains superseded. |

---

### TD-S33-NEW-1 — `hist_atm_option_bars_5m` reason-to-exist re-evaluation post-wick-experiment retirement

| | |
|---|---|
| **Filed** | 2026-05-22 (Session 33) |
| **Severity** | S3 (orphan-candidate; non-blocking) |
| **Component** | `hist_atm_option_bars_5m` table (27,082 rows), written by `build_atm_option_bars_mtf.py`, currently read by `experiment_26_option_wick_reversal.py` + `experiment_27_premium_ict.py` + `experiment_27b_premium_small_sweep.py`. Aggregated ATM table with vendor-pre-picked atm_strike per 5m bar + CE/PE OHLC + wick-ratio columns. |
| **Symptom** | Post-ADR-011, ENH-100/103 no longer read this table for ATM PnL computation (now reads `hist_option_bars_1m` chain). Table retains active readers (the three wick-reversal experiments). If/when those experiments are retired or migrated to chain-based wick computation, this table becomes orphaned. |
| **Root cause** | Architectural narrowing — table was built for wick analysis at ATM (its original purpose); ENH-100 v3 misused it for held-strike PnL (corrected by ADR-011 v7 to use chain). Wick experiments remain its only active consumers. |
| **Workaround** | None needed currently — table serves its original purpose for wick experiments. |
| **Proper fix** | Two-step gate: (a) when wick experiments are deprecated / retired, audit whether any other consumer has emerged; (b) if no consumers, drop the table + retire `build_atm_option_bars_mtf.py` writer + remove from Topology / System Map. Until then, no action. |
| **Cost to fix** | <1 hour drop + writer retirement + doc updates, gated on wick experiment retirement decision. |
| **Blocked by** | Operator decision on wick experiment lifecycle (no current plan to retire). |
| **Owner check-in** | Revisit at wave 1.5 / wave 2 ICT primitive build planning, or when wick experiments are formally retired. |

---

### TD-S33-NEW-2 — v6 dead code in `compute_atm_pnl_and_dte` trailing for-loop + retired `_atm_anchor_at` / `_atm_future_at` helpers

| | |
|---|---|
| **Filed** | 2026-05-22 (Session 33) |
| **Severity** | S4 (anti-pattern flagged for future refactor; no behavioral impact) |
| **Component** | `C:\GammaEnginePython\build_ict_primitives.py` lines ~1002-1022 (trailing v3 for-loop after v7 head's early `return out`) + `_atm_anchor_at` (lines ~871-907) + `_atm_future_at` (lines ~910-942). Helpers retired by ADR-011 / ENH-106 but bodies left in place to minimize patch surface. |
| **Symptom** | Three blocks of dead code: (a) v3 same-strike for-loop in `compute_atm_pnl_and_dte` is unreachable (v7 head returns before reaching it); (b) `_atm_anchor_at` is no longer called by any caller (v7 `compute_atm_pnl_and_dte` and `compute_retest_atm_pnl` use `_chain_premium_at`); (c) `_atm_future_at` same. Python doesn't error on unreachable code or unreferenced functions; AST validation passes. |
| **Root cause** | Patch surface minimization — ENH-106 v7 patch script (`patch_s33_enh106_chain_heldstrike_atm_pnl_writer.py`) made 4 substitutions; replacing entire function bodies would have required ~150 more lines of `old_str` match and risk of substitution failure on whitespace edge cases. Dead code path was the safer trade-off. |
| **Workaround** | None needed — dead code is inert. |
| **Proper fix** | Next writer refactor session: (a) delete `_atm_anchor_at` + `_atm_future_at` function bodies entirely; (b) delete the trailing v3 for-loop in `compute_atm_pnl_and_dte` after the v7 `return out`. AST-validate. ~15 min work. |
| **Cost to fix** | ~15 min in next writer refactor session. |
| **Blocked by** | nothing |
| **Owner check-in** | At next `build_ict_primitives.py` edit, or proactively if file readability matters before then. |

---

### TD-S33-NEW-3 — Post-v7 falsification audit needs re-scope

| | |
|---|---|
| **Filed** | 2026-05-22 (Session 33) |
| **Severity** | S2 (audit was committed-to in ENH-100 falsification criterion; now tautological in current form; needs replacement design) |
| **Component** | ENH-100 falsification criterion specified "ATM PnL columns must agree with `hist_option_bars_1m` premium-percent change to within 5% on a 100-sample audit." Post-ADR-011 / ENH-106 v7, both audit and writer read the SAME chain table — agreement is by construction. |
| **Symptom** | The original audit criterion no longer falsifies anything because it would compare the writer's chain read against the auditor's chain read of the same rows. Both will agree by construction unless one of them has a bug — but the bug class is different (strike-rounding correctness, expiry calendar lookup correctness, cache key computation). |
| **Root cause** | Source-table change invalidates the original audit design. |
| **Workaround** | None needed for trading decisions (ADR-011 evidence is the cohort-flip, which itself IS a strong falsification — universally negative→universally positive median is not a noise artifact). |
| **Proper fix** | New audit design: (a) sample 50-100 primitives across (symbol, tf, primitive_type, direction) cells; (b) for each, independently compute ATM strike via spot lookup + manual rounding; (c) independently identify nearest weekly expiry via direct DOW + holiday rule (NOT the empirical calendar — to cross-check the calendar lookup); (d) compare to writer's stored strike + expiry. Confirms strike-rounding + expiry-calendar logic, not the trivial chain-read agreement. |
| **Cost to fix** | ~3-4 hours: audit script + 50-100 sample selection + cross-computation + verdict report. |
| **Blocked by** | nothing |
| **Owner check-in** | S34+ depending on priority vs other carry-forward; non-blocking for trading decisions. |

---

### TD-S33-NEW-4 — D-TF horizon extension — `mfe_pct` + `time_to_mfe_min` columns may already answer "what horizon makes D-TF tradeable"

| | |
|---|---|
| **Filed** | 2026-05-22 (Session 33) |
| **Severity** | S3 (analysis-only; SQL against existing columns; informs future D-TF horizon design) |
| **Component** | `ict_primitive_outcomes` columns `mfe_pct` + `time_to_mfe_min` populated by ENH-100 for all primitives. D-TF cells show positive spot WR (~67% NIFTY D BULL_FVG; ~66% SENSEX) but negative option PnL median at 30m/60m horizons. EOD horizons also negative on D-TF retest cohort. |
| **Symptom** | D-TF spot edge is real but plays out over hours not 30 minutes — theta drains during the 30m/60m hold window before the spot move materializes. Without a longer-horizon option-PnL column, the option-tradeability of D-TF cells cannot be assessed without manual chain-table reads. |
| **Root cause** | ATM_PNL_WINDOWS_MIN constant is `[5, 15, 30, 60]` — designed for M5 cells (where spot moves fast). D-TF cells have spot move time-scales of 2-4 hours. No data layer change required; the data ALREADY exists in `mfe_pct` columns (spot MFE) but not in option-PnL form. |
| **Workaround** | SQL analysis using `mfe_pct` + `time_to_mfe_min` per (symbol, tf, primitive_type, direction) — answers "what horizon would D-TF cells be tradeable at if option PnL tracks spot MFE." If MFE peaks at +90-180m on D-TF cells, that's the candidate horizon. |
| **Proper fix** | Phase 1 — SQL-only analysis: aggregate `mfe_pct` + `time_to_mfe_min` per D-TF cell; verify hypothesis that MFE peaks 90-180m post-formation on D-TF. Phase 2 — if confirmed, decide between (a) extend ATM_PNL_WINDOWS_MIN to include 120m + 180m (writer change + re-backfill), OR (b) use `forward_120m_pct` × derived option-PnL-from-spot model (analysis-only, no writer work). |
| **Cost to fix** | Phase 1: ~30 min SQL analysis. Phase 2 decision-pending. |
| **Blocked by** | nothing |
| **Owner check-in** | S34+ depending on priority. |

---

### TD-S31B-NEW-1 — Pine v6 visual MTF-breach overlay deferred (Task 5 descoped after 5-version iteration with 6 Pine v6 ergonomic walls)

| | |
|---|---|
| **Filed** | 2026-05-21 (Session 31-B) |
| **Severity** | S3 (cosmetic / operator-facing tooling not on critical path; ADR-004 Wave 1 IMPLEMENTED end-to-end on data layer; visual overlay is operator convenience for TradingView) |
| **Component** | `/mnt/user-data/outputs/MERDIAN_ICT_Primitives_canonical.pine` (v1 472 lines through v5 537 lines; final v5 descoped by operator). Visual MTF rendering of `ict_primitives` table on TradingView Pine v6 overlay. |
| **Symptom** | Five Pine v6 iterations hit six independent ergonomic walls before operator descoped: (a) zones rendering as active regardless of breach due to Pine v6 descending for-loop `for i = array.size(arr) - 1 to 0` never executing without explicit `by -1`; (b) D BULL_OBs that should be broken still active due to CE10235 "Return type of if/switch blocks not compatible" — required moving `label.new()` to standalone if block no else; (c) per-TF close fetches via `request.security(sym, "W", close[1], lookahead=lookahead_off)` double-shift bug returning close from 2 periods ago (same bug broke PDH/PDL fetches showing Levels=0 in diagnostic); (d) `var int` global mutation prohibited in functions per CE10088 "Cannot modify global variable in function" — required `var array<int> = array.from(0)` one-element-array workaround; (e) `max_boxes_count=500` hard cap silently GC's overflow boxes (1428 of 1928 zones get GC'd silently — mutations on GC'd boxes are silent no-ops, so any UI state change including breach detection fails to render); (f) PDH/PDL canonical fetch idiom requires `[high[1], low[1]] + lookahead=barmerge.lookahead_on` to work both same-TF and cross-TF. Final v5 used `showBroken=false` default to bypass GC trap; visual rendering technically works at 158 active zones but operator decision: "Its messed up. Lets drop the pine script for now and proceed with the rest." |
| **Root cause** | Pine v6 ergonomic constraints are **systemic not incidental** — six independent classes of bugs surface when attempting to mirror Python detector logic verbatim with MTF rendering on a single overlay. The `max_boxes_count=500` hard cap is architectural (Pine v6 platform constraint) — cannot be increased; requires either TF filtering for <500 zones, GC-aware rendering, or alternative display patterns (multi-pane, multiple scripts). Task 5 estimated as 0.5-1 session at S31-A planning grew to 5 iterations because the constraint set was not understood up front. |
| **Workaround** | Operators consume `ict_primitives` table directly via SQL queries against Supabase or via downstream Python tools rendering to PNG/SVG (not TradingView native overlay). Data layer (ADR-004 Wave 1 IMPLEMENTED end-to-end) is unaffected — all 19,399 primitives + 19,399 outcomes are queryable via standard Supabase REST + SQL. Pine overlay is a convenience layer for TradingView users, not a critical-path artifact. |
| **Proper fix** | Wave 1.5 or later session — architectural redesign with explicit constraint design: (a) TF filtering to keep visible zones <500 (e.g., show only D + W + last 24h of M5); (b) GC-aware rendering — accept that broken zones disappear (showBroken=false) and accept the visual asymmetry vs Python detector; (c) alternative display patterns — multi-pane Pine layout, separate Pine script per TF, or external rendering tool. **Decision required at wave 1.5 planning:** is visual MTF-breach worth Pine-v6 architectural complexity, or substitute external rendering? Cost estimate: 2-3 sessions for architectural design + implementation if Pine-v6 path; 1 session for external rendering substitute. |
| **Pine v6 engineering catalog (codified for future Pine work)** | (1) Descending for-loops require explicit `by -1` — `for i = N-1 to 0` never executes (silent zero iterations, no compile error). (2) if/else branches must return matching types per CE10235 — pull `label.new()` into standalone if block (no else, no type-compat check). (3) `var int` global mutation from inside functions prohibited per CE10088 — wrap in `var array<int> = array.from(0)`, mutate via `array.set(arr, 0, new_val)`. (4) `close[1] + lookahead_off` double-shifts — canonical previous-completed-close idiom is `close[1] + lookahead_on` OR `close + lookahead_off` (not both). (5) PDH/PDL canonical idiom: `[high[1], low[1]] + lookahead=barmerge.lookahead_on` (works both same-TF and cross-TF). (6) `max_boxes_count` hard cap 500 in Pine v6 — cannot render >500 zones; either reduce zone count via TF filtering, delete on breach (showBroken=false), or accept GC. Mutations on GC'd boxes are silent no-ops, **not errors** — this is the trap that produced 4 iterations of S31-B Pine debugging. |
| **Cost to fix** | 2-3 sessions architectural redesign if Pine-v6 path; 1 session external rendering substitute. **Blocked by:** Operator decision on visual MTF-breach value vs Pine-v6 architectural complexity. **Owner check-in:** When wave 1.5 (ADR-004 Wave 2) planning begins or earlier if operator requests visual overlay sooner. |

---

| | |
|---|---|
| **Severity** | S1 (highest-leverage S30 finding; all gate-stack analyses on OB patterns work on 0.5% non-random sample by construction; per-OB-pattern live-cohort re-validation cannot proceed until attachment is restored) |
| **Discovered** | 2026-05-17 (Session 30 — `s30_gate_audit_and_ob_attachment.py` joined `ict_zones` against `signal_snapshots` on (symbol, ts within zone validity window, spot inside [zone_low, zone_high])) |
| **Component** | `enrich_signal_with_ict()` in `build_trade_signal_local.py` (or its callers / its `detect_ict_patterns.py` callee — exact site to be localized S31). Detection in `ict_zones` is correct; defect is at attachment time. |
| **Symptom** | BULL_OB zone-touches 4,882 over 8 weeks → only 26 tagged BULL_OB in `signal_snapshots.ict_pattern` (0.5% attachment rate). BEAR_OB zone-touches 3,139 → **zero** tagged BEAR_OB in `signal_snapshots.ict_pattern` (0% attachment rate). Most zone-touches end up tagged NONE or as FVG when adjacent FVG zones exist. Cohort-level: BULL_OB live-cohort N=5 (cannot replicate Compendium 84% at this N); BEAR_OB live-cohort N=0 (cannot replicate Compendium 92%). |
| **Root cause** | Unknown precisely — S30 audit confirmed (a) `ict_zones` rows have correct `pattern_type` (BULL_OB / BEAR_OB) and correct (symbol, valid_from, valid_to, zone_high, zone_low); (b) `signal_snapshots` rows captured at zone-touch timestamps with correct spot inside zone range; (c) yet `signal_snapshots.ict_pattern` does not get populated. Defect is in the join/lookup logic at attachment time, not in zone definition or signal capture. Top suspects: (1) `enrich_signal_with_ict()` may filter OB zones by some condition that excludes most of them (e.g. status, MTF context, validity recency); (2) priority ordering may prefer adjacent FVG zones over containing OB zones; (3) `detect_ict_patterns.py` runner pre-S17-TD060 single-bar window logic may still leak into the attachment path even after the S17 fix. |
| **Workaround** | None for OB cohort analysis. Continue trading discretionary on TV-displayed OB zones (these are sourced from `ict_zones` and remain correct). MERDIAN signal stream contains correct OB zones but does not surface them in `ict_pattern` column. FVG-tagged cohort analyses remain valid (BULL_FVG N=99 / BEAR_FVG N=107 from S30 v5 cohort). |
| **Proper fix** | (1) Read `enrich_signal_with_ict()` and trace OB-attachment path; (2) reproduce zero-tagging case on a single zone-touch row from S30 audit (e.g. an explicit BULL_OB zone-touch on 2026-05-06 14:26 NIFTY); (3) localize defect; (4) patch via patched-copy AST-validated pattern (mirror of S26 / S29 / S30 deployment workflow); (5) backfill `ict_pattern` column on historical `signal_snapshots` rows (~3 month window, ~12K rows) — optional if forward-only attachment is sufficient for S31+ re-validation; (6) re-run `s30_gate_audit_and_ob_attachment.py` post-fix to verify attachment rate ≥80% (operational threshold per S30 finding). |
| **Cost to fix** | ~1 session (~2-4 hours): defect localization + patch + smoke test + verification audit. Backfill of historical rows is optional and adds ~30 min if scoped. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-17 |

---

### TD-S30-NEW-4 — DTE=0 cohort behavior unknown — live cohort N too small for verdict

| | |
|---|---|
| **Severity** | S2 (orthogonal to OB attachment defect; if BULL_OB / BEAR_OB cohort grows post-TD-S30-NEW-3 fix, DTE=0 sub-cohort may surface independent gate-direction question) |
| **Discovered** | 2026-05-17 (Session 30 — `s30_gate_audit_and_ob_attachment.py` 8-dimension audit included DTE bucket but live cohort N per DTE bucket was too small for statistically meaningful verdict on DTE=0 specifically) |
| **Component** | `build_trade_signal_local.py` DTE gate (currently rejects DTE=0 in some configurations); evaluation on live cohort blocked on N expansion |
| **Symptom** | DTE=0 live cohort sub-N is insufficient for confidence-bounded verdict; cannot determine whether the DTE=0 gate suppresses positive-EV or negative-EV setups on live cohort. Bound: 89 of 211 setups were on weekly expiry (DTE 0-2); only ~30-35 of those were DTE=0; sub-cohort WR is wide CI. |
| **Root cause** | Sub-cohort sample size; not a code defect. Needs natural cohort growth (continued live signal capture; ~1-2 months for N≥30 per pattern × DTE=0 bucket) before statistically meaningful verdict can be reached. |
| **Workaround** | Keep DTE gate at S29 settings until N≥30 per pattern × DTE=0 sub-cohort. Document this as known unknown rather than gate any DTE=0 decisions on insufficient evidence. |
| **Proper fix** | (a) Wait for natural N accumulation; (b) re-run audit when N≥30; (c) decide based on live-cohort sub-bucket WR + CI bounds (D.13.1 principle applies; D.9.3 cohort-translation discipline applies). |
| **Cost to fix** | ~1-2 months calendar (N accumulation); ~30 min audit re-run when N met. |
| **Blocked by** | TD-S30-NEW-3 partially (if OB attachment defect is in DTE-conditional logic, fixing it may surface different DTE behavior); live cohort N≥30 per pattern × DTE bucket. |
| **Owner check-in** | 2026-05-17 |

---

### TD-S30-NEW-5 — Gate stack inversion on three context dimensions (gamma / breadth / vix) — investigation queued

| | |
|---|---|
| **Severity** | S2 (live cohort empirical evidence shows three gates suppress positive-EV buckets; gate-stack inversion mechanism is unknown; may be cohort-translation hazard or may be live-cohort-specific structural finding) |
| **Discovered** | 2026-05-17 (Session 30 — `s30_gate_audit_and_ob_attachment.py` 8-dimension audit per-bucket WR + mean + median across gamma_regime, breadth_regime, vix_regime) |
| **Component** | Three gates in `build_trade_signal_local.py`: (a) LONG_GAMMA hard-block; (b) BEARISH-ALIGNED breadth modifier; (c) HIGH VIX rejection path. All three are currently active on production (not env-disabled). |
| **Symptom** | (a) gamma_regime LONG_GAMMA WR 55.1% N=158 (gated BLOCK) vs SHORT_GAMMA WR 73.3% N=15 (gated PASS) — gating direction correct but rejected bucket is huge (15× the size of the gated-PASS bucket); bulk of high-edge setups blocked. (b) breadth_regime BEARISH-ALIGNED WR 64.7% (gate suppresses on alignment claim). (c) vix_regime HIGH WR 61.2% N=49 (gate suppresses on elevated path). All three gate-direction decisions inverted on live cohort vs the cohort they were derived from (likely `hist_pattern_signals` 5m-batch). |
| **Root cause** | Unknown — multiple hypotheses: (1) Cohort-translation hazard (D.13.1) — gates were validated on 5m-batch cohort and direction-of-edge is opposite on live cohort; same as ENH-76/77/88 + tier mult finding. (2) Mechanism difference — buyer's edge on live cohort may live in different regime/condition windows than research cohort. (3) Sample size — SHORT_GAMMA N=15 is tiny; the 73.3% may be coincidence. Investigation needs each gate isolated in dedicated study. |
| **Workaround** | Gates remain active at S30 close (env-flag disablement scope limited to ENH-76/77/88 + tier mult per S30 decision). LONG_GAMMA hard-block is the highest-impact gate; if it's a false-block, the operator-visible cost is ~158 setups/8 weeks = ~20 setups/week of potential positive-EV signals suppressed. Cost to investigate < cost of leaving suppression in place. |
| **Proper fix** | Per-gate dedicated study: (a) extract live-cohort pure-ICT setups by each gate decision (PASS / BLOCK); (b) measure WR + mean + median P&L per bucket; (c) compute Wilson CI bounds + p-value vs Compendium settled baseline; (d) decide based on D.13.1 cohort-translation discipline + statistical significance. Output: 3 separate findings for ADR-009 §S30+ case studies; possible env-flag disablement of one or more gates pending live-cohort re-validation. |
| **Cost to fix** | ~1 session per gate (3 gates × 1 session = ~3 sessions sequenced). Recommend LONG_GAMMA first (highest leverage). Investigation does not deploy code changes; deployment decisions per gate follow per D.13.1. |
| **Blocked by** | nothing (orthogonal to TD-S30-NEW-3 OB attachment; uses FVG cohort which is correctly attached). |
| **Owner check-in** | 2026-05-17 |

---

### TD-S30-NEW-6 — Replay infrastructure (`replay_build_trade_signal.py`) lacks ENH-88 — header line 15 attests S17 ENH was added post-S24 build

| | |
|---|---|
| **Severity** | S3 (replay parity gap; affects what-if experiment validity on any cohort that includes BULL_FVG cluster gate decisions; ~30 min patch) |
| **Discovered** | 2026-05-17 (Session 30 — operator confirmed via inspection of `C:\GammaEnginePython\replay\replay_build_trade_signal.py` header line 15 which lists ENH versions baked in at S24 build: ENH-53/55/76/77/78; ENH-88 was shipped S17 post-replay-build at S24, never back-ported to replay) |
| **Component** | `replay/replay_build_trade_signal.py` (Local — replay parity file for `build_trade_signal_local.py` per ADR-008 zero-touch constraint) |
| **Symptom** | Replay-time signal generation lacks ENH-88 BULL_FVG cluster gate logic. Any what-if experiment that hinges on whether ENH-88 fires (gate PASS / BLOCK) will produce results that don't match the live decision tree as it existed during the replay window. Specifically: live signal_snapshots rows captured S26+ may have `cautions` array containing "ENH-88: BULL_FVG standalone blocked" entries, but replay re-runs of the same boundary would NOT produce that caution because the replay file's gate logic predates ENH-88. |
| **Root cause** | Standard architectural drift between live and replay — when ENH-88 was shipped S17, the canonical workflow per ADR-008 §replay-vs-live parity required parallel patch to replay file; this back-port was not executed S17 nor at any subsequent session. Replay file is at S24-build state; live file is at S30-build state (now includes 4 env-flag gates + tier mult force from S30 + ENH-88 from S17). |
| **Workaround** | Avoid what-if experiments that intersect ENH-88 gate decisions until parity restored. Compendium settled cohort metrics on BULL_FVG remain valid (Compendium predates ENH-88 in scope). |
| **Proper fix** | Apply ENH-88 patch to `replay_build_trade_signal.py` mirroring the live ship S17 (commit at S26 deploy was `8407169` per CURRENT.md S26 block): add `ENH88_LOOKBACK_MIN: int = 90` + `_has_recent_bull_ob()` helper + ENH-88 gate block before `return out, flags`; sync three sites action + trade_allowed + out{} as in live; set `out["raw"]["enh88_decision"]`. AST-validate post-patch. Smoke test via single-boundary replay invocation matching a live signal_snapshots row known to have "ENH-88: BULL_FVG standalone blocked" caution; verify replay produces same caution. |
| **Cost to fix** | ~30 min (single-file patch + smoke test). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-17 |

---

### TD-S30-NEW-7 — Hold-time bucket study scope — formal N≥100 per exit-bucket measurement on live cohort

| | |
|---|---|
| **Severity** | S3 (S30 found hold-time persistence inversely correlated with edge on live cohort; T+30m Compendium-settled exit timing may be past asymmetric-winners-tail exhaustion; warrants formal study with proper N) |
| **Discovered** | 2026-05-17 (Session 30 — `s30_path1_live_cohort_pnl_v4.py` persistence × P&L analysis on live cohort) |
| **Component** | Exit timing decision (currently T+30m Compendium-settled). Affects: realized cohort P&L distribution; hold-time discipline in operator's hybrid TV-MERDIAN + discretionary workflow; future automation choice of exit logic. |
| **Symptom** | S30 v4 measured 4 exit buckets on live cohort: flipped-10-20m bucket WR 64.3% mean +4.00% (BEST); flipped-20-30m WR 56.5% mean +2.20%; held-full-30m exit WR 50% mean -1.80% (WORST); persistence-flipped-and-recovered WR mid-range. Direction: asymmetric winners are time-localized to first 10-20 min after signal; holding past 20m captures progressively more mean-reversion than continuation. Compendium settled WR (BEAR_OB 92% / BULL_OB 84% / BULL_FVG 50%) is measured at T+30m; if live-cohort optimal exit is T+10-20m, Compendium WR understates actual hold-the-right-time WR by an unknown but non-zero margin. Magnitude finding S30 cohort N=211 (total) ÷ 4 buckets = ~50/bucket — sufficient for direction-of-edge finding, insufficient for formal cohort verdict. |
| **Root cause** | Multiple hypotheses: (1) ICT signals are time-localized to entry mechanic (zone-touch + reversal) and don't have continuation thesis beyond 20 min; (2) cohort-wide mean-reversion regime; (3) selection bias in flipped vs held-full buckets. Investigation needed to disentangle. |
| **Workaround** | Operator discretionary trading already exits faster than T+30m on intuition — S30 finding empirically validates intuition. No production gate is on hold-time so no immediate code action needed. |
| **Proper fix** | Formal hold-time bucket study: (a) live cohort N≥100 per exit-bucket measurement; (b) compute WR + mean + median P&L per bucket × per ICT pattern type (BULL_FVG / BEAR_FVG / BULL_OB / BEAR_OB after TD-S30-NEW-3 fix); (c) compute Wilson CI bounds; (d) decide based on directional consistency across patterns + statistical significance whether to file ADR-010+ codifying live-cohort optimal exit window. ADR candidate if T+30m settled timing is empirically superseded. |
| **Cost to fix** | ~1 session for the study (data already accumulated). Ongoing analysis as cohort grows. |
| **Blocked by** | TD-S30-NEW-3 partially (per-pattern bucket counts need OB attachment to be useful for OB patterns; FVG patterns can proceed regardless). |
| **Owner check-in** | 2026-05-17 |

---

### TD-NEW-A — `market_ticks` retention runaway → 62 GB bloat → INSERT timeouts cascading into breadth outage (RESOLVED Session 29 in-flight)

**RESOLVED Session 29 (2026-05-14) in-flight as part of Incident §1 firefighting.** Full closure block is in the **Resolved (audit trail)** section below. Original pg_cron `delete-old-market-ticks` (jobid 45, `30 14 * * 1-5`, 2-day horizon) had been failing every weekday for 14+ consecutive runs since at least 2026-04-30 with `ERROR: canceling statement due to statement timeout` (Postgres 57014). Failed deletes accumulated `market_ticks` to 62 GB (22 GB heap + 40 GB indexes). At that size, `ws_feed_zerodha.py` bulk INSERT (2282 instruments × tick rate) began exceeding statement_timeout, producing 6+ hour breadth cascade on 2026-05-14. Fix: `TRUNCATE public.market_ticks` (62 GB → 856 kB in <1s, DDL primitive); `cron.unschedule(45)`; new `cron.schedule('prune-market-ticks', '*/30 * * * 1-5', $$DELETE FROM public.market_ticks WHERE ts < now() - interval '1 hour'$$)` → jobid 46. Design rationale: cadence 1/day → 1/30min, horizon 2days → 1hour decouples worst-case DELETE workload from cron cadence. Codified as CLAUDE.md B25 (TRUNCATE vs DELETE) + Topology §6.10 (token edits don't restart consumers; this TD's Root Cause A partner) + OI-12 RE-RESOLVED block in `MERDIAN_OpenItems_Register_v7.md`. See also `CASE-2026-05-14-breadth-cascade-token-and-bloat.md`.

---

### TD-NEW-B — `pg_cron` job failures invisible by default — needs polling daemon or session-start gate

| | |
|---|---|
| **Severity** | S1 (root cause of the 14+ day silent failure that escalated into the 2026-05-14 breadth cascade; without telemetry the next pg_cron failure class will also escalate silently before operator-visible symptoms surface) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — surfaced during TD-NEW-A diagnosis when `cron.job_run_details` revealed 10 consecutive `delete-old-market-ticks` failures going back to at least 2026-04-30) |
| **Component** | `cron.job_run_details` Supabase system table records every cron run with `status` and `return_message`, but no MERDIAN telemetry polls it. New cron jobs (jobid 46 `prune-market-ticks` from TD-NEW-A fix) introduce the same blind spot until polling is implemented. |
| **Symptom** | Pg_cron job fails every weekday for weeks; downstream consumer eventually breaks; root cause invisible until cascade. Example: `delete-old-market-ticks` failed 14+ weekdays before 2026-05-14 breadth outage. |
| **Root cause** | No telemetry layer for `cron.job_run_details`. `merdian_pipeline_alert_daemon.py` (Local) polls Supabase tables but does not query the `cron` schema. Telegram alert daemon doesn't subscribe to cron-failure events. |
| **Workaround** | Manual session-start checklist SQL (per CLAUDE.md B26 + Topology §6.11): `SELECT jobname, status, return_message, start_time FROM cron.job_run_details d JOIN cron.job j USING (jobid) WHERE start_time > now() - interval '7 days' AND status != 'succeeded' ORDER BY start_time DESC;` Empty result = healthy. Any rows = investigate. Operator session-start ritual addition. |
| **Proper fix** | Either (a) extension of `merdian_pipeline_alert_daemon.py` to query `cron.job_run_details` every N minutes and Telegram-alert on any `status != 'succeeded'` row in last 24h, or (b) dashboard widget on `merdian_live_dashboard.py` surfacing recent cron failures. Approach (a) closes the failure class more aggressively; (b) requires operator to look at dashboard. Recommend (a). |
| **Cost to fix** | 1-2 sessions (Telegram daemon extension or dashboard widget; needs decision on alert deduplication policy). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-C — `ws_feed_zerodha.py` silent on Supabase 500 / token errors (extends TD-NEW-9)

| | |
|---|---|
| **Severity** | S2 (extends TD-NEW-9 — when WS feed reconnect-loops because Supabase rejects writes with 500 statement_timeout, the script silently retries indefinitely; no Telegram alert; operator has to grep logs to discover. Today on 2026-05-14 6+ hours of silent retries before manual log tail revealed `Supabase write error 500: ... statement timeout`) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — `tail -f logs/ws_feed.log` revealed silent reconnect loop after restart with new token; the error class was distinct from TD-NEW-9's silent-on-success class but shared the same script and same "operator must manually grep logs" workaround) |
| **Component** | `ws_feed_zerodha.py` running on MERDIAN AWS — error logging is `print()` to log file only; no Telegram alert path; no escalation when retry count exceeds threshold |
| **Symptom** | Feeder receives ticks, attempts INSERT to `market_ticks`, Supabase returns 500 with statement_timeout, feeder retries indefinitely. No alert. Logs show repeated `Supabase write error 500: {...}` lines. Operator only finds out via downstream breadth-cascade symptoms hours later. |
| **Root cause** | No Telegram alert wiring in `ws_feed_zerodha.py`. The `import telegram_utils; telegram_utils.send_alert(...)` pattern used by other MERDIAN scripts is not present. |
| **Workaround** | Operator session-start session-start log tail: `tail -n 50 logs/ws_feed.log` looking for `error` / `500` / `timeout` substrings. |
| **Proper fix** | Bundle with TD-NEW-9 (silent-on-success heartbeat). Same touch point — add: (a) every N=1000 ticks log `[HEARTBEAT] N ticks processed, last_ts=X, latency=Yms`; (b) on any non-200 Supabase response, log error + send Telegram alert (dedupe by 5-min window); (c) on N=3 consecutive Supabase errors in 60s, escalate Telegram alert priority. |
| **Cost to fix** | <1 session if merged with TD-NEW-9 (~45 min). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-D — `ws_feed_zerodha.py` log timestamps `[HH:MM:SS IST]` are actually UTC (cosmetic)

| | |
|---|---|
| **Severity** | S2 (cosmetic — logs are mislabeled and 5h30m off but otherwise functional; operator triage time increases when reading timestamps in logs that are not what they claim) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — verified via two adjacent log entries: `[04:27:06 IST]` actually issued at 09:57 IST; `[12:39:43 IST]` actually issued at 18:09 IST; 5h30m apart in real time despite both labeled IST) |
| **Component** | `ws_feed_zerodha.py` log prefix construction — uses `datetime.now()` which returns naive local-system-time UTC on AWS Ubuntu, then formats with `[%H:%M:%S IST]` literal string |
| **Symptom** | Log lines display incorrect `IST` timestamp by 5h30m. Operator manually adds 5h30m every read. |
| **Root cause** | `datetime.now()` on AWS Ubuntu returns UTC (no IST timezone). Format string hardcodes `IST` literal. |
| **Workaround** | Operator mental conversion. |
| **Proper fix** | Single-line change: `datetime.now()` → `datetime.now(ZoneInfo('Asia/Kolkata'))`. Bundle with TD-NEW-9 + TD-NEW-C in next ws_feed touch. |
| **Cost to fix** | 15 minutes at next ws_feed_zerodha.py touch. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-E — Topology §7.2 Task Scheduler inventory stale (17→19 entries) (CLOSED Session 29 in doc-close rewrite)

**CLOSED Session 29 (2026-05-14) as documentation gap.** Topology §7.2 was rewritten in S29 close commit: 17-task table → 19-task table reflecting S29 audit final state. Two newly-discovered tasks (`MERDIAN_Dhan_Token_Refresh`, `MERDIAN_Intraday_Session_Start`) added with action-untouched/settings-hardened state. Filed-and-closed pattern (same shape as TD-NEW-11 S28).

---

### TD-NEW-F — `runbook_update_kite_flow.md` missing Step 2d (consumer-restart) (RESOLVED Session 29 via runbook edits)

**RESOLVED Session 29 (2026-05-14) via 5 verbatim markdown edits applied at S29 close.** Header `Last verified` row updated to 2026-05-14 + Step 2d inserted between Step 2c and Step 3 + 2 new failure-mode rows + 2026-05-14 architectural-gap addition + change-history row. Closes the runbook gap that produced the 2026-05-14 breadth cascade incident (operator ran token-refresh sequence twice with correct `.env` end-state but did not restart the consumer process holding the prior token in memory). Codified as CLAUDE.md B24 (`.env` edits do not propagate to running processes) + Topology §6.10 new gotcha.

---

### TD-NEW-H — `backfill_volatility_snapshots.py` NULL `expiry_date` schema violation produces 7 daily pre-market CRASHes
> **SUPERSEDED Session 55 (2026-06-17).** Symptom (7 daily pre-market crashes) no longer exists: backfill_volatility_snapshots.py de-scheduled in the AWS migration (not in cron, no log or script_execution_log activity), and the script was rewritten to target volatility_snapshots with upsert(on_conflict=symbol,ts) and a _smallest_expiry resolver. It is a manual ENH-97 backfill tool, not a daily job. Re-verify only if reinstated.

| | |
|---|---|
| **Severity** | S2 (recurring CRASH count contributes to false-alarm noise; backfill writes are partially-blocked rather than fully-blocked, so research data is partially populated; pollutes script_execution_log audit) |
| **Discovered** | 2026-05-14 (Session 29 firefighting — surfaced during script_execution_log attribution analysis showing 7 daily CRASHes from `backfill_volatility_snapshots.py`) |
| **Component** | `backfill_volatility_snapshots.py` — pre-market backfill for `volatility_snapshots`; the script attempts INSERT with NULL `expiry_date` for some rows |
| **Symptom** | 7 CRASH exit_reason rows per day in `script_execution_log` from `backfill_volatility_snapshots.py`. Postgres rejects INSERT because `volatility_snapshots.expiry_date NOT NULL` constraint. Rows that should write don't write; backfill is partially incomplete. |
| **Root cause** | Unknown — needs source read of `backfill_volatility_snapshots.py`. Likely: query returns row with no expiry_date populated (e.g. weekend cycle or pre-market window before option chain populated). |
| **Workaround** | None active; partial backfill data is acceptable for research-only context. |
| **Proper fix** | Read source; identify whether NULL `expiry_date` rows should (a) be filtered out before INSERT (likely), (b) get a sentinel expiry_date value, or (c) trigger schema change to allow NULL. Then patch. |
| **Cost to fix** | <1 session (read script + 1-3 line patch + smoke test). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-14 |

---

### TD-NEW-I — Daily audit thresholds `spot_bars_per_symbol_min` + `market_spot_snapshots_per_symbol` too tight (RESOLVED Session 29)

**RESOLVED Session 29 (2026-05-14).** Full closure block is in the **Resolved (audit trail)** section below. `merdian_daily_audit.py` thresholds `spot_bars_per_symbol_min: 370` + `market_spot_snapshots_per_symbol: 370` flagged FAIL on days with 98% coverage (367/375). 2026-05-14 audit returned 4-fail FAIL OVERALL spuriously when actual coverage was 367/375 NIFTY and 366/375 SENSEX. Patched both thresholds to 365. Patch via `patch_s29_td_new_i_j_v2.py` (v1 abandoned due to regex undercatch). Backup `merdian_daily_audit_PRE_S29_TD_NEW_I_J_V2.py`. Codification: audit thresholds should match actual coverage realities (375 bars/day market, allow for 2-3 known gap minutes from operational timing windows). See `CASE-2026-05-14-spot-gap-backfill.md`.

---

### TD-NEW-J — `capture_spot_1m_v2.py` emits `'OUTSIDE_MARKET_HOURS'` exit_reason (= TD-083; RESOLVED Session 29)

**RESOLVED Session 29 (2026-05-14) — same root cause as TD-083, unified closure.** Full closure block is in the **Resolved (audit trail)** section below. `capture_spot_1m_v2.py` emitted exit_reason `'OUTSIDE_MARKET_HOURS'` against `chk_exit_reason_valid` closed-set constraint causing daily false-alarm CRASH rows. Patched call-site L346 + docstring L36 to `'OFF_HOURS'` via `patch_s29_td_new_i_j_v2.py`. Backup `capture_spot_1m_v2_PRE_S29_TD_NEW_I_J_V2.py`. Codification (B23 evolution): when code-side string literal renamed, prose-side references must update in lockstep OR rewrite prose to preserve grep-discoverability of old name. Patch v2 used `OFF_HOURS (was OUTSIDE_MARKET_HOURS pre-TD-NEW-J 2026-05-14)` in docstring to satisfy both.

---

### TD-061 — Task Scheduler entry points spawn visible console windows during pre-market and post-market hours (RESOLVED Session 29)

**RESOLVED Session 29 (2026-05-14).** Full closure block is in the **Resolved (audit trail)** section below. **NOTE: This TD was footer-claimed-RESOLVED at S18; body remained in Active section; S23 audit confirmed only 4/15 migrated; S29 audit found 19 tasks (up from 17 at S23) with only 4/19 on pythonw at S29-start. The earlier "RESOLVED" claim was a body-state-vs-footer-claim divergence — fixed at S29 close per Doc Protocol v4 candidate Rule N.** S29 firefighting completed the migration: `migrate_to_pythonw.ps1` (v2 — v1 abandoned due to regex shell-redirection capture bug); 13/19 tasks now on `pythonw.exe` directly; 18/19 with `Hidden=$true + MultipleInstances=IgnoreNew` settings; 5 residual flashes are low-frequency sources (Intraday_Supervisor_Start, Watchdog, Intraday_Session_Start, Dhan_Token_Refresh, Market_Tape_1M-broken). New `run_ict_htf_zones_daily.py` Python orchestrator replaces 3-step `.bat` for ICT_HTF_Zones_0845 task. Backups under `backups\scheduler\20260514_184211\` + `backups\scheduler\20260514_190443\`. See Topology §7.2 final-state table (S29 update) + `CASE-2026-05-14-breadth-cascade-token-and-bloat.md` (companion incident).

---

### TD-NEW-13 — Python 3.10 `fromisoformat()` rejects non-3/6-digit microsecond fractions (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. TD-NEW-4 `_dte_from_ts` helper passed Local Python 3.12 smoke on 5 sample rows but failed 60/587 backfill cycles on AWS Python 3.10 with `ValueError: Invalid isoformat string`. Supabase serializes PostgreSQL timestamps with variable microsecond precision (2-7 digits common); Python 3.10 accepts only exactly 3 or 6 digits; Python 3.12 is permissive. Fix: regex normalize microseconds to exactly 6 digits via pad/truncate before `fromisoformat()` in `_dte_from_ts` helper. Commit `447634c`. Retry on 60 failed run_ids: 60/60 success post-patch. Codified as Assumption Register §D.11.3 + Deployment Topology §6.9 + CLAUDE.md B22 (cross-Python-version stdlib semantics).

---

### TD-NEW-12 — AWS shadow runner writes to production `gamma_metrics` instead of `gamma_metrics_shadow` (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. Shadow architecture not implemented since MERDIAN AWS shadow runner deployment (~2026-04-29). `compute_gamma_metrics_local.py` on MERDIAN AWS wrote to production `gamma_metrics` table for 13 days; race-condition double-writes against the same `(symbol, ts)` row that Local was upserting (UPSERT semantics determined which value persisted per cycle). `gamma_metrics_shadow` table existed in Supabase but had 0 rows. Architectural invariant per Deployment Topology §6.5 silently violated. Fix: `--shadow` flag plumbing (TARGET_TABLE constant routes read + write + telemetry) + AWS wrapper line 479 passes flag + schema reconciliation (7 missing cols + UNIQUE constraint). Commits `72622a9` + `de23467`. Codified as Assumption Register §D.11.1 + Deployment Topology §6.5 update + §6.8 new gotcha + CLAUDE.md S28 settled bullet.

---

### TD-NEW-11 — `merdian_order_placer.py` not catalogued in Deployment Topology §3 AWS-only scripts (RESOLVED Session 28 documentation gap)

**RESOLVED Session 28 (2026-05-13) as documentation gap.** Full closure in S28 doc-close rewrite of `MERDIAN_Deployment_Topology.md` — §3 row added for Phase 4B Order Placer (HTTP server port 8767, Dhan-IP-whitelisted Elastic IP `13.63.27.85`, `@reboot` cron, deployed 2026-04-29). §7.1 @reboot cron entry added. §8.2 log path `logs/order_placer.log` added. Filed as S3 documentation gap surfaced when investigating TD-NEW-10 (which was filed-in-error as un-audited process; investigation showed it was intentional Phase 4B service, just absent from docs). No code change needed.

---

### TD-NEW-10 — `merdian_order_placer.py` running deployed but un-audited (CLOSED Session 28 filed-in-error)

**CLOSED Session 28 (2026-05-13) as filed-in-error.** Full closure block is in the **Resolved (audit trail)** section below. Process discovered running on MERDIAN AWS during S28 investigation; PID 579 confirmed; filed as "un-audited process". Investigation surfaced: intentional Phase 4B Order Placer (HTTP server port 8767, Dhan-IP-whitelisted Elastic IP, @reboot cron, deployed 2026-04-29 — predates current session's full Topology audit). Not a defect. Real issue was documentation gap → TD-NEW-11 filed and closed same session by adding row to Topology §3 + §7.1 + §8.2. CLAUDE.md S28 settled-decision bullet codifies the canonical "audited live, confirmed intentional" closure pattern.

---

### TD-NEW-9 — `ws_feed_zerodha.py` silent on success; no INFO heartbeat for nominal operation

| | |
|---|---|
| **Severity** | S2 (operational hygiene — when WS feed appears stuck, operator cannot distinguish "stuck/dead" from "running fine but silent on success" without grep'ing for new ticks landing in `market_ticks` table; cost is investigation time, not signal quality). |
| **Discovered** | 2026-05-13 (Session 28 — S28 drift period included a ~5 min WS feed outage triage where operator suspected stuck process; root cause was Zerodha-side connectivity which resolved via reconnect after 60s cycles, but script-side logs were silent making the diagnosis slower than necessary). |
| **Component** | `ws_feed_zerodha.py` running on MERDIAN AWS — currently logs only on errors, reconnects, and structural events. No periodic heartbeat or per-N-tick INFO line. |
| **Symptom** | `tail -f logs/ws_feed.log` shows no output during nominal operation. Operator cannot confirm liveness without cross-checking `market_ticks` table writes (DB-side proxy). When MERDIAN_WS_Stop pkill fires at 15:32 IST, log just stops mid-silence; no "shutting down" or "tick count summary" line. |
| **Root cause** | Original `ws_feed_zerodha.py` design optimized for low log volume; no heartbeat-style instrumentation. Standard pattern across other long-running MERDIAN scripts is per-cycle INFO line on `script_execution_log` table, but WS feed runs continuously not in cycles. |
| **Workaround** | Cross-check `SELECT MAX(ts) FROM market_ticks WHERE symbol='NIFTY'` to confirm liveness. Costs ~15-30 seconds during a triage. |
| **Proper fix** | Add per-N-tick INFO heartbeat (e.g., every 1000 ticks log `[HEARTBEAT] N ticks processed, last tick TIMESTAMP, latency Xms`). Plus shutdown handler: on SIGTERM/SIGINT log final summary before exit. Plus periodic (every 60s) liveness line even if 0 ticks processed in window — distinguishes "alive but idle" from "dead". |
| **Cost to fix** | <1 session (~30-45 min — ws_feed_zerodha.py is the touch point; tests local before AWS git pull). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-13 |

---

### TD-NEW-8 — MERDIAN_WS_Stop cron `pkill -f` ignores SIGTERM; 9 zombies accumulate (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. MERDIAN AWS crontab entry `02 10 * * 1-5 pkill -f ws_feed_zerodha.py` (15:32 IST WS stop) was sending SIGTERM (default `kill -15`). `ws_feed_zerodha.py` ignored SIGTERM (no signal handler installed); accumulated 9 zombies over Apr 30 → May 11 (~1.4GB RAM impact). Fix: `pkill -9 -f` (SIGKILL) — kernel kills process unconditionally. Config-only change. Topology §7.1 updated. CLAUDE.md S28 settled-decision bullet.

---

### TD-NEW-7 — MALPHA → MERDIAN AWS Zerodha token propagation is manual `sed`; should be Supabase `system_config` automation (Dhan-flow mirror)

| | |
|---|---|
| **Severity** | S1 (production-impacting — two outages in two months (2026-04-22 + 2026-05-12) directly traced to this manual step; live signal pipeline can't function on AWS without Kite-token-dependent scripts working; Local has its own Kite auth path so production decisions continue, but AWS shadow + AWS-side per-strike OHLC backfill paths break). |
| **Discovered** | 2026-05-13 (Session 28 — surfaced via MALPHA-as-third-environment Topology gap analysis; two operational outages had been investigated separately but never connected to the architectural cause; S28 doc-close work made the dependency visible). |
| **Component** | MALPHA AWS (Zerodha Kite token gateway, `~/meridian-alpha`, `ubuntu@13.51.242.119`) writes new Zerodha access token to local `.env`; operator manually runs `sed` on MERDIAN AWS `/home/ssm-user/meridian-engine/.env` to propagate. No automation. |
| **Symptom** | When Zerodha access token expires (typically once per market day per Kite Connect TOS), MALPHA refreshes via headless-interactive browser-TOTP flow on its own EC2. The new token is in MALPHA's `.env` only. Until operator manually runs the `sed` step on MERDIAN AWS, MERDIAN-AWS-side scripts that import `kiteconnect` (`ingest_option_chain_local.py` AWS path for shadow chain; any Zerodha-side per-strike OHLC backfill; `check_kite_auth.py`) operate against stale token and fail. Two outages observed: 2026-04-22 morning, 2026-05-12 morning. Both presented as AWS-side option-chain ingest failure; investigation each time traced to stale Zerodha token. |
| **Root cause** | Architectural — MALPHA writes only locally, no Supabase write. The original MALPHA design treated MALPHA as a self-contained Kite gateway; the dependency from MERDIAN AWS for Kite-side calls emerged later (around the time `ingest_option_chain_local.py` AWS path was extended to call Kite REST). The manual `sed` step was a temporary workaround that became permanent. |
| **Workaround** | Operator manually runs the `sed` step on MERDIAN AWS after MALPHA refresh. ~3 minutes per occurrence. Forgotten or delayed → outage. |
| **Proper fix** | Mirror the Dhan token flow exactly: (1) MALPHA writes refreshed Zerodha access token to Supabase `system_config` table (key = `ZERODHA_ACCESS_TOKEN`, write_ts, host=`malpha`). (2) MERDIAN AWS `pull_token_from_supabase.py` (currently Dhan-only) extended to also pull Zerodha key; writes to `/home/ssm-user/meridian-engine/.env`. (3) AWS cron `MERDIAN_Token_Refresh_Zerodha` at e.g. 03:10 UTC = 08:40 IST (5 min after Dhan token pull to allow MALPHA replication). Closes the failure class. Runbook update: `docs/runbooks/runbook_update_kite_flow.md` updated to remove manual sed step and document the automation. |
| **Cost to fix** | ~60-90 min spans MALPHA + MERDIAN AWS + Supabase. Per the Dhan-flow precedent (which works reliably), the pattern is known. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-13 |

---

### TD-NEW-6 — Local `MERDIAN_WS_Feed_0900` task is a dead-stub firing daily; pollutes logs (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. Local Task Scheduler `MERDIAN_WS_Feed_0900` (~09:00 IST Mon-Fri) was wired to `cmd.exe /c run_ws_feed_zerodha.bat` (wraps `ws_feed_zerodha.py`). Actual production WS feed runs on MERDIAN AWS only (browser-TOTP auth flow can't run headless on AWS unless gateway-routed, but the Local invocation was a vestigial design that never produced useful ticks — `market_ticks` writes came from AWS or were absent). Daily firings polluted `task_output.log` + `script_execution_log` with no-op runs that occasionally crashed mid-session interrupting operator workflow. Fix: PowerShell `Disable-ScheduledTask -TaskName MERDIAN_WS_Feed_0900` (durable). Topology §2 + §7.2 updated. CLAUDE.md S28 settled-decision bullet.

---

### TD-NEW-5 — Pine overlay regeneration not chained off `MERDIAN_ICT_HTF_Zones_0845`; operator must run manually (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. `run_ict_htf_zones_daily.bat` (wraps `build_ict_htf_zones.py --timeframe both`) was producing fresh `ict_htf_zones` rows at 08:45 IST but `generate_pine_overlay.py` (which produces the TradingView Pine v6 overlay file from current zone state) had to be run manually each session. Operator missed runs occasionally → stale Pine overlay rendered against current price action with old zones. Fix: bat file extended with Call 3 (`python generate_pine_overlay.py --output dashboards\ict_overlay.pine`) chained after the two existing zone-build calls. Config-only change. Topology §A.2 + §7.2 updated. CLAUDE.md S28 settled-decision bullet.

---

### TD-NEW-4 — `compute_gamma_metrics_local.py` `dte` payload derived from `date.today()` not `result.ts.date()` (RESOLVED Session 28)

**RESOLVED Session 28 (2026-05-13).** Full closure block is in the **Resolved (audit trail)** section below. `upsert_gamma_metrics()` computed `dte` as `(date.fromisoformat(result.expiry_date) - date.today()).days`. Live writes were correct because `result.ts ≈ now` (within seconds). Backfill writes were systematically wrong — running compute on 2026-05-12 NIFTY data on 2026-05-13 produced `dte = -1` instead of `dte = 0` (the run was on its expiry day). Latent bug, surfaced during TD-NEW-12 smoke test. Fix: `_dte_from_ts(result)` helper at module level derives as-of date from `result.ts` in IST; payload line uses helper. Bundled in commit `72622a9`. Cross-validated 2026-05-12 NIFTY run_id `e2dd1a09-...`: post-patch dte=0 (correct), pre-patch dte=-1 (wrong). Codified as Assumption Register §D.11.2 + CLAUDE.md S28 settled bullet.

---

### TD-099 — URL-encoding bug pattern audit (RESOLVED Session 26 as filed-in-error)

**RESOLVED Session 26 (2026-05-10) as filed-in-error.** Full closure block is in the **Resolved (audit trail)** section below. Operator picked TD-099 at S26 opening for sweep work; URL-spy verification (intercepted `requests.get` calls) showed all 4 scripts in scope emit clean single-`?` URLs with proper encoding — match was a false-positive grep against dashboard-style code patterns. ~3 hours of unnecessary patching avoided. Filing rule established: "same anti-pattern in N other scripts" claims require URL-spy or runtime trace verification before priority assignment, not just grep matches. CLAUDE.md B19 codifies the broader OI-18 propagation lesson (TD-099 grep was shape-specific to URL construction; the real propagation site was TD-101 inside a writer-side helper that grep couldn't reach).

---

### TD-101 — `build_momentum_features_local.py::get_session_open_spot()` unbounded query NULLs `ret_session` (RESOLVED Session 26 same-session)

**RESOLVED Session 26 (2026-05-10) same-session as discovery.** Full closure block is in the **Resolved (audit trail)** section below. Patch script `patch_s26_td101_ret_session.py` replaces `get_session_open_spot()` body with bounded query — `today_start_utc_iso` derived from `current_ts.astimezone(timezone.utc)` date; `gte("ts", today_start_utc_iso)` filter; limit=20; defense-in-depth date filter inside loop preserved; threshold 03:35 UTC preserved per ENH-01/V18G regression history (catches both 09:05 IST Local PreOpen now-disabled and 09:08 IST AWS PreOpen current anchor). Smoke test PASS Friday 2026-05-08 close prices: NIFTY 24,161.3, SENSEX 77,582.08; Sunday both None (clean, no errors). Backup `build_momentum_features_local_PRE_S26_TD101.py` preserved. Commit `3cb84e2`. **Same OI-18 anti-pattern class as S25 TD-097 dashboard fix** — propagation never reached this writer-side helper because S25 TD-099 grep audit was shape-specific to URL construction. Live impact: ENH-55 momentum opposition gate (which gates on `ret_session is not None`) was silent no-op for 24 trading days 2026-04-17 → 2026-05-10, ~5,000 signals. Surfaced retrospective evidence (N=44 OPPOSED at 79.5% WR vs Exp 20's claimed 38.3%) directionally falsifying Exp 20 hypothesis, prompting same-session ENH-55 disablement by env flag (commit `5b94c78`, default OFF, reversible via `MERDIAN_ENH55_ENABLED=1`). Filed as Assumption Register §D.9 (5 rows D.9.1–D.9.5 + 4 open follow-ups + ADR-009 first-case-study material). CLAUDE.md B19 codifies the broader OI-18 propagation lesson.

---

### TD-098 — Single-boundary replay momentum_regime classification differs from full-day orchestrator

| | |
|---|---|
| **Severity** | S4 (replay-side artifact; affects what-if experiment interpretation when single boundaries are spot-checked rather than running the full orchestrator). |
| **Discovered** | 2026-05-10 (Session 25 — observed during S25 ret_session anchor migration validation; replay invoked at single boundaries produced different `momentum_regime` than the same boundary inside a full-day orchestrator run). |
| **Component** | `replay/replay_build_momentum_features.py` — when invoked standalone at a single `--replay-ts`, downstream momentum_regime classification can differ from the full-day orchestrator's value at the same boundary. |
| **Symptom** | Single-boundary replay reports e.g. `momentum_regime='BULLISH_TRENDING'` at 11:05 IST. Full-day orchestrator running 09:15→15:30 reports `momentum_regime='BULLISH_PULLBACK'` at the same 11:05 boundary. Discrepancy traces to upstream state (prior `session_vwap` series, prior momentum_snapshots row for ret_session_anchor) being computed differently when replay starts mid-session vs. running through every boundary in sequence. |
| **Root cause** | Likely: `momentum_snapshots_replay` filters with `ts <= replay_ts ORDER BY ts DESC LIMIT 1` for "prior cycle" lookup; in single-boundary mode this returns whatever's already in the table from a previous run (possibly nothing, possibly stale) instead of an in-sequence prior boundary's row. Confirmed pattern matches what ADR-008 `'What what-if experiment means'` framework already noted: "Per-boundary script ordering contract is load-bearing." Single-boundary spot-checks under-detect for the same reason ICT pattern detection does — patterns whose anchor bar is outside 30-bar lookback at sparse invocations. Same logic applies to momentum sequence dependencies. |
| **Workaround** | Always run full-day orchestrator for replay-vs-replay comparison. Single-boundary invocation acceptable only for plumbing smoke-tests, not for momentum-regime classification analysis. Document in ADR-008 §'Single-boundary caveat' (already partially noted; expand in S26 or whenever ADR-008 is next touched). |
| **Proper fix** | Two options: (a) require single-boundary replay invocation to fail-fast if no prior `momentum_snapshots_replay` row exists for the same `replay_date` and `run_id` (defensive guard); (b) document the constraint and rely on operator discipline. Option (a) is safer; ~1 session of work. |
| **Cost to fix** | ~1 session for option (a); zero code for option (b). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-10 |

---

### TD-097 — Dashboard pre-open status URL-encoding bug (RESOLVED Session 25)

**RESOLVED Session 25 (2026-05-10).** Full closure block is in the **Resolved (audit trail)** section below. Patch script `patch_s25_dashboard_preopen_gap.py` deployed; 5 substitutions applied to `merdian_live_dashboard.py`; ENH-96 (gap display widget) shipped same-session as side-effect of the investigation.

---

### TD-096 — Replay reconstructor skips boundary 15:30 because last `hist_spot_bars_1m` bar is at 15:29 IST

| | |
|---|---|
| **Severity** | S4 (cosmetic — replay produces 75/76 boundaries instead of 76/76; downstream effect is one missing replay row at the session-close boundary). |
| **Discovered** | 2026-05-09 (Session 24 — observed during ENH-93 Phase 4b full-day orchestrator run on 2026-05-07). |
| **Component** | `C:\GammaEnginePython\replay\replay_chain_reconstructor.py` `_reconstruct_symbol`; the `direct datetime lookup` in `bars_by_ts.get(boundary_utc, [])` returns empty for the 15:30 IST boundary because no `hist_option_bars_1m` row has bar_ts=15:30 IST (last hist bar is 15:29 IST). Reconstructor reports `boundaries: emitted=75 skipped=1` per symbol. |
| **Symptom** | One boundary missing per symbol per replay run (76 generated → 75 emitted). Per-script success matrix shows N/152 instead of N/154 baseline-corrected. Phase 4b 2026-05-07 run: gamma 144/152, volatility 147/152, options_flow 150/152 — all reflect this skipped boundary cascading to dependent scripts. |
| **Root cause** | `hist_spot_bars_1m` and `hist_option_bars_1m` capture bars whose `bar_ts` represents the bar START minute. Session ends 15:30 IST inclusive, so the last bar STARTS at 15:29 IST (covers 15:29:00–15:29:59) and there is no bar starting at 15:30:00. Replay's boundary generator emits 76 5-min boundaries 09:15–15:30 inclusive; the 15:30 one has no corresponding hist bar. |
| **Workaround** | Accept 75-boundary replay as healthy. None of the per-script success criteria fail because of this — the orchestrator's per-script success-rate matrix is the trustworthy diagnostic. |
| **Proper fix** | Two options: (a) extend `hist_spot_bars_1m` capture to write a 15:30:00 bar at session close (operational change to capture pipeline; requires upstream coordination); (b) reconstructor synthesizes a 15:30 boundary by carrying forward 15:29's close as 15:30's spot (single-line addition; preserves bar count parity). Option (b) is simpler but introduces a synthetic-bar source that future debugging needs to be aware of. |
| **Cost to fix** | ~30min (option b) to ~1 session (option a). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-09 |

---

### TD-095 — `atm_iv_avg` unit ambiguity surfaces in `detect_ict_patterns_runner.py` Kelly sizing path

| | |
|---|---|
| **Severity** | S3 (potentially mis-sizes Kelly lots if Kelly was designed for percent — observed cosmetically as `iv=0.1%` in detector log when actual IV is 14.9%; functional impact pending verification of `compute_kelly_lots` IV-input expectation). |
| **Discovered** | 2026-05-09 (Session 24 — observed during ENH-93 Phase 3 ICT detector run on 2026-05-07; replay surfaced the issue but it applies to live identically). |
| **Component** | `compute_volatility_metrics_local.py` (writes `atm_iv_avg`); `detect_ict_patterns_runner.py` `load_atm_iv` reader + Kelly-lot writer; `merdian_utils.compute_kelly_lots` (consumer). |
| **Symptom** | `compute_volatility_metrics_local.py` writes `atm_iv_avg` as decimal fraction (e.g., 0.149 for 14.9%). Live and replay `detect_ict_patterns_runner.py` reads `vol.get("atm_iv_avg")`, formats as `f"{iv:.1f}%"` rendering 0.149 as "0.1%" in the log line, AND passes 0.149 to `compute_kelly_lots(_, _, _, current_spot, atm_iv_pct, dte_days)`. The parameter name `atm_iv_pct` suggests percent expected but receives decimal. |
| **Root cause** | Unit drift between writer (decimal) and consumer (parameter named `_pct` suggests percent). Has been latent across both production paths since at least Session 13 ENH-37 wiring. Replay made it visible because the detector log printed under operator inspection. |
| **Workaround** | None operationally — Kelly outputs lot counts that look reasonable (T1:112, T2:90, T3:45 for INR 25,000 capital) so end-state is not obviously broken. May or may not be silently mis-sizing depending on Kelly's IV-elasticity term. |
| **Proper fix** | Inspect `compute_kelly_lots` signature + IV-elasticity math. Decide which unit is canonical (decimal or percent). Fix writer or consumer to align. Then audit every other consumer of `atm_iv_avg` (signal builder reads it for HIGH_IV gate; gamma metrics; etc.) for the same drift. Likely 1-2 hour investigation + small patch. |
| **Cost to fix** | ~1 session (find canonical, audit consumers, patch). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-09 |

---

### TD-094 — `hist_option_bars_1m.oi=0` across all rows from S22 Kite backfill (Kite `historical_data` API does not return OI for index option minute bars) — RECLASSIFIED STALE Session 29

| | |
|---|---|
| **Session 29 status — RECLASSIFIED STALE (2026-05-16)** | **Verified empirically that the source-data limitation described below NO LONGER APPLIES.** Vendor-purchased historical data has replaced the S22 Kite backfill in `hist_option_bars_1m`. S29 query (`SELECT date_trunc('month', bar_ts) AS m, COUNT(*), AVG(oi)::int AS avg_oi, MAX(oi) FROM hist_option_bars_1m GROUP BY m ORDER BY m`) returns OI populated 99.9% across all 12 months Apr 2025 → Mar 2026: avg ~1M, max 66M per row. The replay reconstructor's live-OI-lift compensation (`_fetch_live_oi_for_replay`) remains correct architecturally but is no longer needed for OI specifically — historical OI is now in `hist_option_bars_1m` directly. **TD-094 is reclassified as stale documentation, not an active code defect.** When the original S22 backfill was replaced with vendor data is unknown (no commit marker in scope); finding the replacement boundary is not blocking but worth documenting. **Operational discipline lesson:** when a TD claims a data limitation, verify against current table state before designing around the limitation. Codified into CLAUDE.md S29 operational findings. **Unblocks Phase 0b dimensions** that were gated on gamma-context: P1 LONG_GAMMA, P3 flip_distance, P5 PINNED proxy (initial S29 P5 run was constrained by gamma_metrics sparsity — backfill `backfill_gamma_metrics_to_main.py` running at S29 close to produce full-cohort gamma_metrics for re-run). Also unblocks ENH-80 per-strike GEX work. **Action:** retain entry in tech_debt for audit history; mark RECLASSIFIED-STALE in footer; do not re-open as active. |
| **Severity** | S2 (would have permanently broken ENH-93 replay reconstructor without the live-OI-lift compensation; affects any future research / replay that needs OI from `hist_option_bars_1m`). |
| **Discovered** | 2026-05-09 (Session 24 — diagnosed during ENH-93 Phase 2 reconstructor build when `replay_compute_gamma_metrics` returned `DATA_ERROR all option rows filtered out as unusable` for run_id from reconstructed chain). |
| **Component** | `hist_option_bars_1m` Supabase table; data was written by S22 Kite backfill (`backfill_option_zerodha_OI_FIXED.py`); root cause is Kite Connect `historical_data` API behavior, not the backfill script. |
| **Symptom** | Direct query: `SELECT COUNT(*), MIN(oi), MAX(oi) FROM hist_option_bars_1m WHERE trade_date='2026-05-07'` returns ~8,250 rows for NIFTY with oi MIN=0 MAX=0. Volume populates correctly (e.g., 114,790 / 942,240 / 1,945,645 — full session traded volumes). Downstream consequence: replay reconstructor wrote chain rows with oi=0; `compute_gamma_metrics` filter `gamma!=0 AND oi>0` drops every row; gamma computation fails entirely. |
| **Root cause** | Kite Connect `historical_data` REST endpoint returns OHLC + Volume for index option minute bars but does NOT include open interest. OI is only available via real-time WebSocket OI ticks (KiteTicker `oi` field at run-time) or `quote()` REST calls (snapshot per-strike, run-time only — not historical). The S22 backfill assumed implicitly that historical_data returned OI; it does not. The defect was undetected because S22 backfill was followed immediately by ENH-93 work which initially planned to use only volume from hist_option_bars_1m. |
| **Workaround** | Permanent compensation in `replay_chain_reconstructor.py` `_fetch_live_oi_for_replay`: lifts OI from live `option_chain_snapshots` per (boundary, strike, option_type) tuple within ±150s tolerance window of each replay 5-min boundary. Live OI for past dates is immutable; this is a permitted READ from live per ADR-008. Tested on 2026-05-07: NIFTY 35,668 live rows → 35,668 entries across 74/76 boundaries; SENSEX 31,820 live rows → 30,100 entries across 70/76 boundaries (6 SENSEX boundaries in 2026-05-07 OI-gap windows have no live data to lift, producing oi=0 in those replay rows; cascades to gamma/volatility/options_flow failures at those boundaries). |
| **Proper fix** | Three options: (a) Re-backfill OI via Zerodha `quote()` per strike — many calls but accurate, requires per-day per-strike snapshot capture; (b) Drop `hist_option_bars_1m.oi NOT NULL` constraint, write NULL when unavailable, change downstream filters from `oi > 0` to `oi IS NULL OR oi > 0` — preserves backfill semantics but loses signal on actual zero-OI strikes; (c) Skip `hist_option_bars_1m` entirely for OI in research/replay; always lift from live `option_chain_snapshots` (current replay strategy) — works for any date where live captured the chain, fails for dates where live ingest was completely down. Recommend (a) for proper fix when research needs OI from past dates beyond what live captured. |
| **Cost to fix** | (a) ~2 sessions (per-strike `quote()` snapshot capture script + backfill of historical date range). (b) <1 session (DDL + filter audit). (c) Already in place via reconstructor. |
| **Blocked by** | Decision: which historical date ranges need OI? If only ENH-93 replay use case, (c) suffices. If broader research (e.g., regime studies on 2024-2025 historical data), (a) or (b) needed. |
| **Owner check-in** | 2026-05-09 |

---

### TD-087 — `hist_option_bars_1m.bar_ts` IST-as-UTC defect (5h30m phantom offset; only on option bars, not spot bars)

| | |
|---|---|
| **Severity** | S2 (silently mis-aligns option bars by 5h30m if read naively; replay reconstructor compensates but every other consumer needs awareness). |
| **Discovered** | 2026-05-09 (Session 24 — diagnosed during ENH-93 Phase 2 reconstructor build when boundary lookups returned no option bars at canonical UTC boundaries despite 8,250 rows present). |
| **Component** | `hist_option_bars_1m` Supabase table `bar_ts` column; introduced by some S22 backfill or upstream historical-data ingest path (specific root commit not identified). `hist_spot_bars_1m.bar_ts` is correctly stored UTC; the defect is option-bars-only. |
| **Symptom** | A bar that represents the 09:15 IST minute (= 03:45 UTC) is stored as `'2026-05-07 09:15:00+00'` instead of `'2026-05-07 03:45:00+00'`. The clock value is IST but the timezone tag is UTC, so `datetime.fromisoformat()` yields a datetime that is 5h30m AHEAD of the true UTC instant. Downstream code that does direct UTC-boundary lookup (`bars_by_ts.get(boundary_utc, [])`) finds nothing. |
| **Root cause** | Either upstream Kite-historical-data response timestamps are in IST and the ingest path tagged them `+00:00` without conversion, OR a `.replace(tzinfo=...)` instead of `.astimezone(...)` was used somewhere in the backfill chain. Closely related to TD-084 (S22 same-session resolution: `backfill_option_zerodha_OI_FIXED.py` had `.replace(tzinfo=ZoneInfo('UTC')).astimezone(IST)` which mis-shifted timestamps) — TD-087 is the residual defect where the timestamps in the table never got corrected. |
| **Workaround** | Permanent compensation in `replay_chain_reconstructor.py` `_fetch_hist_option_bars`: subtracts `timedelta(hours=5, minutes=30)` from each parsed `bar_ts` before storing as `bar_ts_dt`. Documented in code comment: "DO NOT apply this adjustment to hist_spot_bars_1m — that table stores correct UTC." |
| **Proper fix** | Two options: (a) Backfill correction — `UPDATE hist_option_bars_1m SET bar_ts = bar_ts - INTERVAL '5 hours 30 minutes'` after verifying every row is affected (must be all-or-none; mixed rows would corrupt the fix). (b) Schema decision: rename column to `bar_ts_ist_as_utc` to make the convention explicit, document, and adjust every consumer. Option (a) preferred — single DDL run, all consumers get correct UTC. |
| **Cost to fix** | (a) ~30min for the UPDATE + verification queries; ~1 session if the audit reveals mixed rows requiring per-row inspection. |
| **Blocked by** | Verification that all hist_option_bars_1m rows uniformly have the defect (no mixed-correctness). |
| **Owner check-in** | 2026-05-09 |

---

### TD-084 — `backfill_option_zerodha_OI_FIXED.py` UTC/IST timezone bug truncated Kite output to 46 bars per strike (RESOLVED same session)

> **Status: RESOLVED** Session 22 (2026-05-07) — see Resolved (audit trail) below for closure details. Listed here briefly to reflect the discovery of a pattern: any code that does `.replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)` to a Kite-returned `historical_data` datetime is wrong (Kite returns IST-tagged datetimes natively).

---

### TD-083 — ExecutionLog rejects `OUTSIDE_MARKET_HOURS` exit_reason from capture_spot_1m_v2 (RESOLVED Session 29 via TD-NEW-J)

**RESOLVED Session 29 (2026-05-14) — same root cause as TD-NEW-J, unified closure.** See TD-NEW-J entry above + Resolved (audit trail) section below. Fix routed via code-side rename rather than enum migration: `'OUTSIDE_MARKET_HOURS'` → `'OFF_HOURS'` at `capture_spot_1m_v2.py` call-site L346 + docstring L36 (`patch_s29_td_new_i_j_v2.py`). The `'NO_DATA'` exit_reason mentioned in original filing was a sibling case not exercised in production this session — recommend separate audit if it ever fires.

---

### TD-082 — `ingest_option_chain_local.py` contract miscalibration: backfill spike of 482 writes vs expected 50 logged as success (write-contract too permissive)

| | |
|---|---|
| **Severity** | S3 (degrades audit signal but doesn't break the pipeline; backfill-style spikes blur the line between "real run wrote 50 rows successfully" and "10x burst-write somehow" — both green) |
| **Discovered** | 2026-05-07 (Session 22 — surfaced during ingest_option_chain failure pattern audit; one row in `script_execution_log` showed 482 actual_writes for `option_chain_snapshots` where typical run writes ~50) |
| **Component** | `ingest_option_chain_local.py::_write_exec_log()` and the `contract_met` predicate |
| **Symptom** | One run on 2026-05-07 logged 482 rows written to option_chain_snapshots, compared to typical 50 per run. `contract_met=true` because predicate is `actual_writes >= 1`. The 482-row write was likely a multi-cycle accumulation from a partially-stuck process or coalesced retry, not a single intended cycle. |
| **Root cause hypothesis** | Either (a) script had a stuck cycle that buffered N cycles' worth of writes, or (b) write-batching accumulated mid-outage and flushed at recovery. Not yet diagnosed. |
| **Workaround** | None. Audit treats >300-row writes as anomaly worth investigating but doesn't fail the contract. |
| **Proper fix** | Tighten contract: `contract_met = (actual_writes >= 30 and actual_writes <= 100)` for option_chain_snapshots — outside that band is contract violation regardless of direction (zero rows = bad ingest, 500 rows = stuck or stale buffer). |
| **Cost to fix** | ~3 exchanges (read script, identify write path, tighten predicate, verify on backfill day). |
| **Blocked by** | TD-080 (Dhan outage diagnosis — same script, same module). |
| **Owner check-in** | 2026-05-07 |

---

### TD-081 — No data-freshness guard between primary ingestion and derived layers — signal builder produces signals on stale data without warning

| | |
|---|---|
| **Severity** | S2 HIGH (architectural — when primary ingestion is partially failing as Session 22, the derived signal layer continues to produce output based on last-good snapshot, which can be 30-60 minutes stale; signals get fired into Telegram with no staleness flag) |
| **Discovered** | 2026-05-07 (Session 22 — observed during Dhan outage; while ingest_option_chain failed 50% of cycles, build_trade_signal_local.py continued producing signal_snapshots rows; downstream consumers had no way to know the option_chain underlying signals was stale) |
| **Component** | `build_trade_signal_local.py`, `compute_gamma_metrics_local.py`, `compute_volatility_metrics_local.py`, etc. — the derived chain. Architectural defect spans the pipeline. |
| **Symptom** | When Dhan ingest fails for 30+ minutes, derived layer still emits signals using the last successful option_chain_snapshots row as if it were current. Signal confidence/direction gets computed against stale data. |
| **Root cause** | No upstream-freshness check before derived computation. Each derived script reads the latest row of its source table; if the source table hasn't received a fresh row, the derived script proceeds anyway. |
| **Workaround** | None operationally. Operator trusts pipeline + ad-hoc inspects script_execution_log when alerts surface. |
| **Proper fix** | Each derived script must check `option_chain_snapshots.created_at` (or upstream equivalent) and reject if older than max-staleness threshold (e.g., 10 min for 5-min cycle). Reject = exit with SKIPPED_STALE_SOURCE; don't write a signal. Telegram alert escalates if N consecutive cycles skip. Pattern: ENH-71 instrumentation layer extended with a "freshness gate" predicate. |
| **Cost to fix** | ~2 sessions (design + implement across 6 scripts + test). Likely should be filed as ENH-93 not just TD. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-07 |

---

### TD-080 — AWS Dhan token refresh failure mode (cross-script Dhan 401 outage on 2026-05-07; reframed Session 25; PROMOTED to S1 RECURRING Session 29)

| | |
|---|---|
| **Session 29 status update — PROMOTED to S1 RECURRING (2026-05-14)** | **Third documented occurrence (S22 2026-05-07 151/299; S28 2026-05-13 alluded; S29 2026-05-14 99/808 = 12.3% failure rate over 4h19m).** Same token, same `/v2/optionchain` endpoint, same alternating-window symptom shape. Per-token rate-limit instability hypothesis (S22) now corroborated across 3 sessions. **Priority elevated from S2 HIGH to S1 RECURRING.** **ENH spec for rate-limit-aware retry layer + circuit breaker in `ingest_option_chain_local.py` is P0 carry-forward to S30.** Likely fix track: (a) exponential backoff with per-token quota tracking; (b) circuit breaker pause after 429 to avoid escalating to threatened "user being blocked"; (c) dedicated runbook for Dhan 429 storm response. See `CASE-2026-05-14-spot-gap-backfill.md` §5 for full S29 occurrence analysis. Pre-S29 instrumentation (S26 probe-log) is still relevant input but is now upstream of a confirmed production-blocking failure class, not just a diagnostic curiosity. |
| **Severity** | S2 HIGH (loses ~70% of trading day's option chain ingest; permanent loss of full chain greeks/IV smile/OI per strike for outage windows; option_chain_snapshots gap of 64 5-min windows on 2026-05-07) |
| **Discovered** | 2026-05-07 (Session 22 — incident from 09:30 IST onwards, 151 of 299 attempts failed with `401 Authentication Failed - Client ID or Token invalid`). **Reframed S25 2026-05-10:** investigation surface narrowed from "Dhan option chain endpoint reliability" to "AWS Dhan token refresh failure mode" based on cross-script 401 evidence on 2026-05-07. |
| **Component** | `refresh_dhan_token.py` running on AWS at 03:05 UTC (08:35 IST) — single source for AWS-side Dhan tokens consumed by `ingest_option_chain_local.py` AND PreOpen 03:38 UTC (`capture_postmarket_1600.py` not affected). Cross-script 401s on 2026-05-07 (PreOpen 03:38 UTC + option chain 09:30-13:30 IST + 14:45-15:25 IST) point to single token-refresh failure on AWS, not a Dhan-side service incident. |
| **Symptom** | Alternating 50/50 success/fail pattern across full trading day on 2026-05-07; hourly-stable. Two outage windows: 09:30-13:30 IST (~4hrs) + 14:45-15:25 IST (40min). Manual token refresh at 13:30 IST temporarily restored, broke again ~14:45. Same token served `/charts/intraday` (capture_spot_1m_v2) at 97% throughout — endpoint-specific behavior consistent with token being valid for some endpoint paths and not others, which is itself evidence of token-refresh-mode partial success rather than Dhan-side endpoint-specific block. |
| **Root cause** | **UNCONFIRMED but narrowed.** Working hypothesis (S25): `refresh_dhan_token.py` on AWS occasionally produces a token that is partially valid (works for `/charts/intraday`, fails for `/optionchain` or similar) — possibly due to a token-scope or session-binding issue at refresh time. Six hypotheses from S22 remain refuted (token sync silent failure, TD-072 battery side-effect, AWS competing writer, MeridianAlpha competition, stale-token daemon, shadow_runner in-memory stale token). New focus: the refresh script's actual API call sequence and what the freshly-issued token's effective scope is. |
| **Workaround** | Local-side Dhan ingestion via Kite/MeridianAlpha backfill remains operational redundancy until AWS reliability established. Validated end-to-end Session 22 (24,749 rows for 2026-05-07). |
| **Proper fix** | Dedicated investigation session: (a) instrument `refresh_dhan_token.py` with full-response logging; (b) compare freshly-issued token's response on `/charts/intraday` vs `/optionchain` immediately post-refresh; (c) reproduce on a controlled day; (d) once root cause is identified, harden refresh script and observe N clean trading days before declaring TD-080 closed. |
| **Cost to fix** | 1 dedicated investigation session for root-cause + 1 session for hardening + N trading days observation. |
| **Blocked by** | Nothing — investigation session is the next logical work item. |
| **Blocks** | **ADR-006 drafting (Phase α Q3 sequencing — token reliability FIRST, ADR-006 actions second).** Local Capture writers (16:00 post-market dual-write disposal, 09:08 PreOpen disposal) cannot execute until AWS Dhan-token-dependent reliability is established across N clean trading days. |
| **Owner check-in** | 2026-05-10 (S26 instrumentation deployed — see below). Next investigation: post-Mon-2026-05-12 probe-log triage; dedicated root-cause session if probe-log evidence supports a hypothesis. |
| **Session 26 status update (instrumentation)** | **DEPLOYED** Session 26 commit `718ef39` — root-cause investigation pending Mon 2026-05-12 first probe-log triage (P0b S27). New Supabase table `dhan_token_probe_log` (12 columns) + view `v_dhan_token_probe_today`. `pull_token_from_supabase.py` extended 50 → 355 lines: atomic .env write with readback verify; post-write probes of Dhan `/v2/marketfeed/ltp` + `/v2/optionchain/expirylist` immediately after .env write; audit logging to probe-log table; asymmetry verdict logic (both 200 → OK; one 200 + one 4xx → PARTIAL with endpoint flag; both fail → FAIL token-side problem). Sunday 2026-05-10 smoke test PASS at 20:28 IST: token len=280, both probes 200 OK, verdict=OK. AWS cron `5 3 * * 1-5 /usr/bin/python3 pull_token_from_supabase.py` continues to fire 03:05 UTC = 08:35 IST as before; no scheduler change. **Mon 2026-05-12 verification SQL** (Topology §9.B documented): `SELECT * FROM v_dhan_token_probe_today ORDER BY ts_ist DESC LIMIT 10;` Decision tree: both 200 → token side healthy if option-chain still fails 09:15 IST then endpoint-side investigation; partial → JWT scope / endpoint-specific auth; both fail → upstream TOTP / login flow on Local 08:15. Backup `pull_token_from_supabase_PRE_S26.py` preserved. **Status remains UNRESOLVED** until probe-log evidence supports a root-cause hypothesis; instrumentation is the input to investigation, not the closure. |
| **Resolution (S36 2026-05-25)** | **CLOSED via ENH-99 SHIPPED.** Failure-shape diagnosis against `script_execution_log` partitioned the failure surface into three independent modes (A: 429 quota / B: 401 token / C: orphan RUNNING). **Mode B (token 401) was determined to be SOLVED UPSTREAM at S29** via the S26 commit `718ef39` instrumentation evolution path culminating in `pull_token_from_supabase.py` atomic write + readback verify + post-write Dhan endpoint probes + `dhan_token_probe_log` audit logging — zero post-S29 401 incidents observed in 11 instrumented trading days. Mode B was therefore DROPPED from ENH-99 scope. **Mode A (429 quota)** was addressed via ENH-99 Component 1: `gamma_engine_retry_utils.retry_call` extended with `retry_predicate: Callable[[Exception], bool] | None = None` kwarg (per-attempt predicate gates retry; non-predicate exceptions raise immediately without consuming budget); 2 Dhan retry sites in `ingest_option_chain_local.py` at lines 316 + 346 bumped from attempts=3 / delay=5.0s / x1.5 to attempts=6 / delay=15.0s / x1.5 with `retry_predicate=is_dhan_429` predicate; ~24s → ~96s retry budget vs ~60s Dhan quota window (margin of safety). Patches deployed via `patch_s36_enh99_v2.py` (INGEST) + `patch_s36_enh99_v3.py` (RETRY_UTILS via regex-anchor `def retry_call\(.*?raise RuntimeError\([^)]*\)` with re.DOTALL after v1+v2 literal-anchor approaches failed on CRLF/LF straddle); backups `_PRE_S36.py` preserved; AST validated pre+post. **Mode C (orphan RUNNING)** was addressed via ENH-99 Component 2: NEW `orphan_run_janitor.py` (Local) using house DB convention (raw HTTP via `requests` against `/rest/v1/*`, not supabase-py); int4 duration clamp `min(int(age_ms), 2_147_483_647)` per D.18.4; PATCH closes any RUNNING row aged > 5 min to `exit_reason='DATA_ERROR'` + `notes='ORPHAN_RECOVERED: age_min=N'` prefix + clamped `duration_ms`. `MERDIAN_Orphan_Janitor` Task Scheduler task registered weekly Mon-Fri 09:14 IST (Hidden + IgnoreNew + 5min execution limit; task count 19 → 20). Smoke-fire test 2026-05-25 17:26:26 closed 22/24 orphans + 2 REPL stragglers (after int4 clamp fix) — final state 0 RUNNING > 5min. **Component 3** (telemetry): `[RETRY_BURN_DOWN]` stderr tag on final retry failure carries script identity + last exception class + attempt count. **Component 4** (audit thresholds in `merdian_daily_audit.py`) DEFERRED to S37+ pending config schema visibility. **TD-080 priority status:** PROMOTED at S29 to S1 RECURRING (third documented occurrence on 2026-05-14 99/808 cycles); SHIPPED at S36 via ENH-99. **No further root-cause investigation of the original 2026-05-07 cross-script 401 outage is required** — the S26 → S29 instrumentation + atomic-write hardening evolution path silently resolved the recurrence pattern (verified empirically: zero post-S29 401s); ENH-99 Component 1 addresses the 429 quota storm that emerged as the residual recurring failure mode. **Cross-references:** ENH-99 detail block in Enhancement Register Part 4; Assumption Register §D.18.2 (capture-layer Mode A/B/C taxonomy); §D.18.3 (PostgREST Prefer header RLS interaction); §D.18.4 (int4 duration_ms clamp pattern); System Map §A.S36 (orphan_run_janitor.py + patched scripts inventory); Deployment Topology §7.2 (MERDIAN_Orphan_Janitor task row + 19 → 20 count). |

---

### TD-079 — Zone date-expiry vs ICT canon (RESOLVED Session 26 via ADR-005 implementation)

**RESOLVED Session 26 (2026-05-10).** Full closure block is in the **Resolved (audit trail)** section below. Patch script `patch_s26_td079_zone_validity.py` applied 13 surgical replacements AST-validated implementing Phase α Q1 answer (S25 architecture conversation): D/W OB/FVG `valid_to=None` price-breach-only canonical; 1H OB/FVG `valid_to=str(trade_date+timedelta(days=7))` tactical fallback; `expire_old_zones()` filter widened `["W","D"]` → `["W","D","H"]`; PDH/PDL date-expiry unchanged. Backfill SQL revived 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k from EXPIRED → ACTIVE valid_to=NULL. Live rebuild produced 80 zones; Pine overlay 36 → 62 zones (49 HTF + 13 intraday). Commit `0731e67`. ADR-005 formal draft (P2 S27 carry-forward) follows the implementation per CLAUDE.md S26 lesson: architecture-defect TDs implementable before formal ADR when Phase α answer in hand and decision recorded in Decision Index + Assumption Register §D.7.

---

### TD-078 — TD-070 closure verification incomplete — empirically multi-week BULL_OB lookback may not be firing as designed

**RESOLVED Session 25 (2026-05-10).** Full closure block is in the **Resolved (audit trail)** section below. SQL verification confirmed TD-070 v2 multi-week unbreached-anchor lookback fires as designed; the apparent absence of an Apr-13 BULL_OB row was a schema-convention misunderstanding, not a missed detection.

---

### TD-077 — Wide FVG zones during volatile weeks lack outlier filter

| | |
|---|---|
| **Severity** | S4 LOW (cosmetic + signal-quality edge case — during high-volatility weeks FVG zones can span 800-1500 points which dominate the Pine overlay and reduce visual clarity) |
| **Discovered** | 2026-05-06 (Session 21 — observed during HTF zone rebuild; one BEAR_FVG on NIFTY spans 1,200 points) |
| **Component** | `build_ict_htf_zones.py` FVG detection (no outlier filter on zone_high - zone_low spread) |
| **Symptom** | Volatile weeks produce FVG zones with high-low spread of 800-1500 points (compared to typical 100-300). These dominate Pine overlay, can mask narrower more-actionable zones, and produce overly-large stop levels if zone is used for execution. |
| **Root cause** | Detection includes any 3-bar imbalance regardless of size. No upper bound on zone spread. |
| **Workaround** | Operator visually filters wide zones during analysis. Pine `show_h` toggle helps. Not blocking. |
| **Proper fix** | Add `MAX_ZONE_SPREAD_PCT` parameter (e.g., 1.5% of underlying for W) and reject FVG candidates wider than that. Verify on Session 21's wide-zone case. |
| **Cost to fix** | ~2 exchanges. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-07 |

---

### TD-076 — SENSEX DTE gate persistent block on weekly expiry

| | |
|---|---|
| **Severity** | S4 LOW (operator-tier visibility issue; the DTE gate skips signals on SENSEX expiry day every Thursday which is a high-edge expiry-gamma window) |
| **Discovered** | 2026-05-06 (Session 21 — observed signal_snapshots for SENSEX Thursday expiry day showing all DTE=0 SKIPPED) |
| **Component** | `build_trade_signal_local.py` DTE gate logic (`signal_snapshots.dte_gate_blocked`) |
| **Symptom** | Every SENSEX Thursday expiry day shows all signals SKIPPED with reason `DTE=0`. SENSEX expiry-gamma is one of the higher-edge windows historically (Exp 9 SMDM analysis). Gate is over-conservative. |
| **Root cause** | DTE gate built around NIFTY's previous Thursday-expiry pattern when NIFTY was Thursday-weekly. With NIFTY moved to Tuesday and SENSEX still Thursday, the gate doesn't account for SENSEX-specific edge on its own expiry. |
| **Workaround** | Operator manually overrides on SENSEX expiry days. |
| **Proper fix** | Per-symbol DTE gate: NIFTY Tuesday allows DTE=0 with attenuation; SENSEX Thursday allows DTE=0 with full sizing (or ENH-77-style time-band routing for expiry-gamma window). |
| **Cost to fix** | ~1 session. |
| **Blocked by** | TD-074 (related ENH-77 routing review). |
| **Owner check-in** | 2026-05-07 |

---

### TD-075 — Confidence threshold 60 vs observed max 45 (gate never reached)

| | |
|---|---|
| **Severity** | S3 MED (production gate set to 60 but live signals top out at confidence 45; gate is effectively dead code — never trips, never blocks anything; likely should be lowered to 40-45 or made dynamic) |
| **Discovered** | 2026-05-06 (Session 21 — confidence histogram across signal_snapshots showed max=45, gate at 60 never reached) |
| **Component** | `build_trade_signal_local.py` confidence threshold for trade_allowed gating |
| **Symptom** | trade_allowed always FALSE due to confidence < 60 threshold; no signals ever pass to execution layer. Effective trading gate is purely operator-discretionary at this point. |
| **Root cause** | Threshold derived from a different signal-generation regime (pre-ENH-35? pre-V4?). Hasn't been recalibrated since then. |
| **Workaround** | Operator-discretionary execution. Trade_allowed gate ignored. |
| **Proper fix** | Recalibrate threshold based on observed distribution: median, p75, p90 across last 30 days. Or make threshold dynamic by regime (LONG_GAMMA vs SHORT_GAMMA different). |
| **Cost to fix** | ~1 session — distributional analysis + threshold revision + 2-week shadow validation per Master V15 18.1 rule. |
| **Blocked by** | signal_regret_log accumulation (Master V15 says 30+ sessions before threshold change). |
| **Owner check-in** | 2026-05-07 |

---

### TD-074 — ENH-77 BULL_OB AFTERNOON NIFTY hard skip blocked the only TIER1 signal

| | |
|---|---|
| **Severity** | S3 MED (over-aggressive routing rule — ENH-77 hard-skips BULL_OB+AFTERNOON+NIFTY; 2026-05-06 had a 700pt rally for which the only TIER1 BULL_OB signal was hard-skipped, costing capture) |
| **Discovered** | 2026-05-06 (Session 21 — post-mortem on missed TIER1 signal on 700pt rally afternoon) |
| **Component** | `build_trade_signal_local.py` — ENH-77 time-of-day routing for BULL_OB |
| **Symptom** | BULL_OB signals in AFTERNOON time band (12:00-15:00 IST) on NIFTY are hard-routed to SKIP. The 2026-05-06 rally had a TIER1 BULL_OB at ~13:00 that should have triggered; was skipped per ENH-77 rule. |
| **Root cause** | ENH-77 rule was derived from cohort analysis showing AFTERNOON BULL_OB underperforms; but the rule is hard-skip not attenuation, eliminating the long tail of high-edge AFTERNOON cases. Direction-asymmetric defect: BEAR_OB+AFTERNOON not hard-skipped, only BULL_OB. |
| **Workaround** | Operator-discretionary execution overrides. |
| **Proper fix** | Replace hard-skip with attenuation (size_mult 0.5x instead of 0x) OR rebuild ENH-77 with finer time bands (12:00-13:30 vs 13:30-15:00 may be different cohorts). |
| **Cost to fix** | ~1 session — ENH-77 cohort review + rule revision + 2-week shadow validation. |
| **Blocked by** | signal_regret_log accumulation (same as TD-075). |
| **Owner check-in** | 2026-05-07 |

---

### TD-073 — Momentum direction lagged 700pt rally May 6 by ~60 min

| | |
|---|---|
| **Severity** | S2 HIGH (signal-quality defect — momentum_direction component of build_trade_signal lagged the 2026-05-06 700pt rally by ~60 min; signal stayed BEARISH/NEUTRAL while spot was already in clear bullish expansion; downstream signal direction wrong throughout the lag window) |
| **Discovered** | 2026-05-06 (Session 21 — observed during live trading on rally day) |
| **Component** | `build_momentum_features_local.py` — `momentum_direction` derivation; possibly `ret_session` or `vwap_slope` lag |
| **Symptom** | Spot rallied from 24,200 to 24,900 over ~13:00-14:30 IST window. `momentum_snapshots.momentum_direction` stayed `BEARISH` until ~14:00 then flipped `NEUTRAL` then finally `BULLISH` at ~14:30 — by which point most of the move was over. Lag of ~60 min vs price action. |
| **Root cause hypothesis** | `ret_session` uses session_open as reference; if session opened weak and rallied, ret_session takes time to flip sign. `vwap_slope` is a lagging indicator by construction. Multi-vote system (5 momentum components) may have 3 lagging components dragging the vote. |
| **Workaround** | Operator-discretionary direction override during live trading (but then signal confidence is also wrong). |
| **Proper fix** | Diagnose which of the 5 momentum components is laggiest; consider replacing with a faster-responding indicator (e.g., 5m return + 15m return weighted majority) OR add a "fast momentum override" when 5m return exceeds 0.5%. |
| **Cost to fix** | ~1.5 sessions — instrument each component + correlate with price; design replacement; shadow-test. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-07 |

---


### TD-069 — D timeframe doesn't generate OB/FVG even with real data (W and 1H do)

| | |
|---|---|
| **Severity** | S2 (architectural — daily timeframe contributes 0 directional zones; only PDH/PDL liquidity levels; loses one timeframe of context for ICT MTF context computation) |
| **Discovered** | 2026-05-05 (Session 20 — HTF zone rebuild after spot data backfill produced 33 W OB/FVG NIFTY + 35 SENSEX with real OHLC, but D timeframe produced 0 OB/FVG for both symbols — only PDH/PDL) |
| **Component** | `build_ict_htf_zones.py::detect_daily_zones()` |
| **Symptom** | After spot data backfill produced clean real OHLC for Apr 1 → May 5, weekly detector fired 33+35 OB/FVG zones across full year (correctly distinguishing real candle direction). Daily detector fired 0 OB/FVG despite operating on the same underlying data — only generating PDH/PDL. Direct example: May 4 NIFTY (+0.49% close-vs-open ≥ 0.40% threshold) should fire D-OB but didn't. |
| **Root cause** | Unknown — code review needed. Possible candidates: (a) D detector uses different threshold than W (perhaps stricter `OB_MIN_MOVE_PCT`); (b) D detector requires 3+ trading days for FVG (`prior_dates[-3]`) but only-prior-day for OB — interaction with date logic may have a bug; (c) `target_date` computed differently than W; (d) D detector reads from different source (`daily_ohlcv` aggregated from minute bars) where aggregation may drop OHLC variation. |
| **Workaround** | None — system functions, just loses D-timeframe MTF context. W and 1H zones provide sufficient ICT context for current detection. |
| **Proper fix** | Code review of `detect_daily_zones()` vs `detect_weekly_zones()`. Identify divergence. Likely 1-line or threshold change. |
| **Cost to fix** | ~6 exchanges (read code, identify cause, patch, verify) |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-05 |

---

### TD-068 — `capture_spot_1m.py` writes synthetic O=H=L=C=spot bars to `hist_spot_bars_1m` (RESOLVED same session via v2.1 deployment)

| | |
|---|---|
| **Severity** | S1 (production-impacting — entire BULL_OB / BEAR_OB pattern detection blind to live data because all candles are flat O=H=L=C from synthetic bar; OB detection requires candle direction) |
| **Discovered** | 2026-05-05 (Session 20 — surfaced via Session 19 audit script (broken at time of discovery, fixed in same session) flagging BULL_OB/BEAR_OB zero-emission in `ict_zones`; locked diagnosis after triple-verification: source code reads `O=H=L=C=spot` literally per docstring; today's bars sampled = 376/376 flat; `script_execution_log` confirmed `capture_spot_1m.py` is sole writer to `hist_spot_bars_1m` with 3,897 runs in 30 days) |
| **Component** | `capture_spot_1m.py` synthetic bar writer (lines 165-178: `bar_rows.append({"open": spot, "high": spot, "low": spot, "close": spot, ...})`) |
| **Symptom** | Despite running every minute during market hours and writing to both `market_spot_snapshots` (live spot dashboard) and `hist_spot_bars_1m` (ICT detector input), the bars table contained only synthetic flat candles. ICT detection requires candle direction (`open vs close`); cannot fire on flat bars. Result: 7+ days of zero BULL_OB / BEAR_OB emission in `ict_zones`. |
| **Root cause** | Original `capture_spot_1m.py` design treats `hist_spot_bars_1m` as snapshot table not OHLC table — uses `/v2/marketfeed/ltp` endpoint which returns single price; writes that as O=H=L=C to satisfy schema. Likely unintended consequence of dual-purpose script (spot snapshot + bar writer) where original requirement was just spot capture. OB detection added later assumed real OHLC; never noticed flat bars because BULL_FVG / BEAR_FVG can fire on consecutive close prices alone. |
| **Workaround** | None — went straight to fix. |
| **Proper fix** | `capture_spot_1m_v2.py` (475 lines, v2.1) shipped Session 20: drop-in replacement using `/v2/charts/intraday` endpoint which returns full 1-min OHLC arrays. v2.1 features: market-hours guard (skip outside 09:15-15:30 IST), filler-bar skip (V=0+flat detection prevents post-market filler writes). Same .env vars, same instrumentation, same heartbeat wrapper. Task Scheduler `MERDIAN_Spot_1M` action repointed to v2 with full `pythonw.exe` path. v1 untouched at `capture_spot_1m.py` for rollback. **Backfill of pre-Session-20 historical data:** 16,500 rows for Apr 1 → May 5 backfilled real OHLC via Kite `historical_data` (16 stray 15:30 boundary flats deleted post-backfill). HTF zone rebuild on backfilled data confirmed all 4 ICT pattern types now fire. |
| **Cost to fix** | ~25 exchanges including diagnostic oscillation, backfill, v2 design + write + deploy. Closed same session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-05 — RESOLVED via v2.1 deployment. **Verification deferred to next live cycle** 2026-05-06 09:16:02 IST: query `script_execution_log` for capture_spot_1m_v2 invocations + `hist_spot_bars_1m` for is_flat=false on today's bars. |

---

### TD-067 — Intraday backfill detector for Apr 1 → today historical pattern record

| | |
|---|---|
| **Severity** | S2 (research enablement — system functions live, but historical intraday pattern record for Apr 1 → May 5 missing because pre-TD-068 data was synthetic flats; once backfilled real OHLC exists, detection should be replayed to populate `ict_zones` for those days) |
| **Discovered** | 2026-05-05 (Session 20 — after spot data backfill produced clean real OHLC for Apr 1 → May 5, recognized that runner-based intraday detection only runs forward-going on today's bars; days before today have no `ict_zones` records on real OHLC) |
| **Component** | New script needed: `backfill_ict_zones.py` that walks each day's `hist_spot_bars_1m` and runs `ICTDetector` on each session's bars |
| **Symptom** | `ict_zones` table has no historical records for Apr 1 → May 5 patterns detected on real OHLC. Research/replay queries against this table see zero or mostly-empty data for that range. Live runner only fills today's slot going forward. |
| **Workaround** | None needed for production (live detection works on today). For research replay, run `experiment_15_pure_ict_compounding.py` which simulates detection per session (different code path, different output format). |
| **Proper fix** | Build `backfill_ict_zones.py`: load `hist_spot_bars_1m` for date range, group by symbol+trade_date, instantiate `ICTDetector`, walk bars, write to `ict_zones` with same schema as live runner. Verify against today's real-time output. ~30 min build + run for Apr 1 → May 5 (22 trading days × 2 symbols). |
| **Cost to fix** | ~10 exchanges (build + verify + run) |
| **Blocked by** | TD-068 RESOLVED (real OHLC exists for Apr 1 → May 5 now) |
| **Owner check-in** | 2026-05-05 |

---

### TD-060 — Live runner emits zero OBs across 14 days due to detect_ict_patterns check_from filter / runner cycle stride mismatch (RESOLVED same session)

| | |
|---|---|
| **Severity** | S1 (production-impacting — entire bear-side OB and most FVG signal flow blind to live system) |
| **Discovered** | 2026-05-03 (Session 17 — uncovered while attempting ENH-88 BULL_FVG cluster gate deploy; `signal_snapshots` last 14 days had only NONE and BULL_FVG, zero OBs of either direction; investigation revealed runner cycles 14 × ~2280 = ~32,000 invocations producing zero OB rows in `ict_zones`) |
| **Component** | `detect_ict_patterns_runner.py` invocation of `detector.detect()` AND `detect_ict_patterns.py` `check_from = max(0, len(bars) - 10)` filter |
| **Symptom** | Despite Session 17 TD-058 detector patch (BEAR_FVG branch added) and Session 15 zone-builder fix (1,384 W BEAR_FVG zones in `hist_ict_htf_zones`), the live `ict_zones` table had only 76 BULL_FVG rows and 0 OBs/BEAR_FVG/JUDAS over 14 trading days. Sub-detectors (`detect_obs`, `detect_fvg`) found 14 OBs + 13 FVGs on Feb 01 NIFTY when called directly; `ICTDetector.detect()` returned 0 patterns on the same data. |
| **Root cause** | Two-bug pair. (a) `detect_ict_patterns.py` had `check_from = max(0, len(bars) - 10)` filter that limited visible OB-candle slot to indices `[len-10, len-7]` — exactly 4 bars wide regardless of input size, because `detect_obs` caps `i in range(n - 6)`. (b) `detect_ict_patterns_runner.py` passed `bars=bars` (full session ~400 bars) every 5-min cycle. Combined: cycle stride=5 bars + eligible window=4 bars = systematic gap where most session OBs miss every cycle. Only OBs at session-idx N where some cycle ends at N+7..N+10 surfaced; those ending exactly on cycle boundaries (multiples-of-5+10) caught their target. End-of-day BULL_FVGs slipped through more often than mid-day BEAR_OBs, explaining the all-BULL_FVG production rows. |
| **Workaround** | None applied — went straight to fix. |
| **Proper fix** | F4 + G1 patch pair shipped as TD-060 fix: (F4) `detect_ict_patterns_runner.py` line `bars=bars` → `bars=bars[-30:]` so per-cycle scan window is bounded to last 30 bars. (G1) `detect_ict_patterns.py` `check_from` line + 3 `if idx >= check_from` filters from list comprehensions removed entirely. Per-cycle re-detection of older patterns is idempotent via `on_conflict` upsert in `write_new_zones()`. Verification: `diag_td060_full_day_smoke.py` simulated 80 5-min cycles on Feb 01 NIFTY, achieved 14/14 OB coverage = 100% within tradeable hours (versus 9/14 = 64% with F4 alone, 0/14 pre-fix). Both patches deployed Local + AWS via `git pull`; `_PRE_S17_TD060.py` snapshots preserved. |
| **Cost to fix** | ~6 exchanges of diagnostic + 2 patches + 3 hotfix iterations on related Pine work. Closed same session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-03 — RESOLVED |

---

### TD-061 — Task Scheduler entry points spawn visible console windows during pre-market and post-market hours (RESOLVED Session 29 — see Resolved section)

**SEE Active-section S29 entry above and Resolved (audit trail) closure block below.** Original Active body (S17 filing) preserved in commit history (`git show HEAD~N:tech_debt.md` to recover pre-S29 text).

---

### TD-062 — Saturday LastRun timestamps on 5 Task Scheduler tasks despite DoW=62 (Mon-Fri) trigger — stuck-process accumulation root cause unknown

| | |
|---|---|
| **Severity** | S2 (operational hygiene — stuck Python processes accumulate across days, eventually requiring kill, which disables tasks until manual re-enable; root cause hidden) |
| **Discovered** | 2026-05-03 (Session 17 — Get-ScheduledTask diagnostic showed Market_Close_Capture, Post_Market_1600_Capture, Session_Markers_1602, Spot_1M, EOD_Breadth_Refresh all had LastRun timestamps from 02-05-2026 (Saturday) despite all having `DoW=62` = Mon-Fri only triggers; LastResult 2147946720 = 0x80070420 = 'instance is currently running') |
| **Component** | Task Scheduler interaction with long-running Python processes; possibly Spot_1M or Supervisor entering hung state on holiday-day calendar queries |
| **Symptom** | Saturday LastRun timestamps decoded NOT as new Saturday triggers (DoW=62 correctly excludes Saturday) but as kill-time artifacts when operator killed the running instances. The LastResult code 2147946720 means a previous instance was still alive when the next scheduled fire attempted to start — Task Scheduler refused to start a duplicate, returned the error code, and recorded the time as LastRun. The accumulated processes were the same task's previous instance still running, NOT new Saturday firings. |
| **Root cause** | Unknown. Hypothesis: a script called by one of the affected tasks (likely Spot_1M which fires every minute, or the Supervisor which spawns child processes) hangs on a Supabase call, network call, or holiday-gate evaluation when calendar state is unusual (NULL open_time per Incident #1 class, or just slow-responding). Task instance never exits. Subsequent triggers fire, find existing instance, error out with 2147946720. Process count grows. |
| **Workaround** | Operator manually kills runaway processes when noticeable; killing disables the task in Windows Task Scheduler until manually re-enabled. Done May-3 this session for all 13 MERDIAN_* tasks. |
| **Proper fix** | Three steps: (1) Identify which script gets stuck — instrument every long-running task with a heartbeat write to `script_execution_log` (or local heartbeat file with rolling timestamp); compare actual LastRun vs heartbeat to find which task's instances outlive their schedule. (2) Add timeout to all Supabase calls in calendar-gate code paths (currently no timeout means a stuck connection hangs forever). (3) Add `subprocess.Popen(timeout=N)` or signal-based kill to supervisor child processes so a stuck Python script gets reaped after reasonable wall time. |
| **Cost to fix** | 1 session for instrumentation, 1 session for fix once root cause identified. |
| **Blocked by** | TD-061 (window-suppression fix may interact — pythonw.exe migration could change process lifecycle behavior; do TD-062 instrumentation first) |
| **Owner check-in** | 2026-05-03 |

---

### TD-063 — Single-instance enforcement missing on Task Scheduler tasks (RESOLVED Session 29 — see Resolved section)

**RESOLVED Session 29 (2026-05-14).** Full closure block in Resolved (audit trail) section below. **NOTE: Same body-state-vs-footer-claim divergence as TD-061** — footer-claimed-RESOLVED at S18; body remained Active. S29 applied: `MultipleInstances=IgnoreNew` setting now hardened on 18/19 MERDIAN_* tasks via `migrate_to_pythonw.ps1` v2 settings pass. 1 failure on `MERDIAN_Intraday_Supervisor_Start` documented as known limitation (multi-trigger XML quirk in PowerShell's `Set-ScheduledTask -Settings <obj>` — workaround: build full `Register-ScheduledTask` XML + `Force` overwrite). See Topology §7.2 final-state table.

---

---

### TD-001 — `pull_token_from_supabase.py` deployed but not in `merdian_reference.json` Block 3 inventory until v18D audit

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-04 (Appendix V18D_v2 audit fix M-01) |
| **Component** | `merdian_reference.json` files inventory |
| **Symptom** | File exists in production, listed in Block 9 failure modes, missing from Block 3 inventory |
| **Root cause** | Inventory update lag — file added in production before being added to JSON |
| **Workaround** | Audit caught it; corrected in V18D v2 |
| **Proper fix** | Pre-commit hook that diffs deployed `*.py` files against `merdian_reference.json` files keys |
| **Cost to fix** | 2 sessions |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-19 |

---

### TD-002 — `breadth_regime` NULL before 2025-07-16 in `hist_market_state`

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | Appendix V18F v2 Block 4 |
| **Component** | `public.hist_market_state` |
| **Symptom** | Any signal validation that filters by `breadth_regime` silently drops Apr–Jul 2025 sessions |
| **Root cause** | Breadth indicator backfill started 2025-07-16; earlier rows have NULL |
| **Workaround** | Validation queries explicitly mark coverage as `2025-07-16 onwards` and exclude earlier sessions |
| **Proper fix** | Backfill `breadth_regime` for Apr–Jul 2025 from raw `equity_eod` |
| **Cost to fix** | 1 session (similar to other backfill scripts) |
| **Blocked by** | nothing — can be done any time |
| **Owner check-in** | — |

---

### TD-003 — `experiment_15b` `detect_daily_zones` date type mismatch (now CLOSED — kept here as template example)

| | |
|---|---|
| **Severity** | ~~S2~~ → moved to Resolved |

*See "Resolved" section below for the closing entry. Keeping the template visible here so future tech debt items have an example to follow.*

---

### TD-004 — `BFO_CONTRACT_05062025.csv` permanent ingestion failure (malformed Date column header)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | Appendix V18D v2 (SENSEX F+O corrected ingest) |
| **Component** | SENSEX F+O daily ingestion pipeline |
| **Symptom** | One file fails ingestion every time it's encountered; logs flag it, pipeline continues |
| **Root cause** | Source CSV from exchange has a malformed header for that single date |
| **Workaround** | Skip-list the file in the ingestion runner; rebuild that date's gamma from adjacent days if needed |
| **Proper fix** | Manually clean and re-ingest the one file; update the source-file checksum |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | — |

---

### TD-005 — `option_execution_price_history` table marked DEPRECATED but not yet DROPPED

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | merdian_reference.json (E-06) |
| **Component** | `public.option_execution_price_history` |
| **Symptom** | Table exists in DB, takes up space, no writers, one stale reader pending migration |
| **Root cause** | `build_option_execution_outcomes_v1.py` migration pending |
| **Workaround** | Mark DEPRECATED in JSON, no new writes |
| **Proper fix** | Complete the outcome engine migration (E-06), then `DROP TABLE` |
| **Cost to fix** | 2 sessions |
| **Blocked by** | E-06 migration |
| **Owner check-in** | 2026-04-19 |

---

### TD-006 — `run_market_tape_1m.py` disabled due to DhanError 401 / Windows ACCESS_VIOLATION

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-07 (merdian_reference.json files entry) |
| **Component** | `run_market_tape_1m.py`, `MERDIAN_Market_Tape_1M` Task Scheduler task |
| **Symptom** | DhanError 401 every run, returncode=3221225786 (Windows ACCESS_VIOLATION), 390 extra Dhan calls/day |
| **Root cause** | Unknown — auth path through this runner differs from main runners |
| **Workaround** | Task disabled. Tape data not currently captured at 1m granularity. |
| **Proper fix** | Either rebuild against shared auth helper (preferred) or formally deprecate and remove |
| **Cost to fix** | 2–3 sessions |
| **Blocked by** | Decision: do we still want 1m market tape? If no → close as WONTFIX |
| **Owner check-in** | — |

---

### TD-007 — `is_pre_market` column in `hist_spot_bars_1m` is vestigial

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-22 (OI-18 investigation during Session 5 — see `session_log.md` 2026-04-22 entry) |
| **Component** | `public.hist_spot_bars_1m` column + all producers and consumers (20+ files) |
| **Symptom** | Column is always written `false` by every producer (`capture_spot_1m.py`, `backfill_spot_zerodha.py`, all backfill and MTF builders). Every consumer filters `.eq("is_pre_market", False)` — the filter drops zero rows because no producer ever writes `True`. Dead code path masquerading as a semantic filter. |
| **Root cause** | Column was added with intent to mark pre-open (09:00–09:14 IST) bars so they could be excluded from analytics. Writer-side implementation was never completed; consumers were written defensively with the filter assumption. Nobody noticed because the filter is functionally a no-op. |
| **Workaround** | None needed — column works, just adds no value. Pre-open bars ARE being captured and used in analytics today; the filter is decorative. |
| **Proper fix** | Two mutually exclusive paths:<br>  (a) Make the column honest — writer computes `is_pre_market = (IST time of bar_ts between 09:00:00 and 09:14:59)`. All consumers accept the new filter semantics. Requires one-time backfill to retag historical pre-open rows from `False` to `True`. Multi-file, ~20 consumer files to review.<br>  (b) Drop the column + drop all `.eq("is_pre_market", False)` filters from consumers. Schema-breaking but simpler. ~1 session. |
| **Cost to fix** | 2–3 sessions for (a), 1 session for (b) |
| **Blocked by** | Decision: is the pre-open exclusion semantics actually wanted, or is it a bug-shaped assumption that no one actually depends on? If wanted → (a). If not → (b). |
| **Owner check-in** | 2026-04-22 |

---

### TD-009 — `.bak` file debris in `docs/registers/`

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-22 (V19A Block 11.4) |
| **Component** | `docs/registers/` directory |
| **Symptom** | Six intermediate `.bak` files left over from the 2026-04-19/20 register unification work: `MERDIAN_Enhancement_Register_v7.md.bak` (35 KB), `_v7.md.bak_v8_20260419_112002` (29 KB), `_v7.md.pre_enh5954.bak` (40 KB), `_v7.md.pre_enh6364.bak` (41 KB), `_v7.md.pre_enh64_close.bak` (45 KB), `_v7.md.pre_enh65.bak` (45 KB). Total ~235 KB. Also present: 5 `merdian_reference.json.bak_*` files totaling ~415 KB. No operational value post-unification. |
| **Root cause** | Safety-backup pattern during `fix_enh*.py` patch runs created these incidentally. Never cleaned up after the patches landed. `.gitignore` now prevents new `.bak` files being tracked (commit `bca369d`), but existing files on disk remain. |
| **Workaround** | Ignore. Not tracked in git anymore. Disk cost trivial. |
| **Proper fix** | Move to `docs/registers/archive/` for audit trail, or delete outright. Archive is the safer default — disk is cheap, audit trail is valuable. |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-22 |

---

### TD-010 — PowerShell 5.1 `Get-Content` defaults to cp1252 when reading UTF-8 files

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-22 (verifying `session_log.md` post-prepend; sibling of OI-20 write-path BOM issue but different path — this one is read-side) |
| **Component** | PS 5.1 default decoder in `Get-Content`, `Select-String`, `Import-Csv`, and most PS file-reading cmdlets |
| **Symptom** | UTF-8 multi-byte characters in files (em-dash `—` = `E2 80 94`, middle dot `·` = `C2 B7`, curly quotes, etc.) display as multi-character cp1252 mojibake — e.g. `—` renders as `â€”`, `·` renders as `Â·`. **File bytes on disk are correct**; only the PS display is wrong. Verified by re-reading the same file with `-Encoding UTF8` flag which renders correctly. |
| **Root cause** | PS 5.1 reads bytes then decodes them with cp1252 by default. The `$PROFILE` fix from OI-20 (which set `$OutputEncoding`, `[Console]::OutputEncoding`, `[Console]::InputEncoding` to UTF-8 without BOM) addresses the OUTPUT / stdout / argv-to-git-commit paths. It does NOT control `Get-Content`'s INPUT decoder — that is governed by the cmdlet's internal default which remains cp1252 on PS 5.1. Two orthogonal PS 5.1 defaults; OI-20 fix covered one, TD-010 is the other. |
| **Workaround** | Pass `-Encoding UTF8` explicitly to every `Get-Content`, `Select-String`, `Import-Csv` call when the target file contains non-ASCII. Irritating but correct. |
| **Proper fix** | Extend `$PROFILE` with `$PSDefaultParameterValues['*:Encoding']='utf8'` — sets UTF-8 as the default for every cmdlet that accepts an `-Encoding` parameter. Verified safe: does not affect cmdlets without an `-Encoding` param; explicit `-Encoding` passes still override. Long-term answer is PS 7 but that's a multi-session migration with Task Scheduler retest burden. |
| **Cost to fix** | <1 session for the `$PROFILE` addition. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-22 |

### TD-015 — `run_preflight.py` 4-stage preflight system is undocumented; reinvented as one-off

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 (Session 7 close + Friday post-market work, morning preflight) |
| **Component** | `run_preflight.py`, runbook coverage, CLAUDE.md "Common operations" table |
| **Symptom** | A canonical 4-stage preflight (env / auth / db / runner_drystart) exists at `run_preflight.py` but is referenced by no runbook, not in CLAUDE.md's operations table, and not surfaced in `merdian_reference.json` operations index. On 2026-04-24 morning the chat re-invented it as `preflight_20260424.py` (now an untracked file in working tree, gitignored as `preflight_*.py` scratch). Future sessions will re-invent it again unless the canonical path is surfaced. |
| **Root cause** | Documentation gap. `run_preflight.py` predates the runbook layer (Rule 11, 2026-04-22); never retroactively given a runbook entry. Tribal knowledge that didn't survive the Session 6 -> 7 chat boundary. |
| **Workaround** | Operator memory. One-off `preflight_20260424.py` written for today, never run again; not committed. |
| **Proper fix** | (a) Create `docs/runbooks/runbook_run_preflight.md` from `RUNBOOK_TEMPLATE.md` documenting the four stages, expected exit codes, when to run each, and the standard "all-PASS = green to start day" criterion. (b) Add row to CLAUDE.md "Common operations" table. (c) Delete `preflight_20260424.py` from working tree. (d) Confirm `merdian_reference.json` has a `files.run_preflight.py` entry; add if missing. |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

### TD-016 — Dhan TOTP scheduled task fails with `Invalid TOTP`; manual run with same seed succeeds

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 08:15 IST scheduled task |
| **Component** | `refresh_dhan_token.py`, `MERDIAN_Refresh_Dhan_Token` Task Scheduler task, Dhan TOTP auth path |
| **Symptom** | 08:15 IST scheduled invocation of `refresh_dhan_token.py` returned `Invalid TOTP`. Manual run of the same script at 09:03 IST, same seed, same host, succeeded on first attempt. Both inside Dhan's accepted TOTP window. No diagnostic context captured at the failing run beyond the error string. |
| **Root cause** | Unknown. Three plausible causes, none yet confirmed: (a) Windows clock drift not surfaced by `w32tm /query /status`; (b) TOTP seed cache mismatch between Task Scheduler service context and interactive PowerShell; (c) Dhan-side rate-limit silently rejecting first call when a stale failed-login is still cached upstream. |
| **Workaround** | Manual `python refresh_dhan_token.py` at session start when the scheduled task fails. AWS picks up the new token via `pull_token_from_supabase.py` after the manual run completes. Token refresh is operator-supervised at session start anyway, so the failure mode is non-blocking — but it costs ~5 minutes per occurrence. |
| **Proper fix** | When the failure recurs, run a 30-minute diagnostic capture: (1) `w32tm /stripchart /computer:time.windows.com` against +/-10s of the 08:15 fire moment, (2) capture exact request/response (envvars, CWD, egress IP, computed TOTP value at the same wall-clock) for scheduled-context vs interactive-context, (3) diff. One of the three suspected causes should fall out. Until reproduction, document the manual-fallback procedure in `runbook_update_dhan_token.md`'s failure-modes section. |
| **Cost to fix** | 1 session diagnosis when it recurs (cannot reproduce on demand). Possibly +1 session for the actual fix once root cause is identified. |
| **Blocked by** | Recurrence — cannot reproduce on demand. Next 08:15 IST `Invalid TOTP` is the trigger. |
| **Owner check-in** | 2026-04-24 |

---

### TD-017 — `build_ict_htf_zones.py --timeframe H` has no scheduled invocation

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 (pre-market `--timeframe H` returned 0 zones; investigation confirmed this is structurally correct but the post-market scheduled run is missing) |
| **Component** | `build_ict_htf_zones.py`, Windows Task Scheduler + AWS cron coverage for `--timeframe H` |
| **Symptom** | The 09:00 IST cron runs `--timeframe D` only. `--timeframe H` requires >= 2 completed 1H candles of the current session and is therefore a no-op pre-market — confirmed not a bug (added to CURRENT.md DO_NOT_REOPEN). But there is no post-market scheduled invocation, so 1H HTF zones in `ict_htf_zones` lag behind D zones whenever the operator forgets the manual run. |
| **Root cause** | Original cron deployment included `--timeframe D` only. Post-market H requirement was identified during today's investigation but never converted into a scheduled task. Behaviour of the builder is correct; scheduling coverage is incomplete. |
| **Workaround** | Manual post-market run by operator. Inconsistently performed — 1H zone freshness is therefore best-effort. |
| **Proper fix** | Add Windows Task Scheduler task **and** AWS cron entry at 16:15 IST (15 min after EOD ingest) running `python build_ict_htf_zones.py --timeframe H`. Mirror logging, exit-code capture, and Telegram alert pattern of the existing 09:00 IST D-timeframe task. Update `merdian_reference.json` cron inventory. Verify whether OI-11 maps cleanly to this concern; if so, mark OI-11 as superseded by TD-017 in the historical OI register (register itself stays closed per Rule 9). |
| **Cost to fix** | 1 session (Task Scheduler + AWS cron + JSON inventory + runbook touch in `runbook_*` if appropriate) |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

### TD-018 — `build_ict_htf_zones.py:468` uses deprecated `datetime.utcnow()`

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-24 (DeprecationWarning surfaced during D-timeframe build run) |
| **Component** | `build_ict_htf_zones.py` line 468 (and likely other callsites repo-wide) |
| **Symptom** | `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).` emitted on every D build. No functional impact today; will hard-break when the cpython release that removes `utcnow()` reaches the deployed Python. |
| **Root cause** | Code written against pre-3.12 Python. `datetime.utcnow()` was deprecated in Python 3.12. |
| **Workaround** | Ignore the warning. Builder produces correct zones. |
| **Proper fix** | Replace `datetime.utcnow()` at `build_ict_htf_zones.py:468` with `datetime.now(timezone.utc)` (and add `from datetime import timezone` import). Verify call-site treats the resulting tz-aware datetime correctly — tz-aware vs naive comparison is the typical breakage on this migration. While in there, `grep -rn "utcnow()" *.py` for other callsites and fix in the same patch — there are likely several. |
| **Cost to fix** | <1 session for `build_ict_htf_zones.py:468` alone; ~1 session for codebase-wide migration. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

---

### TD-019 — `hist_spot_bars_5m` pipeline stale since 2026-04-15; blocks forward research validation

| | |
|---|---|
| **Severity** | ~~S2~~ → CLOSED 2026-04-26 (Session 9) |
| **Discovered** | 2026-04-25 (Session 8 — Exp 17 backtest discovered last bar 2026-04-15 09:55) |
| **Component** | `hist_spot_bars_5m`, `hist_spot_bars_1m`, `build_spot_bars_mtf.py`, `capture_spot_1m.py`, `MERDIAN_Spot_1M` Task Scheduler task |
| **Symptom** | `hist_spot_bars_5m` last bar 2026-04-15 15:25 IST for both NIFTY and SENSEX. 10 calendar-day / 7 trading-day gap as of 2026-04-26. The 2026-04-24 NIFTY -393 / SENSEX -1,100 cascade event — the motivating event for Experiment 17 — was missing from the dataset, blocking forward overlay validation of any current research. |
| **Root cause** | (FINAL) `build_spot_bars_mtf.py` was uninstrumented (no `script_execution_log` writes ever) AND was never bound to Task Scheduler. It was a manual on-demand full-history rebuild. Last manual run was on or around 2026-04-15 EOD; nobody ran it again until Session 9. Capture pipeline (`capture_spot_1m.py`, `market_spot_snapshots`, `hist_spot_bars_1m`) was healthy throughout — the gap was purely downstream. The originally-hypothesised candidate causes ((a) Task Scheduler silent fail, (b) aggregator cron broken, (c) capture writer error) were all refuted by Q-A audit (no script in `script_execution_log` ever claimed `hist_spot_bars_5m` as a write target) and Q-B trading-day pattern (clean 150-row days through 04-15 with no irregular bulk-load shape). |
| **Workaround** | None needed post-fix. |
| **Proper fix** | Applied 2026-04-26 in three changes (all delivered same session, override of "no fix in diagnosis session" rule logged): (1) **Instrument** — patched `build_spot_bars_mtf.py` with ENH-71 `core.execution_log.ExecutionLog`. `expected_writes={"hist_spot_bars_5m": 1, "hist_spot_bars_15m": 1}` (minimum-1 row semantics catches "ran cleanly but wrote nothing"). Wraps `_run()` in try/except → `exit_with_reason('CRASH', ...)` for unhandled exceptions. Patch scripts: `fix_td019_instrument_build_spot_bars_mtf.py` (+1830 bytes) + `fix_td019_add_sys_import.py` (+11 bytes) — second was a follow-up because original file never imported `sys`. Both ast.parse() validated; backup at `build_spot_bars_mtf.py.pre_td019.bak`. (2) **Backfill** — manual `python build_spot_bars_mtf.py` run wrote 42,324 5m rows + 14,440 15m rows in 116s. Idempotent on `idx_hist_spot_5m_key` / `idx_hist_spot_15m_key` unique indexes. Verified via `script_execution_log`: `exit_reason=SUCCESS, contract_met=true, host=local, git_sha=1de239a`. (3) **Schedule** — registered `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task. Daily 16:00 IST Mon-Fri. Wrapper `run_spot_mtf_rollup_once.bat` matches existing MERDIAN task pattern (logs to `logs\task_output.log`). Smoke-tested same session: second SUCCESS row in `script_execution_log` 11:37 IST, `LastTaskResult=0`, `NextRunTime=2026-04-27 16:00`. |
| **Cost to fix** | Delivered in 1 session (Session 9, 2026-04-26). |
| **Blocked by** | — closed. |
| **Owner check-in** | CLOSED 2026-04-26 |

---

### TD-020 — LONG_GAMMA gate on 2026-04-24 strongly directional day — diagnosis required before ADR-002 ratification

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-25 (Session 8 — chart review of 2026-04-24 NIFTY -393 / SENSEX -1,100 intraday cascade) |
| **Component** | `build_market_state_snapshot_local.py` (gamma regime classification), gating logic in `build_trade_signal_local.py`, `options_flow_snapshots`, ADR-002 (in-flight) |
| **Symptom** | 2026-04-24 was the strongest directionally-bearish intraday day of the recent month: NIFTY -393 pts H-L (-1.6%), SENSEX -1,100 pts H-L (-1.4%). CURRENT.md "Live trading" block records BULL_FVG TIER2 signals on both indices BLOCKED by LONG_GAMMA gate. LONG_GAMMA classification implies dealer-driven mean reversion expected; the actual price action was strongly trending. Concern: if BEAR setups were also generated and also blocked, the gate left a high-conviction directional opportunity on the table; if BEAR setups were NOT generated despite the bearish breadth context, that is a separate signal-generation question. ADR-002 is currently being drafted around the assumption that the gate "did its job" by blocking trades — that framing is not yet evidence-supported for the strongest test case in recent history. |
| **Root cause** | Unknown. Three sub-hypotheses to discriminate: (a) **Regime classification was correct** but local positioning differed from net (Exp 23 territory — net GEX positive but local-near-spot GEX negative); gate fired correctly given the data it had, but the data was the wrong granularity for the regime question. (b) **Regime classification was wrong** — net GEX was actually negative all day but classifier returned LONG_GAMMA due to bug, stale source_ts, or threshold miscalibration. (c) **Regime classification was correct AND positioning was correct** — gamma did try to hedge, but other forces (breadth-driven momentum, news flow, FII positioning) dominated; gate is doing what it's designed to do, ADR-002 framing stands. |
| **Workaround** | None operationally — Phase 4A live trading continues. ADR-002 drafting paused until diagnosis completes. |
| **Proper fix** | Session 9 diagnosis (sub-hypotheses to discriminate): (1) Pull `options_flow_snapshots` for 2026-04-24 09:15-15:30 IST, both indices, every snapshot. Plot net GEX time series. Confirm regime classification matches the reported LONG_GAMMA state at each cycle. (2) Pull all signals generated 2026-04-24 from signal pipeline output — every direction (bull AND bear), every tier. Confirm whether BEAR signals were generated and what gate dispositioned them. (3) Compute local-vs-net gamma divergence (Exp 23 framework — strikes within ±0.5% of spot vs full chain). If they diverge significantly, this is the smoking gun for sub-hypothesis (a). (4) Check `source_ts` freshness on the gamma JSONB block during 2026-04-24 — Candidate D's concern. If the gamma block was reading stale data, that's sub-hypothesis (b). |
| **Cost to fix** | 1 session for diagnosis (read-only DB queries, no code change). Outcome determines whether Session 10 needs a code fix or ADR-002 can ratify as-is. |
| **Blocked by** | TD-019 partially — the spot bar gap on 2026-04-24 means we have GEX/options data for that day but not 5m spot bars. GEX time-series + tick data should be sufficient for the diagnosis without 5m spot bars. |
| **Owner check-in** | 2026-04-25 |


**Disposition (2026-04-25, Session 8 extended diagnosis):** All three originally-hypothesised sub-causes refuted or moot. Replaced by sub-hypothesis (d), undocumented at filing.

**Evidence:**
- `gamma_metrics` 2026-04-24 09:15-14:25 IST: 100 NIFTY rows + 123 SENSEX rows. `regime='LONG_GAMMA'` on every row. NIFTY `net_gex` range +5.3T to +18.6T. SENSEX `net_gex` range +185B to +2.2T (avg +1.5T). No regime flip, no sign change in net_gex. Classification was numerically correct.
- `signal_snapshots` 2026-04-24 full day: 245 rows (122 NIFTY, 123 SENSEX). `ict_pattern='NONE'` on all 245. `direction_bias='NEUTRAL'` on all 245. `action='DO_NOTHING'` on all 245. **Zero ICT setups generated all day, either direction, either index.**
- `hist_pattern_signals`, `signal_snapshots_shadow`, `signal_state_snapshots` 2026-04-24: zero rows in each. The 245 signal_snapshots rows are the complete 2026-04-24 signal record.

**Sub-hypothesis evaluation:**
- (a) Local-vs-net divergence: MOOT -- gate had no signals to filter, so its granularity is irrelevant for 2026-04-24.
- (b) Regime classification was wrong: REFUTED -- net_gex strongly positive throughout, LONG_GAMMA correctly assigned.
- (c) Regime correct AND gate worked as designed: PARTIALLY SUPPORTED but misleading -- regime call was correct, but the gate did not protect anything because it received no inputs to gate.
- **(d) NEW: ICT pattern detector silent on the strongest directional day of the recent month.** Cannot be diagnosed under TD-020 scope (which assumed gate-behaviour question). Filed as TD-022.

**Reconciliation with Session 7 CURRENT.md statement:** Session 7's CURRENT.md described "BULL_FVG TIER2 signals on both indices BLOCKED by LONG_GAMMA gate" on 2026-04-24. The signal_snapshots data does not support this -- no BULL_FVG signals existed. Either Session 7's CURRENT.md was incorrect (the more likely explanation; possibly described expected behaviour rather than observed), or BULL_FVG signals were generated and rejected upstream of signal_snapshots in a layer not yet identified. This warrants a brief check in Session 9 of any pre-`signal_snapshots` log/queue that might hold rejected setups; if no such layer exists, treat the Session 7 statement as erroneous and update DO_NOT_REOPEN.

**Impact on ADR-002:** Cannot ratify the "gate-protected posture" framing. The protection on 2026-04-24 was not the gate; it was the absence of signals. ADR-002 remains BLOCKED, now blocked on TD-022 (the real causal question), not TD-020 (which is closed).

**Status:** CLOSED -- diagnosed.
**Closed:** 2026-04-25
**Closed_by:** Session 8 extended diagnosis
**Successor:** TD-022 (ICT detector silent on cascade days)

---

### TD-021 -- Two undocumented operational conventions surfaced during Session 8

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-25 (Session 8) |
| **Component** | `.gitignore`, `merdian_pm.py`, `merdian_start.py` |
| **Symptom** | Two small things that bit operations during this session and will bite again unless documented. (a) `.gitignore` line 78 `/experiment_*.py` blocks default-add of new experiment scripts at repo root; convention is to force-add experiments worth keeping reproducible (precedent: `experiment_15.py`, `experiment_15b.py`, `experiment_17_bull_zone_break_cascade.py`). The convention is undocumented anywhere. Cost when missed: one extra commit and a confused user. (b) Adding a new managed process requires two parallel edits -- `merdian_pm.py` PROCESSES dict AND `merdian_start.py` hardcoded list at line 150. ENH-73 deployment hit this exactly: pm_stop killed the process correctly (saw it in PROCESSES) but pm_start didn't launch it (start.py's loop didn't include it). |
| **Root cause** | Both are missing-documentation issues, not bugs. (a) gitignore convention only became apparent when a new experiment was force-added; no comment in `.gitignore` flags it. (b) Schema duplication between `merdian_pm.PROCESSES` and `merdian_start.py`'s hardcoded loop. Originally fine when there were 3 processes; now there are 5 and the redundancy has cost. |
| **Workaround** | Operator memory + this register entry. |
| **Proper fix** | (a) Add a one-line comment above `.gitignore:78` reading something like `# experiment_*.py is default-ignored to keep scratch out of git. Force-add (git add -f) for experiments worth retaining. Precedent: experiment_15.py, experiment_15b.py, experiment_17_bull_zone_break_cascade.py.` (b) Refactor `merdian_start.py` line 150 to iterate over `pm.PROCESSES.keys()` directly, eliminating the second list. ~5 line change. After this, adding a process anywhere requires only one edit. |
| **Cost to fix** | <1 session -- bundle into a future OPS commit. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-25 |

---

### TD-022 -- ICT pattern detector generated zero setups on 2026-04-24 directional cascade day; live signal generation may be silently skipping cascade conditions

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-25 (Session 8 extended TD-020 diagnosis) |
| **Component** | ICT pattern detector (`build_ict_zones.py` / `build_ict_htf_zones.py` upstream; `build_trade_signal_local.py` integration), `signal_snapshots`, `hist_pattern_signals` |
| **Symptom** | 2026-04-24 was the strongest bearish intraday day of the recent month (NIFTY -1.6%, SENSEX -1.4%, NIFTY broke W BULL_FVG 24,074-24,241 by 09:30 IST and cascaded -393 pts intraday; SENSEX similar at 77,636 cascading -1,100 pts). The chart-visible W BULL_FVG zones existed in `ict_htf_zones` (confirmed by 2026-04-25 morning chart screenshots labelled "W BULL_FVG 24,074 PRICE INSIDE [Apr 17]"). Despite this, `signal_snapshots` for 2026-04-24 contains 245 rows, ALL with `ict_pattern='NONE'`, `direction_bias='NEUTRAL'`, `action='DO_NOTHING'`. The live ICT detector did not register the zone interaction or the break. Phase 4A's apparent risk-aversion on this day was not produced by the gate (LONG_GAMMA gate on 2026-04-24 received zero signals to filter -- see TD-020 disposition); it was produced by detector silence. |
| **Root cause** | Unknown. Three plausible classes, requires investigation: (1) **Lookback/window mismatch** -- detector may require zone status that `ict_htf_zones` doesn't yet have; e.g. detector reads `status='ACTIVE'` but the W BULL_FVG was already `BREACHED` by mid-morning, removing it from candidates. (2) **Detector input gap** -- TD-019 stale `hist_spot_bars_5m` may already have been affecting live detection on 2026-04-24 (last bar 2026-04-15 means detector reading from a 9-day-stale price feed by 2026-04-24, possibly outputting NONE because no fresh candles to anchor patterns to). (3) **Pattern type filter** -- detector may be configured to detect only certain ICT patterns (e.g. `BREAK_OF_STRUCTURE`, `LIQUIDITY_SWEEP`) and the cascade pattern of "open inside zone, break below, close below" doesn't map to any registered pattern. |
| **Workaround** | None. Phase 4A is currently relying on detector silence as if it were intentional risk control. Any apparent system success on directional days is unverified -- could be skill, could be silence. |
| **Proper fix** | Session 9 (NEW Candidate A, replacing TD-020 LONG_GAMMA diagnosis): (1) Read `build_trade_signal_local.py` and the ICT detector entry-point. Document what input each pattern type requires from `ict_htf_zones` and `hist_spot_bars_5m`. (2) Replay 2026-04-24 against the detector with current data: pull a single 2026-04-24 bar from Kite REST (one-off, doesn't fix TD-019), feed it to the detector against the ict_htf_zones at that moment in time (`created_at <= 2026-04-24 09:30:00 IST`), see what the detector outputs. (3) If detector outputs NONE for a clear cascade input, that's a pattern-coverage bug -- file ENH. (4) If detector outputs a setup but signal_snapshots shows NONE, that's an integration bug between detector and writer -- file ENH. (5) If detector errors or silently fails on missing 5m bars, that's TD-019's fault -- closure of TD-019 closes this. |
| **Cost to fix** | 1-2 sessions for diagnosis. Fix scope unknown until diagnosis completes. |
| **Blocked by** | Partially TD-019 -- if root cause is TD-019, then TD-019's repair is also TD-022's repair. Diagnosis itself can proceed before TD-019 fix. |
| **Owner check-in** | 2026-04-26 |
| **Blocks** | (was: ADR-002 ratification) -- now superseded by TD-020 reframing |

**Disposition (2026-04-26, Session 9 deep-dive):** TD-022's filed framing
("ICT pattern detector silent on cascade day") was structurally wrong. The
detector ran 404 cycles on 2026-04-24 (per script_execution_log), wrote 3
ict_zones rows for the day (1 NIFTY + 2 SENSEX BULL_FVG TIER2), and produced
output as designed. The "silence" observed in signal_snapshots is downstream
of `enrich_signal_with_ict()` in build_trade_signal_local.py, which filters
zones by direction matching `action`: `direction = +1 if action=="BUY_CE" else -1`.
With `action='DO_NOTHING'` (set upstream by the LONG_GAMMA gate firing on
every cycle), the directional filter matches nothing, returns empty,
ict_pattern is set to NONE. ICT is an innocent passenger; the gate is the
driver.

**Real cause (re-attributed to TD-020 reframing):** LONG_GAMMA gate fired
correctly as designed on every cycle, setting `direction_bias='NEUTRAL'`,
`action='DO_NOTHING'`, `trade_allowed=False`. Session 8 disposition concluded
"gate had no signals to filter; ICT detector silent" — that was reading the
gate's OUTPUT (NEUTRAL/DO_NOTHING) as if it were the gate's INPUT. See TD-020
(reopened/closed-correctly).

**Status:** CLOSED -- duplicate of TD-020 (correctly reframed).
**Closed:** 2026-04-26 (Session 9)
**Closed by:** TD-020 reframing + ENH-37 source read

---

### TD-023 — Uninstrumented data producers (anti-pattern, audit pending)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-26 (Session 9 — surfaced during TD-019 closure) |
| **Component** | All scripts that write to data tables; `script_execution_log` audit coverage |
| **Symptom** | The TD-019 silence was hidden for 7 trading days because `build_spot_bars_mtf.py` never wrote a row to `script_execution_log`. Any producer not wired into ENH-71 contract logging can fail invisibly until a downstream consumer notices. A Q-A audit during TD-019 (searching `script_execution_log` for `actual_writes` / `expected_writes` referencing the stale table) returned zero rows — proving the table had no instrumented producer. By extension, every other public data table needs the same audit; producers that fail the same query are the same kind of trap waiting to spring. |
| **Root cause** | ENH-71 propagation was scoped to a known set of scripts (ENH-72 closed 9, TD-014 added the 10th). Producers outside that explicit set were never required to instrument. `build_spot_bars_mtf.py` was outside the set because it was treated as a "manual rebuild tool" rather than a production writer. Same risk applies to any other manual / occasional / one-off writer that targets a production table. |
| **Workaround** | None active. Operator memory + this register entry. |
| **Proper fix** | Audit pass: (1) `select tablename from pg_tables where schemaname='public'` to list all public data tables. (2) For each, run the Q-A pattern: `WHERE actual_writes::text LIKE '%<table>%' OR expected_writes::text LIKE '%<table>%'` against `script_execution_log`. Tables with zero hits = uninstrumented producer somewhere. (3) `Get-ChildItem -Recurse -Include *.py \| Select-String -Pattern "<table>" -List` to locate the writer(s). (4) Patch each using the `build_spot_bars_mtf.py` template (~10 lines per script). File one sub-TD per uninstrumented producer found; close as patched. |
| **Cost to fix** | 1-2 sessions for the audit. Patching pace depends on producer count. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-024 — 19:01 IST writes to `market_spot_snapshots` (post-close anomaly, two cases)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — Q3 freshness query during TD-019 diagnosis) |
| **Component** | `market_spot_snapshots`, `hist_spot_bars_5m`, possibly `capture_spot_1m.py`, possibly ENH-73 heartbeat |
| **Symptom** | (a) 2026-04-24 `market_spot_snapshots` and `hist_spot_bars_1m` show writes at 19:01:02 IST for both NIFTY and SENSEX. `capture_spot_1m.py` is documented as 09:14-15:31 IST per `MERDIAN_Spot_1M` Task Scheduler task. A 19:01 write is ~3.5 hours after schedule end. `script_execution_log` shows `capture_spot_1m.py` last_run 2026-04-24 19:01:01 IST — the script ran, it just ran outside its window. (b) 2026-04-13 (Mon) `hist_spot_bars_5m` shows 152 bars (vs typical 150) with `last_bar` at 16:10 IST. Two extra post-close 5m bars. Different table, different mechanism, but same family (post-close write). |
| **Root cause** | Unknown. Candidate causes: (1) ENH-73 Telegram alerts + 10-min heartbeat deployed Session 8 — fits 04-24 timing but not 04-13 (12 days earlier, before ENH-73). (2) Undocumented EOD job not in Task Scheduler inventory. (3) Manual run not recorded in operator memory. (4) Clock or tz handling issue at the wrapping shell layer. |
| **Workaround** | Not a data-correctness issue; bars and snapshots are well-formed. No active mitigation needed. |
| **Proper fix** | Query `script_execution_log` for `capture_spot_1m.py` rows where `started_at` falls outside the 09:14-15:31 IST window. Identify host/git_sha pattern. If ENH-73 heartbeat: document as expected behaviour, update `merdian_reference.json` cadence string. If different invoker: trace via Task Scheduler history or `.bat` log files for the same date. |
| **Cost to fix** | <1 session for diagnosis. Resolution scope depends on cause. |
| **Blocked by** | nothing — investigation can run any time. Bundle with TD-023 audit if convenient. |
| **Owner check-in** | 2026-04-26 |

---

### TD-025 — `build_spot_bars_mtf.py` re-aggregates full history every run (compute waste)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — observed during TD-019 patch design) |
| **Component** | `build_spot_bars_mtf.py` |
| **Symptom** | Each invocation reloads ALL 1m bars (~210k rows across NIFTY+SENSEX = ~282 trading days × 75 bars × 2 instruments) and re-aggregates the entire history into 5m + 15m, even when only the last day's worth of new data needs producing. At 116s/run × 252 trading days/year × 2 outputs = ~16 hours/year of wasted compute. Idempotent upserts on the unique index mean it's not incorrect, just wasteful. |
| **Root cause** | Original design as a manual on-demand full-history rebuild tool (TD-019 closure context). Was never re-architected after being scheduled as a daily task. |
| **Workaround** | None needed — daily 116s runtime is comfortably within Task Scheduler's 30-min `ExecutionTimeLimit`. |
| **Proper fix** | Parameterise on a date window. Default to "since `MAX(bar_ts)` in `hist_spot_bars_5m`" or "today's `trade_date` only". Full rebuild remains available via `--full` flag for backfills (so the TD-019 backfill recipe is preserved). Reduces typical run from ~116s to <10s. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing. Defer until other priorities clear. |
| **Owner check-in** | 2026-04-26 |

---

### TD-026 — PowerShell scripts must be ASCII-only (encoding pitfall)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — `register_spot_mtf_rollup_task.ps1` failed parse due to em-dashes) |
| **Component** | All `.ps1` and `.bat` files in repo |
| **Symptom** | Windows PowerShell 5.x defaults to ANSI/Windows-1252 when reading a `.ps1` without a BOM. Non-ASCII characters (em-dashes `—`, box-drawing `─`, smart quotes, etc.) get mangled and produce misleading parser errors that point at lines BEFORE the actual offending byte. Exact failure mode encountered Session 9: em-dash on line 52 → parser reported "Missing closing '}' in statement block" at line 51. Wasted one round trip. |
| **Root cause** | Windows PowerShell 5.x text-handling default, not a script bug. Same family as TD-010 (`Get-Content -Encoding UTF8` requirement). PowerShell 7+ defaults to UTF-8 and would not have hit this. |
| **Workaround** | Re-emit script as pure ASCII: replace `—` with `--`, `─` with `-`, smart quotes with straight quotes, box-drawing with `\|`/`+`/`-`. |
| **Proper fix** | Convention, not a code change: all `.ps1` and `.bat` in this repo are ASCII-only. No em-dashes in comments, no box-drawing in banners. Add a one-line note to CLAUDE.md alongside TD-010 / `Get-Content -Encoding UTF8` so the rule is visible at session start. |
| **Cost to fix** | Convention-only; no fix to apply. Closes when documented in CLAUDE.md. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-027 — `merdian_pipeline_alert_daemon` scope drifted from name

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — Item 4 of TD-022 follow-up parking lot) |
| **Component** | `merdian_pipeline_alert_daemon.py`, ENH-73 + ENH-46-A |
| **Symptom** | The daemon's name and ENH-73 description suggest broad "pipeline alerting." Initial implementation alerted only on infrastructure failures from `script_execution_log`. ENH-46-A extended it to also alert on tradable signals (signal_snapshots). The file now does two distinct jobs but is named for one. |
| **Root cause** | ENH-73 was scoped narrowly during Session 8 deployment (infrastructure visibility); name and description used the broader "pipeline" term that implied wider scope. Documentation drift between intent and implementation, not a bug. ENH-46-A absorbed the gap rather than splitting into a new daemon. |
| **Workaround** | None needed; the daemon does what it does correctly post-ENH-46-A. This TD is about clarity going forward. |
| **Proper fix** | Two paths, mutually exclusive: (a) **Rename narrowly**: rename to `merdian_infra_alert_daemon.py`, keep ENH-73 narrow, treat ENH-46-A as a separate daemon `merdian_signal_alert_daemon.py`. Cleaner separation of concerns, requires file rename + Task Scheduler / pm.PROCESSES + state.json migration. (b) **Embrace the broad name**: keep the file name; document the multi-mode behaviour in the daemon docstring and ENH-73 description; accept a kitchen-sink. Recommendation: (b) for now, revisit if scope balloons further (e.g. third alerting domain added later). |
| **Cost to fix** | <1 session. Not urgent. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-028 — `merdian_pm.py` silently fails on unknown process name

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-26 (Session 9 — ENH-46-A daemon restart) |
| **Component** | `merdian_pm.py`, `start()` and `status()` functions |
| **Symptom** | Calling `python merdian_pm.py stop merdian_pipeline_alert_daemon` (full script filename instead of registry key `pipeline_alert`) returned no output and took no action. Calling `python merdian_pm.py status` also returned no output (whether the registry was empty or the function silently no-op'd is unclear). Net effect: operator believed the daemon had been stopped/restarted when in fact it had not, leading to ~10 minutes of confusion (PID 24968 still running with old code while operator thought new code was loaded). The pm tool's `start()` returns `False, f"Unknown: {name}"` on miss — but only the print path was checked; the actual return path was not surfaced, so the user saw nothing. |
| **Root cause** | Two issues entangled: (1) `start()` and `stop()` print the result tuple via wrappers in some code paths but not others — when called via `python merdian_pm.py <cmd> <name>` from CLI, the bool/msg tuple is returned but not echoed. (2) `status` likely outputs only when there are processes to report, suppressing the "no processes registered" case entirely. Either should fail loudly. |
| **Workaround** | Use the actual registry keys (`pipeline_alert`, `health_monitor`, `signal_dashboard`, `supervisor`, `exit_monitor`) not the script filenames. For start/restart, fall back to direct `Start-Process` PowerShell launch (used in Session 9 to relaunch the alert daemon after `merdian_pm.py start pipeline_alert` produced no output). |
| **Proper fix** | Three changes: (a) print the `(ok, msg)` tuple unconditionally at the top of every CLI handler. (b) emit `[OK] No matching processes` (or similar) from `status` when registry is empty. (c) consider raising on unknown process name (rather than `return False, "Unknown: ..."`) so silent-fail can't happen. <1 session. Bundle with TD-021 fix on the `merdian_start.py` dual-list issue (same file family, related cleanup). |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-029 — `hist_spot_bars_1m` and `hist_spot_bars_5m` pre-04-07 era TZ-stamping bug

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-26 (Session 10 mid-experiment, hist_spot_bars_5m TZ diagnostic) |
| **Component** | `hist_spot_bars_1m`, `hist_spot_bars_5m` (rows with `trade_date < 2026-04-07`) |
| **Symptom** | Pre-04-07 rows have IST clock-time stored under UTC tzinfo marker. Approximately 2,820 rows in 5m table affected. 1m table also affected (Q-1M-TZ-DIAGNOSTIC confirmed identical era boundary). |
| **Root cause** | One-off ingest event 2026-04-18 04:43 UTC misclassified the timezone metadata for previously-ingested historical bars. Post-04-07 rows are correctly UTC-stamped (current writer behaviour is correct). |
| **Workaround** | Era-aware CASE on `trade_date` in queries: pre-04-07 → strip-tzinfo-and-reattach-IST; post-04-07 → standard UTC→IST conversion. Used successfully in Exp 29 v2, Exp 31, Exp 32, Exp 15 re-run. Code pattern documented at `experiment_29_1h_threshold_sweep_v2.py:canonicalize_ts_to_ist()`. |
| **Proper fix** | Two options: (a) **Repair**: `UPDATE hist_spot_bars_1m / 5m SET bar_ts = bar_ts - INTERVAL '5 hours 30 minutes' WHERE trade_date < '2026-04-07' AND created_at BETWEEN '2026-04-18 04:43' AND '2026-04-18 04:45';`. Cleaner long-term, but irreversible if scope is wrong. (b) **Document**: write era boundary into `merdian_reference.json`, add CASE-on-trade_date helper to query helpers. Safer. Recommendation: Path A (repair) once scope confirmed via full row-count audit. |
| **Cost to fix** | <1 session if Path A; ~2 sessions if Path B (helper + audit + propagation). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-030 — `build_ict_htf_zones.py` doesn't re-evaluate breach on existing active zones

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 pre-open ops) |
| **Component** | `build_ict_htf_zones.py` (all timeframes; affects `ict_htf_zones` table integrity) |
| **Symptom** | Two W BULL_FVG zones (NIFTY 24,074-24,241, SENSEX 77,636-78,203) formed 2026-04-20 remained `status='ACTIVE'` after Friday 04-24's selloff broke through them. Zones with `valid_to >= today` AND `status='ACTIVE'` AND price already below `zone_low` (BULL) or above `zone_high` (BEAR) constitute zombie zones that mislead MTF context lookups. |
| **Root cause** | Script applies breach filter at *write time* during detection of new candidate zones — eliminates already-violated candidates before INSERT. Does NOT re-evaluate existing active zones for breach when subsequent price action breaks them. The "Expired old zones before <date>" log line is date-based expiry only, not breach-based invalidation. |
| **Workaround** | Manual SQL UPDATE per session when zones are visibly stale. Zombie-zone detection query: compute current spot vs zone boundaries with directional CASE, mark BULL_BREACHED if spot < zone_low / BEAR_BREACHED if spot > zone_high. Then UPDATE matching IDs to `status='BREACHED', valid_to=CURRENT_DATE`. Used 2026-04-27 pre-open with success (cleared 2 zombie BULL_FVG zones). |
| **Proper fix** | Add a re-evaluation pass at the start of every `build_ict_htf_zones.py` run: for each existing `status='ACTIVE'` zone, compute its current breach status against the most recent bar's close. If breached, UPDATE to BREACHED before detecting new candidates. Incremental cost minimal — one extra SELECT + conditional UPDATE per active zone, runs once per script invocation. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-031 — D BEAR_OB / D BEAR_FVG detection underactive in `build_ict_htf_zones.py`

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 pre-open ops, post-rebuild zone audit) |
| **Component** | `build_ict_htf_zones.py` daily zone detection (D BEAR_OB and D BEAR_FVG specifically) |
| **Symptom** | Q-D-BEAR-COVERAGE returned: D BEAR_OB total ever written = 2 (last 2026-04-11). D BEAR_FVG total ever written = 0. D BULL_OB = 4 lifetime, D BULL_FVG = 0. Despite multiple visibly bearish daily candles in the past two weeks (NIFTY -1.87% week ending 04-24, SENSEX -1.29%, both with strong red 1D bars 04-23/04-24), the script wrote zero new D BEAR structures. |
| **Root cause** | **(Session 15 update)** Original hypotheses partly confirmed via manual replay during Session 15 code review. Two distinct issues: (a) D-FVG detection was entirely missing from `detect_daily_zones()` for both directions — closed Session 15 as part of TD-048 (BEAR_FVG defect) via S1.b patch; D BEAR_FVG count post-backfill = 79 rows. (b) D-OB detector uses a non-standard ICT definition (uses move bar K+1 itself as OB instead of opposing prior K) — this is the root cause of D BEAR_OB underactivity. Standard ICT definition would generate ~6 D BEAR_OB candidates per Session 15 manual replay vs 1-2 actual. **Promoted to TD-049** for definitional fix. |
| **Workaround** | None for D-OB underactivity. D BULL_FVG / D BEAR_FVG now populated post-Session 15 patches — those parts are no longer underactive. |
| **Proper fix** | D-FVG portion CLOSED via TD-048 fix Session 15. D-OB portion remaining — see TD-049. |
| **Cost to fix** | D-FVG portion done. D-OB portion: <1 session if retroactive backfill, 1 session if version-boundary documentation (decision pending — see TD-049). |
| **Blocked by** | TD-049 (carries the D-OB definitional fix forward) |
| **Owner check-in** | 2026-05-02 (Session 15 reframing — D-FVG closed, D-OB remains open as TD-049) |

---

### TD-032 — Dashboard execution panel ignores `direction_bias` / `action`, displays trades inconsistent with DB ground truth

| | |
|---|---|
| **Severity** | S2 (becomes S1 the moment ENH-46-C ships and trade_allowed=true rows appear) |
| **Discovered** | 2026-04-27 (Session 10 live, post-F0 unmasking) |
| **Component** | `merdian_signal_dashboard.py` execution panel rendering pipeline |
| **Symptom** | Multiple observed inconsistencies between dashboard execution panel and `signal_snapshots` ground truth, observed live during 2026-04-27 trading session: (a) At 11:21 IST, NIFTY signal_snapshots row had `direction_bias=BEARISH, action=BUY_PE, atm_strike=24050, spot=24068.8`. Dashboard rendered: "Strike 24,100 CE / premium ₹85" — wrong instrument (CE not PE), wrong strike (24,100 not 24,050). (b) At 11:38 IST, dashboard rendered "▲ BUY CE / Strike 24,000 CE" while DB had `direction_bias=BEARISH, action=BUY_PE, atm_strike=24050` — dashboard showed BULLISH instrument while DB was BEARISH. (c) At 12:10 IST, dashboard correctly showed ▼ SELL/BUY PE / Strike 24,050 CE — strike-number now matched but instrument label still CE despite BUY_PE action. Pattern is non-deterministic across cycles. |
| **Root cause (provisional)** | Pattern-driven hardcoding ruled out (dashboard CAN render PE on BULL_FVG patterns at other times). Most likely candidates: (a) race condition between cycle's signal_snapshots write and dashboard's multi-field render, (b) dashboard reads some fields from a different/stale source while reading other fields fresh, (c) in-memory cached state in dashboard process clobbering periodic reads. The DB is consistently correct; the dashboard is the unreliable layer. Pre-F0 the inconsistency was masked because direction_bias was clobbered to NEUTRAL on every LONG_GAMMA cycle (the F0 regression). F0's unclobber unmasked the dashboard rendering bug that has presumably existed for weeks. |
| **Workaround** | Always validate against `signal_snapshots` directly before placing any trade. Dashboard is unreliable for direction/strike/instrument-type rendering. `SELECT direction_bias, action, atm_strike, spot FROM signal_snapshots WHERE symbol=$1 ORDER BY ts DESC LIMIT 1`. |
| **Proper fix** | Source code audit of `merdian_signal_dashboard.py` rendering pipeline. Identify which fields come from where, ensure single-source-of-truth (DB row at render time) for the action/strike/instrument triple. Add a "DB-vs-display consistency check" log line at every render: if dashboard-computed strike/instrument differs from DB row, log warning. |
| **Cost to fix** | 1-2 sessions for diagnosis + fix. |
| **Blocked by** | nothing — investigation can run any time |
| **BLOCKER FOR** | **ENH-46-C ship.** Conditional gate lift cannot promote any signal to live `trade_allowed=true` while operator cannot trust dashboard to show correct trade direction. Without TD-032 fixed, an operator looking at the dashboard could place a CE trade when the system intended PE (or vice-versa), causing a 100%-direction-wrong loss. |
| **Owner check-in** | 2026-04-27 |

---

### TD-033 — Dashboard "SELL / BUY PE" label conflation

| | |
|---|---|
| **Severity** | S3 (cosmetic/confusing but does not change actual order routing) |
| **Discovered** | 2026-04-27 (Session 10 live) |
| **Component** | `merdian_signal_dashboard.py` direction label rendering |
| **Symptom** | Dashboard direction label concatenates direction-bias short-form ("SELL" or "BUY") with action ("BUY_CE" or "BUY_PE"), producing strings like "▼ SELL / BUY PE" or "▲ BUY / BUY CE". Two different concepts (short-form bias label vs concrete trade action) shown as one combined label. No real OMS does this. Confusing for operators, especially under stress. |
| **Root cause** | Dashboard rendering layer building label string from two fields without disambiguating them. Likely an early-stage UI prototype that never got cleaned up. |
| **Workaround** | None needed; just confusing. Read the dashboard label as: short-form before the slash = bias, after slash = trade action. The action is what would be placed. |
| **Proper fix** | Display action (BUY_CE / BUY_PE) prominently as the trade. Display direction_bias separately as a regime tag if at all. Or remove the bias label entirely — `gamma_regime` and `wcb_regime` already render in the gate footer. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-034 — `hist_atm_option_bars_5m` severely undersampled on expiry days (dte=0)

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 extension, while running Experiment 33) |
| **Component** | `hist_atm_option_bars_5m` ingestion pipeline + the resulting backtest data quality |
| **Symptom** | Only 11 NIFTY expiry days (dte=0) and 22 SENSEX expiry days observed in 2025-04-01 to 2026-03-30 window. Expected ~50 per symbol (one per weekly expiry day, including monthlies). NIFTY coverage rate: 22%. SENSEX coverage rate: 44%. The `hist_atm_option_bars_5m` table has reasonable coverage on non-expiry days (247 distinct dates) but loses most expiry-day rows. |
| **Impact** | Any backtest research on expiry-day behaviour has 22-44% sample coverage. Affects retrospective analysis of: Exp 31 (expiry-day options replay), Exp 33 (inside-bar before expiry), future ENH-46-C shadow analysis on expiry days, any expiry-day-conditional ICT filter design. The Experiment 33 result of "71% next-day continuation" is based on N=14 instead of the ~50 inside-bar-before-expiry candidates a full coverage would have surfaced. |
| **Root cause (hypotheses)** | (a) Ingestion script has an expiry-day exclusion filter (intentional or accidental), (b) ATM-strike-only filter drops rows when ATM changes intraday on volatile expiries (intraday strike migration), (c) ingestion failures on expiry days due to API rate limits or option chain volatility, (d) a `dte > 0` filter somewhere upstream. None confirmed. |
| **Workaround** | Use spot data (`hist_spot_bars_1m`) for expiry-day characterisation where possible — full coverage. Use option_chain_snapshots' 14-day window for fill-in. For backtests requiring multi-month expiry-day option data, accept the smaller sample. |
| **Proper fix** | Trace ingestion logic. Identify why dte=0 rows are missing. If filter bug → patch + backfill. If API/timing issue → add retry logic + flag missing days. Backfill historical expiry days from upstream (Dhan/Zerodha) where API allows. |
| **Cost to fix** | ~2 sessions diagnostic, ~1-2 sessions backfill if data sources available. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-035 — `signal_snapshots.wcb_regime` is NULL on all rows but dashboard shows "BULLISH"

| | |
|---|---|
| **Severity** | S3 (cosmetic on dashboard, may indicate routing inconsistency) |
| **Discovered** | 2026-04-27 (Session 10 live, during DB-vs-dashboard verification) |
| **Component** | `signal_snapshots` table + dashboard wcb_regime rendering |
| **Symptom** | `SELECT wcb_regime FROM signal_snapshots WHERE ts >= CURRENT_DATE LIMIT 10` returns null on every row. Dashboard footer shows "LONG_GAMMA  BULLISH" — the BULLISH portion is wcb_regime per the rendering logic, but DB has NULL. Dashboard must be reading wcb_regime from a different source (likely `wcb_alignment` field or a separate `market_state_snapshots` table) but the contract is undocumented. |
| **Impact** | Two layers may be making decisions on different wcb_regime sources without explicit acknowledgment. ENH-35 gate logic that depends on wcb_regime classification could be operating on `wcb_alignment` (related but not identical) or on `market_state_snapshots.wcb_regime` (separate table) — unverified which. Architecturally suspect. |
| **Workaround** | Treat dashboard's wcb display as informational only, not as the gate's wcb input. For verification, query `market_state_snapshots` directly, or read `signal_snapshots.wcb_alignment`. |
| **Proper fix** | Source-trace `build_trade_signal_local.py` and `merdian_signal_dashboard.py` to find where wcb_regime is read for each. Either: (a) populate `signal_snapshots.wcb_regime` correctly on every cycle (if it should always be set), or (b) drop the column from signal_snapshots if it's redundant with wcb_alignment / market_state_snapshots, or (c) document explicitly that the column is intentionally null and the canonical source is elsewhere. |
| **Cost to fix** | <1 session — diagnostic + decide which path. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-036 — `signal_snapshots.confidence_score` flat-lines for hours

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-27 (Session 10 live, during signal_snapshots monitoring) |
| **Component** | `build_trade_signal_local.py` confidence scoring logic |
| **Symptom** | `confidence_score` for NIFTY = 20.0 across 10 cycles spanning 11:18 to 12:10 IST. SENSEX = 32.0 across same window. Earlier 09:31-09:41 IST window also NIFTY=20, SENSEX=32. Score has not moved for at least 1 hour, possibly the entire session. |
| **Impact** | Confidence score should respond to changing market state. Either: (a) score is computed only at coarser granularity (e.g., once per session) and held constant — design choice but not documented, (b) score is computed per cycle but inputs aren't moving enough to change it — possible but unlikely over 90+ minutes of price action, (c) bug pinning score to a constant. Without diagnostic, hard to know which. |
| **Workaround** | Don't use confidence_score for any trade decision. Treat it as deprecated until validated. |
| **Proper fix** | Source-trace confidence scoring logic. Decide whether it should be dynamic or static. If dynamic → fix update cadence. If static → rename to something like `static_confidence_baseline` to clarify. |
| **Cost to fix** | <1 session diagnostic. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-037 — Schema column-name inconsistency across timestamp-bearing tables

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-27 (Session 10 extension, surfaced by repeated SQL errors during Exp 33 development) |
| **Component** | Database schema across multiple tables |
| **Symptom** | Three different timestamp column conventions across canonical tables: `signal_snapshots` uses `ts`, `hist_spot_bars_1m` uses `bar_ts`, `ict_zones` uses both `detected_at_ts` and `session_bar_ts`, `option_chain_snapshots` uses `ts`, `market_spot_snapshots` uses `ts`, `hist_atm_option_bars_5m` uses `bar_ts`, `script_execution_log` uses `started_at` and `finished_at`. Ad-hoc queries error out frequently with "column ts does not exist" or similar; consumes time iterating through column-discovery queries. |
| **Impact** | Friction on ad-hoc queries during live diagnostics. Real cost: during Session 10 extension, 4 query iterations were needed before getting to working SQL for `hist_spot_bars_1m` — adds up to ~10 minutes of iteration time when troubleshooting under market hours. Also makes Claude/AI sessions less efficient because column names can't be predicted from one table to another. |
| **Workaround** | Always run column-discovery query first when querying a new table: `SELECT column_name FROM information_schema.columns WHERE table_name='X'`. Document common patterns in a Session 11+ schema reference card. |
| **Proper fix** | Aspirational schema-hygiene refactor — standardise on `bar_ts` for time-series bar data, `ts` for snapshot/event data, `created_at`/`updated_at` as sidecars. Would require migrations and code refactors across all readers. Not worth scheduling unless an unrelated migration is happening. |
| **Cost to fix** | ~3-5 sessions for schema migration + reader updates. Cost-benefit not favourable for now. |
| **Blocked by** | nothing — but not a priority |
| **Owner check-in** | 2026-04-27 |

---

### TD-038 — `hist_spot_bars_5m` has no `is_pre_market` column (schema assumption mismatch)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-28 (Session 11 Exp 34 bug B1) |
| **Component** | `hist_spot_bars_5m`, any research script querying it |
| **Symptom** | Scripts that filter `.eq("is_pre_market", False)` raise `APIError 42703: column does not exist`. First hit: Exp 34 initial run returned 0 events because the Supabase query failed silently. |
| **Root cause** | The column `is_pre_market` does not exist in `hist_spot_bars_5m`. Pre-market exclusion must be done by filtering `bar_ts` to session hours (09:15–15:30 IST). |
| **Workaround** | Filter by time: `WHERE EXTRACT(HOUR FROM bar_ts AT TIME ZONE 'Asia/Kolkata') * 60 + EXTRACT(MINUTE ...) BETWEEN 555 AND 930`. In Python (with TD-029 workaround applied): filter post-fetch using `9*60+15 <= bar_minutes(dt) <= 15*60+30`. |
| **Proper fix** | Either (a) add `is_pre_market` column as a computed boolean on insert, or (b) document the absence in `merdian_reference.json` tables entry and ensure all scripts use time-based filtering. Option b is lighter. |
| **Cost to fix** | <0.5 sessions for option b. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-28 |

---

### TD-039 — `hist_pattern_signals.ret_30m` stored as percentage points, not decimal fraction

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-28 (Session 11 Exp 41 — ret_30m inflated by 100x, corrected in Exp 41B) |
| **Component** | `hist_pattern_signals` table, `ret_30m` and `ret_60m` columns |
| **Symptom** | Any script that uses `ret_30m` as a decimal fraction (multiplying directly by spot price) gets numbers 100x too large. Exp 41 showed SENSEX E4 EV = −11,649 pts per trade, clearly impossible. |
| **Root cause** | `ret_30m` is populated as a percentage (e.g., 0.1351 = 0.1351% move, not 13.51%). The schema comment or docs do not make this explicit. |
| **Workaround** | Divide `ret_30m` by 100 before using as a decimal fraction. Sign convention: BEAR_OB wins when `ret_30m < 0` (spot fell). BULL_OB wins when `ret_30m > 0`. Codified in CLAUDE.md Rule 14. |
| **Proper fix** | Either (a) update all writers to store as decimal fraction (breaking change to any existing consumers), or (b) rename column to `ret_30m_pct` to make the unit explicit in the schema. Option b is safer. Also add column comment in Supabase: `COMMENT ON COLUMN hist_pattern_signals.ret_30m IS 'Spot return in percentage points (divide by 100 for fraction)'`. |
| **Cost to fix** | <0.5 sessions for option b + comment. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-28 |

---

> **Session 14 TDs (TD-040 through TD-047) noted in `session_log.md` line 1 are not yet filed in this register.** Historical gap — their content lives in the Session 14 one-liner. Backfill in a future operational session is OPEN. Session 15 TDs below resume at TD-048.

---

### TD-048 — *(see Resolved section — CLOSED Session 15: BEAR_FVG defect across detector pipeline)*

The numeric ID TD-048 is reserved for the BEAR_FVG defect closed in Session 15. Full entry lives in **Resolved (audit trail)** below since it was opened and closed within the same session. Cross-referenced here for ID continuity.

---

### TD-049 — D-OB detector uses non-standard ICT definition (D timeframe only)

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced during code review of `build_ict_htf_zones_historical.py` for the BEAR_FVG defect; consolidates "TD-S2.a" working name from Session 15 closeout) |
| **Component** | `detect_daily_zones()` in both `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` |
| **Symptom** | D-OB detector marks the prior bar K+1 (the move bar itself) as the OB. Standard ICT defines an OB as the LAST opposing-color candle BEFORE the displacement (i.e., bar K, not K+1). W-OB in `detect_weekly_zones()` uses the standard ICT definition; D-OB does not. Inconsistent across timeframes within the same script. |
| **Root cause** | Detector logic in `detect_daily_zones()` checks `prior_move >= OB_MIN_MOVE_PCT` and writes the prior bar itself as the OB zone. Should look back one further bar to find the last opposing-color candle. Carried forward from initial Phase-1 implementation. |
| **Workaround** | None. The system uses the current (non-standard) D-OB definition. Symptom: D BEAR_OB candidates fire ~6 expected per Session 15 manual replay vs 1-2 actual = false negatives at standard ICT criterion. |
| **Proper fix** | Change D-OB detector to standard ICT definition (find K-1 = last opposing-color bar before K = displacement bar). Decision required: (a) re-run full historical backfill on `hist_ict_htf_zones` after fix (invalidates 118 BULL + 135 BEAR D-OB rows from Session 15 backfill), or (b) ship for new detections only and document version boundary. Recommendation: option (a) since backfill cost is ~5 minutes (proven during Session 15). |
| **Cost to fix** | <1 session for code + retroactive backfill. |
| **Blocked by** | nothing — investigation can run any time. Operator decision needed on retroactivity. |
| **Owner check-in** | 2026-05-02 |

---

### TD-050 — D-zone non-FVG validity = 1 day (single-session expiry)

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced during ADR-003 Phase 1 v2 investigation when "0 D zones in 10-day lookback" pointed at validity bug; consolidates "TD-S2.b") |
| **Component** | `detect_daily_zones()` in both `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` (D-OB and D PDH/PDL specifically — D BULL_FVG / D BEAR_FVG were given 5-day validity in the Session 15 S1.b patch via `D_FVG_VALID_DAYS=5`) |
| **Symptom** | D-zone non-FVG validity = exactly 1 day (`valid_from = valid_to = target_date`). D zones effectively expire by next session. ADR-003 Phase 1 v2 saw 0 D zones in 10-day lookback because each D zone's `valid_to < lookback_start_date`. Same root pattern as previously-documented H-zone single-day-validity bug (line 53 H zones, all single-day, all EXPIRED). |
| **Root cause** | Hardcoded `valid_to = target_date` in detector, written when D zones were considered ephemeral. Whether 1-day validity is intentional or unintentional has never been documented. |
| **Workaround** | None. Downstream consumers (signal builder, `detect_ict_patterns_runner.py`) querying `valid_from <= today AND valid_to >= today` see D-OB / D PDH / D PDL only on the day of detection, not subsequent days. |
| **Proper fix** | Decide: (a) extend D-zone non-FVG validity to N days (e.g., 2-5 like the new D-FVG validity), OR (b) document 1-day as intentional and adjust downstream consumers to use a different date filter (e.g., look up most recent ACTIVE zone). |
| **Cost to fix** | <1 session for either path. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-02 |

---

### TD-051 — PDH/PDL `+/-20` band hardcoded, symbol-agnostic

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced during code review for BEAR_FVG defect; consolidates "TD-S3.a") |
| **Component** | `detect_weekly_zones()` and `detect_daily_zones()` in both builders. Live `detect_1h_zones()` for session-high/session-low PDH-PDL also uses `+/- 10` (separate constant) |
| **Symptom** | PDH/PDL zones get `zone_high = level + 20`, `zone_low = level - 20` regardless of symbol. NIFTY at ~24,000 → 20pt = ~0.083%. SENSEX at ~80,000 → 20pt = ~0.025%. SENSEX PDH/PDL zones are 3.2x narrower in % terms. 1H session-high/low uses `+/- 10` which is even more asymmetric. |
| **Root cause** | Hardcoded `+/- 20` constant in both builders' D and W detection blocks; `+/- 10` in 1H detector. Single literal, no symbol-conditional logic. |
| **Workaround** | None. Live trading is asymmetric across symbols at this PDH/PDL level. May be acceptable (band is small relative to zone width for OB/FVG zones used as primary structure) but worth quantifying before deciding. |
| **Proper fix** | Replace with `+/- (level * BAND_PCT)` where `BAND_PCT` is a config constant per timeframe (e.g., 0.05% W/D = NIFTY ~12pt / SENSEX ~40pt). Audit downstream consumers (TIER assignment in `detect_ict_patterns.py`, signal generation `APPROACH_PCT` interactions in `build_hist_pattern_signals_5m.py`) before patching — band changes may shift TIER thresholds. |
| **Cost to fix** | <1 session for code; ~1 session for downstream audit. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-02 |

---

### TD-052 — Zone status workflow: write-once, never-recompute (historical builder only)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced during ADR-003 Phase 1 v2 investigation when status filter on `hist_ict_htf_zones` was a no-op; consolidates "TD-S3.b") |
| **Component** | `build_ict_htf_zones_historical.py` (live `build_ict_htf_zones.py` is correct: `recheck_breached_zones` updates status — verified in Session 15 code review) |
| **Symptom** | Historical builder writes `status='ACTIVE'` once per zone and never recomputes. ADR-003 Phase 1 v2 filtered on `status='ACTIVE'` and the filter was a no-op (every historical zone is ACTIVE because no recheck logic exists in the historical builder). Total `hist_ict_htf_zones.status='ACTIVE'` post-Session-15-backfill = 40,384 = 100% of rows. |
| **Root cause** | By-design absence of recheck logic in the historical builder. The no-lookahead audit invariant says: as-of-date snapshot of `hist_ict_htf_zones` must NOT be polluted by future price action. The historical builder honours this by never recomputing status. The implication — that `status` is meaningless on `hist_ict_htf_zones` — is undocumented. |
| **Workaround** | Don't filter on `status` in queries against `hist_ict_htf_zones`. Compute breach manually using `hist_spot_bars_5m` per query (more expensive but correct and respects no-lookahead). Live `ict_htf_zones` queries can use `status` correctly. |
| **Proper fix** | Either: (a) add a separate `historical_zone_status_at(zone_id, as_of_date)` view/function that joins zones with subsequent bars to derive status as-of any date — preserves no-lookahead invariant in source table, OR (b) document that `status` field on `hist_ict_htf_zones` is meaningless and add a CHECK constraint or column comment. Recommendation: (b) for documentation cost, then (a) when a query genuinely needs status (none currently). |
| **Cost to fix** | <1 session for documentation-only; 1-2 sessions for view+function approach. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-02 |

---

### TD-053 — CLAUDE.md Rule 16 needs era-aware addendum (post-04-07 era)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced via ADR-003 Phase 1 v2 + Exp 44 + `diagnostic_bar_coverage_audit_v2.py`; consolidates "TD-NEW-RULE16-ERA-AWARE") |
| **Component** | `CLAUDE.md` Rule 16 (TZ handling guidance for `bar_ts`); affects every repo script that applies the rule |
| **Symptom** | Rule 16 says: apply `replace(tzinfo=None)` to bar_ts and filter to in-session 09:15-15:30. This is correct for pre-04-07 era (bars stored as IST-labelled-as-UTC, the "TD-029 era"). Post-04-07 era stores bars as true UTC. Applying Rule 16 verbatim post-04-07 produces a UTC clock-time and filtering to 09:15-15:30 IST drops most of the day (~9 bars vs ~76 bars per session). Hits any script analysing post-04-07 data with verbatim Rule 16. |
| **Root cause** | Rule 16 was written when only the pre-04-07 era existed. Post-04-07 era introduced 2026-04-07 was not retroactively documented in Rule 16. **Related:** TD-029 (the underlying TZ-stamping bug that created the era boundary). |
| **Workaround** | Era-aware: pre-04-07 use `replace(tzinfo=None)`; post-04-07 use `astimezone(IST_TZ)`. Verified in `diagnostic_bar_coverage_audit_v3.py` which avoids the issue entirely by filtering on `trade_date` column instead of bar_ts time. |
| **Proper fix** | Edit `CLAUDE.md` Rule 16 to add era boundary at 2026-04-07 with code snippet for both eras. Audit all repo scripts that apply Rule 16 verbatim and patch them. Affected scripts identified in Session 15: ADR-003 Phase 1 (v1, v2 INVALID), `experiment_44_inverted_hammer_cascade.py` (verdict survives caveat re-evaluation but v2 re-run cleaner). |
| **Cost to fix** | <1 session for CLAUDE.md edit; ~1 session for repo audit + patches. |
| **Blocked by** | nothing — operator can edit CLAUDE.md anytime; audit can run any session |
| **Owner check-in** | 2026-05-02 |

---

### TD-054 — `ret_60m` column is uniformly 0 in `hist_pattern_signals`

| | |
|---|---|
| **Severity** | S2 (raised from S3 Session 16 — extended scope: column has only 4.7-5.0% agreement with locally-computed forward return across 3 cohorts now, 30% NULL — invalidates any analysis using `ret_30m` directly) |
| **Discovered** | 2026-05-01 (Session 15 — surfaced when Exp 47 review showed `ret_60m` 0.000% across all rows; consolidates "TD-NEW-RET60M"). 2026-05-03 (Session 16) extended scope: `ret_30m` column on same table also broken, not just `ret_60m`. Local re-derive on 3 separate cohorts (Exp 41, Exp 50 v2, ADR-003 Phase 1 v3 indirectly) shows 5% agreement with locally-computed forward return. |
| **Component** | `build_hist_pattern_signals_5m.py` and possibly upstream `hist_market_state` source |
| **Symptom** | `ret_60m` column in `hist_pattern_signals` is 0.000% across every single row — verified Session 15 in Exp 47b output and Exp 50 output. Session 16 expanded: `ret_30m` also unreliable — 4.7% agreement (24/509) with locally-computed forward return on Exp 41 cohort, 5.0% (81/1611) on Exp 50 v2 cohort, 30-35% NULL across both. Any experiment using `ret_30m` sign or magnitude as outcome metric gets noise. |
| **Root cause** | Most likely both columns are computed with broken or stale logic in the signal builder, OR the source `hist_market_state` columns are themselves broken. Not yet diagnosed. |
| **Workaround** | **Do not use `ret_30m` or `ret_60m` columns from `hist_pattern_signals` as outcome metrics.** Compute forward return locally from `hist_spot_bars_5m` using Exp 41 mechanics (Rule 20 era-aware): join signal `bar_ts` to spot bars, find bar at signal_ts and signal_ts + 30/60 minutes, compute `(close_t30 - close_t0) / close_t0 * 100`. Used by every Session 15-16 experiment that needed forward returns. More expensive but correct. |
| **Proper fix** | Diagnose: (a) check `hist_market_state.ret_60m` for population (run a SELECT DISTINCT, MIN, MAX, COUNT against the column). If null/zero, fix at source. If populated correctly there, the signal builder isn't reading it — patch the signal builder to read and forward. Same diagnosis for `ret_30m`. (b) Backfill all `hist_pattern_signals` rows after fix via signal rebuild. **OR**, per ENH-87 (Session 16 filed): consider deprecating `hist_pattern_signals` entirely — Session 16 demonstrated that live-detector replay (`experiment_15_with_csv_dump.py` pattern) provides equivalent research utility without the integrity issues. Decision deferred to Session 17/18. |
| **Cost to fix** | <1 session diagnostic, ~1 session for fix + backfill if pursued. ENH-87 deprecation alternative: 2-3 sessions to migrate downstream consumers. |
| **Blocked by** | ENH-87 (deprecation review) — recommend deciding fix-vs-deprecate before fixing. |
| **Owner check-in** | 2026-05-03 (Session 16 — extended scope, locally-computed workaround in active use); 2026-05-10 (Session 26 — confirmed orthogonal to TD-101 live-side fix). |
| **Cross-reference TD-101** | TD-101 fixed the LIVE-side `momentum_snapshots.ret_session` writer (`build_momentum_features_local.py::get_session_open_spot()` unbounded-query OI-18 anti-pattern). TD-054 is the RESEARCH-side `hist_pattern_signals.ret_30m` / `ret_60m` columns broken by separate writer (`build_hist_pattern_signals_5m.py` and possibly `hist_market_state` source). The two bugs are in different code paths writing different tables; the live fix does not auto-resolve the research-side defect. Locally-computed forward-return workaround per Session 15-16 experiments remains in active use for any analysis on `hist_pattern_signals`. TD-054 status unchanged: defer fix-vs-deprecate decision per ENH-87 (deprecation review). |

---

### TD-055 — `ret_eod` column entirely absent from `hist_pattern_signals`

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-01 (Session 15 — surfaced when Exp 50 setup tried to compute EOD outcome; consolidates "TD-NEW-RETEOD") |
| **Component** | `build_hist_pattern_signals_5m.py` schema; `hist_pattern_signals` table schema |
| **Symptom** | `ret_eod` column does not exist on `hist_pattern_signals`. EOD analysis on this table alone is impossible — every EOD-outcome experiment must JOIN to `hist_spot_bars_5m` and compute the session-end forward return per row. |
| **Root cause** | Column was never added to schema. Existing forward-return columns are `ret_30m` (TD-039: stored as percentage points) and `ret_60m` (TD-054: zeros). |
| **Workaround** | Compute EOD outcome from `hist_spot_bars_5m` directly (or from the daily OHLCV close vs signal-bar close). Used in this form by Session 15 experiments (Exp 44 horizons, ADR-003 Phase 1). |
| **Proper fix** | (a) `ALTER TABLE hist_pattern_signals ADD COLUMN ret_eod NUMERIC(10,6);` (decimal-fraction this time per TD-039 lesson — name it `ret_eod_pct` to match unit-explicit convention from TD-039 proper-fix path). (b) Patch `build_hist_pattern_signals_5m.py` to compute it from session-end bar (15:25 IST, idx -1 of session). (c) Backfill via signal rebuild. |
| **Cost to fix** | 1 session including schema migration, code, backfill, verification. |
| **Blocked by** | TD-039 (column-naming convention decision affects this) — recommend coordinating both fixes. |
| **Owner check-in** | 2026-05-02 |

---

### TD-056 — Signal-detector bull-skew across BOTH code paths (5m batch AND 1m live)

| | |
|---|---|
| **Severity** | S2 (raised from S3 Session 16 — confirmed structural across both detector code paths, not just 5m batch) |
| **Discovered** | 2026-05-02 (Session 15 — surfaced post-BEAR_FVG fix verification on `hist_pattern_signals` 5m batch); 2026-05-03 (Session 16 — Section 17 of `analyze_exp15_trades.py` confirmed live `detect_ict_patterns.py` 1m cohort also bull-skewed; not a 5m-batch-specific artefact) |
| **Component** | BOTH (a) `build_hist_pattern_signals_5m.py` zone-approach filter logic, AND (b) `detect_ict_patterns.py` live 1m detector. Both are bull-skewed independently. |
| **Symptom** | **5m-batch (`hist_pattern_signals`)**: NIFTY 60d signals BULL_FVG 274 / BEAR_FVG 150 (1.83x). NIFTY DOWN regime alone: 112 BULL_FVG / 20 BEAR_FVG = **5.60x bull-skew in DOWN regime**. SENSEX DOWN: 2.30x. **1m-live (`detect_ict_patterns.py` running through Exp 15)**: full year 49 BULL_OB / 25 BEAR_OB pooled. NIFTY DOWN regime: 23 BULL_OB / 7 BEAR_OB = **3.29x**. SENSEX DOWN: 1.50x. Plus: **live detector emits ZERO BEAR_FVG signals across full year**, despite Session 15's `build_ict_htf_zones.py` BEAR_FVG fix (separate issue, see TD-058). Canonical 5m BEAR_FVG / BULL_FVG shapes in `hist_spot_bars_5m` are essentially symmetric (NIFTY 562 BEAR / 587 BULL; SENSEX 567 / 575) — both detector paths underemit BEAR signals relative to raw price-structure availability. |
| **Root cause** | Two non-mutually-exclusive hypotheses: **(H1) zone-availability asymmetry** — the "in or near zone with proximity" filter requires same-direction zones to exist near current price; in an uptrending market BULL zones above-spot are more available than BEAR zones below-spot, so the filter naturally tags more BULL signals. **(H2) detector-symmetry bug** — code paths for BULL vs BEAR detection differ in some non-obvious way (e.g., asymmetric proximity, asymmetric validity windows, missing branch). Session 16 evidence supports H1 partially (bull-skew ratio higher in 5m-batch which has zone-availability filter at signal time, lower in 1m-live which has its own zone construction) but does not fully exonerate H2 (bull-skew persists in DOWN regime where H1 alone would invert the ratio). Mechanism investigation deferred to Session 17 Priority C. |
| **Workaround** | None automated. Operationally: live trading sees more BULL setups than BEAR setups as a result. Operator-side mitigation: **be more discretionary about looking for bear setups in chop/down sessions**, especially when MERDIAN isn't flagging them — the system undersignals bear opportunities, not because individual BEAR signals are wrong (they're 92% WR on the live cohort) but because there are fewer of them than market structure would imply. |
| **Proper fix** | **Phase 1 — mechanism diagnosis (Session 17 Priority C, ~1-2 sessions investigation):** code review `detect_ict_patterns.py` for asymmetric BULL/BEAR branches (proximity computation, validity, opt_type mapping); code review `build_hist_pattern_signals_5m.py` zone-approach filter for direction-asymmetric thresholds; instrument both with detection-attempt counters by direction to measure where BEAR candidates are being filtered out. **Phase 2 — patch (1 session if H2 confirmed, 0 sessions if H1 only):** if asymmetric branch identified, patch and re-verify. If H1 only, document as regime-driven and accept (or rebalance proximity threshold per direction). |
| **Cost to fix** | 1-3 sessions total (Phase 1 + optional Phase 2). |
| **Blocked by** | TD-058 (BEAR_FVG live emission — likely shares root cause with TD-056 H2). Recommend coordinating both investigations. |
| **Owner check-in** | 2026-05-03 (Session 16 — confirmed structural, not 5m-batch-specific; Phase 1 deferred to Session 17 Priority C) |

---

### TD-057 — Exp 15 framework provenance gap (no findable execution audit trail)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-05-03 (Session 16 — surfaced during framework audit when stress-testing Compendium claims) |
| **Component** | `experiment_15_pure_ict_compounding.py`, `MERDIAN_Experiment_Compendium_v1.md` (Exp 15 entry dated 2026-04-12), git history |
| **Symptom** | The only execution log of `experiment_15_pure_ict_compounding.py` on disk is from 2026-04-11 21:40:35, 427 bytes, showing `SyntaxError: unterminated f-string literal at build_ict_htf_zones.py L475`. The script crashed at import. Compendium entry for Exp 15 dated **one day later** (2026-04-12) reports detailed per-pattern findings (BEAR_OB N=36 94.4% WR, BULL_OB N=44 86.4% WR, BULL_FVG N=155 50.3% WR, BULL_OB MEDIUM 90% WR N=45). Recursive search of `C:\GammaEnginePython\logs\` found no successful execution log of this exact script anywhere. `portfolio_simulation_v2.log` from same evening (21:47:10) is a different experiment with different exit rules and no per-pattern WR aggregates. Three possibilities: (a) script rerun successfully post-fix and log deleted/never persisted, (b) numbers from interactive output captured to clipboard not log, (c) numbers from different script attribution. Plus: April-13 commit `c78b6ea` modified BOTH `experiment_15_pure_ict_compounding.py` AND `detect_ict_patterns.py` together, including silent MTF tier relabeling — pre-Apr-13 vocabulary (HIGH=W, MEDIUM=D, LOW=none) became post-Apr-13 (VERY_HIGH=W, HIGH=D, MEDIUM=H, LOW=none). The Apr-12 Compendium uses post-Apr-13 vocabulary to describe pre-Apr-13 measurements. The "1H zones confirmed Established V18F" claim in `merdian_reference.json` rests on this relabeling. |
| **Root cause** | Combination of: (a) interactive-shell run pattern at the time (no automatic log capture), (b) git commits modifying experiment scripts and detector code together with non-descriptive commit messages making provenance hard to reconstruct, (c) Compendium written from session-end state rather than from durable execution artefacts. Not a defect in any single component — an aggregate of process-hygiene gaps. |
| **Workaround** | Session 16 produced `experiment_15_with_csv_dump.py` as a verbatim methodology copy of the original with a CSV-dump tail that produces a durable trade-list artefact (`exp15_trades_<stamp>.csv`). Future research that depends on Exp 15 results uses the CSV pattern, not direct re-attribution to the Apr-12 Compendium claims. Critically: **Session 16 full-year run replicated the Compendium headlines within 2-3pp** (BEAR_OB 92.0% vs claimed 94.4%, BULL_OB 83.7% vs 86.4%, BULL_FVG 50.3% vs 50.3%) — so the published numbers, while audit-traceless, are not refuted. |
| **Proper fix** | (a) Going forward: every experiment must be invoked with `... 2>&1 \| Tee-Object -FilePath <log>` (already in canonical session pattern). (b) Every Compendium entry must cite the execution log path and git commit hash from which findings were derived. (c) Major published findings should be re-runnable in <30 min with current code; if they aren't, the methodology has drifted. (d) Apr-12-era Compendium entries should be flagged as "vocabulary aligned to post-Apr-13 MTF relabeling" so future readers don't conflate "MEDIUM" across the boundary. |
| **Cost to fix** | Going-forward fix is process-only (zero code, zero compute). Retroactive flagging of Apr-12-era entries: 0.5 session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-03 |

---


### TD-059 — ENH-37 MTF context hierarchy inverted from claim (LOW outperforms HIGH on OB patterns)

| | |
|---|---|
| **Severity** | S2 (production sizing rule rests on inverted assumption — currently BOOSTING confidence on cells that empirically UNDERPERFORM) |
| **Discovered** | 2026-05-03 (Session 16 — Section 10 of `analyze_exp15_trades.py` per-cell confidence intervals on N=231 live-cohort trades) |
| **Component** | `build_trade_signal_local.py` (consumes `mtf_context` from `signal_snapshots`); `detect_ict_patterns.py` `get_mtf_context` (computes the tier label); ENH-37 documentation in Enhancement Register |
| **Symptom** | Exp 15 published Compendium claim: "MEDIUM context (1H zone) ADDS edge — keep in MTF hierarchy." Session 16 measurement on 231-trade live cohort with Wilson 95% CIs: **BULL_OB|HIGH (D zone) 71.4% N=7, BULL_OB|MEDIUM (H zone) 81.8% N=11 [52.3, 94.9], BULL_OB|LOW (no zone) 87.1% N=31 [71.1, 94.9]**. **BEAR_OB|HIGH 71.4% N=7, BEAR_OB|MEDIUM 100% N=1, BEAR_OB|LOW 100% N=17 [81.6, 100]**. LOW context outperforms HIGH on BOTH BULL_OB and BEAR_OB. The hierarchy current production code applies (HIGH = high confidence, LOW = low confidence) is **inverted from current-code measurement**. (Note: current vocabulary differs from Apr-12 Compendium — see TD-057 — but even using current vocabulary on current data, the hierarchy is wrong.) |
| **Root cause** | Hypothesis: when a signal triggers in HIGH context (inside a daily zone), the price action is contested — buyers and sellers are both engaged at a known level. The "trade against the zone" logic plays out, but with chop and reduced edge. When a signal triggers in LOW context (no archive-zone confluence), price is in clean expansion — the OB pattern catches a moving market with directional follow-through. Effectively, archive zones may CAUSE the chop they're supposed to identify. Untested hypothesis but consistent with the data. |
| **Workaround** | Operationally for now: **treat MTF context tier as informational, not as a confidence multiplier.** When operator sees a BULL_OB or BEAR_OB on TradingView, do not size up just because it's tagged HIGH context. The pattern itself is the edge; the context tier is currently misleading. |
| **Proper fix** | Three options for Session 18+ to evaluate: **(a) Remove MTF context as a confidence multiplier** — keep as an informational annotation but don't let it affect sizing or tier classification. **(b) Invert it** — LOW becomes "high confidence" in production scoring. Risky without more data; current N=17-31 per cell is enough for direction but not for magnitude. **(c) Run shadow mode with both rules** — keep current production rule live, run alternative rule in shadow, log signal_snapshots with both `confidence_score_v1` (current) and `confidence_score_v2` (alternative) for 4-8 weeks, then compare. Recommend (c) — measure before changing production. |
| **Cost to fix** | (a) ~0.5 session (annotation-only change). (b) ~1 session (invert + verify nothing else depends on the tier ordering). (c) ~1 session to wire shadow mode + 4-8 weeks of measurement + 1 session to decide and ship. |
| **Blocked by** | TD-057 (vocabulary alignment) — fix should clearly state which MTF vocabulary is canonical (Apr-12 vs Apr-13+) before redesigning. |
| **Owner check-in** | 2026-05-03 |

---

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| Hand-patching files on AWS to fix something fast | Creates Local↔AWS drift, no audit trail | Use BREAK_GLASS protocol; doc in Change Protocol Step 8 |
| `print()` left in production code | Pollutes logs; hides real signals | Pre-commit Step 1.5 catches this |
| Hardcoded Windows paths in files destined for AWS | Breaks AWS run silently | Pre-commit Step 1.5 catches this |
| Patch script (`fix_*.py`) without `ast.parse()` validation | Invalid syntax shipped, found at market open | Standing rule (CLAUDE.md #5) — ast.parse every patch |
| Creating a new `OI-N` ID | Register is closed | Use this file (TD-N), ENH-N, or C-N |
| Pasting full master into session | Burns context window, dilutes focus | Targeted JSON lookup per Session Mgmt Rule 4 |
| Mixing concerns in one session | Accelerates context degradation | Split sessions per Session Mgmt Rule 3 |

---

## Resolved (audit trail)

### TD-S58-NEW-1 — purchased options chain (2025-04→2026-03) has 0% Greeks; historical per-strike IV/Greeks + concentration solve — RESOLVED S62

| Field | Value |
|---|---|
| **Severity** | S3 (research-substrate limitation, not a production break) |
| **Filed** | 2026-06-22 (Session 58) |
| **Component** | `hist_option_bars_1m` (purchased vendor chain); ENH-SDM backward frequency study |
| **Symptom** | P0a coverage probe (S58): `hist_option_bars_1m.gamma` is **0.00% present across all 12 purchased months** (2025-04→2026-03) — `iv/delta/gamma/theta/vega` all NULL. Bars are continuous (3.8–5.4M/mo) and OI is 99.9% present, but Greeks are absent. In `gamma_metrics`, `pin_risk_score` traces back only to 2026-05-25 and `straddle_atm` to 2026-05-08, so only ~8 expiry days have all four ENH-SDM primitives co-present (`rows_all5_present` = 1,500 / 40,611). N≈8 cannot support a frequency study or an ADR-009 holdout. |
| **Root cause** | The purchased vendor chain arrived Greeks-less. The live pipeline solves Greeks forward (`gamma_metrics` has gamma now), but the S29 "full-year backfill" computed `net_gex`/`gamma_concentration` from a partial pass and never solved per-strike Greeks or the pin/straddle layer over the purchased year. |
| **Impact** | The ENH-SDM backward study (the cohort that would lift N from ~8 toward ~50) is blocked. `straddle_atm` backfill is viable standalone (no Greeks needed — just ATM CE+PE close). `pin_risk_score` + `gamma_concentration` backfill require a full per-strike IV/Greeks solve over ~55M bars first. |
| **Workaround** | ENH-SDM ships as a **forward observability monitor** (P1 schema + P2 context-writer, display-not-gate); the cohort accrues forward from S58. No backward study, and no signal/modes build, until the Greeks backfill is funded. |
| **Proper fix** | Scoped Greeks-backfill project: per-strike BS/Heston IV+gamma solve over `hist_option_bars_1m` 2025-04→2026-03, then recompute `pin_risk_score` + `gamma_concentration`, validated against live forward values (ADR-009-grade) before any study consumes it. |
| **Cost to fix** | Multi-session (solve + recompute + validation over ~55M bars). |
| **Blocked by** | Ideally ENH-07 (risk-free rate — the unresolved 6.5% hardcode would bias the IV solve) and TD-095 (IV-solver unit ambiguity) resolved first. |
| **Related** | ENH-SDM; ADR-018 D4; CASE-2026-06-02; TD-S34-NEW-4 (post-Apr-2026 chain gap); TD-094 (historical OI — confirmed clean at 99.9% this probe); TD-095 (IV unit ambiguity). |
| **Closed** | 2026-07-01 (Session 62) |
| **Resolution** | Built + ran the historical per-strike solve to completion. `backfill_hist_greeks.py` (vectorized numpy IV bisection over `hist_option_bars_1m`, NOT mutated; reproduces `signed_gex_vec` verbatim; deep-ITM reject + PE flip + `γ·oi·S²/1e7`) writes a lean `iv`+`gamma` sidecar `hist_option_greeks_1m`. **KEY DISCOVERY:** a pre-existing full-window (Apr 2025–Mar 2026) both-symbol 1-minute `hist_gamma_metrics` series already carried `net_gex`/`flip_level`/`regime` etc. with its **one** empty column being `gamma_concentration` — so the task collapsed from "recompute everything" to "fill that one column." `fill_gamma_concentration.py` computes `gamma_concentration = max|gex|/sum|gex|` (verbatim from `compute_gamma_concentration`; Herfindahl, scale-invariant) and idempotently PATCHes only that column on (symbol, bar_ts). `run_fullwindow.py` orchestrated per-month solve+fill, token-independent, resumable. Expiry days handled as an explicit `SKIPPED_EXPIRY` (0-DTE flat-vol net_gex is numerically unreconstructible — `diag_1125.py`; live-sourced instead). Flat r=6.5% (ENH-07 A closed no-op). |
| **Verification** | `--validate` gates PASS: sidecar sign≥98/sreg≥94/mag 0.9–1.1 on 2025-09-19 (100/100/1.00) + 2025-09-29 (99/95/0.96); concentration reconstruction reproduces existing-table net_gex on 2025-08-01 (sign 376/376=100%; conc min 0.135/med 0.190/max 0.217 — sane index dominance). **NIFTY COMPLETE** (12 mo, ~71,900 conc rows, expiry-day nulls exactly on the expiry Tuesdays). **SENSEX COMPLETE** — `ALL DONE symbol=SENSEX total 1145.4 min`. A proven-DIVERGENT `--fast` path was ABANDONED (not loosened) per "correct-and-slower beats fast-and-subtly-wrong." |
| **Residual** | ONE day: SENSEX 2026-01-19 unfilled (SSLError mid-solve) → filed as **TD-S62-NEW-2** with a one-line resume. Apr 2026+ has no raw bars (backfill correctly loud-aborts there). |
| **Enables** | The expiry-memory seed for ENH-116 (PROPOSED, P2) and any future ENH-SDM backward study. |

### TD-S53-NEW-4 — option-chain ingest :00–:29 hourly hole in hours 04–09 UTC — RESOLVED S54 via `*/5`

| Field | Value |
|---|---|
| **Filed** | 2026-06-12 (Session 53) |
| **Closed** | 2026-06-15 (Session 54) via crontab `*/5` |
| **Severity** | S3 |
| **Symptom** | Hours 04–09 UTC ingested only at minutes 30,35,40,45,50,55, leaving the :00–:29 half of every hour with no option-chain ingest — stale option_chain_snapshots feeding GEX/pin/headline-spot, and 409 collisions during the gap before the upsert landed. |
| **Fix applied** | Changed the two 04–09 UTC ingest crontab lines' minute field from `30,35,40,45,50,55` → `*/5` (surgical minute-field-only edit; `bash run_ingest.sh NIFTY/SENSEX FULL` args untouched). Snapshot taken pre-edit; diff confirmed only the minute field moved on two lines. |
| **Verification** | Live on 2026-06-15: `*/5` fires in the former dead zone (run_ids streaming 04:30–09:55, INGEST OPTION CHAIN COMPLETED 460/372 rows). 2026-06-15 audit: option_chain 68 distinct-min/symbol, dense `*/5` with no gaps after the mid-window flip remnant (04:00–04:25). |
| **Residual** | Doubles Dhan option-chain calls 6→12/hr in 04–09 — watch cron.log for 429/401; if quota is tight, fall back to 10-min spacing (0,10,20,30,40,50). Tracked as a carry-forward watch item, not a TD. |

### TD-S53-NEW-3 — compute_volatility_metrics_local.py lacked ON CONFLICT → 409 collisions during the ingest hole — RESOLVED via upsert

| Field | Value |
|---|---|
| **Filed** | 2026-06-12 (Session 53) |
| **Closed** | 2026-06-12 (Session 53) — commit cd98a87 |
| **Severity** | S2 |
| **Symptom** | Volatility writes used `sb.insert(...)` with no ON CONFLICT, so repeated (symbol, ts) within a window threw 409 / 23505 and failed those orchestrator cycles. |
| **Fix applied** | `sb.insert(TARGET_TABLE,[row])` → `sb.upsert(TARGET_TABLE,[row], on_conflict="symbol,ts")`. core/supabase_client.py already had upsert (Prefer: resolution=merge-duplicates); the insert-not-upsert was punted 'out of scope for ENH-72', not deliberate. Deployed Local Notepad→commit cd98a87→EC2 `git checkout origin/main -- compute_volatility_metrics_local.py` (NOT full pull — dirty CRLF tree). |
| **Verification** | Live: sb.upsert on disk, COMPILE OK, PIPELINE COMPLETE, no 23505. 2026-06-15 full day: 0 PIPELINE FAILED, upsert held. |
| **Note** | Correct fix — but for SENSEX it converted a loud 409 into a silent merge, unmasking the pre-existing SENSEX compute under-write now tracked as TD-S54-NEW-1. |

### TD-S53-NEW-2 — four run_ingest.sh crontab lines corrupted by the 00:47 UTC reinstall — RESOLVED S53

| Field | Value |
|---|---|
| **Filed** | 2026-06-12 (Session 53) |
| **Closed** | 2026-06-12 (Session 53) |
| **Severity** | S1 |
| **Symptom** | The 00:47 UTC 2026-06-12 crontab reinstall corrupted the four run_ingest.sh lines (command body lost) so option-chain ingest never ran. |
| **Fix applied** | Reconstructed the 4 ingest lines to the working UNQUOTED form `cd /home/ssm-user/meridian-engine && bash run_ingest.sh NIFTY/SENSEX FULL >> cron.log 2>&1` (run_ingest.sh self-sources .env; the S49 single-quoted 'NIFTY FULL' form is NOT what's live — the unquoted form is). |
| **Verification** | 248+ INGEST OPTION CHAIN COMPLETED post-fix; ingest firing on schedule. |

### TD-S53-NEW-1 — cron `SHELL=/bin/bash` directive dropped → dash → every `source .env` chain died silently — RESOLVED S53 (root cause of the blackout)

| Field | Value |
|---|---|
| **Filed** | 2026-06-12 (Session 53) |
| **Closed** | 2026-06-12 (Session 53) |
| **Severity** | S1 |
| **Symptom** | Total capture + compute blackout since ~2026-06-11 05:03 UTC: 0 shadow_runner rows, frozen status.json, empty capture tables, all four S52 monitors silent. |
| **Root cause** | A crontab reinstall at 00:47 UTC 2026-06-12 dropped `SHELL=/bin/bash` → cron defaulted to /bin/sh (dash) → `source` is a bash builtin dash lacks → every `cd … && source .env && python3 …` chain died with `/bin/sh: source: not found` into discarded cron mail. Capture + all 4 monitors share that chain → died identically. |
| **Fix applied** | Added `SHELL=/bin/bash` as crontab line 1 via `crontab -e`. |
| **Verification** | logs/monitor.log created + cron self-running within ~80s; capture + all 4 monitors resurrected at once; 05:00 UTC orchestrator cycle PIPELINE COMPLETE. |
| **Canonical lesson** | Always verify `SHELL=/bin/bash` as crontab line 1 on AWS. Probe: `/bin/sh -c 'source .env && echo CHAIN_OK'` and `pwd; echo HOME=$HOME; SHELL=$SHELL`. Monitors must not share the env-loading failure chain of what they monitor. |

### TD-S41-NEW-4 — `build_wcb_snapshot_local.py` writer not instrumented to `script_execution_log` — DISCOVERED + CLOSED same-session

| Field | Value |
|---|---|
| **Filed** | 2026-06-01 (Session 41) |
| **Closed** | 2026-06-01 (Session 41 — DISCOVERED + CLOSED same-session; the 13th same-session NEW+RESOLVED pattern across MERDIAN history) |
| **Severity** | S2 |
| **Symptom** | Marketview Health dashboard WRITER FRESHNESS table row for WCB showed "never" despite `weighted_constituent_breadth_snapshots` having 588 rows over the prior 7 days. Q1 diagnostic confirmed only `ingest_breadth_from_ticks.py` + `ingest_breadth_intraday_local.py` present in `script_execution_log` under wcb/breadth filter; `build_wcb_snapshot_local.py` silent to instrumentation. Q2 confirmed writer alive (latest snapshot 2026-05-29 09:40 UTC) but invisible to observable-health surface. |
| **Root cause** | `build_wcb_snapshot_local.py` predates ENH-72 ExecutionLog instrumentation standardization; never had `from core.execution_log import ExecutionLog` import or `ExecutionLog.open() / record_write() / complete() / exit_with_reason()` lifecycle calls. Writer cron runs, writes to `weighted_constituent_breadth_snapshots`, exits — without leaving a row in `script_execution_log`. Health dashboard reads `script_execution_log.script_name = 'build_wcb_snapshot_local'` so the row never appears. |
| **Fix applied** | `patch_s41_p0b_build_wcb_executionlog_instrumentation.py` (2 replacements, v3 BOM-safe + AST-validate + `_PRE_S41.py` backup): R1 add `from core.execution_log import ExecutionLog`; R2 rewrite `main()` with canonical pattern from `compute_gamma_metrics_local.py` — parse args BEFORE ExecutionLog open, open log with `expected_writes={"weighted_constituent_breadth_snapshots":1}` + `symbol=index_symbol` (Choice A — per-symbol writer cadence), wrap try/except, record_write/complete/exit_with_reason, change `main() -> int` and `sys.exit(main())`. CRLF preserved 12,668 → 14,777 bytes. |
| **Verification** | Smoke-fire NIFTY + SENSEX both produced SUCCESS rows in `script_execution_log`: exit_reason=SUCCESS, contract_met=true, actual_writes={"weighted_constituent_breadth_snapshots":1}, host=local, durations 1858/2401 ms. Marketview Health dashboard WCB row now reads the writer's runtime instead of "never". |
| **Lessons** | (a) **Observable-surface-first discovery** — Marketview Health dashboard surfaced the gap within 30s polling cadence; runtime gap detection from dashboard → diagnostic SQL → writer-source-reading → instrumentation patch + smoke-fire all in <90 min. Pattern is observable-surface-first not log-grep-first when the question is "is this writer instrumented" rather than "is this writer failing". (b) **ENH-72 ExecutionLog instrumentation pattern is canonical** — `compute_gamma_metrics_local.py` is the reference implementation; replicate args-parse-before-log-open + record_write-per-target + complete + exit_with_reason at every other writer that lacks the pattern. (c) **Choice A symbol=index_symbol** for per-symbol writer cadence — NIFTY and SENSEX rows in `script_execution_log` are distinct, mirrors the writer's actual per-symbol invocation pattern; alternative Choice B `symbol='wcb'` would have collapsed both into one row obscuring per-symbol freshness. |
| **Related** | ENH-72 ExecutionLog instrumentation pattern, `compute_gamma_metrics_local.py` (reference implementation), Marketview Health dashboard (observable surface that surfaced the gap), `weighted_constituent_breadth_snapshots` (the write target). |

---


> Closed items live here forever. Never delete — they are evidence of work done and decisions made.

### TD-S37-01 (closed) — Hardcoded τ_pin = τ_accel = 0.3 in ENH-81 SQL views → runtime `get_parameter_num('pin.tau.'||symbol)` lookup against `merdian_parameters`

| | |
|---|---|
| **Filed** | 2026-05-25 (Session 37) |
| **Closed** | 2026-05-29 (Session 40 — P1 carry-forward from S39 actioned) |
| **Closing patch** | `patch_s40_enh83_view_tau_rewrite.py` (BOM-safe via `read_bytes() + decode('utf-8-sig')` per house v3 patch canon; predominant-EOL detection + preservation on write to prevent Windows CRLF corruption; AST-validate pre+post via SQL syntax check; `_PRE_S40.sql` backups preserved for both view DDL files; idempotency guard rejects re-application via marker check; ASCII-clean v2 post initial cp1252 incompatibility (TD-S40-NEW-1)). Two surgical replacements applied: (1) `0.3::numeric AS tau_pin` → `get_parameter_num('pin.tau.'||p.symbol)::numeric AS tau_used` in `sql/2026-05-25_enh81_v_gex_strike_pin_zone.sql`; (2) `0.3::numeric AS tau_accel` → `get_parameter_num('accel.tau.'||p.symbol)::numeric AS tau_used` in `sql/2026-05-25_enh81_v_gex_strike_accel_zone.sql`. Both view DDLs re-applied via Supabase SQL editor → smoke-fire SQL `SELECT DISTINCT tau_used FROM v_gex_strike_pin_zone WHERE symbol='NIFTY'` → `0.30`; same against `v_gex_strike_accel_zone` for both symbols; against live `merdian_parameters` rows (`pin.tau.NIFTY=0.30`, `pin.tau.SENSEX=0.30`, `accel.tau.NIFTY=0.30`, `accel.tau.SENSEX=0.30` — all from ENH-110 Phase 1 bootstrap seed S39). `// TAU_PIN — swap for ENH-83 lookup` markers removed from view bodies. |
| **End-to-end calibration round-trip verification** | Operator-initiated round-trip 0.30→0.25→0.30 on `pin.tau.NIFTY` via `update_parameter` RPC (with TD-S40-NEW-2 fix landed same-session to make the RPC functional): clean temporal chain confirmed (1st baseline row `valid_to=null`; 2nd update closes 1st `valid_to=t1` + inserts new `valid_from=t1 valid_to=null`; 3rd update closes 2nd `valid_to=t2` + inserts new `valid_from=t2 valid_to=null`); ENH-81 views read updated τ correctly across the round-trip. |
| **Architectural significance** | First operator-driven runtime calibration round-trip against a live trading-engine parameter through the full ENH-83 plumbing (Lovable-scaffolded `merdian_parameters` table + `core/parameters.py` typed-column API + `update_parameter` SECURITY DEFINER RPC + `get_parameter_num` SQL function consumed inside view DDLs). Calibration-deferred-by-design pattern (S37) → calibration-functional pattern (S40) executed in 3 sessions. The marker pattern (S37) for the future plumb-point was the discipline that prevented 6-12 month archaeology when the plumb finally happened — grep for `TAU_PIN` returned every site that had to be touched, and the patch script targeted those sites mechanically. |
| **Lessons** | **(a) Calibration-deferred-by-design works iff the deferral is marked mechanically** — the `// TAU_PIN — swap for ENH-83 lookup` markers at every value-site reduced TD-S37-01 closure to a 2-edit patch script + Supabase re-apply, total wallclock ~10 min; codified as discipline-pattern at §D.19.1 + ADR-016 + Doc Protocol v4 candidate Rule N+1. **(b) End-to-end round-trip smoke-fires surface schema-defect bugs that table-creation tests miss** — TD-S40-NEW-2 (`valid_to DEFAULT now()` CHECK violation) only surfaced when the calibration round-trip attempted an actual `update_parameter` call inside a transaction; any schema-add-constraints + RPC pair must include a same-session round-trip smoke-fire to surface CHECK-violation interactions. **(c) Patch script ASCII-only authoring discipline for Windows-side scripts** — initial v1 used Unicode minus-sign `−` (U+2212) in a comment which failed on Windows cp1252 console (TD-S40-NEW-1); v2 ASCII-clean shipped same-session; codify as Windows patch-script ASCII-only authoring rule. |
| **Related** | ADR-016 PROPOSED (parent decision, S37); ENH-83 calibration console (target build — graduated PROPOSED→SHIPPED S39 via Lovable-scaffolded `merdian_parameters` + S39 trimmed ALTER); ENH-81 views (now reading τ from `merdian_parameters` runtime, S40); TD-S40-NEW-2 same-session closure (`valid_to DROP DEFAULT` fix made the round-trip possible); D.22.1 §Assumption Register S40 (Lovable temporal-immutable column DEFAULT audit pattern, REFUTED via this round-trip's CHECK violation); CLAUDE.md v1.30 (S40 settled-decisions footer entry for TD-S37-01 closure pattern via `get_parameter_num` runtime swap). |

---

### TD-S40-NEW-2 (closed same-session) — `update_parameter()` SECURITY DEFINER RPC violated `chk_valid_from_to` CHECK constraint due to `merdian_parameters.valid_to DEFAULT now()`

| | |
|---|---|
| **Filed** | 2026-05-29 (Session 40 — discovered during TD-S37-01 closure round-trip smoke-fire) |
| **Closed** | 2026-05-29 (Session 40 same-session as discovery) |
| **Closing change** | Single ALTER TABLE statement: `ALTER TABLE public.merdian_parameters ALTER COLUMN valid_to DROP DEFAULT;` applied via Supabase SQL editor. No code change; no patch script; no backup needed (DDL-only). |
| **Verification** | `SELECT column_default FROM information_schema.columns WHERE table_schema='public' AND table_name='merdian_parameters' AND column_name='valid_to'` returns NULL post-fix. Round-trip 0.30→0.25→0.30 on `pin.tau.NIFTY` succeeded post-fix; clean temporal chain (1st row valid_to=null, 2nd row 1st gets valid_to=t1 / new row valid_from=t1 valid_to=null, 3rd row 2nd gets valid_to=t2 / new row valid_from=t2 valid_to=null — strict chain confirmed). |
| **Root cause analysis** | Lovable's auto-scaffold for `merdian_parameters` (S39) gave `valid_to` a `DEFAULT now()` value at table-create time. PostgreSQL `now()` returns transaction-timestamp (not statement-timestamp), which is identical across all calls within a single transaction. `update_parameter`'s atomic close-old-row (`SET valid_to=now()`) + insert-new-row pattern runs both statements inside one transaction; the new row inherited `valid_to = now() = valid_from = now()` from the column default; CHECK `chk_valid_from_to (valid_from < valid_to OR valid_to IS NULL)` rejected. Lovable's DEFAULT choice would have been reasonable for SELECT-time inserts (single statement, single now()) but is broken for multi-statement atomic transactions where rows need to differentiate by transaction-time. |
| **Lessons (codified §D.22.1 Assumption Register S40)** | Any column intended to differentiate rows by transaction-time within a single transaction must NOT carry `DEFAULT now()` or any statement-timestamp-equivalent default; subsequent Lovable schema scaffolds for temporal-immutable tables require pre-deploy `information_schema.columns` audit for `column_default IS NOT NULL AND column_default LIKE '%now()%'` on any column whose semantics span multiple rows within one transaction. Specifically: temporal-immutable / SCD-Type-2 / valid_from-valid_to row-versioning patterns are vulnerable; bitemporal patterns are also vulnerable. Append-only insert-with-current-timestamp patterns are NOT vulnerable (a single statement = a single now() call). |
| **Related** | TD-S37-01 closure (round-trip that surfaced this); §D.22.1 Assumption Register S40 (Lovable temporal-immutable column DEFAULT audit pattern, REFUTED-S40); ENH-110 Phase 1 backend (S39 — Lovable scaffold that introduced the defective DEFAULT); `update_parameter` RPC definition (still correct as designed; the column DEFAULT was the bug, not the RPC body). |

---

### TD-S40-NEW-1 (closed same-session) — Patch script `patch_s40_enh83_view_tau_rewrite.py` v1 contained cp1252-incompatible Unicode minus-sign

| | |
|---|---|
| **Filed** | 2026-05-29 (Session 40) |
| **Closed** | 2026-05-29 (Session 40 same-session as discovery — dry-run surfaced before live application) |
| **Closing change** | v1 → v2 single-character replacement: `−` (U+2212 MINUS SIGN) → `-` (U+002D HYPHEN-MINUS) in a comment block at module top of `patch_s40_enh83_view_tau_rewrite.py`. v2 dry-run PASS → live → PASS. v1 was never applied to live SQL DDL files. |
| **Verification** | `python patch_s40_enh83_view_tau_rewrite.py --dry-run` PASS post-replacement on operator's Windows cp1252 PowerShell console. Live application proceeded normally; both view DDLs patched cleanly. |
| **Root cause** | Patch script authoring habit picked up Unicode minus-sign `−` (U+2212) from copy-paste of mathematical-typography source material; Windows PowerShell default cp1252 console encoding cannot render U+2212 (only ASCII `-` is in cp1252's character set); script failed at `print()` calls trying to emit comment text to stdout. Patch logic itself was correct — encoding incompatibility prevented reaching the AST-validate / live-apply steps. |
| **Lessons** | Windows patch-script ASCII-only authoring discipline: any patch script intended to run on operator's Windows console must avoid Unicode characters outside cp1252's character set in print statements, comments printed to stdout, or string literals passed through `print()`. Codified as patch-script ASCII-only authoring corollary to CLAUDE.md patch-script protocol (which codifies the `read_bytes() + decode('utf-8-sig')` + `write_bytes(text.encode(enc))` discipline for the patched-file contents — this TD adds an authoring-side rule for the patch-script-source itself). Alternative: run patches under `chcp 65001` UTF-8 PowerShell context, but the operator's default is cp1252 so ASCII-only is the safer default. |
| **Related** | `patch_s40_enh83_view_tau_rewrite.py` v1 (encoding bug, never applied to live files) → v2 (ASCII-clean, APPLIED — closes TD-S37-01 same-session); CLAUDE.md patch-script protocol (S29 codification of `_PATCHED.py` → dry-run → live → verify → rename + `_PRE_<session>.py` backups pattern; this TD adds Windows ASCII-only authoring corollary). |


---

### TD-061 — Task Scheduler entry points spawn visible console windows (S38 FINAL LONG-TAIL CLOSURE)

| | |
|---|---|
| **Severity at close** | RESOLVED-S29 (declared with 5 residuals documented) → RESOLVED-FINAL-S38 (3 of 5 residuals actioned, 0 live window-flash sources) |
| **Final closure date** | 2026-05-26 (Session 38 — P6 long-tail closure) |
| **S38 actions taken** | 3 PowerShell commands executed: (a) `MERDIAN_Dhan_Token_Refresh` migrated `python.exe → pythonw.exe` (args unchanged) via `Set-ScheduledTask -Action` with `New-ScheduledTaskAction -Execute "C:\Users\balan\AppData\Local\Programs\Python\Python312\pythonw.exe" -Argument "C:\GammaEnginePython\refresh_dhan_token.py"`; (b) `MERDIAN_Intraday_Session_Start` migrated from `cmd /c cd /d C:\GammaEnginePython && python.exe run_option_snapshot_intraday_runner.py >> logs\option_runner.log 2>&1` to direct `pythonw.exe run_option_snapshot_intraday_runner.py` after reading runner source confirmed script has internal `logs/option_snapshot_intraday_runner.log` logging making cmd-wrapper redirection duplicative; (c) `MERDIAN_Market_Tape_1M` `Disable-ScheduledTask` (broken DhanError 401 since 2026-04-07 — S23 candidate finally actioned). |
| **S38 final state** | 16/20 actions on pythonw (was 14/20 at S36, +2 from S38); 19/20 settings hardened with `Hidden=$true + MultipleInstances=IgnoreNew` (unchanged — `MERDIAN_Intraday_Supervisor_Start` multi-trigger XML quirk still open as TD-S38-NEW-1 S4); **0 live window-flash sources** (down from 5 at S29 close). |
| **Documented residuals (post-S38)** | 4 of 20 tasks remain non-pythonw, all legitimate: (1) `MERDIAN_Watchdog` PowerShell observer by design (`watchdog_check.ps1`); (2) `MERDIAN_Intraday_Supervisor_Start` PowerShell by design (`merdian_morning_start.ps1`) + multi-trigger XML settings quirk (TD-S38-NEW-1 S4); (3) `MERDIAN_Market_Tape_1M` DISABLED durable S38 (was broken DhanError 401); (4) `MERDIAN_WS_Feed_0900` DISABLED durable S28. None of the 4 produce live window flashes. |
| **Lessons** | **(a) TDs declared RESOLVED with documented residuals should be re-audited at sprint cadence** — S29 listed 5 residuals as legitimate exceptions but 3 of 5 were actually trivially-actionable (Dhan_Token_Refresh + Intraday_Session_Start + Market_Tape_1M); operator session S38 P6 walked all 3 in <30 min; residuals may have moved from blocking to trivially-actionable as upstream changed. (b) Cmd-wrapper-to-direct migration decisions benefit from reading the wrapped script's source — `run_option_snapshot_intraday_runner.py` has internal `script_execution_log` + per-step logging via `log()` writing to dedicated logfile, making the cmd-wrapper's `>> logs\option_runner.log 2>&1` redirection structurally duplicative; choosing Option A (drop wrapper) over Option B (preserve wrapper for log capture) was data-driven not pattern-matched. (c) **Doc Protocol v4 Rule N alignment finally achieved** — TD-061 body-state matches footer-claim across all 20 tasks (no "footer says RESOLVED but body still has 5 residuals" divergence S29's discipline still left). |
| **Related** | TD-061 S29 RESOLVED block (above in Resolved section — preserved verbatim per no-crunch), TD-S38-NEW-1 (the 1 remaining XML quirk residual), Topology §7.2 (canonical 20-task inventory with S38 column added), CLAUDE.md v1.28 (S38 settled-decisions including TD-061 final-state). |


---

### TD-NEW-2 (closed) — `flip_level` regression: stuck at ~21,250 due to spurious deep-ITM CE gamma from Dhan

| | |
|---|---|
| **Filed** | 2026-05-11 (Session 27 — discovery via Phase 0a §3 sign-convention audit Q3 stuck-flip diagnostic across 30-day NIFTY lookback) |
| **Closed** | 2026-05-11 (Session 27 same-session — third same-session NEW+RESOLVED pattern after TD-097 S25 + TD-101 S26) |
| **Closing commit** | `241f943` |
| **Severity at filing** | S1 (production gamma engine writing meaningless flip values for 3+ trading days; ENH-35 LONG_GAMMA gate consumes these values; impacts live trading signals on every cycle 2026-05-08 onwards) |
| **Component** | `compute_gamma_metrics_local.py::signed_gamma_exposure()` (input layer) + `compute_gamma_metrics_local.py::compute_flip_level()` (algorithm layer). Primary live writer of `gamma_metrics.flip_level`. |
| **Discovery path** | Session 27 began with ADR-002 v2 step-3 first sequencing (sign audit before refinement before adoption). Audit pulled 3 reference cycles from source-material dashboard screenshots (Apr 28 12:21 IST clean pin, Apr 28 12:23 IST flip-edge stress, Apr 30 ~10:50 IST cascade warning) for MERDIAN-vs-source comparison. MERDIAN's `flip_level` at Apr 30 ~10:50 IST showed 24,218-24,263 across 4 cycles while source dashboard read flip at 23,877 (370-pt gap). Diagnostic Query 1 (flip-stuck hourly distribution across 30 days) revealed 2026-05-08 and 2026-05-11 had 95%+ of rows with `flip_level` clustered at 21,250.05 across multiple distinct intraday cycles, while every prior session (2026-04-01 through 2026-05-07) showed 11-119 distinct flip values per day with operationally reasonable ranges (mostly 22,000-25,000). Regression window narrowed to 2026-05-07 09:00 UTC → 2026-05-08 03:00 UTC. **Cutoff diagnosis ruled out code regression** (no Session 26 commits touched gamma compute pipeline). Diagnostic Query Apr-28-vs-May-08 inspection of `option_chain_snapshots` deep-strike rows 21,000-22,000 revealed Dhan started returning `gamma=0.00007` at strike 21,250 CE on 2026-05-08 (oi=130, spot ~24,200). For deep-ITM CE with delta≈1, gamma should be near zero; 70× ATM gamma is impossible for a legitimate ITM option. Additional spurious values at strikes 21,500 CE (gamma=0.000025), 22,000 CE (gamma=0.0000109) confirmed multiple bad rows. **Latent algorithm fragility surfaced by input-shape change**, not a code regression. |
| **Symptom** | `gamma_metrics.flip_level` stuck at 21,250.05 (or 21,200-21,254 narrow band) across 95%+ of intraday cycles on 2026-05-08 + 2026-05-11. Spot ~24,200 across same window → `flip_distance_pct` resolves to ~12% (3,000+ pts from spot), placing every cycle deep into LOW_GAMMA zone per `determine_gamma_zone()` thresholds (<0.5%=HIGH, <1.5%=MID, ≥1.5%=LOW). Operational flip should be within ~1-2% of spot during normal market structure. Production `gamma_zone` field LOW_GAMMA across the broken window contributes to ENH-35 gate decisions on every signal cycle. |
| **Root cause** | Two-layer fragility. **Layer 1 (input)**: `signed_gamma_exposure()` accepted all rows from Dhan unconditionally (only rejected `gamma == 0.0 or oi <= 0.0 or spot <= 0.0`); no sanity guard for impossible-for-deep-ITM gamma values. **Layer 2 (algorithm)**: `compute_flip_level()` walked cumulative GEX bottom-up from `min_strike=17,850` and returned first zero-crossing. When Dhan's spurious deep-ITM CE gamma injects positive contributions at deep strikes where surrounding strikes have legitimately zero contribution (because deep-OTM/deep-ITM options have near-zero legitimate gamma), the running sum crosses zero at the spurious strike's neighborhood and the algorithm returns that as `flip_level` — semantically the "first crossing walking up from min_strike" but operationally meaningless. The algorithm's correctness assumption "deep-strike contributions are small" was data-conditional, not algorithmic — held for entire prior history under Dhan's pre-2026-05-08 response shape, broke when input shape changed. |
| **Fix** | Two-part patch via `fix_td_new_2_flip_level.py` (canonical patch pattern: BOM-safe read via `read_bytes() + decode('utf-8-sig')`, EOL detection + preservation on write via `write_bytes`, `ast.parse()` self-validation before write, `_PRE_TD-NEW-2.py` backup, `_PATCHED.py` output for inspection). **Part A (necessary fix)** modifies `signed_gamma_exposure()` to reject rows where `\|strike-spot\|/spot > 5%` AND `\|gamma\| > 5e-5` (5× typical ATM gamma; well outside legitimate deep-ITM values; reject threshold calibrated against HEALTHY 2026-05-07 data — zero false positives observed in verification). **Part B (algorithm hardening)** modifies `compute_flip_level()` to accept optional `spot` parameter and walk outward from ATM in both directions, returning zero-crossing nearest to spot (operational flip definition). Legacy bottom-up walk preserved as fallback when `spot=None` (backward compatibility for callers that haven't been updated). Three edits applied: `signed_gamma_exposure` body + `compute_flip_level` body + call site at line 605 to pass `spot`. AST OK. |
| **Validation** | Verification harness `verify_td_new_2_flip_level.py` imports PATCHED module via importlib (sys.modules registration required pre-exec_module for `@dataclass` GammaMetricsResult declaration — known importlib + dataclass interaction). Runs pure functions against 2 real `option_chain_snapshots` cycles: **HEALTHY 2026-05-07 04:01:25 IST** — LIVE flip 24,785.97 vs PATCHED flip 24,773.93, delta -12.05pts (0.05%); confirms no regression on clean data, sanity guard threshold well-calibrated. **BROKEN 2026-05-08 04:00:09 IST** — LIVE flip 21,250.05 stuck vs PATCHED flip 25,060.15 near-spot (spot 24,239), delta +3,810pts correction. Both PASS. Also notable: PATCHED `net_gex` on broken cycle dropped from 22T to 2.27T after Part A filtering — multiple bad rows filtered, not just strike 21,250. Renamed PATCHED → canonical via `del compute_gamma_metrics_local.py && ren compute_gamma_metrics_local_PATCHED.py compute_gamma_metrics_local.py`. Backup `compute_gamma_metrics_local_PRE_TD-NEW-2.py` preserved. **Live verification queued for Mon 2026-05-12 09:15 IST first cycle** — SQL `SELECT ts, spot, net_gex, flip_level, regime FROM gamma_metrics WHERE symbol='NIFTY' AND ts > NOW() - INTERVAL '10 minutes'` expects flip_level in 23,000-25,500 range (operational, near spot), not stuck ~21,250. |
| **Honest reframing from smoke test** | Original framing called Part A + Part B "belt + suspenders" — implying defensive redundancy. Smoke test caught important framing correction: Part B alone is **insufficient** against this specific bug pattern. The spurious contribution at strike 21,250 sits in a region where all surrounding strikes have legitimately zero contribution; walk-from-ATM cumulative stays uniformly positive through the bad-row plateau and only dips to zero at the strike below — that's a zero-crossing walk-from-ATM correctly detects, but it's not the operational flip. Honest reframing: **Part A is necessary; Part B is hardening for class-of-future-bugs** (noisy distributed contributions, multiple small spurious values across the chain). Both parts shipped together, but the framing matters for future operator understanding — don't assume defensive equivalence between parts. |
| **Live impact (silent-failure window)** | 2026-05-08 → 2026-05-11 (3 trading days, ~430 cycles per day × 2 symbols ≈ 2,500 cycles total). `flip_level` field stuck at ~21,250 across the window. `flip_distance_pct` field stuck at ~12%. `gamma_zone` field stuck at LOW_GAMMA. ENH-35 LONG_GAMMA gate consumes regime (which is sign-only from `net_gex`, so regime classification was correct) but downstream signal logic that reads `flip_distance_pct` magnitude saw stale values across the window. Backfill of broken-window `gamma_metrics` rows for 2026-05-08 onwards deferred to S28+ as P1 carry-forward (custom script reusing patched compute module, not via `backfill_gamma_metrics.py` which writes to separate `hist_gamma_metrics`). |
| **Replay parity** | `replay/replay_compute_gamma_metrics.py` carries its own copy of `signed_gamma_exposure` + `compute_flip_level` (replay script comment: "All Black-Scholes / pure-function logic unchanged"). Replay file received TD-NEW-3 unit fix in same session but **TD-NEW-2 Parts A+B parity is deferred** to S28+ carry-forward — replay used only for Phase 0b retroactive computation which is ~3-4 sessions away. Replay-vs-live parity restoration is P5 S28 carry-forward. |
| **Lesson (codified as CLAUDE.md B20 + B21)** | **B20**: Phase 0 calibration discipline is justified by its first execution. Sign audit was scoped as 2-hour PASS/FAIL on ADR-002 v2 build path; surfaced TWO production bugs (TD-NEW-2 + TD-NEW-3) that had been writing bad data for 3+ days. Without the audit, ADR-002 v2 build (ENH-80, etc.) would have layered new code atop broken foundation. **B21 (companion to TD-NEW-3)**: unit-scale bugs are silent when all consumers sign-only. Both lessons codified for B19 audit-derived patterns going forward. **Additional codification**: latent algorithm fragility surfaces only under input-shape change — TD-NEW-2 was stable for months against stable input; Dhan response-shape change 2026-05-08 (spurious deep-ITM gamma values where previously zero) exposed fragility that prior data never triggered. Defense-in-depth (Part A input filter + Part B algorithm hardening) is the appropriate response class. |
| **Related** | TD-NEW-3 (same-session sibling — net_gex unit standardisation; both surfaced via same audit), TD-097 (S25 precedent for same-session NEW+RESOLVED pattern), TD-101 (S26 second instance of same-session pattern), ADR-002 v2 §Methodology §3 sign-convention audit (mandate that surfaced this defect), CLAUDE.md B20 + B21 + "ADR-002 v2 ACCEPTED" + "TD-NEW-2 RESOLVED" settled-decisions bullets, Assumption Register §D.10.3 (walk-from-ATM canonical flip definition codified from this resolution). |

---

### TD-NEW-3 (closed) — `net_gex` stored in raw rupees ~10³ too large vs operational Crore convention

| | |
|---|---|
| **Filed** | 2026-05-11 (Session 27 — surfaced during cross-comparison of MERDIAN `net_gex` magnitudes against source-material Cr dashboard values during Phase 0a sign-convention audit) |
| **Closed** | 2026-05-11 (Session 27 same-session — fourth same-session NEW+RESOLVED pattern after TD-097 S25 + TD-101 S26 + TD-NEW-2 (this session)) |
| **Closing commit** | `241f943` |
| **Severity at filing** | S2 architectural (silent unit-scale bug across entire gamma engine deployment history; no live-trading impact because all downstream consumers are sign-only; but blocks any cross-comparison to source-of-truth Cr references and blocks every magnitude-consuming future gate from ADR-002 v2 build sequence) |
| **Component** | Three production writer files with duplicate `signed_gamma_exposure` / `signed_gex` implementations: `compute_gamma_metrics_local.py::signed_gamma_exposure()` (live writer line 110), `replay/replay_compute_gamma_metrics.py::signed_gamma_exposure()` (replay writer line 65), `backfill_gamma_metrics.py::signed_gex()` (historical writer line 82). All three return `gamma * oi * spot²` in raw rupees with no `/1e7` Crore conversion. |
| **Discovery path** | During Phase 0a sign-convention audit (TD-NEW-2 sibling), comparison of MERDIAN `gamma_metrics.net_gex` values against source-material dashboard Cr values (e.g., -976 Cr, -14,323 Cr, +13,003 Cr) showed MERDIAN magnitudes in 10¹²-10¹³ range — clearly off by orders of magnitude. Diagnostic Q3 dividing MERDIAN values by `1e7` produced -1,538,435 Cr on 2026-04-28 cycle — still 10² too large vs expected Cr range. Symmetric diagnostic Q4 across symbols revealed NIFTY avg abs `net_gex` = 22.9T, SENSEX = 9.3T; ratio 2.47× ≈ NIFTY/SENSEX lot ratio 25/10=2.5× confirms lot-size signature consistent (rules out symbol-specific bug). Order-of-magnitude expected calculation: `gamma×OI×spot² × 100 / 1e7` for NIFTY ATM (gamma~0.0001, OI~1M aggregate, spot²~5.76e8) produces ~576 Cr per strike ≈ thousands of Cr aggregated. MERDIAN's 22.9T is ~10³ too large vs expected Cr scale, consistent with missing `/1e7` divisor. |
| **Why this was silent** | Audit of every downstream consumer of `net_gex` field in production codebase (grep across active production scripts, filtering out backups/checkpoints): `compute_gamma_metrics_local.py::determine_regime` line 470 (`net_gex >= 0` sign-only); `compute_gamma_metrics_local.py::compute_expansion_probability` line 447 (`if net_gex < 0` sign-only); `backfill_gamma_metrics.py::determine_regime` line 109 (same sign-only check); `detect_structural_manipulation.py` line 491 (`if net_gex <= 0` sign-only); `build_market_state_snapshot_local.py` (pass-through read forwarding to `market_state_snapshots.net_gex`); `backfill_market_state.py` (pass-through); `build_trade_signal_local.py` line 480 (pass-through forwarding to `signal_snapshots.raw.net_gex`); replay equivalents (mirror of live). **Zero magnitude thresholds in entire reader codebase** — every consumer is sign-only or pass-through. Unit-scale wrong by 10³ is therefore invisible to gate logic. Surfaced only via cross-comparison to source-material Cr references during the sign audit. |
| **Root cause** | Standard practitioner convention for net GEX storage is `gamma × OI × spot² × 100 / 1e7` (rupees scaled to Crore for operational legibility). MERDIAN's `signed_gamma_exposure` (and parallel `signed_gex` in backfill) returned `gamma × oi × spot²` raw — missing the Crore conversion. Storage column `gamma_metrics.net_gex` was labeled with implied Cr semantics (operator dashboards expect Cr values; ADR-002 v2 Positioning Landscape specs all values in Cr) but never actually stored as Cr. Bug present since gamma engine first deployment; never surfaced because no consumer checked magnitude. |
| **Fix** | Patch script `fix_td_new_3_net_gex_unit.py` applies `/1e7` to `base` calculation in all three writer files identically. Edit text precisely matched per file (whitespace conventions differ between files — canonical files use `base = gamma * oi * (spot ** 2)` with spaces; backfill uses compact `base=gamma*oi*(spot**2)`). Each file: read with BOM-safe `decode('utf-8-sig')`, EOL detected (compute_gamma_metrics_local.py=LF, replay=CRLF, backfill=LF) and preserved on write via `write_bytes`, `ast.parse()` self-validation before write, `_PRE_TD-NEW-3.py` backup per file, `_PATCHED.py` output for inspection. Note: `compute_gamma_metrics_local.py` already carried TD-NEW-2 Parts A+B at time of TD-NEW-3 patch (sequential application same session); backup chain `_PRE_TD-NEW-2.py` (pre-TD-NEW-2 state) + `_PRE_TD-NEW-3.py` (post-TD-NEW-2 / pre-TD-NEW-3 state) preserves full history. |
| **Validation** | Verification harness `verify_td_new_3_net_gex_unit.py` (mirrors TD-NEW-2 harness pattern — importlib with sys.modules registration for dataclass) runs `compute_net_gex` on real 2026-05-11 04:00:09 IST cycle. **LIVE pre-patch**: `net_gex` = 775,285,881,741 (raw rupees in `gamma_metrics` column). **PATCHED**: `net_gex` = 78,544.84 (Crore from patched compute). Ratio LIVE/PATCHED = 9,870,615 ≈ 10,000,000 (98.7% of expected 1e7, within 5% tolerance — the 1.3% deviation traces to TD-NEW-2 Part A filter rejecting some bad rows in the patched compute that were included in the raw LIVE total, not to unit-conversion math). Both decision criteria PASS: ratio ~1e7, Crore value in operational range (100 < |x| < 1M Cr). Renamed three PATCHED → canonical via PowerShell `del ... && ren ...` sequence. All backups preserved. |
| **Live impact** | Zero — all downstream consumers sign-only. No gate behavior change. Only display/audit value change: `gamma_metrics.net_gex` column from S28 09:15 IST onwards stores Cr (operationally legible numbers in thousands-of-Cr range), dashboards will display sane values, future magnitude-consuming gates from ADR-002 v2 build sequence have correct unit baseline. |
| **Backfill scope** | `gamma_metrics` rows from full deployment history through 2026-05-11 are stored in raw rupees. Going forward (Mon 2026-05-12 09:15 IST onwards) writes Cr. Two unit conventions coexist in the table — a `WHERE ts >= '2026-05-12'` filter or a transformation column would be needed for any historical-Cr cross-comparison. Backfill is **P1 S28 carry-forward** along with TD-NEW-2 broken-window backfill — both bundled (cost amortization) — via custom script reusing patched compute module. Estimated 30-60 min. |
| **Replay parity** | Replay file received this TD-NEW-3 unit fix in same session. TD-NEW-2 Parts A+B replay parity is deferred to S28+ (separate carry-forward) — replay used only for Phase 0b retroactive computation which is ~3-4 sessions away. |
| **Lesson (codified as CLAUDE.md B21)** | Unit-scale bugs are silent when all consumers are sign-only. TD-NEW-3 had been writing 10³-too-large values since the gamma engine first deployed; never surfaced because no gate threshold consumed magnitude. Surfaced only via cross-comparison to source-material Cr references during the sign audit. **B21 rule**: when introducing magnitude-consuming gates, audit existing column unit conventions FIRST against source-of-truth references, before threshold tuning. Otherwise threshold values get fitted against meaningless internal-only numbers and become invisible to external operator interpretation. ADR-002 v2 build sequence (ENH-81 force scenarios in Cr, ENH-84 RR ratio, λ-score) would have ingested wrong-unit baseline if this bug had not been caught pre-build. |
| **Related** | TD-NEW-2 (same-session sibling — flip_level regression; both surfaced via same Phase 0a audit), TD-097 (S25 precedent for same-session NEW+RESOLVED), TD-101 (S26 second instance), ADR-002 v2 §Methodology §3 sign-convention audit + §Schema Crore unit requirement for all scalars, CLAUDE.md B21 + "TD-NEW-3 RESOLVED" settled-decisions bullet, Assumption Register §D.10.4 (Crore canonical unit codified from this resolution). |

---

### TD-NEW-13 (closed) — Python 3.10 `fromisoformat()` rejects non-3/6-digit microsecond fractions

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during P1 broken-window backfill retry after TD-NEW-12 + TD-NEW-4 patches landed; 60/587 cycles failed on AWS Python 3.10) |
| **Closed** | 2026-05-13 (Session 28 same-session — fifth same-session NEW+RESOLVED pattern after TD-097 S25 + TD-101 S26 + TD-NEW-2/3 S27) |
| **Closing commit** | `447634c` |
| **Severity at filing** | S2 (production-blocking for backfill operations; live writes succeeded because timestamps from `result.ts` written by AWS at sub-second precision happen to have exactly 6-digit microseconds; failure mode is cross-version stdlib semantic gap, surfaces at scale on historical-data parse paths) |
| **Component** | `compute_gamma_metrics_local.py::_dte_from_ts()` (helper added in TD-NEW-4 fix); reads `result.ts` ISO timestamp, parses via `datetime.fromisoformat()` to derive as-of date for `dte` payload. |
| **Discovery path** | Post-TD-NEW-12 + TD-NEW-4 patches deployed Local + AWS via git pull (commit `72622a9`), S28 P1 broken-window backfill executed on MERDIAN AWS: `for run_id in failed_run_ids: python compute_gamma_metrics_local.py --shadow --run-id "$run_id"`. 587 run_ids targeted; 527 succeeded, 60 failed with `ValueError: Invalid isoformat string: '2026-05-08T03:45:12.123456789+00:00'` or similar (varied microsecond digits 2-7). Failure pattern: timestamps with microsecond fraction having 2, 4, 5, or 7 digits (NOT 3 or 6) — Python 3.10 stdlib `fromisoformat()` accepts only those two precisions; anything else raises. Local Python 3.12 smoke test had passed on 5 sample rows because the sample happened to include only 3/6-digit microsecond timestamps. |
| **Symptom** | `ValueError: Invalid isoformat string: '...'` on `datetime.fromisoformat(ts_iso)` calls inside `_dte_from_ts`. Backfill cycles fail; rows not written to `gamma_metrics_shadow`; backfill script logs failures. No production impact during live writes because AWS-written `result.ts` timestamps consistently have 6-digit microseconds. |
| **Root cause** | Python stdlib `datetime.fromisoformat()` API is not portable across runtime versions for variable-microsecond-precision input. Python 3.10 stdlib accepts ISO timestamps with microsecond fraction of exactly 3 digits or exactly 6 digits; raises `ValueError` for any other precision. Python 3.12 stdlib accepts arbitrary precision (truncates or pads internally). Supabase serializes PostgreSQL timestamps with variable precision (2-7 digits common, depending on `pg_clock_gettime()` resolution and database default). Local development on Python 3.12 sees no problem; AWS production on Python 3.10 fails for cross-precision timestamps. Cross-version stdlib semantic gap. |
| **Fix** | Patch script `fix_td_new_13_microsecond_normalize.py` modifies `_dte_from_ts()` to regex-normalize the microsecond fraction to exactly 6 digits before calling `fromisoformat()`. Regex pattern: `r'\.(\d+)([+-]\d{2}:\d{2})?$'` — matches the microsecond + optional timezone offset tail; group 1 is the microsecond digits; pad with zeros to 6 if shorter, truncate to 6 if longer; reassemble. Canonical patch pattern: BOM-safe read, EOL detection (LF on file) + preservation, `ast.parse()` self-validation before write, `_PRE_TD-NEW-13.py` backup. Cross-version-tested: pattern works on Python 3.10 + 3.12 identically. |
| **Validation** | Local smoke test: 8 sample timestamps with microsecond fractions of 2, 3, 4, 5, 6, 7 digits + edge cases (no microsecond, no timezone) all parse correctly post-patch. AWS retry on the 60 failed run_ids: 60/60 success. Post-retry `gamma_metrics_shadow` row count matched target (587/587 for broken-window across 2026-05-08 + 2026-05-11). `still_unpatched = 0` on all 4 day/symbol diagnostics. |
| **Lesson (codified as CLAUDE.md B22 + Topology §6.9)** | **B22**: any Python module that parses ISO timestamps from Supabase MUST run cross-version-compatible code paths. Normalize the microsecond fraction to exactly 6 digits via regex pad/truncate before `fromisoformat()`. Verify on AWS, not just Local — Local Python 3.12 smoke testing is necessary but not sufficient. Long-term: align Python versions across Local + AWS. Until then, normalize defensively. **Topology §6.9** codifies the operational rule with affected-symptoms diagnostic shape. Future Supabase-timestamp-parse code paths adopt this normalization helper directly. |
| **Related** | TD-NEW-4 (sibling — both fixes in `_dte_from_ts` helper; TD-NEW-4 added the helper, TD-NEW-13 hardened it for cross-Python), TD-NEW-12 (parent — surfaced during TD-NEW-12 backfill retry phase), CLAUDE.md B22 + "TD-NEW-13 RESOLVED" settled-decisions bullet, Assumption Register §D.11.3 (cross-Python microsecond normalization invariant), Deployment Topology §6.9 (new AWS gotcha). |

---

### TD-NEW-12 (closed) — AWS shadow runner writes to production `gamma_metrics` instead of `gamma_metrics_shadow`

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — discovery during TD-080-adjacent investigation; SQL audit of today's `gamma_metrics` rows showed 2 writes per `(symbol, ts)` bucket per cycle, AWS-written `script_execution_log` rows confirmed `actual_writes: {"gamma_metrics": 1}` — literally writing to production table; `gamma_metrics_shadow` had 0 rows for 13 days) |
| **Closed** | 2026-05-13 (Session 28 same-session — sixth same-session NEW+RESOLVED pattern) |
| **Closing commit** | `72622a9` (compute patch + schema fix) + `de23467` (AWS wrapper patch) |
| **Severity at filing** | S1 (architectural — `gamma_metrics_shadow` table empty for 13 days; `evaluate_shadow_vs_live.py` evaluation cohort non-existent; production `gamma_metrics` rows had race-condition double-writes from Local + AWS competing on UPSERT; downstream readers consume whichever value won the race; behavior is "production data has noise but isn't corrupted because both writers compute the same thing on the same input" — not catastrophic but architectural integrity violated). |
| **Component** | `compute_gamma_metrics_local.py::upsert_gamma_metrics()` (hardcoded `"gamma_metrics"` table name across SELECT for prior + UPSERT for current + ExecutionLog telemetry); `run_merdian_shadow_runner.py` line 479 (subprocess invocation passed no flag to redirect writes to shadow table); `gamma_metrics_shadow` Supabase table (7 missing columns vs production `gamma_metrics` + missing UNIQUE constraint matching the UPSERT on_conflict). |
| **Discovery path** | S28 P0 closed 09:25 IST 2026-05-12 (TD-NEW-2/3 live cycle PASS). S28 mandate then drifted to investigating why TD-080 probe-log monitoring showed AWS-side option-chain ingest succeeding cleanly while signal_snapshots were not appearing — diagnostic SQL revealed AWS shadow runner was producing `script_execution_log` rows with `actual_writes: {"gamma_metrics": 1}` (the production table, not shadow). Cross-check: `SELECT symbol, ts, COUNT(*) FROM gamma_metrics WHERE ts > NOW() - INTERVAL '1 hour' GROUP BY symbol, ts HAVING COUNT(*) > 1` returned 2 writes per `(symbol, minute-bucket)` row for every cycle. Cross-check on shadow: `SELECT COUNT(*) FROM gamma_metrics_shadow WHERE ts > NOW() - INTERVAL '13 days'` returned 0. AWS option-chain ingest writes were therefore being upserted INTO PRODUCTION gamma_metrics, double-writing the same row Local had just written. UPSERT semantics determined which value persisted (typically AWS's because AWS cron at +0 to +30 seconds runs after Local at 0-second cycle boundary). Architectural intent per Topology §6.5 ("shadow ≠ live") silently violated since AWS shadow runner deployment (~2026-04-29). |
| **Symptom** | (1) `gamma_metrics_shadow` Supabase table has 0 rows. (2) `gamma_metrics` has 2 writes per `(symbol, ts)` per cycle since Apr 29. (3) AWS `script_execution_log` rows have `actual_writes: {"gamma_metrics": 1}` — telemetry honest but pointing at production target. (4) `evaluate_shadow_vs_live.py` (the comparison runner) would return zero-result trivially because cohort is empty; not exercised since deployment so no one noticed. |
| **Root cause** | `compute_gamma_metrics_local.py` was written assuming Local-only deployment. Hardcoded `"gamma_metrics"` table name in `fetch_prior_gamma_metrics()` SELECT, `upsert_gamma_metrics()` UPSERT, and `ExecutionLog` telemetry constructor. AWS shadow runner deployment added `run_merdian_shadow_runner.py` as the AWS-side wrapper; the wrapper invokes `compute_gamma_metrics_local.py` as a subprocess but passes no flag to redirect writes. The architectural intent was either (a) refactor `compute_gamma_metrics_local.py` for parameterized target table, OR (b) write a separate `compute_gamma_metrics_local_shadow.py`. Neither was done; the hardcode shipped to AWS via `git pull` and the architectural invariant was silently violated. Compounded by `gamma_metrics_shadow` table schema drift: created via `CREATE TABLE gamma_metrics_shadow LIKE gamma_metrics` (no `INCLUDING ALL` — columns only, no constraints/indexes); 7 columns added to production over time (dte, gamma_zone, otm_oi_velocity, raw, run_type, spot_vs_range, straddle_velocity) never propagated to shadow; UNIQUE(symbol,ts) constraint missing. |
| **Fix** | Two coordinated patches. **Compute patch** (commit `72622a9`) via `fix_td_new_12_shadow_flag.py`: (a) module-level `USE_SHADOW = "--shadow" in sys.argv` sniff before custom argv parser runs (must use sys.argv inspection, not parsed args, because the custom parser raises on unknown flags). (b) `TARGET_TABLE = "gamma_metrics_shadow" if USE_SHADOW else "gamma_metrics"` constant. (c) `fetch_prior_gamma_metrics()` SELECT routed via TARGET_TABLE. (d) `upsert_gamma_metrics()` UPSERT routed via TARGET_TABLE. (e) `ExecutionLog` `expected_writes` dict keyed by TARGET_TABLE + `record_write()` instrumentation honest about actual table. (f) Strip `--shadow` from argv list before custom parser sees it. Also bundled TD-NEW-4 dte-from-result.ts fix into same compute patch commit. **AWS wrapper patch** (commit `de23467`) via `fix_run_merdian_shadow_runner.py`: appends `"--shadow"` to subprocess args list at line 479. **Schema reconciliation** via SQL `ALTER TABLE gamma_metrics_shadow ADD COLUMN IF NOT EXISTS <col> <type>` for each of 7 missing columns + `ALTER TABLE gamma_metrics_shadow ADD CONSTRAINT gamma_metrics_shadow_symbol_ts_key UNIQUE (symbol, ts)` + `NOTIFY pgrst, 'reload schema'` to clear PostgREST schema cache. |
| **Validation** | Local smoke test Path 1 (no `--shadow` flag): `python compute_gamma_metrics_local.py --once --symbol NIFTY` writes 1 row to `gamma_metrics`; `actual_writes={"gamma_metrics": 1}`. Path 2 (`--shadow` flag): same script + `--shadow` writes 1 row to `gamma_metrics_shadow`; `actual_writes={"gamma_metrics_shadow": 1}`. AWS smoke at 07:07 IST 2026-05-13 via `ssm-user` SSH: deploy patched files via `git pull`, manual invocation of `python compute_gamma_metrics_local.py --shadow --once --symbol NIFTY` confirmed write to `gamma_metrics_shadow` table; full shadow runner cycle at 09:15 IST cron 2026-05-13 (live trading day) deferred to S29 first observation. |
| **Live impact** | Reader codebase audit confirmed all consumers of `gamma_metrics.net_gex` + `flip_level` + `gamma_zone` are sign-only or pass-through (zero magnitude thresholds), so the 13-day race-condition double-write window produced no incorrect production decisions — Local and AWS compute the same value on the same input (option_chain_snapshots), so whichever value persisted was correct. `evaluate_shadow_vs_live.py` cohort starts at S29 09:15 IST cron forward (TD-NEW-14-OPTIONAL Q14 in Topology §9 for backfill decision). |
| **Lesson (codified as Topology §6.5 update + §6.8 + Assumption Register §D.11.1 + CLAUDE.md S28 settled-decision bullet)** | (1) **Schema-present-behavior-absent deployment is a silent architectural-invariant violation.** Existence of `gamma_metrics_shadow` table was treated by Topology §6.5 narrative as evidence the architecture was wired; in reality the code did not enforce it. Going forward: for any architectural separation that depends on flag/parameter wiring, verify the wiring is exercised end-to-end at deployment time. Schema-only proxies for separation are insufficient. Smoke test must include `actual_writes` telemetry showing the expected target table. (2) **`CREATE TABLE ... LIKE` without `INCLUDING ALL` is a maintenance trap.** Constraints + indexes + defaults must be propagated separately. Audit every `_shadow` paired table for this gap. Topology §6.8 new gotcha. (3) **`NOTIFY pgrst, 'reload schema'` is mandatory after ALTER.** PostgREST caches schema for performance; does not auto-reload on DDL. |
| **Related** | TD-NEW-4 (bundled into same compute patch commit `72622a9` — different bug, same touch point), TD-NEW-13 (surfaced during TD-NEW-12 backfill retry — Python 3.10 microsecond rejection), Assumption Register §D.11.1 (shadow architecture invariant codified from this resolution), Topology §6.5 (update — narrative-only enforcement → architectural enforcement) + §6.8 (new — shadow schema parity gotcha), CLAUDE.md "TD-NEW-12 RESOLVED" settled bullet, ENH-93 `evaluate_shadow_vs_live.py` (becomes meaningful S29 09:15 IST cron forward). |

---

### TD-NEW-11 (closed) — `merdian_order_placer.py` not catalogued in Deployment Topology

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during TD-NEW-10 investigation; the un-audited process turned out to be intentional but documentation gap was real) |
| **Closed** | 2026-05-13 (Session 28 — closed by S28 doc-close rewrite of `MERDIAN_Deployment_Topology.md`) |
| **Closing commit** | `<S28-doc-close>` (single commit covering all 7 doc-close files including Topology rewrite) |
| **Severity at filing** | S3 (documentation gap; no production impact; affects only Topology reader integrity going forward) |
| **Component** | `MERDIAN_Deployment_Topology.md` §3 AWS-only scripts (missing `merdian_order_placer.py` row); §7.1 AWS cron entries (missing `@reboot merdian_order_placer.py` line); §8.2 MERDIAN AWS runtime artifacts (missing `logs/order_placer.log` path). |
| **Symptom** | Process `merdian_order_placer.py` running on MERDIAN AWS as HTTP server on port 8767 since 2026-04-29 was not documented in any Topology section. Future sessions reading the Topology would not know it exists; future Topology audits would surface it as un-audited (which is exactly what happened in S28 → TD-NEW-10). |
| **Root cause** | Documentation drift — the order placer was deployed during a session that did not include a Topology update commit. Pre-existing register hygiene gap. |
| **Workaround** | None applicable; cosmetic. |
| **Fix** | Three rows added in S28 Topology rewrite: §3 row with full why-AWS-only rationale (Dhan IP whitelisting of AWS Elastic IP `13.63.27.85`; Local's multi-WAN home network has unstable IP); §7.1 `@reboot` cron entries section (also adds `@reboot merdian_signal_dashboard.py` which had the same gap but was less visible); §8.2 log path `logs/order_placer.log`. Plus §1 side-by-side row updated for "Phase 4B order placer (Dhan REST)" with Local=❌ MERDIAN AWS=✅ MALPHA=❌. |
| **Validation** | Topology rewrite verified — §3 row present, §7.1 @reboot block present, §8.2 log path present. Cross-checked with TD-NEW-10 closure that pointed at this same fix. |
| **Lesson** | Catalog-gap TDs are real even when no production impact — they surface in audits as un-audited processes (TD-NEW-10 was the first instance). Filing TD-NEW-11 as a separate S3 even though the work was done in the same session preserves the audit trail showing the gap was identified, scoped, and closed cleanly. |
| **Related** | TD-NEW-10 (filed-in-error parent — the un-audited process discovery surfaced this documentation gap), Deployment Topology §3 + §7.1 + §8.2 + §1 + §9.C (S28 boundary discoveries section). |

---

### TD-NEW-10 (closed) — `merdian_order_placer.py` running deployed but un-audited (filed-in-error after investigation)

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — discovered via `ps aux | grep python` on MERDIAN AWS during S28 drift period investigation) |
| **Closed** | 2026-05-13 (Session 28 same-session as filed-in-error after investigation) |
| **Closing commit** | n/a (no code change; documentation gap closed via TD-NEW-11) |
| **Severity at filing** | S2 (filed as un-audited process — could be benign or could be unauthorized; investigation needed) |
| **Component** | `merdian_order_placer.py` running on MERDIAN AWS as PID 579 (S28 inspection); HTTP server bound to port 8767; spawned via `@reboot` cron entry. |
| **Discovery path** | S28 drift period included broader audit of MERDIAN AWS process state (post-P0 closure). `ps aux | grep python` on MERDIAN AWS showed `python merdian_order_placer.py` running with PID 579. Process was not in Topology §3 AWS-only scripts list; not in §7.1 cron table; not mentioned in `merdian_reference.json` AWS runtime files inventory. Filed as un-audited process at S2 ("unknown process running on production EC2"). |
| **Symptom** | Process running on MERDIAN AWS; not documented; appeared as unauthorized or forgotten infrastructure on first inspection. |
| **Investigation** | (1) Read `merdian_order_placer.py` source on Local (committed to git): HTTP server providing endpoints `/place_order`, `/square_off`, `/order_status`, `/margin` for Dhan Trading API integration; called by Local dashboard's PLACE ORDER button. (2) Read git log: file added in Session 18 / V18G Phase 4B build; intentional Phase 4B Order Placer service. (3) Cross-check Dhan API documentation: Trading API endpoints (vs read-only endpoints) require IP-whitelisted source; MERDIAN AWS Elastic IP `13.63.27.85` is whitelisted; Local's multi-WAN home network IP is not stable enough to whitelist. (4) Cross-check crontab: `@reboot /bin/bash -lc 'set -a; . ./.env; set +a; nohup python /home/ssm-user/meridian-engine/merdian_order_placer.py > logs/order_placer.log 2>&1 &'` confirmed @reboot persistent service. (5) Disposition: not a defect; not unauthorized; deployed as intended in Phase 4B; missing from Topology because the deployment-time Topology update commit was skipped. |
| **Closure** | Filed-in-error at S28. Real issue (documentation gap) split out as TD-NEW-11. The un-audited-process framing was wrong; "Phase 4B service in production since 2026-04-29" framing is correct. |
| **Lesson** | When an unexpected production process is discovered, file as "unaudited" first (S1-S2), investigate, then close as filed-in-error if intentional. Document the absence in whatever register should have caught it; close the documentation gap in the same session. This separates "real defect" from "documentation drift" cleanly. Codified as CLAUDE.md S28 settled-decision bullet (canonical "audited live, confirmed intentional" closure pattern). |
| **Related** | TD-NEW-11 (sibling — documentation gap closed in same session by S28 Topology rewrite), CLAUDE.md S28 settled bullet codifying the closure pattern, Deployment Topology §3 + §7.1 + §8.2. |

---

### TD-NEW-8 (closed) — MERDIAN_WS_Stop cron `pkill -f` ignores SIGTERM; 9 zombies accumulate

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during AWS process audit; 9 ws_feed_zerodha.py zombies + 1 active = 10 instances, ~1.4GB RAM impact) |
| **Closed** | 2026-05-13 (Session 28 same-session via crontab edit) |
| **Closing commit** | n/a (crontab edit, not code commit; logged in `logs/aws_crontab_snapshot_*.txt`) |
| **Severity at filing** | S2 (operational hygiene — accumulating zombies eventually require manual `kill -9 -f ws_feed_zerodha.py` + cron restart; not yet blocking but unsustainable) |
| **Component** | MERDIAN AWS crontab line `02 10 * * 1-5 pkill -f ws_feed_zerodha.py` (15:32 IST WS stop, intended to gracefully stop WS feed at session close). |
| **Discovery path** | S28 AWS process audit during drift period: `ps aux | grep ws_feed_zerodha` showed 10 instances; only 1 currently active (PID from today's WS feed), 9 zombies from prior days. Memory footprint ~140MB per zombie = ~1.26GB zombies + ~150MB active. Crontab inspection showed `pkill -f ws_feed_zerodha.py` (default SIGTERM = signal 15). |
| **Symptom** | 9 zombie processes accumulated over Apr 30 → May 11 (10 trading days). RAM consumption ~1.4GB on t3.small (2GB total). System swap usage rising. WS feed restart at 09:00 IST each Mon-Fri morning was succeeding but the prior day's instance was not exiting on 15:32 IST stop. |
| **Root cause** | `ws_feed_zerodha.py` has no SIGTERM handler installed (`signal.signal(signal.SIGTERM, ...)` absent). Default Python SIGTERM behavior is to interrupt blocking I/O calls; `kiteconnect.KiteTicker.connect()` runs an asyncio event loop that consumes the SIGTERM at the Python interpreter level but the WebSocket I/O continues. Process appears to receive the signal but does not exit. `pkill -f ws_feed_zerodha.py` (default SIGTERM) therefore returns success (signal delivered) but process does not exit. Each subsequent run @ 09:00 IST spawns a new instance; previous zombie remains. |
| **Fix** | Crontab edit: `pkill -f ws_feed_zerodha.py` → `pkill -9 -f ws_feed_zerodha.py` (SIGKILL = signal 9; kernel kills process unconditionally regardless of handlers). Single-character change. Snapshot of crontab pre-edit + post-edit preserved in `logs/aws_crontab_snapshot_20260513_*.txt`. Active zombies cleaned manually: `pkill -9 -f ws_feed_zerodha.py` once + restart cron entry. |
| **Validation** | Post-edit `ps aux | grep ws_feed_zerodha`: zero processes (clean kill of all 10). Post-edit cron entry verified via `crontab -l | grep ws_feed`. Monday 2026-05-19 09:00 IST WS feed start → 15:32 IST WS stop will be the first full lifecycle test; expect zero residual zombies post-15:32. |
| **Live impact** | Zero — WS feed was producing ticks correctly while zombies accumulated; only memory pressure was the side effect. Could have eventually OOM'd the t3.small. |
| **Lesson** | Default SIGTERM is not always sufficient for processes that ignore or mishandle the signal. When `pkill -f <pattern>` is the lifecycle terminator and the target process has no explicit SIGTERM handler, use SIGKILL (`-9` flag). Long-term proper fix: install signal handler in `ws_feed_zerodha.py` that gracefully shuts down KiteTicker before exit; not done because (a) SIGKILL works reliably, (b) WS feed is stateless from MERDIAN's perspective (ticks land in `market_ticks` per-row; mid-shutdown loss of <1s of ticks is acceptable). Filed as candidate enhancement only if signal-handler hygiene becomes important. |
| **Related** | TD-NEW-9 (sibling — `ws_feed_zerodha.py` silent-on-success logging; would help diagnose zombie state from log alone instead of `ps aux`), Deployment Topology §7.1 updated, CLAUDE.md S28 settled bullet. |

---

### TD-NEW-6 (closed) — Local `MERDIAN_WS_Feed_0900` task is dead-stub; pollutes logs

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during Topology audit; Local task firing daily but `market_ticks` writes traced to MERDIAN AWS only) |
| **Closed** | 2026-05-13 (Session 28 same-session via PowerShell `Disable-ScheduledTask`) |
| **Closing commit** | n/a (Task Scheduler state change, durable across reboots) |
| **Severity at filing** | S3 (operational hygiene — Local task fires daily but produces no useful work; `script_execution_log` rows pollute audit trail; occasional mid-session crashes interrupt operator workflow) |
| **Component** | Windows Task Scheduler `MERDIAN_WS_Feed_0900` (~09:00 IST Mon-Fri), wired to `cmd.exe /c run_ws_feed_zerodha.bat` → wraps `ws_feed_zerodha.py`. Per Deployment Topology §2, the actual production WS feed runs on MERDIAN AWS only (Kite browser-TOTP auth flow can't run headless on AWS unless gateway-routed, but the Local invocation was vestigial design that never produced useful ticks). |
| **Discovery path** | S28 Topology audit: cross-check `market_ticks` table for `host`/`source` column to identify which environment writes ticks. All recent ticks tagged with AWS host. Local task `MERDIAN_WS_Feed_0900` confirmed firing daily at 09:00 IST per `script_execution_log` rows but writing zero ticks to `market_ticks` (Local Kite auth path produces ticks for breadth ingest but those go to `market_breadth_intraday`, not `market_ticks`). Local task was vestigial. |
| **Symptom** | Daily firings on Mon-Fri 09:00 IST pollute `task_output.log` + `script_execution_log` with no-op runs that occasionally crashed mid-session (network error mid-WS connection attempt) interrupting operator workflow. |
| **Root cause** | Vestigial design — `MERDIAN_WS_Feed_0900` was added when the WS feed architecture was Local-first; subsequent migration to AWS-first (around Session 18 / V18G) deprecated the Local invocation but the Task Scheduler entry was never disabled. |
| **Fix** | `Disable-ScheduledTask -TaskName MERDIAN_WS_Feed_0900` via PowerShell. Durable across reboots. No code change. Task remains in Task Scheduler for re-enable if needed (e.g., if AWS WS feed becomes unavailable and Local-as-fallback is desired). |
| **Validation** | Post-disable: task state confirmed `Disabled` via `Get-ScheduledTask MERDIAN_WS_Feed_0900`. Mon-Fri 09:00 IST onwards: no new `script_execution_log` rows for `MERDIAN_WS_Feed_0900`. No interruptions to operator workflow. |
| **Live impact** | Zero — Local task was producing no useful ticks before disable. AWS-side WS feed continues unchanged. |
| **Lesson** | Vestigial Task Scheduler entries accumulate across migration boundaries. Audit task list periodically against actual data flow (which environment writes which table). Disable-not-delete preserves rollback option. Codified as CLAUDE.md S28 settled bullet. Topology §7.2 updated with `State=Disabled` annotation. |
| **Related** | Deployment Topology §2 + §7.2 (note about state), Deployment Topology §A.2 (run_ws_feed_zerodha.bat is now wrapper for disabled task), CLAUDE.md S28 settled bullet. |

---

### TD-NEW-5 (closed) — Pine overlay regeneration not chained off `MERDIAN_ICT_HTF_Zones_0845`

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced when operator noticed Pine overlay rendering against stale zones during Mon morning chart prep) |
| **Closed** | 2026-05-13 (Session 28 same-session via bat file edit) |
| **Closing commit** | n/a (bat file edit on Local; not committed to repo as it's environment config) |
| **Severity at filing** | S2 (operational — stale Pine overlay means operator chart prep uses yesterday's zones; signal context wrong) |
| **Component** | `run_ict_htf_zones_daily.bat` (Local Task Scheduler wrapper at 08:45 IST Mon-Fri) was running `build_ict_htf_zones.py --timeframe both` correctly but `generate_pine_overlay.py` (which reads `ict_htf_zones` rows + writes TradingView Pine v6 overlay file to `dashboards/ict_overlay.pine`) was a manual step operator had to remember to run each morning. |
| **Discovery path** | Mon 2026-05-12 morning: operator opened TradingView, noticed Pine overlay rendering zones from 2026-05-09 (Friday) instead of today's fresh zones. Manual run of `python generate_pine_overlay.py --output dashboards\ict_overlay.pine` produced fresh overlay; reload in TradingView showed today's zones correctly. Pattern repeated 2-3 times prior weeks; operator had been working around it but called it out for S28 fix. |
| **Symptom** | Pine overlay file at `dashboards/ict_overlay.pine` not updated after 08:45 IST zone build; remains stale until operator runs `generate_pine_overlay.py` manually. Stale overlay = chart context wrong = signal interpretation wrong. |
| **Root cause** | `run_ict_htf_zones_daily.bat` chained Call 1 (`--timeframe D`) + Call 2 (`--timeframe H`) but no Call 3 for Pine regeneration. Original bat file design treated Pine generation as a separate downstream operation; the dependency was not formalized. |
| **Fix** | Edit `run_ict_htf_zones_daily.bat` to add Call 3: `python generate_pine_overlay.py --output dashboards\ict_overlay.pine` after the two existing build calls. PowerShell `(Get-Content path) -replace 'exit /b 0', "newcontent\r\nexit /b 0" | Set-Content path` pattern (TD-067 / Session 21 lesson — `Add-Content` after `exit /b` makes line unreachable). Config-only change. |
| **Validation** | Manual run of patched bat file: zones built + Pine overlay file regenerated; file mtime updated. Mon 2026-05-19 08:45 IST scheduled run will be the first auto-test; expect Pine overlay file mtime to be 08:45 IST + few seconds. |
| **Live impact** | Zero retroactive impact (manual fallback always available). Forward impact: removes one manual step from operator morning checklist. |
| **Lesson** | Downstream auto-publication artifacts (Pine overlays, dashboards, exported CSVs) should be chained off the upstream data refresh task, not left as manual steps. Codified as CLAUDE.md S28 settled bullet + Topology §A.2 + §7.2 (action column updated). |
| **Related** | Deployment Topology §A.2 (run_ict_htf_zones_daily.bat row updated), Topology §7.2 (MERDIAN_ICT_HTF_Zones_0845 row updated), `generate_pine_overlay.py` (downstream artifact), CLAUDE.md S28 settled bullet. |

---

### TD-NEW-4 (closed) — `compute_gamma_metrics_local.py` `dte` payload from `date.today()` not `result.ts.date()`

| | |
|---|---|
| **Filed** | 2026-05-13 (Session 28 — surfaced during TD-NEW-12 smoke test which exercised backfill code path that production live writes don't stress) |
| **Closed** | 2026-05-13 (Session 28 same-session — bundled with TD-NEW-12 fix into same commit `72622a9`) |
| **Closing commit** | `72622a9` |
| **Severity at filing** | S2 (latent bug; surfaces only on backfill / replay paths where compute is run on historical data; live writes unaffected because result.ts ≈ now within seconds) |
| **Component** | `compute_gamma_metrics_local.py::upsert_gamma_metrics()` — `dte` payload field computed as `(date.fromisoformat(result.expiry_date) - date.today()).days`. |
| **Discovery path** | TD-NEW-12 fix smoke test required exercising the backfill path (running compute on 2026-05-12 data on 2026-05-13). Post-patch row in `gamma_metrics_shadow`: `dte = -1` for NIFTY 2026-05-12 09:15 IST cycle. Expected: `dte = 0` (NIFTY's expiry on that Tuesday was the same day per new NIFTY weekly expiry calendar). Investigation: `result.ts.date() = 2026-05-12`; `date.today() = 2026-05-13`; expiry_date = `2026-05-12`. `(date(2026-05-12) - date(2026-05-13)).days = -1`. Code was using wall clock instead of cycle's actual timestamp. |
| **Symptom** | Backfill / replay computes produce `dte` values that are off-by-N-days where N = days between cycle's actual timestamp and wall clock at run time. Live writes are correct because the gap is sub-second. |
| **Root cause** | `date.today()` returns the wall clock date at the moment the function executes. For live writes this matches the cycle date. For backfill/replay/repair runs, the cycle date is in the past; using `date.today()` produces wrong as-of date. Standard pattern in payload-computation code is to use the result's own timestamp field for any temporal derivation. |
| **Fix** | Module-level helper `_dte_from_ts(result)` added to `compute_gamma_metrics_local.py`. Helper extracts as-of date from `result.ts` (timestamp field) in IST timezone (consistent with rest of MERDIAN's IST convention). Payload line in `upsert_gamma_metrics()` updated to use helper. Canonical patch pattern: BOM-safe read, EOL preservation, `ast.parse()` validation, `_PRE_TD-NEW-4.py` backup. Bundled into commit `72622a9` (TD-NEW-12 + TD-NEW-4 together — both fixes to `compute_gamma_metrics_local.py` to amortize one deploy cycle). |
| **Validation** | Cross-validation 2026-05-12 NIFTY run_id `e2dd1a09-...`: pre-patch `dte = -1` (wrong); post-patch `dte = 0` (correct). Same cycle, same data, helper-derived as-of date matches result.ts.date(). |
| **Live impact** | Zero on live writes (sub-second gap). Backfill / replay corrected forward; pre-S28 backfilled rows have `dte` values from when they were computed (typically wrong by N days), filed as candidate cleanup if any downstream consumer reads `dte` on historical rows (none confirmed — `dte` is mostly diagnostic). |
| **Lesson (codified as Assumption Register §D.11.2 + CLAUDE.md S28 settled bullet)** | All `dte`-class temporal payload fields must be derived from result's own timestamp field, never wall clock. Wall-clock derivation is correct only for live writes where the gap is sub-second; backfill/replay/repair paths produce wrong values silently. Canonical pattern: module-level `_<field>_from_ts(result)` helpers. Future temporal-payload fields adopt same pattern. Surfaced via TD-NEW-12 smoke test which exercised the rarely-stressed code path; live cadence alone is not sufficient validation surface for temporal-payload logic. |
| **Related** | TD-NEW-12 (parent — bundled into same commit; both fixes touch `compute_gamma_metrics_local.py`), TD-NEW-13 (sibling — Python 3.10 stdlib gap in `_dte_from_ts` helper surfaced during backfill retry), Assumption Register §D.11.2 (result-ts-based dte invariant codified), CLAUDE.md S28 settled bullet, Phase 0a + 0b retroactive backfill paths (use this fix). |

---

### TD-101 (closed) — `build_momentum_features_local.py::get_session_open_spot()` unbounded query NULLs `ret_session`

| | |
|---|---|
| **Filed** | 2026-05-10 (Session 26 — discovery via diagnostic SQL after TD-099 closure) |
| **Closed** | 2026-05-10 (Session 26 same-session) |
| **Closing commit** | `3cb84e2` |
| **Severity at filing** | S1 (live trading bug — silently NULLed `ret_session` for 3+ trading weeks; broke ENH-55 momentum opposition gate which became silent no-op for the entire window) |
| **Component** | `build_momentum_features_local.py::get_session_open_spot()` (Local primary pipeline) |
| **Discovery path** | Operator picked TD-054 (broken `ret_30m` research column) at session opening after closing TD-099 as filed-in-error. Diagnostic SQL Q2 (`SELECT raw->>'ret_session' FROM signal_snapshots WHERE ts >= '2026-04-17' AND raw->>'ret_session' IS NULL`) showed NULL on every signal back to 2026-04-17 (3+ weeks; ~5,000 signals across multiple trading days). Q4 confirmed `market_state_snapshots.momentum_features.ret_session` value=NULL but key=present on every row. Q-source (`SELECT COUNT(*) FILTER (WHERE ret_session IS NOT NULL) FROM momentum_snapshots WHERE ts >= '2026-04-17'`) confirmed `momentum_snapshots.ret_session` 100% NULL while `ret_15m` / `ret_30m` / `ret_60m` were 100% populated — bug isolated to ret_session-specific compute path. |
| **Symptom** | `momentum_snapshots.ret_session` NULL on every row 2026-04-17 → 2026-05-10. Propagated to `market_state_snapshots.momentum_features.ret_session` NULL (consolidator forwarded the NULL). Propagated to `signal_snapshots.raw.ret_session` NULL (signal builder reads from market_state_snapshots and forwards). ENH-55 inner condition `if ret_session is not None and abs(ret_session) > 0.0005:` evaluated to False on every signal — gate did not fire opposition block, did not award alignment +10 bonus. Telemetrically identical to "gate not firing because ret_session in neutral band" — no ERROR logs, no contract violations. Silent failure. |
| **Root cause** | `get_session_open_spot()` body: `rows = supabase_select("market_spot_snapshots", filters={"symbol": symbol}, order_by="ts", desc=False, limit=500)`. Returns OLDEST 500 rows in unbounded `market_spot_snapshots` table (no date filter, no time-range filter on the order_by column). Today-date filter inside loop discards all 500. Returns None silently. Downstream `compute_return(curr, None)` returns None. Stored as NULL. Same OI-18 anti-pattern shape as S25 TD-097 dashboard fix (unbounded `order_by`+`limit` returning oldest rows; today-filter inside loop) but in writer-side helper rather than dashboard URL construction. |
| **Why TD-099 grep didn't catch it** | TD-099 audit grep was `requests.get.*SUPABASE.*params` — shape-specific to dashboard's REST URL construction pattern. TD-101's anti-pattern is inside `supabase_select()` helper (Python client wrapper), not at top-level URL construction. Grep couldn't match because the bug is buried inside a helper call. The class of bug is the same; the code shape isn't. |
| **Fix** | Patch script `patch_s26_td101_ret_session.py` (v3 patch canon — `utf-8-sig` decode, byte-write, `ast.parse` validation, idempotency guards, snapshot original). Replaces `get_session_open_spot()` body with bounded query: `today_start_utc_iso` derived from `current_ts.astimezone(timezone.utc)` date; `gte("ts", today_start_utc_iso)` filter; `limit=20` (down from 500 — bounded query needs only first ~20 rows of today to find threshold-crossing); defense-in-depth date filter inside loop preserved (idempotent safety net); threshold 03:35 UTC preserved per ENH-01 / V18G regression history (catches both 09:05 IST Local PreOpen now-disabled and 09:08 IST AWS PreOpen current anchor). Backup `build_momentum_features_local_PRE_S26_TD101.py` preserved. AST OK on Local + AWS post-pull. |
| **Validation** | Smoke test on Friday 2026-05-08 close prices (no Sunday data; replay invocation): NIFTY returned 24,161.3 (correct first-tick-after-09:08 spot), SENSEX returned 77,582.08 (correct first-tick-after-09:08 spot). Sunday 2026-05-10 invocation returned None for both as expected (no data on non-trading day). No errors, no exceptions. **Live verification** deferred to Mon 2026-05-12 first cycle: `SELECT COUNT(*) FILTER (WHERE ret_session IS NOT NULL) / COUNT(*) FROM momentum_snapshots WHERE ts >= CURRENT_DATE + INTERVAL '4 hours'` should approach 100% from second cycle onwards (first cycle may legitimately neutral if open == 09:08 spot). |
| **Live impact (silent-failure window)** | 2026-04-17 → 2026-05-10 (24 trading days, ~5,000 signals). ENH-55 momentum opposition gate (Exp 20 evidence: ALIGNED 60.9% WR vs OPPOSED 38.3% WR, +22.6pp lift) was silent no-op for entire window — both opposition hard-block AND alignment +10 confidence bonus inactive. Production data on the cohort that ENH-55 *would have* gated produced retrospective audit results that directionally falsify Exp 20 hypothesis (see TD-101 cascade impact below). |
| **Cascade impact — ENH-55 disablement (commit `5b94c78`)** | Retrospective audit on the silent-failure window partitioned actionable signals (action ∈ {BUY_CE, BUY_PE} ∧ `trade_allowed=TRUE`) into ENH-55-decision buckets: WOULD_HAVE_BLOCKED (opposed) N=44 79.5% WR; WOULD_HAVE_ALIGNED_BONUS N=35 54.3% WR; NEUTRAL_BAND N=1 0% WR. Sign of lift opposite to Exp 20; magnitude (gap of 25pp between WOULD_BLOCK and WOULD_ALIGN) clears Assumption Register §D.8.3 prospective-parity flag-drift criterion (>15pp). Decomposition: all 44 OPPOSED-but-winning trades are BUY_PE in up-sessions; 43/44 have `ict_pattern=NONE` — pure momentum-driven signals where 15m/30m turn down despite session running up; signature is intraday-rollover-of-up-session-strength = exhaustion / mean-reversion edge. Operator decision: keep TD-101 fix (writer bug unambiguously correct, orthogonal to gating decision) + disable ENH-55 by env flag (the calibration question). `patch_s26_enh55_disable.py` adds `ENH55_ENABLED: bool = os.getenv("MERDIAN_ENH55_ENABLED", "0").strip() == "1"` after `SIGNAL_V4_ENABLED` declaration; modifies inner condition to `if ENH55_ENABLED and ret_session is not None and abs(ret_session) > 0.0005:`. Disables BOTH opposition block AND alignment bonus (same evidence base, symmetric claims falsified together). ENH-53 breadth modifier untouched. Default OFF; reversible. Filed as Assumption Register §D.9 (5 rows D.9.1–D.9.5 + 4 open follow-ups + ADR-009 first-case-study material). |
| **Lesson (codified as CLAUDE.md B19)** | When an OI-18-class bug ships and is fixed at one site, the closure of the class requires (a) URL-spy or runtime-trace verification of every candidate site, not just grep — the grep is shape-specific and misses helper-buried instances; (b) audit must extend to writer-side helpers downstream of the symptom site, not just request-side construction at the symptom site. Filing rule: "same anti-pattern in N scripts" claims require runtime verification before priority assignment. The grep is the trigger to investigate, not the verdict. TD-097 was fixed; TD-099 was filed-in-error; TD-101 was the real instance the grep audit missed. Cost of grep-only audit: 24 days of broken gate before retrospective evidence cascade surfaced it. |
| **Related** | TD-097 (precedent — S25 fix at one OI-18 site), TD-099 (closed filed-in-error S26 — grep audit produced false matches), CLAUDE.md B19 (lesson codification), Assumption Register §D.9 (ENH-55 falsification 5 rows), ENH-55 entry (status COMPLETE PROMOTED ENV-DISABLED). |

---

### TD-099 (closed) — URL-encoding bug pattern audit (filed-in-error after URL-spy verification)

| | |
|---|---|
| **Filed** | 2026-05-10 (Session 25 — sweep filed at S2 HIGH after TD-097 dashboard fix on strength of `grep -rn "requests.get.*SUPABASE.*params"` matching 5 production scripts) |
| **Closed** | 2026-05-10 (Session 26 — closed as filed-in-error after URL-spy verification) |
| **Closing commit** | None (no code changes — diagnostic-only closure) |
| **Severity at filing** | S2 HIGH (presumed silent under-fetch in 5 production scripts, same shape as TD-097) |
| **Severity at closure** | N/A (filed-in-error — no real defect existed) |
| **Component** | Five production scripts: `build_signal_market_path_audit_v1.py`, `build_signal_outcome_audit_local.py`, `build_signal_regret_log_v1.py`, `build_option_execution_outcomes_v1.py`, `premium_outcome_writer.py`. |
| **Verification method** | URL-spy: monkey-patched `requests.get` to print URLs and params before each call, ran each script in dry-run mode, inspected emitted URLs. |
| **Outcome** | All 4 scripts in scope (`build_signal_market_path_audit_v1.py`, `build_signal_outcome_audit_local.py`, `build_signal_regret_log_v1.py`, `build_option_execution_outcomes_v1.py`) emit clean single-`?` URLs with proper encoding (`%2A`=`*`, `%2C`=`,`). 5th script `premium_outcome_writer.py` uses supabase Python client (`supabase.table(...).select(...).execute()`), not raw `requests.get` — different code path entirely; the grep matched a comment or unrelated import line. **No actual instances of TD-097 anti-pattern in any of the 5 scripts.** |
| **Why grep produced false-positives** | Grep regex `requests.get.*SUPABASE.*params` matched both broken TD-097 form (URL with embedded `?col=eq.{val}` AND params dict — the double-encoding bug shape) and standard-correct form (clean URL + params dict only — Python client's normal pattern). Regex is shape-specific to "URL contains params" not "URL is broken". Distinguishing requires either (a) more specific regex matching `URL_with_query_string + params=`, or (b) runtime URL-spy verification. The latter is the canonical verification pattern. |
| **Cost avoided** | ~3 hours of unnecessary patching (5 scripts × ~30min each per S25 estimate). |
| **Lesson (codified as CLAUDE.md B19 + filing rule)** | Before assigning priority to a "same anti-pattern in N scripts" claim, verify with URL-spy or equivalent runtime trace, not grep alone. False-positive grep matches against dashboard-style code patterns are common; the symptom that surfaced the original bug (silent 200-OK with empty results) does not necessarily survive in code-shape grep terms. **Filing pattern going forward:** TD-097-style audit-derived TDs require runtime verification of at least one match before filing the rest. The grep is the trigger to investigate, not the verdict. **Note:** while TD-099 was filed-in-error, the TD-101 instance (real propagation, writer-side helper that the grep couldn't reach by construction) confirms the broader OI-18 propagation concern was correct in principle even if the specific grep targets were wrong. |
| **Related** | TD-097 (precedent), TD-101 (real propagation site the grep missed), CLAUDE.md B19 (lesson). |

---

### TD-079 (closed) — Zone date-expiry vs ICT canon (architectural defect — RESOLVED via ADR-005 implementation)

| | |
|---|---|
| **Filed** | 2026-05-07 (Session 22 — Pine overlay visually missing all >78k resistances surfaced architectural defect) |
| **Closed** | 2026-05-10 (Session 26 — implementation shipped per Phase α Q1 answer locked S25) |
| **Closing commit** | `0731e67` |
| **Severity at filing** | S2 HIGH (architectural defect bleeding signal quality across months of trading) |
| **Component** | `build_ict_htf_zones.py::expire_old_zones()` — applied date-based expiry uniformly across pattern_types regardless of ICT canon. |
| **Symptom (pre-fix)** | Unbreached structurally-relevant W zones (especially BEAR_OB/BEAR_FVG resistances above current spot during a bull market) marked EXPIRED on the 4-weeks-after-source-bar boundary regardless of whether price ever closed through them. Pine overlay visually missing all resistances above 78,000 throughout the 2026-04 → 2026-05 bull leg. Detector still emitted new zones each rebuild but the historical archive of unbreached structure was silently discarded. |
| **Root cause** | `valid_to` model was wrong for OB/FVG. Per ICT canon: zones live until price *closes through them*, not date-expire. PDH/PDL legitimately date-expire (they are daily levels by definition). OB/FVG should expire only on price-breach, never on date. Original code conflated the two pattern type families with uniform date-expiry logic. |
| **Phase α Q1 answer (S25 architecture conversation)** | (a) pure price-based canonical with timeframe-tiered fallback intraday-only — D/W OB/FVG = price-breach only, `valid_to=NULL`; 1H OB/FVG = price-breach OR 1 week (whichever first; tactical fallback to prevent intraday memory pile-up); PDH/PDL = date-expire (unchanged). |
| **Implementation (Session 26)** | Patch script `patch_s26_td079_zone_validity.py` applied 13 surgical replacements AST-validated to `build_ict_htf_zones.py`: (1) D/W OB/FVG zones written with `valid_to=None` (was `week_end + 4 weeks` for W, `bar_date + 1 day` for D); (2) 1H OB/FVG zones written with `valid_to = str(trade_date + timedelta(days=7))` (tactical fallback); (3) PDH/PDL date-expiry logic untouched; (4) `expire_old_zones()` filter widened from `["W","D"]` → `["W","D","H"]` so 1H zones get expired by date when their week is up; (5) `recheck_breached_zones()` becomes the primary status transition for D/W (price-breach detection runs against any ACTIVE zone with `valid_to=NULL`). Backup `build_ict_htf_zones_PRE_S26.py` preserved. |
| **Backfill SQL** | `td079_backfill.sql` applied: `UPDATE ict_htf_zones SET status='ACTIVE', valid_to=NULL WHERE timeframe IN ('W','D') AND pattern_type IN ('BULL_OB','BEAR_OB','BULL_FVG','BEAR_FVG') AND status='EXPIRED' AND zone_high > <breach_test>` with subsequent breach-recheck pass. Revived 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k from EXPIRED → ACTIVE valid_to=NULL. |
| **Validation** | Live rebuild via `build_ict_htf_zones.py --timeframe both` produced 80 zones (47 NIFTY + 33 SENSEX); Pine overlay regenerated via `generate_pine_overlay.py` shows 62 zones (49 HTF + 13 intraday) up from S25's 36; visual confirmation: all major resistances 78k → 86k now displayed on TradingView. |
| **ADR-005 status** | Phase α Q1 answer locked S25, recorded in `docs/decisions/MERDIAN_Decision_Index.md` and `docs/registers/MERDIAN_Assumption_Register.md` §D.7. ADR-005 formal draft (P2 S27 carry-forward) follows the implementation per CLAUDE.md S26 lesson: architecture-defect TDs implementable before formal ADR when (a) Phase α answer is in hand, (b) implementation is reversible (snapshot original), (c) ADR draft follows in dedicated session to capture rationale + alternatives. Doc Protocol v4 Rule 10 ADR-mandatory-before-code is satisfied because the architectural decision was made S25 and recorded in Decision Index + Assumption Register §D.7; the ADR draft is the writeup of an already-made decision. |
| **Side effect** | Pine overlay zone count grew 36 → 62 (+72%); operator-side discretionary use restored to mid-March 2026 baseline coverage of resistance/support stack. |
| **Related** | ADR-005 (formal draft pending S27 P2), Phase α Q1 answer (Decision Index, Assumption Register §D.7), `build_ict_htf_zones.py` snapshot `_PRE_S26.py`. |

---

### TD-097 (closed) — Dashboard pre-open status URL-encoding bug producing 0% accuracy widget on `merdian_live_dashboard.py`

| | |
|---|---|
| **Closed** | 2026-05-10 (Session 25, same-session as discovery and fix) |
| **Closing commit** | (single S25 commit — see session-end commit message) |
| **Fix applied** | Patch script `patch_s25_dashboard_preopen_gap.py` (16,791 bytes; v3 patch canon — `utf-8-sig` decode, byte-write, `ast.parse` validation, idempotency guards). 5 substitutions applied to `C:\GammaEnginePython\merdian_live_dashboard.py`: (1) `get_preopen_status()` URL-encoding fixed by collapsing `requests.get(url, params={...})` into a single fully-encoded URL via `urllib.parse.urlencode()`; (2) `get_gap_status()` new function added (gap-card data path); (3) `collect_data()` wired to invoke `get_gap_status()` alongside existing status getters; (4) `gap_html` builder added; (5) gap card placement HTML inserted between Token card and Pre-open card. Backups preserved as `merdian_live_dashboard_PRE_S25.py` and `merdian_live_dashboard_PRE_S25b.py` (post-FIX1 cosmetic reposition). Two cosmetic post-patch repositionings on the gap-card location. |
| **Validation** | Pre-fix: dashboard pre-open accuracy widget showed `0%` because the URL-encoding double-applied caused Supabase to return zero matching rows (silent failure — endpoint returned 200 OK with empty results). Post-fix on 2026-05-10 evening: dashboard pre-open accuracy widget returned correct historical reading; gap card displays `prev close → prelim gap (16:00 vs 09:08) → final gap (16:00 vs 09:15)` with valid data. Diagnostic scripts `diag_preopen_render.py`, `_v2.py`, `_v3.py` retained in tree for future debugging. |
| **Lesson** | The same `requests.get(SUPABASE_URL + endpoint, params={...})` URL-encoding anti-pattern exists in 5 other production scripts (filed as TD-099). Whenever one occurrence of this bug ships and is fixed, audit all `requests.get` call sites in the codebase for the same pattern — `grep -rn "requests.get.*SUPABASE.*params"` reveals them in seconds. Same root cause as TD-097 will produce silent under-fetch in any of those 5 scripts whenever they run in production. |
| **ENH side-effect** | ENH-96 (gap display widget on dashboard) shipped as same-session side-effect of this investigation — the data was already captured (PreOpen 09:08 row exists in `market_spot_snapshots`); the dashboard just wasn't surfacing it. ENH-96 entry in Enhancement Register tracks the feature beyond the bugfix. |

---

### TD-078 (closed) — TD-070 closure verification incomplete — empirically multi-week BULL_OB lookback may not be firing as designed

| | |
|---|---|
| **Closed** | 2026-05-10 (Session 25) |
| **Closing commit** | (single S25 commit — see session-end commit message) |
| **Fix applied** | No code change required. SQL verification per the proper-fix procedure: `SELECT * FROM ict_htf_zones WHERE timeframe='W' AND pattern_type='BULL_OB' AND source_bar_date='2026-04-13'`. Initial result: empty. Investigation revealed the convention used by `build_ict_htf_zones.py` for W-timeframe `source_bar_date` is the **week-start Monday date** (e.g. `2026-04-13` BULL_OB anchor lives under `source_bar_date='2026-04-13'` ONLY if Apr 13 was a Monday week-start; if the week started on a different Monday, the anchor lives under that Monday's date). Adjusted query to scan W BULL_OB zones across April-May 2026 produced the expected anchor row tied to the correct Monday week-start. TD-070 v2 multi-week unbreached-anchor lookback fires as designed. |
| **Validation** | Adjusted SQL: `SELECT source_bar_date, prior_move, status FROM ict_htf_zones WHERE timeframe='W' AND pattern_type='BULL_OB' ORDER BY source_bar_date DESC LIMIT 20` returned the expected unbreached-anchor row from a Monday in mid-April 2026 with `status='ACTIVE'`. Confirms the Apr-13 sustained-bull-week BULL_OB candidate was correctly captured under the v2 lookback logic, not silently dropped by the dedup. The "missing" original-query result was a schema-convention misunderstanding, not a missed detection. |
| **Lesson** | `ict_htf_zones.source_bar_date` semantics differ by timeframe — for W timeframe it's the Monday week-start, for D it's the bar's calendar date, for 1H it's the hour bucket date. This convention is implicit in `build_ict_htf_zones.py` and not documented elsewhere. Filed for inclusion in System Map §B annotations on `ict_htf_zones` schema. Whenever debugging a "missing" zone row, check the timeframe-aware convention before concluding the row is absent. |

---

### TD-084 (closed) — `backfill_option_zerodha_OI_FIXED.py` UTC/IST timezone bug truncated Kite output to 46 bars per strike

| | |
|---|---|
| **Closed** | 2026-05-07 (Session 22, same-session as discovery) |
| **Closing commit** | uncommitted MALPHA dirty (~/meridian-alpha/backfill_option_zerodha_OI_FIXED.py with .bak_S22 preserved). MALPHA dirty acceptable per S20 directive (Kite gateway only). |
| **Fix applied** | sed-replaced line 184: `dt_ist = bar["date"].replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)` → `dt_ist = bar["date"].astimezone(IST) if bar["date"].tzinfo else bar["date"].replace(tzinfo=IST)`. New logic: if bar["date"] already has tzinfo (it does, from Kite as IST) → astimezone(IST) is a no-op; if tzinfo missing → assume IST (safe fallback). |
| **Validation** | Pre-fix dry-run: 46 bars/strike per SENSEX strike on 2026-05-07. Direct Kite probe via `/tmp/check_sensex_kite.py`: 375 bars confirmed (full session). Post-fix dry-run: 375 bars/strike for both NIFTY+SENSEX. Live run wrote 24,749 rows (NIFTY 8,250 = 22 strikes × 1 expiry; SENSEX 16,499 = 44 strikes × 2 expiries). Verified per-strike via SQL `SELECT strike, expiry_date, option_type, COUNT(*) FROM hist_option_bars_1m WHERE trade_date='2026-05-07' GROUP BY 1,2,3` showing 375 bars/contract uniformly. |
| **Lesson** | Kite returns IST-tagged datetimes for `historical_data` calls — applying `.replace(tzinfo=ZoneInfo("UTC"))` is the canonical timezone bug pattern, never apply to Kite output. The same bug pattern can appear anywhere in the codebase that consumes Kite historical data; audit `grep -rn "tzinfo=ZoneInfo.*UTC.*astimezone(IST)"` to find latent instances. Filed as a CLAUDE.md operational finding. |

---

### TD-072 (closed) — 22-min Task Scheduler gap 13:25-13:47 IST traced to power-source change events

| | |
|---|---|
| **Closed** | 2026-05-06 (Session 21) |
| **Closing commit** | uncommitted (S21 patches still in working tree at S22 close) |
| **Fix applied** | PowerShell loop set `DisallowStartIfOnBatteries=$false` and `StopIfGoingOnBatteries=$false` on 8 market-hours tasks: MERDIAN_Spot_1M, MERDIAN_PreOpen, MERDIAN_IV_Context_0905, MERDIAN_PO3_SessionBias_1005, MERDIAN_Market_Tape_1M, MERDIAN_HB_Watchdog, MERDIAN_ICT_HTF_Zones_0845, MERDIAN_Intraday_Supervisor_Start. |
| **Validation** | Battery flags persist verified at Session 22 pre-market (08:00 IST PowerShell `Get-ScheduledTask | Get-ScheduledTaskSettings`). 08:45 IST cron fired clean Session 22 — no gap re-occurrence. |
| **Lesson** | Windows Task Scheduler default `DisallowStartIfOnBatteries=$true` + `StopIfGoingOnBatteries=$true` is a silent killer for laptop-based production systems. Apply battery flags to every market-hours task at task creation time, not after a gap is observed. Codified as CLAUDE.md operational finding. |

---

### TD-071 (closed) — Stale 2025 zones still showing ACTIVE due to `expire_old_zones()` order bug in `build_ict_htf_zones.py`

| | |
|---|---|
| **Closed** | 2026-05-06 (Session 21) |
| **Closing commit** | uncommitted (S21 patches still in working tree at S22 close) |
| **Fix applied** | `fix_td071_zone_pipeline_order.py` (v3 patch canon). expire_old_zones() rewritten — dropped `.eq("status","ACTIVE")` filter, added `.in_("timeframe",["W","D"])` (H carve-out per operator), added `.neq("status","EXPIRED")` idempotency guard. Pipeline reorder in main(): expire moved from BEFORE upserts to AFTER recheck_breached_zones(). Final order: detect → upsert(ACTIVE) → recheck(price-breach) → expire(date). Backup `_PRE_S21_TD071.py` preserved. |
| **Validation** | Session 21 18:33 IST verification rebuild: 18 stale BREACHED W zones flipped to EXPIRED correctly (the very issue TD-071 was filed to fix). Session 22 08:45 IST cron: 82 zones written, 0 ON CONFLICT errors, expiry transitions correct. |
| **Lesson** | Pipeline ordering matters in idempotent zone management — the order detect → upsert → recheck → expire is the only correct one because: (a) detect produces new candidates; (b) upsert writes ACTIVE for new + leaves existing untouched; (c) recheck flips status based on price action across new + existing; (d) expire flips date-based across all. Reordering any step makes the sequence non-idempotent or produces wrong final state. |

---

### TD-070 (closed) — `prev_move < 0` over-filters BULL_OB candidates in `detect_weekly_zones()` (TD-070 v1 + v2 dedup stack)

| | |
|---|---|
| **Closed** | 2026-05-06 (Session 21) |
| **Closing commit** | uncommitted (S21 patches still in working tree at S22 close) |
| **Fix applied** | TWO-STAGE FIX: **Stage 1 (TD-070 v1):** `fix_td070_weekly_ob_lookback.py` replaced single-bar `prior_move < 0` check in detect_weekly_zones() with 8-week unbreached-anchor lookback via new `_find_unbreached_anchor()` helper (`TD070_LOOKBACK_WEEKS = 8`); symmetric BULL_OB + BEAR_OB; body-based breach test; most-recent-bearish anchor selection; backward-compat preserved. **Stage 2 (TD-070 v2 dedup):** Initial v1 deploy crashed live with Postgres 21000 'cannot affect row a second time' error on upsert ON CONFLICT. Root cause: 8-week lookback can produce multiple zone entries from same source-bar-date → same conflict key (symbol, timeframe, pattern_type, source_bar_date, zone_high, zone_low). Fixed via `fix_td070_v2_dedup.py` adding `_dedup_zones_by_conflict_key()` to collapse zones matching upsert ON CONFLICT key, keeping earliest valid_from. Backups `_PRE_S21.py`, `_PRE_TD070V2.py` preserved. |
| **Validation** | Session 21 18:33 IST verification rebuild: NIFTY 37 W zones + SENSEX 39 W zones = 78 total, zero ON CONFLICT errors. Session 22 08:45 IST cron: 82 zones written cleanly. **Verification gap: TD-078 PENDING** — Apr-13 BULL_OB SQL not yet run to confirm new lookback actually catches sustained-bull-week BULL_OB candidates that prev_move<0 would have rejected. |
| **Lesson** | (a) When relaxing a filter to widen acceptance, ALWAYS verify that the upsert ON CONFLICT key handles the new multiplicity. The 8-week lookback can produce 1-3 zone entries per source bar; ON CONFLICT predicate must dedupe upstream of the upsert. (b) `prev_move < 0` single-bar check was a simplified ICT canon shortcut; canonical ICT allows scanning 1-3 bars back for any bearish candle. The simplification was wrong in sustained bull markets. (c) v3 patch canon (read_bytes+utf-8-sig, normalize CRLF→LF, ast.parse validate, idempotency guard, write_bytes preserve LF, output `_PATCHED.py` then operator-rename) is the only correct way to apply Python source patches on Windows; bare PowerShell string-replacement breaks on encoding/line-endings. |

---

### TD-058 (closed) — Live `detect_ict_patterns.py` emitted zero BEAR_FVG signals across full year

| | |
|---|---|
| **Closed** | 2026-05-03 (Session 17) |
| **Closing commit** | `pending` (Session 17 batch — both detector and runner patches deployed Local + AWS; `_PRE_S17.py` and `_PRE_S17_TD060.py` snapshots preserved) |
| **Fix applied** | `patch_td058_bear_fvg_emission.py` made 5 surgical edits across 2 files: (1) `detect_ict_patterns.py` `OPT_TYPE` dict added `BEAR_FVG: PE`; (2) `DIRECTION` dict added `BEAR_FVG: -1`; (3) `detect_fvg()` body added BEAR predicate `prev.low > nxt.high and (prev.low - nxt.high)/ref >= min_g` mirroring the BULL clause; (4) zone-construction `elif pattern_type == "BEAR_FVG"` block added with `zone_high = bars[idx-1].low`, `zone_low = bars[idx+1].high`; (5) `experiment_15_pure_ict_compounding.py` `build_simulated_htf_zones()` 1H BEAR_FVG mirror added. Originals preserved as `_PRE_S17.py`. |
| **Validation** | Re-run of Exp 15 simulator on full-year cohort: BEAR_FVG signal count went from 0 → 138 across 12 months. Combined NIFTY+SENSEX P&L: ₹11.7L → ₹12.6L (+22.8pp lift on already-strong baseline). Per-pattern T+30m analysis confirmed BEAR_FVG WR 45.7% [37.6, 54.0] (CI spans 50% — coin flip standalone, parallel to BULL_FVG; cluster effect to be measured separately per ENH-90 candidate). Section 17 of `analyze_exp15_trades.py` confirmed bear-side FVG detection now functional across all regimes. |
| **Lesson** | Parallel direction-asymmetric defects exist across the codebase: Session 15 fixed the same pattern in `build_ict_htf_zones.py` (zone-builder side); Session 17 fixed the live-detector mirror. Whenever a direction-asymmetric bug surfaces in one component, audit the parallel component immediately — same author, same era, same blind spot likely applies. Codified as a check pattern in CLAUDE.md Session 17 footer. |

---

### TD-003 (closed) — `experiment_15b` `detect_daily_zones` date type mismatch

| | |
|---|---|
| **Closed** | 2026-04-13 (Appendix V18F follow-on session) |
| **Closing commit** | `<hash>` |
| **Fix applied** | `_daily_str = {str(k): v for k, v in daily_ohlcv.items()}` passed to `detect_daily_zones`. LOT_SIZE corrected: NIFTY=75, SENSEX=20. |
| **Lesson** | `date.fromisoformat()` inside `detect_daily_zones` requires string keys; tracking it as TD vs OI made the lifecycle visible. |

---

### TD-008 (closed) — Enhancement Register ENH-72 status drift

| | |
|---|---|
| **Closed** | 2026-04-22 (same session as discovery) |
| **Closing commit** | Session 2026-04-22 batched [OPS] commit (hash TBD at commit time) |
| **Fix applied** | `fix_td008_enh72_register_flip.py` — performed 5 exact string-match replacements in `MERDIAN_Enhancement_Register.md` (lines at ~114, 152, 1892, 1999, 2064), flipping `PROPOSED` → `CLOSED 2026-04-21`. Appended 1,916-byte closure block after the ENH-72 detail section with commit chain `3a22735..f121fca` and per-script live-validation numbers. File size 114,396 → 116,392 bytes. Backup preserved at `.pre_td008.bak`. |
| **Validation** | `Select-String` for `ENH-72.*PROPOSED` returns zero results post-patch. `Select-String` for `ENH-72.*CLOSED` returns 5+ matches (original 5 flipped locations + new matches in the closure block). |
| **Lesson** | Documentation-drift between the JSON authoritative-state layer and the markdown human-readable register is a real class of bug. The `enhancement_register_delta_<date>.md` delta-file pattern used on 2026-04-21 was an anti-pattern — it deferred the real register update indefinitely. **Going forward:** when an ENH closes, update the unified register in the same commit as the JSON and the session_log. No delta files. |

---

### TD-014 (closed) — `ingest_breadth_from_ticks.py` write-contract instrumentation

| | |
|---|---|
| **Closed** | 2026-04-23 (Session 7) |
| **Closing commit** | `1630726` |
| **Fix applied** | Added `_write_exec_log()` helper and instrumentation at all exit paths of `main()`. Writes one row to `script_execution_log` per invocation with `host='local'`, `exit_code`, `exit_reason` from `chk_exit_reason_valid` enum (SUCCESS / SKIPPED_NO_INPUT / DATA_ERROR), `contract_met` flag, `actual_writes` JSONB. `contract_met` is True iff `coverage_pct >= 50%` AND `market_breadth_intraday` write succeeded. Telemetry write wrapped in try/except so failure cannot crash the pipeline (preserves write-path correctness regardless of telemetry state). |
| **Validation** | Tested 2026-04-23 19:09 IST — `SKIPPED_NO_INPUT` path exercised (market closed, no ticks in 10-min window). Row written to `script_execution_log` with `host='local'`, `exit_code=1`, `contract_met=false`, `actual_writes={market_breadth_intraday:0, breadth_intraday_history:1}`. Production run 2026-04-24 first cycle 09:31 IST exercised SUCCESS path with realistic 291/983 BEARISH breadth, `contract_met=true`. |
| **Lesson** | Write-contract instrumentation on every persistence-side script is non-optional. Without `script_execution_log` rows, the 27-day breadth cascade silent failure had no detection signal. The `coverage_pct >= 50% + write_succeeded` rule is what makes the contract enforceable rather than aspirational. ENH-71 (foundation) + ENH-72 (propagation to 9 critical scripts) + this TD-014 (10th, breadth-specific) form the full instrumentation layer. |

---

### TD-019 (closed) — `hist_spot_bars_5m` pipeline stale since 2026-04-15

| | |
|---|---|
| **Closed** | 2026-04-26 (Session 9) |
| **Closing commit** | `<hash>` (Session 9 commit batch) |
| **Fix applied** | Three changes in one session (override of no-fix-in-diagnosis-session rule logged): (1) Patched `build_spot_bars_mtf.py` with ENH-71 `core.execution_log.ExecutionLog` instrumentation. `expected_writes={"hist_spot_bars_5m": 1, "hist_spot_bars_15m": 1}` (minimum-1 row semantics); try/except wrap → `CRASH` exit reason on unhandled exceptions. (2) Backfilled 42,324 5m rows + 14,440 15m rows via `python build_spot_bars_mtf.py`, 116s, idempotent on `idx_hist_spot_5m_key` / `idx_hist_spot_15m_key`. (3) Registered `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task. Daily 16:00 IST Mon-Fri via `run_spot_mtf_rollup_once.bat` wrapper (mirrors existing MERDIAN task pattern; logs to `logs\task_output.log`). |
| **Validation** | `script_execution_log` shows two SUCCESS rows for `build_spot_bars_mtf.py` on 2026-04-26 (manual run 11:22 IST, smoke-test invocation via Task Scheduler 11:37 IST). Both `contract_met=true`, both `actual_writes={"hist_spot_bars_5m": 42324, "hist_spot_bars_15m": 14440}`, durations 116s and 118s. `Get-ScheduledTaskInfo MERDIAN_Spot_MTF_Rollup_1600` returns `LastTaskResult=0, NextRunTime=2026-04-27 16:00:00`. |
| **Files changed** | `build_spot_bars_mtf.py` (patched in place; `+1841` bytes; backup `build_spot_bars_mtf.py.pre_td019.bak`). New: `run_spot_mtf_rollup_once.bat`, `register_spot_mtf_rollup_task.ps1`, `fix_td019_instrument_build_spot_bars_mtf.py`, `fix_td019_add_sys_import.py`. Updated: `merdian_reference.json` (build_spot_bars_mtf entry status + cadence + scheduled_tasks block + ENH-73 + TD entries), `tech_debt.md` (this entry + TD-023..026), `CURRENT.md` (full rewrite for Session 10), `session_log.md` (one-liner). |
| **Lesson** | (a) "Manual on-demand rebuild" is a data-pipeline anti-pattern — it survives one operator's memory gap by exactly zero days. Every writer to a production table must be both instrumented (ENH-71) and scheduled. (b) Q-A pattern (`script_execution_log.actual_writes::text LIKE '%<table>%'`) is the canonical detector for uninstrumented producers — the absence of a hit IS the smoking gun. Filed as TD-023 to audit-and-patch the rest of the producers. (c) Override of "no fix in diagnosis session" rule was justified by the user this session ("overheads are too much to carry to next") but burned the firebreak that the rule was protecting. The rule pays its rent across multiple sessions; future overrides should be rare and explicit. |

---

### TD-020 (closed) — LONG_GAMMA gate on 2026-04-24 strongly directional day -- diagnosis required before ADR-002 ratification

| | |
|---|---|
| **Closed** | 2026-04-26 (Session 9 reframing; Session 8's prior close was incorrect) |
| **Closing commit** | `<hash>` (Session 9 second-batch commit) |
| **Original Session 8 disposition (NOW SUPERSEDED):** Concluded "gate had no signals to filter; ICT detector silent" and pointed at TD-022 as the real cause. That conclusion was wrong. |
| **Corrected disposition (2026-04-26, Session 9):** The LONG_GAMMA gate DID fire on every 2026-04-24 cycle, exactly as designed. Source path in `build_trade_signal_local.py`: when `gamma_regime == "LONG_GAMMA"`, three things happen in sequence: `cautions.append(...)`, `action = "DO_NOTHING"`, `trade_allowed = False`, **`direction_bias = "NEUTRAL"`**. The gate setting `direction_bias=NEUTRAL` is part of firing, not evidence the gate received nothing. Session 8 saw the gate's OUTPUT (NEUTRAL/DO_NOTHING) and read it as the gate's INPUT (no signals). |
| **Evidence (Session 9 verification):** Q-022-A: 245 signal_snapshots rows on 04-24, all `direction_bias='NEUTRAL'`, all `action='DO_NOTHING'`, `gamma_regime='LONG_GAMMA'` on every row, `net_gex` strongly positive throughout. Q-022-10: gamma_regime breakdown 04-20 to 04-24 confirmed 100% LONG_GAMMA / NO_FLIP coverage on 04-22 / 04-23 (NIFTY) / 04-24 — and on those exact dates, zero PE rows. PE rows fired only in the brief SHORT_GAMMA windows on 04-21 (3 PEs) and 04-23 (35 PEs). |
| **Why this matters:** The gate is mechanically correct. The question of whether it should have fired on a -1.6%/-1.4% directional cascade day is a CALIBRATION question, not a BEHAVIOUR question. ENH-35's 47.7% historical accuracy on LONG_GAMMA cycles validates the gate against a population average; whether the directional sub-population within LONG_GAMMA is mis-served is the question Exp 28/28b investigated (see Compendium). |
| **Files referenced (no code changed for this TD):** `build_trade_signal_local.py` (read-only confirmation of gate logic in the LONG_GAMMA branch). |
| **Validation:** None coded. The disposition is documentary — a corrected reading of existing live data. |
| **Lesson** | When a gate's design includes mutating the inputs it conditions on (here: gate sets `direction_bias=NEUTRAL` AS PART of firing), reading the resulting state to ask "did the gate fire?" is circular. Always trace the gate from its trigger, not from its visible aftermath. Session 8 made the inverse error and chained TD-022 onto a flawed premise; Session 9's deep-dive into source restored the ordering. Going forward, any TD that hypothesises "gate did/didn't fire" must verify by reading source flow, not output state. |

---

### TD-048 (closed) — BEAR_FVG missing across detector pipeline (13-month silent bug)

| | |
|---|---|
| **Closed** | 2026-05-02 (Session 15) |
| **Closing commit** | `8543e08` (Session 15 commit batch — production patches to `build_ict_htf_zones_historical.py` and `build_ict_htf_zones.py`, full historical backfill, signal table rebuild) |
| **Original symptom** | `hist_pattern_signals` contained 0 BEAR_FVG signals over 13 months across NIFTY + SENSEX (2025-04 → 2026-04), despite 1,129 canonical BEAR-FVG 3-bar shapes existing in `hist_spot_bars_5m` over 60d alone, and 46-50% of recent sessions being bear-direction days. `hist_ict_htf_zones` had 0 BEAR_FVG of 35,862 rows pre-fix. |
| **Discovery vehicle** | Exp 50 (FVG-on-OB cluster vs standalone) ran during Session 15. Operator challenged the "0 BEAR_FVG over 13 months" finding as impossible per market structure — sustained bear periods clearly visible on weekly chart Apr 2024-2026, NIFTY -17% Aug 2024 → Mar 2025. Triggered `diagnostic_bear_fvg_audit.py` 5-step audit (S1 distinct pattern_type counts; S2 schema + direction columns; S3 sibling tables; S4 daily candle bear-share; S5 manual canonical 3-bar BEAR_FVG shape scan in `hist_spot_bars_5m`). Audit conclusive on H1 (detector-side asymmetry): 1,129 canonical shapes in 5m bars vs 0 in `hist_pattern_signals` = bug must be detector or signal builder. Subsequently traced: `build_hist_pattern_signals_5m.py` is direction-symmetric (innocent — would emit BEAR_FVG signals if zones existed); bug is upstream in zone builders. |
| **Root cause** | Zone builders had no BEAR_FVG branch in `detect_weekly_zones()` (only BULL_FVG implemented). `detect_daily_zones()` had no FVG detection of either direction. `detect_1h_zones()` (live builder only) had only BULL_FVG. Three locations affected, two scripts. Code review of `build_ict_htf_zones_historical.py` surfaced six bugs ranked S1 (symptom-causing, fixed) / S2 (related but separate, catalogued as TD-049, TD-050) / S3 (cosmetic but real, catalogued as TD-051, TD-052). |
---

### TD-S30-CANDIDATE-1 — Live `compute_gamma_metrics_local.py` regressed on TD-NEW-3 Cr unit conversion (~10^7 factor too large)

| | |
|---|---|
| **Severity** | S2 (consumers using `gamma_concentration` ratio + `flip_distance_pct` are unit-invariant and unaffected; consumers using `net_gex` magnitude thresholds would be biased; data-integrity audit material) |
| **Discovered** | 2026-05-15 (Session 29 — surfaced during full-year `gamma_metrics` backfill parity comparison: backfill `net_gex` is in plausible ±10K-1M Cr range; live `gamma_metrics` rows post-S27 commit `241f943` show ±trillions/quadrillions; ratio matches exactly the `/1e7` Cr conversion that TD-NEW-3 was supposed to apply. Live writer apparently regressed at some point between S27 close commit `241f943` and S29 start.) |
| **Component** | `compute_gamma_metrics_local.py` net_gex unit handling — TD-NEW-3 S27 mandated `/1e7` to convert raw rupees → Crores. Regression site to be identified via `git log -p compute_gamma_metrics_local.py | grep -E '1e7\|net_gex'` between S27 close (`241f943`) and present HEAD. |
| **Symptom** | `gamma_metrics.net_gex` in live cycle rows is ~10^7 too large vs expected Cr-scale magnitudes. Backfill writer (independent reimplementation) writes correct Cr-scale values. Difference is unit conversion, not signal direction. |
| **Root cause** | UNCONFIRMED — needs git log + diff investigation. Hypothesis: a refactor or bundled commit removed the `/1e7` line that TD-NEW-3 added; alternatively the constant is applied but at a wrong point in the compute chain. |
| **Workaround** | Phase 0b consumers in S29 only use `gamma_concentration` (ratio) + `flip_distance_pct` (signed scalar in pct points) — both unit-invariant. Phase 1+ buyer-side consumers that may threshold on `net_gex` magnitude would be biased. Recommend: use backfill values for any analysis comparing magnitudes across history. |
| **Proper fix** | (S30 work) — identify regression commit via `git log -p compute_gamma_metrics_local.py` between `241f943` and current; restore `/1e7` conversion; re-validate via live cycle parity comparison against backfill output. |
| **Cost to fix** | <1 session (git diff + 1-line patch + smoke test). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-05-15 (filed as TD-S30 candidate at S29 close) |
| **Resolution (S36 2026-05-25)** | **CLOSED-MISDIAGNOSIS.** Direct read of the writer function body in S36 first turn (`findstr /N /C:"1e7" backfill_gamma_metrics_to_main.py` + `signed_gamma_exposure` inspection in `compute_gamma_metrics_local.py`) confirmed the `/1e7` Cr conversion was intact at S27 commit `241f943` — the live writer was NEVER regressed. **The residual was historical data unit-mix mis-labeled at S29 close as live-writer regression**, carried forward 7 sessions S29 → S35 without verification of the writer state itself. Three-epoch SQL on `gamma_metrics.net_gex` magnitude-by-week revealed: (a) pre-2026-03 = Cr-correct backfill rows (10⁶ range, consistent with `/1e7` conversion); (b) 2026-03-02→2026-05-04 = raw-rupees ~3,500 rows from the pre-S27 live writer's pre-/1e7-patch window (10¹⁰-10¹³ range); (c) post-2026-05-11 = Cr-correct from S27 `/1e7` patch (commit `241f943` intact at HEAD). Resolution: `python backfill_gamma_metrics_to_main.py --start 2026-03-02 --end 2026-05-04 --mode overwrite --symbol both` (2,850 cycles written; March epoch fully recovered to Cr via overwrite-recompute). April-early-May ~4,300 rows could NOT recompute (chain coverage residual under TD-S35-NEW-1 sparse `hist_option_bars_1m` post-Apr-2026 — vendor delivery boundary; backfill returns 0 chain bars on these dates) — these rows were DELETEd via `DELETE FROM gamma_metrics WHERE ts >= '2026-03-02' AND ts < '2026-05-12' AND ABS(net_gex) > 1e8`. One outlier 2026-05-19 09:55:14 NIFTY -4.7B from a single anomalous cycle DELETEd separately. Post-cleanup verification: every remaining `gamma_metrics` row has `net_gex` magnitude consistent with Cr units (no raw-rupee outliers above `1e8` threshold survive globally). Residual ~4,300 missing-row Apr-early-May window filed as **TD-S36-NEW-1 S3** — closeable in the same recovery window as ADR-013 Breeze fallback graduation (n≥3 successful Breeze-tier backfills accumulated). **Foundational diagnosis-ordering lesson codified in Assumption Register §D.18.1** — when an aggregate-magnitude metric drifts on a derived table, read the writer function body BEFORE inferring from aggregate magnitudes; aggregate magnitudes are downstream of both live-writer state and historical-data unit-mix, and aggregate evidence alone cannot discriminate between live regression and historical contamination. The 7-session carry-forward cost of inverting this order is itself the empirical foundation for the lesson. **Cross-references:** §D.18.1 in Assumption Register; ENH-99 SHIPPED block in Enhancement Register (orthogonal TD closure same session); TD-S36-NEW-1 (residual row gap); CURRENT.md S36 Last session block; CLAUDE.md v1.26 settled-decisions S36 entry. |

---

(End of S29 new TDs section — original Active debt continues below)

| **Fix applied** | Three patches in two scripts: (a) **S1.a** = added W BEAR_FVG branch in `detect_weekly_zones()` mirroring the existing W BULL_FVG branch; threshold `FVG_W_MIN_PCT=0.10%`. (b) **S1.b** = added D BULL_FVG and D BEAR_FVG detection in `detect_daily_zones()`; new constants `FVG_D_MIN_PCT=0.10%` and `D_FVG_VALID_DAYS=5` (D-FVG validity window 5 calendar days, longer than D-OB which retains TD-050's 1-day issue). (c) **S15-1H** = added BEAR_FVG branch to `detect_1h_zones()` in live builder mirroring existing BULL_FVG branch. Patches applied to both `build_ict_htf_zones_historical.py` (S1.a + S1.b) and `build_ict_htf_zones.py` (S1.a + S1.b + S15-1H). |
| **Backfill executed** | (1) `build_ict_htf_zones_historical_PATCHED.py` full backfill: 264 NIFTY + 263 SENSEX trading days = 40,384 rows written to `hist_ict_htf_zones`. Counts: W BEAR_FVG=1,384, W BULL_FVG=2,603 (ratio 0.53 — bull-trend regime, makes sense), D BEAR_FVG=79, D BULL_FVG=84 (ratio 0.94 — symmetric, makes sense). (2) `build_ict_htf_zones_PATCHED.py --timeframe both` live run: 85 zones written to `ict_htf_zones`, 10 ACTIVE per symbol post breach-recheck. (3) `build_hist_pattern_signals_5m.py` (no code change — direction-symmetric verified): `hist_pattern_signals` 6,318 → 7,484 rows. **BEAR_FVG: 0 → 795.** |
| **Files renamed (after backfill verified)** | `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` ARE NOW the patched versions; originals preserved as `build_ict_htf_zones_PRE_S15.py` and `build_ict_htf_zones_historical_PRE_S15.py`. Scheduled task `MERDIAN_ICT_HTF_Zones` (08:45 IST Mon-Fri) automatically uses patched live builder going forward. |
| **End-to-end re-verification** | `diagnostic_bear_fvg_audit.py` re-run post-rebuild: BEAR_FVG count 795 (was 0). NIFTY 60d signals: BULL_FVG 274 / BEAR_FVG 150. SENSEX 60d: BULL_FVG 263 / BEAR_FVG 208. Asymmetry 1.83x (NIFTY) / 1.26x (SENSEX) noted as residual finding — canonical 5m shapes are ~symmetric (NIFTY 562 BEAR / 587 BULL; SENSEX 567 / 575) so signal builder may have a regime-driven bull-skew filter. Filed as TD-056 for investigation. |
| **Bugs intentionally NOT fixed (catalogued as separate TDs)** | TD-049 (D-OB definition non-standard ICT — uses move bar K+1 as OB instead of opposing prior K), TD-050 (D-zone non-FVG validity = 1 day), TD-051 (PDH/PDL `+/-20pt` hardcoded), TD-052 (zone status workflow write-once-never-recompute on historical builder). All four candidates for Session 16 Candidate D. Decision to ship S1 only was deliberate: low-risk symmetric mirror of existing logic, unblocks Exp 50/50b re-run on bidirectional data without forcing definition-change discussions in the same session. |
| **Lessons** | **(a) Verify experiment results against market reality before believing them.** Operator's chart-based challenge to "0 BEAR_FVG over 13 months" was the only thing that surfaced this 13-month silent bug — the zone builder, signal builder, and downstream consumers had been running clean across multiple sessions without anyone noticing the asymmetry. The bug was discoverable by inspection but not by automated test. **(b) Full-file PATCHED.py copies + post-verification rename is the safe deploy pattern (vs in-place edit).** Allows dry-run, real-run, end-to-end verification, and rollback as discrete steps; rollback is one rename. Operator preferred this pattern over `.bak` files. **(c) When a known-incomplete detector (S1.a / S1.b) is being patched, run a code review to surface what else is wrong before patching** — the six-bug catalogue (TD-049/050/051/052 + S1.a + S1.b) emerged from one review pass; spreading discovery across multiple sessions would have been more expensive. **(d) Direction-symmetry verification on the signal builder before patching the detector** — by confirming `build_hist_pattern_signals_5m.py` was innocent first, Session 15 avoided the trap of patching the signal builder symptomatically while leaving the zone-builder root cause intact. The 5-step audit S5 (canonical shape scan) was the test that proved this. |

---

### TD-061 (closed) — Task Scheduler entry points spawn visible console windows (S29 RESOLUTION)

| | |
|---|---|
| **Severity at close** | S2 → RESOLVED |
| **Discovered** | 2026-05-03 (Session 17) |
| **Closed** | 2026-05-14 (Session 29 firefighting — full closure after S17/S18 partial closure was insufficient; body-state-vs-footer-claim divergence documented as Doc Protocol v4 candidate Rule N input) |
| **Root cause confirmed** | Task action ran `python.exe` (console) instead of `pythonw.exe` (no-console). Earlier sessions migrated 4/19 tasks; S29 completed the remaining 9 migrations + hardened settings on 18/19 tasks. |
| **Fix applied** | (1) `migrate_to_pythonw.ps1` (v2 — v1 abandoned due to regex shell-redirection capture bug). Two-phase application: phase 1 hit 13 .bat-wrapping tasks via regex-extract-py-script-path approach; v1 captured shell redirection metacharacters as `pythonw` args (caught before -Apply by dry-run review); v2 whitelisted argument shapes + blacklisted shell metas. Phase 2 (after operator pasted 4 wrapper-internal contents) dropped 4 PowerShell/.bat wrappers that called `pythonw.exe` internally — re-pointed tasks at the `pythonw.exe` direct invocation. (2) New `run_ict_htf_zones_daily.py` Python orchestrator replaces `.bat` for ICT_HTF_Zones_0845 (the 3-step chain with rc-fold + banner format couldn't collapse to single pythonw call). `sys.executable` propagation ensures pythonw all the way down. (3) Settings tightened on 18/19 tasks: `Hidden=$true + MultipleInstances=IgnoreNew + ExecutionTimeLimit=30min + battery flags`. |
| **State at close (S29 audit final)** | **13 of 19 actions on pythonw.exe** (was 4 at S29-start). **18 of 19 settings tightened.** Residual 5 window-flash sources are low-frequency: `Intraday_Supervisor_Start` (08:00 + logon — multi-trigger XML quirk in PowerShell `Set-ScheduledTask` blocked the single settings update; documented as known limitation), `Watchdog` (interval, PowerShell so can't migrate to pythonw), `Intraday_Session_Start` (cadence pending operator verification — newly-discovered S29 task), `Dhan_Token_Refresh` (once-per-morning), `Market_Tape_1M` (broken since 2026-04-07; firing daily as Ready but failing 401). |
| **Backups** | `backups\scheduler\20260514_184211\*.xml` (18 task XMLs from v1 -Apply run); `backups\scheduler\20260514_190443\*.xml` (4 task XMLs from phase-2 wrapper-drop run). Rollback path: `Register-ScheduledTask -Xml (Get-Content <backup>.xml -Raw) -TaskName <name> -Force`. |
| **Orphaned wrappers (cleanup pending)** | `run_ict_htf_zones_daily.bat`, `run_eod_breadth_refresh.ps1`, `run_iv_context_once.ps1`, `run_po3_session_bias_once.bat` — kept on disk unreferenced from Task Scheduler. Delete in cleanup pass after 1 week of new-config stability (operator action 2026-05-21+). Filed in System Map §A.9. |
| **Lessons** | **(a) TD body-state must match footer-claim** (Doc Protocol v4 candidate Rule N) — S18 footer claimed TD-061 RESOLVED; body remained Active; S23 audit confirmed only 4/15 migrated; the discrepancy was visible in Topology §7.2 but never reflected back. **(b) Regex capture of arbitrary trailing tokens unsafe in command-injection contexts** (B28) — v1 of `migrate_to_pythonw.ps1` greedily captured `>>`, `2>&1`, etc. as pythonw args. **(c) Wrapper-to-direct migration: comments vs code state alignment** — when retiring a `.bat`/`.ps1`, document orphaning explicitly so future operators don't grep-discover the stale file as if it were canonical. **(d) Single-trigger `Set-ScheduledTask` reliability ≠ multi-trigger** — multi-trigger tasks (Weekly + AtLogon on Supervisor) require full XML re-register instead. |
| **Related** | TD-063 (single-instance enforcement — bundled into same `migrate_to_pythonw.ps1` settings pass; both RESOLVED same session), CLAUDE.md B24 + B25 + B26 + B27 + B28 (S29 anti-pattern lines), Topology §7.2 (19-task table rewrite S29), CLAUDE.md S29 settled-decisions footer entry. |

---

### TD-063 (closed) — Single-instance enforcement missing on Task Scheduler tasks (S29 RESOLUTION)

| | |
|---|---|
| **Severity at close** | S3 → RESOLVED |
| **Discovered** | 2026-05-03 (Session 17) |
| **Closed** | 2026-05-14 (Session 29 firefighting — bundled into TD-061 settings pass) |
| **Root cause** | Default `MultipleInstances=Parallel` allowed new instance to attempt start even when previous still running, leading to `2147946720` errors observed in S17. |
| **Fix applied** | `MultipleInstances=IgnoreNew` applied on 18/19 MERDIAN_* tasks via `migrate_to_pythonw.ps1` v2 settings pass. Skipped new fire if previous still running; symptom of TD-062 stuck-process accumulation is now self-clearing on each successive trigger. |
| **State at close** | 18/19 tasks hardened. The 1 failure: `MERDIAN_Intraday_Supervisor_Start` retains loose settings due to multi-trigger XML quirk in PowerShell's `Set-ScheduledTask -Settings <obj>` (Weekly Mon-Fri + AtLogon = two triggers, `Set-ScheduledTask` couldn't apply settings cleanly). Workaround documented in Topology §7.2 Note: build full `Register-ScheduledTask` XML + `Force` overwrite, or skip settings-only update for multi-trigger tasks. Filed as TD candidate for next Task Scheduler touch. |
| **Backups** | Same as TD-061 (bundled). |
| **Related** | TD-061 (bundled — same migration script + same session closure), TD-062 (stuck-process root cause — IgnoreNew makes TD-062 self-clearing rather than ever-accumulating; TD-062 root cause investigation remains open but is now less urgent). |

---

### TD-NEW-A (closed) — `market_ticks` retention runaway → 62 GB bloat → INSERT timeouts (S29 IN-FLIGHT RESOLUTION)

| | |
|---|---|
| **Severity at close** | S1 → RESOLVED |
| **Discovered** | 2026-05-14 (Session 29 firefighting — during Incident §1 diagnosis of breadth cascade) |
| **Closed** | 2026-05-14 (Session 29 same-session — seventh same-session NEW+RESOLVED pattern after TD-097 S25 + TD-101 S26 + TD-NEW-2/3 S27 + TD-NEW-4/5/6/8/12/13 S28) |
| **Discovery trail** | Initial hypothesis was simple token-stale (matched 2026-04-22 pattern); operator ran token-refresh twice with no improvement. Restart of `ws_feed_zerodha.py` revealed `Supabase write error 500: {"code":"57014","message":"canceling statement due to statement timeout"}` in feeder log — the smoking gun for second root cause. Table size query: 62 GB total (22 GB heap + 40 GB indexes). `cron.job_run_details` query showed 10 consecutive `delete-old-market-ticks` (jobid 45) failures since at least 2026-04-30 with same statement_timeout error. Failed deletes accumulated unbounded; at ~62 GB even bulk INSERTs began exceeding statement_timeout, producing the cascade. |
| **Root cause** | Two-tier: (A) original schedule `30 14 * * 1-5` + horizon `2 days` produced a worst-case DELETE workload that, once table crossed a threshold, exceeded statement_timeout. (B) `cron.job_run_details` failures are invisible by default (no MERDIAN telemetry polls it; filed as TD-NEW-B). The combination meant pg_cron was silently failing for 14+ weekdays before downstream consumer (`ws_feed_zerodha.py`) noticed. |
| **Fix applied** | (1) `pkill -9 -f ws_feed_zerodha.py` to release write locks. (2) `TRUNCATE public.market_ticks` (62 GB → 856 kB in <1s; DDL primitive — DELETE itself would have timed out at this size). (3) `cron.unschedule(45)` retired the broken job. (4) `cron.schedule('prune-market-ticks', '*/30 * * * 1-5', $$DELETE FROM public.market_ticks WHERE ts < now() - interval '1 hour'$$)` created jobid 46. (5) Restart `ws_feed_zerodha.py`; verified next INSERT successful + no 500 errors in log. |
| **Design rationale (new schedule)** | Cadence increased 1/day → 1/30min (worst-case DELETE workload now ~30 min of accumulation ≈ ~1 GB, well inside statement_timeout). Horizon shortened 2 days → 1 hour (breadth ingest reads only last 10 min; 1-hour horizon caps table size at ~1 GB during active session). Active Mon-Fri = 1-5 unchanged (holiday no-feed produces no DELETE workload either way). |
| **Cost incurred** | `market_breadth_intraday`: 0 rows for 2026-05-14 (not recoverable — 10-min rolling window is ephemeral). `signal_snapshots.breadth_regime`: NULL for all 697 signals 2026-05-14 (replay reads `market_breadth_intraday` so also not recoverable). Operator hours: ~3h incident response. Trading: degraded signals 09:15 onwards; hybrid discretionary process compensated, no live trades on bad data. |
| **Lessons** | **B25 (TRUNCATE vs DELETE on bloated tables)** — for tables under statement_timeout pressure, DELETE itself is timing out; TRUNCATE is O(1) DDL primitive. **B26 (pg_cron failures invisible by default)** — `cron.job_run_details` is not polled; needs alerting layer (TD-NEW-B). **Compound-incident diagnostic discipline** — operator pattern-matched first hypothesis (token-stale) and tried fix twice with no improvement; the third diagnostic step (log tail of restarted process) revealed the independent second root cause. Codified into B24 + B25 + B26 + operational findings in CLAUDE.md S29 section. |
| **Related** | OI-12 RE-RESOLVED block in `MERDIAN_OpenItems_Register_v7.md` (same fix; OI-12 was originally closed 2026-04-14 with the now-failed jobid 45; permanent closure marker preserved per no-crunch but new closure block records the structural redesign). TD-NEW-B S1 (the alerting-layer fix for the silent-pg_cron-failure failure class), TD-NEW-C S2 (`ws_feed_zerodha.py` silent on Supabase 500 — the symptom-side counterpart). Topology §6.10 + §6.11 new gotchas. `CASE-2026-05-14-breadth-cascade-token-and-bloat.md` full incident chronology. |

---

### TD-NEW-I (closed) — Daily audit thresholds 370 → 365 (S29 RESOLUTION)

| | |
|---|---|
| **Severity at close** | S3 → RESOLVED |
| **Discovered** | 2026-05-14 (Session 29 firefighting) |
| **Closed** | 2026-05-14 (Session 29 same-session — eighth same-session NEW+RESOLVED pattern) |
| **Root cause** | `merdian_daily_audit.py` thresholds `spot_bars_per_symbol_min: 370` + `market_spot_snapshots_per_symbol: 370` were too tight against 98% coverage reality. 2026-05-14 audit returned `OVERALL: FAIL` on 367/375 NIFTY and 366/375 SENSEX (~98% coverage). Operational reality: 375 bars/day theoretical maximum (375 minutes 09:15→15:29 inclusive at 1-min cadence) but typical day has 2-5 known gap minutes from operational timing windows (writer cycle micro-jitter, Dhan endpoint stress, etc). |
| **Fix applied** | `patch_s29_td_new_i_j_v2.py` (v1 abandoned — regex undercaught threshold sites). 2 single-line changes in `merdian_daily_audit.py`: `spot_bars_per_symbol_min: 370 → 365`, `market_spot_snapshots_per_symbol: 370 → 365`. AST-validated. Backup `merdian_daily_audit_PRE_S29_TD_NEW_I_J_V2.py`. |
| **Verification** | 2026-05-15 daily audit should return PASS on the affected thresholds (1-day forward verification). Filed as auto-verification in `CASE-2026-05-14-spot-gap-backfill.md` §8 forward verification list. |
| **Lessons** | Audit thresholds should match operational reality, not theoretical maximum. ~98% coverage with known intra-day gap windows is healthy; 370 was a research-time threshold (when system was fresh and gap-free); 5 years of operational data shows 365 is the right baseline. Periodic threshold-vs-reality calibration pass is operationally healthy. |
| **Related** | TD-NEW-J (= TD-083; bundled into same patch script `patch_s29_td_new_i_j_v2.py`), `CASE-2026-05-14-spot-gap-backfill.md`. |

---

### TD-NEW-J (closed) — `capture_spot_1m_v2.py` emits 'OUTSIDE_MARKET_HOURS' against closed-set enum (= TD-083, S29 RESOLUTION)

| | |
|---|---|
| **Severity at close** | S3 → RESOLVED (also closes TD-083 as same root cause) |
| **Discovered** | 2026-05-07 (Session 22 — filed as TD-083); re-discovered S29 during script_execution_log attribution analysis showing daily false-alarm CRASH rows |
| **Closed** | 2026-05-14 (Session 29 — ninth same-session NEW+RESOLVED pattern; TD-NEW-J + TD-083 unified closure) |
| **Root cause** | `capture_spot_1m_v2.py` v2.1 added clean exit reasons (`'OUTSIDE_MARKET_HOURS'`, `'NO_DATA'`) that didn't exist in the `chk_exit_reason_valid` closed-set enum constraint. INSERT silently fails or gets reclassified as CRASH; daily false-alarm Telegram alerts. |
| **Fix applied** | `patch_s29_td_new_i_j_v2.py` made 2 surgical changes: (a) call-site L346: `"OUTSIDE_MARKET_HOURS"` → `"OFF_HOURS"` (matches enum's closed set); (b) docstring L36: `"OUTSIDE_MARKET_HOURS"` → `"OFF_HOURS (was OUTSIDE_MARKET_HOURS pre-TD-NEW-J 2026-05-14)"` — preserves grep-discoverability of the old name. Patch v1 was abandoned because its regex undercaught the docstring change site + risked docstring breakage. AST-validated. Backup `capture_spot_1m_v2_PRE_S29_TD_NEW_I_J_V2.py`. |
| **Verification** | 2026-05-15 forward: 0 CRASH rows attributable to `OUTSIDE_MARKET_HOURS` in `script_execution_log` from `capture_spot_1m_v2.py`. |
| **Lessons (B23 evolution)** | When a code-side string literal is renamed, the prose-side references must be updated in lockstep OR the prose rewritten to preserve grep-discoverability of the old name (the `(was X pre-TD-Y date)` pattern). v1 of the patch chose to leave docstring untouched; v2 chose the annotated rewrite. Future patch scripts should default to the annotated rewrite. |
| **Related** | TD-NEW-I (bundled into same patch script), TD-083 (same root cause; closed simultaneously). |

---

*MERDIAN tech_debt.md v1 — created concurrent with CLAUDE.md and Documentation Protocol v3. Updated Session 18 (2026-05-04): TD-061/063/056/065 RESOLVED, TD-062 PARTIAL (heartbeat foundation), TD-064/066/067 NEW (migrated from closed OpenItems Register). Updated Session 28 (2026-05-13): TD-NEW-4 + TD-NEW-5 + TD-NEW-6 + TD-NEW-8 + TD-NEW-12 + TD-NEW-13 RESOLVED same-session (six NEW+RESOLVED, fifth/sixth same-session pattern after TD-097 S25 + TD-101 S26 + TD-NEW-2/3 S27); TD-NEW-7 (S1, MALPHA→MERDIAN AWS Zerodha token automation) + TD-NEW-9 (S2, ws_feed silent-on-success heartbeat) NEW pending S29+; TD-NEW-10 CLOSED filed-in-error (merdian_order_placer.py confirmed intentional Phase 4B); TD-NEW-11 CLOSED documentation gap (Topology §3 + §7.1 + §8.2 updated in same-session S28 doc-close rewrite). **Updated Session 29 (2026-05-14 firefighting + 2026-05-14→2026-05-16 build): TD-061 + TD-063 RESOLVED (both were footer-claimed-RESOLVED at S18 with body-state Active — body-state-vs-footer-claim divergence; S23 audit confirmed only 4/15 migrated; S29 audit found 19 tasks and only 4/19 on pythonw at S29-start; S29 firefighting completed via `migrate_to_pythonw.ps1` v2 — 13/19 pythonw + 18/19 Hidden+IgnoreNew; new orchestrator `run_ict_htf_zones_daily.py` replaces `.bat`). TD-083 RESOLVED via TD-NEW-J unified closure (`capture_spot_1m_v2.py` exit_reason `'OUTSIDE_MARKET_HOURS'` → `'OFF_HOURS'` via `patch_s29_td_new_i_j_v2.py`). TD-080 PROMOTED to S1 RECURRING (3rd documented occurrence: S22 + S28 + S29; ENH spec for Dhan 429 retry layer + circuit breaker is P0 carry-forward to S30). TD-094 RECLASSIFIED-STALE (vendor data replaced broken S22 Kite backfill; OI populated 99.9%; unblocks Phase 0b gamma-context dimensions). NEW + RESOLVED same-session (ninth/tenth same-session pattern): TD-NEW-A S1 (`market_ticks` 62GB bloat → INSERT timeouts → 6h breadth cascade — TRUNCATE + new cron jobid 46), TD-NEW-I S3 (audit thresholds 370 → 365), TD-NEW-J S3 (= TD-083). NEW + CLOSED in documentation: TD-NEW-E S3 (Topology §7.2 17→19 staleness — closed via §7.2 rewrite), TD-NEW-F S2 (`runbook_update_kite_flow.md` Step 2d missing — closed via 5 runbook edits). NEW pending S30+: TD-NEW-B S1 (`pg_cron` health-check daemon — alerting layer for cron.job_run_details failures), TD-NEW-C S2 (`ws_feed_zerodha.py` silent on Supabase 500 — merge with TD-NEW-9), TD-NEW-D S2 (`ws_feed_zerodha.py` log timestamps mislabeled UTC-as-IST), TD-NEW-H S2 (`backfill_volatility_snapshots.py` NULL `expiry_date` schema violation). TD-S30-CANDIDATE-1 S2 (live `compute_gamma_metrics_local.py` regressed on TD-NEW-3 Cr unit — net_gex in raw rupees ~10^7 too large vs backfill; investigate S30). Five same-session NEW+RESOLVED in single session (TD-NEW-A + TD-NEW-I + TD-NEW-J + TD-NEW-E + TD-NEW-F) — new session record. Update inline as items are added/closed; commit with `MERDIAN: [OPS] tech_debt — <action>`. **Updated Session 30 (2026-05-17 — diagnostic + production patch session): 5 NEW TDs filed pending S31+ at top of Active section — TD-S30-NEW-3 S1 (OB attachment broken at signal-builder layer; highest-leverage S30 finding; 4,882 BULL_OB zone-touches → 0.5% attached / 3,139 BEAR_OB → 0% attached; detection correct, defect at `enrich_signal_with_ict()` or callers; S31 P0 investigation), TD-S30-NEW-4 S2 (DTE=0 cohort N too small for verdict), TD-S30-NEW-5 S2 (gate stack inversion on gamma/breadth/vix — three gates suppress positive-EV buckets; per-gate dedicated study queued), TD-S30-NEW-6 S3 (replay_build_trade_signal.py lacks ENH-88 per ADR-008 header line 15 attestation; ~30 min patch), TD-S30-NEW-7 S3 (hold-time bucket study scope — N≥100 per exit-bucket measurement; live cohort shows T+10-20m optimal vs T+30m Compendium-settled). TD-S30-CANDIDATE-1 (S29 carry-forward, live `compute_gamma_metrics_local.py` Cr unit regression) remains un-actioned at S30 close; carries forward as S31 P0_PRIMARY (not retracted, not investigated). 0 TDs CLOSED Session 30; 1 carry-forward un-actioned. ENH-76/77/88 + tier mult ENV-DISABLED via commit `2604fc2` per D.13.1 cohort-translation general principle codification. **Updated Session 35 (2026-05-24 — TD-S34-NEW-4 closure + dual-source chain reader + Breeze surgical fill + ADR-012 SL writer ship): TD-S34-NEW-4 CLOSED-MECHANICAL — Resolution block appended; 81% zone-primitive recovery via ENH-106 v8/v8.1/v8.2 + Breeze 04-16 surgical fill; structural residual carries forward as TD-S35-NEW-1. 4 NEW TDs filed pending S36+ at top of Active section: TD-S35-NEW-1 S2 (HOCS strike-coverage structural limit — `ingest_option_chain_local` ATM±N capture window); TD-S35-NEW-2 S1 (pre-Apr-2026 chain vendor uncatalogued — critical institutional knowledge at risk, bus-factor-of-one); TD-S35-NEW-3 S4 (SENSEX Breeze symbology `stock_code="BSESEN"` not "SENSEX"); TD-S35-NEW-4 S3 (`build_ict_primitives.py upsert_outcomes` is INSERT-only on existing rows — schema column adds require manual DELETE before recompute populates new columns). 1 TD CLOSED in resolution block (TD-S34-NEW-4); 0 same-session NEW+RESOLVED this session. 7 TDs carry-forward un-actioned. ADR-012 IMPLEMENTED via writer v9 (5 sl_* columns + spot-anchored SL evaluation block); single-cell n=5 verified; full validation cohort gated on S36 TRUNCATE + full recompute. ADR-013 PROPOSED (Breeze canonical historical backfill source). ENH-109 PROPOSED (Breeze rollingoption + get_historical_data_v2 graduation). MERDIAN AWS instance ID drift surfaced (memory `i-0e60e4ed9ce20cefb` → console `i-0878c118835386ec2`; reconcile at S36). **Updated Session 36 (2026-05-25 — TD-S30-CANDIDATE-1 closed-misdiagnosis + TD-080 closed via ENH-99 SHIPPED + 4 new TDs filed): TD-S30-CANDIDATE-1 CLOSED-MISDIAGNOSIS — Resolution block appended; live `compute_gamma_metrics_local.py` writer was NEVER regressed (S29 close mis-labeled historical data unit-mix as live regression; 7-session carry-forward cost from inverted diagnosis order, codified §D.18.1). March epoch recovered via overwrite-recompute (2,850 cycles); April-early-May ~4,300 rows DELETEd as confirmed gaps (TD-S36-NEW-1 residual). TD-080 CLOSED via ENH-99 SHIPPED — Resolution block appended; failure-shape diagnosis Mode A 429 / Mode B 401 SOLVED-UPSTREAM-S29 / Mode C orphan RUNNING; Components 1+2+3 shipped (retry predicate + orphan janitor + telemetry); Component 4 audit thresholds DEFERRED. **MERDIAN_Orphan_Janitor** Task Scheduler task registered weekly Mon-Fri 09:14 IST (task count 19 → 20). 4 NEW TDs filed pending S37+ at top of Active section: TD-S36-NEW-1 S3 (gamma_metrics Apr-early-May row gap — closeable in ADR-013 Breeze fallback cycle); TD-S36-NEW-2 S3 (`MERDIAN_Dhan_Token_Refresh` not instrumented to `script_execution_log` — straightforward 30-min retrofit); TD-S36-NEW-3 S4 (`dhan_token_probe_log` forward-only from 2026-05-10 — documentation-only gap); TD-S36-NEW-4 S3 (`script_execution_log.duration_ms` int4 — clamp-at-write-time operational pattern works, int8 migration is proper fix). 2 TDs CLOSED in resolution blocks; 0 same-session NEW+RESOLVED this session (S36 was closure-and-shipping, not discovery). 12 TDs carry-forward un-actioned to S37 (TD-061 6/19 pythonw remaining, TD-094, TD-S33-NEW-1/2/3/4, TD-S35-NEW-1/2/3/4, ENH-84, ENH-108). ENH-99 PROPOSED → SHIPPED (consumed S29 reservation). No new ADR acceptances. No new ENH filings. Foundational diagnosis-ordering lesson §D.18.1 codified for future TD investigation methodology. PostgREST `Prefer: return=representation` RLS interaction codified §D.18.3. int4 `duration_ms` clamp pattern codified §D.18.4.* ***Updated Session 37 (2026-05-25 — ENH-80 per-strike GEX writer SHIPPED + ENH-81 Positioning Landscape SHIPPED + ADR-014 → ADR-015 same-session schema supersession + ADR-016 PROPOSED build-deferred + GEX-as-context-not-gate decision codified): 3 NEW TDs filed pending S38+ at top of Active section — TD-S37-01 S3 (hardcoded τ_pin = τ_accel = 0.3 in ENH-81 SQL views; formalize as `merdian_parameters` lookup when ENH-83 calibration console builds; `// TAU_PIN — swap for ENH-83 lookup` markers in place at every site in `v_gex_strike_pin_zone` + `v_gex_strike_accel_zone` for mechanical plumb when ADR-016 graduates), TD-S37-02 S3 (§F1 dealer-vs-positioning GEX split scaffolded via `v_oi_prev_close_snapshots` view; writer integration deferred pending design decisions on sign convention + OI-change window definition), TD-S37-03 S3 (Lovable anon-key brittleness — RLS misconfiguration produces silent empty datasets not auth errors; per-table RLS+GRANT triplet must be documented inline in commit message + smoke-tested via direct anon-key probe before deploying any new view). 0 TDs CLOSED Session 37; 12 TDs carry-forward un-actioned to S38 (TD-061 6/19 pythonw remaining, TD-094 if still relevant post-S29 reclassification, TD-S33-NEW-1/2/3/4, TD-S35-NEW-1/2/3/4, TD-S36-NEW-1/2/3/4, ENH-84 / ENH-108 deferred). 0 same-session NEW+RESOLVED this session (S37 was build session, not closure session). 3 ADRs touched: ADR-014 ACCEPTED then SUPERSEDED same session (per-strike GEX schema v1 16-col with derived booleans superseded post-quant-review of marker noise 39% NIFTY / 20% SENSEX fire rates); ADR-015 ACCEPTED (per-strike GEX schema v2 12-col minimum-sufficient-statistic with `gamma_call`/`gamma_put` split preserving IV skew; writer shipped via `patch_s37_enh80_writer_v2.py`; cross-symbol smoke-fire abs_diff ≤ 1e-10 Cr); ADR-016 PROPOSED build-deferred (parameter calibration pattern — temporal-immutable `merdian_parameters` table with mandatory `change_reason`; design surfaced 9 magic-number clusters needing same treatment; ENH-83 build deferred until N grows for cohort-driven recalibration to be useful). 2 ENH status updates: ENH-80 per-strike GEX writer PROPOSED → SHIPPED; ENH-81 Positioning Landscape (3 SQL views + Pine overlay v1+v2 + Lovable dashboard) PROPOSED → SHIPPED. 0 new ENH filings. GEX-as-context-not-gate decision codified per operator framing — MERDIAN's gating capacity is saturated (5 existing gating layers); new positioning intelligence ships as display layer (Lovable dashboard + Pine overlay PIN/ACCEL zones) not as routing input to `build_trade_signal_local.py`; operator is the integration layer for GEX-derived decisions. PE/CE GEX split preserved in schema but not surfaced — research-grade only. §D.19 added to Assumption Register (3 rows D.19.1 minimum-sufficient-statistic at write layer / D.19.2 IV skew preservation via gamma_call/put split / D.19.3 GEX-as-context-not-gate framing). MERDIAN AWS instance ID memory update actioned (S35 P0_TERTIARY carry-forward, `i-0878c118835386ec2`). 4 production patches deployed (`patch_s37_enh80_writer.py` v1 then schema-migrated; `patch_s37_enh80_writer_v2.py` canonical; `patch_s37_enh81_pine_overlay.py` v1; `patch_s37_enh81_pine_overlay_v2.py` zone-edge labels + single-strike widening). 4 backups preserved Local. 1 new table (`gex_strike_snapshots`), 4 new views (`v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`, `v_dealer_flow_sim`, `v_oi_prev_close_snapshots` scaffold-only). 7 canonical files modified at session close per Doc Protocol v4 Rule 3 + Rule 9 + Rule 10 + Rule 11 — full-file no-crunch discipline maintained throughout. 3 new ADR files: ADR-014-per-strike-gex-schema.md + ADR-015-per-strike-gex-schema-v2.md + ADR-016-parameter-calibration-pattern.md. 0 git commits / 0 tags this session (session-37-close pending operator).* **Updated Session 40 (2026-05-29 — TD-S37-01 CLOSED via patch_s40_enh83_view_tau_rewrite.py runtime τ lookup + Marketview v4 atomic-card redesign + AWS deploy pipeline + 9-canonical-file doc-close pack): 3 NEW TDs filed at top of Active section: TD-S40-NEW-1 S4 (cp1252-incompatible Unicode minus-sign in patch script v1 — RESOLVED-SAME-SESSION via ASCII-clean v2 deploy; codification of Windows patch-script ASCII-only authoring discipline), TD-S40-NEW-2 S3 (`update_parameter` SECURITY DEFINER RPC violated `chk_valid_from_to` CHECK constraint because Lovable auto-scaffold gave `merdian_parameters.valid_to` `DEFAULT now()` — DISCOVERED-CLOSED-SAME-SESSION via `ALTER TABLE ... DROP DEFAULT`; codified §D.22.1 Lovable temporal-immutable column DEFAULT audit pattern REFUTED-S40), TD-S40-NEW-3 S2 (TradingView Pine overlay extension for PIN + ACCEL zones — operator-asked-for-but-deferred pending full `generate_pine_overlay.py` 505-line review; ~30-40 min estimated extension work carry-forward S41+). TD-S37-01 CLOSED via `patch_s40_enh83_view_tau_rewrite.py` — closure block prepended to Resolved section above; two surgical replacements of hardcoded τ=0.3 → `get_parameter_num('pin.tau.'||symbol)::numeric AS tau_used` and `get_parameter_num('accel.tau.'||symbol)::numeric AS tau_used` in `v_gex_strike_pin_zone` + `v_gex_strike_accel_zone`; smoke-fire SQL verified `tau_used = 0.30` cross-symbol; calibration round-trip 0.30→0.25→0.30 verified via the now-functional `update_parameter` RPC (TD-S40-NEW-2 fix landed in same session to make this round-trip possible). **3 TDs CLOSED Session 40** (TD-S37-01 via patch_s40 + TD-S40-NEW-1 RESOLVED-SAME-SESSION + TD-S40-NEW-2 DISCOVERED-CLOSED-SAME-SESSION); 0 TDs CLOSED via patch (TD-S40-NEW-3 deferred). 12 TDs carry-forward un-actioned to S41 (TD-S39-NEW-3 anon key in public repo P0; 4 writer-side TDs for VIX/WCB/Pin Risk Score/Pin Risk Timeline surfacing as empty Marketview cards; TD-S39-NEW-2/4/5 + TD-S37-02/03 + TD-S36-NEW-1/2/3/4). 0 same-session NEW+RESOLVED in this session if counted strictly (S40 produced 2 same-session NEW+RESOLVED — TD-S40-NEW-1 + TD-S40-NEW-2; the 11th and 12th same-session pattern instances after TD-097 S25 + TD-101 S26 + TD-NEW-2/3 S27 + 6 in S28 + 5 in S29 + 0 in S30-S39). 0 production Python code patches this session (S40 was SQL DDL + frontend Lovable iterations + AWS deploy infra + doc-close; no Python production code edits). 2 SQL files patched (both ENH-81 view DDLs) + 1 new SQL file (`sql/v_max_pain_by_strike.sql` long-format pivot view). 1 patch script new (`patch_s40_enh83_view_tau_rewrite.py` ASCII-clean v2). 1 schema change (`ALTER TABLE public.merdian_parameters ALTER COLUMN valid_to DROP DEFAULT`). 1 new view (`v_max_pain_by_strike`). Codified §D.22 Assumption Register S40 with 3 rows: D.22.1 Lovable temporal-immutable column DEFAULT audit pattern REFUTED-S40 (canonical lesson — any column intended to differentiate rows by transaction-time within a single transaction must NOT carry `DEFAULT now()`); D.22.2 atomic single-metric card layout VALIDATED-S40 (collapsed-Hero-paragraph cards violate ADR-017 P1 three-filter rule); D.22.3 stacked-by-strike charts VALIDATED-S40 (vertical strike-axis alignment is mandatory when two charts measure different metrics over the same strike domain — horizontal side-by-side breaks cross-reference eye-tracking). AWS infrastructure update: new clone path `/home/ssm-user/meridian-connect` for Marketview frontend source (cataloged in Topology §8.2); canonical 3-line deploy command codified `cd ~/meridian-connect && git pull && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/`. Marketview v4 atomic-card layout APPLIED via Lovable through 4 mockup iterations + schema-mismatch correction prompt for Lovable column-name fixes; dashboard live at http://13.63.27.85/marketview rendering bundle index-vDqPX1iO.js. 4 cards confirmed empty-by-design (writer-side gaps, not frontend bugs): India VIX (gamma_metrics.vix NULL), WCB (market_breadth_intraday.wcb column missing), Pin Risk Score (gamma_metrics.pin_risk_score column missing), Pin Risk Timeline (depends on pin_risk_score). All four filed as P1 writer-side carry-forward to S41+. 0 git commits / 0 tags this session (session-40-close pending operator).*

 **Updated Session 41 (2026-06-01 — Marketview Health dashboard MVP + India VIX + max_gamma_strike + Pin Risk Score writer + FIX-1 + 30-day backfill + WCB ExecutionLog instrumentation + Pine GEX overlay color/box-count fixes): 4 NEW TDs filed at top of Active section — TD-S41-NEW-1 S3 (`trading_calendar` lacks NSE holiday pre-population; ENH-66 doctrine violation; fix annual seed or `merdian_start.py.ensure_calendar_row()` holiday-aware), TD-S41-NEW-2 S2 (Dhan token refresh suppressed across NSE holidays; cross-host single-point-of-failure with Local sole refresh path; AWS consumes from Supabase but doesn't refresh; materially elevates ADR-006 AWS migration urgency; interim fix WAKETOWRUN=true + AWS-side heartbeat staleness check), TD-S41-NEW-3 S3 (`merdian_reference.json` schema drift — 3-strike SQL guess pattern surfaced twice this session; Path A audit script / Path B kill JSON-as-schema-source / Path C auto-regenerate from `information_schema.columns`), TD-S41-NEW-5 S2 (Sub-A WCB writer 17% NIFTY active-weight degradation from PostgREST pagination cap 50×150>5000; 11 missing tickers SBIN/SBILIFE/SHRIRAMFIN/SUNPHARMA/TATACONSUM/TATASTEEL/TECHM/TITAN/ULTRACEMCO/WIPRO/TCS; SENSEX unaffected 30-ticker basket; fix `gte('trade_date', N_days_ago)` server-side filter / Sub-B regime threshold disagreement Python 60/40 vs SQL 62.5/37.5; both produce TRANSITION today but boundary cases would disagree; Path A align Python to SQL fast closure or Path C call SQL function from Python cleanest). 1 TD CLOSED Session 41: TD-S41-NEW-4 DISCOVERED+CLOSED same-session (build_wcb_snapshot_local.py ExecutionLog instrumentation gap; observable-surface-first discovery via Marketview Health dashboard WCB row "never" → diagnostic SQL → writer-source-reading → 2-replacement v3 patch + smoke-fire NIFTY+SENSEX SUCCESS in <90 min; 13th same-session NEW+RESOLVED pattern across MERDIAN history). 12 TDs carry-forward un-actioned to S42 (TD-S39-NEW-3 anon key in public repo P0 + S35/S36/S37/S33 backlog + older items). 5 production patches deployed S41: compute_gamma_metrics_local.py (P0.a India VIX + max_gamma_strike + Pin Risk Score writer); compute_gamma_metrics_local.py (FIX-1 max_gamma_strike positive-GEX argmax correction); build_wcb_snapshot_local.py (TD-NEW-4 ExecutionLog instrumentation); generate_pine_overlay.py (Pine GEX overlay color cyan/magenta); generate_pine_overlay.py (Pine GEX overlay max_boxes_count 250→500). 1 DDL applied (gamma_metrics 3-column addition vix + max_gamma_strike + pin_risk_score). 2 new anon SELECT RLS policies (script_execution_log + dhan_token_probe_log; canonical fix `CREATE POLICY anon_select_* FOR SELECT TO anon USING(true)` on every newly-RLS-enabled ops table; codified D.23.2). 3,787 backfill rows written (2,909 VIX bars + 439 max_gamma_strike + 439 pin_risk_score via 591-line `backfill_s41_p0a_columns_30d.py`). 0 ADR acceptances S41 (execution against existing ADR-016 + ADR-017). §D.23 added to Assumption Register with 3 rows: D.23.1 max_gamma_strike positive-GEX argmax VALIDATED (semantic alignment with Marketview pin-candidate magnet UX); D.23.2 Lovable RLS rowsecurity-true without policies = silent empty anon datasets VALIDATED-S41 (canonical fix CREATE POLICY anon_select_* FOR SELECT TO anon USING(true) on every newly-RLS-enabled ops table); D.23.3 Pine v6 box-count silent-overflow-drop VALIDATED-S41 (late-emitted objects silently dropped when count exceeds max_boxes_count; raise to 500 ceiling at template-emit time). Marketview Health dashboard MVP live at http://13.63.27.85/marketview/health (3 sections SYSTEM STATUS + WRITER FRESHNESS + ERROR RATE LAST 24H; 30s polling; off-hours mute). MERDIAN_Marketview_Reference.docx delivered (15,988 bytes / 152 paragraphs / validates PASS). 0 git commits / 0 tags this session (session-41-close pending operator).*

## TD-S47-NEW-1 (S1 priority) — volatility_metrics table doesn't exist; graceful fallback working

**Context:** compute_volatility_metrics_local.py reads from production compute_volatility_metrics table (for historical intraday context). Table doesn't exist in Supabase yet (ADR-006 DDL pending). Script was crashing on 404 PGRST205.

**Fix applied S47:** Added exception handler in main() insert block. Catches PGRST205 error, calls `log.exit_with_reason("SKIPPED_NO_OUTPUT", exit_code=0)` + `sys.exit(0)`. Now exits cleanly with 0 when table missing.

**Status:** FIXED S47. Script passes orchestrator contract (10/10 steps green). Table creation is separate ADR-006 work.

**Owner:** Navin  
**Closed:** S47  
**Follow-up:** None (graceful fallback sufficient until ADR-006 lands)

---

## TD-S47-NEW-2 (S2 priority) — gamma_metrics --shadow flag parsed as symbol

**Context:** compute_gamma_metrics_local.py parse_args() had module-level `--shadow` strip (from sys.argv at import time) but parse_args didn't defensively re-strip. When orchestrator called `compute_gamma_metrics_local.py <run_id> --shadow`, the --shadow flag made it through to parse_args and got matched as symbol name, causing "symbol=--SHADOW" mismatch error.

**Fix applied S47:** Added defensive `argv = [a for a in argv if a != "--shadow"]` at top of parse_args() function. Now --shadow is stripped even if module-level strip failed.

**Status:** FIXED S47. Tested: parse_args now correctly parses `['compute_gamma_metrics_local.py', 'e57d1db6-...', '--shadow']` → `run_id='e57d1db6-...', symbol=None, run_type='FULL'`.

**Owner:** Navin  
**Closed:** S47  
**Follow-up:** None (dual-strip is defensive pattern, acceptable overhead)

---

## TD-S47-NEW-3 (S1 priority) — Dhan token refresh architecture: move from Local-only to AWS-first

**Context:** Current token refresh is Local-Windows-only: Task Scheduler task runs 02:45 UTC daily, writes token to Supabase `merdian_dhan_token` table. If workstation offline (weekend, holiday, power loss), AWS pipeline has no token refresh path. Interim mitigation (S42): AWS cron job added + Local task WAKETOWRUN fallback, insufficient. **Dhan token expires 2026-06-28 (20 days from S47 open).**

**Blocker:** If Local workstation offline on weekend/holiday before 2026-06-28, AWS loses refresh capability. Token expiry forces cutover.

**Proposed architecture:**
1. **Primary:** AWS cron job `/home/ssm-user/meridian-engine/refresh_dhan_token_aws.py` fires 02:45 UTC daily (already deployed S42; verify still active)
2. **Fallback:** Local Windows task ENABLED as 24-hour safety margin (if AWS token stale >24h, Local can refresh)
3. **Monitoring:** Add Supabase health check query: `SELECT token_acquired_at FROM merdian_dhan_token ORDER BY created_at DESC LIMIT 1` — alert if timestamp >26 hours old (signals AWS cron failure)

**Implementation plan:**
1. Verify AWS cron entry exists: `crontab -l | grep refresh_dhan` (should show `15 02 * * 1-5 ...`)
2. Test token rotation: manually trigger AWS script, verify Supabase row writes with correct timestamp
3. Add Supabase health check to EC2 log-parse runbook or daily operator checklist
4. Document: add section to `runbook_aws_cli_file_operations.md` or create `runbook_dhan_token_aws_refresh.md`

**Owner:** Navin (token automation)  
**Estimated effort:** 1-2 hours (cron validation + test + health check setup + documentation)  
**Target completion:** Before 2026-06-28 (20-day buffer)  
**Signed off:** S47  
**Status:** FILED (not started)

Updated Session 52 (2026-06-12 — observability infrastructure): 0 new TDs filed S52. Silent-death prevention infrastructure (health monitor, dashboard refresh, contract validator, timeout enforcer) deployed without debt. Monitoring scripts use dotenv for .env; all 4 crontab entries active + tested; Telegram integration live; status.json health snapshot every 1 min. Carry-forward S53: market-open monitoring validation + orchestrator execution log review + Telegram alert validation.
Updated Session 53–54 (2026-06-12 → 2026-06-16 — blackout recovery + first-full-day audit): 6 TDs filed (TD-S53-NEW-1..6 + TD-S54-NEW-1..4 — net of the S53 set, S54 added NEW-1..4); 4 closed (TD-S53-NEW-1/2/3 same-session S53 root-cause + ingest + volatility upsert; TD-S53-NEW-4 closed S54 via `*/5`). Open headline: TD-S54-NEW-1 S1 SENSEX compute silent under-write (code trace pending). Still open: TD-S53-NEW-5 monitors false-state, TD-S53-NEW-6 futures SyntaxError, TD-S54-NEW-2/3/4.

Updated Session 55 (2026-06-17 — carry-forward execution sweep): TDs closed 4 (S54-NEW-1 code, S55-NEW-1 vol read-path, S54-NEW-3, S54-NEW-4); S53-NEW-6 parse-fixed (futures contract-resolution open); TD-NEW-H superseded; S36-NEW-4 resolved (duration_ms bigint); S41-NEW-2 downgraded S2->S3; S48-NEW-1 re-diagnosed (breadth feed, open, narrowed to one read); 1 new TD filed+closed (S55-NEW-1).

Updated Session 56 (2026-06-18 — RECONSTRUCTED at S57): futures resolver exact-match fix (8eae351) + Dhan scripmaster reloader ported to AWS with staging table + swap RPC (132eddc, 234,882 rows) + futures cron re-enabled; closed the S55 NEW-6 contract-resolution tail.
Updated Session 57 (2026-06-19 — data audit + breadth root-cause + ADR-018): TD-S48-NEW-1 breadth RE-DIAGNOSED → CLOSED-DECISION (feed was on AWS not MALPHA, expired-token 403 loop, unsupervised; implementation carries as TD-S57-NEW-1 + TD-S57-NEW-2). 2 new TDs filed (S57-NEW-1 enable/cutover the S56-built systemd units onto MALPHA + WCB cron; S57-NEW-2 reader recency-floor guard). Correction post-S57: S56 had already built+committed the wsfeed preflight + alert + 5 deploy/systemd units (afe8112/30cca59/b627914); S57-NEW-1 is cutover, not build. SMDM retired (ADR-018 D3, evidence-based vs ENH-30 Exp 9 NEUTRAL) and rebuilt as ENH-SDM (PROPOSED). Signal-orphan disposition open for options_flow / iv_context / shadow-v3.
Updated Session 57 (2026-06-19 — register sync): folded ΔPCR/strike-PCR into ENH-02 + CoC/basis-velocity into ENH-07; filed ENH-115 (FII/DII positioning) + ENH-SDM (structural divergence monitor); corrected ENH-02/07 stale COMPLETE→IN PROGRESS; filed TD-S57-NEW-3 (register dual-structure inconsistency).
Updated Session 58 (2026-06-22): filed TD-S58-NEW-1 (purchased chain 0% Greeks; ENH-SDM backward study blocked behind a Greeks solve; forward observability monitor is the unblocked path). #1 systemd cutover + #2 recency-floor verified live this session (TD-S57-NEW-1 / TD-S57-NEW-2 close on verification; TD-081 + TD-NEW-K/L/M with them).
Updated Session 58 close (2026-06-22): TD-S57-NEW-1 + TD-S57-NEW-2 CLOSED-VERIFIED on the Monday open (breadth-fragility class ended); TD-081 + TD-NEW-K/L/M closed downstream; TD-S58-NEW-1 filed (purchased-chain 0% Greeks). ADR-018 D1 host corrected MALPHA->AWS; ADR-019 accepted (orphan port-not-retire); ENH-SDM reframed observability-first + P1 schema deployed.

Updated Session 60 (2026-06-26 — Muharram holiday): 5 NEW TDs filed at top of Active section. TD-S60-NEW-1 (S2) marker-header phantom +4.34% CLOSED (stalled `market_spot_session_markers` writer → 21-day-stale prev_close baseline; cron + freshness guard + open/prevclose window fixes). TD-S60-NEW-2 (S1) `trading_calendar.json` 2-of-15 holidays misdated → every NSE holiday mismarked open since ~April → pipeline ran on Muharram; CLOSED AT SOURCE (15 official holidays, `bafddc2`, reseed + stale-row UPDATE) + orchestrator gate belt (`af74d0c`). TD-S60-NEW-3 (S2) shared holiday-gate helper `core/trading_calendar_gate.py` BUILT (`3b3b8ee` self-sufficient v2) + orchestrator CUT OVER (`38a82ff`); ~28 bespoke gates migrate incrementally. TD-S60-NEW-4 (S2) holiday-noise compute rows on 06-26 CLOSED via scoped single-date DELETE (gamma 30 / market_state 30 / volatility 30 / momentum 29 / signal 34 / SDM 16; 0 remaining; spot+markers preserved). TD-S60-NEW-5 (S2) `core/config.py` Windows-hardcoded `BASE_DIR` FILED (latent AWS portability landmine; surfaced by the NEW-3 smoke-test). TD-S59-NEW-2 (exec_log exit_reason) annotated CARRIED TO S61 (operator-stated priority #1, ~15 min, schema confirmed). 4 TDs closed this session (NEW-1/-2/-4 + the calendar root cause), 1 built (NEW-3), 1 filed (NEW-5). No new ADR (bug-fixes + a compute writer + data-repair + a helper-consolidation; Doc Protocol v4 Rule 10 bar not met). 8 commits; all production patches canon-v3 with `_PRE_S60` backups.

Updated Session 61 (2026-06-27 — carry-forward execution sweep): **TD-S59-NEW-2 CLOSED** (exec_log `exit_reason` → `_classify_exit_reason` valid enum, `3533d22` — the operator's #1; closes the silent-failure hole behind the S59 breadth freeze). **ENH-02 WIRED** (`compute_options_flow_local.py` re-homed to the orchestrator) + **TD-S61-NEW-1 NEW+CLOSED** (ADR-018 D2 floor `MERDIAN_FLOW_RECENCY_FLOOR_MIN` on `_fetch_options_flow` — the ENH-02/04 ±3/4/5 modifiers had run off a ~24-day-stale row since S49; `8ddbc78`+`d16986c`). **ENH-07 B basis-velocity context BUILT+DEPLOYED** (`compute_basis_context_local.py` → `basis_context_snapshots`, display-only context-not-gate, `141386d`) + `hist_basis_context` backfill (NIFTY 92,515 / SENSEX 29,689, zero-shift pairing). **TD-S61-NEW-2 NEW+CLOSED** (hist bar pairing IST-clock-as-UTC zero-shift, 14%→~99%). **TD-S61-NEW-3 FILED** (reference.json `_meta` vestigial-header drift; resynced). **ENH-07 A reframed** (no live BS solver/rate; `core/bs_engine.py` built+validated). 3 TDs closed (TD-S59-NEW-2 + TD-S61-NEW-1/-2), 3 filed (TD-S61-NEW-1/2/3). No new ADR. 4 commits + backfill; all production patches canon-v3 with `_PRE_S61` backups.

Updated Session 63 (2026-07-02): **TD-S62-NEW RESOLVED** in place (Resolution row + heading marker) — SENSEX `compute_flip_level` regime-conditional fix deployed `dc63bb3` (near-spot sign-change walk + short-γ display guard; StockMojo parity confirms near-spot). **TD-S62-NEW-2 CARRIED** to S64 (SENSEX 2026-01-19 concentration resume not run this session). No new TDs (ENH-115 built clean — participant writer live + 270-day backfill + cash leg wired + daily cron; the backfill's DB-calendar-gate→local-weekday-filter fix is codified as a CLAUDE.md Rule 18 corollary, not a TD). No-crunch: all prior entries preserved verbatim; only the TD-S62-NEW heading marker + Resolution row added.

Updated Session 62 (2026-07-01): 2 NEW TDs at top of Active — **TD-S62-NEW (S2)** SENSEX `compute_flip_level` spurious deep-tail flip (−6.75%/−7.11%) under NEGATIVE_γ, isolated by StockMojo parity as the sole divergent field (all other readings match exactly); root cause = ATM-outward walk falls through a uniform short-γ near-spot pit to a deep-tail crossing; fix = near-spot sign-change walk + short-γ display guard; per-strike confirmation deferred post-backfill. **TD-S62-NEW-2 (S3)** SENSEX 2026-01-19 `gamma_concentration` unfilled (SSLError mid-solve); one-line resume filed. **TD-S58-NEW-1 CLOSED** and MOVED to Resolved with evidence — historical per-strike Greeks sidecar (`backfill_hist_greeks.py`) + the DISCOVERY that a full-window `hist_gamma_metrics` series already existed needing only its `gamma_concentration` column filled (`fill_gamma_concentration.py`, `run_fullwindow.py`); NIFTY + SENSEX run to completion (bar 2026-01-19 → TD-S62-NEW-2); a divergent `--fast` path abandoned not loosened. No new ADR (ENH-116 is a PROPOSED spec; ENH-07 A close is a no-op ruling — Doc Protocol v4 Rule 10 bar not met). 0 git commits (backfill scripts + ENH-116 spec staged, carry to S63).
Updated Session 65 (2026-07-07 — breadth/`equity_eod` diagnosis + carry execution): 1 NEW TD at top of Active — **TD-S65-NEW-1 (S3)** `check_eod_coverage_freshness.py` mis-tuned (denominator nominal ~1,385 vs active ~1,159; staleness 5-day vs last-trading-day + ~3-day Dhan-lag; `/1` false-OK). 0 TDs closed. The 07-03/07-06 `equity_eod` absence was diagnosed as Dhan EOD publish-lag (NOT a bug; `compute_date_window` T−1/220 proven correct) — no TD filed for it. OAuth `client_secret` rotation APPLIED (ENH-117 security fold; old-client delete + denial test pending).
