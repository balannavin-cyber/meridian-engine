# ADR-003 — ICT Zone Detection Architecture Review (PHASE 1 RUN — RESULT INVALID, v3 NEEDED)

**Status:** PROPOSED 2026-04-30 (Session 14, end-of-day operator observation). Phase 1 RUN Session 15 (2026-05-01) — verdict INVALID (script-side TZ-handling methodology bug, NOT an architecture finding); Phase 1 v3 with era-aware Rule 16 deferred to Session 16+. **The decision driver remains UNRESOLVED.** Bonus: Phase 1 setup discovered and closed an unrelated 13-month BEAR_FVG production defect (TD-048).
**Decision driver:** Operator observation that ICT zones drawn by `build_ict_htf_zones.py` are not reflecting actual price-pivot behavior reliably this week, despite working "last week". Specific symptom: zones either (a) sit far from where intraday price respects/rejects, or (b) old zones remain ACTIVE despite price clearly invalidating them, or (c) fresh structural pivots intraday don't get captured as new zones.

## Context

The ICT zone detection layer is foundational. ENH-76 / ENH-77 / ENH-78 / ENH-46-D / dashboard / Pine all read from `ict_htf_zones` and trust the zones' boundaries + status. If the zone layer is misaligned, every signal downstream is operating on bad context.

This concern is NOT new — it has surfaced over multiple sessions in different forms:
- TD-030 (CLOSED Session 11 ext) — `recheck_breached_zones()` not running, zones never marked BREACHED
- TD-031 (CLOSED Session 11 ext) — D BEAR_OB underactive (filter timing bug)
- TD-040 (CLOSED Session 13) — recheck order overwrote BREACHED → ACTIVE every rebuild
- TD-042 (CLOSED Session 13) — Pine bar_index negative on old zones (rendering, not detection)
- TD-047 (Session 14) — `ict_zones` vs `ict_htf_zones` two-table architecture confusion

The pattern is: each session finds a different specific bug in the zone layer, fixes it, but the operator's underlying confidence in zone correctness has not stabilized. Today's observation suggests the cumulative fixes have not addressed something more fundamental.

## Hypotheses (not yet tested)

1. **Detection thresholds tuned to wrong regime.** Current OB threshold (0.40% NIFTY, 0.30% SENSEX from Exp 29 v2 Session 10) may be calibrated for a normal-vol environment. Current week is high-vol (today -1.5% NIFTY). Threshold may admit too many noisy candidates or miss real structural pivots.
2. **5m basis is too noisy for HTF zones.** ADR-002 settled "5m for ICT", but H/D/W zones may need source bars at the same TF as the zone (D zones from D bars, not 5m bars rolled up).
3. **Breach detection is necessary but not sufficient.** Marking a zone BREACHED is a binary outcome — but zones can also EXPIRE / become STALE without being broken (e.g. price moves away, the zone becomes structurally irrelevant). No "stale" status currently exists.
4. **Zone validity windows (`valid_from` / `valid_to`) may be too long.** Default 30-day weekly zone window may persist zones past their useful life. Today's spot is reading against zones from 04-06 to 05-08 — three weeks of lookback, possibly too long for the current move structure.
5. **Order block detection logic may be wrong.** Standard ICT OB definition is "the last opposite-direction candle before a strong directional move". MERDIAN's `detect_order_blocks()` implementation may not match this definition exactly. Worth code review against ICT canon.
6. **PDH/PDL coverage may be misaligned.** Daily PDH/PDL is defined by yesterday's high/low — but yesterday vs which session? Cash session 09:15-15:30? Or 24h day? Or NSE/BSE close timestamp?
7. **The whole concept may not work in current regime.** ICT works best in mean-reverting environments. Trending environments (today, this week) may simply not respect HTF structures at the same rate. The edge may be regime-conditional.

## Decision required

NOT this session. NOT this week. This needs a structured diagnostic before any redesign work.

**Proposed work plan:**

| Phase | Session | Output |
|---|---|---|
| **Phase 1 — Diagnostic** | Session 15 (or 16 if ENH-79 takes priority) | Pull last 10 trading days. For each day: query `ict_htf_zones` ACTIVE zones at session open; identify intraday pivots in `hist_spot_bars_5m`; compute "respect rate" — % of pivots that occurred within X points of an active zone boundary. Per-symbol, per-pattern-type. Publish numeric truth. |
| **Phase 2 — Targeted redesign** | Sessions 16-17+ | Only after Phase 1 identifies WHICH layer is broken (W vs D vs H, OB vs FVG vs PDH-PDL, threshold vs validity window vs definition). Targeted, not from-scratch. |
| **Phase 3 — Rebuild + validation** | Sessions 17-18+ | Implement, deploy with shadow window, compare old-vs-new respect rates, cut over only on >X% improvement. |

