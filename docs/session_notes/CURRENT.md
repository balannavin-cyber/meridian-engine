# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. **S99 (its pointer block, 1,090 B, sha256 `56ab7a26…`) and S100 (7,695 B, sha256 `d11e991b…`) moved at the S101 close (run in S102)**, each asserted byte-identical on both sides. **S100 (its pointer block, 1,738 B, sha256 `e9003302…`) and S101 (5,674 B, sha256 `6a68012f…`) moved at the S102 close (run in S103)**, each asserted byte-identical on both sides. **S101 (its pointer block, 1,116 B, sha256 `7313f892…`) and S102 (7,511 B, sha256 `8c50b1b1…`) moved at the S103 close (run in S104)**, each asserted byte-identical on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S104 — Saturday 2026-10-31 09:19 IST → Wednesday 2026-11-04 06:30 IST** (operator-called end of session; this close). S104
opened as the carry-forward of S103 and became the session that closed the Marketview anon-key exposure. Saturday: the
project-knowledge prune (186 → 149 docs, `docs/research/s104/pk_prune_audit_S104.md`), the S1 re-apply (live 10:14 IST) and
the two read-only CC sweeps. Sunday: the S103 doc-close (`9d26281`) and its follow-up (`d5a4600`), the eleven PK deletions, the
TD-S103-NEW-6 (a first drop undone by its own rollback, AR §D.58.1) and TD-S103-NEW-9 DDL. Sunday–Monday: the BS-1 Dhan TOTP +
PIN rotation (operator) and the Marketview unit read against the database. Tuesday: from 18:40 the tape stream's brief that the Marketview bundle
carries the Supabase anon key — **measured, fixed and closed the same evening** (`docs/decisions/CASE-2026-11-03-marketview-anon-key-exposure.md`).
Wednesday 01:41 IST the production box's SSM agent lost DNS; the operator, who had been in arrears on AWS payments, paid and
the box was **rebooted 06:25 IST** and verified (TD-S104-NEW-7). Rulings: `docs/research/s92_parity/rulings_s104.md` (S104-A…F).
**Progress lives in the tracker**, `docs/registers/agentic_layer_roadmap_S90.md` (v2.21), **§2.2 is the single list**.

