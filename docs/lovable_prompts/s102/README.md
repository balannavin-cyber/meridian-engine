# S102 Lovable rounds — ADR-032 D1, Γ sizes in ₹ Cr per 1 % move (2026-10-30)

Record of the two rounds, the guards and the manual build. Rulings: `docs/research/s92_parity/rulings_s102.md`
(S102-A…E). Evidence in full: `docs/research/s102/S102_close_inputs.md` §2.3; the ADR's D1 record:
`docs/decisions/ADR-032-gex-stored-unit.md`. Inventory: `docs/research/s102/gex_unit_inventory_S102.md` v2.

| File | What |
|---|---|
| `lovable_prompt_s102_gamma_per_1pct.md` | Round 1 — board: 7 files, 41 replacements, data source → the seven `_1pct` views; wording table W (approved 08:43 IST, S102-C) |
| `mv_lovable_guard_s102.sh` | Round-1 guard (copy of the s92 guard v2: allowlist = the seven paths; reads only of the seven `_1pct` views; round fingerprint) |
| `lovable_prompt_s102b_legacy_per_1pct.md` | Round 2 — legacy pages (RESCALE, S102-D): `src/lib/queries.ts`, `src/marketview/sections.tsx`, 10 replacements; the "Σdmp …k" mislabel fixed |
| `mv_lovable_guard_s102b.sh` | Round-2 guard; sha256 `00767d959b36406dcc8ee12b4337e2fe4d9ef167b7c34076c06ff0d6dd7bab80` |
| `s102_manual_v05.sh` | Builds manual v0.5 (`manual.json` `ede04e14…4481`) from the engine source `0f103a58…` → `e4872ab6…` by the 18 anchored edits in its `edits_man.py`; sha256 `2fa161d34fdd39fbd27942128c71e2cf3e32e81082484a7fdb2fa948f5c41f79` |

## Chain (meridian-connect `main`)

Live before the rounds `f964e40` (bundle `index-BFOk56iL.js`, manual v0.4 copied into `/var/www/marketview/help/` after the
build, see the s92 README promote rule) → `27c0e17` (manual v0.4 in git) → `2f60ffe` / `f27aae5` round 1 on `lovable-sync` →
`8326ed0` merge PR #1 → `56539fd` / `3b3b0d4` round 2 → `7cba2cd` / `1171975` Σdmp wording → **`30998f2`** manual v0.5 (box
push). **Promoted 11:01 IST: live = staging = `30998f2`, bundle `index-EtZmieBR.js`; rollback target
`/var/www/marketview.bak-27c0e17`** (proven ≡ `f964e40` JS + manual v0.4 by `diff -rq` and the manual sha).

## Reads (PASS, operator's Chrome against SQL at the same `ts`)

- Round 1, 09:30 run, both symbols: strip Net Γ, Gross, ladder readout, Net Γ today, river hover, ∂Γ tiles, 3D peak; strip
  Net Γ = −(Hedge per 1 %) (T2's identity on the board).
- Round 2, ts 04:40:06 / 04:40:07 UTC: NIFTY Net Γ 1,569.67, Σdmp 35,741.83 / Σamp −34,172.16, pk 6,446.75 @ 23000, 104
  strikes, intraday max 10,159.25; SENSEX −256.05, 4,309.87 / −4,565.93, pk 525.42 @ 75000, 163 strikes, intraday 117.30 /
  −579.16. ∂Γ SENSEX chain 10:15: −101.77 / 652.95, −12.64 / 506.65 = staging −102 / 653, −13 / 507.
- Live 11:02 IST (SENSEX, chain 11:00): Net Γ `+595 Cr · long γ · 0.06 of gross · ₹ Cr per 1 % move`; Hedge per 1 % SELL
  595; ∂Γ −20 / 678, −92 / 567; legacy NET Γ +594.78 with the unit sub-line; manual v0.5 hash match; 0 "unit pending".

## Findings carried (filed at the S102 close)

TD-S102-NEW-1 (the Lovable-hosted public copy publishes `main` outside the guard), -2 (`board_bundle` stamp stale), -3
(screenshots on the old scale, option B owed), -5 (two writers raced one change — the one-writer rule is now in the s92
README), -6 (a file copied into the live tree outside a build; promote checks live ≡ named backup).
