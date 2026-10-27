.PHONY: up down build seed reseed-realistic test backend-test frontend-build

up:
	docker compose up --build

down:
	docker compose down -v

build:
	docker compose build

seed:
	docker compose exec backend python -m seed.seed_data

reseed-realistic:
	cd backend && PYTHONPATH=. python -m seed.reseed_realistic --seed $(or $(SEED),20261025)

test:
	docker compose exec backend pytest -v

backend-test:
	cd backend && PYTHONPATH=. python -m pytest -v

frontend-build:
	cd frontend && npm run build
