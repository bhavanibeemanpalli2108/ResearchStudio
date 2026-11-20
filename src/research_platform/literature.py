"""Cached metadata retrieval; generated prose is never treated as a citation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


class LiteratureError(RuntimeError):
    code = "literature_unavailable"


def _text(value: Any, limit: int = 1000) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


class LiteratureClient:
    def __init__(
        self,
        cache_dir: str | Path,
        *,
        client: httpx.Client | None = None,
        environ: Mapping[str, str] | None = None,
        ttl_seconds: float = 86400,
    ):
        self.cache_dir = Path(cache_dir)
        self.client = client or httpx.Client(timeout=httpx.Timeout(20, connect=5), trust_env=False)
        self.environ = environ if environ is not None else os.environ
        self.ttl_seconds = ttl_seconds

    def close(self) -> None:
        self.client.close()

    def search(self, query: str, limit: int = 6, *, demo: bool = False) -> list[dict[str, Any]]:
        if demo:
            return []
        query = _text(query, 500)
        if not query:
            return []
        limit = max(1, min(int(limit), 10))
        identity = hashlib.sha256(json.dumps([query, limit]).encode()).hexdigest()
        cache = self.cache_dir / f"{identity}.json"
        if cache.is_file() and time.time() - cache.stat().st_mtime < self.ttl_seconds:
            try:
                values = json.loads(cache.read_text(encoding="utf-8"))
                if isinstance(values, list):
                    return values
            except (OSError, ValueError):
                pass
        params: dict[str, Any] = {
            "search": query,
            "per-page": limit,
            "select": "id,doi,title,publication_year,authorships,primary_location,cited_by_count",
        }
        if self.environ.get("OPENALEX_API_KEY"):
            params["api_key"] = self.environ["OPENALEX_API_KEY"]
        try:
            response = self.client.get(
                "https://api.openalex.org/works",
                params=params,
                headers={"User-Agent": "ResearchPlatform/0.1 (verified scholarly metadata)"},
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            raise LiteratureError(
                "OpenAlex metadata lookup failed; no citations were invented. Configure OPENALEX_API_KEY if required by the service."
            ) from None
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise LiteratureError("OpenAlex returned an unexpected metadata envelope.")
        retrieved = datetime.now(timezone.utc).isoformat()
        items: list[dict[str, Any]] = []
        for work in data["results"]:
            if not isinstance(work, dict):
                continue
            work_id = work.get("id", "")
            title = _text(work.get("title"))
            if (
                not isinstance(work_id, str)
                or not re.fullmatch(r"https://openalex.org/W[0-9]+", work_id)
                or not title
            ):
                continue
            doi = work.get("doi")
            if not isinstance(doi, str) or not doi.startswith("https://doi.org/10."):
                doi = None
            year = work.get("publication_year")
            authors = []
            authorships = work.get("authorships")
            for authorship in authorships[:20] if isinstance(authorships, list) else []:
                if isinstance(authorship, dict) and isinstance(authorship.get("author"), dict):
                    author = _text(authorship["author"].get("display_name"), 200)
                    if author:
                        authors.append(author)
            items.append(
                {
                    "id": work_id,
                    "title": title,
                    "authors": authors,
                    "year": year if isinstance(year, int) else None,
                    "doi": doi,
                    "url": doi or work_id,
                    "source": "OpenAlex",
                    "verified": True,
                    "verification": "Metadata retrieved from OpenAlex; paper contents and findings were not independently verified.",
                    "retrieved_at": retrieved,
                    "cited_by_count": work.get("cited_by_count", 0),
                }
            )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary = cache.with_suffix("." + uuid.uuid4().hex + ".tmp")
        temporary.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        temporary.replace(cache)
        return items


def search_literature(
    query: str, cache_dir: str | Path, *, limit: int = 6, demo: bool = False
) -> list[dict[str, Any]]:
    client = LiteratureClient(cache_dir)
    try:
        return client.search(query, limit, demo=demo)
    finally:
        client.close()
