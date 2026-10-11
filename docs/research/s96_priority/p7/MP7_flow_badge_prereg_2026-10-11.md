# M-P7 — can a DEX flow-vs-book badge speak under the defect-derived abstain rule? Pre-registration

| Field | Value |
|---|---|
| **Status** | **PRE-REGISTERED on commit**, together with `mp7/`, **before** any `mp7/*.sql` runs against the database. Its `git hash-object` is recorded in the result doc. |
| **Track item** | Roadmap §2.1 **P7**, sub-item P7a (ruling **S96-A**, D1 and D7). Risk class **RO** (`bin/roq.sh`, `merdian_ro`). |
| **Design** | `P7_flow_vs_book_design_note_2026-10-11.md` §6, ruled as recommended (S96-A); verdict cut §7 agreed by the operator before commit. |

## 1. The question

P7 can show today's flow beside the standing book. Ruling S96-A (D7) holds the **SAME / OPPOSITE**
badge back until this measurement. The badge may speak only when **all four signs are robust to the
known delta defect** — flow net and book net, each keeping its sign when the vendor put delta is
replaced by the parity-implied put delta `Δ_C − 1` (P6 design note §4.2: the substitution moves the book
net 1.6–2.9×). The question is not whether the badge predicts anything. **It is whether, under that rule,
the badge says something often enough to be worth drawing.**

## 2. What has been seen — disclosure

- The **book** under both delta sets was measured on the four legs of the 2026-10-08 settled runs (P6 §4.2):
  sign unchanged on all four. Nothing else of the book's sign history has been computed.
- **Flow has never been computed on real data.** No flow net, flow sign, or badge state has been viewed.
- The scorer was exercised on a **synthetic fixture** (`mp7/fixture/README.md`). Its numbers are
  generated and carry no information about the market; they were used only to show the code runs and the
  gates can fail.

## 3. Sample (fixed at commit)

1. **Dates:** every calendar date 2026-08-24 → 2026-10-09 IST (the chain retention window named in
   roadmap §8.3; how much of it the table still holds is unmeasured, TD-S94-NEW-4, so the status files
   **report** what is there rather than assume it).
2. **Session, per symbol** (`mp7_status.sql`) — the rules of the live views, not new ones:
   - `NOT_SESSION`: an explicit `trading_calendar.is_open = false` row, **or** `count(DISTINCT spot) ≤ 1`
     in `market_spot_snapshots` to 15:15 IST (ENH-140 clauses 1 and 2; catches 2026-10-02);
   - `NO_FRONT`: no chain row with `expiry_date ≥` the date, to 15:15;
   - `NO_PREOPEN`: the first front-expiry row of the date is at or after 09:15 IST (S95-B: absence, never a
     fallback);
   - `ANCHORED`: otherwise. Only ANCHORED sessions are scored.
3. **Rule 13** (`mp7_part0_rule13.sql`): a date is excluded if a `data_contamination_ranges` row whose
   `affected_tables` names `option_chain_snapshots`, `market_spot_snapshots` or `trading_calendar` overlaps
   it. The scorer **stops** if `merdian_ro` sees no rows of that table at all (TD-S94-NEW-1).
4. **SENSEX 2026-09-25, 09-28, 09-29** are scored **separately and reported, not used in the verdict**
   (TD-S95-NEW-1: legs with volume 0 held 33–94 % of front OI and 73–98 % of DEX gross; the book's
   **level** on those days is vendor artefact).
5. Front expiry = ENH-140 leg 1; dte 0 is included (the book publishes it, S94-I).

## 4. Definitions (fixed at commit)

- **Cycle:** each distinct front-expiry chain `ts` in [09:15, 15:15] IST of an ANCHORED session.
- **Anchor:** the session's first front-expiry row (S95-B).
- **Leg arithmetic** (`mp7_cycles.sql`) is ENH-140's, verbatim: `delta × oi × spot / 1e7`, no PE flip;
  no OI → a true 0, tested **before** the gap; gap = `delta IS NULL OR (delta = 0 AND COALESCE(iv,0) = 0)`;
  totals are the measured part, with the uncovered quantity beside them.
- **Flow:** the same arithmetic on `ΔOI = oi(cycle) − oi(anchor)`, NULL unless both sides carry an oi.
- **Delta sets:** vendor (`_v`); parity (`_p`) = PE delta replaced by `Δ_C − 1`, CE unchanged, and a PE
  value is a gap under `_p` when its strike's CE delta is a gap or absent.
