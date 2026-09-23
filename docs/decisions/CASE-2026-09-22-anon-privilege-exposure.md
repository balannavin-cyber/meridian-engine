# CASE — 2026-09-22 · the `anon` role held full write privileges on 211 public relations, and the live Dhan broker token was readable through `system_config`

**Filed as a CASE, not a TD**, per Doc Protocol v4: a single-event failure with a diagnosis, a
remediation and a residual goes to a CASE; the residual work is filed separately as
**TD-S81-NEW-1 / -2 / -3**.

**Discovered and remediated 2026-09-22 (Session 81), mid-session**, ahead of the
`v_max_pain_by_strike` work that surfaced it. **No production impact is known.** The exposure
question is open and is the reason this file exists.

---

## 1. What was measured, before remediation

| measurement | value |
|---|---|
| public relations where `anon` held privileges **beyond SELECT** | **211** |
| tables with **RLS OFF** and `anon` INSERT/UPDATE/DELETE | **100+** (listing truncated at 100; 211 is the privilege-level count) |
| **auto-updatable views** — writes pass through to base tables | **11** |
| `dhan_auth_tokens` | RLS off, **0 policies**, `anon` SELECT/INSERT/UPDATE/DELETE |
| `system_config` | **anon-readable, including `config_value` where `config_key='dhan_api_token'`** |

**`system_config` is where the operational Dhan token actually lives.** Confirmed by reading
`pull_token_from_supabase.py:176`. `dhan_auth_tokens` — the table whose name suggests it — is
referenced by **no `.py` in the tree at all**.

**The anon key is public by design.** It inlines into the Marketview bundle at build time and sits
in the public `meridian-connect` repo (**D.21.2**). So "holder of the anon key" is not a meaningful
restriction: it is anyone with the site URL.

---

## 2. Root cause

**Supabase DEFAULT PRIVILEGES grant `anon` ALL on new objects in `public`.**

**S39 fixed the objects that existed then — thirteen surfaces — and did not touch the mechanism.**
Every object created afterwards came up with ALL again. **`v_max_pain_by_strike` (S40), measured at
all seven privileges this session, is the proof**: it was created *after* the S39 cleanup and
inherited the full grant.

**So D.21.1 was a live regression, not a closed item.** It was recorded "remediated" at S39, and
remediated is what it was — **at the instances, never at the mechanism.** This is precisely the
shape TD-S69-NEW-1 carries and **D.37.8** names: *a resolved item has no watcher.*

**D.21.2's trust model was false for every table with RLS off.** That model reads: *"the security
boundary is the RLS policy + GRANT pair, not key secrecy."* With **no RLS there is no policy to
filter**, so the GRANT alone was the boundary — and the GRANT was ALL. The model is correct where
RLS is on; it was silently inapplicable across ~100 tables where it is not.

---

## 3. What made the exposure smaller than it looks — stated, because overstating it would be wrong

On `v_max_pain_by_strike` specifically, `anon` held all seven privileges and yet the **practical**
write exposure was **LOW**, and this must be said plainly rather than left implied:

- it is **not auto-updatable** (GROUP BY + aggregates + joins), so INSERT/UPDATE/DELETE fail;
- **TRUNCATE does not apply to views**;
- **REFERENCES/TRIGGER need DDL that PostgREST never issues.**

**The grant set was wrong; it was not an open door.** That is true of the views. It is **not** true
of the ~100 RLS-off base tables, where the grant was both wrong and effective — and it is not true
of the token read, which required no write privilege at all.

---

## 4. Remediation applied (operator, verified in-database)

1. `REVOKE ALL ON system_config, dhan_auth_tokens FROM anon, authenticated`
2. `REVOKE INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER ON ALL TABLES IN SCHEMA public FROM anon, authenticated`
3. **`ALTER DEFAULT PRIVILEGES FOR ROLE postgres … same set`**

**(3) is the one that matters.** It closes the **mechanism**. Steps 1 and 2 are what S39 did; doing
only those would have reproduced S39's outcome — correct today, silently regressed on the next
object created.

**Editor verification:** `relations_with_anon_non_select = 0`; `anon_select` false on both token
tables.

**Verified through the real anon path, with value-free probes:** `system_config` → **HTTP 401**;
`dhan_auth_tokens` → **401**; `POST {}` to `breadth_ingest_state` → **401**, `pg_code 42501`;
**22 of 23** frontend relations → **206** with healthy row counts. **Marketview unaffected.**

