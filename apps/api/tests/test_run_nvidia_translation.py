import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


class StubHttpResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


@pytest.fixture()
def translation_runner(monkeypatch):
    project_root = Path(__file__).resolve().parents[3]
    scripts_dir = project_root / "scripts"
    script_path = scripts_dir / "run_nvidia_translation.py"
    monkeypatch.syspath_prepend(str(scripts_dir))
    spec = spec_from_file_location("run_nvidia_translation_under_test", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load translation runner: {script_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def articles() -> list[dict[str, str | None]]:
    return [
        {
            "article_key": "doi:10.1000/first",
            "title": "First neuroscience title",
            "abstract": "First neuroscience abstract.",
        }
    ]


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_default_timeout_allows_slow_model_responses(translation_runner) -> None:
    assert translation_runner.DEFAULT_TIMEOUT == 300


def prepare_batch(
    tmp_path: Path,
    articles: list[dict[str, str | None]],
) -> Path:
    batch_path = tmp_path / "batch-0001.json"
    write_json(batch_path, {"articles": articles})
    return batch_path


def response_payload(translations: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": "test-response",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {"translations": translations},
                        ensure_ascii=False,
                    ),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }


def test_run_batch_posts_only_source_text_and_binds_article_key(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
) -> None:
    batch_path = prepare_batch(tmp_path, articles)
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data)
        return StubHttpResponse(
            json.dumps(
                response_payload(
                    [{"title_zh": "神经科学标题", "abstract_zh": "神经科学摘要。"}]
                ),
                ensure_ascii=False,
            ).encode("utf-8")
        )

    monkeypatch.setattr(translation_runner.urllib.request, "urlopen", fake_urlopen)

    translation_runner.run_batch(
        api_url="https://example.test/v1/chat/completions",
        api_key="secret-key",
        model=translation_runner.DEFAULT_MODEL,
        batch_path=batch_path,
        timeout=37,
        max_tokens=512,
        resume=False,
    )

    body = captured["body"]
    assert body["model"] == translation_runner.DEFAULT_MODEL
    assert body["response_format"] == {"type": "json_object"}
    assert body["temperature"] == 0
    assert json.loads(body["messages"][1]["content"]) == {
        "source_texts": [
            {
                "title": "First neuroscience title",
                "abstract": "First neuroscience abstract.",
            }
        ]
    }
    assert "article_key" not in body["messages"][1]["content"]
    assert captured["timeout"] == 37
    assert captured["request"].get_header("Authorization") == "Bearer secret-key"

    final_output = json.loads(
        batch_path.with_suffix(".output.json").read_text(encoding="utf-8")
    )
    assert final_output == {
        "translations": [
            {
                "article_key": "doi:10.1000/first",
                "title_zh": "神经科学标题",
                "abstract_zh": "神经科学摘要。",
            }
        ]
    }
    attempt_dirs = list(tmp_path.glob(".batch-0001.nvidia-attempt-*"))
    assert len(attempt_dirs) == 1
    assert (attempt_dirs[0] / "response.json").is_file()
    assert (attempt_dirs[0] / "nvidia.log").is_file()


def test_multi_article_batch_is_bound_in_response_order(
    tmp_path,
    monkeypatch,
    translation_runner,
) -> None:
    articles = [
        {
            "article_key": "doi:10.1000/first",
            "title": "First neuroscience title",
            "abstract": "First abstract.",
        },
        {
            "article_key": "doi:10.1000/second",
            "title": "Second AI title",
            "abstract": None,
        },
    ]
    batch_path = prepare_batch(tmp_path, articles)
    monkeypatch.setattr(
        translation_runner.urllib.request,
        "urlopen",
        lambda request, timeout: StubHttpResponse(
            json.dumps(
                response_payload(
                    [
                        {"title_zh": "第一篇标题", "abstract_zh": "第一篇摘要。"},
                        {"title_zh": "第二篇人工智能标题", "abstract_zh": None},
                    ]
                ),
                ensure_ascii=False,
            ).encode("utf-8")
        ),
    )

    translation_runner.run_batch(
        api_url=translation_runner.DEFAULT_API_URL,
        api_key="secret-key",
        model=translation_runner.DEFAULT_MODEL,
        batch_path=batch_path,
        timeout=120,
        max_tokens=512,
        resume=False,
    )

    output = json.loads(
        batch_path.with_suffix(".output.json").read_text(encoding="utf-8")
    )
    assert [item["article_key"] for item in output["translations"]] == [
        "doi:10.1000/first",
        "doi:10.1000/second",
    ]


