import unittest
import polars as pl
from app.ingestion.normalizer import (
    get_multipliers,
    normalize_price,
    normalize_dataframe,
)


class TestNormalizer(unittest.TestCase):
    def test_multipliers(self):
        # GOLD: 10g quote, 995 purity -> unit=1.0, purity=999/995
        u, p = get_multipliers("GOLD")
        self.assertAlmostEqual(u, 1.0)
        self.assertAlmostEqual(p, 999.0 / 995.0, places=5)

        # GOLDGUINEA: 8g quote, 999 purity -> unit=10/8=1.25, purity=1.0
        u, p = get_multipliers("GOLDGUINEA")
        self.assertAlmostEqual(u, 1.25)
        self.assertAlmostEqual(p, 1.0)

        # GOLDPETAL: 1g quote, 999 purity -> unit=10/1=10.0, purity=1.0
        u, p = get_multipliers("GOLDPETAL")
        self.assertAlmostEqual(u, 10.0)
        self.assertAlmostEqual(p, 1.0)

        # GOLDTEN: 10g quote, 999 purity -> unit=1.0, purity=1.0
        u, p = get_multipliers("GOLDTEN")
        self.assertAlmostEqual(u, 1.0)
        self.assertAlmostEqual(p, 1.0)

    def test_normalize_price(self):
        # 1g petal at ₹7,500 should normalize to ₹75,000 for 10g
        norm = normalize_price("GOLDPETAL", 7500.0)
        self.assertAlmostEqual(norm, 75000.0)

        # 8g guinea at ₹60,000 should normalize to ₹75,000 for 10g
        norm = normalize_price("GOLDGUINEA", 60000.0)
        self.assertAlmostEqual(norm, 75000.0)

    def test_normalize_dataframe(self):
        df = pl.DataFrame({
            "symbol": ["GOLD", "GOLDM", "GOLDGUINEA", "GOLDPETAL", "GOLDTEN"],
            "close": [75000.0, 75050.0, 60000.0, 7500.0, 75100.0],
        })

        norm_df = normalize_dataframe(df)

        self.assertIn("norm_close_10g_999", norm_df.columns)
        self.assertIn("unit_multiplier", norm_df.columns)
        self.assertIn("purity_multiplier", norm_df.columns)
        self.assertEqual(norm_df.height, 5)

        # Verify petal normalized close
        petal_row = norm_df.filter(pl.col("symbol") == "GOLDPETAL").row(0, named=True)
        self.assertAlmostEqual(petal_row["norm_close_10g_999"], 75000.0)

        # Verify guinea normalized close
        guinea_row = norm_df.filter(pl.col("symbol") == "GOLDGUINEA").row(0, named=True)
        self.assertAlmostEqual(guinea_row["norm_close_10g_999"], 75000.0)


if __name__ == "__main__":
    unittest.main()
