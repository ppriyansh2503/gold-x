import logging
from datetime import date, datetime
from dateutil.parser import parse

logger = logging.getLogger(__name__)

GOLD_CONTRACTS = {"GOLD", "GOLDM", "GOLDGUINEA", "GOLDPETAL", "GOLDTEN"}

def parse_trade_date(raw: str) -> date:
    """Handle ISO format (YYYY-MM-DD) and MM/DD/YYYY from MCX responses."""
    clean_raw = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(clean_raw, fmt).date()
        except ValueError:
            continue
    try:
        return parse(clean_raw).date()
    except Exception as e:
        raise ValueError(f"Failed to parse trade date: {raw}") from e

def parse_expiry_date(raw: str) -> date:
    """Handle compact format like '04SEP2026', hyphenated, or ISO format."""
    clean_raw = str(raw).strip().upper()
    for fmt in ("%d%b%Y", "%d-%b-%Y", "%d%B%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(clean_raw, fmt).date()
        except ValueError:
            continue
    try:
        return parse(clean_raw).date()
    except Exception as e:
        raise ValueError(f"Failed to parse expiry date: {raw}") from e

def validate_response_date(requested: date, returned: date) -> bool:
    """Return True only if they match. Log a warning if MCX returned a different date."""
    if requested != returned:
        logger.warning(f"Date mismatch: requested {requested}, but MCX returned {returned}.")
        return False
    return True

def clean_symbol(raw: str) -> str:
    """Strip whitespace, uppercase."""
    return raw.strip().upper()

def is_gold_contract(symbol: str) -> bool:
    """Return True if symbol is one of GOLD, GOLDM, GOLDGUINEA, GOLDPETAL, GOLDTEN."""
    return clean_symbol(symbol) in GOLD_CONTRACTS
