-- =====================================================================================================================
-- sql/2026-10-12_s96_td_s95_new_2_calendar_backfill.sql — TD-S95-NEW-2: closed-day rows for 2026-08-24 → 2026-10-04
-- Ruling S96-J (2026-10-12 06:54 IST): prepared now, applied by the operator AFTER THE CLOSE in the SQL editor.
--
-- WHAT. trading_calendar holds no row for past closed days before the S90 seeder change (82619f8), so 10-02 and the
-- September weekends read as "no row", not closed (TD-S95-NEW-2: S* T(c) unscorable on three NIFTY L3 arms; the P5
-- probe-1 is_open guard never fired). This writes the 14 closed days of the chain-retention window as rows.
--
-- THE 14 DATES, three independent sources, all agreeing (computed 2026-10-12 ~08:15 IST, not recalled):
--   (1) trading_calendar.py get_session_config_for_date() over every day 08-24 → 10-04: 14 closed — 12 'Weekend',
--       2026-09-14 'Ganesh Chaturthi', 2026-10-02 'Mahatma Gandhi Jayanti';
--   (2) trading_calendar.json holidays in the window: the same two;
--   (3) Rule 18 — the published 2026 NSE list (cleartax.in/s/nse-holidays-2026, read 08:16 IST): 09-14 and 10-02 are
--       equity + derivatives trading holidays; no other weekday holiday in the window.
-- SHAPE = the seeder's closed-day path (seed_trading_calendar.py S90_SEED_CLOSED_DAYS): is_open false, open_time NULL,
--   holiday_name = the rule engine's note, ON CONFLICT DO NOTHING (an existing row is never overwritten).
-- Additive; touches no existing row. No live gate reads these dates (they are past).
-- =====================================================================================================================

BEGIN;
INSERT INTO public.trading_calendar (trade_date, is_open, open_time, holiday_name, notes)
VALUES ('2026-08-29', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-08-30', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-09-05', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-09-06', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-09-12', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-09-13', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-09-14', false, NULL, 'Ganesh Chaturthi',       'closed (S96 TD-S95-NEW-2 backfill, NSE holiday)'),
       ('2026-09-19', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-09-20', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-09-26', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-09-27', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-10-02', false, NULL, 'Mahatma Gandhi Jayanti', 'closed (S96 TD-S95-NEW-2 backfill, NSE holiday)'),
       ('2026-10-03', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)'),
       ('2026-10-04', false, NULL, 'Weekend',                'closed (S96 TD-S95-NEW-2 backfill, Weekend)')
ON CONFLICT (trade_date) DO NOTHING;
COMMIT;

-- VERIFICATION (last result shown). PASS = exactly one row:
--   closed_dates_with_row 14 | closed_dates_marked_closed 14 | closed_dates_marked_open 0 | weekday_open_rows <W>
--   where <W> is unchanged from the pre-check (this batch writes no open row).
WITH d AS (
    SELECT x::date AS trade_date FROM unnest(ARRAY['2026-08-29','2026-08-30','2026-09-05','2026-09-06','2026-09-12',
      '2026-09-13','2026-09-14','2026-09-19','2026-09-20','2026-09-26','2026-09-27','2026-10-02','2026-10-03',
      '2026-10-04']) AS x)
SELECT current_user                                                         AS role_now,
       count(t.trade_date)                                                  AS closed_dates_with_row,
       count(*) FILTER (WHERE t.is_open = false)                            AS closed_dates_marked_closed,
       count(*) FILTER (WHERE t.is_open = true)                             AS closed_dates_marked_open,
       (SELECT count(*) FROM public.trading_calendar
         WHERE trade_date BETWEEN '2026-08-24' AND '2026-10-04' AND is_open) AS weekday_open_rows
FROM d LEFT JOIN public.trading_calendar t USING (trade_date);
