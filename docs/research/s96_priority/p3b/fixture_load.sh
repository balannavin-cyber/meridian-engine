#!/usr/bin/env bash
# P3b fixture DB: the six golden days into local Postgres 16, under the live table names. Not for live.
set -euo pipefail
G=${1:-/mnt/user-data/uploads/GammaEnginePython/tests/golden}
PSQL="su postgres -c"
$PSQL "dropdb --if-exists p3b; createdb p3b"
q(){ su postgres -c "psql -v ON_ERROR_STOP=1 -q -d p3b" ; }
hdr(){ python3 -c "import gzip,sys; print(gzip.open(sys.argv[1],'rt').readline().rstrip())" "$1"; }
gm_cols=$(hdr "$G/2026-10-01_SENSEX/inputs/gamma_metrics.csv.gz"); gs_cols=$(hdr "$G/2026-10-01_SENSEX/inputs/gex_strike.csv.gz"); oc_cols=$(hdr "$G/2026-10-01_SENSEX/inputs/ocs.csv.gz")
mk(){ echo "CREATE TABLE $1 ($(echo "$2" | sed 's/,/ text, /g') text);"; }
{ mk stg_gm "$gm_cols"; mk stg_gs "$gs_cols"; mk stg_oc "$oc_cols"; } | q
for d in "$G"/*/; do
  for p in "gm gamma_metrics" "gs gex_strike" "oc ocs"; do set -- $p
    f="$d/inputs/$2.csv.gz"; [ "$(hdr "$f")" = "$(eval echo \"\$${1}_cols\")" ] || { echo "HEADER MISMATCH $f"; exit 1; }
    zcat "$f" > /tmp/p3b_load.csv; chmod 644 /tmp/p3b_load.csv
    echo "\\copy stg_$1 FROM '/tmp/p3b_load.csv' CSV HEADER" | q
  done
done
cat <<'SQL' | q
CREATE TABLE gamma_metrics AS SELECT symbol, expiry_date::date, run_id, ts::timestamptz, net_gex::float8,
  NULLIF(gamma_concentration,'')::float8 gamma_concentration, NULLIF(flip_level,'')::float8 flip_level FROM stg_gm;
CREATE TABLE gex_strike_snapshots AS SELECT symbol, expiry_date::date, run_id, ts::timestamptz, strike::numeric,
  spot::float8, oi_call::numeric, oi_put::numeric, gex_cr::float8 FROM stg_gs;
CREATE TABLE option_chain_snapshots AS SELECT symbol, expiry_date::date, run_id, ts::timestamptz, strike::numeric,
  option_type, NULLIF(gamma,'')::float8 gamma, NULLIF(oi,'')::numeric oi, NULLIF(bid,'')::float8 bid,
  NULLIF(ask,'')::float8 ask, NULLIF(spot,'')::float8 spot FROM stg_oc;
CREATE INDEX ON gex_strike_snapshots (ts); CREATE INDEX ON option_chain_snapshots (run_id, expiry_date, symbol);
DROP TABLE stg_gm, stg_gs, stg_oc;
SELECT 'gm' t, count(*) FROM gamma_metrics UNION ALL SELECT 'gs', count(*) FROM gex_strike_snapshots
UNION ALL SELECT 'oc', count(*) FROM option_chain_snapshots;
SQL
