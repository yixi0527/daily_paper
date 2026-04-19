# Daily Paper Tracker

Daily Paper Tracker is a monorepo web application for monitoring newly published papers across high-impact neuroscience, AI, and multidisciplinary journals. It is built around a stability-first ingestion strategy:

1. Official RSS / official feeds whenever available.
2. Crossref REST API as the metadata-safe fallback.
3. No full-text scraping, no translation, and no routine browser automation.

The system tracks both:

- `current_issue`
- `online_first` / `advance online` / `articles in press`

It provides a FastAPI backend, a React web app, a daily scheduler, Docker deployment, Alembic migrations, pytest examples, and a GitHub Pages workflow that republishes the latest synchronized content every day.

## Why RSS / API first

This project intentionally avoids aggressive publisher-page crawling because that is the fastest way to trigger bot defenses and verification walls. The current design reduces CAPTCHA and anti-bot risk by:

- using official publisher feeds whenever the publisher exposes them
- using Crossref for stable metadata fallback instead of hitting publisher HTML repeatedly
- using low-frequency polling
- sending a reasonable User-Agent
- honoring `ETag` / `Last-Modified` / conditional requests when the source supports them
- rate-limiting outbound requests per host
- storing raw source payloads instead of fetching article detail pages repeatedly
- not crawling full-text pages just to enrich metadata

## Covered journals

- Cell
- Neuron
- Nature
- Science
- Nature Neuroscience
- Nature Reviews Neuroscience
- Nature Human Behaviour
- Nature Machine Intelligence
- Trends in Cognitive Sciences
- Trends in Neurosciences
- The Lancet Neurology
- Brain
- Artificial Intelligence Review
- Brain Informatics

## Source strategy summary

- Cell / Neuron / Trends titles: Cell Press RSS for `current` and `inpress`, with Crossref fallback
- Nature family journals: official `current-issue.rss` plus journal RSS, with Crossref fallback
- Science: Crossref-first because official pages are more strongly gated in unattended environments
- The Lancet Neurology: Crossref-first for reliability and anti-bot safety
- Brain: Crossref-first for reliability and anti-bot safety
- Artificial Intelligence Review / Brain Informatics: Springer RSS where stable, then Crossref fallback

## Architecture

- `apps/api`: FastAPI backend, scheduler, ingestion adapters, Alembic migrations, CLI
- `apps/web`: Vite + React frontend, supports live API mode and static GitHub Pages mirror mode
- `packages/shared`: shared journal configuration

Core backend services:

- `PublisherAdapter` abstract base class
- `RSSParserService`
- `CrossrefClientService`
- `ArticleNormalizer`
- `DedupService`
- `SearchService`
- `SchedulerService`
- `SyncOrchestrationService`

## Directory tree

```text
.
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── pages-sync.yml
├── apps/
│   ├── api/
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   ├── app/
│   │   │   ├── adapters/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   ├── utils/
│   │   │   ├── cli.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   └── Dockerfile
│   └── web/
│       ├── public/
│       ├── src/
│       │   ├── api/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── lib/
│       │   ├── pages/
│       │   └── styles/
│       ├── Dockerfile
│       └── nginx.conf
├── packages/
│   └── shared/
│       └── config/
│           └── journals.json
├── scripts/
│   ├── bootstrap.ps1
│   ├── bootstrap.sh
│   └── run_alembic.py
├── .env.example
├── docker-compose.yml
├── Makefile
├── package.json
└── pyproject.toml
```

## Data model

Main tables:

- `journals`
- `source_states`
- `articles`
- `article_authors`
- `article_payloads`
- `sync_runs`
- `sync_run_journals`

Important guarantees:

- unique DOI constraint
- fallback dedup hash on `title + first_author + published_date`
- raw payload persistence for each source item
- per-source state for `etag`, `last_modified`, `cursor`, last success time, and failure streak
- sync run isolation so one journal failure does not stop the global job

## Quick start

### 1. Bootstrap

Windows PowerShell:

```powershell
./scripts/bootstrap.ps1
```

macOS / Linux:

```bash
./scripts/bootstrap.sh
```

### 2. Configure environment

```bash
cp .env.example .env
```

Update at least:

- `DATABASE_URL`
- `CROSSREF_MAILTO`
- `HTTP_USER_AGENT`

### 3. Initialize database

```bash
python scripts/run_alembic.py upgrade head
python -m app.cli seed-journals
```

