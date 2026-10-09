import logging
import polars as pl
from typing import Tuple

logger = logging.getLogger(__name__)

CONTRACT_SPECS = {
    "GOLD":        {"quote_unit_grams": 10, "purity": 995, "lot_size_grams": 1000},
    "GOLDM":       {"quote_unit_grams": 10, "purity": 995, "lot_size_grams": 10},
    "GOLDGUINEA":  {"quote_unit_grams": 8,  "purity": 999, "lot_size_grams": 8},
    "GOLDPETAL":   {"quote_unit_grams": 1,  "purity": 999, "lot_size_grams": 1},
    "GOLDTEN":     {"quote_unit_grams": 10, "purity": 999, "lot_size_grams": 10},
}

def get_multipliers(symbol: str) -> Tuple[float, float]:
    """Returns (unit_mult, purity_mult)"""
    symbol_upper = symbol.strip().upper()
    if symbol_upper not in CONTRACT_SPECS:
        raise ValueError(f"Unknown symbol: {symbol_upper}")
    
    spec = CONTRACT_SPECS[symbol_upper]
    unit_mult = 10.0 / spec["quote_unit_grams"]
    purity_mult = 999.0 / spec["purity"]
    
    return unit_mult, purity_mult

def normalize_price(symbol: str, raw_price: float) -> float:
    """Normalize price based on symbol's quote unit and purity."""
    unit_mult, purity_mult = get_multipliers(symbol)
    return raw_price * unit_mult * purity_mult

def normalize_dataframe(df: pl.DataFrame) -> pl.DataFrame:
    """
    Adds norm_close_10g_999, purity_multiplier, unit_multiplier columns.
    Assumes 'symbol' and 'close' columns exist.
    """
    if "symbol" not in df.columns or "close" not in df.columns:
        logger.error("DataFrame must contain 'symbol' and 'close' columns.")
        return df

    # Map symbols to their multipliers
    symbols = df["symbol"].unique().to_list()
    
    unit_mult_map = {}
    purity_mult_map = {}
    
    for sym in symbols:
        try:
            u_mult, p_mult = get_multipliers(sym)
            unit_mult_map[sym] = u_mult
            purity_mult_map[sym] = p_mult
        except ValueError:
            logger.warning(f"Unknown symbol '{sym}' encountered during normalization. Using 1.0 for multipliers.")
            unit_mult_map[sym] = 1.0
            purity_mult_map[sym] = 1.0

    df = df.with_columns(
        pl.col("symbol").replace_strict(unit_mult_map, default=1.0, return_dtype=pl.Float64).alias("unit_multiplier"),
        pl.col("symbol").replace_strict(purity_mult_map, default=1.0, return_dtype=pl.Float64).alias("purity_multiplier"),
    )
    
    df = df.with_columns(
        (pl.col("close") * pl.col("unit_multiplier") * pl.col("purity_multiplier")).alias("norm_close_10g_999")
    )

    return df
