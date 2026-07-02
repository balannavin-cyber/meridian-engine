"""ENH-115 P1 — participant positioning + cash-flow daily writer.

Runs once EOD (post ~18:30 IST) on MERDIAN AWS. Source-only, display-not-gate.
  1. trading-day gate (core/trading_calendar_gate) — skip weekends/holidays.
  2. fetch + parse NSE participant-wise OI  -> participant_oi_daily (exchange='NSE')
  3. fetch + parse BSE participant-wise OI  -> participant_oi_daily (exchange='BSE')   [TODO: live format]
  4. fetch + parse consolidated FII/DII cash -> fii_dii_cash_daily                      [TODO: live header]
  5. UPSERT via raw-HTTP PostgREST (house convention, D.18); ENH-72 write-contract.

Publish lag: NSE publishes ~17:00-19:00 IST, later on expiry days. A not-yet-
published file (404 / empty) is a BENIGN skip (exit_reason SKIPPED_NO_INPUT),
NOT a failure — cron re-fires on a later slot. Never carry a prior day forward.

Usage:
    python ingest_participant_positioning.py                 # today IST, NSE (+BSE/cash when wired)
    python ingest_participant_positioning.py --date 2026-07-01
    python ingest_participant_positioning.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

from core.execution_log import ExecutionLog                     # ENH-72 write-contract
from core.trading_calendar_gate import assert_trading_day_or_exit, is_trading_day
from parse_participant_oi import parse_nse_participant_oi

IST = timezone(timedelta(hours=5, minutes=30))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# NSE archive is date-templated and generally served without the www cookie dance.
NSE_PARTICIPANT_URL = "https://archives.nseindia.com/content/nsccl/fao_participant_oi_{ddmmyyyy}.csv"
NSE_HOME = "https://www.nseindia.com"
NSE_CASH_URL = "https://www.nseindia.com/api/fiidiiTradeReact"  # consolidated NSE+BSE+MSEI cash


def _env():
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing")
    return url, key


def _fetch_nse_participant_csv(trade_date_iso: str) -> str | None:
    """Return CSV text, or None if not-yet-published (benign)."""
    dd = datetime.fromisoformat(trade_date_iso).strftime("%d%m%Y")
    url = NSE_PARTICIPANT_URL.format(ddmmyyyy=dd)
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "text/csv,*/*"})
    r = s.get(url, timeout=30)
    if r.status_code in (403, 401):
        # warm cookies via the homepage, then retry once (www anti-bot posture)
        s.get(NSE_HOME, timeout=30)
        r = s.get(url, timeout=30)
    if r.status_code == 404:
        return None                       # not published yet -> benign skip
    r.raise_for_status()
    text = r.text.strip()
    if not text or "Participant wise Open Interest" not in text:
        return None                       # empty / placeholder -> benign skip
    return text


def _upsert(url: str, key: str, table: str, rows: list[dict], on_conflict: str) -> int:
    """Raw-HTTP PostgREST upsert (D.18 house convention; no Prefer=representation)."""
    if not rows:
        return 0
    resp = requests.post(
        f"{url}/rest/v1/{table}",
        params={"on_conflict": on_conflict},
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        json=rows,
        timeout=60,
    )
    resp.raise_for_status()
    return len(rows)


def _fetch_nse_cash():
    """Fetch the consolidated FII/DII cash JSON. www host needs the cookie
    warm-up (unlike the permissive archives host). Returns parsed JSON or None."""
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json,*/*",
                      "Referer": "https://www.nseindia.com/reports/fii-dii"})
    s.get(NSE_HOME, timeout=30)                     # warm cookies
    r = s.get(NSE_CASH_URL, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    try:
        data = r.json()
    except Exception:
        return None
    return data or None


def parse_cash(data, requested_date=None):
    """Map fiidiiTradeReact rows -> one fii_dii_cash_daily record.
    Rows carry category (FII/FPI, DII), date (e.g. '01-Jul-2026'), buy/sell/net."""
    def num(x):
        try:
            return float(str(x).replace(",", "").strip())
        except Exception:
            return None

    fii = dii = None
    trade_date = None
    for row in data:
        cat = str(row.get("category", "")).upper()
        d = str(row.get("date", "")).strip()
        if d and trade_date is None:
            try:
                trade_date = datetime.strptime(d, "%d-%b-%Y").date().isoformat()
            except Exception:
                pass
        if "FII" in cat or "FPI" in cat:
            fii = row
        elif "DII" in cat:
            dii = row
    if fii is None and dii is None:
        return None, None
    rec = {
        "trade_date": trade_date or requested_date,
        "scope": "NSE_BSE_MSEI",
        "fii_buy_cr": num(fii.get("buyValue")) if fii else None,
        "fii_sell_cr": num(fii.get("sellValue")) if fii else None,
        "fii_net_cr": num(fii.get("netValue")) if fii else None,
        "dii_buy_cr": num(dii.get("buyValue")) if dii else None,
        "dii_sell_cr": num(dii.get("sellValue")) if dii else None,
        "dii_net_cr": num(dii.get("netValue")) if dii else None,
        "source": "nse_fiidiiTradeReact",
    }
    return rec["trade_date"], rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(IST).date().isoformat(),
                    help="IST trade date (default: today IST)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    log = ExecutionLog(
        script_name="ingest_participant_positioning.py",
        expected_writes={"participant_oi_daily": 5},   # NSE board = 5 participant rows
        notes=f"date={args.date}",
    )

    # Trading-day gate — assert_trading_day_or_exit logs HOLIDAY_GATE + exits on non-trading days.
    if not is_trading_day(args.date):
        return log.exit_with_reason("HOLIDAY_GATE", exit_code=0,
                                    error_message=f"{args.date} not a trading day")

    try:
        csv_text = _fetch_nse_participant_csv(args.date)
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"NSE fetch failed: {e}")

    if csv_text is None:
        # publish lag — benign, cron re-fires later; do NOT write a stale row.
        return log.exit_with_reason("SKIPPED_NO_INPUT", exit_code=0,
                                    error_message="NSE participant OI not yet published")

    try:
        trade_date, rows = parse_nse_participant_oi(csv_text, exchange="NSE")
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"NSE parse failed: {e}")

    if trade_date != args.date:
        # published file is for a different session than requested — surface, don't guess.
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"file date {trade_date} != requested {args.date}")

    if args.dry_run:
        print(f"[DRY-RUN] {trade_date} NSE: {len(rows)} participant rows parsed; no write.")
        for r in rows:
            print(f"  {r['participant']:<6} fut_idx {r['fut_idx_long']}/{r['fut_idx_short']}")
        print("\n[DRY-RUN] cash probe (fiidiiTradeReact) — raw then parsed:")
        try:
            cash_raw = _fetch_nse_cash()
            import json as _json
            print(_json.dumps(cash_raw, indent=2)[:1200] if cash_raw else "  (no cash payload)")
            if cash_raw:
                cdate, crow = parse_cash(cash_raw, requested_date=args.date)
                print(f"  parsed -> date={cdate} fii_net={crow['fii_net_cr']} "
                      f"dii_net={crow['dii_net_cr']}")
        except Exception as e:
            print(f"  cash probe error: {e}")
        return 0

    url, key = _env()
    try:
        n = _upsert(url, key, "participant_oi_daily", rows, on_conflict="exchange,trade_date,participant")
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=f"upsert failed: {e}")
    log.record_write("participant_oi_daily", n)
    print(f"participant_oi_daily NSE {trade_date}: upserted {n} rows")

    # --- Consolidated FII/DII cash (scope='NSE_BSE_MSEI') --------------------
    # Best-effort: a cash failure must NOT undo the participant write above.
    try:
        cash_raw = _fetch_nse_cash()
        if cash_raw:
            cdate, crow = parse_cash(cash_raw, requested_date=args.date)
            if crow and crow["trade_date"] == args.date:
                m = _upsert(url, key, "fii_dii_cash_daily", [crow],
                            on_conflict="trade_date,scope")
                log.record_write("fii_dii_cash_daily", m)
                print(f"fii_dii_cash_daily {cdate}: upserted {m} row "
                      f"(fii_net={crow['fii_net_cr']} dii_net={crow['dii_net_cr']})")
            else:
                got = crow["trade_date"] if crow else None
                print(f"[cash] skipped — payload date {got} != {args.date} (not yet updated)")
        else:
            print("[cash] no payload (not yet published) — skipped, non-fatal")
    except Exception as e:
        print(f"[cash] non-fatal error, participant write stands: {e}")

    # --- BSE participant OI (exchange='BSE') ---------------------------------
    # Dropped for P1: participant-wise OI is an NSE/NSCCL-only report; BSE has no
    # equivalent board. BSE (+SENSEX) exposure is covered by the consolidated cash
    # above. exchange='BSE' remains a harmless schema capability for the future.

    return log.complete()


if __name__ == "__main__":
    sys.exit(main())