- **Nets:** `book_net_x = book_call + book_put_x`, `flow_net_x = flow_call + flow_put_x`, x ∈ {v, p}.
- **Badge state per cycle:** `ABSTAIN` if any of the four nets is exactly 0, or
  `sign(flow_net_v) ≠ sign(flow_net_p)`, or `sign(book_net_v) ≠ sign(book_net_p)`. Otherwise **SAME** if
  `sign(flow_net_v) = sign(book_net_v)`, else **OPPOSITE**.
- **Buckets:** early [09:15, 10:00), mid [10:00, 14:30), late [14:30, 15:15].

## 5. Part 0 — gates before any sign is computed

- **0a Rule 13** as §3.3.
- **0b Live control.** `mp7_control_live.sql` reads the live `v_dex_standing_book` (leg 1:
  `leg_call_dex_cr`, `leg_put_dex_cr`, `leg_oi_qty`, `leg_gap_oi_qty`, `settled_ts`) and the live
  `v_oi_since_preopen` (`anchor_ts`, Σ anchor OI, strikes with an anchor OI). The replay's row for the same
  date at the settled cycle must equal all eight: the two DEX totals within **1e-9 Cr** (both sides are
  `numeric` products and a division by a power of ten, so equality is expected to be exact; the tolerance
  only absorbs text formatting), the three quantities and the anchor time **exactly**.
  **It fails** if the replay's session, front, anchor, gap or arithmetic rule differs from the live
  views' — which is exactly what it exists to catch. On the fixture it fails on a 1e-6 Cr and a 5-minute
  perturbation (`mp7/fixture/README.md`).
  **Timing:** the live views show 2026-10-09 until the 2026-10-12 pre-open rows land (~08:30 IST), so
  **Part 0b must run before then.**
- **If 0a or 0b stops,** no Part 1 number is computed. The defect is fixed, this document is re-issued as
  v2 and committed **before** the re-run, as P2 did (v1 stopped, v2 registered before scoring).

## 6. Reported (all, per symbol, per bucket and overall)

1. Cycles, and counts of SAME / OPPOSITE / ABSTAIN; the **abstain share**.
2. Flow `|net_v| / gross_v`: p25 / p50 / p75.
3. **Persistence:** share of consecutive cycle pairs within a session whose badge state is unchanged, and
   whose flow-net sign is unchanged.
4. Median share of `|ΔOI|` that is uncovered by a delta (flow gap share).
5. Session counts by status; integrity counts (duplicate strikes per cycle; more than one spot in a cycle).

## 7. Verdict (fixed at commit)

- Per symbol, primary sample: **INCONCLUSIVE** if fewer than **20** ANCHORED sessions (P4's n per symbol);
  otherwise **SPEAKS** if the overall abstain share is **≤ 1/2**, else **SILENT**.
- **Why 1/2.** The badge is either showing a state or empty. If it is empty on more cycles than it speaks,
  its empty slot is the board's normal state, and what you learn from it is mostly that it abstained. A
  majority is the cut that says that and nothing more. It is a judgement, fixed here before any flow is
  computed. **Operator yes, 2026-10-11 18:12 IST** ("1 - 20 sessions"), recorded with S96-A in `rulings_s96.md`.
- **Overall:** **BUILD** the badge if both symbols SPEAK; **DECLINED-ON-EVIDENCE** if either is SILENT;
  **INCONCLUSIVE** if either is INCONCLUSIVE. In every case the flow **numbers** still ship (S96-A D7);
  only the badge is decided here.
- **Nothing here tests prediction.** No price, return or outcome is read. A BUILD verdict means the badge
  can be drawn; it does not mean SAME or OPPOSITE carries information about what happens next.

## 8. Run

From `~/meridian-cc` on the box, after this commit and **before 08:30 IST on 2026-10-12**:

```
bash docs/research/s96_priority/p7/mp7/mp7_run.sh
python3 -I docs/research/s96_priority/p7/mp7/mp7_score.py ~/mp7_out
```

Outputs stay in `~/mp7_out` (bulk export, local, pinned by `SHA256SUMS` in the result doc — S95-F).
Each statement runs under `roq.sh`'s 30 s timeout; a timeout fails the run, it does not truncate it.

## 9. Files

`mp7/mp7_part0_rule13.sql` · `mp7/mp7_control_live.sql` · `mp7/mp7_status.sql` · `mp7/mp7_cycles.sql` ·
`mp7/mp7_run.sh` · `mp7/mp7_score.py` · `mp7/fixture/` (synthetic test, local Postgres only).
