# ADR-032 — Gamma exposure is stated in ₹ Cr per 1 % move: display now, storage after an impact study

| Field | Value |
|---|---|
| Status | **D1 RULED + LIVE; D2–D5 PROPOSED.** D1 **RULED** by the operator 2026-10-30 ("1 first", S102-A / S102-B) and **LIVE 2026-10-30 11:02 IST** (Marketview `30998f2`, bundle `index-EtZmieBR.js`; record below). **D2–D5 PROPOSED — not to be implemented** until the impact study (§5) and the change roadmap (§6) are written, reviewed and ruled, and every step has passed its test before it reaches the board. Filed into `docs/decisions/` at the S102 doc-close (run in Session 103) from the S102 draft, header changed from PROPOSED to this line and the inventory link repointed; nothing else rewritten. |
| Date | 2026-10-30 |
| Session | S102 |
| Supersedes | nothing. **Reopens** the CLAUDE.md settled item "TD-NEW-2 + TD-NEW-3 P0 verification PASS" (S28) only as to the *unit* it names ("net_gex in Crore range"); the S28 fix itself stands |
| Superseded by | nothing |
| Parent | **ADR-025** C8 / S100-R C (Γ = aggregate exposure); **S92-G / S92-J** (one rule, in the database) |
| Register entries | E-1 / E-D1 (unit definition pending); R26 (√τ normalisation, parked); TD-NEW-3 (S28); TD-S101-NEW-5 (gamma math outside `merdian_compute`) |
| Bound inventory | [`docs/research/s102/gex_unit_inventory_S102.md`](../research/s102/gex_unit_inventory_S102.md) v2. **The inventory is not restated here.** |
| DDL (D1) | `sql/2026-10-30_s102_gex_per_1pct_views.sql` — **applied 2026-10-30** (operator); T1–T5 PASS |
| Board (D1) | `docs/lovable_prompts/s102/lovable_prompt_s102_gamma_per_1pct.md` (round 1, board) and `lovable_prompt_s102b_legacy_per_1pct.md` (round 2, legacy pages) — **landed, staged, read against SQL, promoted** |

---

## Context

