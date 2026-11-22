import hashlib
from datetime import datetime, timezone
import json
import contextlib
import sys
from types import SimpleNamespace

import httpx
import pytest

from src.research_platform.literature import LiteratureClient, LiteratureError
from src.research_platform.providers import (
    AuthenticationError,
    ContextBudgetError,
    ModelUnavailableError,
    ProviderError,
    ProviderRouter,
    RateLimitError,
    StructuredOutputError,
    TruncatedOutputError,
)
from src.research_platform.tracing import redacted_trace, trace_metadata, trace_root_id


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_demo_is_deterministic_and_labeled():
    router = ProviderRouter(environ={})
    first = router.complete("mock", "mock-researcher", "planning", "question")
    assert first == router.complete("mock", "mock-researcher", "planning", "question")
    assert "demonstration" in first.text
    assert first.estimated_cost == 0 and first.usage_is_estimated
    assert json.loads(first.text)["hypotheses"]


def test_missing_credential_does_not_contact_network():
    router = ProviderRouter(
        environ={}, client=client(lambda request: pytest.fail("network called"))
    )
    with pytest.raises(AuthenticationError, match="GEMINI_API_KEY"):
        router.models("gemini")


@pytest.mark.parametrize("status", [429, 503, None])
def test_failed_attempt_diagnostics_survive_a_later_budget_refusal_without_secrets(status):
    from src.research_platform.ledger import BudgetExceeded

    failures, requests, reservations = [], [], []

    def reserve(*args):
        if len(reservations) == 2:
            raise BudgetExceeded("Input reservation limit")
        reservations.append(args)

    def respond(request):
        requests.append(request)
        if status is None:
            raise httpx.ConnectError("secret-token in private transport detail", request=request)
        return httpx.Response(status, json={"error": {"message": "secret-token private body"}})

    router = ProviderRouter(
        client=client(respond),
        environ={"GEMINI_API_KEY": "secret-token"},
        on_request=reserve,
        on_failure=lambda stage, data: failures.append({"stage": stage, **data}),
        sleep=lambda _: None,
        jitter=lambda: 0,
    )
    with pytest.raises(BudgetExceeded):
        router._request(
            "gemini",
            "POST",
            "https://example.invalid/private?key=secret-token",
            request_context=("selected-model", "experiment_spec", "private prompt", 128),
        )
    assert len(requests) == len(reservations) == len(failures) == 2
    assert all(row["status_code"] == status and row["reservation_retained"] for row in failures)
    assert all(row["stage"] == "experiment_spec" for row in failures)
    assert (
        failures[0]["category"]
        == {429: "rate_limit", 503: "provider_unavailable", None: "transport_error"}[status]
    )
    assert "secret-token" not in json.dumps(failures)
    assert "private" not in json.dumps(failures)


@pytest.mark.parametrize("provider", ["gemini", "groq"])
def test_structured_schema_payload_and_compatibility_retry_are_charged(provider):
    generated, charges = [], []
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "integer"}},
        "required": ["answer"],
        "additionalProperties": False,
    }

    def respond(request):
        if request.method == "GET":
            if provider == "gemini":
                return httpx.Response(
                    200,
                    json={
                        "models": [
                            {
                                "name": "models/structured-model",
                                "supportedGenerationMethods": ["generateContent"],
                                "inputTokenLimit": 32000,
                                "outputTokenLimit": 2048,
                            }
                        ]
                    },
                )
            return httpx.Response(
                200, json={"data": [{"id": "structured-model", "context_window": 32000}]}
            )
        payload = json.loads(request.content)
        generated.append(payload)
        if len(generated) == 1:
            if provider == "gemini":
                assert payload["generationConfig"]["responseJsonSchema"] == schema
            else:
                assert payload["response_format"]["json_schema"]["schema"] == schema
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "json_schema response_format is not supported for this model"
                    }
                },
            )
        if provider == "gemini":
            assert "responseJsonSchema" not in payload["generationConfig"]
            assert "Required JSON schema" in payload["contents"][0]["parts"][0]["text"]
            return httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": [{"text": '{"answer": 42}'}]}}],
                    "usageMetadata": {"promptTokenCount": 25, "candidatesTokenCount": 8},
                },
            )
        assert payload["response_format"] == {"type": "json_object"}
        assert "Required JSON schema" in payload["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"answer": 42}'}}],
                "usage": {"prompt_tokens": 25, "completion_tokens": 8},
            },
        )

    router = ProviderRouter(
        client=client(respond),
        environ={
            "GEMINI_API_KEY": "private",
            "GROQ_API_KEY": "private",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("private".encode()).hexdigest(),
        },
        on_request=lambda *args: charges.append(args),
    )
    result = router.complete(
        provider, "structured-model", "feasibility", "Return JSON", 100, json_schema=schema
    )
    assert json.loads(result.text) == {"answer": 42}
    assert len(generated) == len(charges) == 2
    assert all("Required JSON schema" in charge[3] for charge in charges)
    assert all(charge[:2] == (provider, "structured-model") for charge in charges)


