"""Transactional gateway tests: temporary databases, fake keys, no provider network."""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.research_platform.database import (
    Database,
    GatewayGrant,
    ModelUsage,
    Project,
    Run,
    WorkflowEvent,
)
from src.research_platform.ledger import refresh_usage
from src.research_platform.ledger import accounting_lock, reserve_model_call
from src.research_platform.gateway_client import prepare_cli_environment
from src.research_platform.gateway_network import destination_allowed, qemu_network_arguments
from src.research_platform.model_gateway import (
    GatewayDenied,
    GatewaySettings,
    create_gateway_app,
    issue_grant,
    revoke_grant,
)
from src.research_platform.schemas import Budgets

KEY = "provider-secret-fixture-not-a-real-key"
MODEL = "gemini-2.5-flash"
PAYLOAD = {
    "contents": [{"role": "user", "parts": [{"text": "Reply OK"}]}],
    "generationConfig": {"maxOutputTokens": 128},
}
ANSWER = {
    "candidates": [
        {"content": {"role": "model", "parts": [{"text": "OK"}]}, "finishReason": "STOP"}
    ],
    "usageMetadata": {
        "promptTokenCount": 5,
        "candidatesTokenCount": 2,
        "thoughtsTokenCount": 3,
        "totalTokenCount": 10,
    },
}


def seed(database, *, engine="original", status="running", **budgets):
    with database.sessions.begin() as session:
        project = Project(
            title="Offline gateway test",
            question="Does gateway accounting stop excess requests?",
            domain="Offline validation",
        )
        session.add(project)
        session.flush()
        run = Run(
            project_id=project.id,
            status=status,
            profile="full_research" if engine == "original" else "free_research",
            provider="gemini",
            model=MODEL,
            config={"engine": engine, "budgets": Budgets(**budgets).model_dump()},
        )
        session.add(run)
        session.flush()
        refresh_usage(session, run)
        return run.id


@pytest.fixture
def gateway(tmp_path):
    database = Database(f"sqlite:///{(tmp_path / 'gateway.db').as_posix()}")
    database.migrate()
    run_id = seed(database)
    grant_id, token = issue_grant(database, run_id, allowed_models=[MODEL], max_output_tokens=128)
    calls = []
    lock = threading.Lock()

    async def provider(request):
        with lock:
            calls.append(request)
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["x-goog-api-key"] == KEY
        assert token not in str(request.headers)
        await asyncio.sleep(0.005)
        return httpx.Response(200, json=ANSWER)

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    settings = GatewaySettings(enabled=True, provider_key=KEY)
    app = create_gateway_app(database, settings, client=upstream)
    yield database, run_id, grant_id, token, calls, settings, app
    database.engine.dispose()


def url(run_id, operation="generateContent", model=MODEL):
    return f"/runs/{run_id}/v1beta/models/{model}:{operation}"


def headers(token):
    return {"x-goog-api-key": token}


def rows(database, run_id):
    with database.sessions() as session:
        return list(session.scalars(select(ModelUsage).where(ModelUsage.run_id == run_id)))


def test_twenty_call_limit_rejects_twenty_first_before_dispatch(gateway):
    db, run_id, _, token, calls, _, app = gateway
    with TestClient(app) as client:
        for _ in range(20):
            result = client.post(url(run_id), headers=headers(token), json=PAYLOAD)
            assert result.status_code == 200, result.text
        denied = client.post(url(run_id), headers=headers(token), json=PAYLOAD)
    assert denied.status_code == 403 and "budget_exhausted" in denied.text
    assert len(calls) == len(rows(db, run_id)) == 20
    assert len({row.id for row in rows(db, run_id)}) == 20
    with db.sessions() as session:
        run = session.get(Run, run_id)
        assert run.usage["calls"] == 20 and run.usage["remaining_calls"] == 0
        assert run.usage["estimated_cost"] is None
        decisions = list(
            session.scalars(select(WorkflowEvent).where(WorkflowEvent.run_id == run_id))
        )
        assert any(row.data.get("decision") == "budget_exhausted" for row in decisions)


