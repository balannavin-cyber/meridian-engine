---
paths:
  - "docs/research/**/*.md"
  - "experiment_*.py"
  - "docs/registers/MERDIAN_Experiment_Compendium*.md"
---

# Research, cohorts and calibration

Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028). Rule text is
unchanged; only its location moved.

- ❌ Treating `signal_snapshots.action='BUY_CE'/'BUY_PE'` as a real trade. Those are decision rows only. Real trades live in `signal_outcomes` once that table exists. (Session 5 / Session 7 / Session 8 / Session 9 all reverted this misunderstanding.)
- ❌ Trusting `direction_bias` when `wcb_regime=NULL` in `signal_snapshots` — `wcb_regime` has been NULL since 2026-03-19 (regression, only 32/2171 rows ever populated). On BULLISH breadth days this caused `direction_bias=BEARISH` producing BUY_PE on BULL_FVG. Do not trade on `direction_bias` until TD-035 is fixed and `wcb_regime` is populated. (Session 11 extension live session.)
- ✅ Options-only framework (Experiment 2b, 2026-04-12)
- ✅ T+30m exit timing (Experiment 8/14b/15, multiple confirmations)
- ✅ BEAR_OB AFTERNOON → HARD SKIP (Signal Rule Book v1.1, 17% WR)
- ✅ **Naked intraday PDH/PDL sweeps have no edge** (Exp 34, Session 11) — WR=11.1% (PDH), 1.8% (PDL) at T+60m. ~0.73 events/session — normal mean reversion, not institutional. Do not retest without structural change.
- ✅ **PDL DTE<3 next-week CE = SKIP** (Exp 35D, Session 11) — T+1D WR=42.9%. EOD bounce is mechanical expiry pinning, not institutional. Fades next day. Confirmed.
- ✅ **BEAR_OB AFTERNOON + PO3_BEARISH = 33.3% WR** (Exp 40, Session 11) — the distribution move is already done by AFTERNOON on bearish-bias sessions. Hard skip. Do not trade.
- ✅ **BULL_OB MIDDAY + PO3_BULLISH = 30.3% WR** (Exp 40, Session 11) — premature. Bullish accumulation doesn't resolve until AFTERNOON London open. Hard skip.
- ✅ **NIFTY BULL_OB AFTERNOON + PO3_BULLISH = 50% WR** (Exp 40, Session 11) — no edge on NIFTY for this signal. SENSEX only (73.7%). Do not route NIFTY here.
- ✅ **Current-week PE beats next-week PE for PDH DTE<3** (Exp 41, Session 11) — NIFTY mean +46% vs +20%, SENSEX mean +125% vs +68%. Current-week captures gamma explosion. Settled.
- ✅ **Entry at T+0 (rejection bar close) always beats waiting** (Exp 41, Session 11) — waiting 1 bar hurts across all edges and both symbols. Never wait.
- ✅ **Exp 42 DONE** (Session 13, 2026-04-29) — BEAR_OB MIDDAY occurs in 72.5% of all sessions. Unfiltered WR=48%, EV negative. PO3_BEARISH is the rare gate (~7% of sessions). Composition rate question answered. Do not re-run.
- ✅ **Universal big-move-day capture rate 99.2% (118/119)** (Session 34, 2026-05-24) — MERDIAN's ICT primitive layer sees every ≥1% intraday move structurally over the 14-month vendor window. Audit: 119 ≥1% intraday move-days across 2025-04-01 → 2026-05-19 (57 NIFTY + 62 SENSEX, parity threshold) joined to `ict_primitives` with direction-aligned + zone-interaction filters; 118 captured, 1 miss (NIFTY 2025-05-20 DOWN — DISPLACEMENT_DOWN existed but price didn't reach zone). Origin distribution: FVG 84% (BEAR_FVG 47%, BULL_FVG 36%), OB 16%; timeframe D+W 74% (D 47%, W 27%), H 14%, M5 11%. Standout zone-reuse cases: 2026-04-06 W BULL_FVG fired on 4 ≥1% UP days; 2025-04-04 D BEAR_FVG (~354 days old) anchored the March 2026 crash days; 2025-04-15 W BULL_FVG triggered 5 reactions across the year. **Capture is not the binding constraint on trade discoverability — selection is.** Codified as D.16.1 + D.16.2 in Assumption Register. Do not re-derive capture-rate audit on the same 14-month window; result is established.
- ✅ **Selection problem articulated** (Session 34, 2026-05-24) — Selection (which active zone of 50+ fires today) is the unsolved problem; capture (does MERDIAN have an aligned zone at all) is solved at 99.2%. Selection-research arc framed as 3-5 session work item; framework doc deferred to S35+ per operator sequencing (SL fix → file gap → file arc → first feature). Five candidate selection features identified for future research: pre-open structural signature (gap + multi-TF aligned + sweep); same-day momentum confirmation gate (first H bar close direction); HTF context alignment (require W direction alignment for D zones); zone freshness (first-touch > N-touch retest hit rate); DTE-aware option leg selection (extends S33 DTE 3-bucket finding). ENH-108 N-touch retest detection is the foundational schema unlock for selection research — without per-touch outcomes data, "is this primitive being touched right now for the Nth time and what's the empirical hit rate by N?" cannot be answered. Do not collapse selection into capture; they are distinct problems with distinct solutions.
- ✅ **GEX-as-context-not-gate** (Session 37, 2026-05-25) — Operator framing: *"Meridian doesn't need anymore gates. It's already gating everything."* MERDIAN already operates 5 gating layers (ADR-001 stability+validity two-layer gate; ENH-55 falsified and env-disabled; routing-data-driven SKIP for BEAR_FVG; proximity tiers T1/T2/T3 on Pine overlay; ADR-009 graduated-strictness holdout calibration). ENH-80 + ENH-81 ship as **display layer** (Lovable dashboard for at-a-glance regime read; Pine overlay PIN/ACCEL zones for chart-time corroboration) — not as automated routing inputs to `build_trade_signal_local.py`. PE/CE GEX split preserved in schema (ADR-015 `gamma_call`/`gamma_put`) but not surfaced in dashboard or Pine — research-grade column for future inversion-based dealer-flow research. Operator is the integration layer for GEX-derived decisions. Do not wire GEX as a gate in `build_trade_signal_local.py` without explicit operator request AND N≥30 live-cohort validation per D.13.1 cohort-translation discipline.
- ✅ **A "latest snapshot" selector must never order by `created_at`.** `ingest_option_chain_local.py` computes `snapshot_ts` ONCE and reuses it, so every expiry in a cycle shares one `ts` — but **not** `created_at`, a DB-side default and therefore later for the extra-expiry pass. Two production selectors ordered by exactly the column that differs, so at capture depth ≥ 2 the runner would have handed gamma, volatility and options flow **W2's `run_id` from the first cycle**, silently: each `run_id` is still single-expiry, so TD-S79-NEW-12's guard sees one expiry and returns W2's date without raising, and `gamma_metrics.dte` jumps 0/2 → 7/9. **Canonical form: `order="ts.desc,expiry_date.asc"` — latest snapshot, then its front expiry.** Deliberately **no `">= today"` guard** in the orchestrator, unlike the views: the ingest never writes past expiries, and a no-fallback guard there converts an edge case into a **compute outage** rather than a display gap. Note also that **ADR-025 A1's stdout `Run ID:` precondition is TRUE and guards nothing here** — the AWS runner never reads that line, it re-queries the table (`89ad2bb`, ADR-025 B5).

