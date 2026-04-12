# MERDIAN — Master Open Items & Enhancement Status Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Edition | v6 — Research Session Update — 2026-04-12 |
| Source documents | Open Items Register v5 · Research Sessions 2 and 3 (2026-04-11/12) |
| Current latest appendix | V18E (live canary) + Research Appendix (experiments) |
| Authority | This document aggregates and does not supersede any master. |

---

### Research Session Changes (2026-04-11 through 2026-04-12)

**Experiments completed:** 2 (full year), 2b, 2c, 2c v2, 5, 8, 10c, 15, 16 — all 11 scheduled experiments complete except 15b (date type fix pending, not blocking).

**Key decisions made:**
- Futures experiments permanently closed — options only
- INR 50L capital ceiling and INR 25L sizing freeze established
- Strategy D (Full Kelly tiered) selected for live implementation
- T+30m exit confirmed over ICT structure break
- MEDIUM (1H zone) context confirmed — keep in ENH-37
- BEAR_OB AFTERNOON hard skip rule established
- Signal Rule Book v1.1 ready to write (ENH-40)

**Open items added:** OI-07, OI-08, OI-09, OI-10

**Shadow gate:** 8/10 sessions complete (Mon/Tue = sessions 9 and 10)

---

## Section 1 — Critical Fixes

### C-07b — Pre-open capture gap (09:00-09:08 window)
**Status:** OPEN

All other C-series items: CLOSED — see v5.

---

## Section 5 — Open Items Register (OI series)

### OI-01 through OI-06
**Status:** CLOSED — see v5

---

### OI-07 — Experiment 15b completion
**Status:** OPEN — minor fix required

`experiment_15b_kelly_sizing.py` has a date type mismatch in `detect_daily_zones`. Fix: ensure `daily_ohlcv` "date" field is passed as string to zone builders while dict keys remain as date objects. Non-blocking — Exp 15 already confirmed 1H zone edge. Run after shadow gate completes.

---

### OI-08 — ENH-38 Live Kelly Sizing Implementation
**Status:** OPEN — next engineering build after shadow gate

Implement Kelly tiered sizing in `detect_ict_patterns_runner.py`. Replace current `ict_size_mult` flat multiplier with dynamic lot calculation per trade:
1. Read current capital from `capital_tracker` table (OI-09)
2. Apply `effective_sizing_capital()`: floor INR 2L, freeze at INR 25L, hard cap INR 50L
3. Compute lots using Half Kelly fractions: TIER1=50%, TIER2=40%, TIER3=20%
4. Write computed lots to `signal_snapshots`: `ict_lots_t1`, `ict_lots_t2`, `ict_lots_t3`
5. Execution layer reads at trade time

Start with Half Kelly (Strategy C). Upgrade to Full Kelly after 3-6 months live experience.

---

### OI-09 — Capital Tracker Table
**Status:** OPEN — required for OI-08

New Supabase table:
```sql
CREATE TABLE capital_tracker (
  symbol      text PRIMARY KEY,
  capital     numeric NOT NULL DEFAULT 200000,
  updated_at  timestamptz DEFAULT now()
);
INSERT INTO capital_tracker VALUES ('NIFTY', 200000, now());
INSERT INTO capital_tracker VALUES ('SENSEX', 200000, now());
```
Updated after every trade close (T+30m). Read by sizing engine at next signal fire. Build before OI-08.

---

### OI-10 — Signal Rule Book v1.1
**Status:** OPEN — document update

Update Signal Rule Book with all research-validated rules:

**New rules:**
- BEAR_OB AFTERNOON (13:00-14:30) SKIP — hard rule. 17% WR, -24.7% expectancy.
- BULL_OB AFTERNOON (13:00-15:00) TIER1 — 100% WR, +75.3% expectancy.
- BULL_FVG|HIGH|DTE=0 TIER1 — 87.5% WR, +58.9% expectancy.
- JUDAS_BULL confirmation at T+15m (not T+5m) — T2 rate 12%→44%.

**Changed rules:**
- BEAR_OB DTE=0 and DTE=1 — combined structure (futures + CE insurance), not pure PE.
- BULL_FVG without regime context — TIER3 minimum sizing only (50.3% WR unconfluenced).
- BEAR_FVG HIGH context — remove zone filter (HIGH context destroys BEAR_FVG edge).

**Confirmed rules (document as tested):**
- T+30m exit over ICT structure break — confirmed +41% more P&L.
- BEAR_OB MORNING TIER1 — 100% WR, +70.9%.
- BULL_OB DTE=0 TIER1 — 100% WR, +107.4%.
- 1H zones (MEDIUM) in ENH-37 hierarchy — confirmed edge, BULL_OB MEDIUM avg +INR 18,938 vs +INR 9,774 without.
- MOM_YES = single strongest filter — +21.6pp lift on BEAR_OB.

---

## Section 6 — Shadow Gate Tracking

| Session | Date | Status |
|---|---|---|
| 1-8 | 2026-04-06 to 2026-04-11 | PASSED |
| 9 | 2026-04-14 Monday | PENDING |
| 10 | 2026-04-15 Tuesday | PENDING |

Gate passes after sessions 9 and 10. Post-gate: implement OI-09 then OI-08.

---

*MERDIAN Open Items Register v6 — 2026-04-12*
*Supersedes v5 (2026-04-09).*
