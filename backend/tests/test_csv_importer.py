"""Unit tests for local MCX Bhavcopy CSV import workflow."""

import csv
import io
import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.models import Base, DailyBhavcopy, NormalizedPrices
from app.ingestion.csv_importer import (
    parse_and_validate_csv_rows,
    import_csv_file,
    import_csv_files,
    import_path_or_dir,
    ImportSummary,
    BatchImportSummary,
)
from app.config import get_settings

SAMPLE_CSV_HEADER = "Date,Symbol,InstrumentName,ExpiryDate,OptionType,StrikePrice,Open,High,Low,Close,PreviousClose,Volume,Value,OpenInterest\n"

VALID_SYNTHETIC_CSV = SAMPLE_CSV_HEADER + (
    "2099-09-18,GOLD,FUTCOM,05OCT2099,,0.0,152250.0,154600.0,152171.0,154381.0,152981.0,7025,1080570.59,8101\n"
    "2099-09-18,GOLDM,FUTCOM,05OCT2099,,0.0,152434.0,154696.0,152304.0,154467.0,153114.0,52608,809758.91,31588\n"
    "2099-09-18,GOLDGUINEA,FUTCOM,30SEP2099,,0.0,122625.0,124150.0,122321.0,123861.0,122959.0,10595,13089.09,9737\n"
    "2099-09-18,GOLDPETAL,FUTCOM,30SEP2099,,0.0,15360.0,15514.0,15273.0,15480.0,15360.0,258446,39892.25,184129\n"
    "2099-09-18,GOLDTEN,FUTCOM,30SEP2099,,0.0,152960.0,154974.0,152460.0,154617.0,153318.0,28177,43420.53,20605\n"
)

VALID_SYNTHETIC_CSV_DAY2 = SAMPLE_CSV_HEADER + (
    "2099-09-17,GOLD,FUTCOM,05OCT2099,,0.0,151500.0,153200.0,151200.0,152981.0,151800.0,6500,990000.0,7800\n"
    "2099-09-17,GOLDM,FUTCOM,05OCT2099,,0.0,151600.0,153300.0,151350.0,153114.0,151900.0,48000,730000.0,30000\n"
)

MIXED_COMMODITIES_CSV = SAMPLE_CSV_HEADER + (
    "2026-09-18,ALUMINI,FUTCOM,30SEP2026,,0.0,352.85,359.8,339.45,354.05,353.1,6135,21614.22,1559\n"
    "2026-09-18,COPPER,FUTCOM,30SEP2026,,0.0,1393.6,1404.8,1392.9,1403.05,1395.05,7084,247927.76,8631\n"
    "2026-09-18,GOLD,FUTCOM,05OCT2026,,0.0,152250.0,154600.0,152171.0,154381.0,152981.0,7025,1080570.59,8101\n"
    "2026-09-18,SILVER,FUTCOM,04DEC2026,,0.0,91000.0,92500.0,90500.0,92100.0,91200.0,1500,138000.0,2500\n"
)

MALFORMED_DATES_CSV = SAMPLE_CSV_HEADER + (
    "2026-09-18,GOLD,FUTCOM,05OCT2026,,0.0,152250.0,154600.0,152171.0,154381.0,152981.0,7025,1080570.59,8101\n"
    "invalid-date,GOLDM,FUTCOM,05OCT2026,,0.0,152434.0,154696.0,152304.0,154467.0,153114.0,52608,809758.91,31588\n"
    "2026-09-18,GOLDGUINEA,FUTCOM,bad-expiry,,0.0,122625.0,124150.0,122321.0,123861.0,122959.0,10595,13089.09,9737\n"
)

ZERO_AND_MISSING_CLOSES_CSV = SAMPLE_CSV_HEADER + (
    "2099-09-18,GOLD,FUTCOM,05OCT2099,,0.0,152250.0,154600.0,152171.0,154381.0,152981.0,7025,1080570.59,8101\n"
    "2099-09-18,GOLDM,FUTCOM,05NOV2099,,0.0,0.0,0.0,0.0,0.0,153898.0,0,0.0,0\n"
    "2099-09-18,GOLDTEN,FUTCOM,30NOV2099,,0.0,0.0,0.0,0.0,,155020.0,0,0.0,0\n"
)


