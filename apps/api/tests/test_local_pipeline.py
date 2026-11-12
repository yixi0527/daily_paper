"""Exercise the real Windows runner and its failure/resume boundaries."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows Task Scheduler runner")
GIT = r"C:\Program Files\Git\cmd\git.exe"
GUARD = r"C:\Users\yixi0\.codex\bin\CodexPowerShellGuard.exe"


@pytest.fixture()
def local_pipeline(tmp_path):
    root = Path(__file__).resolve().parents[3]
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    runner = scripts / "run_sites_update.ps1"
    shutil.copyfile(root / "scripts/run_sites_update.ps1", runner)
    subprocess.run([GIT, "init", str(tmp_path)], check=True, capture_output=True)
    runtime = tmp_path / "data/site-workflow"
    runtime.mkdir(parents=True)
    (scripts / "site_workflow.py").write_text(
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "runtime = Path(os.environ['DAILY_PAPER_RUNTIME_DIR'])\n"
        "with (runtime / 'calls.txt').open('a') as output: output.write('update\\n')\n"
        "state = json.loads((runtime / 'state.json').read_text())\n"
        "if state['fail_update']: sys.exit(7)\n"
        "state.update(status='ready', stage='publish')\n"
        "(runtime / 'state.json').write_text(json.dumps(state))\n",
        encoding="utf-8",
    )
    (scripts / "publish_github_pages.py").write_text(
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "runtime = Path(os.environ['DAILY_PAPER_RUNTIME_DIR'])\n"
        "with (runtime / 'calls.txt').open('a') as output: output.write('publish\\n')\n"
        "state = json.loads((runtime / 'state.json').read_text())\n"
        "if state['fail_publish']: sys.exit(9)\n"
        "state.update(status='published')\n"
        "(runtime / 'state.json').write_text(json.dumps(state))\n",
        encoding="utf-8",
    )
    return runner, runtime


@pytest.mark.parametrize(
    ("status", "fail_update", "expected_exit", "expected_calls"),
    [
        ("failed", False, 0, ["update", "publish"]),
        ("failed", True, 7, ["update"]),
        ("ready", True, 0, ["publish"]),
    ],
)
def test_local_run_orders_stages_and_never_publishes_failed_updates(
    local_pipeline, status, fail_update, expected_exit, expected_calls
):
    runner, runtime = local_pipeline
    (runtime / "state.json").write_text(json.dumps({
        "status": status, "stage": "sync", "date": "2000-01-01",
        "fail_update": fail_update, "fail_publish": False,
    }), encoding="utf-8")
    result = subprocess.run([GUARD, "--run-file", str(runner)], capture_output=True, text=True)
    assert result.returncode == expected_exit, result.stderr
    assert (runtime / "calls.txt").read_text().splitlines() == expected_calls


def test_publication_retry_keeps_the_prepared_batch(local_pipeline):
    runner, runtime = local_pipeline
    state = {
        "status": "ready", "stage": "publish", "date": "2000-01-01",
        "run_id": "saved-batch", "fail_update": True, "fail_publish": True,
    }
    state_path = runtime / "state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    result = subprocess.run([GUARD, "--run-file", str(runner)], capture_output=True, text=True)
    assert result.returncode == 9, result.stderr
    assert json.loads(state_path.read_text()) == state
    state['fail_publish'] = False
    state_path.write_text(json.dumps(state), encoding="utf-8")
    result = subprocess.run([GUARD, "--run-file", str(runner)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (runtime / "calls.txt").read_text().splitlines() == ["publish", "publish"]
    assert json.loads(state_path.read_text())["run_id"] == "saved-batch"
