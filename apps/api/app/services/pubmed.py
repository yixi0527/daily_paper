from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

from app.services.http import HTTPClientService
from app.utils.text import normalize_space
from rapidfuzz import fuzz


class PubMedClientService:
    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, http: HTTPClientService) -> None:
        self.http = http

    def fetch_metadata(
        self,
        *,
        doi: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any] | None:
        for term, source in self._build_search_terms(doi=doi, title=title):
            pmid = self._search_pmid(term)
            if not pmid:
                continue
            record = self._fetch_record(pmid)
            if not record:
                continue
            if source == "title" and title:
                score = fuzz.WRatio(title.lower(), (record.get("title") or "").lower())
                if score < 95:
                    continue
            return record
        return None

    def _build_search_terms(self, *, doi: str | None, title: str | None) -> list[tuple[str, str]]:
        queries: list[tuple[str, str]] = []
        if doi:
            queries.append((f'"{doi}"[AID]', "doi"))
        if title:
            queries.append((f'"{title}"[Title]', "title"))
        return queries

    def _search_pmid(self, term: str) -> str | None:
        try:
            response = self.http.get(
                self.SEARCH_URL,
                params={
                    "db": "pubmed",
                    "term": term,
                    "retmode": "json",
                },
            )
            data = response.json()
        except Exception:  # noqa: BLE001
            return None
        ids = data.get("esearchresult", {}).get("idlist", [])
        return str(ids[0]) if ids else None

    def _fetch_record(self, pmid: str) -> dict[str, Any] | None:
        try:
            response = self.http.get(
                self.FETCH_URL,
                params={
                    "db": "pubmed",
                    "id": pmid,
                    "retmode": "xml",
                },
            )
            root = ElementTree.fromstring(response.text)
        except Exception:  # noqa: BLE001
            return None

        abstract_parts: list[str] = []
        for node in root.findall(".//AbstractText"):
            text = normalize_space("".join(node.itertext()))
            if not text:
                continue
            label = normalize_space(node.attrib.get("Label"))
            abstract_parts.append(f"{label}: {text}" if label else text)

        publication_types = [
            normalize_space("".join(node.itertext()))
            for node in root.findall(".//PublicationType")
            if normalize_space("".join(node.itertext()))
        ]
        article_title = normalize_space(
            "".join(node for node in root.findtext(".//ArticleTitle", default=""))
        )
        return {
            "pmid": pmid,
            "title": article_title or None,
            "abstract": " ".join(abstract_parts) or None,
            "publication_types": publication_types,
        }
