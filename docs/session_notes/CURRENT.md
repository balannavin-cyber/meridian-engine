# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. **S99 (its pointer block, 1,090 B, sha256 `56ab7a26…`) and S100 (7,695 B, sha256 `d11e991b…`) moved at the S101 close (run in S102)**, each asserted byte-identical on both sides. **S100 (its pointer block, 1,738 B, sha256 `e9003302…`) and S101 (5,674 B, sha256 `6a68012f…`) moved at the S102 close (run in S103)**, each asserted byte-identical on both sides. **S101 (its pointer block, 1,116 B, sha256 `7313f892…`) and S102 (7,511 B, sha256 `8c50b1b1…`) moved at the S103 close (run in S104)**, each asserted byte-identical on both sides. **S103 (its pointer block with the S103 rulings, 1968 B, sha256 `771a46c4…`) and S104 (8023 B, sha256 `23ed8d18…`) moved at the S105 close**, each asserted byte-identical on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S106 — Thursday 2026-11-05 ≈ 11:30 IST → Saturday 2026-11-21 ≈ 10:00 IST** (engine lane; doc-close this pass).
Sixteen days in which engine-lane work ran in chat under the name "S105" after that session's git close, and **no
lane fact reached an engine register.** That gap is what **Doc Protocol v5.1** (in force 2026-11-21, ruled "as
recommended") and **`docs/registers/STREAMS.md` v0.2** exist to shut: five lanes, one hub, each fact with one home.
This close is the first run of the v5.1 intake: **`docs/registers/intake/I001.md`** (I-001), rulings **R1–R9**.

**State at close.** Engine `origin/main` was **`e4ef1b8`** when this close opened; the archive of the engine-lane
docs is **`c2fde5b`** (20 files, 1,588 insertions: `docs/research/s106/`, `docs/research/parity_eval/`, STREAMS.md,
Doc Protocol v5.1, I-001). **This supersedes the S105 block's "engine `origin/main` = `be197b3`, unchanged"** —
true on 2026-11-05, and seven commits stale since: `7c64e7d` (the S105 close merged), `ae2b10a`, `9107c79`,
`79efb0b` (tape scoring v0.4), `8fde9df`, `ba505cf` (futures-OI pre-registrations) and `e4ef1b8`. No engine
compute, no view and no DDL changed in this close; it is documentation only.

**What closed.** **One-login is live** — E1/E3/E10 shipped in `e4ef1b8` (`dhan_drop.py`, `bin/dhan_login.sh`,
tests T1–T10) and the **first live drop ran 2026-11-21** with `feed_adopted`; E9 is the daily 08:20 IST login cron.
The **Dhan mint is recorded at 08:20 IST** (`50 2 * * 1-5`, moved at S100-G), correcting three stale 08:35
statements. **18 TDs filed** under the new lane prefixes — TD-S106-NEW-1…10, TD-FOI1-NEW-1…3, TD-FOI2-NEW-1,
TD-PIN1-NEW-1…4 — and `tech_debt.md` is no longer sixteen days behind.

**What was refuted — and nothing shipped on it.** **Assumption Register §D.60** (7 rows). The **Board pin is not
the dominant-gamma strike** (matches on 15–36 % of runs; pin gamma negative on 21–47 %; 6/6 verdicts FAIL) and
**nothing on the Board changed**. The **vendor's call/put gammas at one strike disagree** (ratio 1.11–1.43, median
1.22), which **amends D.19.2** — the schema decision stands, the IV-skew reading does not. **Futures OI predicts
nothing** we tested (§D.60.4 NOT MET; §D.60.5 M1/M2/C1 all negative, the 2026-04→08 holdout spent). The **MALPHA
token hop is a cron, not manual** (§D.60.6), and the **S105 `tape_w` grants and R-2 were applied all along**
(§D.60.7) — three documents agreed they were not, because each was copied from the last rather than read.

