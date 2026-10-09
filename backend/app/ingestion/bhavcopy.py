import logging
import httpx
import polars as pl
from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.ingestion.validator import (
    parse_trade_date,
    parse_expiry_date,
    validate_response_date,
    clean_symbol,
    is_gold_contract
)
from app.ingestion.normalizer import normalize_dataframe
from app.db.models import DailyBhavcopy, NormalizedPrices

logger = logging.getLogger(__name__)
settings = get_settings()

async def fetch_bhavcopy(trade_date: date) -> List[Dict[str, Any]]:
    """
    POST to MCX endpoint with date formatted as DD/MM/YYYY. 
    Parse JSON response. Filter for gold contracts only. Apply validator functions.
    """
    date_str = trade_date.strftime("%d/%m/%Y")
    payload = {"Date": date_str}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.MCX_BHAVCOPY_URL, 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch bhavcopy for date {date_str}: {e}")
            return []

    records = data.get("d", [])
    if not records:
        logger.info(f"No records found for date {date_str}")
        return []

    processed = []
    for row in records:
        sym = clean_symbol(row.get("Symbol", ""))
        if not is_gold_contract(sym):
            continue

        raw_trade_date_str = row.get("Date")
        if not raw_trade_date_str:
            continue
            
        row_trade_date = parse_trade_date(raw_trade_date_str)
        if not validate_response_date(trade_date, row_trade_date):
            continue

        expiry_date = parse_expiry_date(row.get("ExpiryDate", ""))
        
        try:
            open_price = float(row.get("Open", 0)) if row.get("Open") else None
            high_price = float(row.get("High", 0)) if row.get("High") else None
            low_price = float(row.get("Low", 0)) if row.get("Low") else None
            close_price = float(row.get("Close", 0)) if row.get("Close") else None
            vol = int(row.get("Volume", 0)) if row.get("Volume") else 0
            oi = int(row.get("OpenInterest", 0)) if row.get("OpenInterest") else 0
        except (ValueError, TypeError):
            logger.warning(f"Could not parse numeric fields for {sym} on {row_trade_date}")
            continue

        processed.append({
            "trade_date": row_trade_date,
            "symbol": sym,
            "expiry_date": expiry_date,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": vol,
            "open_interest": oi
        })
        
    return processed

async def ingest_date(trade_date: date, session: AsyncSession) -> int:
    """
    Fetch bhavcopy, normalize prices, upsert into both tables. 
    Return count of records inserted. Use Polars for the transformation pipeline.
    """
    logger.info(f"Ingesting data for {trade_date}")
    raw_data = await fetch_bhavcopy(trade_date)
    if not raw_data:
        logger.info(f"No valid gold contracts fetched for {trade_date}")
        return 0

    df = pl.DataFrame(raw_data)
    
    # 1. Upsert into daily_bhavcopy
    daily_records = df.to_dicts()
    if daily_records:
        stmt = insert(DailyBhavcopy).values(daily_records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['trade_date', 'symbol', 'expiry_date'],
            set_={
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'close': stmt.excluded.close,
                'volume': stmt.excluded.volume,
                'open_interest': stmt.excluded.open_interest,
            }
        )
        await session.execute(stmt)

    # 2. Normalize and Upsert into normalized_prices
    # Ensure there are positive close prices available for normalization
    df_valid_close = df.filter(pl.col("close").is_not_null() & (pl.col("close") > 0))
    if df_valid_close.height > 0:
        norm_df = normalize_dataframe(df_valid_close)
        norm_df = norm_df.rename({"close": "raw_close"})
        
        norm_records = norm_df.select([
            "trade_date", "symbol", "expiry_date", "raw_close", 
            "norm_close_10g_999", "purity_multiplier", "unit_multiplier", 
            "volume", "open_interest"
        ]).to_dicts()
        
        if norm_records:
            norm_stmt = insert(NormalizedPrices).values(norm_records)
            norm_stmt = norm_stmt.on_conflict_do_update(
                index_elements=['trade_date', 'symbol', 'expiry_date'],
                set_={
                    'raw_close': norm_stmt.excluded.raw_close,
                    'norm_close_10g_999': norm_stmt.excluded.norm_close_10g_999,
                    'purity_multiplier': norm_stmt.excluded.purity_multiplier,
                    'unit_multiplier': norm_stmt.excluded.unit_multiplier,
                    'volume': norm_stmt.excluded.volume,
                    'open_interest': norm_stmt.excluded.open_interest,
                }
            )
            await session.execute(norm_stmt)

    await session.commit()
    logger.info(f"Successfully ingested {len(daily_records)} records for {trade_date}")
    return len(daily_records)

async def ingest_date_range(start: date, end: date, session: AsyncSession) -> Dict[str, Any]:
    """
    Loop through business days, call ingest_date for each. 
    Return summary stats. Skip weekends.
    """
    logger.info(f"Starting ingestion from {start} to {end}")
    current_date = start
    total_records = 0
    days_processed = 0

    while current_date <= end:
        if current_date.weekday() < 5:  # Monday to Friday
            records = await ingest_date(current_date, session)
            total_records += records
            days_processed += 1
        current_date += timedelta(days=1)

    return {
        "start_date": start,
        "end_date": end,
        "days_processed": days_processed,
        "total_records_ingested": total_records
    }
