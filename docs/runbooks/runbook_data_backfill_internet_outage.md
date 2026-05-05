# MERDIAN Data Backfill Runbook — Internet Outage Recovery

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | runbook_data_backfill_internet_outage.md |
| Version | v1 |
| Created | 2026-05-04 |
| Type | Runbook — operational procedure |
| Trigger | Internet outage causing data gaps in MERDIAN primary tables |
| Location | `docs/runbooks/` |

---

## Purpose

Handle complete data recovery when internet connectivity disrupts MERDIAN's real-time data collection, causing gaps in:
- Spot price bars (`hist_spot_bars_1m`)
- Options premium bars (`hist_option_bars_1m`) 
- Option chain snapshots (`option_chain_snapshots`)
- Market state snapshots (`market_state_snapshots`)
- Signal snapshots (`signal_snapshots`)

**Success criteria:** Complete data integrity restored, pattern detection fully functional, no gaps in historical continuity.

---

## When to Use This Runbook

**Primary triggers:**
- Internet outage during market hours (9:15-15:30 IST)
- ISP failover causing data collection gaps
- Network-related MERDIAN process failures
- WiFi/router issues affecting laptop connectivity

**Detection signals:**
- Flat OHLC bars (O=H=L=C) in spot data
- Zero option bars for trade_date
- Missing option chain snapshots during market hours
- Pattern detection showing zero Order Block patterns
- `merdian_daily_audit.py` reporting data gaps

**When NOT to use:**
- Single instrument failures (broker API issues)
- Partial data (some instruments working)
- After-market data gaps (use standard backfill)
- Schema or processing errors (not connectivity)

---

## Prerequisites

**Environment access:**
- Local Windows: `C:\GammaEnginePython\` 
- AWS access: MeridianAlpha instance (`13.51.242.119`)
- Supabase credentials: Working `.env` files both environments

**Required tools:**
- Kite API credentials (active session)
- Git access (for committing backfill scripts)
- Database access (Supabase SQL editor or CLI)

**Preparation check:**
```powershell
# Verify Kite API access
python -c "from kiteconnect import KiteConnect; import os; from dotenv import load_dotenv; load_dotenv(); kite = KiteConnect(api_key=os.environ['KITE_API_KEY']); kite.set_access_token(os.environ['KITE_ACCESS_TOKEN']); print('Kite auth:', kite.profile()['user_id'])"

# Verify Supabase access  
python -c "import requests, os; from dotenv import load_dotenv; load_dotenv(); response = requests.get(f'{os.environ[\"SUPABASE_URL\"]}/rest/v1/', headers={'apikey': os.environ['SUPABASE_SERVICE_ROLE_KEY']}); print('Supabase:', response.status_code)"
```

---

## Diagnostic Phase

### Step 1: Assess Data Gaps

**Check spot data quality:**
```sql
-- Identify corrupted spot data (flat bars)
SELECT 
    trade_date,
    symbol,
    COUNT(*) as total_bars,
    COUNT(CASE WHEN open = high AND high = low AND low = close THEN 1 END) as flat_bars,
    COUNT(CASE WHEN open = high AND high = low AND low = close THEN 1 END) * 100.0 / COUNT(*) as flat_percentage
FROM hist_spot_bars_1m 
WHERE trade_date >= CURRENT_DATE - INTERVAL '5 days'
GROUP BY trade_date, symbol
HAVING COUNT(CASE WHEN open = high AND high = low AND low = close THEN 1 END) > 0
ORDER BY trade_date DESC, symbol;
```

**Check options data gaps:**
```sql
-- Check option bars coverage
SELECT 
    trade_date,
    COUNT(*) as total_option_bars,
    COUNT(DISTINCT strike) as strikes_count,
    COUNT(DISTINCT option_type) as types_count
FROM hist_option_bars_1m 
WHERE trade_date >= CURRENT_DATE - INTERVAL '3 days'
GROUP BY trade_date
ORDER BY trade_date DESC;

