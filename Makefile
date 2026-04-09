UV ?= uv
APP_MODULE ?= app.main:app

.PHONY: install run lint format fix typecheck test coverage security precommit install-precommit compose-up compose-down test-db-up db-upgrade db-revision

install:
	$(UV) sync --all-extras

run:
	$(UV) run uvicorn $(APP_MODULE) --host 0.0.0.0 --port 8000 --reload

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

fix:
	$(UV) run ruff check . --fix
	$(UV) run ruff format .

typecheck:
	$(UV) run mypy app tests

test:
	$(UV) run pytest

coverage:
	$(UV) run pytest --cov=app --cov-report=term-missing --cov-report=xml

security:
	$(UV) run bandit -r app
	$(UV) run pip-audit

precommit:
	$(UV) run pre-commit run --all-files

install-precommit:
	$(UV) run pre-commit install

compose-up:
	docker compose up --build

compose-down:
	docker compose down --remove-orphans

test-db-up:
	docker compose up -d test-db

db-upgrade:
	$(UV) run alembic upgrade head

db-revision:
	$(UV) run alembic revision --autogenerate -m "$(m)"
