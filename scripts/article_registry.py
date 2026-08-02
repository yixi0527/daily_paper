from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
if not API_ROOT.is_dir():
    raise FileNotFoundError(API_ROOT)
sys.path.insert(0, str(API_ROOT))

from app.services.article_registry import build_article_key, text_sha256  # noqa: E402

SCHEMA_VERSION = 1
CJK_RE = re.compile(r"[\u3400-\u9fff]")


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def load_registry(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Registry schema_version must be {SCHEMA_VERSION}")
    if not isinstance(payload.get("articles"), dict):
        raise ValueError("Registry articles must be an object")
    return payload


def source_abstract(article: dict[str, Any]) -> tuple[str | None, str | None]:
    if article.get("abstract"):
        return article["abstract"], "abstract"
    if article.get("snippet"):
        return article["snippet"], "snippet"
    return None, None


def fetch_site_data(args: argparse.Namespace) -> None:
    request = urllib.request.Request(
        args.url,
        headers={"User-Agent": "DailyPaperRegistry/1.0"},
    )
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Site data request failed with HTTP {response.status}")
        content = response.read()
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload.get("articles"), list):
        raise ValueError("Downloaded site data does not contain an articles array")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    print(json.dumps({"article_count": len(payload["articles"]), "output": str(args.output)}))


def prepare(args: argparse.Namespace) -> None:
    if args.work_dir.exists() and any(args.work_dir.iterdir()):
        raise FileExistsError(f"Work directory must be empty: {args.work_dir}")
    args.work_dir.mkdir(parents=True, exist_ok=True)

    bundle = read_json(args.site_data)
    articles = bundle.get("articles")
    if not isinstance(articles, list) or not articles:
        raise ValueError("Site data articles must be a non-empty array")
    registry = load_registry(args.registry)
    registry_articles = registry["articles"]

    manifest_articles: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for article in articles:
        title = article["title"]
        journal_slug = article["journal"]["slug"]
        article_key = build_article_key(
            doi=article.get("doi"),
            journal_slug=journal_slug,
            title=title,
        )
        exported_key = article.get("article_key")
        if exported_key and exported_key != article_key:
            raise ValueError(f"Exported article_key mismatch for {article_key}")
        if article_key in seen_keys:
            raise ValueError(f"Duplicate article key in site data: {article_key}")
        seen_keys.add(article_key)

        abstract, abstract_field = source_abstract(article)
        existing = registry_articles.get(article_key)
        acquired_at = (
            existing["acquired_at"]
            if existing is not None
            else article.get("acquired_at") or args.default_acquired_at
        )
        if not acquired_at:
            raise ValueError(f"Missing acquired_at for {article_key}")
        source_title_sha256 = text_sha256(title)
        source_abstract_sha256 = text_sha256(abstract)
        manifest_item = {
            "article_key": article_key,
            "doi": article.get("doi"),
            "journal_slug": journal_slug,
            "title": title,
            "abstract": abstract,
            "abstract_source": abstract_field,
            "acquired_at": acquired_at,
            "source_title_sha256": source_title_sha256,
            "source_abstract_sha256": source_abstract_sha256,
        }
        manifest_articles.append(manifest_item)

        translation_is_current = (
            existing is not None
            and existing.get("source_title_sha256") == source_title_sha256
            and existing.get("source_abstract_sha256") == source_abstract_sha256
            and bool(existing.get("title_zh"))
            and CJK_RE.search(existing["title_zh"]) is not None
            and (abstract is None or bool(existing.get("abstract_zh")))
            and (
                abstract is None or CJK_RE.search(existing["abstract_zh"]) is not None
            )
            and existing.get("translation_model") == args.model
        )
        if not translation_is_current:
            pending.append(
                {
                    "article_key": article_key,
                    "title": title,
                    "abstract": abstract,
                }
            )

    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_source_chars = 0
    for item in pending:
        item_source_chars = len(item["title"]) + len(item["abstract"] or "")
        exceeds_count = len(current_batch) >= args.batch_size
        exceeds_characters = (
            bool(current_batch)
            and current_source_chars + item_source_chars > args.max_source_chars
        )
        if exceeds_count or exceeds_characters:
            batches.append(current_batch)
            current_batch = []
            current_source_chars = 0
        current_batch.append(item)
        current_source_chars += item_source_chars
    if current_batch:
        batches.append(current_batch)

    batch_files: list[str] = []
    for batch_number, batch in enumerate(batches, start=1):
        batch_path = args.work_dir / f"batch-{batch_number:04d}.json"
        write_json(batch_path, {"articles": batch})
        batch_files.append(batch_path.name)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "model": args.model,
        "source_site_data": str(args.site_data),
        "article_count": len(manifest_articles),
        "pending_count": len(pending),
        "batch_size": args.batch_size,
        "max_source_chars": args.max_source_chars,
        "total_source_chars": sum(
            len(item["title"]) + len(item["abstract"] or "") for item in pending
        ),
        "batch_files": batch_files,
        "articles": manifest_articles,
    }
    manifest_path = args.work_dir / "manifest.json"
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "article_count": len(manifest_articles),
                "pending_count": len(pending),
                "batch_count": len(batch_files),
                "manifest": str(manifest_path),
            }
        )
    )


