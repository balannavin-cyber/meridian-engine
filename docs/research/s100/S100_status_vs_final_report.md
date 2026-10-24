# Status of the parity final report's MERIDIAN items — as at S100, Sat 2026-10-24 18:30 IST

Source: `claude/parity_eval/parity_target_final_report_2026-10-19.md` §7 (A / T / N), §8 (defects 1–13), §9 (owed).
Evidence: `claude/rulings_s100.md` (S100-A…R), `claude/B3_reads_2026-10-24.md`, `claude/S100_close_inputs.md`, tracker §2.2 (S98-B row).
"Live Mon" = deployed; confirms on the 2026-10-26 Part C read.

## §7.1 Adopt
| # | item | status | where |
|---|---|---|---|
| A1 | closing-session state on SPOT, official close, no "LIVE" on a held value | **Built, live Mon.** Label `Spot · held since 15:15` / `Spot · close`; close value = 15:40 γ-run spot once S98-B's 15:40 cycle runs | S100-R (1aeb000), S98-B (2edd25f) |
| A2 | stale strip when the γ run is > 10 min old, incl. 15:15–15:40; per-tile "stale · as of" | **Built (window to 15:45), live Mon**; per-tile "stale · as of" not built | S100-S (f964e40) |
| A3 | γ to 15:30 / 15:40 every day | **Built, live Mon** (closing cycles 15:30 / 15:35 / 15:40; runner waits for its own chain run — also removes the one-run compute lag R41) | S98-B `2edd25f` |
| A4 | basis from the spot the SPOT tile shows | **Built as a label**: stored basis kept, sub-line names its spot `vs spot X @ hh:mm`; exposed a writer lag (futures rows keep the 15:15 spot to 15:40 while the chain has the close) — TD candidate | S100-S (f964e40) |
| A5 | explicit CLOSED state, date-specific post-close wording | **Built**: strip `Closed · showing the <date> session · next open <date>`, plus `Pre-open …` and `Closing session …` states | S100-S (f964e40) |
| A6 | pocket word from net Γ | **Step 1 live:** "pocket (local γ) … Net gamma is long/short, x of gross"; step 2 (net-based three-state word) = T1 | S100-Q / Q.1 (3366bf1) |
| A7 | hover-to-explain; qualifiers at narrow widths | **Open** (parked behind R5 / R11) | R25 |
| A8 | write-once pin history if ever shown | **Recorded as a design constraint**; nothing built | R28 |

## §7.2 Test
| # | item | status |
|---|---|---|
| T1 | three-state regime | **Open — needs the net/gross threshold measured on ENH-133 + pre-reg** (S100-Q step 2) |
| T2 | pin hysteresis / tie state | **Open** (R13, pre-reg) |
| T3 | √τ-normalised GEX | **Open** (R26) |
| T4 | ENH-131 root not bracketed by strike sign change | **Answered — by construction, no TD.** The flip is a true root of the repriced total curve (10-14 NIFTY 22,480.4, SENSEX 72,688.9, single crossing ≤ 2σ); bars are per-strike at the observed spot — different objects (R10) |
| T5 | "γ ceiling / floor" slot | **Open** (R27, park) |
| T6 | wall hysteresis / degenerate corridor | **Open** (R11) |
| T7 | front-future basis jumps | **Answered — no capture defect.** Board basis = captured rows exactly; the jumps are last-traded-price bounce, 2–4 bp on both indices (SENSEX 3.1 bp sd vs NIFTY 3.7 bp), not staleness; `raw` holds no bid/ask/depth, so a quote-based basis is an ENH (R8) |
| T8 | faster cadence / no one-run lag | **Part:** compute lag fixed by S98-B (live Mon); board polling lag (R16, tabs not re-polling) open |
| T9 | new substrates (RV, aggressor tape, per-strike bars, wall history, vol ÷ OI) | **Open, parked** (R29) |
| T10 | settlement probability | **Declined for now** (R30) |

## §7.3 Don't adopt — all stand
N1 D-4 verdict (S96-I kept) · N2 their pin as forecast · N3 their log as ground truth · N4 their HHI.

## §8 MERIDIAN defects 1–13
| # | defect | status |
|---|---|---|
| 1 | no close print; "LIVE" on held value; γ stops 15:20; no stale strip 15:15–15:40 | label + γ to 15:40 **built (live Mon)**; close printed via the 15:40 γ spot (Mon); **stale strip open** |
| 2 | basis jumps | **answered** (T7) — display noise from last-trade price, not a defect of the capture |
| 3 | board one γ run behind | compute half **fixed** (S98-B, Mon); polling half **open** (R16) |
| 4 | pocket word vs net Γ | **step 1 live** (S100-Q.1) |
| 5 | pin flicker; read text on a different wall than PIN | **open** (R11 / R13) |
| 6 | degenerate corridor, wall flicker | **open** (R11) |
| 7 | "SPOT ≡ FLIP" up to 55 pts apart | **open** (R11) |
| 8 | net long with spot below our strike-axis zero | **explained by construction** (R10: net Γ is the total at spot; the strike-axis zero is an interpolation between bars — different objects) |
| 9 | CLOCKS card absent / at 800 px | **open** (R11 / R25) |
| 10 | phantom overnight change on SPOT | **explained and now labelled** (R18; S100-S strip `Pre-open · figures are from the pre-open chain …`) |
| 11 | opening spot 40 pts off at 09:16–09:17 | **open; probable cause** R38 (the "live" 1-min value is the previous closed bar, 62–65 s behind its ts) — not verified on the eval minutes |
| 12 | `/help` → 403 | **closed in S97** (route `/manual`) |
| 13 | slowdown / 0×0 on aged tabs | **re-diagnosed** (R16): the board's views stop re-polling on an aged tab — ours, open |

## Not in the report, fixed because of reads it triggered
- Legacy Context / Structure showed a two-session change all session (+392.1 for a +103.5 move) → **fixed** S100-N (142c3e6).
- Context "IV skew" was a same-strike put/call IV gap → **now the view's skew** S100-P (2ee83e1).
- Dealer-claim wording across board, drawers, Home → **qualified** S100-R D1–D5 (1aeb000).

## §9 Still owed
| item | status |
|---|---|
| `07` Q4 / NIFTY OI gap (F7) | **done — ours right**: same-minute 15:40 equals the target to 0.0 % on two strikes, 3.6 % on the third; F7 compared our 15:20 with their 15:40 (R7) |
| Q5a/b (SENSEX γ curve) | **done** as R10 (10-14 minutes, both symbols) |
| Day-4 (e) futures ticks | **done** as R8 |
| Q1–Q3 (spot freeze), Day-3 (a)–(d), Day-4 (f)–(g) | **not run** — Q1–Q3's question is answered by design (1-min ends 15:15; close on the 15:40 chain); the rest are target-comparison reads dropped by R31 |
| official closes 16 / 19 Oct | **not fetched**; 10-16 NIFTY 23,146.15 is in `gamma_metrics` 15:40 (S98 O1) |
| `hwcap` export | **dropped** (R31, parity closed) |

## Count
Of the 13 §8 defects: **answered / closed 3** (2, 8, 12) · **partly built, confirming Monday 2** (1 — stale strip still open; 3 — polling
half still open) · **step 1 done 1** (4) · **open 7** (5, 6, 7, 9, 10, 11, 13 — of these 10 is explained, 11 has a probable cause, 13 is re-diagnosed).
Of §7.1 A1–A8: **built 6** (A1, A2 strip, A3, A4 label, A5, A6 step 1) · **recorded 1** (A8) · **open 1** (A7); A2's per-tile stale and A4's writer lag remain.
