.PHONY: up down logs migrate seed rls shell test

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose exec app python manage.py migrate

seed:
	docker compose exec app python manage.py seed_demo

rls:
	docker compose exec db psql -U app -d app -f /app/scripts/enable_rls.sql

shell:
	docker compose exec app python manage.py shell

test:
	docker compose exec app pytest