def validate_translation(
    translation: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    if translation.get("article_key") != expected["article_key"]:
        raise ValueError(f"Unexpected translation key: {translation.get('article_key')}")
    if not isinstance(translation.get("title_zh"), str) or not translation["title_zh"].strip():
        raise ValueError(f"Missing title_zh for {expected['article_key']}")
    if CJK_RE.search(translation["title_zh"]) is None:
        raise ValueError(f"title_zh contains no Chinese text for {expected['article_key']}")
    abstract_zh = translation.get("abstract_zh")
    if expected["abstract"] is not None and (
        not isinstance(abstract_zh, str) or not abstract_zh.strip()
    ):
        raise ValueError(f"Missing abstract_zh for {expected['article_key']}")
    if expected["abstract"] is not None and CJK_RE.search(abstract_zh) is None:
        raise ValueError(f"abstract_zh contains no Chinese text for {expected['article_key']}")
    if expected["abstract"] is None and abstract_zh is not None:
        raise ValueError(f"abstract_zh must be null for {expected['article_key']}")


def merge(args: argparse.Namespace) -> None:
    registry = load_registry(args.registry)
    manifest = read_json(args.manifest)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Manifest schema_version must be {SCHEMA_VERSION}")
    if manifest.get("model") != args.model:
        raise ValueError("Manifest model does not match merge model")

    manifest_by_key = {item["article_key"]: item for item in manifest["articles"]}
    pending_by_key: dict[str, dict[str, Any]] = {}
    for batch_file in manifest["batch_files"]:
        batch = read_json(args.manifest.parent / batch_file)
        for item in batch["articles"]:
            pending_by_key[item["article_key"]] = item
    if len(pending_by_key) != manifest["pending_count"]:
        raise ValueError("Manifest pending_count does not match batch inputs")

    translations_by_key: dict[str, dict[str, Any]] = {}
    for batch_file in manifest["batch_files"]:
        output_path = args.manifest.parent / batch_file.replace(".json", ".output.json")
        output = read_json(output_path)
        translations = output.get("translations")
        if not isinstance(translations, list):
            raise ValueError(f"Translation output must contain an array: {output_path}")
        for translation in translations:
            article_key = translation.get("article_key")
            if article_key in translations_by_key:
                raise ValueError(f"Duplicate translated article key: {article_key}")
            if article_key not in pending_by_key:
                raise ValueError(f"Unexpected translated article key: {article_key}")
            validate_translation(translation, pending_by_key[article_key])
            translations_by_key[article_key] = translation
    if set(translations_by_key) != set(pending_by_key):
        missing = sorted(set(pending_by_key) - set(translations_by_key))
        raise ValueError(f"Missing translations for keys: {missing}")

    translated_at = args.translated_at or datetime.now(tz=UTC).isoformat()
    registry_articles = registry["articles"]
    for article_key, manifest_item in manifest_by_key.items():
        existing = registry_articles.get(article_key)
        translated = translations_by_key.get(article_key)
        title_zh = translated["title_zh"].strip() if translated else existing["title_zh"]
        if translated is not None:
            abstract_zh = (
                translated["abstract_zh"].strip()
                if translated["abstract_zh"] is not None
                else None
            )
        else:
            abstract_zh = existing.get("abstract_zh") if existing else None
        registry_articles[article_key] = {
            "doi": manifest_item["doi"],
            "journal_slug": manifest_item["journal_slug"],
            "title": manifest_item["title"],
            "acquired_at": existing["acquired_at"] if existing else manifest_item["acquired_at"],
            "source_title_sha256": manifest_item["source_title_sha256"],
            "source_abstract_sha256": manifest_item["source_abstract_sha256"],
            "source_abstract": manifest_item["abstract_source"],
            "title_zh": title_zh,
            "abstract_zh": abstract_zh,
            "translation_model": args.model,
            "translated_at": translated_at if translated else existing["translated_at"],
        }

    registry["updated_at"] = translated_at
    registry["articles"] = dict(sorted(registry_articles.items()))
    write_json(args.registry, registry)
    print(
        json.dumps(
            {
                "registry_count": len(registry_articles),
                "translated_count": len(translations_by_key),
                "registry": str(args.registry),
            }
        )
    )


def verify(args: argparse.Namespace) -> None:
    bundle = read_json(args.site_data)
    registry = load_registry(args.registry)
    verified = 0
    for article in bundle["articles"]:
        article_key = build_article_key(
            doi=article.get("doi"),
            journal_slug=article["journal"]["slug"],
            title=article["title"],
        )
        entry = registry["articles"].get(article_key)
        if entry is None:
            raise ValueError(f"Registry entry missing for {article_key}")
        abstract, _ = source_abstract(article)
        if entry["source_title_sha256"] != text_sha256(article["title"]):
            raise ValueError(f"Title hash is stale for {article_key}")
        if entry["source_abstract_sha256"] != text_sha256(abstract):
            raise ValueError(f"Abstract hash is stale for {article_key}")
        if not entry["title_zh"]:
            raise ValueError(f"Title translation missing for {article_key}")
        if CJK_RE.search(entry["title_zh"]) is None:
            raise ValueError(f"Title translation contains no Chinese text for {article_key}")
        if abstract is not None and not entry["abstract_zh"]:
            raise ValueError(f"Abstract translation missing for {article_key}")
        if abstract is not None and CJK_RE.search(entry["abstract_zh"]) is None:
            raise ValueError(f"Abstract translation contains no Chinese text for {article_key}")
        if entry["translation_model"] != args.model:
            raise ValueError(f"Translation model mismatch for {article_key}")
        verified += 1
    print(json.dumps({"verified_count": verified, "model": args.model}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain the persistent article registry")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--url", required=True)
    fetch_parser.add_argument("--output", required=True, type=Path)
    fetch_parser.add_argument("--timeout", type=int, default=120)
    fetch_parser.set_defaults(handler=fetch_site_data)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--site-data", required=True, type=Path)
    prepare_parser.add_argument("--registry", required=True, type=Path)
    prepare_parser.add_argument("--work-dir", required=True, type=Path)
    prepare_parser.add_argument("--model", default="gpt-5.3-codex-spark")
    prepare_parser.add_argument("--batch-size", type=int, default=30)
    prepare_parser.add_argument("--max-source-chars", type=int, default=24000)
    prepare_parser.add_argument("--default-acquired-at")
    prepare_parser.set_defaults(handler=prepare)

    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument("--manifest", required=True, type=Path)
    merge_parser.add_argument("--registry", required=True, type=Path)
    merge_parser.add_argument("--model", default="gpt-5.3-codex-spark")
    merge_parser.add_argument("--translated-at")
    merge_parser.set_defaults(handler=merge)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--site-data", required=True, type=Path)
    verify_parser.add_argument("--registry", required=True, type=Path)
    verify_parser.add_argument("--model", default="gpt-5.3-codex-spark")
    verify_parser.set_defaults(handler=verify)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
