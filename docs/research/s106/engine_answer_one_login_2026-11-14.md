# Engine-lane answer to `engine_request_one_login_2026-11-14.md` (2026-11-14, MR-S10)

From: engine lane. To: retail lane. Basis: project docs only (rulings S100, Deployment Topology §5 / §S71 / §S82, `runbook_update_kite_flow.md`, tape T0 / Muhurat docs, tech debt S66/S81/S86). I have no shell on the production box from this session. Nothing below was run. **UNVERIFIED** = the docs do not show it; the read that settles it is in section 3.

## 1. The three questions that unblock retail

**E1 (hand the Dhan key): NOT DONE.** Needs E5's transport first and one code change on the box (spec in section 2). The engine side is owed after retail supplies the receiving end.

**E6 (which Kite app makes the morning key): the operator's personal Kite Connect app, the one whose `api_key` sits in MALPHA's `.env` and is used by `~/meridian-alpha/core/refresh_kite_token.py`.** It is not a retail app (the request says retail has none; P3b's app does not exist yet). The engine has the same `api_key` in its own `.env` as `ZERODHA_API_KEY`: a Kite access token is valid only with the key that minted it, and the pushed token authenticates on the engine on normal days (`profile()` in `preopen_probe.py` and the `merdian-wsfeed` preflight), so the two keys are the same app. That is an inference from the push working; the hash comparison of `ZERODHA_API_KEY` on MALPHA and the engine (owed since 11-13, see section 3) would confirm it. The tape runner also uses this app (tape design O-1). The API secret stays on MALPHA only and never goes into a drop file.

Consequence for retail: Kite has the same one-minter rule. A second login on this app by anything other than MALPHA's `refresh_kite_token.py` can end the session the engine, the feed and the recorder hold (MR-S11 already says so for `kite_one_session.sh`). Retail only adopts the key.

**Holiday and refusal question: see section 4.**

## 2. E1 to E10, one by one

| # | Status | Answer |
|---|---|---|
| E1 | **Not done** | Spec for the build: a helper called at the end of the success path of `refresh_dhan_token.py`. Writes `broker=dhan`, `access_token`, `expires` (as returned), `minted_at` (IST ISO), `client_id` (from `DHAN_CLIENT_ID`) to a temporary name in the drop directory, mode 0600, then renames. No value logged. A failure of the drop is caught and logged by name only; it must never fail the engine's own login or touch `.env` or Supabase `system_config`. Not built: waits on E5. |
| E2 | **Partly answered; code read not done** | From the docs, the Dhan login (`https://auth.dhan.co/app/generateAccessToken`) is in `refresh_dhan_token.py` (cron, 08:20 IST Mon–Fri since S100-G), `refresh_dhan_token_aws.py`, `dhan_token_refresh_lib.py`, `fix_oi21_token_refresh_hardening.py`. `pull_token_from_supabase.py` and `sync_token_to_aws.py` move a token and do not log in. **Known conflict with R3:** since V18E the script retries Invalid TOTP after 30 s, three attempts (S82: "3 × Invalid TOTP"), so it breaks the 300 s spacing. Operator-run logins also happen (BS-1, 10-26). Whether `refresh_dhan_token_aws.py` or the old 03:05 UTC / 09:05 IST entries are still scheduled is UNVERIFIED (reads 1 and 2). Tape code: Kite only in the docs; UNVERIFIED by grep. Proposed rule: keep the 30 s retry only when the response is exactly Invalid TOTP; any other answer (including HTTP 200 with no token) stops the run, and the next attempt waits 300 s. Retail to confirm whether a TOTP-rejected attempt starts Dhan's ~2-minute window (the docs only show it for a successful login followed by another). |
| E3 | **Not done** | Spec: on a failed 08:20 run, write nothing to the drop; write `dhan_login_status` containing `failed <IST time>`; on success remove it or write `ok <time>`. Same transport and same non-fatal rule as E1. |
| E4 | **Cannot confirm; no such path found in the docs** | No doc shows an engine re-login on 401, DH-901 or DH-906. TD-S81-NEW-14 describes the retry predicate failing fast on these. The 08:20 login is the only scheduled one. UNVERIFIED by grep (read 2). If a path is found it is removed, not guarded: an unexpected DH-906 is reported (the 09:09 probe pages) and the operator decides. |
| E5 | **Transport chosen; not done** | **How the Kite key reaches retail today: by hand.** MALPHA's cron pushes only to the engine (direct SSH, key on MALPHA, `ssm-user@172.31.35.90`, rewrites one line of the engine `.env`, silent on success). The retail leg is the operator writing `/etc/tape/kite_token.env` himself (Muhurat checklist; tape T0 §5 "manual (MALPHA → engine → retail box)"). So **no automated path to retail exists for Dhan to reuse.** **Chosen: a forced-command SSH key on the retail box.** Dedicated key per sender (engine for Dhan, MALPHA for Kite), `authorized_keys` options `restrict,command="<retail drop writer>"`, the command accepts only "write one file named dhan or kite into the retail drop directory" from stdin, rejects anything else, size-limited. Drop directory retail-owned, never the tape's. Network: the retail box is ap-south-1, the engine eu-north-1; a security-group rule for port 22 from the sender's address is needed and is UNVERIFIED (not in the docs). **Retail owes:** the drop path, the writer command, the `authorized_keys` line with its public key slots, the SG change. **Engine owes:** generate the sender key on the engine, give retail the public half. |
| E6 | **Answered; not done** | App: the operator's personal Kite Connect app (section 1). Destination: MALPHA's morning step gets a second push beside the existing one, to the retail drop, content `broker=kite`, `api_key`, `access_token`, `user_id`, `expires` (next 06:00 IST), never the secret. The edit is on MALPHA's crontab, not the engine's. Two cautions from the docs: (a) the schedule on MALPHA is recorded two ways, `0 3` UTC = 08:30 IST (S100-E, 10-24) and `45 0` UTC = 06:15 IST gated on `.env` mtime (S91 correction, 10-07): UNVERIFIED which is live (read 4); (b) the existing push overwrites the engine's line unconditionally and an empty value would blank it, so the new push must send nothing when the token is empty. |
| E7 | **Answered from the docs** | On a refusal the script prints the failure, writes no new token, and leaves the previous `DHAN_API_TOKEN` in `.env` and Supabase. Invalid TOTP: 30 s wait, three tries, then exit as failed (09-17 and 09-24). Whether `runtime/token_status.json` (V18E, April) is still written, and how HTTP 200 with no token is treated, are UNVERIFIED (read 3). Nothing in the refresh itself alerts; cron is silent by design (S82). The 09:09 IST pre-open probe pages when the token fails on Dhan expiry list, LTP or intraday. |
| E8 | **Answered** | The engine reads the token from `.env` at process start (anti-pattern B24: `.env` edits do not reach running processes), with `ingest_equity_eod_local.py` re-reading at use through `_current_dhan_token()`. The refresh script writes `.env` and Supabase `system_config` (`config_key=dhan_api_token`). **Nothing in E1 may touch `.env`, `system_config` or `runtime/`.** The drop file is a separate output. |
| E9 | **Not done; ruled yes with a sequence** | Ruling: run the login every day, `50 2 * * *` UTC, once E1, E3 and E10 exist; installing the daily line alone would mint on Sunday and hand over nothing. The change is mine (production crontab, S100-G rule: after 15:45 IST, with a backup, one line, diff read back). Anything depending on no weekend login: nothing in the docs; the 09:09 probe, the wsfeed retry timer and the ingest crons stay Mon–Fri, so a weekend login would have no consumer and no page. UNVERIFIED: any calendar gate inside the refresh script (read 3). The install block is held until the code lands. |
| E10 | **Not done** | Today the manual re-login is `cd ~/meridian-engine && python3 refresh_dhan_token.py` (what BS-1 ran), which has no 300 s guard and no handoff. Spec: a `bin/dhan_login.sh` that refuses with the seconds remaining if the last attempt stamp is under 300 s old, runs the script, and calls the same helper as E1. The 08:20 cron calls the same wrapper so one stamp covers both. |

## 3. Read-only reads that settle the UNVERIFIED items (engine box, no secrets printed)

Read 1, every scheduled Dhan login or token move:
```bash
crontab -l | grep -Ei 'dhan|token' | cut -c1-160
```
Read 2, every login call and any re-login on 400/401/906:
```bash
cd ~/meridian-engine && grep -rln "generateAccessToken" --include=*.py . ; grep -rn "DH-906\|re-login\|relogin" --include=*.py . | cut -c1-140
```
Read 3, holiday gate, refusal handling, status file in the refresh script:
```bash
cd ~/meridian-engine && grep -n "trading_calendar\|is_trading_day\|holiday\|HOLIDAY\|token_status\|sleep\|attempt" refresh_dhan_token.py dhan_token_refresh_lib.py | cut -c1-140
```
Read 4, on MALPHA (SSH), the live Kite push line:
```bash
crontab -l | grep -i ZERODHA | cut -c1-120
```
Kite key and token hashes on both hosts, still owed from 11-13 (printed hashes only, never values): `ZERODHA_API_KEY` and `ZERODHA_ACCESS_TOKEN`, first 12 hex of sha256, engine versus MALPHA; the key hashes matching settles E6's inference.

## 4. The last question: the 08:20 cron on an exchange holiday, and when Dhan refuses

- **Holiday:** the cron is `50 2 * * 1-5` UTC (S100-G). It fires on every weekday, including a weekday exchange holiday. No doc shows a calendar gate in `refresh_dhan_token.py`, so on a holiday it mints (UNVERIFIED, read 3). Other jobs carry a holiday gate (`HOLIDAY_GATE` in the ingest). The first Dhan-dependent consumer on a holiday is the 09:09 probe, which passes on the freshly minted token. Weekends have no login at all today (10-24: Friday's token returned 401 / DH-901 on the Saturday probe).
- **Refusal:** no new token is written and the previous one stays everywhere. It keeps working until Dhan retires it, and the printed expiry is not the validity horizon (measured twice, 09-17 and 09-24). The refresh does not alert. If the old token has died, the 09:09 IST probe pages. Under one-login-per-account that stale-token window is exactly where retail sees "taken", which is why E3's status file matters.

## 5. Owed next, by whom

- Retail: drop path, receiving writer command, `authorized_keys` line, SG rule; answer whether a TOTP-rejected attempt starts Dhan's window.
- Engine: reads 1–3 from the operator's shell; hashes for E6; then a CC prompt for the helper, `bin/dhan_login.sh` and the 300 s stamp (tests first); then the daily crontab line with backup after 15:45 IST.
- Operator: MALPHA read 4; the second push on MALPHA's crontab after the retail drop exists.
- The engine's Dhan token returns Monday 08:20 IST (retail runs killed it Saturday); the 09:09 probe will show whether it did.
