from __future__ import annotations
import os
import time
import boto3
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

INSTANCE_ID = "i-XXXXXXXXXXXXXXXXX"   # <-- paste your EC2 instance ID here
AWS_REGION   = "ap-south-1"           # <-- confirm your region
AWS_ENV_PATH = "/home/ssm-user/meridian-engine/.env"

def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    token = os.getenv("DHAN_API_TOKEN", "").strip()
    if not token:
        print("ERROR: DHAN_API_TOKEN not found in local .env")
        return 1

    ssm = boto3.client("ssm", region_name=AWS_REGION)

    # sed replaces only the token line, leaves everything else intact
    command = f"sed -i 's|^DHAN_API_TOKEN=.*|DHAN_API_TOKEN={token}|' {AWS_ENV_PATH}"

    resp = ssm.send_command(
        InstanceIds=[INSTANCE_ID],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [command]},
        TimeoutSeconds=30,
    )
    command_id = resp["Command"]["CommandId"]

    # Poll for result
    for _ in range(10):
        time.sleep(2)
        result = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=INSTANCE_ID,
        )
        status = result["Status"]
        if status == "Success":
            print(f"Token synced to AWS successfully.")
            return 0
        elif status in ("Failed", "Cancelled", "TimedOut"):
            print(f"ERROR syncing token to AWS: {status} — {result.get('StandardErrorContent', '')}")
            return 1

    print("ERROR: SSM command did not complete within timeout.")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
