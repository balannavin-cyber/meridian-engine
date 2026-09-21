# Claude Code Brief — SRS Exploration (read-only measurement)

**Run on:** EC2, `~/meridian-cc`, on a branch — `s80/srs-exploration`. Never `main` (P-4).
**Declared concern (one only):** measure the five quantities that the v3 pre-registration (`prereg_sr_premium_sell_2026-09-21.md`) needs before its parameters are frozen. **No production code, no writes to any table, no schema change.**

---

## 0. Preconditions — operator confirms before starting

| # | Precondition | Source |
|---|---|---|
| 1 | Database access is **read-only**: the read-only Postgres role if it exists, otherwise GET-only PostgREST with every python invocation approved per call. **Never read `.env` with `cat`/`grep`/`bash -x`** — load it inside python only. | Guardrails §1, §7.6; CLAUDE.md Rule 19 |
| 2 | `CLAUDE.md` size problem (407k vs the context ceiling) acknowledged. **This brief is self-contained**; do not rely on CLAUDE.md being fully in context. | overview / S73 |
| 3 | New files go **only** under `research/srs/` (create it). No file whose basename duplicates one under `docs/` (P-7). | P-7, P-8 |

---

## 1. Preflight — state the prediction before each check (Guardrails §8)

```
git branch --show-current            # predict: s80/srs-exploration
git status --short                   # predict: the known untracked set only
crontab -l | wc -l                   # predict: 53
echo "=== PREFLIGHT SENTINEL OK ==="
```

Keep a **claim ledger**: ID · claim · basis (CODE / DATA / DOC / INFERENCE) · verdict. Withdrawn claims stay in the ledger, never silently re-fitted.

---

## 2. Data rules — violating any one invalidates the run

- **Extent:** read `docs/registers/MERDIAN_Data_Inventory.md` first. Do not measure one table and generalise.
- **`hist_option_bars_1m.bar_ts`** is IST labelled +00:00 (TD-087). **`hist_spot_bars_5m.bar_ts`** is the same. Use `replace(tzinfo=None)`, **never** `astimezone()`.
- **PostgREST caps at 1000 rows** per request. Paginate. Chunk per (symbol, day) to avoid `57014` timeouts.
- **Timestamps:** tolerant parser — Python 3.10 `fromisoformat()` rejects 4-digit fractional seconds.
- **Two eras:** 1m bars 2025-04 → 2026-03; ~5m chain sources (HOCS / GSS / OCS) after. **Report the eras separately.** The cadence break is a cohort boundary.
- **Expiry weekday:** derive each cycle's expiry from the `expiry_date` present in the chain data. **Never hardcode a weekday** — it has changed.
- **Lot size:** compute P&L per unit. NIFTY 75 → 65 from January 2026; SENSEX 20.
- **σ_daily** = `spot × atm_iv/100 / sqrt(252)`. **EM** = ATM straddle premium at cycle Day-1 10:30.

---

## 3. Measurements

Each result is one table in `research/srs/srs_exploration_<date>.md`, with N shown in every cell. Cells with N < 20 are printed but marked `THIN`.

### M1 — Premium decay curve (sets the §5.1 harvest point)
- **Per cycle:** mid-price of the ~1 % OTM PE and CE, and the ATM straddle, at each Day-N close, as % of the Day-1 10:30 value. Include expiry day at 13:00.
- **Split by:** symbol × era × `untested` (spot never came within 0.5 σ_daily of the strike) vs `tested`.
- **Output:** median / P25 / P75 per day; % of cycles reaching ≥ 70 % and ≥ 80 % decay by Day-3 close and by Day-4 close.
- **Prior (a guess, to be refuted):** for untested 1 % OTM, ≥ 75 % decay by Day-3 close in 55–65 % of cycles.

### M2 — S/R hold rates (sets §2 thresholds)
- **Build:** zones exactly per pre-reg v3 §2 — fractals, weights, 0.2 σ clustering. The code lives in `research/srs/levels.py`.
- **Per cycle:** for the nearest support and the nearest resistance, record strength, σ-distance from spot at cycle open, and whether a §2 **break** occurred before expiry.
- **Output:** hold rate by strength bucket (2–3 / 4–5 / 6+) × σ-distance bucket. Compare against the breach rate of a plain 1 % OTM strike on the same cycles.
- **Prior:** strength ≥ 4 zones hold through the cycle 65–70 % of the time.

### M3 — Expected vs realised move, by regime (tests the T2 premise)
- **Per cycle:** max excursion (high − low) and close-to-close move from Day-1 10:30 to expiry, each divided by EM.
- **Split by:** net GEX sign at cycle open (`gamma_metrics`, first cycle row). Also by `corridor_state` in the era where ENH-120 exists.
- **Output:** % of cycles with realised < EM; median ratio.
- **Prior:** realised < EM in 65–70 % of cycles, more often when net GEX > 0.

### M4 — Opposite-side triggers (tests §4)
- **Replay** T1, T2 and T3 mechanically on 1H bars. G0 = T2 without its GEX conditions.
- **Per fire:** did an opposite-side short sold at the §3.2 strike rule (i) reach 75 % capture, (ii) get broken, (iii) do neither by expiry-day 13:00?
- **Output:** fire count and outcome split per trigger. Show G0 vs G1 for T2.
- **No prior** — this is the open question.

### M5 — Skew (tie-break for which side to sell first)
- **Per 10:30 snapshot:** IV of the ~1 % OTM PE minus IV of the ~1 % OTM CE. Use MERDIAN-solved IV in the 1m era; in the chain era use the source's own IV column only if the Data Inventory marks it populated.
- **Output:** distribution by symbol × era.
- **Prior:** put-over-call in > 85 % of snapshots.

---

## 4. Stop conditions — report and stop, do not work around

- Any source returns zero rows where the Data Inventory says rows exist.
- The option chain for a cycle is missing its expiry, or has fewer than 40 strikes.
- A timeout recurs on the same chunk after one retry.
- Any result contradicts its prior by more than 2× — re-read the source and log a claim-ledger row **before** continuing.

## 5. Deliverable

- `research/srs/srs_exploration_<date>.md`: the five tables, the claim ledger, and a list of every cycle excluded and why.
- `research/srs/levels.py` and `research/srs/explore.py`, read-only.

**Do not commit.** The operator reviews first. Commits and pushes are ask-first.
