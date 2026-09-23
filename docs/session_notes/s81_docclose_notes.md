# S81 doc-close notes (running)

## Guard half (closed)
- TD-S80-NEW-18: bin/disk_guard.sh shipped 9a5114e, scheduled 51af3d8.
  Crontab 53 -> 59 lines, 15 02 * * * daily. Alert proven on 3 branches
  (blocks WARN/CRIT + inodes WARN via loopback fs). First scheduled run
  2026-09-23 02:15 UTC - NOT YET OBSERVED at time of writing.
  MOVE HEADING *AND* STATUS ROW TOGETHER (TD-S80-NEW-19 shape).
- Gotcha for a TD or the runbook: `crontab <file>` truncates the filename
  at ~100 chars (Debian crontab.c MAX_FNAME). Scratchpad paths exceed it;
  first install failed harmlessly on a truncated path. Use `crontab - < file`.

## New TDs to file
- FINDING A: ~/redeploy_marketview.sh has SRC_DIR=~/merdian-marketview
  (stale May-27 clone, 14b63f3). Live /var/www/marketview is md5-identical
  to ~/meridian-connect/dist (7b60d01, Jul-12). Register S40 footer already
  names ~/meridian-connect canonical. Script points at the wrong tree.
  S72 flat-namespace shape.
- FINDING B: a THIRD strike scalar. Client-side maxGammaStrike (argmax of
  POSITIVE gex_cr, ADR-024 Amd A) renders under three labels today:
  "MAX g" (SnapshotStrip), "Max g Strike" (KeyParameters), "strongest
  dampen" (PositioningSection scalar row). Pre-existing ADR-017 P1
  redundancy violation; compounds TD-S79-NEW-13. S81 Lovable prompt
  collapses all three to "NET-LONG g STRIKE" (label-only, ADR-024's own
  "naming, not code" remedy).

## sql/-vs-database divergence — runs BOTH ways (TD-S79-NEW-3 shape)
Measured S81 on all three S79 GEX views:
  | layer            | in sql/          | in database |
  | view bodies      | present          | present, MATCH (semantic, 3/3) |
  | COMMENT ON VIEW  | present (3/3)    | ABSENT (3/3) at S81 open |
  | GRANT SELECT anon| COMMENTED OUT 3/3| PRESENT 3/3 (exactly SELECT) |
- A rebuild from sql/ yields views correct in body, better documented than
  live, and ANON-INACCESSIBLE -> three panels at HTTP 200 with zero rows,
  i.e. the TD-S37-03 silent-empty-dataset shape.
- Bears on ADR-025 D2 clause 4: "DDL committed under sql/" is met in
  letter, and sql/ is NOT a true rebuild source. S81's own SQL file
  inherits the grants half of the defect (comments only).
- RESIDUAL AFTER S81: v_gex_abs_exposure's S79 comment
  (sql/2026-09-15_s79_v_gex_abs_exposure.sql:145-146) STILL UNAPPLIED.
  The grants half is unfixed on all three by instruction.
- Root cause of the missing comments: the S79 apply ran Section 1 per view
  and never ran the COMMENT statements. Wider than TD-S79-NEW-13, which
  assumed the sentence was unwritten rather than the file part-run.

## Applied S81
- dc2e6b5 sql/2026-09-22_s81_comment_on_view_strike_disambiguation.sql
- Both COMMENT ON VIEW applied live. Stored lengths: walls 1449,
  concentration 1951. My published expectation of 1451 for walls was taken
  from the source literal and double-counted the two '' escapes; stored =
  literal - 2. Operator diagnosed it.

## Measured 2026-09-22 08:15 UTC (design evidence, keep)
- NIFTY dte 0, SENSEX dte 2 -> live proof that P6 salience must key on
  DTE+sigma not symbol (TD-S79-NEW-11).
- call_wall == top_strike_net on BOTH symbols (23400 / 75000).
- coverage: NIFTY 64/96 = 66.7%, SENSEX 110/154 = 71.4% -> a SENSEX-keyed
  partial-chain badge would have fired on the LESS affected panel
  (TD-S79-NEW-8 correction, live).
- NIFTY sigma 215.51 at dte 0 with ~105/375 min left -> TD-S79-NEW-1
  overstatement ~1.9x, live, in the deployed view body.

## ADR-025 Amendment B (operator decision, S81)
- Presentation of the parity layers is DEFERRED until all fourteen carry a
  disposition. Trigger for rendering = full dispositional coverage, not
  "a layer is BUILT".
- Rationale (operator): on Hedgewall most layers only make sense IN
  COMPARISON with each other, so the board must be designed as a whole.
- This REVERSES part of ADR-025 Consequences, which said "the board
  reorders immediately to rendering". Record as a reversal, not a gloss.
- Consequence for D2 clause 3 ("visible on at least one operator
  surface"): BUILT count stays 2 of 14 for now BY DECISION. ENH-120/121/
  122 remain PENDING on clause 3 only. This is a deliberate hold, not a
  lapse, and must be written so a later reader cannot mistake it for one.
- Remaining parity build is DAYS, not weeks: spec section 3 ~= 5 working
  days, and that is a FLOOR. Do not restate it as weeks.
- Only genuine clock: L9 at NIFTY depth 4 needs one week of ENH-99
  telemetry. A FIRST L9 build does not need it.

## Carried for reuse (do NOT rebuild from scratch)
- S81 STEP 3 design for ENH-120/121/122 on Positioning: OI Corridor tile
  in KeyParametersSection; gross g scalar folded into NetDealerGammaSection;
  new GammaSharpnessSection; field cuts; corridor_state/iv_fresh silence
  rules; dte=0 sigma line (display-only, never rescaling); three-axis
  strike naming (CALL/PUT OI WALL, g-CONC STRIKE, NET-LONG g STRIKE);
  coincidence rendered with a plain "=" token and NO P4 styling; P6
  salience DEFERRED to ENH-110 Phase 3, uniform weight; run-deduped
  sparkline buffer (>=3 distinct ts).
- The full paste-ready Lovable prompt was drafted and NOT run. It is in
  the S81 transcript. Reuse it when the board is designed as a whole;
  re-check it against the then-current sections.tsx before running.

## ENH-125 v_gex_strike_rank (L12 ranked leg) - commit 4fcd740
- REGISTER ENTRY OWED. Next free id was ENH-125 (ENH-124 highest filed;
  ENH-118/119 cited-but-never-filed per the register Rule 5 residual -
  consumed, not reusable).
- L12 now has BOTH legs computing: HHI (ENH-122) + ranked (ENH-125).
- Also satisfies parity spec 2.5 L15 "Absolute Gamma Strike"
  (strike_rank=1) and "Large Gamma Strike, ranked" (1..N). Per ADR-025 D5
  an extension does NOT count toward parity -> counts as L12 only.
- ADR-025 D2 status: clause 1 MET (output read), clause 2 MET (EXPLAIN
  11.8 ms exec / 12.2 ms plan, 618 shared hit / 7 read, no Seq Scan on
  gex_strike_snapshots, 251 scoped -> 84 removed by gex_cr<>0 -> 167
  ranked), clause 4 MET (sql/2026-09-22_s81_v_gex_strike_rank.sql).
  CLAUSE 3 PENDING BY DECISION under Amendment B. Write it as a
  deliberate hold; a later reader must not read it as a lapse.
- FIRST object today for which sql/ == database including COMMENT and
  GRANT. Sections 2 and 3 shipped as LIVE statements for that reason.

### Plan-shape note (record, do NOT fix)
- The volatility_snapshots LEFT JOIN LATERAL in the sig CTE runs
  loops=167 - once per ranked ROW, not once per run. The planner pushed
  it below the join with ranked. 0.019 ms/loop, 501 buffer hits: trivial
  at this grain, but it scales with STRIKE count, not SYMBOL count.
  Revisit if strike counts grow or if a history object replays many runs.

### Two observations for the ENH-125 entry (observations, NOT findings)
- (a) Every DAMPENING row sits above spot and every AMPLIFYING row below,
  on both symbols. That is ADR-024 Amendment A's OI-imbalance arithmetic
  made visible per row - the tautology the abs-rank design exists to
  EXPOSE rather than hide. It is not evidence of dealer behaviour.
- (b) NIFTY coverage fell 64/96 (08:15) -> 56/96 (~14:35) -> 60/96
  (14:41) on its expiry day: the TD-S79-NEW-8 DTE effect moving live
  intraday. NIFTY concentration extreme - top 5 hold 72.6% of the |gex|
  book vs SENSEX 37.9%.

### METHOD NOTE - pairing counts across a latest-run-scoped view
- The anon/editor count pairing gave NIFTY 56 (editor) vs 60 (anon) and
  SENSEX 111 vs 111. NOT a defect: a new GEX run landed between the two
  reads (~5 min writer cadence). Confirmed by reading v_gex_concentration
  on the same run - n_contributing=60/96, hhi_net=0.2017,
  top_strike_net=23450, exactly matching the rank view's 60 / 0.2017 /
  23450. SENSEX paired only because its count happened to be stable
  across the run boundary.
- GENERALISE: for a LATEST-RUN-SCOPED view, a count pairing between two
  reads taken minutes apart is NOT a stable check - it can fail for a
  reason other than the one it names (run rollover), i.e. a FALSE ALARM
  where Rule 0 usually warns about the opposite. The stable form is to
  fetch ts alongside the count and compare counts ONLY when ts matches.
  Apply this to any future anon/editor pairing on the GEX view family.

## TD-S80-NEW-10 expiry half (v_max_pain_by_strike)
- NEW FINDING, fourth divergence shape today and the worst:
  sql/v_max_pain_by_strike.sql HAS NEVER EXISTED. Absent from disk,
  `git log --all` for the path is EMPTY, only max-pain DDL in the repo is
  ENH-123's. The Enhancement Register S40 footer claim "1 new SQL file
  (sql/v_max_pain_by_strike.sql)" is FALSE, and TD-S80-NEW-10's own
  Component row cites the same non-existent path. The object has lived in
  the live database only since S40 -> exactly ADR-025 D2 clause 4's
  "one DROP from unrecoverable". It also has NO ENH register entry.
- Remedied in part: captured baseline committed cebcc03 as
  sql/2026-09-22_s81_v_max_pain_by_strike_CAPTURED_BASELINE.sql
  (pg_get_viewdef verbatim, pre-change, so the fix lands as a diff).
- FIVE defects found in the live body, all recorded in that file's header:
  (1) no expiry filter -> per-strike max() mixture across expiries;
  (2) no ts + unbounded max(ts), no recency floor;
  (3) max_pain tie-break NON-DETERMINISTIC - row_number() ORDER BY
      total_pain with no tie-break column; ENH-123 orders by
      (total_pain, candidate_strike). OUT OF APPROVED SCOPE for the S81
      fix -> OWED AS ITS OWN TD. One-line correction.
  (4) `strikes` CTE is a structural no-op;
  (5) latest_ts = max(ts) GROUP BY symbol over the whole table, the
      S72 FIX 2 cost shape. Left unchanged by instruction; EXPLAIN
      reported in the fix file's Section 4a.
- ANON HELD ALL SEVEN PRIVILEGES on this view, has_comment false. This is
  the S39 Lovable ALL-grants shape on an S40 object created AFTER the S39
  13-surface REVOKE cleanup => D.21.1 IS A LIVE REGRESSION, not a closed
  item. Exposure was LOW and must be stated as such: not auto-updatable
  (GROUP BY + aggregates + joins) so INSERT/UPDATE/DELETE fail, TRUNCATE
  does not apply to views, REFERENCES/TRIGGER need DDL that PostgREST
  never issues. Grant set wrong; not an open door.
- SCHEMA-WIDE anon audit query is owed a run; record count + list here as
  the D.21.1 regression item.
- merdian_reference.json records NO schema for option_chain_snapshots.

### The multi-expiry path is UNTESTABLE TODAY - owned by L9 stage 1
- The S81 same-statement EXCEPT check proves NO REGRESSION on today's
  data (one expiry per cycle, measured across 2,923 cycles). It CANNOT
  prove the filter behaves correctly once a second expiry appears, which
  is the only condition the filter exists for.
- OWNER: TD-S80-NEW-1 stage 1 verification. On the FIRST stage-1 day, once
  a snapshot carries two expiries:
    (a) compare v_max_pain_by_strike output against the same computation
        restricted BY HAND to W1 -> EXPECT IDENTICAL ROWS;
    (b) run the CAPTURED BASELINE body against that same snapshot ->
        EXPECT IT TO DIFFER (the max() mixture).
  (b) is the load-bearing half: without it (a) passes even if the filter
  does nothing. Two expiries present is the precondition; do not run this
  on a single-expiry snapshot, where both arms agree trivially.
- Stage 1 does NOT run 2026-09-22: NIFTY is on expiry.

## [S1 SECURITY] anon role held full write privileges on 211 public relations; live Dhan token readable via system_config
Discovered and remediated 2026-09-22 (Session 81), mid-session, ahead of
the v_max_pain_by_strike work. File as an INCIDENT, not a TD.

### Measured (before remediation)
- 211 public relations where anon held privileges beyond SELECT.
- 100+ tables with RLS OFF and anon INSERT/UPDATE/DELETE. (The listing was
  truncated at 100; 211 is the privilege-level count.)
- 11 auto-updatable views - writes pass through to base tables.
- dhan_auth_tokens: RLS off, 0 policies, anon SELECT/INSERT/UPDATE/DELETE.
- system_config: anon-readable, INCLUDING config_value where
  config_key='dhan_api_token'. THIS IS THE LIVE BROKER TOKEN. Confirmed by
  reading pull_token_from_supabase.py:176 - the operational token is NOT
  in dhan_auth_tokens, which no .py in the tree references at all.
- anon key is public by design (Marketview bundle + public
  meridian-connect repo, D.21.2).

### Root cause
- Supabase DEFAULT PRIVILEGES grant anon ALL on new objects in public.
- S39's 13-surface REVOKE fixed the objects that existed THEN. Every
  object created afterwards came up with ALL again - v_max_pain_by_strike
  (S40) measured at all seven privileges today is the proof.
- D.21.1 was recorded "remediated" but was never closed AT THE MECHANISM,
  only at the instances. Same shape as TD-S69-NEW-1: a resolved item has
  no watcher.
- D.21.2's trust model - "the security boundary is the RLS policy + GRANT
  pair, not key secrecy" - was FALSE for every table with RLS OFF. With no
  RLS there is no policy to filter, so the GRANT alone was the boundary,
  and the GRANT was ALL.

### Fix applied (operator, verified in database)
1. REVOKE ALL ON system_config, dhan_auth_tokens FROM anon, authenticated
2. REVOKE INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER
     ON ALL TABLES IN SCHEMA public FROM anon, authenticated
3. ALTER DEFAULT PRIVILEGES FOR ROLE postgres ... same set
   (3 is what stops it regressing - it closes the MECHANISM, which is
    what S39 did not do)
Editor verify: relations_with_anon_non_select = 0; anon_select false on
both token tables.

### Verified through the real anon path (S81, value-free probes)
- system_config -> HTTP 401. dhan_auth_tokens -> HTTP 401.
- POST {} to breadth_ingest_state -> HTTP 401, pg_code 42501.
- 22 of 23 frontend relations -> HTTP 206 with healthy row counts.
- v_dealer_flow_sim -> 500/57014 UNFILTERED, 200 in 0.44s when filtered by
  symbol as the frontend actually calls it. PRE-EXISTING, not caused by the
  revoke. See separate finding below.
- Marketview is unaffected.

### Production dependency census (read-only, before the revoke)
- No production write path depends on anon. Every one of 80
  SUPABASE_ANON_KEY references across 47 files is a FALLBACK after
  SUPABASE_SERVICE_ROLE_KEY ("or ANON", or a candidate list with anon
  last; canonical_ict_recall.py:156 comments "# last resort").
- SUPABASE_KEY (344 refs) is NOT an env var - a local alias bound from
  SUPABASE_SERVICE_ROLE_KEY in 95 of 98 sites.
- Dhan token path is service-role END TO END: refresh_dhan_token.py and
  refresh_dhan_token_aws.py both SUPABASE_SERVICE_ROLE_KEY only;
  dhan_token_refresh_lib.py references no Supabase key at all;
  pull_token_from_supabase.py:160 service-role.
- Frontend has ZERO .insert/.update/.delete/.upsert. One RPC,
  update_parameter, SECURITY DEFINER, unaffected by table grants.

### OWED
(a) Supabase API log review for anon reads of system_config and anon
    writes over the exposure window. The window opens no later than S40
    for v_max_pain_by_strike and plausibly at project creation for the
    tables with RLS off.
(b) DHAN TOKEN ROTATION DECISION. The live token was readable by anyone
    holding the public anon key for an unbounded period. Treat as
    potentially disclosed until (a) says otherwise.
(c) Restrict anon SELECT to the frontend's 23 relations. capital_tracker,
    app_settings and others remain anon-readable and are not consumed.
(d) BEHAVIOUR CHANGE, expected and correct: a script with an empty
    SUPABASE_SERVICE_ROLE_KEY no longer degrades silently to anon - it now
    fails loudly. The fix when it surfaces is to SUPPLY THE KEY, never to
    restore the grant. Expect rarely-run backfill / canonical_* scripts to
    surface first.
(e) STANDING CHECK, because a resolved item has no watcher: a daily query
    asserting relations_with_anon_non_select = 0, wired into the
    disk_guard Telegram path (bin/disk_guard.sh, S81) or eod_health_check.
    Without it, item 3 of the fix is trusted rather than verified.

### Separate finding surfaced by the verification
- v_dealer_flow_sim (ENH-81, S37) is the THIRD sibling that ADR-021's
  latest-run scoping never covered. S69 scoped v_gex_strike_pin_zone and
  v_gex_strike_accel_zone; this one was left unbounded and now returns
  57014 on any unfiltered read. The frontend escapes it only because
  useDealerFlow filters by symbol first. Same cost shape, same fix.
  OWED AS ITS OWN TD.

## TD-S80-NEW-10 expiry half: DONE (commit b1bb829)
- Applied and verified live. Sections 1/2/3a/3b all succeeded.
- 4b INERTNESS: old_minus_new = 0, new_minus_old = 0; NIFTY 236/236,
  SENSEX 196/196. Run as ONE statement so both bodies read the same
  transaction snapshot.
- 4c anon: SELECT only. 4d comment: 4123 chars.
- sql/ == database for this object including COMMENT and GRANT. Second
  such object today (after ENH-125). Baseline at cebcc03, fix at b1bb829,
  so the change is a reviewable diff rather than an assertion.
- L9 STAGE 1 PRECONDITION IS MET. Stage 1 can run on the next NON-EXPIRY
  day (not 2026-09-22; NIFTY was on expiry). The two-armed multi-expiry
  test is already assigned to TD-S80-NEW-1 stage 1 above - do not lose the
  second arm (baseline must DIFFER), it is the load-bearing half.

### NEW TD OWED - S2 WITH A CLOCK
v_max_pain_by_strike.latest_ts full-index-scans option_chain_snapshots;
the view crosses the PostgREST 8 s ceiling in roughly four weeks

- MEASURED 2026-09-22 (4a, cold cache): total 3396 ms, planning 3.4 ms.
  latest_ts alone = 3260 ms: Index Only Scan on idx_ocs_ts_symbol_expiry
  over ALL 1,336,714 rows, Heap Fetches 145,354, shared read 14,240 /
  written 3,191. NOT a seq scan - a full-index scan, which is cheaper but
  still O(table). The rest of the view is cheap and BOUNDED: front_expiry
  2.8 ms, chain 432 rows on the latest ts, pain 113 ms.
- PROJECTION - AN ESTIMATE, and here is how it was derived. Only the
  latest_ts term scales with table size; the remaining ~136 ms is fixed.
  Solving 3260*k + 136 = 8000 gives k = 2.41, i.e. ~3.22M rows. That is
  ~1.89M rows of growth from today's 1,336,714. jobid 19 (the OCS thinning
  job) is DISABLED per TD-S76-NEW-2, so the table grows ~68k rows/day,
  giving ~28 days. ASSUMPTIONS: linear scaling in row count, cold cache,
  constant growth rate, no index change. A warm cache is much faster, so
  the failure will present INTERMITTENTLY first - cold reads failing while
  warm ones pass, which is harder to diagnose than a clean break.
