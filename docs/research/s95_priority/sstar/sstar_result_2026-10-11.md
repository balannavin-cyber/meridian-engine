# S\* — the re-priced zero-Δ level: RESULT (S95, 2026-10-11)

**Verdict: APPLY** — scored exactly as pre-registered. Pre-registration `sstar_prereg_2026-10-11.md`,
git hash-object **`7bfafb49`**, commit **`90c8c50`**, committed before the first real export. Nothing in
it was changed after the export. Ruling basis S94-H. Roadmap §2.1 P6.

## 1. What ran

`sstar_gates.py --emit-sql` → 15 read-only files through `bin/roq.sh` (merdian_ro), 2026-10-11 ~12:58
IST, into `~/sstar_data/` on the box (local only, `.gitignore:43`). `sstar_gates.py --score` → exit 0.

| export | rows | sha256 (12) |
|---|---|---|
| arms_resolved.csv | 11 | `f73e9f3adc25` |
| calendar.csv | 55 | `8d1dedbf3d81` |
| chain.csv | 8,784 | `3fcec45d4864` |
| futures.csv | 822 | `0feb710c5874` |
| view_asof_01 … _11.csv | 1 each | `846352f08ede` `4da4a0164194` `261e89068dab` `ccbc24047ad0` `946ccf55ea72` `d0753fcfc857` `8fa2707c09c1` `8ee5b9f911d1` `9a2807a63e6d` `7b355db1a604` `7f0eb0975c04` |

## 2. Gates

| gate | result |
|---|---|
| **G1** view body (as-of) = independent Python | **PASS on all 11 arms**, incl. the dte-0 control refused on both sides |
| **G3** structure | **PASS** — strictly increasing, ≤ 1 crossing, neg→pos, every scorable arm × 9 variants |
| **G4** r band at T(b), ≤ 0.25 σ₁d | **PASS** — 0.005 to 0.164 σ₁d |
| **G5** L3 Gate 5 re-run, r band × T(a,b,c), ≤ 0.25 σ₁d | **PASS** — 0.027 to **0.239** σ₁d |
| mutants M1–M5 | **all caught** by their assigned gates |
| scorable arms (≥ 6 required) | **7 of 10** |

Per arm (descriptive, from `~/sstar_spreads.out`, computed after the verdict from the committed harness
functions; it does not and cannot change the verdict):

| arm | dte | σ₁d | S\* − spot (σ) | G4 (σ) | G5 (σ) | T(c)/T(b) | r p10 / sess / p90 | n_r |
|---|---|---|---|---|---|---|---|---|
| L3-E SENSEX 09-22 12:00 | 2 | 463.7 | +0.013 | 0.1109 | 0.1709 | 1.35 | −0.0120 / 0.0436 / 0.1051 | 45 |
| L3-C SENSEX 09-23 15:40 | 1 | 416.9 | +0.063 | 0.1636 | **0.2386** | 1.46 | −0.1126 / 0.0392 / 0.2222 | 149 |
| OOS NIFTY 10-07 12:00 | 6 | 145.7 | +0.091 | 0.0303 | 0.0310 | 0.94 | 0.0373 / 0.0428 / 0.0489 | 61 |
| OOS SENSEX 10-07 12:00 | 1 | 606.2 | +0.009 | 0.0052 | 0.0334 | 1.26 | 0.0559 / 0.0647 / 0.0695 | 61 |
| OOS NIFTY 10-08 12:00 | 5 | 152.3 | +0.304 | 0.0305 | 0.0891 | 0.84 | 0.0339 / 0.0428 / 0.0487 | 61 |
| OOS NIFTY 10-09 12:00 | 4 | 148.6 | +0.315 | 0.0271 | 0.0273 | 0.70 | 0.0600 / 0.0693 / 0.0758 | 61 |
| OOS SENSEX 10-09 12:00 | 6 | 533.3 | +0.456 | 0.0324 | 0.0330 | 0.94 | 0.0645 / 0.0723 / 0.0786 | 61 |
| L3-F NIFTY 09-18 · L3-D NIFTY 09-23 · L3-A NIFTY 09-24 | 4 · 6 · 5 | — | not scored: T(c) unmeasurable | | | | | |

## 3. What the record must say (all in the view COMMENT)

1. **Margin.** L3-C (SENSEX, 1 dte) used **95 %** of the G5 tolerance — the widest r band of any arm and
   the largest T(c)/T(b). Both 1-dte arms carry the largest spreads. S\* on 1-dte SENSEX is the least
   stable reading the view publishes.
2. **Only 2 of L3's 5 arms were re-scored.** The three NIFTY L3 arms span September weekends with no
   `trading_calendar` row; October weekends have rows (the S90 seeder writes closed days). The
   pre-registered rule made T(c) unmeasurable — ADR-020, absence is not a verdict — rather than inferring
   sessions. The scoring rests mostly on the five out-of-sample arms.
3. **G2 (descriptive).** S\* sat **above spot on all 7** arms, +0.009 to +0.456 σ₁d, with the repriced
   net at spot negative throughout. The repriced book and the **vendor-delta** book — the one on the
   board — **disagreed in sign at spot on 2 of 7** (L3-E −477 vs +2,069 Cr; OOS NIFTY 10-07 −4,046 vs
   +621 Cr). A reader can see Net DEX and the side of S\* point opposite ways on such a day. Neither is a
   dealer claim.

## 4. What this does NOT show

S\* is a **level computed from today's book**, not a forecast: nothing here tests whether price moves
toward it or away from it. Seven arms on five sessions. The curve's magnitude stays indicative (vendor iv,
sticky strike); the level is what is published.

## 5. Corrections to my own work, before and during the run

- The local test found mutant M1 (L3's PE flip copied) **uncaught by G3** — a flipped book can stay
  monotone with no zero. Reassigned to G1, with M5 (d1 negated) added for G3, **before** the commit.
- The first commit attempt failed: `.gitignore:43 *.csv` silently skipped `arms.csv` (TD-S93-NEW-2).
  Fixed with one negation line, never `add -f`.
- The availability probe resolved arm ts *at or before* the label (11:55 for 12:00); the pre-registration
  states the rule actually used (`[label, label + 5 min)`).
