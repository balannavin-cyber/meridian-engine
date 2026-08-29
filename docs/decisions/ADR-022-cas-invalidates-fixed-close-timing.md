# ADR-022 — The settled close is an announced equilibrium price, not a wall-clock constant: SEBI's Closing Auction Session invalidates every fixed 15:30 anchor in the EOD pipeline

| Field | Value |
|---|---|
| Status | **Accepted** (doctrine accepted; per-job re-anchoring is the tracked follow-up) |
| Date decided | 2026-08-13 |
| Date documented | 2026-08-13 (S69 interim capture) · formalised S70 from capture v2 |
| Session | Session 69 |
| Supersedes | The implicit system-wide assumption *"15:30 IST = clean settled close"*, in force since V11 and never written down. Recorded and refuted as Assumption Register **D.27.1**. |
| Related ENH / TD / ADR | ADR-002 v2 (market structure philosophy — external market-structure change forces adaptation) · ADR-001 (stable lies) · ADR-016 (`OB_MIN_MOVE_PCT` calibration) · ADR-009 (calibration discipline) · ADR-019 (M5 detector disposition) · TD-S69-NEW-5 (M5 detector is a Local-only orphan) · TD-S69-NEW-8 (daily-lookback verification) · Rule 18 (`trading_calendar` is a trust-anchor) |
| Rule 10 class | **Deployment-topology change + reversal of a settled (if undocumented) decision.** Mandatory ADR. |
| External source | SEBI circular on the Closing Auction Session; NSE *Closing Auction Session* product page; effective **2026-08-03**. Re-verified at the S70 doc-close before this ADR was written. |

---

## Context

MERDIAN's entire EOD layer was built against a market that closed at 15:30 IST. That is no longer the market MERDIAN trades.

**Effective 2026-08-03**, SEBI introduced the Closing Auction Session (CAS) for Category-I securities — every equity-cash stock with active F&O contracts — across NSE, BSE and MSEI:

| Segment | Before 2026-08-03 | From 2026-08-03 |
|---|---|---|
| **Category-I (F&O) stocks** — continuous trading | 09:15 → **15:30** | 09:15 → **15:15** |
| **Closing price, Category-I** | VWAP of trades 15:00–15:30 | **CAS equilibrium price.** Auction 15:15–15:35: order collection 15:15–15:30, matching + price publication 15:30–15:35. Reference price = VWAP **15:00–15:15**. Band ±3% of reference; limit + market orders only (no stop-loss, no iceberg). |
| **Category-II (non-F&O) stocks** | 09:15 → 15:30, VWAP 15:00–15:30 | **unchanged** |
| **Equity derivatives (index + stock F&O) — MERDIAN's instruments** | 09:15 → 15:30 | 09:15 → **15:40** |
| **Post-close** | 15:40–16:00 | **15:50–16:00** |
| **Pre-open** | 09:00–09:15, fixed phases | restructured from **2026-09-07**: 09:00–09:05 market+limit · 09:05–09:10 limit-only with system-driven **random close 09:08–09:10** · 09:10–09:12 matching · 09:12–09:15 transition |

Market open time is unchanged; commodity and currency segments are untouched.

The implication MERDIAN cares about most is second-order. **NIFTY and SENSEX are computed from constituents that are all Category-I names.** So the index's own settled level is now derived from CAS equilibrium prices published in the **15:30–15:35** window — and the index derivatives that MERDIAN actually trades keep trading for five minutes *after* that, to 15:40. There is no longer any instant at 15:30 at which "today's close" exists.

This was found in S69 as a side-thread while diagnosing why the M5 ICT detector had written nothing since 2026-06-02. The `MERDIAN_ICT_EOD` Local task fires at **15:35** — squarely inside the auction/extended-derivatives window. It has been doing so since 2026-08-03 with nobody noticing, because a task that runs, exits 0, and writes zero rows looks identical to a quiet market.

## Decision

**Three rules, in force from acceptance.**

**D1 — No job may treat a wall-clock time as equivalent to "the close."** Any EOD-anchored job must fire strictly after the last event that can change the settled series it reads. For MERDIAN's instruments that boundary is **15:40 IST**, and the safe anchor is **≥ 15:45 IST**. `MERDIAN_ICT_EOD` moves from 15:35 to **15:45 or later**; every other close-anchored job is audited against the same boundary.