---

## 5. Production dependency census, run read-only BEFORE the revoke

**No production write path depends on `anon`.**

- All **80** `SUPABASE_ANON_KEY` references across **47** files are a **fallback after**
  `SUPABASE_SERVICE_ROLE_KEY` — *"or ANON"*, or a candidate list with anon last;
  `canonical_ict_recall.py:156` comments *"# last resort"*.
- `SUPABASE_KEY` (**344** refs) is **not an env var** — a local alias bound from
  `SUPABASE_SERVICE_ROLE_KEY` in **95 of 98** sites.
- **The Dhan token path is service-role end to end**: `refresh_dhan_token.py` and
  `refresh_dhan_token_aws.py` use service-role only; `dhan_token_refresh_lib.py` references no
  Supabase key at all; `pull_token_from_supabase.py:160` service-role.
- **The frontend has ZERO `.insert` / `.update` / `.delete` / `.upsert`.** One RPC,
  `update_parameter`, is SECURITY DEFINER and unaffected by table grants.

**This census is why the revoke could be applied the same session** rather than staged behind a
migration window.

---

## 6. Expected behaviour change — and the wrong fix for it

A script with an empty `SUPABASE_SERVICE_ROLE_KEY` **no longer degrades silently to anon. It now
fails loudly.** Expect rarely-run backfill and `canonical_*` scripts to surface first.

**The fix when that happens is to SUPPLY THE KEY. Never to restore the grant.** This is written down
because the failure will present as a working script that suddenly stopped, and the fastest way to
make it work again is also the way that re-opens the hole.

---

## 7. What is still owed

| # | owed | filed as |
|---|---|---|
| (a) | **Supabase API log review** for anon reads of `system_config` and anon writes over the exposure window. The window opens **no later than S40** for `v_max_pain_by_strike` and plausibly **at project creation** for the RLS-off tables. | **TD-S81-NEW-1** |
| (b) | **DHAN TOKEN ROTATION DECISION.** The live token was readable by anyone holding the public anon key for an unbounded period. **Treat as potentially disclosed until (a) says otherwise.** | **TD-S81-NEW-1** |
| (c) | **Restrict anon SELECT to the frontend's 23 relations.** `capital_tracker`, `app_settings` and others remain anon-readable and are consumed by nothing. | **TD-S81-NEW-2** |
| (e) | **A STANDING CHECK**, because a resolved item has no watcher: a daily query asserting `relations_with_anon_non_select = 0`, wired into the proven `bin/disk_guard.sh` Telegram path or `eod_health_check`. **Without it, item 3 of the fix is trusted rather than verified.** | **TD-S81-NEW-3** |

*(d) is §6 above — a behaviour change to expect, not work to do.*

---

## 8. A separate finding, surfaced by the verification rather than by the incident

`v_dealer_flow_sim` (ENH-81, S37) returned **500 / `57014` on an unfiltered read**, and **200 in
0.44 s** when filtered by symbol as `useDealerFlow` actually calls it. **Pre-existing — not caused
by the revoke**, which is what the probe was testing when it appeared.

It is the **third ADR-021 sibling**: S69 scoped `v_gex_strike_pin_zone` and
`v_gex_strike_accel_zone` and left this one unbounded. Same cost shape, same fix. **The frontend
escapes it only by accident of call shape**, which is a property of the caller and not of the view.
Filed as **TD-S81-NEW-4**.

---

## 9. What this case is really about

Three of this project's standing findings arrived together, on one object:

1. **A resolved item has no watcher** (TD-S69-NEW-1, D.37.8). D.21.1 read "remediated" for 42
   sessions while regressing on every new object.
2. **Fixing instances is not fixing the mechanism.** S39 revoked thirteen surfaces; the default
   privilege that created them was untouched, so the fix had a half-life measured in new objects.
3. **A trust model is only as good as its precondition.** D.21.2 is sound where RLS is on. Nobody
   checked how many tables had it off, and the answer was ~100.

**Cross-ref.** D.21.1 (reopened as a live regression, then closed at the mechanism) · D.21.2 (trust
model corrected) · **D.37.8** · TD-S69-NEW-1 · TD-S81-NEW-1 / -2 / -3 / -4 · TD-S80-NEW-10 and
ENH-128 (`v_max_pain_by_strike`, the object that surfaced it) · ADR-021 · S39 13-surface REVOKE.
