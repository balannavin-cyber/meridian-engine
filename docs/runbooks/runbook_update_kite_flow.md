# RUNBOOK: Update Kite broker flow

---

| Field | Value |
|---|---|
| **Operation** | Refresh Zerodha Kite access_token daily AND propagate it to MERDIAN AWS so the WebSocket feeder and breadth reference cron can authenticate |
| **Frequency** | **Every trading day, target 06:00 IST.** Zerodha access_tokens expire at ~06:00 IST daily; doing this immediately after gives ~3hr buffer before 09:05 IST cron cascade starts. |
| **Environment** | Two hosts: **MeridianAlpha AWS** (token source, semi-manual browser login) → **MERDIAN AWS** (token consumer, manual SSH+sed propagation). |
| **Prerequisites** | (1) Browser-accessible machine for Zerodha login. (2) SSH access to MeridianAlpha AWS (`13.51.242.119`, key at `C:\MeridianAlpha\Security\malpha-key.pem`). (3) SSM access to MERDIAN AWS (`i-0878c118835386ec2` in `eu-north-1`). (4) `refresh_kite_token.py` on MeridianAlpha + `ws_feed_zerodha.py` + `check_kite_auth.py` on MERDIAN AWS present. |
| **Expected duration** | ~5 minutes if everything works. Up to 30 min if propagation chain breaks. |
| **Who can do this** | Navin only — requires Zerodha account credentials. |
| **Last verified** | 2026-04-27 (Session 10 — refreshed at 06:58 IST. Added nano-typed verification script and SSM TTY hang failure mode after live debugging.) |

---

## When to use this runbook

**Every morning before market open — target 06:00 IST or immediately after Zerodha access_tokens expire.**

Downstream consumers that depend on a fresh token in MERDIAN AWS `.env`:
- `ws_feed_zerodha.py` (AWS cron `44 3 * * 1-5` = 09:14 IST start) — populates `market_ticks`, blocks breadth cascade if auth fails
- `refresh_equity_intraday_last.py` (AWS cron `35 3 * * 1-5` = 09:05 IST) — uses Kite REST `ohlc()` to populate `equity_intraday_last` for breadth reference prices

If Step 2 is skipped, both downstream scripts run with the previous day's token, Kite rejects their auth, and you get a silent breadth cascade failure (exactly what happened 2026-04-22 — Step 2 was forgotten that day).

Skip this runbook only on confirmed market holidays (check `trading_calendar`).

---

## Steps

### 1. Refresh Zerodha token on MeridianAlpha AWS (~06:00 IST)

SSH from Local Windows PowerShell:

```bash
ssh -i "C:\MeridianAlpha\Security\malpha-key.pem" ubuntu@13.51.242.119
cd ~/meridian-alpha && source venv/bin/activate && python core/refresh_kite_token.py
```

*What to expect:*
- Script prints a Kite login URL
- Open URL in a browser, log into Zerodha
- Browser redirects to `http://127.0.0.1/callback?request_token=XXXXXX&...`
- Copy just the `request_token` value (a 32-char string after `request_token=`)
- Paste it when the script prompts `Paste request_token here:`
- Script exchanges it via `kite.generate_session()` and writes the new `ZERODHA_ACCESS_TOKEN` to `~/meridian-alpha/.env`
- Confirmation: `Token refreshed and saved to .env` + truncated access_token preview

### 2. Propagate the new token to MERDIAN AWS (~06:05 IST) — MANUAL, HIGH RISK

This is the step that silently breaks breadth if skipped. **This is what was forgotten on 2026-04-22.**

