"""Public scholarly retrieval, cache/provenance and selected-context integration."""

import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.research_platform.backend import app as api_module
from src.research_platform.config import Settings
from src.research_platform.database import Database, Run
from src.research_platform.literature import LiteratureClient, LiteratureError, normalize_doi
from src.research_platform.services import ResearchServices


def oa():
    return {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.1000/ABC",
                "title": "A real metadata record",
                "publication_year": 2022,
                "authorships": [{"author": {"display_name": "A Author"}}],
                "abstract_inverted_index": {"Observed": [0], "metadata": [1]},
            }
        ]
    }


def cr():
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1000/abc",
                    "title": ["Same DOI"],
                    "author": [{"given": "A", "family": "Author"}],
                    "issued": {"date-parts": [[2022]]},
                    "abstract": "<jats:p>Only deposited abstract.</jats:p>",
                    "container-title": ["A journal"],
                    "volume": "4",
                },
                {"DOI": "10.1000/other", "title": ["Other paper"]},
            ]
        }
    }


def library(tmp_path, handler):
    return LiteratureClient(
        tmp_path,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        environ={"OPENALEX_API_KEY": "DO-NOT-SEND", "GROQ_API_KEY": "DO-NOT-SEND"},
    )


def test_two_public_requests_deduplicate_and_cache_snapshots(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        assert "DO-NOT-SEND" not in str(request.url) and "authorization" not in request.headers
        return httpx.Response(200, json=oa() if request.url.host == "api.openalex.org" else cr())

    client = library(tmp_path, respond)
    result = client.discover("test topic")
    assert len(calls) == 2 and len(result["papers"]) == 2 and result["warnings"] == []
    paper = result["papers"][0]
    assert paper["doi"] == "https://doi.org/10.1000/abc"
    assert paper["abstract"] == "Observed metadata"
    assert paper["citation_metadata"]["journal"] == "A journal"
    assert [p["source"] for p in paper["provenance"]] == ["OpenAlex", "Crossref"]
    assert result["papers"][1]["abstract"] is None and result["papers"][1]["authors"] == []
    assert client.discover("test topic")["cached"] and len(calls) == 2
    selected = client.resolve_selected([paper["selection_id"]])
    assert (
        selected[0]["selection"] == "explicit_user_selection"
        and selected[0]["provenance"] == paper["provenance"]
    )
    path = tmp_path / "papers" / (paper["selection_id"] + ".json")
    value = json.loads(path.read_text())
    value["title"] = "Forged title"
    path.write_text(json.dumps(value))
    with pytest.raises(LiteratureError, match="changed"):
        client.resolve_selected([paper["selection_id"]])


@pytest.mark.parametrize("failure", ["timeout", "rate_limit", "server", "invalid"])
def test_partial_failure_is_safe_and_rate_limits_are_not_retried(tmp_path, failure):
    calls = []

    def respond(request):
        calls.append(request)
        if request.url.host == "api.crossref.org":
            return httpx.Response(200, json=cr())
        if failure == "timeout":
            raise httpx.ReadTimeout("sensitive raw diagnostic")
        if failure == "rate_limit":
            return httpx.Response(429, headers={"retry-after": "120"})
        return (
            httpx.Response(503) if failure == "server" else httpx.Response(200, json={"wrong": []})
        )

    client = library(tmp_path, respond)
    result = client.discover("topic")
    assert result["papers"] and result["warnings"] and len(calls) == 2
    assert "sensitive raw diagnostic" not in str(result)
    client.discover("another topic")
    assert len(calls) == 2  # shared per-source cooldown also applies across queries


def test_abstracts_come_only_from_source_and_are_bounded(tmp_path):
    data = oa()
    data["results"][0]["abstract_inverted_index"] = {"gap": [5]}
    result = library(
        tmp_path,
        lambda r: httpx.Response(200, json=data if r.url.host == "api.openalex.org" else cr()),
    ).discover("topic")
    paper = result["papers"][0]
    assert (
        paper["abstract"] == "Only deposited abstract." and paper["abstract_source"] == "Crossref"
    )
    assert "<jats:" not in paper["abstract"]


def test_doi_lookup_uses_fixed_crossref_origin_and_limit_is_ten(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json=oa()
            if request.url.host == "api.openalex.org"
            else {"message": cr()["message"]["items"][0]},
        )

    result = library(tmp_path, respond).discover("https://doi.org/10.1000/ABC", 100)
    assert len(result["papers"]) <= 10
    assert calls[1].url.host == "api.crossref.org" and calls[1].url.path.endswith("10.1000/abc")
    assert calls[0].url.params["per-page"] == "10"
    assert normalize_doi("javascript:evil") is None


def test_no_network_when_source_busy_and_empty_results_cache(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={"results": []}
            if request.url.host == "api.openalex.org"
            else {"message": {"items": []}},
        )

    client = library(tmp_path, respond)
    assert not client.discover("empty")["papers"]
    assert client.discover("empty")["cached"] and len(calls) == 2
    with pytest.raises(LiteratureError):
        client.resolve_selected(["../escape"])


def test_search_and_attachment_api_keep_client_metadata_untrusted(tmp_path, monkeypatch):
    settings = replace(
        Settings(),
        database_url=f"sqlite:///{tmp_path / 'app.db'}",
        artifact_root=tmp_path / "artifacts",
        checkpoint_path=tmp_path / "checkpoints.db",
    )
    db = Database(settings.database_url)
    monkeypatch.setattr(
        api_module,
        "LiteratureClient",
        lambda cache: library(
            cache,
            lambda r: httpx.Response(200, json=oa() if r.url.host == "api.openalex.org" else cr()),
        ),
    )
    with TestClient(api_module.create_app(settings, database=db)) as client:
        response = client.post(
            "/api/literature/search", json={"query": "SPT scheduling", "limit": 10}
        )
        assert response.status_code == 200
        paper = response.json()["papers"][0]
        project = client.post(
            "/api/projects",
            json={
                "title": "Grounded study",
                "question": "Does shortest processing time improve scheduling?",
            },
        ).json()
        payload = {
            "profile": "free_research",
            "provider": "groq",
            "model": "openai/gpt-oss-20b",
            "selected_paper_ids": [paper["selection_id"]],
        }
        run = client.post(f"/api/projects/{project['id']}/runs", json=payload)
        assert run.status_code == 201
        snapshot = run.json()["config"]["selected_literature"]
        assert (
            snapshot[0]["title"] == paper["title"]
            and snapshot[0]["provenance"] == paper["provenance"]
        )
        payload["selected_paper_ids"] = ["a" * 64]
        assert client.post(f"/api/projects/{project['id']}/runs", json=payload).status_code == 422
        payload["selected_literature"] = [{"title": "Fake citation"}]
        assert client.post(f"/api/projects/{project['id']}/runs", json=payload).status_code == 422
        with db.sessions() as session:
            assert len(list(session.scalars(select(Run)))) == 1
        assert (
            client.post("/api/literature/search", json={"query": "a", "limit": 11}).status_code
            == 422
        )


def test_selected_context_survives_retrieval_outage_without_new_search():
    papers = [
        {
            "id": "https://doi.org/10.1000/abc",
            "title": "Selected",
            "provenance": [{"source": "Crossref"}],
        }
    ]
    service = object.__new__(ResearchServices)
    service.run_record = lambda: {"config": {"selected_literature": papers}}
    service.emit = lambda *args: None
    saved = []
    service.save_artifact = lambda *args: saved.append(args)
    assert service.literature("topic") == papers
    assert saved[0][0] == "selected-literature.json"


def test_organization_author_metadata_is_not_dropped(tmp_path):
    record = cr()
    record["message"]["items"][1]["author"] = [{"name": "Research Consortium"}]
    result = library(
        tmp_path,
        lambda r: httpx.Response(200, json=oa() if r.url.host == "api.openalex.org" else record),
    ).discover("topic")
    assert result["papers"][1]["authors"] == ["Research Consortium"]


def test_http_date_retry_after_is_honored_without_retry(tmp_path):
    import time
    from email.utils import formatdate

    retry_at = time.time() + 7200
    client = library(
        tmp_path,
        lambda r: httpx.Response(429, headers={"retry-after": formatdate(retry_at, usegmt=True)}),
    )
    assert client.discover("topic")["warnings"]
    cooldown = json.loads((tmp_path / "Crossref.cooldown.json").read_text())
    assert cooldown["until"] >= retry_at - 1
