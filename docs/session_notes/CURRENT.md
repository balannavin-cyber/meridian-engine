# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. **S99 (its pointer block, 1,090 B, sha256 `56ab7a26…`) and S100 (7,695 B, sha256 `d11e991b…`) moved at the S101 close (run in S102)**, each asserted byte-identical on both sides. **S100 (its pointer block, 1,738 B, sha256 `e9003302…`) and S101 (5,674 B, sha256 `6a68012f…`) moved at the S102 close (run in S103)**, each asserted byte-identical on both sides. **S101 (its pointer block, 1,116 B, sha256 `7313f892…`) and S102 (7,511 B, sha256 `8c50b1b1…`) moved at the S103 close (run in S104)**, each asserted byte-identical on both sides. **S103 (its pointer block with the S103 rulings, 1968 B, sha256 `771a46c4…`) and S104 (8023 B, sha256 `23ed8d18…`) moved at the S105 close**, each asserted byte-identical on both sides. **S105 (5607 B, sha256 `c0127326…`) moved at the S107 close**, asserted byte-identical on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S107 — Saturday 2026-11-21 ≈ 10:00 IST → Thursday 2026-11-26 ≈ 10:30 IST** (engine lane; operator-called close).
The session in which the Board's "Pin" stopped being a net quantity, and in which the engine built a second gamma
calculation beside the first instead of correcting the first. Decision **ADR-033** (PROPOSED, carried out in part);
rulings **S107-A…Q** (`docs/research/s107/rulings_s107.md`); intakes **I-002** (bodies written this close) and
**I-003** (MR-OFL9, MR-S13, MR-PIN3).

