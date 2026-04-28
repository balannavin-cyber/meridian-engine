# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-28 (Session 12 — documentation / philosophy session) |
| **Concern** | Two items competed: Item A (gamma dashboard analysis deferred from Session 11) and Item B (ENH-75 PO3 live detection build). Item A was chosen first and consumed the full session. Item B (ENH-75) was NOT built. |
| **Type** | Documentation + philosophy + register overhaul. No code shipped. Single-session-rule override not required — this was always a valid documentation session under the backlog. |
| **Outcome** | DONE (documentation). DEFERRED (ENH-75 build). Gamma dashboard built by a successful options writer (short-gamma seller) formally analysed against MERDIAN Gamma Engine. Six structural gaps identified. ADR-002 authored and filed at `docs/decisions/`. MERDIAN_Enhancement_Register.md rewritten as unified file ENH-01 through ENH-83. merdian_reference.json bumped to v7. session_log.md updated. ENH-75 deferred to Session 13. |
| **Git start → end** | `15720d6` → pending commit (Session 11 experiment scripts + Session 12 documentation files both uncommitted). |
| **Local + AWS hash match** | Local ahead of origin. AWS still at `15720d6` — shadow runner down since 2026-04-15, no AWS activity this session. |
| **Files changed (code)** | None. |
| **Files added / rewritten (docs)** | `docs/decisions/ADR-002-market-structure-philosophy.md` (NEW — 6 principles, capital scaling roadmap, GEX weekly storage decision); `MERDIAN_Enhancement_Register.md` (FULL REWRITE — unified ENH-01 through ENH-83, prior file had fragmented delta sections); `merdian_reference.json` (v7 — change log, ADR-002 file entry, gex_strike_snapshots PROPOSED table, gamma_metrics proposed columns, governance rules 14/15/16 + ADR-002 principles + capital scaling roadmap, Session 12 session_log entry); `session_log.md` (Session 12 one-liner prepended to v3 canonical section); `CURRENT.md` (this rewrite). |
| **Tables changed** | None. |
| **Cron / Tasks added** | None. |
| **`docs_updated`** | YES — all five canonical files updated. |

### What Session 12 did, in bullets

**Gamma dashboard analysis — six structural gaps identified:**

- **Gap 1 — No per-strike GEX histogram.** MERDIAN stores scalar summary metrics (`net_gex`, `flip_level`, `gamma_concentration`). The options writer's dashboard shows the full GEX histogram across every strike — where the positive clusters are, where negative bars begin, the shape of the curve. Without the per-strike distribution, pin zones, acceleration zones, and local vs aggregate divergence are all invisible. All downstream ADR-002 features depend on this as the foundational data layer.

- **Gap 2 — Binary regime misclassifies PINNED sessions.** MERDIAN's `LONG_GAMMA` / `SHORT_GAMMA` regime is derived from net GEX sign. The dashboard surfaced a case (Screenshot 2) where net GEX was −976 Cr (SHORT_GAMMA — MERDIAN would call this "dealers amplify moves") while local GEX around spot was deeply positive (dealers are pinning spot right where it currently lives). MERDIAN misclassifies this session type entirely. Documented in Appendix D as known gap. Experiment 23 is the empirical validation path; PINNED is the proposed third regime state (ENH-82).

- **Gap 3 — No acceleration zone as first-class output.** MERDIAN knows the flip level but doesn't model what happens above it as a zone with a specific character. The dashboard explicitly marks the acceleration zone (red bars above 24,301 where dealers must sell every rally) as a named, bordered zone. MERDIAN has a point, not a zone.

- **Gap 4 — Direction only, no force.** The dashboard's dealer flow simulator answers: "if spot moves ±0.5% or ±1%, how many Crore of futures must dealers transact to rehedge?" MERDIAN produces a regime label (LONG/SHORT). The Crore number is what tells you whether a structural level will hold or be steamrolled. This is P2 of ADR-002.

- **Gap 5 — No regime velocity.** Max gamma migrated 24,600 → 24,200 between the two screenshots. Net GEX fell from −976 Cr to −14,323 Cr. MERDIAN captures point-in-time snapshots only. The direction and speed of the GEX structure's movement is itself a signal — untracked.

