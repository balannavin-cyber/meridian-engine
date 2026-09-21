# Claude Code Brief — SRS Exploration (read-only measurement) · v2

**Run on:** EC2, `~/meridian-cc`, branch `s80/srs-exploration`. Never `main` (P-4).
**Declared concern (one only):** measure the quantities the v4 pre-registration (`docs/research/srs/prereg_sr_premium_sell_2026-09-21.md`) needs before its parameters are frozen. **No production code, no writes to any table, no schema change.**

> **v2 amendment.** M1's thresholds widened, two measurements added (**M6**, **M7**), and a vol-regime split imposed on every table. M2–M5 are unchanged — **if M1 has already run under v1, keep its output; only the threshold columns are added.** Nothing here invalidates work already done.

---

## 0. Preconditions — settled

| # | Precondition | Status |
|---|---|---|
| 1 | Database read-only | **Mode (b).** No read-only Postgres role exists (Guardrails §7.6 never done). GET-only PostgREST through a single `_get()` choke point, modelled on `~/meridian-engine/scripts/build_data_inventory.py` — read it, reuse the pattern, do not import from the production tree. No POST/PATCH/DELETE/RPC anywhere; assert it. Credentials loaded inside python only. Every Supabase run approved per call. |
| 2 | `CLAUDE.md` not in context | Confirmed. Brief is self-contained; flag any rule it does not restate. |
| 3 | New files under `research/srs/` only | Confirmed. `srs_` prefix pre-authorised on any basename collision under `docs/`. |

---

## 1. Preflight — prediction before each check (Guardrails §8)

```
git -C ~/meridian-cc branch --show-current   # predict: s80/srs-exploration
git -C ~/meridian-cc rev-parse --short HEAD  # predict: ee20e6e or later
git -C ~/meridian-cc status --short          # predict: known untracked set only
crontab -l | wc -l                           # predict: 53
echo "=== PREFLIGHT SENTINEL OK ==="
```

**Claim ledger** throughout: ID · claim · basis (CODE / DATA / DOC / INFERENCE) · verdict. Withdrawn claims stay, never silently re-fitted.

---

## 2. Data rules — violating any one invalidates the run

- **Extent:** read `docs/registers/MERDIAN_Data_Inventory.md` first. Never measure one table and generalise.
- **`hist_option_bars_1m.bar_ts`** is IST labelled +00:00 (TD-087). **`hist_spot_bars_5m.bar_ts`** likewise. `replace(tzinfo=None)`, **never** `astimezone()`.
- **PostgREST caps at 1000 rows.** Paginate; chunk per (symbol, day) to avoid `57014`.
- **Tolerant timestamp parser** — Python 3.10 `fromisoformat()` rejects 4-digit fractional seconds.
- **Two eras:** 1m bars 2025-04 → 2026-03; ~5m chain sources after. **Report separately** — the cadence break is a cohort boundary.
- **Expiry weekday from the data's own `expiry_date`.** Never hardcode; it has changed.
- **Lot size:** P&L per unit. NIFTY 75 → 65 from Jan 2026; SENSEX 20.
- **σ_daily** = `spot × atm_iv/100 / sqrt(252)`. **EM** = ATM straddle at cycle Day-1 10:30.

### 2.1 Vol-regime split — applies to EVERY table
Tag each cycle by ATM IV tercile at cycle open (low / mid / high), computed within era. **Every output table carries the regime breakdown as well as the pooled row.** Pooled-only results are not acceptable: the reference practitioner records one regime as *"brutal — low vol, no follow through"* and the next as *"a completely different regime, almost 2x volatility"*, which is exactly the variation a pooled mean hides.

---

## 3. Measurements

One table each in `research/srs/srs_exploration_<date>.md`, N in every cell. N < 20 printed and marked `THIN`.

### M1 — Premium decay curve — *thresholds widened*
- **Per cycle:** mid-price of the ~1 % OTM PE and CE, and the ATM straddle, at each Day-N close as % of Day-1 10:30. Include expiry day 13:00.
- **Split:** symbol × era × regime × `untested` (spot never within 0.5 σ_daily of the strike) vs `tested`.
- **Output:** median / P25 / P75 per day, **plus % of cycles reaching ≥ 50 %, ≥ 60 %, ≥ 70 %, ≥ 80 % decay at each of Day-2, Day-3 and Day-4 close.** The four thresholds are the v4 §5.1 harvest sweep; v1's 70/80-only pair assumed the answer.
- **Prior (to be refuted):** untested 1 % OTM reaches ≥ 50 % by Day-2 close in > 60 % of cycles, and ≥ 75 % by Day-3 close in 55–65 %.

