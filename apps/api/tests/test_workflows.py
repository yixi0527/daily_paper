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


def test_pages_workflow_only_deploys_the_prepared_snapshot() -> None:
    workflow = load_workflow("pages-sync.yml")
    assert "schedule" not in workflow["on"]
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert workflow["concurrency"]["cancel-in-progress"] is False
    steps = workflow["jobs"]["build-and-deploy"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "validate_pages_assets.py stamp" in commands
    assert "app.cli sync" not in commands
    assert "refresh-translations" not in commands
    assert "nvidia" not in commands.lower()
    assert step_by_name(workflow, "build-and-deploy", "Upload Pages artifact")["with"]["path"] == "dist"
    assert workflow["permissions"]["pages"] == "write"
    assert workflow["permissions"]["id-token"] == "write"


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
