"""
merdian_live_dashboard.py — MERDIAN Operational Dashboard v2

Serves at http://localhost:8765
Auto-refreshes every 30 seconds.
Action buttons run foreground, result shown inline within 5 seconds.

Sections:
- Session state: computed live from calendar + clock. Never stale.
- Token: last refresh time, expiry countdown.
- Pre-open block (09:00-09:08): spot captured Y/N, value.
- Pipeline stages: last run time + actual value per stage per symbol.
- Breadth: advances, declines, regime, last capture time.
- AWS shadow: last cycle time, result, per-symbol status — via Supabase.
- Heartbeats: supervisor, runner, telemetry, alert daemon.
- Actions: each shows last execution time + output inline. No click and pray.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests as req
from dotenv import load_dotenv

# Force UTF-8 safe output on Windows cp1252 systems
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
TOKEN_STATUS_FILE = BASE_DIR / "runtime" / "token_status.json"
HEARTBEAT_DIR = BASE_DIR / "runtime" / "heartbeats"

IST = timezone(timedelta(hours=5, minutes=30))

load_dotenv(dotenv_path=ENV_PATH)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

_action_results: Dict[str, Dict] = {}
_action_lock = threading.Lock()

ACTIONS = {
    "refresh_token": {
        "label": "Refresh Dhan Token",
        "cmd": [sys.executable, str(BASE_DIR / "refresh_dhan_token.py")],
        "confirm": "Refresh Dhan API token now?",
        "timeout": 90,
        "aws": False,
    },
    "run_preflight": {
        "label": "Run Preflight",
        "cmd": [sys.executable, str(BASE_DIR / "run_preflight.py"), "--mode", "full"],
        "confirm": "Run full preflight check?",
        "timeout": 120,
        "aws": False,
    },
    "start_supervisor": {
        "label": "Start Supervisor",
        "cmd": ["powershell", "-Command", "Start-ScheduledTask -TaskName MERDIAN_Intraday_Supervisor_Start"],
        "confirm": "Start the intraday supervisor?",
        "timeout": 30,
        "aws": False,
    },
    "start_runner": {
        "label": "Start Runner (manual)",
        "cmd": [sys.executable, str(BASE_DIR / "run_option_snapshot_intraday_runner.py")],
        "confirm": "Start runner manually? Only use if supervisor failed.",
        "timeout": 30,
        "aws": False,
    },
}


def now_ist() -> datetime:
    return datetime.now(IST)


def read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sb_get(table: str, params: str) -> List[Dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        r = req.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=headers, timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def fmt_lag(lag) -> str:
    if lag is None:
        return "?"
    s = int(lag)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s//60}m {s%60}s"
    return f"{s//3600}h {(s%3600)//60}m"


def parse_ist_dt(ts_str: str) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        s = str(ts_str).strip()
        # Handle microseconds truncation — take first 26 chars max
        # but preserve timezone info which comes after
        if "+" in s[10:]:
            # Has timezone — split on + to preserve it
            parts = s[10:].split("+", 1)
            s = s[:10] + parts[0][:16] + "+" + parts[1]
        elif "Z" in s:
            s = s.replace("Z", "+00:00")
            s = s[:26]
        else:
            s = s[:26] + "+00:00"
        s = s.replace(" ", "T")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST)
    except Exception:
        try:
            # Fallback: try parsing just the date+time part
            s = str(ts_str).strip()[:19].replace(" ", "T")
            dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
            return dt.astimezone(IST)
        except Exception:
            return None


def lag_sec(ts_str: str) -> Optional[int]:
    dt = parse_ist_dt(ts_str)
    if dt is None:
        return None
    return int((now_ist() - dt).total_seconds())


def fmt_expiry_countdown(expiry_iso: str) -> tuple[str, str]:
    """Returns (display_string, color)"""
    if not expiry_iso:
        return "unknown", "#888"
    try:
        exp = datetime.fromisoformat(expiry_iso.replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        rem = (exp - datetime.now(timezone.utc)).total_seconds()
        if rem <= 0:
            return "EXPIRED", "#8b0000"
        h, m = int(rem // 3600), int((rem % 3600) // 60)
        color = "#1a7a1a" if h > 4 else "#b45000" if h > 0 else "#8b0000"
        return f"{h}h {m}m remaining", color
    except Exception:
        return "?", "#888"


def badge(ok: Optional[bool], ok_txt="OK", fail_txt="FAIL", none_txt="?") -> str:
    if ok is True:
        return f'<span style="color:#1a7a1a;background:#e8f5e9;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:600">{ok_txt}</span>'
    if ok is False:
        return f'<span style="color:#8b0000;background:#ffebee;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:600">{fail_txt}</span>'
    return f'<span style="color:#555;background:#f5f5f5;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:600">{none_txt}</span>'


def staleness_badge(lag) -> str:
    if lag is None:
        return badge(None, none_txt="NO DATA")
    if lag < 600:
        return f'<span style="color:#1a7a1a;background:#e8f5e9;padding:2px 8px;border-radius:4px;font-size:11px">LIVE · {fmt_lag(lag)} ago</span>'
    return f'<span style="color:#b45000;background:#fff3e0;padding:2px 8px;border-radius:4px;font-size:11px">STALE · {fmt_lag(lag)} ago</span>'


def get_session_info() -> Dict:
    try:
        from trading_calendar import get_today_session_config, current_session_state
        current = now_ist()
        cfg = get_today_session_config(current)
        state = current_session_state(current)
        next_event, next_in = "", ""
        if cfg.is_open:
            for label, dt in [
                ("Pre-open starts", cfg.monitor_start_dt),
                ("Pre-open ref 09:08", cfg.premarket_ref_dt),
                ("Market open 09:15", cfg.open_dt),
                ("Market close 15:30", cfg.close_dt),
                ("Post-market ref 16:00", cfg.postmarket_ref_dt),
            ]:
                if dt > current:
                    next_event = label
                    next_in = fmt_lag((dt - current).total_seconds())
                    break
        return {
            "is_open": cfg.is_open,
            "state": state,
            "date": cfg.date,
            "notes": cfg.notes,
            "open_time": cfg.open_time.strftime("%H:%M"),
            "close_time": cfg.close_time.strftime("%H:%M"),
            "next_event": next_event,
            "next_in": next_in,
        }
    except Exception as e:
        return {
            "is_open": False, "state": "ERROR",
            "date": now_ist().strftime("%Y-%m-%d"),
            "notes": str(e), "open_time": "09:15", "close_time": "15:30",
            "next_event": "", "next_in": "",
        }


def get_token_status() -> Dict:
    data = read_json(TOKEN_STATUS_FILE)
    if not data:
        return {"success": None, "refreshed_at": "never", "expiry": "", "error": ""}
    return {
        "success": data.get("success"),
        "refreshed_at": data.get("refreshed_at_ist", "?"),
        "expiry": data.get("expiry_time", ""),
        "error": data.get("error", ""),
    }


def get_preopen_status() -> Dict:
    rows = sb_get("market_spot_snapshots", "select=ts,spot,symbol&order=ts.asc&limit=10")
    today = now_ist().strftime("%Y-%m-%d")
    captured = []
    for row in rows:
        dt = parse_ist_dt(row.get("ts", ""))
        if dt and dt.strftime("%Y-%m-%d") == today and dt.hour == 9 and dt.minute < 9:
            captured.append({
                "ts": dt.strftime("%H:%M:%S"),
                "spot": row.get("spot"),
                "symbol": row.get("symbol"),
            })
    return {"captured": len(captured) > 0, "count": len(captured), "rows": captured[:3]}


def get_pipeline_stages() -> Dict:
    result = {}
    for symbol in ["NIFTY", "SENSEX"]:
        stages = []

        rows = sb_get("option_chain_snapshots", f"select=ts,spot&symbol=eq.{symbol}&order=ts.desc&limit=1")
        if rows:
            ts = rows[0].get("ts", "")
            dt = parse_ist_dt(ts)
            lag = lag_sec(ts)
            stages.append({"name": "Options", "ts": dt.strftime("%H:%M:%S") if dt else "?",
                           "value": f"Spot {rows[0].get('spot','?')}", "lag": lag, "ok": lag is not None and lag < 600})
        else:
            stages.append({"name": "Options", "ts": "—", "value": "—", "lag": None, "ok": False})

        rows = sb_get("gamma_metrics", f"select=ts,regime,flip_level&symbol=eq.{symbol}&order=ts.desc&limit=1")
        if rows:
            ts = rows[0].get("ts", "")
            dt = parse_ist_dt(ts)
            lag = lag_sec(ts)
            flip = rows[0].get("flip_level")
            stages.append({"name": "Gamma", "ts": dt.strftime("%H:%M:%S") if dt else "?",
                           "value": f"{rows[0].get('regime','?')} / flip {int(flip) if flip else '?'}",
                           "lag": lag, "ok": lag is not None and lag < 600})
        else:
            stages.append({"name": "Gamma", "ts": "—", "value": "—", "lag": None, "ok": False})

        rows = sb_get("volatility_snapshots", f"select=ts,india_vix,vix_regime,atm_iv_avg&symbol=eq.{symbol}&order=ts.desc&limit=1")
        if rows:
            ts = rows[0].get("ts", "")
            dt = parse_ist_dt(ts)
            lag = lag_sec(ts)
            vix = rows[0].get("india_vix", "?")
            iv = rows[0].get("atm_iv_avg")
            stages.append({"name": "Volatility", "ts": dt.strftime("%H:%M:%S") if dt else "?",
                           "value": f"VIX {vix} {rows[0].get('vix_regime','?')} / IV {f'{iv:.1f}%' if iv else '?'}",
                           "lag": lag, "ok": lag is not None and lag < 600})
        else:
            stages.append({"name": "Volatility", "ts": "—", "value": "—", "lag": None, "ok": False})

        rows = sb_get("momentum_snapshots", f"select=ts,momentum_regime,ret_session&symbol=eq.{symbol}&order=ts.desc&limit=1")
        if rows:
            ts = rows[0].get("ts", "")
            dt = parse_ist_dt(ts)
            lag = lag_sec(ts)
            ret_s = rows[0].get("ret_session")
            stages.append({"name": "Momentum", "ts": dt.strftime("%H:%M:%S") if dt else "?",
                           "value": f"{rows[0].get('momentum_regime','?')} / sess {f'{ret_s*100:.2f}%' if ret_s is not None else '?'}",
                           "lag": lag, "ok": lag is not None and lag < 600})
        else:
            stages.append({"name": "Momentum", "ts": "—", "value": "—", "lag": None, "ok": False})

        rows = sb_get("market_state_snapshots", f"select=ts,gamma_features,wcb_features&symbol=eq.{symbol}&order=ts.desc&limit=1")
        if rows:
            ts = rows[0].get("ts", "")
            dt = parse_ist_dt(ts)
            lag = lag_sec(ts)
            gf = rows[0].get("gamma_features") or {}
            if isinstance(gf, str):
                try: gf = json.loads(gf)
                except: gf = {}
            wf = rows[0].get("wcb_features") or {}
            if isinstance(wf, str):
                try: wf = json.loads(wf)
                except: wf = {}
            gamma_r = gf.get("regime", gf.get("gamma_regime", "?"))
            wcb_r = wf.get("wcb_regime", "?")
            stages.append({"name": "Market State", "ts": dt.strftime("%H:%M:%S") if dt else "?",
                           "value": f"γ:{gamma_r} WCB:{wcb_r}",
                           "lag": lag, "ok": lag is not None and lag < 600})
        else:
            stages.append({"name": "Market State", "ts": "—", "value": "—", "lag": None, "ok": False})

        rows = sb_get("signal_snapshots", f"select=created_at,action,confidence_score,trade_allowed&symbol=eq.{symbol}&order=created_at.desc&limit=1")
        if rows:
            ts = rows[0].get("created_at", "")
            dt = parse_ist_dt(ts)
            lag = lag_sec(ts)
            action = rows[0].get("action", "?")
            conf = rows[0].get("confidence_score", "?")
            allowed = rows[0].get("trade_allowed", False)
            stages.append({"name": "Signal", "ts": dt.strftime("%H:%M:%S") if dt else "?",
                           "value": f"{action} | conf {conf} | {'✓' if allowed else '✗'}",
                           "lag": lag, "ok": lag is not None and lag < 600,
                           "action": action, "allowed": allowed})
        else:
            stages.append({"name": "Signal", "ts": "—", "value": "—", "lag": None, "ok": False})

        result[symbol] = stages
    return result


def get_breadth_status() -> Dict:
    rows = sb_get("market_breadth_intraday", "select=ts,advances,declines,breadth_score,breadth_regime&order=ts.desc&limit=1")
    if rows:
        ts = rows[0].get("ts", "")
        dt = parse_ist_dt(ts)
        lag = lag_sec(ts)
        return {
            "ok": lag is not None and lag < 600,
            "ts": dt.strftime("%H:%M:%S IST") if dt else "?",
            "lag": lag,
            "advances": rows[0].get("advances", "?"),
            "declines": rows[0].get("declines", "?"),
            "regime": rows[0].get("breadth_regime", "?"),
            "score": rows[0].get("breadth_score", "?"),
        }
    return {"ok": False, "ts": "no data", "lag": None, "advances": "?", "declines": "?", "regime": "?", "score": "?"}


def get_aws_status() -> Dict:
    rows = sb_get("system_config", "select=config_value,updated_at&config_key=eq.aws_shadow_cycle_status")
    if not rows:
        return {"available": False, "last_cycle_ts": "never", "last_cycle_ok": None,
                "breadth_coverage": None, "per_symbol": {}, "last_error": "", "lag": None}
    try:
        raw = rows[0].get("config_value", "{}")
        data = json.loads(raw) if isinstance(raw, str) else raw
        updated_at = rows[0].get("updated_at", "")
        dt = parse_ist_dt(updated_at)
        lag = lag_sec(updated_at)
        return {
            "available": True,
            "last_cycle_ts": dt.strftime("%H:%M:%S IST") if dt else "?",
            "last_cycle_ok": data.get("cycle_ok"),
            "breadth_coverage": data.get("breadth_coverage"),
            "per_symbol": data.get("per_symbol", {}),
            "last_error": data.get("last_error", ""),
            "lag": lag,
        }
    except Exception as e:
        return {"available": False, "last_cycle_ts": "error", "last_cycle_ok": None,
                "breadth_coverage": None, "per_symbol": {}, "last_error": str(e), "lag": None}


def get_heartbeats() -> Dict:
    comps = {
        "gamma_engine_supervisor": "Supervisor",
        "run_option_snapshot_intraday_runner": "Runner",
        "gamma_engine_telemetry_logger": "Telemetry",
        "gamma_engine_alert_daemon": "Alert Daemon",
    }
    result = {}
    for comp, label in comps.items():
        data = read_json(HEARTBEAT_DIR / f"{comp}.json")
        if data.get("last_heartbeat_utc"):
            try:
                ts = datetime.fromisoformat(data["last_heartbeat_utc"].replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age = int((datetime.now(timezone.utc) - ts).total_seconds())
                stale_after = data.get("stale_after_seconds", 180)
                result[label] = {"ok": age <= stale_after, "age": age, "notes": data.get("notes", "")[:80]}
            except Exception:
                result[label] = {"ok": False, "age": None, "notes": "parse error"}
        else:
            result[label] = {"ok": False, "age": None, "notes": "no heartbeat file"}
    return result


def collect_data() -> Dict:
    return {
        "now": now_ist().strftime("%Y-%m-%d %H:%M:%S IST"),
        "session": get_session_info(),
        "token": get_token_status(),
        "preopen": get_preopen_status(),
        "pipeline": get_pipeline_stages(),
        "breadth": get_breadth_status(),
        "aws": get_aws_status(),
        "heartbeats": get_heartbeats(),
    }


def build_html(data: Dict) -> str:
    session = data["session"]
    token = data["token"]
    preopen = data["preopen"]
    pipeline = data["pipeline"]
    breadth = data["breadth"]
    aws = data["aws"]
    hb = data["heartbeats"]

    state = session["state"]
    state_colors = {
        "REGULAR_SESSION": "#1a7a1a", "PREMARKET_MONITOR": "#1565c0",
        "PREMARKET_REF_DUE": "#1565c0", "OPEN_WAIT": "#1565c0",
        "CLOSE_REF_DUE": "#b45000", "POSTMARKET_COMPLETE": "#555",
        "CLOSED": "#555", "ERROR": "#8b0000",
    }
    state_color = state_colors.get(state, "#555")

    token_ok = token.get("success") is True
    token_fail = token.get("success") is False
    countdown, countdown_color = fmt_expiry_countdown(token.get("expiry", ""))

    preopen_html = ""
    for r in preopen.get("rows", []):
        preopen_html += f'<div style="font-size:12px;margin:2px 0;color:#333">{r["ts"]} — {r["symbol"]} <strong>{r["spot"]}</strong></div>'
    if not preopen_html:
        preopen_html = '<div style="font-size:12px;color:#888">No pre-open data for today</div>'

    pipeline_rows = ""
    for symbol in ["NIFTY", "SENSEX"]:
        stages = pipeline.get(symbol, [])
        cells = ""
        for stage in stages:
            lag = stage.get("lag")
            ok = stage.get("ok", False)
            bg = "#e8f5e9" if ok else "#ffebee" if lag is not None else "#f5f5f5"
            tc = "#1a7a1a" if ok else "#8b0000" if lag is not None else "#888"
            val = (stage.get("value") or "—")[:30]
            cells += f"""<td style="padding:5px 6px;text-align:center;border-right:1px solid #eee">
                <div style="font-size:11px;font-weight:600;color:{tc};background:{bg};border-radius:3px;padding:1px 4px">{stage.get('ts','—')}</div>
                <div style="font-size:10px;color:#555;margin-top:2px;white-space:nowrap;overflow:hidden;max-width:110px;text-overflow:ellipsis" title="{stage.get('value','')}">{val}</div>
            </td>"""
        pipeline_rows += f"""<tr style="border-bottom:1px solid #eee">
            <td style="padding:8px 10px;font-weight:700;font-size:13px;border-right:1px solid #eee;white-space:nowrap">{symbol}</td>
            {cells}
        </tr>"""

    aws_sym_html = ""
    for sym, status in aws.get("per_symbol", {}).items():
        color = "#1a7a1a" if status == "OK" else "#8b0000"
        aws_sym_html += f'<span style="margin-right:10px;font-size:12px;color:{color}">{sym}: <strong>{status}</strong></span>'

    hb_rows = ""
    for label, h in hb.items():
        ok = h.get("ok", False)
        age = h.get("age")
        hb_rows += f"""<tr style="border-bottom:1px solid #f0f0f0">
            <td style="padding:6px 12px;font-size:12px">{label}</td>
            <td style="padding:6px 12px">{badge(ok)}</td>
            <td style="padding:6px 12px;font-size:11px;color:#666">{fmt_lag(age)} ago</td>
            <td style="padding:6px 12px;font-size:11px;color:#888">{h.get('notes','')}</td>
        </tr>"""

    with _action_lock:
        results = dict(_action_results)

    btns_html = ""
    for aid, ainfo in ACTIONS.items():
        confirm = (ainfo.get("confirm") or "").replace('"', '&quot;')
        confirm_attr = f'onclick="return confirm(\"{confirm}\")"' if confirm else ""
        is_aws = ainfo.get("aws", False)
        btn_bg = "#e3f2fd" if is_aws else "#fff"
        last = results.get(aid, {})
        feedback = ""
        if last:
            ok = last.get("ok")
            out = (last.get("output") or "")[:250].replace("<", "&lt;").replace(">", "&gt;")
            fb_bg = "#e8f5e9" if ok else "#ffebee"
            fb_col = "#1a7a1a" if ok else "#8b0000"
            feedback = f'<div style="margin-top:4px;padding:4px 8px;background:{fb_bg};border-radius:4px;font-size:11px;color:{fb_col}">{last.get("ts","")} — {"SUCCESS" if ok else "FAILED"}<br><code style="color:#333;font-size:10px">{out}</code></div>'
        btns_html += f"""<div style="margin:6px 0;padding:8px 10px;border:1px solid #e1e4e8;border-radius:6px;background:{btn_bg}">
            <form method="POST" action="/action/{aid}" style="display:inline">
                <button type="submit" {confirm_attr} style="padding:6px 16px;border:1px solid #bbb;border-radius:4px;background:#fff;cursor:pointer;font-size:13px;font-weight:500">
                    {'🔵 ' if is_aws else ''}{ainfo['label']}
                </button>
            </form>
            {feedback}
        </div>"""

    next_banner = f'<div style="font-size:11px;color:#8b949e;margin-top:2px">Next: <strong style="color:#79c0ff">{session["next_event"]}</strong> in {session["next_in"]}</div>' if session.get("next_event") else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<title>MERDIAN</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#f0f2f5;color:#222;font-size:13px}}
.hdr{{background:#0d1117;color:#fff;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}}
.hdr h1{{font-size:17px;letter-spacing:1px;font-weight:600}}
.card{{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin:8px 14px;overflow:hidden}}
.ct{{background:#f6f8fa;padding:7px 14px;font-size:11px;font-weight:700;color:#444;border-bottom:1px solid #e1e4e8;text-transform:uppercase;letter-spacing:0.5px}}
.cb{{padding:10px 14px}}
table{{width:100%;border-collapse:collapse}}
th{{background:#f6f8fa;padding:6px 10px;text-align:left;font-size:11px;color:#666;border-bottom:1px solid #e1e4e8;font-weight:700;text-transform:uppercase}}
.g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0 8px;margin:0 14px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:0 8px;margin:0 14px}}
</style>
</head>
<body>

<div class="hdr">
  <div>
    <h1>MERDIAN Live Dashboard</h1>
    <div style="font-size:11px;color:#8b949e;margin-top:2px">Market Structure Intelligence Engine · Auto-refresh 30s</div>
  </div>
  <div style="text-align:right">
    <div style="font-size:15px">{data["now"]}</div>
    <div style="font-size:12px;color:#8b949e;margin-top:1px">State: <strong style="color:{state_color}">{state}</strong>{'&nbsp;·&nbsp;' + session['open_time'] + '–' + session['close_time'] if session['is_open'] else ''}</div>
    {next_banner}
  </div>
</div>

<div class="g3" style="margin-top:8px">

  <div class="card">
    <div class="ct">Session</div>
    <div class="cb">
      <div style="font-size:20px;font-weight:700;color:{state_color}">{state.replace('_',' ')}</div>
      <div style="font-size:11px;color:#666;margin-top:4px">{session['date']} · {session['notes']}</div>
      {'<div style="font-size:11px;color:#1565c0;margin-top:5px">Next: <strong>' + session['next_event'] + '</strong> in ' + session['next_in'] + '</div>' if session.get('next_event') else ''}
    </div>
  </div>

  <div class="card">
    <div class="ct">Dhan Token</div>
    <div class="cb">
      <div>{badge(token_ok if not token_fail else False, "VALID", "FAILED", "UNKNOWN")}</div>
      <div style="font-size:12px;margin-top:5px">Refreshed: <strong>{token['refreshed_at']}</strong></div>
      <div style="font-size:11px;color:#666;margin-top:2px">Expires: {token.get('expiry','?')[:19] if token.get('expiry') else 'unknown'}</div>
      <div style="font-size:12px;font-weight:600;color:{countdown_color};margin-top:2px">{countdown}</div>
      {'<div style="font-size:10px;color:#8b0000;margin-top:2px">' + token.get('error','')[:80] + '</div>' if token.get('error') else ''}
    </div>
  </div>

  <div class="card">
    <div class="ct">Pre-open 09:00–09:08</div>
    <div class="cb">
      <div>{badge(preopen['captured'], f"CAPTURED ({preopen['count']} rows)", "NOT CAPTURED", "NOT CAPTURED")}</div>
      <div style="margin-top:5px">{preopen_html}</div>
    </div>
  </div>

</div>

<div class="card">
  <div class="ct">Pipeline Stages</div>
  <table>
    <tr>
      <th style="width:65px">Symbol</th>
      <th style="text-align:center">Options</th>
      <th style="text-align:center">Gamma</th>
      <th style="text-align:center">Volatility</th>
      <th style="text-align:center">Momentum</th>
      <th style="text-align:center">Market State</th>
      <th style="text-align:center">Signal</th>
    </tr>
    {pipeline_rows}
  </table>
</div>

<div class="g2">

  <div class="card">
    <div class="ct">Breadth (Local)</div>
    <div class="cb">
      <div>{staleness_badge(breadth.get('lag'))}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:8px">
        <div style="font-size:12px">Advances: <strong style="color:#1a7a1a">{breadth['advances']}</strong></div>
        <div style="font-size:12px">Declines: <strong style="color:#8b0000">{breadth['declines']}</strong></div>
        <div style="font-size:12px">Regime: <strong>{breadth['regime']}</strong></div>
        <div style="font-size:12px">Score: <strong>{breadth['score']}</strong></div>
      </div>
      <div style="font-size:11px;color:#666;margin-top:4px">Last: {breadth['ts']}</div>
    </div>
  </div>

  <div class="card">
    <div class="ct">🔵 AWS Shadow Runner</div>
    <div class="cb">
      {'<div>' + badge(aws.get("last_cycle_ok"), "LAST CYCLE OK", "LAST CYCLE FAILED", "NO STATUS YET") + '</div>' if aws.get('available') else '<div style="color:#888;font-size:12px">No Supabase status yet — runner not started or never wrote status</div>'}
      <div style="font-size:12px;margin-top:5px">Last cycle: <strong>{aws['last_cycle_ts']}</strong> {staleness_badge(aws.get('lag')) if aws.get('available') else ''}</div>
      <div style="margin-top:4px">{aws_sym_html}</div>
      {'<div style="font-size:11px;color:#1a7a1a;margin-top:3px">Breadth coverage: ' + str(aws.get('breadth_coverage','?')) + '%</div>' if aws.get('breadth_coverage') else ''}
      {'<div style="font-size:11px;color:#8b0000;margin-top:3px">' + str(aws.get('last_error',''))[:100] + '</div>' if aws.get('last_error') else ''}
    </div>
  </div>

</div>

<div class="card">
  <div class="ct">Component Heartbeats</div>
  <table>
    <tr><th>Component</th><th>Status</th><th>Last Beat</th><th>Notes</th></tr>
    {hb_rows if hb_rows else '<tr><td colspan="4" style="padding:10px;color:#888;text-align:center">No heartbeat files</td></tr>'}
  </table>
</div>

<div class="card">
  <div class="ct">Actions — result shown inline after click</div>
  <div style="padding:10px 14px">{btns_html}</div>
</div>

<div style="text-align:right;padding:4px 18px 10px;font-size:10px;color:#aaa">MERDIAN v2 · {data["now"]}</div>
</body>
</html>"""


