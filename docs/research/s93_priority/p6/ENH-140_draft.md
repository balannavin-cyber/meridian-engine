# ENH-140 — draft register entry (NOT YET SPLICED)

**Status of this file:** a splice-ready draft of the `ENH-140` entry for
`docs/registers/MERDIAN_Enhancement_Register.md`. **It has deliberately not been written
into the register.** The register's own S92 Part-7 note records the sequencing:

> *"The post-parity track (S92-I) mints **no** ENH ids yet: the DEX standing book (P6) and
> the flow leg (P7) are filed when P1 returns, by operator sequencing."*

Splicing ENH-140 in now would contradict that recorded decision, so the id is **reserved and
checked free** (highest existing: ENH-139) and the text is parked here. Two things are owed
when P1 returns: paste the summary row at its number position in the table, and the detail
block in id order. Both are below, verbatim and ready.

If the operator would rather the id were not reserved at all until P1 returns, delete this
file — nothing else depends on the number.

---

## 1. Summary-table row

Insert in id order, immediately after the `ENH-139` row:

```markdown
| ENH-140 | P6 DEX standing book — `v_dex_standing_book`: per-strike call/put/net delta exposure of the open interest, in ₹ crore, for the latest settled run of each leg | display | **PROPOSED 2026-10-09 (S93)** — authored, **not applied**. `sql/2026-10-09_s93_v_dex_standing_book.sql` (1 view, 24 cols, grain `(symbol, expiry_date, strike)`), design note `docs/research/s93_priority/p6/P6_dex_design_note.md`, offline test `tests/test_dex_recompute.py`. Roadmap §2.1 **P6** (ruling S92-I). Not a parity layer (ADR-025 closed, Amendment D); display-only per S37. **No dealer column** — ADR-015's sign gloss is inverted against ADR-014 §2.3, and the two dealer readings differ in size always and in sign whenever `net_dex_cr > 0`; P2 rules. **No zero-Δ column** — both briefed candidates measured degenerate; S\* (re-priced, ENH-131 code path) specified and pending operator ruling. |
```

## 2. Detail block

Insert in id order, after the `ENH-139` detail section:

```markdown
### ENH-140 — `v_dex_standing_book`, the DEX standing book (PROPOSED 2026-10-09, S93)

**Roadmap** §2.1 **P6** of the S92-I post-parity priority track ("DEX standing book plus
zero-Δ strike, on the board"). **Ruling basis** S92-I; S92-G / S92-J for the one-rule /
one-implementation constraint. **Not a parity layer** — ADR-025 closed at Amendment D;
this adds no layer and amends no disposition. Display-only (S37 GEX-as-context-not-gate).

**What it is.** Per strike, the delta exposure standing in the open interest:
`call_dex_cr`, `put_dex_cr`, `net_dex_cr` from `option_chain_snapshots` as
`delta × oi × spot / 1e7` — ₹ crore on the same convention as `gex_cr`, with **one** power
of spot where GEX uses two. Grain `(symbol, expiry_date, strike)`, the latest **settled**
run per leg (last run at or before 15:15 IST — the ENH-126 river rule, because after 15:15
the index is auction-frozen, ADR-022). Both legs, `leg_n` ranks them; consumers filter
`leg_n = 1`. Per-leg totals and the un-deltaed OI are **columns**, so no client recomputes
anything (S92-G). The leg totals are the **measured part** of the leg, not a complete
total: `leg_gap_oi_qty` is the OI they do not cover, and the pair is read together. **No
running cumulative** — its only consumer was the withdrawn cumulative zero-Δ candidate, and
a running sum over `COALESCE(…, 0)` walks past gap strikes unflagged.

**STATUS: AUTHORED, NOT APPLIED.** No `CREATE`, `COMMENT` or `GRANT` has been issued. The
body was costed as a plain `SELECT` through `bin/roq.sh`; Section 4 has not been run.

**Measured at design time** (probes in the design note, each with its SQL):

- **`oi` is a QUANTITY, not a contract count** — 100 % divisibility at 20 (SENSEX) and 65
  (NIFTY) with the minimum positive `oi` equal to the lot, corroborated by
  `public.instruments.lot_size` and by **ADR-014 §2.3's S75 correction**, which already
  established that Dhan reports `oi` lot-multiplied. P6 reproduces that conclusion
  independently; it does not discover it. So no multiplier appears anywhere.
- **`gex_cr` reconstruction** from the chain with `signed_gamma_exposure()`'s formula
  verbatim matched the stored column on 159 strikes, **max abs diff 1.17e-9 Cr, 0
  mismatches** — the anchor that fixes the ₹ crore convention DEX mirrors.
- **PE delta is stored negative** (min −0.99341), so **DEX carries no explicit sign flip**;
  GEX needs one only because vendor gamma is positive on both sides. Copying GEX's flip
  would double the negation and destroy the netting.
- **`delta` is never NULL in the data but is ZERO as a GAP** on 9.1 % (NIFTY) / 23.6 %
  (SENSEX) of positive-OI rows. Over 55,228 rows of 2026-10-08, **every** `delta = 0` row
  also carries `gamma = 0` and `iv = 0`, with **zero** rows at `delta = 0, iv > 0` — the
  vendor drops the whole greeks block together. The gap is ITM-concentrated and
  put-asymmetric (3 CE rows / 4,100 units vs 51 PE rows / 7,722,860 units at the SENSEX
  settled run). NULL is published, never 0 (ADR-018 D2 / ENH-116 lineage).
- **`run_id` is per `(symbol, ts, expiry_date)`, not per cycle**, and
  `gex_strike_snapshots` holds the W1 leg only — so W2's run is not discoverable from it,
  which is why the grain is per-leg.
- **Cost**: cold **1,322.7 / 1,445.0 / 1,934.3 ms**, warm **81.6–103.4 ms**, 862 rows,
  against anon's binding 3 s `statement_timeout` (MV-6) — **1.55× headroom at the worst
  cold run**, and the cold figure is the variable one. The first draft of the leg-discovery CTE was a
  plain join at **8,095 ms** (3.2 M index entries scanned, 3,113,638 rows removed by join
  filter); the `CROSS JOIN LATERAL` rewrite took it to 61 ms. **ADR-021 shape, found by
  measuring.**

**Two things this view deliberately does NOT carry.**

1. **No dealer column.** ADR-014 §2.3 — which ADR-015 says it carries unchanged — reads
   positive `gex_cr` as **dealer LONG** with calls the positive term, i.e. calls
   dealer-long and puts dealer-short. ADR-015's own gloss says the convention coincides
   with *"dealers short calls and long puts"*, **the exact inverse on both legs**. The code
   is not in doubt; the English in ADR-015 is. The two readings give dealer delta
   `= call_dex_cr − put_dex_cr` and `= −net_dex_cr`, which on NIFTY W1 2026-10-08 are
   **+129,272.61** and **+11,878.01** Cr — the same sign on this leg but an order of
   magnitude apart; they differ in **sign** whenever `net_dex_cr > 0`, which was not
   observed on the four legs measured. **P2 (S92-I item 2) rules.** Every surface reads
   *"open-interest delta — dealer side unruled (P2)"*.
2. **No zero-Δ column.** Both candidates in the P6 brief were measured and withdrawn: the
   cumulative `net_dex` has **no zero crossing on any of 4 legs** under either of two delta
   sets (it starts at 0, runs monotonically negative to −24,813 Cr and ends at the leg
   total −11,878 Cr, because there is effectively no ITM-call OI below spot), and "nearest
   strike to zero net DEX" lands on the **chain's lowest strike**, where net is 0 because
   there is no OI at all. The replacement — **S\***, the re-priced zero-Δ level where
   `Σ Δ_i(S*) × OI_i = 0`, specified to reuse the **ENH-131 / `v_gex_repriced_flip`** code
   path with gamma replaced by delta (`Φ(d1)` / `Φ(d1) − 1`, `Φ(x) = 0.5·erfc(−x/√2)`,
   exact on PostgreSQL 17.6), same `r_sess`, same T convention, same ±10 % / 201-point
   grid, same dte-0 refusal — is **specified and PENDING OPERATOR RULING**. An absent
   column, not a provisional one.

**Limits on how far the numbers may be read, measured and recorded as limits.**
Put–call delta parity fails in the vendor data (`Δ_CE − Δ_PE` measured **0.577–1.281**,
mean 0.816–0.882, against a theoretical ≈1), so a parity gate is recorded as
**mis-specified for this data and dropped, never widened until it passes** (S83).
`|net| ÷ gross` is **9.2–23.7 %**, and substituting the parity-implied put delta moves
`net_dex` by **1.6–2.9×** with the sign unchanged on all four legs. **The magnitude is
indicative, not measured; no gate is built on it**, and four legs of one run is not a
measurement of sign stability.

**Open operator ruling:** whether the book should read the vendor `delta` column or an
in-house Black-Scholes delta from each leg's own `iv`. The view ships on the vendor column
pending that ruling; switching it **reuses the S\* repricer inputs (T, `r_sess`, the dte-0
refusal) and is not a one-line change**.

**Access** (ADR-031 D6): `security_invoker = false`, `REVOKE ALL … FROM anon, authenticated`
then `GRANT SELECT` to `anon` and `merdian_ro`. `authenticated` is revoked because the S92
views left it with ALL (TD-S92-NEW-4). The base table's own `anon = rm` (R01-F8 /
TD-S81-NEW-2) is neither widened nor relied on.

**Artefacts.** `sql/2026-10-09_s93_v_dex_standing_book.sql` (Sections 1→3 apply, Section 4
verifies: 4a anon grain, 4b cost, 4c independent in-SQL recompute, 4d NULL-is-a-gap
(`n_zero_where_gap_c/_p`; its `leg_total_mismatch` and `gap_oi_unaccounted` are labelled
ARITHMETIC SANITY ONLY — identities that cannot fail for a modelling defect, rule 0),
4e WITHDRAWN, 4f chain-side liveness cross-check, 4g
COMMENT `len 7614` / `md5 634428a33305107247c43910c3729669`, 4h ACL, 4i view vs an
independent Python recompute from a live chain export, same `run_id`s — **not** against the
offline expected table, which 4i never reads) ·
`docs/research/s93_priority/p6/P6_dex_design_note.md` ·
`tests/test_dex_recompute.py` (+ `docs/research/s93_priority/p6/expected/`, which is the
offline run's output and is gitignored by `.gitignore:43 *.csv`, so local-only — §7 carry 9).

**Carries:** apply + Section 4; ~~run the offline test after 15:40 IST~~ **run 2026-10-09
17:45:28 IST, PASS (11 ok, 0 failed)** — wiring it into `tests/run_offline.sh` is still
owed; the S\* ruling; the
vendor-vs-BS-delta ruling; the board read (as ADR-025 C7 was measured); and the ADR-015
gloss correction, which is its own change and is not made here.
```

## 3. Register housekeeping owed at splice time

- The register's **Scope** line (`ENH-01 through ENH-139`) advances to **ENH-140**.
- The **S92 Part-7 footer note** quoted above is amended: P6's id is no longer unminted.
- Rule 23 (registers.md) mirror pattern: this is the **Active** block. A **Resolved** block
  is added when the view is applied, Section 4 passes and the board reads it.
- No new ID prefix is introduced, so CLAUDE.md rule 10 does not apply.