def test_unrelated_bad_request_does_not_trigger_schema_fallback():
    calls = []

    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "model", "context_window": 8192}]})
        calls.append(request)
        return httpx.Response(400, json={"error": {"message": "Input content rejected"}})

    router = ProviderRouter(
        client=client(respond),
        environ={
            "GROQ_API_KEY": "private",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("private".encode()).hexdigest(),
        },
    )
    with pytest.raises(ProviderError):
        router.complete(
            "groq", "model", "feasibility", "Return JSON", 100, json_schema={"type": "object"}
        )
    assert len(calls) == 1


def test_groq_json_validation_failure_is_typed_not_schema_compatibility_retry():
    calls = []

    def respond(request):
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": "openai/gpt-oss-20b", "context_window": 8192}]}
            )
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["reasoning_effort"] == "low" and payload["include_reasoning"] is False
        assert payload["max_completion_tokens"] == 100 and "max_tokens" not in payload
        assert "Required JSON schema" not in payload["messages"][0]["content"]
        assert payload["response_format"]["type"] == "json_schema"
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": "json_validate_failed",
                    "type": "invalid_request_error",
                    "message": "Generated JSON does not match the expected schema",
                    "failed_generation": "private reasoning should never appear in errors",
                }
            },
        )

    router = ProviderRouter(
        client=client(respond),
        environ={
            "GROQ_API_KEY": "private",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("private".encode()).hexdigest(),
        },
    )
    with pytest.raises(StructuredOutputError) as error:
        router.complete(
            "groq",
            "openai/gpt-oss-20b",
            "feasibility",
            "Return JSON",
            100,
            json_schema={"type": "object"},
        )
    assert len(calls) == 1 and error.value.details["code"] == "json_validate_failed"
    assert error.value.details["failed_generation_json_valid"] == "false"
    assert "private reasoning" not in str(error.value) and "private reasoning" not in json.dumps(
        error.value.details
    )


def test_truncated_structured_response_is_typed():
    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "model", "context_window": 8192}]})
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "length", "message": {"content": '{"incomplete":'}}]
            },
        )

    router = ProviderRouter(
        client=client(respond),
        environ={
            "GROQ_API_KEY": "private",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("private".encode()).hexdigest(),
        },
    )
    with pytest.raises(TruncatedOutputError):
        router.complete(
            "groq", "model", "feasibility", "Return JSON", 100, json_schema={"type": "object"}
        )


def test_gemini_discovery_and_completion_use_real_api_shapes():
    requests = []

    def respond(request):
        requests.append(request)
        assert request.headers["x-goog-api-key"] == "private-value"
        assert "private-value" not in str(request.url)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/discovered-gemini",
                            "supportedGenerationMethods": ["generateContent"],
                            "inputTokenLimit": 32000,
                            "outputTokenLimit": 2048,
                        }
                    ]
                },
            )
        assert json.loads(request.content)["generationConfig"]["maxOutputTokens"] == 100
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "observed reply"}]}}],
                "usageMetadata": {"promptTokenCount": 17, "candidatesTokenCount": 4},
            },
        )

    router = ProviderRouter(environ={"GEMINI_API_KEY": "private-value"}, client=client(respond))
    result = router.complete("gemini", "discovered-gemini", "planning", "question", 100)
    assert (
        result.text == "observed reply" and result.input_tokens == 17 and result.output_tokens == 4
    )
    assert result.estimated_cost is None and not result.usage_is_estimated
    assert len(requests) == 2


