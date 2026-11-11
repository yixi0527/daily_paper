import json
import subprocess
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


@pytest.fixture()
def publisher(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = spec_from_file_location("pages_publisher_test", root / "scripts/publish_github_pages.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RUNTIME", tmp_path / "runtime")
    module.RUNTIME.mkdir()
    return module


def test_incomplete_article_cannot_bypass_the_metadata_gate(publisher, tmp_path):
    target = tmp_path / "assets"
    target.mkdir()
    (target / "index.json").write_text(json.dumps({"articles": [{
        "article_key": "doi:10.1000/test", "title_zh": None,
        "abstract": None, "snippet": None, "abstract_zh": None,
    }]}), encoding="utf-8")
    (target / "metadata.json").write_text(json.dumps({
        "article_count": 1, "translations": {"pending_articles": 0},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete translations"):
        publisher.validate(target)


def test_failed_migration_resumes_the_saved_run_without_retranslation(publisher, monkeypatch):
    module = publisher
    state = {"status": "published", "run_id": "prepared-batch"}
    (module.RUNTIME / "state.json").write_text(json.dumps(state), encoding="utf-8")
    module.save({
        "provider": "github-pages", "published": False, "commit_sha": "prepared-commit",
        "workflow_run_id": "42", "run_id": "prepared-batch", "stage": "deployment",
    })
    monkeypatch.setattr(module, "validate", lambda target: {})
    watches = []
    fail = True
    recorded = []

    def run(arguments, *, capture=False, **kwargs):
        if arguments[1:3] == ["rev-parse", "HEAD"]:
            return "prepared-commit\n"
        if arguments[1] == "api":
            return json.dumps({"html_url": "https://example.test/papers/"})
        if arguments[1:3] == ["run", "watch"]:
            watches.append(arguments[3])
            if fail:
                raise subprocess.CalledProcessError(1, arguments)
        if arguments[1:3] == ["run", "list"]:
            pytest.fail("An existing deployment must be resumed without creating another run")
        if arguments[1:3] == ["run", "view"]:
            return json.dumps({"headSha": "prepared-commit", "conclusion": "success"})
        if arguments[-1] == "publication":
            recorded.append(json.loads(kwargs["input"]))
        return ""

    monkeypatch.setattr(module, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        module.publish()
    failed = json.loads((module.RUNTIME / "publication.json").read_text(encoding="utf-8"))
    assert failed["published"] is False
    assert "CalledProcessError" in failed["error"]
    assert failed["workflow_run_id"] == "42"
    assert json.loads((module.RUNTIME / "state.json").read_text(encoding="utf-8")) == state
    fail = False
    module.publish()
    assert watches == ["42", "42"]
    assert recorded[0]["published"] is True
    assert recorded[0]["commit_sha"] == "prepared-commit"