-- Check option chain coverage
SELECT 
    DATE(created_at AT TIME ZONE 'Asia/Kolkata') as trade_date,
    COUNT(*) as snapshots,
    MIN(created_at AT TIME ZONE 'Asia/Kolkata') as first_snapshot,
    MAX(created_at AT TIME ZONE 'Asia/Kolkata') as last_snapshot
FROM option_chain_snapshots 
WHERE created_at >= CURRENT_DATE - INTERVAL '3 days'
GROUP BY DATE(created_at AT TIME ZONE 'Asia/Kolkata')
ORDER BY trade_date DESC;
```

**Pattern detection verification:**
```sql
-- Verify pattern detection is working
SELECT 
    trade_date,
    pattern_type,
    COUNT(*) as pattern_count
FROM ict_patterns 
WHERE trade_date >= CURRENT_DATE - INTERVAL '3 days'
GROUP BY trade_date, pattern_type
ORDER BY trade_date DESC, pattern_type;
```

### Step 2: Determine Backfill Scope

**Based on diagnostic results, determine what needs backfill:**

| Data Type | Criteria | Action |
|---|---|---|
| Spot bars | >50% flat bars OR <700 total bars for trade date | Spot backfill required |
| Option bars | 0 bars for trade date OR <1000 total bars | Option backfill required |
| Option chain | <50,000 snapshots for trade date | Usually preserved, verify only |
| Market state | <200 snapshots for trade date | Check dependency on other data |
| Patterns | 0 OB patterns but >10 FVG patterns | Data quality issue, verify after backfill |

---

## Recovery Phase

### Phase 1: Spot Data Recovery

**When:** Flat bars detected OR insufficient bar count for trade date

**Location:** AWS MeridianAlpha (has working Kite credentials)

```bash
# SSH to AWS
ssh -i "C:\MeridianAlpha\Security\malpha-key.pem" ubuntu@13.51.242.119

# Navigate to working directory
cd ~/meridian-alpha

# Check current spot backfill script status
ls -la backfill_spot_zerodha.py

# Edit BACKFILL_DATES to include missing date(s)
sudo nano backfill_spot_zerodha.py
# Add: date(2026, 5, 4),  # or whatever date needs backfill

# Test with dry run
python3 backfill_spot_zerodha.py --dry-run

# Run live backfill
python3 backfill_spot_zerodha.py

# Verify results
```

**Verification query:**
```sql
SELECT 
    symbol,
    COUNT(*) as bars,
    COUNT(CASE WHEN open = high AND high = low AND low = close THEN 1 END) as flat_bars,
    MIN(bar_ts AT TIME ZONE 'Asia/Kolkata') as first_bar,
    MAX(bar_ts AT TIME ZONE 'Asia/Kolkata') as last_bar
FROM hist_spot_bars_1m 
WHERE trade_date = '2026-05-04'  -- Replace with target date
GROUP BY symbol;
```

**Expected result:** 375 bars per symbol, 0 flat bars, time range 09:15-15:29 IST

### Phase 2: Options Data Recovery

**When:** Missing option bars for trade date

**Location:** AWS MeridianAlpha (script exists but may need schema updates)

**⚠️ Critical:** Options backfill requires proper schema mapping and constraint handling.

```bash
# Check if options backfill script exists
ls -la backfill_option_zerodha*.py

# If missing, use the schema-corrected version from this session
# Copy from local to AWS:
# scp -i "C:\MeridianAlpha\Security\malpha-key.pem" "C:\Path\To\backfill_option_zerodha_OI_FIXED.py" ubuntu@13.51.242.119:~/meridian-alpha/

# Edit BACKFILL_DATES in the script
nano backfill_option_zerodha_OI_FIXED.py

# Test with dry run (subset)
python3 backfill_option_zerodha_OI_FIXED.py --dry-run | head -50

