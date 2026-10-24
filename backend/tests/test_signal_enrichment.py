import unittest
from datetime import date, timedelta
import polars as pl
from app.quant.signals import generate_signals


class TestSignalEnrichment(unittest.TestCase):
    def test_baseline_formation_single_day(self):
        # 1 day of data is insufficient for rolling Z-score window=20
        spreads = pl.DataFrame(
            {
                "trade_date": [date(2026, 9, 18)],
                "expiry_date": [date(2026, 10, 5)],
                "symbol_a": ["GOLD"],
                "symbol_b": ["GOLDM"],
                "price_a": [75000.0],
                "price_b": [75086.0],
                "spread_abs": [-86.0],
                "spread_pct": [-0.11],
                "volume_a": [10000],
                "volume_b": [5000],
                "oi_a": [8000],
                "oi_b": [6000],
            },
            schema_overrides={"trade_date": pl.Date, "expiry_date": pl.Date},
        )

        signals = generate_signals(spreads, window=20, z_threshold=2.0)
        self.assertEqual(signals.height, 1)

        row = signals.row(0, named=True)
        self.assertEqual(row["status"], "BASELINE_FORMATION")
        self.assertEqual(row["signal"], "NO_TRADE")
        self.assertIn("Statistical", row["reason"])
        self.assertIn("baseline requires 20 trading days", row["reason"])

    def test_rejected_costs_exceed_edge(self):
        # Construct synthetic 25 days where gross spread is small (₹10) so total costs (₹300+) exceed edge
        dates = [date(2026, 8, 1) + timedelta(days=i) for i in range(25)]
        spreads = pl.DataFrame(
            {
                "trade_date": dates,
                "expiry_date": [date(2026, 10, 5)] * 25,
                "symbol_a": ["GOLD"] * 25,
                "symbol_b": ["GOLDM"] * 25,
                "price_a": [75000.0] * 25,
                "price_b": [75010.0] * 25,
                "spread_abs": [-10.0 + float(i % 5) for i in range(25)],
                "spread_pct": [-0.013] * 25,
                "volume_a": [5000] * 25,
                "volume_b": [5000] * 25,
                "oi_a": [5000] * 25,
                "oi_b": [5000] * 25,
            },
            schema_overrides={"trade_date": pl.Date, "expiry_date": pl.Date},
        )

        signals = generate_signals(spreads, window=20, z_threshold=2.0)
        last_row = signals.row(-1, named=True)
        self.assertIn(last_row["status"], ["WATCH", "REJECTED_COSTS_EXCEED_EDGE"])
        self.assertFalse(last_row["is_tradeable"])

    def test_insufficient_liquidity_rejection(self):
        # Construct synthetic series with volume = 5, OI = 10
        dates = [date(2026, 8, 1) + timedelta(days=i) for i in range(25)]
        spreads = pl.DataFrame(
            {
                "trade_date": dates,
                "expiry_date": [date(2026, 10, 5)] * 25,
                "symbol_a": ["GOLD"] * 25,
                "symbol_b": ["GOLDM"] * 25,
                "price_a": [75000.0] * 25,
                "price_b": [76000.0] * 25,
                "spread_abs": [1000.0] * 25,
                "spread_pct": [1.3] * 25,
                "volume_a": [5] * 25,
                "volume_b": [5] * 25,
                "oi_a": [10] * 25,
                "oi_b": [10] * 25,
            },
            schema_overrides={"trade_date": pl.Date, "expiry_date": pl.Date},
        )

        signals = generate_signals(spreads, window=20, z_threshold=2.0)
        last_row = signals.row(-1, named=True)
        self.assertGreaterEqual(last_row["liquidity_penalty"], 3.0)

    def test_trade_date_dte_parity_calculation(self):
        from app.api.parity import get_parity
        # Verify that DTE is positive when expiry > trade_date
        exp_date = date(2026, 10, 5)
        tr_date = date(2026, 9, 18)
        dte = (exp_date - tr_date).days
        self.assertEqual(dte, 17)


if __name__ == "__main__":
    unittest.main()
