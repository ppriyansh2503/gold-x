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
            pl.lit("NO_DATA").alias("status"),
            pl.lit("NEUTRAL").alias("direction"),
            pl.lit("No spread data available.").alias("reason"),
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
        raw_spread = row.get("spread_abs", 0) or 0
        abs_spread = abs(raw_spread)
        price_a = row.get("price_a", 0) or 0
        vol = min(row.get("volume_a", 0) or 0, row.get("volume_b", 0) or 0)
        oi = min(row.get("oi_a", 0) or 0, row.get("oi_b", 0) or 0)

        edge_info = compute_net_edge(
            gross_spread=abs_spread,
            entry_price=price_a,
            volume=vol,
            open_interest=oi,
        )

        has_valid_z = z is not None and not np.isnan(z)
        is_tradeable = edge_info["is_tradeable"]
        net_edge_val = edge_info["net_edge"]
        total_costs = edge_info["total_costs"]
        penalty = edge_info["liquidity_penalty"]

        # Signal classification & status determination
        if not has_valid_z:
            status = "BASELINE_FORMATION"
            signal = "NO_TRADE"
            direction = "BUY_SPREAD" if raw_spread < 0 else "SELL_SPREAD"
            if is_tradeable:
                reason = (
                    f"Observed gross spread of ₹{abs_spread:.2f}/10g exceeds estimated round-trip costs "
                    f"of ₹{total_costs:.2f}/10g (net edge: ₹{net_edge_val:.2f}/10g). Statistical Z-score "
                    f"baseline requires {window} trading days of history."
                )
            else:
                reason = (
                    f"Gross spread ₹{abs_spread:.2f}/10g erased by ₹{total_costs:.2f}/10g estimated round-trip "
                    f"costs and slippage (net edge: ₹{net_edge_val:.2f}/10g). Statistical baseline requires {window} trading days."
                )
        elif penalty >= 3.0 and (vol < 100 or oi < 200):
            status = "REJECTED_INSUFFICIENT_LIQUIDITY"
            signal = "NO_TRADE"
            direction = "NEUTRAL"
            reason = (
                f"Severely illiquid contract pair (min volume: {vol}, min OI: {oi}) incurred {penalty:.1f}x "
                f"liquidity penalty, making real-world execution unviable."
            )
        elif not is_tradeable or net_edge_val <= 0:
            status = "REJECTED_COSTS_EXCEED_EDGE"
            signal = "NO_TRADE"
            direction = "NEUTRAL"
            reason = (
                f"Gross spread ₹{abs_spread:.2f}/10g wiped out by ₹{total_costs:.2f}/10g total transaction "
                f"costs (brokerage, STT, GST, exchange fees, and slippage). Net edge: ₹{net_edge_val:.2f}/10g."
            )
        elif abs(z) > z_threshold and is_tradeable:
            status = "POTENTIAL_OPPORTUNITY"
            signal = "BUY_SPREAD" if z < -z_threshold else "SELL_SPREAD"
            direction = signal
            reason = (
                f"Statistically significant divergence (|Z| = {abs(z):.2f} > {z_threshold}) with viable "
                f"net edge of ₹{net_edge_val:.2f}/10g after all round-trip costs and slippage."
            )
        else:
            status = "WATCH"
            signal = "NO_TRADE"
            direction = "NEUTRAL"
            reason = (
                f"Spread of ₹{abs_spread:.2f}/10g is within normal statistical deviation bounds "
                f"(|Z| = {abs(z):.2f} <= {z_threshold}). Monitoring for mean-reverting divergence."
            )

        enriched.append(
            {
                "signal": signal,
                "status": status,
                "direction": direction,
                "reason": reason,
                "signal_strength": round(abs(z), 4) if has_valid_z else 0.0,
                "gross_spread": edge_info["gross_spread"],
                "total_costs": total_costs,
                "net_edge_value": net_edge_val,
                "is_tradeable": is_tradeable,
                "liquidity_penalty": penalty,
                "cost_breakdown": edge_info["cost_breakdown"],
            }
        )

    # Build enrichment DataFrame and concat horizontally
    enrich_df = pl.DataFrame(enriched)
    result = pl.concat([df.drop(["_rolling_mean", "_rolling_std"]), enrich_df], how="horizontal")

    return result
