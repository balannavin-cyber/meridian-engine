# S93 dev starter — written at the S92 close (2026-10-09)

> Read `CLAUDE.md` then `docs/session_notes/CURRENT.md` first. This file is the **ordered work
> list**, not a second copy of session state. Rulings: `docs/research/s92_parity/rulings_s92.md`.
> The post-parity track and its statuses: `docs/research/s90_agentic/agentic_layer_roadmap_S90.md` §2.1.

---

## 0. Where things stand

**Hedgewall parity is CLOSED** (ADR-025 Amendment D, `579d273`). The work now runs on the
**post-parity priority track, ruling S92-I**: P1 → P8, each followed to DONE with evidence or
DECLINED-ON-EVIDENCE. **P1 is mid-run.** Nothing in P2–P8 starts before P1's decision point.

## 1. P1 — finish the level test (after 15:40 IST, writer idle)

Folder `docs/research/s92_priority/p1/` — read its `README.md` table first.

1. **Part 3** `p1_part3_replay_check.sql` — one statement. **Expect zero rows.** Any row: stop;
   the replay is not the shipped rule. Do not reason about which side is right.
2. **Part 2** `p1_part2_extract.sql` — **the whole file as ONE execution** (temp tables). This is the
   first query that reads outcomes. Export the result as JSON.
3. `python3 -I p1_score.py <extract.json>` — it asserts N 85 / 84 and calibration 56 / 56 against
   Part 1b before scoring. Verdict = A-NIFTY and B-NIFTY only (§5.8 of the pre-registration).
4. Write the result document beside the pre-registration, citing its hash `7a708a64c4bb73f0…`;
   update roadmap §2.1 P1; **apply the S92-I decision point** — a NO on both arms means the operator
   re-plans P2–P8 before anything else is built.

## 2. S92-J — the optional 3D view

**DONE 2026-10-09 (S92 post-close)** — live at `meridian-connect` `417e966`; TD-S92-NEW-2 resolved.
Residuals: TD-S92-NEW-6 (box install path); delete `/var/www/marketview.bak-1deeb87` once live has
run a full session.

## 3. Verifications owed (none recorded as done)

| Check | PASS | Closes |
|---|---|---|
| basis step, 2026-10-09 (first full day of `bd91d27`) | 0 DATA_ERROR runs | TD-S91-NEW-6 |
| basis step 08:31–09:26 IST, 2026-10-09 | 12 no-input cycles exit 0, `exit_reason` still `SKIPPED_NO_INPUT` | TD-S91-NEW-15 (basis site) |
| `gex_cycle_history` front leg vs `gamma_metrics` | 77 of 77 | TD-S91-NEW-1 |
| Telegram with the chat **unmuted** | ≈ 14 in-session sends, none overnight | TD-S91-NEW-12 |
| **Tue 2026-10-20** weekday holiday | validator silent; no chain rows; `cycle_health` CLOSED | TD-S91-NEW-13, R0.8 / TD-S89-NEW-1 |

## 4. Owed rulings

- Whether a BUILT layer that later breaks **reopens parity** or is an ordinary defect on its register.
- Doc Protocol v5 (drafted S90).

## 5. After P1

P2 (dealer-side check against participant OI) → P3 (= R2.2 + R2.3) → P4 (∂Δ/∂σ, ∂Δ/∂t evidence) →
P5 (PPC-1) → P6 (DEX standing book) → P7 (flow leg) → P8 (∂Δ/∂t every cycle, only if P4 predicts).
**Dev documents for P2–P8 — ENH entries for P6 and P7, design notes for P2 and P4 — are written when
P1 returns** (operator sequencing, 2026-10-09).

## 6. Carried

TD-S92-NEW-1 / -3 / -4 · TD-S91-NEW-2 sites 1, 3, 4, 5, 6 (adopt `core.ts_parse`) · TD-S91-NEW-3
08:40 IST Zerodha preflight · TD-S80-NEW-1 NIFTY L9 arm · ~Tue 2026-10-13 drop the S90-H backups
(TD-S90-NEW-11).