def test_concurrent_clients_and_app_instances_cannot_oversubscribe(gateway):
    db, run_id, _, token, calls, settings, app = gateway

    def attempt(index):
        # Independent gateway instances/connections share only the SQL ledger.
        other = Database(str(db.engine.url))
        application = create_gateway_app(other, settings, client=app.state.gateway.client)
        try:
            with TestClient(application) as client:
                return client.post(url(run_id), headers=headers(token), json=PAYLOAD).status_code
        finally:
            other.engine.dispose()

    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(attempt, range(40)))
    assert statuses.count(200) == 20 and statuses.count(403) == 20
    assert len(calls) == len(rows(db, run_id)) == 20


@pytest.mark.parametrize("status", [401, 403, 404, 429, 503])
def test_failed_attempts_retain_reservations_and_never_leak_provider_errors(gateway, status):
    db, run_id, _, token, _, settings, _ = gateway
    calls = []

    async def fail(request):
        calls.append(request)
        return httpx.Response(
            status, json={"error": {"message": KEY + token}}, headers={"x-secret": KEY}
        )

    app = create_gateway_app(
        db, settings, client=httpx.AsyncClient(transport=httpx.MockTransport(fail))
    )
    with TestClient(app) as client:
        for _ in range(2):
            result = client.post(url(run_id), json=PAYLOAD, headers=headers(token))
            assert result.status_code >= 400
            assert (
                KEY not in result.text
                and token not in result.text
                and "x-secret" not in result.headers
            )
    reserved = rows(db, run_id)
    assert len(calls) == len(reserved) == 2  # explicit retry is a separate charged attempt
    assert all(
        row.status == "failed" and row.reserved_output_tokens == 128 and not row.reported
        for row in reserved
    )


def test_ambiguous_timeout_restart_does_not_refund_or_replay(gateway):
    db, run_id, _, token, _, settings, _ = gateway
    calls = []

    async def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout(KEY, request=request)

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
    for _ in range(2):
        app = create_gateway_app(db, settings, client=upstream)
        with TestClient(app) as client:
            response = client.post(url(run_id), headers=headers(token), json=PAYLOAD)
            assert response.status_code == 502 and KEY not in response.text
        assert len(rows(db, run_id)) == len(calls)
    assert len(calls) == 2  # app construction/restart never dispatched old rows
    assert all(
        row.status == "uncertain" and row.reserved_output_tokens == 128 for row in rows(db, run_id)
    )


@pytest.mark.parametrize("mode", ["expired", "revoked", "wrong_run", "wrong_model", "invalid"])
def test_scoped_credentials_rejected_without_consuming_budget(gateway, mode):
    db, run_id, grant_id, token, calls, _, app = gateway
    target = run_id
    if mode == "expired":
        with db.sessions.begin() as session:
            session.get(GatewayGrant, grant_id).expires_at = time.time() - 1
    elif mode == "revoked":
        revoke_grant(db, grant_id)
    elif mode == "wrong_run":
        target = seed(db)
    elif mode == "invalid":
        token = "invalid" * 8
    with TestClient(app) as client:
        response = client.post(
            url(target, model="unapproved-model" if mode == "wrong_model" else MODEL),
            json=PAYLOAD,
            headers=headers(token),
        )
    assert response.status_code in {401, 403}
    assert not calls and not rows(db, target)


