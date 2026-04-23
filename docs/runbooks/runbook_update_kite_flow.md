# RUNBOOK: Update Kite broker flow

> **Status:** FILLED 2026-04-23 (Session 7) — seeded from AppendixV18H_v2 §7.1, Master V19 §5.1, and Session 7 incident response.

---

| Field | Value |
|---|---|
| Operation | Refresh Zerodha Kite access_token daily AND propagate it to MERDIAN AWS so the WebSocket feeder can authenticate |
| Frequency | **Every trading day, closer to 06:00 IST.** Zerodha tokens expire at ~06:00 IST daily; doing this immediately after gives ~3hr buffer before 09:05 IST cron cascade starts. |
| Environment | Two hosts: **MeridianAlpha AWS** (token source, semi-manual browser login) → **MERDIAN AWS** (token consumer, manual SSH+sed propagation). |
| Prerequisites | (1) Browser-accessible machine for Zerodha login. (2) SSH access to MeridianAlpha AWS (`13.51.242.119`, key at `C:\MeridianAlpha\Security\malpha-key.pem`). (3) SSM access to MERDIAN AWS (`i-0878c118835386ec2` in `eu-north-1`). (4) `refresh_kite_token.py` on MeridianAlpha + `ws_feed_zerodha.py` on MERDIAN AWS present. |
| Expected duration | ~5 minutes if everything works. Up to 30 min if something in the propagation chain breaks. |
| Who can do this | Navin only — requires Zerodha account credentials. |
| Last verified | 2026-04-23 (fixed live during Session 7 after 04-22 full-day outage caused by skipped Step 2 — the `sed` patch on MERDIAN AWS was forgotten). |

---

## When to use this runbook

**Every morning before market open — target 06:00 IST or immediately after Zerodha access_tokens expire.**

Downstream consumers that depend on a fresh token in MERDIAN AWS `.env`:
- `ws_feed_zerodha.py` (AWS cron `44 3 * * 1-5` = 09:14 IST start) — populates `market_ticks`, blocks breadth cascade if auth fails
- `refresh_equity_intraday_last.py` (AWS cron `35 3 * * 1-5` = 09:05 IST) — uses Kite REST `ohlc()` to populate `equity_intraday_last` for breadth reference prices

**If Step 2 is skipped**, both downstream scripts run with the previous day's token, Kite rejects their auth, and you get a silent breadth cascade failure (exactly what happened 2026-04-22 — Step 2 was forgotten that day).

Skip this runbook only on confirmed market holidays (check `trading_calendar`).

---

## Steps

### Step 1 — Refresh Zerodha token on MeridianAlpha AWS (~06:00 IST)

SSH from Local Windows PowerShell:

```bash
ssh -i "C:\MeridianAlpha\Security\malpha-key.pem" ubuntu@13.51.242.119
cd ~/meridian-alpha && source venv/bin/activate && python core/refresh_kite_token.py
```

What to expect:
- Script prints a Kite login URL
- Open URL in a browser, log into Zerodha
- Browser redirects to `http://127.0.0.1/callback?request_token=XXXXXX&...`
- Copy just the `request_token` value (a 32-char string after `request_token=`)
- Paste it when the script prompts `Paste request_token here:`
- Script exchanges it via `kite.generate_session()` and writes the new `ZERODHA_ACCESS_TOKEN` to `~/meridian-alpha/.env`
- Confirmation: `Token refreshed and saved to .env` + truncated access_token preview

### Step 2 — Propagate the new token to MERDIAN AWS (~06:05 IST) — **MANUAL, HIGH RISK**

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

**2c. Patch `.env` on MERDIAN AWS:**

```bash
cd /home/ssm-user/meridian-engine
cp .env .env.bak_$(date +%Y-%m-%d)
sed -i 's|^ZERODHA_ACCESS_TOKEN=.*|ZERODHA_ACCESS_TOKEN=NEW_TOKEN_HERE|' .env
grep ZERODHA_ACCESS_TOKEN .env | tail -c 20
```

Replace `NEW_TOKEN_HERE` with the actual token from step 2a. The `grep | tail -c 20` prints the last 20 chars as a visual confirmation sed replaced correctly.

**Watch-out:** if the paste introduces any trailing whitespace or a stray newline, sed will silently create a broken `.env` line. Always run the verification step 3.

### Step 3 — Verify authentication works on MERDIAN AWS (~06:10 IST) — **MANDATORY**

Without this check, you won't know Step 2 succeeded until 09:14 IST when the cron fires and fails silently. Today's 04-22 outage happened because Step 3 was never run.

Still on MERDIAN AWS:

```bash
cd /home/ssm-user/meridian-engine
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from kiteconnect import KiteConnect
kite = KiteConnect(api_key=os.environ[''ZERODHA_API_KEY''])
kite.set_access_token(os.environ[''ZERODHA_ACCESS_TOKEN''])
try:
    p = kite.profile()
    print(''AUTH OK user:'', p.get(''user_name''))
except Exception as e:
    print(''AUTH FAILED:'', type(e).__name__, ''-'', e)
"
```

Expected: `AUTH OK user: Navin Balan`.

