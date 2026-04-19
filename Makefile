PYTHON ?= python
PIP ?= $(PYTHON) -m pip
NPM ?= npm

.PHONY: install install-web install-api migrate seed sync export-static api-dev web-dev scheduler test lint format docker-up docker-down

install: install-api install-web

install-api:
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"

install-web:
	$(NPM) install

migrate:
	$(PYTHON) scripts/run_alembic.py upgrade head

seed:
	$(PYTHON) -m app.cli seed-journals

sync:
	$(PYTHON) -m app.cli sync --all

export-static:
	$(PYTHON) -m app.cli export-static --output apps/web/public/data

api-dev:
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir apps/api/app

web-dev:
	$(NPM) --workspace apps/web run dev

scheduler:
	$(PYTHON) -m app.cli scheduler

test:
	pytest

lint:
	ruff check .
	$(NPM) --workspace apps/web run lint

format:
	ruff format .
	$(NPM) --workspace apps/web run format

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

