from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ROOT = PROJECT_ROOT / ".github" / "workflows"


def load_workflow(name: str) -> dict:
    workflow_path = WORKFLOW_ROOT / name
    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Workflow must be a mapping: {workflow_path}")
    return payload


def step_by_name(workflow: dict, job_name: str, step_name: str) -> dict:
    steps = workflow["jobs"][job_name]["steps"]
    matching_steps = [step for step in steps if step.get("name") == step_name]
    if len(matching_steps) != 1:
        raise ValueError(
            f"Expected one step named {step_name} in {job_name}; found {len(matching_steps)}"
        )
    return matching_steps[0]


def test_pages_workflow_encodes_the_sync_deployment_contract() -> None:
    workflow = load_workflow("pages-sync.yml")

    assert workflow["on"]["schedule"] == [{"cron": "23 17 * * *"}]
    assert workflow["concurrency"] == {"group": "pages", "cancel-in-progress": False}
    assert workflow["jobs"]["build-and-deploy"]["timeout-minutes"] == 120
    assert step_by_name(workflow, "build-and-deploy", "Checkout")["uses"] == (
        "actions/checkout@v6"
    )
    assert step_by_name(workflow, "build-and-deploy", "Checkout")["with"][
        "fetch-depth"
    ] == 0
    assert step_by_name(workflow, "build-and-deploy", "Setup Python")["uses"] == (
        "actions/setup-python@v6"
    )
    assert step_by_name(workflow, "build-and-deploy", "Setup Node")["with"][
        "node-version"
    ] == "24"
    assert step_by_name(workflow, "build-and-deploy", "Configure Pages")["uses"] == (
        "actions/configure-pages@v6"
    )
    assert "npm ci" in step_by_name(workflow, "build-and-deploy", "Install dependencies")[
        "run"
    ]
    assert "scripts/pages_deploy.py mode" in step_by_name(
        workflow, "build-and-deploy", "Determine deployment mode"
    )["run"]
    assert "scripts/run_alembic.py upgrade head" in step_by_name(
        workflow, "build-and-deploy", "Prepare database and seed"
    )["run"]
    assert step_by_name(workflow, "build-and-deploy", "Prepare database and seed")[
        "if"
    ] == "steps.mode.outputs.mode == 'full'"
    assert "--require-complete" in step_by_name(
        workflow, "build-and-deploy", "Run synchronization"
    )["run"]
    export_command = step_by_name(workflow, "build-and-deploy", "Export static data")["run"]
    for required_argument in (
        "--source-revision",
        "--source-event",
        "--workflow-run-id",
    ):
        assert required_argument in export_command
    refresh_step = step_by_name(
        workflow, "build-and-deploy", "Refresh static translations"
    )
    assert refresh_step["if"] == "steps.mode.outputs.mode == 'translations'"
    assert "refresh-translations" in refresh_step["run"]
    assert step_by_name(workflow, "build-and-deploy", "Upload Pages artifact")[
        "uses"
    ] == "actions/upload-pages-artifact@v5"
    assert step_by_name(workflow, "build-and-deploy", "Deploy to GitHub Pages")[
        "uses"
    ] == "actions/deploy-pages@v5"
    assert step_by_name(workflow, "build-and-deploy", "Build static site")["env"][
        "VITE_STATIC_DATA_VERSION"
    ] == "${{ github.run_id }}"


def test_ci_uses_reproducible_node_install_and_single_head_migration() -> None:
    workflow = load_workflow("ci.yml")

    assert step_by_name(workflow, "test-and-build", "Checkout")["uses"] == (
        "actions/checkout@v6"
    )
    assert step_by_name(workflow, "test-and-build", "Setup Python")["uses"] == (
        "actions/setup-python@v6"
    )
    assert step_by_name(workflow, "test-and-build", "Setup Node")["with"][
        "node-version"
    ] == "24"
    assert step_by_name(workflow, "test-and-build", "Install Node dependencies")[
        "run"
    ] == "npm ci"
    assert "scripts/run_alembic.py upgrade head" in step_by_name(
        workflow, "test-and-build", "Run migrations and seed"
    )["run"]
    assert step_by_name(workflow, "test-and-build", "Run Python lint")["run"] == (
        "ruff check ."
    )
    assert step_by_name(workflow, "test-and-build", "Run web lint")["run"] == (
        "npm --workspace apps/web run lint"
    )