- CONSEQUENCE WHEN IT FIRES: 57014, and the live Marketview Max Pain page
  empties silently. This is the ADR-021 failure mode exactly - the same
  shape that emptied the Pine overlay for weeks at S69.
- FIX: replace latest_ts with the S72 FIX 2 recursive symbol skip-scan +
  CROSS JOIN LATERAL latest-ts probe. ENH-123 and ENH-125 already use it;
  this is the last max-pain object that does not. Separate change,
  separate decision - deliberately NOT bundled into the expiry fix.
- RELATED: v_dealer_flow_sim has the same untreated shape (see the
  security incident section). Two ENH-81-era objects now carry it.

### NEW TD OWED - max_pain tie-break is non-deterministic
- v_max_pain_by_strike.max_pain uses
  row_number() OVER (PARTITION BY symbol, expiry_date ORDER BY total_pain)
  with NO tie-break column, so equal total_pain yields an arbitrary
  winner. ENH-123 orders by (total_pain, candidate_strike).
- Present in the S40 baseline and CARRIED UNCHANGED through the S81 fix by
  instruction: correcting it is one line but was outside the approved
  scope, and it is a semantic change to a view the frozen Marketview
  reads. Reported rather than altered silently.
- Ties in real OI-weighted pain are near-impossible, so this is latent,
  not live. It is recorded because the S81 fix registered this object's
  DDL for the first time, and shipping known non-determinism in a
  first-ever canonical DDL without writing it down is how defects become
  invisible.

## L14 source measurement (S81) - coverage, holes, and the unit bridge that does not exist

### Measured coverage
| source | span | days/symbol |
|---|---|---|
| hist_gamma_metrics | 2025-04-01 -> 2026-03-30 | 244 |
| gamma_metrics | NIFTY 2026-06-12, SENSEX 2026-06-10 -> 09-22 | 72 / 74 |
| gex_strike_snapshots | 2026-05-25 -> 09-22 | NIFTY 81 / SENSEX 82 |

### 3a RETURNED ZERO ROWS: hist_gamma_metrics and gamma_metrics DO NOT OVERLAP
- hist ends 2026-03-30; gamma_metrics starts 2026-06-10/12. The x1e7 unit
  bridge between the two eras is therefore **UNVERIFIED and unverifiable
  from these two tables alone**. This is the TD-S30-CANDIDATE-1 trap
  (seven sessions lost to a unit-convention misdiagnosis) sitting
  unexercised. Any future stitch across 2026-03-30 MUST establish the
  ratio empirically first, on a third source that overlaps both.
- 3b matched 1,731 runs at ratio 1.0 exactly - join and grain are sound,
  but it is BY CONSTRUCTION (same signed_gamma_exposure output) and
  verifies no unit. 3c found no unit step inside gamma_metrics
  (monthly median |net_gex| stable Jun-Sep: NIFTY 1.1-1.7M, SENSEX
  0.46-0.59M).

### WHY gamma_metrics STARTS 2026-06-10/12 - it is a retention artefact
90 days before 2026-09-09 (when jobid 19 was disabled, TD-S76-NEW-2) is
2026-06-11. The last cleanup deleted everything older, and nothing has
been deleted since. **The start date records when the janitor stopped,
not when data began.** Consequence: the window keeps growing now, and
SNAPS BACK to 90 days the moment jobid 19 is re-enabled. A 30-session
panel (~42 calendar days) survives that reversal; a 299-day panel would
not, and would become the thing blocking the reversal.

### GAP CLASSIFICATION against trading_calendar (Rule 18 applied)
trading_calendar spans **2026-03-25 -> 2027-01-29 only**. It cannot
classify any 2025 date, nor 2026-03-10. Those gaps are UNCLASSIFIABLE by
this calendar, not "holidays".

| date | dow | calendar | independent evidence | verdict |
|---|---|---|---|---|
| 2025-04-23 | - | NO ROW (out of span) | - | UNCLASSIFIABLE |
| 2025-04-28 | - | NO ROW (out of span) | - | UNCLASSIFIABLE |
| 2025-06-05 | - | NO ROW (out of span) | - | UNCLASSIFIABLE |
| 2026-03-10 | - | NO ROW (out of span) | - | UNCLASSIFIABLE |
| 2026-05-28 | Thu | **NO ROW, inside span** | markers 0, signals 0 | see below |
| 2026-06-03 | Wed | is_open=true | markers 2, signals 0 | **REAL HOLE (GSS)** |
| 2026-06-04 | Thu | is_open=true | markers 2, signals 0 | **REAL HOLE (GSS)** |
| 2026-06-08 | Mon | is_open=true | markers 2, signals 0 | **REAL HOLE (GSS)** |
| 2026-06-11 | Thu | is_open=true | markers 2, signals 1 | **REAL HOLE (GSS, NIFTY)** |
| 2026-09-14 | Mon | is_open=false | - | holiday, correctly absent |

**gamma_metrics has NO real holes.** Its only gap, 09-11 -> 09-15, has
exactly one missing weekday (09-14) and the calendar marks it closed.
09-11 and 09-15 are both present. This is the strongest single argument
for the gamma_metrics-only decision.

### NEW TD OWED - S2: trading_calendar is missing a weekday row INSIDE its span
- 2026-05-28 (Thu) has **no row**, while every other weekday 2026-05-20
  -> 06-05 carries one and weekends correctly carry none. The calendar
  does record closures as rows (09-14 is present with is_open=false), so
  an absent weekday is neither "open" nor "closed" - it is undefined.
- That is exactly the **ADR-020 contract collision** landing on a real
  date: the gate reads no-row as ALLOW, the seeder writes no-row to mean
  CLOSED. Rule 18 says a gate over a wrong calendar is worse than no gate.
- TWO READINGS, UNRESOLVED, and I am not picking one: (a) 05-28 was a
  genuine closure whose holiday row was never seeded - but then it should
  look like 09-14 and does not; (b) 05-28 was a trading day on which the
  ENTIRE pipeline was dark - markers 0 and signals 0 against 148 and 143
  on the neighbouring sessions - and the calendar is independently
  missing its row. Reading (b) means a whole-day outage nobody recorded.
- SETTLE IT AGAINST THE OFFICIAL NSE/BSE 2026 HOLIDAY LIST, per Rule 18.
  Do not settle it from the calendar, which is the artefact in question.

### DEFERRED - the long-history extension (2026-03-31 -> 2026-05-24)
- That stretch is covered by NO current source: hist_gamma_metrics ends
  03-30, gex_strike_snapshots starts 05-25, gamma_metrics starts 06-10.
- Fillable only by RECOMPUTE from historical_option_chain_snapshots,
  which overlaps hist_gamma_metrics (03-16 -> 03-30) AND
  gex_strike_snapshots (05-25 -> 06-03). Those overlaps are what make it
  **the unit bridge 3a could not provide** - it is the only object that
  can measure the x1e7 ratio empirically against both eras.
- NOT BUILT NOW. Recorded so that whoever attempts a 299-day river knows
  the bridge is a prerequisite, not a detail, and that TD-S30-CANDIDATE-1
  is what it costs to skip it.

### 2026-05-28 SETTLED - and the gate held
SUPERSEDES the two-reading entry above. Reading (a) is correct.
- **NSE circular NSE/CMTR/71775 (Ref 172/2025, 12 Dec 2025)** lists
  28 May 2026 (Thu) as **Bakri Id, a trading holiday.** Reading (b), the
  whole-day blackout, is RULED OUT.
- MEASURED S81, and it refines the finding further:
  `trading_calendar.json` **DOES carry it** - `holidays[8] = {"date":
  "2026-05-28", "name": "Bakri Eid"}`, one of 16 2026 dates in the file.
  The **DB table `trading_calendar` is the only thing missing the row.**
- So the defect is in **SEEDING**, not in the calendar source. The JSON is
  right; `seed_trading_calendar.py` did not land this row in the table,
  while it did land 2026-09-14 (present, is_open=false, so the seeder
  does write closure rows).
- **THE GATE HELD, and ADR-020 is why.** `core/trading_calendar_gate.py`
  resolves a missing row through the V18E rule engine
  (`trading_calendar.get_session_config_for_date`) rather than defaulting,
  so it read the JSON, found Bakri Eid, and returned closed. markers=0 /
  signals=0 on 05-28 is the gate working, not an outage. **This is ADR-020
  doing exactly the job it was written for** - a validation of that
  decision, recorded as such.
- TD BECOMES (S2, S60 family, Rule 18): "`trading_calendar` table is
  missing the 2026-05-28 Bakri Id closure row that `trading_calendar.json`
  carries." Scope: find why the seeder skipped it and whether other JSON
  holidays are equally absent from the table - 16 JSON dates against
  whatever the table holds is a one-query diff and was NOT run this
  session. Do not fix now.
- NOTE THE RESIDUAL RISK: the gate is safe because it falls through to the
  JSON, but **any consumer reading `trading_calendar` directly** - rather
  than through the gate - still sees no row for 05-28 and, per the
  seeder's own convention, would read that as closed while the gate's
  documented contract reads no-row as allow. The ADR-020 collision is
  contained in the canonical gate, not eliminated system-wide.

## ENH-126 v_gex_net_gamma_river (L14) - observations and one operator-caught defect

### DEFECT IN MY OWN DESIGN, caught by the operator on first read
- session_complete shipped in draft as
  `session_date < today_IST OR last_run >= 15:15`.
  The date clause made **every past session complete BY CONSTRUCTION** -
  the column could not fail for the reason it existed. Rule 0 clause 1,
  authored fresh rather than inherited.
- The counter-example it missed: **2026-08-17**, both symbols, n_runs 64,
  last run at or before 15:15 = **14:10**. The writer stopped ~1 hour
  early and the old rule called the day finished.
- Redefined to `last_ts_ist_any >= session_date + time '15:10'`, no date
  clause. Today mid-session now reads false under the same rule, with no
  special case. A regression assertion for 08-17 is in the file's 4c.