### M2 — S/R hold rates — *unchanged*
Zones per pre-reg §2 (`research/srs/levels.py`). Per cycle: nearest support and resistance, strength, σ-distance at cycle open, and whether a §2 break occurred before expiry. Output: hold rate by strength bucket (2–3 / 4–5 / 6+) × σ-distance bucket, against the breach rate of a plain 1 % OTM strike on the same cycles. **Prior:** strength ≥ 4 holds 65–70 %.

### M3 — Expected vs realised move by regime — *unchanged*
Per cycle: max excursion and close-to-close from Day-1 10:30 to expiry, each ÷ EM. Split by net GEX sign at cycle open, and by `corridor_state` where ENH-120 exists. Output: % of cycles realised < EM; median ratio. **Prior:** 65–70 %, more often when net GEX > 0.

### M4 — Opposite-side triggers — *T5 added*
Replay T1, T2, T3 **and T5** mechanically on 1H bars. G0 = T2 without GEX; T5 does not exist in G0.
- **T5 definition:** on any 1H bar, spot below its Day-1 10:30 level **and** net GEX rising over the prior 3 cycles of `gamma_metrics` **and** HHI fallen ≥ 0.3 absolute from its cycle high **and** PCR < 0.7.
- **Per fire:** did an opposite-side short at the §3.2 strike rule (i) reach 50 % capture, (ii) reach 75 %, (iii) get broken, (iv) none of these by expiry-day 13:00?
- **Output:** fire count and outcome split per trigger; G0 vs G1 for T2. **No prior.**

### M5 — Skew — *unchanged*
Per 10:30 snapshot: IV of ~1 % OTM PE minus ~1 % OTM CE. MERDIAN-solved IV in the 1m era; in the chain era only if the Data Inventory marks the source's IV column populated. Output: distribution by symbol × era. **Prior:** put-over-call > 85 %.

### M6 — Wing cost by time of day — **NEW, highest priority after M1**
This single measurement decides pre-reg §1.3 (W-ENTRY vs W-DEFER), and §1.3 is what the 2 % guarantee rests on.
- **Per cycle-day, per side:** the price of the wing strike (0.75 σ_daily beyond the ~1 % OTM short) at **09:30, 10:30, 11:30, 13:00, 14:00, 15:15**, absolute and as % of the 09:30 price.
- **Paired with:** the short leg's own decay over the same stamps, so the net credit of buying late is visible, not just the wing saving.
- **Gap cost of deferring:** for every cycle-day, the overnight close→next-open move in σ_daily, and the **P&L an unhedged short of that strike would have taken** on the worst such move in the window. This is the price of the unhedged window.
- **Output:** median wing saving from 09:30 → 14:00 (points and %), by regime; distribution of adverse open gaps; **and the break-even — how large the unhedged clip may be before one bad gap erases a year of wing savings.**
- **Prior:** wing cost falls 30–50 % from 09:30 to 14:00 on untested days, and rises on tested ones (exactly when the hedge is needed).

### M7 — Positioning-divergence cue (T5 standalone) — **NEW**
Independently of trade replay, measure whether the cue has any forward content.
- **Per occurrence** of the M4 T5 condition: forward spot return over 1, 4 and 12 hours, and to expiry, in σ_daily.
- **Control:** the same forward returns on all 1H bars where the condition does **not** hold, matched by regime.
- **Output:** N, mean and median forward return, hit rate vs control. **If it does not beat its control, T5 is struck from the pre-reg** rather than carried into a backtest that could fit it.
- **No prior** — this is a single practitioner's stated cue on a single day (2026-08-27), which is an anecdote until measured.

---

## 4. Stop conditions — report and stop, do not work around
- Any source returns zero rows where the Data Inventory says rows exist.
- A cycle's chain is missing its expiry, or carries fewer than 40 strikes.
- A timeout recurs on the same chunk after one retry.
- Any result contradicts its prior by more than 2× — re-read the source and log a claim-ledger row **before** continuing.

## 5. Deliverable
- `research/srs/srs_exploration_<date>.md` — seven tables, each with its regime split; claim ledger; every excluded cycle and why.
- `research/srs/levels.py`, `research/srs/explore.py` — read-only.

**Order:** M1 → **M6** → M2 → M3 → M7 → M4 → M5. Stop after M1 and after M6 and show the table before continuing. M6 is second because W-ENTRY vs W-DEFER changes what every later measurement is measuring.

**Do not commit.** Operator reviews first; commits and pushes are ask-first.
