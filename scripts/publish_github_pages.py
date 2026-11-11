"""Publish the prepared local snapshot and resume its exact GitHub Actions run."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

from validate_pages_assets import validate

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get("DAILY_PAPER_RUNTIME_DIR", ROOT / "data/site-workflow"))
GIT = r"C:\Program Files\Git\cmd\git.exe"
GH = r"C:\Users\yixi0\AppData\Local\Programs\GitHub CLI\gh.exe"
REPOSITORY = "yixi0527/daily_paper"
WORKFLOW = "pages-sync.yml"
DATA_PATHS = ["apps/web/public/data", "packages/shared/data/article_registry.json"]


def run(arguments: list[str], *, capture: bool = False, **kwargs) -> str:
    result = subprocess.run(
        arguments, cwd=ROOT, text=True, encoding="utf-8",
        stdout=subprocess.PIPE if capture else None, **kwargs,
    )
    if result.returncode and capture:
        print(result.stdout, flush=True)
    result.check_returncode()
    return result.stdout if capture else ""


def save(receipt: dict) -> None:
    from run_nvidia_translation import write_json

    write_json(RUNTIME / "publication.json", receipt)


def publish() -> None:
    state = json.loads((RUNTIME / "state.json").read_text(encoding="utf-8"))
    previous = json.loads((RUNTIME / "publication.json").read_text(encoding="utf-8"))
    if (
        state["status"] == "published"
        and previous.get("provider") == "github-pages"
        and previous.get("published") is True
        and previous.get("run_id") == state["run_id"]
    ):
        print(json.dumps(previous, ensure_ascii=False))
        return
    if state["status"] not in {"ready", "published"}:
        raise ValueError(f"The local library is not ready to publish: {state['status']}")
    validate(ROOT / "apps/web/public/data")
    if previous.get("version_id"):
        history = RUNTIME / "publications"
        history.mkdir(exist_ok=True)
        shutil.copyfile(RUNTIME / "publication.json", history / "codex-sites-final.json")
    receipt = {"provider": "github-pages", "published": False, "run_id": state["run_id"]}
    try:
        run([GIT, "add", "--", *DATA_PATHS])
        changes = run([GIT, "diff", "--cached", "--name-only", "--", *DATA_PATHS], capture=True)
        if changes:
            run([GIT, "commit", "--only", "-m", "Update prepared literature snapshot", "--", *DATA_PATHS])
        commit = run([GIT, "rev-parse", "HEAD"], capture=True).strip()
        pages = json.loads(run([GH, "api", f"repos/{REPOSITORY}/pages"], capture=True))
        receipt.update(commit_sha=commit, url=pages["html_url"], stage="push")
        if previous.get("provider") == "github-pages" and previous.get("commit_sha") == commit:
            receipt.update(previous, published=False)
        save(receipt)
        run([GIT, "push", "origin", "HEAD:main"])
        receipt["stage"] = "deployment"
        save(receipt)
        if not receipt.get("workflow_run_id"):
            for _ in range(24):
                runs = json.loads(run([
                    GH, "run", "list", "--repo", REPOSITORY, "--workflow", WORKFLOW,
                    "--branch", "main", "--event", "push", "--commit", commit,
                    "--json", "databaseId,status,conclusion,headSha,url", "--limit", "1",
                ], capture=True))
                if runs:
                    receipt.update(workflow_run_id=str(runs[0]["databaseId"]), workflow_url=runs[0]["url"])
                    save(receipt)
                    break
                time.sleep(5)
            else:
                raise TimeoutError(f"No Pages workflow run appeared for {commit}")
        run([
            GH, "run", "watch", receipt["workflow_run_id"], "--repo", REPOSITORY,
            "--exit-status", "--interval", "10", "--compact",
        ], timeout=1200)
        deployed = json.loads(run([
            GH, "run", "view", receipt["workflow_run_id"], "--repo", REPOSITORY,
            "--json", "headSha,status,conclusion,url",
        ], capture=True))
        if deployed["headSha"] != commit or deployed["conclusion"] != "success":
            raise ValueError(f"The expected Pages revision was not deployed: {deployed}")
        receipt.update(published=True, stage="published")
        receipt.pop("error", None)
        run([sys.executable, "-X", "utf8", str(ROOT / "scripts/site_workflow.py"), "publication"], input=json.dumps(receipt))
        print(json.dumps(receipt, ensure_ascii=False), flush=True)
    finally:
        error = sys.exception()
        if error is not None:
            receipt.update(published=False, error="".join(traceback.format_exception(error)))
            save(receipt)


if __name__ == "__main__":
    publish()