### THE DAILY VALUE IS THE 15:10 CYCLE, not the 15:15 one
- Runs stamp about **seven seconds past** the five-minute mark, so the
  15:15 cycle lands at **15:15:07** and falls outside the
  at-or-before-15:15 test in `pick`. The last qualifying cycle is
  15:10:07.
- This is intended - inside continuous trading, clear of the ADR-022
  auction boundary - but **the window is named 15:15 and the value taken
  is the 15:10 cycle, and those are not the same sentence.** Recorded in
  the COMMENT so a later reader does not rediscover it as a bug.

### OBSERVATION - expiry days dominate the river's scale
Session minima, all at **dte = 0**:
  SENSEX 2026-09-10  -62.2M
  NIFTY  2026-08-11  -40.1M
  NIFTY  2026-09-01  -27.9M
  SENSEX 2026-09-17  -25.3M
against typical NON-expiry closes of ~0.1-3M - **one to two orders of
magnitude**. This is the S62 0-DTE gamma blow-up visible in the LIVE
series: at 15:10 the expiring book is twenty minutes from vanishing and
gamma is unbounded as T->0.
- NOT a defect and NOT reconstructed - gamma_metrics is the live source,
  which is exactly why S62 permits expiry days here at all.
- CONSEQUENCE FOR RENDERING: on a linear axis four expiry sessions will
  flatten the other twenty-six to a baseline. `dte` is already a column,
  so a renderer can mark, separate, or axis-break 0-DTE sessions without
  a schema change. **Presentation question, DEFERRED under Amendment B.**
- Do not "fix" this by excluding expiry days. They are real sessions and
  the largest gamma states in the window.

### OBSERVATION - 2026-08-17 is a partial compute day
- Both symbols, 64 runs, writer stopped ~14:10. A **real hole in the last
  hour**, not a holiday - the calendar marks it a trading day.
- Distinct from the four early-June GSS holes (06-03/04/08/11), which are
  whole-day compute failures on days where capture ran.
- Not investigated. Recorded so the river's 08-17 point is known to be a
  14:10 value rather than a 15:10 one, which is precisely what
  session_complete now surfaces.

### ENH-126 D2 status and what is owed
- **ADR-025 D2 clause 1 MET** - output read, 30 rows per symbol, all seven
  invariants 0 including the two 08-17 regression assertions.
- **Clause 2 MET** - EXPLAIN 54 ms, Seq Scan on gamma_metrics (11,280 rows
  scanned, 10,170 kept by the 90-day predicate). A seq scan is correct at
  this size; the predicate is there for when it is not.
- **Clause 4 MET** - sql/2026-09-22_s81_v_gex_net_gamma_river.sql, with
  COMMENT and REVOKE/GRANT as live statements, so sql/ matches the
  database. Third object today for which that is true.
- **Clause 3 PENDING BY DECISION** under ADR-025 Amendment B. A deliberate
  hold, not a lapse. Write it that way.
