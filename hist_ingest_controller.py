"""
hist_ingest_controller.py
=========================
MERDIAN — Historical Vendor Data Ingest Controller

Walks a vendor delivery directory (year/month/day structure) and ingests
1-minute OHLCV CSV files into the Supabase hot tier and a local Parquet
warm tier.

Usage:
    python hist_ingest_controller.py --root "D:\\vendor_drop" --dry-run
    python hist_ingest_controller.py --root "D:\\vendor_drop"
    python hist_ingest_controller.py --root "D:\\vendor_drop" --date 2024-03-15
    python hist_ingest_controller.py --root "D:\\vendor_drop" --year 2024

Architecture:
    Vendor CSV → parser_validator → segment_router → bar_loader (Supabase)
                                                   → parquet_archiver (local)
                                 → ingest_rejects  → Supabase
    On completion → completeness_checker → Supabase
    On completion → raw file logged in hist_ingest_log → Supabase

S3 Integration:
    Not yet active. parquet_archiver writes to local warm_tier_path.
    When S3 is ready, swap LocalParquetArchiver for S3ParquetArchiver —
    interface is identical, controller code does not change.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import shutil
import tempfile
import zipfile
from typing import Any, Iterator

import pandas as pd

from core.config import get_settings
from core.supabase_client import SupabaseClient

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(get_settings().logs_dir) / "hist_ingest.log",
            encoding="utf-8"
        ),
    ],
)
log = logging.getLogger("hist_ingest")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum rows per Supabase upsert call — reduced from 1000 to avoid timeouts
UPSERT_BATCH_SIZE = 500

# Expected bars in a full session: 09:15 to 15:29 inclusive = 375 minutes
EXPECTED_BARS_FULL_SESSION = 375

# Expiry horizon in days — contracts beyond this are flagged as LEAP
LEAP_HORIZON_DAYS = 90

# Pre-market cutoff
PRE_MARKET_CUTOFF = "09:15:00"

# Filename prefix → segment mapping
# Must match the check constraint on hist_ingest_log.segment:
#   OPTIONS, FUTURES, SPOT, MIXED, OPTIONS_FUTURES_NSE,
#   OPTIONS_FUTURES_BSE, SPOT_NSE, SPOT_BSE
SEGMENT_MAP = {
    "GFDLNFO":  "OPTIONS_FUTURES_NSE",   # NSE options + continuous futures
    "GFDLCM":   "SPOT_NSE",              # NSE cash / spot index
    "GFDLBFO":  "OPTIONS_FUTURES_BSE",   # BSE options + continuous futures
    "GFDLBM":   "SPOT_BSE",              # BSE cash / spot index
    "BFO":      "OPTIONS_FUTURES_BSE",   # SENSEX contractwise F&O
    "BSE":      "SPOT_BSE",              # BSE spot indices (BSE_INDICES_*)
}

# Tickers that are continuous futures series, not options
FUTURES_PATTERN = re.compile(r"^(NIFTY|SENSEX|BANKNIFTY)-(I{1,3})\.(NFO|BFO)$")

# Individual dated futures contracts: SENSEX08APR25FUT.BFO
INDIVIDUAL_FUTURES_PATTERN = re.compile(
    r"^(?P<symbol>[A-Z]+)(?P<day>\d{2})(?P<month>[A-Z]{3})(?P<year>\d{2})FUT\.(?P<exchange>NFO|BFO)$"
)

# Options ticker pattern: NIFTY03JUL2522800CE.NFO
OPTIONS_PATTERN = re.compile(
    r"^(?P<symbol>[A-Z]+)(?P<day>\d{2})(?P<month>[A-Z]{3})(?P<year>\d{2})"
    r"(?P<strike>\d+)(?P<opt_type>CE|PE)\.(?P<exchange>NFO|BFO)$"
)

# Spot ticker pattern: NIFTY 50.NSE_IDX, SENSEX.BSE_IDX
SPOT_PATTERN = re.compile(r"^.+\.(NSE_IDX|BSE_IDX)$")

MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParsedTicker:
    raw: str
    kind: str           # OPTIONS | FUTURES | SPOT
    symbol: str         # NIFTY, SENSEX
    exchange: str       # NFO, BFO, NSE_IDX, BSE_IDX
    expiry_date: date | None = None
    strike: float | None = None
    opt_type: str | None = None
    contract_series: int | None = None


@dataclass
class IngestResult:
    batch_id: str
    filename: str
    vendor_date: date
    segment: str
    rows_received: int = 0
    rows_accepted: int = 0
    rows_rejected: int = 0
    rows_pre_market: int = 0
    rows_leap_flagged: int = 0
    rejects: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    status: str = "IN_PROGRESS"
    parquet_path: str | None = None


# ---------------------------------------------------------------------------
# Ticker parser
# ---------------------------------------------------------------------------

def parse_ticker(raw: str) -> ParsedTicker | None:
    """
    Parse a vendor ticker string into a structured ParsedTicker.
    Returns None if the ticker does not match any known pattern.
    """
    # Continuous futures: NIFTY-I.NFO, NIFTY-II.NFO, NIFTY-III.NFO
    m = FUTURES_PATTERN.match(raw)
    if m:
        series_map = {"I": 1, "II": 2, "III": 3}
        return ParsedTicker(
            raw=raw,
            kind="FUTURES",
            symbol=m.group(1),
            exchange=m.group(3),
            contract_series=series_map.get(m.group(2), 1),
        )

    # Individual dated futures: SENSEX08APR25FUT.BFO
    # contract_series=0 distinguishes from continuous series (1/2/3)
    m = INDIVIDUAL_FUTURES_PATTERN.match(raw)
    if m:
        try:
            expiry = date(
                2000 + int(m.group("year")),
                MONTH_MAP[m.group("month")],
                int(m.group("day")),
            )
        except (KeyError, ValueError):
            return None
        return ParsedTicker(
            raw=raw,
            kind="FUTURES",
            symbol=m.group("symbol"),
            exchange=m.group("exchange"),
            expiry_date=expiry,
            contract_series=0,
        )

    # Options: NIFTY03JUL2522800CE.NFO
    m = OPTIONS_PATTERN.match(raw)
    if m:
        try:
            expiry = date(
                2000 + int(m.group("year")),
                MONTH_MAP[m.group("month")],
                int(m.group("day")),
            )
        except (KeyError, ValueError):
            return None
        return ParsedTicker(
            raw=raw,
            kind="OPTIONS",
            symbol=m.group("symbol"),
            exchange=m.group("exchange"),
            expiry_date=expiry,
            strike=float(m.group("strike")),
            opt_type=m.group("opt_type"),
        )

    # Spot index: NIFTY 50.NSE_IDX, SENSEX.BSE_IDX
    m = SPOT_PATTERN.match(raw)
    if m:
        exchange = raw.split(".")[-1]
        symbol = "NIFTY" if "NIFTY" in raw.upper() else "SENSEX"
        return ParsedTicker(raw=raw, kind="SPOT", symbol=symbol, exchange=exchange)

    return None


# ---------------------------------------------------------------------------
# Parser / Validator
# ---------------------------------------------------------------------------

def parse_and_validate(
    df: pd.DataFrame,
    trade_date: date,
    batch_id: str,
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Validate all rows in a raw vendor DataFrame.
    Returns (accepted_df, rejects_list).
    Rejects include row number, ticker, and reason.
    """
    accepted_rows = []
    rejects = []

    for i, row in df.iterrows():
        reason = None

        # OHLC integrity
        try:
            o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
        except (ValueError, TypeError):
            reason = "OHLC_PARSE_ERROR"

        if reason is None:
            if h < l:
                reason = "HIGH_LT_LOW"
            elif c > h or c < l:
                reason = "CLOSE_OUTSIDE_RANGE"
            elif o > h or o < l:
                reason = "OPEN_OUTSIDE_RANGE"

        # Ticker parseable
        if reason is None:
            ticker = str(row.get("Ticker", ""))
            parsed = parse_ticker(ticker)
            if parsed is None:
                reason = "UNPARSEABLE_TICKER"

        # Volume and OI non-negative
        if reason is None:
            try:
                vol = int(row["Volume"])
                oi = int(row["Open Interest"])
                if vol < 0 or oi < 0:
                    reason = "NEGATIVE_VOLUME_OI"
            except (ValueError, TypeError):
                reason = "VOLUME_OI_PARSE_ERROR"

        if reason:
            rejects.append({
                "id": str(uuid.uuid4()),
                "batch_id": batch_id,
                "source_row_number": int(i) + 2,
                "raw_ticker": str(row.get("Ticker", "")),
                "raw_date": str(row.get("Date", "")),
                "raw_time": str(row.get("Time", "")),
                "reject_reason": reason,
                "raw_row": ",".join(str(v) for v in row.values),
            })
        else:
            accepted_rows.append(row)

    accepted_df = pd.DataFrame(accepted_rows) if accepted_rows else pd.DataFrame(columns=df.columns)
    return accepted_df, rejects


