#!/usr/bin/env python3
"""
Breeze API authentication manager.

Handles checksum computation, session token management, and authenticated requests.
Per Breeze API spec: https://api.icicidirect.com/breezeapi/documents/index.html

Checksum = SHA256(ISO8601_Timestamp + JSONPostData + secret_key)
"""

import os
import json
import hashlib
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class BreezeAuthManager:
    def __init__(self):
        self.breeze_api_key = os.getenv("BREEZE_API_KEY")
        self.breeze_secret = os.getenv("BREEZE_API_SECRET")
        self.base_url = "https://api.icicidirect.com/breezeapi/api/v1"
        self.session_token = None
        self.app_key = None
        
        if not self.breeze_api_key or not self.breeze_secret:
            raise ValueError("BREEZE_API_KEY and BREEZE_API_SECRET required in .env")
    
    def _get_iso_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format with .000Z."""
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    
    def _compute_checksum(self, timestamp: str, payload_json: str) -> str:
        """
        Compute SHA256 checksum per Breeze spec.
        Checksum = SHA256(timestamp + payload_json + secret_key)
        """
        message = timestamp + payload_json + self.breeze_secret
        return hashlib.sha256(message.encode('utf-8')).hexdigest()
    
    def _get_headers(self, timestamp: str, checksum: str) -> Dict[str, str]:
        """Construct authenticated request headers."""
        return {
            'Content-Type': 'application/json',
            'X-Checksum': f'token {checksum}',
            'X-Timestamp': timestamp,
            'X-AppKey': self.breeze_api_key,
            'X-SessionToken': self.session_token or ''
        }
    
    def authenticate(self) -> bool:
        """
        Initial authentication to get session token.
        This step requires BREEZE_SESSION_TOKEN from .env (obtained via web login).
        """
        breeze_session_token = os.getenv("BREEZE_SESSION_TOKEN")
        if not breeze_session_token:
            raise ValueError("BREEZE_SESSION_TOKEN required in .env (from web login)")
        
        url = f"{self.base_url}/customerdetails"
        payload = json.dumps({
            "SessionToken": breeze_session_token,
            "AppKey": self.breeze_api_key
        })
        
        # CustomerDetails doesn't require checksum (per spec)
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            resp = requests.get(url, headers=headers, data=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("Status") == 200 and "Success" in data:
                self.session_token = data["Success"].get("session_token")
                print(f"[OK] Breeze authenticated. Session token: {self.session_token[:20]}...")
                return True
            else:
                print(f"[ERROR] Breeze auth failed: {data.get('Error')}")
                return False
        
        except Exception as e:
            print(f"[ERROR] Breeze auth request failed: {e}")
            return False
    
    def get_historical_data(self, 
                           stock_code: str,
                           exchange_code: str,
                           from_date: str,
                           to_date: str,
                           interval: str = "day",
                           product_type: str = "futures",
                           expiry_date: Optional[str] = None,
                           right: str = "others",
                           strike_price: str = "0") -> list:
        """
        Fetch historical OHLC data via Breeze API.
        
        Args:
            stock_code: "NIFTY", "BSESEN" (for SENSEX)
            exchange_code: "NFO" for futures/options
            from_date: "2026-03-01" (YYYY-MM-DD)
            to_date: "2026-06-07" (YYYY-MM-DD)
            interval: "day" (only daily supported for backfill)
            product_type: "futures" or "options"
            expiry_date: ISO 8601 (required for options/futures)
            right: "others" (futures), "call"/"put" (options)
            strike_price: "0" (futures), numeric (options)
        
        Returns:
            List of OHLC bars
        """
        
        # Convert dates to ISO 8601 format (Breeze spec)
        from_dt = f"{from_date}T00:00:00.000Z"
        to_dt = f"{to_date}T23:59:59.000Z"
        
        # Expiry date required for futures/options
        if not expiry_date:
            # For backfill, use the to_date as expiry (next monthly expiry)
            # This is a simplification; ideally we'd compute the actual expiry
            expiry_date = to_dt
        
        url = f"{self.base_url}/historicalcharts"
        
        payload = json.dumps({
            "stock_code": stock_code,
            "exchange_code": exchange_code,
            "product_type": product_type,
            "interval": interval,
            "from_date": from_dt,
            "to_date": to_dt,
            "expiry_date": expiry_date,
            "right": right,
            "strike_price": strike_price
        }, separators=(',', ':'))
        
        timestamp = self._get_iso_timestamp()
        checksum = self._compute_checksum(timestamp, payload)
        headers = self._get_headers(timestamp, checksum)
        
        try:
            print(f"[INFO] Fetching {stock_code} {product_type} {from_date} to {to_date}...")
            print(f"[DEBUG] Payload: {payload}")
            print(f"[DEBUG] URL: {url}")
            print(f"[DEBUG] Checksum: {checksum[:20]}...")
            resp = requests.get(url, headers=headers, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            print(f"[DEBUG] Response status: {data.get('Status')}, Error: {data.get('Error')}")
            
            if data.get("Status") == 200:
                bars = data.get("Success", [])
                print(f"[OK] {stock_code}: {len(bars)} bars")
                return bars
            else:
                print(f"[WARN] Breeze returned status {data.get('Status')}: {data.get('Error')}")
                return []
        
        except Exception as e:
            print(f"[ERROR] Breeze fetch failed: {e}")
            return []
    
    def get_quotes(self,
                   stock_code: str,
                   exchange_code: str,
                   product_type: str,
                   expiry_date: str,
                   right: str,
                   strike_price: str) -> Optional[Dict[str, Any]]:
        """Fetch latest quote for a security."""
        
        url = f"{self.base_url}/quotes"
        
        payload = json.dumps({
            "stock_code": stock_code,
            "exchange_code": exchange_code,
            "product_type": product_type,
            "expiry_date": expiry_date,
            "right": right,
            "strike_price": strike_price
        }, separators=(',', ':'))
        
        timestamp = self._get_iso_timestamp()
        checksum = self._compute_checksum(timestamp, payload)
        headers = self._get_headers(timestamp, checksum)
        
        try:
            resp = requests.get(url, headers=headers, data=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("Status") == 200:
                quotes = data.get("Success", [])
                return quotes[0] if quotes else None
            else:
                print(f"[WARN] Quote fetch failed: {data.get('Error')}")
                return None
        
        except Exception as e:
            print(f"[ERROR] Quote fetch error: {e}")
            return None


if __name__ == '__main__':
    # Test authentication
    try:
        breeze = BreezeAuthManager()
        if breeze.authenticate():
            print("[SUCCESS] Breeze auth manager ready")
        else:
            print("[ERROR] Breeze authentication failed")
    except Exception as e:
        print(f"[ERROR] {e}")
