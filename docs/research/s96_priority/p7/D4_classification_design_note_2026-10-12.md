# D-4 — classified flow (writing / covering / unwinding) for P7: design note (DRAFT, S96)

**Status: RULED S96-I (2026-10-12): K0 = decline. D-4 is DECLINED-ON-EVIDENCE; K1–K6 are not taken up.** Nothing built, nothing applied. Roadmap §2.1 P7 absorbs ENH-98 D-4. S96-A D3
amended the L7/L8 badge to *"flow-vs-book shown on unclassified ΔOI; classification (D-4) not built"* rather than
retiring it.

Inputs read for this note:
- `claude/P7_flow_vs_book_design_note_2026-10-11_DRAFT.md` §1, §5, §7 D3;
- roadmap §2.1, last paragraph;
- `tests/golden/2026-10-01_SENSEX/queries/ladder_replay_1001.sql`, where per-cycle classes are already defined;
- `claude/ref_2026-10-01_SENSEX_0DTE.md`, its limits section;
- TD-S95-NEW-1;
- `claude/parity_dovetail_and_post_parity_plan_S89.md` §1.2 (D-4).

No query was run for this note.

---

## 0. A conflict I should have flagged at 06:50

The four-case method (ΔOI × premium change: OI up/premium up, OI up/premium down, OI down/premium up, OI down/premium
down) **was triaged off this track on 2026-10-09**. Roadmap §2.1's last paragraph lists *"ΔOI × price four-case"*
among the items not on the track. The P7 design note (§1 item 2, §7 D3) recorded that unclassified flow does not
discharge D-4, and that the badge can be retired only if the four-case is ruled off D-4 for good.

So "keep D-4 in P7" (your answer this morning, on my recommendation) means **re-admitting the four-case to the track**,
which amends the 10-09 triage. My question at 06:50 didn't say so. **K0 below asks it properly before anything is
built.**

## 1. What D-4 would add

Today P7 shows **how much** exposure was added or removed since the pre-open (unclassified ΔOI × greek). D-4 would split
that ΔOI by what the premium did over the same interval:

| ΔOI | premium | the parity target's name | what it can and cannot say |
|---|---|---|---|
| up | down | short build-up ("writing") | consistent with net selling. It does not identify who sold |
| up | up | long build-up | consistent with net buying |
| down | up | short covering | consistent with shorts closing |
| down | down | long unwinding | consistent with longs closing |

**The limit that matters for this board:** premium moves with spot, iv and time as well as with order flow. On a day
spot falls, every put's premium rises and every call's falls, whoever traded. So the four cases partly re-encode the
spot move. The method is the target's *India ΔOI* (#596), and the 10-01 replay used it per cycle. It is a heuristic,
not a measurement of who traded. The board's existing sentence, *"this does not say who bought or wrote"*, applies to
it with more force.

## 2. Proposed rulings

| # | Decision | Recommendation | Alternative |
|---|---|---|---|
| **K0** | Re-admit the four-case to the §2.1 track as P7's D-4 (amends the 10-09 triage)? | **Your call; I lean to decline.** The limit in §1 means the classes partly restate the spot move, and n = 1 day (10-01) is all the evidence there is. Declining makes D-4 **DECLINED-ON-EVIDENCE**, keeps the amended badge as a permanent D3 deviation, and lets P7 close **DONE** on today's live read | Re-admit: build it with K1–K6, about 1 session plus a pre-registration |
| K1 | Interval | **Per cycle (5-min), summed over the session**, as in the 10-01 replay. A since-pre-open net hides a leg built and then closed within the day | Since the pre-open anchor (matches P7's flow) |
| K2 | Premium | **Mid when bid and ask are both > 0, else unclassified.** LTP is stale on untraded legs (TD-S95-NEW-1) | LTP, as the replay did |
| K3 | Units | **OI quantity and share of standing OI** (scale-free; the 10-01 limits note asked for this) | Delta-weighted Rs crore, like the flow tiles |
| K4 | Where | **A view** over the session's chain: the 10-01 replay pattern, and P3b's T4 measured about 216k chain rows in about 1 s | A per-cycle sidecar table |
| K5 | Words on the board | **Neutral descriptors** (*"OI up · premium down"*), with the target's names only in the explanation box. Your yes is needed on every string | The target's names on the tile |
| K6 | Evidence before it ships | A **pre-registered measurement** first, like M-P7: share unclassified, stability by time bucket, and how much of each class the spot move alone explains. Reports only | Ship as display-only without a measurement |

## 3. If K0 = decline

- **P7 → DONE after today's live read.** The exit evidence ("flow-vs-book shown on the board; L7/L8 badge retired")
  is met with the badge **amended, not retired**, recorded as an ADR-025 D3 deviation, with the reason in §1.
- The roadmap §2.1 P7 row records D-4 as **DECLINED-ON-EVIDENCE**, citing this note.
- No board change. The amended badge text stays true as written.

## 4. If K0 = re-admit

Order:
1. K1–K6 ruled.
2. Pre-registration hashed before the first query.
3. View authored, costed through `roq.sh`, applied with its verification SELECT.
4. Measurement scored.
5. Board round under the S92 guard, with your yes on every string.
