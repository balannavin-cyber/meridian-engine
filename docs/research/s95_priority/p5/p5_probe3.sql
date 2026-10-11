-- S95 check owed (TD-S91-NEW-13, R0.8): trading_calendar for the next two weeks.
SELECT trade_date, to_char(trade_date, 'Dy') AS dow, is_open, open_time, holiday_name, notes
  FROM trading_calendar
 WHERE trade_date BETWEEN DATE '2026-10-12' AND DATE '2026-10-23'
 ORDER BY trade_date;