# ---------------------------------------------------------------------------
# Segment router
# ---------------------------------------------------------------------------

def route_segments(
    df: pd.DataFrame,
    trade_date: date,
    batch_id: str,
) -> dict[str, pd.DataFrame]:
    """
    Split a validated DataFrame into options, futures, and spot segments.
    Applies pre-market flag and LEAP flag.
    Returns dict with keys: 'options', 'futures', 'spot'.
    """
    segments: dict[str, list[dict]] = {"options": [], "futures": [], "spot": []}

    for _, row in df.iterrows():
        ticker = str(row["Ticker"])
        parsed = parse_ticker(ticker)
        if parsed is None:
            continue

        # Parse timestamp
        try:
            bar_ts = datetime.strptime(
                f"{row['Date']} {row['Time']}",
                "%d/%m/%Y %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        is_pre_market = row["Time"] < PRE_MARKET_CUTOFF
        base = {
            "id": str(uuid.uuid4()),
            "ingest_batch_id": batch_id,
            "trade_date": trade_date.isoformat(),
            "bar_ts": bar_ts.isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "is_pre_market": is_pre_market,
        }

        if parsed.kind == "SPOT":
            segments["spot"].append({**base})

        elif parsed.kind == "FUTURES":
            segments["futures"].append({
                **base,
                "expiry_date": parsed.expiry_date.isoformat() if parsed.expiry_date else None,
                "contract_series": parsed.contract_series if parsed.contract_series is not None else 0,
                "volume": int(row["Volume"]),
                "oi": int(row["Open Interest"]),
            })

        elif parsed.kind == "OPTIONS":
            is_leap = False
            if parsed.expiry_date:
                days_to_expiry = (parsed.expiry_date - trade_date).days
                is_leap = days_to_expiry > LEAP_HORIZON_DAYS

            segments["options"].append({
                **base,
                "expiry_date": parsed.expiry_date.isoformat() if parsed.expiry_date else None,
                "strike": parsed.strike,
                "option_type": parsed.opt_type,
                "volume": int(row["Volume"]),
                "oi": int(row["Open Interest"]),
                "is_leap": is_leap,
            })

    return {k: pd.DataFrame(v) for k, v in segments.items()}


# ---------------------------------------------------------------------------
# Instrument ID resolver
# ---------------------------------------------------------------------------

class InstrumentResolver:
    """
    Resolves symbol → instrument UUID from the existing instruments table.
    Caches results to avoid repeated Supabase calls.
    """

    def __init__(self, client: SupabaseClient):
        self.client = client
        self._cache: dict[str, str] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        rows = self.client.select("instruments", columns="id,symbol,exchange")
        for row in rows:
            key = f"{row['symbol']}|{row['exchange']}"
            self._cache[key] = row["id"]
        log.info(f"InstrumentResolver loaded {len(self._cache)} instruments")

    def resolve(self, symbol: str, exchange: str) -> str | None:
        return self._cache.get(f"{symbol}|{exchange}")


# ---------------------------------------------------------------------------
# Parquet archiver (local — S3 ready interface)
# ---------------------------------------------------------------------------

class LocalParquetArchiver:
    """
    Writes DataFrames to local Parquet warm tier.
    Partitioned as: warm_root/table/year=YYYY/month=MM/day=DD/data.parquet

    S3 upgrade path:
        Replace with S3ParquetArchiver(bucket, prefix) — same write() interface.
        Controller code is unchanged.
    """

    def __init__(self, warm_root: Path):
        self.warm_root = warm_root

    def write(self, table: str, df: pd.DataFrame, trade_date: date) -> str:
        if df.empty:
            return ""

        partition = (
            self.warm_root
            / table
            / f"year={trade_date.year}"
            / f"month={trade_date.month:02d}"
            / f"day={trade_date.day:02d}"
        )
        partition.mkdir(parents=True, exist_ok=True)
        path = partition / "data.parquet"
        df.to_parquet(path, index=False, engine="pyarrow", compression="snappy")
        log.info(f"Parquet written → {path} ({len(df)} rows)")
        return str(path)


# ---------------------------------------------------------------------------
# Bar loader — Supabase upsert in batches
# ---------------------------------------------------------------------------

def upsert_batched(
    client: SupabaseClient,
    table: str,
    rows: list[dict],
    on_conflict: str,
    batch_size: int = UPSERT_BATCH_SIZE,
) -> int:
    """
    Upsert rows into Supabase in chunks of batch_size.
    Retry logic for transient network errors is handled in SupabaseClient._request.
    Returns total rows upserted.
    """
    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        client.upsert(table, chunk, on_conflict=on_conflict)
        total += len(chunk)
        log.debug(f"  Upserted {total}/{len(rows)} rows to {table}")
    return total


# ---------------------------------------------------------------------------
# Completeness checker
# ---------------------------------------------------------------------------

def run_completeness_check(
    client: SupabaseClient,
    batch_id: str,
    instrument_id: str,
    trade_date: date,
    expiry_date: date | None,
    actual_bars: int,
) -> None:
    expected = EXPECTED_BARS_FULL_SESSION
    flag = actual_bars < (expected * 0.80)

    client.insert("hist_completeness_checks", {
        "id": str(uuid.uuid4()),
        "batch_id": batch_id,
        "instrument_id": instrument_id,
        "trade_date": trade_date.isoformat(),
        "expiry_date": expiry_date.isoformat() if expiry_date else None,
        "expected_bars": expected,
        "actual_bars": actual_bars,
        "flag_incomplete": flag,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    })

    if flag:
        log.warning(
            f"Completeness flag: {actual_bars}/{expected} bars "
            f"({100*actual_bars//expected}%) on {trade_date} "
            f"expiry={expiry_date}"
        )


# ---------------------------------------------------------------------------
# File checksum
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Directory walker
# ---------------------------------------------------------------------------

def walk_vendor_directory(
    root: Path,
    filter_date: date | None = None,
    filter_year: int | None = None,
) -> Iterator[tuple[date, Path]]:
    """
    Walk vendor delivery structure:
      <root>/<year>/<MONTH_YEAR>.zip -> <MONTH_YEAR>/<prefix>_DDMMYYYY.csv

    Extracts each ZIP to a temp directory, yields (trade_date, csv_path),
    then cleans up the temp directory after all files in that ZIP are yielded.
    Applies optional date or year filter.
    """
    for year_dir in sorted(root.iterdir()):
        if not year_dir.is_dir():
            continue
        try:
            year = int(year_dir.name)
        except ValueError:
            continue

        if filter_year and year != filter_year:
            continue

        for zip_path in sorted(year_dir.glob("*.zip")):
            tmp_dir = Path(tempfile.mkdtemp(prefix="meridian_hist_"))
            try:
                log.info(f"Extracting: {zip_path.name}")
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(tmp_dir)

                zip_stem = zip_path.stem
                inner_dir = tmp_dir / zip_stem

                search_dir = inner_dir if inner_dir.is_dir() else tmp_dir

                for csv_file in sorted(search_dir.glob("*.csv")):
                    trade_date = _parse_date_from_filename(csv_file.name)
                    if trade_date is None:
                        log.warning(f"Cannot parse trade date from filename: {csv_file.name}")
                        continue
                    if filter_date and trade_date != filter_date:
                        continue
                    yield trade_date, csv_file

            except zipfile.BadZipFile as exc:
                log.error(f"Bad ZIP file: {zip_path} -- {exc}")
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)


