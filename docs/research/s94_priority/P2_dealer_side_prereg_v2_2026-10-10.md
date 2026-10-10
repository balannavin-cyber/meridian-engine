# P2 — Dealer-side check: pre-registration **v2**

| Field | Value |
|---|---|
| **Status** | **PRE-REGISTERED (v2).** Committed with `p2/p2_score_v2.py` **before** the extract is scored. Its `git hash-object` is recorded in the result doc. Approved by the operator on 2026-10-10 08:42 IST. |
| **Supersedes** | v1, `P2_dealer_side_design_2026-10-10.md` (`git hash-object f425f171df981f16f578daeb50d9b8225b378b41`, commit `dcf567a`). **v1 is not edited.** It ended **STOPPED — integrity gate mis-specified, no verdict**. The record is `p2/v1_stop_2026-10-10.md`. |
| **Track item** | Roadmap §2.1 **P2** (ruling **S94-A**). Risk class **RO**. |

## 1. What carries over from v1 unchanged

All of v1 carries over **except the two clauses in §2 below**: the question (v1 §1), the limits
(§2: NSE only and so **NIFTY only**; aggregate index options; sign only; contract counts), the
Part 0 results (§3a), the definitions of `net_call` / `net_put` and of *holds* / *inverted* /
*mixed* (§4), the proxies (**Pro** primary, **Pro + FII** secondary, the rest descriptive), the
verdict rule (§5: CONSISTENT / INVERTED at **Wilson 95 % lower bound ≥ 0.80**, otherwise
REGIME-DEPENDENT; primary and secondary must agree), and the window (2025-05-28 → 2026-10-09,
**n = 340**, asserted). v1 is cited for these, not restated, so the two cannot drift apart.

## 2. The two changed clauses

**2.1 Integrity tolerance (replaces v1 §3a's exact-equality assertion).** v1 required the four
categories to sum **exactly** to NSE's TOTAL row on each leg. Measured on the extract (integrity
only, with no net position or classification computed): **457 of 1,360** (date, leg) cells
differ, **all by exactly ±1 contract**; the largest relative difference is **5.3 × 10⁻⁷**; and
TOTAL long = TOTAL short on **all 340** dates.

The tolerance is **derived from rounding mechanics, not from the ±1 observed.** If each of the
4 categories and the TOTAL is rounded independently, each carries at most ±0.5. So
|Σ categories − TOTAL| ≤ 4 × 0.5 + 0.5 = 2.5, which for integers is **≤ 2**.

- **Assert |Σ categories − TOTAL| ≤ 2** on every date and leg. A difference above 2 **stops** P2.
- **TOTAL long = TOTAL short stays exact.** It is the both-sides identity, and it held on every date.

**2.2 Rounding-indeterminate signs count as *mixed* (added to v1 §4).** For a scored group of
*k* categories, on any date where **|net_call| ≤ 2k or |net_put| ≤ 2k** contracts, the sign
cannot be resolved at the source's granularity. That date is classed as **mixed**, never as
*holds* or *inverted*. (The tight bound is *k*, since each category's net is a difference of two
values rounded ±0.5. 2*k* was approved as the conservative form.) This can only make CONSISTENT
or INVERTED **harder** to reach. The scorer reports how many dates this clause reclassified, per
group.

## 3. Execution

1. Commit this note, `p2/p2_score_v2.py`, `p2/v1_stop_2026-10-10.md` and
   `p2/part1_extract_v2.sql` (the SELECT used to extract; see the v1 stop record for why v1's
   `COPY` could not run). Record `git hash-object` of this note.
2. Score the **existing** extract `p2/part1_extract_2026-10-10.csv` (sha256
   `5fbc3a9b280ac279910e2076ea90c7d6f19e934af09e34254f02b9bc070a31b3`) with
   `python3 -I p2_score_v2.py`. It is not re-extracted, so v1's stop and v2's score read the same bytes.
3. Write `P2_dealer_side_result_2026-10-10.md` with the verdict, the table, the limits from v1
   §2, and the v1 → v2 history. Commit it with the extract.