class TestCsvImporterValidation(unittest.TestCase):
    """Test CSV parsing, filtering, and validation without requiring a database."""

    def test_parse_valid_gold_rows(self):
        reader = csv.DictReader(io.StringIO(VALID_SYNTHETIC_CSV))
        records, total_read, gold_found, error_rows, errors = parse_and_validate_csv_rows(reader)

        self.assertEqual(total_read, 5)
        self.assertEqual(gold_found, 5)
        self.assertEqual(error_rows, 0)
        self.assertEqual(len(records), 5)
        self.assertEqual(len(errors), 0)

        # Verify parsed types
        first = records[0]
        self.assertEqual(first["symbol"], "GOLD")
        self.assertEqual(first["trade_date"], date(2099, 9, 18))
        self.assertEqual(first["expiry_date"], date(2099, 10, 5))
        self.assertEqual(first["close"], 154381.0)
        self.assertEqual(first["volume"], 7025)
        self.assertEqual(first["open_interest"], 8101)

    def test_unsupported_symbols_skipped(self):
        reader = csv.DictReader(io.StringIO(MIXED_COMMODITIES_CSV))
        records, total_read, gold_found, error_rows, errors = parse_and_validate_csv_rows(reader)

        self.assertEqual(total_read, 4)
        self.assertEqual(gold_found, 1)  # Only GOLD
        self.assertEqual(error_rows, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["symbol"], "GOLD")

    def test_malformed_dates_handled_safely(self):
        reader = csv.DictReader(io.StringIO(MALFORMED_DATES_CSV))
        records, total_read, gold_found, error_rows, errors = parse_and_validate_csv_rows(reader)

        self.assertEqual(total_read, 3)
        self.assertEqual(gold_found, 3)  # 3 gold rows identified
        self.assertEqual(error_rows, 2)  # 2 had bad dates
        self.assertEqual(len(records), 1)  # 1 valid record preserved
        self.assertEqual(records[0]["symbol"], "GOLD")
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("Invalid trade date" in e for e in errors))
        self.assertTrue(any("Invalid expiry date" in e for e in errors))


