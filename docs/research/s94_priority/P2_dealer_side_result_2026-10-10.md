# P2 — Dealer-side check: RESULT

| Field | Value |
|---|---|
| **Pre-registration** | **v2** `P2_dealer_side_prereg_v2_2026-10-10.md`, `git hash-object 7342cacd29495b47837ac4fd24a871b90bdc7780`, commit `c920832`. Supersedes v1 (`f425f171…`, `dcf567a`), which **STOPPED** on a mis-specified integrity gate with no verdict computed (`p2/v1_stop_2026-10-10.md`). |
| **Input** | `p2/part1_extract_2026-10-10.csv`: 1,701 lines (header + 340 dates × 5 categories), sha256 `5fbc3a9b280ac279910e2076ea90c7d6f19e934af09e34254f02b9bc070a31b3`, from `p2/part1_extract_v2.sql` through `bin/roq.sh`. This is the **same file** v1 stopped on; its sha256 was re-checked before scoring. |
| **Scorer** | `p2/p2_score_v2.py`, run as `python3 -I`, exit 0. |
| **Scored** | 2026-10-10 ~08:45 IST (S94), operator-run on the box. |

**Verdict (v2 §1 → v1 §5): REGIME-DEPENDENT.** Neither proxy reaches CONSISTENT or INVERTED
(Wilson 95 % lower bound ≥ 0.80).

## Scorer output, verbatim

```
Input `part1_extract_2026-10-10.csv` · dates 2025-05-28 → 2026-10-09 · n = 340 · integrity OK (|Σ−TOTAL| ≤ 2; TOTAL long = short exact)

| group | holds | inverted | mixed (of which rounding-indeterminate) | holds 95% (Wilson) | inverted 95% | verdict |
|---|---:|---:|---:|---|---|---|
| Pro (PRIMARY) | 23 | 113 | 204 (0) | [0.045, 0.099] | [0.284, 0.384] | REGIME-DEPENDENT |
| Pro+FII (SECONDARY) | 0 | 231 | 109 (0) | [0.000, 0.011] | [0.628, 0.727] | REGIME-DEPENDENT |
| Client (descriptive) | 226 | 0 | 114 (0) | [0.613, 0.713] | [0.000, 0.011] | — |
| DII (descriptive) | 0 | 12 | 328 (8) | [0.000, 0.011] | [0.020, 0.061] | — |
| FII (descriptive) | 0 | 255 | 85 (0) | [0.000, 0.011] | [0.701, 0.793] | — |

**Verdict (§5): REGIME-DEPENDENT**
```

*holds* = net long index calls **and** net short index puts, which is the position the board's
CE+ / PE− sign assumes for the dealer (`compute_gamma_metrics_local.py:133`). *inverted* is the
mirror of that.

## Limits — what this result cannot carry

1. **Serial dependence (not stated in the pre-registration; added here).** Open interest is a
   stock that carries from day to day, so the 340 dates are **not independent**. Wilson's interval
   assumes they are, so **every interval above is too narrow**. The verdict is unaffected: wider
   intervals cannot lift a point estimate of 0.68 to a lower bound of 0.80. But it means no
   statement stronger than REGIME-DEPENDENT can be made from this table.
2. **NSE only, so NIFTY only. SENSEX is untested** (v1 §2).
3. **The index-option aggregate covers all NSE index underlyings**, not NIFTY alone (v1 §2,
   §3a: no per-underlying column).
4. **Sign of net contract counts, not gamma.** P2 says nothing about per-strike positioning,
   the flip, the walls or magnitudes.
5. **"Dealer" is a proxy.** Pro and FII are the pre-registered stand-ins. NSE labels no one a dealer.

## Descriptive observations — NOT findings, not claimable

These are stated so that a later pre-registration starts from something written down, not
remembered.

- The pre-registered proxies **never** held the board's assumed position: Pro + FII on 0 of 340
  dates, and FII on 0. They held the **opposite** on 231 (Pro + FII) and 255 (FII) of 340 dates.
- **Client** held the board's assumed position on 226 of 340 dates and the opposite on none.
- Read together, the board's CE+ / PE− sign looks much more like the **client** book than like
  either dealer proxy. That is consistent with ADR-015's own statement that `gex_cr` is
  *"positioning gamma, not dealer gamma"*. Because of limit 1, it is **not** evidence that the
  sign is inverted.
- The rounding-indeterminate clause (v2 §2.2) reclassified **0** dates for the scored groups,
  and 8 for DII (descriptive).

## Owed under v1 §5 (REGIME-DEPENDENT branch)

v1 §5 requires the split **by DTE bucket and by 5-day spot trend**, as **reporting strata only**.
It is **not yet produced**: the scorer does not carry spot or expiry. DTE is also ambiguous for
an aggregate spanning several underlyings with different expiry days. That ambiguity has to be
resolved in the reporting script, and stated, before the split is produced. Any conditional claim
from it would be a **new** pre-registration.

## Consequences for the track (for the operator; nothing applied)

- **Assumption Register, dealer-sign row:** proposed status **UNDER REVIEW: P2
  REGIME-DEPENDENT (NSE aggregate; the pre-registered proxies did not hold the board's sign on
  any date)**. The register entry is made at doc-close.
- **S94-A stands:** P5, P6 and P7 remain on HOLD until **P4** also reports. P2's result does
  not release them.
- **Owed ruling (new):** the board labels positive `gex_cr` *dampening* and negative
  *amplifying*. Those words describe **dealer** gamma. P2 does not support reading the sign as
  dealer gamma. Whether to relabel (for example *"positioning γ, call-side +"*), caveat, or leave
  the labels is the operator's ruling. It is the same family as S94-D.
