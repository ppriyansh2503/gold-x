"""Parity API — normalized prices and spread matrix."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import polars as pl
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parity", tags=["parity"])


@router.get("", include_in_schema=False)
@router.get("/")
async def get_parity(
    session: AsyncSession = Depends(get_async_session),
):
    """Return latest normalized prices for all gold contracts, grouped by expiry.

    Also returns a pairwise spread matrix per expiry.
    """
    query = text("""
        WITH latest AS (
            SELECT DISTINCT ON (symbol, expiry_date)
                trade_date, symbol, expiry_date,
                raw_close, norm_close_10g_999,
                volume, open_interest
            FROM normalized_prices
            ORDER BY symbol, expiry_date, trade_date DESC
        )
        SELECT * FROM latest
        ORDER BY expiry_date, symbol
    """)

    result = await session.execute(query)
    rows = result.mappings().all()

    if not rows:
        return {}

    # Group by expiry_date
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        exp_key = row["expiry_date"].isoformat()
        days_to_expiry = (row["expiry_date"] - date.today()).days

        entry = {
            "symbol": row["symbol"],
            "expiry": exp_key,
            "raw_close": float(row["raw_close"]),
            "normalized_price": float(row["norm_close_10g_999"]),
            "volume": row["volume"] or 0,
            "open_interest": row["open_interest"] or 0,
            "trade_date": row["trade_date"].isoformat(),
            "days_to_expiry": days_to_expiry,
        }
        grouped.setdefault(exp_key, []).append(entry)

    return grouped


@router.get("/history")
async def get_spread_history(
    symbol_a: str = Query(..., description="First contract symbol"),
    symbol_b: str = Query(..., description="Second contract symbol"),
    expiry_date: date = Query(..., description="Shared expiry date"),
    session: AsyncSession = Depends(get_async_session),
):
    """Return historical spread time series for a pair sharing an expiry."""
    query = text("""
        SELECT
            a.trade_date,
            a.symbol AS symbol_a,
            b.symbol AS symbol_b,
            a.norm_close_10g_999 AS price_a,
            b.norm_close_10g_999 AS price_b,
            (a.norm_close_10g_999 - b.norm_close_10g_999) AS spread_abs,
            CASE WHEN b.norm_close_10g_999 > 0
                THEN ((a.norm_close_10g_999 - b.norm_close_10g_999) / b.norm_close_10g_999 * 100)
                ELSE 0
            END AS spread_pct,
            a.volume AS volume_a,
            b.volume AS volume_b,
            a.open_interest AS oi_a,
            b.open_interest AS oi_b
        FROM normalized_prices a
        JOIN normalized_prices b
            ON a.trade_date = b.trade_date
            AND a.expiry_date = b.expiry_date
        WHERE a.symbol = :sym_a
          AND b.symbol = :sym_b
          AND a.expiry_date = :exp
        ORDER BY a.trade_date
    """)

    result = await session.execute(
        query,
        {"sym_a": symbol_a.upper(), "sym_b": symbol_b.upper(), "exp": expiry_date},
    )
    rows = result.mappings().all()

    return [
        {
            "trade_date": r["trade_date"].isoformat(),
            "symbol_a": r["symbol_a"],
            "symbol_b": r["symbol_b"],
            "price_a": float(r["price_a"]),
            "price_b": float(r["price_b"]),
            "spread_abs": float(r["spread_abs"]),
            "spread_pct": round(float(r["spread_pct"]), 4),
            "volume_a": r["volume_a"] or 0,
            "volume_b": r["volume_b"] or 0,
        }
        for r in rows
    ]
