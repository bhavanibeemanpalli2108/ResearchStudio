"""Bounded public scholarly metadata retrieval; no models or paid API keys."""

from __future__ import annotations
import hashlib
import json
import os
import re
import time
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote
import httpx


class LiteratureError(RuntimeError):
    code = "literature_unavailable"


def _text(value: Any, limit: int = 1000) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = unquote(
        re.sub(r"(?i)^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip())
    ).lower()
    return (
        "https://doi.org/" + quote(raw, safe="/:;().-_")
        if re.fullmatch(r'10\.\d{4,9}/[^\s<>"{}\\]{1,450}', raw)
        else None
    )


def _inverted_abstract(value: Any) -> str | None:
    if not isinstance(value, dict) or len(value) > 3000:
        return None
    positions: dict[int, str] = {}
    for word, indexes in value.items():
        if not isinstance(word, str) or not isinstance(indexes, list):
            return None
        for index in indexes:
            if type(index) is not int or not 0 <= index < 4000 or index in positions:
                return None
            positions[index] = word
    if not positions or set(positions) != set(range(len(positions))):
        return None
    return " ".join(positions[i] for i in range(len(positions)))


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _abstract(value: Any) -> tuple[str | None, bool]:
    if not isinstance(value, str) or not value.strip():
        return None, False
    parser = _PlainText()
    try:
        parser.feed(value[:40000])
    except (ValueError, AssertionError):
        return None, False
    plain = " ".join(" ".join(parser.parts).split())
    return plain[:2000] or None, len(plain) > 2000 or len(value) > 40000


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix("." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


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
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(8, connect=4), trust_env=False, follow_redirects=False
        )
        self.environ = environ if environ is not None else os.environ
        self.ttl_seconds = ttl_seconds

    def close(self) -> None:
        self.client.close()

    def _request(self, source: str, query: str, limit: int) -> dict[str, Any]:
        """One request, no retries; serialize per cache/source across processes."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        lock = self.cache_dir / f"{source}.lock"
        cooldown = self.cache_dir / f"{source}.cooldown.json"
        try:
            if lock.exists() and time.time() - lock.stat().st_mtime > 60:
                lock.unlink(missing_ok=True)
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        except FileExistsError:
            raise LiteratureError(source + " is busy; try later") from None
        try:
            if cooldown.exists():
                try:
                    blocked = (
                        json.loads(cooldown.read_text(encoding="utf-8"))["until"] > time.time()
                    )
                except (ValueError, KeyError):
                    blocked = False
                if blocked:
                    raise LiteratureError(source + " cooldown is active; try later")
            params: dict[str, Any]
            if source == "OpenAlex":
                url = "https://api.openalex.org/works"
                params = {
                    "search": query,
                    "per-page": limit,
                    "select": "id,doi,title,publication_year,authorships,abstract_inverted_index,cited_by_count",
                }
            else:
                doi = normalize_doi(query)
                url = "https://api.crossref.org/works" + (
                    "/" + quote(unquote(doi.removeprefix("https://doi.org/")), safe="")
                    if doi
                    else ""
                )
                params = {} if doi else {"query.bibliographic": query, "rows": limit}
            # Keyless public access only: no OpenAlex prepaid key, Crossref Plus
            # key, provider credential, inherited auth or automatic billing.
            headers = {"User-Agent": "Reseon/1.1 (local scholarly metadata discovery)"}
            until = time.time() + 1
            try:
                started = time.monotonic()
                with self.client.stream("GET", url, params=params, headers=headers) as response:
                    if response.status_code == 429:
                        try:
                            retry = response.headers.get("retry-after", "60")
                            delay = (
                                float(retry)
                                if retry.isdigit()
                                else parsedate_to_datetime(retry).timestamp() - time.time()
                            )
                            delay = min(604800, max(60, delay))
                        except ValueError:
                            delay = 60
                        until = time.time() + delay
                        raise LiteratureError(
                            source + " rate limited (HTTP 429); no automatic retry"
                        )
                    if response.status_code != 200:
                        until = time.time() + 30
                        raise LiteratureError(
                            f"{source} unavailable (HTTP {response.status_code}); no citations were invented"
                        )
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > 2_000_000 or time.monotonic() - started > 12:
                            raise LiteratureError(source + " response exceeded bounded size/time")
                    data = json.loads(content)
                    if not isinstance(data, dict):
                        raise ValueError("Invalid envelope")
                    return data
            except (httpx.HTTPError, ValueError, RecursionError):
                until = time.time() + 30
                raise LiteratureError(
                    source + " metadata request failed; no citations were invented"
                ) from None
            finally:
                _atomic(cooldown, {"until": until})
        finally:
            lock.unlink(missing_ok=True)

    def _papers(
        self, source: str, data: dict[str, Any], query: str, limit: int
    ) -> list[dict[str, Any]]:
        message = data.get("message", {})
        records = (
            data.get("results")
            if source == "OpenAlex"
            else (message.get("items") if isinstance(message, dict) else None)
        )
        if (
            source == "Crossref"
            and normalize_doi(query)
            and isinstance(message, dict)
            and message.get("DOI")
        ):
            records = [message]
        if not isinstance(records, list):
            raise LiteratureError(source + " returned an invalid metadata envelope")
        retrieved = datetime.now(timezone.utc).isoformat()
        result = []
        for work in records[:limit]:
            if not isinstance(work, dict):
                continue
            if source == "OpenAlex":
                source_id = work.get("id", "")
                if not isinstance(source_id, str) or not re.fullmatch(
                    r"https://openalex.org/W\d+", source_id
                ):
                    continue
                title = _text(work.get("title"))
                doi = normalize_doi(work.get("doi"))
                year = work.get("publication_year")
                authors = [
                    _text(a.get("author", {}).get("display_name"), 200)
                    for a in (work.get("authorships") or [])[:20]
                    if isinstance(a, dict) and isinstance(a.get("author"), dict)
                ]
                abstract, truncated = _abstract(
                    _inverted_abstract(work.get("abstract_inverted_index"))
                )
                citation = {}
            else:
                doi = normalize_doi(work.get("DOI"))
                if not doi:
                    continue
                source_id = "https://api.crossref.org/works/" + quote(
                    unquote(doi.removeprefix("https://doi.org/")), safe=""
                )
                titles = work.get("title", [])
                title = _text(titles[0]) if isinstance(titles, list) and titles else ""
                dates = work.get("published") or work.get("issued") or {}
                parts = dates.get("date-parts", [[]]) if isinstance(dates, dict) else []
                year = (
                    parts[0][0]
                    if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]
                    else None
                )
                authors = [
                    _text(
                        " ".join(filter(None, (_text(a.get(k), 200) for k in ("given", "family"))))
                        or a.get("name"),
                        200,
                    )
                    for a in (work.get("author") or [])[:20]
                    if isinstance(a, dict)
                ]
                abstract, truncated = _abstract(work.get("abstract"))
                citation = {
                    key: _text(work.get(key))
                    for key in ("publisher", "volume", "issue", "page")
                    if isinstance(work.get(key), str)
                }
                if isinstance(work.get("container-title"), list) and work["container-title"]:
                    citation["journal"] = _text(work["container-title"][0])
            if not title:
                continue
            result.append(
                {
                    "id": doi or source_id,
                    "title": title,
                    "authors": [a for a in authors if a],
                    "year": year if type(year) is int and 1000 <= year <= 3000 else None,
                    "doi": doi,
                    "url": doi or source_id,
                    "source": source,
                    "abstract": abstract,
                    "abstract_truncated": truncated,
                    "abstract_source": source if abstract else None,
                    "citation_metadata": citation,
                    "verified": True,
                    "verification": "Source metadata retrieved; findings, relevance and novelty are not independently verified.",
                    "retrieved_at": retrieved,
                    "provenance": [
                        {"source": source, "source_id": source_id, "retrieved_at": retrieved}
                    ],
                }
            )
        return result

    def _search(self, query: str, limit: int, sources: tuple[str, ...]) -> dict[str, Any]:
        query, limit = _text(query, 500), max(1, min(int(limit), 10))
        if not query:
            return {"papers": [], "warnings": [], "cached": False}
        cache = self.cache_dir / ("v2-" + _hash([query.casefold(), limit, sources]) + ".json")
        try:
            if cache.is_file() and time.time() - cache.stat().st_mtime < self.ttl_seconds:
                if cache.is_symlink() or cache.stat().st_size > 1_000_000:
                    raise ValueError("Invalid query cache")
                value = json.loads(cache.read_text(encoding="utf-8"))
                if (
                    not isinstance(value, dict)
                    or not isinstance(value.get("papers"), list)
                    or len(value["papers"]) > 10
                ):
                    raise ValueError("Invalid query cache")
                for paper in value["papers"]:
                    if _hash({k: v for k, v in paper.items() if k != "selection_id"}) != paper.get(
                        "selection_id"
                    ):
                        raise ValueError("Changed cached metadata")
                self.resolve_selected([paper["selection_id"] for paper in value["papers"]])
                return {**value, "cached": True}
        except (OSError, ValueError, TypeError, AttributeError, LiteratureError):
            pass
        papers: dict[str, dict[str, Any]] = {}
        ranks: dict[str, tuple[int, int]] = {}
        warnings = []
        for source_number, source in enumerate(sources):
            try:
                for rank, paper in enumerate(
                    self._papers(source, self._request(source, query, limit), query, limit)
                ):
                    ranks[paper["id"]] = min(
                        ranks.get(paper["id"], (100, 100)), (rank, source_number)
                    )
                    if paper["id"] in papers:
                        old = papers[paper["id"]]
                        old["provenance"].extend(paper["provenance"])
                        if not old["abstract"] and paper["abstract"]:
                            for key in ("abstract", "abstract_source", "abstract_truncated"):
                                old[key] = paper[key]
                        old["citation_metadata"].update(paper["citation_metadata"])
                        for key in ("authors", "year"):
                            if not old[key] and paper[key]:
                                old[key] = paper[key]
                    else:
                        papers[paper["id"]] = paper
            except (LiteratureError, OSError, TypeError, AttributeError) as error:
                warnings.append(
                    str(error)
                    if isinstance(error, LiteratureError)
                    else source + " metadata unavailable"
                )
        chosen = [papers[key] for key in sorted(papers, key=lambda key: ranks[key])[:limit]]
        for paper in chosen:
            selection_id = _hash(paper)
            try:
                _atomic(self.cache_dir / "papers" / (selection_id + ".json"), paper)
                paper["selection_id"] = selection_id
            except OSError:
                paper["selection_id"] = None
                warnings.append("Local selection cache unavailable; paper cannot be attached")
        result = {"papers": chosen, "warnings": list(dict.fromkeys(warnings)), "cached": False}
        if not warnings:
            try:
                _atomic(cache, result)
            except OSError:
                pass
        return result

    def discover(self, query: str, limit: int = 10) -> dict[str, Any]:
        return self._search(query, limit, ("OpenAlex", "Crossref"))

    def search(self, query: str, limit: int = 6, *, demo: bool = False) -> list[dict[str, Any]]:
        if demo:
            return []
        result = self._search(query, limit, ("OpenAlex",))
        if result["warnings"] and not result["papers"]:
            raise LiteratureError("; ".join(result["warnings"]))
        return result["papers"]

    def resolve_selected(self, identifiers: list[str]) -> list[dict[str, Any]]:
        if len(identifiers) > 10 or len(set(identifiers)) != len(identifiers):
            raise LiteratureError("Select at most ten distinct papers")
        result = []
        seen = set()
        for identifier in identifiers:
            if not re.fullmatch(r"[a-f0-9]{64}", identifier):
                raise LiteratureError("Invalid paper selection")
            path = self.cache_dir / "papers" / (identifier + ".json")
            try:
                if path.is_symlink() or path.stat().st_size > 64000:
                    raise ValueError("Invalid snapshot")
                value = json.loads(path.read_text(encoding="utf-8"))
                if _hash(value) != identifier:
                    raise ValueError("Changed snapshot")
            except (OSError, ValueError):
                raise LiteratureError(
                    "Selected paper unavailable or changed; search and select again"
                ) from None
            if value["id"] in seen:
                continue
            seen.add(value["id"])
            result.append(
                {**value, "selection_id": identifier, "selection": "explicit_user_selection"}
            )
        return result


def search_literature(
    query: str, cache_dir: str | Path, *, limit: int = 6, demo: bool = False
) -> list[dict[str, Any]]:
    client = LiteratureClient(cache_dir)
    try:
        return client.search(query, limit, demo=demo)
    finally:
        client.close()
