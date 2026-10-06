.PHONY: sync migrate revision run lint format typecheck test test-unit check docker-build docker-up docker-down clean

sync:
	uv sync

migrate:
	uv run alembic upgrade head

revision:
	uv run alembic revision --autogenerate -m "$(m)"

run:
	uv run async-payments-service

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy

test:
	uv run pytest

test-unit:
	uv run pytest -m "not integration"

check: lint typecheck test

docker-build:
	docker compose build

docker-up:
	docker compose up --build -d --wait

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist
