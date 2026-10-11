# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S95 — 2026-10-11 (Sunday, out of hours).** DEX and S\* on the live board; P3a run and wired
in; S\* pre-registered, gated, applied; P5 measured, ruled and applied; five owed rulings made.
This block points; the detail lives in the files named. Rulings:
`docs/research/s92_parity/rulings_s95.md` (S95-A…G, the single source). **First close on Doc
Protocol v5** (S95-E). **Progress lives in the tracker**, now `docs/registers/agentic_layer_roadmap_S90.md`
(v2.12; the old path is a pointer stub).

**`origin/main` — all pushed.** `882df80` P3a · `90c8c50` / `7566e8c` S\* · `21d3142` / `47989ed`
P5 · this close. **Production tree `~/meridian-engine` at `1390584`; pull owed** before Monday's
preflight (S95 carries docs, tests and sql only). **meridian-connect LIVE `858cb46`** (DEX
`d1912d2` → `392256a`; S\* `103f663` / `1c5a047`; sub-line `719e85c` / `858cb46`); backups
`/var/www/marketview.bak-13b1410`, `.bak-392256a`.

**What was established**

1. **P6 DONE.** The DEX book is on the Flows tab with the P2 phrase, every leg total beside its
   gap, and the dte-0 note (ENH-140 board read). **S\*** `v_dex_repriced_zero` (**ENH-141**) was
   pre-registered (`7bfafb49`), scored **APPLY** (G1 on 11 arms; G3/G4/G5 on 7 of 10; the widest
   G5 spread 0.239 σ₁d, 95 % of tolerance, on 1-dte SENSEX), applied, and shown as a tile plus a
   dotted ladder rule. Staging review caught the tile measuring from the chain spot while the
   header shows another clock's spot; fixed to *"above chain spot …"* before promote.
2. **P3a DONE** — PASS on the six golden days under `ulimit -v 700000` (run of record on the
   box, S95-A), wired as `run_offline.sh` step 12/12; its PE-sign mutant was a silent no-op until
   fixed (`882df80`). P3b needs approval.
3. **P5 DONE** — `v_oi_since_preopen` (**ENH-142**), ruling **S95-B**. On NIFTY the pre-open row
   is the 15:40 close on every leg (26/26 changeovers); on SENSEX BSE revises 23–41 % of legs
   overnight. Section 4 PASS; 4d reproduced probe 1 (472 / 0 / 0 and 390 / 102 / 8,420).
4. **Vendor OI on untraded legs is not a measurement** (TD-S95-NEW-1): SENSEX 09-25 / 09-28 /
   09-29, legs with volume 0 held 33–94 % of front OI and 73–98 % of DEX gross.
5. **Rulings S95-C…G** applied at this close: ADR-015 Amendment A; parity is not reopened by a
   break; Doc Protocol v5 adopted; generated-CSV policy (TD-S93-NEW-2 resolved); P8 → dte 1.

**Corrections to my own work:** Assumption Register **§D.49** (11 rows, 9 mine). The one to
carry: a check is tested at real volume, not only on local fixtures (D.49.7).

**DDL applied:** `v_dex_repriced_zero`, `v_oi_since_preopen` (each batch ending in its own
verification SELECT). **ADR-015 amended; rules 0–24 stand, rule 23's text carries S95-A.**

## NEXT SESSION PICKS UP

1. **Pull the production tree** — `~/meridian-engine`, `git pull --ff-only`, before Monday's preflight.
2. **First live session with DEX and S\* on the board:** read both tiles against SQL during
   market hours (the S95 reads were on a closed weekend).
3. **ACL fingerprint re-baseline** before the next Lovable round — `v_oi_since_preopen` was
   created after the 13:18 snapshot (`relations 346 06c07d80…`).
4. **P7, the flow leg** — unblocked (P5 and P6 live); a design note first. **P3b** needs approval.
5. **Checks owed:** Telegram with the chat unmuted (TD-S91-NEW-12) · the 3D view after a full
   session, then delete `/var/www/marketview.bak-1deeb87` · **Tue 10-13** drop the S90-H backups
   (TD-S90-NEW-11) · **Tue 10-20** live-day half of TD-S91-NEW-13 (the calendar half is done).
6. **Filed this session:** TD-S95-NEW-1 (untraded-leg vendor OI), -2 (`trading_calendar` holds
   no rows for past closed days).
