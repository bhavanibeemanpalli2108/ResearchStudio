"""Optional official LangSmith spans containing only selected safe metadata."""

from __future__ import annotations

import contextlib
import math
import os
import re
from collections.abc import Iterator, Mapping
from typing import Any
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid5

SAFE_FIELDS = frozenset(
    {
        "run_id",
        "project_id",
        "stage",
        "iteration",
        "profile",
        "provider",
        "model",
        "status",
        "input_tokens",
        "output_tokens",
        "duration_seconds",
        "demo",
        "error_code",
    }
)


def trace_metadata(values: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Allow-list identifiers and counts; never include prompts, files, or errors."""
    result = {}
    for key, value in dict(values or {}, **kwargs).items():
        if key not in SAFE_FIELDS or not isinstance(value, (str, int, float, bool, type(None))):
            continue
        if isinstance(value, float) and not math.isfinite(value):
            continue
        if isinstance(value, str):
            # Identifiers only. Secret-looking names and arbitrary text cannot
            # enter metadata even through a trusted field name.
            if (
                len(value) > 150
                or not re.fullmatch(r"[A-Za-z0-9._:/ -]*", value)
                or re.search(r"(?i)(api.?key|bearer|secret|token=|sk-)", value)
            ):
                value = "[redacted]"
        result[key] = value
    return result


def trace_root_id(run_id: str) -> str:
    try:
        return str(UUID(run_id))
    except ValueError:
        return str(uuid5(NAMESPACE_URL, "research-platform:" + run_id))


def tracing_status() -> dict[str, Any]:
    requested = os.environ.get("LANGSMITH_TRACING", "false").lower() in {"1", "true", "yes"}
    try:
        import langsmith  # noqa: F401

        available = True
    except ImportError:
        available = False
    return {
        "enabled": requested and available and bool(os.environ.get("LANGSMITH_API_KEY")),
        "sdk_available": available,
        "project": os.environ.get("LANGSMITH_PROJECT", "research-platform"),
        "redaction": "Only stage identifiers, model identifiers, counters and status are sent. Prompts, responses, documents and credentials are excluded.",
    }


@contextlib.contextmanager
def redacted_trace(
    name: str, run_id: str, stage: str, metadata: Mapping[str, Any] | None = None
) -> Iterator[dict[str, Any]]:
    """No-op when disabled; observability failures never stop a research run."""
    safe = trace_metadata(metadata, run_id=run_id, stage=stage)
    safe["root_id"] = trace_root_id(run_id)
    if not tracing_status()["enabled"]:
        yield safe
        return
    try:
        from langsmith import trace, tracing_context

        enabled_context = tracing_context(enabled=True, parent=False, metadata={})
        enabled_context.__enter__()
        span = trace(
            name=re.sub(r"[^A-Za-z0-9 _.-]", "", name)[:80],
            run_type="chain",
            inputs={},
            metadata=safe,
            project_name=os.environ.get("LANGSMITH_PROJECT", "research-platform"),
        )
        run_tree = span.__enter__()
        safe["trace_id"] = str(run_tree.id)
        try:
            url = run_tree.get_url()
            if isinstance(url, str):
                parsed = urlparse(url)
                if (
                    parsed.scheme in {"https", "http"}
                    and parsed.hostname
                    and not parsed.username
                    and not parsed.password
                    and not re.search(r"(?i)(api.?key|token|secret|bearer)", parsed.query)
                ):
                    safe["trace_url"] = url
        except Exception:
            pass
    except Exception:
        if "enabled_context" in locals():
            with contextlib.suppress(Exception):
                enabled_context.__exit__(None, None, None)
        yield safe
        return
    try:
        # Automatic child tracing could capture raw model arguments or graph
        # state. Only explicitly redacted spans may enable export again.
        with tracing_context(enabled=False):
            yield safe
    except BaseException:
        # Do not serialize exception messages; they can contain prompt content.
        try:
            span.__exit__(None, None, None)
        except Exception:
            pass
        finally:
            with contextlib.suppress(Exception):
                enabled_context.__exit__(None, None, None)
        raise
    else:
        try:
            span.__exit__(None, None, None)
        except Exception:
            pass
        finally:
            with contextlib.suppress(Exception):
                enabled_context.__exit__(None, None, None)
