# P5 (PPC-1) — the previous-close OI baseline: measurements, ruling, build (S95, 2026-10-11)

**Status: AUTHORED, NOT APPLIED.** `sql/2026-10-11_s95_v_oi_since_preopen.sql`. Roadmap §2.1 **P5**,
released by S94-G. Parked as PPC-1 at S89 (`docs/research/post_parity_candidates.md`); feeds **P7**
(the flow leg, ENH-98 D-4). Not a parity layer; display-only (S37).

## 1. What was measured first (read-only, `bin/roq.sh`, 2026-10-11 13:52–14:44 IST)

Probe files are in this directory; outputs stay on the box (`~/p5_probe/*.out`).

| probe | md5 as run | what it measured |
|---|---|---|
| `p5_probe1.sql` | `502d3583` | per open session 2026-08-25 → 10-09, per symbol: first row, 09:15 row, last row before the session (naive, and skipping `is_open = false` dates), and leg-by-leg OI of the previous close vs the pre-open row and vs the 09:15 row, front expiry |
| `p5_probe2.sql` | `ed1ff2a5` | `EXPLAIN (ANALYZE)` of the previous-close seek |
| `p5_probe3.sql` | `368d8941` | `trading_calendar` 10-12 → 10-23 (check owed, TD-S91-NEW-13) |
| `p5_drill.sql` | `cf51beaf` | the two SENSEX outliers, leg by leg, 15:00 → next 10:00 |
| `p5_untraded.sql` | `000b7c5d` | legs with volume 0 all session: share of front OI and DEX gross, 09-24 → 10-09 |

**Findings.** 26 comparable changeovers per symbol (excluded: the retention edge 08-24/25, which holds
one 15:30 row a day, and post-expiry days before 09-23, when the new front was not captured at the
previous close).

1. **NIFTY: the pre-open row equals the previous 15:40 close on every leg, 26 / 26.** The 09:15 row
   differs from both on 111–190 legs a day.
2. **SENSEX: the pre-open row differs from the 15:40 close on 23.4–41.5 % of legs on 25 / 25 normal
   changeovers** (BSE revises OI after the close). S81's 09-22 figure (134 / 392, max 8,180) reproduced
   exactly.
3. **2026-10-02 (holiday) has no `trading_calendar` row** and wrote a full day of chain rows, so the
   `is_open = false` guard never fired: Monday 10-05's "previous close" was the holiday's 15:40 row on
   both symbols. The same gap as the missing September weekend rows.
4. **Anchor cost:** index-only scan on `idx_ocs_ts_symbol_expiry`, **0.177 ms**, 16 buffers — against
   **25,117 ms** for `v_oi_prev_close_snapshots` (S89).
5. **Untraded legs carry vendor OI that is not a measurement.** Deep in-the-money SENSEX calls
   (68,200–71,800, spot ~73,000) with volume 0, a frozen LTP and `oi_change = oi` on every row:
   71,800 CE read 48,846,820 all of 09-25 afternoon, 120 at the 09-28 pre-open and 20 at its first
   trade (09:55); 68,200 / 69,300 / 69,400 CE read 0, then ~1.84 million on 09-28 and 09-29, then 0.
   On **SENSEX 09-25, 09-28 and 09-29** legs with no volume held **94.4 / 85.5 / 33.3 %** of front OI and
   **98.2 / 95.6 / 72.9 %** of DEX gross; on every other symbol-session of 22, ≤ 0.16 % and ≤ 0.50 %.
   **No untraded leg changed OI between 09:15 and the close on any of the 22.** It inflates every
   reader of OI levels (DEX book, GEX, max pain) for the whole session. The S\* out-of-sample SENSEX
   arms read 0.03 % (10-07) and 0.50 % (10-09) of DEX gross on untraded legs; the L3 SENSEX arms
   (09-22, 09-23) predate this probe's window and were **not measured**.
6. **Check owed, read half done:** `trading_calendar` holds **2026-10-20 `is_open = false`, Dussehra**
   (S90 belt); weekend rows present going forward. The live-day half waits for 10-20.

## 2. Ruling S95-B (operator, 2026-10-11 14:37 IST)

- **A1 — the baseline is the session's pre-open row**: the first snapshot of the session date in the
  front expiry, **refused if stamped at or after 09:15 IST** (absence, never a fallback). It is the
  previous close on NIFTY (finding 1), BSE's overnight-revised figure on SENSEX (finding 2), and it
  reads only the session's own rows, so finding 3 cannot reach it.
- **B — a view**, as L13 is. No writer, no new process.
- **C — front expiry only**, as L13 and the DEX book.
- After the drill (finding 5): **no anchor guard.** The bad values persist across whole sessions, so a
  guard on the anchor row could not catch them.

## 3. The build

`v_oi_since_preopen` is **L13 (`v_oi_rotation_since_open`) with exactly these changes** — the view
name, the anchored CTE, and the freshness key `oi_preopen.stale_floor_min` (a separate key, ADR-023
A1.2; unset, so the default 30 applies):