def test_daily_token_and_unknown_monetary_limits_share_native_policy(gateway):
    db, run_id, _, token, calls, settings, app = gateway
    settings = replace(settings, daily_call_limit=1)
    app = create_gateway_app(db, settings, client=app.state.gateway.client)
    with TestClient(app) as client:
        assert client.post(url(run_id), headers=headers(token), json=PAYLOAD).status_code == 200
        assert client.post(url(run_id), headers=headers(token), json=PAYLOAD).status_code == 403
    assert len(calls) == 1
    with db.sessions.begin() as session:
        run = session.get(Run, run_id)
        run.config = {**run.config, "budgets": {**run.config["budgets"], "monetary_cap_usd": 1}}
    app = create_gateway_app(
        db, replace(settings, daily_call_limit=100), client=app.state.gateway.client
    )
    with TestClient(app) as client:
        assert client.post(url(run_id), headers=headers(token), json=PAYLOAD).status_code == 403
    assert len(calls) == 1


def test_reported_usage_includes_reasoning_cost_stays_null(gateway):
    db, run_id, _, token, _, _, app = gateway
    with TestClient(app) as client:
        response = client.post(url(run_id), json=PAYLOAD, headers=headers(token))
        assert len(response.headers["X-Gateway-Request-ID"]) == 32
    row = rows(db, run_id)[0]
    assert row.reported and row.input_tokens == 5 and row.output_tokens == 5
    assert row.estimated_cost is None and row.reserved_output_tokens == 0


def test_local_metadata_and_estimated_count_tokens_do_not_dispatch(gateway):
    db, run_id, _, token, calls, _, app = gateway
    with TestClient(app) as client:
        info = client.get(f"/runs/{run_id}/v1beta/models/{MODEL}", headers=headers(token))
        assert info.status_code == 200 and "not generation verification" in info.text
        result = client.post(url(run_id, "countTokens"), json=PAYLOAD, headers=headers(token))
        assert result.json()["gatewayEstimated"]
    assert not calls and not rows(db, run_id)


@pytest.mark.parametrize(
    "extra",
    [
        {"cachedContent": "private-cache"},
        {"contents": [{"parts": [{"fileData": {"fileUri": "https://external.invalid"}}]}]},
        {"tools": [{"googleSearch": {}}]},
        {"generationConfig": {"candidateCount": 2}},
    ],
)
def test_unaccountable_inputs_and_extra_candidates_are_rejected(gateway, extra):
    db, run_id, _, token, calls, _, app = gateway
    with TestClient(app) as client:
        response = client.post(url(run_id), json={**PAYLOAD, **extra}, headers=headers(token))
    assert response.status_code == 400 and not calls and not rows(db, run_id)


def test_completed_native_history_cannot_receive_grants_or_requests(gateway):
    db, _, _, token, calls, _, app = gateway
    native = seed(db, engine="native", status="completed")
    with db.sessions() as session:
        run = session.get(Run, native)
        before = (run.state, run.config, run.usage, run.status)
    with pytest.raises(GatewayDenied):
        issue_grant(db, native, allowed_models=[MODEL])
    with TestClient(app) as client:
        assert client.post(url(native), json=PAYLOAD, headers=headers(token)).status_code == 401
    db.migrate()
    with db.sessions() as session:
        run = session.get(Run, native)
        assert (run.state, run.config, run.usage, run.status) == before
    assert not calls and not rows(db, native)


class SSE(httpx.AsyncByteStream):
    async def __aiter__(self):
        data = ("data: " + json.dumps(ANSWER) + "\r\n\r\n").encode()
        for byte in data:  # exercises fragmented frames/UTF-8 decoder boundaries
            yield bytes([byte])


def test_gemini_sse_usage_and_content_are_preserved(gateway):
    db, run_id, _, token, _, settings, _ = gateway

    async def provider(request):
        assert request.url.params["alt"] == "sse"
        return httpx.Response(200, stream=SSE())

    app = create_gateway_app(
        db, settings, client=httpx.AsyncClient(transport=httpx.MockTransport(provider))
    )
    with TestClient(app) as client:
        result = client.post(
            url(run_id, "streamGenerateContent") + "?alt=sse", json=PAYLOAD, headers=headers(token)
        )
    assert result.status_code == 200 and "text/event-stream" in result.headers["content-type"]
    assert json.loads(result.text.removeprefix("data: "))["candidates"] == ANSWER["candidates"]
    assert rows(db, run_id)[0].reported