**Filed:** 18 TDs · **AR §D.60** (7 rows) · ENH-125 dated line (D-5a lifted for the MR-PIN look-back only; Board
decline stands) · System Map and Topology **§S106** · Data Inventory **§12** (hand-written, flagged as outside the
generator) · tracker **v2.22** · reference **v84** · CLAUDE.md **v1.78**. **No ADR** (ruling R3: Fyers is a
research-only source; ADR-033 waits for a live ingest) and **no new ENH** (next-free stays ENH-149).
**The old-spec-name referrer sweep is RULED, not open:** nine archive and checksum-pinned record files
still carry the old spec file name and **stay as written** — operator ruling 2026-11-21, on CLAUDE.md rule 20 (history
archives), the S104 sweep record's own `SHA256SUMS` pin, and I-001's two occurrences being the rename instruction.
Six live referrers were updated; the standing requirement binds new and edited text only (TD-S106-NEW-9).

## NEXT SESSION PICKS UP

1. **`tape_w`: the password step, V2/V3/V5 and the login proof.** This is what blocks the order-flow lane's first
   live 2b day (earliest Mon 2026-11-23). Grants and R-2 are already applied — read them, do not re-apply.
2. **Sunday 2026-11-22, 08:20 IST:** the second data point on the retail drop and on the Dhan mint — did the drop
   run and did the RECOVERED alert fire (TD-S106-NEW-7)?
3. **DONE 2026-11-23 ~05:05 IST (operator; catalog read confirmed the same day; I-002 section 6).** Was: at the MR-PIN2 close, undo the `merdian_ro` SELECT + policy `ro_select_merdian` on `fyers_futures_bars_1m`
   (ruling R4; undo SQL in `claude/pin/MR_PIN1_close_inputs.md` §3).
4. **Rotate `fyers_loader`** — its password is in a chat transcript (TD-FOI1-NEW-1, the only S1 filed this close
   besides the gamma leg) and clear `$env:FYERS_LOADER_PW` on Local.
5. **MALPHA host-key fix** (TD-S106-NEW-3, ruling R8): `StrictHostKeyChecking=yes`, token on stdin not `/tmp`,
   refuse an empty value, write via temp file + rename.
6. **Bucket-scoped S3 policy** for the production box, then detach `AmazonS3FullAccess` (TD-S106-NEW-4).
7. **The greeks / forward study** — one engine-lane study (ruling R9), fed by MR-FOI and MR-PIN. §D.60.3 leaves the
   cause OPEN with three unexamined candidates: bar closes vs mids, no intraday decay, calendar-day T.
8. **Operator, outside a session:** delete the old `.env.bak_*` / `.env.save*` files (ruling R6, TD-S106-NEW-6) and
   set "include administrators" on `main` branch protection (ruling R7, TD-S106-NEW-8).
9. **Every lane's next close inputs must carry the "Engine intake" section** (v5.1 Rule 13, STREAMS §4 R3) —
   OFL9, MR-S13, FOI3, PIN2. Without it, the next engine close is as blind as this one was.
10. **VERIFY: Topology L414 second 09:05 `refresh_dhan_token.py` schedule vs the single `50 2` crontab line** (E1 plan
    read 2026-11-20: one Dhan login line). Operator ruling 2026-11-21: no TD until it is measured — read the live
    crontab and the Windows Task Scheduler, then correct whichever register is wrong.

## OPERATOR RULINGS, S106

**All rulings live in `docs/registers/intake/I001.md` §1**, the single source (approved 2026-11-21 ~09:52 IST,
"as recommended"). They are numbered R1–R9, not S106-A…F: this close's rulings came in with the intake rather
than from a session's own ruling file, and renumbering them would break every citation already written.

| # | Topic |
|---|---|
| **R1** | Doc Protocol v5.1 in force (Rules 12–17); `STREAMS.md` v0.2 in force |
| **R2** | The 2026-11-05 → 11-21 engine work closes as **S106**; "S105" keeps meaning `eba1193` |
| **R3** | Fyers is a **research-only** data source; ADR-033 waits for a live Fyers ingest |
| **R4** | The `merdian_ro` grant on `fyers_futures_bars_1m` stays until MR-PIN2 closes, then is undone |
| **R5** | Tracker S99-D line applied as "held, tested null" |
| **R6** | Old engine `.env.bak_*` / `.env.save*` deleted by the operator (not in this close) |
| **R7** | Branch protection on `main`: set "include administrators"; merges stay the operator's |
| **R8** | MALPHA token push: host-key checking **on**, engine host key pinned on MALPHA |
| **R9** | The greeks / forward question is **one engine-lane study**, fed by MR-FOI and MR-PIN |