def _run_action(action_id: str, ainfo: dict) -> None:
    ts = now_ist().strftime("%H:%M:%S IST")
    try:
        result = subprocess.run(
            ainfo["cmd"],
            cwd=str(BASE_DIR),
            capture_output=True,
            timeout=ainfo.get("timeout", 60),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        stdout = result.stdout.decode("utf-8", errors="replace").strip() if result.stdout else ""
        stderr = result.stderr.decode("utf-8", errors="replace").strip() if result.stderr else ""
        output = stdout[-400:] or stderr[-400:]
        ok = result.returncode == 0
    except subprocess.TimeoutExpired:
        ok, output = False, "Timed out"
    except Exception as e:
        ok, output = False, str(e)[:300]
    # Strip non-ASCII characters that cause cp1252 encoding errors on Windows
    output = output.encode("ascii", errors="replace").decode("ascii")
    with _action_lock:
        _action_results[action_id] = {"ok": ok, "ts": ts, "output": output}


class DashboardHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            html = build_html(collect_data())
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(html.encode("utf-8", errors="replace"))
        except Exception as e:
            try:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())
            except Exception:
                pass

    def do_POST(self):
        if not self.path.startswith("/action/"):
            self.send_response(404)
            self.end_headers()
            return
        action_id = self.path[len("/action/"):]
        ainfo = ACTIONS.get(action_id)
        if not ainfo:
            self.send_response(404)
            self.end_headers()
            return
        t = threading.Thread(target=_run_action, args=(action_id, ainfo), daemon=True)
        t.start()
        t.join(timeout=5)  # Wait up to 5s so result is ready for redirect
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = HTTPServer(("localhost", args.port), DashboardHandler)
    print(f"MERDIAN Live Dashboard running at http://localhost:{args.port}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