- **Gap 6 — DTE as binary gate, not force multiplier.** The same GEX Crore at DTE=1 vs DTE=5 is a categorically different force equation. MERDIAN uses `min_dte_threshold = 2` as a binary execution block. DTE should also modify the force calculations in the gamma engine.

**ADR-002 authored:**

- Six principles formalised: P1 (zones not points — every structural feature has width, not just a level), P2 (force not direction — dealer Cr flow is the edge), P3 (know where sellers panic — the flip zone is where short-gamma cascades originate), P4 (regime velocity — max gamma migration and gex_velocity are signals), P5 (local beats aggregate — local GEX cluster around spot overrides net GEX sign), P6 (DTE is a force multiplier not a risk flag).

- Capital scaling roadmap settled: Phase 1 = directional naked options buying (current, ~25,000 lot capacity ceiling before market impact becomes material); Phase 2 = debit spreads (at ceiling or when IV makes naked premium unfavourable); Phase 3 = defined-risk selling (credit spreads, NOT naked — requires full P1–P5 ADR-002 implementation first). Phase 3 cannot be attempted until `gex_strike_snapshots` is live and Experiment 23 is validated.

- GEX weekly time-series storage decision: store per-strike GEX at the same 5-minute cadence as the existing options ingestion. Data already in `option_chain_snapshots` — this is aggregation, not new collection. ~15,600 rows/day across NIFTY + SENSEX. Manageable within Supabase budget.

**New ENH filed (ENH-80 through ENH-83):**

- **ENH-80** — Per-strike GEX time-series + zone bounds. New `gex_strike_snapshots` table. Zone bound columns added to `gamma_metrics`. Foundational data layer for ENH-81, ENH-82, and Experiment 23. Build immediately after ENH-75.
- **ENH-81** — Dealer flow simulator + regime velocity. Four spot-move scenarios (±0.5%, ±1.0%) → Crore of dealer futures flow. `max_gamma_strike_delta` and `gex_velocity` derived fields. Requires ENH-80 (needs prior GEX row to diff against).
- **ENH-82** — PINNED gamma regime state (third regime). Criteria: spot inside positive local GEX cluster of sufficient magnitude regardless of net GEX sign. Threshold must be empirically set via Experiment 23. BLOCKED until Experiment 23 run and ENH-80 data accumulated.
- **ENH-83** — DTE-adjusted force multiplier on dealer flow Crore outputs from ENH-81. Deferred Phase 1.5+ — DTE force curve cannot be estimated without multiple expiry cycles of `gex_strike_snapshots` data.

**Build sequencing locked (ADR-002):**
```
ENH-75 (PO3 live detection — Session 13 primary)
  ↓
ENH-80 (per-strike GEX table) — next gamma layer priority
  ↓
ENH-81 (force metrics) — requires ENH-80
  ↓
Experiment 23 (local vs net GEX divergence) — requires ENH-80 data
  ↓
ENH-82 (PINNED regime) — requires Exp 23 threshold
  ↓
ENH-83 (DTE multiplier) — requires ENH-80 data + multiple expiry cycles
```

**Register overhaul:**

- `MERDIAN_Enhancement_Register.md` rewritten as a single unified file covering ENH-01 through ENH-83. The prior on-disk file had the original v7 body plus multiple appended delta sections (v8 appended, delta-2026-04-21, ENH-72 closure note, ENH-73a/73b). All content preserved, delta structure eliminated.
- `merdian_reference.json` bumped to v7. Added: Session 12 change_log entry, ADR-002 file entry, `gex_strike_snapshots` PROPOSED table with full DDL and storage estimate, `gamma_metrics` proposed ENH-80/ENH-81 columns, governance rules for `ret_30m_percentage_points` (Rule 14), `supabase_1000_row_cap` (Rule 15), `bar_ts_tz_workaround` (Rule 16), `no_is_pre_market_column`, `adr_002_market_structure_philosophy`, `capital_scaling_roadmap`. Session 12 session_log entry added (marked partial — ENH-75 not yet built).

**One meta-observation documented:**