## DO NOT

- Do NOT touch `build_ict_htf_zones.py` reactively in Session 15 based on intuition. Diagnosis first.
- Do NOT propose a full rewrite without numeric evidence of which layer is broken.
- Do NOT block ENH-79 build on this — ENH-79's PWL weekly sweep is a different signal layer (price levels, not zones).
- Do NOT re-litigate TD-030/031/040/042/047 closures. Those were real fixes, just incomplete.

---

## Phase 1 Results (Session 15, 2026-05-01) — INVALID verdict, methodology bug

### What ran

Two scripts, run in sequence:

- **`adr003_phase1_zone_respect_rate.py` (v1)** — first pass at the diagnostic specified in the work plan above. Pulled active zones from `ict_htf_zones` and `hist_ict_htf_zones` for last 10 sessions; for each zone, found 5m bars where spot entered the zone (high ≥ zone_low AND low ≤ zone_high); classified each entry as RESPECTED (spot reversed within zone) or BROKEN (spot exited the other side); computed respect-rate per (symbol, timeframe, pattern_type).
- **`adr003_phase1_zone_respect_rate_v2.py`** — re-run after v1's raw 0% result triggered investigation. Same logic as v1 with refinements to entry/exit classification.

### Raw findings (v1 + v2)

- **Respect-rate: 0% across all timeframes for both symbols.** Every "zone touch" classified as BROKEN.
- **Apparent post-04-07 `hist_spot_bars_5m` bar coverage: 27.5%.** (Pre-04-07 era showed ~100% coverage.)
- **D zone count in 10-day lookback: 0.** No D-OB, D-FVG, or D-PDL/PDH zones found in the lookback window despite W zones being plentiful.

These three results would have been damning evidence of architecture failure if true. Two of the three were artifacts.

### Mid-investigation diagnosis — two independent bugs surfaced, neither in the architecture

**Bug 1 — Script-side TZ-handling methodology bug (the one that invalidates Phase 1).** The v1/v2 scripts applied CLAUDE.md Rule 16 verbatim to the entire date range. Rule 16 says: apply `replace(tzinfo=None)` to `bar_ts` and filter to in-session 09:15-15:30. **This is correct for the pre-04-07 era only.** Pre-04-07, bars were stored as IST-clock-time-labelled-as-UTC (TD-029 root cause). Post-04-07, bars are stored as true UTC. Applying Rule 16 verbatim post-04-07 produces a UTC clock-time, and filtering to 09:15-15:30 IST drops most of the day — keeping only bars that fall in the UTC 09:15-10:00 window which corresponds to IST 14:45-15:30 (the last 45 minutes of the session).

This explains the 27.5% bar coverage figure: ~9 of ~76 in-session bars passed the filter on post-04-07 days. With ~78% of the bar evidence missing, "did spot reverse within the zone?" defaulted to BROKEN for almost every zone touch — there were no bars to evidence the reversal.

Confirmed by running `diagnostic_bar_coverage_audit_v3.py` which uses the `trade_date` column instead of `bar_ts` time filter — real coverage post-04-07 is ~100%. Filed as **TD-053 (CLAUDE.md Rule 16 needs era-aware addendum)** during Session 15 closeout.

**Bug 2 — D-zone non-FVG validity = 1 day (the one that explains "0 D zones in lookback").** The historical zone builder writes D-OB and D-PDH/PDL zones with `valid_to = valid_from = target_date` — exactly 1 day validity. By definition, every D zone older than today expires before any 10-day lookback query can see it. Filter `valid_from ≤ lookback_start AND valid_to ≥ today` excludes them all. **This is a genuine architecture finding** but it predates ADR-003 — it's been present since the historical builder was written. Filed as **TD-050 (D-zone non-FVG validity = 1 day)** during Session 15 closeout.

### Verdict — Phase 1 INVALID

Methodology compromised by Bug 1 (TZ-handling) AND Bug 2 (D-zone validity). Without era-aware TZ handling, the respect-rate metric measures the bug, not the architecture. Re-run as Phase 1 v3 with both bugs fixed before any architecture verdict can be drawn.

### Bonus — Phase 1 setup discovered an unrelated 13-month production defect

While Phase 1 was running, Exp 50 (FVG-on-OB cluster vs standalone) ran on the same dataset and surfaced that `hist_pattern_signals` contained 1,261 BULL_FVG and 0 BEAR_FVG over 13 months — impossible per market structure. That triggered a 5-step BEAR_FVG audit, six-bug code review of the zone builders, and S1 patches that were shipped end-to-end in Session 15 (closing **TD-048**). Pipeline now symmetric: 0 BEAR_FVG → 795 BEAR_FVG signals.