## LANES (Doc Protocol v5.1 Rule 7 — pointers only; the hub register is `docs/registers/STREAMS.md`)

| Lane | Series / open session | Latest close inputs |
|---|---|---|
| Engine (hub) | S / **S106** (this close) | `claude/intake/engine_intake_I001_2026-11-21.md`; git `docs/registers/intake/I001.md` |
| Order flow (tape) | MR-OFL / **OFL9** in session | `MR_OFL8_close_inputs.md` (OFL8, 2026-11-16) |
| Retail | MR-S / **S13** in session | `MR_S12_close_inputs.md` (S12, 2026-11-18) + the S13 interim note |
| Futures OI | MR-FOI / **FOI3** next | `MR_FOI2_close_inputs.md` (FOI2, 2026-11-19) |
| Board pin | MR-PIN / **PIN3** in session | `docs/research/pin_proof/MR_PIN2_close_inputs.md` (PIN2, 2026-11-22) |
| Parity (reference) | none — build closed 2026-10-09 (ADR-025) | `docs/research/parity_eval/` |

**Project knowledge:** every lane follows `docs/operational/MERDIAN_PK_Protocol_v1.md` — P5 at open, P4 at close, PK delta in its close inputs; the engine runs P6 and records `knowledge_size` here at every close.

## Previous session S105

> *The `NEXT SESSION PICKS UP` list inside this block is as written at the S105 close and is superseded by the S106 list above. Its items 1-4 are carried as TD-S105-NEW-7 / -6 / -4 / -5 and its item 5 is done: `ops/s105-close` merged as `7c64e7d` and `tape/scoring-v04` as `79efb0b`.*

**S105 — Wednesday 2026-11-04 ≈ 18:30 IST → Thursday 2026-11-05 ≈ 11:30 IST** (tape stream; operator-called close). Two jobs,
both offline and both on `meridian-tape-staging`, never `origin`: the **exploration** of the three declared exploration days
under pre-registration v0.3, and the **v0.4 scoring build** that implements the definitions it fed. Rulings
`docs/research/s92_parity/rulings_s105.md` (S105-A…F). Branches: `tape/exploration` `bc14f18` (exploration) · `9cf1fcb` (S-window counts); `tape/scoring-v04` `6b8bdf9` (code) · `ea27c17` (ledger entry) · `0ef8f71` (ledger note + `.gitattributes`). Operator's staging-`main` commits in the window:
`f481d9c` (pre-registration v0.4, sha256 `b45477d3…`) and `07a8a53` (ledger v0.4 entry beside it).

**State at close.** Engine `origin/main` = `be197b3`, unchanged by S105 (no engine code, no DDL, no box change); this close is
on branch `ops/s105-close` for the operator to merge. Tape scoring head `0ef8f71`: `score.py` `9011aba0…`,
`scoring_extract.sql` `8f3db643…`, `run_extract.sh` `01bff874…`, `wilcoxon.py` `e4dbace5…` (unchanged); `check_hashes()` =
no differences against the last ledger entry. Guards 25/25, unit checks 21/21, mutants 40/40 ×5 with 5/5 controls (Local,
R-1 override). Offline suite still **40 steps**.

**What was established**

1. **The clocks line up (exploration B.1–B.2).** Board runs land ≈ 6.6 s after each 5-minute mark; a run's spot equals the
   close of the bar ending at the mark (SENSEX exact on 73–80 % of runs), so `hist_spot_bars_1m` labels are minute-start.
   That exposed the **R(T) one-bar-late defect** in the hashed v0.2 scorer (`m0 = hm + 1`): fixed in v0.4 before any run,
   **no result affected** (TD-S105-NEW-1, closed at filing).
