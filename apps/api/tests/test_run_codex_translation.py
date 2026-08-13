import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


@pytest.fixture()
def translation_runner(monkeypatch):
    project_root = Path(__file__).resolve().parents[3]
    scripts_dir = project_root / "scripts"
    script_path = scripts_dir / "run_codex_translation.py"
    monkeypatch.syspath_prepend(str(scripts_dir))
    spec = spec_from_file_location("run_codex_translation_under_test", script_path)
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


def prepare_runner_paths(
    tmp_path: Path,
    articles: list[dict[str, str | None]],
) -> tuple[Path, Path, Path]:
    batch_path = tmp_path / "batch-0001.json"
    codex_executable = tmp_path / "codex.exe"
    spark_schema_path = tmp_path / "spark-schema.json"
    write_json(batch_path, {"articles": articles})
    codex_executable.write_bytes(b"")
    write_json(spark_schema_path, {"type": "object"})
    return batch_path, codex_executable, spark_schema_path


def test_run_batch_sends_only_source_text_and_binds_article_key(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
) -> None:
    batch_path, codex_executable, spark_schema_path = prepare_runner_paths(
        tmp_path,
        articles,
    )
    raw_translations = [
        {"title_zh": "神经科学标题", "abstract_zh": "神经科学摘要。"},
    ]
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        raw_output_index = command.index("--output-last-message") + 1
        raw_output_path = Path(command[raw_output_index])
        captured["raw_output_path"] = raw_output_path
        write_json(raw_output_path, {"translations": raw_translations})

    monkeypatch.setattr(translation_runner.subprocess, "run", fake_run)

    translation_runner.run_batch(
        codex_executable=codex_executable,
        spark_schema_path=spark_schema_path,
        batch_path=batch_path,
        resume=False,
    )

    command = captured["command"]
    assert command[-1] == translation_runner.TRANSLATION_PROMPT
    source_payload = json.loads(captured["input"])
    assert source_payload == {
        "source_texts": [
            {
                "title": "First neuroscience title",
                "abstract": "First neuroscience abstract.",
            }
        ]
    }
    assert "article_key" not in captured["input"]
    assert translation_runner.TRANSLATION_PROMPT not in captured["input"]

    raw_output_path = captured["raw_output_path"]
    assert isinstance(raw_output_path, Path)
    raw_output = json.loads(raw_output_path.read_text(encoding="utf-8"))
    assert all(
        set(translation) == {"title_zh", "abstract_zh"}
        for translation in raw_output["translations"]
    )

    final_output = json.loads(
        batch_path.with_suffix(".output.json").read_text(encoding="utf-8")
    )
    assert final_output == {
        "translations": [
            {
                "article_key": "doi:10.1000/first",
                "title_zh": "神经科学标题",
                "abstract_zh": "神经科学摘要。",
            },
        ]
    }


@pytest.mark.parametrize(
    ("source_abstract", "raw_translations", "error_match"),
    [
        (
            "First neuroscience abstract.",
            [],
            "count does not match",
        ),
        (
            "First neuroscience abstract.",
            [
                {
                    "article_key": "doi:10.1000/first",
                    "title_zh": "神经科学标题",
                    "abstract_zh": "神经科学摘要。",
                },
            ],
            "must contain only Chinese fields",
        ),
        (
            "First neuroscience abstract.",
            [
                {
                    "title_zh": "First neuroscience title",
                    "abstract_zh": "神经科学摘要。",
                },
            ],
            "contains no Chinese text",
        ),
        (
            "First neuroscience abstract.",
            [
                {"title_zh": "神经科学标题", "abstract_zh": None},
            ],
            "Missing abstract_zh",
        ),
        (
            None,
            [
                {
                    "title_zh": "神经科学标题",
                    "abstract_zh": "不应生成摘要。",
                },
            ],
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
def test_invalid_spark_output_does_not_publish_final_output(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
    source_abstract,
    raw_translations,
    error_match,
) -> None:
    test_articles = [{**articles[0], "abstract": source_abstract}]
    batch_path, codex_executable, spark_schema_path = prepare_runner_paths(
        tmp_path,
        test_articles,
    )

    def fake_run(command, **kwargs):
        raw_output_index = command.index("--output-last-message") + 1
        raw_output_path = Path(command[raw_output_index])
        write_json(raw_output_path, {"translations": raw_translations})

    monkeypatch.setattr(translation_runner.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match=error_match):
        translation_runner.run_batch(
            codex_executable=codex_executable,
            spark_schema_path=spark_schema_path,
            batch_path=batch_path,
            resume=False,
        )

    assert not batch_path.with_suffix(".output.json").exists()


def test_multi_article_batch_is_rejected_before_spark_runs(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
) -> None:
    multi_article_batch = [
        articles[0],
        {
            "article_key": "doi:10.1000/second",
            "title": "Second AI title",
            "abstract": None,
        },
    ]
    batch_path, codex_executable, spark_schema_path = prepare_runner_paths(
        tmp_path,
        multi_article_batch,
    )

    def unexpected_run(*args, **kwargs):
        raise AssertionError("Spark must not run for a multi-article batch")

    monkeypatch.setattr(translation_runner.subprocess, "run", unexpected_run)

    with pytest.raises(ValueError, match="exactly one article"):
        translation_runner.run_batch(
            codex_executable=codex_executable,
            spark_schema_path=spark_schema_path,
            batch_path=batch_path,
            resume=False,
        )

    assert not batch_path.with_suffix(".output.json").exists()


def test_preexisting_unlocked_lock_file_does_not_block_translation(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
) -> None:
    batch_path, codex_executable, spark_schema_path = prepare_runner_paths(
        tmp_path,
        articles,
    )
    lock_path = batch_path.with_suffix(".translation.lock")
    lock_path.write_text("stale lock metadata\n", encoding="utf-8")

    def fake_run(command, **kwargs):
        raw_output_index = command.index("--output-last-message") + 1
        raw_output_path = Path(command[raw_output_index])
        write_json(
            raw_output_path,
            {
                "translations": [
                    {"title_zh": "神经科学标题", "abstract_zh": "神经科学摘要。"}
                ]
            },
        )

    monkeypatch.setattr(translation_runner.subprocess, "run", fake_run)

    translation_runner.run_batch(
        codex_executable=codex_executable,
        spark_schema_path=spark_schema_path,
        batch_path=batch_path,
        resume=False,
    )

    translation_runner.validate_output(
        batch_path,
        batch_path.with_suffix(".output.json"),
    )
    assert lock_path.is_file()


def test_resume_with_valid_final_output_skips_spark(
    tmp_path,
    monkeypatch,
    translation_runner,
    articles,
) -> None:
    batch_path, codex_executable, spark_schema_path = prepare_runner_paths(
        tmp_path,
        articles,
    )
    write_json(
        batch_path.with_suffix(".output.json"),
        {
            "translations": [
                {
                    "article_key": "doi:10.1000/first",
                    "title_zh": "神经科学标题",
                    "abstract_zh": "神经科学摘要。",
                },
            ]
        },
    )

    def unexpected_run(*args, **kwargs):
        raise AssertionError("Spark must not run when a valid final output is resumed")

    monkeypatch.setattr(translation_runner.subprocess, "run", unexpected_run)

    translation_runner.run_batch(
        codex_executable=codex_executable,
        spark_schema_path=spark_schema_path,
        batch_path=batch_path,
        resume=True,
    )

    assert list(tmp_path.glob(".batch-0001.spark-attempt-*")) == []
