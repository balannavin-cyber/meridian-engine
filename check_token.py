import os

with open('.env') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if 'DHAN_API_TOKEN' in line:
            val = line.split('=', 1)[1].strip().strip('"').strip("'")
            print(f'Token length: {len(val)}')
            print(f'Token first 20: {val[:20]}...')
            print(f'Token last 10: ...{val[-10:]}')
            print(f'Has spaces: {" " in val}')
            print(f'Has newline: {chr(10) in val}')
        if line.startswith('DHAN_CLIENT_ID'):
            val = line.split('=', 1)[1].strip().strip('"').strip("'")
            print(f'Client ID: {val}')
