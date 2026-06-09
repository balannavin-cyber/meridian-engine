# **RUNBOOK: AWS CLI Login & File Operations on MERDIAN AWS**

**Purpose:** Access MERDIAN AWS instance (i-0878c118835386ec2) via AWS CLI + Systems Manager Session Manager; transfer files to/from EC2 using S3 intermediary or direct SCP

**Scope:** Local Windows → AWS S3 bucket → EC2 instance file operations

**Prerequisites:** 
- AWS CLI v2 installed on Local Windows
- AWS credentials configured (NavinBal user AKIASI4GEQXTVHBZFW4K)
- SSM Session Manager plugin installed
- S3 bucket `meridian-engine-deploy` exists in eu-north-1
- EC2 instance i-0878c118835386ec2 running with IAM role `meridian-ssm-ec2-role-v2` (has S3 access)

---

## **PART A: VERIFY AWS CLI SETUP (One-Time)**

### **Step A.1 — Verify AWS CLI Installation**

```powershell
aws --version
# Expected: aws-cli/2.34.63 (or higher)

aws sts get-caller-identity
# Expected output shows NavinBal user
```

**If AWS CLI not installed:**
- Download from https://awscli.amazonaws.com/AWSCLIV2.msi
- Install with defaults
- Restart PowerShell

### **Step A.2 — Verify AWS Credentials**

```powershell
# Check credentials file location
$env:USERPROFILE\.aws\credentials

# Verify profile
cat $env:USERPROFILE\.aws\credentials
# Should show [default] with aws_access_key_id and aws_secret_access_key
```

**If credentials missing:**
```powershell
# Configure interactively
aws configure
# Paste:
# AWS Access Key ID: AKIASI4GEQXTVHBZFW4K
# AWS Secret Access Key: [from secure store]
# Default region: eu-north-1
# Default output format: json
```

### **Step A.3 — Verify SSM Session Manager Plugin**

```powershell
# Check if installed
aws ssm start-session --target i-0878c118835386ec2 --document-name "AWS-StartInteractiveCommand"

# If plugin missing, install:
# Download: https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe
# Install with defaults
# Restart PowerShell
```

---

## **PART B: LOGIN TO AWS EC2 VIA SSM SESSION MANAGER**

### **Step B.1 — Start SSM Session**

```powershell
# Connect to MERDIAN AWS instance
aws ssm start-session --target i-0878c118835386ec2

# Expected: prompt shows
# [ssm-user@ip-172-31-35-90 ~]$
```

**If connection fails:**
```powershell
# Verify instance status
aws ec2 describe-instances --instance-ids i-0878c118835386ec2 --region eu-north-1 --query 'Reservations[0].Instances[0].State.Name'
# Should return: running

# Verify IAM role has SSM permissions
aws iam get-role --role-name meridian-ssm-ec2-role-v2
```

### **Step B.2 — Verify AWS CLI on EC2**

Once logged in via SSM:

```bash
aws --version
# Expected: aws-cli/1.22.34 (AWS Python 3.10 version, older than Local)

aws s3 ls s3://meridian-engine-deploy/
# Should list: core/ scripts/
```

### **Step B.3 — Verify S3 Access from EC2**

```bash
# List S3 bucket contents
aws s3 ls s3://meridian-engine-deploy/ --recursive | head -20

# Verify EC2 has S3 permissions (via IAM role, not credentials)
# If access denied, check role: meridian-ssm-ec2-role-v2 must have AmazonS3FullAccess
```

### **Step B.4 — Exit SSM Session**

```bash
exit
# Returns to Local PowerShell prompt
```

---

## **PART C: UPLOAD FILES — LOCAL → S3**

### **Step C.1 — Upload Single File to S3**

**From Local Windows PowerShell:**

```powershell
# Upload a Python script to S3
aws s3 cp C:\GammaEnginePython\run_merdian_shadow_runner_aws.py `
  s3://meridian-engine-deploy/scripts/run_merdian_shadow_runner_aws.py `
  --region eu-north-1

# Expected: upload progress + "upload: ... to s3://..."
```

### **Step C.2 — Bulk Upload Directory to S3**

```powershell
# Upload entire core/ directory
aws s3 cp C:\GammaEnginePython\core\ `
  s3://meridian-engine-deploy/core/ `
  --recursive `
  --exclude "__pycache__/*" `
  --region eu-north-1

# Expected: uploads all .py files with progress
```

### **Step C.3 — Verify Upload**

```powershell
# List what was uploaded
aws s3 ls s3://meridian-engine-deploy/scripts/ --recursive

