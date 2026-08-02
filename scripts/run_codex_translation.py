from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MODEL = "gpt-5.3-codex-spark"


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_output(batch_path: Path, output_path: Path) -> None:
    batch = read_json(batch_path)
    output = read_json(output_path)
    expected_keys = [item["article_key"] for item in batch["articles"]]
    translations = output.get("translations")
    if not isinstance(translations, list):
        raise ValueError(f"Missing translations array: {output_path}")
    actual_keys = [item.get("article_key") for item in translations]
    if len(actual_keys) != len(expected_keys) or set(actual_keys) != set(expected_keys):
        missing = sorted(set(expected_keys) - set(actual_keys))
        extra = sorted(set(actual_keys) - set(expected_keys))
        raise ValueError(
            "Translation keys do not match the batch input: "
            f"expected={len(expected_keys)} actual={len(actual_keys)} "
            f"missing={missing} extra={extra} output={output_path}"
        )


def run_batch(
    *,
    codex_executable: Path,
    project_root: Path,
    schema_path: Path,
    batch_path: Path,
    resume: bool,
) -> None:
    output_path = batch_path.with_suffix(".output.json")
    log_path = batch_path.with_suffix(".codex.log")
    if output_path.exists():
        if not resume:
            raise FileExistsError(output_path)
        validate_output(batch_path, output_path)
        return
    prompt = (
        f"Read {batch_path}. Translate every article title and available abstract into accurate, "
        "natural Simplified Chinese suitable for neuroscience and AI researchers. Preserve technical "
        "terms, abbreviations, section labels, numbers, and study design meaning. Do not summarize or "
        "add commentary. For an input whose abstract is null, set abstract_zh to null. Return exactly "
        "one translation for every input article, in the same order, and match the supplied JSON schema."
    )
    command = [
        str(codex_executable),
        "exec",
        "--model",
        MODEL,
        "--config",
        'model_reasoning_effort="low"',
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--color",
        "never",
        "--cd",
        str(project_root),
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(output_path),
        prompt,
    ]
    with log_path.open("w", encoding="utf-8") as log_file:
        subprocess.run(
            command,
            cwd=project_root,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            check=True,
        )
    validate_output(batch_path, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate article batches with Codex Spark")
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--codex-executable", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "scripts" / "translation-output.schema.json"
    if not args.codex_executable.is_file():
        raise FileNotFoundError(args.codex_executable)
    if not schema_path.is_file():
        raise FileNotFoundError(schema_path)
    manifest = read_json(args.work_dir / "manifest.json")
    batch_files = manifest["batch_files"]
    if args.workers < 1:
        raise ValueError("workers must be at least 1")
    for group_start in range(0, len(batch_files), args.workers):
        group = batch_files[group_start : group_start + args.workers]
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = []
            for group_offset, batch_file in enumerate(group):
                index = group_start + group_offset + 1
                batch_path = args.work_dir / batch_file
                print(
                    f"Translating batch {index}/{len(batch_files)}: {batch_path.name}",
                    flush=True,
                )
                futures.append(
                    executor.submit(
                        run_batch,
                        codex_executable=args.codex_executable,
                        project_root=project_root,
                        schema_path=schema_path,
                        batch_path=batch_path,
                        resume=args.resume,
                    )
                )
            for future in futures:
                future.result()
    print(json.dumps({"translated_batches": len(batch_files), "model": MODEL}))


if __name__ == "__main__":
    main()
