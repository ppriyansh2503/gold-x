#!/usr/bin/env bash
# GOLD-X Data Ingestion Helper
# Usage:
#   ./scripts/ingest.sh                    # Ingest today
#   ./scripts/ingest.sh 2025-09-01         # Ingest specific date
#   ./scripts/ingest.sh 2025-01-01 2025-09-30  # Ingest range

set -euo pipefail

API_URL="${GOLDX_API:-http://localhost:8000}"

if [ $# -eq 0 ]; then
    DATE=$(date +%Y-%m-%d)
    echo "Ingesting today ($DATE)..."
    curl -s -X POST "$API_URL/api/ingest" \
        -H 'Content-Type: application/json' \
        -d "{\"start_date\": \"$DATE\"}" | python3 -m json.tool
elif [ $# -eq 1 ]; then
    echo "Ingesting $1..."
    curl -s -X POST "$API_URL/api/ingest" \
        -H 'Content-Type: application/json' \
        -d "{\"start_date\": \"$1\"}" | python3 -m json.tool
elif [ $# -eq 2 ]; then
    echo "Ingesting $1 to $2..."
    curl -s -X POST "$API_URL/api/ingest" \
        -H 'Content-Type: application/json' \
        -d "{\"start_date\": \"$1\", \"end_date\": \"$2\"}" | python3 -m json.tool
else
    echo "Usage: $0 [start_date] [end_date]"
    exit 1
fi
