# TD-S95-NEW-1 (c) — untraded-leg guard survey (S96)

Descriptive, read-only; reads no price outcome; decides nothing. Feeds the operator's call on a guard that the
M-P7 badge needs before it goes live (M-P7 result §4).

- `guard_cycles.sql` — per (symbol, cycle) of the front expiry, 09:15–15:15 IST, on every session in
  2026-08-26 → 10-09 (45 dates): share of DEX gross and OI on suspect legs, by signature, **evaluated at the cycle**:
  - **S1** volume 0 so far on a leg with OI (a live guard cannot use "volume 0 all session");
  - **S2** S1 and `oi_change = oi` — the vendor reports all of today's OI as new while nothing traded, which cannot
    happen (the S95 artefact legs carried `oi_change = oi` on every row).
- `guard_run.sh` — runs it per date through `bin/roq.sh` into `~/guard_out` (45 CSVs + `SHA256SUMS`).
- `guard_summary.py` — per symbol-session min/median/max, and per bucket the separation between the three
  TD-S95-NEW-1 days (SENSEX 09-25 / 09-28 / 09-29) and the rest.

Fixture check (S96, local Postgres, synthetic): 45 files; a planted artefact leg (volume 0, `oi_change = oi`,
48.8 M OI) reads S2 ≈ 99 % of gross on its day and S2 = 0 on every other session; S1 is high on every
session by construction of the fixture — the reason S1 alone is not expected to serve.
