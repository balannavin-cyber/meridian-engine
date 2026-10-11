# P7 — flow vs book for DEX, ∂Δ/∂σ and ∂Δ/∂t: design note (S96)

**Status: RULED — §7 D1–D7 as recommended, ruling S96-A (`docs/research/s92_parity/rulings_s96.md`). Nothing built, nothing applied. Next: the M-P7 pre-registration.**
Roadmap §2.1 P7 (v2.12): *Flow leg for DEX, ∂Δ/∂σ and ∂Δ/∂t (absorbs ENH-98 D-4)*. Unblocked S95
(P5 and P6 live). Proposed git home: `docs/research/s96_priority/p7/`.

Inputs read for this note (origin/main `ecd101f`): `sql/2026-10-11_s95_v_oi_since_preopen.sql`
(ENH-142), `sql/2026-10-09_s93_v_dex_standing_book.sql` (ENH-140), `sql/2026-10-03_s89_v_gex_greeks_l2.sql`
(ENH-98, L7/L8), `rulings_s92.md` (S92-C/E/I), `rulings_s94.md` (S94-G/I), `rulings_s95.md` (S95-B),
`parity_dovetail_and_post_parity_plan_S89.md` (D-4), TD-S95-NEW-1, the parity-target read
(`Ashwin_Badrinath_analysis_Mar-Oct2026.pdf`, items 5–6 and 9 of "the read", #456 #480 #522 #525 #533 #596).
No query was run for this note; every number below is quoted from those files.

---

## 1. What "flow vs book" means here

For any per-leg exposure `g_i` (a greek per contract, already scaled to Rs crore per unit of quantity):

- **book(t)** = Σᵢ gᵢ(t) · OIᵢ(t) — what the live views publish today (DEX: ENH-140; ∂Δ/∂σ, ∂Δ/∂t: ENH-98).
- **flow(t)** = Σᵢ gᵢ(t) · ΔOIᵢ(t), with ΔOIᵢ(t) = OIᵢ(t) − OIᵢ(anchor), anchor = the session's pre-open row (S95-B).
- **Identity, exact by construction:** book(t) − flow(t) = Σᵢ gᵢ(t) · OIᵢ(anchor). This is the check that
  binds the two to one clock (§6, C1).

"Flow vs book" is the comparison of the two, per construct, like for like: DEX flow against the DEX book,
∂Δ/∂σ flow against the ∂Δ/∂σ book, ∂Δ/∂t flow against the ∂Δ/∂t book. **Never across constructs** — the
DEX book is signed by each option's own delta (ENH-140), the second-order pair carries the PE negation of
`signed_gamma_exposure()` (ENH-98). Each flow inherits the sign convention of the book it is compared with,
so a flow sign is comparable with its own book and with nothing else on the board.

**What flow is not.**
1. **Not a dealer claim.** An OI delta cannot tell writing from buying (ENH-142 COMMENT); P2 returned
   regime-dependent. Every flow surface carries the book's P2 phrase.
2. **Not the four-case classification** (long build-up / short build-up / covering / unwinding from OI change
   vs price change). That is the parity target's *India ΔOI* method (#596) and what D-4 was written around,
   but "ΔOI × price four-case" was triaged **off this track** on 2026-10-09 (roadmap §2.1, last paragraph).
   P7 builds **unclassified** flow. §7 D3 asks how that discharges D-4.
3. **Not GEX flow.** The target's *"negative on standing, positive today → moves dampened"* (#456, #480) is a
   γ statement. P7's scope is DEX and the Δ-pair; γ × ΔOI is not in S92-I's wording.
4. **Not path-aware.** flow(t) values today's added contracts at **today's** greeks, not at the greeks when
   they were added. Snapshots give no fill path; this is a definition, stated, not a defect.

## 2. Clock — the one place this can go quietly wrong

| Input | Clock |
|---|---|
| `v_oi_since_preopen` (P5) | anchor = first front-expiry row of the session, < 09:15 IST; latest = **latest snapshot** (to 15:40) |
| `v_dex_standing_book` (P6) | **settled run** = last run ≤ 15:15 IST per leg (ENH-126 river rule) |
| `v_gex_greeks_l2_*` (L7/L8) | **latest** chain ts, both legs |

Mid-session the settled run *is* the latest run, so all three agree. **After 15:15 they do not**: the DEX book
holds at the 15:10 cycle while P5's `oi_latest` moves to 15:40. S95 already met this shape once (the S\* tile
measured from the chain spot while the header showed another clock's spot). So:

- **DEX flow** takes the **anchor OI** from P5 (`anchor_ts`, `ce_oi_anchor_qty`, `pe_oi_anchor_qty`) and the
  **OI and delta at the settled run** from the book (`oi_call`, `oi_put`, `delta_call`, `delta_put`,
  `settled_ts`). It does **not** use P5's `oi_latest` or `*_oi_delta_qty`. One implementation of each rule:
  the anchor rule stays in P5, the session/settled-run/gap rules stay in the book.
- **Second-order flow** is valued at the L7/L8 ts, against L7/L8's own book. After 15:15 the DEX pair and the
  Δ-pair therefore sit on different clocks on the Flows tab — **already true of the two books today**, not
  introduced by P7. Recorded, not fixed here (§7 D5).
- **Join guard:** P5 and the book must agree on `session_date` and front `expiry_date` per symbol; where they
  do not, **no row** (absence, ADR-023 D1), never a fallback.

## 3. P7a — DEX flow (no change to any live view)

Per front-leg strike, at the book's settled run:

```
ce_dex_flow_cr = delta_call · (oi_call − ce_oi_anchor_qty) · spot / 1e7
pe_dex_flow_cr = delta_put  · (oi_put  − pe_oi_anchor_qty) · spot / 1e7     -- no PE flip; delta carries its sign
net_dex_flow_cr = ce + pe, NULL if either side is NULL
```

Inherited exactly from the book (ENH-140), not re-decided:
- **NULL is a gap.** A side whose delta is a gap (`delta IS NULL OR (delta = 0 AND COALESCE(iv,0) = 0)`)
  publishes NULL flow; its ΔOI rides in `dOI_call_no_delta` / `dOI_put_no_delta`. The gap is ITM- and
  put-concentrated (SENSEX settled run: 51 PE rows / 7,722,860 units vs 3 CE / 4,100).
- **Leg totals are columns** (`leg_*_dex_flow_cr`, `leg_dOI_qty`, `leg_gap_dOI_qty`), window sums of the measured
  part, so the client never sums (S92-G).
- A strike on one side only (P5 presence `LATEST_ONLY` / `ANCHOR_ONLY`) has NULL ΔOI on that side — never 0.

Proposed object: **`v_dex_flow_vs_book`**, grain (symbol, expiry_date, strike), front leg only, plus the book's
leg totals beside the flow's so one read carries both sides of the comparison. ENH id at filing (next free:
ENH-143, to be confirmed against the register).

