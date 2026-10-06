import ast, hashlib, sys
p = 'build_wcb_snapshot_local.py'; s = open(p).read()
MARK = 'S90_WCB_LIVE_LTP'
if MARK in s:
    print('already patched'); sys.exit(0)
assert hashlib.sha256(s.encode()).hexdigest().startswith('7194b4c19f76'), 'unexpected base version'
E = [
 ('def fetch_daily_breadth_rows(',
  f'# {MARK} (ruling S90-G, R01-F9): the move is live LTP (market_ticks, EQ) over the\n'
  '# PRIOR close. equity_intraday_last is refreshed once a day at 09:05 IST with Kite\n'
  '# ohlc().close, i.e. it IS the prior close -- it was being used as the live price, which\n'
  '# froze WCB for whole sessions (S90 MV-9). No ticks in the window => no live price =>\n'
  '# the constituent drops out (honest), never a stale fallback (ADR-023 D2).\n'
  'LIVE_TICK_WINDOW_MIN = 10\n\n\n'
  'def _bare(ticker: str) -> str:\n'
  '    return ticker.split(":", 1)[1] if ":" in ticker else ticker\n\n\n'
  'def fetch_live_ltp_from_ticks(sb: SupabaseClient, tickers: List[str]) -> List[Dict[str, Any]]:\n'
  '    if not tickers:\n'
  '        return []\n'
  '    by_bare = {_bare(t): t for t in tickers}\n'
  '    since = (datetime.now(timezone.utc) - timedelta(minutes=LIVE_TICK_WINDOW_MIN)).isoformat()\n'
  '    in_payload = "(" + ",".join(\'"\' + b + \'"\' for b in by_bare) + ")"\n'
  '    latest: Dict[str, Dict[str, Any]] = {}\n'
  '    offset, page = 0, 1000\n'
  '    while True:\n'
  '        rows = retry_call(\n'
  '            lambda: sb.select(\n'
  '                table="market_ticks",\n'
  '                columns="tradingsymbol,last_price,ts",\n'
  '                filters={"instrument_type": "eq.EQ", "ts": f"gte.{since}",\n'
  '                         "tradingsymbol": f"in.{in_payload}"},\n'
  '                order="ts.desc", limit=page, offset=offset,\n'
  '            ),\n'
  '            attempts=3, delay_seconds=5.0, backoff_multiplier=1.5,\n'
  '            label="select market_ticks EQ for WCB basket",\n'
  '        )\n'
  '        for r in rows:\n'
  '            b = r.get("tradingsymbol")\n'
  '            if b in by_bare and b not in latest and r.get("last_price") is not None:\n'
  '                latest[b] = {"ticker": by_bare[b], "last_price": r["last_price"], "ts": r.get("ts")}\n'
  '        if len(rows) < page or len(latest) == len(by_bare):\n'
  '            break\n'
  '        offset += page\n'
  '    return list(latest.values())\n\n\n'
  'def fetch_prev_close_map(sb: SupabaseClient, tickers: List[str]) -> Dict[str, float]:\n'
  '    out: Dict[str, float] = {}\n'
  '    for r in fetch_latest_intraday_prices(sb, tickers):\n'
  '        t = str(r.get("ticker") or "").strip().upper()\n'
  '        v = to_float(r.get("last_price"))\n'
  '        if t and v:\n'
  '            out[t] = v\n'
  '    return out\n\n\n'
  'def fetch_daily_breadth_rows('),
 ('    latest_breadth_row: Optional[Dict[str, Any]],\n) -> Dict[str, Any]:\n',
  '    latest_breadth_row: Optional[Dict[str, Any]],\n'
  f'    prev_close_map: Optional[Dict[str, float]] = None,  # {MARK}\n'
  ') -> Dict[str, Any]:\n'),
 ('        prev_close = to_float(daily.get("prev_close"))\n',
  '        prev_close = (prev_close_map.get(ticker) if prev_close_map is not None\n'
  '                      else to_float(daily.get("prev_close")))\n'),
 ('        intraday_rows = fetch_latest_intraday_prices(sb, tickers)\n',
  f'        # {MARK}: live LTP from market_ticks; prior close from equity_intraday_last\n'
  '        intraday_rows = fetch_live_ltp_from_ticks(sb, tickers)\n'
  '        prev_close_map = fetch_prev_close_map(sb, tickers)\n'
  '        print(f"Live LTP tickers (last {LIVE_TICK_WINDOW_MIN} min): {len(intraday_rows)}; "\n'
  '              f"prior closes: {len(prev_close_map)}")\n'),
 ('            latest_breadth_row=latest_breadth_row,\n        )\n',
  '            latest_breadth_row=latest_breadth_row,\n'
  '            prev_close_map=prev_close_map,\n        )\n'),
]
for o, n in E:
    c = s.count(o)
    assert c == 1, f'anchor count {c}: {o[:60]!r}'
    s = s.replace(o, n)
ast.parse(s)
open(p, 'w').write(s)
print('patched', hashlib.sha256(s.encode()).hexdigest()[:12])
