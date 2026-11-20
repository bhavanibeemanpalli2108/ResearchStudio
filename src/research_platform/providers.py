"""Small, explicit provider boundary. Secrets never enter returned diagnostics."""

from __future__ import annotations

import email.utils
import hashlib
import ipaddress
import json
import os
import random
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, TypeGuard
from urllib.parse import quote, urlparse

import httpx


class ProviderError(RuntimeError):
    code = "provider_error"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        status_code: int | None = None,
        details: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.details = details or {}


def _error_identifier(value: Any) -> str:
    return (
        value
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\[\]-]{0,99}", value)
        else ""
    )


class AuthenticationError(ProviderError):
    code = "authentication_error"


class FreeTierUnverifiedError(ProviderError):
    code = "free_tier_unverified"


def groq_free_tier_verified(environ: Mapping[str, str]) -> bool:
    """Fresh operator attestation bound to this key; never infer a plan from quota.

    Groq does not expose account billing eligibility in model discovery. This is
    an explicit local prerequisite, not independent proof of the remote plan.
    """
    try:
        key = environ.get("GROQ_API_KEY", "").strip()
        verified = datetime.fromisoformat(environ.get("GROQ_FREE_TIER_VERIFIED_AT", ""))
        age = (datetime.now(timezone.utc) - verified).total_seconds()
        return (
            bool(key)
            and 0 <= age <= 86400
            and hashlib.sha256(key.encode()).hexdigest()
            == environ.get("GROQ_FREE_TIER_KEY_SHA256", "")
        )
    except (ValueError, TypeError):
        return False


class RateLimitError(ProviderError):
    code = "rate_limit"
    retryable = True


class ProviderUnavailableError(ProviderError):
    code = "provider_unavailable"
    retryable = True


class ContextBudgetError(ProviderError):
    code = "context_budget_exceeded"


class ModelUnavailableError(ProviderError):
    code = "model_unavailable"


class StructuredOutputUnsupportedError(ProviderError):
    code = "structured_output_unsupported"


class StructuredOutputError(ProviderError):
    code = "malformed_structured_output"


class TruncatedOutputError(StructuredOutputError):
    code = "truncated_output"


@dataclass(frozen=True)
class ModelInfo:
    id: str
    provider: str
    context_tokens: int = 4096
    max_output_tokens: int = 2048
    context_is_estimated: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    provider: str
    model: str
    estimated_cost: float | None = None
    usage_is_estimated: bool = False


def estimate_tokens(text: str) -> int:
    """Reserve one token per UTF-8 byte plus chat-message overhead.

    This deliberately over-reserves high-entropy and multilingual prompts;
    provider-reported usage remains the only measured token count. It avoids
    the common characters/4 estimate under-reserving unfamiliar tokenization.
    """
    return len(text.encode("utf-8")) + 64


def _positive(value: Any, default: int) -> int:
    return (
        value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else default
    )