- **ENH-126 REGISTER ENTRY OWED** (with ENH-125's). ENH-126 is the next
  free id; ENH-125 was the previous highest.

### OBSERVED, not theorised: the view was live and anon-unreadable
- Section 3b (GRANT SELECT) was missed on the first application pass. The
  view existed, computed correctly, and returned nothing to the anon role
  until the grant was re-run. 4d caught it: anon_select false on all seven
  privileges.
- **This is the TD-S37-03 silent-empty-dataset shape happening, not being
  described.** Harmless here only because nothing consumes this view yet -
  Marketview is frozen under Amendment B. Had it been a rendered layer,
  the panel would have shown an empty chart at HTTP 200 with no error.
- REINFORCES the S81 rule that COMMENT and GRANT ship as LIVE statements
  in the sql/ file: the file was right, the application pass skipped a
  statement, and only a verification query that tests the ANON path -
  rather than the object's existence - could distinguish the two.

## ENH-127 v_oi_rotation_since_open (L13 live leg)
- **D2 clause 1 MET** - read verified. NIFTY anchor 09:15:04, latest
  15:40:05, dte 0, 236 strikes, all BOTH, churned 0. SENSEX same shape,
  196 strikes, dte 2. Top-10 read sane (NIFTY 23350 CE +20.0M qty on
  expiry day, 23400 PE -8.8M).
- **Clause 2 MET** - EXPLAIN 24.7 ms, index seeks throughout via
  idx_ocs_symbol_created_at_desc and idx_ocs_ts_symbol_expiry, no full
  scan. Contrast v_max_pain_by_strike at 3,396 ms.
- **Clause 4 MET** - sql/2026-09-22_s81_v_oi_rotation_since_open.sql with
  COMMENT and REVOKE/GRANT live. Fourth object today for which sql/
  matches the database.
- **Clause 3 PENDING BY DECISION** under ADR-025 Amendment B.
- **ENH-127 REGISTER ENTRY OWED**, with ENH-125 and ENH-126.
- 4c: all five invariants 0.
- is_fresh read FALSE at verification time (72.3 min past the 15:40
  snapshot, floor 30). The column worked on its first run rather than
  being decorative.

### idx_ocs_symbol_created_at_desc EXISTS - it is what the max-pain fix needs
The 4a plan shows option_chain_snapshots carries
**idx_ocs_symbol_created_at_desc** alongside idx_ocs_ts_symbol_expiry.
That is the (symbol, <time> DESC) prefix the S72 FIX 2 lateral probe
requires, and it is exactly what the v_max_pain_by_strike latest_ts fix
needs - the 3,260 ms full-index scan filed this session with a ~4-week
clock. ENH-127 demonstrates the pattern working on the SAME TABLE at
24.7 ms. The retrofit is therefore not speculative: the index is present
and the shape is proven in production.
CAVEAT, UNMEASURED: the index name says created_at, not ts. If it is on
created_at rather than ts the two are close but NOT the same column, and
the lateral must probe whichever column the view orders by. **Verify the
index definition before writing the retrofit** - do not assume from the
name. (This is the S72 three-indexes-one-access-path shape: names are
not definitions.)

### CORRECTION - I published an unmeasured expected value
I told the operator to expect comment_len 4637. The file literal is
**5632**, which is what the database stored, so the artefact was always
correct. The number came from nowhere: the verification run that would
have printed it aborted on a wrong assertion before reaching that line,
and I stated a figure anyway. The operator caught it by comparing.
DISTINCT FROM the four earlier assertion slips this session, which were
checks misfiring on my own prose - those were wrong CHECKS, this was a
wrong CLAIM with no measurement behind it. Rule: an expected value handed
to a verifier must be computed, and computed from the artefact, not
recalled.

## ENH-98 (L7 vanna / L8 charm) - deferral LIFTED, build WAITS for a clean re-run

### Status
- **OPERATOR DECISION S81: the ENH-98 deferral is LIFTED.** It was blocked
  on "Phase 2 deployment plan commitment" because vanna/charm had no
  Phase-1 consumer. **Hedgewall parity is that consumer.** ENH-98 moves
  PROPOSED -> IN BUILD. Parent is ADR-002 v2 P8. Build L7 and L8 under the
  EXISTING ENH-98 id; do not mint a new one.
- **BUILD NOT STARTED.** The go/no-go measurement was INCONCLUSIVE on a
  contaminated sample. Re-run first. Query below, ready to paste.

### idx_ocs_symbol_created_at_desc - CAVEAT RESOLVED
Measured: it is `(symbol, created_at DESC)`, **on created_at, NOT ts**.
So it is valid for the SYMBOL SKIP-SCAN only (symbol is its leading
column); the latest-ts probe rides `idx_ocs_ts_symbol_expiry
(ts DESC, symbol, expiry_date)`. Both exist, so **the v_max_pain_by_strike
latest_ts retrofit has the indexes it needs.** The earlier "verify before
relying on it" caveat is CLOSED - and it was worth raising: the name says
created_at and would have been read as ts.
Full index set on option_chain_snapshots: idx_ocs_run_id(run_id);
idx_ocs_symbol_created_at_desc(symbol, created_at DESC);
idx_ocs_symbol_expiry_strike_type(symbol, expiry_date, strike,
option_type); idx_ocs_ts_symbol_expiry(ts DESC, symbol, expiry_date);
option_chain_snapshots_pkey(id); uix_ocs_run_strike_type UNIQUE(run_id,
strike, option_type).

### The S81 measurement, and why it does not decide
SENSEX only (NIFTY was dte 0, excluded by T>0 - itself an S62
demonstration). dte 2, 392 chain rows, spot from gamma_metrics with a
20-minute gap.
  gamma_rel_err median by bucket:
    dte/252   ATM 0.1287  NEAR 0.1268  FAR 0.1979
    dte/365   ATM 0.0739  NEAR 0.1270  FAR 0.1961
    exact/365 ATM 0.0757  NEAR 0.1267  FAR 0.2040
  delta_abs_err median: ATM ~0.046-0.052, NEAR 0.009-0.016, FAR ~0.006

1. **Calendar-year time fits better than trading-day time** - ATM gamma
   7.4% on dte/365 against 12.9% on dte/252. The vendor almost certainly
   prices a 365-day year. NOTE: dte/365 and exact/365 are
   INDISTINGUISHABLE at 2 DTE (0.0739 vs 0.0757) - 20 minutes out of two
   days is ~0.7%. **The conventions only separate at 0-1 DTE, which is
   exactly when it matters.** Today's sample cannot choose between them;
   that is a fact about the test, not about the conventions.
2. **Stopping rule NOT met, and NOT passed.** The stated rule was: refuse
   if gamma_rel_err_med > ~0.10 in ATM AND NEAR under BOTH conventions.
   Under dte/365 ATM is 0.0739, so the refusal condition is not met.
   NEAR at 0.127 means it is not a pass either. **INCONCLUSIVE.**
3. **THE TEST WAS CONTAMINATED, AND THE CONTAMINATION WAS SELF-INFLICTED.**
   I joined gamma_metrics for spot. **option_chain_snapshots HAS ITS OWN
   spot COLUMN** - same row, same moment, 0 nulls on 66,528 rows today.
   The right column was on the row I was already reading.
   Worse, the gap is not "20 minutes stale": the chain is at 15:40 and the
   spot at ~15:20, and per ADR-022 the index is FROZEN 15:15-15:28 with
   the settled close in the 15:29 bar. The two straddle the AUCTION
   BOUNDARY - two different market states, not drift.
   QUANTIFIED: SENSEX ocs.spot 74,529.08 vs the gamma_metrics 74,653.2 I
   used = **124 points, 0.17%**. Via delta_err ~ gamma x dS with SENSEX
   ATM gamma ~ n(d1)/(S*sigma*sqrt(T)) ~ 0.399/(74529*0.00874) ~ 0.00061,
   a 0.046 delta error implies ~75 points. Same order, same direction,
   against a measured 124. The spot mismatch accounts for most of it.
4. **Vendor greek coverage is partial and the wings are junk.**
   133 of 392 SENSEX front-expiry rows (34%) have iv zero or null - the
   TD-S79-NEW-8 shape at the GREEK level, not just the gamma level. And
   iv reaches **337.86** on the wings. Those are not volatilities.
   **They must be excluded BY RULE, never by eye.** The re-run uses a
   |vendor delta| in [0.05, 0.95] band, which is self-describing and
   standard, and REPORTS how many rows the rule removed.

### TWO DEFECTS IN MY OWN RE-RUN QUERY, caught by the operator
1. **exact/365 was off by exactly one day.** It used (dte-1) days plus
   seconds-left-today; remaining time is dte days PLUS seconds-left-today.
   At dte=1 on an 11:00 IST session it returned 0.19 days against a true
   1.19. Replaced with the direct form: epoch of
   ((expiry_date + 15:30) AT TIME ZONE IST - latest_ts) / (365*86400),
   clamped at 0. **The convention meant to be the most precise was the one
   that was wrong**, and at low DTE the error is a large fraction of T -
   easily large enough to read as a model failure.
2. **round(max(spot),1) would have thrown 42883 on the first run.**
   PostgreSQL has round(numeric,int) but NO round(double precision,int),
   and spot is double precision. Now cast. The other round() calls in the
   block were already cast; this one was not, which is how it survived a
   read-through. A scan of every round() in these notes found exactly one
   other, already correct.

### PREDICTION, STATED BEFORE THE RE-RUN (Rule 0 clause 3)
Using ocs.spot, ATM delta_abs_err should fall from ~0.046 to **well under
0.01**. If it does not, the spot explanation is WRONG and there is a real
model mismatch. Record the outcome against this sentence, not against a
number adjusted afterwards.

### WHY THE FORWARD VARIANT CANNOT TEST 3(a) - include it anyway, cheaply
Black-76 with F = S*exp(rT) has an ALGEBRAICALLY IDENTICAL d1 to spot-BS:
ln(S*exp(rT)/K) + sigma^2*T/2 == ln(S/K) + rT + sigma^2*T/2. The only
difference is an exp(-rT) discount on delta and gamma, which at 1-2 DTE
and r=6.5% is 0.9998. It cannot move a 12% gamma error. It settles the
DISCOUNTING question and nothing else.
The instruments that DO discriminate a spot offset are in the re-run:
  * **signed** median delta error beside the absolute one. Consistent sign
    => spot offset. Signed ~ 0 with large absolute => model noise.
  * **implied_spot_offset_pts = median((v_delta - bs_delta)/bs_gamma)**,
    which reads the mismatch directly in index points, since
    delta_err ~ gamma * dS.

### RE-RUN CONDITIONS (operator to run)
Tomorrow **mid-session ~11:00 IST, NOT post-close**, both symbols, NIFTY
on its next expiry with dte >= 1, SENSEX dte 1. Spot from
option_chain_snapshots.spot - the SAME ROW as the greeks. Same three
conventions. Same stopping rule, restated: **refuse if gamma_rel_err_med
> 0.10 in ATM AND NEAR under all three conventions.**

### RE-RUN QUERY (ready to paste)
```sql
WITH bounded AS (
  SELECT symbol, ts, expiry_date, strike, option_type, iv, delta, gamma, spot
    FROM option_chain_snapshots
   WHERE ts >= now() - interval '1 day'
), latest AS (
  SELECT symbol, max(ts) AS latest_ts FROM bounded GROUP BY symbol
), front AS (
  SELECT l.symbol, l.latest_ts,
         (l.latest_ts AT TIME ZONE 'Asia/Kolkata')::date AS session_date,
         min(b.expiry_date) AS expiry_date
    FROM latest l
    JOIN bounded b ON b.symbol = l.symbol AND b.ts = l.latest_ts
     AND b.expiry_date >= (l.latest_ts AT TIME ZONE 'Asia/Kolkata')::date
   GROUP BY l.symbol, l.latest_ts
), raw AS (
  SELECT f.symbol, f.latest_ts, f.expiry_date,
         (f.expiry_date - f.session_date) AS dte, b.spot, b.strike,
         b.option_type, b.iv, b.delta AS v_delta, b.gamma AS v_gamma,
         EXTRACT(epoch FROM (((f.expiry_date + time '15:30')
                  AT TIME ZONE 'Asia/Kolkata') - f.latest_ts)) AS secs_to_expiry
    FROM front f
    JOIN bounded b ON b.symbol = f.symbol AND b.ts = f.latest_ts
                  AND b.expiry_date = f.expiry_date
), kept AS (
  SELECT *, abs(v_delta) BETWEEN 0.05 AND 0.95 AS in_band
    FROM raw WHERE iv > 0 AND v_gamma > 0 AND v_delta IS NOT NULL
), t AS (
  SELECT k.*, c.conv, c.tt
    FROM kept k
    CROSS JOIN LATERAL (VALUES
      ('dte/365',   GREATEST(k.dte,0)::numeric/365.0),
      ('dte/252',   GREATEST(k.dte,0)::numeric/252.0),
      ('exact/365', GREATEST(k.secs_to_expiry, 0)::numeric/(365*86400))) AS c(conv, tt)
   WHERE k.in_band AND c.tt > 0
), d AS (
  SELECT t.*, t.iv/100.0 AS sigma,
         (ln(t.spot/t.strike) + (0.065 + (t.iv/100.0)^2/2)*t.tt)
           / NULLIF((t.iv/100.0)*sqrt(t.tt),0) AS d1
    FROM t
), e AS (
  SELECT d.*, exp(-d.d1*d.d1/2)/sqrt(2*pi()) AS nd1,
         1/(1+0.2316419*abs(d.d1)) AS q
    FROM d
), f2 AS (
  SELECT e.*,
    e.nd1/NULLIF(e.spot*e.sigma*sqrt(e.tt),0)                      AS bs_gamma_spot,
    exp(-0.065*e.tt)*e.nd1/NULLIF(e.spot*e.sigma*sqrt(e.tt),0)     AS bs_gamma_fwd,
    CASE WHEN e.d1 >= 0
         THEN 1 - e.nd1*(e.q*(0.319381530+e.q*(-0.356563782+e.q*(1.781477937
                  +e.q*(-1.821255978+e.q*1.330274429)))))
         ELSE     e.nd1*(e.q*(0.319381530+e.q*(-0.356563782+e.q*(1.781477937
                  +e.q*(-1.821255978+e.q*1.330274429))))) END      AS n_d1
    FROM e
), cmp AS (
  SELECT f2.symbol, f2.conv, f2.dte, f2.spot,
         CASE WHEN abs(f2.strike/f2.spot-1) <= 0.01 THEN 'ATM'
              WHEN abs(f2.strike/f2.spot-1) <= 0.03 THEN 'NEAR'
              ELSE 'FAR' END AS bucket,
         ((CASE WHEN f2.option_type='CE' THEN f2.n_d1 ELSE f2.n_d1-1 END)
            - f2.v_delta)                                   AS d_signed,
         abs((CASE WHEN f2.option_type='CE' THEN f2.n_d1 ELSE f2.n_d1-1 END)
            - f2.v_delta)                                   AS d_abs,
         abs(f2.bs_gamma_spot - f2.v_gamma)/NULLIF(f2.v_gamma,0) AS g_spot,
         abs(f2.bs_gamma_fwd  - f2.v_gamma)/NULLIF(f2.v_gamma,0) AS g_fwd,
         (f2.v_delta - (CASE WHEN f2.option_type='CE' THEN f2.n_d1 ELSE f2.n_d1-1 END))
            / NULLIF(f2.bs_gamma_spot,0)                     AS implied_dspot
    FROM f2
)
SELECT symbol, conv, bucket, max(dte) AS dte, round(max(spot)::numeric,1) AS spot,
       count(*) AS n,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY g_spot)::numeric,4)  AS gamma_relerr_med,
       round(percentile_cont(0.9) WITHIN GROUP (ORDER BY g_spot)::numeric,4)  AS gamma_relerr_p90,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY g_fwd)::numeric,4)   AS gamma_relerr_fwd_med,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY d_abs)::numeric,4)   AS delta_abserr_med,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY d_signed)::numeric,4) AS delta_signederr_med,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY implied_dspot)::numeric,1) AS implied_spot_offset_pts
  FROM cmp GROUP BY symbol, conv, bucket
 ORDER BY symbol, conv, bucket;
```
Run alongside it, to make the exclusion rule visible rather than silent:
```sql
SELECT symbol, count(*) AS rows_front_expiry,
       count(*) FILTER (WHERE iv IS NULL OR iv = 0)        AS iv_zero_or_null,
       count(*) FILTER (WHERE iv > 100)                    AS iv_over_100,
       count(*) FILTER (WHERE abs(delta) < 0.05 OR abs(delta) > 0.95) AS outside_delta_band,
       round(min(iv) FILTER (WHERE iv > 0)::numeric,2)     AS iv_min,
       round(max(iv)::numeric,2)                           AS iv_max
  FROM option_chain_snapshots o
 WHERE o.ts = (SELECT max(ts) FROM option_chain_snapshots x WHERE x.symbol = o.symbol
                AND x.ts >= now() - interval '1 day')
 GROUP BY symbol;
```

## v_max_pain_by_strike latest_ts retrofit - the ~4-week clock TD is RESOLVED

### Before / after, measured
| | before | after |
|---|---|---|
| whole view | **3,396 ms** | **140.9 ms** |
| latest_ts CTE | **3,260 ms** | **0.18 ms** |
| latest_ts access | full-index scan, 1,336,714 rows, 145,354 heap fetches | Index Cond (symbol = s.symbol) on idx_ocs_ts_symbol_expiry, rows=1 per symbol |
| buffers | 14,240 read / 3,191 written (cold) | 1,146 shared hit, **0 reads** |

**THE CLOCK IS REMOVED, NOT DEFERRED.** The old cost scaled with TABLE
SIZE - option_chain_snapshots grows ~68k rows/day with jobid 19 disabled,
which put the view ~4 weeks from the PostgREST 8 s ceiling, at which
point the live Marketview Max Pain page would have emptied silently (the
ADR-021 failure mode). The remaining 140.9 ms is almost entirely the
`pain` CTE: a nested-loop left join of 94,112 rows, the within-symbol
strike x strike cross product. **That is O(strikes^2) per snapshot,
bounded by CHAIN WIDTH and independent of table growth.** A wider chain
would raise it; a bigger table will not.

### Equivalence and compatibility
- 4b same-statement EXCEPT against the CAPTURED BASELINE body, **run
  twice, identical both times**: old_minus_new 0, new_minus_old 0,
  NIFTY 236/236, SENSEX 196/196.
- The output SELECT block is **byte-identical** to the expiry-fix file -
  asserted in the generator, not eyeballed. Twelve columns, same order,
  same side strings, same freshness columns. The frozen Marketview is
  untouched.
- Exactly ONE CTE changed. front_expiry, chain, cohort, strikes, pain,
  max_pain all carried byte-for-byte.
- 4c: anon SELECT true, INSERT false. comment_len 5062 and
  comment_md5 c3d4d97e98700768a044df70d7583ca7, **both computed from the
  file literal and confirmed equal to the stored value** - the ENH-127
  correction applied (an expected value handed to a verifier must be
  computed from the artefact, never recalled).

### STILL OPEN, deliberately
- **Stall degradation mode.** The only ts DESC index is
  idx_ocs_ts_symbol_expiry (ts DESC, symbol, expiry_date), where symbol
  is the SECOND column, so the probe walks in ts order and filters on
  symbol. Both symbols write every cycle, so the match is the first row.
  If ONE symbol stalls, its probe walks back through the other symbol's
  newer entries - ~34k index entries per stalled day, index-only,
  milliseconds not seconds. Acceptable. A dedicated (symbol, ts DESC)
  index would remove it; **that is a SEPARATE decision and was
  deliberately not taken in this change.** Recorded in the view's COMMENT.
- **max_pain tie-break TD stays OPEN.** row_number() ORDER BY total_pain
  with no tie-break column. One line to fix, still out of scope. One
  change, one reason.

## L9 stage-1 prerequisite: FRONT-EXPIRY run_id fix (commit 89ad2bb)

### The defect, and a correction to my own audit
`ingest_option_chain_local.py` computes `snapshot_ts = utc_now_iso()` ONCE
at line 449 and passes the same value to W1 (457) and to the S80
extra-expiry pass (548), so **every expiry in a cycle shares one `ts`**.
They do NOT share `created_at` - a DB-side default, therefore LATER for
the extra pass. Two selectors ordered by exactly the column that differs:
  run_merdian_shadow_runner_aws.py:104  fetch_latest_run_ids()
  compute_options_flow_local.py:155     fetch_latest_runs_per_symbol()

**I first recorded gamma and volatility as SAFE** on the grounds that the
runner passes run_id explicitly. It does - but it RE-DERIVES that run_id
by created_at.desc, so passing it explicitly protected nothing. Had the
depth flip gone first, from its FIRST cycle the runner would have handed
gamma and volatility W2's run_id and options flow would independently
have picked W2 too. Silently: each run_id is still single-expiry, so
TD-S79-NEW-12's guard sees one expiry and returns W2's date without
raising. gex_strike_snapshots, gamma_metrics, ENH-120/121/122/125/126,
the Pine overlay and Positioning would all have followed;
gamma_metrics.dte would have jumped from 0/2 to 7/9.

**ADR-025 A1's precondition that the ingest's "Run ID:" stdout line stays
bound to W1 is TRUE AND GUARDS NOTHING HERE** - the AWS runner never
reads that line, it re-queries the table. A precondition that holds and
protects nothing is the shape this project has a rule about.

### Fix and verification
`order="ts.desc,expiry_date.asc"` at both sites - latest snapshot, then
its front expiry. `core/supabase_client._normalize_order` returns a
string verbatim when it ends in .asc/.desc, and compute_options_flow
builds raw PostgREST params, so the multi-column order passes through
both clients unaltered (verified from source BEFORE writing the patch).
**No ">= today" guard**, deliberately and unlike the views: the ingest
never writes past expiries, and a no-fallback guard in the orchestrator
converts an edge case into a compute OUTAGE (no run_id => gamma does not
run). Stated in a comment at both sites.

READ-ONLY verification, 2026-09-22 (no script run, no table written):
| symbol | old selector run_id | new selector run_id | same? |
|---|---|---|---|
| NIFTY | 7a2ec638-6cc6-4b4a-ac0b-2ce8c6fc7f82 | same | YES |
| SENSEX | be93cc98-703e-4394-9215-780b7de2c271 | same | YES |
Latest ts carries exactly ONE expiry per symbol (NIFTY 2026-09-22, 472
rows; SENSEX 2026-09-24, 392 rows), one run_id each - so the change is
**provably inert at depth 1**, which is what makes it safe to deploy
ahead of the flip.

**First live exercise: the runner's first cycle after the pull, `*/5
03-09 UTC` = 08:30-08:35 IST tomorrow.** It fires on existing chain data
and is independent of any depth change.

### SIBLING SWEEP (B18) - three more sites, NOT fixed, awaiting ruling
| site | pattern | at depth 2 | scheduled? |
|---|---|---|---|
| build_option_atm_snapshots_v1.py:20-25 | OCS `order=ts.desc limit=200` | **WOULD MIX** - 200 rows at the latest ts span W1 and W2 nondeterministically | NO |
| build_option_execution_snapshots_v1.py:177-183 | OCS `order=ts.desc` limit 1000, symbol+signal_ts filtered | **WOULD MIX** | NO |
| stage2_db_contract.py:238 | `("option_chain_snapshots","created_at",600)` freshness contract | NOT broken - sees W2's newer created_at, so it passes MORE easily. Weakened, not wrong | NO |
None of the three is in the crontab or in the shadow runner's invoke
list. All are manual/diagnostic. Fix only on operator ruling.

### FOUR ITEMS RECORDED FOR DOC-CLOSE CORRECTION
1. **ingest_option_chain_local.py lines 57-59** carry the SAME off-by-one
   as TD-S80-NEW-1's Status row: `stage 1 = depth 1 / stage 2 = depth 2 /
   stage 3 = depth 4`, against ADR-025 A1's "a stage 0 at depth 1 --
   provably inert -- precedes W1+W2". **The code comment matters more
   than the TD**: it is what an implementer reads when choosing a value.
   Both need correcting.
2. **record_write under-count.** `log.record_write("option_chain_snapshots",
   inserted_count)` at line 512 records **W1 only**; the extra-expiry rows
   are never added. After the flip, `script_execution_log` under-reports
   by ~half, so **the log cannot be used to verify the flip landed** -
   verification must query the table.
3. **merdian_daily_audit.py:90** `option_chain_snapshots_min: 80_000` is a
   day-TOTAL floor. At depth 2 the total roughly doubles, so the floor
   becomes trivially satisfied and masks a partial day even more
   thoroughly than TD-S80-NEW-9 already records.
4. **useIvSmile (queries.ts:395) collides.** It neither selects nor
   filters `expiry_date`, filters to `maxTs`, then writes
   `entry.ce = r.iv` into a Map keyed by strike - **last write wins**.
   Two expiries at one ts collide and one silently overwrites. Renders in
   `BreadthVolSection` (sections.tsx:372-379): the IV skew number and the
   smile chart on the **Breadth** page. A frontend fix is owed BEFORE or
   ALONGSIDE the flip; Amendment B currently freezes that surface, so
   this is a genuine conflict needing an operator decision, not a
   quiet proceed.

## Two operator rulings, S81

### RULING 1 - sibling OCS readers: NOT fixed, recorded as one TD
**NEW TD OWED (S3): "manual/diagnostic option_chain_snapshots readers are
not expiry-scoped."** Three sites, none scheduled, none in the crontab or
the shadow runner's invoke list:
| site | at depth 2 |
|---|---|
| `build_option_atm_snapshots_v1.py:20-25` | **would MIX** - `order=ts.desc limit=200` spans W1 and W2 nondeterministically at one ts |
| `build_option_execution_snapshots_v1.py:177-183` | **would MIX** - `order=ts.desc`, limit 1000 |
| `stage2_db_contract.py:238` | NOT broken - `("option_chain_snapshots","created_at",600)` freshness sees W2's NEWER created_at, so it passes more easily. Weakened, not wrong |
Filed so that **anyone reviving one of these knows it predates depth 2**.
Do not fix without a ruling; they are diagnostic tools, and a silent
"fix" to an unscheduled script is how a tool's output stops matching the
run it is being compared against.

### RULING 2 - useIvSmile fix is NOT blocked by Amendment B
Being fixed via Lovable: select `expiry_date`, keep `min(expiry_date)` at
`maxTs`, before the Map. **Operator ruling: this is a CORRECTNESS fix to
an existing card, not new parity presentation, so ADR-025 Amendment B
does not block it.** Recorded because Amendment B's scope will be read
again: it defers *presentation of the parity layers*, not repairs to
surfaces already shipped. Without this distinction written down, the next
reader could treat the freeze as blocking bug fixes, which it does not.

## STAGE 1 DEPLOYED (commit 8d51cce) - tomorrow's verification

`EXPIRY_DEPTH = {"NIFTY": 2, "SENSEX": 2}`, live in ~/meridian-engine.
**Nothing fires until the 08:30 IST ingest of 2026-09-23.**
The stage table was renumbered to ADR-025 A1 in the same anchor: stage 0
= depth 1, stage 1 = W1+W2, stage 2 = NIFTY 4. TD-S80-NEW-1's Status row
still carries the old numbering and is owed the same correction.

### RUN THIS AT ~09:20 IST, 2026-09-23. Every verdict must read PASS.
```sql
WITH latest AS (
  SELECT symbol, max(ts) AS ts FROM option_chain_snapshots
   WHERE ts >= now() - interval '8 hours' GROUP BY symbol
), chain AS (
  SELECT o.symbol, count(DISTINCT o.expiry_date) AS n_expiries,
         count(DISTINCT o.run_id) AS n_run_ids, min(o.expiry_date) AS front_expiry
    FROM option_chain_snapshots o JOIN latest l ON l.symbol=o.symbol AND l.ts=o.ts
   GROUP BY o.symbol
), gm AS (
  SELECT symbol, count(*) AS rows_today, count(DISTINCT ts) AS cycles_today
    FROM gamma_metrics WHERE ts >= (now() AT TIME ZONE 'Asia/Kolkata')::date
   GROUP BY symbol
), gm_last AS (
  SELECT DISTINCT ON (symbol) symbol, expiry_date AS gm_expiry, dte AS gm_dte
    FROM gamma_metrics WHERE ts >= (now() AT TIME ZONE 'Asia/Kolkata')::date
   ORDER BY symbol, ts DESC
), of_last AS (
  SELECT DISTINCT ON (symbol) symbol, run_id
    FROM options_flow_snapshots WHERE ts >= (now() AT TIME ZONE 'Asia/Kolkata')::date
   ORDER BY symbol, ts DESC
), of_exp AS (
  SELECT f.symbol, min(o.expiry_date) AS of_expiry
    FROM of_last f JOIN option_chain_snapshots o ON o.run_id = f.run_id
   GROUP BY f.symbol
)
SELECT c.symbol, 'A depth_landed' AS chk,
       c.n_expiries::text || ' expiries / ' || c.n_run_ids::text || ' run_ids' AS observed,
       CASE WHEN c.n_expiries = 2 AND c.n_run_ids = 2 THEN 'PASS' ELSE 'FAIL' END AS verdict
  FROM chain c
UNION ALL
SELECT c.symbol, 'B gamma_on_FRONT_expiry',
       'gm=' || COALESCE(g.gm_expiry::text,'NULL') || ' front=' || c.front_expiry::text
         || ' dte=' || COALESCE(g.gm_dte::text,'NULL'),
       CASE WHEN g.gm_expiry = c.front_expiry THEN 'PASS' ELSE 'FAIL' END
  FROM chain c LEFT JOIN gm_last g ON g.symbol = c.symbol
UNION ALL
SELECT m.symbol, 'C gamma_one_row_per_cycle',
       m.rows_today::text || ' rows / ' || m.cycles_today::text || ' cycles',
       CASE WHEN m.rows_today = m.cycles_today THEN 'PASS' ELSE 'FAIL' END
  FROM gm m
UNION ALL
SELECT c.symbol, 'D options_flow_on_FRONT_expiry',
       'of=' || COALESCE(f.of_expiry::text,'NO ROW') || ' front=' || c.front_expiry::text,
       CASE WHEN f.of_expiry = c.front_expiry THEN 'PASS' ELSE 'FAIL' END
  FROM chain c LEFT JOIN of_exp f ON f.symbol = c.symbol
 ORDER BY 1, 2;
```

**Check B is the one that proves the run_id fix held**, and it is written
self-referentially ON PURPOSE: it compares `gamma_metrics.expiry_date`
against `min(expiry_date)` observed in the chain at that same ts, rather
than against a dte I predicted. A hardcoded "dte must not be 13" would
have to be re-derived every week and would silently stop testing anything
the moment the expiry calendar shifted. If the fix had NOT held, gamma
would carry W2 - NIFTY ~10-06 rather than ~09-29, SENSEX ~10-01 rather
than 09-24 - and B reads FAIL without anyone needing to know the calendar.

**Check A can fail for a reason that is NOT a defect:** if the vendor
offers only one future expiry for a symbol, `select_expiries` returns a
shorter list by design and `n_expiries = 1`. Read the ingest log line
`S80 extra expiries (depth=2): [...]` before calling A a failure.

### ENH-99 retry telemetry (shell, on the box)
```
grep -E "get_option_chain 20[0-9-]+|insert extra expiry" \
     /home/ssm-user/meridian-engine/cron.log | tail -40
```
Those two `label=` strings are built at ingest lines 542 and 563 and
exist ONLY on the extra-expiry path, so any retry banner carrying them is
stage-1-induced. `grep -c retry_call` is the WRONG instrument - it fires
on success too.

### Also confirm no guard exception
```
grep -iE "infer_expiry_date|multi-expiry|Traceback" \
     /home/ssm-user/meridian-engine/cron.log | tail -20
```
Expect nothing. TD-S79-NEW-12 raises by design on a multi-expiry run_id;
it should not fire, because each expiry has its own run_id.

### ROLLBACK
One line at `ingest_option_chain_local.py:74` back to
`EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}`, commit, push, `git pull
--ff-only` on the box. **Effective on the next cron fire, within 5
minutes** - `run_ingest.sh` re-execs Python each cycle and the constant is
read at import. No restart, no daemon, no cache. Already-written W2 rows
stay; they are run_id-keyed and no front-expiry-scoped consumer sees them.

### REMEMBER: script_execution_log CANNOT verify this
`record_write` at ingest line 512 logs **W1 only**. After the flip the log
under-reports by about half. Verify from the TABLE, which is what the
block above does.

## Marketview redeploy: useIvSmile expiry-collision fix (2026-09-22)

### What shipped
`~/meridian-connect` 7b60d01 -> **a408fb4** ("Fixed IV smile expiry
collision", plus one "Changes" commit). Diff across BOTH incoming commits
is **one file, one function**: `src/lib/queries.ts`, 10 insertions /
3 deletions, all inside `useIvSmile`. No exported-function signature was
added or removed. Confirmed before pulling, not after.

The fix: `expiry_date` added to the select; rows narrowed to `maxTs`, then
to the **minimum `expiry_date`** among them (ISO date strings sort
chronologically under `localeCompare`), before the Map keyed by strike.
The previous code did `entry.ce = r.iv` with no expiry filter, so two
expiries at one ts collided and one silently overwrote the other. Falls
back to the unfiltered maxTs set only when NO row carries an expiry at
all - which preserves today's behaviour rather than blanking the card.

### NOT used: ~/redeploy_marketview.sh
That script's `SRC_DIR` is `~/merdian-marketview`, the **stale May-27
clone** (S81 Finding A). Built from `~/meridian-connect`, which md5 proved
at S81 to be the tree the live bundle actually came from. Ownership left
as `ssm-user:ssm-user` to match what was already being served - the
script's `chown www-data` was NOT applied, because the live tree is
ssm-user-owned and works, which is further evidence the Jul-12 deploy did
not use that script either.

### Verification
| check | result |
|---|---|
| files changed 7b60d01..a408fb4 | **1** (`src/lib/queries.ts`) |
| CSS hash | **unchanged** `index-CqIIwJkK.css` - correct for a .ts-only change |
| JS hash | `index-dwQ-izwF.js` -> **`index-DLdbWkEE.js`** |
| dist vs served, file-for-file md5 | **IDENTICAL**, manifest md5 `b4802df6a0301f84983cf5f5e2ae5c13` |
| `/`, `/index.html`, both assets over HTTP | **200** |
| OLD bundle `/assets/index-dwQ-izwF.js` | **404** - proves a real swap, not a cache |
| index.html references | the NEW bundle only |
| **fix present in the SERVED bytes** | `ts, expiry_date, strike, option_type, iv` occurs **1x** in `index-DLdbWkEE.js` |

That last row is the one that matters: it proves the correctness fix is in
the bytes nginx is serving, not merely in the repo. A green build and a
matching md5 would both pass on a bundle that never contained the change.

### Rollback
`/var/www/marketview.PRE_S81` holds the exact pre-deploy tree (CSS
983217234aa1f3a110256dffb166349b, JS 2c8c7bd9e30332fc2380aa1ff9086e13).
`sudo rsync -a --delete /var/www/marketview.PRE_S81/ /var/www/marketview/`
restores it immediately - nginx serves from disk, no reload needed.

### Sequencing
Done BEFORE the 08:30 IST ingest of 2026-09-23, which is when
EXPIRY_DEPTH stage 1 first produces two expiries at one ts. So the Breadth
page never renders a collided smile.

## READ-ONLY DB ACCESS: role `merdian_ro` + `bin/roq.sh` (2026-09-23)

**From now on the session runs its own verification queries.** SQL no
longer goes to the operator to paste into the Supabase SQL editor. This
removes the S81 failure mode where an expected value was *published*
rather than *computed* (see the ENH-127 correction above): the artefact
can now be measured directly at the moment the claim is made.

### The role
`merdian_ro` — a LOGIN role, and nothing else. Measured, not assumed:

| attribute | value |
|---|---|
| rolsuper / rolcreaterole / rolcreatedb / rolbypassrls / rolreplication | **all false** |
| rolcanlogin | true |
| public relations | 233 |
| SELECT | **231** |
| INSERT / UPDATE / DELETE / TRUNCATE / REFERENCES / TRIGGER | **0 / 0 / 0 / 0 / 0 / 0** |

The two relations it CANNOT read are exactly the two the S81 security
incident names: **`system_config`** (which holds the live Dhan token at
`config_key='dhan_api_token'`) and **`dhan_auth_tokens`**. Both return
`permission denied for table ...` through the real connection, verified
rather than inferred.

So the role is a true read-only login. The `default_transaction_read_only`
setting in the helper is a second layer, not the only one — which matters,
because the server's refusal of `CREATE TEMP TABLE` reads *"cannot execute
CREATE TABLE in a read-only transaction"*, i.e. the setting fired **before**
privileges were consulted and would have masked a writable role. The
privilege audit above is what actually establishes the claim.

### The credential
`$HOME/.merdian_ro_env`, **mode 600**, owner `ssm-user`, one line
`MERDIAN_RO_DSN=<uri>`. **Outside every git tree** — `git check-ignore`
does not merely ignore it, it errors with *"is outside repository"*, which
is the strongest containment statement git can make. Tracked-path match: 0.
Untracked-candidate match: 0. Tracked files containing a `postgres://`
literal: 0.

