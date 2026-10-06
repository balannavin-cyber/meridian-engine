#!/usr/bin/env python3
"""
check_contracts_shadow.py — S90 DRAFT, roadmap R1.2 (SC, shadow, report-only).

Reads public.data_contracts + public.product_lineage (ADR-031 D1) and writes one
public.cycle_health row per product per cycle (ADR-031 D2). Blocks nothing,
feeds no consumer, changes no live table. Generated checks only — there is no
per-table code in this file; every threshold comes from the contract row.

Checks per product (own status):
  calendar   intraday product outside its session, or a closed day   -> CLOSED
  presence   no row at all for the scope                              -> MISSING
  freshness  intraday: newest row older than freshness_sla_min        -> MISSING
             daily:    newest date more than sla/1440 trading days back-> MISSING
  shape      rows / distinct expiries at the newest time outside the
             contract's expected_per_cycle ranges                     -> DEGRADED
  movement   movement_cols identical across movement_window_cycles+1
             newest times (intraday products only)                    -> STALE
Lineage (inherited status): an input that is MISSING / STALE / NOT_COMPUTED
makes its dependant STALE (its rows exist but rest on bad inputs); UNKNOWN
propagates as UNKNOWN; DEGRADED as DEGRADED; CLOSED is ignored.
Final = worse of own and inherited. Order:
  MISSING > NOT_COMPUTED > STALE > UNKNOWN > DEGRADED > OK ; CLOSED stands alone.

Usage (after the DDL is applied and ruled):
  python3 check_contracts_shadow.py                 # print only (default)
  python3 check_contracts_shadow.py --write         # also upsert cycle_health
  python3 check_contracts_shadow.py --as-of 2026-10-05T09:35:00Z
--as-of bounds every read (time_col <= as_of), so the same code scores history.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
SESSION_OPEN, SESSION_CLOSE = time(9, 15), time(15, 30)
SEVERITY = {"OK": 0, "DEGRADED": 1, "UNKNOWN": 2, "STALE": 3, "NOT_COMPUTED": 4, "MISSING": 5}
SCRIPT = "check_contracts_shadow.py"


# ---------------------------------------------------------------- pure logic
def worse(a: str, b: str) -> str:
    """Worse of two statuses; CLOSED never wins against a real status."""
    if a == "CLOSED":
        return b
    if b == "CLOSED":
        return a
    return a if SEVERITY[a] >= SEVERITY[b] else b


def inherited_from(input_status: str) -> str:
    if input_status in ("MISSING", "STALE", "NOT_COMPUTED"):
        return "STALE"
    if input_status in ("UNKNOWN", "DEGRADED"):
        return input_status
    return "OK"  # OK and CLOSED inputs impose nothing


def in_range(value: int, rng: Optional[List[int]]) -> bool:
    return rng is None or (rng[0] <= value <= rng[1])


def signature(rows: List[Dict[str, Any]], cols: List[str]) -> str:
    vals = sorted(json.dumps([r.get(c) for c in cols], default=str) for r in rows)
    return hashlib.sha256("|".join(vals).encode()).hexdigest()


def is_daily(contract: Dict[str, Any]) -> bool:
    return int(contract["cadence_min"]) >= 1440


def session_open_at(as_of: datetime, is_trading_day) -> bool:
    local = as_of.astimezone(IST)
    return is_trading_day(local.date().isoformat()) and SESSION_OPEN <= local.time() <= SESSION_CLOSE


def own_status(contract: Dict[str, Any], newest: Optional[Any], at_newest: List[Dict[str, Any]],
               window: Dict[Any, List[Dict[str, Any]]], as_of: datetime, open_now: bool,
               trading_days_behind: Optional[int]) -> Tuple[str, str, Dict[str, Any]]:
    """Return (status, reason, checks). Pure: all data is passed in."""
    checks: Dict[str, Any] = {}
    daily = is_daily(contract)
    if not daily and not open_now:
        return "CLOSED", "outside session or closed day", {"calendar": "closed"}
    if newest is None:
        return "MISSING", "no row for scope", {"presence": False}
    checks["presence"] = True

    if daily:
        allowed = max(1, int(contract["freshness_sla_min"]) // 1440)
        checks["trading_days_behind"] = trading_days_behind
        if trading_days_behind is None:
            return "UNKNOWN", "trading-day distance not resolvable", checks
        if trading_days_behind > allowed:
            return "MISSING", f"newest {newest} is {trading_days_behind} trading days behind (allowed {allowed})", checks
    else:
        # S90_SESSION_END: a product whose writer stops before the market closes (spot: the
        # ADR-022 CAS guard ends capture at 15:14) is judged for freshness AS OF its own session
        # end once that has passed. A feed that died before the end still fails; a product with
        # no session_end_ist keeps the 15:30 session.
        judged_at = as_of
        end = contract.get("session_end_ist")
        if end:
            hh, mm = (int(x) for x in str(end)[:5].split(":"))
            local = as_of.astimezone(IST)
            end_dt = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if local > end_dt:
                judged_at = end_dt.astimezone(as_of.tzinfo)
                checks["judged_at_session_end"] = str(end)[:5]
        age_min = (judged_at - newest).total_seconds() / 60.0
        checks["age_min"] = round(age_min, 1)
        if age_min > int(contract["freshness_sla_min"]):
            return "MISSING", f"newest row {age_min:.0f} min old (SLA {contract['freshness_sla_min']})", checks

    status, reasons = "OK", []
    exp = contract.get("expected_per_cycle") or {}
    n_rows = len(at_newest)
    checks["rows_at_newest"] = n_rows
    if not in_range(n_rows, exp.get("rows")):
        status, reasons = "DEGRADED", reasons + [f"rows {n_rows} outside {exp.get('rows')}"]
    if exp.get("expiries") is not None:
        n_exp = len({r.get("expiry_date") for r in at_newest})
        checks["expiries_at_newest"] = n_exp
        if not in_range(n_exp, exp["expiries"]):
            status, reasons = "DEGRADED", reasons + [f"expiries {n_exp} outside {exp['expiries']}"]

    cols = list(contract.get("movement_cols") or [])
    need = int(contract.get("movement_window_cycles") or 3) + 1
    if cols and not daily:
        sigs = [signature(window[t], cols) for t in sorted(window)[-need:]]
        checks["movement_points"] = len(sigs)
        if len(sigs) >= need and len(set(sigs)) == 1:
            status = worse(status, "STALE")
            reasons.append(f"{','.join(cols)} unchanged across {len(sigs)} cycles")
    if reasons:
        reasons.insert(0, f"newest {newest.isoformat() if hasattr(newest, 'isoformat') else newest}")
    return status, "; ".join(reasons) or None, checks


def propagate(own: Dict[str, Tuple[str, Optional[str]]], edges: List[Tuple[str, str]]) -> Dict[str, Tuple[str, Optional[str]]]:
    """Fixed-point propagation along product_lineage (acyclic expected)."""
    final = dict(own)
    for _ in range(len(own) + 1):
        changed = False
        for product, requires in edges:
            if product not in final or requires not in final:
                continue
            p_status, p_reason = final[product]
            r_status, _ = final[requires]
            if p_status == "CLOSED":
                continue
            inh = inherited_from(r_status)
            if inh == "OK":
                continue
            new = worse(p_status, inh)
            note = f"input {requires} {r_status}"
            if new != p_status or note not in (p_reason or ""):
                final[product] = (new, f"{p_reason}; {note}" if p_reason else note)
                changed = changed or new != p_status
        if not changed:
            break
    return final


# ---------------------------------------------------------------- I/O
def floor_cycle(ts: datetime) -> datetime:
    return ts.replace(minute=ts.minute - ts.minute % 5, second=0, microsecond=0)


_FRAC = re.compile(r"\.(\d{1,6})(?=[+-]\d{2}:?\d{2}$|Z$|$)")


def parse_ts(v: Any) -> Any:
    """ISO timestamp -> aware datetime. Pads fractional seconds to 6 digits:
    PostgREST trims trailing zeros ('03.89154') and Python < 3.11 rejects that."""
    if isinstance(v, str) and "T" in v:
        v = v.replace("Z", "+00:00")
        v = _FRAC.sub(lambda m: "." + m.group(1).ljust(6, "0"), v)
        return datetime.fromisoformat(v)
    return v


def scope_filters(c: Dict[str, Any]) -> Dict[str, str]:
    return {c["scope_col"]: f"eq.{c['scope_symbol']}"} if c.get("scope_symbol") else {}


PAGE = 1000  # PostgREST max_rows cap observed on this project (S90 first read)


def select_all(sb, table: str, columns: str, filters: Dict[str, str], order: str,
               stop_after: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Page through a select ordered ascending on `order`; a single select is silently
    capped at PAGE rows. stop_after: stop once a page passes this time -- the client takes
    one filter per column, so the upper bound is enforced by stopping, not by the query
    (S90: an --as-of a week back otherwise paged every row up to today)."""
    out: List[Dict[str, Any]] = []
    while True:
        page = sb.select(table, columns=columns, filters=filters, order=order, limit=PAGE, offset=len(out))
        out.extend(page)
        if len(page) < PAGE or len(out) >= 200_000:
            return out
        if stop_after is not None and parse_ts(page[-1][order]) > stop_after:
            return out


