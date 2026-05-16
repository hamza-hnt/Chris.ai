SHELL := /bin/bash
PYTHON ?= python3

.PHONY: up down logs migrate seed eval check-env sample test

up: check-env
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose run --rm backend python -m app.seed

eval: check-env
	docker compose run --rm --no-deps backend python -m tests.prompt_evals.harness

sample:
	docker compose run --rm backend python -m app.sample_turn

test:
	docker compose run --rm --no-deps backend pytest

check-env:
	@$(PYTHON) scripts/check_env.py