def test_interrupted_stream_is_charged_and_closed(gateway):
    db, run_id, _, token, _, settings, _ = gateway
    closed = threading.Event()

    class Slow(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"candidates":[{"content":{"parts":[{"text":"partial"}]}}]}\n\n'
            await asyncio.sleep(10)
            yield ("data: " + json.dumps(ANSWER) + "\n\n").encode()

        async def aclose(self):
            closed.set()

    async def provider(request):
        return httpx.Response(200, stream=Slow())

    app = create_gateway_app(
        db, settings, client=httpx.AsyncClient(transport=httpx.MockTransport(provider))
    )
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False, ws="none"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    try:
        with httpx.Client(trust_env=False) as client:
            with client.stream(
                "POST",
                f"http://127.0.0.1:{port}" + url(run_id, "streamGenerateContent"),
                headers=headers(token),
                json=PAYLOAD,
            ) as response:
                assert response.status_code == 200
                assert "partial" in next(response.iter_lines())
        assert closed.wait(5), "Disconnected stream did not close its upstream"
        row = rows(db, run_id)[0]
        assert row.status == "uncertain" and not row.reported and row.reserved_output_tokens == 128
        assert len(rows(db, run_id)) == 1
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def test_reserved_dispatch_survives_database_reopen_without_replay(gateway):
    db, run_id, _, token, calls, settings, app = gateway
    with db.sessions.begin() as session:
        run = session.get(Run, run_id)
        run.config = {**run.config, "budgets": {**run.config["budgets"], "max_llm_calls": 1}}
    app.state.gateway.reserve(token, run_id, MODEL, PAYLOAD, "fixture-before-dispatch-crash")
    reopened = Database(str(db.engine.url))
    try:
        restarted = create_gateway_app(reopened, settings, client=app.state.gateway.client)
        with TestClient(restarted) as client:
            assert client.post(url(run_id), json=PAYLOAD, headers=headers(token)).status_code == 403
        assert not calls and rows(reopened, run_id)[0].status == "reserved"
    finally:
        reopened.engine.dispose()


def test_preexisting_native_style_reservations_share_same_run_cap(gateway):
    db, run_id, _, token, calls, _, app = gateway
    for _ in range(19):
        with db.sessions.begin() as session:
            accounting_lock(session)
            reserve_model_call(
                session,
                session.get(Run, run_id),
                daily_limit=100,
                provider="gemini",
                model=MODEL,
                stage="planning",
                predicted=10,
                maximum=5,
            )
    with TestClient(app) as client:
        assert client.post(url(run_id), json=PAYLOAD, headers=headers(token)).status_code == 200
        assert client.post(url(run_id), json=PAYLOAD, headers=headers(token)).status_code == 403
    assert len(calls) == 1 and len(rows(db, run_id)) == 20


def test_authorization_rechecked_inside_reservation_transaction(gateway, monkeypatch):
    db, run_id, grant_id, token, calls, _, app = gateway
    original = app.state.gateway.reserve

    def revoked_before_reservation(*args, **kwargs):
        revoke_grant(db, grant_id)
        return original(*args, **kwargs)

    monkeypatch.setattr(app.state.gateway, "reserve", revoked_before_reservation)
    with TestClient(app) as client:
        assert client.post(url(run_id), json=PAYLOAD, headers=headers(token)).status_code == 401
    assert not calls and not rows(db, run_id)


