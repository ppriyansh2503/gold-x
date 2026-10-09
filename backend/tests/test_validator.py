import unittest
from datetime import date
from app.ingestion.validator import (
    parse_trade_date,
    parse_expiry_date,
    validate_response_date,
    clean_symbol,
    is_gold_contract,
)


class TestValidator(unittest.TestCase):
    def test_clean_symbol(self):
        self.assertEqual(clean_symbol("  gold "), "GOLD")
        self.assertEqual(clean_symbol("goldm"), "GOLDM")

    def test_is_gold_contract(self):
        self.assertTrue(is_gold_contract("GOLD"))
        self.assertTrue(is_gold_contract("goldm"))
        self.assertTrue(is_gold_contract("GOLDGUINEA"))
        self.assertTrue(is_gold_contract("GOLDPETAL"))
        self.assertTrue(is_gold_contract("GOLDTEN"))
        self.assertFalse(is_gold_contract("SILVER"))
        self.assertFalse(is_gold_contract("CRUDEOIL"))

    def test_parse_trade_date(self):
        self.assertEqual(parse_trade_date("01/15/2025"), date(2025, 1, 15))
        self.assertEqual(parse_trade_date(" 10/25/2024 "), date(2024, 10, 25))

    def test_parse_expiry_date(self):
        self.assertEqual(parse_expiry_date("05FEB2025"), date(2025, 2, 5))
        self.assertEqual(parse_expiry_date(" 04SEP2026 "), date(2026, 9, 4))

    def test_validate_response_date(self):
        d1 = date(2025, 1, 15)
        d2 = date(2025, 1, 15)
        d3 = date(2025, 1, 16)
        self.assertTrue(validate_response_date(d1, d2))
        self.assertFalse(validate_response_date(d1, d3))


if __name__ == "__main__":
    unittest.main()
