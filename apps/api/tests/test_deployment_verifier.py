from pathlib import Path
from runpy import run_path
from urllib.parse import parse_qs, urlsplit


def verifier_globals() -> dict:
    project_root = Path(__file__).resolve().parents[3]
    return run_path(str(project_root / "scripts" / "verify_pages_deployment.py"))


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