## 4. P7b — ∂Δ/∂σ and ∂Δ/∂t flow (needs a change to a BUILT layer)

L7/L8 publishes **strike aggregates** (`delta_drift_iv_cr_per_volpt`, `delta_drift_time_cr_per_day`) already
multiplied by OI, with no per-leg signed value. Flow needs the per-leg, per-contract derivative times ΔOI.
CE and PE do **not** share it in practice: q = 0 makes the closed form identical only at equal σ, and each
leg carries its own vendor IV and passes the deep-ITM guard on its own. So flow cannot be read off the strike
view.

**Option B1 (recommended):** factor L7/L8's leg CTE into a base view **`v_gex_greeks_l2_leg`** (per leg:
d1, d2, the two per-contract derivatives, spot scale, status; **no OI**), have `v_gex_greeks_l2_strike` read it
and multiply by OI exactly as now, and have the flow view read the same base and multiply by ΔOI. One
implementation of the greeks. This is **maintenance on a BUILT layer** (S95-D: parity not reopened), and its
gate is a comparing test (Rule 0, fourth clause): all four constructs, both legs, per strike, before vs after,
max abs diff ≤ 1e-9 Cr, `status` and `n_legs` identical — on the live run **and** on a golden day.
The `AS MATERIALIZED` gate CTE (164 ms vs 26 s) must survive the split; EXPLAIN as anon re-measured twice.

