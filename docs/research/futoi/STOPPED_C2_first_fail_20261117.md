# MR-FOI M1/M2 run STOPPED at Part 0 step 6

Date (UTC): 2026-11-17T23:27:37+00:00

Pre-registration section 5: "Any control failing stops the run. The cause is diagnosed before anything in section 3 or section 4 is computed."

**Nothing in section 3, 4 or 7 was computed.**

## C2 FAILED -- units of futures OI and option OI

**The control fails when:** a contract-count series has GCD 1; two different units would make h-hat dimensionally meaningless

**Measured:**

```
median series-1 futures OI at close:               14956275  (n=247 sessions)
median front-expiry option OI per strike
  over the 5 strikes nearest spot:                  3373425  (n=2470 legs)
pooled GCD over the whole window, futures:                5
pooled GCD over the whole window, options:                5
   (pooling collapses eras; the per-session GCD is the measurement)
per-session GCD, futures -- contiguous runs:
     2025-04-01 .. 2025-12-30   GCD 75
     2025-12-31 .. 2026-03-30   GCD 65
per-session GCD, options -- contiguous runs:
     2025-04-01 .. 2025-06-18   GCD 75
     2025-06-19 .. 2025-06-25   GCD 25
     2025-06-26 .. 2025-12-22   GCD 75
     2025-12-23 .. 2025-12-29   GCD 25
     2025-12-30 .. 2026-03-23   GCD 65
     2026-03-24 .. 2026-03-27   GCD 5
     2026-03-30 .. 2026-03-30   GCD 65
sessions where the two GCDs agree:          234/247
```

units do NOT agree -- h-hat is withheld until a conversion is stated.

## Controls that passed

- C1 clock alignment, futures vs spot 1-minute returns
- C3 gamma parity, sign(g) vs sign(net_gex)
- C4 delta sanity at the money
