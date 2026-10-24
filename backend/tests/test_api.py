import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


class TestApiRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._init_db_patch = patch("app.main.init_db", new_callable=AsyncMock)
        cls._init_db_patch.start()
        cls._client_ctx = TestClient(app)
        cls.client = cls._client_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._client_ctx.__exit__(None, None, None)
        cls._init_db_patch.stop()

    def test_root(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"service": "GOLD-X", "version": "1.0.0"})

    def test_parity_trailing_slash_handling(self):
        # Both without and with slash must return 200 directly without 307 redirect
        res_no_slash = self.client.get("/api/parity", follow_redirects=False)
        self.assertEqual(res_no_slash.status_code, 200)

        res_slash = self.client.get("/api/parity/", follow_redirects=False)
        self.assertEqual(res_slash.status_code, 200)

    def test_signals_trailing_slash_handling(self):
        # Both without and with slash must return 200 directly without 307 redirect
        res_no_slash = self.client.get("/api/signals", follow_redirects=False)
        self.assertEqual(res_no_slash.status_code, 200)

        res_slash = self.client.get("/api/signals/", follow_redirects=False)
        self.assertEqual(res_slash.status_code, 200)

    def test_backtest_trailing_slash_handling(self):
        # Both without and with slash must return 200 directly without 307 redirect
        res_no_slash = self.client.get("/api/backtest-performance", follow_redirects=False)
        self.assertEqual(res_no_slash.status_code, 200)

        res_slash = self.client.get("/api/backtest-performance/", follow_redirects=False)
        self.assertEqual(res_slash.status_code, 200)

        # Summary route
        res_summary = self.client.get("/api/backtest-performance/summary", follow_redirects=False)
        self.assertEqual(res_summary.status_code, 200)
        self.assertIn(res_summary.json().get("status"), ["no_data", "insufficient_data"])

    def test_csv_ingest_endpoint(self):
        # Invalid path returns 400 with detail
        res = self.client.post("/api/ingest/csv", json={"file_path": "non_existent.csv"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("File not found", res.json().get("detail", ""))

    def test_market_overview_endpoint(self):
        res = self.client.get("/api/market-overview")
        self.assertEqual(res.status_code, 200)
        self.assertIn("status", res.json())

    def test_system_status_endpoint(self):
        res = self.client.get("/api/system/status")
        self.assertEqual(res.status_code, 200)
        self.assertIn("status", res.json())


if __name__ == "__main__":
    unittest.main()