class TestCsvImporterDatabase(unittest.IsolatedAsyncioTestCase):
    """Test database ingestion, upsert idempotency, and normalization."""

    async def asyncSetUp(self):
        settings = get_settings()
        self.engine = create_async_engine(settings.DATABASE_URL, echo=False)
        self.session_maker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.execute(text("DELETE FROM normalized_prices WHERE trade_date >= '2099-01-01'"))
            await conn.execute(text("DELETE FROM daily_bhavcopy WHERE trade_date >= '2099-01-01'"))
        await self.engine.dispose()

    async def test_full_import_and_normalization(self):
        async with self.session_maker() as session:
            stream = io.StringIO(VALID_SYNTHETIC_CSV)
            summary = await import_csv_file(stream, session)

            self.assertEqual(summary.status, "ok")
            self.assertEqual(summary.total_rows_read, 5)
            self.assertEqual(summary.gold_rows_found, 5)
            self.assertEqual(summary.daily_bhavcopy_upserted, 5)
            self.assertEqual(summary.normalized_prices_upserted, 5)
            self.assertEqual(summary.error_rows, 0)

            # Query normalized_prices from database
            stmt = select(NormalizedPrices).where(NormalizedPrices.trade_date == date(2099, 9, 18))
            res = await session.execute(stmt)
            norm_rows = {(r.symbol, r.expiry_date): r for r in res.scalars().all()}

            # Verify normalization values for specific contracts:
            # GOLD (05OCT2099): 154381.0 * 1.0 * (999/995) = 155001.6261
            gold = norm_rows[("GOLD", date(2099, 10, 5))]
            expected_gold = round(154381.0 * (999.0 / 995.0), 4)
            self.assertAlmostEqual(float(gold.norm_close_10g_999), expected_gold, places=2)

            # GOLDGUINEA (30SEP2099): 8g quote -> 123861.0 * 1.25 = 154826.25
            guinea = norm_rows[("GOLDGUINEA", date(2099, 9, 30))]
            self.assertAlmostEqual(float(guinea.norm_close_10g_999), 123861.0 * 1.25, places=2)

            # GOLDPETAL (30SEP2099): 1g quote -> 15480.0 * 10 = 154800.0
            petal = norm_rows[("GOLDPETAL", date(2099, 9, 30))]
            self.assertAlmostEqual(float(petal.norm_close_10g_999), 15480.0 * 10.0, places=2)

            # GOLDTEN (30SEP2099): baseline 10g 999 -> 154617.0
            ten = norm_rows[("GOLDTEN", date(2099, 9, 30))]
            self.assertAlmostEqual(float(ten.norm_close_10g_999), 154617.0, places=2)

    async def test_duplicate_import_idempotency(self):
        """Repeated imports of the same CSV should not create duplicate rows."""
        async with self.session_maker() as session:
            # Import first time
            summary1 = await import_csv_file(io.StringIO(VALID_SYNTHETIC_CSV), session)
            self.assertEqual(summary1.status, "ok")

            count1 = await session.scalar(
                text("SELECT count(*) FROM normalized_prices WHERE trade_date = '2099-09-18'")
            )

            # Import second time
            summary2 = await import_csv_file(io.StringIO(VALID_SYNTHETIC_CSV), session)
            self.assertEqual(summary2.status, "ok")

            count2 = await session.scalar(
                text("SELECT count(*) FROM normalized_prices WHERE trade_date = '2099-09-18'")
            )

            # Count must remain exactly the same
            self.assertEqual(count1, count2)

    async def test_zero_and_missing_closes_excluded_from_normalized(self):
        """Zero or missing close prices must be recorded in daily_bhavcopy but excluded from normalized_prices."""
        async with self.session_maker() as session:
            summary = await import_csv_file(io.StringIO(ZERO_AND_MISSING_CLOSES_CSV), session)

            self.assertEqual(summary.status, "ok")
            self.assertEqual(summary.daily_bhavcopy_upserted, 3)
            # Only the 1 row with close > 0 is normalized
            self.assertEqual(summary.normalized_prices_upserted, 1)

            # Check that normalized_prices only contains the non-zero contract
            res = await session.execute(
                select(NormalizedPrices).where(
                    NormalizedPrices.trade_date == date(2099, 9, 18),
                    NormalizedPrices.symbol.in_(["GOLD", "GOLDM", "GOLDTEN"]),
                )
            )
            symbols_in_norm = [r.symbol for r in res.scalars().all()]
            self.assertIn("GOLD", symbols_in_norm)

    async def test_batch_import_multiple_dates_and_idempotency(self):
        """Import multiple dates, verify distinct trade dates, and confirm duplicate import idempotency."""
        async with self.session_maker() as session:
            # 1. Import day 1 (2099-09-18)
            summary1 = await import_csv_file(io.StringIO(VALID_SYNTHETIC_CSV), session)
            self.assertEqual(summary1.status, "ok")

            # 2. Import day 2 (2099-09-17)
            summary2 = await import_csv_file(io.StringIO(VALID_SYNTHETIC_CSV_DAY2), session)
            self.assertEqual(summary2.status, "ok")

            # Verify both dates exist in normalized_prices
            res = await session.execute(
                select(NormalizedPrices.trade_date).distinct().order_by(NormalizedPrices.trade_date)
            )
            distinct_dates = [d[0] for d in res.all()]
            self.assertIn(date(2099, 9, 17), distinct_dates)
            self.assertIn(date(2099, 9, 18), distinct_dates)

            # Get current count for both dates
            count_day1 = await session.scalar(
                text("SELECT count(*) FROM normalized_prices WHERE trade_date = '2099-09-18'")
            )
            count_day2 = await session.scalar(
                text("SELECT count(*) FROM normalized_prices WHERE trade_date = '2099-09-17'")
            )

            # 3. Re-import day 2 — must remain identical (idempotent, 0 duplicates)
            summary2_repeat = await import_csv_file(io.StringIO(VALID_SYNTHETIC_CSV_DAY2), session)
            self.assertEqual(summary2_repeat.status, "ok")

            count_day2_repeat = await session.scalar(
                text("SELECT count(*) FROM normalized_prices WHERE trade_date = '2099-09-17'")
            )
            self.assertEqual(count_day2, count_day2_repeat)

    async def test_import_path_or_dir_missing_handling(self):
        """Verify error handling when a non-existent file or empty directory is passed."""
        async with self.session_maker() as session:
            res = await import_path_or_dir("completely_bogus_dir_or_file_12345", session)
            self.assertEqual(res.status, "error")


if __name__ == "__main__":
    unittest.main()
