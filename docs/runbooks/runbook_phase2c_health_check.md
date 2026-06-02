# Runbook: Phase 2.c Health Check — ENH-113 Parallel Test Daily Verification

**Status:** Active S42–S43 (5 trading days)  
**Purpose:** Verify both Local + AWS capture writers fire daily, zero gaps, zero errors  
**Success:** All checks ✓ for 5 consecutive trading days → Phase 2.d cutover approved

---

## Quick Start (Run daily, 30 seconds)

### On AWS (terminal)

```bash
cd /home/ssm-user/meridian-engine

# Check all logs for SUCCESS (no 401s, no crashes)
echo "=== CAPTURE LOGS ===" && \
tail -3 /var/log/merdian/capture_spot_aws.log && \
tail -3 /var/log/merdian/ingest_chain_aws.log && \
tail -3 /var/log/merdian/ingest_breadth_aws.log && \
tail -3 /var/log/merdian/ict_zones_aws.log

# Check token freshness (should be < 1 hour old)
echo "=== TOKEN AGE ===" && \
psql "$DATABASE_URL" -c "SELECT updated_at, EXTRACT(HOUR FROM (NOW() - updated_at)) as age_hours FROM system_config WHERE config_key = 'dhan_api_token';"
```

### In Supabase (SQL)

```sql
-- Count bars today (should be ~91 for NIFTY + SENSEX option chains, 09:15–15:30 IST)
SELECT symbol, COUNT(*) as bars_today
FROM option_chain_snapshots
WHERE created_at::date = CURRENT_DATE
GROUP BY symbol
ORDER BY symbol;

-- Expected: NIFTY ~91, SENSEX ~91

-- Check for gaps (query returns any 5-min intervals with NO bars)
WITH 5min_expected AS (
  SELECT generate_series(
    DATE_TRUNC('day', NOW()) + INTERVAL '9 hours 15 minutes',
    DATE_TRUNC('day', NOW()) + INTERVAL '15 hours 30 minutes',
    INTERVAL '5 minutes'
  ) as expected_ts
)
SELECT COUNT(*) as gap_count
FROM 5min_expected
WHERE expected_ts NOT IN (
  SELECT DATE_TRUNC('minute', created_at) FROM option_chain_snapshots
  WHERE created_at::date = CURRENT_DATE
);

-- Expected: gap_count = 0 (no gaps)
```

---

## Full Daily Checklist (3 minutes)

### Morning (after 09:15 IST intraday start)

**On AWS:**
```bash
# 1. Option chain ingest (first cycle ~09:20 IST)
grep -c "Inserted rows returned" /var/log/merdian/ingest_chain_aws.log
# Expected: > 0

# 2. Breadth ingest (first cycle ~09:20 IST)
grep -c "COMPLETED" /var/log/merdian/ingest_breadth_aws.log
# Expected: > 0

# 3. Check for 401 token errors
grep "401\|Authentication Failed" /var/log/merdian/*.log
# Expected: (empty — no 401s)
```

**In Supabase:**
```sql
-- Option chain coverage (FULL mode returns ~470 rows per symbol per cycle)
SELECT symbol, MAX(created_at) as latest_bar_time, COUNT(*) as row_count
FROM option_chain_snapshots
WHERE created_at::date = CURRENT_DATE AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY symbol;

-- Expected: NIFTY and SENSEX both present, row_count > 100 each
```

### Afternoon (after 16:00 IST post-market)

**On AWS:**
```bash
# 4. Spot ingest (16:00 IST)
tail -5 /var/log/merdian/capture_spot_aws.log
# Expected: "Inserted rows: 2" (NIFTY + SENSEX)

# 5. ICT zones rebuild (16:30 IST post-market)
grep "Written.*zones" /var/log/merdian/ict_zones_aws.log | tail -1
# Expected: line showing zones written today
```

**In Supabase:**
```sql
-- Spot snapshot freshness
SELECT symbol, created_at, spot
FROM market_spot_snapshots
WHERE created_at::date = CURRENT_DATE
ORDER BY created_at DESC
LIMIT 2;

-- Expected: NIFTY and SENSEX both present, created_at ~16:00 IST
```

---

## PASS / FAIL Criteria

| Item | PASS | FAIL | Action |
|---|---|---|---|
| All 4 cron jobs fire | ✓ Log entries present for all 4 | ✗ Missing log entries | Check cron with `crontab -l` |
| Option chain bars > 90 | ✓ Both NIFTY + SENSEX | ✗ Count < 90 | Check Dhan API status, token age |
| Zero gaps (5-min cycle) | ✓ gap_count = 0 | ✗ gap_count > 0 | Likely AWS writer missed a cycle; check logs |
| Token age < 1h | ✓ age_hours < 1 | ✗ age_hours >= 1 | Token refresh failed; run `python3 pull_token_from_supabase.py` manually |
| Zero 401 errors | ✓ grep returns empty | ✗ 401 found in logs | Token invalid; run pull script above |
| Spot snapshot present | ✓ 2 rows (NIFTY + SENSEX) | ✗ 0 or 1 rows | Check post-market capture; may need manual run |
| ICT zones written | ✓ "Done -- X zones written" | ✗ No entry or error | Check build_ict_htf_zones.py manually |

---

## Fallback (if any FAIL)

### If token 401 (Option chain or Breadth fails)
```bash
# On AWS
python3 pull_token_from_supabase.py

# Verify both probes 200 OK (shown in output)
# Then retry ingest manually:
python3 ingest_option_chain_local.py NIFTY FULL
python3 ingest_option_chain_local.py SENSEX FULL
```

### If spot snapshot or ICT zones missing
```bash
# On AWS, manual run:
python3 capture_market_spot_snapshot_local.py
python3 build_ict_htf_zones.py --timeframe D
python3 build_ict_htf_zones.py --timeframe H
```

### If option chain gap (>5-min with zero bars)
Check AWS log for 429 rate limits:
```bash
grep "429\|rate" /var/log/merdian/ingest_chain_aws.log | tail -5
```
If found, Dhan is throttling; Supabase retry layer should catch it. If persistent, report to operations.

### If all AWS fails (systematic failure)

**Revert to Local-only (temporary):**

On Local Windows:
```powershell
# Re-enable Local tasks manually
Enable-ScheduledTask -TaskName "MERDIAN_Post_Market_1600_Capture"

# Verify supervisor (intraday chain + breadth) is running
Get-ScheduledTask -TaskName "MERDIAN_Intraday_Supervisor_Start" | Select-Object State

# Check Local logs for SUCCESS
Get-Content C:\GammaEnginePython\logs\* | Select-String "SUCCESS" | Select -Last 5
```

Then file TD-NEW (capture/AWS failure root cause) and resume Phase 2.c on next day after investigation.

---

## Daily Log Template (copy-paste to track)

```
[DATE] — Phase 2.c Day N/5

Option chain: [✓ or ✗ + issue]
Breadth: [✓ or ✗ + issue]
Spot: [✓ or ✗ + issue]
ICT zones: [✓ or ✗ + issue]
Token age: [<1h or > 1h issue]
Data gaps: [none or describe]

Notes: [any observations]
```

---

*Phase 2.c Health Check — 2026-06-01 S42. Run daily 09:30 IST + 16:30 IST. 5 days to pass.*
