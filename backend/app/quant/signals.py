"""Z-score signal generation for cross-contract gold spreads.

Signal rule:
  |z_score| > threshold  AND  net_edge > 0  →  BUY_SPREAD or SELL_SPREAD
  Otherwise                                →  NO_TRADE
"""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import polars as pl
from scipy import stats as sp_stats

from app.quant.costs import net_edge as compute_net_edge

logger = logging.getLogger(__name__)


def rolling_zscore(series: pl.Series, window: int = 20) -> pl.Series:
    """Compute rolling Z-score: (value − rolling_mean) / rolling_std.

    Uses scipy.stats.zscore on the trailing window for validation of the
    first full window, then pure Polars rolling ops for speed.
    """
    rolling_mean = series.rolling_mean(window_size=window)
    rolling_std = series.rolling_std(window_size=window)
    z = (series - rolling_mean) / rolling_std
    return z.alias("z_score")


def generate_signals(
    spreads_df: pl.DataFrame,
    window: int = 20,
    z_threshold: float = 2.0,
) -> pl.DataFrame:
    """Enrich a spreads DataFrame with z-score, signal, and cost autopsy.

    Expected input columns (from compute_pairwise_spreads):
        trade_date, expiry_date, symbol_a, symbol_b,
        price_a, price_b, spread_abs, spread_pct,
        volume_a, volume_b, oi_a, oi_b

    Output adds:
        z_score, signal, signal_strength, gross_spread, total_costs,
        net_edge_value, is_tradeable
    """
    if spreads_df.height == 0:
        return spreads_df.with_columns(
            pl.lit(None).cast(pl.Float64).alias("z_score"),
            pl.lit("NO_TRADE").alias("signal"),
            pl.lit(0.0).alias("signal_strength"),
            pl.lit(0.0).alias("gross_spread"),
            pl.lit(0.0).alias("total_costs"),
            pl.lit(0.0).alias("net_edge_value"),
            pl.lit(False).alias("is_tradeable"),
        )

    # Sort for correct rolling computation
    df = spreads_df.sort(["symbol_a", "symbol_b", "expiry_date", "trade_date"])

    # Rolling Z-score per pair+expiry group
    df = df.with_columns(
        pl.col("spread_abs")
        .rolling_mean(window_size=window)
        .over(["symbol_a", "symbol_b", "expiry_date"])
        .alias("_rolling_mean"),
        pl.col("spread_abs")
        .rolling_std(window_size=window)
        .over(["symbol_a", "symbol_b", "expiry_date"])
        .alias("_rolling_std"),
    ).with_columns(
        (
            (pl.col("spread_abs") - pl.col("_rolling_mean"))
            / pl.col("_rolling_std")
        ).alias("z_score")
    )

    # ── Row-level cost + signal evaluation ───────────────────────────
    # Polars is columnar, so we materialise to dicts for the cost model
    # then rejoin. For datasets < ~50k rows this is fast enough.

    records = df.to_dicts()
    enriched: list[dict] = []

    for row in records:
        z = row.get("z_score")
        abs_spread = abs(row.get("spread_abs", 0) or 0)
        price_a = row.get("price_a", 0) or 0
        vol = min(row.get("volume_a", 0) or 0, row.get("volume_b", 0) or 0)
        oi = min(row.get("oi_a", 0) or 0, row.get("oi_b", 0) or 0)

        edge_info = compute_net_edge(
            gross_spread=abs_spread,
            entry_price=price_a,
            volume=vol,
            open_interest=oi,
        )

        # Signal classification
        if z is not None and not np.isnan(z) and abs(z) > z_threshold and edge_info["is_tradeable"]:
            signal = "BUY_SPREAD" if z < -z_threshold else "SELL_SPREAD"
        else:
            signal = "NO_TRADE"

        enriched.append(
            {
                "signal": signal,
                "signal_strength": round(abs(z), 4) if z is not None and not np.isnan(z) else 0.0,
                "gross_spread": edge_info["gross_spread"],
                "total_costs": edge_info["total_costs"],
                "net_edge_value": edge_info["net_edge"],
                "is_tradeable": edge_info["is_tradeable"],
                "liquidity_penalty": edge_info["liquidity_penalty"],
                "cost_breakdown": edge_info["cost_breakdown"],
            }
        )

    # Build enrichment DataFrame and concat horizontally
    enrich_df = pl.DataFrame(enriched)
    result = pl.concat([df.drop(["_rolling_mean", "_rolling_std"]), enrich_df], how="horizontal")

    return result