2. **Tape flow moves with spot, not ahead of it** (pooled 1-minute corr 0.82 at lag 0, 0.06 at +1). The one early signal is
   **Kite OI at the wall**, which shows the next run's ≥ 5 % wall-OI move a median 1.1 min sooner (88 % / 93 % vs base 14 % /
   9 %) — the same exchange number read earlier. Recorded in v0.4 as descriptive **T4**, never an H-B input.
3. **v0.4's tape sign S is the trailing 30 minutes** (cumulative S was +1 on every NIFTY cycle; group counts only for
   15/30/60/90, no outcome computed; window ruled 08:14 IST). Built with per-label H-B, window-coverage reporting, T4 as an
   **optional** input (`tape_minute_oi`, `OPTIONAL SKIP` never aborts), and a hash check on the **last** ledger entry.
4. **Wording and exposure carried.** v0.4 §6 says "three files"; four are hashed (ledger note, TD-S105-NEW-2, closed). LF-only
   hashes are exposed to a CRLF checkout: `services/tape_scoring/.gitattributes` added; the exploration tree's `SHA256SUMS`
   still exposed (TD-S105-NEW-3).
5. **Not run / not verified.** The full `tests/run_offline.sh` (owed on Linux after 15:45; Rule 23's `ulimit -v` half is
   unenforceable on Windows, TD-S105-NEW-4); the `tape_minute_oi` SELECT against `roq.sh`'s 30 s timeout and a real `roq.sh`
   run (TD-S105-NEW-5). **The scoring build ran on Opus; the `/model` switch to Sonnet did not happen** (AR §D.59.2).
6. **Operator readings at the close, filed not investigated:** the recorder's `n_subscribed` 186 at 09:01 vs 148 expected,
   per-symbol split pending (TD-S105-NEW-6); the weekday timer's NEXT blank while its service runs (TD-S105-NEW-7).

**Filed:** TD-S105-NEW-1…7 (-1, -2 closed at filing). **AR §D.59** (6 rows, all mine). **No ADR, no ENH.** CLAUDE.md v1.77
(footer only; no rule changed).

## NEXT SESSION PICKS UP

1. **After 15:52 IST today:** `systemctl list-timers` on the tape box — NEXT must read Fri 2026-11-06 03:20 UTC
   (TD-S105-NEW-7); read the per-symbol `n_subscribed` split (TD-S105-NEW-6) and record the SENSEX band and its effective date
   in the ledger (v0.4 §6).
2. **On Linux after 15:45 IST:** `( ulimit -v 700000; bash tests/run_offline.sh )` at the merged tape head (TD-S105-NEW-4).
3. **First operator extract:** read the `tape_minute_oi` PRECHECK / EXTRACT lines and time (TD-S105-NEW-5).
4. **`docs/tape/.gitattributes`** `* text eol=lf` on `tape/exploration`, then a fresh-clone `SHA256SUMS` check (TD-S105-NEW-3).
5. **Merge** `ops/s105-close` (this close) and decide when `tape/scoring-v04` merges to engine `main`.
6. **Carried from S104** (unchanged; see the S104 block in `CURRENT_history.md`): the second box and the Wednesday open,
   Marketview proxy parity and `http2`, the anon-class closes (TD-S81-NEW-3, TD-S39-NEW-3, TD-S104-NEW-5/-6/-2), the view md5
   registration, the S103 carries, ENH-148.

## OPERATOR RULINGS, S105

**All rulings live in `docs/research/s92_parity/rulings_s105.md`**, the single source.

| # | Topic |
|---|---|
| **S105-A** | Exploration plan approved (1-minute local tape, two added parameters, real depth, directory + pointer) |
| **S105-B** | S-window group counts only (15/30/60/90); window 30 ruled into v0.4 §1 |
| **S105-C** | v0.4 scoring plan F-1…F-4 approved; T4 input optional; last-entry hash check |
| **S105-D** | Ledger note (four files) and `services/tape_scoring/.gitattributes`; no code change |
| **S105-E** | Close in a new worktree off `main`, branch pushed for merge |
| **S105-F** | The eight close items, carried here and in TD-S105-NEW-1…7 |