### 4. Run the backend

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir apps/api/app
```

Open:

- API docs: `http://localhost:8000/api/docs`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

### 5. Run the frontend

```bash
npm install
npm --workspace apps/web run dev
```

Open:

- Web app: `http://localhost:5173`

## CLI commands

Seed journals:

```bash
python -m app.cli seed-journals
```

Run full sync:

```bash
python -m app.cli sync --all --triggered-by cli
```

Run single-journal sync:

```bash
python -m app.cli sync --journal nature-neuroscience --category current_issue --category online_first
```

Export static data for GitHub Pages:

```bash
python -m app.cli export-static --output apps/web/public/data
```

Start the blocking scheduler:

```bash
python -m app.cli scheduler
```

## Daily scheduler

Default schedule:

- Every day at `22:00` Asia/Shanghai time

Environment variables:

- `SYNC_TIMEZONE`
- `SYNC_HOUR`
- `SYNC_MINUTE`

The scheduler can run either:

- as a standalone container via `docker-compose`
- inside the API process if `RUN_SCHEDULER=true`

## Docker deployment

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Web: `http://localhost:8080`
- Postgres: `localhost:5432`

The compose stack automatically:

- runs Alembic migrations
- seeds journal configuration
- starts the API
- starts a separate scheduler container

## GitHub Pages daily publishing

This repository includes `.github/workflows/pages-sync.yml`.

What it does:

1. Runs every day at `14:00 UTC` which is `22:00 Asia/Shanghai`
2. Initializes a SQLite database inside the workflow
3. Seeds the 14 journals
4. Executes the synchronization job
5. Exports static JSON into `apps/web/public/data`
6. Builds the React app in `static` mode
7. Deploys the built site to GitHub Pages

After enabling GitHub Pages in repository settings, the public link will be:

```text
https://<OWNER>.github.io/<REPO>/
```

That pages build is a static mirror of the latest synchronized metadata, while the FastAPI service remains the full live API deployment path.

## REST API

Required endpoints implemented:

- `GET /api/journals`
- `GET /api/articles`
- `GET /api/articles/{id}`
- `GET /api/search`
- `POST /api/sync/run`
- `POST /api/sync/run/{journal_slug}`
- `GET /api/sync/runs`
- `GET /api/health`

Additional endpoint:

- `GET /api/dashboard`

### Example requests

List journals:

```bash
curl http://localhost:8000/api/journals
```

List articles:

```bash
curl "http://localhost:8000/api/articles?page=1&page_size=20&journal=nature-neuroscience&source_category=online_first"
```

Search by author and title:

```bash
curl "http://localhost:8000/api/search?author=Hopper&title=memory"
```

Run a manual sync:

```bash
curl -X POST http://localhost:8000/api/sync/run \
  -H "Content-Type: application/json" \
  -d '{"categories":["current_issue","online_first"],"triggered_by":"manual"}'
```

Run a single-journal sync:

```bash
curl -X POST http://localhost:8000/api/sync/run/nature-neuroscience \
  -H "Content-Type: application/json" \
  -d '{"categories":["online_first"],"triggered_by":"manual"}'
```

## Testing

```bash
pytest
```

Included test coverage examples:

- dedup normalization
- health endpoint
- article list endpoint
- search endpoint
- journal seed script

## Frontend behavior

The frontend supports two modes:

- `live`: calls the FastAPI backend
- `static`: reads the exported `site-data.json` bundle for GitHub Pages

Features implemented:

- responsive dashboard
- article listing with pagination and filters
- article detail view
- author/title/abstract search
- URL-synced filter state
- DOI copy button
- external publisher links
- recent searches in `localStorage`
- sync history page
- journal source overview page
- loading, empty, and error states

## Notes on source quality

Because publishers expose metadata differently, the system normalizes everything into one internal article model. RSS entries and Crossref works can differ in:

- DOI placement
- author shape
- volume/issue availability
- abstract richness
- online-vs-print timestamps

The `ArticleNormalizer` absorbs those differences so the UI and API can stay consistent.

## Useful Make targets

```bash
make install
make migrate
make seed
make sync
make export-static
make test
make docker-up
```

## Next steps

- add optional publisher-specific browser fallback behind an explicit feature flag for the few journals that remain gated
- add richer source health dashboards and alerting
- add database-backed full-text search or Postgres `tsvector` indexing for larger deployments
- add Slack / email digest delivery on top of the synchronized metadata