@pytest.mark.parametrize(
    "extra_usage,expected_output",
    [
        ({"thoughtsTokenCount": 30, "totalTokenCount": 51}, 34),
        ({"thoughtsTokenCount": 30}, 34),
        ({"totalTokenCount": 57}, 40),
    ],
)
def test_gemini_output_usage_includes_hidden_thinking(extra_usage, expected_output):
    def respond(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/thinking-model",
                            "supportedGenerationMethods": ["generateContent"],
                            "inputTokenLimit": 32000,
                            "outputTokenLimit": 2048,
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "thought": True,
                                    "text": "Internal reasoning should not be retained",
                                },
                                {"text": "Visible answer"},
                            ]
                        }
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 17,
                    "candidatesTokenCount": 4,
                    **extra_usage,
                },
            },
        )

    router = ProviderRouter(environ={"GEMINI_API_KEY": "private-value"}, client=client(respond))
    result = router.complete("gemini", "thinking-model", "planning", "question", 100)
    assert result.input_tokens == 17 and result.output_tokens == expected_output
    assert result.text == "Visible answer"
    assert not result.usage_is_estimated


def test_retry_after_and_each_attempt_budget_callback():
    attempts, waits, charges = [], [], []

    def respond(request):
        if request.method == "GET":
            return httpx.Response(
                200, json={"data": [{"id": "discovered-groq", "context_window": 8192}]}
            )
        attempts.append(request)
        if len(attempts) < 3:
            return httpx.Response(
                429, headers={"Retry-After": "3"}, json={"error": "private-value"}
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "reply"}}],
                "usage": {"prompt_tokens": 9, "completion_tokens": 2},
            },
        )

    router = ProviderRouter(
        environ={
            "GROQ_API_KEY": "private-value",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("private-value".encode()).hexdigest(),
        },
        client=client(respond),
        sleep=waits.append,
        jitter=lambda: 0,
        on_request=lambda *args: charges.append(args),
    )
    result = router.complete("groq", "discovered-groq", "ideas", "question", 100)
    assert result.text == "reply" and len(charges) == 3 and waits == [3, 3]
    assert charges[0] == ("groq", "discovered-groq", "ideas", "question", 100)


def test_quota_callback_can_stop_retry_before_request():
    calls = []

    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json={"models": [{"name": "small"}]})
        calls.append(request)
        return httpx.Response(429)

    def budget(*args):
        if calls:
            raise RuntimeError("budget exhausted")

    router = ProviderRouter(
        environ={}, client=client(respond), on_request=budget, sleep=lambda delay: None
    )
    with pytest.raises(RuntimeError, match="budget exhausted"):
        router.complete("ollama", "small", "planning", "q", 10)
    assert len(calls) == 1


def test_errors_do_not_expose_provider_body_or_credentials():
    router = ProviderRouter(
        environ={
            "GROQ_API_KEY": "private-secret",
            "GROQ_FREE_TIER_VERIFIED_AT": datetime.now(timezone.utc).isoformat(),
            "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256("private-secret".encode()).hexdigest(),
        },
        client=client(lambda request: httpx.Response(401, json={"message": "private-secret"})),
    )
    with pytest.raises(AuthenticationError) as caught:
        router.models("groq")
    assert "private-secret" not in str(caught.value)
    assert caught.value.status_code == 401


def test_429_is_typed_after_bounded_attempts():
    count = []

    def respond(request):
        count.append(request)
        return httpx.Response(429)

    router = ProviderRouter(
        environ={}, client=client(respond), sleep=lambda _: None, max_attempts=2
    )
    with pytest.raises(RateLimitError):
        router.models("ollama")
    assert len(count) == 2


