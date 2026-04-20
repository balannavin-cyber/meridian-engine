# MERDIAN — Master Open Items & Enhancement Status Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Edition | v7 — Research Session Update — 2026-04-18 |
| Source documents | Open Items Register v6 · Research Sessions 4 and 5 (2026-04-17/18) |
| Current latest appendix | V18E (live canary) + Research Appendix (experiments) |
| Authority | This document aggregates and does not supersede any master. |

---

### Research Session Changes (2026-04-17 through 2026-04-18)

**Experiments completed:** 17, 18, 19 (5m), 20 (5m), 23, 23b, 23c, 25 (5m), 26, 27, 27b — 11 experiments

**Infrastructure built:**
- `hist_spot_bars_5m` — 41,248 rows
- `hist_spot_bars_15m` — 14,072 rows
- `hist_atm_option_bars_5m` — 27,082 rows (PE+CE OHLC + wick metrics)
- `hist_atm_option_bars_15m` — 9,601 rows
- `hist_pattern_signals` — 6,318 rows (backfill_5m)

**Architectural decision — 1m → 5m:**
All ICT pattern detection must operate on 5m bars. 1m = execution entry only.
This is now the permanent standard for all future experiments.

**Key decisions made:**
- LONG_GAMMA gate confirmed correct and symmetric (Exp 17, 19)
- OI wall + ICT confluence independent — OI synthesis signal REJECTED (Exp 18)
- Sweep reversal has NO mechanical edge — ENH-54 REJECTED (Exp 23/23b/23c)
- Breadth is independent of ICT edge — remove as hard gate (Exp 25)
- Momentum alignment +22.6pp — add as hard block (Exp 20)
- Small PE premium sweep (<1%) has edge 64.5% WR — monitor (Exp 27b)
- Option ICT concepts valid in premium space but need tighter filters (Exp 27)

**Open items added:** OI-11, OI-12, OI-13, OI-14, OI-15

**Live trade logged:** 2026-04-17 NIFTY BUY_CE — +25% — ICT sweep reversal, discretionary

---

## Section 1 — Critical Fixes

### C-07b — Pre-open capture gap (09:00-09:08 window)
**Status:** OPEN

---

### C-08 — latest_market_breadth_intraday VIEW → TABLE fix
**Status:** OPEN — MEDIUM priority

`latest_market_breadth_intraday` is a VIEW in Supabase. The upsert in `ingest_breadth_from_ticks.py` silently fails because you cannot upsert to a view. Breadth data is computed correctly but not persisted. Dashboard shows stale breadth permanently.

**Fix:** Convert view to materialised table in Supabase:
```sql
DROP VIEW latest_market_breadth_intraday;
CREATE TABLE latest_market_breadth_intraday (
  symbol       text PRIMARY KEY,
  advances     integer,
  declines     integer,
  regime       text,
  score        integer,
  updated_at   timestamptz DEFAULT now()
);
```
Then verify `ingest_breadth_from_ticks.py` upsert syntax matches.

**Impact:** Breadth reads correctly in signal engine and dashboard. Currently reading stale data from prior day (23h+ stale shown on 2026-04-17).

---

## Section 5 — Open Items Register (OI series)

### OI-01 through OI-06
**Status:** CLOSED — see v5

---

### OI-07 — Experiment 15b completion
**Status:** OPEN — minor fix, non-blocking

---

### OI-08 — ENH-38 Live Kelly Sizing Implementation
**Status:** OPEN — next engineering build after shadow gate

---

### OI-09 — Capital Tracker Table
**Status:** OPEN — required for OI-08

---

### OI-10 — Signal Rule Book v1.1
**Status:** OPEN — document update

---

### OI-11 — Remove Breadth Hard Gate (ENH-43)
**Status:** OPEN — signal engine build required

Experiment 25 (5m, 2026-04-17) confirmed breadth is independent of ICT edge:
WR spread = 1.0pp across BULLISH/BEARISH/NEUTRAL breadth regimes.

**Changes to `build_signal_v3.py`:**
1. Remove `breadth_regime` from hard gate / DO_NOTHING logic
2. Demote to confidence modifier only:
   - BULLISH_BREADTH + BUY_CE → +5 confidence points
   - BEARISH_BREADTH + BUY_PE → +5 confidence points
   - Opposing breadth → 0 points (no penalty)
3. Remove "Breadth regime is BEARISH/BULLISH" from DO_NOTHING reasons

**Test:** Run shadow test for 5 sessions before promoting to live.

**Note:** Breadth data is currently stale anyway (C-08 bug). Fix C-08 first to confirm breadth reads correctly before changing gate logic.

---

### OI-12 — Add Momentum Opposition Hard Block (ENH-44)
**Status:** OPEN — signal engine build required

Experiment 20 (5m, 2026-04-17) confirmed +22.6pp lift for momentum alignment.

