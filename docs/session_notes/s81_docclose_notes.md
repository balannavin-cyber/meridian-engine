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
