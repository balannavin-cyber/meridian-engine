# S93 — session starter prompt (paste as the first message)

Session 93, MERIDIAN. Read, in this order, before doing anything: `CLAUDE.md`,
`docs/session_notes/CURRENT.md`, `docs/session_notes/S93_dev_starter.md` (the ordered work list),
`docs/research/s92_parity/rulings_s92.md`, and roadmap §2.1 in
`docs/research/s90_agentic/agentic_layer_roadmap_S90.md`. Project docs first, then git. Do not ask
me to check anything the docs already answer.

**Where we are.** Hedgewall parity is CLOSED (ADR-025 Amendment D). Work runs on the post-parity
track, ruling S92-I: P1 → P8, each to DONE-with-evidence or DECLINED-ON-EVIDENCE, in order. The
optional 3D view is live (`meridian-connect` `417e966`, S92-J). **P1 is mid-run, and nothing in
P2–P8 starts before P1's decision point.**

## The one concern of this session: finish P1 and apply the S92-I decision point

Folder `docs/research/s92_priority/p1/`; read its README first. Pre-registration hash
`7a708a64c4bb73f0712a6d6e78f92a5d411a8ece` — nothing in it changes now.

**Only after 15:40 IST on a trading day** (the GEX writer is idle then). If it is earlier, do the
section-2 checks first and wait.

1. **Part 3** — `p1_part3_replay_check.sql`, one statement, Supabase SQL editor.
   PASS = **zero rows**. Any row: STOP and report it. Do not reason about which side is right,
   and do not run Part 2.
2. **Part 2** — `p1_part2_extract.sql`, **the whole file as ONE execution** (temp tables; the editor
   shows only the last result). It is the first query that reads outcomes. I export the result as JSON
   and send it.
3. **Score** — `python3 -I p1_score.py <extract.json>`. It must first assert N 85 / 84 and calibration
   56 / 56 against `part1b_result_2026-10-09_0923.json`; if that assertion fails, stop. The verdict uses
   A-NIFTY and B-NIFTY only (pre-registration §5.8); everything else is descriptive.
4. **Record** — result document beside the pre-registration, citing its hash; roadmap §2.1 P1 →
   DONE or DECLINED-ON-EVIDENCE; commit.
5. **Decision point (S92-I)** — state the result plainly. If neither arm beats the null, P2–P8 are
   re-planned with me before anything is built. If one does, draft the P2–P8 dev documents
   (ENH entries for P6 DEX standing book and P7 flow leg; design notes for P2 and P4) for my review.

Give me every command and SQL block in full, one step at a time, with the exact output that means PASS.

## 2. Checks owed (any time in the session; none is recorded as done)

Build each query from `merdian_reference.json` and the cited TD entry. Do not guess column names.
State before running what result would FAIL each one.

| Check | PASS | Closes |
|---|---|---|
| basis step on 2026-10-09 (first full day of `bd91d27`) | **0 DATA_ERROR** runs in `script_execution_log` | TD-S91-NEW-6 |
| basis step 08:31–09:26 IST, 2026-10-09 | the **12 no-input cycles exit 0**, `exit_reason` still `SKIPPED_NO_INPUT` | TD-S91-NEW-15 (basis site) |
| `gex_cycle_history` front leg vs `gamma_metrics`, one full session | **every** `gamma_metrics` cycle has its front-leg row (S91 target: 77 of 77, not 64) | TD-S91-NEW-1 |
| Live 3D view after a full session | `/board` loads no 3D code; `/board/3d` shows 14 sessions with today's slice settled | then I delete `/var/www/marketview.bak-1deeb87` |
| Telegram, chat **unmuted** | ≈ 14 in-session sends, none overnight | TD-S91-NEW-12 (needs me to unmute) |

**Dated, not this session unless the date has come:**
- **~Tue 2026-10-13:** drop the S90-H backup tables (TD-S90-NEW-11).
- **Tue 2026-10-20 (weekday holiday):** validator silent; no chain rows; `cycle_health` CLOSED
  → TD-S91-NEW-13, R0.8 / TD-S89-NEW-1.

## 3. My calls, do not do them without me

- **TD-S92-NEW-5:** insert the closed `trading_calendar` row for 2026-10-02 (SQL in the TD entry), then
  check the other 2026 holidays in `trading_calendar.json` for the same gap.
- **Owed rulings:** whether a BUILT layer that later breaks *reopens parity*; Doc Protocol v5.

## 4. Carried (not this session's concern)

TD-S92-NEW-6 (guards hide install failures; drop `--silent`) · TD-S92-NEW-1 / -3 / -4 ·
TD-S91-NEW-2 sites 1, 3, 4, 5, 6 → `core.ts_parse` · TD-S91-NEW-3 08:40 Zerodha preflight ·
TD-S80-NEW-1 NIFTY L9 arm.

## Standing rules for this session

- Delivery: you cannot push. Commit locally, `git format-patch` → xz → base64 in chunks ≤ 111 lines,
  each with its own sha256 prefix, plus the combined sha256 and line count; I paste with nano, run
  `tr -d ' \t\r'` before checking, then `git am --3way` and push from `~/meridian-engine`. Confirm
  TREE_MATCH after.
- No fixture-suite run 08:30–15:40 IST, and every run under `ulimit -v` (rule 23).
- Never run a GRANT an error HINT suggests. Never cat/grep `.env` (rule 19).
- Lovable never touches Supabase, SQL, env, package or config files.
- Never label second-order terms vanna or charm; γ stays lower case.
- Upload changed register docs to the Project when they change (rule 12).
