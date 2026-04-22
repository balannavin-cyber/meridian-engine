# RUNBOOK: Rotate Dhan access token

> **SEED — PARTIALLY FILLED.** Some details I could infer from `merdian_reference.json` and session appendices. Items marked `⚠ NAVIN: FILL` are things only Navin knows. Replace all `⚠` markers with real values the first time this runbook is used, then delete this note.

---

| Field | Value |
|---|---|
| **Operation** | Rotate the Dhan access token used by all local and AWS runners |
| **Frequency** | Daily — Dhan tokens expire overnight; refreshed at 08:15 IST per Change Protocol daily cadence |
| **Environment** | Both Local and AWS (AWS pulls from Supabase `system_config`) |
| **Prerequisites** | Dhan account login credentials · Supabase service role key in `.env` · 08:15 IST task refresh slot |
| **Expected duration** | ⚠ NAVIN: FILL (likely ~2 minutes) |
| **Who can do this** | Navin · automated via Local Task Scheduler at 08:15 IST |
| **Last verified** | ⚠ NAVIN: FILL |

---

## When to use this runbook

Use when:
- Scheduled daily 08:15 IST refresh failed (Telegram FAIL alert)
- A runner is returning DhanError 401
- Live canary preflight Gate 1 (Auth/API smoke) fails on token validation
- Manual rotation after credential change

**Do not use** for any other type of Dhan error — a 500-level error is a Dhan-side issue, not a token issue.

---

## Steps

### 1. Confirm the token is actually the problem

```bash
# On Local, in C:\GammaEnginePython
python -c "from dhanhq import dhanhq; import os; print(dhanhq(os.getenv('DHAN_CLIENT_ID'), os.getenv('DHAN_ACCESS_TOKEN')).get_fund_limits())"
```

*What to expect:* If this returns fund data → token is fine, problem is elsewhere. If it returns `{'status': 'failure', 'remarks': {'error_code': 'DH-901', ...}}` → token has expired, proceed.

### 2. Generate a fresh token

⚠ NAVIN: FILL — document the exact steps. Based on the project context this is likely one of:
- (a) Log into Dhan web portal → API section → regenerate token, OR
- (b) Run an automated TOTP-based refresh script, OR
- (c) Call a token-refresh endpoint with stored credentials

*What to expect:* A new access token string (typically long JWT-style).

### 3. Update the local `.env`

```
# Edit C:\GammaEnginePython\.env
DHAN_ACCESS_TOKEN=<new token>
```

*What to expect:* File saved. No restart needed yet.

### 4. Push the token to Supabase `system_config` (so AWS can pull it)

⚠ NAVIN: FILL — confirm the exact table name and column. Based on the project:
- Table: `system_config`
- The runner on AWS is `pull_token_from_supabase.py` which reads from `system_config` and writes to local `.env`

The update is likely:

```python
# Via a small helper script or direct Supabase SQL:
UPDATE system_config
SET value = '<new token>', updated_at = now()
WHERE key = 'DHAN_ACCESS_TOKEN';   -- ⚠ NAVIN: confirm exact key name
```

*What to expect:* One row updated. `updated_at` reflects now.

### 5. Trigger the AWS pull

On AWS (via SSM Session Manager):

```bash
cd /home/ssm-user/meridian-engine
python3 pull_token_from_supabase.py
```

*What to expect:* Log line indicating token was written to `/home/ssm-user/meridian-engine/.env`. No Dhan API call — this script only reads from Supabase and writes to `.env`.

### 6. Re-run preflight Gate 1 on both environments

Local:
```powershell
# Run the preflight auth stage
⚠ NAVIN: FILL — exact preflight command
```

AWS:
```bash
⚠ NAVIN: FILL — exact preflight command on AWS
```

*What to expect:* Both return PASS. If Local passes but AWS fails, investigate whether `pull_token_from_supabase.py` actually ran (check `/home/ssm-user/meridian-engine/.env` `DHAN_ACCESS_TOKEN` line matches the new value).

---

## Verification

```bash
# On either environment, confirm token is active:
python -c "from dhanhq import dhanhq; import os; from dotenv import load_dotenv; load_dotenv(); print(dhanhq(os.getenv('DHAN_CLIENT_ID'), os.getenv('DHAN_ACCESS_TOKEN')).get_fund_limits())"
```

Expected output: a dict containing `'availabelBalance'` (Dhan spells it this way) or similar fund-state keys, no error code.

---

## Failure modes

| If you see… | It probably means… | Do this |
|---|---|---|
| `DH-901 Invalid Access Token` after Step 2 | Token not regenerated correctly | Re-do Step 2; check for trailing whitespace |
| AWS shows old token after Step 5 | `pull_token_from_supabase.py` did not run or wrote to wrong path | Check AWS `.env` file, re-run pull script, confirm path matches `merdian_reference.json` environments.aws.env_file |
| Local works, AWS returns 401 persistently | AWS system clock drift (Dhan signing is time-sensitive) | Check AWS time: `timedatectl`; resync if drifted |
| Token refresh ran but Telegram never alerted PASS | Telegram credentials or bot token issue, not Dhan issue | See `runbook_recover_telegram_alerts.md` |

---

## Related

- **Related runbooks:** `runbook_recover_dhan_401.md`, `runbook_resolve_hash_mismatch.md`
- **Related tech debt:** none currently
- **Related code files:** `pull_token_from_supabase.py`, `.env`, any runner that uses `DHAN_ACCESS_TOKEN`
- **Related tables:** `system_config`
- **Rule reference:** Change Protocol Rule 6 — "Token refresh at 08:15 IST — before preflight, not after"

---

## Change history

| Date | Change | Commit |
|---|---|---|
| 2026-04-22 | Created as seed runbook (partial fill) | `<hash>` |
| ⚠ | First real use — fill the ⚠ placeholders | |

---

*Runbook — commit with `MERDIAN: [OPS] runbook_update_dhan_token — <action>`.*
