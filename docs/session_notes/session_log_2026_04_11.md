# MERDIAN Session Log

---

## Entry 2026-04-11 — Research + ENH-35 Validation + ENH-37 Full Build

**Session type:** Research + Engineering
**Git range:** 858de8f → 26c5e72
**Shadow gate:** 8/10 (sessions 9+10 Monday/Tuesday)

---

### What Was Done

**Expiry bug discovered and fixed:**
NIFTY switched Thursday→Tuesday expiry around September 2025. Hardcoded `EXPIRY_WD = {"NIFTY": 3}` in all experiment scripts caused every post-August session to be skipped as "no option data." DB confirmed full coverage Apr 2025–Mar 2026 (39 zones/day average). Fix: `merdian_utils.py` with DB-driven `build_expiry_index_simple()` + `nearest_expiry_db()`. All 11 experiment scripts patched via `patch_expiry_fix.py`.

**Experiments 14 + 14b — Session pyramid closed:**
Exp 14 (v1 mid-bounce entry): Pyramid -₹9,044 (22% WR) vs single T+30m +₹8,329 (100% WR) across 9 sessions.
Exp 14b (v2 confirmed reversal): Improved v1 by ₹3,133 — confirmation logic correct but still -₹12,645 vs single trade.
Verdict: Single T+30m exit on first OB remains optimal. Session pyramid deferred to post-ENH-42 (WebSocket).
All 9 qualifying sessions were BEARISH — asymmetric dataset. Needs bullish sessions + real-time feed.

**ENH-35 — Three validation runs:**

| Run | Changes | NIFTY Accuracy | Signal Count |
|---|---|---|---|
| Run 1 (baseline) | None | 47.4% below random | 25,762 |
| Run 2 (LONG_GAMMA gate + CONFLICT fix + VIX removed) | 3 changes | 48.2% overall, SHORT_GAMMA 55.5% | 8,967 |
| Run 3 (+ NO_FLIP gate + conf threshold + power hour) | 6 changes | 58.6% STRONG EDGE | 244 |

Final: trade_allowed=YES pool 268 bars, 55.2% accuracy. Phase 4 target met.

Key finding: CONFLICT BUY_CE (breadth BULLISH + momentum BEARISH) = 67.9% accuracy at N=661 — strongest signal in dataset. The old CONFLICT rule was blocking the best trades.

**Six signal engine changes applied:**
1. CONFLICT BUY_CE now trades
2. LONG_GAMMA → DO_NOTHING (47.7%, below random)
3. NO_FLIP → DO_NOTHING (45-48%, below random)
4. VIX gate removed (HIGH_IV has more edge)
5. Confidence threshold 60→40
6. Power hour gate — no signals after 15:00 IST

SENSEX anomaly: 24 signals at 20.8% — all fired 15:04-15:28 (expiry unwinding). Gate eliminates this.

**ENH-37 — ICT Pattern Detection Layer (complete):**

All 6 steps built and deployed:
- `ict_zones_ddl.sql` — two new tables (28 + 16 cols)
- `detect_ict_patterns.py` — ICTDetector class with VERY_HIGH/HIGH/MEDIUM/LOW MTF hierarchy
- `build_ict_htf_zones.py` — W/D/H zone builder. 39 zones written on first run. 1H added after design discussion — bridges the gap between weekly/daily and 1M bars.
- `detect_ict_patterns_runner.py` — runner integration, every 5-min cycle, non-blocking
- Signal engine enriched with 4 new fields (ict_pattern, ict_tier, ict_size_mult, ict_mtf_context)
- Dashboard: ICT zones card + signal display updated

ICT MTF hierarchy rationale: zone age = institutional significance. Weekly zones (multi-session, tested) > daily (session-proven, pre-market) > 1H (nascent, same-session). The 1H layer bridges the timeframe gap — without it, a 1M pattern in a bullish 1H structure would get LOW context incorrectly.

**Registers updated:** Enhancement Register v4, Open Items Register v6.

---

### Commits

| Hash | Description |
|---|---|
| 7c346fb | Phase 4 prerequisites — ENH-35 validated changes (3 changes) |
| (follow-up) | NO_FLIP gate + power hour gate + conf threshold |
| 26c5e72 | ENH-37 Steps 4+5 — runner + signal wiring |
| (follow-up) | Dashboard ICT wiring |
| (follow-up) | Registers v4/v6 |

---

### Monday Pre-Market Checklist

```
[ ] python build_ict_htf_zones.py --timeframe D   (refresh daily zones)
[ ] Confirm supervisor starts at 09:14
[ ] Watch dashboard for ICT zones populating during session
[ ] Watch signal_snapshots for ict_pattern field on first SHORT_GAMMA signal
[ ] Shadow session 9/10 — log result
```

---

### Next Session Goals

1. Shadow sessions 9+10 results → Phase 4 decision
2. If Phase 4 approved: wire ict_size_mult to actual order quantity (ENH-38)
3. If Phase 4 approved: ENH-42 WebSocket scoping
4. C-07b (pre-open capture gap) — dedicated cron before 09:00
5. Rerun critical experiments on full year data (post-expiry fix): Exp 5, 8, 10c, portfolio sims

---

### State Snapshot

```
Local:  clean at 26c5e72
AWS:    clean at 26c5e72
DB:     ict_zones (28 cols), ict_htf_zones (16 cols, 39 active zones)
        signal_snapshots: + ict_pattern, ict_tier, ict_size_mult, ict_mtf_context
Shadow: 8/10
Phase 4: NOT YET
Signal engine: SHORT_GAMMA only, 268 bars/year, 55.2% accuracy
```
