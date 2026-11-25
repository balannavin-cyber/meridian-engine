<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/ruling_shadow_dropped_2026-11-23.md -->
# Ruling: the ten-day shadow replay is dropped; a standing measurement discipline replaces it (MR-PIN3, Mon 2026-11-23 20:48 IST)

Operator, verbatim: "We will drop the shadow - we should build a some way, discipline to measure how it is workingf".

## What is ruled
1. The ten-trading-day shadow replay (MR-PIN2 close inputs section 5 row 1; `pin_fix_scope_DRAFT_2026-11-21.md` sections 7-8; engine I-002 row 1 / ENH-149) is **dropped** as a condition. Reason given by the operator at 20:46 IST: anomalies were found in the underlying compute and the current Board pin does not do what it was supposed to; further waiting is not justified. The pin lane agreed: the replay-v2 result (53 unseen days, frozen rule met by VS only) and the order check on revision 3 (PASS, `fix/order_check_rev3/`, main `5a96195`) already answer what ten more days scored the same way would answer.
2. A **standing discipline to measure how the pin is working** is to be built. Design not yet approved; the pin lane proposes it and the operator rules on it.

## What is NOT ruled (unchanged)
- No Board switch is authorised. Nothing is authorised for the Board, `gamma.py` or any signal gate.
- A Board switch still needs the operator's decision, an order-flow lane note first (STREAMS X1), and the engine's build with the ADR-024 Amend A / ENH-125 / ENH-122 / manual corrections in the same change (I-002 row 17).
- The pin lane's position, not yet ruled on: measure the VS pin against the Pin Band on stored data before a switch (unmeasured; decides whether the pin moves alone or with the band).

## Owed from this ruling
- Tell the engine: row 1's shadow condition is withdrawn (ENH-149 text; STREAMS X10).
- Pin lane: propose the measurement discipline (what is recorded each trading day, the baseline, the review rule), pre-registered before the first outcome figure is read.
