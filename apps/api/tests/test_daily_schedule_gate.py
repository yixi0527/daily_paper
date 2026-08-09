from datetime import date
from pathlib import Path
from runpy import run_path
from zoneinfo import ZoneInfo

import pytest


def schedule_gate_globals() -> dict:
    project_root = Path(__file__).resolve().parents[3]
    return run_path(str(project_root / "scripts" / "validate_daily_schedule_run.py"))


def successful_schedule_run() -> dict:
    return {
        "databaseId": 31270513592,
        "status": "completed",
        "conclusion": "success",
        "event": "schedule",
        "createdAt": "2026-08-08T17:52:33Z",
        "headSha": "b" * 40,
        "url": "https://github.com/yixi0527/daily_paper/actions/runs/31270513592",
    }


def test_schedule_gate_converts_utc_into_shanghai_date() -> None:
    validate_schedule_run = schedule_gate_globals()["validate_schedule_run"]

    result = validate_schedule_run(
        successful_schedule_run(),
        timezone=ZoneInfo("Asia/Shanghai"),
        expected_date=date(2026, 8, 9),
    )

    assert result["database_id"] == "31270513592"
    assert result["created_at_local"] == "2026-08-09T01:52:33+08:00"
    assert result["local_date"] == "2026-08-09"


def test_schedule_gate_rejects_previous_shanghai_date() -> None:
    validate_schedule_run = schedule_gate_globals()["validate_schedule_run"]
    run = successful_schedule_run()
    run["createdAt"] = "2026-08-08T15:52:33Z"

    with pytest.raises(ValueError, match="outside the expected local date"):
        validate_schedule_run(
            run,
            timezone=ZoneInfo("Asia/Shanghai"),
            expected_date=date(2026, 8, 9),
        )


def test_schedule_gate_rejects_incomplete_run() -> None:
    validate_schedule_run = schedule_gate_globals()["validate_schedule_run"]
    run = successful_schedule_run()
    run["status"] = "in_progress"
    run["conclusion"] = ""

    with pytest.raises(ValueError, match="status must be completed"):
        validate_schedule_run(
            run,
            timezone=ZoneInfo("Asia/Shanghai"),
            expected_date=date(2026, 8, 9),
        )


def test_schedule_gate_requires_exactly_one_run() -> None:
    parse_run_list = schedule_gate_globals()["parse_run_list"]

    with pytest.raises(ValueError, match="Expected one latest schedule run"):
        parse_run_list("[]")