Rule 19 applies to it in full: never printed, echoed, `cat`-ed, logged or
committed. It is sourced **only inside a subshell**, which decomposes the
URI into libpq `PG*` variables, so the connection string never reaches
argv and therefore never `ps` or shell history. `psql` is invoked with no
connection argument at all. `MERDIAN_RO_DSN` is `unset` before `psql` is
exec'd, so it is not even in the client's environment. psql's stderr is
passed through a literal-substring redactor before it reaches the
terminal.

### `bin/roq.sh`
Reads SQL from stdin or a file argument. Four layers, weakest last:
1. the role cannot write (the guarantee);
2. `PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=30s`
   — backend startup options, applied before any statement, silent;
3. the same two re-issued as a SQL prelude, so they survive a pooler that
   strips startup options **— this is not hypothetical here: the
   connection reports `application_name=Supavisor`, so it lands through
   Supabase's pooler even on port 5432**;
4. a client-side write-verb guard (INSERT/UPDATE/DELETE/TRUNCATE/DROP/
   ALTER/CREATE/GRANT/REVOKE/COPY) outside comments and string literals.

`statement_timeout=30s` means a mistake **fails rather than hangs**.

`--skip-verb-guard` disables **only** layer 4. Its sole purpose is to
prove layers 1-3 work by watching the server refuse a known write —
verifying the braces requires removing the belt. It cannot make the role
writable, and the check below demonstrates that.

EXPLAIN is detected and printed tuples-only/unaligned so the plan passes
through exactly as the server emitted it; everything else prints aligned.

### Verification, 2026-09-23 (every check can fail)
| # | check | result |
|---|---|---|
| 1 | `current_user`, `session_user` | **`merdian_ro` / `merdian_ro`**, db `postgres`, PostgreSQL 17.6 |
| 2 | `SHOW default_transaction_read_only` | **`on`**; `statement_timeout` **`30s`** |
| 3 | last snapshot, both symbols | NIFTY **2 expiries / 2 run_ids**, SENSEX **2 / 2** (see stage-1 section) |
| 4 | `EXPLAIN (ANALYZE, BUFFERS) v_max_pain_by_strike` | **161.5 ms**, `latest_ts` **1.4 ms**, `shared hit=414 read=6` |
| 5a | `CREATE TEMP TABLE zzz(i int)` | **refused by the guard**, exit 2 |
| 5b | same, `--skip-verb-guard` | **`ERROR: cannot execute CREATE TABLE in a read-only transaction`**, exit 3 |
| 6 | `system_config`, `dhan_auth_tokens` | **`permission denied`** on both, exit 3 |

Check 4 confirms the S81 retrofit is holding in production: `latest_ts`
resolves via the recursive symbol skip-scan plus
`Index Cond: (symbol = s_1.symbol)` on `idx_ocs_ts_symbol_expiry`, rows=1
per symbol — **not** the 3,260 ms / 1,336,714-row full-index scan the
retrofit removed. The 161.5 ms against the 140.9 ms recorded at S81 is
the `pain` CTE's strike x strike join at a wider chain (110,240 rows today
against 94,112), which is the growth axis that section predicted:
**bounded by chain width, independent of table size.**

### A settings conflict the operator should rule on
`.claude/settings.json:25` denies `Bash(psql *)`. That rule predates the
read-only role and blocks *direct* psql invocation; it does not match
`bin/roq.sh`, so the helper runs. **This is a wrapper around a denied
command and is recorded as such rather than left implicit.** The deny was
sound when any psql connection was a potentially-writing one; it is now
arguably too broad, since `roq.sh` is strictly safer than the rule it sits
beside. Either narrow the deny or keep it and treat `roq.sh` as the single
sanctioned path — but the situation should be a decision, not an accident.

### Install note
`postgresql-client` (14) was absent and was installed via apt. needrestart
listed nginx; **nginx was NOT restarted** and was confirmed `active` with
`/marketview` still serving HTTP 200 afterwards — the S81 redeploy is
undisturbed.

### LIMITATION — roq.sh reads 0 rows, silently, from RLS tables with no `merdian_ro` policy

`merdian_ro` has `rolbypassrls = false`. Supabase's RLS policies on this
project are written `TO anon`. A role that matches no policy gets **an
empty result set, not an error** — so a query against such a table is
indistinguishable from a table that is genuinely empty. **This is the
TD-S37-03 silent-empty-dataset shape arriving inside the new verification
path itself**, and it is the failure mode most likely to make a future
session confidently wrong.

**It bit on its first real use.** The 08:53 IST run of the stage-1 block
returned `B gamma_on_FRONT_expiry -> FAIL, gm=NULL` and **check C produced
no row at all** (its CTE was empty, so the UNION branch vanished). Both
were artefacts. `compute_gamma_metrics NIFTY OK` / `SENSEX OK` stood in
`shadow_runner.log` at 03:25 and 03:30 UTC the whole time. **A FAIL was
reported to the operator that was a property of the reader, not of the
system** — and the rollback trigger for stage 1 was *"if B or D reads
FAIL"*. Recorded because the near-miss is the lesson: the check could not
distinguish "gamma is on W2" from "I cannot see gamma".

