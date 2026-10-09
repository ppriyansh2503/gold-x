"""Backtest performance API."""

from __future__ import annotations

import logging

import polars as pl
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.quant.backtester import BacktestEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backtest-performance", tags=["backtest"])


async def _load_all_normalized(session: AsyncSession) -> pl.DataFrame:
    """Load the full normalized_prices table into Polars."""
    query = text("""
        SELECT trade_date, symbol, expiry_date,
               norm_close_10g_999, volume, open_interest
        FROM normalized_prices
        ORDER BY trade_date
    """)
    result = await session.execute(query)
    rows = result.mappings().all()

    if not rows:
        return pl.DataFrame()

    return pl.DataFrame(
        [
            {
                "trade_date": r["trade_date"],
                "symbol": r["symbol"],
                "expiry_date": r["expiry_date"],
                "norm_close_10g_999": float(r["norm_close_10g_999"]),
                "volume": r["volume"] or 0,
                "open_interest": r["open_interest"] or 0,
            }
            for r in rows
        ]
    )


@router.get("", include_in_schema=False)
@router.get("/")
async def run_backtest(
    window: int = Query(20, ge=5, le=60),
    z_threshold: float = Query(2.0, ge=1.0, le=4.0),
    session: AsyncSession = Depends(get_async_session),
):
    """Run full walk-forward backtest on all available data.

    Returns complete BacktestResult including trade log (capped at 100).
    """
    prices_df = await _load_all_normalized(session)
    if prices_df.height == 0:
        return {
            "status": "no_data",
            "message": "No normalized price data available for backtesting.",
        }

    distinct_dates = prices_df["trade_date"].n_unique()
    if distinct_dates < window + 1:
        return {
            "status": "insufficient_data",
            "message": f"Requires at least {window + 1} trading days for rolling {window}-day window (currently {distinct_dates} day{'s' if distinct_dates > 1 else ''} available).",
            "days_available": distinct_dates,
            "days_required": window + 1,
            **BacktestEngine(prices_df).run(window=window, z_threshold=z_threshold).to_dict(),
            "trades": [],
        }

    engine = BacktestEngine(prices_df)
    result = engine.run(window=window, z_threshold=z_threshold)

    return {
        "status": "ok",
        **result.to_dict(),
        "trades": result.trades,
    }


@router.get("/summary")
async def get_backtest_summary(
    window: int = Query(20, ge=5, le=60),
    z_threshold: float = Query(2.0, ge=1.0, le=4.0),
    session: AsyncSession = Depends(get_async_session),
):
    """Return high-level backtest stats only (no trade log)."""
    prices_df = await _load_all_normalized(session)
    if prices_df.height == 0:
        return {
            "status": "no_data",
            "message": "No normalized price data available.",
        }

    distinct_dates = prices_df["trade_date"].n_unique()
    if distinct_dates < window + 1:
        return {
            "status": "insufficient_data",
            "message": f"Requires at least {window + 1} trading days for rolling {window}-day window (currently {distinct_dates} day{'s' if distinct_dates > 1 else ''} available).",
            "days_available": distinct_dates,
            "days_required": window + 1,
            **BacktestEngine(prices_df).run(window=window, z_threshold=z_threshold).to_dict(),
        }

    engine = BacktestEngine(prices_df)
    result = engine.run(window=window, z_threshold=z_threshold)

    return {"status": "ok", **result.to_dict()}
