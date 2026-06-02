# Runbook: Phase 2.c Fallback & Rollback — ENH-113 Capture Writer Migration

**Scope:** Procedures if AWS capture writers fail during 5-day parallel test  
**Status:** Standby (activate only if daily health check fails)  
**Authority:** ENH-113 Phase 2 contingency

---

## Scenario 1: Single Writer Failure (Token/API issue)

### If Option Chain ingest fails (401 or rate limit)

**Symptom:** `ingest_chain_aws.log` shows "401" or "429" errors; Supabase has gap in `option_chain_snapshots`.

**Immediate fix (AWS):**
```bash
cd /home/ssm-user/meridian-engine

# Refresh token from Supabase
python3 pull_token_from_supabase.py

# Verify both Dhan probes pass (output shows "200 OK" x2)
# Then manually re-ingest latest cycle
python3 ingest_option_chain_local.py NIFTY FULL
python3 ingest_option_chain_local.py SENSEX FULL

# Check logs for SUCCESS
tail -10 /var/log/merdian/ingest_chain_aws.log
```

**If still fails after 2 attempts:**
```bash
# Fall back to Local: manually run on Windows
# (see "Scenario 3: Local Fallback" below)
```

---

### If Breadth ingest fails

**Symptom:** `ingest_breadth_aws.log` shows errors; Supabase `market_breadth_intraday` has gaps.

**Immediate fix (AWS):**
```bash
cd /home/ssm-user/meridian-engine
python3 ingest_breadth_intraday_local.py

# Check log
tail -10 /var/log/merdian/ingest_breadth_aws.log
```

**If fails after 2 attempts → Local fallback.**

---

### If Spot snapshot fails

**Symptom:** Post-market 16:00 IST passes but `capture_spot_aws.log` shows error or 0 rows written.

**Immediate fix (AWS):**
```bash
cd /home/ssm-user/meridian-engine
python3 capture_market_spot_snapshot_local.py

# Check log
tail -5 /var/log/merdian/capture_spot_aws.log
# Expected: "Inserted rows: 2"
```

**If fails → Local fallback.**

---

### If ICT zones rebuild fails

**Symptom:** Daily or hourly zone rebuild hangs or produces no zones; `ict_zones_aws.log` shows error.

**Immediate fix (AWS):**
```bash
cd /home/ssm-user/meridian-engine

# Run daily zones rebuild manually (16:30 IST window)
timeout 120 python3 build_ict_htf_zones.py --timeframe D

# Run hourly zones rebuild (manual test)
timeout 120 python3 build_ict_htf_zones.py --timeframe H

# Check log
tail -20 /var/log/merdian/ict_zones_aws.log
```

**If rebuilds still fail after 2 attempts → Escalate as TD (zone builder issue, not writer issue).**

---

## Scenario 2: Systematic AWS Failure (All writers down)

**Symptom:** All 4 cron logs empty or all show errors; Supabase receives no new data for >2 hours.

**Diagnosis (AWS):**
```bash
# Check if Python works
python3 --version
# Expected: Python 3.10.x

# Check if cron daemon is running
systemctl status cron

# Check if .env is readable and valid
cat /home/ssm-user/meridian-engine/.env | grep DHAN_API_TOKEN
# Expected: token=eyJ0eX...

# Manually test one writer
cd /home/ssm-user/meridian-engine
python3 capture_market_spot_snapshot_local.py 2>&1 | head -20
# Should show SUCCESS or traceable error, not hang
```

### If diagnosis unclear

**Revert to Local-only (temporary):**

1. **Disable AWS cron temporarily:**
   ```bash
   crontab -e
   # Comment out all Phase 2.b lines (add # to start of each)
   # Save
   
   # Verify disabled
   crontab -l | grep -v "^#" | wc -l
   # Should show 0 or only non-Phase-2b entries
   ```

2. **On Local Windows, re-enable capture tasks:**
   ```powershell
   Enable-ScheduledTask -TaskName "MERDIAN_Post_Market_1600_Capture"
   Enable-ScheduledTask -TaskName "MERDIAN_Intraday_Session_Start"
   Enable-ScheduledTask -TaskName "MERDIAN_Intraday_Supervisor_Start"
   
   # Verify
   Get-ScheduledTask | Where-Object {$_.TaskName -like "MERDIAN_*Session*" -or $_.TaskName -like "*Capture"} | Select TaskName, State
   ```

