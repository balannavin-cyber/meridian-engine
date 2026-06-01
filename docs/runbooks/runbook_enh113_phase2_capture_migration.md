# Runbook: ENH-113 Phase 2 — Capture Writer AWS Migration

**Status:** Actionable S42+  
**Objective:** Migrate five Local capture writers → AWS, eliminate laptop dependency  
**Success:** All writers fire on AWS, Local disabled, zero data gaps

---

## Phase 2.a: Pre-Migration Audit (S42)

### Writer 1: `ingest_market_spot_snapshots.py`

**Current (Local):**
- Task Scheduler: `MERDIAN_Post_Market_1600_Capture` at 16:00 IST
- Fetches NSE closing spot via Zerodha Kite API
- Writes to Supabase `market_spot_snapshots`

**AWS compatibility check:**
- ✅ No filesystem access
- ✅ Uses Kite API (credentials in .env)
- ✅ Supabase write (same as all writers)
- **Action:** Copy as-is to AWS, add cron entry

**Cron entry (AWS):**
```
00 16 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_market_spot_snapshots.py >> /var/log/merdian/ingest_spot_aws.log 2>&1
```

---

### Writer 2: `ingest_option_chain_snapshots.py`

**Current (Local):**
- Task Scheduler: `MERDIAN_Intraday_Option_Chain_5m` at 5-min cycle (09:15, 09:20, ... 15:30 IST)
- Fetches option chain (strike, IV, gamma, OI, etc.)
- Writes to `option_chain_snapshots`

**AWS compatibility check:**
- ✅ No filesystem access
- ✅ Dhan API (credentials in .env)
- ✅ Supabase write
- **Action:** Copy as-is, add cron entries (one for each 5-min firing)

**Cron entries (AWS):**
```
15,20,25,30,35,40,45,50,55 09 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_option_chain_snapshots.py >> /var/log/merdian/ingest_chain_aws.log 2>&1
00,05,10,15,20,25,30,35,40,45,50,55 10-15 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_option_chain_snapshots.py >> /var/log/merdian/ingest_chain_aws.log 2>&1
```

---

### Writer 3: `capture_india_vix.py`

**Current (Local):**
- Part of gamma metrics computation, runs intraday
- Fetches India VIX from Dhan (security_id=21)

**AWS compatibility check:**
- ✅ Dhan API
- ✅ Supabase write (or part of gamma_metrics batch)
- **Action:** Already embedded in compute_gamma_metrics flow; verify it runs on AWS

**Note:** May already be running on AWS shadow runner. Confirm in `script_execution_log` for VIX writes.

---

### Writer 4: `ingest_breadth_intraday_local.py`

**Current (Local):**
- Task Scheduler: `MERDIAN_Intraday_Breadth_5m` at 5-min cycle
- Fetches market breadth (advances/declines) from Zerodha Kite
- Writes to `market_breadth_intraday`, `weighted_constituent_breadth_snapshots`

**AWS compatibility check:**
- ✅ Kite API
- ✅ Supabase write
- **Action:** Copy as-is, add cron entries (5-min cycle 09:15–15:30 IST)

**Cron entries (AWS):**
```
15,20,25,30,35,40,45,50,55 09 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_breadth_intraday_local.py >> /var/log/merdian/ingest_breadth_aws.log 2>&1
00,05,10,15,20,25,30,35,40,45,50,55 10-15 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_breadth_intraday_local.py >> /var/log/merdian/ingest_breadth_aws.log 2>&1
```

---

### Writer 5: `build_ict_htf_zones.py`

**Current (Local):**
- Manually triggered or via orchestration at specific times
- Rebuilds ICT zones (Daily, Hourly, 5-min) from bar data
- Writes to `ict_htf_zones`

**AWS compatibility check:**
- ✅ Reads from `hist_option_bars_*m` tables (Supabase)
- ✅ Supabase write
- **Action:** Copy as-is, add cron entries (post-market + hourly rebuilds)