7. **Carried:** TD-S94-NEW-1…4 · TD-S93-NEW-1 / -3 · TD-S91-NEW-2 sites 1, 3, 4, 5, 6 ·
   TD-S91-NEW-3 · TD-S80-NEW-1 · TD-S92-NEW-3…6 · the stale PK draft
   `claude/P2_dealer_side_design_2026-10-10_DRAFT.md` and the duplicate PK `CLAUDE_history.md`
   (operator's call).

## OPERATOR RULINGS, S95

**All rulings live in `docs/research/s92_parity/rulings_s95.md`**, the single source.

| # | Topic |
|---|---|
| **S95-A** | Rule 23's hours bind trading days only; `ulimit -v` always |
| **S95-B** | P5: the pre-open row is the baseline; a view; front expiry |
| **S95-C** | ADR-015's gloss corrected by amendment, English only |
| **S95-D** | A break in a BUILT layer is maintenance; parity is not reopened |
| **S95-E** | Doc Protocol v5 adopted |
| **S95-F** | Generated CSVs: committed result inputs by negation line; bulk exports local by sha256 |
| **S95-G** | P8 re-scoped to dte 1; P4 gate unchanged |

## Previous session S94

**S94 — 2026-10-10 (Saturday, out of hours).** The P2–P8 re-plan ruled; P2 and P1c answered
to their pre-registrations; P4 pre-registered and accruing; the DEX standing book applied,
verified and live; the board's wording settled. This block points; the detail lives in the
files named. Rulings: `docs/research/s92_parity/rulings_s94.md` (S94-A…I, the single source).

**`origin/main` — all pushed. Production tree `~/meridian-engine` is at `0f1e5bc`; pull owed**
(operator, `git pull --ff-only`, before Monday's preflight — S94 carries no runtime code, but
rule 2 compares hashes). `0f1e5bc` PK-only docs archived · `f1db3f1` S94-A…E · `dcf567a` /
`c920832` / `2dbf8a4` **P2** · `cde0e0b` **P4** · `ed4979b` / `4a74885` / `c17e30d` **P1c** ·
`6c19553` Lovable kit · `4a0733d` S94-F…I · `d843354` P6 COMMENT brought current · this close.
**meridian-connect:** `5b84c16` (net ±γ relabel, not approved) → **`13b1410` live** (S94-F).
Backups `/var/www/marketview.bak-417e966`, `.bak-5b84c16`, `.bak-1deeb87`.

**What was established**

1. **S93-B is discharged** by **S94-A** (P2 → P4 → P1c → P3; P5–P7 held; P8 gated), amended by
   **S94-G**: P5 and P6 released, **P7 held until P6 is live**, **P8 NEEDS RE-SCOPE** (L8 skips
   dte 0 by design, so "∂Δ/∂t every cycle on expiry day" cannot be built as worded).
2. **P2 DONE — REGIME-DEPENDENT** (`2dbf8a4`; v2 `7342cacd…`). Of 340 dates (2025-05-28 →
   2026-10-09) the position the board's CE+/PE− sign assumes for the dealer held for **Pro on
   23, Pro+FII on 0** — and for **Client on 226** (descriptive). Aggregate, NSE only, dates not
   independent, so no stronger statement is available. v1 (`f425f171…`) **stopped** on an
   exact-equality gate that NSE's ±1 rounding broke on 457 of 1,360 cells; v2 was registered
   before scoring.
3. **P1c DONE — INCONCLUSIVE** (`c17e30d`; `abde07ca…`). NIFTY holdout pinned-positive n = 6,
   below the pre-registered 8 (calibration e 0.136, holdout 0.023, untested). The dampening
   claim is **still untested to standard** (Assumption Register §D.2, premise QUALIFIED).
4. **P4 PRE-REGISTERED, ACCRUING** (`cde0e0b`; `0a8af475…`) — net ∂Δ/∂t sign at dte 1, forward,
   pooled n = 40, about 13 weeks. Chain retention is unmeasured (TD-S94-NEW-4).
5. **`merdian_ro` could not read two tables.** `participant_oi_daily` and
   `data_contamination_ranges` returned zero rows with no error until a `merdian_ro_select`
   policy each (operator DDL ~08:32 IST, `sql/2026-10-10_s94_merdian_ro_read_policies.sql`).
   **Rule 13 checks made through `roq.sh` before today could not find a range** (TD-S94-NEW-1).
6. **The board's γ labels stay dampening / amplifying** (S94-F). I put a net ±γ relabel live
   (`5b84c16`) that the operator had not approved; restored as `13b1410` with "quantity"
   (**TD-S92-NEW-1 resolved**), the P1 levels note (S94-D) and one P2 caveat sentence in the
   Net Γ explanation only.
7. **P6 `v_dex_standing_book` is LIVE; ENH-140 filed.** The first apply landed Section 1 only
   (COMMENT NULL, default ACL) while the editor said Success and **4a passed**; 4b's
   `merdian_ro` permission error found it, and Sections 2–3 were re-run with a trailing
   verification SELECT (TD-S94-NEW-3). Section 4 then **PASSED** — 4i on **862 strikes, max
   abs diff 3.638e-12 Cr**; 4f's 10-02 frozen-day control fired as it should. On 10-09 two legs
   were **net positive** (NIFTY 10-19, SENSEX 10-22), so the two dealer readings disagree in
   sign there — more reason for no dealer column. **The board read is owed.**
8. **P3a** (`tests/test_p3a_invariants.py`, offline invariants I1–I6 on the golden days, mutants
   built in) is **committed at this close, not run**, and not wired into `run_offline.sh`.

**Corrections to my own work.** Recorded as Assumption Register **§D.48** (9 rows, 7 mine):
- the unapproved relabel;
- P2 v1's exact-equality gate;
- the P1c scorer read P1's time-only `ats_ist` as a full timestamp, and its σ tolerance was set
  too tight before commit;
- the S94 guard died silently under `pipefail` on a zero-match `git grep`;
- a `grep -F "a\|b"` check could not match anything;
- I had the operator copy a 7,812-character line out of the terminal, then read 4a's pass as a
  full apply.

Also recorded there: the S93 4a expectation is labelled per leg when it is per symbol, and the
`merdian_ro` access assumption. The P6 COMMENT would have gone live saying "unruled" and
"pending ruling"; it was patched before the apply (`d843354`).

**Registers touched:**
- `rulings_s94.md` (S94-A…I, and the P6 outcome line)
- roadmap **v2.9 → v2.11**
- Enhancement Register (**ENH-140**, Part 9)
- `tech_debt.md` (**TD-S94-NEW-1…4**; TD-S92-NEW-1 → Resolved)
- Assumption Register (§D.2 ×2, **§D.48**)
- `merdian_reference.json` **v73**
- `CLAUDE.md` **v1.67**
- `sql/2026-10-09_s93_v_dex_standing_book.sql` (comments only)
- `CURRENT.md` (S92 → `CURRENT_history.md`)
- `session_log.md` (S85 → history)

**No ADR filed, none amended; rules 0–24 unchanged. DDL applied:** two RLS policies; the P6 view.

## NEXT SESSION PICKS UP — as S94 left it (SUPERSEDED by the S95 list above)

1. **Pull the production tree** — `~/meridian-engine`, `git pull --ff-only` to this close, before
   Monday's preflight.
2. **DEX on the board (P6).** Run one Lovable pass under the S92 guard, layout-only. It shows the
   book with *"open-interest delta; dealer side regime-dependent (P2)"*, and every leg total sits
   beside its `leg_gap_oi_qty`. On dte 0 the explanation says greek gaps can flip the total's
   sign (S94-I). Verify on `/staging/` against the view before promoting. **The ACL fingerprint
   needs a fresh baseline**: the S94 baseline (`rls_policies 28 d16e21d6…`, relations 344) was
   taken before the view existed.
3. **P3a** — run `tests/test_p3a_invariants.py` out of hours as `( ulimit -v 700000; … )`, then
   decide whether it joins `run_offline.sh`. P3b (the SC sidecar) needs operator approval after
   P3a reports.
4. **S\*** — `v_dex_repriced_zero`, L3's gate record re-run for the delta curve (S94-H).
   **P5** (PPC-1) is released.
5. **Checks owed, none recorded as done:**
   - Telegram with the chat unmuted (**TD-S91-NEW-12**).
   - The 3D view after a full live session, then delete `/var/www/marketview.bak-1deeb87`.
   - **~Tue 10-13:** drop the S90-H backup tables (**TD-S90-NEW-11**).
   - **Tue 10-20** (weekday holiday): validator silent; no chain rows; `cycle_health` CLOSED
     (**TD-S91-NEW-13**, **TD-S89-NEW-1 / R0.8**). NIFTY's W2 leg expires Mon 10-19, which fits
     a 10-20 holiday; that is evidence from the expiry dates, not a `trading_calendar` read.
6. **Rulings owed:**
   - the **ADR-015 sign-convention gloss**;
   - whether a BUILT layer that later breaks **reopens parity**;
   - **Doc Protocol v5**;
   - **TD-S93-NEW-2** (gitignore policy for generated CSVs);
   - **P8 re-scope**.
7. **Filed this session:**
   - **TD-S94-NEW-1** — `merdian_ro` RLS blind spot; audit residual.
   - **-2** — roq's COPY guard.
   - **-3** — partial apply from a terminal copy.
   - **-4** — P4 vs chain retention.
8. **Carried:**
   - TD-S93-NEW-1 / -3.
   - TD-S91-NEW-2 sites 1, 3, 4, 5, 6.
   - TD-S91-NEW-3.
   - TD-S80-NEW-1.
   - TD-S92-NEW-3 / -4 / -5 / -6.
   - Delete the stale PK draft `claude/P2_dealer_side_design_2026-10-10_DRAFT.md` — needs the
     operator's yes.
   - The duplicate PK `CLAUDE_history.md` (10-08 copy) — the operator removes it in the UI.

## OPERATOR RULINGS, S94

**All rulings live in `docs/research/s92_parity/rulings_s94.md`**, the single source.

| # | Topic |
|---|---|
| **S94-A** | The P2–P8 re-plan (discharges S93-B) |
| **S94-B / -C** | P1c added; P1b deferred |
| **S94-D** | The P1 evidence note on the board |
| **S94-E** | PK cleanup to a parallel session |
| **S94-F** | Board γ labels stay dampening / amplifying; P2 caveat in the Net Γ explanation only |
| **S94-G** | Amends S94-A: P5/P6 released, P7 held until P6 live, P8 needs re-scope |
| **S94-H** | S\* as its own view after the book |
| **S94-I** | Vendor delta for the book |
