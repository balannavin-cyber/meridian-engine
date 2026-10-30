# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. **S99 (its pointer block, 1,090 B, sha256 `56ab7a26…`) and S100 (7,695 B, sha256 `d11e991b…`) moved at the S101 close (run in S102)**, each asserted byte-identical on both sides. **S100 (its pointer block, 1,738 B, sha256 `e9003302…`) and S101 (5,674 B, sha256 `6a68012f…`) moved at the S102 close (run in S103)**, each asserted byte-identical on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S102 — Wednesday 2026-10-28 09:58 IST → Friday 10-30 11:05 IST** (closed in S103 Part A). Wednesday applied the S101
doc-close (`3abb83f`), read the NIFTY pin path across the expiry roll, and built and tested six engine bundles that were
**not applied**; Friday found that every Γ size on the board was shown at 100 × its "₹ Cr" label and fixed the display in
one morning — ADR-032 D1, seven `_1pct` wrapper views, two Lovable rounds, manual v0.5, promoted and read live at 11:02.
This block points; the detail lives in the files named. Rulings: `docs/research/s92_parity/rulings_s102.md` (S102-A…F;
the single source). Evidence and findings: `docs/research/s102/S102_close_inputs.md` (its stated record limit: the 10-28
transcript was compacted; figures not in a commit message are re-read, not reconstructed). **Progress lives in the
tracker**, `docs/registers/agentic_layer_roadmap_S90.md` (v2.19), and **its §2.2 is the single list** of open work.

