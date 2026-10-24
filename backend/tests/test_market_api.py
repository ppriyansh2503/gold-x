import unittest
from app.db.session import async_session_maker, engine
from app.api.market import get_market_overview, get_system_status


class TestMarketApi(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await engine.dispose()

    async def asyncTearDown(self):
        await engine.dispose()

    async def test_market_overview_logic(self):
        async with async_session_maker() as session:
            data = await get_market_overview(session)
            self.assertIn("status", data)
            if data["status"] == "ok":
                self.assertIsNotNone(data["trade_date"])
                self.assertIsNotNone(data["benchmark_price"])
                self.assertIn("benchmark_contract", data)
                self.assertIn("contracts", data)
                self.assertGreater(data["total_contracts"], 0)
                first_contract = data["contracts"][0]
                self.assertIn("symbol", first_contract)
                self.assertIn("quote_unit", first_contract)
                self.assertIn("purity", first_contract)
                self.assertIn("normalized_price", first_contract)
                self.assertIn("days_to_expiry", first_contract)
                self.assertGreaterEqual(first_contract["days_to_expiry"], 0)

    async def test_system_status_logic(self):
        async with async_session_maker() as session:
            data = await get_system_status(session)
            self.assertIn("status", data)
            self.assertTrue(data.get("database_connected", False))
            self.assertIn("bhavcopy_records", data)
            self.assertIn("normalized_records", data)
            self.assertIn("distinct_trade_dates", data)
            self.assertIn("supported_contracts", data)
            self.assertIn("GOLD", data["supported_contracts"])
            self.assertIn("GOLDM", data["supported_contracts"])


if __name__ == "__main__":
    unittest.main()
