# R2.4 — Parity fixtures from the reference's own screenshots, scored per field (S92)

| | |
|---|---|
| Roadmap item | **R2.4** (agentic_layer_roadmap_S90 Stage 2) — *inside parity* by ruling **S92-A** |
| Governs | ADR-025 **D3** (the reference binds; deviation needs a stated reason) · **C1** (scores are **reported, not a BUILT gate**) |
| Date | 2026-10-09 (Session 92) |
| Status | **REPORTED** — 40 fixtures, 199 field scores |
| Files (this folder) | `inventory_65.json` · `fixtures_40.json` · `blind_read_verify.jsonl` · `r24_score_fixtures.sql` (+ `r24_score_rerun3.sql`) · `meridian_asof.json` · `score.py` · `scores.csv` |

**The images are not committed.** They are the reference author's own posts. Each fixture cites its
file name in the operator's archive `ashwinbadri2_images_Mar-Oct2026.zip` (on the operator's PC,
`Downloads/Badri analysis with images/`), which is where they can be re-read.

---

## 1. What a fixture is

A screenshot of the reference dashboard that (a) shows at least one number MERIDIAN also computes,
(b) has a known symbol, and (c) falls where MERIDIAN holds per-strike data
(`gex_strike_snapshots`, from 2026-05-25). Each fixture carries:

- **reference values**, read verbatim off the image;
- an **anchor time**: the time printed on the screen if there is one; otherwise the post time, capped
  at 15:30 IST for posts after the close; a weekend post anchors on the previous session's close;
- **MERIDIAN's values as of that anchor**, from MERIDIAN's own rules replayed on stored runs.

## 2. Inventory

