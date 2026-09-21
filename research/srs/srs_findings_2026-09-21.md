# S80 SRS exploration — findings arising outside M1's scope

Claim-ledger rows for defects surfaced while measuring M1. Each is stated with
the evidence that produced it. **These are filed here, not in
`docs/registers/tech_debt.md`, because the exploration brief restricts new
files to `research/srs/`.** They need transcribing into the register at session
close.

---

## TD-CANDIDATE-1 — `hist_spot_bars_5m` PADS absent sessions with carried-forward rows

**Severity: S2.** Not a Muhurat problem. A general one.

### What was measured

SENSEX, 2025-10-21 (Diwali Muhurat — the option chain ran **13:45–14:44 only**,
so the equity market was shut all morning).

`hist_spot_bars_5m` nevertheless reports a full session: **82 rows spanning
09:15–16:00**.

```
09:15  O=84363.37 H=84363.37 L=84363.37 C=84363.37 V=None
09:20  O=84363.37 H=84363.37 L=84363.37 C=84363.37 V=None
09:25  O=84363.37 H=84363.37 L=84363.37 C=84363.37 V=None
...
15:50  O=84426.34 H=84426.34 L=84426.34 C=84426.34 V=None
15:55  O=84426.34 H=84426.34 L=84426.34 C=84426.34 V=None
16:00  O=84426.34 H=84426.34 L=84426.34 C=84426.34 V=None
```

- every bar has `O == H == L == C` — **zero intrabar range on all 82**
- `volume` is **NULL on every row**, never 0
- only **18 distinct OHLC tuples across 82 rows** — long runs of one carried
  value

Those morning rows describe a session that did not happen.

### Why it matters beyond this date

The padding is **not** specific to Muhurat. Any halt, any partial feed outage,
any early close would be padded the same way and would be **invisible to every
consumer that counts rows or reads a session's first/last bar**. A reader
asking "was the market open?" gets yes; a reader asking "how many bars?" gets
a full session.

Two specific consequences already observed:

1. **Session-shape detection cannot use spot.** M1's special-session detector
   had to read the option chain instead (first chain bar later than 11:00 IST).
   Spot reported a normal 09:15–16:00 day.

2. **`is_filler_bar()` would not fire on these rows.** The S70 check requires
   `volume == 0` **and** a flat bar. Here volume is **NULL**, not 0, so the
   first clause fails and the padded bar passes as real. If that helper is
   relied on anywhere as a padding guard, it has a hole exactly the width of
   this case.

### What would falsify this

A day with genuinely flat prices and NULL volume that the market really was
open through. The 13:45 chain start on the same date rules that out here: the
chain and spot cannot both be right about 09:15–13:45.

### Not investigated further

Deliberately scoped. Not established: which writer pads, whether it pads on
halts as well as closed sessions, whether `hist_spot_bars_1m` and the era-2
spot sources do the same, and how many days in the 2025-04 → 2026-03 window
are affected. Each is a real question; none is this one.
