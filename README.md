# GOLD-X — Quantitative Parity Intelligence Platform

A quantitative intelligence platform that analyzes MCX gold commodity futures
to identify relative pricing differences between contracts representing the
same underlying metal.

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  MCX Bhavcopy│───▶│ Polars + DB  │───▶│   FastAPI     │───▶│  React/Vite  │
│  (Data Feed) │    │ (PostgreSQL) │    │  (REST API)   │    │  (Dashboard) │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

## Gold Contract Normalization

All prices are normalized to **10g of 999-purity gold**:

| Contract    | Quote Unit | Purity | Multiplier              |
|-------------|-----------|--------|-------------------------|
| GOLD        | 10g       | 995    | × (999/995) = 1.00402   |
| GOLDM       | 10g       | 995    | × (999/995) = 1.00402   |
| GOLDTEN     | 10g       | 999    | × 1.0 (baseline)        |
| GOLDGUINEA  | 8g        | 999    | × (10/8) = 1.25         |
| GOLDPETAL   | 1g        | 999    | × (10/1) = 10.0         |

**Formula:** `P_norm = P_raw × (10 / quote_unit_grams) × (999 / purity)`

## Prerequisites

- Docker & Docker Compose (for deployment)
- Python 3.11+ (for local development)
- Node.js 18+ (for local frontend development)

---

## 🚀 Production Deployment (Docker)

```bash
# 1. Clone and configure
git clone <repo-url> && cd mcx
cp .env.example .env
# Edit .env — change POSTGRES_PASSWORD for production!

# 2. Build and start all services
make build
make up

# 3. Ingest MCX Data
# Option A: Local CSV Import (Recommended when online MCX endpoint returns 403)
make import-csv FILE="data/imports/mcx_20260918 (1).csv"
# Or using the helper script:
./scripts/import_csv.sh "data/imports/mcx_20260918 (1).csv"

# Option B: Online MCX Ingestion (Requires WAF bypass/broker API if direct requests return 403)
make ingest                                           # Today
make ingest-range START=2025-01-01 END=2026-09-30     # Date range
```

**Dashboard:** http://localhost  
**API Docs:** http://localhost:8000/docs  

### Docker Services

| Service   | Container        | Port | Description                    |
|-----------|-----------------|------|--------------------------------|
| db        | goldx_db        | 5432 | PostgreSQL 16 (Alpine)         |
| backend   | goldx_backend   | 8000 | FastAPI (4 Uvicorn workers)    |
| frontend  | goldx_frontend  | 80   | Nginx serving React SPA        |

### Make Commands

```
make help           # Show all available commands
make build          # Build all Docker images
make up             # Start production stack
make down           # Stop all services
make dev            # Start DB + backend with hot-reload
make logs           # Follow container logs
make clean          # Remove containers, volumes, and images
make ingest         # Ingest today's MCX data
make ingest-range   # Ingest date range
make import-csv     # Import local Bhavcopy CSV (usage: make import-csv FILE=data/imports/file.csv)
make status         # Check service health
make test           # Run backend tests
make test-docker    # Run backend tests inside Docker container
```

---

## 🛠️ Local Development

```bash
# 1. Start PostgreSQL
make dev
# Or manually: docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db backend

# 2. Backend (if not using Docker)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
npm run dev
```

**Dashboard:** http://localhost:5173  
**API Docs:** http://localhost:8000/docs  

---

## API Endpoints

| Endpoint                             | Method | Description                              |
|--------------------------------------|--------|------------------------------------------|
| `/api/parity`                        | GET    | Latest normalized prices & spread matrix |
| `/api/parity/history`                | GET    | Historical spread time series            |
| `/api/signals`                       | GET    | Current signals with cost autopsy        |
| `/api/signals/history`               | GET    | Signal history                           |
| `/api/backtest-performance`          | GET    | Full backtest results                    |
| `/api/backtest-performance/summary`  | GET    | High-level backtest stats                |
| `/api/ingest`                        | POST   | Trigger online data ingestion            |
| `/api/ingest/csv`                    | POST   | Trigger local Bhavcopy CSV import        |

## Signal Logic

1. Compute pairwise spreads between contracts sharing the same expiry
2. Calculate rolling Z-score (default window = 20 trading days)
3. Deduct full round-trip transaction costs (exchange fees, STT, GST, brokerage, slippage)
4. Apply liquidity penalty based on volume and open interest
5. **Net Edge = Gross Spread − Total Costs**
6. If net edge ≤ 0 → **NO TRADE** (with full cost autopsy)

## Project Structure

```
mcx/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── app/
│       ├── main.py              # FastAPI entry point
│       ├── config.py            # Pydantic settings
│       ├── db/                  # PostgreSQL models & session
│       ├── ingestion/           # MCX data pipeline
│       ├── quant/               # Spreads, signals, costs, backtester
│       └── api/                 # REST endpoints
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── components/          # Dashboard, Radar, Signals, Lifecycle
│       ├── hooks/               # useApi data fetching
│       └── styles/              # Dark theme CSS
├── scripts/
│   └── ingest.sh               # Data ingestion helper
├── docker-compose.yml           # Production stack
├── docker-compose.dev.yml       # Development override
├── Makefile                     # Build & deploy commands
├── .env.example                 # Environment template
└── README.md
```

## Tech Stack

- **Data Engine:** Python 3.11, Polars, SciPy
- **Database:** PostgreSQL 16
- **Backend:** FastAPI (async), SQLAlchemy 2.0, httpx
- **Frontend:** React 18, Vite, pure CSS (Flexbox)
- **Deployment:** Docker, Nginx, multi-stage builds

## License

Private — Internal Use Only
