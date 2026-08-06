# Automation runbook

## Ownership and schedule

| Time (Asia/Shanghai) | Owner | Responsibility |
| --- | --- | --- |
| 01:23 daily | GitHub Actions | Fetch DOI-indexed metadata, require all journals to succeed, export static data, deploy Pages |
| 06:00 daily | Local Codex automation | Verify that exact scheduled deployment, translate pending records with `gpt-5.3-codex-spark`, validate and push the registry |
| After the registry push | GitHub Actions | Refresh translations from the healthy Pages snapshot and deploy the pushed registry revision |
| End of the local run | Local Codex automation | Verify the exact push-triggered deployment and report the result |

The FastAPI scheduler configured by `SYNC_HOUR` and `SYNC_MINUTE` operates a persistent API
database. It has no role in the Pages-to-Spark handshake.

## GitHub synchronization contract

`.github/workflows/pages-sync.yml` first classifies the deployment:

- `schedule`, `workflow_dispatch`, branch creation, and any push containing files beyond the
  translation registry use `full` mode;
- a push whose exact diff is only `packages/shared/data/article_registry.json` uses
  `translations` mode.

Full mode performs these stages in order:

1. Upgrade a fresh SQLite database to the single Alembic head.
2. Seed the tracked journal configuration.
3. Run every journal synchronization with `--require-complete`.
4. Export `site-data.json` and `metadata.json`.
5. Build and deploy the static site.

Translations mode downloads the currently deployed `site-data.json` and `metadata.json`, requires
the underlying synchronization to be successful and current for the Shanghai calendar date,
requires every deployed article to have a current source-hash-matched registry entry, refreshes
the full article list and dashboard article list, records both the base deployment and translation
deployment revisions, then builds and deploys. It does not contact journal, publisher, PubMed, or
Crossref endpoints.

`metadata.json` records:

- the synchronization run ID, status, timestamps, processed journal count, and failure count;
- the Git revision, GitHub event, and workflow run ID that produced the deployment;
- the export time and article/journal counts.

A partial run exits nonzero before export, preserving the previously healthy Pages deployment.

## Local Spark translation contract

The active Codex automation is named `每日文献 Spark 翻译`. It must complete these checks before
writing translation output:

1. The local Git worktree is fully clean, including untracked files.
2. `git pull --ff-only origin main` succeeds.
3. The latest `pages-sync.yml` run triggered by `schedule` completed successfully on the current
   Shanghai calendar date.
4. The deployed `metadata.json` matches that workflow run ID, head revision, event, and sync date.
5. Every configured journal was processed and the deployed failure count is zero.

Translation work stays under ignored `data/translation-work/<run-id>/`. The registry preparation
uses source hashes, so unchanged translations stay untouched. The task writes and validates every
batch, merges the outputs, verifies the complete site bundle, runs backend and frontend checks,
and permits only `packages/shared/data/article_registry.json` in the final diff.

After pushing, the task waits for the `push`-triggered Pages workflow whose head revision equals
the translation commit. It then runs `scripts/verify_pages_deployment.py` against the public
metadata endpoint with that workflow run ID and revision.

## Failure handling

- Migration graph errors stop database preparation.
- Any failed journal stops the Pages publication.
- A stale base deployment or stale/missing registry translation stops translation-only publication.
- A stale, delayed, failed, or mismatched scheduled deployment stops local translation.
- Invalid or incomplete translation output stops the merge.
- Test, commit, push, redeploy, or final deployment verification failure stops the local task.
- Work products and logs remain in the ignored run directory for diagnosis.

Every failure report should include the command, exit code, workflow URL when applicable, affected
file or journal, and the original error text.

## Manual checks

Inspect migration heads:

```bash
python scripts/run_alembic.py heads
```

Run the complete local verification suite:

```bash
ruff check .
pytest
npm run lint:web
npm run build:web
```

Verify a downloaded deployment metadata file through the same validator used by automation:

```bash
python scripts/verify_pages_deployment.py \
  --url https://yixi0527.github.io/daily_paper/data/metadata.json \
  --output data/translation-work/manual/metadata.json \
  --expected-workflow-run-id <run-id> \
  --expected-source-revision <commit-sha> \
  --expected-source-event schedule \
  --expected-sync-date <YYYY-MM-DD> \
  --timezone Asia/Shanghai
```
