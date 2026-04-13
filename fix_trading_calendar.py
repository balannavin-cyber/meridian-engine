import json
from pathlib import Path

f = Path('C:/GammaEnginePython/trading_calendar.json')
data = json.loads(f.read_text())
sessions = data.get('sessions', [])
dates = {s['date'] for s in sessions}

if '2026-04-06' not in dates:
    sessions.append({
        'date': '2026-04-06',
        'is_open': False,
        'monitor_start_time': '09:00',
        'premarket_ref_time': '09:08',
        'open_time': '09:15',
        'close_time': '15:30',
        'postmarket_ref_time': '16:00',
        'final_eod_ltp_time': '16:15',
        'special_session': False,
        'notes': 'Sunday - market closed'
    })

if '2026-04-07' not in dates:
    sessions.append({
        'date': '2026-04-07',
        'is_open': True,
        'monitor_start_time': '09:00',
        'premarket_ref_time': '09:08',
        'open_time': '09:15',
        'close_time': '15:30',
        'postmarket_ref_time': '16:00',
        'final_eod_ltp_time': '16:15',
        'special_session': False,
        'notes': 'Normal trading day - NIFTY weekly expiry Tuesday'
    })

sessions.sort(key=lambda x: x['date'])
data['sessions'] = sessions
f.write_text(json.dumps(data, indent=2))
print('Done')