**The six commissioning checks did not catch it and could not have** —
checks 1, 2, 5 and 6 touch no table, check 3 touches
`option_chain_snapshots` (RLS off) and check 4 a view. **A commissioning
suite that never reads an RLS-enabled relation cannot discover this.** Any
future extension of roq.sh's verification must include one known-nonempty
RLS table as a control.

**Operator applied `merdian_ro_select` policies to `gamma_metrics` and
`gex_strike_snapshots` on 2026-09-23.** Those two now read. **57 remain**
(measured after the fix, `relkind IN ('r','p')`, RLS on, SELECT granted,
no policy matching `merdian_ro` and none matching PUBLIC):

```
_s36_outcomes_pre_truncate        basis_context_snapshots
bse_t1_securities                 data_contamination_ranges
dhan_scripmaster                  dhan_scripmaster_staging
dhan_token_probe_log              eq_instrument_events
eq_paper_trades                   eq_price_daily_backup_20260618
eq_price_daily_v2                 expiry_outcomes
fii_dii_cash_daily                gamma_metrics_replay
gex_pin_maxpain_history           hist_basis_context
hist_greeks_backfill_log          hist_option_greeks_1m
ict_primitive_outcomes            ict_primitive_outcomes_pre_s77
ict_primitives                    ict_primitives_pre_s77
ict_zones                         ict_zones_replay
market_breadth_intraday           market_environment_snapshots
market_spot_session_markers       market_spot_snapshots_replay
market_state_snapshots_replay     merdian_parameters
momentum_snapshots_replay         nifty_cycle_base
nifty_move_anchor                 option_chain_snapshots_replay
options_flow_snapshots_replay     participant_oi_daily
po3_session_state                 script_execution_log
script_execution_log_replay       signal_snapshots
signal_snapshots_replay           structural_divergence_snapshots
structural_divergence_snapshots_replay
study_accel_stat  study_eligible  study_null_pair  study_path
study_pin_stat    study_real_pair study_recon_accel study_recon_pin
study_runs_m      study_step_m    study_zone_ref
vol_analytics                     vol_analytics_shadow
volatility_snapshots_replay
```

**`signal_snapshots`, `ict_primitives`, `ict_primitive_outcomes`,
`script_execution_log`, `merdian_parameters`, `market_breadth_intraday`
and `gex_pin_maxpain_history` are on that list** — most of what a
verification query actually wants. Read a zero from any of them and check
this list **before** believing it.

The reusable diagnostic, one lookup:
```sql
WITH me AS (SELECT oid FROM pg_roles WHERE rolname='merdian_ro')
SELECT c.relname
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname='public' AND c.relkind IN ('r','p') AND c.relrowsecurity
   AND has_table_privilege('merdian_ro', c.oid, 'SELECT')
   AND NOT EXISTS (SELECT 1 FROM pg_policy p
                    WHERE p.polrelid=c.oid AND p.polcmd IN ('r','*')
                      AND (0 = ANY(p.polroles) OR (SELECT oid FROM me) = ANY(p.polroles)))
 ORDER BY 1;
```

## STAGE 1 VERIFIED — the §"RUN THIS AT ~09:20 IST" block, run 2026-09-23

Run through `roq.sh` at **09:14 IST**, after the two policies landed so B
and C were genuinely measurable:

```
 symbol |              chk               |               observed               | verdict
--------+--------------------------------+--------------------------------------+---------
 NIFTY  | A depth_landed                 | 2 expiries / 2 run_ids               | PASS
 NIFTY  | B gamma_on_FRONT_expiry        | gm=2026-09-29 front=2026-09-29 dte=6 | PASS
 NIFTY  | C gamma_one_row_per_cycle      | 5 rows / 5 cycles                    | PASS
 NIFTY  | D options_flow_on_FRONT_expiry | of=2026-09-29 front=2026-09-29       | PASS
 SENSEX | A depth_landed                 | 2 expiries / 2 run_ids               | PASS
 SENSEX | B gamma_on_FRONT_expiry        | gm=2026-09-24 front=2026-09-24 dte=1 | PASS
 SENSEX | C gamma_one_row_per_cycle      | 4 rows / 4 cycles                    | PASS
 SENSEX | D options_flow_on_FRONT_expiry | of=2026-09-24 front=2026-09-24       | PASS
```

### B's COUNTERFACTUAL — this is what makes it a check that could have failed
Had `89ad2bb` not landed, both selectors would still order by
`created_at.desc`. W1 and W2 share one `ts` but **not** `created_at` — a
DB default, therefore later for the S80 extra-expiry pass — so the
newest-`created_at` row is **W2**. Gamma would then carry:

| symbol | front expiry (observed) | W2, i.e. what a FAIL would show | dte |
|---|---|---|---|
| NIFTY | **2026-09-29** (dte 6) | 2026-10-06 | **13** |
| SENSEX | **2026-09-24** (dte 1) | 2026-10-01 | **8** |

Both alternatives were live in the table at the same `ts` — the check had
a real wrong answer available to it and did not return it. **Not a
tautology.** And per the notes above, B is written self-referentially
against `min(expiry_date)` observed in the chain at that same `ts`, not
against a dte predicted in advance, so it keeps testing after the expiry
calendar rolls.

**First live exercise of the selector fix with two expiries actually
present, and it held on both symbols.** No rollback.

### Log checks, same run
- **ENH-99 retry labels on the extra-expiry path:** exactly one banner
  (NIFTY W2 `2026-10-06`, 401). Not a 429. **CORRECTED LATER:** that grep
  matches only the *extra-expiry* label, which alone carries a date, so it
  could not see the **second** 401 of the day — SENSEX's **W1** call,
  which cost SENSEX its whole 03:05 cycle. Two 401s, not one, and W1 WAS
  affected. See TD (d) for the pattern defect and the corrected scope; do
  not read this line's "one banner" as the day's total.
- **Guard exceptions** (`infer_expiry_date|multi-expiry|Traceback`):
  **nothing**, as designed — each expiry gets its own `run_id`, so
  TD-S79-NEW-12's guard never sees a mixed one.
- **Expiries selected:** `depth=2` chose W2 `2026-10-06` (NIFTY, 460 rows)
  and `2026-10-01` (SENSEX, 364 rows). NIFTY 996 = 536 + 460, SENSEX
  756 = 392 + 364 — log and table agree exactly.

## FOUR TDs OWED — file verbatim at doc-close; NOT spliced into the register now

Deliberately held out of `tech_debt.md` per **TD-S79-NEW-25**: the
register is written in one pass at doc-close, and splicing mid-session
means the close must reconcile a file that already moved. Numbering is
**not** pre-assigned here — the next free `TD-S81-NEW-n` is whatever the
doc-close derives from the headings, never incremented by hand.
**None of the four is stage-1 related. All four are live.**

### (a) S2 — Dhan HTTP 500 on the W1 call drops a whole ingest cycle on both symbols
- **Symptom:** the **08:45 IST** cycle (`03:15:01Z START`) produced **no
  rows for either symbol**. `Selected expiry: 2026-09-24` / `2026-09-29`
  printed, then
  `[retry_call] <SYM> get_option_chain failed on attempt 1/6 with error:
  Dhan HTTP error | status=500 | path=/v2/optionchain |
  response={"data":{"800":"Internal Server Error"}}. Predicate returned
  False -- failing fast.`
- **Evidence:** `grep -c "status=500 | path=/v2/optionchain" cron.log` = **2**
  (one per symbol, same cycle). Table confirms the hole: today's cycles
  are 08:35 (NIFTY only), 08:40, 08:50, 08:55 — **08:45 absent for both.**
- **Why it is NOT stage-1:** the failure is on the **W1** call, which
  exists identically at depth 1. The extra-expiry pass was never reached.
- **Priority S2** — a silently dropped capture cycle; pre-existing vendor
  flakiness, TD-080 family.
- **Cross-ref:** TD-080 (S1-recurring, S22/S28/S29) · the retry-budget TD
  (d) below, which is the same log line seen from the other side ·
  D.16.4 (vendor tier behaviour) · **TD (b) — same 08:30–09:30 IST
  window, entirely different failure; see the do-not-conflate table under
  (b) before merging anything at doc-close.**

### (b) S2 — the shadow runner invokes `compute_basis_context` for a full hour before its only input exists: a cron-hour mismatch, structural and daily

**This entry REPLACES an earlier draft** that described the same symptom
as *"failed every cycle since 03:01 UTC, onset bounded by retention."*
**That framing was wrong**, and the two corrections behind it are recorded
below rather than quietly dropped, because both were errors of
instrumentation rather than of the system.

- **The mismatch, which is the whole finding:**

  | job | crontab | hours UTC | IST window |
  |---|---|---|---|
  | shadow runner | line 14, `*/5 03-09 * * 1-5` | **03**–09 | **08:30**–15:29 |
  | `capture_index_futures_snapshot_local.py` | lines 9-10, `*/5 04,05,06,07,08,09 * * 1-5` | **04**–09 | **09:30**–15:29 |

  **08:30–09:29 IST — twelve runner cycles every trading morning — invoke
  `compute_basis_context_local.py` before `index_futures_snapshots` has
  any row to read.** Structural, daily, pre-existing. Not an outage.

- **Mechanism, exact:** the script's only input is
  `index_futures_snapshots` (`fetch_recent_futures`, `LOOKBACK_MIN = 30`).
  With no row inside the lookback both symbols land `no_input`, and
  `:273-277` returns **`SKIPPED_NO_INPUT` with `exit_code=1`**. The script
  behaves exactly as written; nothing in it is broken.

- **CORRECTION 1 — "empty stdout" was an `awk` filter artefact, not the
  log.** The banner at `:221` prints unconditionally, and the log says:
  ```
  MERDIAN - compute_basis_context_local (ENH-07 B)
  Skipping NIFTY: no recent index_futures_snapshots rows.
  Skipping SENSEX: no recent index_futures_snapshots rows.
  ```
  The reason was in the log the entire time. It was filtered out by
  `awk '/Starting: |OK$|FAILED|PIPELINE/'` and then reported as a property
  of the script. **A pattern that selects status lines cannot see a
  diagnostic, and reporting its silence as evidence is the shape Rule 0
  warns about, applied to a reader rather than a check.**

- **CORRECTION 2 — "4 of 62 on 09-22" measured a truncated window.**
  `shadow_runner.log.1` begins at **`2026-09-22T04:50:04`**, i.e. **after**
  futures capture had started that day (09-22 futures ran late, first row
  **10:10 IST = 04:40 UTC**). So all 62 invocations it holds sit *inside*
  the futures window, the morning's structural failures are **not in the
  retained log at all**, and those **4 failures are a DIFFERENT cause** —
  genuine transient gaps in futures capture mid-session. The earlier
  "intermittent on 09-22" reading was right by accident and for the wrong
  reason.

- **Today is fully explained and is NOT an outage.** `shadow_runner.log`
  covers `03:00:04 → 03:50:30` UTC; all 8 invocations fall inside the
  03:00–03:59 hour. `index_futures_snapshots` had 0 rows and
  `capture_index_futures_snapshot_local.py` 0 invocations in `cron.log` at
  09:21 IST — nine minutes before its first scheduled fire.

- **ONSET: not knowable from retained logs.** `shadow_runner.log.1` starts
  04:50 UTC and older runner logs are rotated away. Do not state a start
  date. The mismatch is as old as whichever cron line moved last, and that
  is not recoverable from what is on the box.

- **Consumer impact: NONE, and the floor is why.** Sole consumer is
  `build_trade_signal_local.py:503-529`; nothing in `~/meridian-connect/src`
  reads it. The ADR-018 D2 floor added at S61
  (`MERDIAN_BASIS_RECENCY_FLOOR_MIN`, default 15) blanks the context past
  the floor (`_basis_ctx = {}` at `:524`) and writes `basis_context_stale`
  into the signal row at `:911`, so the label goes **NULL rather than
  stale**. Fail-to-absent, correctly implemented. Basis context is
  display-only per S37/S61 — no confidence modifier — so **signal
  generation is unaffected.** This is ADR-023 working as intended, and is
  worth recording as a *validation* of that decision, not only as context.

- **RLS note, corrected for accuracy:** `basis_context_snapshots` and
  `hist_basis_context` ARE on the 57-table list, so the *output* could not
  be read through `roq.sh`. `index_futures_snapshots` is **not** on that
  list and read normally — which is what allowed the diagnosis. Do not
  restate this as "could not be diagnosed through roq.sh."

- **Priority S2** — not for data loss (there is none) but because it
  pins the runner's contract signal; see the two decisions below.
- **Cross-ref:** ENH-07 B (S57 scope add, S61 ship) · ADR-018 D2 (the
  floor that contains it) · ADR-023 (fails-to-absent) · TD-S61-NEW-2 ·
  §D.25 · TD (a) above — **same window, different failure, see below**.

#### TWO DECISIONS THAT FALL OUT OF (b) — UNRESOLVED, options recorded, none chosen

**Decision 1 — should `SKIPPED_NO_INPUT` exit 1 at all?**
It converts a *legitimate pre-market state* into a contract breach. The
exit reason itself says "skipped", and `SKIPPED_NO_INPUT` is a valid
`script_execution_log` reason — but paired with `exit_code=1` the runner
reads it as a failure. **The name and the exit code disagree about what
happened.**

**Decision 2 — the runner's contract signal is pinned FAIL for an hour
every morning, so a REAL failure in that window cannot be reported.**
Twelve cycles a day emit `PIPELINE FAILED: 1 step(s)` and
`Shadow runner cycle failed (contract not met)` for a benign reason. **A
signal that reads FAIL on healthy mornings is as uninformative as one
that reads OK on broken ones** — precisely the `merdian-wsfeed` shape
(§S72.B, D.27), where a normal shutdown lands in `failed (Result:
timeout)` and a hang is indistinguishable from a clean stop. **That
property was codified and has now recurred at a second surface.**

Options, recorded without choosing:
1. **Align the cron hours** — move the futures capture to `03-09`, or the
   runner to `04-09`. Smallest change; requires knowing why they differ
   (09:30 IST may be deliberate — futures quotes before then may be thin
   or absent, in which case moving capture earlier buys nothing).
2. **Make `SKIPPED_NO_INPUT` exit 0** — honest about "nothing to do", but
   it would also silence a *genuine* futures-capture outage mid-session,
   which is exactly what the 09-22 four were. **This option trades a false
   FAIL for a false OK and should not be taken alone.**
3. **Have the runner treat no-input as NOT-APPLICABLE rather than failed**
   — a third contract state, distinct from both OK and FAIL. Most work,
   and the only option that preserves the ability to report a real
   mid-session futures outage while not failing the pre-market hour.

Whichever is chosen, **option 2's hazard is the thing to decide
deliberately**: the 09-22 failures are real and must stay visible.

#### (a) AND (b) ARE DIFFERENT FAILURES IN THE SAME WINDOW — DO NOT CONFLATE AT DOC-CLOSE
Both surfaced in the same hour on the same morning and both concern the
08:30–09:30 IST pre-market window, which makes them easy to merge into one
entry. They have **nothing in common**:

