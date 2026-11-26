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