**Option B2 (not recommended):** copy L7/L8's leg arithmetic into the flow view. Two implementations of one
rule — exactly what S92-G retired for L13.

**Limits P7b inherits:**
- **dte 0 is SKIPPED in L7/L8** (status `SKIPPED_EXPIRY`), and P5 is **front expiry only** (S95-B). So on each
  symbol's expiry day (NIFTY Tue, SENSEX Thu) the front leg has no second-order flow at all. W2 has a book but
  no anchor. Fixing that means extending P5 to W2 — an amendment to S95-B (§7 D4).
- The Δ-pair's net is meaningfully signed (|net|/gross 0.844–1.000 for ∂Δ/∂σ; 0.957–1.000 for ∂Δ/∂t on 7 of 8
  arms, 0.181 on SENSEX dte 2 — ENH-98 COMMENT). Those are **book** ratios; nothing is known yet of the flow's.

## 5. Data defects flow inherits

1. **Vendor OI on untraded legs (TD-S95-NEW-1).** From 09:15 no untraded leg changed OI on any of 22
   symbol-sessions, so flow is clean after the open. Before 09:15 the latest row **is** a pre-open row: a
   non-zero flow then is a vendor revision before any trade, not flow. Proposal: a `flow_window` column —
   `PRE_OPEN` while the settled run is stamped < 09:15, `SESSION` after — and the board shows flow only in
   `SESSION`. A non-zero ΔOI on a leg with volume 0 is the other tell; neither P5 nor the book exposes
   volume, so flagging it is tied to TD-S95-NEW-1 (c) (§7 D6).
2. **Vendor delta.** Put–call delta parity fails in the data (Δ_CE − Δ_PE 0.577–1.281 against 1), and the
   parity-implied put delta moves the **book** net by 1.6–2.9× (sign unchanged on four legs of one run). The
   flow inherits this; the badge rule in §6 is built on it.
3. **Thin early flow.** The target's own caveat (#533): classification "runs on almost nothing" before ~10:00.
   We have no measurement of our own. Not a rule yet — §6 M-P7 measures it.

## 6. The SAME / OPPOSITE read, and what has to be measured before it ships

The target ranks *"today's flow vs the standing book"* highest and reads opposite signs as *the day pushing
against the position* (#522, #525). Our net DEX is a near-cancellation (|net|/gross 9.2 % NIFTY W1, 21.4 %
SENSEX W1, ENH-140) and its magnitude is "indicative, not measured". A sign badge on a cancellation residue is
the ENH-131 Gate 2 shape. So **the badge does not ship on a sign test alone.**

**Proposed abstain rule, derived from the known defect, stated before any measurement:** for DEX, compute the
flow net and the book net under **both** delta sets (vendor, and parity-implied put delta); the badge shows
SAME or OPPOSITE only when **all four signs are robust** — each net keeps its sign across the two delta sets.
Otherwise it shows nothing. The threshold is not a number chosen by eye: it is the measured error of the input.
For the Δ-pair the analogue is the T-convention sweep already in ENH-98 (exact/365 vs dte/365), since T is what
moves those nets (2.4× on SENSEX dte 2) and r does not.

**M-P7 — pre-registered measurement, before the badge is built** (RO, through `roq.sh`, out of the live path):
over every session in retention (from 2026-08-24), front leg, both symbols, every cycle ≥ 09:15:
(a) flow |net|/gross distribution, (b) share of cycles where the abstain rule abstains, (c) cycle-to-cycle sign
persistence of flow net, by time bucket (pre-10:00 / mid / post-14:30). Pre-registered and hashed before the
first query, like P1/P2/P1c. It reports; it does not tune the rule. If the abstain rule abstains on most
cycles, that is the finding and the badge is DECLINED-ON-EVIDENCE, with flow still shown as numbers.