**`origin/main` — `3abb83f` + this close.** No S102 engine code was pushed; the six 10-28 bundles (`s102r48` → `s102r40` →
`s102td8` → `s102fut` → `s102argv` → `s102mk`, each baselined on the previous one's post state) wait for the S90-J window.
Offline suite 25 steps on `main` (29 once the bundles land). Crontab unchanged (70 lines; `s102mk` carries the markers
line `40 10` → `0 11` UTC). **Marketview live = staging = `30998f2`** (bundle `index-EtZmieBR.js`, promoted 10-30 11:01
IST; rollback target `/var/www/marketview.bak-27c0e17` ≡ `f964e40` JS + manual v0.4, proven by `diff -rq`). Database: the
seven `_1pct` views and `v_market_ticks_eq_latest` (applied 10-28 for `s102r40`). ACL baseline re-measured 10-30 10:59
(`docs/lovable_prompts/s92/README.md`).

**What was established**

1. **The Γ unit (S102-A / S102-B, ADR-032).** Stored gamma exposure `γ·OI·S²/1e7` is the hedge for a **100 %** move; the
   conventional "₹ Cr per 1 % move" is × 0.01, and only `v_dealer_flow_sim.flow_cr` applied it. No decision reads the
   magnitude (sign, ratios and shares cancel a constant). **D1 RULED + LIVE:** the conversion is made once, in the
   database, by seven additive `security_invoker` wrapper views (`sql/2026-10-30_s102_gex_per_1pct_views.sql`, T1–T5
   PASS); stored columns, writers, source views, pins and the retail contract are untouched. **D2–D5 PROPOSED**, gated on
   the §5 impact study and §6 roadmap. Inventory v2: `docs/research/s102/gex_unit_inventory_S102.md`.
2. **Board (S102-C, S102-D; `docs/lovable_prompts/s102/`).** Round 1: seven files, 41 replacements, wording table W;
   round 2: the legacy pages **rescaled** (not retired), the "Σdmp …k" mislabel fixed. Each round guarded, staged, read
   against SQL at the same `ts` on both symbols, then promoted together with manual v0.5 as `30998f2`. Live read 11:02:
   SENSEX Net Γ `+595 Cr · long γ · 0.06 of gross · ₹ Cr per 1 % move`, Hedge per 1 % SELL 595 (= −Net Γ × 1 %).
3. **Manual v0.5 (S102-E).** 18 anchored edits on the engine source (`0f103a58…` → `e4872ab6…`), built on the box by
   `s102_manual_v05.sh`; text restated ÷ 100 with "(then shown as …)"; screenshots still on the old scale (option B owed).
   This close lands the same 18 edits in `docs/marketview_manual/` and points `build_help_pack.py` at `index-EtZmieBR.js`.
4. **Six engine bundles built and tested 10-28, none applied** (`S102_close_inputs.md` §2.2): R48 / R49 (`run_ingest.sh`
   END line carries the rc; offline step 26), R40 (breadth-from-ticks keyset-reads `v_market_ticks_eq_latest`: 1,313 rows
   in 407 ms against ~161,000 rows / 140–176 s; 379 of 431 runs over 60 s on 10-26/27), TD-S77-NEW-8 (the refresh ledger
   via `core.execution_log`; step 27), TD-S100-NEW-1 (futures basis against the index LTP from the same Dhan request;
   step 28), the futures writer scoped to its cron line's symbol (10-27: both lines wrote both symbols), and the session
   markers from the CAS-settled close with the cron moved 16:10 → 16:30 IST (`MISSING_CLOSE_1530` every session 10-12 →
   10-27; step 29).
5. **Pin path across the NIFTY expiry roll, part 2: PASS** (10-28) — the writer carries per `(symbol, expiry_date)`.
6. **Process.** One writer per change (Lovable or the box, never both — a 10:47 race dropped a box commit); the promote
   block checks live ≡ the named backup by `diff -rq` before naming a rollback target; rollback text only inside a
   refusing block and never in the same paste-ready message as the forward step (§D.56.13 — the operator pasted it and
   live reverted for about a minute).

**Filed:** TD-S102-NEW-1…8 — the Lovable-hosted public copy publishes `main` outside the guard; the help pack's
`board_bundle` stamp; screenshots on the old scale; the engine manual source behind the live pack (closed by this close);
two writers on one change (closed: the rule is in the s92 README); a file copied into the live tree outside a build; the
`market_ticks` duplicate index; `hist_gamma_metrics.net_gex`'s contradictory unit. TD-S100-NEW-3 gains the bare-"Cr"
note on `NarrativeModal`.

**Corrections to my own work:** Assumption Register **§D.56** (S102, 16 rows). The one to carry: read what is live before
naming a rollback target, and never print the rollback beside the forward step (D.56.12–13).

**ADR-032 filed (D1 RULED + LIVE; D2–D5 PROPOSED); settled line added (`CLAUDE.md` v1.74); rules 0–25 unchanged.** System
Map §S102; Deployment Topology §S102.

## NEXT SESSION PICKS UP

1. **The six 10-28 engine bundles** in their baseline order (r48 → r40 → td8 → fut → argv → mk): apply after 15:40 IST,
   push after 16:30 IST (S90-J); per bundle baseline sha, dry-run, apply, `ast.parse`, its offline step; the full suite
   (29 steps) once, out of hours, under `ulimit -v`; one commit per bundle; `s102mk` carries the live crontab edit, read
   back with `crontab -l`. Next-session live checks: the END line with rc on a failing ingest; breadth-from-ticks run time;
   the 09:05 refresh ledger row; futures rows one per symbol per minute with `raw.spot_source =
   dhan_ltp_idx_i_same_request` through 15:40; markers `close_1530` from CAS.
2. **R19 re-read (carried twice):** `breadth_indicators_daily` for 10-26 onward — expected = universe tickers with an
   `equity_eod` close that date; PASS = equal, `eod_pct ≥ 95`.
3. **Rulings owed, each raised with a recommendation from the code:** Health OVERALL token threshold; the NIFTY board after
   the expiry-day close; Context IV skew on a 0-DTE front leg; WCB from pre-open ticks; `held_for_cycles` across an expiry
   roll on the same strike; the 10-28 rulings 1–5, R16 freeze fix, R20 (a / b), TD-S97-NEW-4 (b); the Lovable-hosted public
   copy (unpublish or keep); manual option B timing; ADR-032 D2–D5 only after the §5 study and §6 roadmap.
4. **Then tracker §2.2 in its order** from where S102 stopped.

## OPERATOR RULINGS, S102

**All rulings live in `docs/research/s92_parity/rulings_s102.md`**, the single source.

| # | Topic |
|---|---|
| **S102-A** | Γ size: display-only rescale first (× 0.01 to ₹ Cr per 1 % move) |
| **S102-B** | ADR-032: D1 display now; D2–D5 after the impact study and roadmap |
| **S102-C** | D1 board wording table W approved; √τ (R26) not taken |
| **S102-D** | Legacy pages rescale, not retire |
| **S102-E** | Manual: text restated now (A), new screenshots later (B) |
| **S102-F** | Close S102; the doc-close runs in S103 |

## Previous session S101

**S101 — Sunday 2026-10-25 20:41 IST → Wednesday 10-28 09:58 IST** (doc-close `3abb83f`, run in S102). The engine's
pure compute packaged as `merdian_compute` and imported back by the writers (deployed `4a1d8e1` 10-26 17:08 IST, read live
10-27); contract v2.1; the live pin / accel zone views registered. The full block is in `docs/registers/CURRENT_history.md`.

## OPERATOR RULINGS, S101

**All rulings live in `docs/research/s92_parity/rulings_s101.md`**, the single source.

| # | Topic |
|---|---|
| **S101-A** | Core split: package the composed gamma cycle (C2) |
| **S101-B** | Deploy after the Part C reads; fast-forward, read-only check, written rollback |
| **S101-C** | Board-core gaps: ATM IV (C3), the pin path (C4), contract (C5) |
| **S101-D** | File the S101 findings as TDs at the close |
| **S101-E** | Register the live pin / accel zone views (C6, C7); live views by md5 |
| **S101-F** | Close TD-S97-NEW-4, TD-S82-NEW-1, -2; the `57014` exit a new TD |
| **S101-G** | Schedule the 10-27 close reads and R19 |
| **S101-H** | Close S101; the doc-close runs in S102 |
