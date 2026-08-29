# Daily Paper Tracker

Daily Paper Tracker is a monorepo web application for monitoring newly published papers across high-impact neuroscience, AI, and multidisciplinary journals. It is built around DOI-indexed ingestion:

1. Crossref REST API retrieves journal metadata.
2. DOI is the sole article identity used during synchronization.
3. Records without a DOI are excluded before database insertion.

It provides a FastAPI backend, a React web app, a daily scheduler, Docker deployment, Alembic migrations, pytest examples, and a GitHub Pages workflow that republishes the latest synchronized content every day.

## Why DOI / API first

This project intentionally avoids aggressive publisher-page crawling because that is the fastest way to trigger bot defenses and verification walls. The current design reduces CAPTCHA and anti-bot risk by:

- using Crossref for stable DOI-indexed metadata
- using low-frequency polling
- sending a reasonable User-Agent
- honoring `ETag` / `Last-Modified` / conditional requests when the source supports them
- rate-limiting outbound requests per host
- storing raw source payloads instead of fetching article detail pages repeatedly
- not crawling full-text pages just to enrich metadata
- loading persistent Chinese title and abstract translations from the tracked article registry

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
- Nature Reviews Neurology
- Molecular Psychiatry
- Molecular Neurodegeneration
- Translational Neurodegeneration
- Journal of Neuroinflammation
- Acta Neuropathologica
- Annual Review of Neuroscience
- JAMA Neurology
- Brain Stimulation
- Neuroscience & Biobehavioral Reviews
- Psychological Review
- Sleep Medicine Reviews

## Source strategy summary

- Cell / Neuron / Trends titles: Cell Press RSS for `current` and `inpress`, with Crossref fallback
- Nature family journals: official `current-issue.rss` plus journal RSS, with Crossref fallback
- Springer Nature journal pages: Springer RSS search feeds where stable, with Crossref metadata coverage by ISSN
- ScienceDirect journals: official publication RSS feeds where stable, with Crossref metadata coverage by ISSN
- Science: Crossref-first because official pages are more strongly gated in unattended environments
- The Lancet Neurology: Crossref-first for reliability and anti-bot safety
- Brain: Crossref-first for reliability and anti-bot safety
- Annual Reviews / JAMA / APA journals: Crossref-first by ISSN when public RSS is unavailable or blocked in unattended environments
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
- `ArticleAnalysisService`
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
│   ├── article_registry.py
│   ├── bootstrap.ps1
│   ├── bootstrap.sh
│   ├── run_nvidia_translation.py
│   ├── run_daily_nvidia_translation.py
│   ├── run_nvidia_translation_task.ps1
│   ├── register_nvidia_translation_task.ps1
│   ├── verify_pages_deployment.py
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
- stable acquisition dates and provider-tagged Chinese title/abstract translations in `packages/shared/data/article_registry.json`
- display dates after `2026-07-01` use the first acquisition timestamp and default ordering follows that display date
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
- `NVIDIA_API_KEY` as a user-scoped Windows environment variable (never commit it)

`ARTICLE_REGISTRY_FILE` can override the tracked registry path. The default is
`packages/shared/data/article_registry.json`.

The default translation model is `openai/gpt-oss-20b` through
`https://integrate.api.nvidia.com/v1/chat/completions`. Override it with the
`NVIDIA_API_MODEL` user environment variable only after verifying that the model is available
from the NVIDIA `/v1/models` endpoint.

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
python -m app.cli sync --journal nature-neuroscience
```

Prepare translation batches from an exported site bundle:

```bash
python scripts/article_registry.py prepare \
  --site-data apps/web/public/data/site-data.json \
  --registry packages/shared/data/article_registry.json \
  --work-dir data/translation-work/<run-id>