aws s3 ls s3://meridian-engine-deploy/core/ --recursive
```

---

## **PART D: DOWNLOAD FILES — S3 → EC2**

### **Step D.1 — Start SSM Session Again**

```powershell
aws ssm start-session --target i-0878c118835386ec2
```

### **Step D.2 — Pull Files from S3 to EC2**

Once in SSM session on EC2:

```bash
# Download single file from S3
aws s3 cp s3://meridian-engine-deploy/scripts/run_merdian_shadow_runner_aws.py \
  /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py \
  --region eu-north-1

# Verify download
ls -lh /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py
```

### **Step D.3 — Bulk Download Core Directory**

```bash
# Download all core modules
aws s3 cp s3://meridian-engine-deploy/core/ \
  /home/ssm-user/meridian-engine/core/ \
  --recursive \
  --region eu-north-1

# Verify
ls -lh /home/ssm-user/meridian-engine/core/ | head -10
```

### **Step D.4 — Set Executable Permissions**

```bash
# Make scripts executable
chmod +x /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py
chmod +x /home/ssm-user/meridian-engine/*.py

# Verify
ls -la /home/ssm-user/meridian-engine/ | grep "^-rwx"
```

---

## **PART E: DIRECT FILE OPERATIONS ON EC2 (WITHIN SSM SESSION)**

### **Step E.1 — View File Contents**

```bash
# SSH into EC2 via SSM (already in session)
# View script
cat /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py | head -30

# Check log
tail -f /home/ssm-user/meridian-engine/shadow_runner.log
```

### **Step E.2 — Create/Edit Files**

**Option A: Nano editor (simple)**
```bash
nano /home/ssm-user/meridian-engine/config.env
# Edit, Ctrl+X, Y, Enter to save
```

**Option B: Heredoc paste (for larger files)**
```bash
cat > /home/ssm-user/meridian-engine/test_file.py << 'EOF'
#!/usr/bin/env python3
# Paste your Python code here
print("Hello from AWS")
EOF

chmod +x /home/ssm-user/meridian-engine/test_file.py
```

### **Step E.3 — Copy Files on EC2**

```bash
# Copy within EC2
cp /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py \
   /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws_BACKUP.py

# Move/rename
mv /home/ssm-user/meridian-engine/old_name.py \
   /home/ssm-user/meridian-engine/new_name.py

# List directory
ls -lh /home/ssm-user/meridian-engine/
```

---

## **PART F: DOWNLOAD FILES — EC2 → S3 → LOCAL**

### **Step F.1 — Upload Files from EC2 to S3 (within SSM session)**

```bash
# Copy file from EC2 to S3
aws s3 cp /home/ssm-user/meridian-engine/shadow_runner.log \
  s3://meridian-engine-deploy/logs/shadow_runner.log \
  --region eu-north-1

# Copy entire logs directory
aws s3 cp /home/ssm-user/meridian-engine/logs/ \
  s3://meridian-engine-deploy/logs/ \
  --recursive \
  --region eu-north-1
```

### **Step F.2 — Exit SSM Session**

```bash
exit
# Back to Local PowerShell
```

### **Step F.3 — Download from S3 to Local Windows**

```powershell
# Download file from S3 to Local
aws s3 cp s3://meridian-engine-deploy/logs/shadow_runner.log `
  C:\GammaEnginePython\logs\shadow_runner.log `
  --region eu-north-1

# Bulk download
aws s3 cp s3://meridian-engine-deploy/logs/ `
  C:\GammaEnginePython\logs\ `
  --recursive `
  --region eu-north-1
```

---

## **PART G: TROUBLESHOOTING**

### **Problem: "Unable to locate credentials"**

```powershell
# Verify credentials configured
aws sts get-caller-identity
# If fails, run: aws configure

# Verify environment variables not interfering
$env:AWS_ACCESS_KEY_ID  # Should be empty or match configured
$env:AWS_SECRET_ACCESS_KEY  # Should be empty or match configured
```

### **Problem: "Session target not found"**

```powershell
# Verify instance is running
aws ec2 describe-instances --instance-ids i-0878c118835386ec2 --region eu-north-1

# Verify SSM plugin installed
aws ssm start-session --target i-0878c118835386ec2 --document-name "AWS-StartInteractiveCommand"
```

### **Problem: "An error occurred (AccessDenied) when calling S3 operation"**

On EC2 (within SSM):
```bash
# Verify IAM role has S3 permissions
aws sts get-caller-identity
# Should show EC2 role, not user credentials

# If still denied, check role:
# meridian-ssm-ec2-role-v2 must have AmazonS3FullAccess policy attached
```

### **Problem: "Command timed out"**

```powershell
# SSM sessions have 20-minute idle timeout
# For long operations, use nohup or screen:

# Within SSM session:
screen
# Run long command
nohup python3 /home/ssm-user/meridian-engine/long_script.py &
# Detach: Ctrl+A, D
# Reattach later: screen -r

exit  # Exit screen
exit  # Exit SSM session
```

---

## **PART H: CANONICAL WORKFLOW — UPDATE ORCHESTRATOR SCRIPT**

**Scenario:** Update `run_merdian_shadow_runner_aws.py` on AWS EC2

### **Step H.1 — Edit locally (Local Windows)**

```powershell
# Edit the script
code C:\GammaEnginePython\run_merdian_shadow_runner_aws.py
```

### **Step H.2 — Upload to S3**

```powershell
aws s3 cp C:\GammaEnginePython\run_merdian_shadow_runner_aws.py `
  s3://meridian-engine-deploy/scripts/run_merdian_shadow_runner_aws.py `
  --region eu-north-1
```

### **Step H.3 — Validate via git (preferred)**

```powershell
# Commit to git first
cd C:\GammaEnginePython
git add run_merdian_shadow_runner_aws.py
git commit -m "S47: Update orchestrator script"
git push origin main

# Then on AWS, pull from git (recommended deployment method)
# Don't use S3 for production code — use git pull per ADR-006
```

### **Step H.4 — If using S3, download to EC2**

```powershell
aws ssm start-session --target i-0878c118835386ec2
```

```bash
# On EC2, pull from S3
aws s3 cp s3://meridian-engine-deploy/scripts/run_merdian_shadow_runner_aws.py \
  /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py \
  --region eu-north-1

# Verify
python3 -m py_compile /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py
# If no output = syntax OK

# Set executable
chmod +x /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py

# Test
/home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py --help
```

### **Step H.5 — Verify on EC2**

```bash
# Check crontab still running
crontab -l | grep run_merdian

# Check execution log
tail -20 /home/ssm-user/meridian-engine/shadow_runner.log
```

---

## **PART I: QUICK REFERENCE — COMMON COMMANDS**

### **Local Windows PowerShell**

```powershell
# Login / verify credentials
aws sts get-caller-identity

# Start SSM session
aws ssm start-session --target i-0878c118835386ec2

# Upload to S3
aws s3 cp <local-file> s3://meridian-engine-deploy/<path>/

# Upload directory
aws s3 cp <local-dir> s3://meridian-engine-deploy/<path>/ --recursive

# Download from S3
aws s3 cp s3://meridian-engine-deploy/<path>/<file> <local-file>

# List S3 bucket
aws s3 ls s3://meridian-engine-deploy/ --recursive
```

### **On EC2 (within SSM session)**

```bash
# Check AWS CLI
aws --version

# List S3 bucket
aws s3 ls s3://meridian-engine-deploy/ --recursive

# Download from S3
aws s3 cp s3://meridian-engine-deploy/<path>/<file> /home/ssm-user/meridian-engine/

# Pull from git (preferred)
cd /home/ssm-user/meridian-engine
git pull origin main

# Check crontab
crontab -l

# View logs
tail -f /home/ssm-user/meridian-engine/shadow_runner.log

# Exit SSM
exit
```

---

## **PART J: DEPLOYMENT VECTOR DECISION TREE**

**Which method to use?**

```
Is this production code?
  ├─ YES → Use git pull (canonical per ADR-006)
  │   └─ git commit locally → git push → aws ssm → git pull
  │
  └─ NO (experimental/backfill/diagnostic)
      ├─ Single file? → Use S3 intermediary
      │   └─ aws s3 cp local → aws s3 cp s3→ec2
      │
      └─ Multiple files? → Use git branch or tar+heredoc
          └─ tar czf archive.tar.gz <files> → heredoc paste to EC2 → tar xzf
```

**For S47 Breeze backfill scripts:**
- Experimental/diagnostic → use S3 intermediary (not git)
- Once validated → commit to git + use git pull

---

## **CHANGELOG**

| Session | Date | Change |
|---|---|---|
| S47 | 2026-06-07 | Initial runbook created |

---

**Ready for S47 file operations.**
