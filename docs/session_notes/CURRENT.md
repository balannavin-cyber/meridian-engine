# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. **S99 (its pointer block, 1,090 B, sha256 `56ab7a26…`) and S100 (7,695 B, sha256 `d11e991b…`) moved at the S101 close (run in S102)**, each asserted byte-identical on both sides. **S100 (its pointer block, 1,738 B, sha256 `e9003302…`) and S101 (5,674 B, sha256 `6a68012f…`) moved at the S102 close (run in S103)**, each asserted byte-identical on both sides. **S101 (its pointer block, 1,116 B, sha256 `7313f892…`) and S102 (7,511 B, sha256 `8c50b1b1…`) moved at the S103 close (run in S104)**, each asserted byte-identical on both sides. **S103 (its pointer block with the S103 rulings, 1968 B, sha256 `771a46c4…`) and S104 (8023 B, sha256 `23ed8d18…`) moved at the S105 close**, each asserted byte-identical on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

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

## Previous session S104

**S104 — Saturday 2026-10-31 09:19 IST → Wednesday 2026-11-04 06:30 IST** (doc-close `be197b3`). The Marketview anon-key
exposure measured and closed in four layers (`docs/decisions/CASE-2026-11-03-marketview-anon-key-exposure.md`), CLAUDE.md
rule 26, two read-only sweeps, the S103 close applied, and the production box brought back from an SSM outage. The full block
is in `docs/registers/CURRENT_history.md`.

## OPERATOR RULINGS, S104

**All rulings live in `docs/research/s92_parity/rulings_s104.md`**, the single source.

| # | Topic |
|---|---|
| **S104-A** | Anon shrink Phase 1 approved (applied 18:58 IST) |
| **S104-B** | Dedicated read role `marketview_ro` |
| **S104-C** | Option B-nginx: same-origin `/rest/v1/` to Supabase REST with a server-held read-only token; A2 dropped |
| **S104-D** | Promote the same-origin bundle first, speed afterwards |
| **S104-E** | Final revoke of `anon` SELECT (22:36 IST) |
| **S104-F** | End of session called by the operator; this close |