@pytest.mark.parametrize(
    ("articles", "translations", "error_match"),
    [
        (
            [
                {
                    "article_key": "doi:10.1000/first",
                    "title": "First neuroscience title",
                    "abstract": "First abstract.",
                }
            ],
            [],
            "count does not match",
        ),
        (
            [
                {
                    "article_key": "doi:10.1000/first",
                    "title": "First neuroscience title",
                    "abstract": "First abstract.",
                }
            ],
            [
                {
                    "article_key": "doi:10.1000/first",
                    "title_zh": "神经科学标题",
                    "abstract_zh": "神经科学摘要。",
                }
            ],
            "only title_zh and abstract_zh",
        ),
        (
            [
                {
                    "article_key": "doi:10.1000/first",
                    "title": "First neuroscience title",
                    "abstract": "First abstract.",
                }
            ],
            [{"title_zh": "First title", "abstract_zh": "神经科学摘要。"}],
            "contains no Chinese text",
        ),
        (
            [
                {
                    "article_key": "doi:10.1000/first",
                    "title": "First neuroscience title",
                    "abstract": "First abstract.",
                }
            ],
            [{"title_zh": "神经科学标题", "abstract_zh": None}],
            "Missing abstract_zh",
        ),
        (
            [
                {
                    "article_key": "doi:10.1000/first",
                    "title": "First neuroscience title",
                    "abstract": None,
                }
            ],
            [{"title_zh": "神经科学标题", "abstract_zh": "不应生成摘要。"}],
            "abstract_zh must be null",
        ),
    ],
    ids=[
        "wrong-count",
        "extra-article-key",
        "no-cjk",
        "missing-required-abstract",
        "translated-null-abstract",
    ],
)
def test_invalid_api_output_does_not_publish_final_output(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
    translations,
    error_match,
) -> None:
    test_batch = prepare_batch(tmp_path, articles)
    monkeypatch.setattr(
        translation_runner.urllib.request,
        "urlopen",
        lambda request, timeout: StubHttpResponse(
            json.dumps(response_payload(translations), ensure_ascii=False).encode("utf-8")
        ),
    )

    with pytest.raises(ValueError, match=error_match):
        translation_runner.run_batch(
            api_url=translation_runner.DEFAULT_API_URL,
            api_key="secret-key",
            model=translation_runner.DEFAULT_MODEL,
            batch_path=test_batch,
            timeout=120,
            max_tokens=512,
            resume=False,
        )

    assert not test_batch.with_suffix(".output.json").exists()


def test_preexisting_unlocked_lock_file_does_not_block_translation(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
) -> None:
    batch_path = prepare_batch(tmp_path, articles)
    lock_path = batch_path.with_suffix(".translation.lock")
    lock_path.write_text("stale lock metadata\n", encoding="utf-8")
    monkeypatch.setattr(
        translation_runner.urllib.request,
        "urlopen",
        lambda request, timeout: StubHttpResponse(
            json.dumps(
                response_payload(
                    [{"title_zh": "神经科学标题", "abstract_zh": "神经科学摘要。"}]
                ),
                ensure_ascii=False,
            ).encode("utf-8")
        ),
    )

    translation_runner.run_batch(
        api_url=translation_runner.DEFAULT_API_URL,
        api_key="secret-key",
        model=translation_runner.DEFAULT_MODEL,
        batch_path=batch_path,
        timeout=120,
        max_tokens=512,
        resume=False,
    )

    translation_runner.validate_output(
        batch_path,
        batch_path.with_suffix(".output.json"),
    )
    assert lock_path.is_file()


def test_resume_with_valid_final_output_skips_api(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
) -> None:
    batch_path = prepare_batch(tmp_path, articles)
    write_json(
        batch_path.with_suffix(".output.json"),
        {
            "translations": [
                {
                    "article_key": "doi:10.1000/first",
                    "title_zh": "神经科学标题",
                    "abstract_zh": "神经科学摘要。",
                }
            ]
        },
    )

    def unexpected_api_call(*args, **kwargs):
        raise AssertionError("NVIDIA API must not run when a valid final output is resumed")

    monkeypatch.setattr(
        translation_runner.urllib.request,
        "urlopen",
        unexpected_api_call,
    )

    translation_runner.run_batch(
        api_url=translation_runner.DEFAULT_API_URL,
        api_key="secret-key",
        model=translation_runner.DEFAULT_MODEL,
        batch_path=batch_path,
        timeout=120,
        max_tokens=512,
        resume=True,
    )

    assert list(tmp_path.glob(".batch-0001.nvidia-attempt-*")) == []