def test_context_rejected_before_generation():
    router = ProviderRouter(environ={})
    with pytest.raises(ContextBudgetError):
        router.complete("mock", "mock-researcher", "planning", "x" * 100000, 1000)
    with pytest.raises(ModelUnavailableError):
        router.complete("mock", "unavailable", "planning", "q")


def test_demo_respects_small_output_budget_before_charging():
    charges = []
    router = ProviderRouter(environ={}, on_request=lambda *args: charges.append(args))
    with pytest.raises(ContextBudgetError, match="output budget"):
        router.complete("mock", "mock-researcher", "planning", "q", 10)
    assert charges == []


def test_remote_ollama_origin_is_rejected():
    router = ProviderRouter(environ={"OLLAMA_BASE_URL": "http://169.254.169.254"})
    with pytest.raises(ProviderError, match="loopback"):
        router.models("ollama")


def test_fallback_never_silently_uses_demo():
    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json={"models": [{"name": "small"}]})
        return httpx.Response(503)

    router = ProviderRouter(environ={}, client=client(respond), max_attempts=1)
    with pytest.raises(ProviderError):
        router.complete(
            "ollama",
            "small",
            "ideas",
            "q",
            10,
            allow_fallback=True,
            fallback_providers=["mock", "paid-provider"],
        )


def test_literature_caches_verified_metadata_and_never_invents(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "title": "Actual metadata title",
                        "doi": "https://doi.org/10.1000/example",
                        "publication_year": 2020,
                        "authorships": [{"author": {"display_name": "A Researcher"}}],
                    },
                    {"id": "javascript:bad", "title": "reject"},
                ]
            },
        )

    library = LiteratureClient(tmp_path, client=client(respond), environ={})
    assert library.search("q", demo=True) == [] and calls == []
    result = library.search("q")
    assert len(result) == 1 and result[0]["verified"]
    assert result[0]["authors"] == ["A Researcher"]
    assert library.search("q") == result and len(calls) == 1


def test_literature_failure_is_explicit(tmp_path):
    library = LiteratureClient(
        tmp_path, client=client(lambda request: httpx.Response(503)), environ={}
    )
    with pytest.raises(LiteratureError, match="no citations were invented"):
        library.search("q")


def test_trace_redaction_and_disabled_noop(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    result = trace_metadata(
        {"prompt": "private", "api_key": "secret", "model": "sk-private", "iteration": 2}
    )
    assert result == {"model": "[redacted]", "iteration": 2}
    with redacted_trace("test", "run-123", "planning", {"prompt": "private"}) as metadata:
        assert "prompt" not in metadata
        assert metadata["root_id"] == trace_root_id("run-123")


def test_enabled_trace_exports_empty_inputs_and_disables_automatic_children(monkeypatch):
    state = {"enabled": False}
    observed = {}

    @contextlib.contextmanager
    def tracing_context(*, enabled, **kwargs):
        old = state["enabled"]
        state["enabled"] = enabled
        try:
            yield
        finally:
            state["enabled"] = old

    class Trace:
        def __init__(self, **kwargs):
            observed.update(kwargs)

        def __enter__(self):
            assert state["enabled"]
            return SimpleNamespace(
                id="actual-sdk-id", get_url=lambda: "https://smith.langchain.com/actual-sdk-run"
            )

        def __exit__(self, *args):
            observed["exit"] = args

    monkeypatch.setitem(
        sys.modules, "langsmith", SimpleNamespace(trace=Trace, tracing_context=tracing_context)
    )
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "private-key")
    with pytest.raises(RuntimeError, match="private-error"):
        with redacted_trace(
            "safe stage", "run", "planning", {"project_id": "project-1", "prompt": "private-prompt"}
        ) as metadata:
            assert not state["enabled"]
            assert metadata["trace_url"] == "https://smith.langchain.com/actual-sdk-run"
            raise RuntimeError("private-error")
    assert observed["inputs"] == {}
    assert "private" not in json.dumps(observed)
    assert observed["metadata"]["project_id"] == "project-1"
    assert observed["exit"] == (None, None, None)
    assert not state["enabled"]


