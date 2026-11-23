# lookback_v5 PART 2 — wall view identity (Rule 25) and the band parameters

Read-only, via `bin/roq.sh` as `merdian_ro`. Catalog and parameter reads only — no
`hist_*` relation, so no EXPLAIN gate applies.

## (a) Rule 25 identity for `public.v_gex_strike_walls` — **NOT VERIFIED**

### The live measurement (this half succeeded)

```
SELECT length(d), md5(d)
  FROM (SELECT pg_get_viewdef('public.v_gex_strike_walls'::regclass, true) AS d) v;
```

| | value |
|---|---|
| `length` | **4664** |
| `md5` | **`8135c42b4fe3613a676ec7e05af7ee9d`** |

The viewdef text was saved to `out/_live_viewdef.sql` and **re-hashed locally as a
control**: the saved copy measures length 4664 / md5 `8135c42b4fe3613a676ec7e05af7ee9d`,
identical to what the server reported. So the local copy is faithful and any mismatch
below is a real difference, not a transport artefact.

### Why the verdict is NOT VERIFIED, not NO MATCH

Rule 25 asks for the live md5 to be compared against **"the length and md5 the file's
body reproduces"**. *Reproduces* is the operative word: it is the md5 of
`pg_get_viewdef` **after applying the file**, not the md5 of the file's text.
`pg_get_viewdef` returns the parser's deparsed form — it re-qualifies columns, renames
duplicate aliases and inserts `AS` labels — so a hand-written `sql/` file can never
hash equal to it by direct text comparison, however correct the file is.

Establishing "this file reproduces this object" therefore requires **applying the file
and re-dumping**, which is a database write. This task forbids writes. Hence:

> **NOT VERIFIED — reason: the Rule 25 comparison requires a `pg_get_viewdef` capture
> of the file's body, which can only be produced by applying the file (a write). No
> such capture exists in `sql/`. The live identity is recorded above; the file side of
> the equality is unavailable under read-only constraints.**

This is a property of the artefact, not of this session: **`sql/2026-09-15_s79_v_gex_strike_walls.sql`
stores hand-written SQL, not a deparsed capture, so Rule 25 is not executable against
it read-only.** That is the same gap TD-S81-NEW-5 records for this view family — a
`sql/` file that carries only the view body is not a verifiable rebuild source.

### Supporting structural comparison — evidence, explicitly NOT identity

Compared the live viewdef against the file body (`sql/2026-09-15_s79_v_gex_strike_walls.sql`
lines **48–199**, the `CREATE OR REPLACE VIEW … AS` body through its `;`):

| | raw length | raw md5 |
|---|---|---|
| live `pg_get_viewdef` | 4664 | `8135c42b4fe3613a676ec7e05af7ee9d` |
| file body, as written | 7492 | `2d393198e333382f203fe24cbfe70da1` |

Raw text differs, as expected. On a token comparison (comments stripped, lowercased):

- live **934** tokens, file **849** tokens, **800 matching = 85.65 %** of live
- differing tokens by kind: **30 alias suffixes** (`g` → `g_1`), **6 added `AS`
  labels**, **115 "other"** — and the "other" bucket is dominated by live's added
  `scoped.` table qualifications, visible in the first six diff hunks, all of the form
  live `scoped .` against file *nothing*.

Every difference inspected is a deparse artefact. **No difference in a predicate, a
column, a filter or an aggregate was found.** First divergence, at normalised character
36, is representative:

```
live: with recursive symbols as ( select ( select min(g_1.symbol) as min from gex_strike_snapshots g_1) as symbol union all …
file: with recursive symbols as ( select (select min(g.symbol)      from gex_strike_snapshots g)   as symbol union all …
```

So the file is **consistent with** being the source of the live view, and nothing
contradicts it. That is weaker than Rule 25 and is recorded as weaker: a marker check,
a matching comment or "the newest file" is exactly what Rule 25 forbids relying on, and
an 85.65 % token match is the same class of evidence.

**Unchanged from `lookback_v4/walls.md`:** `public.latest_gamma_walls` appears in the
S104 grant lists (`sql/2026-11-03_s104_anon_shrink_ROLLBACK.sql:102`) and has **no
definition anywhere in `sql/`**.

## (b) Band parameters — both readable, both 1.5

```
SELECT get_parameter_num('wall.band.NIFTY'), get_parameter_num('wall.band.SENSEX');
```

| parameter | value |
|---|---|
| `wall.band.NIFTY` | **1.5** |
| `wall.band.SENSEX` | **1.5** |

Neither is NULL and both are readable by `merdian_ro`. Read through
`get_parameter_num`, the same function the view itself calls at
`sql/2026-09-15_s79_v_gex_strike_walls.sql:114`, so these are the values the view sees.

Both equal the view's hardcoded `COALESCE` fallback of 1.5, so **the live band would be
1.5 whether or not these rows existed** — this read cannot distinguish "parameter set
to 1.5" from "parameter absent, fallback used". What it does establish is that the rows
are present and readable, so a future change to either row would take effect.