The options writer's system is a Phase 3 tool — built by a seller who needed the full force-structure picture to survive. MERDIAN is built for options buying (Phase 1). The two are complementary, not competing. His system is better at characterising force structure; MERDIAN is building the pipeline to act on it. The ideal future state is MERDIAN consuming his type of GEX structure data as upstream input — which is exactly what ENH-80 through ENH-82 begin to build.

---

## This session

> Session 13. Primary path: **ENH-75 — PO3 Live Session Bias Detection**.

### Candidate A (required) — ENH-75: PO3 Live Session Bias Detection

| Field | Value |
|---|---|
| **Goal** | Wire Exp 35C detection logic into the live pipeline. Detect PDH/PDL first-sweep in OPEN window (09:15–10:00 IST) with 35C filters. Write `po3_session_bias = PO3_BEARISH / PO3_BULLISH / PO3_NONE` to market state by 10:05 IST. Prerequisite for ENH-76 and ENH-77. |
| **Type** | Code — small to medium. Reuses Exp 35C detection logic. |
| **Time budget** | ~15–25 exchanges. |

### Candidate B (if A completes quickly) — ENH-76: BEAR_OB MIDDAY gate on PO3_BEARISH

| Field | Value |
|---|---|
| **Goal** | Gate BEAR_OB MIDDAY signals on `po3_session_bias = PO3_BEARISH`. One filter condition in signal engine. Requires ENH-75 first. |
| **Type** | Code — small. |

### Candidate C (if B completes quickly) — ENH-77: BULL_OB AFTERNOON gate on PO3_BULLISH (SENSEX)

| Field | Value |
|---|---|
| **Goal** | Gate BULL_OB AFTERNOON (SENSEX only) on `po3_session_bias = PO3_BULLISH`. Requires ENH-75 first. |
| **Type** | Code — small. |

### Candidate D — Exp 42 composition rate

| Field | Value |
|---|---|
| **Goal** | How often does a PDH-sweep session (E1) also produce a MIDDAY BEAR_OB (E4) in the same session? What is the mean T+30m return in points for E4? Query `hist_pattern_signals` for BEAR_OB MIDDAY on E1 session dates. |
| **Type** | Research — small. |

### DO_NOT_REOPEN

- All Session 10 + Session 11 + Session 12 DO_NOT_REOPEN items.
- ADR-002 principles (P1–P6) are settled — do not re-litigate.
- ENH-80 through ENH-83 sequencing is settled — ENH-80 cannot be built before ENH-75 is complete and data accumulates.
- Exp 34–41B design decisions — do not re-run with minor parameter tweaks without new evidence.
- PDL DTE<3 next-week recommendation is SKIP — confirmed.
- BEAR_OB AFTERNOON + PO3_BEARISH = 33.3% — hard skip.
- NIFTY BULL_OB AFTERNOON + PO3_BULLISH WR=50% — discarded. SENSEX only.

### Watch-outs

- ENH-46-C still BLOCKED on TD-032. TD-032 PATCHED (Session 11 extension) but 10-cycle live verification required to formally close.
- **TD-038 live trading risk:** EXIT AT label on dashboard shows UTC not IST. Compute exit manually until fixed.
- ENH-46-C still BLOCKED on TD-032.
- `hist_pattern_signals.win_60m` is NULL for most backfill signals.
- `ret_30m` in `hist_pattern_signals` is PERCENTAGE POINTS (÷100 for decimal fraction). **Rule 14.**
- Supabase hard-caps at 1000 rows/request. Always `page_size = 1000`. **Rule 15.**
- `hist_spot_bars_5m.bar_ts`: stored as IST labeled +00:00. Use `replace(tzinfo=None)`. **Rule 16.**
- `hist_spot_bars_5m` has **no** `is_pre_market` column. Filter by time: `bar_ts.time() < time(9, 15)`.
- Kelly fractions from Exp 41B based on N=6–19. Hard cap 5-8% per trade until N=30 live events.

---

## Live state snapshot (at Session 13 start)

**Environment:** Local Windows primary; AWS shadow runner down since 2026-04-15 (pre-existing).

**Git state:** Local ahead of origin. Session 11 experiment scripts + Session 12 documentation files (ADR-002, Enhancement Register rewrite, merdian_reference.json v7, session_log, CURRENT.md) all pending commit. AWS at `15720d6`.