def _records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _is_token_count(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _usage_count(value: Any, fallback: int) -> tuple[int, bool]:
    if _is_token_count(value):
        return value, False
    return fallback, True


class ProviderRouter:
    PROVIDERS = ("mock", "gemini", "groq", "ollama")
    FALLBACK_PROVIDERS = frozenset({"gemini", "groq", "ollama"})

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        environ: Mapping[str, str] | None = None,
        on_request: Callable[[str, str, str, str, int], Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
        max_attempts: int = 3,
    ):
        self.environ = environ if environ is not None else os.environ
        self.client = client or httpx.Client(timeout=httpx.Timeout(45, connect=5), trust_env=False)
        self.on_request = on_request
        self.sleep, self.jitter = sleep, jitter
        self.max_attempts = max(1, min(max_attempts, 5))
        self._models: dict[str, tuple[float, list[ModelInfo]]] = {}

    def close(self) -> None:
        self.client.close()

    def _error_details(self, response: httpx.Response) -> tuple[dict[str, str], str]:
        try:
            envelope = response.json()
        except ValueError:
            return {}, ""
        error = envelope.get("error") if isinstance(envelope, dict) else None
        if not isinstance(error, dict):
            return {}, ""
        details = {
            key: identifier
            for key in ("code", "type", "param")
            if (identifier := _error_identifier(error.get(key)))
        }
        for key in list(details):
            value = details[key]
            if re.search(r"(?i)^(gsk_|sk[-_]|AIza|secret|bearer)", value) or any(
                value == secret
                for name, secret in self.environ.items()
                if any(marker in name.upper() for marker in ("KEY", "TOKEN", "PASSWORD", "SECRET"))
                and secret
            ):
                details.pop(key)
        message = error.get("message")
        failed_generation = error.get("failed_generation")
        if isinstance(failed_generation, str):
            details["failed_generation_bytes"] = str(len(failed_generation.encode("utf-8")))
            try:
                json.loads(failed_generation)
                details["failed_generation_json_valid"] = "true"
            except (ValueError, TypeError, RecursionError):
                details["failed_generation_json_valid"] = "false"
        if not isinstance(message, str):
            return details, ""
        # Inspect the server explanation only in memory. Never retain failed
        # generation, prompt echoes, raw bodies, credentials, URLs or paths.
        rejection = message.lower()
        if any(
            word in rejection
            for word in ("schema", "response_format", "responsejsonschema", "response_json_schema")
        ):
            safe_message = "Provider rejected the structured-output schema or response format."
        elif "temperature" in rejection:
            safe_message = "Provider rejected the temperature parameter."
        elif (
            "max_tokens" in rejection
            or "max_completion_tokens" in rejection
            or "maxoutputtokens" in rejection
        ):
            safe_message = "Provider rejected the output-token limit parameter."
        elif "model" in rejection and any(
            word in rejection
            for word in (
                "not found",
                "does not exist",
                "decommission",
                "not available",
                "not supported",
            )
        ):
            safe_message = "The model is unavailable for generation with this account or endpoint."
        elif "json" in rejection and any(
            word in rejection for word in ("failed", "invalid", "validation")
        ):
            safe_message = "Provider could not produce valid structured JSON."
        elif "billing" in rejection or "quota" in rejection:
            safe_message = "Provider rejected the account quota or billing state."
        else:
            safe_message = (
                "Provider rejected the request; inspect the nonsecret error code and parameter."
            )
        details["message"] = safe_message
        return details, rejection

    def _check_provider(self, provider: str) -> None:
        if provider not in self.PROVIDERS:
            raise ProviderError("Unsupported provider.", provider=provider)

    def _credentials(self, provider: str) -> str:
        names = {"gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "groq": ("GROQ_API_KEY",)}
        for name in names.get(provider, ()):
            if self.environ.get(name, "").strip():
                return self.environ[name].strip()
        if provider in names:
            raise AuthenticationError(
                f"Configure {names[provider][0]} to use {provider}.", provider=provider
            )
        return ""

    def _ollama_url(self) -> str:
        value = self.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        parsed = urlparse(value)
        host = parsed.hostname or ""
        try:
            local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host == "localhost"
        if (
            parsed.scheme not in {"http", "https"}
            or not local
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ProviderError(
                "OLLAMA_BASE_URL must be a loopback HTTP(S) origin.", provider="ollama"
            )
        return value

    @staticmethod
    def _retry_after(value: str | None) -> float:
        if not value:
            return 0.0
        try:
            return max(0.0, min(float(value), 60.0))
        except ValueError:
            try:
                date = email.utils.parsedate_to_datetime(value)
                return max(0.0, min((date - datetime.now(timezone.utc)).total_seconds(), 60.0))
            except (TypeError, ValueError, OverflowError):
                return 0.0

    def _request(
        self,
        provider: str,
        method: str,
        url: str,
        *,
        request_context: tuple[str, str, str, int] | None = None,
        structured_output: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        for attempt in range(self.max_attempts):
            if provider == "groq" and not groq_free_tier_verified(self.environ):
                raise FreeTierUnverifiedError(
                    "Groq requests are blocked. Verify this key's organization is on the Free plan "
                    "with no paid usage, then record a fresh local attestation (valid 24 hours).",
                    provider=provider,
                )
            if request_context and self.on_request:
                model, stage, prompt, maximum = request_context
                self.on_request(provider, model, stage, prompt, maximum)
            try:
                response = self.client.request(method, url, **kwargs)
            except httpx.TransportError:
                error = ProviderUnavailableError(
                    f"{provider} could not be reached.", provider=provider
                )
                if attempt + 1 == self.max_attempts:
                    raise error from None
                self.sleep(min(2**attempt + self.jitter(), 60))
                continue
            if response.status_code in {401, 403}:
                raise AuthenticationError(
                    f"{provider} rejected the configured credential.",
                    provider=provider,
                    status_code=response.status_code,
                )
            if response.status_code == 404:
                details, _ = self._error_details(response)
                raise ModelUnavailableError(
                    f"{provider} endpoint or model is unavailable."
                    + (" " + details["message"] if details.get("message") else ""),
                    provider=provider,
                    status_code=404,
                    details=details,
                )
            if response.status_code == 429 or response.status_code >= 500:
                cls = RateLimitError if response.status_code == 429 else ProviderUnavailableError
                retry_error = cls(
                    f"{provider} temporarily rejected the request (HTTP {response.status_code}).",
                    provider=provider,
                    status_code=response.status_code,
                )
                if attempt + 1 == self.max_attempts:
                    raise retry_error
                self.sleep(
                    max(
                        self._retry_after(response.headers.get("Retry-After")),
                        min(2**attempt + self.jitter(), 60),
                    )
                )
                continue
            if response.is_error:
                details, rejection = self._error_details(response)
                if details.get("code") == "json_validate_failed":
                    raise StructuredOutputError(
                        "The provider failed to generate JSON matching the requested component schema. Retry only this component within its repair budget.",
                        provider=provider,
                        status_code=response.status_code,
                        details=details,
                    )
                if structured_output and response.status_code in {400, 422}:
                    format_named = any(
                        word in rejection
                        for word in (
                            "schema",
                            "response_format",
                            "responsemimetype",
                            "response_json_schema",
                            "responsejsonschema",
                        )
                    )
                    unsupported = any(
                        word in rejection
                        for word in (
                            "unsupported",
                            "not supported",
                            "unknown name",
                            "unrecognized",
                            "not available",
                            "invalid schema",
                            "not permitted",
                            "not allowed",
                            "unknown parameter",
                            "must be one of",
                        )
                    )
                    if format_named and unsupported:
                        raise StructuredOutputUnsupportedError(
                            "The selected model does not support this structured response schema.",
                            provider=provider,
                            status_code=response.status_code,
                            details=details,
                        )
                raise ProviderError(
                    f"{provider} request failed (HTTP {response.status_code})."
                    + (" " + details["message"] if details.get("message") else "")
                    + (" Provider code: " + details["code"] + "." if details.get("code") else "")
                    + (" Parameter: " + details["param"] + "." if details.get("param") else ""),
                    provider=provider,
                    status_code=response.status_code,
                    details=details,
                )
            try:
                data = response.json()
            except ValueError:
                raise ProviderError(
                    f"{provider} returned invalid JSON.", provider=provider
                ) from None
            if not isinstance(data, dict):
                raise ProviderError(
                    f"{provider} returned an unexpected response.", provider=provider
                )
            return data
        raise ProviderUnavailableError("Provider retry limit reached.", provider=provider)

    def models(self, provider: str, *, refresh: bool = False) -> list[ModelInfo]:
        self._check_provider(provider)
        cached = self._models.get(provider)
        if cached and not refresh and time.monotonic() - cached[0] < 300:
            return list(cached[1])
        key = self._credentials(provider)
        if provider == "mock":
            result = [ModelInfo("mock-researcher", "mock", 32768, 4096, False)]
        elif provider == "gemini":
            data = self._request(
                provider,
                "GET",
                "https://generativelanguage.googleapis.com/v1beta/models",
                headers={"x-goog-api-key": key},
            )
            result = [
                ModelInfo(
                    str(item["name"]).removeprefix("models/"),
                    provider,
                    _positive(item.get("inputTokenLimit"), 4096),
                    _positive(item.get("outputTokenLimit"), 2048),
                    "inputTokenLimit" not in item,
                )
                for item in _records(data.get("models"))
                if item.get("name")
                and "generateContent" in (item.get("supportedGenerationMethods") or [])
            ]
        elif provider == "groq":
            data = self._request(
                provider,
                "GET",
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            result = [
                ModelInfo(
                    str(item["id"]),
                    provider,
                    _positive(item.get("context_window"), 4096),
                    _positive(item.get("max_completion_tokens"), 2048),
                    "context_window" not in item,
                )
                for item in _records(data.get("data"))
                if item.get("id") and item.get("active", True)
            ]
        else:
            data = self._request(provider, "GET", self._ollama_url() + "/api/tags")
            result = [
                ModelInfo(str(item["name"]), provider)
                for item in _records(data.get("models"))
                if item.get("name")
            ]
        self._models[provider] = (time.monotonic(), result)
        return result

    def health(self, provider: str) -> dict[str, Any]:
        try:
            models = self.models(provider, refresh=True)
            return {
                "provider": provider,
                "status": "discovered" if models else "no_models",
                "generation_verified": False,
                "models": [m.as_dict() for m in models],
                "detail": "Local installed models only."
                if provider == "ollama"
                else "Model discovery succeeded; generation has not been verified.",
            }
        except ProviderError as exc:
            return {
                "provider": provider,
                "status": "unavailable",
                "models": [],
                "error": exc.code,
                "detail": str(exc),
            }

    def preflight(self, provider: str, model: str) -> Completion:
        """One bounded generation attempt; callers must attach durable accounting.

        Discovery is not proof of generation. No fallback or automatic retry is
        allowed here, and this result only verifies the current account/endpoint.
        """
        if provider == "mock" or self.on_request is None:
            raise ProviderError("Generation preflight requires a real provider and run accounting.")
        attempts = self.max_attempts
        self.max_attempts = 1
        try:
            return self.complete(provider, model, "provider_preflight", "Reply with OK.", 128)
        finally:
            self.max_attempts = attempts

    def complete(
        self,
        provider: str,
        model: str,
        stage: str,
        prompt: str,
        max_output_tokens: int = 1024,
        *,
        allow_fallback: bool = False,
        fallback_providers: Sequence[str] = (),
        json_schema: dict[str, Any] | None = None,
    ) -> Completion:
        try:
            return self._complete(
                provider, model, stage, prompt, max_output_tokens, json_schema=json_schema
            )
        except (ProviderUnavailableError, RateLimitError) as original:
            if not allow_fallback:
                raise
            for alternative in fallback_providers:
                if alternative not in self.FALLBACK_PROVIDERS or alternative == provider:
                    continue
                try:
                    candidates = self.models(alternative)
                    if candidates:
                        return self._complete(
                            alternative,
                            candidates[0].id,
                            stage,
                            prompt,
                            max_output_tokens,
                            json_schema=json_schema,
                        )
                except ProviderError:
                    continue
            raise original

    def _complete(
        self,
        provider: str,
        model: str,
        stage: str,
        prompt: str,
        max_output_tokens: int,
        *,
        json_schema: dict[str, Any] | None = None,
    ) -> Completion:
        self._check_provider(provider)
        answer: object
        if (
            not isinstance(max_output_tokens, int)
            or isinstance(max_output_tokens, bool)
            or not 1 <= max_output_tokens <= 65536
        ):
            raise ContextBudgetError(
                "Output token limit must be between 1 and 65536.", provider=provider
            )
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model):
            raise ModelUnavailableError("Invalid model identifier.", provider=provider)
        models = self.models(provider)
        info = next((item for item in models if item.id == model), None)
        if info is None:
            raise ModelUnavailableError(
                "Selected model was not returned by current provider discovery.", provider=provider
            )
        schema_text = ""
        if json_schema is not None:
            try:
                schema_text = json.dumps(
                    json_schema, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                )
            except (TypeError, ValueError, RecursionError):
                raise ProviderError(
                    "Response schema must be finite JSON.", provider=provider
                ) from None
            if not isinstance(json_schema, dict) or len(schema_text.encode("utf-8")) > 24000:
                raise ProviderError(
                    "Response schema must be an object smaller than 24KB.", provider=provider
                )
        budget_prompt = prompt + ("\nRequired JSON schema:\n" + schema_text if schema_text else "")
        estimated_input = estimate_tokens(budget_prompt)
        if (
            max_output_tokens > info.max_output_tokens
            or estimated_input + max_output_tokens > info.context_tokens
        ):
            raise ContextBudgetError(
                f"Prompt and output exceed the selected model budget ({info.context_tokens} tokens).",
                provider=provider,
            )
        if provider == "mock":
            payloads = {
                "planning": {
                    "summary": "Deterministic demonstration of a reproducible circle-packing study.",
                    "steps": [
                        "Measure a baseline",
                        "Compare a curated configuration",
                        "Report limitations",
                    ],
                    "hypotheses": [
                        {
                            "id": "H1",
                            "statement": "A more balanced grid may increase the sum of circle radii for 26 circles.",
                            "test": "Compare two deterministic valid grid packings of 26 circles.",
                        }
                    ],
                },
                "ideas": {
                    "ideas": [
                        {
                            "id": "grid-comparison",
                            "title": "Compare valid square grid packings",
                            "hypothesis": "Increasing grid density increases total packed radii.",
                            "method": "Compare curated CPU configurations with feasibility checks.",
                            "expected_outcome": "Measured configuration-dependent radius sum.",
                            "risks": ["Small curated problem; no general scientific conclusion."],
                            "score": 0.75,
                        }
                    ]
                },
                "selection": {
                    "idea_id": "grid-comparison",
                    "rationale": "A bounded reproducible comparison suitable for a demonstration.",
                },
                "experiment_plan": {
                    "objective": "Compare curated circle-packing configurations for 26 circles.",
                    "baseline": "26 circles on a 7-column, 4-row grid",
                    "intervention": "26 circles on a 6-column, 5-row grid",
                    "metrics": ["sum_radii", "valid"],
                    "success_criteria": "Both packings pass geometry checks; compare radius sums.",
                    "reproducibility": "Deterministic curated code and configuration.",
                },
                "evaluation": {
                    "interpretation": "The deterministic demo values illustrate workflow behavior only.",
                    "limitations": ["Fixture values are not measured experimental evidence."],
                    "decision": "synthesize",
                    "rationale": "Complete the demonstration with an explicit evidence limitation.",
                },
            }
            payload = payloads.get(
                stage,
                {
                    "kind": "deterministic_demo",
                    "stage": stage,
                    "summary": f"Demonstration {stage} output. This fixture is not scientific evidence.",
                },
            )
            answer = (
                "# Demonstration interpretation\n\nThis deterministic fixture illustrates the research workflow. Demo values are not measured scientific evidence. No external literature was verified.\n"
                if stage in {"synthesis", "report"}
                else json.dumps(payload, sort_keys=True)
            )
            estimated_output = estimate_tokens(answer)
            if estimated_output > max_output_tokens:
                raise ContextBudgetError(
                    "The output budget is too small for the deterministic stage fixture.",
                    provider=provider,
                )
            if self.on_request:
                self.on_request(provider, model, stage, budget_prompt, max_output_tokens)
            return Completion(answer, estimated_input, estimated_output, provider, model, 0.0, True)
        key = self._credentials(provider)
        context = (model, stage, budget_prompt, max_output_tokens)
        if provider == "gemini":
            generation_config: dict[str, Any] = {"maxOutputTokens": max_output_tokens}
            if json_schema is not None:
                generation_config.update(
                    {"responseMimeType": "application/json", "responseJsonSchema": json_schema}
                )
            payload = {
                "contents": [{"role": "user", "parts": [{"text": budget_prompt}]}],
                "generationConfig": generation_config,
            }
            data = self._structured_request(
                provider,
                "POST",
                f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model, safe='')}:generateContent",
                headers={"x-goog-api-key": key},
                json=payload,
                structured_output=json_schema is not None,
                fallback_prompt=budget_prompt,
                request_context=context,
            )
            try:
                if data["candidates"][0].get("finishReason") == "MAX_TOKENS":
                    raise TruncatedOutputError(
                        "The model reached its output limit before completing this component.",
                        provider=provider,
                    )
                answer = "".join(
                    part["text"]
                    for part in data["candidates"][0]["content"]["parts"]
                    if isinstance(part, dict)
                    and not part.get("thought", False)
                    and isinstance(part.get("text"), str)
                )
            except (KeyError, IndexError, TypeError):
                raise ProviderError(
                    "Gemini returned no generated text (possibly filtered).", provider=provider
                ) from None
            usage = data.get("usageMetadata") or {}
            if not isinstance(usage, dict):
                usage = {}
            input_count = usage.get("promptTokenCount")
            candidates = usage.get("candidatesTokenCount")
            thoughts = usage.get("thoughtsTokenCount", 0)
            total = usage.get("totalTokenCount")
            output_counts: list[int] = []
            if _is_token_count(candidates) and _is_token_count(thoughts):
                output_counts.append(candidates + thoughts)
            if _is_token_count(total) and _is_token_count(input_count) and total >= input_count:
                output_counts.append(total - input_count)
            # Visible candidate counts can exclude reasoning tokens. Charge the
            # largest valid reported total without retaining hidden thought text.
            output_count = max(output_counts) if output_counts else None
        elif provider == "groq":
            groq_payload: dict[str, Any] = {
                "model": model,
                "messages": [{"role": "user", "content": budget_prompt}],
                "max_tokens": max_output_tokens,
                "temperature": 0.2,
            }
            if model in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}:
                # Verified Groq model capabilities, not model selection. Keep
                # hidden reasoning private and within the same output budget.
                groq_payload.update(
                    {
                        "reasoning_effort": "low",
                        "include_reasoning": False,
                        "max_completion_tokens": groq_payload.pop("max_tokens"),
                    }
                )
            if json_schema is not None:
                groq_payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "research_component",
                        "strict": False,
                        "schema": json_schema,
                    },
                }
            data = self._structured_request(
                provider,
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json=groq_payload,
                structured_output=json_schema is not None,
                fallback_prompt=budget_prompt,
                request_context=context,
            )
            try:
                if data["choices"][0].get("finish_reason") == "length":
                    raise TruncatedOutputError(
                        "The model reached its output limit before completing this component.",
                        provider=provider,
                    )
                answer = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise ProviderError("Groq returned no generated text.", provider=provider) from None
            usage = data.get("usage") or {}
            if not isinstance(usage, dict):
                usage = {}
            input_count, output_count = usage.get("prompt_tokens"), usage.get("completion_tokens")
        else:
            data = self._request(
                provider,
                "POST",
                self._ollama_url() + "/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": budget_prompt}],
                    "stream": False,
                    **({"format": json_schema} if json_schema is not None else {}),
                    "options": {
                        "num_predict": max_output_tokens,
                        "num_ctx": info.context_tokens,
                        "temperature": 0.2,
                    },
                },
                request_context=context,
            )
            message = data.get("message")
            answer = message.get("content") if isinstance(message, dict) else None
            input_count, output_count = data.get("prompt_eval_count"), data.get("eval_count")
        if not isinstance(answer, str) or not answer.strip():
            raise ProviderError(f"{provider} returned no generated text.", provider=provider)
        counted_input, input_estimated = _usage_count(input_count, estimated_input)
        counted_output, output_estimated = _usage_count(output_count, estimate_tokens(answer))
        return Completion(
            answer,
            counted_input,
            counted_output,
            provider,
            model,
            0.0 if provider == "ollama" else None,
            input_estimated or output_estimated,
        )

    def _structured_request(
        self,
        provider: str,
        method: str,
        url: str,
        *,
        fallback_prompt: str,
        structured_output: bool,
        json: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            return self._request(
                provider, method, url, json=json, structured_output=structured_output, **kwargs
            )
        except StructuredOutputUnsupportedError:
            # Exactly one compatibility retry, with the same provider, model,
            # prompt, output cap and accounting hook. Schema validation still
            # occurs in preparation; unsupported constrained decoding never
            # authorizes switching a model or bypassing application validation.
            fallback = dict(json)
            if provider == "gemini":
                fallback["generationConfig"] = {
                    key: value
                    for key, value in json["generationConfig"].items()
                    if key != "responseJsonSchema"
                }
                fallback["contents"] = [{"role": "user", "parts": [{"text": fallback_prompt}]}]
            else:
                fallback["response_format"] = {"type": "json_object"}
                fallback["messages"] = [{"role": "user", "content": fallback_prompt}]
            return self._request(provider, method, url, json=fallback, **kwargs)
