"""Run-scoped Gemini protocol gateway. No worker, campaign or grant-issuing HTTP API.

Provider credentials belong to this trusted process, never the disposable worker.
HTTP dispatch accounting is enforced here; network bypass prevention requires the
separately deployed VM egress boundary and is deliberately not claimed here.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import secrets
import time
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from typing import Any, TypeGuard

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from .database import Database, GatewayGrant, Job, ModelUsage, Run, WorkflowEvent, new_id
from .ledger import BudgetExceeded, accounting_lock, refresh_usage, reserve_model_call
from .providers import estimate_tokens

PROVIDER_ORIGIN = "https://generativelanguage.googleapis.com"
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}\Z")
PATH = re.compile(
    r"/runs/([a-f0-9]{32})/(v1beta|v1)/models(?:/([A-Za-z0-9._-]+)(?::(generateContent|streamGenerateContent|countTokens))?)?\Z"
)
MAX_BODY = 256 * 1024
MAX_RESPONSE = 2 * 1024 * 1024


@dataclass(frozen=True)
class GatewaySettings:
    enabled: bool = False
    provider_key: str = field(default="", repr=False)
    daily_call_limit: int = 100
    timeout_seconds: float = 45
    metadata_limit: int = 200

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.timeout_seconds)
            or not 0 < self.timeout_seconds <= 60
            or not 1 <= self.daily_call_limit <= 100000
            or not 1 <= self.metadata_limit <= 1000
        ):
            raise ValueError("Invalid bounded gateway settings")


class GatewayDenied(Exception):
    def __init__(self, code: str, status: int = 403):
        self.code, self.status = code, status


def _audit(session: Any, run_id: str, decision: str, request_id: str, **data: Any) -> None:
    count = (
        session.scalar(
            select(func.count())
            .select_from(WorkflowEvent)
            .where(WorkflowEvent.run_id == run_id, WorkflowEvent.kind == "gateway_decision")
        )
        or 0
    )
    # Optional denial/metadata logging is capped. Ledger/grant linkage must
    # survive a flood of denied requests; admitted calls are budget-bounded.
    if count >= 1000 and decision not in {
        "reserved",
        "grant_issued",
        "grant_revoked",
        "completed",
        "failed",
        "uncertain",
    }:
        return
    session.add(
        WorkflowEvent(
            run_id=run_id,
            stage="upstream_gateway",
            kind="gateway_decision",
            message="Gateway " + decision,
            data={"decision": decision, "request_id": request_id, **data},
        )
    )


def _active_run(run: Run | None) -> Run:
    # Gateway grants cannot be used to alter completed/native historical studies.
    if (
        run is None
        or run.profile != "full_research"
        or run.config.get("engine") != "original"
        or run.provider != "gemini"
        or run.status != "running"
        or run.control in {"cancel", "pause"}
        or (run.state.get("original") and run.state["original"].get("deadline", 0) <= time.time())
    ):
        raise GatewayDenied("run_not_authorized")
    return run


def issue_grant(
    database: Database,
    run_id: str,
    *,
    allowed_models: list[str],
    ttl_seconds: int = 300,
    max_output_tokens: int = 1024,
) -> tuple[str, str]:
    """Trusted operator function; returns the scoped secret once, never a provider key.

    No run is created or started. Only an already-authorized original run qualifies.
    Tests create synthetic runs directly; web original launch remains disabled.
    """
    if (
        type(ttl_seconds) is not int
        or not 1 <= ttl_seconds <= 900
        or type(max_output_tokens) is not int
        or not 1 <= max_output_tokens <= 4096
        or not 1 <= len(allowed_models) <= 8
        or any(not MODEL.fullmatch(m) for m in allowed_models)
    ):
        raise ValueError("Invalid bounded gateway grant policy")
    with database.sessions.begin() as session:
        accounting_lock(session)
        return issue_grant_locked(
            session,
            run_id,
            allowed_models=allowed_models,
            ttl_seconds=ttl_seconds,
            max_output_tokens=max_output_tokens,
        )


def issue_grant_locked(
    session: Any,
    run_id: str,
    *,
    allowed_models: list[str],
    ttl_seconds: int,
    max_output_tokens: int,
) -> tuple[str, str]:
    """Caller holds accounting_lock; grant and controller state commit atomically."""
    if (
        type(ttl_seconds) is not int
        or not 1 <= ttl_seconds <= 900
        or type(max_output_tokens) is not int
        or not 1 <= max_output_tokens <= 4096
        or not 1 <= len(allowed_models) <= 8
        or any(not MODEL.fullmatch(m) for m in allowed_models)
    ):
        raise ValueError("Invalid bounded gateway grant policy")
    run = _active_run(session.get(Run, run_id))
    token = "gw_" + secrets.token_urlsafe(32)
    grant = GatewayGrant(
        run_id=run.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        allowed_models=list(dict.fromkeys(allowed_models)),
        max_output_tokens=max_output_tokens,
        expires_at=time.time() + ttl_seconds,
    )
    session.add(grant)
    session.flush()
    _audit(
        session,
        run.id,
        "grant_issued",
        new_id(),
        grant_id=grant.id,
        models=grant.allowed_models,
        expires_at=grant.expires_at,
    )
    return grant.id, token


def revoke_grant(database: Database, grant_id: str) -> None:
    with database.sessions.begin() as session:
        accounting_lock(session)
        grant = session.get(GatewayGrant, grant_id)
        if grant is None:
            raise ValueError("Gateway grant unavailable")
        grant.revoked = True
        _audit(session, grant.run_id, "grant_revoked", new_id(), grant_id=grant.id)


class GeminiGateway:
    def __init__(self, database: Database, settings: GatewaySettings, client: httpx.AsyncClient):
        self.database, self.settings, self.client = database, settings, client

    def authorize(
        self, session: Any, token: str, run_id: str, model: str | None = None
    ) -> tuple[GatewayGrant, Run]:
        if not self.settings.enabled or not self.settings.provider_key:
            raise GatewayDenied("gateway_disabled", 503)
        if not 32 <= len(token) <= 256:
            raise GatewayDenied("invalid_credential", 401)
        digest = hashlib.sha256(token.encode()).hexdigest()
        grant = session.scalar(select(GatewayGrant).where(GatewayGrant.token_hash == digest))
        if (
            grant is None
            or grant.run_id != run_id
            or grant.revoked
            or not math.isfinite(grant.expires_at)
            or grant.expires_at <= time.time()
        ):
            raise GatewayDenied("invalid_credential", 401)
        run = _active_run(session.get(Run, run_id))
        if run.state.get("original"):
            job = session.scalar(select(Job).where(Job.run_id == run.id))
            if (
                job is None
                or not job.owner
                or not job.owner.startswith("original:")
                or job.lease_until <= time.time()
                or run.state["original"].get("operation") not in {"submitting", "running"}
            ):
                raise GatewayDenied("controller_not_authorized")
        if model is not None and (not MODEL.fullmatch(model) or model not in grant.allowed_models):
            raise GatewayDenied("model_not_authorized")
        return grant, run

    def decision(self, run_id: str, token: str, request_id: str, decision: str) -> None:
        # Only a still-authorized original run receives request audit records.
        try:
            with self.database.sessions.begin() as session:
                accounting_lock(session)
                self.authorize(session, token, run_id)
                _audit(session, run_id, decision, request_id)
        except GatewayDenied:
            pass

    def reserve(
        self, token: str, run_id: str, model: str, payload: dict[str, Any], request_id: str
    ) -> tuple[str, dict[str, Any], float]:
        with self.database.sessions.begin() as session:
            accounting_lock(session)
            grant, run = self.authorize(session, token, run_id, model)
            # A supplied request identity is never replayed or refunded. Identical
            # prompts with different identities remain separate, charged attempts.
            reservation_id = hashlib.sha256((run_id + ":" + request_id).encode()).hexdigest()[:32]
            if session.get(ModelUsage, reservation_id) is not None:
                raise GatewayDenied("duplicate_request", 409)
            config = dict(payload.get("generationConfig") or {})
            wanted = config.get("maxOutputTokens", grant.max_output_tokens)
            if (
                type(wanted) is not int
                or not 1 <= wanted <= 65536
                or type(config.get("candidateCount", 1)) is not int
                or config.get("candidateCount", 1) != 1
            ):
                raise GatewayDenied("invalid_output_limit", 400)
            if config.get("responseModalities", ["TEXT"]) != ["TEXT"]:
                raise GatewayDenied("unsupported_modality", 400)
            maximum = min(wanted, grant.max_output_tokens)
            config["maxOutputTokens"] = maximum
            payload = {**payload, "generationConfig": config}
            serialized = json.dumps(
                payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            )
            row = reserve_model_call(
                session,
                run,
                daily_limit=self.settings.daily_call_limit,
                provider="gemini",
                model=model,
                stage="upstream_gateway",
                predicted=estimate_tokens(serialized),
                maximum=maximum,
                reservation_id=reservation_id,
            )
            _audit(
                session,
                run_id,
                "reserved",
                request_id,
                usage_id=row.id,
                grant_id=grant.id,
                model=model,
                payload_sha256=hashlib.sha256(serialized.encode()).hexdigest(),
                max_output_tokens=maximum,
            )
            timeout = min(self.settings.timeout_seconds, grant.expires_at - time.time())
            if timeout <= 0:
                raise GatewayDenied("invalid_credential", 401)
            return row.id, payload, timeout

    def finish(
        self,
        usage_id: str,
        request_id: str,
        *,
        usage: dict[str, Any] | None,
        outcome: str,
        provider_status: int | None = None,
    ) -> None:
        with self.database.sessions.begin() as session:
            accounting_lock(session)
            row = session.get(ModelUsage, usage_id)
            assert row is not None
            if row.status != "reserved":
                return
            counts = measured_usage(usage) if outcome == "completed" else None
            if counts is not None:
                row.input_tokens, row.output_tokens = counts
                row.reported, row.status, row.reserved_output_tokens = True, "completed", 0
            else:
                row.status = "failed" if outcome == "failed" else "uncertain"
            # No remote price is invented, including when usage is reported.
            row.estimated_cost = None
            run = session.get(Run, row.run_id)
            assert run is not None
            refresh_usage(session, run)
            _audit(
                session,
                run.id,
                row.status,
                request_id,
                usage_id=row.id,
                provider_status=provider_status,
            )

    def sanitize(self, value: Any, token: str) -> Any:
        if isinstance(value, str):
            return value.replace(self.settings.provider_key, "[redacted]").replace(
                token, "[redacted]"
            )
        if isinstance(value, list):
            return [self.sanitize(item, token) for item in value]
        if isinstance(value, dict):
            return {
                self.sanitize(key, token): self.sanitize(item, token) for key, item in value.items()
            }
        return value


def measured_usage(usage: dict[str, Any] | None) -> tuple[int, int] | None:
    if not isinstance(usage, dict):
        return None
    prompt, candidate, thoughts, total = (
        usage.get(key)
        for key in (
            "promptTokenCount",
            "candidatesTokenCount",
            "thoughtsTokenCount",
            "totalTokenCount",
        )
    )

    def valid(value: Any) -> TypeGuard[int]:
        return type(value) is int and 0 <= value <= 10**9

    if not valid(prompt):
        return None
    outputs = []
    thoughts = 0 if thoughts is None else thoughts
    if valid(candidate) and valid(thoughts):
        outputs.append(candidate + thoughts)
    if valid(total) and total >= prompt:
        outputs.append(total - prompt)
    return (prompt, max(outputs)) if outputs else None


def _error(code: str, status: int, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "code": status,
                "status": {
                    400: "INVALID_ARGUMENT",
                    401: "UNAUTHENTICATED",
                    403: "PERMISSION_DENIED",
                    404: "NOT_FOUND",
                    429: "RESOURCE_EXHAUSTED",
                }.get(status, "UNAVAILABLE"),
                "message": "Gateway " + code,
                "requestId": request_id,
            }
        },
        status_code=status,
        headers={"X-Gateway-Request-ID": request_id, "Cache-Control": "no-store"},
    )


def validate_payload(payload: Any, model: str) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("model", model) not in (
        model,
        "models/" + model,
    ):
        raise GatewayDenied("invalid_payload", 400)
    allowed = {
        "model",
        "contents",
        "systemInstruction",
        "tools",
        "toolConfig",
        "generationConfig",
        "safetySettings",
        "labels",
    }
    if (
        set(payload) - allowed
        or not isinstance(payload.get("contents"), list)
        or not payload["contents"]
    ):
        raise GatewayDenied("unsupported_payload", 400)
    if not isinstance(payload.get("generationConfig", {}), dict):
        raise GatewayDenied("invalid_generation_config", 400)

    def inspect(value: Any) -> None:
        if isinstance(value, dict):
            if {"fileData", "inlineData", "cachedContent"} & set(value):
                raise GatewayDenied("unsupported_external_or_binary_input", 400)
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    inspect(payload)
    if not isinstance(payload.get("tools", []), list):
        raise GatewayDenied("invalid_tools", 400)
    for tool in payload.get("tools", []):
        if not isinstance(tool, dict) or set(tool) - {"functionDeclarations"}:
            raise GatewayDenied("unsupported_server_side_tool", 400)
    return payload


def create_gateway_app(
    database: Database, settings: GatewaySettings, *, client: httpx.AsyncClient | None = None
) -> FastAPI:
    owns_client = client is None
    client = client or httpx.AsyncClient(
        timeout=httpx.Timeout(settings.timeout_seconds, connect=5),
        follow_redirects=False,
        trust_env=False,
    )
    gateway = GeminiGateway(database, settings, client)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if owns_client:
            await client.aclose()

    app = FastAPI(
        title="Run-scoped Gemini budget gateway",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.gateway = gateway

    @app.middleware("http")
    async def authenticate(request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("x-reseon-request-id") or new_id()
        if not re.fullmatch(r"[a-f0-9]{32}", request_id):
            return _error("invalid_request_id", 400, new_id())
        request.state.request_id = request_id
        match = PATH.fullmatch(request.url.path)
        token = request.headers.get("x-goog-api-key", "")
        bearer = request.headers.get("authorization", "")
        if bearer:
            if not bearer.startswith("Bearer ") or token and token != bearer[7:]:
                return _error("invalid_credential", 401, request_id)
            token = bearer[7:]
        if match is None:
            return _error("invalid_route_or_credential", 401, request_id)
        run_id, version, model, operation = match.groups()
        request.state.identity = (run_id, version, model, operation, token)
        try:
            with database.sessions() as session:
                gateway.authorize(session, token, run_id, model)
            if (
                set(request.query_params) - {"alt"}
                or request.query_params.get("alt", "sse") != "sse"
            ):
                raise GatewayDenied("unsupported_query", 400)
            response = await call_next(request)
            response.headers["X-Gateway-Request-ID"] = request_id
            response.headers["Cache-Control"] = "no-store"
            return response
        except GatewayDenied as error:
            return _error(error.code, error.status, request_id)
        except SQLAlchemyError:
            return _error("accounting_unavailable", 503, request_id)

    @app.api_route("/runs/{run_id}/{version}/models", methods=["GET"])
    @app.api_route("/runs/{run_id}/{version}/models/{tail:path}", methods=["GET", "POST"])
    async def protocol(request: Request) -> Any:
        run_id, version, model, operation, token = request.state.identity
        request_id = request.state.request_id
        try:
            if request.method == "GET" or operation == "countTokens":
                return await metadata(request, gateway)
            if (
                request.method != "POST"
                or operation not in {"generateContent", "streamGenerateContent"}
                or model is None
            ):
                raise GatewayDenied("unsupported_operation", 400)
            payload = validate_payload(await read_body(request), model)
            try:
                usage_id, payload, timeout = gateway.reserve(
                    token, run_id, model, payload, request_id
                )
            except BudgetExceeded:
                raise GatewayDenied("budget_exhausted") from None
            url = f"{PROVIDER_ORIGIN}/{version}/models/{model}:{operation}"
            params = {"alt": "sse"} if operation == "streamGenerateContent" else None
            upstream: httpx.Response | None = None
            deadline = time.monotonic() + timeout
            try:
                async with asyncio.timeout(timeout):
                    # Only fixed Gemini origin/path; no caller auth, URL or headers pass upstream.
                    upstream = await client.send(
                        client.build_request(
                            "POST",
                            url,
                            params=params,
                            json=payload,
                            headers={"x-goog-api-key": settings.provider_key},
                            timeout=httpx.Timeout(timeout, connect=min(5, timeout)),
                        ),
                        stream=True,
                        follow_redirects=False,
                    )
                if not 200 <= upstream.status_code < 300:
                    status = (
                        upstream.status_code
                        if upstream.status_code in {400, 401, 403, 404, 429}
                        else 502
                    )
                    gateway.finish(
                        usage_id,
                        request_id,
                        usage=None,
                        outcome="failed",
                        provider_status=upstream.status_code,
                    )
                    await upstream.aclose()
                    classification = {
                        401: "provider_authentication_failed",
                        403: "provider_access_denied",
                        404: "provider_model_unavailable",
                        429: "provider_rate_limited",
                    }.get(status, "provider_rejected")
                    return _error(classification, status, request_id)
                if operation == "streamGenerateContent":
                    return StreamingResponse(
                        stream_response(
                            request,
                            gateway,
                            upstream,
                            usage_id,
                            max(0.001, deadline - time.monotonic()),
                        ),
                        media_type="text/event-stream",
                    )
                async with asyncio.timeout(max(0.001, deadline - time.monotonic())):
                    data = await read_response(upstream)
                body = json.loads(data)
                if not isinstance(body, dict) or "error" in body:
                    raise ValueError("Invalid provider envelope")
                response = JSONResponse(gateway.sanitize(body, token))
                gateway.finish(
                    usage_id,
                    request_id,
                    usage=body.get("usageMetadata"),
                    outcome="completed",
                    provider_status=upstream.status_code,
                )
                return response
            except (httpx.HTTPError, TimeoutError, ValueError, RecursionError):
                gateway.finish(usage_id, request_id, usage=None, outcome="uncertain")
                return _error("upstream_uncertain", 502, request_id)
            except asyncio.CancelledError:
                gateway.finish(usage_id, request_id, usage=None, outcome="uncertain")
                raise
            finally:
                if upstream is not None and operation != "streamGenerateContent":
                    await upstream.aclose()
        except GatewayDenied as error:
            gateway.decision(run_id, token, request_id, error.code)
            return _error(error.code, error.status, request_id)

    return app


async def read_body(request: Request) -> Any:
    data = bytearray()
    try:
        async with asyncio.timeout(15):
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > MAX_BODY:
                    raise GatewayDenied("request_too_large", 413)

        def reject(value: str) -> Any:
            raise ValueError("Nonfinite JSON")

        return json.loads(data, parse_constant=reject)
    except (ValueError, RecursionError, TimeoutError):
        raise GatewayDenied("invalid_json", 400) from None


async def read_response(response: httpx.Response) -> bytes:
    data = bytearray()
    async for chunk in response.aiter_bytes():
        data.extend(chunk)
        if len(data) > MAX_RESPONSE:
            raise ValueError("Response too large")
    return bytes(data)


async def metadata(request: Request, gateway: GeminiGateway) -> Any:
    run_id, _, model, operation, token = request.state.identity
    payload = await read_body(request) if request.method == "POST" else None
    if (
        request.method == "POST"
        and operation != "countTokens"
        or request.method == "GET"
        and operation
    ):
        raise GatewayDenied("unsupported_operation", 400)
    with gateway.database.sessions.begin() as session:
        accounting_lock(session)
        grant, run = gateway.authorize(session, token, run_id, model)
        count = (
            session.scalar(
                select(func.count())
                .select_from(WorkflowEvent)
                .where(WorkflowEvent.run_id == run_id, WorkflowEvent.kind == "gateway_metadata")
            )
            or 0
        )
        if count >= gateway.settings.metadata_limit:
            raise GatewayDenied("metadata_quota_exhausted")
        session.add(
            WorkflowEvent(
                run_id=run_id,
                stage="upstream_gateway",
                kind="gateway_metadata",
                message="Local metadata only; no provider dispatch",
                data={"request_id": request.state.request_id},
            )
        )
        if operation == "countTokens":
            return {
                "totalTokens": estimate_tokens(json.dumps(payload, ensure_ascii=False)),
                "gatewayEstimated": True,
            }
        models = [
            {
                "name": "models/" + name,
                "displayName": name,
                "version": "gateway-policy",
                "description": "Gateway policy metadata, not generation verification",
                "inputTokenLimit": run.config["budgets"]["max_input_tokens"],
                "outputTokenLimit": grant.max_output_tokens,
                "supportedGenerationMethods": [
                    "generateContent",
                    "streamGenerateContent",
                    "countTokens",
                ],
            }
            for name in grant.allowed_models
            if model is None or name == model
        ]
        return {"models": models} if model is None else models[0]


async def stream_response(
    request: Request,
    gateway: GeminiGateway,
    upstream: httpx.Response,
    usage_id: str,
    timeout: float,
):
    run_id, _, model, _, token = request.state.identity
    request_id = request.state.request_id
    usage = None
    last_usage_complete = False
    outcome = "uncertain"
    total = 0
    buffer = ""
    try:
        async with asyncio.timeout(timeout):
            async for text in upstream.aiter_text():
                total += len(text.encode())
                if total > MAX_RESPONSE:
                    raise ValueError("Response too large")
                with gateway.database.sessions() as session:
                    gateway.authorize(session, token, run_id, model)
                if await request.is_disconnected():
                    return
                buffer = (buffer + text).replace("\r\n", "\n")
                while "\n\n" in buffer:
                    frame, buffer = buffer.split("\n\n", 1)
                    content = "\n".join(
                        line[5:].lstrip() for line in frame.splitlines() if line.startswith("data:")
                    )
                    if not content:
                        continue
                    body = json.loads(content)
                    if not isinstance(body, dict) or "error" in body:
                        raise ValueError("Invalid stream envelope")
                    counts = measured_usage(body.get("usageMetadata"))
                    last_usage_complete = counts is not None
                    if counts is not None:
                        previous = measured_usage(usage)
                        prompt = max(counts[0], previous[0] if previous else 0)
                        output = max(counts[1], previous[1] if previous else 0)
                        usage = {"promptTokenCount": prompt, "totalTokenCount": prompt + output}
                    yield (
                        "data: "
                        + json.dumps(
                            gateway.sanitize(body, token), ensure_ascii=False, allow_nan=False
                        )
                        + "\n\n"
                    )
            if buffer.strip():
                raise ValueError("Incomplete stream envelope")
            outcome = "completed" if last_usage_complete else "uncertain"
    except (httpx.HTTPError, TimeoutError, ValueError, GatewayDenied, RecursionError):
        yield 'data: {"error":{"code":502,"status":"UNAVAILABLE","message":"Gateway upstream_uncertain"}}\n\n'
    finally:
        gateway.finish(
            usage_id, request_id, usage=usage, outcome=outcome, provider_status=upstream.status_code
        )
        await upstream.aclose()


def main() -> None:
    """Explicit trusted-Linux-host deployment, never reads the research .env."""
    import argparse
    import os
    import stat
    from pathlib import Path
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8843)
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    args = parser.parse_args()
    if not args.serve or os.environ.get("RESEARCH_GATEWAY_ENABLED") != "1":
        parser.error("Gateway disabled; explicit trusted-host deployment is required")
    if os.environ.get("RESEARCH_GATEWAY_HOST_ACK") != "outside-disposable-worker-v1":
        parser.error("Provider credentials must remain outside the disposable worker")
    if not args.tls_cert or not args.tls_key:
        parser.error("A trusted TLS certificate and private key are required")
    try:
        if os.name != "posix":
            raise ValueError(
                "Use a reviewed POSIX secret-file deployment; Windows ACL deployment is not validated"
            )
        key_file = Path(os.environ["RESEARCH_GATEWAY_PROVIDER_KEY_FILE"])
        if not key_file.is_absolute():
            raise ValueError("Private absolute key file required")
        descriptor = os.open(key_file, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_mode & 0o077
                or info.st_uid not in {0, os.getuid()}
            ):
                raise ValueError("Private owner-only provider file required")
            provider_key = stream.read(4097).strip()
        if not 16 <= len(provider_key) <= 4096 or "\n" in provider_key:
            raise ValueError("Invalid provider key file")
        database = Database(os.environ["RESEARCH_GATEWAY_DATABASE_URL"])
        settings = GatewaySettings(
            enabled=True,
            provider_key=provider_key,
            daily_call_limit=int(os.environ.get("DAILY_API_CALL_BUDGET", "100")),
        )
    except (KeyError, OSError, ValueError):
        parser.error("Trusted gateway configuration is incomplete or private-file checks failed")
    # Migrations/grants are explicit operator operations, not startup side effects.
    uvicorn.run(
        create_gateway_app(database, settings),
        host=args.host,
        port=args.port,
        ssl_certfile=args.tls_cert,
        ssl_keyfile=args.tls_key,
        access_log=False,
        proxy_headers=False,
        limit_concurrency=16,
    )


if __name__ == "__main__":
    main()
