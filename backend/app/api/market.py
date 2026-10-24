"""Market Overview & System Status API."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.ingestion.normalizer import CONTRACT_SPECS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["market"])


@router.get("/market-overview")
async def get_market_overview(
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Return executive market summary for the latest available trade date.

    Includes:
      - Latest snapshot trade date
      - Institutional Benchmark reference price (₹/10g 999 purity)
      - Total contracts and active expiry breakdown
      - Maximum cross-contract parity spread observed
      - Normalized price table across all active gold contracts
    """
    # 1. Fetch latest trade date
    latest_dt_result = await session.execute(
        text("SELECT MAX(trade_date) FROM normalized_prices")
    )
    latest_dt = latest_dt_result.scalar_one_or_none()

    if not latest_dt:
        return {
            "status": "no_data",
            "message": "No market data available.",
            "trade_date": None,
            "benchmark_price": None,
            "total_contracts": 0,
            "active_expiries": [],
            "max_spread_abs": 0.0,
            "max_spread_pct": 0.0,
            "contracts": [],
        }

    # 2. Query all contract rows for latest trade date
    query = text("""
        SELECT
            symbol, expiry_date, raw_close, norm_close_10g_999,
            volume, open_interest, trade_date
        FROM normalized_prices
        WHERE trade_date = :trade_date
        ORDER BY expiry_date, symbol
    """)
    result = await session.execute(query, {"trade_date": latest_dt})
    rows = result.mappings().all()

    contracts = []
    expiries_set = set()
    norm_prices: list[float] = []

    # Benchmark: preferentially use GOLD (standard 1kg 995 -> normalized to 999) nearest expiry
    benchmark_price: float | None = None

    for r in rows:
        sym = r["symbol"]
        exp_date = r["expiry_date"]
        exp_iso = exp_date.isoformat()
        expiries_set.add(exp_iso)

        raw_c = float(r["raw_close"])
        norm_c = float(r["norm_close_10g_999"])
        norm_prices.append(norm_c)

        if benchmark_price is None and sym == "GOLD":
            benchmark_price = norm_c

        spec = CONTRACT_SPECS.get(sym, {"quote_unit_grams": 10, "purity": 995, "lot_size_grams": 100})
        dte = (exp_date - latest_dt).days

        contracts.append(
            {
                "symbol": sym,
                "expiry_date": exp_iso,
                "days_to_expiry": dte,
                "raw_close": raw_c,
                "normalized_price": norm_c,
                "quote_unit": f"{spec['quote_unit_grams']}g",
                "purity": f"{spec['purity']}/1000",
                "lot_size": f"{spec['lot_size_grams']}g",
                "volume": r["volume"] or 0,
                "open_interest": r["open_interest"] or 0,
            }
        )

    # Fallback benchmark if GOLD contract not present
    if benchmark_price is None and norm_prices:
        benchmark_price = sum(norm_prices) / len(norm_prices)

    # Calculate overall max cross-contract spread across contracts sharing an expiry
    max_spread_abs = 0.0
    max_spread_pct = 0.0

    # Group by expiry
    by_exp: dict[str, list[float]] = {}
    for c in contracts:
        by_exp.setdefault(c["expiry_date"], []).append(c["normalized_price"])

    for exp, prices in by_exp.items():
        if len(prices) > 1:
            spread = max(prices) - min(prices)
            pct = (spread / min(prices)) * 100 if min(prices) > 0 else 0.0
            if spread > max_spread_abs:
                max_spread_abs = spread
                max_spread_pct = pct

    return {
        "status": "ok",
        "trade_date": latest_dt.isoformat(),
        "benchmark_price": round(benchmark_price, 2) if benchmark_price else None,
        "benchmark_contract": "GOLD (Standard 10g 999 Basis)",
        "total_contracts": len(contracts),
        "active_expiries": sorted(list(expiries_set)),
        "max_spread_abs": round(max_spread_abs, 2),
        "max_spread_pct": round(max_spread_pct, 4),
        "contracts": contracts,
    }


@router.get("/system/status")
async def get_system_status(
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Return database health, record counts, and ingestion pipeline status."""
    try:
        # Combined query to avoid asyncpg multi-statement locking
        counts_res = await session.execute(
            text("""
                SELECT 
                    (SELECT COUNT(*) FROM daily_bhavcopy) AS bhav_count,
                    (SELECT COUNT(*) FROM normalized_prices) AS norm_count
            """)
        )
        counts_row = counts_res.mappings().one()
        bhav_count = counts_row["bhav_count"] or 0
        norm_count = counts_row["norm_count"] or 0

        # Distinct trade dates
        dates_res = await session.execute(
            text("SELECT DISTINCT trade_date FROM normalized_prices ORDER BY trade_date")
        )
        dates = [d.isoformat() for d in dates_res.scalars().all()]

        return {
            "status": "healthy",
            "database_connected": True,
            "bhavcopy_records": bhav_count,
            "normalized_records": norm_count,
            "distinct_trade_dates": len(dates),
            "trade_dates": dates,
            "supported_contracts": list(CONTRACT_SPECS.keys()),
            "ingestion_mode": "Local CSV Ingestion (Akamai WAF perimeter active on direct endpoint)",
            "platform_version": "1.0.0",
        }
    except Exception as e:
        logger.exception("Failed to query system status")
        return {
            "status": "degraded",
            "database_connected": False,
            "error": str(e),
        }
