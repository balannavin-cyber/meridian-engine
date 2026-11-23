# Ruling — pin definition, 2026-11-21

Session MR-PIN2. Operator ruling, Sat 21 Nov 2026 11:48 IST: "lets settle for text" — the textbook pin.

## What is ruled

The pin is the strike with the largest gross gamma × open interest: argmax over strikes of g_K · (call OI + put OI). Not the netted call − put quantity the Board ranks on today (`v_gex_strike_rank`, ENH-125), and not a pressure-weighted variant.

Basis: `claude/pin/pin_behaviour_v5_result_2026-11-21.md` (12 months, 246 NIFTY / 245 SENSEX sessions, 24 runs per session).

## What is not ruled

- Whether the Board shows the lead beside the pin, or both strikes when the lead is under 5 %. Recommended by the reviewing session; not yet confirmed by the operator.
- Which gamma production uses (per-strike or flat), the tie-break, and the strike set. These belong to the production gamma fix scoping (one gamma per strike, blank leg not zero, forward from market).
- Any change to the Board or to production. Nothing is authorised by this ruling; the change is a separate, scoped piece of work.
- Any relabel of "dampening / amplifying".

## Known properties of the chosen pin (from the study)

- It is one of the two walls on about two-thirds of runs (66.1 % NIFTY, 64.5 % SENSEX).
- It does not locate the settle strike better than the ATM strike in any bucket.
- About 45 % of its changes happen when the lead was under 5 %.
- It is the same strike as the wide pressure pin on 91–93 % of runs.

## D-5a

The pressure variants were examined for the look-back only, as re-opened in `claude/pin/ruling_D5a_reopen_2026-11-20.md`. With this ruling neither goes forward.
