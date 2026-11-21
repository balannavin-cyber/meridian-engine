# Request to the engine lane: one login per broker account (2026-11-14, MR-S10)

From: retail lane. To: engine lane (production box). Nothing here is done from retail; production is read-only from retail. Source plan: `retail-gateway/docs/S3_one_login_plan.md` at `b60a7b2`, section 3.4 (E1 to E10), section 4 (Kite).

## Why
Dhan allows one live token per account. A new login kills the previous token (measured: mint A, mint B 150 s later; A then answered 400 DH-906, B 200). Any Dhan login on the operator's account by retail would kill the engine's token until 08:20, and the engine's 08:20 login kills a retail-held key. So inside Meridian each broker account has exactly one minter. For the operator's Dhan account the minter is the engine; retail only reuses the key it is handed. A second Dhan login less than about 2 minutes after the first is refused by Dhan (HTTP 200, no token; measured at 40 s).

## Requests
- **E1 Hand the Dhan key to retail.** After the existing 08:20 IST Dhan login succeeds, write one file to the retail drop directory (path and transport agreed in E5): `broker=dhan`, `access_token`, `expires` (exactly as Dhan returned it), `minted_at` (IST, ISO), `client_id`. Mode 0600, written under a temporary name and renamed. Do not log any value. Nothing else new at login time.
- **E2 Count your Dhan logins.** List every place in engine and tape code that calls the Dhan login (retry loops, health checks, "re-login on 400"). Each must wait at least 300 s after the previous login attempt on that account, and each successful one must write the file in E1 again. If any logs in outside 08:20, say when.
- **E3 Failed 08:20 login.** Write nothing. Write a one-line status file `dhan_login_status` with `failed` and the time, so retail can show "feed not available" instead of "taken".
- **E4 No re-login on an unexpected DH-906.** If the engine gets DH-906 before its own stored expiry, it must not re-login on its own. Report it and let the operator decide.
- **E5 Transport.** Confirm how the operator's morning Kite key reaches the retail box today, and whether Dhan can use the same path into a different, retail-owned directory (never the tape's). If not, say what you can run (fallback: a forced-command SSH key on the retail box accepting only "write one file into the retail drop directory").
- **E6 Kite.** Where the operator's morning command writes the Kite key to the engine box and the retail box, add one destination: the retail drop directory. Content: `broker=kite`, `api_key`, `access_token`, `user_id`, `expires` (next 06:00 IST). Never the API secret. Say whether the Kite app that makes this key is the engine's app or another.
- **E7 Refusals.** Confirm what the engine's login does when Dhan refuses it, on any day.
- **E8 Reading back.** Say whether the engine reads its Dhan key from a file or from memory after login. If it re-reads a file, nothing in E1 may overwrite it.
- **E9 Every day.** Run the 08:20 IST Dhan login every day, not weekdays only (cron `50 2 * * *` UTC), and write the handoff file each day. Say if anything in the engine depends on there being no login at weekends. (Reason: the operator must see the same screens on every day; a subscriber gets a fresh key on a Saturday.)
- **E10 Manual re-login.** Name the one manual command that re-runs the Dhan login on the engine box. It must respect the 300 s spacing and write the handoff file again (E1). This is the operator's way back after "taken".

## Facts the engine lane should know
- The engine's token was killed on Sat 2026-11-14 by retail measurement runs (two logins on the account); it returns at Monday 08:20 IST.
- Retail has no Kite Connect app of its own; it will use the key the operator makes each morning (no second manual step).
- The gateway verifies a handed key with one read call and checks the account id against a feed list before sealing it. It never logs in on a listed account.
- Open question from the retail side, for the engine lane to answer: does the 08:20 cron run on an exchange holiday, and what does it do if Dhan refuses?

## Answers wanted back
One doc per E-number (done / not done / cannot, with the transport chosen), plus the answer to E6's Kite-app question.