**2a. Read the new token from MeridianAlpha** (while still SSH'd from Step 1):

```bash
grep ZERODHA_ACCESS_TOKEN ~/meridian-alpha/.env
```

Copy the full value (everything after `ZERODHA_ACCESS_TOKEN=`). This is the new access_token.

**2b. SSM into MERDIAN AWS** (new PowerShell window on Local):

```powershell
aws ssm start-session --target i-0878c118835386ec2 --region eu-north-1
```

*What to expect:* shell prompt at `ssm-user@ip-172-31-35-90`. **Immediately verify shell output works** (Session 10 finding — see Failure modes):

```bash
echo hello
```

If `echo hello` returns nothing, exit and reconnect SSM. Do not proceed until basic shell output is confirmed.

**2c. Patch `.env` on MERDIAN AWS:**

```bash
cd /home/ssm-user/meridian-engine
cp .env .env.bak_$(date +%Y-%m-%d)
sed -i 's|^ZERODHA_ACCESS_TOKEN=.*|ZERODHA_ACCESS_TOKEN=NEW_TOKEN_HERE|' .env
grep ZERODHA_ACCESS_TOKEN .env | tail -c 20
```

Replace `NEW_TOKEN_HERE` with the actual token from step 2a. The `grep | tail -c 20` prints the last 20 chars as visual confirmation sed replaced correctly.

*Watch-out:* if the paste introduces any trailing whitespace or a stray newline, sed will silently create a broken `.env` line. Always run Step 3 verification.

### 3. Verify authentication works on MERDIAN AWS (~06:10 IST) — MANDATORY

Without this check, you won't know Step 2 succeeded until 09:14 IST when the cron fires and fails silently. The 04-22 outage happened because Step 3 was never run.

Use the persistent verification script:

```bash
cd /home/ssm-user/meridian-engine
python3 check_kite_auth.py
```

*What to expect:* `AUTH OK user: Navin Balan`

*If `AUTH FAILED`:* token didn't propagate correctly. Most likely wrong token pasted in step 2c, or MeridianAlpha refresh hadn't actually written the new token. Return to Step 2.

*If `KeyError: 'ZERODHA_API_KEY'`:* the script file is corrupted (Session 10 finding — heredoc-pasted scripts can contain hidden characters that break dotenv parsing despite passing `cat`/`nano` visual checks). Recreate cleanly:

```bash
rm /home/ssm-user/meridian-engine/check_kite_auth.py
nano /home/ssm-user/meridian-engine/check_kite_auth.py
```

Type (don't paste from heredoc) the canonical contents below. Save with Ctrl+O, Enter, Ctrl+X. Then re-run Step 3.

*Canonical `check_kite_auth.py` contents:*

```python
import os
from dotenv import load_dotenv
load_dotenv("/home/ssm-user/meridian-engine/.env")
from kiteconnect import KiteConnect
kite = KiteConnect(api_key=os.environ['ZERODHA_API_KEY'])
kite.set_access_token(os.environ['ZERODHA_ACCESS_TOKEN'])
try:
    p = kite.profile()
    print('AUTH OK user:', p.get('user_name'))
except Exception as e:
    print('AUTH FAILED:', type(e).__name__, '-', e)
```

Note the explicit absolute path in `load_dotenv()` — removes cwd-discovery ambiguity.

---

## Verification

After the 09:14 IST cron fires, verify within 5 minutes:

```sql
-- Confirm market_ticks is ingesting today
SELECT
    COUNT(*) AS today_rows,
    (MAX(ts) AT TIME ZONE 'Asia/Kolkata')::timestamp AS latest_tick_ist
FROM public.market_ticks
WHERE ts >= (CURRENT_DATE AT TIME ZONE 'Asia/Kolkata');
```

Expected: `today_rows` growing rapidly (1000s per minute during active session), `latest_tick_ist` within 60s of current time.

If `today_rows = 0` at 09:20 IST the feeder auth failed silently. Check `/home/ssm-user/meridian-engine/logs/ws_feed.log` for `Feed error` loop.

---

## Failure modes

| If you see… | It probably means… | Do this |
|---|---|---|
| Step 1: `Failed: ...` instead of token refreshed | The request_token was consumed twice or is stale | Re-do browser login, get a fresh request_token, retry Step 1 |
| Step 1: Refresh returns same access_token as yesterday | Kite sometimes returns the same token within a session window — fine if it works | Continue to Step 3 and verify; if `profile()` works, token is valid even if unchanged |
| Step 2b: `echo hello` returns no output | SSM Session Manager TTY buffering broke; output is being produced but not displayed (Session 10 finding) | `exit` the SSM session entirely, reconnect via fresh `aws ssm start-session ...`, verify with `echo hello` immediately on reconnect before doing anything else |
| Step 2c: `sed` silently does nothing, grep shows old token | Token format has a special char that broke sed's replacement pattern | Use `nano .env` directly instead of sed; manually replace the line; save with Ctrl+O, Ctrl+X |
| Step 3: `AUTH FAILED: TokenException - Incorrect api_key or access_token.` | Token in MERDIAN AWS `.env` doesn't match what Kite expects | Re-read Step 2a token from MeridianAlpha; re-run Step 2c carefully; retry Step 3 |
| Step 3: `AUTH FAILED: NetworkError` | AWS can't reach Kite API | Check instance networking; check if Kite API is down (rare) |
| Step 3: `KeyError: 'ZERODHA_API_KEY'` despite `.env` containing the var | Script file at `check_kite_auth.py` was created via heredoc and contains hidden non-printing characters that break dotenv parsing (Session 10 finding) | Recreate cleanly with nano: `rm check_kite_auth.py && nano check_kite_auth.py`, then type (don't paste from heredoc) the canonical script contents in Step 3. Use `load_dotenv("/home/ssm-user/meridian-engine/.env")` with explicit absolute path. |
| 09:20 IST: market_ticks zero rows | Feeder started but can't auth — token propagation failed silently | Check `logs/ws_feed.log` for `Feed error` loop; if present, Kite auth broken — redo Steps 2-3 + restart feeder with `pkill -f ws_feed_zerodha.py && nohup python3 ws_feed_zerodha.py >> logs/ws_feed.log 2>&1 &` |
| `equity_intraday_last` hasn't updated today by 09:10 IST | The `refresh_equity_intraday_last.py` cron (09:05 IST) failed, likely also due to stale token | Same underlying cause — fix token propagation (Steps 2-3), then manually run `python3 refresh_equity_intraday_last.py` on AWS |

---

## Related

**Related runbooks:**
- `runbook_update_dhan_token.md` — sibling daily token flow (Dhan broker, separate Task Scheduler on Local Windows, different propagation mechanism via `pull_token_from_supabase.py`)

**Related tech debt:**
- Step 2 (MeridianAlpha → MERDIAN AWS sync) is fully manual and silently fragile — Session 7 finding, still open
- Step 3 manual verification has at least two known fragility modes (heredoc corruption, SSM TTY hang) — Session 10 findings, still open
- Proposed mitigation: automated Telegram pre-flight check on MERDIAN AWS at 09:10 IST that calls `kite.profile()` and alerts on failure — would catch all three Step 2/3 failure modes before market open

**Related code files:**
- `~/meridian-alpha/core/refresh_kite_token.py` (MeridianAlpha) — Step 1 script
- `/home/ssm-user/meridian-engine/.env` (MERDIAN AWS) — where token lives
- `/home/ssm-user/meridian-engine/check_kite_auth.py` (MERDIAN AWS) — Step 3 verification script (canonical contents in Step 3 above)
- `/home/ssm-user/meridian-engine/ws_feed_zerodha.py` (MERDIAN AWS) — primary consumer, 09:14 IST cron
- `/home/ssm-user/meridian-engine/refresh_equity_intraday_last.py` (MERDIAN AWS) — secondary consumer, 09:05 IST cron

**Related tables:**
- `market_ticks` — populated by `ws_feed_zerodha.py`; if empty mid-session, token propagation likely failed
- `equity_intraday_last` — populated by `refresh_equity_intraday_last.py`; if stale, token propagation likely failed
- `market_breadth_intraday` — downstream of `equity_intraday_last`; will silently produce wrong breadth if reference is stale

**Relationship to Dhan:**
- Dhan (Local Windows, via TOTP → Task Scheduler) and Zerodha (MeridianAlpha AWS, via browser login → manual SSH) are independent broker flows
- Dhan serves SENSEX options + all spot capture; Zerodha serves NIFTY options chain + full equity breadth ticks via WebSocket
- Both tokens must be fresh daily. Different mechanisms, different failure modes. Don't conflate.

---

## Change history

| Date | Change | Commit |
|---|---|---|
| 2026-04-22 | Stub created (empty template) | prior session |
| 2026-04-23 | First real fill — after Session 7 live incident recovery. All placeholders replaced with observed mechanics. | (Session 7) |
| 2026-04-27 | Session 10 update: heredoc-script-corruption failure mode + SSM TTY hang failure mode added. Verification script promoted from `/tmp/check_kite_auth.py` to persistent `/home/ssm-user/meridian-engine/check_kite_auth.py`. Canonical script contents now embedded in Step 3 with explicit `load_dotenv()` absolute path. Pre-flight Telegram check carry-forward to tech debt. | (this commit) |

---

*Runbook — commit with `MERDIAN: [OPS] runbook_update_kite_flow — Session 10 update`.*
