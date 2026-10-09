"""Transaction cost model for MCX gold contracts.

All fee constants are in DECIMAL form (not percentage), e.g. 0.0026 = 0.26%.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── MCX fee structure (approximate, discount-broker basis) ────────────

EXCHANGE_FEE_RATE = 0.00026       # 0.026% exchange transaction charges
SEBI_FEE_RATE = 0.000001          # SEBI turnover fee (negligible)
STT_SELL_RATE = 0.0001            # 0.01% STT on sell side for commodity futures
GST_ON_FEES_RATE = 0.18           # 18% GST on (brokerage + exchange fees)
BROKERAGE_PER_SIDE = 20.0         # Flat ₹20 per order (discount broker)
ESTIMATED_SLIPPAGE_RATE = 0.0005  # 5 bps estimated slippage


def round_trip_cost(
    entry_price: float,
    exit_price: float,
    lot_value: float = 1.0,
) -> dict:
    """Calculate full round-trip cost breakdown.

    Args:
        entry_price: Per-unit entry price.
        exit_price: Per-unit exit price.
        lot_value: Multiplier representing lot size in units.

    Returns:
        Dict with each cost component and total.
    """
    entry_val = entry_price * lot_value
    exit_val = exit_price * lot_value
    turnover = entry_val + exit_val

    exch_fee = turnover * EXCHANGE_FEE_RATE
    sebi_fee = turnover * SEBI_FEE_RATE
    stt = exit_val * STT_SELL_RATE
    brokerage = BROKERAGE_PER_SIDE * 2
    gst = (exch_fee + brokerage) * GST_ON_FEES_RATE
    slippage = turnover * ESTIMATED_SLIPPAGE_RATE

    total = exch_fee + sebi_fee + stt + brokerage + gst + slippage

    return {
        "exchange_fee": round(exch_fee, 4),
        "sebi_fee": round(sebi_fee, 4),
        "stt": round(stt, 4),
        "brokerage": round(brokerage, 2),
        "gst": round(gst, 4),
        "slippage": round(slippage, 4),
        "total_cost": round(total, 4),
    }


def liquidity_penalty(volume: int, open_interest: int) -> float:
    """Return a cost multiplier based on volume and open-interest thresholds.

    1.0 = liquid (no penalty), higher = worse.
    Volume alone is not market depth — this is a conservative heuristic.
    """
    if volume < 100:
        penalty = 3.0
    elif volume < 500:
        penalty = 2.0
    elif volume < 1000:
        penalty = 1.5
    else:
        penalty = 1.0

    # OI supplement: low open interest signals thin participation
    if open_interest < 500:
        penalty += 0.5

    return penalty


def net_edge(
    gross_spread: float,
    entry_price: float,
    volume: int,
    open_interest: int,
    lot_value: float = 1.0,
) -> dict:
    """Calculate net edge after all transaction costs and liquidity penalty.

    Returns a dict with cost autopsy and is_tradeable flag.
    Strict rule: is_tradeable is True ONLY if net_edge > 0.
    """
    costs = round_trip_cost(entry_price, entry_price + gross_spread, lot_value)
    base_cost = costs["total_cost"]

    liq_penalty = liquidity_penalty(volume, open_interest)
    total_costs = round(base_cost * liq_penalty, 4)

    edge = round(gross_spread - total_costs, 4)

    return {
        "gross_spread": round(gross_spread, 4),
        "cost_breakdown": costs,
        "liquidity_penalty": liq_penalty,
        "total_costs": total_costs,
        "net_edge": edge,
        "is_tradeable": edge > 0,
    }