def count_exact(sb, table: str, filters: Dict[str, str]) -> int:
    if hasattr(sb, "count_exact"):  # S90 replay harness: fixture client counts in memory
        return sb.count_exact(table, filters)
    import requests
    h = dict(sb.headers); h["Prefer"] = "count=exact"; h["Range"] = "0-0"
    params = {"select": "*", **{k: sb._normalize_filter_value(v) for k, v in filters.items()}}
    r = requests.get(sb._url(table), headers=h, params=params, timeout=30)
    r.raise_for_status()
    return int(r.headers["Content-Range"].split("/")[-1])


def read_product(sb, c: Dict[str, Any], as_of: datetime):
    t = c["time_col"]
    bound = as_of.isoformat() if t == "ts" else as_of.astimezone(IST).date().isoformat()
    head = sb.select(c["relation_name"], columns=t, filters={**scope_filters(c), t: f"lte.{bound}"},
                     order=t, ascending=False, limit=1)
    if not head:
        return None, [], {}
    newest = parse_ts(head[0][t])
    if is_daily(c):
        n = count_exact(sb, c["relation_name"], {**scope_filters(c), t: f"eq.{head[0][t]}"})
        return newest, [{}] * n, {}
    exp_cols = ["expiry_date"] if (c.get("expected_per_cycle") or {}).get("expiries") else []
    cols = sorted(set(list(c.get("movement_cols") or []) + exp_cols + [t]))
    need = int(c.get("movement_window_cycles") or 3) + 1
    since = newest - timedelta(minutes=int(c["cadence_min"]) * (need + 1))
    rows = select_all(sb, c["relation_name"], ",".join(cols),
                      {**scope_filters(c), t: f"gte.{since.isoformat()}"}, order=t, stop_after=newest)
    window: Dict[Any, List[Dict[str, Any]]] = {}
    for r in rows:
        rt = parse_ts(r[t])
        if rt <= newest:  # upper bound applied here: one filter per column in this client
            window.setdefault(rt, []).append(r)
    return newest, window.get(newest, []), window


