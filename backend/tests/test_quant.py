import unittest
from datetime import date, timedelta
import polars as pl
from app.quant.spreads import compute_pairwise_spreads, compute_spread_timeseries
from app.quant.costs import round_trip_cost, liquidity_penalty, net_edge
from app.quant.signals import rolling_zscore, generate_signals
from app.quant.backtester import BacktestEngine


class TestQuantEngine(unittest.TestCase):
    def test_cost_model(self):
        costs = round_trip_cost(75000.0, 75100.0)
        self.assertIn("exchange_fee", costs)
        self.assertIn("brokerage", costs)
        self.assertIn("stt", costs)
        self.assertIn("gst", costs)
        self.assertIn("slippage", costs)
        self.assertIn("total_cost", costs)
        self.assertGreater(costs["total_cost"], 0)

        # Flat brokerage is ₹40 total (₹20 per side)
        self.assertEqual(costs["brokerage"], 40.0)

    def test_liquidity_penalty(self):
        # High volume & OI -> penalty = 1.0
        self.assertEqual(liquidity_penalty(2000, 2000), 1.0)
        # Low volume (<100) -> penalty base 3.0 + 0.5 (low OI) = 3.5
        self.assertEqual(liquidity_penalty(50, 100), 3.5)

    def test_net_edge(self):
        # Gross spread of ₹10 vs large costs -> is_tradeable False
        edge_small = net_edge(gross_spread=10.0, entry_price=75000.0, volume=1000, open_interest=1000)
        self.assertFalse(edge_small["is_tradeable"])
        self.assertLess(edge_small["net_edge"], 0)

        # Huge gross spread of ₹1000 -> is_tradeable True
        edge_large = net_edge(gross_spread=1000.0, entry_price=75000.0, volume=1000, open_interest=1000)
        self.assertTrue(edge_large["is_tradeable"])
        self.assertGreater(edge_large["net_edge"], 0)

    def test_compute_pairwise_spreads(self):
        df = pl.DataFrame({
            "trade_date": [date(2025, 1, 15), date(2025, 1, 15)],
            "symbol": ["GOLD", "GOLDM"],
            "expiry_date": [date(2025, 2, 5), date(2025, 2, 5)],
            "norm_close_10g_999": [75300.0, 75350.0],
            "volume": [1000, 2000],
            "open_interest": [5000, 6000],
        })

        spreads = compute_pairwise_spreads(df)
        self.assertEqual(spreads.height, 1)
        row = spreads.row(0, named=True)
        self.assertEqual(row["symbol_a"], "GOLD")
        self.assertEqual(row["symbol_b"], "GOLDM")
        self.assertAlmostEqual(row["spread_abs"], -50.0)

    def test_generate_signals_synthetic_data(self):
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(30)]
        rows = []
        for i, d in enumerate(dates):
            # Introduce a large spread divergence on day 25
            spread_offset = 800.0 if i >= 25 else 50.0
            rows.append({
                "trade_date": d,
                "symbol": "GOLD",
                "expiry_date": date(2025, 3, 5),
                "norm_close_10g_999": 75000.0,
                "volume": 2000,
                "open_interest": 5000,
            })
            rows.append({
                "trade_date": d,
                "symbol": "GOLDM",
                "expiry_date": date(2025, 3, 5),
                "norm_close_10g_999": 75000.0 + spread_offset,
                "volume": 2000,
                "open_interest": 5000,
            })

        df = pl.DataFrame(rows)
        spreads = compute_pairwise_spreads(df)
        signals = generate_signals(spreads, window=20, z_threshold=2.0)

        self.assertEqual(signals.height, 30)
        # Early days should have NO_TRADE
        self.assertEqual(signals.row(5, named=True)["signal"], "NO_TRADE")
        # Day 26 should trigger a trade because spread jumped from 50 to 800 with high volume
        late_row = signals.row(26, named=True)
        self.assertIn(late_row["signal"], ["BUY_SPREAD", "SELL_SPREAD"])
        self.assertTrue(late_row["is_tradeable"])

    def test_backtest_engine_synthetic_data(self):
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(40)]
        rows = []
        for i, d in enumerate(dates):
            # Spread widens at i=22 then reverts at i=28
            spread_offset = 500.0 if 22 <= i <= 27 else 0.0
            rows.append({
                "trade_date": d,
                "symbol": "GOLD",
                "expiry_date": date(2025, 4, 5),
                "norm_close_10g_999": 75000.0,
                "volume": 2000,
                "open_interest": 5000,
            })
            rows.append({
                "trade_date": d,
                "symbol": "GOLDM",
                "expiry_date": date(2025, 4, 5),
                "norm_close_10g_999": 75000.0 + spread_offset,
                "volume": 2000,
                "open_interest": 5000,
            })

        df = pl.DataFrame(rows)
        engine = BacktestEngine(df)
        res = engine.run(window=20, z_threshold=2.0, exit_z=0.5)

        self.assertGreater(res.total_signals, 0)
        self.assertIsInstance(res.to_dict(), dict)


if __name__ == "__main__":
    unittest.main()