**Standard check — SQL helper:**

```sql
SELECT public.is_breadth_contaminated(ts) FROM your_query;
-- Or filter:
WHERE NOT public.is_breadth_contaminated(ts)
```

**For non-breadth fields:**

```sql
SELECT * FROM public.data_contamination_ranges
WHERE field_scope ILIKE '%your_field%';
```

**When to add a new entry:**

Whenever a new data-integrity incident is diagnosed, INSERT a row into `data_contamination_ranges` with:
- Unique `contamination_id` (pattern: `SCOPE-DESCRIPTION-YYYY-MM-DD`)
- `field_scope` (comma-separated list of affected column/field names)
- `contamination_start` and `contamination_end` (timestamptz, IST)
- `affected_tables` (array of table names, including views' underlying tables)
- `root_cause` (what broke)
- `remediation` (how it was fixed)
- `created_session`

**Current registered contamination ranges (2026-04-23):**
- `BREADTH-STALE-REF-2026-03-27`: 27-day breadth cascade (Session 7). See `merdian_reference.json` TD-NNN for context.

**Anti-pattern:** Running experiments on historical data without first checking `data_contamination_ranges`. Research conclusions drawn on tainted data are worse than no conclusions.

- **ADR-019 (S58) — signal-subsystem orphans are PORTED, not retired, and retirement requires evidence a capability has NO value — never an experiment verdict.** The three S49 orphans (options_flow + iv_context -> shadow-v3) went dark from a migration-scope wiring gap, not a failed test. Verdicts don't reliably transfer (SMDM scored NEUTRAL then was rebuilt as ENH-SDM). Default for a migration-orphaned subsystem is port-sequenced-behind-a-live-consumer; deletion needs a separate explicit decision once its owning ENH closes.
- **ENH-SDM is observability-first: a single validated case justifies MEASURING conditions, never ACTING on them (S58).** CASE-2026-06-02 (+71%) is one day; N~8 across the gamma_metrics history; the backward study to grow N is blocked behind a Greeks backfill (purchased chain has 0% Greeks, TD-S58-NEW-1). So ENH-SDM ships as a display-not-gate monitor (per S37 GEX doctrine) and the cohort accrues forward; signal/modes gated on N. Codified: do not build a signal off one case — build the monitor, let the cohort form.
