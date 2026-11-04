# Rulings — Session 104 (Saturday 2026-10-31 → Wednesday 2026-11-04)

The single source for S104 operator rulings. S104 took no rulings on the ADR-032 build (held until after launch, S103-T). The decisions below were taken in the anon-exposure work of 2026-11-03; the record is `docs/decisions/CASE-2026-11-03-marketview-anon-key-exposure.md`.

| # | Date | Ruling | Effect |
|---|---|---|---|
| **S104-A** | 2026-11-03 | Phase 1 of the anon shrink approved ("Proceed") | `sql/2026-11-03_s104_anon_shrink.sql` applied 18:58 IST |
| **S104-B** | 2026-11-03 | A dedicated read role for Marketview approved | `marketview_ro` (`sql/2026-11-03_s104_marketview_ro_role.sql`) |
| **S104-C** | 2026-11-03 | Option B-nginx chosen ("Lets do this"): nginx forwards same-origin `/rest/v1/` to Supabase REST with a server-held read-only token; the self-hosted PostgREST (A2) is dropped | CASE §3 |
| **S104-D** | 2026-11-03 | Promote the same-origin bundle before the speed work ("lets promote if safe. We can circle back to improve the times") | live `index-DkX9XNeY.js`; HTTP/2 and region = ENH-148 |
| **S104-E** | 2026-11-03 | Revoke the remaining anon SELECT now that nothing reads through it ("Does this need to be done here?" → done 22:36 IST) | `sql/2026-11-03_s104_anon_final_revoke.sql`; `anon_select_remaining = 0` |
| **S104-F** | 2026-11-04 | End of session: the operator called the doc-close (06:30 IST) | this close |

Taken earlier in S104 (operator actions, not rulings): the S103 doc-close follow-up and the eleven PK deletions (the ten deferred S103 docs and the old ADR-032 draft); the TD-S103-NEW-6 and TD-S103-NEW-9 DDL; the BS-1 Dhan TOTP + PIN rotation (TD-S81-NEW-1 / TD-S71-NEW-11 operator actions).