**State at close.** Engine `origin/main` was **`6a69dbe`** when this close opened. This close is on branch
**`engine/s107-close`** for the operator to merge: it brings the engine's S107 package from `pin/v2-check`
(`2574709`) to `main` by path (18 files; the pin lane's check files stay on that branch) and the register edits.
**No V1 engine code changed.** Marketview live = **`d7642c2`** (bundle `index-CHOS8H-T.js`), since 2026-11-25
about 18:08 IST; the build it replaced is at `/var/www/marketview.bak-90cb618`.

**What is live that was not before.**

1. **The Board Pin is the gross pin** (`v_gex_pin_gross` over `v_gex_strike_rank_gross`). The earlier pin is
   shown as "Net peak" with its state and conviction. Regime, expansion probability, pin score and the dealer-flow
   simulation are labelled "legacy, unvalidated"; the Flip "experimental". Manual v0.6. **ENH-149.**
2. **`tape_w` can log in** (2026-11-24): password set on the box, login proved, V1–V5 read, E-1 probe passed, E-6
   comments applied. This unblocked the order-flow lane's writer; its first live 2b day is earliest Mon 2026-11-30.

**What is built and not switched on.** Gamma V2 (**ENH-150**): `merdian_compute/gamma_v2.py` (rule v1.2, one gamma
per strike), tables `gex_strike_v2` and `gex_run_v2`, the `p3b2` checker. The stored history is backfilled —
**19,050 runs, 2,679,771 strike rows, 2026-05-25 → 2026-11-25, 0 input errors** — and checked: no failure on any
run; the per-strike recompute from the chain is possible on 10,067 runs and not on the 8,983 whose chain rows are
not stored. The pin lane's independent implementation agrees on 486 chain runs and 313 stored-row runs, and with
the backfilled rows on 156 of 156 fixture runs. **Not approved:** the live writer hook, the `p3b2` job, the
`v_gex2_*` views, any Board tile on V2.

**What was refuted or not met — Assumption Register §D.61 (3 rows) and §D.62 (8 rows).** One gamma per strike is
closer to an own solve than production's per-leg rule on both symbols, and the vendor's gamma is never missing, it
is `0.0` (§D.61.1). The regime gate is computed and stored and nothing found acts on it (§D.61.3). Mine: two
expected values written from belief and given to others to check against (§D.62.1, §D.62.2); a deploy script
without the build settings, caught on staging (§D.62.3); the order-flow note that was to precede a Board pin change
was written after it (§D.62.4); a package committed on another lane's branch (§D.62.5).

**Filed:** 31 TDs (TD-PIN2-NEW-1…13, TD-PIN3-NEW-1…3, TD-OFL9-NEW-1…8, TD-S107-NEW-1…7; one closed at filing) ·
**AR §D.61, §D.62** · **ADR-033** (Decision Index row; next-free `ADR-034+`) · **ENH-149, ENH-150** (next-free
ENH-151) · System Map and Topology **§S107** · Data Inventory **§13** (hand-written) · STREAMS (X1, X3, X10 updated;
X11, X12, R9 added) · tracker **v2.23** · reference **v85** · CLAUDE.md **v1.80** (no rule changed).

## NEXT SESSION PICKS UP

1. **The `script_execution_log` read** (TD-S107-NEW-6; statement in `docs/research/s107/engine_to_pin_LATEST.md`
   §1.4). The pin lane's step 9 uses it. Asked of the operator 2026-11-26; not returned at this close.
2. **The operator's look at the live Board in market hours** with the comparison read of `v_gex_pin_gross`
   (four checks; rollback line in ENH-149). Owed from Thu 2026-11-26 after 09:20 IST; not reported at this close.
3. **Wait for the pin lane's step 9** (V1 against V2 on history), then the operator's decision. Until then build
   nothing on V2. If the decision is to go on: the **eight-check gate** for the writer hook (ENH-150), then the
   `v_gex2_*` views as **one family** (ruling S107-O).
4. **Order-flow lane:** the note on the Board Pin switch is written (`docs/research/s107/`); OFL10 decides the
   `/tape` anchor (STREAMS X1). Still owed by the engine: the E-4 contract INSERTs on the writer-start day and the
   `''` confirmation (X3).
5. **Next Board round** (authored, not run): the Pin detail panel caveat, the "#2" label, manual v0.7
   (TD-PIN3-NEW-3). It needs its own guard and promote with the proxy build settings (TD-S107-NEW-1).
6. **`data_contracts` rows** for the V2 tables and the two gross views (TD-S107-NEW-2): two reads, then the INSERTs.
7. **Operator decisions waiting:** ADR-033 PROPOSED → ACCEPTED or not; the PUBLIC grants on `cron` / `net`
   (TD-S107-NEW-3); whether the signal builder keeps running (TD-PIN2-NEW-10); the production box's memory
   (TD-PIN2-NEW-12).
8. **Carried from S106, untouched in S107:** the Sunday 2026-11-22 08:20 data point on the retail drop and the Dhan
   mint (TD-S106-NEW-7) — not read; rotate `fyers_loader` (TD-FOI1-NEW-1, S1); the MALPHA host-key fix
   (TD-S106-NEW-3); the bucket-scoped S3 policy (TD-S106-NEW-4); the greeks / forward study (ruling R9), now with
   §D.61.1 and §D.61.2 as inputs; the operator's deletion of old `.env` backups and "include administrators" on
   `main` (R6, R7); the Topology L414 second 09:05 schedule, now joined by the Windows refresh failure
   (TD-S107-NEW-4).
9. **Project knowledge:** the PK delta of this close is in `docs/research/s107/S107_close_inputs.md`. PK was at
   85.1 % when the close opened, above the 85 % prune line.

## OPERATOR RULINGS, S107

**All rulings live in `docs/research/s107/rulings_s107.md`**, the single source.

| # | Topic |
|---|---|
| **S107-A** | The regime gate (`trade_allowed`) is a leftover; registers corrected (AR §D.61.3) |
| **S107-B, -D** | The gross rule is the preferred pin; the ten-day shadow is dropped for a daily monitor |
| **S107-C** | Root `.gitignore`: one negation block for `docs/research/` |
| **S107-E** | Fix gamma at the source, one gamma per strike; the gross pin keeps the name "Pin"; no box resize |
| **S107-F…J** (R1–R6) | Versioned isolation (ADR-033); the Board Pin switches now; legacy labels now; dealer wording unchanged; no V2 flip |
| **S107-K, -L, -M, -N** | Backfill yes; the independent check; the order of work; every stored run kept |
| **S107-O, -P, -Q** | Board to V2 by family in one release; an eight-check gate for the writer hook; no Pin Band rebuild, no label changes |

## LANES (Doc Protocol v5.1 Rule 7 — pointers only; the hub register is `docs/registers/STREAMS.md`)

| Lane | Series / open session | Latest close inputs |
|---|---|---|
| Engine (hub) | S / **S108** next | `docs/research/s107/S107_close_inputs.md`; intake `docs/registers/intake/I003.md` |
| Order flow (tape) | MR-OFL / **OFL10** next | `claude/ofl/MR_OFL9_close_inputs.md` (OFL9, 2026-11-24) |
| Retail | MR-S / **S14** next | `claude/retail/MR_S13_close_inputs.md` (S13, 2026-11-23) |
| Futures OI | MR-FOI / **FOI3** next | `MR_FOI2_close_inputs.md` (FOI2, 2026-11-19) |
| Board pin | MR-PIN / **PIN4** in session | `docs/research/pin_proof/MR_PIN3_close_inputs.md` (PIN3, 2026-11-25) |
| Parity (reference) | none — build closed 2026-10-09 (ADR-025) | `docs/research/parity_eval/` |

**Project knowledge:** every lane follows `docs/operational/MERDIAN_PK_Protocol_v1.md` — P5 at open, P4 at close, PK delta in its close inputs; the engine runs P6 and records `knowledge_size` here at every close. **At the S107 close: 1,702,983 / 2,000,000 (85.1 %) when the close opened**; the figure after the engine's P4 and the Tier A refresh is in `docs/research/s107/S107_close_inputs.md`.

## Previous session S106

> *The `NEXT SESSION PICKS UP` list inside this block is as written at the S106 close and is superseded by the S107 list above. Its item 1 (`tape_w`) is done (2026-11-24); item 3 is done (2026-11-23); item 9 is met for OFL9, MR-S13, PIN2 and PIN3; items 2, 4–8 and 10 are carried in the S107 list, item 8.*

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

