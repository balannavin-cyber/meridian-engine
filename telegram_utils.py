#!/usr/bin/env python3
"""Telegram utility module for MERDIAN alerts."""

import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# Load .env
from dotenv import load_dotenv
load_dotenv('/home/ssm-user/meridian-engine/.env')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

LEVELS = {
    'INFO': '✅',
    'WARNING': '⚠️',
    'CRITICAL': '🚨',
    'ERROR': '❌',
}

def send_alert(message: str, level: str = 'INFO', context: Optional[Dict[str, Any]] = None, script_name: Optional[str] = None) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Telegram credentials not configured")
        return False
    
    emoji = LEVELS.get(level, '•')
    ts = datetime.utcnow().strftime('%H:%M:%S UTC')
    
    lines = [
        f"{emoji} {level} @ {ts}",
        message,
    ]
    
    if script_name:
        lines.append(f"Script: {script_name}")
    
    if context:
        lines.append("\nContext:")
        for key, value in context.items():
            lines.append(f"  {key}: {value}")
    
    text = '\n'.join(lines)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'plain'
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"[WARN] Telegram send failed: {e}")
        return False

def send_critical(message: str, context: Optional[Dict[str, Any]] = None) -> bool:
    return send_alert(message, level='CRITICAL', context=context)

def send_warning(message: str, context: Optional[Dict[str, Any]] = None) -> bool:
    return send_alert(message, level='WARNING', context=context)

if __name__ == '__main__':
    send_alert("Test message from MERDIAN", level='INFO')
    print("Telegram test sent")