| | (a) | (b) |
|---|---|---|
| failing component | Dhan `/v2/optionchain`, **W1 call** | `compute_basis_context_local.py` |
| cause | vendor **HTTP 500**, transient | **cron-hour mismatch**, structural |
| input table | `option_chain_snapshots` | `index_futures_snapshots` |
| frequency | one cycle, 2026-09-23 08:45 | **twelve cycles, every trading day** |
| data lost | a full capture cycle, both symbols | **none** |
| fix | retry predicate / vendor | schedule or contract semantics |

(a) is a real gap in captured data. (b) loses nothing and is a reporting
defect. **Merging them would produce an entry whose "fix" addresses
neither.**

#### VERDICT ON (b): pre-existing, and unrelated to BOTH of yesterday's changes
The question asked was whether (b) is (i) pre-existing, (ii) triggered by
the front-expiry selector fix `89ad2bb`, or (iii) triggered by stage 1.
**(i), on evidence rather than inference:**

1. **`compute_basis_context_local.py` is unchanged for three months** —
   mtime 2026-06-26, and `git log --since=2026-09-21` over the script,
   `core/execution_log.py`, `core/supabase_client.py` and
   `run_merdian_shadow_runner_aws.py` returns **exactly one** commit.
2. **That one commit is `89ad2bb`, and it touched only run_id ordering in
   the runner.** `compute_basis_context_local.py` **reads no `run_id` at
   all** — it queries `index_futures_snapshots` by `ts`. There is no
   shared code path; the selector cannot reach it.
3. **Stage 1 changed `EXPIRY_DEPTH`, which affects
   `option_chain_snapshots` only.** `index_futures_snapshots` has a
   different writer, a different cron, and no expiry dimension whatsoever.
4. **The mismatch is visible before either change.**
   `index_futures_snapshots` first row is **09:30 IST on 2026-09-17,
   09-18 and 09-21** — all pre-dating yesterday. The same twelve cycles
   failed on those mornings too; their runner logs are simply rotated
   away, which is the same retention limit that makes onset unknowable.

**Falsifiable prediction, stated at 09:21 IST before observing** (per
Rule 0 clause 3 — record the outcome against this sentence, not against a
number adjusted afterwards): the futures writer fires at 09:30 IST, so
**basis_context should return OK unaided on the first runner cycle at or
after ~09:35 IST.** If it does not, this diagnosis is wrong and the cause
is something other than the cron window.

**OUTCOME — PREDICTION HELD, recorded against the sentence above.**
Observed 09:36:30 IST, no intervention of any kind:

| runner cycle (UTC) | IST | verdict |
|---|---|---|
| 03:46:15 | 09:16 | FAILED (exit 1) |
| 03:51:17 | 09:21 | FAILED (exit 1) |
| 03:56:17 | 09:26 | FAILED (exit 1) |
| **04:01:23** | **09:31** | **OK** |
| 04:06:19 | 09:36 | **OK** |

`index_futures_snapshots` today: **first row 09:30:07 IST**, both symbols,
4 rows each by 09:35:09 — exactly the scheduled 04:00 UTC hour boundary.
The 04:06 cycle wrote real values for both symbols (NIFTY basis 30.95,
`basis_velocity_pp` +0.033, label NEUTRAL; SENSEX basis 36.85,
−0.017, NEUTRAL) and printed `COMPUTE BASIS CONTEXT COMPLETED`.

**The transition lands exactly on the cron-hour boundary and nowhere
else.** Three failures in the 03:xx hour, OK on the first cycle of the
04:xx hour. Diagnosis (i) is confirmed; no fix was applied and none was
needed.

**CORRECTION 3, found by this check.**
`grep -c "capture_index_futures_snapshot" cron.log` returned **0 both
before and after** the writer demonstrably ran — the capture script does
not write an identifiable line to `cron.log`. I had cited that zero at
09:21 as supporting evidence that the writer had not yet started. It
agreed with the truth by coincidence. **A grep that returns 0 whether or
not the thing happened is not evidence** — the same CAN FIRE / CANNOT
FIRE shape as CORRECTION 1 above, and the third instrumentation error in
this one investigation. The authoritative instrument is the table:
`min(ts)` on `index_futures_snapshots`, which can distinguish the two
states and did.

### (c) S3 — a crontab line invokes `build_wcb_snapshot_local.py` with no symbol argument, every 5 minutes
- **Symptom:** `Usage: python .\build_wcb_snapshot_local.py <NIFTY|SENSEX>`
  in `cron.log`. The script prints usage and exits; **it has never done
  work from this line.** Note the Windows-style `.\` path in its own usage
  string — a Local-era artefact.
- **Evidence:** crontab line 11 —
  `*/5 03,04,05,06,07,08,09 * * 1-5 cd /home/ssm-user/meridian-engine && source .env && /usr/bin/python3 build_wcb_snapshot_local.py >> cron.log 2>&1`
  — no argument, against line 14's shadow runner which calls
  `build_wcb_snapshot NIFTY` and `SENSEX` **successfully** in the same
  window (both `OK` at `03:25:45`–`03:25:53`).
- **So the WCB work IS being done**, by the runner. The cron line is a
  redundant duplicate that only emits noise — which is why it survived:
  **it fails in a way that looks like a log line, not like an outage.**
- **This is the S48/ADR-018 "WCB cron arg" defect at a second site.** That
  one was fixed in the same pass as ADR-018 D1; this line was not.
- **Priority S3** — noise, not data loss. Fix is deleting the line or
  adding the arguments, but confirm against the runner first so the work
  is not then done twice.
- **Cross-ref:** ADR-018 D1 (S57) · S48 WCB cron arg fix · TD-S41-NEW-4
  (`build_wcb_snapshot_local.py` ExecutionLog instrumentation).

### (d) S2 — the ENH-99 retry budget has NEVER been exercised, and the ADR-025 stage-2 gate is meant to be decided on exactly that telemetry

The load-bearing half of this entry is **predicate behaviour**, which is
settled from source and from retained-log counts. The 401's *mechanism*
is a separate and still-open question, recorded at the end as UNCONFIRMED
with the check that would settle it.

#### Predicate behaviour, from source
`retry_call` — `gamma_engine_retry_utils.py:10-56`. On exception: if
`retry_predicate` is not None **and returns False**, print
`Predicate returned False -- failing fast` and **re-raise immediately**
(`:35-40`), consuming none of the budget. Otherwise sleep `current_delay`,
multiply by `backoff_multiplier`, retry to `attempts`, then print
`[RETRY_BURN_DOWN]` and re-raise.

The predicate — `ingest_option_chain_local.py:29-37`:
```python
def is_dhan_429(exc: Exception) -> bool:
    msg = str(exc)
    return "status=429" in msg or '"805"' in msg
```
**RETRIES: 429 only** — the literal substring `status=429`, or error code
`"805"` in the body. **FAILS FAST: everything else** — 401, 500, 502, 404,
network, parse. Its own docstring says so; this is deliberate S36 design,
not an oversight.

Call sites: all three Dhan calls — `:389` expiry list, `:432` W1 chain,
`:546` W2 chain — pass `retry_predicate=is_dhan_429` with
`attempts=6, delay_seconds=15.0, backoff_multiplier=1.5`. The two Supabase
inserts (`:504`, `:572`) pass **no** predicate and so retry on any
exception, `attempts=3, delay_seconds=5.0`.

#### Has the 6-attempt budget ever been exercised? NO — not once, by any class
Counted across every retained log (`cron.log`, `.1`, and six `.gz`):

| marker | meaning | cron.log | .1 | .2.gz | .3.gz | .4.gz | .5.gz | .6.gz | .7.gz |
|---|---|---|---|---|---|---|---|---|---|
| `Retrying in` | predicate said **retry** | **0** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `Predicate returned False` | **failed fast** | 6 | 0 | 4 | 4 | 4 | 2 | 0 | 2 |
| `RETRY_BURN_DOWN` | budget exhausted | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Zero retries in the entire retained history. 22 fail-fasts.** And the
error classes that actually occur:

```
  12  status=502
   9  status=401
   2  status=500
       (429: ZERO occurrences)
```

**The only class the predicate retries has never happened, and every class
that has happened fails fast.** The budget is not merely unused — on the
observed distribution it is **unreachable**. Note also that **502 is the
most common class by a wide margin**, which no prior session had surfaced;
the 401 had all the attention and is second.

#### Can the predicate express "401 -> re-read token and retry once" vs "500 -> retry"? NO
`retry_predicate` returns a **bool**, and `attempts` / `delay_seconds` /
`backoff_multiplier` are fixed per call site. The contract can express
*whether* to retry — never *how many times*, *how long*, or *what to do
first*. So "re-read the token, then retry once" and "back off six times
over ~2.5 minutes" cannot both be expressed through it. **It is one
predicate and one budget for all classes.**

Expressing the distinction needs one of, and this is a design decision not
taken here:
1. the predicate returns a **policy** (retry-count + delay, or an enum)
   rather than a bool;
2. a **pre-retry hook** (`on_retry`) on `retry_call`, which is where a
   token re-read would legitimately live;
3. **separate call sites / wrappers** per class.

Option: putting the token re-read *inside* the predicate would work
mechanically and is **the wrong place** — a hidden side effect in a
function named `is_…`. Recorded so it is rejected deliberately rather than
rediscovered.

#### CONSEQUENCE FOR THE STAGE-2 GATE — this is why the entry is S2
**ADR-025 A1 stage 2 (NIFTY depth 4) is gated on "a week of ENH-99 retry
telemetry."** That telemetry is `Retrying in` / `RETRY_BURN_DOWN` counts.
Since the predicate retries only 429 and 429 never occurs, **a week of it
will read clean no matter what happens** — while 401s and 500s drop
captures at fail-fast speed and never appear in the retry counters at all.

**A gate whose evidence cannot record the failures actually being observed
is Rule 0's CAN FIRE / CANNOT FIRE applied to a rollout decision.** The
week would not be measuring stage-1 stress; it would be measuring the
absence of a class that has never occurred.

**What the gate would need instead** (decision, not taken): count
`Predicate returned False` by class, and count dropped captures
(`failed=[...]` non-empty on the extra-expiry path, plus cycles with no
END line), rather than counting retries. Those can fire.

#### 401 MECHANISM — UNCONFIRMED, and deliberately not pursued further
**Hypothesis:** `refresh_dhan_token.py` (crontab line 2, `5 3 * * 1-5`,
appending to the same `cron.log`) rotates the token mid-cycle; the ingest
constructs `DhanClient()` once (`ingest_option_chain_local.py:378`) and
`core/dhan_client.py:34` builds the auth header from
`self.settings.dhan_access_token` captured at construction, so a running
process keeps the old token and 401s after the rotation. That is
**anti-pattern B24** (".env edits do not propagate to running processes")
and the **S66/S67 "token read at import, not at use"** shape — and S67's
fix (`_current_dhan_token()` + `load_dotenv(override=True)` at use,
`ingest_equity_eod_local.py:109/116/126`) **was applied to the equity EOD
ingest and never to this one** (B18, N silent siblings).

**Why it is NOT confirmed, despite the log appearing to show it.**
`cron.log` does contain `DHAN TOKEN REFRESH SUCCESS` /
`DHAN_API_TOKEN has been refreshed in .env` positioned between the
`03:05:01Z START` lines and the 401s. **Position in a shared append-mode
log is not event order.** Three processes write to that file concurrently
and the refresh's banner lines **carry no timestamp of their own**; a
Python process with block-buffered stdout can flush its whole block at
exit, so the banner's position establishes only that the refresh ran in
that general window — not that the token write preceded the failing HTTP
calls. Treating the interleaving as chronology would be the same
instrument error as the four already filed this session.

**THE CHECK THAT WOULD SETTLE IT** — one query, once the access exists:
a timestamped record of the token write with sub-second precision,
compared against the `03:05:01Z–03:05:12Z` window. `dhan_token_probe_log`
is the natural source and **`merdian_ro` is BLIND to it** (RLS on, no
matching policy — verified, so its `0` is meaningless and was not reported
as absence). So: **add a `merdian_ro` SELECT policy to
`dhan_token_probe_log`, or have the operator run it**, and compare the
write timestamp to that window. Confirmed if the write lands inside it and
before the SENSEX call; refuted if it lands outside.

**Cheap durable fix for the ordering question itself** (separate decision):
make the refresh script timestamp its own output lines. It currently
prints untimestamped banners into a shared append log, which is why this
question is unanswerable from the log at all.

#### SCOPE OF THE 401 — CORRECTED, and the correction matters
**An earlier draft of this entry said "W2 only, W1 never affected in any
cycle, 0 rows lost." That is FALSE and is corrected here.**

| symbol | what failed | cost |
|---|---|---|
| **SENSEX** | **W1** `2026-09-24` | **entire 03:05 cycle lost** — no END line, no 08:35 rows |
| NIFTY | W2 `2026-10-06` only | W2 snapshot only; W1 wrote 536 rows, `rc=0` |

**Two 401s on 2026-09-23, not one.** SENSEX's W1 failure is **not
stage-1 related** — W1 exists identically at depth 1. NIFTY's W2 failure
is stage-1-*exposed* (a second call, hence a window to straddle), not
stage-1-caused.

**How the error was made, because the instrument is the lesson.** The
search pattern `get_option_chain 20[0-9-]+` requires a **date** in the
retry label — and only the extra-expiry path emits one
(`label=f"{symbol} get_option_chain {_ed}"`, `:555`). W1's label has no
date (`:441`). **The pattern was structurally incapable of matching a W1
failure**, and its silence was reported as "W1 never affected" into a
rollback assessment. Fifth instrumentation error of this session and the
same shape as the other four. A second slip from the same sweep: "the
03:05 cycle was NIFTY only" — both symbols started; SENSEX produced no
END because it died on the 401, and a `tail -16` had cut off its START.

- **Priority S2** — not for the 401 (self-healing, small) but for the
  gate consequence above.
- **Cross-ref:** ENH-99 (S36, the predicate) · **ADR-025 Amendment A
  stage-2 gate** · TD-080 (S1-recurring) · TD-S66-NEW-1 / S67
  `_current_dhan_token()` fix, **not applied here** · CLAUDE.md **B24**
  (`.env` edits do not reach running processes), **B18** (N silent
  siblings) · **Rule 0** · `gamma_engine_retry_utils.py:10-56` ·
  `ingest_option_chain_local.py:29-37, :389, :432, :546` ·
  `core/dhan_client.py:34` · TD (a) above — the 500s counted here are the
  same log lines seen from the capture side.

### (e) S3 — the register says `merdian_order_placer.py` runs from an `@reboot` cron line; measured today, neither the line nor the process exists
- **Measured 2026-09-23:** `crontab -l | grep -c '@reboot'` = **0** — there
  is no `@reboot` line of any kind. `ps -eo pid,etimes,cmd` shows **no
  placer process**; the only long-lived Python on the box is
  `ws_feed_zerodha.py` (Zerodha, holds no Dhan token). No systemd unit
  hosts it either — the only MERDIAN unit is `merdian-wsfeed.service`.
- **The claim is carried in CLAUDE.md's settled-decisions** ("Phase 4B
  Order Placer … `@reboot` cron", S28) and in the Deployment Topology
  §3 / §7.1 entries written at the same time. It was true when written.
- **Priority S3** — nothing is broken; a register entry describes a
  process that is not running. But this is precisely the **decay shape**
  the project has filed repeatedly: *a register entry written from a live
  observation has no watcher, and nothing fires when its premise expires*
  (TD-S69-NEW-1, D.37.8). Four of five carried items at S71 described a
  system measurement did not find.
- **Scope of the fix:** determine whether the placer was deliberately
  retired, silently lost (e.g. a crontab reinstall — the S53 shape, where
  a dropped line caused a 28 h blackout), or moved to a launch path not
  yet catalogued. **Do not re-add the line before answering that** — an
  order placer is the one component in MERDIAN that can transact.
- **Bears on TD (d):** a daemon that caches the Dhan token at import
  (`merdian_order_placer.py:60`, module-level) and runs indefinitely is
  the **worst case in the B18 family** — it would hold an invalidated
  token from the first rotation after boot until restarted. It is not
  live, so it is not exposed today; **if it is revived, the at-use token
  read must land with it.**
- **Cross-ref:** CLAUDE.md S28 settled bullet · Deployment Topology §3 /
  §7.1 / §8.2 · TD-S69-NEW-1 + **D.37.8** (a resolved item has no
  watcher) · TD-S53 crontab-reinstall shape · TD (d) below-the-line
  family table · TD-S71 "four of five carried items had expired".

## PROPOSAL — read the Dhan token AT USE in `core/dhan_client.py` (S67 pattern). NOT APPLIED.

Written up at operator request; **no file was modified and nothing was
committed but this note.** Apply only on an explicit instruction.

### Where the fix belongs — NOT in `ingest_option_chain_local.py`
That script never builds a header. It constructs `DhanClient()` once at
`:378`; `core/dhan_client.py:31-36` captures the token into `self.headers`
at construction and `_post` reuses it at `:44`. All three public methods
(`get_ltp`, `get_option_chain`, `get_expiry_list`) route through that one
`_post`. **So this is a single edit in `core/dhan_client.py` that fixes
every `DhanClient` consumer at once** — not a patch to the ingest.

### THE TWO FACTS THAT MAKE THIS NON-OBVIOUS — a future reader will get these wrong
Recorded first because the naive fix ("move the `os.getenv` call later")
**would change nothing and would look correct**:

1. **`get_settings()` is NOT cached.** `core/config.py:40` is a plain
   function building a fresh frozen `Settings` from `os.environ` on every
   call — no `lru_cache`. So there is no settings cache to invalidate, and
   a reader who assumes there is will design a needless invalidation path.
2. **`core/config.py:10-14` hardcodes `BASE_DIR = Path(r"C:\GammaEnginePython")`
   and only loads `.env` `if ENV_FILE.exists()` — which on AWS is NEVER**
   (TD-S60-NEW-5, already recorded for the trading-calendar gate). The
   process environment is therefore **whatever `source .env` exported at
   process start, and it never refreshes.**

**Together these mean `os.getenv("DHAN_API_TOKEN")` at use returns the
SAME STALE VALUE as at import, within one process.** Reading later is not
reading fresher. **`load_dotenv(override=True)` is the load-bearing
part** — it is the only step that re-reads the rotated file. `override=True`
is required too: without it, dotenv will not overwrite the already-set
(stale) environment variable. This is exactly why S67's helper does both,
and why copying only half of it would produce a fix that passes review and
fixes nothing.

### The exact change — three anchors

**Anchor 1**, imports (`:1-7`):
```python
from typing import Any

