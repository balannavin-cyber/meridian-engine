-- S90 R01-F5 belt — write the two remaining 2026 weekday holidays as CLOSED rows.
-- SQL editor, postgres, ONE execution. Additive; touches no existing row.
--
-- WHY. P4 (2026-10-05) shows no trading_calendar row for Tue 2026-10-20.
-- ingest_option_chain_local.py:293-327 and capture_spot_1m_v2.py:265-290 read
-- NO ROW as open, so 10-20 would repeat 10-02 (79,680 chain rows at one frozen
-- spot). Both read an is_open=false row as closed. seed_trading_calendar.py
-- upserts OPEN days only, so it will not overwrite these rows.
-- Dates from trading_calendar.json (R0.1 §7): 10-20 Dussehra, 11-10
-- Diwali-Balipratipada. 11-08 (Sun) Muhurat is a SESSION and is not touched.
-- merdian_start.py:66-70 already treats a pre-loaded is_open=false row as a holiday
-- and preserves it (the established pattern).
-- Proper fix stays R0.8: route both inline gates through core/trading_calendar_gate.py.

BEGIN;
INSERT INTO public.trading_calendar (trade_date, is_open, open_time, holiday_name, notes)
VALUES ('2026-10-20', false, NULL, 'Dussehra', 'Holiday (S90 belt, R01-F5)'),
       ('2026-11-10', false, NULL, 'Diwali-Balipratipada', 'Holiday (S90 belt, R01-F5)')
ON CONFLICT (trade_date) DO NOTHING;
COMMIT;

-- Evidence (last result shown): expect both rows is_open=false.
SELECT current_user AS role_now, trade_date, is_open, open_time, holiday_name, notes
FROM public.trading_calendar
WHERE trade_date IN ('2026-10-20','2026-11-10','2026-11-08')
ORDER BY trade_date;
