# Health — stop tracking `build_ict_htf_zones.py` (ruling S100-M (a)) — Lovable prompt

**Paste into the `meridian-connect` Lovable project.** One change to `src/pages/Health.tsx`. Read-only page; no data
read, query, string or style changes.

## Context

The Health page's OVERALL reads CRITICAL every day because one tracked writer, `build_ict_htf_zones.py`, has no
scheduled invoker (last success 36 days ago on 2026-10-22). A status that is always red carries no information. The
same was done in S90 for `merdian_pipeline_alert_daemon` — see the comment already in the array.

## The change

In `src/pages/Health.tsx`, in `const TRACKED_WRITERS: WriterDef[] = [ … ]`, replace exactly this line:

```ts
  { script: "build_ict_htf_zones.py", cadence: 1440, symbol_scoped: false },
```

with exactly this comment line:

```ts
  // S100-M: build_ict_htf_zones.py removed — no scheduled invoker (TD-S77-NEW-14); re-add when the ICT stream schedules it.
```

Leave every other entry, the S90 comment, and every other file unchanged. Do **not** touch `src/pages/Settings.tsx`
(its "rebuild ICT zones" button stays).

## Reply with

The one file changed and the line replaced (old → new). Confirm: no `supabase.` line was added, edited or removed; no
other line, file, string, style or behaviour changed. If the line above does not exist exactly as quoted, change nothing
and say so.

---

## Checks (Claude / operator)

1. Guard: `bin/mv_lovable_guard.sh 04fcd05` (layout-only) PASS — one path, `src/pages/Health.tsx` M; net **1 insertion,
   1 deletion**; no new data reads, no credentials; build clean.
2. Staging read `/staging/health`: the Writer Freshness board has no `build_ict_htf_zones.py` row; the `tracked`
   denominator is one less than live's at the same moment; no other row changed.
3. Promote from the checked commit in a refusing block with a backup of `04fcd05` (`/var/www/marketview.bak-04fcd05`);
   then S100-L retention: newest 3 `.bak-` kept (→ `.bak-04fcd05`, `.bak-804d684`, `.bak-c81b700`), `.bak-62f5c55` deleted.

---

## Round record

**Lovable** 2026-10-24 ~12:24 IST: commits `f9e4391` "Changes", `1072593` "Disabled S100-M writer in Health"; reply reported
the one line replaced at `Health.tsx`:42, no `supabase.` line touched. Not taken as evidence; the guard and reads were.

**Guard** (round copy `~/s100m/mv_lovable_guard_s100m.sh` = `docs/lovable_prompts/s92/mv_lovable_guard.sh` with the
allowlist line 34 changed to `src/pages/Health.tsx` only; `diff` showed that one line): one path `M src/pages/Health.tsx`;
no new data reads, no credentials, no vanna/charm; tsc and build clean; staging deployed `1072593`; net **1 file, 1
insertion, 1 deletion**.

**Staging read** (Claude, operator's Chrome, `https://marketview.meridianalpha.in/staging/health`, 12:29 IST, twice):
`5 healthy / 14 tracked` against live's `5 / 15`; no `build_ict_htf_zones.py` row (live: 06:21:16 IST, 38 d, host local);
the other 14 rows equal to live (last success, cadence, host; ages within the 0.1 h rounding between reads); top errors
equal to live on the second read (the first read's "no errors" was the panel loading). OVERALL CRITICAL on both — 9
writers stale outside trading hours; green-or-not is a trading-day read (Part C).

**Promoted** 12:32 IST from `1072593`, refusing subshell (HEAD, no tracked changes, backup path absent, tsc, build rooted
at `/assets/`): backup `/var/www/marketview.bak-04fcd05`; `/tmp/mv-live-build` → `/var/www/marketview/`, `diff -rq` clean
(`LIVE = BUILD`), bundle `assets/index-BHDegYdK.js`. S100-L retention: `.bak-62f5c55` deleted; left `.bak-04fcd05`,
`.bak-804d684`, `.bak-c81b700` + 3 `PRE_*`. **Live read** 12:32 IST: `5 healthy / 14 tracked`, no ICT HTF row.

**Noted:** the bare-IP address `http://13.63.27.85/…` in older docs no longer serves the board (nginx 301 → 
`https://marketview.meridianalpha.in`, behind oauth2). The error-rate / top-errors panels show "no errors" while their
query is still loading (seen on first load of both staging and live) — an empty state indistinguishable from a real zero.
