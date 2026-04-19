## 2026-04-19 — code_debug — C-08 breadth writer targets view instead of table

**Goal:** Diagnose why latest_market_breadth_intraday showed stale data from 2026-04-16 10:38 IST and apply fix. V18H_v2 proposed a DDL-based fix (DROP VIEW; CREATE TABLE); validate that plan before applying.

**Session type:** code_debug

**Investigation path:**

1. Queried view definition — found latest_market_breadth_intraday is `SELECT ... FROM market_breadth_intraday ... ORDER BY ts DESC LIMIT 1`. Not a writable object.
2. Queried market_breadth_intraday (underlying table) — 1,371 rows, last write 2026-04-16 05:08:48 UTC, single universe excel_v1.
3. Read ingest_breadth_from_ticks.py — found `.table("latest_market_breadth_intraday").upsert(...)` targeting the view. File header comment confirms it replaced ingest_breadth_intraday_local.py on 2026-04-16.
4. Git log on breadth scripts — commit 4599bb8 "Breadth: retire Dhan REST, add Zerodha WebSocket EQ subscriptions, ingest from market_ticks" is the cutover. Exact date matches the symptom.
5. Confirmed breadth_intraday_history receives writes every 5 minutes on 2026-04-17 at 99.7% coverage — the script runs, computes correctly, and writes one of its two targets fine. Only the view-upsert was silently failing.

**Root cause:** Commit 4599bb8 introduced a writer that targets a view instead of the underlying table. Supabase silently ignores upserts to non-materialised views. market_breadth_intraday was orphaned from its writer at the moment the old Dhan-REST writer was retired.

**Fix applied:** One-line change in ingest_breadth_from_ticks.py —

```python
# BEFORE
sb.table("latest_market_breadth_intraday").upsert(
    payload, on_conflict="universe_id"
).execute()

# AFTER
sb.table("market_breadth_intraday").upsert(
    payload, on_conflict="ts,universe_id"
).execute()
```

Plus two docstring/log-line updates for accuracy.

**Verification:** Saturday (market closed), so ran two direct database tests:

1. Upsert to market_breadth_intraday with test universe_id=c08_test — row landed, no errors. Cleaned up.
2. Upsert to market_breadth_intraday with universe_id=excel_v1 and sentinel universe_count=9999 — view query returned the sentinel row within 30 seconds. Cleanup confirmed. Test row removed.

**V18H_v2 audit-process finding:** V18H_v2's proposed DDL (DROP VIEW; CREATE TABLE latest_market_breadth_intraday with symbol PRIMARY KEY and 6 columns) was incorrect on three counts — the view is the correct abstraction, the primary key should be (ts, universe_id), and the payload has 14 columns not 6. Had it been applied blindly it would have broken the first upsert. Lesson: audit diagnoses should verify write-path and underlying-object freshness, not just consumer symptoms.

**Registry gaps uncovered:** ingest_breadth_from_ticks.py was never added to merdian_reference.json when introduced in 4599bb8. Also tables.breadth_intraday_history was missing. Both added this session. Proposes RESEARCH-OI-16: audit full files section of merdian_reference.json for other post-V18F additions that slipped through.

**Files changed:** ingest_breadth_from_ticks.py (one-line fix + two comment updates), docs/registers/merdian_reference.json (C-08 closed, table entries updated, missing file and table entries added)

**Schema changes:** none

**Open items closed:** C-08 (fully, not provisional)

**Open items added:** RESEARCH-OI-16 proposed (file-registry audit)

**Git commit hash:** (pending — this session)

**Next session goal:** RESEARCH-OI-11 + RESEARCH-OI-12 — remove breadth hard gate, add momentum opposition hard block in build_trade_signal_local.py. Shadow test 5 sessions before live promotion.

**docs_updated:** yes
