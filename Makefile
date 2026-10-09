.PHONY: help build up down dev logs clean ingest test

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker compose build

up: ## Start all services (production)
	docker compose up -d
	echo "GOLD-X is running at http://localhost:$${WEB_PORT:-80}"

down: ## Stop all services
	docker compose down

dev: ## Start development mode (DB + backend with hot-reload)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db backend
	echo "Backend: http://localhost:8000/docs"
	echo "Start frontend: cd frontend && npm run dev"

logs: ## Follow logs
	docker compose logs -f

clean: ## Remove containers, volumes, and images
	docker compose down -v --rmi local

ingest: ## Ingest today's MCX data
	curl -s -X POST http://localhost:8000/api/ingest \
		-H 'Content-Type: application/json' \
		-d '{"start_date": "'$$(date +%Y-%m-%d)'"}' | python3 -m json.tool

ingest-range: ## Ingest date range (usage: make ingest-range START=2025-01-01 END=2025-09-30)
	curl -s -X POST http://localhost:8000/api/ingest \
		-H 'Content-Type: application/json' \
		-d '{"start_date": "$(START)", "end_date": "$(END)"}' | python3 -m json.tool

import-csv: ## Import local MCX Bhavcopy CSV (usage: make import-csv FILE="data/imports/file.csv")
	@./scripts/import_csv.sh "$(FILE)"

import-all: ## Import all CSV files in data/imports/
	@./scripts/import_csv.sh data/imports/

test: ## Run backend tests
	cd backend && (python3 -m pytest tests/ -v 2>/dev/null || python3 -m unittest discover -s tests -v)

test-docker: ## Run backend tests inside Docker container
	docker exec goldx_backend python -m unittest discover -s tests -v

status: ## Check service health
	@echo "--- Services ---"
	@docker compose ps
	@echo ""
	@echo "--- API Health ---"
	@curl -s http://localhost:8000/ | python3 -m json.tool 2>/dev/null || echo "Backend not reachable"