**Changes to `build_signal_v3.py`:**
1. Before pattern tier evaluation, check `ret_session`:
```python
MOMENTUM_THRESHOLD = 0.0005  # 0.05%

if abs(ret_session) > MOMENTUM_THRESHOLD:
    if direction == "BUY_PE" and ret_session > 0:
        return DO_NOTHING, "Momentum opposes signal (ret_session positive, BUY_PE signal)"
    if direction == "BUY_CE" and ret_session < 0:
        return DO_NOTHING, "Momentum opposes signal (ret_session negative, BUY_CE signal)"
# else: neutral momentum → allow
```
2. Remove current `momentum_regime` confidence modifier (superseded by hard gate)
3. Add "Momentum aligned" as +10 confidence points when direction matches

**Expected impact:** Will reduce signal frequency. OPPOSED signals (38.3% WR) blocked — these are actively loss-generating. ALIGNED signals (60.9% WR) pass.

**Priority:** HIGH — implement alongside OI-11. Both are signal engine changes, do in one build.

---

### OI-13 — Patch Script Syntax Validation Standard
**Status:** OPEN — process rule

All `fix_*.py` patch scripts must end with `ast.parse()` validation before writing to target file.

**Incident:** `force_wire_breadth.py` on 2026-04-16 inserted breadth block at wrong indentation (8-space instead of 4-space). IndentationError discovered at market open 2026-04-17 — runner failed to start. Fixed with `fix_runner_indent.py` during live session.

**Rule to add to Change Protocol:**
```python
# MANDATORY — add to every patch script before sys.exit()
import ast
try:
    ast.parse(Path(TARGET).read_text(encoding="utf-8"))
    print("Syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    sys.exit(1)  # Do NOT write broken file
```

---

### OI-14 — Shadow Gate Status Update
**Status:** OPEN — verify sessions 9 and 10

Per v6: sessions 9 and 10 were scheduled for 2026-04-14 (Mon) and 2026-04-15 (Tue).

**Action:** Confirm pass/fail for both sessions. If both passed, gate is complete. Proceed to OI-09 (capital tracker) then OI-08 (Kelly sizing).

---

### OI-15 — Premium Sweep Signal Monitoring (ENH-45)
**Status:** OPEN — monitoring phase

Experiment 27b found 64.5% WR for PE premium sweeps < 1% in morning session (N=107).

**Monitoring plan:**
- Live `hist_atm_option_bars_5m` captures 5m ATM option bars each session (pipeline already live)
- Log each morning PE sweep < 1% with outcome at T+30m
- Target: 50 live occurrences before building ENH-45
- Threshold for build: sustained 60%+ WR on live data

**What constitutes a PE small sweep signal:**
```
Morning session (09:15-10:30)
ATM PE bar high > prior morning session bar high by 0.2-1.0%
ATM PE bar close < prior morning high (rejection confirmed)
First sweep of session only
→ Note, do NOT trade yet — observe only
```

---

## Section 6 — Shadow Gate Tracking

| Session | Date | Status |
|---|---|---|
| 1-8 | 2026-04-06 to 2026-04-11 | PASSED |
| 9 | 2026-04-14 Monday | VERIFY |
| 10 | 2026-04-15 Tuesday | VERIFY |

Verify sessions 9 and 10. Post-gate: implement OI-09 then OI-08.

---

## Section 7 — Rejected Proposals

| Item | Reason | Experiment |
|---|---|---|
| Sweep reversal signal (ENH-54) | 17-19% WR on 1m and 5m. Requires discretionary judgment — unmitigated zone + wick quality on HTF. Cannot mechanise. | Exp 23/23b/23c |
| LONG_GAMMA asymmetric gate (ENH-55) | No asymmetry. BULL_OB under LONG_GAMMA = 50.5% WR (coin flip). Today's trade was discretionary sweep reversal, not BULL_OB zone entry. | Exp 19 |
| OI wall synthesis signal (ENH-56) | OI walls and ICT zones are statistically independent. CE wall ICT lift = +4.5pp (noise). PE wall ICT lift = -2.1pp (negative). | Exp 18 |
| Option wick as standalone gate | 1.7pp lift — noise. Only meaningful under SHORT_GAMMA (76.9% WR, N=13 — too small). | Exp 26 |

---

## Section 8 — Pending Experiments

| Exp | Question | Data needed | Priority |
|---|---|---|---|
| 23d (if pursued) | Sweep reversal with true unmitigated zone tracking | Need to build zone mitigation tracker | LOW |
| 26b | PE wick under SHORT_GAMMA with more sessions | More live SHORT_GAMMA data | LOW — monitor |
| 27c (if pursued) | Premium ICT with tighter filters (session-first, prior day levels) | Already have hist_atm_option_bars_5m | MEDIUM |
| 28 (future) | LTF entry refinement (5m CHoCH inside HTF zone) | Needs live signal data + 5m bars | Phase 4C+ |

---

*MERDIAN Open Items Register v7 — 2026-04-18*
*Supersedes v6 (2026-04-12).*