**Cron entries (AWS):**
```
# Post-market rebuild (16:30 IST)
30 16 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 build_ict_htf_zones.py --timeframe D >> /var/log/merdian/ict_zones_aws.log 2>&1

# Hourly rebuild (08:45, 09:45, ... 15:45 IST)
45 08,09,10,11,12,13,14,15 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 build_ict_htf_zones.py --timeframe H >> /var/log/merdian/ict_zones_aws.log 2>&1
```

---

## Phase 2.b: AWS Deployment (S42–S43)

### Step 1: Copy scripts to AWS

On AWS:
```bash
cd /home/ssm-user/meridian-engine
git pull origin main  # Ensure latest

# Scripts should already be there from repo.
# Verify:
ls -la ingest_market_spot_snapshots.py \
       ingest_option_chain_snapshots.py \
       ingest_breadth_intraday_local.py \
       build_ict_htf_zones.py
```

### Step 2: Create log directory

```bash
sudo mkdir -p /var/log/merdian
sudo chown ssm-user:ssm-user /var/log/merdian
```

### Step 3: Add all cron entries

Combine entries from above and add to crontab:

```bash
(crontab -l 2>/dev/null; cat << 'CRON_ENTRIES'
# Capture writers — Phase 2 AWS migration (ENH-113)
00 16 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_market_spot_snapshots.py >> /var/log/merdian/ingest_spot_aws.log 2>&1
15,20,25,30,35,40,45,50,55 09 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_option_chain_snapshots.py >> /var/log/merdian/ingest_chain_aws.log 2>&1
00,05,10,15,20,25,30,35,40,45,50,55 10-15 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_option_chain_snapshots.py >> /var/log/merdian/ingest_chain_aws.log 2>&1
15,20,25,30,35,40,45,50,55 09 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_breadth_intraday_local.py >> /var/log/merdian/ingest_breadth_aws.log 2>&1
00,05,10,15,20,25,30,35,40,45,50,55 10-15 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 ingest_breadth_intraday_local.py >> /var/log/merdian/ingest_breadth_aws.log 2>&1
30 16 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 build_ict_htf_zones.py --timeframe D >> /var/log/merdian/ict_zones_aws.log 2>&1
45 08,09,10,11,12,13,14,15 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 build_ict_htf_zones.py --timeframe H >> /var/log/merdian/ict_zones_aws.log 2>&1
CRON_ENTRIES
) | crontab -

# Verify
crontab -l | grep "ingest_\|build_ict"
```

### Step 4: Manual test each writer

```bash
cd /home/ssm-user/meridian-engine

# Test spot ingest
python3 ingest_market_spot_snapshots.py

# Test option chain
python3 ingest_option_chain_snapshots.py

# Test breadth
python3 ingest_breadth_intraday_local.py

# Test ICT zones
python3 build_ict_htf_zones.py --timeframe D
python3 build_ict_htf_zones.py --timeframe H
```

All should report SUCCESS and write to respective log files.

---

## Phase 2.c: Parallel Testing (5 trading days, S43)

### Daily Checklist

**Morning (after 08:15 IST token refresh + 09:15 IST intraday start):**

1. **Token refresh (already verified):**
   ```bash
   tail -5 /var/log/merdian/token_refresh_aws.log
   # Should show: ✓ Token obtained + ✓ Token written
   ```

2. **Option chain ingest:**
   ```bash
   grep "SUCCESS" /var/log/merdian/ingest_chain_aws.log | wc -l
   # Should be > 0 (at least one successful run by 09:20 IST)
   ```

3. **Breadth ingest:**
   ```bash
   grep "SUCCESS" /var/log/merdian/ingest_breadth_aws.log | wc -l
   # Should be > 0
   ```

4. **ICT zones:**
   ```bash
   grep "SUCCESS" /var/log/merdian/ict_zones_aws.log | wc -l
   # Should be > 0 (hourly rebuilds 08:45, 09:45, etc.)
   ```

**Afternoon (post-market 16:00 IST):**

5. **Spot ingest:**
   ```bash
   tail -5 /var/log/merdian/ingest_spot_aws.log
   # Should show: ✓ Spot snapshot written
   ```

6. **Post-market ICT rebuild:**
   ```bash
   grep "16:" /var/log/merdian/ict_zones_aws.log | grep SUCCESS
   # Should appear ~16:30 IST
   ```

