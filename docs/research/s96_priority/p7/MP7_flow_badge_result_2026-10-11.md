# M-P7 — DEX flow-vs-book badge under the defect-derived abstain rule: result

| Field | Value |
|---|---|
| **Verdict** | **BUILD** — NIFTY SPEAKS, SENSEX SPEAKS (pre-registration §7). **Qualified:** the badge needs an untraded-leg guard before it goes live (§4). |
| **Pre-registration** | `MP7_flow_badge_prereg_2026-10-11.md`, blob `5813af540df15d542ddb5f509585cba08c9fef83` (commit `d909559`), and **Amendment A1** (`MP7_amendment_A1_2026-10-11.md`, commit `9460d5d`, query shape only, filed before any Part 1 row was returned). |
| **Run** | 2026-10-11 ~18:30–18:41 IST, `~/meridian-cc` at `9460d5d`, `bin/roq.sh` (merdian_ro, read-only, 30 s timeout), under `ulimit -v 700000`. Exit 0. |
| **Outputs (local, S95-F)** | `~/mp7_out/` — 96 CSVs; `SHA256SUMS` sha256 `32a091fd12cce70409540daab3cbf0f2886c9fdf0dbc8cfde249e348ab00d49c`; `mp7_score.json` sha256 `6bd4800ec082e7c2fd2850ec989581644a52563f21651105169e7ee397733de3`. |
| **Track** | Roadmap §2.1 P7 → P7a (ruling S96-A D7; cut S96-B). |

## 1. Gates (Part 0), all before any sign was computed

- **0a Rule 13:** `merdian_ro` sees 1 row of `data_contamination_ranges`; **no range** overlaps 2026-08-24 → 10-09 or names a study table.
- **0b Live control, 2026-10-09:** the replay equals the live `v_dex_standing_book` and `v_oi_since_preopen` on **all 8 fields, both symbols** — settled cycle 15:10:07; NIFTY book call 87,880.32 / put −96,169.64 Cr, leg OI 439,910,900, gap 220,805, anchor 08:30:08 (368,565,535 qty, 239 strikes); SENSEX 19,137.81 / −22,338.30 Cr, 24,542,240, 19,980, anchor 08:35:05 (10,073,900, 198). So the extract's session, front, anchor, gap and arithmetic rules are the live views' rules, at real volume.
- **Integrity:** no duplicate strikes in any cycle; one spot per cycle.

## 2. Sample

| status (per symbol, 47 dates) | NIFTY | SENSEX |
|---|---|---|
| ANCHORED | 31 | 31 |
| NOT_SESSION (calendar closed or tape frozen) | 14 | 14 |
| NO_FRONT | 2 | 2 |
| NO_PREOPEN | 0 | 0 |

- **NO_FRONT = 2026-08-24 and 08-25, both symbols:** the tape moved (316–359 distinct spots) but the chain holds **no front-expiry row to 15:15**. So the chain as now retained starts after 08-25 on both symbols, not on 08-24 as roadmap §8.3 / §5.4 state. Recorded for TD-S94-NEW-4 (chain retention unmeasured); not investigated here.
- Primary sample: NIFTY 31 sessions / 2,222 cycles; SENSEX **28** / 2,006 (31 less the three TD-S95-NEW-1 days, scored separately).

## 3. Part 1 — primary sample

| | bucket | cycles | ABSTAIN | SAME | OPPOSITE | abstain share | flow \|net\|/gross p25 / p50 / p75 | badge persists | flow sign persists |
|---|---|---|---|---|---|---|---|---|---|
| **NIFTY** | early | 272 | 75 | 42 | 155 | 0.276 | 0.113 / 0.225 / 0.368 | 0.755 | 0.863 |
| | mid | 1,671 | 554 | 604 | 513 | 0.332 | 0.136 / 0.271 / 0.433 | 0.801 | 0.968 |
| | late | 279 | 97 | 87 | 95 | 0.348 | 0.196 / 0.324 / 0.469 | 0.821 | 0.989 |
| | **all** | **2,222** | **726** | **733** | **763** | **0.327** | 0.138 / 0.272 / 0.433 | 0.799 | 0.959 |
| **SENSEX** | early | 245 | 101 | 65 | 79 | 0.412 | 0.074 / 0.154 / 0.284 | 0.664 | 0.889 |
| | mid | 1,509 | 604 | 628 | 277 | 0.400 | 0.082 / 0.193 / 0.322 | 0.820 | 0.929 |
| | late | 252 | 95 | 103 | 54 | 0.377 | 0.090 / 0.228 / 0.376 | 0.813 | 0.905 |
| | **all** | **2,006** | **800** | **796** | **410** | **0.399** | 0.083 / 0.193 / 0.323 | 0.802 | 0.922 |

Median share of |ΔOI| with no usable delta: NIFTY 0.24 %, SENSEX 0.10 %.

**Verdict arithmetic (§7):** both symbols ≥ 20 sessions; abstain 0.327 and 0.399, each ≤ 1/2 → SPEAKS, SPEAKS → **BUILD**.

**What the table shows, and does not.**
- The badge changes state about one cycle in five (persistence 0.80, runs of ~5 cycles ≈ 25 min); the flow sign under it persists 0.92–0.96, so most changes come from the book's sign or from abstaining, not from flow turning.
- Flow net is itself a partial cancellation (median |net|/gross 0.27 NIFTY, 0.19 SENSEX).
- Before 10:00 NIFTY flow mostly opposes the book (155 OPPOSITE vs 42 SAME). **Reported only.** No price, return or outcome was read; nothing here says SAME or OPPOSITE carries information about what happens next (§7).

## 4. Secondary — SENSEX 2026-09-25 / 09-28 / 09-29 (TD-S95-NEW-1), reported, not scored

216 cycles: **OPPOSITE 205, SAME 8, ABSTAIN 3** (abstain share 0.014); mid and late OPPOSITE on **every** cycle;
flow |net|/gross median **0.957**; badge persistence 0.97.

On these days legs with volume 0 held 33–94 % of front OI and 73–98 % of DEX gross, so the **book's** sign is
set by vendor values that are not OI. The badge then speaks with near-total confidence about an artefact.
The study excluded these days by date; **the live board cannot**. So the BUILD verdict carries a condition:
**the badge must not go live without a guard that abstains when OI levels are dominated by untraded legs** —
TD-S95-NEW-1 option (c), which is the operator's call and is not chosen here. The flow numbers are not
affected (no untraded leg changed OI after 09:15 on any of 22 symbol-sessions, TD-S95-NEW-1).

## 5. Corrections recorded during the run

- The first run stopped on a 30 s timeout (planner walked `idx_ocs_symbol_expiry_strike_type`); fixed by A1
  before any Part 1 row was returned.
- A fixture comparison ran against a stopped local server and reported "same" on two empty outputs; discarded
  and re-run with row counts (A1 §Evidence).
- The run's expected log line count was stated as 49 without computing it; the correct figure is 48
  (47 dates + the done line). The run was right; the expectation was recalled, not computed.

## 6. Next (owed to the operator)

1. **The untraded-leg guard** (TD-S95-NEW-1 (c)) — a condition for the badge, not for the flow numbers.
2. **Board wording** for flow and the badge (design note §6) — operator's explicit yes before anything goes live.
3. **P7a SQL** — `v_dex_flow_vs_book`, authored and costed through `roq.sh`, operator apply.
