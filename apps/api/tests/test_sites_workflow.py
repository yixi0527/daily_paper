import json
from contextlib import nullcontext
from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest


@pytest.fixture()
def workflow(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = spec_from_file_location("site_workflow_under_test", root / "scripts/site_workflow.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RUNTIME", tmp_path / "runtime")
    monkeypatch.setattr(module, "initialize", lambda: module.RUNTIME.mkdir(exist_ok=True))
    monkeypatch.setattr(module, "setup_logging", lambda _: None)
    return module


def test_translation_failure_resumes_without_repeating_successful_sync(workflow, monkeypatch):
    module = workflow
    module.initialize()
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    state_path = module.RUNTIME / "state.json"
    module.write_json(state_path, {"date": today, "status": "failed", "last_sync_date": today})
    translated = False

    def unexpected_sync(*args, **kwargs):
        pytest.fail("A successful same-day sync must not be repeated")

    def export(db, target, **kwargs):
        target.mkdir(parents=True, exist_ok=True)
        article = {
            "id": "article-id",
            "article_key": "doi:10.1000/resume",
            "title_zh": "已翻译" if translated else None,
            "abstract": "Source abstract",
            "abstract_zh": "完整译文" if translated else None,
            "snippet": None,
            "authors": [],
            "online_published_at": None,
        }
        module.write_json(
            target / "site-data.json",
            {"articles": [article], "dashboard": {"latest_articles": [article]}},
        )
        module.write_json(target / "metadata.json", {"article_count": 1})

    def prepare(args):
        args.work_dir.mkdir(parents=True)
        module.write_json(args.work_dir / "manifest.json", {"pending_count": 1, "batch_files": []})

    def failed_translation(**kwargs):
        raise TimeoutError("NVIDIA request timed out in the test")

    def complete_translation(args):
        nonlocal translated
        translated = True

    monkeypatch.setattr(module, "SessionLocal", lambda: nullcontext(None))
    monkeypatch.setattr(module.SeedService, "seed_journals", lambda *args: None)
    monkeypatch.setattr(module.SyncOrchestrationService, "run", unexpected_sync)
    monkeypatch.setattr(module.StaticExportService, "export", staticmethod(export))
    monkeypatch.setattr(module, "prepare", prepare)
    monkeypatch.setattr(module, "translate_batches", failed_translation)
    monkeypatch.setattr(module, "merge", complete_translation)
    monkeypatch.setattr(module, "verify", lambda args: None)
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only")

    with pytest.raises(TimeoutError, match="NVIDIA request timed out"):
        module.update()
    failed = json.loads(state_path.read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["last_sync_date"] == today
    assert "TimeoutError: NVIDIA request timed out in the test" in failed["error"]
    assert not (module.ROOT / "apps/web/public/data/index.json").exists()

    monkeypatch.setattr(module, "translate_batches", lambda **kwargs: None)
    module.update()
    ready = json.loads(state_path.read_text(encoding="utf-8"))
    assert ready["status"] == "ready"
    assert ready["article_count"] == 1
    assert ready["run_id"] != failed["run_id"]
    monkeypatch.setattr(module, "prepare", unexpected_sync)
    module.update()
    assert json.loads(state_path.read_text(encoding="utf-8")) == ready