Board wording — every word below changes how you read the board, so **none of it goes live without your yes**:
- flow figures labelled *"flow since pre-open"* with the anchor time, and the book's P2 phrase;
- the badge words SAME / OPPOSITE, and no gloss (no "covering", "exhaustion", "dampened") — those are
  classification and γ claims P7 does not make;
- `PRE_OPEN` flow not drawn; a *"since 09:15"* note beside the first reads of the day.

## 6a. Checks (Section 4 of each SQL file), each with what makes it fail

| # | Check | Fails when |
|---|---|---|
| C1 | `book − flow = Σ g · OI_anchor`, recomputed from the chain at the settled run, max abs diff ≤ 1e-9 Cr | flow and book are on different clocks, or ΔOI is joined to the wrong strike/leg |
| C2 | P5 and book agree on session and front expiry per symbol; disagreeing symbols return 0 rows | the join falls back instead of going absent |
| C3 | Live at ~09:05 Monday: `flow_window = PRE_OPEN`; after the first ≥ 09:15 run, `SESSION` | the window flag follows the clock instead of the run |
| C4 | Mutant: one leg's delta nulled → that strike's net flow NULL and its ΔOI in the gap column | a gap is netted as zero |
| C5 | (P7b) L7/L8 before vs after the base-view split: four constructs × both legs ≤ 1e-9 Cr; status identical | the refactor changes a BUILT layer |
| C6 | anon EXPLAIN ANALYZE twice, under the 3 s anon ceiling (MV-6) | the new view joins two latest-scoped views into a heap scan |

Every check run on the live views at real volume (862-row book), not only on a fixture (§D.49.7).

## 7. Decisions owed (recommendation first)

| # | Decision | Recommendation |
|---|---|---|
| D1 | Split P7 into **P7a** (DEX flow, two live views, no live view changed) and **P7b** (Δ-pair flow, base-view refactor of L7/L8) | **Yes.** P7a carries no change to a BUILT layer and can be measured first |
| D2 | P7b method | **B1** (base view, one implementation), gated by C5 |
| D3 | D-4 was ruled as *classified* flow. Does unclassified flow discharge it? | **No — amend the L7/L8 badge, don't retire it**: *"flow-vs-book shown on unclassified ΔOI; classification (D-4) not built"*. Retire only if you rule the four-case off D-4 for good. Board wording → your yes |
| D4 | Extend P5 to W2 so the Δ-pair has flow on expiry days | **Not now.** Ship with SKIPPED on the front leg's expiry day; revisit after M-P7 |
| D5 | After-15:15 clock split between the DEX pair (settled) and the Δ-pair (latest) | **Record, don't fix in P7.** It predates P7 and touches L7/L8 semantics |
| D6 | Flag ΔOI on volume-0 legs | **Fold into your TD-S95-NEW-1 call** — it needs volume exposed by P5 or the book, a definition change to a live view |
| D7 | The SAME/OPPOSITE badge | **Only after M-P7**, with the defect-derived abstain rule of §6; flow numbers can ship before it |

## 8. Order once you have ruled

1. M-P7 pre-registration (hash before the first query).
2. P7a SQL authored; body costed through `roq.sh`; Sections 1–3 as one operator apply ending in its own
   verification SELECT (TD-S94-NEW-3); Section 4 one statement at a time.
3. M-P7 scored → badge decision.
4. Lovable round under the S92 guard (one named view), fingerprint against the S96 baseline before and after;
   `/staging/` read against SQL **in market hours**; promote with a backup.
5. P7b: base view, C5 on a golden day and live, then the flow view, then its board round.

Risk class: views only → S90-J "anything else", deploys any time; the board change is the LIVE part.
Never label second-order terms vanna or charm; γ lower case.
