#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# GOLD-X — One-Command Setup
# ═══════════════════════════════════════════════════════════
# Run this once after opening the project in VS Code:
#   chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}   GOLD-X — First-Time Setup                   ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo ""

# ── Step 1: Check prerequisites ──────────────────────────
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found. Install: brew install python@3.11${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Python: $(python3 --version)"

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found. Install: brew install node${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Node: $(node --version)"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found. Install with Node.js${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} npm: $(npm --version)"

# ── Step 2: Check/Setup PostgreSQL ───────────────────────
echo ""
echo -e "${YELLOW}[2/6] Checking PostgreSQL...${NC}"

if command -v psql &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL found: $(psql --version | head -1)"
elif command -v brew &> /dev/null; then
    echo -e "  ${YELLOW}PostgreSQL not found. Installing via Homebrew...${NC}"
    brew install postgresql@16
    echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
    export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
    echo -e "  ${GREEN}✓${NC} PostgreSQL installed"
else
    echo -e "${RED}✗ Neither PostgreSQL nor Homebrew found.${NC}"
    echo "  Install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# Start PostgreSQL if not running
if command -v brew &> /dev/null; then
    brew services start postgresql@16 2>/dev/null || true
    sleep 2
fi

# Create database and user (ignore errors if already exist)
echo -e "  Setting up database..."
createdb goldx 2>/dev/null || echo -e "  ${GREEN}✓${NC} Database 'goldx' already exists"
psql -d goldx -c "DO \$\$ BEGIN CREATE USER goldx WITH PASSWORD 'goldx_dev'; EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;" 2>/dev/null || true
psql -d goldx -c "GRANT ALL PRIVILEGES ON DATABASE goldx TO goldx;" 2>/dev/null || true
psql -d goldx -c "GRANT ALL ON SCHEMA public TO goldx;" 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Database 'goldx' ready with user 'goldx'"

# ── Step 3: Setup Backend ────────────────────────────────
echo ""
echo -e "${YELLOW}[3/6] Setting up Python backend...${NC}"
cd backend

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "  ${GREEN}✓${NC} Virtual environment created"
else
    echo -e "  ${GREEN}✓${NC} Virtual environment exists"
fi

source .venv/bin/activate
pip install -q -r requirements.txt
echo -e "  ${GREEN}✓${NC} Python dependencies installed"
cd ..

# ── Step 4: Setup Frontend ───────────────────────────────
echo ""
echo -e "${YELLOW}[4/6] Setting up React frontend...${NC}"
cd frontend
npm install --silent
echo -e "  ${GREEN}✓${NC} Node dependencies installed"
cd ..

# ── Step 5: Create .env ─────────────────────────────────
echo ""
echo -e "${YELLOW}[5/6] Creating environment file...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "  ${GREEN}✓${NC} .env created from .env.example"
else
    echo -e "  ${GREEN}✓${NC} .env already exists"
fi

# ── Step 6: Make scripts executable ──────────────────────
echo ""
echo -e "${YELLOW}[6/6] Setting permissions...${NC}"
chmod +x scripts/ingest.sh
echo -e "  ${GREEN}✓${NC} Scripts are executable"

# ── Done ─────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Setup Complete!                           ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Now open ${BLUE}two terminals${NC} in VS Code and run:"
echo ""
echo -e "  ${YELLOW}Terminal 1 (Backend):${NC}"
echo -e "    cd backend && source .venv/bin/activate"
echo -e "    uvicorn app.main:app --reload --port 8000"
echo ""
echo -e "  ${YELLOW}Terminal 2 (Frontend):${NC}"
echo -e "    cd frontend && npm run dev"
echo ""
echo -e "  Then open ${BLUE}http://localhost:5173${NC} in your browser"
echo ""
echo -e "  To load MCX data, run in a third terminal:"
echo -e "    ./scripts/ingest.sh 2025-06-01 2025-09-30"
echo ""
