"""Pairwise spread computation between gold contracts sharing the same expiry.

The key constraint: spreads are ONLY computed between contracts that share the
exact same expiry_date, to separate mechanical roll-down from genuine curve
changes.
"""

from __future__ import annotations

import logging
from datetime import date

import polars as pl

logger = logging.getLogger(__name__)


def compute_pairwise_spreads(df: pl.DataFrame) -> pl.DataFrame:
    """Compute all pairwise spreads between different symbols on the same
    trade_date and expiry_date.

    Args:
        df: Normalized prices with columns —
            trade_date, symbol, expiry_date, norm_close_10g_999,
            volume, open_interest

    Returns:
        DataFrame with columns:
            trade_date, expiry_date, symbol_a, symbol_b,
            price_a, price_b, spread_abs, spread_pct,
            volume_a, volume_b, oi_a, oi_b
    """
    required = {"trade_date", "symbol", "expiry_date", "norm_close_10g_999"}
    missing = required - set(df.columns)
    if missing:
        logger.error("Missing columns for spread computation: %s", missing)
        return pl.DataFrame()

    lf = df.lazy()

    # Self-join on (trade_date, expiry_date); keep symbol_a < symbol_b
    # to avoid duplicate pairs and self-pairs.
    pairs = (
        lf.join(lf, on=["trade_date", "expiry_date"], how="inner", suffix="_right")
        .filter(pl.col("symbol") < pl.col("symbol_right"))
        .select(
            pl.col("trade_date"),
            pl.col("expiry_date"),
            pl.col("symbol").alias("symbol_a"),
            pl.col("symbol_right").alias("symbol_b"),
            pl.col("norm_close_10g_999").alias("price_a"),
            pl.col("norm_close_10g_999_right").alias("price_b"),
            pl.col("volume").alias("volume_a"),
            pl.col("volume_right").alias("volume_b"),
            pl.col("open_interest").alias("oi_a"),
            pl.col("open_interest_right").alias("oi_b"),
        )
        .with_columns(
            (pl.col("price_a") - pl.col("price_b")).alias("spread_abs"),
            pl.when(pl.col("price_b") != 0)
            .then(
                (pl.col("price_a") - pl.col("price_b"))
                / pl.col("price_b")
                * 100
            )
            .otherwise(0.0)
            .alias("spread_pct"),
        )
    )

    return pairs.collect()


def compute_spread_timeseries(
    df: pl.DataFrame,
    symbol_a: str,
    symbol_b: str,
    expiry_date: date,
) -> pl.DataFrame:
    """Return the time-series of spreads for a specific pair and expiry.

    Handles the case where the caller's (symbol_a, symbol_b) ordering
    doesn't match the canonical (sorted) order used internally.
    """
    spreads = compute_pairwise_spreads(df)
    if spreads.height == 0:
        return spreads

    # Canonical order is alphabetical
    s1, s2 = sorted([symbol_a, symbol_b])
    needs_flip = s1 != symbol_a

    ts = (
        spreads.filter(
            (pl.col("symbol_a") == s1)
            & (pl.col("symbol_b") == s2)
            & (pl.col("expiry_date") == expiry_date)
        )
        .sort("trade_date")
    )

    if needs_flip and ts.height > 0:
        ts = ts.with_columns(
            pl.col("symbol_b").alias("symbol_a"),
            pl.col("symbol_a").alias("symbol_b"),
            pl.col("price_b").alias("price_a"),
            pl.col("price_a").alias("price_b"),
            (-pl.col("spread_abs")).alias("spread_abs"),
            (-pl.col("spread_pct")).alias("spread_pct"),
            pl.col("volume_b").alias("volume_a"),
            pl.col("volume_a").alias("volume_b"),
            pl.col("oi_b").alias("oi_a"),
            pl.col("oi_a").alias("oi_b"),
        )

    return ts