```diff
--- v_oi_rotation_since_open (L13 Section 1)
+++ v_oi_since_preopen (P5 Section 1)
@@ -1,4 +1,4 @@
-CREATE OR REPLACE VIEW public.v_oi_rotation_since_open AS
+CREATE OR REPLACE VIEW public.v_oi_since_preopen AS
 WITH RECURSIVE symbols AS (
         -- S72 FIX 2 skip scan. Symbols derived, never a literal list.
         SELECT (SELECT min(o.symbol) FROM option_chain_snapshots o) AS symbol
@@ -37,10 +37,11 @@
            AND o.expiry_date >= (l.latest_ts AT TIME ZONE 'Asia/Kolkata')::date
          GROUP BY l.symbol, l.latest_ts
      ), anchored AS (
-        -- First snapshot at or after 09:15 IST on the SESSION date, in the
-        -- front expiry. CROSS JOIN LATERAL, so a session with no 09:15
-        -- snapshot yet yields no row for that symbol: absence, never a
-        -- fallback to the pre-open row.
+        -- S95-B: the FIRST snapshot of the SESSION date in the front expiry --
+        -- the pre-open row, 08:30-08:40 IST -- and it must be stamped BEFORE
+        -- 09:15 IST. A session whose first row is at or after 09:15 (a late
+        -- start, a thinned retention day) has no pre-open anchor and yields NO
+        -- ROW for that symbol: absence, never a fallback to a later row.
         SELECT f.symbol, f.latest_ts, f.session_date, f.expiry_date,
                a.ts AS anchor_ts
           FROM front f
@@ -49,11 +50,12 @@
                  FROM option_chain_snapshots o
                 WHERE o.symbol = f.symbol
                   AND o.expiry_date = f.expiry_date
-                  AND o.ts >= ((f.session_date + time '09:15') AT TIME ZONE 'Asia/Kolkata')
+                  AND o.ts >= ((f.session_date + time '00:00') AT TIME ZONE 'Asia/Kolkata')
                   AND o.ts <= f.latest_ts
                 ORDER BY o.ts
                 LIMIT 1
           ) a
+         WHERE a.ts < ((f.session_date + time '09:15') AT TIME ZONE 'Asia/Kolkata')
      ), a_rows AS (
         SELECT k.symbol, k.expiry_date, o.strike, o.option_type, o.oi
           FROM anchored k
@@ -122,9 +124,9 @@
     END AS pe_presence,
 
     round(EXTRACT(epoch FROM (now() - k.latest_ts)) / 60.0, 1) AS snapshot_age_min,
-    COALESCE(get_parameter_num('rotation.stale_floor_min'), 30)  AS stale_floor_min_used,
+    COALESCE(get_parameter_num('oi_preopen.stale_floor_min'), 30)  AS stale_floor_min_used,
     (EXTRACT(epoch FROM (now() - k.latest_ts)) / 60.0)
-        <= COALESCE(get_parameter_num('rotation.stale_floor_min'), 30) AS is_fresh
+        <= COALESCE(get_parameter_num('oi_preopen.stale_floor_min'), 30) AS is_fresh
   FROM pivoted p
   JOIN anchored k
     ON k.symbol = p.symbol AND k.expiry_date = p.expiry_date;
```

COMMENT: 3,118 characters, md5 `0b0676edfb6b0086ff328e5438312112`. Privileges: `REVOKE ALL FROM
anon, authenticated; GRANT SELECT TO anon, merdian_ro`. The apply batch ends with its own
verification SELECT (TD-S94-NEW-3).

## 4. Tested before commit (local PostgreSQL 16, hand-built data — machinery only)

Data: a SENSEX session 10-01, a **holiday with rows** on 10-02, a session 10-05 with a pre-open row
(08:40, strike 200 revised +40), a 09:15 row (strike 100 +290) and a 15:40 row, plus an expired
contract that must not be read. Expected values computed by hand before running.

| check | expected | got |
|---|---|---|
| anchor | 10-05 08:40 | 10-05 08:40 |
| deltas, strike 100 / 200, CE and PE | +390 / +390, +50 / +50, all `BOTH` | same |
| front expiry | 10-06 (not the expired 10-01) | 10-06 |
| refusal: delete the 08:40 row | 0 rows | 0 rows |
| batch verification SELECT | 3118 / `0b0676ed…`, anon r, no write, merdian_ro r, authenticated none | same |
| 4b independent recompute | 0 / 0, n 2 = 2 | 0 / 0, 2 = 2 |
| 4c invariants | all 0 | all 0 |
| 4d anchor vs previous close | *not predicted; checked by hand after the run:* the holiday rows, \|1,010 − 9,999\| = 8,989 | 4 compared, 4 differ, max 8,989 |
| 4e anon path | `role_now anon`, n 2 | same |
| **mutant M1** — L13's 09:15 anchor | 4b fails | **2 / 2** |
| **mutant M2** — refusal clause removed, pre-open row missing | 4b fails | **2 / 0**, n 2 vs 0 |

**4d's expected values on the live database were measured before the view existed** (probe 1,
session 10-09): NIFTY 472 compared / 0 differ; SENSEX 390 / 102 / max 8,420. They hold only while the
view's session is 2026-10-09, so 4d is run before 08:30 IST Monday 10-12.

## 5. What this does not show

The view is a baseline and a difference, not a classification: an OI delta cannot tell writing from
buying, and P7 (flow vs book) is not built. The untraded-leg defect (finding 5) is filed separately; this
view does not repair it. 26 changeovers per symbol is what retention holds (oldest chain row 2026-08-24).
