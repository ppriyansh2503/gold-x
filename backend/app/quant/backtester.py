"""Walk-forward backtester for GOLD-X cross-contract gold strategy.

Rules:
  • Day-by-day simulation — no look-ahead bias.
  • Only data up to the current day is used for rolling statistics.
  • GOLDTEN is isolated to dates >= 2025-01-01.
  • Alpha is attributed to the cross-contract spread, NOT gold price movement.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any

import numpy as np
import polars as pl

from app.quant.spreads import compute_pairwise_spreads
from app.quant.costs import net_edge as compute_net_edge

logger = logging.getLogger(__name__)

GOLDTEN_START = date(2025, 1, 1)


@dataclass
class Trade:
    """One hypothetical spread trade."""
    entry_date: date
    exit_date: date | None
    symbol_a: str
    symbol_b: str
    expiry_date: date
    direction: str          # BUY_SPREAD or SELL_SPREAD
    entry_spread: float
    exit_spread: float | None = None
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    costs: float = 0.0


@dataclass
class BacktestResult:
    total_signals: int = 0
    tradeable_signals: int = 0
    no_trade_signals: int = 0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    avg_holding_days: float = 0.0
    trades: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Exclude individual trades for the summary view
        d.pop("trades", None)
        return d


class BacktestEngine:
    """Day-by-day walk-forward backtester."""

    def __init__(self, prices_df: pl.DataFrame):
        """
        Args:
            prices_df: DataFrame with columns —
                trade_date, symbol, expiry_date, norm_close_10g_999,
                volume, open_interest
        """
        self.prices_df = prices_df.sort("trade_date")

    def run(
        self,
        window: int = 20,
        z_threshold: float = 2.0,
        exit_z: float = 0.5,
    ) -> BacktestResult:
        """Execute the walk-forward simulation.

        Args:
            window: Rolling window for Z-score.
            z_threshold: Entry threshold for |z|.
            exit_z: Exit when |z| falls below this.
        """
        result = BacktestResult()

        # Filter out GOLDTEN before its listing date
        df = self.prices_df.filter(
            ~(
                (pl.col("symbol") == "GOLDTEN")
                & (pl.col("trade_date") < GOLDTEN_START)
            )
        )

        all_dates = sorted(df["trade_date"].unique().to_list())
        if len(all_dates) < window + 1:
            logger.warning("Not enough data for backtesting (need > %d days)", window)
            return result

        open_trades: list[Trade] = []
        closed_trades: list[Trade] = []
        equity_curve: list[float] = []
        cumulative_pnl = 0.0

        for i, today in enumerate(all_dates):
            if i < window:
                continue  # need at least `window` days of history

            # Data available up to today (no look-ahead)
            history = df.filter(pl.col("trade_date") <= today)

            # Compute pairwise spreads across the full history
            spreads = compute_pairwise_spreads(history)
            if spreads.height == 0:
                continue

            # Compute rolling stats only from the history window
            spreads_sorted = spreads.sort(
                ["symbol_a", "symbol_b", "expiry_date", "trade_date"]
            )

            today_spreads = spreads_sorted.filter(pl.col("trade_date") == today)
            if today_spreads.height == 0:
                continue

            # ── Check exits for open trades ──────────────────────────
            still_open = []
            for trade in open_trades:
                # Find today's spread for this pair+expiry
                match = today_spreads.filter(
                    (pl.col("symbol_a") == trade.symbol_a)
                    & (pl.col("symbol_b") == trade.symbol_b)
                    & (pl.col("expiry_date") == trade.expiry_date)
                )
                if match.height == 0:
                    # Contract may have expired — force close at last known
                    still_open.append(trade)
                    continue

                row = match.row(0, named=True)
                current_spread = row["spread_abs"]

                # Compute Z for this pair using available trailing data
                pair_history = spreads_sorted.filter(
                    (pl.col("symbol_a") == trade.symbol_a)
                    & (pl.col("symbol_b") == trade.symbol_b)
                    & (pl.col("expiry_date") == trade.expiry_date)
                    & (pl.col("trade_date") <= today)
                ).tail(window)

                if pair_history.height < window:
                    still_open.append(trade)
                    continue

                mean_spread = pair_history["spread_abs"].mean()
                std_spread = pair_history["spread_abs"].std()
                if std_spread is None or std_spread == 0:
                    still_open.append(trade)
                    continue

                z = (current_spread - mean_spread) / std_spread

                # Exit condition: Z reverts below exit threshold
                if abs(z) < exit_z:
                    trade.exit_date = today
                    trade.exit_spread = current_spread

                    if trade.direction == "BUY_SPREAD":
                        trade.gross_pnl = trade.exit_spread - trade.entry_spread
                    else:
                        trade.gross_pnl = trade.entry_spread - trade.exit_spread

                    # Deduct costs
                    vol = min(row.get("volume_a", 0) or 0, row.get("volume_b", 0) or 0)
                    oi = min(row.get("oi_a", 0) or 0, row.get("oi_b", 0) or 0)
                    edge = compute_net_edge(
                        abs(trade.gross_pnl),
                        row["price_a"],
                        vol,
                        oi,
                    )
                    trade.costs = edge["total_costs"]
                    trade.net_pnl = trade.gross_pnl - trade.costs

                    closed_trades.append(trade)
                    cumulative_pnl += trade.net_pnl
                else:
                    still_open.append(trade)

            open_trades = still_open
            equity_curve.append(cumulative_pnl)

            # ── Check entries ────────────────────────────────────────
            for row in today_spreads.iter_rows(named=True):
                pair_key = (row["symbol_a"], row["symbol_b"], row["expiry_date"])

                # Skip if already in a trade for this pair
                if any(
                    (t.symbol_a, t.symbol_b, t.expiry_date) == pair_key
                    for t in open_trades
                ):
                    continue

                # Compute Z from trailing history
                pair_hist = spreads_sorted.filter(
                    (pl.col("symbol_a") == pair_key[0])
                    & (pl.col("symbol_b") == pair_key[1])
                    & (pl.col("expiry_date") == pair_key[2])
                    & (pl.col("trade_date") <= today)
                ).tail(window)

                if pair_hist.height < window:
                    continue

                mean_s = pair_hist["spread_abs"].mean()
                std_s = pair_hist["spread_abs"].std()
                if std_s is None or std_s == 0:
                    continue

                z = (row["spread_abs"] - mean_s) / std_s
                result.total_signals += 1

                # Cost check
                vol = min(row.get("volume_a", 0) or 0, row.get("volume_b", 0) or 0)
                oi = min(row.get("oi_a", 0) or 0, row.get("oi_b", 0) or 0)

                if abs(z) > z_threshold:
                    edge = compute_net_edge(
                        abs(row["spread_abs"]),
                        row["price_a"],
                        vol,
                        oi,
                    )
                    if edge["is_tradeable"]:
                        direction = "BUY_SPREAD" if z < -z_threshold else "SELL_SPREAD"
                        trade = Trade(
                            entry_date=today,
                            exit_date=None,
                            symbol_a=pair_key[0],
                            symbol_b=pair_key[1],
                            expiry_date=pair_key[2],
                            direction=direction,
                            entry_spread=row["spread_abs"],
                        )
                        open_trades.append(trade)
                        result.tradeable_signals += 1
                    else:
                        result.no_trade_signals += 1
                else:
                    result.no_trade_signals += 1

        # ── Aggregate results ────────────────────────────────────────
        result.total_trades = len(closed_trades)
        result.gross_pnl = round(sum(t.gross_pnl for t in closed_trades), 4)
        result.net_pnl = round(sum(t.net_pnl for t in closed_trades), 4)

        wins = [t for t in closed_trades if t.net_pnl > 0]
        result.win_rate = round(len(wins) / max(len(closed_trades), 1), 4)

        # Max drawdown from equity curve
        if equity_curve:
            peak = equity_curve[0]
            max_dd = 0.0
            for val in equity_curve:
                if val > peak:
                    peak = val
                dd = peak - val
                if dd > max_dd:
                    max_dd = dd
            result.max_drawdown = round(max_dd, 4)

        # Sharpe (annualized, using daily returns)
        if len(equity_curve) > 1:
            daily_returns = np.diff(equity_curve)
            if daily_returns.std() > 0:
                result.sharpe_ratio = round(
                    float(daily_returns.mean() / daily_returns.std() * math.sqrt(252)),
                    4,
                )

        # Average holding period
        holding_days = []
        for t in closed_trades:
            if t.exit_date and t.entry_date:
                holding_days.append((t.exit_date - t.entry_date).days)
        result.avg_holding_days = round(
            sum(holding_days) / max(len(holding_days), 1), 1
        )

        # Serialise trades
        result.trades = [asdict(t) for t in closed_trades[:100]]  # cap at 100

        return result
