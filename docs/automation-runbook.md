# Automation runbook

## Ownership and schedule

| Time (Asia/Shanghai) | Owner | Responsibility |
| --- | --- | --- |
| 00:23 daily | GitHub Actions | Fetch DOI-indexed metadata, require all journals to succeed, export static data, deploy Pages |
| 03:30 and 06:30 daily | Windows Task Scheduler | Verify the Pages snapshot, translate pending records through NVIDIA, validate and push the registry |
| After the registry push | GitHub Actions | Refresh translations from the healthy Pages snapshot and deploy the pushed registry revision |
| End of the local run | Windows Task Scheduler | Verify the exact push-triggered deployment and retain the run report |

The task is registered as `Daily Paper NVIDIA Translation`. It runs the repository scripts directly;
it does not start Codex or depend on a Codex automation. The old `每日文献 Spark 翻译` Codex
automation is paused and must remain paused to prevent duplicate runs.

The FastAPI scheduler configured by `SYNC_HOUR` and `SYNC_MINUTE` operates a persistent API
database. It has no role in the Pages-to-NVIDIA handshake.

## GitHub synchronization contract

`.github/workflows/pages-sync.yml` first classifies the deployment:

- `schedule`, `workflow_dispatch`, branch creation, and a push containing files beyond the
  translation registry use `full` mode;
- a push whose exact diff is only `packages/shared/data/article_registry.json` uses `translations`
  mode.

Full mode upgrades a fresh SQLite database, seeds the tracked journals, requires every journal
synchronization to succeed, exports `site-data.json` and `metadata.json`, and deploys the static
site with a workflow-run-specific data URL.

Translations mode downloads the currently deployed `site-data.json` and `metadata.json`, checks
the source bundle integrity and synchronization metadata, refreshes the article and dashboard
translations from the registry, and deploys again. It does not contact journal, publisher, PubMed,
or Crossref endpoints.

The deployment metadata records the synchronization run, Git revision, GitHub event, workflow run
ID, static bundle size and SHA-256 digest, and complete/pending translation counts. A partial sync
or an incomplete bundle cannot pass the local gate.

## Local NVIDIA translation contract

The Windows task invokes `scripts/run_nvidia_translation_task.ps1 -Execute`, which starts
`scripts/run_daily_nvidia_translation.py`. The runner uses:

- endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`;
- default model: `openai/gpt-oss-20b`;
- secret: user-scoped `NVIDIA_API_KEY` environment variable;
- four concurrent API requests, with one article per batch;
- 300-second response timeout per API request;
- JSON-mode Chat Completions responses, followed by script-owned schema, order, Chinese-text, and
  null-abstract validation.

The API key is never placed in a batch, command argument, log, registry entry, or Git commit.
Hash-matched historical translations retain their original `translation_model` value. Changing the
translation engine therefore does not falsely relabel old records or trigger a full retranslation;
new and source-changed records are written with the NVIDIA model name.

Each invocation follows this sequence:

1. Acquire the cross-trigger lock at `data/translation-work/.nvidia-automation.lock` and create a
   unique run directory under `data/translation-work/`.
2. Record the main worktree status, fetch `origin/main`, and create a detached worktree from the
   fetched revision. The user's existing local changes are not modified.
3. Run `scripts/validate_daily_schedule_run.py` with the verified GitHub CLI path. Its JSON output
   is the only accepted schedule identity and supplies the Shanghai date, workflow ID, and source
   revision. For an explicitly requested one-off catch-up, launch the wrapper with
   `-AssumeTriggerTime`; that mode selects the latest completed successful Pages deployment and
   records its actual event/date while leaving the normal scheduled-task gate strict.
4. Download and validate the canonical
   `https://yixi0527.github.io/daily_paper/data/metadata.json` with
   `scripts/verify_pages_deployment.py`. A successful, complete deployment is required.
5. Download the matching canonical `site-data.json` and run `article_registry.py prepare` against
   the detached worktree registry. The preparation uses source hashes and produces one-article
   batches with a 9,000-character source limit.
6. Run `run_nvidia_translation.py`. It sends only title/abstract source text to the API, binds
   article keys locally, writes outputs atomically, and leaves raw API responses in the ignored run
   directory for diagnosis.
7. Run `article_registry.py merge` and `article_registry.py verify`.
8. Run Ruff, the complete pytest suite, the web lint, and the production web build.
9. Confirm that the detached worktree diff contains only
   `packages/shared/data/article_registry.json`. Re-fetch `origin/main`, reject a remote race,
   create a single-file commit, verify its file list, and push `HEAD:main`.
10. Locate the push-triggered `pages-sync.yml` run by its exact commit, wait for completed/success,
    validate the exact final metadata with `--require-complete-translations`, download the exact
    final site data, and run registry verification again.

The task never creates an empty commit, force-pushes, edits project files outside the registry
during a run, or falls back to another model after an API failure.

## Failure handling

Every command is recorded under the run directory with its exact argument list, exit code, stdout,
and stderr. API attempts also retain the raw response and a small response log. A failed command
leaves the run directory and detached worktree in place for diagnosis; it does not merge partial
translations or push a partial registry. Rerun the same validated workflow only after correcting
the reported root cause. Failures are surfaced for follow-up and any available deployment status is
retained before the invocation ends; no error is silently skipped or replaced by a fallback result.

## Installation and manual checks

Set the API key once for the Windows user that owns the scheduled task:

```powershell
[Environment]::SetEnvironmentVariable('NVIDIA_API_KEY', '<your-key>', 'User')
```

Register or update the task:

```powershell
& 'C:\Users\yixi0\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe' `
  -NoLogo -NoProfile -File scripts/register_nvidia_translation_task.ps1
```

Run one manual catch-up while treating the current time as the trigger time:

```powershell
& 'C:\Users\yixi0\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe' `
  -NoLogo -NoProfile -File scripts/run_nvidia_translation_task.ps1 -Execute -AssumeTriggerTime
```

Inspect the real parser contracts before changing automation:

```powershell
python scripts/run_nvidia_translation.py --help
python scripts/run_daily_nvidia_translation.py --help
python scripts/article_registry.py fetch --help
python scripts/article_registry.py prepare --help
python scripts/article_registry.py merge --help
python scripts/article_registry.py verify --help
python scripts/validate_daily_schedule_run.py --help
python scripts/verify_pages_deployment.py --help
```

For a complete local quality check:

```powershell
ruff check .
pytest
npm run lint:web
npm run build:web
```