@pytest.mark.parametrize("kind", ["missing_usage", "redirect", "secret"])
def test_missing_usage_redirect_and_success_response_redaction(gateway, kind):
    db, run_id, _, token, _, settings, _ = gateway
    dispatches = []

    async def provider(request):
        dispatches.append(request)
        if kind == "redirect":
            return httpx.Response(307, headers={"Location": "https://external.invalid"})
        body = {**ANSWER}
        if kind == "missing_usage":
            body.pop("usageMetadata")
        if kind == "secret":
            body["candidates"] = [{"content": {"parts": [{"text": KEY + token}]}}]
        return httpx.Response(200, json=body)

    app = create_gateway_app(
        db, settings, client=httpx.AsyncClient(transport=httpx.MockTransport(provider))
    )
    with TestClient(app) as client:
        response = client.post(url(run_id), json=PAYLOAD, headers=headers(token))
    assert KEY not in response.text and token not in response.text and len(dispatches) == 1
    row = rows(db, run_id)[0]
    assert row.estimated_cost is None
    if kind != "secret":
        assert row.status != "completed" and row.reserved_output_tokens == 128
    with db.sessions() as session:
        events = str(
            [
                row.data
                for row in session.scalars(
                    select(WorkflowEvent).where(WorkflowEvent.run_id == run_id)
                )
            ]
        )
        assert KEY not in events and token not in events


def test_input_output_and_metadata_bounds(gateway):
    db, run_id, _, token, calls, settings, app = gateway
    with db.sessions.begin() as session:
        run = session.get(Run, run_id)
        run.config = {**run.config, "budgets": {**run.config["budgets"], "max_input_tokens": 128}}
    with TestClient(app) as client:
        assert client.post(url(run_id), json=PAYLOAD, headers=headers(token)).status_code == 403
    assert not calls
    with db.sessions.begin() as session:
        run = session.get(Run, run_id)
        run.config = {
            **run.config,
            "budgets": {
                **run.config["budgets"],
                "max_input_tokens": 32000,
                "max_output_tokens": 128,
            },
        }
    with TestClient(app) as client:
        assert client.post(url(run_id), json=PAYLOAD, headers=headers(token)).status_code == 200
        assert client.post(url(run_id), json=PAYLOAD, headers=headers(token)).status_code == 403
    assert len(calls) == 1
    limited = create_gateway_app(
        db, replace(settings, metadata_limit=1), client=app.state.gateway.client
    )
    with TestClient(limited) as client:
        path = f"/runs/{run_id}/v1beta/models/{MODEL}"
        assert client.get(path, headers=headers(token)).status_code == 200
        assert client.get(path, headers=headers(token)).status_code == 403


def test_cli_profile_configuration_is_private_scoped_and_does_not_overwrite(tmp_path):
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    token = "gw_" + "x" * 43
    base = "https://10.0.2.100:8843/runs/" + "a" * 32
    env = prepare_cli_environment(home, base, token)
    assert env["GEMINI_API_KEY"] == token and "GOOGLE_API_KEY" not in env
    settings = json.loads((home / ".gemini/settings.json").read_text())
    assert settings["security"]["auth"]["selectedType"] == "gemini-api-key"
    assert settings["privacy"]["usageStatisticsEnabled"] is False
    with pytest.raises(FileExistsError):
        prepare_cli_environment(home, base, token)
    with pytest.raises(ValueError):
        prepare_cli_environment(home, "http://external.invalid/runs/" + "a" * 32, token)


def test_prepared_host_side_network_policy_has_one_fixed_guest_egress():
    assert destination_allowed("10.0.2.100", 8843)
    for address in ("8.8.8.8", "142.250.0.1", "169.254.169.254", "10.0.2.2", "::1", "2607:f8b0::1"):
        assert not destination_allowed(address, 443)
    assert not destination_allowed("10.0.2.100", 53)
    args = qemu_network_arguments()
    assert args[0] == "-nic" and "restrict=on" in args[1]
    assert "TCP4:127.0.0.1:8843" in args[1]
    assert "hostfwd=tcp:127.0.0.1:2222-:22" in args[1]
    assert "restrict=off" not in args[1] and "host.docker.internal" not in args[1]