MERIDIAN stores gamma exposure as `γ · OI · S² / 1e7` (`merdian_compute/gamma.py:54`, TD-NEW-3, S28: "store in Crore"). OI is
lot-inclusive quantity. The conventional figure — ₹ of delta-notional dealers re-hedge **per 1 % move** — carries a further
`× 0.01`; the stored number is the hedge for a 100 % move, so every Γ size on the board ("+3.3L Cr") is **100 ×** the figure its
"₹ Cr" label implies ("~3,300 Cr per 1 %"). Measured S97 (F1, `claude/parity_eval/03_findings.md`): one strike recomputed by hand
equals the stored value; converted with × 0.01 (and the target's √(τ/5 d)), SENSEX net 3,709 against the parity target's 3,417.

**Nothing that decides anything reads the magnitude** — regime, flip side and the pin-risk base read the sign; concentration, HHI,
shares, net/gross, runner-up ratio and pin/accel τ × peak are ratios, and a constant factor cancels (inventory §1). One reader
compensates already: `v_dealer_flow_sim.flow_cr = −net_gex × pct` is per-1 % at ±1 %. **The defect is one of meaning, and it
reaches every reader who takes `gex_cr` as rupees.**

## D1 — Display first, in the database, without touching what is stored (RULED 2026-10-30)

**Decision.** The board states every Γ size in **₹ Cr per 1 % move**. The conversion `× 0.01` is made **once, in the database**,
by thin wrapper views named `<source>_1pct` that add `<column>_1pct = <column> × 0.01` beside every original column. No stored
column, writer, existing view, test pin, replay hash or the retail contract changes.

**Why wrappers and not `CREATE OR REPLACE` of the source views.** Five source views have no md5-registered live definition
(rule 25; inventory §4): rewriting them from `sql/` risks reverting an unregistered live change, the S101 C6 / C7 failure. A
wrapper reads whatever is live, is additive, and drops cleanly. **`security_invoker = true`**, so a wrapper grants nothing a reader
did not already have.

**Not rescaled:** `flow_cr` (already per-1 %) and every delta-type column (DEX, ∂Δ/∂t, ∂Δ/∂σ — scale `oi · S / 1e7`, true ₹ Cr).
The board's `crLakh` formatter is shared with DEX and is **not** changed; the scale enters through the data only.

**Dependency.** Each wrapper depends on its source: a `DROP VIEW` of a source now errors, and `CREATE OR REPLACE` of a source
may only append columns. A later change to a source drops and re-creates its wrapper in the same batch. None of the six bundles
queued 2026-10-28 (R48, R40, TD8, futures spot, argv, markers) touches any of the seven sources (read 2026-10-30). The retail
ENGINE-REF pin covers none of them, so D1 needs no retail re-pin.

**Gate.** Views applied and verified (tests T1–T5 in the DDL file; T5 reads every wrapper as `anon`) before the Lovable round; the round staged and every surface of
inventory §3A / §3B read in Chrome against SQL at the same `ts` before promote. Legacy pages (inventory A9–A10) rescale or retire
in a second round; **ruled RESCALE 2026-10-30 09:43 IST** and done before promote, so one app never shows two scales of Net γ.

## D2 — The stored unit becomes ₹ Cr per 1 % move (PROPOSED)

Every gamma-exposure column — `gex_strike_snapshots.gex_cr`, `gamma_metrics.net_gex`, `gex_cycle_history.net_gex` /
`gamma_at_pin`, `gex_pin_maxpain_history.peak_pin_gex_cr`, the copies in `market_state_snapshots`, `signal_snapshots`,
`structural_divergence_snapshots`, `merdian_compute`'s return values, and the gamma pair of `v_gex_greeks_l2_*` — is written as
`γ · OI · S² · 0.01 / 1e7`.

## D3 — History: convert in place or a dated unit break (PROPOSED; the study chooses)

Either every historical row is converted, or the change is dated and registered (Rule 13 style) so every study spanning it
scales across the boundary. The choice is recorded as an amendment **before any write**.

## D4 — Units are stated where the value lives (PROPOSED)

Each Γ column carries its unit in a `COMMENT`; `merdian_compute` docstrings and contract §2 state it; the System Map records it.

## D5 — Out of scope

√(τ / 5 d) normalisation (R26): if ever adopted, a separate additional column under its own decision.

## Consequences

- **D1:** seven new views (additive, droppable); one Lovable round; manual v0.4 restated (inventory §3D). The board's numbers fall
  by 100× and gain a unit; sign, ratios and every decision are unchanged. After D1, the board and `flow_cr` agree by construction.
- **D2–D3 (if ruled):** the wrappers of D1 become identity and are retired; `merdian_compute` contract v3 and a retail re-pin;
  step 25 pins and S101 golden hashes regenerated; replays re-baselined; a writer change in the S90-J window.

## §5 — Impact study (owed before D2 / D3)

Every reader and writer of a Γ size, found by code search **and** by a live `pg_depend` / `pg_get_viewdef` read (rule 25), each
with: what it does with the value (magnitude / sign / ratio / compensating), the change it needs, its test, and its owner (engine,
board, retail, research). Must also settle the inventory's §5 questions: `hist_gamma_metrics`' contradictory unit, any surviving
pre-TD-NEW-3 `gamma_metrics` rows, the OI unit of `backfill_gamma_metrics_to_main.py`'s source, and the volume / time of an
in-place conversion of `gex_strike_snapshots` against a dated break.

## §6 — Change roadmap (owed; least-impact order to be ruled)

Indicatively: (1) D1, done first; (2) writers write a new per-1 % column beside the old, both kept; (3) every reader moves to the
new column, each tested; (4) history per D3; (5) the old columns and the D1 wrappers retire after a stated quiet period. Each step:
offline test with a mutant, replay before vs after, `/staging/` read before the board, written rollback, S90-J window where a
writer changes.

## D1 record (2026-10-30)

| Step | Evidence |
|---|---|
| Views | 7 `_1pct` wrappers applied; T1 (all 7 wrappers, rerun 10:22 IST with ∂Γ rows: `bad`, `same_as_x1`, `same_as_x01`, `null_mismatch` all 0; `n_rows` 4–1,856), T2 (`net_gex_1pct = −flow_cr` at +1 %), T3, T4 privileges, T5 anon read: PASS |
| Round 1 (board, 7 files, 41 replacements) | wording table W approved 08:43 IST; Lovable `f27aae5`, merged PR #1 `8326ed0`; guard `mv_lovable_guard_s102.sh` PASS; staging read vs SQL at the 09:30 run, both symbols: PASS |
| Legacy ruling | RESCALE, operator 09:43 IST |
| Round 2 (legacy, 2 files, 10 replacements) | Lovable `56539fd`/`3b3b0d4`; Σdmp wording `7cba2cd`/`1171975`; guard `mv_lovable_guard_s102b.sh` (sha256 `00767d95…ab80`) PASS twice; staging vs SQL: NIFTY ts 04:40:06 UTC (Net Γ 1,569.67; Σdmp 35,741.83 / Σamp −34,172.16; pk 6,446.75; 104 strikes; intraday max 10,159.25) and SENSEX ts 04:40:07 (−256.05; 4,309.87 / −4,565.93; pk 525.42 @ 75,000; 163 strikes; intraday 117.30 / −579.16): PASS; ∂Γ SENSEX chain 10:15 (−101.77 / 652.95; −12.64 / 506.65 = staging −102 / 653, −13 / 507): PASS |
| Manual | operator "So lets go" 10:20 IST on options A/B/C, taken as **A** (text restated, screenshots later): manual v0.5, 18 anchored edits on engine `3abb83f`, built on the box (`s102_manual_v05.sh` `2fa161d3…`), `manual.json` `ede04e14…4481`, commit `30998f2` (box push) |
| ACL fingerprint 10:59 IST | `anon_writable_objs 0`; `default_privileges 27 9db86164…`; `schemas 10 2a889318…`; `anon_role c506ff14…`; `public_functions 41 ef1d66a1…`; new baseline `relations 358 830967b5…`, `anon_public_privs 263 1f238394…`, `rls_policies 80 be718afb…` |
| Promote 11:01 IST | live `30998f2`, `index-EtZmieBR.js`; rollback target `/var/www/marketview.bak-27c0e17` (= `f964e40` JS + manual v0.4, `489a135e…`); `.bak-3366bf1` removed (S100-L) |
| Live read 11:02 IST (SENSEX, chain 11:00) | board Net Γ +595 Cr `long γ · 0.06 of gross · ₹ Cr per 1 % move`; Hedge per 1 % SELL 595; ∂Γ −20 / 678, −92 / 567; legacy NET Γ +594.78 with unit sub-line; Σdmp line with unit; manual v0.5 hash match; 0 "unit pending" |

## Governance language

When D1 is applied and read live, CLAUDE.md gains a settled-decisions line: *"Γ sizes on the board are ₹ Cr per 1 % move, made by
the `_1pct` wrapper views; stored columns remain γ·OI·S²/1e7 until ADR-032 D2 is ruled."* D2–D5 add no CLAUDE.md text until ruled.