| | count |
|---|---|
| Images in the archive (2 Mar – 2 Oct 2026) | 316 (307 jpg, 3 png, 5 mp4, 1 manifest) |
| Read (posted on or after 27 Apr, the dashboard's first appearance) | **225** |
| Dashboard screenshots among them | **65** (`inventory_65.json`) — the rest: 63 payoffs, 44 broker positions, 16 price charts, 18 text/tables, 19 other |
| **Scoreable fixtures** | **40** — NIFTY 36, SENSEX 4 (`fixtures_40.json`) |
| Not scoreable | 25: 13 before 2026-05-25 (MERIDIAN holds only `gamma_metrics` there), the rest landing page, changelog, OI tapes, a delta-only screen, or no comparable field |

**Reference values were read twice, blind.** Two independent passes, neither seeing the other's
output: **186 of 199 values identical**; the other 13 were formatting (list separators) except three
pin-tab top-5 lists where the passes took different columns (pressure vs gamma — **the strike order
agrees**, and only strikes are scored) and two values the second pass could not read (F38 top-5,
F55 runner-up), which are kept and marked unverified in `blind_read_verify.jsonl`.

**Anchors corrected by hand (4).** F52 and F61 (the parser took the session-open stamp, not the tick
time); F37 and F41 (the date on the HHI tab is the end of its history axis, not the read time — the
reference's own DTE puts them on the post day); F26 (posted Saturday 18 Jul → Friday's close). F26,
F37 and F41 were re-queried (`r24_score_rerun3.sql`).

## 3. How MERIDIAN's side is computed

The live views return the latest run only (ENH-134 as-of functions are not built), and
`gex_cycle_history` starts 2026-10-05, after every fixture. So `r24_score_fixtures.sql` **replays
MERIDIAN's own rules as of each anchor**, read-only:

| field | MERIDIAN as of the anchor | rule it replays |
|---|---|---|
| spot, net GEX (Cr), regime, flip, DTE | `gamma_metrics`, latest run ≤ anchor, same IST date | — |
| leader (pin), runner-up, top-5, top-1 share | `gex_strike_snapshots`, latest run ≤ anchor, front expiry; rank by \|gex_cr\| | `v_gex_strike_rank` |
| HHI | Σ share², share = \|gex_cr\| / Σ\|gex_cr\| over the run's strikes | `gex_cycle_history.conc_hhi` |
| ± gamma peaks | max / min `gex_cr` strike | — |
| call / put wall | OI argmax within band·σ, σ from the latest ATM IV ≤ run | `v_gex_strike_walls` (**current** band params, not as-of — R0.6 `parameter_as_of` not used) |

**Flip is the legacy construct.** Before 2026-10-05 only `gamma_metrics.flip_level` exists — the
construct L3 *declined* and replaced with `v_gex_repriced_flip` (ENH-131). It is scored here because
it is all the history holds; it is **not** the flip the board shows.

## 4. Scores (reported, not gating — ADR-025 C1)

| field | n | result |
|---|---:|---|
| DTE | 19 | **19 match** |
| Spot | 26 | **23 within 0.1 %**; 3 differ by ~150 pts — F32/F33 (HHI tab read after the 4 Aug close) and F49 (SENSEX 10 Sep, opening tick 09:18) |
| Pin strike vs MERIDIAN leader | 26 | **11 exact**, 9 more inside MERIDIAN's top 5, 6 outside |
| Top-5 strike set | 12 | overlap 4/5 ×3, 3/5 ×7, 1/5 ×1, 2/2 ×1 |
| Runner-up | 9 | 2 exact, 5 inside MERIDIAN's top 5, 2 outside |
| Net GEX — sign | 21 | **17 agree** (incl. 3 "net dealer gamma"), 4 disagree; 2 no MERIDIAN `gamma_metrics` row (May) |
| Net GEX — magnitude | — | **reported only** (unit definition E-D1 open): same order of magnitude, ref/MERIDIAN ratio 0.06–3.6 |
| Regime | 11 | 8 match, 3 differ — the same three fixtures as the sign disagreements (F50, F54, F55) |
| Call wall / put wall | 8 / 9 | 4 / 4 exact; misses 50–500 pts |
| ± gamma peaks | 8 | 1 exact; 3 consistent with a swapped sign; 4 neither |
| HHI | 10 | reported: reference/MERIDIAN ratio **1.42–3.42, median 2.09** |
| Top-5 share | 7 | reference higher **every time** (54–95 % vs 40.5–82.9 %) |
| Flip (vs legacy `flip_level`) | 17 | 7 reference shows none; 10 differ, **reference always lower**, by 64–2,461 pts (median 407) |

Per-field detail for every fixture: `scores.csv`.

## 5. Findings

1. **The pin is mostly the same place.** In 20 of 26 the reference's pin strike is MERIDIAN's leader or
   inside MERIDIAN's top 5, and the top-5 sets mostly share three or four strikes. Where they part
   (6), the reference's pin from August is ranked on *pressure* (an undisclosed formula, study #558)
   while MERIDIAN ranks on \|gamma\| — the study already notes the two "invert". A pressure leg was
   declined on evidence (D-5a); this is that D3 deviation showing in the scores, not a new one.
2. **Concentration runs about 2× hotter in the reference** (HHI median ratio 2.09; top-1 and top-5
   shares likewise higher every time). The strike sets agree, so the difference is in the
   **denominator**: the reference's screens state a window ("74 STRIKES · ATM ± 36") while MERIDIAN
   divides by every strike in the run. MERIDIAN's labels are numbers only (no band), so nothing on
   the board is mislabelled by this; any future HHI band must be set on MERIDIAN's own scale, not
   borrowed from the reference's 0.10 / 0.25 thresholds.
3. **Net GEX sign agrees 17 of 21; magnitudes are on the same scale but not comparable yet.** The four
   sign disagreements (F32 4 Aug close, F50 16 Sep close, F54/F55 21 Sep 11:30) are small reference
   values (|ref| ≤ 1.63L Cr) or a near-zero MERIDIAN value (F50: +0.04L Cr) — i.e. close to the flip.
   Magnitude stays unscored until E-D1 defines MERIDIAN's unit.
4. **The ± gamma peaks do not reduce to one sign flip.** Three of eight read as swapped (all in
   September), one matches directly, four match neither. The study records a put-GEX sign change in
   the reference between 15 and 21 Jul; that does not explain the August cases. Left open, n = 8.
5. **Flip cannot be scored fairly on this history.** The reference flip is always below MERIDIAN's
   legacy `flip_level`, by a median 407 pts — consistent with the S78 audit that declined
   `flip_level` (branches on opposite sides of spot, steps up to 1,330 pts). The board's flip (L3,
   repriced) has history only from 2026-10-05 (`gex_cycle_history.repriced_flip_level`); **no fixture
   falls after that date**, so the L3 comparison waits for new screenshots.
6. **Walls agree half the time (8 of 17).** Misses are 50–500 pts, in both directions. MERIDIAN's wall
   is OI argmax inside band·σ with **today's** band parameters; the reference's definition is not
   published. Not investigated further.

## 6. Limits

- **n = 40, one author, mostly NIFTY (36).** SENSEX has four fixtures.
- **Anchors are approximate** where the screen prints no time: a post can follow its screenshot by
  minutes; MERIDIAN's run can precede the anchor by up to 5 minutes (one cycle).
- **MERIDIAN's side is a replay, not the stored output** of the live views (they are latest-only). The
  replay uses the views' rules; for walls it uses current parameters.
- **No tolerance is a gate.** ADR-025 C1: any tolerance that turns a score into a BUILT condition
  needs its own ruling. None is proposed here.

## 7. How to extend

New screenshots after 2026-10-05 can be scored against stored outputs directly
(`gex_cycle_history`: pin, conviction, held-for, HHI, walls, repriced flip) instead of a replay —
which is what makes the L3 and L12 pin-state comparisons possible. Add rows to `fixtures_40.json`,
re-run the SQL with the new VALUES, then `python3 score.py`.
