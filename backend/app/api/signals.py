"""Signals API — current trading signals with full cost autopsy."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import polars as pl
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.quant.spreads import compute_pairwise_spreads
from app.quant.signals import generate_signals

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/signals", tags=["signals"])


async def _load_normalized_prices(
    session: AsyncSession,
    lookback_days: int = 60,
) -> pl.DataFrame:
    """Load recent normalized prices into a Polars DataFrame."""
    latest_dt_result = await session.execute(text("SELECT MAX(trade_date) FROM normalized_prices"))
    latest_dt = latest_dt_result.scalar()
    if not latest_dt:
        return pl.DataFrame()

    cutoff = latest_dt - timedelta(days=lookback_days)
    query = text("""
        SELECT trade_date, symbol, expiry_date,
               norm_close_10g_999, volume, open_interest
        FROM normalized_prices
        WHERE trade_date >= :cutoff
        ORDER BY trade_date
    """)
    result = await session.execute(query, {"cutoff": cutoff})
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
async def get_signals(
    window: int = Query(20, ge=5, le=60, description="Rolling window size"),
    z_threshold: float = Query(2.0, ge=1.0, le=4.0, description="Z-score threshold"),
    session: AsyncSession = Depends(get_async_session),
):
    """Return current signals for all active pairs.

    Each signal includes: action, z_score, contract pair, expiry,
    gross_spread, full cost_breakdown, net_edge, is_tradeable.
    When NO_TRADE: full cost autopsy explains why.
    """
    prices_df = await _load_normalized_prices(session)
    if prices_df.height == 0:
        return []

    # Compute spreads then signals
    spreads = compute_pairwise_spreads(prices_df)
    if spreads.height == 0:
        return []

    signals_df = generate_signals(spreads, window=window, z_threshold=z_threshold)

    # Only return the latest date's signals
    latest_date = signals_df["trade_date"].max()
    today_signals = signals_df.filter(pl.col("trade_date") == latest_date)

    output = []
    for row in today_signals.iter_rows(named=True):
        cost_bd = row.get("cost_breakdown", {})
        if isinstance(cost_bd, str):
            import json
            try:
                cost_bd = json.loads(cost_bd)
            except (json.JSONDecodeError, TypeError):
                cost_bd = {}

        output.append(
            {
                "trade_date": str(row["trade_date"]),
                "contract_a": row["symbol_a"],
                "contract_b": row["symbol_b"],
                "expiry_date": str(row["expiry_date"]),
                "action": row["signal"],
                "status": row.get("status", "NO_DATA"),
                "direction": row.get("direction", "NEUTRAL"),
                "reason": row.get("reason", ""),
                "price_a": float(row.get("price_a", 0) or 0),
                "price_b": float(row.get("price_b", 0) or 0),
                "volume_a": row.get("volume_a", 0) or 0,
                "volume_b": row.get("volume_b", 0) or 0,
                "oi_a": row.get("oi_a", 0) or 0,
                "oi_b": row.get("oi_b", 0) or 0,
                "z_score": row.get("z_score"),
                "signal_strength": row.get("signal_strength", 0),
                "gross_spread": row.get("gross_spread", 0),
                "net_edge": row.get("net_edge_value", 0),
                "is_tradeable": row.get("is_tradeable", False),
                "verdict": "YES" if row.get("is_tradeable", False) else "NO",
                "cost_breakdown": {
                    "exchange_fees": cost_bd.get("exchange_fee", 0),
                    "brokerage": cost_bd.get("brokerage", 0),
                    "stt": cost_bd.get("stt", 0),
                    "gst": cost_bd.get("gst", 0),
                    "slippage": cost_bd.get("slippage", 0),
                    "liquidity_penalty": row.get("liquidity_penalty", 1.0),
                    "total_costs": row.get("total_costs", 0),
                    "gross_spread": row.get("gross_spread", 0),
                },
            }
        )

    return output


@router.get("/history")
async def get_signal_history(
    days: int = Query(30, ge=1, le=365, description="Lookback days"),
    session: AsyncSession = Depends(get_async_session),
):
    """Return signal history over the requested period."""
    prices_df = await _load_normalized_prices(session, lookback_days=days + 60)
    if prices_df.height == 0:
        return []

    spreads = compute_pairwise_spreads(prices_df)
    if spreads.height == 0:
        return []

    signals_df = generate_signals(spreads)

    cutoff = date.today() - timedelta(days=days)
    recent = signals_df.filter(pl.col("trade_date") >= cutoff)

    # Summarise by date
    summary = []
    for dt in sorted(recent["trade_date"].unique().to_list()):
        day_data = recent.filter(pl.col("trade_date") == dt)
        total = day_data.height
        tradeable = day_data.filter(pl.col("is_tradeable") == True).height
        no_trade = total - tradeable

        summary.append(
            {
                "date": str(dt),
                "total_pairs": total,
                "tradeable": tradeable,
                "no_trade": no_trade,
            }
        )

    return summary
