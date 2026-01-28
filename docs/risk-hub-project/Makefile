# =============================================================================
# risk-hub Development Makefile
# =============================================================================

.PHONY: help up down logs shell migrate seed test lint typecheck ci clean

# Default target
help:
	@echo "risk-hub Development Commands"
	@echo "=============================="
	@echo ""
	@echo "  up          - Start all services"
	@echo "  down        - Stop all services"
	@echo "  logs        - Follow logs"
	@echo "  shell       - Django shell"
	@echo "  dbshell     - PostgreSQL shell"
	@echo ""
	@echo "  migrate     - Run migrations"
	@echo "  makemigrations - Create migrations"
	@echo "  seed        - Create demo tenant"
	@echo "  createsuperuser - Create admin user"
	@echo ""
	@echo "  test        - Run tests"
	@echo "  test-cov    - Run tests with coverage"
	@echo "  lint        - Run linter (ruff)"
	@echo "  typecheck   - Run type checker (mypy)"
	@echo "  ci          - Run all checks"
	@echo ""
	@echo "  clean       - Remove containers and volumes"
	@echo "  rebuild     - Rebuild and restart"

# =============================================================================
# Docker Compose
# =============================================================================

up:
	docker compose up -d
	@echo ""
	@echo "✅ Services started"
	@echo "   App:     http://demo.localhost:8080/"
	@echo "   MinIO:   http://localhost:9001/"

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

shell:
	docker compose exec app python manage.py shell_plus

dbshell:
	docker compose exec db psql -U app -d risk_hub

# =============================================================================
# Django Management
# =============================================================================

migrate:
	docker compose exec app python manage.py migrate

makemigrations:
	docker compose exec app python manage.py makemigrations

seed:
	docker compose exec app python manage.py seed_demo

createsuperuser:
	docker compose exec app python manage.py createsuperuser

collectstatic:
	docker compose exec app python manage.py collectstatic --noinput

# =============================================================================
# Testing & Quality
# =============================================================================

test:
	docker compose exec app pytest

test-cov:
	docker compose exec app pytest --cov=apps --cov-report=html --cov-report=term

lint:
	docker compose exec app ruff check src/ tests/
	docker compose exec app ruff format --check src/ tests/

lint-fix:
	docker compose exec app ruff check --fix src/ tests/
	docker compose exec app ruff format src/ tests/

typecheck:
	docker compose exec app mypy src/

ci: lint typecheck test
	@echo ""
	@echo "✅ All checks passed"

# =============================================================================
# Infrastructure
# =============================================================================

rls-enable:
	docker compose exec db psql -U app -d risk_hub -f /docker-entrypoint-initdb.d/enable_rls.sql

# =============================================================================
# Cleanup
# =============================================================================

clean:
	docker compose down -v --remove-orphans
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d
