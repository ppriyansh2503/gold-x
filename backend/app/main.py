"""FastAPI application entry point for GOLD-X."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import init_db, get_async_session
from app.api.parity import router as parity_router
from app.api.signals import router as signals_router
from app.api.backtest import router as backtest_router
from app.ingestion.bhavcopy import ingest_date, ingest_date_range
from app.ingestion.csv_importer import import_csv_file, import_path_or_dir

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("GOLD-X backend started.")
    yield
    logger.info("GOLD-X backend shutting down.")


app = FastAPI(
    title="GOLD-X",
    description="Quantitative Parity Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parity_router)
app.include_router(signals_router)
app.include_router(backtest_router)


@app.get("/")
async def root():
    return {"service": "GOLD-X", "version": "1.0.0"}


# ── Ingestion endpoint ────────────────────────────────────────────────


class IngestRequest(BaseModel):
    start_date: date
    end_date: date | None = None


@app.post("/api/ingest")
@app.post("/api/ingest/", include_in_schema=False)
async def trigger_ingestion(
    req: IngestRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Trigger data ingestion for a single date or a date range."""
    end = req.end_date or req.start_date
    if end < req.start_date:
        raise HTTPException(400, "end_date must be >= start_date")
    if (end - req.start_date).days > 365:
        raise HTTPException(400, "Maximum ingestion range is 365 days")

    try:
        if req.start_date == end:
            count = await ingest_date(req.start_date, session)
            return {
                "status": "ok",
                "date": req.start_date.isoformat(),
                "records_ingested": count,
            }
        else:
            summary = await ingest_date_range(req.start_date, end, session)
            return {"status": "ok", **summary}
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(500, f"Ingestion error: {e}")


class CsvImportRequest(BaseModel):
    file_path: str


@app.post("/api/ingest/csv")
@app.post("/api/ingest/csv/", include_in_schema=False)
async def trigger_csv_ingestion(
    req: CsvImportRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Import a local MCX Bhavcopy CSV file into PostgreSQL."""
    try:
        summary = await import_path_or_dir(req.file_path, session)
        if summary.status not in ("ok", "partial"):
            raise HTTPException(400, f"CSV import error: {summary.errors}")
        return summary.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("CSV import failed")
        raise HTTPException(500, f"CSV import error: {e}")