def _parse_date_from_filename(filename: str) -> date | None:
    """
    Extract trade date from vendor filename.
    Handles:
      GFDLNFO_BACKADJUSTED_DDMMYYYY.csv  (NSE F&O backadjusted)
      GFDLCM_NIFTY 50_DDMMYYYY.csv       (NSE spot)
      BFO_CONTRACT_DDMMYYYY.csv           (BSE F&O contractwise)
      BSE_INDICES_DDMMYYYY.csv            (BSE spot)
    Last underscore-separated token before extension is always DDMMYYYY.
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    date_token = parts[-1]

    if len(date_token) == 8 and date_token.isdigit():
        try:
            return date(
                int(date_token[4:8]),
                int(date_token[2:4]),
                int(date_token[0:2]),
            )
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# Core: process one CSV file
# ---------------------------------------------------------------------------

def process_file(
    csv_path: Path,
    trade_date: date,
    client: SupabaseClient,
    resolver: InstrumentResolver,
    archiver: LocalParquetArchiver,
    dry_run: bool = False,
) -> IngestResult:
    """
    Full pipeline for one vendor CSV file:
      1. Checksum + deduplication check
      2. Parse + validate rows
      3. Route segments
      4. Upsert to Supabase (batched)
      5. Write Parquet (warm tier)
      6. Completeness checks
      7. Update hist_ingest_log
    """
    filename = csv_path.name
    batch_id = str(uuid.uuid4())

    prefix = filename.split("_")[0]
    segment = SEGMENT_MAP.get(prefix, "SPOT_BSE")

    result = IngestResult(
        batch_id=batch_id,
        filename=filename,
        vendor_date=trade_date,
        segment=segment,
    )

    log.info(f"Processing: {csv_path} | batch={batch_id}")

    # ------------------------------------------------------------------
    # Step 1: Checksum + deduplication
    # ------------------------------------------------------------------
    checksum = sha256_file(csv_path)

    if not dry_run:
        existing = client.select(
            "hist_ingest_log",
            columns="id,status",
            filters={"source_checksum": checksum},
        )
        if existing:
            log.warning(f"SKIP — already ingested: {filename} (checksum match, status={existing[0]['status']})")
            result.status = "SKIPPED_DUPLICATE"
            return result

        client.insert("hist_ingest_log", {
            "id": batch_id,
            "source_filename": filename,
            "source_checksum": checksum,
            "vendor_date": trade_date.isoformat(),
            "segment": segment,
            "rows_received": 0,
            "rows_accepted": 0,
            "rows_rejected": 0,
            "status": "IN_PROGRESS",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

    # ------------------------------------------------------------------
    # Step 2: Load CSV
    # ------------------------------------------------------------------
    try:
        df_raw = pd.read_csv(csv_path)
    except Exception as exc:
        result.status = "FAILED"
        result.errors.append(f"CSV read error: {exc}")
        log.error(f"CSV read failed: {csv_path} — {exc}")
        _update_ingest_log(client, batch_id, result, dry_run, checksum)
        return result

    result.rows_received = len(df_raw)
    log.info(f"  Rows received: {result.rows_received}")

    # ------------------------------------------------------------------
    # Step 3: Parse + validate
    # ------------------------------------------------------------------
    df_valid, rejects = parse_and_validate(df_raw, trade_date, batch_id)
    result.rows_rejected = len(rejects)
    result.rejects = rejects
    result.rows_accepted = len(df_valid)

    log.info(f"  Accepted: {result.rows_accepted} | Rejected: {result.rows_rejected}")

    if rejects and not dry_run:
        upsert_batched(client, "hist_ingest_rejects", rejects,
                       on_conflict="id", batch_size=500)

    if df_valid.empty:
        result.status = "FAILED"
        result.errors.append("No valid rows after validation")
        _update_ingest_log(client, batch_id, result, dry_run, checksum)
        return result

    # ------------------------------------------------------------------
    # Step 4: Route segments
    # ------------------------------------------------------------------
    segments = route_segments(df_valid, trade_date, batch_id)

    options_df = segments["options"]
    futures_df = segments["futures"]
    spot_df    = segments["spot"]

    if not options_df.empty:
        result.rows_pre_market += options_df["is_pre_market"].sum()
        result.rows_leap_flagged += options_df["is_leap"].sum()

    if not spot_df.empty:
        result.rows_pre_market += spot_df["is_pre_market"].sum()

    log.info(
        f"  Segments — options: {len(options_df)} | "
        f"futures: {len(futures_df)} | spot: {len(spot_df)} | "
        f"pre-market: {result.rows_pre_market} | LEAPs: {result.rows_leap_flagged}"
    )

    if dry_run:
        log.info(f"  DRY RUN — skipping Supabase writes and Parquet output")
        result.status = "DRY_RUN"
        return result

    # ------------------------------------------------------------------
    # Step 5: Resolve instrument IDs and upsert to Supabase
    # ------------------------------------------------------------------

    # Options
    if not options_df.empty:
        nifty_id = resolver.resolve("NIFTY", "NSE")
        sensex_id = resolver.resolve("SENSEX", "BSE")
        inst_id = nifty_id if "NSE" in segment else sensex_id
        if inst_id:
            options_rows = options_df.copy()
            options_rows["instrument_id"] = inst_id
            upsert_batched(
                client,
                "hist_option_bars_1m",
                options_rows.to_dict("records"),
                on_conflict="instrument_id,bar_ts,expiry_date,strike,option_type",
            )
        else:
            log.warning("Could not resolve instrument_id for options — check instruments table")

    # Futures — conflict key includes expiry_date to handle both continuous
    # series (expiry_date=NULL, contract_series=1/2/3) and individual dated
    # contracts (expiry_date=YYYY-MM-DD, contract_series=0)
    if not futures_df.empty:
        inst_id = resolver.resolve("NIFTY", "NSE") if "NSE" in segment else resolver.resolve("SENSEX", "BSE")
        if inst_id:
            futures_rows = futures_df.copy()
            futures_rows["instrument_id"] = inst_id
            upsert_batched(
                client,
                "hist_future_bars_1m",
                futures_rows.to_dict("records"),
                on_conflict="instrument_id,bar_ts,contract_series,expiry_date",
            )

    # Spot
    if not spot_df.empty:
        inst_id = resolver.resolve("NIFTY", "NSE") if "NSE" in segment else resolver.resolve("SENSEX", "BSE")
        if inst_id:
            spot_rows = spot_df.copy()
            spot_rows["instrument_id"] = inst_id
            upsert_batched(
                client,
                "hist_spot_bars_1m",
                spot_rows.to_dict("records"),
                on_conflict="instrument_id,bar_ts",
            )

    # ------------------------------------------------------------------
    # Step 6: Parquet warm tier
    # ------------------------------------------------------------------
    parquet_paths = []
    for table, df in [
        ("hist_option_bars_1m", options_df),
        ("hist_future_bars_1m", futures_df),
        ("hist_spot_bars_1m",   spot_df),
    ]:
        if not df.empty:
            p = archiver.write(table, df, trade_date)
            if p:
                parquet_paths.append(p)

    result.parquet_path = "|".join(parquet_paths) if parquet_paths else None

    # ------------------------------------------------------------------
    # Step 7: Completeness checks (per active expiry, non-LEAP only)
    # ------------------------------------------------------------------
    if not options_df.empty:
        inst_id = resolver.resolve("NIFTY", "NSE") if "NSE" in segment else resolver.resolve("SENSEX", "BSE")
        if inst_id:
            active = options_df[~options_df["is_leap"] & ~options_df["is_pre_market"]]
            for expiry_str, grp in active.groupby("expiry_date"):
                try:
                    expiry_date = date.fromisoformat(str(expiry_str))
                except ValueError:
                    continue
                unique_ts = grp["bar_ts"].nunique()
                run_completeness_check(
                    client, batch_id, inst_id,
                    trade_date, expiry_date, unique_ts
                )

    # ------------------------------------------------------------------
    # Step 8: Finalise ingest log
    # ------------------------------------------------------------------
    result.status = "BARS_LOADED"
    _update_ingest_log(client, batch_id, result, dry_run, checksum)

    log.info(f"  Completed: {filename} | status={result.status}")
    return result


# ---------------------------------------------------------------------------
# Ingest log updater
# ---------------------------------------------------------------------------

def _update_ingest_log(
    client: SupabaseClient,
    batch_id: str,
    result: IngestResult,
    dry_run: bool,
    checksum: str = "",
) -> None:
    if dry_run:
        return
    try:
        client.upsert(
            "hist_ingest_log",
            {
                "id": batch_id,
                "source_filename": result.filename,
                "source_checksum": checksum,
                "vendor_date": result.vendor_date.isoformat(),
                "segment": result.segment,
                "rows_received": int(result.rows_received),
                "rows_accepted": int(result.rows_accepted),
                "rows_rejected": int(result.rows_rejected),
                "rows_pre_market": int(result.rows_pre_market),
                "rows_leap_flagged": int(result.rows_leap_flagged),
                "parquet_path": result.parquet_path,
                "status": result.status,
                "error_detail": "; ".join(result.errors) if result.errors else None,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="id",
        )
    except Exception as exc:
        log.error(f"Failed to update hist_ingest_log for batch {batch_id}: {exc}")


# ---------------------------------------------------------------------------
# Summary reporter
# ---------------------------------------------------------------------------

def print_summary(results: list[IngestResult]) -> None:
    total_files    = len(results)
    total_received = sum(r.rows_received for r in results)
    total_accepted = sum(r.rows_accepted for r in results)
    total_rejected = sum(r.rows_rejected for r in results)
    total_leaps    = sum(r.rows_leap_flagged for r in results)
    failed         = [r for r in results if r.status in ("FAILED", "PARTIAL")]
    skipped        = [r for r in results if r.status == "SKIPPED_DUPLICATE"]

    log.info("=" * 60)
    log.info("INGEST SUMMARY")
    log.info(f"  Files processed : {total_files}")
    log.info(f"  Rows received   : {total_received:,}")
    log.info(f"  Rows accepted   : {total_accepted:,}")
    log.info(f"  Rows rejected   : {total_rejected:,}")
    log.info(f"  LEAPs flagged   : {total_leaps:,}")
    log.info(f"  Files failed    : {len(failed)}")
    log.info(f"  Files skipped   : {len(skipped)}")

    if failed:
        log.warning("FAILED FILES:")
        for r in failed:
            log.warning(f"  {r.filename}: {'; '.join(r.errors)}")
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MERDIAN historical vendor data ingest controller"
    )
    parser.add_argument(
        "--root", required=True,
        help="Root of vendor delivery directory (e.g. D:\\vendor_drop)"
    )
    parser.add_argument(
        "--warm-tier", default=None,
        help="Local warm tier Parquet root (default: <base_dir>/warm_tier)"
    )
    parser.add_argument(
        "--date", default=None,
        help="Process only this date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--year", type=int, default=None,
        help="Process only this year"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and validate only — no Supabase writes, no Parquet output"
    )
    args = parser.parse_args()

    settings = get_settings()

    root = Path(args.root)
    if not root.exists():
        log.error(f"Vendor root does not exist: {root}")
        sys.exit(1)

    warm_root = Path(args.warm_tier) if args.warm_tier else settings.data_dir / "warm_tier"
    warm_root.mkdir(parents=True, exist_ok=True)

    filter_date = date.fromisoformat(args.date) if args.date else None

    client   = SupabaseClient()
    resolver = InstrumentResolver(client)
    archiver = LocalParquetArchiver(warm_root)

    results: list[IngestResult] = []

    for trade_date, csv_path in walk_vendor_directory(root, filter_date, args.year):
        try:
            result = process_file(
                csv_path=csv_path,
                trade_date=trade_date,
                client=client,
                resolver=resolver,
                archiver=archiver,
                dry_run=args.dry_run,
            )
            results.append(result)
        except Exception as exc:
            log.error(f"Unhandled error on {csv_path}: {exc}", exc_info=True)
            results.append(IngestResult(
                batch_id=str(uuid.uuid4()),
                filename=csv_path.name,
                vendor_date=trade_date,
                segment="UNKNOWN",
                status="FAILED",
                errors=[str(exc)],
            ))

    print_summary(results)


if __name__ == "__main__":
    main()