import requests

from core.config import get_settings
```
becomes
```python
import os
from typing import Any

import requests
from dotenv import load_dotenv

from core.config import get_settings
```

**Anchor 2**, insert the helper immediately before `class DhanClient:` (`:26`):
```python
class DhanClient:
    def __init__(self) -> None:
```
becomes
```python
def _current_dhan_token(fallback: str = "") -> str:
    """S81/TD-S66-NEW-1 family: read the token AT USE, not at construction.

    DhanClient captured the token in __init__ and reused it for the life of the
    client, so a rotation written to .env mid-cycle left a running process
    holding an invalidated token (anti-pattern B24).

    load_dotenv(override=True) is load-bearing, and override=True is not
    optional: on AWS core/config.py's ENV_FILE is a Windows path that never
    resolves (TD-S60-NEW-5), so the process environment is whatever
    `source .env` set at start. os.getenv alone would return the same stale
    value, and dotenv without override would refuse to replace it.

    Mirrors ingest_equity_eod_local.py:109-119 (S67). Falls back to the
    construction-time token so the failure mode of a bad re-read is today's
    behaviour, never an empty header.
    """
    try:
        load_dotenv(override=True)
    except Exception:
        pass
    return os.getenv("DHAN_API_TOKEN", "").strip() or fallback


class DhanClient:
    def __init__(self) -> None:
```

**Anchor 3**, `_post` (`:42-47`):
```python
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
```
becomes
```python
            headers = dict(self.headers)
            headers["access-token"] = _current_dhan_token(
                self.headers.get("access-token", "")
            )
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
```

`self.headers` is deliberately retained as the construction-time snapshot
and used as the fallback argument.

### Verification

**The check that CAN FAIL — and it must be run against the UNPATCHED file
first.** Offline, no network, no touching the live `.env`: in a temp cwd
holding a `.env` with `DHAN_API_TOKEN=SENTINEL_NEW`, set
`os.environ["DHAN_API_TOKEN"]="SENTINEL_OLD"`, construct the client, assert
`c.headers["access-token"] == "SENTINEL_OLD"`, monkeypatch `requests.post`
to capture headers, issue one call, then **assert the captured
`access-token` is `SENTINEL_NEW`.**

**State the belief before measuring: unpatched this asserts `SENTINEL_OLD`
and FAILS; patched it passes.** Running it against the current file first
is what makes it a check rather than documentation — *if it passes before
the patch, the test is wrong, not the code.*

**Negative control:** same test with **no** `.env` in the temp dir → the
header must equal `SENTINEL_OLD`, not empty. This catches a "fix" that
appears to work by blanking the token.

**Edit gate** (S64 lesson — `ast.parse` alone is insufficient, a
`str_replace` can eat a `def` header and still parse): `ast.parse` **and**
`py_compile` **and** an explicit named-object check that both
`_current_dhan_token` and `DhanClient._post` still exist. Read with
`read_bytes().decode('utf-8-sig')`, write with `write_bytes()`, and
measure the file's EOL mix first (B6).

**Sequence** (Session 71 got this wrong twice): Local patch → confirm
`M core/dhan_client.py` in `git status --porcelain` → commit → push →
`git pull --ff-only` on the box → **then** test on the box.

**Live smoke is CONFIRMATORY ONLY and must be labelled so.** One ingest
cycle writing rows at `rc=0` proves the client still works; it **cannot
fail for the reason the fix exists**, because a clean cycle looks
identical with or without the change.

### PRE-REGISTERED ACCEPTANCE TEST (the longitudinal check)
- **Baseline today: 9 × `status=401`** across all retained logs
  (`cron.log`, `.1`, six `.gz`, spanning ~2026-09-16 → 09-23, ~6 trading
  days) ≈ **~1.5 per trading day**, of which **2 were on the 03:05 cycle
  on 2026-09-23** (SENSEX W1, NIFTY W2).
- **Test:** after the fix, count `status=401` **on the 03:05 cycle
  specifically** over **N = 10 trading days**. **Expect ZERO.**
- **Why N = 10.** At the observed all-cycle rate (~1.5/day) ten clean
  trading days is overwhelming; even at a conservative 0.5/day the
  probability of zero by chance is ~0.7 %. Ten days is also two calendar
  weeks — long enough to include a monthly expiry and any weekly token
  quirk, short enough to act on.
- **SETUP STEP THAT MUST HAPPEN FIRST, or the test asserts against an
  unknown denominator:** the **9** is an all-cycles total. The matched
  pre-fix base rate **for the 03:05 cycle alone has NOT been measured** —
  only today's 2 are attributed to it. Before starting the N=10 window,
  count 03:05-cycle 401s in the retained logs. If that matched baseline is
  ~2/day, N=10 is ample; if it turns out to be ~2 in total, **N=10 is
  underpowered and the test would read PASS on a fix that did nothing** —
  the Rule 0 shape, arriving through the denominator rather than the
  assertion.
- **Refutation:** a non-zero count refutes either the fix or the
  mechanism. That distinction stays recoverable precisely because the fix
  does not depend on the mechanism (below).

### THE FIX DOES NOT DEPEND ON THE 401 MECHANISM BEING CONFIRMED
Stated explicitly so the proposal is **not blocked** on a check that
currently cannot be run (`dhan_token_probe_log` is RLS-blind to
`merdian_ro`).

**Reading a credential at use rather than at import is correct regardless
of whether it caused today's 401.** The defect is that a process holds a
credential across an interval in which another process can rotate it —
true by construction, visible in the source, and independent of the 401's
provenance. If the mechanism is later **refuted**, this change is still
correct and costs one `.env` read per request. If it is **confirmed**,
this change is the fix. The mechanism check decides *what we say about
today's incident*, not *whether the credential should be read at use*.

### B18 FAMILY — one fix, plus two live siblings
Eleven scripts capture `DHAN_API_TOKEN` at module import; exactly one
(`ingest_equity_eod_local.py`, S67) reads at use. Exposure depends on
whether the script is **running at 03:05 UTC**, when the rotation fires:

| script | token read | schedule | at 03:05? | exposed |
|---|---|---|---|---|
| `ingest_option_chain_local.py` (via `DhanClient`) | construction | `run_ingest.sh`, dedicated `0,5,…,55 03` line | **yes** | **YES — demonstrated 09-23, both symbols** |
| **`capture_spot_1m_v2.py`** | import `:84` | `*/1 03,04…09` | **yes, every minute** | **YES — LIVE SIBLING, separate smaller change** |
| **`compute_gamma_metrics_local.py`** | `os.getenv` in-function `:734` | shadow runner `*/5 03-09` | **yes** | **PARTIAL — LIVE SIBLING. Reads late but never re-reads `.env`, so still stale within the process. This is exactly the trap the two facts above describe, already present in the codebase.** |
| `capture_market_spot_snapshot_local.py` | import `:43` | `41 3` | no (03:41) | only if a rotation runs late |
| `capture_index_futures_snapshot_local.py` | import `:43` | `*/5 04…09` | no | no |
| `capture_cas_close.py` | import `:95` | `50 10` | no | no |
| `ingest_equity_eod_local.py` | **at use (S67)** | long cursored sweep | straddles by design | **already fixed — the reference** |
| `ingest_breadth_intraday_local.py`, `ingest_ad_intraday_local.py`, `capture_spot_1m.py`, `backfill_cas_close_from_daily.py`, `backfill_s41_p0a_columns_30d.py`, `ingest_equity_eod_shadow_diagnostic.py`, `stage1_auth_smoke.py` | import / in-function | **no crontab line** | — | manual/diagnostic; file so a reviver knows |
| `merdian_order_placer.py` | import `:60` | **no `@reboot` line, no process** (measured) | — | **not live — see TD (e). Worst case in the family if revived: a daemon holds the token from boot forever.** |
| `pull_token_from_supabase.py` | — | — | — | not a consumer; it is the **writer** |

**Verdict: ONE fix, plus TWO live siblings needing separate smaller
changes** — `capture_spot_1m_v2.py` and `compute_gamma_metrics_local.py`.
The rest are unscheduled: file them rather than patch thirteen scripts.

**Blast radius, measured not assumed:** `DhanClient()` is constructed in
three files — `ingest_option_chain_local.py:378`, `test_core_layer.py:35`,
and `ingest_breadth_intraday_local.BEFORE_BATCH_FIX.py:155` (a dead
backup). **Two live call sites.**

## L3 — the three open decisions are RULED (operator, S81)

**PROVENANCE, stated because it matters.** These rulings were made **in
session at S81** and **did not reach this file** during the session. They
were added at the doc-close on operator confirmation. **Source is the S81
session, not this notes file** — recorded that way so a later reader does
not go looking for a contemporaneous note that does not exist, and so the
distinction between *recorded late* and *reconstructed* stays visible.
They were **not** written until the operator confirmed them, because the
doc-close pass found zero textual support here and declined to invent
them.

These close the three decisions **ADR-025 B4 previously listed as
outstanding**, which is why L3 moves off BLOCKED-ON-DECISION.

### RULING 1 — TD-S79-NEW-17: **ADD A DISCRIMINATOR**
- `gamma_metrics.flip_level` **values are unchanged.**
- **Add a column recording WHICH CONSTRUCTION produced each row** — LONG
  cumulative-crossing-nearest-spot vs SHORT per-strike sign-flip.
- **No regime or signal behaviour changes.**
- This is the minimal option of the three NEW-17 named. It does not pick a
  winner between the constructions; it makes the blend **readable**, which
  is what made every S79 flip statistic uninterpretable — *a blend is a
  property of neither construction*. Once the column exists, any past
  statistic can be re-cut by construction rather than re-derived.

### RULING 2 — TD-S79-NEW-20: **RE-SYNC replay to production**
- Replay is **pinned to production's legacy fallback branch** and its
  signature cannot accept the argument that selects the other two.
- **Fix: pass spot, so replay takes production's branches.**
- **Record one historical day's before/after replay flip** — the evidence
  that the re-sync actually changed which branch executed. Without that
  one measured day the re-sync is a code change with no witness.

### RULING 3 — TD-S79-NEW-21: **MEASURE, THEN PARAMETERISE**
- **Sweep the SHORT-branch relative floor.**
- **Report flip sensitivity** across the sweep.
- **Only then** move it to `merdian_parameters`, **at the measured value.**
- The ordering is the ruling. Parameterising an unmeasured constant
  **relocates it rather than calibrating it**, and a parameter carries an
  implication that its value was chosen — which, unswept, it was not.

### RULING 4 — what L3 actually builds
- **A NEW display-only view of the REPRICED zero-gamma level.**
- **It does NOT read, and does NOT change, `gamma_metrics.flip_level`.**
- So the unsound shipped construct is neither displayed nor depended on,
  and the three rulings above are about making the EXISTING column
  honest — not about feeding it to the new layer. **Two separate tracks
  that happen to share a name.**

### SEQUENCING
- **None of -17, -20 or -21 ships before the stage-1 verification has
  passed.**
- **It has passed** — 2026-09-23 09:14 IST, all four checks PASS on both
  symbols (see the STAGE 1 VERIFIED section above). **So all three are
  UNBLOCKED as of this doc-close.**

### CONSEQUENCE FOR ADR-025
L3's disposition moves **BLOCKED-ON-DECISION → PENDING**: the decisions
that blocked it are made, and what remains is build work. Recorded in
**ADR-025 Amendment B7**, with B4's L3 row updated to match so the
disposition table and the ruling cannot drift apart — the TD-S80-NEW-19
shape applied to an ADR rather than a TD.
