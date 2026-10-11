CREATE TABLE option_chain_snapshots (id serial, ts timestamptz NOT NULL, symbol text NOT NULL, expiry_date date NOT NULL,
  spot numeric NOT NULL, strike numeric NOT NULL, option_type text NOT NULL, ltp numeric, oi numeric, delta numeric, iv numeric, gamma numeric, volume numeric, run_id uuid);
CREATE INDEX idx_ocs_ts_symbol_expiry ON option_chain_snapshots (ts DESC, symbol, expiry_date);
CREATE INDEX idx_ocs_symbol_expiry_strike_type ON option_chain_snapshots (symbol, expiry_date, strike, option_type);
CREATE TABLE trading_calendar (trade_date date PRIMARY KEY, is_open boolean);
CREATE TABLE market_spot_snapshots (id serial, ts timestamptz, symbol text, spot numeric);
CREATE TABLE data_contamination_ranges (contamination_id text, field_scope text, contamination_start timestamptz, contamination_end timestamptz, affected_tables text[]);
CREATE FUNCTION get_parameter_num(k text) RETURNS numeric LANGUAGE sql AS 'SELECT NULL::numeric';