**Active TDs (unchanged from Session 10):**
- TD-029 (S2) — `hist_spot_bars_1m`/`5m` pre-04-07 TZ-stamping bug. Workaround: `replace(tzinfo=None)`.
- ~~TD-030~~ — CLOSED Session 11 extension: `recheck_breached_zones()` added; zones mitigated mid-session now marked BREACHED.
- ~~TD-031~~ — CLOSED Session 11 extension: OB/FVG written unconditionally; 72 zones (was 35).
- TD-038 (S2) — Dashboard EXIT AT label shows UTC not IST. **Live trading risk.** Fix: apply IST conversion to `exit_ts` in `card()`.
- TD-039 (S3) — SENSEX DTE=2 on expiry day 04-28 (expected 0). DTE computation or expiry calendar bug.
- **TD-032 (S2) — Dashboard ↔ DB inconsistency. BLOCKER for ENH-46-C.**
- TD-033 (S3) — Dashboard "SELL / BUY PE" label conflation.
- TD-034 (S2) — `hist_atm_option_bars_5m` severely undersampled on dte=0.
- TD-035 (S3) — `signal_snapshots.wcb_regime` NULL but dashboard shows BULLISH.
- TD-036 (S3) — `confidence_score` flat-lined for 90+ minutes.
- TD-037 (S4) — Schema column-name inconsistency across timestamp-bearing tables.

**Active ENH:**
- ENH-46-A: Telegram alert daemon. SHIPPED + live-verified.
- ENH-46-C: Conditional gate lift. **BLOCKED on TD-032.**
- ENH-46-D: Pine HTF zones live JSON feed. PARTIAL — `generate_pine_overlay.py` shipped with proximity tier system (T1/T2/T3); `/download_pine` dashboard endpoint + PINE OVERLAY button added Session 11 extension. TradingView paste workflow eliminated.
- ENH-47: Inside-bar-before-expiry. PROPOSED, discretionary first.
- **ENH-75: PO3 live detection. Session 13 primary.**
- ENH-76: BEAR_OB MIDDAY gate on PO3_BEARISH. Requires ENH-75.
- ENH-77: BULL_OB AFTERNOON gate on PO3_BULLISH (SENSEX). Requires ENH-75.
- ENH-78: DTE<3 PDH sweep → current-week PE instrument rule. PROPOSED.
- ENH-79: PWL weekly sweep → swing entry detection. PROPOSED.
- ENH-80: Per-strike GEX time-series + zone bounds. PROPOSED. Build after ENH-75.
- ENH-81: Dealer flow simulator + regime velocity. PROPOSED. Requires ENH-80.
- ENH-82: PINNED gamma regime. PROPOSED. Blocked on Exp 23 (needs ENH-80 data first).
- ENH-83: DTE-adjusted force multiplier. PROPOSED. Deferred Phase 1.5+.
- F3: Daily zone scheduling. Validated by Exp 15. Ready to ship.

**Session 11 edges proven (for reference):**

| Edge | WR | N | EV/trade | Instrument |
|---|---|---|---|---|
| E4 BEAR_OB MIDDAY + PO3_BEARISH | 88.2% T+30m | 17 | 116.5 pts SENSEX | ATM PE current-week |
| E7 PWL Weekly + Daily Confluence | 100% EOD | 5 | T+2D +534 pts SENSEX | Next-week CE |
| E1 PDH First-Sweep filtered | 93.3% EOD | 15 | ~97 pts NIFTY | Session bias → E4 |
| E3 PDH DTE<3 | 90.9% EOD | 11 | +125% option SENSEX | Current-week ATM PE |
| E6 PWL Refined Weekly | 76.9% EOW | 13 | +534 pts SENSEX T+2D | Next-week CE |
| E2 PDL First-Sweep filtered | 84.6% EOD | 13 | ~255 pts SENSEX | Session bias → E5 |
| E5 BULL_OB AFT + PO3_BULLISH | 73.7% T+30m | 19 | 35.5 pts SENSEX | ATM CE current-week |

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-04-28 (end of Session 12).*
