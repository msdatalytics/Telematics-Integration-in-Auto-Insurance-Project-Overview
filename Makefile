# Telematics UBI Development Makefile

.PHONY: help up down logs seed train eval score test fmt lint clean export-data

# Default target
help:
	@echo "Telematics UBI Development Commands:"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View service logs"
	@echo "  make seed        - Generate sample data"
	@echo "  make train       - Train ML models"
	@echo "  make eval        - Evaluate models"
	@echo "  make score       - Compute daily scores"
	@echo "  make test        - Run all tests"
	@echo "  make fmt         - Format code"
	@echo "  make lint        - Lint code"
	@echo "  make clean       - Clean up containers and volumes"
	@echo "  make export-data - Export data for submission"

# Docker Compose commands
up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started. API: http://localhost:8000, Frontend: http://localhost:5173"

down:
	@echo "Stopping all services..."
	docker-compose down

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-frontend:
	docker-compose logs -f frontend

logs-db:
	docker-compose logs -f db

logs-redis:
	docker-compose logs -f redis

# Data and ML commands
seed:
	@echo "Seeding sample data..."
	docker-compose exec api python -m src.backend.db.seed
	@echo "Sample data created successfully"

train:
	@echo "Training ML models..."
	docker-compose exec api python -m src.backend.ml.train
	@echo "Model training completed"

eval:
	@echo "Evaluating models..."
	docker-compose exec api python -m src.backend.ml.evaluate
	@echo "Model evaluation completed"

score:
	@echo "Computing daily risk scores..."
	docker-compose exec api python -m src.backend.ml.score_service --compute-daily
	@echo "Daily scoring completed"

# Development commands
test:
	@echo "Running tests..."
	docker-compose exec api python -m pytest tests/ -v
	docker-compose exec frontend npm test

test-api:
	docker-compose exec api python -m pytest tests/backend/ -v

test-ml:
	docker-compose exec api python -m pytest tests/backend/test_features.py tests/backend/test_ml.py -v

test-pricing:
	docker-compose exec api python -m pytest tests/backend/test_pricing.py -v

fmt:
	@echo "Formatting code..."
	docker-compose exec api python -m ruff format src/
	docker-compose exec api python -m ruff check --fix src/
	docker-compose exec frontend npm run format

lint:
	@echo "Linting code..."
	docker-compose exec api python -m ruff check src/
	docker-compose exec frontend npm run lint

# Utility commands
clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker system prune -f

restart:
	@echo "Restarting services..."
	docker-compose restart

rebuild:
	@echo "Rebuilding services..."
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

# Data export for submission
export-data:
	@echo "Exporting data for submission..."
	@mkdir -p export
	@cp -r src/ export/
	@cp -r docs/ export/
	@cp -r models/ export/
	@cp -r data/ export/
	@cp README.md export/
	@cp compose.yaml export/
	@cp Makefile export/
	@echo "Data exported to export/ directory"

# Development setup
setup:
	@echo "Setting up development environment..."
	cp env.example .env
	docker-compose up -d
	sleep 10
	make seed
	make train
	make eval
	@echo "Development environment ready!"

# Production-like testing
prod-test:
	@echo "Running production-like tests..."
	docker-compose -f compose.yaml -f compose.prod.yaml up -d
	sleep 15
	make test
	docker-compose -f compose.yaml -f compose.prod.yaml down

# Database operations
db-migrate:
	docker-compose exec api python -m src.backend.db.migrate

db-reset:
	docker-compose exec api python -m src.backend.db.reset

# Monitoring
monitor:
	@echo "Starting monitoring services..."
	docker-compose up -d prometheus grafana
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"

# Stream processing
start-producer:
	docker-compose exec api python -m src.backend.stream.producer --users 50 --trips 500

start-consumer:
	docker-compose exec api python -m src.backend.stream.consumer

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "API not healthy"
	@curl -f http://localhost:5173 || echo "Frontend not healthy"
	@docker-compose exec db pg_isready || echo "Database not healthy"
	@docker-compose exec redis redis-cli ping || echo "Redis not healthy"
