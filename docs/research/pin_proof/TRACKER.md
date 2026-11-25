<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/TRACKER.md -->
# Board pin and gamma work: the one tracker

**Owner:** pin lane. **Updated:** Wed 2026-11-25, evening, at the MR-PIN3 close (next session MR-PIN4). This is the single place that says what we set out to do, what is done, and what is next. Both lanes read it. The pin lane rewrites it whenever a step changes state. The session record is `MR_PIN3_close_inputs.md`.

## What we set out to do (19 Nov 2026)

Work through the Board discrepancy list, **pin first**: prove the Board's pin is wrong, find the right one, put it on the Board. Then the rest of the list.

Along the way we found a wider fault: the vendor leaves gamma blank on many legs, and the old code drops those legs, so net gamma and everything built on it is off. That became a second goal: fix gamma at the source.

## Goal 1: the right pin on the Board

| # | Step | State | Date |
|---|---|---|---|
| 1 | Show the Board's pin is wrong, with evidence | Done | 21 Nov |
| 2 | Rule what the pin is: the strike with the largest gross gamma exposure | Done | 21 Nov |
| 3 | Rule how to compute it: one gamma per strike | Done | 22 Nov |
| 4 | Build the gross pin view and check it independently | Done, check passed | 23 Nov |
| 5 | Put it on the Board as "Pin"; old pin shown as "Net peak" | **Done, live** | 25 Nov, 18:08 IST |
| 6 | Look at it in market hours | Next | 26 Nov, after 09:20 |
| 7 | Measure daily how it behaves (the monitor) | Running; day 1 recorded (25 Nov); day 2 due 26 Nov after 16:30 | from 25 Nov |

**Goal 1 is achieved**, subject to step 6.

## Goal 2: fix gamma at the source

Order changed by the operator on 25 Nov, 18:50 IST: tables and backfill first, then the comparison.

| # | Step | State | Who |
|---|---|---|---|
| 1 | Measure the fault (gamma pipeline audit) | Done, 22 Nov | |
| 2 | Decide the approach: new version alongside the old, old one untouched | Done, 25 Nov | |
| 3 | Write the rule for the new calculation | Done (v1.2), 25 Nov | |
| 4 | Engine writes the new code | Done, 25 Nov | |
| 5 | Prove the code matches the rule, independently | Done: passed for v1.1, v1.2 and the final package, 25 Nov | |
| 6 | Create the two new tables | **Done**, 25 Nov, about 19:15 IST | Operator applied |
| 7 | Backfill one day (2026-08-27) and check it against the independent output | **Done: check passed**, 25 Nov, 19:50 IST | Operator ran; pin lane checked |
| 8 | Backfill the full stored history | **Running**: operator started it about 19:57 IST, 25 Nov. Outcome with the engine | Operator runs the engine's list |
| 9 | Compare old against new on history; report how far each figure moves | Not started. Pin lane drafts the pre-registration; operator approves before it runs | Pin lane |
| 10 | Operator decides on that result | | Operator |
| 11 | Switch the live writer on; schedule the invariant job | Written, **not approved** | Engine, operator |
| 12 | Build the new-version views | Not started, not approved | Engine |
| 13 | Move Board tiles to the new figures, one by one | Not started, not approved | Engine, operator |

**Goal 2: steps 1 to 7 done, step 8 running. Nothing of it is live on the Board.** The new tables exist; nothing reads them. Steps 11 to 13 wait on step 10.

Ruled on 25 Nov: runs outside market hours stay in the new tables; the comparison in step 9 uses 09:15 to 15:30 IST as its main set and reports the others separately (boundary to be approved with the design).

## Goal 3: the old interpretations (added 25 Nov)

| # | Step | State |
|---|---|---|
| 1 | Label the old flip-based outputs "legacy, unvalidated" on the Board | Done, live 25 Nov |
| 2 | Label the Board Flip "experimental" | Done, live 25 Nov |
| 3 | Remove the legacy outputs from the Board | Later, one release |
| 4 | Decide whether a flip is needed at all, and test candidates | Parked until Goal 2 is built |
| 5 | Dealer wording, case by case | To be discussed; nothing changes meanwhile |

## Goal 4: the rest of the Board discrepancy list

Not started. The pin was first by your ruling.

## Open questions, not blocking

- Should the Pin Band follow the gross pin? Today it is drawn around the net peak.
- Should the gross pin get its own "state" and "conviction"? Today those describe the net peak.
- Does the gross pin actually attract price? The monitor collects the evidence; no test has been run.
- On 2026-08-27 there is no stored run at 15:25, 15:30 or 15:35. Asked the engine whether that is every day.

## What is next, in order

1. **Engine and operator:** the full backfill (Goal 2, step 8) is running; the engine reports the result.
2. **Pin lane (MR-PIN4):** read the B3 result; draft the step 9 pre-registration for approval.
3. **Thu 26 Nov after 09:20:** look at the Board in market hours (operator, with the engine's short list).
4. **Thu 26 Nov after 16:30:** monitor day 2 (operator, one prompt; the pin lane writes it before 16:30).
5. **Operator, this evening:** the git route for the pin lane's records (steps in the MR-PIN3 chat), so the PK files can be cleared.

## Small loose ends

- A misleading line in the Pin detail panel (engine, next Board round).
- The engine's guard and promote scripts in git are the faulty versions; engine to replace.
- Git copies of the v1.2 check files, the B2 files, the advisor pack, monitor day 1 and the PK files in `claude/pin/` (pin lane; the zip is built, the operator commits it).
- The branch `pin/v2-check` carries the engine's package commits as well as the pin lane's files: do not merge it into `main` as it stands.
- A stray folder on Windows: `C:\Users\balan\docs\research\pin_proof\v2_check`.

## Who does what

- **Engine lane:** writes all production code, SQL and Board prompts.
- **Pin lane:** independent checks, the monitor, and this tracker.
- **Operator:** rulings, applying SQL, commits, running Board prompts.
