"""Local MCX Bhavcopy CSV Importer for GOLD-X.

Reads local MCX CSV files, extracts and validates supported gold contracts,
idempotently upserts into `daily_bhavcopy`, normalizes prices with valid closes,
and idempotently upserts into `normalized_prices`.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Union

import polars as pl
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DailyBhavcopy, NormalizedPrices
from app.db.session import async_session_maker
from app.ingestion.normalizer import normalize_dataframe
from app.ingestion.validator import (
    clean_symbol,
    is_gold_contract,
    parse_expiry_date,
    parse_trade_date,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportSummary:
    """Summary of local CSV ingestion process."""
    file_path: str = ""
    status: str = "ok"
    total_rows_read: int = 0
    gold_rows_found: int = 0
    daily_bhavcopy_upserted: int = 0
    normalized_prices_upserted: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    errors: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    trade_dates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchImportSummary:
    """Summary of batch CSV ingestion process across multiple files."""
    status: str = "ok"
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_rows_read: int = 0
    gold_rows_found: int = 0
    daily_bhavcopy_upserted: int = 0
    normalized_prices_upserted: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    trade_dates: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    file_summaries: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    val_str = str(val).strip().replace(",", "")
    if not val_str:
        return None
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> int:
    f = _safe_float(val)
    if f is None:
        return 0
    try:
        return int(f)
    except (ValueError, TypeError):
        return 0


def parse_and_validate_csv_rows(
    reader: csv.DictReader,
) -> tuple[list[dict[str, Any]], int, int, int, list[str]]:
    """Parse CSV rows from a DictReader, filtering and validating gold contracts.

    Returns:
        (valid_gold_records, total_rows_read, gold_rows_found, error_rows, error_messages)
    """
    total_rows = 0
    gold_rows = 0
    error_rows = 0
    errors: list[str] = []
    valid_records: list[dict[str, Any]] = []

    # Build case-insensitive header mapping
    field_map: dict[str, str] = {}
    if reader.fieldnames:
        for f in reader.fieldnames:
            if f:
                field_map[f.strip().lower()] = f

    def get_field(row_dict: dict, *names: str) -> str:
        for name in names:
            actual = field_map.get(name.lower())
            if actual and actual in row_dict:
                val = row_dict[actual]
                if val is not None:
                    return str(val).strip()
        return ""

    for line_num, row in enumerate(reader, start=2):
        total_rows += 1

        raw_sym = get_field(row, "Symbol", "symbol")
        sym = clean_symbol(raw_sym)
        if not is_gold_contract(sym):
            continue

        gold_rows += 1

        raw_trade_date = get_field(row, "Date", "trade_date", "trade date")
        if not raw_trade_date:
            error_rows += 1
            errors.append(f"Row {line_num} ({sym}): Missing trade date")
            continue

        try:
            trade_dt = parse_trade_date(raw_trade_date)
        except Exception as e:
            error_rows += 1
            errors.append(f"Row {line_num} ({sym}): Invalid trade date '{raw_trade_date}': {e}")
            continue

        raw_expiry = get_field(row, "ExpiryDate", "expiry_date", "expiry date")
        if not raw_expiry:
            error_rows += 1
            errors.append(f"Row {line_num} ({sym}): Missing expiry date")
            continue

        try:
            expiry_dt = parse_expiry_date(raw_expiry)
        except Exception as e:
            error_rows += 1
            errors.append(f"Row {line_num} ({sym}): Invalid expiry date '{raw_expiry}': {e}")
            continue

        open_val = _safe_float(get_field(row, "Open", "open"))
        high_val = _safe_float(get_field(row, "High", "high"))
        low_val = _safe_float(get_field(row, "Low", "low"))
        close_val = _safe_float(get_field(row, "Close", "close"))
        volume_val = _safe_int(get_field(row, "Volume", "volume"))
        oi_val = _safe_int(get_field(row, "OpenInterest", "open_interest", "oi"))

        valid_records.append({
            "trade_date": trade_dt,
            "symbol": sym,
            "expiry_date": expiry_dt,
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "volume": volume_val,
            "open_interest": oi_val,
        })

    return valid_records, total_rows, gold_rows, error_rows, errors


async def import_csv_file(
    source: Union[str, Path, TextIO],
    session: AsyncSession,
) -> ImportSummary:
    """Import an MCX Bhavcopy CSV into PostgreSQL.

    Args:
        source: File path (str/Path) or an open text file / StringIO buffer.
        session: Active SQLAlchemy async session.

    Returns:
        ImportSummary with detailed counts and logs.
    """
    file_label = str(source) if isinstance(source, (str, Path)) else "<stream>"
    logger.info("Starting CSV import from %s", file_label)

    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.is_file():
            # Try prepending /app if running inside docker
            alt_path = Path("/app") / p
            if alt_path.is_file():
                p = alt_path
            else:
                logger.error("CSV file not found: %s", source)
                return ImportSummary(
                    file_path=file_label,
                    status="error",
                    errors=[f"File not found: {source}"],
                )

        file_label = str(p)
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            records, total_read, gold_found, err_rows, errors = parse_and_validate_csv_rows(reader)
    else:
        reader = csv.DictReader(source)
        records, total_read, gold_found, err_rows, errors = parse_and_validate_csv_rows(reader)

    skipped = (total_read - gold_found) + err_rows

    if not records:
        logger.warning(
            "CSV import completed for %s: 0 valid gold records found out of %d total rows.",
            file_label,
            total_read,
        )
        return ImportSummary(
            file_path=file_label,
            total_rows_read=total_read,
            gold_rows_found=gold_found,
            skipped_rows=skipped,
            error_rows=err_rows,
            errors=errors,
        )

    # 1. Upsert into daily_bhavcopy
    df = pl.DataFrame(records)
    daily_records = df.to_dicts()

    stmt = insert(DailyBhavcopy).values(daily_records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["trade_date", "symbol", "expiry_date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "open_interest": stmt.excluded.open_interest,
        },
    )
    await session.execute(stmt)

    # 2. Filter for positive close prices and upsert into normalized_prices
    # Exclude zero or missing closes from normalized_prices
    df_valid_close = df.filter(pl.col("close").is_not_null() & (pl.col("close") > 0))
    norm_upserted_count = 0

    if df_valid_close.height > 0:
        norm_df = normalize_dataframe(df_valid_close)
        norm_df = norm_df.rename({"close": "raw_close"})

        norm_records = norm_df.select([
            "trade_date",
            "symbol",
            "expiry_date",
            "raw_close",
            "norm_close_10g_999",
            "purity_multiplier",
            "unit_multiplier",
            "volume",
            "open_interest",
        ]).to_dicts()

        if norm_records:
            norm_stmt = insert(NormalizedPrices).values(norm_records)
            norm_stmt = norm_stmt.on_conflict_do_update(
                index_elements=["trade_date", "symbol", "expiry_date"],
                set_={
                    "raw_close": norm_stmt.excluded.raw_close,
                    "norm_close_10g_999": norm_stmt.excluded.norm_close_10g_999,
                    "purity_multiplier": norm_stmt.excluded.purity_multiplier,
                    "unit_multiplier": norm_stmt.excluded.unit_multiplier,
                    "volume": norm_stmt.excluded.volume,
                    "open_interest": norm_stmt.excluded.open_interest,
                },
            )
            await session.execute(norm_stmt)
            norm_upserted_count = len(norm_records)

    await session.commit()

    symbols = sorted(list({r["symbol"] for r in records}))
    trade_dates = sorted(list({r["trade_date"].isoformat() for r in records}))

    logger.info(
        "Successfully imported %s: %d total rows, %d gold rows, %d daily_bhavcopy, %d normalized.",
        file_label,
        total_read,
        gold_found,
        len(daily_records),
        norm_upserted_count,
    )

    return ImportSummary(
        file_path=file_label,
        status="ok",
        total_rows_read=total_read,
        gold_rows_found=gold_found,
        daily_bhavcopy_upserted=len(daily_records),
        normalized_prices_upserted=norm_upserted_count,
        skipped_rows=skipped,
        error_rows=err_rows,
        errors=errors,
        symbols=symbols,
        trade_dates=trade_dates,
    )


async def import_csv_files(
    paths: list[Union[str, Path]],
    session: AsyncSession,
) -> BatchImportSummary:
    """Import multiple MCX Bhavcopy CSV files sequentially in a single session.

    Idempotent across repeated calls and multiple dates.
    """
    batch = BatchImportSummary(total_files=len(paths))
    all_trade_dates: set[str] = set()
    all_symbols: set[str] = set()

    for p in paths:
        summary = await import_csv_file(p, session)
        batch.file_summaries.append(summary.to_dict())
        if summary.status == "ok":
            batch.successful_files += 1
        else:
            batch.failed_files += 1
            batch.errors.extend(summary.errors)

        batch.total_rows_read += summary.total_rows_read
        batch.gold_rows_found += summary.gold_rows_found
        batch.daily_bhavcopy_upserted += summary.daily_bhavcopy_upserted
        batch.normalized_prices_upserted += summary.normalized_prices_upserted
        batch.skipped_rows += summary.skipped_rows
        batch.error_rows += summary.error_rows
        all_trade_dates.update(summary.trade_dates)
        all_symbols.update(summary.symbols)

    batch.trade_dates = sorted(list(all_trade_dates))
    batch.symbols = sorted(list(all_symbols))
    if batch.failed_files > 0 and batch.successful_files == 0:
        batch.status = "error"
    elif batch.failed_files > 0:
        batch.status = "partial"

    return batch


async def import_path_or_dir(
    source: Union[str, Path],
    session: AsyncSession,
) -> Union[ImportSummary, BatchImportSummary]:
    """Import a single file, a directory of CSVs, or a list of files."""
    p = Path(source)
    if not p.exists():
        alt = Path("/app") / p
        if alt.exists():
            p = alt

    if p.is_dir():
        csv_files = sorted(list(p.glob("*.csv")) + list(p.glob("*.CSV")))
        if not csv_files:
            return BatchImportSummary(
                status="error",
                errors=[f"No CSV files found in directory: {source}"],
            )
        return await import_csv_files(csv_files, session)
    return await import_csv_file(p, session)


async def _run_cli():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Import MCX Bhavcopy CSV(s) into GOLD-X database")
    parser.add_argument(
        "paths",
        nargs="+",
        help="Path(s) to CSV file(s), directory containing CSVs, or '-' for stdin",
    )
    args = parser.parse_args()

    async with async_session_maker() as session:
        if args.paths == ["-"]:
            content = sys.stdin.read()
            summary = await import_csv_file(io.StringIO(content), session)
            print("\n--- GOLD-X CSV Import Summary ---")
            print(json.dumps(summary.to_dict(), indent=2))
            if summary.status != "ok":
                sys.exit(1)
            return

        # Resolve paths, expanding directories to *.csv
        files_to_import: list[Path] = []
        for p_str in args.paths:
            p = Path(p_str)
            if not p.exists():
                alt = Path("/app") / p
                if alt.exists():
                    p = alt

            if p.is_dir():
                found = sorted(list(p.glob("*.csv")) + list(p.glob("*.CSV")))
                files_to_import.extend(found)
            elif p.is_file():
                files_to_import.append(p)
            else:
                files_to_import.append(p)

        if not files_to_import:
            print(json.dumps({"status": "error", "message": "No CSV files found in provided path(s)"}, indent=2))
            sys.exit(1)

        if len(files_to_import) == 1:
            summary = await import_csv_file(files_to_import[0], session)
            print("\n--- GOLD-X CSV Import Summary ---")
            print(json.dumps(summary.to_dict(), indent=2))
            if summary.status != "ok":
                sys.exit(1)
        else:
            batch_summary = await import_csv_files(files_to_import, session)
            print("\n--- GOLD-X Batch CSV Import Summary ---")
            print(json.dumps(batch_summary.to_dict(), indent=2))
            if batch_summary.status == "error":
                sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(_run_cli())