# Run full backfill
python3 backfill_option_zerodha_OI_FIXED.py
```

**Key script parameters:**
- `STRIKE_RANGE = 5` (ATM ±5 strikes)
- `MIN_DTE = 0, MAX_DTE = 7` (current week expiries only)
- `OPTION_INSTRUMENT_IDS`: Maps NIFTY/SENSEX to underlying spot instrument_id
- `oi: 0` (default for backfilled data without OI information)

**Verification query:**
```sql
SELECT 
    COUNT(*) as total_option_bars,
    COUNT(DISTINCT strike) as strikes,
    COUNT(DISTINCT option_type) as option_types,
    COUNT(DISTINCT CASE WHEN option_type = 'CE' THEN strike END) as ce_strikes,
    COUNT(DISTINCT CASE WHEN option_type = 'PE' THEN strike END) as pe_strikes
FROM hist_option_bars_1m 
WHERE trade_date = '2026-05-04';  -- Replace with target date
```

**Expected result:** ~2,000+ bars, ~22 strikes, 2 option types (CE/PE), balanced CE/PE distribution

### Phase 3: Data Quality Verification

**Pattern detection verification:**
```sql
-- Should show both FVG and OB patterns after proper data recovery
SELECT 
    pattern_type,
    COUNT(*) as count
FROM ict_patterns 
WHERE trade_date = '2026-05-04'  -- Replace with target date
GROUP BY pattern_type;
```

**Market hours verification:**
```sql
-- Verify all data is within market hours
SELECT 
    'spot_bars' as data_type,
    MIN(bar_ts AT TIME ZONE 'Asia/Kolkata') as first_ts,
    MAX(bar_ts AT TIME ZONE 'Asia/Kolkata') as last_ts,
    COUNT(*) as total_records
FROM hist_spot_bars_1m WHERE trade_date = '2026-05-04'
UNION ALL
SELECT 
    'option_bars' as data_type,
    MIN(bar_ts AT TIME ZONE 'Asia/Kolkata') as first_ts,
    MAX(bar_ts AT TIME ZONE 'Asia/Kolkata') as last_ts,
    COUNT(*) as total_records
FROM hist_option_bars_1m WHERE trade_date = '2026-05-04';
```

**Expected:** All timestamps between 09:15:00 and 15:29:00 IST

---

## Common Issues and Solutions

### Issue 1: Schema Errors During Options Backfill

**Symptoms:**
- `"Could not find column 'exchange'"` 
- `"null value in column 'oi' violates not-null constraint"`
- `"no unique constraint matching ON CONFLICT specification"`

**Solution:**
Use the schema-corrected script (`backfill_option_zerodha_OI_FIXED.py`) which:
- Removes non-existent `exchange`, `trading_symbol` columns
- Sets `oi: 0` instead of `null`
- Uses correct `instrument_id` mapping
- Removes problematic `ON CONFLICT` clauses

### Issue 2: Kite API Rate Limiting

**Symptoms:**
- "Rate limit exceeded" errors
- Timeouts during large backfills

**Solution:**
```python
# Add delays between requests in backfill script
time.sleep(0.2)  # 200ms between instruments