If `AUTH FAILED: TokenException - Incorrect api_key or access_token.` the token didn't propagate correctly. Most likely: wrong token pasted in step 2c, or MeridianAlpha's refresh hadn't actually written the new token (re-run step 1). Return to Step 2.

---

## Verification (end-to-end)

After the 09:14 IST cron fires, verify within 5 minutes:

```sql
-- Confirm market_ticks is ingesting today
SELECT 
    COUNT(*) AS today_rows,
    (MAX(ts) AT TIME ZONE ''Asia/Kolkata'')::timestamp AS latest_tick_ist
FROM public.market_ticks
WHERE ts >= (CURRENT_DATE AT TIME ZONE ''Asia/Kolkata'');
```

Expected: `today_rows` growing rapidly (1000s per minute during active session), `latest_tick_ist` within 60s of current time.

If `today_rows = 0` at 09:20 IST the feeder auth failed silently, check `/home/ssm-user/meridian-engine/logs/ws_feed.log` for `Feed error` loop.

---

## Failure modes

| If you see | It probably means | Do this |
|---|---|---|
| Step 1: `Failed: ...` instead of token refreshed | The request_token was consumed twice or is stale | Re-do browser login, get a fresh request_token, retry Step 1 |
| Step 1: Refresh returns same access_token as yesterday | Kite sometimes returns the same token within a session window - fine if it works | Continue to Step 3 and verify; if `profile()` works, token is valid even if unchanged |
| Step 2c: `sed` silently does nothing, grep shows old token | Token format has a special char that broke sed's replacement pattern | Use `nano .env` directly instead of sed; manually replace the line; save with `Ctrl+O`, `Ctrl+X` |
| Step 3: `AUTH FAILED: TokenException - Incorrect api_key or access_token.` | Token in MERDIAN AWS `.env` doesn't match what Kite expects | Re-read Step 2a token from MeridianAlpha; re-run Step 2c carefully; retry Step 3 |
| Step 3: `AUTH FAILED: NetworkError` | AWS can't reach Kite API | Check instance networking; check if Kite API is down (rare) |
| 09:20 IST: market_ticks zero rows | Feeder started but can't auth - token propagation failed silently | Check `logs/ws_feed.log` for `Feed error` loop; if present, Kite auth broken - redo Steps 2-3 + restart feeder with `pkill -f ws_feed_zerodha.py && nohup python3 ws_feed_zerodha.py >> logs/ws_feed.log 2>&1 &` |
| `equity_intraday_last` hasn't updated today by 09:10 IST | The `refresh_equity_intraday_last.py` cron (09:05 IST) failed, likely also due to stale token | Same underlying cause - fix token propagation (Steps 2-3), then manually run `python3 refresh_equity_intraday_last.py` on AWS |

---

## Related

**Related runbooks:**
- `runbook_update_dhan_token.md` - sibling daily token flow (Dhan broker, separate Task Scheduler on Local Windows, different propagation mechanism via `pull_token_from_supabase.py`)

**Related code files:**
- `~/meridian-alpha/core/refresh_kite_token.py` (MeridianAlpha) - Step 1 script
- `/home/ssm-user/meridian-engine/.env` (MERDIAN AWS) - where token lives
- `/home/ssm-user/meridian-engine/ws_feed_zerodha.py` (MERDIAN AWS) - primary consumer, 09:14 IST cron
- `/home/ssm-user/meridian-engine/refresh_equity_intraday_last.py` (MERDIAN AWS) - secondary consumer, 09:05 IST cron

**Related tables:**
- `market_ticks` - populated by `ws_feed_zerodha.py`; if this is empty mid-session, token propagation likely failed
- `equity_intraday_last` - populated by `refresh_equity_intraday_last.py`; if this is stale, token propagation likely failed
- `market_breadth_intraday` - downstream of `equity_intraday_last`; will silently produce wrong breadth if reference is stale

**Relationship to Dhan:**
- Dhan (Local Windows, via TOTP -> Task Scheduler) and Zerodha (MeridianAlpha AWS, via browser login -> manual SSH) are **independent** broker flows
- Dhan serves SENSEX options + all spot capture; Zerodha serves NIFTY options chain + full equity breadth ticks via WebSocket
- Both tokens must be fresh daily. Different mechanisms, different failure modes. Don't conflate.

**Architectural known-gap (Session 7 finding, 2026-04-23):**
- Step 2 (MeridianAlpha -> MERDIAN AWS sync) is fully manual and silently fragile
- Step 3 verification is not automated - today's 04-22 outage happened because Step 2 was skipped and nothing caught it until signals had been running on stale breadth for hours
- **Proposed improvement (Session 9 candidate):** either (a) automate the SSH+sed via a Local Windows post-hook that fires after `refresh_kite_token.py` completes, or (b) add a pre-flight check on MERDIAN AWS at 09:10 IST that calls `kite.profile()` and alerts via Telegram on failure

---

## Change history

| Date | Change | Commit |
|---|---|---|
| 2026-04-22 | Stub created (empty template) | prior session |
| 2026-04-23 | First real fill - after Session 7 live incident recovery. All placeholders replaced with observed mechanics. | (this commit) |