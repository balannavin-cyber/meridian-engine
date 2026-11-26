<!-- pk: lane=engine; git=meridian-engine:docs/research/s107/engine_note_board_pin_switch_for_ofl_2026-11-26.md -->
# Engine note to the order-flow lane: the Board Pin changed; the `/tape` anchor did not (2026-11-26)

For MR-OFL10. STREAMS X1 required this note **before** any Board pin change. It was not written before the change;
it is written now, at the S107 engine close (Assumption Register §D.62.4). Nothing here asks the order-flow lane to
change anything today.

## 1. What changed

- **When:** Wed 2026-11-25, about 18:08 IST, on the operator's ruling of 09:23 IST that day. Board `d7642c2`.
- **The Board's "Pin" tile** now reads `v_gex_pin_gross`: the strike with the largest **gross** exposure among the
  strikes within 5 % of spot (gamma × (OI call + OI put)), with its share and its lead over the runner-up.
- **The earlier pin** is still on the Board, under the name **"Net peak"**, with pin state, held cycles and
  conviction beneath it. It is `gex_cycle_history.pin_leader_strike`, rank 1 of `v_gex_strike_rank` on absolute
  **net** exposure.

## 2. What did not change

- `gex_cycle_history.pin_leader_strike` is **not redefined**, and `v_gex_strike_rank` is not replaced.
- `/tape` reads those two objects (STREAMS §2). So the `/tape` PIN anchor is the same strike it was before the
  switch, computed the same way.
- No grant on any `tape_live_*` table changed. `tape_w` and `merdian_ro` are as you read them on 2026-11-24.

## 3. What is now different for a reader of both pages

`/tape` labels its anchor "PIN". From 2026-11-25 the Board calls a different quantity "Pin". On the pin lane's first
monitor day (2026-11-25, 75 runs per symbol) the gross pin equalled the earlier pin on 42 of 75 NIFTY runs and 11 of
75 SENSEX runs. So on many runs, most of them on SENSEX that day, the two pages show different strikes under the
same word. That is one day; it is not a rate.

## 4. The decision that is yours to bring to the operator

| Option | What it needs |
|---|---|
| A. `/tape` keeps the net anchor and renames it "Net peak" | A `/tape` wording change only |
| B. `/tape` moves its anchor to the gross pin | Whichever role `/tape` reads with must hold SELECT on `v_gex_pin_gross` (today: `authenticated`, `marketview_ro`, `merdian_ro`); if it does not, the engine authors the grant and the operator applies it. Note the view is latest-run only: it has no history, so an offline replay cannot read past values from it. For 2026-05-25 → 2026-11-25 the gross pin strike of a past run can be derived from `gex_strike_v2` (the `in_band` row with the largest `gross_cr`; ties are broken in the view by distance to spot, then strike); those tables have no live writer, so nothing after 2026-11-25 is there |
| C. `/tape` shows both | As B, plus the wording of A |

Under pre-registration v0.4 the tape scoring definitions are frozen. Whether a change of anchor touches a scored
definition is the order-flow lane's to say; the engine has not read it.

## 5. Also for OFL10, from the engine side

- X3 is done except two items: the E-4 contract INSERTs on the writer-start day, and the engine's confirmation that
  the offline path stores `''` in `tape_live_label.reason` and `tape_live_events.side`. The second has not been
  read; say when you want it.
- Your eight TD candidates are filed as TD-OFL9-NEW-1…8; your intake rows are taken in
  `docs/registers/intake/I003.md`.
- Production box memory is STREAMS X12 (TD-PIN2-NEW-12).