**Data validation (SQL):**

```sql
-- Check for gaps in option_chain_snapshots (should be continuous 5-min bars)
SELECT created_at::date, COUNT(*) as bar_count
FROM option_chain_snapshots
WHERE created_at::date = CURRENT_DATE
GROUP BY created_at::date;

-- Should show 91 bars (09:15 to 15:30 IST = 6h 15m = 375 min / 5 = 75 bars... adjust for actual market hours)

-- Check token age
SELECT updated_at, EXTRACT(HOUR FROM (NOW() - updated_at)) as age_hours
FROM system_config WHERE config_key = 'dhan_api_token';

-- Should show age < 1 hour
```

### Pass Criteria

- ✅ All five writers fire daily for 5 trading days
- ✅ Zero data gaps in any capture table
- ✅ Token age < 1h at all times
- ✅ Zero 401 token errors in `script_execution_log`
- ✅ No errors in cron logs

---

## Phase 2.d: Cutover (S43–S44)

### Step 1: Disable Local capture tasks (on Local Windows)

```powershell
# Post-market spot
Disable-ScheduledTask -TaskName "MERDIAN_Post_Market_1600_Capture" -Confirm:$false

# Intraday option chain (5-min cycle)
Disable-ScheduledTask -TaskName "MERDIAN_Intraday_Option_Chain_5m" -Confirm:$false

# Intraday breadth (5-min cycle)
Disable-ScheduledTask -TaskName "MERDIAN_Intraday_Breadth_5m" -Confirm:$false

# Verify all disabled
Get-ScheduledTask -TaskName "MERDIAN_Post_Market_1600_Capture",
                           "MERDIAN_Intraday_Option_Chain_5m",
                           "MERDIAN_Intraday_Breadth_5m" | Select-Object TaskName, State
```

### Step 2: Verify AWS continues (1 trading day)

Next day, run same daily checklist (Phase 2.c). Confirm all writers fire successfully on AWS alone.

### Step 3: Commit cutover

```powershell
cd C:\GammaEnginePython
git add -A
git commit -m "ENH-113 Phase 2 CUTOVER: capture writers moved to AWS (ADR-006 Phase 2 complete)

- Disabled Local capture tasks:
  - MERDIAN_Post_Market_1600_Capture
  - MERDIAN_Intraday_Option_Chain_5m
  - MERDIAN_Intraday_Breadth_5m
- AWS cron active for all five writers
- 5-day parallel test: PASS
- Zero data gaps post-cutover
- Laptop dependency eliminated for market data ingest"
git push origin main
```

---

## Phase 2.e: Derived-Layer Validation (S44)

Verify downstream consumers (gamma_metrics, volatility, etc.) process AWS capture data correctly.

**Checklist:**
1. gamma_metrics runs successfully on AWS-sourced option chain data
2. Signal quality (win rates, directional accuracy) unchanged post-cutover
3. No regression in overlay zones (PIN, ACCEL, ICT patterns)

---

## Rollback (if cutover fails)

**Re-enable Local tasks:**
```powershell
Enable-ScheduledTask -TaskName "MERDIAN_Post_Market_1600_Capture"
Enable-ScheduledTask -TaskName "MERDIAN_Intraday_Option_Chain_5m"
Enable-ScheduledTask -TaskName "MERDIAN_Intraday_Breadth_5m"

# Disable AWS cron (on AWS)
# crontab -e, delete capture writer entries, save
```

**Commit rollback:**
```
"ENH-113 Phase 2 ROLLBACK: reverted to Local capture writers (identified [issue])"
```

---

## Manual Fallback (permanent)

Even after cutover, Local scripts remain as manual fallback:

```powershell
# If AWS writer fails, operator can manually run:
cd C:\GammaEnginePython
python ingest_market_spot_snapshots.py
python ingest_option_chain_snapshots.py
python ingest_breadth_intraday_local.py
python build_ict_htf_zones.py --timeframe D
```

Scripts write to same Supabase tables. Downstream consumers automatically pick up manually-ingested data.

---

*Runbook created 2026-06-01 (S42). ENH-113 actionable S42–S44.*
