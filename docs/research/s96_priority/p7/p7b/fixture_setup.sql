-- p7b fixture additions on a copy of the mp7 fixture (local Postgres only).
CREATE TABLE index_futures_snapshots (id serial, ts timestamptz, symbol text, expiry_date date,
  futures_price numeric, spot_price numeric);
-- futures: every 5 min 09:20..15:40 IST on 2026-10-09, front-month future, r = 6.5 % on the spot of the
-- nearest chain row at or before that minute
INSERT INTO index_futures_snapshots (ts, symbol, expiry_date, futures_price, spot_price)
SELECT t, x.symbol, x.fexp,
       sp * exp(0.065 * extract(epoch from ((x.fexp + time '15:30') at time zone 'Asia/Kolkata') - t) / (365*86400)),
       sp
  FROM (VALUES ('NIFTY', date '2026-10-27'), ('SENSEX', date '2026-10-29')) x(symbol, fexp)
  CROSS JOIN generate_series(timestamptz '2026-10-09 09:20+05:30', timestamptz '2026-10-09 15:40+05:30', interval '5 min') t
  CROSS JOIN LATERAL (SELECT spot AS sp FROM option_chain_snapshots o WHERE o.symbol = x.symbol AND o.ts <= t
                       ORDER BY o.ts DESC LIMIT 1) s;
-- vendor gamma: Black-Scholes gamma at the vendor iv (q = 0, r = 6.5 %); stays NULL where iv is NULL/0
UPDATE option_chain_snapshots o SET gamma = g.gamma
  FROM (SELECT id,
               exp(-0.5 * power(d1, 2)) / sqrt(2 * pi()) / (spot * sig * sqrt(tt)) AS gamma
          FROM (SELECT id, spot::float8 AS spot, (iv / 100.0)::float8 AS sig, tt,
                       (ln(spot::float8 / strike::float8) + (0.065 + 0.5 * power(iv / 100.0, 2)) * tt)
                         / ((iv / 100.0) * sqrt(tt)) AS d1
                  FROM (SELECT id, spot, strike, iv,
                               extract(epoch from ((expiry_date + time '15:30') at time zone 'Asia/Kolkata') - ts)
                                 / (365.0 * 86400) AS tt
                          FROM option_chain_snapshots WHERE iv > 0) q
                 WHERE tt > 0) q2) g
 WHERE g.id = o.id;
-- deep-ITM guard plants at the latest ts: two far strikes per symbol with vendor gamma above 5e-5
UPDATE option_chain_snapshots o SET gamma = 1e-4
 WHERE o.ts = (SELECT max(ts) FROM option_chain_snapshots WHERE symbol = o.symbol)
   AND abs(o.strike - o.spot) / o.spot > 0.06 AND o.oi > 0
   AND o.id IN (SELECT min(id) FROM option_chain_snapshots o2
                 WHERE o2.ts = (SELECT max(ts) FROM option_chain_snapshots WHERE symbol = o2.symbol)
                   AND abs(o2.strike - o2.spot) / o2.spot > 0.06 AND o2.oi > 0
                 GROUP BY o2.symbol, o2.option_type);