3. **Verify Local writers fire next cycle:**
   ```powershell
   # Check Local logs (in next 10 minutes)
   Get-Content C:\GammaEnginePython\logs\supervisor.log | Select -Last 20
   # Should show ingest operations
   ```

4. **File incident:**
   ```
   TD-NEW: Phase 2.c AWS systematic failure — reverted to Local pending root cause analysis
   - Date: YYYY-MM-DD
   - Symptom: [describe all 4 writers failed]
   - Root cause: [TBD]
   - Mitigation: Local writers re-enabled, parallel test paused
   - Action: Resume Phase 2.c S43 after fix verification
   ```

---

## Scenario 3: Local Fallback (One-time manual recovery)

If AWS writer fails and immediate fix doesn't work, manually ingest using Local.

### On Local Windows

```powershell
cd C:\GammaEnginePython

# Option chain (both NIFTY and SENSEX)
python ingest_option_chain_local.py NIFTY FULL
python ingest_option_chain_local.py SENSEX FULL

# Breadth
python ingest_breadth_intraday_local.py

# Spot (post-market)
python capture_market_spot_snapshot_local.py

# ICT zones
python build_ict_htf_zones.py --timeframe D
python build_ict_htf_zones.py --timeframe H

# All should show SUCCESS and inserted row counts
```

**Result:** Data written to same Supabase tables. Downstream consumers (gamma_metrics, etc.) unaffected — they read from the tables, not from Local/AWS distinction.

---

## Scenario 4: Full Rollback (Abandon Phase 2.c, stay on Local-only)

If AWS fails repeatedly and no fix found, abort parallel test and rollback to Local-only.

### On AWS, permanently disable Phase 2.b cron:

```bash
crontab -e
# Delete ALL Phase 2.b lines (capture_*, ingest_*, build_ict lines)
# Keep only Phase 1.c (token refresh)
# Save

# Verify only token refresh remains
crontab -l | grep -v "^#"
# Expected: only token refresh + any other existing crons
```

### On Local Windows, ensure tasks enabled:

```powershell
Enable-ScheduledTask -TaskName "MERDIAN_Post_Market_1600_Capture"
Enable-ScheduledTask -TaskName "MERDIAN_Intraday_Session_Start"
Enable-ScheduledTask -TaskName "MERDIAN_Intraday_Supervisor_Start"
```

### Commit rollback:

```powershell
cd C:\GammaEnginePython
git add -A
git commit -m "ENH-113 Phase 2.c ROLLBACK: AWS capture writer migration abandoned

Reason: [describe systematic failure]
AWS token refresh (Phase 1.c) remains active.
Local capture writers re-enabled pending investigation.
Filing TD-NEW for root cause analysis.

Partial rollback: AWS token refresh retained (TD-S41-NEW-2 still solved).
Full forward progress: only Phase 1 of ADR-006 remains active."
git push origin main
```

---

## Monitoring During Recovery

Track on daily health check:

| Day | Status | Action |
|---|---|---|
| D1 | AWS fail → immediate fix attempt | If success, continue test. If fail, Local fallback. |
| D2 | Monitor Local + AWS together | If both work, continue parallel test. |
| D3–D5 | Daily verification | If no further issues, Phase 2.c PASS → Phase 2.d cutover approved. |

---

## Decision Tree

```
AWS writer fails
├─ Token 401?
│  └─ python3 pull_token_from_supabase.py
│     ├─ Success → Retry writer, continue test
│     └─ Fail → Escalate, Local fallback
├─ Data gap but no error log?
│  └─ Likely rate limit or network glitch → Retry, continue test
├─ Timeout or hang?
│  └─ Check `ps aux | grep python` for stale processes → Kill, retry
└─ Multiple writers fail?
   └─ Disable AWS cron, re-enable Local, file TD-NEW
```

---

*Phase 2.c Fallback Runbook — 2026-06-01 S42. Activate on daily health check failure.*