# Or run in smaller batches
# Edit BACKFILL_DATES to include only 1-2 dates per run
```

### Issue 3: Missing Option Instruments

**Symptoms:**
- "Found 0 option instruments"
- Script completes but writes 0 rows

**Solution:**
```bash
# Debug instrument discovery
python3 -c "
from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv
load_dotenv()
kite = KiteConnect(api_key=os.environ['KITE_API_KEY'])
kite.set_access_token(os.environ['KITE_ACCESS_TOKEN'])
instruments = kite.instruments('NFO')
nifty_options = [i for i in instruments if i['name'] == 'NIFTY' and i['instrument_type'] in ['CE', 'PE']]
print(f'Found {len(nifty_options)} NIFTY options')
"
```

Check:
- Expiry dates are within DTE range
- Strike prices are reasonable for current spot
- Market is open (no weekend/holiday backfill)

### Issue 4: AWS Security Group IP Changes

**Symptoms:**
- SSH connection refused
- "Connection timed out"

**Solution:**
```bash
# Update AWS security group for new public IP
# Check current IP: curl ifconfig.me
# Update sg-0123456789abcdef0 to allow new IP on port 22
aws ec2 authorize-security-group-ingress --group-id sg-0123456789abcdef0 --protocol tcp --port 22 --cidr YOUR_NEW_IP/32
```

---

## Automation Integration

This runbook integrates with `merdian_daily_audit.py` (see companion file):

**Automated triggers:**
- `merdian_daily_audit.py` runs at 16:00 IST daily
- Detects data gaps using diagnostic queries from this runbook
- Sends alerts if gaps detected
- Can trigger automated backfill for recent dates

**Manual override:**
```bash
# Force audit for specific date
python3 merdian_daily_audit.py --date 2026-05-04 --auto-backfill

# Audit only (no automatic backfill)
python3 merdian_daily_audit.py --date 2026-05-04 --alert-only
```

---

## Success Verification Checklist

**Before closing recovery session:**

```
☐ Spot data: >700 bars per symbol, 0 flat bars, proper market hours
☐ Option data: >1,500 option bars, balanced CE/PE, proper strikes
☐ Pattern detection: Both FVG and OB patterns detected (if market conditions support)
☐ Market state: >200 snapshots, proper time range
☐ Option chain: >50,000 snapshots (should be preserved during outage)
☐ Signal snapshots: >200 signals, proper time range
☐ No schema errors or constraint violations in logs
☐ All backfill scripts committed to Git with updated BACKFILL_DATES
☐ Documentation updated: this session noted in session_log.md
☐ merdian_reference.json updated with any file status changes
```

**Final verification query:**
```sql
-- Complete data health check for recovered date
WITH data_summary AS (
  SELECT 
    '2026-05-04' as trade_date,
    (SELECT COUNT(*) FROM hist_spot_bars_1m WHERE trade_date = '2026-05-04') as spot_bars,
    (SELECT COUNT(*) FROM hist_option_bars_1m WHERE trade_date = '2026-05-04') as option_bars,
    (SELECT COUNT(*) FROM option_chain_snapshots WHERE DATE(created_at AT TIME ZONE 'Asia/Kolkata') = '2026-05-04') as option_snapshots,
    (SELECT COUNT(*) FROM market_state_snapshots WHERE DATE(created_at AT TIME ZONE 'Asia/Kolkata') = '2026-05-04') as market_snapshots,
    (SELECT COUNT(*) FROM signal_snapshots WHERE DATE(created_at AT TIME ZONE 'Asia/Kolkata') = '2026-05-04') as signal_snapshots,
    (SELECT COUNT(*) FROM ict_patterns WHERE trade_date = '2026-05-04') as patterns
)
SELECT 
  *,
  CASE 
    WHEN spot_bars >= 700 AND option_bars >= 1500 AND option_snapshots >= 50000 
         AND market_snapshots >= 200 AND signal_snapshots >= 200 AND patterns >= 10
    THEN 'PASS' 
    ELSE 'FAIL' 
  END as recovery_status
FROM data_summary;
```

---

## File References

**Created/Modified during recovery:**
- `backfill_spot_zerodha.py` (AWS) — BACKFILL_DATES updated
- `backfill_option_zerodha_OI_FIXED.py` (AWS) — new schema-corrected version
- `session_log.md` — recovery session documented
- `merdian_reference.json` — file status updated

**Dependencies:**
- `.env` files (Local + AWS) — Kite/Supabase credentials
- AWS security group configuration — SSH access
- Supabase database schema — target tables
- Git repository — version control for scripts

---

*Data Backfill Runbook v1 — 2026-05-04 — Tested on internet outage recovery session*