**State at close.** Engine `origin/main` at the start of this close = `9268b9a` (the S103 close `9d26281`, the sweep records
`d5a4600`, and the tape stream's merges `0b61672`…`9268b9a`, all docs and offline tape code) + this close. Offline suite
**30 steps**, no engine code changed in S104. **Marketview live = `6f14a92` built for the same-origin data path**, bundle
**`index-DkX9XNeY.js`** (promoted ≈ 22:00 IST 2026-11-03 by `~/mv_promote_s104_proxy.sh GO`); rollback target
`/var/www/marketview.bak-pre-proxy-20261103_1623` (previous bundle `index-BIJiXoC3.js`); the S103 `.bak-*` set is unchanged.
Database: `anon` holds **zero** SELECT grants in `public` (Phase 1 18:58, final revoke 22:36 IST), `marketview_ro` reads the 48
relations Marketview needs, `gex_strike_snapshots` has 7 indexes (the unused twin dropped), `v_gex_greeks_l2_strike_1pct` has
24 columns. nginx: `location ^~ /rest/v1/` proxies GET/HEAD to Supabase under the Google session with server-held
credentials (`/etc/nginx/snippets/marketview_supabase_auth.conf`).

**What was established**

1. **The Marketview exposure was the read surface, not only the write surface.** `anon` could SELECT 265 relations (116
   `public` tables with RLS off, ≈ 30.8 GB, including `capital_tracker`, `trade_log`, `app_settings`) and EXECUTE five
   SECURITY DEFINER write functions (`insert_option_chain_*`, `trigger_ingest*`); the key was in the public bundle and the
   public repo's `.env`. Fixed in four layers: Phase 1 shrink (265 → 48), `marketview_ro`, the same-origin nginx proxy with a
   server-held read-only token, and the final revoke (48 → 0). The bundle holds no credential and no Supabase URL; the old
   key gets 401 on every table (outside check). It is the **fourth** time this class has surfaced (S81, S84, S89, S104):
   **CLAUDE.md rule 26** now states the standing rule. Detail, rollbacks and the decision trail are in the CASE.
2. **The plug costs speed.** The self-hosted PostgREST (A2) measured ≈ 1.16 s per request and was dropped for nginx → Supabase
   REST (S104-C). Board first load ≈ 6.5 s against ≈ 3.1 s; accepted (S104-D). Next: `http2` on the two `listen 443` lines,
   then the Mumbai region move (ENH-148, needs a plan: new project, new keys everywhere).
3. **Anon-key rotation is now hygiene.** It must update the `apikey` line of the nginx snippet in the same step; the
   `marketview_ro` token expires **2027-11-03** (TD-S104-NEW-2). The committed `.env` is TD-S39-NEW-3 (open).
4. **Operations.** The production box's SSM agent lost DNS (error 2026-11-03 20:11:03Z, `lookup ssm.eu-north-1.amazonaws.com on
   127.0.0.53:53 … i/o timeout`), Ping Offline for ≈ 5 h after an AWS billing lapse; an EC2 reboot restored it (nginx,
   oauth2-proxy, cron, DNS, the site all verified). Cause not established; no alarm exists (TD-S104-NEW-7). **The second
   instance (retail / tape, `ip-172-31-30-166`) was not checked.**
5. **Process (AR §D.58, 10 rows, all mine).** A rollback in the same message as its forward step was run (D.58.1); I kept the
   0-scan twin and sent a live-table DDL during market hours without stating the S90-J window (D.58.2); I claimed the new path
   would load "like production" before measuring (D.58.4); my first fix of the promote script did not work and was shown wrong
   by `bash -x` (D.58.8). The two to carry: **a rollback is never in the same message as its forward step; a fix is shown
   working by its own trace before it is called a fix.**

**Filed:** TD-S104-NEW-1…8 (-3 closed at filing as a duplicate of TD-S39-NEW-3). **Closed:** TD-S103-NEW-6 (twin dropped),
TD-S103-NEW-9 (24-column wrapper), TD-S81-NEW-2, TD-S84-NEW-5, TD-S89-NEW-5 (anon read surface: 265 → 48 → 0). **Open in this
class:** TD-S81-NEW-3 (the standing check; next), TD-S39-NEW-3, TD-S92-NEW-4, TD-S103-NEW-11, TD-S90-NEW-8, TD-S104-NEW-2/-4/-5/-6.
**Enhancement Register:** ENH-148 minted (HTTP/2, then the Mumbai region). **Not evidenced in this close:** the Monday
2026-11-02 live-check readings (taken in the session chat, not written down), the Tuesday S103-B board leg roll (**not built**),
the `pg_stat_statements` re-run for TD-S103-NEW-7 (**not done**); each keeps its S103 status until a read is recorded.

**CLAUDE.md v1.76 (rule 26 added: no browser-side credential; new relations unreachable by default).** Deployment Topology
§S104; System Map §S104; ADR next-free marker unchanged (`ADR-033+`; the decision is a CASE, an ADR candidate is noted).
**Project knowledge:** `claude/anon_plug_RESULT_S104.md` (working record), `claude/anon_exposure_plan_S104.md`,
`claude/anon_phase2_design_S104.md` (marked superseded); the ten DEFERRED S103 docs and the old ADR-032 draft were deleted
earlier in S104 (git homes named in the prune audit).

## NEXT SESSION PICKS UP

1. **The second box (retail / tape, `ip-172-31-30-166`) and the Wednesday open.** Connect via SSM; if Offline, reboot the
   instance (not Stop / Start; the Elastic IP is kept on the production box, check the other); `uptime -s`. On the
   production box read the first runs of 2026-11-04: the 08:20 IST Dhan refresh, the 09:11 spot capture, the 09:15 ingest, and
   any engine script that fell back to the anon key (it now answers 401; TD-S104-NEW-4); `cron.log`.
2. **Marketview through the proxy:** parity on Pin, Gamma, OI, Flows, IV and Settings (staging covered Board and Health);
   then **`http2`** on the two `listen 443` lines (backup, anchored edit, hunk count, `nginx -t`, reload) and re-measure with
   the Performance API (TD-S104-NEW-1).
3. **Close the anon class:** the standing check from `data_contracts.access` (TD-S81-NEW-3); replace the committed `.env`
   (TD-S39-NEW-3; who owns the push); the API-log review while the 7-day window still reaches the exposure (TD-S104-NEW-5,
   operator); stop `postgrest-mv` (TD-S104-NEW-6); calendar reminder for the token (TD-S104-NEW-2).
4. **Read live and register** the md5 of `v_gex_greeks_l2_strike_1pct` (24 columns; TD-S103-NEW-9 closed on the operator's run).
5. **Carried from S103:** the Monday / Tuesday live-check readings that were not recorded (close inputs §5), S103-B (board
   leg roll after an expiry-day close), the `pg_stat_statements` re-run (TD-S103-NEW-7), tracker §2.2 remainder in its order
   (B2 R5 / R38 live reads, BS-1 remainder, B3, TD-S101-NEW-4 other half, manual option B timing), and the S99-D gate question
   (the options were offered and not answered). **ADR-032 S2 onward stays held until after launch** (date unknown).
6. **Offered, not drafted:** the Mumbai migration plan (ENH-148: inventory, cutover order, rollback, checks; one new project,
   one anon-key rotation, three streams).

## OPERATOR RULINGS, S104

**All rulings live in `docs/research/s92_parity/rulings_s104.md`**, the single source.

| # | Topic |
|---|---|
| **S104-A** | Anon shrink Phase 1 approved (applied 18:58 IST) |
| **S104-B** | Dedicated read role `marketview_ro` |
| **S104-C** | Option B-nginx: same-origin `/rest/v1/` to Supabase REST with a server-held read-only token; A2 dropped |
| **S104-D** | Promote the same-origin bundle first, speed afterwards |
| **S104-E** | Final revoke of `anon` SELECT (22:36 IST) |
| **S104-F** | End of session called by the operator; this close |

## Previous session S103

**S103 — Friday 2026-10-30 11:05 IST → Saturday 10-31 09:11 IST** (doc-close `9d26281`, run in S104). The six S102 engine
bundles applied, twelve owed rulings (S103-A…L) taken in one sitting, the WCB basket found truncated by PostgREST `max-rows`
and two NIFTY constituents found renamed (TMPV, LTM), three Marketview rounds (live `6f14a92`), the Lovable-hosted copy
unpublished, and ADR-032 D2–D5 ruled in form with F0 and S1 live (S2 held until after launch). The full block is in
`docs/registers/CURRENT_history.md`.

## OPERATOR RULINGS, S103

**All rulings live in `docs/research/s92_parity/rulings_s103.md`**, the single source.

| # | Topic |
|---|---|
| **S103-A** | Health OVERALL token threshold: scored as the daily writers (LIVE `05f556c`) |
| **S103-B** | NIFTY board after the expiry-day close: board-side roll to the next leg (ruled, not built) |
| **S103-C** | Context IV skew on a 0-DTE front leg: `SKIPPED_EXPIRY` + the next leg (LIVE `05f556c`) |
| **S103-D** | WCB writer: no row before the 09:15 IST open (`82c517d`) |
| **S103-E / K** | `held_for_cycles` resets on an expiry roll: the design, recorded |
| **S103-F** | `v_gex_max_pain` / `v_gex_pin_maxpain` on the skip-scan `latest_run` (`613c2cb`) |
| **S103-G** | WCB basket bounded, ordered, paged; prior close under a 5-day floor (`608917e`) |
| **S103-H** | TMPV and LTM renamed in our tables (operator SQL) |
| **S103-I** | R16 freeze button + strip (LIVE `2f3c2f0`); R36 closed as read |
| **S103-J** | R20 (a): `v_close_print` + `useOpenGap` (LIVE `6f14a92`) |
| **S103-L** | TD-S97-NEW-4 (b) closed as by design |
| **S103-M** | Lovable-hosted public copy: unpublished (404) |
| **S103-N / O** | OTM OI velocity on; prior-row read bounded to the IST session (`c11b564`) |
| **S103-P…T** | ADR-032 D2 additive · D3 dated break · D4 COMMENTs · Pine labels · legacy objects one retirement TD (S103-T amended: name the `service_role` reader first) |

