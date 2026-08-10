import argparse
from pathlib import Path
from runpy import run_path
from urllib.parse import parse_qs, urlsplit

import pytest


def verifier_globals() -> dict:
    project_root = Path(__file__).resolve().parents[3]
    return run_path(str(project_root / "scripts" / "verify_pages_deployment.py"))


def pages_deploy_globals() -> dict:
    project_root = Path(__file__).resolve().parents[3]
    return run_path(str(project_root / "scripts" / "pages_deploy.py"))


def test_cache_busted_url_preserves_existing_query() -> None:
    cache_busted_url = verifier_globals()["cache_busted_url"]

    result = cache_busted_url(
        "https://example.test/data/metadata.json?existing=value",
        "workflow-123-attempt-2",
    )

    parsed = urlsplit(result)
    assert parsed.scheme == "https"
    assert parsed.netloc == "example.test"
    assert parsed.path == "/data/metadata.json"
    assert parse_qs(parsed.query) == {
        "existing": ["value"],
        "deployment_check": ["workflow-123-attempt-2"],
    }


def test_deployment_verifier_defaults_to_canonical_metadata_url() -> None:
    globals_ = verifier_globals()
    parser = globals_["build_parser"]()

    args = parser.parse_args(
        [
            "--output",
            "metadata.json",
            "--expected-workflow-run-id",
            "123",
            "--expected-source-revision",
            "a" * 40,
            "--expected-source-event",
            "schedule",
            "--expected-sync-date",
            "2026-08-10",
            "--timezone",
            "Asia/Shanghai",
        ]
    )

    assert args.url == globals_["CANONICAL_METADATA_URL"]


def test_deployment_verifier_rejects_noncanonical_metadata_url() -> None:
    canonical_metadata_url = verifier_globals()["canonical_metadata_url"]

    with pytest.raises(argparse.ArgumentTypeError, match="canonical endpoint"):
        canonical_metadata_url(
            "https://yixi0527.github.io/daily_paper/data/site-metadata.json"
        )


def test_translation_refresh_cache_key_preserves_existing_query() -> None:
    cache_busted_url = pages_deploy_globals()["cache_busted_url"]

    result = cache_busted_url(
        "https://example.test/data/site-data.json?existing=value",
        "workflow-456-site-data",
    )

    parsed = urlsplit(result)
    assert parse_qs(parsed.query) == {
        "existing": ["value"],
        "deployment_refresh": ["workflow-456-site-data"],
    }
