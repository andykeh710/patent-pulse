.PHONY: up down build logs shell test migrate seed clean

# Start all services
up:
	docker compose up -d

# Start with logs
up-logs:
	docker compose up

# Stop all services
down:
	docker compose down

# Rebuild all images
build:
	docker compose build

# View logs
logs:
	docker compose logs -f

# View specific service logs
logs-%:
	docker compose logs -f $*

# Shell into backend container
shell:
	docker compose exec backend bash

# Shell into frontend container
shell-frontend:
	docker compose exec frontend sh

# Run backend tests
test:
	docker compose exec backend pytest

# Run backend tests with coverage
test-cov:
	docker compose exec backend pytest --cov=app --cov-report=html

# Run frontend tests
test-frontend:
	docker compose exec frontend npm test

# Run alembic migrations
migrate:
	docker compose exec backend alembic upgrade head

# Create new migration
migration:
	@read -p "Migration message: " msg; \
	docker compose exec backend alembic revision --autogenerate -m "$$msg"

# Run linting
lint:
	docker compose exec backend ruff check app
	docker compose exec frontend npm run lint

# Format code
format:
	docker compose exec backend ruff format app

# Reset database
reset-db:
	docker compose down -v
	docker compose up -d db
	sleep 3
	docker compose exec backend alembic upgrade head

# Install backend dependencies locally (for IDE support)
install-local:
	cd backend && poetry install

# Install frontend dependencies locally
install-frontend:
	cd frontend && npm install

# Clean up
clean:
	docker compose down -v --rmi local
	rm -rf backend/.pytest_cache backend/.coverage backend/htmlcov
	rm -rf frontend/.next frontend/node_modules

# Export pip requirements from poetry.lock (prod + dev split)
deps-export:
	cd backend && poetry export --without-hashes -f requirements.txt -o requirements.txt
	cd backend && poetry export --without-hashes --only dev -f requirements.txt -o requirements-dev.txt
	@echo "requirements.txt ($(shell wc -l < backend/requirements.txt) lines)"
	@echo "requirements-dev.txt ($(shell wc -l < backend/requirements-dev.txt) lines)"

# CI check: fail if requirements.txt is stale relative to poetry.lock
deps-check:
	cd backend && poetry export --without-hashes -f requirements.txt -o /tmp/req-check.txt
	cd backend && poetry export --without-hashes --only dev -f requirements.txt -o /tmp/req-dev-check.txt
	diff backend/requirements.txt /tmp/req-check.txt || (echo "ERROR: requirements.txt is stale — run 'make deps-export'" && exit 1)
	diff backend/requirements-dev.txt /tmp/req-dev-check.txt || (echo "ERROR: requirements-dev.txt is stale — run 'make deps-export'" && exit 1)
	@rm -f /tmp/req-check.txt /tmp/req-dev-check.txt
	@echo "requirements.txt and requirements-dev.txt are up to date."

# Production build
build-prod:
	docker compose -f docker-compose.yml build

# Health check
health:
	@echo "Backend:"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "Backend not running"
	@echo "\nFrontend:"
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "Frontend not running"
