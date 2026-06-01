# Phase 1.c Execution Plan: AWS Token Refresh Refactoring (S42)

## Status: Deliverables Ready

**Sub-1.c.1 ✅** Portable library created: `dhan_token_refresh_lib.py`
**Sub-1.c.2 ✅** AWS wrapper created: `refresh_dhan_token_aws.py`
**Sub-1.c.3 ⏳** Cron dispatcher setup (this document)
**Sub-1.c.4 ⏳** Credentials hardening plan
**Sub-1.c.5 ⏳** Parallel testing design
**Sub-1.c.6 ⏳** Cutover procedure

---

## Sub-1.c.3: AWS Cron Dispatcher Setup

### Option A: Add to existing cron in /home/ssm-user/meridian-engine

Current AWS runner likely has cron entries. Add this line to `/etc/cron.d/merdian` or equivalent:

```bash
15 08 * * 1-5 ssm-user cd /home/ssm-user/meridian-engine && /usr/bin/python3 refresh_dhan_token_aws.py >> /var/log/merdian/token_refresh_aws.log 2>&1
```

**Breakdown:**
- `15 08` = 08:15 IST daily
- `* * 1-5` = Mon–Fri (1=Mon, 5=Fri)
- `ssm-user` = run as ssm-user (adjust for your AWS setup)
- `cd /home/ssm-user/meridian-engine` = ensure correct path
- `python3 refresh_dhan_token_aws.py` = execute script
- `>> /var/log/merdian/token_refresh_aws.log 2>&1` = log output

### Option B: SystemD timer (more modern)

Create `/etc/systemd/system/merdian-dhan-token-refresh.service`:

```ini
[Unit]
Description=MERDIAN Dhan Token Refresh (AWS)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ssm-user
WorkingDirectory=/home/ssm-user/meridian-engine
ExecStart=/usr/bin/python3 /home/ssm-user/meridian-engine/refresh_dhan_token_aws.py
StandardOutput=append:/var/log/merdian/token_refresh_aws.log
StandardError=append:/var/log/merdian/token_refresh_aws.log
EnvironmentFile=/home/ssm-user/meridian-engine/.env
```

Create `/etc/systemd/system/merdian-dhan-token-refresh.timer`:

```ini
[Unit]
Description=MERDIAN Dhan Token Refresh Timer (AWS)

[Timer]
OnCalendar=Mon-Fri 08:15:00 IST
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable merdian-dhan-token-refresh.timer
sudo systemctl start merdian-dhan-token-refresh.timer
sudo systemctl status merdian-dhan-token-refresh.timer
```

---

## Sub-1.c.4: Credentials Hardening Plan

**Current state:**
- Credentials stored in `/home/ssm-user/meridian-engine/.env` (plain text, in repo)
- Risk: .env may be version-controlled or exposed

**Phase 1.c.4 Execution:**

### Path A: AWS Secrets Manager (recommended for AWS)

1. Store credentials in AWS Secrets Manager:
```bash
aws secretsmanager create-secret --name merdian/dhan-credentials \
  --secret-string '{"client_id":"...", "pin":"...", "totp_seed":"..."}'
```

2. Modify `refresh_dhan_token_aws.py` to read from Secrets Manager instead of .env:
```python
import boto3

secrets_client = boto3.client('secretsmanager', region_name='eu-north-1')
secret = secrets_client.get_secret_value(SecretId='merdian/dhan-credentials')
creds = json.loads(secret['SecretString'])
client_id = creds['client_id']
pin = creds['pin']
totp_seed = creds['totp_seed']
```

3. Supabase credentials remain in .env (less sensitive — just API key to read config table).

4. Local Windows continues to use .env (no exposure risk on local machine).

### Path B: Supabase secure config table

Store credentials in a new table `secure_credentials` encrypted at rest in Supabase:
- Requires additional DDL and migration
- Adds dependency on Supabase availability for credential fetch
- More complex but consistent with existing architecture

**Recommendation:** Path A (Secrets Manager) for Phase 1.c. Path B can be future work.

