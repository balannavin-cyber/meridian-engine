import os
from dotenv import load_dotenv
load_dotenv()

print("=== Dhan token state ===")
tok = os.environ.get("DHAN_ACCESS_TOKEN", "")
cid = os.environ.get("DHAN_CLIENT_ID", "")
print(f"DHAN_CLIENT_ID:    {cid[:8]}...{cid[-4:] if len(cid)>8 else cid}")
print(f"DHAN_ACCESS_TOKEN length: {len(tok)}")
print(f"DHAN_ACCESS_TOKEN first 10: {tok[:10]}")
print(f"DHAN_ACCESS_TOKEN last 8: ...{tok[-8:]}")
print()

# Try an auth call
print("=== Dhan API test ===")
try:
    from dhanhq import dhanhq
    dhan = dhanhq(cid, tok)
    r = dhan.get_fund_limits()
    if r.get("status") == "success":
        print(f"AUTH OK — Dhan API responding. availableBalance: {r.get('data', {}).get('availabelBalance', '?')}")
    else:
        print(f"AUTH FAILED — Dhan response: {r}")
except Exception as e:
    print(f"AUTH FAILED — {type(e).__name__}: {e}")