@pytest.mark.parametrize("status", [200, 404, 401, 429, 503])
def test_gemini_discovery_does_not_prove_generation_and_preflight_never_retries(status):
    posts, reservations = [], []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-2.5-flash",
                            "supportedGenerationMethods": ["generateContent"],
                            "inputTokenLimit": 8192,
                            "outputTokenLimit": 2048,
                        }
                    ]
                },
            )
        posts.append(request)
        assert str(request.url).endswith("/models/gemini-2.5-flash:generateContent")
        assert json.loads(request.content)["generationConfig"]["maxOutputTokens"] == 128
        if status == 200:
            return httpx.Response(
                200,
                json={
                    "candidates": [{"content": {"parts": [{"text": "OK"}]}}],
                    "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 1},
                },
            )
        return httpx.Response(status, json={"error": {"message": "private server detail"}})

    router = ProviderRouter(
        client=client(handler),
        environ={"GEMINI_API_KEY": "fixture-secret"},
        on_request=lambda *args: reservations.append(args),
    )
    health = router.health("gemini")
    assert health["status"] == "discovered" and health["generation_verified"] is False
    assert not posts and not reservations
    if status == 200:
        assert router.preflight("gemini", "gemini-2.5-flash").text == "OK"
    else:
        with pytest.raises(ProviderError) as error:
            router.preflight("gemini", "gemini-2.5-flash")
        assert error.value.status_code == status
        assert "private server detail" not in str(error.value)
    assert len(posts) == len(reservations) == 1
    assert reservations[0][2] == "provider_preflight"
    assert router.max_attempts == 3


def test_preflight_requires_accounting_and_does_not_claim_mock_readiness():
    router = ProviderRouter(
        client=client(lambda request: pytest.fail("network called")), environ={}
    )
    with pytest.raises(ProviderError, match="accounting"):
        router.preflight("gemini", "gemini-2.5-flash")
    router.on_request = lambda *args: None
    with pytest.raises(ProviderError, match="real provider"):
        router.preflight("mock", "mock-researcher")
    with pytest.raises(AuthenticationError):
        router.preflight("gemini", "gemini-2.5-flash")


@pytest.mark.parametrize("state", ["missing", "expired", "future", "naive", "invalid", "wrong_key"])
def test_groq_unverified_free_tier_blocks_before_dispatch_or_reservation(state):
    from datetime import timedelta
    from src.research_platform.providers import FreeTierUnverifiedError

    now = datetime.now(timezone.utc)
    env = {
        "GROQ_API_KEY": "fake-private",
        "GROQ_FREE_TIER_VERIFIED_AT": now.isoformat(),
        "GROQ_FREE_TIER_KEY_SHA256": hashlib.sha256(b"fake-private").hexdigest(),
    }
    if state == "missing":
        env.pop("GROQ_FREE_TIER_VERIFIED_AT")
    elif state == "expired":
        env["GROQ_FREE_TIER_VERIFIED_AT"] = (now - timedelta(hours=25)).isoformat()
    elif state == "future":
        env["GROQ_FREE_TIER_VERIFIED_AT"] = (now + timedelta(minutes=1)).isoformat()
    elif state == "naive":
        env["GROQ_FREE_TIER_VERIFIED_AT"] = now.replace(tzinfo=None).isoformat()
    elif state == "invalid":
        env["GROQ_FREE_TIER_VERIFIED_AT"] = "invalid"
    else:
        env["GROQ_API_KEY"] = "different-fake-key"
    router = ProviderRouter(
        environ=env,
        client=client(lambda request: pytest.fail("Unverified network dispatch")),
        on_request=lambda *args: pytest.fail("Unverified reservation"),
    )
    with pytest.raises(FreeTierUnverifiedError):
        router.models("groq")
    # A cached discovery result cannot bypass the per-attempt billing check.
    from src.research_platform.providers import ModelInfo
    import time

    router._models["groq"] = (time.monotonic(), [ModelInfo("test", "groq")])
    with pytest.raises(FreeTierUnverifiedError):
        router.complete("groq", "test", "planning", "Test only", 128)
    router.close()