def trading_days_behind(newest_date_iso: str, as_of: datetime, prev_day) -> Optional[int]:
    d, n = as_of.astimezone(IST).date().isoformat(), 0
    while d > newest_date_iso and n < 15:
        d, prov = prev_day(d)
        if prov.startswith("fail-open"):
            return None
        n += 1
    return n if d <= newest_date_iso else None


def evaluate(sb, contracts: List[Dict[str, Any]], edges: List[Tuple[str, str]], as_of: datetime,
             now: datetime, is_trading_day, previous_trading_day):
    """Score every contract as of `as_of`. I/O only through `sb`, so the S90 replay harness
    (tests/replay) runs this exact code against frozen golden days with a fixture client."""
    open_now = session_open_at(as_of, is_trading_day)
    own: Dict[str, Tuple[str, Optional[str]]] = {}
    detail: Dict[str, Dict[str, Any]] = {}
    for c in contracts:
        historical = as_of < now - timedelta(minutes=15)
        g = c.get("grain") or []
        if historical and c["time_col"] not in g and "run_id" not in g:
            # grain with neither a time column nor run_id = one row per key, overwritten: no history
            own[c["product"]] = ("UNKNOWN", "latest-only product; cannot be judged as of a past time")
            detail[c["product"]] = {"history": False}
            continue
        if not is_daily(c) and not open_now:  # calendar first: no read outside the session
            own[c["product"]] = ("CLOSED", "outside session or closed day")
            detail[c["product"]] = {"calendar": "closed"}
            continue
        try:
            newest, at_newest, window = read_product(sb, c, as_of)
            behind = None
            if is_daily(c) and newest is not None:
                behind = trading_days_behind(str(newest)[:10], as_of, previous_trading_day)
            st, why, chk = own_status(c, newest, at_newest, window, as_of, open_now, behind)
        except Exception as e:  # a check that cannot run is UNKNOWN, never OK
            st, why, chk = "UNKNOWN", f"check failed: {type(e).__name__}: {e}"[:300], {}
        vf = c.get("valid_from")
        if vf and as_of < parse_ts(vf):
            # contracts are not versioned yet (PK = product): a past as-of is judged by
            # today's contract. Say so on the row rather than present it as in force.
            note = f"contract applied retroactively (in force from {str(vf)[:10]})"
            why = f"{why}; {note}" if why else (note if st != "OK" else None)
            chk = {**chk, "contract_in_force": False}
        own[c["product"]] = (st, why)
        detail[c["product"]] = chk

    return propagate(own, edges), own, detail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="upsert cycle_health (default: print only)")
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args()

    from core.supabase_client import SupabaseClient
    from core.execution_log import ExecutionLog
    from core.trading_calendar_gate import is_trading_day, previous_trading_day

    as_of = parse_ts(a.as_of) if a.as_of else datetime.now(timezone.utc)
    sb = SupabaseClient()
    contracts = sb.select("data_contracts", filters={"valid_to": "is.null"})
    edges = [(e["product"], e["requires"]) for e in sb.select("product_lineage")]
    # Print mode touches no table at all, not even the ledger.
    log = ExecutionLog(SCRIPT, expected_writes={"cycle_health": len(contracts)},
                       notes=f"R1.2 shadow as_of={as_of.isoformat()}") if a.write else None
    import subprocess
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    final, own, detail = evaluate(sb, contracts, edges, as_of, datetime.now(timezone.utc),
                                  is_trading_day, previous_trading_day)
    cycle_ts = floor_cycle(as_of)
    out = [{"product": p, "cycle_ts": cycle_ts.isoformat(), "status": s, "reason": r,
            "checks": {"own": own[p][0], **detail[p]}, "checker_version": sha}
           for p, (s, r) in sorted(final.items())]
    for row in out:
        print(f"{row['product']:<52} {row['status']:<12} {row['reason'] or ''}")
    if not a.write:
        return 0
    sb.upsert("cycle_health", out, on_conflict="product,cycle_ts")
    log.record_write("cycle_health", len(out))
    return log.complete()


if __name__ == "__main__":
    sys.exit(main())