**D2 — "Settled close" for an F&O-linked instrument means the CAS equilibrium price, not a VWAP.** Any code, comment, doc or column that describes the close as "the 15:00–15:30 VWAP" is now wrong for Category-I names and for the indices derived from them. `eod_spot` and every daily-OHLC consumer must be verified to be reading the vendor's *final* settled value, not an intraday-derived one — and the vendor's own publication time for that value must be established, not assumed.

**D3 — A market-structure change is a first-class trigger for a pipeline audit, on the same footing as a schema change.** External timing/definition changes do not announce themselves in any log MERDIAN owns. They are found by reading exchange circulars, and the finding must produce an ADR and a job-by-job sweep — not a single patched cron line.

**Exposure inventory at acceptance** (the D1/D2 audit scope, carried as this ADR's open follow-up):

| Job | Schedule | Exposure |
|---|---|---|
| `MERDIAN_ICT_EOD` → `detect_ict_patterns_runner.py` | **15:35 IST** (Local Task Scheduler) | **Fires inside the auction / extended-derivatives window.** Its 5-minute bars for the last slot are no longer settled continuous-session bars. **Must move ≥ 15:45.** |
| `build_ict_htf_zones.py` daily-close logic | EOD | Daily OHLC may be assembled mid-auction; the D-timeframe close definition itself changed for F&O-linked instruments. Note this file was also changed in S69 for an unrelated reason (`a4bdb4c`, daily lookback) — the CAS exposure is independent of that fix and is **not** addressed by it. |
| ambient compiler `eod_spot` / settlement anchor | `0 16` (16:00 IST) | Wall-clock is safe (after 16:00). **The definition is not** — must be confirmed to read the CAS-settled value. |
| `capture_postmarket_1600.py` | `30 10` UTC (16:00 IST) | Post-everything under the new 15:50–16:00 post-close, but confirm rather than assume — post-close now *ends* at 16:00. |
| `market_spot_session_markers` | `40 10` UTC (16:10 IST) | Wall-clock safe; **close semantics** need confirming (which value becomes `prev_close`). |
| Pre-open dependent logic | — | **Dated exposure: 2026-09-07.** Random close 09:08–09:10 means the pre-open equilibrium is no longer available at a fixed instant. |

## Evidence (rationale)

This is a regulatory fact, not a measured finding: the timings above are stated in the SEBI circular and reproduced on the NSE Closing Auction Session product page, effective 2026-08-03, and were independently re-verified at the S70 doc-close before this ADR was written.

The *system* evidence is the M5 detector. `ict_zones` newest ACTIVE `trade_date` is **2026-06-02** — 53 trading days stale at capture. The Local task is `State: Ready`, `LastTaskResult: 0`, `LastRunTime: 2026-08-13 17:13`. It runs, it succeeds, it writes nothing. The dominant cause of the *freeze* is the ADR-016 threshold problem (`OB_MIN_MOVE_PCT = 0.40%` against 30-session maxima of NIFTY 0.366% / SENSEX 0.369% — nothing can clear it), so CAS is not why the table is frozen. But CAS is why, **once the threshold is recalibrated, the detector would have started writing auction-contaminated bars** — a corrected threshold would have produced confidently wrong zones. The two defects were stacked, and fixing only the loud one would have shipped the quiet one into production.

That is the generalisable point: **an external timing change is invisible to every health check the system owns.** No writer errors, no exit code, no freshness alarm. It surfaces only as slightly-wrong data, which is exactly the failure class ADR-001 exists to refuse.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| **Move `MERDIAN_ICT_EOD` to 15:45 and stop there** | **Rejected as sufficient.** It fixes the one job that was found and leaves five others resting on the same refuted assumption. The assumption is the defect; the cron line is one instance of it. |
| **Leave 15:35 — "five minutes of auction won't move a 5-minute ICT bar much"** | **Rejected outright.** The magnitude of the error is unknown and unmeasured, and the whole point of the M5 detector is displacement thresholds measured in tenths of a percent (ADR-016). An unquantified contamination on the exact quantity being thresholded is not tolerable, and "probably small" is a stable lie (ADR-001). |
| **Anchor EOD jobs to a data-driven signal (wait until the vendor publishes a settled bar) rather than a clock** | **Deferred, not rejected — the better long-run design.** It removes the constant entirely and would survive the next timing change without an ADR. Not adopted now because it needs a per-vendor definition of "settled" that MERDIAN does not yet have (D2 must land first). Recorded as the successor design. |
| **Treat CAS as a data-quality problem and filter auction bars downstream** | **Rejected.** Pushes a market-structure fact into every consumer separately — the same fork-the-definition error rejected in ADR-021. Re-anchor once, at the schedule. |
| **Wait for the vendor (Dhan/Zerodha) to signal the change** | **Rejected.** Vendors publish bars; they do not publish "your assumptions are now wrong." The S69 finding came from reading the circular, which is the only channel that carries it. |

## Consequences

**Positive**
- The EOD layer gets an explicit, written boundary (15:40 / safe ≥ 15:45) where it previously carried an unwritten constant.
- The M5 detector recalibration (ADR-016 follow-through) can now proceed without silently importing auction bars into the very measurement being recalibrated.
- MERDIAN gains a documented trigger class — external market-structure change — that previously had no home in the protocol.

**Negative**
- Every EOD-anchored artefact produced between **2026-08-03** and the completion of the D1 re-anchoring is of uncertain timing provenance. In practice the blast radius looks small (the M5 detector wrote nothing in the window, and the 16:00+ jobs are wall-clock safe), but "small" here is inferred, not measured.
- The EOD chain finishes later, compressing the post-close window before the ambient compiler's `0 16` slot.
- A second, dated exposure lands **2026-09-07** (pre-open restructure) and must be handled before it goes live, not after.

**Mitigations**
- Deployment Topology §S69 carries the new session-timing table as the reference; no job schedule is to be reasoned about from memory of "15:30".
- Assumption Register **D.27.1** records the refuted assumption so it cannot be silently re-adopted.
- The 2026-09-07 pre-open change is filed as a dated follow-up rather than a vague one.

## Relationship to other documents

- **ADR-002 v2** — market-structure philosophy. This is that philosophy meeting an actual change in market structure: the principles are unchanged, the clock they were calibrated against is not.
- **ADR-016** — `OB_MIN_MOVE_PCT` recalibration must land **after** the D1 re-anchoring, or the recalibrated cohort is measured on auction-contaminated bars.
- **ADR-009** — the recalibration is still bound by calibration discipline: SQL committed to `docs/research/` before any register entry, because changing the threshold invalidates the WR cohort behind every `WR 84%` / `WR 92%` label.
- **ADR-019** — retirement requires evidence of no value. The M5 detector's silence is a threshold + timing defect, not evidence of worthlessness; it is repaired, not retired.
- **Rule 18** (`trading_calendar` is a trust-anchor, validate against the official NSE source) — this ADR is the same lesson one level up: **session *timings* are as much an external trust-anchor as session *dates*.**

## AMENDMENT 1 (Session 71, 2026-08-29) — D1 answered; exchange hours confirmed; the 15:29 bar is a vendor artefact

### A1.1 — D1 CLOSED: the intraday window audit, job by job

Eight job groups audited against the CAS window. **Five lines extended, four deliberately not** — see System Map §S71.B for the full verdict table. Extended to `0,5,10 10 * * 1-5` (15:30 / 15:35 / 15:40 IST): index futures ×2, `run_ingest.sh` ×2, breadth at `0-10 10`. Not extended: `capture_spot_1m_v2` (index frozen, guard already at 15:15), the hour-`03` ingest pair, `build_wcb_snapshot_local` (chain consumer), the shadow runner (contracts written against different semantics).

A blanket `09` → `10` — the form TD-S70-NEW-6 proposed — would have polled to 16:25 IST and collided with the detectors at `10:20`/`10:22` and `capture_cas_close.py` at `10:50`.

### A1.2 — Exchange hours CONFIRMED against NSE

**Equity Derivatives Segment: 9:15 am – 3:40 pm.** Non-CAS cash continuous trading: 9:15 – 3:30. Corroborated operationally by Zerodha (F&O GTT orders and price alerts trigger until 3:40 PM, versus 3:30 PM for non-F&O). Rationale: F&O contracts settle against the equity cash closing price, which CAS now finalises later, so derivatives were extended ten minutes to keep cash and F&O aligned.

The register's 15:40 figure was correct. The Session 71 scepticism about it was wrong, and is recorded as such.

### A1.3 — The "15:29 bar" in this ADR describes a Dhan artefact, not the exchange schedule

This ADR states that the settled close lands in the 15:29 bar. NSE publishes the CAS equilibrium price **between 3:30 and 3:35**. MERDIAN's own observations: the settled close arrives in the **15:34** bar on 2026-08-03/04/05 and in the **15:29** bar from 08-20 onward.

The 15:34 observations match the exchange schedule. The 15:29 ones do not — which means the change is in **Dhan's bar timestamping**, not in the auction. The ADR's rationale should be read as describing the vendor's presentation of an exchange event, and any future vendor change will move it again.

`capture_cas_close.py` now handles both: the accepted-slot set `{15:29, 15:34}` governs **acceptance**, and the canonical `CAS_CLOSE_BAR` governs **storage**, with the true vendor slot preserved as `raw.bar_slot_ist`. That separation is what keeps a vendor timestamping shift from becoming a second closing bar per session.

### A1.4 — The auction window is a semantic discontinuity, and it is a READ-path concern

During the auction all Category-I constituents are in the auction, so the index has no continuous input and does not move, while options and futures keep trading against it. GEX computed against a pinned spot is not the same quantity as GEX computed against a live one — same column, different meaning.

A write-path marker was proposed and **rejected on reading the code**: `ingest_option_chain_local.py:223` stores `"raw": option_raw`, the vendor payload verbatim, and annotating it would destroy that field's only property. The window is in any case a pure function of `ts`, which every row already carries.

**Consumers scope the 15:15–15:40 discontinuity on `ts` at read time**, per the ADR-021 derived-view pattern. No schema change, no new column, no ingest-path code.

---

## Governance language

> **The settled close is an announced equilibrium price, not a wall-clock constant (ADR-022, S69).** SEBI's Closing Auction Session (live 2026-08-03) ended continuous trading for F&O stocks at 15:15, sets the close by auction 15:15–15:35 (reference = VWAP 15:00–15:15), and extends index/stock derivatives to **15:40** (post-close 15:50–16:00; pre-open restructured 2026-09-07). NIFTY/SENSEX are built from Category-I constituents, so the index close now lands ~15:35–15:40. **No EOD job may fire before 15:40; safe anchor ≥ 15:45** — `MERDIAN_ICT_EOD` moves off 15:35. "Close" for an F&O-linked instrument means the CAS equilibrium price, never a 15:00–15:30 VWAP. An external market-structure change is a first-class audit trigger: it is invisible to every health check MERDIAN owns and surfaces only as slightly-wrong data.

## Open follow-ups

1. **P0 — re-time `MERDIAN_ICT_EOD`** from 15:35 to ≥ 15:45. Smallest, most exposed item; do it first.
2. **P0 — job-by-job D1/D2 audit** of the six-row exposure inventory above; record each verdict in Deployment Topology §S69.
3. **P0 — establish the vendor's settled-close definition and publication time** (Dhan daily OHLC; Zerodha historical) for Category-I instruments post-CAS. D2 cannot be verified without it.
4. **P1 — ADR-016 follow-through** (`OB_MIN_MOVE_PCT` 0.40% → candidate 0.25%) *after* item 1, under ADR-009 discipline.
5. **P1 — dated: 2026-09-07 pre-open restructure.** Audit any pre-open-anchored logic before that date; the random close 09:08–09:10 removes the fixed pre-open instant.
6. **P2 — successor design:** replace clock anchors with a data-settled trigger, so the next timing change costs zero ADRs.

---

*ADR-022 — 2026-08-13 — Session 69 — found while chasing a frozen detector, which is the only reason it was found at all. Nothing in the system reported it, because nothing in the system can: the pipeline kept running correctly against a market that had moved. Two defects were stacked on the same job, and repairing the loud one alone would have shipped the quiet one into production.*
