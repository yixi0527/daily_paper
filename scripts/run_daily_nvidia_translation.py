from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if os.name == "nt":
    import msvcrt
else:
    import fcntl

DEFAULT_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
REPOSITORY = "yixi0527/daily_paper"
WORKFLOW = "pages-sync.yml"
BRANCH = "main"
TIMEZONE = "Asia/Shanghai"
METADATA_URL = "https://yixi0527.github.io/daily_paper/data/metadata.json"
SITE_DATA_URL = "https://yixi0527.github.io/daily_paper/data/site-data.json"
REGISTRY_RELATIVE_PATH = Path("packages/shared/data/article_registry.json")
COMMIT_MESSAGE = "data: translate daily papers with NVIDIA API"


class CommandFailed(RuntimeError):
    pass


class CommandRunner:
    def __init__(self, log_directory: Path) -> None:
        self.log_directory = log_directory
        self.log_directory.mkdir(parents=True, exist_ok=False)
        self.step = 0

    def run(
        self,
        *,
        label: str,
        executable: Path,
        arguments: list[str],
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]:
        self.step += 1
        command = [str(executable), *arguments]
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        prefix = f"{self.step:03d}-{label}"
        (self.log_directory / f"{prefix}.stdout.txt").write_text(
            result.stdout,
            encoding="utf-8",
        )
        (self.log_directory / f"{prefix}.stderr.txt").write_text(
            result.stderr,
            encoding="utf-8",
        )
        (self.log_directory / f"{prefix}.command.json").write_text(
            json.dumps(
                {
                    "command": command,
                    "cwd": str(cwd),
                    "exit_code": result.returncode,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"$ {' '.join(command)}", flush=True)
        if result.stdout:
            print(result.stdout, end="", flush=True)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr, flush=True)
        if result.returncode != 0:
            raise CommandFailed(
                f"Command failed with exit code {result.returncode}; "
                f"stdout={self.log_directory / f'{prefix}.stdout.txt'}; "
                f"stderr={self.log_directory / f'{prefix}.stderr.txt'}"
            )
        return result


@contextmanager
def exclusive_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("a+b")
    try:
        lock_file.seek(0)
        lock_file.write(b"0")
        lock_file.flush()
        lock_file.seek(0)
        if os.name == "nt":
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(f"{os.getpid()}\n".encode())
        lock_file.flush()
        os.fsync(lock_file.fileno())
        yield
    finally:
        lock_file.close()


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def read_json(path: Path) -> dict[str, Any]:
    require_file(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON document must be an object: {path}")
    return payload


def parse_json_output(result: subprocess.CompletedProcess[str], label: str) -> Any:
    output = result.stdout.strip()
    if not output:
        raise ValueError(f"{label} returned no JSON output")
    return json.loads(output)


def git_status(runner: CommandRunner, git: Path, cwd: Path) -> list[str]:
    result = runner.run(
        label="git-status",
        executable=git,
        arguments=["status", "--porcelain=v1", "--untracked-files=all"],
        cwd=cwd,
    )
    return result.stdout.splitlines()


def run_python_script(
    runner: CommandRunner,
    *,
    python: Path,
    script: Path,
    arguments: list[str],
    cwd: Path,
    label: str,
) -> subprocess.CompletedProcess[str]:
    return runner.run(
        label=label,
        executable=python,
        arguments=["-X", "utf8", str(script), *arguments],
        cwd=cwd,
    )


def fetch_json_document(
    runner: CommandRunner,
    *,
    python: Path,
    registry_script: Path,
    url: str,
    output: Path,
    cache_key: str,
    cwd: Path,
    label: str,
) -> dict[str, Any]:
    result = run_python_script(
        runner,
        python=python,
        script=registry_script,
        arguments=[
            "fetch",
            "--url",
            url,
            "--output",
            str(output),
            "--timeout",
            "120",
            "--cache-key",
            cache_key,
        ],
        cwd=cwd,
        label=label,
    )
    parse_json_output(result, label)
    return read_json(output)


def verify_metadata(
    runner: CommandRunner,
    *,
    python: Path,
    verifier: Path,
    output: Path,
    workflow_run_id: str,
    source_revision: str,
    source_event: str,
    sync_date: str,
    cwd: Path,
    label: str,
    require_complete: bool = False,
) -> dict[str, Any]:
    arguments = [
        "--url",
        METADATA_URL,
        "--output",
        str(output),
        "--expected-workflow-run-id",
        workflow_run_id,
        "--expected-source-revision",
        source_revision,
        "--expected-source-event",
        source_event,
        "--expected-sync-date",
        sync_date,
        "--timezone",
        TIMEZONE,
        "--wait-seconds",
        "1800",
        "--poll-seconds",
        "30",
        "--max-site-data-bytes",
        "15000000",
    ]
    if require_complete:
        arguments.append("--require-complete-translations")
    result = run_python_script(
        runner,
        python=python,
        script=verifier,
        arguments=arguments,
        cwd=cwd,
        label=label,
    )
    parse_json_output(result, label)
    return read_json(output)


def translation_counts(metadata: dict[str, Any]) -> dict[str, int]:
    translations = metadata["translations"]
    return {
        "total_articles": int(translations["total_articles"]),
        "complete_articles": int(translations["complete_articles"]),
        "pending_articles": int(translations["pending_articles"]),
    }


def wait_for_push_run(
    runner: CommandRunner,
    *,
    gh: Path,
    commit_sha: str,
    cwd: Path,
    wait_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + wait_seconds
    while True:
        result = runner.run(
            label="gh-list-push-run",
            executable=gh,
            arguments=[
                "run",
                "list",
                "--repo",
                REPOSITORY,
                "--workflow",
                WORKFLOW,
                "--branch",
                BRANCH,
                "--event",
                "push",
                "--commit",
                commit_sha,
                "--json",
                "databaseId,status,conclusion,event,headSha,url,createdAt",
                "--limit",
                "1",
            ],
            cwd=cwd,
        )
        runs = parse_json_output(result, "gh push run query")
        if not isinstance(runs, list):
            raise ValueError("GitHub CLI push run query must return an array")
        if runs:
            run = runs[0]
            if not isinstance(run, dict):
                raise ValueError("GitHub CLI push run must be an object")
            return run
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"No push workflow run appeared for commit {commit_sha} "
                f"within {wait_seconds} seconds"
            )
        time.sleep(min(15, remaining))


def wait_for_completed_push_run(
    runner: CommandRunner,
    *,
    gh: Path,
    run_id: str,
    expected_sha: str,
    cwd: Path,
    wait_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + wait_seconds
    while True:
        result = runner.run(
            label="gh-view-push-run",
            executable=gh,
            arguments=[
                "run",
                "view",
                run_id,
                "--repo",
                REPOSITORY,
                "--json",
                "databaseId,status,conclusion,event,headSha,url,createdAt",
            ],
            cwd=cwd,
        )
        run = parse_json_output(result, "gh push run status")
        if not isinstance(run, dict):
            raise ValueError("GitHub CLI push run status must be an object")
        if run.get("headSha") != expected_sha:
            raise ValueError(
                "Push workflow head SHA mismatch: "
                f"expected={expected_sha} actual={run.get('headSha')}"
            )
        if run.get("status") == "completed":
            if run.get("conclusion") != "success":
                raise ValueError(
                    "Push workflow did not succeed: "
                    f"run_id={run_id} conclusion={run.get('conclusion')} url={run.get('url')}"
                )
            return run
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Push workflow {run_id} did not complete within {wait_seconds} seconds"
            )
        time.sleep(min(30, remaining))


def remove_worktree(
    runner: CommandRunner,
    *,
    git: Path,
    project_root: Path,
    worktree: Path,
) -> None:
    runner.run(
        label="git-worktree-remove",
        executable=git,
        arguments=["worktree", "remove", "--force", str(worktree)],
        cwd=project_root,
    )


def run_translation_automation(args: argparse.Namespace) -> dict[str, Any]:
    project_root = args.project_root.resolve()
    git = args.git_executable.resolve()
    python = args.python_executable.resolve()
    gh = args.gh_executable.resolve()
    ruff = args.ruff_executable.resolve()
    pytest = args.pytest_executable.resolve()
    npm = args.npm_executable.resolve()
    for directory in (project_root, project_root / ".git"):
        if not directory.is_dir():
            raise FileNotFoundError(directory)
    for path in (project_root / "pyproject.toml", git, python, gh, ruff, pytest, npm):
        require_file(path)
    if not os.environ.get("NVIDIA_API_KEY"):
        raise OSError("NVIDIA_API_KEY is not set for the scheduled translation task")
    if args.workers < 1:
        raise ValueError("workers must be at least 1")
    if args.batch_size < 1:
        raise ValueError("batch-size must be at least 1")
    if args.wait_seconds < 1:
        raise ValueError("wait-seconds must be positive")

    translation_root = project_root / "data" / "translation-work"
    translation_root.mkdir(parents=True, exist_ok=True)
    lock_path = translation_root / ".nvidia-automation.lock"
    with exclusive_lock(lock_path):
        run_name = f"nvidia-{datetime.now(tz=UTC).strftime('%Y%m%d-%H%M%S-%f')}-{os.getpid()}"
        run_directory = translation_root / run_name
        run_directory.mkdir(parents=True, exist_ok=False)
        runner = CommandRunner(run_directory / "commands")
        initial_status = git_status(runner, git, project_root)
        (run_directory / "initial-git-status.txt").write_text(
            "\n".join(initial_status) + ("\n" if initial_status else ""),
            encoding="utf-8",
        )
        runner.run(
            label="git-fetch-origin-main",
            executable=git,
            arguments=["fetch", "origin", BRANCH],
            cwd=project_root,
        )
        base_revision = runner.run(
            label="git-rev-parse-origin-main",
            executable=git,
            arguments=["rev-parse", "origin/main"],
            cwd=project_root,
        ).stdout.strip()
        worktree = run_directory / "worktree"
        runner.run(
            label="git-worktree-add",
            executable=git,
            arguments=["worktree", "add", "--detach", str(worktree), base_revision],
            cwd=project_root,
        )
        registry_script = worktree / "scripts" / "article_registry.py"
        schedule_validator = worktree / "scripts" / "validate_daily_schedule_run.py"
        deployment_verifier = worktree / "scripts" / "verify_pages_deployment.py"
        translation_runner = worktree / "scripts" / "run_nvidia_translation.py"
        for script in (registry_script, schedule_validator, deployment_verifier, translation_runner):
            require_file(script)

        schedule_result = run_python_script(
            runner,
            python=python,
            script=schedule_validator,
            arguments=[
                "--gh-executable",
                str(gh),
                "--repository",
                REPOSITORY,
                "--workflow",
                WORKFLOW,
                "--branch",
                BRANCH,
                "--timezone",
                TIMEZONE,
            ],
            cwd=worktree,
            label="validate-schedule",
        )
        schedule = parse_json_output(schedule_result, "schedule validation")
        if not isinstance(schedule, dict):
            raise ValueError("Schedule validation must return an object")
        schedule_run_id = str(schedule["database_id"])
        schedule_revision = str(schedule["head_sha"])
        sync_date = str(schedule["local_date"])
        gate_metadata_path = run_directory / "gate-metadata.json"
        gate_metadata = verify_metadata(
            runner,
            python=python,
            verifier=deployment_verifier,
            output=gate_metadata_path,
            workflow_run_id=schedule_run_id,
            source_revision=schedule_revision,
            source_event="schedule",
            sync_date=sync_date,
            cwd=worktree,
            label="verify-gate-deployment",
        )
        gate_counts = translation_counts(gate_metadata)
        site_data_path = run_directory / "site-data.json"
        fetch_json_document(
            runner,
            python=python,
            registry_script=registry_script,
            url=SITE_DATA_URL,
            output=site_data_path,
            cache_key=schedule_run_id,
            cwd=worktree,
            label="fetch-gate-site-data",
        )

        if gate_counts["pending_articles"] == 0:
            verify_result = run_python_script(
                runner,
                python=python,
                script=registry_script,
                arguments=[
                    "verify",
                    "--site-data",
                    str(site_data_path),
                    "--registry",
                    str(worktree / REGISTRY_RELATIVE_PATH),
                ],
                cwd=worktree,
                label="verify-complete-registry",
            )
            summary = {
                "status": "already-complete",
                "model": os.environ.get("NVIDIA_API_MODEL", DEFAULT_MODEL),
                "schedule_run_id": schedule_run_id,
                "schedule_url": schedule["url"],
                "article_count": gate_counts["total_articles"],
                "pending_articles": 0,
                "registry_verification": parse_json_output(verify_result, "registry verification"),
                "run_directory": str(run_directory),
            }
            remove_worktree(runner, git=git, project_root=project_root, worktree=worktree)
            return summary

        batches_directory = run_directory / "batches"
        model = os.environ.get("NVIDIA_API_MODEL", DEFAULT_MODEL)
        prepare_result = run_python_script(
            runner,
            python=python,
            script=registry_script,
            arguments=[
                "prepare",
                "--site-data",
                str(site_data_path),
                "--registry",
                str(worktree / REGISTRY_RELATIVE_PATH),
                "--work-dir",
                str(batches_directory),
                "--model",
                model,
                "--batch-size",
                str(args.batch_size),
                "--max-source-chars",
                "9000",
                "--default-acquired-at",
                datetime.now(tz=UTC).isoformat(),
            ],
            cwd=worktree,
            label="prepare-translation-batches",
        )
        parse_json_output(prepare_result, "translation preparation")
        manifest = read_json(batches_directory / "manifest.json")
        pending_count = int(manifest["pending_count"])
        if pending_count == 0:
            verify_result = run_python_script(
                runner,
                python=python,
                script=registry_script,
                arguments=[
                    "verify",
                    "--site-data",
                    str(site_data_path),
                    "--registry",
                    str(worktree / REGISTRY_RELATIVE_PATH),
                ],
                cwd=worktree,
                label="verify-noop-registry",
            )
            summary = {
                "status": "no-new-translations",
                "model": model,
                "schedule_run_id": schedule_run_id,
                "schedule_url": schedule["url"],
                "article_count": gate_counts["total_articles"],
                "pending_articles": gate_counts["pending_articles"],
                "registry_verification": parse_json_output(verify_result, "registry verification"),
                "run_directory": str(run_directory),
            }
            remove_worktree(runner, git=git, project_root=project_root, worktree=worktree)
            return summary

        api_url = os.environ.get("NVIDIA_API_URL", DEFAULT_API_URL)
        run_python_script(
            runner,
            python=python,
            script=translation_runner,
            arguments=[
                "--work-dir",
                str(batches_directory),
                "--api-url",
                api_url,
                "--model",
                model,
                "--max-tokens",
                "8192",
                "--workers",
                str(args.workers),
                "--resume",
            ],
            cwd=worktree,
            label="translate-with-nvidia-api",
        )
        manifest_path = batches_directory / "manifest.json"
        run_python_script(
            runner,
            python=python,
            script=registry_script,
            arguments=[
                "merge",
                "--manifest",
                str(manifest_path),
                "--registry",
                str(worktree / REGISTRY_RELATIVE_PATH),
                "--model",
                model,
                "--translated-at",
                datetime.now(tz=UTC).isoformat(),
            ],
            cwd=worktree,
            label="merge-translation-registry",
        )
        verify_result = run_python_script(
            runner,
            python=python,
            script=registry_script,
            arguments=[
                "verify",
                "--site-data",
                str(site_data_path),
                "--registry",
                str(worktree / REGISTRY_RELATIVE_PATH),
            ],
            cwd=worktree,
            label="verify-translation-registry",
        )
        runner.run(
            label="ruff-check",
            executable=ruff,
            arguments=["check", "."],
            cwd=worktree,
        )
        runner.run(
            label="pytest",
            executable=pytest,
            arguments=["-q"],
            cwd=worktree,
        )
        runner.run(
            label="npm-lint-web",
            executable=npm,
            arguments=["run", "lint:web"],
            cwd=worktree,
        )
        runner.run(
            label="npm-build-web",
            executable=npm,
            arguments=["run", "build:web"],
            cwd=worktree,
        )
        final_status = git_status(runner, git, worktree)
        expected_status = [f" M {REGISTRY_RELATIVE_PATH.as_posix()}"]
        if final_status != expected_status:
            raise ValueError(
                "Unexpected worktree after translation: "
                f"expected={expected_status} actual={final_status}"
            )
        runner.run(
            label="git-fetch-before-commit",
            executable=git,
            arguments=["fetch", "origin", BRANCH],
            cwd=worktree,
        )
        latest_remote_revision = runner.run(
            label="git-rev-parse-before-commit",
            executable=git,
            arguments=["rev-parse", "origin/main"],
            cwd=worktree,
        ).stdout.strip()
        if latest_remote_revision != base_revision:
            raise ValueError(
                "origin/main changed while translation was running: "
                f"base={base_revision} latest={latest_remote_revision}"
            )
        runner.run(
            label="git-commit-registry",
            executable=git,
            arguments=[
                "commit",
                "--only",
                REGISTRY_RELATIVE_PATH.as_posix(),
                "-m",
                COMMIT_MESSAGE,
            ],
            cwd=worktree,
        )
        committed_paths = runner.run(
            label="git-verify-commit-files",
            executable=git,
            arguments=["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            cwd=worktree,
        ).stdout.splitlines()
        if committed_paths != [REGISTRY_RELATIVE_PATH.as_posix()]:
            raise ValueError(
                "Translation commit contains unexpected files: "
                f"{committed_paths}"
            )
        commit_sha = runner.run(
            label="git-rev-parse-commit",
            executable=git,
            arguments=["rev-parse", "HEAD"],
            cwd=worktree,
        ).stdout.strip()
        divergence = runner.run(
            label="git-check-push-divergence",
            executable=git,
            arguments=["rev-list", "--left-right", "--count", "origin/main...HEAD"],
            cwd=worktree,
        ).stdout.strip().split()
        if divergence != ["0", "1"]:
            raise ValueError(f"Unexpected branch divergence before push: {divergence}")
        runner.run(
            label="git-push-registry",
            executable=git,
            arguments=["push", "origin", "HEAD:main"],
            cwd=worktree,
        )
        push_run = wait_for_push_run(
            runner,
            gh=gh,
            commit_sha=commit_sha,
            cwd=worktree,
            wait_seconds=args.wait_seconds,
        )
        push_run_id = str(push_run["databaseId"])
        completed_push_run = wait_for_completed_push_run(
            runner,
            gh=gh,
            run_id=push_run_id,
            expected_sha=commit_sha,
            cwd=worktree,
            wait_seconds=args.wait_seconds,
        )
        final_metadata_path = run_directory / "final-metadata.json"
        final_metadata = verify_metadata(
            runner,
            python=python,
            verifier=deployment_verifier,
            output=final_metadata_path,
            workflow_run_id=push_run_id,
            source_revision=commit_sha,
            source_event="push",
            sync_date=sync_date,
            cwd=worktree,
            label="verify-final-deployment",
            require_complete=True,
        )
        final_site_data_path = run_directory / "final-site-data.json"
        fetch_json_document(
            runner,
            python=python,
            registry_script=registry_script,
            url=SITE_DATA_URL,
            output=final_site_data_path,
            cache_key=push_run_id,
            cwd=worktree,
            label="fetch-final-site-data",
        )
        final_verify_result = run_python_script(
            runner,
            python=python,
            script=registry_script,
            arguments=[
                "verify",
                "--site-data",
                str(final_site_data_path),
                "--registry",
                str(worktree / REGISTRY_RELATIVE_PATH),
            ],
            cwd=worktree,
            label="verify-final-registry",
        )
        final_counts = translation_counts(final_metadata)
        summary = {
            "status": "completed",
            "model": model,
            "api_url": api_url,
            "schedule_run_id": schedule_run_id,
            "schedule_url": schedule["url"],
            "translated_articles": pending_count,
            "batch_count": int(manifest["batch_count"]),
            "commit": commit_sha,
            "push_workflow_run_id": push_run_id,
            "push_workflow_url": completed_push_run["url"],
            "article_count": final_counts["total_articles"],
            "site_data_bytes": final_metadata["site_data_bytes"],
            "pending_articles": final_counts["pending_articles"],
            "registry_verification": parse_json_output(final_verify_result, "final registry verification"),
            "run_directory": str(run_directory),
        }
        (run_directory / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        remove_worktree(runner, git=git, project_root=project_root, worktree=worktree)
        return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the daily paper translation workflow with the NVIDIA API"
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--python-executable", required=True, type=Path)
    parser.add_argument("--git-executable", required=True, type=Path)
    parser.add_argument("--gh-executable", required=True, type=Path)
    parser.add_argument("--ruff-executable", required=True, type=Path)
    parser.add_argument("--pytest-executable", required=True, type=Path)
    parser.add_argument("--npm-executable", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--wait-seconds", type=int, default=1800)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_translation_automation(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
