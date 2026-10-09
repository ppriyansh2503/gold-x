#!/usr/bin/env bash
# GOLD-X Local Bhavcopy CSV Import Helper
# Usage:
#   ./scripts/import_csv.sh                                # imports all CSVs in data/imports/
#   ./scripts/import_csv.sh "data/imports/mcx_20260918.csv" # imports a single file
#   ./scripts/import_csv.sh data/imports/*.csv             # imports multiple files
#   ./scripts/import_csv.sh data/imports/                  # imports entire directory

set -euo pipefail

TARGETS=("$@")

if [ ${#TARGETS[@]} -eq 0 ]; then
    if [ -d "data/imports" ]; then
        echo "No arguments provided. Scanning 'data/imports/' for CSV files..."
        TARGETS=("data/imports")
    else
        echo "Usage: $0 <path-to-csv-file-or-dir> [additional-files...]"
        echo "Example: $0 \"data/imports/mcx_20260918 (1).csv\""
        echo "Example: $0 data/imports/"
        exit 1
    fi
fi

API_URL="${GOLDX_API:-http://localhost:8000}"

# If Docker container is running, execute importer inside container
if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "^goldx_backend$"; then
    echo "Running import via goldx_backend container..."
    for item in "${TARGETS[@]}"; do
        if [ -d "$item" ]; then
            # Directory: pass container-mounted path /app/data/... if relative to data/
            if [[ "$item" == data/* ]] || [[ "$item" == ./data/* ]]; then
                cont_path="/app/${item#./}"
                docker exec goldx_backend python -m app.ingestion.csv_importer "$cont_path"
            else
                for f in "$item"/*.csv "$item"/*.CSV; do
                    [ -f "$f" ] || continue
                    echo "Importing $f..."
                    docker exec -i goldx_backend python -m app.ingestion.csv_importer - < "$f"
                done
            fi
        elif [ -f "$item" ]; then
            echo "Importing $item..."
            docker exec -i goldx_backend python -m app.ingestion.csv_importer - < "$item"
        else
            echo "Warning: '$item' not found, skipping."
        fi
    done
else
    # Fallback to API endpoint
    echo "Docker container not running. Posting to $API_URL/api/ingest/csv..."
    for item in "${TARGETS[@]}"; do
        curl -s -X POST "$API_URL/api/ingest/csv" \
            -H 'Content-Type: application/json' \
            -d "{\"file_path\": \"$item\"}" | python3 -m json.tool
    done
fi