This is unrelated to ADR-003's architecture question (the BEAR_FVG bug was missing detection branches in the builder, not zone-quality calibration), but it is relevant context: **the architecture review was running on a dataset that was structurally one-sided**. Any Phase 1 v3 re-run uses the now-symmetric data.

### Cross-reference correction (Session 15 closeout addendum)

The "Context" section above lists TD closures that don't all match the canonical state in `tech_debt.md` as of 2026-05-02. Operator and Session 14 author wrote what they believed to be true at the time:

- **TD-030 ("CLOSED Session 11 ext")** — `tech_debt.md` shows TD-030 still **OPEN**. The `recheck_breached_zones` ordering bug (Session 13) was patched, but the broader "no re-eval on existing zones" framing was never closed.
- **TD-031 ("CLOSED Session 11 ext")** — `tech_debt.md` shows TD-031 still **OPEN**, expanded by Session 15 (D-FVG portion closed via TD-048; D-OB portion remains as TD-049).
- **TD-040 ("CLOSED Session 13")** — TD-040 does not exist in `tech_debt.md`. Session 14 `session_log.md` references TD-044/045/046/047 but `tech_debt.md` jumps from TD-039 to TD-048 (Session 15 numbering). The Session 13 TD work referred to here was likely closed at the session-narrative level but never filed in the register.
- **TD-042 ("CLOSED Session 13")** — also does not exist in `tech_debt.md`.
- **TD-047 ("Session 14")** — also does not exist in `tech_debt.md`.

Filed as a known historical gap in `tech_debt.md` (Session 15 closeout block at TD-048 prefix). Not corrected here — the original author's reasoning was based on the session_log narrative, not register state, and that's the document that should remain readable as-is.

### Phase 1 v3 plan (Session 16+)

| Element | Plan |
|---|---|
| **Script** | `adr003_phase1_zone_respect_rate_v3.py` — fork of v2 with era-aware TZ handling. |
| **TZ fix** | Replace verbatim Rule 16 application with: pre-04-07 → `replace(tzinfo=None)`; post-04-07 → `astimezone(IST_TZ)`. Or use `trade_date` column for date filters and `bar_ts` only for ordering — eliminates the issue. Recommended: the latter. |
| **D-zone fix workaround** | For D zones, drop the `valid_to ≥ today` filter. Pull the most recent ACTIVE-status D zone per (symbol, pattern_type) regardless of `valid_to`. This sidesteps TD-050 for the diagnostic — fixing TD-050 itself is a separate Session 16 Candidate D item. |
| **Sample window** | Last 10 trading days (per original plan). Verify with operator if a longer window is preferred — full 13 months now produces enough events post-fix. |
| **Other carry-forwards** | TD-053 (CLAUDE.md Rule 16 era-aware addendum) should be addressed in the same session — adding the addendum surfaces the bug everywhere it currently sits dormant. |
| **Decision rule** | Same as Phase 1 v1/v2: per-symbol, per-pattern-type respect rate published as numeric truth. >50% respect = layer working. <30% = layer broken. 30-50% = needs sub-investigation by zone age, market regime, or zone width. No architecture verdict from a single number — the goal is to identify WHICH layer is broken (W vs D vs H, OB vs FVG vs PDH-PDL). |

### What Session 15 changed in this ADR

- Status updated from PROPOSED to PHASE 1 RUN — RESULT INVALID
- Phase 1 verdict published (INVALID due to methodology bugs, not architecture findings)
- Two TDs filed as a result of Phase 1 investigation: TD-053 (Rule 16 era-aware), TD-050 (D-zone single-day validity)
- One unrelated TD CLOSED as a side-effect of Phase 1 setup: TD-048 (BEAR_FVG defect)
- Phase 1 v3 plan documented with concrete fix path
- The original DO NOT list (above) remains in force. The "Do NOT touch `build_ict_htf_zones.py` reactively" rule was technically violated by Session 15's BEAR_FVG fix, but the violation was justified: TD-048 was a separate detection-completeness bug (missing direction branch), not a zone-calibration question. The zone-calibration question (what Phase 1 was supposed to answer) remains open.
- The architecture review is **not closed**. Phase 1 needs a clean run before Phase 2 can begin.

---

## Status

- **PROPOSED** 2026-04-30 (Session 14)
- **PHASE 1 RUN — RESULT INVALID** 2026-05-01 (Session 15) — methodology bug, see Phase 1 Results above
- **PHASE 1 v3 NEEDED** 2026-05-02 — Session 16+ Candidate C
- Operator concern logged. Architecture verdict still pending.
- File at `docs/decisions/ADR-003-ict-zone-architecture-review.md` when committing.