```

The translations are produced by `scripts/run_nvidia_translation.py` and merged back into the
registry with the same script. The runner uses the NVIDIA OpenAI-compatible Chat Completions API,
validates JSON and Chinese output, and never writes the API key to a batch, log, or registry.
Hash-matched historical translations keep their original `translation_model` provenance; only new
or source-changed records are sent to the NVIDIA API.

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

This scheduler serves a persistent API database. The GitHub Pages mirror and the Windows NVIDIA
translation task use the separate sequence documented in
[`docs/automation-runbook.md`](docs/automation-runbook.md).

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

1. Runs every day at `16:23 UTC` which is `00:23 Asia/Shanghai` on the following calendar day
2. Initializes a SQLite database inside the workflow
3. Seeds the 26 journals
4. Executes the synchronization job and rejects every partial synchronization
5. Merges acquisition dates and persisted translations from the tracked registry
6. Exports compact static JSON without upstream raw payloads, plus an exact deployment handshake into `apps/web/public/data`
7. Builds and deploys the React app to GitHub Pages

After enabling GitHub Pages in repository settings, the public link will be:

```text
https://<OWNER>.github.io/<REPO>/
```

That pages build is a static mirror of the latest synchronized metadata, while the FastAPI service remains the full live API deployment path.

The GitHub Pages workflow performs no model calls. Windows Task Scheduler runs
`Daily Paper NVIDIA Translation` at `03:30` and `06:30` Asia/Shanghai. Each invocation verifies
the exact successful scheduled deployment for the current Shanghai date, translates only new or
source-changed papers through NVIDIA, validates the registry, commits only that registry file, and
pushes it. The push triggers a second Pages run, and the task verifies that the new commit is the
exact revision exposed by the deployed metadata. The two daily triggers share a global lock, so a
long first run cannot overlap the second. The operating objective is a fully built prior-day site
with zero pending translations before `09:00` Asia/Shanghai. Failed invocations are recorded and
reported for follow-up, while the two scheduled invocations remain independent.

Register the Windows task after setting the user-scoped key:

```powershell
[Environment]::SetEnvironmentVariable('NVIDIA_API_KEY', '<your-key>', 'User')
& 'C:\Users\yixi0\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe' `
  -NoLogo -NoProfile -File scripts/register_nvidia_translation_task.ps1
```

For a one-off manual catch-up that treats the current time as the trigger time, run:

```powershell
& 'C:\Users\yixi0\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe' `
  -NoLogo -NoProfile -File scripts/run_nvidia_translation_task.ps1 -Execute -AssumeTriggerTime
```

This explicit switch uses the latest completed successful Pages deployment as the input snapshot;
the registered scheduled task remains on the strict current-date schedule gate.

The installed Codex automation named `每日文献 Spark 翻译` is paused and is not part of this
workflow.

The local task delegates GitHub schedule selection and UTC-to-Shanghai conversion to
`scripts/validate_daily_schedule_run.py`. Its validated JSON output is the only accepted schedule
identity, which keeps model-generated shell logic out of the date gate.

`scripts/verify_pages_deployment.py` embeds the canonical public metadata endpoint and uses it when
`--url` is omitted. Supplying any other metadata URL is rejected before a network request.

Each Pages build injects its workflow run ID into the static-data URL. This prevents a browser from
reusing a prior day's `site-data.json` when two daily deployments share the same Git revision.
Deployment metadata records the exact static bundle size, SHA-256 digest, and complete/pending
translation counts.

The schedule uses minute 23 because GitHub documents heavier queue load at the start of each
hour. The local task starts several hours later so the metadata synchronization has time to finish.

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
curl "http://localhost:8000/api/articles?page=1&page_size=20&journal=nature-neuroscience&source_category=doi"
```

Search by author and title:

```bash
curl "http://localhost:8000/api/search?author=Hopper&title=memory"
```

Run a manual sync:

```bash
curl -X POST http://localhost:8000/api/sync/run \
  -H "Content-Type: application/json" \
  -d '{"triggered_by":"manual"}'
```

Run a single-journal sync:

```bash
curl -X POST http://localhost:8000/api/sync/run/nature-neuroscience \
  -H "Content-Type: application/json" \
  -d '{"triggered_by":"manual"}'
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

- responsive article feed with one paper per page on mobile
- article listing with journal and author filters
- article detail view
- persistent title and abstract translations with model provenance
- deployment-versioned static data with complete translation counts
- author/title/journal search
- URL-synced filter state
- collapsible primary navigation
- browser-persistent favorites keyed by stable article identity
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