---

## Sub-1.c.5: Parallel Testing Design (5 trading days)

### Day 1–5: Both Local and AWS refresh, write to Supabase

**Local side (unchanged):**
- `MERDIAN_Dhan_Token_Refresh` Task Scheduler runs at 08:15 IST (with WAKETOWRUN)
- Calls `refresh_dhan_token.py`
- Writes to Supabase `system_config.dhan_api_token`
- Writes to local `runtime/token_status.json`

**AWS side (new):**
- Cron job runs `refresh_dhan_token_aws.py` at 08:15 IST
- Calls same Dhan API
- Writes to Supabase `system_config.dhan_api_token` (same row)

**Race condition handling:**
- Both write to same Supabase row at ~same time
- Last writer wins (Supabase `updated_at` timestamp determines canonical)
- Acceptable for Phase 1.c testing — verify no collisions or errors in logs

**Verification (daily):**
1. Check `script_execution_log` for both refresh tasks firing at 08:15 IST
2. Verify `system_config.dhan_api_token.updated_at` has recent timestamp
3. Check `dhan_token_probe_log` for any staleness_check_failed events (should be zero during parallel test)
4. Log summary: both writes succeeded, token age < 1 hour, no 401 errors in downstream writers

**Test window:** 5 clean trading days (assume Mon–Fri, no holidays)

**Pass criteria:**
- Local refresh completes and writes to Supabase
- AWS refresh completes and writes to Supabase
- Token age in Supabase is always < 1 hour at next writer's pull time (03:05 UTC)
- No Mode B 401 errors in any downstream writers
- No staleness_check_failed events in dhan_token_probe_log

---

## Sub-1.c.6: Cutover Procedure

**Go/No-Go Decision (Day 6):**
Review 5-day test results. If all pass criteria met:

### Cutover Steps:

**Step 1: Disable Local refresh task** (08:15 IST)
```powershell
Disable-ScheduledTask -TaskName "MERDIAN_Dhan_Token_Refresh" -Confirm:$false
Get-ScheduledTask -TaskName "MERDIAN_Dhan_Token_Refresh" | Select-Object State
```

**Step 2: Verify AWS continues alone** (08:15 IST next day)
- Check Supabase `system_config.dhan_api_token.updated_at` has fresh timestamp
- Verify `script_execution_log` shows AWS refresh only (no Local task)
- Verify token age < 1 hour at next writer pull time

**Step 3: Monitor for 1 trading day**
- No Mode B 401 errors
- No staleness_check_failed events
- Downstream writers all report success

**Step 4: Document cutover**
- Update `merdian_reference.json` task inventory (mark Local task DISABLED, AWS task CANONICAL)
- Update `MERDIAN_Deployment_Topology.md` with new AWS cron entry
- File commit: "S42 Phase 1.c CUTOVER: move Dhan token refresh to AWS (TD-S41-NEW-2 architectural fix)"

**Rollback plan (if issues arise during cutover):**
1. Re-enable Local Task Scheduler task
2. Verify Local writes to Supabase
3. Disable AWS cron
4. Verify no token staleness

---

## Timeline Summary

| Sub-task | Effort | Timeline |
|---|---|---|
| **1.c.1** Library extraction | 30 min | ✅ Done |
| **1.c.2** AWS wrapper | 30 min | ✅ Done |
| **1.c.3** Cron setup | 20 min | Today (S42) |
| **1.c.4** Credentials hardening | 1–2 hr | Today–S43 |
| **1.c.5** Parallel test (5 days) | Observation | S42–S43 boundary |
| **1.c.6** Cutover (1 day) | 30 min | S43 |

**Total hands-on:** ~4 hours  
**Total calendar:** 6–7 trading days (5 test + 1 cutover verification)

---

## Next Action

**Choose cron setup path (Option A or B) and confirm:**
- Cron path preference
- Secrets Manager availability on AWS
- Ready to deploy dhan_token_refresh_lib.py + refresh_dhan_token_aws.py to git today?
